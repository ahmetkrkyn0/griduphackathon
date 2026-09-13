# Pano Beyni — I/O Tablosu (v1)

> **Sahip:** Kişi C · Kaynak: `blok-diyagrami.md`. Her pin: sinyal, yön, gerilim seviyesi,
> izolasyon sınırı, bağlandığı blok. Register/adres eşlemesi için bkz. `contracts/modbus-map.yaml`
> ve `docs/03-modbus-haritasi.md` (B'nin ürettiği doküman — bizim donanım haritamız o sözleşmeyi
> fiziksel olarak taşır).

| # | Pin / arayüz | Yön | Sinyal | Seviye | İzolasyon | Blok | Not |
|---|---|---|---|---|---|---|---|
| 1 | J1.1–2 | Giriş | 230 VAC L/N | 230 VAC | Ana izolasyon (SMPS) | Güç | Sigortalı fişli klemens, iç ihtiyaç devresi |
| 2 | J2.1–4 | Çıkış | 5 V, 3V3, GND | 5 V / 3V3 | — | Güç → tüm kart | SMPS + LDO çıkışı |
| 3 | RS485-A (J3.1–3) | Çift yön | A/B/GND, master | RS485 diferansiyel | 2,5 kV (ADM2587E) | RS485 #1 | MPR-53CS + TVOC-2 hattı, 120 Ω sonlandırma anahtarlı |
| 4 | RS485-B (J4.1–3) | Çift yön | A/B/GND, slave | RS485 diferansiyel | 2,5 kV (ADM2587E) | RS485 #2 | RTU/SCADA'ya sunulan harita |
| 5 | RADIO_ANT (U.FL) | Çıkış | 802.15.4/BLE anten | 2,4 GHz RF | — | Radyo modülü | Pano içi, dış antene gerek yok (metal kabin) |
| 6 | CELL_ANT (SMA, panel üstü) | Çıkış | Hücresel anten | RF | — | Modem | Şartname 2.2.8.1.iv harici anten çıkışından geçirilir |
| 7 | CELL_UART (J5.1–4) | Çift yön | TXD/RXD/PWR_EN/GND | 1,8 V UART | — | Modem konnektörü | Quectel EC200A M.2/UART arabirimi |
| 8 | RELAY1 (J6.1–2) | Çıkış | Kuru kontak, NO | 24 VDC / 1 A | Röle bobini galvanik ayrık | Röle #1 | Siren/flaşör (P1) |
| 9 | RELAY2 (J6.3–4) | Çıkış | Kuru kontak, NO | 24 VDC / 1 A | Röle bobini galvanik ayrık | Röle #2 | Isıtıcı/fan (otomatik aksiyon, insan onaysız — GK6 kapsamı dışı, koruma değil) |
| 10 | OPTO_IN1 (J7.1–2) | Giriş | Kapı reed kontağı | 24 VDC, PC817 | 5 kV (opto) | Optokuplör #1 | S5 kapı sensörü |
| 11 | OPTO_IN2–4 (J7.3–8) | Giriş | Harici kontak (yedek) | 24 VDC, PC817 | 5 kV (opto) | Optokuplör #2–4 | Kullanılmıyor (v1), gelecekteki genişleme |
| 12 | CT1–3 (J8.1–6) | Giriş | Fider akımı (ops., S8) | 0–5 A sekonder → burden → 0–3V3 | Ayrık çekirdek (galvanik temassız) | AT girişi + INA226 | AT sekonderi asla açık bırakılmaz (kurulum kuralı) |
| 13 | I2C (dahili) | Çift yön | SDA/SCL | 3V3 | — | MCU ↔ ATECC608A, INA226 | Kart üzeri, dışa çıkmaz |
| 14 | EXP_CONN (J9.1–10) | Çift yön | SPI/I2C + 3V3/5V | 3V3/5V | — | PD ön uç kartı konnektörü | OG eklentisi (rapor §3.7), boş bırakılabilir |
| 15 | DEBUG (J10, kapalı) | — | UART TX/RX, JTAG | 3V3 | — | MCU | **Üretimde lehim köprüsüyle devre dışı** (IEC 62443, "sahada gelen port yok") |
| 16 | DIN_GND | — | Koruma toprağı | — | — | Kutu | DIN ray üzerinden pano PE'sine |

**Toplam dış konnektör sayısı:** 10 (J1–J10), tamamı fişli/vidalı klemens; lehim/ek yok (şartname 2.2.10.1).

## Yalıtım koordinasyonu özeti

| Arayüz | Anma yalıtım gerilimi | Standart |
|---|---|---|
| RS485 ↔ MCU tarafı | 2500 Vrms, 1 dk | ADM2587E veri sayfası, IEC 60664-1 |
| Optokuplör girişi ↔ MCU | 5000 Vrms | PC817, IEC 60747-5-5 |
| SMPS giriş (230 VAC) ↔ çıkış (5V) | 3000 Vrms | IRM-10 veri sayfası, IEC 62368-1 |
| AT girişi ↔ MCU | Galvanik temassız (ayrık çekirdek) | — |
