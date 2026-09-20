# Pano Beyni — Bağlantı (Net) Tablosu (v1)

> **Sahip:** Kişi C · **Tarih:** 20 Eylül 2026 · **Kaynaklar:** [`blok-diyagrami.md`](blok-diyagrami.md),
> [`io-tablosu.md`](io-tablosu.md), [`bom.csv`](bom.csv), `docs/13-donanim-tasarimi.md`,
> `docs/19-tedas-sartname-uyumu.md` §3.
>
> Bu dosya `io-tablosu.md`'nin **dışa bakan** 16 arayüzünü, kart **içindeki** netlerle birleştirir:
> hangi işlevsel uç hangi işlevsel uca bağlanır, sinyal hangi seviyede, net hangi izolasyon
> alanında durur ve hangi sınırı geçer.

---

## 0. Bu dosya bir ŞEMATİK DEĞİLDİR

Depoda `.kicad_sch` **yoktur** ve bu bilinçli bir karardır; gerekçesi [`README.md`](README.md)
satır 11–29'da ve [`blok-diyagrami.md`](blok-diyagrami.md) satır 6–12'de yazılıdır (bu ortamda
internet erişimi ve kurulu KiCad yoktu; doğrulanamayan bir şema dosyası "sahte şema" izlenimi
bırakırdı). **Bu dosya o kararı çürütmez, üzerine inşa eder:** bir şemanın taşıdığı asıl bilgi
net listesidir, çizim değil. Aşağıdaki tablolar o net listesidir.

### 0.1 Bu dosya NEYİ taşır

| Taşıdığı | Nerede |
|---|---|
| Net listesi — her netin kaynağı, hedefleri, işlevsel uç adlarıyla | §3 |
| Sinyal seviyeleri (230 VAC / 24 V / 5 V / 3V3 / RS485 diferansiyel / RF) | §3, "Seviye" sütunu |
| İzolasyon alanları ve netlerin hangi sınırı geçtiği | §2, §3 "İzolasyon sınırı" sütunu |
| Topoloji kuralları (sonlandırma, serbest dolaşım yolu, AT sekonderinin açılmaması) | §3.2, §3.8, §3.10 |
| J1–J10 konnektörleriyle çapraz referans | §4 |
| Bu tabloyu kurarken ortaya çıkan **tutarsızlıklar ve boşluklar** | §5 |
| Layout öncesi veri sayfasından doğrulanması gerekenler | §6 |

### 0.2 Bu dosya NEYİ taşımaz

| Taşımadığı | Neden |
|---|---|
| **Fiziksel pin numaraları** (paket üzerindeki bacak numarası) | §0.3 |
| Bileşen paketleri / footprint'ler | Veri sayfası yok; paket boyutu ve pad geometrisi oradan gelir |
| Katman yığını (stack-up), bakır kalınlığı, dielektrik | `bom.csv` satır 17 yalnızca "4 katmanlı PCB" der; laminat sınıfı ve yüzey işlemi **tanımlanmamıştır** (`docs/19` satır 105) |
| Empedans kontrollü iz, iz genişliği, diferansiyel çift kotları | Stack-up olmadan hesaplanamaz |
| Clearance / creepage **ölçüleri** | `docs/13` §4: IEC 60664-1 tam metnine erişilmedi, mesafeler **hesaplanmadı/ölçülmedi** |
| Gerber / ODB++ / montaj dosyaları, yerleşim (placement) | Kart çizilmedi |
| Pasif bileşen **değerleri** (direnç/kondansatör) | §5 md. 6; değerlerin çoğu veri sayfası parametresi ister |
| Tam referans tanımlayıcı (designator) listesi | Bu dosyada yalnızca netleri anlatmaya yetecek kadar sembolik ad kullanılır (`RT1`, `R_OPTO1`, `R_BURDEN1`, `D_ORING`, `U_LVL`, `SB_TXD`) |
| Herhangi bir **ölçüm** | Kart üretilmedi. Burada hiçbir net süreklilik, izolasyon ya da sinyal bütünlüğü testinden geçmemiştir |

### 0.3 Fiziksel pin numaraları neden YAZILMADI

Bu geliştirme ortamında **hiçbir üretici veri sayfasına erişilmedi** — `docs/19` satır 83–86'daki
aynı kayıt. Depoda parça **numaraları** var (`bom.csv`, 17 satır kalem, gerçek üretici kodlarıyla),
parça **veri sayfaları** yok.

Uydurulmuş bir pin numarasının özelliği şudur: **yanlış olduğu okurken belli olmaz.** "ESP32-S3
pin 14" gibi bir satır, tabloda diğerleriyle aynı biçimde durur, gözden geçirmeden geçer ve
layout aşamasında sessizce yanlış bir karta döner. Yanlış bir *metin* düzeltilir; yanlış bir
*pin ataması* üretilmiş karttır.

Bu yüzden bu dosyada yalnızca **işlevsel uç adları** kullanılır (`U0TXD`, `DE`/`RE`, `SDA`/`SCL`,
`IN`/`OUT`, `A`/`B` gibi) ve **tüm işlevsel uç adları veri sayfasına karşı DOĞRULANMADI.** Uç
adının bile yanlış olabileceği yerler §6 kontrol listesinde tek tek işaretlidir.

Pin ataması bir **layout kararıdır** ve bu teslimin dışındadır. ESP32-S3 tarafında ek bir sebep
daha var: modülün çevre birimlerinin hangi bacaklara yönlendirilebildiği (GPIO matrisi) ve
hangilerinin modül içi flash/PSRAM tarafından rezerve edildiği veri sayfasından okunmadan
belirlenemez — §6 satır 1 ve 3.

---

## 1. Okuma kuralları

**Gösterim.** `Bileşen.UÇ_ADI` — örn. `TLV1117-33.OUT`. Birden çok aynı parça varsa `#n` ile
ayrılır: `ADM2587E#1`, `INA226#2`. Depoda parça karşılığı **olmayan** elemanlar sembolik adla
yazılır ve **değerleri/parça numaraları yoktur**: `R_`/`RT` (direnç), `D_` (diyot), `U_` (entegre),
`SB_` (lehim köprüsü). Bu adların hepsi §5 md. 6'nın kapsamındadır — BOM'da satırları yoktur.

**Konnektör atıfları.** `io-tablosu.md`'ye atıflar o tablonun **`#` sütunundaki satır numarasıyla**
yapılır — depodaki yerleşik kullanım budur (`docs/19` satır 61, 66; `docs/11` satır 17).
Konnektör uçları yalnızca `io-tablosu.md`'nin verdiği **aralık** olarak yazılır (`J7.1–2` gibi);
aralık **içindeki** kutup sırası (hangi ucun L, hangisinin N olduğu) depoda tanımlı **değildir** ve
bu dosya da belirlemez — o bir mekanik/layout kararıdır.

**Dayanak etiketleri** ("Not" sütununda):

| Etiket | Anlamı |
|---|---|
| `[io-N]` | `io-tablosu.md` satır N'de karşılığı var |
| `[blok:L]` | `blok-diyagrami.md` dosya satırı L'de karşılığı var |
| `[bom:L]` | `bom.csv` dosya satırı L'de karşılığı var |
| `[YENİ]` | **Depoda dayanağı yok.** Bu dosyada ilk kez yazılıyor, bir tasarım **önerisidir**, doğrulanmamıştır |
| `[AÇIK]` | Depoda **çelişki ya da boşluk** var; §5'te numaralı madde olarak açılmıştır |

**Bu dosya `io-tablosu.md` ile çelişmez.** Çelişki bulunan tek yer `hardware/pd-karti/` tarafıdır
ve §5 md. 8'de işaretlenmiştir — burada **`io-tablosu.md` esas alınmıştır**.

---

## 2. İzolasyon alanları

Her net tam olarak bir alanda durur; alanlar arasında geçiş yalnızca aşağıdaki sınır elemanlarından
olur. Yalıtım gerilimi değerleri `io-tablosu.md` "Yalıtım koordinasyonu özeti" tablosundan aynen
alınmıştır ve o tablonun kendi uyarısı burada da geçerlidir: **bu değerler aktarılmış veri sayfası
iddialarıdır, teyit edilmemiştir** (`docs/19` satır 93, 101).

