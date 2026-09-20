# Sensör Düğümü — Bağlantı (Net) Tablosu

**Sahip:** Kişi C · **Tarih:** 20 Eylül 2026 · **Sürüm:** v1

> **Kaynak dosyalar (bu dosyadaki her satır bunlardan birine dayanır):**
> [`blok-diyagrami.md`](blok-diyagrami.md), [`io-tablosu.md`](io-tablosu.md),
> [`enerji-ve-termal-hesap.md`](enerji-ve-termal-hesap.md), [`bom.csv`](bom.csv),
> [`README.md`](README.md) ve karşı taraf için
> [`../pano-beyni/io-tablosu.md`](../pano-beyni/io-tablosu.md),
> [`../pano-beyni/blok-diyagrami.md`](../pano-beyni/blok-diyagrami.md).
> Depo dışı hiçbir kaynak kullanılmamıştır.

---

## 0. Kapsam — bu dosya ne DEĞİLDİR

**Bu bir şematik DEĞİLDİR.** Bir netlist de değildir; bir CAD aracına doğrudan aktarılamaz.
Yaptığı tek şey, dört ayrı dosyaya dağılmış blokların **hangi sinyalle birbirine bağlandığını**
tek tabloda toplamak ve **neyin bilinmediğini** aynı tabloda göstermektir.

| Bu dosyada **var** | Bu dosyada **yok** (ve neden) |
|---|---|
| Blok-blok net listesi, sinyal adı, yön, kaynak dosya:satır | **Fiziksel paket pin numarası** — depoda hiçbir bileşenin veri sayfası yok; numara yazmak uydurma olurdu |
| `io-tablosu.md`'de atanmış **işlevsel** pin/port adları (`P0.26`, `SWDIO`, `AIN0` …) | **Mutlak maksimum değerler, paket ölçüleri, besleme sınırları** — aynı gerekçe |
| `enerji-ve-termal-hesap.md`'deki sayıların olduğu gibi taşınması | **Yeni hesap / yeni sayı** — bu dosya hiçbir değer türetmedi |
| Depo içi çelişkilerin kaydı (Bölüm 8) | **Çelişkilerin çözümü** — hangisinin doğru olduğu ölçülmeden bilinemez |

> **Pin adları hakkında:** bu dosyadaki **her işlevsel pin/port adı** (`P0.xx`, `AIN0/1/5`,
> `SWDIO`, `SWDCLK`, `SDA`, `SCL`, `VDD`, `VSS`) doğrudan `io-tablosu.md`'den alınmıştır ve
> **veri sayfasına karşı DOĞRULANMADI.** Bir portun gerçekten o çevre birimine bağlanabildiği,
> bu adların üreticinin kullandığı adlarla birebir örtüştüğü ve bir paket ayağına karşılık geldiği
> **kontrol edilmemiştir.**

**Doğrulama durumu — tek cümleyle:** bu düğüm **üretilmedi**, hiçbir net **ölçülmedi**, BOM'un
11 satırının hiçbiri **veri sayfasına karşı doğrulanmadı** ve kablosuz menzil metal kabin içinde
**hiç ölçülmedi** (`../../docs/19-tedas-sartname-uyumu.md:130`,
`../../docs/17-donanimsiz-dogrulama.md:249`). Aşağıdaki "Durum" sütununda
**DOĞRULANMADI** yazan her satır bu cümlenin kapsamındadır.

`../pano-beyni/README.md`'deki **"KiCad şeması hakkında dürüstlük notu"** bu dizin için de aynen geçerlidir:
elde KiCad yoktur, sembol/footprint doğrulaması yapılamaz, bu yüzden teslim seviyesi
**blok diyagramı + I/O tablosu + BOM + bu net tablosudur.**

---

## 1. Güç netleri (hibrit kaynak)

