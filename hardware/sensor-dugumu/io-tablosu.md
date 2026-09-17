# Sensör Düğümü I/O ve Pin Haritası

**Mikrodenetleyici:** Nordic Semiconductor nRF52833 (QFN-40 / 7x7 mm)

| Pin No | Pin Adı | Tip | Sinyal Adı | Bağlı Blok | Açıklama |
|---|---|:---:|---|---|---|
| P0.02 | AIN0 | Analog | `VBAT_SENSE` | LTC3331 Pil İzleme | 1/2 gerilim bölücü ile pil gerilimi ölçümü |
| P0.03 | AIN1 | Analog | `VHARVEST_SENSE` | LTC3331 Hasat Gerilimi | Hasat edilen enerji hattının voltajı |
| P0.04 | DIO | Dijital Çıkış | `PGV_INT` | LTC3331 Güç Durumu | Güç iyi (Power Good) kesme pini |
| P0.26 | I2C_SDA | Dijital Giriş/Çıkış | `I2C_SDA` | TMP117 & SHT40 | 4.7 kΩ pull-up ile 400 kHz I2C veri |
| P0.27 | I2C_SCL | Dijital Çıkış | `I2C_SCL` | TMP117 & SHT40 | 4.7 kΩ pull-up ile 400 kHz I2C saat |
| P0.11 | DIO | Dijital Giriş | `TMP_ALERT` | TMP117 Alert | Yüksek sıcaklık anlık donanım kesmesi |
| P0.29 | AIN5 | Analog | `ANT_TUNE` | RF Katı | Empedans izleme / RF tanı |
| SWDIO | SWDIO | Debug | `SWDIO` | SWD Test Noktası | Seri tel hata ayıklama / üretim programlama |
| SWDCLK| SWDCLK| Debug | `SWDCLK` | SWD Test Noktası | Programlama saati |
| VDD   | POWER | Besleme | `VDD_3V0` | LTC3331 Buck Çıkışı| 3.0V temiz regüle sistem beslemesi |
| VSS   | GND   | Güç | `GND` | Sistem Şasisi | Ortak toprak düzlemi |

---

## I2C Cihaz Adresleme Tablosu

| Cihaz | Standart I2C Adresi | Fonksiyon | Örnekleme Hızı |
|---|:---:|---|:---:|
| TI TMP117 | `0x48` | Bara Noktasal Sıcaklığı (16-bit, 0.0078125 °C çözünürlük) | 10 saniyede bir |
| Sensirion SHT40 | `0x44` | Pano İçi Bağıl Nem ve Sıcaklık (16-bit) | 10 saniyede bir |
