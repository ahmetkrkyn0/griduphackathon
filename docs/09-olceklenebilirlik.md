# 09 — Ölçeklenebilirlik, Yük Testi ve Veri Bütçesi

> **Sahip:** Kişi B · **Ölçüm tarihi:** 13 Eylül 2026 (§6.1 veri bütçesi: **18 Eylül 2026**) ·
> **Araçlar:** `loadtest/fleet.py` (yük), `loadtest/storage.py` (depolama), `loadtest/veri_butcesi.py` (uyarlanabilir raporlama, §6.1)
> **Ham sonuçlar:** `loadtest/results/*.json` (git dışı; bu dokümandaki her sayı oradan alındı) ·
> **Grafana:** "Grid Up — Ölçek ve yük testi" (koşu seçilerek) ve "Grid Up — Alarm KPI" · Rapor karşılığı: §6.8

## 1. Özet

| Filo | Nokta/pano | Mesaj/s | Satır/s | Alım p95 | **Görünme p95** | Alarm → SMS p95 | Backend CPU (ort.) | DB RAM (maks.) | Kayıp |
|---|---|---|---|---|---|---|---|---|---|
| 100 pano | 7 | 10 | 810 | 2,8 ms | **657 ms** | 726 ms | 0,04 çekirdek | 177 MiB | 0 |
| **1.000 pano** | 7 | 100 | 8.100 | 6,3 ms | **657 ms** | 606 ms | 0,16 çekirdek | 635 MiB | 0 |
| 1.000 pano | 25 | 100 | 18.900 | 7,9 ms | **694 ms** | 748 ms | 0,21 çekirdek | 937 MiB | 0 |
| 3.000 pano | 7 | 300 | 24.300 | 7,3 ms | **704 ms** | 831 ms | 0,26 çekirdek | 2.020 MiB | 0 |
| 5.000 pano | 7 | 500 | 40.500 | 15,2 ms | **769 ms** | 919 ms | 0,36 çekirdek | 2.079 MiB | 0 |
| 10.000 pano (stres) | 7 | 1.000 | 81.000 | 3.717 ms | **18.941 ms** | 9.565 ms | 0,72 çekirdek (maks. 1,16) | 1.646 MiB | 0 |

- **R9 "en az 100 modül": 10 katı ölçüldü.** 1.000 panoda sensör zamanından veritabanında görünmeye p95 **657 ms** (plan hedefi
  < 2 s), mesaj kaybı **0**, alarm → SMS p95 **606 ms**; backend bir çekirdeğin ortalama **%16**'sını kullandı.
- **Kapasite sınırı ölçüldü:** tek backend süreci **5.000 panoya** (500 mesaj/s) kadar görünme p95'i 1 saniyenin altında tuttu; **10.000
  panoda** (1.000 mesaj/s) doydu. Veri kaybı yine yok ama görünme p95 19 s. Darboğaz ölçüldü: mesaj başına 615 µs'lik alım işinin
  **501 µs'i şema doğrulaması** (§4.4).
- **Depolama:** TimescaleDB sıkıştırması **46–48 kat** ölçüldü ve şemaya eklendi (`deploy/initdb/005_compression.sql`).
  100 pano × 7 nokta × 10 s: günde **13,9 GB → 0,29 GB**.
- **Hücresel veri:** 10 s JSON ile pano başına ayda ~456 MB (7 nokta) / ~1.014 MB (25 nokta). **Uyarlanabilir raporlama 18 Eylül'de
  uygulandı ve ölçüldü** (F-36): 25 noktalı panoda 1.071 MB → **632 MB**, yani **1,70 kat** — rapordaki 6 kat tahmininin oldukça altında.
  Alarm anı ölçümle **değişmedi**. Ayrıntı ve tahmin/ölçüm karşılaştırması §6.1'de.

## 2. Test düzeneği

| | |
|---|---|
| Makine | Intel Core i7-14700KF (20 çekirdek / 28 iş parçacığı), 31,8 GB RAM, Windows 11 |
| Sanallaştırma | Docker Desktop 29.7 (WSL2 VM: 28 vCPU, 15,5 GiB) |
| Yığın | `docker compose` (tek makine, on-prem modeli): Mosquitto 2.0 · TimescaleDB 2.30 / PostgreSQL 16.15 · backend (Python 3.12, FastAPI) |
| Backend ayarı | Tek süreç; ingest yazıcısı parti başına en çok 500 mesaj veya 0,5 s; bellek kuyruğu 50.000 mesaj |
| Yük üreteci | **Aynı makinede** (`loadtest/fleet.py`); CPU'da yığınla yarışır, yani sonuçlar temkinli |

