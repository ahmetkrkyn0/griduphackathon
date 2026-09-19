# 16 — UX Tasarımı

> **Sahip:** Kişi C · Kod: `frontend/src/`. Ekran görüntüleri: `assets/ekran/` (bkz. §5).

## 1. Tasarım yönü: "RAL 7035"

> **17 Eylül 2026 arayüz güncellemesi:** Kullanıcının yoğun kontrol merkezi kullanımına yönelik
> talebiyle nötr çalışma yüzeyleri, kompakt envanter/alarmlar ve GDZ turuncusunun küçük gezinme
> vurguları benimsendi. Aşağıdaki ilk tasarım kararları tarihsel bağlamdır; güncel uygulama ve
> araştırma [tasarım notlarında](../frontend/TASARIM-ARASTIRMASI-2026-09.md) açıklanır.
> Bölge haritasındaki il/ilçe araması, paketteki çevrimdışı sınır geometrisi ve plaka kodlarıyla
> çalışır; API sözleşmesine yeni adres alanı eklemez. Mahalle verisi bulunmadığından mahalle
> filtresi sunulmaz. İlçe adları coğrafi alanları içinde, pano noktaları ise gelen koordinatlarda
> gösterilir. Marka vurguları alarm öncelik renklerinden ayrı tutulur.

Üç yön denendi (`frontend/sketches/`, atılabilir): A) pano gövdesinin RAL 7035 açık grisi zemin
alan, ISA-101 tarzı bir kontrol odası ekranı; B) mühendislik çizim kâğıdı üzerinde canlı tek hat
şeması; C) açılışta 14 günlük "sınıra kalan süre" zaman ekseni. **A seçildi**, C'nin zaman ekseni
Filo ekranının açılış öğesi olarak entegre edildi (aşağıda §2.1).

**Güncelleme notu (14 Eylül revizyonu):** Yön adı "RAL 7035" olarak kaldı, ama zemin artık RAL 7035
grisi değil: `--bg` kullanıcı geri bildirimi üzerine 14 Eylül'de tam beyaza (`#ffffff`) çekildi
(`frontend/src/theme.css` — "grimsi RAL7035 tonu tamamen kaldirildi"; gerekçe
[`frontend/TASARIM-REVIZYONU.md`](../frontend/TASARIM-REVIZYONU.md) §11 ve §12). Yönün asıl aldığımız
kuralı — **renk yalnızca anormal durumda** — değişmedi; marka turuncusu yalnızca marka katmanında,
veri alanının dışında kalıyor (`theme.css` `--brand` yorumu).

> **Düzeltme (19 Eylül):** Yukarıdaki `#ffffff` **bugün artık doğru değil** ve bu satır bir tarih
> kaydı olarak bırakıldı. `theme.css:3` şu an `--bg: #f5f6f8` (hafif gri-mavi); tam beyaz
> yalnızca `--surface` için geçerli. Değer `frontend/src/theme.test.ts` ile kilitlendi, yani
> bir daha sessizce eskiyemez.

**Gerekçe:**
- Jüride ADM/GDZ'nin saha ve SCADA ekiplerinden kişiler olması muhtemel (rapor §9). Bu kitle her
  gün bir kontrol odası ekranı kullanıyor; ISA-101/yüksek performanslı HMI dilini (nötr/sakin zemin,
  renk yalnızca anormal durumda) tanıyorlar ve "bilinçli bir seçim" olduğunu anlıyorlar.
