# 18 Eylül 2026 — L2 filo akran karşılaştırması ve taban geçerliliği (F-32)

**Dosya:** `contracts/openapi.yaml`
**Öneren:** Kişi A (Tuna)
**Durum:** **KABUL EDİLDİ ve UYGULANDI — 18 Eylül 2026**
**Sürüm etkisi:** `1.5.0` → `1.6.0`

**Ne değişiyor:**
1. Yeni şema `FleetPeers` — akran karşılaştırması özeti ve yeniden baz alma önerileri.
2. Tek yeni uç: `GET /api/v1/fleet/peers` (okuma, açık).

**Neden:** `K/K₀` bir noktayı yalnızca **kendi geçmişiyle** ölçer. Devreye alma gününde
zaten gevşek olan bir bağlantıda taban **bozuk değeri** dondurur: K yüksek, K₀ aynı oranda
yüksek, `k_ratio` 1,0. O nokta ömrü boyunca sağlıklı görünür ve L1 eşiği (`k_ratio_warn`
1,3) **hiçbir zaman tetiklenmez**. Nokta kendi geçmişiyle karşılaştırıldığı sürece bu hata
görülemez; gören tek şey **akranlarıdır**.

**Etkilenen kulvarlar:** B (bir depo yöntemi, bir uç)
**Geri uyumlu mu:** **evet.** Yalnızca ekleme; var olan hiçbir uç, şema veya alan değişmedi.

**Onaylar:** [x] A  [x] B  [x] C

---

## Telemetri şeması DEĞİŞMEDİ — K₀ merkezde yeniden türetiliyor

Bu maddenin en kolay yanlışı, kenara `k0` diye yeni bir alan açmaktı.
`contracts/mqtt-telemetry.schema.json` `t_conn[]` için `additionalProperties: false`
tanımlıyor: kenara yeni alan açmak **mesajı reddettirir** ve üç dosyalık donmuş sözleşme
zincirini (şema → Modbus haritası → üretilmiş dokümanlar → firmware başlığı) tetiklerdi.

Gerek yoktu. `k_ratio = k / K₀` olduğundan **K₀ = k / k_ratio** ve iki alan da
(`t_conn[].k`, `t_conn[].k_ratio`) donmuş şemada **zaten var**. Merkez tabanı okumaz,
**yeniden türetir**. Aynı kaçış F-10'un `_verify` çözümünde kullanılmıştı: liste kenardan
taşınmaz, merkezde yeniden üretilir.

Tabanı **donmamış** nokta karşılaştırmaya girmez. `edge.py` taban yokken `k_ratio`'yu
sabit 1,0 döndürür; oradan çıkan sayı bir taban değil anlık kestirimdir. Atlanan nokta
"K₀ yok" demektir, **"sağlıklı" demek değildir**.

## Yeni alarm kodu AÇILMADI

Sözleşmede `layer: L2` etiketli alarm kodu yok ve bu öneri **bir tane açmıyor**. Sebebi
usul: `alarm-codes.yaml`'daki her kodun bir `bit` alanı var, yani yeni bir kod Modbus
bit tahsisini, beş üretecin çıktısını ve `firmware/core/modbus_map_generated.h`'yi
birden tetikler. L2'nin ilk çıktısının bir **alarm** değil bir **öneri** olması ayrıca
doğru olandır: otomatik yeniden baz alma gerçek bozulmayı susturur (aşağıda).

L2 için alarm kodu açmak istenirse bu **ayrı bir `contracts/changes/` önerisidir**.

## Yeniden baz alma neden yalnızca ÖNERİ

Otomatik yeniden baz alma alarmı susturabilir: bozulmakta olan bir noktada tabanı
güncellemek `k_ratio`'yu 1,0'a geri çeker ve gerçek bozulma **görünmez** olur — alarmın
kendisini silen bir "düzeltme". Bu yeni bir yazılım hata türüdür ve
`docs/07b-fmea-yazilim-sistem.md`'ye **Y11** satırı olarak girildi.

Bu yüzden uç K₀'a **dokunmaz**. Çıktısı bir bayrak ve gerekçedir; kararı operatör verir.
`rebaseline_suggestions[].reasons` boş olamaz — gerekçesiz öneri üretilmez.

## Akran grubu nokta adıdır

`DSYA4_L3` yalnızca başka panoların `DSYA4_L3`'ü ile karşılaştırılır. Şema nokta adını
sabit bir regex'e bağlıyor (`^(GIRIS_(L1|L2|L3|N)|DSYA[1-7]_L[1-3])$`) ve TEDAŞ tipi
panoda aynı ad aynı çıkış boyunu, yani aynı anma akımını gösterir. `GIRIS_L1` ile
`DSYA1_L1`'i aynı torbaya koymak **2312 A ile 250 A'i** karşılaştırmak olurdu; K₀'ları
mertebe farklılığındadır (`K = dT / I²`).

Skor **MAD tabanlı modifiye z**'dir. Ortalama/standart sapma kullanılsaydı bozuk panonun
kendisi ölçüye girer ve **aradığımız şeyi saklardı**; medyan ve MAD %50'ye kadar bozuk
veriye dayanır.

## "Ölçemedik" ile "aykırı değil" ayrı şeydir

Akran sayısı `min_peers` altında kalan noktalar yanıtta **yer alır** ama `robust_z` `null`
döner ve aykırı sayılmazlar. `points_unmeasurable` bunları **sayıyla** raporlar, böylece
kapsanmayan nokta gizlenmez. Az akranla üretilen bir z, ölçmediğimiz bir dağılımdan emin
görünmek olurdu (GK10).

## Ölçülen

- **GK10 uyarısı ölçüldü ve yanıta gömüldü.** `generator.py:342` sağlıklı K₀'ı **sınırlı
  düzgün dağılımdan** çekiyor (`rng.uniform(-K_SPREAD, K_SPREAD)`, `K_SPREAD = 0.15`).
  Düzgün dağılımın **kuyruğu yoktur**: sağlıklı bir pano yapısal olarak aykırı **çıkamaz**.
  Analitik tavan 1,349; 500 sağlıklı panoda (seed 20260918) **ölçülen en büyük |z| = 1,534**
  (sonlu örneklemde MAD gerçek değerinin biraz altında çıkar). Aykırılık eşiği **3,5** —
  sağlıklı pano eşiğin **yarısına bile** ulaşamıyor. Yani 1,6'nın üstündeki **her** eşik bu
  veride kusursuz ayrım verir ve bu, yöntemin değil **üretecin** özelliğidir. Kilitleyen
  test: `libs/panoalgo/tests/test_fleet.py::test_sentetik_filoda_saglikli_pano_asla_aykiri_cikamaz`.
  Aynı cümle `GET /fleet/peers` yanıtının `uyari` alanında da döner.
- `scripts/check_contracts.py`: "SOZLESMELER TUTARLI". `required_paths` listesine
  `/api/v1/fleet/peers` eklendi.
- Beş üreteç de `--check` ile "guncel" — bu öneri alarm kodu veya Modbus adresi
  açmadığı için hiçbirinin çıktısı değişmedi.
- Testler: `libs/panoalgo/tests/test_fleet.py`, `libs/panoalgo/tests/test_onset.py`,
  `libs/panoalgo/tests/test_detect.py` (taban kanıtı) ve
  `backend/tests/test_api_insights.py` (uç, türetme, yetersiz akran, 503).