**Dürüstlük notu:** Bu bir geliştirme iş istasyonudur; tek çekirdek hızı tipik bir sunucu vCPU'sundan yüksektir. Bu yüzden CPU kullanımını
**çekirdek** cinsinden veriyoruz (%100 = bir çekirdek). Sunucuya taşırken kapasite sınırının %30–50 daha erken gelmesi beklenmelidir (§7).

## 3. Yöntem

**Yük.** Her sanal pano (`SIM-00001` …) sözleşmeye (`contracts/mqtt-telemetry.schema.json`) uyan telemetriyi 10 saniyede bir, periyot
içinde **rastgele fazla** yayınlar: saha cihazları aynı saniyede uyanmaz. Yük **şablondur**: değerler zamanla değişir ama fiziksel model
değildir. Bu yük platformu (broker → ingest → veritabanı → alarm → bildirim) ölçer, **tespit başarısını ölçmez** (o `docs/12`, Kişi A).
Panolar 20–50 MQTT bağlantısına paylaştırılır (sahada her panonun kendi bağlantısı vardır; bkz. §8).

| Ölçüm | Nasıl |
|---|---|
| **Alım gecikmesi** | Yayın anı (üreteç saati) → backend'in mesajı aldığı an (`panel_latest.last_rx`). İki saat arasındaki fark her koşunun başında ölçüldü (−0,3…+1,8 ms) ve düzeltildi |
| **Görünme gecikmesi** | Yayın anı → yeni `seq`'in veritabanındaki son durumda ilk görüldüğü an. 50 örnek pano 250 ms'de bir yoklanır: ölçüm 250 ms'lik taneciklidir ve **uçtan uca** gecikmeyi (broker + doğrulama + kuyruk + toplu yazma + commit) kapsar |
| **Kaynak** | `docker stats`, 5 s'de bir: backend, TimescaleDB, Mosquitto CPU ve bellek |
| **Alarm zinciri** | Koşunun ortasında 5 pano K/K₀ > 1,6 gönderir → P2 `ALM-K-ALM` → iki (hayali, demo) alıcıya sanal modem üzerinden SMS. Açılma: `annunciated_at − raised_at`; SMS: ilk başarılı `sent_at − raised_at` (`raised_at` sensör zamanıdır) |
| **Kayıp** | Backend sayaçları: `rejected` (şema dışı), `dropped` (kuyruk dolu), `write_errors` |
| **Depolama** | Ayrı deney (§5): canlı koşularda silinen satırların boşalttığı sayfalar yeniden kullanıldığı için bayt/satır güvenilir değildi (79–183 B arası oynadı) |

Her koşunun sonunda `SIM-*` verisi silinir ve backend yeniden başlatılır. Aksi halde bellekteki alarm yöneticisi, susan binlerce sanal
pano için 5 dakika sonra `ALM-COMMS-LOST` üretirdi.

## 4. Sonuçlar

### 4.1 Gecikme ve kayıp — *elle yazılmış, kanıt dosyası yok*

> **Bu tablonun hiçbir satırının kanıt dosyası klonda YOKTUR ve bunu saklamıyoruz.**
> `loadtest/results/` 20 Eylül'e kadar `.gitignore` ile tamamen dışarıdaydı, yani
> bu koşumların özet JSON'ları hiçbir zaman sürüm kontrolüne girmedi ve bugün geri
> üretilemezler. Sayılar ölçülmüştür, ama **depoyu klonlayan biri bunları
> doğrulayamaz** — okuyucu bize güvenmek zorunda kalır. Kanıt dosyası commit'li
> olan koşumlar §4.1b'dedir; ikisi bilerek ayrı tutuldu, birleştirmek kanıtlı ile
> kanıtsızı ayırt edilemez hâle getirirdi.

| Filo | Nokta | Süre | Mesaj | Alım p50 / p95 / maks. | Görünme p50 / p95 / maks. | Reddedilen / düşürülen / yazma hatası |
|---|---|---|---|---|---|---|
| 100 | 7 | 180 s | 1.800 | 0,6 / 2,8 / 8,2 ms | 386 / 657 / 906 ms | 0 / 0 / 0 |
| 1.000 | 7 | 300 s | 30.000 | 2,0 / 6,3 / 18,3 ms | 385 / 657 / 771 ms | 0 / 0 / 0 |
| 1.000 | 25 | 180 s | 18.000 | 2,2 / 7,9 / 28,9 ms | 390 / 694 / 821 ms | 0 / 0 / 0 |
| 3.000 | 7 | 120 s | 36.000 | 2,5 / 7,3 / 20,6 ms | 400 / 704 / 809 ms | 0 / 0 / 0 |
| 5.000 | 7 | 120 s | 60.000 | 3,4 / 15,2 / 48,0 ms | 403 / 769 / 883 ms | 0 / 0 / 0 |
| 10.000 | 7 | 120 s | 120.000 | 134 / 3.717 / 4.495 ms | 8.453 / 18.941 / 20.416 ms | 0 / 0 / 0 |

