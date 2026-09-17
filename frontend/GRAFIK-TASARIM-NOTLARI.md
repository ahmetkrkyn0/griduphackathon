# Grafik tasarımı · 17 Eylül 2026

Yoğun kontrol merkezi kullanımında önce ölçümün anlamı ve son değeri, sonra eğilimi okunmalıdır. Görsel değişiklikler gerçek ölçüm verisini, boşluklarını ve mevcut etkileşimleri korur.

## İncelenen örnekler

- [Siemens Industrial Experience: grafikler](https://ix.siemens.io/docs/components/charts-overview/overview): endüstriyel arayüzle tutarlı grafik teması. Burada mevcut hafif SVG altyapısı korundu; ek grafik kütüphanesi indirilmedi.
- [Siemens: çizgi grafiği](https://ix.siemens.io/docs/components/line-chart/overview): zamana bağlı eğilimler için çizgi grafiği ve sınırlı seri sayısı.
- [Carbon: eksenler ve etiketler](https://carbondesignsystem.com/data-visualization/axes-and-labels/): anlaşılır ölçüm isimleri, metrikler ve zaman aralığına uygun eksen etiketleri.
- [Carbon: basit grafikler](https://carbondesignsystem.com/data-visualization/simple-charts/): iki ölçüm arasındaki ilişkiyi göstermek için dağılım grafiği.

## Uygulanan kararlar

- SVG genişliği kartın gerçek genişliğini izler. Telefonda grafik küçültülerek metinler okunmaz hale getirilmez; eksen etiketleri sabit okunabilir boyutta kalır, yatay etiket sayısı azaltılır.
- K/K₀ ve ΔT trend ekranında ayrı kartlarda sunulur. Böylece farklı birimler ve ölçekler aynı çizgi yüksekliğiyle yanlış karşılaştırılmaz. Diğer ekranların çift eksen desteği korunur.
- K/K₀ mavi, sıcaklık farkı turuncu, çiy noktası marjı yeşildir. Marka rengi durum/alarm renklerini değiştirmez.
- Son değerler zaman damgasıyla okunur; zaman dilimi Türkiye saatidir. Eksik ölçümler çizgide boşluk olarak kalır. Klavye ve işaretçiyle ölçüm inceleme, seri açma/kapama korunur.
- Risk gibi sınırları tanımlı ölçümler için sabit eksen aralığı desteği vardır. K/K₀ grafiğinde başlangıç 1,0 referansı gösterilir; bu bir alarm eşiği olarak sunulmaz.
- Dağılım grafiğinde dönem başına gerçek örnek sayısı ve doğrusal eğilimler görünür. Geçersiz sayılar çizime ve regresyona alınmaz. Eğilim tek başına arıza teşhisi olarak sunulmaz.
- Risk dağılımında süre tahmini olmayanlar ayrı sütundadır. Dar ekranda nokta isimleri sadece odaklandığında görünür; ayrıntı satırı seçili panoyu açıklar.

## Sonraki veri odaklı iyileştirmeler

Kalite bayrakları ve gerçek sensör örnekleme aralığı API tarafından sağlandığında veri kesintisi bantları; işletmenin onayladığı eşikler sağlandığında eşik bölgeleri eklenebilir. Mevcut ölçümlerden yeni alarm eşikleri veya kesin arıza yorumları üretilmedi.
