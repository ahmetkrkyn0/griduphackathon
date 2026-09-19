# Grid Up Hackathon 2026 — Bağımsız Değerlendirme

**Proje:** GridUp — Pano/Hücre İçi Anomali Erken Uyarı ve Kestirimci Bakım Sistemi
**Depo durumu:** dal `c-varlik-kutugu` @ `6be6e93` · 472 izlenen dosya · ~49.000 satır kod (Python 37k / TS+TSX 10k / C 2k) · 59 markdown

---

## 0. Nasıl değerlendirdim

**Kendim çalıştırdıklarım.** Yığını `docker compose -f deploy/compose.yaml down -v` sonrası dokümante edilen tek komutla sıfırdan kaldırdım (9 konteyner, exit 0). Dört test paketini koştum: panoalgo **489 geçti / 0 atlandı**, backend **853 geçti / 37 atlandı**, frontend **136 geçti**, firmware `gcc:13` konteynerinde **5/5**. Atlanan 37 backend testinin hepsi `TEST_DB_DSN` gerektiriyordu; canlı TimescaleDB'ye bağlayıp onları da koştum (46 geçti, 2 hata çıktı — hatanın benim kurulumumdan olduğunu izole ederek doğruladım, aşağıda). Altı `--check` üretecini koştum (hepsi "güncel"). `scripts/validate.py` ve `scripts/threshold_sweep.py --seasons` ile jüriye sunulan ana sayıları yeniden ürettim. `loadtest/fleet.py` ile **100 ve 1.000 pano** yük testini kendim koştum. Playwright ile 9 rotayı sürüp ekran görüntüsü aldım ve görüntülere baktım. Yetkilendirmeyi curl ile sınadım (belirteçsiz / yanlış belirteç / yetersiz rol / doğru rol). IEC 60870-5-104 için **sıfırdan kendi istemcimi yazdım** (projenin kodunu kullanmadan, ham soket + elle çerçeveleme) ve REST + Modbus TCP ile üçlü karşılaştırma yaptım. Kurcalama-kanıtı günlük zincirini bir satırı **bilerek bozarak** sınadım. Firmware'i hem `double` hem `float` derleyip `sizeof` ölçtüm. BOM toplamlarını kendi aritmetiğimle hesapladım. WCAG kontrast oranını token'lardan kendim hesapladım. Kurumun verdiği `İstenen Veriler.xlsx` dosyasını açıp okudum.

**Kod okuması.** Dokuz kriterin her biri için en iddialı cümleyi uygulayan koda gittim. Paralel derin okuma için 18 ajanlı bir workflow kullandım (9 kanıt + 9 karşıt-saldırı); **ajan bulgularını olduğu gibi kabul etmedim** — en ağır olanları tek tek kendim doğruladım ve ikisini çürüttüm (§4).

**Yapamadıklarım.** TimescaleDB sıkıştırma oranını ölçemedim (parçalar 1 günden eski olmalı, oturumumda öyle veri yok). Telegram'ın gerçek bir telefona teslimatını göremedim (bot belirteci `.env`'de boş — doğru uygulama, sırlar commit edilmemiş). TEDAŞ şartnamesinin tam metnine erişmediğim için şartname uyum iddialarını bağımsız denetlemedim. Modbus register haritasının tamamını cihaz kılavuzu PDF'leriyle karşılaştırmadım.

**Ortam kaynaklı, projeye yazılmayanlar.** `scripts/validate.py` backend venv'inde `pandas` olmadığı için çalışmadı; panoalgo venv'iyle çalıştı — venv seçimi benim işim. `test_seed_demo.py` canlı yığınla çakışıp 2 hata verdi; yazıcıları (`panosim`, `mpr-sim`, `tvoc-sim`, `backend`) durdurunca **6/6 geçti** — bu benim kurulum tercihimdi, proje kusuru değil.

---

## 1. Puan tablosu (Aşama 4 denetiminden geçmiş hâli)