Görünme gecikmesinin ~400 ms'lik tabanı yazıcının **0,5 s parti aralığı** ile yoklamanın 250 ms tanesinden gelir; 100 ile 5.000 pano
arasında neredeyse değişmemesi, sistemin bu aralıkta yük altında olmadığını gösterir. Aralık düşürülebilir (daha çok, daha küçük commit).

### 4.1b Kanıt dosyası commit'li koşumlar — *`scripts/gen_olcek_doc.py` üretir*

> Aşağıdaki iki tablo **elle yazılmaz**. `python scripts/gen_olcek_doc.py` onları
> `loadtest/results/` altındaki **commit'li** JSON eserlerinden üretir;
> `python scripts/gen_olcek_doc.py --check` güncel değilse 1 ile çıkar. Yeni bir
> koşumun eseri commit'lenince satır kendiliğinden belirir, eser silinirse satır
> kaybolur. Koşum makinesi ve koşulları §3'tedir; **yük üreteci ölçülen sistemle
> AYNI makinededir**, yani sayılar temkinlidir.

<!-- URETILMIS:kanitli-kosumlar -->
| Filo | Nokta | Süre | Mesaj | Alım p50 / p95 / maks. | Görünme p50 / p95 / maks. | Red / düş / hata | Kanıt dosyası |
|---|---|---|---|---|---|---|---|
| 1.000 | 7 | 180 s | 18.000 | 1,4 / 12,8 / 63,6 ms | 404,5 / 710,5 / 835,9 ms | 0 / 0 / 0 | [`20260919T135916-1000p.json`](../loadtest/results/20260919T135916-1000p.json) |
<!-- /URETILMIS:kanitli-kosumlar -->

**Veri bütçesi koşumları** (`loadtest/veri_butcesi.py`). "Bastırma", sabit 10 s'lik
yayına göre kaçınılan mesaj oranıdır; "pano başına aylık" 25 noktalı panoda ölçülen
bayttan gelir.

<!-- URETILMIS:veri-butcesi -->
| Kanıt dosyası | Pencere | Pano | Nokta | Politika | Mesaj | Bastırma | Pano başına aylık |
|---|---|---|---|---|---|---|---|
| [`veri-butcesi-2p-0.06g-20260918.json`](../loadtest/results/veri-butcesi-2p-0.06g-20260918.json) | 0,7 sa | 2 | 25 | `sabit-10s` | 518 | %0 | 1068,5 MB |
| ↳ | 0,7 sa | 2 | 25 | `uyarlanabilir-%1` | 488 | %5,8 | 1006,6 MB |
| ↳ | 0,7 sa | 2 | 25 | `uyarlanabilir-%2` | 273 | %47,3 | 562,8 MB |
| ↳ | 0,7 sa | 2 | 25 | `uyarlanabilir-%5` | 269 | %48,1 | 554,6 MB |
| ↳ | 0,7 sa | 2 | 25 | `uyarlanabilir-%10` | 259 | %50 | 534 MB |
| [`veri-butcesi-5p-9g-20260918.json`](../loadtest/results/veri-butcesi-5p-9g-20260918.json) | 48 sa | 5 | 25 | `sabit-10s` | 86.400 | %0 | 1071,2 MB |
| ↳ | 48 sa | 5 | 25 | `uyarlanabilir-%1` | 81.350 | %5,8 | 1008,7 MB |
| ↳ | 48 sa | 5 | 25 | `uyarlanabilir-%2` | 50.932 | %41 | 632,5 MB |
| ↳ | 48 sa | 5 | 25 | `uyarlanabilir-%5` | 41.843 | %51,6 | 519,9 MB |
| ↳ | 48 sa | 5 | 25 | `uyarlanabilir-%10` | 33.093 | %61,7 | 411,2 MB |
<!-- /URETILMIS:veri-butcesi -->

### 4.2 Kaynak kullanımı

