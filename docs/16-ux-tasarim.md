# 16 — UX Tasarımı

> **Sahip:** Kişi C · Kod: `frontend/src/`. Ekran görüntüleri: `assets/ekran/` (bkz. §5).

## 1. Tasarım yönü: "RAL 7035"

Üç yön denendi (`frontend/sketches/`, atılabilir): A) pano gövdesinin RAL 7035 açık grisi zemin
alan, ISA-101 tarzı bir kontrol odası ekranı; B) mühendislik çizim kâğıdı üzerinde canlı tek hat
şeması; C) açılışta 14 günlük "sınıra kalan süre" zaman ekseni. **A seçildi**, C'nin zaman ekseni
Filo ekranının açılış öğesi olarak entegre edildi (aşağıda §2.1).

**Gerekçe:**
- Jüride ADM/GDZ'nin saha ve SCADA ekiplerinden kişiler olması muhtemel (rapor §9). Bu kitle her
  gün bir kontrol odası ekranı kullanıyor; ISA-101/yüksek performanslı HMI dilini (gri zemin, renk
  yalnızca anormal durumda) tanıyorlar ve "bilinçli bir seçim" olduğunu anlıyorlar.
- B (tek hat şeması) yalnızca tek pano için anlamlıydı, filo görünümünü taşımıyordu.
- Renk körlüğüne karşı: öncelik her yerde **renk + şekil + karakter** ile gösterilir (`PrioMark.tsx`):
  P1 kare "1", P2 üçgen "2", P3 daire "3", SYS çerçeveli "S". Renk yalnızca normal dışı durumda
  kullanılır (bkz. `frontend/src/theme.css` token'ları).

## 2. Ekran envanteri (rapor §6.7)

| # | Ekran | Dosya | Durum |
|---|---|---|---|
| 1 | Bölge haritası | `pages/BolgeHaritasi.tsx` | Yapıldı (§3'teki kapsam notuyla) |
| 2 | Filo listesi | `pages/FiloListesi.tsx` | Yapıldı (TC1) |
| 3 | Pano detay — dijital ikiz | `pages/PanoDetay.tsx`, `components/OnGorunus.tsx` | Yapıldı (TC1+TC2: nokta trendi eklendi) |
| 4 | Alarm konsolu | `pages/AlarmKonsolu.tsx` | Yapıldı (TC2) |
| 5 | Trend & korelasyon | `pages/TrendKorelasyon.tsx` | Yapıldı (TC3) |
| 6 | Olay analizi (kara kutu) | `pages/OlayAnalizi.tsx` | Yapıldı (TC3) |
| 7 | Cihaz sağlığı | `pages/CihazSagligi.tsx` | Yapıldı (§3'teki kapsam notuyla, TC3) |
| 8 | Mobil saha (PWA) | — | **Won't** (PLAN.md MoSCoW) |
| 9 | Devreye alma sihirbazı | — | **Won't** (PLAN.md MoSCoW) |

**Kabul kriteri karşılandı:** 9 ekranın 7'si çalışıyor (PLAN.md TC3 kabul ölçütü).

## 2.1 Filo ekranı: "sınıra kalan süre" ekseni

Açılış ekranının kahramanı bir dashboard değil, bir zaman eksenidir: paneller sorunun **ne zaman**
kritikleşeceğine göre dizilir (`components/SureEkseni.tsx`). Eksen logaritmiktir (`axisFraction`,
`lib/worklist.ts`) — yakın gelecek geniş, uzak gelecek sıkışık — çünkü operatör için "6 gün" ile
"7 gün" arasındaki fark, "60 gün" ile "61 gün" arasındakinden çok daha önemlidir. Kartlar aynı
zaman diliminde çakışırsa `layoutAxisRows` satırlara dağıtır (birim testli, `worklist.test.ts`).

## 3. Bilinçli kapsam sınırları (dürüstlük kuralı, Bölüm C)

İki ekran, sözleşmede eksik bir alan yüzünden tam istenen granülerlikte değil. İkisi de
`contracts/changes/2026-09-14-fleet-health-bulk.md` önerisiyle çözülebilir:

1. **Bölge haritası**, il/ilçe bazlı değil **dağıtım şirketi bazlı** (ADM/GDZ) gruplanır. Sözleşmede
   yalnızca opsiyonel `lat`/`lon` var (çoğu zaman boş); coğrafi olarak yanlış bir kırılımı "harita"
   diye sunmak yerine, gerçekten pano kimliğinden çıkarılabilen tek yapısal ayrımı gösteriyoruz.
2. **Cihaz sağlığı**, toplu bir "filo sağlığı" ucu olmadığı için görünen panoları tek tek
   (sınırlı eşzamanlılıkla, 6) çeker. 20 panoda görünmez, 1.000 panoda yavaşlar; ekranın altında
   bu açıkça yazar.

Gerçek harita karosu hiçbir ekranda kullanılmaz (GK4: yığın internetten bağımsız çalışır).

## 4. Erişilebilirlik

- Tüm etkileşimli SVG noktaları (`OnGorunus.tsx`) `role="button"`, `tabIndex`, klavye (Enter/Space)
  ile de seçilebilir; odak halkası `:focus-visible` ile görünür (tema rengi).
- Grafikler (`CizgiGrafik`, `SacilimGrafik`) `role="img"` + açıklayıcı `aria-label` taşır.
- Hareket: `prefers-reduced-motion: reduce` durumunda nokta halka animasyonu (`og-halo`, `chart`
  öğeleri) durur (`theme.css`).
- Kontrast: gövde metni `--ink` (#212629) / zemin `--bg` (#E2E4DF) ~11:1, WCAG AA'nın üstünde.
- 400 px genişlikte (cep telefonu) yatay taşma yok; tüm tablo/eksen içerikleri kendi
  `overflow-x: auto` kapsayıcısında (`tbl-wrap`).

## 5. Ekran görüntüleri

`assets/ekran/` altında, örnek veri modunda (`npm run dev:mock`) alınmış ekran görüntüleri:

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

## 6. Sonraki adım

KiCad şeması gibi, "toplu cihaz sağlığı" ucu da bir sonraki iterasyonun ilk maddesidir — üç onay
alırsa Bölge haritası gerçek il/ilçe kırılımına, Cihaz sağlığı tek bir isteğe düşer.
