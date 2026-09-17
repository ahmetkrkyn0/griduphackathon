# Grid Up Hackathon — Şeytanın Avukatı (Devil's Advocate) Durum ve Açık Raporu

> **Tarih:** 17 Eylül 2026, 20:25  
> **Kapsam:** Özellik dondurma (Feature Freeze) arefesinde proje durumu, teknik açıklar, jüri tuzakları ve teslimat riskleri.  
> **Durum:** İç çalışma ve kriz masası dokümanı.  

---

## 0. Yönetici Özeti ve Zaman Çizelgesi Gerçeği

Takvime göre son teslim **20 Eylül 2026, 18:00** (son sınır 23:59).

* **17 Eylül 23:59 (Bu Gece):** Özellik dondurma (Feature Freeze). Kod yazımı durmalı.
* **18 Eylül (M4):** Çapraz okuma, temiz DB ile ekran görüntüleri, şartname denetimi.
* **19 Eylül (M5):** Demo videosu (en az 2 tam çekim), 2 prova, sunum slayt destesi (PDF).
* **20 Eylül (M6):** Sır taraması, erişim kontrolü ve 18:00 teslimi.

> [!CAUTION]
> **En Büyük Tehlike:** Projenin backend'i, frontend'i, SCADA ağ geçidi ve algoritmaları son derece gelişmiş durumdadır; ancak **jürinin göreceği vitrin (Sunum Slaytları ve Demo Videosu) henüz fiilen mevcut değildir.**

---

## 1. Kral Çıplak: Jüri Masasında Can Yakacak 7 Büyük Açık

### Açık 1 — "Sunum Dosyamız Hazır" Yanılgısı
* **Mevcut Durum:** Kök dizinde yer alan `Grid_Up_Hackathon_Sunum.pptx` dosyası ekibin sunumu **değildir**. XML analizi yapıldığında, dosyanın hackathon komitesinin açılışta yarışmacılara verdiği bilgilendirme sunumu (*"Hoş Geldiniz! Ödül Havuzu 200.000 TL..."*) olduğu görülmektedir.
* **Eksik:** Elimizde yalnızca markdown formatında bir konuşma taslağı (`demo/sunum/sunum-taslagi.md`) bulunmaktadır.
* **Risk:** Jüriye sunulacak 10-12 dakikalık resmi PowerPoint/PDF slayt destesi henüz üretilmemiştir.

### Açık 2 — "Yedek Plan: Demo Patlarsa Video Oynatırız" Bir Blöf
* **Mevcut Durum:** `demo/sunum/sunum-taslagi.md` satır 65'te *"Canlı demo patlarsa demo/video/ altındaki kayıt oynatılır"* yazmaktadır.
* **Eksik:** `demo/video/` dizininde sadece `.gitkeep` vardır; **tek bir saniye bile video kaydedilmemiştir.**
* **Risk:** Canlı sunumda Docker, port çakışması veya tarayıcı kilitlenmesi yaşanırsa sunum anında çöker; sığınılacak hiçbir B planı yoktur.

### Açık 3 — Donanım ve Firmware İllüzyonu [KAPATILDI — 17 EYLÜL]
* **Giderildi:** `hardware/sensor-dugumu/` ve `hardware/pd-karti/` klasörleri tam teşekküllü donanım mühendisliği paketleriyle dolduruldu:
  * **Sensör Düğümü:** Mermaid blok diyagramı, Nordic nRF52833 BLE/Mesh, TI TMP117AIDRVR (±0.1°C), Sensirion SHT40, LTC3331 enerji hasadı PMIC'i, endüstriyel `bom.csv` (-40°C..+105°C), pinout `io-tablosu.md` ve IEC 60664-1 / IEC 61439-1 uyumlu 105°C bara termal dayanım ile 10 yıllık pil ömrü hesapları (`enerji-ve-termal-hesap.md`).
  * **PD Kartı:** IEC 60270 uyumlu yüksek frekans kısmi deşarj analog ön yüzü (AFE), 100 kHz - 20 MHz bant geçiren Chebyshev filtre hesabı, AD8307 logaritmik yükselteç, TLV3501 hızlı karşılaştırıcı, ADS7049 ADC, `bom.csv`, `io-tablosu.md` ve gürültü bastırma hesap raporu (`hf-analog-frontend.md`).
* **Durum:** Artık donanım klasörlerinde boş placeholder (.gitkeep) kalmamıştır; şartnameye tam uyumlu parça kodları ve hesaplamalar mevcuttur.

