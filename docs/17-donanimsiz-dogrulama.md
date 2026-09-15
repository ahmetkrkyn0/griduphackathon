# 17 — Donanım Olmadan Neyi, Nasıl Kanıtladık?

> **Sahip:** Kişi B · **Kapsam:** üç kulvarın kanıtları tek yerde (PLAN.md Bölüm C, GK3).
> Kulvar sahipleri kanıtlarını sohbette iletir, bu dosyayı yalnızca B düzenler (PLAN.md kural 2). **Son güncelleme: 15 Eylül 2026.**
> Üç kulvar `main`'de birleşti; A ve C'nin kanıtları ölçülüp aşağıya işlendi. Hâlâ açık olan tek tek §6'dadır.

**Dürüstlük kuralı.** Sunumda ve README'de "simüle edildi" olan her şey açıkça simüle edildi yazılır. Jüri kandırıldığını anlarsa her şey
çöker; bilinçli bir mühendislik seçimi olduğunu görürse puan kazanırız.

## 1. Neden donanımsız?

Donanım satın alınmadı (PLAN.md GK3). Bu bir eksiklik değil, üç gerekçesi olan bir karardır:

1. **Arıza gösterilebilirliği.** Gevşeyen bir bağlantı 7–30 günde bozulur. Masadaki bir ısıtıcı bunu gösteremez; fizik modeli
   (`τ·dΔT/dt + ΔT = K·I²`) altı günlük bozulmayı dakikalar içinde ve **etiketli** olarak oynatır. Tespit başarısı böylece ölçülebilir.
2. **Ürün, geliştirme kartı değildir.** Rapor §5: breadboard ve geliştirme kartı sunmak puan kaybettirir. Üretilebilir bir ürün tasarımı
   (şema, BOM, yerleşim, FMEA) sahaya daha yakındır.
3. **Merkez yazılımı donanımdan bağımsız olarak gerçektir.** Broker, veritabanı, alarm yöneticisi, SMS sürücüsü ve Modbus ağ geçidi sahada
   da aynı koddur; değişen tek şey veriyi üreten uçtur.

## 2. Ne simüle edildi, ne gerçek?

