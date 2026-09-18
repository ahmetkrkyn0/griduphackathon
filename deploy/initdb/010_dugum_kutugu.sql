-- Grid Up — dugum ve sensor kutugu: seri no, parti, kalibrasyon vadesi ve nokta eslemesi
-- (F-31, Kisi B).
-- Yalnizca BOS bir volume'de ilk acilista calisir. Calisan veritabanina uygulamak icin
-- (yalnizca ekleme yapar, tekrar tekrar calistirilabilir):
--   docker exec -i gridup-timescaledb psql -U postgres -d gridup < deploy/initdb/010_dugum_kutugu.sql
--
-- HANGI BOSLUGU KAPATIYOR — ayrimi yapmazsak var olan bir yetenegi yeniden insa ederiz:
--   OLCUM NOKTASI kimligi ZATEN VAR. `t_conn[].pt` donmus semada sabit bir regex'e bagli
--   (GIRIS_L1 | DSYA4_L3 ...), kalite bitleri de nokta bazinda tutuluyor ve docs/05 §10
--   bir sapmayi nokta ADIYLA teshis edebiliyor. Burada eksik olan o DEGIL.
--   FIZIKSEL DUGUM kimligi YOK. `health` blogu yalnizca nodes_ok / nodes_total SAYILARINI
--   tasir. Bir dugum kayboldugunda "kac dugum gitti" biliniyor, "HANGI FIZIKSEL PARCA
--   gitti" bilinmiyor: seri no yok, uretim partisi yok, kalibrasyon vadesi yok ve
--   nokta <-> dugum eslemesi yok. Bu gocun tek isi odur.
--
-- TELEMETRI SEMASINA DOKUNULMADI. `t_conn[]` ve `health` icin additionalProperties: false
-- tanimli; kenara dugum kimligi alani acmak mesaji reddettirir ve uc dosyalik donmus
-- zinciri (sema -> Modbus haritasi -> uretilmis dokumanlar -> firmware basligi) tetiklerdi.
-- Gerek de yok: eslemeyi kutuk tutar, "hangi dugum sustu" sorusu MERKEZDE, noktanin
-- kalite bitlerinden YENIDEN TURETILIR (F-10'un _verify kacisiyla ayni desen).
--
-- "IZLENEBILIR OLCUM" IDDIASI YOKTUR. Metrolojik izlenebilirlik akredite bir kalibrasyon
-- zinciri gerektirir; bu depoda yok (GK3). Burada yapilan yalnizca KUTUK VE VADE TAKIBIDIR:
-- sensorun ne oldugu, ne zaman kalibre edildigi ve vadesinin ne zaman doldugu yazilir.
-- Sertifika numarasi alani BILEREK ACILMADI — dolduracak gercek bir kaynak olmadan alan
-- acmak GK10 ihlali olurdu.
--
-- HER SUTUN (kimlik disinda) NULL KABUL EDER: kutugu girilmemis dugum "veri yok" olarak
-- gorunur, sifir ya da bos dize olarak degil.

-- ------------------------------------------------------------------- dugum kutugu
CREATE TABLE IF NOT EXISTS nodes (
    node_id        TEXT PRIMARY KEY,
    pano_id        TEXT NOT NULL REFERENCES panels (pano_id) ON DELETE CASCADE,
    -- Kutuk alanlari. Hicbiri uydurulmaz; ice aktarilmayan alan NULL kalir.
    uretici        TEXT,
    model          TEXT,
    seri_no        TEXT,
    uretim_partisi TEXT,
    montaj_at      TIMESTAMPTZ,
    -- Kalibrasyon VADE TAKIBI (izlenebilirlik iddiasi degil, bkz. baslik).
    son_kalibrasyon_at     TIMESTAMPTZ,
    sonraki_kalibrasyon_at TIMESTAMPTZ,
    -- Kaydin NEREDEN geldigi kaydin icindedir; kaynagi yazilmayan kutuk kabul edilmez.
    kutuk_kaynak   TEXT NOT NULL,
    kutuk_at       TIMESTAMPTZ NOT NULL
);

-- Seri no filo genelinde benzersizdir; ayni sensoru iki panoda gostermek kutugun
-- kendisini anlamsizlastirirdi. Kismi indeks: seri no'su girilmemis dugumlerin hepsi
-- NULL tasir ve NULL'lar UNIQUE kisitini tetiklemez.
CREATE UNIQUE INDEX IF NOT EXISTS nodes_seri_no_idx ON nodes (seri_no) WHERE seri_no IS NOT NULL;

CREATE INDEX IF NOT EXISTS nodes_pano_idx ON nodes (pano_id);

-- Vadesi yaklasan sensorleri tek sorguda listelemek icin.
CREATE INDEX IF NOT EXISTS nodes_kalibrasyon_idx ON nodes (sonraki_kalibrasyon_at)
    WHERE sonraki_kalibrasyon_at IS NOT NULL;

-- --------------------------------------------------------------- nokta eslemesi
-- Bir dugum BIRDEN COK olcum noktasi tasiyabilir (cok kanalli sensor kartlari); bir
-- nokta ise tek bir dugume baglidir. Bu yuzden eslemede birincil anahtar NOKTADIR.
--
-- Eslemenin varlik sebebi: bir dugum sustugunda hangi NOKTALARIN korlestigi, dolayisiyla
-- hangi fiziksel parcanin degismesi gerektigi buradan okunur.
CREATE TABLE IF NOT EXISTS node_points (
    pano_id TEXT NOT NULL REFERENCES panels (pano_id) ON DELETE CASCADE,
    point   TEXT NOT NULL,
    node_id TEXT NOT NULL REFERENCES nodes (node_id) ON DELETE CASCADE,
    PRIMARY KEY (pano_id, point)
);

CREATE INDEX IF NOT EXISTS node_points_node_idx ON node_points (node_id);
