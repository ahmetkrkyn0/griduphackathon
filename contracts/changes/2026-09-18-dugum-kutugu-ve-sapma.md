# 18 Eylül 2026 — Düğüm/sensör kütüğü ve ardışık sapma tespiti (F-31)

**Dosyalar:** `contracts/alarm-codes.yaml`, `contracts/openapi.yaml`
**Öneren:** Kişi A (Tuna)
**Durum:** **KABUL EDİLDİ ve UYGULANDI — 18 Eylül 2026**
**Sürüm etkisi:** `alarm-codes.yaml` `3` → `4` · `openapi.yaml` `1.6.0` → `1.7.0`

**Ne değişiyor:**
1. `alarm-codes.yaml`: yeni alarm kodu **`ALM-DQ-DRIFT`** (bit 22, `layer: "L-1"`, `prio: SYS`)
   ve dört yeni eşik: `dq_drift_samples`, `dq_drift_rise_k`, `dq_drift_max_slope_growth`,
   `dq_drift_persist_samples`.
2. `openapi.yaml`: `NodeRegistry` / `NodeFleet` / `NodeImport` / `BlindNodes` şemaları ve üç uç —
   `GET /api/v1/fleet/nodes`, `POST /api/v1/fleet/nodes` (**`muhendis` rolü**),
   `GET /api/v1/fleet/nodes/blind`.

**Etkilenen kulvarlar:** A (üreteç, L-1 kuralı), B (göç, üç uç), C (alarm metni)
**Geri uyumlu mu:** **evet.** Yalnızca ekleme. Yeni bit 22, Modbus `alarm_bits_16_31`
register'ının **zaten var olan** 32 bitlik alanına düşer; harita değişmedi.

**Onaylar:** [x] A  [x] B  [x] C

---

## `mqtt-telemetry.schema.json` ve `modbus-map.yaml` DEĞİŞMEDİ

Backlog bu maddenin "tek başına donmuş sözleşmenin **üç** dosyasına birden dokunduğunu"
söylüyordu. Uygulamada **iki** dosya yetti ve bu bir kaçamak değil, doğru olandı.

`t_conn[]` ve `health` için `additionalProperties: false` tanımlı: kenara düğüm kimliği
alanı açmak mesajı reddettirir ve zinciri (şema → Modbus haritası → üretilmiş dokümanlar →
firmware başlığı) tetiklerdi. Gerek yoktu, çünkü **kimlik telemetriye ait değil**:

- Seri no, üretim partisi, kalibrasyon vadesi ve nokta↔düğüm eşlemesi **10 saniyede bir
  akması gereken veriler değildir**; bunlar F-21'in künyesiyle aynı cinsten **kütük**
  verileridir ve bir kez içe aktarılır.
- "Hangi düğüm kör" sorusu ise **zaten yayınlanan** veriden türetilebilir: kenar nokta
  başına kalite bitlerini (`t_conn[].q`) gönderiyor, kütük nokta→düğüm eşlemesini tutuyor.
  Merkez ikisini birleştirip **fiziksel parçayı adlandırıyor**. Bu, F-10'un `_verify`
  çözümünün aynısıdır: liste kenardan taşınmaz, merkezde yeniden türetilir.

Modbus haritası da değişmedi: alarm bitleri `alarm_bits_0_15` + `alarm_bits_16_31` olarak
**32 bitlik** bir alanda yaşıyor ve bit 22 oraya sığıyor. `check_contracts.py` bunu
zaten denetliyor (`max_bit >= live_regs * 16` kontrolü).

## Ayrım: ölçüm noktası kimliği zaten VARDI

Backlog "düğüm kimliği hiçbir yerde yok" diyor; bu **fazla geniş**. Ölçüldü:

| Ne | Durum |
|---|---|
| **Ölçüm noktası** kimliği | **VARDI** — `t_conn[].pt`, donmuş şemada sabit regex; `q` kalite bitleri de nokta bazında. `docs/05` §10 sapmayı nokta adıyla teşhis edebiliyordu |
| **Fiziksel düğüm/sensör** kimliği | **YOKTU** — `health` yalnızca `nodes_ok` / `nodes_total` **sayılarını** taşıyor |

Bu ayrım yapılmasaydı var olan bir yetenek yeniden inşa edilirdi. Maddenin gerçek işi
*"bir düğüm kaybolduğunda hangi fiziksel parçanın gittiğini söyleyebilmek"*tir; göç
`010_dugum_kutugu.sql` ve `GET /fleet/nodes/blind` tam olarak onu yapar.

## "İzlenebilir ölçüm" iddiası KURULMADI

Metrolojik izlenebilirlik akredite bir kalibrasyon zinciri ister; bu depoda yok (GK3).
Yapılan yalnızca **kütük ve vade takibidir** ve `GET /fleet/nodes` bunu kendi `uyari`
alanında söyler. **Sertifika numarası alanı bilerek açılmadı**: dolduracak gerçek bir
kaynak olmadan alan açmak GK10 ihlali olurdu — F-21'in "üretici/seri no uydurulmaz"
satırıyla aynı kural. Demo filosunun düğüm kütüğü **boştur** ve bu `kapsama` alanında
sayıyla görünür.

## Sürüklenme: önce üretecin kendisi düzeldi

Backlog "sensör sürüklenmesini **üretiyoruz** ama tespit eden hiçbir kural yok" diyordu.
Ölçüldüğünde premisin **ilk yarısı da tutmuyordu**:

