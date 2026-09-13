# 17 — Donanım Olmadan Neyi, Nasıl Kanıtladık?

> **Sahip:** Kişi B · **Kapsam:** üç kulvarın kanıtları tek yerde (PLAN.md Bölüm C, GK3).
> Kulvar sahipleri kanıtlarını sohbette iletir, bu dosyayı yalnızca B düzenler (PLAN.md kural 2). **Son güncelleme: 13 Eylül 2026.**
> Bu tarihte A (veri üreteci, simülatörler, firmware) ve C (donanım tasarımı, arayüz) kulvarlarının kanıtları henüz gelmedi; ilgili satırlar
> **bekliyor** olarak işaretli ve beklenen kanıt tek tek yazılı.

**Dürüstlük kuralı.** Sunumda ve README'de "simüle edildi" olan her şey açıkça simüle edildi yazılır. Jüri kandırıldığını anlarsa her şey
çöker; bilinçli bir mühendislik seçimi olduğunu görürse puan kazanırız.

## 1. Neden donanımsız?

Donanım satın alınmadı (PLAN.md GK3). Bu bir eksiklik değil, üç gerekçesi olan bir karardır:

1. **Arıza gösterilebilirliği.** Gevşeyen bir bağlantı 7–30 günde bozulur. Masadaki bir ısıtıcı bunu gösteremez; fizik modeli
   (`τ·dΔT/dt + ΔT = K·I²`) altı günlük bozulmayı dakikalar içinde ve **etiketli** olarak oynatır. Tespit başarısı böylece ölçülebilir.
2. **Ürün, geliştirme kartı değildir.** Rapor §5: breadboard ve geliştirme kartı sunmak puan kaybettirir. Üretilebilir bir ürün tasarımı
   (şema, BOM, yerleşim, FMEA) sahaya daha yakındır.
3. **Merkez yazılımı donanımdan bağımsız olarak gerçektir.** Broker, veritabanı, alarm yöneticisi, SMS sürücüsü ve Modbus ağ geçidi sahada
   da aynı koddur; değişen tek şey veriyi üreten uçtur.

## 2. Ne simüle edildi, ne gerçek?

| Bileşen | Sahada | Bu teslimde | Ne kadar gerçek | Kanıt | Kulvar / durum |
|---|---|---|---|---|---|
| Bağlantı sıcaklık düğümleri, ortam düğümleri | Kablosuz sensörler | Fizik tabanlı veri üreteci (`libs/panoalgo`) | Simülasyon; ısıl model ve arıza enjeksiyonu denklemle savunulur | `docs/14`, `docs/05` | A · **bekliyor** |
| MPR-53CS, TVOC-2 | Gerçek cihazlar | Register simülatörleri (kılavuzdaki adresler) | Protokol ve adresler gerçek, ölçüm simülasyon | QModMaster okuması, TVOC-2 ID 248 davranışı | A · **bekliyor** |
| Pano Beyni firmware'i | MCU | Taşınabilir C çekirdeği, host ikilisi | Kod gerçek, hedef donanım yok | `ctest`, C = Python test vektörü | A · **bekliyor** |
| Pano Beyni donanımı | Özel PCB | KiCad şema, I/O tablosu, BOM, yerleşim, mekanik | Üretime verilebilir tasarım, üretilmedi | `hardware/`, `docs/13` | C · **bekliyor** |
| Hücresel hat | LTE, özel APN | Tek makinede yerel ağ | Simülasyon; gecikme ve kopukluk yok | docs/09 §8 | B · bilinen sınır |
| MQTT broker, ingest, TimescaleDB | Merkez sunucu | **Aynısı** (`docker compose`) | **Gerçek** | 1.000 pano yük testi (docs/09) | B · ✅ |
| Risk açıklaması + ISA-18.2 alarm yöneticisi | Merkez | **Aynısı** | **Gerçek** | `test_alarm_manager`, `test_risk`, `test_api_alarms` | B · ✅ |
| GSM modem (SMS, arama) | USB modem veya terminal sunucusu | Sanal modem (`scripts/virtual_gsm_modem.py`) | **Sürücü gerçek** (AT komutları, PDU); modem simülasyon. Gerçek modemde yalnızca `SMS_DEVICE` değişir | AT kaydı + PDU dökümü (`deploy/runtime/sms-log.txt`), `test_sms_modem` | B · ✅ |
| WhatsApp | Meta Cloud API | Gerçek API istemcisi | **Gerçek**; telefona teslim için Meta test numarası ve token gerekir | `test_whatsapp`, `test_notifier` | B · istemci ✅, **gerçek telefona teslim bekliyor** (token: Ahmet) |
| SCADA / RTU | Dağıtım SCADA'sı | QModMaster / pymodbus istemcisi | **Ağ geçidi gerçek**, istemci test aracı | docs/03 §14, `test_scada_*` | B · ✅ |
| 1.000–10.000 pano filosu | Saha | Şablon yük üreteci (`loadtest/fleet.py`) | Platform yükü gerçek, değerler fiziksel değil | docs/09 | B · ✅ |
| Operasyon arayüzü | Kontrol odası | React arayüzü | **Gerçek** | `frontend/`, `docs/16` | C · **bekliyor** |

