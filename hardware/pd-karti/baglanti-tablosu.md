# PD Kartı — Bağlantı (Net) Tablosu

**Sahip:** Kişi C · **Tarih:** 20 Eylül 2026 · **Sürüm:** v1

> **Kaynak dosyalar (bu dosyadaki her satır bunlardan birine dayanır):**
> [`blok-diyagrami.md`](blok-diyagrami.md), [`io-tablosu.md`](io-tablosu.md),
> [`hf-analog-frontend.md`](hf-analog-frontend.md), [`bom.csv`](bom.csv),
> [`README.md`](README.md) ve karşı taraf için
> [`../pano-beyni/io-tablosu.md`](../pano-beyni/io-tablosu.md),
> [`../pano-beyni/blok-diyagrami.md`](../pano-beyni/blok-diyagrami.md).
> Verilen HFCT veri sayfalarının sayıları için [`../../docs/13-donanim-tasarimi.md`](../../docs/13-donanim-tasarimi.md) §7.1.
> Depo dışı hiçbir kaynak kullanılmamıştır.

---

## 0. Kapsam — bu dosya ne DEĞİLDİR

**Bu bir şematik DEĞİLDİR.** Bir netlist de değildir. Yaptığı tek şey, blok diyagramı ile I/O
tablosuna dağılmış sinyal zincirini tek tabloda toplamak, `hf-analog-frontend.md`'deki filtre ve
dinamik aralık değerlerini o tabloya taşımak ve **hangi bağlantının hâlâ belirsiz olduğunu**
aynı yerde göstermektir.

| Bu dosyada **var** | Bu dosyada **yok** (ve neden) |
|---|---|
| Blok-blok net listesi, sinyal adı, yön, kaynak dosya:satır | **Fiziksel paket pin numarası, paket ölçüleri, mutlak maksimum değerler** — depoda hiçbir bileşenin veri sayfası yok |
| `hf-analog-frontend.md`'deki değerlerin olduğu gibi taşınması | **Yeni filtre hesabı, yeni L/C değeri, yeni kazanç** — bu dosya hiçbir değer türetmedi |
| Konnektör adlandırma çakışmasının kaydı (Bölüm 5) | **Çakışmanın çözümü** — hangi adın doğru olduğu tasarım kararıdır, bu dosyanın işi değil |
| Standardın **adı**, deponun kendi yazdığı biçimiyle: IEC 60270 (`README.md:3`) | **IEC 60270 madde numarası** — standart metnine erişilmedi (`../../docs/13-donanim-tasarimi.md:179`), numara yazmak uydurma olurdu |

> **Pin ve uç adları hakkında:** bu dosyadaki **her işlevsel sinyal/uç adı** (`HF_IN+`, `SPI_CS`,
> `SPI_SCK`, `SPI_MISO`, `TRIG_OUT`, `VREF_SET`, `J1`, `J2-x`) doğrudan `io-tablosu.md`'den
> alınmıştır ve **veri sayfasına karşı DOĞRULANMADI.** Bileşenlerin ayak adları ve numaraları
> bu dosyada hiç yer almaz.

**Doğrulama durumu — tek cümleyle:** bu kart **üretilmedi**, HFCT **temin edilmedi**, AG panoda
**hiçbir PD ölçümü yapılmadı** ve pC kalibrasyonu **yapılmadı**
(`../../docs/13-donanim-tasarimi.md:174,179,181–183`; `../../docs/19-tedas-sartname-uyumu.md:131`).
Kartın kapsam etiketi deponun kendi içinde de tek değildir: `../../docs/10-bom-maliyet-roi.md:11`
"OG+PD" varyantını **"yalnızca tasarım notu — Won't"** diye işaretlerken
`../pano-beyni/README.md` ("Diğer donanım dizinleri" başlığı) bu dizini **"Could seviyesi"** diye anar. Her iki etikette de ortak
olan şey aynıdır: **bu kart bu teslimde üretilmemiştir.** Aşağıdaki "Durum" sütununda
**DOĞRULANMADI** yazan her satır bu cümlenin kapsamındadır.

---

## 1. Sinyal zinciri netleri (HFCT → AFE → sayısallaştırma)

