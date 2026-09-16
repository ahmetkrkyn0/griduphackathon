# 19 — TEDAŞ Şartname Uyum Haritası

> **Sahip:** Kişi C · **Tarih:** 16 Eylül 2026 · **Kaynaklar:** `HACKATHON_ANALIZ_RAPORU.md` §3.1–§3.3
> (komitenin verdiği `Hackathon Verileri/AG PANO MALZEME ŞARTNAMESİ.pdf`'ten okunarak çıkarılmıştır),
> `hardware/pano-beyni/bom.csv`, `io-tablosu.md`, `blok-diyagrami.md`, `docs/13-donanim-tasarimi.md`,
> `docs/08-kurulum-proseduru.md`, `docs/11-standartlar-uyum.md`.

**Bu dokümanın amacı** jüri değerlendirme kriterlerinden **"saha koşullarında uygulanabilirlik"**
başlığına dürüst bir cevap vermektir. Cevap "hepsini karşılıyoruz" değildir. Bu teslimde **hiçbir
donanım üretilmedi, hiçbir tip testi (EMC, ortam, titreşim, dielektrik) yapılmadı.** Aşağıdaki her
satır ya bir **tasarım hedefidir** ya da **doğrulanması gereken açık bir kalemdir**. Bu ayrımı
kendimiz yazıyoruz ki jüri bulmak zorunda kalmasın (GK3).

---

## 1. Önce bir ayrım: ortada iki ayrı şartname var

| | Şartname | Konusu | Bu depodaki durumu |
|---|---|---|---|
| **(1)** | **TEDAŞ-MLZ/2003-06.B** — AG Dağıtım Panoları Teknik Şartnamesi | Panonun kendisi: çalışma koşulları, yapı, malzeme, bölmeler, donanım listesi | **Tam metin elimizde.** Komitenin verdiği `AG PANO MALZEME ŞARTNAMESİ.pdf` (66 sayfa) budur; madde numaraları `HACKATHON_ANALIZ_RAPORU.md` §3.1'de PDF'ten okunarak çıkarılmıştır. Bölüm 2'deki tablo bu şartname üzerine kuruludur. |
| **(2)** | **TEDAŞ-MLZ/2019-064.B** — Haberleşme Ünitesi Teknik Şartnamesi | Panoya takılan haberleşme ünitesi — yani bizim ürün sınıfımıza en yakın belge | **Tam metnine erişilmedi.** `docs/11-standartlar-uyum.md`'de yalnızca **adı** geçiyor, arkasında içerik yok. Deponun kendi analiz raporunda "1 Ocak 2025'ten itibaren zorunlu" olarak kaydedilmiştir; bu bilgi **ikincil kaynaktan** gelmektedir ve bu oturumda **doğrulanmamıştır.** |

> **Bu dosyanın en dürüst satırı:** *TEDAŞ-MLZ/2019-064.B'nin tam metnine erişilmedi; aşağıdaki
> satırların tamamı 2003-06.B şartnamesi ve genel AG pano pratiği üzerinden kurulmuştur.*
> **2019-064.B için hiçbir madde numarası yazılmamıştır** — yazılsaydı uydurma olurdu.

**2019-064.B hakkında yazabileceğimizin tamamı:**

- Adı: TEDAŞ-MLZ/2019-064.B, konusu **haberleşme ünitesi**.
- Bir dağıtım panosuna takılan haberleşme ünitesinin tabi olduğu belgedir; Pano Beyni'nin ürün
  sınıfı büyük olasılıkla bu şartnamenin kapsamına girer (**değerlendirme, doğrulanmadı**).
- Zorunluluk tarihi olarak deponun analiz raporuna "1 Ocak 2025" kaydedilmiştir — **ikincil kaynak,
  bu oturumda doğrulanmadı.**
- Muhtemel bir **uygunluk/tip onayı süreci** (TEDAŞ onaylı ürün listesi, numune testi) pilot
  öncesinde çözülmesi gereken **ticari ve takvimsel bir risktir**; içeriği bilinmediği için bu
  teslimde ne süresi ne maliyeti tahmin edilmiştir. Bkz. Bölüm 4.
- **Sonraki adımın ilk maddesi:** bu şartnamenin tam metninin ADM/GDZ üzerinden temin edilmesi.
  Bu doküman o metin geldiğinde yeniden yazılacak biçimde kurulmuştur.

---

## 2. Tablo (a) — TEDAŞ-MLZ/2003-06.B madde madde

Sütunların anlamı:

- **Karşıladığımızı iddia edebileceklerimiz:** depoda gerçekten bir dosyaya dayanan **tasarım
  hedefi**. "Karşılıyoruz" demiyoruz — **tip testi yapılmadı.**
- **Fiziksel doğrulama gerektirenler:** donanım üretildikten sonra ölçülmesi/test edilmesi gereken,
  bugün **bilinmeyen** kalemler.

| Madde (2003-06.B) | Şartname ne diyor | Karşıladığımızı iddia edebileceklerimiz (tasarım hedefi — tip testi yapılmadı) | Fiziksel doğrulama gerektirenler |
|---|---|---|---|
| **1.4 / Tablo 1** | Çalışma koşulları: dahili −5…+40 °C (24 sa ort. 35 °C), harici −25…+40 °C, rakım ≤ 2000 m, bağıl nem dahili +20 °C'de %90 / harici +25 °C'de %100, kirlilik Düzey II (dahili) / III (harici), buzlanma sınıf 10, deprem yatay 0,5 g dikey 0,4 g | Elektronik için **−40…+85 °C endüstriyel sınıf bileşen** ve **pano içi −25…+70 °C** bara yakını hedefi yazılıdır (`docs/13` §5). Nem/yoğuşma için akrilik konformal kaplama (IPC-CC-830), kutu içi nem alıcı (`docs/13` §5). Kirlilik sınıfı II varsayımıyla yalıtım koordinasyonu (`docs/13` §4). | **Hiçbiri ölçülmedi.** Sıcaklık döngüsü, soğuk/kuru sıcaklık, nemli ısı, rakım (barometrik) ve titreşim/sarsma testlerinin **hiçbiri yapılmadı.** Ayrıca kontrolcünün üst bölmedeki **gerçek yerel sıcaklığı hiç ölçülmedi** — pano ortam sıcaklığı ile bara yakını arasındaki bir değerdir, hangi değer olduğu bilinmiyor. Bölüm 3'ün tamamı bu maddeye bağlıdır. |
| **2.2.1.xiii** | Tüm plastik yalıtkan malzemeler IEC 60695-11-10'a göre **V-0** | BOM'da kutu **V-0 polikarbonat** olarak seçilmiştir (`bom.csv`, `Fibox ARCA 92/125 (PC V-0)`); mekanik kaynak da V-0 notuyla yazılıdır (`hardware/mekanik/din-kutu.scad`). Tasarım kuralı olarak kablo bağı/braket dahil pano içine giren tüm plastiklerin V-0 olması `docs/13` §5'te yazılıdır. | Her plastik parçanın **üretici V-0 sertifikası çekilmedi** — BOM'daki "V-0" ibaresi bizim seçim notumuzdur, veri sayfasından teyit edilmemiştir. Klemens gövdesi, konnektör, kablo bağı, sensör gövdesi ve konformal kaplamanın alev sınıfı **doğrulanmadı.** |
| **2.2.2** | Koruma derecesi: dahili **IP2X**, harici **IP54** | Kutu **IP20 dahili tip** olarak seçilmiştir (`bom.csv` tedarik notu, `blok-diyagrami.md` §2). IP20 kâğıt üzerinde IP2X'i kapsar; ancak **kutunun IP sınıfı veri sayfasından teyit edilmedi ve IEC 60529 testi yapılmadı** (bkz. Bölüm 3, satır 15). | **Harici tip pano için bir varyantımız yok.** IP54 gerektiren harici sahalarda kutu ve konnektör seçimi **yeniden yapılmalıdır**; bu teslimde tasarlanmadı. IP testi (IEC 60529) yapılmadı. |
| **2.2.3** | Sıcaklık artışları TS EN 61439-1 sınırlarını aşmayacak | L0 mutlak sıcaklık eşiklerimizin dayanağı budur (`contracts/alarm-codes.yaml`, `docs/05`). Kurulum kuralı olarak sensör gövdesinin **mevcut açıklık (clearance) / kaçak yolu (creepage) mesafesini azaltmaması** yazılıdır (`docs/08` §2 madde 3) — bu kural **elektrikseldir, ısıl değildir.** | **Kritik ve açık:** panoya cihaz eklemenin panonun kendi sıcaklık artışı doğrulamasını etkileyip etkilemediği **hiç ölçülmedi.** Pano bir tasarımı doğrulanmış düzenektir; içine sensör/kontrolcü eklemek panonun kendi doğrulamasını (TS EN 61439-1/-2) etkileyebilir. Bu, **pano üreticisi ve TEDAŞ ile birlikte** çözülmesi gereken bir konudur ve bu teslimde değerlendirilmemiştir. Ayrıca sensörün bara/pabuç bağlantısının **ısıl direncini değiştirip değiştirmediği** için depoda yazılı bir kurulum kuralı **yoktur** — açık kalem. |
| **2.2.5** | İç ark oluşumunu önleyici ve süresini kısaltıcı önlemler | TVOC-2 ark koruması panoda zaten vardır; bizim rolümüz **salt okunur izleme** ve koruma sisteminin sağlığını raporlamaktır (GK6; `docs/06-alarm-matrisi.md`, `blok-diyagrami.md` §1). Koruma devresine **yazma yapılmaz.** | Ark koşullarında (38 kA etken / 80 kA tepe — rapor §3.1) kontrolcünün ve sensörlerin mekanik/elektriksel davranışı **test edilmedi.** İç ark testi yapılmadı, yapılması da pano üreticisinin kapsamındadır. |
| **2.2.6.1** | Form 2B; dikey baraların önünde **alev almaz saydam gözetleme pencereli** kapaklar | Termal dizi sensörünün **saydam kapağın iç tarafına** monte edileceği, kapak dışından çalışmayacağı belgelenmiştir (rapor §3.1, `docs/08` §2 madde 4, `hardware/yerlesim/ek2-14-yerlesim.svg`). | Braket montajının kapak/kilit işlevini, Form 2B ayrımını ve kapak kapanma açıklığını bozup bozmadığı **fiziksel olarak denenmedi** (gerçek pano yok). |
| **2.2.8.1.iv** | Çatının iç tarafında veya panonun üst kısmında **haberleşme üniteleri için bölmeler**; talep halinde **harici anten çıkışı** | Kontrolcünün yeri bu maddeye göre seçilmiştir: üst bölme, "Modem" kutusunun yanı, ana baralardan **≥ 250 mm** (`docs/13` §3, `blok-diyagrami.md` §2). Hücresel anten harici anten çıkışından geçirilir (`io-tablosu.md` satır 6, `docs/08` §2 madde 6). | Bölmenin gerçek iç hacmi, DIN ray varlığı ve anten çıkışının **sahadaki mevcudiyeti panodan panoya değişir** — `docs/08` §1'de saha keşfi adımı olarak yazılıdır ama **hiçbir gerçek panoda kontrol edilmedi.** Metal kabin içinde hücresel/2,4 GHz sinyal seviyesi **ölçülmedi.** |
| **2.2.8.5** | Sıcaklık artışını ve **terlemeyi** önlemek için havalandırma: altta giriş, üstte çıkış; dahili panoların üst kapağında açıklık yok | Ortam düğümlerinin biri **alt kablo bölgesine** (giriş havası, yoğuşma riski en yüksek), biri **üst bölmeye** (çıkış havası) konumlandırılmıştır (`docs/08` §2 madde 4). Çiy noktası marjı tespit katmanımızın temel büyüklüğüdür (`docs/05` §6 — "L1 — Yoğuşma"); eşik seçiminin **ölçülmüş yanlış alarm bedeli** `docs/05` §11'dedir (eşiği kısmak 71,4 → 171,4 olay/100 pano/gün). | Gerçek bir panoda alt/üst hava sıcaklık farkının ve yoğuşmanın **fiziksel ölçümü yapılmadı**; çiy noktası modelimiz sentetik veriyle doğrulandı (`docs/12`), sahada değil. Kutunun havalandırma akışını engelleyip engellemediği **denenmedi.** |
| **2.2.10.1** | Cihazlar arası kablolar silikon yalıtımlı, kablo kanallarında; **lehim/ek yok** | **10 vidalı/fişli klemens konnektörü (J1–J10)** + **2 RF konnektörü** (U.FL dahili anten, SMA panel üstü anten çıkışı); lehimli ek yok (`io-tablosu.md` satır 5–6 ve "Toplam dış konnektör sayısı" satırı — o özet satırı "tamamı fişli/vidalı klemens" derken RF konnektörlerini saymamaktadır). Mimarinin tamamı **yeni kablo sayısını en aza indirmek** üzerine kuruludur: besleme iç ihtiyaç devresinden, sensörler kablosuz (`docs/08` §2). | Kullanılacak kabloların **silikon yalıtımlı ve doğru kesitte** olduğu bir malzeme kararıdır ve BOM'da **kablo kalemi yoktur** — montaj malzemesi listesi bu teslimde çıkarılmadı. |
| **2.2.10.2** | Ana baralar kalay kaplı elektrolitik bakır; 1600 kVA'da giriş **direkt bara bağlantılı** | Sıcak nokta adaylarının (bara ek noktaları, kayar bara civataları, pabuçlar) çıkarılması ve sensör yerleşimi bu maddeye dayanır (rapor §3.2, `hardware/yerlesim/`). | Bara üzerine **hiçbir fiziksel sensör monte edilmedi**; bağlantının ısıl temas kalitesi, montaj kuvvetinin bara bağlantısını gevşetip gevşetmediği ve sensörün kendi ısıl kütlesinin ölçümü saptırıp saptırmadığı **bilinmiyor.** |
| **2.2.11.i** | Ana girişte **Enerji Ölçer (Enerji Analizörü)** veya elektronik sayaç + ampermetre | Ana giriş elektriksel verisi **mevcut cihazdan Modbus ile** okunur, yeni akım sensörü eklenmez (`contracts/modbus-map.yaml` `electrical_mirror`, `docs/03`). MPR-53CS register haritası gerçek kılavuzdan alınmıştır (rapor §3.6). | Sahadaki cihazın **gerçekten MPR-53CS olduğu ve register haritasının birebir tuttuğu** yalnızca simülatörde doğrulandı (`docs/17` §2). Farklı marka/model analizörlerde harita **değişir** — bu bir entegrasyon riskidir. |
| **2.2.11.v** | Panolarda **modem kullanılabilecek**, uygun bölmelerde | Hücresel modem (Quectel EC200A-EU, `bom.csv`) ve özel APN yaklaşımı bu maddeye dayanır; modem konnektörü I/O tablosunda tanımlıdır (satır 7). | Şebeke kapsaması, özel APN erişimi, SIM tedariki ve gerçek bir sahada bağlantı sürekliliği **hiç test edilmedi**; `docs/17` §2'de "hücresel hat: tek makinede yerel ağ, gecikme ve kopukluk yok" olarak zaten bilinen sınırdır. |
| **2.2.11 (enerji ölçer özellikleri)** | Enerji ölçer **RS485 + MODBUS**; faz akımlarının min/max kaydı, enerji kesilince silinmemesi; şifreli programlanabilir 2 dijital röle çıkışı; 1–49. harmonik | RS485 #1 **master** portu bu cihazı okumak üzere izoleli olarak tasarlanmıştır (ADM2587E, `io-tablosu.md` satır 3); RS485 #2 **slave** portu RTU/SCADA'ya kendi haritamızı sunar (satır 4). Modbus RTU'nun tek master oluşu bir mimari senaryo olarak ele alınmıştır (`docs/03-modbus-haritasi.md` §2, Senaryo A/B/C). | Hattın gerçek elektriksel davranışı (hat uzunluğu, sonlandırma, mevcut master ile çakışma) **sahada ölçülmedi.** İzolasyon değerleri `io-tablosu.md`'de **veri sayfası değeri olarak** yazılıdır, bu oturumda veri sayfasından teyit edilmemiştir. |
| **2.2.12** | İç ihtiyaç çıkışı: 10 A priz + iç aydınlatma | Kontrolcü beslemesi **yeni hat çekilmeden iç ihtiyaç devresinden, sigortalı fişli klemensle** alınır (`io-tablosu.md` satır 1, `docs/08` §2 madde 1, kontrol listesi). Tipik sürekli tüketim **~0,6 A @ 5 V ≈ 3 W** (`blok-diyagrami.md` §4). | İç ihtiyaç devresinin gerçek yükü ve sigorta seçiciliği **sahada kontrol edilmedi.** Modem TX darbelerinde çekilen tepe akımın (SMPS 2 A'ya göre seçildi) devre üzerindeki etkisi **ölçülmedi.** Süperkapasitör "son nefes" süresi (~15,8 s) **hesaplanmıştır** (`docs/13` §2), ölçülmemiştir. |
| **5.3** | İş güvenliği: **5 güvenlik kuralı** (gerilimi kes, tekrar gelmesini engelle, gerilim yokluğunu kontrol et, toprakla ve kısa devre et, çalışma alanını işaretle) | Kurulum prosedürünün ilk adımı budur ve saha ekibinin imzaladığı kontrol listesinin ilk maddesidir (`docs/08` §2 ve §4). Hedef: **tek planlı kesinti penceresi, ≤ 45 dk, 2 kişi.** | **≤ 45 dk hedefi bir tasarım hedefidir, sahada ölçülmedi.** Prosedür gerçek bir panoda hiç uygulanmadı; gerçek uygulama süresi ve adım sırası pilotta doğrulanmalıdır. |
| **Elektriksel değerler bölümü** (rapor §3.1'de aktarılmıştır; madde numarası burada kasten yazılmamıştır) | 231/400 V, 3 faz 4 telli, 50 Hz, Uimp = 8 kV; 1600 kVA'da giriş anma akımı 2312 A; kısa devre 38 kA etken / 80 kA tepe | Yalıtım koordinasyonu (clearance/creepage, IEC 60664-1) ve manyetik alan hesabı bu değerler üzerinden yapılmıştır: **≥ 250 mm mesafede ~1,54 mT @ 30 cm** (`docs/13` §3, §4). Ölçüm zinciri `io-tablosu.md` satır 12'de yazılıdır: **ayrık çekirdekli AT sekonderi → burden direnci → INA226**; Hall etkili/açık manyetik devreli bir ölçüm elemanı **BOM'da yoktur** (`bom.csv`). Bu değerlendirmenin kaynağı `docs/13` §3'tür. | **Dielektrik dayanım ve darbe (Uimp) testi yapılmadı.** Kısa devre anında alanın ~35 kat artacağı **hesaptır** (`docs/13` §3), ölçüm değildir; RS485 TVS koruması ve mekanik montaj bu varsayıma göre seçilmiştir, doğrulanmamıştır. |

---

## 3. Tablo (b) — BOM parçası ↔ şartname ortam sınırı

**Bu tablonun değeri "hepsi uygun" demek değil, hangi parçanın doğrulanması gerektiğini bilmektir.**

**Uygulanan sınırlar** (kaynak: `HACKATHON_ANALIZ_RAPORU.md` §3.1 Tablo 1 + `docs/13` §5):

- **[A] Dahili pano ortamı:** −5…+40 °C (24 saat ortalaması 35 °C), bağıl nem +20 °C'de %90, kirlilik Düzey II, rakım ≤ 2000 m.
- **[B] Harici pano ortamı:** −25…+40 °C, bağıl nem +25 °C'de %100, kirlilik Düzey III, buzlanma sınıf 10, deprem yatay 0,5 g / dikey 0,4 g, rakım ≤ 2000 m.
- **[C] Pano içi, bara yakını tasarım hedefi:** **−25…+70 °C** (`docs/13` §5). Kontrolcü üst bölmededir, baralardan ≥ 250 mm; **yerel sıcaklığı [A] ile [C] arasında bir yerdedir ve ölçülmemiştir.** Tabloda en ağır durum olarak **[C]** uygulanmıştır.
- **[D] Yanıcılık:** madde 2.2.1.xiii — IEC 60695-11-10 **V-0** (pano içindeki tüm plastikler).

> **Uyarı — bu tablonun tek dürüst sütunu "çalışma aralığı" sütunudur.** Bu oturumda **hiçbir
> üretici veri sayfasına erişilmedi** (bu geliştirme ortamında internet erişimi yok —
> `hardware/pano-beyni/README.md`'deki KiCad notuyla aynı sebep). Bu yüzden **hiçbir parça için
> sıcaklık aralığı yazılmamıştır.** Yazılsaydı uydurma olurdu (GK10).

| # | BOM parçası (üretici kodu) | Adet | Çalışma aralığı | Uygulanan şartname sınırı | Uygun / uygun değil / doğrulanmadı | Neden bu satır riskli (mühendislik değerlendirmesi, ölçüm değil) |
|---|---|---|---|---|---|---|
| 1 | MCU modülü — Espressif ESP32-S3-WROOM-1-N8R8 | 1 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] −25…+70 °C, [A]/[B] nem | **Doğrulanmadı** | Sistemin kalbi; sıcaklık sınıfı yetmezse **tüm tasarım değişir**. Aynı modülün farklı sıcaklık sınıfına sahip varyantları olabilir; hangisinin sipariş edileceği BOM'da belirtilmemiştir. **Önce bu çekilmeli.** |
| 2 | Güvenli eleman — Microchip ATECC608A-SSHDA | 1 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] | **Doğrulanmadı** | Cihaz kimliği ve imzalı OTA bu parçaya bağlanacaktır — ancak her ikisi de `docs/15` §3.5'te **📐 tasarım düzeyi (uygulanmadı)** olarak işaretlidir; `GELISTIRME-BACKLOGU.md` imzalı OTA'yı **MoSCoW Won't, "tasarım düzeyinde bile yazılı değil"** sayar. Arızası cihazı üretim dışı bırakır. |
| 3 | Harici flash 16 MB — Winbond W25Q128JVSIQ | 1 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] | **Doğrulanmadı** | 7 günlük halka tampon burada tutuluyor (`blok-diyagrami.md`). Flash'ta **hem sıcaklık sınıfı hem de yazma döngüsü ömrü** doğrulanmalı; 10 saniyelik telemetri sürekli yazma demektir ve ömür hesabı bu teslimde **hiç yapılmadı.** |
| 4 | İzoleli RS485 transceiver — Analog Devices ADM2587EBRWZ | 2 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] + yalıtım (2500 Vrms hedefi) | **Doğrulanmadı** | `io-tablosu.md`'de 2500 Vrms / 1 dk yazılıdır; bu değer **veri sayfası iddiası olarak aktarılmıştır, teyit edilmemiştir.** Pano şebekesinden galvanik ayrımın tek dayanağı bu parçadır — karşılıklı zarar önlemenin kilit taşı. |
| 5 | İzoleli AC/DC SMPS 5 V 2 A — MEAN WELL IRM-10-5 | 1 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] + **rakım ≤ 2000 m** + yalıtım (3000 Vrms hedefi) | **Doğrulanmadı** | **En yüksek öncelikli üç kalemden biri.** Şebekeye doğrudan bağlanan tek parça. Üç ayrı doğrulama gerekir: (i) sıcaklık sınıfı ve **sıcaklıkla güç düşümü (derating)**, (ii) 2000 m rakımda yalıtım/soğutma düşümü, (iii) 3000 Vrms yalıtım iddiası. Ayrıca modem TX tepe akımını (2 A) karşılayıp karşılamadığı **ölçülmedi.** |
| 6 | 3V3 LDO regülatör — Texas Instruments TLV1117-33 | 1 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] | **Doğrulanmadı** | Lineer regülatör ısı üretir; **+70 °C ortamda kendi ısınmasıyla birlikte** ısıl bütçe bu teslimde **hesaplanmadı.** |
| 7 | Süperkapasitör 10 F 2,7 V — Eaton HB1840-2R7107-R | 2 (seri) | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] −25…+70 °C | **Doğrulanmadı** | **En yüksek öncelikli üç kalemden biri.** Süperkapasitörlerde kapasite ve eşdeğer seri direnç sıcaklıkla ve yaşlanmayla değişir; bu, "son nefes" hesabını (`docs/13` §2, ~15,8 s) doğrudan etkiler. Hesap **yeni ve oda sıcaklığındaki** bir parça varsayar. **Ömür sonu ve düşük sıcaklık davranışı hesaba katılmamıştır.** |
| 8 | 802.15.4/BLE modül — Nordic nRF52840 tabanlı modül (ör. Fanstel BT840F) | 1 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] | **Doğrulanmadı** | Ayrıca **kablosuz menzil/paket kaybı metal kabin içinde hiç ölçülmedi** — bu, sıcaklık sınıfından daha büyük bir risktir. Sensör düğümü tarafının donanımı **hiç tasarlanmadı** (aşağıdaki kapsam notu). |
| 9 | Hücresel modem — Quectel EC200A-EU | 1 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] | **Doğrulanmadı** | **En yüksek öncelikli üç kalemden biri.** Modemlerde tipik olarak "çalışma" ve "genişletilmiş/sınırlı işlev" sıcaklık aralıkları ayrı tanımlanır; hangi aralıkta hangi işlevin garanti edildiği **bilinmiyor.** Ayrıca operatör/bant onayı ve özel APN erişimi **doğrulanmadı.** |
| 10 | Kuru kontak röle 24 V — Omron G5LE-1-VD 24DC | 2 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] + [D] V-0 (gövde plastiği) | **Doğrulanmadı** | Elektromekanik parça: sıcaklık **ve** titreşim/deprem (0,5 g) altında kontak davranışı, ayrıca gövde plastiğinin alev sınıfı doğrulanmalı. |
| 11 | Darlington dizi sürücü — Texas Instruments ULN2003AN | 1 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] | **Doğrulanmadı** | Röle bobini sürerken güç harcar; yüksek ortam sıcaklığında paket ısı düşümü **hesaplanmadı.** |
| 12 | Optokuplör girişi — Toshiba TLP291 (PC817 eşdeğeri) | 4 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] + yalıtım (5000 Vrms hedefi) | **Doğrulanmadı** | `io-tablosu.md`'de 5000 Vrms yazılıdır — **aktarılmış veri sayfası iddiası, teyit edilmedi.** Ek olarak optokuplörlerde akım transfer oranı sıcaklıkla ve yaşla düşer; giriş direnci buna göre **boyutlandırılmadı.** |
| 13 | I2C akım/gerilim ADC — Texas Instruments INA226AIDGST | 3 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] | **Doğrulanmadı** | Yalnızca opsiyonel fider akımı ölçümünde kullanılır (S8). Ölçüm doğruluğunun sıcaklıkla kayması **karakterize edilmedi.** |
| 14 | Vidalı klemens 2 kutup — Phoenix Contact MC 1.5/2-ST-3.5 | 10 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] + [D] **V-0** + kirlilik Düzey II/III | **Doğrulanmadı** | J1 (230 VAC) bu klemens ailesinden geçiyor; **anma gerilimi, kirlilik derecesine göre kaçak yolu ve V-0 sınıfı** doğrulanmalı. BOM'da "J1–J10 gövde ortalama" notu vardır; yani **tek tip varsayılmıştır** — 230 VAC için ayrı bir seçim gerekebilir. |
| 15 | DIN ray kutu — Fibox ARCA 92/125 (PC V-0) | 1 | Doğrulanmadı — üretici veri sayfası kontrol edilmedi | [C] −25…+70 °C + [D] **V-0** + IP2X (dahili) / IP54 (harici) | **Doğrulanmadı** (BOM'da "V-0" notu var, veri sayfasıyla teyit edilmedi) | İki ayrı soru: (i) **V-0 sertifikası** gerçekten var mı, (ii) polikarbonatın **sürekli kullanım sıcaklığı +70 °C hedefinin üstünde mi.** Ayrıca harici tip pano için IP54 varyantı **seçilmedi.** |
| 16 | 4 katmanlı PCB + montaj — yerli PCB üreticisi | 1 | Doğrulanmadı — üretici/işlem şartnamesi belirlenmedi | [C] + [D] (laminat alev sınıfı) + kirlilik Düzey II | **Doğrulanmadı** | Laminat sınıfı, bakır kalınlığı, cam geçiş sıcaklığı ve **yüzey işlemi BOM'da tanımlanmamıştır.** Kirlilik ve yoğuşma altında yüzey kaçak yolu mesafeleri `docs/13` §4'te yalnızca **yöntem düzeyinde** ele alınmıştır; kart üzerinde çizilmiş bir yerleşim yoktur. |
| 17 | Konformal kaplama (akrilik) — işlem hizmeti | 1 | Doğrulanmadı — malzeme ve işlem şartnamesi belirlenmedi | [B] %100 bağıl nem / yoğuşma + [D] | **Doğrulanmadı** | Yoğuşmaya karşı **tek savunmamız budur** (`docs/13` §5). Hangi kaplama malzemesi, hangi kalınlık, hangi kaplama sınıfı ve maskeleme planı (konnektör/anten yüzeyleri) **hiç tanımlanmadı.** IPC-CC-830 adı geçiyor, uygunluk **doğrulanmadı.** |

**Özet:** 17 BOM satırının **17'si de "doğrulanmadı"**. Bu, tasarımın kötü olduğu anlamına gelmez —
**bu oturumda hiçbir üretici veri sayfasına erişilmediği** anlamına gelir. Tabloyu "uygun" diye
doldurmak, doğrulanabilir tek çıktımız olan dürüstlüğü harcamak olurdu.

**Maliyet notu:** `bom.csv` toplam satırı **adet 1'de ~56 USD/kontrolcü kartı, adet 1.000'de
~37 USD/kontrolcü kartı** (**sensör düğümleri S1–S5**, SIM/veri aboneliği ve kurulum işçiliği
**hariç**; BOM yalnızca Pano Beyni kontrolcü kartını kapsar — `docs/10` §2). Yani bu rakam
**pano başına toplam donanım maliyeti değildir**; §3.1'de listelenen kalemlerin hiçbirini içermez.
**Tip test ve sertifikasyon maliyeti de bu rakamın içinde değildir ve bu teslimde
hesaplanmamıştır.**

### 3.1 Bu tablonun kapsamadıkları (BOM'da satırı olmayanlar)

Aşağıdakiler için **BOM satırı yoktur**, dolayısıyla şartname sınırlarına karşı **karşılaştırılamazlar**:

| Kalem | Durum |
|---|---|
| **Kablosuz bağlantı sıcaklık düğümü (S1)** ve ortam düğümü (S3/S4) | `hardware/sensor-dugumu/` dizini **boştur.** Düğüm donanımı bu teslimde tasarlanmadı; `PLAN.md` MoSCoW listesinde **"gerçek sensör" Won't kümesindedir**, düğüm donanımının/BOM'unun kendisi ise **hiçbir MoSCoW kümesinde yer almaz** (`PLAN.md` MoSCoW bölümü, `docs/10` §2). Oysa şartname sınırlarına **en çok maruz kalan parça budur** — bara üzerinde, en sıcak noktada duruyor. Pil/enerji toplama, gövde malzemesi (V-0), yalıtım mesafesi ve sıcaklık sınıfı **tamamen açıktır.** |
| **PD ön uç kartı** | `hardware/pd-karti/` dizini **boştur**; bilinçli kapsam dışı (rapor §3.7, `docs/11`). |
| Montaj malzemesi: kablo, kablo bağı, braket, kelepçe, nem alıcı, TVS bileşenleri | BOM'da **yok.** `docs/08` ve `docs/13` bunlara metin içinde atıf yapıyor ama **parça seçimi yapılmadı** — hepsi V-0 ve sıcaklık sınıfı kontrolü gerektirir. |
| SIM/veri aboneliği, kurulum işçiliği | BOM'da **bilinçli olarak hariç** (bom.csv toplam satırı). |

---

## 4. Sonraki adım — PoC fazının doğrulama listesi

Bu bölüm **bir sonraki fazın işidir**; bu teslimde **hiçbiri yapılmamıştır.**

### 4.1 Önce veri sayfası çekilecek parçalar (öncelik sırasıyla)

| Sıra | Parça | Neden önce bu | Çekilecek bilgi |
|---|---|---|---|
| 1 | **MEAN WELL IRM-10-5** (SMPS) | Şebekeye bağlanan tek parça; hem güvenlik hem ısıl bütçe hem rakım ona bağlı | Sıcaklık aralığı, sıcaklıkla güç düşümü eğrisi, 2000 m rakım düşümü, yalıtım gerilimi ve sertifikaları, tepe akım davranışı |
| 2 | **Eaton HB1840-2R7107-R** (süperkapasitör) | "Son nefes" garantimizin (`docs/13` §2) tek fiziksel dayanağı | Sıcaklık aralığı, kapasite/ESR'nin sıcaklık ve yaşlanmayla değişimi, ömür sonu değerleri |
| 3 | **Quectel EC200A-EU** (modem) | Backhaul'un tamamı buna bağlı; sıcaklıkta işlev kısıtı olabilir | Çalışma ve genişletilmiş sıcaklık aralıkları, hangi aralıkta hangi işlev garanti, bant/operatör onayı |
| 4 | **ESP32-S3-WROOM-1-N8R8** (MCU) | Sınıf yetmezse tüm tasarım değişir | Sıcaklık sınıfı ve varyantlar, flash/PSRAM sıcaklık sınırı |
| 5 | **Fibox ARCA 92/125** (kutu) | V-0 iddiası ve +70 °C hedefi burada sınanır | V-0 sertifikası, sürekli kullanım sıcaklığı, IP sınıfı, harici tip (IP54) muadili |
| 6 | **ADM2587EBRWZ**, **TLP291** (yalıtım elemanları) | `io-tablosu.md`'deki 2500 / 5000 Vrms iddialarının kaynağı | Yalıtım gerilimi ve süresi, sıcaklık aralığı, akım transfer oranının sıcaklıkla düşümü |
| 7 | **Phoenix Contact MC 1.5/2-ST-3.5** (klemens) | 230 VAC girişi bundan geçiyor | Anma gerilimi, kirlilik derecesine göre kaçak yolu, V-0 sınıfı |
| 8 | **W25Q128JVSIQ** (flash) | Sıcaklık **ve** yazma ömrü | Sıcaklık sınıfı, blok silme döngüsü ömrü, veri tutma süresi |
| 9 | ULN2003AN, TLV1117-33, INA226AIDGST, G5LE-1-VD, ATECC608A, nRF52840 modülü | İkinci dalga | Sıcaklık sınıfları, ısı düşümü, (röle için) titreşim ve gövde alev sınıfı |
| 10 | PCB laminatı ve konformal kaplama malzemesi | Henüz **seçilmedi**, satın alma şartnamesi yazılmalı | Laminat sınıfı/cam geçiş sıcaklığı, alev sınıfı, kaplama malzemesi ve kalınlığı |

### 4.2 Tip testi listesi (hiçbiri yapılmadı)

| Test ailesi | Kapsam | Dayanak / neden |
|---|---|---|
| **Ortam — sıcaklık** | Soğuk, kuru sıcaklık, sıcaklık değişimi/döngüsü; sınırlar madde 1.4 Tablo 1 ([A]/[B]) ve `docs/13` §5'teki [C] −25…+70 °C hedefi | `docs/11`'de **IEC 60068-2** serisi listelidir; **alt bölüm numaraları bu oturumda doğrulanmadığı için yazılmamıştır.** Kabul ölçütü: 24 saat ortalaması 35 °C profilinde ve bara yakını en kötü durumda kesintisiz çalışma |
| **Ortam — nem ve yoğuşma** | Nemli ısı (sabit ve döngüsel), yoğuşma sonrası yalıtım direnci | Harici pano +25 °C'de **%100 bağıl nem**; konformal kaplamanın tek savunma olması |
| **Ortam — rakım** | 2000 m eşdeğeri düşük basınç altında yalıtım ve soğutma | Madde 1.4 Tablo 1: rakım ≤ 2000 m |
| **Mekanik — titreşim ve deprem** | Sarsma masasında **yatay 0,5 g / dikey 0,4 g**; DIN ray klipsi ve konnektörlerin kalıcılığı | Madde 1.4 Tablo 1 (harici); `docs/13` §5 |
| **Mekanik — darbe ve montaj** | Kutu montajı, konnektör çekme dayanımı, kapak kapanma açıklığı | `io-tablosu.md` (10 fişli/vidalı konnektör), madde 2.2.6.1 |
| **EMC — bağışıklık** | Elektrostatik boşalma, hızlı geçici rejim (burst), yüzey darbesi (surge), iletilen ve ışınan RF bağışıklığı, **güç frekansı manyetik alan bağışıklığı** | `docs/11`'de **IEC 61000-6-5** listelidir (güç istasyonu/şalt sahası ortamı). Manyetik alan testi bizde özellikle kritik: `docs/13` §3 hesabı **30 cm'de ~1,54 mT**, ≥ 250 mm bandında **~1,5–2 mT** diyor; bu **hesaptır, ölçüm değildir**; kısa devrede ~35 kat artış öngörülüyor |
| **EMC — emisyon** | İletilen ve ışınan emisyon | Aynı; panoda mevcut koruma/ölçü cihazlarını bozmama şartı (GK6: koruma fonksiyonu etkilenmemeli) |
| **Elektriksel — yalıtım** | Dielektrik dayanım ve darbe dayanımı; clearance/creepage ölçümü | Şartnamenin elektriksel değerler bölümü: **Uimp = 8 kV** (rapor §3.1); `docs/13` §4 (IEC 60664-1); `docs/08` kontrol listesindeki "sensör gövdeleri clearance/creepage mesafesini azaltmadı" maddesinin fiziksel karşılığı |
| **Koruma derecesi** | IP2X (dahili) / IP54 (harici) | Madde 2.2.2; IEC 60529 (`docs/11`) |
| **Yanıcılık** | Tüm plastiklerin V-0 belgelenmesi | Madde 2.2.1.xiii; IEC 60695-11-10 (`docs/11`) |
| **Pano düzeyi — sıcaklık artışı** | Cihaz takılmış panoda sıcaklık artışının TS EN 61439-1 sınırlarını **aşmadığının** gösterilmesi | Madde 2.2.3. **Bu, pano üreticisiyle ortak yürütülmesi gereken tek testtir**; ürünümüzü tek başına test etmek yetmez |
| **Saha doğrulaması** | Metal kabin içinde kablosuz menzil/paket kaybı, hücresel sinyal seviyesi, `docs/08` prosedürünün gerçek süresi (hedef ≤ 45 dk) | Pilot fazı; bu teslimde `docs/17` §2'de "simülasyon" olarak işaretli olan her satır |

### 4.3 Belge ve süreç işleri

1. **TEDAŞ-MLZ/2019-064.B tam metninin temini** (ADM/GDZ üzerinden) ve bu dokümanın o metne göre
   yeniden yazılması. Bugün elimizde **yalnızca şartnamenin adı ve konusu** vardır.
2. Varsa **uygunluk/tip onayı süreci** (numune, test raporu, onaylı ürün listesi) için takvim ve
   maliyet çıkarılması — bugün **bilinmiyor**, pilot takvimi için risktir.
3. Pano üreticisiyle **madde 2.2.3** görüşmesi: panoya cihaz eklemenin panonun kendi tasarım
   doğrulamasını etkileyip etkilemediği.
4. **Harici tip pano varyantı** (IP54, −25 °C, kirlilik Düzey III) için ayrı bir BOM türetilmesi —
   bugünkü BOM **yalnızca dahili tip** içindir.
5. Kablosuz sensör düğümü BOM'unun yazılması (`hardware/sensor-dugumu/` bugün **boş**).

---

## 5. Bağlantılı dokümanlar

- [`docs/11-standartlar-uyum.md`](11-standartlar-uyum.md) — standart ve mevzuat tablosu. TEDAŞ-MLZ/2003-06.B
  ve TEDAŞ-MLZ/2019-064.B orada listelidir; **bu doküman o iki satırın arkasını dolduran belgedir.**
  docs/11'in "Kapsanmayan standartlar" bölümündeki *"Sertifikasyon testleri (EMC, ortam) bu teslimde
  yapılmadı"* cümlesinin ayrıntılı karşılığı Bölüm 4.2'dir.
- [`docs/13-donanim-tasarimi.md`](13-donanim-tasarimi.md) — §3 manyetik alan hesabı, §4 yalıtım
  koordinasyonu, §5 çevresel dayanım özeti. Bu dokümandaki **[C] −25…+70 °C** hedefi ve
  **−40…+85 °C endüstriyel sınıf bileşen** hedefi docs/13 §5'ten alınmıştır.
- [`hardware/pano-beyni/bom.csv`](../hardware/pano-beyni/bom.csv) · [`io-tablosu.md`](../hardware/pano-beyni/io-tablosu.md)
  · [`blok-diyagrami.md`](../hardware/pano-beyni/blok-diyagrami.md) — Bölüm 3'ün kaynağı.
- [`docs/08-kurulum-proseduru.md`](08-kurulum-proseduru.md) — madde 5.3 (5 güvenlik kuralı),
  2.2.8.1.iv (anten çıkışı), 2.2.12 (iç ihtiyaç) ve clearance/creepage kuralının saha karşılığı.
- [`docs/17-donanimsiz-dogrulama.md`](17-donanimsiz-dogrulama.md) §6 — bilinçli kapsam sınırlarının
  tek kaynağı. Bu dokümandaki "doğrulanmadı" satırları oradaki *"donanım üretilmedi"* kararının
  doğrudan sonucudur.