- B (tek hat şeması) yalnızca tek pano için anlamlıydı, filo görünümünü taşımıyordu.
- Renk körlüğüne karşı: öncelik her yerde **renk + şekil + karakter** ile gösterilir (`PrioMark.tsx`):
  P1 kare "1", P2 üçgen "2", P3 daire "3", SYS çerçeveli "S". Renk yalnızca normal dışı durumda
  kullanılır (bkz. `frontend/src/theme.css` token'ları).

## 2. Ekran envanteri (rapor §6.7)

Seviye sütunundaki **adlar bizimdir** (aşağıdaki nota bakınız), ISA-101.01'in seviye adları değildir.

| # | Ekran | Dosya | Seviye (bizim adlandırmamız) | Durum |
|---|---|---|---|---|
| 1 | Bölge haritası | `pages/BolgeHaritasi.tsx` | **1 — Filo** (coğrafi genel bakış) | Yapıldı (§3'teki kapsam notuyla) |
| 2 | Filo listesi | `pages/FiloListesi.tsx` | **1 — Filo** (açılış, "sınıra kalan süre" ekseni) | Yapıldı (TC1) |
| 3 | Pano detay — dijital ikiz | `pages/PanoDetay.tsx`, `components/OnGorunus.tsx` | **2 — Pano** (nokta seçilince 3'e iner) | Yapıldı (TC1+TC2: nokta trendi eklendi) |
| 4 | Alarm konsolu | `pages/AlarmKonsolu.tsx` | **1 — Filo** (filo geneli alarm özeti; satırdan panoya iner) | Yapıldı (TC2) |
| 5 | Trend & korelasyon | `pages/TrendKorelasyon.tsx` | **3 — Nokta** (I²–ΔT, K/K₀, çiy marjı; nokta bazlı) | Yapıldı (TC3) |
| 6 | Olay analizi (kara kutu) | `pages/OlayAnalizi.tsx` | **4 — destek/tanı** (olay sonrası inceleme/kanıt) | Yapıldı (TC3) |
| 7 | Cihaz sağlığı | `pages/CihazSagligi.tsx` | **4 — destek/tanı** (düğüm, RSSI, yedek pil, sürüm) | Yapıldı (§3'teki kapsam notuyla, TC3) |
| 8 | Mobil saha (PWA) | — | — | **Won't** (PLAN.md MoSCoW) |
| 9 | Devreye alma sihirbazı | — | — | **Won't** (PLAN.md MoSCoW) |

**Kabul kriteri karşılandı:** 9 ekranın 7'si çalışıyor (PLAN.md TC3 kabul ölçütü).

Arayüz, ANSI/ISA-101.01'in **çok seviyeli ekran hiyerarşisi** yaklaşımına göre kurgulandı; bizim
zincirimiz **Filo → Pano → Nokta → destek/tanı (kara kutu, cihaz sağlığı)**
(`frontend/TASARIM-REVIZYONU.md` §2, Emerson DeltaV Live satırı). Seviye 1 "hangi panoya bakmalıyım",
seviye 2 "bu panonun neresi", seviye 3 "bu noktanın davranışı neden anormal", seviye 4 "olaydan sonra
ne olmuştu / cihazın kendisi sağlıklı mı" sorusunu cevaplar. Bir ekran temelde tek bir seviyenin
sorusuna odaklanır, ama gerektiğinde bağlamı koruyarak bir alt seviyeye iner (Pano detayında nokta
seçilince 3'e inmesi gibi) — operatör hiçbir adımda bağlamı kaybetmez.

> **Uygunluk iddiası yok (GK3/GK10).** ISA-101.01'in tam metnine erişimimiz olmadığı için madde
> düzeyinde uygunluk iddia etmiyoruz ve "birebir karşılık" demiyoruz. Depodaki dayanak
> `GELISTIRME-BACKLOGU.md` F-18 maddesindeki tek cümle ("ANSI/ISA-101.01 ekran hiyerarşisini dört
> seviye olarak tanımlar") ve `frontend/TASARIM-REVIZYONU.md` §2'nin Emerson DeltaV Live satırıdır;
> §2 kaynak listesindeki tek ISA-101 kaynağı bir renk stratejisi yazısıdır. Seviye adları
> ("Filo / Pano / Nokta / destek-tanı") ve Alarm konsolunun seviye 1'e yerleştirilmesi **bizim
> yorumumuzdur**. Standart izi: `docs/11-standartlar-uyum.md`.

## 2.1 Filo ekranı: "sınıra kalan süre" ekseni

Açılış ekranının kahramanı bir dashboard değil, bir zaman eksenidir: paneller sorunun **ne zaman**
kritikleşeceğine göre dizilir (`components/SureEkseni.tsx`). Eksen logaritmiktir (`axisFraction`,
`lib/worklist.ts`) — yakın gelecek geniş, uzak gelecek sıkışık — çünkü operatör için "6 gün" ile
"7 gün" arasındaki fark, "60 gün" ile "61 gün" arasındakinden çok daha önemlidir. Kartlar aynı
zaman diliminde çakışırsa `layoutAxisRows` satırlara dağıtır (birim testli, `worklist.test.ts`).
"Zaman ekseni / Risk matrisi" geçişiyle ikinci bir görünüm de var (`components/RiskMatrisi.tsx`,
Y3): x = sınıra kalan süre, y = API'nin `risk_score`'u — bkz. `frontend/TASARIM-REVIZYONU.md` §7.

## 2.2 Pano detay: olay modu

Bir pano'da onaylanmamış bir P1 alarmı varken ekran "olay moduna" geçer: alarm kartının üst kenarı
kırmızıya döner, geçen süre kalınlaşır, bir "Kara kutuyu aç" kısayolu belirir; diğer bölümler
(faz karşılaştırması, trend, ölçüm özeti) soluklaşır ama kaybolmaz (Y2, `PanoDetay.tsx`, `.quiet`
sınıfı). Dijital ikiz ve karar bilgisi her zaman tam görünür kalır — bu, operatörün konum ve eylem
bilgisini kaybetmeden dikkatinin en kritik olaya yönlenmesini sağlar.

Karar bilgisi artık üç değil **dört** blok: "Neden? / **Ne doğrulanmalı?** / Ne yapmalı? /
Ne kadar acil?" (`components/AlarmNedeni.tsx`). Dördüncüsü F-10 ile eklendi ve sırada "Neden?"in
hemen altına konuldu, çünkü ikisi aynı hipotezin iki yüzü: "Neden?" baskın hipotezin bu örnekte
**görülen** kanıtlarını yazar, "Ne doğrulanmalı?" aynı hipotezin sözleşmede tanımlı olup bu
örnekte **henüz görülmemiş** kanıtlarını yazar (karşı-olgusal açıklama; `backend/app/risk.py`
`_verify` — liste hipotez tanımından yeniden türetilir, kenarın mesajına yeni alan açılmaz).
Operatöre "neyi doğrularsam teşhis kesinleşir" sorusunun cevabını verir; aynı zamanda füzyon
skoru eşleşen kanıt oranı üzerinden hesaplandığı için (`panoalgo.fusion.score`), eksik kanıt
skorun neden 100 olmadığının da açıklamasıdır. Hipotezin kanıt listesi yoksa blok hiç çizilmez —
boş bir başlık gösterilmez.

## 3. Bilinçli kapsam sınırları (dürüstlük kuralı, Bölüm C)

1. **Cihaz sağlığı** — *18 Eylül 2026'da kapandı.* Bu ekran, toplu bir "filo sağlığı" ucu
   olmadığı için görünen panoları tek tek (sınırlı eşzamanlılıkla, 6) çekiyordu. Öneri
   (`contracts/changes/2026-09-14-fleet-health-bulk.md`) üç onayı aldı ve uygulandı:
   `GET /api/v1/fleet/health` (`openapi.yaml` v1.1.0, yalnızca ekleme) ile ekran artık
   **tek istek** atıyor (`pages/CihazSagligi.tsx`). Uçun, yerini aldığı pano-başına
   çağrıdan farklı bir değer döndürmediği backend'de testle kilitli
   (`test_fleet_health_matches_panel_detail`).
   **Kalan dürüstlük sınırı:** 100+ panoda beklenen kazanç **ölçülmedi** — demo filosu
   3–20 pano ve bu ölçekte fark zaten görünmüyordu. Değişen şey **istek sayısıdır**
   (N → 1); bu bir kod özelliğidir, ölçülmüş bir gecikme iyileştirmesi değildir.
   Depodaki 1.000 pano ölçümleri backend alım/görünme p95'ine aittir, bu ekranın istek
   davranışına değil.

**Bölge haritası** (15 Eylül güncellemesi, **18 Eylül'de F-21 ile revize edildi**):
sözleşmede `lat`/`lon` zaten onaylı bir alan. Yukarıdaki önerinin il/ilçe kısmı 15 Eylül'de
**uygulanmamıştı** ve gerekçesi şuydu: `panels` tablosunda il/ilçe kolonu yok ve bu depoda
dolduracak gerçek bir kaynak da yok (GK3 — CBS içe aktarımı yapılmadı); alan açıp boş
bırakmak ya da `pano_id` önekinden il uydurmak GK10 ihlali olurdu; o iş varlık künyesi
maddesine aittir (`GELISTIRME-BACKLOGU.md` F-21).

**F-21 o işi yaptı ve itiraz üç koşulla birden karşılandı** (`contracts/changes/2026-09-18-varlik-kutugu.md`):
`il` ve `ilce` kolonları **açıldı** (göç `deploy/initdb/008_varlik_kutugu.sql`), ama (1) alan
tek başına açılmadı — doldurma yolu da açıldı: `POST /fleet/assets` doğrulanmış, `muhendis`
rolüyle korumalı ve testli bir CBS içe aktarım ucudur; (2) **uydurma yok** — `pano_id`
önekinden il/ilçe türetilmedi, `uretici` ve `seri_no` hiçbir panoda doldurulmadı; (3) boş
künye **"veri yok" diye görünür** — künyesi olmayan pano `asset: null` döner ve
`GET /fleet/assets` kapsama oranını **sayıyla** verir. **Bu teslimde demo filosunun künyesi
boştur**: uç ve şema çalışır, içe aktarılmış gerçek veri yoktur ve bu gizlenmez. Harita hâlâ
`lat`/`lon` ile çizer; il/ilçe kırılımlı harita ayrı bir maddedir (F-26). Mock veride (`api/mock.ts`) her panonun adı
zaten gerçek bir ilçe/semt (Efeler, Bornova, Söke...) olduğundan, bu ilçelerin gerçek merkez
koordinatları dolduruldu ve panolar artık gerçek enlem/boylamına göre yerel ölçekli bir konum
grafiğine yerleştiriliyor (`pages/BolgeHaritasi.tsx`). Konum, ilçe merkezi hassasiyetindedir
(gerçek trafo GPS pini değil) — bu ekranda açıkça belirtilir. Gerçek backend'den `lat`/`lon`
gelmeyen panolar (alan opsiyonel) otomatik olarak eski dağıtım-şirketi gruplamasına düşer,
böylece olmayan veri hiçbir zaman olmuş gibi gösterilmez. Ayrıntı:
[`frontend/TASARIM-REVIZYONU.md`](../frontend/TASARIM-REVIZYONU.md) §16.

Gerçek harita karosu hiçbir ekranda kullanılmaz (GK4: yığın internetten bağımsız çalışır).

## 4. Erişilebilirlik

- Tüm etkileşimli SVG noktaları (`OnGorunus.tsx`) `role="button"`, `tabIndex`, klavye (Enter/Space)
  ile de seçilebilir; odak halkası `:focus-visible` ile görünür (tema rengi).
- Grafikler (`CizgiGrafik`, `SacilimGrafik`) `role="img"` + açıklayıcı `aria-label` taşır.
- Hareket: `prefers-reduced-motion: reduce` durumunda nokta halka animasyonu (`og-halo`, `chart`
  öğeleri) durur (`theme.css`).
- **Kontrast — 19 Eylül'de yeniden ölçüldü ve bu bölüm testle değiştirildi.** Sayılar artık
  bu dosyada değil, `frontend/src/theme.test.ts` (token matematiği) ve
  `frontend/e2e/smoke.spec.ts` (gerçekten çizilen renkler, `@axe-core/playwright`) içinde
  yaşıyor. Aşağıdaki tablo o testlerin çıktısıdır, elle hesap değildir:

  | Çift | Ölçülen | WCAG AA gövde eşiği (4,5:1) |
  |---|---:|---|
  | `--ink` #202b34 / `--bg` #f5f6f8 | **13,33:1** | geçiyor, geniş marjla |
  | `--dim` #65717d / `--bg` #f5f6f8 | **4,61:1** | geçiyor, **yalnızca 0,11 ile** |
  | `--ink` / `--p3` #a37a12 (P3 rozeti) | **3,67:1** | **geçmiyor** |

  **Bu bölümün önceki hâli yanlıştı ve nasıl yanlış olduğu öğreticidir.** "Gövde ~16:1,
  ikincil ~5,8:1" yazıyordu; o iki oran `--ink` #1f2224 / `--bg` #ffffff / `--dim` #5f666b
  üçlüsüne aitti ve **bu üç değerin hiçbiri bugün `theme.css`'te yok**. Yani sayı yanlış
  hesaplanmamıştı, **eskimişti** — ve metne yazıldığı için sessizce eskidi. İkincil metnin
  AA marjı 1,30× iken **1,02×'e** indi; `--dim` bir tık daha açılırsa eşiğin altına düşer.

  **Elle hesabın göremediği şey (ölçüldü):** elle yapılan hesap zeminin her zaman `--bg`
  olduğunu varsayar. axe gerçekten çizilen rengi okur ve bu varsayımın yanlış olduğu yerde
  patladı — `/bölge` ekranındaki `.kesinti-serit` zemini `--bg` değil `#ebecee`'dir ve aynı
  `--dim` token'ı orada 4,61:1 değil **4,21:1** verir, yani **AA'nın altına düşer**.

  **Ölçülen erişilebilirlik ihlalleri — gizlenmiyor.** `@axe-core/playwright` ile WCAG 2.1 A +
  AA taraması: mock kipinde **5 düğüm**, canlı kipte **23 düğüm**; hepsi `color-contrast`,
  başka hiçbir axe kuralı ihlal edilmiyor. Ayrıntı ve düğüm listesi
  `frontend/e2e/smoke.spec.ts` başındaki blokta. Kip farkının tamamı `AppShell`'deki iki
  öğeden gelir (`.connection-pill` 4,26:1 ve `.btn-link` 2,91:1); ikisi de örnek veri
  kipinde çizilmez. Renkler bu oturumda **değiştirilmedi** — palet kararı test işi değildir —
  ama sayı artık testte kilitli, düzeltilirse test düşer ve bu tablo da güncellenmek zorunda kalır.
- Dar ekranda yatay taşmaya karşı tüm tablo/eksen içerikleri kendi `overflow-x: auto`
  kapsayıcısında (`.tbl-wrap`, `frontend/src/app.css`). **Doğrulama biçimi:** 390 px ve 1440 px
  genişlikte elle görsel kontrolden geçti (`frontend/TASARIM-REVIZYONU.md` §11). **19 Eylül
  düzeltmesi:** bu maddenin "otomatik viewport testi yok, frontend testleri `environment: node`
  ile koşar" gerekçesi artık geçersiz — `.tsx` bileşen testleri jsdom'da koşuyor ve Playwright
  depoda. Sonuç yine de **kısmen doğru**, o yüzden dar yazılıyor: e2e tezgâhı **tek bir
  genişlikte (1425 px)** koşar, çünkü o genişlik `assets/ekran/` görüntülerinin ölçüsüdür.
  **390 px doğrulaması hâlâ elle yapılıyor ve bu bir ölçüm boşluğudur.**

## 5. Ekran görüntüleri

`assets/ekran/` altında, örnek veri modunda (`npm run dev:mock`) alınmış ekran görüntüleri.

> **19 Eylül:** Bu sekiz görüntü artık elle alınmıyor — `frontend/e2e/smoke.spec.ts` üretiyor.
> Yeniden üretmek için: `cd frontend && npm run e2e`. Dosya adları ve **1425 px** genişlik
> spec'te sabittir; aşağıdaki yedi bağlantı bu yüzden kırılmaz.
>
> **Görsel regresyon karşılaştırması bilinçli olarak YOK ve bu ölçüldü:** ekran canlı saat
> (`AppShell.tsx:185-191`), göreli zaman (`format.ts:33-40`) ve `Math.random()` ile 3 sn'de bir
> oynayan örnek veri (`mock.ts:550-556`) içerir; `toHaveScreenshot()` bu depoda kararsız olurdu.
> Spec görüntüyü **üretir, karşılaştırmaz** — görüntüler kanıt değil belgeleme malzemesidir.

| Ekran | Normal | Alarm / dolu |
|---|---|---|
| Pano detay | ![Normal](../assets/ekran/02-pano-detay-normal.png) | ![Alarm](../assets/ekran/02-pano-detay-alarm.png) |
| Filo listesi | — | ![Filo](../assets/ekran/01-filo-listesi.png) |
| Alarm konsolu | — | ![Alarm konsolu](../assets/ekran/03-alarm-konsolu.png) |
| Trend & korelasyon | — | ![Trend](../assets/ekran/04-trend-korelasyon.png) |
| Olay analizi (kara kutu) | — | ![Kara kutu](../assets/ekran/05-olay-analizi-kara-kutu.png) |
| Cihaz sağlığı | — | ![Cihaz sağlığı](../assets/ekran/06-cihaz-sagligi.png) |
| Bölge haritası | — | ![Bölge](../assets/ekran/07-bolge-haritasi.png) |

Filo/Alarm konsolu/Bölge gibi filo-genelindeki ekranlarda tek bir "normal" hali anlamlı değildir
(zaten yalnızca ilgi bekleyenler öne çıkar); bu yüzden yalnızca dolu (gerçek veriyle) hali verildi.

## 5.1 3D dijital ikiz ve tasarım revizyonu (14 Eylül)

Pano detay ekranında ön görünüşün yanında **3D ikiz** görünümü var (`components/Ikiz3D.tsx`,
three.js npm'den ayrı parça olarak yüklenir, CDN yok). Aynı geometri kaynağını (`lib/panelGeometry.ts`)
ve aynı API durumlarını kullanır; seçili nokta anormalse altında 14 günlük bir zaman kaydırıcı çıkar
(geçmiş K/K₀ değerini API'nin bugünkü durum rengiyle taban grisi arasında interpolasyonla gösterir).
ADM/GDZ marka analizi, dünyadaki benzer ürünlerin incelemesi ve revize görsel sistem (ADM/GDZ
turuncu-grafit-mavi paleti; **tek font ailesi: Barlow + Barlow Semi Condensed**): kullanıcı
tarafından onaylandı ve uygulandı — bkz.
[`frontend/TASARIM-REVIZYONU.md`](../frontend/TASARIM-REVIZYONU.md) §6. Aynı oturumun sonraki
turlarında iki şey daha değişti ve bugünkü kod bu haldedir: zemin tam beyaza çekildi (§1
güncelleme notu) ve ayrı bir marka başlık fontu (Nunito) **kaldırıldı** — `@fontsource/nunito`
paketten silindi, `--display` token'ı `--cond` ile aynı yığına bağlandı
(`frontend/src/theme.css` `--sans`/`--cond`/`--display`; `frontend/TASARIM-REVIZYONU.md` §11).

## 6. Sonraki adım

KiCad şeması gibi, "toplu cihaz sağlığı" ucu da bir sonraki iterasyonun ilk maddesidir — üç onay
alırsa Cihaz sağlığı tek bir isteğe düşer (Bölge haritası zaten §3'te anlatıldığı gibi gerçek
`lat`/`lon` kullanıyor; üç onay gelirse yalnızca ilçe merkezi yerine gerçek pano konumuna geçer).
