# 13 — Donanım Tasarımı

> **Sahip:** Kişi C · Blok diyagram: `hardware/pano-beyni/blok-diyagrami.md`. I/O: `io-tablosu.md`.
> BOM: `bom.csv`. Yerleşim: `hardware/yerlesim/ek2-14-yerlesim.svg`. Mekanik:
> `hardware/mekanik/din-kutu.scad`.

## 1. Blok diyagram ve I/O

Tam blok diyagram (Mermaid, gerçek parça numaralarıyla) ve tasarım gerekçeleri
[`hardware/pano-beyni/blok-diyagrami.md`](../hardware/pano-beyni/blok-diyagrami.md) dosyasındadır.
16 pinlik I/O listesi (sinyal, yön, seviye, izolasyon) [`io-tablosu.md`](../hardware/pano-beyni/io-tablosu.md)'dedir.
**KiCad şeması yerine bu ikili neden tercih edildi:** bkz. `hardware/pano-beyni/README.md`
(dürüstlük notu — bu ortamda doğrulanamayan bir `.kicad_sch` üretmek yerine).

## 2. Güç bütçesi

Özet tablo `blok-diyagrami.md` §4'te: tipik sürekli tüketim ~0,6 A @ 5V (~3 W), hücresel modem
TX darbelerinde 2 A tepeye çıkabilir (SMPS bu tepeye göre seçildi — MEAN WELL IRM-10-5, 2 A).
Süperkapasitör boyutlandırması: 2× 10 F @ 2,7 V seri (5 F eşdeğer, ~5,4 V), kesinti anında
kontrolcünün "son nefes" mesajını göndermesi için gereken enerji:

```
V_min = 3,2 V  (yedek besleme yolunun varsayılan kesme gerilimi — VARSAYIM, ölçülmedi)
E = 1/2 * C * (V_dolu^2 - V_min^2) = 0,5 * 5 F * (5,4^2 - 3,2^2) V^2 ≈ 47,3 J
Sürekli 0,6 A @ 5V ≈ 3 W tüketimde: t = E / P ≈ 47,3 / 3 ≈ 15,8 saniye
```

15–16 saniye, MQTT bağlantısının kapanmasını algılayıp son bir "besleme kesildi" (`ALM-LASTGASP`)
mesajı yayınlamak için yeterlidir; radyo/hücresel gönderim önceliklendirilir, diğer görevler
(sensör okuma) bu sürede askıya alınır.

**Bu hesabın dürüstlük sınırları (GK10):**

- **Bu bir hesaptır, ölçüm değildir.** Donanım üretilmediği için süperkapasitörlü son nefes
  süresi hiç ölçülmedi. Hesap **yeni ve oda sıcaklığındaki** bir parça varsayar; kapasite ve
  eşdeğer seri direncin sıcaklık/yaşlanma ile değişimi hesaba katılmamıştır
  (`docs/19-tedas-sartname-uyumu.md`, BOM kalem 7). Dönüştürücü verimi ve kaçak akım da
  ihmal edilmiştir; gerçek süre bu değerin **altında** kalır.
- **V_min = 3,2 V bir varsayımdır**, veri sayfasından ya da ölçümden gelmiyor. Bu değer
  değişirse süre de değişir: aynı formülle V_min = 3,0 V için E ≈ 50,4 J ve t ≈ 16,8 s çıkar.
- **`hardware/pano-beyni/blok-diyagrami.md` §4 ile tutarsızlık — açıkça bildiriyoruz.** O tablo
  "kesinti sonrası **≥ 20 s** son nefes" yazıyor; buradaki boyutlandırma bu hedefi
  **karşılamıyor.** 3 W'ta 20 saniye 60 J ister; aynı formülle bu, 5,4 → 3,2 V aralığında
  **≈ 6,3 F** eşdeğer kapasite demektir, bugünkü 5 F değil. Doğru olan bu bölümdeki hesaptır
  (≈15,8 s); `blok-diyagrami.md` §4'teki "≥ 20 s" ifadesi bir **hedef** olarak yazılmıştır ve
  o satır düzeltilmelidir. 20 s gerçekten gerekiyorsa süperkapasitör bankı büyütülmelidir.

## 3. Manyetik alan hesabı (rapor §7.2, §15.1)

1600 kVA, 400 V sistemde nominal akım:

```
I = S / (√3 · U) = 1.600.000 / (1,732 × 400) ≈ 2309 A   (şartname: 2312 A)
```