| Bileşen | Sahada | Bu teslimde | Ne kadar gerçek | Kanıt | Kulvar / durum |
|---|---|---|---|---|---|
| Bağlantı sıcaklık düğümleri, ortam düğümleri | Kablosuz sensörler | Fizik tabanlı veri üreteci (`libs/panoalgo`) | Simülasyon; ısıl model ve arıza enjeksiyonu denklemle savunulur | `docs/14`, `docs/05`, 331 test | A · ✅ |
| MPR-53CS, TVOC-2 | Gerçek cihazlar | Register simülatörleri (kılavuzdaki adresler) | Protokol ve adresler gerçek, ölçüm simülasyon | Canlı yığında CT=500 ve L1 akımı; TVOC-2 ID 248 sessizliği ham soketle ölçüldü | A · ✅ |
| Pano Beyni firmware'i | MCU | Taşınabilir C çekirdeği, host ikilisi | Kod gerçek, **hedef donanımda çalıştırılmadı** | `ctest` 5/5 (`double` + `float`), C ↔ Python farkı K 1,36e-8 / τ 1,42e-8 (eşik 1e-6) | A · ✅ (kapsam sınırı: DH2) |
| Pano Beyni donanımı | Özel PCB | Blok diyagram, I/O tablosu, BOM, yerleşim, mekanik (`.scad`) | Üretime verilebilir tasarım, üretilmedi | `hardware/`, `docs/13` | C · ✅ (KiCad yerine üçlü: §6) |
| Hücresel hat | LTE, özel APN | Tek makinede yerel ağ | Simülasyon; gecikme ve kopukluk yok | docs/09 §8 | B · bilinen sınır |
| MQTT broker, ingest, TimescaleDB | Merkez sunucu | **Aynısı** (`docker compose`) | **Gerçek** | 1.000 pano yük testi (docs/09) | B · ✅ |
| Risk açıklaması + ISA-18.2 alarm yöneticisi | Merkez | **Aynısı** | **Gerçek** | `test_alarm_manager`, `test_risk`, `test_api_alarms` | B · ✅ |
| GSM modem (SMS, arama) | USB modem veya terminal sunucusu | Sanal modem (`scripts/virtual_gsm_modem.py`) | **Sürücü gerçek** (AT komutları, PDU); modem simülasyon. Gerçek modemde yalnızca `SMS_DEVICE` değişir | AT kaydı + PDU dökümü (`deploy/runtime/sms-log.txt`), `test_sms_modem` | B · ✅ |
| WhatsApp | Meta Cloud API | Gerçek API istemcisi | **Gerçek**; telefona teslim için Meta test numarası ve token gerekir | `test_whatsapp`, `test_notifier` | B · istemci ✅, **gerçek telefona teslim bekliyor** (token: Ahmet) |
| SCADA / RTU | Dağıtım SCADA'sı | QModMaster / pymodbus istemcisi; IEC 104 için bağımsız test istemcisi | **Ağ geçidi gerçek** (Modbus TCP + IEC 60870-5-104), istemci test aracı | docs/03 §14, docs/04 §8, `test_scada_*`, `test_iec104_*` | B · ✅ |
| 1.000–10.000 pano filosu | Saha | `loadtest/fleet.py` → **A'nın fizik üreteci** (`--generator physics`, varsayılan) | Platform yükü gerçek, **değerler de artık fiziksel** | docs/09, `test_loadtest_physics` | B · ✅ |
| Operasyon arayüzü | Kontrol odası | React arayüzü (9 ekranın 7'si) | **Gerçek** | `frontend/` 71 test, `docs/16`; 7 ekran gerçek API'de 0 konsol hatası | C · ✅ |

## 3. Beş hamle — durum ve kanıt

### DH1 — Üretilebilir donanım tasarımı (Kişi C) · **✅, bir sapmayla**

| Kanıt | Durum |
|---|---|
| Gerçek parça numaralarıyla tasarım, **geliştirme kartı yok** | ✅ `hardware/pano-beyni/bom.csv` (adet 1 ve adet 1.000) |
| I/O tablosu ve güç bütçesi | ✅ `hardware/pano-beyni/io-tablosu.md`, `docs/13` |
| EK-II/14 üzerinde yerleşim | ✅ `hardware/yerlesim/` (SVG) |
| Clearance/creepage ve manyetik alan hesabı | ✅ `docs/13` |
| DIN kutu mekaniği | ✅ `hardware/mekanik/din-kutu.scad` — **STL üretilmedi** (OpenSCAD kurulu bir makinede `openscad -o din-kutu.stl din-kutu.scad` yeterli) |
| **KiCad şeması (PDF)** | ❌ **Çizilmedi.** MoSCoW'da *Must*'tı; yerine blok diyagram + I/O tablosu + BOM üçlüsü seçildi. Gerekçe `hardware/pano-beyni/README.md`'de; sunumda bilinçli sapma olarak söylenir (§6). |

### DH2 — Firmware gerçekten koşuyor (Kişi A) · **✅, kapsamı daraltılmış**

| Kanıt | Durum |
|---|---|
| `ctest` yeşil | ✅ 5/5 `double`, 5/5 `-DPANO_USE_FLOAT=ON`; `-Wall -Wextra -Wpedantic` uyarısız (Ubuntu 24.04 / gcc 13.3) |
| C ve Python RLS aynı test vektöründe ≤ 1e-6 | ✅ **K 1,36e-8 · τ 1,42e-8** (`data/fixtures/rls_vectors.csv`, `firmware/akis-diyagramlari/ana-dongu.md`) |
| `malloc` yok, sabit bellek | ✅ — ama nokta başına **320 B** (hedef 48 B); sapma gerekçesi `docs/13` |
| Akış diyagramları | ✅ `firmware/akis-diyagramlari/` |
| `panobeyni-sim`: Modbus master döngüsü + MQTT yayını | ✅ `sim/panobeyni_sim.py` (15 Eylül). MPR-53CS ve TVOC-2 simülatörlerinden **gerçek Modbus TCP** ile okur (CT oranını cihazın 0x8001 register'ından öğrenir), kenar boru hattından geçirir, MQTT'ye yayınlar. 12 test, sahte Modbus yok: testler gerçek cihaz simülatörlerini alt süreç olarak kaldırır. **Ölçülen:** `--trip-after` ile üretilen gerçek bir ark tripi artık `ALM-ARC-TRIP` olarak yayına çıkıyor; 14 Eylül'e kadar depoda hiçbir Modbus **istemcisi** yoktu ve bu olay hiçbir yere akmıyordu. |
| Halka tampon (broker yokken biriktirme) | ✅ `RingBuffer`; dolunca **en eski** düşer ve sayılır, `health.buffered` alanı bekleyeni bildirir |
| **Sanal SERİ port üzerinden Modbus** | ❌ TCP kullanılıyor. Sahada RS485; değişen ağ geçidi, protokol çerçevesi aynı. |
| **Kenarda Modbus SLAVE sunumu** | ❌ Kenarda yapılmıyor. Aynı harita merkezde sunuluyor (`backend/app/scada/`, :502), sözleşmesi `contracts/modbus-map.yaml`. |
| Taşıma katmanı C değil Python | ⚠️ Bilinçli: kanıtlanmak istenen "kenarda ve merkezde aynı algoritma"dır ve o C'de doğrulanmıştır (yukarıdaki 1,4e-8 satırı). C'de sıfırdan MQTT/Modbus yığını yazmak buna bir şey katmazdı. |
| Renode / Wokwi üzerinde MCU emülasyonu | ❌ Atlandı (MoSCoW *Should*) |

**B'nin bu hamleye katkısı hazır:** firmware'in sunacağı Modbus haritası (`contracts/modbus-map.yaml`) merkezde birebir çalışıyor. Aynı adresler,
aynı kodlama kuralları, aynı "yok" değerleri (docs/03 §5). Firmware bu tabloyu sözleşmeden üretecek; merkezle ayrışamaz.

### DH3 — Fizik motoru, rastgele sayı değil (Kişi A) · **✅**

| Kanıt | Durum |
|---|---|
| Isıl model ve yük profili | ✅ `docs/14` (τ·dΔT/dt + ΔT = K·I², saat-of-hafta profili × mevsim × AR(1)) |
| Lag-1 otokorelasyon > 0,9 (verilen Excel'in 0,00'ına karşı) | ✅ `libs/panoalgo/tests/test_generator.py` |
| **S1'de L1 katmanı, sabit 70 K eşiğinden en az 48 saat önce uyarıyor** | ✅ **209 saat (8,7 gün)** — kriterin dört katından fazla. İlk L1 tespiti 13 Tem 22:15, 70 K ihlali 22 Tem 15:15 (`docs/12` §2) |
| Duyarlılık (recall) | ✅ **1,00** — beklenen alarmı olan 8 senaryonun hepsinde; S0 ve S6'da beklenen alarm yoktur (S6'nınkini merkez üretir) |
| Yasaklı alarm (`not_expect`) | ✅ 10 senaryonun hiçbirinde çıkmadı — ör. S2 aşırı yükte `ALM-K-ALM` yok |
| Yanlış alarm tabanı (S0 normal gün) | ✅ **71,4** alarm/100 pano/gün (sözleşme sınırı 150). Ağırlıklı olarak çiy noktası uyarıları — sıfır değildir ve sunumda böyle söylenir. |
| `docs/12` elle yazılmadı, betikle üretilir | ✅ `python scripts/validate.py --out docs/12-...md` → birebir aynı dosya |
| 10 senaryonun fixture'ları aynı tohumla yeniden üretilebilir | ✅ 20 dosyanın 20'si bayt bayt aynı |

**B'nin bu hamleye katkısı bağlandı:** merkez dedektör (`panoalgo.central.CentralDetector`) artık
`main.py`'de gerçekten kurulu (TB2 Adım 4 kapandı). Bağlanır bağlanmaz iş gördü: B'nin elle yazdığı
test yükünde kenarın bildirmediği **iki gerçek eşik ihlali** buldu (GİRİŞ_L2 diğer iki fazdan 37 K
sıcak — sınır 4 K; `ttl_h` 150,5 saat — sınır 336). Kanıt: `backend/tests/test_central_detector.py`.

**B'nin bu hamleye katkısı hazır:** kenar tespitinin sonucu merkezde açıklanıyor ve yönetiliyor (Neden / Ne yapmalı / Ne kadar acil). Merkez
dedektör kancası (`CentralDetector`) `panoalgo` gelince yalnızca bağlanacak; TB2 Adım 4.

### DH4 — Gerçek protokol, gerçek adresler (Kişi A + B) · **✅**

| Kanıt | Durum |
|---|---|
| Merkezde Modbus TCP 502: her pano bir birim, kenardakiyle aynı harita; FC01/02/03/04/06/16 | ✅ 35 protokol testi (pymodbus istemcisi + elle kurulmuş ham çerçeveler), mutasyon 19/19 |
| Canlı yığında PC'den okuma: 3 panoda `conn_temp` = arayüzün gördüğü değer × 10 | ✅ 13 Eylül |
| Koruma cihazına yazma yok: TVOC-2 aynasına yazma **doğru şifreyle bile** 0x02 | ✅ `test_scada_gateway`, 13 Eylül canlı |
| Harita dokümanı ve Excel tablosu sözleşmeden üretilir, elle yazılmaz | ✅ `docs/03`, `test_gen_modbus_doc` |
| Merkezde IEC 60870-5-104 kontrollü istasyon (2404): genel sorgulama, yayın adresi, saat senkronu, zaman etiketli kendiliğinden gönderim, t1/t2/t3, k/w | ✅ 72 test (elle kurulmuş çerçeveler), mutasyon 37/37 · kodek 12/12 · nokta planı 9/9 |
| Canlı yığında bağımsız IEC 104 istemcisi: IEC 104 = REST API (87 kontrol) = Modbus FC03 (139 adres) | ✅ 13 Eylül, **0 fark**; ilk koşu yayın sorgusunda standart dışı cevabı yakaladı, düzeltildi (`docs/04` §8) |
| MPR-53CS ve TVOC-2 simülatörleri kılavuz adreslerinde; CT = 500 dönüşümü ve L1 akımı | ✅ canlı yığında okundu (`mpr-sim` :5020) |
| **TVOC-2 fabrika ID 248'de sessiz, 1–247'de cevap veriyor** | ✅ ham Modbus TCP çerçevesiyle ölçüldü (`sim/tests/test_tvoc2_server.py`). **Düzeltme geçmişi:** 14 Eylül'e kadar bu satır doğrulanmamıştı ve **yanlıştı** — pymodbus varsayılanı bilinmeyen birim için `0x8B` / kod 11 (Gateway Target Device Failed To Respond) döndürüyordu, yani cihaz "sessiz" değil "hata veren"di. `ignore_missing_slaves=True` ile düzeltildi; test düzeltmeden önce kırmızı olduğu doğrulanarak yazıldı. |
| Merkezde Modbus TCP = arayüz: `conn_temp` 25 noktanın tamamında API değeri × 10 | ✅ canlı yığın, **fark 0** |

Jüri demosu (QModMaster adımları): docs/03 §11.

### DH5 — Bildirim gerçekten telefona düşüyor (Kişi B) · **SMS yolu ✅, gerçek telefona WhatsApp bekliyor**

| Kanıt | Durum |
|---|---|
| SMS sürücüsü üretim sürücüsü: AT komutları, **PDU modu** (3GPP TS 23.040), birleşik SMS, kopuk oturumu ESC ile toparlama | ✅ `test_pdu`, `test_sms_modem` |
| Sanal modem gerçek modem kadar katı: uzunluğu tutmayan PDU'yu `+CMS ERROR: 304` ile reddeder | ✅ `test_sms_modem::test_virtual_modem_rejects_a_pdu_whose_length_does_not_match` |
| AT komut kaydı ve PDU dökümü; PDU'lar herhangi bir çevrimiçi çözücüyle doğrulanabilir | ✅ `deploy/runtime/sms-log.txt` (git dışı, numara içerir) |
| Uçtan uca ölçüm: sensör zamanından modemin SMS'i kabulüne p95 **606 ms** (1.000 pano yükü altında) | ✅ docs/09 §4.3 |
| Çift yönlü onay: "1 <alarm no>" yanıtı alarmı onaylar; kayıtsız numara yok sayılır | ✅ `test_notifier`, canlı yığın (docs/06 §10) |
| P1'de 5. dakikada arama, 15. dakikada üst amire eskalasyon | ✅ canlı yığın (docs/06 §10) |
| WhatsApp Cloud API istemcisi: şablon/serbest metin, geçici hatada tekrar, kalıcı hatada tek kayıt | ✅ `test_whatsapp`, `test_notifier` |
| **Gerçek bir telefona WhatsApp mesajı** | **bekliyor:** Meta test numarası + token + doğrulanmış alıcı (Ahmet). İnternet yoksa demo SMS yolu ve AT kaydıyla sürer |

## 4. B kulvarının kanıt özeti

| Alan | Otomatik test | Mutasyon denetimi | Canlı / ölçüm |
|---|---|---|---|
| Ingest, veritabanı, API | ✅ (gerçek TimescaleDB entegrasyon testleri dahil) | — | 1.000 pano: görünme p95 657 ms, kayıp 0 |
| Alarm yöneticisi + bildirim | ✅ | TB2'de 107 mutasyonun tamamı | P1/P2 SMS, eskalasyon, SMS onayı |
| Modbus TCP ağ geçidi | 35 + 61 + 9 | 19/19 · 35/35 · kodlayıcı 28/28 | Modbus = API; GK6 yazma reddi |
| IEC 60870-5-104 istasyonu | 30 + 24 + 12 + 3 + 3 | 37/37 · 12/12 · 9/9 | IEC 104 = API = Modbus, 0 fark; komut reddi |
| Analiz uçları (seri, kara kutu, KPI) | 25 + 4 (gerçek DB) | 20/20 | Seri ve KPI canlı veriden |
| Yük, depolama, sıkıştırma | 12 + 5 + 2 (gerçek DB) | 5/5 | 100 → 10.000 pano; sıkıştırma 48× |
| Grafana panoları | Her panel sorgusu gerçek DB'de | 4/4 | Paneller canlı veriyle |
| Temiz veritabanı kurulumu | `initdb` 001–005 boş DB'de, 23 gerçek DB testi o DB'de | — | 13 Eylül |

Toplam: `TEST_DB_DSN` ile **605 test** (580 + merkez dedektör bağlantısı ve fizik üreteci için 25 yeni test).

### 4.1 Üç kulvarın test sayıları (15 Eylül, `main` üzerinde)

| Katman | Nasıl koşulur | Sonuç |
|---|---|---|
| `libs/panoalgo` (A) | `cd libs/panoalgo && pytest` | **331 / 331** |
| Firmware C çekirdeği (A) | `cmake -S firmware -B b && cmake --build b && ctest --test-dir b` | `double` **5/5**, `float` **5/5** |
| `sim/` (A) | `cd sim && pytest` | **21 / 21** |
| Backend (B) | `cd backend && pytest` | **583 / 583** (+22 gerçek TimescaleDB testi `TEST_DB_DSN` ile) |
| Frontend (C) | `npm ci && npm test && npm run build` | **71 / 71**, `tsc` + `vite build` başarılı |

### 4.2 Birleşmeden sonra canlı yığında ölçülenler

- `panosim` → mosquitto → ingest → TimescaleDB: **karantina 0**, panolar API'de görünüyor,
  kenar alanları (`k_ratio`, `risk`, `q`) pano detayına ulaşıyor.
- Modbus TCP :502 — `conn_temp` 25 noktanın tamamında API değeri × 10, **fark 0**.
- IEC 104 :2404 — STARTDT act → con.
- Frontend `nginx` üzerinden API ve WebSocket'e ulaşıyor (101 Switching Protocols).
- 7 ekran gerçek API ile Playwright'ta gezildi: **0 konsol hatası / uyarısı**.
- Duman testi 16 kontrolün 16'sı geçti (TVOC-2 ID 248 kontrolü düzeltmeden sonra yeşil).
- Git hijyeni: index'te 0 CRLF; izlenen dosyalarda gerçek sır yok (yalnızca testlerdeki
  sahte `+90555000000x` numaraları).

