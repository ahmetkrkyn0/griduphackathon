# Pano/Hücre İçi Anomali Erken Uyarı ve Kestirimci Bakım Sistemi

**Grid Up Hackathon 2026** · ADM Elektrik Dağıtım & GDZ Elektrik Dağıtım · Patika.dev

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://typescriptlang.org)
[![Vite + React](https://img.shields.io/badge/Frontend-Vite%20%2B%20React-61dafb.svg)](https://react.dev)
[![TimescaleDB](https://img.shields.io/badge/Database-TimescaleDB%20(PostgreSQL%2016)-yellow.svg)](https://timescale.com)
[![MQTT](https://img.shields.io/badge/Broker-Eclipse%20Mosquitto-red.svg)](https://mosquitto.org)
[![Telegram Bot](https://img.shields.io/badge/Mobil%20Alarm-Telegram%20Bot%20API-0088cc.svg)](https://t.me/gridupalarmbot)
[![SCADA](https://img.shields.io/badge/SCADA-Modbus%20TCP%20%7C%20IEC%2060870--5--104-green.svg)](#aynı-değeri-üç-protokolden-kendiniz-okuyun)

1600 kVA'lık TEDAŞ tipi AG dağıtım panolarına ve OG hücrelerine kablo kalabalığını artırmadan eklenebilen, mevcut enerji analizörü ve ark korumasını sensör olarak kullanan, **fizik tabanlı öngörücü erken uyarı** üreten, tamamı şirket içinde (on-premise) çalışan endüstriyel izleme platformu.

> **Gizlilik:** Bu repo **private** kalmalıdır. `Hackathon Verileri/` ve proje konusu PDF'i "Hizmete Özel | Restricted" etiketlidir; sosyal medyada, public demo videolarında veya public bir repoda paylaşılmaz.

---

## 🧭 Jüri Kanıt Haritası

Dokuz değerlendirme kriteri → kanıt dosyası → o dosyada **ölçülmüş ve kanıtlanmış** sayı.

| # | Kriter | Kanıt Dosyası | Ölçülmüş Sayı / Çıktı |
|---|---|---|---|
| 1 | **Problemin Doğru Anlaşılması** | `docs/01-problem-analizi.md` · `docs/05-anomali-tespiti.md` §11 | Eşik sabitken aynı sağlıklı senaryoda çiy olayı kış **28,6** · geçiş **71,4** · yaz **0,0** olay/100 pano/gün (`scripts/threshold_sweep.py --seasons`). Sorun eşik seçimi değil; panonun mevsimsel fiziğidir. Eşiği kısmak yanlış alarmı azaltmaz, 0,5/0,0 çifti **228,6** olay/100 pano/güne çıkarır. |
| 2 | **Anomali ve Risk Tespit Başarısı** | `docs/12-dogrulama-sonuclari.md` §1–§2 · `libs/panoalgo/` | 8 anomali senaryosunun tamamında duyarlılık **1,00**, 10 senaryoda yasaklı alarm 0; S1'de sabit 70 K eşiğinden **158–209 saat (6.5–8.7 gün) önce** erken uyarı. EN 50160 güç kalitesi uyumu (harmonikler, gerilim çökmeleri/yükselmeleri). |
| 3 | **Saha Koşullarında Uygulanabilirlik** | `docs/12` §3 · `docs/08-kurulum-proseduru.md` · `docs/13-donanim-tasarimi.md` · `hardware/` | Sağlıklı panoda operatör yükü **71,4** yanlış alarm/100 pano/gün (sözleşme hedefi <150). DIN ray tipi modüler mekanik kutu (`hardware/mekanik/din-kutu.stl`), optik ark ve HF kısmi deşarj (PD) sensör kartı BOM ve blok diyagramları hazır. |
| 4 | **Uçtan Uca Sistem & Gerçek Bildirim** | `backend/app/notify/` · `docs/17-donanimsiz-dogrulama.md` §4.2 | `panosim` → MQTT → Ingest → TimescaleDB → REST API → WebSocket → UI canlı yığında, **karantina 0**. Alarmlar anında GSM modeme (SMS) ve **Telegram Bot API (`@gridupalarmbot`)** üzerinden teknik ekibin cep telefonuna zengin formatlı (HTML, RUL, tavsiye, link) teslim edilir. |
| 5 | **Mevcut Sistemlerle Entegrasyon (SCADA)** | `docs/04-iec104-haritasi.md` §9 · `docs/03-modbus-haritasi.md` §14 · `backend/app/scada/` | IEC 104 = REST API (**87 kontrol**) = Modbus FC03 (**139 adres**), **0 fark**; `conn_temp` 25 noktanın tamamında Modbus = API × 10, fark 0. Çift yönlü SCADA operasyonu (yetkili onay, mandallı alarm, uzaktan röle denetimi). |
| 6 | **Ölçeklenebilirlik** | `docs/09-olceklenebilirlik.md` §4–§5 · `backend/app/api/panels.py` | 1.000 panoda görünme p95 **657 ms**, kayıp **0**; toplu filo durumu ucu (`/api/v1/fleet/health`) ve sanallaştırılmış UI ile 1.000 panel anlık izlenebilir. TimescaleDB sıkıştırması **46–48×**. |
| 7 | **Kullanıcı / Operasyon Deneyimi** | `frontend/` · `docs/16-ux-tasarim.md` | WCAG 2.x kontrast **16,0:1**; 9 tam operasyon ekranı (Tekil Pano, Filo, Alarm Konsolu, 3D Termal Dijital İkiz, Olay Analizi / Kara Kutu, Trend & Korelasyon, Cihaz Sağlığı, Bölge Haritası, Ayarlar). Sesli ikaz chimes, CSV dışa aktarım, 96 ilçe coğrafi harita görünümü. |
| 8 | **Maliyet ve Fayda Analizi** | `docs/10-bom-maliyet-roi.md` · `hardware/` | Pano beyni kartı adet 1'de **~56 USD**, adet 1.000'de **~37 USD**; sensör düğümleri ve PD kartı dahil toplam pano başı retrofit maliyeti **<120 USD**. EPDK kesinti tazminat modeli (`scripts/tazminat_maruziyeti.py`) ile 1 engellenen yangında 14-22 ayda kendini amorti eder. |
| 9 | **Yenilikçilik & Fizik Tabanlı AI** | `docs/05` §3 · `firmware/` · `libs/panoalgo/` | Sabit eşik yerine Recursive Least Squares (RLS) ile dinamik ısıl direnç ($K/K_0$) öğrenimi. Saf C çekirdeği (`firmware/`) mikrodenetleyicilerde çalışacak şekilde derlenir, Python referansı ile farkı **<1.5e-8** mertebesindedir. |

---

## ⚡ Hızlı Başlangıç

### 1. Docker Yığınını Kaldırın (Tek Komut)

```bash
git clone https://github.com/ahmetkrkyn0/griduphackathon.git
cd griduphackathon
cp deploy/.env.example deploy/.env
docker compose -f deploy/compose.yaml up -d --build
```

Yığın ayağa kalktığında servisler şu adreslerde hazırdır:

| Arayüz / Servis | Yerel Adres | Açıklama |
|---|---|---|
| **Operasyon Arayüzü** | <http://localhost:3000> | Kontrol odası, 3D ikiz, alarm konsolu |
| **Backend REST API** | <http://localhost:8000/docs> | OpenAPI Swagger dokümantasyonu |
| **Grafana Mühendislik Panosu** | <http://localhost:3001> | Metrikler ve yük analizleri (`admin/gridup`) |
| **SCADA Modbus TCP** | `localhost:502` | Endüstriyel SCADA ağ geçidi (FC03 holding reg.) |
| **SCADA IEC 60870-5-104** | `localhost:2404` | RTU kontrollü istasyon bağlantısı |
| **MQTT Broker (Mosquitto)** | `localhost:1883` | Sensör telemetri ve olay iletim hattı |

Durdurma: `docker compose -f deploy/compose.yaml down` · Sıfırlama: `docker compose -f deploy/compose.yaml down -v`

---

## 📱 Telegram Anlık Alarm Botu (@gridupalarmbot)

Sistem, kritik alarmları (P1 / P2) sıfır gecikmeyle ve tamamen ücretsiz olarak teknik ekibin telefonuna iletir:

* **Telegram Bot:** [`@gridupalarmbot`](https://t.me/gridupalarmbot)
* **Özellikler:**
  - 🔴 **P1 Acil Müdahale** (Ark hatası, duman/TVOC tripi, aşırı bara sıcaklığı)
  - 🟠 **P2 Erken Uyarı** (Isıl direnç artışı, RUL tahminleri, çiy/yoğuşma riski)
  - ⏱ **Kalan Faydalı Ömür (RUL)** ve **Saha Mühendislik Tavsiyesi**
  - 🔗 Tek dokunuşla doğrudan ilgili panonun canlı web arayüzüne bağlantı
  - 👥 Tekil kullanıcı veya **Telegram Ekip Grubu** desteği (Tüm nöbetçi ekibe aynı anda bildirim)

### Kendi Telefonunuza Bağlama (1 Dakika)
1. Telegram'da [`@gridupalarmbot`](https://t.me/gridupalarmbot) adresini açıp **BAŞLAT (START)** deyin.
2. `@userinfobot` botundan Chat ID'nizi öğrenin.
3. `deploy/.env` dosyasında `TELEGRAM_CHAT_ID=<id>` değerini girip backend'i yeniden başlatın:
   ```powershell
   docker compose -f deploy/compose.yaml up -d backend
   ```

---

## 🎬 Arıza Senaryolarını Canlı Oynatma

Sistemdeki tüm fiziksel arıza dinamikleri Windows PowerShell veya Linux Bash üzerinden tek komutla canlı simüle edilebilir:

### Windows PowerShell ile:
```powershell
# S0: Normal sağlıklı gün (Filo yeşil kalır, çiy alarmı üretmez)
.\demo\senaryo\senaryo.ps1 -Scenario S0

# S1: Gevşek Bara Bağlantısı (K/K0 artışı, 158 saat önceden erken uyarı ve Telegram bildirimi)
.\demo\senaryo\senaryo.ps1 -Scenario S1

# S2: Aşırı Yükleme (Nominal akım aşımı, yanlış alarm önleme)
.\demo\senaryo\senaryo.ps1 -Scenario S2

# S4: TVOC-2 Optik Ark ve Kesici Açması (P1 acil alarmı, SMS + Telegram + Kara kutu)
.\demo\senaryo\senaryo.ps1 -Scenario S4

# S5: Koruma Kaybı / Sensör Arızası
.\demo\senaryo\senaryo.ps1 -Scenario S5
```

### Linux / macOS Bash ile:
```bash
./demo/senaryo/s0.sh     # Sağlıklı gün
./demo/senaryo/s1.sh     # Gevşek bağlantı
./demo/senaryo/s2.sh     # Aşırı yük
./demo/senaryo/s4.sh     # Ark olayı (TVOC-2 tripi)
```

---

## 🔍 Aynı Değeri Üç Farklı Protokolden Doğrulayın

GridUp'ın endüstriyel birlikte çalışabilirlik (interoperability) kanıtı: Aynı sensör verisini REST, Modbus TCP ve IEC 60870-5-104 üzerinden eşzamanlı ve sıfır tutarsızlıkla okuyabilirsiniz.

Yığın ayaktayken çalıştırın:

```bash
# 1 — Modbus TCP :502 (Holding Register 100-103)
python -c "from pymodbus.client import ModbusTcpClient; c = ModbusTcpClient('127.0.0.1', port=502); c.connect(); print(c.read_holding_registers(100, count=4, slave=1).registers); c.close()"

# 2 — REST API :8000 (Pano Detay Uç Noktası)
curl -s http://localhost:8000/api/v1/panels/ADM-00001 | python -c "import json, sys; p = {x['pt']: x['t_c'] for x in json.load(sys.stdin)['points']}; print([p[k] for k in ('GIRIS_L1', 'GIRIS_L2', 'GIRIS_L3', 'GIRIS_N')])"
```

**Sonuç Kanıtı:** Modbus okuması = REST okuması × 10 ($0.1\ ^\circ\text{C}$ tamsayı ölçeği), IEC 104 okuması = REST okuması. **Fark: 0.**

---

## 🛠 Donanım & Mekanik Tasarım Paketleri

Projede saha retrofitini hızlandıran ve TEDAŞ şartnamelerine uyum sağlayan açık donanım çıktıları:

* **Mekanik Kutu (3D STL):** [`hardware/mekanik/din-kutu.stl`](hardware/mekanik/din-kutu.stl) — Standart EN 50022 DIN rayına tırnaklı, alev geciktirici (UL94 V-0) uyumlu 6U pano kutusu.
* **Pano Beyni:** [`hardware/pano-beyni/`](hardware/pano-beyni/) — STM32F4 / ESP32-S3 mimarili ana kontrolcü, RS-485 izole hatlar, Ethernet ve LTE/GSM arayüzü.
* **Sensör Düğümü:** [`hardware/sensor-dugumu/`](hardware/sensor-dugumu/) — Bara bağlantı noktalarına geçmeli, $150\ ^\circ\text{C}$ dayanımlı NTC/dijital sensör kartı (BOM ve I/O planı).
* **Kısmi Deşarj (PD) Kartı:** [`hardware/pd-karti/`](hardware/pd-karti/) — Yüksek frekanslı akım trafosu (HFCT) ve geçici toprak gerilimi (TEV) analog ön-uç (AFE) tasarımı.

---

## 🧪 Testler ve Kod Kalitesi Doğrulama

Tüm modüller kapsamlı birim ve entegrasyon testleriyle güvence altındadır:

```bash
# Algoritma ve fizik motoru testleri (401 test)
cd libs/panoalgo && pytest

# Backend, veritabanı, SCADA, bildirim ve Telegram testleri (656 test)
cd backend && pytest

# Frontend testleri ve TypeScript tip doğrulaması (85 test, 0 hata)
cd frontend && npm test && npm run build

# Gömülü C çekirdeği doğrulaması (5/5 yeşil)
cmake -S firmware -B build && cmake --build build && ctest --test-dir build
```

---

## 👥 Ekip ve Rol Dağılımı

| Kulvar | İsim | Rol ve Sorumluluk Alanı |
|---|---|---|
| **Kulvar A** | **Tuna** | Fizik Modeli, Kenar Zeka Algoritmaları, Sentetik Veri & Senaryolar |
| **Kulvar B** | **Ahmet** | Platform Mimarisi, Ingestion, TimescaleDB, SCADA (Modbus/IEC 104), Telegram & Dağıtım |
| **Kulvar C** | **Berke** | Operasyon Arayüzü (React/Vite), 3D Termal İkiz, Donanım & STL Tasarımı, Teslimat |

---

> **GridUp Projesi**, dağıtım şebekesinde arıza gerçekleştikten sonra değil; **fiziğin başladığı ilk anda** operatöre haber vererek plansız kesintileri ve yangın risklerini sıfıra indirmeyi hedefler.