| Net | Kaynak (sürücü) | Hedef(ler) | Değer / seviye | Dayanak | Durum |
|---|---|---|---|---|---|
| `N_HARVEST_AC` | Split-core hasat trafosu sekonderi (Murata / Custom Split-Core CT 1:1000) | LTC3331 AC hasat girişi | AC indüklenen akım (genlik yazılı değil) | `blok-diyagrami.md:10,20`; `bom.csv:6` | DOĞRULANMADI — parça "Custom", numara yok |
| `VBAT_PRI` | Tadiran TL-5902/S LiSOCl2 (+) | LTC3331 primer pil girişi | 3,6 V / 1200 mAh | `blok-diyagrami.md:18,21`; `bom.csv:7`; `enerji-ve-termal-hesap.md:40` | DOĞRULANMADI |
| `VSTORE` | LTC3331 ↔ süperkapasitör (çift yön) | Murata DMF3Z5R5H474M3DTA0, 100 mF | 3,3 V'a şarj edilir | `blok-diyagrami.md:17,22`; `enerji-ve-termal-hesap.md:53`; `bom.csv:8` | DOĞRULANMADI |
| `VDD_3V0` | LTC3331 buck çıkışı | nRF52833 VDD, TMP117, SHT40, I2C pull-up'ları | 3,0 V regüle | `blok-diyagrami.md:23`; `io-tablosu.md:16` | DOĞRULANMADI |
| `GND` | — | Tüm bloklar, ortak toprak düzlemi | 0 V | `io-tablosu.md:17` | — |

**Kasten yazılmadı:** yukarıdaki netlerin LTC3331'in **hangi ayağına** gideceği. LTC3331'in
ayak adları/numaraları depoda hiçbir yerde geçmiyor; yazsaydık veri sayfası uydurmuş olurduk.

---

## 2. Hibrit güç — hangi kaynak ne zaman devreye girer

Aşağıdaki tablo `enerji-ve-termal-hesap.md` §3'ün sayılarını **olduğu gibi** taşır. Yeni eşik,
yeni verim, yeni geçiş süresi **üretilmemiştir**.

| Fider akımı (bara) | Baskın kaynak | Depodaki sayı | Dayanak | Durum |
|---|---|---|---|---|
| Akım yok / çok düşük | Tadiran LiSOCl2 pil | Hasatsız en kötü senaryoda ömür **≈ 5,74 yıl** (1020 mAh kullanılabilir ÷ ~177,5 mAh/yıl) | `enerji-ve-termal-hesap.md:41–45` | Hesap — ölçüm değil |
| **I > 15 A** | Hasat trafosu + LTC3331 devreye girer | Sekonderde **en az 25 µW** indüklenir; LTC3331 süperkapasitörü **3,3 V**'a şarj eder | `enerji-ve-termal-hesap.md:52–53` | Hesap/kabul — ölçülmedi |
| **I ≥ 20 A** | Yalnızca manyetik hasat | Ortalama **56,7 µW** gücün tamamı manyetik alandan; **pilden 0,0 µA** | `enerji-ve-termal-hesap.md:54–55` | Hesap/kabul — ölçülmedi |

**Bu tabloda olmayan ve hiçbir dosyada yazılı olmayanlar** (doğrulama listesine taşındı):
devreye girme/çıkma **histerezisi**, kaynak değişimi sırasındaki **geçiş süresi ve gerilim çökmesi**,
süperkapasitörün pile geri düşme eşiği, ve 15 A eşiğinin trafonun **1:1000 sarım oranından**
(`bom.csv:6`) nasıl türetildiği — oran BOM'da var, türetme hiçbir dosyada yok.

### 2.1 Enerji bütçesi (10 saniyelik çevrim) — taşınan tablo

| Aşama | Süre | Akım @ 3,0 V | Enerji | Dayanak |
|---|---:|---:|---:|---|
| Derin uyku (RTC aktif, RAM retention) | 9,95 s | 1,8 µA | 17,91 µAs | `enerji-ve-termal-hesap.md:32` |
| Sensör okuma (TMP117 + SHT40, I2C) | 15 ms | 0,65 mA | 9,75 µAs | `enerji-ve-termal-hesap.md:33` |
| AES-128 şifreleme + paket hazırlama | 5 ms | 4,2 mA | 21,00 µAs | `enerji-ve-termal-hesap.md:34` |
| RF iletimi (+4 dBm BLE 5.0 TX) | 5 ms | 14,5 mA | 72,50 µAs | `enerji-ve-termal-hesap.md:35` |
| RX penceresi | 10 ms | 6,8 mA | 68,00 µAs | `enerji-ve-termal-hesap.md:36` |
| **Toplam** | **10,0 s** | **ort. 18,9 µA** | **189,16 µAs** | `enerji-ve-termal-hesap.md:37` |

