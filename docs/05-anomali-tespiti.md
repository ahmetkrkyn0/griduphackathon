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

**Tabanın kendisi geçerli mi? (F-32)** `k_ratio`'nun tüm anlamı K₀'a bağlıdır, ama K₀ tek bir
sayıdır ve donduğu anda "bu sayı nasıl oluştu" bilgisi kayboluyordu. Artık donma anında bir
kanıt kaydı tutuluyor (`detect.py` → `BaselineEvidence`) ve tabana **üç ayrı kanıtla** bakılıyor:

| Kanıt | Ne sorar | Düşükse ne demek |
|---|---|---|
| **Uyarım oranı** | Öğrenme penceresinde kaç örnek kalıcı uyarım koşulunu sağladı | RLS güncellenmedi; K₀ fiziksel bağlantıyı değil başlangıç **önselini** kodluyor |
| **Pencere kararlılığı** | Pencerenin ikinci yarısı birinciden kalıcı olarak sapıyor mu (CUSUM) | Makine kararlı değildi; **bozulma taban öğrenilirken başladı** |
| **Akran konumu** | K₀ aynı adlı noktanın filo medyanından yukarı aykırı mı | Devreye alma anında **zaten gevşek** bir bağlantının tabanı olabilir |

Üçüncüsü, `k_ratio`'nun tek başına **göremediği** tek durumdur: devreye alma gününde zaten
bozuk bir bağlantıda K yüksek, K₀ aynı oranda yüksek ve `k_ratio` 1,0 kalır — nokta ömrü
boyunca sağlıklı görünür. Onu ancak akranları ele verir (`fleet.py`, `GET /fleet/peers`).

Üçünden biri düşükse **yeniden baz alma önerilir**; asla otomatik uygulanmaz (§10, `docs/07b` Y11).

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

Bu tahminin geri testi — α-λ doğruluğu, prognostic horizon, göreli doğruluk ve
yakınsama — [12-dogrulama-sonuclari.md](12-dogrulama-sonuclari.md) §4'tedir; ölçüt
tanımları `libs/panoalgo/panoalgo/prognostics.py` içindedir. **Ölçülen sonuç
olumsuzdur**, §10'daki iki kayda bakın.

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
| Ortam altı | `dq_below_ambient_deadband_k` = 1,0 K (ölü bant, aşağıda) | `ALM-DQ-BELOW-AMBIENT` / 16 |
| Düğüm sessiz | `nodes_ok < nodes_total` | `ALM-NODE-LOST` / 17 |

**Ölü bant neden var.** Hafif yüklü noktalar (özellikle `GIRIS_N`) fiziksel olarak ortam
sıcaklığında oturur; σ ≈ 0,2 K ölçüm gürültüsüyle `dt_c` ara ara negatife düşer. Bu gerçek
sensör davranışıdır, kırpılmaz. Ölü bant olmadan sağlıklı pano sürekli SYS alarmı üretirdi.
Değer 1,0 K'dır (3σ üzeri, yuvarlak) ve **18 Eylül'de sözleşmeye taşındı**
(`alarm-codes.yaml` v2, [gerekçe](../contracts/changes/2026-09-14-eksik-esikler.md)) —
ama **türetilmiştir, ölçülmemiştir** ve sözleşmedeki yorumunda böyle yazar.

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

- **L2 katmanı kısmen kod üretiyor (18 Eylül, F-32).** Rapor §6.5'te saat-of-hafta robust z,
  EWMA/CUSUM ve filo karşılaştırması tanımlı. Üçünden **ikisi** artık kodda:
  **filo akran karşılaştırması** (`libs/panoalgo/panoalgo/fleet.py`, MAD tabanlı modifiye z)
  ve **CUSUM değişim noktası** (`onset.py`, bozulmanın başlangıç anı). **Saat-of-hafta robust z
  hâlâ yok.** `contracts/alarm-codes.yaml`'da `layer: L2` etiketli **hiçbir alarm kodu yok** ve
  F-32 bilerek bir tane açmadı: her kodun bir `bit` alanı var, yani yeni kod Modbus bit
  tahsisini ve beş üretecin çıktısını birden tetikler. L2'nin çıktısı bu yüzden bir **alarm
  değil öneri**: `GET /api/v1/fleet/peers` tabanı şüpheli noktaları operatör onayına sunar.
  Gerekçe: `contracts/changes/2026-09-18-l2-filo-akran.md`.