Zincirin sırası `blok-diyagrami.md:18–20,28–30`'dan alınmıştır. Aradaki düğüm adları
(`N_…`) bu dosyada **etiket olarak** verilmiştir; depoda başka bir adları yoktur.

| # | Net | Kaynak (sürücü) | Hedef | Sinyal | Dayanak | Durum |
|---|---|---|---|---|---|---|
| 1 | `HF_IN+` | HFCT sekonderi (kart dışı), J1 SMA üzerinden | Çift yönlü TVS (Semtech RCLAMP0502A) | ±5 V tepe, **50 Ω** empedans | `io-tablosu.md:7`; `blok-diyagrami.md:9,10`; `bom.csv:6,8` | DOĞRULANMADI |
| 2 | `GND_SHIELD` | HFCT koaksiyel blendajı, J1 kasası | Koruyucu şasi topraklaması | 0 V | `io-tablosu.md:8` | Şasi ↔ analog toprak birleşme noktası **yazılı değil** |
| 3 | `N_TVS_OUT` | TVS | Pasif LC bant geçiren filtre (BPF) girişi | HF darbe | `blok-diyagrami.md:18` | DOĞRULANMADI |
| 4 | `N_BPF_OUT` | BPF çıkışı | TI **OPA656U** LNA girişi | 100 kHz – 20 MHz bandı | `blok-diyagrami.md:19`; `bom.csv:2` | DOĞRULANMADI |
| 5 | `N_LNA_OUT` | OPA656U çıkışı | Analog Devices **AD8307ARZ** logaritmik dedektör girişi | Yükseltilmiş HF | `blok-diyagrami.md:20`; `bom.csv:3` | LNA kazancı **hiçbir dosyada yazılı değil** |
| 6 | `N_LOG_ENV` | AD8307 çıkışı ("zarf gerilimi") | TI **ADS7049** 12-bit 2 MSPS SAR ADC analog girişi | Eğim 25 mV/dB | `blok-diyagrami.md:28`; `bom.csv:5`; `hf-analog-frontend.md:31` | DOĞRULANMADI |
| 7 | `N_LOG_PEAK` | AD8307 çıkışı ("hızlı tepe sinyali") | TI **TLV3501** karşılaştırıcı girişi | Lojik darbe tetikleme | `blok-diyagrami.md:24,29`; `bom.csv:4` | Aynı çıkışın iki yükü sürmesi **yük analizi yapılmadan** yazılmış |
| 8 | `N_VTH` | Ayarlanabilir eşik referansı | TLV3501 referans girişi | 0 – 3,3 V | `blok-diyagrami.md:26,30`; `io-tablosu.md:15` | **Kaynağı çelişkili** — bkz. Bölüm 8, satır 3 |

**Kasten yazılmadı:** hangi op-amp/komparatör ayağının evirici, hangisinin evirmeyen giriş olduğu.
OPA656U, AD8307 ve TLV3501'in ayak adları depoda hiçbir yerde geçmiyor.

---

## 2. Filtre ve dinamik aralık — `hf-analog-frontend.md`'den taşınan değerler

Bu tablo **yeni hesap içermez**; her satır kaynağındaki değerin aynısıdır.

