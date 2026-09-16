# Tasarım Revizyonu Planı — "RAL 7035 + Aydem kimliği"

> **Sahip:** Kişi C (Berke) · **Tarih:** 14 Eylül 2026 · **Durum:** kullanıcı onayladı, **plan uçtan uca
> uygulandı (R1–R5)**. Bağlantılı: [`docs/16-ux-tasarim.md`](../docs/16-ux-tasarim.md) (tasarım gerekçesi).

## 0. Tek paragrafta öneri

Arayüz kontrol odası dilini (ISA-101: gri zemin, renk yalnızca anormal durumda) **korusun**; ADM/GDZ
kimliği **veri alanına değil, çerçeveye** girsin. Marka turuncusu (`#FF671D`) üst kimlik bandında,
ürün işaretinde ve boş durumlarda; markanın grafit grisi (`#4D4D4D`) plakalarda ve birincil düğmelerde;
markanın mavisi (`#003DA5`) "bizim donanımımız / seçim / odak" rengi olur. Durum cümleleri markanın
yazı tipi Nunito ile, sayılar ve etiketler Barlow Semi Condensed ile yazılır. Ekran ilk bakışta
"Aydem grubu" der, ama bir alarm turuncusu marka turuncusuyla karışmaz. Buna ek olarak jüride fark
yaratacak yenilikler öneriyorum; en güçlüsü **3D zaman kaydırıcı** (§4).

---

## 1. ADM Elektrik ve GDZ Elektrik: ne bulduk

Kaynak: `admelektrik.com.tr` ve `gdzelektrik.com.tr` canlı sitelerinin hesaplanmış CSS'i ve logo
SVG'leri (tarayıcıda okundu, 14 Eylül 2026), Aydem Enerji logo kılavuzu sayfası.

| Öğe | Değer | Not |
|---|---|---|
| Birincil renk | `--colorFirst: #FF671D` | İki sitede de aynı. Düğmeler, vurgular, ikonlar |
| Birincil hover | `--colorFirstHover: #E2520C` | |
| İkincil | `--colorSecond: #4D4D4D` | Grafit gri; menü, koyu yüzeyler |
| Mavi | `--colorBlue: #003DA5` | Az kullanılıyor, kurumsal mavi |
| Başarı | `--success: #00AF66` | |
| Nötr zeminler | `#FFFFFF`, `#F4F4F4`, `#EDEDED`, koyu `#1E1E1E` | |
| Gradyan | `#E45D0B → #FFDE59` (45°), `#F7B745 → #E45C0E` | Kampanya kartları |
| Yazı tipi | **Nunito** (başlık/gövde), Calibri | Yuvarlak hatlı humanist grotesk |
| Logo | "Adm" / "Gdz" kelime markası + sağda üçgen "kıvılcım" işareti | ADM SVG `#F26829`, GDZ SVG `#FF671D` |
| Grup kimliği | Aydem Enerji: turuncu → kırmızı-pembe → mor gradyanlı üçgen kıvılcım, yuvarlak geometrik yazı (Kurumsal Kimlik Rehberi 2020) | ADM/GDZ bunun tek renkli turuncu türevi |

**Çıkarımlar**

1. **ADM ve GDZ görsel olarak aynı marka.** Aynı şablon, aynı token'lar; yalnızca kelime markası
   farklı. Arayüzde iki şirketi renkle ayırmak markaya aykırı olur. Ayrım **metinle** (ADM/GDZ plakası)
   yapılmalı. Bölge ekranında bugün de öyle.
2. **Turuncu = marka**, ama bizim alarm paletimizde **turuncu = P2** (`#DD6418`). İki ton göz kararıyla
   neredeyse aynı. Bu revizyonun ana tasarım problemi bu (§3.2).
3. Marka turuncusu **metin rengi olarak kullanılamaz**: beyaz üzerinde `#FF671D` 2,9:1, `#E2520C` 3,9:1
   (WCAG AA metin için 4,5:1 gerekir). Yalnızca grafik öğe ve büyük dolgu olarak kullanılabilir.
4. Grafit `#4D4D4D` (beyaz üzerinde 8,5:1) ve mavi `#003DA5` (9,5:1) veri arayüzünde rahatça
   kullanılabilir. Bunlar markayı taşıyan "sessiz" renkler.
5. **Logo dosyalarını uygulamaya gömmüyoruz.** Marka kullanım izni bizde değil ve ürün "Grid Up"
   adıyla bizim prototipimiz. Kimliği renk, yazı tipi ve şirket adı metniyle taşıyoruz.

---

## 2. Dünyada benzer ürünler: ne yapmışlar, ne alıyoruz

| Ürün / kaynak | Öne çıkan tasarım fikri | Bizim için ne demek |
|---|---|---|
| **ISA-101 / High Performance HMI** | Orta gri zemin, ekranın büyük kısmı gri; renk yalnızca anormal durum için. Sahada yaygın eşleme: P1 kırmızı, P2 amber/turuncu, P3 sarı. Renk tek başına anlam taşımaz | Temelimiz zaten bu; korunuyor. Marka rengi bu kurala uyacak şekilde yerleştiriliyor |
| **ABB Ability SWICOM** (şalt cihazı durum izleme) | Hücre başına sağlık durumu, kalan ömür, kritik noktaların sıcaklığı, kısmi deşarj; yerinde dokunmatik HMI + mobil + bulut panosu | "Kalan ömür / sınıra kalan süre" ana metriği doğru seçim; bizde de açılış ekranı bu |
| **Schneider EcoStruxure Continuous Thermal Monitoring** | Kablosuz sıcaklık sensörleri, eşik, trend, bildirim; kapak üstü HMI | Mutlak sıcaklık ve eşiğe dayanıyorlar. Bizim farkımız **yüke göre normalize (K/K₀)**; arayüzde daha görünür olmalı |
| **Siemens Electrification X** | Şebeke genelinde olay/alarm panosu; sağlık analizini yük profili, sıcaklık ve nemle ilişkilendirme | Trend & korelasyon ekranımızın karşılığı; doğru yoldayız |
| **Hitachi Energy Lumada APM** | Varlık sınıfı başına sağlık endeksi, **arıza olasılığı risk matrisi**; fizik + ML + istatistik modeller | Filo için **risk matrisi** önerisi (§4, Y3) buradan |
| **GE Vernova GridOS** | Rutin iş ve yüksek baskılı olaylar için optimize edilmiş **tek birleşik** kullanıcı deneyimi | **Olay modu** önerisi (§4, Y2) |
| **Emerson DeltaV Live** | HTML5 grafikler, hazır ekran hiyerarşisi, Center for Operator Performance en iyi uygulamaları, ISA-101 | Seviye hiyerarşimiz: Filo → Pano → Nokta → Kara kutu. Gezinmede açıkça görünmeli |
| **Siemens iX tasarım sistemi** | Endüstriyel yazılım için "Brand" ve "Classic" açık/koyu tema ayrımı | Aynı mantık: **marka katmanı** ile **durum katmanı** ayrı token'lar |
| **Honeywell Experion Operations Assistant** (2026) | Pilotta olayları ortalama 5–10 dk önce öngördü; her öneri gerekçesiyle gelir, eylem için insan onayı şart | "Neden? / Ne yapmalı? / Ne kadar acil?" yapımız bu çizgide. Kural tabanlı olay özeti eklenebilir (Y7) |
| **Cognite Industrial Canvas** | 3D model, zaman serisi, doküman ve iş emri tek tuvalde, bağlamlandırılmış | 3D düğüme tıklayınca trend + faz karşılaştırması: artık bizde var (§6) |
| **Tesla Powerwall uygulaması** | Canlı enerji akışı çizgileri, kaynağa göre renk, dokununca ayrıntı | 3D'de barada **yüke orantılı sakin akış animasyonu** (Y5), nötr renkte |
| **Calm technology / alarm yorgunluğu** | Bilgi periferide; dikkat yalnızca gerektiğinde istenir | Hareket yalnızca **onaylanmamış** alarmda (Y6); bugün halka onaydan sonra da atıyor |
| **Güç sistemi kontrol odalarında durumsal farkındalık** (Energies 2026, "Infostructure") | Dijital ikiz varlıkları hem **mekânsal** hem **zamansal** boyutta göstermeli | İki kahramanımız tam olarak bu: 3D ikiz (mekân) + sınıra kalan süre ekseni (zaman). Y1 ikisini birleştiriyor |

