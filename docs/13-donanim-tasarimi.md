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
E = 1/2 * C * (V_dolu^2 - V_min^2) = 0,5 * 5 F * (5,4^2 - 3,0^2) V^2 ≈ 47,3 J
Sürekli 0,6 A @ 5V ≈ 3 W tüketimde: t = E / P ≈ 47,3 / 3 ≈ 15,8 saniye
```

15–16 saniye, MQTT bağlantısının kapanmasını algılayıp son bir "besleme kesildi" (`ALM-LASTGASP`)
mesajı yayınlamak için yeterlidir; radyo/hücresel gönderim önceliklendirilir, diğer görevler
(sensör okuma) bu sürede askıya alınır.

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
IEC 60664-1 Tablo F.2/F.4'ten okunur; sensör gövdesinin bara/pabuç üzerine montajı **hiçbir
şekilde mevcut clearance/creepage mesafesini azaltmamalıdır** (kurulum kontrol listesi,
`docs/08`).

## 5. Çevresel dayanım özeti

| Risk | Tasarım önlemi |
|---|---|
| Sıcaklık (−25…+70 °C bara yakını) | Kontrolcü elektroniği endüstriyel sınıf (−40…+85 °C) bileşenler; kart konformal kaplamalı |
| Nem/yoğuşma (harici panoda %100 BN) | Akrilik konformal kaplama (IPC-CC-830), kutu içi nem alıcı |
| Kirlilik (Düzey II–III) | V-0 polikarbonat kutu (`din-kutu.scad`), IP20 dahili |
| Titreşim/deprem (0,5 g) | DIN ray klipsi + kilitli konnektörler (I/O tablosu, tüm konnektörler vidalı/fişli) |
| Yangın dayanımı | Tüm plastikler UL94/IEC 60695-11-10 V-0 (BOM'daki kutu ve konnektör seçimleri) |

## 6. Mekanik

DIN ray kutusu parametrik OpenSCAD kaynağı: [`hardware/mekanik/din-kutu.scad`](../hardware/mekanik/din-kutu.scad)
(125×92×60 mm, Fibox ARCA 92/125 sınıfı referans alınarak). **STL bu teslimde üretilmedi** — bu
geliştirme ortamında `openscad` kurulu değildi; dosya, OpenSCAD kurulu bir makinede doğrudan
`openscad -o din-kutu.stl din-kutu.scad` ile STL'e çevrilebilir durumdadır (`STATUS.md` karar #4).