## 3. Beş hamle — durum ve kanıt

### DH1 — Üretilebilir donanım tasarımı (Kişi C) · **bekliyor**

Beklenen kanıt: KiCad şeması (PDF) gerçek parça numaralarıyla ve **geliştirme kartı olmadan**; I/O tablosu; güç bütçesi; BOM (adet 1 ve adet
1.000); DIN kutu mekaniği (STL); EK-II/14 üzerinde yerleşim; clearance/creepage ve manyetik alan hesabı (`docs/13`).

### DH2 — Firmware gerçekten koşuyor (Kişi A) · **bekliyor**

Beklenen kanıt: `ctest` yeşil; C ve Python RLS çıktılarının aynı test vektöründe ≤ 1e-6 farkla eşleşmesi (`data/fixtures/rls_vectors.csv`);
`panobeyni-sim` ikilisinin sanal seri porttan Modbus master, kendi haritasıyla Modbus slave ve MQTT yayını; `malloc` yok.

**B'nin bu hamleye katkısı hazır:** firmware'in sunacağı Modbus haritası (`contracts/modbus-map.yaml`) merkezde birebir çalışıyor. Aynı adresler,
aynı kodlama kuralları, aynı "yok" değerleri (docs/03 §5). Firmware bu tabloyu sözleşmeden üretecek; merkezle ayrışamaz.

### DH3 — Fizik motoru, rastgele sayı değil (Kişi A) · **bekliyor**

Beklenen kanıt: ısıl model ve yük profili (`docs/14`); lag-1 otokorelasyon > 0,9 testi (verilen Excel'in 0,00'ına karşı); S1 gevşek bağlantı
senaryosunda K/K₀'ın 1,6'yı sabit 70 K eşiğinden **en az 48 saat önce** geçmesi; `docs/12` doğrulama tablosu (duyarlılık, keskinlik,
öne alma süresi, yanlış alarm/100 pano/gün).

**B'nin bu hamleye katkısı hazır:** kenar tespitinin sonucu merkezde açıklanıyor ve yönetiliyor (Neden / Ne yapmalı / Ne kadar acil). Merkez
dedektör kancası (`CentralDetector`) `panoalgo` gelince yalnızca bağlanacak; TB2 Adım 4.

### DH4 — Gerçek protokol, gerçek adresler (Kişi A + B) · **B ✅, A bekliyor**

