# Sensör Düğümü Sistem Blok Diyagramı ve Mimarisi

**Sahip:** Kişi C · **Hedef:** Bara ve Terminal Sıcaklık/Nem İzleme Düğümü (25x40 mm PCB)

```mermaid
flowchart TB
    subgraph BaraArayuzu["Bara Temas Arayüzü (105°C Dayanımlı)"]
        BARA[("Bara Bakır Yüzeyi")]
        THERMAL_PAD["Yüksek Isıl İletkenli Silikon Ped (6 W/mK)"]
        CT_COIL["Minyatür Split-Core Hasat Trafosu (Murata)"]
        BARA -->|Isı İletimi| THERMAL_PAD
        BARA -->|Manyetik Alan| CT_COIL
    end

    subgraph GucYonetimi["Güç Yönetimi ve Enerji Hasadı"]
        LTC3331["LTC3331 Harvester + Buck/Boost PMIC"]
        SUPERCAP["100mF 3.3V Düz Kapasitör"]
        BATTERY["Tadiran TL-5902 3.6V 1.2Ah LiSOCl2 (-55..+85°C)"]
        
        CT_COIL -->|AC İndüklenen Akım| LTC3331
        BATTERY -->|Yedek Primer Pil| LTC3331
        LTC3331 <-->|Enerji Depolama| SUPERCAP
        LTC3331 -->|3.0V Regüle VDD| MCU
    end

    subgraph Sensorler["Hassas Endüstriyel Sensörler"]
        TMP117["TI TMP117AIDRVR\n(Bara Sıcaklık ±0.1°C, -55..+150°C)"]
        SHT40["Sensirion SHT40-AD1B\n(Ortam Nem ±1.5% RH, -40..+125°C)"]
        THERMAL_PAD -->|Doğrudan Termal Temas| TMP117
    end

    subgraph MCU_RF["İşlemci ve Radyo Çekirdeği"]
        MCU["Nordic nRF52833\n(ARM Cortex-M4F 64MHz, 128KB RAM, 512KB Flash)"]
        ANT["2.4 GHz Seramik Çip Anten (Johanson 2450AT)"]
        
        TMP117 -->|I2C (0x48)| MCU
        SHT40 -->|I2C (0x44)| MCU
        LTC3331 -->|PGV / Pil Voltajı Analog| MCU
        MCU -->|2.4GHz BLE 5.0 / 802.15.4| ANT
    end

    ANT -.->|Şifreli Paket (AES-128 CCM)| KENAR["Pano Beyni (ESP32-S3 Kenar Kontrolcü)"]
```

---

## Fiziksel ve Elektriksel İzolasyon Prensipleri

1. **IEC 60664-1 Yalıtım Koordinasyonu:**
   - Bara anma gerilimi: 1 kV izolasyon, darbe dayanımı 6 kV (Kategori III).
   - Sensör düğümü gövdesi UL94 V-0 sınıfı alev geciktirici Lexan 940A polikarbonattan üretilmiştir.
   - Bara ile PCB devre elemanları arasında 3 mm katı dielektrik bariyer ve 6 kV izolasyon dayanımlı silikon ped bulunur.
2. **Kablosuz Ağ Güvenliği:**
   - Her düğüm fabrikasyon EUI-64 adresine ve önceden tanımlanmış 128-bit AES kök anahtarına sahiptir.
   - Pano Beyni ile iletişim AES-128 CCM ile şifreli ve replay korumalıdır.
3. **Mekanik Montaj:**
   - Düğüm, baraya yüksek sıcaklığa dayanıklı paslanmaz çelik/naylon-66 klemens kayışı veya yüksek güçlü Neodimyum (N52H, 120°C dayanımlı) manyetik klips ile alet kullanmadan 15 saniyede takılır.