> Bu tabloda **gerilim bölücü sızıntısı, pull-up direnci akımı ve LTC3331 kendi sükûnet akımı
> için satır yoktur.** Yani 18,9 µA ortalama **yalnızca sayılan beş kalemin** toplamıdır;
> gerçek ortalamanın bunun üzerinde çıkıp çıkmadığı **bu teslimde hesaplanmadı.**

---

## 3. Sensör arayüzü netleri (I2C)

| Net | Kaynak (sürücü) | Hedef(ler) | Elektriksel not | Dayanak | Durum |
|---|---|---|---|---|---|
| `I2C_SDA` | Çift yön (MCU master) | nRF52833 `P0.26` ↔ TMP117 SDA ↔ SHT40 SDA | 4,7 kΩ pull-up → `VDD_3V0`, 400 kHz | `io-tablosu.md:10`; `blok-diyagrami.md:36,37` | Pin adı veri sayfasına karşı **DOĞRULANMADI** |
| `I2C_SCL` | nRF52833 `P0.27` (çıkış) | TMP117 SCL, SHT40 SCL | 4,7 kΩ pull-up → `VDD_3V0`, 400 kHz | `io-tablosu.md:11` | Pin adı **DOĞRULANMADI** |
| `TMP_ALERT` | TMP117 ALERT çıkışı | nRF52833 `P0.11` (giriş) | Yüksek sıcaklık donanım kesmesi | `io-tablosu.md:12` | **DOĞRULANMADI** |

**I2C adres ve örnekleme** (taşınan):

| Cihaz | Adres | Ölçtüğü | Örnekleme | Dayanak |
|---|:---:|---|:---:|---|
| TI TMP117AIDRVR | `0x48` | Bara noktasal sıcaklığı, 16-bit | 10 s | `io-tablosu.md:25`; `bom.csv:3` |
| Sensirion SHT40-AD1B | `0x44` | Pano içi bağıl nem + sıcaklık, 16-bit | 10 s | `io-tablosu.md:26`; `bom.csv:4` |

**Isıl yol (elektriksel net değildir, ama bağlantı tablosuna aittir):**
Bara bakır yüzeyi → Bergquist Sil-Pad TSP 1600 (6 W/mK) → TMP117 gövdesi
(`blok-diyagrami.md:9,11,29`; `bom.csv:12`). Bu yolun **ısıl direnci ölçülmedi**; sensörün kendi
ısıl kütlesinin ölçümü saptırıp saptırmadığı bilinmiyor (`../../docs/19-tedas-sartname-uyumu.md:62`).

---

## 4. Güç izleme ve durum netleri

| Net | Kaynak | Hedef | Not | Dayanak | Durum |
|---|---|---|---|---|---|
| `VBAT_SENSE` | Pil hattı üzerindeki 1/2 gerilim bölücü | nRF52833 `P0.02` / `AIN0` (analog giriş) | Pil gerilimi ölçümü | `io-tablosu.md:7` | Bölücü direnç değerleri **hiçbir dosyada yok** |
| `VHARVEST_SENSE` | Hasat hattı | nRF52833 `P0.03` / `AIN1` (analog giriş) | Hasat hattı gerilimi | `io-tablosu.md:8` | Bölücü var mı, oranı ne — **yazılı değil** |
| `PGV_INT` | LTC3331 güç-iyi (Power Good) çıkışı | nRF52833 `P0.04` | Kesme pini | `io-tablosu.md:9`; `blok-diyagrami.md:38` | **Yön çelişkisi** — bkz. Bölüm 8, satır 3 |