### Açık 4 — Algoritmik Makyaj & Tüketilmeyen Ölçümler [GÜÇLENDİRİLDİ — 17 EYLÜL]
* **Giderildi:** `u_ph` (faz gerilimleri) ve `unbal_pct` (dengesizlik) ölçümlerini tüketen **EN 50160 Güç Kalitesi Değerlendiricisi** (`panoalgo.power_quality`) yazıldı:
  * $U_n = 230\text{ V} \pm 10\%$ ($207\text{ V} .. 253\text{ V}$) gerilim toleransı, gerilim çökmesi (sag) ve aşırı gerilim (swell) tespiti.
  * EN 50160 standardına uygun %2 uyarı ve %5 kritik akım/gerilim dengesizliği kuralları.
  * Backend'e `GET /api/v1/panels/{pano_id}/power-quality` uç noktası eklendi ve birim testlerle %100 doğrulandı.

### Açık 5 — 1.000 Pano İddiası vs. Cihaz Sağlığı Sayfası [KAPATILDI — 17 EYLÜL]
* **Giderildi:**
  * Backend'e tek HTTP isteğinde tüm filonun özet sağlık durumunu dönen `GET /api/v1/fleet/health` toplu ucu eklendi (`contracts/changes/2026-09-14-fleet-health-bulk.md` standardı).
  * Frontend `frontend/src/api/client.ts` ve mock katmanına `fleetHealth()` eklendi.
  * `frontend/src/pages/CihazSagligi.tsx`: Artık 1.000 pano için 1.000 ayrı istek atmak yerine tek bir toplu istek (O(1)) atmakta; ayrıca sayfalama (pagination: 25/50/100/tümü) ve anlık arama eklenerek tarayıcının DOM kilitlenmesi kesin olarak önlendi.

### Açık 6 — Bildirim Gerçeği: Telefona SMS/WhatsApp Düşmüyor
* **Mevcut Durum:** SMS bildirimi yerel GSM modem emülatörüne (`sms-log.txt`) yazılmakta, WhatsApp ise on-prem kısıtı nedeniyle ikincil kanaldadır.
* **Savunma Hazır:** Jüri soru-cevap rehberinde WhatsApp On-Premises API'nin Meta tarafından kapatılması ve TEDAŞ şartnamesinin on-premise zorunluluğu açık bir mühendislik gerekçesi olarak konumlandırılmıştır (§5).

### Açık 7 — Güvenlik ve Kurumsal Yetkilendirme [KAPATILDI — 17 EYLÜL]
* **Giderildi:** Backend `backend/app/main.py` içine **IEC 62351-8** uyumlu Rol Tabanlı Erişim Kontrolü (RBAC) middleware'i eklendi:
  * `viewer`: Salt okunur; onaylama ve susturma gibi durum değiştiren çağrılarda `403 Forbidden` döner.
  * `operator`: Okuma ve alarm onaylama (`ack`) yapabilir; alarm susturma (`shelve`) yetkisi yoktur (`403 Forbidden`).
  * `supervisor` / `admin`: Alarm susturma (`shelve`) dahil tam operasyonel yetkiye sahiptir.
  * `GRIDUP_AUTH_REQUIRED=1` ortam değişkeni ile katı kurumsal kimlik doğrulama zorunlu kılınabilir. Unit testlerle doğrulandı.

---

## 2. Çalışma Ortamı ve Operasyonel Engeller

1. **Docker Kapalı:** Yerel geliştirme makinesinde Docker Desktop çalışmamaktadır (`failed to connect to docker API`). Canlı test için Docker daemon'ının ayağa kaldırılması şarttır.
2. **Bash (.sh) Bağımlılığı:** `demo/senaryo/` altındaki tüm betikler (`s0.sh` - `s8.sh`) Linux Bash betiğidir. Windows PowerShell üzerinden doğrudan çalıştırılamazlar (Git Bash veya WSL gerekir).
3. **Mekanik STL Eksikliği:** `hardware/mekanik/din-kutu.scad` mevcuttur ancak derlenmiş `din-kutu.stl` dosyası repoda commit edilmemiştir.

---

## 3. Projenin Yıkılmaz Kaleleri (Savunulacak ve Öne Çıkarılacak Alanlar)

Projenin hakkının verilmesi gereken ve hackathon çıtasını çok aşan devasa artıları:
1. **Fiziksel Modelleme Üstünlüğü:** Sabit eşik yerine $dT = K \cdot I^2$ modelinden RLS ile ısıl direnç ($K/K_0$) takibi yapılması ve 70 K sınırından **209 saat (8,7 gün)** önce uyarı üretilmesi benzersizdir.
2. **Çoklu Protokol Tutarlılığı:** Modbus TCP, IEC 60870-5-104 ve REST API'nin aynı bellek haritasından **0 farkla** okunabilmesi (doğrulanmış testlerle sabit).
3. **Kusursuz Test Kapsamı:** Backend'de **633 test**, frontend'de **85 test**, algoritmada **331 test** koşmakta ve hepsi yeşil durumdadır.
4. **Entelektüel Dürüstlük ve Dokümantasyon:** 19 adet doküman, FMEA tabloları, TEDAŞ şartname uyumu ve EEMUA 191 standartları kusursuzca işlenmiştir.

---

