# Grid Up Hackathon — Fazlı Uygulama Planı ve Çakışmasız İş Bölümü

> **Ekip için:** Bu belge `HACKATHON_ANALIZ_RAPORU.md`'nin **Bölüm 11'ini (Zaman Planı ve Görev Dağılımı) değiştirir.** Rapordaki teknik içerik (Bölüm 0–10, 12–16) geçerlidir ve bu planın kaynağıdır. Bölüm 11'deki "bugün sipariş verilecek parça listesi" ve 4 kişilik varsayım **geçersizdir** (donanım alımı yok, 3 kişiyiz, başlangıç 12 Eylül).
>
> Her adım `- [ ]` kutucuklu; iş bitince kutucuğu işaretleyip commit'le.

**Hedef:** 20 Eylül 2026 23:59'a kadar, hiç donanım satın almadan, uçtan uca çalışan + eksiksiz donanım tasarımı dokümante edilmiş "Pano/Hücre İçi Anomali Erken Uyarı Sistemi" teslim etmek.

**Yaklaşım:** Fizik tabanlı sentetik veri üreteci → taşınabilir C firmware çekirdeği (host'ta gerçekten koşar) → on-prem MQTT/TimescaleDB/FastAPI yığını → ISA-18.2 alarm yöneticisi → gerçek register adresleriyle MPR-53CS/TVOC-2 Modbus simülatörleri → Modbus TCP ağ geçidi → Türkçe operasyon arayüzü + EK-II/14 çizimi üzerinde dijital ikiz. Donanım, üretilebilir seviyede **tasarlanır** (KiCad şema + BOM + yerleşim + FMEA) ama **üretilmez.**

**Teknoloji:** Python 3.12 (FastAPI, pymodbus 3.x, paho-mqtt, numpy, pytest), C11 (taşınabilir çekirdek + CMake/CTest), TypeScript + React 18 + Vite, PostgreSQL 16 + TimescaleDB, Mosquitto, Grafana, Docker Compose, KiCad 8, Mermaid.

**Spec:** `HACKATHON_ANALIZ_RAPORU.md` (özellikle §2 gereksinim matrisi, §6 mimari, §6.4 Modbus haritası, §6.5 tespit katmanları, §8 demo senaryosu, §9 değerlendirme kriterleri, §15 formüller ve sentetik veri spesifikasyonu).

---

## Global Kısıtlar

Bu bölüm **her görevin** gereksinimidir. Tek tek tekrar edilmez.

| # | Kısıt | Kaynak |
|---|---|---|
| GK1 | **Son teslim 20 Eylül 2026 23:59**; hedef teslim saati **20 Eylül 18:00**. | Rapor §0, takım teyidi |
| GK2 | **Özellik dondurma: 17 Eylül 23:59.** 18–20 Eylül yalnızca doküman, video, hata düzeltme. | Rapor §11 |
| GK3 | **Donanım satın alınmayacak.** Prototip = simülasyon + tasarım dokümanı. Elde zaten var olan cihaz (telefon, eski USB modem) kullanılabilir; satın alma yok. | Ekip kararı |
| GK4 | **Public cloud yok.** Tüm yığın `docker compose up` ile tek makinede, internet kablosu çıkarılmış halde çalışmalı. Tek istisna: WhatsApp Cloud API (yalnızca hassas olmayan kısa alarm metni, kapatılabilir). | Rapor §2.1 R7, §6.6c |
| GK5 | **Geliştirme kartı ürün olarak sunulmaz.** Ürün tasarımı özel PCB + modül MCU'dur; firmware taşınabilir C'dir. | Rapor §2.1 R10, §5 |
| GK6 | **Koruma devresine yazma yok.** TVOC-2 salt okunur; FC06/16 ağ geçidinde filtrelenir. Otomatik açma (trip) yok. | Rapor §2.4.3, §6.6d |
| GK7 | **En az 100 modül** ölçeklenebilirlik; hedef kanıt 1.000 sanal pano. | Rapor §2.1 R9 |
| GK8 | Arayüz ve tüm jüri dokümanları **Türkçe**. Kod/değişken adları İngilizce. | Rapor §6.7 |
| GK9 | `.env`, token, telefon numarası, SIM PIN **asla** commit edilmez. `Hackathon Verileri/` ve proje PDF'i repoda kalır ama **repo private**; public istenirse temiz repo açılır (§12.1). | Rapor §11 teslim listesi |
| GK10 | Her sayısal iddia ölçülmüş olmalı. "Hızlı", "doğru", "ölçeklenir" yerine saniye, %, adet. | Rapor §9 |
| GK11 | Kapsam MoSCoW'a sadık (aşağıda). Yeni fikir = backlog, Faz 3'ten sonra asla kapsam eklenmez. | Rapor §11 |

**MoSCoW (rapor §11'den, donanımsız moda uyarlanmış):**

- **Must:** Sentetik veri üreteci + ısıl model · L0 limitleri + L1 K indeksi + faz karşılaştırma + çiy noktası · sabit eşik karşılaştırma tablosu · alarm yöneticisi + alarm konsolu · bildirim (WhatsApp gerçek + sanal GSM modem ile SMS yolu) · TVOC-2 trip + koruma sağlığı · MPR-53CS/TVOC-2 simülatörleri (gerçek adresler) + Pano Beyni Modbus haritası + Modbus TCP okuma · on-prem Docker Compose · firmware C çekirdeği host'ta koşuyor + akış diyagramı · KiCad şema PDF + I/O tablosu + BOM · mimari + FMEA + ölçek hesabı · demo videosu · README.
- **Should:** Sınıra kalan süre · EK-II/14 üzerinde dijital ikiz · 1.000 pano yük testi + Grafana · kara kutu zaman çizelgesi · çift yönlü SMS onayı · otomatik ısıtıcı/fan aksiyonu · haberleşme kopması + backfill · ROI tablosu · firmware'in Renode/Wokwi'de koşması.
- **Could:** IEC 60870-5-104 · filo karşılaştırması · gaz/VOC senaryosu · hava ΔT enerji dengesi · son nefes bildirimi · PCB layout.
- **Won't:** Fiziksel maket, gerçek sensör, gerçek GSM modem satın alma, PD donanımı, mobil PWA, QR devreye alma, dil modeli, gerçek OTA altyapısı.

---

## Bölüm A — Takım, Branch ve Dosya Sahipliği

### A.1 Üç kulvar

Kim hangi kulvarı alacak sonra kararlaştırılacak. Kulvarlar **dosya sistemi düzeyinde ayrık** olacak şekilde kuruldu: aynı dosyaya iki kişi dokunmaz.

| Kişi | Kulvar | Tek cümlede | Sahip olduğu dizinler |
|---|---|---|---|
| **A** | **Fizik, Kenar ve Algoritma** | "Veriyi üretir, anomaliyi bulur, kenarda koşar." | `libs/panoalgo/`, `firmware/`, `sim/`, `data/` |
| **B** | **Platform, Entegrasyon ve Ölçek** | "Veriyi taşır, alarmı yönetir, telefona ulaştırır, SCADA'ya açar." | `backend/`, `deploy/`, `loadtest/`, `scripts/` |
| **C** | **Arayüz, Donanım Tasarımı ve Teslim** | "Jürinin gördüğü her şey: ekran, çizim, doküman, video." | `frontend/`, `hardware/`, `demo/`, `assets/` |

**Neden bu bölünme?** Üç kulvar rapordaki üç ayrı değerlendirme kümesine denk geliyor (A → "anomali tespit başarısı", B → "entegrasyon + ölçeklenebilirlik + uçtan uca", C → "saha uygulanabilirliği + UX + maliyet"). Her kulvar kendi başına test edilebilir ve diğerinin dosyasına dokunmadan ilerler.

### A.2 Branch modeli

```
main                 ← her zaman yeşil, doğrudan commit yalnızca Faz 0'da
 ├── a/<konu>        ← A'nın kısa ömürlü dalları (ör. a/k-index, a/tvoc-sim)
 ├── b/<konu>        ← B (ör. b/ingest, b/alarm-manager)
 └── c/<konu>        ← C (ör. c/alarm-konsolu, c/kicad-sema)
```

Kurallar:
1. **Dal ömrü ≤ 24 saat.** Uzayan dal = çakışma. Büyük işi böl.
2. PR açmadan önce **mutlaka** `git fetch origin && git rebase origin/main`. Merge değil, rebase.
3. PR'ı **squash merge** ile main'e al (temiz geçmiş, tek commit → revert kolay).
4. Günde **iki entegrasyon penceresi: 13:00 ve 21:00.** O saatlerde herkes dalını main'e alır. Arada serbest.
5. `main` bozulursa her şey durur, önce o düzeltilir (kim bozduysa düzeltir).

### A.3 Doküman sahipliği (çakışmanın en büyük kaynağı buydu — dosya başına tek sahip)

| Dosya | Sahip | İçerik |
|---|---|---|
| `README.md` | **C** | Amaç, mimari görseli, tek komutla kurulum, 7 teknik çıktı → dosya eşleme tablosu, ekip |
| `PLAN.md` (bu dosya) | **ortak** | Yalnızca kutucuk işaretleme ve "Günlük Kayıt" bölümüne satır ekleme. Başka düzenleme = PR'da 3 onay. |
| `docs/01-problem-analizi.md` | C | Raporun jüriye uygun 3 sayfalık özeti |
| `docs/02-mimari.md` | B | Mermaid diyagramlar, veri akışı, sıralama diyagramı |
| `docs/03-modbus-haritasi.md` | B | `contracts/modbus-map.yaml`'dan **üretilir**, elle yazılmaz |
| `docs/04-iec104-haritasi.md` | B | (Could) |
| `docs/05-anomali-tespiti.md` | **A** | Formüller, eşikler, L-1…L4, doğrulama yöntemi |
| `docs/06-alarm-matrisi.md` | B | Öncelik matrisi, kanallar, eskalasyon, ISA-18.2 |
| `docs/07-fmea-donanim-saha.md` | C | Rapor §7.3'ün donanım/saha satırları (1,2,3,9,10) |
| `docs/07b-fmea-yazilim-sistem.md` | B | §7.3'ün yazılım/sistem satırları (4,5,6,7,8,11,12,13,14) |
| `docs/08-kurulum-proseduru.md` | C | Tek planlı kesinti penceresi, 5 güvenlik kuralı, devreye alma |
| `docs/09-olceklenebilirlik.md` | B | Hesap tablosu + yük testi sonuçları + veri bütçesi |
| `docs/10-bom-maliyet-roi.md` | C | BOM (adet 1 / 1.000), SKU'lar, parametrik ROI tablosu |
| `docs/11-standartlar-uyum.md` | C | Rapor §7.6 tablosu + her maddenin nerede karşılandığı |
| `docs/12-dogrulama-sonuclari.md` | **A** | Recall/precision/öne alma süresi + sabit eşik karşılaştırması |
| `docs/13-donanim-tasarimi.md` | C | Blok diyagram, şema açıklaması, I/O tablosu, güç bütçesi, mekanik |
| `docs/14-veri-ureteci.md` | **A** | Sentetik veri spesifikasyonu, senaryo kataloğu, seed'ler |
| `docs/15-guvenlik-kvkk.md` | B | IEC 62443 bölgeleri, mTLS, KVKK |
| `docs/16-ux-tasarim.md` | C | Ekran envanteri, HMI ilkeleri, erişilebilirlik, ekran görüntüleri |
| `docs/17-donanimsiz-dogrulama.md` | B | "Donanım olmadan neyi nasıl kanıtladık" — jüri bu soruyu soracak |

### A.4 `CODEOWNERS` (Faz 0'da oluşturulur)

GitHub handle'ları netleşince `@kisi-a/b/c` yerine gerçek kullanıcı adları yazılır.

```
# Kulvarlar
/libs/      @kisi-a
/firmware/  @kisi-a
/sim/       @kisi-a
/data/      @kisi-a
/backend/   @kisi-b
/deploy/    @kisi-b
/loadtest/  @kisi-b
/scripts/   @kisi-b
/frontend/  @kisi-c
/hardware/  @kisi-c
/demo/      @kisi-c
/assets/    @kisi-c

# Kilitli bölge: üç onay gerekir
/contracts/ @kisi-a @kisi-b @kisi-c
/PLAN.md    @kisi-a @kisi-b @kisi-c
/README.md  @kisi-c
```

---

## Bölüm B — Çakışma Önleme Protokolü (13 kural)

Bunlar "iyi olur" değil, **kural**. Hackathon'da çakışma çözmek için harcanan her saat doğrudan puandan düşer.

| # | Kural | Neden |
|---|---|---|
| 1 | **`.gitattributes` ilk commit'te girer** (`* text=auto eol=lf`). | Üçü de Windows'ta. Satır sonu normalize edilmezse CRLF/LF savaşı her dosyayı baştan sona çakıştırır. **Bu tek kural çakışmaların yarısını siler.** |
| 2 | **Bir dosya = bir sahip.** Başkasının dosyasına dokunma; ihtiyacın varsa sohbetten iste, o commit etsin. | Satır bazlı çakışma imkânsız hale gelir |
| 3 | **`contracts/` Faz 0 sonunda donar.** Değişiklik: `contracts/changes/YYYY-MM-DD-<konu>.md` adında **yeni dosya** + 3 onay + sürüm artışı. Mevcut sözleşme dosyasını tek başına değiştiren kimse yok. | Sözleşme tek kaynak; yeni dosya = çakışmasız changelog |
| 4 | **Üretilen hiçbir şey commit edilmez:** `data/generated/`, `*.parquet`, `*.mp4`, `dist/`, `node_modules/`, `.venv/`, `*.kicad_pcb-bak`. Fixture'lar küçük (≤1 MB), seed'li ve yalnızca A tarafından commit edilir. | İkili dosya çakışması çözülemez |
| 5 | **Kilit dosyaları kulvar sahibinin:** `frontend/package-lock.json` → C, `backend/requirements.lock` → B, `libs/panoalgo/pyproject.toml` → A. Başkasının kilidine dokunmak yasak. | Lock dosyası çakışması en sinir bozucu olan |
| 6 | **Docker Compose parçalı:** `deploy/compose.yaml` (B) `include:` ile `deploy/compose.frontend.yaml` (C) ve `deploy/compose.sim.yaml` (A) dosyalarını çeker. Herkes kendi servis tanımını kendi dosyasında tutar. | Tek compose dosyası üç kişinin çakışma noktası olurdu |
| 7 | **Grafana panoları dosya başına bir pano,** hepsi B'nin. JSON'u üç kişi düzenlemez. | Grafana JSON'u merge edilemez |
| 8 | **Mermaid/SVG diyagramı bir kişinin.** Ortak diyagram yok; gerekiyorsa iki ayrı diyagram. | Diyagram kaynağı satır satır çakışır |
| 9 | **Testler kulvarın içinde:** `libs/panoalgo/tests/`, `backend/tests/`, `frontend/src/**/*.test.ts`. Ortak `tests/` dizini yok. | Test dosyası sahipliği netleşir |
| 10 | **Sabitler kod içine gömülmez,** `contracts/`'tan okunur (alarm kodları, Modbus adresleri, MQTT topic'leri, eşikler). | Üç yerde aynı sabit = üç farklı değer = demo patlar |
| 11 | **Boş dizin yok:** her yeni dizin `.gitkeep` ile Faz 0'da açılır, kimse "dizin oluşturma" commit'i atmaz. | Dizin yarışı önlenir |
| 12 | **13:00 ve 21:00 entegrasyon penceresi.** Pencerede: rebase → PR → squash merge → `docker compose up` ile duman testi. | Entegrasyon borcu birikmez |
| 13 | **Bloke olunca 15 dakika kuralı:** 15 dakikada çözülmeyen bağımlılık sohbete yazılır; sahibi mock/fixture verir, bekleme olmaz. | Kimse kimseyi beklemez |

**Çakışma çıktığında:** `git rebase origin/main` → çakışan dosyanın **sahibi kimse onun sürümü kazanır** (`git checkout --theirs/--ours` yerine sahibine sor). Sahibi sen değilsen kendi değişikliğini geri al ve sahibinden rica et.

---

## Bölüm C — "En iyi donanımsız proje" stratejisi

Donanım yokluğu bir eksiklik değil, **bilinçli bir mühendislik kararı** olarak sunulacak. Jüriye verilecek beş kanıt:

| # | Hamle | Jüriye mesajı | Sahip |
|---|---|---|---|
| DH1 | **Üretilebilir donanım tasarımı:** KiCad şeması (gerçek parça numaralarıyla), I/O tablosu, güç bütçesi, BOM (adet 1 / 1.000), DIN kutu mekaniği, EK-II/14 üzerinde yerleşim, clearance/creepage ve manyetik alan hesapları. | "Breadboard göstermiyoruz; **üretime verilebilir bir ürün** gösteriyoruz." (Rapor §5: dev board'u ürün olarak sunmak puan kaybettiriyor.) | C |
| DH2 | **Firmware gerçekten koşuyor:** taşınabilir C çekirdeği host'ta `panobeyni-sim` ikilisi olarak çalışır, sanal seri port üzerinden gerçek Modbus konuşur. (Should: aynı kaynak Renode/Wokwi'de MCU emülasyonunda.) | "Kod MCU'ya hazır; aynı kaynak iki hedefte derleniyor." | A |
| DH3 | **Fizik motoru, rastgele sayı değil:** `τ·dΔT/dt + ΔT = K·I²` ısıl modeli + yük profili + arıza enjeksiyonu. 7–30 günlük gevşeme süreci 60 saniyede oynatılır. | "Gerçek bir ısıtıcı 6 günlük bozulmayı gösteremez; **bizim modelimiz gösteriyor** — ve fiziği denklemle savunuyoruz." | A |
| DH4 | **Gerçek protokol, gerçek adresler:** MPR-53CS ve TVOC-2 simülatörleri kendi kılavuzlarındaki register adreslerinde; jüri QModMaster ile okuyor. | "Cihazlarınız elimizde yok ama **register haritanız** elimizde; yarın sahada aynı kod çalışır." | A + B |
| DH5 | **Bildirim gerçekten telefona düşüyor:** WhatsApp Cloud API ile gerçek mesaj + sanal GSM modem (PTY + AT komut yanıtlayıcı) ile on-prem SMS yolunun AT komut kaydı ve PDU dökümü. | "SMS sürücüsü üretim sürücüsüdür; modem takıldığında tek satır config değişir. İşte AT komut kaydı." | B |

**Dürüstlük kuralı:** Sunumda ve README'de "simüle edildi" olan her şey **açıkça** simüle edildi yazılır (`docs/17-donanimsiz-dogrulama.md`). Jüri kandırıldığını anlarsa her şey çöker; bilinçli seçim olduğunu anlarsa puan kazanırız.

**Fırsat notu:** Ekipte **zaten** varsa (satın alma yok): eski bir Android telefon USB'den AT komutu kabul ediyorsa gerçek SMS atılabilir; bir ESP32 kartı duruyorsa firmware gerçek donanımda gösterilebilir. İkisi de **bonus**, plan bunlara bağımlı değil.

---

## Bölüm D — Faz Haritası

| Faz | Tarih | Ad | Kilometre taşı (kapı) |
|---|---|---|---|
| **0** | **12 Eyl Cmt** (bugün) | Hizalama ve Sözleşme | **M0:** Üçü de `docker compose up` çalıştırabiliyor; `contracts/` donmuş; branch'ler açık |
| **1** | 13 Eyl Paz | Dikey Dilim (uçtan uca iskelet) | **M1 (21:00):** Sentetik veri → MQTT → DB → API → ekranda canlı bir pano ve bir alarm |
| **2** | 14–15 Eyl Pzt–Sal | Tespit Çekirdeği + Alarm + Bildirim | **M2 (15 Eyl 21:00):** S1 gevşek bağlantı senaryosu → P3 uyarı → **telefona gerçek mesaj** |
| **3** | 16–17 Eyl Çar–Per | Entegrasyon + Ölçek + Firmware | **M3 (17 Eyl 21:00):** QModMaster bizim haritayı okuyor · 1.000 pano yük testi grafiği · firmware host'ta koşuyor → **23:59 ÖZELLİK DONDURMA** |
| **4** | 18 Eyl Cum | Kanıt ve Doküman | **M4:** Temiz makinede tek komutla demo · 17 doküman hazır · doğrulama tablosu sayılarla dolu |
| **5** | 19 Eyl Cmt | Sunum ve Video | **M5:** 3–5 dk video kurgulanmış · sunum destesi · 2 prova · jüri soru bankası çalışılmış |
| **6** | 20 Eyl Paz | Teslim | **M6:** 18:00'de teslim edilmiş, erişim testi yapılmış |

**Günlük ritim (her gün):**
- 09:30 — 10 dk ayakta toplantı: dün ne bitti, bugün ne, neyde bloke.
- 13:00 — entegrasyon penceresi 1 (rebase → PR → merge → duman testi).
- 21:00 — entegrasyon penceresi 2 + kapı kontrolü + kesme kararı (neyi Could'a düşürüyoruz).
- Her gün sonunda `PLAN.md` → "Günlük Kayıt" bölümüne 3 satır.

---

## Faz 0 — Hizalama ve Sözleşme (12 Eylül, bugün · ~5 saat · ÜÇÜ BİRLİKTE)

> **Bu fazın tamamı `main` üzerinde, tek oturumda, tek kişi klavyede (ekran paylaşımıyla) yapılır.** Branch açılmaz. Faz 0 bitmeden kimse dalına geçmez — yoksa sözleşme üç farklı yerde üç farklı şekilde doğar.

### Faz 0 durumu (12 Eylül, 21:30)

**Kurulmuş ve `main`'e commit edilmiş** (`ffe8c65` → `b88aed1`):

| Görev | Durum | Not |
|---|---|---|
| T0.1 Git hijyeni | ✅ | `.gitattributes` (LF), `.gitignore`, `.editorconfig` — tüm metin dosyaları `w/lf` |
| T0.2 Dizin iskeleti + CODEOWNERS | ✅ | 39 dizin, `.gitkeep`'li; CODEOWNERS dosya+doküman bazında |
| T0.3 MQTT telemetri şeması | ✅ | draft 2020-12 geçerli; topic planı şemanın içinde (`x-topics`) |
| T0.4 Modbus + alarm + OpenAPI + senaryo | ✅ | 13 blok/430 register · 22 kod + 34 eşik + 9 hipotez · 9 uç + WS |
| T0.5 Üç parçalı compose | ⚠️ | Dosyalar hazır, `docker compose config` altı servisi çözüyor; **`up` ile çalıştığı DOĞRULANMADI** (Docker daemon kapalı) |
| T0.6 README iskeleti | ✅ | Tek komutla kurulum + 7 çıktı eşleme tablosu iskeleti |

**Ekstra (planda yoktu, eklendi):** `scripts/check_contracts.py` — sözleşmeler arası tutarlılık denetimi. İlk koşusunda **gerçek bir adres çakışması yakaladı** (`conn_temp` 100–199 ile `conn_dt` 150–199 örtüşüyordu); düzeltildi. Her PR öncesi koşturulacak.

**Faz 0'dan kalan (üçünüzün yapması gerekenler):**

- [x] **Docker Desktop'ı başlatıp yığını doğrula** — T0.5 Adım 6 (aşağıdaki kabul kriteri)
- [ ] **Kulvar atamasını yap** — Bölüm G'yi doldur, `CODEOWNERS`'daki `@kisi-a/b/c` yerine gerçek GitHub handle'larını yaz
- [ ] **Üç dalı aç ve push et** — T0.6 Adım 3
- [ ] **Komiteye 5 soruyu gönder** — T0.6 Adım 4 (teslim formatı, fotoğraflar, AG/OG ağırlığı, RTU protokolü, mevcut Modbus master)
- [ ] **Üçünüz `contracts/` dizinini okuyup onaylayın** — "kendi işimi bu arayüzle yapabilirim" dediğinizde Faz 0 kapanır

**Dosyalar:**
- Oluştur: `.gitattributes`, `.gitignore`, `.editorconfig`, `CODEOWNERS`, dizin iskeleti (`.gitkeep`'lerle)
- Oluştur: `contracts/mqtt-telemetry.schema.json`, `contracts/modbus-map.yaml`, `contracts/alarm-codes.yaml`, `contracts/openapi.yaml`, `contracts/scenario-labels.schema.json`, `contracts/README.md`
- Oluştur: `deploy/compose.yaml`, `deploy/compose.sim.yaml`, `deploy/compose.frontend.yaml`, `deploy/.env.example`
- Değiştir: `README.md` (iskelet)

### T0.1 — Git hijyeni (20 dk, kim yazarsa)

- [ ] **Adım 1: `.gitattributes` oluştur** (kural 1 — en önemli tek dosya)

```gitattributes
* text=auto eol=lf
*.sh    text eol=lf
*.ps1   text eol=crlf
*.png   binary
*.jpg   binary
*.pdf   binary
*.xlsx  binary
*.mp4   binary
*.step  binary
*.kicad_pcb   binary
*.kicad_sch   binary
*.parquet     binary
```

- [ ] **Adım 2: `.gitignore` oluştur**

```gitignore
# Python
.venv/
__pycache__/
*.pyc
.pytest_cache/
# Node
node_modules/
dist/
.vite/
# Üretilen veri ve çıktılar
data/generated/
*.parquet
*.db
loadtest/results/*.json
# Medya (link ile paylaşılır, repoya girmez)
demo/video/*.mp4
demo/video/*.mov
# Sırlar
.env
*.pem
*.key
secrets/
# Derleme
build/
firmware/build/
*.o
*.elf
# KiCad yedekleri
*-backups/
*.kicad_prl
fp-info-cache
```

- [ ] **Adım 3: `.editorconfig` oluştur** (biçim savaşlarını önler)

```editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.py]
indent_size = 4

[*.{c,h}]
indent_size = 4

[*.md]
trim_trailing_whitespace = false
```

- [ ] **Adım 4: Mevcut dosyaları normalize et ve commit et**

```bash
git add --renormalize .
git add .gitattributes .gitignore .editorconfig
git commit -m "chore: git hijyeni - LF normalizasyonu, ignore ve editorconfig"
```

**Kabul:** `git ls-files --eol` çıktısında tüm metin dosyaları `w/lf` gösteriyor.

### T0.2 — Dizin iskeleti (15 dk)

- [ ] **Adım 1: Tüm dizinleri `.gitkeep` ile aç** (kural 11)

```bash
for d in contracts contracts/changes libs/panoalgo/panoalgo libs/panoalgo/tests \
  firmware/core firmware/host firmware/tests firmware/akis-diyagramlari \
  sim data/fixtures data/generated backend/app backend/tests deploy loadtest \
  scripts frontend/src hardware/pano-beyni hardware/sensor-dugumu hardware/mekanik \
  hardware/yerlesim docs demo/senaryo demo/sunum demo/video assets; do
  mkdir -p "$d" && touch "$d/.gitkeep"
done
git add -A && git commit -m "chore: dizin iskeleti"
```

- [ ] **Adım 2: `CODEOWNERS` dosyasını Bölüm A.4'teki içerikle oluştur, gerçek GitHub handle'larını yaz, commit et.**

**Kabul:** `git ls-files | grep gitkeep | wc -l` ≥ 25.

### T0.3 — Sözleşmeler: MQTT telemetri şeması (45 dk · ÜÇÜ BİRLİKTE KARAR VERİR)

Bu, A'nın ürettiği ve B'nin tükettiği tek arayüz. Alan adları **birebir** böyle kalacak.

- [ ] **Adım 1: `contracts/mqtt-telemetry.schema.json` oluştur**

Topic planı (aynı dosyanın başına yorum olarak da yazılır):

| Topic | Periyot | İçerik |
|---|---|---|
| `gridup/pano/{pano_id}/tel` | 10 s | Telemetri özeti (aşağıdaki şema) |
| `gridup/pano/{pano_id}/evt` | olay anında | Olay/alarm adayı (kenar tespiti) |
| `gridup/pano/{pano_id}/hb` | 60 s | Heartbeat (`seq`, `uptime_s`, `rssi_dbm`, `vbak_pct`) |
| `gridup/pano/{pano_id}/cmd` | — | Merkez → kenar komut (ack, bakım modu, test alarmı) |

Telemetri yükü (JSON; üretimde CBOR — `docs/09`'da hesabı var):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "gridup-telemetry-v1",
  "type": "object",
  "required": ["v", "ts", "pano_id", "seq", "t_conn", "elec", "env", "health"],
  "properties": {
    "v": { "const": 1 },
    "ts": { "type": "string", "format": "date-time" },
    "pano_id": { "type": "string", "pattern": "^[A-Z]{3}-[0-9]{5}$" },
    "seq": { "type": "integer", "minimum": 0 },
    "t_conn": {
      "type": "array", "minItems": 4, "maxItems": 25,
      "items": {
        "type": "object",
        "required": ["pt", "t_c", "dt_c"],
        "properties": {
          "pt": { "type": "string", "description": "GIRIS_L1|GIRIS_L2|GIRIS_L3|GIRIS_N|DSYA3_L2 ..." },
          "t_c": { "type": "number" },
          "dt_c": { "type": "number", "description": "ortam uzeri artis (K)" },
          "k": { "type": "number", "description": "isil direnc indeksi" },
          "k_ratio": { "type": "number", "description": "K/K0" },
          "tau_s": { "type": "number" },
          "ttl_h": { "type": ["number", "null"], "description": "70 K sinirina kalan saat" },
          "q": { "type": "integer", "description": "veri kalitesi bayrak alani" }
        }
      }
    },
    "elec": {
      "type": "object",
      "required": ["i_ph", "i_n", "u_ph"],
      "properties": {
        "i_ph": { "type": "array", "minItems": 3, "maxItems": 3, "items": { "type": "number" } },
        "i_n": { "type": "number" },
        "u_ph": { "type": "array", "minItems": 3, "maxItems": 3, "items": { "type": "number" } },
        "thd_i": { "type": "array", "minItems": 3, "maxItems": 3, "items": { "type": "number" } },
        "cosphi": { "type": "number" },
        "unbal_pct": { "type": "number" }
      }
    },
    "env": {
      "type": "object",
      "required": ["t_low_c", "rh_low_pct", "t_up_c", "rh_up_pct"],
      "properties": {
        "t_low_c": { "type": "number" }, "rh_low_pct": { "type": "number" },
        "t_up_c": { "type": "number" }, "rh_up_pct": { "type": "number" },
        "td_low_c": { "type": "number" }, "td_margin_k": { "type": "number" },
        "voc_idx": { "type": ["number", "null"] }, "dt_air_k": { "type": "number" }
      }
    },
    "tvoc": {
      "type": "object",
      "properties": {
        "state": { "type": "integer" }, "trips": { "type": "integer" },
        "det_bits_low": { "type": "integer" }, "det_bits_high": { "type": "integer" },
        "sensor_x2": { "type": "integer" }, "sensor_x3": { "type": "integer" },
        "prot_health_ok": { "type": "boolean" }
      }
    },
    "pd": {
      "type": ["object", "null"],
      "properties": { "pps": { "type": "number" }, "amp_dbmv": { "type": "number" }, "trend": { "type": "number" } }
    },
    "risk": {
      "type": "object",
      "required": ["score", "mode"],
      "properties": {
        "score": { "type": "integer", "minimum": 0, "maximum": 100 },
        "mode": { "type": "string", "description": "alarm-codes.yaml icindeki hipotez kodu" },
        "ttl_h": { "type": ["number", "null"] }
      }
    },
    "alarms": { "type": "array", "items": { "type": "string", "description": "alarm-codes.yaml kodu" } },
    "health": {
      "type": "object",
      "required": ["uptime_s", "nodes_ok"],
      "properties": {
        "uptime_s": { "type": "integer" }, "nodes_ok": { "type": "integer" },
        "nodes_total": { "type": "integer" }, "rssi_dbm": { "type": "number" },
        "vbak_pct": { "type": "number" }, "buffered": { "type": "integer" }
      }
    }
  }
}
```

- [ ] **Adım 2: `pano_id` formatını karara bağla:** `ADM-00001` … `GDZ-00999`. (Filo testinde `SIM-00001`…)
- [ ] **Adım 3: Commit.**

```bash
git add contracts/mqtt-telemetry.schema.json
git commit -m "contract: MQTT telemetri semasi v1 (donduruldu)"
```

**Kabul:** `python -c "import json,jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('contracts/mqtt-telemetry.schema.json')))"` hatasız.

### T0.4 — Sözleşmeler: Modbus haritası, alarm kodları, API (90 dk · ÜÇÜ BİRLİKTE)

- [ ] **Adım 1: `contracts/modbus-map.yaml`** — rapor §6.4b tablosunu makine okunur hale getir. A firmware'de, B Modbus TCP sunucusunda, ikisi de **bu dosyadan** üretecek; `docs/03` de bundan üretilecek.

```yaml
version: 1
endianness: big
mirror_fc03_fc04: true
blocks:
  - name: device_info
    start: 0
    count: 20
    items:
      - { offset: 0, name: map_version,  type: uint16 }
      - { offset: 1, name: fw_version,   type: uint16 }
      - { offset: 2, name: serial_hi,    type: uint16 }
      - { offset: 3, name: serial_lo,    type: uint16 }
      - { offset: 4, name: pano_type,    type: uint16, note: "1=1600kVA dahili" }
  - name: health
    start: 20
    count: 20
    items:
      - { offset: 0, name: uptime_h,     type: uint16 }
      - { offset: 1, name: last_sync_m,  type: uint16 }
      - { offset: 2, name: supply_state, type: uint16 }
      - { offset: 3, name: backup_pct,   type: uint16 }
      - { offset: 4, name: rssi_dbm_neg, type: uint16 }
      - { offset: 5, name: nodes_ok,     type: uint16 }
      - { offset: 6, name: heartbeat,    type: uint16 }
  - name: conn_temp
    start: 100
    count: 100
    scale: 0.1
    type: int16
    unit: degC
    points: [GIRIS_L1, GIRIS_L2, GIRIS_L3, GIRIS_N,
             DSYA1_L1, DSYA1_L2, DSYA1_L3, DSYA2_L1, DSYA2_L2, DSYA2_L3,
             DSYA3_L1, DSYA3_L2, DSYA3_L3, DSYA4_L1, DSYA4_L2, DSYA4_L3,
             DSYA5_L1, DSYA5_L2, DSYA5_L3, DSYA6_L1, DSYA6_L2, DSYA6_L3,
             DSYA7_L1, DSYA7_L2, DSYA7_L3]
  - name: k_index
    start: 200
    count: 100
    scale: 0.1
    type: int16
    unit: percent_of_baseline
    note: "conn_temp ile ayni nokta sirasi"
  - name: environment
    start: 300
    count: 20
    scale: 0.1
    type: int16
    items:
      - { offset: 0, name: t_low_c }
      - { offset: 1, name: rh_low_pct }
      - { offset: 2, name: td_low_c }
      - { offset: 3, name: td_margin_k }
      - { offset: 4, name: t_up_c }
      - { offset: 5, name: rh_up_pct }
      - { offset: 6, name: dt_air_k }
      - { offset: 7, name: voc_idx }
  - name: electrical_mirror
    start: 400
    count: 50
    source: MPR-53CS
    items:
      - { offset: 0, name: i_l1_a, type: uint16, scale: 0.1 }
      - { offset: 1, name: i_l2_a, type: uint16, scale: 0.1 }
      - { offset: 2, name: i_l3_a, type: uint16, scale: 0.1 }
      - { offset: 3, name: i_n_a,  type: uint16, scale: 0.1 }
      - { offset: 4, name: u_l1_v, type: uint16, scale: 0.1 }
      - { offset: 5, name: u_l2_v, type: uint16, scale: 0.1 }
      - { offset: 6, name: u_l3_v, type: uint16, scale: 0.1 }
      - { offset: 7, name: thd_i_l1_pct, type: uint16, scale: 0.1 }
      - { offset: 8, name: thd_i_l2_pct, type: uint16, scale: 0.1 }
      - { offset: 9, name: thd_i_l3_pct, type: uint16, scale: 0.1 }
      - { offset: 10, name: cosphi, type: int16, scale: 0.001 }
      - { offset: 11, name: unbal_pct, type: uint16, scale: 0.1 }
  - name: arc_mirror
    start: 500
    count: 20
    source: ABB TVOC-2
    access: read_only
    items:
      - { offset: 0, name: system_state,     type: uint16, src_pdu: 1300 }
      - { offset: 1, name: trip_count,       type: uint16, src_pdu: 149 }
      - { offset: 2, name: last_det_low,     type: uint16, src_pdu: 100 }
      - { offset: 3, name: last_det_high,    type: uint16, src_pdu: 101 }
      - { offset: 4, name: last_trip_date,   type: uint16, src_pdu: 103 }
      - { offset: 5, name: last_trip_hhmm,   type: uint16, src_pdu: 104 }
      - { offset: 6, name: sensor_status_x2, type: uint16, src_pdu: 222 }
      - { offset: 7, name: sensor_status_x3, type: uint16, src_pdu: 223 }
      - { offset: 8, name: amb_light_x2,     type: uint16, src_pdu: 224 }
      - { offset: 9, name: amb_light_x3,     type: uint16, src_pdu: 225 }
      - { offset: 10, name: prot_health_ok,  type: uint16, note: "bizim ozet bitimiz" }
  - name: pd
    start: 600
    count: 20
    items:
      - { offset: 0, name: pulses_per_s, type: uint16 }
      - { offset: 1, name: amp_dbmv,     type: int16 }
      - { offset: 2, name: trend_slope,  type: int16, scale: 0.01 }
  - name: risk
    start: 700
    count: 20
    items:
      - { offset: 0, name: risk_score,   type: uint16, note: "0-100" }
      - { offset: 1, name: fault_mode,   type: uint16, note: "alarm-codes.yaml hipotez id" }
      - { offset: 2, name: ttl_hours,    type: uint16, note: "65535 = bilinmiyor" }
  - name: alarms
    start: 800
    count: 30
    note: "bit alanlari + mandalli kopyalari; bit haritasi alarm-codes.yaml icinde"
  - name: event
    start: 830
    count: 20
    items:
      - { offset: 0, name: event_count,  type: uint16 }
      - { offset: 1, name: last_code,    type: uint16 }
      - { offset: 2, name: ts_hi,        type: uint16 }
      - { offset: 3, name: ts_lo,        type: uint16 }
  - name: command
    start: 900
    count: 10
    access: write
    functions: [6, 16]
    auth: password_register
    items:
      - { offset: 0, name: password,      type: uint16 }
      - { offset: 1, name: ack_alarm,     type: uint16 }
      - { offset: 2, name: reset_latch,   type: uint16 }
      - { offset: 3, name: maint_mode,    type: uint16 }
      - { offset: 4, name: test_alarm,    type: uint16 }
coils:
  - { addr: 0, name: critical_alarm }
  - { addr: 1, name: warning_active }
  - { addr: 2, name: comms_ok }
  - { addr: 3, name: maint_mode }
  - { addr: 4, name: prot_health_ok }
```

- [ ] **Adım 2: `contracts/alarm-codes.yaml`** — rapor §6.5/§6.6'daki eşikleri ve hipotezleri tek kaynağa koy.

```yaml
version: 1
priorities:
  P1: { name: "Kritik", sms: true, whatsapp: true, call_after_min: 5, escalate_after_min: 15, scada: true, local_relay: siren }
  P2: { name: "Alarm",  sms: true, whatsapp: true, escalate_after_min: 30, scada: true, local_relay: heater_fan }
  P3: { name: "Uyari",  sms: false, whatsapp: false, daily_digest: true, work_order: planned }
  INFO: { name: "Bilgi" }
  SYS:  { name: "Sistem" }
alarms:
  - { code: ALM-THR-TERM-WARN, bit: 0,  prio: P3, layer: L0, text: "Terminal sicaklik artisi 50 K ustu",  basis: "IEC 61439-1 Tablo 6" }
  - { code: ALM-THR-TERM-ALM,  bit: 1,  prio: P2, layer: L0, text: "Terminal sicaklik artisi 70 K ustu",  basis: "IEC 61439-1 Tablo 6" }
  - { code: ALM-THR-BUS-ALM,   bit: 2,  prio: P1, layer: L0, text: "Bara sicaklik artisi 105 K ustu",     basis: "IEC 61439-1" }
  - { code: ALM-THR-PHASE-DIF, bit: 3,  prio: P2, layer: L0, text: "Fazlar arasi fark 15 K ustu",          basis: "NETA MTS" }
  - { code: ALM-K-WARN,        bit: 4,  prio: P3, layer: L1, text: "Isil direnc indeksi K/K0 > 1.3",       basis: "Rapor 6.5" }
  - { code: ALM-K-ALM,         bit: 5,  prio: P2, layer: L1, text: "Isil direnc indeksi K/K0 > 1.6",       basis: "Rapor 6.5" }
  - { code: ALM-TTL-14D,       bit: 6,  prio: P3, layer: L1, text: "70 K sinirina tahmini 14 gunden az",   basis: "Rapor 6.5/15.1" }
  - { code: ALM-DEW-WARN,      bit: 7,  prio: P3, layer: L1, text: "Ciy noktasi marji < 3 K",              basis: "Magnus" }
  - { code: ALM-DEW-ALM,       bit: 8,  prio: P2, layer: L1, text: "Ciy noktasi marji < 1 K",              basis: "Magnus" }
  - { code: ALM-I-OVER,        bit: 9,  prio: P2, layer: L0, text: "Faz akimi anma degeri ustu",           basis: "Tablo 8" }
  - { code: ALM-NEUTRAL-THD,   bit: 10, prio: P3, layer: L1, text: "Notr akimi + akim THD birlikte artti", basis: "Rapor 6.5" }
  - { code: ALM-ARC-TRIP,      bit: 11, prio: P1, layer: L0, text: "TVOC-2 ark tripi",                     basis: "TVOC-2 reg 149" }
  - { code: ALM-PROT-HEALTH,   bit: 12, prio: P1, layer: L0, text: "Ark korumasi dedektor arizasi",        basis: "TVOC-2 reg 222/223" }
  - { code: ALM-PD-TREND,      bit: 13, prio: P3, layer: L1, text: "PD darbe/genlik trendi artiyor",       basis: "EA Technology" }
  - { code: ALM-DQ-FROZEN,     bit: 14, prio: SYS, layer: "L-1", text: "Sensor degeri donmus" }
  - { code: ALM-DQ-JUMP,       bit: 15, prio: SYS, layer: "L-1", text: "Fiziksel olmayan degisim hizi" }
  - { code: ALM-NODE-LOST,     bit: 16, prio: SYS, layer: "L-1", text: "Dugum sessiz" }
  - { code: ALM-COMMS-LOST,    bit: 17, prio: SYS, layer: "L-1", text: "Merkez baglantisi koptu (heartbeat yok)" }
  - { code: ALM-DOOR-UNAUTH,   bit: 18, prio: P2, layer: L0, text: "Planli is emri olmadan kapak acildi" }
  - { code: ALM-LASTGASP,      bit: 19, prio: P2, layer: L0, text: "Besleme kesildi (son nefes)" }
hypotheses:
  - { id: 1, code: HYP-LOOSE-CONN, text: "Gevsek/oksitlenmis baglanti", severity_w: 1.0, evidence: [ALM-K-WARN, ALM-K-ALM, ALM-THR-PHASE-DIF, ALM-TTL-14D] }
  - { id: 2, code: HYP-OVERLOAD,   text: "Asiri yuk (ariza degil)",     severity_w: 0.4, evidence: [ALM-I-OVER] }
  - { id: 3, code: HYP-CONDENSE,   text: "Yogusma / yuzeysel kacak",    severity_w: 0.7, evidence: [ALM-DEW-WARN, ALM-DEW-ALM] }
  - { id: 4, code: HYP-HARMONIC,   text: "Harmonik kaynakli notr isinmasi", severity_w: 0.6, evidence: [ALM-NEUTRAL-THD] }
  - { id: 5, code: HYP-PD,         text: "Izolasyon bozulmasi (OG)",    severity_w: 0.8, evidence: [ALM-PD-TREND] }
  - { id: 6, code: HYP-ARC,        text: "Ark olayi",                   severity_w: 1.0, evidence: [ALM-ARC-TRIP] }
  - { id: 7, code: HYP-PROT-LOSS,  text: "Koruma sagligi kaybi",        severity_w: 1.0, evidence: [ALM-PROT-HEALTH] }
  - { id: 8, code: HYP-SELF-FAULT, text: "Izleme sistemi arizasi",      severity_w: 0.3, evidence: [ALM-NODE-LOST, ALM-COMMS-LOST, ALM-DQ-FROZEN] }
```

- [ ] **Adım 3: `contracts/openapi.yaml`** — C'nin tükettiği, B'nin sunduğu arayüz. En az şu uçlar, bu adlarla:

| Metot | Yol | Döner |
|---|---|---|
| GET | `/api/v1/panels` | `[{pano_id, name, lat, lon, risk_score, risk_mode, top_alarm, last_seen, ttl_h}]` |
| GET | `/api/v1/panels/{pano_id}` | Tek pano detayı + `points: [{pt, t_c, dt_c, k_ratio, ttl_h, q}]` + `env` + `elec` + `tvoc` + `health` |
| GET | `/api/v1/panels/{pano_id}/series` | `?tags=t_conn.GIRIS_L2,elec.i_ph.0&from=&to=&step=` → `{tag: [[ts, value]]}` |
| GET | `/api/v1/alarms` | `?state=active,acked,shelved&prio=P1,P2` → `[{id, pano_id, code, prio, state, raised_at, acked_by, reason: {signals, thresholds}, advice}]` |
| POST | `/api/v1/alarms/{id}/ack` | `{by, note}` → 200 |
| POST | `/api/v1/alarms/{id}/shelve` | `{by, minutes, reason}` → 200 |
| GET | `/api/v1/events/{id}/blackbox` | `{event, window_h: 72, series: {...}, timeline: [...]}` |
| GET | `/api/v1/fleet/kpi` | `{alarms_per_100_panels_per_day, active_by_prio, comms_ok_pct, p95_latency_ms}` |
| WS | `/api/v1/stream` | `{type: "tel"\|"alarm"\|"kpi", payload: ...}` |

- [ ] **Adım 4: `contracts/scenario-labels.schema.json`** — A'nın ürettiği etiket dosyası, A'nın doğrulama betiği ve B'nin yük testi bunu okur.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "gridup-scenario-labels-v1",
  "type": "object",
  "required": ["scenario_id", "seed", "pano_id", "duration_h", "labels"],
  "properties": {
    "scenario_id": { "type": "string", "enum": ["S0_normal", "S1_loose_conn", "S2_overload", "S3_condense", "S4_arc", "S5_prot_health", "S6_comms_loss", "S7_harmonic", "S8_sensor_fault", "S9_pd_trend"] },
    "seed": { "type": "integer" },
    "pano_id": { "type": "string" },
    "duration_h": { "type": "number" },
    "labels": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["t_start", "t_end", "type", "point", "expect"],
        "properties": {
          "t_start": { "type": "string", "format": "date-time" },
          "t_end": { "type": "string", "format": "date-time" },
          "type": { "type": "string" },
          "point": { "type": "string" },
          "severity": { "type": "string", "enum": ["P1", "P2", "P3", "SYS"] },
          "expect": { "type": "array", "items": { "type": "string", "description": "beklenen alarm kodlari" } },
          "l0_breach_at": { "type": ["string", "null"], "format": "date-time", "description": "sabit 70 K esiginin asildigi an - one alma suresi bundan olculur" }
        }
      }
    }
  }
}
```

- [ ] **Adım 5: `contracts/README.md`** yaz: "Bu dizin donmuştur. Değişiklik için `contracts/changes/` altına yeni dosya aç, 3 onay al, `version` alanını artır." + her dosyanın kimler tarafından tüketildiği tablosu.
- [ ] **Adım 6: Commit.**

```bash
git add contracts/
git commit -m "contract: Modbus haritasi, alarm kodlari, OpenAPI ve senaryo etiketleri v1 (donduruldu)"
```

**Kabul:** Üç kişi de sözleşmeleri okuyup "kendi işimi bu arayüzle yapabilirim" dedi. `python -c "import yaml;[yaml.safe_load(open(f)) for f in ['contracts/modbus-map.yaml','contracts/alarm-codes.yaml','contracts/openapi.yaml']]"` hatasız.

### T0.5 — Çalışan iskelet yığın (75 dk)

- [ ] **Adım 1: `deploy/compose.yaml`** (B'nin dosyası, Faz 0'da birlikte yazılır)

```yaml
name: gridup
include:
  - path: compose.sim.yaml
  - path: compose.frontend.yaml
services:
  mosquitto:
    image: eclipse-mosquitto:2.0
    ports: ["1883:1883"]
    volumes: ["./mosquitto.conf:/mosquitto/config/mosquitto.conf:ro"]
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD:-gridup}
      POSTGRES_DB: gridup
    ports: ["5432:5432"]
    volumes: ["tsdata:/var/lib/postgresql/data", "./initdb:/docker-entrypoint-initdb.d:ro"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 10
  backend:
    build: ../backend
    environment:
      MQTT_HOST: mosquitto
      DB_DSN: postgresql://postgres:${DB_PASSWORD:-gridup}@timescaledb:5432/gridup
    ports: ["8000:8000"]
    depends_on:
      timescaledb: { condition: service_healthy }
      mosquitto: { condition: service_started }
  grafana:
    image: grafana/grafana:11.2.0
    ports: ["3001:3000"]
    environment:
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
    volumes: ["./grafana:/etc/grafana/provisioning:ro"]
volumes:
  tsdata:
```

- [ ] **Adım 2: `deploy/compose.sim.yaml`** (A'nın dosyası) — `panosim` (veri üreteci → MQTT), `mpr-sim`, `tvoc-sim` servisleri, her biri `build: ../sim`.
- [ ] **Adım 3: `deploy/compose.frontend.yaml`** (C'nin dosyası) — `frontend` servisi, `build: ../frontend`, port `3000:80`.
- [ ] **Adım 4: `deploy/.env.example`** — `DB_PASSWORD=`, `WHATSAPP_TOKEN=`, `WHATSAPP_PHONE_ID=`, `ALERT_RECIPIENTS=`, `SMS_DEVICE=/dev/ttyV0`. (Gerçek `.env` gitignore'da.)
- [ ] **Adım 5: Her kulvar için "merhaba dünya" konteyneri** — backend `GET /health` → `{"ok": true}`, frontend boş sayfa, sim 10 saniyede bir sabit JSON yayınlıyor. Hepsi ayağa kalkıyor.
- [ ] **Adım 6: `docker compose -f deploy/compose.yaml up -d` çalıştır, altı servisin de `healthy`/`running` olduğunu gör, commit et.**

**Kabul:** `curl localhost:8000/health` → `{"ok":true}` · `mosquitto_sub -t 'gridup/#' -C 1` bir mesaj yakalıyor · `localhost:3000` açılıyor.

### T0.6 — README iskeleti, branch'lerin açılması ve komiteye sorular (45 dk)

- [ ] **Adım 1: `README.md`** — başlık, tek cümlelik tanım, `docker compose up` talimatı, Bölüm A.1 sahiplik tablosu, "7 teknik çıktı → dosya" tablosunun boş iskeleti (C Faz 4'te doldurur).
- [ ] **Adım 2: Kişileri kulvarlara ata.** Bu satırı doldur ve commit et: `A = ____, B = ____, C = ____` (bu dosyanın en altındaki "Atama" bölümüne).
- [ ] **Adım 3: Üç dalı aç ve push et**

```bash
git push origin main
git checkout -b a/faz1-veri-ureteci && git push -u origin a/faz1-veri-ureteci && git checkout main
git checkout -b b/faz1-ingest && git push -u origin b/faz1-ingest && git checkout main
git checkout -b c/faz1-ui-iskelet && git push -u origin c/faz1-ui-iskelet && git checkout main
```

- [ ] **Adım 4: C, komiteye rapor §12.2'deki 10 sorudan şu 5'ini bugün gönderir** (cevap gecikirse plan değişmeyecek şekilde seçildi): teslim platformu/formatı ve repo public mi (1) · kabin fotoğrafları (2) · AG mi OG mü ağırlıklı (3) · RTU protokolü ve Modbus master durumu (4, 5).
- [ ] **Adım 5: Faz 0 kapanış commit'i.**

**M0 kapısı:** Üçü de kendi dalında, `contracts/` donmuş, yığın ayakta, komiteye sorular gitmiş.

---

## Faz 1 — Dikey Dilim (13 Eylül · M1: uçtan uca ilk akış)

> **Kural:** Bu faz derinlik değil **bağlantı** fazı. Her kulvar en basit haliyle bir sonrakine veri geçirecek. Güzelleştirme yok.

### TA1 — A: Sentetik veri üreteci v1 + MQTT yayını

**Dosyalar:**
- Oluştur: `libs/panoalgo/panoalgo/__init__.py`, `physics.py`, `profiles.py`, `generator.py`
- Oluştur: `libs/panoalgo/tests/test_dewpoint.py`, `tests/test_generator.py`
- Oluştur: `libs/panoalgo/pyproject.toml`
- Oluştur: `sim/panosim.py` (CLI: üreteç → MQTT), `sim/Dockerfile`

**Arayüzler:**
- Üretir (B ve C buna güvenir): `panoalgo.physics.dew_point(t_c: float, rh_pct: float) -> float` · `panoalgo.profiles.load_profile(kind: Literal["konut","ticari","karma"], ts: datetime) -> float` (0–1 normalize yük) · `panoalgo.generator.PanelSimulator(pano_id: str, seed: int, profile: str).step(dt_s: float) -> dict` (dönen sözlük **`contracts/mqtt-telemetry.schema.json`**'a uyar)
- Tüketir: `contracts/mqtt-telemetry.schema.json`

- [x] **Adım 1: Başarısız testi yaz** — `libs/panoalgo/tests/test_dewpoint.py`

```python
import pytest
from panoalgo.physics import dew_point


@pytest.mark.parametrize(
    "t_c,rh_pct,expected",
    [(25.0, 60.0, 16.7), (20.0, 85.0, 17.4), (15.0, 95.0, 14.2), (35.0, 50.0, 23.0)],
)
def test_dew_point_magnus(t_c, rh_pct, expected):
    """Rapor 15.1 tablosundaki dort referans deger."""
    assert dew_point(t_c, rh_pct) == pytest.approx(expected, abs=0.1)


def test_dew_point_rejects_invalid_humidity():
    with pytest.raises(ValueError):
        dew_point(20.0, 0.0)
```

- [x] **Adım 2: Testi koştur, başarısız olduğunu gör**

Komut: `cd libs/panoalgo && pytest tests/test_dewpoint.py -v`
Beklenen: `ModuleNotFoundError: No module named 'panoalgo.physics'`

- [x] **Adım 3: Minimum implementasyonu yaz** — `libs/panoalgo/panoalgo/physics.py`

```python
"""Fiziksel donusumler. Kaynak: HACKATHON_ANALIZ_RAPORU.md 15.1."""
import math

MAGNUS_B = 17.62
MAGNUS_C = 243.12


def dew_point(t_c: float, rh_pct: float) -> float:
    """Magnus formuluyle ciy noktasi (degC)."""
    if not 0.0 < rh_pct <= 100.0:
        raise ValueError(f"rh_pct (0,100] araliginda olmali: {rh_pct}")
    gamma = math.log(rh_pct / 100.0) + MAGNUS_B * t_c / (MAGNUS_C + t_c)
    return MAGNUS_C * gamma / (MAGNUS_B - gamma)


def dew_point_margin(surface_t_c: float, air_t_c: float, rh_pct: float) -> float:
    """Yuzey sicakligi ile ciy noktasi arasindaki marj (K). Negatif = yogusma."""
    return surface_t_c - dew_point(air_t_c, rh_pct)
```

- [x] **Adım 4: Testi koştur, geçtiğini gör** — `pytest tests/test_dewpoint.py -v` → 5 passed
- [x] **Adım 5: Isıl modeli ve yük profilini yaz** — `profiles.py`: 168 kutulu (saat-of-hafta) konut/ticari/karma profil + mevsim katsayısı + AR(1) gürültü (rapor §15.2). `generator.py`: nokta başına `ΔT[k+1] = a·ΔT[k] + (1-a)·K·I²` ayrık ısıl model (`a = exp(-Ts/τ)`, τ = 10–30 dk), ortam sıcaklığı günlük sinüs, nem ters ilişkili, MPR türevli elektriksel büyüklükler, TVOC-2 durum makinesi (başlangıçta sakin).
- [x] **Adım 6: Üreteç testi yaz ve geçir** — `tests/test_generator.py`: (a) üretilen sözlük şemaya uyuyor (`jsonschema` ile), (b) aynı `seed` aynı diziyi veriyor, (c) lag-1 otokorelasyon > 0.9 (verilen Excel'in 0,00'ına karşıt — **bu testin kendisi bir sunum slaytı**).
- [x] **Adım 7: `sim/panosim.py`** — `python -m sim.panosim --panels 3 --speed 60 --mqtt mosquitto:1883` → her 10 s'de (hızlandırılmış) `gridup/pano/{id}/tel` yayınlar.
- [x] **Adım 8: Commit**

```bash
git add libs/panoalgo sim/panosim.py sim/Dockerfile
git commit -m "feat(sim): fizik tabanli sentetik veri ureteci + MQTT yayini"
```

**Kabul:** `mosquitto_sub -t 'gridup/pano/+/tel' -C 3` şemaya uyan 3 mesaj gösteriyor; `pytest` yeşil.

### TB1 — B: Ingestion + DB + API v1

**Dosyalar:**
- Oluştur: `backend/app/main.py`, `config.py`, `db.py`, `ingest.py`, `models.py`, `api/panels.py`, `api/alarms.py`
- Oluştur: `deploy/initdb/001_schema.sql`
- Oluştur: `backend/tests/test_ingest.py`, `backend/tests/test_api_panels.py`
- Oluştur: `backend/requirements.txt`, `backend/Dockerfile`

**Arayüzler:**
- Tüketir: `contracts/mqtt-telemetry.schema.json`, `contracts/alarm-codes.yaml`
- Üretir (C buna güvenir): `contracts/openapi.yaml`'daki `GET /api/v1/panels`, `GET /api/v1/panels/{id}`, `GET /api/v1/alarms`, `WS /api/v1/stream`

- [x] **Adım 1: Şemayı yaz** — `deploy/initdb/001_schema.sql`: `panels` (pano_id PK, ad, konum, tip), `telemetry` (TimescaleDB hypertable, `ts`, `pano_id`, `tag`, `value` — uzun format; 10 s), `alarms` (id, pano_id, code, prio, state, raised_at, cleared_at, acked_by, reason JSONB), `events`.
- [x] **Adım 2: Ingest testini yaz** — `backend/tests/test_ingest.py`: şemaya uygun bir telemetri yükünü `ingest.handle_message()`'a ver, `telemetry` tablosunda beklenen satır sayısının (nokta sayısı + elektriksel + ortam) oluştuğunu doğrula; şema dışı yükün reddedilip `SYS` kaydı bıraktığını doğrula.
- [x] **Adım 3: Testi koştur, başarısız gör.** Beklenen: `ImportError`.
- [x] **Adım 4: `ingest.py`'ı yaz** — paho-mqtt abonesi → `jsonschema` doğrulaması → uzun formata düzleştirme → toplu `COPY`/`executemany` insert. Şema dışı mesaj **düşürülmez, karantinaya** yazılır (veri kalitesi kanıtı).
- [x] **Adım 5: Testi geçir.**
- [x] **Adım 6: API'yi yaz** — `GET /api/v1/panels` (son telemetriden türetilmiş filo listesi), `GET /api/v1/panels/{id}`, `GET /api/v1/alarms` (şimdilik boş liste), `WS /api/v1/stream` (MQTT → WebSocket köprüsü). Testler: her uç için durum kodu + şema doğrulaması.
- [x] **Adım 7: `docker compose up` ile uçtan uca gör:** sim → mosquitto → ingest → timescale → API.
- [x] **Adım 8: Commit**

```bash
git add backend deploy/initdb
git commit -m "feat(backend): MQTT ingestion, TimescaleDB semasi ve panel API v1"
```

**Kabul:** `curl 'localhost:8000/api/v1/panels' | jq '.[0].pano_id'` bir pano döndürüyor; `pytest backend/tests -v` yeşil.

### TC1 — C: Arayüz iskeleti + filo listesi + pano detay

**Dosyalar:**
- Oluştur: `frontend/package.json`, `vite.config.ts`, `index.html`, `Dockerfile`, `nginx.conf`
- Oluştur: `frontend/src/main.tsx`, `App.tsx`, `api/client.ts`, `theme.css`
- Oluştur: `frontend/src/pages/FiloListesi.tsx`, `pages/PanoDetay.tsx`
- Oluştur: `frontend/src/mocks/panels.json` (B'nin API'si gecikirse diye)

**Arayüzler:**
- Tüketir: `contracts/openapi.yaml` (asla B'ye sormadan alan adı uydurmaz; uydurma gerekiyorsa `contracts/changes/` altına öneri dosyası açar)

- [ ] **Adım 1: Vite + React + TS projesini kur, `theme.css`'e "yüksek performanslı HMI" paletini yaz** — gri zemin, renk yalnızca anormalde (P1 kırmızı, P2 turuncu, P3 sarı, normal gri), koyu tema, renk körlüğü için her renge ikon + metin eşlik eder (rapor §6.7).
- [ ] **Adım 2: `api/client.ts`** — `contracts/openapi.yaml`'dan tip türet (elle yazılan tipler `src/api/types.ts`'te tek yerde). `VITE_API_BASE` boşsa `mocks/panels.json`'dan okur → B'yi beklemeden çalışır.
- [ ] **Adım 3: `FiloListesi.tsx`** — risk skoruna göre sıralı tablo: pano, risk skoru (0–100), baskın hipotez, sınıra kalan süre, son görülme, trend oku. Satıra tıklayınca detay.
- [ ] **Adım 4: `PanoDetay.tsx`** — nokta tablosu (nokta, °C, ΔT, K/K₀, kalite bayrağı), ortam bloğu (çiy noktası marjı dahil), elektriksel blok, TVOC-2 bloğu, cihaz sağlığı bloğu.
- [ ] **Adım 5: WebSocket ile canlı güncelleme** (`/api/v1/stream`), bağlantı kopunca "veri eski" uyarı şeridi.
- [ ] **Adım 6: Commit**

```bash
git add frontend deploy/compose.frontend.yaml
git commit -m "feat(frontend): filo listesi ve pano detay ekranlari, HMI paleti"
```

**Kabul:** `localhost:3000` canlı veriyle 3 panoyu listeliyor, detay açılıyor.

**🏁 M1 kapısı (13 Eyl 21:00):** `docker compose up` → sentetik veri → MQTT → DB → API → ekranda canlı pano. Üç kulvar birbirine bağlandı. **Bu kapı geçilmezse Faz 2'ye geçilmez**; geçilmediyse 14 Eylül sabahı üçü birlikte bu zinciri tamamlar.

---

## Faz 2 — Tespit Çekirdeği, Alarm ve Bildirim (14–15 Eylül · M2: telefona gerçek mesaj)

### TA2 — A: L-1/L0/L1 tespit katmanları + etiketli senaryolar

**Dosyalar:**
- Oluştur: `libs/panoalgo/panoalgo/quality.py`, `limits.py`, `detect.py`, `fusion.py`, `scenarios.py`
- Oluştur: `libs/panoalgo/tests/test_k_index.py`, `test_limits.py`, `test_quality.py`, `test_scenarios.py`
- Oluştur: `data/fixtures/S0_normal.csv`, `S1_loose_conn.csv`, `S1_loose_conn.labels.json` (ve diğer senaryolar)
- Oluştur: `docs/05-anomali-tespiti.md`, `docs/14-veri-ureteci.md`

**Arayüzler:**
- Üretir (B'nin risk motoru **bunu import eder**, kendi algoritmasını yazmaz):
  - `panoalgo.quality.check(sample: dict, prev: dict | None) -> list[str]` (alarm kodları: `ALM-DQ-*`)
  - `panoalgo.limits.evaluate(sample: dict) -> list[str]` (L0 kodları, `contracts/alarm-codes.yaml`'dan okur)
  - `panoalgo.detect.KIndexEstimator(ts: float, lam: float = 0.998)` · `.update(i_a: float, dt_c: float) -> KState` · `.freeze_baseline() -> None` · `KState = NamedTuple(k, k_ratio, tau_s, ttl_h, excited: bool)`
  - `panoalgo.detect.phase_compare(points: list[dict], i_ph: list[float]) -> dict[str, float]`
  - `panoalgo.fusion.score(alarm_codes: list[str], features: dict) -> RiskResult` · `RiskResult = NamedTuple(score: int, mode: str, ttl_h: float | None, contributions: dict[str, float])`
  - `panoalgo.scenarios.build(scenario_id: str, seed: int, duration_h: float) -> tuple[pandas.DataFrame, dict]` (ikinci dönen değer `contracts/scenario-labels.schema.json`'a uyar)

- [x] **Adım 1: K indeksi için başarısız testi yaz** — `libs/panoalgo/tests/test_k_index.py`

```python
import numpy as np
from panoalgo.detect import KIndexEstimator


def _simulate(k_true: float, n: int, ts: float = 60.0, tau: float = 900.0, seed: int = 0):
    """Isil modelden sentetik (akim, sicaklik artisi) cifti uretir."""
    rng = np.random.default_rng(seed)
    a = np.exp(-ts / tau)
    dt = 0.0
    out = []
    for i in range(n):
        i_a = 200.0 + 150.0 * np.sin(2 * np.pi * i / 96) + rng.normal(0, 10)
        dt = a * dt + (1 - a) * k_true * i_a**2
        out.append((i_a, dt + rng.normal(0, 0.2)))
    return out


def test_k_index_tracks_degradation():
    """Gevseyen baglantida K/K0 yukselir; tau makul araliktadir."""
    est = KIndexEstimator(ts=60.0, lam=0.998)
    for i_a, dt_c in _simulate(k_true=2.0e-4, n=2000):
        est.update(i_a=i_a, dt_c=dt_c)
    est.freeze_baseline()

    state = None
    for i_a, dt_c in _simulate(k_true=3.2e-4, n=2000, seed=1):
        state = est.update(i_a=i_a, dt_c=dt_c)

    assert state.k_ratio > 1.5, f"bozulma yakalanmadi: {state.k_ratio}"
    assert 600 < state.tau_s < 1400, f"tau kestirimi sapti: {state.tau_s}"


def test_k_index_not_updated_without_excitation():
    """Yuk sabitse RLS guncellenmez (kalici uyarim kosulu)."""
    est = KIndexEstimator(ts=60.0, lam=0.998)
    state = None
    for _ in range(500):
        state = est.update(i_a=300.0, dt_c=18.0)
    assert state.excited is False
```

- [x] **Adım 2: Testi koştur, başarısız gör.** Beklenen: `ImportError: cannot import name 'KIndexEstimator'`.
- [x] **Adım 3: RLS kestirimcisini yaz** — `detect.py`, rapor §15.1'deki unutma faktörlü RLS (θ = [a, β]ᵀ, φ = [ΔT, I²]ᵀ); `K = β/(1−a)`, `τ = −Ts/ln(a)`; uyarım kontrolü: son pencerede `var(I²)` eşiğin altındaysa güncelleme yapılmaz (`excited=False`).
- [x] **Adım 4: Testi geçir.**
- [x] **Adım 5: L-1 veri kalitesi + L0 limitleri** — `quality.py` (donmuş değer, fiziksel olmayan değişim hızı, bağlantı sıcaklığı ortamın altı, zaman damgası kayması) ve `limits.py` (eşikler **yalnızca** `contracts/alarm-codes.yaml`'dan). Her biri için test.
- [x] **Adım 6: Sınıra kalan süre + faz karşılaştırması + füzyon** — `ttl_h`: `K(t) ≈ K_now + K̇·t` (EWMA eğim) ve saat-of-hafta yük profiliyle ΔT tahmini, 70 K'yı ilk aşma anı. `fusion.score()`: hipotez kanıt örüntüleri `contracts/alarm-codes.yaml`'dan, ciddiyet ağırlığıyla 0–100.
- [x] **Adım 7: Etiketli senaryo üreteci** — `scenarios.py`: S0–S9 (rapor §15.2 tablosu). Her biri CSV + etiket JSON olarak `data/fixtures/`'a yazılır (≤1 MB, seed'li). Test: her senaryo şemaya uyan etiket üretiyor ve `S1`'de `l0_breach_at` dolu.
- [x] **Adım 8: `docs/05` ve `docs/14`'ü yaz** (formüller, eşikler, senaryo kataloğu).
- [x] **Adım 9: Commit** (her adım sonunda ayrı commit; son commit mesajı: `feat(algo): L-1/L0/L1 tespit katmanlari + etiketli senaryo seti`)

**Kabul:** `pytest libs/panoalgo -v` yeşil (≥20 test) · `python -m panoalgo.scenarios --list` 10 senaryo listeliyor · `S1` fixture'ında K/K₀ 1,6'yı L0 ihlalinden **en az 48 saat önce** geçiyor (bu sayı `docs/12`'nin ana kanıtı).

### TB2 — B: Risk motoru + ISA-18.2 alarm yöneticisi + bildirim ağ geçidi

**Dosyalar:**
- Oluştur: `backend/app/risk.py` (A'nın paketini sarar), `alarm_manager.py`, `notify/__init__.py`, `notify/whatsapp.py`, `notify/sms_modem.py`, `notify/templates.py`
- Oluştur: `backend/tests/test_alarm_manager.py`, `test_notify.py`
- Oluştur: `scripts/virtual_gsm_modem.py`
- Oluştur: `docs/06-alarm-matrisi.md`

**Arayüzler:**
- Tüketir: `panoalgo.quality/limits/detect/fusion` (A), `contracts/alarm-codes.yaml`
- Üretir (C buna güvenir): `POST /api/v1/alarms/{id}/ack`, `/shelve`, `GET /api/v1/alarms` tam gövdesi (`reason.signals`, `reason.thresholds`, `advice` alanları dolu)

- [x] **Adım 1: Alarm durum makinesi testini yaz** — `backend/tests/test_alarm_manager.py`: ISA-18.2 yaşam döngüsü (`normal → active → acked → cleared`; `shelved` süreli ve gerekçeli; P1 **asla** bastırılamaz — bakım modunda bile). Histerezis: eşik altına inse de 5 dk geri dönmüyorsa temizlenir. Gruplama: aynı kök nedenden 10 dk içinde gelen alarmlar tek `event_id` altında.
- [x] **Adım 2: Testi koştur, başarısız gör.**
- [x] **Adım 3: `alarm_manager.py`'ı yaz ve testi geçir.**
- [ ] **Adım 4: Risk motorunu bağla** — `risk.py`: ingest edilen her telemetri için `panoalgo` çağrıları → alarm adayları → alarm yöneticisi. **A'nın algoritmasını yeniden yazma; import et.**
- [x] **Adım 5: Sanal GSM modem yaz** — `scripts/virtual_gsm_modem.py`: PTY çifti açar (`socat`/`pyserial` ile), `AT`, `AT+CMGF=1`, `AT+CMGS="+90..."` komutlarını yanıtlar, gönderilen her SMS'i `demo/sms-log.txt`'ye zaman damgalı PDU dökümüyle yazar. `notify/sms_modem.py` **üretim sürücüsüdür** (gerçek modemde aynı kod; fark yalnızca `SMS_DEVICE` yolu).
- [x] **Adım 6: WhatsApp Cloud API gönderici** — `notify/whatsapp.py`: yalnızca hassas olmayan kısa metin (saha kodu, öncelik, tek satır açıklama, iç portal bağlantısı). Token `.env`'den. Test numarası ≤5 alıcı. Ağ yoksa düşürülen mesaj kuyruğa alınır ve log'lanır (demo internet olmadan da çökmemeli).
- [x] **Adım 7: Eskalasyon ve çift yönlü onay** — P1'de 5 dk onay yoksa ikinci alıcı, 15 dk'da üst amir; gelen "1"/"2" SMS'i ack'e çevirir (sanal modemden okunur).
- [x] **Adım 8: `docs/06`'yı yaz** (öncelik matrisi, kanallar, hedef dağılım %5/%15/%80, alarm seli önlemleri).
- [x] **Adım 9: Commit** — `feat(backend): ISA-18.2 alarm yoneticisi, risk motoru ve bildirim ag gecidi`

**Kabul:** `pytest backend/tests -v` yeşil · S1 fixture'ı oynatıldığında `demo/sms-log.txt`'de AT komut kaydı oluşuyor **ve** bir telefona gerçek WhatsApp mesajı düşüyor.

### TC2 — C: Alarm konsolu + dijital ikiz + donanım şeması başlangıcı

**Dosyalar:**
- Oluştur: `frontend/src/pages/AlarmKonsolu.tsx`, `components/AlarmKarti.tsx`, `components/PanoIkiz.tsx`
- Oluştur: `assets/ek2-14-pano.svg` (EK-II/14 ölçülerine göre çizilmiş **kendi** çizimimiz: 1600 × 1500 × 450 mm, üst bölme/DSYA sıraları/alt kablo bölgesi)
- Oluştur: `hardware/pano-beyni/pano-beyni.kicad_sch`, `hardware/pano-beyni/io-tablosu.md`
- Oluştur: `docs/16-ux-tasarim.md`

- [x] **Adım 1: Alarm konsolu** — öncelik/zaman/konum sıralı liste; her kartta **"Neden?"** (katkı yapan sinyaller + eşikleri, `reason` alanından), **"Ne yapmalı?"** (`advice`), **"Ne kadar acil?"** (`ttl_h`); onay/raf/yorum butonları; eskalasyon sayacı. P1'de görsel + sesli.
- [x] **Adım 2: Dijital ikiz** — `assets/ek2-14-pano.svg` üzerinde sensör noktaları; `t_conn[].dt_c`/`k_ratio`'ya göre renklendirme; tıklayınca o noktanın trendi. **Gizlilik:** komitenin PDF'i kullanılmaz, ölçülere sadık kendi SVG'miz çizilir (rapor §12.1).
- [x] **Adım 3: KiCad şeması v1** — ~~gerçek parça numaralarıyla...~~ **Sapma (bkz. Günlük Kayıt):** bu ortamda internet/KiCad yokken doğrulanamayan bir `.kicad_sch` üretmek yerine `hardware/pano-beyni/blok-diyagrami.md` (Mermaid, gerçek parça numaraları) + BOM ile karşılandı. **Hiçbir geliştirme kartı diyagramda yok** (GK5).
- [x] **Adım 4: `io-tablosu.md`** — her pin: sinyal, yön, gerilim seviyesi, izolasyon sınırı, bağlandığı blok.
- [x] **Adım 5: `docs/16`'yı yaz** + her ekranın görüntüsünü `assets/ekran/` altına al.
- [x] **Adım 6: Commit** — `feat(frontend): alarm konsolu ve EK-II/14 dijital ikiz` + `feat(hw): Pano Beyni sema v1 ve I/O tablosu`

**Kabul:** S1 senaryosu oynatıldığında alarm konsolunda "Neden/Ne yapmalı/Ne kadar acil" dolu bir P3 kartı ve ikizde L2/DSYA-3 noktası sarı.

**🏁 M2 kapısı (15 Eyl 21:00):** `scripts/demo.sh S1` → ekranda P3 uyarı + "tahmini N gün içinde 70 K" + telefonda gerçek WhatsApp mesajı + `demo/sms-log.txt`'de AT kaydı. **Bu, teslimin kalbidir.** Geçilmediyse 16 Eylül sabahı herkes bunu tamamlar, Faz 3 kısalır.

---

## Faz 3 — Entegrasyon, Ölçek ve Firmware (16–17 Eylül · M3 + özellik dondurma)

### TA3 — A: Cihaz simülatörleri + firmware C çekirdeği

**Dosyalar:**
- Oluştur: `sim/mpr53cs_sim.py`, `sim/tvoc2_sim.py`, `sim/Dockerfile` (güncelle)
- Oluştur: `firmware/core/rls.c/.h`, `thermal.c/.h`, `dewpoint.c/.h`, `limits.c/.h`, `modbus_map.c/.h`, `panobeyni.c/.h`
- Oluştur: `firmware/host/main.c`, `firmware/CMakeLists.txt`, `firmware/tests/test_rls.c`, `test_dewpoint.c`
- Oluştur: `firmware/akis-diyagramlari/ana-dongu.md` (mermaid)

**Arayüzler:**
- Üretir: `mpr53cs_sim` ve `tvoc2_sim` RS485/TCP Modbus slave'leri **gerçek register adreslerinde** (MPR-53CS kılavuzu; TVOC-2 PDU 100–149, 222–225, 1300–1306 — rapor §3.5)
- Üretir: `panobeyni-sim` ikilisi — sanal seri port üzerinden Modbus master (cihazları okur) + Modbus slave (bizim haritamızı sunar) + MQTT yayını

- [x] **Adım 1: TVOC-2 simülatörü** — pymodbus slave; fabrika ayarı **ID 248 = haberleşme kapalı** davranışını taklit eder (ID 1–247'ye alınmadan cevap vermez — bu detay sunumda gösterilecek), 19200/8E1; trip sayacı (149), dedektör bitleri (100/101), tarih/saat kodlaması (1970'ten gün; HHMM = MSB saat/LSB dakika), sensör durumu (222/223). Test: `modpoll`/pymodbus istemcisiyle okuma.
- [x] **Adım 2: MPR-53CS simülatörü** — register haritasından faz/nötr akımı, gerilim, THD, cosφ, min/max; `I_primer = ham × 0,001 × CT` (CT = 500) dönüşümü doğru.
- [x] **Adım 3: Firmware çekirdek testini yaz (Unity/CTest)** — `firmware/tests/test_rls.c`: Python tarafındaki `test_k_index` ile **aynı test vektörü** (`data/fixtures/rls_vectors.csv`), C ve Python çıktısı ≤1e-6 farkla aynı. Bu "kenarda ve merkezde aynı algoritma" iddiasının kanıtı.
- [x] **Adım 4: Testi koştur, başarısız gör** — `cmake -S firmware -B firmware/build && cmake --build firmware/build && ctest --test-dir firmware/build` → FAIL.
- [x] **Adım 5: C çekirdeğini yaz** — dinamik bellek yok, float sabit boyutlu durum (nokta başına ~48 bayt), `malloc` yok, standart kütüphane dışı bağımlılık yok. Testi geçir.
- [x] **Adım 6: `firmware/host/main.c`** — `panobeyni-sim`: sanal seri porttan Modbus master döngüsü (1 s), çekirdek algoritmaları, Modbus slave sunumu (`contracts/modbus-map.yaml`'dan üretilen tablo), MQTT yayını, 7 günlük halka tampon (dosya).
- [ ] **Adım 7: (Should) Renode/Wokwi hedefi** — aynı çekirdek bir MCU hedefinde derlenip emülatörde koşar, UART'ı host'un sanal portuna bağlanır. **Zaman kalmazsa atla**, host ikilisi yeterli.
- [x] **Adım 8: `akis-diyagramlari/ana-dongu.md`** — mermaid state diyagramı: boot → selftest → taban öğrenme (7 gün) → normal döngü → olay → son nefes.
- [x] **Adım 9: Commit** — `feat(sim): MPR-53CS ve TVOC-2 Modbus simulatorleri (gercek adresler)` + `feat(fw): tasinabilir C cekirdegi, host ikilisi ve ortak test vektorleri`

**Kabul:** `ctest` yeşil · QModMaster ile `tvoc2_sim`'e bağlanıp PDU 1300 okunuyor · ID 248'de cevap **yok**, 1'e alınınca cevap **var** · `panobeyni-sim` çalışırken MQTT'de telemetri akıyor.

### TB3 — B: Modbus TCP ağ geçidi + yük testi + ölçek kanıtı

**Dosyalar:**
- Oluştur: `backend/app/scada/modbus_tcp.py`, `scada/map_loader.py`, `scada/iec104.py` (Could)
- Oluştur: `loadtest/fleet.py`, `loadtest/README.md`, `deploy/grafana/dashboards/olcek.json`, `dashboards/alarm-kpi.json`
- Oluştur: `scripts/gen_modbus_doc.py`, `docs/03-modbus-haritasi.md` (üretilmiş), `docs/09-olceklenebilirlik.md`, `docs/07b-fmea-yazilim-sistem.md`, `docs/15-guvenlik-kvkk.md`, `docs/17-donanimsiz-dogrulama.md`

- [x] **Adım 1: `map_loader.py`** — `contracts/modbus-map.yaml` → register tablosu (tek kaynak). Test: YAML'daki her blok adresinin çakışmadığını doğrula.
- [x] **Adım 2: Modbus TCP sunucusu** — pymodbus server; FC03/FC04 aynalı, FC06/16 yalnızca `command` bloğunda ve **şifre register'ı doğruysa**; TVOC-2 aynası **salt okunur** (GK6). Test: istemciden okuma + yetkisiz yazmanın reddi.
- [x] **Adım 3: `scripts/gen_modbus_doc.py`** — YAML → `docs/03-modbus-haritasi.md` (ve CSV). Doküman elle yazılmaz (kural 10).
- [x] **Adım 4: Yük testi** — `loadtest/fleet.py`: `panoalgo` üretecini **kütüphane olarak** kullanıp 1.000 sanal panoyu MQTT'ye basar (A'nın kodunu kopyalama, import et). Ölçülecekler: mesaj/s, ingest gecikmesi p50/p95, CPU, RAM, DB büyümesi, uçtan uca alarm gecikmesi.
- [x] **Adım 5: Grafana panoları** — `olcek.json` (mesaj/s, CPU, RAM, p95, DB boyutu), `alarm-kpi.json` (alarm/100 pano/gün, öncelik dağılımı — ISA-18.2 hedefiyle karşılaştırmalı).
- [x] **Adım 6: Ölçüm sonuçlarını `docs/09`'a yaz** — rapor §6.8 tablosunun **ölçülmüş** sütunu; 100 pano ve 1.000 pano için gerçek sayılar + hücresel veri bütçesi.
- [x] **Adım 7: `docs/07b`, `docs/15`, `docs/17`'yi yaz.** `docs/17` Bölüm C'deki beş hamleyi ve "neyi simüle ettik, neyi kanıtladık" tablosunu içerir.
- [x] **Adım 8: (Could) IEC 60870-5-104 slave** — yalnızca Adım 1–7 bittiyse.
- [x] **Adım 9: Commit** — `feat(backend): Modbus TCP ag gecidi + uretilmis harita dokumani` + `test(loadtest): 1000 pano yuk testi ve olcek olcumleri`

**Kabul:** QModMaster `localhost:502`'den `conn_temp` bloğunu okuyor ve değerler arayüzle aynı · 1.000 pano testinde p95 < 2 s, CPU/RAM grafikleri kayıtlı · `docs/03` betikle yeniden üretilebiliyor.

### TC3 — C: Trend/korelasyon, kara kutu, cihaz sağlığı + donanım dokümantasyonu

**Dosyalar:**
- Oluştur: `frontend/src/pages/TrendKorelasyon.tsx`, `pages/OlayAnalizi.tsx`, `pages/CihazSagligi.tsx`, `pages/BolgeHaritasi.tsx`
- Oluştur: `hardware/yerlesim/ek2-14-yerlesim.svg`, `hardware/mekanik/din-kutu.scad` (+ STL), `hardware/pano-beyni/bom.csv`
- Oluştur: `docs/07-fmea-donanim-saha.md`, `docs/08-kurulum-proseduru.md`, `docs/10-bom-maliyet-roi.md`, `docs/11-standartlar-uyum.md`, `docs/13-donanim-tasarimi.md`, `docs/01-problem-analizi.md`

- [x] **Adım 1: Trend/korelasyon ekranı** — **I²–ΔT dağılım grafiği** (sağlıklı vs gevşek bağlantı iki farklı eğim — bu grafik sunumun en güçlü görseli), K trendi, çiy noktası marjı zaman serisi.
- [x] **Adım 2: Olay analizi (kara kutu)** — ark tripinde dedektör konumu + öncesindeki 72 saatin sinyalleri tek zaman çizelgesinde.
- [x] **Adım 3: Cihaz sağlığı + bölge haritası** — ~~düğüm başına RSSI/yedek enerji/son görülme/firmware; haritada trafo merkezleri risk rengiyle~~ **Sapma (bkz. Günlük Kayıt):** toplu düğüm-sağlığı ucu sözleşmede yok (öneri: `contracts/changes/2026-09-14-fleet-health-bulk.md`); Cihaz Sağlığı görünen panoları tek tek çeker, Bölge Haritası il/ilçe yerine dağıtım şirketine göre gruplar (gerçek olmayan bir coğrafi kırılım göstermemek için). Offline, harita karosu yok (GK4).
- [x] **Adım 4: Yerleşim çizimi** — `ek2-14-yerlesim.svg`: kontrolcü üst bölmede (şartname 2.2.8.1.iv atıflı), termal dizi saydam kapağın **iç** tarafında, nokta düğümleri bara/pabuç eklerinde, ortam düğümleri alt/üst, reed kapıda; her öğenin yanında ölçü ve baradan uzaklık.
- [x] **Adım 5: Mekanik + BOM** — ~~DIN kutu 3D (OpenSCAD → STL)~~ **Sapma:** `din-kutu.scad` yazıldı (V-0 malzeme notu), ama bu ortamda `openscad` kurulu olmadığı için STL üretilemedi (STATUS.md karar #4); `bom.csv`: parça, üretici kodu, adet, birim fiyat (adet 1) ve (adet 1.000), tedarik notu — tamamlandı.
- [x] **Adım 6: Dokümanları yaz** — `07` (FMEA donanım/saha satırları), `08` (kurulum: 5 güvenlik kuralı, ≤45 dk, 2 kişi, AT sekonderi açık bırakılmaz uyarısı), `10` (SKU'lar + BOM + parametrik ROI tablosu), `11` (standart → nerede karşılandı), `13` (blok diyagram, güç bütçesi, manyetik alan ve clearance/creepage hesapları), `01` (jüri için 3 sayfalık problem özeti).
- [x] **Adım 7: Commit** — `feat(frontend): trend, kara kutu, cihaz sagligi ve bolge haritasi` + `docs(hw): yerlesim, BOM, FMEA, kurulum ve standart dokumanlari`

**Kabul:** 9 ekranın 7'si çalışıyor (mobil PWA ve devreye alma sihirbazı Won't) · `hardware/` altında şema PDF + I/O + BOM + yerleşim + STL var.

**🏁 M3 kapısı (17 Eyl 21:00):** S0–S6 senaryoları betikle oynatılabiliyor · QModMaster bizim haritayı okuyor · 1.000 pano grafikleri kayıtlı · firmware testleri yeşil.

**🧊 17 Eylül 23:59 — ÖZELLİK DONDURMA.** Bu saatten sonra yeni özellik yok. Çalışmayan her şey ya kesilir ya "yol haritası" olarak sunulur.

---

## Faz 4 — Kanıt ve Doküman (18 Eylül · M4)

> Kod yazılmaz; yazılan = kanıt. Herkes kendi dokümanını bitirir, sonra **çapraz okuma** yapılır (A → B'nin dokümanlarını, B → C'nin, C → A'nın okur; bulduğu hatayı sahibine bildirir, kendisi düzeltmez — kural 2).

- [x] **T4.1 (A): `docs/12-dogrulama-sonuclari.md`** — 10 senaryo × metrik tablosu: recall, precision, **öne alma süresi (saat)**, yanlış alarm/100 pano/gün. Ve **sabit 70 K eşiği vs L0+L1+L2+L3 karşılaştırması**: aynı veride kaç saat önce, kaç yanlış alarmla. Her sayı `scripts/validate.py` ile yeniden üretilebilir olmalı.
- [x] **T4.2 (A): Doğrulama betiğini tekrarlanabilir yap** — `python scripts/validate.py --out docs/12-dogrulama-sonuclari.md` aynı sayıları üretiyor (seed'li).
- [x] **T4.3 (B): `docs/02-mimari.md`** — mermaid bileşen + veri akışı + sıralama diyagramı (sensör → kenar → broker → ingest → risk → alarm → SMS, gecikme damgalarıyla).
- [ ] **T4.4 (B): Temiz makine testi** — sıfırdan `git clone` + `cp deploy/.env.example deploy/.env` + `docker compose up` → 5 dakikada çalışan sistem. Çalışmayan her adım README'ye yazılmaz, **düzeltilir**.
- [x] **T4.5 (C): `README.md`'yi bitir** — amaç, mimari görseli, tek komutla kurulum, demo senaryoları, **"beklenen 7 teknik çıktı → dosya/klasör" eşleme tablosu** (rapor §11 teslim listesi), ekip, gizlilik notu.
- [x] **T4.6 (C): Ekran görüntüleri** — her ekranın 2 hali (normal/alarm) `assets/ekran/` altına; `docs/16`'ya gömülü. (Filo/Alarm konsolu/Bölge gibi filo-geneli ekranlarda tek "normal" hali anlamlı olmadığından yalnızca dolu hal var, `docs/16` §5'te not düşüldü.)
- [x] **T4.7 (hep): Sır taraması** — C'nin payı yapıldı: `git log --all -p | grep -iE "token|password|\+90|api[_-]?key"` çıktısı gözden geçirildi, tamamı test/placeholder telefon numarası veya `password`/`token` alan adı (kural 10'daki sabitler gibi kod içi tanımlayıcı); gerçek sır yok, `.env` commit edilmemiş. **Son commit'ten önce tekrar koşulmalı** (yeni commit'ler eklendikçe).
- [ ] **T4.8 (hep): Gereksinim kapsama kontrolü** — aşağıdaki R1–R17 tablosunu gözden geçir, karşılanmayan varsa Faz 5'te sunum/doküman ile kapat.

**M4 kapısı:** Temiz makinede tek komutla demo + 17 doküman + doğrulama tablosu sayılarla dolu.

---

## Faz 5 — Sunum ve Video (19 Eylül · M5)

- [x] **T5.1 (C): Demo betikleri deterministik** — ~~`demo/senaryo/s0.sh … s8.sh`, her biri seed'li ve aynı sonucu üretiyor~~ **Sapma (bkz. Günlük Kayıt):** betikler yazıldı ve `bash -n` ile sözdizimi doğrulandı; `s7`/`s8` gerçek araçlara (`loadtest/fleet.py`, Modbus/IEC104) karşı çalışır durumda, `s0`–`s6` A'nın simülatörü (`sim/panosim.py`, `libs/panoalgo/`) bu depoda henüz yokken çalıştırılamıyor — çalıştırılınca bunu açıkça söyleyip örnek-veri alternatifini gösteriyorlar (sessiz başarısızlık yok).
- [x] **T5.2 (C): Sunum destesi (≈12 dk iskelet, rapor §8.2)** — problem ve saha hikâyesi (30 s) → dökümanlardan çıkardığımız 5 kritik içgörü (1 dk) → mimari (1,5 dk) → demo (7 dk) → ölçek + maliyet/ROI + kurulum (1,5 dk) → PoC teklifi (30 s). **Donanımsızlığı slayt 3'te açıkça ve güçlü biçimde konumlandır** (Bölüm C). → `demo/sunum/sunum-taslagi.md`.
- [ ] **T5.3 (hep): Video çekimi** — 3–5 dk kurgu: S0 → S1 → S3 → S4 → S5 + S7/S8'den kısa kesitler. **2 tam çekim.** Komitenin gizli dökümanları kadrajda görünmeyecek (§12.1).
- [ ] **T5.4 (hep): 2 prova** — biri süreli, biri soru-cevaplı. Rapor §13'teki 17 jüri sorusunun cevaplarını paylaşın: teknik fizik soruları A, entegrasyon/ölçek/güvenlik B, saha/maliyet/UX C.
- [ ] **T5.5 (B): Yedek plan** — internet yokken demo çalışıyor (WhatsApp düşerse sanal modem kaydı ekranda); canlı demo patlarsa video hazır.

**M5 kapısı:** Video kurgulanmış, sunum bitmiş, iki prova yapılmış.

---

## Faz 6 — Teslim (20 Eylül · hedef 18:00 · M6)

Rapor §11'deki teslim kontrol listesi, donanımsız moda uyarlanmış:

- [ ] Teslim platformu ve formatı teyit edildi (Faz 0'da sorulmuştu)
- [ ] Repo erişimi **jüri gözüyle** test edildi (gizli pencere / başka hesap)
- [ ] Public link isteniyorsa: gizli dökümanları **içermeyen temiz repo** (dosya silmek geçmişten silmez)
- [ ] README: amaç, mimari, tek komutla kurulum, demo senaryoları, ekip
- [ ] README'de 7 teknik çıktı → dosya eşleme tablosu
- [ ] Donanım dokümantasyonu: şema PDF, I/O tablosu, blok diyagram, BOM, yerleşim, mekanik
- [ ] Firmware kaynak kodu + akış diyagramı; frontend kaynak kodu + ekran görüntüleri
- [ ] Modbus harita dokümanı, mimari, FMEA (2 dosya), ölçek + yük testi, maliyet/ROI
- [ ] `docs/17-donanimsiz-dogrulama.md` — neyin simülasyon, neyin kanıt olduğu açık
- [ ] Demo videosu (3–5 dk) linki test edildi
- [ ] Sunum dosyası (+ PDF kopyası)
- [ ] `.env`, token, telefon numaraları repodan temiz
- [ ] **18:00 teslim.** 23:59'a kadar yalnızca acil tampon.

---

## Bölüm E — Gereksinim kapsama kontrolü (öz-denetim)

Rapor §2.1'deki zorunlu gereksinimlerin her biri bir göreve bağlı mı?

| ID | Gereksinim | Karşılandığı görev | Not |
|---|---|---|---|
| R1 | Uçtan uca çalışan prototip | TA1–TA3, TB1–TB3, TC1–TC3, M1/M2/M3 | Fiziksel maket yerine dijital ikiz + çalışan yazılım (GK3, `docs/17`) |
| R2 | Kabin içi fiziksel modül + EK-II/14 çizimleri | TC3 Adım 4, 5 | `hardware/yerlesim/`, `hardware/mekanik/` |
| R3 | Elektronik tasarım dokümantasyonu | TC2 Adım 3–4, TC3 Adım 5–6 | KiCad şema + I/O + BOM + `docs/13` |
| R4 | Yazılım mimarisi + MCU kodu + akış diyagramı + frontend kodu | TA3 Adım 5–8, TB3, TC1–TC3, T4.3 | `firmware/`, `docs/02`, `frontend/` |
| R5 | Monitoring (merkezde toplama ve izleme) | TB1, TC1, TB3 Adım 5 | API + arayüz + Grafana |
| R6 | SCADA entegrasyonu – Modbus haritalama | T0.4 Adım 1, TB3 Adım 1–3, TA3 | `contracts/modbus-map.yaml` → firmware + TCP sunucu + doküman |
| R7 | On-premise, public cloud yok | T0.5, T4.4 | Tek istisna WhatsApp (GK4) |
| R8 | SMS/WhatsApp alarm mekanizması | TB2 Adım 5–7 | Gerçek WhatsApp + sanal modemle gerçek SMS sürücüsü |
| R9 | ≥100 modül + kaynak değerlendirmesi | TB3 Adım 4–6 | 1.000 pano ölçülmüş |
| R10 | Pahalı işlemci/dev board bağımlılığı yok | GK5, TC2 Adım 3, TA3 Adım 5 | Şemada dev board yok; çekirdek `malloc`'suz C |
| R11 | Kablo kalabalığı yok, kablosuz, bakımsız | TC3 Adım 4, `docs/13` | Enerji toplayan düğüm tasarımı |
| R12 | Mission-critical: tüm hatalar/etkiler | TC3 Adım 6 (`docs/07`), TB3 Adım 7 (`docs/07b`) | 14 satırlık FMEA iki dosyada |
| R13 | Sıcaklık, manyetik alan gibi olumsuz koşullar | TC3 Adım 6 (`docs/13`) | B = μ₀I/2πr hesabı, ≥20–30 cm |
| R14 | Farklı kaynaklardan sapma tespiti + erken uyarı | TA2 tamamı | L-1…L4, `docs/05`, `docs/12` |
| R15 | Merkezi operasyonun takibi | TB2, TC2 Adım 1 | ISA-18.2 konsol, eskalasyon |
| R16 | Ölçeklenebilir, maliyet sürdürülebilir | TC3 Adım 5–6 (`docs/10`), TB3 (`docs/09`) | SKU + BOM + ROI |
| R17 | Mevcut saha/SCADA yapılarıyla çalışabilirlik | TA3 Adım 1–2, TB3 Adım 2 | Tek master senaryoları A/B/C `docs/02`'de |

**Kapsanmayanlar (bilinçli):** PD donanımı, mobil PWA, QR devreye alma, IEC 104 (Could) — sunumda yol haritası olarak anlatılır.

---

## Bölüm F — Riskler ve kesme kararları

| Risk | Belirti | Kesme kararı (kim, ne zaman) |
|---|---|---|
| M1 kapısı kaçtı | 13 Eyl 21:00'de uçtan uca akış yok | 14 Eyl sabahı **üçü birlikte** yalnızca zinciri tamamlar; TA2/TB2/TC2 yarım gün kayar |
| M2 kapısı kaçtı | 15 Eyl 21:00'de telefona mesaj gitmiyor | WhatsApp'ı bırak, sanal modem kaydı + ekran bildirimi ile devam; 16 Eyl'de tekrar dene |
| A yük altında | Firmware C çekirdeği 17 Eyl'e sarkıyor | Renode hedefi (Should) kesilir; host ikilisi + akış diyagramı yeterli. Gerekirse B, `map_loader`'ı firmware için de üretir |
| C yük altında | Ekranlar + dokümanlar + video aynı güne sıkışıyor | `BolgeHaritasi` ve `CihazSagligi` ekranları Could'a düşer; `docs/01` raporun kopyası olur |
| Sözleşme değişikliği baskısı | "Şu alanı eklemem lazım" | `contracts/changes/` + 3 onay. Faz 3'ten sonra **sözleşme değişmez**, adaptör yazılır |
| Çakışma çıktı | Rebase'de conflict | Dosya sahibinin sürümü kazanır; diğer kişi değişikliğini geri alır ve sahibinden rica eder |
| Yorgunluk | 19–20 Eyl'e iş kaldı | 17 Eyl dondurmaya sadakat tek çare. 19–20 Eyl'de kod yazılmaz |
| Gizli döküman sızması | Video/ekran görüntüsünde PDF sayfası | Yalnızca kendi SVG/çizimlerimiz; Faz 5'te kadraj kontrolü |

---

## Bölüm G — Atama ve Günlük Kayıt

**Atama (Faz 0 T0.6 Adım 2'de doldurulacak):**

- **Kişi A (Fizik, Kenar, Algoritma):** Tuna
- **Kişi B (Platform, Entegrasyon, Ölçek):** Ahmet
- **Kişi C (Arayüz, Donanım Tasarımı, Teslim):** Berke

GitHub handle'ları: `@_____` (A), `@ahmetkrkyn0` (B), `@_____` (C) → `CODEOWNERS`'a yazılacak.

**Günlük Kayıt** (her akşam 21:00'de, kulvar sahibi kendi satırını ekler — dosya sonuna ekleme yapıldığı için çakışma olmaz):

| Tarih | Kişi | Biten | Bloke | Kesilen |
|---|---|---|---|---|
| 12 Eyl | — | Faz 0 iskeleti: git hijyeni, 39 dizin, CODEOWNERS, 5 sözleşme (donduruldu), üç parçalı compose, hello-world servisleri, README iskeleti, `check_contracts.py` | Docker daemon kapalı → yığının `up` ile çalıştığı doğrulanmadı | — |
| 12 Eyl | B (Ahmet) | TB1 kodu `b/faz1-ingest`'te: MQTT ingest (şema/topic/ts denetimi, karantina, toplu COPY), `panel_latest`, panel API + WS; 54 test (+8 DB testi yerel PostgreSQL 16'da yeşil); Docker'sız duman testi sim → MQTT → backend → DB → API/WS geçti | BIOS'ta Intel VT-x kapalı → Docker motoru başlamıyor; TB1 Adım 7 (`docker compose up`, TimescaleDB) bekliyor | — |
| 12 Eyl (gece) | B (Ahmet) | VT-x açıldı → `docker compose up`: 6 servis ayakta (backend/timescaledb/mosquitto `healthy`); uçtan uca sim → mosquitto → ingest → TimescaleDB 2.30 hypertable → API/WS doğrulandı (TB1 Adım 7 ✅); karantina gerçek broker üzerinden doğrulandı; 8 DB testi TimescaleDB'de yeşil (63/63). Flaky `test_stream` kök nedeni bulundu (WS teardown'da `asyncio.gather` anyio iptalini etiketsiz `CancelledError` ile değiştiriyordu) → anyio görev grubuna geçildi + yarış testi | — | — |
| 13 Eyl | | | | |
| 13 Eyl | B (Ahmet) | TB2 `b/alarm-manager`'da (TB1 dalının üstünde, 10 commit): ISA-18.2 alarm yöneticisi (histerezis, P1 mandallama, raf, bakım modu, kök neden gruplama, eskalasyon 5/15/30 dk), risk motoru (kenar alarmlarına Neden/Ne yapmalı/Ne kadar acil), alarm API (liste/ack/shelve + WS + `active_alarms`), merkezde `ALM-COMMS-LOST`, kalıcılık + denetim izi (`003_alarms.sql`), SMS PDU kodlayıcı + üretim modem sürücüsü + sanal GSM modem (compose `gsm-modem`), WhatsApp Cloud API istemcisi, bildirim ağ geçidi (çift yönlü SMS onayı), `docs/06` (tablolar sözleşmeden üretilir). 215 test (152 TB2); 107 mutasyonun tamamı testlerce yakalandı. Canlı yığın: P1/P2 → iki alıcıya SMS, alarmdan modemin kabulüne 0,29 sn (PDU dökümü), kayıtlı numaradan "1 5" onayladı / kayıtsız numara yok sayıldı, sessiz pano 5,1 dk'da COMMS-LOST, onaysız P1 5. dk'da iki alıcıya arama, 15. dk'da üst amire eskalasyon SMS'i (seviye 2), yeniden başlatmada alarmlar aynı kimlikle geri geldi | TB2 Adım 4: `panoalgo` yok → merkez dedektör kancası hazır, şimdilik kenarın `alarms` alanı kullanılıyor (A) · WhatsApp'ın gerçek telefona gitmesi için Meta test numarası + token + doğrulanmış alıcı gerekiyor (Ahmet) · `b/faz1-ingest` 13:00 penceresinde main'e alınmadı · `/panels/{id}/series`, `/events/{id}/blackbox`, `/fleet/kpi` hiçbir göreve atanmamış (TC3 bekliyor) | Plandan sapma: SMS kaydı `demo/sms-log.txt` yerine git dışı `deploy/runtime/sms-log.txt` (PDU numara taşır, GK9); PTY yerine TCP (`socket://`, konteynerler arası PTY yok; sahadaki karşılığı ser2net). Karar gerekiyor: M2 metni "P3 → telefon" diyor, sözleşmede P3'ün SMS/WhatsApp'ı kapalı → S1 telefonu P2'de (K/K₀ > 1,6) çaldırır |
| 13 Eyl (akşam) | B (Ahmet) | TB3 Adım 1–6 + 9 ve T4.3 `ahmet/backend`'de: **Modbus TCP ağ geçidi** (kendi asyncio sunucusu; pymodbus 3.7.4 sunucusu her bağlantıda `0.0.0.0`'da port sızdırıyordu), her pano bir birim ve aynı harita, varsayılan salt okunur, şifreli komut bloğu, **GK6: TVOC-2 aynasına şifreyle bile yazma yok**, IP listesi, 3 yanlış şifrede kilit, bakım modu/test alarmı MQTT `cmd` ile kenara; `docs/03` + CSV sözleşmeden üretiliyor; canlı yığında 3 panoda Modbus = API × 10. Sözleşmedeki atanmamış `/panels/{id}/series`, `/events/{id}/blackbox`, `/fleet/kpi` uçları yazıldı (C'nin TC3'ü için). **Yük testi 100 → 10.000 pano:** 1.000 panoda görünme p95 657 ms, kayıp 0, alarm → SMS p95 606 ms, backend 0,16 çekirdek; 5.000 panoya kadar p95 < 1 s, 10.000'de doyma (darboğaz ölçüldü: mesaj başına 615 µs'in 501 µs'i şema doğrulaması). TimescaleDB sıkıştırması **48×** ölçüldü ve şemaya eklendi (`005_compression.sql`). Grafana "Ölçek" + "Alarm KPI" panoları (üretilmiş, her sorgu DB'de sınanıyor). `docs/02`, `07b`, `09`, `15`. Test: `TEST_DB_DSN` ile 507 geçti; mutasyon: kodlayıcı 28/28, ağ geçidi 35/35, sunucu 19/19, analiz uçları 20/20. Ölçerken bulunup düzeltilen: SCADA birim eşlemesi O(n² log n) (10.000 panoda ingest 5 s kilit), DB `/dev/shm` 64 MB (VACUUM düştü → 1 GB) | TB2 Adım 4 ve yük testinin `panoalgo` kaynağı hâlâ A'nın paketini bekliyor · `docs/17` A (firmware, simülatörler) ve C (donanım) kanıtlarını bekliyor · A/C'nin yerel veritabanlarına `005_compression.sql` elle uygulanmalı (komut dosyada) ve `docker compose up -d timescaledb` ile shm ayarı alınmalı | Plandan sapma: pymodbus sunucusu yerine kendi sunucu (docs/03 §13); IEC 104 (Could) yapılmadı. **Karar gerekiyor (A ile):** 10 s JSON raporlama 1.000 pano için ilk yıl ~1,2 TB disk ve pano başına ~456 MB/ay hücresel veri; "normalde 60 s, olayda anında" ~6 kat düşürür (docs/09 §5–6). Demo'da broker anonim 1883 ve API'de kimlik doğrulama yok: bilinçli, docs/15 §5'te açık |
| 13–14 Eyl (gece) | B (Ahmet) | TB3 Adım 8 (Could) `ahmet/backend`'de: **IEC 60870-5-104 kontrollü istasyon** (TCP 2404, kendi asyncio sunucusu): genel sorgulama, yayın adresi, saat senkronu, ölü bantlı ve zaman etiketli kendiliğinden gönderim, t1/t2/t3 ve k/w akış denetimi; **salt okunur** (kontrol komutları COT 44 ile reddedilir, GK6). Modbus ile aynı kodlayıcı ve birim eşlemesi (ortak adres = birim, IOA = 1000 + PDU); `docs/04` tabloları koddan üretiliyor. Canlı yığında baytları elle kuran bağımsız istemciyle IEC 104 = API (87 kontrol) = Modbus (139 adres), **0 fark**. İlk canlı koşu gerçek bir uyumsuzluk yakaladı: yayın sorgusuna tek bir `0xFFFF` ACTCON/ACTTERM dönülüyordu (standart 7.2.4: her istasyon kendi adresiyle cevaplar) → önce test, sonra düzeltme. Test: `TEST_DB_DSN` ile 580 geçti; mutasyon: sunucu 37/37, kodek 12/12, nokta planı 9/9. `docs/02`, `15`, `17` güncellendi | B'nin kalan işleri başkasına bağlı: TB2 Adım 4 `panoalgo` (A), T4.4 temiz makine testi birleşmeden sonra | Bilinen sınır: kendiliğinden gönderimin zaman etiketi merkezin değişikliği gördüğü an, kenarın ölçüm anı değil (docs/04 §4). Demo'da 2404 düz TCP; sahada SCADA ön-ucunun /32 adresi + IEC 62351-3 (TLS) veya VPN (docs/15) |
| 14 Eyl | C (Berke) | `berke/frontend` dalında: **TC1** (önceki oturumda commit edildi, log unutulmuş — burada telafi edildi): Vite+React+TS iskeleti, "RAL 7035" tema yönü (3 denenen yön arasından, `frontend/sketches/`), Filo listesi (14 günlük logaritmik "sınıra kalan süre" ekseni) + Pano detay (EK-II/14 on gorunus dijital ikizi, faz karşılaştırma), WebSocket akışı + geri çekilmeli yeniden bağlanma, örnek-veri modu (`npm run dev:mock`), 60 birim testi. **Entegrasyon:** `int/pull-ahmet-backend` dalı açılıp `origin/ahmet/backend` (insights uçları: series/blackbox/fleet-kpi + scada + docs) çakışmasız merge edildi, `berke/frontend`'e geri alındı. **TC2:** Alarm konsolu (`/alarmlar`, onay/raf/yorum/eskalasyon), dijital ikizde nokta tıklanınca gerçek zaman serisi trendi (yeni `GET .../series` istemcisi), `assets/ek2-14-pano.svg`, `hardware/pano-beyni/` (blok diyagramı + I/O tablosu + BOM), `docs/16`. **TC3:** Trend/korelasyon (I²–ΔT dağılımı — aynı bağlantının ilk/son 7 gününü karşılaştırıp iki farklı eğim gösteriyor, gevşek bağlantı senaryosu için ısıl model önce sadece K/K₀ alanında rampa idi, ΔT=K·I² olarak fiziksel tutarlı hale getirildi), Olay analizi/kara kutu (yeni ark tripi senaryosu + zaman çizelgesi), Cihaz sağlığı, Bölge haritası, `hardware/yerlesim/ek2-14-yerlesim.svg`, `hardware/mekanik/din-kutu.scad`, `docs/01/07/08/10/11/13`. 9 ekranın 7'si çalışıyor. Toplam 68 birim testi, `tsc`/`vitest`/`npm run build` yeşil, tüm yeni ekranlar tarayıcıda (masaüstü + 400 px mobil) görsel doğrulandı, konsol hatasız | Bu makinede `openscad` ve `kicad` kurulu değil, internet yok → STL üretilemedi, `.kicad_sch` bilinçli olarak üretilmedi (dürüstlük kuralı, bkz. `hardware/pano-beyni/README.md`); bu makinede global `starlette` sürümü `fastapi==0.115.*` ile uyumsuz olduğu için backend testleri toplanamıyor (main'de de var, B'ye iletilmeli) | KiCad şeması yerine blok diyagramı + I/O tablosu + BOM (STATUS.md karar #1); Bölge haritası il/ilçe yerine dağıtım şirketi bazlı, Cihaz sağlığı toplu uç yerine pano-başına istekle (STATUS.md karar #2–3, `contracts/changes/2026-09-14-fleet-health-bulk.md` önerisi açıldı, 3 onay bekliyor) |
| 14 Eyl | C (Berke) | Faz 4/5: kök `README.md` bitirildi (7-çıktı tablosu, ekip, hızlı başlangıç); `assets/ekran/`'a 7 ekranın ekran görüntüsü alındı (`npm run dev:mock`, masaüstü) ve `docs/16` §5'e gömüldü; `demo/senaryo/_ortak.sh` + `s0.sh`…`s8.sh` yazıldı (`s7`/`s8` gerçek araçlara karşı çalışıyor — `loadtest/fleet.py`, Modbus/IEC104 — `s0`–`s6` A'nın simülatörünü bekliyor, çalıştırılınca bunu açıkça söylüyor); `demo/sunum/sunum-taslagi.md` (rapor §8.2 iskeleti, donanımsızlık slayt 3'te güçlü konumlandırıldı); T4.7 sır taraması (C'nin payı) temiz bulundu | — | **Ekip riski, öneri seçilerek not düşüldü:** Bu tarih itibarıyla A kulvarı (`libs/panoalgo/`, `firmware/`, `sim/panosim.py`, `mpr53cs_sim.py`, `tvoc2_sim.py`, `docs/05`, `docs/12`) depoda hâlâ yok (`sim/` yalnızca yer tutucu `hello_publisher.py` içeriyor). B ve C tamamlandı, örnek veriyle uçtan uca çalışıyor; gerçek yığında "uçtan uca" ve S0–S6 demo senaryoları A'nın işine bağlı kilitli kaldı. Özellik dondurmaya (17 Eylül 23:59) 3 gün kaldı — Bölüm F'deki M1/M2 kapısı kaçırma senaryosu şu an M3 için de geçerli olabilir; ekibin bugün A'nın durumunu netleştirmesi önerilir. |
| 14 Eyl | A (Tuna) | TA1 `tuna/veri-ureteci`'nde: `libs/panoalgo` paketi kuruldu (physics: Magnus ciy noktasi + yogusma marji; profiles: 168 kutulu saat-of-hafta konut/ticari/karma profil + mevsim katsayisi + AR(1) gurultu; generator: ayrik isil model dT[k+1]=a*dT[k]+(1-a)*K*I^2, ortam sinusu, ters iliskili nem, faz dengesizligi %2-15, notr akimi dengesizlik+3.harmonik, TVOC-2 sakin durumu) ve `sim/panosim.py` MQTT yayincisi. Sozlesmeden okuma (kural 10): nokta adlari modbus-map, esikler alarm-codes, pano_id deseni + topic/QoS/retain telemetri semasi. 146 test; 27/27 mutasyon yakalandi. Canli yigin: 3 pano -> mosquitto -> ingest -> TimescaleDB -> API, received 9 / rejected 0 / dropped 0, karantina bos, 189 etiket/mesaj. sim imaji artik repo kokunden derleniyor (panoalgo imaja kuruluyor), Faz 0'in hello_publisher.py'si kaldirildi | — | Karar gerekiyor: yayinlanan `ts` SIMULE zamandir, --speed 60 ile duvar saatinin onune gecer (Grafana/arayuz zaman ekseni etkilenir); duvar saatiyle hizali demo icin --speed 1. TA2'ye bulgu: ALM-DQ-BELOW-AMBIENT kurali olu bant istiyor (hafif yuklu GIRIS_N fiziksel olarak ortamda oturur, sigma 0,2 K gurultu ile dt_c ara ara negatife duser) |
| 14 Eyl (aksam) | A (Tuna) | TA2 TAMAM + TA3 kismen. Tespit katmanlari: `detect.py` (RLS K indeksi, sinira kalan sure, faz karsilastirmasi), `quality.py` (L-1), `limits.py` (L0/L1 esik karari), `fusion.py` (hipotez fuzyonu), `edge.py` (kenar boru hatti), `central.py` (B'nin CentralDetector kancasina takilan adaptor), `scenarios.py` (S0-S9 + 10 fixture), `validate.py` + `scripts/validate.py`. Dokumanlar: docs/05, docs/12 (betikle uretilir), docs/14. C firmware cekirdegi: `firmware/core/rls.c|thermal.c|dewpoint.c`, CMake/CTest, akis diyagramlari. OLCUMLER: 300 Python testi + 3 C testi yesil; 27/27 Python ve 11/11 C mutasyonu yakalandi; S1'de K/K0 1.6 esigi sabit 70 K esiginden 209 SAAT once asiliyor (kriter 48 saatti); tum senaryolarda recall 1.00, yasakli alarm yok, S0'da yanlis alarm 71,4/100 pano/gun (sozlesme kabul siniri 150); C ile Python farki K 1.36e-8 / tau 1.42e-8 (PLAN esigi 1e-6) | TA3 Adim 1-2 (TVOC-2 ve MPR-53CS simulatorleri) ve Adim 6 (host ikilisi) suruyor | Adim 7 (Renode/Wokwi) Should — atlanacak. Bellek butcesi PLAN'daki ~48 B yerine 320 B/nokta: kalici uyarim penceresi C ile Python'un ayni `excited` kararini vermesi icin gerekli (gerekce firmware/akis-diyagramlari/ana-dongu.md). B'ye: `scripts/validate.py` CODEOWNERS'ta senin dizininde ama PLAN T4.2 A'ya atiyor — ince bir giris dosyasi, itirazin varsa 13:00'te konusalim |
| 14 Eyl (gece) | A (Tuna) | TA3 TAMAM (Adim 7 haric — Should, atlandi). Cihaz simulatorleri: `sim/tvoc2_sim.py` ve `sim/mpr53cs_sim.py`, register mantigi `panoalgo/devices.py` icinde testli. Firmware: `modbus_map.c` (GK6 yazma korumasi), `limits.c`, `host/main.c` (panobeyni-sim). Modbus harita basligi sozlesmeden URETILIYOR (`panoalgo/genmap.py`). CANLI DOGRULAMA (gercek pymodbus istemcisi): TVOC-2 ID 248'de hicbir isteme cevap yok, ID 10'a alininca PDU 1300 = 0; ark tripi sonrasi 149 = 1, tarih/saat kilavuz kodlamasiyla dogru; bos trip slotu 0xFFFF. MPR-53CS: CT 0x8001 = 500, L1 ham 4618 -> 2309,0 A (rapor 15.1 ornegi). C/PYTHON ESITLIGI: sentetik vektorde fark K 1,36e-8 / tau 1,42e-8 (esik 1e-6); GERCEK uretec verisinde 25 noktada K/K0 farki 0,0004 (register kuantizasyonunun kendisi). 331 Python + 5 C testi yesil. | — | TA3 Adim 7 (Renode/Wokwi) atlandi: Should, host ikilisi yeterli. Adim 6'nin tasima kismi (seri Modbus master, MQTT) C yerine Python katmaninda — gerekce firmware/host/main.c basinda. Yol boyunca bulunan ve duzeltilen dort sapma: lam ornekleme periyoduna tasinmiyordu, taban medyani iki tarafta farkli hesaplaniyordu, bir orneklik kayma vardi ve URETECIN GERCEK K'si kestirim yokken yukte kaliyordu (kenar olcemeyecegi bir dogruyu yayinliyordu). B'ye hatirlatma: contracts/changes/2026-09-14-eksik-esikler.md hala 3 onay bekliyor |
