# hardware/pd-karti/ — Kısmi Deşarj (PD) ve HF Algılama Modülü

**Sahip:** Kişi C · **Sürüm:** v1.0 (17 Eylül 2026) · **Standart Uyumu:** IEC 60270 (High-voltage test techniques — Partial discharge measurements)

| Dosya | İçerik |
|---|---|
| [`blok-diyagrami.md`](blok-diyagrami.md) | Sistem blok diyagramı (Mermaid), HFCT algılayıcı, analog ön yüz (AFE) ve dijitalleştirme |
| [`io-tablosu.md`](io-tablosu.md) | Pano Beyni (ESP32-S3) bağlantı konnektörü, SPI veri hatları ve hızlı tetikleme kesmesi |
| [`bom.csv`](bom.csv) | HF analog ve RF komponent listesi, gerçek üretici parça kodları, 1 ve 1.000 adet maliyetleri |
| [`hf-analog-frontend.md`](hf-analog-frontend.md) | 100 kHz - 20 MHz bant geçiren filtre hesabı, 50 Hz şebeke frekansı bastırması (>80 dB) ve IEC 60270 pC eşleme |

---

## Tasarım Amacı ve Çalışma Prensibi

Dağıtım panolarında izolasyon delinmesi ve ark arızaları ani bir felaket şeklinde patlamadan önce günler hatta aylar boyunca **mikro-arklar ve kısmi deşarjlar (Partial Discharge - PD)** şeklinde sinyal verir.
* **Şebeke Gürültüsü Engeli:** 50 Hz ana harmonikler ve motor/sürücü anahtarlama gürültüleri alçak gerilim panolarında çok yüksektir.
* **Yüksek Frekans Ayrımı (HFCT):** Sistem, bara toprak hattına bağlanan ferrit nüveli yüksek frekans akım trafosu (HFCT) ile **100 kHz - 20 MHz** arasındaki nano-saniyelik darbe akımlarını izole eder.
* **Hızlı Eşik Tetikleme:** Logaritmik yükselteç (AD8307) ve 4.5 ns hızlı karşılaştırıcı (TLV3501) sayesinde arıza arkı parlamadan önce Pano Beyni'ne donanım seviyesinde alarm fırlatılır.