| Büyüklük | Değer | Dayanak |
|---|---|---|
| Alt kesim frekansı, `fc,low` | **100 kHz** | `hf-analog-frontend.md:13` |
| Üst kesim frekansı, `fc,high` | **20 MHz** | `hf-analog-frontend.md:14` |
| Filtre topolojisi | 5. derece pasif LC Chebyshev yüksek geçiren + 3. derece alçak geçiren kombinasyonu | `hf-analog-frontend.md:12` |
| 50 Hz bastırma **gereksinimi** | > 80 dB sönümleme | `hf-analog-frontend.md:11`; `blok-diyagrami.md:14,47` |
| 50 Hz'de **hesaplanan** zayıflama | ≈ −100 dB | `hf-analog-frontend.md:16` |
| Bastırılacak gürültü bandı | 0 – 50 kHz (50/150/250 Hz harmonikleri, 2 kHz PWM anahtarlama) | `hf-analog-frontend.md:10`; `blok-diyagrami.md:47` |
| PD darbe genişliği (AFE tasarım noktası) | τ ≈ 5 ns – 40 ns | `hf-analog-frontend.md:27` |
| Algılama aralığı | 20 pC – 5000 pC | `hf-analog-frontend.md:28` |
| AD8307 giriş dinamik aralığı | −75 dBm … +17 dBm (92 dB) | `hf-analog-frontend.md:30`; `blok-diyagrami.md:16` |
| AD8307 eğimi | 25 mV/dB | `hf-analog-frontend.md:31`; `blok-diyagrami.md:48` |
| Doğrusallaştırılmış çıkış | `Vout = 0,025 · (P_dBm + 84)` | `hf-analog-frontend.md:33` |
| OPA656 kazanç bant genişliği | 230 MHz GBW | `blok-diyagrami.md:15`; `bom.csv:2` |
| Filtre bileşenleri | Murata LQW18AN (bobin) + Murata GJM1555C (kapasitör), **6 adet** | `bom.csv:7` |
| Nominal bara akımı (gürültü kaynağı bağlamı) | 1600 A | `hf-analog-frontend.md:18` |

**Bu tablonun boşlukları (hiçbir dosyada yazılı değil):** filtrenin **tekil L ve C değerleri**,
karakteristik empedansı, Chebyshev dalgalanma (ripple) değeri, giriş/çıkış sonlandırması ve
`N_LNA_OUT` üzerindeki kazanç. `bom.csv:7` yalnızca **seri adı** verir, değer vermez.
Bu yüzden bu dosya 100 kHz – 20 MHz bandını **tasarım hedefi** olarak taşır, gerçeklenmiş bir
filtre olarak değil.

---

## 3. Besleme netleri — ve eksik ray

| Net | Kaynak | Hedef(ler) | Seviye | Dayanak | Durum |
|---|---|---|---|---|---|
| `VDD_5V` | Pano Beyni güç katı → J2-1 | OPA656U, AD8307 | +5,0 V DC | `io-tablosu.md:9` | DOĞRULANMADI |
| `GND` | Pano Beyni → J2-2 | Ortak analog ve dijital referans | 0 V | `io-tablosu.md:10` | Analog/dijital toprak ayrımı **yazılı değil** |
| **3,3 V rayı** | — | ADS7049, TLV3501, SPI sürücüleri | — | **Hiçbir dosyada yok** | **AÇIK BOŞLUK** — aşağıya bakınız |

> **Açık boşluk — 3,3 V nereden geliyor?**
> `io-tablosu.md:9` PD kartına giren tek besleme olarak **+5,0 V**'u gösteriyor, ama aynı dosyanın
> 11–15. satırları tüm sayısal sinyalleri **0 – 3,3 V** seviyesinde tanımlıyor ve `bom.csv`'de
> **hiçbir regülatör/LDO kalemi yok.** Kart üstünde 3,3 V üretilmiyorsa bu ray konnektörden
> gelmelidir — Pano Beyni'nin `EXP_CONN` tanımı zaten **"SPI/I2C + 3V3/5V"** diyor
> (`../pano-beyni/io-tablosu.md:23`), ama PD kartının kendi I/O tablosunda **3V3 ucu yoktur.**
> Bu çelişki bu teslimde **çözülmedi.**

> **İkinci açık kalem — tek mi çift besleme?**
> OPA656U ve AD8307'nin tek beslemeli (+5 V) mi yoksa çift beslemeli mi çalıştırılacağı
> **hiçbir dosyada yazılı değildir**; `bom.csv`'de negatif ray üreten bir bileşen yoktur.
> Veri sayfasına karşı **DOĞRULANMADI.**

> **Üçüncü açık kalem — güç bütçesi.**
> PD kartı, Pano Beyni'nin güç bütçesi tablosunda **yer almıyor**
> (`../pano-beyni/blok-diyagrami.md:87–97`; toplam sürekli ~0,6 A @ 5 V ≈ 3 W). Kartın çektiği
> akım hiçbir dosyada yazılı olmadığı için bütçeye eklenemedi.

---

## 4. Pano Beyni arayüz netleri

