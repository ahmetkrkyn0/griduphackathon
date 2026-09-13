# 11 — Standartlar ve Uyum

> **Sahip:** Kişi C · Kaynak tablo: rapor §7.6. "Nerede karşılandı" sütunu bu depodaki gerçek
> dosyalara işaret eder.

| Alan | Standart / rehber | Nerede karşılandı |
|---|---|---|
| AG panolar | TS EN / IEC 61439-1, -2, -5; TEDAŞ-MLZ/2003-06.B | `contracts/alarm-codes.yaml` L0 eşikleri (terminal/bara sıcaklık artışı); `hardware/yerlesim/`, `assets/ek2-14-pano.svg` (EK-II/14 ölçüleri) |
| OG hücreler | IEC 62271-200 | `docs/01` §"PD" notu (Could seviyesi, uygulanmadı) |
| Kısmi deşarj | IEC 60270; IEC TS 62478 | Rapor §3.7 tasarım notu; donanım üretilmedi (Won't) |
| Yalıtım koordinasyonu | IEC 60664-1 | `docs/13-donanim-tasarimi.md` clearance/creepage hesabı; `io-tablosu.md` izolasyon sütunu |
| Koruma derecesi / yanıcılık | IEC 60529 (IP); IEC 60695-11-10 / UL94 (V-0) | `hardware/mekanik/din-kutu.scad` (V-0 malzeme notu, IP20 dahili); `docs/08` kurulum prosedürü |
| EMC ve çevre | IEC 61000-6-5; IEC 60068-2 | `docs/13` EMC hedefi ve RS485 izolasyon notu |
| Fonksiyonel güvenlik (bağlam) | IEC 61508 / IEC 62061 (TVOC-2 SIL-2) | `docs/06-alarm-matrisi.md` (B) — TVOC-2 salt okunur entegrasyon, GK6 |
| Haberleşme | Modbus Application Protocol v1.1b3; Modbus over Serial Line v1.02; IEC 60870-5-104; MQTT | `contracts/modbus-map.yaml`, `docs/03-modbus-haritasi.md`, `docs/04-iec104-haritasi.md` (B) |
| Siber güvenlik | IEC 62443 | `docs/15-guvenlik-kvkk.md` (B); `io-tablosu.md` satır 15 (debug portu üretimde kapalı) |
| Alarm yönetimi | ANSI/ISA-18.2 / IEC 62682; EEMUA 191 | `docs/06-alarm-matrisi.md` (B); `frontend/src/pages/AlarmKonsolu.tsx` (onay/raf/eskalasyon uygulaması) |
| Termografi / bakım | NETA MTS; NFPA 70B | `contracts/alarm-codes.yaml` `phase_diff_alarm_k` eşiği; `frontend/src/pages/TrendKorelasyon.tsx` (I²–ΔT eğim karşılaştırması) |
| Türkiye mevzuatı | Elektrik Kuvvetli Akım Tesisleri Yön.; Topraklamalar Yön.; EPDK kalite yönetmeliği; KVKK; TEDAŞ-MLZ/2019-064.B | `docs/10-bom-maliyet-roi.md` (EPDK tazminat dayanağı); `docs/15-guvenlik-kvkk.md` (B, KVKK) |

## Kapsanmayan standartlar (bilinçli, MoSCoW Won't/Could)

- **IEC 62271-200** (OG hücreler) ve **IEC 60270/62478** (PD ölçümü): AG pano bu teslimin ana
  odağı; OG/PD yalnızca kavramsal eklenti olarak ele alındı (rapor §3.7).
- Sertifikasyon testleri (EMC, ortam) bu teslimde **yapılmadı** — tasarım hedefleri belgelenmiştir,
  fiziksel doğrulama bir sonraki PoC fazının konusudur (`docs/17-donanimsiz-dogrulama.md`).
