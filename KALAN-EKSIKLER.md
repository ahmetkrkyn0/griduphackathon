# Kalan Eksikler — Üç Dal `main`'de Birleştikten Sonra

> **Tarih:** 15 Eylül 2026, 00:15 · **Baz:** `main` = `5c969d1` (GitHub'daki `origin/main` ile aynı commit)
> **Kapsam:** Birleştirmeden sonra `main` üzerinde yapılan doğrulamada bulunanlar + `PLAN.md`'de açık kalanlar.
> **Takvim:** Özellik dondurma **17 Eylül 23:59** (≈3 gün) · M4 18 Eylül · M5 19 Eylül · Teslim hedefi **20 Eylül 18:00**, son sınır 23:59.
> **Not:** Bu dosya commit **edilmedi**. Jüriye gidecek repoda iç çalışma notu durmasın diye; paylaşmak isterseniz ayrıca karar verin.

**Sahipler:** A = Tuna (fizik, kenar, algoritma) · B = Ahmet (platform, entegrasyon, ölçek) · C = Berke (arayüz, donanım, teslim)
**Öncelik:** 🔴 kritik (demoyu ya da teslimi doğrudan bozar) · 🟠 yüksek (17 Eylül dondurmasından önce) · 🟡 orta (M4–M5) · ⚪ düşük

---

## 1. Birleştirme özeti

- `ahmet/backend` → `d286a88`, `berke/frontend` → `f5d5f5c`, `tuna/veri-ureteci` → `5c969d1`. Üçü de `--no-ff` merge commit; kişi bazlı geçmiş korundu.
- Metin çakışması **yalnızca `PLAN.md`'de** çıktı, iki bölgede. İkisi de birleşim olarak çözüldü:
  - **Faz 4 kutucukları:** T4.1/T4.2 (A) ile T4.3 (B) komşu satırdaydı. Üçü de `[x]` olarak birleştirildi.
  - **Günlük Kayıt tablosu:** üç dal da tablonun sonuna satır eklemişti. Hiçbir satır atılmadı; commit saatine göre kronolojik sıra korundu (B 13 Eyl akşam → B 13–14 gece → C 14 Eyl ×2 → A 14 Eyl → akşam → gece).
  - **Makineyle kontrol:** her dalın eklediği her satır sonuçta var, sildiği satır yok (1187 + 4 + 3 = 1194 satır).
- Başka dosyada örtüşme yoktu. `berke/frontend` zaten `ahmet/backend`'in tamamını içeriyordu; `tuna/veri-ureteci` ile diğerlerinin tek ortak dosyası `PLAN.md`'ydi.
- `origin/main`, 14 Eylül 23:38'de `5c969d1`'e push edildi (reflog: "update by push").

## 2. Doğrulama sonuçları (`main` = `5c969d1` üzerinde)

| Katman | Nasıl koşuldu | Sonuç |
|---|---|---|
| Backend (B) | `cd backend && TEST_DB_DSN=postgresql://postgres:gridup@localhost:5432/gridup .venv/Scripts/python -m pytest` | **580/580** (22 gerçek TimescaleDB testi dahil) |
| `libs/panoalgo` (A) | `cd libs/panoalgo && pytest`; ortam `pip install -r sim/requirements.txt` | **331/331** |
| Firmware C çekirdeği (A) | Ubuntu 24.04 / gcc 13.3: `cmake -S firmware -B b && cmake --build b && ctest --test-dir b` | `double` **5/5**, `-DPANO_USE_FLOAT=ON` **5/5**; `-Wall -Wextra -Wpedantic` uyarısız |
| Frontend (C) | `npm ci && npm test && npm run build` | **71/71**; `tsc` + `vite build` başarılı |
| `docs/12` yeniden üretim (T4.2) | `python scripts/validate.py --out <geçici>` + `diff` | Üretim zamanı satırı dışında **birebir aynı** |
| Compose yapılandırması | `docker compose -f deploy/compose.yaml config` | 9 servis, host port çakışması yok |
| Canlı yığın | `docker compose up -d --build` + duman testi | **15/16** (tek başarısız: K4) |
| Arayüz gerçek API ile | Playwright: Filo, Pano detay, Alarmlar, Trend, Kara kutu, Cihaz sağlığı, Bölge | 7 ekran, **0 konsol hatası / uyarısı** |
| Git hijyeni | index'te CRLF, izlenen dosyalarda sır taraması | 0 CRLF; yalnızca testlerdeki sahte `+90555000000x` numaraları |

> **19 Eylül notu — yukarıdaki tablo DEĞİŞTİRİLMEDİ, çünkü o `main` = `5c969d1` anının kaydıdır.**
> Sayılar bugün geçerli değil; güncel değerler için `README.md` "Testler" bölümü ve
> `docs/17` §4 tablosu esastır. İki satır özellikle eskidi ve okuyucu yanılmasın diye
> buraya yazılıyor:
>
> - **Frontend "71/71"** → 19 Eylül ölçümü **154/154** (17 dosya, vitest 2.1.9). Aradaki
>   zincir 71 → 85 → 136 → 154; son artış K7/7.1 bileşen testlerinden geliyor.
> - **"Arayüz gerçek API ile · 7 ekran, 0 konsol hatası / uyarısı"** → o gün **doğruydu ama
>   tezgâhı depoda yoktu**, yani bir iddiaydı. 19 Eylül'de tezgâh eklendi
>   (`frontend/playwright.config.ts` + `frontend/e2e/smoke.spec.ts`) ve **ölçüm bir kusur
>   buldu**: kara kutu ekranı (`/olay/:id`) React #310 ile tamamen boş çıkıyordu, yani 7
>   ekranın 6'sı hatasızdı. Kusur düzeltildi, testle kilitlendi, ölçüm yenilendi ve **10
>   rotada 0 hata / 0 uyarı** çıktı. Aynı koşu ayrıca **canlı kipte 23 kontrast ihlali**
>   ölçtü — o gün hiç ölçülmemiş bir şeydi.
>
> **D5 maddesi (§6) bu işle kısmen kapandı:** `assets/ekran/` görüntülerini artık spec
> üretiyor. Görüntüler hâlâ **örnek veri kipinde** alınıyor; canlı yığından üretmek için
> `GRIDUP_E2E_KIP=canli GRIDUP_E2E_EKRAN=1 npx playwright test` yolu açık bırakıldı ama
> **bu oturumda koşulmadı ve commit edilen görüntüler örnek veri kipindendir.**

**Canlı duman testinin ayrıntısı:**
- A'nın `panosim`'i → mosquitto → B'nin ingest'i → TimescaleDB:
  - karantina 0;
  - `ADM-00001..3` API'de görünüyor;
  - kenar alanları (`k_ratio`, `risk`, `q`) pano detayına ulaşıyor.
- Modbus TCP :502, `conn_temp` 25 noktanın tamamında API `t_c × 10` ile aynı (fark 0).
- IEC 104 :2404 STARTDT act → con.
- MPR-53CS sim :5020 CT = 500, L1 akımı okunuyor.
- Frontend `nginx` üzerinden API ve WebSocket'e ulaşıyor (101 Switching Protocols).
- Grafana çalışıyor.
- Faz 0'dan kalan `GDZ-00001` için `ALM-COMMS-LOST` alarmı oluştu ve konsolda "Neden / Ne yapmalı / Ne kadar acil" alanlarıyla göründü. Haberleşme kopması mekanizması çalışıyor.

**Bu oturumda doğrulanMAyanlar:**
- sıfırdan `git clone` ile temiz makine testi (T4.4),
- gerçek telefona WhatsApp,
- 1.000 pano yük testinin tekrarı,
- `s7`/`s8` betiklerinin çalıştırılması,
- arayüzün arıza senaryosu verisiyle (S1–S6) görünümü.

Son maddedeki veri üretilemiyor, bkz. K1.

---

## 3. 🔴 Kritik

### K1 — Senaryo oynatma yok; `s0`–`s6` demo betikleri birleşmeden sonra hata veriyor · **A + C**
- **Kanıt:**
  - `sim/panosim.py` yalnızca normal üreteç verisi yayınlıyor. Argümanları `--mqtt --panels --period --speed --seed --prefix --start --max-messages --profile --dry-run`; senaryo ya da arıza enjeksiyonu yok.
  - `panoalgo.scenarios` CSV ve etiket üretiyor (`data/fixtures/`), ama bunları MQTT'ye basan bir araç yok.
- **Birleşmenin etkisi:**
  - `demo/senaryo/_ortak.sh:30-32` (`panoalgo_var_mi`) eskiden "A'nın işi yok" uyarısı veriyordu. Dosyalar artık `main`'de olduğu için kontrol geçiyor.
  - Betik şuna düşüyor: `panosim.py: error: unrecognized arguments: --scenario S0_normal --pano SIM-00001 --duration 60`
  - `s1` `--point`, `s5` `--detector` bayrağını da bekliyor.
- **Neyi engelliyor:**
  - S1 (gevşek bağlantı), S3 (yoğuşma), S4 (ark), S5 (koruma sağlığı) canlı demosu;
  - video kurgusu (T5.3: S0 → S1 → S3 → S4 → S5);
  - arıza senaryolarının gerçek yığın ekran görüntüleri.
- **Mevcut kısmi araç:** `tvoc-sim` üzerinde `--trip-after` ve `--sensor-error` bayrakları var, ama bunlar yalnızca Modbus düzeyinde gösterim sağlar. Depoda cihaz simülatörlerini okuyan hiçbir Modbus istemcisi olmadığı için olay MQTT'ye ve alarma akmaz (bkz. Y2).
- **Yapılacak:**
  - [ ] **A:** `data/fixtures/*.csv` ya da `scenarios.build()` çıktısını MQTT'ye oynatan bir mod yazmalı. Öneri: `sim/replay.py` veya `panosim --scenario`. `ts` duvar saatine hizalanmalı (K3).
  - [ ] **C:** betikleri gerçek CLI'ya bağlamalı. `_ortak.sh` kontrolü "dosya var mı" yerine "senaryo modu destekleniyor mu" olmalı; bu yapılana kadar eski dürüst uyarı korunur.
  - [ ] **A + C:** bayrak adlarını birlikte sabitlemeli (`--scenario`, `--pano`, `--duration`, `--point`, `--detector`).

### K2 — Jüriye giden metinler birleşmeden sonra yanlış bilgi veriyor · **C (README, sunum, demo) + B (docs/17)**
Her dal kendi içinde doğruydu; `main`'de artık yanlış olan ifadeler:
- [ ] **`README.md` (C):**
  - Satır 39, 40 ve 42: "Kişi A, henüz başlamadı", "firmware bekliyor", "s0–s6 A'nın simülatörünü bekliyor".
  - Satır 47–52: "En büyük açık risk: A kulvarı henüz başlamamış görünüyor".
  - Satır 61–64: `libs/panoalgo`, `firmware/`, `sim/`, `data/` için "*henüz yok*".
  - Satır 71: "17 dokümandan 15'i hazır".
  - **Gerçek durum:** A'nın bütün dizinleri `main`'de ve 18 doküman dosyasının (01–17 + 07b) hepsi mevcut. Jüri README'yi ilk açtığında "prototip eksik" okuyacak.
- [ ] **`demo/sunum/sunum-taslagi.md` (C):**
  - Satır 35 ve 37: "(A tamamlandığında)".
  - Satır 40–42: "A kulvarı henüz tamamlanmadı".
- [ ] **`demo/senaryo/README.md` (C):** satır 7–13 ve 21–26, "A'nın simülatörünü bekliyor". K1 çözülünce güncellenmeli.
- [ ] **`docs/17-donanimsiz-dogrulama.md` (B):**
  - Satır 4–6, 26–29, 37, 41, 46, 54, 63, 73 ve §6: A ve C satırları "bekliyor", "Son güncelleme 13 Eylül".
  - Kanıt listesi Y3'te.
- Tarihsel kayıtlar (`PLAN.md` T5.1 sapma notu, Berke'nin 14 Eyl günlük satırı, `STATUS.md` §0.1) o anın doğrusudur, silinmemeli. İstenirse altına "birleşmeyle çözüldü" notu düşülebilir.

### K3 — Simüle zaman damgası duvar saatinin önüne geçiyor · **Karar: A + B + C**
- **Neden:** `deploy/compose.sim.yaml` varsayılanı `SIM_SPEED=60`, `SIM_PERIOD_S=10`. Her gerçek dakika 60 simüle dakika ediyor ve yayınlanan `ts` simüle zaman (Tuna'nın 14 Eylül "karar gerekiyor" notu).
- **Ölçüldü:** yığın 11 dakika çalıştıktan sonra `ADM-00001`'in en yeni `ts`'si duvar saatinden **10,5 saat ileride**; **11.757 satır** geleceğe tarihli.
- **Etkisi:**
  - Trend, K trendi ve çiy noktası grafikleri `to = new Date()` penceresi kullanıyor (`frontend/src/pages/TrendKorelasyon.tsx:52`). Yeni veri grafiğe girmiyor ve demo uzadıkça fark büyüyor.
  - Kara kutu pencereleri ve `ts` tabanlı sıkıştırma politikası da aynı sorundan etkilenir.
  - `last_seen` ve `ALM-COMMS-LOST` alındı zamanını kullandığı için etkilenmiyor (doğrulandı).
- **Seçenekler:**
  - (a) Fizik hızlandırılmış kalsın ama yayında duvar saati `ts`'si kullanılsın.
  - (b) Canlı demoda `SIM_SPEED=1`.
  - (c) Arıza senaryoları K1'deki oynatma ile gösterilsin.
- [ ] Kararı verip `compose.sim.yaml` ve `docs/14`'e yazın.

### K4 — TVOC-2 simülatörü ID 248'de "sessiz" değil · **A**
- **İddia:** PLAN TA3 kabul kriteri, `docs/17` DH4 ve `tvoc2_sim.py` logu "hiçbir isteme cevap yok, istisna bile dönmez" diyor. Jüri demosunda vurgulanan bir nokta.
- **Ölçülen:**
  - Ham Modbus TCP FC03 (birim 248, PDU 1300) → `0x83` istisna, **kod 11** (Gateway Target Device Failed to Respond).
  - Konteyner logunda "istisna bile donmez" satırının hemen ardından `Exception Response(131, 3, GatewayNoResponse)` yazıyor.
- **Kök neden:**
  - pymodbus 3.7.4 `server/async_io.py:196-200`: bilinmeyen birimde `ignore_missing_slaves=False` (varsayılan) ise `GatewayNoResponse` döner.
  - `sim/tvoc2_sim.py:135` `StartTcpServer(...)` bu parametreyi vermiyor.
- **Seçenekler:**
  - [ ] **Kodu düzelt:** `StartTcpServer(..., ignore_missing_slaves=True)` + sunucu düzeyinde "zaman aşımı, cevap yok" testi + canlı tekrar.
  - [ ] **Ya da metni düzelt:** davranışı koru, metinleri "ağ geçidi istisnası 0x0B" diye güncelle. Gerçek bir RS485→TCP ağ geçidi de sessiz cihaz için 0x0B döndürür.

### K5 — Merkez dedektör bağlı değil (TB2 Adım 4) · **B**
- **Kanıt:**
  - `backend/app/main.py:72` `AlarmService(contracts, active_store, hub, clock=clock)` çağrısına `detector` verilmiyor.
  - Kanca hazır: `alarm_service.py:55` dedektörü alıyor ve `:61`'de `RiskEngine`'e aktarıyor.
  - Uygulama hazır: `libs/panoalgo/panoalgo/central.py` (`CentralDetector`, B'nin Protocol'üne uyuyor, istisna sızdırmıyor, DQ ve COMMS kodlarını bilerek dışarıda bırakıyor).
- **Engel:** backend imajının build context'i `backend/`. `backend/Dockerfile` yalnızca `app/`'i kopyaladığı için imajda `libs/panoalgo` yok.
- **Yapılacak:**
  - [ ] Build context'i repo köküne al, `COPY libs/panoalgo` + `pip install --no-deps` ekle (`sim/Dockerfile`'daki desen).
  - [ ] `main.py`'de `detector=CentralDetector()` ver.
  - [ ] Test ortamında `panoalgo`'yu yola ekle; bir entegrasyon testi yaz.
- **Dikkat:** Y5'teki eşik önerisi onaylanmadan bağlanırsa kenar ve merkez türetilmiş varsayılanları kullanır. İkisi de aynı `limits.evaluate`'i çağırdığı için tutarlı olur, ama sayılar sözleşmede değil kodda kalır.

---

## 4. 🟠 Yüksek (17 Eylül 23:59'dan önce)

### Y1 — Taban öğrenme canlı demoda ≈2,8 gerçek saat sürüyor · **A (demo planı)**
- **Neden:** `contracts/alarm-codes.yaml:236` `baseline_learning_days: 7` → 168 simüle saat. `--speed 60 --period 10` ile bu 1.008 tur × 10 s ≈ **2,8 saat** eder; bu sürede K/K₀ = 1,0 kalır. `panosim` logu ve arayüzdeki "Taban öğrenme 1. gün" bunu doğruluyor.
- [ ] Canlı yığında L1 (K/K₀) alarmı gösterilecekse iki yol var: önceden ısıtılmış bir volume ile başlamak ya da K1'deki oynatmayı kullanmak.

### Y2 — TA3 Adım 6'nın taşıma katmanı yok; `sim/panobeyni_sim.py` hiç yazılmamış · **A**
- **PLAN beklentisi:** TA3 Adım 6 `[x]` işaretli. Adım "sanal seri porttan Modbus master döngüsü, Modbus slave sunumu, MQTT yayını, 7 günlük halka tampon" istiyor. Kabul kriteri: "`panobeyni-sim` çalışırken MQTT'de telemetri akıyor".
- **Durum:**
  - `firmware/host/main.c` stdin'den ölçüm okuyup register tablosunu stdout'a JSON olarak basıyor. Kapsam kararı dosyanın başında dürüstçe yazılı.
  - Başlıktaki `main.c:13` taşıma katmanı için `sim/panobeyni_sim.py`'yi gösteriyor, ama bu dosya **hiçbir dalda hiç var olmamış**.
  - Depoda Modbus istemcisi yok: `mpr-sim`/`tvoc-sim` tek başına duruyor.
  - Halka tampon yok.
- **Seçenekler:**
  - [ ] **İnce taşıma kabuğunu yaz:** cihaz simülatörlerini Modbus TCP ile oku → çekirdek/boru hattı → MQTT.
  - [ ] **Ya da kapsamı küçült:** `main.c` atfını, PLAN kutucuğunu (sapma notuyla) ve `docs/17` DH2 metnini güncelle. DH2 "sanal seri port üzerinden gerçek Modbus konuşur" diyor.

### Y3 — `docs/17`'yi A ve C kanıtlarıyla doldur · **B**
- [ ] **A kanıtları** (hepsi ölçülmüş, dosyaları `main`'de):
  - 331 Python testi; 5 C testi hem `double` hem `float` derlemede.
  - C↔Python farkı K 1,36e-8 / τ 1,42e-8, eşik 1e-6 (`firmware/akis-diyagramlari/ana-dongu.md`).
  - S1'de K/K₀ 1,6 eşiği 70 K'dan **209 saat** önce aşılıyor (kriter 48 saat).
  - Recall 1,00 tüm senaryolarda; S0 yanlış alarm 71,4/100 pano/gün (sınır 150).
  - `docs/12` betikle birebir yeniden üretilebiliyor.
  - MPR-53CS CT = 500 ve L1 dönüşümü.
  - Renode/Wokwi atlandı (Should); bellek 320 B/nokta sapması gerekçeli.
  - TVOC-2 ID 248 satırı K4 çözülene kadar "doğrulanmadı" kalmalı.
- [ ] **C kanıtları:**
  - blok diyagram + I/O tablosu + BOM (KiCad yok, Y6), yerleşim SVG, `din-kutu.scad` (STL yok);
  - 9 ekranın 7'si, `docs/16`.
- [ ] **Birleşik kanıt:** §2'deki canlı duman testi (Modbus = API × 10, 25 nokta, fark 0; karantina 0; 7 ekran gerçek API'de hatasız).
- [ ] §6 "Açık kalanlar" tablosunu bu listeyle değiştir, "Son güncelleme" tarihini düzelt.

### Y4 — T4.4 temiz makine testi ve demo öncesi veritabanı temizliği · **B**
- [ ] Sıfırdan `git clone` → `cp deploy/.env.example deploy/.env` → `docker compose -f deploy/compose.yaml up -d --build` → 5 dakikada çalışan sistem. Bu oturumdaki doğrulama mevcut makinede, var olan volume'larla yapıldı.
- [ ] Yerel veritabanlarında Faz 0 `hello_publisher`'ından kalan `GDZ-00001` duruyor. Filoda "1 pano ilgi bekliyor" ve `ALM-COMMS-LOST` üretiyor; ayrıca K3'teki ileri tarihli satırlar var. Demo ve ekran görüntüsü öncesi `docker compose -f deploy/compose.yaml down -v` ile temiz başlatın. Bu, B'nin 13 Eylül notundaki `005_compression.sql` ve `shm` ayarını da kapsar.

### Y5 — Sözleşme değişiklik önerileri onaysız · **A + B + C**
- [ ] **`contracts/changes/2026-09-14-eksik-esikler.md` (A önerdi):**
  - `dq_below_ambient_deadband_k: 1.0`
  - `neutral_current_ratio_warn: 0.30`
  - `neutral_thd_warn_pct: 15.0`
  - `ALM-PD-TREND` için kapsam notu
  - `excitation_min_cv_i2: 0.02`
  - Onaylanmazsa türetilmiş varsayılanlar kodda kalır (`quality.py`, `detect.py`, `fusion.py`).
- [ ] **`contracts/changes/2026-09-14-fleet-health-bulk.md` (C önerdi):** `GET /api/v1/fleet/health`. PLAN Bölüm F "Faz 3'ten sonra sözleşme değişmez" diyor. Ya şimdi onaylanıp B uygulamalı ya da bilinçli olarak sonraki sürüme bırakılmalı.
- İki dosyada da hiçbir onay kutusu işaretli değil.

### Y6 — KiCad şema PDF (MoSCoW **Must**) ve STL yok · **C + ekip kararı**
- **Beklenti:** MoSCoW Must "KiCad şema PDF + I/O tablosu + BOM", Faz 6 kontrol listesi "şema PDF".
- **Mevcut:** `hardware/pano-beyni/blok-diyagrami.md`, `io-tablosu.md`, `bom.csv`. KiCad yerine bu seçimin gerekçesi `hardware/pano-beyni/README.md`'de.
- **STL:** `hardware/mekanik/din-kutu.scad` var, STL yok. OpenSCAD kurulu bir makinede `openscad -o din-kutu.stl din-kutu.scad` yeterli.
- [ ] **Karar:** KiCad kurulu ve internetli bir makinede şema çizilecek mi, yoksa sapma README, `docs/17` ve sunumda açıkça mı savunulacak?

### Y7 — Demo betikleri Windows host'a hazır değil · **C**
- [ ] Betikler `python3` çağırıyor (`s0`–`s7`). Bu makinede `python3` → "Python bulunamadı" (Windows Store kısayolu); ekibin üçü de Windows'ta. Öneri: `PYTHON="${PYTHON:-python3}"` ile değiştirilebilir yorumlayıcı ya da `py -3` / `python` geri dönüşü.
- [ ] Host'ta `panoalgo` kurulu değil. Betik README'sine kurulum adımı eklenmeli: `pip install -r sim/requirements.txt && pip install -e libs/panoalgo`. Alternatif: betikleri `docker compose run` ile konteynerde koşturmak.

### Y8 — `loadtest/fleet.py` hâlâ kendi şablon üretecinde · **B**
- [ ] `loadtest/fleet.py:11` "panoalgo üretecine geçiş A'nın paketi geldiğinde eklenecek" diyor; PLAN TB3 Adım 4 "A'nın kodunu kütüphane olarak import et" istiyor. Paket artık `main`'de. Geçilmezse `docs/09` ve `docs/17`'deki "değerler fiziksel değil" notu korunmalı.

### Y9 — `libs/panoalgo` test bağımlılığı eksik bildirilmiş · **A**
- **Ölçüldü:** yalnızca `pyproject.toml`'daki `[test]` extras ile kurulan temiz ortamda `tests/test_scenarios.py`'deki 27 test `ModuleNotFoundError: pandas` ile düşüyor. `sim/requirements.txt` ile 331/331 geçiyor.
- [ ] `pandas==2.2.*`'yi `[test]` extras'a ekle ya da README'de kurulumu `pip install -r sim/requirements.txt` olarak yaz.

---

## 5. 🟡 Orta (M4 18 Eylül – M5 19 Eylül)

- [ ] **O1 — Video (T5.3, hep):**
  - 3–5 dk, 2 tam çekim; `demo/video/` şu an boş (`.gitkeep`).
  - S1/S3/S4/S5 kesitleri **K1'e bağlı**.
  - Komitenin gizli dokümanları kadrajda olmayacak.
- [ ] **O2 — İki prova (T5.4, hep):** biri süreli, biri soru-cevaplı. Rapor §13'teki 17 jüri sorusu paylaşılacak: fizik → A, entegrasyon/ölçek/güvenlik → B (cevaplar `docs/17` §5'te), saha/maliyet/UX → C.
- [ ] **O3 — Yedek plan (T5.5, B):** internetsiz demo; WhatsApp düşerse sanal modem kaydı (`deploy/runtime/sms-log.txt`) ekranda; canlı demo patlarsa video hazır.
- [ ] **O4 — Gerçek telefona WhatsApp (B / Ahmet):** Meta test numarası + token + doğrulanmış alıcı gerekiyor (`docs/17` DH5).
- [ ] **O5 — Gereksinim kapsama kontrolü (T4.8, hep):** PLAN Bölüm E, R1–R17. Riskli olanlar: R1 (uçtan uca arıza senaryoları → K1), R2/R3 (STL, KiCad → Y6), R4 (MCU kodu + akış diyagramı → Y2).
- [ ] **O6 — Sır taraması (T4.7, hep):** son commit'ten önce PLAN'daki geçmiş taraması tekrar koşulmalı: `git log --all -p | grep -iE "token|password|\+90|api[_-]?key"`. Bu oturumda çalışma ağacı taraması temizdi.
- [ ] **O7 — Sunum dosyası (C):** `demo/sunum/sunum-taslagi.md` → sunum destesi + PDF kopyası (Faz 6). Rakamlar `docs/09`, `docs/12` ve Y3'teki ölçümlerden alınmalı.
- [ ] **O8 — Faz 6 teslim kontrol listesi (hep):**
  - teslim platformu ve formatı teyidi;
  - repo erişiminin jüri gözüyle testi (gizli pencere / başka hesap);
  - public link istenirse `Hackathon Verileri/` ve proje PDF'i olmadan temiz repo (dosya silmek geçmişten silmez);
  - iç çalışma dosyalarının (`STATUS.md`, `frontend/TASARIM-REVIZYONU.md`, bu dosya) teslim reposunda kalıp kalmayacağı kararı.

---

## 6. ⚪ Düşük / defter tutma

- [ ] **D1 — Yapılmış ama işaretlenmemiş kutucuklar:**
  - Faz 0 T0.1–T0.6 adımları ("Faz 0 durumu" tablosunda ✅).
  - TC1 Adım 1–6 (Berke'nin 14 Eylül kaydı: "önceki oturumda commit edildi").
  - Faz 0 kalanları (komiteye 5 soru, `contracts/` onayı): yapıldıysa işaretleyin, yapılmadıysa komite soruları O8'deki teslim formatı teyidiyle birleştirilebilir.
- [ ] **D2 — Handle'lar:** `CODEOWNERS` hâlâ `@kisi-a/b/c` yer tutucusu kullanıyor; PLAN Bölüm G'de A ve C'nin GitHub handle'ları boş (`@_____`).
- [ ] **D3 — `scripts/validate.py` sahipliği:** CODEOWNERS `/scripts/`'i B'ye veriyor, PLAN T4.2 dosyayı A'ya atıyor (dosya başındaki not). Ya B sahiplenir ya da `python -m panoalgo.validate` kullanılıp dosya kaldırılır.
- [ ] **D4 — Sunumda söylenmesi gereken bilinçli sapmalar:**
  - 9 ekranın 7'si (mobil PWA ve devreye alma sihirbazı Won't).
  - Cihaz Sağlığı pano başına istek atıyor (6 eşzamanlı).
  - Bölge haritası il/ilçe yerine ADM/GDZ bazlı (sözleşmede il/ilçe alanı yok).
  - pymodbus sunucusu yerine kendi Modbus sunucumuz (`docs/03` §13).
  - Firmware belleği 48 B yerine 320 B/nokta.
  - Renode/Wokwi atlandı.
- [ ] **D5 — Ekran görüntüleri:** `assets/ekran/` örnek veri modunda alındı (`docs/16` §5'te yazılı). K1 hazır olunca gerçek yığından alınması dürüstlük açısından daha güçlü olur.
- [ ] **D6 — Demo yığınının bilinçli güvenlik sınırları** (`docs/15` §5): broker anonim 1883, API kimlik doğrulamasız, Modbus/IEC 104 düz TCP. Sunumda "üretim farkları" olarak anlatılmalı.
- [ ] **D7 — Çiy alarmı kalibrasyonu (A):** `docs/12` §3'e göre 10 senaryonun 9'undaki yanlış alarmların tamamı `ALM-DEW-ALM` / `ALM-DEW-WARN` (S1'de `ALM-PANEL-TEMP`). S0 normal gününde 71,4/100 pano/gün sınırın içinde, ama `s0.sh` "Filo yeşil" bekliyor; canlı demoda çiy alarmı çıkabilir.
- [ ] **D8 — Süreç notu:** PLAN A.2 "rebase + squash merge" diyor. Bu entegrasyonda dallar birbirini içerdiği için (`berke/frontend` ⊃ `ahmet/backend`) `--no-ff` merge kullanıldı. Bundan sonraki kısa dallar için squash kuralına dönülebilir.

---

## 7. Karar gündemi (tek toplantıda kapatılabilir)

| # | Karar | Kimler | İlgili madde |
|---|---|---|---|
| 1 | Simüle `ts` mi, duvar saati mi? Canlı demo hızı kaç? | A + B + C | K3, Y1 |
| 2 | Senaryo oynatma arayüzü (bayrak adları) ve sahibi | A + C | K1 |
| 3 | TVOC-2 ID 248: kod mu düzeltilecek, metin mi? | A | K4 |
| 4 | Taşıma kabuğu (`sim/panobeyni_sim.py`) yazılacak mı, kapsam mı küçülecek? | A + B | Y2 |
| 5 | İki `contracts/changes` önerisi: onay mı, sonraki sürüm mü? | A + B + C | Y5 |
| 6 | KiCad şema PDF (Must) çizilecek mi, sapma mı savunulacak? | Ekip | Y6 |
| 7 | Raporlama periyodu: 10 s mi, "normalde 60 s, olayda anında" mı? `docs/09` §5–6: 10 s'de 1.000 pano ilk yıl ~1,2 TB disk, pano başına ~456 MB/ay hücresel veri | A + B | B'nin 13 Eyl notu |
| 8 | P3 telefonu çaldırır mı? M2 metni "P3 → telefon" diyor, sözleşmede P3 SMS/WhatsApp kapalı → S1 telefonu P2'de (K/K₀ > 1,6) çalar | Ekip | B'nin 13 Eyl notu |
| 9 | `scripts/validate.py` sahipliği | A + B | D3 |

---

## 8. Önerilen sıra

| Gün | İş |
|---|---|
| **15 Eylül** | Karar toplantısı (§7) · K4 (tek satır) · K2 metin düzeltmeleri (README, sunum, demo README) · Y9 |
| **16 Eylül** | K1 oynatma modu (A) + betik bağlantısı (C) · K5 dedektör bağlama (B) · Y2 kararı ve uygulaması · Y7 |
| **17 Eylül** | Y3 `docs/17` · Y4 temiz makine testi · Y5 onaylar · Y6 · **23:59 özellik dondurma** |
| **18 Eylül (M4)** | T4.8 gereksinim kapsama · çapraz okuma · temiz DB ile gerçek yığından ekran görüntüleri |
| **19 Eylül (M5)** | Video (2 tam çekim) · 2 prova · sunum PDF |
| **20 Eylül (M6)** | Sır taraması · erişim testi · **18:00 teslim** (23:59 son sınır) |

---

## 9. Kişi bazlı yapılacaklar

**A — Tuna**
- [ ] K1: senaryo oynatma modu (MQTT'ye, duvar saatine hizalı `ts`)
- [ ] K3: simüle `ts` kararının uygulanması
- [ ] K4: TVOC-2 `ignore_missing_slaves=True` + test (ya da metin düzeltmesi)
- [ ] Y1: canlı demoda taban öğrenme süresi için çözüm
- [ ] Y2: taşıma kabuğu ya da kapsam/doküman düzeltmesi (`main.c:13`, PLAN TA3 Adım 6)
- [ ] Y5: eşik önerisinin onayını topla
- [ ] Y9: `pyproject.toml` test extras'a `pandas`
- [ ] D7: çiy alarmı gürültüsünü gözden geçir

**B — Ahmet**
- [ ] K2 + Y3: `docs/17`'yi A ve C kanıtlarıyla güncelle
- [ ] K5: `CentralDetector`'ı bağla (Dockerfile context + `main.py` + test)
- [ ] Y4: T4.4 temiz makine testi; demo öncesi `down -v`
- [ ] Y5: iki sözleşme önerisine onay/ret; kabul edilirse `fleet/health` ucu
- [ ] Y8: `loadtest/fleet.py` → `panoalgo` üreteci (ya da not)
- [ ] O3: yedek plan · O4: gerçek telefona WhatsApp
- [ ] D3: `scripts/validate.py` sahipliği

**C — Berke**
- [ ] K1: betikleri gerçek CLI'ya bağla, `_ortak.sh` kontrolünü düzelt
- [ ] K2: `README.md` (39, 40, 42, 47–52, 61–64, 71), `sunum-taslagi.md` (35–42), `demo/senaryo/README.md`
- [ ] Y6: KiCad şema PDF kararı + STL üretimi
- [ ] Y7: `python3` taşınabilirliği + host kurulum adımı
- [ ] O7: sunum destesi + PDF · D5: gerçek yığından ekran görüntüleri

**Ortak**
- [ ] §7 karar toplantısı
- [ ] O1 video · O2 iki prova · O5 T4.8 · O6 sır taraması · O8 Faz 6 listesi
- [ ] D1 PLAN kutucukları · D2 GitHub handle'ları