| PD kartı ucu | Sinyal | Yön (PD kartına göre) | Seviye | Pano Beyni karşılığı | Dayanak |
|---|---|---|---|---|---|
| J2-1 | `VDD_5V` | Giriş | +5,0 V DC | Güç katı / `EXP_CONN` 5 V ucu | `io-tablosu.md:9`; `../pano-beyni/io-tablosu.md:23` |
| J2-2 | `GND` | — | 0 V | Ortak referans | `io-tablosu.md:10` |
| J2-3 | `SPI_CS` | Giriş | 0 – 3,3 V | ESP32-S3 GPIO (aktif düşük) | `io-tablosu.md:11` |
| J2-4 | `SPI_SCK` | Giriş | 0 – 3,3 V | ESP32-S3 SPI CLK, 20 MHz'e kadar | `io-tablosu.md:12` |
| J2-5 | `SPI_MISO` | Çıkış | 0 – 3,3 V | ESP32-S3 SPI MISO | `io-tablosu.md:13` |
| J2-6 | `TRIG_OUT` | Çıkış (push-pull) | 0 – 3,3 V | ESP32-S3 harici kesme | `io-tablosu.md:14`; `blok-diyagrami.md:35,38` |
| J2-7 | `VREF_SET` | Giriş | 0 – 3,3 V | "ESP32-S3 DAC çıkışı" | `io-tablosu.md:15` |

**Bu tablonun sınırları:**

1. **Uç-uç eşleme yoktur.** Pano Beyni tarafında genişleme konnektörü `EXP_CONN (J9.1–10)` olarak
   tanımlı ve "boş bırakılabilir" notuyla yazılmış (`../pano-beyni/io-tablosu.md:23`); **hangi PD
   sinyalinin J9'un kaçıncı ucuna gideceği hiçbir dosyada yazılı değildir.** Bu dosya da yazmıyor —
   yazsaydık uydurmuş olurduk.
2. **MOSI yoktur.** `blok-diyagrami.md:37` ve `io-tablosu.md:13` ADC'yi yalnızca `MISO` üzerinden
   okunur gösteriyor. ADS7049'un yapılandırma yazması gerekip gerekmediği **veri sayfasına karşı
   DOĞRULANMADI**; gerekiyorsa konnektöre bir uç daha eklenmesi gerekir.
3. **`VREF_SET`'in karşı tarafı belirsiz.** `io-tablosu.md:15` bunu "ESP32-S3 DAC Çıkışı" diye
   tanımlıyor; Pano Beyni'nin MCU'sunda kullanılabilir bir analog çıkış olup olmadığı
   **veri sayfasına karşı DOĞRULANMADI.** Yoksa PWM + RC süzme veya kart üstü bir DAC gerekir —
   ikisi de `bom.csv`'de yoktur.
4. **Tetikleme gecikmesi ölçülmedi.** `io-tablosu.md:14` ve `blok-diyagrami.md:35` "< 10 ns
   gecikme" diyor; bu bir **ölçüm değildir.** `blok-diyagrami.md:49` aynı olayı "mikrosaniyeden
   kısa" diye tarif ediyor — iki ifade birbirini yalanlamıyor, ama aralarında **100 kattan fazla**
   bir kesinlik farkı var ve hangisinin tasarım gereksinimi olduğu belirsiz
   (bkz. Bölüm 8, satır 6).

---

## 5. Konnektör adlandırma çakışması (çözülmedi, kaydedildi)

| Kaynak | Ne diyor |
|---|---|
| `blok-diyagrami.md:33` | Pano Beyni bağlantısı **"J10 Klemens"** |
| `io-tablosu.md:9–15` | Uçlar **J2-1 … J2-7** — yani **7 sinyal** |
| `bom.csv:9` | Phoenix Contact MC 1.5/4-ST-3.5 — **4 kutuplu** klemens |
| `../pano-beyni/io-tablosu.md:23` | Karşı taraftaki genişleme konnektörü **`EXP_CONN (J9.1–10)`** |
| `../pano-beyni/io-tablosu.md:24` | Pano Beyni'nin **J10**'u **DEBUG** portudur ve *"üretimde lehim köprüsüyle devre dışı"* bırakılır |

**İki ayrı sorun:**