---

## 3. Görsel sistem revizyonu

### 3.1 Katman kuralı

```
┌─ MARKA KATMANI ─────────────────────────────────────────────┐
│ 4 px turuncu kimlik bandı · ürün işareti · boş durumlar     │  ← #FF671D, Nunito
├─ ÇERÇEVE ───────────────────────────────────────────────────┤
│ gezinme · KPI'lar · düğmeler (grafit) · seçim/odak (mavi)   │  ← #4D4D4D, #003DA5
├─ VERİ ALANI (ISA-101) ──────────────────────────────────────┤
│ gri zemin · gri çizim · renk YALNIZCA P1/P2/P3/SYS          │  ← marka turuncusu YASAK
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Turuncu çakışmasının çözümü

| Seçenek | Artı | Eksi | Karar |
|---|---|---|---|
| A. P2'yi turuncudan başka renge kaydırmak | Çakışma tamamen biter | Sahada P2 = amber/turuncu alışkanlığı var; SCADA ekibinden jüri yanlış okur | ✗ |
| B. Marka turuncusunu hiç kullanmamak | Sıfır risk | "Şirkete ait olduğu belli olsun" isteği karşılanmaz | ✗ |
| **C. Mekânsal ayrım + şekil + ton farkı** | Marka görünür, alarm alışkanlığı korunur | Kuralın disiplinle uygulanması gerekir | **✓ önerilen** |

**C'nin kuralları:**
- Marka turuncusu **yalnızca** marka katmanında (üst bant, ürün işareti, boş durum çizgisi). Veri
  alanında, grafiklerde, 3D sahnede ve düğmelerde **yok**. Kabul ölçütü olarak grep ile kontrol edilir.
- P2 her zaman **üçgen + "2"** ile gelir (bugün de öyle); marka turuncusu hiçbir zaman bir şekil içinde
  veya bir sayının yanında görünmez.
- P2 tonu markadan ayrılır: `#DD6418` → `#D9530F` (daha kırmızımsı ve koyu; beyazda 4,0:1).

### 3.3 Token'lar: önce / sonra

| Token | Bugün | Öneri | Gerekçe |
|---|---|---|---|
| `--bg` | `#E2E4DF` | `#E4E5E2` | RAL 7035 hissi korunur; yeşilimsi ton markanın nötr grisine yaklaşır |
| `--surface` | `#F4F5F1` | `#F6F6F4` | Markanın `#F4F4F4`'üne yakın |
| `--ink` | `#212629` | `#1F2224` | |
| `--plate` | `#2A2F33` | **`#4D4D4D`** | Marka ikincil rengi: pano kimlik plakası, birincil düğmeler |
| `--ours` | `#2C63C9` | **`#003DA5`** | Marka mavisi: bizim donanım, seçim, odak halkası (9,5:1) |
| `--brand` | yok | **`#FF671D`** | Yalnızca marka katmanı |
| `--brand-deep` | yok | `#E2520C` | Açık zeminde grafik öğe (3,9:1) |
| `--p1` | `#C62828` | `#C62828` | Değişmez |
| `--p2` | `#DD6418` | `#D9530F` | §3.2 |
| `--p3` | `#C99700` | `#C99700` | Değişmez |
| `--sys` | `#56688A` | `#5A6275` | Mavi seçim rengiyle karışmasın diye daha gri |
| `--display` | yok | `"Nunito"` | Marka yazı tipi, `@fontsource/nunito` ile çevrimdışı (GK4) |

### 3.4 Tipografi

