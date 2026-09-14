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

**Backend/frontend'i Docker olmadan denemek** (ör. bu ortamda olduğu gibi Docker yoksa):
`cd frontend && npm run dev:mock` — örnek veriyle, backend'e bağlı olmadan tüm operasyon
arayüzünü açar (üstte "örnek veriyle çalışıyor" şeridiyle açıkça işaretli).

---

## Beklenen teknik çıktılar → nerede

| # | Final sunumunda istenen | Nerede | Durum |
|---|---|---|---|
| 1 | Fiziksel modül veya çalışan prototip | `hardware/pano-beyni/`, `hardware/yerlesim/`, `hardware/mekanik/`; `firmware/` (Kişi A, henüz başlamadı) | ⚠️ Donanım tasarımı tamam (blok diyagram+I/O+BOM+yerleşim, `hardware/pano-beyni/README.md`'de KiCad yerine bu üçlünün seçilme gerekçesi); firmware bekliyor |
| 2 | Uçtan uca veri akışı | `sim/` (Kişi A, henüz başlamadı) → `backend/` (Kişi B, ✅) → `frontend/` (✅) | ⚠️ Backend+frontend hazır; sentetik veri üreteci/simülatörler eksik, bu yüzden gerçek yığında uçtan uca henüz gösterilemiyor |
| 3 | Monitoring / SCADA ekranları | `frontend/src/pages/` (7/9 ekran ✅), `deploy/grafana/` (✅), `backend/app/scada/` (Modbus TCP + IEC 104, ✅) | ✅ |
| 4 | Örnek normal ve anormal çalışma senaryoları | `demo/senaryo/s0–s8.sh` (yazıldı; s0–s6 A'nın simülatörünü bekliyor, s7–s8 çalışır); `frontend/src/api/mock.ts` (9 senaryo, bugün çalışır) | ⚠️ Örnek-veri modunda tüm senaryolar canlı gösterilebiliyor; gerçek yığında A'nın işi bekleniyor |
| 5 | Alarm oluşması ve bildirim mekanizması | `backend/app/alarm_manager.py`, `backend/app/notify/` (✅, 152 test), `frontend/src/pages/AlarmKonsolu.tsx` (✅) | ✅ |
| 6 | Sistem mimarisi | `docs/02-mimari.md` | ✅ |
| 7 | Gerçek saha uygulaması ve ölçeklendirme | `docs/08-kurulum-proseduru.md`, `docs/09-olceklenebilirlik.md`, `docs/13-donanim-tasarimi.md` | ✅ |

**En büyük açık risk:** Kişi A'nın kulvarı (`libs/panoalgo/`, `firmware/`, `sim/panosim.py`,
`mpr53cs_sim.py`, `tvoc2_sim.py`, `docs/05`, `docs/12`) bu yazının yazıldığı an (14 Eylül) henüz
başlamamış görünüyor. B ve C kulvarları (backend, SCADA ağ geçidi, frontend, donanım tasarımı,
teslim dokümanları) tamamlandı ve örnek veriyle uçtan uca çalışıyor; **gerçek fizik tabanlı
sentetik veri ve firmware olmadan uçtan uca "canlı yığın" demosu eksik kalır.** Özellik dondurma
17 Eylül 23:59 — bu risk PLAN.md Bölüm F'ye ve `STATUS.md`'ye işlendi.

---

## Repo haritası

| Dizin | Sahip | İçerik |
|---|---|---|
| `contracts/` | **kilitli bölge** | MQTT şeması, Modbus haritası, alarm kodları ve eşikler, OpenAPI, senaryo etiketleri |
| `libs/panoalgo/` | A | Fizik ve tespit algoritmaları (Python), sentetik veri üreteci — *henüz yok* |
| `firmware/` | A | Taşınabilir C çekirdeği (host'ta koşar) + akış diyagramları — *henüz yok* |
| `sim/` | A | Veri üreteci yayıncısı, MPR-53CS ve TVOC-2 Modbus simülatörleri — *henüz yok* |
| `data/` | A | Etiketli senaryo fixture'ları — *henüz yok* |
| `backend/` | B | Ingestion, risk motoru, alarm yöneticisi, bildirim, SCADA ağ geçidi (Modbus TCP + IEC 104) |
| `deploy/` | B | Docker Compose, veritabanı şeması, Grafana |
| `loadtest/` | B | 1.000 pano yük testi (`fleet.py`, gerçek CLI, `demo/senaryo/s7.sh` bunu kullanır) |
| `frontend/` | C | Operasyon arayüzü (7 ekran), dijital ikiz — bkz. `frontend/README.md` |
| `hardware/` | C | Blok diyagramı + I/O tablosu + BOM (`pano-beyni/`), yerleşim (`yerlesim/`), mekanik (`mekanik/`) |
| `demo/` | C | Senaryo betikleri (`senaryo/`), sunum (`sunum/`), video (`video/`) |
| `docs/` | dosya başına tek sahip | Jüriye teslim edilecek 17 dokümandan **15'i hazır** (`docs/05`, `docs/12` — A bekliyor) |

**Yol haritası, faz planı ve çalışma kuralları: [`PLAN.md`](PLAN.md)** · **Teknik analiz: [`HACKATHON_ANALIZ_RAPORU.md`](HACKATHON_ANALIZ_RAPORU.md)** · **Kişi C'nin oturum durumu: [`STATUS.md`](STATUS.md)**

---

## Ekip

| Kulvar | Kişi | Alan |
|---|---|---|
| A | Tuna | Fizik, Kenar, Algoritma |
| B | Ahmet | Platform, Entegrasyon, Ölçek |
| C | Berke | Arayüz, Donanım Tasarımı, Teslim |