| Alan | Kapsadığı | Bu alana geçişi sağlayan eleman | Anma yalıtımı (aktarılmış iddia) |
|---|---|---|---|
| `D0-ŞEBEKE` | 230 VAC L/N, J1, SMPS birincil tarafı | — (kartın dış sınırı) | — |
| `D1-KART` | 5 V, 3V3, GND ve tüm mantık netleri; MCU, flash, güvenli eleman, INA226'lar, ULN2003AN girişleri, röle **bobinleri**, J2, J9, J10 | `IRM-10-5` (ana izolasyon) | 3000 Vrms, `D0`↔`D1` |
| `D2-485A` | RS485 #1 saha tarafı: `485A_A`, `485A_B`, `485A_GND_ISO`, J3 | `ADM2587E#1` (izoleli transceiver + izoleli DC/DC) | 2500 Vrms / 1 dk, `D1`↔`D2` |
| `D3-485B` | RS485 #2 saha tarafı: `485B_A`, `485B_B`, `485B_GND_ISO`, J4 | `ADM2587E#2` | 2500 Vrms / 1 dk, `D1`↔`D3` |
| `D4-OPTO1…4` | Her optokuplör girişinin **saha ilmeği** (4 ayrı alan), J7 | `TLP291#1…#4` | 5000 Vrms, `D1`↔`D4n` |
| `D5-KONTAK1/2` | Röle **kontak** tarafı (kuru kontak), J6 | `G5LE-1-VD` röle kontak–bobin ayrımı | `io-tablosu.md` satır 8–9: "röle bobini galvanik ayrık"; **sayısal anma değeri depoda yok** |
| `D6-AT` | Akım trafosu çekirdeği ve sekonderi, J8 | Ayrık çekirdekli AT (galvanik temassız) | `io-tablosu.md`: "galvanik temassız" |
| `PE` | `DIN_GND`, koruma toprağı | DIN rayı → pano PE | — |

**Dört ayrı opto alanı neden?** `io-tablosu.md` satır 10 ve 11, J7'de her kanala **ikişer uç**
ayırır (J7.1–2 = kanal 1; J7.3–8 = kanal 2–4). Yani her kanalın kendi saha ilmeği vardır ve ortak
bir saha dönüşü **varsayılmamıştır**. Ortak dönüş istenirse bu bir tasarım değişikliğidir: dört
ayrı izolasyon alanı tek alana iner ve `io-tablosu.md` satır 10–11'in kutup dağılımı değişir.

---

## 3. Net listesi

### 3.1 Güç ağacı

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `MAINS_L` | J1.1–2 (iç ihtiyaç devresi, sigortalı fişli klemens) | `IRM-10-5.L` | 230 VAC | `D0` | `[io-1]` · Besleme yeni hat çekilmeden iç ihtiyaç devresinden alınır (`docs/08` §2 md. 1) |
| `MAINS_N` | J1.1–2 | `IRM-10-5.N` | 230 VAC | `D0` | `[io-1]` · J1 içinde L/N kutup sırası depoda tanımlı değil (§1) |
| `+5V` | `IRM-10-5.+Vo` | `TLV1117-33.IN`, `D_ORING` (süperkapasitör kolu), J2.1–4 (5 V), J9.1–10 (5 V), hücresel modem besleme yolu `[AÇIK]` | 5 V DC | `D1` | `[io-2]` `[blok:19]` `[bom:6]` |
| `GND` | `IRM-10-5.−Vo` | Kart ortak referansı: `MCU.GND`, `TLV1117-33.GND`, `ADM2587E#1/#2.GND1`, `ATECC608A.GND`, `W25Q128JVSIQ.GND`, `INA226#1–3.GND`, `ULN2003AN.GND`, `TLP291#1–4.emiter`, J2, J9, J10 | 0 V | `D1` referansı | `[io-2]` · `GND` ile `DIN_GND` arasındaki bağ (doğrudan / kondansatörlü / hiç) depoda **tanımlı değil** — §5 md. 7 |
| `+3V3` (ADM2587E `VDD1` dâhil — `blok-diyagrami.md:62` `V33 --> RS485`; transceiver besleme aralığı veri sayfasına karşı **DOĞRULANMADI**, §6) | `TLV1117-33.OUT` | `MCU.3V3`, `ATECC608A.VCC`, `W25Q128JVSIQ.VCC`, `INA226#1–3.VS`, radyo modülü besleme ucu, J2.1–4 (3V3), J9.1–10 (3V3) | 3,3 V DC | `D1` | `[io-2]` `[blok:21,61-64]` `[bom:7]` |
| `VCAP_BANK` | `SUPERCAP#1.+` (seri bankın üst ucu) | `D_ORING` üzerinden `+5V` | ~5,4 V dolu (`docs/13` §2) | `D1` | `[blok:20,22]` · **`D_ORING` (ORing/ayırma elemanı) ve şarj akımı sınırlama `bom.csv`'de YOK** — §5 md. 2 |
| `VCAP_MID` | `SUPERCAP#1.−` / `SUPERCAP#2.+` orta nokta | Gerilim dengeleme elemanı (**seçilmedi**) | ~2,7 V | `D1` | `[YENİ]` `[AÇIK]` · Seri bağlı iki süperkapasitörde dengeleme depoda hiç ele alınmamış — §5 md. 2 |
| `VCAP_GND` | `SUPERCAP#2.−` | `GND` | 0 V | `D1` | `[blok:20]` |
| `V_COIL` | **Kaynağı belirsiz** — kartta 24 V rayı yok | `G5LE#1.bobin+`, `G5LE#2.bobin+`, `ULN2003AN.COM` | 24 V DC (`blok-diyagrami.md` satır 96) | `D1` | `[AÇIK]` · **En ağır açık madde** — §5 md. 3 |
| `DIN_GND` | DIN rayı → pano PE | Kutu/şasi bağlantı ucu | Koruma toprağı | `PE` | `[io-16]` · Kutu polikarbonattır (`bom.csv` satır 16), yani **bağlanacak metalik gövde yoktur** — §5 md. 7 |

**Süperkapasitör kolu hakkında.** "Son nefes" süresi hesabı `docs/13` §2'dedir (~15,8 s) ve o
bölüm kendi içinde `blok-diyagrami.md` §4'teki "≥ 20 s" hedefiyle **tutarsız olduğunu açıkça
yazar** (`docs/13` satır 41–46). Bu dosya o tartışmayı **tekrarlamaz ve çözmez**; yalnızca şunu
ekler: hesabın varsaydığı yedekleme yolunu kuran elemanlar (ORing, şarj sınırlama, dengeleme)
**net olarak burada görünüyor ama BOM'da satır kalemi olarak yok**.

---

### 3.2 RS485 #1 — master (MPR-53CS + TVOC-2 hattı)

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `485A_TXD` | `MCU.UART[485A].TXD` | `ADM2587E#1.TxD` | 3,3 V CMOS | `D1` | `[blok:34,37]` · MCU tarafı UART **tahsisi depoda yok** — §5 md. 1 |
| `485A_RXD` | `ADM2587E#1.RxD` | `MCU.UART[485A].RXD` | 3,3 V CMOS | `D1` | `[blok:34,37]` |
| `485A_DE_RE` | `MCU.GPIO` (yön kontrolü) | `ADM2587E#1.DE` **ve** `ADM2587E#1.RE` (birlikte sürülür) | 3,3 V CMOS | `D1` | `[YENİ]` · Yarım çift yönlü sürüş: tek hat hem sürücüyü açar hem alıcıyı kapatır. Yön dönüş zamanlaması Modbus RTU'da kritiktir (standart adı: *Modbus over Serial Line v1.02*, `docs/11` satır 16 — **madde numarası verilmiyor**, standardın metnine erişilmedi) |
| `485A_A` | `ADM2587E#1.A` | J3.1–3 (saha), `RT1` sonlandırma kolu, TVS `[AÇIK]` | RS485 diferansiyel | `D2` | `[io-3]` |
| `485A_B` | `ADM2587E#1.B` | J3.1–3, `RT1`, TVS `[AÇIK]` | RS485 diferansiyel | `D2` | `[io-3]` |
| `485A_GND_ISO` | `ADM2587E#1.GND2` (izole taraf referansı) | J3.1–3 (GND ucu) | İzole referans | `D2` | `[io-3]` — satır "A/B/GND" der |
| `485A_TERM` | `RT1` anahtarı (DIP/jumper, **seçilmedi**) | `485A_A` ↔ `485A_B` arasına 120 Ω | — | `D2` | `[io-3]` · io satırı "120 Ω sonlandırma anahtarlı" der; **120 Ω direnç ve anahtar `bom.csv`'de satır kalemi olarak YOK** — §5 md. 6 |

