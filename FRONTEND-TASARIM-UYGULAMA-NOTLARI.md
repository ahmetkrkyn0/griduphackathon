# Endüstriyel arayüz ve grafik güncellemesi

> Bu dosya ilk uygulamanın kaydıdır. Güncel açık tema, Inter fontu ve 3D yüzey değişiklikleri: [Açık tema revizyonu](FRONTEND-ACIK-TEMA-REVIZYONU.md).

19 Eylül 2026 · Uygulandı · Görsel kontroller örnek veri modunda yapıldı.

## Tasarım yönü

Siemens iX'in çizgi grafiklerini, çoklu eksen örneklerini, gelişmiş grafik araçlarını ve 3D demosunu inceledim. Ana yaklaşım; koyu analitik yüzey, sakin ızgara, yüksek kontrastlı seri renkleri ve grafiğe yakın kontroller. Bunları mevcut pano izleme akışına uyarladım. Siemens'in logosu, yazı tipi, uygulama şablonu veya ekran görselleri ürüne taşınmadı. Barlow ve GDZ/ADM kimliği devam ediyor.

ThingsBoard'un sayaç, alarm ve grafiklerin birlikte okunabildiği ekranları; bilgi kartları ve analiz düzeni için ikinci referans oldu. Ana çalışma alanı açık, grafikler koyu tutuldu. Böylece tablo ve alarm okumakla ölçüm incelemek arasında belirgin bir görsel ayrım var.