* **Ad çakışması:** aynı arayüz üç farklı adla anılıyor (J10 / J2 / J9). Üstelik `blok-diyagrami.md`'nin
  seçtiği **J10**, Pano Beyni tarafında **üretimde kapatılan hata ayıklama portunun adıdır** —
  aynı kartta iki farklı şeye aynı ad verilmiş olur.
* **Kutup sayısı:** I/O tablosu **7 sinyal** sayıyor, BOM **4 kutuplu** bir klemens satın alıyor.
  En az üç kutup eksiktir (veya bazı sinyaller kaldırılmalıdır).

Bu dosya bir ad **seçmez**; seçim bir tasarım kararıdır ve üç dosyanın birlikte düzeltilmesini
gerektirir.

---

## 6. HFCT — kartın dışındaki parça

| Gerçek | Dayanak |
|---|---|
| `bom.csv`'de **HFCT kalemi yoktur** (9 satır kalemi); sensör karta **J1 SMA** üzerinden dışarıdan bağlanır | `bom.csv`; `io-tablosu.md:7`; `bom.csv:8` |
| `blok-diyagrami.md:8` "TDK B64290 Nüve, 100 kHz – 20 MHz" der — bu bir **nüve** referansıdır, tamamlanmış bir HFCT parça numarası değildir. Sarım oranı, sekonder yük direnci ve mV/mA hassasiyeti **hiçbir dosyada yoktur** | `blok-diyagrami.md:8` |
| Komitenin verdiği **gerçek** HFCT veri sayfaları (Techimp HFCT30 / HFCT50) bandı **1–60 MHz** ve **1–80 MHz (−6 dB)** verir | `../../docs/13-donanim-tasarimi.md:118` |
| Aynı veri sayfaları: 50 Hz'de **0,6 Vpp @ 100 A**, PD frekansında **0,4 Vpp @ 100 pC** (yüksüz) | `../../docs/13-donanim-tasarimi.md:121,122` |
| HFCT **faz iletkenine değil topraklama iletkenine** takılır | `../../docs/13-donanim-tasarimi.md:127` |
| HFCT cihazı **temin edilmedi** | `../../docs/13-donanim-tasarimi.md:174` |

> **Bu bölümün en önemli satırı:** bu kartın alt kesim frekansı **100 kHz**
> (`hf-analog-frontend.md:13`), ama depodaki iki gerçek HFCT veri sayfasının alt bant sınırı
> **1 MHz**'tir (`../../docs/13-donanim-tasarimi.md:118`). Yani AFE'nin 100 kHz – 1 MHz aralığı,
> eldeki sensörlerin belirtilmiş bandının **dışındadır**. Hangi HFCT ile çalışılacağı
> **seçilmemiştir** ve bu seçim yapılmadan filtre bandı kesinleşmez.

---

## 7. Bu tabloda KASTEN yazılmayanlar

| Yazılmayan | Neden |
|---|---|
| Fiziksel paket pin numaraları, paket ölçüleri, mutlak maksimum değerler, besleme sınırları | Depoda **hiçbir bileşenin veri sayfası yok** |
| **IEC 60270 madde numarası** | Standart metnine **erişilmedi** (`../../docs/13-donanim-tasarimi.md:179`). Standardın yalnızca **adı** yazılır |
| **pC ↔ mV kalibrasyon katsayısı** | Kalibrasyon **yapılmadı** (`../../docs/13-donanim-tasarimi.md:179`); katsayı yazmak olmayan bir ölçümü var göstermek olurdu |
| Filtre L/C değerleri, dalgalanma, karakteristik empedans | `bom.csv:7` yalnızca seri adı verir; değer uydurmak yerine Bölüm 2'de boşluk olarak kaydedildi |
| 50 Ω kontrollü empedans **yığını** (katman kalınlıkları, hat genişliği) | `bom.csv:10` yalnızca "4 katmanlı empedans kontrollü (50 ohm) PCB" der; yığın hiçbir dosyada yok |
| **ADC giriş aralığı ile AD8307 çıkış aralığının uyumu** | Bu teslimde **hesaplanmadı**; hesaplamak yeni sayı üretmek olurdu |
| 50 Hz sıfır geçişi / faz referansı (PRPD için) | Depoda **yok** olarak zaten kayıtlı (`../../docs/13-donanim-tasarimi.md:177,178`); bu kartta da bir net karşılığı yoktur |