CPU **çekirdek** cinsinden (ortalama / en yüksek 5 s'lik örnek), bellek en yüksek değer.

| Filo | Nokta | Backend CPU | Backend RAM | TimescaleDB CPU | TimescaleDB RAM | Mosquitto CPU / RAM |
|---|---|---|---|---|---|---|
| 100 | 7 | 0,04 / 0,17 | 58 MiB | 0,02 / 0,06 | 177 MiB | 0,003 / 8 MiB |
| 1.000 | 7 | 0,16 / 0,29 | 69 MiB | 0,05 / 0,18 | 635 MiB | 0,01 / 8 MiB |
| 1.000 | 25 | 0,21 / 0,37 | 80 MiB | 0,10 / 0,19 | 937 MiB | 0,01 / 8 MiB |
| 3.000 | 7 | 0,26 / 0,44 | 94 MiB | 0,12 / 0,21 | 2.020 MiB | 0,02 / 8 MiB |
| 5.000 | 7 | 0,36 / 0,57 | 119 MiB | 0,18 / 0,33 | 2.079 MiB | 0,02 / 8 MiB |
| 10.000 | 7 | 0,72 / 1,16 | 615 MiB | 0,29 / 0,68 | 1.646 MiB | 0,03 / 16 MiB |

TimescaleDB belleği büyük ölçüde PostgreSQL sayfa önbelleğidir (koşular ilerledikçe dolar), sızıntı değildir. 10.000 panoda backend belleğinin
600 MiB'a çıkması **kuyruğun birikmesidir**: yazıcı gelen hıza yetişemedi (yazma hızı p50 918 mesaj/s < gelen 1.000 mesaj/s).

### 4.3 Alarm zinciri

| Filo | Açılan alarm | Açılma p50 / p95 | İlk SMS p50 / p95 (sensör zamanından modemin kabulüne) |
|---|---|---|---|
| 100 | 5 / 5 | 160 / 497 ms | 514 / 726 ms |
| 1.000 | 5 / 5 | 95 / 337 ms | 501 / 606 ms |
| 1.000 × 25 nokta | 5 / 5 | 190 / 604 ms | 318 / 748 ms |
| 3.000 | 5 / 5 | 293 / 517 ms | 641 / 831 ms |
| 5.000 | 5 / 5 | 376 / 433 ms | 791 / 919 ms |
| 10.000 | 5 / 5 | 8.275 / 8.934 ms | 8.612 / 9.565 ms |

Alarm açılması görünmeden kısadır: alarm servisi, telemetri partisinin yazımından hemen sonra çalışır. SMS süresi sanal modemin kabulüne
kadardır; gerçek şebekede operatörün teslim süresi (tipik birkaç saniye) eklenir. Beş alarm iki alıcıya sırayla gittiği için son SMS'ler
kuyruk bekler: p95, küçük bir **alarm selinin** gecikmesidir.

### 4.4 Kapasite sınırı ve darboğaz

10.000 panoda kayıp yoktur: 50.000'lik kuyruk 120 saniyelik aşırı yükü emdi ve yük bitince boşaldı. Ama alarm gecikmesi 9 saniyeye çıktı.
Operasyonel açıdan bu, sistemin **doymuş** olduğu anlamına gelir. Alım gecikmesinin de (p95 3,7 s) büyümesi, sorunun veritabanında değil
**mesajı alan tarafta** olduğunu gösterdi. TimescaleDB bu sırada ortalama 0,29 çekirdekteydi.

Mesaj başına alım maliyeti (aynı makine, 7 noktalı 1.623 baytlık yük, 2.000 tekrar ortalaması):

| Adım | Süre | Pay |
|---|---|---|
| `json.loads` | 15 µs | %2 |
| **JSON şema doğrulaması** (`jsonschema`, draft 2020-12) | **501 µs** | **%81** |
| Uzun formata düzleştirme | 55 µs | %9 |
| Alım toplamı (`_parse`) | 615 µs | — |
| Risk motoru (alarmsız örnek) | 2 µs | — |

615 µs, MQTT thread'ini tek başına ~1.600 mesaj/s ile sınırlar. Yazıcı thread'i (COPY satırları) ve alarm servisi aynı Python sürecinde
GIL'i paylaştığı için doyma daha erken, 1.000 mesaj/s civarında geldi.

**Ölçek kaldıraçları** (ölçümle önceliklendirildi; aksi belirtilmedikçe hackathon kapsamında uygulanmadı, 🧭):

| Kaldıraç | Beklenen etki | Not |
|---|---|---|
| **Uyarlanabilir raporlama** (ölü bant + azami sessizlik + olayda anında) | **Tahmin 6 kat idi; ölçülen 1,70 kat** (§6.1) | **18 Eylül'de uygulandı ve ölçüldü** (`panoalgo.reporting`, `--adaptive`). Tespit kenarda 10 s'de koşmaya devam eder; alarm anı ölçümle değişmedi |
| Şema doğrulamasını derlenmiş doğrulayıcıya almak | Alım işinin %81'i | Draft 2020-12 uyumu doğrulanmalı; doğrulama **kaldırılmaz** (karantina ve güvenlik sınırı) |
| MQTT paylaşımlı abonelik (`$share/ingest/...`) ile birden çok ingest süreci | Doğrusal ölçek (Mosquitto 2 destekler) | Alarm yöneticisi **tek yazıcı** kalır; ingest süreçleri yalnızca telemetriyi yazar |
| Parti aralığını 0,5 s'den kısaltmak | Görünme tabanı ~400 ms'den aşağı | Commit sayısı artar; DB tarafında pay var |

## 5. Veri bütçesi — depolama

### 5.1 Ölçüm

Kısa bir yük testi sıkıştırmayı olduğundan kötü gösterir, çünkü segmentler dolmaz. Bu yüzden `loadtest/storage.py`, **bir günlük** şablon
telemetriyi (5 pano, 10 s) üretimdekiyle aynı indeksli **geçici** bir hypertable'a yazdı, boyutu ölçtü, sonra pano + etiket segmentli
sıkıştırıp yeniden ölçtü. Geçici tablo sonunda silindi, üretim tablosuna dokunulmadı.

| Nokta/pano | Satır/mesaj | Satır (1 gün, 5 pano) | Yazma hızı (COPY) | Sıkıştırmasız | **Sıkıştırılmış** | Oran |
|---|---|---|---|---|---|---|
| 7 | 81 | 3.499.200 | 279 bin satır/s | 198 B/satır | **4,09 B/satır** | **48×** |
| 25 | 189 | 8.164.800 | 162 bin satır/s | 202 B/satır | **4,38 B/satır** | **46×** |

Sıkıştırmasız 198 B/satır'ın **%57,5'i** `(pano_id, tag, ts)` indeksidir (aynı deneyde `hypertable_detailed_size` ile ölçüldü); geri kalanı PostgreSQL satır başı ek yükü ve veridir. Uzun format (satır başına
bir etiket) sıkıştırmada avantaja döner: bir pano/etiket serisi ardışık ve benzer değerlerden oluşur.

**Sonuç:** sıkıştırma isteğe bağlı değil, zorunludur. Şemaya eklendi: bir günden eski parçalar sıkıştırılır
(`deploy/initdb/005_compression.sql`). Geç gelen veri (kenarın 7 günlük tamponu) sıkıştırılmış parçaya da yazılabilir; `/series` okuması
aynı sonucu verir (`backend/tests/test_compression.py`, gerçek TimescaleDB).

### 5.2 Projeksiyon

| Filo | Nokta | Satır/gün | Sıkıştırmasız GB/gün | Sıkıştırılmış GB/gün | **Kurulu politika, 1. yıl** | Önerilen politika, kararlı durum |
|---|---|---|---|---|---|---|
| 100 | 7 | 70,0 M | 13,9 | 0,29 | **118 GB** | 74 GB |
| 1.000 | 7 | 699,8 M | 138,6 | 2,86 | **1.180 GB** | 742 GB |
| 10.000 | 7 | 7,0 milyar | 1.386 | 28,6 | 11,8 TB | 7,4 TB |
| 100 | 25 | 163,3 M | 33,0 | 0,72 | 293 GB | 184 GB |
| 1.000 | 25 | 1,6 milyar | 330,4 | 7,15 | 2,9 TB | 1,8 TB |

- **Kurulu politika:** 1 gün sıkıştırmasız + kalan günler sıkıştırılmış, silme yok.
- **Önerilen politika** (rapor §6.8, 🧭): ham 10 s veri 90 gün (ilk gün sıkıştırmasız), ardından tüm etiketlerin 1 dk ortalaması 2 yıl. Özet
  terimi üst sınırdır, çünkü tüm etiketlerin özetlendiği varsayıldı.
- **En büyük kaldıraç raporlama periyodudur:** normalde 60 s, olayda anında raporlamada satır sayısı 6'da birine iner. 100 pano × 7 nokta
  için sıkıştırılmış yıllık yük ~**17 GB**, 1.000 pano için ~**174 GB** olur. **18 Eylül notu (F-36):** bu satırdaki 6 kat bir tahmindir ve
  ölçüm onu doğrulamadı — uyarlanabilir raporlama %2 ölü bantla **1,70 kat** verdi (§6.1), yani karşılığı ~**62 GB** / ~**620 GB**.
  Yavaş değişen alanların (`k`, `tau_s`, `excited`) 10 s yerine
  60 s'de gönderilmesi 10 s raporlamada da satır sayısını ~%22 azaltır (nokta başına 6 satırın 3'ü; mesaj başına 81 → ~63 satır).