| Kanıt | Durum |
|---|---|
| Merkezde Modbus TCP 502: her pano bir birim, kenardakiyle aynı harita; FC01/02/03/04/06/16 | ✅ 35 protokol testi (pymodbus istemcisi + elle kurulmuş ham çerçeveler), mutasyon 19/19 |
| Canlı yığında PC'den okuma: 3 panoda `conn_temp` = arayüzün gördüğü değer × 10 | ✅ 13 Eylül |
| Koruma cihazına yazma yok: TVOC-2 aynasına yazma **doğru şifreyle bile** 0x02 | ✅ `test_scada_gateway`, 13 Eylül canlı |
| Harita dokümanı ve Excel tablosu sözleşmeden üretilir, elle yazılmaz | ✅ `docs/03`, `test_gen_modbus_doc` |
| MPR-53CS ve TVOC-2 simülatörleri kılavuz adreslerinde; TVOC-2 fabrika ID 248'de sessiz, 1–247'de cevap veriyor; CT = 500 dönüşümü | A · **bekliyor** |

Jüri demosu (QModMaster adımları): docs/03 §11.

### DH5 — Bildirim gerçekten telefona düşüyor (Kişi B) · **SMS yolu ✅, gerçek telefona WhatsApp bekliyor**

| Kanıt | Durum |
|---|---|
| SMS sürücüsü üretim sürücüsü: AT komutları, **PDU modu** (3GPP TS 23.040), birleşik SMS, kopuk oturumu ESC ile toparlama | ✅ `test_pdu`, `test_sms_modem` |
| Sanal modem gerçek modem kadar katı: uzunluğu tutmayan PDU'yu `+CMS ERROR: 304` ile reddeder | ✅ `test_sms_modem::test_virtual_modem_rejects_a_pdu_whose_length_does_not_match` |
| AT komut kaydı ve PDU dökümü; PDU'lar herhangi bir çevrimiçi çözücüyle doğrulanabilir | ✅ `deploy/runtime/sms-log.txt` (git dışı, numara içerir) |
| Uçtan uca ölçüm: sensör zamanından modemin SMS'i kabulüne p95 **606 ms** (1.000 pano yükü altında) | ✅ docs/09 §4.3 |
| Çift yönlü onay: "1 <alarm no>" yanıtı alarmı onaylar; kayıtsız numara yok sayılır | ✅ `test_notifier`, canlı yığın (docs/06 §10) |
| P1'de 5. dakikada arama, 15. dakikada üst amire eskalasyon | ✅ canlı yığın (docs/06 §10) |
| WhatsApp Cloud API istemcisi: şablon/serbest metin, geçici hatada tekrar, kalıcı hatada tek kayıt | ✅ `test_whatsapp`, `test_notifier` |
| **Gerçek bir telefona WhatsApp mesajı** | **bekliyor:** Meta test numarası + token + doğrulanmış alıcı (Ahmet). İnternet yoksa demo SMS yolu ve AT kaydıyla sürer |

## 4. B kulvarının kanıt özeti (13 Eylül)

| Alan | Otomatik test | Mutasyon denetimi | Canlı / ölçüm |
|---|---|---|---|
| Ingest, veritabanı, API | ✅ (gerçek TimescaleDB entegrasyon testleri dahil) | — | 1.000 pano: görünme p95 657 ms, kayıp 0 |
| Alarm yöneticisi + bildirim | ✅ | TB2'de 107 mutasyonun tamamı | P1/P2 SMS, eskalasyon, SMS onayı |
| Modbus TCP ağ geçidi | 35 + 60 + 9 | 19/19 · 35/35 · kodlayıcı 28/28 | Modbus = API; GK6 yazma reddi |
| Analiz uçları (seri, kara kutu, KPI) | 25 + 4 (gerçek DB) | 20/20 | Seri ve KPI canlı veriden |
| Yük, depolama, sıkıştırma | 12 + 5 + 2 (gerçek DB) | 5/5 | 100 → 10.000 pano; sıkıştırma 48× |
| Grafana panoları | Her panel sorgusu gerçek DB'de | 4/4 | Paneller canlı veriyle |
| Temiz veritabanı kurulumu | `initdb` 001–005 boş DB'de, 23 gerçek DB testi o DB'de | — | 13 Eylül |

Toplam: `TEST_DB_DSN` ile **507 test**.