### 3.3 RS485 #2 — slave (RTU/SCADA'ya harita sunar)

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `485B_TXD` | `MCU.UART[485B].TXD` | `ADM2587E#2.TxD` | 3,3 V CMOS | `D1` | `[blok:35,38]` · §5 md. 1 |
| `485B_RXD` | `ADM2587E#2.RxD` | `MCU.UART[485B].RXD` | 3,3 V CMOS | `D1` | `[blok:35,38]` |
| `485B_DE_RE` | `MCU.GPIO` | `ADM2587E#2.DE` + `ADM2587E#2.RE` | 3,3 V CMOS | `D1` | `[YENİ]` |
| `485B_A` | `ADM2587E#2.A` | J4.1–3 (saha), `RT2` `[YENİ]` | RS485 diferansiyel | `D3` | `[io-4]` |
| `485B_B` | `ADM2587E#2.B` | J4.1–3, `RT2` `[YENİ]` | RS485 diferansiyel | `D3` | `[io-4]` |
| `485B_GND_ISO` | `ADM2587E#2.GND2` | J4.1–3 (GND ucu) | İzole referans | `D3` | `[io-4]` |
| `485B_TERM` | `RT2` anahtarı | `485B_A` ↔ `485B_B` arasına 120 Ω | — | `D3` | `[YENİ]` · **`io-tablosu.md` satır 4 bu hat için sonlandırmadan söz ETMEZ** (satır 3 eder). Bu satır bir **öneridir**; slave cihaz hattın ucunda mı ortasında mı olduğu kurulum yerleşimine bağlıdır ve depoda belirlenmemiştir |

**İki RS485 alanı birbirine bağlı değildir.** `485A_GND_ISO` ile `485B_GND_ISO` **ayrı** netlerdir
ve `GND`'ye de bağlanmazlar; aksi hâlde `io-tablosu.md` satır 3–4'ün dayandığı galvanik ayrım
düşer. Bu, kart üzerinde en kolay yapılan hatadır ve §6 satır 6'da kontrol maddesidir.

**TVS koruması.** `docs/13` satır 69 RS485 hatlarında **TVS koruma zorunlu** der. TVS
`bom.csv`'de **yoktur** ve `docs/19` satır 132 bunu zaten "montaj malzemesi… BOM'da yok" olarak
kaydeder. Bu dosya o boşluğu kapatmaz; netlerin üzerinde nerede duracağını (`485A_A`/`485A_B` →
`485A_GND_ISO`) işaretler.

---

### 3.4 I2C ağacı

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `I2C_SDA` | Çift yön — `MCU.SDA` (açık drenaj) | `ATECC608A.SDA`, `INA226#1.SDA`, `INA226#2.SDA`, `INA226#3.SDA`, `R_PU_SDA` → `+3V3` | 3,3 V açık drenaj | `D1` | `[io-13]` "kart üzeri, dışa çıkmaz" · Pull-up dirençleri `bom.csv`'de **YOK** — §5 md. 6 |
| `I2C_SCL` | `MCU.SCL` | `ATECC608A.SCL`, `INA226#1–3.SCL`, `R_PU_SCL` → `+3V3` | 3,3 V açık drenaj | `D1` | `[io-13]` |
| `INA_ALERT` | `INA226#1–3.ALERT` (açık drenaj, ortak çekilir) | `MCU.GPIO` (kesme girişi), `R_PU_ALERT` → `+3V3` | 3,3 V açık drenaj | `D1` | `[YENİ]` · Depoda tanımlı değil. Kullanılmayacaksa açık bırakılabilir, ama o zaman aşırı akım bildirimi **yalnızca yazılım sorgulamasıyla** gelir |
| `INA1_A0`, `INA1_A1` | `INA226#1.A0` / `.A1` | Sabit seviye (veri sayfasının izin verdiği seviyelerden biri — **okunmadı**) | 3,3 V | `D1` | §3.4.1 |
| `INA2_A0`, `INA2_A1` | `INA226#2.A0` / `.A1` | Sabit seviye, `#1`'den **farklı** kombinasyon | 3,3 V | `D1` | §3.4.1 |
| `INA3_A0`, `INA3_A1` | `INA226#3.A0` / `.A1` | Sabit seviye, `#1` ve `#2`'den **farklı** kombinasyon | 3,3 V | `D1` | §3.4.1 |

#### 3.4.1 Adres çatışması nasıl çözülür

Tek I2C ağacında **dört** cihaz var: `ATECC608A` + 3× `INA226` (`blok-diyagrami.md` satır 27, 53;
`bom.csv` satır 3, 14).

**Yöntem (uygulanacak sıra):**

1. Üç `INA226`, adres seçme uçları `A0`/`A1` üzerinden **birbirinden ayrılır**: her cihaza farklı
   bir `A0`/`A1` seviye kombinasyonu verilir. İki uç, en az iki seviyeyle bile dört kombinasyon
   üretir — üç cihaz için yeterlidir. **Her kombinasyonun hangi adrese karşılık geldiği ve bu
   uçların kaç farklı seviyeye bağlanabildiği veri sayfası tablosundan okunmalıdır** (§6 satır 8);
   bu depoda o tablo yoktur.
2. `ATECC608A`'nın adresinin bu aralığa düşüp düşmediği kontrol edilir. Düşüyorsa üç seçenek
   vardır: (a) `INA226` kombinasyonlarından çatışmayanları seçmek, (b) güvenli elemanı **ayrı bir
   I2C denetleyicisine** almak, (c) I2C anahtarı/çoklayıcı eklemek.
3. Seçilen kombinasyon firmware'deki adres sabitleriyle birlikte kilitlenir.

**Bu depoda hiçbir I2C adres DEĞERİ yazılmamıştır ve yazılmayacaktır.** Ne `INA226`'nın
`A0`/`A1` → adres tablosu, ne `ATECC608A-SSHDA`'nın adresi bu ortamda okunabildi. Adres
değerleri veri sayfası içeriğidir; uydurulan bir adres, kart üretildikten sonra "cihaz yanıt
vermiyor" olarak ortaya çıkar. Kontrol maddeleri: §6 satır 8, 9, 10.

Yukarıdaki 2(b) seçeneği **ESP32-S3'te birden fazla donanımsal I2C denetleyicisi bulunduğunu
varsayar — bu DOĞRULANMADI** (§6 satır 1).

---

