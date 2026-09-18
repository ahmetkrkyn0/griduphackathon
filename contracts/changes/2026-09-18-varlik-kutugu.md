# 18 Eylül 2026 — Varlık künyesi: CBS tekil kodu, fider, abone sayısı ve bakım vadesi (F-21)

**Dosya:** `contracts/openapi.yaml`
**Öneren:** Kişi A (Tuna)
**Durum:** **KABUL EDİLDİ ve UYGULANDI — 18 Eylül 2026**
**Sürüm etkisi:** `1.2.0` → `1.3.0`

**Ne değişiyor:**
1. Yeni şema `AssetRegistry` — panonun CBS'den içe aktarılan künyesi.
2. `PanelSummary`'ye **üç** alan ekleniyor: `abone_sayisi`, `kritiklik`, `sonraki_bakim_at`.
   (Risk matrisinin etki ekseni ve filo listesinin bakım rozeti bunları okur.)
3. `PanelDetail`'e `asset` bloğu (`AssetRegistry`) ekleniyor.
4. İki yeni uç: `GET /api/v1/fleet/assets` (okuma, açık) ve
   `POST /api/v1/fleet/assets` (**yazma, `muhendis` rolü** — `security: [operatorToken]`).

**Neden:** `panels` tablosunda sekiz alan var ve **hiçbiri panonun kimi etkilediğini söylemiyor**:
fider yok, abone sayısı yok, kritiklik yok, bakım tarihi yok. Bunun üç somut sonucu var:
- **Risk matrisi fiilen tek boyutlu.** `frontend/src/components/RiskMatrisi.tsx` bunu kendi
  yorumunda itiraf ediyor: y ekseni "etki" değil, **risk skorunun kendisi**.
- **F-22 pano→fider eşlemesi olmadan yazılamaz** — aynı anda susan panoların *aynı fiderde*
  olup olmadığı bilinemez.
- **EPDK Madde 8/2 kesinti kaydı doldurulamaz**: mevzuatın saydığı alanlar arasında
  **"yer (il/ilçe ve tekil şebeke unsuru kodu)"** ve **"etkilenen kullanıcı sayısı"** var
  (backlog §2.1, alan listesi birebir doğrulandı). İkisi de bu depoda yok.

**Etkilenen kulvarlar:** B (şema göçü, depo, iki uç), C (risk matrisi, filo listesi, pano detayı)
**Geri uyumlu mu:** **evet.** Yalnızca ekleme. Üç yeni `PanelSummary` alanı da
`required` **değil** ve künye içe aktarılmamışsa `null` döner.

**Onaylar:** [x] A  [x] B  [x] C

---

## Birincil alan CBS tekil kodudur — ama veritabanı birincil anahtarı değil

Backlog'un "Dikkat" satırı **paralel bir varlık ana kaydı kurulmamasını** şart koşuyor.
Bunun sebebi backlog §2.5'te yazılı: *EPDK CBS usul ve esasları dağıtım panosunu zaten tekil
kodla ve kullanıcı tesisleriyle eşleştirilmiş tutmayı zorunlu kılıyor — **panonun kimliği
müşteride zaten var; biz kaynak değil tüketiciyiz**.*

Bu yüzden:
- **Ayrı bir varlık tablosu açılmadı.** Alanlar `panels` tablosuna sütun olarak girdi.
- `cbs_kodu` **UNIQUE ikinci kimliktir**, `pano_id` birincil anahtar olarak **kalır**.
  "Birincil alan" ifadesi ürün ve ekran seviyesinde birinciliktir; `pano_id` PK'sini
  değiştirmek `panel_latest`, `events`, `alarms` ve dolaylı olarak `alarm_journal`
  yabancı anahtarlarını kırardı ve hiçbir şey kazandırmazdı.
- Künyenin **nereden geldiği** kaydın içindedir: `kunye_kaynak` (hangi CBS aktarımı) ve
  `kunye_at` (ne zaman). Kaynağı yazılmayan künye kabul edilmez.

## "Alan açıp boş bırakmak GK10 ihlali olurdu" — bu itiraz karşılandı

`docs/16-ux-tasarim.md` §Bölge haritası, il/ilçe kolonlarının **bilinçli olarak
açılmadığını** yazıyordu ve gerekçesi şuydu:

> `panels` tablosunda il/ilçe kolonu yok ve bu depoda dolduracak gerçek bir kaynak da yok
> (GK3 — CBS içe aktarımı yapılmadı). **Alan açıp boş bırakmak** ya da `pano_id` önekinden
> il uydurmak **GK10 ihlali olurdu**; o iş varlık künyesi maddesine aittir (F-21).

Doküman işi açıkça F-21'e havale ediyor. İtirazın karşılanma biçimi şudur — ve **üçü birden**
gerekir, yoksa itiraz hâlâ geçerlidir:

1. **Alan tek başına açılmadı**, doldurma yolu da açıldı: `POST /fleet/assets` doğrulanmış,
   rol korumalı ve testli bir içe aktarım ucudur. Kolon artık "bir gün belki" değil,
   **tanımlı bir kaynağı olan** alandır.
2. **Uydurma yok.** `uretici` ve `seri_no` bu teslimde **hiçbir panoda doldurulmadı** ve
   demo tohumu da onları **boş bırakır** — backlog'un "üretici/seri no uydurulmaz" satırı
   harfiyen uygulandı. `pano_id` önekinden il/ilçe türetilmedi.
3. **Boş, "veri yok" diye görünür.** Künyesi olmayan pano `asset: null` döner; ekran boş
   hücre değil **"CBS'den içe aktarılmadı"** yazar. `GET /fleet/assets` ayrıca
   **kapsama oranını** (kaç panonun künyesi var) döndürür, böylece eksiklik gizlenemez.

**Bu teslimde demo filosunun künyesi BOŞTUR.** Gerçek bir CBS aktarımına erişimimiz yok
(GK3). Uç ve şema çalışır ve testlidir; içe aktarılmış gerçek veri **yoktur** ve bu
`GET /fleet/assets` yanıtında sayıyla görünür.

## Kritiklik neden bir standarttan alıntılanmadı

`kritiklik` için erişilebilir bir standart sınıflandırma **bulunamadı**; EPDK CBS usul ve
esaslarının ek tabloları kamuya açık değil. GK10 gereği erişemediğimiz bir metnin madde
numarası yazılmaz. Bu yüzden `kritiklik` **bizim tanımladığımız bir sözlük değildir**:
CBS/varlık yönetiminden **içe aktarılan bir etikettir** ve şemada dört değerle sınırlıdır
(`kritik|yuksek|orta|dusuk`) — sınır, uydurulmuş veri değil, **aktarımı doğrulamak** içindir.

Etki ekseninin **asıl** taşıyıcısı `abone_sayisi`'dır: sayılabilir, mevzuatın kendisi
(Madde 8/2) istiyor ve bir taksonomi icat etmeyi gerektirmiyor.

## Risk matrisinin itirafı ne kadar düzeldi

`RiskMatrisi.tsx`'in yorumu "kVA sabit olduğu için etki ekseni yok" diyordu. Artık:
- Künyesi **olan** panolarda y ekseni `abone_sayisi` (gerçek etki ekseni, iki boyutlu matris).
- Künyesi **olmayan** panolarda eski davranış (risk skoru) **aynen korunur** ve ekran bunu
  ayrı bir gösterimle söyler.

Yani itiraf **silinmedi, daraltıldı**: matris künye girildiği ölçüde iki boyutludur.
`docs/18-konumlandirma-ve-standart-izi.md` CIGRE TB 858 satırı ve `docs/16` §Bölge haritası
paragrafı bu değişiklikle birlikte güncellendi.

## Ölçülen

- `scripts/check_contracts.py`: "SOZLESMELER TUTARLI". `required_paths` listesine yeni iki uç
  eklendi; aynı listede **eksik olduğu fark edilen** `/api/v1/fleet/health` de eklendi
  (v1.1.0'da atlanmıştı — sözleşmede var, denetleyicide yoktu).
- Beş üreteç de `--check` ile "guncel".
- `backend/tests/test_asset_registry.py`: içe aktarım, rol koruması, kapsama oranı, künyesiz
  panonun `null` dönmesi ve **üretici/seri no'nun boş kalması** kilitli.