- **Filo karşılaştırmasının sentetik veride ölçülen sınırı (GK10).** `generator.py:342`
  sağlıklı K₀'ı **sınırlı düzgün dağılımdan** çekiyor (`K_SPREAD = 0.15`) ve düzgün dağılımın
  **kuyruğu yoktur**: sağlıklı bir pano yapısal olarak aykırı **çıkamaz**. Ölçüldü (500 pano,
  seed 20260918): en büyük |z| = **1,534**, aykırılık eşiği **3,5** — sağlıklı pano eşiğin
  yarısına bile ulaşmıyor. Yani 1,6'nın üstündeki **her** eşik bu veride kusursuz ayrım verir;
  bu, yöntemin değil **üretecin** özelliğidir. Buradan çıkan hiçbir ayrım oranı saha başarımı
  olarak sunulamaz. Kilitleyen test:
  `libs/panoalgo/tests/test_fleet.py::test_sentetik_filoda_saglikli_pano_asla_aykiri_cikamaz`.
- **Taban geçerliliği artık ölçülüyor, ama yeniden baz alma UYGULANMIYOR.** `freeze_baseline()`
  donma anında bir kanıt kaydı tutuyor (`BaselineEvidence`: kaç örnek, kaçı uyarılmış, dağılım
  ne kadar dar) ve öğrenme penceresinin kendi içinde kararlı olup olmadığı CUSUM ile sınanıyor.
  Üç kanıttan biri düşükse **yeniden baz alma önerilir** — ama **hiçbir zaman otomatik
  uygulanmaz**: bozulmakta olan bir noktada tabanı güncellemek `k_ratio`'yu 1,0'a geri çeker ve
  gerçek bozulmayı görünmez kılar. Bu yeni hata türü `docs/07b-fmea-yazilim-sistem.md` **Y11**
  satırında.
- **İki kodun eşiği 18 Eylül'de sözleşmeye taşındı** (`alarm-codes.yaml` v2):
  `ALM-DQ-BELOW-AMBIENT` → `dq_below_ambient_deadband_k`, `ALM-NEUTRAL-THD` →
  `neutral_current_ratio_warn` **ve** `neutral_thd_warn_pct` (iki koşul birlikte).
  Kenar ile merkezin aynı kuralı farklı sayıyla uygulama riski böylece kalktı.
  **Ama bu sayılar hâlâ türetilmiştir, ölçülmemiştir** — sözleşmedeki yorumlarında
  böyle yazıyor; yalnızca `excitation_min_cv_i2 = 0.02` ölçülmüş bir taramadan gelir.
  `ALM-PD-TREND` **bilerek eşiksiz bırakıldı**: AG panoda `pd` bloğu şema gereği `null`,
  yani değerlendirilecek veri yok; eşik yerine `scope:` notu düşüldü. PD donanımı
  kapsama girerse eşik ayrı bir `contracts/changes/` dosyasıyla tanımlanır.
  Gerekçe ve ölçümler: `contracts/changes/2026-09-14-eksik-esikler.md`.
- **Aşırı yükte öne alma yoktur** (ölçülen: 1,2 saat). Beklenen davranış: sebep bozulma
  değil yüktür, fizik katmanının bir üstünlüğü yoktur ve olmamalıdır.
- **`ttl_h` henüz güvenilir bir kalan ömür kestirimi değildir.** Geri testi yapıldı
  ([12-dogrulama-sonuclari.md](12-dogrulama-sonuclari.md) §4): S1'deki 790 tahminin
  yalnızca **%5,2'si** ±%20 konisinin içinde; **prognostic horizon yok** — tahmin hiçbir
  noktadan sonra konide kalmıyor; ihlale 48 saatten az kala koni içinde kalma oranı
  **%0**; ortalama göreli doğruluk **−5,12**. Sonuç **tek yörüngeden** (n = 1) gelir, güven aralığı yoktur.
