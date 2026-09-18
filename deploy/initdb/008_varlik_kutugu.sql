-- Grid Up — varlik kutugu: CBS tekil kodu, kunye ve bakim takvimi (F-21, Kisi B).
-- Yalnizca BOS bir volume'de ilk acilista calisir. Calisan veritabanina uygulamak icin
-- (yalnizca ekleme yapar, tekrar tekrar calistirilabilir):
--   docker exec -i gridup-timescaledb psql -U postgres -d gridup < deploy/initdb/008_varlik_kutugu.sql
--
-- NEDEN panels TABLOSUNA SUTUN, AYRI TABLO DEGIL
-- EPDK CBS usul ve esaslari dagitim panosunu ZATEN tekil kodla ve kullanici tesisleriyle
-- eslestirilmis tutmayi zorunlu kiliyor: panonun kimligi musteride var, biz KAYNAK DEGIL
-- TUKETICIYIZ. Paralel bir varlik ana kaydi acmak (ayri tablo + kendi kimligi) ikinci bir
-- dogruluk kaynagi yaratirdi; backlog F-21'in "Dikkat" satiri bunu acikca yasakliyor.
--
-- pano_id BIRINCIL ANAHTAR OLARAK KALIR. cbs_kodu UNIQUE ikinci kimliktir. "Birincil alan
-- CBS tekil kodudur" ifadesi urun/ekran seviyesindedir; PK'yi degistirmek panel_latest,
-- events, alarms ve dolayli olarak alarm_journal yabanci anahtarlarini kirardi.
--
-- HER SUTUN NULL KABUL EDER. Bilinmeyen pano ilk telemetri mesajinda yalnizca
-- (pano_id, name) ile kendiliginden kaydolur (db.py _REGISTER_PANEL); NOT NULL bir sutun
-- eklemek alimi tamamen durdururdu. Bos kunye, "bu pano icin CBS aktarimi yapilmadi"
-- demektir ve API'de null olarak GORUNUR — sifir ya da bos dize yazilmaz.
--
-- URETICI VE SERI NO BILEREK BOS BIRAKILIR. Bu teslimde hicbir panoda doldurulmadi ve
-- demo tohumu da doldurmaz (GK3: gercek bir CBS aktarimina erisimimiz yok). Sutunlar
-- vardir cunku ice aktarim yolu vardir; uydurulmus bir deger yazmak GK10 ihlali olurdu.

-- --------------------------------------------------------------- CBS kimligi
ALTER TABLE panels ADD COLUMN IF NOT EXISTS cbs_kodu     TEXT;
ALTER TABLE panels ADD COLUMN IF NOT EXISTS fider_id     TEXT;
ALTER TABLE panels ADD COLUMN IF NOT EXISTS il           TEXT;
ALTER TABLE panels ADD COLUMN IF NOT EXISTS ilce         TEXT;

-- CBS tekil kodu filo genelinde benzersizdir. Kisi (partial) indeks: kunyesi girilmemis
-- panolarin hepsi NULL tasir ve NULL'lar UNIQUE kisitini tetiklemez, ama niyeti yazili
-- birakmak icin WHERE sarti aciktir.
CREATE UNIQUE INDEX IF NOT EXISTS panels_cbs_kodu_idx ON panels (cbs_kodu) WHERE cbs_kodu IS NOT NULL;

-- F-22 pano->fider eslemesini bu sutundan okur; ayni fiderdeki panolarin es zamanli
-- susmasi tek bir kesinti olayina toplanir.
CREATE INDEX IF NOT EXISTS panels_fider_idx ON panels (fider_id) WHERE fider_id IS NOT NULL;

-- ------------------------------------------------------------------- etki ekseni
-- abone_sayisi EPDK Kalite Yonetmeligi Madde 8/2'nin "etkilenen kullanici sayisi" alanini
-- besler ve risk matrisinin ETKI eksenidir. Sayilabilir bir buyukluktur; bir taksonomi
-- icat etmeyi gerektirmez.
ALTER TABLE panels ADD COLUMN IF NOT EXISTS abone_sayisi INTEGER;

-- trafo_kva pano BASINA degisir. pano_type ('1600kVA-dahili') kVA'yi tasir ama filodaki
-- HER PANODA AYNIDIR; sabit bir alani "etki" gibi gostermek yaniltici olurdu
-- (RiskMatrisi.tsx bunu kendi yorumunda yaziyordu).
ALTER TABLE panels ADD COLUMN IF NOT EXISTS trafo_kva    INTEGER;

-- kritiklik CBS/varlik yonetiminden ICE AKTARILAN bir etikettir; bizim tanimladigimiz bir
-- sozluk DEGILDIR. Erisilebilir bir standart siniflandirma bulunamadi ve GK10 geregi
-- erisemedigimiz bir metnin madde numarasi yazilmaz. CHECK, uydurma veri uretmek icin
-- degil AKTARIMI DOGRULAMAK icindir.
ALTER TABLE panels ADD COLUMN IF NOT EXISTS kritiklik    TEXT;
DO $$
BEGIN
    ALTER TABLE panels ADD CONSTRAINT panels_kritiklik_chk
        CHECK (kritiklik IS NULL OR kritiklik IN ('kritik', 'yuksek', 'orta', 'dusuk'));
EXCEPTION
    WHEN duplicate_object THEN NULL;   -- goc tekrar kostu; kisit zaten var
END $$;

-- ------------------------------------------------------------------- kunye
-- UYDURULMAZ, BOS BIRAKILIR. Bkz. dosya basindaki not.
ALTER TABLE panels ADD COLUMN IF NOT EXISTS uretici      TEXT;
ALTER TABLE panels ADD COLUMN IF NOT EXISTS seri_no      TEXT;

-- ------------------------------------------------------------------- bakim takvimi
ALTER TABLE panels ADD COLUMN IF NOT EXISTS son_bakim_at     TIMESTAMPTZ;
ALTER TABLE panels ADD COLUMN IF NOT EXISTS sonraki_bakim_at TIMESTAMPTZ;

-- ------------------------------------------------------------------- koken (provenance)
-- Kunyenin NEREDEN geldigi kaydin icindedir: kaynagi yazilmayan kunye kabul edilmez.
-- Bu, "alan acip bos birakmak" ile "tanimli bir kaynagi olan alan" arasindaki farktir
-- (docs/16 §Bolge haritasi bu itirazi kayda gecmisti).
ALTER TABLE panels ADD COLUMN IF NOT EXISTS kunye_kaynak TEXT;
ALTER TABLE panels ADD COLUMN IF NOT EXISTS kunye_at     TIMESTAMPTZ;
