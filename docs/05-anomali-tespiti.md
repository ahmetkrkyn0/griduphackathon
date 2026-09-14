# 05. Anomali Tespiti — Formüller, Eşikler ve Katmanlar

**Sahip:** Kişi A · **Kaynak:** HACKATHON_ANALIZ_RAPORU.md §6.5 ve §15.1 · **Kod:** `libs/panoalgo/`

Bu belge, sistemin bir arızayı **nasıl** anladığını anlatır. Her formülün kod karşılığı ve
her eşiğin sözleşme karşılığı verilmiştir. Ölçülen sonuçlar [12-dogrulama-sonuclari.md](12-dogrulama-sonuclari.md)'dedir.

## 0. Tek cümlelik özet

Sabit bir sıcaklık eşiği, arızayı ancak hasar oluştuktan sonra görür. Biz sıcaklığı
**akıma göre normalize ederek** bağlantının fiziksel sağlığını (ısıl direnç indeksi K)
ölçüyoruz; K bozulmaya çok daha erken tepki verir. Ölçülen fark: aynı veride
**209 saat (8,7 gün)** önce uyarı.

## 1. Neden sabit eşik yetmiyor

Bir bağlantının ısınması akımın karesiyle orantılıdır:

```
dT = K * I^2
```

Buradaki `K` bağlantının kendi özelliğidir (temas direnci × ısıl direnç). Gevşeyen bir
bağlantıda `K` büyür — ama `dT` yalnızca **o anda akım yüksekse** büyür. Yani:

- Gece, düşük yükte: bağlantı ciddi biçimde bozulmuş olabilir, sıcaklık normaldir.
- Gündüz, tepe yükte: sağlıklı bir bağlantı bile ısınır.

Sabit 70 K eşiği ikisini ayıramaz. `K` ise yükten bağımsızdır: **aynı bağlantının
dünkü hâliyle bugünkü hâlini** karşılaştırır.

## 2. Katman haritası

| Katman | Ne yapar | Kod | Ürettiği alan / kod |
|---|---|---|---|
| **L-1** | Bozuk ölçümü arızadan ayırır | `quality.py` | `t_conn[].q` bitleri |
| **L0** | Mutlak limit karşılaştırması | `limits.py` | `ALM-THR-*`, `ALM-I-OVER`, `ALM-PANEL-TEMP` |
| **L1** | Fizik tabanlı tespit | `detect.py` + `limits.py` | `ALM-K-*`, `ALM-TTL-14D`, `ALM-DEW-*`, `ALM-NEUTRAL-THD`, `ALM-PD-TREND` |
| **L3** | Hipotez füzyonu | `fusion.py` | `risk.score`, `risk.mode`, `risk.contributions` |
| **L4** | Açıklama (Kişi B) | `backend/app/risk.py` | alarm kartındaki "Neden / Ne yapmalı" |

Bu katmanları kenarda birleştiren boru hattı `edge.py`'dir. **Tespit kenarda çalışır**,
çünkü merkezdeki kanca (`backend/app/risk.py` `CentralDetector`) yalnızca `list[str]`
kabul eder; K, τ, ttl ve `q` merkeze ancak telemetri alanlarıyla girebilir.

## 3. L1 — Isıl direnç indeksi K

### 3.1 Model

```
sürekli :  tau * d(dT)/dt + dT = K * I^2
ayrık   :  dT[k+1] = a*dT[k] + beta*I2[k],   a = exp(-Ts/tau)
            K   = beta / (1 - a)
            tau = -Ts / ln(a)
```

`I2[k]` **bir önceki** örneğin akımıdır (sıfırıncı derece tutucu). Bu indis kritiktir:
üreteç ile kestirimci farklı indis kullanırsa 10 s örneklemede fark görünmez ama
15 dakikalık dışa aktarımda K kestirimi ters yöne gider (ölçüldü: gerçek çarpan 2,0
iken kestirim 0,47).

### 3.2 Kestirim — unutma faktörlü RLS

```
theta = [a, beta]^T          phi[k] = [dT[k], I2[k]]^T
e = dT[k+1] - phi^T * theta
g = P*phi / (lam + phi^T*P*phi)
theta <- theta + g*e
P     <- (P - g*phi^T*P) / lam
```

