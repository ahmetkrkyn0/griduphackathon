-- Grid Up — altin demo veritabaninin kunyesi (F-01, Kisi B).
--
-- Bu tablo VERI DEGIL, verinin NEREDEN GELDIGIni tutar. GK10: demo veritabanindaki hicbir satir
-- sahadan olculmus degildir; hepsi libs/panoalgo fizik ureteciyle uretilmis SENTETIK veridir.
-- Bir ekran goruntusu ya da rapor bu veritabanindan cikiyorsa, `SELECT * FROM demo_seed` tek
-- basina kaynagi, tohumu ve pencereyi soyler — jurinin sormasina gerek kalmaz.
--
-- scripts/seed_demo.py her kosuda bu dosyayi idempotent olarak yeniden uygular (004_loadtest.sql
-- ile ayni desen: initdb yalnizca BOS bir volume'de calisir, mevcut veritabaninda calismaz).
-- Elle uygulamak icin:
--   docker exec -i gridup-timescaledb psql -U postgres -d gridup < deploy/initdb/006_demo_seed.sql

CREATE TABLE IF NOT EXISTS demo_seed (
    id              BIGSERIAL PRIMARY KEY,
    seeded_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    origin          TEXT        NOT NULL,   -- "sentetik ..." — veri kaynaginin tek cumlelik kunyesi
    script          TEXT        NOT NULL,   -- uretici betik + surumu
    scenario        TEXT        NOT NULL,   -- panoalgo senaryo kimligi (or. S0_normal)
    seed            INTEGER     NOT NULL,   -- ayni tohum -> ayni veri
    window_start    TIMESTAMPTZ NOT NULL,   -- uretilen gecmisin ilk ornegi
    window_end      TIMESTAMPTZ NOT NULL,   -- son ornegi (canli akisin devraldigi an)
    sample_period_s DOUBLE PRECISION NOT NULL,
    panels          INTEGER     NOT NULL,
    samples         INTEGER     NOT NULL,
    telemetry_rows  BIGINT      NOT NULL,
    alarms          INTEGER     NOT NULL,
    journal_entries INTEGER     NOT NULL,
    baseline_day    SMALLINT    NOT NULL,   -- taban ogrenme tamamlandi mi (7 = evet)
    digest          TEXT        NOT NULL    -- uretilen yukun sha256'si: tekrar uretilebilirlik kaniti
);
