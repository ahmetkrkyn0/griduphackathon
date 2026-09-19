# Pano/Hücre İçi Anomali Erken Uyarı ve Kestirimci Bakım Sistemi

**Grid Up Hackathon 2026** · ADM Elektrik Dağıtım & GDZ Elektrik Dağıtım · Patika.dev

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://typescriptlang.org)
[![Vite + React](https://img.shields.io/badge/Frontend-Vite%20%2B%20React-61dafb.svg)](https://react.dev)
[![TimescaleDB](https://img.shields.io/badge/Database-TimescaleDB%20(PostgreSQL%2016)-yellow.svg)](https://timescale.com)
[![MQTT](https://img.shields.io/badge/Broker-Eclipse%20Mosquitto-red.svg)](https://mosquitto.org)
[![Telegram Bot](https://img.shields.io/badge/Mobil%20Alarm-Telegram%20Bot%20API-0088cc.svg)](https://t.me/gridupalarmbot)
[![SCADA](https://img.shields.io/badge/SCADA-Modbus%20TCP%20%7C%20IEC%2060870--5--104-green.svg)](#-aynı-değeri-üç-farklı-protokolden-doğrulayın)

1600 kVA'lık TEDAŞ tipi AG dağıtım panolarına ve OG hücrelerine kablo kalabalığını artırmadan eklenebilen, mevcut enerji analizörü ve ark korumasını sensör olarak kullanan, **fizik tabanlı öngörücü erken uyarı** üreten, tamamı şirket içinde (on-premise) çalışan endüstriyel izleme platformu.

> **Gizlilik:** Bu repo **private** kalmalıdır. `Hackathon Verileri/` ve proje konusu PDF'i "Hizmete Özel | Restricted" etiketlidir; sosyal medyada, public demo videolarında veya public bir repoda paylaşılmaz.

---

## 🧭 Jüri Kanıt Haritası

Dokuz değerlendirme kriteri → kanıt dosyası → o dosyada **ölçülmüş ve kanıtlanmış** sayı.

| # | Kriter | Kanıt Dosyası | Ölçülmüş Sayı / Çıktı |
|---|---|---|---|
| 1 | **Problemin Doğru Anlaşılması** | `docs/01-problem-analizi.md` · `docs/05-anomali-tespiti.md` §11 | Eşik sabitken aynı sağlıklı senaryoda çiy olayı kış **28,6** · geçiş **71,4** · yaz **0,0** olay/100 pano/gün (`scripts/threshold_sweep.py --seasons`). Tek bir sabit eşik üç mevsimde birden çalışmıyor; eşiği kısmak yanlış alarmı azaltmaz, 0,5/0,0 çifti **228,6** olay/100 pano/güne çıkarır. **Ölçüm koşulu:** bu sonuç, üretecin iklim modelinin (`generator.py:96-97`, RH = 50 + 2·(40−T), tavan %98) bir özelliğidir — kış sıcaklıklarında nem tavanda kaldığı için çiy marjı negatife oturur. Gerçek saha verisiyle doğrulanmadı. Kurumun `İstenen Veriler.xlsx` ile istediği üç kalem koda döndü: mA sekonder + çarpan (`devices.py:223`), ABB TVOC-2 Modbus (`sim/tvoc2_sim.py`), HFCT/EA Technology PD (`contracts/alarm-codes.yaml:167`). |
| 2 | **Anomali ve Risk Tespit Başarısı** | `docs/12-dogrulama-sonuclari.md` §1–§2 · `libs/panoalgo/` | **Eşleşen modelde** (üreteç ile dedektör aynı denklemi çözer) 8 senaryonun tamamında duyarlılık **1,00**, yasaklı alarm 0. **Dedektörün varsaymadığı fizik eklendiğinde** (S10–S13: komşu terminal kuplajı, yüke bağlı τ, ikinci ısıl kutup, ölçüm zinciri doğrusalsızlığı) duyarlılık **0,88**'e iniyor ve yöntemin sınırı görünür oluyor: ölçüm sıkışmasında terminal gerçekte **78,90 K**'dayken ölçüm **48,48 K** gösteriyor, yani **sabit 70 K eşiği tamamen körleşiyor** — oran tabanlı K tespiti ise ayakta kalıyor. İkinci ısıl kutupta yayımlanan τ **9,5 kat** sapıyor ve sistem gerçekten arızalı noktayı "kalibrasyon şüpheli" diye **yanlış teşhis ediyor**. Dedektör bu iş için **değiştirilmedi**; amaç güçlendirmek değil sınırı ölçmekti (`docs/12` §1.1, `docs/14` §9). S1'de sabit 70 K eşiğinden **209 saat önce** erken uyarı — ama bu sayıyı tetikleyen kod `ALM-TTL-14D`, yani **tespit değil prognoz**; yalnızca K/K₀ eşiğine dayanan öne alma ~**172 saat**tir ve `docs/12` §2 artık tetikleyen kodu ayrı sütunda basar. Bu dosya elle yazılmaz: `python scripts/validate.py --out docs/12-dogrulama-sonuclari.md` tabloyu yeniden üretir. **Prognoz geri testini de aynı dosya yayımlar ve sonuç iyi değildir** (§4: S1 koni içinde %5,2, CRA −5,12) — RUL bir tahmindir, garanti değil. EN 50160 güç kalitesi değerlendiricisi (`libs/panoalgo/panoalgo/power_quality.py`, gerilim toleransı + %2 dengesizlik sınırı). L2 akran karşılaştırması ve değişim noktası ile K₀ körlüğü daraltıldı (**F-32**, kısmen). |
| 3 | **Saha Koşullarında Uygulanabilirlik** | `docs/12` §3 · `docs/08-kurulum-proseduru.md` · `docs/13-donanim-tasarimi.md` · `hardware/` | Sağlıklı panoda operatör yükü **71,4** yanlış alarm/100 pano/gün (sözleşme hedefi <150). DIN ray tipi modüler mekanik kutu (`hardware/mekanik/din-kutu.stl`, 324 üçgenlik ikili STL, `hardware/mekanik/din-kutu.scad`'den parametrik üretiliyor). **Ark tespiti için ayrı kart yoktur** — ABB TVOC-2'nin kendi optik sensörü Modbus'tan okunur (`docs/13` §204); ayrı kart olarak yalnızca **HF kısmi deşarj (PD)** kartı tasarlandı (`hardware/pd-karti/`, BOM + blok diyagram). Hücresel veri bütçesi ölçüldü (**F-36**, aşağıda) ve düğüm seri no/sapma kütüğü eklendi (**F-31**, kısmen). |
| 4 | **Uçtan Uca Sistem & Bildirim** | `backend/app/notify/` · `backend/app/journal_chain.py` · `docs/17-donanimsiz-dogrulama.md` §4 | `panosim` → MQTT → Ingest → TimescaleDB → REST API → WebSocket → UI canlı yığında, **karantina 0** (`GET /health` sayaçları + `quarantine` tablosu boş). Tek komutla 9 servis kalkar. Bildirim kanalları: **sanal GSM modem** (`scripts/virtual_gsm_modem.py` — gerçek donanım değil, simülatör; çıktı `deploy/runtime/sms-log.txt`), WhatsApp ve **Telegram Bot API** (`backend/app/notify/telegram.py` + `backend/tests/test_telegram.py`; **bot belirteci `.env`'de boştur, girilene kadar Telegram kanalı devre dışıdır**). Alarm yaşam döngüsü **kurcalama-kanıtı hash zincirine** yazılır (**F-20**): `scripts/verify_journal.py` bozulan satırı halka numarasıyla bulur. |
| 5 | **Mevcut Operasyon Sistemleriyle Entegrasyon** | `backend/app/scada/` · `backend/app/api/assets.py` · `backend/app/api/outages.py` · `backend/app/epdk.py` | **Üç ayrı operasyon sistemi sınıfına** arayüz var. **① SCADA:** IEC 104 = REST API (**87 kontrol**) = Modbus FC03 (**139 adres**), dokümante edilen 0,1 °C register ölçeğinde **fark 0**; `conn_temp` 25 noktanın tamamında Modbus = round(API × 10). Yazılabilir blok: yetkili onay, mandallı alarm sıfırlama, bakım kipi, test alarmı (röle kumandası **yoktur**, GK6). **② CBS/GIS:** `POST /api/v1/fleet/assets` ile CBS künyesi içe aktarılır — CBS kodu, fider, il/ilçe, abone sayısı, kritiklik, bakım vadesi (**F-21**). **③ OMS + mevzuat:** aynı fiderde eş zamanlı susan panolar tek kesinti olayına bağlanır (**F-22**), olaydan EPDK Kalite Yönetmeliği Madde 8 alanlarıyla **TASLAK** kesinti kaydı ve 72 saatlik kanıt zaman çizelgesi üretilir (**F-23**, sebep sınıfı öneri — karar değil). |
| 6 | **Ölçeklenebilirlik** | `docs/09-olceklenebilirlik.md` §4–§6 · `loadtest/fleet.py` · `backend/app/api/insights.py` | 1.000 panoda görünme p95 **657 ms**, kayıp **0** (ölçüm makinesi ve koşulları `docs/09` §3'te yazılı: i7-14700KF / Docker Desktop WSL2, yük üreteci **aynı makinede** — yani sonuçlar temkinli). Toplu filo durumu ucu `GET /api/v1/fleet/health` (`backend/app/api/insights.py`) + **sayfalanmış** listeler ile 1.000 panel izlenebilir (liste sanallaştırması kullanılmadı). TimescaleDB sıkıştırması **46–48×** (`deploy/initdb/005_compression.sql`; segmentby `pano_id, tag` — oran 1 günden eski parçalarda ölçülür). **F-36:** uyarlanabilir yayın ile mesaj sayısı 86.400 → 50.932 (**%41,0 bastırma**), pano başına aylık **1.071 MB → 632 MB**; **tespit 10 s'de kaldı**, arıza rejiminde dokuz alarm kodunun tamamı aynı turda çıktı. |
| 7 | **Kullanıcı / Operasyon Deneyimi** | `frontend/src/pages/` · `docs/16-ux-tasarim.md` | Gövde metni kontrastı **13,33:1** (`theme.css` `--ink #202b34` / `--bg #f5f6f8`; WCAG AAA eşiği 7:1). **Planlanan 9 ekranın 7'si çalışıyor** (`docs/16` §2): Filo, Tekil Pano (içinde 3D termal ikiz sekmesi), Alarm Konsolu, Olay Analizi / Kara Kutu, Trend & Korelasyon, Cihaz Sağlığı, Bölge Haritası. Kapsam dışı bırakılanlar: Ayarlar ekranı ve mobil PWA. Operasyon döngüsü kapalıdır: uyarı → **Neden / Ne doğrulanmalı / Ne yapmalı / Ne kadar acil** → Onayla/Rafa al → denetim izine kaydı. Sesli ikaz, CSV vardiya raporu, 96 ilçe coğrafi harita. |
| 8 | **Maliyet ve Fayda Analizi** | `docs/10-bom-maliyet-roi.md` · `hardware/*/bom.csv` · `scripts/tazminat_maruziyeti.py` | **Pano Beyni kontrolcü kartı**, `hardware/pano-beyni/bom.csv` satır kalemlerinin toplamı: **adet 1'de 70,73 USD**, **adet 1.000'de 47,68 USD** (hücresel modem dahil). **Pano başına toplam** (kontrolcü + N sensör düğümü, adet 1.000): **103,48 USD** (4 düğüm) – **145,33 USD** (7 düğüm) – **396,43 USD** (25 düğüm, sözleşmenin tamamı); N bir belirsizlik değil **yapılandırma seçimidir** ve sınırlarını `contracts/modbus-map.yaml` verir. Düğüm ve PD kartı BOM'ları (23,25 / 13,95 ve 19,80 / 11,79 USD) `hardware/` altında blok diyagramı + I/O tablosu + BOM üçlüsüyle **belgelidir** — ama **hiçbiri veri sayfasına karşı doğrulanmadı ve üretilmedi** (`docs/19` §3). Kurulum işçiliği, SIM/veri aboneliği ve tip test **hiçbir toplamda yoktur**. **Asıl tasarruf kalemi:** mevcut cihazlar sensör olarak okunduğu için 4 akım trafosu, 3 gerilim girişi, 2 ark dedektörü ve 1 ark koruma merkez ünitesi BOM'a **eklenmez** (`scripts/tazminat_maruziyeti.py` bunları listeler). **Geri ödeme bir aralık olarak yayımlanır, tek sayı olarak değil:** aynı betik `--duyarlilik` ile her girdiyi ±%50 oynatır. Ölçülen sonuç — geri ödemeyi belirleyen üç varsayımın (P(arıza) · arıza başı maliyet · tespit oranı) kaldıracı **birebir eşit** çıktı (1,33×), çünkü model çarpımsal; en büyük tek kaldıraç ise bir belirsizlik değil **düğüm sayısı seçimi** (4→25 arası geri ödemeyi 7,4 aydan 28,3 aya taşıyor). Maruziyet tarafında ölçülen yapısal sonuç: **tarifenin kaldıracı üstten 1,00× ile sınırlıdır** (kaldıracı tam olarak ÖTMSÜRE'nin toplamdaki payıdır), **eşiğe olan mesafeninki sınırsızdır** — altı parametre setinde 0,09×–3,57× ölçüldü. Yani "tarifeyi bilmiyorsunuz" itirazı bu hesabın baskın belirsizliği **olamaz**. (İlk yazdığımız *"sıralama değişmez"* iddiası **yanlıştı ve düzeltildi**; hikâyesi `docs/10` §7.4'te duruyor.) Tarife, yönetmelik eşiği ve kaçınılan kalem fiyatları hâlâ `veri yok` döndürür — *"betik bunları uydurmaz"* (`scripts/roi-ornek-parametreler.yaml`, üç sütun: değer/kaynak/güven). **OPEX:** ölçülen hacim **12,85 GB/pano/yıl** (bugün teslim edilen sabit 10 s davranışı) → **7,58 GB** (uyarlanabilir %2, **`--adaptive` ile açılır, varsayılan kapalı**). İkisi de **25 noktalı** panoda ölçüldü; tarife işletmecinin, ve gerçek fatura bu hacmin **üstünde** çıkar (altı sebebi `docs/10` §6.3'te sayılı). |
| 9 | **Yenilikçilik & Fizik Tabanlı AI** | `docs/05` §3 · `firmware/` · `libs/panoalgo/panoalgo/detect.py` | Sabit eşik yerine Recursive Least Squares (RLS) ile dinamik ısıl direnç ($K/K_0$) öğrenimi: canlı S1 koşumunda `ALM-K-WARN` 232. saatte, sabit 70 K eşikli `ALM-THR-TERM-ALM` 520. saatte çıkar — **288 saat erken**. **Kenar ile merkez kanıtlanmış biçimde aynı algoritmayı koşar:** saf C çekirdeği (`malloc` yok, sabit bellek) ile Python referansı ortak test vektörü üzerinde her adımda karşılaştırılır (`firmware/tests/test_rls.c`, 240 adım, K + τ + `excited`). Ölçülen en büyük göreli fark: `double` derlemede **1,36e-08**, gerçek MCU hedefi olan `float` derlemede **6,96e-06** (tolerans 1e-4; fark bilinçli bir hız/bellek takasıdır, `firmware/tests/test_rls.c` başlığında gerekçelendirilmiştir). Nokta başına bellek: **384 B** (double) / **196 B** (float) → 25 nokta = 9,4 KB. |

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
| **Backend REST API** | <http://localhost:8000/docs> | OpenAPI Swagger dokümantasyonu (sözleşme: `contracts/openapi.yaml`) |
| **Grafana Mühendislik Panosu** | <http://localhost:3001> | Metrikler ve yük analizleri (`admin/gridup`) |
| **SCADA Modbus TCP** | `localhost:502` | Endüstriyel SCADA ağ geçidi (FC03 holding reg.) |
| **SCADA IEC 60870-5-104** | `localhost:2404` | RTU kontrollü istasyon bağlantısı |
| **MQTT Broker (Mosquitto)** | `localhost:1883` | Sensör telemetri ve olay iletim hattı (anonim; **varsayılan demo yolu**) |
| **MQTT Broker — mTLS (F-27)** | `localhost:8883` | Yalnızca `--profile mtls` ile açılır; istemci sertifikası zorunlu, **cihaz başına topic ACL** (`docs/15` §5.1) |

Durdurma: `docker compose -f deploy/compose.yaml down` · Sıfırlama: `docker compose -f deploy/compose.yaml down -v`

mTLS profili (isteğe bağlı, **varsayılan kapalı**): `docker compose -f deploy/compose.yaml --profile mtls up -d mosquitto-mtls` — 8883, düz 1883'ün *yerine* değil **yanına** kalkar.

---

## 📱 Telegram Anlık Alarm Botu (@gridupalarmbot)

Sistem, kritik alarmları (P1 / P2) ücretsiz olarak teknik ekibin telefonuna iletebilir.

> **Varsayılan yığında bu kanal kapalıdır.** `deploy/.env` içindeki `TELEGRAM_BOT_TOKEN` **boş gelir** (bot belirteci bir sırdır, depoya commit edilmez). Belirteç girilene kadar alarmlar yalnızca SMS/WhatsApp kanallarına düşer; canlı bir alarmın `notified` alanında bunu görebilirsiniz. Kanalın kodu ve testi hazırdır: [`backend/app/notify/telegram.py`](backend/app/notify/telegram.py) · [`backend/tests/test_telegram.py`](backend/tests/test_telegram.py).

* **Telegram Bot:** [`@gridupalarmbot`](https://t.me/gridupalarmbot)
* **Özellikler:**
  - 🔴 **P1 Acil Müdahale** (Ark hatası, duman/TVOC tripi, aşırı bara sıcaklığı)
  - 🟠 **P2 Erken Uyarı** (Isıl direnç artışı, RUL tahminleri, çiy/yoğuşma riski)
  - ⏱ **Kalan Faydalı Ömür (RUL)** ve **Saha Mühendislik Tavsiyesi** — RUL bir tahmindir; geri testi `docs/12` §4'te yayımlanır ve şu an zayıftır (koni içinde %5,2)
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

# S1: Gevşek Bara Bağlantısı (K/K0 artışı, sabit eşikten 209 saat önce erken uyarı)
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

**Sonuç Kanıtı:** Modbus register'ı = `round(REST × 10)`, IEC 104 değeri = REST değerinin 0,1 °C'ye yuvarlanmışı. Üç taşıma da aynı bellek-içi `PanelImage`'ı, dokümante edilen **0,1 °C register ölçeğinde** yayınlar: `conn_temp` 25 noktanın tamamında **fark 0**. (Ölçek `docs/03` ve `docs/04`'te her nokta için tablolanmıştır; ham REST değeri iki ondalık taşır, taşıma katmanı onu register çözünürlüğüne indirir.)

---

## 🏛 Operasyon ve Mevzuat Yetenekleri

SCADA dışındaki entegrasyon yüzeyi. Her madde yığın ayaktayken tek komutla denenebilir.

### Rol tabanlı yetkilendirme (F-19)

Yazma uçları üç kademeli denetimden geçer: **belirteçsiz → 401**, **yetersiz rol → 403**, **doğru rol → 200**.

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/api/v1/alarms/1/ack            # 401
curl -s -X POST localhost:8000/api/v1/alarms/1/ack \
  -H "Authorization: Bearer ORNEK-izleyici-belirteci"                                          # 403 — rol yetersiz
curl -s -X POST localhost:8000/api/v1/alarms/1/ack -H "Content-Type: application/json" \
  -H "Authorization: Bearer ORNEK-operator-belirteci" -d '{"note":"kontrol"}'                  # 200
```

### Kurcalama kanıtlı denetim izi (F-20)

Alarmın her hâl değişimi (`raised → notified → acked`) bir **hash zincirine** yazılır; her halka bir öncekinin özetini taşır.

```bash
python scripts/verify_journal.py --dsn "postgresql://postgres:gridup@127.0.0.1:5432/gridup"
# ZINCIR SAGLAM - N halka dogrulandi

# Negatif test: bir satırı bozun, doğrulayıcı kaçıncı halkada durduğunu söylesin
docker exec gridup-timescaledb psql -U postgres -d gridup \
  -c "update alarm_journal set note='kurcalandi' where id=(select min(id) from alarm_journal);"
python scripts/verify_journal.py --dsn "postgresql://postgres:gridup@127.0.0.1:5432/gridup"
# ZINCIR KOPUK - halka N (alarm_journal.id=...): satirin icerigi ozetine uymuyor - satir DEGISTIRILMIS
```

### CBS / GIS varlık künyesi (F-21)

Pano artık yalnızca bir kimlik değil, **kimi etkilediğini** bilen bir varlık: CBS kodu, fider, il/ilçe, abone sayısı, kritiklik ve bakım vadesi. Mühendis rolü ister.

```bash
curl -s -X POST localhost:8000/api/v1/fleet/assets -H "Content-Type: application/json" \
  -H "Authorization: Bearer ORNEK-muhendis-belirteci" -d @scripts/ornek-cbs-aktarim.json
# {"guncellenen":3,"kapsama":{"panolar":6,"kunyeli":3,...}}
```

> Örnek dosya başında **"ÖRNEKTİR — GERÇEK CBS VERİSİ DEĞİLDİR"** yazar ve `uretici`/`seri_no` alanları bilerek boştur: gerçek aktarımda bu alanları CBS doldurur, biz uydurmayız.

### Kesinti olayı ve EPDK Madde 8 taslağı (F-22, F-23)

Aynı fiderde eş zamanlı susan panolar **tek kesinti olayına** bağlanır; olaydan EPDK Kalite Yönetmeliği Madde 8 alanlarıyla bir **TASLAK** kayıt ve 72 saatlik kanıt zaman çizelgesi üretilir.

```bash
# Kesinti olayları — panolar sessizleşip bağıntı kurulana kadar boş dizi döner
curl -s localhost:8000/api/v1/outages

# Bir olay oluştuktan sonra Madde 8 taslağını ve kanıt zaman çizelgesini okuyun
OID=$(curl -s localhost:8000/api/v1/outages | python -c "import json,sys; d=json.load(sys.stdin); print(d[0]['outage_id'] if d else '')")
[ -n "$OID" ] && curl -s "localhost:8000/api/v1/outages/$OID/epdk-kaydi" | head -c 400
```

> Sebep sınıfı bir **öneridir, karar değildir**; kaydı işletmeci onaylar. Mevzuat eşikleri, dağıtım bedeli ve ortalama talep depoda bulunmadığı için **tazminat tutarı hesaplanmaz** — uç yalnızca Madde 8 alanlarını ve kanıtı doldurur.

### Düğüm kütüğü ve akran karşılaştırması (F-31, F-32 — kısmen)

Düğüm kütüğü `POST /api/v1/fleet/nodes` ile doldurulur (varlık künyesiyle aynı desen); **kütük boşken uçlar boş liste döner** — uydurma seri no üretilmez.

```bash
curl -s localhost:8000/api/v1/fleet/nodes        # düğüm seri no, ardışık sapma, kalibrasyon vadesi
curl -s localhost:8000/api/v1/fleet/nodes/blind  # tabanı güvenilmez (kör) düğümler
```

> Kütük bir **kalibrasyon vade takibidir**; uç yanıtının içinde de yazdığı gibi, akredite bir kalibrasyon zinciri olmadan "izlenebilir ölçüm" iddiası kurulmaz.

### Hücresel veri bütçesi (F-36)

Uyarlanabilir yayın **varsayılan kapalıdır** (`--adaptive`); ölü bantlar `contracts/alarm-codes.yaml` eşiklerinden türetilir, sözleşmeye dokunulmaz.

```bash
python loadtest/veri_butcesi.py            # varsayılanlar aşağıdaki tabloyu birebir üretir
                                           # (5 pano × 25 nokta, 7 gün ısınma + 48 saat ölçüm, tohum 20260918)
python loadtest/veri_butcesi.py --hizli    # kısa bakış
```

| Politika | Mesaj | Pano başına aylık | Bastırma |
|---|---:|---:|---:|
| sabit-10 s (bugünkü davranış) | 86.400 | 1.071 MB | — |
| uyarlanabilir %1 | 81.350 | 1.009 MB | %5,8 |
| **uyarlanabilir %2** | **50.932** | **632 MB** | **%41,0** |
| uyarlanabilir %5 | 41.843 | 520 MB | %51,6 |
| uyarlanabilir %10 | 33.093 | 411 MB | %61,7 |

**Seyrelen yalnızca yayındır; tespit kenarda 10 saniyede koşmaya devam eder.** Arıza rejiminde dokuz alarm kodunun tamamı beş politikada da aynı turda yayınlandı. Geri kurma hatası hiçbir alanda ölü bandı aşmadı (en büyük 40,4 A / bant 41,6 A). Tahminimiz 6 kat azalma idi, ölçüm 1,70 kat çıktı — **tahmin sütunu silinmedi**, fark `docs/09` §6.1'e yazıldı.

---

## 🧭 Bilinçli Kapsam Sınırları (Dürüstlük Notu)

Sunumda da aynen böyle anlatılır. Sapmaların **tek kaynağı** `docs/17` §6, demo yığını ile üretim arasındaki farklar `docs/15` §5'tedir.

* **Donanım satın alınmadı.** Ölçüm uçları fizik tabanlı veri üreteciyle simüle edilir; merkez yazılımı ise sahadakiyle **aynı koddur**.
* **KiCad şeması yerine** blok diyagram + I/O tablosu + BOM üçlüsü seçildi (gerekçe: [`hardware/pano-beyni/README.md`](hardware/pano-beyni/README.md)).
* **Mobil PWA, devreye alma sihirbazı ve Ayarlar ekranı** bilinçli olarak kapsam dışı bırakıldı (`docs/16` §2). Planlanan 9 ekrandan **7'si** çalışır durumdadır.
* **Kısmen yapılanlar, "tamamlandı" diye sayılmaz.** Kimlik doğrulama (**F-19**) uçları role bağlar ama kurumsal SSO yoktur; düğüm kimliği ve sensör sapması (**F-31**) ile L2 akran karşılaştırması (**F-32**) kısmen uygulanmıştır. Hepsinin kalan işi `GELISTIRME-BACKLOGU.md` içinde madde madde yazılıdır.
* **Cihaz kimliği (IDevID/LDevID, sıfır-dokunuş kayıt, PKI işletimi) için YALNIZCA YOL HARİTASI vardır — kod yoktur** (**F-28**). Bugünkü mTLS sertifikaları elle üretilir (`scripts/sertifika-uret.sh`); otomatik kayıt, yenileme ve iptal listesi yazılmadı.
* **RUL (kalan faydalı ömür) tahmini zayıftır ve bunu kendimiz ölçüp yayımlıyoruz:** `docs/12` §4 geri testinde S1 için koni içinde kalma %5,2, CRA −5,12. Erken uyarı sinyali güçlüdür; ömür *sayısı* henüz güvenilir değildir.
* **Varsayılan demo yolu büyük ölçüde kimlik doğrulamasızdır.** 18 Eylül'de iki kez daraltıldı: REST yazma/onay uçları **operatör belirteci** ister (**F-19**) ve MQTT için ayrı bir **mTLS profili** vardır (**F-27**, `--profile mtls`, varsayılan kapalı, cihaz başına topic ACL). **Boşluk daraldı, kapanmadı:** okuma uçları, WebSocket, Modbus TCP (502) ve IEC 104 (2404) düz/açık kalır. Her iki durum da `GET /health` yanıtında görünür (`auth.enabled`, `mqtt_tls`) — gizlenmez.

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
# Algoritma ve fizik motoru testleri — 489 test, 0 atlanan
cd libs/panoalgo && pytest

# Backend, veritabanı, SCADA, bildirim ve Telegram testleri — 853 test
cd backend && pytest

# Frontend birim testleri ve TypeScript tip doğrulaması — 136 test, 0 hata
cd frontend && npm test && npm run build

# Gömülü C çekirdeği doğrulaması — 5/5 yeşil (gcc 13 önerilir)
cmake -S firmware -B build && cmake --build build && ctest --test-dir build
```

Backend'de **37 test veritabanı ister** ve DSN verilmezse atlanır (sessizce geçmez, `SKIPPED` olarak raporlanır). Yığın ayaktayken hepsini koşmak için:

```bash
# Tohumlayıcı münhasır bir veritabanı bekler: önce yazıcıları durdurun
docker compose -f deploy/compose.yaml stop panosim mpr-sim tvoc-sim backend
TEST_DB_DSN="postgresql://postgres:gridup@127.0.0.1:5432/gridup" pytest   # backend/ içinde → 890 test
docker compose -f deploy/compose.yaml start backend panosim mpr-sim tvoc-sim
```

**Dokümanın kodla tutarlılığı ayrıca sınanır** — bu dosyaların hiçbiri elle yazılmaz, hepsi `--check` ile denetlenir:

```bash
python scripts/check_contracts.py --check        # Modbus + alarm + OpenAPI çapraz tutarlılığı
python scripts/gen_modbus_doc.py --check         # docs/03 güncel mi
python scripts/gen_iec104_doc.py --check         # docs/04 güncel mi
python scripts/gen_alarm_doc.py --check          # docs/06 güncel mi
python scripts/gen_grafana_dashboards.py --check # Grafana panoları güncel mi
python scripts/sir_taramasi.py                   # sır/sızıntı taraması (472 izlenen dosya)
python scripts/validate.py --out docs/12-dogrulama-sonuclari.md   # §1-§4 tablolarını yeniden üretir
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
