# Açık tema ve grafik revizyonu

19 Eylül 2026 — önceki koyu grafik tasarımının yerine uygulandı.

- Grafikler, ölçüm özetleri, araç çubukları ve veri tabloları açık renk paletine döndü. Yan menü lacivert kaldı.
- Yerel Inter fontuna geçildi; arayüz gövdesi 15 px, tablo/filtreler ağırlıkla 13 px, grafik eksenleri 12 px. Satır aralıkları artırıldı.
- Pano, nokta ve dönem kontrolleri aynı alt çizgiye hizalandı; seçiciler 40 px yüksekliğinde.
- Açık / Rafta / Tümü ve diğer seçimlerde aktif durum marka turuncusu oldu.
- Grafik altındaki veri gölgeli kalın kaydırıcı, sade ve ince bir aralık seçicisine dönüştü. Yakınlaştırma işlevi korunuyor.
- Risk dağılımına okunaklı özet, hafif çizgiler ve daha belirgin noktalar eklendi.
- Zaman planı ortak logaritmik zaman ölçeği üzerinde yatay süre çizgilerine dönüştü. Süre tahmini bulunmayan panolar ayrı bağlantılar halinde gösteriliyor.

## Referansların karşılığı

[ThingsBoard Smart Energy](https://thingsboard.io/use-cases/smart-energy/) açık dashboard kartları, ölçüm özetleri ve tablo/grafik birlikteliği için; [ABB varlık görünürlüğü yaklaşımı](https://www.abb.com/global/en/company/innovation/news/granular-visibility) sağlık ve bakım önceliği düzeni için; [Siemens iX grafikleri](https://ix.siemens.io/docs/components/line-chart/overview) grafik etkileşimleri için referans alındı. Bunlar özgün uygulamaya yapılan uyarlamalardır, birebir ekran kopyaları değildir.

## Siemens görseli ve 3D farkı

Referanstaki görsel bir **yüzey grafiği**. Önceki uygulama bir **nokta dağılımıydı**; fark teknik kapasiteden değil seçilen grafik türünden geliyordu. Kullandığımız ECharts GL yüzey çizimini destekliyor; [Siemens'in dokümanı](https://ix.siemens.io/docs/components/3d/overview) da bu türü içeriyor.

Artık 3D ölçüm uzayında iki seçenek var:

1. **Ölçüm noktaları:** aynı zamanlı gerçek API örnekleri.
2. **Isıl yüzey · model:** ΔT = K₀ × (K/K₀) × I² ilişkisiyle tel örgülü, renk geçişli yüzey.

K₀, geçerli örneklerin ΔT / (I² × oran) katsayılarının medyanından hesaplanır. Yüzey yalnızca gözlenen akım ve oran aralıklarında oluşturulur. Aralık içindeki tüm kombinasyonlar ölçülmüş değildir; bu yüzden yüzey açıkça model olarak işaretlenir. Yeterli örnek veya iki eksende değişim yoksa yüzey seçeneği kapalıdır. Bu, yeni bir arıza tahmin algoritması değildir.

Siemens örneğindeki dalgalı şekli üretmek teknik olarak mümkün; fakat bizim ısıl ilişkimiz aynı şekli vermiyor. Görsel benzerlik için ölçümden bağımsız dalgalar eklenmedi. Fiziksel pano ikizi ayrı bir ekran olarak devam ediyor.

Denemek için `/trend/ADM-00014` → **3D ölçüm uzayı** → **Isıl yüzey · model**.

## Görseller

- [Açık analiz ekranı](assets/ekran/light-analysis.png)
- [3D yüzey](assets/ekran/light-surface.png)
- [Risk dağılımı](assets/ekran/light-risk.png)
- [Zaman planı](assets/ekran/light-plan.png)
- [Turuncu alarm filtreleri](assets/ekran/light-alarm-filters.png)
- [Mobil görünüm](assets/ekran/light-mobile.png)

## Doğrulama

114 birim testi, 7 Edge tarayıcı testi ve üretim derlemesi geçti. Yeni kontroller: açık grafik zemini, filtre hizalaması, turuncu aktif alarm filtresi, yüzey görünümü ve modelin ölçümden ayrılması. Isıl yüzeyin bilinen matematiksel ilişkiyi koruduğu ve yetersiz veriden üretilmediği ayrıca test edildi. Masaüstü/mobil kontroller örnek veri modunda yapıldı.
