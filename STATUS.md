# Kişi C — Durum Takibi (Arayüz, Donanım Tasarımı, Teslim)

> **OTURUM SONUCU:** PLAN.md'de Kişi C'ye açıkça atanmış tüm kutucuklar işaretlendi
> (TC1–TC3, T4.5–T4.7, T5.1–T5.2). Tüm değişiklikler `berke/frontend` dalına commit edilip
> `origin`'e push edildi (son commit `5314e10`). Kalan tek açık uç, C'nin kontrolü dışında:
> Kişi A'nın kulvarı (§0.1).

> Bu dosya yalnızca C'nin (Berke) kendi ilerleme takibi içindir; PLAN.md'nin yerine geçmez.
> PLAN.md'de yalnızca kutucuk işaretleme ve "Günlük Kayıt" satırı ekleme yapılır (kural: ortak dosya).
> Her önemli adımdan sonra bu dosya güncellenir. Dal: `berke/frontend` (origin'e push edildi).

**Son güncelleme:** 14 Eylül 2026 akşam (2D Ön görünüşe de 3D ile eş düzey gerçekçilik, §16).
**Son commit:** 2D SVG'ye durum LED'leri (TVOC-2 gerçek sağlık durumuna bağlı), devre kesici
anahtar kolları, kondansatör tahliye izi eklendi.

## 16. Oturum 6 devamı — "2D pano çizimleri için de bir şeyler yaptın mı"

Kullanıcı §15'teki 3D gerçekçilik geçişinden sonra haklı bir soru sordu: 2D "Ön görünüş"
(`components/OnGorunus.tsx`) hâlâ dokunulmamıştı. Aynı detaylar 3D ile eş düzeyde SVG'ye eklendi:

- Durum LED'leri (TVOC-2/Pano Beyni/Modem) — TVOC-2'ninki `tvoc.prot_health_ok`'a bağlı, 3D'deki
  gibi yeşil/kırmızı. `OnGorunus`'a yeni `tvoc` prop'u eklendi.
- DSYA devre kesicilerine anahtar kolu + pencere (yalnızca gerçek breaker'larda).
- Kompanzasyon kondansatörlerine basınç tahliye izi, DIN raya ince kenar parlaması.

Ayrıntı: `frontend/TASARIM-REVIZYONU.md` §14. Doğrulama: tsc temiz, 71/71 test yeşil, build
başarılı; ADM-00014 (yeşil LED) ve GDZ-00231 (kırmızı LED) ile görsel kontrol, 390 px mobilde
yatay taşma yok. İki ekran görüntüsü kullanıcıya doğrudan gönderildi (SendUserFile).

## 15. Oturum 6 devamı — "panoları daha gerçekçi yap"

Kullanıcının isteği üzerine `components/Ikiz3D.tsx`'teki 3D sahneye, harici model/doku dosyası
eklemeden (GK4: internet yok), yalnızca prosedürel three.js geometrisiyle gerçekçilik detayları
eklendi:

| Detay | Ne eklendi |
|---|---|
| DIN ray | Tek düz kutu yerine 3 katmanlı, gerçek TS35 profiline yakın siluet |
| Durum LED'leri | TVOC-2 (API'nin `tvoc.prot_health_ok` alanına bağlı — yeşil/kırmızı, kural 10 ile çatışmaz), Pano Beyni, Modem (dekoratif titreşim) |
| DSYA devre kesicileri | Her faz yüzeyine anahtar kolu + pencere — gerçek MCB görünümü |
| Kablolar | Düz silindir yerine `TubeGeometry` ile hafif sarkan/bükülen tüpler |
| Kablo pabuçları / kondansatörler | Cıvata başı ve kıvrım bantları eklendi |
| Malzemeler | RAL 7035 gövdeye clearcoat, bakır/DIN raya daha metalik değerler, yumuşak dolgu ışığı |

Ayrıntı: `frontend/TASARIM-REVIZYONU.md` §13. Doğrulama: tsc temiz, 71/71 test yeşil, build
başarılı (Ikiz3D parçası 529 kB, tembel yükleniyor). ADM-00014 (sağlıklı) ve GDZ-00231 (arızalı
TVOC-2, kırmızı LED) ile görsel kontrol yapıldı. **İki ekran görüntüsü kullanıcıya doğrudan
gönderildi (SendUserFile)** — bu oturumdaki "önce göster, sonra anlat" dersi uygulandı (§12).

## 14. Oturum 6 devamı — "hâlâ grimsi": iki kök neden

Kullanıcı §13'ün hemen ardından: "arkaplanlarda hala o grimsi arkaplan var artifactta da öyle
oraları istediğim gibi beyaz + turuncu detaylar yapmamışsın."

1. `--bg` (`#F7F7F5`) yeterince beyaz değildi, `--surface` (tam beyaz) yanında hâlâ grimsi
   okunuyordu → `--bg` de `#FFFFFF`'e çekildi; kartlar artık yalnızca kenarlık+gölgeyle ayrışıyor.
   Turuncu parıltı iki katmana çıkarıldı (yakın+belirgin / geniş+soluk) ki tam beyazda kaybolmasın.
2. **Karşılaştırma Artifact'ının kendi CSS'i hiç güncellenmemişti** — ilk yazıldığı andaki eski
   token değerlerini (`#e4e5e2` vb.) sabit kopyalamıştı, uygulamanın `theme.css`'i sonra
   değiştikçe bu kopya senkronize edilmemişti. Bu yüzden "artifactta da öyle" haklı bir tespitti.
   Artifact'ın token'ları uygulamayla birebir eşitlendi, figür/chip kartlarına gölge eklendi.

Ayrıntı ve alınan ders: `frontend/TASARIM-REVIZYONU.md` §12. Doğrulama: tsc temiz, 71/71 test
yeşil, build başarılı, 1440px görsel kontrol. `assets/ekran/`'daki 8 dosya beşinci kez yeniden
çekildi, Artifact tekrar yayınlandı (v4).

## 13. Oturum 6 devamı — zemin ve tipografi: tek standart

Kullanıcı §12'deki düzen revizyonunun hemen ardından: "arkaplanı biraz daha aç beyaz tonları belki
turuncu hafif fade efekti olabilir backgroundda şu grimsi renkten kurtul bir de fontta tek bir
standarttan ilerleyelim."

- `--bg` `#E4E5E2` → `#F7F7F5`, `--surface` → `#FFFFFF`, `--well`/`--line` orantılı açıldı.
- `body`'ye üst banttan sarkan %8 opaklıkta turuncu `radial-gradient` eklendi.
- `--display` token'ı Nunito'dan Barlow Semi Condensed'e (yani `--cond` ile aynı) çevrildi;
  `@fontsource/nunito` paketten kaldırıldı. Ürün artık tek font ailesi (Barlow ailesi, iki
  genişlik) kullanıyor.
- `assets/ekran/`'daki 8 dosya dördüncü kez yeniden çekildi; önce/sonra karşılaştırma Artifact'ı
  (bkz. §12) güncellendi.

Ayrıntı: `frontend/TASARIM-REVIZYONU.md` §11. Doğrulama: tsc temiz, 71/71 test yeşil, build
başarılı, 1440px/390px görsel kontrol.

## 12. Oturum 6 — Kullanıcı geri bildirimi: "tasarımda değişiklik göremiyorum" + düzen revizyonu

Kullanıcı iki ayrı geri bildirim verdi:
1. "Ben tasarımda bir değişiklik göremiyorum... GDZ'nin turuncusunun kullanıldığı bir tasarım yok
   benim önümde." → **Kök neden: hiçbir görsel paylaşılmamıştı**, yalnızca metinle "doğrulandı"
   denmişti. Düzeltme: önce/sonra karşılaştırma sayfası hazırlanıp Artifact olarak yayınlandı
   (üç ekranın gerçek ekran görüntüleriyle), ardından turuncu kullanımını artırıp artırmama kararı
   `AskUserQuestion` ile soruldu → **"Daha belirgin yap" seçildi.**
2. Aynı mesajın hemen ardından (turuncu artırma işi sürerken): "sayfa düzeni renkleri falan her
   şeyi aynı bırakmışsın sen... global projelerden ilham al dedim." → **Haklı bir eleştiri**: R1–R5
   yalnızca CSS token'larını (renk/tipografi) değiştirmişti, sayfa düzenini ve bileşen yapısını hiç
   değiştirmemişti.

**Yapılan (tek geçişte, her iki geri bildirime birden yanıt):**

| İş | Durum |
|---|---|
| Önce/sonra karşılaştırma Artifact'ı (3 ekran, gerçek görseller) | ✅ Yayınlandı, kullanıcıya link verildi |
| Turuncuyu belirginleştirme (birincil buton, aktif sekme, kart kenarı) | ✅ Uygulandı |
| **Kart + gölge sistemi** (`--radius`/`--shadow` token'ları, tüm kartlara uygulandı) | ✅ Uygulandı |
| KPI şeridi → büyük-sayı karoları (GE Vernova/ABB tarzı) | ✅ Uygulandı |
| İş listesi → kart ızgarası (Hitachi APM tarzı, tek sütunlu liste değil) | ✅ Uygulandı |
| Pano detayda "sağlık şeridi" split'ten önce, her zaman görünür (ABB SWICOM tarzı) | ✅ Uygulandı |
| `.qa`/`.console-card` "kart içinde kart" sorunu giderildi | ✅ Uygulandı |
| Ekran görüntüleri 3. kez yeniden çekildi, karşılaştırma Artifact'ı güncellendi | ✅ Uygulandı |

Ayrıntı, gerekçe tablosu ve bilinçli sınır (`.console-filters`'a turuncu eklenmedi, gerekçesi):
`frontend/TASARIM-REVIZYONU.md` §10.

**Ders (kendime not):** Görsel bir değişikliği yalnızca terminaldeki otomatik tarayıcı kontrolüyle
"doğruladım" demek yetmez — kullanıcı hiçbir şey görmeden ikna olmasını beklemek doğru değildi.
Bundan sonra görsel değişikliklerde ekran görüntüsünü veya Artifact linkini doğrudan paylaşmak
gerekiyor.

## 11. Oturum 5 — Tasarım revizyonu uygulaması: R5 (14 Eylül, "Devam et")

Kullanıcı yine "Devam et" dedi; planın son adımı R5 (ekran görüntülerini yeni paletle yenileme)
uygulandı. **`frontend/TASARIM-REVIZYONU.md` planının tamamı (R1–R5) artık uygulanmış durumda.**

`assets/ekran/`'daki 8 dosyanın hepsi aynı rota/pano/sekme kombinasyonlarıyla (1440×900, mock
verisi) yeniden çekildi ve eskilerinin üzerine yazıldı; tek tek görsel olarak kontrol edildi
(turuncu kimlik bandı, grafit plaka, yeni mavi/turuncu tonlar, olay modu, risk matrisi hepsi
doğru görünüyor). `docs/16-ux-tasarim.md`'ye §2.1 risk matrisi notu ve yeni §2.2 (olay modu) eklendi.
Ayrıntı: `frontend/TASARIM-REVIZYONU.md` §8.

**Bu, kullanıcının 14 Eylül öğleden sonra başlattığı tasarım revizyonu talebinin tamamının
kapanışıdır** (ADM/GDZ marka analizi → global araştırma → revize plan → R1 token/tipografi → R2
marka katmanı → R3 Y6+Y1 → R4 Y2+Y3 → R5 ekran görüntüleri). Sıradaki iş, önceki oturumlarda
not düşülen ekip riskine (§0.1, A kulvarı) veya PLAN.md'de C'ye kalan başka bir maddeye bağlı.

## 10. Oturum 4 — Tasarım revizyonu uygulaması: R4 (14 Eylül, "Devam et")

Kullanıcı "Devam et" dedi; planın §5'inde R3'ten sonra sıradaki adım olan R4 (Y2 olay modu, Y3 risk
matrisi) uygulandı.

| İş | Durum |
|---|---|
| Y2 — Olay modu | ✅ `AlarmNedeni.tsx` (P1+onaysızda kırmızı kart kenarı, kalın kırmızı geçen süre, kara kutu kısayolu), `PanoDetay.tsx` (`.quiet` ile destekleyici bölümler soluklaşır) |
| Y3 — Risk matrisi | ✅ Yeni `components/RiskMatrisi.tsx`, Filo ekranında "Zaman ekseni / Risk matrisi" geçişi |
| Mock veri düzeltmesi (yan bulgu) | ✅ `mock.ts` `EVENTS`'e eksik olan `EVT-51` (GDZ-00231 P1 koruma sağlığı) eklendi |

**Kararlar (öneri seçilerek, dürüstlük kuralı gereği plan metninden sapma):**
1. **Y3'te "etki" ekseni `pano_type` (kVA) değil `risk_score`.** Uygulama sırasında fark edildi:
   sözleşmede filodaki **tüm panolar aynı `pano_type`** değerine sahip (1600 kVA, tek ürün kapsamı).
   Sabit bir alanı değişken bir "etki" ekseni gibi göstermek yanıltıcı olurdu; bunun yerine gerçekten
   panodan panoya değişen ve API'nin ürettiği `risk_score` (0–100) kullanıldı. Ayrıntı:
   `frontend/TASARIM-REVIZYONU.md` §7.
2. **"Sağ üst köşe" → "sol üst köşe" düzeltmesi.** İlk plan taslağında bir yön hatası vardı (x ekseni
   soldan sağa zaman arttığı için en acil+riskli köşe sol üsttür, sağ üst değil); uygulama sırasında
   düzeltildi.
3. **Y2, ayrı bir bileşen yerine mevcut `AlarmNedeni.tsx`'e gömüldü** — "olay kartı" zaten oydu,
   yeni bir kart eklemek yinelenme yaratırdı.

**Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı. Tarayıcıda: Filo risk
matrisinde noktaya tıklayınca doğru panoya gidiyor; GDZ-00231 ve Alarm konsolunda P1 kartının kırmızı
kenarı + "Kara kutuyu aç" bağlantısı (artık gerçek EVT-51 verisine gidiyor) doğrulandı; 390 px mobilde
risk matrisi görünümü (varsayılan) yatay taşmasız çalışıyor.

## 9. Oturum 3 — Tasarım revizyonu uygulaması: R1–R3 (14 Eylül, kullanıcı onayı sonrası)

Kullanıcı `TASARIM-REVIZYONU.md`'yi onayladı ("Onaylıyorum"). Planın §5'inde tanımlanan sırayla R1–R3
uygulandı; R4 (olay modu, risk matrisi) ve R5 (ekran görüntüsü yenileme) özellik dondurmaya kadar
zaman kalırsa yapılacak.

| İş | Durum |
|---|---|
| R1 — Token'lar + Nunito | ✅ `theme.css` (`--brand`, `--brand-deep`, güncellenmiş `--plate`/`--ours`/`--p2`/`--sys`/`--bg`/`--surface`/`--ink`), `@fontsource/nunito` |
| R2 — Marka katmanı (kimlik bandı, ürün işareti, plakalar, boş durumlar) | ✅ `App.tsx` (`BrandMark`), `app.css`, favicon |
| R3 — Y6 (onaylanınca duran hareket) + Y1 (3D zaman kaydırıcı) | ✅ `OnGorunus.tsx`, `Ikiz3D.tsx`, `PanoDetay.tsx` |
| Sabit kodlanmış eski palet renkleri (grafikler) | ✅ `PanoDetay.tsx`, `TrendKorelasyon.tsx`, `OlayAnalizi.tsx` güncellendi |

**Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı. Tarayıcıda ADM-00014
(3D zaman kaydırıcı sürüklenerek gri↔turuncu interpolasyonu doğrulandı), GDZ-00231, ADM-00301 (boş
durum/`.calm`), GDZ-00088 sayfaları görsel + konsol kontrolünden geçti; 390 px mobil genişlikte yatay
taşma yok. Onayla butonuna basılıp Y6 canlı test edildi: alarm onaylandıktan sonra hem 2D
(`og-halo`) hem 3D halka animasyonu durdu, nokta rengi (durum) değişmeden kaldı.

**Karar (öneri seçilerek):** Y1'in "geçmişte griden turuncuya" görselleştirmesi, yeni bir eşik
icat etmeden yapıldı — geçmiş `k_ratio` değeri, API'nin BUGÜN verdiği durum rengi ile 1.0 taban
grisi arasında **oran olarak** interpolasyona tabi tutuluyor (iki ucu da API belirliyor, aradaki
oranı biz hesaplıyoruz). Ayrıntı ve gerekçe: `frontend/TASARIM-REVIZYONU.md` §6, kod içi yorum
(`components/Ikiz3D.tsx` başlığı).

## 8. Oturum 2 — 3D ikiz entegrasyonu ve tasarım revizyonu (14 Eylül öğleden sonra)

Kullanıcı talebi: 3D ikizi uygulamaya entegre et; ADM/GDZ marka tasarımını ve dünyadaki benzer
ürünleri (yenilikçi olanlar dahil) araştır; revize bir tasarım planı çıkar.

| İş | Durum |
|---|---|
| 3D ikiz, Pano detayda "Ön görünüş / 3D ikiz" geçişi (`components/Ikiz3D.tsx`) | ✅ tsc temiz, 71/71 test, build OK, tarayıcıda ADM-00014 ve GDZ-00231 ile doğrulandı, konsol temiz |
| ADM/GDZ marka analizi (canlı sitelerin CSS token'ları ve logo SVG'leri) | ✅ `frontend/TASARIM-REVIZYONU.md` §1 |
| Global araştırma (ISA-101, ABB, Schneider, Siemens, Hitachi, GE Vernova, Emerson, Honeywell, Cognite, Tesla…) | ✅ aynı dosya §2 |
| Revize tasarım planı (token'lar, tipografi, marka katmanı, 7 yenilik, uygulama sırası) | ✅ yazıldı, **kullanıcı onayı bekliyor**; görsel sistem henüz değiştirilmedi |

**Kararlar (öneri seçilerek):**
1. **React Three Fiber yerine doğrudan three.js.** Spike kodu doğrudan taşınabildi; ek bağımlılık
   (R3F + drei) gerekmedi. Sahne tek bir `buildScene` fonksiyonunda, React yalnızca veri ve düğmeleri
   yönetiyor.
2. **3D tembel yüklenen ayrı parça.** `Ikiz3D` parçası 509 kB (gzip 130 kB); ana paket 229 kB'de kaldı.
   Vite'in 500 kB parça uyarısı bu parça için bilinçli olarak kabul edildi (yalnızca 3D açılınca iner).
3. **Varsayılan görünüm 2D**, seçim `localStorage`'da hatırlanır. WebGL/paket hatasında sayfa çökmez.
4. **3D geometri 2D ile aynı kaynaktan** (`pointPos3d`, birim testli). Spike'taki ayrı koordinatlar atıldı.
5. **Marka logoları uygulamaya gömülmeyecek** (kullanım izni bizde değil); kimlik renk, Nunito ve şirket
   adı metniyle taşınacak.
6. **Marka turuncusu (#FF671D) ile P2 alarm turuncusu çakışıyor** → plan "mekânsal ayrım + şekil + ton
   farkı" öneriyor (turuncu yalnızca marka katmanında, P2 `#D9530F`). Ayrıntı plan §3.2.

## 0.1 ⚠️ Ekip riski (öneri seçilerek not düşüldü, aksiyon ekipte)

**A kulvarı (`libs/panoalgo/`, `firmware/`, `sim/panosim.py`, `mpr53cs_sim.py`, `tvoc2_sim.py`,
`docs/05`, `docs/12`) bu tarih itibarıyla depoda hâlâ yok** — `sim/` yalnızca bir yer tutucu
(`hello_publisher.py`) içeriyor, `docs/` klasöründe 17 dosyadan yalnızca A'ya ait 2'si eksik.
B ve C tamamlandı ve örnek veriyle uçtan uca çalışıyor; ama **gerçek Docker yığınında "uçtan uca"
demo ve `demo/senaryo/s0-s6` A'nın işi olmadan gösterilemez.** Özellik dondurmaya (17 Eylül 23:59)
3 gün var. Bu, C'nin çözebileceği bir şey değil (dosya sahipliği kuralı); PLAN.md Günlük Kayıt'a
ve bu bölüme not düşüldü ki ekip bugün görüp aksiyon alsın.

## 0. Bu oturumun hedefi

Kullanıcı talebi (özet): C'nin kalan tüm frontend/donanım/teslim görevlerini bitir. Başka daldan
bir şey gerekirse mevcut daldan yeni bir dal aç, birleştirmeyi orada yap. Karar gereken yerlerde
önerilen seçeneği uygula. Her şeyi not düş, bu dosyayı sürekli güncelle.

## 1. Genel ilerleme

| Faz | Durum |
|---|---|
| TC1 (Filo listesi, pano detay, WS akışı) | ✅ Tamamlandı (önceki oturum) |
| Entegrasyon (`origin/ahmet/backend` merge) | ✅ Tamamlandı |
| TC2 (Alarm konsolu, dijital ikiz trendi, donanım şeması başlangıcı) | ✅ Tamamlandı, commit `f98058b` |
| TC3 (Trend/korelasyon, kara kutu, cihaz sağlığı, bölge haritası, donanım dok.) | ✅ Tamamlandı, commit `f98058b` |
| Faz 4/5/6 (README, ekran görüntüleri, demo betikleri, sunum) | ⏳ Devam ediyor |

## 2. Yapılan entegrasyon

- **`int/pull-ahmet-backend` dalı** `berke/frontend`'den açıldı, `origin/ahmet/backend` içine
  merge edildi (çakışmasız, 58 dosya), sonra `berke/frontend`'e geri merge edildi. Artık
  `berke/frontend` şunları da içeriyor:
  - `backend/app/api/insights.py` → `GET /panels/{id}/series`, `GET /events/{id}/blackbox`,
    `GET /fleet/kpi` (TC3'ün kullandığı uçlar).
  - `backend/app/scada/*`, `docs/02/03/04/07b/09/15/17`, `loadtest/`, `scripts/gen_*` — B'nin işi.
- **Doğrulama notu:** Bu makinede global `starlette` sürümü (`1.0.0`) `fastapi==0.115.*` ile
  uyumsuz olduğu için backend testleri toplanamıyor. **Merge öncesi `main`'de de var** — benim
  değişikliğimden kaynaklanmıyor. B'ye bildirilmeli.

## 3. TC2 — tamamlandı

Alarm konsolu (`/alarmlar`), dijital ikizde nokta tıklanınca gerçek zaman serisi trendi, yeni API
uçları (`alarms`, `shelve`, `series`, `blackbox`), `assets/ek2-14-pano.svg`,
`hardware/pano-beyni/` (blok diyagramı + I/O tablosu + BOM + README), `docs/16-ux-tasarim.md`.
Ayrıntı: PLAN.md TC2 bölümü + Günlük Kayıt (14 Eylül).

## 4. TC3 — tamamlandı

`TrendKorelasyon.tsx` (I²–ΔT dağılımı — **fizik düzeltmesi yapıldı**, bkz. §6), `OlayAnalizi.tsx`
(kara kutu + yeni ark tripi senaryosu), `CihazSagligi.tsx`, `BolgeHaritasi.tsx`,
`hardware/yerlesim/ek2-14-yerlesim.svg`, `hardware/mekanik/din-kutu.scad`, `docs/01/07/08/10/11/13`.
**9 ekranın 7'si çalışıyor** (kabul kriteri karşılandı). Ayrıntı: PLAN.md TC3 + Günlük Kayıt.

## 5. Faz 4/5/6 — C'nin görevleri

| Görev | Durum |
|---|---|
| T4.5 README (repo kökü) 7-çıktı tablosu | ✅ Tamamlandı |
| T4.6 Ekran görüntüleri (`assets/ekran/`, 7 ekran) | ✅ Tamamlandı, `docs/16` §5'e gömülü |
| T4.7 Sır taraması (C'nin payı) | ✅ Temiz — son commit'ten önce tekrar koşulmalı |
| T5.1 Belirlenimli demo betikleri (`demo/senaryo/`) | ✅ Yazıldı (`s0`–`s6` A'yı bekliyor, `s7`/`s8` çalışır) |
| T5.2 Sunum taslağı (`demo/sunum/`) | ✅ Tamamlandı |
| Faz 6 teslim kontrol listesi | ⏳ Ekip teslim gününde (20 Eylül) yapacak |

## 6. Kararlar (öneri seçilerek verildi — kullanıcı talimatı gereği, uygulandıkları haliyle)

1. **KiCad şeması → blok diyagramı + I/O tablosu + BOM.** İlk planda "stok KiCad sembolleriyle
   geçerli bir `.kicad_sch`" düşünülmüştü; **uygulama sırasında bundan vazgeçildi**: KiCad'in
   sürüme özgü dosya formatı (uuid, `lib_symbols`, sayfa şeması) bu ortamda (KiCad kurulu değil,
   internet yok) doğrulanamazdı — küçük bir sözdizimi hatası dosyayı açılmaz/bozuk hale
   getirebilirdi, bu da "sahte şema" izlenimi doğurup dürüstlük kuralını asıl ihlal eden şey
   olurdu. Bunun yerine `hardware/pano-beyni/blok-diyagrami.md` (Mermaid, gerçek parça
   numaralarıyla) + `io-tablosu.md` + `bom.csv` — rapor §10'un kendi tanımladığı asgari seviye.
   Gerekçe `hardware/pano-beyni/README.md`'de açık yazılı.
2. **Bölge haritası → il/ilçe değil dağıtım şirketi (ADM/GDZ) bazlı.** Sözleşmede (`PanelSummary`)
   gerçek bir il/ilçe alanı yok, yalnızca genelde boş `lat`/`lon`. Coğrafi olarak uydurma bir
   kırılım göstermek yerine, pano kimliğinden gerçekten çıkarılabilen tek yapısal ayrımı
   (ADM-xxxxx / GDZ-xxxxx öneki) kullandım. `docs/16` §3'te açıkça belirtildi.
3. **Cihaz sağlığı ekranı ölçek sınırı.** API'de toplu "düğüm sağlığı" ucu yok. Görünen panoları
   sınırlı eşzamanlılıkla (6) tek tek çekiyor; ekranın altında bu açıkça yazıyor. Kalıcı çözüm
   için `contracts/changes/2026-09-14-fleet-health-bulk.md` önerisi açıldı (3 onay bekliyor).
4. **OpenSCAD/STL üretilmedi.** Bu ortamda `openscad` kurulu değil, internet de yok; yalnızca
   `.scad` kaynağı teslim edildi (`hardware/mekanik/din-kutu.scad`), STL üretimi ekip içinde
   OpenSCAD kurulu bir makinede yapılmalı. README'de not düşüldü.
5. **Sentetik veri fizik düzeltmesi (TC3 sırasında bulundu).** İlk `mockSeries.ts` sürümünde
   bağlantı ΔT'si ve panel akımı birbirinden bağımsız, ayrı gürültü fonksiyonlarıyla üretiliyordu.
   Bu, I²–ΔT saçılım grafiğinde "sağlıklı vs gevşek bağlantı farklı eğim" iddiasını **görsel
   olarak yalanlıyordu** (ilk ve son 7 günün eğimi ~aynı çıktı: 530 vs 677 yerine ~30 vs ~30).
   Kök neden: ΔT, gerçek fizik modelinden (ΔT = K·I²) değil, bağımsız bir zaman rampasından
   geliyordu. Düzeltme: `connPointValue` artık `elecValue`'nun kullandığı **aynı** akım
   fonksiyonunu (`phaseCurrentA`) kullanıp ΔT'yi bu akımdan `K₀·K_ratio·I²` olarak türetiyor.
   Tarayıcıda doğrulandı: düzeltme sonrası eğim farkı 530,91 vs 677,20 (×10⁻⁶) — rapor §6.5
   L1-1'in iddia ettiği görsel artık gerçekten ortaya çıkıyor.
6. **Demo betikleri (henüz yapılmadı, T5.1):** Gerçek Docker yığını bu ortamda çalışmadığı için
   `demo/senaryo/*.sh` betikleri yazılacak ve yalnızca statik olarak gözden geçirilecek, gerçek
   yığına karşı çalıştırılıp doğrulanmayacak. Ekip bir kez gerçek yığında çalıştırıp süreleri
   teyit etmeli.

## 7. Riskler / ekibe not

- Backend ortam sorunu (§2) B'ye iletilmeli.
- `contracts/changes/2026-09-14-fleet-health-bulk.md` üç onay bekliyor.
- Demo betikleri (T5.1 tamamlanınca) gerçek yığında bir kez çalıştırılıp zamanlamaları teyit
  edilmeli.
- `hardware/mekanik/din-kutu.scad` bir OpenSCAD kurulu makinede STL'e çevrilmeli.

---
*Bu bölümün altına yeni girişler en üste eklenir (en yeni en üstte).*