- **Nunito 700/800:** ürün adı, sayfa başlıkları ve büyük durum cümlesi (ör. *"DSYA-3 L2 bağlantısı,
  yük değişmezse yaklaşık 6 gün sonra sıcaklık sınırını aşacak."*). Bu cümle arayüzün sesi; markanın
  yazı tipiyle konuşur.
- **Barlow Semi Condensed 600:** tablo başlıkları, KPI sayıları, plakalar, eksen etiketleri. Dar ve
  tabular rakamlı; kontrol odası yoğunluğu için uygun.
- **Barlow 400/500:** gövde metni.
- İki aile birbirinden net ayrılır: yuvarlak humanist (Nunito) ve dar grotesk (Barlow).

### 3.5 Marka katmanı yerleşimi

```
┌────────────────────────────────────────────────────────────────────────┐
│████████████████████████ 4px #FF671D ███████████████████████████████████│
│ ◢ Grid Up   Filo  Alarmlar  Trend  Kara kutu  Cihaz  Bölge │ 20 pano … │
│             ────                                                        │
└────────────────────────────────────────────────────────────────────────┘
  ◢ = kendi ürün işaretimiz (grafit üçgen, turuncu kenar). Aydem kıvılcımına
      gönderme yapar, kopyalamaz. Aktif menü alt çizgisi grafit, turuncu değil.
```

- Pano detayda plaka `ADM-00014` grafit; yanında soluk metinle "Adm Elektrik".
- Boş durumlar ("Aktif alarm yok"): ince turuncu çizgi + Nunito cümle. Sakin anlar marka anları olur.
- Sunumda her ekran görüntüsünün üst bandı turuncu olduğu için slaytlar da kurumsal görünür.

---

## 4. Yenilikler

Öncelik, özellik dondurmaya (17 Eylül 23:59) göre verildi.

| # | Yenilik | İlham | Ne gösteriyor | Efor | Öncelik |
|---|---|---|---|---|---|
| **Y1** | **3D zaman kaydırıcı** | Infostructure (mekân + zaman), Cognite | 3D ikizin altında 14 günlük kaydırıcı: DSYA-3 L2 düğümü gün gün griden turuncuya döner, K/K₀ etikette akar. Mevcut `GET /series` ile, yeni uç gerekmez | 1 gün | **Must**: demo S1 anlatımının merkezi |
| **Y2** | **Olay modu** | GE Vernova GridOS, ISA-101 | P1 aktif ve onaylanmamışken veri alanı sadeleşir: olay kartı, geri sayım, kara kutu kısayolu öne çıkar; geri kalanı soluklaşır. Onaylanınca normale döner | 0,5 gün | **Should** |
| **Y3** | **Risk matrisi** | Hitachi Lumada APM | Filo ekranında ikinci görünüm: x = sınıra kalan süre (log), y = etki (trafo gücü, `pano_type`). Sağ üst = "önce buraya git" | 0,5 gün | **Should** |
| **Y4** | **Termal görünüm** | Sahadaki termal kamera alışkanlığı | 3D'de "termal" düğmesi: bağlantı ΔT değerleri baralar boyunca renk gradyanı (gri → sarı → turuncu) | 0,5 gün | Could |
| **Y5** | **Sakin akış** | Tesla Powerwall | 3D'de baralarda yüke orantılı, çok soluk gri akış çizgileri; hareket azaltma tercihinde kapalı | 0,5 gün | Could |
| **Y6** | **Onaylanınca duran hareket** | Calm technology, ISA-18.2 | Halka animasyonu yalnızca onaylanmamış alarmda | 1 saat | **Must** |
| **Y7** | **Olay anlatısı** | Honeywell Operations Assistant | Kara kutuda zaman çizelgesinden kural tabanlı tek paragraf özet (ark algılandı → açtı → onaylandı, süreleriyle). LLM yok, çevrimdışı | 0,5 gün | Could |

**Bilinçli olarak önerilmeyenler:** koyu tema (ISA-101 uzun vardiyada orta gri önerir; koyu tema
"demo şovu" gibi okunur), harita karosu (GK4 çevrimdışı), AR/VR (saha gerçekçiliği yok).

---

## 5. Uygulama sırası

| Adım | İçerik | Dosyalar | Durum |
|---|---|---|---|
| R1 | Token'lar + Nunito (§3.3, §3.4) | `theme.css`, `app.css`, `main.tsx`, `package.json` | ✅ Uygulandı |
| R2 | Marka katmanı: kimlik bandı, ürün işareti, plakalar, boş durumlar (§3.5) | `App.tsx`, `app.css`, `index.html` (favicon) | ✅ Uygulandı |
| R3 | Y6 (onaylanınca duran hareket) + Y1 (3D zaman kaydırıcı) | `Ikiz3D.tsx`, `OnGorunus.tsx`, `PanoDetay.tsx` | ✅ Uygulandı |
| R4 | Y2 (olay modu) + Y3 (risk matrisi) | `PanoDetay.tsx`, `AlarmNedeni.tsx`, `FiloListesi.tsx`, yeni `RiskMatrisi.tsx`, `mock.ts` düzeltmesi | ✅ Uygulandı |
| R5 | Ekran görüntülerini yeniden al, `docs/16`'yı güncelle | `assets/ekran/`, `docs/16-ux-tasarim.md` | ✅ Uygulandı |

**Kabul ölçütleri:** tüm testler yeşil; kontrast (metin ≥ 4,5:1, grafik ≥ 3:1) token bazında
doğrulanmış; veri alanı stillerinde `--brand` kullanımı sıfır (grep); 400 px genişlikte yatay taşma yok.

**Kapsam sınırı:** R1–R3 dondurmadan önce kesin, R4 zaman kalırsa. Hiçbiri sözleşme değişikliği
gerektirmez; Y3'teki "etki" yalnızca mevcut `pano_type` alanından gelir.

## 6. Yapıldı: R1–R3 (14 Eylül, aynı oturum)

- **R1 — Token'lar + Nunito.** `theme.css` §1 tablosundaki tüm değerler uygulandı (`--brand`,
  `--brand-deep`, güncellenmiş `--plate`/`--ours`/`--p2`/`--sys`/`--bg`/`--surface`/`--ink`).
  `@fontsource/nunito` npm'den eklendi (700/800), `--display` token'ı ürün adı, sayfa başlıkları
  (`.hero h1`) ve büyük durum cümlesinde (`.statement`) kullanılıyor.
- **R2 — Marka katmanı.** `.topbar`'a 4px `--brand` üst bant (`border-top`, sticky ile birlikte
  kayar); `App.tsx`'e kendi ürün işaretimiz (`BrandMark`, grafit üçgen + turuncu kenar — logo dosyası
  gömülmedi); favicon `--plate`/`--ours` token'larıyla güncellendi; `.calm` (boş/sakin durum, ör.
  "Aktif alarm yok.") ince turuncu çizgi + Nunito cümleye geçti; `.btn` (Onayla/Rafa al) `--plate`
  grafitine geçti.
- **R3 — Y6 + Y1.**
  - **Y6:** `OnGorunus.tsx` ve `Ikiz3D.tsx`'e `ackedPoints` prop'u eklendi (`PanoDetay.tsx`'te
    `active_alarms`'tan türetilir); onaylanmış alarma bağlı noktada halka/pulse animasyonu durur,
    nokta rengi (durum) değişmez. Tarayıcıda doğrulandı: ack sonrası `og-halo`/3D halo kayboluyor.
  - **Y1:** `Ikiz3D.tsx`'e 14 günlük zaman kaydırıcı eklendi. Seçili nokta anormalse (`k_ratio>1.02`
    ve durum warn/alarm/critical), `GET /panels/{id}/series` ile geçmiş `k_ratio` çekilir; kaydırıcı
    geçmiş değeri **API'nin bugün verdiği durum rengi ile 1.0 taban grisi arasında** interpolasyonla
    gösterir — yeni bir eşik icat edilmez, yalnızca zaten API'nin belirlediği iki uç nokta arasında
    oran gösterilir (kural 10 ile çatışmaz, kod içinde gerekçelendirildi). Tarayıcıda doğrulandı:
    "14 gün önce" ucunda düğüm griye dönüyor, ara noktalarda kademeli turuncuya geçiyor.
  - Sabit kodlanmış eski palet renkleri (`#2C63C9`, `#DD6418`) grafik serilerinde (`PanoDetay.tsx`,
    `TrendKorelasyon.tsx`, `OlayAnalizi.tsx`) yeni token değerlerine (`#003DA5`, `#D9530F`) güncellendi.
- **Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı, ADM-00014/GDZ-00231/
  ADM-00301/GDZ-00088 sayfalarında görsel + konsol kontrolü yapıldı (hata yok), 390 px mobil genişlikte
  yatay taşma yok.

## 7. Yapıldı: R4 — Y2 (olay modu) + Y3 (risk matrisi)