Kod: `panoalgo/detect.py` `KIndexEstimator`. **numpy kullanılmaz**, 2×2 matris cebri
elle açılmıştır — aynı çekirdek TA3'te `firmware/core/rls.c` olarak C'ye taşınacak ve
iki taraf aynı test vektörünü 1e-6 farkla geçmek zorunda.

**Ölçülen isabet** (PLAN.md TA2 test vektörü, K 2,0e-4 → 3,2e-4):

| Büyüklük | Gerçek | Kestirim | Hata |
|---|---|---|---|
| K (sağlıklı) | 2,000e-4 | 1,960e-4 | %2,0 |
| K (bozulmuş) | 3,200e-4 | 3,124e-4 | %2,4 |
| τ | 900 s | 826 s | %8,3 |
| **K/K₀** | **1,600** | **1,595** | **%0,31** |

Oranın hatası tekil kestirimlerden bir mertebe küçüktür: sistematik sapma pay ve
paydada birbirini götürür. Alarmı tetikleyen zaten orandır.

### 3.3 Üç sayısal koruma (hepsi ölçümle bulundu)

1. **Kalıcı uyarım.** Yük sabitse `I²` değişmez, RLS kestirimi anlamsızlaşır. Sözleşme
   `excitation_min_var_i2 = 1.0e7` mutlak eşiğini verir. Ölçüldü ki bu eşik **ölçeğe
   bağımlıdır**: nötr iletken faz akımının ~1/6'sını taşır, `var(I²)` ~1000 kat küçüktür
   (GIRIS_L1: 1,67e9 / cv 0,022 — GIRIS_N: 1,24e6 / cv 0,028). Aynı göreli yük
   değişimi, ama mutlak eşik yalnızca fazı geçiriyor. Ölçekten bağımsız ikinci ölçüt
   (değişim katsayısı) eklendi; sözleşmeye eklenmesi [önerildi](../contracts/changes/2026-09-14-eksik-esikler.md).
2. **Unutma faktörü örnekleme periyoduna bağlıdır.** `lam = 0.998` tek başına anlamsızdır;
   etkin hafıza `T = -Ts/ln(lam)` saniyedir. 10 s'de 1,4 saat, 15 dk'da 125 saat eder.
   `lambda_for_period()` bunu taşır, ama **örnek sayısı** için de alt sınır koyar (100):
   6 örneklik hafızayla iki parametreli kestirim yapılamaz — ölçüldü ki P kovaryans
   matrisi pozitif tanımlılığını kaybediyor ve K/K₀ 12.000'e fırlıyor.
3. **K = β/(1−a) patlaması.** `a` 1'e yaklaştıkça K sonsuza gider. τ fiziksel aralığa
   (1 dk – 6 saat) kırpılır; ayrıca kovaryans köşegeni negatife düşerse P başlangıç
   değerine döndürülür. Gömülü sürümde de aynı koruma gerekir.

### 3.4 Taban (K₀) ve eşikler

`K₀` = devreye almadan sonraki **7 günlük medyan** (`baseline_learning_days`). Medyan
seçilir, ortalama değil: taban penceresindeki tek bir sıçrama ortalamayı bozar.

| Eşik | Değer | Kod |
|---|---|---|
| `k_ratio_warn` | 1,3 | `ALM-K-WARN` (P3) |
| `k_ratio_alarm` | 1,6 | `ALM-K-ALM` (P2) |

Taban donmadan `k_ratio` 1,0 döner — devreye alma gününde sahte alarm yağmuru olmaz.

## 4. L1 — Sınıra kalan süre (ttl)

```
K(t)         ~ K_şimdi + Kdot * t          (Kdot EWMA ile)
dT_tahmin(t) = K(t) * I2_profil(t)
ttl          = dT_tahmin(t) >= 70 K olan İLK t
```

Gelecek yük **sabit varsayılmaz**; 168 kutulu saat-of-hafta profilinden okunur. `ttl_h`
şu üç durumda `null` döner (uydurmak yerine susmak):

