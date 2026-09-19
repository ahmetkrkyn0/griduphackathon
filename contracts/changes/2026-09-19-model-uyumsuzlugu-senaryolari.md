# 19 Eylül 2026 — Model-uyumsuzluğu senaryoları (S10–S13) ve `unmodelled_physics`

**Dosya:** `contracts/scenario-labels.schema.json`
**Öneren:** Kişi A (Tuna)
**Durum:** **ÖNERİ — onay bekliyor**
**Sürüm etkisi:** şemada `version` alanı yok; `$id` `…-v1` olarak kalır (geriye uyumlu ekleme)

**Ne değişiyor:**

1. `scenario_id` enum'una dört kimlik: `S10_coupling`, `S11_load_tau`, `S12_two_pole`,
   `S13_sensor_nonlin`.
2. Kök nesneye tek **opsiyonel** alan: `unmodelled_physics` (dize dizisi, `minItems: 1`,
   kapalı enum).

**Etkilenen kulvarlar:** A (üreteç + doğrulama). B tarafında fiilî etki yok —
`loadtest/fleet.py` bu şemayı kullanmıyor.
**Geri uyumlu mu:** **evet.** Yalnızca ekleme. Mevcut on etiket dosyası ve on CSV
**bayt bayt** değişmeden kalır (aşağıda ölçüldü).

**Onaylar:** [ ] A  [ ] B  [ ] C

---

## Neden

`docs/12` §1 bugün şunu yazıyor: *beklenen alarmı olan sekiz senaryonun sekizinde
duyarlılık 1,00.* Bu sayı doğru ama **eksik okunuyor**, çünkü üreteç ile dedektör
**aynı** ayrık denklemi çözüyor:

| | Denklem | Dosya |
|---|---|---|
| Üreteç | `dT[k+1] = a·dT[k] + (1−a)·K·I²[k]`, `a = exp(−Ts/τ)` | `generator.py` `_advance_points` |
| Dedektör | `dT[k+1] = a·dT[k] + β·I²[k]`, `K = β/(1−a)` | `detect.py` modül başlığı |

Arıza da `spec.k0 · _k_multiplier[...]` ile **doğrudan kestirilen parametreye**
enjekte ediliyor. Yani ölçülen şeyin bir bölümü *"kestirici kendi ileri modelini ters
çevirebiliyor"*dur. Sahadaki asıl zorluklar — komşu terminal kuplajı, yüke bağlı zaman
sabiti, ikinci ısıl kutup, ölçüm zinciri doğrusalsızlığı — **hiç sınanmıyordu**;
üreteçte bunları enjekte edecek bir kanca da yoktu (`grep coupling|tau2|second_order`
→ sıfır eşleşme).

Bu öneri o boşluğu kapatır: üretece, **dedektörün varsaymadığı** dört fizik eklenir
(hepsi varsayılan olarak kapalı), bunları tek tek açan dört senaryo tanımlanır ve
`scripts/validate.py` tabloyu `eslesen` / `uyumsuz` diye iki bloğa ayırır.

**Dedektör değiştirilmiyor.** Amaç onu güçlendirmek değil, **sınırını ölçmektir.**

## 1. Neden yeni bir alan gerekiyor — ve neden `params` yetmiyor

Şemanın kökünde `additionalProperties: false` var, yani alan eklemek şema değişikliği
gerektiriyor. En cazip kestirme, bilgiyi `labels[].params` içine gizlemekti (`params`
serbest nesnedir, bugün oraya her şey yazılabilir). **Reddedildi**, üç sebeple:

1. `params` **arıza enjeksiyonunun** parametreleridir (`k_growth_pct`, `gap_h`).
   Model uyumsuzluğu bir arıza değil, **panonun ve ölçüm zincirinin kendi
   özelliğidir** — taban öğrenme penceresinde de açıktır. İkisini aynı torbaya
   koymak, "sahada zaten var olan fizik" ile "biz enjekte ettik"i karıştırır.
