# 14. Sentetik Veri Üreteci — Spesifikasyon ve Senaryo Kataloğu

**Sahip:** Kişi A · **Kaynak:** HACKATHON_ANALIZ_RAPORU.md §15.2 · **Kod:** `libs/panoalgo/`, `sim/panosim.py`

## 0. Neden üreteç

Gerçek bir pano, 7–30 günlük bir bozulmayı demo süresinde gösteremez. Bir ısıtıcıyla
"sıcak nokta" taklit etmek de işe yaramaz: o, sıcaklığı yükseltir ama **bağlantının ısıl
direncini** değiştirmez — yani tam olarak ölçmek istediğimiz büyüklüğü değiştirmez.

Burada bozulma bir denklemle üretilir. Bu bir eksiklik değil, üç şey kazandırır:

1. **Hızlandırılabilir** — 30 günlük gevşeme dakikalar içinde oynatılır.
2. **Etiketlidir** — arızanın ne zaman başladığı tam olarak bilinir, bu yüzden öne alma
   süresi *ölçülebilir*.
3. **Savunulabilir** — her sayı bir denklemden gelir, jüriye formül olarak gösterilir.

> **Dürüstlük kuralı (PLAN.md Bölüm C):** bu belgedeki her şey simülasyondur ve öyle
> sunulur. Aşağıda "RAPORDA YOK — TÜRETİLMİŞ" ibaresi taşıyan sayılar, rapor bir değer
> vermediği için bizim seçtiğimiz değerlerdir; gerekçeleri yanlarında yazılıdır.

## 1. Zincir

```
yük profili (saat-of-hafta) × mevsim × AR(1) gürültü
   → faz akımları (dengesizlik) → nötr akımı (dengesizlik + 3. harmonik)
   → nokta başına ayrık ısıl model   dT[k+1] = a·dT[k] + (1−a)·K·I²[k]
   → ortam sıcaklığı (günlük sinüs + mevsim) ve ters ilişkili nem
   → Magnus çiy noktası + yoğuşma marjı
   → şemaya uyan telemetri sözlüğü
```

Sözleşme kuralı (PLAN.md kural 10): nokta adları `contracts/modbus-map.yaml`'dan,
eşikler `contracts/alarm-codes.yaml`'dan, `pano_id` deseni ve topic/QoS/retain telemetri
şemasından okunur. Üreteç kodunda gömülü sözleşme sayısı **yoktur**.

## 2. Yük profili

168 kutulu (saat-of-hafta) tablo, kutular arası doğrusal ara değerle. Üç profil:

| Profil | Pik saatleri (rapor §15.2) |
|---|---|
| konut | 07–09 ve 18–23 |
| ticari | 09–18 |
| karma | ikisinin ortalaması |

Hafta içi / hafta sonu ayrı tablolardır. **Karma yeniden normalize edilmez**: edilseydi
mesai ortasında ticariyi aşardı ve "iki profilin karışımı" olmaktan çıkardı.

*Kutu değerleri RAPORDA YOK — TÜRETİLMİŞ.* Rapor saat başı sayısal tablo vermez, nitel
tarif eder. Testler sayıları değil rapordaki iddiaları doğrular: konut akşam piki > gece,
ticari gündüz > gece, ticari hafta sonu düşer, karma ikisinin arasında.

**Mevsim katsayısı:** yıllık kosinüs, tepe ~27 Temmuz, genlik ±%18 (Ege yaz klima piki).
*TÜRETİLMİŞ.*

### 2.1 AR(1) gürültü — bir slayt değerinde

```
n[k] = phi1 * n[k-1] + eps[k]        phi1 = exp(-Ts/tau_yük)
yük[k] = profil × mevsim × (1 + n[k])
```

Verilen "İstenen Veriler.xlsx"te akım serisinin **lag-1 otokorelasyonu 0,00'dır**
(rapor §3.4a) — yani ardışık ölçümler birbirinden tamamen bağımsız. Bu fiziksel olarak
imkânsızdır: bir şebekenin yükü 15 dakikada hafızasını kaybetmez. Bizim serimizde
lag-1 > 0,9'dur ve bunu bir test kilitler (`test_load_series_is_strongly_autocorrelated`).

Bu, jüriye "verinizi eleştiriyoruz" diye değil, *"sistemimiz gerçek dışı ölçümleri ayırt
ediyor"* diye sunulur.

## 3. Isıl model

```
dT[k+1] = a·dT[k] + (1−a)·K·I²[k]        a = exp(−Ts/τ)
```

