-- Grid Up — denetim izinde kurcalama kaniti: hash zinciri (F-20, Kisi B).
-- Yalnizca BOS bir volume'de ilk acilista calisir. Calisan veritabanina uygulamak icin
-- (yalnizca ekleme yapar, tekrar tekrar calistirilabilir):
--   docker exec -i gridup-timescaledb psql -U postgres -d gridup < deploy/initdb/007_journal_chain.sql
--
-- Her alarm_journal satiri bir oncekinin ozetini icine alarak ozetlenir:
--   hash = sha256(prev_hash || alarm_id || at || action || state || by_user || note)
-- Hesap backend/app/journal_chain.py'dedir (SAF Python; veritabaninda hesaplanmaz ki
-- merkez ile bagimsiz dogrulayici AYNI kodu kullansin).
--
-- GERIYE DONUK HASH URETILMEZ. Bu gocten ONCEKI satirlarin hash'i NULL kalir ve
-- dogrulayici onlari "zincir oncesi" olarak sayar. Eski satirlara hash uretmek,
-- olmayan bir butunluk iddiasi olurdu: o satirlarin degismedigini kanitlayan bir sey yok.

ALTER TABLE alarm_journal ADD COLUMN IF NOT EXISTS prev_hash TEXT;
ALTER TABLE alarm_journal ADD COLUMN IF NOT EXISTS hash      TEXT;

-- Dogrulayici zinciri id sirasiyla yurur ve son halkayi okumak icin bu indeksi kullanir.
CREATE INDEX IF NOT EXISTS alarm_journal_chain_idx ON alarm_journal (id) WHERE hash IS NOT NULL;

-- Zincirin nerede basladigini KAYDA GECIRIR: dogrulayici "kac satir zincir disinda"
-- dedigin de bu satira bakilir. Tek satirlik tablo; goc tekrar kosarsa degismez.
CREATE TABLE IF NOT EXISTS journal_chain_start (
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    from_row_id  BIGINT,      -- bu id'den SONRAKI satirlar zincire dahildir (NULL = tablo bostu)
    note         TEXT
);

INSERT INTO journal_chain_start (from_row_id, note)
SELECT COALESCE(MAX(id), 0),
       'F-20 goc: bu id''den sonraki satirlar zincirlidir. Onceki satirlarin hash''i NULL ' ||
       've bilerek uretilmedi — degismediklerini kanitlayan bir sey yok.'
FROM alarm_journal
WHERE NOT EXISTS (SELECT 1 FROM journal_chain_start);