## 5. Jüri soruları — ölçümle güncellenmiş cevaplar (B)

Rapor §13 soru bankasındaki entegrasyon, ölçek ve güvenlik soruları (PLAN.md T5.4: B). Rapordaki tahmini cevaplar ölçümle değişti.

| # | Soru | Cevap (kanıtıyla) |
|---|---|---|
| 5 | Mevcut SCADA'ya nasıl bağlanıyor? | Merkezden **Modbus TCP 502** çalışıyor: her pano bir birim, kenardaki haritanın aynısı, varsayılan salt okunur (docs/03). Sahada RTU'ya Pano Beyni'nin Modbus slave portu (A). Tek master kısıtı için üç kurulum senaryosu (docs/03 §2). Aynı veri **IEC 60870-5-104 (TCP 2404)** kontrollü istasyon olarak da sunuluyor: genel sorgulama, zaman etiketli kendiliğinden gönderim, salt okunur (docs/04); canlıda IEC 104 = API = Modbus, 0 fark. |
| 6 | "Public cloud yok" dediniz; WhatsApp? | Birincil kanal tamamen yurt içi **GSM SMS**'tir ve sürücüsü üretim sürücüsüdür. WhatsApp ikincil ve kapatılabilir; mesajda yalnızca saha kodu, öncelik ve tek satır var. Alıcı numarası Meta'ya gittiği için açılması KVKK birimi kararına bağlı (docs/15 §4.2). |
| 12 | 10.000 panoya nasıl ölçeklenir? | **Ölçtük:** tek backend süreci 5.000 panoya kadar görünme p95 < 1 s; 10.000'de veri kaybetmeden doyuyor ve darboğaz ölçüldü (şema doğrulaması). Kaldıraçlar: 60 s raporlama (mesaj hızı ÷6) ve paylaşımlı abonelikle çoklu ingest. Depolama: sıkıştırma 48× **ölçüldü ve açık**; 100 pano 10 s'de ~105 GB/yıl, 60 s'de ~17 GB/yıl (docs/09). |
| 13 | Siber güvenlik? | Kodda olanlar: sözleşme dışı veri karantinası, pano kimliği denetimi, Modbus IP listesi + salt okunur varsayılan + koruma cihazına yazma yasağı + kaba kuvvet kilidi, denetim izi (docs/15). Tasarımda olanlar: cihaz sertifikası, mTLS, imzalı OTA (A/C). **Demo yığınında broker anonim ve API'de kimlik doğrulama yok**; üretim farkları listelendi (docs/15 §5). |
| 14 | Veri nerede, KVKK? | Tamamı şirket veri merkezinde. Telefon numaraları yalnızca yapılandırmada; veritabanında ve kayıtta **maskeli**. Disk şifreleme ve saklama süresi politikası yol haritasında (docs/15 §4.3). |
| 7 | TVOC-2 arkı zaten kesiyor; sizin katkınız? | (B tarafı) Koruma sağlığı SCADA'ya ayrı bir coil olarak açılır (`prot_health_ok`); arızalı dedektör P1 alarmı telefonu çaldırır; olay öncesi 72 saatlik kara kutu API'si hazır. **Koruma devresine hiçbir yoldan yazmıyoruz**: ağ geçidi bunu şifreyle bile reddediyor. |

