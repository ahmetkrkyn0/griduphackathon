# 08 — Kurulum Prosedürü

> **Sahip:** Kişi C · Kaynak: `HACKATHON_ANALIZ_RAPORU.md` §7.1. Hedef: **tek planlı kesinti
> penceresi**, ≤45 dakika, 2 kişilik saha ekibi.

> **Bu dokümanın dürüstlük sınırı (tek cümle):** aşağıdaki prosedür **hiçbir gerçek panoda
> uygulanmadı.** ≤45 dk hedefi bir tasarım hedefidir, sahada ölçülmedi
> (`docs/19-tedas-sartname-uyumu.md` satır 67, madde 5.3). §6–§11'deki tablolar mevcut belgelerin
> (docs/07, docs/07b, docs/13, docs/19, `contracts/`, kod) **çapraz bağıdır**; yeni bir ölçüm,
> yeni bir RÖS ve yeni bir eşik üretmez.

## 1. Kesinti öncesi (pano enerjili, dokunmasız)

1. **Uzaktan hazırlık:** Pano kimliği (`pano_id`, ör. `ADM-00014`), tipi (1600 kVA dahili),
   SIM/APN, cihaz sertifikası ve Modbus adres planı merkez sistemde önceden oluşturulur.
2. **Saha keşfi:** Pano fotoğrafları, RS485 hattında mevcut bir master (modem/RTU) olup olmadığı
   tespit edilir → `docs/03-modbus-haritasi.md` §2'deki Senaryo A/B/C'den hangisinin uygulanacağı
   belirlenir; harici anten çıkışının durumu kontrol edilir (şartname 2.2.8.1.iv).
   *(Düzeltme: bu satır daha önce `docs/02-mimari.md`'ye atıf yapıyordu; Senaryo A/B/C tablosu
   orada değil, `docs/03` §2'dedir — `docs/03-modbus-haritasi.md:26-34`.)*

## 2. Planlı kesinti penceresi (hedef ≤ 45 dk, 2 kişilik ekip)

> **5 güvenlik kuralı** (şartname madde 5.3) — sıra kesinlikle bozulmaz:
> 1) Gerilimi kes → 2) Tekrar gelmesini engelle (kilitle-etiketle) → 3) Gerilim yokluğunu
> kontrol et → 4) Toprakla ve kısa devre et → 5) Çalışma alanını işaretle.

1. Pano Beyni'ni üst bölmedeki DIN rayına tak; besleme **iç ihtiyaç devresinden, sigortalı,
   fişli klemensle** alınır (yeni bir güç hattı çekilmez).
2. RS485'i MPR-53CS/TVOC-2 hattına bağla — izoleli port, hat sonu 120 Ω direnç anahtarı kontrolü.
3. **Bağlantı sıcaklık düğümlerini** (S1) V-0, yüksek sıcaklık sınıfı kablo bağı/kelepçe ile
   pabuç/bara eklerine tak. **Sensör gövdesi hiçbir fazlar arası/faz-toprak açıklığı (clearance)
   veya kaçak yolu (creepage) mesafesini azaltmamalı** (bkz. `docs/13` yalıtım koordinasyonu).
4. Termal dizi (S2) braketini saydam kapağın **iç** tarafına, ortam düğümlerini (S3/S4) alt ve
   üst bölgeye, kapı reed'ini (S5) kapıya monte et (tam konumlar: `hardware/yerlesim/ek2-14-yerlesim.svg`).
5. **(Opsiyonel) Fider akımı ölçümü:** yalnızca ayrık çekirdekli (devreyi açmayan) sensör
   kullanılır. **⚠ AT sekonderi hiçbir koşulda açık devre bırakılmaz** — bu, FMEA'daki (`docs/07`
   satır 10) en ağır donanım riskidir; kontrol listesinde ayrıca imzalanır.
6. Anteni şartnamedeki harici anten çıkışından geçir.
7. Kapakları kapat, enerjiyi ver.

## 3. Kesinti sonrası (pano enerjili, dokunmasız)

1. **Devreye alma kontrolü:** Her düğümün rapor verdiği doğrulanır (canlı yığında `CihazSagligi`
   ekranı, `nodes_ok / nodes_total`).
2. **Otomatik testler:** Modbus okumaları makul mü (CT oranı = 500 kontrolü — bkz.
   `contracts/modbus-map.yaml` `electrical_mirror` bloğu), TVOC-2 ID ≠ 248 mü, test alarmı
   bildirimi geldi mi. Ölçülebilir hâli: **§7 kabul kriterleri tablosu**.
