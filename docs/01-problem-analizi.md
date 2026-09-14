# 01 — Problem Analizi (Jüri Özeti)

> **Sahip:** Kişi C · Kaynak: `HACKATHON_ANALIZ_RAPORU.md` (tam analiz). Bu doküman o raporun
> 3 sayfalık, jüriye sunulacak özetidir.

## Sorunun tek cümlesi

ADM Elektrik ve GDZ Elektrik, 1600 kVA'lık TEDAŞ tipi AG dağıtım panolarına — kablo kalabalığını
artırmadan, bakım gerektirmeden — eklenebilen; donanım + gömülü yazılım + merkezi on-premise
izleme + SCADA entegrasyonu + SMS/WhatsApp alarmı içeren; en az 100 modüle ölçeklenen, uçtan uca
çalışan bir prototip istiyor. Fikir yeterli değil; **çalışan bir sistem** gösterilmesi bekleniyor.

## Neden zor: çoğu takımın kaçıracağı gerçekler

1. **Verilen örnek akım verisi rastgele gürültü.** `İstenen Veriler.xlsx`'teki 152 örneklik seri,
   lag-1 otokorelasyonu 0,00 — gerçek bir yük profili değil, yalnızca format örneği. Bu veriyle
   "normal/anormal" öğrenilemez; fizik tabanlı kendi sentetik veri üretecimiz bunun içindir.
2. **Panoda zaten iki akıllı cihaz var:** ENTES MPR-53CS (enerji analizörü) ve ABB TVOC-2 (ark
   koruma), ikisi de Modbus RTU. Yeni bir akım sensörüne gerek yok — bu cihazları **okumak**
   yeterli. Bu, hem maliyeti düşürür hem kablo kalabalığını artırmaz (rapor §3.2, §3.5, §3.6).
3. **TVOC-2 zaten arkı <1 ms'de kesiyor (SIL-2).** Bizim katkımız arkı "tespit etmek" değil:
   koruma sisteminin **sağlığını** izlemek (dedektör arızası = pano sessizce korumasız kalır),
   olayı konumla bildirmek ve ark öncesi öncülleri (ısınma, yoğuşma) yakalamak.
4. **AG panoda kısmi deşarj (PD) fiziksel olarak nadir** (havada Paschen minimumu ~327 V; 400 V
   sistemde pratikte beklenmez). PD'yi AG'nin ana özelliği gibi sunan bir takım "problemi yanlış
   anlamış" görünür; biz PD'yi bilinçli olarak bir **OG hücre eklentisi** olarak konumlandırıyoruz.
5. **WhatsApp On-Premises API 23 Ekim 2025'te kapandı.** "Public cloud yok" şartıyla çelişen bir
   noktayı fark etmek jüriye "problemi doğru anladık" mesajı verir: birincil kanal tamamen on-prem
   **GSM SMS**, WhatsApp yalnızca hassas olmayan kısa metinle ikincil kanal.
6. **Modbus RTU tek master'dır.** Panodaki RS485 hattı zaten bir modem/RTU tarafından
   sorgulanıyor olabilir; mimarimiz üç kurulum senaryosuna (yeni kurulum / dinleme / şeffaf ağ
   geçidi) göre tasarlandı (rapor §6.4a).
7. **Saydam kapak polikarbonat/cam, uzun dalga kızılötesini (8–14 µm) geçirmez.** Termal kamerayı
   kapak dışına koyan bir çözüm sahada çalışmaz; sensör kapağın **içinde** olmalı.

## Önerilen çözüm (özet)

"Pano Beyni": pano üst bölmesine DIN rayına takılan düşük maliyetli MCU tabanlı kenar kontrolcü +
kablosuz, enerji toplayan bağlantı sıcaklık düğümleri + ortam (sıcaklık/nem/çiy noktası) düğümü +
mevcut MPR-53CS/TVOC-2'nin Modbus'tan okunması. Kenarda **fizik tabanlı** anomali tespiti (ısıl
direnç indeksi + faz karşılaştırma + çiy noktası marjı), merkezde on-prem MQTT + zaman serisi DB +
ISA-18.2 alarm yönetimi + SMS/WhatsApp + Modbus TCP/IEC 104 SCADA ağ geçidi + operasyon arayüzü.
1.000 sanal pano ile ölçek kanıtı.

## Bizi ayıran 5 şey

1. **"Sınıra kalan süre" tahmini** — mutlak sıcaklık henüz normalken erken uyarı.
2. **Koruma sisteminin sağlık izlemesi** — "pano sessizce korumasız" durumunu yakalama.
3. **Gerçek register haritalarıyla çalışan simülatörler** — jüri kendi Modbus istemcisiyle okuyabilir.
4. **Ölçülen performans** — recall/precision/öne alma süresi/yanlış alarm oranı, sayılarla.
5. **Sahaya hazır mühendislik** — TEDAŞ şartname atıflı yerleşim, FMEA, kurulum prosedürü, standart
   uyum tablosu.

## Donanımsız teslim (bilinçli karar)

Donanım satın alınmadı (ekip kararı, `PLAN.md` GK3). Bunun yerine: **üretilebilir donanım tasarımı**
(blok diyagram + I/O tablosu + BOM, gerçek parça numaraları — bkz. `hardware/pano-beyni/`),
**gerçekten çalışan firmware** (host'ta), **gerçek register adresleriyle simülatörler**, **gerçek
protokollerle SCADA entegrasyonu**. Detay: `docs/17-donanimsiz-dogrulama.md`.
