# 17 — Donanım Olmadan Neyi, Nasıl Kanıtladık?

> **Sahip:** Kişi B · **Kapsam:** üç kulvarın kanıtları tek yerde (PLAN.md Bölüm C, GK3).
> Kulvar sahipleri kanıtlarını sohbette iletir, bu dosyayı yalnızca B düzenler (PLAN.md kural 2). **Son güncelleme: 16 Eylül 2026.**
> Üç kulvar `main`'de birleşti; A ve C'nin kanıtları ölçülüp aşağıya işlendi.
>
> **İki bölüm tek kaynaktır:** §5 provaya hazır **17 soruluk jüri cevap kartıdır** (her cevabın yanında kanıt dosyası, sayısı
> olmayan soruda düz "ölçmedik"); §6 **"neyi yapmadınız?" sorusunun tek kaynağıdır** — bilinçli sapmalar, hâlâ açık olanlar ve
> aleyhimize çıkan iki ölçüm orada toplanmıştır.

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
| Bağlantı sıcaklık düğümleri, ortam düğümleri | Kablosuz sensörler | Fizik tabanlı veri üreteci (`libs/panoalgo`) | Simülasyon; ısıl model ve arıza enjeksiyonu denklemle savunulur | `docs/14`, `docs/05`, 401 test | A · ✅ |
| MPR-53CS, TVOC-2 | Gerçek cihazlar | Register simülatörleri (kılavuzdaki adresler) | Protokol ve adresler gerçek, ölçüm simülasyon | Canlı yığında CT=500 ve L1 akımı; TVOC-2 ID 248 sessizliği ham soketle ölçüldü | A · ✅ |
| Pano Beyni firmware'i | MCU | Taşınabilir C çekirdeği, host ikilisi | Kod gerçek, **hedef donanımda çalıştırılmadı** | `ctest` 5/5 (`double` + `float`), C ↔ Python farkı K 1,36e-8 / τ 1,42e-8 (eşik 1e-6) | A · ✅ (kapsam sınırı: DH2) |
| Pano Beyni donanımı | Özel PCB | Blok diyagram, I/O tablosu, BOM, yerleşim, mekanik (`.scad`) | Üretime verilebilir tasarım, üretilmedi | `hardware/`, `docs/13` | C · ✅ (KiCad yerine üçlü: §6) |
| Hücresel hat | LTE, özel APN | Tek makinede yerel ağ | Simülasyon; gecikme ve kopukluk yok | docs/09 §8 | B · bilinen sınır |
| MQTT broker, ingest, TimescaleDB | Merkez sunucu | **Aynısı** (`docker compose`) | **Gerçek** | 1.000 pano yük testi (docs/09) | B · ✅ |
| Risk açıklaması + ISA-18.2 alarm yöneticisi | Merkez | **Aynısı** | **Gerçek** | `test_alarm_manager`, `test_risk`, `test_api_alarms` | B · ✅ |
| GSM modem (SMS, arama) | USB modem veya terminal sunucusu | Sanal modem (`scripts/virtual_gsm_modem.py`) | **Sürücü gerçek** (AT komutları, PDU); modem simülasyon. Gerçek modemde yalnızca `SMS_DEVICE` değişir | AT kaydı + PDU dökümü (`deploy/runtime/sms-log.txt`), `test_sms_modem` | B · ✅ |
| WhatsApp | Meta Cloud API | Gerçek API istemcisi | **Gerçek**; telefona teslim için Meta test numarası ve token gerekir | `test_whatsapp`, `test_notifier` | B · istemci ✅, **gerçek telefona teslim bekliyor** (token: Ahmet) |
| SCADA / RTU | Dağıtım SCADA'sı | QModMaster / pymodbus istemcisi; IEC 104 için bağımsız test istemcisi | **Ağ geçidi gerçek** (Modbus TCP + IEC 60870-5-104), istemci test aracı | docs/03 §14, docs/04 §9, `test_scada_*`, `test_iec104_*` | B · ✅ |
| 1.000–10.000 pano filosu | Saha | `loadtest/fleet.py` → **A'nın fizik üreteci** (`--generator physics`, varsayılan) | Platform yükü gerçek, **değerler de artık fiziksel** | docs/09, `test_loadtest_physics` | B · ✅ |
| Operasyon arayüzü | Kontrol odası | React arayüzü (9 ekranın 7'si) | **Gerçek** | `frontend/` 85 test, `docs/16`; 7 ekran gerçek API'de 0 konsol hatası | C · ✅ |

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
| `malloc` yok, sabit bellek | ✅ — ama nokta başına **320 B** (hedef 48 B); sapma gerekçesi `firmware/akis-diyagramlari/ana-dongu.md` §4, özeti §6 satır 4 |
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
sıcak — sınır 4 K; `ttl_h` 150,5 saat — sınır 336). Kenar tespitinin sonucu da merkezde açıklanıyor ve
yönetiliyor (Neden / Ne yapmalı / Ne kadar acil). Kanıt: `backend/tests/test_api_alarms.py` (iki ihlalin
sayıları ve uçtan uca testi: `test_the_central_safety_net_adds_codes_the_edge_missed`) +
`backend/tests/test_central_detector.py` (emniyet ağının kendi testleri, kurulum dahil:
`test_the_application_actually_builds_a_central_detector`).

### DH4 — Gerçek protokol, gerçek adresler (Kişi A + B) · **✅**

