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

| Deneme | Haftalık tepe dT | 50 K altı? | ×3 → 70 K? |
|---|---:|---|---|
| 35 K | 34,6 | evet | evet |
| **40 K** | **39,5** | **evet** | **evet** |
| 55 K | 54,3 | **hayır** | evet |

İlk seçim 60 K'ydı; ölçüldü ki sağlıklı panoyu 59 K'ya çıkarıyor ve örneklerin %20'sinde
`ALM-THR-TERM-WARN` üretiyordu.

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
| PD | yalnızca OG; AG panoda `null` | Rapor §3.7 (Paschen ~327 V) |

## 5. Senaryo kataloğu

`python -m panoalgo.scenarios --list`

| Kimlik | Enjeksiyon | Beklenen tespit | Süre |
|---|---|---|---:|
| `S0_normal` | yok | yanlış alarm tabanı | 168 h |
| `S1_loose_conn` | K %0 → %200, sonra plato | `ALM-K-WARN/ALM`, `ALM-THR-TERM-*` | 720 h |
| `S2_overload` | yük ×1,8, **K sabit** | `ALM-I-OVER`; **`ALM-K-ALM` çıkmamalı** | 168 h |
| `S3_condense` | kış + nem +%25 | `ALM-DEW-WARN/ALM` | 168 h |
| `S4_arc` | TVOC-2 trip sayacı artar | `ALM-ARC-TRIP` | 72 h |
| `S5_prot_health` | dedektör sağlık biti düşer | `ALM-PROT-HEALTH` | 72 h |
| `S6_comms_loss` | 6 saat veri boşluğu | `ALM-COMMS-LOST` (**merkezde**) | 168 h |
| `S7_harmonic` | THD ×3,5 | `ALM-NEUTRAL-THD` | 168 h |
| `S8_sensor_fault` | donma + sürüklenme + düşme | `ALM-DQ-*`; **pano alarmı çıkmamalı** | 168 h |
| `S9_pd_trend` | OG panoda PD etkinliği artar | `ALM-PD-TREND` | 168 h |

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
gerçekten aşar ve `ALM-PANEL-TEMP` örneklerin yarısında **doğru** bir şekilde çıkar.
Bu bir yanlış alarm değildir — şartname ortam varsayımı 40 °C'dir ve aşılmaktadır — ama
yanlış alarm **tabanı** ölçmek istediğimiz bir senaryoda algoritmayı değil iklimi
ölçerdi. Yaz koşulunun kendisi ayrı bir bulgu olarak [docs/05](05-anomali-tespiti.md)'te
ve doğrulama tablosunda durur.

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
| `--baseline-hours` | taban öğrenmeyi kısaltır (aşağıda) |

Oynatma bitince hangi alarmın kaçıncı simüle saatte çıktığı ve etiketin beklediğiyle
karşılaştırması ekrana yazılır. S1'de sıralama şöyle görünür: `ALM-K-WARN` → `ALM-K-ALM`
→ (çok sonra) sabit 70 K eşiğinin ihlali `ALM-THR-TERM-ALM`. Ekrandaki saatlerin
**çözünürlüğü seyreltme adımı kadardır**; öne alma süresinin ölçülmüş değeri seyreltilmemiş
veriden hesaplanır ve `docs/12`'dedir: **209 saat** (kabul kriteri 48 saat).

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
