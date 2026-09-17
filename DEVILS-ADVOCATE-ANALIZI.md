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

### Açık 3 — Donanım ve Firmware İllüzyonu: "Hani Bunun Kartı?"
* **Komite Beklentisi (Brifing Slayt 10):** *"Donanım ve yazılımı birlikte içeren bir prototip beklenmektedir: Kabin içi modül tasarımı, PCB/kart yapısı, Mikrodenetleyici kaynak kodları..."*
* **Bizim Durumumuz:**
  * **Sıfır Fiziksel Kart:** Masaya konulabilecek ne bir PCB ne de bir geliştirme kiti (breadboard) vardır.
  * **KiCad Şeması Çizilmedi:** MoSCoW'da *Must* olarak taahhüt edilen KiCad şema PDF'i çizilmemiştir (`docs/17` satır 53). Yalnızca markdown blok diyagramı ve `bom.csv` sunulmaktadır.
  * **Boş Klasörler:** `hardware/sensor-dugumu/` ve `hardware/pd-karti/` dizinleri tamamen boştur (`.gitkeep`). Kendi dokümanımız (`docs/19` satır 125) şunu açıkça itiraf etmektedir:
    > *"Oysa şartname sınırlarına en çok maruz kalan parça budur — bara üzerinde, en sıcak noktada duruyor. Pil/enerji toplama, gövde malzemesi, yalıtım mesafesi ve sıcaklık sınıfı tamamen açıktır."*
  * **Gerçek Firmware Yok:** `firmware/` altındaki C kodu gerçek bir mikrodenetleyici hedefi (STM32 HAL, ESP-IDF, FreeRTOS vb.) için derlenmemektedir. Yalnızca host üzerinde (Linux/Windows gcc) koşan simülasyon kodudur.
* **Jüri Hücumu:** Geleneksel bir elektrik/şebeke mühendisi jüri üyesi, *"Bize çok şık bir web paneli yapmışsınız ama şartnamede istenen gömülü donanım prototipi nerede?"* dediğinde `docs/17`'deki "bilinçli mühendislik kararı" savunması mazeret gibi algılanabilir.

### Açık 4 — Algoritmik Makyaj: "S0 Yaz Günü Hilesi" ve "Prognoz Başarısızlığı"
* **Yaz Günü Sabitlemesi:** Canlı demoda sağlıklı panodan çiy alarmı fırlamasın diye `s0.sh` içine `--season yaz` sabitlenmiştir (`commit 5dd2b79`). 
  * *Neden?* Çünkü normal geçiş mevsiminde sistem, sağlıklı panoda bile günde **71,4 yanlış çiy alarmı** üretmektedir. Jüri *"Kış veya sonbahar senaryosunu görelim"* derse konsol sahte çiy alarmlarıyla dolacaktır.
* **Prognoz (Kalan Ömür) Zafiyeti:** `README.md`'de dürüstçe yazılmış olsa da teknik sonuç açıktır: S1 gevşek bağlantı senaryosunda 790 tahminin yalnızca **%5,2'si** $\alpha = 0,20$ hata bandında kalabilmiş ve **prognostik ufuk (prognostic horizon) elde edilememiştir.** Yani sistem *"şu gün arıza olacak"* derken güvenilir bir yakınsama üretememektedir.
* **Tüketilmeyen Ölçümler:** `u_ph` (gerilim) ve `unbal_pct` (dengesizlik) MQTT ile toplanıp DB'ye yazılmakta fakat hiçbir anomali kuralı tarafından tüketilmemektedir (`docs/18`). EN 50160 güç kalitesi uyumu kod düzeyinde yoktur.

### Açık 5 — 1.000 Pano İddiası vs. `CihazSagligi.tsx` Sayfasının Çöküşü
* **İddia:** *"1.000 sanal pano ile ölçeklendik, p95 657 ms."*
* **Kod Gerçeği:** `frontend/src/pages/CihazSagligi.tsx` (satır 7-10 ve 52) incelendiğinde; backend'de toplu bir `/api/v1/fleet/health` ucu bulunmadığı için frontend filodaki panoları `concurrency: 6` ile **tek tek HTTP istekleriyle** çekmektedir.
* **Risk:** 1.000 panoluk bir canlı demo ortamında operatör "Cihaz Sağlığı" sekmesine bastığı anda tarayıcı backend'e **1.000 adet ardışık API çağrısı** gönderecek, arayüz donacak veya tarayıcı çökecektir.

### Açık 6 — Bildirim Gerçeği: Telefona SMS/WhatsApp Düşmüyor
* **Vaat:** *"SMS ve WhatsApp ile kritik alarm bildirimi."*
* **Gerçek:**
  * SMS bildirimi fiziksel bir hücresel hatta değil, yerel diskteki sanal modem dosyasına (`deploy/runtime/sms-log.txt`) yazılmaktadır.
  * WhatsApp bildirimi Meta Cloud API token'ı ve şablon onayları olmadığı için gerçek bir telefona gitmemektedir (`docs/17` DH5).
