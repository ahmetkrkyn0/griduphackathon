# 18 — Konumlandırma ve Analitik Standart İzi

> **Sahip:** Ortak doküman (18–20 Eylül doküman penceresi, PLAN.md GK2; bu dosya 16 Eylül'de açıldı) · **Kaynak:**
> `GELISTIRME-BACKLOGU.md` §2 (sektörel bulgular) ve §4 F-15 · `HACKATHON_ANALIZ_RAPORU.md` §4
> **Ölçülen her sayının kaynağı satır içinde dosya adıyla verilmiştir (GK10).**

Bu doküman üç şey yapar: (a) ürünü **cihaz** düzeyinde değil **platform** düzeyinde konumlandırır ve
bizde olmayan her yeteneğin bir boşluk mu yoksa yazılı bir kısıt kararı mı olduğunu ayırır;
(b) ürünün ana işi olan **durum izleme ve prognoz** için standart → kod dosyası → ölçülen sonuç →
dürüst boşluk izini kurar; (c) kapsam dışı bırakılan **veri türleri ve bildirim kanalları** için
(akustik, termal görüntü, WhatsApp) gerekçeyi ve **gerekçenin sınırını** tek yerde toplar.
Bu doküman **hiçbir rakip ürünün kötü olduğunu iddia etmez**, hiçbir rakip
ürün için **fiyat yazmaz** ve erişilemeyen hiçbir standardın madde/tablo numarasını vermez — ISO ve
CIGRE metinlerine bu teslimde erişilmedi, atıflar yalnızca **bölüm başlığı düzeyindedir** ve hiçbiri
birebir alıntı değildir. Doğrulanamayan her hücre "doğrulanmadı" diye işaretlidir.

---

## (a) Konumlandırma ve özellik matrisi

### a.1 Neden cihaz değil, platform karşılaştırması

`HACKATHON_ANALIZ_RAPORU.md` §4'te sekiz satırlık bir **cihaz/sensör** karşılaştırması var (TH110,
CL110, HeatTag, TVOC-2, UltraTEV, HFCT, pasif RFID, termografi turu). O tablo doğru ama yanlış
soruyu cevaplıyor: dağıtım şirketi tek bir sensör satın almıyor, bir **izleme katmanı** satın alıyor.
Jüri kriterlerinden "mevcut sistemlerle entegrasyon", "ölçeklenebilirlik" ve "kullanıcı/operasyon
deneyimi" cihaz düzeyinde hiç görünmez; ancak platform düzeyinde görünür. Bu yüzden aşağıdaki asıl
matris platform düzeyindedir; sensör katmanı §a.4'te ayrı ve daha kısa tutulmuştur.

### a.2 Karşılaştırılan platformlar ve doğrulama durumu

| Platform | Bu teslimde **doğrulanan** özellik | Kaynak | Bu teslimde **doğrulanmayan** |
|---|---|---|---|
| **ABB Ability EDCS** | Çok tesisli (multi-site) karşılaştırma sunduğu | `GELISTIRME-BACKLOGU.md` §2 md. 12 (abb.com) | Protokol listesi, dağıtım modeli, kurulum gereksinimleri |
| **Siemens SENTRON powermanager** | EN 50160 raporlamasının bir eklenti değil **ana modül** olduğu | `GELISTIRME-BACKLOGU.md` §2 md. 12 (siemens.com) | "Kesici kalan ömür" hesabının yöntemi ve doğruluğu |
| **Schneider PME** | EN 50160 raporlamasının **ana modül** olduğu | `GELISTIRME-BACKLOGU.md` §2 md. 12 (product-help.schneider-electric.com) | Analitik/uyarı katmanının ayrıntısı |
| **Eaton Foreseer** | — | F-15 karşılaştırma listesinde adı geçiyor | **Ürün özellikleri bu teslimde doğrulanmadı**; hakkında hiçbir iddia yazılmadı |
| **Hitachi TXpert** | — | F-15 karşılaştırma listesinde adı geçiyor | **Ürün özellikleri bu teslimde doğrulanmadı**; hakkında hiçbir iddia yazılmadı |

**Not (aynı üretici, farklı ürün karışmasın):** depoda Hitachi tarafında doğrulanmış tek kayıt
**Lumada APM**'dir (`frontend/TASARIM-REVIZYONU.md` §2) ve risk matrisi fikrimiz oradan gelir.
**TXpert ayrı bir üründür ve bu teslimde doğrulanmadı** — ikisi birbirinin yerine kullanılmamıştır.

**Fiyat:** bu dokümanda **hiçbir rakip ürün için fiyat yazılmamıştır** (F-15 "Dikkat" satırı).
Kendi maliyetimiz §a.3'te verilmiştir; bu bir karşılaştırma değil, şeffaflık kalemidir.

### a.3 Özellik matrisi

Son sütun kasıtlı olarak vardır: **bizde olmayan her şey eksik değildir.** Bir kısmı yazılı bir
kısıtın (GK3/GK4/GK6) doğrudan sonucudur, bir kısmı gerçekten boşluktur. İkisini ayırmadan okunan
bir matris yanıltıcıdır.

Kısıtların PLAN.md'deki tanımları (birebir teyit edildi): **GK3** — donanım satın alınmayacak,
prototip = simülasyon + tasarım dokümanı. **GK4** — public cloud yok; tüm yığın `docker compose up`
ile tek makinede, internet kablosu çıkarılmış hâlde çalışmalı (tek istisna: kapatılabilir WhatsApp
Cloud API metni). **GK6** — koruma devresine yazma yok; TVOC-2 salt okunur, FC06/16 ağ geçidinde
filtrelenir, otomatik açma (trip) yok.

