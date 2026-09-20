# Grid Up Hackathon 2026 — Bağımsız Değerlendirme

**Proje:** Pano/Hücre İçi Anomali Erken Uyarı ve Kestirimci Bakım Sistemi (GridUp)
**Depo durumu:** `c6b5dcd` · 2026-09-20 02:13:48 +0300 · çalışma ağacı temiz
**Değerlendirme tarihi:** 2026-09-20
**Değerlendirici:** Bağımsız teknik değerlendirici (projeyi yazmadım, ekibi tanımıyorum)

> **Bu raporun kuralı:** Bir sayıyı rapora yazdıysam ya o sayıyı üreten komutu ben
> çalıştırdım (`ÖLÇTÜM`), ya onu üreten kodu ben okudum (`OKUDUM`), ya da yanında
> `BEYAN` etiketi vardır. Dördüncü seçenek yok.
>
> Projenin kendi dokümanlarındaki kriter-kanıt tabloları (README "Jüri Kanıt
> Haritası", `TAM_ANALIZ.md`, `STATUS.md`, `docs/17`) bu raporun **girdisi değil,
> denetlenen nesnesidir**. Hiçbir sayı oradan kopyalanmadı.

---

## 0. Nasıl değerlendirdim

### 0.1 Sıra

Dokuz kriterin 3/6/9 çapalarını **depoyu açmadan önce** yazdım (Ek A). Sonra depoyu
açtım, komutları koştum, kodu okudum, puanladım, kendi puanlarımı denetledim.

### 0.2 Çalıştırdığım komutlar (hepsinin çıktısını gördüm)

| # | Komut | Sonuç |
|---|---|---|
| 1 | `docker ps` | 9 servis ayakta (yığın zaten kalkmıştı) |
| 2 | `backend/ pytest -q` | **896 geçti, 37 atlandı**, 177 s |
| 3 | `libs/panoalgo/ pytest -q` | **500 geçti, 0 atlandı**, 132 s |
| 4 | `sim/ pytest -q` | **41 geçti**, 100 s |
| 5 | `cmake -S firmware -B … && ctest` (double) | **5/5 geçti** |
| 6 | `cmake … -DPANO_USE_FLOAT=ON && ctest` | **5/5 geçti** |
| 7 | `test_rls.exe data/fixtures/rls_vectors.csv` | 240 adım; double K **1,362e-08**, float K **6,774e-06** |
| 8 | `python -m panoalgo.vectors --out <geçici>` | Depodaki CSV ile **bayt bayt aynı** |
| 9 | `npx vitest run` | **162 test / 19 dosya geçti** |
| 10 | `GRIDUP_E2E_KIP=canli npx playwright test` | **2 geçti**; 10 rota, **0 konsol hatası**, 23 kontrast ihlali |
| 11 | `npx playwright test` (mock) ×2 | **8 geçti, 2 DÜŞTÜ** (tekrarlanabilir) |
| 12 | `python scripts/validate.py --out <geçici>` | 14 senaryo; `docs/12` ile **tek fark: zaman damgası** |
| 13 | `python scripts/threshold_sweep.py --seasons` | kış **28,6** · geçiş **71,4** · yaz **0,0**; 0,5/0,0 → **228,6** |
| 14 | `python scripts/check_contracts.py` | 5 dosya, 430 register, 23 alarm kodu — **TUTARLI** |
| 15 | `gen_{modbus,iec104,alarm,grafana}_doc.py --check` | Dördü de **"guncel"** |
| 16 | `python scripts/tazminat_maruziyeti.py --duyarlilik` | Girdisiz: her kalem **"veri yok"** |
| 17 | `… --parametreler … --duyarlilik` | 1,33× ×3 girdi; 4/7/25 düğüm → **7,4 / 10,4 / 28,3 ay** |
| 18 | BOM CSV'lerini kendim topladım | **9 rakamın 9'u birebir** tuttu |
| 19 | pymodbus FC03 :502 ↔ REST :8000 | **0/25 uyuşmazlık** |
| 20 | Kendi yazdığım ham IEC 104 istemcisi :2404 | STARTDT con, GI act-con/act-term, **139 ölçüm + 29 tekil nokta**; REST ile **0/25** |
| 21 | `POST /alarms/76/ack` — 4 kimlik varyantı | **401 / 403 / 401 / 200** |
| 22 | `python scripts/verify_journal.py --dsn …` | **ZİNCİR SAĞLAM — 161 halka** |
| 23 | Hash zincirini **kendi kodumla** yeniden hesapladım | **164/164 halka tuttu**; kurcalama benzetimi özeti değiştirdi |
| 24 | S1 fixtüründen alarm zamanlarını çıkardım | K-WARN **226,5 h**, THR-TERM-ALM **399,0 h** → **172,5 h** |
| 25 | S13 fixtüründen ölçüm sıkışması | ölçülen **48,48 K** doğrulandı |
| 26 | `python scripts/sir_taramasi.py` | **temiz** — 522 izlenen dosya |
| 27 | Playwright ile 7 ekranın görüntüsünü aldım | Hepsine **baktım** (aşağıda) |
| 28 | `GET /api/v1/panels/ADM-00001/power-quality` | Canlı EN 50160 değerlendirmesi döndü |

### 0.3 Okuduğum kod (tam liste değil, kritik olanlar)

`libs/panoalgo/panoalgo/`: `detect.py`, `generator.py`, `physics.py`, `power_quality.py`,
`validate.py`, `vectors.py` · `backend/app/`: `auth.py`, `journal_chain.py`, `ingest.py`,
`epdk.py`, `api/panels.py`, `scada/iec104_points.py` · `firmware/`: `CMakeLists.txt`,
`core/dewpoint.c/.h`, `tests/test_rls.c` · `frontend/`: `playwright.config.ts`,
`e2e/smoke.spec.ts`, `src/theme.test.ts`, `src/components/Ikiz3D.tsx`,
`src/pages/PanoDetay.tsx` · `loadtest/fleet.py` · `sim/panobeyni_sim.py` ·
`contracts/modbus-map.yaml`, `alarm-codes.yaml`, `openapi.yaml` · `deploy/compose*.yaml`,
`deploy/.env.example` · `docs/05, 09, 12, 13, 14, 17, 18` · `Hackathon Verileri/İstenen Veriler.xlsx`

### 0.4 Yapamadıklarım ve nedeni

| Yapamadığım | Neden | Etiket |
|---|---|---|
| Yük testi (`loadtest/fleet.py`) | Betik bitişte backend konteynerini yeniden başlatıyor; sanal alan konteyner yazma/yeniden başlatmayı reddetti. Ayrıca canlı demo veritabanına SIM-* yazar. | **DOĞRULANAMADI — ortam** |
| 37 atlanan DB entegrasyon testi | Ayrı bir denetim veritabanı açmak istedim; `docker exec … psql` yazma izni reddedildi. Canlı `gridup` veritabanına koşmak demo verisini bozardı (bir test `alarm_journal`'ın ilk satırını kurcalıyor). | **DOĞRULANAMADI — ortam** |
| mTLS / topic ACL (F-27) | `--profile mtls` varsayılan kapalı; broker'ı ayağa kaldırmak konteyner işlemi gerektiriyor. | **DOĞRULANAMADI — ortam** |
| Telegram kanalı | `TELEGRAM_BOT_TOKEN` boş (proje bunu **kendisi yazıyor**). | **DOĞRULANAMADI — tasarım gereği** |
| Şartname PDF'lerinin madde madde kapsam denetimi | 8 PDF, zaman kısıtı. `İstenen Veriler.xlsx`'i okudum, PDF'leri okumadım. | **Kendi eksiğim** |

**Ortam notu — kendi hatamı düzeltiyorum:** `scripts/validate.py`'yi ilk koşumda
`backend/.venv` ile denedim ve `pandas` bulunamadı. Sonra `libs/panoalgo/.venv`'in
**pandas 2.2.3 ile zaten hazır olduğunu** gördüm. Yani bu bir proje eksiği değildi,
benim yanlış yorumlayıcı seçimimdi. Projeye eksi yazılmadı.

---

## 1. Puan tablosu (Aşama 4 denetiminden GEÇMİŞ hâli)

| # | Kriter | Puan | Tek cümlelik gerekçe | Kanıt türü |
|---|---|:---:|---|---|
| 1 | Problemin doğru anlaşılması | **8** | Kurumun `İstenen Veriler.xlsx`'te istediği üç kalemin üçü de kodda karşılanmış (`devices.py` mA sekonder + çarpan, TVOC-2 Modbus simülatörü, `alarm-codes.yaml` HFCT/PD); kapsam dışı bırakılanlar gerekçesiyle yazılı — fayda tarafı ise ölçüm değil varsayım. | ÖLÇTÜM + OKUDUM |
| 2 | Anomali ve risk tespit **yaklaşımının** başarısı | **8** | Yöntem gerekçeli, sabit 70 K taban çizgisine karşı ölçülmüş, metrik betiği tekrar koştuğumda aynı dosyayı üretti; ama manşet 1,00 duyarlılık üreteç ile dedektörün **aynı denklemi çözmesinden** geliyor ve bunu proje kendisi yazıyor. | ÖLÇTÜM + OKUDUM |
| 3 | Çözümün saha koşullarında uygulanabilirliği | **7** | Çevrimdışı halka tampon kodda var ve üç ayrı testle sınanıyor, veri bütçesi sayısal; ama hiçbir kart üretilmedi, hiçbir fiyat veri sayfasına karşı doğrulanmadı (proje bunu yazıyor) ve kurulum prosedürü yalnızca doküman. | OKUDUM + BEYAN |
| 4 | Uçtan uca sistem **yaklaşımı** | **8** | Tek komutla 9 servis; canlı `/health` `received 2169 / rejected 0 / dropped 0`; zincirin her halkasının kodu var ve şema dışı mesaj düşürülmeyip karantinaya yazılıyor — ama en güçlü entegrasyon testleri varsayılan koşumda atlanıyor. | ÖLÇTÜM + OKUDUM |
| 5 | Mevcut **operasyon sistemleriyle** entegrasyon kabiliyeti | **8** | İki sanayi protokolünü **bağımsız istemcilerle** doğruladım (pymodbus FC03; kendi yazdığım ham IEC 104 istemcisi doğru GI dizisini aldı), üç taşımada 0/25 fark, RBAC 401/403/200 — ama çağrı merkezi ve iş emri entegrasyonu **yok**. | ÖLÇTÜM |
| 6 | Ölçeklenebilirlik | **7** | Yük tezgâhı metodolojik olarak dürüst ve doyma noktasını kendisi yayımlıyor; ama tek bir sayısını bile yeniden üretemedim, `loadtest/results/` sürüm kontrolü dışında ve depodaki tek ölçüm eseri dokümandakinden farklı. | BEYAN + OKUDUM |
| 7 | Kullanıcı/operasyon deneyimi | **7** | 10 rotada **0 konsol hatası** ölçtüm ve operatör döngüsü (Neden/Ne doğrulanmalı/Ne yapmalı/Ne kadar acil → onay → denetim izi) ekranda gerçek; ama yayımlanan "5 kontrast ihlali" bugün **83** ve onu koruyan test **kırmızı**. | ÖLÇTÜM + OKUDUM |
| 8 | Maliyet ve sağlanan fayda | **8** | README'deki dokuz BOM rakamının dokuzunu da CSV satırlarından kendim toplayıp birebir doğruladım, duyarlılık analizi doğru ve betik girdisiz hiçbir sayı uydurmuyor; ama faydanın tamamı `[varsayım]` etiketli. | ÖLÇTÜM |
| 9 | Yenilikçilik | **8** | Kenar-merkez uyumunu uçtan uca ben doğruladım (vektörü Python'dan bayt bayt yeniden ürettim, C'yi **başka bir derleyiciyle** tazeden derledim, 240 adım tuttu) ve rakip matrisi gerçek; ama README §9'un manşet sayısı ölçümle uyuşmuyor. | ÖLÇTÜM + OKUDUM |

**Toplam (eşit ağırlık): 69/90 = 7,7/10**

---

## 2. Üç ağırlık, üç toplam

| Ağırlıklandırma | Hesap | Sonuç |
|---|---|---|
| **A — Eşit** | 69 / 9 | **7,67 / 10** |
| **B — Teknik** (K2, K4, K5 çift) | 93 / 12 | **7,75 / 10** |
| **C — Ticari** (K1, K3, K8 çift) | 92 / 12 | **7,67 / 10** |

### Karar üç ağırlıkta da aynı mı? **Evet — ve fark hesaplama gürültüsü düzeyinde (0,08 puan).**

Bu sonuç sağlamdır ve sağlamlığının **yapısal bir sebebi** var: projenin puanları
7 ile 8 arasında sıkışmış, yani hiçbir kriterde ne çöküş ne de parlama var. Ağırlık
değiştirmek, birbirine bu kadar yakın dokuz sayının ortalamasını oynatamaz.

**Jüriye asıl söylenmesi gereken bu:** GridUp, "bir konuda olağanüstü, üç konuda boş"
tipi bir hackathon projesi **değildir**. Dokuz kriterin dokuzunda da çalışan bir şey
var. Bunun bedeli de var — hiçbir kriterde 9-10 yok.

Yine de hangi bakışın neyi öne çıkardığı önemli:

- **Teknik jüri (B)** en yüksek sonucu verir, çünkü projenin en iyi kanıtlanmış
  yanı entegrasyon (K5) ve uçtan uca bütünlük (K4). Bu iki kriter benim birinci
  elden ÖLÇTÜM kanıtımla desteklenen yerler.
- **Ticari bakış (C)** en düşüğü verir, çünkü çift ağırlık verilen K3 (saha) puanı
  7'dir: donanım üretilmedi, kurulum işçiliği hiçbir toplamda yok.
- **Belirleyici kriter K3'tür.** K3'ü 7 yerine 9 saysaydım C **8,0**'a çıkar ve
  ticari bakış teknik bakışı geçerdi. K3'ü 5'e indirseydim C **7,3**'e düşerdi.
  Yani "donanımın gerçekten yapılabilirliğine ne kadar inanıyorsunuz" sorusu bu
  projede tek başına ±0,4 puan oynatır; diğer sekiz kriterin hiçbiri bu kadar
  oynatmaz.

---

## 3. Kriter kriter kanıt defteri

### Kriter 1 — Problemin doğru anlaşılması → **8/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| Kurumun istediği mA sekonder + çarpan koda döndü | `README.md:24` | **OKUDUM** | `libs/panoalgo/panoalgo/devices.py:221-224`: `MPR_CT_REGISTER = 0x8001`, `MPR_CURRENT_SCALE = 0.001`, yorum `I_primer = ham * 0.001 * CT`. `İstenen Veriler.xlsx` hücre 5-9 ("Sekonder Cinsten Akım Değeri / mA / Çarpan / A / Hesaplanan Primer Akım") ile birebir örtüşüyor. |
| ABB TVOC-2 Modbus'tan okunuyor | `README.md:24` | **ÖLÇTÜM** | `sim/tvoc2_sim.py` var; `docker ps` → `gridup-tvoc-sim` :5021 ayakta. `İstenen Veriler.xlsx` hücre 10-11 aynı şeyi istiyor. |
| HFCT/EA Technology PD kodu var | `contracts/alarm-codes.yaml:162` | **OKUDUM** | `ALM-PD-TREND`, `basis: "EA Technology kalici HFCT trend yaklasimi"`. **Eşik bilerek tanımlanmamış** ve nedeni yazılı: "PD yalnizca OG hucre/trafo icin anlamlidir ve AG panoda telemetri semasi geregi pd: null gelir". Bu bir eksik değil, yazılı bir kapsam sınırıdır. |
| Hedef: 1600 kVA TEDAŞ tipi AG panosu | `README.md:13` | **OKUDUM** | `contracts/modbus-map.yaml:36` `pano_type: 1 = 1600 kVA dahili (EK-II/14)`; 25 ölçüm noktası (GİRİŞ L1-L3+N, DSYA1-7 × 3 faz) sözleşmede sayılı. |
| Mevcut cihazlar sensör olarak kullanılıyor, kablo kalabalığı artmıyor | `README.md:13` | **OKUDUM** | `scripts/tazminat_maruziyeti.py` çıktısı 10 kalemi sayıyor (4 AT, 3 gerilim girişi, 2 ark dedektörü, 1 ark merkez ünitesi) ve bunların BOM'a eklenmediğini gösteriyor. |
| Kapsam dışı bırakılanlar yazılı | `docs/16 §2`, `docs/18 a.3` | **ÖLÇTÜM** | 9 ekranın 7'si çalışıyor, Ayarlar ekranı ve mobil PWA kapsam dışı ilan edilmiş; `docs/18` satır 5-14'te 14 yetenek "karar mı, boşluk mu" diye ayrılmış. |
| Fayda ölçülebilir etkiye bağlanmış | `README.md:32` | **KISMİ** | `scripts/tazminat_maruziyeti.py` çıktısında P(arıza), arıza başı maliyet ve tespit oranı **`[varsayim]`** etiketli; EPDK eşikleri ve tarife "veri yok". Yani etki niceliksel **değil**, ve proje bunu saklamıyor. |

**Puanın gerekçesi.** Çapamda 9 için "ölçülebilir etkiyle gerekçelenmiş" istemiştim;
fayda tarafı varsayım olduğu için 9 vermedim. 8, şunun karşılığı: hedef varlık,
arıza modları ve **kurumun kendi veri talebi** kodda tek tek karşılanmış, kapsam
sınırları yazılı. Şartname PDF'lerinin madde madde denetimini yapmadım (§0.4).

---

### Kriter 2 — Anomali ve risk tespit **yaklaşımının** başarısı → **8/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| Eşleşen modelde duyarlılık 1,00, yasaklı alarm 0 | `README.md:26` | **ÖLÇTÜM** | `validate.py`'yi geçici dosyaya koşturdum; S0–S9 bloğunda 12/12 yakalandı, yasaklı alarm yok. |
| Model uyumsuzluğunda duyarlılık 0,88'e iniyor | `README.md:26` | **ÖLÇTÜM** | Aynı çıktı: uyumsuz blokta 14/16 = 0,875. S13'te recall 0,50, kaçan kodlar `ALM-THR-TERM-ALM` ve `ALM-THR-TERM-WARN`. |
| `docs/12` elle yazılmaz, betik üretir | `README.md:26` | **ÖLÇTÜM** | Yeniden ürettim; depodakiyle **tek farkı üretim zaman damgası**. Dokümanın güncelliği kanıtlanmış durumda. |
| Eşikler sözleşmeden türetiliyor, koda gömülü değil | PLAN kural 10 | **OKUDUM** | `detect.py:197,201,205,207` → `thresholds["rls_lambda"]`, `["excitation_min_var_i2"]`, `["term_rise_alarm_k"]`, `["tau_init_s"]`. `detect.py`'deki sayısal sabitler (P0=10.0, BASELINE_WINDOW=1000) **algoritma sabitleridir**, alarm eşiği değil, ve her biri satır içinde gerekçeli. |
| Üreteç ile dedektör aynı denklemi çözüyor | `docs/12 §1.1`, `docs/14 §9` | **OKUDUM** | `generator.py:10` `dT[k+1] = a*dT[k] + (1-a)*K*I^2` · `detect.py:5` `dT[k+1] = a*dT[k] + beta*I2[k], K = beta/(1-a)`. **Aynı denklem**, β=(1−a)K. Dedektörün RLS'i üretecin ileri modelini birebir ters çeviriyor. |
| Ölçüm sıkışmasında gerçek 78,90 K, ölçülen 48,48 K | `README.md:26` | **ÖLÇTÜM + OKUDUM** | S13 fixtüründen `worst_dt_c` tepe değeri **48,48 K** çıktı; 78,90 rakamı `docs/14:489,493` tablosunda eşleşen ikizin gerçek değeri. İkisi tutarlı. |
| S1'de 209 saat öne alma, tetikleyen kod prognoz | `README.md:26` | **ÖLÇTÜM** | Yeniden ürettiğim `docs/12` §2: ilk L1 13 Tem 22:15, tetikleyen `ALM-TTL-14D`, 70 K ihlali 22 Tem 15:15, öne alma 209,0 h. Tetikleyen kod ayrı sütunda basılıyor. |
| K/K₀ eşiğine dayanan öne alma ~172 saat | `README.md:26` | **ÖLÇTÜM** | S1 fixtüründen kendim: `ALM-K-WARN` 226,5. saat, `ALM-THR-TERM-ALM` 399,0. saat → **172,5 saat**. README §2 doğru. |
| Prognoz geri testi kötü ve yayımlanıyor | `README.md:26` | **ÖLÇTÜM** | Yeniden ürettiğim `docs/12` §4: S1 koni içinde %5,2, CRA −5,12, PH yok. §4.3'te n=1 olduğu, ihlalden sonra 587 tahmin üretildiği, S8/S13'te prognoz yanlış-alarmının §3 sayacına **görünmediği** yazıyor. |
| EN 50160 güç kalitesi değerlendiricisi var | `README.md:26` | **ÖLÇTÜM + OKUDUM** | `power_quality.py:19-29` (230 V, ±%10 → 207/253 V, −%15 → 195,5 V, %2 dengesizlik), `api/panels.py:46-66` ile uca bağlı. Canlı çağırdım, gerçek değerlendirme döndü. **Not:** `docs/18` satır 5 bunu "Yok" diyor — o satır 16 Eylül tarihli ve **bayat**; açık kapanmış. Projenin lehine. |
| Taban çizgisiyle karşılaştırma kodda | `docs/12 §2` | **OKUDUM** | `validate.py` sabit `thresholds.term_rise_alarm_k` = 70 K'yı ayrı bir karşılaştırma sütunu olarak işliyor; `threshold_sweep.py` ayrıca 11 eşik değerinde tarama yapıyor. |

**Test gücü değerlendirmesi.** `libs/panoalgo/tests/` altında 386 test tanımı / 607
assert satırı, **0 skip**. `test_scenarios.py`, `test_detect.py`, `test_prognostics.py`
gerçek fixtür üzerinde çalışıyor. Totolojik kalıp aramadım demiyorum — aradım,
`detect` tarafında bulamadım.

**Puanın gerekçesi.** Çapamdaki 9'un altı maddesinin **altısı da** literal olarak
karşılanıyor: yöntem gerekçeli ✓, taban çizgisiyle karşılaştırılmış ✓, metriklerle
ölçülmüş ✓, betik tekrar koşulabiliyor ve aynı sayıyı veriyor ✓, yanıldığı durumlar
yazılı ✓, eşikler sözleşmeden ✓. Buna rağmen 8 verdim ve sebebini açıkça yazıyorum:

1. Manşet 1,00, yöntemin saha başarısını değil **kendi ileri modelini ters
   çevirebildiğini** ölçüyor. Proje bunu itiraf ediyor, ama itiraf sayıyı
   düzeltmiyor.
2. Uyumsuz bloktaki 0,88 **tek bir yörüngeden** (n=1) geliyor; güven aralığı yok.
3. README §9 bu kriterin komşusunda yanlış bir sayı taşıyor (§7'de).

Bu üçü birlikte bir puanlık kesintiyi hak ediyor, daha fazlasını değil — çünkü
**sınırı ölçmek için dört senaryo yazıp dedektörü değiştirmeden sonucu yayımlamak**,
bu yarışmada gördüğüm en olgun metodolojik hamledir.

---

### Kriter 3 — Çözümün saha koşullarında uygulanabilirliği → **7/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| Çevrimdışı halka tampon var | `sim/panobeyni_sim.py:40` | **OKUDUM** | `panobeyni_sim.py:172-251` halka tampon, `--ring` parametresi, `payload["health"]["buffered"]` ile bildiriliyor (satır 363). |
| Tampon testli | — | **ÖLÇTÜM + OKUDUM** | `sim/tests/test_panobeyni_sim.py:221,234,249` — "en eskiyi düşürür ve sayar", "gönderim başarısızken her şeyi tutar", "ilk hatada durur, gerisini tutar". Üçü de benim koşumumda geçti (41/41). Bu **zayıf test değil**: üç ayrı arıza kipini ayrı ayrı sınıyor. |
| Sağlıklı panoda operatör yükü 71,4 yanlış alarm/100 pano/gün | `README.md:28` | **ÖLÇTÜM** | `threshold_sweep.py --seasons` geçiş mevsiminde 71,4; sözleşme hedefi <150. Yeniden ürettiğim `docs/12` §3 aynı sayıyı veriyor. |
| Veri bütçesi ölçüldü (F-36) | `README.md:30` | **BEYAN** | `loadtest/veri_butcesi.py` ve iki sonuç JSON'u (`veri-butcesi-2p…`, `veri-butcesi-5p…`) depoda var, ama koşmadım. |
| Ark tespiti için ayrı kart yok, TVOC-2 okunuyor | `README.md:28` | **OKUDUM** | `docs/13 §204`; `hardware/` altında yalnızca `pano-beyni`, `sensor-dugumu`, `pd-karti`, `mekanik`, `yerlesim` var — ark kartı yok. İddia ile dizin yapısı uyuşuyor. |
| DIN ray tipi mekanik kutu parametrik üretiliyor | `README.md:28` | **BEYAN** | `hardware/mekanik/din-kutu.stl` ve `.scad` var; 324 üçgen iddiasını saymadım. |
| Hiçbir kart üretilmedi, fiyatlar veri sayfasına karşı doğrulanmadı | `README.md:32` (`docs/19 §3`) | **OKUDUM** | Proje bunu **kendisi** yazıyor. Yarışma kuralları donanım almayı beklemiyor; bu bir eksi değil, **dürüstlük işareti**. |
| Kurulum işçiliği, SIM aboneliği, tip test hiçbir toplamda yok | `README.md:32` | **ÖLÇTÜM** | `tazminat_maruziyeti.py` çıktısı bu dört kalemi ayrı satırda "veri yok" olarak basıyor ve "bu dört kalemin BOM satırı yok" diyor. Sessizce dışarıda bırakmıyor. |
| Sahada doğrulandığı iması | tüm depo | **BULAMADIM** | Aşağıda §7'de ayrıntılı. Bu kategoride **yanıltıcı ifade bulamadım**. |

**Puanının gerekçesi.** Çapamda 6/10 "kod/test karşılığı yok, anlatı düzeyinde"
diyordu — GridUp bunun üstünde: halka tamponu kodda **ve** üç testte. Çapamda 9/10
"montaj/kalibrasyon prosedürü yazılı, sahada kim ne yapacak belli" diyordu; `docs/08`
prosedür dokümanı var ama hiç fiziksel doğrulama yok, kartlar üretilmedi, kurulum
işçiliği fiyatlanmadı. 7, bu ikisinin arası. Kuralın 3. maddesi gereği donanım
yokluğunu **eksi yazmadım**; eksi yazdığım şey saha uygulanabilirliğinin kodda
kanıtlanmış kısmının tek bir mekanizmayla (tampon) sınırlı olması.

---

### Kriter 4 — Uçtan uca sistem **yaklaşımı** → **8/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| Tek komutla 9 servis kalkar | `README.md:28` | **ÖLÇTÜM + OKUDUM** | `compose.yaml` 5 servis + `include:` ile `compose.sim.yaml` (4) + `compose.frontend.yaml` (1) = 10; `compose.mtls.yaml`'ın 1 servisi profil kapılı. → varsayılanda **9**. `docker ps` çıktım tam 9 konteyner gösterdi. İddia birebir doğru. |
| `panosim → MQTT → Ingest → TimescaleDB → REST → WebSocket → UI` canlı | `README.md:28` | **ÖLÇTÜM** | `GET /health`: `"ingest":{"received":2169,"rejected":0,"written":2169,"dropped":0,"write_errors":0}`. Ayrıca UI ekran görüntümde ADM-00001 için "son veri 4 sn önce" ve gerçek faz akımları çizili. |
| Karantina 0 | `README.md:28` | **ÖLÇTÜM** | `/health` `rejected: 0`. |
| Şema dışı mesaj düşürülmez, karantinaya yazılır | `ingest.py:9` | **OKUDUM** | `backend/app/ingest.py:5,9` — "Sema disi mesaj DUSURULMEZ, nedeniyle karantinaya yazilir". Yol gerçek; `test_ingest.py` ve `test_db_integration.py` bunu sınıyor. |
| Alarm yaşam döngüsü hash zincirine yazılır (F-20) | `README.md:28` | **ÖLÇTÜM** | `verify_journal.py` → "ZİNCİR SAĞLAM — 161 halka". |
| Zincir gerçekten zincir (sadece hash değil) | `journal_chain.py` | **ÖLÇTÜM** | Formülü **kendi kodumla** yeniden yazıp 164 satırı yeniden hesapladım: **164/164** tuttu, her satırın `prev_hash`'i bir öncekinin `hash`'ine eşit. `by_user`'ı değiştirdiğimde özet değişti. Bu, projenin kendi koduna değil **benim bağımsız uygulamama** dayanan bir doğrulama. |
| Zincirin yapamadıkları yazılı | `journal_chain.py:20-30` | **OKUDUM** | Üç sınır açıkça sayılmış: kuyruk kesmeyi göremez, HMAC değil (yazma yetkisi olan zinciri yeniden kurabilir), göç öncesi satırlar NULL. **Bu bir dürüstlük işaretidir.** |
| Sanal GSM modem gerçek donanım değil | `README.md:28` | **OKUDUM** | README'nin kendisi "gerçek donanım değil, simülatör" diyor; `docker ps` → `gridup-gsm-modem`. |
| Uçtan uca entegrasyon testleri gerçek DB'ye karşı | `test_db_integration.py:1-8` | **DOĞRULANAMADI** | Testler güçlü yazılmış (kendi `TST-xxxxx` panolarını yazıp siliyor), ama `TEST_DB_DSN` olmadan **37'si atlanıyor** ve ben izole DB açamadım (§0.4). |

**Puanın gerekçesi.** Çapamda 9 için "uçtan uca en az bir entegrasyon testi gerçekten
geçiyor (ve ben koşturunca da geçiyor)" demiştim. Bu koşul **tam olarak** sağlanamadı:
projenin en güçlü uçtan uca testleri varsayılan koşumda sessizce atlanıyor.
Buna karşılık zinciri canlı yığında uçtan uca ben sürdüm ve her halkayı gördüm.
8 bunun karşılığı.

**Bir gözlem (§8'de de var):** Çalışan `gridup-frontend` konteyneri, çalışma
ağacındaki kaynaktan **daha eski** görünüyor — canlı DOM'da `div.i3-stage` var,
kaynakta ise `Ikiz3D.tsx:1174` `div.twin-workbench` üretiyor. Sebebini kesin
saptayamadım; "tek komutla kalkar" iddiasını çürütmez ama demo ile depo arasında
bir sürüm farkı olduğunu gösterir.

---

### Kriter 5 — Mevcut **operasyon sistemleriyle** entegrasyon kabiliyeti → **8/10**

> **Kriteri projenin ağzından okumadım.** Resmî ifade "mevcut operasyon sistemleriyle
> entegrasyon kabiliyeti"dir; SCADA bunun yalnızca bir alt kümesidir. OMS, CBS,
> çağrı merkezi, varlık yönetimi ve iş emri sistemi de bu kriterin kapsamındadır.

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| Modbus FC03 gerçek protokol uygulaması | `README.md:30` | **ÖLÇTÜM** | **Üçüncü parti** `pymodbus` istemcisiyle :502'ye bağlandım, `read_holding_registers(100, 25, slave=1)` çalıştı. Oyuncak değil. |
| IEC 60870-5-104 gerçek protokol uygulaması | `README.md:30` | **ÖLÇTÜM** | Projenin kodunu **hiç kullanmadan**, standarttan ham soket istemcisi yazdım. Aldığım dizi: `STARTDT act → con (0x0b)`, `C_IC_NA_1 (100) COT=6 → COT=7 (act-con) → COT=10 (act-term)`, arada `M_ME_NC_1 (13) COT=20` **139 nesne**, `M_SP_NA_1 (1) COT=20` **29 nesne**, `M_ME_TF_1 (36) COT=3` kendiliğinden 17 nesne. Bu, standarda uygun bir kontrollü istasyondur. |
| "139 adres" | `README.md:30` | **ÖLÇTÜM** | GI'de tam **139** ölçüm nesnesi saydım. |
| Üç taşımada fark 0 | `README.md:30` | **ÖLÇTÜM** | Sıkı ölçüm (GI 0,02 sn'de bitti, ardından Modbus + REST): **IEC104 vs REST 0/25**, **Modbus vs REST 0/25**. |
| — *(kendi ölçüm hatam)* | — | — | İlk denememde 24/25 fark gördüm; sebebi GI'yi 10 sn boyunca beklemem ve bu sürede canlı verinin kaymasıydı. **Ölçümü sıkılaştırınca fark sıfırlandı.** Bunu rapora yazıyorum çünkü aksi hâlde uydurulmuş bir bulgu olurdu. |
| RBAC: belirteçsiz 401, yetersiz rol 403, doğru rol 200 | `README.md:60-66` | **ÖLÇTÜM** | Canlı `POST /api/v1/alarms/76/ack`: belirteçsiz **401**, izleyici **403** (`"bu islem 'operator' rolu gerektiriyor"`), uydurma belirteç **401** (`"gecersiz belirtec"`), operatör **200** `{"ok":true}`. Dördünü de gördüm. |
| Yazma uçları sabit zamanlı karşılaştırma kullanıyor | `auth.py:21` | **OKUDUM** | `hmac.compare_digest`. |
| Kimlik doğrulama boş tabloda kapalı (fail-open) | `auth.py:29-32` | **OKUDUM** | Kasıtlı, `/health`'te görünür (`auth.enabled`), başlangıçta `log.warning`, denetim izine `"anonim (kimlik dogrulama kapali)"` yazılıyor — gerçek bir kullanıcı adına **benzememesi kasıtlı**. Sessiz varsayılan değil. Yine de üretimde risktir ve `auth.py:24-33` bunu sayıyor: SSO yok, parola yok, oturum süresi yok, iptal listesi yok, düz HTTP. |
| CBS/GIS varlık künyesi (F-21) | `README.md:30` | **ÖLÇTÜM** | `GET /api/v1/fleet/assets` → `{"kapsama":{"panolar":6,"kunyeli":3,"fiderli":3,"aboneli":3}}` ve gerçek künye (`cbs_kodu: TR-ADM-DP-000001`, `fider_id: F-EFELER-03`). **Kapsamayı kendisi raporluyor**: 6 panodan 3'ünün künyesi var, eksik olanı var göstermiyor. |
| OMS + EPDK Madde 8 taslağı (F-22, F-23) | `README.md:30` | **OKUDUM** | `backend/app/epdk.py` (182 satır): her alan `durum` taşıyor (`ölçülen` / `öneri` / `elle_doldurulacak`), **alan yanıttan hiçbir zaman düşürülmüyor**, tazminat alanı **yok**, başlıkta "TASLAKTIR" uyarısı. `outage.py` (147 satır) fider bazlı bağıntı kuruyor. Canlı `GET /api/v1/outages` → `[]` (henüz eşzamanlı kesinti olmamış). |
| Sözleşme tutarlılığı denetleniyor | `scripts/check_contracts.py` | **ÖLÇTÜM** | "5 sozlesme dosyasi, 430 register, 25 nokta, cakisma yok, 23 alarm kodu, 17 uc — TUTARLI". |
| **Çağrı merkezi / iş emri / CMMS entegrasyonu** | — | **YOK** | 17 API ucunun hiçbiri bunu karşılamıyor. `grep` ile "çağrı merkezi / iş emri / work order / CRM" yalnızca `docs/04`, `docs/06`, `config.py`, `labels.ts` içinde **kavram olarak** geçiyor. Bu kriterin açık kalan yanıdır. |
| **CIM / IEC 61968 eşlemesi** | — | **YOK** | Aramada bulamadım. Kurumsal OMS/CBS entegrasyonunun fiilî standardı budur. |

**Bulgu — sözleşme kaçağı.** `GET /api/v1/panels/{pano_id}/power-quality` kodda var
(`api/panels.py:46`) ve canlı çalışıyor, ama `contracts/openapi.yaml`'da **yok**;
`check_contracts.py` "17 uç" deyip geçiyor. Yani sözleşme denetimi **tek yönlü**:
sözleşmede olup kodda olmayanı yakalar, kodda olup sözleşmede olmayanı yakalamaz.
Projenin kendi kuralı (PLAN.md kural 10, "sözleşme tek kaynaktır") burada delinmiş.
Ağırlık: hafif, ama denetim aracının kör noktası olduğu için kaydediyorum.

**Puanın gerekçesi.** Çapamda 9 için "SCADA dışında **en az bir** operasyon sistemi
sınıfı daha somut biçimde ele alınmış" demiştim — GridUp **iki** tane daha ele almış
(CBS ve OMS/EPDK), ve iki sanayi protokolünü bağımsız istemcilerle doğrulayabildim.
Ama çağrı merkezi, iş emri ve CIM eşlemesi yok; kimlik doğrulama paylaşılan sır
düzeyinde. 9 vermedim, 8 verdim.

---

### Kriter 6 — Ölçeklenebilirlik → **7/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| 1.000 panoda görünme p95 657 ms, kayıp 0 | `README.md:30`, `docs/09:13` | **BEYAN** | Koşamadım (§0.4). **Ve depodaki tek ölçüm eseri bunu vermiyor:** `loadtest/results/20260919T135916-1000p.json` → `visible_latency_ms.p95 = 710.5`, `receive_latency_ms.p95 = 12.8`, süre 180 s. `docs/09` satır 69'daki satır ise 300 s / 657 / 6,3. **Farklı koşumlar**; ikisi çelişmiyor ama dokümandaki sayının deposunda karşılığı yok. |
| Kayıp 0 | `docs/09:13` | **ÖLÇTÜM (dolaylı)** | Depodaki JSON: `publish.sent=18000`, `ingest.written=18072`, `rejected=0`, `dropped=0`, `write_errors=0`. Kayıp gerçekten 0. |
| `loadtest/results/` sürüm kontrolünde | — | **YANILTICI DEĞİL ama önemli** | `git ls-files loadtest/results/` → yalnızca `.gitkeep`. Yani `docs/09`'daki **on iki satırlık ölçüm tablosunun hiçbiri** depoda bir eserle desteklenmiyor; elimdeki tek JSON bile izlenmiyor. |
| Yük üreteci sistemle aynı makinede | `README.md:30`, `docs/09 §3` | **OKUDUM** | Proje bunu **kendisi** yazıyor ve "sonuçlar temkinli" diyor. Dürüstlük işareti. |
| Ölçüm aracı doğru şeyi sayıyor | `loadtest/fleet.py` | **OKUDUM** | `fleet.py:455-476` `probe_latency`: yayın anı → API'de yeni `seq`in ilk görüldüğü an. Gerçekten uçtan uca görünme gecikmesi; yerel döngü süresi değil. `fleet.py:325-333` p50/p95/max'ı "en yakın sıra" yöntemiyle hesaplıyor — standart. |
| Tam kenar boru hattı (RLS) yük testinde kullanılmıyor | `fleet.py:26-29` | **OKUDUM** | Açıkça yazılmış: 7 günlük taban öğrenmesi gerektirdiği için 300 s'lik koşuda anlamsız olurdu ve 1.000 panoda darboğaza dönerdi. Yani **ölçülen şey platformdur, tespit değildir** ve bu söyleniyor. |
| 10.000 panoda doyma, p95 19 s | `docs/09:17` | **BEYAN** | Koşamadım. Ama projenin **kendi doyma noktasını yayımlaması** lehine bir işarettir. |
| TimescaleDB sıkıştırma 46–48× | `README.md:30` | **BEYAN** | `deploy/initdb/005_compression.sql` var, oranı ölçmedim. |
| F-36 uyarlanabilir yayın %41 bastırma | `README.md:30` | **BEYAN** | `sim/tests/test_uyarlanabilir_raporlama.py` benim koşumumda geçti (41/41 içinde), ama %41 sayısını üreten ölçümü koşmadım. |
| Toplu filo ucu ve sayfalama | `README.md:30` | **ÖLÇTÜM** | `GET /api/v1/fleet/health` canlı çalıştı, 6 pano döndü. Liste sanallaştırması yok — proje bunu yazıyor. |

**Puanın gerekçesi.** Çapamda 6/10 "mimari uygun ama hiç yük ölçülmemiş", 9/10
"ölçek sayısal olarak sınanmış, sonucu kayıtlı ve **tekrar üretilebilir**". GridUp
ölçmüş (buna inanıyorum: tezgâh gerçek, yöntemi doğru, doyma noktasını yayımlamış),
ama **tekrar üretilebilirlik sağlanmamış**: sonuç dosyaları sürüm kontrolü dışında
ve elimdeki tek dosya dokümandaki sayıyı vermiyor. Darboğaz tespit edilmiş
(mesaj başına 615 µs'in 501 µs'i şema doğrulaması — `docs/18:72`), bu 9'a ait bir
davranış. Net: **7**. Bu, bu raporda **BEYAN borcu yüzünden düşürülen tek puandır**
(§4.2).

---

### Kriter 7 — Kullanıcı/operasyon deneyimi → **7/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| 7 ekran çalışıyor, 2'si kapsam dışı | `README.md:31` | **ÖLÇTÜM** | 7 rotanın hepsini açtım, ekran görüntülerini aldım ve **baktım**. Hepsi gerçek veri çiziyor: Operasyon özeti (`main` metni 1536 krk), Alarm merkezi (1059), Trend (1624), Cihaz sağlığı (955), Bölge haritası (2451), Olay analizi (9395). Boş iskelet **yok**. |
| 10 rotada 0 konsol hatası / uyarısı | `README.md:31` | **ÖLÇTÜM** | Canlı kip e2e: "OK … 0 hata, 0 uyari" ×10. Kendi bağımsız Playwright betiğimde de altı rotada `konsol hata=0`. |
| Operasyon döngüsü kapalı | `README.md:31` | **ÖLÇTÜM** | Alarm konsolu ekran görüntümde birebir görünüyor: **Neden?** (Ark koruması trip sayısı = 1, *Dayanak: TVOC-2 PDU 149 trip sayacı değişimi*) → **Ne doğrulanmalı?** → **Ne yapmalı?** → **Ne kadar acil?** (Bildirildi: SMS) → *"vardiya.amiri onayladı, 13 sa önce"*. Süsleme değil, işleyen bir akış. |
| 96 ilçe coğrafi harita | `README.md:31` | **ÖLÇTÜM** | Ekran görüntüsünde "3 pano · **96 ilçe** · ADM ve GDZ hizmet bölgesi" ve gerçek ilçe adları (Bergama, Akhisar, Ödemiş, Nazilli, Söke, Milas…) çizili. |
| Kontrast dışı hiçbir WCAG 2.1 AA ihlali yok | `README.md:31` | **ÖLÇTÜM** | `smoke.spec.ts:198` `expect(kontrastDisi).toHaveLength(0)` — **her iki kipte de kilitli** ve canlı kipte benim koşumumda geçti. Güçlü assert. |
| Canlı kipte 23 kontrast ihlali | `README.md:31` | **ÖLÇTÜM** | Benim koşumum: 5+2+2+2+2+2+2+2+2+2 = **23**. Birebir. |
| **Örnek veri kipinde 5 kontrast ihlali, sayı testte kilitli** | `README.md:31` | **YANILTICI** | Kilit var (`BILINEN_KONTRAST = {"/":3,"/trend":1,"/bolge":1}` = 5) ama **bugünkü kod onu sağlamıyor**. Ölçülen: `{"/":11,"/alarmlar":8,"/bolge":13,"/boyle-bir-sayfa-yok":3,"/cihaz-sagligi":9,"/olay":4,"/olay/EVT-42":5,"/pano/ADM-00014":10,"/pano/ADM-00057":10,"/trend":10}` = **83**. Test **DÜŞÜYOR** ve iki ayrı koşumda tekrarlandı. |
| 154 vitest testi / 17 dosya | `README.md:31` | **KISMİ (lehte sapma)** | Ölçtüm: **162 test / 19 dosya**. README eksik söylüyor, fazla değil. |
| Gövde metni kontrastı 13,33:1, sayı testte yaşıyor | `README.md:31` | **OKUDUM** | `theme.test.ts` **totolojik değil**: `theme.css`'in metnini okuyor, token'ı regex'le çıkarıyor, WCAG bağıl parlaklık formülünü standarttan uyguluyor ve token değerlerini kilitliyor. Üstelik **kendi sınırını yazıyor**: "burada ölçülen şey TOKEN MATEMATİĞİDİR, ekranın kendisi değil" ve axe'in `/bolge`de 4,21:1 bulduğunu söylüyor. Bu, gördüğüm en dürüst test başlığı. |
| 3B ikiz | `README.md:31` | **KISMİ** | Canlıda "3D ikiz" düğmesine bastım, canvas **çizildi** (`canvas` 0→1, hata yok). Ama `smoke.spec.ts:19-23` bu sekmeyi **bilerek açmıyor** ve buna "ÖLÇÜM BOŞLUĞU" diyor — dürüst. Ayrı `twin.spec.ts` ise **düşüyor**. |
| Mobil (390 px) 3B ikiz | `twin.spec.ts:52` | **YANILTICI DEĞİL, KIRIK** | Viewport 390×844'e geçince `.twin-workbench` içinde "3/4 görünüş" düğmesi 45 s'de bulunamıyor. İki koşumda da aynı. |

**Puanın gerekçesi.** Çapamda 9/10 "arayüz koşturulup her ekranı görüntülenmiş,
konsol hatası yok, erişilebilirlik düşünülmüş" diyordu. İlk ikisi tam sağlanıyor,
üçüncüsü **yarım**: erişilebilirlik gerçekten düşünülmüş (axe entegre, kontrast dışı
ihlaller sıfıra kilitli, `theme.test.ts` ciddi) ama yayımlanan sayı bayat ve koruyucu
test kırmızı. Bir de mobil görünümde kırık bir test var. 8'den 7'ye indirdim (§4.1).

---

### Kriter 8 — Maliyet ve sağlanan fayda → **8/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| Pano Beyni adet 1: 70,73 USD · adet 1.000: 47,68 USD | `README.md:32` | **ÖLÇTÜM** | `hardware/pano-beyni/bom.csv`'yi kendim topladım (adet × birim fiyat): **70,73 / 47,68**. Birebir. |
| Sensör düğümü 23,25 / 13,95 · PD kartı 19,80 / 11,79 | `README.md:32` | **ÖLÇTÜM** | Kendi toplamım: **23,25 / 13,95** ve **19,80 / 11,79**. Birebir. |
| Pano toplam 103,48 (4 düğüm) / 145,33 (7) / 396,43 (25) | `README.md:32` | **ÖLÇTÜM** | `47,68 + N×13,95` → **103,48 / 145,33 / 396,43**. Dokuz rakamın dokuzu da tuttu. |
| Geri ödeme tek sayı değil aralık | `README.md:32` | **ÖLÇTÜM** | `--parametreler … --duyarlilik`: 4 düğüm **7,4 ay**, 7 düğüm **10,4 ay**, 25 düğüm **28,3 ay**. Birebir. |
| Üç varsayımın kaldıracı birebir eşit (1,33×) | `README.md:32` | **ÖLÇTÜM** | Çıktı: `ariza_olasiligi_yil 1.33x`, `ariza_basi_maliyet_usd 1.33x`, `tespit_orani 1.33x`, `dugum_sayisi 0.67x`. **Ve bu matematiksel olarak doğru**: model çarpımsal olduğu için üç çarpanın ±%50 kaldıracı zorunlu olarak aynıdır. Betik bunu kendisi açıklıyor. |
| Betik veriyi uydurmaz | `README.md:32` | **ÖLÇTÜM** | Parametresiz koştum: maruziyet "veri yok", kaçınılan toplam "veri yok", geri ödeme "veri yok", duyarlılık "oynatılacak girdi yok". **Tek bir varsayılan sayı üretmedi.** Bu, iddianın en sağlam kanıtı. |
| Kaçınılan kalemler sayılıyor ama fiyatlanmıyor | `README.md:32` | **ÖLÇTÜM** | Çıktı 10 kalemi listeliyor (4 AT, 3 gerilim girişi, 2 ark dedektörü, 1 merkez ünite), hepsi "veri yok". Yerine **fiyat gerektirmeyen** bir metrik veriyor: "başa baş eşiği 0,49 USD (adet 1) / 0,37 USD (adet 1.000)". Bu akıllıca bir kaçış: tedarikçi fiyatı olmadan da ölçülebilir bir sonuç üretiyor. |
| Fayda tarafı varsayım | `README.md:32` | **ÖLÇTÜM** | Çıktıda `[varsayim]` etiketi üç girdinin de yanında; ayrıca "tespit orani 0.7 [varsayim] (olculen: docs/12 … 1,00 … 0,50'ye kadar)" diye kendi ölçümüyle karşılaştırıyor. |
| OPEX 12,85 → 7,58 GB/pano/yıl | `README.md:32` | **BEYAN** | Ölçmedim. Çıktı OPEX'i "veri yok — hücresel tarife depoda yok" diyerek geri ödemeden **dışarıda tutuyor** ve sonucun "bir ALT SINIR" olduğunu yazıyor. |
| Eski bir iddianın yanlış olduğu itiraf ediliyor | `README.md:32` | **OKUDUM** | "İlk yazdığımız *'sıralama değişmez'* iddiası **yanlıştı ve düzeltildi**; hikâyesi `docs/10` §7.4'te duruyor." Dürüstlük işareti. |

**Puanın gerekçesi.** Çapamda 9/10 "kaynağı belirtilmiş varsayımlar + duyarlılık +
geri ödeme + tekrar koşulabilir betik" diyordu. Dördünden üçü tam: duyarlılık ✓,
geri ödeme aralığı ✓, betik ✓ (ve ben koşturdum). Eksik olan **varsayımların
kaynaklandırılması**: P(arıza), arıza başı maliyet ve tespit oranı etiketli ama
kaynaksız. Maliyet tarafı ölçüm, fayda tarafı varsayım — ve proje bunu gizlemiyor.
8.

**Muhalif not (kendime):** "145,33 USD, birilerinin CSV'ye yazdığı sayıların toplamı;
fiyatların hiçbiri doğrulanmadı." Doğru — ama projenin kendisi de bunu söylüyor
(`docs/19 §3`). Benim doğruladığım şey **aritmetik bütünlük ve uydurmama disiplini**;
fiyatların piyasa doğruluğu değil. Puanı bu ayrımla verdim.

---

### Kriter 9 — Yenilikçilik → **8/10**

> Resmî kriterin adı yalnızca "Yenilikçilik"tir. Proje bunu "Yenilikçilik & Fizik
> Tabanlı AI" diye genişletmiş; ben genişletilmiş hâline göre değil, resmî ifadeye
> göre değerlendirdim.

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| RLS ile dinamik K/K₀ öğrenimi kodda | `README.md:33` | **OKUDUM** | `detect.py:5-8` model ve regresör tanımı, `:197` unutma faktörü sözleşmeden, `:214` `theta=[a, beta*I2_SCALE]`, `:241-242` `K = beta/(1-a)` ve negatif kırpma. Ölçekleme (`I2_SCALE`) sayısal kararlılık için gerekçelendirilmiş (`:21`). Matematik doğru. |
| Kenar ile merkez **kanıtlanmış biçimde** aynı algoritmayı koşar | `README.md:33` | **ÖLÇTÜM** | Üç adımda kendim doğruladım: **(1)** `python -m panoalgo.vectors` ile vektörü yeniden ürettim → depodaki CSV ile **bayt bayt aynı** (241 satır). **(2)** C çekirdeğini `cmake` + `ninja` ile **sıfırdan derledim**. **(3)** `test_rls.exe` 240 adımda K, τ ve `excited`'ı karşılaştırdı ve geçti. Test vektörü **dışarıdan** geliyor, test içinde yeniden hesaplanmıyor — zayıf test kalıplarının hiçbirine girmiyor. |
| double'da en büyük göreli fark 1,36e-08 | `README.md:33` | **ÖLÇTÜM** | Benim ölçümüm: **K 1,362e-08**, τ 1,419e-08. Birebir. |
| float'ta 6,96e-06 | `README.md:33` | **KISMİ** | Benim ölçümüm: **K 6,774e-06**, τ 6,239e-06 — tolerans 1e-04'ün çok altında ama README'nin üçüncü anlamlı hanesi tutmuyor. Sebebi derleyici farkı (bende MinGW GCC **6.3.0**). Yani bu sayı **araç zincirine bağlıdır** ve sabit bir rakam gibi yayımlanması aşırı kesinliktir. İddia yanlış değil, fazla kesin. |
| `malloc` yok, sabit bellek | `README.md:33` | **OKUDUM** | `CMakeLists.txt:12` "Cekirdek yalnizca C11 ve standart kutuphaneye baglidir; dinamik bellek kullanmaz"; `rls.c:57` halka tampon "kaydirma yok". |
| Aynı kaynak hem host hem MCU'da derlenir | `CMakeLists.txt:13` | **KISMİ** | `PANO_USE_FLOAT` seçeneğiyle iki derleme hedefi gerçek ve ikisini de ben derledim; ama **gerçek bir MCU'da koşturulmadı** ve proje bunu iddia etmiyor. |
| Magnus formülü C ve Python'da aynı sabitlerle | — | **OKUDUM** | `firmware/core/dewpoint.h:8-9` `17.62` / `243.12` ≡ `physics.py:7-8`. Tek kaynak disiplini gerçek. |
| Rakip ürünlerden farkı somut yazılmış | `docs/18` | **OKUDUM** | 14 satırlık yetenek matrisi; her satırda "Bizde (ölçülmüş kanıt)", "Ticari platform tarafında **doğrulanan**", ve **"karar mı, boşluk mu"** sütunu. ABB Ability EDCS, Siemens SENTRON, Schneider PME, Easergy TH110/CL110 adlarıyla ve kaynaklarıyla. "Hiçbir rakip ürün için fiyat yazılmamıştır" ve "hiçbir rakibin kötü olduğu iddia edilmez" diyor. Bu, pazarlama değil konumlandırma. |
| Yeniliğin sınırları yazılı | `docs/14 §9`, `docs/18` | **OKUDUM** | `docs/14 §9` "Bu bölümün var olma sebebi bir **itiraftır**" diye başlıyor ve döngüselliği denklemleriyle yan yana koyuyor. `docs/18` satır 5, 6, 10, 12'de kendi boşluklarını sayıyor. |
| **`ALM-K-WARN` 232. saat, `ALM-THR-TERM-ALM` 520. saat → 288 saat erken** | `README.md:33` | **YANILTICI** | S1 fixtüründen kendim ölçtüm: `ALM-K-WARN` **226,5. saat**, `ALM-THR-TERM-ALM` **399,0. saat** → öne alma **172,5 saat**. README'nin kendi 2. satırı da "~172 saat" diyor. Aynı tablonun iki satırı çelişiyor ve §9'daki sayı ölçüleni **%67 abartıyor**. |

**Puanın gerekçesi.** Çapamda 9/10 "özgün fikir kodda uygulanmış ✓, mevcut çözümlerin
neden yapamadığı anlatılmış ✓, en az bir karşılaştırmalı kanıt ✓, sınırları yazılı ✓"
diyordu — dördü de karşılanıyor. 9 vermeyişimin **tek** sebebi manşet sayının yanlış
olması: kriterin en görünür iddiası, jürinin ilk okuyacağı satır, ölçümle uyuşmuyor.
Bir puan kesinti bunun karşılığıdır.

**Muhalif not (kendime):** "C ve Python'un uyuşması önemsiz — aynı kişi, aynı
algoritma." Saldırı **tutmadı**: vektörü ben yeniden ürettim, C'yi **onlarınkinden
farklı bir derleyiciyle** ben derledim, ve 240 adımda üç ayrı büyüklük (K, τ,
`excited` boolean) tuttu. Farklı bir araç zincirinin aynı sayıyı vermesi önemsiz
değildir. Saldırının **tuttuğu tek yer**, float rakamının araç zincirine bağlı
çıkmasıydı — o da yukarıda kayıtlı.

---

## 4. Kendi denetimimin sonucu

### 4.1 Denetimde değişen puanlar

| # | Önce | Sonra | Neden |
|---|:---:|:---:|---|
| 6 | 8 | **7** | Ölçeklenebilirliğin **tüm** kanıt tabanı BEYAN kaldı. Kapatmayı denedim, koşamadım (ortam). Ama sonra §5C taramasında şunu buldum: `loadtest/results/` sürüm kontrolü dışında ve depodaki tek ölçüm eseri (710,5 ms) dokümandaki sayıyı (657 ms) vermiyor. "Ölçüldüğüne inanıyorum ama tekrar üretilemiyor" 8 değil 7'dir. |
| 7 | 8 | **7** | Canlı koşum ve ekran görüntüleri beni 8'e ikna etmişti. Sonra mock kipini koştum: yayımlanan "5 kontrast ihlali" bugün **83** ve koruyucu test **kırmızı**. Yayımlanmış bir erişilebilirlik sayısının yanlış olması ve testinin düşmesi bir puanlık kesintidir. |
| 9 | 9 | **8** | Firmware zincirini uçtan uca doğruladıktan sonra 9 düşünüyordum. Sonra §9'un manşet sayısını fixtürden ölçtüm: 288 değil **172,5**. Kriterin en görünür iddiasının yanlış olması 9'u engeller. |
| 1,2,3,4,5,8 | — | **değişmedi** | Neyle doğruladığım her birinin defterinde yazılı. |

### 4.2 BEYAN muhasebesi

İzlediğim **20 manşet iddia**dan:

- **14'ü kapandı** → `ÖLÇTÜM` veya `OKUDUM`:
  docs/12 üretimi, eşik taraması, BOM toplamları, duyarlılık analizi, uydurmama
  disiplini, Modbus, IEC 104, üç taşıma tutarlılığı, RBAC, hash zinciri (bağımsız
  yeniden hesap), firmware uyumu (iki duyarlık + vektör yeniden üretimi), sözleşme
  denetimi, doküman üreteçleri, EN 50160, 96 ilçe, operatör döngüsü, 0 konsol hatası.
- **5'i açık kaldı** → `BEYAN`, ve **puana katkıları düşüldü**:
  | Kapanmayan | Hangi kriter | Ne yaptım |
  |---|---|---|
  | 657 ms / 46–48× sıkıştırma / 10.000 pano doyması | K6 | Puanı 8 → **7** indirdim |
  | F-36 %41 bastırma, 12,85 → 7,58 GB | K3, K6 | K6 kesintisine dahil; K3'te tek başına belirleyici değil |
  | mTLS + topic ACL (F-27) | K5 | Puana **katmadım** (varsayılan kapalı, koşulamadı) |
  | Telegram kanalı | K4 | Puana **katmadım** (proje belirtecin boş olduğunu yazıyor) |
  | `din-kutu.stl` 324 üçgen | K3 | Puana **katmadım** (önemsiz ayrıntı) |
- **1'i `DOĞRULANAMADI — ortam`**: 37 DB entegrasyon testi. **Puanı bu yüzden
  düşürmedim**; K4'te belirsizlik olarak raporladım.

### 4.3 Yüksek puanlara saldırı — tuttu mu?

Rolümü değiştirip "bu puan şişirilmiş" demeye çalıştım. Üç 8'e saldırdım:

**K5 (entegrasyon) — saldırı: "Bu yalnızca kendi kendine tutarlılık; aynı bellek
içi görüntü üç kere servis ediliyor."**
→ **Tutmadı.** `pymodbus` üçüncü parti bir istemcidir ve FC03 konuştu. IEC 104
istemcisini standarttan **ben yazdım**, projenin kodunu hiç kullanmadım, ve sunucu
doğru STARTDT/GI/act-term dizisini ve doğru ASDU tiplerini (1, 13, 36) üretti.
Bu protokol uyumluluğudur, öz-tutarlılık değil. Puan **artık daha sağlam**.
Saldırının tuttuğu yer: **genişlik**. Çağrı merkezi ve iş emri yok — zaten 9 değil
8 olmasının sebebi bu.

**K9 (yenilikçilik) — saldırı: "C/Python uyumu önemsiz."**
→ **Tutmadı** (gerekçe §3-K9'da). Kısmen tuttuğu yer float rakamının araç
zincirine bağlılığıydı; kayda geçti.

**K8 (maliyet) — saldırı: "Girdiyi bozsam ne olur?"**
→ **Denedim, tuttu — projenin lehine.** Betiği **parametresiz** koştum: tek bir
sayı uydurmadı, her kalemde "veri yok" dedi ve neyin eksik olduğunu adıyla söyledi.
Bu, "yalnızca demo verisinde çalışan yol" aramasının tam tersi bir sonuçtur.

### 4.4 Doküman-kod farkı taraması (§5C)

"Tamamlandı/ölçüldü" denen maddelerden **en kolayları değil**, sayı içerenleri
seçtim. İlk beşte **iki** uyuşmazlık çıkınca taramayı **on maddeye genişlettim**:

| # | Madde | Verdikt | Kanıt |
|---|---|---|---|
| 1 | F-20 hash zinciri | **UYUŞUYOR** | Bağımsız yeniden hesapta 164/164 |
| 2 | F-19 RBAC | **UYUŞUYOR** | Canlı 401/403/401/200 |
| 3 | F-21 CBS künyesi | **UYUŞUYOR** | Canlı uç + dürüst kapsama raporu |
| 4 | K7 7.3 "5 kontrast ihlali" | **UYUŞMUYOR** | Ölçülen **83**, test kırmızı |
| 5 | K9 "288 saat erken" | **UYUŞMUYOR** | Ölçülen **172,5 saat** |
| 6 | `docs/17:204` "S8'de 99 tahmin, 89'u alarma döndü" | **UYUŞMUYOR** | Üretilmiş `docs/12` §4.3: **183 tahmin, 86'sı** |
| 7 | `docs/13:201` + `docs/17:79` "209 saat **tespit** katmanındandır, tahmin değildir" | **UYUŞMUYOR** | Üretilmiş `docs/12` §2: tetikleyen kod `ALM-TTL-14D` = **prognoz**. `docs/05:307` bunu düzeltmiş, `docs/13` ve `docs/17` düzeltilmemiş. |
| 8 | README "154 vitest / 17 dosya" | **DAHA_AZI (lehte)** | Gerçek: **162 / 19** |
| 9 | `docs/09` 657 ms | **ESER YOK** | Depodaki tek JSON 710,5 ms; `results/` izlenmiyor |
| 10 | `check_contracts` "17 uç" | **DAHA_AZI** | Kodda 18. uç var (`/power-quality`), sözleşmede yok |

**Uyuşmazlık sayısı: 5 (+2 lehte/hafif sapma).** Hepsinin ortak kökü aynı:
**19 Eylül'de yapılan bir düzeltme depoya tam yayılmamış.** Düzeltme `docs/05`,
`docs/12` ve README §2'ye işlenmiş; `docs/13`, `docs/17` ve README §9'a
işlenmemiş.

### 4.5 Öz eleştiri dokümanlarının tarihle okunması

Kuralın 5. maddesi gereği, projenin kendi açık listelerini **bugünkü koddan**
kontrol ettim:

- `docs/18` satır 5: "EN 50160 **Yok**" (16 Eylül'de grep ile ölçülmüş).
  → **Bugün kapanmış.** `power_quality.py` var, testli, uca bağlı, canlı çalışıyor.
  Bu açığı **eksi yazmadım**; aksine kapanmış olması lehte.
- `docs/05:307-313`: "bu belgenin önceki hâli bunun tersini yazıyordu" —
  proje kendi manşet sayısının yorumunu **kendisi düzeltmiş** ve düzeltmenin
  tarihini yazmış. **Lehte.**
- `docs/10 §7.4`: "sıralama değişmez iddiası yanlıştı ve düzeltildi". **Lehte.**
- `DEVILS-ADVOCATE-ANALIZI.md`, `KALAN-EKSIKLER.md`: okudum; içlerindeki
  maddelerin bir kısmı kapanmış. Kapanmışları eksi yazmadım.

### 4.6 Çapa denetimi — puanı mı düzelttim, çapayı mı?

**Hiçbir çapayı oynatmadım.** Ek A'daki metinler, depoyu açmadan önce yazdığım
hâlleriyle duruyor. Denetimde **üç puanı** düzelttim (§4.1), üç çapayı değil.

En yakın geldiğim yer K2 idi: çapamın 9/10 maddesinin **altı alt koşulunun altısı
da literal olarak karşılanıyor**. Çapayı "ama ölçümün temeli döngüsel olmamalı"
diye genişletmek aklımdan geçti — **bunu yapmadım**, çünkü ölçüyü sonuca uydurmak
olurdu. Bunun yerine çapayı olduğu gibi bıraktım ve 8 verip **sebebini açıkça
yazdım** (§3-K2). Jüri, çapaya bakıp "bu aslında 9" diyebilir; itirazı görebilsin
diye ikisini de yazdım.

### 4.7 En az emek verdiğim kriter (§5E)

**Kriter 9'un "mevcut ürünlerden farkı" yanıydı.** Fark ettim, kapattım:
`docs/18`'i okudum (151 satır, 14 satırlık yetenek matrisi) ve raporun K9
defterine işledim. Kapatmasaydım K9'u 7 verecektim; matris gerçek olduğu için 8'de
kaldı.

**İkinci en az emek: Kriter 1.** `Hackathon Verileri/İstenen Veriler.xlsx`'i açıp
kurumun istediği üç kalemi çıkardım ve üçünün de kodda karşılığını buldum — ama
**8 şartname PDF'ini okumadım**. Bu benim eksiğimdir ve K1 puanının belirsizlik payı
buradadır (§8).

---

## 5. En güçlü üç şey

### 1. Sözleşmeden koda, koddan dokümana giden zincir gerçekten kapalı

Bu, projenin tek en ayırt edici özelliği. `contracts/*.yaml` tek kaynak; kod ondan
okuyor; dokümanlar ondan **üretiliyor**; ve üretimin güncelliği `--check` ile
sınanabiliyor. Ben dördünü de koştum: `gen_modbus_doc`, `gen_iec104_doc`,
`gen_alarm_doc`, `gen_grafana_dashboards` → dördü de **"guncel"**. Üstüne
`validate.py`'yi koşturup `docs/12`'yi yeniden ürettim: depodakiyle **tek farkı
zaman damgası**. `check_contracts.py` 430 register ve 23 alarm kodunu çakışmasız
buluyor. Hackathon projelerinde dokümanlar kodun üç gün gerisinden gelir; burada
üç büyük doküman kodun **çıktısı**.

### 2. Kendi sınırını ölçmek için ayrı senaryo yazıp dedektörü değiştirmemiş olması

`docs/14 §9` şu cümleyle başlıyor: *"Bu bölümün var olma sebebi bir itiraftır."*
Sonra üreteç ile dedektörün denklemini yan yana koyuyor — ben ikisini kodda
doğruladım (`generator.py:10` ≡ `detect.py:5`, β=(1−a)K). Ardından dört yeni fizik
(kuplaj, yüke bağlı τ, ikinci kutup, ölçüm doğrusalsızlığı) ekleyip **dedektöre
hiçbir şey eklemeden** yeniden ölçmüşler ve duyarlılığın 1,00'dan 0,88'e düştüğünü
yayımlamışlar. Ben bu sayıyı yeniden ürettim.

Aynı disiplin prognozda da var: geri testi yapmışlar, **kötü çıkmış** (koni içinde
%5,2, CRA −5,12, PH yok), ve saklamamışlar. §4.3'te n=1 olduğunu, ihlalden sonra
587 tahmin daha üretildiğini, ve **S8/S13'teki prognoz yanlış-alarmlarını §3'teki
sayacın göremediğini** kendileri yazmışlar.

Bir yarışma projesinin kendi manşetini zayıflatan ölçümü yayımlaması nadirdir.

### 3. İki sanayi protokolü, bağımsız istemcilerle doğrulandı

Bunu özellikle vurguluyorum çünkü **kendi bağımsız kanıtım var**. IEC 104
istemcisini standarttan ben yazdım; projenin hiçbir kodunu kullanmadım. Sunucu
`STARTDT con`, ardından `C_IC_NA_1` için `COT=7` (act-con) ve `COT=10` (act-term)
verdi; arada 139 `M_ME_NC_1` ve 29 `M_SP_NA_1` nesnesi taşıdı, üstüne 17 zaman
etiketli kendiliğinden nesne gönderdi. Modbus tarafında `pymodbus` FC03 konuştu.
Üç taşıma (REST / Modbus / IEC 104) 25 noktanın **25'inde de** aynı değeri verdi.

Buna **F-20 hash zincirini** de ekliyorum: dokümante edilen SHA-256 formülünü kendi
kodumla yazıp canlı veritabanındaki 164 satırı yeniden hesapladım — **164/164
tuttu**. Bu, "kendi kendini onaylama" olmayan bir doğrulamadır.

---

## 6. En zayıf üç şey

### 1. Ölçeklenebilirlik kanıtı depoda yeniden üretilemiyor

`docs/09` on iki satırlık bir ölçüm tablosu yayımlıyor (657 ms, 46–48×, 10.000
panoda doyma). Bu sayıların **hiçbirinin** deposunda bir eseri yok:
`git ls-files loadtest/results/` yalnızca `.gitkeep` döndürüyor. Diskte duran tek
JSON dosyası (`20260919T135916-1000p.json`) sürüm kontrolünde değil **ve
dokümandaki sayıyı vermiyor**: `visible_latency_ms.p95 = 710.5`, dokümanda 657.
(Farklı süreli koşumlar olduğu için çelişki değil; ama dokümandaki satırı
destekleyen bir dosya yok.)

Projenin kendi standardı bu değil: `docs/12`'yi bir betik üretiyor ve ben yeniden
üretebiliyorum. `docs/09` aynı muameleyi görmemiş. **Sonuç:** kriter 6'nın tamamı
bana `BEYAN` olarak kaldı.

### 2. 19 Eylül düzeltmesi depoya yarım yayılmış — üç yerde eski iddia duruyor

Proje, manşet "209 saatlik öne alma"nın aslında **prognozdan** geldiğini fark edip
düzeltmiş. Düzeltme `docs/05`, `docs/12` ve README §2'ye işlenmiş. Ama:

- `docs/13:201` hâlâ *"209 saat **tespit** katmanındandır, tahmin değildir"* diyor.
- `docs/17:79` ve `:204` aynı şeyi söylüyor, üstelik `:204` S8 için **99/89**
  diyor — üretilmiş `docs/12` §4.3'te bu **183/86**.
- README §9 ise üçüncü bir sayı taşıyor: **288 saat**. Ben fixtürden ölçtüm:
  `ALM-K-WARN` 226,5. saat, `ALM-THR-TERM-ALM` 399,0. saat → **172,5 saat**.
  README'nin **kendi 2. satırı** zaten "~172 saat" diyor.

Yani jürinin okuyacağı ilk tabloda, aynı büyüklük için iki farklı sayı var ve
büyük olanı %67 abartıyor. Bu, kötü niyetten çok **yayılmayan bir düzeltmedir** —
ama bulan kişi için ayrımı yapmak zordur ve projenin geri kalanındaki dürüstlük
sermayesini yakar.

### 3. Yayımlanmış erişilebilirlik sayısı bayat ve koruyucu testi kırmızı

README "örnek veri kipinde **5** kontrast ihlali ölçülmüştür … ve sayı testte
kilitlidir" diyor. Kilit gerçekten var (`smoke.spec.ts:170-173`) ama **bugünkü kod
onu sağlamıyor**: ölçtüğüm toplam **83** ve test **düşüyor** (iki ayrı koşumda
tekrarlandı). Muhtemel sebep `FRONTEND-ACIK-TEMA-REVIZYONU.md` ile gelen açık tema
değişikliğinin yeniden ölçülmemesi.

Yanına iki şey daha ekliyorum:
- `twin.spec.ts` mobil genişlikte (390 px) **düşüyor** — 45 s boyunca "3/4 görünüş"
  düğmesini bulamıyor.
- Çalışan `gridup-frontend` konteyneri kaynaktan **eski** görünüyor: canlı DOM'da
  `div.i3-stage`, kaynakta `Ikiz3D.tsx:1174` `div.twin-workbench`. Demo ile depo
  aynı sürüm değil.

---

## 7. YANILTICI bulgular ve zayıf testler

### 7.1 YANILTICI (iddia ile kod/ölçüm uyuşmuyor)

| # | İddia | Nerede | Ölçülen gerçek | Ağırlık |
|---|---|---|---|---|
| Y1 | "`ALM-K-WARN` 232. saatte, `ALM-THR-TERM-ALM` 520. saatte → **288 saat erken**" | `README.md:33` | **226,5 / 399,0 → 172,5 saat**. README'nin kendi 26. satırı "~172 saat" diyor. | **AĞIR** — manşet sayı, %67 abartı, iç çelişki |
| Y2 | "209 saat **tespit** katmanındandır, tahmin değildir" | `docs/13:201`, `docs/17:79`, `docs/17:204` | Üretilmiş `docs/12` §2: tetikleyen kod `ALM-TTL-14D` = **prognoz**. `docs/05:307` bunu zaten düzeltmiş. | **AĞIR** — düzeltilmiş bir hatanın üç yerde yaşaması |
| Y3 | "örnek veri kipinde **5** kontrast ihlali … sayı testte kilitlidir" | `README.md:31` | **83**; test **DÜŞÜYOR** (tekrarlanabilir) | **AĞIR** — yayımlanmış sayı yanlış + koruyucu test kırmızı |
| Y4 | "S8'de **99** tahmin çıktı ve **89'u** `ALM-TTL-14D` alarmına döndü" | `docs/17:204` | Üretilmiş `docs/12` §4.3: **183** tahmin, **86'sı** | **ORTA** — elle yazılmış doküman üretilmiş dokümanın gerisinde |
| Y5 | `check_contracts.py` "OpenAPI: 17 uç" | `scripts/check_contracts.py` | Kodda **18.** uç var (`GET /panels/{id}/power-quality`, `api/panels.py:46`), sözleşmede yok. Denetim tek yönlü. | **HAFİF** — kör nokta, PLAN kural 10 ihlali |

### 7.2 Donanım / saha iddiası taraması — **yanıltıcı ifade BULAMADIM**

Bu kategoriyi özellikle taradım, çünkü kuralların en ağır cezalandırdığı yer burası.
`sahada`, `gerçek pano`, `üretildi`, `imal`, `kalibre`, `donanımda`, `MCU` kalıplarını
aradım ve bağlamlarıyla okudum. **Yapılmamış bir şeyi yapılmış gibi anlatan tek bir
cümle bulamadım.** Aksine, projenin kendi sınırını çizdiği yerler:

- `README.md:32` — *"hiçbiri veri sayfasına karşı doğrulanmadı ve üretilmedi"*
- `README.md:28` — sanal GSM modem için *"gerçek donanım değil, simülatör"*
- `README.md:28` — *"bot belirteci `.env`'de boştur, girilene kadar Telegram kanalı devre dışıdır"*
- `docs/18:70` — *"Sertifikalı donanım, tip testi, EMC: **Yok.** … **Karar — GK3.** 'Karşılıyoruz' değil, 'tasarım hedefi, tip testi yapılmadı'"*
- `docs/18:72` — *"bizimki **sanal** panodur, saha ölçeği değildir"*
- `docs/18:83` — sensör seçimi için *"tasarım düzeyindedir, fiziksel doğrulama yapılmadı"*
- `README.md:26` — *"Prognoz geri testini de aynı dosya yayımlar ve **sonuç iyi değildir**"*

Firmware yalnızca host derlemesinde koşuyor (`CMakeLists.txt`, `firmware/host/`) ve
proje gerçek MCU'da koştuğunu **iddia etmiyor**. Yarışma kuralları donanım almayı
ve saha kurulumunu beklemiyor; sentetik veriyle gösterim serbest. **Bu kategoride
projenin sicili temiz.**

### 7.3 Zayıf testler

| Bulgu | Kalıp | Ağırlık |
|---|---|---|
| `backend/tests/`de **37 test** varsayılan koşumda atlanıyor (`TEST_DB_DSN` tanımsız) | **SKIP** | **ORTA** — atlananlar aslında deponun **en güçlü** testleri (gerçek DB'ye yazıp `psql` ile kurcalayıp bağımsız betiği koşuyorlar). Test *kalitesi* sorunu değil, *koşulmama* sorunu. |
| `smoke.spec.ts` 3B ikiz sekmesini **hiç açmıyor** | **ÖLÇÜM BOŞLUĞU** | **HAFİF** — ama proje bunu `smoke.spec.ts:19-23`'te *"bu bir ÖLÇÜM BOŞLUĞUDUR, böyle yazıldı"* diye **kendisi** ilan ediyor. Gizlenmiş değil. |
| Canlı kipte kontrast sayısı **kilitlenmiyor** | **TESTSİZ_SAYI** | **HAFİF** — kodda gerekçesi var (veri artefaktı olurdu) ve her koşumda basılıyor; ama README "sayı testte kilitlidir" derken bu ayrımı yapmıyor. |
| `industrial.spec.ts` "3D evidence" testi **kararsız** | **FLAKY** | **HAFİF** — tam pakette bir kez düştü, tek başına ve sonraki iki tam koşumda geçti. Not: `playwright.config.ts` `retries: 0` **bilerek** ayarlanmış ("retry, kararsız bir hatayı 'geçti' diye gizler") — yani kararsızlık gizlenmiyor, görünür kılınıyor. |

**Aradığım ama bulamadığım kalıplar** (bu da bir sonuçtur ve projenin lehinedir):

- **TOTOLOJİK test bulamadım.** Özellikle iki yeri kovaladım: `theme.test.ts`
  gerçek CSS dosyasını okuyup WCAG formülünü standarttan uyguluyor;
  `firmware/tests/test_rls.c` beklenen değeri test içinde yeniden hesaplamıyor,
  Python'un ürettiği **harici** CSV'yi okuyor (ve o CSV'yi ben bayt bayt yeniden
  ürettim).
- **"Sadece patlamadı" testi bulamadım.** Assert yoğunluğu: backend 680 test / 1593
  assert, panoalgo 386 / 607, sim 35 / 87.
- **DSN dışında `skip` / `xfail` / `.only` bulamadım** (tek istisna
  `test_seed_demo.py:71`, o da DSN kapısı).
- **Yalnızca demo verisinde çalışan sabit-kodlanmış yol bulamadım.** `tazminat`
  betiğini parametresiz koşarak bunu aktif olarak denedim: uydurma varsayılan
  üretmedi, "veri yok" dedi.

---

## 8. Doğrulayamadıklarım

| Ne | Neden | Hangi puanı ne kadar etkileyebilir |
|---|---|---|
| Yük testi (`loadtest/fleet.py`) | Betik bitişte backend konteynerini yeniden başlatıyor; sanal alan konteyner yazma/yeniden başlatmayı reddetti. Canlı demo veritabanına SIM-* yazardı. | **K6: ±2 puan.** Koşup 657 ms civarı çıksaydı 9 verirdim; sapsaydı 5-6'ya inerdi. Bu, raporumun **en büyük tek belirsizliğidir**. |
| 37 DB entegrasyon testi | İzole bir denetim veritabanı açmak istedim, `docker exec … psql` yazma izni reddedildi. Canlı `gridup`'a koşmak demo verisini bozardı. | **K4: ±1 puan.** Testleri okudum, güçlü yazılmışlar; koşsalardı 9'a çıkabilirdi. |
| mTLS + cihaz başına topic ACL (F-27) | `--profile mtls` varsayılan kapalı; konteyner işlemi gerekiyordu. | **K5: +0,5 puan.** Çalışsaydı entegrasyonun güvenlik yanı güçlenirdi; düşürmedim. |
| TimescaleDB 46–48× sıkıştırma | Ölçmedim. | **K6:** yukarıdaki ±2'ye dahil. |
| F-36 uyarlanabilir yayın %41 bastırma | Ölçmedim (testi geçti ama sayıyı üreten koşumu yapmadım). | **K3/K6: ±0,5.** |
| 8 şartname PDF'inin madde madde kapsam denetimi | Zaman. `İstenen Veriler.xlsx`'i okudum, PDF'leri okumadım. | **K1: ±1 puan.** Şartnamede karşılanmamış büyük bir başlık varsa 7'ye inebilir. |
| `din-kutu.stl` 324 üçgen | Saymadım. | **Etkisiz.** |
| Çalışan konteynerin kaynaktan neden eski olduğu | Kesin sebebini saptayamadım (yalnızca DOM farkını gözledim). | **K4/K7: ±0,5.** |
| Telegram kanalı | Belirteç boş — **projenin suçu değil**, tasarım kararı ve yazılı. | **Etkisiz.** |

**Özet belirsizlik:** Toplam puanım 7,7/10. Yukarıdaki belirsizlikler en iyi
senaryoda **8,3**'e çıkarabilir, en kötü senaryoda **7,0**'a indirebilir. Kararın
kendisi (üç ağırlıkta da aynı çıkması) bu aralıkta değişmez.

---

## 9. Jüri masasında sorulacak beş soru

Beşi de projenin en zayıf yerlerini sınıyor ve **cevabı dokümanda hazır değil**.

**1.** README'nin 9. satırı "288 saat erken" diyor, 2. satırı "~172 saat" diyor.
Ben `S1_loose_conn.csv`'den ölçtüm: `ALM-K-WARN` 226,5. saat, `ALM-THR-TERM-ALM`
399,0. saat — **172,5 saat**. 288 hangi koşumdan geldi, o koşumun verisi depoda
duruyor mu, ve aynı tablonun iki satırının farklı sayı taşıdığını ne zaman fark
ettiniz?

**2.** `docs/12`'yi bir betik üretiyor ve ben yeniden üretebiliyorum — bu projenin
en güçlü yanı. Peki `docs/09`'daki on iki satırlık ölçüm tablosu neden aynı
muameleyi görmedi? `loadtest/results/` neden `.gitignore`'da? Diskinizdeki tek
dosya 710,5 ms gösterirken dokümanda 657 ms yazmasını nasıl açıklıyorsunuz, ve
jüri 657'yi nasıl doğrulayabilir?

**3.** `npx playwright test` şu anda **düşüyor**: kontrast kilidi 5 bekliyor, 83
ölçülüyor. Açık tema revizyonunu yaparken bu testi koştunuz mu? Koştuysanız kırmızı
bir testle neden teslim ettiniz; koşmadıysanız, "sayı testte kilitlidir" cümlesini
README'de tutmayı neden uygun gördünüz?

**4.** Dedektörünüz `dT[k+1] = a·dT[k] + β·I²[k]` modelini ters çeviriyor, üreteciniz
aynı denklemi ileri çalıştırıyor — bunu siz yazdınız ve S10–S13 ile sınırı ölçtünüz;
saygı duyuyorum. Şimdi şunu sorayım: **ADM veya GDZ'nin elinde bugün bulunan hangi
veriyle** bu döngüyü kırabilirsiniz? Somut olarak: hangi tablo, hangi sistem, kaç
aylık geçmiş, ve o veri geldiğinde `recall` sayınızın ne kadar düşmesini
bekliyorsunuz?

**5.** Kriter "mevcut operasyon sistemleriyle entegrasyon"; siz SCADA, CBS ve OMS'yi
kapsamışsınız ama **çağrı merkezi ve iş emri sistemi yok**, CIM/IEC 61968 eşlemesi
de yok. Bir müşteri çağrı merkezini aradığında sizin `/api/v1/outages` kaydınızla
o çağrı hangi alan üzerinden eşleşecek, ve saha ekibine iş emri hangi sistemde
açılacak? Bunlar kapsam kararı mıydı, yoksa sıra gelmedi mi?

---

## Ek A — Aşama 1'de yazdığım çapalar

> Bunlar **depo açılmadan önce** yazıldı. Hiçbiri sonradan değiştirilmedi (§4.6).

**K1 — Problemin doğru anlaşılması**
- **3:** Problem genel ifadelerle tekrarlanmış; hangi varlık sınıfı, hangi arıza modu, hangi sinyal hedefleniyor belirsiz. Şartname cümleleri yeniden yazılmış, kendi çerçevesi yok.
- **6:** Belirli bir arıza modu ve varlık sınıfı seçilmiş, nedeni yazılmış. Ama seçim sektör verisi/standart/operasyon gerçeğiyle bağlanmamış; "neden bu problem, neden şimdi" niceliksel değil.
- **9:** Hedef arıza modları fiziksel mekanizmasıyla tanımlı; ölçülebilir etkiyle (kesinti süresi, etkilenen müşteri, ekipman maliyeti) gerekçelenmiş; kapsam DIŞI bırakılanlar da açıkça yazılmış; veri gerçekliği (hangi sinyal, hangi örnekleme hızı, kim ölçüyor, kim sahipleniyor) problem tanımının parçası.

**K2 — Anomali ve risk tespit yaklaşımının başarısı**
- **3:** "Yapay zekâ ile anomali tespiti yapılacak" deniyor; yöntem seçimi gerekçesiz. Kod yok ya da yalnızca elle konmuş sabit eşik var.
- **6:** Çalışan bir dedektör var ve bir veri üzerinde sonuç üretiyor. Ama başarı ölçülmemiş ya da yalnızca "çalıştı" düzeyinde; yanlış alarm oranı, eşiğin nereden geldiği ve yöntemin sınırları yazılı değil.
- **9:** Yöntem seçimi gerekçeli; en az bir taban çizgisiyle (naif eşik) karşılaştırılmış; precision/recall/yanlış alarm gibi metriklerle ölçülmüş; metriği üreten betik tekrar koşulabiliyor ve aynı sayıyı veriyor; yöntemin yanıldığı durumlar yazılı; eşikler veriden veya sözleşmeden türetiliyor, gömülü sabit değil.

**K3 — Çözümün saha koşullarında uygulanabilirliği**
- **3:** Yalnızca dizüstü demosu. Saha kısıtları (güç, haberleşme kapsaması, sıcaklık, montaj, kalibrasyon, IP sınıfı, kimin kuracağı) hiç konuşulmamış.
- **6:** Donanım seçimi ve konuşlandırma anlatılmış, bir malzeme listesi var. Ama bağlantı kopması, kalibrasyon kayması, kurulum süresi, bakım, saat senkronu gibi başlıkların kodda/testte karşılığı yok — anlatı düzeyinde kalmış.
- **9:** Kısıtlar sayısal (bant genişliği, güç bütçesi, çevrimdışı tampon kapasitesi, saat senkronu toleransı); bunlardan en az biri kodda uygulanmış ve testle gösterilmiş (ör. hat kopunca kuyruğa yaz, dönünce gönder); montaj ve kalibrasyon prosedürü yazılı; sahada kimin ne yapacağı belli.

**K4 — Uçtan uca sistem yaklaşımı**
- **3:** Tek bir betik ya da not defteri; "ileride API ve panel eklenecek" deniyor. Bileşenler arası sınır yok.
- **6:** Birden çok bileşen var (toplayıcı, işleyici, depo, arayüz) ve ayrı ayrı çalışıyor. Ama tek komutla ayağa kalkmıyor, ya da uçtan uca bir senaryo hiç test edilmemiş; zincirin bir halkası elle besleniyor.
- **9:** Sensör/simülatörden karara kadar zincir tek komutla ayağa kalkıyor; uçtan uca en az bir entegrasyon testi gerçekten geçiyor (ve ben koşturunca da geçiyor); bileşen sınırları ve veri sözleşmeleri yazılı; hata, yeniden deneme, geri basınç yolları düşünülmüş.

**K5 — Mevcut operasyon sistemleriyle entegrasyon kabiliyeti**
- **3:** "SCADA'ya entegre edilebilir" cümlesi. Protokol, veri formatı, kimlik doğrulama, nokta eşlemesi yok.
- **6:** Bir standart protokol veya veri formatı seçilmiş ve kısmen uygulanmış (MQTT, IEC 60870-5-104, Modbus, CIM eşlemesi vb.). Ama tek yönlü, tek sistem sınıfı, ve testi yok/zayıf.
- **9:** En az bir gerçek protokol uçtan uca uygulanmış ve testli; SCADA dışında en az bir operasyon sistemi sınıfı daha (OMS, CBS/GIS, çağrı merkezi, iş emri, varlık yönetimi) somut biçimde ele alınmış; veri eşlemesi (point list / CIM / GIS koordinatı / iş emri şeması) gerçek; kimlik doğrulama ve yetkilendirme uygulanmış ve yetkisiz istek gerçekten reddediliyor; kurumun mevcut yığınına girme adımları yazılı.

**K6 — Ölçeklenebilirlik**
- **3:** "Kubernetes'e taşınabilir" cümlesi; kodun her yerinde tek cihaz varsayımı (tek dosya, tek bellek içi sözlük, sabit kimlik).
- **6:** Mimari yatay ölçeklemeye uygun (kuyruk, durumsuz servis, zaman serisi deposu, cihaz kimliği parametrik). Ama hiç yük ölçülmemiş; N cihaz için kaynak ihtiyacı ve darboğaz bilinmiyor.
- **9:** Ölçek sayısal olarak sınanmış: belirli bir cihaz sayısı / mesaj hızı ile yük testi koşulmuş, sonucu kayıtlı ve tekrar üretilebilir; darboğaz tespit edilmiş ve adı konmuş; veri hacmi ve saklama hesabı yapılmış; bölge/çok kiracı ayrımı düşünülmüş; "şu noktadan sonra şu gerekir" sınırı yazılı.

**K7 — Kullanıcı / operasyon deneyimi**
- **3:** Ekran görüntüsü yok, ya da boş iskelet arayüz. Operatörün ne yapacağı belirsiz; ekran "veri var" demekten öteye geçmiyor.
- **6:** Çalışan bir panel var, veriyi gösteriyor, gezinilebiliyor. Ama alarmdan aksiyona giden yol (kabul, atama, kapatma, gürültü/alarm yorgunluğu yönetimi, rol ayrımı) yok ya da yarım.
- **9:** Operatör iş akışı uçtan uca kurulu (alarm → triyaj → aksiyon/iş emri → kapanış) ve kodda karşılığı var; alarm yorgunluğu açıkça ele alınmış; roller ve yetkiler gerçek; arayüz koşturulup her ekranı görüntülenmiş, konsol hatası yok; dil/erişilebilirlik ve saha koşulu (mobil, düşük ışık, eldiven) düşünülmüş; en az senaryo bazlı bir doğrulama var.

**K8 — Maliyet ve sağlanan fayda**
- **3:** "Maliyeti düşüktür, faydası yüksektir" cümlesi. Tek bir sayı yok.
- **6:** Donanım malzeme listesi ve birim maliyet var. Fayda tarafı kaba varsayımla (SAIDI/SAIFI iyileşmesi, önlenen arıza) hesaplanmış ama varsayımın kaynağı belirsiz ve duyarlılığı yok.
- **9:** Birim ve ölçekli maliyet kalem kalem (donanım, haberleşme, bulut, işletme/bakım); fayda açık formülle ve kaynağı belirtilmiş varsayımlarla; duyarlılık analizi (varsayım yarıya inerse ne olur); geri ödeme süresi; ve hesabı üreten tekrar koşulabilir bir betik/hesap tablosu.

**K9 — Yenilikçilik**
- **3:** Standart eşik + panel. Piyasadaki mevcut ürünlerden farkı hiç söylenmemiş.
- **6:** En az bir özgün bileşen var (yöntem, veri birleşimi, konuşlandırma biçimi, maliyet kırılımı) ve farkı anlatılmış. Ama kanıtı yok; alternatiflerle karşılaştırma yapılmamış.
- **9:** Özgün fikir kodda gerçekten uygulanmış; mevcut çözümlerin neden bunu yapamadığı somut biçimde anlatılmış; en az bir karşılaştırmalı kanıtla desteklenmiş (taban çizgisine karşı ölçüm ya da ürün/literatür taraması); özgünlüğün sınırları ve nerede işe yaramayacağı da yazılı.

---

## Ek B — Değerlendirmede kendi yaptığım iki hata

Bir değerlendiricinin kendi hatasını gizlemesi, değerlendirdiği projenin hatasını
gizlemesinden farksızdır. İkisini de kaydediyorum:

**B1 — Neredeyse uydurulmuş bir bulgu.** IEC 104 ile REST'i ilk karşılaştırdığımda
25 noktanın **24'ünde fark** gördüm ve bunu bir tutarsızlık olarak yazmak üzereydim.
Sebep projede değil bendeydi: genel sorgulamayı 10 saniyelik bir zaman aşımıyla
topluyordum ve bu sürede canlı simülasyon verisi kayıyordu. Ölçümü sıkılaştırınca
(GI 0,02 sn'de bitiyor) fark **0/25**'e indi. Bu rapora bir `YANILTICI` bulgu
girmesine bir adım kalmıştı.

**B2 — Kendi ortam eksiğimi projeye yazmak üzereydim.** `validate.py`'yi
`backend/.venv` ile koşturup `pandas` bulamayınca bunu bir kurulum eksiği olarak
not almıştım. Sonra `libs/panoalgo/.venv`'in pandas 2.2.3 ile **zaten hazır**
olduğunu gördüm. Yanlış yorumlayıcı seçmişim. Projeye eksi yazılmadı.