`PanelSimulator.set_sensor_fault` aynı arızayı her çağrıda yeniden kuruyor ve yaşını
**sıfırlıyordu**. Senaryo yürütücüsü `_inject`'i **her adımda** çağırdığı için sürüklenme
hiç birikmiyordu: 112 saatlik enjeksiyon penceresi boyunca kayma **tek adımlık 0,5 K'da
çakılı** kalıyordu. Yani "sürüklenme üretiyoruz" ifadesi fiilen doğru değildi.

İki düzeltme yapıldı:
1. **Aynı arızayı yeniden kurmak yaşı sıfırlamıyor** (idempotentlik).
2. **Hız 2,0 → 0,1 K/saat.** 2,0 K/h fiziksel değildi: 112 saatte 224 K eder ve senaryoyu
   bir sensör arızasından **termal arızaya** çevirirdi — ölçüldü, `ALM-THR-TERM-ALM` 345 kez
   çıkıyordu ve S8'in `not_expect` kısıtını ihlal ediyordu. 0,1 K/h ölçülerek seçildi:
   termal alarm yok, `ALM-K-ALM` yok, ama K/K₀ 1,49'a şişiyor ve belgelenmiş belirti
   (eşik aşılmadan sahte kalan ömür tahminleri) **üretiliyor**.

Sonuç `docs/12` §4.3'te görünür: S8'in yanlış-alarm sayısı **99 → 183** tahmin, **89 → 86**
`ALM-TTL-14D`. docs/12 üretilmiş bir dokümandır ve yeniden üretildi; **yalnızca S8 satırı
değişti**, diğer dokuz senaryo bit bit aynı kaldı.

## Sürüklenme kuralının ayracı FİZİKTİR

Isıl model `dT = a·I² + b`; fizik `b = 0` der (yük yoksa ısınma yok). İki bozulma bu iki
katsayıyı **ayrı ayrı** bozar:

- **Bağlantı** bozulursa ısıl direnç büyür: `a` büyür, `b` sıfırda kalır.
- **Sensör** kayarsa ölçüme sabit ofset eklenir: `b` büyür, `a` değişmez.

Kural pencereye en küçük kareler uydurur ve **yalnızca `b`'nin** büyümesine bakar; `a` da
büyümüşse kayma **ilan edilmez**. Bu kısıt olmadan ölçüldü: gerçek gevşek bağlantıda (S1)
20 kez sahte `ALM-DQ-DRIFT` çıkıyordu. **Gerçek bir arızayı "kalibrasyon şüpheli" diye
raporlamak en kötü yanlış yöndür.**

İlk tasarım "düşük yük tabanının yükselmesine" bakıyordu ve S1'de **96** yanlış pozitif
verdi — çünkü K üç katına çıkınca düşük yük tabanı da üç katına çıkar. Kesişim ayracı
bunu kapattı. O tasarımdan kalan `dq_drift_floor_quantile` eşiği sözleşmeye **hiç
girmedi**: aynı değişiklik içinde kaldırıldı, çünkü kullanılmayan bir eşik sözleşmede
durursa okuyan üç kulvardan biri onu bir gün "uygulanmış" sanır.

Ek iki koruma:
- **Uyarım şartı:** I² pencerede yeterince değişmezse regresyon kötü koşullanır ve `a` ile
  `b` ayrılamaz; böyle bir pencerede karar **verilmez** ("kayma yok" denmez, ölçülmedi).
  Aynı ölçüt ve aynı sözleşme anahtarı: `excitation_min_cv_i2`.
- **Süreklilik:** koşul `dq_drift_persist_samples` kadar **ardışık** örnekte sağlanmalı.
  Ölçüldü: yanlış pozitiflerin en uzun ardışık koşusu **9** (S1) ve **7** (S2 yük basamağı);
  gerçek kayma **190** ardışık örnek sürüyor. 16 (= 4 saat) ikisinin arasında ve her iki
  tarafa geniş pay bırakıyor.
- **Daha özgül tanı kazanır:** donmuş veya yerinden düşmüş sensöre kayma kodu **asılmaz**
  (ölçüldü: bastırma olmadan donmuş nokta 97, düşmüş nokta 49 sahte kayma üretiyordu).

## Ölçülen

- **Ayrım, on senaryonun hepsinde:** `S8_sensor_fault`'ta yalnızca `DSYA4_L3`, 230 kez
  (seed 42), enjeksiyondan **26,25 saat** sonra. Diğer **dokuz** senaryoda — gerçek gevşek
  bağlantı `S1_loose_conn` ve sağlıklı taban `S0_normal` dahil — **sıfır** yanlış pozitif.
  Kilitleyen test: `libs/panoalgo/tests/test_drift.py` (10 senaryo parametrik).
  **GK10:** bu ayrım tek bir yörüngeden (n = 1) ve sentetik veriden gelir; üreteç kaymayı
  sabit hızla ve tek noktaya enjekte eder. Saha başarımı **değildir**.
- `scripts/check_contracts.py`: "SOZLESMELER TUTARLI" — 23 kod (bit 0-22), 44 eşik, 17 uç.
- **Beş üreteç de "guncel"**: `gen_alarm_doc` ve `gen_iec104_doc` yeniden üretildi (yeni kod
  ikisinin de çıktısında görünür); `gen_modbus_doc`, `gen_grafana_dashboards` ve
  `panoalgo.genmap` değişmedi (bit 22 var olan register alanına düştü).
- Göç `010_dugum_kutugu.sql` ayakta olan veritabanına elle uygulandı ve **idempotent**
  olduğu iki kez koşturularak doğrulandı.
- Testler: `backend/tests/test_node_registry.py` (16), `libs/panoalgo/tests/test_drift.py` (18).