### 5.3 Rapor §6.8 tablosuyla karşılaştırma

| 100 pano | Rapor (tahmin) | **Ölçülen (7 nokta, 10 s)** | Fark nedeni |
|---|---|---|---|
| Etiket (satır) / saniye | 400 | **810** | Nokta başına 6–7 alan (T, ΔT, K, K/K₀, τ, uyarım) + elektriksel/ortam/TVOC-2/sağlık: mesaj başına 81 satır |
| Nokta / gün | 34,6 M | **70,0 M** | aynı |
| Sıkıştırmasız bayt/satır | ≈50 B | **198 B** | %57,5'i indeks; PostgreSQL satır başı ek yükü dahil |
| Sıkıştırılmış bayt/satır | ≈2 B | **4,09 B** | — |
| Sıkıştırılmış GB/gün | ~0,07 | **0,29** | Satır sayısı ×2, bayt/satır ×2 |
| Yıllık sıkıştırılmış | ~25 GB | **~105 GB** (10 s) · **~17 GB** (60 s raporlama) | Rapordaki "normalde 60 s" varsayımıyla ölçüm, tahminle aynı mertebede |

## 6. Hücresel veri bütçesi

Ölçülen JSON yükü ve MQTT 3.1.1 QoS 1 PUBLISH başlığı; TCP/IP ve TLS ek yükü mesaj başına ~110 B tahminidir (TCP/IP 40 B, TLS kaydı 29 B,
ACK ~40 B).

