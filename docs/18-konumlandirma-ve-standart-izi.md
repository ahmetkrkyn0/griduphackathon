# 18 — Konumlandırma ve Analitik Standart İzi

> **Sahip:** Ortak doküman (18–20 Eylül doküman penceresi, PLAN.md GK2; bu dosya 16 Eylül'de açıldı) · **Kaynak:**
> `GELISTIRME-BACKLOGU.md` §2 (sektörel bulgular) ve §4 F-15 · `HACKATHON_ANALIZ_RAPORU.md` §4
> **Ölçülen her sayının kaynağı satır içinde dosya adıyla verilmiştir (GK10).**

Bu doküman iki şey yapar: (a) ürünü **cihaz** düzeyinde değil **platform** düzeyinde konumlandırır ve
bizde olmayan her yeteneğin bir boşluk mu yoksa yazılı bir kısıt kararı mı olduğunu ayırır;
(b) ürünün ana işi olan **durum izleme ve prognoz** için standart → kod dosyası → ölçülen sonuç →
dürüst boşluk izini kurar. Bu doküman **hiçbir rakip ürünün kötü olduğunu iddia etmez**, hiçbir rakip
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
| 10 | Bulut portalı / üretici uzaktan servisi | **Yok.** Tüm yığın tek makinede, internet kablosu çıkarılmış hâlde çalışır | Bulut panosu ABB SWICOM kaydında doğrulandı (`frontend/TASARIM-REVIZYONU.md` §2) | **Karar — GK4.** Tek istisna kapatılabilir WhatsApp Cloud API metni |
| 11 | Kimlik doğrulama, rol tabanlı erişim, kurumsal SSO | **Kısmen var** (18 Eylül, F-19). Onaylayan adı artık istemciden **gelmiyor**: `by` alanı sözleşmeden kaldırıldı (`openapi` v1.2.0) ve doğrulanmış `Authorization: Bearer` başlığından türer (`backend/app/auth.py`, 23 test). Roller: izleyici < operator < muhendis | **Doğrulanmadı** | **Boşluk daraldı, kapanmadı.** Kurumsal SSO/OIDC **değildir** (belirteçler paylaşılan sır; parola, oturum süresi, yenileme, iptal yok); yalnızca **yazma** uçlarını korur; ekranlarda role göre gizleme yapılmadı; TLS yok. `GRIDUP_OPERATORS` boşsa tamamen kapalıdır ve bunu `GET /health` söyler. Ayrıntı: `contracts/changes/2026-09-18-kimlik-dogrulama.md` |
| 12 | Sertifikalı donanım, tip testi, EMC/ortam doğrulaması | **Yok.** Tasarım hedefleri belgelendi, **fiziksel doğrulama yapılmadı** (`docs/13-donanim-tasarimi.md`, `docs/11-standartlar-uyum.md` "Kapsanmayan standartlar", `docs/19-tedas-sartname-uyumu.md`) | Ticari ürünler sertifikalı | **Karar — GK3.** "Karşılıyoruz" değil, "tasarım hedefi, tip testi yapılmadı" |
| 13 | Kısmi deşarj ve dalga biçimi imzası | **Yok.** 10 saniyelik skaler mimari seri arkı ve kontak kıvılcımlanmasını **fiziksel olarak göremez** — gerekçesi `docs/13-donanim-tasarimi.md` §7'de toplu | OG tarafında PD ürünleri yerleşik (`HACKATHON_ANALIZ_RAPORU.md` §4) | **Karar — GK3 + MoSCoW Won't.** "Yapabiliriz" denmiyor; bugünkü mimarinin göremediği yazılıyor |
| 14 | Ölçek kanıtı | **1.000 sanal pano**: görünme p95 **657 ms**, kayıp **0**; alarm → SMS uçtan uca p95 **606 ms**; 10.000 panoda veri kaybetmeden doyma, darboğaz ölçüldü (mesaj başına 615 µs'in **501 µs**'i şema doğrulaması); TimescaleDB sıkıştırma **46–48×** (`docs/09-olceklenebilirlik.md`) | Saha ölçeği ticari platformlarda on binler mertebesinde (`GELISTIRME-BACKLOGU.md` §1) | **Kapsam farkı dürüstçe yazılır:** bizimki **sanal** panodur, saha ölçeği değildir. GK7 en az 100 modül ister, hedef kanıt 1.000 sanal pano |
| 15 | Birim maliyet | Adet 1: **~56 USD/pano**, adet 1.000: **~37 USD/pano** — `hardware/pano-beyni/bom.csv`. **SIM/veri aboneliği ve kurulum işçiliği hariçtir** | **Fiyat yazılmadı** (F-15 kuralı); karşılaştırma yapılmamıştır | — |
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
| **ISO 13381-1** — durum izleme ve tanı, **prognoz** | Kalan ömür kestirimi; prognozun **doğrulanması** ve sonucun bir **güven ifadesiyle** verilmesi | `libs/panoalgo/panoalgo/detect.py` → `_ttl_h()` / `time_to_limit()` (K'nin EWMA eğimi + 168 kutulu saat-of-hafta yük profili; üç durumda `null` döner — uydurmak yerine susar). Geri test ölçütleri: `libs/panoalgo/panoalgo/prognostics.py` (α-λ, prognostic horizon, relative accuracy, convergence — Saxena ve ark. 2010 / NASA Prognostics Metrics Library) | **Ölçüldü ve olumsuz çıktı** (`docs/12` §4): `S1_loose_conn`'da **790 tahmin**, ihlal öncesi yalnızca **%5,2**'si α = 0,20 konisinde; **prognostic horizon YOK**; **CRA −5,12**; medyan tahmin/gerçek **1,69**. İhlale 48 saatten az kala koni içinde kalma oranı **%0**. `S2_overload`'da **hiç tahmin üretilmedi**. `S8_sensor_fault`'ta sınır **hiç aşılmadığı hâlde 99 tahmin** üretildi ve **89'u** `ALM-TTL-14D` alarmına döndü — bu bir **prognoz yanlış-alarmıdır** ve `docs/12` §3'teki yanlış alarm sayacı onu **görmez** | **Bu tablonun en önemli satırı.** `ttl_h` bugün **güvenilir bir kalan ömür kestirimi değildir** ve bunu yumuşatmıyoruz. Standardın istediği **güven ifadesi üretilmiyor**: sonuç **tek yörüngeden** gelir (**n = 1**), **güven aralığı yoktur**. Ayrıca manşetteki **209 saatlik öne alma tespit katmanından (K/K₀ eşiği) gelir, bu tahminden değil** — ikisi karıştırılmamalıdır (`docs/05` §10) |
| **CIGRE TB 858** — varlık sağlık indeksleri | Varlık **sağlık indeksi** kurulması ve indeksin **monotonluk** ilkesine uyması: daha fazla ya da daha ağır kanıt indeksi düşürmemeli | Risk skoru 0–100: `libs/panoalgo/panoalgo/fusion.py` (`RiskResult.score`, `contributions`). Monotonluk **özellik testiyle** sınanıyor: `libs/panoalgo/tests/test_fusion.py` — sözleşmedeki kanıt kodlarının **0–3 elemanlı tüm alt kümeleri** taban alınıp her tabana kalan her kod tek tek ekleniyor, üç ayrı özellik kümesiyle | Monotonluk testi geçiyor; `libs/panoalgo` **410/410** test yeşil (18 Eylül 2026, bu dalda ölçüldü). Risk skorunun bildirim kararını **yönetmediği** kodda yazılı: SMS/arama kararı alarm önceliğinden (P1/P2/P3) çıkar, skordan değil | **Boşluk daraldı, kapanmadı** (18 Eylül, F-21). Risk matrisinin artık **gerçek bir etki ekseni var**: y = `abone_sayisi`, varlık künyesinden gelir (`contracts/openapi.yaml` v1.3.0 `AssetRegistry`, göç `deploy/initdb/008_varlik_kutugu.sql`). Abone sayısı **sayılabilir** bir büyüklüktür ve EPDK Kalite Yönetmeliği Madde 8/2 zaten "etkilenen kullanıcı sayısı"nı istiyor; eski kVA itirazı (filodaki her panoda **aynı** `pano_type`) böylece aşıldı. **Kalan sınır:** matris **künye girildiği ölçüde** iki boyutludur — künyesi içe aktarılmamış pano ayrı bir şeritte gösterilir ve y=0'a **konmaz** ("abonesi yok" ile "abone sayısı bilinmiyor" ayrı şeylerdir), hiçbir panonun künyesi yoksa eski tek boyutlu davranış **aynen** korunur. **Bu teslimde demo filosunun künyesi boştur** (GK3: gerçek bir CBS aktarımına erişim yok) ve bu `GET /fleet/assets` `kapsama` alanında sayıyla görünür. Sağlık indeksinin **kendisi** hâlâ yaş ve bakım geçmişi içermiyor: künye bunları taşıyor ama `fusion.py` skoru onları **okumuyor** — kritiklik bir **etki** ekseni olarak duruyor, sağlık indeksine karıştırılmadı. Ayrıntı: `contracts/changes/2026-09-18-varlik-kutugu.md` |
| **IEC 62974-1** — cihazın **ürün sınıfı** standardı | — | — | — | Bu doküman kapsamı dışıdır: ürün sınıfı standardı olarak `docs/11-standartlar-uyum.md`'de işlendi |

### b.1 İzin tek cümlelik özeti

Durum izleme tarafında (ISO 17359 / ISO 13379-1 konuları) kodun standartla aynı **konuyu** konuştuğu
ve sonuçlarının ölçüldüğü gösterilebiliyor; prognoz tarafında (ISO 13381-1 konusu) **ölçtük ve
tutmadı** — bunu jüri bulmadan biz yazıyoruz. Bu dokümanın varlık sebebi tam olarak budur.

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
