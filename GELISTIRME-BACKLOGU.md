# Geliştirme Backlog'u — 15 Eylül 2026

Bu dosya, "Pano/Hücre İçi Anomali Erken Uyarı Sistemi" için üç aşamalı bir çalışmanın damıtılmış çıktısıdır: (1) sekiz ayrı açıdan sektör taraması — AG/OG pano izleme ürün ekosistemi, Türkiye dağıtım şirketi işletme gerçeği, standart ve birlikte çalışabilirlik, kestirimci bakım analitiği, kenar cihaz filo yönetimi, gerçek şebeke izleme projeleri, kontrol odası operasyonu, güvenlik ve satın alma güvencesi; (2) her adayın bu depoya karşı dosya ve satır düzeyinde doğrulanması ("bu gerçekten yok mu, kısmen var mı, kısıtları zorluyor mu"); (3) üç bağımsız lensle eleştiri — sektörel gerçeklik, mühendislik maliyeti ve jüri/ürün değeri. Üretim tarihi 15 Eylül 2026; kısıtlar [PLAN.md](PLAN.md) GK1–GK11 ve açık kalemler [KALAN-EKSIKLER.md](KALAN-EKSIKLER.md) esas alınmıştır. **Bu dosya [KALAN-EKSIKLER.md](KALAN-EKSIKLER.md)'nin yerine geçmez, onu tamamlar.** O dosya "söz verileni bitirme" listesidir (K1–K5 kritik, Y1–Y9 yüksek — birleştirme sonrası açık kalan işler); bu dosya "sektöre göre ne eklenebilir" listesidir. Çakışma olmaması için: oradaki bir kalem burada tekrar edilmedi, yalnızca bağımlılık olarak anıldı. İkisi aynı anda okunmalı, çünkü aşağıdaki A kovasının bütçesi oradaki kalemlerden **arta kalan** zamandır.

**Dürüstlük notu:** buradaki efor tahminleri tahmindir; depodaki mevcut desenlere bakılarak verilmiştir, ölçülmemiştir. Kaynak bağlantıları ve mevzuat atıfları taranırken doğrulanmıştır; doğrulanamayan her yer metinde "doğrulanmadı" diye işaretlidir. Madde ve tablo numarası düzeyindeki hiçbir standart atfı bu dosyada kesin olarak verilmemiştir.

---

## 1. Nerede duruyoruz