| # | Yetenek | Bizde (ölçülmüş kanıt) | Ticari platform tarafında **doğrulanan** | Bizde yoksa: **karar mı, boşluk mu** |
|---|---|---|---|---|
| 1 | Yüke normalize erken uyarı (K/K₀) | `dT = K·I²`, unutma faktörlü RLS — `libs/panoalgo/panoalgo/detect.py`. S1'de sabit 70 K eşiğinden **209,0 saat (8,7 gün)** önce uyarı (`docs/12-dogrulama-sonuclari.md` §2) | İncelenen kaynaklarda mutlak sıcaklık + eşik/trend izleme doğrulandı (`frontend/TASARIM-REVIZYONU.md` §2). Yüke normalize ısıl indeks olup olmadığı **doğrulanmadı** | — |
| 2 | Etiketli senaryo üzerinde ölçülmüş tespit başarımı | 10 senaryo; beklenen alarmı olan **8'inde recall 1,00**, 10 senaryonun **hiçbirinde** yasaklı alarm yok (`docs/12` §1). Tek komutla yeniden üretilir: `scripts/validate.py` | Üretici iç testi; yayımlanmış bir doğrulama seti **doğrulanmadı** | — |
| 3 | Yanlış alarm yükünün ölçülmesi ve eşiğin taramayla savunulması | S0'da **71,4** alarm/100 pano/gün (sözleşme sınırı 150) — `docs/12` §3. Eşik taraması (`scripts/threshold_sweep.py`, `docs/05-anomali-tespiti.md` §11): eşiği kısmak yükü artırıyor — (1,0/0,0) → **171,4**, (0,5/0,0) → **228,6**. Aynı sağlıklı senaryo, eşik sabit, mevsim değişken: kış **28,6** · geçiş **71,4** · yaz **0,0** | **Doğrulanmadı** | — |
| 4 | Prognoz (kalan ömür) ve **doğruluğunun** ölçülmesi | `ttl_h` üretiliyor (`detect.py`, `time_to_limit`); geri testi yapıldı ve **olumsuz** çıktı — §(b) ISO 13381-1 satırı ve `docs/12` §4 | "Kalan ömür" göstergesi ABB SWICOM kaydında görülüyor (`frontend/TASARIM-REVIZYONU.md` §2); doğruluğunun **yayımlanmış ölçüsü doğrulanmadı** | **Boşluk** (ölçüldü, kötü çıktı, saklanmadı) |
| 5 | EN 50160 güç kalitesi değerlendirmesi ve raporu | **Yok.** `u_ph` ve `unbal_pct` toplanıyor ama **tüketen kural yok**: `contracts/alarm-codes.yaml` içinde `u_ph` **0 kez** geçiyor; `unbal_pct` ne sözleşmedeki alarm kodlarında ne de `libs/panoalgo/panoalgo/limits.py`'da geçiyor — yalnızca üretilip taşınıyor (`libs/panoalgo/panoalgo/generator.py`, `contracts/mqtt-telemetry.schema.json`). (16 Eylül 2026'da arama ile ölçüldü.) `thd_i` ise **tüketiliyor**, ama yalnızca **akım** THD'si olarak ve tek bir kuralda: nötr akım oranı **ve** ortalama THD birlikte eşiği aşarsa `ALM-NEUTRAL-THD` (`libs/panoalgo/panoalgo/limits.py`, `contracts/alarm-codes.yaml`). Bu bir ısınma kuralıdır; **EN 50160'ın konusu olan gerilim kalitesi değerlendirmesi değildir** (sözleşmedeki `unbal_pct` de gerilim değil akım dengesizliğidir) | Siemens SENTRON powermanager ve Schneider PME'de **ana modül** (`GELISTIRME-BACKLOGU.md` §2 md. 12) | **Boşluk** — kısıt kararı değil. MoSCoW kapsamında yok; ürünleşme kalemi |
| 6 | Rapor üretimi ve dışa aktarma | **Kısmen var.** (i) Tek olay için **yazdırılabilir olay dosyası**: Olay Analizi (kara kutu) ekranı `window.print()` ile A4 dikey çıktı verir; tek yazdırma kuralı kaynağı `frontend/src/print.css`, sayfa `frontend/src/pages/OlayAnalizi.tsx`, testi `frontend/src/print.test.ts` — yeni npm bağımlılığı yok. (ii) Günlük P3/SYS özeti tek parça SMS olarak gider: `backend/app/notify/dispatcher.py` `digest()`, saati `DIGEST_AT` (`deploy/.env.example`) | EN 50160 dahil **periyodik rapor üretimi ana modül** (Siemens SENTRON powermanager, Schneider PME — `GELISTIRME-BACKLOGU.md` §2 md. 12) | **Kısmi boşluk:** **periyodik filo raporu** (günlük/aylık, ekranda üretilen) ve **veri dışa aktarma** (CSV/PDF indirme) yok — `frontend/src/` içinde `download` / `createObjectURL` / `text/csv` **hiç geçmiyor** (16 Eylül'de arama ile ölçüldü). Kısıt kararı değil, kapsam boşluğu |
| 7 | Çok tesisli / filo karşılaştırma | Filo Listesi + Risk Matrisi + Bölge Haritası (`frontend/src/pages/`) | ABB Ability EDCS çok tesisli karşılaştırma | **Kısmen var.** Bölge Haritası **15 Eylül'den beri** sözleşmede zaten onaylı `lat`/`lon` alanıyla **konum tabanlı** bir görünüm çizer; koordinatı olmayan panolar dağıtım şirketi gruplamasına düşer (`frontend/src/pages/BolgeHaritasi.tsx`) — olmayan veri olmuş gibi gösterilmez. Konum **gerçek trafo GPS pini değil ilçe merkezidir** ve ekranda böyle yazar; gerçek harita karosu yoktur, çünkü yığın internetsiz çalışır (GK4). Kaynak: `docs/17-donanimsiz-dogrulama.md` §6 madde 8 |
| 8 | Üretici bağımsız SCADA entegrasyonu | Modbus TCP 502 (**139 adres**) + IEC 60870-5-104 2404 (**87 kontrol**) + REST; üçü arasında **0 fark** ölçüldü (`docs/03-modbus-haritasi.md`, `docs/04-iec104-haritasi.md`, `docs/17` §4.2). Modbus `conn_temp` 25 noktanın tamamında API değeri × 10, **fark 0** | Her ürün kendi ekosistem ve protokol setini taşıyor; karşılaştırmalı protokol listesi **doğrulanmadı** | — |
| 9 | Koruma cihazına yazma / otomatik açma | **Asla yok.** TVOC-2 aynası salt okunur; FC06/16 ağ geçidinde filtrelenir; IEC 104 kontrol komutları COT 44 ile reddedilir (`docs/03-modbus-haritasi.md` §8 "Yazma güvenliği ve komut bloğu" md. 2–3; COT 44 için `docs/04-iec104-haritasi.md`) | **Doğrulanmadı** | **Karar — GK6.** Eksiklik değil, ürünün güvenlik sınırı |
| 10 | Bulut portalı / üretici uzaktan servisi | **Yok.** Tüm yığın tek makinede, internet kablosu çıkarılmış hâlde çalışır | Bulut panosu ABB SWICOM kaydında doğrulandı (`frontend/TASARIM-REVIZYONU.md` §2) | **Karar — GK4.** İstisna fiilen **iki** kapatılabilir kanaldır: WhatsApp Cloud API ve Telegram Bot API; ikisi de varsayılan **kapalı** ve yalnızca hassas olmayan kısa metin taşır (§c.3) |
| 11 | Kimlik doğrulama, rol tabanlı erişim, kurumsal SSO | **Kısmen var** (18 Eylül, F-19). Onaylayan adı artık istemciden **gelmiyor**: `by` alanı sözleşmeden kaldırıldı (`openapi` v1.2.0) ve doğrulanmış `Authorization: Bearer` başlığından türer (`backend/app/auth.py`, 23 test). Roller: izleyici < operator < muhendis | **Doğrulanmadı** | **Boşluk daraldı, kapanmadı.** Kurumsal SSO/OIDC **değildir** (belirteçler paylaşılan sır; parola, oturum süresi, yenileme, iptal yok); yalnızca **yazma** uçlarını korur; ekranlarda role göre gizleme yapılmadı; **REST/WS tarafında TLS yok** (MQTT taşımasında 18 Eylül'de mTLS geldi — F-27, ayrı profil, `docs/15` §5.1). `GRIDUP_OPERATORS` boşsa tamamen kapalıdır ve bunu `GET /health` söyler. Ayrıntı: `contracts/changes/2026-09-18-kimlik-dogrulama.md` |
| 12 | Sertifikalı donanım, tip testi, EMC/ortam doğrulaması | **Yok.** Tasarım hedefleri belgelendi, **fiziksel doğrulama yapılmadı** (`docs/13-donanim-tasarimi.md`, `docs/11-standartlar-uyum.md` "Kapsanmayan standartlar", `docs/19-tedas-sartname-uyumu.md`) | Ticari ürünler sertifikalı | **Karar — GK3.** "Karşılıyoruz" değil, "tasarım hedefi, tip testi yapılmadı" |
| 13 | Kısmi deşarj ve dalga biçimi imzası | **Yok.** 10 saniyelik skaler mimari seri arkı ve kontak kıvılcımlanmasını **fiziksel olarak göremez** — gerekçesi `docs/13-donanim-tasarimi.md` §7'de toplu | OG tarafında PD ürünleri yerleşik (`HACKATHON_ANALIZ_RAPORU.md` §4) | **Karar — GK3 + MoSCoW Won't.** "Yapabiliriz" denmiyor; bugünkü mimarinin göremediği yazılıyor |
| 14 | Ölçek kanıtı | **1.000 sanal pano**: görünme p95 **763 ms** (20 Eylül; 13 Eylül'de 657 ms ölçülmüştü ve o sayı bugün yeniden üretilemedi — `docs/09` §4.1c), kayıp **0**; alarm → SMS uçtan uca p95 **606 ms**; 10.000 panoda veri kaybetmeden doyma, darboğaz ölçüldü (mesaj başına 615 µs'in **501 µs**'i şema doğrulaması); TimescaleDB sıkıştırma **46–48×** (`docs/09-olceklenebilirlik.md`) | Saha ölçeği ticari platformlarda on binler mertebesinde (`GELISTIRME-BACKLOGU.md` §1) | **Kapsam farkı dürüstçe yazılır:** bizimki **sanal** panodur, saha ölçeği değildir. GK7 en az 100 modül ister, hedef kanıt 1.000 sanal pano |
| 15 | Birim maliyet | **Kontrolcü kartı** — adet 1: **70,73 USD**, adet 1.000: **47,68 USD** (`hardware/pano-beyni/bom.csv` satır toplamı, hücresel modem dahil). **Pano başına toplam** (kontrolcü + N sensör düğümü) adet 1.000'de **103,48 – 396,43 USD**, düğüm sayısına göre — `docs/10` §7. SIM/veri aboneliği, kurulum işçiliği ve tip test **hariçtir** | **Fiyat yazılmadı** (F-15 kuralı); karşılaştırma yapılmamıştır | **19 Eylül düzeltmesi:** bu satır ~56/~37 USD diyordu; fark tam olarak hücresel modem kalemidir (14,50 / 10,80 USD) |
| 16 | Kenar hesabının merkezle bit düzeyinde eşitliği | C ↔ Python RLS farkı: K **1,36e-8**, tau **1,42e-8** (eşik 1e-6) — `docs/17` §3 DH2/DH3 | **Doğrulanmadı** | Bilinen sapma: firmware bellek tüketimi nokta başına **320 B**, hedef 48 B idi (`docs/17` §6) |

### a.4 Sensör katmanı: aynı satıra konmayanlar

Sensör karşılaştırmasında en sık yapılan hata, **bağlantı noktası termal sensörünü** ortam
sensörüyle aynı satıra koymaktır. İkisi aynı kategoride değildir ve birbirinin yerine geçmez.

| Ürün | Ne ölçer | **Kategori** | Bizdeki karşılığı |
|---|---|---|---|
| **Schneider Easergy TH110** | Bağlantı noktası (kontak) sıcaklığı; iletkenin manyetik alanından enerji hasadı, kablosuz | **Bağlantı noktası termal sensörü** | Pano Beyni'nin izlediği nokta sıcaklıkları (`contracts/modbus-map.yaml`, `hardware/pano-beyni/io-tablosu.md`). Sensör seçimi **tasarım düzeyindedir**, fiziksel doğrulama yapılmadı (GK3) |
| **Schneider Easergy CL110** | **Ortam** sıcaklığı ve bağıl nemi | **Ortam sensörü** — TH110 ile aynı kategori değildir | Ortam T/RH ve **çiy noktası marjı**: `libs/panoalgo/panoalgo/physics.py` `dew_point()` / `dew_point_margin()` (Magnus formülü) |
| **Schneider PowerLogic HeatTag** | Pano havasındaki gaz ve mikro partikül; yalıtım bozunumunu 170–200 °C bandında, duman çıkmadan | Gaz/partikül sensörü | **Bizde yok** — donanım alınmadı (GK3); gaz/VOC senaryosu MoSCoW "Could" |
| **ABB TVOC-2** | Optik ark tespiti, <1 ms açma | **Koruma cihazı** (sensör değil) | Sensör olarak **okunur**, yazılmaz: salt okunur ayna (GK6). `ALM-ARC-TRIP` tek kanıtıyla risk 100 üretir (`libs/panoalgo/panoalgo/fusion.py`) |
| **ENTES MPR-53CS** (panoda **zaten var**) | Akım, gerilim, THD, dengesizlik | **Mevcut enerji analizörü** | Yeni cihaz alınmadan **sensör olarak okunur** — kaynak alanları `contracts/modbus-map.yaml` `source:`; simülatörü `sim/mpr53cs_sim.py`, register mantığı `libs/panoalgo/panoalgo/devices.py` içinde testli |

Kaynak: `HACKATHON_ANALIZ_RAPORU.md` §4 ve `GELISTIRME-BACKLOGU.md` §2 md. 11 (se.com, DOCA0171EN).
Bu satırların hiçbirinde ürün **fiyatı** veya "onlarınki kötü" değerlendirmesi yoktur.

**Bu tabloda yer almayan iki sensör kategorisi** — akustik/ultrasonik dinleme ve termal görüntü —
bilerek kapsam dışıdır; gerekçeleri ve gerekçelerin sınırları §(c)'dedir.

### a.5 ADM/GDZ'nin EcoStruxure ADMS alımına konumlanma

ADM Elektrik ve GDZ Elektrik (aynı grup) **20 Mayıs 2026**'da Schneider Electric + Inavitas ile
EcoStruxure ADMS anlaşması imzaladı: **SCADA ve Kesinti Yönetim Sistemi yenileniyor**, DMS/DERMS ve
CBS entegrasyonu kapsamda, 5 ilde 6M+ abone (kaynak: `GELISTIRME-BACKLOGU.md` §2 md. 4 —
enerjibulteni.com, aa.com.tr).

Bu bizim için bir tehdit değil, **konum tarifidir**: ADMS bir kontrol ve kesinti yönetim katmanıdır;
AG panosunun içindeki bağlantı noktası sıcaklığını, çiy marjını ve ısıl direnç indeksini ölçen bir
katman değildir. Biz onun **yerine** değil, **altına** konumlanıyoruz — ve bağlantı noktamız zaten
mevcut ve ölçülmüş: IEC 60870-5-104 kontrollü istasyon, 87 kontrol, REST ve Modbus ile **0 fark**
(`docs/04-iec104-haritasi.md`, `docs/17` §4.2).

> **Bölümün sonucu — sunuma çıkacak tek cümle:**
> **"Onların platformu geliyor; biz onun altındaki ölçüm katmanıyız. Bugün IEC 104 ile bağlanırız,
> koruma devresine asla yazmayız."**

---

## (b) Analitik standart izi: standart → kod dosyası → ölçülen sonuç → dürüst boşluk

**Erişim durumu (hepsi için aynı):** ISO 17359, ISO 13379-1, ISO 13381-1 ve CIGRE TB 858
**metinlerine bu teslimde erişilmedi.** Aşağıdaki "neyi ister" hücreleri **bölüm başlığı
düzeyindedir**, madde/tablo numarası içermez ve birebir alıntı değildir. Standartların ne istediğine
dair özetler `GELISTIRME-BACKLOGU.md` §2 (md. 14, 15) ve kodun kendi başlık yorumlarından gelir;
uyum **iddia edilmemekte**, yalnızca hangi kod dosyasının hangi standardın konusuna denk düştüğü
gösterilmektedir.

| Standart | Neyi ister (bölüm başlığı düzeyinde) | Bizdeki karşılığı (**kod dosyası**) | Ölçülen | **Dürüst boşluk** |
|---|---|---|---|---|
| **ISO 17359** — durum izleme ve tanı, genel kılavuz | Durum izleme **programı** kurulması; makine kararlıyken alınmış bir **baz çizgisi**; ve **alarm kriterinin zaman içinde yinelemeli optimize edilmesi** | Baz çizgisi: `libs/panoalgo/panoalgo/detect.py` → `freeze_baseline()` (K₀ = kestirim geçmişinin **medyanı**; ortalama değil, çünkü tek sıçrama tabanı bozar). Filo düzeyi: `libs/panoalgo/panoalgo/edge.py` → `freeze_baselines()`. Öğrenme penceresi `baseline_learning_days = 7` ve eşikler (`k_ratio_warn` 1,3 / `k_ratio_alarm` 1,6) `contracts/alarm-codes.yaml`'da | Taban donmadan `k_ratio` 1,0 döner → devreye alma günü sahte alarm yağmuru yok (`docs/05` §3.4). Eşiğin veriyle savunulması: `scripts/threshold_sweep.py` ile taranmış, sonuçlar `docs/05` §11 ve §a.3 satır 3. Erken uyarı: **209,0 saat** (`docs/12` §2) | **Kısmen karşılandı (F-32, 18 Eylül).** Baz çizginin "makine kararlıyken" alındığı artık **sınanıyor**: donma anında bir kanıt kaydı tutuluyor (`detect.py` → `BaselineEvidence`: kaç örnek, kaçı uyarılmış, dağılım ne kadar dar) ve öğrenme penceresinin kendi içinde kalıcı bir kayma taşıyıp taşımadığı CUSUM ile ölçülüyor (`onset.py` → `baseline_window_is_stable`). Üçüncü kanıt akran konumudur (`fleet.py`). Üçünden biri düşükse **yeniden baz alma önerilir** — `GET /api/v1/fleet/peers`, gerekçesiyle birlikte. **Kalan boşluk:** öneri **otomatik uygulanmıyor** ve eşikler dondurulmuş sözleşmede sabit; standardın istediği kapalı döngü yinelemeli optimizasyon bu değildir. Otomatik yeniden baz alma **bilerek** yapılmadı: bozulmakta olan bir noktada tabanı güncellemek `k_ratio`'yu 1,0'a geri çeker ve gerçek bozulmayı görünmez kılar (`docs/07b` **Y11**). Karar operatöründür |
| **ISO 13379-1** — durum izleme ve tanı, veri yorumlama ve tanı teknikleri | Semptom ile arıza modu arasındaki ilişkinin **izlenebilir** kurulması; gözlemden teşhise giden yolun gösterilmesi | Hipotez → kanıt → skor füzyonu: `libs/panoalgo/panoalgo/fusion.py` (`S_h = (mevcut kanıt / toplam kanıt) × severity_w`, mod = argmax). Hipotez tanımları koda **gömülü değil**: `contracts/alarm-codes.yaml` `hypotheses` bloğu (9 hipotez, `evidence` listeleri ve `severity_w`). Karşı-olgusal yön: `backend/app/risk.py` → `_verify()` (F-10 "Ne doğrulanmalı" bloğu, eksik kanıtları döndürür); arayüz tipi `frontend/src/api/types.ts` `AlarmReason.verify` | Alarm kodu düzeyinde: beklenen alarmı olan **8 senaryoda recall 1,00**, 10 senaryonun hiçbirinde yasaklı alarm yok (`docs/12` §1). `_verify()` aynı zamanda skorun neden 100 olmadığının açıklaması: füzyon skoru kanıt oranı üzerinden hesaplanır | **Teşhis doğruluğu (hipotez/mod düzeyi) ölçülmedi.** `docs/12` §1 **alarm kodu** düzeyinde ölçer; "doğru arıza modunu mu seçti" sorusunun ölçülmüş cevabı yok. Kanıt **ikili** (var/yok); dereceli semptom ağırlığı yok — gerekçesi `fusion.py` başlığında yazılı (eşiksiz kodlarda dereceli karşılık olmadığı için). L2 katmanı **kısmen kod üretiyor** (F-32, 18 Eylül): üç yöntemden **ikisi** kodda — filo akran karşılaştırması (`fleet.py`, MAD tabanlı modifiye z) ve CUSUM değişim noktası (`onset.py`, bozulmanın başlangıç anı); **saat-of-hafta robust z hâlâ yok**. Sözleşmede `layer: L2` etiketli alarm kodu **hâlâ yok** ve F-32 bilerek açmadı (her kodun bir `bit` alanı var; yeni kod Modbus tahsisini ve beş üretecin çıktısını tetikler). L2'nin çıktısı bu yüzden alarm değil **öneri**: `GET /api/v1/fleet/peers`. **Sentetik veride ölçülen sınır (GK10):** üreteç sağlıklı K₀'ı sınırlı düzgün dağılımdan çektiği için sağlıklı bir pano yapısal olarak aykırı çıkamaz — ölçülen en büyük |z| **1,534**, eşik **3,5**; buradan çıkan ayrım oranı saha başarımı değildir (`docs/05` §10) |
| **ISO 13381-1** — durum izleme ve tanı, **prognoz** | Kalan ömür kestirimi; prognozun **doğrulanması** ve sonucun bir **güven ifadesiyle** verilmesi | `libs/panoalgo/panoalgo/detect.py` → `_ttl_h()` / `time_to_limit()` (K'nin EWMA eğimi + 168 kutulu saat-of-hafta yük profili; üç durumda `null` döner — uydurmak yerine susar). Geri test ölçütleri: `libs/panoalgo/panoalgo/prognostics.py` (α-λ, prognostic horizon, relative accuracy, convergence — Saxena ve ark. 2010 / NASA Prognostics Metrics Library) | **Ölçüldü ve olumsuz çıktı** (`docs/12` §4): `S1_loose_conn`'da **790 tahmin**, ihlal öncesi yalnızca **%5,2**'si α = 0,20 konisinde; **prognostic horizon YOK**; **CRA −5,12**; medyan tahmin/gerçek **1,69**. İhlale 48 saatten az kala koni içinde kalma oranı **%0**. `S2_overload`'da **hiç tahmin üretilmedi**. `S8_sensor_fault`'ta sınır **hiç aşılmadığı hâlde 183 tahmin** üretildi ve **86'sı** `ALM-TTL-14D` alarmına döndü — bu bir **prognoz yanlış-alarmıdır** ve `docs/12` §3'teki yanlış alarm sayacı onu **görmez** | **Bu tablonun en önemli satırı.** `ttl_h` bugün **güvenilir bir kalan ömür kestirimi değildir** ve bunu yumuşatmıyoruz. Standardın istediği **güven ifadesi üretilmiyor**: sonuç **tek yörüngeden** gelir (**n = 1**), **güven aralığı yoktur**. Ayrıca manşetteki **209 saatlik öne almayı tetikleyen kod `ALM-TTL-14D`'dir, yani prognozdur; K/K₀ eşiğine dayanan öne alma 172,5 saattir** — ikisi karıştırılmamalıdır (`docs/05` §10) |
| **CIGRE TB 858** — varlık sağlık indeksleri | Varlık **sağlık indeksi** kurulması ve indeksin **monotonluk** ilkesine uyması: daha fazla ya da daha ağır kanıt indeksi düşürmemeli | Risk skoru 0–100: `libs/panoalgo/panoalgo/fusion.py` (`RiskResult.score`, `contributions`). Monotonluk **özellik testiyle** sınanıyor: `libs/panoalgo/tests/test_fusion.py` — sözleşmedeki kanıt kodlarının **0–3 elemanlı tüm alt kümeleri** taban alınıp her tabana kalan her kod tek tek ekleniyor, üç ayrı özellik kümesiyle | Monotonluk testi geçiyor; `libs/panoalgo` **410/410** test yeşil (18 Eylül 2026, bu dalda ölçüldü). Risk skorunun bildirim kararını **yönetmediği** kodda yazılı: SMS/arama kararı alarm önceliğinden (P1/P2/P3) çıkar, skordan değil | **Boşluk daraldı, kapanmadı** (18 Eylül, F-21). Risk matrisinin artık **gerçek bir etki ekseni var**: y = `abone_sayisi`, varlık künyesinden gelir (`contracts/openapi.yaml` v1.3.0 `AssetRegistry`, göç `deploy/initdb/008_varlik_kutugu.sql`). Abone sayısı **sayılabilir** bir büyüklüktür ve EPDK Kalite Yönetmeliği Madde 8/2 zaten "etkilenen kullanıcı sayısı"nı istiyor; eski kVA itirazı (filodaki her panoda **aynı** `pano_type`) böylece aşıldı. **Kalan sınır:** matris **künye girildiği ölçüde** iki boyutludur — künyesi içe aktarılmamış pano ayrı bir şeritte gösterilir ve y=0'a **konmaz** ("abonesi yok" ile "abone sayısı bilinmiyor" ayrı şeylerdir), hiçbir panonun künyesi yoksa eski tek boyutlu davranış **aynen** korunur. **Bu teslimde demo filosunun künyesi boştur** (GK3: gerçek bir CBS aktarımına erişim yok) ve bu `GET /fleet/assets` `kapsama` alanında sayıyla görünür. Sağlık indeksinin **kendisi** hâlâ yaş ve bakım geçmişi içermiyor: künye bunları taşıyor ama `fusion.py` skoru onları **okumuyor** — kritiklik bir **etki** ekseni olarak duruyor, sağlık indeksine karıştırılmadı. Ayrıntı: `contracts/changes/2026-09-18-varlik-kutugu.md` |
| **IEC 62974-1** — cihazın **ürün sınıfı** standardı | — | — | — | Bu doküman kapsamı dışıdır: ürün sınıfı standardı olarak `docs/11-standartlar-uyum.md`'de işlendi |

### b.1 İzin tek cümlelik özeti

Durum izleme tarafında (ISO 17359 / ISO 13379-1 konuları) kodun standartla aynı **konuyu** konuştuğu
ve sonuçlarının ölçüldüğü gösterilebiliyor; prognoz tarafında (ISO 13381-1 konusu) **ölçtük ve
tutmadı** — bunu jüri bulmadan biz yazıyoruz. Bu dokümanın varlık sebebi tam olarak budur.

---

## (c) Kapsam dışı bırakılan veri türleri ve kanallar

Bu bölüm §(a)'nın son sütunundaki işi üçüncü bir eksende yapar: **bizde olmayan bir şeyin boşluk mu
yoksa yazılı bir kapsam kararı mı olduğunu** ayırır. Buraya üç kalem giriyor — ikisi **veri türü**
(akustik, termal görüntü), biri **bildirim kanalı** (WhatsApp).

**Neden ayrı bir bölüm gerekti: depodaki gerekçeler asimetrikti.** Termal görüntü için yazılı bir
gerekçe vardı (`docs/01-problem-analizi.md` md. 7; `HACKATHON_ANALIZ_RAPORU.md` satır 49, 209, 1101).
Akustik için ise yalnızca iki MoSCoW satırı vardı — "Won't (bu teslimde): … ultrasonik algılama"
(`HACKATHON_ANALIZ_RAPORU.md` satır 1050) ve "Ultrasonik (~40 kHz) yüzeysel kaçak/ark sesi dinleme …
Won't" (aynı dosya satır 1133). **Bir MoSCoW etiketi bir gerekçe değildir.** Aşağıdaki üç madde o
boşluğu kapatır; jüri sorduğunda verilecek cevap burada hazırdır.

> **Bölümün tamamı için geçerli tek cümle.** Buradaki hiçbir madde bir **bulgu** değildir. Bu depoda
> ne bir akustik ölçüm yapıldı, ne bir termal görüntü alındı, ne de WhatsApp Cloud API'ye gerçek bir
> istek gönderildi. Bu yüzden hiçbir yerde "işe yaramaz" denmiyor; **"bu teslimde kapsam dışı
> bırakıldı, gerekçesi şu"** deniyor. **"Ölçmedik" ile "gereksiz" aynı şey değildir.**

### c.1 Akustik / ultrasonik dinleme — kapsam kararı

**Depodaki durum (20 Eylül 2026'da arama ile ölçüldü):**

| Nerede | Ne var |
|---|---|
| `HACKATHON_ANALIZ_RAPORU.md` satır 455 (sensör seti S4) | Üst ortam düğümünde **"ops. ultrasonik (~40 kHz) mikrofon"** — baştan beri *opsiyonel* |
| `HACKATHON_ANALIZ_RAPORU.md` satır 1050 ve 1133 | MoSCoW **Won't** (iki ayrı satır; gerekçe yazılmamış) |
| `HACKATHON_ANALIZ_RAPORU.md` satır 427 | "Mikrofonla PD dinleme" — diğer takımların yapacağı **yaygın hata** listesinde |
| `contracts/mqtt-telemetry.schema.json` | Akustik alan **yok.** Kök nesne `additionalProperties: false` ve izin verilen alanlar yalnızca: `v, ts, pano_id, seq, fw, t_conn, elec, env, tvoc, pd, risk, alarms, health` |
| `contracts/alarm-codes.yaml` | Akustik bir alarm kodu **yok** (23 alarm kodu; PD ekseninde tek kod `ALM-PD-TREND`) |
| `hardware/*/bom.csv` (üç BOM) | Mikrofon / ultrasonik dönüştürücü satırı **yok** |

**Gerekçe — dört madde:**

1. **Akustik, bu ürün bağlamında öncelikle bir PD yöntemidir; PD ise zaten OG kapsamına alındı.**
   Depoda anılan standardın adı **IEC TS 62478**'dir ve depodaki tanımı "elektromanyetik ve akustik
   PD yöntemleri"dir (`HACKATHON_ANALIZ_RAPORU.md` satır 873; `docs/11-standartlar-uyum.md` satır 11
   ve "Kapsanmayan standartlar" bölümü). **Madde numarası verilmiyor — standardın metnine bu teslimde
   erişilmedi.** PD'nin AG'de değil OG'de anlamlı olduğu kararı ve gerekçesi zaten yazılı:
   `docs/05-anomali-tespiti.md` §10 ("PD yalnızca OG içindir"), `docs/13-donanim-tasarimi.md` §7.1–7.2,
   ve §a.3 satır 13. Akustik yöntem **aynı kapsam kararının içine** düşer: AG panoda aranacak olayın
   kendisi nadir kabul edildiyse, onu ikinci bir fizikle aramanın gerekçesi de aynı ölçüde zayıftır.
   Bu bir **tutarlılık** argümanıdır — akustiği kendi başına çürütmez, onu var olan bir karara bağlar.
2. **Pano kabini akustik olarak sessiz bir ortam değildir.** Deponun kendi çevresel tablosu mekanik
   uyarıcıları sayıyor: "Trafo uğultusu, deprem (0,5 g)" (`HACKATHON_ANALIZ_RAPORU.md` satır 826).
   Buna kendi tasarımımızın anahtarlama elemanları ekleniyor: iki kuru kontak rölesi
   (`hardware/pano-beyni/bom.csv`, Omron G5LE-1-VD 24DC ×2) ve bunlardan biri **ısıtıcı/fan** çıkışıdır
   (`hardware/pano-beyni/io-tablosu.md`, `RELAY2` satırı; `hardware/pano-beyni/blok-diyagrami.md`
   röle çıkışı bloğu). Şartname ayrıca alttan girişli/üstten çıkışlı **havalandırma** istiyor
   (`docs/19-tedas-sartname-uyumu.md` md. 2.2.8.5).
   Ultrasonik bandın duyulabilir banttan daha temiz olması **beklenir**, ama bu depoda ne pano içi
   gürültü tabanı ne de ultrasonik arka plan **ölçüldü** — bu bir beklentidir, ölçüm değil.
3. **Eşiği olmayan bir kanal, ölçülmüş yanlış alarm bütçesini harcar.** Bu depoda ölçülen tek gerçek
   yanlış alarm kaynağı çiy eşikleridir: S0'da **71,4** alarm/100 pano/gün, sözleşme sınırı 150
   (`docs/12-dogrulama-sonuclari.md` §3; §a.3 satır 3). Eşiği hiç taranmamış yeni bir sürekli kanal bu
   bütçeyi tüketir. Akustik için bir eşik **uydurmak** ise deponun kendi kuralına aykırıdır:
   `ALM-PD-TREND`'in eşiği tam bu yüzden bilerek boş bırakıldı, yerine bir `scope:` notu düşüldü
   (`contracts/alarm-codes.yaml`; `docs/13` §7.1) — değerlendirilecek veri gelmiyorsa eşik yazmak,
   olmayan bir yeteneği var gibi gösterir.
4. **Veri mimarisi sınırı.** Telemetri sözleşmesi **10 saniyelik skaler özet** taşır; ham örnek dizisi
   veya dalga biçimi alanı yoktur (`docs/13` §7.3). Akustik bir kanal ya kenarda kendi özetine
   indirgenmek zorundadır (ki o özetin eşiği yoktur — md. 3), ya da sözleşmenin taşımadığı bir veri
   tipi ister. Sözleşme donmuştur (`contracts/mqtt-telemetry.schema.json` açıklama alanı:
   "DONMUSTUR (PLAN.md kural 3)"; özellik dondurma `PLAN.md` GK2, 17 Eylül 23:59).

> **Gerekçenin sınırı — bu paragraf atlanmamalıdır.** Akustik/ultrasonik izleme yalnızca kısmi deşarj
> için kullanılmaz; sahada **mekanik gevşeme** ve **korona** için de kullanılır. **Bu iki kullanımı ele
> almadık.** Bu depoda bu iki konuda ne bir literatür taraması, ne bir hesap, ne bir ölçüm vardır;
> "akustik bir yöntem gevşek bağlantıyı ısıl direnç indeksinden daha erken görür mü" sorusunu **hiç
> sormadık**. Dolayısıyla yukarıdaki dört madde *"akustik AG panoda gereksizdir"* demez; **"bu teslimde
> akustiği kapsam dışı bıraktık ve gerekçemiz PD ekseninde kuruludur"** der. Gerekçenin PD dışında
> kalan yarısı **açık boşluktur** ve bir sonraki fazın konusudur.

**Jüri sorarsa tek cümle:** "Akustiği ölçmedik; PD'yi OG'ye aldığımız kararın aynısını akustiğe de
uyguladık. Ama gerekçemiz yalnızca PD eksenini kapsıyor — mekanik gevşeme ve korona için akustiğin ne
getireceğini bilmiyoruz, ölçmedik."

### c.2 Termal görüntü (termal dizi / termal kamera) — kapsam kararı

**Mevcut gerekçe (buraya taşınıyor).** Saydam kapak polikarbonat/camdır ve uzun dalga kızılötesini
(8–14 µm) geçirmez; şartname baraların önünde alev almaz saydam gözetleme pencereli kapak istiyor. Bu
yüzden kapağın **dışına** konan bir termal kamera sahada çalışmaz. Kaynaklar:
`docs/01-problem-analizi.md` md. 7; `HACKATHON_ANALIZ_RAPORU.md` satır 49, 209, 409, 1101;
`docs/19-tedas-sartname-uyumu.md` md. 2.2.6.1.

**Bu gerekçenin eksiği — açıkça yazıyoruz.** Yukarıdaki argüman **kapağın dışındaki kamerayı** çürütür,
**teknolojinin kendisini değil.** Deponun kendi tasarımı çözümü zaten söylüyor: termal dizi (S2)
**kapağın İÇ tarafına** monte edilir (`HACKATHON_ANALIZ_RAPORU.md` satır 258 ve 453;
`docs/08-kurulum-proseduru.md` §2 md. 4; `hardware/yerlesim/ek2-14-yerlesim.svg` çiziminde birebir not:
"Termal dizi, saydam kapagin IC tarafi (sartname 2.2.6.1: PC/cam LWIR gecirmez)"). Yani termal dizi
**reddedilmedi; tasarımda duruyor ama uygulanmadı.** İkisi farklı şeylerdir ve doğru olan ikincisidir.

**Depodaki gerçek durum:**

| Nerede | Termal dizi (S2) |
|---|---|
| MoSCoW (`HACKATHON_ANALIZ_RAPORU.md` satır 1049) | **"Could"** — Must değil |
| Ürün paketi (`docs/10-bom-maliyet-roi.md` §1, "Temel") | Pakette yazılı: "termal dizi (1–2 adet)" |
| Yerleşim çizimi (`hardware/yerlesim/ek2-14-yerlesim.svg`) | **Var** (kapak içi braket, notuyla) |
| Kurulum prosedürü (`docs/08` §2 md. 4) | **Var** |
| BOM (`pano-beyni/`, `sensor-dugumu/`, `pd-karti/`) | **Yok** — üç `bom.csv`'nin hiçbirinde termal dizi satırı yok |
| Telemetri sözleşmesi | **Yok** — `t_conn` nokta sıcaklıklarıdır; dizi/piksel alanı yoktur, kök nesne `additionalProperties: false` |
| Alarm kodu / algoritma | **Yok** |

**Neden seçilmedi — üç gerekçe:**

1. **Yayınım (emissivity) belirsizliği.** Sözleşmenin tanımladığı 25 bağlantı noktası **doğrudan
   temasla** ölçülür: `hardware/sensor-dugumu/bom.csv` satırları TMP117 ("bara temas yuzeyine
   yakin") ve Bergquist Sil-Pad termal ped ("bara temas yastigi") — bunlar BOM'un kendi parça
   tanımlarıdır; hiçbiri **üretici veri sayfasına karşı doğrulanmadı**
   (`docs/19-tedas-sartname-uyumu.md` §3). Temas ölçümü yüzeyin yayınımından **bağımsızdır.**
   Termal dizi ise **radyometriktir**: okuduğu değer baktığı yüzeyin yayınımına bağlıdır ve pano
   içinde yan yana duran çıplak/kalaylı iletken, boyalı sac ve yalıtım malzemesi aynı yayınıma
   sahip değildir. Düzeltmek için bölge bölge bir yayınım katsayısı **girilmesi** gerekir — bu,
   devreye almaya elle bir kalibrasyon adımı ekler ve "bakım gerektirmeyen" hedefiyle (rapor §2.1 R11)
   gerilir. **Bu bir mühendislik gerekçesidir, bu depoda yapılmış bir ölçüm değildir:** ne yayınım
   ölçüldü, ne de iki yöntem karşılaştırıldı.
2. **Görüş alanı ve montaj kısıtı.** Termal dizi ancak **gördüğünü** ölçer ve kapağın iç tarafındaki tek
   braketten DSYA sıralarına bakar (`HACKATHON_ANALIZ_RAPORU.md` satır 453). Sözleşmedeki 25 noktanın
   (`contracts/modbus-map.yaml` `conn_temp.points`; `docs/10` §7.1) kaçının bu görüş alanına girdiği
   **hesaplanmadı**; braketin kapak/kilit işlevini ve Form 2B ayrımını bozup bozmadığı da **fiziksel
   olarak denenmedi** — bu zaten `docs/19` md. 2.2.6.1'de açık boşluk olarak duruyor. Noktasal düğüm bu
   belirsizliği taşımaz: hangi noktayı ölçtüğü sözleşmede **adıyla** yazılıdır (`GIRIS_L1` … `DSYA7_L3`).
3. **Sözleşme ve kapsam.** Termal dizi çıktısı (bölge maskesi, bölge başına maksimum —
   `HACKATHON_ANALIZ_RAPORU.md` satır 642) donmuş telemetri sözleşmesinde karşılığı **olmayan** bir veri
   tipidir. 17 Eylül özellik dondurmasından sonra sözleşmeye alan eklenmedi (`PLAN.md` GK2). "Could"
   seviyesindeki bir kalem için donmuş sözleşmeyi açmak, ölçülmüş olan L0/L1 zincirini riske atardı.

**Maliyet — yalnızca depodaki gerçek sayılar (adet 1.000):**

| Kalem | Kaynak | Adet 1.000 |
|---|---|---:|
| Sensör düğümü (bir bağlantı noktası ölçer) | `hardware/sensor-dugumu/bom.csv` toplam satırı | **13,95 USD/düğüm** |
| 7 düğüm (ölçümlerin çoğunun yapılandırması) | `docs/10` §7.2 | 7 × 13,95 = **97,65 USD** |
| 25 düğüm (sözleşmenin tamamı) | `docs/10` §7.2 | 25 × 13,95 = **348,75 USD** |
| **Termal dizi modülü** | — | **Depoda fiyat YOK** — üç `bom.csv`'nin hiçbirinde satırı yok |

**Bu tablodan çıkan dürüst sonuç:** "termal dizi daha ucuz / daha pahalı" **diyemiyoruz ve
demiyoruz** — karşılaştırmanın bir tarafı ölçülü, diğer tarafı depoda hiç yok. Söyleyebildiğimiz tek
şey şudur: pano maliyetini belirleyen kalem düğüm sayısıdır (25 düğümde pano toplamının **%88,0'ı** —
`docs/10` §7.2), dolayısıyla termal dizinin ekonomik savı "nokta sensör sayısını azaltmak"tır
(`HACKATHON_ANALIZ_RAPORU.md` satır 453) ve **bu sav bu teslimde sayıyla sınanmadı.**

**Jüri "termal kamera neden yok?" derse verilecek cevap:** "Kapağın dışından çalışmaz — polikarbonat
8–14 µm'yi geçirmez ve bu, şartnamenin kendi maddesinden çıkar. Ama bu argüman teknolojiyi değil o
montajı çürütür; bizim yerleşim çizimimizde termal dizi zaten kapağın içinde duruyor ve MoSCoW'da
'Could'. Uygulamadık, çünkü (i) temasla ölçüm yayınım belirsizliği taşımaz, termal dizi taşır ve bölge
bölge kalibrasyon ister; (ii) tek braketin görüş alanına 25 noktanın kaçının girdiğini hesaplamadık;
(iii) sözleşme 17 Eylül'de dondu ve dizi verisi için alan yok. Maliyet karşılaştırması yapamıyoruz:
düğüm fiyatımız ölçülü (adet 1.000'de 13,95 USD), termal dizi modülünün fiyatı ise depomuzda yok."

### c.3 Bildirim kanalları: gösterilebilir ikincil kanal **Telegram**'dır

| Kanal | Kod | Test | Varsayılan yapılandırma | **Gerçek servise karşı denendi mi?** | **Jüri deneyebilir mi?** |
|---|---|---|---|---|---|
| **SMS** (birincil) | `backend/app/notify/sms_modem.py`, `pdu.py` | var | `SMS_DEVICE=socket://gsm-modem:7000` (`deploy/.env.example`) | **Modem gerçek donanım değil**, sanal: `scripts/virtual_gsm_modem.py`. Sürücü gerçek AT/PDU (`docs/17-donanimsiz-dogrulama.md` §2, GSM modem satırı) | **Evet** — yığın içinde çalışır, çıktı `deploy/runtime/sms-log.txt` |
| **Telegram** (ikincil) | `backend/app/notify/telegram.py` | `backend/tests/test_telegram.py` | `TELEGRAM_BOT_TOKEN=` ve `TELEGRAM_CHAT_ID=` **boş** (`deploy/.env.example` satır 108–109) → kanal kapalı (`backend/app/notify/dispatcher.py` satır 95–97) | **Hayır.** Testler tamamen `httpx.MockTransport` (`test_telegram.py` satır 23, 66); gerçek telefona teslim kanıtı **yok**, gecikme **ölçülmedi** — bu zaten `docs/20-p0-kanit-ve-sinir-raporu.md` §3 md. 7 ve §4 md. 5'te yazılı | **Evet, ama tarif eksiktir.** `README.md` §"Kendi Telefonunuza Bağlama" yalnızca `TELEGRAM_CHAT_ID` girmeyi söyler; `dispatcher.py:95-97` kanalı açmak için **hem belirteç hem chat id** ister ve `TELEGRAM_BOT_TOKEN` varsayılan boştur. Jürinin iki yolu var: (1) ekip `@gridupalarmbot` belirtecini ayrıca verir (bir **sırdır**, depoya commit edilmez), ya da (2) jüri BotFather'dan **kendi** botunu alıp iki değişkeni de yazar. İkisi de dakikalar sürer — WhatsApp'tan farkı budur |
| **WhatsApp** (ikincil) | `backend/app/notify/whatsapp.py` | `backend/tests/test_whatsapp.py` | `WHATSAPP_TOKEN=` ve `WHATSAPP_PHONE_ID=` **boş** (`deploy/.env.example` satır 99–100) → kanal kapalı (`dispatcher.py` satır 85–87) | **Hayır.** Testler tamamen `httpx.MockTransport`; test dosyasının kendi başlığı bunu yazıyor: "Gercek API'ye gidilmez" (`test_whatsapp.py` satır 6). `docs/17` §2 bu satırı zaten **"gerçek telefona teslim bekliyor"** diye işaretlemişti | **Hayır.** Meta Cloud API bir **işletme hesabı** ve doğrulanmış numara ister; `.env.example` satır 98 demo sınırını da yazıyor ("Meta test numarasi en fazla 5 dogrulanmis aliciya gonderir"). Jüri bunu masa başında kuramaz |

**Ölçtüğüm (20 Eylül 2026, `tuna/polish` dalı):**

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_whatsapp.py tests/test_telegram.py -q
# -> 19 passed in 0.48s
```

Bu 19 testin **hiçbiri ağa çıkmaz.** Ölçtükleri şey üretilen HTTP isteğinin **biçimidir** (uç nokta,
`Authorization` başlığı, gövde JSON'u, şablon/serbest metin ayrımı) ve hata sınıflandırmasıdır
(`retryable` ayrımı, belirtecin hata metnine sızmaması). **Teslim ölçülmedi. Birim testi bir teslim
kanıtı değildir.**

**İki kanalda da belirteç boş — fark nerede?** Ölçtüm: `deploy/.env` (depoya girmez, `.gitignore`
satır 3) içinde `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID`
**dördü de boştur**; `deploy/.env.example`'da da dördü boş gelir. Fark belirtecin boşluğunda değil,
**doldurulabilirliğindedir:**

- **Telegram:** belirteç jürinin kendi telefonundan, kendi botuyla, dakikalar içinde üretilir. Bu yüzden
  **gösterilebilir ikincil kanal Telegram'dır.** Gösterilen şey "bizim kanalımız çalışıyor" değil,
  "jüri kendi hesabıyla kanalı açıp alarmı kendi telefonunda görebilir"dir.
- **WhatsApp:** belirteç bir Meta işletme hesabı, doğrulanmış işletme numarası ve 24 saatlik müşteri
  hizmeti penceresi dışında **onaylı şablon** ister (`backend/app/notify/whatsapp.py` başlık yorumu;
  `deploy/.env.example` satır 94–98). Bunlar jüri masasında kurulamaz.

> **Açıkça yazıyoruz.** **WhatsApp kanalı gerçek Meta Cloud API'ye karşı hiç denenmedi; yalnızca birim
> testleriyle doğrulandı.** Bu depoda hiçbir yerde "WhatsApp çalışıyor" izlenimi bırakılmamalıdır.
> **Telegram için de gerçek telefona teslim kanıtımız yoktur** (`docs/20` §4 md. 5) — Telegram'ın farkı
> kanıtta değil, **jürinin kendisinin deneyebilmesindedir.**

**Brief'le ilişkisi.** Gereksinim R8 "SMS/WhatsApp alarm mekanizması" der (`HACKATHON_ANALIZ_RAPORU.md`
§2.1). Karşıladığımız şey: **SMS** (sanal modemle uçtan uca, `docs/17` §2 ve §4) + WhatsApp ve Telegram için
**kanal kodu ve birim testi**. WhatsApp'ın kapatılabilir olması aynı zamanda GK4'ün (public cloud yok)
tek yazılı istisnasıdır (`PLAN.md` satır 26; §a.3 satır 10).

> **Kendi kuralımızla bir gerilim — jüri bulmadan biz yazıyoruz.** GK4'ün istisna cümlesi **yalnızca
> WhatsApp Cloud API'yi** adlandırır (`PLAN.md` satır 26). Telegram Bot API de şirket dışı bir buluttur
> ve bu kanal 17 Eylül'de, kural yazıldıktan sonra eklendi; üstelik `HACKATHON_ANALIZ_RAPORU.md` satır
> 424 "Firebase/ThingSpeak/AWS + Telegram bot"u **"public cloud yasak"** başlığı altında sayıyor. Kuralı
> fiilen bozmayan tek şey şudur: kanal **varsayılan kapalıdır** ve belirteç girilmedikçe istemci hiç
> oluşturulmaz (`dispatcher.py` satır 95–97) — yığın internet kablosu çıkarılmış hâlde çalışmaya devam
> eder. Yine de GK4'ün metni bugün eksiktir: istisna listesi fiilen **iki kanaldır**, bir kanal değil.

---

## Bu doküman neyi **kanıtlamaz**

1. **Standart uyumu kanıtlamaz.** ISO 17359, ISO 13379-1, ISO 13381-1 ve CIGRE TB 858 metinlerine
   erişilmedi; hiçbir madde numarası verilmedi, hiçbir alıntı yapılmadı ve hiçbir yerde
   "bu standardı karşılıyoruz" denmedi. Tablo yalnızca **konu eşlemesidir**.
2. **Rakip ürünlerin yetersizliğini kanıtlamaz.** Doğrulanan her özellik kaynağıyla yazıldı,
   doğrulanamayan her hücre "doğrulanmadı" olarak bırakıldı. Fiyat karşılaştırması **yapılmadı**.
3. **Saha başarımını kanıtlamaz.** Buradaki her sayı **sentetik senaryolardan** ve **sanal
   panolardan** gelir; gerçek bir AG panosunda ölçüm yapılmadı, donanım üretilmedi (GK3).
   Donanımsız doğrulamanın kapsamı `docs/17-donanimsiz-dogrulama.md` §5–§6'dadır.
4. **Prognozun çalıştığını kanıtlamaz — tersini gösterir.** §(b) ISO 13381-1 satırındaki sonuçlar
   n = 1 yörüngeden gelir, güven aralığı yoktur ve olumsuzdur.
5. **Ticari hazırlığı kanıtlamaz.** Kurumsal SSO ve okuma uçlarında yetki, **periyodik filo raporu
   ve veri dışa aktarma** (tek olay için yazdırma var, fazlası yok) ve varlık kütüğü bu teslimde
   yoktur; §a.3'te boşluk olarak işaretlidir. (Yazma uçlarındaki operatör kimliği 18 Eylül'de
   eklendi — bu boşluğu **daralttı**, kapatmadı.)
6. **Kapsam dışı bıraktığımız veri türlerinin gereksiz olduğunu kanıtlamaz.** §(c) bir **karar**
   kaydıdır, bir bulgu değil: bu depoda akustik hiç ölçülmedi, termal görüntü hiç alınmadı.
   Akustik gerekçemiz **yalnızca PD eksenini** kapsıyor; mekanik gevşeme ve korona ele alınmadı.
   Termal dizi ise **reddedilmedi** — yerleşim çiziminde ve kurulum prosedüründe duruyor, MoSCoW'da
   "Could" ve uygulanmadı; depoda bir termal dizi **fiyatı yoktur**, bu yüzden maliyet
   karşılaştırması da yapılmamıştır.
7. **Bildirim kanallarının gerçekten teslim ettiğini kanıtlamaz.** WhatsApp gerçek Meta Cloud API'ye
   karşı **hiç denenmedi**; Telegram için de gerçek telefona teslim kanıtı **yoktur** (`docs/20` §4
   md. 5). Her iki kanalın testleri tamamen `httpx.MockTransport` ile sahtedir ve yalnızca istek
   biçimini ölçer (§c.3).