### 3.5 SPI flash (halka tampon)

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `SPI_CLK` | `MCU.SPI.CLK` | `W25Q128JVSIQ.CLK`, J9.1–10 (genişleme kartı) | 3,3 V CMOS | `D1` | `[io-14]` `[blok:28,30]` |
| `SPI_MOSI` | `MCU.SPI.MOSI` | `W25Q128JVSIQ.DI (IO0)` | 3,3 V CMOS | `D1` | `[blok:30]` · J9 (EXP_CONN) kutupları §3.11'de zaten dolu; SPI'nin genişleme konnektörüne çıkıp çıkmayacağı **AÇIK MADDE** (§5) |
| `SPI_MISO` | Çift kaynak (paylaşımlı, tek seferde tek CS aktif): `W25Q128JVSIQ.DO (IO1)`, J9.1–10 | `MCU.SPI.MISO` | 3,3 V CMOS | `D1` | `[blok:30]` |
| `FLASH_CS_N` | `MCU.GPIO` | `W25Q128JVSIQ.CS` (aktif düşük) | 3,3 V, aktif düşük | `D1` | `[blok:28]` |
| `FLASH_WP_N` | `MCU.GPIO` **ya da** sabit `+3V3` | `W25Q128JVSIQ.WP (IO2)` | 3,3 V | `D1` | `[YENİ]` · Karar depoda yok; yazma koruması firmware'den sürülecekse GPIO, sürülmeyecekse sabit |
| `FLASH_HOLD_N` | Sabit `+3V3` | `W25Q128JVSIQ.HOLD (IO3)` | 3,3 V | `D1` | `[YENİ]` |

**Uyarı — modül içi flash ile karıştırmayın.** Sipariş kodu `ESP32-S3-WROOM-1-N8R8`'dir
(`bom.csv` satır 2). Son ekin ne kodladığı bir **üretici kataloğu bilgisidir ve bu ortamda
DOĞRULANMADI** — modülün dahili flash/PSRAM yapılandırması veri sayfasından teyit edilmelidir
(§6). Yukarıdaki `SPI_*`
netleri, modülün dışa çıkan bacaklarındaki **ayrı** bir SPI çevre birimini varsayar. Modülün
hangi bacaklarının dahili flash/PSRAM tarafından rezerve edildiği veri sayfasından okunmadan
bu netler bir bacağa atanamaz — §6 satır 3. Bu, pin numarası uydurmanın en pahalıya patladığı
yerdir: rezerve bir bacağa harici flash bağlanırsa modül **açılmaz**.

---

### 3.6 Radyo modülü (pano içi 802.15.4 / BLE)

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `RADIO_TXD` | `MCU.UART[RADIO].TXD` | Radyo modülü `RXD` | 3,3 V CMOS | `D1` | `[YENİ]` `[AÇIK]` — §5 md. 4 |
| `RADIO_RXD` | Radyo modülü `TXD` | `MCU.UART[RADIO].RXD` | 3,3 V CMOS | `D1` | `[YENİ]` `[AÇIK]` |
| `RADIO_RESET_N` | `MCU.GPIO` | Radyo modülü `RESET` (aktif düşük varsayımı) | 3,3 V | `D1` | `[YENİ]` · Aktiflik yönü **doğrulanmadı** |
| `RADIO_IRQ` | Radyo modülü `GPIO` (olay bildirimi) | `MCU.GPIO` (kesme girişi) | 3,3 V | `D1` | `[YENİ]` |
| `RADIO_VDD` | `+3V3` | Radyo modülü besleme ucu | 3,3 V | `D1` | `[blok:63]` |
| `RADIO_ANT` | Radyo modülü `ANT` | U.FL konnektörü (pano içi anten) | 2,4 GHz RF | `D1` | `[io-5]` · Dış antene gerek yok (metal kabin içi). **Hat empedansı yazılmadı:** io-tablosu.md #5 yalnızca "2,4 GHz RF" der, depoda empedans değeri yoktur — modül ve konnektör veri sayfasından alınmalıdır (§6) |

**Bu blok depodaki en zayıf temele sahip bloktur.** `blok-diyagrami.md` satır 43 MCU ile radyo
arasında yalnızca **çift yönlü bir ok** gösterir; arabirimin **türü** (UART mi, SPI mi) depoda
hiçbir yerde yazılı değildir ve `io-tablosu.md`'de bu bağ için **satır yoktur** (yalnızca satır 5,
anten konnektörü). Üstelik parça da kesinleşmemiştir: `bom.csv` satır 9 modülü **"ör. Fanstel
BT840F"** diye yazar — "ör." kelimesi oradadır. Yukarıdaki dört sinyal bir **öneridir**; modül
seçimi kesinleştiğinde arabirim onun veri sayfasından yeniden yazılmalıdır (§6 satır 11).

---

### 3.7 Hücresel modem (backhaul)

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `CELL_TXD_3V3` | `MCU.UART[CELL].TXD` | `U_LVL.A1` (seviye çevirici, **seçilmedi**) | 3,3 V CMOS | `D1` | `[io-7]` `[AÇIK]` — §5 md. 5 |
| `CELL_TXD_1V8` | `U_LVL.B1` | `EC200A.RXD` (J5.1–4) | 1,8 V CMOS | `D1` | `[io-7]` · io satırı arabirimi **1,8 V UART** olarak tanımlar |
| `CELL_RXD_1V8` | `EC200A.TXD` (J5.1–4) | `U_LVL.B2` | 1,8 V CMOS | `D1` | `[io-7]` |
| `CELL_RXD_3V3` | `U_LVL.A2` | `MCU.UART[CELL].RXD` | 3,3 V CMOS | `D1` | `[io-7]` |
| `CELL_PWR_EN` | `MCU.GPIO` (seviye çevirici üzerinden) | `EC200A.PWR_EN` (J5.1–4) | 1,8 V tarafı `[AÇIK]` | `D1` | `[io-7]` · Darbe süresi / seviye gereksinimi **doğrulanmadı** (§6 satır 12) |
| `CELL_GND` | `GND` | `EC200A.GND` (J5.1–4) | 0 V | `D1` | `[io-7]` |
| `CELL_VBAT` | `+5V` **ya da** ayrı besleme yolu | `EC200A` besleme ucu | **Belirsiz** | `D1` | `[AÇIK]` · **`io-tablosu.md` satır 7 J5'i yalnızca TXD/RXD/PWR_EN/GND olarak sayar; besleme ucu bu dörtlüde YOKTUR** — §5 md. 5 |
| `CELL_ANT` | `EC200A.ANT` | SMA konnektörü (panel üstü) | RF | `D1` | `[io-6]` · Şartname 2.2.8.1.iv harici anten çıkışından geçirilir |

---

### 3.8 Röle sürücüleri

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `RLY1_DRV` | `MCU.GPIO` | `ULN2003AN.IN1` | 3,3 V CMOS | `D1` | `[blok:51,55]` |
| `RLY2_DRV` | `MCU.GPIO` | `ULN2003AN.IN2` | 3,3 V CMOS | `D1` | `[blok:51,55]` |
| `RLY1_COIL_LO` | `ULN2003AN.OUT1` (çeken çıkış) | `G5LE#1.bobin−` | `V_COIL` seviyesi | `D1` | `[bom:11,12]` |
| `RLY2_COIL_LO` | `ULN2003AN.OUT2` | `G5LE#2.bobin−` | `V_COIL` seviyesi | `D1` | `[bom:11,12]` |
| `ULN_COM` | `V_COIL` | `ULN2003AN.COM` | `V_COIL` seviyesi | `D1` | **Serbest dolaşım yolu** — aşağıya bakın |
| `RLY1_CONTACT` | `G5LE#1` kontak (COM/NO) | J6.1–2 | 24 VDC / 1 A kuru kontak | `D5-KONTAK1` | `[io-8]` · Siren/flaşör (P1) |
| `RLY2_CONTACT` | `G5LE#2` kontak (COM/NO) | J6.3–4 | 24 VDC / 1 A kuru kontak | `D5-KONTAK2` | `[io-9]` · Isıtıcı/fan |

**Serbest dolaşım (flyback) yolu — tasarım varsayımı, DOĞRULANMADI.** Röle bobini endüktif bir
yüktür; sürücü kesildiği anda bobin üzerinde ters yönde yüksek bir gerilim oluşur ve bu gerilim
sürücüyü bozar. Bu tabloda varsayım şudur: **`ULN2003AN`'ın `COM` ucu, dizinin dahili serbest
dolaşım diyotlarının ortak ucudur ve bobin besleme rayına (`V_COIL`) bağlanır** — enerji oradan
boşalır. Bu, `ULN2003AN` **veri sayfasına karşı doğrulanmadı** (§6 satır 13).