- **Y2 (olay modu).** `AlarmNedeni.tsx` içine gömüldü (ayrı bileşen yerine "olay kartı"nın kendisi
  güçlendirildi): P1 + onaysız alarmda kart üst kenarı `--p1` kırmızısına döner (`qa-event`), geçen
  süre (`ago()`, zaten canlı güncelleniyordu) kırmızı/kalın olur, ve `event_id` varsa "Kara kutuyu
  aç →" kısayolu belirir. `PanoDetay.tsx`'te bu durumda (`eventMode`) destekleyici bölümler (diğer
  alarmlar, faz karşılaştırması, trend, ölçüm özeti/tablosu) `.quiet` sınıfıyla soluklaşır (hover/
  focus'ta tam görünürlüğe döner) — dijital ikiz ve karar bilgisi (Neden/Ne yapmalı/Ne kadar acil)
  tam opaklıkta kalır.
- **Y3 (risk matrisi).** Yeni `components/RiskMatrisi.tsx`, Filo ekranında "Zaman ekseni / Risk
  matrisi" geçişiyle. **Plan metninden bir sapma yapıldı:** ilk taslak y eksenini "trafo gücü
  (`pano_type`)" olarak öneriyordu, ama sözleşmede filodaki **tüm panolar aynı `pano_type`**
  değerine sahip (1600 kVA, tek ürün kapsamı — `docs/10-bom-maliyet-roi.md`) — bu alanı "etki" gibi
  göstermek sabit bir sayıyı değişkenmiş gibi sunmak olurdu (dürüstlük kuralı ihlali). Bunun yerine
  gerçekten panodan panoya değişen ve API'nin ürettiği `risk_score` (0–100) kullanıldı. Ayrıca ilk
  taslaktaki "sağ üst köşe = önce buraya git" ifadesi de düzeltildi: x ekseni soldan sağa zaman
  arttığı için en acil+riskli köşe **sol üst**tür; kod ve arayüz buna göre yazıldı. Süre tahmini
  olmayan P1/P2 alarmlar (ark, koruma sağlığı kaybı) x=0 ("şimdi") ucuna yerleşir — yeni bir eşik
  icat edilmedi, yalnızca "geri sayımı yok" durumu en acil uca haritalandı.
- **Mobil varsayılan görünüm.** Zaman ekseni (`SureEkseni`) dar ekranda halihazırda gizliydi (sabit
  piksel düzeni, `app.css` @media 960px). Risk matrisi SVG'si ölçekli olduğu için mobilde çalışıyor;
  mobil kullanıcı boş alanla karşılaşmasın diye `matchMedia` ile ilk açılış görünümü mobilde "risk
  matrisi" olacak şekilde ayarlandı (masaüstünde değişiklik yok).
- **Mock veri düzeltmesi (yan bulgu).** Y2'nin "Kara kutuyu aç" kısayolu test edilirken, GDZ-00231'in
  P1 alarmının (`ALM-PROT-HEALTH`, `event_id: "EVT-51"`) kara kutu verisi hiç yoktu (`mock.ts`
  `EVENTS` sabitinde yalnızca `EVT-60`/`EVT-42` tanımlıydı) — bu, yeni özellik olmadan gizli kalan
  önceden var olan bir eksiklikti. `EVENTS`'e `EVT-51` girdisi eklendi (üç adımlık gerçekçi zaman
  çizelgesiyle); artık depodaki her iki P1 senaryosu da kara kutuya sahip.
- **Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı. Tarayıcıda: Filo'da
  risk matrisi noktasına tıklayınca doğru panoya gidiyor; GDZ-00231/Alarm konsolunda P1 kartının
  kırmızı üst kenarı ve kara kutu kısayolu (EVT-51 → gerçek zaman çizelgesi) doğrulandı; 390 px
  mobilde hem risk matrisi hem Filo listesi yatay taşmasız.

## 8. Yapıldı: R5 — ekran görüntüleri yenilendi

`assets/ekran/`'daki 8 dosyanın hepsi, R1–R4 sonrası yeni palet ve düzenle (`npm run dev:mock`,
1440×900, mock verisi) aynı rota/pano/sekme kombinasyonlarıyla yeniden çekildi:

| Dosya | Rota | Not |
|---|---|---|
| `01-filo-listesi.png` | `/` | Zaman ekseni (varsayılan) sekmesi |
| `02-pano-detay-alarm.png` | `/pano/ADM-00014` | Ön görünüş sekmesi |
| `02-pano-detay-normal.png` | `/pano/ADM-00301` | Boş/sakin durum (`.calm`, ince turuncu çizgi) |
| `03-alarm-konsolu.png` | `/alarmlar` | Açık filtre; iki P1 kartı da olay modu stilinde |
| `04-trend-korelasyon.png` | `/trend/ADM-00014` | Nokta DSYA-3 L2, tam sayfa |
| `05-olay-analizi-kara-kutu.png` | `/olay/EVT-60` | 72 saat penceresi |
| `06-cihaz-sagligi.png` | `/cihaz-sagligi` | — |
| `07-bolge-haritasi.png` | `/bolge` | — |

`docs/16-ux-tasarim.md` §2.1'e risk matrisi, yeni §2.2'ye olay modu notu eklendi; §5'teki tablo aynı
dosya adlarını kullandığı için görsel değişmiş haliyle otomatik güncel.

---

## 9. Yapıldı: 3D dijital ikiz entegrasyonu (14 Eylül, önceki oturum)

- `frontend/src/components/Ikiz3D.tsx`: spike'taki sahnenin üretim hali. three.js npm'den
  (`three@0.169.0`) ve **ayrı parça** olarak yüklenir (509 kB, gzip 130 kB); ilk açılış paketi
  229 kB'de kaldı. CDN yok (GK4).
- Pano detayda "Ön görünüş / 3D ikiz" geçişi; seçim tarayıcıda hatırlanır. WebGL veya paket yükleme
  hatasında sayfa çökmez, ön görünüşe yönlendiren mesaj çıkar.
- Geometri 2D ile **aynı kaynaktan** (`panelGeometry.ts` → `pointPos3d`, birim testli). Durum
  API'deki `ConnPoint.state`'ten (kural 10), renk değerleri tema token'larından gelir; R1 uygulanınca
  3D de otomatik güncellenir.
- Açılışta kamera birincil alarmın noktasına uçar; düğüme tıklamak 2D'deki gibi faz karşılaştırmasını ve
  trendi açar. TVOC-2 koruma sağlığı arızasında (`last_det_label`) ilgili dedektörün kapsama konisi
  kırmızı yanar ve "korumasız bölge" etiketi çıkar.
- Çakışan etiketler önem sırasına göre gizlenir; hareket azaltma tercihine uyulur; sahne yalnızca
  değişiklik olduğunda yeniden çizilir.

---

## 10. Düzen revizyonu — kart sistemi (kullanıcı geri bildirimi sonrası, 14 Eylül)

**Gerekçe.** R1–R5 yalnızca renk/tipografi token'larını değiştirdi; sayfa düzeni ve bileşen yapısı
aynı kaldı. Kullanıcı bunu "her şeyi aynı bırakmışsın, global projelerden ilham al dedim" diye
haklı olarak eleştirdi. Bu bölüm, §2'deki global araştırmadan (Hitachi Lumada APM, ABB SWICOM,
GE Vernova, Cognite Industrial Canvas) doğrudan alınan somut düzen kalıplarını uygular.

