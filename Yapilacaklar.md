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

`nginx.conf` düzeltmesi şöyle doğrulandı: backend konteyneri silinip yeniden yaratıldı ve `172.18.0.5 → 172.18.0.13` IP'sine taşındı; **frontend'e hiç dokunulmadan** 30 saniye boyunca `/api/v1/panels` sürekli `200` döndü. Sorgu dizesi (`?limit=2`) ve WebSocket (`101 Switching Protocols`) de doğrulandı.

---

## 1. Öncelik sırası — birim emek başına puan

| Sıra | İş | Kriter | Tahmini kazanç | Emek | Neden bu sırada |
|:--:|---|:--:|:--:|:--:|---|
| **1** | Model-uyumsuzluğu senaryosu | K2 | +1,5 | 2–4 gün | Projenin **en büyük yapısal açığı**. "Duyarlılık 1,00" şu an dedektörün kendi modelini ters çevirmesini ölçüyor; bu iş onu gerçek bir başarı kanıtına çevirir. |
| **2** | ROI hesaplayıcı + OPEX | K8 | +2,0 | 2–3 gün | **En düşük puanlı kriter.** F-36 ölçümü (632 MB/pano/ay) OPEX'i besleyecek gerçek sayıyı zaten üretti — bağlamak kaldı. |
| **3** | Bileşen testleri + Playwright spec'i depoya | K7 | +0,5 | 1 gün | Ucuz. Arayüzün **hiç** testi yok; "0 konsol hatası" iddiasının tezgahı depoda değil. |
| **4** | Çoklu tohumla FPR/precision dağılımı | K2 | +0,5 | 1–2 gün | `validate.py:410` zaten "tek tohum, tek yörünge" diyor. n=10'dan n=500'e çıkmak ucuz. |
| **5** | Devreye alma prosedürünü gerçekleştir | K3 | +1,0 | 2–3 gün | **Saha jürisinin en çok bakacağı yer.** `docs/08` 3.787 bayt — bir ekibin izleyeceği belge değil. |
| **6** | Sıkıştırma oranını ölçülebilir kıl | K6 | +0,5 | 0,5 gün | Tek doğrulanamayan ölçüm. Betikle kapanır. |
| **7** | RUL'u kalibre et veya iddiayı daralt | K2/K9 | +0,5 | 1–2 gün | Kendi geri testiniz %5,2 diyor. Düzeltmek zor, **dürüstçe daraltmak** ucuz ve yeterli. |
| **8** | Birim→pano eşlemesini çalışma anında yayınla | K5 | +0,3 | 1 saat | Tek satırlık iş, K5'i 10'a yaklaştırır. |
| **9** | `docs/01` Paschen çelişkisini düzelt | K1 | +0,3 | 15 dakika | İki doküman birbirini yalanlıyor. |
| **10** | 10k pano projeksiyonu | K6 | +0,3 | 0,5 gün | Ölçülmüş 1.000 pano verisinden türetilir. |
| **11** | Bileşen düşüşünde arayüz davranışı | K4 | +0,3 | 1 gün | "Bayat veri" göstergesi. |
| **12** | S3_condense senaryosu | K2 | 0 / −risk | 2 saat | Karar: **bırakılıyor.** Riski aşağıda yazılı. |

**Toplam potansiyel:** eşit ağırlıkta ~7,6 → **~9,0**.

---

## 2. Kriter kriter detay

### K2 — Anomali ve risk tespit yaklaşımı · şu an **7**

#### 2.1 ⭐ Model-uyumsuzluğu senaryosu (P0 — en önemli tek iş)

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

### K8 — Maliyet ve sağlanan fayda · şu an **5** (README düzeltmesiyle ~6)

Bu, **en düşük puanlı ve en hızlı yükselecek** kriter. Üç yanlış sayı temizlendi; şimdi yerlerine gerçek analiz koymak gerekiyor.

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

---

### K7 — Kullanıcı / operasyon deneyimi · şu an **8**

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
| Dedektörün varsaymadığı fizik eklenirse duyarlılık ne olur? | **2.1** |
| BOM toplamı ile dipnot neden tutmuyor? | ✅ düzeltildi |
| "14-22 ay" hangi hesaptan çıkıyor? | **8.1** (ve iddia kaldırıldı) |
| Backend yeniden başlayınca operatör ekranı? | ✅ düzeltildi |
| S3_condense hiçbir şey enjekte etmiyor, farkında mısınız? | **2.4** (yorum ekleyin — "evet, bilinçli" cevabı hazır olsun) |

**En önemli tavsiye:** Bu projenin ayırt edici özelliği, iddialarını yeniden çalıştırılabilir üreteçlere bağlamış olması — `docs/12` birebir yeniden üretilebiliyor, üç protokol sıfır farkla okunuyor, denetim zinciri kurcalamayı yakalıyor. Jüri karşısında **bu disiplini** anlatın, özellik sayısını değil. Yukarıdaki işlerin çoğu da zaten aynı disiplini, henüz uygulanmadığı üç alana (maliyet, arayüz testi, model sınırı) taşımaktan ibarettir.