| Yük | JSON | MQTT | Ek yükle | 10 s, aylık | 60 s, aylık *(aritmetik, olaysız)* |
|---|---|---|---|---|---|
| 7 nokta | 1.620 B | 1.652 B | ~1.761 B | ~456 MB | ~76 MB |
| 25 nokta | 3.772 B | 3.804 B | ~3.913 B | ~1.014 MB | ~169 MB |
| İkili özet (rapor tahmini, CBOR/protobuf) | — | 300 B | — | ~78 MB | ~13 MB |

Son sütun bir **aritmetiktir**: 10 s sayısının 6'ya bölünmesi. Kusursuz 60 s'lik bir ritim ve **sıfır olay yayını** varsayar, yani
ulaşılabilir alt sınırdır. İkili özet satırı da ~110 B ek yük **içermez**; JSON satırlarıyla aynı tabanda değildir (adil taban ~410 B → ~106 MB).
Gerçek uyarlanabilir raporlamanın ne verdiği §6.1'de **ölçülmüştür**.

### 6.1 Uyarlanabilir raporlama — ölçüm (F-36, 18 Eylül 2026)

`panoalgo.reporting` nokta başına **ölü bant**, **azami sessizlik** (60 s) ve **olayda anında yayın** uygular. Seyrelen yalnızca **yayındır**:
tespit kenarda 10 saniyede koşmaya devam eder (ölçüm aracı bunu şart koşar, aksi halde sayı yazmadan durur).

**Düzenek:** `loadtest/veri_butcesi.py`, **gerçek fizik üreteci** (`panoalgo.generator.PanelSimulator`), 5 pano × 25 nokta, tohum 20260918,
10 s tespit periyodu. 9 simüle günün **ilk 7'si taban öğrenme** (K₀ donuncaya kadar), bütçe **son 48 saat** için ölçüldü: **86.400 örnek**.
Beş politika **aynı örnek akışını** görür — karşılaştırma iki ayrı deneyden değil tek koşudan gelir.

| Politika | Mesaj | JSON | MQTT | Faturalanan | Pano başına aylık | Bastırılan | Azalma |
|---|---|---|---|---|---|---|---|
| Sabit 10 s (bugünkü davranış) | 86.400 | 344,8 MB | 347,6 MB | 357,1 MB | **1.071 MB** | %0,0 | 1,00× |
| Ölü bant %1 | 81.350 | — | — | 336,2 MB | 1.009 MB | %5,8 | 1,06× |
| **Ölü bant %2 (teslim edilen varsayılan)** | **50.932** | 203,6 MB | 205,2 MB | 210,8 MB | **632 MB** | **%41,0** | **1,70×** |
| Ölü bant %5 | 41.843 | — | — | 173,3 MB | 520 MB | %51,6 | 2,06× |
| Ölü bant %10 | 33.093 | — | — | 137,1 MB | 411 MB | %61,7 | 2,61× |

**Neyin azaldığını tanımlıyoruz (GK10):** üç kalem farklı sayılar verir ve üçü de yukarıda ayrı sütunda. **Mesaj sayısı** ve **JSON/MQTT baytı
ölçülmüştür**; "faturalanan" ise MQTT baytına mesaj başına ~110 B TCP/IP+TLS+ACK eklenmiş **tahmindir** (§6 girişindeki aynı sayı). Bayt
muhasebesi **sıkıştırılmış JSON** üzerinedir; `sim/panosim.py` boşluklu `json.dumps` kullanır ve **ölçüldü: 1,139 kat** büyüktür.

**Tahmin ile ölçüm arasındaki fark — maddenin asıl bulgusu:**

| | Rapor/§4.4 tahmini | **Ölçülen (%2)** | Fark nedeni |
|---|---|---|---|
| Mesaj hızı azalması | 6 kat | **1,70 kat** | 60 s heartbeat teorik olarak %83 bastırmaya izin verir; ölçülen %41,0. Yayınların **%22,7'si olay** (alarm kümesi, risk kipi, veri kalitesi bitleri), **%70,2'si ölü bant aşımı**, yalnızca **%7,1'i heartbeat**. Gerçek fizikte "hiçbir şey değişmiyor" hâli varsayıldığı kadar sık değil |
| Pano başına aylık hücresel (25 nokta) | ~169 MB (60 s, aritmetik) | **632 MB** | Aynı oran farkı; aritmetik sütun sıfır olay varsayıyor |

