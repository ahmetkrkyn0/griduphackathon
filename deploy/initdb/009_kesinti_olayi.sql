-- Grid Up — ust sebeke kesintisi olayi (F-22, Kisi B).
-- Yalnizca BOS bir volume'de ilk acilista calisir. Calisan veritabanina uygulamak icin
-- (yalnizca ekleme yapar, tekrar tekrar calistirilabilir):
--   docker exec -i gridup-timescaledb psql -U postgres -d gridup < deploy/initdb/009_kesinti_olayi.sql
--
-- NEDEN AYRI TABLO, events'e EKLENMEDI
-- `events` tablosu TEK PANOLUDUR: pano_id NOT NULL REFERENCES panels (001_schema.sql) ve
-- event_id bicimi alarm_manager icinde 'EVT-{alarm_id}'dir. Kesinti PANOLAR ARASI bir
-- olaydir; ona bir "temsilci pano" secmek, olmayan bir sahiplik uydurmak olurdu.
--
-- NEDEN alarm_journal'A YAZILMIYOR (F-20 zinciri)
-- alarm_journal.alarm_id NOT NULL REFERENCES alarms(id) (003_alarms.sql): alarma bagli
-- olmayan bir denetim izi satiri YAZILAMAZ. Kesintinin baglanacagi bir alarm yok — uydurma
-- bir alarm satiri acmak zincirin anlamini bozardi. Alt alarmlar ise bugunku yoldan
-- (tek yazici PgStore.save_alarm_changes, advisory kilit + link_hash sirasi) journal'a
-- yazmaya devam eder; yani ZINCIR NE CATALLANDI NE DE ANLAMI DEGISTI ve
-- scripts/verify_journal.py aynen calisir.
--
-- KIMLIK TURETILMISTIR: outage_id = OUT-{fider}-{baslangic UTC}. Alarm zamanlayicisi her
-- tik'te (5 s) ayni kesintiyi yeniden tespit eder; rastgele kimlik her tik yeni bir kayit
-- acardi. Turetilmis kimlik + ON CONFLICT yazmayi kendiliginden fikirli yapar.

CREATE TABLE IF NOT EXISTS outages (
    outage_id    TEXT PRIMARY KEY,
    fider_id     TEXT        NOT NULL,
    -- Panolarin sustugu an (kumedeki EN GEC last_rx). Enerjinin kesildigi anin OLCULEBILEN
    -- en iyi yaklasimidir; kesme aninin kendisi gozlemlenmiyor.
    started_at   TIMESTAMPTZ NOT NULL,
    -- Merkezin bagintiyi kurdugu an (haberlesme zaman asimi kadar sonra).
    detected_at  TIMESTAMPTZ NOT NULL,
    -- Haberlesmenin GERI DONDUGU an. DIKKAT: enerjinin geri geldigi an DEGILDIR ve
    -- histerezislidir. Restorasyon ani bu depoda olculmuyor (F-23 bunu isaretler).
    ended_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS outages_started_idx ON outages (started_at DESC);
CREATE INDEX IF NOT EXISTS outages_open_idx    ON outages (fider_id) WHERE ended_at IS NULL;

-- Olaya bagli panolar. Kesinti anindaki last_rx ve abone sayisi SAKLANIR (kopyalanir):
-- kunye sonradan degisirse gecmis kesinti kaydi degismemeli — EPDK kaydi o gunun
-- verisiyle duzenlenir.
CREATE TABLE IF NOT EXISTS outage_panels (
    outage_id    TEXT NOT NULL REFERENCES outages (outage_id) ON DELETE CASCADE,
    pano_id      TEXT NOT NULL REFERENCES panels (pano_id),
    last_rx      TIMESTAMPTZ NOT NULL,
    abone_sayisi INTEGER,        -- NULL = kunye yok; SIFIR DEGIL
    PRIMARY KEY (outage_id, pano_id)
);

-- ALARMA SUTUN EKLENMEDI — bilincli.
-- Alt alarmin kesintiye baglanmasi (`Alarm.outage_id`) SAKLANMAZ, TURETILIR: bir alarm,
-- panosu kesintiye dahilse VE olayin baslangicindan sonra aciImissa o kesintinin parcasidir.
-- Gerekce: baglanti zaten pano + zaman penceresinin bir SONUCUDUR, bagimsiz bir olgu degil;
-- saklamak onu alarm yazma yoluna (tek yazici, F-20 hash zincirinin de gectigi sicak yol)
-- yeni bir sutun sokmak demekti ve ayni bilgiyi iki yerde tutup ayrisma riski yaratirdi.
-- Turetme kurali backend/app/api/outages.py icindedir ve testle kilitlidir.