3. **7 günlük taban öğrenme modu:** Yalnızca L0 (mutlak limit) alarmları aktiftir; L1/L2 (ısıl
   direnç indeksi, istatistiksel sapma) 7 gün sonra devreye girer (`health.baseline_day` alanı
   arayüzde bu ilerlemeyi gösterir, bkz. `PanoDetay.tsx`). Bu cümlenin **kod düzeyindeki tam
   karşılığı ve bir kapsam düzeltmesi §10'dadır.**

## 4. Kontrol listesi (saha ekibi imzalar)

Maddeler §6'daki FMEA çapraz bağı tablosundan **K** kimlikleriyle anılır.

- [ ] **K1** — 5 güvenlik kuralı sırayla uygulandı
- [ ] **K2** — Yeni güç hattı çekilmedi (iç ihtiyaçtan, sigortalı)
- [ ] **K3** — RS485 hat sonu direnci doğrulandı
- [ ] **K4** — Sensör gövdeleri clearance/creepage mesafesini azaltmadı
- [ ] **K5** — AT sekonderi (kullanıldıysa) hiçbir an açık devre kalmadı
- [ ] **K6** — Anten harici çıkıştan geçirildi
- [ ] **K7** — Devreye alma sonrası tüm düğümler rapor veriyor
- [ ] **K8** — Test alarmı bildirimi alıcıya ulaştı (açık kanal yapılandırmaya bağlıdır:
      `SMS_DEVICE` / `TELEGRAM_*` / `WHATSAPP_*` — `backend/app/notify/dispatcher.py:81-98`)
- [ ] **K9** — S1 düğümleri **çift bağ** ile tespit edildi (V-0 kablo bağı + mekanik kilit) —
      `docs/07` satır 1 önlem sütunu
- [ ] **K10** — Mevcut master testi yapıldı; Senaryo A/B/C kararı kayda geçti
      (`docs/03-modbus-haritasi.md` §2, satır 26-34)
- [ ] **K11** — Üç fazın **karşılıklı** noktalarına düğüm kondu; ortam düğümleri alt/üst bölgede
      (çapraz kontrolün ön koşulu — `docs/07` satır 9)
- [ ] **K12** — Her düğümün devreye alma anındaki `health.vbak_pct` değeri kaydedildi
      (`docs/07` satır 2)
- [ ] **K13** — `arc_mirror` okunuyor: `tvoc_comm_ok` = 1 **ve** `prot_health_ok` = 1
      (`contracts/modbus-map.yaml:152-153`)

## 5. Uzaktan yönetim (kesintisiz işletme)

Kurulumdan sonra sahaya **dokunmadan**: konfigürasyon, eşik parametreleri (`alarm-codes.yaml`
üzerinden merkez), firmware güncellemesi (imzalı OTA, A/B bölümlü + otomatik geri dönüş) ve
uzaktan tanılama yapılabilir. Bakım gerektiren tek fiziksel bileşen, pilli varyantta ≥10 yıl
hedefli pil değişimidir (pil telemetrisi `health` alanında izlenir).

> **Sınır:** imzalı OTA bu teslimde **uygulanmadı**; `docs/15` §3.5'te 📐 tasarım düzeyindedir ve
> `GELISTIRME-BACKLOGU.md` onu MoSCoW **Won't** sayar (`docs/19` satır 91). Yukarıdaki cümle bir
> **tasarım hedefidir**, çalışan bir yetenek değildir.

---

## 6. FMEA çapraz bağı — hangi arıza modu hangi adımda önleniyor

Amaç: `docs/07-fmea-donanim-saha.md`'deki her satırın kurulum prosedüründe bir **fiziksel
karşılığı** olduğunu göstermek. **RÖS değerleri `docs/07`'den olduğu gibi alınmıştır; bu doküman
yeni RÖS üretmez ve mevcut RÖS'leri düşürmez.**

