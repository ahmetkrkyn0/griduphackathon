# Pano Beyni — Blok Diyagramı (v1)

> **Sahip:** Kişi C · **Durum:** taslak parça numaralarıyla, üretime hazırlanabilir seviyede.
> `docs/13-donanim-tasarimi.md`'nin kaynağıdır; I/O ayrıntısı `io-tablosu.md`'de, maliyet `bom.csv`'de.
>
> **Neden KiCad şeması yerine bu diyagram?** Bu ortamda internet erişimi ve KiCad kurulu bir makine
> yoktu; gerçek üretici sembollerini (ADM2587E, ATECC608A, …) barındıran doğrulanmış bir `.kicad_sch`
> üretmek riskli olurdu (açılmayan/bozuk sembol → "sahte şema" izlenimi, dürüstlük kuralına aykırı).
> Bu yüzden GK5'i ve "gerçek parça numarası" gereksinimini **blok diyagramı + I/O tablosu + BOM**
> üçlüsüyle karşılıyoruz — Rapor §10'un kendisinin izin verdiği asgari seviye ("en azından şema +
> blok diyagram + BOM + I/O tablosu"). KiCad dosyası ekip KiCad kurulu bir makineye geçtiğinde
> eklenecek; bu diyagramdaki bloklar ve net listesi doğrudan şemaya aktarılabilir haldedir.

## 1. Sistem blok diyagramı

```mermaid
flowchart TB
  subgraph PWR["Güç"]
    ACIN["İç ihtiyaç 230 VAC\n(sigortalı fişli klemens)"] --> PSU["İzoleli AC/DC SMPS\nMEAN WELL IRM-10-5\n5 V / 2 A"]
    PSU --> SUPERCAP["Süperkapasitör yedek\nEaton HB1840-2R7107\n10 F / 2.7 V x2 seri"]
    PSU --> V33["3V3 LDO\nTLV1117-33"]
    SUPERCAP -. "kesinti anında" .-> V33
  end

  subgraph MCU_BLOCK["İşlemci"]
    MCU["MCU modülü\nESP32-S3-WROOM-1-N8R8\n(Wi-Fi/BLE + 802.15.4 uyumlu harici radyo)"]
    SE["Güvenli eleman\nMicrochip ATECC608A-SSHDA\n(I2C, cihaz kimliği/imza)"]
    FLASH["Harici flash\nW25Q128JV, 16 MB\n(7 günlük halka tampon)"]
    MCU <--> SE
    MCU <--> FLASH
  end

  subgraph RS485["RS485 (izoleli, x2)"]
    RS1["RS485 #1 — master\nADM2587E (izoleli transceiver)\nMPR-53CS + TVOC-2 okur"]
    RS2["RS485 #2 — slave\nADM2587E (izoleli transceiver)\nRTU/SCADA'ya harita sunar"]
  end
  MCU <--> RS1
  MCU <--> RS2

  subgraph RADIO["Pano içi radyo"]
    RADIO_IC["802.15.4 / BLE modülü\nnRF52840 tabanlı harici modül\n(S1 kablosuz düğümlerle)"]
  end
  MCU <--> RADIO_IC

  subgraph CELL["Backhaul"]
    MODEM_CONN["Hücresel modem konnektörü\nQuectel EC200A (M.2/UART)\nözel APN"]
  end
  MCU <-- "UART" --> MODEM_CONN

  subgraph IO["Yerel I/O"]
    RELAY["2x röle çıkışı\nOMRON G5LE-1 + ULN2003 sürücü\nsiren/flaşör, ısıtıcı-fan"]
    OPTO["4x optokuplörlü giriş\nPC817, 24 VDC\nkapı, harici kontak"]
    CT["3x AT girişi\nburden direnci + INA226 (I2C ADC)\nfider akımı (ops.)"]
  end
  MCU --> RELAY
  OPTO --> MCU
  CT --> MCU

  EXP["PD ön uç kartı konnektörü\n(OG eklentisi, Bölüm 3.7)"] -.-> MCU

  V33 --> MCU
  V33 --> RS485
  V33 --> RADIO_IC
  V33 --> CT

  MCU -->|"RS485 #1"| MPR["ENTES MPR-53CS\n(enerji analizörü, mevcut)"]
  MCU -->|"RS485 #1"| TVOC["ABB TVOC-2\n(ark koruma, mevcut, SALT OKUNUR — GK6)"]
```

## 2. Fiziksel yerleşim (kutu)

- **Kutu:** DIN raya montajlı, V-0 (UL94) polikarbonat, IP20 (dahili pano içi — şartname 2.2.1.xiii).
- **Konum:** Pano üst bölmesinde, "Modem" kutusunun yanında (şartname 2.2.8.1.iv), ana baralardan
  ≥ 250 mm (bkz. `assets/ek2-14-pano.svg`, `docs/13` manyetik alan hesabı).
- **Genişlik:** ~4 modül (72 mm) DIN ray, 90 mm derinlik.
- **Konformal kaplama:** Kart, nem ve yoğuşmaya karşı akrilik konformal kaplamalı (IPC-CC-830).

## 3. Neden bu seçimler (GK5 — geliştirme kartı değil)

| Blok | Seçim | Neden geliştirme kartı değil |
|---|---|---|
| MCU | ESP32-S3-WROOM-1 **modülü** (kart üzerine SMD lehimli) | DevKit değil, üretim modülü; RAM/Flash entegre, dış bileşen minimum |
| Radyo | Harici nRF52840 modül (ayrı, düşük güçlü 802.15.4) | Metal kabin içi kısa menzil için ESP32'nin dahili 2,4 GHz'inden daha güvenilir aynı bantta çakışma önleme |
| Güvenlik | ATECC608A donanım güvenli eleman | Cihaz kimliği + imzalı OTA (IEC 62443) |
| İzolasyon | ADM2587E (dahili izoleli DC/DC + transceiver) | RS485 hattı pano şebekesinden galvanik izole (rapor 2.4 karşılıklı zarar önleme) |

## 4. Güç bütçesi (taslak)

| Blok | Tipik akım @ 3V3/5V | Not |
|---|---|---|
| MCU (aktif, radyo TX) | 240 mA @ 3V3 | Kısa darbeler, çoğu zaman uyku modu |
| MCU (uyku) | 8 mA @ 3V3 | 1 s döngü arası |
| 2x RS485 izoleli | 2 × 45 mA @ 5V | Sorgu sırasında |
| 802.15.4 modül | 20 mA @ 3V3 (RX) / 30 mA (TX) | |
| Hücresel modem | 250 mA ort. / 2 A tepe (TX burst) | SMPS tepe akımı buna göre seçildi (IRM-10, 2 A) |
| Röle sürücüleri (2x, aktifken) | 2 × 70 mA @ 24V bobin | Yalnızca tetiklendiğinde |
| **Toplam sürekli (tipik)** | **~0,6 A @ 5V ~3 W** | Süperkapasitör kesinti sonrası ≥ 20 s "son nefes" mesajı için yeterli boyutlandırılır (bkz. `docs/13` hesabı) |

## 5. Değişiklik günlüğü

- **v1 (14 Eylül 2026):** İlk taslak, TC2 Adım 3 kapsamında.