| Değişiklik | Kaynak ilham | Nerede |
|---|---|---|
| Kart + gölge sistemi (`--radius`, `--shadow-sm`, `--shadow` token'ları) | Hitachi APM, ABB SWICOM, Cognite — hepsi duz sinirlar yerine yukseltilmis kart kullanir | `theme.css`, tüm kart sınıfları |
| KPI şeridi → büyük-sayı karoları | GE Vernova / ABB filo panolarının "big number" özet şeritleri | `App.tsx` `FleetKpis`, `app.css` `.kpis` |
| "Şimdi yapılacaklar" → kart ızgarası (tek sütunlu yoğun liste değil) | Hitachi Lumada APM'in varlık sağlığı kartları | `app.css` `.work`/`.work-row` |
| Pano detayda "sağlık şeridi": split'ten önce, her zaman görünür | ABB SWICOM'un durum özet bandı | `PanoDetay.tsx` (`PanoOzeti` split'ten önce taşındı, artık `quiet` değil) |
| Birincil buton (Onayla) → dolgun marka turuncusu + koyu metin | Kullanıcı talebi: "GDZ'nin turuncusu kullanılan bir tasarım yok" | `app.css` `.btn` |
| Aktif sekme/görünüm altına turuncu şerit (`box-shadow: inset 0 -3px 0 var(--brand)`) | Kullanıcı talebi (bkz. AskUserQuestion, "Daha belirgin yap" seçildi) | `.nav-link.active`, `.chart-range`/`.i3-bar` `[aria-pressed=true]` |
| Kart kenarı vurgusu (hover/focus'ta turuncu sol kenar) | — | `.pin-card`, `.work-row` |

**Bilinçli sınır — turuncu her yerde değil.** `.console-filters` (Açık/Rafta/Tümü/**Kritik/Alarm/
Uyarı**/Sistem) düğmelerine turuncu EKLENMEDİ: bu düğmelerden biri kelimenin tam anlamıyla "Alarm"
(P2'nin adı) — turuncu vurgu koysak, revizyonun tam önlemeye çalıştığı "turuncu = P2 alarmı"
karışıklığını tam da orada yeniden yaratırdı. Bu, kullanıcının "daha belirgin yap" talebiyle
çelişmez — talep genel görünürlük artışıydı, alarm etiketli düğmelere özel bir istisna değildi;
karar öneri seçilerek verildi.

**`.qa`/`.console-card` birleştirmesi.** Alarm konsolunda `AlarmNedeni` (`.qa`) `.console-card`
içine gömülüydü — ikisi de kart kenarlığı çizdiği için "kart içinde kart" görünümü oluşuyordu.
`.console-card` artık yalnızca liste aralığı veriyor; görsel kart her yerde (pano detay + alarm
konsolu) tek başına `.qa`.

**Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı. Filo/Pano detay/
Alarm konsolu/Bölge haritası 1440px ve 390px genişlikte görsel + konsol kontrolünden geçti, yatay
taşma yok. `assets/ekran/`'daki 8 dosya bu düzenle üçüncü kez yeniden çekildi (bkz. §8 tablo, aynı
dosya adları).

---

## 11. Zemin ve tipografi: tek standart (kullanıcı geri bildirimi, aynı oturum)

Kullanıcı: "arkaplanı biraz daha aç beyaz tonları... şu grimsi renkten kurtul bir de fontta tek bir
standarttan ilerleyelim."

- **Zemin.** `--bg` RAL7035 grimsi tondan (`#E4E5E2`) açık/beyaza yakın bir tona (`#F7F7F5`) geçti;
  `--surface` (kart zemini) tam beyaza (`#FFFFFF`); `--well` ve `--line` orantılı olarak açıldı.
  `body`'ye üst banttan sarkan, %8 opaklıkta bir `radial-gradient` turuncu parıltı eklendi
  (`theme.css`) — marka rengini zemine taşır ama veri alanındaki durum renkleriyle asla yarışmaz
  (opaklık çok düşük, ISA-101 "renk = alarm" kuralını bozmaz).
- **Tipografi — tek aile.** `--display` token'ı artık ayrı bir marka fontu (Nunito) değil,
  `--cond` (Barlow Semi Condensed) ile aynı yığın; `@fontsource/nunito` paketten tamamen
  kaldırıldı (`npm uninstall`). Ürün artık tek bir font ailesi kullanıyor: Barlow (gövde metni) +
  Barlow Semi Condensed (başlıklar, etiketler, rakamlar) — ikisi aynı ailenin iki genişliği,
  ayrı bir "marka sesi" fontu yok. `main.tsx`'e Barlow Semi Condensed 800 ağırlığı eklendi (büyük
  başlıklarda kullanılan tek ağırlık).
- **Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı; Filo/Pano detay/
  Alarm konsolu 1440px ve 390px'de görsel + konsol kontrolünden geçti. `assets/ekran/`'daki 8 dosya
  dördüncü kez yeniden çekildi; önce/sonra karşılaştırma Artifact'ı güncellendi.

## 12. Düzeltme: "hâlâ grimsi" — iki kök neden (aynı oturum, hemen ardından)

Kullanıcı: "arkaplanlarda hala o grimsi arkaplan var artifactta da öyle oraları istediğim gibi
beyaz + turuncu detaylar yapmamışsın." İki ayrı kök neden bulundu:

1. **Uygulamada `--bg` hâlâ beyazdan belirgin uzaktı.** §11'deki `#F7F7F5` yeterince beyaz
   değildi — `--surface` (kartlar) tam beyazken `--bg` (sayfa zemini) hafif farklı kaldığı için
   yan yana durunca "grimsi" okunuyordu. Düzeltme: `--bg` de tam beyaza (`#FFFFFF`) çekildi;
   kartlar artık yalnızca kenarlık + gölge ile ayrışıyor (renk farkıyla değil). Turuncu parıltı
   iki katmana çıkarıldı (üstte belirgin bir odak + altta geniş ve çok soluk bir yayılma) ki tam
   beyaz zeminde görünür kalsın.
2. **Karşılaştırma Artifact'ının KENDİ CSS'i hiç güncellenmemişti.** O sayfa, ilk yazıldığı anda
   (§ kullanıcıya ilk gönderildiğinde) uygulamanın O ANKİ token'larını elle kopyalamıştı
   (`--bg:#e4e5e2` vb.). Uygulamanın kendi `theme.css`'i sonraki turlarda değiştikçe, Artifact'ın
   kopyası GÜNCELLENMEDİ — bu yüzden kullanıcı "artifactta da öyle" dedi, haklı olarak. Düzeltme:
   Artifact'ın `:root` token'ları uygulamanın güncel `theme.css`'iyle birebir eşitlendi ve figür/
   chip kartlarına da gölge eklendi (onlar da beyaz zeminde beyazdı, ayrışmıyordu).

**Ders:** Bir HTML raporu/Artifact'ı uygulamanın tasarım sistemini "an itibarıyla" kopyalayarak
yazmak, sistem sonra değiştiğinde sessizce bayatlıyor. Böyle bir rapor tekrar yayınlanacaksa,
kaynak token'ların o anki halini yeniden okuyup senkronize etmek gerekiyor.

---

## 13. 3D dijital ikizde gerçekçilik geçişi (kullanıcı isteği: "panoları daha gerçekçi yap")

`components/Ikiz3D.tsx`'teki sahne şimdiye kadar düz renkli kutulardan oluşuyordu (fonksiyonel,
ama "oyuncak" görünümlü). Harici model/doku dosyası eklenmedi (GK4: internet yok, CDN yok) —
hepsi mevcut three.js geometrilerinden **prosedürel** olarak üretildi:

| Detay | Ne değişti |
|---|---|
| DIN ray | Düz tek kutu yerine 3 kutulu bir siluet (ince alt/üst kenar + içeri çekilmiş gövde) — gerçek TS35 profiline yakın; parlak galvanizli çelik malzeme (`mat.rail`) |
| Durum LED'leri | TVOC-2, Pano Beyni, Modem'in ön yüzünde küçük parlayan küreler. **TVOC-2'ninki dekoratif değil**: `tvoc.prot_health_ok` API alanına bağlı — sağlıklıyken yeşil, arızalıyken kırmızı (kural 10 ile çatışmaz, yeni bir eşik icat edilmedi, zaten var olan durumu gösteriyor). Modem LED'i veri aktivitesini çağrıştıran hafif düzensiz bir titreşimle yanıp sönüyor (saf dekoratif) |
| DSYA devre kesicileri | Her faz yüzeyine siyah anahtar kolu + altında açık renkli bir pencere eklendi — gerçek bir MCB'nin önden görünüşüne yakın. Anahtar durumu herhangi bir alarm rengine bağlanmadı (sensör düğümü zaten durumu gösteriyor; anahtar yalnızca "gerçek bir cihaz" hissi katmak için) |
| Kablolar | Dümdüz silindir yerine `CatmullRomCurve3` + `TubeGeometry` ile hafifçe sarkan/bükülen tüpler — doğal ağırlık altında eğilen kablo görünümü |
| Kablo pabuçları | Ön yüzde küçük bir bağlantı cıvatası başı eklendi |
| Kompanzasyon kondansatörleri | Gövde üzerinde iki ince koyu kıvrım bandı (gerçek kondansatörlerdeki crimp bantları) |
| Malzemeler | RAL 7035 gövde artık `MeshPhysicalMaterial` + hafif clearcoat (boyalı sacın donuk parlaklığı); bakır baralar ve DIN ray daha metalik (`metalness` 0.9); yumuşak bir dolgu ışığı eklendi (sert gölgeleri hafifletir, stüdyo fotoğrafçılığındaki "fill light" mantığı) |

**Bilinçli sınır:** Anahtar/pencere renkleri ve DIN ray detayı tamamen **dekoratif malzeme
detayı** — hiçbiri yeni bir durum/alarm anlamı taşımıyor, kural 10'u (renkler yalnızca API'nin
`ConnPoint.state`'inden) ihlal etmiyor. Tek istisna TVOC-2 LED'i, o da zaten var olan
`tvoc.prot_health_ok` alanını yansıtıyor, yeni bir şey icat etmiyor.

**Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı (Ikiz3D parçası
511 kB'den 529 kB'ye çıktı, hâlâ tembel yükleniyor, ilk açılış paketini etkilemiyor). Tarayıcıda
ADM-00014 (sağlıklı TVOC-2, yeşil LED) ve GDZ-00231 (arızalı TVOC-2, kırmızı LED) ile görsel
doğrulama yapıldı; ekran görüntüleri kullanıcıya doğrudan gönderildi (SendUserFile) — yalnızca
metinle anlatılmadı (bkz. §12'nin dersi).

---

## 14. 2D Ön görünüşte de gerçekçilik: 3D ile eş düzey (kullanıcı sordu: "2D'ler de gerçekçi mi")

§13'te yalnızca 3D dijital ikiz güncellenmişti; kullanıcı 2D "Ön görünüş"ün (`components/
OnGorunus.tsx`) durumunu sordu — haklı bir soruydu, dokunulmamıştı. Aynı detaylar SVG'ye de
eklendi (yine yalnızca dekoratif geometri/renk, harici görsel yok):

| Detay | 2D karşılığı |
|---|---|
| Durum LED'leri | TVOC-2/Pano Beyni/Modem üzerinde küçük yeşil noktalar. TVOC-2'ninki 3D'deki gibi `tvoc.prot_health_ok`'a bağlı (yeşil/kırmızı) — bunun için `OnGorunus`'a yeni `tvoc` prop'u eklendi, `PanoDetay.tsx`'ten `detail.tvoc` geçiliyor |
| DSYA devre kesicileri | Her breaker gövdesinin üstüne siyah anahtar kolu + açık renkli pencere (yalnızca gerçek breaker'larda, yedeklerde değil) |
| Kompanzasyon kondansatörleri | Dairenin merkezinden 3 yöne basınç tahliye izi (gerçek güç kondansatörlerinin üst yüzeyindeki çizik desen) — 3D'deki kıvrım bandının 2D karşılığı, çünkü önden bakışta gövde bantları değil üst yüzey izi görünür |
| DIN ray | İnce bir "üst kenar parlaması" çizgisi eklendi (3D'deki 3 katmanlı profilin 2D karşılığı) |

**Bilinçli sınır (3D ile aynı):** LED'ler ve anahtarlar dekoratif; hiçbiri yeni bir alarm/durum
anlamı taşımıyor. Tek işlevsel bağlantı yine TVOC-2 LED'i — API'nin zaten verdiği
`tvoc.prot_health_ok` alanını gösteriyor, yeni bir eşik icat edilmedi (kural 10).

**Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı. ADM-00014 (yeşil
TVOC-2 LED'i) ve GDZ-00231 (kırmızı TVOC-2 LED'i) ile görsel doğrulama yapıldı, 390 px mobilde
yatay taşma yok. İki ekran görüntüsü (gerçek boyut + yakınlaştırılmış) kullanıcıya doğrudan
gönderildi (SendUserFile).

## 15. "Neredeyse birebir gerçeğe benzemesin" isteği — gerçek ürün araştırması (14 Eylül, aynı oturum)

Kullanıcı önce "gerçek görüntü/model kullansak olmaz mı, bizimki ne kadar benziyor gerçeğe"
diye sordu; cevap üç ayrı soruya ayrıldı: (a) gerçek foto/CAD modelini doğrudan gömmek —
telif/lisans riski + GK4 offline kural nedeniyle hayır; (b) mevcut temsilin doğruluğu — bunu
gerçekten araştırıp ölçmek gerekiyordu, tahmin etmek yerine; (c) gerçek çizim şeması var mı —
TEDAŞ şartnamesi kamuya açık genel referans, komitenin kendi EK-II/14 PDF'i ise gizli (yalnızca
sayısal ölçüler yeniden kullanılabilir, görsel kopyalanamaz). Ardından kullanıcı işi netleştirdi:
**"Ben bizimkilerin neredeyse birebir gerçeğe benzemesini istiyorum."** Bu, (b)'yi ciddiye alıp
adı geçen gerçek ürünleri tek tek araştırmayı gerektirdi.

### 15.1 DSYA: yanlış model düzeltmesi (ayrı commit `3784cd7`)

Araştırma sırasında ortaya çıkan en önemli hata: DSYA ("Dikey Sigortalı Yük Ayırıcı") bir MCB
(minyatür devre kesici) değil, **NH bıçak sigortalı dikey yük ayırıcıdır** — Etien'in DSYA ürün
sayfası doğrulandı. Önceki modelde küçük bir anahtar kolu + durum penceresi vardı (MCB
görünümü); bu factüel olarak yanlıştı. Düzeltme: hem `Ikiz3D.tsx` hem `OnGorunus.tsx`'te anahtar
+ pencere geometrisi kaldırıldı, yerine silindirik sigorta gövdesi + çekme tutamağı (puller cap)
kondu. `mat.toggle` → `mat.fuseCap`, CSS `.og-toggle`/`.og-toggle-window` →
`.og-fusecap`/`.og-fusecap-hi` olarak yeniden adlandırıldı.

### 15.2 Kompanzasyon kondansatörü rengi

`halitguner.com`'dan indirilen gerçek "1600 kVA Dahili Tip AG Pano TEDAŞ Tipi" ürün fotoğrafı
incelendi (`pano-referans.jpg`, yalnızca referans amaçlı görüntülendi, projeye gömülmedi).
Fotoğrafta güç kondansatörleri **koyu/siyah** gövdeli; bizim modelimiz açık gri (`#D9DCDD`,
diğer birçok parçayla paylaşılan `mat.face`) kullanıyordu. Düzeltme: yeni özel malzeme
`mat.capBody` (`#26292b`) 3D'de, `--cap-body` token'ı (aynı ton) 2D'de tanımlandı; `og-comp`
artık dolu koyu daire (önceden yalnızca ince gri ana hattı), basınç tahliye izleri daha görünür
kontrast için açık gri (`#6a7178`) yapıldı.

### 15.3 TVOC-2 ve MPR-53CS: tanınabilir cihaz yüzü

- **MPR-53CS** (ENTES MPR-53CS-DIN/96 şebeke analizörü): ürün sayfası **96×96 mm DIN panel
  formatını doğruladı** — bizim ölçümüz (`box(96,96,...)`) zaten tesadüfen doğruydu. Eksik olan
  gövdenin "meç yüzü": gerçek cihazda 3 satırlık LCD + gezinme tuşları var. Hem 3D'ye hem
  (önceden hiç yoktu) 2D'ye ekran + 4 tuş detayı eklendi.
- **TVOC-2** (ABB Arc Guard System TVOC-2): tam ölçü dokümantasyonuna erişilemedi — ABB ürün
  sayfası `WebFetch` zaman aşımına uğradı, katalog PDF'i indirildi ama gömülü görsel PDF olduğu
  için metin çıkarımı başarısız oldu; bu ortamda `pdftoppm`/poppler-utils kurulu olmadığından
  PDF sayfalarını görsel olarak inceleme (Read ile) de mümkün olmadı. Doğrulanan tek şey: gerçek
  cihazın dokunmatik HMI ekranı var, panel kapağına monte edilebiliyor (arama sonuçlarından).
  Kesin piksel ölçüsü yerine **makul bir oran tahmini** kullanıldı: gövdenin çoğunu kaplayan tek
  parça dokunmatik ekran (buton yok — gerçek cihaz dokunmatik), bu açıkça bir tahmin olarak
  işaretleniyor, kesin spec olarak sunulmuyor.
- Her iki cihaz için yeni paylaşılan malzeme/token: 3D'de `mat.screen` (koyu cam, hafif yeşil
  emissive), 2D'de `--screen` + `.og-screen`/`.og-screen-bezel`/`.og-screen-btn`.