## 6. Açık kalanlar ve bilinçli sapmalar

**Bilinçli sapmalar** — hepsi sunumda açıkça söylenir:

| # | Sapma | Gerekçe |
|---|---|---|
| 1 | KiCad şema PDF'i yok (MoSCoW *Must*) | Blok diyagram + I/O tablosu + BOM üçlüsü seçildi; üretime aynı bilgiyi verir. `hardware/pano-beyni/README.md` |
| 2 | Taşıma kabuğu Python; sanal seri port yerine TCP; kenarda Modbus slave yok | Modbus master döngüsü ve MQTT yayını **yapıldı** (`sim/panobeyni_sim.py`, 12 test); kalan üç fark DH2'de tek tek yazılı. Hesap çekirdeği C'de doğrulandı ve Python ile 1e-8 farkla eşleşiyor. |
| 3 | DIN kutu STL'i üretilmedi | `.scad` kaynağı var; OpenSCAD kurulu bir makinede tek komut |
| 4 | Firmware belleği 48 B yerine 320 B/nokta | `docs/13` |
| 5 | Renode / Wokwi emülasyonu atlandı | MoSCoW *Should* |
| 6 | 9 ekranın 7'si | Mobil PWA ve devreye alma sihirbazı *Won't* |
| 7 | Cihaz Sağlığı ekranı pano başına istek atıyor | 6 eşzamanlı; toplu uç (`fleet/health`) sözleşme değişikliği ister |
| 8 | Bölge haritası il/ilçe yerine ADM/GDZ bazlı | Sözleşmede il/ilçe alanı yok |
| 9 | pymodbus sunucusu yerine kendi Modbus sunucumuz | `docs/03` §13 |
| 10 | Demo yığını kimlik doğrulamasız (broker anonim 1883, API açık, Modbus/IEC 104 düz TCP) | Üretim farkları `docs/15` §5 |
| 11 | S0'da 71,4 yanlış alarm/100 pano/gün | Sözleşme sınırı 150; sıfır değildir, ağırlıklı olarak çiy noktası uyarısıdır |

**Hâlâ açık:**

| Kanıt | Sahip | Hedef |
|---|---|---|
| Gerçek bir telefona WhatsApp teslimi (Meta test numarası + token + doğrulanmış alıcı) | B | M2 |
| Sıfırdan `git clone` ile temiz makine testi (T4.4) | B | M4 (18 Eylül) |
| 1.000 pano yük testinin fizik üreteciyle tekrarı (`docs/09` sayıları şablon üreteçle ölçülmüştü) | B | M4 |
| İki `contracts/changes` önerisinin onayı ya da bilinçli erteleme | A + B + C | 17 Eylül |
| Gerçek yığından (örnek veri değil) ekran görüntüleri | C | M4 |