- yük profili yoksa,
- kalıcı uyarım yoksa (K güncellenmiyor, eğim anlamsız),
- eğim **sürekli pozitif** değilse — bu koşul sözleşmeden gelir (`ALM-K-ALM` ek koşulu
  "eğim sürekli pozitif"). Tek başına EWMA yeterli değildir: kararlı bir K'de bile
  gürültü eğimi kıl payı pozitif bırakıp sahte bir aciliyet üretebilir.

Eşik: `ttl_warn_days = 14` → `ALM-TTL-14D` (P3). **Gün değil saat** karşılaştırılır
(14 × 24 = 336 h); çevrim unutulursa 14 gün yerine 14 saat kala alarm verilir.

## 5. L1 — Faz karşılaştırması

```
r_i   = dT_i / I_i^2
sapma = r_i / medyan(r_grup)
```

Ham `dT` farkına bakmak yanlıştır: `dT = K*I²` olduğu için iki kat akım taşıyan faz
**dört kat** ısınır, ama K'si aynıdır. Gruplama çıkış bazlıdır (GIRIS, DSYA1…DSYA7);
nötr dışarıdadır. Fider akımı ana akımın sabit bir kesri olduğundan grup içi oranlamada
o kesir sadeleşir.

L0 tarafındaki ham fark kuralı (`ALM-THR-PHASE-DIF`, 15 K) sözleşmede **"benzer yükte"**
niteliğiyle yazılıdır. Bu niteleme atlanırsa faz dengesizliği tek başına alarm üretir:
%14 akım farkı %31 sıcaklık farkı demektir ve 45 K'lik bir noktada 14 K eder. Ölçüldü:
niteleme olmadan sağlıklı pano örneklerinin **%33'ünde** yanlış alarm çıkıyordu.

## 6. L1 — Yoğuşma

Magnus çiy noktası (rapor §15.1):

```
gamma = ln(RH/100) + b*T/(c+T)      b = 17,62   c = 243,12 °C
Td    = c*gamma / (b - gamma)
marj  = T_yüzey - Td
```

| T (°C) | BN (%) | Td (°C) |
|---|---|---|
| 25 | 60 | 16,7 |
| 20 | 85 | 17,4 |
| 15 | 95 | 14,2 |
| 35 | 50 | 23,0 |

Eşikler: marj < 3,0 K → `ALM-DEW-WARN`, marj < 1,0 K → `ALM-DEW-ALM`. Referans yüzey
**soğuk metaldir** (dış ortam sıcaklığı), pano içi havası değil — yoğuşma soğuk yüzeyde olur.

## 7. L-1 — Veri kalitesi

Amaç bir arıza bulmak değil, arızaya benzeyen **bozuk ölçümü** ayıklamaktır. Verilen
"İstenen Veriler.xlsx"te 15 dakikada 438 A'lık sıçramalar var (rapor §3.4a); bunlar
L0/L1'e girmeden burada işaretlenir. Öncelik `SYS`: izleme sistemi arızası, pano arızası değil.

| Kural | Eşik | Kod / bit |
|---|---|---|
| Donmuş değer | `dq_frozen_samples` = 30 örnek | `ALM-DQ-FROZEN` / 14 |
| Fiziksel olmayan hız | `dq_max_rate_k_per_min` = 10,0 K/dk | `ALM-DQ-JUMP` / 15 |
| Ortam altı | **ölü bant** (aşağıda) | `ALM-DQ-BELOW-AMBIENT` / 16 |
| Düğüm sessiz | `nodes_ok < nodes_total` | `ALM-NODE-LOST` / 17 |

**Ölü bant sözleşmede yok ve gereklidir.** Hafif yüklü noktalar (özellikle `GIRIS_N`)
fiziksel olarak ortam sıcaklığında oturur; σ ≈ 0,2 K ölçüm gürültüsüyle `dt_c` ara ara
negatife düşer. Bu gerçek sensör davranışıdır, kırpılmaz. Ölü bant olmadan sağlıklı
pano sürekli SYS alarmı üretirdi. Türetilmiş varsayılan 1,0 K (3σ üzeri);
[sözleşmeye eklenmesi önerildi](../contracts/changes/2026-09-14-eksik-esikler.md).

