# HF Analog Ön Yüz (AFE) ve IEC 60270 Hesap Raporu

**Hazırlayan:** Kişi C · **Tarih:** 17 Eylül 2026 · **Kapsam:** Yüksek Frekans Kısmi Deşarj ve Ark Erken Tespiti

---

## 1. Bant Geçiren Filtre Tasarımı (100 kHz – 20 MHz)

### 1.1 Şebeke Frekansı ve Harmoniklerinin Bastırılması
Alçak gerilim panolarında ana bara akımı (50 Hz) yüzlerce amperdir ve fiderlerde sürücülerden kaynaklı harmonikler (150 Hz, 250 Hz, 2 kHz PWM anahtarlama) mevcuttur.
* **Gereksinim:** 50 Hz ana akımın algılama katına sızmasını tamamen engellemek ($> 80\text{ dB}$ sönümleme).
* **Filtre Tipi:** 5. Derece Pasif LC Chebyshev Yüksek Geçiren + 3. Derece Alçak Geçiren Bant Filtre kombinasyonu.
* **Alt Kesim Frekansı ($f_{c,\text{low}}$):** $100\text{ kHz}$.
* **Üst Kesim Frekansı ($f_{c,\text{high}}$):** $20\text{ MHz}$.

$$\text{50 Hz Frekanstaki Zayıflama:} \quad A(50\text{ Hz}) \approx -20 \cdot n \cdot \log_{10}\left(\frac{100\text{ kHz}}{50\text{ Hz}}\right) \approx -100\text{ dB}$$

Bu sayede 1600 A nominal bara akımı geçse dahi 50 Hz sızıntısı mikrovolt seviyesinin altında kalarak sıfır yanlış tetikleme sağlar.

---

## 2. IEC 60270 Yük Kalibrasyonu ve Dinamik Aralık

Kısmi deşarj olayları pikoCoulomb ($\text{pC}$) cinsinden ifade edilir:
$$q = \int i(t) \, dt$$

* **Darbe Genişliği:** $\tau \approx 5\text{ ns} .. 40\text{ ns}$.
* **Algılama Aralığı:** $20\text{ pC} .. 5000\text{ pC}$.
* **AD8307 Logaritmik Dedektör:**
  - Giriş dinamik aralığı: $-75\text{ dBm} .. +17\text{ dBm}$ ($92\text{ dB}$).
  - Eğim: $25\text{ mV/dB}$.
  - Doğrusallaştırılmış çıkış gerilimi:
    $$V_{\text{out}} = 0.025 \cdot \left(P_{\text{dBm}} + 84\right)$$

---

## 3. Ark Parlaması (S4) ile Yüzey Kısmi Deşarjı (PD) Ayrımı

| Özellik | Yüzey Kısmi Deşarjı (Korona / Nemli Toz) | Arıza Arkı (Flashover / Seri Ark) |
|---|---|---|
| **Darbe Tekrarlama Frekansı** | Şebeke geriliminin tepe anlarında ($50\text{ Hz}$ periyotlu demetler) | Sürekli, kaotik ve geniş bantlı gürültü |
| **Darbe Süresi** | Çok kısa ($<50\text{ ns}$) | Uzun süreli sürekli plazma akımı ($>1\text{ ms}$) |
| **TVOC Gaz Emisyonu** | Sıfır veya ihmal edilebilir | Yüksek (İzolasyon yanması nedeniyle TVOC fırlar) |
| **Işık Parlaması (Optik)** | Gözle görünmez | Çok yüksek lümen flaş patlaması |
| **Algoritma Kararı** | `ALM-PD-WARN` (Bakım planlama hipotezi) | `ALM-ARC-TRIP` (Anında 10 ms kesici açtırma) |