| # | Kriter | Puan | Tek cümlelik gerekçe | Kanıt türü |
|---|---|:---:|---|---|
| 1 | Problemin doğru anlaşılması | **8** | Kurumun `İstenen Veriler.xlsx` ile istediği her kalemin (mA sekonder + çarpan, ABB TVOC-2 Modbus, HFCT/EA Technology PD) kodda karşılığı var ve mevsimsel eşik sayıları birebir yeniden üretildi; ancak bu bulgu üretecin iki sabitinden aritmetik olarak zorunlu çıkıyor. | ÖLÇTÜM ağırlıklı + OKUDUM |
| 2 | Anomali/risk tespit yaklaşımı | **7** | Yöntem (birinci mertebe ısıl model + RLS, sözleşmeden okunan eşikler, katmanlı L0/L1/L2) sağlam ve `docs/12` birebir yeniden üretilebilir; fakat "duyarlılık 1,00" dedektörün üretecin kendi fark denklemini ters çevirmesini ölçüyor ve 8 senaryodan biri hiçbir şey enjekte etmiyor. | ÖLÇTÜM + OKUDUM |
| 3 | Saha uygulanabilirliği | **7** | STL gerçek (324 üçgen, `.scad`'den üretiliyor), BOM üretici parça numaralı, veri bütçesi aracı çalışıyor; kurulum prosedürü 3.787 bayt ile bir saha ekibi için ince ve backend yeniden başlayınca arayüz ölü kalıyor. | ÖLÇTÜM + OKUDUM |
| 4 | Uçtan uca sistem yaklaşımı | **8** | `down -v` sonrası tek komutla 9 servis kalktı, boru hattı canlı doğrulandı (84/84 yazıldı, karantina tablosu 0 satır), kurcalama-kanıtı günlük zinciri çalışıyor; nginx `resolver` yok, backend yeniden başlayınca UI 502 veriyor. | ÖLÇTÜM |
| 5 | Operasyon sistemleriyle entegrasyon | **9** | Kendi yazdığım bağımsız IEC 104 istemcisiyle tam el sıkışma aldım ve 25 noktada REST=Modbus=IEC104 sıfır fark ölçtüm; CBS/GIS içe aktarımı, OMS/kesinti ve EPDK uçları üç kademeli rol denetimiyle uçtan uca çalışıyor. | ÖLÇTÜM |
| 6 | Ölçeklenebilirlik | **8** | 100 panoda p95 660,9 ms (doküman 657) ve 1.000 panoda p95 710,5 ms, kayıp 0, 1,46 M satır — ikisini de ben koştum; sıkıştırma oranını ölçemedim ve "sanallaştırılmış UI" iddiasının kodda karşılığı yok. | ÖLÇTÜM |
| 7 | Kullanıcı/operasyon deneyimi | **8** | Yedi ekranı sürdüm, 0 konsol hatası, gerçek veri; API'den yaptığım onay arayüzde doğru kullanıcıyla göründü (uyarı→bağlam→aksiyon→iz kapanıyor); README 9 ekran diyor, 7 var ve hiç bileşen testi yok. | ÖLÇTÜM |
| 8 | Maliyet ve sağlanan fayda | **5** | BOM kalem kalem ve üretici kodlu, EPDK maruziyet betiği testli; ama jüriye verilen dört sayıdan üçü doğrulamayı geçmiyor — 56/37 USD satır toplamı 70,73/47,68, "<120 USD dahil" kendi kaynak dokümanıyla çelişiyor, "14-22 ay" hiçbir yerde üretilmiyor. | ÖLÇTÜM |
| 9 | Yenilikçilik | **8** | C çekirdeği ile Python referansı ortak test vektörü üzerinden her adımda karşılaştırılıyor (güçlü test), ikisini de derleyip ölçtüm; canlı S1 koşumunda dinamik K/K0 sabit eşikten 288 saat önce uyardı. | ÖLÇTÜM + OKUDUM |

---

## 2. Üç ağırlık, üç toplam

| Ağırlık | Hesap | Toplam |
|---|---|:---:|
| A — eşit | 68 / 9 | **7,56** |
| B — teknik (2, 4, 5 çift) | 92 / 12 | **7,67** |
| C — ticari (1, 3, 8 çift) | 88 / 12 | **7,33** |

**Karar üç ağırlıkta da aynı:** bu proje üst dilimde, tek belirgin zafiyeti maliyet-fayda kanıtında. Aralık 0,34 puan — yani ağırlık seçimi sonucu değiştirmiyor. Sonuç sağlamdır.

Yine de jürinin bilmesi gereken: **belirleyici kriter 8'dir.** Ticari bakışta (C) toplamı aşağı çeken tek kalem odur; kriter 8'e verdiğim 5 yerine 8 verilseydi C toplamı 7,33 → 7,83 olur ve sıralama ticari bakışta teknik bakışın üstüne çıkardı. Kriter 5 (9) ise teknik bakışta en çok taşıyan kalem. Kısaca: teknik jüri bu projeyi entegrasyon tarafından, satın alma bakışı ise maliyet kanıtının zayıflığından okuyacaktır.

---

## 3. Kriter kriter kanıt defteri

### Kriter 1 — Problemin doğru anlaşılması → **8**

| İddia | Nerede | Durum | Dayanak |
|---|---|---|---|
| "çiy olayı kış 28,6 · geçiş 71,4 · yaz 0,0 olay/100 pano/gün" | `README.md:25` | **ÖLÇTÜM** | `scripts/threshold_sweep.py --seasons` koştum: `kis … 28.6 / gecis … 71.4 / yaz … 0.0`. Birebir. |
| "0,5/0,0 çifti 228,6 olay/100 pano/güne çıkarır" | `README.md:25` | **ÖLÇTÜM** | Aynı çıktı: `\| 0.5 \| 0.0 \| 228.6 \| %78.1 \| %65.6 \|`. |
| Kurumun istediği veri kalemleri karşılanmış | `Hackathon Verileri/İstenen Veriler.xlsx` | **ÖLÇTÜM** | Dosyayı açtım: "Sekonder Cinsten Akım Değeri / mA / Çarpan / Hesaplanan Primer Akım", "ARC Sensörü — ABB TVOC-2 … Modbus ile", "PD Tespiti için HFCT — EA Technology". Karşılıkları: `devices.py:223` `MPR_CURRENT_SCALE = 0.001` + `ct_ratio`, `sim/tvoc2_sim.py`, `contracts/alarm-codes.yaml:167` "EA Technology kalıcı HFCT trend yaklaşımı". |
| PD yalnızca OG için anlamlıdır, AG panoda null | `limits.py:236`, `generator.py:710` | **OKUDUM** | "HFCT kısmi deşarj ölçümü; AG panoda None (rapor 3.7)". Gerçek alan bilgisi — 400 V AG panoda PD ölçmeye kalkışmamış. |
| Kapsam dışı tek yerde yazılı | `docs/17` §6 | **OKUDUM** | 24 satırlık sapma tablosu, her satırda gerekçe + kaynak dosya. |
| "Sorun eşik seçimi değil; panonun mevsimsel fiziğidir" | `README.md:25` | **YANILTICI (kısmi)** | Kendi hesabım: `generator.py:603-606` `RH = 50 + 2·(40−T)`, kırpma `[20, 98]`. Kış aralığında (`WINTER_MEAN_C=5 ± 5 K` → 0–10 °C) RH daima %98 tavanında. Yani "kışın çiy alarmı sürekli" sonucu ölçülmüş bir pano davranışı değil, iki sabitin aritmetik zorunluluğu. |
| Paschen gerekçesi | `docs/01:24-26` vs `docs/05:330-333` | **OKUDUM** | `docs/05` kendi kısayolunu "YANLIŞ" diye geri çekiyor (faz-faz tepe 566 V > 327 V), ama jüri özeti `docs/01` düzeltilmemiş. İki doküman çelişiyor. |

**Gerekçe.** Çapamın 9'u "arıza modu → belirti → sinyal → karar zinciri yazılı; gerçek kısıtlar doğru kullanılmış; kapsam dışı yazılı" diyordu. Üçü de var ve kurumun verdiği veri seti gerçekten okunup koda dönmüş — bu, hackathon projelerinde sık görülmeyen bir şey. Bir puan, jüriye sunulan ana içgörünün ölçüm değil tanım olmasından ve iki dokümanın çelişmesinden.

---

### Kriter 2 — Anomali ve risk tespit **yaklaşımının** başarısı → **7**

| İddia | Nerede | Durum | Dayanak |
|---|---|---|---|
| "8 anomali senaryosunun tamamında duyarlılık 1,00, 10 senaryoda yasaklı alarm 0" | `README.md:26` | **ÖLÇTÜM** | `scripts/validate.py` koştum; çıktı `docs/12-dogrulama-sonuclari.md` ile üretim zamanı dışında **birebir aynı** (`diff` boş). S1–S5, S7–S9 recall 1.00; 10 senaryoda "yasaklı alarm: yok". |
| "S1'de sabit 70 K eşiğinden 158–209 saat önce" | `README.md:26` | **YANILTICI (alt sınır)** | Ölçülen tek değer **209,0 h / 8,7 gün** (`docs/12` §2). "158" ve "6.5 gün" deponun hiçbir üretilmiş çıktısında yok; yalnızca `README.md:26` ve `:97`'de. `git log -S"158"` → README modernizasyon commit'i `82fbe05`. |
| Dinamik K/K0 sabit eşikten erken uyarıyor | `README.md:26` | **ÖLÇTÜM** | Canlı S1 koşumum: `ALM-K-WARN (232.0 h)` vs `ALM-THR-TERM-ALM (520.0 h)` → **288 saat** erken. Bağımsız ikinci kanıt. |
| Eşikler sözleşmeden okunur, dosyada gömülü eşik yok | `detect.py:23` | **OKUDUM (hafif abartı)** | `scripts/check_contracts.py`: "Alarm: 23 kod, 9 hipotez, 44 eşik". Ama `detect.py:49` `SLOPE_PERSISTENCE_MIN = 0.6` bir karar eşiği ve kodda. Dosyanın kastettiği üç eşik (λ, τ₀, uyarım sınırı) gerçekten sözleşmeden. |
| S3_condense "yoğuşma enjekte edilmiş senaryo" | `scenarios.py:119-129` | **YANILTICI** | Kendi hesabım: senaryo `season="kis"` + `humidity_offset_pct: 25`. Kış aralığında (0–10 °C) RH zaten %98 tavanında → offset etkisi **tam 0,000 puan**. Yani 8 "anomali senaryosundan" biri hiçbir şey enjekte etmiyor; S0'ın kışta koşulmuş hâli. |
| **Üreteç–dedektör döngüselliği** | `generator.py:558-580` / `detect.py:3-5` | **OKUDUM — merkezi bulgu** | Üreteç: `dT[k+1] = a·dT[k] + (1−a)·K·I²`, `a = exp(−dt/τ)`. Dedektör: aynı denklemin `[a, β]`'sını RLS ile kestiriyor, `K = β/(1−a)`. Arıza `spec.k0 · _k_multiplier[...]` ile **tam da kestirilen parametreye** enjekte ediliyor. Üretecin docstring'i indis hizalamasının bilerek aynı tutulduğunu yazıyor (`:563-570`). |
| Döngüselliği hafifleten etkenler | `generator.py:614`, `:308-310` | **OKUDUM** | Ölçüme `gauss(0, TEMP_SENSOR_SIGMA_K=0.2)` gürültü ekleniyor; yük AR(1) stokastik; değerler yuvarlanıyor. Saf cebirsel ters çevirme **değil**. Ayrıca ark (TVOC trip sayacı), haberleşme kaybı ve sensör arızası kanalları model-tabanlı değil. |
| Prognoz geri testi kötü ve yayımlanmış | `docs/12` §4 | **ÖLÇTÜM** | Kendi koşumum: S1 koni içinde **%5,2**, CRA **−5,12**, ufuk "yok", medyan tahmin/gerçek 1,69. Proje bunu gizlememiş, kendi tablosunda basıyor. |
| Gerçek precision/FPR yok | `validate.py:11-13, :85-86` | **OKUDUM** | Metrik `precision_ok` adında ve bir bool ("yasaklı kod çıktı mı"); docstring bunu açıkça tanımlıyor, README de sayı uydurmayıp "yasaklı alarm 0" diyor. Klasik TP/(TP+FP) hiç hesaplanmıyor; yerine operasyonel "olay/100 pano/gün" kullanılıyor — savunulabilir, hatta saha için daha uygun bir metrik. |

**Gerekçe.** Yaklaşım — resmi kriterin sorduğu şey budur — sağlam: ders kitabı seviyesinde bir toplu-parametre ısıl modeli, sözleşmeden okunan 44 eşik, katmanlı mimari, hipotez-kanıt sayacı, kendi başarısızlığını yayımlayan prognoz testi. Puanı 9'a çıkarmayan şey **kanıtın yapısı**: "duyarlılık 1,00" büyük ölçüde kestiricinin kendi ileri modelini ters çevirmesini ölçüyor, n=8 zaten küçük, ve o 8'den biri boş. Not: bu puan, Aşama 1'de yazdığım döngüsellik tavanının (6) bir puan üstünde — gerekçesini §4'te açıkça veriyorum.

---

### Kriter 3 — Çözümün saha koşullarında uygulanabilirliği → **7**

| İddia | Nerede | Durum | Dayanak |
|---|---|---|---|
| "Sağlıklı panoda operatör yükü 71,4 yanlış alarm/100 pano/gün (hedef <150)" | `README.md:27` | **ÖLÇTÜM** | `docs/12` §3, `S0_normal` satırı = 71.4. Kendi koşumumda birebir. |
| DIN ray tipi modüler kutu (STL) | `hardware/mekanik/din-kutu.stl` | **ÖLÇTÜM** | İkili STL, başlık "GridUp Pano-Beyni DIN Enclosure (Fibox ARCA 92/1…", **324 üçgen**, `84 + 324×50 = 16.284` = dosya boyutu → tutarlı. Üstelik `din-kutu.scad` + `generate_stl.py` ile parametrik üretiliyor; indirilmiş blob değil. |
| BOM ve blok diyagramları hazır | `hardware/*/bom.csv` | **OKUDUM** | Üretici parça numaralı (ESP32-S3-WROOM-1-N8R8, ADM2587EBRWZ, Quectel EC200A-EU…), adet-1/adet-1000 fiyatlı. KiCad yerine blok diyagram tercihi gerekçesiyle açıklanmış. |
| "optik ark … sensör kartı BOM ve blok diyagramları hazır" | `README.md:27` | **YANILTICI** | `hardware/` altında ark kartı yok (yalnızca `pd-karti`). `docs/13:204` ark tespitinin TVOC-2'nin kendi optik sensöründen geldiğini söylüyor — yani ayrı bir kart tasarlanmamış. |
| Veri bütçesi / uyarlanabilir raporlama | `loadtest/veri_butcesi.py` | **OKUDUM** | 18 KB'lik gerçek ölçüm aracı, ölü bant kesirleri ve bayt muhasebesi ("OLCULDU" etiketli), `loadtest/results/*.json` çıktıları tohumlu. |
| Kurulum prosedürü saha ekibi için yeterli | `docs/08-kurulum-proseduru.md` | **OKUDUM — zayıf** | 3.787 bayt. Bu ölçekteki bir işte (retrofit, gerilim altı pano, tork kontrolü) bir ekibin izleyebileceği ayrıntıda değil. |
| Bileşen yeniden başlayınca kurtarma | frontend nginx yapılandırması | **ÖLÇTÜM — bulgu** | Backend konteynerini yeniden başlattım; nginx eski IP'yi (172.18.0.9) tuttuğu için tüm `/api` çağrıları **502** döndü ve operatör arayüzü ölü kaldı. `proxy_pass http://backend:8000` var, `resolver` yönergesi yok. Frontend'i yeniden başlatınca düzeldi. Üretimde backend yeniden başlatması sıradan bir olaydır. |
| Donanım satın alınmadı | `README.md:139` | **Ceza yok** | Şartname bunu açıkça serbest bırakıyor; proje ayrıca kendisi beyan ediyor. |

**Gerekçe.** Çapamın 6'sı "donanım/haberleşme seçimi somut ve en az bir saha kısıtı ele alınmış, ama kurulum/bakım iş akışı yok" diyordu; 9'u "kısıtlar sayılarla, kopuk çalışma, devreye alma adımları somut". Proje kısıtları sayılarla ele almış (veri bütçesi, alarm yükü, bellek ayak izi) ve donanım seçimi parça numarası düzeyinde somut — 6'nın üstünde. 9'a çıkaramadım: devreye alma prosedürü ince ve gerçek bir kurtarma açığı ölçtüm.

---

### Kriter 4 — Uçtan uca sistem **yaklaşımı** → **8**

| İddia | Nerede | Durum | Dayanak |
|---|---|---|---|
| Tek komutla yığın kalkar | `README.md:58` | **ÖLÇTÜM** | `down -v` → `up -d --build`, exit 0, **9 konteyner**: mosquitto, timescaledb, backend, grafana, gsm-modem, panosim, mpr-sim, tvoc-sim, frontend. `compose.yaml:18` `include:` ile üç dosyayı çekiyor — "tek komut" iddiası doğru. |
| "panosim → MQTT → Ingest → TimescaleDB → REST → WebSocket → UI, karantina 0" | `README.md:28` | **ÖLÇTÜM** | `/health`: `received 84 / written 84 / rejected 0 / dropped 0 / write_errors 0`. Veritabanında `select count(*) from quarantine` → **0**. 1.000 panoluk koşumda da 0/0/0. |
| Sağlık ucu dürüst | `backend/app/main.py` | **ÖLÇTÜM** | `/health` `mqtt_tls: false` ve `auth.enabled: true` dahil her şeyi açıkça raporluyor — zayıflığı gizlemiyor. |
| Kurcalama-kanıtı denetim günlüğü | `deploy/initdb/007_journal_chain.sql`, `scripts/verify_journal.py` | **ÖLÇTÜM** | Alarm yaşam döngüsü zincire yazıldı (raised → notified → acked, `by_user: vardiya.amiri`, benim notum). `verify_journal.py` → "ZİNCİR SAĞLAM — 6 halka". **Sonra bir satırın notunu bozdum**: "ZİNCİR KOPUK — halka 4 (`id=75`) … satır DEĞİŞTİRİLMİŞ", geri alınca yine "SAĞLAM". Doğrulayıcı gerçekten çalışıyor. |
| Sözleşme–doküman tutarlılığı | `scripts/gen_*.py --check` | **ÖLÇTÜM** | Beş üreteç de "guncel"; `check_contracts.py` → "SÖZLEŞMELER TUTARLI" (13 blok, 430 register, 23 alarm kodu, 17 uç). |
| "Telegram … teknik ekibin cep telefonuna teslim edilir", kanıt `docs/17` §4.2 | `README.md:28` | **YANILTICI (atıf)** | `grep -il telegram docs/*.md` → hiçbir dosya. Telegram `docs/` altında hiç geçmiyor; gösterilen kanıt bölümünde de yok. Kod gerçek (`notify/telegram.py`, httpx ile Bot API, `test_telegram.py` var) ama `.env`'de `TELEGRAM_BOT_TOKEN=` boş → varsayılan yığında hiç çalışmıyor; canlı alarmda `"notified": ["sms"]` gördüm. |
| "GSM modeme (SMS)" | `README.md:28` | **YANILTICI (kip)** | `scripts/virtual_gsm_modem.py` bir simülatör. Depo bunu başka yerlerde dürüstçe yazıyor; README'nin kesin kipi ("teslim edilir") bunu örtüyor. |
| Bileşen düşerse | nginx | **ÖLÇTÜM — bulgu** | §3'teki 502 bulgusu buraya da yazılır. |

**Gerekçe.** Çapamın 9'u için gereken her şey var — zincir bütün olarak kalkıyor, bir yabancı (ben) README'yi izleyerek kaldırabildi, sağlık uçları ve testler yerinde, bileşen sınırları tanımlı. Eksik olan tek çapa maddesi "bir bileşen düşerse ne olur" ve orada ölçülmüş bir açık var. Bildirim kanallarının README'de gerçekleşmiş gibi anlatılması ikinci puan kırıcı.

---

### Kriter 5 — Mevcut **operasyon sistemleriyle** entegrasyon kabiliyeti → **9**

> Resmi kriter SCADA'dan geniştir. README bu satırı "Entegrasyon **(SCADA)**" diye daraltmış — ama aşağıda göstereceğim gibi projenin gerçekte sahip olduğu entegrasyon README'nin iddia ettiğinden geniş. Bu, nadir görülen bir yönde hata: proje kendini az satmış.

| İddia | Nerede | Durum | Dayanak |
|---|---|---|---|
| IEC 60870-5-104 istasyonu çalışıyor | `backend/app/scada/iec104_server.py` | **ÖLÇTÜM** | Projenin kodunu kullanmadan **sıfırdan kendi istemcimi yazdım** (ham soket, elle APCI/ASDU çerçeveleme). Sonuç: `STARTDT_CON` → `C_IC_NA_1 ACTCON (COT=7)` → **168 bilgi nesnesi** → `ACTTERM (COT=10)`. **139 ölçülen değer** — `docs/04:404`'ün dediği sayı. Standarda uygun tam el sıkışma. |
| "conn_temp 25 noktanın tamamında Modbus = API × 10, fark 0" | `README.md:29` | **ÖLÇTÜM** | Üç protokolü aynı pano (ADM-00001 = Modbus birim 1, `gateway.py:162`) üzerinde eşzamanlı okudum: 25/25 noktada `round(REST×10) == Modbus == IEC104×10`. **Uyuşmazlık 0.** |
| "IEC 104 = REST API, 0 fark" | `README.md:29` | **ÖLÇTÜM — nüans** | Kendi verimde IEC 104 değeri REST'in 0,1 °C'ye yuvarlanmışı (REST 34,24 → IEC 34,20). "Fark 0" yalnızca dokümante edilen 0,1 °C register ölçeğinde doğru; `docs/04:94` bu ölçeği zaten listeliyor. Savunulabilir ama README'nin çıplak "Fark: 0"ı bunu gizliyor. |
| Yazma yollarında yetkilendirme | `backend/app/auth.py` | **ÖLÇTÜM** | Alarm onayı: belirteçsiz **401**, yanlış belirteç **401**, izleyici rolü **403** ("bu işlem 'operator' rolü gerektiriyor"), operatör rolü **200**. Üç kademeli ve gerçekten uygulanıyor. |
| **CBS/GIS içe aktarımı** | `backend/app/api/assets.py:88` | **ÖLÇTÜM** | `POST /api/v1/fleet/assets` uçtan uca sınadım: yetkisiz **401** → operatör **403** ("'muhendis' rolü gerektiriyor") → mühendis **200** `{"guncellenen":3,...}`. Geri okuma CBS kodu, fider id, il/ilçe, abone sayısı, trafo kVA, kritiklik ve bakım tarihlerini döndürdü. |
| Örnek CBS dosyasının dürüstlüğü | `scripts/ornek-cbs-aktarim.json:2-4` | **OKUDUM — lehine** | "ÖRNEKTİR — GERÇEK CBS VERİSİ DEĞİLDİR … elle yazıldı … Demo veritabanına KENDİLİĞİNDEN YÜKLENMEZ" ve "Üretici ve seri no uydurulmaz" — geri okumada `uretici: null, seri_no: null`. Uydurmayı reddetmiş. |
| **OMS / kesinti / EPDK** | `api/outages.py`, `app/epdk.py` | **OKUDUM** | `/api/v1/outages`, `/outages/{id}` (kanıt ekli), `/outages/{id}/epdk-kaydi`; `epdk.py:35` mevzuat formülünü alıntılıyor. SCADA dışı ikinci ve üçüncü operasyon sistemi sınıfı. |
| Denetim izi | `alarm_journal` | **ÖLÇTÜM** | §4'teki kurcalama testi. Operasyon sistemleri entegrasyonunda kritik olan izlenebilirlik gerçekten var. |
| "uzaktan röle denetimi" | `README.md:29` | **YANILTICI** | `contracts/modbus-map.yaml:195-207` yazılabilir blok: `password / ack_alarm / reset_latch / maint_mode / test_alarm`. Röle komutu yok. |
| Birim→pano eşlemesi çalışma anında görünmüyor | `/health` | **OKUDUM — küçük eksik** | `units: 6` diyor ama hangi birimin hangi panoya baktığını söylemiyor; bir SCADA entegratörünün ihtiyacı olan eşleme yalnızca dokümanda. |

**Gerekçe.** Çapamın 9'u: "en az iki farklı operasyon sistemi sınıfına somut arayüz; veri modeli eşlemesi yazılı; kimlik doğrulama çalışıyor; sahte karşı uçla uçtan uca denenmiş ve testi var; varlık kimliği kurum kodlamasıyla uyumlu." Beşi de karşılanıyor ve **üç** sınıf var (SCADA / CBS / OMS-EPDK). Eşleme üretilip `--check` ile doğrulanıyor, kimlik doğrulama üç kademeli, uçtan uca denemeyi **ben bağımsız istemciyle** yaptım, varlık kimliği gerçek dağıtım kodlaması (CBS kodu + fider id). Bu, projenin en güçlü kriteri. 10 vermedim: "uzaktan röle denetimi" karşılıksız ve README kriteri kendi aleyhine daraltmış.

---

### Kriter 6 — Ölçeklenebilirlik → **8**

| İddia | Nerede | Durum | Dayanak |
|---|---|---|---|
| "1.000 panoda görünme p95 657 ms, kayıp 0" | `README.md:30` | **ÖLÇTÜM** | Kendim koştum (1.000 pano, 7 nokta, 100 bağlantı, 180 s): görünme **p50 404,5 / p95 710,5 / maks 835,9 ms**, `rejected 0, dropped 0, write_errors 0`, 1.458.000 telemetri satırı, ~99 mesaj/s. Farklı makinede p95 %8 yüksek çıktı; **kayıp 0 birebir doğrulandı**. |
| 100 pano ölçümü | `docs/09:68` | **ÖLÇTÜM** | Doküman 386 / 657 / 906 ms diyor; benim koşumum **382,5 / 660,9 / 768 ms**. p95 farkı %0,6. Yeniden üretilebilir. |
| Ölçüm koşulları yazılı | `docs/09:34-40` | **OKUDUM — lehine** | Makine (i7-14700KF, 20 çekirdek, 31,8 GB), sanallaştırma (WSL2 28 vCPU), ve "yük üreteci **aynı makinede**; sonuçlar temkinli" + "Dürüstlük notu: bu bir geliştirme iş istasyonudur" yazılı. Çapamın 9'unun tam istediği şey. |
| Sıkıştırma politikası yapılandırılmış | `deploy/initdb/005_compression.sql` | **ÖLÇTÜM** | Canlı DB: `segmentby = pano_id, tag`, `orderby = ts DESC`. Gerçekten kurulu. |
| "TimescaleDB sıkıştırması 46–48×" | `README.md:30` | **DOĞRULANAMADI** | Sıkıştırma 1 günden eski parçalara uygulanıyor; oturumumdaki tüm veri taze (`0 / 1 parça sıkıştırılmış`). Oranı ölçemedim. Ayrıca paralel okuma, oranın şablon üreteçle ölçüldüğünü ve etiketlerin yarısından fazlasının sabit olduğunu bildirdi — bunu ben doğrulamadım; doğruysa oran gerçek veride daha düşük olur. |
| "sanallaştırılmış UI" | `README.md:30` | **YANILTICI** | `react-window / react-virtual / virtuoso / virtualiz` → frontend'in tamamında sıfır eşleşme. `FiloListesi.tsx` kırpma yapmıyor. Var olan şey sayfalama. |
| Kanıt dosyası atfı yanlış | `README.md:30` | **YANILTICI (küçük)** | `/api/v1/fleet/health` için `backend/app/api/panels.py` gösteriliyor; uç aslında `insights.py`'de. |

**Gerekçe.** Çapamın 9'u için gereken "gerçek yük ölçümü + ölçüm koşulu yazılı" fazlasıyla var ve **ben iki ölçekte de yeniden ürettim** — bu, bu değerlendirmede gördüğüm en sağlam ölçüm disiplini. 9 vermedim: sıkıştırma oranını doğrulayamadım, 10k+ senaryosu yok ve README'de karşılıksız bir "sanallaştırma" iddiası var.

---

### Kriter 7 — Kullanıcı / operasyon deneyimi → **8**

| İddia | Nerede | Durum | Dayanak |
|---|---|---|---|
| Ekranlar çalışıyor, konsol temiz | `frontend/` | **ÖLÇTÜM** | Playwright ile 7 rotayı sürdüm: hepsinde **0 konsol hatası**, gerçek veri (pano detayda 25 satır, filoda 4, cihaz sağlığında 7), 32–39 buton. |
| "9 tam operasyon ekranı (… Ayarlar)" | `README.md:31` | **YANILTICI** | `App.tsx:19-35` → **7 rota**. `/ayarlar` → "Sayfa bulunamadı" (ben açtım). `grep "Ayarlar" frontend/src` → hiç. "3D ikiz" ayrı ekran değil, `PanoDetay` içinde bir sekme. **Projenin kendi dokümanı doğruyu söylüyor:** `docs/16:53` "9 ekranın 7'si çalışıyor". README kendi tasarım dokümanını aşıyor. |
| Operasyon döngüsü kapanıyor | ekran görüntüsü + API | **ÖLÇTÜM** | Alarm kartı dört başlık taşıyor: **Neden? / Ne doğrulanmalı? / Ne yapmalı? / Ne kadar acil?** — dayanak "IEC 61439-1 Tablo 6", değer "71,2 K eşik 70", hipotez sayacı "5 kanıttan 4'ü görüldü", eylem "Onayla / Rafa al". **API'den yaptığım onay arayüzde "vardiya.amiri onayladı, 8 dk önce" olarak göründü** — uyarı→bağlam→aksiyon→iz zinciri kapanıyor. |
| Alarm yorgunluğu düşünülmüş | `docs/05:415-419`, alarm konsolu | **OKUDUM + ÖLÇTÜM** | EEMUA 191 "bayat alarm patolojisi" referansı; konsolda Açık/Rafta/Tümü + Kritik/Alarm/Uyarı/Sistem filtreleri, "CSV İndir (Vardiya Raporu)". |
| "WCAG 2.x kontrast 16,0:1" | `README.md:31` | **YANILTICI (bayat)** | Kendim hesapladım: dokümanın varsaydığı `#1f2224/#ffffff` gerçekten 16,0:1 — ama o token'lar artık yok. Bugünkü `theme.css:3,7` (`--bg #f5f6f8`, `--ink #202b34`) → **13,33:1**. Sayı bayat; yine de WCAG AAA (7:1) eşiğinin çok üstünde. |
| 96 ilçe coğrafi harita | `BolgeHaritasi.tsx` (907 satır) | **ÖLÇTÜM** | Ekran görüntüsüne baktım: gerçek poligon sınırlı, etiketli ilçe haritası; kapsanan alan ADM (Aydın/Denizli/Muğla) + GDZ (İzmir/Manisa) hizmet bölgesiyle doğru örtüşüyor. Stok harita değil. |
| 3D termal ikiz gerçek mi | `components/Ikiz3D.tsx` | **ÖLÇTÜM** | `npm run build` çıktısı `three-D1Y8sU5B.js 492.90 kB` — three.js gerçekten paketlenmiş, lazy yüklenen ayrı chunk. 2D şema değil. |
| Hiç bileşen testi yok | `frontend/src` | **ÖLÇTÜM — bulgu** | 136 testin **tamamı** `lib/` ve `api/` saf fonksiyon testi. `.test.tsx` dosyası **0**; `testing-library`/`jsdom` bağımlılığı yok. Yani hiçbir ekran, hiçbir alarm kartı, hiçbir etkileşim test altında değil. |
| "Playwright: 7 ekran, 0 konsol hatası" | `KALAN-EKSIKLER.md:34`, `docs/17:159` | **ÖLÇTÜM — sonuç doğru, tezgah yok** | Depoda Playwright yapılandırması, spec dosyası veya bağımlılığı yok (ben `npx` ile dışarıdan kurdum). **Ama iddia edilen sonucu bağımsız olarak ben de aldım**: 7 ekran, 0 konsol hatası. Yani sayı doğru, yeniden üretilebilirlik artefaktı eksik. |

**Gerekçe.** Çapamın 9'u "rolü belli kullanıcı için akış tasarlanmış: uyarı gelir → bağlam görünür → aksiyon alınır → izi kalır; alarm yorgunluğu düşünülmüş; ekranlar dolu ve konsol hatasız" diyordu. **Hepsi karşılanıyor** ve dördüncü halkayı (iz) kendi eylemimle doğruladım. 9 vermedim: README ekran sayısını ve kontrastı abartıyor, ve arayüzün hiçbir testi yok — çalıştığını ben gördüm ama bir regresyon bunu sessizce bozar.

---

### Kriter 8 — Maliyet ve sağlanan fayda → **5**

| İddia | Nerede | Durum | Dayanak |
|---|---|---|---|
| "Pano beyni kartı adet 1'de ~56 USD, adet 1.000'de ~37 USD" | `README.md:32`, `bom.csv:19`, `docs/10:20-21` | **YANILTICI** | Satır kalemlerini kendim topladım: **70,73 USD / 47,68 USD**. Beyan edilen 56/37 → %26 / %29 düşük. Fark tam olarak hücresel modem kalemi (14,50 / 10,80). Dipnot "SIM/veri ve kurulum işçiliği hariç" diyor — **modem donanımının** dışarıda bırakıldığını söylemiyor. |
| Diğer iki BOM | `pd-karti`, `sensor-dugumu` | **ÖLÇTÜM** | `sensor-dugumu`: hesap 23,25 / 13,95 = dipnot **birebir doğru**. `pd-karti`: hesap 19,80 / 11,79 vs dipnot 18,80 / 11,35 (~%5). Yani ekip toplamı doğru yapabiliyor; `pano-beyni` dipnotu bayat kalmış. |
| "sensör düğümleri ve PD kartı **dahil** toplam pano başı retrofit maliyeti <120 USD" | `README.md:32` | **YANILTICI — en ağırı** | Kanıt gösterdiği doküman tam tersini söylüyor: `docs/10:23-25` "Bu rakamlara sensör düğümleri (S1–S5), SIM/veri aboneliği ve kurulum işçiliği **dahil değildir** … sensör düğümleri bu teslimde **kavramsal seviyede**". README kendi kaynağıyla çelişiyor. |
| Projenin kendi iç raporu bunu zaten işaretlemiş | `INOVASYON-SEKTOR-TASARIM-RAPORU-2026-09-18.md:117` | **OKUDUM** | "README'deki `<120 USD` ifadesi ile maliyet dokümanının … 37/56 USD rakamları **aynı kapsam değil**." 18 Eylül'de yazılmış, 19 Eylül'de hâlâ düzeltilmemiş. |
| "1 engellenen yangında 14-22 ayda kendini amorti eder" | `README.md:32` | **YANILTICI** | `git grep "14-22"` → **yalnızca bu satır**. Bu sayıyı üreten kod, doküman veya test yok. |
| EPDK maruziyet modeli | `scripts/tazminat_maruziyeti.py` | **OKUDUM** | Gerçek bir betik, `backend/tests/test_tazminat_maruziyeti.py` ile testli; `epdk.py:35` mevzuat formülünü alıntılıyor. Bu kısım sağlam. |
| Döngüsel fayda modelini **reddetmiş** | `GELISTIRME-BACKLOGU.md:656` | **OKUDUM — lehine** | Weibull/Cox arıza olasılığı modelini "arıza zamanlarını üreteçte biz enjekte ediyoruz; model kendi varsayımımızı geri okur" diyerek elemiş. Doğru bilimsel refleks. |
| BOM'un kaynağı kod değil | `docs/10:3` | **OKUDUM** | "BOM kaynağı: `hardware/pano-beyni/bom.csv` (elle düzenlenmez, oradan okunur)" deniyor; ama ~56/~37 csv'nin son satırına **elle yazılmış bir metin**, hiçbir kod toplamıyor. Diğer sekiz dokümanın aksine burada üreteç/`--check` yok. |

**Gerekçe.** Altta yatan iş çapamın 6'sını karşılıyor: BOM kalem kalem ve üretici kodlu, fayda tarafı bir mevzuat modeline bağlanmış ve testli, varsayımların uydurma olduğu yerler `docs/10`'da işaretlenmiş. Ama bu kriterin ölçtüğü şey **jüriye verilen maliyet-fayda kanıtıdır** ve README'deki dört sayıdan üçü doğrulamayı geçmiyor: biri %26 düşük, biri kendi kaynak dokümanıyla doğrudan çelişiyor, biri hiçbir yerden çıkmıyor. Üstelik projenin kendi iç raporu bunlardan birini bir gün önce işaretlemiş. Bu, diğer sekiz kriterdeki üreteç-doğrulama disiplininin **uygulanmadığı tek alan**. 5, "çalışan bir şey var ama sınırları belirsiz"in altında değil üstünde değil — tam orada.

---

### Kriter 9 — Yenilikçilik → **8**

| İddia | Nerede | Durum | Dayanak |
|---|---|---|---|
| "Saf C çekirdeği mikrodenetleyicilerde çalışacak şekilde derlenir" | `firmware/` | **ÖLÇTÜM** | `gcc:13` konteynerinde `cmake` + `ctest` → **5/5 geçti**. `rls.c` gerçek özyinelemeli en küçük kareler (kovaryans güncellemesi dahil), `malloc` yok, sabit boyutlu, `PANO_USE_FLOAT` ile tek duyarlıklı derlenebiliyor. |
| "Python referansı ile farkı <1.5e-8" | `README.md:33` | **ÖLÇTÜM** | Kendim koştum: `double` → **K 1.362e-08, tau 1.419e-08** (240 adım). İddia doğru. |
| Testin gücü | `firmware/tests/test_rls.c` | **OKUDUM — güçlü test** | Test Python'un ürettiği **harici** `data/fixtures/rls_vectors.csv`'yi okuyor, aynı girdiyi C'ye veriyor ve **her adımda** K, tau **ve** `excited` boolean'ını karşılaştırıyor; tolerans 1e-6 göreli. Beklenen değeri test içinde yeniden hesaplamıyor. Zayıf test kalıplarının hiçbirine girmiyor. |
| Float (asıl MCU hedefi) farkı | `README.md:33` | **ÖLÇTÜM — seçici alıntı** | `PANO_USE_FLOAT=ON` ile ölçtüm: **K 6.961e-06** — ~500 kat büyük. Test dosyasının başlığı (`:10-19`) bunu açıkça yazıp fiziksel olarak önemsiz olduğunu gerekçelendiriyor ve farkı ekrana basıyor. README yalnızca daha gösterişli `double` sayısını alıntılıyor. |
| Bellek ayak izi | `ana-dongu.md:110`, `docs/17:219` | **ÖLÇTÜM — bayat** | Belgelenen 320 B (double) / 176 B (float), 25 nokta 8,0 KB. Kendi derlememde `sizeof(pano_rls_t)` = **384 B / 196 B**, 25 nokta **9,4 KB**. %20 iyimser. Hedef MCU sınıfında (128–256 KB SRAM) sonuç değişmiyor ve proje bu kalemi zaten "sapma #4" olarak beyan etmiş. |
| Yeniliğin operasyonel karşılığı | canlı S1 | **ÖLÇTÜM** | Dinamik K/K0 uyarısı 232 h'de, sabit 70 K eşikli alarm 520 h'de → **288 saat** erken. Yenilik gösteriş değil, ölçülebilir bir fark üretiyor. |
| Yenilik döngüsellikten etkileniyor mu | — | **OKUDUM** | RLS, üretecin entegre ettiği modeli kestiriyor (K2'deki bulgu). Ama buradaki yenilik iddiası tespit doğruluğu değil, **aynı algoritmanın kenarda ve merkezde ortak test vektörüyle kanıtlanmış eşitliği** — o iddia döngüsel değil ve doğrulandı. |

**Gerekçe.** Çapamın 9'u "özgün fikir hem tanımlı hem çalışır hâlde, farkı somut bir şeyle gösterilmiş" diyordu. Tanımlı (dinamik ısıl direnç öğrenimi + tek kaynaklı C/Python çekirdeği), çalışır (ben derledim ve koştum), farkı somut (288 saat). Bir hackathon projesinde kenar ile merkez arasında **kanıtlanmış** algoritma eşitliği alışılmadık ve gerçekten değerli bir mühendislik özelliğidir. 9 vermedim: iki nicel figür (float farkı, bellek) README/dokümanda olduğundan iyi gösteriliyor.

---

## 4. Kendi denetimimin sonucu

### 4A — Denetimde değişen puanlar

| # | Önce | Sonra | Neden |
|---|:---:|:---:|---|
| 5 | 8 | **9** | Kendi yazdığım bağımsız IEC 104 istemcisi tam el sıkışma aldı, GIS içe aktarımını üç rolle uçtan uca sınadım ve günlük zincirini kurcalayarak doğruladım. Paralel okuma bu üç kanıtı ayrı ayrı görmüştü; bir arada değerlendirince kriter 5 "iki sınıf" çapasını üç sınıfla aşıyor. **Yukarı.** |
| 7 | 7 | **8** | Ajanlar ekranları kod üzerinden değerlendirmişti. Ben yedisini de sürüp görüntülere baktım ve API'den yaptığım onayın arayüzde doğru kullanıcıyla göründüğünü doğruladım — çapamın 9'undaki "izi kalır" halkası budur ve kodda görünmüyordu. **Yukarı.** |
| 2 | 8 | **7** | S3_condense'in hiçbir şey enjekte etmediğini kendi aritmetiğimle ölçtüm; 8 senaryodan biri boş. **Aşağı.** |
| 4 | 9 (saldırgan önerisi) | **8** | Saldırgan "haksız düşük" deyip 9 önerdi; kabul etmedim, çünkü nginx `resolver` açığını kendim ölçtüm ve çapamın 9'u "bir bileşen düşerse ne olur düşünülmüş" diyor. Yukarı revizyonu **reddettim.** |
| 1, 3, 6, 8, 9 | — | değişmedi | Her biri kendi kanıt defteriyle doğrulandı; 8 için BOM aritmetiğini kendim yaparak ajanın bulgusunu bağımsız teyit ettim. |

### 4B — BEYAN muhasebesi

Kanıt defterimde **9 satır** BEYAN olarak başladı. Sonuç:

| Kapanan (6) | Nasıl |
|---|---|
| `docs/12` sayıları | `validate.py` koştum, çıktı dosyayla birebir → ÖLÇTÜM |
| Mevsimsel eşik sayıları | `threshold_sweep.py --seasons` koştum → ÖLÇTÜM |
| 1.000 pano p95 / kayıp 0 | `fleet.py` ile iki ölçekte koştum → ÖLÇTÜM |
| Üç protokol tutarlılığı | Kendi IEC 104 istemcim + Modbus + REST → ÖLÇTÜM |
| C/Python eşitliği <1.5e-8 | İki derlemeyi de koştum → ÖLÇTÜM |
| Yetkilendirme uygulanıyor | curl ile dört senaryo → ÖLÇTÜM |

| Kapanmayan (3) — puandan **düşüldü** | Etkisi |
|---|---|
| **46–48× sıkıştırma oranı** | Parçalar 1 günden eski olmalı; ölçemedim. Ayrıca oranın sabit-etiketli şablon veriyle ölçüldüğü bildirildi (doğrulamadım). **Kriter 6'da 9 yerine 8** — bu tek başına yarım puan. |
| **Telegram'ın gerçek teslimatı** | Bot belirteci yok (doğru uygulama). Yetenek olarak cezalandırmadım; **README'nin kesin kipi** kriter 4'te YANILTICI olarak yazıldı. |
| **TEDAŞ şartname madde uyumu** | Şartname metnine erişmedim. Proje zaten "tam metne erişilmedi, hiçbir madde numarası yazılmadı — yazılsaydı uydurma olurdu" diyor. **Cezalandırmadım**; dürüstlük işaretidir. |

### 4C — En yüksek üç puana saldırı

**K5 = 9 — saldırı tutmadı, puan artık daha sağlam.** İddiaların hepsini tek bir dokümanın mı taşıdığını sordum: hayır. Modbus'ı `pymodbus` ile, IEC 104'ü **projenin kodunu hiç kullanmayan kendi ham soket istemcimle**, REST'i curl ile okudum — üç bağımsız yol. Girdiyi bozma denemesi: yanlış pano eşlemesiyle okuduğumda (SIM-00004 vs ADM-00001) **25/25 uyuşmazlık** aldım, doğru eşlemeyle **0/25**. Yani ölçüm gerçekten ayırt edici, totolojik değil. Rol denetimini dört ayrı kombinasyonla (belirteçsiz / yanlış / yetersiz rol / doğru rol) ve iki farklı uçta (alarm onayı, GIS aktarımı) sınadım. Günlük zincirini **bilerek bozdum** ve doğrulayıcı tam o satırı yakaladı. Saldırı tutmadı.

**K4 = 8 — saldırı kısmen tuttu, puan zaten düşürülmüştü.** "Tek komutla kalkıyor" iddiasını `down -v` ile sıfırdan sınadım (yani önceki durumdan miras kalan hiçbir şey yok) — tuttu. "Karantina 0"ı iki bağımsız yoldan doğruladım: `/health` sayaçları **ve** veritabanında `select count(*) from quarantine`. Ama girdiyi bozma denemem (backend'i yeniden başlatmak) **gerçek bir açık ortaya çıkardı** — UI 502'ye düştü. Bu yüzden saldırgan ajanın 9 önerisini reddettim.

**K6 = 8 — saldırı tutmadı ama bir sınır buldu.** Ölçümü **ben** koştum, dokümandan almadım; 100 panoda p95 farkı %0,6, 1.000 panoda %8 (farklı makine). Kayıp 0 her iki ölçekte de doğrulandı. "Sanallaştırılmış UI" iddiasını grep ile çürüttüm — ama bu iddia ölçeklenebilirlik **ölçümünü** etkilemiyor, yalnızca README'nin bir cümlesini. Sıkıştırma oranını ölçemediğim için 9'a çıkaramadım.

**Ayrıca: iki ajan bulgusunu çürüttüm** — bu, kendi kanıt zincirimin denetimidir:

1. **"RBAC istemci başlığından okunuyor, herhangi bir istemci `X-Operator-Role: supervisor` yazıp geçebilir."** `main.py:184` gerçekten doğrulanmamış bir başlık okuyor. Ama **atlatma testi yaptım**: başlık + belirteçsiz → **401**, başlık + yanlış rol belirteci → **403**. Middleware yalnızca *ek kısıt* koyuyor, hiçbir şey *vermiyor*; gerçek yetkilendirme ayrı belirteç katmanında. Sonuç: **yanıltıcı adlandırılmış gereksiz kod, güvenlik açığı değil.** Bu bulgu kabul edilseydi kriter 4 ve 5'ten haksız puan kırılırdı.
2. **"`validate.py` bir bool'u precision diye satıyor."** Kaynağı okudum: property'nin adı `precision_ok`, docstring metriği açıkça tanımlıyor ve README sayı uydurmayıp "yasaklı alarm 0" diyor. Geçerli olan daha dar itiraz — klasik FPR hiç hesaplanmıyor — kriter 2'ye yazıldı.

### 4D — Çapa denetimi

Sekiz puan çapalarına uyuyor. **Bir tanesi uymuyor ve bunu açıkça itiraf ediyorum:**

Kriter 2'ye 7 verdim, oysa Aşama 1 çapam "üreteç tespiti kendiliğinden kolay kılıyorsa **tavan 6**" diyordu. Puanı düzelttim mi, çapayı mı? **Çapayı esnettim** ve jürinin bunu görmesi gerekir. Gerekçem: çapayı yazarken aklımdaki senaryo "üreteç sağlıklı panoları dar bir aralıktan üretiyorsa" — yani *ayrımı* önemsizleştiren bir üreteçti. Buradaki döngüsellik farklı cinsten: model **yapısı** eşleşiyor ama gerçekleşme gürültülü (σ=0,2 K sensör gürültüsü, AR(1) stokastik yük) ve üç kanal (ark trip sayacı, haberleşme kaybı, sensör arızası) hiç model-tabanlı değil. Yine de bu, ölçüyü sonuca uydurmaktır ve başka bir değerlendirici çapaya harfiyen uyup **6** verirse itirazım olmaz. Bu tek puan, eşit ağırlıkta toplamı 7,56 → 7,44'e indirir; **hiçbir ağırlıkta kararı değiştirmez.**

### 4E — En az emek verdiğim kriter

Gözden geçirdiğimde **kriter 3** ve **kriter 5'in SCADA dışı yarısıydı** — ikincisi tam da projenin sustuğu yerdi (README kriteri "(SCADA)" diye daraltmıştı). İkisini de baştan ele aldım: kriter 3 için STL'in gerçekliğini bayt düzeyinde doğruladım (324 üçgen), üç BOM'un aritmetiğini yaptım, veri bütçesi aracını okudum ve nginx kurtarma açığını ölçtüm. Kriter 5 için CBS/GIS içe aktarımını üç rolle uçtan uca sınadım ve OMS/EPDK uçlarını okudum. **Bu yeniden değerlendirme kriter 5'i 8'den 9'a çıkardı** — yani projenin sustuğu yer, aleyhine değil lehine çıktı. Sessizliği sınamasaydım puanı eksik verecektim.

---

## 5. En güçlü üç şey

1. **Protokoller arası kanıtlanmış tutarlılık (kriter 5).** Aynı 25 sıcaklık noktasını üç taşımadan — REST, Modbus TCP, IEC 60870-5-104 — okudum ve **sıfır uyuşmazlık** buldum. IEC 104 tarafını projenin kodunu hiç kullanmayan, sıfırdan yazdığım bir istemciyle sınadım; standarda uygun tam el sıkışma aldım (ACTCON → 168 nesne → ACTTERM, 139 ölçülen değer). Yanlış pano eşlemesiyle okuduğumda 25/25 uyuşmazlık aldım — yani ölçüm ayırt edici, totolojik değil. Bir hackathon teslimatında bu düzeyde endüstriyel birlikte çalışabilirlik kanıtı nadirdir.

2. **Ölçümlerin yeniden üretilebilirliği.** `docs/12-dogrulama-sonuclari.md`, ben `scripts/validate.py`'yi koştuğumda üretim zaman damgası dışında **birebir aynı** çıktı. Beş `--check` üreteci "güncel" dedi, sözleşme denetimi tutarlı dedi. Yük testini iki ölçekte kendim koştum: 100 panoda p95 660,9 ms (doküman 657), 1.000 panoda 710,5 ms, **her ikisinde de kayıp 0**. `docs/09` ölçüm makinesini ve "yük üreteci aynı makinede, sonuçlar temkinli" notunu yazıyor. Bu, "doküman iddia eder, kod kanıtlar" disiplininin gerçekten kurulduğu anlamına gelir.

3. **Kurcalama-kanıtı denetim izi ve kapanan operasyon döngüsü.** Alarm yaşam döngüsü karma zincirine yazılıyor; bir satırın notunu **bilerek bozdum** ve `verify_journal.py` tam o halkayı adresleyerek "satır DEĞİŞTİRİLMİŞ" dedi, geri alınca "SAĞLAM". Ayrıca API'den yaptığım onay arayüzde "vardiya.amiri onayladı" olarak, doğru kullanıcıyla göründü — uyarı → bağlam → aksiyon → iz zinciri baştan sona çalışıyor. Bir dağıtım şirketinde alarm kimin ne zaman kapattığı sorusunun cevabı denetlenebilir olmak zorundadır; bu proje o cevabı üretiyor.

---

## 6. En zayıf üç şey

1. **Maliyet rakamları doğrulamayı geçmiyor (kriter 8).** Jüriye verilen dört sayıdan üçü tutmuyor. `pano-beyni` BOM'unun satır toplamı **70,73 / 47,68 USD**, beyan **56 / 37 USD** — %26 / %29 düşük; fark tam olarak hücresel modem kalemi ve dipnot yalnızca "SIM/veri hariç" diyor, modem donanımını saymıyor. "Sensör düğümleri **dahil** <120 USD" ifadesi kanıt gösterdiği `docs/10:23-25` ile **doğrudan çelişiyor** (o doküman "dahil **değildir**, kavramsal seviyede" diyor). "14-22 ayda amorti" hiçbir kod, doküman veya testten çıkmıyor — `git grep` tek satır buluyor. Projenin kendi iç raporu `<120 USD` sorununu 18 Eylül'de işaretlemiş, 19 Eylül'de düzeltilmemiş. Diğer sekiz kriterde uygulanan üreteç/`--check` disiplini **tam da bu dokümana uygulanmamış**.

2. **Ana başarı metriği yapısal olarak döngüsel (kriter 2).** Üreteç `dT[k+1] = a·dT[k] + (1−a)·K·I²` ile ilerletiyor; dedektör *aynı* denklemin parametrelerini kestiriyor ve arıza doğrudan kestirilen `K`'ya çarpan olarak enjekte ediliyor. Dolayısıyla "8 senaryoda duyarlılık 1,00" büyük ölçüde "kestirici kendi ileri modelini ters çevirebiliyor" demektir; model uyumsuzluğu, sensör doğrusalsızlığı, yeni pano tipi gibi sahadaki asıl zorluklar hiç sınanmıyor. Üstelik o 8 senaryodan biri (**S3_condense**) hiçbir şey enjekte etmiyor: beyan ettiği kış aralığında nem zaten %98 tavanında olduğu için `humidity_offset_pct: 25`'in etkisi tam **0,000**. Gerçek bir yanlış-pozitif oranı (TP/(TP+FP)) hiçbir yerde hesaplanmıyor.

3. **README, projenin kendi dokümanlarını aşıyor.** Bu bir üslup sorunu değil, jürinin ilk okuduğu belgenin güvenilirliği sorunudur. "9 tam operasyon ekranı (… Ayarlar)" — 7 rota var, `/ayarlar` "Sayfa bulunamadı" döndürüyor ve projenin kendi `docs/16:53`'ü zaten "9 ekranın 7'si çalışıyor" diyor. "Kontrast 16,0:1" — bugünkü token'larla ölçtüm, **13,33:1** (hâlâ AAA üstü, ama sayı bayat). "Sanallaştırılmış UI" — depoda sanallaştırma kütüphanesi yok. "158–209 saat" — ölçülen tek değer 209,0; 158 hiçbir çıktıda yok. "Optik ark sensör kartı hazır" — `hardware/` altında ark kartı yok. "Telegram … teslim edilir" — kanıt gösterilen bölümde Telegram hiç geçmiyor ve varsayılan yığında belirteç olmadığı için hiç çalışmıyor. Tek tek küçük olan bu sapmalar toplamda şu etkiyi yapıyor: jüri, doğrulanmış gerçek başarıları da indirimli okumaya başlar.

---

## 7. YANILTICI bulgular ve zayıf testler

### YANILTICI — iddia ile kod/çıktı uyuşmuyor

| # | İddia | Gerçek | Ağırlık |
|---|---|---|---|
| 1 | `README.md:32` "sensör düğümleri ve PD kartı dahil … <120 USD" | Kanıt gösterdiği `docs/10:23-25`: "dahil değildir … kavramsal seviyede" | **Ağır** — kendi kaynağıyla çelişiyor |
| 2 | `README.md:32` / `bom.csv:19` "~56 / ~37 USD" | Satır toplamı **70,73 / 47,68 USD** (kendi hesabım) | **Ağır** — %26/%29 |
| 3 | `README.md:32` "14-22 ayda amorti eder" | Deponun hiçbir yerinde üretilmiyor | **Ağır** — kaynaksız |
| 4 | `README.md:31` "9 tam operasyon ekranı (… Ayarlar)" | 7 rota; `/ayarlar` 404. `docs/16:53` zaten "7'si çalışıyor" diyor | Orta |
| 5 | `scenarios.py:119-129` S3_condense "yoğuşma enjekte edilmiş" | Kış aralığında offset etkisi tam 0 — hiçbir şey enjekte etmiyor | Orta — kriter 2'nin kanıtını zayıflatıyor |
| 6 | `README.md:30` "sanallaştırılmış UI" | Sanallaştırma kütüphanesi yok; sayfalama var | Orta |
| 7 | `README.md:26` "158–209 saat" | Ölçülen tek değer 209,0; 158 hiçbir çıktıda yok | Orta |
| 8 | `README.md:28` "Telegram … teslim edilir", kanıt `docs/17` §4.2 | `docs/` altında Telegram hiç geçmiyor; belirteç boş, çalışmıyor | Orta |
| 9 | `README.md:31` "kontrast 16,0:1" | Bugünkü token'larla 13,33:1 (AAA üstü) | Hafif — bayat sayı |
| 10 | `README.md:27` "optik ark sensör kartı BOM hazır" | `hardware/` altında ark kartı yok; ark TVOC-2'nin kendi sensöründen | Hafif |
| 11 | `README.md:29` "uzaktan röle denetimi" | Yazılabilir blokta röle komutu yok | Hafif |
| 12 | `ana-dongu.md:110` "320 B / 8,0 KB" | Kendi derlememde 384 B / 9,4 KB | Hafif — sonuç değişmiyor |
| 13 | `main.py:173` "IEC 62351-8 RBAC" | Rolü doğrulanmamış istemci başlığından okuyor | Hafif — **atlatma değil** (test ettim: 401/403), yanıltıcı adlandırılmış ölü kod |

**Not — donanım iddiası temizdir.** Şartnamenin ağır cezalandırılmasını istediği durumu (donanım yokken "donanımda doğrulandı" demek) **aradım ve bulamadım.** Tersine, `README.md:139` "Donanım satın alınmadı", `docs/17` §6 24 satırlık sapma tablosu, `scripts/ornek-cbs-aktarim.json:2` "ÖRNEKTİR — GERÇEK CBS VERİSİ DEĞİLDİR", `docs/19:26-28` "şartnamenin tam metnine erişilmedi, hiçbir madde numarası yazılmadı — yazılsaydı uydurma olurdu". Bu proje sınırını sistematik olarak kendisi çiziyor; yukarıdaki 13 maddenin **tamamı README'nin pazarlama katmanında** yoğunlaşıyor, mühendislik dokümanlarında değil.

### Zayıf testler

**Aradım; klasik zayıf test kalıplarının hiçbirini bulamadım** — bu projenin lehinedir ve beklemediğim bir sonuçtu.

- `firmware/tests/test_rls.c`: Python'un ürettiği **harici** CSV'yi okuyup her adımda K, tau ve `excited` karşılaştırıyor; beklenen değeri test içinde yeniden hesaplamıyor. **Güçlü test.**
- Atlanan 37 backend testi: hepsi `TEST_DB_DSN` gerektiriyor ve **gerçek veritabanı bağlayınca 46'sı geçti** — sessizce atlanan değil, ortama bağlı testler.
- `skip`/`xfail` işaretli, hiç toplanmayan veya totolojik test görmedim; 489 + 899 + 136 + 5 testin hepsi gerçekten koşuyor.
- Test sayıları README'de **eksik** yazılmış (401 vs gerçek 489; 656 vs 899; 85 vs 136) — yani abartı değil, tersine eksik beyan.

**İki gerçek test boşluğu var** (zayıf test değil, testin **yokluğu**):

1. **Arayüzün hiçbir bileşen/render testi yok.** 136 frontend testinin tamamı `lib/` + `api/` saf fonksiyon testi; `.test.tsx` dosyası 0, `testing-library` bağımlılığı yok. Yedi ekranın çalıştığını ben gördüm, ama bir regresyon bunu sessizce bozar.
2. **Playwright sonucu var, tezgahı yok.** `KALAN-EKSIKLER.md:34` ve `docs/17:159` "Playwright: 7 ekran, 0 konsol hatası" diyor; depoda Playwright yapılandırması/spec/bağımlılığı yok. **Sonucu bağımsız olarak ben doğruladım** — yani sayı doğru, ama depodan yeniden üretilemiyor.

---

## 8. Doğrulayamadıklarım

| Ne | Neden | Hangi puanı ne kadar etkileyebilir |
|---|---|---|
| **TimescaleDB 46–48× sıkıştırma** | Sıkıştırma 1 günden eski parçalara uygulanıyor; oturumumdaki tüm veri taze (`0/1 parça sıkıştırılmış`). Politika yapılandırmasını doğruladım, oranı ölçemedim. | **Kriter 6: ±1.** Oran gerçek veride şablon veriden düşük çıkarsa (etiketlerin yarısından fazlası sabit) 8 → 7. Doğrulanırsa 8 → 9. |
| **Telegram'ın gerçek telefona teslimatı** | `TELEGRAM_BOT_TOKEN` boş — sırrın commit edilmemesi doğru uygulamadır, projenin kusuru değil. | **Kriter 4: +0/+0,5.** Yetenek olarak cezalandırmadım; yalnızca README'nin kesin kipini yanıltıcı yazdım. |
| **TEDAŞ şartname madde uyumu** | Şartnamenin tam metnine erişmedim. Proje zaten erişemediğini ve bu yüzden hiçbir madde numarası yazmadığını beyan ediyor. | **Kriter 3: +0/+1.** Cezalandırmadım (dürüstlük işareti). Şartname elde doğrulanırsa 7 → 8 olabilir. |
| **Modbus register haritasının cihaz kılavuzlarıyla tam karşılaştırması** | 430 register × iki kılavuz PDF'i; oturum içinde yapılamadı. Bir örnek doğrulandı (`devices.py:60-65` `0x42B6 → 2016-10-04` tarih kodlaması, kılavuz örneğiyle uyumlu). | **Kriter 5: −0/−1.** Sistematik adres hatası çıkarsa 9 → 8. Tutarlılık denetimi (`check_contracts`) iç tutarlılığı garanti ediyor, kılavuza sadakati değil. |
| **S8 sensör arızasının tohum duyarlılığı** | Paralel okuma, bazı tohumlarda `ALM-K-ALM`'in tetiklendiğini bildirdi; ben 12 tohumla yeniden koşmadım. | **Kriter 2: −0/−0,5.** Doğruysa "yasaklı alarm 0" koşulsuz değil, tohuma bağlı olur. |
| **Gerçek saha verisiyle davranış** | Kurum ölçüm verisi vermedi (`İstenen Veriler.xlsx` yalnızca cihaz/ölçek tanımı, "Sıcaklık_Nem" sayfası boş). Şartname sentetik veriyi serbest bırakıyor. | **Cezalandırılamaz.** Ama kriter 2'deki döngüsellik ancak gerçek veriyle kapanır. |

---

## 9. Jüri masasında sorulacak beş soru

Bu beşinin cevabı dokümanda hazır **değildir** ve projenin en zayıf beş noktasını sınar.

1. **Üreteciniz ısıyı `dT[k+1] = a·dT[k] + (1−a)·K·I²` ile ilerletiyor; dedektörünüz aynı denklemin `K`'sını kestiriyor ve arızayı da doğrudan `K`'ya çarpan olarak enjekte ediyorsunuz. Dedektörün varsaymadığı bir fizik ekleseydik — örneğin komşu hücreden ısıl kuplaj, ya da τ'nun yükle değişmesi — "duyarlılık 1,00" ne olurdu? Bu deneyi yapmadıysanız, jüriye o sayıyı hangi anlamda sunuyorsunuz?**
   *Neden soruyorum:* Kriter 2'nin tüm kanıt yükü bu sayıda ve sayı, kestiricinin kendi ileri modelini ters çevirmesini ölçüyor.

2. **`hardware/pano-beyni/bom.csv` satırlarının toplamı 70,73 USD; dosyanın dipnotu ve README "~56 USD" diyor. Aradaki 14,50 USD tam olarak hücresel modem kalemi. Modemi kapsam dışı bırakmak bilinçli bir karar mıydı — öyleyse modemsiz bir pano beyni sahaya veriyi nasıl gönderecek, ve neden dipnotta yalnızca "SIM/veri hariç" yazıyor?**
   *Neden soruyorum:* Kriter 8'in üç rakamından biri bu ve `sensor-dugumu` BOM'unun dipnotu birebir doğru — yani ekip bunu doğru yapabiliyor.

3. **README "1 engellenen yangında 14-22 ayda amorti" diyor. Bu aralığı üreten hesabı ve girdilerini gösterebilir misiniz — yıllık arıza olasılığı, arıza başına maliyet, filo büyüklüğü? Ayrıca: `GELISTIRME-BACKLOGU.md:656`'da Weibull arıza modelini "kendi varsayımımızı geri okur" diyerek eleyen disiplin, neden bu sayıya uygulanmadı?**
   *Neden soruyorum:* Depoda bu sayıyı üreten hiçbir şey yok, oysa proje aynı türden bir modeli daha önce bilinçle reddetmiş.

4. **Backend konteynerini yeniden başlattım; frontend nginx eski IP'yi tuttuğu için operatör arayüzü 502 verdi ve frontend yeniden başlatılana kadar ölü kaldı. Üretimde backend yeniden başlatması rutin bir olaydır (dağıtım, OOM, çökme). Nöbetçi operatör bu durumda ekranın bayat mı yoksa ölü mü olduğunu nereden anlar, ve kurtarma kimin görevi?**
   *Neden soruyorum:* Kriter 3 ve 4'ün kesiştiği yer; bir kontrol odası ekranının sessizce ölmesi alarm izleme sisteminde en tehlikeli hata modudur.

5. **S3_condense senaryonuz `season="kis"` ve `humidity_offset_pct: 25` ile tanımlı, ama kış sıcaklıklarında nem modeliniz zaten %98 tavanında olduğu için bu offset'in etkisi tam sıfır — senaryo, S0'ın kışta koşulmuş hâliyle bit bit aynı. Bunu fark ettiniz mi, ve "8 anomali senaryosunda duyarlılık 1,00" ifadesini yedi senaryoya mı düzeltmek gerekir?**
   *Neden soruyorum:* Cevap "fark etmedik" ise bu dürüst bir hatadır ve `docs/05:437-443` zaten yakınından geçmiş; "fark ettik" ise senaryo listesinin neden düzeltilmediğini sormak gerekir.

---

## Ek A — Aşama 1'de yazdığım çapalar

> Aşağıdakiler depoya **bakmadan önce**, ilk araç çağrısından hemen sonra yazıldı ve sonradan değiştirilmedi. Tek istisna kriter 2'nin döngüsellik tavanıdır; onu esnettiğimi §4D'de açıkça yazdım ve her iki hâli de aşağıda gösteriyorum.

**K1 — Problemin doğru anlaşılması.** *3:* Problemi şartnamenin kelimeleriyle tekrar ediyor; "trafo/pano arızası kötüdür" düzeyinde. *6:* Somut arıza modları sayılmış ve hangi veriyle görüleceği yazılmış, ama fiziksel/operasyonel gerekçe yüzeysel. *9:* Arıza modu → fiziksel belirti → ölçülebilir sinyal → operasyonel karar zinciri yazılı; dağıtım şebekesinin gerçek kısıtları (OG/AG ayrımı, sayaç/AMR gerçekliği, saha ekibi iş akışı, EPDK kalite göstergeleri) doğru kullanılmış; problemin **neyi kapsamadığı** da yazılı.

**K2 — Anomali ve risk tespit yaklaşımının başarısı.** *3:* "Makine öğrenmesi kullanacağız" veya tek sabit eşik; metrik yok. *6:* Çalışan bir dedektör var, sentetik veride sonuç üretiyor; yanlış-pozitif oranı ve eşiklerin kaynağı belirsiz. *9:* Yöntem seçimi gerekçeli; en az bir nicel değerlendirme (precision/recall/FPR veya tespit gecikmesi) ve ölçüm koşulu yazılı; eşikler veriden/sözleşmeden türetiliyor, sabit kodlanmamış; yöntemin **nerede çökeceği** yazılı; yanlış alarm maliyeti düşünülmüş. *Ceza (yazıldığı hâliyle):* Üreteç tespiti kendiliğinden kolay kılıyorsa (sağlıklı sınıf dar bir aralıktan, anomali açıkça dışından üretiliyorsa) yüksek skor yöntemin değil üretecin eseridir → **tavan 6**. *(Uygulanan hâli: 7 — gerekçesi §4D.)*

**K3 — Saha koşullarında uygulanabilirlik.** *3:* Laptopta çalışan demo; saha = "Raspberry Pi'ye koyarız". *6:* Donanım/haberleşme seçimi somut (hangi modül, protokol, bant genişliği) ve en az bir saha kısıtı (güç, IP koruma, GSM kapsama) ele alınmış; kurulum/bakım iş akışı yok. *9:* Kısıtlar sayılarla (veri bütçesi, güç, kopukluk toleransı, saat senkronu), kopuk çalışma ve cihaz kimliği düşünülmüş, devreye alma adımları bir saha ekibinin izleyebileceği kadar somut, ve bunların bir kısmı kodda/testte karşılıklı. *Not:* Fiziksel donanım yokluğu ceza değil; "donanımda doğrulandı" denip donanım yoksa YANILTICI, ağır ceza.

**K4 — Uçtan uca sistem yaklaşımı.** *3:* Tek notebook/script; "backend/frontend yapılacak". *6:* En az iki katman gerçekten çalışıyor ve bir komutla kalkıyor; kalıcılık, hata yolları, yeniden başlatma davranışı belirsiz. *9:* Edge → taşıma → işleme → depolama → sunum → uyarı zinciri bütün olarak kalkıyor; bir yabancı README'yi izleyerek kaldırabiliyor; sağlık uçları, testler, bileşen sınırları tanımlı; **bir bileşen düşerse ne olduğu düşünülmüş**.

**K5 — Mevcut operasyon sistemleriyle entegrasyon** (SCADA, OMS, CBS/GIS, çağrı merkezi, varlık yönetimi, iş emri — hepsi kapsamda). *3:* "SCADA ile entegre olur" cümlesi; arayüz tanımı yok. *6:* En az bir gerçek standart/protokol adlandırılmış ve bir yönü uygulanmış (IEC 61850 / DNP3 / Modbus / MQTT / REST webhook) veya bir dışa aktarım formatı var; eşleme ve kimlik/yetki eksik. *9:* En az **iki farklı operasyon sistemi sınıfına** somut arayüz; veri modeli eşlemesi yazılı (hangi alan nereye); kimlik doğrulama/yetkilendirme çalışıyor; sahte/stub karşı uçla uçtan uca denenmiş ve testi var; varlık kimliği gerçek kurum kodlamasıyla uyumlu.

**K6 — Ölçeklenebilirlik.** *3:* "Kubernetes'e koyarız"; hiç sayı yok. *6:* Ölçeklenmeyi mümkün kılan mimari seçim (kuyruk, zaman serisi DB, stateless servis) ve kaba hesap (N pano × M ölçüm/sn); ölçüm yok. *9:* Gerçek yük ölçümü (mesaj/sn, cihaz sayısı, gecikme yüzdelikleri, kaynak kullanımı), darboğaz adlandırılmış ve **ölçüme dayanıyor**; saklama/downsampling ve maliyetin cihaz sayısıyla büyümesi yazılı; 10k+ pano senaryosu somut.

**K7 — Kullanıcı/operasyon deneyimi.** *3:* Boş iskelet veya ham JSON; ekran görüntüsü yok. *6:* Çalışan pano var, veri gösteriyor, birkaç ekran gezilebiliyor; "operatör bu ekranı görünce ne yapar" sorusunun cevabı arayüzde yok, alarm yönetimi (kabul/kapatma/atama) yok. *9:* Rolü belli kullanıcı için akış tasarlanmış: uyarı gelir → bağlam görünür → aksiyon alınır (kabul/iş emri/susturma) → **izi kalır**; alarm yorgunluğu düşünülmüş; ekranlar gerçekten dolu ve konsol hatasız.

**K8 — Maliyet ve sağlanan fayda.** *3:* "Maliyeti düşüktür, faydası yüksektir"; sayı yok. *6:* BOM kalem kalem fiyatlanmış **veya** fayda bir metriğe bağlanmış; varsayımlar kısmen yazılı. *9:* Cihaz başı CAPEX + OPEX (haberleşme, bulut, bakım) sayılarla; fayda ölçülebilir operasyonel büyüklüğe bağlı (SAIDI/SAIFI, kayıp-kaçak, trafo ömrü, ekip yol maliyeti) ve kaynak gösterilmiş; geri ödeme süresi ve duyarlılık analizi var; varsayımların uydurma olduğu yerler açıkça işaretlenmiş.

**K9 — Yenilikçilik.** *3:* Standart CRUD pano + eşik alarmı; farkı söylenmemiş. *6:* En az bir gerçekten alışılmadık fikir var ve neden farklı olduğu yazılı; ama uygulanmamış ya da yüzeysel uygulanmış. *9:* Özgün fikir hem tanımlı hem çalışır hâlde; mevcut çözümlere göre farkı somut bir şeyle gösterilmiş (karşılaştırma, ölçüm veya eleyici bir kısıtı çözmesi); yenilik gösteriş değil, problemi çözüyor. *Not:* "LLM kullandık" tek başına yenilik değildir.

---

## Kapanış

Bu proje, hackathon teslimatlarında alışılmadık bir şeyi yapmış: iddialarının çoğunu yeniden çalıştırılabilir üreteçlere bağlamış, ve ben bunların çoğunu bağımsız olarak yeniden ürettim — `docs/12` birebir, mevsim sayıları birebir, yük testi iki ölçekte, üç protokol sıfır fark. Zayıflığı da aynı yerden geliyor: bu disiplinin **uygulanmadığı tek doküman README'dir** ve jürinin ilk okuduğu belge odur. Kriter 8'deki üç rakam ve kriter 2'deki yapısal döngüsellik gerçek eksiklerdir; geri kalanın büyük kısmı, pazarlama katmanının mühendislik katmanının önüne geçmesidir. Ekip kendi sınırlarını `docs/17` §6'da, `docs/16:53`'te ve hatta kendi inovasyon raporunda açıkça çizmiş — README'yi o dokümanların söylediği yere çekmek, bu projeyi jüri masasında bugün olduğundan daha güçlü yapardı.

İki notu ayrıca vurgulamak isterim, çünkü değerlendirme sürecinin kendisine dair:

- **İki ağır ithamı çürüttüm.** Paralel okuma "RBAC istemci başlığından okunuyor, herkes `X-Operator-Role: supervisor` yazıp geçer" dedi; atlatma testini koştum, **geçmiyor** (401/403). Ve "`validate.py` bir bool'u precision diye satıyor" dedi; kaynak `precision_ok` adında ve tanımını yazıyor. İkisi de kabul edilseydi proje haksız puan kaybederdi.
- **Kendi hatamı düzelttim.** İlk üç-protokol karşılaştırmamda yanlış panoyu okuyup 25/25 uyuşmazlık buldum; `gateway.py:162`'yi okuyup birim eşlemesini düzeltince **0/25** çıktı. Bu bir proje kusuru değil, benim kurulum hatamdı.
