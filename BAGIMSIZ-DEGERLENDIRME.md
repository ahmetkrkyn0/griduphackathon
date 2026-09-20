# Grid Up Hackathon 2026 — Bağımsız Değerlendirme

**Değerlendirilen:** Pano/Hücre İçi Anomali Erken Uyarı ve Kestirimci Bakım Sistemi (GridUp)
**Depo durumu:** dal `tuna/polish`, HEAD `467e99c`, 207 commit, 534 izlenen dosya
**Değerlendirme tarihi:** 20 Eylül 2026, 15:20–17:00 (TSİ)

> ## ⚠ BAĞIMSIZLIK NOTU — SONRADAN EKLENDİ
>
> **Bu rapor 20 Eylül 2026, 17:00'da bağımsız olarak tamamlandı ve teslim edildi.**
> Sonrasında proje ekibi, raporda listelenen YANILTICI bulguların düzeltilmesini benden
> istedi ve **düzeltmeleri ben uyguladım** (aşağıdaki liste). Dolayısıyla **bu tarihten
> sonraki depo durumu için artık bağımsız değerlendirici değilim.** Rapordaki puanlar,
> bulgular ve ölçümler **düzeltme öncesi** depoya (`HEAD = 467e99c`) aittir ve
> değiştirilmemiştir. Jüri, aşağıdaki düzeltmeleri **bağımsız olarak doğrulanmamış**
> saymalıdır.
>
> Uyguladığım düzeltmeler (hepsi §8'deki bulgulara karşılık gelir):
> `loadtest/fleet.py` +`import os` (Y2 — araç artık koşuyor, doğruladım) ·
> `docs/09` §4.1b makine bloğu cümlesi gerçeğe göre yeniden yazıldı (Y1) ·
> `docs/05` §7 ve `firmware/akis-diyagramlari/ana-dongu.md` akım kuralı boşluğu açıkça
> yazıldı (Y3) · `docs/01`, `docs/14`, `HACKATHON_ANALIZ_RAPORU.md` TVOC-2 açma süresi ve
> Paschen gerekçesi düzeltildi (Y4, Y5) · `README.md` yuvarlama, 657 ms eseri ve F-36
> bayatlığı notlandı · `docs/09` başlığı "git dışı" → gerçek durum ·
> `demo/senaryo/s4.sh` ve `sim/panosim.py` yanıltıcı konsol/metin ifadeleri düzeltildi.
>
> **Hiçbir puan değiştirilmedi.** Düzeltmelerin puana etkisi §5.3'ün altındaki
> senaryo hesabında tahmin olarak verilmiştir; gerçekleşmesi **yeni ve bağımsız** bir
> değerlendirme gerektirir.
>
> ### Ek not — `origin/main` birleştirildikten sonra (20 Eylül, 17:40)
>
> Değerlendirme `tuna/polish` dalında yapıldı. Sonradan `origin/main` (11 commit) bu dala
> alındı ve **K6'nın en ağır bulgusunun dayanağı değişti:**
>
> - **`976ff06` 13 Eylül yük koşumlarının 7 eserini klona almış.** Yani §3.3'te
>   `ÜRETİLEMEZ` yazdığım **657 ms artık bir eserde duruyor**:
>   `loadtest/results/20260913T151550-1000p.json` → 1.000 pano / 7 nokta / 300 s,
>   görünme p50 384,7 / **p95 657,0** / maks 771,2 ms, kayıp 0. `docs/09` §1 tablosunun
>   **altı satırının tamamı** artık eserle örtülü (3.000 → 704,0 · 5.000 → 769,1 ·
>   10.000 → 18.940,5 · 1.000×25 → 693,7 ms). **Bu bulgum kapanmıştır.** Değerlendirdiğim
>   ağaçta (`467e99c`) eser gerçekten yoktu; ekip bunu `main`'de zaten kapatmıştı, `polish`
>   dalı geride kalmıştı.
> - **Kapanmayan kısım:** 14 eserin **hiçbiri** hâlâ `makine` bloğu taşımıyor (özyineli
>   olarak yeniden taradım). Y1 geçerliliğini koruyor ve dokümanı buna göre düzelttim.
> - **Birleştirmenin ortaya çıkardığı YENİ bir kusur:** `976ff06` eserleri commit'lerken
>   `docs/09`'u yeniden üretmemiş. `origin/main`'i ayrı bir çalışma ağacına alıp denedim:
>   **`python scripts/gen_olcek_doc.py --check` `main`'in kendisinde de düşüyor**
>   (`guncel degil`). Yeniden ürettim (7 satır eklendi), artık geçiyor.
>
> **Bu ek notla K6'nın gerekçesi değişir.** Puanı raporda değiştirmiyorum — ama jüri için
> açık olsun: bugünkü birleşik ağaçta K6'nın üç dayanağından ikisi (araç çöküyor, 657 ms
> eseri yok) **kapanmıştır**; açık kalanlar eserlerdeki makine bloğu eksikliği ve F-36
> eserinin bayatlığıdır. Aynı çapalarla bugün K6'ya **8** verirdim; bu, A ortalamasını
> 7,89 → 8,22'ye taşır. **Bu, bağımsız olarak doğrulanmamış bir güncellemedir.**

> Bu rapordaki her sayının yanında ne olduğu yazılıdır: **ÖLÇTÜM** (komutu ben koştum,
> çıktısı burada), **BEYAN** (doküman söylüyor, koşmadım), **ÜRETİLEMEZ** (sayıyı üreten
> eser/betik depoda yok), **DOĞRULANAMADI** (koşamadım, sebebi yazılı), **YANILTICI**
> (iddia ile kod/çıktı uyuşmuyor). Etiketsiz sayı yoktur.

---

## 0. Nasıl değerlendirdim

### 0.1 Ölçüm makinem (projeden istediğim tekrar-üretilebilirliği kendimden de istiyorum)

| | |
|---|---|
| İşletim sistemi | Windows 11 Home Single Language 10.0.26200 |
| Mantıksal CPU | **8** (`nproc`) |
| Sanallaştırma | Docker Desktop **29.2.1**, `docker info`: `NCPU=8`, `MemTotal=8.195.268.608 B` (≈7,63 GiB) |
| Python | 3.11.4 (depodaki `backend/.venv`) · Node v24.14.1 · git 2.41.0.windows.3 |
| Derleyici (gömülü) | `gcc:13` konteyneri, **gcc 13.4.0**, cmake 3.25.1 |

**Önemli uyarı — kendi ölçümüm hakkında.** Bu makine 8 iş parçacıklıdır. Projenin `docs/09`
§2'de kayıtlı ölçüm düzeneği i7-14700KF / 28 iş parçacığıdır. Bu yüzden **kendi yük
ölçümlerimi projenin sayılarıyla "daha iyi / daha kötü" diye karşılaştırmıyorum.** Görev
metni §3② tam olarak bu tuzağı işaret ediyor; projenin kendisi de aynı tuzağa bir kez
düşüp geri çekmiş (`docs/09` §4.1c). Ben yalnızca *"bu sayıyı üreten şey koşuyor mu, çıktısı
yayımlananla aynı mı"* sorusunu sordum.

### 0.2 Koştuğum komutlar (süreleriyle)

| Komut | Sonuç | Süre |
|---|---|---|
| `docker compose -f deploy/compose.yaml down -v` + `up -d --build` | 9 servis ayakta | **71 s** (imaj katmanları önbellekte) |
| `cd libs/panoalgo && pytest` | **500 passed, 0 skipped** | 254,95 s |
| `cd backend && pytest` (DSN yok) | **896 passed, 37 skipped** | 184,44 s |
| `cd backend && TEST_DB_DSN=… pytest` | **933 passed, 0 skipped** | 357,90 s |
| `cd frontend && npm test` | **166 test / 19 dosya, hepsi geçti** | 56,03 s |
| `cd frontend && npm run e2e` | **10/10 geçti**, 10 rota, 0 konsol hatası, 0 axe ihlali | 3,3 dk |
| `GRIDUP_E2E_KIP=canli npx playwright test` | 2/2 geçti, 0 konsol hatası, **20 kontrast ihlali** | 57,3 s |
| `cmake -S firmware …` + `ctest` (gcc:13) | **5/5 double + 5/5 float**, 0 uyarı | ~2 dk |
| `scripts/validate.py --out <geçici>` | 14 senaryo; `docs/12` ile fark **yalnızca zaman damgası** | 2,45 s |
| `scripts/threshold_sweep.py --seasons` | kış 28,6 / geçiş 71,4 / yaz 0,0 | 10,2 s |
| `scripts/sir_taramasi.py` | temiz, 534 izlenen dosya | <5 s |
| `scripts/check_contracts.py --check` + 5 `gen_*.py --check` | altısı da `guncel` / `TUTARLI` | <30 s |
| `scripts/tazminat_maruziyeti.py` (+`--duyarlilik`) | parametresiz `veri yok`; duyarlılık tablosu üredi | <10 s |
| `scripts/verify_journal.py` (+2 negatif test) | sağlam → kopuk (değişmiş) → kopuk (silinmiş) | <10 s |
| `loadtest/veri_butcesi.py` (varsayılan) | koştu, **yayımlanan sayıyı üretmedi** | **71 dk 35 s** |
| `loadtest/veri_butcesi.py --panolar 2 --gun 0.06` ×2 | iki koşum birebir aynı, eserle birebir aynı | ~2 dk |
| `loadtest/fleet.py` ×3 | **üçünde de çöktü**, eser üretmedi | 120 s + 10 s + 10 s |
| Kendi Modbus istemcim (25 nokta × 4 koşum) | 3 koşumda FARK 0, 1 koşumda 1 fark | <1 dk |
| **Kendi ham IEC 104 istemcim** (projenin kodeği kullanılmadan) | protokol uygunluğu doğrulandı | <1 dk |
| Kendi GSM PDU çözücüm | SMS-SUBMIT çözüldü | <1 s |
| Kendi WCAG kontrast hesabım | 13,3330 ve 12,5909 | <1 s |
| Kendi xlsx çözümleyicim | lag-1 = 0,0003; maks. sıçrama 438,0 A | <1 s |
| Kendi S1 fikstür hesabım | öne alma **172,5 saat** | <1 s |

### 0.3 Koşamadıklarım

- **Gerçek donanım yok** (yarışmanın kısıtı, projenin değil) — puan düşürmedim.
- **TimescaleDB 46–48× sıkıştırma oranı:** oran 1 günden eski parçalarda ölçülüyor; bir
  günlük veri biriktiremedim. Politikanın **etkin olduğunu** doğruladım (aşağıda).
- **10.000 panoya kadar yük tekrarı:** 8 iş parçacıklı makinede anlamlı olmazdı; ayrıca
  `fleet.py` zaten çöküyor.

### 0.4 Kendi bulaşmam (dürüstlük notu)

Yığın ben gelmeden önce başka bir oturumdan ayaktaydı. **Temiz bir "yabancı bunu kaldırabilir
mi" testi için `down -v` ile tamamen sildim ve sıfırdan kurdum.** Rapordaki bütün yığın
ölçümleri bu soğuk kalkıştan sonrasıdır. Değerlendirme sırasında depoda yaptığım her
değişikliği geri aldım; bitiş durumu `git status` ile temizdir (yalnızca görev dosyası
izlenmiyor). Ayrıntı: **Ek B**.

---

## 1. Puan tablosu

| # | Kriter | Puan | Tek cümlelik gerekçe | Kanıt türü |
|---|---|---:|---|---|
| 1 | Problemin doğru anlaşılması | **7** | Kurumun dokuz dosyası register/madde düzeyinde okunmuş ve sayısal analizinin üçünü ben de doğruladım; ama jüriye bakan özet katmanı (`docs/01`) projenin kendi derin dokümanlarının çürüttüğü iki fiziği hâlâ taşıyor ve bir iddia kodla çelişiyor | ÖLÇTÜM + 3 YANILTICI |
| 2 | Anomali ve risk tespit başarısı | **9** | `docs/12`'nin tamamı 2,45 s'de yeniden üredi (fark: yalnızca zaman damgası); döngüselliği proje kendisi bulmuş, ölçmüş ve yayımlamış — kendi olumsuz sonucu dâhil | ÖLÇTÜM |
| 3 | Saha koşullarında uygulanabilirlik | **8** | Beş güvenlik kuralı şartname maddesine atıflı, AT sekonderi uyarısı imzalı kontrol listesinde, parça numaralı BOM, bayt bayt yeniden üretilebilen STL; hiçbiri fiziksel olarak doğrulanmadı ve proje bunu 39 yerde açıkça yazıyor | ÖLÇTÜM + BEYAN |
| 4 | Uçtan uca sistem ve gerçek bildirim | **8** | Soğuk kalkıştan 71 s'de 9 servis; S4 senaryosu gerçekten `ALM-ARC-TRIP` üretti; SMS PDU'sunu kendim çözdüm (gerçek GSM 03.40); kurcalama zinciri iki bozma biçimini de ayırt etti — ama dış kanalların hiçbiri gerçek bir servise gitmiyor | ÖLÇTÜM |
| 5 | Mevcut sistemlerle entegrasyon (SCADA) | **9** | Kendi ham IEC 104 istemcimle uygunluğu doğruladım: STARTDT, COT 7→20→10, 139 ölçülen nokta, bilinmeyen tip → COT 44, tek komut → **reddedildi**; Modbus 25 noktada REST ile fark 0 | ÖLÇTÜM |
| 6 | Ölçeklenebilirlik | **5** | Ölçüm aracı `loadtest/fleet.py` HEAD'de **çöküyor** (3/3 koşumda), commit'li on eserin **hiçbirinde** makine bilgisi yok — oysa `docs/09` §4.1b "eseri açıp bakın" diyor; manşet 657 ms'in eseri depoda değil | YANILTICI + ÜRETİLEMEZ |
| 7 | Kullanıcı / operasyon deneyimi | **8** | 166 birim + 10 e2e testi geçti, örnek kipte 0 axe ihlali, iki kontrast oranını kendim hesapladım (13,3330 / 12,5909); canlı kipte **20 kontrast ihlali ölçtüm** ve bu CI'yı kilitlemiyor | ÖLÇTÜM |
| 8 | Maliyet ve fayda | **8** | Üç BOM toplamını da, pano başı üç yapılandırmayı da, duyarlılık tablosunun iki satırını da kendim yeniden ürettim; betik eksik girdide **uydurmuyor**, `veri yok` diyor — ama fiyatların tarihi ve tedarikçisi yok | ÖLÇTÜM |
| 9 | Yenilikçilik | **9** | Manşet 172,5 saati commit'li fikstür + sözleşme eşiğinden **kendim hesapladım, birebir çıktı**; C↔Python farkı 1,36e-08 / 6,96e-06 ve 384 B / 196 B bellek ölçtüm | ÖLÇTÜM |