Tek iletken yaklaşımıyla manyetik alan `B = μ₀·I / (2π·r)`, `μ₀ = 4π×10⁻⁷ H/m`:

| Bara mesafesi (r) | B (2312 A'de) |
|---|---|
| 5 cm | 9,25 mT |
| 10 cm | 4,62 mT |
| 20 cm | 2,31 mT |
| **30 cm** | **1,54 mT** |

**Tasarım kararı:** Pano Beyni kontrolcüsü ana baralardan **≥ 250 mm** (bkz.
`hardware/yerlesim/ek2-14-yerlesim.svg`) yerleştirilir; bu mesafede alan ~1,5–2 mT bandında,
hiçbir Hall sensör veya açık manyetik devreli bileşen kullanılmadığından (I/O tablosunda yalnızca
INA226 tipi shunt-tabanlı ölçüm var) elektroniği etkilemez. Kısa devrede (38 kA etken / 80 kA
tepe) alan geçici olarak ~35 kat artabilir; bu yüzden RS485 hatlarında TVS koruma ve kontrolcü
gövdesinin sabit, sallanmayan montajı şarttır (bkz. `docs/07` satır 1).

## 4. Yalıtım koordinasyonu (clearance/creepage, IEC 60664-1)

Sistem gerilimi 400 V (faz-nötr 231 V), Uimp = 8 kV, kirlilik derecesi II (dahili pano). Bara
üzerine veya yakınına yerleştirilen S1 bağlantı sıcaklık düğümleri için **güçlendirilmiş yalıtım**
sınıfı hedeflenir: minimum hava aralığı (clearance) ve yüzey kaçak yolu (creepage) mesafeleri
IEC 60664-1'in yalıtım koordinasyonu tablolarından okunmalıdır. **Standardın tam metnine bu
teslimde erişilmedi** (`Hackathon Verileri/` içinde yok); bu nedenle madde/tablo numarası
bilinçli olarak yazılmamıştır ve **mesafeler hesaplanmadı/ölçülmedi** — aynı gerekçe
`docs/19-tedas-sartname-uyumu.md`'de de yazılıdır. Sensör gövdesinin bara/pabuç üzerine montajı
**hiçbir şekilde mevcut clearance/creepage mesafesini azaltmamalıdır** (kurulum kontrol listesi,
`docs/08`); bu bir tasarım/kurulum kuralıdır, doğrulanmış bir ölçüm değildir.

## 5. Çevresel dayanım özeti

| Risk | Tasarım önlemi |
|---|---|
| Sıcaklık (−25…+70 °C bara yakını) | **Hedef:** kontrolcü elektroniğinde endüstriyel sınıf (−40…+85 °C) bileşen seçimi; kart konformal kaplamalı. **BOM kalemlerinin sıcaklık sınıfı üretici veri sayfalarından DOĞRULANMADI** (`bom.csv`'de sıcaklık aralığı sütunu yoktur), sıcaklık döngüsü testi yapılmadı, kontrolcünün pano içindeki gerçek yerel sıcaklığı ölçülmedi (`docs/19`) |
| Nem/yoğuşma (harici panoda %100 BN) | Akrilik konformal kaplama (IPC-CC-830), kutu içi nem alıcı |
| Kirlilik (Düzey II–III) | V-0 polikarbonat kutu (`din-kutu.scad`), IP20 dahili |
| Titreşim/deprem (0,5 g) | DIN ray klipsi + kilitli konnektörler (I/O tablosu, tüm konnektörler vidalı/fişli) |
| Yangın dayanımı | **Kutu gövdesi V-0 seçildi** (`bom.csv`: Fibox ARCA 92/125, PC V-0) — BOM'da alev sınıfı yazılı tek kalem budur. Diğer plastik gövdeli parçaların (konnektör, röle, klemens, kablo bağı) alev sınıfı üretici veri sayfasından **DOĞRULANMADI**; malzeme sertifikası toplanmadı, yanma testi (UL94 / IEC 60695-11-10) yapılmadı (`docs/19`). "Pano içine giren tüm plastikler V-0" bir **tasarım kuralıdır**, doğrulanmış bir durum değil |

## 6. Mekanik

DIN ray kutusu parametrik OpenSCAD kaynağı: [`hardware/mekanik/din-kutu.scad`](../hardware/mekanik/din-kutu.scad)
(125×92×60 mm, Fibox ARCA 92/125 sınıfı referans alınarak). **STL bu teslimde üretilmedi** — bu
geliştirme ortamında `openscad` kurulu değildi; dosya, OpenSCAD kurulu bir makinede doğrudan
`openscad -o din-kutu.stl din-kutu.scad` ile STL'e çevrilebilir durumdadır (`STATUS.md` karar #4).

## 7. Kısmi deşarj ve dalga biçimi: bu mimarinin göremedikleri

> Komite dosya paketine iki kısmi deşarj (PD) sensörü veri sayfası koydu; biz PD'yi **bilinçli
> olarak kapsam dışı** bıraktık. Gerekçesi bugüne kadar rapor, `docs/11` ve `docs/05` arasına
> dağılmıştı; bu bölüm onu tek yerde toplar ve üstüne, jüri sormadan, **kendi mimarimizin
> göremediği arıza sınıfını** yazar. Buradaki her sayının yanında kaynağı vardır.

### 7.1 Verilen HFCT veri sayfaları — kendi sayılarıyla

Tablo doğrudan `Hackathon Verileri/DS_HFCT30_eng.pdf` ve `Hackathon Verileri/DS_HFCT50_eng.pdf`
(Techimp) dosyalarından okundu; `HACKATHON_ANALIZ_RAPORU.md` §3.7 tablosuyla **uyumludur**
(birebir kopya değildir: bu tabloya veri sayfasındaki mekanik kotlar ayrıca eklenmiş, delik çapı
ile dış ölçü ayrı satırlara bölünmüş, raporun "uygulama alanları" satırı ise aşağıdaki
**dürüstlük notuna** taşınmıştır — teknik değerler aynıdır).

| Özellik | HFCT 30 mm | HFCT 50 mm |
|---|---|---|
| Bant genişliği | 1–60 MHz | 1–80 MHz (−6 dB) |
| Maks. hassasiyet (Vout/Iin @ 42 MHz, 50 Ω yük) | 17 mV/mA | 17 mV/mA |
| Yük empedansı / çıkış | 50 Ω, BNC koaksiyel | 50 Ω |
| **50 Hz'de çıkış (yüksüz)** | **0,6 Vpp @ 100 A** | veri sayfasında yok |
| **PD frekansında çıkış (yüksüz)** | **0,4 Vpp @ 100 pC** | veri sayfasında yok |
| Delik çapı | Ø30 mm (mekanik çizimde Ø30,5 / 34 mm kotları) | Ø50 mm |
| Dış ölçü | veri sayfasında ayrıca verilmemiş | 111 × 123 × 38 mm |
| Elektriksel yalıtım | 25 kV tepe (1 saat) | veri sayfasında yok |
| Çalışma sıcaklığı | −20…+70 °C | −20…+70 °C |
| Montaj | Test edilen sistemin **topraklama bağlantısına**; ok toprak yönünde → Vout, Iin ile aynı fazda | Topraklama/bonding kablosuna; daha büyük çap özel imalat gerektirir |

**Bu sayılardan çıkan üç mühendislik sonucu:**

1. **Sensör faz iletkenine değil topraklama iletkenine takılır.** Canlı iletkene temas yok, pano içi
   kablo yığınına ek yük yok — retrofit açısından güvenli taraf budur. Ama ölçtüğü şey de topraklama
   akımıdır ve AG panoda o iletken 50 Hz taşır.
2. **"HFCT'yi takıp okuruz" basit değildir.** Aynı veri sayfası, 100 A'lik 50 Hz akım için **0,6 Vpp**,
   100 pC'lik gerçek bir PD darbesi için **0,4 Vpp** veriyor. Yani ham çıkışta şebeke frekansı bileşeni,
   aramaya çalıştığımız PD sinyalinden **daha büyüktür** (iki veri sayfası değerinin doğrudan
   karşılaştırması; bizim ölçümümüz değildir). HFCT30'un frekans tepkisi eğrisi 10 kHz'te ≈ −60 dB ile
   zaten yüksek geçiren davranıyor, buna rağmen 50 Hz'de bu çıkış kalıyor. Ön uçta **yüksek geçiren
   filtre + aşırı gerilim sınırlayıcı zorunlu** olurdu; bu, pasif bir okuma değil ayrı bir analog
   kart tasarımıdır.
3. **400 V'ta sürekli PD aktivitesi tipik olarak raporlanmaz — ama gerekçeyi doğru kurmak gerekir.**
   Sık tekrarlanan "havada Paschen minimumu ≈ **327 V**, dolayısıyla 400 V'ta PD olmaz" kısayolu
   kendi içinde eksiktir: 400 V sistemde faz-faz tepe gerilimi √2 × 400 ≈ **566 V**'tur, yani
   327 V'un **üstündedir**; salt gerilim eşiği bu sonucu vermez. Doğru gerekçe geometriktir:
   Paschen eğrisi gerilimi değil **basınç × boşluk mesafesi** çarpımını sınırlar, ve AG panoda
   beklenen boşluk boyutları ile alan şiddetlerinde tek darbenin taşıdığı enerji, OG/YG'de
   ölçülen türden **sürekli ve yinelenen** bir PD aktivitesi üretecek düzeyde değildir.
   **Bu bir literatür/akıl yürütme kabulüdür** (`HACKATHON_ANALIZ_RAPORU.md` §3.7), **bizim
   ölçümümüz değildir — AG panoda PD ölçümü yapılmadı** ve bu kabul depoda hiçbir veriyle
   sınanmadı. AG panoda baskın arıza mekanizmaları **gevşek/oksitlenmiş bağlantı ısınması, aşırı
   yük, yoğuşma kaynaklı yüzeysel kaçak ve ark**tır — ürünün ölçüm ekseni bu yüzden
   ısıl-elektriksel-çevreseldir. Kabul yanlışsa sonucu §7.3'teki tabloda görünür: PD sütunumuz
   "hiçbir şey"dir.

**Dürüstlük notu:** HFCT30 veri sayfasının "suitable for" listesinde *switchboards* da geçiyor. Liste
gerilim seviyesi ayırmıyor. Bizim gerekçemiz sensörün yapamadığı bir şey değil, **400 V'ta olayın
kendisinin nadir olması**dır; sensör OG/YG bağlamında doğru araçtır.

Bu karar donmuş sözleşmeye de yansımıştır: `contracts/mqtt-telemetry.schema.json` içinde `pd` bloğu
"OG eklentisi (HFCT); AG panoda null" olarak tanımlıdır ve `contracts/alarm-codes.yaml`'daki
`ALM-PD-TREND` (P3) bir OG kodudur — eşiği sözleşmede yoktur
([05-anomali-tespiti.md](05-anomali-tespiti.md) §10).

### 7.2 OG'de ne gerekirdi — ve depoda ne var

PD izleme asıl **OG hücre, trafo ve OG kablo başlıklarında** anlamlıdır. Gerekecek zincir ve bizdeki
gerçek durum:

| Gereken | Neden | Depodaki durum |
|---|---|---|
| HFCT (Ø30 / Ø50), topraklama iletkenine kelepçe | Sinyal alımı | Veri sayfası var, **cihaz temin edilmedi** |
| Pasif yüksek geçiren filtre + aşırı gerilim sınırlayıcı | §7.1 md. 2: 50 Hz bileşenini bastırmak, ön ucu geçici olaylardan korumak | Yalnızca tasarım notu (rapor §3.7) |
| Logaritmik yükselteç + tepe tutucu | PD darbelerinin geniş dinamik aralığı | Yalnızca tasarım notu |
| 50 Hz sıfır geçişine senkronizasyon | Faz çözümlü PD (PRPD) histogramı için faz referansı | **Yok** |
| PD / gürültü ayrımı | Gerçek PD belirli faz aralıklarında kümelenir, gürültü faza düzgün dağılır | **Yok** |
| pC kalibrasyonu (IEC 60270 ailesi) | Genliğin anlamlı olması için | **Yapılmadı**; standart metnine erişilmedi |

**Durum tek cümleyle:** bunların hepsi **tasarım notu düzeyindedir. Donanım üretilmedi, HFCT temin
edilmedi, hiçbir PD ölçümü yapılmadı.** `docs/11-standartlar-uyum.md` PD satırını "Won't" olarak
işaretler; bu bölüm o işareti değiştirmez, gerekçelendirir.

### 7.3 10 saniyelik mimarinin göremedikleri (bu bölümün en önemli parçası)

Ölçüm zincirimiz baştan sona **skalerdir**: kenar 1 s'lik çevrimde işler, merkeze **10 s özet** gider
([02-mimari.md](02-mimari.md), [14-veri-ureteci.md](14-veri-ureteci.md)). 50 Hz'de bir tam periyot
20 ms, yarım periyot 10 ms eder. Yani kenardaki 1 s penceresi yarım periyodun **100 katı**, merkeze
giden 10 s özeti **1000 katı**dır. `contracts/mqtt-telemetry.schema.json` içinde ham örnek dizisi
veya dalga biçimi alanı **yoktur** — saklanan şey RMS/ortalama/maksimum mertebesinde tek sayılardır.

Bunun doğrudan sonucu şudur: **bugünkü mimari seri arkı ve kontak kıvılcımlanmasını fiziksel olarak
göremez.** Sahada yangın/ateşleme önlemede en etkili olduğu bilinen yaklaşım (Texas A&M *Distribution
Fault Anticipation*, Gridware) arıza öncesi imzayı **yarım periyot altı dalga biçiminden** çıkarır
(kaynak: `GELISTIRME-BACKLOGU.md` §2 md. 18). 10 saniyelik RMS bu sınıfı kaçırır. Bu bir ayar veya
eşik meselesi değildir; **örnekleme çözünürlüğünün sınırıdır ve algoritma değiştirilerek kapatılamaz.**

| Olay sınıfı | Gördüğümüz | Görmediğimiz |
|---|---|---|
| Gevşek/oksitlenmiş bağlantı ısınması (yavaş) | Isıl direnç indeksi K/K₀; ölçüldü: S1'de sabit 70 K eşiğinden **209,0 saat (8,7 gün)** önce uyarı (docs/12 §2) | **Ne zaman biteceğini güvenilir söyleyemiyoruz.** `ttl_h` geri testi S1'de: 790 tahminin yalnızca **%5,2'si** ±%20 konisinde, **prognostic horizon yok**, ihlale 48 saatten az kala koni içi oran **%0**, CRA **−5,12** (docs/12 §4, docs/05 §10). 209 saat **tespit** katmanındandır, tahmin değildir |
| Aşırı yük | Görülüyor, ama öne alma yalnızca **1,2 saat** (docs/12 §2) — üstünlük iddiası yok | Kalan ömür kestirimi yok: S2'de `ttl_h` **hiç tahmin üretmedi** (0 tahmin, docs/12 §4) |
| Yoğuşma / yüzeysel kaçak | Çiy noktası marjı eşikleri (docs/05 §6, §11) | — |
| Ark parlaması (arc flash) | TVOC-2 **kendi optik dedektörüyle** tripledikten **sonra** `ALM-ARC-TRIP` (P1, L0) — bu bir **rapordur, tespit değil** | Ark oluşmadan önceki imza |
| **Seri ark / kontak kıvılcımlanması** | **Hiçbir şey** | Yarım periyot altı akım/gerilim imzası |
| **Kısmi deşarj** | **Hiçbir şey** — `pd` bloğu AG'de null, donanım yok (§7.2) | MHz bandı darbe dizisi, PRPD kümelenmesi |

Bu kayıt yeni değil, **birleştirilmiş** bir kayıttır: [05-anomali-tespiti.md](05-anomali-tespiti.md)
§10 algoritmanın bilinen sınırlarını, [12-dogrulama-sonuclari.md](12-dogrulama-sonuclari.md) §4.3
prognozun dürüstlük kayıtlarını (n = 1, güven aralığı yok, S8'de 99 tahminlik prognoz yanlış-alarmı)
zaten açık tutuyor. Aradaki fark şudur: oradakiler **algoritmanın** sınırlarıydı, buradaki
**donanım ve veri mimarisinin** sınırıdır.

**Bunu jüri bulmadan bizim söylememiz gerekir.** Veri şemasını açan biri zaten dalga biçimi alanı
olmadığını görecektir; kapatılmamış bir boşluğu kapatılmış göstermek, ölçülmüş 209 saatlik öne almanın
da inandırıcılığını götürür. Söylemediğimiz tek şey "yapabiliriz"dir.

**Kapanış.** Tetikli dalga biçimi yakalama — bir eşik tetiğinde yarım periyot altı ham örnek
penceresinin yakalanıp saklanması — **bir sonraki donanım revizyonunun konusudur.** Bu teslimde ne
şema, ne kart, ne de bir uygulama önerisi vardır; özellik dondurma sonrası kod yazılmamıştır ve
`contracts/` donmuştur. Bugünkü cevabımız tek cümledir: **bugünkü mimari bu sınıfı göremez.**