`COM` bağlanmazsa ya da dizide böyle bir diyot yoksa, bobin başına **ayrı bir serbest dolaşım
diyodu** gerekir; `bom.csv`'de diyot satır kalemi **yoktur**.

Ayrıca `bom.csv` satır 11 röleyi **`Omron G5LE-1-VD 24DC`** diye yazar. `-VD` son ekinin ne
anlattığı (bobin diyodu mu, kontak malzemesi mi, başka bir varyant mı) üretici kataloğundan
**doğrulanmalıdır** (§6 satır 13). Bu tabloda **röle içinde bir diyot bulunduğu varsayılmamıştır.**

---

### 3.9 Optokuplör girişleri

Aşağıdaki desen dört kanalın her biri için aynıdır (`n` = 1…4). `io-tablosu.md` satır 10 kanal 1'i
(S5 kapı reed kontağı, J7.1–2), satır 11 kanal 2–4'ü (J7.3–8, v1'de kullanılmıyor) tanımlar.

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `OPTOn_FLD+` | J7 (saha, 24 VDC harici kontak) | `R_OPTOn` (seri direnç, **değeri belirlenmedi**) → `TLP291#n.anot` | 24 VDC saha | `D4-OPTOn` | `[io-10,11]` |
| `OPTOn_FLD−` | J7 (saha dönüşü) | `TLP291#n.katot` | 24 VDC saha | `D4-OPTOn` | `[io-10,11]` · Her kanalın kendi dönüşü vardır (§2) |
| `OPTOn_OUT` | `TLP291#n.kollektör` | `MCU.GPIO` (giriş), `R_PU_OPTOn` → `+3V3` | 3,3 V | `D1` | `[io-10,11]` · Pull-up `bom.csv`'de **yok** |
| `GND` (bu blokta) | `TLP291#n.emiter` | `GND` (§3.1) | 0 V | `D1` | Dört kanalın emiteri ortak `GND`'dedir |

**Seri direncin değeri bu dosyada YAZILMAMIŞTIR ve hesaplanmamıştır.** Değer, LED ileri gerilimi
ve seçilecek ileri akımdan çıkar; ikisi de veri sayfası parametresidir. `docs/19` satır 101 bunu
zaten kaydeder: *"optokuplörlerde akım transfer oranı sıcaklıkla ve yaşla düşer; giriş direnci
buna göre boyutlandırılmadı."* Bu dosya o boşluğu **kapatmaz**, direncin net üzerinde nerede
durduğunu gösterir (§6 satır 14).

**Parça adı notu.** `io-tablosu.md` satır 10–11 optokuplörü **PC817** diye yazar; `bom.csv` satır
13 ise **Toshiba TLP291 (PC817 eşdeğeri)** der. Bu dosyada BOM'un sipariş edilebilir kodu
(`TLP291`) kullanılmıştır; iki ad aynı parçayı kasteder, "eşdeğer" niteleme BOM satırındadır ve
**doğrulanmamıştır**.

---

### 3.10 CT (akım trafosu) girişleri

`io-tablosu.md` satır 12: üç kanal, J8.1–6, ölçüm zinciri **ayrık çekirdekli AT sekonderi →
burden direnci → INA226**. Kanal deseni (`n` = 1…3):

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `CTn_SEC_A` | J8 (AT sekonderi, ayrık çekirdek) | `R_BURDENn` ucu, `CTn_SENSE+` | 0–5 A sekonder | `D6-AT` → `D1` | `[io-12]` |
| `CTn_SEC_B` | J8 (AT sekonderi) | `R_BURDENn` diğer ucu, `CTn_SENSE−` | 0–5 A sekonder | `D6-AT` → `D1` | `[io-12]` |
| `CTn_SENSE+` | `R_BURDENn` üst ucu | `INA226#n.IN+` | Burden üzerindeki gerilim `[AÇIK]` | `D1` | `[io-12]` · §5 md. 9 |
| `CTn_SENSE−` | `R_BURDENn` alt ucu | `INA226#n.IN−`, `GND` referansı | Burden üzerindeki gerilim | `D1` | `[io-12]` |
| `CTn_VBUS` | `INA226#n.VBUS` | **Kullanılmıyor** — bağlanma kuralı belirlenmedi | — | `D1` | `[YENİ]` `[AÇIK]` · Burden okumasında bara gerilimi ölçülmez; ucun açık mı yoksa bir referansa mı bağlanacağı veri sayfasından okunmalı (§6 satır 15) |

**Topoloji kuralı — bu bloğun en önemli satırı.** `io-tablosu.md` satır 12 kurulum kuralını
yazar: **"AT sekonderi asla açık bırakılmaz."** Bunun kart üzerindeki karşılığı şudur:

> `CTn_SEC_A` ve `CTn_SEC_B` ile `R_BURDENn` arasında **açılabilir hiçbir eleman bulunmamalıdır**
> — anahtar, jumper, sigorta, soketli/geçmeli direnç, ayrılabilir klemens köprüsü dâhil.

Açık kalan bir AT sekonderinde çekirdek doyar ve uçlarda tehlikeli gerilim oluşur. Bu, `docs/17`
satır 206'da **"FMEA'daki en ağır donanım riski"** olarak geçen kuralın net seviyesindeki
karşılığıdır.

**Burden direnci bu dosyada boyutlandırılmamıştır** — §5 md. 9 ve §6 satır 15–16.

---

### 3.11 EXP_CONN — PD ön uç kartı konnektörü (J9)

`io-tablosu.md` satır 14: J9.1–10, "SPI/I2C + 3V3/5V", OG eklentisi, boş bırakılabilir. Karşı
taraftaki sinyal listesi `hardware/pd-karti/io-tablosu.md` satır 9–15'tedir.

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `+5V` | `IRM-10-5.+Vo` | J9 → PD kartı `VDD_5V` | 5 V | `D1` | `[io-14]` · PD tarafı: `pd-karti/io-tablosu.md` satır 9 |
| `+3V3` | `TLV1117-33.OUT` | J9 | 3,3 V | `D1` | `[io-14]` · PD kartı v1'de 3V3 **kullanmıyor** |
| `GND` | — | J9 → PD kartı `GND` | 0 V | `D1` | `[io-14]` |
| `SPI_CLK` | `MCU.SPI.CLK` | J9 → PD kartı `SPI_SCK` | 3,3 V | `D1` | §3.5 ile aynı net |
| `SPI_MISO` | PD kartı `SPI_MISO` | J9 → `MCU.SPI.MISO` | 3,3 V | `D1` | §3.5 ile aynı net (paylaşımlı) |
| `EXP_CS_N` | `MCU.GPIO` | J9 → PD kartı `SPI_CS` | 3,3 V, aktif düşük | `D1` | **Ayrı CS** — flash ile aynı CS kullanılamaz |
| `EXP_TRIG` | PD kartı `TRIG_OUT` | J9 → `MCU.GPIO` (kesme girişi) | 3,3 V push-pull | `D1` | `[AÇIK]` · SPI/I2C değil — §5 md. 8 |
| `EXP_VREF` | `MCU` analog/PWM çıkışı | J9 → PD kartı `VREF_SET` | 0–3,3 V analog | `D1` | `[AÇIK]` · Üretim yöntemi belirsiz — §5 md. 8, §6 satır 2 |
| `I2C_SDA`, `I2C_SCL` | §3.4 | J9 (yedek) | 3,3 V | `D1` | `[io-14]` "SPI/I2C" der; PD kartı v1'de I2C kullanmıyor |

J9'un on kutbundan PD kartının v1'de kullandığı **yedisidir**; kalan üçü yedektir. **J9'un hangi
kutbunda hangi sinyalin durduğu iki dosyada da tanımlı değildir** ve bu dosya da tanımlamaz —
kutup ataması bir mekanik/layout kararıdır (§1).

---

### 3.12 DEBUG portu (J10)

`io-tablosu.md` satır 15: UART TX/RX + JTAG, **üretimde lehim köprüsüyle devre dışı**
(IEC 62443 — "sahada gelen port yok"; standardın **madde numarası verilmiyor**, metnine
erişilmedi).