| Kanıt | Durum |
|---|---|
| Merkezde Modbus TCP 502: her pano bir birim, kenardakiyle aynı harita; FC01/02/03/04/06/16 | ✅ 35 protokol testi (pymodbus istemcisi + elle kurulmuş ham çerçeveler), mutasyon 19/19 |
| Canlı yığında PC'den okuma: 3 panoda `conn_temp` = arayüzün gördüğü değer × 10 | ✅ 13 Eylül |
| Koruma cihazına yazma yok: TVOC-2 aynasına yazma **doğru şifreyle bile** 0x02 | ✅ `test_scada_gateway`, 13 Eylül canlı |
| Harita dokümanı ve Excel tablosu sözleşmeden üretilir, elle yazılmaz | ✅ `docs/03`, `test_gen_modbus_doc` |
| Merkezde IEC 60870-5-104 kontrollü istasyon (2404): genel sorgulama, yayın adresi, saat senkronu, zaman etiketli kendiliğinden gönderim, t1/t2/t3, k/w | ✅ **74 test** (elle kurulmuş çerçeveler; 16 Eylül'de yeniden toplandı), mutasyon 37/37 · kodek 12/12 · nokta planı 9/9 |
| Canlı yığında bağımsız IEC 104 istemcisi: IEC 104 = REST API (87 kontrol) = Modbus FC03 (139 adres) | ✅ 13 Eylül, **0 fark**; ilk koşu yayın sorgusunda standart dışı cevabı yakaladı, düzeltildi (`docs/04` §9) |
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
| Modbus TCP ağ geçidi | 35 + 61 + 9 + 84 = **189** (protokol · ağ geçidi politikası · uygulama · kodlayıcı) | 19/19 · 35/35 · kodlayıcı 28/28 | Modbus = API; GK6 yazma reddi |
| IEC 60870-5-104 istasyonu | 30 + 24 + 12 + 3 + 5 = **74** (sunucu · kodek · nokta · uygulama · doküman) | 37/37 · 12/12 · 9/9 | IEC 104 = API = Modbus, 0 fark; komut reddi |
| Analiz uçları (seri, kara kutu, KPI) | 26 + 4 (gerçek DB) | 20/20 | Seri ve KPI canlı veriden |
| Yük, depolama, sıkıştırma | 12 + 5 + 2 (gerçek DB) | 5/5 | 100 → 10.000 pano; sıkıştırma 46–48× |
| Grafana panoları | Her panel sorgusu gerçek DB'de | 4/4 | Paneller canlı veriyle |
| Temiz veritabanı kurulumu | `initdb` 001–006 boş DB'de, `pytest -m integration` ile **29** gerçek DB testi o DB'de | — | 13 Eylül ölçümü; 16 Eylül'de `006_demo_seed.sql` ve 6 test eklendi, sayı yeniden toplandı |

Toplam: `TEST_DB_DSN` ile **661 test** (gerçek TimescaleDB entegrasyon testleri dahil; 16 Eylül'de yeniden ölçüldü).

### 4.1 Üç kulvarın test sayıları (16 Eylül 2026'da yeniden ölçüldü)

| Katman | Nasıl koşulur | Sonuç |
|---|---|---|
| `libs/panoalgo` (A) | `cd libs/panoalgo && pytest` | **401 / 401** |
| Firmware C çekirdeği (A) | `cmake -S firmware -B b && cmake --build b && ctest --test-dir b` | `double` **5/5**, `float` **5/5** |
| `sim/` (A) | `cd sim && ../backend/.venv/Scripts/python -m pytest tests` | **33 / 33** (16 Eylül'de yeniden koşuldu, 72,7 s). `sim/` kendi sanal ortamına sahip değil; backend'in ortamıyla koşar. Eski 21 sayısı 15 Eylül ölçümüydü ve **eskimiştir** |
| Backend (B) | `cd backend && pytest` | **661 / 661** (`TEST_DB_DSN` verildiğinde; gerçek TimescaleDB testleri dahil) |
| Frontend (C) | `npm ci && npm test && npm run build` | **85 / 85**, `tsc --noEmit` **0 hata** |

> Bu tablodaki sayılar 15 Eylül'e göre arttı (panoalgo 331 → 401, backend 583 → 661, frontend 71 → 85).
> `README.md` ve depodaki bazı özet metinler hâlâ eski sayıları taşıyorsa doğru kaynak bu tablodur.

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

## 5. Jüri cevap kartı — 17 soru, her cevabın yanında kanıt dosyası

Provanın (KALAN-EKSIKLER O2) tek hazırlık artefaktı budur. Rapor §13'teki soru bankası tahmini cevaplarla yazılmıştı;
aşağıdaki sürüm **ölçülmüş sayılarla** yeniden yazıldı ve fizik/saha/maliyet/UX tarafı da eklendi.

**Kartın kuralları:**

- **Numaralar bu kartın kendi numaralarıdır.** Rapor §13 soru bankasındaki karşılığı olan sorularda parantez içinde
  (`rapor §13 #n`) verilir.
- **Her cevapta kanıt dosyası adı vardır.** Kanıtı olmayan cümle karta girmez.
- **Ölçmediğimiz yere düz "ölçmedik" yazılır** (7 ve 9. satırlarda geçiyor; 11. satırda ise bir ölçüm boşluğu değil **bilinçli
  bir kapsam kararı** yazılıdır: rakip ürünlerin fiyatı karşılaştırılmadı, birim maliyetleri ölçülmedi). Tahmin edilen sayı "tasarım hedefi" diye
  işaretlenir; "karşılıyoruz" denmez (GK3).
- **Kim cevaplar:** 1–6 fizik ve tespit → A · 7–11 saha, maliyet, UX, konumlandırma → C · 12–17 entegrasyon, ölçek, güvenlik → B.
- Rapor §13 #2'nin cevabında duran `[demo sonucunu yazın]` yer tutucusu **3. satırda ölçülmüş sayıyla kapatılmıştır**
  (rapor bir analiz belgesidir; ölçümün kaynağı `docs/12` §3'tür).

| # | Soru | Cevap (ölçülmüş sayı + kanıt dosyası) |
|---|---|---|
| 1 | Neden yapay zekâ değil de fizik tabanlı model; "K/K₀" tam olarak nedir? *(rapor §13 #1)* | Sahada etiketli arıza verisi yok, komitenin verdiği örnek veri de rastgele (lag-1 otokorelasyonu 0,00; bizim üretecimizde > 0,9 — `libs/panoalgo/tests/test_generator.py`). Model tek denklem: `τ·dΔT/dt + ΔT = K·I²`. **K** ısıl direnç indeksidir (sıcaklık artışının akım karesine oranı); her nokta için **unutma faktörlü RLS** ile çevrimiçi kestirilir — `numpy` yok, 2×2 cebir elle açık, çünkü aynı çekirdek MCU'da koşmalı (`panoalgo/detect.py` → `firmware/core/rls.c`). **K₀** devreye almadan sonraki **7 günlük medyan** tabandır (ortalama değil: tek sıçrama tabanı bozar); taban donmadan `k_ratio` 1,0 döner, yani devreye alma günü alarm yağmuru olmaz. Alarm orana bakar: 1,3 uyarı (P3), 1,6 alarm (P2). Ölçülen isabet: tekil K hatası %2,0–2,4 iken **K/K₀ hatası %0,31** — sistematik sapma pay ve paydada birbirini götürür. Kanıt: `docs/05` §3, `docs/14`, `libs/panoalgo` 401/401 test. |
| 2 | Tespit başarınız ne kadar? | 10 etiketli senaryoda **duyarlılık (recall) 1,00** — beklenen alarmı olan 8 senaryonun 8'inde; **yasaklı alarm (`not_expect`) 10 senaryonun hiçbirinde çıkmadı** (ör. aşırı yükte `ALM-K-ALM` yok). Sabit 70 K eşiğine karşı öne alma: gevşek bağlantıda (S1) **209,0 saat = 8,7 gün**; aşırı yükte (S2) yalnızca **1,2 saat** — ve bu doğru sonuçtur, çünkü orada sebep bozulma değil yüktür, fizik katmanının üstünlüğü olmamalıdır. Kanıt: `docs/12` §1–§2; dosya elle yazılmaz, `python scripts/validate.py` üretir. **Sınır:** senaryolar sentetik ve etiketli; saha doğrulaması yok (GK3). |
| 3 | **Yanlış alarm oranınız ne?** *(rapor §13 #2)* | **71,4 alarm / 100 pano / gün** — sağlıklı senaryoda (`S0_normal`, geçiş mevsimi) ölçüldü. Sözleşme hedefi günde 150, üst sınır 300; yani sınırın içindeyiz ama **sıfır değil** ve sunumda böyle söylüyoruz. Çıkan kodların **tamamı** çiy noktası (`ALM-DEW-ALM` / `ALM-DEW-WARN`): ısıl tespit katmanı bu yükün hiçbirini üretmiyor. Ölçüm tanımı bize karşı cömerttir — kesintisiz aralık tek olay sayılır, ama `S0`'ın hiç etiketi olmadığı için fiziksel olarak **doğru** olan çevresel alarmlar da "yanlış" hanesine yazılır. Kanıt: `docs/12` §3, `docs/05` §11.6. |
| 4 | Öyleyse eşiği kısın — çiy alarmı çok fazla değil mi? | Kısmayı **ölçtük, yükü artırıyor**: (uyarı 1,0 / alarm 0,0) çifti **171,4**, (0,5 / 0,0) **228,6** olay/100 pano-gün — dar eşik, ayakta duran tek bir alarmı kesik kesik (chattering) bir alarm dizisine çeviriyor ve 150 bütçesini aşıyor. Gevşetmek sayıyı 28,6'ya düşürüyor ama alarmı haftanın %100'ünde ayakta bırakıyor: EEMUA 191'in **bayat alarm** patolojisi. Asıl sürücü eşik değil hava: aynı sağlıklı senaryo, **eşik sabit** — kış **28,6** · geçiş **71,4** · **yaz 0,0** (yazda çiy marjı medyan +10,17 K). Bu yüzden canlı demoda S0 yaz günü oynatılır (`demo/senaryo/s0.sh --season yaz`) ve sağlıklı panodan çiy alarmı çıkmaz; **eşik değiştirilmedi, sözleşme değişikliği önerilmedi**. Kanıt: `scripts/threshold_sweep.py --verify --seasons`, `docs/05` §11. |
| 5 | "Şu kadar saat ömrü kaldı" diyorsunuz; bu tahmin ne kadar güvenilir? | **Geri testini yaptık ve kötü çıktı; saklamıyoruz.** S1'de üretilen **790 tahminin yalnızca %5,2'si** ±%20 konisinin içinde; **prognostic horizon YOK** (tahmin hiçbir andan sonra konide kalmıyor); ortalama göreli doğruluk **−5,12**; ihlale 48 saatten az kala koni içinde kalma **%0**. S2'de hiç tahmin üretilmedi. S8'de sınır hiç aşılmadığı hâlde **99 tahmin** çıktı ve **89'u** `ALM-TTL-14D` alarmına döndü — bu bir **prognoz yanlış-alarmıdır** ve §3'teki sayaç onu görmez. Sonuç **tek yörüngeden** gelir (n = 1), **güven aralığı yoktur**. Cümlemiz şudur: **`ttl_h` bir yön göstergesidir, takvim değildir**; manşetteki 209 saat **tespit** katmanından (K/K₀ eşiği) gelir, bu tahminden değil — ikisi karıştırılmamalıdır. Kanıt: `docs/12` §4, `docs/05` §10, ölçüt tanımları `libs/panoalgo/panoalgo/prognostics.py`. |
| 6 | AG panoda kısmi deşarj neden yok — dosya paketinde HFCT veri sayfaları vardı? | AG panoda **sürekli ve yinelenen PD aktivitesi tipik olarak raporlanmaz**; ama gerekçeyi doğru kurmak gerekir. Sık tekrarlanan "havada Paschen minimumu ≈ 327 V, dolayısıyla 400 V'ta PD olmaz" kısayolunu **kullanmıyoruz**: 400 V sistemde faz-faz tepe gerilimi √2 × 400 ≈ 566 V'tur, yani 327 V'un **üstündedir** — salt gerilim eşiği bu sonucu vermez. Doğru gerekçe **geometriktir**: Paschen eğrisi gerilimi değil **basınç × boşluk mesafesi** çarpımını sınırlar ve AG panoda beklenen boşluk boyutlarında tek darbenin taşıdığı enerji, OG/YG'de ölçülen türden sürekli bir PD aktivitesi üretecek düzeyde değildir. **Bu bir literatür/akıl yürütme kabulüdür, bizim ölçümümüz değildir — AG panoda PD ölçümü yapılmadı** ve kabul depoda hiçbir veriyle sınanmadı. Telemetri şemasında `pd` bloğu AG için `null`. Asıl dürüst cevap bundan daha ağırdır: tüm tespit zincirimiz **10 saniyelik skaler** değerler üzerine kuruludur, dolayısıyla **bugünkü mimari seri arkı ve kontak kıvılcımlanmasını dalga biçimi düzeyinde göremez**. "Yapabiliriz" demiyoruz; tetikli dalga biçimi yakalama bir sonraki donanım revizyonunun konusudur. Kanıt: `docs/13` §7.1 (gerekçenin tam kuruluşu ve "bizim ölçümümüz değildir" kaydı orada), `docs/11` "Kapsanmayan standartlar", `docs/05` §10. **Not:** `docs/05` §10 16 Eylül'de bu gerekçeye göre düzeltildi. `HACKATHON_ANALIZ_RAPORU.md` (15 Eylül tarihli analiz belgesi) §13 #8 ve §2'deki özet satırlar kısayolu hâlâ sıkıştırılmış biçimde anıyor; belge tarihli bir girdi artefaktıdır ve §3.7'sinde ayrıntılı gerekçe zaten vardır — geçerli metin `docs/13` §7.1'dir. |
| 7 | Kurulum kesinti gerektiriyor mu, sahada ne kadar sürer; sensörlerin enerjisi nereden? | **Tasarım hedefi** (ölçülmedi): tek planlı kesinti penceresi, **≤ 45 dk, 2 kişi**. Besleme iç ihtiyaç devresinden sigortalı ve fişli klemensle alınır — yeni güç hattı çekilmez; 5 güvenlik kuralı sırayla uygulanır; akım trafosu sekonderi hiçbir an açık devre bırakılmaz (FMEA'daki en ağır donanım riski, kontrol listesinde ayrıca imzalanır). Kurulumdan sonra sahaya dokunmadan uzaktan yönetim ve imzalı OTA. **Ölçmedik:** 45 dakika sahada kronometreyle doğrulanmadı ve sensör düğümlerinin enerji toplama/pil ömrü (≥ 10 yıl hedefi) **ölçülmedi** — donanım üretilmedi (GK3, §1). Kanıt: `docs/08`, `docs/07`, `docs/13`. |
| 8 | TEDAŞ şartnamesine uyuyor mu? | Uyum haritası `docs/19-tedas-sartname-uyumu.md`'dedir ve **ortada iki ayrı şartname olduğu için ikiye ayrılır**: panonun kendi şartnamesi **TEDAŞ-MLZ/2003-06.B** komitenin verdiği PDF'ten okunduğu için tablo (a) **madde madde** kuruldu (1.4/Tablo 1, 2.2.1.xiii, 2.2.2, 2.2.3, 2.2.5, 2.2.6.1, 2.2.8.1.iv, 2.2.8.5, 2.2.10–2.2.12, 5.3); haberleşme ünitesi şartnamesi **TEDAŞ-MLZ/2019-064.B'nin tam metnine erişilmedi ve onun için hiçbir madde numarası yazılmadı** — yazılsaydı uydurma olurdu (`docs/19` §1). İki tablo veriyor: (a) madde → şartname ne diyor → tasarımın karşıladığını iddia edebildiklerimiz (tasarım hedefi) → **fiziksel doğrulama (tip testi) gerektirenler**; (b) BOM parçası → çalışma aralığı → uygulanan şartname sınırı → uygun / doğrulanmadı. Tablo (b)'nin 17 satırının **17'si de "doğrulanmadı"**: bu oturumda hiçbir üretici veri sayfasına erişilmedi, bu yüzden hiçbir parça için sıcaklık aralığı yazılmadı. Dilimiz "karşılıyoruz" değil **"tasarım hedefi, tip testi yapılmadı"**dır: EMC ve ortam sertifikasyon testleri bu teslimde **yapılmadı**. Standart ailesi tablosu `docs/11`'de, malzeme kaynağı `hardware/pano-beyni/bom.csv`. |
| 9 | Maliyet ne kadar, geri ödemesi ne? *(rapor §13 #11)* | `hardware/pano-beyni/bom.csv`'den okunan kontrolcü kartı maliyeti: **adet 1'de ~56 USD**, **adet 1.000'de ~37 USD/pano**. Bu rakama sensör düğümleri, SIM/veri aboneliği ve kurulum işçiliği **dahil değildir ve ölçülmedi**. Mevcut MPR-53CS ve TVOC-2 Modbus'tan sensör olarak okunduğu için BOM'a girmeyen kalemler haritadan sayıldı (4 akım trafosu, 3 gerilim girişi, 2 ark dedektörü, 1 ark merkez ünitesi) — ama **birim fiyatları depoda yok, bu yüzden net fark "veri yok"**. Buna karşılık ödenen kalem ölçülüdür: izole RS485 arayüzü 4,90 USD (adet 1) / 3,70 USD (adet 1.000). ROI tablosu bir **hesaplayıcı taslağıdır** ve varsayımlarını kendisi işaretler (P(arıza) %3, arıza başı 8.000 USD, tespit oranı ölçülen 1,00 yerine **bilinçli iskontolu %70**). Ölçülebilir olan taraf ayrı tutuldu: `scripts/tazminat_maruziyeti.py` parametresiz çalıştırıldığında hesap yapmaz, yönetmelik eşiğini ve tarifeyi **uydurmaz**. "Şu kadar arıza önledik" cümlesi hiçbir yerde geçmez. Kanıt: `docs/10`. |
| 10 | Operatör bu alarmla ne yapacak? | Her alarm kartı üç soruyu cevaplar — **Neden / Ne yapmalı / Ne kadar acil** — artı karşı-olgusal dördüncü blok: **"Ne doğrulanmalı"** (teşhisi kesinleştirecek eksik kanıt). Yönetim ISA-18.2 yaşam döngüsüdür: onay, **süreli ve gerekçeli raf** (P1 rafa alınamaz — API 403), bakım modu (P1 asla bastırılmaz), gruplama, histerezis, eskalasyon (P1'de 5. dakikada arama, 15. dakikada üst amir). Hedef öncelik dağılımı %5 / %15 / %80 (EEMUA 191). Arayüz ISA-101 / yüksek performanslı HMI dilindedir: nötr/sakin zemin (14 Eylül revizyonunda RAL 7035 grisi yerine beyaz — `theme.css` `--bg: #ffffff`), renk yalnızca anormal durumda, öncelik **renk + şekil + karakter** ile (renk körlüğü); açılış ekranı bir gösterge panosu değil **"sınıra kalan süre" zaman eksenidir**. Kanıt: `docs/06`, `docs/16`, `frontend/` 85/85 test, 7 ekran gerçek API'de 0 konsol hatası. |
| 11 | Piyasadaki ticari ürünlerden farkınız ne? | Konumlandırma `docs/18-konumlandirma-ve-standart-izi.md`'dedir: büyük üreticilerin varlık/enerji izleme platformları **üstte** durur; biz onların **altındaki ölçüm ve erken uyarı katmanıyız** — bugün IEC 60870-5-104 ve Modbus TCP ile bağlanırız, koruma devresine hiçbir yoldan yazmayız. Ölçülmüş üç somut fark: (a) mevcut MPR-53CS ve TVOC-2 **sensör olarak** okunur, ek cihaz alınmaz (`contracts/modbus-map.yaml` `source:` alanları); (b) tespit kenarda çalışır ve aynı RLS çekirdeği C ile Python'da **K 1,36e-8 / τ 1,42e-8** farkla eşleşir; (c) aynı veri üç arayüzde (REST, Modbus, IEC 104) **0 farkla** sunulur. **Fiyat karşılaştırması yapmadık** — rakip platformların birim maliyeti **ölçülmedi**, rakip ürün için fiyat yazmıyoruz ve doğrulayamadığımız hücreyi boş bırakıyoruz. Aynı dosyada durum izleme / tanı / prognoz / sağlık indeksi standart aileleri kod dosyalarına bağlanır. |
| 12 | Mevcut SCADA'ya nasıl bağlanıyor? *(rapor §13 #5)* | Merkezden **Modbus TCP 502** çalışıyor: her pano bir birim, kenardaki haritanın aynısı, varsayılan salt okunur (docs/03). Sahada RTU'ya Pano Beyni'nin Modbus slave portu (A). Tek master kısıtı için üç kurulum senaryosu (docs/03 §2). Aynı veri **IEC 60870-5-104 (TCP 2404)** kontrollü istasyon olarak da sunuluyor: genel sorgulama, zaman etiketli kendiliğinden gönderim, salt okunur (docs/04); canlıda IEC 104 = API (87 kontrol) = Modbus FC03 (139 adres), **0 fark**. |
| 13 | "Public cloud yok" dediniz; WhatsApp? *(rapor §13 #6)* | Birincil kanal tamamen yurt içi **GSM SMS**'tir ve sürücüsü üretim sürücüsüdür. WhatsApp ikincil ve kapatılabilir; mesajda yalnızca saha kodu, öncelik ve tek satır var. Alıcı numarası Meta'ya gittiği için açılması KVKK birimi kararına bağlı (docs/15 §4.2). |
| 14 | 10.000 panoya nasıl ölçeklenir? *(rapor §13 #12)* | **Ölçtük:** tek backend süreci 5.000 panoya kadar görünme p95 < 1 s; 10.000'de veri kaybetmeden doyuyor ve darboğaz ölçüldü — mesaj başına 615 µs'in **501 µs'i şema doğrulaması**. Kaldıraçlar: 60 s raporlama (mesaj hızı ÷6) ve paylaşımlı abonelikle çoklu ingest. Depolama: sıkıştırma **46–48×** ölçüldü ve şemaya eklendi; 100 pano 10 s'de ~105 GB/yıl, 60 s'de ~17 GB/yıl (docs/09). |
| 15 | Siber güvenlik? *(rapor §13 #13)* | Kodda olanlar: sözleşme dışı veri karantinası, pano kimliği denetimi, Modbus IP listesi + salt okunur varsayılan + koruma cihazına yazma yasağı + kaba kuvvet kilidi, denetim izi (docs/15). Tasarımda olanlar: cihaz sertifikası, mTLS, imzalı OTA (A/C). **Demo yığınında broker anonim ve API'de kimlik doğrulama yok**; üretim farkları listelendi (docs/15 §5, ayrıca §6'daki tablo). |
| 16 | Veri nerede, KVKK? *(rapor §13 #14)* | Tamamı şirket veri merkezinde. Telefon numaraları yalnızca yapılandırmada; veritabanında ve kayıtta **maskeli**. Disk şifreleme ve saklama süresi politikası yol haritasında (docs/15 §4.3). |
| 17 | TVOC-2 arkı zaten kesiyor; sizin katkınız? *(rapor §13 #7)* | Koruma sağlığı SCADA'ya ayrı bir coil olarak açılır (`prot_health_ok`); arızalı dedektör P1 alarmı telefonu çaldırır; olay öncesi 72 saatlik kara kutu API'si hazır; arkı doğuran öncüller (bağlantı ısınması, yoğuşma) zaten L1'de izlenir. **Koruma devresine hiçbir yoldan yazmıyoruz**: ağ geçidi bunu doğru şifreyle bile 0x02 ile reddediyor (`test_scada_gateway`, 13 Eylül canlı). |

**Kartın zayıf tarafları — soru gelirse önce biz söyleriz:** 5. satır (prognoz geri testi olumsuz) ve 3–4. satırlar
(çiy alarmı yükü ve bunun mevsime bağlılığı). İkisi de §6'da "aleyhimize çıkan iki ölçüm" başlığı altında ayrıca durur.

## 6. Bilinçli kapsam sınırları — "neyi yapmadınız?" sorusunun tek kaynağı

Bu bölüm, teslimdeki **bütün** bilinçli sapmaların toplandığı tek yerdir. Sapmalar kendi dosyalarında da yazılıdır
(`docs/03` §13, `docs/05` §10–§11, `docs/09` §8, `docs/10` §2, `docs/11` "Kapsanmayan standartlar", `docs/13`, `docs/15` §5,
`docs/16` §3 ve §5, `firmware/akis-diyagramlari/ana-dongu.md` §4) — burada özetlenir ve her satır kaynak dosyasına atıf verir,
böylece jüri hepsini tek sayfada görür. **Her satırın gerekçesi vardır:** gerekçesiz bir "yapmadık" listesi eksik listesi gibi
okunur, oysa bunların hepsi karar anında verilmiş ve o anda yazılmış mühendislik takaslarıdır. Hiçbiri sonradan keşfedilmedi.

### Bilinçli sapmalar

| # | Sapma | Gerekçe | Kaynak |
|---|---|---|---|
| 1 | KiCad şema PDF'i yok (MoSCoW *Must*) | Blok diyagram + I/O tablosu + BOM üçlüsü seçildi; üretime aynı bilgiyi verir. Bu ortamda doğrulanamayan bir `.kicad_sch` üretmektense doğrulanabilir üç dosya verildi | `hardware/pano-beyni/README.md`, `docs/13` §1 |
| 2 | Taşıma kabuğu Python; sanal seri port yerine TCP; kenarda Modbus slave sunumu yok | Modbus master döngüsü ve MQTT yayını **yapıldı** (`sim/panobeyni_sim.py`, 12 test). Kanıtlanmak istenen "kenarda ve merkezde aynı algoritma"dır ve o C'de doğrulandı (K 1,36e-8 / τ 1,42e-8); C'de sıfırdan MQTT/Modbus yığını yazmak buna bir şey katmazdı. Sahada RS485 olacak, protokol çerçevesi aynı | §3 DH2 |
| 3 | DIN kutu STL'i üretilmedi | `.scad` kaynağı var; bu geliştirme ortamında `openscad` kurulu değil, kurulu bir makinede tek komut yeterli | `docs/13` §6, `hardware/mekanik/din-kutu.scad` |
| 4 | Firmware belleği nokta başına 48 B yerine **320 B** (`double`; `float` derlemede 176 B) | Kalıcı uyarım koşulu 30 örneklik `I²` penceresi ister ve pencere tek başına 240 B tutar. Üstel düzleştirmeye geçmek belleği ~80 B'ye indirirdi **ama o zaman C ile Python farklı `excited` kararı verirdi** ve ortak test vektörü iki uygulamayı eşleştiremezdi. 25 nokta = 8,0 KB; hedeflenen MCU sınıfında (128–256 KB SRAM) sorun değil | `firmware/akis-diyagramlari/ana-dongu.md` §4 |
| 5 | Renode / Wokwi üzerinde MCU emülasyonu atlandı | MoSCoW *Should*. Zaten "hedef donanımda çalıştı" iddiamız yok; §2'de açıkça yazılı | §3 DH2, PLAN.md MoSCoW |
| 6 | 9 arayüz ekranının 7'si yapıldı | Mobil PWA ve devreye alma sihirbazı MoSCoW *Won't*; kabul ölçütü 7 ekrandı ve karşılandı | `docs/16` §2 |
| 7 | Cihaz Sağlığı ekranı pano başına istek atıyor (6 eşzamanlı) | Toplu `fleet/health` ucu **donmuş sözleşmede** yok; öneri açıldı ama sözleşmeye teslim penceresinde dokunulmadı. 20 panoda görünmez, 1.000 panoda yavaşlar — ekranın altında bu açıkça yazıyor | `docs/16` §3, `contracts/changes/2026-09-14-fleet-health-bulk.md` |
| 8 | Bölge haritası ilçe merkezi hassasiyetinde; gerçek harita karosu yok | 15 Eylül'de sözleşmede zaten onaylı `lat`/`lon` alanına geçildi, ama konum gerçek trafo GPS pini değil ilçe merkezidir ve ekranda böyle yazar. `lat`/`lon` göndermeyen panolar dağıtım şirketi gruplamasına düşer — olmayan veri hiçbir zaman olmuş gibi gösterilmez. Karo yok, çünkü yığın internetsiz çalışmak zorunda (GK4) | `docs/16` §3 |
| 9 | pymodbus sunucusu yerine kendi Modbus TCP sunucumuz | pymodbus 3.7.4 sunucusu her kapanan bağlantıda rastgele bir portta yeni dinleme soketi açıyordu (3 bağlantı → 3 sızan port) ve yazmayı değerine göre reddetmeye, bağlantıyı IP'ye göre kesmeye izin vermiyordu. pymodbus **istemcisi** testlerde bağımsız doğrulayıcı olarak kullanılmaya devam ediyor | `docs/03` §13 |
| 10 | Demo yığını kimlik doğrulamasız (broker anonim 1883, API açık, Modbus/IEC 104 düz TCP) | Demo tek makinede, internetsiz ve sertifika altyapısı kurmadan çalışsın diye sadeleştirildi (GK4). Sadeleştirmelerin **hiçbiri koddaki kontrolleri kapatmaz**; eksik olan altyapıdır ve üretim karşılığı satır satır yazılıdır | `docs/15` §5 |
| 11 | **S0'da 71,4 yanlış alarm/100 pano/gün** | Sözleşme sınırı 150; sıfır değildir ve tamamı çiy noktası uyarısıdır. Eşiği kısmak yükü **artırıyor** (ölçüldü) → aşağıdaki "Aleyhimize çıkan iki ölçüm" | `docs/12` §3, `docs/05` §11 |
| 12 | **`ttl_h` prognoz geri testi olumsuz çıktı** | Ölçtük, kötü çıktı, sakladığımız yok: iddia küçültüldü (`ttl_h` = yön göstergesi, takvim değil) → aşağıdaki "Aleyhimize çıkan iki ölçüm" | `docs/12` §4, `docs/05` §10 |
| 13 | L2 istatistiksel katman hiçbir alarm kodu üretmiyor | Rapor §6.5 saat-of-hafta robust z, EWMA/CUSUM ve filo karşılaştırmasını tanımlıyor; donmuş `contracts/alarm-codes.yaml`'da `layer: L2` etiketli kod **yok**. Sözleşmeyi teslim penceresinde değiştirmemeyi seçtik — boşluk rapor ile sözleşme arasındadır ve gizlenmiyor | `docs/05` §10 |
| 14 | Üç alarm kodunun eşiği sözleşmede yok, türetilmiş varsayılanla çalışıyor (`ALM-DQ-BELOW-AMBIENT`, `ALM-NEUTRAL-THD`, `ALM-PD-TREND`) | Öneri dosyası açıldı, üç onay bekliyor. Kabul edilene kadar kenar ile merkezin aynı kuralı farklı sayıyla uygulama riski vardır; risk saklanmıyor, yazılıyor | `docs/05` §10, `contracts/changes/2026-09-14-eksik-esikler.md` |
| 15 | Kısmi deşarj ve dalga biçimi kapsam dışı (komite HFCT veri sayfası paylaşmış olmasına rağmen) | AG panoda sürekli/yinelenen PD aktivitesi tipik olarak raporlanmaz; gerekçe **gerilim eşiği değil geometriktir** (Paschen eğrisi gerilimi değil basınç × boşluk mesafesini sınırlar — 400 V'ta faz-faz tepe gerilimi ≈ 566 V olduğu için "~327 V'un altındayız" kısayolu yanlıştır). **Bu bir literatür kabulüdür, bizim ölçümümüz değildir: AG panoda PD ölçümü yapılmadı.** Üstelik 10 saniyelik skaler mimari seri arkı ve kontak kıvılcımlanmasını **fiziksel olarak göremez**. "Yapabiliriz" demiyoruz; tetikli dalga biçimi yakalama sonraki donanım revizyonunun konusudur | `docs/13` §7.1, `docs/11` "Kapsanmayan standartlar" |
| 16 | Sertifikasyon ve tip testleri (EMC, ortam, şartname doğrulaması) yapılmadı | Donanım üretilmedi (GK3, §1). Tasarım hedefleri belgelendi; dilimiz "karşılıyoruz" değil **"tasarım hedefi, tip testi yapılmadı"** | `docs/11`, `docs/19` |
| 17 | Sensör düğümleri (S1–S5) kavramsal seviyede; BOM yalnızca Pano Beyni kartını kapsıyor | Sınırlı bütçe ve zaman kontrolcü kartına ayrıldı. Bu yüzden ~37 USD/pano sayısı **yalnızca karttır**; sensör düğümü, SIM/veri aboneliği ve kurulum işçiliği dahil değildir ve **ölçülmedi** | `docs/10` §2, `hardware/sensor-dugumu/` |
| 18 | Hücresel hat simüle edilmedi: tek makinede yerel ağ, gecikme ve kopukluk yok | Ölçülmek istenen platform kapasitesiydi. Hücresel gecikme (tipik 50–300 ms) bu sayıların **dışındadır**; kopukluk davranışı ayrıca halka tamponla ve backfill'le sınandı | `docs/09` §8, §2 tablosu |
| 19 | Yük testinde 1.000–10.000 ayrı TLS bağlantısı ve alarm seli ölçeği sınanmadı; koşular 2–5 dakika | 20–50 MQTT bağlantısı panoları paylaştı; TLS el sıkışma fırtınası (toplu yeniden bağlanma) ve yüzlerce eşzamanlı P1 ayrıca sınanmalıdır. 24 saatlik etkiler (sıkıştırma işinin kendisi, autovacuum, parça oluşturma) ölçümün dışındadır | `docs/09` §8 |
| 20 | Ekran görüntüleri örnek veri modunda alındı | `npm run dev:mock` ile alındı ve `docs/16` §5'te böyle işaretlendi; gerçek yığından yenilenmesi aşağıdaki "hâlâ açık" listesindedir | `docs/16` §5 |

### Aleyhimize çıkan iki ölçüm

Bu iki madde teslimi zayıflatmaz, güçlendirir: **ikisini de biz ölçtük ve biz yayımladık.** Olgun programlar sınırlarını
kendileri yazar; jüri bunları bizden önce bulursa dürüstlük iddiasının tamamı çöker.

**1. Prognoz geri testi olumsuz çıktı.** Kalan ömür tahmininin (`ttl_h`) doğruluğunu ölçtük ve sonuç şu:

| Ölçüt (S1, gevşek bağlantı) | Ölçülen | Sağlıklı bir prognozda beklenen |
|---|---|---|
| ±%20 konisi içinde kalan tahmin (α = 0,20) | 790 tahminin **%5,2**'si | arıza yaklaştıkça 1'e gitmesi |
| Prognostic horizon (PH) | **yok** | pozitif bir an |
| Ortalama göreli doğruluk (CRA) | **−5,12** | 1,00'e yakın |
| İhlale < 48 saat kala koni içinde kalma | **%0** | en yüksek doğruluk bölgesi |
| Medyan tahmin / gerçek | 1,69 | 1,00 |
| Yörünge sayısı | **n = 1 → güven aralığı YOK** | çok sayıda yörünge |

Yanında iki kayıt daha: `S2_overload`'da **hiç tahmin üretilmedi** (kalıcı uyarım ve sürekli pozitif eğim koşulları
sağlanmadı, `ttl_h` null kaldı — uydurmak yerine susuyor); `S8_sensor_fault`'ta ise sınır **hiç aşılmadığı hâlde 99 tahmin**
üretildi ve **89'u** `ALM-TTL-14D` alarmına döndü. Bu bir **prognoz yanlış-alarmıdır** ve `docs/12` §3'teki yanlış alarm
sayacı onu görmez, çünkü etiket penceresinin içinde çıkıyor. Kaynağı da ölçüldü: 99 tahminin tamamı S8'in **sürüklenen**
sensöründen geliyor ve L-1 veri kalitesi katmanı o noktayı 672 örneğin hiçbirinde işaretlemiyor.

*Ne yaptık:* sayıyı saklamak yerine **iddiayı küçülttük**. Sunumda `ttl_h` bir **yön göstergesi** olarak anlatılır, takvim
olarak değil; manşetteki **209 saatlik öne alma tespit katmanından (K/K₀ eşiği) gelir, bu tahminden değil** ve ikisi
karıştırılmaz. *Neden bu teslimde düzeltmedik:* kestirimin yeniden tasarımı yeni bir doğrulama turu ister; ölçülmüş ve
yayımlanmış bir zayıflık, aceleyle değiştirilmiş bir kestirimden daha savunulabilir. Sonraki iterasyonun ilk maddesidir.
Kanıt: `docs/12` §4 (betikle üretilir), `docs/05` §10, `libs/panoalgo/panoalgo/prognostics.py`.

**2. Çiy eşiği taraması: sayı kısmen algoritmayı değil iklimi ölçüyor.** Sözleşme eşik çifti sağlıklı panoda 71,4 olay
üretiyor. "Eşiği kısın" itirazını ölçtük — tersi çıktı:

| Uyarı / alarm eşiği (K) | Olay / 100 pano / gün | Not |
|---|---:|---|
| **3,0 / 1,0 (sözleşme)** | **71,4** | alarm hâlâ temizleniyor (ayakta kalma %94,5, 4 ayrı olay) |
| 2,0 / 0,5 | 128,6 | |
| 1,0 / 0,0 | **171,4** | sözleşmenin 150 bütçesini **aşıyor** |
| 0,5 / 0,0 | **228,6** | |
| 4,0 / 2,0 (gevşetme) | 28,6 | sayı düşüyor ama alarm haftanın %100'ünde ayakta — EEMUA 191'in **bayat alarm** patolojisi |

Aynı sağlıklı senaryo, **eşik sabit**, yalnızca mevsim değişiyor: kış **28,6** · geçiş **71,4** · **yaz 0,0**
(yazda çiy marjı medyan +10,17 K, en düşük +7,48 K). Yani 71,4 bir algoritma hatası değil, büyük ölçüde bir **mevsim
özelliğidir** ve bunu kendi tablomuz gösteriyor. İkinci dürüst kayıt: sağlıklı panonun en düşük çiy marjı (−1,69 K) ile
yoğuşma enjekte edilmiş `S3_condense`'in marjı (−1,72 … −1,69 K) **aynı bölgede**; bu iki durum bu özellik üzerinden
**hiçbir eşikle** ayrılamaz — ayrım ancak gerçek yüzey sıcaklığı ölçülürse mümkün olur, yani bu bir donanım/sözleşme
konusudur, eşik konusu değil.

*Ne yaptık:* eşik **değiştirilmedi** ve sözleşme değişikliği **önerilmedi**; canlı demoda `S0` artık yaz günü oynatılıyor
(`demo/senaryo/s0.sh --season yaz`, ölçülen: 0,0 olay) — yani değişen şey eşik değil **senaryo mevsimidir** ve bunu
demo betiğinin başında da, burada da yazıyoruz. `docs/12` §3'teki 71,4 sayısı, fixture'lar "geçiş" mevsiminde üretildiği
için aynen geçerlidir. Kanıt: `scripts/threshold_sweep.py --verify --seasons`, `docs/05` §11,
`libs/panoalgo/tests/test_threshold_sweep.py`.

### Hâlâ açık

| Kanıt | Sahip | Hedef / durum |
|---|---|---|
| Gerçek bir telefona WhatsApp teslimi (Meta test numarası + token + doğrulanmış alıcı) | B | M2'de kapanmadı, teslim gününe kadar açık. Gelmezse bilinçli sınır olarak sunulur; demo SMS yolu ve AT kaydıyla sürer (§3 DH5) |
| Sıfırdan `git clone` ile temiz makine testi (T4.4) | B | M4 (18 Eylül) |
| 1.000 pano yük testinin fizik üreteciyle tekrarı (`docs/09` sayıları şablon üreteçle ölçülmüştü; `loadtest/fleet.py` artık varsayılan olarak fizik üretecini kullanıyor) | B | M4 (18 Eylül) |
| İki `contracts/changes` önerisinin onayı ya da bilinçli erteleme | A + B + C | 17 Eylül (özellik dondurma, GK2). Bu tarihten sonra onaylansa bile uygulaması sonraki sürüme kalır; o durumda yukarıdaki 7. ve 14. satırlarda **bilinçli erteleme** olarak durur |
| Gerçek yığından (örnek veri değil) ekran görüntüleri | C | M4 (18 Eylül) |

> Bu bölümde adı geçmeyen bir sapma varsa bu bir hatadır, saklama değildir — fark edildiği anda buraya eklenir.