- **Manşetteki 209 saatlik öne alma, bu güvenilmez tahminin KENDİSİNDEN geliyor —
  19 Eylül'de ölçüldü ve bu belgenin önceki hâli bunun tersini yazıyordu.** Öne alma
  süresi "ilk L1 kodu" ile tanımlıdır ve `ALM-TTL-14D` de `contracts/alarm-codes.yaml`'da
  **L1**'dir. `S1_loose_conn`'da ilk çıkan L1 kodu `ALM-TTL-14D`'dir (13 Tem 22:15);
  K indeksi eşiği (`ALM-K-WARN`) **41 saat sonra** uyarır (15 Tem 10:45). Yani 209 saat,
  geri testi aynı dosyada yapılıp **zayıf bulunan** bir tahminden gelir; yalnızca K/K₀
  eşiğine dayanan öne alma daha kısadır (ölçülen ~172 saat). `S2_overload`'daki 1,2 saati
  tetikleyen kod ise `ALM-DEW-*`'dır, yani ısıl tespit değil çiy kuralı.
  [docs/12](12-dogrulama-sonuclari.md) §2 artık **tetikleyen kodu ayrı bir sütunda**
  basar, böylece sayı bir daha yanlış okunamaz. Eşik tanımı **değiştirilmedi**: değiştirmek
  manşet sayıyı sessizce düşürürdü ve bu kararın ayrı verilmesi gerekir.
- **Prognoz yanlış-alarmı (S8, sensör arızası) — 18 Eylül'de kısmen kapandı (F-31).**
  Sınır hiç aşılmadığı hâlde **183 tahmin** üretiliyor ve bunların **86'sı** `ALM-TTL-14D`
  (P3) alarmına dönüyor (`docs/12` §4.3). Tahminlerin kaynağı `DSYA4_L3`, yani S8'in
  **sürüklenen** sensörü.
  **Önce üretecin kendisi düzeldi.** `set_sensor_fault` aynı arızayı her çağrıda yeniden
  kuruyor ve yaşını **sıfırlıyordu**; senaryo yürütücüsü enjeksiyonu her adımda çağırdığı
  için "sürüklenme" 112 saatlik pencere boyunca **0,5 K'da çakılı** kalıyordu. Yani depo
  "sensör sürüklenmesi üretiyoruz" diyordu ama fiilen **üretmiyordu**. Ayrıca hız 2 K/saat
  ile fiziksel değildi (112 saatte 224 K); ölçülerek **0,1 K/saat**e indirildi — bu değer
  termal alarmı tetiklemez, `ALM-K-ALM` tetiklemez, ama K/K₀'ı 1,49'a şişirir.
  **Sonra sürüklenme tespit edilir oldu.** Yeni `ALM-DQ-DRIFT` (bit 22, `layer: L-1`, SYS)
  kuralı bu noktayı artık **işaretliyor**: fixture'da 239 örnekte, enjeksiyondan **26,25
  saat** sonra. Ayraç fiziktir — `dT = a·I² + b`'de gerçek bağlantı bozulması `a`'yı
  büyütür, sensör kayması yükten bağımsız `b`'yi. Ölçüldü (seed 42, 10 senaryo): gerçek
  gevşek bağlantı (S1) ve sağlıklı taban (S0) dahil diğer dokuz senaryoda **sıfır** yanlış
  pozitif. Gerekçe: `contracts/changes/2026-09-18-dugum-kutugu-ve-sapma.md`.
  **Kalan:** `ttl_h` üretimi hâlâ kalite bitlerinden **bağımsız** çalışıyor (`edge.py`
  kestirimi `q` hesabından önce yapar), yani nokta "kalibrasyon şüpheli" işaretlenmiş olsa
  bile tahmin üretilmeye devam eder. Bu bir tespit değil **tahmin** yanlış-alarmıdır ve
  docs/12 §3'teki yanlış alarm sayacı onu görmez. Saklanmıyor, burada duruyor.