---

## 8. Depo içi çelişkiler — bu dosya çözmez, kaydeder

| # | Çelişki | A diyor ki | B diyor ki | Durum |
|---|---|---|---|---|
| 1 | **Algılama aralığı** | `blok-diyagrami.md:48`: **10 pC – 10.000 pC** | `hf-analog-frontend.md:28`: **20 pC – 5000 pC** | İki dosya iki farklı dinamik aralık veriyor; hangisinin AFE tasarım noktası olduğu belirsiz |
| 2 | **Darbe genişliği** | `blok-diyagrami.md:46`: **1 ns – 50 ns** | `hf-analog-frontend.md:27`: **5 ns – 40 ns**; `hf-analog-frontend.md:42`: **< 50 ns** | Üç farklı aralık. En kısa darbenin 1 ns mi 5 ns mi olduğu, filtrenin üst kesim frekansı seçimini doğrudan etkiler; tasarım noktası **seçilmemiştir** |
| 3 | **Eşik DAC'ı nerede?** | `blok-diyagrami.md:26` eşik referansını **kart üzerindeki** bir `DAC_REF` bloğu olarak çiziyor | `io-tablosu.md:15` aynı sinyali **Pano Beyni'nin DAC çıkışından** gelen bir giriş olarak tanımlıyor | `bom.csv`'de **DAC kalemi yok** → blok diyagramındaki blok bir karşılığa sahip değil |
| 4 | **Konnektör adı** | `blok-diyagrami.md:33`: **J10** | `io-tablosu.md:9–15`: **J2**; `../pano-beyni/io-tablosu.md:23`: **J9** (ve `:24`'te J10 = DEBUG) | Bölüm 5 |
| 5 | **Kutup sayısı** | `io-tablosu.md:9–15`: **7 sinyal** | `bom.csv:9`: **4 kutuplu** klemens | En az 3 kutup eksik |
| 6 | **Tetikleme gecikmesi** | `io-tablosu.md:14` ve `blok-diyagrami.md:35`: **< 10 ns** uçtan uca | `blok-diyagrami.md:24` ve `bom.csv:4`: karşılaştırıcı için anılan gecikme **4,5 ns**; `blok-diyagrami.md:49`: "mikrosaniyeden kısa" | "< 10 ns" **ölçülmedi.** Karşılaştırıcının 4,5 ns'inin üstüne konnektör, klemens ve hat gecikmesi eklendiğinde bütçenin tutup tutmadığı **hesaplanmadı**; ayrıca aynı olay için iki farklı kesinlik iddia ediliyor |
| 7 | **SPI hızı** | `blok-diyagrami.md:34` ve `io-tablosu.md:12`: **20 MHz** SPI | `bom.csv:5`: ADC **2 MSPS** | 20 MHz saatin gerekip gerekmediği ve Pano Beyni tarafının destekleyip desteklemediği **hiçbir yerde yazılı değil** |
| 8 | **TVS adedi** | `blok-diyagrami.md:9` tek bir TVS bloğu çiziyor | `bom.csv:6` **2 adet** RCLAMP0502A listeliyor | İkinci TVS'in hangi net üzerinde olduğu yazılı değil |
| 9 | **3,3 V rayı** | `io-tablosu.md:11–15` sayısal sinyalleri 0 – 3,3 V tanımlıyor | `io-tablosu.md:9` tek besleme olarak +5,0 V veriyor; `bom.csv`'de regülatör yok | Bölüm 3 — **açık boşluk** |
| 10 | **Filtre topolojisi ifadesi** | `blok-diyagrami.md:14`: "Pasif LC **5. Derece Bant Geçiren** Filtre" | `hf-analog-frontend.md:12`: "**5. derece** yüksek geçiren **+ 3. derece** alçak geçiren **kombinasyonu**" | Toplam derece ve dolayısıyla bileşen sayısı belirsiz; `bom.csv:7`'deki 6 adetlik LC grubunun hangisine yettiği kontrol edilmedi |

---

## 9. Layout öncesi doğrulanması gerekenler

Aşağıdakilerin **hiçbiri bu teslimde yapılmamıştır.**

1. **HFCT seçimi önce yapılmalı.** Techimp HFCT30/HFCT50 mi, `blok-diyagrami.md:8`'deki nüve ile
   özel sarım mı? Sensörün bandı (`../../docs/13-donanim-tasarimi.md:118`) seçilmeden AFE'nin
   100 kHz alt kesimi (Bölüm 6) savunulamaz.
2. **Veri sayfalarının temini.** OPA656U, AD8307ARZ, TLV3501AIDBVR, ADS7049QDCURQ1,
   RCLAMP0502A için veri sayfası çekilmeli; Bölüm 1'deki tüm blok-blok bağlantıları ayak
   düzeyinde doğrulanmalı. Fiziksel pin numaraları ancak bu adımdan sonra yazılabilir.
3. **Besleme mimarisi kapatılmalı:** 3,3 V rayının kaynağı (Bölüm 3), tek/çift besleme kararı ve
   PD kartının akımının Pano Beyni güç bütçesine (`../pano-beyni/blok-diyagrami.md:87–97`) eklenmesi.
4. **Filtre gerçeklenmeli.** 5. derece Chebyshev'in L/C değerleri, dalgalanması ve sonlandırması
   çıkarılmalı; `bom.csv:7`'deki 6 adetlik LC grubunun yeterliliği kontrol edilmeli.
   `hf-analog-frontend.md:16`'daki ≈ −100 dB **bir hesaptır**, ölçüm değildir — prototipte
   ağ analizörüyle doğrulanmalıdır.
5. **Zincir seviye planı (level plan) çıkarılmalı.** LNA kazancı, AD8307 giriş seviyesi ve ADC
   giriş aralığı uçtan uca eşleştirilmeli; `hf-analog-frontend.md:33`'teki çıkış formülü ile
   ADC'nin referansı örtüşüyor mu kontrol edilmeli (**bu teslimde hesaplanmadı**).
6. **Eşik referansının kaynağı kararlaştırılmalı** (Bölüm 8, satır 3) ve gerekirse BOM'a
   DAC veya RC süzme kalemi eklenmeli.
7. **Konnektör adı, kutup sayısı ve uç-uç eşlemesi** üç dosyada birden düzeltilmeli
   (Bölüm 5); Pano Beyni'nin `EXP_CONN (J9.1–10)` uçlarına eşleme yazılmalı.
8. **Toprak mimarisi.** Şasi (`GND_SHIELD`) ile analog toprağın nerede ve nasıl birleşeceği,
   50 Ω kontrollü hat yığını ve blendaj stratejisi belirlenmeli (`bom.csv:10` yalnızca
   "empedans kontrollü" der).
9. **pC kalibrasyonu.** IEC 60270 ailesinin isteyeceği kalibrasyon **yapılmadı**
   (`../../docs/13-donanim-tasarimi.md:179`); standardın tam metni temin edilmeden bu kartın
   çıktısı pC cinsinden **raporlanamaz**.
10. **Tetikleme gecikmesinin ölçülmesi** (Bölüm 8, satır 6) — "< 10 ns" iddiası bir osiloskopla
    sınanmadan bırakılmamalıdır.
11. **Bölüm 8'deki on çelişkinin kapatılması** — özellikle 1, 2 ve 10, çünkü bunlar doğrudan
    filtre ve dinamik aralık tasarımını değiştirir.
12. **Kapsam kararının gözden geçirilmesi.** Kart hâlâ OG eklentisidir ve AG panoda PD ölçümü
    yapılmamıştır (`../../docs/13-donanim-tasarimi.md:181–183`); layout'a geçmeden önce bu
    kararın hâlâ geçerli olduğu teyit edilmelidir.

---

## 10. Değişiklik günlüğü

| Tarih | Değişiklik |
|---|---|
| 20 Eylül 2026 | İlk sürüm. Sinyal zinciri, besleme ve Pano Beyni arayüzü tek tabloya toplandı; `hf-analog-frontend.md`'deki filtre ve dinamik aralık değerleri **olduğu gibi** taşındı; on depo içi çelişki ve on iki açık doğrulama kalemi kaydedildi. **Hiçbir yeni sayı, pin numarası veya standart madde numarası üretilmedi.** |
