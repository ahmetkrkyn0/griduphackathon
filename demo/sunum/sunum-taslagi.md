# Sunum Taslağı — ~12 dakika (rapor §8.2)

> **Sahip:** Kişi C · Format: PDF'e çevrilecek slayt destesi için konuşma metni + slayt notu.
> Sunucu rolleri: teknik fizik soruları A, entegrasyon/ölçek/güvenlik B, saha/maliyet/UX C
> (rapor §13 jüri soru bankası, T5.4).

## Slayt 1 — Problem ve saha hikâyesi (30 sn)

> "ADM ve GDZ'nin 26.210 trafosu var, bunların yalnızca ~%2-3'ü SCADA'dan uzaktan izleniyor.
> Bir 1600 kVA trafo yüzlerce aboneyi besliyor; gevşek bir bağlantı fark edilmeden haftalarca
> ısınıp bir gün arka dönüşebiliyor. Biz bunu, mutlak sıcaklık henüz normalken yakalayan bir
> sistem kurduk — donanım satın almadan, tamamen çalışan bir prototiple."

**Slayt içeriği:** Tek görsel — EK-II/14 pano taslağı üzerinde "Pano Beyni" konumu
(`assets/ek2-14-pano.svg`), başlık: "Pano/Hücre İçi Anomali Erken Uyarı Sistemi".

## Slayt 2 — 5 kritik içgörü (1 dk)

Rapor §0'daki 12 içgörüden en güçlü 5'i (`docs/01-problem-analizi.md`):

1. Verilen örnek veri rastgele gürültü — kendi fizik tabanlı sentetik veri üretecimiz var.
2. Panoda zaten iki akıllı cihaz var (MPR-53CS, TVOC-2) — yeni sensöre gerek yok.
3. TVOC-2 arkı zaten kesiyor; bizim katkımız **koruma sağlığını** izlemek.
4. AG panoda kısmi deşarj fiziksel olarak nadir — PD'yi OG eklentisi olarak konumlandırdık.
5. WhatsApp On-Premises API kapandı — birincil kanal tamamen on-prem GSM SMS.

## Slayt 3 — Donanımsızlık: bilinçli bir mühendislik kararı (güçlü konumlandırma)

> **Bu slayt açıkça ve güçlü biçimde donanımsızlığı bir eksiklik değil, bir karar olarak sunar**
> (PLAN.md Bölüm C). Beş kanıt (DH1–DH5):

| Kanıt | Mesaj |
|---|---|
| Üretilebilir donanım tasarımı (blok diyagram + I/O + BOM, gerçek parça numaraları) | "Breadboard göstermiyoruz; üretime verilebilir bir ürün gösteriyoruz." |
| Firmware host'ta gerçekten koşuyor (A tamamlandığında) | "Kod MCU'ya hazır." |
| Fizik motoru, rastgele sayı değil (τ·dΔT/dt + ΔT = K·I²) | "Isıl direnç indeksi gerçek bir fiziksel modelden geliyor." |
| Gerçek register adresleriyle simülatörler (A/B tamamlandığında) | "Cihazlarınız elimizde yok ama register haritanız elimizde." |
| Bildirim gerçekten telefona düşüyor (WhatsApp + sanal GSM modem) | "SMS sürücüsü üretim sürücüsüdür." |

**Not (dürüstlük):** Bu depoda bugün itibarıyla A kulvarı (fizik motoru, firmware, simülatörler)
henüz tamamlanmadı; sunumda hangi kanıtların canlı gösterilebildiği demo provasında netleşecek
(bkz. `STATUS.md`).

## Slayt 4 — Mimari (1,5 dk)

`docs/02-mimari.md`'deki bileşen diyagramını göster: kenar (sensörler + Pano Beyni) → MQTT →
ingest → risk motoru → alarm yöneticisi → bildirim; paralelde SCADA ağ geçidi (Modbus TCP +
IEC 104) ve operasyon arayüzü. Vurgu: "kenar önce" ilkesi (bağlantı kopsa da yerel tespit çalışır).

## Slayt 5 — Canlı demo (7 dk)

`demo/senaryo/` betiklerinin sırasıyla: **S0 → S1 → S3 → S4 → S5** (rapor §8.2 video kurgusuyla
aynı), sonra **S7 (ölçek)** ve **S8 (entegrasyon)**'dan kısa kesitler.

| Adım | Süre | Anlatı |
|---|---|---|
| S1 Gevşek bağlantı | 90 sn | "Sabit eşik bunu göremezdi" — K/K₀ 1,4, mutlak sıcaklık hâlâ limit altında |
| S3 Yoğuşma | 60 sn | Otomatik ısıtıcı aksiyonu, alarm kendini temizliyor |
| S4 Ark olayı | 60 sn | P1 → telefona gerçek SMS/WhatsApp, kara kutu 72 saatlik geçmiş |
| S5 Koruma sağlığı | 30 sn | "Pano sessizce korumasız" — operasyonu anlama kanıtı |
| S7 Ölçek | 45 sn | Grafana'da 1.000 pano, p95 gecikme |
| S8 Entegrasyon | 30 sn | QModMaster'dan bizim haritamızı okuma |

**Yedek plan (T5.5, B):** Canlı demo patlarsa `demo/video/` altındaki kayıt oynatılır.

## Slayt 6 — Ölçek + maliyet/ROI + kurulum (1,5 dk)

- **Ölçek:** `docs/09-olceklenebilirlik.md`'den ölçülmüş sayılar (1.000 panoda p95 gecikme, DB
  sıkıştırma oranı).
- **Maliyet:** `docs/10-bom-maliyet-roi.md`'den SKU tablosu + adet 1/1.000 birim maliyet
  (~56 → ~37 USD/kontrolcü) + parametrik ROI formülü.
- **Kurulum:** `docs/08-kurulum-proseduru.md`'den tek planlı kesinti penceresi, ≤45 dk, 2 kişi.

## Slayt 7 — PoC teklifi (30 sn)

> "3 ay, 10 pano (farklı yük tipleri, iç/dış). KPI: gerçek bulgu sayısı, yanlış alarm/pano/ay,
> veri erişilebilirliği %, kurulum süresi, saha ekibi memnuniyeti." (rapor §13, soru 17)

---

## Prova notları (T5.4)

- 2 prova: biri süreli (12 dk sınırına uyulduğunu ölçün), biri soru-cevaplı.
- Jüri soru bankası (rapor §13, 17 soru) ekipçe paylaşılıp rol dağılımına göre çalışılmalı.
- Videoda/slaytlarda komitenin gizli dokümanlarının (`Hackathon Verileri/`, proje PDF'i) hiçbir
  sayfası görünmemeli — yalnızca kendi çizimlerimiz (`assets/`, `hardware/yerlesim/`) kullanılır.