---

## 5. RF ve anten netleri

| Net | Kaynak | Hedef | Not | Dayanak | Durum |
|---|---|---|---|---|---|
| `ANT_FEED` | nRF52833 anten çıkışı | Johanson Technology 2450AT18A100E seramik çip anten | 2,4 GHz BLE 5.0 / 802.15.4 | `blok-diyagrami.md:34,39`; `bom.csv:9` | **Eşleme ağı (L/C) BOM'da ayrı kalem değil** |
| `ANT_TUNE` | RF katı | nRF52833 `P0.29` / `AIN5` (analog) | "Empedans izleme / RF tanı" | `io-tablosu.md:13` | BOM'da bunu gerçekleyen bileşen **yok** — bkz. Bölüm 8, satır 4 |

**Kablosuz bağlantı (kablo/konnektör yoktur):**

| Uç | Ne | Dayanak |
|---|---|---|
| Gönderen | Sensör düğümü anteni, AES-128 CCM şifreli paket | `blok-diyagrami.md:42,54,55` |
| Alan | Pano Beyni'ndeki **nRF52840 tabanlı harici 802.15.4/BLE modülü** | `../pano-beyni/blok-diyagrami.md:41` |
| Pano Beyni anteni | `RADIO_ANT` (U.FL), pano içi, dış antene gerek yok | `../pano-beyni/io-tablosu.md:14` |

> Düğüm ile Pano Beyni arasında **hiç kablo yoktur**; bu bilinçli bir karardır
> (`README.md:19` — 24–30 noktaya kablo çekmek izolasyon aralığını bozar).
> **Menzil, paket kaybı ve metal kabin içi zayıflama ÖLÇÜLMEDİ**
> (`../../docs/19-tedas-sartname-uyumu.md:97`).

---

## 6. Programlama / üretim test netleri

| Net | Yön | Karşı taraf | Dayanak | Durum |
|---|---|---|---|---|
| `SWDIO` | Çift yön | SWD test noktası (üretim programlama / hata ayıklama) | `io-tablosu.md:14` | — |
| `SWDCLK` | Giriş | SWD test noktası | `io-tablosu.md:15` | — |
| `VDD_3V0`, `GND` | — | Programlayıcı referansı için aynı test alanı | `io-tablosu.md:16,17` | — |

**Bu bölümün boşlukları:** BOM'da programlama **konnektörü kalemi yoktur** (`bom.csv`), yani
bağlantı yaylı pin (pogo) test pedi varsayımıyla kurgulanmıştır — ama bu varsayım hiçbir dosyada
yazılı değildir. **Reset hattı** hiçbir dosyada tanımlı değildir.

---

## 7. Bu tabloda KASTEN yazılmayanlar

| Yazılmayan | Neden |
|---|---|
| Fiziksel paket pin numaraları, paket ölçüleri, mutlak maksimum değerler | Depoda **hiçbir bileşenin veri sayfası yok** |
| Besleme dekuplaj kondansatörleri | `bom.csv`'de ayrı kalem yok; değer uydurmak yerine boşluk olarak kaydedildi |
| RF eşleme ağı L/C değerleri ve anten açıklık (keep-out) alanı | Aynı — BOM'da yok, veri sayfası yok |
| **Düşük frekans saat kaynağı** (32,768 kHz kristal mi, dahili RC mi) | BOM'da kristal/osilatör kalemi **yok**, ama 9,95 s derin uyku bir RTC gerektiriyor (`enerji-ve-termal-hesap.md:32`). Seçim **yapılmamıştır** |
| **Güvenli eleman (secure element)** | `blok-diyagrami.md:54` her düğümün EUI-64 ve 128-bit AES kök anahtarı taşıdığını söyler; `bom.csv`'de Pano Beyni'ndeki ATECC608A benzeri bir eleman **yoktur** (`../pano-beyni/io-tablosu.md:22`). Anahtarın nerede durduğu **yazılı değil** |
| Bara izolasyon bariyerinin mekanik kotları | `blok-diyagrami.md:52` "3 mm katı dielektrik bariyer" der; bu bir tasarım hedefidir, **dielektrik testi yapılmadı** |

