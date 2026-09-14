-- Telemetri sikistirmasi (TB3 Adim 6, Kisi B).
--
-- Olcum (loadtest/storage.py, bir gunluk veri, 13 Eylul 2026, TimescaleDB 2.30):
--   7 nokta : sikistirmasiz 198 B/satir -> sikistirilmis 4,09 B/satir (48 kat)
--   25 nokta: sikistirmasiz 202 B/satir -> sikistirilmis 4,38 B/satir (46 kat)
-- Sikistirma olmadan 100 pano (7 nokta, 10 s) gunde 13,9 GB buyur; sikistirmayla 0,29 GB. Ayrinti: docs/09 §5.
--
-- Bir gunden eski parcalar pano + etiket segmentli, zamana gore sirali sikistirilir: bir pano/etiketin serisi
-- ardisik ve benzer degerlerden olustugu icin sutun sikistirmasi en yuksek orani burada verir.
-- Gec gelen veri (kenarin 7 gunluk tamponu) sikistirilmis parcaya da yazilabilir; /series okumasi ayni kalir
-- (backend/tests/test_compression.py).
--
-- initdb YALNIZCA bos volume'da calisir. Mevcut veritabanina uygulamak icin (tekrar calistirmak zararsizdir):
--   docker exec -i gridup-timescaledb psql -U postgres -d gridup < deploy/initdb/005_compression.sql

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'telemetry' AND compression_enabled
    ) THEN
        ALTER TABLE telemetry SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'pano_id, tag',
            timescaledb.compress_orderby   = 'ts DESC'
        );
    END IF;
END
$$;

SELECT add_compression_policy('telemetry', compress_after => INTERVAL '1 day', if_not_exists => TRUE);