| Yetenek | Bizde | Sektörde tipik | Boşluk |
|---|---|---|---|
| Fizik tabanlı erken uyarı | dT = K·I² + unutma faktörlü RLS; S1'de 70 K sınırından 209 saat önce uyarı (ölçüldü) | eşik/termografi turu, bazılarında benzerlik tabanlı artık izleme | Yok — burası güçlü yanımız |
| Tespit doğrulaması | 10 etiketli senaryo, 8'inde recall 1,00; yanlış alarm 71,4/100 pano-gün (ölçüldü) | üretici iç testi, nadiren yayımlanır | Prognoz doğruluğu (yakınsama) hiç ölçülmedi |
| Alarm yaşam döngüsü | ISA-18.2: onay, raf, histerezis, olay gruplama, first-out, eskalasyon, bakım modu | aynı; üstüne periyodik başarım raporu ve "kötü aktör" listesi | Sel/bayat/chattering metrikleri ve kod bazında kötü aktör yok |
| SCADA entegrasyonu | Modbus TCP 502 + IEC 60870-5-104 2404, canlı ve eşdeğerliği ölçülmüş (0 fark) | aynı ikisi + DNP3/IEC 61850; ADMS tarafında CIM | Standart formda birlikte çalışabilirlik listesi yok |
| Ölçek | 1.000 sanal pano, görünme p95 657 ms, kayıp 0; 46-48x sıkıştırma | on binler (Iberdrola STAR ~90.000 merkez) | "Hangi 100 pano önce" sorusunun cevabı yok |
| Varlık kimliği | `panels` tablosunda 8 alan: pano_id, ad, tip, lat/lon, kurulum, taban günü, not | CBS tekil kodu, fider/TM, abone sayısı, kritiklik, bakım tarihi | Panonun NE olduğu ve KİMİ etkilediği sistemde yok |
| Risk gösterimi | Risk matrisi; y ekseni risk skorunun kendisi (kodda dürüstçe itiraf edilmiş) | sağlık × kritiklik (CBRM/CNAIM) | Matris fiilen tek boyutlu — etki ekseni yok |
| Güç kalitesi | u_ph, thd_i (akım THD'si), unbal_pct (akım dengesizliği) toplanıyor | EN 50160 değerlendirmesi ve raporu bir ana modül | Toplanan gerilim verisi hiçbir kuralda tüketilmiyor |
| Bakım çıktısı | Alarm + öneri metni | durum sınıfı, bir sonraki muayene tarihi, bakım kaydı | Bakım diline çeviren hiçbir çıktı yok |
| Bildirim | SMS (AT+PDU), sesli arama, WhatsApp, çift yönlü onay, maskeleme | aynı + günlük/aylık özet raporu | Sözleşmede söz verilen P3 günlük özeti kodda yok |
| Kimlik ve yetki | Yok; onaylayan adı istemciden geliyor (bilinçli, docs/15 §5'te açık) | rol tabanlı erişim, kurumsal SSO | Bilinçli boşluk; ürünleşmenin ön koşulu |
| Kenar güvenliği | Demo broker 1883 anonim; kenarda güvenli eleman kullanılmıyor | mTLS, cihaz başına topic yetkisi, IDevID/LDevID | Bilinçli boşluk; belgelenmiş |
| Kenar yaşam döngüsü | Firmware host'ta koşuyor, 1e-6 eşitlik doğrulanmış | imzalı OTA, A/B geçiş, kanarya, reset nedeni telemetrisi | MoSCoW Won't; tasarım düzeyinde bile yazılı değil |
| Maliyet/fayda | Parametrik ROI formülü + varsayımsal örnek tablo (dosya bunu kendisi yazıyor) | mevzuat tazminatı ve termografi turu tasarrufu üzerinden hesap | Teslimin en zayıf parçası; tek varsayımsal dokümanımız |
| Dürüstlük kaydı | Bilinçli sapmalar 4 ayrı dosyaya dağılmış, hepsi yazılı | "kapsanmayan" bölümü tek sayfa olur | Dağınık olduğu için jüri tek tek bulmak zorunda |

---

## 2. Sektörel bulgular

**Türkiye mevzuatı ve dağıtım şirketi gerçeği**

1. EPDK Kalite Yönetmeliği (RG 29/12/2020, 31349 mük.) Madde 8/2, her kesinti kaydında şu alanları zorunlu kılıyor: numara, kademe, yer (il/ilçe ve **tekil şebeke unsuru kodu**), neden, sınıf, başlama/sona erme, süre, etkilenen kullanıcı sayısı, toplam etkilenme süresi, dağıtılmayan enerji. — lexpera.com.tr, konsolide metin (alan listesi birebir doğrulandı).
2. 21/12/2012 tarihli "Hizmet Kalitesi Yönetmeliği" **yürürlükten kaldırılmıştır** (2020 Kalite Yönetmeliği m.48). Sektör taramasından gelen üç aday bu ölü metinden madde numarası alıntılıyordu; bu dosyada o atıflar kullanılmamıştır.
3. Kesinti tazminatı başvurusuz ve formülü yayımlanmış: ÖTMSÜRE = SBSÜRE + (TKSÜRE − ESÜRE) × K × DB × OT; ayrıca kesinti sayısı için ayrı bir ÖTMSAYI formülü var. SBSÜRE bir literal tutar değil, parametredir. — 23/10/2025 değişikliği, alomaliye.com özeti.
4. ADM Elektrik ve GDZ Elektrik (aynı grup) 20 Mayıs 2026'da Schneider Electric + Inavitas ile EcoStruxure ADMS anlaşması imzaladı: SCADA ve Kesinti Yönetim Sistemi yenileniyor, DMS/DERMS ve CBS entegrasyonu kapsamda, 5 ilde 6M+ abone. — enerjibulteni.com, aa.com.tr.
5. EPDK CBS usul ve esasları dağıtım panosunu da tekil kodla, kullanıcı tesisleriyle eşleştirilmiş olarak CBS'de tutmayı zorunlu kılıyor. Yani panonun kimliği müşteride zaten var; biz kaynak değil tüketiciyiz. — aa.com.tr, epdk.gov.tr.
6. Enerji Sektöründe Siber Güvenlik Yetkinlik Modeli Yönetmeliği (RG 6/6/2023, 32213) elektrik dağıtım lisansı sahiplerini yükümlü kılıyor ve sektör için asgari Seviye 2 öngörüyor; ekteki teknik kontrol maddeleri kamuya açık değil. — epdk.gov.tr (yönetmelik adı ve yükümlü kapsamı doğrulandı).
7. GDZ sahada 55 ayrı bakım-onarım ekip merkezi işletiyor; SCADA 170 TM ve 1.970 fideri kapsıyor. Tek düz bildirim alıcı listesi bu ölçekte işlemez. — gdzelektrik.com.tr.

**Ürün ve standart ekosistemi**

8. IEC 62974-1:2017 tam olarak bizim cihaz sınıfımızı tanımlıyor: ≤1 kV AC, pano içine veya DIN raya sabitlenen "energy server / data logger / data gateway / I/O konsantratör". Depoda "62974" kelimesi hiç geçmiyor. — webstore.iec.ch/28169 (kapsam doğrulandı).
9. NFPA 70B 2023 baskısı tavsiyeden zorunluluk diline geçti; tüm ekipmana en az 12 ayda bir muayene, en kötü durum sınıfında termografi en az 6 ayda bir. Madde/tablo numaraları ikincil kaynaklardan; doğrulanmadı ve bu dosyada kullanılmıyor. ABD standardıdır, Türkiye'de bağlayıcı değildir. — FLIR, TÜV SÜD, Eaton özetleri.
10. Türkiye'de bağlayıcı olan, İş Ekipmanlarının Kullanımında Sağlık ve Güvenlik Şartları Yönetmeliği EK-III'ün elektrik tesisatı için yıllık kontrol zorunluluğudur. NFPA ile asla birbirinin yerine sunulmamalı. — emo.org.tr.
11. Schneider Easergy TH110 bağlantı noktası termal sensörü, CL110 ise **ortam** sensörüdür (sıcaklık/nem); ikisi aynı kategori değildir. HeatTag gaz/mikro-partikül ile 170-200 °C yalıtım bozunumunu duman çıkmadan yakalar ve alarmı doğrudan bakım eylemine bağlar (planlı / hızlı kontrol / acil). — se.com, DOCA0171EN.
12. Siemens SENTRON powermanager ve Schneider PME'de EN 50160 raporlaması bir eklenti değil ana modüldür; ABB Ability EDCS çok-tesisli karşılaştırma sunar. Bizde rapor kavramı sıfır: tek bir yazdırma veya dışa aktarma yolu yok. — siemens.com, product-help.schneider-electric.com, abb.com.
13. IEC 60870-5-104 uygulayan her ürün standardın kendi formunda bir birlikte çalışabilirlik listesi yayımlıyor ve bölüm başlıkları sabit (istasyon parametreleri, ASDU seçimi, tip↔COT, temel uygulama fonksiyonları, zaman aşımları, k/w, port 2404). — Beckhoff TF6500, Bachmann, Phoenix Contact 104RTU belgeleri.

**Analitik, ölçüm ve saha**

14. ISO 17359 baz çizgisinin makine kararlıyken alınmasını ve alarm kriterinin **zaman içinde yinelemeli** optimize edilmesini ister; bizde K₀ 7 günlük medyanla bir kez donuyor ve bir daha güncellenmiyor. — iso.org/standard/33011 (madde numarası verilmedi).
15. Prognoz doğruluğunun yerleşik metrikleri var: Prognostic Horizon, alfa-lambda, Relative Accuracy, Convergence (Saxena ve ark.; NASA açık kaynak kütüphanesi). — github.com/nasa/PrognosticsMetricsLibrary.
16. EEMUA 191 sayısal: alarm seli = 10 dakikada >10 yeni alarm, bayat alarm = 24 saatten uzun duran, kabul edilebilir yük ~150 alarm/operatör/gün, rasyonalize edilmemiş sistemlerde ilk 10 alarm oluşumların %60-80'ini üretir. — processvue.com, eemua.org.
17. Electricity North West'in AG izleme programı iki sonuç bıraktı: AG şebekesinin tamamını izlemek gereksiz, hedefli izleme yeterli; ve 1 dakikalık örnekleme sürdürülemeyip 10 dakikaya düşürüldü (EN 50160 zaten 10 dakikalık pencere ister). Ayrıca devreye almada varlık numarasının yanlış kaydedilmesi başlı başına bir arıza modu olarak raporlanmış. — ofgem.gov.uk, LVNS kapanış raporu.
18. Sahada en çok yangın/ateşleme önleyen yaklaşım (Texas A&M DFA, Gridware) yarım periyot altı dalga biçimi imzasına dayanıyor; 10 saniyelik RMS mimarisi bu sınıfı fiziksel olarak göremez. — distribution.epri.com, latitudemedia.com.

---

## 3. A — Özellik dondurmaya kadar (15-17 Eylül)

Sıra **etki sırasıdır**, bütçe sırası değil. Bu on maddenin toplamı ~27-33 saat; [KALAN-EKSIKLER.md](KALAN-EKSIKLER.md)'deki K/Y kalemleri üç kişide zaten bağlı olduğu için serbest bütçe gerçekçi olarak 12-15 saat. Yukarıdan aşağı alın, çizginin altı kalsın. **Kabul kapısı:** 15-17 Eylül'de yeni işe ancak dört koşul birden sağlanıyorsa başlanır — tek kulvar, [contracts/](contracts/) dokunmuyor, ≤3-4 saat, mevcut 987 testi kırmıyor.

### F-01 · Altın demo veritabanı ve tek seferlik göç penceresi — ✅ tamamlandı
Bekleyen tüm şema göçlerini tek `down -v` anında uygular ve ≥7 günlük temiz veriyle ısıtılmış bir veritabanı üretir · **Etki:** çok yüksek · **Efor:** 2-3 saat · **Nerede yaşar:** [deploy/initdb/](deploy/initdb/), [deploy/compose.yaml](deploy/compose.yaml), yeni bir `scripts/seed_demo.py`
**Sektörel dayanak:** Her ölçüm iddiasının tekrar üretilebilir bir zeminden çıkması gereği (ENWL kapanış raporu, devreye alma kayıt kalitesi bulgusu).
**Bizdeki boşluk:** [deploy/initdb/](deploy/initdb/) yalnızca boş volume'de koşuyor; yerel veritabanlarında Faz 0 artıkları ve geçmiş zaman damgası bozukluğundan kalan satırlar var. Taban öğrenme canlı yığında gerçek saatler sürüyor.
**Ne üretir:** Demo, ekran görüntüsü, video ve F-03/F-05/F-06'nın tamamının üzerinde koşacağı tek ortak veri zemini; üç geliştiricinin `down -v` maliyeti bir kez ödenir.
**Dikkat:** Bu iş yapılmazsa aşağıdaki rapor üreten dört madde de gerçek sayı üretemez ve GK10'a takılır. Y4 (temiz makine testi) ile aynı pencerede yapılmalı.

### F-02 · GK10 bütünlük geçişi: üç sayı ve metin düzeltmesi — ✅ tamamlandı
Jüriye giden metinlerde kendi ölçümümüzle çelişen üç yeri kapatır · **Etki:** çok yüksek · **Efor:** 1-1,5 saat · **Nerede yaşar:** [docs/10-bom-maliyet-roi.md](docs/10-bom-maliyet-roi.md), [backend/app/api/insights.py](backend/app/api/insights.py), [deploy/compose.yaml](deploy/compose.yaml)
**Sektörel dayanak:** GK10'un kendisi; ayrıca ölçümlerin tekrar üretilebilirliği için imaj sabitleme yerleşik pratik (CISA SBOM asgari unsurları, bileşen hash'i).
**Bizdeki boşluk:** (a) [docs/10-bom-maliyet-roi.md](docs/10-bom-maliyet-roi.md) "tespit oranı %70 (etiketli senaryo setinde ölçülecek)" diyor — oysa [docs/12-dogrulama-sonuclari.md](docs/12-dogrulama-sonuclari.md) bunu ölçmüş ve 10 senaryonun 8'inde recall 1,00 çıkmış; kendi performansımızı düşük gösteriyoruz. (b) Kara kutu penceresinin üst sınırı 168 saat, oysa manşet sayımız 209 saatlik öne alma — kendi en iyi sonucumuzu kendi ekranımızda gösteremiyoruz. (c) [deploy/compose.yaml](deploy/compose.yaml)'da bir imaj etiketi sabit değil; iki kişi farklı imaj çalıştırabilir.
**Ne üretir:** Düzeltilmiş ROI örneği, 336 saate çıkarılmış kara kutu penceresi, digest ile sabitlenmiş imaj.
**Dikkat:** Saat başına getirisi listedeki her şeyden yüksek. Pencere üst sınırı değişirken varsayılan (72 saat) korunmalı, yoksa ekran ağırlaşır.

### F-03 · P3 günlük özeti ve SYS toplu özeti — ✅ tamamlandı
Sözleşmede tanımlı ama kodda hiç uygulanmamış özet bildirimini gerçekten gönderir · **Etki:** çok yüksek · **Efor:** 3-4 saat · **Nerede yaşar:** [backend/app/notify/dispatcher.py](backend/app/notify/dispatcher.py), [backend/app/alarm_service.py](backend/app/alarm_service.py), [backend/app/notify/templates.py](backend/app/notify/templates.py), [backend/app/config.py](backend/app/config.py)
**Sektörel dayanak:** EcoStruxure Asset Advisor her alarmda bildirim + periyodik rapor zincirini ürünleştirmiş; ISA-18.2 izleme-değerlendirme aşaması periyodik raporlamayı öngörür.
**Bizdeki boşluk:** [contracts/alarm-codes.yaml](contracts/alarm-codes.yaml) P3 için `daily_digest: true`, SYS için `sms: digest_only` diyor ve **jüriye giden** [docs/06-alarm-matrisi.md](docs/06-alarm-matrisi.md) §4 "P3 günlük özete, SYS toplu özete gider" yazıyor — kodda "digest" kelimesi yalnızca bir docstring'de geçiyor. K/K₀ erken uyarısının tamamı P3, yani 209 saatlik başlığımız bugün bir veritabanı satırında bitiyor.
**Ne üretir:** Günde bir kez gönderilen tek parça özet mesajı + testi; jüri dokümanındaki bir vaadin kapanması.
**Dikkat:** Sözleşme değişikliği **gerekmiyor**, alanlar zaten tanımlı. Metin tek parça GSM-7 sınırına uymalı; maskeleme kurallarına dokunulmamalı (GK9). Haftalık yönetim raporu ve mevzuat eşlemesi bu kapsamın dışında bırakıldı.

### F-04 · Prognoz geri testi: alfa-lambda, prognostic horizon, relative accuracy — ✅ tamamlandı
"209 saat önce uyardı" tek noktasını, tahminin zamanla yakınsayıp yakınsamadığını gösteren bir eğriye çevirir · **Etki:** çok yüksek · **Efor:** 3-5 saat · **Nerede yaşar:** yeni `libs/panoalgo/panoalgo/prognostics.py`, [libs/panoalgo/panoalgo/validate.py](libs/panoalgo/panoalgo/validate.py), yeni `libs/panoalgo/tests/test_prognostics.py`
**Sektörel dayanak:** Saxena ve ark. prognostik performans metrikleri ve NASA Prognostics Metrics Library; ISO 13381-1 prognozun doğrulanmasını ve güven ifadesini ister.
**Bizdeki boşluk:** [docs/12-dogrulama-sonuclari.md](docs/12-dogrulama-sonuclari.md) §2 prognoz hakkında tek bir sayı veriyor. Fixture'larda sınır ihlali anı zaten etiketli olduğu için gerçek kalan ömür her örnek için hesaplanabilir — yeni veri gerekmiyor, sadece kod gerekiyor.
**Ne üretir:** docs/12'ye yeni bir bölüm: tahminin ne zaman güvenilir hale geldiği, bandın içinde kalma oranı, yakınsama.
**Dikkat:** Çıktı docs/12'ye **elle yazılamaz** — dosya betikle üretiliyor ve yeniden üretim testiyle korunuyor; metrikler `render_markdown()` içine girmeli. İki dürüstlük kaydı zorunlu: sonuç tek yörüngeden geliyor (n=1) ve sensör arızası senaryosunda sınır ihlali olmadığı halde 99 kez tahmin üretiliyor — bu bir prognoz yanlış-alarmıdır, saklanmaz, [docs/05-anomali-tespiti.md](docs/05-anomali-tespiti.md) "bilinen sınırlar" bölümüne yazılır.

### F-05 · Tazminat maruziyeti hesaplayıcısı
docs/10'un varsayımsal ROI tablosunu, formülü mevzuatta yayımlanmış bir maruziyet hesabıyla değiştirir · **Etki:** yüksek · **Efor:** 2-3 saat · **Nerede yaşar:** yeni `scripts/tazminat_maruziyeti.py`, [docs/10-bom-maliyet-roi.md](docs/10-bom-maliyet-roi.md)
**Sektörel dayanak:** EPDK Kalite Yönetmeliği'nin tazminat formülü (ÖTMSÜRE ve ÖTMSAYI); Whisker Labs/sigorta modelinde olduğu gibi fayda kaleminin dış bir kurala bağlanması.
**Bizdeki boşluk:** [docs/10-bom-maliyet-roi.md](docs/10-bom-maliyet-roi.md) baştan sona varsayım üzerine kurulu ve bunu kendisi yazıyor ("Sayılar iddia değil, örnektir") — teslimin GK10 açısından en zayıf parçası. Aynı geçişte ikinci bir bedava sayı da eklenmeli: mevcut enerji analizörü ve ark koruma cihazını sensör olarak kullandığımız için **eklemediğimiz** kalemlerin (akım trafoları, ayrı ark dedektörü, ek kablaj) BOM farkı.
**Ne üretir:** Parametreli bir hesaplayıcı betiği + docs/10 §3'ün yeniden yazımı; jüri kendi tarife değerini girer.
**Dikkat:** API ucu ve arayüz kartı **eklenmeyecek** (donmuş openapi, onay kuyruğu tıkalı). Çıktı kesinlikle MARUZİYET dilinde olmalı: "bu pano kesilirse yönetmeliğe göre şu kadar tazminat doğar". "Şu kadar arıza önledik" ölçülemez, GK10 ihlalidir. Dağıtım bedeli ve ortalama talep girilmediyse hesap "veri yok" demeli.

### F-06 · Çiy noktası eşik taraması — ✅ tamamlandı
Ölçülmüş tek gerçek zayıflığı (sağlıklı panoda 71,4 yanlış alarm/100 pano-gün, tamamı çiy kaynaklı) veriyle savunur veya öneri açar · **Etki:** yüksek · **Efor:** 3-4 saat · **Nerede yaşar:** yeni `scripts/threshold_sweep.py`, [docs/05-anomali-tespiti.md](docs/05-anomali-tespiti.md)'ye yeni bölüm, gerekirse `contracts/changes/` altında öneri
**Sektörel dayanak:** IEEE C57.104-2019 eşikleri popülasyon yüzdeliğinden türetiyor; ISO 17359 alarm kriterinin yinelemeli optimize edilmesini ister.
**Bizdeki boşluk:** [contracts/alarm-codes.yaml](contracts/alarm-codes.yaml)'daki hiçbir eşiğin "neden bu sayı" sorusuna ölçülmüş cevabı yok. Sorun zaten kayıtlı ve sahiplenilmiş ([KALAN-EKSIKLER.md](KALAN-EKSIKLER.md) D7).
**Ne üretir:** Çiy marjı eşikleri için ROC benzeri bir tablo; ya mevcut sayının savunması ya da `contracts/changes/` altında gerekçeli bir öneri. Yan kazanç: canlı demoda sağlıklı panodan çiy alarmı çıkma riski kapanır.
**Dikkat:** Tam ızgara yapılmamalı — yalnızca çiy eşikleri, yalnızca sağlıklı senaryo üzerinde. [libs/panoalgo/panoalgo/validate.py](libs/panoalgo/panoalgo/validate.py) tespiti yeniden koşturmuyor, fixture'ın hazır alarm sütununu okuyor; her ızgara noktasında fixture yeniden üretilmeli. Eşiği **değiştirmek** 17 Eylül'den sonra imkânsız; bu iş eşiği yalnızca savunur.

### F-07 · EEMUA 191 alarm başarım panelleri
Sel, bayat, chattering ve kod bazında "kötü aktör" metriklerini Grafana'da ham SQL ile üretir · **Etki:** yüksek · **Efor:** 3-4 saat · **Nerede yaşar:** [scripts/gen_grafana_dashboards.py](scripts/gen_grafana_dashboards.py) → [deploy/grafana/dashboards/alarm-kpi.json](deploy/grafana/dashboards/alarm-kpi.json), [backend/tests/](backend/tests/) yeniden üretim testi
**Sektörel dayanak:** EEMUA 191 sayısal tanımları (10 dakikada >10 alarm = sel; 24 saatten uzun = bayat) ve ISA-18.2 izleme-değerlendirme aşaması; chatter index için run-length dağılımı (Kondaveeti ve ark., 2013).
**Bizdeki boşluk:** Panonun kendisi zaten yayında ve EEMUA hedef karşılaştırması, raf sayacı ve **pano** bazında ilk-on içinde var. Gerçekten eksik olan üç şey: kod bazında kötü aktör, chattering ve bayat alarm. **Ve bir GK10 hatası:** mevcut panellerden birinin açıklaması "10 dakikada 10'dan fazla alarm sel sayılır" diyor ama sorgusu saatlik kova kullanıyor — panel, hesaplamadığı bir tanımı iddia ediyor.
**Ne üretir:** Dört yeni panel + düzeltilmiş açıklama; ISA-18.2 iddiasının "uyguladık"tan "ölçüyoruz"a geçmesi.
**Dikkat:** **İlk iş** yanlış panel açıklamasını kapatmak. Grafana JSON elle düzenlenmez, [scripts/gen_grafana_dashboards.py](scripts/gen_grafana_dashboards.py) üzerinden geçer; pano dosyaları [PLAN.md](PLAN.md) Bölüm B kural 7 gereği tek sahiplidir (B). Filo KPI şemasına alan eklenmeyecek — üç ayrı yerde depo uygulaması demek. Ölçüm yük testi verisiyle yapılamaz (tek kod üretiyor); senaryo oynatmalarıyla yapılmalı.

### F-08 · IEC 104 birlikte çalışabilirlik bloğu (koddan üretilmiş)
Çalışan IEC 104 istasyonumuzu standardın kendi form başlıklarıyla belgeler · **Etki:** yüksek · **Efor:** 1-1,5 saat · **Nerede yaşar:** [scripts/gen_iec104_doc.py](scripts/gen_iec104_doc.py) → [docs/04-iec104-haritasi.md](docs/04-iec104-haritasi.md) yeni §7 bloğu, mevcut test dosyasına iki doğrulama
**Sektörel dayanak:** IEC 60870-5-104 uygulayan her ürün bu listeyi yayımlıyor; bölüm başlıkları ve işaretleme kuralı standarttır (Beckhoff, Bachmann, Phoenix Contact örnekleri).
**Bizdeki boşluk:** İçeriğin çoğu zaten üretiliyor (k/w, t1/t2/t3, IOA, tip↔COT matrisi) ama bizim anlattığımız biçimde. Eksik delta: COT ve ortak adres alan uzunlukları, azami APDU, t0'ın yokluğu ve desteklenmeyen uygulama fonksiyonlarının açıkça işaretlenmesi.
**Ne üretir:** SCADA entegrasyon mühendisinin okuduğu formda, koddan üretilen ve yeniden üretim testiyle korunan bir bölüm.
**Dikkat:** Ayrı dosya, ayrı betik, ayrı test modülü açılmamalı. Standardın ek formundaki satırlar birebir kopyalanmamalı, yalnızca bölüm başlıkları kullanılmalı. Desteklenmeyen her şey (tüm kontrol ASDU'ları, sayaç sorgulaması, dosya transferi) açıkça "desteklenmiyor" işaretlenmeli — bu GK6 hikâyesini standart formda güçlendirir.

### F-09 · Yazdırılabilir olay dosyası
Operatörün kara kutu ekranında gördüğünü tek sayfalık, imzalanabilir bir olay raporuna çevirir · **Etki:** yüksek · **Efor:** 2-3 saat · **Nerede yaşar:** yeni `frontend/src/print.css`, [frontend/src/pages/OlayAnalizi.tsx](frontend/src/pages/OlayAnalizi.tsx), [frontend/src/app.css](frontend/src/app.css)
**Sektörel dayanak:** EcoStruxure Power Commission kabul raporlarını, Asset Advisor aylık raporları otomatik üretiyor; NFPA 70B 2023 bakım ve olay kayıtlarının belgelenmesini istiyor (ABD standardı, Türkiye'de bağlayıcı değil).
**Bizdeki boşluk:** Depoda tek bir `@media print` kuralı, tek bir yazdırma çağrısı ve tek bir dışa aktarma yolu yok. Kara kutu ucu, olay zaman çizelgesi ve "neden/ne yapmalı/ne kadar acil" üçlüsü zaten hazır; iş tek bir CSS dosyasına iniyor.
**Ne üretir:** A4'e sığan, gezinme ve etkileşim gizlenmiş, altında imza satırları olan yazdırılabilir olay raporu; örnek çıktı demo paketine konur.
**Dikkat:** Yeni npm bağımlılığı eklenmeyecek (derleme ve GK4 tartışması açar) — tarayıcı yazdırma yeterli. 3B ikiz tuvali yazdırmada boş çıkar; rapora 2D görünüş ve çizgi grafikler konmalı. "Örnek/sentetik veriden üretilmiştir" ibaresi ve hem olay hem alındı zaman damgası basılmalı.

### F-10 · Karşı-olgusal açıklama: "Ne doğrulanmalı" satırı
Alarm kartına, teşhisi kesinleştirmek için eksik olan kanıtı yazar · **Etki:** orta · **Efor:** 2-4 saat · **Nerede yaşar:** [backend/app/risk.py](backend/app/risk.py), [frontend/src/components/AlarmNedeni.tsx](frontend/src/components/AlarmNedeni.tsx), [libs/panoalgo/tests/](libs/panoalgo/tests/)
**Sektörel dayanak:** Açıklanabilirlikte karşı-olgusal açıklama yerleşik ikinci aile; ISO 13379-1 semptom-arıza ilişkisinin izlenebilir kurulmasını ister; CIGRE TB 858 sağlık indeksinde monotonluk ilkesini koyar.
**Bizdeki boşluk:** Füzyon yalnızca **eşleşen** kanıtları döndürüyor; hipotezin eksik kanıtı hiçbir yere yazılmıyor. Operatöre "neyi doğrularsam teşhis kesinleşir" diyemiyoruz. Ayrıca skorun monotonluğu genel olarak test edilmemiş.
**Ne üretir:** Alarm kartında üçüncü blok ("Ne doğrulanmalı") — tek paylaşılan bileşen olduğu için iki ekranda birden görünür; artı bir monotonluk özellik testi.
**Dikkat:** Eksik kanıt MQTT yüküne **konulmayacak** — telemetri şeması ek alana kapalı, yeni alan mesajı reddettirir. Merkezde, hipotez tanımından yeniden türetilmeli; gerekli sözlükler zaten kurulu, kenar hiç değişmez.

**Çizginin hemen altındakiler** (bütçe açılırsa sırayla): kalan ısıl pay / "bu pano ne kadar daha yük kaldırır" (3-4 sa, uçsuz, frontend'de hesaplanabilir); saat sapması kapısı (2-3 sa, ikinci savunma katmanı — kökü zaten kapandı); varlık kimliği ve etki ekseni (3-4 sa, göç vergisi + onay bağımlılığı); EN 50160 gerilim bandı ön taraması (2-3 sa, mevcut seri ucuyla, "yöntem gösterimi" etiketiyle); durum sınıfı ve sonraki muayene tarihi (3-4 sa, uçsuz); vardiya devir betiği (3-4 sa, betik sürümü); kurulum tutarlılık raporu — nokta↔faz ve akım trafosu oranı denetimi (3 sa); eşzamanlı sessizlik paneli (1-1,5 sa); frontend duman testi, yedi ekranın mock veriyle render edilmesi (2 sa); sözleşmedeki davranış vaatlerinin kodda tüketicisi var mı denetimi (1-1,5 sa).

---

## 4. B — Teslim penceresi (18-20 Eylül, yalnızca doküman/sunum/video)

GK2 gereği bu pencerede kod yazılmaz. **Doküman bütçesi kararı:** en çok **iki** yeni dosya açılır (`docs/18` ve `docs/19`); sektör taramasından gelen sekiz ayrı yeni doküman önerisi bu ikisinde birleştirilmiştir. Depoda zaten 18 doküman var ve M4'te hepsi çapraz okunacak; yirminci dosya jüriye değer değil, okuma yükü ve çelişki riski ekler.

### F-11 · Jüri kanıt haritası: dokuz kriter → dosya → ölçülmüş sayı
Değerlendirme kriterlerinin her biri için tek satırlık kanıt eşlemesi · **Etki:** çok yüksek · **Efor:** 1-1,5 saat · **Nerede yaşar:** [README.md](README.md) başı veya yeni `docs/00-juri-kanit-haritasi.md`
**Sektörel dayanak:** Yok — bu bir teslim disiplini maddesi; jürinin kendi değerlendirme cetveline hizalanma.
**Bizdeki boşluk:** 18 doküman teslim ediyoruz, jüri dokuz kriterden puan veriyor ve aradaki eşlemeyi kurma işini jüriye bırakıyoruz.
**Ne üretir:** Tek sayfa: kriter | kanıt dosyası | ölçülmüş sayı (recall 1,00 · 209 saat · 71,4 yanlış alarm/100 pano-gün · p95 657 ms · 1.000 pano · 46-48x sıkıştırma · mutasyon sayıları · 987 test · üç protokolde 0 fark).
**Dikkat:** Yeni hiçbir iş üretmiyor, yalnızca ölçülmüş olanı hizalıyor. Provada herkesin ezberleyeceği tek sayfa da bu olmalı.

### F-12 · 17 soruluk jüri cevap kartı
Muhtemel jüri sorularının cevaplarını ölçülmüş sayılarla doldurur · **Etki:** çok yüksek · **Efor:** 1-1,5 saat · **Nerede yaşar:** [docs/17-donanimsiz-dogrulama.md](docs/17-donanimsiz-dogrulama.md) §5 genişletmesi veya demo paketinde tek kart
**Sektörel dayanak:** Yok — sunum hazırlığı.
**Bizdeki boşluk:** Mevcut cevap seti yalnızca entegrasyon/ölçek/güvenlik tarafını ölçümle güncellemiş; fizik ve saha/maliyet/UX soruları için hazır kart yok. Üstelik en sık sorulacak sorulardan birinin ("yanlış alarm oranınız ne?") cevabında hâlâ bir yer tutucu duruyor — oysa sayı [docs/12-dogrulama-sonuclari.md](docs/12-dogrulama-sonuclari.md) §3'te var.
**Ne üretir:** Provaya hazır tek kart; en çok puanlanan anın (soru-cevap) tek hazırlık artefaktı.
**Dikkat:** Her cevabın yanında kanıt dosyası adı olmalı; sayısı olmayan soruya "ölçmedik" yazılmalı.

### F-13 · "Kendiniz okuyun" kartı: üç komutla canlı doğrulama
Jürinin kendi istemcisiyle üç protokolden aynı değeri okuyup eşitliği doğrulaması için komut kartı · **Etki:** yüksek · **Efor:** ~1 saat · **Nerede yaşar:** [docs/03-modbus-haritasi.md](docs/03-modbus-haritasi.md) ve [README.md](README.md)
**Sektörel dayanak:** Moxa, Beckhoff gibi ürünlerde birlikte çalışabilirlik belgesinin yanında "kendi istemcinizle doğrulayın" akışı standart.
**Bizdeki boşluk:** [docs/01-problem-analizi.md](docs/01-problem-analizi.md)'deki ayırt edici özellikler listesinde "jüri kendi Modbus istemcisiyle okuyabilir" yazıyor ama bunu nasıl yapacağını söyleyen tek satır yok.
**Ne üretir:** Üç komut (Modbus 502, IEC 104 2404, REST) ve beklenen eşit çıktı; iddiayı cümleden canlı kanıta çeviren en ucuz hamle.
**Dikkat:** Komutlar demo makinesinde bir kez koşturulup çıktı kaydedilmeli; koşmayan bir komut kartı ters teper.

### F-14 · Bilinçli kapsam sınırları — tek sayfa
Dört ayrı dosyaya dağılmış itirafları tek yerde toplar · **Etki:** yüksek · **Efor:** ~1 saat · **Nerede yaşar:** yeni `docs/00-bilincli-sinirlar.md` veya F-11 ile aynı sayfanın ikinci yarısı
**Sektörel dayanak:** SSEN'in AG fider arıza tespiti projesi kapanış raporunda saha denemelerinin "sınırlı başarı" olarak yazılması gibi; olgun programlar sınırlarını kendileri yazar.
**Bizdeki boşluk:** Altı bilinçli sapma (ekran sayısı, harita kırılımı, kendi Modbus sunucumuz, firmware bellek sınırı, atlanan emülatörler, cihaz sağlığı istek deseni) artı "kapsanmayan standartlar" artı UX ve donanımsız doğrulama sapmaları dört ayrı dosyada duruyor; jüri hepsini bulamaz.
**Ne üretir:** "Neyi yapmadınız?" sorusunun tek kaynağı; dürüstlüğün dağınık değil toplu okunması.
**Dikkat:** Her satır gerekçeli olmalı; gerekçesiz "yapmadık" listesi eksik listesi gibi okunur.

### F-15 · docs/18 — Ticari ürün karşılaştırması ve analitik standart izi
Cihaz düzeyindeki mevcut karşılaştırmayı platform düzeyine taşır ve durum izleme standart ailesini kod dosyalarına bağlar · **Etki:** yüksek · **Efor:** 3-4 saat · **Nerede yaşar:** yeni `docs/18-konumlandirma-ve-standart-izi.md`
**Sektörel dayanak:** Karşılaştırılacak platformlar: ABB Ability EDCS çok-tesisli karşılaştırma, Siemens SENTRON powermanager (EN 50160 raporu, kesici kalan ömür), Eaton Foreseer, Hitachi TXpert, Schneider PME. Standart izi: ISO 17359 (durum izleme programı ve alarm kriteri), ISO 13379-1 (veri yorumlama ve tanı), ISO 13381-1 (prognoz, kalan ömür), CIGRE TB 858 (varlık sağlık indeksleri).
**Bizdeki boşluk:** Cihaz düzeyinde sekiz satırlık bir karşılaştırma tablosu iç çalışma dosyasında zaten var ama jüriye gitmiyor; platform düzeyi hiç yok. Ayrıca ürünün ANA İŞİ için (durum izleme + prognoz) depoda sıfır standart izi var: K₀ = baz çizgisi, ttl = kalan ömür, risk skoru = sağlık indeksi eşlemesi hiçbir yerde yazılı değil.
**Ne üretir:** İki bölümlü tek doküman: (a) özellik matrisi + "bizde yok, çünkü GK3/GK4/GK6" sütunu + ADM/GDZ'nin ADMS alımına konumlanma satırı; (b) standart → kod dosyası → ölçülen sonuç → dürüst boşluk tablosu.
**Dikkat:** Rakip fiyatı ve "onlarınki kötü" iddiası yasak; doğrulanamayan hücre boş bırakılır. Termal bağlantı sensörü ile ortam sensörü aynı satıra konmamalı. ISO madde numarası ve birebir alıntı yazılmayacak (metinlere erişim yok). Sunuma tek cümle çıkar: "onların platformu geliyor, biz onun altındaki ölçüm katmanıyız; bugün IEC 104 ile bağlanırız, koruma devresine asla yazmayız."

### F-16 · docs/19 — TEDAŞ şartname uyum haritası
Türkiye'de bir dağıtım panosuna takılan haberleşme ünitesinin tabi olduğu şartnameyle madde madde karşılaştırma · **Etki:** yüksek · **Efor:** 2-3 saat · **Nerede yaşar:** yeni `docs/19-tedas-sartname-uyumu.md`, [docs/11-standartlar-uyum.md](docs/11-standartlar-uyum.md)'den atıf
**Sektörel dayanak:** TEDAŞ-MLZ/2019-064.B haberleşme ünitesi teknik şartnamesi (deponun kendi analiz raporunda "1 Ocak 2025'ten itibaren zorunlu" olarak kaydedilmiş); ayrıca komitenin verdiği AG pano şartnamesinin çalışma koşulları maddesi (dahili/harici sıcaklık aralıkları, 24 saat ortalama, rakım).
**Bizdeki boşluk:** [docs/11-standartlar-uyum.md](docs/11-standartlar-uyum.md)'de şartnamenin adı geçiyor ama arkasında hiçbir içerik yok. Ayrıca [hardware/](hardware/) BOM'undaki parçaların şartnamedeki ortam sınırlarına karşı satır satır karşılaştırması hiçbir yerde yok — "saha koşullarında uygulanabilirlik" jüri kriterinin doğrudan konusu.
**Ne üretir:** İki tablo: (a) şartname başlığı | karşıladığımızı iddia edebileceklerimiz | fiziksel doğrulama gerektirenler; (b) BOM parçası | çalışma aralığı | şartname sınırı | uygun/uygun değil/doğrulanmadı.
**Dikkat:** Tam metne erişim yoksa başlık düzeyinde kalınmalı, madde numarası uydurulmamalı. "Karşılıyoruz" yerine "tasarım hedefi, tip testi yapılmadı" dili kullanılmalı (GK3).

### F-17 · Kısmi deşarj ve dalga biçimi: verilen veri sayfalarına dürüst cevap
Komitenin paylaştığı HFCT veri sayfalarının neden kullanılmadığını ve 10 saniyelik mimarinin neyi göremediğini tek yerde kapatır · **Etki:** yüksek · **Efor:** 1-1,5 saat · **Nerede yaşar:** [docs/13-donanim-tasarimi.md](docs/13-donanim-tasarimi.md) yeni bölüm, [docs/11-standartlar-uyum.md](docs/11-standartlar-uyum.md)'deki mevcut PD sapma notunun hemen yanı
**Sektörel dayanak:** Texas A&M Distribution Fault Anticipation ve Gridware, arıza öncesi imzayı yarım periyot altı dalga biçiminden çıkarıyor; EA Technology UltraTEV yönetilen PD anketleri sahada yerleşik.
**Bizdeki boşluk:** Komite dosya paketine iki HFCT veri sayfası koydu, biz PD'yi bilinçli olarak kapsam dışı bıraktık ve bunun gerekçesi tek bir dokümanda toplanmış değil. Ayrıca tüm tespit zincirimiz 10 saniyelik skaler değerler üzerine kurulu ve bu, seri ark ile kontak kıvılcımlanmasını **fiziksel olarak** göremez — bunu jüri bulmadan bizim söylememiz gerekir.
**Ne üretir:** Bir sayfa: PD neden kapsam dışı (verilen veri sayfalarının kendi sayılarıyla), OG'de ne gerekirdi, ve "tetikli dalga biçimi yakalama bir sonraki donanım revizyonunun konusudur" paragrafı.
**Dikkat:** "Yapabiliriz" denmeyecek; "bugünkü mimari bunu göremez" denecek. Kod önerilmeyecek (GK2 + GK3 + donmuş şema).

### F-18 · docs/11'e iki standart satırı ve ISA-101 seviye haritası
Cihazın kendi ürün sınıfı standardını ve arayüz dilimizin standardını tabloya ekler · **Etki:** orta · **Efor:** 1-1,5 saat · **Nerede yaşar:** [docs/11-standartlar-uyum.md](docs/11-standartlar-uyum.md), [docs/16-ux-tasarim.md](docs/16-ux-tasarim.md) §2 tablosuna bir sütun
**Sektörel dayanak:** IEC 62974-1:2017 (≤1 kV AC, pano içi/DIN ray, veri toplama ve ağ geçidi cihazları — kapsam doğrulandı; Socomec bu standarda tabi olduğunu beyan ediyor). ANSI/ISA-101.01 ekran hiyerarşisini dört seviye olarak tanımlar.
**Bizdeki boşluk:** "62974" depoda hiç geçmiyor — jüri "bu cihaz hangi standarda göre üretilir?" diye sorduğunda cevapsızız. ISA-101 docs/11'de hiç yok, oysa tüm arayüz dilimiz ona dayanıyor; seviye eşlemesi ("Filo → Pano → Nokta → Kara kutu") jüriye gitmeyen bir iç dosyada yazılı.
**Ne üretir:** İki yeni standart satırı + yedi ekranın ISA-101 seviye sütunu.
**Dikkat:** "Karşılıyoruz" değil "ürün sınıfı budur, EMC ve ortam doğrulaması yapılmadı" denmeli. Kiosk/duvar ekranı **önerilmiyor** — sekizinci ekran MoSCoW dışıdır ve kabul ölçütünü bozar. Türkiye mevzuatı satırına siber güvenlik yetkinlik modeli yönetmeliğinin adı da eklenebilir; ekteki kontrol maddeleri kamuya açık olmadığı için seviye iddiası yazılmaz.

---

## 5. C — Hackathon sonrası ürün yol haritası (3-12 ay)

Bu kova, jüri teslimi için değil ürünleşme için. Sıra etki sırasıdır; bağımlılıklar her maddede yazılı.

### F-19 · Kimlik doğrulama, rol ve kurumsal SSO (on-prem)
Onaylayan kimliğini istemciden değil kimlik belirtecinden alır ve uçları role bağlar · **Etki:** çok yüksek · **Efor:** 2-3 hafta · **Nerede yaşar:** yeni `backend/app/auth/`, [contracts/openapi.yaml](contracts/openapi.yaml), [deploy/compose.yaml](deploy/compose.yaml), [frontend/src/api/](frontend/src/api/) ve yedi ekran
**Sektörel dayanak:** IEC 62351-8 güç sistemi yönetimi için rol tabanlı erişimi tanımlar; Siemens SICAM kişiye bağlı hesapları buna göre rollendirir. IEC 62443-3-3 kullanıcı tanımlama, yetkilendirme ve denetlenebilir olayları ayrı sistem gereksinimleri olarak sayar.
**Bizdeki boşluk:** Hiçbir kimlik doğrulama yok; onay/raf isteğinde kullanıcı adı serbest metin. [docs/15-guvenlik-kvkk.md](docs/15-guvenlik-kvkk.md) bunu üç ayrı yerde bilinçli boşluk olarak belgeliyor.
**Ne üretir:** Rol bazlı yetki, kimlik belirtecinden gelen denetim izi, ekranlarda role göre gizlenen eylemler.
**Dikkat:** Bulut kimlik sağlayıcı GK4 gereği kullanılamaz; on-prem çözüm şart. Bu madde F-20 ve F-26'nın ön koşuludur.

### F-20 · Denetim izinde kurcalama kanıtı (hash zinciri)
Alarm ve bildirim denetim izini zincirleyip bağımsız bir doğrulayıcıyla sınanabilir kılar · **Etki:** yüksek · **Efor:** 1-2 hafta (F-19 sonrası) · **Nerede yaşar:** [deploy/initdb/](deploy/initdb/), [backend/app/db.py](backend/app/db.py), yeni `scripts/verify_journal.py`, [backend/tests/](backend/tests/)
**Sektörel dayanak:** IEC 62443-3-3 denetim bilgisinin korunmasını ayrı bir gereksinim sayar; Siemens SICAM güvenlik denetim izini kalıcı tutup dışa aktarır.
**Bizdeki boşluk:** Denetim izi düz bir tablo; yetkili bir veritabanı kullanıcısı bir satırı sessizce silebilir.
**Ne üretir:** Negatif testle **ölçülmüş** bir iddia: bir satır bozulduğunda doğrulayıcının kaçıncı halkada durduğu.
**Dikkat:** Kimlik doğrulama olmadan zincir yalnızca "kayıt değişmedi"yi kanıtlar, "kim yaptı"yı değil — bu yüzden F-19'dan sonra gelir. Geriye dönük hash üretilemez; göç zinciri o andan başlatır ve bunu kayda geçirir.

### F-21 · Varlık kütüğü: CBS tekil kodu, künye ve bakım takvimi
Panonun ne olduğunu ve kimi etkilediğini sisteme getirir · **Etki:** çok yüksek · **Efor:** 2-3 hafta · **Nerede yaşar:** [deploy/initdb/](deploy/initdb/), [backend/app/api/panels.py](backend/app/api/panels.py), [contracts/openapi.yaml](contracts/openapi.yaml), [frontend/src/components/RiskMatrisi.tsx](frontend/src/components/RiskMatrisi.tsx), [frontend/src/pages/FiloListesi.tsx](frontend/src/pages/FiloListesi.tsx)
**Sektörel dayanak:** EPDK CBS usul ve esasları dağıtım panosunu tekil kodla ve kullanıcı tesisleriyle eşleştirilmiş tutmayı zorunlu kılıyor; EA Technology CBRM/CNAIM sağlık × kritiklik ile riski parasallaştırıyor; ABB Emax 2 koruma birimi bile son bakım tarihinden sonraki bakımı kestiriyor.
**Bizdeki boşluk:** `panels` tablosunda sekiz alan var, hiçbiri trafo gücü, fider, abone sayısı, kritiklik veya bakım tarihi değil. Risk matrisinin etki ekseni bu yüzden risk skorunun kendisi — kodda dürüstçe itiraf edilmiş.
**Ne üretir:** Gerçek iki eksenli risk matrisi, kritikliğe göre önceliklendirme, bakım vadesi rozeti, ve tüm mevzuat çıktılarının (F-22, F-23) veri tabanı.
**Dikkat:** Paralel bir varlık ana kaydı **kurulmamalı** — birincil alan CBS tekil kodu olmalı ve künye "CBS'den içe aktarılır" diye etiketlenmeli. Üretici/seri no uydurulmaz, boş bırakılır.

### F-22 · Üst şebeke kesintisi bağıntısı ve OMS'e hazır kesinti olayı
Aynı anda susan N panoyu tek bir kesinti olayına çevirir · **Etki:** çok yüksek · **Efor:** 2-3 hafta (F-21 sonrası) · **Nerede yaşar:** yeni `backend/app/outage.py`, [backend/app/alarm_manager.py](backend/app/alarm_manager.py), [deploy/initdb/](deploy/initdb/), [frontend/src/pages/BolgeHaritasi.tsx](frontend/src/pages/BolgeHaritasi.tsx)
**Sektörel dayanak:** Enedis'te sayaç ve toplayıcılar AG arızasını çoğu zaman ilk müşteri aramadan önce tespit ediyor, bölge daraltmasıyla müdahale süresi ~%30 azalıyor; kesinti tespiti dağıtım trafosu izleyicilerinin dört ana kullanımından biri.
**Bizdeki boşluk:** Olay gruplama pano içidir; panolar arası hiçbir bağıntı yok. Bir fider açıldığında konsol yüzlerce ayrı "izleme sistemi arızası" alarmıyla dolar — oysa doğru yorum tersidir.
**Ne üretir:** Tek kesinti olayı, alt alarmların ona bağlanması, harita üzerinde kesinti bölgesi; OMS'in en değerli girdisi.
**Dikkat:** Pano→fider eşlemesi F-21'e bağımlı. Eşik ve pencere yapılandırılabilir olmalı; tek panolu durumda eski davranış aynen korunmalı. Hackathon penceresinde yalnızca "eşzamanlı sessiz pano sayısı" paneli ve bir tasarım notu yapılabilir.

### F-23 · EPDK Madde 8 kesinti kaydı üreteci ve sebep kanıt paketi
Olayı, mevzuatın saydığı alanlarla doldurulmuş bir kesinti kaydı taslağına çevirir · **Etki:** yüksek · **Efor:** 2 hafta (F-21, F-22 sonrası) · **Nerede yaşar:** yeni `backend/app/api/outage_record.py`, [deploy/initdb/](deploy/initdb/), [frontend/src/pages/OlayAnalizi.tsx](frontend/src/pages/OlayAnalizi.tsx)
**Sektörel dayanak:** EPDK Kalite Yönetmeliği Madde 8/2'nin alan listesi (doğrulandı); kesinti sebebinin sınıflandırılması doğrudan tazminat hesabına giriyor.
**Bizdeki boşluk:** Olay tablosunda sebep, sınıf, etkilenen kullanıcı ve dağıtılmayan enerji alanları yok; daha önemlisi **enerjinin geri geldiği an hiç gözlemlenmiyor**, yani süre ve sona erme bu depodan türetilemez.
**Ne üretir:** Madde 8 alanlarıyla bir kesinti kaydı taslağı + 72 saatlik kanıt zaman çizelgesi; sebep sınıfı için **öneri**, karar değil.
**Dikkat:** Çıktı kesinlikle "TASLAK" etiketli olmalı ve ölçmediğimiz alanlar "elle doldurulacak" diye işaretlenmeli. Önce enerji dönüşünün gözlemlenmesi (restorasyon tespiti) gerekir. Hackathon penceresinde yalnızca "hangi alanları ölçmüyoruz" tablosu yazılabilir.

### F-24 · IEC 61968 (CIM) ADMS/OMS adaptörü
Alarmı, kesinti olayını ve bakım önerisini dağıtım şirketinin kurumsal diline çevirir · **Etki:** yüksek · **Efor:** 3-4 hafta · **Nerede yaşar:** yeni `backend/app/export/cim.py`, `docs/` altında eşleme tablosu (contracts/ altına değil)
**Sektörel dayanak:** IEC 61968 ailesi dağıtım tarafı entegrasyonun standardı (3 şebeke işletimi, 4 kayıt ve varlık yönetimi, 6 bakım ve inşa, 9 sayaç okuma); ADM/GDZ'nin Mayıs 2026 ADMS alımı tam bu dünyaya giriyor.
**Bizdeki boşluk:** SCADA tarafımız nokta protokolü seviyesinde; bir alarm ADMS'te varlık ve iş nesnesine bağlanmadan iş akışı doğurmaz. Depoda "61968", "CIM", "ADMS", "OMS" geçen tek satır yok.
**Ne üretir:** Alarm ve kesinti olayının CIM kavram modeline eşlemesi + örnek mesajlar + bir dışa aktarıcı.
**Dikkat:** Resmî şemalara erişim yok — "gerçek şemaya uyuyor" iddia edilemez, "kavram modeline göre eşleme önerisi" denir. Olay tipi kodları standardın ekindedir, uydurulamaz. Eşleme dosyası donmuş sözleşme dizinine konmaz.

### F-25 · İş emri nesnesi, bakım penceresi ve CMMS/EAM entegrasyonu
Alarmı sahada işe çeviren köprüyü kurar · **Etki:** yüksek · **Efor:** 4-6 hafta (F-19, F-21 sonrası) · **Nerede yaşar:** yeni `backend/app/workorder.py`, [deploy/initdb/](deploy/initdb/), [backend/app/alarm_manager.py](backend/app/alarm_manager.py), [frontend/src/pages/AlarmKonsolu.tsx](frontend/src/pages/AlarmKonsolu.tsx)
**Sektörel dayanak:** IBM Maximo durum geçişleri ve SAP PM bildirim→iş emri→katalog kodlu kapanış zinciri yerleşik; IEC 61968-6 dağıtım tarafında iş emri mesajlarını tanımlıyor; Schneider HeatTag alarmın kritikliğini doğrudan bakım eylemine bağlıyor.
**Bizdeki boşluk:** Sözleşmede her öncelik için iş emri bayrağı var ve bir alarmın metni "planlı iş emri olmadan kapak açıldı" diyor — ama sistemde karşılaştırılacak bir iş emri nesnesi yok, yani o alarm bugün doğrulanamıyor. Bakım modu gerekçesiz, süresiz ve kimliksiz açılıyor ve en yüksek öncelik dışındaki her şeyi bastırıyor.
**Ne üretir:** İş emri nesnesi ve durum makinesi, gerekçeli ve süreli bakım penceresi, planlı kesinti duyurusuyla bağ, CMMS'e aktarılabilir ara biçim.
**Dikkat:** Hedef CMMS tahmin edilmemeli — ADM/GDZ'nin iş yönetimi ADMS alımıyla birlikte yenileniyor. En yüksek öncelikli alarmın asla bastırılmadığı makineyle korunmalı. Kapsam MoSCoW'da yeni bir kalem olarak beyan edilmeli.

### F-26 · Şirket, bölge ve işletme kırılımı (kırılımlı gösterge raporlaması)
Filoyu gerçek coğrafi ve kurumsal hiyerarşiye göre böler · **Etki:** orta · **Efor:** 3-4 hafta (F-19, F-21 sonrası) · **Nerede yaşar:** [deploy/initdb/](deploy/initdb/), [backend/app/api/insights.py](backend/app/api/insights.py), [frontend/src/pages/BolgeHaritasi.tsx](frontend/src/pages/BolgeHaritasi.tsx), [frontend/src/pages/FiloListesi.tsx](frontend/src/pages/FiloListesi.tsx)
**Sektörel dayanak:** ABB Ability EDCS çok-tesisli karşılaştırma; EPDK göstergeleri dağıtım bölgesi, il ve ilçe bazında hesaplatıyor; Socomec kurulumu yansıtan coğrafi + elektriksel hiyerarşi kurduruyor.
**Bizdeki boşluk:** Ayrım yalnızca pano kimliğinin önekinde; veri modelinde şirket, bölge veya il/ilçe alanı yok ve harita bunu bilinçli kusur olarak kaydetmiş.
**Ne üretir:** İl/ilçe bazlı harita, bölge kırılımlı filo göstergeleri, işletme müdürlüğü kıyaslaması.
**Dikkat:** ADM ve GDZ aynı grubun iki lisans şirketidir ve tek bir kurulumu paylaşır — ihtiyaç "iki müşteriyi yalıtmak" değil, "tek kurulumda kırılım". Kimlik doğrulama olmadan buna "çok kiracılı" denmez; olsa olsa görüntü filtresidir.

### F-27 · mTLS, cihaz başına topic yetkisi ve IEC 62351-3 TLS profili
Kenar-merkez arasındaki tüm bağlantıları şifreler ve cihazı kendi topic'ine hapseder · **Etki:** yüksek · **Efor:** 2-3 hafta · **Nerede yaşar:** [deploy/mosquitto.conf](deploy/mosquitto.conf) ve yeni ACL dosyası, ayrı bir compose profili, [backend/app/scada/](backend/app/scada/), [backend/app/ingest.py](backend/app/ingest.py), [backend/app/config.py](backend/app/config.py)
**Sektörel dayanak:** IEC 62351-3 güç sistemi protokolleri için TLS profilini tanımlar; Türkiye'de OSOS haberleşme donanımı asgari özellikleri cihazda kimlik doğrulama, şifreleme ve IP kısıtı şart koşuyor.
**Bizdeki boşluk:** Demo broker düz ve anonim; merkezin MQTT istemcisinde TLS çağrısı ve ayarlarda sertifika alanı yok. [docs/15-guvenlik-kvkk.md](docs/15-guvenlik-kvkk.md) bunu üç yerde bilinçli üretim farkı olarak yazıyor.
**Ne üretir:** Ölçülmüş bir kanıt: bir panonun sertifikasıyla başka bir panonun topic'ine yayın denemesinin broker tarafından reddedilmesi.
**Dikkat:** Varsayılan demo yolu bozulmamalı; ayrı profil, varsayılan kapalı, duman testi iki modda da koşmalı. Tam 62351-3 profili (şifre takımı kısıtları, iptal) uygulanmadan "62351 uyumlu" denmez. Sertifikalar asla commit edilmez.

### F-28 · Cihaz kimliği: IDevID/LDevID, sıfır-dokunuş kayıt ve PKI işletimi
Sertifikayı elle basılan bir dosyadan işletilebilir bir yaşam döngüsüne çevirir · **Etki:** yüksek · **Efor:** 6-10 hafta (donanım revizyonuyla) · **Nerede yaşar:** `firmware/core/` kimlik modülü, yeni `backend/app/pki/`, [deploy/](deploy/) altında yerel sertifika otoritesi, [hardware/pano-beyni/](hardware/pano-beyni/)
**Sektörel dayanak:** IEEE 802.1AR-2018 fabrika (IDevID) ve saha (LDevID) kimliğini tanımlar; IETF RFC 8995 (BRSKI) ve RFC 7030 (EST) sıfır-dokunuş kaydı standartlaştırır; IEC 62351-9 güç sistemi ekipmanı için anahtar yaşam döngüsü ve iptali tanımlar.
**Bizdeki boşluk:** BOM'da güvenli eleman var ama onu kullanan tek bir akış yok. F-27 sertifikaları elle üretir; bu üç panoda çalışır, 100+ modülde çalışmaz.
**Ne üretir:** Kayıt ucu, sertifika verme ve yenileme takvimi, iptal listesi ve broker yetkisinin sertifikadan türemesi.
**Dikkat:** GK3 nedeniyle bu teslimde kod yazılamaz; gerçek güvenli eleman ve bir üretim hattı prosedürü gerektirir. Hackathon payı yalnızca bir yol haritası paragrafıdır.

### F-29 · İmzalı OTA: manifest, A/B geçiş, anti-rollback ve kanarya kampanyası
Sahaya çıkmış 1.000 panonun yazılımını güvenle güncellenebilir kılar · **Etki:** çok yüksek · **Efor:** 4-6 hafta · **Nerede yaşar:** yeni `scripts/fw_manifest.py`, kenar tarafında ilk komut tüketicisi, merkezde kampanya uçları ve tabloları
**Sektörel dayanak:** IETF RFC 9019 güncelleme mimarisinin rollerini, RFC 9124 manifest bilgi modelini (imza, sürüm, uygulanabilirlik, geri sürüm yasağı) tanımlar; seçilen mikrodenetleyici A/B yuvası ve otomatik geri dönüşü yerleşik sunuyor; ThingsBoard'un yayımlanmış varsayılanı 60 saniyede 100 cihaz.
**Bizdeki boşluk:** [docs/08-kurulum-proseduru.md](docs/08-kurulum-proseduru.md) sahaya dokunmadan imzalı OTA sözü veriyor, [docs/15-guvenlik-kvkk.md](docs/15-guvenlik-kvkk.md) bunu tasarım olarak işaretliyor, kodda hiçbir karşılığı yok. Dahası komut konusu bugün tek yönlü: kenarda hiçbir komut tüketicisi yok.
**Ne üretir:** İmzalı manifest, A/B geçiş ve otomatik geri dönüş, kanarya halkaları ve kapı kriterleri, kampanya durumu.
**Dikkat:** MoSCoW'da açıkça "Won't" — hackathon penceresinde başlanmamalı. Koruma cihazına hiçbir güncelleme yolu açılmaz (GK6) ve bu testle gösterilmeli. İlk teslim edilebilir parça yalnızca manifest üreteci ve anti-rollback testidir.

### F-30 · Güvenli önyükleme, donanımsal güven kökü ve firmware direnci
Güncelleme yeteneğinin karşı ağırlığını kurar · **Etki:** yüksek · **Efor:** donanım revizyonuyla birlikte, 6-10 hafta · **Nerede yaşar:** [docs/13-donanim-tasarimi.md](docs/13-donanim-tasarimi.md), [hardware/pano-beyni/](hardware/pano-beyni/), firmware önyükleyici yapılandırması
**Sektörel dayanak:** NIST SP 800-193 koruma / tespit / kurtarma üçlüsünü tanımlar; seçilen mikrodenetleyici imzalı imaj ve tek yönlü sürüm sayacı sunar.
**Bizdeki boşluk:** Güvenlik hikâyemizin tamamı merkezde duruyor; kenar cihazın kendisi için tek satır tasarım notu var. İmzasız firmware kabul eden bir kenar, 1.000 panoya aynı anda kötücül yazılım dağıtmanın yoludur.
**Ne üretir:** Üretim hattında anahtar yönetimi, tek yönlü sigorta yakma prosedürü, hata ayıklama portunun kapatılması ve kurtarma senaryosu.
**Dikkat:** GK3 ihlali — gerçek donanım olmadan gösterilemez ve sigorta yakma geri alınamaz. Bu teslimde kod yazılmamalı; uygulaması olmayan bir başlık dosyası bile "var gibi görünme" üretir.

### F-31 · Düğüm kimliği ve sensör sapması tespiti
Sistemin düğüm sayısını değil düğümün kendisini tanımasını sağlar · **Etki:** orta · **Efor:** 4-6 hafta · **Nerede yaşar:** [contracts/mqtt-telemetry.schema.json](contracts/mqtt-telemetry.schema.json), [contracts/modbus-map.yaml](contracts/modbus-map.yaml), [contracts/alarm-codes.yaml](contracts/alarm-codes.yaml), [libs/panoalgo/panoalgo/quality.py](libs/panoalgo/panoalgo/quality.py), [deploy/initdb/](deploy/initdb/), [frontend/src/pages/CihazSagligi.tsx](frontend/src/pages/CihazSagligi.tsx)
**Sektörel dayanak:** Rittal CMC III sensörleri otomatik tanıyıp tek tek izliyor; Schneider CL110 için batarya ve servis ömrü takip edilen bir veri; OMA LwM2M bağlantı sağlığını ayrı bir nesne olarak standartlaştırıyor.
**Bizdeki boşluk:** Sağlık bloğu yalnızca "kaç düğüm iyi / kaç düğüm var" taşıyor; düğüm kimliği hiçbir yerde yok, yani bir düğüm kaybolduğunda hangi fiziksel parçanın gittiğini söyleyemiyoruz. Dahası sensör sürüklenmesini **üretiyoruz** ama tespit eden hiçbir kural yok — FMEA'daki en yüksek risklerden birinin azaltıcı önlemi kâğıt üstünde.
**Ne üretir:** Düğüm listesi ve kimliği, sensör kütüğü, ardışık sapma için yeni bir alarm kodu, düğüm bazına inen cihaz sağlığı ekranı.
**Dikkat:** Tek başına donmuş sözleşmenin üç dosyasına birden dokunuyor ve üç üretilmiş dokümanın yeniden üretimini gerektiriyor — dondurma öncesi kesinlikle başlanmamalı. "İzlenebilir ölçüm" (metrolojik izlenebilirlik) iddiası akredite kalibrasyon olmadan kurulamaz; yalnızca "kütük ve vade takibi" denebilir.

### F-32 · L2 filo akran karşılaştırması ve taban geçerliliği
K₀ körlüğünü akran dağılımı ve değişim noktası tespitiyle kapatır · **Etki:** yüksek · **Efor:** 3-4 hafta (gerçek filo verisiyle) · **Nerede yaşar:** yeni `libs/panoalgo/panoalgo/fleet.py` ve `onset.py`, [libs/panoalgo/panoalgo/detect.py](libs/panoalgo/panoalgo/detect.py), [backend/app/api/insights.py](backend/app/api/insights.py)
**Sektörel dayanak:** GE Vernova SmartSignal beklenen değeri benzerlik tabanlı modelleyip artığı izliyor; ISO 17359 baz çizgisinin yinelemeli optimize edilmesini istiyor; drift ve değişim noktası için olgun, saf Python, tamamen yerel kütüphaneler mevcut.
**Bizdeki boşluk:** [docs/05-anomali-tespiti.md](docs/05-anomali-tespiti.md) kendi ifadesiyle "L2 katmanı henüz kod üretmiyor" diyor ve sözleşmede L2 etiketli tek bir alarm kodu yok. Devreye alma anında zaten bozuk olan bir bağlantıda K/K₀ hep 1,0 kalır ve o noktayı ancak akranları ele verir. Taban bir kez donuyor ve bakımdan sonra da güncellenmiyor.
**Ne üretir:** Akran sıralama skoru, bozulmanın başlangıç anı, operatör onayına sunulan yeniden baz alma önerisi.
**Dikkat:** Sentetik filoda K₀ sınırlı düzgün dağılımdan geldiği için sağlıklı bir pano yapısal olarak aykırı çıkamaz — sentetik veride "mükemmel ayrım" bir üreteç artefaktıdır, yöntem kanıtı değil. Otomatik yeniden baz alma alarmı susturabilir; yalnızca öneri üretmeli ve yazılım FMEA'sına bir satır girmeli.

### F-33 · Operatör geri bildirimi, olay kapanış kodu ve isabet ölçümü
"Bu alarm doğru muydu" sorusunun cevabını sisteme geri yazar · **Etki:** yüksek · **Efor:** 3-4 hafta (F-19, F-25 sonrası) · **Nerede yaşar:** [frontend/src/components/AlarmNedeni.tsx](frontend/src/components/AlarmNedeni.tsx), [backend/app/alarm_service.py](backend/app/alarm_service.py), [deploy/initdb/](deploy/initdb/), [libs/panoalgo/panoalgo/validate.py](libs/panoalgo/panoalgo/validate.py)
**Sektörel dayanak:** ISO 14224 her arızayı "gözlenen problem / neden / yapılan iş" üçlüsüyle kaydeder; ISA-18.2 izleme, değerlendirme ve denetim aşamalarını zorunlu kılar; durum izleme platformlarında kapanış geri bildirimi tahmin doğruluğunu besleyen standart döngüdür.
**Bizdeki boşluk:** Hiçbir yerde alarmın doğru çıkıp çıkmadığı tutulmuyor; dokuz hipotezimizin saha isabeti ölçülemiyor ve doğrulama sonsuza kadar sentetik veriye mahkûm kalıyor. Kara kutu zaman çizelgesi tek yönlü: arayüz "not" satır türünü bekliyor ama merkez hiç üretmiyor.
**Ne üretir:** Kapanış kodu taksonomisi, hipotez isabet oranı ve saha doğruluğunun sentetik doğrulukla yan yana raporlanması.
**Dikkat:** Kimlik doğrulama olmadan "kim kapattı" doğrulanamaz. Demo verisinden üretilen isabet oranı gerçek isabet oranı değildir ve öyle sunulamaz.

### F-34 · Tetikli dalga biçimi yakalama (arıza öncesi imza)
10 saniyelik mimarinin göremediği hızlı elektriksel imzayı görünür kılar · **Etki:** çok yüksek · **Efor:** donanım revizyonu; 2-3 ay · **Nerede yaşar:** [hardware/pano-beyni/](hardware/pano-beyni/) yeni analog ön uç, `firmware/core/` tetik ve halka tampon, [contracts/mqtt-telemetry.schema.json](contracts/mqtt-telemetry.schema.json), [frontend/src/pages/OlayAnalizi.tsx](frontend/src/pages/OlayAnalizi.tsx)
**Sektörel dayanak:** Texas A&M DFA on yılı aşkın sürede 20'den fazla dağıtım şirketiyle yüksek çözünürlüklü dalga biçimlerinden arıza öncesi imza çıkarıyor; Gridware saniyede binlerce ölçümle harmonik ve mekanik imza analizi yapıyor; Whisker Labs mikro-ark tespitini tüketici ölçeğinde ticarileştirmiş.
**Bizdeki boşluk:** Tüm tespit zincirimiz 10 saniyelik skaler değerler üzerine kurulu. Yavaş ısıl bozulmayı çok iyi görüyor (S1'de 209 saat), seri arkı ve kontak kıvılcımlanmasını fiziksel olarak göremiyor.
**Ne üretir:** Tetikli olay dosyası, kara kutuda dalga biçimi paneli, ark ve kısmi deşarj öncüllerinin gerçek imzası.
**Dikkat:** GK3 ve donmuş sözleşme nedeniyle bu teslimde yalnızca bir tasarım bölümü yazılır (bkz. F-17). Bugünkü mimarinin sınırı açıkça söylenmeli.

### F-35 · Tam güç kalitesi zinciri (gerilim THD'si, frekans, fliker) ve EN 50160 değerlendirmesi
Topladığımız ama kullanmadığımız gerilim tarafını gerçek bir mevzuat çıktısına çevirir · **Etki:** orta · **Efor:** 1-2 ay · **Nerede yaşar:** [contracts/modbus-map.yaml](contracts/modbus-map.yaml), [contracts/mqtt-telemetry.schema.json](contracts/mqtt-telemetry.schema.json), [sim/mpr53cs_sim.py](sim/mpr53cs_sim.py), `firmware/core/modbus_map.c`, yeni `libs/panoalgo/panoalgo/pq.py`
**Sektörel dayanak:** EPDK Kalite Yönetmeliği teknik kalite hükümleri TS EN 50160'a atıf yapıyor; Siemens ve Schneider'de EN 50160 raporlaması ana modül; ENWL 10 dakikalık pencerenin yeterli olduğunu sahada ölçmüş.
**Bizdeki boşluk:** Gerilim genliği dışında hiçbir parametre yok: okunan THD **akım** THD'sidir, dengesizlik **akım** dengesizliğidir, frekans ve fliker hiç yok. Üreteçte üç fazın gerilimi aynı formülden geliyor, yani sentetik veri hiçbir zaman sınır dışına çıkamaz.
**Ne üretir:** 10 dakikalık toplama, haftalık yüzdelik değerlendirmesi, parametre başına uygun/uygun değil kararı.
**Dikkat:** Mevzuata esas ölçüm belirli bir ölçüm cihazı sınıfı gerektirir ve kullandığımız enerji analizörünün bu sınıfta olduğu **doğrulanmadı** — çıktı "gösterge amaçlı ön tarama" olarak adlandırılmalı, resmî ölçümün yerine geçtiği asla iddia edilmemeli. Üç donmuş sözleşme dosyasına birden dokunur.

### F-36 · Uyarlanabilir raporlama ve hücresel veri bütçesi
Kenarın tespit hızını düşürmeden yayın hacmini azaltır · **Etki:** orta · **Efor:** 2-3 hafta · **Nerede yaşar:** yeni `libs/panoalgo/panoalgo/reporting.py`, [libs/panoalgo/panoalgo/edge.py](libs/panoalgo/panoalgo/edge.py), [sim/panosim.py](sim/panosim.py), [docs/09-olceklenebilirlik.md](docs/09-olceklenebilirlik.md)
**Sektörel dayanak:** ENWL 1 dakikalık örneklemeyi veri hacmi yüzünden 10 dakikaya düşürdü; ölü bantlı kendiliğinden gönderim IEC 104'te standart pratik (bizde zaten uygulanıyor); Memfault cihaz telemetrisini 9 bayta kadar inen parçalarla taşıyor.
**Bizdeki boşluk:** Kenar her turda tam yük üretiyor; raporlama kararı katmanı yok. [docs/09-olceklenebilirlik.md](docs/09-olceklenebilirlik.md) periyot ve ölü bandın etkisini dürüstçe "uygulanmadı" olarak işaretliyor ve tahmin ile ölçümü ayrı sütunlarda tutuyor — yani kapatılacak bir yalan değil, tamamlanacak bir kaldıraç var.
**Ne üretir:** Nokta başına ölü bant, azami sessizlik süresi, olayda anında yayın; ölçülmüş veri hacmi azalması ve filo toplamı aylık maliyet kalemi.
**Dikkat:** Seyrelen yalnızca **yayın** olmalı, tespit kenarda 10 saniyede koşmaya devam etmeli — aksi halde unutma faktörü ve K kestirimi bozulur. Ölçüm, yük testinin kendi şablon üreteciyle değil gerçek fizik üreteciyle yapılmalı; yoksa ölçülen oran gürültünün artefaktı olur.

---

## 6. Bilinçli olarak önermediklerimiz

Aşağıdaki fikirler sektör taramasında çıktı, depoya karşı doğrulandı ve üç eleştirmenden en az biri tarafından elendi. "Nereye gitti" sütunu, fikrin tamamen mi elendiğini yoksa yalnızca 15-20 Eylül penceresinden mi çıkarıldığını gösterir.

| Fikir | Neden elendi | Nereye gitti |
|---|---|---|
| EN 50160 tam uygunluk raporu üreteci (üç kopyanın ikisi) | Dayanak gösterilen yönetmelik yürürlükten kalkmış; üreteç hiçbir hafta ihlal üretemiyor (tautoloji); ölçüm cihazı sınıfı doğrulanmadı | Yol haritası F-35; hackathon dilimi A çizgisinin altında |
| Sparkplug B köprüsü | Standart gerçek ama alıcı yanlış: fabrika/IIoT dili, hiçbir Türk dağıtım şirketi SCADA'sı konuşmuyor; yeni dizin + yeni bağımlılık | Tamamen elendi |
| OPC UA salt okunur sunucu | Hedef müşterinin dili değil; adayın kendi etkisi "düşük"; odaklanmama sinyali verir | Tamamen elendi |
| DNP3 nokta planı ve outstation (iki aday) | Türkiye telekontrolünde yerleşik protokol IEC 104 ve o bizde canlı; aynı pencerede ikinci bir "kâğıt protokol" doküman şişirmesi olarak okunur | Tamamen elendi |
| IEC 61850 ICD/SCL dosyası ve MMS sunucusu | Kategori hatası: AG panosuna takılan izleme kutusu istasyon veri yolunda bir koruma cihazı değil; doğrulayıcıya erişim olmadan dosya teslim edilemez | Tamamen elendi; OG'ye çıkış senaryosu F-15 içinde tek paragraf |
| IEC 61968/CIM'in üç ayrı aday kopyası | Aynı iş üç kez sayılmış ve her biri ayrı doküman açıyor | Tek yol haritası maddesine indirildi (F-24) |
| Federe öğrenme ile iki şirket arasında model paylaşımı | Premis çöküyor: ADM ve GDZ aynı grubun iki lisans şirketi ve tek bir platformu birlikte satın aldılar | Tamamen elendi |
| Weibull/Cox ile filo arıza olasılığı | Arıza zamanlarını üreteçte biz enjekte ediyoruz; model kendi varsayımımızı geri okur, üretilen her olasılık GK10 ihlali olur | Yalnızca "gerçek olasılık için gereken veri" kutusu (F-05 içinde) |
| Genişletilmiş Kalman filtresi | Donmuş Modbus haritasına yeni register ister ve doğrulanmış C/Python eşitlik kanıtını yeniden kurmayı gerektirir; "bedava güven aralığı" iddiası yanlış | Tamamen elendi |
| Enerji dengesi ile kayıp-kaçak tespiti | Yanlış ölçüm noktası (abone sayacı tarafına erişimimiz yok), yanlış bölge (Ege düşük oranlı), üç donmuş dosya | Tamamen elendi |
| OSOS/MASS ve ihbar hattıyla çapraz doğrulama | Teslim edilmiş bir KVKK beyanını ("tekil abone tüketimi toplanmaz") geçersiz kılıyor | Tamamen elendi |
| Operatör eğitim ve tatbikat modu | Bu ürün kategorisi işletmecinin SCADA/ADMS tedarikçisinden alınır; ayrıca dayandığı gerekçe (senaryo oynatıcı nasılsa yazılacak) artık geçersiz | Tamamen elendi |
| Alarm tepki prosedürü kartları (22 kod için SOP) | Dağıtım şirketi kendi İSG talimatı ve çalışma izni prosedürünü kullanır; uydurma emniyet adımı sorumluluk doğurur | Tamamen elendi; yalnızca mevcut öneri metinleri korunur |
| Alarm felsefesi, rasyonalizasyon kaydı ve denetim/MOC dokümanları | Üç ayrı yeni doküman; gerekçelerin çoğu mevcut alarm matrisinde zaten tablo halinde var; değerlerin ikinci kez yazılması çelişki riski | Tamamen elendi; MOC için tek cümlelik atıf yeterli |
| Bakım penceresi takvimi ve planlı bastırma (tam sürüm) | En çok testli modülün bastırma yoluna dokunuyor; yanlış yazılırsa en yüksek öncelikli alarmı susturur | Dar dilimi F-25'e taşındı |
| Cihaz künyesi / varlık kütüğü kopyaları (dört adaydan üçü) | Aynı şema göçünü dört kez ödemek; seri no ve abonelik kimlikleri GK3 gereği uydurma olacak | Tek maddede birleşti (F-21) |
| Yaygınlaştırma önceliklendirme aracı (iki kopya) | Gerçek varlık verisi olmadan çıktı bir bulgu değil yöntem gösterimi; iki kopya çelişen iki sıralama üretir | Tamamen elendi; etki sıralaması F-21'in doğal çıktısı |
| Kimlik doğrulama / RBAC'ın hackathon içinde uygulanması | 17 Eylül'e 2,5 gün; donmuş sözleşmeyi ve tüm arayüz çağrı yüzeyini kırar; eksiklik zaten bilinçli karar olarak belgelenmiş | Yol haritası F-19 |
| Hash zinciri, mTLS, SBOM, PSIRT, fuzzing, RPO/RTO tatbikatı, 62443 öz değerlendirme, tehdit modeli, ürün güvenlik beyanı | Değerlendirme kriterlerinin hiçbiri doğrudan güvenlik değil; bunlar satın alma komitesi artefaktı ve ekip kapasitesi K/Y kalemleriyle dolu | Yalnızca imaj digest sabitlemesi A kovasında (F-02); gerisi F-19/F-20/F-27 |
| İmzalı OTA, device twin, reset nedeni telemetrisi, sıfır-dokunuş kayıt, secure boot | MoSCoW "Won't" ihlali, donmuş telemetri şeması ve GK3; kenarda komut tüketicisi bile yok | Yol haritası F-28/F-29/F-30/F-31 |
| IEC TR 60890 ile muhafaza ısınma hesabı | İki uydurma girdi üst üste gerekiyor (katsayı tabloları standardın içinde, watt cinsinden kayıp gücü depoda yok) | Tamamen elendi |
| ttl güven bandı ve ISO 13381-1 aralığı (iki kopya) | Aynı bütçeden prognoz geri testi daha fazla ölçülmüş sayı üretiyor; eğim yüzdeliği gerçek güven aralığı değil; asıl belirsizlik model hatası | Tamamen elendi; F-04 yerine geçiyor |
| seq boşluk muhasebesi, heartbeat topic'inin tüketilmesi, uyarlanabilir raporlamanın ölçümü | Jüri masasında görünmüyor, donmuş şemaya veya bekleyen onaylara bağlı, ya da ölçüm zemini henüz gerçek fizik üretecine bağlanmamış | F-36 ve yol haritası; biri dürüstlük satırı olarak yazılır |

---

## 7. Eğer sadece 3 şey yapılacaksa

1. **F-02 — GK10 bütünlük geçişi (1-1,5 saat).** Maliyet dokümanımız kendi ölçülmüş sonucumuzu "ölçülecek" diye yazıp performansımızı düşük gösteriyor; kara kutu penceremiz manşet sayımız olan 209 saati alamıyor; bir imaj etiketi sabit olmadığı için tüm ölçümlerin tekrar üretilebilirliği askıda. Üçü de kendi kanıtımızla kendi metnimiz arasındaki çelişki — jüri bunları kodu koşturunca tek tek bulur. Saat başına getirisi bu listedeki her şeyden yüksek ve yeni hiçbir risk üretmiyor.

2. **F-03 — P3 günlük özeti (3-4 saat).** Jüriye teslim edilen alarm matrisi "P3 günlük özete, SYS toplu özete gider" diye yazıyor; kodda bunun tek satır karşılığı yok. Üstelik erken uyarının tamamı P3 önceliğinde, yani 209 saatlik en güçlü iddiamız bugün pratikte bir veritabanı satırında bitiyor ve kimsenin telefonuna düşmüyor. Sözleşme değişikliği gerektirmeyen, tek kulvarda biten ve verilmiş bir sözü tutan tek madde bu.

3. **F-04 — Prognoz geri testi (3-5 saat).** Elimizdeki en güçlü kriter anomali tespiti ve orada tek noktalı bir iddiamız var: "209 saat önce uyardık". Tahminin zamanla yakınsayıp yakınsamadığı, ne zaman güvenilir hale geldiği ölçülmemiş. Fixture'larda sınır ihlali anı zaten etiketli olduğu için yeni veri gerekmiyor, sadece kod gerekiyor — GK10 açısından kapatılabilecek en ucuz boşluk. Sonucun bir kısmı kötü çıkarsa (sensör arızası senaryosundaki yanlış tahminler gibi) bu bir risk değil, bu ekibin en ayırt edici özelliğinin kanıtıdır.