### 15.4 Dürüst tavan (kullanıcıya aynen iletildi)

"Neredeyse birebir" hedefi kısmen karşılanabilir: DSYA artık doğru **tür** bir bileşen (MCB
değil, gerçek NH sigortalı ayırıcı formunda), MPR-53CS gerçek **ölçüsünde** (96×96mm) ve artık
tanınabilir bir **yüze** sahip, kondansatörler gerçek **rengine** yakın. Ama şunlar hâlâ
prosedürel bir kavramsal ikiz, ADM/GDZ'nin sahadaki gerçek donanımının CAD-birebir kopyası
değil: (1) TVOC-2'nin tam ölçüsü/HMI düzeni doğrulanamadı, makul tahmin kullanıldı; (2) hiçbir
gerçek fotoğraf/CAD modeli doğrudan gömülmedi (telif riski + GK4 offline kuralı); (3) boya
dokusu, cıvata detayları, üretici logoları gibi ince yüzey detayları modellenmedi — bunlar
maliyet/fayda açısından bu aşamada anlamlı değil. Bu sınırlar kullanıcıya açıkça anlatıldı,
"artık fotogerçekçi/birebir" diye abartılmadı.

**Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı (three.js chunk
uyarısı önceden var, bu değişiklikle ilgisiz). ADM-00014'te 2D ve 3D görünüm chrome-devtools ile
kontrol edildi: kondansatörler artık koyu dolu daire + tahliye izi, MPR-53CS'de ekran+4 tuş,
TVOC-2'de tek parça koyu ekran görünüyor; konsolda hata yok (yalnızca ilgisiz, önceden var olan
bir form-alanı erişilebilirlik uyarısı).