| İncelenen kaynak | Dikkat edilen özellik | Bizim uygulamadaki karşılığı |
|---|---|---|
| [Siemens iX grafik sistemi](https://ix.siemens.io/docs/components/charts-overview/overview) | ECharts tabanı, seri renkleri, eksen ve veri durumları | Ortak grafik yüzeyi, tutarlı araç çubuğu ve boş ölçüm mesajları |
| [Siemens iX çizgi grafikleri](https://ix.siemens.io/docs/components/line-chart/overview) | Çoklu seri, çift eksen, okunaklı ızgara | Pano ayrıntısı ve olay analizinde iki eksenli çizgi grafikler |
| [Siemens iX gelişmiş grafik araçları](https://ix.siemens.io/docs/components/special-chart/overview) | Yakınlaştırma, sıfırlama, dışa aktarma | Zaman aralığı kaydırıcısı, Ctrl + tekerlek, aralık sıfırlama, SVG indirme |
| [Siemens iX 3D](https://ix.siemens.io/docs/components/3d/overview) | Gerçek üçüncü boyutu olan verilerin mekânsal gösterimi | Akım–ΔT–K/K₀ dağılımı, döndürme ve kamera kontrolleri |
| [Siemens iX bileşenleri](https://ix.siemens.io/docs/components/overview) | Uygulama kabuğu, paneller ve durum hiyerarşisi | Lacivert gezinme, daha keskin kartlar, kompakt seçim kontrolleri |
| [ThingsBoard Smart Energy](https://thingsboard.io/use-cases/smart-energy/) | Ölçüm, varlık listesi ve alarm birlikteliği | Ölçüm özetleri, analiz kartları, mevcut alarm/kanıt akışının korunması |

Siemens referansları: [çizgi grafiği ekranı](assets/tasarim-referanslari/siemens-line-detail.png), [3D demo ekranı](assets/tasarim-referanslari/siemens-3d-detail.png). Bunlar üçüncü taraf araştırma görselleridir; bizim uygulamamızdan alınmamıştır.

## Uygulanan değişiklikler

### Ortak görünüm

- Lacivert yan menü, açık gri çalışma alanı, turuncu marka vurgusu.
- Operasyon özetinde ayrı KPI kartları, daha belirgin panel başlıkları ve tablo sütunları.
- Ortak filtre, dönem seçimi, kart, gezinme ve mobil düzen güncellemeleri.
- Fiziksel 3D ikizde yeni kontrol yüzeyi ve seçili nokta başlığı. Termal fark ölçeğinde birim K olarak düzeltildi.

### Çizgi ve dağılım grafikleri

Elle çizilen ölçüm grafikleri ECharts tabanına geçirildi. Değişiklikler yalnızca trend sayfasında değil, aynı bileşeni kullanan pano ayrıntısı ve olay incelemesinde de görünür.

- Çizgi grafiklerinde zaman aralığı seçimi ve yakınlaştırma.
- Seri açma/kapatma, çapraz imleç ve ölçüm araç ipuçları.
- Çift Y ekseni, başlangıç referansı ve olay zamanı işaretleri.
- SVG indirme; grafikler raster ekran görüntüsüne bağımlı değil.
- Türkçe sayılar ve Türkiye saat dilimi; kısa zaman aralıklarında saat etiketleri.
- Çizgi grafiği altında klavyeyle kullanılabilen ölçüm zamanı seçicisi.
- Dağılım grafiklerinde eğilim doğruları, örnek sayıları ve sayısal tablo.
- Eksik/null örneklerde çizgi kesilir; sıfır ölçümler kayıp veri sayılmaz.

Seri kimlikleri korundu: mavi, turuncu ve yeşil serilerin koyu zemine uygun açık karşılıkları kullanıldı. Alarm öncelik renkleri ayrıca korunuyor.

### 3D ölçüm uzayı

Trend ekranındaki **3D ölçüm uzayı** düğmesi şu eksenleri açar:

- X: faz akımı, A.
- Y: bağlantının ortam üzerindeki sıcaklık artışı, K.
- Z: başlangıç ısıl direncine göre K/K₀ oranı.

Her nokta, üç serinin **aynı zaman damgasındaki** geçerli ölçümlerinden oluşur. Yakın zamanlar birleştirilmez; boşluklar tahminle doldurulmaz. İlk ve ikinci dönem, zaman aralığının orta noktasına göre turkuaz ve mor gösterilir. 2D dağılım karşılaştırması aynı zaman ayrımını kullanır.

Siemens'in yüzey grafiği ilham verdi; mevcut verilerimiz için yüzey uydurmak yerine ölçüm noktalarını kullandım. Bu görünüm fiziksel pano modelinden ayrı bir analiz aracıdır. WebGL açılamazsa açıklama ve ölçüm tablosu kalır. Nötr gibi faz akımı eşleşmeyen seçimlerde veri eksikliği belirtilir.

## Deneme rotası

1. `frontend` içinde `npm run dev:mock` çalıştırın ve terminalin verdiği adresi açın.
2. `/trend/ADM-00014` adresine gidin. Gevşek bağlantı örneği, değişimi göstermek için uygundur.
3. K/K₀ eğilimini ve ilk/ikinci dönem dağılımını karşılaştırın.
4. **3D ölçüm uzayı** seçin; döndürün, **Önden** ve **Görünümü sıfırla** kontrollerini deneyin.
5. `/pano/ADM-00014` üzerinden fiziksel ikizi ve çift eksenli trendi inceleyin.
6. `/olay/EVT-42` üzerinden olay grafikleri ve yazdırma görünümünü açın.

Örnek veri modu sentetik ölçümler içerir. Yeni grafikler mevcut API serilerini tüketir; yeni bir tahmin veya teşhis modeli eklenmedi. Gerçek backend/saha bağlantısıyla doğrulama bu çalışmanın parçası değildi. Mevcut demo olay listesinde kara kutu örneği tanımlanmamış kayıtlar da bulunuyor; örneğin `EVT-55` 404 döndürür. İnceleme için tanımlı `EVT-42`, `EVT-51` veya `EVT-60` kullanılabilir.

## Ekran görüntüleri

Bu bölümdeki görseller güncellenmiş uygulamadan alınmıştır:

- [Operasyon özeti](assets/ekran/industrial-overview.png)
- [2D analiz](assets/ekran/analytics-2d.png)
- [3D analiz — ayrıntı](assets/ekran/analytics-3d-detail.png)
- [3D analiz — tam sayfa](assets/ekran/analytics-3d.png)
- [Fiziksel pano ikizi](assets/ekran/industrial-twin.png)
- [Mobil analiz](assets/ekran/industrial-mobile.png)
- [Olay inceleme](assets/ekran/industrial-event.png)
- [Yazdırma görünümü](assets/ekran/industrial-print.png)

## Teknik uygulama ve doğrulama

Grafikler `ChartSurface`, `CizgiGrafikImpl`, `SacilimGrafikImpl` ve `SpatialAnalysis` bileşenlerinde. Ortak tasarım `industrial.css` dosyasında. Ağır 2D ve 3D modülleri ilgili görünüm açıldığında yüklenir. Son üretim derlemesinde ana JavaScript dosyası yaklaşık 388 kB, gzip ile 127 kB; bu rakam fontlar, CSS ve sonradan yüklenen grafik/3D parçalarını içermez.

Grafik geçişi sırasında iki mevcut hata da düzeltildi: pano seçiminin yönlendiği `/trend/:panoId` rotasının eksik olması ve olay ayrıntısında veri geldikten sonra değişen React hook sırası. Yeni testler olay ayrıntısını da açıyor. Yazdırmada gezinme/araç çubukları gizleniyor, rapor başlığı ve imza alanları korunuyor.

- `npm test`: **112 test geçti**.
- `npm run build`: TypeScript ve üretim derlemesi geçti.
- `npm run test:e2e`: **6 tarayıcı testi geçti**; Edge üzerinde örnek veri modunda.
- Tarayıcı kapsamı: seri seçimi, dönem değiştirme, klavyeyle veri inceleme, SVG indirme, pano yönlendirmesi, 3D açma/kapatma ve kamera kontrolleri, WebGL yokken tablo, olay raporunun yazdırma görünümü.
- Yedi ana rota 1440 px ve 390 px genişlikte kontrol edildi; sayfa dışına yatay taşma veya JavaScript çökmesi görülmedi.

Tarayıcı testleri bu Windows ortamındaki Microsoft Edge'i kullanır. Başka bir ortamda `playwright.config.ts` içindeki tarayıcı kanalı uygun kurulumla değiştirilmelidir. Tam erişilebilirlik denetimi veya tüm tarayıcılar için uyumluluk sertifikasyonu yapılmış değildir.