§5.2'deki depolama satırı da aynı orandan etkilenir: 100 pano × 7 nokta için yıllık sıkıştırılmış yük 10 s'de **ölçülen** ~105 GB idi;
"60 s" varsayımıyla ~17 GB'a iniyordu. Ölçülen 1,70 kat uygulanırsa **~62 GB** olur. Bu sayı **türetilmiştir, ölçülmemiştir**: oran 25
noktalı panolarda ölçüldü ve 7 noktalı bir panoda ölü bandı aşma şansı daha az olduğu için gerçek tasarruf bundan **iyi** olabilir.

**Alarm gecikmesi değişmedi — ölçüldü, varsayılmadı.** Araç her alarm kodunun **ilk yayınlandığı turu** politikalar arasında karşılaştırır.
Gevşek bağlantının sürünerek büyüdüğü arıza rejiminde dokuz kodun tamamı beş politikada da **aynı turda** yayınlandı; örneğin
`ALM-THR-TERM-ALM` beşinde de **15.161. turda** (≈42. saat) çıktı. Sebebi yapısaldır: alarm kümesindeki, risk kipindeki, koruma durumundaki
ve veri kalitesi bitlerindeki **her değişim anında yayın tetikler**, yani ölü bant yalnızca eşik altındaki sayısal sürünmeyi bastırabilir.