---

## 8. Depo içi çelişkiler — bu dosya çözmez, kaydeder

| # | Çelişki | A diyor ki | B diyor ki | Durum |
|---|---|---|---|---|
| 1 | **Bileşen sıcaklık sınıfı** | `README.md:18`: gövde ve komponentler bu sıcaklığa dayanıklı seçilmiştir, **−40 … +125 °C** | Aynı aralığı kart üstündeki **her bileşen karşılamıyor**: LTC3331 (`enerji-ve-termal-hesap.md:20`), TMP117 (−55 … +150 °C, `enerji-ve-termal-hesap.md:18`) ve SHT40-AD1B (−40 … +125 °C, `blok-diyagrami.md:28`) karşılar. Buna karşılık nRF52833 **−40 … +105 °C** (`enerji-ve-termal-hesap.md:19`, `bom.csv:2`), pilin seçilen varyantı **−55 … +85 °C** (`:21`, `bom.csv:7`), gövde RTI **115 °C** (`:15`) | README'deki "−40 … +125 °C" ifadesi **tüm komponentler için geçerli değildir**; düğümün sıcaklık sınıfını en düşük üye (pil, +85 °C) belirler |
| 2 | **Pil ömrü** | `README.md:20` "10+ yıl raf ömürlü"; `enerji-ve-termal-hesap.md:56` "saha kullanım ömrü 15+ yıl" | `enerji-ve-termal-hesap.md:45` hasatsız senaryoda **≈ 5,74 yıl** | Üç farklı sayı üç farklı varsayıma ait; hangisinin hangi koşulda geçerli olduğu **tek yerde yazılı değil** |
| 3 | **`PGV_INT` yönü** | `io-tablosu.md:9` sinyali **"Dijital Çıkış"** olarak listeliyor | `blok-diyagrami.md:38` okun yönü **LTC3331 → MCU** | MCU tarafında bunun bir **giriş** olması gerekir; I/O tablosundaki yön alanı düzeltilmeli |
| 4 | **`ANT_TUNE`** | `io-tablosu.md:13` "empedans izleme / RF tanı" için bir analog pin ayırıyor | `bom.csv`'de yönlü kuplör, detektör diyot veya ayarlanabilir eleman **yok** | Pin ayrılmış ama **devresi yok**; ya kaldırılmalı ya da BOM'a karşılığı eklenmeli |
| 5 | **Gövde içi tepe sıcaklığı** | `enerji-ve-termal-hesap.md:21` "gövde içi tepe sıcaklığı **+68 °C**'yi geçmez" | Bu değerin **hangi yöntemle** (analitik direnç ağı mı, simülasyon mu) bulunduğu yazılı değil; ölçüm yok | Bir **kabul**tür, ölçüm değildir; pilin −55…+85 °C sınırı buna dayanıyor |
| 6 | **Hasat trafosu parçası** | `blok-diyagrami.md:10` "Minyatür Split-Core Hasat Trafosu (Murata)" | `bom.csv:6` "Murata / **Custom** Split-Core CT (1:1000)" — gerçek üretici kodu **yok** | 25 µW iddiası (`enerji-ve-termal-hesap.md:52`) **hiçbir somut parçaya bağlı değil** |
| 7 | **Bara sıcaklığı türetimi** | `README.md:18` 35 °C ortam + 70 K → 105 °C | `enerji-ve-termal-hesap.md:10` ortam **maks. +45 °C**, pano içi yerel hava **+55 °C** kabul ediliyor, ama `:11` yine 35 °C + 70 K kullanıyor | İki farklı ortam sıcaklığı aynı dosyada; hangi ortam değerinin tasarım noktası olduğu **belirsiz** |

---

## 9. Layout öncesi doğrulanması gerekenler

Aşağıdakilerin **hiçbiri bu teslimde yapılmamıştır.** Liste, kart çizimine başlamadan önce
kapatılması gereken açık kalemlerdir.

