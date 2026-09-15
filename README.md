# Pano/Hücre İçi Anomali Erken Uyarı Sistemi

**Grid Up Hackathon 2026** · ADM Elektrik & GDZ Elektrik · Patika.dev

1600 kVA'lık TEDAŞ tipi AG dağıtım panolarına kablo kalabalığını artırmadan eklenebilen, mevcut enerji analizörü ve ark korumasını da sensör olarak kullanan, **fizik tabanlı öngörücü uyarı** üreten, tamamı şirket içinde (on-premise) çalışan düşük maliyetli izleme platformu.

> **Gizlilik:** Bu repo **private** kalmalıdır. `Hackathon Verileri/` ve proje konusu PDF'i "Hizmete Özel | Restricted" etiketlidir; sosyal medyada, public demo videolarında veya public bir repoda paylaşılmaz.

---

## Hızlı başlangıç

```bash
git clone <repo>
cd griduphackathon
cp deploy/.env.example deploy/.env        # doldurmak zorunda değilsiniz; varsayılanlarla çalışır
docker compose -f deploy/compose.yaml up -d --build
```

| Arayüz | Adres | Ne için |
|---|---|---|
| Operasyon arayüzü | <http://localhost:3000> | Kontrol odası ekranları |
| API dokümanı | <http://localhost:8000/docs> | Uç noktalar (sözleşme: `contracts/openapi.yaml`) |
| Grafana | <http://localhost:3001> | Mühendislik görünümü, ölçek panoları |
| MQTT broker | `localhost:1883` | Kenar → merkez telemetri |

Durdurma: `docker compose -f deploy/compose.yaml down` · sıfırlama: `down -v`

**Arıza senaryolarını canlı oynatma** (yığın ayaktayken):

```bash
./demo/senaryo/s1.sh     # gevşek bağlantı: K/K₀ sabit 70 K eşiğinden çok önce uyarır
./demo/senaryo/s2.sh     # aşırı yük: "arıza değil" — yanlış alarm önleme
./demo/senaryo/s4.sh     # ark olayı: P1, telefona SMS/WhatsApp, kara kutu
```

Ayrıntı ve senaryo listesi: [`demo/senaryo/README.md`](demo/senaryo/README.md)

**Backend/frontend'i Docker olmadan denemek** (ör. bu ortamda olduğu gibi Docker yoksa):
`cd frontend && npm run dev:mock` — örnek veriyle, backend'e bağlı olmadan tüm operasyon
arayüzünü açar (üstte "örnek veriyle çalışıyor" şeridiyle açıkça işaretli).

---

## Beklenen teknik çıktılar → nerede

| # | Final sunumunda istenen | Nerede | Durum |
|---|---|---|---|
| 1 | Fiziksel modül veya çalışan prototip | `hardware/pano-beyni/`, `hardware/yerlesim/`, `hardware/mekanik/`; `firmware/` | ⚠️ Donanım tasarımı tamam (blok diyagram+I/O+BOM+yerleşim, `hardware/pano-beyni/README.md`'de KiCad yerine bu üçlünün seçilme gerekçesi); taşınabilir C çekirdeği host'ta koşuyor ve `ctest` yeşil (`double` ve `float` derlemede 5/5), ama **hedef MCU üzerinde çalıştırılmadı** |
| 2 | Uçtan uca veri akışı | `sim/` → `backend/` → `frontend/` | ✅ Canlı yığında uçtan uca doğrulandı: `panosim` → mosquitto → ingest → TimescaleDB → API → arayüz; karantina 0, kenar alanları (`k_ratio`, `risk`, `q`) pano detayına ulaşıyor |
| 3 | Monitoring / SCADA ekranları | `frontend/src/pages/` (7/9 ekran ✅), `deploy/grafana/` (✅), `backend/app/scada/` (Modbus TCP + IEC 104, ✅) | ✅ |
| 4 | Örnek normal ve anormal çalışma senaryoları | `demo/senaryo/s0–s8.sh` (hepsi çalışır); `data/fixtures/` (10 etiketli senaryo + etiketler); `frontend/src/api/mock.ts` | ✅ `s0`–`s6` etiketli senaryoları gerçek yığına canlı oynatır (`panosim --scenario`); oynatılan fizik `docs/12`'yi üreten fiziğin birebir aynısıdır |
| 5 | Alarm oluşması ve bildirim mekanizması | `backend/app/alarm_manager.py`, `backend/app/notify/` (✅, 152 test), `frontend/src/pages/AlarmKonsolu.tsx` (✅) | ✅ |
| 6 | Sistem mimarisi | `docs/02-mimari.md` | ✅ |
| 7 | Gerçek saha uygulaması ve ölçeklendirme | `docs/08-kurulum-proseduru.md`, `docs/09-olceklenebilirlik.md`, `docs/13-donanim-tasarimi.md` | ✅ |

**Bilinçli sınırlar** (sunumda da böyle anlatılır, ayrıntı: `docs/17`):
donanım satın alınmadı — ölçüm uçları fizik tabanlı veri üreteciyle simüle edilir, merkez
yazılımı ise sahadakiyle **aynı koddur**; 9 arayüz ekranının 7'si yapıldı (mobil PWA ve
devreye alma sihirbazı bilinçli olarak kapsam dışı); KiCad şeması yerine blok diyagram +
I/O tablosu + BOM üçlüsü seçildi (gerekçe: `hardware/pano-beyni/README.md`); demo yığını
kimlik doğrulamasızdır ve üretim farkları `docs/15` §5'te listelidir.