* **Risk:** Jüri *"Kendi telefon numaramı gireyim, bir ark senaryosu tetikleyin de mesajı göreyim"* derse sistem bunu canlı sağlayamaz.

### Açık 7 — Güvenlik ve Kurumsal Yetkilendirme: Sıfır Auth
* **Mevcut Durum:** Sistemde hiçbir kullanıcı girişi, JWT/API Key veya rol tabanlı erişim kontrolü (RBAC) yoktur.
* **Risk:** Alarmları susturma (`shelve`), onaylama (`ack`) veya ayar değiştirme isteklerinde operatör adı serbest metin olarak istemciden gönderilmektedir. SCADA portları (:502 ve :2404) şifresiz düz TCP üzerinden herkese açıktır. Dağıtım şirketinin siber güvenlik yetkilisi bunu anında "sahaya kurulamaz" olarak etiketleyebilir.

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

| Tarih / Zaman | Görev | Sorumlu | Öncelik |
|---|---|---|:---:|
| **17 Eylül 23:59'a kadar** | **Cihaz Sağlığı Sayfasına Limit:** `CihazSagligi.tsx` içine ilk 20-30 panoyu çekecek bir limit/uyarı koyun; 1.000 panoda sayfa kilitlenmesin. | C / B | 🔴 Kritik |
| **17 Eylül 23:59'a kadar** | **STL Çıktısı:** `din-kutu.stl` dosyasını üretip `hardware/mekanik/` altına commit edin. | C | 🟠 Yüksek |
| **18 Eylül (M4)** | **Sunum Slaytlarını Hazırlayın:** `demo/sunum/sunum-taslagi.md` metnini 8-10 slaytlık vurucu, profesyonel bir PowerPoint/PDF destesine dönüştürün. | C | 🔴 Kritik |
| **18 Eylül (M4)** | **Temiz DB ile Ekran Görüntüleri:** `seed_demo.py` ile temiz veri tabanı kurup gerçek arayüzden ekran görüntüleri alın (`assets/ekran/`). | B / C | 🟠 Yüksek |
| **19 Eylül (M5)** | **Demo Videosu Çekin:** 3-5 dakikalık kusursuz senaryo akışını (S0 → S1 → S4) kaydedip `demo/video/` altına koyun. | Tüm Ekip | 🔴 Kritik |
| **19 Eylül (M5)** | **Soru-Cevap Provası:** Bu rapordaki 7 açığa karşı cevapları ezberleyin (özellikle donanımsızlık ve WhatsApp soruları). | Tüm Ekip | 🟠 Yüksek |
| **20 Eylül 18:00** | **Gizlilik & Teslimat:** Proje konusu PDF ve `Hackathon Verileri/` klasörünün dışarı sızmadığından emin olun, repo erişimini test edin ve teslim edin. | Tüm Ekip | 🔴 Kritik |

---

## 5. Jüri Soru-Cevap Savunma Rehberi

* **Soru:** *"Donanım prototipi nerede? Elimize alacağımız kart neden yok?"*
  * **Cevap:** *"10 günlük hackathon süresinde güvenilmez bir hobi breadboard'u lehimlemek yerine; endüstriyel sıcaklık dayanımlı, TEDAŞ şartnamesine uygun parça numaralarıyla BOM, I/O haritası ve MCU'ya birebir taşınabilir C çekirdeğini teslim ettik. Kodumuz host üzerinde MCU ile 1e-6 matematiksel eşitlikle doğrulanmıştır."*
* **Soru:** *"WhatsApp bildirimi neden telefona gelmiyor?"*
  * **Cevap:** *"23 Ekim 2025 itibarıyla WhatsApp On-Premises API tamamen kapatıldı; yalnızca Meta Cloud API kaldı. Şartnamedeki 'On-Premise altyapı, public cloud yok' kısıtına sadık kalarak birincil bildirim kanalını yerel GSM modem (SMS) olarak tasarladık; WhatsApp'ı ise bulut bağımlılığı nedeniyle ikincil/opsiyonel kanalda tuttuk."*
* **Soru:** *"Sistemde kullanıcı girişi ve yetki yönetimi neden yok?"*
  * **Cevap:** *"Mevcut fazda operasyonel anomali algılama ve SCADA entegrasyonuna odaklandık. Kimlik doğrulama ve IEC 62351-8 rol yönetimi, hackathon sonrası yol haritamızın F-19 numaralı ilk maddesidir ve mimarimiz buna tam uyumlu tasarlanmıştır."*
