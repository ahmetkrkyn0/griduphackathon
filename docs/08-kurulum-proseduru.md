# 08 — Kurulum Prosedürü

> **Sahip:** Kişi C · Kaynak: `HACKATHON_ANALIZ_RAPORU.md` §7.1. Hedef: **tek planlı kesinti
> penceresi**, ≤45 dakika, 2 kişilik saha ekibi.

## 1. Kesinti öncesi (pano enerjili, dokunmasız)

1. **Uzaktan hazırlık:** Pano kimliği (`pano_id`, ör. `ADM-00014`), tipi (1600 kVA dahili),
   SIM/APN, cihaz sertifikası ve Modbus adres planı merkez sistemde önceden oluşturulur.
2. **Saha keşfi:** Pano fotoğrafları, RS485 hattında mevcut bir master (modem/RTU) olup olmadığı
   tespit edilir → `docs/02-mimari.md`'deki Senaryo A/B/C'den hangisinin uygulanacağı belirlenir;
   harici anten çıkışının durumu kontrol edilir (şartname 2.2.8.1.iv).

## 2. Planlı kesinti penceresi (hedef ≤ 45 dk, 2 kişilik ekip)

> **5 güvenlik kuralı** (şartname madde 5.3) — sıra kesinlikle bozulmaz:
> 1) Gerilimi kes → 2) Tekrar gelmesini engelle (kilitle-etiketle) → 3) Gerilim yokluğunu
> kontrol et → 4) Toprakla ve kısa devre et → 5) Çalışma alanını işaretle.

1. Pano Beyni'ni üst bölmedeki DIN rayına tak; besleme **iç ihtiyaç devresinden, sigortalı,
   fişli klemensle** alınır (yeni bir güç hattı çekilmez).
2. RS485'i MPR-53CS/TVOC-2 hattına bağla — izoleli port, hat sonu 120 Ω direnç anahtarı kontrolü.
3. **Bağlantı sıcaklık düğümlerini** (S1) V-0, yüksek sıcaklık sınıfı kablo bağı/kelepçe ile
   pabuç/bara eklerine tak. **Sensör gövdesi hiçbir fazlar arası/faz-toprak açıklığı (clearance)
   veya kaçak yolu (creepage) mesafesini azaltmamalı** (bkz. `docs/13` yalıtım koordinasyonu).
4. Termal dizi (S2) braketini saydam kapağın **iç** tarafına, ortam düğümlerini (S3/S4) alt ve
   üst bölgeye, kapı reed'ini (S5) kapıya monte et (tam konumlar: `hardware/yerlesim/ek2-14-yerlesim.svg`).
5. **(Opsiyonel) Fider akımı ölçümü:** yalnızca ayrık çekirdekli (devreyi açmayan) sensör
   kullanılır. **⚠ AT sekonderi hiçbir koşulda açık devre bırakılmaz** — bu, FMEA'daki (`docs/07`
   satır 10) en ağır donanım riskidir; kontrol listesinde ayrıca imzalanır.
6. Anteni şartnamedeki harici anten çıkışından geçir.
7. Kapakları kapat, enerjiyi ver.

## 3. Kesinti sonrası (pano enerjili, dokunmasız)

1. **Devreye alma kontrolü:** Her düğümün rapor verdiği doğrulanır (canlı yığında `CihazSagligi`
   ekranı, `nodes_ok / nodes_total`).
2. **Otomatik testler:** Modbus okumaları makul mü (CT oranı = 500 kontrolü — bkz.
   `contracts/modbus-map.yaml` `electrical_mirror` bloğu), TVOC-2 ID ≠ 248 mü, test alarmı SMS'i
   geldi mi.
3. **7 günlük taban öğrenme modu:** Yalnızca L0 (mutlak limit) alarmları aktiftir; L1/L2 (ısıl
   direnç indeksi, istatistiksel sapma) 7 gün sonra devreye girer (`health.baseline_day` alanı
   arayüzde bu ilerlemeyi gösterir, bkz. `PanoDetay.tsx`).

## 4. Kontrol listesi (saha ekibi imzalar)

- [ ] 5 güvenlik kuralı sırayla uygulandı
- [ ] Yeni güç hattı çekilmedi (iç ihtiyaçtan, sigortalı)
- [ ] RS485 hat sonu direnci doğrulandı
- [ ] Sensör gövdeleri clearance/creepage mesafesini azaltmadı
- [ ] AT sekonderi (kullanıldıysa) hiçbir an açık devre kalmadı
- [ ] Anten harici çıkıştan geçirildi
- [ ] Devreye alma sonrası tüm düğümler rapor veriyor
- [ ] Test alarmı SMS'i alıcıya ulaştı

## 5. Uzaktan yönetim (kesintisiz işletme)

Kurulumdan sonra sahaya **dokunmadan**: konfigürasyon, eşik parametreleri (`alarm-codes.yaml`
üzerinden merkez), firmware güncellemesi (imzalı OTA, A/B bölümlü + otomatik geri dönüş) ve
uzaktan tanılama yapılabilir. Bakım gerektiren tek fiziksel bileşen, pilli varyantta ≥10 yıl
hedefli pil değişimidir (pil telemetrisi `health` alanında izlenir).