**Çift alarm tuzağı.** DQ kodları `alarms[]` listesine **yazılmaz**, yalnızca
`t_conn[].q` bitine yazılır. Merkez `q` bitlerini okuyup alarmı doğru noktaya bağlar
(`backend/app/risk.py:184-192`); aynı kod bir de `detect()` dönüşünden gelseydi merkez
onu `point=None` ile ikinci kez kaydeder ve **aynı arıza için iki alarm, iki SMS** çıkardı.

## 8. L3 — Hipotez füzyonu

```
S_h  = (h'nin kanıtlarından kaçı var / h'nin toplam kanıt sayısı) * severity_w[h]
skor = round(100 * max_h S_h) + artış_bonusu        (0-100'e kırpılır)
mod  = argmax_h S_h
```

Kanıt **ikilidir** (var/yok). Rapor "normalize kanıt skoru" der ama tanımını vermez;
eşikli kodlar için dereceli bir skor türetilebilirdi, eşiksiz kodlarda (ark tripi,
koruma sağlığı) karşılığı yoktur ve iki tür kanıt karışık ölçekte toplanırdı. İkili
kanıt jüriye tek cümlede açıklanabilir: *"hipotezin beş kanıtından dördü var,
ciddiyeti 1,0, risk 80."*

Kanıt sayısının hipoteze göre değişmesi bilinçlidir: `HYP-ARC`'ın tek kanıtı vardır ve
ciddiyeti 1,0'dır — tek trip anında risk 100 olur. `HYP-LOOSE-CONN`'un beş kanıtı vardır,
risk kanıt biriktikçe yükselir.

**Ayırt edici.** Sözleşme `HYP-OVERLOAD` için `discriminator: "tüm fazlarda uniform dT
artışı VE K normal"` der. Yani aşırı akım tek başına "aşırı yük" teşhisi koydurmaz;
K tırmanıyorsa bu gerçek bir bozulmadır ve "yük transferi" önerisi yanlış olurdu.

**Risk skoru alarmın yerini tutmaz:** SMS/arama kararı alarm önceliğinden (P1/P2/P3)
çıkar. Skor filo sıralaması ve triyaj içindir.

## 9. Doğrulama yöntemi

10 etiketli senaryo (`data/fixtures/`, seed'li) üzerinde ölçülür:

- **recall** — etiketin `expect` listesindeki kodlardan kaçı pencerede gerçekten çıktı,
- **precision** — `not_expect` listesindeki yasaklı kodlardan biri çıktı mı,
- **öne alma süresi** — `l0_breach_at` (70 K anı) eksi ilk L1 tespiti,
- **yanlış alarm** — etiket penceresi dışında çıkan her alarm, 100 pano × gün ölçeğinde.

Ölçüm betiği etiketi değil **verideki gerçek alarm sütununu** okur; ikisi aynı yerden
gelseydi ölçüm anlamsız olurdu. Yeniden üretim:

```bash
python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures
python scripts/validate.py --out docs/12-dogrulama-sonuclari.md
```

Sonuçlar: [12-dogrulama-sonuclari.md](12-dogrulama-sonuclari.md).

## 10. Bilinen sınırlar (dürüstlük bölümü)

- **L2 katmanı henüz kod üretmiyor.** Rapor §6.5'te saat-of-hafta robust z, EWMA/CUSUM
  ve filo karşılaştırması tanımlı; `contracts/alarm-codes.yaml`'da `layer: L2` etiketli
  **hiçbir alarm kodu yok**. Bu, rapor ile donmuş sözleşme arasındaki bir boşluktur.
- **Üç kodun eşiği sözleşmede yok** (`ALM-DQ-BELOW-AMBIENT`, `ALM-NEUTRAL-THD`,
  `ALM-PD-TREND`) ve türetilmiş varsayılanlarla çalışıyor. Öneri dosyası açıldı, üç onay
  bekliyor. Kabul edilene kadar kenar ile merkezin aynı kuralı farklı sayıyla
  uygulama riski vardır.
- **Aşırı yükte öne alma yoktur** (ölçülen: 1,2 saat). Beklenen davranış: sebep bozulma
  değil yüktür, fizik katmanının bir üstünlüğü yoktur ve olmamalıdır.
- **PD yalnızca OG içindir.** AG panoda `pd` bloğu şema gereği `null`; rapor §3.7'ye göre
  400 V'ta Paschen minimumunun (~327 V) altında kalındığı için PD beklenmez.