**Ekran görüntüleri:** `assets/ekran/`'daki 8 dosyadan yalnızca panonun iç görünümünü gösteren
ikisi (`02-pano-detay-alarm.png` → `/pano/ADM-00014`, "Ön görünüş"; `02-pano-detay-normal.png` →
`/pano/ADM-00301`, sakin durum) bu değişikliklerden etkileniyordu; aynı rota/sekme kombinasyonuyla
yeniden çekildi. Diğer 6 dosya (Filo, Alarm konsolu, Trend, Kara kutu, Cihaz sağlığı, Bölge) pano
iç görünümünü göstermediğinden dokunulmadı — gereksiz yeniden çekim yapılmadı.

## 16. Bölge haritasına gerçek konum ekleme (15 Eylül, "bölge haritasına gerçekten harita ekleyebilir miyiz")

Önceki yanıtım (§15'ten sonraki turda) "kontrat değişikliği onayı gerekiyor" demişti — bu yanlış
çıktı. Kullanıcı `main`'i çekip Kişi B'nin kulvarını (backend) entegre ettikten sonra kontrolü
tekrarladığımda görüldü ki `PanelSummary.lat`/`lon` zaten **onaylı, yayında olan** bir sözleşme
alanı (`contracts/openapi.yaml`, `backend/app/api/views.py:98-99` zaten dolduruyor); bekleyen
`2026-09-14-fleet-health-bulk.md` önerisi bambaşka bir şey öneriyor (il/ilçe + toplu sağlık ucu),
lat/lon kullanmak için o onaya ihtiyaç yok.

Gerçek engel veri eksikliğiydi: `frontend/src/api/mock.ts` her pano için `lat: null, lon: null`
yazıyordu. Ama mock'taki 20 pano adının **hepsi zaten gerçek bir ilçe/semt adı** (Efeler, Nazilli,
Söke, Bodrum, Selçuk, Bornova, Karşıyaka, Yunusemre... — ADM=Aydın/Denizli/Muğla, GDZ=İzmir/Manisa
hizmet bölgesiyle tutarlı). Bu ilçelerin gerçek merkez koordinatları (`DISTRICT_COORDS`, kod içi
yorumla "ilçe merkezi hassasiyetinde, gerçek trafo GPS pini değil" diye işaretli) eklendi.

`pages/BolgeHaritasi.tsx` yeniden yazıldı: en az 2 panoda koordinat varsa (`GeoHarita`)
enlem/boylamdan yerel, ölçek-korumalı bir izdüşümle (boylam, ortalama enlemin kosinüsüyle
düzeltiliyor) SVG üzerine gerçek konumlarına yerleştiriliyor; yoksa eski dağıtım-şirketi
gruplaması (`SirketGruplari`) korunuyor — gerçek backend'den koordinat gelmezse (alan opsiyonel)
olmayan veri asla olmuş gibi gösterilmiyor. Gerçek harita karosu (Google/Mapbox/OSM) kullanılmadı
— GK4 tamamen offline çalışmalı; yalnızca pusula işareti ve kesikli çerçeve var, uydurma bir
kıyı şeridi/sınır çizimi eklenmedi (elimde gerçek bir offline vektör sınır verisi yok, hayalden
kıyı şekli çizmek dürüstlük kuralına aykırı olurdu).

**Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı. `/bolge` rotası
chrome-devtools ile 1440px ve 390px (mobil) genişlikte kontrol edildi — yatay taşma yok, konsolda
hata yok. Sonuç görsel olarak da anlamlı: GDZ panoları (İzmir/Manisa) ve ADM panoları
(Aydın/Denizli/Muğla) haritada kendiliğinden iki ayrı coğrafi kümeye ayrılıyor, çünkü bu gerçek
hizmet bölgeleri gerçekten ayrık. Ekran görüntüsü kullanıcıya gönderildi (SendUserFile),
`assets/ekran/07-bolge-haritasi.png` ve `docs/16-ux-tasarim.md` §3/§6 güncellendi.

## 17. Gerçek ilçe sınırları (polyline) + aktif sekmede tam marka turuncusu (16 Eylül)