| FMEA satırı (`docs/07`) | RÖS (önce → önlem sonrası) | Önleyen kurulum adımı | Kontrol listesi | Kurulumda neye bakılır |
|---|---|---|---|---|
| **1** — Bağlantı sıcaklık düğümü yerinden düştü (`docs/07:9`) | 135 → 36 | §2 md. 3 (V-0 kablo bağı/kelepçe, clearance/creepage korunur) | **K4, K9** | Çift bağ takılı mı; gövde hiçbir açıklığı daraltıyor mu. Düşerse merkez tarafı `ALM-DQ-BELOW-AMBIENT` ile yakalar — bu **tespittir, önlem değil** |
| **2** — Düşük yükte enerji toplama yetersiz (`docs/07:10`) | 72 → 24 | §2 md. 3 (düğüm yerleşimi) + §3 md. 1 (devreye alma okuması) | **K12** | Düğüm sağlığında `health.vbak_pct`; düşük yükte **seyrek gönderim** beklenen davranıştır (`docs/07:10` önlem sütunu). Düğüm beslemesi hibrittir: akım varken manyetik hasat, yokken primer pil (`hardware/sensor-dugumu/README.md:19` — **tasarım/hesap, ölçüm değil**) |
| **3** — Kontrolcü beslemesi kesildi (`docs/07:11`) | 84 → 28 | §2 md. 1 (iç ihtiyaç devresi, sigortalı fişli klemens; şartname 2.2.12) | **K2** | Yeni hat çekilmediği, sigorta seçiciliği. Kesilirse süperkapasitörle `ALM-LASTGASP`, merkezde `ALM-COMMS-LOST` (§11) |
| **9** — Sensör kalibrasyon kayması (`docs/07:12`) | 120 → 45 | §2 md. 3 ve 4 (fazlar arası karşılıklı noktalar + ortam düğümleri) | **K11** | Çapraz kontrolün (`FazKarsilastirma`, `frontend/src/pages/PanoDetay.tsx`) çalışabilmesi için üç fazda **eşdeğer** noktaların seçilmiş olması; gece "eşitlenme" kontrolü ortam sensörlerine dayanır (`docs/07:12`) |
| **10** — Kurulumda AT sekonderinin açık devre kalması (`docs/07:13`) | 80 → 20 | §2 md. 5 (yalnızca ayrık çekirdekli sensör) | **K5** (ayrıca imzalanır) | Sekonder hiçbir an açık kalmadı. `hardware/pano-beyni/io-tablosu.md:21`: "AT sekonderi asla açık bırakılmaz (kurulum kuralı)" |

**`docs/07b`'den (yazılım/sistem) sahada kapanan iki satır** — RÖS'ler `docs/07b`'den alınmıştır:

| FMEA satırı (`docs/07b`) | RÖS | Kurulum karşılığı | Kontrol listesi |
|---|---|---|---|
| **6** — Bizim RS485 bağlantımız mevcut Modbus sorgusunu bozdu (`docs/07b:23`) | 160 → **hedef** 16 | §1 md. 2 saha keşfi + §2 md. 2 izoleli port; Senaryo A/B/C kararı (`docs/03` §2) | **K3, K10** |
| **8** — Kaçırılan alarm (`docs/07b:25`) | 210 → **hedef** 80 | §3 md. 2 sentetik test alarmı (komut register'ı `test_alarm`, `contracts/modbus-map.yaml:207`) | **K8** |

> **Bu tablonun söylemediği:** `docs/07b:60` #6'yı "sahada keşif ve devreye alma prosedürüyle
> kapanır" diye yazar; **kapandığı gösterilmedi**, çünkü prosedür hiçbir sahada uygulanmadı.
> Buradaki bağ bir **izlenebilirlik** bağıdır, bir doğrulama kanıtı değil.

---

## 7. Devreye alma kabul kriterleri — "kurulum başarılı" ne demek

Aşağıdaki maddelerin **hepsi** sağlanmadan kurulum kapatılmaz. Her satırın nerede görüleceği ve
kaynağı yazılıdır; eşikler `contracts/` içinden gelir, bu doküman eşik **üretmez**.

| # | Kabul ölçütü | Beklenen değer | Nerede görülür | Kaynak |
|---|---|---|---|---|
| **KK1** | Tüm düğümler rapor veriyor | `nodes_ok == nodes_total` | `CihazSagligi` ekranı; `GET /api/v1/fleet/health` | `contracts/modbus-map.yaml:36-37`; `frontend/src/pages/CihazSagligi.tsx:88-89` |
| **KK2** | Enerji analizörü okunuyor ve CT oranı doğru | `mpr_comm_ok` = 1; `I_primer = ham × 0,001 × CT`, **CT = 500** | `electrical_mirror` bloğu (PDU 400-449) | `contracts/modbus-map.yaml:116, 130` |
| **KK3** | TVOC-2 fabrika kimliğinde değil | `tvoc_comm_ok` = 1 (ID 248'de cevap gelmez) | `arc_mirror` bloğu | `contracts/modbus-map.yaml:153` |
| **KK4** | Ark koruması sağlıklı | `prot_health_ok` = 1 (**0 = pano korumasız**) | `arc_mirror` + coil 4 | `contracts/modbus-map.yaml:152, 216` |
| **KK5** | Sentetik test alarmı uçtan uca gitti | Alıcıda bildirim **ve** `alarm_journal`'da kanal kaydı | Komut bloğu `test_alarm` → MQTT `cmd` → kenar | `contracts/modbus-map.yaml:207`; `backend/app/scada/gateway.py:27, 300-309`; `backend/app/main.py:327`; denetim izi `docs/06-alarm-matrisi.md:177` |
| **KK6** | Merkez servis sağlığı | `ok` = true, `db` = true, `mqtt` = true, `contracts` = true; `ingest.rejected` ve `ingest.dropped` **artmıyor**; SCADA ağ geçidi devredeyse `scada.listening` = true ve `scada.error` = null (devrede değilse `scada` = `null`) | `GET /health` | `backend/app/main.py:216-244` (alan adları), `backend/app/scada/service.py:121-130` (`scada` alt alanları), `backend/app/ingest.py:162` (sayaç adları) |
| **KK7** | Taban öğrenme başladı | `health.baseline_day` 1…7 arasında ve **her gün artıyor** | Pano detayında "Taban öğrenme — N. gün" | `contracts/modbus-map.yaml:40`; `contracts/mqtt-telemetry.schema.json:194`; `frontend/src/pages/PanoDetay.tsx:552-553` |
| **KK8** | Haberleşme kesintisi alarmı yok | `ALM-COMMS-LOST` açık değil (eşik `heartbeat_timeout_min` = 5 dk) | Alarm konsolu | `contracts/alarm-codes.yaml:210-215`; `docs/06-alarm-matrisi.md:158-163` |

**`/health` yanıtının gerçek alanları** — uydurulmamıştır: `backend/app/main.py:216-244`'ten **ve**
gerçekten çalıştırılmış bir `/health` yanıtından okunmuştur (**ingest ve SCADA kapalı**
bir yapılandırma, `TestClient`):

`ok`, `version`, `mqtt`, `mqtt_tls`, `db`, `contracts`,
`contracts_loaded{alarm_codes, hypotheses, ingest_topics}`,
`ingest{received, rejected, written, dropped, write_errors}`, `scada`,
`auth{enabled, users, protects}`.

> **Üç alan devreye almada yanlış okunmasın diye:**
> - `mqtt_tls` **varsayılan demo yolunda false**'tur (düz 1883, anonim broker). Bu bir kurulum
>   hatası değil, bilinçli ve `/health`'te **görünür** kılınmış bir varsayılandır
>   (`backend/app/main.py:224-227`; `docs/07b:27`).
> - `auth.enabled` operatör tablosu tanımsızsa **false**'tur ve bu da kasıtlı olarak `/health`'te
>   görünür (`backend/app/main.py:160, 237-243`).
>   İkisi de üretim kurulumunda **açılması gereken** kalemlerdir; kabul kriteri olarak "true olmalı"
>   demiyoruz çünkü bu teslimde varsayılan yol kapalıdır.
> - `scada` alt alanlarının adları (`listening`, `port`, `error`, `connections`, `iec104` ve ağ
>   geçidi özeti) **kod kaynağından** verilmiştir; yukarıdaki koşuda `scada` `null` döndü.

---

## 8. Geri alma — kurulum yarıda kalırsa

**Temel soru:** modül enerjisiz bırakılırsa pano normal çalışmaya devam eder mi?
**Cevap: iki koşulla evet.**

| Neden devam eder | Dayanak |
|---|---|
| Koruma bizden bağımsızdır. TVOC-2 ark koruması panoda zaten vardır; bizim rolümüz **salt okunur izleme**dir, koruma devresine yazma yapılmaz | `PLAN.md:28` (GK6); `contracts/modbus-map.yaml:136` `access: read_only`; `docs/19:57` |
| Komut bloğunda **hiçbir şalt kumandası yoktur.** Yazılabilen tek şeyler: `password`, `ack_alarm`, `reset_latch`, `maint_mode`, `test_alarm` | `contracts/modbus-map.yaml:195-207` |
| "Röle kumandası **yoktur** (GK6)" deponun kendi kaydıdır; IEC 104 tarafında tüm kontrol ASDU'ları reddedilir | `README.md:29`; `docs/04-iec104-haritasi.md:380` |

> **Kapsam:** yukarıdaki üç satır **tasarım ve sözleşme düzeyinde** doğrudur.
> `BAGIMSIZ-DEGERLENDIRME.md:357`'de aynı iddianın protokol düzeyinde sınandığı kayıtlıdır;
> **bu oturumda yeniden ölçülmedi** ve gerçek bir panoda hiç denenmedi.

### 8.1 İki koşul — bunlar sağlanmazsa "evet" cevabı düşer

| Koşul | Neden | Dayanak |
|---|---|---|
| **(a) Senaryo C uygulanmamış olmalı.** Senaryo C'de RS485 hattı Pano Beyni **üzerinden geçirilir** (şeffaf ağ geçidi: RTU → slave port → master port → cihazlar). Modül enerjisiz kalırsa **mevcut RTU/SCADA okuması da kopar** | Yalnızca **Senaryo B**'de hat bizden bağımsızdır (orada dinleyiciyiz veya RTU'nun ikinci portundayız). **Senaryo A**'da Pano Beyni hattın *master*'ıdır ve RTU bizim slave portumuzdan okur — modül enerjisiz kalırsa RTU'nun okuması da durur; fark şudur: A'da bizden ÖNCE de kimse sorgulamıyordu, C'de ise mevcut bir okuma kesilir | `docs/03-modbus-haritasi.md:32-34` — **değerlendirme, sahada doğrulanmadı** |
| **(b) Röle çıkışlarının neyi sürdüğü kayda geçmiş olmalı.** RELAY1 siren/flaşör (P1), RELAY2 ısıtıcı/fan (P2). Modül enerjisiz kalırsa bu iki çıkış da düşer | Sözleşmede `local_relay: siren` (P1) ve `local_relay: heater_fan` (P2) tanımlıdır | `hardware/pano-beyni/io-tablosu.md:17-18`; `contracts/alarm-codes.yaml:34, 44` |

> **AÇIK KALEM (bu dokümanda ilk kez yazılıyor):** RELAY2'nin panonun **mevcut** ısıtıcı/fan
> kumandasının *yerine mi geçtiği* yoksa ona *ek mi* olduğu depoda hiçbir yerde tanımlı **değildir**.
> Yerine geçiyorsa geri alma sonrası ısıtıcı/fan kumandası da düşer. Bu, geri alma adımından
> **önce** sahada karara bağlanmalıdır. Depoda dayanağı yoktur — bu bir soru, bir iddia değil.

### 8.2 Geri alma adımları

Sıra, §2'deki 5 güvenlik kuralına **aynen** tabidir (şartname madde 5.3); geri alma da bir
kesinti işidir, enerjili yapılmaz.

| Sıra | Adım | Neden |
|---|---|---|
| 1 | 5 güvenlik kuralı (§2) | Söküm de kurulum kadar risklidir |
| 2 | **AT sekonderi kullanıldıysa: burden devresi sökülmeden önce sekonder kısa devre edilir** | `docs/07` satır 10 ve `io-tablosu.md:21`'in doğrudan sonucu: sekonder hiçbir an açık kalmaz |
| 3 | S1/S2/S3/S4/S5 düğümleri sökülür (**sensör türü etiketleri, düğüm sayısı değil** — `docs/10` §7.3); bara/pabuç ekleri **kuruluma girmeden önceki hâline** döner | Sensör montajının bağlantının ısıl direncini ve montaj kuvvetinin bara bağlantısını değiştirip değiştirmediği **bilinmiyor** (`docs/19:56, 62`) — panoyu belirsiz bir ara durumda bırakmamak için |
| 4 | RS485 bağlantısı sökülür; **hat sonu 120 Ω anahtarı kuruluma girmeden önceki konumuna** alınır | §2 md. 2'nin tersi; hattı bozmamak #6'nın (`docs/07b:23`) tek fiziksel önlemidir |
| 5 | Senaryo C uygulandıysa: hat **modülü atlayarak** eski doğrudan bağlantısına döndürülür | §8.1 (a) |
| 6 | İç ihtiyaç fişli klemensi çekilir, modül DIN raydan alınır | §2 md. 1'in tersi |
| 7 | Anten harici çıkıştan geri alınır, çıkış eski hâline kapatılır | §2 md. 6'nın tersi; şartname 2.2.8.1.iv |
| 8 | Merkezde pano **bakım moduna** alınır | Aksi hâlde susan pano 5 dk sonra `ALM-COMMS-LOST` üretir; bakım modundaki ve hiç veri göndermemiş pano bu alarmı üretmez (`docs/06:160-163`). **Panoyu merkez kaydından tamamen düşüren bir akış depoda tanımlı değildir** — açık kalem |
| 9 | Kesinti kapatılır; hangi adımda durulduğu ve §8.1'deki iki koşulun sahadaki cevabı kayda geçer | İkinci denemede saha keşfi (§1 md. 2) sıfırdan yapılmasın diye |

---

## 9. Yetkinlik, ekip ve KKD

| Konu | Depodaki dayanak | Durum |
|---|---|---|
| İş güvenliği yordamı | Şartname **madde 5.3** — 5 güvenlik kuralı (`docs/19:67`, `docs/08` §2 ve §4/K1) | **Yazılı ve imzalı** |
| Ekip büyüklüğü | **2 kişi** (bu dokümanın başlığı ve `docs/19:67`) | **Hedef** — sahada ölçülmedi |
| Çalışma biçimi | Prosedürün tamamı **enerjisiz** penceredir; §1 ve §3 "pano enerjili, **dokunmasız**" adımlardır | Tasarım kararı |
| **Kimin yapabileceği (yetkinlik/belge)** | **Depoda hiçbir dayanak yok.** Aranan yetki belgesi, eğitim, tatbikat kaydı hiçbir dosyada tanımlı değil | **Kurum prosedürüne tabidir** — bu doküman bir yetkinlik şartı **tanımlamaz** |
| **KKD (kişisel koruyucu donanım)** | **Depoda hiçbir dayanak yok.** `Yapilacaklar.md:582` yalnızca "hangi KKD" sorusunun sorulması gerektiğini yazar; cevabı hiçbir yerde yoktur | **Kurum prosedürüne tabidir.** Ark parlaması sınıfı, giysi seviyesi, mesafe sınırı **hesaplanmadı ve yazılmadı** — yazılsaydı uydurma olurdu |

> **Neden boş bırakıldı:** ark parlaması KKD sınıfı, panonun kısa devre gücüne ve temizleme
> süresine bağlı bir **hesaptır**. Depoda 38 kA etken / 80 kA tepe değerleri vardır (`docs/13:68`)
> ama bu hesap **yapılmadı** ve dayandığı standardın metnine erişilmedi (aynı gerekçe `docs/13:77-79`
> ve `docs/19:23-25`). Bir sınıf numarası yazmak, bu teslimin tek doğrulanabilir çıktısı olan
> dürüstlüğü harcardı.

---

## 10. Kurulum sonrası ilk 7 gün — operatör ne görür, neyi alarm saymamalı

Taban penceresinin sözleşmedeki uzunluğu: `baseline_learning_days` = **7**
(`contracts/alarm-codes.yaml:282`).

| Ne olur | Telemetrideki izi | Dayanak |
|---|---|---|
| Kenar `BASELINE` durumundadır; K₀ öğrenilir | `health.baseline_day` 1…7 | `firmware/akis-diyagramlari/ana-dongu.md:48` |
| **K/K₀ sabit 1.0 raporlanır** → `ALM-K-WARN` ve `ALM-K-ALM` tetiklenemez | `k_index` bloğu 100 (yani 1,0) | `libs/panoalgo/panoalgo/edge.py:25-30`; `firmware/akis-diyagramlari/ana-dongu.md:54-57` |
| Kestirim yoksa `ttl_h` yükten **silinir** → `ALM-TTL-14D` üretilemez | Nokta nesnesinde `ttl_h` yok | `libs/panoalgo/panoalgo/edge.py` (`ESTIMATED_FIELDS`) |
| Arayüzde nokta geçerliliği **"ogreniyor"** görünür | `reason.gecerlilik` | `backend/app/api/views.py:103` |
| L0 (mutlak limit) kodları **her zaman etkin**: terminal/bara sıcaklık artışı, faz farkı, aşırı akım, ark tripi, koruma sağlığı, pano iç sıcaklığı, kapak, son nefes | `alarms[]` | `docs/06-alarm-matrisi.md` §9 alarm kataloğu (L0 satırları) |

**Operatörün ilk 7 günde alarm saymaması gerekenler:**

| Görülen | Neden alarm değil | Dayanak |
|---|---|---|
| Tüm noktaların geçerliliği "ogreniyor" | Taban henüz donmadı; K/K₀ 1,0 raporlanıyor | `backend/app/api/views.py:103` |
| SYS kodları (`ALM-COMMS-LOST`, `ALM-NODE-LOST`, `ALM-DQ-*`) | Hipotezleri `HYP-SELF-FAULT`'tur — **"arıza alarmı değil"**, cihazın kendi durumudur; SYS önceliği anında kimseyi aramaz (`sms: digest_only`) | `contracts/alarm-codes.yaml:59-63`; `docs/06:37`, `docs/06:160-163` |
| P3 uyarıları | P3 **kimseyi aramaz**, günlük özete düşer | `contracts/alarm-codes.yaml:46-54`; `docs/07b:24` |
| Günde bir gelen toplu özet | `DIGEST_AT` ile açıkça kaydedilen günlük P3/SYS özeti | `backend/app/main.py:264-277` |

> **KAPSAM DÜZELTMESİ (§3 md. 3'ün tam karşılığı).** "7 gün boyunca yalnızca L0 aktiftir" ifadesi
> **K tabanlı L1 kodları için doğrudur** (`ALM-K-WARN`, `ALM-K-ALM`, `ALM-TTL-14D`): bunlar
> `k_ratio` ve `ttl_h` üzerinden tanımlıdır ve taban donmadan bu değerler üretilmez
> (`libs/panoalgo/panoalgo/limits.py:57-59`). **Çiy noktası kodları (`ALM-DEW-WARN`,
> `ALM-DEW-ALM`) sözleşmede L1 olmalarına rağmen K₀'a bağlı DEĞİLDİR** — kararları doğrudan
> `env.td_margin_k` eşik karşılaştırmasıdır ve taban penceresinde de üretilebilirler
> (`libs/panoalgo/panoalgo/limits.py:257-263`; aynı ayrımın modül notu `limits.py:19-22`).
> Yani ilk 7 günde bir yoğuşma uyarısı
> görmek **beklenen** davranıştır, kurulum hatası değildir. Bunu burada yazıyoruz ki saha ekibi
> "L1 kapalı olmalıydı" diye yanlış bir arıza kaydı açmasın.

---

## 11. Saha arıza modu — modül ölürse ne olur

| Soru | Cevap | Dayanak |
|---|---|---|
| Merkez bunu nasıl anlar? | Alarm zamanlayıcısı (5 sn) her panonun son mesajından beri geçen süreyi `heartbeat_timeout_min` = **5 dk** ile karşılaştırır; aşan pano için `ALM-COMMS-LOST` (SYS) açılır, gerekçesi `last_rx_age_min`, önerisi `HYP-SELF-FAULT` ("arıza alarmı değil"). Veri gelince histerezisle kapanır | `docs/06:158-163`; `contracts/alarm-codes.yaml:210-215`; `backend/app/alarm_service.py:46` |
| Kenar "öldüğünü" kendi söyleyebilir mi? | **Hayır** — kenar merkeze ulaşamadığını merkeze bildiremez; bu alarm **yalnızca merkezde** üretilir. Besleme kesilmesi ayrı bir olaydır: süperkapasitörle `ALM-LASTGASP` (P2) gönderilir | `docs/06:160`; `contracts/alarm-codes.yaml` (bit 20); `docs/13` §2 |
| Sessizlik mi, kesinti mi? | Aynı fiderde eş zamanlı susan panolar tek kesinti olayına bağlanır; alt alarmlar (`ALM-LASTGASP`, `ALM-COMMS-LOST`) **bastırılmaz**, üretilmeye devam eder | `contracts/changes/2026-09-18-kesinti-bagintisi.md:20, 39`; `contracts/openapi.yaml:626` |
| Hiç veri göndermemiş veya bakım modundaki pano? | Alarm üretmez — devreye alınmamış pano ve teknisyenin kapattığı pano yanlış alarm doğurmaz | `docs/06:163` |
| **Pano korumasız kalır mı?** | **HAYIR.** TVOC-2 ark koruması panonun kendi cihazıdır ve bağımsız çalışır; biz onu yalnızca **okuruz** (`arc_mirror`, `access: read_only`), koruma devresine yazma yoktur (GK6) | `contracts/modbus-map.yaml:136`; `PLAN.md:28`; `docs/19:57`; `docs/18:67` |
| Ne **kaybedilir**? | (i) Sıcaklık/ortam izleme ve L0/L1 tespiti durur; (ii) koruma **sağlığının raporlanması** durur — `ALM-PROT-HEALTH` ("ark koruması dedektör arızası — pano sessizce korumasız") artık üretilemez; (iii) yerel röle çıkışları (siren/flaşör, ısıtıcı/fan) düşer | `docs/06` §9 bit 12; `hardware/pano-beyni/io-tablosu.md:17-18`; `contracts/alarm-codes.yaml:34, 44` |

> **Bu ayrımın önemi:** modülün ölmesi panoyu **korumasız bırakmaz**, ama panonun korumasının
> sağlığını **görünmez** yapar. Yani kayıp bir koruma kaybı değil, bir **görünürlük** kaybıdır.
> Bu cümle bir tasarım sonucudur (GK6); gerçek bir panoda denenmedi.

---

## 12. Bu prosedürün doğrulanmamış tarafı (tek yerde)

| İddia | Durum |
|---|---|
| ≤ 45 dk, 2 kişi | **Hedef.** Sahada ölçülmedi (`docs/19:67`) |
| Prosedürün tamamı | **Hiçbir gerçek panoda uygulanmadı** (`docs/19:59, 67`) |
| §6 FMEA bağları | **İzlenebilirlik**, doğrulama değil. RÖS'ler `docs/07`/`docs/07b`'den alınmıştır, düşürülmemiştir |
| §7 kabul kriterleri | Alan adları ve eşikler koddan/sözleşmeden okundu; **bu maddeler bir sahada koşturulmadı** |
| §8 "pano çalışmaya devam eder" | Tasarım/sözleşme düzeyinde doğru; gerçek panoda denenmedi. §8.1'deki iki koşul (Senaryo C, röle kapsamı) **açık kalemdir** |
| §9 yetkinlik ve KKD | **Depoda dayanak yok**, bilinçli olarak boş bırakıldı |
| §10 ilk 7 gün | Kod davranışı okundu; taban penceresinin sahadaki davranışı ölçülmedi |
| §11 modül ölümü | Merkez tarafı testlidir (`docs/07b:21`); **kenar tarafı ve gerçek pano davranışı ölçülmedi** |
| Sensör montajının panonun kendi ısıl doğrulamasına etkisi | **Ölçülmedi** ve depoda yazılı bir kurulum kuralı **yok** — `docs/19:56`'daki açık kalem burada da açıktır |

---

## 13. Bağlantılı dokümanlar

- [`docs/07-fmea-donanim-saha.md`](07-fmea-donanim-saha.md) — §6'nın kaynağı (satır 1, 2, 3, 9, 10).
- [`docs/07b-fmea-yazilim-sistem.md`](07b-fmea-yazilim-sistem.md) — §6'nın ikinci tablosu (satır 6, 8) ve §11'in merkez tarafı.
- [`docs/03-modbus-haritasi.md`](03-modbus-haritasi.md) §2 — Senaryo A/B/C; §8 — yazma güvenliği ve komut bloğu.
- [`docs/06-alarm-matrisi.md`](06-alarm-matrisi.md) §7, §9 — `ALM-COMMS-LOST`, alarm kataloğu ve öncelik politikası.
- [`docs/13-donanim-tasarimi.md`](13-donanim-tasarimi.md) §2, §4 — son nefes hesabı ve yalıtım koordinasyonu.
- [`docs/19-tedas-sartname-uyumu.md`](19-tedas-sartname-uyumu.md) — madde 5.3, 2.2.8.1.iv, 2.2.12, 2.2.3 ve bu prosedürün şartname karşılığı.
- [`hardware/pano-beyni/io-tablosu.md`](../hardware/pano-beyni/io-tablosu.md) — konnektörler, röle çıkışları, AT girişi kuralı.
- [`contracts/modbus-map.yaml`](../contracts/modbus-map.yaml) — `health`, `arc_mirror`, `electrical_mirror`, `command` blokları (**DONMUŞ**).
