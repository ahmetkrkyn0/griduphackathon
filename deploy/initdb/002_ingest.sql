-- Grid Up — ingest son durum tablosu (TB1, Kisi B).
-- Yalnizca BOS bir volume'de ilk acilista calisir. Mevcut volume'u guncellemek icin:
--   docker compose -f deploy/compose.yaml down -v && docker compose -f deploy/compose.yaml up -d

-- Panonun en son telemetri yuku. Filo listesi ve pano detayi buradan okunur:
-- 1.000 pano = 1.000 satir; hypertable uzerinde "her panonun son satiri" sorgusu gerekmez.
--   ts/seq/payload -> yalnizca DAHA YENI olcumle degisir (7 gunluk backfill son durumu ezmez)
--   last_rx        -> her mesajda ilerler (haberlesme sagligi = merkezin en son ne zaman duydugu)
CREATE TABLE IF NOT EXISTS panel_latest (
    pano_id  TEXT        PRIMARY KEY REFERENCES panels (pano_id),
    ts       TIMESTAMPTZ NOT NULL,
    seq      BIGINT      NOT NULL,
    last_rx  TIMESTAMPTZ NOT NULL,
    payload  JSONB       NOT NULL
);