1. **Veri sayfalarının temini ve pin eşlemesi.** nRF52833, LTC3331, TMP117, SHT40, TL-5902,
   DMF3Z5R5H474M3DTA0 ve 2450AT18A100E için veri sayfası çekilmeli; `io-tablosu.md`'deki
   `P0.xx` / `AIN` atamaları ve bu dosyadaki tüm işlevsel ad eşlemeleri **veri sayfasına karşı
   doğrulanmalıdır.** Fiziksel pin numaraları ancak bu adımdan sonra yazılabilir.
2. **LTC3331 ayak eşlemesi.** Bölüm 1'deki dört güç netinin hangi ayağa gideceği
   (AC hasat girişi, primer pil girişi, depolama, buck çıkışı) belirlenmeli.
3. **Hibrit geçiş davranışı.** Histerezis, geçiş süresi, geçiş anındaki gerilim çökmesi ve
   süperkapasitörden pile geri düşme eşiği tanımlanmalı; 15 A / 20 A eşikleri (Bölüm 2)
   **trafo sarım oranı ve yük empedansıyla birlikte** yeniden kurulmalı.
4. **Hasat trafosunun gerçek parçaya bağlanması.** `bom.csv:6` "Custom" diyor; 25 µW @ I > 15 A
   iddiası ancak seçilmiş bir parçayla ve bir ölçümle anlam kazanır.
5. **Sükûnet akımı bütçesi.** Gerilim bölücü sızıntısı, 4,7 kΩ pull-up'lar ve PMIC sükûnet akımı
   §2.1 tablosuna eklenmeli; 18,9 µA ortalamanın hâlâ geçerli olup olmadığı yeniden hesaplanmalı.
6. **LF saat kaynağı kararı.** Derin uykudaki 10 s uyandırma için kristal mi dahili RC mi
   kullanılacağı seçilmeli; kristal seçilirse BOM'a satır eklenmeli.
7. **Anahtar saklama.** `blok-diyagrami.md:54`'teki AES kök anahtarının MCU flash'ında mı yoksa
   ayrı bir güvenli elemanda mı duracağı kararlaştırılmalı ve BOM'a yansıtılmalı.
8. **RF eşleme ağı ve anten açıklığı.** Eşleme L/C değerleri, referans düzlem kesiği ve
   anten keep-out alanı anten veri sayfasından çıkarılmalı; **metal pano içinde menzil ölçülmeli**
   (`../../docs/19-tedas-sartname-uyumu.md:97`).
9. **Isıl yol doğrulaması.** Bara → silikon ped → TMP117 ısıl direnci ölçülmeli; `+68 °C` gövde
   içi tepe kabulü (Bölüm 8, satır 5) sınanmalı — pilin sıcaklık sınıfı buna bağlıdır.
10. **Yalıtım koordinasyonu.** `blok-diyagrami.md:52`'deki 3 mm bariyer ve 6 kV ped iddiası
    IEC 60664-1 kapsamında **açıklık ve kaçak yolu hesabıyla** desteklenmeli; dielektrik dayanım
    ve darbe testi yapılmalı (bu teslimde **yapılmadı**).
11. **Montajın panoya etkisi.** Sensörün bara bağlantısının ısıl direncini veya montaj kuvvetinin
    bağlantıyı gevşetip gevşetmediği açık kalemdir (`../../docs/19-tedas-sartname-uyumu.md:56,62`).
12. **Bölüm 8'deki yedi çelişkinin kapatılması** — özellikle 1 (sıcaklık sınıfı), 3 (`PGV_INT`
    yönü) ve 4 (`ANT_TUNE`), çünkü bunlar doğrudan şemayı değiştirir.

---

## 10. Değişiklik günlüğü

| Tarih | Değişiklik |
|---|---|
| 20 Eylül 2026 | İlk sürüm. Mevcut dört dosyadaki bağlantılar tek tabloya toplandı; yedi depo içi çelişki ve on iki açık doğrulama kalemi kaydedildi. **Hiçbir yeni sayı, pin numarası veya standart madde numarası üretilmedi.** |