Kullanıcı iki somut istekte bulundu: (a) aktif nav sekmesi (`.nav-link.active`) artık gri/grafit
değil, tamamen marka turuncusu + beyaz metin olsun; (b) Bölge haritasına gerçek ilçe sınırları
(polyline) eklensin, üzerine gelince hafif büyüsün, sınırlar turuncu ve hafif "glow"lu olsun.

**(a)** `app.css`: `.nav-link.active { background: var(--plate); ...box-shadow: inset 0 -3px 0
var(--brand); }` → `{ background: var(--brand); color: #fff; }`. Bu, §3.2'deki "turuncu = P2
alarmı" karışıklığından kaçınma gerekçesini bu ÖZEL öğe için kullanıcının doğrudan talimatıyla
geçersiz kılıyor — nav sekmeleri bir alarm etiketi taşımıyor (Kritik/Alarm/Uyarı gibi), yalnızca
`.console-filters` (alarm şiddeti butonları) için orijinal gerekçe hâlâ geçerli, ona dokunulmadı.

**(b)** Önceki oturumda (§16) yalnızca nokta konumları gerçek enlem/boylama taşınmıştı, ilçe
*sınırları* yoktu. Gerçek, isimlendirilmiş kamu verisi olmadan bir sınır şekli "çizmek" hayal
ürünü olurdu (dürüstlük kuralı) — bu yüzden gerçek bir kaynak arandı ve bulundu:
**UN OCHA HDX `COD-AB-TUR`** (Türkiye idari sınırları, CC BY-IGO), `ttezer/turkiye-harita-verisi`
(MIT kod lisanslı) GitHub deposundaki pinlenmiş snapshot'ı üzerinden indirildi (`dist/geojson/
districts.geojson`, 973 ilçe, 14,7 MB; isim eşlemesi `dist/json/districts.json`'daki `plate_code`
+ `name_ascii` alanlarıyla yapıldı). Yalnızca mock verideki 20 ilçe (Efeler, Bornova, Söke...)
eşleştirildi ve indirildi — tam Türkiye verisini pakete gömmek anlamsız ve gereksiz büyük olurdu.

Ham geometri küçük bir UI haritası için çok ayrıntılıydı (bazı sahil ilçelerinde ~9500 nokta,
Bodrum/Fethiye gibi ada/koy dolu MultiPolygon'lar). Bir Python betiğiyle (a) Douglas-Peucker
sadeleştirmesi (~250 m tolerans) uygulandı, (b) MultiPolygon'larda en büyük parçanın %3'ünden
küçük adacıklar atıldı (görsel gürültüyü azaltmak için — ilçenin ana şekli değişmedi, yalnızca
önemsiz küçük adalar/koylar UI ölçeğinde anlamsız olduğu için çizilmedi). Sonuç: 917 KB → 26,8 KB,
~40.000 nokta → 1.493 nokta. Çıktı `frontend/src/data/ilce-sinirlari.json`'a kondu (build zamanı
pakete gömülür, GK4: çalışma zamanında hiçbir ağ isteği yok).

`pages/BolgeHaritasi.tsx`: `projector()` artık ham `[boylam, enlem]` noktalarını projekte ediyor
(hem pano konumları hem sınır köşe noktaları için ortak); her panonun adının ilk kelimesi
(`districtKey`, `api/mock.ts`'teki `DISTRICT_COORDS` anahtarlarıyla aynı sözleşme) sınır verisinde
aranıyor, bulunursa `<path>` olarak çiziliyor (Polygon/MultiPolygon, `fillRule="evenodd"` ile delik
varsa doğru işleniyor). Gerçek backend'den farklı ilçe adları gelirse (sınır verisinde karşılığı
yoksa) yalnızca nokta çizilir, sınır sessizce atlanır — çökme yok, sahte sınır de yok.

CSS (`app.css`, yeni `.geo-district`): turuncu kontur + SVG `<filter id="geo-glow">`
(`feGaussianBlur` + `feMerge`) ile sürekli hafif parlama; `:hover`'da `transform: scale(1.045)`
(`transform-box: fill-box` ile ilçenin kendi merkezine göre büyür, sayfa köşesine kaymaz), dolgu
ve kontur biraz koyulaşır. `prefers-reduced-motion: reduce`'da geçiş anında olur (proje genelindeki
kural). CC BY-IGO atıf zorunluluğu haritanın altına eklendi (kaynağa bağlantılı).

**Doğrulama:** `tsc --noEmit` temiz, 71/71 test yeşil, `vite build` başarılı (JSON paket boyutunu
~27 KB artırdı, beklenen). `/bolge` sayfası chrome-devtools ile 1440px ve 390px'de kontrol edildi
— gerçek ilçe şekilleri (Bodrum'un yarımada silüeti dahil) doğru çiziliyor, hover büyütme/parlama
çalışıyor, yatay taşma yok, konsolda hata yok. `/cihaz-sagligi` gibi başka bir sayfada aktif nav
sekmesinin tam turuncu + beyaz metin göründüğü ayrıca doğrulandı.

## Kaynaklar

- ADM Elektrik: <https://www.admelektrik.com.tr/> · GDZ Elektrik: <https://www.gdzelektrik.com.tr/>
  (CSS token'ları ve logo SVG'leri tarayıcıda okundu)
- Aydem Enerji logo kılavuzu: <https://www.aydemenerji.com.tr/medya-merkezi/logolar/>
- ISA-101 renk stratejisi: <https://industrialmonitordirect.com/blogs/knowledgebase/isa-101-high-performance-hmi-design-principles-color-strategy>,
  <https://www.realpars.com/blog/hmi-colors>
- ABB SWICOM: <https://new.abb.com/medium-voltage/digital-substations/monitoring-and-diagnostics-solutions/condition-monitoring-for-switchgear-SWICOM>
- Schneider EcoStruxure Continuous Thermal Monitoring: <https://www.productinfo.schneider-electric.com/esxp_digital_apps_iec/ctm/English/ESXP2GE007EN-05_Continuous_Thermal_Monitoring.pdf>
- Siemens Electrification X: <https://www.siemens.com/global/en/products/energy/topics/electrification-x/distribution-grid-monitoring.html>
- Hitachi Energy Lumada APM: <https://www.hitachienergy.com/us/en/news-and-events/press-releases/2023/10/hitachi-energy-launches-the-next-generation-of-its-asset-performance-management-solution-lumada-apm>
- GE Vernova GridOS: <https://www.gevernova.com/news/press-releases/ge-vernova-launches-gridos-distribution-industrys>
- Emerson DeltaV Live: <https://www.emerson.com/en-us/automation/control-and-safety-systems/distributed-control-systems-dcs/deltav-distributed-control-system/deltav-live>
- Siemens iX temalar: <https://ix.siemens.io/docs/styles/theming/usage-designers>
- Honeywell Experion Operations Assistant: <https://www.honeywell.com/us/en/press/2026/03/honeywell-unveils-commercial-launch-of-ai-powered-control-room-assistant-following-successful-pilot>
- Cognite Industrial Canvas: <https://www.cognite.com/en/industrial-canvas>
- Tesla enerji akışı: <https://gridtitans.com/blogs/news/how-the-tesla-app-works>
- Kontrol odası durumsal farkındalık (Infostructure): <https://doi.org/10.3390/en19061472>
- Calm computing: <https://ixdf.org/literature/topics/calm-computing>