| Net adı | Kaynak (bileşen.işlevsel_pin) | Hedefler | Seviye | İzolasyon sınırı | Not |
|---|---|---|---|---|---|
| `DBG_TXD` | `MCU.U0TXD` | `SB_TXD` lehim köprüsü → J10 | 3,3 V CMOS | `D1` | `[io-15]` |
| `DBG_RXD` | J10 → `SB_RXD` lehim köprüsü | `MCU.U0RXD` | 3,3 V CMOS | `D1` | `[io-15]` |
| `DBG_TMS` | JTAG `TMS` | `SB_TMS` → J10 | 3,3 V | `D1` | `[io-15]` · Genel JTAG sinyal adları (standart **adı ve numarası verilmiyor** — metnine erişilmedi); MCU tarafındaki karşılıkları **doğrulanmadı** |
| `DBG_TCK` | JTAG `TCK` | `SB_TCK` → J10 | 3,3 V | `D1` | `[io-15]` |
| `DBG_TDI` | JTAG `TDI` | `SB_TDI` → J10 | 3,3 V | `D1` | `[io-15]` |
| `DBG_TDO` | JTAG `TDO` | `SB_TDO` → J10 | 3,3 V | `D1` | `[io-15]` |
| `GND` | — | J10 | 0 V | `D1` | `[io-15]` |

**Devre dışı bırakma netin neresinde?** Lehim köprüleri (`SB_*`) **MCU ile konnektör arasında**
durur, konnektörün kendisinde değil. Üretimde köprüler açık bırakılır; köprü konnektör tarafında
olsaydı iz MCU'ya kadar canlı kalır ve konnektöre erişen biri sinyale erişirdi. Bu, `io-tablosu.md`
satır 15'in "üretimde devre dışı" ifadesinin **net seviyesindeki** karşılığıdır ve bu dosyada ilk
kez yazılmaktadır `[YENİ]`.

`DBG_TXD`/`DBG_RXD` ile `MCU.U0TXD`/`U0RXD` eşlemesi, UART0'ın önyükleme konsolu olduğu
varsayımına dayanır — **DOĞRULANMADI** (§6 satır 1).

---

## 4. `io-tablosu.md` ile çapraz referans

Her dış konnektör, bu dosyadaki hangi netleri taşır:

| Konnektör | `io-tablosu.md` satırı (`#`) | Kutup (io'da yazılı) | Bu dosyadaki netler | Bölüm | Uyum |
|---|---|---|---|---|---|
| **J1** | 1 | 2 | `MAINS_L`, `MAINS_N` | §3.1 | ✅ |
| **J2** | 2 | 4 | `+5V`, `+3V3`, `GND` | §3.1 | ✅ (4. kutbun ne olduğu io'da belirtilmemiş) |
| **J3** | 3 | 3 | `485A_A`, `485A_B`, `485A_GND_ISO` | §3.2 | ✅ |
| **J4** | 4 | 3 | `485B_A`, `485B_B`, `485B_GND_ISO` | §3.3 | ✅ (sonlandırma `RT2` **yeni öneri**) |
| **U.FL** | 5 | — | `RADIO_ANT` | §3.6 | ✅ |
| **SMA** | 6 | — | `CELL_ANT` | §3.7 | ✅ |
| **J5** | 7 | 4 | `CELL_TXD_1V8`, `CELL_RXD_1V8`, `CELL_PWR_EN`, `CELL_GND` | §3.7 | ⚠️ Besleme ucu yok — §5 md. 5 |
| **J6** | 8, 9 | 2 + 2 | `RLY1_CONTACT`, `RLY2_CONTACT` | §3.8 | ✅ |
| **J7** | 10, 11 | 2 + 6 | `OPTO1…4_FLD+`, `OPTO1…4_FLD−` | §3.9 | ✅ |
| **J8** | 12 | 6 | `CT1…3_SEC_A`, `CT1…3_SEC_B` | §3.10 | ✅ |
| **(dahili)** | 13 | — | `I2C_SDA`, `I2C_SCL` (+ adres ve ALERT netleri) | §3.4 | ✅ "dışa çıkmaz" — J9'a giden yedek uçlar hariç |
| **J9** | 14 | 10 | `+5V`, `+3V3`, `GND`, `SPI_CLK`, `SPI_MISO`, `EXP_CS_N`, `EXP_TRIG`, `EXP_VREF`, `I2C_SDA`, `I2C_SCL` | §3.11 | ⚠️ `EXP_TRIG`/`EXP_VREF` "SPI/I2C" tanımının dışında — §5 md. 8 |
| **J10** | 15 | **belirtilmemiş** | `DBG_TXD`, `DBG_RXD`, `DBG_TMS/TCK/TDI/TDO`, `GND` | §3.12 | ⚠️ Kutup sayısı io'da yok — §5 md. 10 |
| **DIN_GND** | 16 | — | `DIN_GND` | §3.1 | ⚠️ Plastik kutu — §5 md. 7 |

**Kapsama kontrolü:** `io-tablosu.md`'deki **16 satırın 16'sının da** bu dosyada karşılığı vardır.
Ters yönde tam eşleşme yoktur ve olması da beklenmez: bu dosya ayrıca **kart içi** netleri
(besleme ağacı, I2C adres uçları, SPI flash, sürücü girişleri, seviye çevirici) taşır; onların
`io-tablosu.md`'de satırı yoktur çünkü o tablo dışa bakan arayüzleri listeler.

---

## 5. Bu tabloyu kurarken ortaya çıkan AÇIK maddeler

Net listesi, blok diyagramının gizleyebildiği şeyleri görünür kılar: bir blok oku "bağlı" der ve
geçer, bir net ise **iki ucu olmak zorundadır**. Aşağıdakiler bu yüzden ortaya çıktı.

**Bu dosya bu maddelerin hiçbirini ÇÖZMEZ — işaretler.** Çözmek, elimizde olmayan veri
sayfalarıyla ya da donmuş `contracts/` dışındaki tasarım kararlarıyla mümkündür.

| # | Açık madde | Depodaki dayanak | Neden önemli |
|---|---|---|---|
| 1 | **Seri arabirim sayısı, MCU'nun donanımsal UART sayısını aşıyor olabilir.** Bu tabloda **beş** ayrı seri talep var: RS485 #1, RS485 #2, hücresel modem, radyo modülü (arabirim seçilmemiş), DEBUG konsolu | `blok-diyagrami.md` satır 37, 38, 43, 48; `io-tablosu.md` satır 15 | ESP32-S3'ün kaç donanımsal UART taşıdığı **doğrulanmadı**. Beşten azsa çözüm gerekir: radyoyu SPI'a almak, DEBUG'ı üretimde zaten kapalı bir hatla paylaştırmak, ya da modem/radyo arabirimini değiştirmek. **Bu karar layout'tan ÖNCE verilmelidir** ve depoda hiçbir yerde ele alınmamıştır |
| 2 | **Süperkapasitör kolunun elemanları yok.** ORing/ayırma elemanı, şarj akımı sınırlama, seri bankta gerilim dengeleme | `blok-diyagrami.md` satır 20, 22 (yalnızca kesik çizgili "kesinti anında" oku); `bom.csv` — bu üç eleman için **satır yok** | `docs/13` §2'deki ~15,8 s'lik "son nefes" hesabı bu kolun **var olduğunu varsayar**. Dengeleme yoksa seri süperkapasitörlerden biri anma geriliminin üstünde kalabilir |
| 3 | **Röle bobinleri 24 V, ama kartta 24 V rayı yok.** Güç ağacı yalnızca 230 VAC → 5 V → 3V3'tür | `blok-diyagrami.md` satır 19–21 (güç ağacı), satır 96 ("2 × 70 mA @ 24V bobin"); `bom.csv` satır 11 (`G5LE-1-VD **24DC**`); `io-tablosu.md` satır 1–16 — **24 V besleme girişi için konnektör satırı yok** | `V_COIL` netinin kaynağı yok. Üç yol var: (a) panoda 24 VDC yardımcı besleme **varsa** onu yeni bir konnektörden almak (varlığı depoda doğrulanmadı; io-tablosu ve BOM değişir), (b) kartta 5 V→24 V yükseltici eklemek (BOM'da yok), (c) **5 V bobinli röleye geçmek** (BOM satırı 11 değişir). Hiçbiri seçilmemiştir |
| 4 | **MCU ↔ radyo modülü arabirimi hiçbir yerde tanımlı değil.** Üstelik modül de kesinleşmemiş | `blok-diyagrami.md` satır 43 (yalnızca çift yönlü ok); `io-tablosu.md`'de satır **yok**; `bom.csv` satır 9: "ör. Fanstel BT840F" | §3.6'daki dört sinyal `[YENİ]` önerisidir. Modül seçimi arabirimi belirler; bu da md. 1'deki UART bütçesini belirler |
| 5 | **Modem arabiriminde iki eksik: seviye çevirici ve besleme.** J5, TXD/RXD/PWR_EN/GND olarak dört uçtur | `io-tablosu.md` satır 7 (**1,8 V UART**, dört uç); `blok-diyagrami.md` satır 46 ("M.2/UART"); `bom.csv` — seviye çevirici **yok**, M.2 yuvası/konnektörü **yok** | MCU 3,3 V, modem 1,8 V: doğrudan bağlanamazlar. Besleme J5'te olmadığına göre modem büyük olasılıkla kart üzerindeki bir M.2 yuvasına oturuyor — ama o yuva BOM'da yok (`bom.csv` satır 15 yalnızca 10 adet 2 kutuplu vidalı klemens sayar). Ayrıca `blok-diyagrami.md` satır 95 modemin **2 A tepe** çektiğini yazar ve hangi rayda olduğunu söylemez; `IRM-10-5`'in anma akımı da 2 A'dır (`bom.csv` satır 6) — `docs/19` satır 66 bu etkiyi zaten "**ölçülmedi**" diye kaydeder. Burada eklediğimiz, bunun bir **topoloji sorusu** da olduğudur |
| 6 | **BOM'da hiç pasif bileşen satırı yok.** Bu dosyada geçen `RT1`/`RT2` (120 Ω), `R_PU_*` (I2C ve giriş pull-up'ları), `R_OPTO1…4` (seri direnç), `R_BURDEN1…3` (burden), TVS, ayırma/serbest dolaşım diyotları, dengeleme dirençleri, tampon kondansatörler | `bom.csv` 17 satır kalemi taşır ve **hiçbiri direnç/kondansatör/diyot değildir**; `docs/19` satır 132 montaj malzemesi için aynı boşluğu kaydeder; `io-tablosu.md` satır 3 ise "120 Ω sonlandırma anahtarlı" der | Bu, maliyet tablosunu da etkiler: `docs/19` satır 112'deki 70,73 / 47,68 USD toplamları pasifsiz bir karta aittir |
| 7 | **`DIN_GND` nereye bağlanıyor?** Kutu polikarbonattır | `io-tablosu.md` satır 16 ("DIN ray üzerinden pano PE'sine"); `bom.csv` satır 16 (`Fibox ARCA 92/125`, **PC V-0**, yani plastik) | Plastik kutuda topraklanacak metalik gövde yoktur. `DIN_GND` bir klemens ucu olarak kalır; kart `GND`'si ile arasındaki bağ (doğrudan / kondansatörlü / hiç) bir **EMC kararıdır** ve depoda verilmemiştir. `docs/11` satır 14'teki IEC 61000-6-5 hedefi bu karara bağlıdır |
| 8 | **PD kartı ile iki çelişki.** (a) Konnektör numarası, (b) sinyal türü | (a) `hardware/pd-karti/io-tablosu.md` satır 3 bağlantıyı **"J10 klemens"** üzerinden tarif eder; `hardware/pano-beyni/io-tablosu.md` satır 14 EXP_CONN'u **J9**, satır 15 ise J10'u **DEBUG** olarak tanımlar. (b) `pd-karti/io-tablosu.md` satır 14–15 `TRIG_OUT` (kesme) ve `VREF_SET` (analog eşik) ister; `io-tablosu.md` satır 14 J9'u "SPI/I2C + 3V3/5V" diye tanımlar | **Bu dosya `hardware/pano-beyni/io-tablosu.md`'yi esas almıştır: genişleme konnektörü J9'dur.** PD kartı dosyasındaki "J10" ifadesi düzeltilmelidir — ama PD kartı bu teslimin kapsamı değildir (`docs/19` satır 131: kart üretilmedi, doğrulanmadı), bu yüzden burada yalnızca **işaretlenmiştir**. (b) için: `pd-karti/io-tablosu.md` satır 15 `VREF_SET` kaynağını "ESP32-S3 **DAC** çıkışı" diye yazar; ESP32-S3'te donanımsal DAC bulunup bulunmadığı bu depoda **doğrulanmadı** (§6 satır 2) |
| 9 | **Burden çıkış seviyesi ile INA226 giriş aralığı uyuşuyor mu, bilinmiyor.** | `io-tablosu.md` satır 12 ölçüm zincirini "0–5 A sekonder → burden → **0–3V3**" diye yazar; `INA226` bir şönt akım ölçerdir ve şönt giriş tam ölçek aralığı **veri sayfasından okunmadı** | Burden üzerinde 3,3 V'a kadar bir gerilim üretmek ile bir şönt ölçerin giriş aralığı aynı şey olmayabilir. Uyuşmuyorsa ya burden küçültülmeli ya ölçüm elemanı değişmelidir. **Bu iki ifadenin uyumu DOĞRULANMADI** (§6 satır 15) |
| 10 | **Konnektör BOM satırı, istenen kutup sayısını karşılamıyor.** | `bom.csv` satır 15: **10 adet 2 kutuplu** klemens (`Phoenix Contact MC 1.5/2-ST-3.5`, not: "J1-J10 govde ortalama") = **20 kutup**. `io-tablosu.md`'de J1–J9 için açıkça yazılı kutup toplamı: 2+4+3+3+4+4+8+6+10 = **44** (J10'un kutup sayısı hiç belirtilmemiş) | `docs/19` satır 103 bu satır için "tek tip varsayılmıştır" der ve **gerilim** tarafını işaretler; buradaki ek bulgu **kutup sayısıdır**. BOM'un konnektör satırı layout öncesinde kutup sayısına göre ayrıştırılmalıdır |

---

## 6. Layout öncesi DOĞRULANMASI gerekenler

Her satır **bir veri sayfası kontrolüdür.** Hiçbiri bu teslimde yapılmadı — bu depoda hiçbir
üretici veri sayfasına erişilmedi (`docs/19` satır 83–86). Sıra, `docs/19` §4.1'deki öncelik
listesiyle çelişmez; o liste *hangi parçanın* önce çekileceğini söyler, bu liste *o veri sayfasında
neye bakılacağını*.