## 5. Jüri soruları — ölçümle güncellenmiş cevaplar (B)

Rapor §13 soru bankasındaki entegrasyon, ölçek ve güvenlik soruları (PLAN.md T5.4: B). Rapordaki tahmini cevaplar ölçümle değişti.

| # | Soru | Cevap (kanıtıyla) |
|---|---|---|
| 5 | Mevcut SCADA'ya nasıl bağlanıyor? | Merkezden **Modbus TCP 502** çalışıyor: her pano bir birim, kenardaki haritanın aynısı, varsayılan salt okunur (docs/03). Sahada RTU'ya Pano Beyni'nin Modbus slave portu (A). Tek master kısıtı için üç kurulum senaryosu (docs/03 §2). IEC 60870-5-104 **eşlemesi tasarlandı** (rapor §6.4c), kodlanmadı. |
| 6 | "Public cloud yok" dediniz; WhatsApp? | Birincil kanal tamamen yurt içi **GSM SMS**'tir ve sürücüsü üretim sürücüsüdür. WhatsApp ikincil ve kapatılabilir; mesajda yalnızca saha kodu, öncelik ve tek satır var. Alıcı numarası Meta'ya gittiği için açılması KVKK birimi kararına bağlı (docs/15 §4.2). |
| 12 | 10.000 panoya nasıl ölçeklenir? | **Ölçtük:** tek backend süreci 5.000 panoya kadar görünme p95 < 1 s; 10.000'de veri kaybetmeden doyuyor ve darboğaz ölçüldü (şema doğrulaması). Kaldıraçlar: 60 s raporlama (mesaj hızı ÷6) ve paylaşımlı abonelikle çoklu ingest. Depolama: sıkıştırma 48× **ölçüldü ve açık**; 100 pano 10 s'de ~105 GB/yıl, 60 s'de ~17 GB/yıl (docs/09). |
| 13 | Siber güvenlik? | Kodda olanlar: sözleşme dışı veri karantinası, pano kimliği denetimi, Modbus IP listesi + salt okunur varsayılan + koruma cihazına yazma yasağı + kaba kuvvet kilidi, denetim izi (docs/15). Tasarımda olanlar: cihaz sertifikası, mTLS, imzalı OTA (A/C). **Demo yığınında broker anonim ve API'de kimlik doğrulama yok**; üretim farkları listelendi (docs/15 §5). |
| 14 | Veri nerede, KVKK? | Tamamı şirket veri merkezinde. Telefon numaraları yalnızca yapılandırmada; veritabanında ve kayıtta **maskeli**. Disk şifreleme ve saklama süresi politikası yol haritasında (docs/15 §4.3). |
| 7 | TVOC-2 arkı zaten kesiyor; sizin katkınız? | (B tarafı) Koruma sağlığı SCADA'ya ayrı bir coil olarak açılır (`prot_health_ok`); arızalı dedektör P1 alarmı telefonu çaldırır; olay öncesi 72 saatlik kara kutu API'si hazır. **Koruma devresine hiçbir yoldan yazmıyoruz**: ağ geçidi bunu şifreyle bile reddediyor. |

## 6. Açık kalanlar

| Kanıt | Sahip | Hedef |
|---|---|---|
| Veri üreteci, S0–S9 senaryoları, `docs/12` doğrulama tablosu | A | M2–M3 |
| MPR-53CS / TVOC-2 simülatörleri, firmware host ikilisi, `ctest` | A | M3 (17 Eylül) |
| Merkez dedektör bağlantısı (`panoalgo` import, TB2 Adım 4) | B (A'nın paketine bağlı) | paket gelince |
| KiCad şema, BOM, yerleşim, mekanik, `docs/13` | C | M3 |
| Arayüz ekranları ve görüntüleri, `docs/16` | C | M3–M4 |
| Gerçek telefona WhatsApp teslimi | B (token: Ahmet) | M2 |
| Tüm kulvarlar birleşmiş halde temiz makine testi (T4.4) | B | M4 (18 Eylül) |
