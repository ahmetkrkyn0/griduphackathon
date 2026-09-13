# 07b — FMEA: Yazılım ve Sistem

> **Sahip:** Kişi B · **Kaynak:** rapor §7.3 (yazılım/sistem satırları 4, 5, 6, 7, 8, 11, 12, 13, 14) · Donanım ve saha satırları (1, 2, 3, 9, 10):
> `docs/07-fmea-donanim-saha.md` (Kişi C).
> Ölçek: Ş = şiddet, O = olasılık, D = tespit edilemezlik (1–10); **RÖS = Ş × O × D**. Önlem sonrası RÖS yalnızca önlem gerçekten
> **uygulanmış ve sınanmışsa** düşürülür; tasarımda kalan önlem için "hedef" RÖS yazılır.

**Önlem durumu etiketleri** — dürüstlük kuralı (PLAN.md Bölüm C):

| Etiket | Anlamı |
|---|---|
| ✅ **uygulandı** | Kodda var, otomatik testi var; kanıt sütununda test veya ölçüm adı |
| 🟡 **kısmen** | Merkez tarafı uygulandı, kenar/donanım tarafı tasarımda |
| 📐 **tasarım** | Kişi A (firmware) veya C (donanım) kulvarında, henüz kod/donanım yok |
| 🧭 **yol haritası** | Hackathon kapsamı dışı, üretim öncesi yapılacak |

## 1. Rapor §7.3 yazılım / sistem satırları

