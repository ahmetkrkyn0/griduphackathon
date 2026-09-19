-- Grid Up — merkez veritabani semasi (Faz 0 cekirdegi).
-- Kisi B bunu TB1'de genisletir. Yalnizca BOS bir volume'de ilk acilista calisir;
-- degistirdikten sonra:  docker compose -f deploy/compose.yaml down -v && up -d

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------- panolar
CREATE TABLE IF NOT EXISTS panels (
    pano_id       TEXT PRIMARY KEY,
    name          TEXT        NOT NULL,
    pano_type     TEXT        NOT NULL DEFAULT '1600kVA-dahili',
    lat           DOUBLE PRECISION,
    lon           DOUBLE PRECISION,
    installed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    baseline_day  SMALLINT    NOT NULL DEFAULT 0,   -- 7 = taban ogrenme tamamlandi
    notes         TEXT
);

-- --------------------------------------------------------------- telemetri
-- Uzun format: (ts, pano_id, tag, value). Etiket adlari contracts/ ile ayni
-- (or. t_conn.GIRIS_L2.dt_c, k_index.DSYA3_L2, elec.i_ph.0, env.td_margin_k).
CREATE TABLE IF NOT EXISTS telemetry (
    ts       TIMESTAMPTZ      NOT NULL,
    pano_id  TEXT             NOT NULL,
    tag      TEXT             NOT NULL,
    value    DOUBLE PRECISION,
    -- veri kalitesi bayrak alani. INTEGER: bitler alarm-codes.yaml bit numaralariyla
    -- eslesir ve ALM-DQ-BELOW-AMBIENT bit 16'dir; SMALLINT (maks. 32767) tasardi.
    q        INTEGER          NOT NULL DEFAULT 0
);
SELECT create_hypertable('telemetry', 'ts',
                         chunk_time_interval => INTERVAL '1 day',
                         if_not_exists      => TRUE);
CREATE INDEX IF NOT EXISTS telemetry_pano_tag_ts_idx
    ON telemetry (pano_id, tag, ts DESC);

-- Saklama politikasi (docs/09): ham 10 s -> 90 gun, 1 dk ozet -> 2 yil,
-- 15 dk ozet -> 10 yil, olay pencereleri suresiz. Kisi B TB3'te ekler:
--   SELECT add_retention_policy('telemetry', INTERVAL '90 days');
--   CREATE MATERIALIZED VIEW telemetry_1m WITH (timescaledb.continuous) AS ...

-- ------------------------------------------------------------------ olaylar
CREATE TABLE IF NOT EXISTS events (
    event_id     TEXT PRIMARY KEY,
    pano_id      TEXT        NOT NULL REFERENCES panels (pano_id),
    occurred_at  TIMESTAMPTZ NOT NULL,
    code         TEXT        NOT NULL,
    det_label    TEXT,                              -- or. 'X2:4' (TVOC-2 dedektor konumu)
    payload      JSONB       NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS events_pano_time_idx ON events (pano_id, occurred_at DESC);

-- ------------------------------------------------------------------ alarmlar
-- Durum makinesi ISA-18.2: active -> acked -> cleared; shelved sureli ve gerekceli.
CREATE TABLE IF NOT EXISTS alarms (
    id               BIGSERIAL PRIMARY KEY,
    event_id         TEXT        REFERENCES events (event_id),
    pano_id          TEXT        NOT NULL REFERENCES panels (pano_id),
    code             TEXT        NOT NULL,          -- contracts/alarm-codes.yaml
    prio             TEXT        NOT NULL CHECK (prio IN ('P1','P2','P3','INFO','SYS')),
    state            TEXT        NOT NULL DEFAULT 'active'
                     CHECK (state IN ('active','acked','shelved','cleared')),
    point            TEXT,
    raised_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    cleared_at       TIMESTAMPTZ,
    acked_at         TIMESTAMPTZ,
    acked_by         TEXT,
    shelved_until    TIMESTAMPTZ,
    shelve_reason    TEXT,
    escalation_level SMALLINT    NOT NULL DEFAULT 0,
    notified         TEXT[]      NOT NULL DEFAULT '{}',
    reason           JSONB       NOT NULL DEFAULT '{}'::jsonb,  -- 'Neden?' (L4 aciklama)
    advice           TEXT,                                       -- 'Ne yapmali?'
    ttl_h            DOUBLE PRECISION                            -- 'Ne kadar acil?'
);
CREATE INDEX IF NOT EXISTS alarms_state_prio_idx ON alarms (state, prio, raised_at DESC);
CREATE INDEX IF NOT EXISTS alarms_pano_idx       ON alarms (pano_id, raised_at DESC);

-- Bildirim denetim izi (KVKK: kime, ne zaman, hangi kanaldan)
CREATE TABLE IF NOT EXISTS notifications (
    id          BIGSERIAL PRIMARY KEY,
    alarm_id    BIGINT      NOT NULL REFERENCES alarms (id),
    channel     TEXT        NOT NULL CHECK (channel IN ('sms','whatsapp','telegram','call','scada','relay','ui')),
    recipient   TEXT        NOT NULL,               -- maskelenmis saklanir, or. +90*****4567
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    ok          BOOLEAN     NOT NULL DEFAULT TRUE,
    detail      TEXT
);

-- ---------------------------------------------------------------- karantina
-- Sema disi / fiziksel olmayan mesajlar DUSURULMEZ, buraya yazilir.
-- Verilen Excel'deki 15 dk'da 438 A siciramalari burada isaretlenir — jüriye
-- "sistemimiz gercek disi olcumleri ayirt ediyor" kaniti (rapor 15.2).
CREATE TABLE IF NOT EXISTS quarantine (
    id        BIGSERIAL PRIMARY KEY,
    received  TIMESTAMPTZ NOT NULL DEFAULT now(),
    topic     TEXT,
    reason    TEXT        NOT NULL,
    raw       JSONB
);

-- -------------------------------------------------------------- baslangic verisi
INSERT INTO panels (pano_id, name, lat, lon) VALUES
    ('ADM-00001', 'Efeler TM-14',   37.8450, 27.8396),
    ('ADM-00002', 'Nazilli TM-07',  37.9150, 28.3200),
    ('GDZ-00001', 'Bornova TM-22',  38.4700, 27.2200)
ON CONFLICT (pano_id) DO NOTHING;
