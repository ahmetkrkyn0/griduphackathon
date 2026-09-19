# Yapılacaklar — Puanı Tavana Çekme Planı

**Kaynak:** 19 Eylül 2026 tarihli bağımsız değerlendirme ([`TAM_ANALIZ.md`](TAM_ANALIZ.md)).
**Yöntem:** Aşağıdaki her madde **koda bakılarak** yazıldı; dokümanlar yalnızca çapraz kontrol için kullanıldı. Bir doküman ile kod çeliştiğinde **kod esas alındı** — bazı dokümanlar (özellikle `docs/08`, `docs/16` §5, `KALAN-EKSIKLER.md`) 15–18 Eylül'de yazıldı ve bir kısmı eskimiş durumda.

> **Uyarı:** Buradaki puan tahminleri tek bir değerlendiricinin çapalarına dayanır ve garanti değildir. Amaç sıralama vermektir: **hangi iş, birim emek başına en çok puan getirir.**

---

## 0. Bu oturumda zaten kapatılanlar — tekrar yapmayın

| İş | Dosya | Durum |
|---|---|---|
| README'deki 12 yanlış/kaynaksız değer düzeltildi | `README.md` | ✅ |
| Yeni özellikler (F-20/21/22/23/31/32/36) README'ye işlendi | `README.md` → "Operasyon ve Mevzuat Yetenekleri" | ✅ |
| BOM dipnotları satır toplamına eşitlendi (70,73/47,68 ve 19,80/11,79) | `hardware/pano-beyni/bom.csv:19`, `hardware/pd-karti/bom.csv:11` | ✅ |
| Maliyet dokümanındaki 5 türev sayı düzeltildi (%34 → %32,6 dahil) | `docs/10-bom-maliyet-roi.md` | ✅ |
| **nginx `resolver` açığı kapatıldı** — backend yeniden başlayınca arayüz artık ≤10 s'de kendini toparlıyor | `frontend/nginx.conf` | ✅ ölçüldü |
| **Model-uyumsuzluğu senaryosu (madde 1 / §2.1)** — S10–S13, `ModelMismatch`, `docs/12` §1'de eşleşen/uyumsuz blokları | `libs/panoalgo/` · `docs/05` · `docs/12` · `docs/14` · `README.md` | ✅ ölçüldü (19 Eylül, dal `tuna/yapilacaklar-uygulama`) |
| `docs/05` §10'daki **yanlış iddia düzeltildi** — "209 saatlik öne alma tespit katmanından gelir" YANLIŞTI; sayıyı `ALM-TTL-14D` (prognoz) tetikliyor | `docs/05-anomali-tespiti.md` · `docs/12` §2 | ✅ ölçüldü |
| **ROI hesaplayıcı + OPEX (madde 2 / §2 K8)** — `--duyarlilik`, üç sütunlu parametre dosyası, pano başına toplam maliyet, OPEX bölümü, başa baş eşiği · **8.4 fiyat yerine eşik: sapma, kayıtlı** | `scripts/tazminat_maruziyeti.py` · `scripts/roi-ornek-parametreler.yaml` · `docs/10` §5.3/§6/§7 · `backend/tests/` | ✅ ölçüldü (19 Eylül, dal `tuna/yapilacaklar-uygulama`) |
| **Bileşen testleri + Playwright tezgâhı (madde 3 / §2 K7)** — 4 davranış kilitlendi, `e2e/smoke.spec.ts` 7 ekranı geziyor, `assets/ekran/` görüntülerini artık spec üretiyor, `@axe-core/playwright` + `theme.test.ts` · **tezgâh ilk koşusunda üretimdeki bir çökmeyi buldu** (kara kutu ekranı React #310 ile boştu) | `frontend/e2e/` · `frontend/playwright.config.ts` · `frontend/src/**/*.test.tsx` · `frontend/src/pages/OlayAnalizi.tsx` · `docs/16` · `docs/17` · `README.md` | ✅ ölçüldü (19 Eylül, dal `tuna/yapilacaklar-uygulama`) |
| Eski **~56 / ~37 USD** rakamları beş dosyada daha yaşıyordu (BOM düzeltmesi yalnızca README ve `docs/10`'a uygulanmış) — beşi de düzeltildi ve **testle kilitlendi** | `docs/17` (2 yer) · `docs/18` · `docs/19` · `demo/sunum/sunum-taslagi.md` | ✅ ölçüldü |
| **Eskimiş olgunluk etiketi:** `hardware/sensor-dugumu/` ve `hardware/pd-karti/` artık boş değil; "kavramsal / dizin boştur" ifadeleri *"belgelendi ama doğrulanmadı"* olarak düzeltildi | `docs/10` · `docs/17` · `docs/19` · `README.md` · `hardware/pano-beyni/README.md` | ✅ ölçüldü |

`nginx.conf` düzeltmesi şöyle doğrulandı: backend konteyneri silinip yeniden yaratıldı ve `172.18.0.5 → 172.18.0.13` IP'sine taşındı; **frontend'e hiç dokunulmadan** 30 saniye boyunca `/api/v1/panels` sürekli `200` döndü. Sorgu dizesi (`?limit=2`) ve WebSocket (`101 Switching Protocols`) de doğrulandı.

---

## 1. Öncelik sırası — birim emek başına puan

| Sıra | İş | Kriter | Tahmini kazanç | Emek | Neden bu sırada |
|:--:|---|:--:|:--:|:--:|---|
| ~~**1**~~ | ~~Model-uyumsuzluğu senaryosu~~ **✅ YAPILDI** | K2 | +1,5 | — | Tamamlandı 19 Eylül. Sonuç tahmin edilenden **farklı ve daha güçlü** çıktı: duyarlılık üç uyumsuzlukta düşmedi (oran yapısı sabit kazancı sadeleştiriyor — bu bir **güç**), ölçüm zinciri doğrusalsızlığında **0,50**'ye indi ve sabit 70 K eşiğinin tamamen körleştiği gösterildi. Ayrıntı §2.1'de. |
| ~~**2**~~ | ~~ROI hesaplayıcı + OPEX~~ **✅ YAPILDI (8.4 saptı)** | K8 | +2,0 | — | Tamamlandı 19 Eylül. Sonuç **tahminden üç yerde saptı**: (a) düğüm sayısı N=5 değil, sözleşme **25** tanımlıyor ve aralık **4–25**; pano başına toplam tek sayı değil **103,48–396,43 USD**. (b) Duyarlılık, "hangi varsayım belirliyor" sorusunun **cevabı olmadığını** gösterdi — üç varsayımın kaldıracı **birebir eşit** (1,33×, çarpımsal model); asıl belirleyici bir belirsizlik değil **yapılandırma seçimi** (N: 7,4 → 28,3 ay). (c) Maruziyette tarifenin kaldıracı **üstten 1,00× ile sınırlı**, eşiğe olan mesafeninki **sınırsız** (0,09×–3,57×) — ilk yazdığımız *"sıralama değişmez"* iddiası **bağımsız denetimde yanlışlandı ve düzeltildi**. 8.4'te fiyat **uydurulmadı**, yerine ölçülmüş **başa baş eşiği** (0,37 USD) kondu — bu spec'ten bir **sapmadır** ve öyle yazıldı. Ayrıntı §2 K8'de. |
| ~~**3**~~ | ~~Bileşen testleri + Playwright spec'i depoya~~ **✅ YAPILDI** | K7 | +0,5 | — | Tamamlandı 19 Eylül. **Bu maddenin kendi teşhisi iki yerde yanlıştı.** (a) *"Arayüzün **hiç** testi yok"* yanlıştı: 136 test vardı, olmayan şey **DOM/bileşen** testiydi (`.test.tsx` = 0) — bugün 17 dosya / **154 test**, 5'i gerçek DOM'da çiziyor. (b) Plandaki `environment: 'jsdom'` adımı **uygulanmadı**, çünkü denendiğinde 12 dosyanın 3'ü kırıldı (**38 test**, süre 1,95 s → 40,02 s); yalnızca `.tsx` dosyaları jsdom'a alındı. **Asıl kazanç tahmin edilen yerde çıkmadı:** tezgâh ilk koşusunda, hem örnek veri hem **üretim derlemesinde** kara kutu ekranını tamamen boş bırakan bir React #310 çökmesi buldu — yani *"7 ekranda 0 konsol hatası"* iddiası yazıldığı sırada **7 değil 6 ekran için** doğruydu. Düzeltildi, testle kilitlendi, yeniden ölçüldü: iki kipte de **0 hata / 0 uyarı**. Erişilebilirlik taraması ise **gizlenmeyen** bir sonuç verdi: örnek veri kipinde 5, canlı kipte **23 kontrast ihlali**. Ayrıntı §2 K7'de. |
| **4** | Çoklu tohumla FPR/precision dağılımı | K2 | +0,5 | 1–2 gün | `validate.py:410` zaten "tek tohum, tek yörünge" diyor. n=10'dan n=500'e çıkmak ucuz. |
| **5** | Devreye alma prosedürünü gerçekleştir | K3 | +1,0 | 2–3 gün | **Saha jürisinin en çok bakacağı yer.** `docs/08` 3.787 bayt — bir ekibin izleyeceği belge değil. |
| **6** | Sıkıştırma oranını ölçülebilir kıl | K6 | +0,5 | 0,5 gün | Tek doğrulanamayan ölçüm. Betikle kapanır. |
| **7** | RUL'u kalibre et veya iddiayı daralt | K2/K9 | +0,5 | 1–2 gün | Kendi geri testiniz %5,2 diyor. Düzeltmek zor, **dürüstçe daraltmak** ucuz ve yeterli. |
| **8** | Birim→pano eşlemesini çalışma anında yayınla | K5 | +0,3 | 1 saat | Tek satırlık iş, K5'i 10'a yaklaştırır. |
| **9** | `docs/01` Paschen çelişkisini düzelt | K1 | +0,3 | 15 dakika | İki doküman birbirini yalanlıyor. |
| **10** | 10k pano projeksiyonu | K6 | +0,3 | 0,5 gün | Ölçülmüş 1.000 pano verisinden türetilir. |
| **11** | Bileşen düşüşünde arayüz davranışı | K4 | +0,3 | 1 gün | "Bayat veri" göstergesi. **Madde 3 ile KAPATILMADI ve bu bilinçli:** §2 K4 4.1'in metni *"bunu 7.1'deki bileşen testleriyle kilitleyin"* diyor, ama **kilitlenecek özellik henüz yok** (`AppShell.tsx:140` yalnızca "Veri akışı bağlı" gösteriyor). Önce UI kodu yazmak gerekir; o da test işi değil. |
| **12** | S3_condense senaryosu | K2 | 0 / −risk | 2 saat | Karar: **bırakılıyor.** Riski aşağıda yazılı. |

**Toplam potansiyel:** eşit ağırlıkta ~7,6 → **~9,0**. **Madde 1, 2 ve 3 kapandı (19 Eylül);** kalan sıralama **4'ten** başlar.

---

## 2. Kriter kriter detay

### K2 — Anomali ve risk tespit yaklaşımı · şu an **7**

#### 2.1 ✅ Model-uyumsuzluğu senaryosu — **TAMAMLANDI (19 Eylül 2026)**

> **Durum:** dal `tuna/yapilacaklar-uygulama`, commit `3674756`. 498 test geçiyor
> (taban 489 + 9 yeni). S0–S9'un 10 CSV'si **bit bit** korundu.
>
> **Aşağıdaki analiz, işin gerekçesi olarak olduğu gibi bırakıldı.** Ne çıktığı
> hemen altındaki "Ölçülen sonuç" bloğundadır — ve **tahminden sapmıştır**.

##### Ölçülen sonuç — hipotez kısmen yanlışlandı

Beklenti *"uyumsuz senaryolarda duyarlılık 1,00'ın altına inecek"* idi. Üç fizik
önerilen biçimde uygulandığında **hiçbiri tespiti bozmadı** ve sebep yapısaldır:
alarm kuralları K'yı değil **K/K₀ oranını** okur, taban K₀ da aynı uyumsuz fizikle
öğrenildiği için durağan yanlılık `(g·K)/(g·K₀)` içinde **birebir sadeleşir**. Bu
yöntemin bir **gücüdür** ve `docs/05` §10'a öyle yazıldı.

| Senaryo | Uyumsuzluk | Recall | Asıl bedel |
|---|---|---:|---|
| `S10_coupling` | difüzif ısıl kuplaj | 1,00 | `k_ratio` eşiğini aşan nokta 1 → **2**: teşhis "hangi pano" düzeyinde doğru, **"hangi klemens" düzeyinde yanlış** |
| `S11_load_tau` | yüke bağlı τ | 1,00 | τ sapıyor, tespit sağlam — **bloğun seçmeci olmadığının kanıtı**, bilerek yayımlandı |
| `S12_two_pole` | ikinci ısıl kutup | 1,00 | yayımlanan τ **9,5 kat** yanlış (689 s → 6.576 s) + **yasaklı alarm**: `ALM-DQ-DRIFT` gerçekten arızalı noktayı "kalibrasyon şüpheli" diyor |
| `S13_sensor_nonlin` | ölçüm sıkışması | **0,50** | terminal gerçekte **78,90 K**, ölçüm **48,48 K** → **sabit 70 K eşiği tamamen körleşiyor**; oran tabanlı K tespiti ayakta kalıyor |

**Jüri masasında okunuşu:** *"Eşleşen modelde 8/8, duyarlılık 1,00. Dedektörün
varsaymadığı fiziği ekleyince 0,88 — ve nerede kırıldığını biliyoruz: ölçüm zinciri
sıkışırsa sabit 70 K eşiği tamamen körleşiyor, bizim oran tabanlı tespitimiz ise
ayakta kalıyor. Dedektöre hiçbir şey eklemedik; amaç güçlendirmek değil sınırı
ölçmekti."* Bu, "duyarlılık 1,00" demekten çok daha güçlüdür.

##### Tahminden sapan üç karar (gerekçeleriyle)

1. **S10–S12 değil, S10–S13.** Madde "en az üç fizik" diyor; problem tanımının kendisi
   dört saha zorluğu sayıyor ve dördüncüsü (**sensör doğrusalsızlığı**) en net sonucu
   veren oldu. Her senaryo dedektörün **tek** bir varsayımını bozuyor — ikisi birden
   açılsaydı ölçüm hangi varsayıma atfedileceğini kaybederdi.
2. **Kuplaj toplamalı değil difüzif.** Önerilen `steady += c·ort(dT_komşu)` kararlı
   hâli `K·I²/(1−c)` yapıyor, yani panoyu **ısıtıyor** (ölçüldü: tepe artış 79,0 →
   90,6 K). O zaman "model yanlış" ile "pano daha sıcak" ayrıştırılamazdı. Difüzif
   biçimde (Fourier) grup tekdüze ısındığında terim sıfır; değişen tek şey **grup içi
   yapı** — yani `phase_compare`'in ölçtüğü büyüklük.
3. **τ(I) üstel biçimde** (`τ₀·exp(c·I/Iₙ)`): doğrusal formun birinci mertebe eşi, ama
   2× aşırı yükte τ'yu pozitif tutuyor. İşaretin fiziksel yönü **ölçülmedi**; sonuç
   işaretten bağımsız çıktı (c = −0,8 / −0,4 / +1,0 → aynı tespit).

##### Açık kalan

- **Sözleşme değişikliği üç onay bekliyor** (`contracts/changes/2026-09-19-model-uyumsuzlugu-senaryolari.md`). Şema değişikliği
  (enum + `unmodelled_physics`) onaydan önce fiilen uygulandı; akışa uygun
  görülmezse geri alınıp onay sonrasına bırakılabilir.
- **Dört fizik tek tek açılıyor.** Gerçek panoda hepsi aynı andadır; birleşik etki
  ölçülmedi (bilinçli — attribution korunsun diye). `docs/05` §10'da yazılı.
- **Katsayılar sentetik**, saha ölçümü yok. Her biri için gereken ölçüm `docs/14`
  §9.3'te tablo hâlinde.

---

<details>
<summary>İşin özgün analizi (19 Eylül öncesi) — gerekçe olarak korundu</summary>


**Sorun (koddan):** [`generator.py:558-580`](libs/panoalgo/panoalgo/generator.py) ısıyı şu denklemle ilerletiyor:

```
dT[k+1] = a·dT[k] + (1−a)·K·I²[k],   a = exp(−dt/τ)
```

[`detect.py:3-5`](libs/panoalgo/panoalgo/detect.py) **tam olarak aynı** denklemin `[a, β]` parametrelerini RLS ile kestiriyor ve `K = β/(1−a)` diyor. Arıza da `spec.k0 · _k_multiplier[...]` ile **doğrudan kestirilen parametreye** enjekte ediliyor. Üretecin kendi docstring'i (`:563-570`) indis hizalamasının bilerek aynı tutulduğunu yazıyor.

Sonuç: "8 senaryoda duyarlılık 1,00" büyük ölçüde *"kestirici kendi ileri modelini ters çevirebiliyor"* demektir. Sahadaki asıl zorluklar — model uyumsuzluğu, ikinci zaman sabiti, komşu hücre kuplajı, sensör doğrusalsızlığı — hiç sınanmıyor. Üreteçte bunları enjekte edecek **hiçbir kanca yok** (`grep coupling|tau2|second_order` → sıfır eşleşme).

**Yapılacak:**

1. `generator.py`'ye dedektörün **varsaymadığı** en az üç fizik ekleyin, her biri bayrakla açılıp kapanan:
   - **Isıl kuplaj:** komşu bağlantı noktasının sıcaklığının bir kesri (`coupling_k`, ör. 0,05–0,15) her noktanın kararlı hâline eklensin. Dedektör tek noktalı model kullandığı için bu doğrudan bir yanlılık üretir.
   - **Yüke bağlı zaman sabiti:** `τ = τ0 · (1 + c·I/In)`. Dedektör `τ`'yu sabit varsayıyor.
   - **İkinci zaman sabiti:** hızlı (bara) + yavaş (kutu içi hava) iki kutuplu davranış. Gerçek panolarda vardır.
2. `scenarios.py`'ye bunları kullanan **S10–S12** senaryolarını ekleyin; `expect`/`not_expect` etiketleri aynı biçimde.
3. `validate.py` çıktısına **"model uyumu"** sütunu ekleyin: `eşleşen` / `uyumsuz`. `docs/12` §1 tablosu iki bloğa ayrılsın.

**Beklenen sonuç ve nasıl sunulur:** Uyumsuz senaryolarda duyarlılık muhtemelen 1,00'ın altına inecek. **Bu kötü haber değil, asıl kanıttır.** README'de şöyle okunur: *"Eşleşen modelde 8/8; dedektörün varsaymadığı fizik eklendiğinde 2/3 — yöntemin sınırı budur ve ölçtük."* Jüri masasında "duyarlılık 1,00" demekten **çok daha** güçlüdür, çünkü değerlendiricinin ilk soracağı şey budur (bkz. `TAM_ANALIZ.md` §9 soru 1).

**Dikkat:** Yeni fizik `detect.py`'ye **eklenmemeli**. Amaç dedektörü güçlendirmek değil, sınırını ölçmek.

</details>

#### 2.2 Çoklu tohumla gerçek FPR (P1)

**Sorun (koddan):** [`validate.py:85-86`](libs/panoalgo/panoalgo/validate.py) `precision_ok` adında bir **bool** üretir ("yasaklı kod çıktı mı"). Docstring bunu dürüstçe tanımlıyor ve README sayı uydurmuyor — yani *yanıltıcı değil*, ama klasik `TP/(TP+FP)` hiçbir yerde hesaplanmıyor. `validate.py:410` zaten şunu kabul ediyor: *"tek bir seed'li senaryonun tek bir bozulma yörüngesi ölçülmüştür."*

**Yapılacak:**
1. `scripts/validate.py`'ye `--seeds N` (varsayılan 1, önerilen 200–500) ekleyin. Her senaryoyu N tohumla koşun.
2. Şunları raporlayın: senaryo başına **duyarlılık dağılımı** (medyan + %5/%95), **yanlış pozitif oranı**, ve tohum başına olay/100 pano/gün dağılımı.
3. **En değerli çıktı:** hangi tohumlarda ne kırılıyor. `S8_sensor_fault`'un bazı tohumlarda `ALM-K-ALM` tetiklediği bildirildi — 500 tohumla bunu kesinleştirin; doğruysa "yasaklı alarm 0" koşulsuz değil, **oransaldır** ve öyle yazılmalıdır.
4. Koşu süresi uzarsa `--seeds` paralelleştirilebilir (`multiprocessing.Pool`), fikstürler bağımsız.

#### 2.3 RUL: kalibre edin veya iddiayı daraltın (P1)

**Sorun (koddan + ölçümden):** `docs/12` §4'ü ben yeniden ürettim: S1 için **koni içinde %5,2**, **CRA −5,12**, ufuk "yok", medyan tahmin/gerçek **1,69** — yani ömrü sistematik olarak **%69 fazla** tahmin ediyor. [`prognostics.py`](libs/panoalgo/panoalgo/prognostics.py) metrik makinesi doğru (alpha-lambda, prognostic horizon, convergence hepsi var); **kötü olan tahmin edicinin kendisi**, yani kenarın yayınladığı `min_ttl_h`.

**İki yol var, ikisi de kabul edilebilir:**

- **A (ucuz, dürüst):** RUL'u nokta tahmini olarak sunmayı bırakın. Arayüzde ve Telegram'da "78 gün" yerine **"6–14 hafta"** gibi bir bant gösterin; bandı geri testin gözlenen hata dağılımından türetin. README ve `docs/12` zaten geri testi yayımlıyor — bantlı sunum onunla tutarlı olur.
- **B (pahalı, güçlü):** Sistematik 1,69 çarpanı **yanlılıktır, gürültü değil** — yani düzeltilebilir. `min_ttl_h` hesabında ileri tarama, `K̇`'yi EWMA ile düzleştiriyor (`detect.py:47` `K_SLOPE_ALPHA = 0.05`); bu, hızlanan bozulmada eğimi olduğundan küçük gösterir ve ömrü uzun tahmin eder. İkinci dereceden bir terim veya daha kısa pencereli bir eğim kestirimi deneyin, sonra geri testi yeniden koşun.

**Her hâlükârda:** düzelttiyseniz yeni CRA'yı yayımlayın, düzeltmediyseniz mevcut sayıyı görünür tutun. Şu anki en büyük değeriniz, kötü sonucu kendinizin yayımlıyor olması.

#### 2.4 S3_condense — bilinçli olarak bırakılıyor

**Karar: ekip bunu bırakmayı seçti.** Yine de riski yazılı olsun.

**Durum (koddan):** [`scenarios.py:119-129`](libs/panoalgo/panoalgo/scenarios.py) senaryoyu `season="kis"` + `humidity_offset_pct: 25` ile tanımlıyor. Ama [`generator.py:603-606`](libs/panoalgo/panoalgo/generator.py) nem modeli `RH = 50 + 2·(40−T)` ve tavan %98. Kış aralığında (`WINTER_MEAN_C=5 ± 5 K` → 0–10 °C) RH **zaten tavanda** olduğu için offset'in etkisi **tam 0,000 puandır**. Senaryo, `S0_normal`'ın kışta koşulmuş hâliyle bit bit aynıdır.

**Risk:** "8 anomali senaryosu" aslında 7 enjeksiyon + 1 boş. Kodu okuyan bir jüri üyesi bunu bulursa, *doğrulanmış* diğer sayılarınızı da indirimli okumaya başlar.

**Bırakılacaksa en azından şunu yapın (15 dakika):** `scenarios.py:119` üstüne bir yorum düşün — *"S3, kış rejiminde RH tavanda olduğu için ek enjeksiyon içermez; sağlıklı kış davranışının çiy eşiklerini tetiklediğini gösteren bir REGRESYON senaryosudur."* Böylece bulan kişi bunu gizlenmiş bir hata değil, **bilinçli bir tasarım** olarak okur. Bu tek yorum, riski neredeyse sıfırlar.

**İleride düzeltmek isterseniz:** `RH_MAX_PCT`'i değiştirmeyin (S0'ı da bozar). Bunun yerine yoğuşmayı doğru yerden enjekte edin: yüzey sıcaklığını çiy noktasının altına indiren bir **yüzey soğuması** terimi ekleyin (gece radyatif soğuma), ki bu zaten gerçek mekanizmadır.

---

### K8 — Maliyet ve sağlanan fayda · şu an **5** (README düzeltmesiyle ~6) → **8.1–8.3 kapatıldı, 8.4 gerekçeli olarak saptı**

Bu, **en düşük puanlı ve en hızlı yükselecek** kriterdi. Üç yanlış sayı temizlenmişti; yerlerine konan gerçek analiz aşağıdadır.

#### 8.1–8.4 ✅ ROI hesaplayıcısı + OPEX — **8.1, 8.2, 8.3 TAMAMLANDI · 8.4 SAPTI (19 Eylül 2026)**

> **Durum:** dal `tuna/yapilacaklar-uygulama`. Backend testleri geçiyor (taban 853 + **27 yeni**),
> `libs/panoalgo` **498 test** bozulmadı, `scripts/check_contracts.py` → **SOZLESMELER TUTARLI**.
> **Erdem korundu:** `tazminat_maruziyeti.py` argümansız koştuğunda hâlâ `veri yok` diyor ve **1 ile
> çıkıyor** (testle kilitli).
>
> **Bu iş bittikten sonra bağımsız bir denetimden geçti ve denetim üç gerçek kusur buldu** — üçü de
> aşağıda düzeltildi ve ne oldukları yazıldı. Denetimin en değerli bulgusu, aşağıdaki 4. maddede
> yayımlanan ilk iddianın **yanlış** olmasıydı.
>
> **Aşağıdaki analiz, işin gerekçesi olarak olduğu gibi bırakıldı.** Ne çıktığı hemen altındaki
> "Ölçülen sonuç" bloğundadır — ve **üç yerde tahminden sapmıştır**.

##### Ölçülen sonuç — maddenin kendi sayı tahmini yanlışlandı

**1. Düğüm sayısı N = 5 değil.** Madde 8.3, N'i `docs/10` §2'deki *"S1–S5"* ifadesinden **5** diye
okumuş ve pano başına ≈ **117,4 USD** öngörmüştü. Ölçüm bunu yanlışladı: *S1–S5* bir düğüm **sayısı**
değil, raporun **senaryo/sensör türü** etiketidir; sözleşmede 5 noktalı bir yapılandırma **yoktur**.
Gerçek sınırlar ölçülebilir:

| Kaynak | N | Ne söylüyor |
|---|:--:|---|
| `contracts/modbus-map.yaml` `conn_temp.points` | **25** | `GIRIS_L1/L2/L3/N` (4) + 7 DSYA × 3 faz (21). `check_contracts.py` "25 izleme noktası" diye sayıyor |
| `loadtest/fleet.py:348` varsayılanı | **7** | Ana giriş + ilk fider; `docs/09` ölçümlerinin çoğu bu yapılandırmada |
| `loadtest/fleet.py:720` izin verilen aralık | **4–25** | altı reddedilir, üstü sözleşmede yok |

**Pano başına toplam (adet 1.000):** 4 düğüm **103,48 USD** · 7 düğüm **145,33 USD** · 25 düğüm
**396,43 USD** · 25 + PD (OG) **408,22 USD**. Tek sayı yerine **aralık** yayımlandı ve tahmin edilen
117,4 USD aralığın alt ucuna yakın düşüyor.

**2. Maliyeti kontrolcü değil sensör düğümleri belirliyor.** Toplamın **%67,2'si** (N=7) ve **%88,0'ı**
(N=25) düğümlerdir. Hackathon boyunca maliyet tartışması kontrolcünün 47,68 USD'si üzerinden yürüdü;
ölçüm bunun toplamın üçte birinden azı olduğunu gösterdi.

**3. Duyarlılık tablosu "hangi varsayım" sorusuna beklenen cevabı vermedi — daha iyisini verdi.**
Madde, `--duyarlilik`'in *"hangi varsayım sonucu belirliyor"* sorusunu cevaplamasını bekliyordu. Ölçüm,
sorunun bu biçimde **cevabı olmadığını** gösterdi:

| Girdi | Kaldıraç | Güven | Ne demek |
|---|---:|---|---|
| `ariza_olasiligi_yil` | **1,33×** | varsayım | üçü de **birebir eşit** — geri ödeme `maliyet / (P × L × r)` olduğu için her çarpan aynı aralığı verir |
| `ariza_basi_maliyet_usd` | **1,33×** | varsayım | |
| `tespit_orani` | **1,33×** | varsayım | |
| `dugum_sayisi` | 0,67× | türetildi | maliyet bir **toplamdır** (kontrolcü + N × düğüm), çarpım değil |

Yani *"sonucu şu varsayım belirliyor"* denemez; **üçünün çarpımı** belirler ve biri düzeltilmeden hesap
düzelmez. Beklenen değer tam olarak **4/3**'tür ve testle kilitlendi
(`test_carpimsal_girdilerin_kaldiraci_esit_cikar`). Asıl belirleyici ise duyarlılık tablosunda **hiç
görünmüyor**: sözleşmenin izin verdiği 4 → 25 aralığı geri ödemeyi **7,4 aydan 28,3 aya** taşıyor
(3,8 kat) — ama N bir belirsizlik değil bir **seçimdir**, o yüzden ayrı bir tabloda *"duyarlılık değil,
seçim"* başlığıyla basılıyor.

**4. Maruziyet tarafı — önce YANLIŞ yazıldı, denetim yanlışladı, sonra doğrusu ölçüldü.** Bu maddenin
hikâyesi sonucundan daha öğreticidir ve olduğu gibi bırakılıyor.

*İlk yazılan:* tek bir örnek girdi setiyle koşuldu (`kesinti_sayisi` 2,02× en üstte, `dagitim_bedeli`
0,19× en altta) ve buradan **"değişmez olan sıralamadır"** diye genel bir sonuç yazıldı; README'ye ve
`docs/17`'ye de öyle taşındı. *Yanlışlandı:* bağımsız denetim aynı betiği başka bir makul girdi setiyle
koştu — `kesinti_basi_tazminat` 5 TL alındığında `dagitim_bedeli` **0,71×**'e çıkıp `esik_sayi`'yı
(0,59×) **geçiyor**. Sıralama bir ölçüm değil, seçilen örneğin artefaktıymış. Üstelik onu "kilitlediği"
söylenen test, dokümandaki **aynı** girdileri kullandığı için hiçbir şey kanıtlamıyordu.

*Sonra ölçülen (altı parametre setinde):* değişmeyen üç şey var ve üçü de aritmetikten türüyor —
(a) `abone` **her zaman tam 1,00×** (iki kalemi birden çarpan tek girdi); (b) düz çarpanların
(`dagitim_bedeli`, `ortalama_talep_kw`, `kesinti_basi_tazminat`) kaldıracı **kendi kaleminin toplamdaki
payına birebir eşittir**, yani **1,00×'i asla geçemez**; (c) eşik kalemlerinin kaldıracı **sınırsızdır**
— ölçülen aralık **0,09× – 3,57×**.

**"Tarifeyi bilmiyorsunuz" itirazının savunulabilir cevabı budur:** tarife bu hesabın baskın belirsizliği
**olamaz**, çünkü kaldıracı üstten 1,00× ile sınırlıdır; eşiğe olan mesafeninki değildir. Testler artık
örneği değil **özelliği** kilitliyor (`test_maruziyet_kaldiraclarinin_yapisal_sinirlari`), ve ayrıca
sıralamanın değişken olduğunu da kilitliyor (`test_siralama_ornekten_ornege_DEGISIYOR`) — biri ileride
yine "sıralama yapısaldır" diye yazarsa test onu yakalar.

**5. Madde 8.4 için fiyat YAZILMADI — yerine ölçülmüş bir eşik kondu.** Madde *"tek bir kamuya açık
katalog fiyatı bile yeterlidir"* diyordu. Bu oturumda doğrulanabilir bir kataloğa erişilmedi ve
`docs/19`'un kendi ilkesi (*"bu oturumda hiçbir üretici veri sayfasına erişilmedi"*) gereği fiyat
uydurulmadı. Yerine **hiçbir dış fiyata ihtiyaç duymayan** bir sayı yayımlandı:

> Kaçınılan **10** kalemin **ortalama birim fiyatı 0,37 USD**'yi (adet 1.000) / **0,49 USD**'yi (adet 1)
> geçtiği anda mevcut cihazı Modbus'tan okumak kendini öder.

Eşiğin payı ödenen RS485 arayüzünün `bom.csv` fiyatı, paydası sözleşmeden sayılan kalem adedidir —
**tamamı ölçülü**. Yargıyı jüriye devreder: bu eşiğin altında bir ölçüm sınıfı akım trafosu olmadığını
söyleyen biz değiliz, okuyucunun kendi piyasa bilgisidir. Fiyat girilirse betik net farkı zaten yazıyor.

**6. OPEX (8.2) — hacim ölçülü, tarife "işletmeci doldurur".** F-36 paraya bağlandı ama **tarife
uydurulmadı**. En güçlü cümle tarifeden bağımsız çıktı:

| Politika | Hacim (pano/yıl) | §3'ün varsayımsal faydasını sıfırlayan tarife |
|---|---:|---:|
| Sabit 10 s | 12,85 GB | **13,07 USD/GB** |
| Uyarlanabilir %2 | 7,58 GB | **22,15 USD/GB** |

*Uyarlanabilir yayın, projeyi zarara sokan tarife eşiğini **1,70 kat** yukarı taşır* — ve bu oran
bastırma oranının kendisidir, yani **ölçülmüştür**. Ayrıca `docs/10` §6.3, faturanın bu hacimden
**yüksek** çıkmasının **altı ölçülmüş/kayıtlı sebebini** sayıyor (110 B/mesaj tahmini, boşluklu JSON'un
ölçülen 1,139 katı, operatör yuvarlaması, 7 noktalı panoda oranın ölçülmemiş olması, mTLS ek yükü,
iş istasyonunda ölçülmüş sunucu sayıları). Hacim bir **alt sınır** olarak yayımlandı.

##### Bağımsız denetimin bulduğu ve düzeltilen üç kusur

1. **Yayımlanan bir iddia yanlıştı** — yukarıdaki 4. madde. Sayıyı kurtarmak yerine iddia değiştirildi
   ve yanlışlanma süreci yayımlandı.
2. **Betik çöküyordu.** `--tespit-orani 0` verildiğinde brüt fayda sıfır oluyor, `payback_months()`
   doğru davranıp `None` dönüyor, ama rapor satırı onu `{ay:.1f}` ile biçimlendirmeye çalışıp
   `TypeError` ile düşüyordu. Artık *"GERI ODEME: HICBIR ZAMAN — brut yillik fayda sifir"* yazıyor;
   regresyon testi eklendi.
3. **Duyarlılık tablosu, betiğin kendi reddettiği bir yapılandırmadan sayı türetiyordu.** 7 düğümün
   −%50'si 3,5'tir; ne 3,5 düğüm vardır ne de betik 4'ün altını kabul eder. Oynatılan değer artık
   yuvarlanıp sözleşmenin 4–25 sınırlarına **kırpılıyor** ve tabloda hangi değerin kullanıldığı
   yazılıyor. (Yuvarlama *yarıyı yukarı* alır: `round()` bankacı yuvarlaması yapıp 3,5→4 ama 10,5→10
   verdiği için aynı satırın iki ucu farklı yöne yuvarlanıyordu.)

Ayrıca denetim **eskimiş bir atıf** yakaladı: betik ve `docs/10` §3, tespit oranının ölçülen değerini
*"`docs/12` §1'de 1,00"* diye yazıyordu. Bu artık doğru değil — **madde 1** (S10–S13) aynı bölümü iki
bloklu hâle getirdi ve uyumsuz blokta S13 **0,50** veriyor. Üç yerde de iki blok birden yazıldı.

##### Yol üstünde bulunan ve kapatılan iki çelişki (maddede yazmıyordu)

1. **`README` ile `docs/10` birbirini yalanlıyordu.** README *"geri ödeme süresi bu depoda
   hesaplanmamıştır"* derken `docs/10` §3 bir geri ödeme süresi yayımlıyordu: *"< 1 yıl"*. Üstelik o
   sayı **yalnızca kontrolcü maliyetiyle** hesaplanmıştı, yani paydası eksikti. Çözüm sayıyı kurtarmak
   değil **hesabı yürütülebilir kılmak** oldu.
2. **Eski `~56 / ~37 USD` rakamları beş yerde yaşamaya devam ediyordu.** §0 tablosu BOM dipnotlarının
   düzeltildiğini yazıyor (commit `b5e2601`) ama düzeltme yalnızca `README` ve `docs/10`'a uygulanmış;
   `docs/17` (2 yer), `docs/18`, `docs/19` ve **jüriye sözlü anlatılacak** `demo/sunum/sunum-taslagi.md`
   hâlâ eski sayıyı taşıyordu. Beşi de düzeltildi ve **ne yazdıkları not düşüldü** (silinmedi).
   Üç BOM'un dipnotu artık **testle kilitli**
   (`test_bom_toplami_csv_toplam_satirindaki_metinle_ayni`) — aynı sapma bir daha sessizce oluşamaz.

Ayrıca **eskimiş olgunluk etiketi** düzeltildi (maddenin "dikkat" notu 1): `hardware/sensor-dugumu/`
artık boş değil ve deponun **kendi** olgunluk ölçütünü karşılıyor (blok diyagramı + I/O tablosu + BOM —
bu ölçütü `hardware/pano-beyni/README.md` tanımlamıştır; düğüm dizini ayrıca bir enerji/termal hesap
taşıyor, pano-beyni'nde onun dengi yok). `docs/10`, `docs/17`, `docs/19` (3 yer), `README` ve
`hardware/pano-beyni/README.md` düzeltildi. **Değişmeyen sınır açıkça korundu:** hiçbir BOM satırı veri
sayfasına karşı doğrulanmadı, kart üretilmedi, kablosuz menzil metal kabinde ölçülmedi. *"Tasarlanmadı"*
ile *"doğrulanmadı"* ayrımı her düzeltmede yazıldı.

##### Tahminden sapan üç karar (gerekçeleriyle)

1. **Geri ödeme betiğe eklendi, `docs/10` §3'ün tablosuna değil.** Madde yalnızca `--duyarlilik` istiyordu,
   ama duyarlılığın oynatacağı bir **metrik** yoktu: betik maruziyeti hesaplıyordu, geri ödemeyi değil.
   Payı (BOM'dan ölçülen maliyet) ve paydası (varsayılan fayda) ayrı ayrı etiketlenerek eklendi.
2. **`--dugum-sayisi` için varsayılan konmadı.** Konsaydı betik N'i kendi seçmiş olurdu — tam da
   korunması istenen erdemin ihlali. Verilmezse toplam `veri yok` döner ve sözleşmenin sınırlarını yazar.
3. **Parametre dosyası satır içi yorum değil, yapısal üç sütun oldu.** Maddenin örneği `# kaynak: ...`
   biçimindeydi; yorum **denetlenemez**. Yapısal biçimde `guven: isletmeci-doldurur` etiketli bir girdiye
   değer yazılırsa dosya **reddediliyor** — yani uydurulmuş bir sayı, kaynağı "işletmeci" gösterilerek
   tabloya giremiyor. Beş denetimin tamamı testli.

##### Açık kalan

- **Fayda tarafı hâlâ ölçüm değil.** P(arıza), arıza başı maliyet ve tespit oranı varsayımdır ve
  duyarlılık üçünün de sonucu **eşit** belirlediğini gösterdi. Bunu kapatan şey saha arıza istatistiğidir,
  daha iyi bir hesap değil.
- **Hiçbir tarife girilmedi:** hücresel M2M, sunucu/VM, kalibrasyon ve SIM hat bedeli `veri yok`.
  Kaçınılan dört kalemin birim fiyatı da öyle.
- **Kurulum işçiliği, montaj malzemesi ve tip test/sertifikasyon hiçbir toplamda yok** — BOM satırları
  olmadığı için adet olarak bile sayılamıyorlar (`docs/19` §3.1).
- **`loadtest/results/` depoya girmiyor** (`.gitignore`), yani F-36'nın ham çıktısı bir klonda hazır
  bulunmaz; `docs/10` §6.3 bunu yazıyor ve yeniden üretme komutunu veriyor.
- **Başa baş eşiğinin payı belirsiz kaldı ve bilerek karara bağlanmadı.** `bom.csv`'deki 3 adet INA226
  (2,70 USD) 47,68 USD toplamına giriyor ama §5.2'nin dürüstlük notu onların Temel pakette
  kullanılmadığını söylüyor. Eşik ya 0,37 ya 0,64 USD'dir; ikisi de `docs/10` §5.3'te yazılı. Bu bir
  kart yerleşimi sorusudur, burada seçilecek bir sayı değil.
- **Fayda modelinde müdahale terimi yok:** `tespit_orani` doğrudan önleme oranı gibi kullanılıyor, yani
  "alarm çıktı" ile "arıza önlendi" ayrılmıyor. Betiğin *çıktısı* GK10'a uyuyor ("önledik" demiyor) ama
  paydadaki büyüklük fiilen odur. Kapatmak için iki çarpan daha gerekir (müdahale olasılığı × müdahalenin
  etkisi) ve ikisi de ölçülmedi — bu yüzden eklenmedi, uydurulmadı.
- **Maddenin "dikkat" notu 2 eskimiş çıktı:** `scripts/gen_modbus_doc.py --check` temiz HEAD'de **"eski"
  demiyor**, "guncel" diyor ve 0 ile çıkıyor. Altı `--check` üretecinin altısı da temiz.

---

<details>
<summary>İşin özgün analizi (19 Eylül öncesi) — gerekçe olarak korundu</summary>

#### 8.1 ⭐ Geri ödeme hesaplayıcısı — parametre dosyası + duyarlılık (P0)

**Durum (koddan):** [`scripts/tazminat_maruziyeti.py`](scripts/tazminat_maruziyeti.py) doğru davranıyor — parametre verilmezse `veri yok` döndürüyor ve *"betik bunları uydurmaz"* diyor. Bu **korunması gereken** bir erdem. Sorun, jürinin elinde çalıştırabileceği **hiçbir örnek** olmaması.

**Yapılacak:**
1. `scripts/roi-ornek-parametreler.yaml` ekleyin. Her satırda **üç sütun**: değer, kaynak, güven düzeyi. Örnek:
   ```yaml
   abone_sayisi:        412      # kaynak: scripts/ornek-cbs-aktarim.json (ÖRNEK veri)
   dagitim_bedeli_tl:   null     # kaynak: EPDK tarifesi — İŞLETMECİ DOLDURACAK
   ariza_olasiligi_yil: 0.03     # kaynak: docs/10 §3 VARSAYIM, ölçüm değil
   ```
   `null` kalanlar ekranda `veri yok` olarak görünmeye devam etsin — betiğin mevcut davranışı korunur.
2. Betiğe `--duyarlilik` bayrağı ekleyin: her girdiyi ±%50 oynatıp geri ödeme süresinin aralığını **tablo olarak** bassın. Tek bir "14-22 ay" sayısından çok daha savunulabilirdir ve "hangi varsayım sonucu belirliyor" sorusunu cevaplar.
3. `backend/tests/test_tazminat_maruziyeti.py` zaten var; duyarlılık tablosu için bir test daha ekleyin.

#### 8.2 ⭐ OPEX — F-36 ölçümünü maliyete bağlayın (P0, kolay ve etkili)

**Bu şu an masada duran en kolay puan.** F-36 ölçümü zaten elinizde: pano başına aylık **1.071 MB** (sabit 10 s) → **632 MB** (uyarlanabilir %2). Hiçbir yerde **paraya çevrilmemiş.**

**Yapılacak:** `docs/10`'a bir OPEX bölümü ekleyin:

| Kalem | Birim | 1.000 pano / yıl |
|---|---|---|
| Hücresel veri (632 MB/pano/ay) | M2M tarifesi TL/GB | ölçülen hacim × tarife |
| Sunucu (on-prem) | `docs/09` §5 ölçülen CPU/RAM/disk | ölçülen kaynaktan türet |
| Bakım / kalibrasyon | `fleet/nodes` vade takibinden | düğüm başına yıllık |

Tarifeyi bilmiyorsanız **boş bırakın ve "işletmeci doldurur" yazın** — `tazminat_maruziyeti.py`'nin yaptığı gibi. Önemli olan, **hacmin ölçülmüş** olması. Ayrıca burada gösterilecek güçlü bir argüman var: *"uyarlanabilir yayın OPEX'i %41 düşürür ve tespit hızını değiştirmez"* — bu, ölçülmüş bir maliyet-fayda önermesidir.

#### 8.3 Pano başına toplam maliyet (P1)

Şu an doğrulanmış bir toplam **yok** (README bunu artık dürüstçe söylüyor). Kapatmak için sensör düğümü sayısını netleştirin:

- Kontrolcü (adet 1.000): **47,68 USD** ✅ ölçülü
- Sensör düğümü × N: 13,95 USD/düğüm — **N kaç?** `docs/10` "S1–S5" diyor, yani 5 → 69,75 USD
- PD kartı (opsiyonel, yalnızca OG): 11,79 USD
- Toplam (AG, 5 düğüm): **≈ 117,4 USD/pano** · OG (PD dahil): **≈ 129,2 USD/pano**

Bu sayıyı yayımlayabilmek için `hardware/sensor-dugumu/` "kavramsal" etiketinden çıkmalı — en azından I/O planı + mekanik arayüz + montaj yöntemi netleşmeli. Aksi hâlde **"5 düğüm varsayımıyla, düğüm tasarımı kavramsal seviyede"** diye açıkça etiketleyin.

#### 8.4 Kaçınılan kalemleri fiyatlandırın (P1)

`tazminat_maruziyeti.py` **BOM farkı** bölümünde doğru işi yapıyor: mevcut cihazlar sensör olarak okunduğu için 4 akım trafosu, 3 gerilim girişi, 2 ark dedektörü ve 1 ark koruma merkez ünitesi eklenmiyor. Ama hepsi `veri yok` fiyatla. **Bu, projenin en güçlü ticari argümanı ve şu an sayısız.** Üç tedarikçi teklifi yerine tek bir kamuya açık katalog fiyatı bile yeterlidir — kaynağı yazın.

</details>

---

### K7 — Kullanıcı / operasyon deneyimi · şu an **8**

#### 7.1–7.3 ✅ Bileşen testleri + Playwright tezgâhı + erişilebilirlik taraması — **7.1, 7.2, 7.3 TAMAMLANDI (19 Eylül 2026)**

> **Durum:** dal `tuna/yapilacaklar-uygulama`, commit `e3038a1`. Frontend **12 dosya / 136
> test → 17 dosya / 154 test**, hepsi yeşil (vitest 2.1.9). `npm run build`
> (`tsc --noEmit && vite build`) yeşil. Backend **880 geçti / 37 atlandı** ve
> `libs/panoalgo` **498** bozulmadı. `scripts/check_contracts.py` → **SOZLESMELER
> TUTARLI**, `scripts/sir_taramasi.py` → **temiz** (484 izlenen dosya, 14 ignore kuralı).
>
> **Aşağıdaki analiz, işin gerekçesi olarak olduğu gibi bırakıldı.** Ne çıktığı hemen
> altındaki "Ölçülen sonuç" bloğundadır — ve **maddenin kendi teşhisi iki yerde
> yanlışlandı, bir yerde de tezgâh beklenmedik bir kusur buldu.**

##### Ölçülen sonuç — tezgâh ilk koşusunda üretimdeki bir çökmeyi buldu

**1. En önemli sonuç: "7 ekranda 0 konsol hatası" yazıldığı sırada DOĞRU DEĞİLDİ.**
Tezgâh kurulup ilk kez koşturulduğunda **kara kutu ekranı (`/olay/:id`) tamamen boş
çıktı.** `OlayAnalizi.tsx`'te bir `useMemo`, `if (error)` / `if (!data)` erken
dönüşlerinin **altındaydı**: ilk çizimde `data` null olduğu için çağrılmıyor, veri
gelince çağrılıyordu; hook sayısı 9 → 10 değişince React **#310** fırlatıyordu
(*"Rendered more hooks than during the previous render"*). Hem `npm run dev:mock`'ta hem
**:3000 üretim derlemesinde** doğrulandı — yani hata dev'e özgü değildi, dağıtılan
arayüzde de vardı. **Yedi ekranın yedisi değil, altısı hatasızdı.**

Bu, maddenin kendi savunduğu şeyin en iyi kanıtı: *"sonuç doğruydu ama yeniden
üretilemiyordu"* demek yetmiyormuş — **yeniden üretilemeyen sonuç aynı zamanda
yanlışlanamıyordu.** Kusur düzeltildi ve regresyonu `frontend/src/pages/OlayAnalizi.test.tsx`
ile kilitlendi. Testin gerçekten iş gördüğü **düzeltme geri alınarak doğrulandı**:
kusurluyken kırmızı, düzeltmeyle yeşil.

Düzeltmeden **sonra** ölçülen: örnek veri kipinde 10 rotada **0 hata / 0 uyarı**, canlı
kipte 10 rotada **0 hata / 0 uyarı**.

**2. `test.environment = 'jsdom'` adımı (7.1'in 1. maddesi) UYGULANMADI — ölçüm onu
yanlışladı.** Plan global `jsdom` diyordu. Denendi ve **12 dosyanın 3'ü kırıldı**:

| Kırılan | Test | Sebep |
|---|--:|---|
| `print.test.ts` | 14 | `readFileSync(new URL(…, import.meta.url))` — jsdom'da `import.meta.url` `file:` şemasında değil |
| `labels.test.ts` | 16 | aynı |
| `panelGeometry.test.ts` | 8 | aynı |

Toplam **38 test** düştü (136 → 98) ve süre **1,95 s → 40,02 s** çıktı. Ayrıca bu
dosyanın kendi uyarısı (`session.test.ts`'in `Object.assign(globalThis, …)` yüzünden
kırılacağı) **tutmadı** — o dosya sorunsuz geçti. Uygulanan çözüm:
`environmentMatchGlobs` ile **yalnızca `.tsx` testleri** jsdom'a giriyor; node testleri
bedel ödemiyor. Gerekçe `vite.config.ts`'te yazılı.

**3. ★ Sessiz başarısızlık kapatıldı.** `vite.config.ts`'in `include`'u
`src/**/*.test.ts` idi — yani **`.tsx` test dosyaları hiç toplanmıyordu.** Bu
düzeltilmeden yazılan her bileşen testi yazılır, `npm test` yine "136 passed" der ve
**yeşil görünürdü**. Artık `src/**/*.test.ts?(x)`; doğrulama ölçütü *"Test Files sayısı
12'den büyük"*tür ve bugün **17**'dir.

**4. Erişilebilirlik: ihlaller bulundu, düzeltilmedi, GİZLENMEDİ — testte kilitlendi.**
`@axe-core/playwright` ile WCAG 2.1 A + AA taraması:

| Kip | `color-contrast` ihlali | Başka axe kuralı |
|---|--:|---|
| örnek veri (`:5173`) | **5 düğüm** | yok |
| canlı (`:3000`) | **23 düğüm** | yok |

Farkın tamamı `AppShell`'deki **iki ögeden** gelir ve ikisi de örnek veri kipinde hiç
çizilmez: `.connection-pill` **4,26:1** ve `.btn-link` **2,91:1**. Her rotada göründükleri
için 2 × 10 = 20, artı `/`de 3 `.focus-number` = 23. **Yani "arayüzde 5 kontrast ihlali
var" demek yanlış olurdu; hangi kipten söz edildiği söylenmek zorunda.** Bu, iki kipi
ayırmanın en somut karşılığıdır.

Renk paleti **değiştirilmedi** — palet kararı test işi değildir ve `docs/16` ile
`frontend/TASARIM-REVIZYONU.md`'deki tasarım kaydını geçersiz kılardı. Sayı testte kilitli:
yeni ihlal çıkarsa test düşer, **biri düzeltilirse de düşer** ve bu doğrudur, çünkü o zaman
`docs/16` §4'teki tablonun da yeniden ölçülmesi gerekir.

**5. Elle hesabın göremediği şey ölçüldü.** Elle kontrast hesabı zeminin her zaman `--bg`
olduğunu varsayar. axe gerçekten çizilen rengi okur ve varsayımın yanlış olduğu yerde
patladı: `/bölge`deki `.kesinti-serit` zemini `--bg` (#f5f6f8) değil **#ebecee** ve aynı
`--dim` token'ı orada 4,61:1 değil **4,21:1** veriyor — **AA'nın altında.**

**6. Bu işi yaparken yazılan bir varsayım da yanlışlandı.** `theme.test.ts`'e önce
*"`--p1`/`--p2`/`--p3` beyaz zeminde AA'yı geçer"* diye yazıldı; test kırıldı. `app.css`
okununca gerçek çiftlerin bambaşka olduğu görüldü: `.prio` metni **beyaz**, `.prio-P3` ise
`--ink`/`--p3` = **3,67:1** ile eşiğin **altında**. Test ölçülene göre yeniden yazıldı.
Üstelik axe o düğümü **hiç değerlendirmedi**, çünkü taranan yedi ekranın hiçbirinde P3
rozeti çizilmedi — bu da bir ölçüm boşluğu olarak kayda geçti. Ders madde 2'dekiyle aynı:
**tek örnekten genel sonuç çıkarma.**

##### Bu testin NEYİ kilitlediği — dürüst kapsam

"0 konsol hatası" **bir örneğin sonucudur, özelliğin garantisi değildir.** Ölçülen:
tek tarayıcı (Chromium 153), tek genişlik (1425 px), yalnızca **sayfa açılışı**.
**Ölçülmeyenler, açıkça:**

- **Etkileşim sonrası hatalar** — tıklama, form gönderimi, sekme değiştirme.
- **3B ikiz sekmesi** bilerek tıklanmıyor: `Ikiz3D.tsx:104` WebGL yoksa fırlatır; hata
  sınırı (`PanoDetay.tsx:288-295`) yakalasa bile React yine `console.error` basar. 3B
  varsayılan sekme değil ve `lazy()` ile yükleniyor, yani tıklanmadıkça hiç çalışmıyor.
- **390 px viewport** hâlâ elle kontrol ediliyor; e2e tek genişlikte koşar.
- **P3 rozetinin 3,67:1 oranı** axe kapsamına hiç girmedi (ekranlarda P3 rozeti yoktu).
- **Diğer tarayıcılar** (yalnızca chromium kuruldu), yavaş ağ, sahadaki veri çeşitliliği.
- **Canlı kipten ekran görüntüsü** üretilmedi; commit edilen 8 PNG örnek veri kipindendir
  (`GRIDUP_E2E_EKRAN=1` ile canlıdan üretme yolu açık bırakıldı ama koşulmadı).
- **CI'a bağlanmadı** — §3 madde 1 kapsamı, bilinçli olarak dışarıda bırakıldı.

##### Yan çıktı: bayat sayı zinciri aynı anda kapatıldı

`docs/16` §1/§4/§5 (kontrast **~16:1 → 13,33:1**, ikincil **~5,8:1 → 4,61:1**,
`--bg #ffffff → #f5f6f8`, "otomatik viewport testi yok" gerekçesi), `docs/11` satır 18,
`docs/17` (frontend **85 → 154** dört ayrı yerde, panoalgo **401 → 498**, backend
**661 → 880/37**), `README.md` (panoalgo **489 → 498**, backend **853 → 880/37**, frontend
**136 → 154**, DSN'li koşu "890" → **917 toplanır**; DSN'li geçme sayısı bu oturumda
**ölçülmedi** ve öyle yazıldı). `KALAN-EKSIKLER.md` **tarihli bir anlık görüntü** olduğu
için sayıları değiştirilmedi; `5c969d1` kaydı korunup üstüne 19 Eylül notu düşüldü.
`docs/17`'nin *"doğru kaynak bu tablodur"* notu **kendi kendini yanlışlamıştı** (tablo
85'te kalmışken README zaten 136 diyordu) ve bu ders olarak yazıldı.

**Atıf hatası, kayda geçiyor:** aşağıdaki özgün analiz iddianın yerini `docs/17:159`
diyor; gerçek satır **160**'tı ve aynı iddia `docs/17`'de **40** ile **193**. satırlarda
**da** vardı. Yani "tek yeri düzelttim" tuzağı buradaydı; üçü birden düzeltildi. (Özgün
blok belge kaydı olarak değiştirilmeden bırakıldığı için yanlış satır numarası orada
duruyor; satır numaraları bu düzenlemelerden sonra zaten kaymıştır — kalıcı referans
olarak satır numarası değil **dosya + bölüm** kullanılmalıdır.)

Ayrıca **bu işin yanlışladığı dört kaynak yorumu** düzeltildi: `frontend/src/print.test.ts`
ve `src/api/session.test.ts`'teki *"DOM yok"* / *"yeni npm bağımlılığı yasak"* ifadeleri ile
`src/lib/etki.ts` ve `src/lib/kesinti.ts`'teki *"`environment: node`, yalnızca `*.test.ts`
toplanır"* ifadeleri. Dördünde de gerçek sınır **daha dar** yazıldı.

##### Nasıl koşulur

```bash
cd frontend && npm ci
npm test                                  # 17 dosya / 154 test — "Test Files" 12'den BÜYÜK olmalı
npm run build                             # tsc --noEmit && vite build
npm run e2e                               # örnek veri kipi (:5173) — Vite'i spec kendi kaldırır
GRIDUP_E2E_KIP=canli npx playwright test   # canlı yığın (:3000 ÖNCEDEN ayakta olmalı)
```

<details>
<summary><strong>Özgün analiz (iş başlamadan önce yazıldı) — olduğu gibi bırakıldı</strong></summary>

#### 7.1 ⭐ Bileşen testleri (P0 — ucuz)

**Durum (koddan):** `frontend/package.json` yalnızca `vitest` içeriyor; `@testing-library/react`, `jsdom`/`happy-dom` **yok**. 136 testin **tamamı** `src/lib/` ve `src/api/` saf fonksiyon testi; `.test.tsx` dosyası **sıfır**. Yani yedi ekranın hiçbiri, hiçbir alarm kartı, hiçbir etkileşim test altında değil — çalıştıklarını elle gördük, ama bir regresyon bunu sessizce bozar.

**Yapılacak:**
1. `npm i -D @testing-library/react @testing-library/user-event jsdom` ve `vite.config.ts`'e `test.environment = 'jsdom'`.
2. En kritik dört davranışı kilitleyin (her biri ~30 satır):
   - Alarm kartı **dört başlığı** da gösteriyor mu (Neden / Ne doğrulanmalı / Ne yapmalı / Ne kadar acil)?
   - "Onayla" butonu belirteç yokken ne yapıyor? (401 → kullanıcıya anlaşılır hata)
   - Filo listesi boş yanıtta çökmüyor mu?
   - `AlarmNedeni` bileşeni eksik `reason` alanıyla çökmüyor mu?
3. Bunlar `docs/16`'daki tasarım iddialarını **yürütülebilir** hâle getirir — kriter 7'de doküman yerine test gösterebilirsiniz.

#### 7.2 Playwright tezgahını depoya koyun (P0 — yarım gün)

**Durum:** `KALAN-EKSIKLER.md:34` ve `docs/17:159` *"Playwright: 7 ekran, 0 konsol hatası"* diyor. **Depoda Playwright yapılandırması, spec dosyası veya bağımlılığı yok.** Sonucu bağımsız olarak doğruladım — **sayı doğru**, ama depodan yeniden üretilemiyor; yani bir iddia, kanıt değil.

**Yapılacak:** `frontend/e2e/smoke.spec.ts` + `playwright.config.ts` ekleyin. Yedi rotayı gezip **konsol hatası sayısını assert edin** (`expect(errors).toHaveLength(0)`). Ekran görüntülerini `assets/ekran/` altına bu spec üretsin — `docs/16` §5'teki görüntüler şu an örnek veri kipinde alınmış; canlı yığından üretmek `KALAN-EKSIKLER.md:238`'in kendi önerisidir.

#### 7.3 Erişilebilirlik ölçümünü otomatikleştirin (P2)

Kontrast değeri (`13,33:1`) elle hesaplandı ve bir kez daha eskiyecek. `@axe-core/playwright` ile smoke spec'e bir erişilebilirlik taraması ekleyin; sayı artık dokümanda değil **testte** yaşar.

</details>

---

### K3 — Saha koşullarında uygulanabilirlik · şu an **7**

#### 3.1 ⭐ Devreye alma prosedürünü gerçekleştirin (P1 — saha jürisinin sorusu)

**Durum:** [`docs/08-kurulum-proseduru.md`](docs/08-kurulum-proseduru.md) **3.787 bayt**. Retrofit, gerilim altında pano, tork kontrolü gibi bir işte bir saha ekibinin izleyebileceği ayrıntıda değil. Bu kriterde 9 alamamanızın ana sebebi bu.

**Yapılacak — bir ekibin gerçekten izleyebileceği belge:**
1. **Ön koşullar:** hangi pano tipleri uygun, hangi MPR-53CS/TVOC-2 firmware sürümleri, RS-485 hattında kaç cihaz var, boş DIN rayı kaç modül.
2. **Güvenlik:** enerji altında mı kesintide mi çalışılıyor, hangi KKD, kilitleme-etiketleme adımları, kim yetkili. **Bu bölümün yokluğu bir dağıtım şirketinde tek başına eleme sebebidir.**
3. **Mekanik montaj:** kutu nereye, sensör düğümü bara bağlantısına nasıl, **tork değerleri**, kablo kanalı, minimum açıklık.
4. **Elektriksel:** besleme nereden, RS-485 sonlandırma ve polarite, topraklama, ekran bağlantısı hangi uçta.
5. **Ağ:** APN/SIM, hangi portlar, hangi sunucuya, sertifika nasıl yükleniyor (F-27 mTLS kullanılacaksa).
6. **Kabul testi:** *"şu komutu koş, şu çıktıyı gör"* biçiminde bir liste. `GET /health` + `fleet/nodes` + bir test alarmı (`test_alarm` yazılabilir register'ı zaten var). Bu, devreye almanın **bittiğini kanıtlayan** adımdır.
7. **Devreye alma formu:** saha ekibinin imzalayıp dolduracağı tek sayfa — seri no, CBS kodu, kalibrasyon tarihi. Bunlar zaten `POST /api/v1/fleet/nodes` ve `POST /api/v1/fleet/assets` uçlarının beklediği alanlar; form ile API'yi **aynı alan adlarıyla** hizalayın.

Madde 7, K3 ile K5'i aynı anda güçlendirir: kâğıt form ile veri modeli birebir örtüşürse "bu sistem gerçekten devreye alınabilir" iddiası somutlaşır.

#### 3.2 Cihaz kimliği (F-28) — en azından bir dilim kod (P2)

`GELISTIRME-BACKLOGU.md:435` bunu **"yalnızca yol haritası, kod yok"** diye dürüstçe işaretliyor ve bu **lehinize**. Puanı artıracak minimum iş: sertifikaların elle üretilmesini (`scripts/sertifika-uret.sh`) bırakıp **basit bir kayıt ucu** ekleyin — cihaz CSR gönderir, sunucu imzalar, ACL sertifikanın CN'inden türer. Tam PKI işletimi gerekmez; "sıfır-dokunuş kayıt" iddiasının **bir ucu** çalışsın yeter.

---

### K6 — Ölçeklenebilirlik · şu an **8**

#### 6.1 Sıkıştırma oranını ölçülebilir kılın (P1 — yarım gün)

**Durum (koddan):** [`deploy/initdb/005_compression.sql`](deploy/initdb/005_compression.sql) politikası gerçek ve kurulu (`segmentby = pano_id, tag`, `orderby = ts DESC`). Ama sıkıştırma **1 günden eski parçalara** uygulandığı için taze bir yığında oran ölçülemez — değerlendirmede `0/1 parça sıkıştırılmış` çıktı ve **46–48× iddiası doğrulanamadı**.

**Yapılacak:** `scripts/olc_sikistirma.py` ekleyin:
1. Geçmiş tarihli telemetri üret (fizik üreteciyle, **şablon üreteçle değil** — şablonda etiketlerin yarıdan fazlası sabit ve bu oranı yapay olarak şişirir).
2. `SELECT compress_chunk(...)` ile parçaları elle sıkıştır.
3. `hypertable_compression_stats` ile önce/sonra bayt ve oranı bas.
4. İndeksin orana katkısını **ayrı sütunda** göster — mevcut 46–48× indeks elenmesini de içeriyor ve bu ayrıştırılmalı.

Çıkan oran 46–48×'ten düşükse **düşük olanı yazın**; ölçülmüş 20× , ölçülmemiş 48×'ten iyidir.

#### 6.2 10k pano projeksiyonu (P2)

Ölçümünüz 1.000 panoda duruyor; çapada 9 için 10k+ senaryo isteniyor. 10k'yı koşmanız gerekmiyor — **ölçülmüş** 1.000 pano verisinden türetin ve darboğazı adlandırın:
- Ölçülen: ~99 mesaj/s, 1.458.000 satır/180 s, görünme p95 710 ms (benim koşumda), CPU/RAM `docs/09` §5'te.
- 10k'da ne olur: hangi bileşen önce doyar — ingest kuyruğu mu, TimescaleDB yazma mı, MQTT broker mı? **Ölçülmüş** CPU eğrisinden ekstrapole edin ve "şu noktada ikinci bir ingest işçisi / broker kümesi gerekir" deyin.
- F-36 burada da işinize yarar: uyarlanabilir yayın 10k'da mesaj hızını %41 düşürür, yani doyum noktasını öteler. Bunu **sayıyla** gösterin.

---

### K5 — Operasyon sistemleriyle entegrasyon · şu an **9** (en güçlü kriteriniz)

#### 5.1 Birim→pano eşlemesini çalışma anında yayınlayın (P2 — 1 saat)

**Durum (koddan):** [`gateway.py:162`](backend/app/scada/gateway.py) birimleri alfabetik olarak atıyor (`heapq.nsmallest`), ama `GET /health` yalnızca `units: 6` diyor — **hangi birimin hangi panoya baktığını söylemiyor.** Bir SCADA entegratörünün ilk ihtiyacı budur ve şu an yalnızca dokümanda.

**Yapılacak:** `/health` yanıtına `scada.unit_map: {1: "ADM-00001", ...}` ekleyin veya `GET /api/v1/scada/units` açın. Otomatik atama (`auto_units: true`) kullanıldığında eşleme yeniden başlatmada **değişebilir**; bunu da yanıtta belirtin — gerçek kurulumda `MODBUS_UNITS` ile sabitlenmeli, bu da devreye alma prosedürüne bir madde.

#### 5.2 Register haritasını cihaz kılavuzlarıyla doğrulayın (P2)

Değerlendirmede doğrulanamayan tek K5 kalemi buydu: 430 register, iki kılavuz PDF'i. `check_contracts.py` **iç tutarlılığı** garanti ediyor ama kılavuza sadakati değil. `Hackathon Verileri/` altındaki MPR-53CS ve TVOC-2 kılavuzlarından örneklem alıp (her bloktan 5 adres) bir eşleme testi yazın. Bir tanesi zaten var ve çok iyi: `devices.py:60-65` kılavuzun `0x42B6 → 2016-10-04` tarih kodlaması örneğini çözüyor.

---

### K4 — Uçtan uca sistem · şu an **8** (nginx düzeltmesiyle ~9)

#### 4.1 Bileşen düşüşünde arayüz davranışı (P2)

**Durum (koddan):** Dayanıklılık aslında iyi — `ingest.py:385` MQTT için geri çekilmeli yeniden bağlanma, `db.py:463` havuz zaman aşımı ve `OperationalError` yakalama, şema dışı mesajlar **düşürülmüyor** karantinaya yazılıyor (`ingest.py:5,9`). nginx açığı da kapandı.

**Kalan:** Arayüz, backend'e ulaşamadığında veya veri bayatladığında bunu **operatöre söylüyor mu?** Sol altta "Veri akışı bağlı" göstergesi var; kopukluk hâlinde ne olduğu test altında değil. Bir kontrol odası ekranının **sessizce bayatlaması** alarm izlemede en tehlikeli hata modudur.

**Yapılacak:** Son telemetri yaşı eşiği aşınca ekranın üstüne kalıcı bir uyarı şeridi: *"Veri akışı X dakikadır durdu — gösterilen değerler bayat."* Bunu 7.1'deki bileşen testleriyle kilitleyin.

---

### K1 — Problemin doğru anlaşılması · şu an **8**

#### 1.1 Paschen çelişkisini düzeltin (P2 — 15 dakika)

[`docs/01-problem-analizi.md:24-26`](docs/01-problem-analizi.md) hâlâ *"havada Paschen minimumu ~327 V; 400 V sistemde pratikte beklenmez"* diyor. [`docs/05-anomali-tespiti.md:330-333`](docs/05-anomali-tespiti.md) bu kısayolu **"YANLIŞ"** diye geri çekiyor (faz-faz tepe 566 V > 327 V) ve yerine geometrik bir gerekçe koyuyor. Kendi argümanınızı çürütmeniz **lehinize**, ama jüri özeti olan `docs/01` düzeltilmemiş. İki cümlelik iş.

#### 1.2 Mevsimsellik bulgusunu doğru çerçeveleyin (README'de yapıldı, dokümanda da yapın)

`README.md` artık bunun üretecin iklim modelinin bir özelliği olduğunu söylüyor. Aynı çerçeveyi `docs/05` §11'e de taşıyın: kış sıcaklıklarında `RH` tavanda olduğu için çiy marjı zorunlu olarak negatiftir; bu **gerçek bir fiziksel olgudur** ama sizin sayınız onu *ölçmüyor*, modelden *türetiyor*. Gerçek meteoroloji verisiyle (MGM Aydın/İzmir saatlik nem) bir kez doğrulamak bu kriteri 9'a taşır ve bir günlük iştir.

---

### K9 — Yenilikçilik · şu an **8**

#### 9.1 C çekirdeğini gerçek bir hedefte koşturun (P2)

**Durum (koddan):** `firmware/core/rls.c` gerçekten gömülü uyumlu — `malloc` yok, sabit boyutlu yapı, `PANO_USE_FLOAT` ile tek duyarlık. Ölçtüğüm bellek: **384 B** (double) / **196 B** (float), 25 nokta = 9,4 KB. Ortak test vektörü tezgahı (`firmware/tests/test_rls.c`) güçlü bir testtir.

**Eksik:** "Mikrodenetleyicilerde çalışır" iddiası şu an yalnızca **host derlemesiyle** destekleniyor. Bunu kapatmanın ucuz yolu:
1. `arm-none-eabi-gcc` ile Cortex-M4F hedefine **çapraz derleyin** ve `.text`/`.bss`/`.data` boyutlarını (`arm-none-eabi-size`) yayımlayın. Kod çalıştırmanıza gerek yok — **derlenip sığdığını** göstermek iddiayı kanıtlar.
2. İsterseniz QEMU (`qemu-system-arm`, `lm3s6965evb`) üzerinde test vektörünü koşturun; CI'a eklenebilir ve "gömülüde doğrulandı" iddiası artık ölçülüdür.
3. Bir de **çevrim süresi** ölçün: 25 nokta × RLS güncellemesi kaç µs? 10 s periyotta bütçenin ne kadarını yiyor? Bu sayı saha jürisinde karşılık bulur.

---

## 3. Kriterlerin ötesi — sektörel olgunluk

Bunlar puan tablosunda doğrudan görünmez ama "bu ekip bunu gerçekten kurabilir mi" izlenimini belirler.

1. **CI kurun.** Depoda dört test paketi ve altı `--check` üreteci var, hepsi elle koşuluyor. Bir GitHub Actions dosyası (`pytest` × 2, `npm test`, `ctest`, altı `--check`) bu disiplini **otomatik** hâle getirir. Şu an en büyük regresyon riskiniz, birinin bir sözleşmeyi değiştirip `--check`'i koşmaması.
2. **Sürüm ve geri alma.** `compose.yaml` imajları digest ile sabitliyor — bu iyi. Eksik olan: veritabanı göçlerinin (`deploy/initdb/001..010`) **ileri-geri** oynatılabilirliği. Şu an yalnızca sıfırdan kurulum destekleniyor; sahada ikinci sürüme geçiş bir göç aracı ister.
3. **Gözlemlenebilirlik.** Grafana panoları üretiliyor (`gen_grafana_dashboards.py`) ama **uygulama metriği** yok (ingest gecikmesi, kuyruk derinliği, alarm üretim hızı). `/health` zengin; bunu Prometheus formatında da yayınlamak yarım günlük iş ve operasyon ekibinin ilk isteyeceği şey.
4. **KVKK/veri sınırı.** `docs/15` var ve ciddi. Eksik olan tek şey: `notify/privacy.py` neyi maskeliyor, bunun bir testi var mı? Telefon numarası ve chat id'nin loglara düşmediğini **testle** kilitleyin.
5. **Demo dayanıklılığı.** Jüri sunumunda yığın bozulursa kurtarma planı olsun: `scripts/seed_demo.py` münhasır veritabanı istiyor (yazıcılar açıkken kırılıyor — bu değerlendirmede yaşandı). Sunum öncesi çalıştırılacak tek bir `demo-hazirla.sh` yazın: yazıcıları durdur → tohumla → yazıcıları başlat → sağlık kontrolü.

---

## 4. Sunum masası için — hazır olun

Değerlendirme sırasında cevabı dokümanda hazır olmayan beş soru çıktı ([`TAM_ANALIZ.md`](TAM_ANALIZ.md) §9). Yukarıdaki işler bunların dördünü kapatıyor:

| Soru | Kapatan madde |
|---|---|
| Dedektörün varsaymadığı fizik eklenirse duyarlılık ne olur? | ✅ **ölçüldü** — 0,88; kırılan yer ölçüm zinciri doğrusalsızlığı (§2.1) |
| BOM toplamı ile dipnot neden tutmuyor? | ✅ düzeltildi — **ve artık testle kilitli** (üç BOM, `test_bom_toplami_csv_toplam_satirindaki_metinle_ayni`) |
| "14-22 ay" hangi hesaptan çıkıyor? | ✅ **ölçüldü** — iddia kaldırılmıştı; yerine yürütülebilir bir hesap ve **aralık** kondu: 7,4–28,3 ay, belirleyeni düğüm sayısı seçimi (§2 K8) |
| Backend yeniden başlayınca operatör ekranı? | ✅ düzeltildi |
| S3_condense hiçbir şey enjekte etmiyor, farkında mısınız? | **2.4** (yorum ekleyin — "evet, bilinçli" cevabı hazır olsun) |

**En önemli tavsiye:** Bu projenin ayırt edici özelliği, iddialarını yeniden çalıştırılabilir üreteçlere bağlamış olması — `docs/12` birebir yeniden üretilebiliyor, üç protokol sıfır farkla okunuyor, denetim zinciri kurcalamayı yakalıyor. Jüri karşısında **bu disiplini** anlatın, özellik sayısını değil. Yukarıdaki işlerin çoğu da zaten aynı disiplini, henüz uygulanmadığı üç alana (maliyet, arayüz testi, model sınırı) taşımaktan ibarettir.