| # | Hata türü | Etki | Ş | O | D | RÖS | Önlem ve durumu | Kanıt | Sonra |
|---|---|---|---|---|---|---|---|---|---|
| 4 | Hücresel bağlantı koptu | Merkez veri almaz; arıza fark edilmez | 6 | 5 | 2 | 60 | ✅ Merkezde 5 dk sessizlikte `ALM-COMMS-LOST` (SYS, "arıza alarmı değil"); veri dönünce histerezisle kapanır. ✅ Geri doldurulan eski ölçüm son durumu ve alarm durumunu **ezmez**. 📐 Kenarda 7 gün halka tampon, yerel röle çıkışı (A/C) | `test_api_alarms::test_silent_panel_raises_comms_lost_and_clears_after_data_returns`, `test_alarm_manager` (backfill), `test_db_integration` | 6×5×1 = **30** |
| 5 | Merkez sunucu arızası | Alarmlar iletilmez | 9 | 2 | 3 | 54 | ✅ Tek süreç çökmesinde durum kaybı yok: açık alarmlar aynı kimlikle geri yüklenir, MQTT oturumu kalıcı (QoS 1 mesajlar broker'da bekler), yazılamayan alarm değişiklikleri sırayla tekrar denenir. 🧭 Aktif-pasif ikinci sunucu. 📐 Kenar P1'de doğrudan SMS (kenar modemi, C) | `test_alarm_store::test_open_alarms_are_restored_exactly_and_cleared_ones_are_not`, docs/06 §8 | hedef 9×1×2 = 18 |
| 6 | Bizim RS485 bağlantımız mevcut Modbus sorgusunu bozdu | SCADA/OSOS verisi kaybı | 8 | 4 | 5 | 160 | 📐 Senaryo A/B/C analizi, dinleme modu, izoleli port, devreye almada mevcut master testi (A/C; docs/03 §2). ✅ Merkezdeki Modbus TCP ağ geçidi saha RS485 hattına **hiç dokunmaz**: SCADA'ya veriyi hücresel telemetriden sunar | docs/03 §2, `test_scada_app::test_modbus_values_match_the_panel_api` | hedef 8×1×2 = 16 |
| 7 | Yanlış alarm seli | Operatör güveni kaybı, alarmların kapatılması | 7 | 6 | 3 | 126 | ✅ ISA-18.2 yöneticisi: 5 dk histerezis, 10 dk kök neden gruplaması (tek olay, tek telefon), süreli ve gerekçeli raf, bakım modu, P3 kimseyi aramaz. ✅ Grafana "Alarm KPI": günlük alarm (EEMUA 191: ≤150 / 300), öncelik dağılımı (hedef %5/%15/%80), kötü aktör panoları. 📐 Yük-normalize tespit, 7 gün taban öğrenme (A) | `test_alarm_manager` (histerezis, gruplama, raf), `test_notifier::test_warnings_and_system_alarms_page_nobody`, `test_grafana_dashboards` | 7×3×2 = **42** (tespit tarafı A'da tamamlanınca hedef 28) |
| 8 | Kaçırılan alarm (gerçek arıza tespit edilmedi) | Yangın / kesinti | 10 | 3 | 7 | 210 | 🟡 L0 mutlak limitleri her zaman etkin (bakım modunda bile P1 bastırılmaz). ✅ Kenar kodunu merkez körü körüne değil **eşiğiyle** açıklar; eşiği aşmayan kod alarmı yine açar ama "en yakın nokta" gerekçesiyle. 🟡 Sentetik test alarmı: SCADA komut register'ı 904 → MQTT `cmd` ile kenara iletilir (kenar tarafı A). 🧭 Periyodik (günlük) otomatik test alarmı zamanlayıcısı | `test_alarm_manager` (P1 bakımda), `test_risk`, `test_scada_gateway::test_maintenance_and_test_alarm_are_forwarded_to_edge` | hedef 10×2×4 = 80 |
| 11 | TVOC-2'ye yanlışlıkla yazma (reset / diagnostik) | Koruma işlevinin etkilenmesi | 10 | 2 | 4 | 80 | ✅ Modbus TCP ağ geçidi **varsayılan salt okunur** (şifre tanımsızsa her yazma 0x01). ✅ Yazma yalnızca komut bloğunda; TVOC-2 aynası (500–519) dahil başka her adrese yazma **doğru şifreyle bile** 0x02. ✅ Şifre bağlantıya bağlı, süreli; 3 yanlış şifre IP'yi 5 dk kilitler; istek önce tamamen doğrulanır. 📐 Kenarda FC06/16 filtresi aynı harita bayrağıyla (A) | `test_scada_gateway::test_write_outside_command_block_is_illegal_address`, 13 Eylül canlı yığında TVOC-2 aynasına şifreli yazma → 0x02 (docs/03 §14); mutasyon 35/35 | 10×1×2 = **20** |
| 12 | Siber saldırı (sahte veri / komut) | Yanlış aksiyon, gizlilik ihlali | 9 | 3 | 6 | 162 | ✅ Sözleşme dışı veri düşürülmez, **karantinaya** alınır (sahte/bozuk yük görünür olur); topic ile yükteki pano kimliği uyuşmazsa reddedilir. ✅ Modbus TCP: izinli ağ listesi, bağlantı sınırı, boşta zaman aşımı; komutlar denetim izinde IP ile. ✅ Dışa çıkan tek kanal WhatsApp: yalnızca saha kodu + öncelik + tek satır. 📐 Cihaz sertifikası, mTLS, imzalı OTA (A/C). ⚠️ **Demo broker'ı düz MQTT 1883 ve anonimdir** — üretimde mTLS + cihaz başına topic ACL zorunlu (docs/15) | `test_ingest` (karantina, pano kimliği uyuşmazlığı), `test_modbus_tcp::test_client_outside_allowlist_is_dropped` | hedef 9×1×3 = 27 (mTLS olmadan 9×3×4 = 108) |
| 13 | Firmware güncellemesi başarısız | Cihaz çalışmaz | 7 | 3 | 3 | 63 | 📐 A/B bölümlü OTA + otomatik geri dönüş, aşamalı yayılım %1 → %10 → %100 (A). ✅ Merkezde sürüm görünür: telemetri `fw` → Modbus `device_info.fw_version`, pano detayı; güncelleme sonrası sessiz kalan pano `ALM-COMMS-LOST` üretir | `test_scada_encoder` (fw kodlama), `test_api_panels` | hedef 7×1×2 = 14 |
| 14 | Saat senkron kaybı | Olay sıralaması yanlış | 4 | 3 | 5 | 60 | ✅ Alarm yöneticisi histerezis ve gruplamayı **olay zamanıyla**, eskalasyonu **duvar saatiyle** ölçer; panonun son işlediği andan eski örnek canlı alarm durumunu değiştirmez. 📐 Sunucudan periyodik senkron (`cmd` topic `sync_time`, A). 🧭 Merkezde `ts` ile alım zamanı farkı izlenip kayma alarmı | `test_alarm_manager` (backfill yok sayılır) | hedef 4×2×2 = 16 |

## 2. Uygulama sırasında ortaya çıkan hata türleri

Rapordaki tabloda olmayan ama kodu yazarken veya ölçerken **bulunan** hata türleri. Hepsinin önlemi uygulandı ve testle kilitlendi.

| # | Hata türü | Nasıl bulundu | Etki | Ş | O | D | RÖS | Önlem | Kanıt | Sonra |
|---|---|---|---|---|---|---|---|---|---|---|
| Y1 | **Ingest kapasitesinin aşılması** | 10.000 pano stres testi (13 Eyl) | Veri kaybı yok ama görünme gecikmesi p95 18,9 s, alarm → SMS p95 9,6 s | 8 | 2 | 6 | 96 | ✅ Kapasite ölçüldü ve sınır yazıldı (docs/09 §4); ✅ Grafana "Ölçek" panosu yayın ve yazma hızını yan yana gösterir (ayrışma = kuyruk birikiyor); darboğaz ölçüldü: mesaj başına 615 µs'in 501 µs'i şema doğrulaması. 🧭 MQTT paylaşımlı abonelikle yatay ölçek | `loadtest/results/*-10000p.json`, `test_grafana_dashboards` | 8×2×2 = **32** |
| Y2 | **Modbus sunucu kitaplığı her bağlantıda port sızdırıyor** | pymodbus 3.7.4 sunucusunun ön denemesi (13 Eyl) | Her SCADA yeniden bağlantısında `0.0.0.0` üzerinde yeni açık port: kaynak tükenmesi + saldırı yüzeyi | 8 | 8 | 7 | 448 | ✅ Kitaplık sunucusu kullanılmadı; asyncio sunucusu yazıldı, bağlantı sınırı ve boşta zaman aşımıyla; pymodbus yalnızca bağımsız test istemcisi | `test_modbus_tcp` (35 test, mutasyon 19/19), docs/03 §13 | 8×1×2 = **16** |
| Y3 | **SCADA'nın "alarm yok" okuması** (alarm durumu yüklenmeden 0 bit) | Ağ geçidi tasarımı | Aktif P1 varken SCADA'da yeşil ekran | 10 | 3 | 8 | 240 | ✅ Alarm durumu yüklenmemiş panonun okuması 0x0B ile reddedilir; kenarın göndermediği alan 0 değil "yok" (0x8000 / 0xFFFF) | `test_scada_gateway::test_panel_without_loaded_alarm_state_is_target_failed`, `test_scada_encoder` | 10×1×2 = **20** |
| Y4 | **Büyük filoda ingest thread'inin kilitlenmesi** (birim eşlemesi O(n² log n)) | 10.000 pano stres testi hazırlığı | İlk periyotta alım 5 s durur | 7 | 3 | 6 | 126 | ✅ Eşleme parti başına bir kez, O(n log 247) | `test_scada_gateway::test_auto_units_scale_to_a_large_fleet_arriving_at_once` (5,0 s → < 1 s) | 7×1×2 = **14** |
| Y5 | **Bozuk veya sözleşme dışı mesaj** | TB1 | Tek bozuk cihaz tüm partiyi / filoyu durdurur | 7 | 5 | 4 | 140 | ✅ Şema dışı mesaj karantinaya; veri hatalı parti tek tek yazılarak bozuk mesaj ayıklanır, sağlamlar yazılır | `test_ingest::test_data_error_is_isolated_to_the_offending_message`, `test_ingest::test_schema_violation_is_quarantined_not_dropped` | 7×1×2 = **14** |
| Y6 | **Veritabanı erişilemez** | TB1/TB2 | API ve alarm yazımı durur; telefon çalmaz | 9 | 3 | 3 | 81 | ✅ Backend yine açılır (API 503); ingest partiyi saklar; alarm değişiklikleri sırayla bekletilir; **WebSocket ve bildirim yazmayı beklemez** | `test_api_panels::test_unavailable_database_is_reported_as_503`, `test_db_integration::test_unreachable_database_raises_store_error_instead_of_hanging`, docs/06 §8 | 9×1×2 = **18** |
| Y7 | **Bildirim kanalı arızası** (modem koptu, takıldı; internet yok) | TB2 | SMS/WhatsApp gitmez | 9 | 4 | 3 | 108 | ✅ Sürücü yeniden bağlanır, yarım SMS'i ESC ile iptal eder; takılan modem zaman aşımına düşer; WhatsApp geçici hatası tekrar denenir, kalıcı hata bir kez kaydedilir; SMS ve WhatsApp birbirinden bağımsız | `test_sms_modem` (kopuk oturum, zaman aşımı), `test_notifier::test_temporary_whatsapp_failure_is_retried` | 9×2×2 = **36** |
| Y8 | **Sözleşme tutarsızlığı** (yanlış eşik veya adres) | Faz 0 (`check_contracts.py` gerçek bir adres çakışması yakaladı) | Yanlış eşikle alarm, yanlış register'dan SCADA okuması | 9 | 3 | 7 | 189 | ✅ Bozuk sözleşme veya harita servisi **başlatmaz**; adres, alarm ve komut tabloları sözleşmeden **üretilir** (docs/03, docs/06, Grafana) ve güncel olmaları testte sınanır; register'ın merkez kaynağı tanımsızsa ağ geçidi kurulmaz | `test_map_loader`, `test_gen_modbus_doc::test_committed_doc_and_csv_are_up_to_date`, `test_scada_encoder::test_register_without_central_source_refuses_to_build` | 9×1×2 = **18** |
| Y9 | **Modbus portu başka süreçte** | TB3 | Backend hiç açılmazsa alarm zinciri de durur | 8 | 2 | 2 | 32 | ✅ Port açılamazsa backend durmaz; hata `/health` → `scada.error` | `test_scada_app::test_busy_port_does_not_take_the_backend_down` | 8×2×1 = **16** |

## 3. Özet

| | Satır | RÖS toplamı (önce) | RÖS toplamı (şimdi) |
|---|---|---|---|
| Rapor §7.3 yazılım/sistem satırları | 9 | 975 | **801** — uygulanmış önlemle düşenler: #4 60 → 30, #7 126 → 42, #11 80 → 20. Diğerleri tasarım / yol haritası önlemleri tamamlanana kadar **önceki RÖS'te** sayılır |
| Uygulamada bulunan hata türleri | 9 | 1.460 | 184 |

**En yüksek kalan risk:** #8 kaçırılan alarm (RÖS 210). Merkez tarafı hazırdır; tespit başarısı Kişi A'nın doğrulama tablosuyla (docs/12:
duyarlılık, keskinlik, öne alma süresi) ölçülecektir. İkinci sırada #6 (RS485 hattını bozmak, 160) sahada keşif ve devreye alma prosedürüyle
(docs/08, Kişi C) kapanır; üçüncü sırada #12 (siber, 162) üretimde mTLS olmadan kapanmaz ve bu **demo yığınında açıkça yoktur** (docs/15).