---

## 2. Üç ağırlık, üç toplam

| Ağırlık | Hesap | Sonuç (10 üzerinden) |
|---|---|---:|
| **A — Eşit** | (7+9+8+8+9+5+8+8+9) / 9 = 71/9 | **7,89** |
| **B — Teknik** (K2, K4, K5 çift) | 97 / 12 | **8,08** |
| **C — Ticari** (K1, K3, K8 çift) | 94 / 12 | **7,83** |

**Karar üç ağırlıkta da aynı mı? — Evet.** Üç toplam 7,83–8,08 bandında, aralık 0,25 puan.
Hiçbir ağırlık projeyi başka bir sınıfa taşımıyor: her üçünde de "güçlü mühendislik, tek
ciddi tekrar-üretilebilirlik yarası olan bir iş" sonucu çıkıyor. Sonuç **sağlamdır**.

**Belirleyici kriter yok, ama K6 üç ağırlıkta da aynı ağırlıkta (1×) ve üçünü birden
aşağı çekiyor.** K6'nın 5 yerine 8 olduğu bir dünyada A 8,22 / B 8,33 / C 8,08 olurdu —
yani bu tek kriter toplamda ~0,3 puan tutuyor. B'yi C'nin üstüne çıkaran şey K5 ve K2'nin
9'larıdır; yani saha/SCADA jürisi bu projeyi satın alma bakışından **biraz daha yüksek**
değerlendirir. Fark küçüktür ve sıralamayı değiştirmez.

---

## 3. Tekrar-üretilebilirlik taraması

README'nin "Jüri Kanıt Haritası" tablosundaki (satır 23–33) her manşet sayı için tek soru:
*bu sayıyı hangi komut üretir ve o komut depoda mı?*

### 3.1 Betiği olan ve benim koşturduğum sayılar (**ÖLÇTÜM**)

| Manşet sayı | Üreten komut | Sonuç |
|---|---|---|
| Çiy olayı kış **28,6** / geçiş **71,4** / yaz **0,0**; 0,5-0,0 çifti **228,6** | `scripts/threshold_sweep.py --seasons` | Birebir üredi |
| Duyarlılık **1,00** (eşleşen) / **0,88** (uyumsuz), 78,90 K vs 48,48 K, RUL %5,2 / CRA −5,12 | `scripts/validate.py --out …` | `docs/12` ile **tek fark: üretim zamanı** |
| BOM **70,73 / 47,68** USD (+ 23,25/13,95 ve 19,80/11,79) | `hardware/*/bom.csv` (kendi `awk` toplamım) | Üçü de birebir |
| Pano başı **103,48 / 145,33 / 396,43** USD, geri ödeme 7,4 / 10,4 / 28,3 ay | `scripts/tazminat_maruziyeti.py --duyarlilik` | Birebir; elle de doğruladım |
| Kaldıraç **1,33×** ve **0,09× – 3,57×** | aynı betik, `docs/10` §7.4 parametreleriyle | Tablonun iki satırı **birebir** üredi |
| Kontrast **13,33:1** ve **12,59:1** | `frontend/src/theme.test.ts` + kendi WCAG hesabım | 13,3330 ve 12,5909 |
| STL **324 üçgen** | `hardware/mekanik/generate_stl.py` | **Bayt bayt aynı** (aynı SHA-256) |
| C↔Python **1,36e-08** / **6,96e-06**, 240 adım | `ctest` (gcc 13.4) | `1.362e-08` / `6.961e-06` |
| Bellek **384 B / 196 B** | kendi `sizeof` ölçümüm | Birebir |
| **172,5 saat** öne alma (ve 226,5 / 399,0) | *betik yok* — `data/fixtures/S1_loose_conn.csv` + `contracts/alarm-codes.yaml` ile **kendim hesapladım** | **172,5** birebir |
| Test sayıları 500 / 896+37 / 933 / 166 / 5-5 | `pytest`, `npm test`, `ctest` | Beşi de birebir |
| Sır taraması **534 dosya** | `scripts/sir_taramasi.py` | Birebir |
| Modbus = REST×10, 25 noktada fark 0 | kendi `pymodbus` istemcim | 3 koşumda 25/25 |
| Veri bütçesi **2 panolu** eser (518 / 273 / %47,3) | `loadtest/veri_butcesi.py --panolar 2 …` | İki koşumda da birebir |

### 3.2 Üretecin `--check` iddiası (§3③) — **geçti**

Altı üreteç betiğinin altısı da `guncel` döndü ve çalışma ağacı temiz kaldı; yani
`docs/03`, `docs/04`, `docs/06`, `docs/09` §4.1b ve Grafana panoları gerçekten
üretiliyor, elle yazılmıyor. `check_contracts.py --check`: *"kodda 18 uç, hepsi
sözleşmede"* → `SOZLESMELER TUTARLI`. **Bu, projenin en güçlü yapısal savunmalarından
biridir ve ben koştum.**

### 3.3 Betiği olmayan / eseri olmayan sayılar (**ÜRETİLEMEZ**)

| Manşet sayı | Durum |
|---|---|
| **1.000 panoda görünme p95 657 ms** | `loadtest/results/` altındaki **on eserin hiçbirinde** yok. En yakınları 667,8 / 710,5 / 754,5 / 763,2 ms. 13 Eylül i7 koşumunun eseri depoda değil. Koşum **koşulları** `docs/09` §2'de düzyazı olarak kayıtlı (bu iyi), ama **eser yok**. |
| **IEC 104 = REST, 87 kontrol, 0 fark** | 13 Eylül koşumu; eseri depoda yok. *Mekanizmayı* kendi istemcimle doğruladım (aşağıda), ama "87 kontrol" sayısını üreten bir komut yok. |
| **TimescaleDB 46–48× sıkıştırma** | Üreten araç var (`loadtest/storage.py`) ve ölçüm koşulu SQL başlığında yazılı (13 Eylül, bir günlük veri, 198→4,09 B/satır). Eser commit'li değil; ben bir günlük veri biriktiremedim. |
| **Alarm → SMS p95 606 ms** | `docs/09` §1 tablosunda; eseri depoda yok. |

### 3.4 Koşum koşulları kayıtlı mı? (§3②)

**Düzyazıda evet, eserde hayır.** `docs/09` §2 düzeneği örnek alınacak ayrıntıda yazıyor:
işlemci modeli, çekirdek/iş parçacığı, RAM, Docker sürümü, WSL2 vCPU, backend parti ayarı,
**ve yük üretecinin aynı makinede olduğu** ("yani sonuçlar temkinli"). Bu, çoğu yarışma
projesinden iyidir.

**Ama eser düzeyinde kayıt yok ve doküman aksini söylüyor.** Bu, raporun en ağır bulgusudur;
§8'de ayrıca listelenmiştir.

### 3.5 Bayat eser: F-36 artık yeniden üretilmiyor