2. `label_type is None` olan senaryolarda (S0 gibi) `labels` **boş dizidir**, yani
   `params` hiç oluşmaz. Uyumsuz bir **sağlıklı** referans senaryosu ileride
   eklenirse bilgiyi yazacak yer kalmaz.
3. `scripts/validate.py` `scenarios.py`'den **hiçbir şey** import etmiyor ve bu
   bilinçli bir dürüstlük kuralı (modül başlığı: *"etiket yalnızca ne olması
   gerekiyordu'yu söyler"*). Ölçüm, senaryo kimliğinden çıkarım yapmamalı; bilgi
   **veriyle birlikte** gelmelidir.

## 2. `minItems: 1` — "eşleşen"in tek gösterimi alanın YOKLUĞUdur

Alan **opsiyoneldir** ve boş dizi **yazılamaz**. Sebep iki katlı:

- **Tek gösterim.** `eslesen` = alan yok. Boş dizi de serbest olsaydı aynı bilgi iki
  biçimde kodlanır, okuyan tarafın ikisini de düşünmesi gerekirdi.
- **Bayt bayt uyumluluk.** `_labels()` anahtarı **yalnızca liste doluysa** yazar.
  Böylece `data/fixtures/` altındaki on etiket dosyası hiç değişmez.

Alan `ScenarioSpec.mismatch`'ten **türetilir** (`ModelMismatch.names()`), elle
yazılmaz. "Bayrak açık ama etikette yazmıyor" durumu bu yüzden yapısal olarak
imkânsızdır — ölçümün geçerliliği tam olarak buna dayanır.

## 3. `label_type` enum'una yeni değer EKLENMEDİ

Dördü de `loose_connection` kullanır ve bu doğrudur: **enjekte edilen arıza gerçekten
gevşek bağlantıdır** ve S1 ile birebir aynıdır (720 h, `DSYA3_L2`, %200 K büyümesi,
yaz, yük çarpanı 0,95, tohum 1304). Değişen tek şey **panonun fiziğidir**, arıza değil.
Yeni bir `type` açmak, ölçümün kontrollü deney niteliğini bozardı.

`expect` neden gevşetilmedi: `recall = yakalanan / beklenen`. Paydayı küçültmek
uyumsuzluğu **ödüllendirirdi** ("daha az bekle, daha yüksek recall al"). Payda sabit
kalınca tablo doğru soruyu cevaplar: *aynı arıza, aynı eşikler, farklı fizik — kaçı
hâlâ yakalanıyor?*

## 4. Eklenen dört fizik ve dedektörün hangi varsayımını bozdukları

| Senaryo | Fizik | Denklem | `detect.py` varsayımı |
|---|---|---|---|
| `S10_coupling` | terminal grubu içi **difüzif** ısıl kuplaj | `+ c·(ort(dT_komşu) − dT_kendi)` | regresör `[dT, I²]` — nokta **tek başınadır** |
| `S11_load_tau` | yüke bağlı zaman sabiti | `τ = τ₀·exp(c·I/Iₙ)` | `a = exp(−Ts/τ)` **sabit** parametredir |
| `S12_two_pole` | ikinci (yavaş) ısıl kutup | hızlı bara + yavaş kabin havası | sistem **birinci mertebedir** |
| `S13_sensor_nonlin` | ölçüm zinciri doğrusalsızlığı | `dT_ölçülen = dT/(1 + g·dT)` | ölçüm **doğrusaldır** |

**Kuplaj neden toplamalı değil difüzif.** İlk taslak `Yapilacaklar.md` §2.1'in önerdiği
`steady += c·ort(dT_komşu)` biçimindeydi. Kararlı hâli `K·I²/(1−c)` yapıyor, yani
**panoyu ısıtıyor**: ölçüldü, tepe artış 79,0 K → 90,6 K (c = 0,25). O zaman duyarlılık
farkı "model yanlış" ile "pano daha sıcak" arasında ayrıştırılamazdı. Difüzif biçimde
(saf Fourier: akış sıcaklık **farkıyla** orantılıdır) grup tekdüze ısındığında terim
**sıfırdır**; değişen şey panonun ortalama sıcaklığı değil **grup içindeki yapıdır** —
yani tam olarak `detect.phase_compare`'in ölçtüğü büyüklük.

**τ(I) neden üstel.** `Yapilacaklar.md` doğrusal `τ₀·(1 + c·I/Iₙ)` yazıyor; üstel biçim
onun birinci mertebe eşidir ve `LOAD_MULTIPLIER_MAX = 2.0` aşırı yükünde de τ'yu
pozitif tutar (doğrusal biçim `c ≤ −0,5` için sıfıra düşer ve `exp(−dt/τ)` patlar).

**İkinci kutupta arıza çarpanı İKİ kutba da girer.** Yani kararlı hâl toplamı ve DC
kazancı değişmez; uyumsuzluk tamamen **dinamiktedir**. Alternatif (çarpanı yalnızca
hızlı kutba uygulamak) ölçüldü ve **reddedildi**: tepe artış 79,0 K → 64,8 K'ya düşüyor
ve 70 K sınırına hiç ulaşılmıyordu — yani ölçülen şey model uyumsuzluğu değil
**çalışma noktası kayması** olurdu.

## 5. Ölçülen — neden bu iş "duyarlılık düşer" demekten daha değerli çıktı

İlk hipotez *"uyumsuz senaryolarda duyarlılık 1,00'ın altına iner"* idi. Ölçüm bunu
**kısmen yanlışladı** ve daha güçlü bir sonuç verdi. Sebep yapısal: alarm kuralları K'yı
değil **K/K₀ oranını** okur (`k_ratio_warn` / `k_ratio_alarm`) ve taban K₀ **aynı uyumsuz
fizikle** öğrenildiği için durağan bir yanlılık payda ile birlikte **sadeleşir**:

```
k_ratio = (g·K) / (g·K₀) = K / K₀
```

Bu, yöntemin bir **gücüdür** ve `docs/05` §10'a böyle yazılmıştır. Uyumsuzluğun bedeli
duyarlılıkta değil, **başka sütunlarda** görünür. Ölçüldü (720 h, tohum 1304, yaz,
`DSYA3_L2`; eşleşen ikizle aynı koşul):

| Konfigürasyon | Tepe `k_ratio` | Tepe ölçülen dT | Yayımlanan τ | 70 K aşıldı mı | Yasaklı alarm |
|---|---:|---:|---:|---|---|
| eşleşen (taban) | 3,00 | 79,0 K | 689 s | evet (399 h) | yok |
| `coupling_k = 0,15` | 2,74 | 73,0 K | 903 s | evet (419 h) | yok |
| `tau_load_coeff = −0,8` | 3,00 | 79,3 K | 481 s | evet (399 h) | yok |
| `slow_share = 0,45` | 3,11 | 72,3 K | **6.576 s** | evet (423 h) | **`ALM-DQ-DRIFT`** |
| `sensor_gain_per_k = 0,008` | 3,01 | **48,5 K** | 2.489 s | **HAYIR** | yok |

Dört bulgu:

1. **Sabit 70 K eşiği, ölçüm zinciri doğrusalsızlığında tamamen körleşiyor.** Terminal
   gerçekte 79 K'da; ölçüm 48,5 K gösteriyor. Pano **aynı derecede sıcak** — yalanı
   söyleyen alet. `ALM-THR-TERM-ALM` ve `ALM-THR-TERM-WARN` hiç çıkmıyor. Oran tabanlı
   K tespiti ise **ayakta kalıyor** (`k_ratio` 3,01 > 1,6). Bu, "neden sabit eşik
   yetmiyor" sorusunun deneysel cevabıdır.
2. **Yayımlanan τ 9,5 kata kadar yanlış.** İkinci ısıl kutupta 689 s → 6.576 s. τ,
   `min_ttl_h` hesabına girdiği için bu doğrudan `docs/12` §4'teki kötü prognoz
   sonucunu **açıklar**.
3. **Kayma kuralı yanlış teşhis koyuyor.** `ALM-DQ-DRIFT` (L−1, "kalibrasyon şüpheli")
   ikinci kutupta tetikleniyor: kural `dT = a·I² + b`'de b'nin büyümesini sensör
   kayması sayar, ama yavaş ısıl kutup da yükten bağımsız görünen bir bileşen üretir.
   Yani **gerçek bir ısıl olay** "sensörün kendisi bozuk" diye etiketleniyor. Bu,
   `docs/07b` için yeni bir yazılım hata modudur ve dört senaryonun `not_expect`
   listesinde olduğu için tabloda **yasaklı alarm** olarak görünür.
4. **Kuplaj arızayı yanlış terminale yazdırıyor.** `coupling_k = 0,15`'te `k_ratio`
   eşiğini aşan nokta sayısı 1'den **2'ye** çıkıyor: arızasız bir komşu terminal de
   suçlanıyor. Saha ekibi yanlış uca gider — teşhis "hangi pano" düzeyinde doğru,
   "hangi klemens" düzeyinde yanlıştır.

## 6. Ölçülen — regresyon

- `python -m panoalgo.scenarios --all --seed 1304` → S0–S9'un **10 CSV'si** `cmp`
  altında bayt bayt aynı. Kapalı bayrak hiçbir ek RNG çağrısı yapmaz ve hiçbir hesap
  sırasını değiştirmez; `_advance_points` **sıfır** rastgele sayı tüketiyor,
  dolayısıyla dört RNG akışının sırası yapısal olarak korunuyor.
- Etiket dosyaları da değişmez: `unmodelled_physics` yalnızca dolu listede yazılır.
- `scripts/check_contracts.py`: tutarlı.
- Altı `--check` üretecinin çıktısı değişmedi — bu öneri **alarm kodu veya Modbus
  adresi açmıyor**.

## 7. Bilinen sınır (GK10)

Dört fizik de **sentetiktir ve saha verisiyle doğrulanmamıştır.** Katsayılar
(`coupling_k`, `tau_load_coeff`, `slow_share`, `sensor_gain_per_k`) fiziksel olarak
makul aralıklardan seçilmiş, **ölçülmemiştir**; `docs/14` §9 her biri için hangi ölçümün
gerekeceğini yazar. Buradan çıkan sayılar *"yöntem şu koşulda şöyle davranır"* demektir,
*"sahada duyarlılık şudur"* demek değildir.

`tau_load_coeff` işaretinin fiziksel yönü de **ölçülmemiştir**: doğal taşınımda h, dT ile
büyür ve `τ = C/(h·A)` **küçülür** (negatif); buna karşılık yük büyüdükçe ısının
katıldığı kütle derinleşir ve τ **büyür** (pozitif). Hangisinin baskın olduğu geometriye
bağlıdır. Senaryonun sonucu işaretten **bağımsızdır** — ölçüldü: c = −0,8 (τ 481 s),
c = −0,4 (569 s), c = +1,0 (1.223 s); üçünde de tepe `k_ratio` 3,00–3,02 ve beklenen
dört kodun **dördü de** çıkıyor. Bu yüzden işaret bir kanıt sorunu değil, yalnızca bir
tanım sorunudur.

Dördü **tek tek** açılıyor. Gerçek bir panoda hepsi aynı anda vardır ve etkileri
toplanabilir de, birbirini götürebilir de. Birleşik bir senaryo bilerek eklenmedi:
ölçüm o zaman hangi varsayıma atfedileceğini kaybederdi. Bu, kapatılmamış bir boşluktur
ve `docs/05` §10'da böyle yazılıdır.
