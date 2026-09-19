# Kontrol merkezi arayüzü — araştırma ve uygulama

16 Eylül 2026. Kullanım önceliği: kontrol merkezinde yoğun günlük operasyon.

## Tasarım yönü

ADM/GDZ marka turuncusu; grafit gezinme alanı; açık, nötr çalışma yüzeyleri; tek Barlow yazı ailesi. Görsel hiyerarşi görev sırasını izler: filo özeti → öncelik → pano → alarm nedeni → ölçüm ve olay analizi. Operasyon alanında renk, durum ve veri serisini açıklamak için kullanılır. Yüzeylerde dekoratif parıltı ve sürekli hareket yerine sınır, boşluk ve tipografi vardır.

Şirketlerin kamuya açık siteleri marka referansıdır; burada geliştirilen uygulama bir tüketici sitesi değil, vardiya boyunca kullanılan bir çalışma alanıdır. Mevcut GDZ görseli korunmuştur; ADM adı metin olarak gösterilir, yeni bir resmî logo üretildiği iddia edilmez.

## İncelenen birincil kaynaklar ve kararlar

| Kaynak | İncelenen yaklaşım | Projeye uygulama |
| --- | --- | --- |
| [GDZ Elektrik](https://www.gdzelektrik.com.tr/) ve [ADM Elektrik](https://www.admelektrik.com.tr/) | Kurumsal kimlik, ortak hizmet bağlamı | Turuncu vurgu, marka imzası, ADM/GDZ kapsamı |
| [Siemens Electrification X](https://www.siemens.com/en-us/products/electrification-x/) | Varlık durumu, operasyon verisi ve alarm görünürlüğü | Kalıcı gezinme; filo, alarm ve analiz arasında kısa yollar |
| [Siemens Industrial Experience](https://ix.siemens.io/docs/home/overview) | Endüstriyel uygulamalar için tutarlı bileşen ve etkileşim dili | Tek tip filtre, durum rozeti, tablo, gezinme ve odak göstergeleri |
| [Siemens iX grafik yaklaşımı](https://ix.siemens.io/docs/components/charts-overview/overview) | Eksenler, ölçekler, etiketler; ECharts entegrasyonu | Açıklanan birimler, düzenli eksen aralıkları, seri seçimi ve değer okuma |
| [Schneider EcoStruxure Power Monitoring Expert](https://www.se.com/us/en/product-range/65404-ecostruxure-power-monitoring-expert/) | Elektrik sistemi görünürlüğü, alarm önceliği, olay zaman çizelgesi | Alarm özeti ile ayrıntıyı ayırma; olay ve pano bağlantıları |
| [ABB SWICOM](https://electrification.us.abb.com/products/grid-automation/swicom) | Ekipmanın elektriksel ve mekanik durumunu anlaşılır tanıya dönüştürme | Pano ölçümleri, durum noktaları ve alarm gerekçesinin yan yana gösterimi |
| [Carbon eksen ve etiket rehberi](https://carbondesignsystem.com/data-visualization/axes-and-labels/) | Ölçek ve etiketlerin veri karşılaştırmasını desteklemesi | Okunabilir tick değerleri, sayısal biçimleme ve eksen birimleri |
| [Etien DSYA](https://etien.com.tr/160a-dikey-sigortali-yuk-ayirici-dsya) | NH bıçaklı sigortalı dikey yük ayırıcı yapısı | 2D ve 3D'de seramik sigorta gövdeleri, metal kontaklar ve taşıyıcılar |
| [ABB MNS](https://new.abb.com/low-voltage/products/switchgear/mcc-and-iec-low-voltage-switchgear/mns) | Fiziksel pano bölmeleri ve 3D e-katalog | Bölmeli pano, iç yerleşim, erişilebilir bağlantı noktaları için referans |
| [Three.js RoomEnvironment](https://threejs.org/docs/pages/RoomEnvironment.html) | PBR malzemeler için ortam aydınlatması | Çevrimdışı üretilen yansıma ortamı, daha anlaşılır metal ve sac yüzeyler |

Bu kaynaklar ürün ve etkileşim araştırmasıdır. Görünümler kopyalanmadı; herhangi bir endüstriyel standarda uyum sertifikası veya birebir üretici CAD doğruluğu iddia edilmez.

## Uygulanan değişiklikler

- Sabit sol menü, mobil menü, sayfa konumu, demo/bağlantı bilgisi ve klavyeden `Ctrl+K` pano araması.
- Dört filo göstergesi, risk dağılımı, kısa öncelik listesi, aranabilir ve sıralanabilir pano tablosu. Şirket ve durum filtreleri.
- Risk grafiğinde süre tahmini olmayan varlıklar ayrı sütunda. Süre tahminini arıza zamanı gibi sunmayan zaman planı.
- Kompakt alarm satırları; seçilen kaydın neden/işlem/süre ayrıntıları; mevcut onay ve rafa alma işlemleri.
- Etkileşimli çizgi grafikleri: fare ve klavye ile zaman seçimi, ölçüm değerleri, seri gizleme/gösterme, iki eksende açık birimler, veri boşluklarını birleştirmeyen çizgiler.
- Dağılım grafiğinde düzenli eksenler, çizim alanıyla sınırlı regresyon, karşılaştırma serileri. Analiz döneminde 7/14 gün seçimi. Pano değişiminde eski istek iptali; alarmın ilgili noktasını başlangıçta seçme.
- Pano görünümünde 2D metal/bakır yüzeyler, bağlantı parçaları, gövde vidaları ve kablo yolları. 3D'de stüdyo tipi ortam ışığı, katı yan saclar, taban, kablo kanalları, topraklama barası, etiket plakaları ve NH sigorta ayrıntıları.
- 3D açılışında bütün pano görünür; seçilen noktaya yaklaşma kullanıcının kontrolündedir. Kamera, etiket, kapak ve kapsam kontrolleri korunmuştur.
- Olay envanterinde tablo; olay detayında grafikler ve sabit zaman çizelgesi. Cihaz sağlığında arama, inceleme filtresi ve yenileme.
- Bölge haritasının önceki turuncu sınır ve çakışmasız etiket düzenlemesi korunmuştur.

## Görsel ve model tercihi

Pano, projenin ortak `panelGeometry.ts` koordinatlarını kullanır. 2D ve 3D'deki sensör kimlikleri bu yerleşime bağlıdır. Bu nedenle genel bir internet modelini yerleştirmek yerine mevcut modelin malzeme ve mekanik ayrıntıları iyileştirildi. Temsili olduğu ekranda belirtilir. Yeni dış görsel/model indirilmedi; çalışma anında harici CDN veya model sunucusu gerekmez.

Hazır model için en iyi sonraki kaynak, gerçek ekipmanın üretici CAD dosyasıdır. [ABB'nin MNS 3D kataloğu](https://new.abb.com/medium-voltage/switchgear/3d-ecatalogue/low-voltage/mns-front) bir araştırma referansıdır; projenin birebir panosu olduğu varsayılmamalıdır. Uygun CAD gelirse web için GLB'ye dönüştürülüp sensör koordinatlarıyla eşleştirilmelidir.

## Sonraki tasarım önerileri

1. **Pano kimlik kartına gerçek saha fotoğrafı:** ekipman tanıma ve uzaktan teyit için değerlidir. Tarih/konum bilgisiyle gösterilmeli; eski fotoğraf canlı durum yerine geçmemeli.
2. **Bakım geçmişi ve vardiya devri:** son müdahale, açık iş emri ve operatör notları alarm akışına bağlanmalı. Gerçek kayıt ve yetki modeli gerektirir; bu sürümde örnek iş emri uydurulmadı.
3. **Kaydedilmiş operatör görünümleri:** bölge, şirket ve vardiya sorumluluğuna göre filtre profilleri. Gerçek kullanıcı/rol altyapısıyla tamamlanabilir.
4. **Büyük filo için ölçekleme:** sunucuda arama/sıralama, toplu sağlık endpoint'i ve gerektiğinde tablo sanallaştırma. Mevcut filo boyutunda gereksiz paket ve ağ yükü eklenmedi.
5. **Koyu çalışma teması:** karanlık kontrol odasında ayrı bir tercih olarak değerlendirilebilir; grafik ve alarm kontrastları ayrıca kontrol edilmelidir.

## Doğrulama

### 17 Eylül kullanıcı geri bildirimi

- Sidebar'daki harf rozeti kaldırıldı; bölge kapsamı küçük harita ikonu ve metinle gösterilir.
- GDZ turuncusu aktif menü, üst kenar çizgisi, seçili envanter sekmesi ve arama vurgularına eklendi. Alarm renkleri değiştirilmedi.
- İlçe adları pano etiketinden ayrıldı. Coğrafi alanın içinde yeterli yer varsa gösterilir; dar ilçeler yakınlaştırıldığında okunur. Pano koordinatları değiştirilmez.
- Yunusemre'nin eski **demo** koordinatı Şehzadeler sınırına düştüğünden, [belediyenin iletişim sayfasındaki yol tarifi](https://www.yunusemre.bel.tr/iletisim) referans alınarak örnek ilçe merkezi konumu düzeltildi. Bu, gerçek pano GPS konumu değildir; canlı API koordinatları değiştirilmez.
- İl ve ilçe seçimi, il/ilçe/pano adı/kodu araması çevrimdışı veriyle çalışır. İl adları sınır dosyasındaki plaka kodlarına dayanır. Mahalle veri kaynağı bulunmadığından bu düzey sunulmaz.
- Grafiklerin koordinat alanı kapsayıcı genişliğine uyarlanır; mobilde yazılar tüm SVG ile birlikte küçültülmez. Analiz ekranında ısıl direnç indeksi ve sıcaklık artışı ayrı grafiklere ayrılır. Olay incelemesindeki risk grafiğinin ölçeği 0–100 olarak sabittir.

**Doğrulama:** Üretim derlemesi ve 8 dosyadaki 90 test başarılı. Tarayıcıda il/ilçe seçimi, Türkçe/boşluk toleranslı arama, boş sonuç, gerçek fare hareketiyle hover ve Yunusemre konumu doğrulandı. Görünen ilçe etiketlerinin kutu köşeleri kendi SVG çokgenlerinin içinde kaldı. 390 px ekranda harita filtreleri ve grafikler sayfa taşması oluşturmadı; grafik eksenleri yatay kaydırma gerektirmeden gerçek kart genişliğinde çizildi. Genel regresyonda yedi ekran, klavye araması, seri seçimi ve 2D/3D geçişi de kontrol edildi. Grafik araştırması: [ayrıntılı notlar](GRAFIK-TASARIM-NOTLARI.md).

### Harita performansı düzeltmesi

Zoom sırasında 96 ilçe için tekrarlanan 25×25 konum taraması kaldırıldı. Coğrafi ve projeksiyon çokgenleri, SVG sınır yolları ve aday etiket noktaları önbelleğe alınır; zoom sırasında yalnızca az sayıdaki adayın uygunluğu kontrol edilir. Tekerlek ve sürükleme güncellemeleri `requestAnimationFrame` ile bir karede birleştirilir; trackpad hareket miktarı da dikkate alınır.

Yerel Edge/mock ortamında aynı 18 adımlık yakınlaştırma/uzaklaştırma denemesinde toplam JavaScript süresi 3174 ms'den 75 ms'ye indi (yaklaşık %97 azalma). Ölçüm iki animasyon karesi beklediğinden adımın toplam bekleme süresi FPS ölçümü değildir. Başlangıçta görünen ilçe adları 21'den 35'e çıktı; dar alanlarda 9–11 px uyarlanan etiketler kendi çokgenlerinin içinde kalır. Çok küçük ilçelerde üzerine gelme bilgisi ve ilçe seçimi kullanılabilir. Son doğrulama: üretim derlemesi, 92 birim testi ve masaüstü/mobil harita etkileşim kontrolleri başarılı.

### İlk genel yenilemenin doğrulaması

Üretim derlemesi ve 7 dosyadaki 84 test başarılı. Grafik ölçeği ve eksik ölçüm davranışı ek testlerle doğrulandı. Yerel mock ortamında Edge tarayıcısıyla pano arama ve filtreler, alarm genişletme, grafik seri seçimi ve klavye etkileşimi, 2D nokta seçimi, 3D/WebGL çizimi ve haritanın düz turuncu sınırları kontrol edildi. Yedi ekran 390 px genişlikte sayfa taşması olmadan çalıştı; mobil menü ve Ctrl+K araması doğrulandı. Tarayıcıda çalışma zamanı istisnası görülmedi.

3D modülü ihtiyaç halinde yüklenir; üretim derlemesi bu modül için 500 kB paket boyutu uyarısı verir. Mock veri kümesindeki bazı olayların kara kutu kaydı yoktur; olay ayrıntısı mevcut kayıtlarla doğrulandı. Gerçek SCADA verisi ve saha ekipmanıyla kabul testi yapılmadı.
