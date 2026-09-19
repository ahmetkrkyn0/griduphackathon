# PD Kartı I/O ve Bağlantı Tablosu

**Bağlantı Türü:** Pano Beyni (ESP32-S3 Kenar Kontrolcü) ile J10 Klemens ve Dahili SPI Hattı

| Pin / Klemens | Sinyal Adı | Tip | Sinyal Seviyesi | Hedef / Kaynak | Fonksiyon |
|:---:|---|:---:|:---:|---|---|
| J1 (SMA) | `HF_IN+` | RF Analog | $\pm 5\text{ V}$ tepe (TVS korumalı) | HFCT Sekonderi | Kısmi deşarj darbe girişi (50 Ω empedans) |
| J1 (Kasa) | `GND_SHIELD` | Şasi | $0\text{ V}$ | HFCT Koaksiyel blendaj | Koruyucu şasi topraklaması |
| J2-1 | `VDD_5V` | Güç | $+5.0\text{ V}$ DC | Pano Beyni Güç Katı | Analog ön yüz (OPA656 / AD8307) beslemesi |
| J2-2 | `GND` | Güç | $0\text{ V}$ | Pano Beyni | Ortak analog ve dijital referans |
| J2-3 | `SPI_CS` | Dijital Giriş | $0\text{ V} .. 3.3\text{ V}$ | ESP32-S3 GPIO | ADS7049 ADC Chip Select (Aktif Düşük) |
| J2-4 | `SPI_SCK` | Dijital Giriş | $0\text{ V} .. 3.3\text{ V}$ | ESP32-S3 SPI CLK | SPI Saat Sinyali (20 MHz'e kadar) |
| J2-5 | `SPI_MISO`| Dijital Çıkış | $0\text{ V} .. 3.3\text{ V}$ | ESP32-S3 SPI MISO | 12-bit tepe genlik sayısal verisi |
| J2-6 | `TRIG_OUT`| Dijital Çıkış | $0\text{ V} .. 3.3\text{ V}$ (Push-Pull)| ESP32-S3 Harici Kesme | Donanım eşik aşım kesmesi (<10 ns gecikme) |
| J2-7 | `VREF_SET`| Analog Giriş | $0\text{ V} .. 3.3\text{ V}$ | ESP32-S3 DAC Çıkışı | Karşılaştırıcı donanımsal tetik eşiği referansı |