`loadtest/veri_butcesi.py` varsayılanlarla koşturuldu (5 pano × 25 nokta, 7 gün ısınma +
48 saat, tohum 20260918 — commit'li eserin parametrelerinin **birebir aynısı**, doğruladım).
**71 dakika 35 saniye** sürdü ve şunu verdi:

| Politika | Yayımlanan eser | **Benim koşumum** |
|---|---:|---:|
| sabit-10 s | 86.400 / 1071,2 MB | 86.400 / 1071,1 MB |
| uyarlanabilir %1 | 81.350 / %5,8 | 81.302 / %5,9 |
| **uyarlanabilir %2 (manşet)** | **50.932 / %41,0 / 632,5 MB** | **50.612 / %41,4 / 628,3 MB** |
| uyarlanabilir %5 | 41.843 / %51,6 | 41.476 / %52,0 |
| uyarlanabilir %10 | 33.093 / %61,7 | 32.817 / %62,0 |

307 alanın **93'ü** değişti. Sebebi ayırmak için küçük yapılandırmayı **iki kez** koştum:
iki koşumum birbirinin aynısı **ve** commit'li 2 panolu eserin aynısı çıktı. Yani
**betik belirlenimlidir; bayat olan eserdir.** 18 Eylül'den sonra üreteç değişmiş
(19 Eylül `3674756`, S10–S13). Bunu yakalayacak bir `--check` yok — `gen_olcek_doc.py --check`
tabloyu esere göre denetliyor, eseri koda göre değil.

**Sonuç:** README'nin F-36 manşet rakamları (86.400 → 50.932, %41,0, 1.071 → 632 MB)
**bugünkü koddan yeniden üretilemiyor**; ~%0,6 sapıyor. Niteliksel sonuç (bastırma ~%41,
tespit 10 s'de kalıyor) ayakta; rakamların son hanesi değil.

---

## 4. Kriter kriter kanıt defteri

### Kriter 1 — Problemin doğru anlaşılması → **7/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| "`İstenen Veriler.xlsx`'teki 152 örneklik seri, lag-1 otokorelasyonu **0,00**" | `docs/14-veri-ureteci.md:64` | **ÖLÇTÜM** | xlsx'i kendi çözümleyicimle açtım: 4 sayfa, 'Akım Sensörü' 157 satır, kurumun kendi etiketi **"Sentetik Data"**. Sayısal sütun n=152, **lag-1 = 0,0003**. İddia doğru. |
| "15 dakikada **438 A**'lık sıçramalar var" | `docs/05-anomali-tespiti.md:199` | **ÖLÇTÜM** | Ardışık primer akım farkının maksimumunu hesapladım: **tam 438,0 A** (ort. 312,79 A, min 90, maks 540). İddia doğru. |
| "…bunlar L0/L1'e girmeden **burada (L-1) işaretlenir**" | `docs/05:199-200`, `firmware/akis-diyagramlari/ana-dongu.md:81` | **YANILTICI** | `libs/panoalgo/panoalgo/quality.py:140-170` — `point_quality()` yalnızca `sample["t_conn"]` üstünde **iki** kural işletiyor: `t_c < ambient − deadband` ve `abs(t_c − prev.t_c)/dk > dq_max_rate_k_per_min` (10,0 **K**/dk). Depoda **akım için hiçbir değişim-hızı kuralı yok**. 438 A'lık bir sıçrama bu katmanda işaretlenmez. |
| "TVOC-2 zaten arkı **<1 ms'de kesiyor** (SIL-2)" | `docs/01-problem-analizi.md:21` | **YANILTICI** | Kataloğu (`Hackathon Verileri/tvoc.pdf`) kendim ayrıştırdım: *"From light detection to trip (contacts K4, K5, K6) **Approx. 1 ms** (depends on light intensity)"*. İki hata: (a) "~1 ms" ≠ "<1 ms"; (b) bu süre **açma kontağına kadardır**, arkın sönmesi değil (kesicinin açma süresi eklenir). SIL-2 doğru. Projenin kendi derin raporu `HACKATHON_ANALIZ_RAPORU.md:293` bunu **doğru** yazıyor; hata özet katmanında (`:45`, `:405`, `docs/01:21`). |
| "AG'de PD nadir — **Paschen minimumu ~327 V**, 400 V altında" | `docs/01:24-26`, `docs/14:132` | **YANILTICI (kendi kendini çürütmüş)** | `docs/05:366-370` aynı depoda şöyle diyor: *"o kısayol eksiktir: 400 V sistemde faz-faz tepe gerilimi √2×400 ≈ 566 V'tur, yani 327 V'un üstündedir"* ve doğru (geometrik) gerekçeyi veriyor. Sonuç (PD = OG konusu) doğru, **jüriye bakan gerekçe yanlış**. |
| "Kurumun istediği üç kalem koda döndü: ABB TVOC-2 Modbus" | `README.md:25` | **ÖLÇTÜM** | xlsx 'ARC' sayfası: *"ABB TVOC-2 markası verilerinden Modbus ile okunarak alınacaktır"*. `sim/tvoc2_sim.py` mevcut; canlı yığında `gridup-tvoc-sim` :5021'de koşuyor. |
| "…HFCT/EA Technology PD (`contracts/alarm-codes.yaml:167`)" | `README.md:25` | **ÖLÇTÜM** | xlsx 'PD' sayfası: `DS_HFCT30` / *"EA Technology SEA"*. `alarm-codes.yaml:167` bu kaynağı adıyla anıyor. |
| "…mA sekonder + çarpan (`devices.py:223`)" | `README.md:25` | **BEYAN (kısmen)** | `devices.py:223` `MPR_CURRENT_SCALE = 0.001` — bu ENTES MPR-53CS'in **register ölçeğidir**, xlsx'in önerdiği 125 mA sekonder mini akım trafosu fikri değil. Bağlantı gerçek ama README'nin ifadesi birebir değil. |
| "Mevsim taraması: tek sabit eşik üç mevsimde birden çalışmıyor" | `README.md:25`, `docs/05` §11 | **ÖLÇTÜM** | Birebir üredi (28,6 / 71,4 / 0,0). Proje ayrıca bunun **kendi üretecinin iklim modelinin özelliği** olduğunu yazıyor (`generator.py:96-97`) — bu, lehine bir dürüstlük işaretidir. |
| "Sıcaklık_Nem sayfası boş" | `HACKATHON_ANALIZ_RAPORU.md:177` | **ÖLÇTÜM** | Doğru: 0 satır. |
| 20+ standart ve TEDAŞ şartname maddesi atfı | `docs/11`, `docs/19` | **BEYAN** | Atıf listesi alan olarak doğru (IEC 61439-1, 60664-1, 60529, 60695-11-10, 61000-6-5, 62271-200, 62682, 62974-1, ISO 13379-1/13381-1…). Maddelerin metnini tek tek okumadım. |

**Gerekçe.** Kaynak belge çalışması yarışma ortalamasının belirgin üstünde: kurumun dokuz
dosyasının tamamı okunmuş ve **ben de üç sayısal iddiasını bağımsız doğruladım** (lag-1,
438 A, boş sayfa). Kurumun verdiği veriyi "gürültü" diye teşhis edip sentetik üretece
geçmek doğru karardır ve gerekçesi yazılıdır. Buna karşılık jüriye bakan özet katmanı
(`docs/01`) projenin kendi derin dokümanlarının çürüttüğü iki fiziği taşıyor, bir iddiası
da kodla çelişiyor. Çapamda 9/10 "varsayımlar yanlışlanabilir biçimde yazılı" diyordu —
bu sağlanmış; ama aynı çapada "doğru fizik" şartı üç noktada karşılanmıyor. **7.**

---

### Kriter 2 — Anomali ve risk tespit başarısı → **9/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| "Bu dosya elle yazılmaz: `validate.py` tabloyu yeniden üretir" | `README.md:26` | **ÖLÇTÜM** | Geçici yola ürettim, `docs/12` ile `diff`: **11 satır, tek anlamlı fark `Uretim zamani`**. Bütün sayılar birebir. 2,45 s. |
| Eşleşen modelde duyarlılık **1,00** (12/12), uyumsuzda **0,88** (14/16) | `docs/12` §1 | **ÖLÇTÜM** | Kendi ürettiğim dosyada satır 50: *"beklenen alarmların 12/12'i yakalandı (recall 1.00); … 14/16 (recall 0.88)"*. |
| "Üreteç ile dedektör aynı denklemi çözüyor; duyarlılık 1,00 büyük ölçüde *kestirici kendi ileri modelini ters çevirebiliyor* demektir" | `generator.py:140-144` | **ÖLÇTÜM (döngüsellik — projenin kendi tespiti)** | Kodu okudum: dedektörün regresörü `phi = [dT[k], I²[k]]`, θ = [a, β] — **iki serbestlik derecesi**. Komşu kuplajını, ikinci ısıl kutbu, yüke bağlı τ'yu temsil edecek bir serbestlik derecesi **gerçekten yok**. Proje bunu kendisi yazmış. |
| S10–S13 dedektörün varsaymadığı fiziği ekliyor | `scenarios.py:220-314` | **ÖLÇTÜM** | Dördü de gerçekten `ModelMismatch` bayrağı açıyor: `coupling_k=0.15`, `tau_load_coeff=-0.8`, `slow_share=0.45`, `sensor_gain_per_k=0.008`. Tiyatro değil. |
| "İlk uyumsuzluk taslağı çarpımsaldı ve **hiçbiri tespiti bozmadı**; sebep yapısal: `k_ratio = (g·K)/(g·K₀) = K/K₀`, kazanç sadeleşir" | `generator.py:146-158` | **ÖLÇTÜM (en değerli dürüstlük kaydı)** | Matematik doğru ve kod bunu yansıtıyor. Proje **başarısız ilk denemesini silmemiş**, gerekçesiyle bırakmış. |
| RLS matematiği doğru | `detect.py:8-12`, `:393-409` | **ÖLÇTÜM** | Ders kitabı biçimi: `g = Pφ/(λ+φᵀPφ)`, `θ += g·e`, `P ← (P − gφᵀP)/λ`. Ölçekleme (`I2_SCALE=1e5`) gerekçeli. |
| "Prognoz geri testi **iyi değil**: S1 koni içinde %5,2, CRA −5,12" | `docs/12` §4 | **ÖLÇTÜM** | Kendi ürettiğim dosyada satır 123: `S1_loose_conn … 5.2% … -5.12`. **Proje kendi olumsuz sonucunu yayımlıyor.** |
| "209 saati tetikleyen kod **tespit değil prognoz**; K eşiğine dayanan öne alma 172,5 saattir" | `docs/12` §2 dürüstlük kaydı | **ÖLÇTÜM** | Üretilen dosya `Tetikleyen kod` sütununu basıyor ve `ALM-TTL-14D`'yi işaretliyor. 172,5'i ayrıca kendim hesapladım (K9). |
| Sağlıklı panoda yanlış alarm yükü **71,4**/100 pano/gün | `docs/12` §3, `README:27` | **ÖLÇTÜM** | `threshold_sweep` çıktısında sözleşme eşiği satırı (3,0/1,0) **71,4**. |
| 500 algoritma testi, 0 atlanan | `README:268` | **ÖLÇTÜM** | `500 passed in 254.95s`. |
| Gerçek saha verisiyle doğrulama | — | **DOĞRULANAMADI (yarışma kısıtı)** | Gerçek veri yok; proje bunu **iddia etmiyor**, aksine her yerde yazıyor. Kural 3 gereği eksi yazmadım. |

**Gerekçe.** Çapamda 9/10'un şartı şuydu: *"…ve en önemlisi: üreteç ile dedektörün aynı
denklemi çözüp çözmediği (döngüsellik) proje tarafından TARTIŞILMIŞ."* Bu şart yalnızca
karşılanmakla kalmıyor — proje döngüselliği **ölçülebilir hale getirmiş** (S10–S13),
kendi başarısız ilk denemesini kaydetmiş ve prognoz tarafındaki kötü sonucu yayımlamış.
Eksik olan: ROC/PR eğrisi yok, çoğu sonuç tek işletme noktasında, uyumsuzluk büyüklükleri
(0,15 / −0,8 / 0,45 / 0,008) sahadan ölçülmüş değil, ekibin seçimi. **9.**

---

### Kriter 3 — Saha koşullarında uygulanabilirlik → **8/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| Beş güvenlik kuralı, şartname maddesiyle | `docs/08:15-18` | **ÖLÇTÜM (okudum)** | Sıra doğru ve eksiksiz: kes → kilitle-etiketle → gerilim yokluğunu kontrol et → toprakla/kısa devre et → alanı işaretle; madde 5.3'e atıflı. |
| "**AT sekonderi hiçbir koşulda açık devre bırakılmaz**" — FMEA'nın en ağır donanım riski, ayrıca imzalanır | `docs/08:28-30` | **ÖLÇTÜM (okudum)** | Bu, AG/OG saha işinde en kritik tek güvenlik kuralıdır ve doğru yerde, doğru ağırlıkta duruyor. Ayrık çekirdekli (devreyi açmayan) sensör şartı da yazılı. |
| Montaj enerjisizde, ≤45 dk, 2 kişi; enerjili adımlar "dokunmasız" | `docs/08:1-40` | **BEYAN** | Yordam tutarlı ve gerçekçi; sahada denenmedi. |
| Sensör gövdesi clearance/creepage mesafesini azaltmamalı | `docs/08:23-25` | **ÖLÇTÜM (okudum)** | IEC 60664-1 yalıtım koordinasyonuna atıflı. |
| Parça numaralı BOM (3 kart) | `hardware/*/bom.csv` | **ÖLÇTÜM** | Gerçek üretici kodları: ESP32-S3-WROOM-1-N8R8, ATECC608A-SSHDA, ADM2587EBRWZ, IRM-10-5, EC200A-EU, INA226AIDGST, OPA656U, nRF52833-QDAA, Fibox ARCA 92/125… Yer tutucu değil. |
| `din-kutu.stl` **324 üçgen**, `din-kutu.scad`'den parametrik | `README:27` | **ÖLÇTÜM** | 16.284 bayt = 84 + 50×324; başlık alanı 324 diyor; ikili STL. `generate_stl.py` ile yeniden ürettim: **aynı SHA-256** (`1221b540…`). |
| "Ark tespiti için ayrı kart yoktur; yalnızca PD kartı tasarlandı" | `README:27` | **ÖLÇTÜM** | `hardware/` altında üç paket var, `pd-karti` dâhil; ark için ayrı kart yok. TVOC-2 canlı yığında Modbus'tan okunuyor. |
| "Hiçbiri veri sayfasına karşı doğrulanmadı ve üretilmedi" | `docs/19` §3, `docs/13:88` | **ÖLÇTÜM (dürüstlük)** | `docs/13:88` örnek niteliğinde: *"BOM kalemlerinin sıcaklık sınıfı üretici veri sayfalarından DOĞRULANMADI… sıcaklık döngüsü testi yapılmadı"*. `docs/19`'da 39 ayrı "doğrulanmadı/test edilmedi/yapılmadı" ifadesi saydım. |
| FMEA, Ş×O×D = RÖS yöntemiyle, azaltma sonrası RÖS'le | `docs/07` + `docs/07b` | **ÖLÇTÜM (okudum)** | Yöntem doğru (ör. 9×3×5=135 → 9×2×2=36). **DÜZELTME (Ek B md. 10):** ilk yazdığımda "yalnızca ~5 satır, ince" demiştim — **yanlıştı.** FMEA iki dosyaya bölünmüş ve `docs/07:3-5` bölünmeyi açıkça yazıyor: donanım/saha satırları **1, 2, 3, 9, 10** `docs/07`'de, yazılım/sistem satırları **4–8 ve 11–14** `docs/07b`'de. Toplam **14 arıza modu**, numaralandırma sürekli. Bu, tek bir saha cihazı için makul bir kapsamdır. |
| Operatör yükü 71,4 yanlış alarm/100 pano/gün < hedef 150 | `README:27` | **ÖLÇTÜM** | `threshold_sweep` ile üredi. |
| IP20, V-0, −25…+70 °C, EMC 61000-6-5 | `docs/13:88-126` | **BEYAN** | Hedef olarak yazılı, **doğrulanmadığı da yazılı**. Tip test yok. |

**Gerekçe.** Çapamda 9/10 şunları istiyordu: parça numaralı BOM ✔, standart maddesine
referanslı uygunluk iddiası ✔, enerjili montaj için iş güvenliği yordamı ✔, saha arıza modu
✔ (FMEA), hangi iddianın test edilmediği açıkça yazılı ✔✔. Eksik kalanlar: ömür/bakım
periyodu yüzeysel, FMEA ince, ve **hiçbir fiziksel doğrulama yok**. Sonuncusu yarışmanın
kısıtıdır ve proje bunu iddia etmiyor — eksi yazmadım, yalnızca tavanı sınırladı. **8.**

---

### Kriter 4 — Uçtan uca sistem ve gerçek bildirim → **8/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| "Tek komutla **9 servis** kalkar" | `README:28` | **ÖLÇTÜM** | `down -v` + `up -d --build` → **71 saniye**, `compose ps` 9 servis `running`. Not: imajlar önbellekteydi; gerçekten ilk kurulum daha uzun sürer. |
| "`panosim` → MQTT → Ingest → TimescaleDB → REST → WebSocket → UI canlı yığında, **karantina 0**" | `README:28` | **ÖLÇTÜM** | Soğuk kalkıştan sonra `/health`: `received 123, rejected 0, written 123, dropped 0, write_errors 0`. `select count(*) from quarantine` → **0**. |
| S4 senaryosu P1 ark alarmı üretir | `README:106`, `demo/senaryo/s4.sh` | **ÖLÇTÜM (ama konsol çıktısı yanıltıyor)** | Senaryoyu koştum. API'de **`ALM-ARC-TRIP` gerçekten oluştu** (alarm id=3, `notified:['sms']`). Fakat `panosim` konsolu *"beklenenlerden **0/1** görünen: ALM-ARC-TRIP"* yazdı — bu, kenar simülatörünün kendi özetidir; alarmı merkezî dedektör üretti. Senaryoyu koşan bir jüri üyesi **çalıştığı hâlde çalışmadı sanır**. |
| Sanal GSM modem gerçek donanım değil | `README:28` | **ÖLÇTÜM (doğru etiketlenmiş)** | `deploy/runtime/sms-log.txt` gerçek AT komut trafiği içeriyor (`AT+CMGS=80`, `+CMGS: 3 | OK`). **PDU'yu kendi 7-bit çözücümle çözdüm:** SMS-SUBMIT, TOA 0x91, alıcı +905550000001 (sahte 555 aralığı), DCS 0x00, VP 0xAA, 75 septet → *"[GRIDUP P1] SIM-00004: TVOC-2 ark tripi…"*. **Gerçek GSM 03.40 kodlaması**, sahte log satırı değil. |
| "Telegram belirteci `.env`'de boştur, girilene kadar kanal devre dışıdır" | `README:70` | **ÖLÇTÜM** | `deploy/.env` içinde `TELEGRAM_BOT_TOKEN=` satırı gerçekten boş. İddia doğru ve lehine bir dürüstlük işaretidir. |
| Alarm yaşam döngüsü kurcalama-kanıtı **hash zincirine** yazılır; `verify_journal.py` bozulan satırı halka numarasıyla bulur | `README:28,156-169` | **ÖLÇTÜM (iki negatif testle)** | (1) Temiz: `ZINCIR SAGLAM — 6 halka dogrulandi`. (2) Bir satırın `note`'unu değiştirdim: `ZINCIR KOPUK — halka 1 … satirin icerigi ozetine uymuyor — satir DEGISTIRILMIS`. (3) **Ortadan bir satır sildim**: `halka 3 … prev_hash oncekinin hash'ine denk gelmiyor — arada bir satir SILINMIS olabilir`, `saglam: 2 halka`. **İki bozma biçimini ayırt ediyor.** |
| Yetkilendirme: belirteçsiz 401 / yetersiz rol 403 / doğru rol 200 | `README:144-154` | **ÖLÇTÜM** | Üçü de birebir. Ayrıca **uydurduğum belirteç → 401** ve izleyici belirteciyle mühendis ucu → **403**. Reddi ben gördüm. |
| Uçtan uca gecikme ölçülmüş | `docs/09` | **ÜRETİLEMEZ** | Eserlerde `visible_latency_ms` var ama manşet 657 ms'in eseri yok; ayrıca ölçüm aracı bugün çöküyor (K6). |
| Kopma/yeniden bağlanma, QoS, mesaj kaybı | `docs/17` | **BEYAN** | MQTT QoS=1 `panosim` çıktısında görünüyor; kopma senaryosunu ayrıca koşmadım. |

**Ek bulgu (belgelenen tarifin yan etkisi).** README §"Testler", yığın ayaktayken şunu
öneriyor: `TEST_DB_DSN="postgresql://…@127.0.0.1:5432/gridup" pytest`. Bunu yaptım (933 test
geçti). Fakat `backend/tests/test_verify_journal.py:62-65` **canlı tablolara `DELETE FROM
alarm_journal / notifications / alarms / events` uyguluyor** ve `:129,:159` satırlarında
kütüğü bilerek `UPDATE` ediyor; temizlik kurulumda, bitişte değil. Sonuç: tarifeyi izleyen
biri demo veritabanının alarm geçmişini siler ve **denetim izini kurcalanmış hâlde bırakır** —
`verify_journal.py` sonrasında `ZINCIR KOPUK` der. README bu yan etkiyi uyarmıyor. Zinciri
temiz ölçmek için yığını sıfırladım.

**Gerekçe.** Çapamda 9/10 "en az bir **gerçek** kanal çalışıyor ve uçtan uca gecikme
ölçülmüş" diyordu. Gerçek dış kanal yok (hepsi simülatör/kapalı) ve gecikmenin eseri
depoda değil. Buna karşılık zincirin kendisi, kurcalama kanıtı ve yetkilendirme **ölçülerek**
doğrulandı. **8.**

---

### Kriter 5 — Mevcut sistemlerle entegrasyon (SCADA) → **9/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| IEC 104 kontrollü istasyon gerçekten koşuyor | `README:56` | **ÖLÇTÜM (kendi ham istemcimle)** | Projenin kodeğini **kullanmadan**, ham bayt yazdım: `68 04 07 00 00 00` (STARTDT act) → `0B 00 00 00` (con). Doğru U-biçimi el sıkışması. |
| Genel sorgulama (C_IC_NA_1) doğru sırayla cevaplanıyor | `docs/04` | **ÖLÇTÜM** | COT **7** (ACTCON) → veri **COT 20** (istasyon sorgulamasıyla) → COT **10** (ACTTERM). Standarda uygun tam sıra. |
| Modbus FC03 **139 adres** | `README:29` | **ÖLÇTÜM (çapraz doğrulama)** | Sorgulama yanıtında **139 adet `M_ME_NC_1`** (kısa kayan) + 29 adet `M_SP_NA_1` saydım. İki bağımsız taşıma katmanı aynı 139 sayısını veriyor. Sözleşmede 13 blok / 150 tanımlı kalem var. |
| Saat senkronu (C_CS_NA_1) ele alınmış | `docs/04` | **ÖLÇTÜM** | Tip 103 gönderdim → `TypeID=103 COT=7` **olumlu**. `iec104_server.py:9` gerekçeyi yazıyor: merkez saati SCADA'dan değiştirilmez, NTP'nin işidir. Mühendislik kararı, eksiklik değil. |
| Hata yolları standarda uygun | `iec104.py:44-49` | **ÖLÇTÜM** | Bilinmeyen tip 77 → **COT 44, P/N=1**; bilinmeyen ortak adres 0x0099 → **COT 46, P/N=1**. Taklit bir yığın bunları yapmaz. |
| "Röle kumandası **yoktur** (GK6)" | `README:29` | **ÖLÇTÜM (protokol düzeyinde teyit)** | `C_SC_NA_1` (tek komut, tip 45) gönderdim → **COT 44, P/N=1 ile reddedildi**. Güvenlik iddiası dokümanda değil, telde doğrulandı. |
| "`conn_temp` 25 noktanın tamamında Modbus = round(API × 10), **fark 0**" | `README:29,136` | **ÖLÇTÜM (bir nüansla)** | 4 koşum yaptım. 3'ünde **25/25, FARK=0**. 1'inde (okumalar arası 157 ms) `DSYA6_L1` 1 LSB saptı: REST 55,05 → register 551, benim `round()`'um 550. Sebep: `encoder.py:353-361` **yarım-yukarı** (`floor(x·10+0,5)`) kullanıyor; Python'un `round()`'u bankacı yuvarlamasıdır ve tam `x,x5` sınırında ayrışırlar. **`docs/03:80` bunu doğru belgeliyor** ("yarım yukarı yuvarlanır"); **README'nin `round()` kısaltması yanlıştır.** Bir SCADA entegratörü README'yi izlerse 0,1 °C'lik sapma görür. |
| Modbus haritası donmuş tek kaynak; 3 tüketici okuyor | `contracts/modbus-map.yaml:1-15` | **ÖLÇTÜM** | Dosya `endianness: big`, `word_order: high_first`, `mirror_fc03_fc04: true`, blok başına `type`/`scale`/`unit` taşıyor. `gen_modbus_doc.py --check` → `guncel`. Gerçek bir sözleşme. |
| CBS/GIS ve OMS + EPDK Madde 8 taslağı | `README:29` | **BEYAN** | Uçlar mevcut; yetkilendirmeyi doğruladım (izleyici → 403), içeriği uçtan uca koşmadım. Proje "sebep sınıfı öneridir, karar değildir" ve "tazminat tutarı hesaplanmaz" diyor — lehine dürüstlük. |
| "IEC 104 = REST, **87 kontrol**, 0 fark" | `docs/17:105` | **ÜRETİLEMEZ** | 13 Eylül koşumu; eseri depoda yok. Mekanizmayı doğruladım, sayıyı üreten komut yok. |
| Okuma uçları, WebSocket, 502 ve 2404 düz/açık kalır | `README:236` | **ÖLÇTÜM (dürüstlük)** | Doğru: kendi istemcim 2404'e **kimlik doğrulamasız** bağlandı. Proje bunu saklamıyor, `GET /health`'te `auth.enabled`/`mqtt_tls` alanlarında gösteriyor. |

**Gerekçe.** Çapamda 9/10 şunu istiyordu: nokta listesi tam, bir SCADA istemcisiyle okuma
kanıtlanmış, ASDU tipleri/COT/sorgulama/saat senkronu ele alınmış, RTU senaryosu net.
**Hepsi karşılanıyor ve okumayı ben kanıtladım.** Tek eksi: README'nin yuvarlama
kısaltması yanlış (doküman doğru) ve "87 kontrol" eseri yok. **9 — projenin en güçlü kriteri.**

---

### Kriter 6 — Ölçeklenebilirlik → **5/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| "**Her eser artık koştuğu makineyi kendi içinde taşır** (`makine` bloğu…) — §3'teki düzenek tablosuna güvenmek zorunda değilsiniz, **eseri açıp bakın**" | `docs/09:103-105` | **YANILTICI** | Açtım. `loadtest/results/` altındaki **on eserin onunda da** `makine` bloğu **yok** (özyineli anahtar taraması yaptım: `makine/machine/cpu/platform/host/ncpu` — hiçbiri). Paragrafın hemen üstündeki tablo tam olarak bu eserlere bağlanıyor. |
| "`loadtest/fleet.py` artık koşum makinesini esere yazıyor" | `README:30` | **YANILTICI (kod çöküyor)** | Aracı koşturdum — **3/3 koşumda çöktü**: `File "loadtest/fleet.py", line 331, in kosum_makinesi → NameError: name 'os' is not defined`. `os` dosyada **hiç import edilmemiş**. 120 saniyelik yük koşumu tamamlandıktan **sonra**, eser yazılırken çöküyor: **hiçbir çıktı üretilmiyor**. `git log -S` ile baktım: bu satır **HEAD commit'inde** (`467e99c`) eklenmiş. |
| "1.000 panoda görünme p95 **657 ms**, kayıp 0" | `README:30`, `docs/09:19` | **ÜRETİLEMEZ** | On eserin hiçbirinde 657 yok. Commit'li 1.000 panolu koşumlar: p95 **710,5** / **763,2** / **754,5** ms. 657, eseri depoda olmayan 13 Eylül i7 koşumundan geliyor. Koşum **koşulları** `docs/09` §2'de kayıtlı (bu iyi). |
| "Doymamış rejimde sayılar birebir tuttu (p50 385 → 385,5 ms)" | `README:30` | **ÖLÇTÜM (ve dürüst)** | Eserden doğruladım: 20 Eylül 1.000 panolu koşumda `visible p50 = 385,5`. **Proje yalnızca p50'nin tuttuğunu söylüyor, p95'in tuttuğunu iddia etmiyor** — doğru davranış. |
| Ham sonuçlar "**git dışı**" | `docs/09:5` | **İÇ TUTARSIZLIK** | Aynı dokümanın §4.1b'si "**commit'li**" diyor ve 7 esere bağlanıyor. İkisi bir arada duramaz; §1 başlığı bayat. |
| `gen_olcek_doc.py --check` tabloyu eserlerden üretir | `docs/09:98-102` | **ÖLÇTÜM** | `guncel` döndü; tablodaki yedi satırı eserlerden birebir doğruladım. **Bu mekanizma gerçek ve iyi.** |
| F-36: 86.400 → **50.932** (%41,0), 1.071 → **632 MB** | `README:30` | **ÜRETİLEMEZ (bayat eser)** | Varsayılanlarla 71 dk 35 s koşturdum: **50.612 (%41,4), 628,3 MB**. 307 alanın 93'ü farklı. Betiğin belirlenimli olduğunu kanıtladım (aynı parametrelerle iki koşumum birebir aynı **ve** 2 panolu eserle birebir aynı). Yani eser bayat: 18 Eylül'den sonra üreteç değişmiş. Bunu yakalayacak `--check` yok. |
| Doyma noktası ölçülmüş ve düzeneğe bağlı | `docs/09:26-29` | **ÖLÇTÜM (eserden)** | Eserler bunu destekliyor: 1.000 pano p95 ~0,76 s iken 3.000'de **7,36 s**, 5.000'de **42,9 s**, 10.000'de **55,9 s**. Kayıp her koşumda 0. Darboğaz da adlandırılmış (615 µs alımın 501 µs'i şema doğrulaması). |
| TimescaleDB sıkıştırması **46–48×**, segmentby `pano_id, tag` | `README:30` | **Politika: ÖLÇTÜM · oran: BEYAN** | Canlı DB'de doğruladım: `telemetry` hipertablosu `compression_enabled = t`, `segmentby pano_id(1), tag(2)`, `orderby ts DESC`. **Oranı ölçemedim** (bir günden eski parça gerekiyor); ölçümün kaynağı ve koşulu `005_compression.sql` başlığında yazılı. |
| "Gerileme" bulgusunun geri çekilmesi | `docs/09` §4.1c | **ÖLÇTÜM (lehine)** | Bölüm gerçekten var ve iki hatayı (düzeneğin doğrulanmaması, `written_per_s.p50`'nin tavan sanılması) kalem kalem düzeltiyor. **Sessizce değiştirmemişler.** |

**Gerekçe.** Çapamda iki kural vardı ve ikisi de burada tetikleniyor: *"manşet iddia
ÜRETİLEMEZ ise 7'nin üstüne çıkamaz"* ve *"YANILTICI bulgu varsa 5'in üstüne çıkamaz."*
Bu kriterde YANILTICI bulgu **kriterin kendi manşet tekrar-üretilebilirlik iddiasına**
değiyor: doküman "eseri açıp bakın" diyor, eserde o bilgi yok, ve onu yazacak kod çöküyor.
Ölçek çalışmasının kendisi (7 commit'li eser, 10.000 panoya kadar stres, darboğaz analizi,
sıkıştırma, geri çekme dürüstlüğü) **gerçekten güçlü** — bu iki kusur olmasaydı 8 verirdim.
Ama bir jüri üyesi bugün aracı koşarsa **elinde hiçbir şey kalmaz**. **5.**

---

### Kriter 7 — Kullanıcı / operasyon deneyimi → **8/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| **166 vitest testi, 19 dosya** | `README:31` | **ÖLÇTÜM** | `Test Files 19 passed (19) · Tests 166 passed (166)`, 56,03 s. |
| 7 ekran + NotFound gezilir, **0 konsol hatası / uyarısı** | `README:31` | **ÖLÇTÜM** | `npm run e2e`: **10/10 test geçti**, 10 rota, her birinde `0 hata, 0 uyari`. |
| Örnek veri kipinde **0 axe ihlali** | `README:31` | **ÖLÇTÜM** | `[AXE] ihlal yok`. |
| Kontrast **13,33:1** (`theme.css`) ve **12,59:1** (`industrial.css`) | `README:31` | **ÖLÇTÜM** | WCAG 2.1 bağıl parlaklık formülünü kendim uyguladım: `#202b34`/`#f5f6f8` → **13,3330**; `#182c44`/`#eef2f6` → **12,5909**. İkisi de AAA eşiği 7:1'in üstünde. `theme.test.ts:61,141` ikisini de kilitliyor. |
| "**Canlı kip bu teslimde yeniden ölçülmedi** — eski 23 rakamı… ölçmeden güncel diye yazılmıyor" | `README:31` | **ÖLÇTÜM — boşluğu ben kapattım** | `GRIDUP_E2E_KIP=canli` ile ölçtüm: **10 rotanın her birinde 2 ihlal, toplam 20**, hepsi `color-contrast (serious)`, iki bileşende: `.connection-pill` ve `.btn-link`. Konsol hatası canlı kipte de **0**. Testin kendi çıktısı "kilitlenmez" diyor: **bu ihlaller CI'yı düşürmüyor.** Eski 23 rakamı doğru mertebedeydi; proje ölçmediğini söylemekte haklıydı. |
| Ekranlar gerçekten dolu, boş çerçeve değil | `README:31` | **ÖLÇTÜM (görüntülere baktım)** | `assets/ekran/03-alarm-konsolu.png`: 8 alarm, öncelik rozetleri (Kritik/Alarm/Uyarı/Sistem), **Açık / Rafta / Tümü** süzgeçleri, "Onay bekliyor"/"Onaylandı" durumları, CSV vardiya raporu, alarm kartında `Dayanak: TVOC-2 PDU 222/223 sensor status, PDU 1300 hata biti`. `05-olay-analizi-kara-kutu.png`: olay öncesi 72 saat, K/K₀ ve ΔT çift eksen, faz akımları, çiy marjı, risk skoru, zaman çizelgesi, SVG dışa aktarım, "439 zaman noktası" klavyeyle erişilebilir tablo. |
| Arayüz kendi sınırını etiketliyor | — | **ÖLÇTÜM (lehine)** | Ekran görüntülerinde başlıkta **"DEMO ORTAMI · Örnek veriler gösteriliyor. Saha bağlantısı yok."** ve **"kimlik doğrulama kapalı"** yazıyor. Arayüz kendi durumunu jüriye saklamıyor. |
| Operasyon döngüsü: Neden / Ne doğrulanmalı / Ne yapmalı / Ne kadar acil | `README:31` | **ÖLÇTÜM** | Ekran görüntüsünde **üç** başlık görünüyor; dördüncüsü koşulludur: `AlarmNedeni.tsx:42-43` — *"Buna karşı-olgusal dördüncü blok eklenir: Ne doğrulanmalı? (hipotezin eksik kanıtı)"*, test `:31-36` dördünü de kilitliyor. İddia doğru, blok koşullu. |
| Planlanan 9 ekranın **7'si** çalışıyor; Ayarlar ve mobil PWA kapsam dışı | `README:31` | **ÖLÇTÜM (dürüstlük)** | e2e 7 ekranı + NotFound + 2 varyantı geziyor. Kapsam dışı bırakılanlar açıkça yazılı. |
| 1.000 panel sayfalanmış listelerle izlenir, **liste sanallaştırması kullanılmadı** | `README:30` | **BEYAN (dürüst)** | Kendi ölçmedim; projenin sınırı kendisi yazması lehinedir. |
| ISA-18.2 yaşam döngüsü | `README:31` | **BEYAN (kısmi)** | Ack/shelve uçları var ve yetkilendirmeyi doğruladım. Alarm seli (flood) yönetimi ve raf süresi politikasını koşarak sınamadım. |

**Gerekçe.** Çapamda 9/10 "ISA-18.2 uygulanmış, alarm oranı hedefi ölçülmüş, erişilebilirlik
ölçülmüş, denetim izi var" diyordu. Erişilebilirlik ölçülmüş ✔ (ve ben yeniden ölçtüm),
alarm oranı ölçülmüş ✔ (71,4/100/gün), denetim izi ✔ (hash zinciri). Eksik: ISA-18.2'nin
sel/bastırma tarafı, ve **canlı kipte 20 kontrast ihlali** — proje bunu bilmiyordu çünkü
ölçmemişti, ama şimdi ölçülmüş bir eksiktir. **8.**

---

### Kriter 8 — Maliyet ve fayda → **8/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| Pano Beyni **70,73 USD** (adet 1) / **47,68 USD** (adet 1.000) | `README:32` | **ÖLÇTÜM** | 17 satır kalemini `awk` ile kendim topladım: **70,73** ve **47,68**. Birebir. |
| Düğüm 23,25/13,95 · PD kartı 19,80/11,79 USD | `README:32` | **ÖLÇTÜM** | 11 ve 9 satır; birebir. |
| Pano başı **103,48 / 145,33 / 396,43** USD (4/7/25 düğüm) | `README:32` | **ÖLÇTÜM (elle de doğruladım)** | 47,68 + 4×13,95 = 103,48 ✔ · +7×13,95 = 145,33 ✔ · +25×13,95 = 396,43 ✔ |
| "Kurulum işçiliği, SIM/veri aboneliği ve tip test **hiçbir toplamda yoktur**" | `README:32` | **ÖLÇTÜM** | Betiğin çıktısı bu dört kalemi ayrı satırlarda `veri yok` ile listeliyor ve *"bu dört kalemin BOM satırı yok — docs/19 bölüm 3.1; adet olarak bile sayılamadılar"* diyor. Gizlemiyor. |
| "Betik bunları uydurmaz" | `README:32` | **ÖLÇTÜM (en güçlü dürüstlük kanıtı)** | Parametresiz koştum: **her eksik girdi için `veri yok`**, tazminat toplamı yok, geri ödeme yok. *"Yönetmeliğin eşikleri, dağıtım bedeli ve ortalama talep bu depoda yoktur; betik bunları uydurmaz."* Bir yarışma projesinin sayı **üretmemeyi** seçmesi nadirdir. |
| Üç varsayımın kaldıracı **birebir eşit (1,33×)** | `README:32` | **ÖLÇTÜM** | `--duyarlilik` çıktısı: `ariza_olasiligi_yil`, `ariza_basi_maliyet_usd`, `tespit_orani` → **1,33×**; `dugum_sayisi` → 0,67×. Çarpımsal model gereği; matematik doğru. |
| 4→25 düğüm geri ödemeyi **7,4 → 28,3 aya** taşır | `README:32` | **ÖLÇTÜM** | Tablo birebir üredi (7,4 / 10,4 / 28,3 ay). |
| Tarifenin kaldıracı üstten **1,00×** ile sınırlı; eşiğe mesafeninki **0,09×–3,57×** | `README:32` | **ÖLÇTÜM** | `docs/10` §7.4 tablosu **elle yazılmış** (üreteci yok), ama iki satırını komut satırından **birebir** yeniden ürettim: eşiğe yakın → `kesinti_sayisi 3,57×`, `esik_sayi 2,68`, `abone 1,00`, `dagitim_bedeli 0,11`; eşikten uzak → `abone 1,00`, `kesinti_saat 0,90`, `esik_saat 0,09`. |
| *"Sıralama değişmez"* iddiası **yanlıştı ve düzeltildi** | `README:32`, `docs/10` §7.4 | **ÖLÇTÜM (lehine)** | Düzeltme testin docstring'inde kayıtlı (`test_tazminat_maruziyeti.py:309-317`) ve test artık **örneği değil özelliği** kilitliyor. Testi koştum: `4 passed`. |
| Parametre dosyası üç sütunlu (değer/kaynak/güven) ve `isletmeci-doldurur` ise değer `null` olmak zorunda | `scripts/roi-ornek-parametreler.yaml:1-25` | **ÖLÇTÜM (okudum) + test kilitli** | Kural dosyada yazılı ve bir testle bağlanmış. Fayda varsayımları çıktıda `[varsayim]` diye etiketleniyor. |
| OPEX **12,85 GB → 7,58 GB**/pano/yıl | `README:32` | **ÜRETİLEMEZ (bayat)** | F-36 eserinden türüyor; o eser bugünkü koddan yeniden üretilmiyor (§3.5). |
| Fiyat tarihi / tedarikçi teklifi | `hardware/*/bom.csv` | **Eksik** | `tedarik_notu` sütunu var ama **fiyatın tarihi ve kaynağı yok**. Satın alma bakışı için gerçek bir boşluktur. |
| "Altı parametre setinde" vs "beş parametre setinde" | `docs/10:378` vs `:409` | **Küçük iç tutarsızlık** | Doküman tablosu 6 satır, test `MARUZIYET_SETLERI` 5 set. (Tablonun 2. ve 6. satırları aynı kaldıraçları veriyor.) Yanıltıcı değil, dikkatsizlik. |

**Gerekçe.** Çapamda 9/10 "parça numaralı, **tarihli**, adetli BOM + işçilik + yıllık
işletme gideri + kaynaklı fayda varsayımları + duyarlılık" istiyordu. Duyarlılık analizi
beklediğimin üstünde (yapısal kaldıraç sınırları, yanlış iddianın kaydı). Parça numaraları
ve adet kırılımı var. Ama **fiyat tarihi yok, işçilik yok, fayda varsayımları kaynaksız** —
proje bunların hepsini açıkça söylüyor, bu yüzden eksi değil tavan sınırı. **8.**

---

### Kriter 9 — Yenilikçilik → **9/10**

| İddia | Nerede yazıyor | Durum | Dayanak |
|---|---|---|---|
| "`ALM-K-WARN` 226,5. saatte, sabit 70 K'lı `ALM-THR-TERM-ALM` 399,0. saatte → **172,5 saat erken**" | `README:33` | **ÖLÇTÜM (kendim hesapladım)** | Depoda bu sayıyı üreten **betik yok**. Fikstürü (`data/fixtures/S1_loose_conn.csv`, 2.880 satır) ve sözleşme eşiklerini (`k_ratio_warn=1.3`, `term_rise_alarm_k=70`) okuyup kendim hesapladım: K/K₀>1,3 ilk aşım `2026-07-15T10:45`, 70 K ilk aşım `2026-07-22T15:15` → **172,5 saat**. Fikstür başlangıcından (`2026-07-06T00:15`) itibaren **226,5 h** ve **399,0 h**. Üçü de birebir. |
| Saf C çekirdeği, `malloc` yok, sabit bellek | `README:33` | **ÖLÇTÜM** | `firmware/core/` altında `malloc/calloc/realloc/free` çağrısı **yok** (yalnızca bunu belgeleyen bir yorum satırı var). |
| C ↔ Python ortak test vektöründe her adımda karşılaştırılıyor, **240 adım** | `README:33` | **ÖLÇTÜM** | `ctest -V`: `240 adim karsilastirildi | en buyuk goreli fark: K 1.362e-08, tau 1.419e-08 (tolerans 1e-06)`. |
| `double` **1,36e-08** · `float` **6,96e-06** (tolerans 1e-4) | `README:33` | **ÖLÇTÜM** | double `1.362e-08`; float `K 6.961e-06, tau 6.239e-06 (tolerans 1e-04)`. README ve `docs/17` **ikisi de doğru** — farklı derlemelerin toleranslarını veriyorlar. |
| `ctest` **5/5**, `-Wall -Wextra -Wpedantic` uyarısız | `README:270`, `docs/17:59` | **ÖLÇTÜM** | gcc 13.4.0 konteynerinde: double **5/5**, float **5/5**, derlemede **0 uyarı/hata**. |
| Nokta başına **384 B** (double) / **196 B** (float) → 25 nokta = 9,4 KB | `README:33` | **ÖLÇTÜM** | `sizeof(pano_rls_t)` ölçtüm: **384** ve **196** bayt. 25×384 = 9.600 B = 9,4 KB ✔ |
| RLS ile dinamik ısıl direnç öğrenimi, sabit eşik yerine | `detect.py` | **ÖLÇTÜM** | Matematik doğru; `K/K₀` oranını okuması sayesinde sabit kazanç uyumsuzluklarına dayanıklı (bunu projenin kendi analizi gösteriyor ve ben doğruladım). |
| Kenar ile merkez **kanıtlanmış biçimde** aynı algoritmayı koşar | `README:33` | **ÖLÇTÜM** | Ortak test vektörü gerçek; C ve Python her adımda karşılaştırılıyor. Kenar **gerçek MCU'da koşmadı** — proje bunu `docs/17:31`'de yazıyor. |
| Rakip karşılaştırması (Schneider / ABB / Siemens) | `docs/18` | **BEYAN** | Tabloyu okudum; `docs/18:66` karşılaştırmalı protokol listesinin **"doğrulanmadı"** olduğunu kendisi yazıyor. Rakip ürün özelliklerini bağımsız kontrol etmedim. |

**Gerekçe.** Çapamda 9/10: "hem farklı hem değerli; boşluğu kapatıyor, farkın neden önemli
olduğu **ölçülmüş** ve alternatifle karşılaştırılmış." Fark ölçülmüş (172,5 saat — ben
doğruladım), alternatif somut (sabit 70 K eşiği), değer açık (erken uyarı). Kenar/merkez
denklik kanıtı ayrıca sağlam bir mühendislik fikri. 10 vermedim çünkü fikrin kendisi
(kestirimci ısıl direnç izleme) literatürde bilinir; buradaki katkı uygulamanın titizliğidir.
**9.**

---

## 5. Kendi denetimimin sonucu

### 5.1 En yüksek üç puanımı çürütmeye çalıştım

**K5 = 9 (SCADA).** Bunu yanlış kılacak tek bulgu: *IEC 104'ün taklit bir yığın olması* —
yani sabit bayt döndüren bir sahte sunucu. Aradım: bilinmeyen tip 77 gönderdim (**COT 44
P/N=1**), bilinmeyen ortak adres gönderdim (**COT 46 P/N=1**), kumanda gönderdim
(**reddedildi**), saat senkronu gönderdim (**ACTCON**). Sahte bir yığın bu dört negatif
yolu ayırt edemez. Puan ayakta. **İkinci çürütme denemem tuttu ve puanı yukarı değil
yana taşıdı:** README'nin `round()` ifadesi kodla uyuşmuyor — bunu buldum, rapora yazdım,
ama `docs/03` doğru olduğu için kriteri düşürmedi.

**K9 = 9 (Yenilikçilik).** Bunu yanlış kılacak tek bulgu: *172,5 saatin kurgunun eseri
olması* — yani fikstürün alarmı zaten garantileyecek şekilde üretilmiş olması. Bunu tam
olarak çürütemem, çünkü fikstür sentetiktir. Ama şunu yaptım: sayıyı **projenin betiğiyle
değil kendi hesabımla** ve **sözleşmedeki eşiklerle** yeniden ürettim. Yani en azından
"sayı, yayımlanan eşiklerden ve yayımlanan veriden çıkıyor" doğrulandı. Kalan belirsizlik
(fikstürün kendisi) K2'de döngüsellik başlığı altında açıkça yazılıdır ve **projenin
kendisi de yazıyor**.

**K2 = 9 (Tespit).** Bunu yanlış kılacak tek bulgu: *S10–S13'ün aslında uyumsuz olmaması* —
yani "sınırı ölçtük" iddiasının gösteri olması. Aradım: dedektörün regresörünü okudum
(`phi=[dT, I²]`, iki serbestlik derecesi) ve dört uyumsuzluk teriminin dördünün de
dedektörde karşılığı olmadığını doğruladım. Ayrıca projenin **ilk denemesinin işe
yaramadığını** kendi kodunda kaydetmiş olması, gösteri olmadığının en güçlü işareti.
Puan ayakta.

### 5.2 Açık etiket sayımı

§4'teki dokuz kanıt defteri tablosunun satırlarını **saydırarak** çıkardım (bu bölümü ilk
yazdığımda sayıları hafızadan vermiştim ve yanlıştı — bkz. Ek B, madde 9):

