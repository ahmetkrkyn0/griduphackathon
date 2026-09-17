# hardware/sensor-dugumu/ — Bara Üzeri Kablosuz Sensör Düğümü

**Sahip:** Kişi C · **Sürüm:** v1.0 (17 Eylül 2026) · **Standart Uyumu:** TEDAŞ MLZ/2020-069, IEC 60664-1, IEC 61439-1

| Dosya | İçerik |
|---|---|
| [`blok-diyagrami.md`](blok-diyagrami.md) | Sistem blok diyagramı (Mermaid), RF anten/eşleme, enerji hasadı, izolasyon sınırları |
| [`io-tablosu.md`](io-tablosu.md) | MCU pinout, sensör veri yolları (I2C), şarj yönetimi ve SWD programlama arayüzü |
| [`bom.csv`](bom.csv) | Endüstriyel malzeme listesi, gerçek üretici parça kodları, sıcaklık sınıfları, 1 ve 1.000 adet fiyatları |
| [`enerji-ve-termal-hesap.md`](enerji-ve-termal-hesap.md) | 105°C bara sıcaklık dayanımı analizi, 10 yıllık LiSOCl2 pil ömrü ve manyetik alan enerji hasat eşiği hesabı |

---

## Tasarım Özeti ve Saha Zorlukları Çözümü

Alçak gerilim dağıtım panolarında bara bağlantı noktaları en yüksek termal ve elektromanyetik stresin yaşandığı bölgelerdir. TEDAŞ şartnamesine ve IEC 61439-1'e göre:
1. **Bara Sıcaklığı:** Normal çalışma koşullarında bara sıcaklık artışı 70 K, ortam 35°C iken bara mutlak sıcaklığı **105°C**'ye ulaşabilir. Düğüm gövdesi ve komponentleri bu sıcaklığa sürekli dayanıklı seçilmiştir (-40°C .. +125°C).
2. **Kablo Karmaşasını Önleme:** Pano içinde 24-30 ayrı noktaya kablo çekmek izolasyon aralığını bozar ve ark riskini artırır. Bu nedenle sensör düğümleri **kablosuz (2.4 GHz BLE 5.0 / 802.15.4)** çalışır.
3. **Hibrit Güç Kaynağı:** Düğüm, fiderden akım geçerken (I > 15 A) dahili minyatür split-core akım trafosu üzerinden **manyetik enerji hasadı (Energy Harvesting - LTC3331)** ile beslenir. Akım kesildiğinde veya çok düşük olduğunda ise 10+ yıl raf ömürlü **Tadiran LiSOCl2** pil devreye girer.
