# 18 Eylül 2026 — EPDK Madde 8 kesinti kaydı TASLAĞI ve kanıt bağlantısı (F-23)

**Dosya:** `contracts/openapi.yaml`
**Öneren:** Kişi A (Tuna)
**Durum:** **KABUL EDİLDİ ve UYGULANDI — 18 Eylül 2026**
**Sürüm etkisi:** `1.4.0` → `1.5.0`

**Ne değişiyor:**
1. Yeni şema `EpdkKaydi` — Madde 8/2'nin **on alanı**, her biri **durum etiketiyle**.
2. Yeni uç `GET /api/v1/outages/{outage_id}/epdk-kaydi`.

**Neden:** F-22 artık bir kesinti olayı üretiyor ama mevzuatın istediği kayıt onunla aynı şey
değil. EPDK Kalite Yönetmeliği (RG 29/12/2020, 31349 mük.) **Madde 8/2** her kesinti kaydında
şu alanları zorunlu kılıyor (alan listesi backlog §2.1'de birebir doğrulanmış):
numara, kademe, yer (il/ilçe ve **tekil şebeke unsuru kodu**), neden, sınıf,
başlama/sona erme, süre, etkilenen kullanıcı sayısı, toplam etkilenme süresi,
dağıtılmayan enerji.

**Etkilenen kulvarlar:** B (bir uç), C (bölge haritasında yazdırılabilir taslak)
**Geri uyumlu mu:** **evet.** Yalnızca ekleme.

**Onaylar:** [x] A  [x] B  [x] C

---

## Çıktı TASLAKTIR ve bu, şemanın kendisinde yazılıdır

Backlog'un "Dikkat" satırı çıktının **"TASLAK" etiketli** olmasını ve ölçmediğimiz alanların
**"elle doldurulacak"** diye işaretlenmesini şart koşuyor. Bu, yanıtın yanına iliştirilmiş bir
uyarı cümlesi **değil**, şemanın taşıyıcı yapısıdır: her alan bir **durum** taşır.

| Durum | Anlamı |
|---|---|
| `olculen` | Değer bu depodan **türetildi** ve kaynağı alanın içinde yazılı |
| `oneri` | Sistem bir **öneri** üretti; **karar değildir**, operatör onaylar veya değiştirir |
| `elle_doldurulacak` | Bu alanı **ölçmüyoruz**; boş gelir ve neden ölçemediğimiz alanın içinde yazar |

Alan **hiçbir zaman düşürülmez**. Ölçmediğimiz alanı yanıttan çıkarmak, "bu alanı ölçmüyoruz"
bilgisini de kaybettirirdi; `panel_health`'in `null` döndürüp alanı satırda tutmasıyla aynı
kural.

## On alanın hangisini ölçüyoruz — dürüst tablo

| Madde 8/2 alanı | Durum | Gerekçe |
|---|---|---|
| **Yer** (il/ilçe + tekil şebeke unsuru kodu) | `olculen` | F-21 künyesinden (`il`, `ilce`, `cbs_kodu`). **Künye içe aktarılmamışsa `elle_doldurulacak`'a düşer** — uydurulmaz. |
| **Etkilenen kullanıcı sayısı** | `olculen` | F-22'nin `abone_toplami`'ı. Yalnızca künyesi olan panolar toplanır ve **kaç panonun sayılamadığı** alanın içinde yazar. Hiçbirinin künyesi yoksa `elle_doldurulacak`. |
| **Başlama** | `olculen` | F-22 `started_at`. **Bir yaklaşımdır:** panoların sustuğu andır, enerjinin kesildiği anın kendisi gözlemlenmiyor. Bu, alanın açıklamasında yazar. |
| **Neden** | `oneri` | Tek söyleyebildiğimiz: arıza **pano içi değil, panoların yukarısında**. Bunu aynı fiderdeki eş zamanlılıktan çıkarıyoruz. Hava, ağaç, hayvan, kazı gibi bir sebep **tahmin edilmez**. |
| **Sınıf** | `oneri` | Aynı gerekçe. Mevzuatın sınıf sözlüğüne erişimimiz yok; GK10 gereği erişemediğimiz bir metnin sınıf adı yazılmaz. Öneri **kavramsaldır**, kod değil. |
| **Sona erme** | `elle_doldurulacak` | **Restorasyon anı ölçülmüyor.** Elimizdeki tek şey haberleşmenin dönüşüdür ve o da 5 dk histerezislidir — enerji dönüşü değildir. |
| **Süre** | `elle_doldurulacak` | Sona erme yoksa süre de yok. Haberleşme dönüşünden süre hesaplamak, ölçmediğimiz bir şeyi ölçmüş gibi göstermek olurdu. |
| **Toplam etkilenme süresi** | `elle_doldurulacak` | Süre × kullanıcı; süre olmadığı için üretilemez. |
| **Dağıtılmayan enerji** | `elle_doldurulacak` | Süre gerektirir. Kesinti **öncesi** yük telemetride var ve kanıt paketinde **gösterilir**, ama enerji **hesaplanmaz**. |
| **Numara** | `elle_doldurulacak` | Dağıtım şirketinin kendi kayıt numarası; bizde karşılığı yok. |
| **Kademe** | `elle_doldurulacak` | Panolarımız AG tarafındadır; kesinti **üst şebekededir** ve hangi kademede olduğunu ölçmüyoruz. "AG" yazmak yanlış olurdu. |

**Yani on alanın üçü ölçülüyor, ikisi öneri, beşi elle doldurulacak.** Bu oran çıktının
kendisinde `ozet` alanında **sayıyla** görünür.

## Yeni bir zaman çizelgesi ÜRETİLMEDİ

Backlog "72 saatlik kanıt zaman çizelgesi" diyordu; bu **yeni iş değil**:
`GET /events/{event_id}/blackbox` sözleşmede zaten var, `OlayAnalizi.tsx` yazdırılabilir
çizelgeyi üretiyor ve F-02 pencereyi **336 saate** çıkardı (`insights.py` `window_h` üst
sınırı). Madde bu yüzden *"çizelgeyi üret"* değil **"var olan çizelgeyi Madde 8 alanlarına
bağla"** olarak uygulandı: taslak, kesintiye dahil her pano için o panonun **mevcut**
kara kutu olayına `event_id` ile bağlantı verir. Çizelge kodu **kopyalanmadı**.

## Tazminat hesabına GİRİLMEDİ

GK10. Kesinti tazminatı formülü (`ÖTMSÜRE = SBSÜRE + (TKSÜRE − ESÜRE) × K × DB × OT`)
**parametrelidir** ve `SBSÜRE` bir literal tutar değildir. `scripts/tazminat_maruziyeti.py`
zaten var ve parametresiz çalıştırıldığında **hesap yapmaz, uydurmaz** — bu taslak da aynı
çizgide kalır: tazminat alanı **yoktur**.

## Ölçülen

- `scripts/check_contracts.py`: "SOZLESMELER TUTARLI", 14 uç.
- `backend/tests/test_epdk_kaydi.py`: TASLAK etiketi, alan sayısı, künyesiz panoda
  `elle_doldurulacak`'a düşme, sebep/sınıfın **öneri** kalması ve sona erme/sürenin
  **asla** doldurulmaması kilitli.