`I²[k]` **bir önceki** örneğin akımıdır (sıfırıncı derece tutucu) — rapor §15.1 ile aynı
indis. Bu detay küçük görünür ama üreteç ile kestirimci farklı indis kullanırsa 15
dakikalık dışa aktarımda K kestirimi ters yöne gider (ölçüldü: gerçek çarpan 2,0 iken
kestirim 0,47'ye düştü).

| Parametre | Değer | Kaynak |
|---|---|---|
| τ | 600–1800 s, nokta başına rastgele | Rapor §15.2 (10–30 dk) |
| K₀ | `dT_anma / I_anma²`, ±%15 dağılım | Rapor §15.2 ("nokta başına K₀, dağılımlı") |
| Ölçüm gürültüsü | σ = 0,2 K | Rapor §15.2 |
| Anma akımında sağlıklı artış | 40 K | **TÜRETİLMİŞ**, aşağıda |
| Tepe kullanım oranı | 0,80 | **TÜRETİLMİŞ** |

**"Anma akımında 40 K" nasıl seçildi.** İki kısıt arasında kalibre edildi ve ölçülerek
doğrulandı (yaz haftası, 15 dk örnekleme):

- Sağlıklı pano L0 **uyarı** eşiğini (50 K) geçmemeli — yoksa referans senaryo sürekli
  uyarı verir ve yanlış alarm ölçümü anlamsızlaşır.
- K üç katına çıktığında 70 K aşılabilmeli — yoksa sabit eşik hiç tetiklenmez ve
  "sabit eşikle karşılaştırma" yapılamaz.

| Deneme | Haftalık tepe dT | 50 K altı? | ×3 → 70 K? | Uyarı çıkan örnek payı |
|---|---:|---|---|---:|
| 35 K | 34,6 K | evet | evet (103,8 K) | %0,0 |
| **40 K** | **39,5 K** | **evet** | **evet (118,6 K)** | **%0,0** |
| 55 K | 54,3 K | **hayır** | evet (163,0 K) | %6,1 |
| 60 K | 59,3 K | **hayır** | evet (177,8 K) | **%20,7** |

*Tablonun kaynağı (GK10).* Sayılar 16 Eylül 2026'da bu depoda yeniden üretildi:
`libs/panoalgo/.venv` içinde `panoalgo.generator.DT_AT_RATED_K` sırayla 35 / 40 / 55 / 60 K
yapılıp `panoalgo.scenarios.plan("S0_normal", seed=1304, duration_h=168, season="yaz")` +
`iter_samples()` koşturuldu. "Haftalık tepe dT" = 672 örneğin en büyük `worst_dt_c` değeri;
"uyarı çıkan örnek payı" = `alarms` listesinde `ALM-THR-TERM-WARN` bulunan örneklerin oranı;
"×3 → 70 K?" sütunundaki parantez içi tepe dT'nin üç katıdır. Fixture'lar bu taramadan
etkilenmez; `DT_AT_RATED_K` kodda **40,0** olarak kalır.

İlk seçim 60 K'ydı; tablonun son satırı neden bırakıldığını gösterir: sağlıklı panoyu
59,3 K'ya çıkarıyor ve örneklerin **%20,7**'sinde `ALM-THR-TERM-WARN` üretiyordu — yani
"sağlıklı" senaryo sürekli uyarı veren bir senaryo olurdu. Aynı gerekçe kodun kendi
yorumunda da yazılıdır (`libs/panoalgo/panoalgo/generator.py`, `DT_AT_RATED_K`: 60 K →
59 K, örneklerin %20'si).

## 4. Ortam ve elektriksel büyüklükler

| Büyüklük | Model | Kaynak |
|---|---|---|
| Ortam sıcaklığı | günlük kosinüs, tepe 15:00; yaz 35–42 °C, kış 0–10 °C | Rapor §15.2 (İzmir/Aydın) |
| Nem | sıcaklıkla ters: +40 °C'de %50, +20 °C'de %90 → eğim 2 %/K | Rapor §3.1 Tablo 1 |
| Pano alt bölme havası | dış ortam + 2 K | **TÜRETİLMİŞ** |
| Üst–alt hava farkı | tam yükte 12 K'ya kadar, yükün karesiyle | **TÜRETİLMİŞ** |
| Faz dengesizliği | %2,5–14,5, yavaş değişen AR(1) | Rapor §15.2 (%2–15) |
| Nötr akımı | fazör toplamı ⊕ 3·I_h3 (triplen aritmetik toplanır) | Kapalı form **TÜRETİLMİŞ** |
| THD | hafif yükte yüksek: 4–8 % | **TÜRETİLMİŞ** |
| Gerilim | 231 V − yükle düşüş | **TÜRETİLMİŞ** |
| PD | yalnızca OG; AG panoda `null` | Gerekçe geometriktir, "Paschen ~327 V" kısayolu DEĞİL — bkz. `docs/05` §PD |

## 5. Senaryo kataloğu

`python -m panoalgo.scenarios --list`

| Kimlik | Enjeksiyon | Beklenen tespit | Süre |
|---|---|---|---:|
| `S0_normal` | yok | yanlış alarm tabanı | 168 h |
| `S1_loose_conn` | K %0 → %200, sonra plato | `ALM-K-WARN/ALM`, `ALM-THR-TERM-*` | 720 h |
| `S2_overload` | yük ×1,8, **K sabit** | `ALM-I-OVER`; yasaklı: `ALM-K-WARN`, `ALM-K-ALM` | 168 h |
| `S3_condense` | kış + nem +%25 | `ALM-DEW-WARN/ALM` | 168 h |
| `S4_arc` | TVOC-2 trip sayacı artar | `ALM-ARC-TRIP` | 72 h |
| `S5_prot_health` | dedektör sağlık biti düşer | `ALM-PROT-HEALTH` | 72 h |
| `S6_comms_loss` | 6 saat veri boşluğu | `ALM-COMMS-LOST` (**merkezde**) | 168 h |
| `S7_harmonic` | THD ×3,5 | `ALM-NEUTRAL-THD` | 168 h |
| `S8_sensor_fault` | donma + sürüklenme + düşme | `ALM-DQ-BELOW-AMBIENT`; yasaklı: `ALM-THR-TERM-ALM`, `ALM-K-ALM` | 168 h |
| `S9_pd_trend` | OG panoda PD etkinliği artar | `ALM-PD-TREND` | 168 h |
| `S10_coupling` | S1 + terminal grubu içi ısıl kuplaj | S1 ile **aynı** `expect` | 720 h |
| `S11_load_tau` | S1 + yüke bağlı zaman sabiti | S1 ile **aynı** `expect` | 720 h |
| `S12_two_pole` | S1 + ikinci (yavaş) ısıl kutup | S1 ile **aynı** `expect` | 720 h |
| `S13_sensor_nonlin` | S1 + ölçüm zinciri doğrusalsızlığı | S1 ile **aynı** `expect` | 720 h |

Son dört satır **model-uyumsuzluğu** senaryolarıdır ve `S1_loose_conn`'un kontrollü
klonudur; ayrıntısı §9'dadır.

Tablo `libs/panoalgo/panoalgo/scenarios.py` içindeki `SCENARIOS` sözlüğünün `expect` /
`not_expect` alanlarını birebir yansıtır; "yasaklı" sütun parçası `not_expect`tir.

**S8'in yasaklı listesi bir pano alarmını yakalamıyor ve bunu saklamıyoruz.** Ölçüm:
`S8_sensor_fault` senaryosunda 70 K sınırı **hiç aşılmadığı hâlde 183 prognoz üretildi** ve
bunların **86'sı `ALM-TTL-14D`** olarak açıldı — bu kod `contracts/alarm-codes.yaml`'da
**P3 / L1**'dir, yani veri kalitesi ya da sistem alarmı değil, tam anlamıyla bir **pano
alarmıdır**. `not_expect` yalnızca `ALM-THR-TERM-ALM` ve `ALM-K-ALM`'i yasakladığı için
senaryo bunu kırmızıya düşürmez. Ölçülmüş bir **prognoz yanlış-alarmıdır**:
[docs/12 §4.3](12-dogrulama-sonuclari.md) ve [docs/05 §10](05-anomali-tespiti.md).

**Enjeksiyon felsefesi:** hiçbir senaryo "şu alarm çıksın" demez. K'yi büyütür, yükü
artırır, sensörü bozar. Alarmın çıkıp çıkmayacağına tespit katmanları karar verir —
aksi hâlde test, algoritmaya cevabı fısıldamış olurdu.

### 5.1 S1 kalibrasyonu (kabul kriterinin dayanağı)

PLAN.md TA2 kabul kriteri: *K/K₀ 1,6'yı L0 ihlalinden en az 48 saat önce geçmeli.*
İki kısıt birlikte sağlanmalıydı; yük çarpanı taranarak seçildi (720 h, seed 1304):

| Yük | Tepe dT | 70 K aşıldı mı | K>1,6 öne alma |
|---|---:|---|---:|
| 0,85 | 63 K | hayır | — |
| 0,90 | 71 K | evet | 149 h |
| **0,95** | **79 K** | **evet** | **125 h** |
| 1,00 | 88 K | evet | 73 h |

0,95 seçildi: ihlal payı rahat, öne alma kriterin iki katından fazla.

Rampa pencerenin %50'sinde tamamlanır, kalanı platodur. Rapor §15.2 bozulmayı
*"7–30 gün boyunca %0 → %200 artış; ileri evrede aralıklı sıçramalar"* diye tarif eder —
yani K sonsuza kadar doğrusal büyümez. Plato ayrıca en yüksek K ile en yüksek **yükün**
aynı güne denk gelmesine zaman bırakır; kısa platoyla ölçüldü ki tepe artış 53 K'da
kalıyor ve 70 K'ya hiç ulaşılmıyordu.

### 5.2 S0'ın mevsimi

S0 ve diğer ısıl olmayan senaryolar **geçiş mevsiminde** (Nisan) kurulur. Sebep
ölçülmüştür: Ege yazında ortam 35–42 °C'ye çıktığı için pano iç havası 45 °C eşiğini
(`contracts/alarm-codes.yaml`, `panel_temp_alarm_c`) gerçekten aşar ve `ALM-PANEL-TEMP`
**doğru** bir şekilde çıkar. Ölçüm (16 Eylül 2026, aynı `S0_normal` senaryosu yalnızca
mevsimi değiştirilerek, seed 1304, 168 h → 672 örnek; `panoalgo.scenarios.plan(...,
season=...)` + `iter_samples()`):

| Mevsim | `ALM-PANEL-TEMP` taşıyan örnek | En yüksek pano iç hava sıcaklığı |
|---|---:|---:|
| yaz | 348 / 672 = **%51,8** | 51,3 °C |
| geçiş | 0 / 672 = **%0,0** | 28,6 °C |

Bu bir yanlış alarm değildir — şartname ortam varsayımı 40 °C'dir ve aşılmaktadır — ama
yanlış alarm **tabanı** ölçmek istediğimiz bir senaryoda algoritmayı değil iklimi
ölçerdi. Yaz koşulunun kendisi ayrı bir bulgu olarak [docs/05](05-anomali-tespiti.md)'te
ve doğrulama tablosunda durur.

**Fixture ile canlı demo burada ayrışır ve bu bilinçlidir.** Fixture'lar (ve dolayısıyla
`docs/12`'nin 71,4 alarm/100 pano/gün tabanı) senaryonun kendi mevsiminde — geçişte —
üretilmeye devam eder; fixture üretimi `--season` bayrağını **almaz**. Canlı demoda S0
`--season yaz` ile oynatılır (`demo/senaryo/s0.sh`), çünkü aynı sağlıklı pano aynı
sözleşme eşiğiyle yazda **0,0** çiy olayı üretir (§8.2 tablosu). Eşik değişmedi, oynatılan
mevsim değişti.

## 6. Çıktı biçimi ve tekrarlanabilirlik

- **Çözünürlük:** kenar 1 s işler → merkeze 10 s özet; fixture dışa aktarımı **15 dk**
  (rapor §15.2, Excel formatıyla uyum).
- **Fixture'lar:** `data/fixtures/<senaryo>.csv` + `<senaryo>.labels.json`, seed'li,
  en büyüğü 412 KB (PLAN.md kural 4 sınırı 1 MB).
- **Etiket şeması:** `contracts/scenario-labels.schema.json` (donmuş).
- **Aynı seed aynı veriyi verir** — bir test bunu kilitler.

```bash
python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures
python scripts/validate.py --out docs/12-dogrulama-sonuclari.md
```

## 7. Canlı yayın

`sim/panosim.py` iki kipte çalışır.

### 7.1 Sürekli kip — sağlıklı filo trafiği

```bash
python -m sim.panosim --panels 3 --speed 60 --mqtt mosquitto:1883
```

Her mesaj yayınlanmadan önce telemetri şemasına karşı doğrulanır (sözleşme kapısı);
geçersiz mesaj yayınlanmaz. Yük `json.dumps(..., allow_nan=False)` ile serileştirilir —
NaN/Infinity backend'de karantinaya düşer.

### 7.2 Senaryo kipi — etiketli arızanın canlı oynatılması

```bash
python -m sim.panosim --list-scenarios
python -m sim.panosim --scenario S1_loose_conn --point DSYA3_L2        --pano SIM-00001 --duration 90 --mqtt mosquitto:1883
```

Oynatılan fizik, §6'daki fixture'ları ve `docs/12` doğrulama tablosunu üreten fiziğin
**birebir aynısıdır**: ikisi de `panoalgo.scenarios.iter_samples()` yürütücüsünden geçer.
Demoda gösterilen eğri ile raporda savunulan sayı aynı koddan gelir; ayrışmaları mümkün
değildir (`sim/tests/test_panosim_scenario.py`).

Yürütücü fiziği **15 dakikalık adımlarla** koşturur ve bunların yalnızca her *N*'incisini
yayınlar. *N*, `--duration` (duvar saati süresi) ve `--period` (yayınlar arası süre,
varsayılan 1 s) değerlerinden hesaplanır. Bu, gerçek kenarın "1 s işle, 10 s'de bir özet
gönder" davranışının aynısıdır; seyreltme fiziği değil yalnızca raporlama sıklığını etkiler.

| Bayrak | Anlamı |
|---|---|
| `--scenario` | S0–S9 kimliği (`--list-scenarios`) |
| `--pano` | yayının yapılacağı pano kimliği |
| `--duration` | oynatmanın **duvar saati** süresi (sn) |
| `--scenario-hours` | senaryonun **simüle** süresi; varsayılan senaryonun kendi değeri |
| `--point` | enjeksiyon noktası (S1: `DSYA3_L2`) |
| `--detector` | S5'te arızalanan TVOC-2 dedektörü (`X2:4`) — PDU 222'de o bit düşer |
| `--season` | oynatılan mevsim (`kis` / `gecis` / `yaz`); verilmezse senaryonun kendi mevsimi |
| `--baseline-hours` | taban öğrenmeyi kısaltır (aşağıda) |

Oynatma bitince hangi alarmın kaçıncı simüle saatte çıktığı ve etiketin beklediğiyle
karşılaştırması ekrana yazılır. S1'de sıralama şöyle görünür: `ALM-K-WARN` → `ALM-K-ALM`
→ (çok sonra) sabit 70 K eşiğinin ihlali `ALM-THR-TERM-ALM`. Ekrandaki saatlerin
**çözünürlüğü seyreltme adımı kadardır**; öne alma süresinin ölçülmüş değeri seyreltilmemiş
veriden hesaplanır ve `docs/12`'dedir: **209 saat** (kabul kriteri 48 saat) — ama bu sayıyı
tetikleyen kod `ALM-TTL-14D`'dir, yani prognoz; yukarıdaki K/K₀ sıralamasına dayanan öne alma
**172,5 saattir** (`docs/05` §10).

### 7.3 Zaman damgası kararı (K3, 15 Eylül)

**Fizik hızlandırılmış kalır, yayınlanan `ts` duvar saatidir.** Varsayılan budur;
`SIM_WALL_CLOCK=0` ya da `--sim-clock` eski davranışı geri verir.

Neden değiştirildi: `--speed 60` ile simülasyon saati gerçek zamandan 60 kat hızlı akar.
Eskiden `ts` de simüle zamandı, dolayısıyla zaman damgaları duvar saatinin önüne geçiyordu
— ölçüm: yığın 11 dakika çalıştıktan sonra en yeni `ts` duvar saatinden **10,5 saat**
ileride, **11.757 satır** geleceğe tarihliydi. Arayüzün trend, K trendi ve çiy noktası
grafikleri `to = new Date()` penceresi kullandığı için yeni veri grafiğe **hiç girmiyordu**
(`frontend/src/pages/TrendKorelasyon.tsx:52`).

Sonuç ve sınırı açıkça: kenar alanları (K/K₀, τ, `ttl_h`) **simüle zamanda** hesaplanır —
fizik doğrudur — ama yayın anı duvar saatiyle damgalanır. Grafikte x ekseni gerçek zamandır
ve eğri 60 kat sıkıştırılmıştır. Bu bilinçli bir sunum seçimidir; sunumda böyle anlatılır.

Damgalar pano başına **kesin artandır**: aynı saniyeye iki örnek düşerse ikincisi bir saniye
ileri kaydırılır (aksi halde trend grafiğinde üst üste binerler).

### 7.4 Taban öğrenme ve canlı demo (Y1)

Sözleşme `baseline_learning_days: 7` der; bu 168 simüle saattir ve o ana kadar K/K₀ = 1,0
döner (devreye alma gününde sahte alarm olmaması için). Sürekli kipte `--speed 60
--period 10` ile bu **≈2,8 gerçek saat** eder — canlı demoda K/K₀ alarmını görmek
imkânsızdır.

İki çözüm vardır ve ikisi de dürüsttür:

1. **Senaryo kipini kullanın** (önerilen). Oynatma taban öğrenmeyi simüle zamanda geçer;
   S1 90 saniyede 720 simüle saat akıtır ve K/K₀ alarmı demonun içinde çıkar.
2. `--baseline-hours` ile taban öğrenmeyi kısaltın. Bu **sözleşme eşiğini değiştirmez**,
   yalnızca o koşudaki öğrenme penceresini kısaltır; fixture üretimi bu bayrağı asla
   kullanmaz (`docs/12`'nin sayıları sözleşme değeriyle hesaplanmıştır).

## 8. Üreteci kullanan araçlar

Üreteç yalnızca fixture ve canlı yayın üretmez; iki araç onu doğrudan çağırır. İkisi de
`libs/panoalgo`'yu içeri aktardığı için **kendi sanal ortamlarıyla** koşar.

| Araç | Ne yapar | Sanal ortam | Neden o ortam |
|---|---|---|---|
| `scripts/seed_demo.py` (F-01) | Altın demo veritabanı | `backend/.venv` | backend'i (`app.db`, `app.risk`, `app.alarm_manager`) içeri aktarır |
| `scripts/threshold_sweep.py` (F-06) | Çiy eşiği taraması | `libs/panoalgo/.venv` | yalnızca `panoalgo`'yu içeri aktarır, veritabanına dokunmaz |

### 8.1 `scripts/seed_demo.py` — altın demo veritabanı

```bash
backend/.venv/Scripts/python scripts/seed_demo.py \
  --dsn postgresql://postgres:gridup@localhost:5432/gridup --reset
backend/.venv/Scripts/python scripts/seed_demo.py --dry-run   # veritabanına dokunmaz, özet basar
```

Tek komutla: bekleyen şema göçleri + **≥7 günlük geçmiş** + **taban öğrenmesi tamamlanmış**,
tohumlu ve tekrar üretilebilir bir demo veritabanı. Gerekçe §7.4'ün devamıdır: sözleşme
`baseline_learning_days: 7` der, taze bir `down -v` sonrası K/K₀ bir hafta boyunca 1,0
döner ve erken uyarı hikâyesinin tamamı ölçülemez. Rapor üreten her madde sessizce "en az
bir hafta temiz veri" varsayar; bu betik o zemini bir kez üretir. Senaryo `S0_normal`
(sağlıklı filo — demo zemini temiz veri olmalı).

**Ölçüldü** (16 Eylül 2026, bu makine, `scripts/seed_demo.py` özeti): 3 pano / 21 gün /
tohum 1304 → **1.142.265 telemetri satırı**, **2 dk 08 sn**; aynı tohum aynı özeti verir
(`backend/tests/test_seed_demo.py::test_same_seed_and_window_give_the_same_summary`,
`::test_seeding_twice_writes_the_same_database`).

**Neden veritabanına doğrudan yazıyor, MQTT'den akıtmıyor** (betiğin docstring'i):

1. **Backfill kuralı.** `app/db.py` `_UPSERT_LATEST` ve `alarm_manager.observe`, panonun
   son işlenen `ts`'inden eski örneğin canlı durumu değiştirmesine izin vermez. MQTT'den
   akıtırken `panosim` varsayılan olarak `ts`'i duvar saatiyle damgalar (§7.3): geçmiş diye
   yayınlanan her mesaj "şu an" olarak yazılır, 7 günlük geçmiş oluşmaz. `--sim-clock` ile
   simüle damga yayınlansa bile örnekler duvar saatinin **önüne** geçer ve bu kez sonradan
   gelen canlı veri backfill kuralına takılır.
2. **Tekrar üretilebilirlik.** Broker + kuyruk + toplu yazma yolu kayıplıdır ve zamanlamaya
   bağlıdır (ingest kuyruğu dolarsa mesaj düşürülür). "Aynı tohum → aynı satır sayısı" sözünü
   ancak deterministik bir yazma yolu verebilir.
3. **Süre.** 21 günlük geçmiş, 15 dk örneklemeyle pano başına 2.016 mesajdır; broker
   üzerinden gerçek zamanlı akıtmak demoyu bir teslimden uzun sürdürürdü.

**Üretim yolundan sapmaz.** Yük, panoalgo fizik üreteci + kenar tespit boru hattından
(`EdgePipeline`) çıkar, `contracts/mqtt-telemetry.schema.json`'a karşı doğrulanır,
`app.ingest.flatten` ile ayrılır, `app.db.PgStore.write_batch` ile yazılır; alarmlar
üretimdeki `app.risk.RiskEngine` + `app.alarm_manager.AlarmManager` ile üretilip
`PgStore.save_alarm_changes` ile kaydedilir. Betik veriyi **uydurmaz, yalnızca MQTT adımını
atlar**.

Dürüstlük sınırları, betiğin kendi yazdığı gibi:

- Üretilen her satır **sentetiktir**; künye `demo_seed` tablosunda ve her panonun
  `panels.notes` alanındadır, betik bitişte aynı cümleyi ekrana basar.
- Geleceğe tarihli satır **üretilmez** (aksi hâlde canlı simülatörün sonraki mesajları
  backfill kuralına takılır ve arayüz günlerce güncellenmez).
- `notifications` tablosu **boş kalır**: teslim gecikmesi ancak gerçek bir bildirim ağ
  geçidi çalışırken ölçülür, uydurulmaz. Grafana'daki "Uçtan uca bildirim p95" paneli bu
  yüzden demo veritabanında boştur, canlı yığın açılınca dolar.
- Taban öğrenme penceresinden kısa bir `--days` değeri **reddedilir**
  (`::test_a_window_shorter_than_baseline_learning_is_refused`).

### 8.2 `scripts/threshold_sweep.py` — çiy eşiği taraması

```bash
libs/panoalgo/.venv/Scripts/python scripts/threshold_sweep.py --verify --seasons
```

Eşiği **değiştirmez, savunur**. `contracts/alarm-codes.yaml` donmuştur (PLAN.md kural 3);
tarama ya mevcut çifti savunur ya da `contracts/changes/` altına bir öneri için kanıt
üretir. Motivasyon `docs/12` **§3'te** (yanlış alarm yükü) ölçülen tek gerçek zayıflıktır:
sağlıklı panoda 71,4 yanlış alarm/100 pano/gün ve tamamı `ALM-DEW-*`.

Sınırı açıkça yazıyoruz: bu, **sistemin tek zayıflığı değildir**. Ölçülmüş ve daha ağır
olan diğer zayıflık prognoz geri testidir (`docs/12` §4: `S1_loose_conn`'da 790 tahminin
yalnızca **%5,2**'si alfa = 0,20 konisinde, **prognostik ufuk yok**, CRA **−5,12**, medyan
tahmin/gerçek 1,69; `S8_sensor_fault`'ta 99 prognoz yanlış-alarmı, bu belgede §5). Bu tarama çiy
eşiğini savunur, prognoza **dokunmaz** ve onu iyileştirmez.

| Bayrak | Anlamı |
|---|---|
| (bayraksız) | ızgara + eşik çifti taraması, tablo ekrana |
| `--verify` | kestirme yolun kanıtı: sözleşme eşiğiyle hesaplanan kodlar fixture'ın hazır `alarms` sütunuyla satır satır karşılaştırılır |
| `--rerun` | her ızgara noktası için `contracts/` dizininin geçici kopyası o eşikle yazılır ve senaryo üreteç + kenar boru hattından baştan koşturulur |
| `--seasons` | aynı senaryo üç mevsimde (kış / geçiş / yaz), eşik sabit |
| `--out` | markdown çıktısı dosyaya |

**Neden kestirme yol var.** Çiy kararı `limits._environment()` içinde tek bir alan üzerinde
tek bir kesin küçüktür karşılaştırmasıdır: `env.td_margin_k < eşik`. Eşik ne fiziğe, ne
üretece, ne de `td_margin_k` değerine girer — yalnızca karşılaştırmaya girer. Bu yüzden her
ızgara noktasında fixture yeniden üretilmez; karar `td_margin_k` sütunu üzerinde yeniden
koşturulur. **Ölçüldü** (betiğin docstring'i; 168 h / 672 örnek, 11 noktalı ızgara): hızlı
yol **0,024 s**, `--rerun` **30,9 s** (nokta başına ~2,8 s) ve iki yol **aynı** sonucu
veriyor — yani kestirme ~**1.300 kat** ucuz ve bedava değil, kanıtı bu iki bayraktır.

**Mevsim taraması** (aynı sağlıklı senaryo, eşik sabit 3,0 / 1,0 K; `--seasons`):

| Mevsim | Olay/100 pano/gün |
|---|---:|
| kış | 28,6 |
| geçiş | **71,4** |
| yaz | **0,0** |

Eşiği kısmak yükü **azaltmıyor, artırıyor**: 1,0 / 0,0 çifti 171,4 olay/100 pano/gün üretir
ve sözleşmenin kabul edilebilir günlük bütçesini (150) aşar. Tam tablolar ve yorumu
[docs/05 §11](05-anomali-tespiti.md); testleri `libs/panoalgo/tests/test_threshold_sweep.py`
(ör. `::test_rerunning_the_detection_gives_the_same_numbers_as_the_shortcut`,
`::test_rerunning_never_touches_the_frozen_contract`,
`::test_the_dew_thresholds_in_the_contract_are_unchanged`).

## 9. Model uyumsuzluğu enjeksiyonları

Bu bölümün var olma sebebi bir **itiraftır.** §3'teki ısıl model ile
`libs/panoalgo/panoalgo/detect.py`'nin kestirdiği model **aynı denklemdir**:

```
üreteç   dT[k+1] = a·dT[k] + (1−a)·K·I²[k]          a = exp(−Ts/τ)
dedektör dT[k+1] = a·dT[k] + β·I²[k]      ,  K = β/(1−a)
```

Arıza da `spec.k0 · _k_multiplier[...]` ile **doğrudan kestirilen parametreye** enjekte
ediliyor. Dolayısıyla [docs/12](12-dogrulama-sonuclari.md) §1'deki "sekiz senaryoda
duyarlılık 1,00" sonucunun bir bölümü *"kestirici kendi ileri modelini ters
çevirebiliyor"* demektir. Sahadaki asıl zorluklar — komşu terminal kuplajı, yüke bağlı
zaman sabiti, ikinci ısıl kutup, ölçüm zinciri doğrusalsızlığı — 19 Eylül'e kadar
**hiç sınanmamıştı**.

`ModelMismatch` (`generator.py`) bu dördünü ekler. **Hepsi varsayılan olarak kapalıdır**
ve kapalıyken üreteç bit düzeyinde TA1 davranışındadır (ölçüldü: S0–S9'un on CSV'si
`cmp` altında bayt bayt aynı). **Dedektöre hiçbir şey eklenmedi** — amaç onu
güçlendirmek değil, **sınırını ölçmek**.

### 9.1 Dört fizik

| Bayrak | Denklem | Dedektörün bozulan varsayımı |
|---|---|---|
| `coupling_k` | `+ c·(ort(dT_komşu) − dT_kendi)` | regresör `[dT, I²]` — nokta **tek başınadır** |
| `tau_load_coeff` | `τ = τ₀·exp(c·I/Iₙ)` | `a = exp(−Ts/τ)` **sabit** parametredir |
| `slow_share` | hızlı bara kutbu + yavaş kabin havası kutbu | sistem **birinci mertebedir** |
| `sensor_gain_per_k` | `dT_ölçülen = dT/(1 + g·dT)` | ölçüm **doğrusaldır** |

"Komşu", aynı terminal grubundaki diğer noktalardır (`GIRIS_L1/L2/L3/N` kendi arasında,
`DSYA3_L1/L2/L3` kendi arasında). Gruplama `detect.phase_compare`'in kullandığı
gruplamanın **aynısıdır** ve bu bilinçlidir: kuplaj, faz karşılaştırmasının referans
medyanını **içeriden** kirletir — kuralın en sert sınavı budur.

**Kuplaj neden toplamalı değil difüzif.** İlk taslak `steady += c·ort(dT_komşu)`'ydu.
Kararlı hâli `K·I²/(1−c)` yapıyor, yani **panoyu ısıtıyor**: ölçüldü, tepe artış
79,0 K → 90,6 K (c = 0,25). O zaman ölçülen fark "model yanlış" ile "pano daha sıcak"
arasında ayrıştırılamazdı. Difüzif biçimde (Fourier: akış sıcaklık **farkıyla**
orantılıdır) grup tekdüze ısındığında terim **sıfırdır**; değişen şey panonun ortalama
sıcaklığı değil **grup içindeki yapıdır**.

**İkinci kutupta arıza çarpanı İKİ kutba da girer**, yani kararlı hâl toplamı korunur ve
uyumsuzluk tamamen **dinamiktedir**. Alternatif (çarpanı yalnızca hızlı kutba uygulamak)
ölçüldü ve reddedildi: tepe artış 64,8 K'ya düşüyor ve 70 K sınırına hiç ulaşılmıyor —
ölçülen şey model uyumsuzluğu değil **çalışma noktası kayması** olurdu.

### 9.2 Ölçülen — hipotez kısmen yanlışlandı

Beklenti *"uyumsuz senaryolarda duyarlılık 1,00'ın altına iner"* idi. Ölçüm bunu
**yalnızca bir senaryoda** doğruladı ve nedenini açıkladı. Alarm kuralları K'yı değil
**K/K₀ oranını** okur; taban K₀ **aynı uyumsuz fizikle** öğrenildiği için durağan bir
yanlılık payda ile birlikte sadeleşir:

```
k_ratio = (g·K) / (g·K₀) = K / K₀
```

720 h, tohum 1304, yaz, `DSYA3_L2`; her satır eşleşen ikizle **aynı** koşulda:

| Konfigürasyon | Gerçek tepe artış | Ölçülen tepe artış | Yayımlanan τ | Recall | Yasaklı alarm |
|---|---:|---:|---:|---:|---|
| eşleşen (taban, `S1`) | 78,90 K | 78,96 K | 689 s | 1,00 | yok |
| `coupling_k = 0,15` | — | 73,0 K | 903 s | 1,00 | yok |
| `tau_load_coeff = −0,8` | — | 79,3 K | 481 s | 1,00 | yok |
| `slow_share = 0,45` | — | 72,3 K | **6.576 s** | 1,00 | **`ALM-DQ-DRIFT`** |
| `sensor_gain_per_k = 0,008` | **78,90 K** | **48,48 K** | 2.489 s | **0,50** | yok |

Dört bulgu, dördü de `docs/12`'den yeniden üretilebilir:

1. **Ölçüm zinciri doğrusalsızlığında sabit 70 K eşiği tamamen körleşiyor.** Terminal
   gerçekte **78,90 K**'da — eşleşen ikizle **ondalık basamağına kadar aynı**; pano aynı
   derecede sıcak, yalan söyleyen **alet**. Ölçüm 48,48 K gösteriyor, `ALM-THR-TERM-ALM`
   ve `ALM-THR-TERM-WARN` **hiç çıkmıyor** ve recall 0,50'ye iniyor. Oran tabanlı K
   tespiti ise **ayakta kalıyor** (`k_ratio` 3,01 > 1,6). Bu, `docs/05` §1'deki "neden
   sabit eşik yetmiyor" sorusunun **deneysel** cevabıdır.
2. **Yayımlanan τ 9,5 kata kadar yanlış** (689 s → 6.576 s). τ, `min_ttl_h` hesabına
   girer; bu, `docs/12` §4'teki kötü prognoz sonucunun bir **açıklamasıdır**.
3. **Kayma kuralı yanlış teşhis koyuyor.** İkinci ısıl kutupta `ALM-DQ-DRIFT` tetikleniyor
   ve işaretlenen nokta senaryonun **gerçekten arızalı** olduğu noktadır (`DSYA3_L2`;
   tohum 42 / 168 h: 13 örnek, ilk kez 79,25 saat sonra). Yani gerçek bir ısıl olay
   "kalibrasyon şüpheli" diye etiketleniyor — operatörün gerçek arızayı alet hatası
   sanıp kapatmasına yol açabilecek en kötü yanlış teşhis. Kilitleyen test:
   `test_drift.py::test_kayma_yalnizca_kayan_sensorde_isaretlenir[S12_two_pole]`.
4. **Kuplaj arızayı yanlış terminale yazdırıyor.** `k_ratio` eşiğini aşan nokta sayısı
   1'den **2'ye** çıkıyor: arızasız bir komşu da suçlanıyor. Teşhis "hangi pano"
   düzeyinde doğru, **"hangi klemens" düzeyinde yanlıştır** — saha ekibi yanlış uca gider.

`S11_load_tau` tabloda **"uyumsuz ama recall 1,00"** satırıdır ve bilerek yayımlanır:
bloğun seçmeci olmadığının kanıtıdır. τ işaretinin fiziksel yönü ölçülmemiştir (doğal
taşınım negatifi, katılan kütlenin derinleşmesi pozitifi işaret eder), ama **sonuç
işaretten bağımsızdır**: c = −0,8 (τ 481 s), −0,4 (569 s), +1,0 (1.223 s) — üçünde de
tepe `k_ratio` 3,00–3,02 ve beklenen dört kodun **dördü de** çıkıyor.

### 9.3 Bilinen sınır (GK10)

Dört fizik de **sentetiktir ve saha verisiyle doğrulanmamıştır.** Katsayılar fiziksel
olarak makul aralıklardan seçilmiş, **ölçülmemiştir**. Sahada kapatmak için gereken:

| Bayrak | Gereken saha ölçümü |
|---|---|
| `coupling_k` | aynı grupta iki terminale termokupl, birine kontrollü ek direnç; farkın komşuya geçiş oranı |
| `tau_load_coeff` | yük basamağı testi; iki farklı yük seviyesinde τ'nun ayrı ayrı kestirimi |
| `slow_share` | kabin içi hava sıcaklığının bağımsız ölçümü; basamak yanıtının iki üstel ile uydurulması |
| `sensor_gain_per_k` | sensörün referans termokupla karşı kalibrasyonu, 20–100 K artış aralığında |

Ayrıca dördü **tek tek** açılıyor. Gerçek bir panoda hepsi aynı anda vardır ve etkileri
toplanabilir de, birbirini götürebilir de. Birleşik senaryo bilerek eklenmedi: ölçüm o
zaman hangi varsayıma atfedileceğini kaybederdi. Bu, **kapatılmamış bir boşluktur**.

Tam gerekçe ve onay süreci:
[`contracts/changes/2026-09-19-model-uyumsuzlugu-senaryolari.md`](../contracts/changes/2026-09-19-model-uyumsuzlugu-senaryolari.md).
