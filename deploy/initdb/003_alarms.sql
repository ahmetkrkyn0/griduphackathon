-- Grid Up — alarm yoneticisi kaliciligi (TB2, Kisi B).
-- Yalnizca BOS bir volume'de ilk acilista calisir. Calisan veritabanina uygulamak icin
-- (yalnizca ekleme yapar, tekrar tekrar calistirilabilir):
--   docker exec -i gridup-timescaledb psql -U postgres -d gridup < deploy/initdb/003_alarms.sql

-- Yeniden baslatmada durum makinesini geri yuklemek icin iki zaman (backend/app/alarm_manager.py):
--   last_true_at   : kosulun en son dogru goruldugu OLAY zamani  -> histerezis bundan olculur
--   annunciated_at : alarmin operatore duyuruldugu DUVAR saati -> eskalasyon bundan olculur
-- Alarm kimligini tek yazici olan alarm yoneticisi verir (acilista max(id)+1); bu yuzden
-- backend tek kopya calisir (docs/09: aktif-pasif).
ALTER TABLE alarms ADD COLUMN IF NOT EXISTS last_true_at   TIMESTAMPTZ;
ALTER TABLE alarms ADD COLUMN IF NOT EXISTS annunciated_at TIMESTAMPTZ;

-- Acilista yalnizca acik alarmlar yuklenir
CREATE INDEX IF NOT EXISTS alarms_open_idx ON alarms (id) WHERE state <> 'cleared';

-- ISA-18.2 denetim izi: kim, ne zaman, ne yapti (onay notu, raf gerekcesi, eskalasyon adimi).
-- Kara kutu zaman cizelgesi (GET /api/v1/events/{id}/blackbox) de buradan beslenir.
CREATE TABLE IF NOT EXISTS alarm_journal (
    id        BIGSERIAL PRIMARY KEY,
    alarm_id  BIGINT      NOT NULL REFERENCES alarms (id),
    at        TIMESTAMPTZ NOT NULL,              -- duvar saati (kaydin alindigi an)
    action    TEXT        NOT NULL,              -- raised|reactivated|returned|cleared|acked|shelved|unshelved|escalated
    state     TEXT        NOT NULL,              -- islemden sonraki durum
    by_user   TEXT,
    note      TEXT
);
CREATE INDEX IF NOT EXISTS alarm_journal_alarm_idx ON alarm_journal (alarm_id, at);