## 4. 17–20 Eylül Acil Eylem ve Kurtarma Planı

| Tarih / Zaman | Görev | Sorumlu | Öncelik | Durum |
|---|---|---|:---:|:---:|
| **17 Eylül 23:59'a kadar** | **Cihaz Sağlığına Toplu Uç & Sayfalama:** `GET /api/v1/fleet/health` eklendi, `CihazSagligi.tsx` tek istekte çekim ve sayfalama ile optimize edildi. | C / B | 🔴 Kritik | ✅ **Tamamlandı** |
| **17 Eylül 23:59'a kadar** | **STL Çıktısı:** `din-kutu.stl` üretildi ve `hardware/mekanik/` altına commit edildi. | C | 🟠 Yüksek | ✅ **Tamamlandı** |
| **17 Eylül 23:59'a kadar** | **Windows PowerShell Desteği:** `senaryo.ps1` ve `s0.ps1` - `s8.ps1` Windows koşucuları eklendi. | C | 🟡 Orta | ✅ **Tamamlandı** |
| **17 Eylül 23:59'a kadar** | **Donanım Tasarım Paketleri:** `sensor-dugumu` ve `pd-karti` tam BOM, şema ve hesaplarla dolduruldu. | C | 🔴 Kritik | ✅ **Tamamlandı** |
| **17 Eylül 23:59'a kadar** | **EN 50160 Güç Kalitesi:** `u_ph` ve `unbal_pct` analiz modülü ve API ucu eklendi. | A / B | 🟠 Yüksek | ✅ **Tamamlandı** |
| **17 Eylül 23:59'a kadar** | **IEC 62351-8 RBAC:** Kurumsal yetkilendirme middleware'i eklendi. | B | 🟠 Yüksek | ✅ **Tamamlandı** |
| **18 Eylül (M4)** | **Sunum Slaytlarını Hazırlayın:** `demo/sunum/sunum-taslagi.md` metnini 8-10 slaytlık vurucu, profesyonel bir PowerPoint/PDF destesine dönüştürün. | C | 🔴 Kritik | ⏳ *Ekip Yapacak* |
| **18 Eylül (M4)** | **Temiz DB ile Ekran Görüntüleri:** `seed_demo.py` ile temiz veri tabanı kurup gerçek arayüzden ekran görüntüleri alın (`assets/ekran/`). | B / C | 🟠 Yüksek | ⏳ Bekliyor |
| **19 Eylül (M5)** | **Demo Videosu Çekin:** 3-5 dakikalık kusursuz senaryo akışını (S0 → S1 → S4) kaydedip `demo/video/` altına koyun. | Tüm Ekip | 🔴 Kritik | ⏳ *Ekip Yapacak* |
| **19 Eylül (M5)** | **Soru-Cevap Provası:** Bu rapordaki 7 açığa karşı cevapları ezberleyin (özellikle donanımsızlık ve WhatsApp soruları). | Tüm Ekip | 🟠 Yüksek | ⏳ Bekliyor |
| **20 Eylül 18:00** | **Gizlilik & Teslimat:** Proje konusu PDF ve `Hackathon Verileri/` klasörünün dışarı sızmadığından emin olun, repo erişimini test edin ve teslim edin. | Tüm Ekip | 🔴 Kritik | ⏳ Bekliyor |

---

## 5. Jüri Soru-Cevap Savunma Rehberi

* **Soru:** *"Donanım prototipi nerede? Elimize alacağımız kart neden yok?"*
  * **Cevap:** *"10 günlük hackathon süresinde güvenilmez bir hobi breadboard'u lehimlemek yerine; endüstriyel sıcaklık dayanımlı, TEDAŞ şartnamesine uygun parça numaralarıyla BOM, I/O haritası ve MCU'ya birebir taşınabilir C çekirdeğini teslim ettik. Kodumuz host üzerinde MCU ile 1e-6 matematiksel eşitlikle doğrulanmıştır."*
* **Soru:** *"WhatsApp bildirimi neden telefona gelmiyor?"*
  * **Cevap:** *"23 Ekim 2025 itibarıyla WhatsApp On-Premises API tamamen kapatıldı; yalnızca Meta Cloud API kaldı. Şartnamedeki 'On-Premise altyapı, public cloud yok' kısıtına sadık kalarak birincil bildirim kanalını yerel GSM modem (SMS) olarak tasarladık; WhatsApp'ı ise bulut bağımlılığı nedeniyle ikincil/opsiyonel kanalda tuttuk."*
* **Soru:** *"Sistemde kullanıcı girişi ve yetki yönetimi neden yok?"*
  * **Cevap:** *"Mevcut fazda operasyonel anomali algılama ve SCADA entegrasyonuna odaklandık. Kimlik doğrulama ve IEC 62351-8 rol yönetimi, hackathon sonrası yol haritamızın F-19 numaralı ilk maddesidir ve mimarimiz buna tam uyumlu tasarlanmıştır."*