| Etiket | Sayı | Durum |
|---|---:|---|
| **ÖLÇTÜM** | 73 | Kapatıldı — komutu ben koştum, çıktısı tabloda |
| **YANILTICI** | 5 | Kapatıldı (olumsuz sonuçla); §8'de ayrıca listelendi |
| **BEYAN** | 9 | Açık kaldı — makul, koşmadım |
| **ÜRETİLEMEZ** | 5 | Açık kaldı — 657 ms · 87 kontrol · F-36 manşetleri · OPEX 12,85→7,58 GB · uçtan uca gecikme |
| **DOĞRULANAMADI** | 1 | Gerçek saha verisi (yarışma kısıtı) |
| **Karma / diğer** | 3 | "Politika ÖLÇTÜM · oran BEYAN" (sıkıştırma) · iki iç tutarsızlık kaydı |
| **TOPLAM** | **96** | |

İzlediğim iddia: **96**. Kapattığım: **78** (73 ÖLÇTÜM + 5 YANILTICI) = **%81**.
Açık kalan: **18** (%19). Toplam tutuyor: 78 + 18 = 96.

§9'da ayrıca üç **DOĞRULANAMADI** kalemi daha var (sıkıştırma oranı, 10.000 pano tekrarı,
standart metinleri); bunlar defter satırı değil, kapsam notudur ve yukarıdaki sayıma
girmez.