**Veri kaybı sınırlıdır ve ölçülmüştür.** Yayınlanmayan örnekler sıfırıncı derece tutmayla geri kurulduğunda hata hiçbir alanda ölü bandı
aşmadı: en büyük sapma `elec.i_ph` üzerinde **40,4 A** (bant 41,6 A), `ttl_h` üzerinde 6,0 saat (bant 6,72 saat). Ölü bantların hepsi
`contracts/alarm-codes.yaml` eşiklerinden **türetilir** (karar aralığının %2'si); sözleşmeye yeni alan eklenmemiştir.

**Sonuç:** 10 s JSON, düşük kotalı M2M hattı için pahalıdır. Uyarlanabilir raporlama kaldıracın **gerçek ama tahmin edilenden küçük**
olduğunu gösterdi: pano başına ayda 1.071 MB → **632 MB**. Kalan büyük kaldıraç **ikili kodlamadır** (🧭, kenar firmware'i, Kişi A);
merkezde yalnızca ayrıştırıcı değişir. Sözleşme bunu şimdiden söyler: "JSON; üretimde CBOR".

**Sahada açmadan önce iki önkoşul (ölçülmedi, kayda geçiriliyor):**
- **Kayıp mesaj toleransı düşer.** `ALM-COMMS-LOST` 300 s sessizlikte tetiklenir; 10 s'de bu 30 ardışık mesaj demekken 60 s'de 5'e iner.
  `ingest` kuyruğu dolduğunda mesaj sessizce düşer (`backend/app/ingest.py`), yani bu tolerans gerçek bir emniyet payıdır.
- **F-22 kesinti penceresinin gerekçesi 10 s'e dayanıyor.** `outage_window_min: 2` yorumu sözleşmede birebir "telemetri periyodu (10 s) …
  için cömert bırakıldı" der. Uyarlanabilir raporlama **varsayılan olarak kapalıdır** (`--adaptive` ile açılır), bu yüzden gerekçe bugün
  geçerlidir; sahada açılırsa pencere yeniden türetilmelidir.
- Kenar kendi yayın aralığını merkeze **beyan edemez**: telemetri şeması donmuştur ve `additionalProperties: false` taşır. Merkez bu yüzden
  sabit 300 s ile karşılaştırır; emniyet payı kodda korunur (azami sessizlik, sözleşmedeki zaman aşımının yarısını aşamaz).

## 7. Sunucu boyutlandırma — ölçümden

| Ölçek | Rapor önerisi | Ölçülen ihtiyaç (10 s raporlama) | Değerlendirme |
|---|---|---|---|
| 100 pano | Tek VM: 4 vCPU, 16 GB RAM, 500 GB SSD | CPU < 0,1 çekirdek; DB RAM < 0,2 GB; disk 1. yıl 118 GB | CPU'da çok büyük pay; 500 GB disk 10 s raporlamada ~4 yıl yeter |
| 1.000 pano | 2–3 VM, DB için 8 vCPU / 32 GB | Backend 0,16 (en çok 0,29) çekirdek; DB 0,05 (0,18) çekirdek, 0,6 GB; disk 1. yıl ~1,2 TB | **Tek 4–8 vCPU VM CPU için yeterli**; boyutlandıran etken **disk**: 60 s raporlamayla ~175 GB/yıl |
| 5.000 pano | — | Backend 0,36 (0,57) çekirdek; DB 0,18 (0,33) çekirdek, 2,1 GB | Tek backend sürecinin ölçülen üst sınırına yakın (sunucu vCPU'sunda daha erken) |
| 10.000 pano | Kümelenmiş MQTT, TimescaleDB çoğaltma | Tek süreçte doyuyor | §4.4 kaldıraçları: 60 s raporlama veya birden çok ingest süreci |

Yüksek erişilebilirlik (ikinci sunucu, çift broker) kapasiteden bağımsız bir gerekliliktir (FMEA #5, docs/07b).

## 8. Bilinen sınırlar

- **Aynı makine:** yük üreteci yığınla aynı makinede ve CPU'da yarışıyor; ağ gecikmesi yok (hücresel hat gecikmesi eklenmeli, tipik 50–300 ms).
- **İş istasyonu:** tek çekirdek hızı sunucu vCPU'sundan yüksek; kapasite sınırı sunucuda daha erken gelir.
- **Bağlantı sayısı:** 20–50 MQTT bağlantısı panoları paylaştı. 1.000–10.000 ayrı TLS bağlantısı sınanmadı. Mosquitto'nun bu ölçekte
  bağlantı başına belleği küçüktür (ölçülen toplam ≤ 16 MiB) ama TLS el sıkışma fırtınası (toplu yeniden bağlanma) ayrıca sınanmalıdır.
  **18 Eylül notu (F-27):** artık çalışan bir mTLS yolu var, ama `loadtest/fleet.py` düz 1883'e bağlanır ve bu ölçümler o yolla
  alınmıştır; TLS el sıkışma maliyeti **hâlâ ölçülmedi**. Ayrıca cihaz başına sertifika topolojiyi de değiştirir (N pano = N
  bağlantı), yani aşağıdaki sayılar mTLS kipine **doğrudan taşınamaz**.
- **Süre:** koşular 2–5 dakika. 24 saatlik etkiler (sıkıştırma işinin kendisi, autovacuum, parça oluşturma) bu ölçümlerin dışında.
- **Şablon yük:** fiziksel değil; alarm yalnızca 5 panodan. Alarm seli ölçeği (yüzlerce eşzamanlı P1) sınanmadı; bildirim kuyruğu sıralıdır.
- **Görünme ölçümü** 250 ms tanelidir.
- **Test sırasında bulunup düzeltilen hata:** SCADA ağ geçidinin otomatik birim eşlemesi her yeni panoda tüm listeyi sıralıyordu; 10.000
  panoda ingest 5 s kilitlenirdi (docs/07b Y4). 10.000 pano stres testi düzeltmeden **sonra** koşuldu.

## 9. Tekrar üretme

```bash
docker compose -f deploy/compose.yaml up -d
# Alarm -> SMS gecikmesi icin alici gerekir (hayali demo numaralari; yalnizca sanal modeme gider):
ALERT_RECIPIENTS=+905550000001,+905550000002 docker compose -f deploy/compose.yaml up -d backend

backend/.venv/Scripts/python loadtest/fleet.py --panels 1000 --duration 300          # sonuc: loadtest/results/<kosu>.json
backend/.venv/Scripts/python loadtest/fleet.py --panels 1000 --points 25 --duration 180
backend/.venv/Scripts/python loadtest/storage.py --panels 5 --points 7              # 1 gunluk depolama deneyi
backend/.venv/Scripts/python loadtest/fleet.py --cleanup-only                      # yarida kalan kosudan sonra

# Veri butcesi (F-36, §6.1). YIGIN GEREKMEZ: tek surec, deterministik, ~50 dk.
# fleet.py bu soruyu CEVAPLAYAMAZ: onun fizik ureteci her yayinda 15 SIMULE DAKIKA
# ilerler (PhysicsPayloadFactory.SIM_STEP_S=900), yani 10 s'lik olu bant rejimini
# olcemez ve bastirmayi sistematik olarak KUCUK gosterir.
backend/.venv/Scripts/python loadtest/veri_butcesi.py --panolar 5 --gun 9 --isinma-gun 7
backend/.venv/Scripts/python loadtest/veri_butcesi.py --hizli                       # duman testi; SAYILARI RAPORLANMAZ

docker compose -f deploy/compose.yaml up -d backend    # demo alicilarini kaldir
```

Grafana (`localhost:3001`) → Grid Up → **Ölçek ve yük testi** → üstten koşuyu seçin, zaman aralığını koşuya göre ayarlayın. Paneller
(yayın/yazma hızı, alım p95, CPU, bellek, tablo boyutu) `loadtest_metrics` tablosundan okunur; pano tanımları
`scripts/gen_grafana_dashboards.py`'den üretilir ve her panelin sorgusu gerçek TimescaleDB'de sınanır.
