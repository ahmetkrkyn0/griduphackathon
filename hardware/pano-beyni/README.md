# hardware/pano-beyni/ — Kenar kontrolcü donanım tasarımı

**Sahip:** Kişi C · **Sürüm:** v1 (14 Eylül 2026)

| Dosya | İçerik |
|---|---|
| [`blok-diyagrami.md`](blok-diyagrami.md) | Sistem blok diyagramı (Mermaid), fiziksel yerleşim, güç bütçesi, tasarım gerekçeleri |
| [`io-tablosu.md`](io-tablosu.md) | 16 pin/arayüzün tam listesi: sinyal, yön, seviye, izolasyon, bağlı blok |
| [`bom.csv`](bom.csv) | Malzeme listesi, gerçek üretici kodlarıyla, adet 1 ve adet 1.000 birim fiyatları |

## KiCad şeması hakkında dürüstlük notu

PLAN.md TC2 Adım 3, gerçek parça numaralarıyla bir **KiCad şeması** istiyor. Bu depo bu haliyle
`.kicad_sch` dosyası **içermiyor** — bilinçli bir karar:

- Bu geliştirme ortamında ne internet erişimi ne de kurulu bir KiCad vardı. Gerçek üretici
  sembollerini (ADM2587E, ATECC608A, ESP32-S3-WROOM-1 …) barındıran bir şemayı elle, doğrulama
  imkânı olmadan üretmek, açıldığında bozuk çıkma riski taşırdı.
- Böyle bir dosyayı "KiCad şeması" diye sunup gerçekte açılmıyor veya sembolleri eksik çıkıyor
  olması, projenin her yerde uyguladığı **dürüstlük kuralından** (Bölüm C: "simüle edilen açıkça
  simüle edilen olarak yazılır") daha kötü bir izlenim bırakırdı.
- Bunun yerine gereksinimi rapor §10'un kendisinin tanımladığı asgari seviyeyle karşılıyoruz:
  **blok diyagramı + I/O tablosu + BOM**, hepsi gerçek parça numaralarıyla ve elektriksel olarak
  tutarlı (güç bütçesi, izolasyon sınırları, konnektör sayısı I/O tablosuyla birebir eşleşiyor).

**Yapılacak (KiCad kurulu bir makineye geçildiğinde):** `blok-diyagrami.md`'deki net listesi ve
`io-tablosu.md`'deki pinout doğrudan bir KiCad projesine aktarılabilir; parça numaraları BOM'dan
sembol/footprint eşlemesiyle (SnapEDA/Ultra Librarian gibi kaynaklardan) tamamlanabilir. Bu, bir
sonraki iterasyonun ilk adımıdır (`docs/16-ux-tasarim.md` ve `STATUS.md`'de not edilmiştir).

## Diğer donanım dizinleri

- [`../yerlesim/`](../yerlesim/) — EK-II/14 üzerinde sensör yerleşimi (SVG)
- [`../mekanik/`](../mekanik/) — DIN kutu mekanik tasarımı (OpenSCAD kaynağı)
- [`../sensor-dugumu/`](../sensor-dugumu/), [`../pd-karti/`](../pd-karti/) — Could seviyesi. **17 Eylül'de
  ikisi de bu dizinle aynı üçlüye kavuştu** (blok diyagramı + I/O tablosu + BOM); sensör düğümü ayrıca bir
  enerji ve termal hesap taşır. Yani artık "kavramsal" değiller — ama bu dizin gibi onlar da **veri sayfasıyla
  doğrulanmadı ve üretilmedi** (`docs/19` §3)