---

## Repo haritası

| Dizin | Sahip | İçerik |
|---|---|---|
| `contracts/` | **kilitli bölge** | MQTT şeması, Modbus haritası, alarm kodları ve eşikler, OpenAPI, senaryo etiketleri |
| `libs/panoalgo/` | A | Fizik ve tespit algoritmaları (Python), sentetik veri üreteci, senaryo seti |
| `firmware/` | A | Taşınabilir C çekirdeği (host'ta koşar) + akış diyagramları |
| `sim/` | A | Veri üreteci yayıncısı (senaryo oynatma dahil), MPR-53CS ve TVOC-2 Modbus simülatörleri |
| `data/` | A | Etiketli senaryo fixture'ları (S0–S9) ve RLS test vektörleri |
| `backend/` | B | Ingestion, risk motoru, alarm yöneticisi, bildirim, SCADA ağ geçidi (Modbus TCP + IEC 104) |
| `deploy/` | B | Docker Compose, veritabanı şeması, Grafana |
| `loadtest/` | B | 1.000 pano yük testi (`fleet.py`, gerçek CLI, `demo/senaryo/s7.sh` bunu kullanır) |
| `frontend/` | C | Operasyon arayüzü (7 ekran), dijital ikiz — bkz. `frontend/README.md` |
| `hardware/` | C | Blok diyagramı + I/O tablosu + BOM (`pano-beyni/`), yerleşim (`yerlesim/`), mekanik (`mekanik/`) |
| `demo/` | C | Senaryo betikleri (`senaryo/`), sunum (`sunum/`), video (`video/`) |
| `docs/` | dosya başına tek sahip | Jüriye teslim edilecek **18 doküman** (01–17 + 07b), tamamı hazır |

---

## Nasıl doğrularsınız

```bash
cd libs/panoalgo && pytest                              # 331 test — fizik, tespit, senaryolar
cd backend && pytest                                    # 583 test (+22 gerçek TimescaleDB ile)
cd sim && pytest                                        # 21 test — simülatörler, senaryo oynatma
cd frontend && npm ci && npm test && npm run build      # 71 test + üretim derlemesi
cmake -S firmware -B build && cmake --build build && ctest --test-dir build   # C çekirdeği
```

İki iddia betikle yeniden üretilebilir — rapordaki sayılar elle yazılmadı:

```bash
python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures   # 10 etiketli senaryo
python scripts/validate.py --out docs/12-dogrulama-sonuclari.md      # doğrulama tablosu
```

Neyin gerçek, neyin simüle olduğunun tek tek dökümü:
[`docs/17-donanimsiz-dogrulama.md`](docs/17-donanimsiz-dogrulama.md)

---

**Yol haritası, faz planı ve çalışma kuralları: [`PLAN.md`](PLAN.md)** · **Teknik analiz: [`HACKATHON_ANALIZ_RAPORU.md`](HACKATHON_ANALIZ_RAPORU.md)** · **Kişi C'nin oturum durumu: [`STATUS.md`](STATUS.md)**

---

## Ekip

| Kulvar | Kişi | Alan |
|---|---|---|
| A | Tuna | Fizik, Kenar, Algoritma |
| B | Ahmet | Platform, Entegrasyon, Ölçek |
| C | Berke | Arayüz, Donanım Tasarımı, Teslim |
