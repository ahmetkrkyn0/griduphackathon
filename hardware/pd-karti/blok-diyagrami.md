# Kısmi Deşarj (PD) Kartı Sistem Blok Diyagramı

**Sahip:** Kişi C · **Modül:** Yüksek Hızlı Analog Ön Yüz (AFE) ve Kısmi Deşarj Dedektörü

```mermaid
flowchart LR
    subgraph Algilayici["Algılayıcı Sensör"]
        HFCT[("HFCT / Yüksek Frekans Akım Trafosu\n(TDK B64290 Nüve, 100 kHz - 20 MHz)")]
        TVS["Çift Yönlü TVS Diyot (Semtech RCLAMP0502A)\n(Transient & ESD Koruma)"]
        HFCT --> TVS
    end

    subgraph AnalogOnYuz["Analog Ön Yüz (AFE)"]
        BPF["Pasif LC 5. Derece Bant Geçiren Filtre\n(100 kHz - 20 MHz, 50 Hz Bastırma >80 dB)"]
        LNA["Ultra Düşük Gürültülü JFET Op-Amp\n(TI OPA656, 230 MHz GBW)"]
        LOGAMP["92 dB Logaritmik Dedektör / RSSI\n(Analog Devices AD8307ARZ)"]
        
        TVS --> BPF
        BPF --> LNA
        LNA --> LOGAMP
    end

    subgraph KararVeSayisallastirma["Tetikleme ve Sayısallaştırma"]
        COMP["Hızlı Karşılaştırıcı (TI TLV3501, 4.5 ns)\n(Lojik Darbe Tetikleme)"]
        ADC["12-bit 2 MSPS SAR ADC\n(TI ADS7049)"]
        DAC_REF["Referans Eşik Gerilimi (DAC)"]
        
        LOGAMP -->|Zarf Gerilimi| ADC
        LOGAMP -->|Hızlı Tepe Sinyali| COMP
        DAC_REF -->|Ayarlanabilir Eşik| COMP
    end

    subgraph Arayuz["Pano Beyni Bağlantısı (J10 Klemens)"]
        SPI_BUS[("Hızlı SPI Veri Yolu (20 MHz)\n(Darbe Genliği / Sayısı)")]
        TRIG_IRQ[("Donanım Kesme Pini (INT)\n(<10 ns Gecikme ile Ark Alarmı)")]
        
        ADC -->|SPI MISO| SPI_BUS
        COMP -->|Donanım Tetik| TRIG_IRQ
    end
```

---

## Modülün Çalışma Evreleri

1. **Darbe Tespiti:** Yalıtım çatlağından atlayan mikro-ark akımı (1 ns .. 50 ns genişliğinde) HFCT üzerinden geçer.
2. **Gürültü Ayıklama:** 50 Hz şebeke frekansı ve tristör anahtarlama harmonikleri (0 .. 50 kHz) 5. derece LC Chebyshev filtre ile 80 dB'den fazla sönümlenir.
3. **Logaritmik Sıkıştırma:** Sinyal genliği çok geniş dinamik aralığa sahip olduğu için (10 pC .. 10.000 pC arası), AD8307 logaritmik yükselteç ile $V_{\text{out}} = 25\text{ mV/dB}$ formatında zarfa dönüştürülür.
4. **Hızlı Alarm İletimi:** Önceden kalibre edilmiş pikovolt/pikoCoulomb seviyesini aşan bir olayda TLV3501 karşılaştırıcısı mikrosaniyeden kısa sürede Pano Beyni'nin harici kesme pinini tetikler.