Açık `BEYAN`ların hiçbiri bir kriterin manşet iddiası değil; hepsi ikincil (standart
metinleri, rakip karşılaştırması, ISA-18.2 sel yönetimi, kopma/yeniden bağlanma, CBS/OMS
uç içerikleri, liste sanallaştırması). `ÜRETİLEMEZ`lerin **dördü K6'da toplanıyor** ve
puanı belirleyen şey budur.

### 5.3 Çapa denetimi — **bir çapamı esnettim, itiraf ediyorum**

Ek A'daki kuralım şuydu: *"YANILTICI bulgu varsa ilgili kriter 5'in üstüne çıkamaz."*

**K1'de bu kuralı uygulamadım.** K1'de üç YANILTICI bulgu var ama kural harfiyen
uygulansaydı K1 = 5 olurdu; ben 7 verdim. Gerekçem: çapayı yazarken aklımdaki YANILTICI,
kriterin **manşet** iddiasının çürümesiydi ("donanımda doğrulandı" tipi). K1'deki üçü de
**ikincil doküman katmanı** hataları; kriterin manşet iddiası (kurumun verisini doğru
okumak) benim üç bağımsız ölçümümle **doğrulandı**. Kuralı şöyle inceltip uyguladım:
*manşet iddiaya değen YANILTICI → 5 tavanı; ikincil iddiaya değen → −2 puan.*