| # | Parça / belge | Ne doğrulanacak | Bu dosyada etkilediği yer | Yanlışsa ne olur |
|---|---|---|---|---|
| 1 | `ESP32-S3-WROOM-1-N8R8` | Donanımsal UART / I2C / SPI çevre birimi **sayıları**; çevre birimlerinin bacaklara serbestçe yönlendirilip yönlendirilemediği; önyükleme konsolunun hangi UART olduğu | §3.2, §3.3, §3.4.1, §3.6, §3.7, §3.12; §5 md. 1 | Arabirim bütçesi tutmaz; radyo ya da DEBUG portu için topoloji değişir |
| 2 | `ESP32-S3-WROOM-1-N8R8` | Donanımsal **DAC** çıkışı var mı; yoksa analog eşik referansı nasıl üretilecek (PWM + RC alçak geçiren, harici DAC) | §3.11 `EXP_VREF`; §5 md. 8 | PD ön uç kartının eşik referansı üretilemez; J9 tanımı değişir |
| 3 | `ESP32-S3-WROOM-1-N8R8` | Modül içi flash/PSRAM'in **rezerve ettiği** bacaklar; harici SPI için serbest kalanlar | §3.5 | Rezerve bacağa harici flash bağlanırsa **modül açılmaz** |
| 4 | `MEAN WELL IRM-10-5` | Uç adları (`L`, `N`, `+Vo`, `−Vo`); ayrı bir koruma toprağı (FG) ucu var mı; tepe akım davranışı | §3.1 | Şebekeye bağlanan tek parçadır; uç adının yanlış olması doğrudan güvenlik konusudur |
| 5 | `TLV1117-33` | Uç adları (`IN`, `OUT`, `GND`); sabit 3,3 V varyantın ayar ucu var mı; giriş/çıkış kondansatör gereksinimi | §3.1 | 3V3 rayı kararsız çalışır (kondansatörler `bom.csv`'de yok — §5 md. 6) |
| 6 | `ADM2587EBRWZ` | Uç adları (`TxD`, `RxD`, `DE`, `RE`, `A`, `B`, `GND1`, `GND2`, `VDD1`); **yarım çift yönlü** kullanım için uçların köprülenmesi gerekip gerekmediği; izole taraf referansının kart `GND`'sinden ayrı tutulması | §3.2, §3.3 | Yanlış köprüleme hattı sürekli meşgul eder; `GND1`/`GND2` birleşirse **2500 Vrms galvanik ayrım düşer** |
| 7 | `ADM2587EBRWZ` | 120 Ω sonlandırmanın hattın hangi ucuna konacağı ve anahtarlanabilir olmasının kabul edilip edilmediği | §3.2 `485A_TERM`, §3.3 `485B_TERM` | Yansımalar; Modbus RTU'da çerçeve hataları |
| 8 | `INA226AIDGST` | `A0`/`A1` adres seçme tablosu (hangi seviye hangi adresi verir); `ALERT` ucunun açık drenaj olup olmadığı | §3.4, §3.4.1 | Üç cihazdan ikisi aynı adrese düşerse **hiçbiri okunamaz** |
| 9 | `ATECC608A-SSHDA` | I2C adresinin sabit mi yapılandırılabilir mi olduğu (sipariş kodu son eki bunu belirliyor **olabilir** — doğrulanmadı) | §3.4.1 | Güvenli eleman `INA226` bloğuyla çakışırsa cihaz kimliği okunamaz |
| 10 | I2C hattı | Pull-up direnç değeri: toplam hat kapasitansı ve hız sınıfına göre | §3.4; §5 md. 6 | Kenarlar yavaşlar, haberleşme kararsızlaşır |
| 11 | Radyo modülü (**önce parça kesinleşmeli** — `bom.csv` satır 9 "ör." der) | Arabirim türü (UART/SPI), uç adları, `RESET` aktiflik yönü, besleme gerilimi, anten konnektörü tipi | §3.6; §5 md. 4 | Blok tamamen yeniden yazılır |
| 12 | `Quectel EC200A-EU` | Besleme gerilimi ve tepe akımı; UART seviyesinin gerçekten 1,8 V olduğu; `PWR_EN` için gereken seviye ve **darbe süresi**; M.2 mi UART mi bağlanacağı | §3.7; §5 md. 5 | Modem açılmaz ya da 5 V rayı TX darbesinde çöker |
| 13 | `ULN2003AN` + `Omron G5LE-1-VD 24DC` | `COM` ucunun gerçekten dahili serbest dolaşım diyotlarının ortak ucu olduğu; bobin gerilimi/akımı; kontak yapısı (SPST-NO mu SPDT mi — `io-tablosu.md` satır 8–9 yalnızca "NO" der); `-VD` son ekinin ne anlattığı; sürücünün çekebileceği akım | §3.8; §5 md. 3 | Bobin kesilince oluşan ters gerilim **sürücüyü bozar**; kart sahada ölür |
| 14 | `Toshiba TLP291` | LED ileri gerilimi ve önerilen ileri akım (seri direnç bundan çıkar); akım transfer oranının sıcaklık ve yaşla düşümü; çıkış tarafı için gereken pull-up | §3.9 | Direnç büyük seçilirse giriş **sıcakta ya da yıllar sonra okunmaz olur** (`docs/19` satır 101) |
| 15 | `INA226AIDGST` + burden | Şönt giriş tam ölçek aralığı; ortak mod aralığı; `VBUS` ucunun kullanılmadığında nasıl bağlanacağı; burden değerinin AT sekonder akımından hesaplanması | §3.10; §5 md. 9 | `io-tablosu.md` satır 12'nin "0–3V3" ifadesiyle uyuşmazsa ölçüm zinciri baştan kurulur |
| 16 | `INA226AIDGST` | Örnekleme / ortalama davranışının **alternatif akım** ölçümü için yeterli olduğu (AT sekonderi 50 Hz AC taşır) | §3.10 | Fider akımı sistematik olarak yanlış okunur — ve bu, kalibrasyonla düzelmeyen bir hatadır |
| 17 | `W25Q128JVSIQ` | Uç adları (`CS`, `CLK`, `DI/IO0`, `DO/IO1`, `WP/IO2`, `HOLD/IO3`); `WP`/`HOLD` uçlarının boş bırakılamayacağı | §3.5 | Uçlar açık kalırsa flash rastgele kilitlenir |
| 18 | `Phoenix Contact MC 1.5/2-ST-3.5` | **Kutup sayısı varyantları** ve J1 (230 VAC) için anma gerilimi / kaçak yolu | §4; §5 md. 10 | BOM satırı ve maliyet toplamı değişir (`docs/19` satır 103, 112) |
| 19 | `Eaton HB1840-2R7107-R` | Anma gerilimi, dengeleme gereksinimi, şarj akımı sınırı, ESR | §3.1; §5 md. 2 | `docs/13` §2'deki son nefes hesabının fiziksel dayanağı çöker |
| 20 | PCB laminatı (`bom.csv` satır 17: "4 katmanlı PCB") | Katman yığını, bakır kalınlığı, dielektrik — **RS485 ve SPI izlerinin** empedansı bunlara bağlı | §0.2 | Empedans kontrolü yapılamaz; sinyal bütünlüğü tesadüfe kalır |

**Bu listede olmayan bir şey:** clearance/creepage **ölçüleri**. Onlar `docs/13` §4'ün konusudur
ve orada da **hesaplanmamıştır** (IEC 60664-1 tam metnine erişilmedi, madde/tablo numarası
bilinçli olarak yazılmamıştır). Bu dosya `D0`↔`D1` sınırının **nerede** olduğunu söyler, o sınırın
kaç milimetre olması gerektiğini **söylemez**.

---

## 7. Bu dosyanın dürüstlük sınırları — tek paragrafta

Burada **hiçbir şey ölçülmedi.** Kart üretilmedi, hiçbir net süreklilik ya da izolasyon
testinden geçmedi, hiçbir sinyal osiloskopta görülmedi. Bileşenlerin **işlevsel uç adları veri
sayfasına karşı doğrulanmadı** ve **fiziksel pin numarası hiç yazılmadı** (§0.3). Standart
adları depoda zaten anılan standartlardan alınmıştır ve **hiçbirinin madde numarası
verilmemiştir** — metinlerine erişilmedi (`docs/11`, `docs/13` §4, `docs/19` aynı kuralı
uygular). Tek madde numarası, §3.7'deki **şartname 2.2.8.1.iv** atfıdır ve o da
`io-tablosu.md` satır 6'dan **aynen aktarılmıştır**, bu dosyada üretilmemiştir. §5'teki on açık
madde **çözülmemiş**, yalnızca görünür kılınmıştır. Bu dosyanın
katkısı tek cümleyle şudur: **bir şemanın taşıdığı bilgiyi, taşıyamadığı iddiaları eklemeden
yazmak.**

---

## 8. Değişiklik günlüğü

- **v1 (20 Eylül 2026):** İlk sürüm. `blok-diyagrami.md` ve `io-tablosu.md` net seviyesine
  açıldı; §5'teki on açık madde bu çalışma sırasında ortaya çıktı ve hiçbiri kapatılmadı.