- **Dedektörün dört varsayımı 19 Eylül'de sınandı; biri kırıldı, üçü dayandı (S10–S13).**
  `detect.py` şunları varsayar: (a) nokta tek başınadır (regresör `[dT, I²]`), (b) τ
  sabittir, (c) sistem birinci mertebedir, (d) ölçüm doğrusaldır. Üreteç S0–S9'da
  **aynı** denklemi çözdüğü için "duyarlılık 1,00" bu varsayımları hiç sınamıyordu.
  `ModelMismatch` dördünü de bozabiliyor (varsayılan kapalı, dedektöre hiçbir şey
  eklenmedi) ve dört senaryo bunları tek tek açıyor. **Ölçülen** ([docs/12](12-dogrulama-sonuclari.md)
  §1.1, [docs/14](14-veri-ureteci.md) §9):
  - **(d) kırıldı.** Ölçüm zinciri doğrusalsızlığında terminal gerçekte **78,90 K**'da —
    eşleşen ikizle ondalık basamağına kadar aynı — ama ölçüm **48,48 K** gösteriyor.
    Sabit 70 K eşiği **tamamen körleşiyor**, recall **0,50**'ye iniyor. Oran tabanlı K
    tespiti ayakta kalıyor (`k_ratio` 3,01 > 1,6). Bu, §1'deki "sabit eşik yetmiyor"
    savının deneysel kanıtıdır — ama aynı zamanda **kendi L0 katmanımızın da kör
    olabileceğini** gösterir.
  - **(a), (b), (c) dayandı, ve nedeni yapısaldır:** alarm kuralları K'yı değil
    **K/K₀ oranını** okur; taban K₀ aynı uyumsuz fizikle öğrenildiği için durağan bir
    yanlılık payda ile sadeleşir (`k_ratio = g·K / g·K₀ = K/K₀`). Bu bir **güçtür** ve
    seçilerek değil ölçülerek bulunmuştur.
  - **Bedel başka yerde çıktı.** İkinci ısıl kutupta yayımlanan τ **9,5 kat** sapıyor
    (689 s → 6.576 s) ve `ALM-DQ-DRIFT` **gerçekten arızalı** noktayı "kalibrasyon
    şüpheli" diye etiketliyor — operatörün gerçek arızayı alet hatası sanmasına yol
    açabilecek bir yanlış teşhis. Kuplajda ise `k_ratio` eşiğini aşan nokta sayısı
    1'den 2'ye çıkıyor: teşhis "hangi pano" düzeyinde doğru, **"hangi klemens"
    düzeyinde yanlış**.
  - **Kapatılmamış:** dört fizik **tek tek** açılıyor; gerçek panoda hepsi aynı andadır
    ve birleşik etkileri ölçülmedi. Katsayılar da sentetiktir, saha ölçümü yoktur
    (gerekecek ölçümler `docs/14` §9.3'te). Gerekçe:
    `contracts/changes/2026-09-19-model-uyumsuzlugu-senaryolari.md`.
- **PD yalnızca OG içindir.** AG panoda `pd` bloğu şema gereği `null`. Gerekçesi sık
  tekrarlanan "400 V, Paschen minimumunun (~327 V) altındadır" kısayolu **değildir** — o
  kısayol eksiktir: 400 V sistemde faz-faz tepe gerilimi √2 × 400 ≈ 566 V'tur, yani 327 V'un
  üstündedir. Doğru gerekçe geometriktir (Paschen eğrisi gerilimi değil basınç × boşluk
  mesafesini sınırlar) ve bir **literatür kabulüdür, bizim ölçümümüz değildir**: AG panoda PD
  ölçümü yapılmadı. Tam gerekçe, verilen HFCT veri sayfalarının kendi sayılarıyla birlikte
  [13-donanim-tasarimi.md](13-donanim-tasarimi.md) §7.1'dedir.

## 11. Çiy eşiği taraması — ölçülmüş savunma

[12-dogrulama-sonuclari.md](12-dogrulama-sonuclari.md) §3'te ölçülen tek gerçek zayıflık
budur: sağlıklı panoda (`S0_normal`) **71,4 yanlış alarm/100 pano/gün** ve tamamı
`ALM-DEW-*`. Sözleşme sınırı 150 olduğu için "geçiyor", ama "neden 3,0 / 1,0 K" sorusunun
ölçülmüş bir cevabı yoktu ([KALAN-EKSIKLER.md](../KALAN-EKSIKLER.md) D7). Aşağıdaki
tabloların hepsi şu komutla yeniden üretilir; testleri
`libs/panoalgo/tests/test_threshold_sweep.py` içindedir:

```bash
python scripts/threshold_sweep.py --verify --seasons
```

### 11.1 Tarama neyi yeniden koşturuyor

`scripts/validate.py` tespiti yeniden koşturmaz, fixture'ın hazır `alarms` sütununu okur.
Çiy kararı ise `limits._environment()` içinde **tek bir alan** üzerinde **tek bir kesin
küçüktür** karşılaştırmasıdır: `env.td_margin_k < eşik`. Eşik ne fiziğe, ne üretece, ne de
`td_margin_k` değerine girer — yalnızca karşılaştırmaya girer. Bu yüzden her ızgara
noktasında fixture yeniden üretilmedi; kararın kendisi `td_margin_k` sütunu üzerinde
yeniden koşturuldu. Kestirmenin bedava olmadığı iki şekilde kanıtlanır:

- `--verify`: sözleşme eşikleriyle hesaplanan kodlar fixture'ın hazır `alarms` sütunuyla
  **672 satırın 672'sinde** aynı (0 uyuşmazlık).
- `--rerun`: her ızgara noktası için `contracts/` dizininin **geçici bir kopyası** o eşikle
  yazılır ve senaryo üreteç + kenar boru hattından baştan koşturulur. Sonuç hızlı yolla
  **birebir aynı**. Donmuş sözleşme dosyasına yazılmaz (testle kilitli).

**Ölçülen maliyet** (bu makine, 168 h / 672 örnek, 11 noktalı ızgara): hızlı yol
**0,024 s**, tam yeniden koşturma **30,9 s** (nokta başına ~2,8 s). Kestirme yol ~1300 kat
ucuz ve aynı sayıyı veriyor.

### 11.2 Tek eşik taraması (`S0_normal`, 168 h, 672 örnek)

| Eşik (K) | Olay | Olay/100 pano/gün | Ayakta kalma | En uzun kesintisiz | Bayat? |
|---:|---:|---:|---:|---:|---|
| 0,0 | 8 | 114,3 | %65,6 | 17,0 h | hayır |
| 0,5 | 8 | 114,3 | %78,1 | 20,8 h | hayır |
| **1,0 (sözleşme: alarm)** | 4 | 57,1 | %94,5 | 110,0 h | evet |
| 1,5 | 1 | 14,3 | %100,0 | 168,0 h | evet |
| 2,0 | 1 | 14,3 | %100,0 | 168,0 h | evet |
| 2,5 | 1 | 14,3 | %100,0 | 168,0 h | evet |
| **3,0 (sözleşme: uyarı)** | 1 | 14,3 | %100,0 | 168,0 h | evet |
| 3,5 – 6,0 | 1 | 14,3 | %100,0 | 168,0 h | evet |

"Bayat" = EEMUA 191'in tanımı: 24 saatten uzun süre ayakta duran alarm. **Olay sayısı tek
başına yanıltıcıdır** — ayakta duran tek bir alarmı ucuz gösterir, oysa operatör için en
pahalı alarm tam odur.

### 11.3 Eşik çifti taraması

| Uyarı (K) | Alarm (K) | Olay/100 pano/gün | Uyarı ayakta | Alarm ayakta | Yoğuşma yakalandı mı |
|---:|---:|---:|---:|---:|---|
| 6,0 | 3,0 | 28,6 | %100,0 | %100,0 | evet (0,00 h) |
| 5,0 | 2,0 | 28,6 | %100,0 | %100,0 | evet (0,00 h) |
| 4,0 | 2,0 | 28,6 | %100,0 | %100,0 | evet (0,00 h) |
| **3,0 / 1,0 (sözleşme)** | | **71,4** | %100,0 | %94,5 | evet (0,00 h) |
| 2,0 | 1,0 | 71,4 | %100,0 | %94,5 | evet (0,00 h) |
| 2,0 | 0,5 | 128,6 | %100,0 | %78,1 | evet (0,00 h) |
| 1,5 | 0,5 | 128,6 | %100,0 | %78,1 | evet (0,00 h) |
| 1,0 | 0,0 | **171,4** | %94,5 | %65,6 | evet (0,00 h) |
| 0,5 | 0,0 | **228,6** | %78,1 | %65,6 | evet (0,00 h) |

### 11.4 Aynı senaryo, üç mevsim (eşik sabit)

| Mevsim | En düşük marj | Medyan marj | En yüksek marj | Uyarı ayakta | Alarm ayakta | Olay/100 pano/gün |
|---|---:|---:|---:|---:|---:|---:|
| kış | −1,72 K | −1,70 K | −1,69 K | %100,0 | %100,0 | 28,6 |
| geçiş | −1,69 K | −0,76 K | 1,27 K | %100,0 | %94,5 | **71,4** |
| yaz | 7,48 K | 10,17 K | 13,29 K | %0,0 | %0,0 | **0,0** |

### 11.5 Sonuç: eşik veriyle savunuluyor, değiştirilmiyor

1. **Eşiği kısmak yükü azaltmıyor, artırıyor.** 1,0/0,0 çifti 171,4 olay/100 pano/gün
   üretiyor ve sözleşmenin kabul edilebilir günlük bütçesini (150) **aşıyor**; 0,5/0,0
   çifti 228,6. Sebep: dar eşik, ayakta duran tek bir alarmı kesik kesik (chattering)
   bir alarm dizisine çeviriyor.
2. **Eşiği gevşetmek sayıyı düşürüyor ama alarmı işlevsiz bırakıyor.** 2,0 K ve üzerinde
   alarm haftanın %100'ünde ayakta; hiç temizlenmeyen bir alarm bilgi taşımaz. Olay
   metriği bunu "daha iyi" (28,6) gösterir — EEMUA 191'in bayat alarm patolojisi tam
   budur.
3. **Sözleşme çifti ölçülen etkin sınırın üzerinde.** 150 bütçesinin altında kalan ve
   alarm kodu hâlâ **temizlenen** (ayakta kalma %94,5, 4 ayrı olay) tek aday grubu
   3,0/1,0 ve 2,0/1,0'dır; ikisi de 71,4 üretir. Aradaki tek fark uyarı eşiğidir ve
   ölçülebilir hiçbir şeyi değiştirmez (her ikisinde de uyarı tek ve sürekli). Yani
   **sözleşmedeki sayıyı değiştirmenin ölçülmüş bir faydası yok**.
4. **Tespit hiçbir adayda kaybolmuyor** — yani "eşiği kısarsak yoğuşmayı kaçırırız"
   savunması bu veride yapılamaz; savunma yalnızca operatör yükü üzerinden yapılır.

**Sözleşme değişikliği önerilmedi.** `dew_margin_warn_k = 3,0` ve
`dew_margin_alarm_k = 1,0` olduğu gibi kalıyor.

### 11.6 Eşiğin çözmediği şey (dürüstlük)

- **Asıl sürücü eşik değil hava.** Geçiş mevsiminde sağlıklı panonun çiy marjı örneklerin
  **%65,6'sında negatif**; yani referans yüzey gerçekten çiy noktasının altında. Bu
  alarmlar fiziksel olarak **doğru**. Yazın aynı senaryoda çiy alarmı **hiç çıkmıyor**
  (0,0 olay). 71,4 sayısı bir algoritma hatası değil, bir mevsim özelliğidir. Canlı
  demoda sağlıklı panodan çiy alarmı çıkmasını istemiyorsak yapılacak şey eşiği
  oynatmak değil, yaz senaryosunu oynatmaktır.
- **Özellik doyuyor.** Bağıl nem üreteçte %98'de sınırlı ve pano alt bölme havası referans
  yüzeyden 2,0 K sıcak; nem doyunca marj ≈ **−1,70 K** tabanına çakılıyor. Sağlıklı
  panonun en düşük marjı (−1,69 K) ile yoğuşma enjekte edilmiş `S3_condense` senaryosunun
  marjı (−1,72 … −1,69 K) **aynı bölgede**. İki durum bu özellik üzerinden **hiçbir
  eşikle** ayrılamaz; ayrım ancak gerçek yüzey sıcaklığı ölçülürse mümkün olur — bu bir
  donanım/sözleşme konusudur, eşik konusu değil.
- **`ALM-DEW-WARN` sağlıklı panoda bayat alarmdır.** 3,0 K'de uyarı 168 saat boyunca
  kesintisiz ayakta. Sözleşmedeki otomatik aksiyon (`heater_relay_on`) zaten tetikleniyor,
  ama ısıtıcının marjı toparlaması modellenmediği için "aksiyon işe yaradı mı" ölçülemiyor.
  Ölçemediğimiz için öneri de yazmadık.
- **docs/12'nin yanlış alarm tanımı bu kodlar için cömerttir.** §3, etiket penceresi
  dışındaki her alarmı yanlış sayar; `S0_normal`'ın hiç etiketi yoktur, dolayısıyla
  fiziksel olarak doğru olan çevresel alarmlar da "yanlış" hanesine yazılır. Tanımı
  senaryo katalogunda düzeltmek (`scenarios.py`) bu kulvarın dışında bırakıldı.