Bu bir esnetmedir ve saklamıyorum. Karşılaştırma için: **K6'da kuralı harfiyen uyguladım**,
çünkü oradaki YANILTICI tam olarak kriterin tekrar-üretilebilirlik manşetine değiyor.
İnceltmeyi hiç yapmasaydım K1=5 olurdu ve toplamlar A 7,67 / B 7,92 / C 7,50 olurdu —
**karar yine değişmezdi.**

Diğer çapalarım tuttu: "manşet ÜRETİLEMEZ ise 7 tavanı" (K6'da bağlayıcı oldu),
"yalnızca BEYAN'a dayanan kriter 6'yı geçemez" (hiçbir kriter bu durumda değildi),
"dürüstçe yapılmadı denmiş madde eksi yazılmaz" (K3, K4, K8'de defalarca uyguladım).

### 5.4 En az emek harcadığım kriter — **K3, ve ona geri döndüm**

İlk turda K3'ü çoğunlukla BOM ve STL üzerinden değerlendirmiştim; kurulum yordamını,
FMEA'yı ve standart listesini okumamıştım. Geri döndüm ve şunları buldum: beş güvenlik
kuralı şartname maddesine atıflı ve **doğru sırada**; **"AT sekonderi hiçbir koşulda açık
devre bırakılmaz"** uyarısı ayrı imza isteyen bir kontrol listesi maddesi (bir ADM/GDZ saha
ekibinin ilk soracağı şeylerden biri); ayrık çekirdekli sensör şartı; clearance/creepage
uyarısı; 7 günlük taban öğrenme kavramı; Ş×O×D=RÖS yöntemli FMEA; ve 20+ **alanına doğru**
standart (IEC 61439-1, 60664-1, 60529, 61000-6-5, 62271-200, 62682, 62974-1, ISO 13379-1/
13381-1). Bu inceleme K3'ü **6'dan 8'e** çıkardı. İlk puanım haksızdı; düzelttim.

---

## 6. En güçlü üç şey

1. **Dokümanın koda bağlanması mekanizması — ve çalışıyor.** Altı üreteç betiğini `--check`
   ile koştum: altısı da `guncel`. `scripts/validate.py` `docs/12`'nin tamamını 2,45 saniyede
   yeniden üretti ve **tek fark üretim zaman damgasıydı**. `check_contracts.py` kodda 18 uç
   bulup hepsinin sözleşmede olduğunu doğruladı. STL'i yeniden ürettim: **aynı SHA-256**.
   Bu, "doküman iddia eder, kod başka şey yapar" hastalığına karşı yapısal bir bağışıklıktır
   ve bu deponun en değerli mühendislik özelliğidir.

2. **Döngüselliği kendileri bulmuş, ölçmüş ve olumsuz sonucu yayımlamışlar.**
   `generator.py:140-158`: *"dedektör üreteci ile aynı ayrık denklemi çözdüğü sürece
   'duyarlılık 1,00' büyük ölçüde 'kestirici kendi ileri modelini ters çevirebiliyor'
   demektir."* Üstelik **başarısız ilk denemelerini silmemişler**: ilk uyumsuzluk terimleri
   çarpımsaldı ve tespiti hiç bozmadı, çünkü `k_ratio=(g·K)/(g·K₀)=K/K₀`'da kazanç
   sadeleşiyor — bunu yazıp terimleri yeniden kurmuşlar. Aynı dürüstlük prognoz tarafında
   da var: `docs/12` §4 kendi RUL tahmininin **kötü** olduğunu (koni içinde %5,2, CRA −5,12)
   yayımlıyor. Görev metni §8.7'nin "bulabileceğin en değerli bulgu" dediği şeyi, proje
   benden önce bulmuş.

3. **SCADA tarafı gerçek, ve bunu projenin kodunu kullanmadan kanıtladım.** Ham bayt yazan
   kendi IEC 60870-5-104 istemcimle: STARTDT el sıkışması, C_IC_NA_1 için COT 7→20→10 tam
   sırası, 139 ölçülen nokta (Modbus'un 139 adresiyle çakışıyor), saat senkronuna ACTCON,
   bilinmeyen tipe **COT 44 P/N=1**, bilinmeyen ortak adrese **COT 46**. Ve en önemlisi:
   `C_SC_NA_1` tek komutu **reddedildi** — "röle kumandası yoktur" güvenlik iddiası
   dokümanda değil, **telde** doğrulandı. Modbus tarafında 25 noktanın tamamı 3 ayrı
   koşumda REST ile farksız çıktı.

---

## 7. En zayıf üç şey

1. **Ölçek aracı bugün çöküyor ve doküman olmayan bir şeyi "açıp bakın" diyor.**
   `loadtest/fleet.py` 3/3 koşumda `NameError: name 'os' is not defined` (satır 331) ile
   düştü; `os` dosyada hiç import edilmemiş. 120 saniyelik yük koştuktan **sonra**, eseri
   yazarken çöküyor — yani **hiçbir çıktı kalmıyor**. Satır HEAD commit'inde eklenmiş.
   Aynı anda `docs/09` §4.1b *"Her eser artık koştuğu makineyi kendi içinde taşır… eseri
   açıp bakın"* diyor; **on eserin onunda da o blok yok.** Tekrar-üretilebilirlik açığını
   kapatmak için yazılan kod, hem açığı kapatmamış hem aracı bozmuş.

2. **Manşet sayıların bir kısmının eseri depoda yok, bir kısmı bayat.**
   "1.000 panoda p95 **657 ms**" — on eserin hiçbirinde yok (en yakınları 667,8/710,5/754,5/
   763,2). "IEC 104 = REST, **87 kontrol**" — eseri yok. F-36'nın manşetleri (**50.932**,
   %41,0, 632 MB) bugünkü koddan yeniden üretilmiyor: 71 dakikalık koşumum **50.612**,
   %41,4, 628,3 MB verdi ve 307 alanın 93'ü değişti. Betiğin belirlenimli olduğunu
   kanıtladım (iki koşumum birebir aynı), yani kusur betikte değil **esrin bayatlığında** —
   ve bunu yakalayacak bir `--check` yok. Üstelik betik commit'li eseri **sessizce üzerine
   yazıyor**; ben fark edip geri aldım.

3. **Jüriye bakan özet katmanı, projenin kendi derin dokümanlarının çürüttüğü fiziği
   taşıyor.** `docs/01:21` "TVOC-2 arkı **<1 ms'de kesiyor**" diyor; kataloğu kendim
   ayrıştırdım: *"From light detection to trip (contacts K4, K5, K6) **Approx. 1 ms**"* —
   yani yaklaşık, ve **açma kontağına kadar**, arkın sönmesine kadar değil. `docs/01:24`
   Paschen kısayolunu kullanıyor; `docs/05:366-370` aynı depoda o kısayolu *"eksiktir"*
   diye çürütüyor. `docs/05:199` "438 A'lık sıçramalar L-1'de işaretlenir" diyor; `quality.py`
   yalnızca sıcaklık üstünde iki kural işletiyor, **akım için hiçbir kural yok**. Derin
   dokümanlar doğru, özet yanlış — ve jüri özeti okur.

---

## 8. YANILTICI bulgular

> İddia ile kod/çıktı/kaynak belgenin **uyuşmadığı** yerler. Beş tane buldum.

| # | İddia (birebir) | Nerede | Gerçek | Nasıl ölçtüm | Ağırlık |
|---|---|---|---|---|---|
| **Y1** | "**Her eser artık koştuğu makineyi kendi içinde taşır** (`makine` bloğu: mantıksal CPU, Docker'ın gördüğü CPU/bellek, sürüm) — §3'teki düzenek tablosuna güvenmek zorunda değilsiniz, **eseri açıp bakın**." | `docs/09:103-105` | `loadtest/results/` altındaki **10 eserin 10'unda da** böyle bir blok yok. | Her JSON'da özyineli anahtar taraması (`makine/machine/cpu/platform/host/ncpu`) → hepsinde `YOK`. | **Ağır.** Paragrafın işaret ettiği tablo tam olarak o eserlere bağlanıyor; okuyucu açıp bakınca bulamıyor. |
| **Y2** | "`loadtest/fleet.py` **artık koşum makinesini esere yazıyor**, yani iki koşum bir daha sessizce farklı donanımda karşılaştırılamaz." | `README:30` | Kod **çöküyor**: `fleet.py:331 → NameError: name 'os' is not defined`. `os` dosyada hiç import edilmemiş. Eser hiç yazılmıyor. | 3 bağımsız koşum (120 s / 10 s / 10 s), üçü de aynı yerde düştü; çıktı dizini boş. `git log -S` → satır HEAD commit'inde. | **Ağır.** Kriterin ölçüm aracı bugün çalışmıyor. |
| **Y3** | "`İstenen Veriler.xlsx`'te 15 dakikada 438 A'lık sıçramalar var; **bunlar L0/L1'e girmeden burada işaretlenir**" / "**tam olarak bu katmanda ayıklanır**" | `docs/05:199-200`, `firmware/akis-diyagramlari/ana-dongu.md:81-82` | L-1 katmanının dört kuralının hepsi **sıcaklık** üstünde çalışıyor (`dq_max_rate_k_per_min` = 10,0 **K**/dk). Akım için depoda **hiçbir değişim-hızı kuralı yok**. | `quality.py:140-170` okudum: `point_quality()` yalnızca `t_c` karşılaştırıyor. Depo genelinde akım hız kuralı araması boş döndü. | **Orta-ağır.** Kurumun **kendi verisindeki** patolojiye verilen cevap yanlış; jüri tam bunu sorabilir. |
| **Y4** | "TVOC-2 zaten arkı **<1 ms'de kesiyor** (SIL-2)" | `docs/01:21`, `HACKATHON_ANALIZ_RAPORU.md:45,405` | Katalog: *"From light detection to trip (contacts K4, K5, K6) **Approx. 1 ms** (depends on light intensity)"*. (a) ~1 ms ≠ <1 ms; (b) bu süre **açma kontağına** kadardır, arkın sönmesine değil. SIL-2 doğru. | `Hackathon Verileri/tvoc.pdf`'i kendim ayrıştırıp ilgili satırı çıkardım. Projenin kendi `:293` satırı **doğru** yazıyor. | **Orta.** Fizik hatası, ama **rakibi güçlendiriyor** — kendi lehine değil. |
| **Y5** | "AG panoda PD nadir — havada **Paschen minimumu ~327 V**; 400 V sistemde pratikte beklenmez" | `docs/01:24-26`, `docs/14:132` | `docs/05:366-370` aynı depoda: *"o kısayol **eksiktir**: 400 V sistemde faz-faz tepe gerilimi √2×400 ≈ **566 V**'tur, yani 327 V'un üstündedir."* Doğru gerekçe geometriktir. | İki dokümanı karşılaştırdım; `docs/05` daha yeni ve kendi kısayolunu çürütüyor. | **Hafif-orta.** Sonuç doğru, gerekçe yanlış; özet katmanı güncellenmemiş. |

**YANILTICI sayılmayan, ama düzeltilmesi gereken üç nokta** (kasıt yok, doküman/kod
uyuşmazlığı ikincil):

- **README'nin `round()` kısaltması.** `README:136` *"Modbus register'ı = `round(REST × 10)`"*
  diyor. Kod `floor(x·10+0,5)` (**yarım yukarı**) kullanıyor (`encoder.py:353-361`) ve
  `docs/03:80` bunu **doğru** belgeliyor. Tam `x,x5` sınırında ikisi ayrışır: 55,05 →
  kod 551, `round()` 550. Bir koşumumda bu farkı gerçekten gördüm. README'yi izleyen bir
  SCADA entegratörü 0,1 °C sapma bulur.
- **`docs/09:5` "git dışı" vs `docs/09:98` "commit'li".** Aynı dokümanda iki zıt ifade.
- **Demo betiğinin konsol özeti.** S4 koşumunda `panosim` *"beklenenlerden 0/1 görünen:
  ALM-ARC-TRIP"* yazdı; oysa alarm **gerçekten** oluştu (API'de id=3, `notified:['sms']`).
  Kenar simülatörünün kendi özeti, sistemin durumuyla çelişiyor — jüri "çalışmadı" sanır.
- **`demo/senaryo/s4.sh:19`** *"telefonda **gerçek** SMS/WhatsApp"* diyor; kanal sanal
  modemdir. Aynı satır `sms-log.txt`'ye yönlendirdiği için okuyucu yanılmıyor, ama
  kelime README'nin kendi "sanal GSM modem — gerçek donanım değil" ifadesiyle çelişiyor.

---

## 9. Doğrulayamadıklarım

| Ne | Neden | Hangi puanı ne kadar etkileyebilir |
|---|---|---|
| **Gerçek donanımda hiçbir şey** | Donanım yok — **yarışmanın kısıtı**, projenin eksiği değil. Proje da "donanımda doğrulandı" **demiyor**. | Hiçbirini. Kural 3 gereği eksi yazmadım. K3 ve K9'un tavanını sınırlar ama puanı düşürmez. |
| **TimescaleDB 46–48× sıkıştırma oranı** | Oran bir günden eski parçalarda ölçülüyor; bir günlük veri biriktiremedim. Politikanın **etkin olduğunu** ölçtüm. | K6 ±0,5. Oran yanlış çıksa bile K6 zaten 5. |
| **657 ms'in doğruluğu** | Eseri depoda yok; i7 makinesi bende yok. Sayının **yanlış** olduğunu iddia etmiyorum — **denetlenemez** olduğunu söylüyorum. | K6 zaten bu yüzden 5. Eser eklenirse K6 → 7–8. |
| **10.000 panoya kadar tekrar** | 8 iş parçacıklı makinede anlamlı olmaz (§3②); ayrıca araç çöküyor. | K6'ya ek etki yok. |
| **Standart metinlerinin madde madde doğruluğu** | IEC/EN standart metinleri elimde yok. Atıfların **alanı** doğru; **içeriği** okumadım. | K3 ±1. Atıflar yanlış çıkarsa K3 → 7. |
| **Rakip ürün karşılaştırması (`docs/18`)** | Schneider/ABB/Siemens özelliklerini bağımsız kontrol etmedim. Proje listenin **"doğrulanmadı"** olduğunu kendisi yazıyor. | K9 ±0,5. |
| **ISA-18.2 alarm seli / raf süresi politikası** | Ack/shelve uçlarını doğruladım; sel senaryosunu koşmadım. | K7 ±0,5. |
| **MQTT kopma/yeniden bağlanma ve mTLS profili** | mTLS profili (`--profile mtls`) varsayılan kapalı; sertifika üretip ayrı bir tezgâh kurmadım. | K4 ±0,5. |
| **`docs/12` dışındaki senaryoların canlı yığında oynatılması** | Yalnızca S4'ü koştum. | K2 ±0,5. |

**Belirsizliğin toplam etkisi:** en kötü durumda A ortalaması 7,89 → ~7,4; en iyi durumda
→ ~8,2. **Hiçbir senaryoda karar değişmiyor.**

---

## 10. Jüri masasında sorulacak beş soru

> Beşinin de cevabı dokümanda **hazır değil**. İlk üçü ölçülmüş bir kusura, son ikisi
> ölçülmemiş bir riske dokunuyor.

1. **`loadtest/fleet.py` bu depoda çalışmıyor — `os` import edilmemiş ve araç eser yazarken
   çöküyor. `docs/09` §4.1b ise "her eser makineyi taşır, açıp bakın" diyor ama on eserin
   hiçbirinde o blok yok. Bu iki cümle aynı commit'te yazıldı. Ölçek iddialarınızı bugün,
   bu makinede, nasıl yeniden üretmemizi öneriyorsunuz?**

2. **`veri_butcesi.py`'yi varsayılanlarla koştum: yayımladığınız 50.932 yerine 50.612 çıktı
   ve 307 alanın 93'ü değişti. Betiğin belirlenimli olduğunu doğruladım — yani eser bayat.
   `gen_*.py --check` ailesi dokümanı esere göre denetliyor, ama **eseri koda göre**
   denetleyen bir şey yok. Bu boşluğu nasıl kapatırsınız, ve F-36 sayılarının hangisi
   bugün geçerli?**

3. **Kurumun `İstenen Veriler.xlsx` dosyasındaki 438 A'lık sıçramaların "L-1 veri kalitesi
   katmanında ayıklandığını" iki yerde yazmışsınız. `quality.py`'de akım için hiçbir
   değişim-hızı kuralı yok — dört kuralın dördü de sıcaklık üstünde. Bu sıçramalar sahada
   gelseydi sisteminiz ne yapardı, ve bu boşluğu kapatmak kaç satır?**

4. **Erken uyarınızın tamamı `K/K₀` oranına dayanıyor ve bu oranın gücü, uyumsuzluk sabit
   bir kazanç gibi davrandığında sadeleşmesinden geliyor — bunu kendiniz yazmışsınız.
   Peki `K₀`'ın kendisi yanlış öğrenilirse? 7 günlük taban öğrenme penceresinde pano zaten
   gevşek bir bağlantıyla çalışıyorsa, sistem o arızayı "normal" olarak dondurur. F-32
   akran karşılaştırmasını "kısmen" diye işaretlemişsiniz — bir ADM sahasında ilk 7 gün
   boyunca yanlış öğrenilmiş bir `K₀`'ı ne kadar sürede yakalar, ve bunu ölçtünüz mü?**

5. **Canlı kipte arayüzünüzde 20 WCAG kontrast ihlali ölçtüm (10 rotanın her birinde
   `.connection-pill` ve `.btn-link`), ve testiniz bunları raporlayıp **CI'yı kilitlemiyor**.
   Örnek veri kipinde 0, canlı kipte 20. Bir kontrol odasında operatörün gerçekten göreceği
   kip hangisi, ve neden kilitlenen kip o değil?**

---

## Ek A — Aşama 0'da yazdığım çapalar

> Aşağıdaki metin, depoya **hiçbir komut koşulmadan** (görev dosyası okunduktan hemen
> sonra) yazıldı ve değerlendirme boyunca **değiştirilmedi**. Aynen kopyalanmıştır.

### K1 — Problemin doğru anlaşılması
- **3/10:** Dağıtım şebekesi jenerik anlatılmış; OG/AG ayrımı, trafo/fider/pano hiyerarşisi, Türkiye dağıtım mevzuatı (EPDK/ADM/GDZ pratiği) yok. Problem "elektrikte arıza olur" seviyesinde. Hangi fiziksel büyüklüğün neden ölçüldüğü gerekçelendirilmemiş.
- **6/10:** Belirli bir arıza sınıfı (ör. gevşek klemens/ark/termal yükselme) doğru fizikle seçilmiş, ölçülecek büyüklük gerekçeli. Ama mevcut altyapıyla (var olan RTU, ayırıcı, OG hücre) ilişki yüzeysel; saha kısıtları listelenmiş ama sayısallaştırılmamış.
- **9/10:** Arıza mekanizması fiziksel modelle (ısıl zaman sabiti, ark imzası, harmonik) anlatılmış; ADM/GDZ'nin bugün ne kullandığı somut yazılmış; projenin nereye takıldığı tek cümlede net. Varsayımlar ayrı bir listede, her biri yanlışlanabilir biçimde.

### K2 — Anomali ve risk tespit başarısı
- **3/10:** Sabit eşik ("X derece üstü alarm") ya da isimsiz bir "AI modeli". Yanlış alarm oranı hiç konuşulmamış. Test verisi yok ya da yalnızca elle seçilmiş birkaç örnek.
- **6/10:** Dedektör çalışıyor, sentetik veri üstünde tespit oranı var. Ama yanlış alarm yükü (FP/gün/modül) verilmemiş ya da tek işletme noktasında verilmiş; ROC/PR eğrisi, eşik seçimi gerekçesi yok. Normal davranış modeli (mevsim/yük profili) zayıf.
- **9/10:** Etiketli veri kümesi üstünde TP/FP/FN sayıları, erken uyarı süresi dağılımı, birim başına yanlış alarm/gün, eşik seçiminin gerekçesi var. En önemlisi: üreteç ile dedektörün aynı denklemi çözüp çözmediği (döngüsellik) proje tarafından TARTIŞILMIŞ.

### K3 — Saha koşullarında uygulanabilirlik
- **3/10:** "Panoya takılır" denmiş. Gerilim/akım beslemesi, IP sınıfı, sıcaklık aralığı, EMC, yalıtım mesafesi, montajın enerjili mi kesintili mi yapılacağı yok.
- **6/10:** Muhafaza, besleme (ör. CT harvesting / yardımcı gerilim), sıcaklık aralığı ve montaj yordamı yazılmış; ilgili standartlar (IEC 61010, IP5x/6x, IEC 61850-3 iklim) anılmış. Ama hiçbiri doğrulanmamış, tedarikçi/parça numarası yok.
- **9/10:** Parça numaralı BOM, standart maddesine referanslı uygunluk iddiası, enerjili montaj için iş güvenliği yordamı, ömür/bakım periyodu, saha arıza modu (modül ölürse ne olur) yazılı. Hangi iddianın test edilmediği de açıkça yazılı.

### K4 — Uçtan uca sistem ve gerçek bildirim
- **3/10:** Mimari şeması var, kod yok ya da parçalar birbirine bağlanmıyor. "Bildirim gönderilir" denmiş, gönderen kod yok.
- **6/10:** Sensör(sim) → broker → backend → arayüz zinciri gerçekten koşuyor, alarm arayüzde görünüyor. Ama gerçek bir dış bildirim kanalı (SMS/push/e-posta) yok ya da yalnızca log'a yazıyor; uçtan uca gecikme ölçülmemiş.
- **9/10:** Tek komutla kalkan yığın; sensörden telefona kadar en az bir gerçek kanal çalışıyor ve uçtan uca gecikme ÖLÇÜLMÜŞ (p50/p95). Kopma/yeniden bağlanma, mesaj kaybı ve teslim garantisi (QoS) davranışı test edilmiş.

### K5 — Mevcut sistemlerle entegrasyon (SCADA)
- **3/10:** "SCADA'ya bağlanır" cümlesi. Protokol adı geçiyor ama register haritası, nokta listesi, adresleme yok.
- **6/10:** Çalışan bir Modbus (ya da IEC 104) sunucusu var, register haritası dokümante edilmiş. Ama veri tipleri/ölçekleme/endianness, kalite bayrakları, zaman damgası ve gerçek bir istemciyle (ör. modpoll / QTester104) uçtan uca okuma doğrulaması yok.
- **9/10:** Nokta listesi (adres, tip, ölçek, birim, kalite) tam; bir SCADA istemcisiyle okuma kanıtlanmış; IEC 60870-5-104 tarafında ASDU tipleri, COT, sahiplik/soruşturma (interrogation) davranışı ve saat senkronu ele alınmış. RTU senaryosu (mevcut RTU'nun yanına mı, yerine mi) net.

### K6 — Ölçeklenebilirlik
- **3/10:** "Ölçeklenir" iddiası, sayı yok.
- **6/10:** 100+ modül için bir yük testi koşulmuş, throughput verilmiş. Ama koşum koşulları (makine, çekirdek, veri kümesi, başlangıç durumu) kayıtlı değil; veri bütçesi (bayt/mesaj/gün, GSM maliyeti), saklama büyümesi ve darboğaz analizi yok.
- **9/10:** Ölçüm betiği depoda, koşum koşulları kayıtlı, en az iki koşum ve yayılım verilmiş; kaynak hesabı (CPU/RAM/disk/ağ) modül sayısına göre ölçekleniyor; darboğazın nerede olduğu ve hangi modül sayısında kırılacağı yazılı.

### K7 — Kullanıcı / operasyon deneyimi
- **3/10:** Birkaç ekran görüntüsü, alarm listesi. Onaylama (ack), susturma, önceliklendirme yok. Operatörün ne yapacağı belirsiz.
- **6/10:** Alarm yaşam döngüsü (aktif/onaylandı/kapandı) var, öncelik sınıfları var. ISA-18.2 anılmış ama uygulanmamış; alarm seli (flood) ve raf (shelving) yönetimi yok. Erişilebilirlik/kontrast konuşulmamış.
- **9/10:** ISA-18.2 yaşam döngüsü uygulanmış (shelve/suppress/ack, kayıtlı gerekçe), alarm oranı hedefi (ör. <1 alarm/10 dk/operatör) ölçülmüş, iş akışı ekip rolleriyle eşleşmiş, erişilebilirlik ölçülmüş (kontrast/klavye) ve denetim izi var.

### K8 — Maliyet ve fayda
- **3/10:** "Ucuz" denmiş, sayı yok.
- **6/10:** Birim maliyet ve kaba BOM var. Ama tedarikçi/fiyat tarihi yok, adet kırılımı (1/100/1000) yok, işletme maliyeti (GSM/bulut/bakım) ve geri dönüş hesabının girdileri (kesinti maliyeti, önlenen arıza sayısı) dayanaksız.
- **9/10:** Parça numaralı, tarihli, adetli BOM; kurulum işçiliği; yıllık işletme gideri; fayda tarafı kaynaklı varsayımlarla (ENS/kesinti maliyeti) hesaplanmış; duyarlılık analizi var (varsayım %50 yanılırsa geri dönüş ne olur).

### K9 — Yenilikçilik
- **3/10:** Piyasada hazır bulunan bir ürünün yeniden yapımı, farkı anlatılmamış.
- **6/10:** Bir fikir gerçekten farklı ama değeri gösterilmemiş; ya da değerli ama standart (ör. "IoT + dashboard").
- **9/10:** Hem farklı hem değerli: mevcut çözümlerin çözemediği somut bir boşluğu kapatıyor, farkın neden önemli olduğu ölçülmüş ve alternatifle karşılaştırılmış.

### Puanlama kuralı (önceden bağlandı)
- Bir kriterin manşet iddiası ÜRETİLEMEZ ise, o kriter 7'nin üstüne çıkamaz.
- YANILTICI bulgu varsa ilgili kriter 5'in üstüne çıkamaz.
- Yalnızca BEYAN'a dayanan bir kriter 6'nın üstüne çıkamaz.
- Dürüstçe "yapılmadı" denmiş bir madde eksi yazılmaz; yalnızca tavanı sınırlar.

---

## Ek B — Değerlendirme sırasında kendi yaptığım hatalar

1. **Firmware testini yanlış kurup projeye yazacaktım.** İlk koşumda konteynere yalnızca
   `firmware/` dizinini bağladım; `rls_matches_python` testi `/src/../data/fixtures/
   rls_vectors.csv` bulamayıp düştü. **Bu benim hatamdı**, projenin değil. Depoyu doğru
   bağlayınca 5/5 geçti. Bir "1/5 düştü" bulgusu yayımlamaya çok yaklaştım.

2. **Üç protokol karşılaştırmasında yanlış yuvarlama kullandım.** Kendi betiğimde
   `round(REST/scale)` (Python'un bankacı yuvarlaması) kullandım; backend `floor(x·10+0,5)`
   (yarım yukarı) kullanıyor. İlk koşumumdaki tek farkı (`DSYA6_L1`) önce "1 LSB sapma
   bulgusu" sandım. Kodu okuyup sebebini bulana kadar bulgu olarak yazmadım. Sonuçta
   **gerçek bulgu benim hatamın içinden çıktı**: README'nin `round()` ifadesi kodla
   uyuşmuyor (`docs/03` doğru). Yani hata bendeydi, ama README'de de bir imprecision vardı.

3. **Canlı veritabanını kendim kirlettim ve bir an "zincir kopuk" bulgusu sandım.**
   README'nin tarifiyle `TEST_DB_DSN`'i **canlı** demo veritabanına yöneltip 933 testi
   koştum. `test_verify_journal.py` kütüğü bilerek bozuyor. Sonra `verify_journal.py`
   çalıştırınca `ZINCIR KOPUK` gördüm ve bir an bunu projenin kusuru sandım. Testin
   kaynağını okuyup **bulaşmanın bende olduğunu** anladım; yığını `down -v` ile sıfırlayıp
   zinciri temiz ölçtüm (sağlam çıktı). Bu hatadan **gerçek bir ikincil bulgu** çıktı:
   belgelenen tarif demo veritabanını siliyor ve denetim izini kurcalanmış bırakıyor,
   README bunu uyarmıyor.

4. **`generate_stl.py`'yi `--help` ile çağırdım, betik bayrağı yok sayıp dosyayı yeniden
   üretti.** Depoyu istemeden değiştirdim. `git status` ile kontrol ettim: **dosya bayt bayt
   aynıydı** (aynı SHA-256), yani kaza bir tekrar-üretilebilirlik kanıtına dönüştü. Yine de
   bu benim dikkatsizliğimdi.

5. **`veri_butcesi.py` commit'li eseri üzerine yazdı, fark edip geri aldım.** Betiğin
   `--out` bayrağını önceden kontrol etmeden varsayılanlarla koştum. `git diff`'i kanıt
   olarak sakladıktan sonra `git checkout` ile eseri geri aldım. (Betiğin bu davranışı
   ayrıca bir bulgudur ve §7'de yazılıdır.)

6. **Playwright e2e koşumu sekiz ekran görüntüsünü yeniden üretti.** `assets/ekran/*.png`
   değişti; kanıt olarak inceledikten sonra `git checkout` ile geri aldım.

7. **README ile `docs/17` arasında olmayan bir tutarsızlık gördüm.** README `float`
   toleransını 1e-4, `docs/17` `double` toleransını 1e-6 diyor; bunu bir an çelişki sandım.
   `ctest -V` çıktısını görünce **ikisinin de doğru** olduğunu, farklı derlemelerden
   bahsettiklerini anladım. Rapora yanlış bir bulgu girmedi.

8. **Alt-ajan taramasının sonuçlarını kanıt saymadım.** Dokuz kriter için paralel bir
   statik tarama koşturdum; 51 ajandan 21'i tamamlandı, 30'u oturum sınırına takıldı.
   Bu taramanın çıktılarını **yalnızca ipucu** olarak kullandım ve rapora giren her
   bulguyu (438 A, TVOC-2 süresi, Paschen, `devices.py:223`) **kendim yeniden doğruladım**.
   Doğrulanmayan hiçbir alt-ajan iddiası bu rapora girmedi.

9. **Kendi etiket sayımımı hafızadan yazdım ve yanlış çıktı.** §5.2'yi ilk yazdığımda
   "ÖLÇTÜM 62 / BEYAN 11 / ÜRETİLEMEZ 6 / DOĞRULANAMADI 3, toplam 87" demiştim. Sonra
   defter tablolarının satırlarını **saydırdım**: gerçek sayılar 73 / 9 / 5 / 1 (+5
   YANILTICI, +3 karma), toplam **96**. Yani kapanma oranını %71 diye yazmışım, doğrusu
   **%81**. Kendi raporumda, projeden istediğim şeyin tam tersini yapmışım: bir sayıyı
   üreten işlemi koşmadan yazmışım. Düzelttim ve buraya kaydediyorum.

10. **FMEA'yı "ince" diye yazdım — iki dosyanın yalnızca birini saymışım.** K3 defterinde
    "tablo yalnızca ~5 satır, bir saha cihazı için ince" demiştim. `docs/07`'nin başlığı
    (satır 3-5) bölünmeyi açıkça anlatıyor: donanım/saha satırları **1, 2, 3, 9, 10** orada,
    yazılım/sistem satırları **4–8 ve 11–14** `docs/07b`'de. Toplam **14 arıza modu**.
    `docs/07b`'yi okuduğumu §4'te yazmıştım ama satırlarını saymamışım; numaralandırmadaki
    boşluğu (1,2,3,9,10) "eksik tablo" sanmışım. Defter satırını düzelttim. K3 puanı
    değişmiyor (8) — o puan zaten esas olarak fiziksel doğrulamanın yokluğuyla sınırlıydı,
    FMEA derinliğiyle değil; ama gerekçedeki bu cümle yanlıştı.

**Değerlendirme bitiminde depo durumu:** `git status` → yalnızca `DEGERLENDIRME-GOREVI.md`
izlenmiyor. Yaptığım hiçbir değişiklik depoda kalmadı.
