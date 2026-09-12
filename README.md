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

---

## Beklenen teknik çıktılar → nerede

*(Kişi C Faz 4'te doldurur — T4.5)*

| # | Final sunumunda istenen | Nerede | Durum |
|---|---|---|---|
| 1 | Fiziksel modül veya çalışan prototip | `hardware/`, `firmware/` | ⏳ |
| 2 | Uçtan uca veri akışı | `sim/` → `backend/` → `frontend/` | ⏳ |
| 3 | Monitoring / SCADA ekranları | `frontend/`, `deploy/grafana/` | ⏳ |
| 4 | Örnek normal ve anormal çalışma senaryoları | `data/fixtures/`, `demo/senaryo/` | ⏳ |
| 5 | Alarm oluşması ve bildirim mekanizması | `backend/app/alarm_manager.py`, `backend/app/notify/` | ⏳ |
| 6 | Sistem mimarisi | `docs/02-mimari.md` | ⏳ |
| 7 | Gerçek saha uygulaması ve ölçeklendirme | `docs/08-kurulum-proseduru.md`, `docs/09-olceklenebilirlik.md` | ⏳ |

---

## Repo haritası

| Dizin | Sahip | İçerik |
|---|---|---|
| `contracts/` | **kilitli bölge** | MQTT şeması, Modbus haritası, alarm kodları ve eşikler, OpenAPI, senaryo etiketleri |
| `libs/panoalgo/` | A | Fizik ve tespit algoritmaları (Python), sentetik veri üreteci |
| `firmware/` | A | Taşınabilir C çekirdeği (host'ta koşar) + akış diyagramları |
| `sim/` | A | Veri üreteci yayıncısı, MPR-53CS ve TVOC-2 Modbus simülatörleri |
| `data/` | A | Etiketli senaryo fixture'ları |
| `backend/` | B | Ingestion, risk motoru, alarm yöneticisi, bildirim, SCADA ağ geçidi |
| `deploy/` | B | Docker Compose, veritabanı şeması, Grafana |
| `loadtest/` | B | 1.000 pano yük testi |
| `frontend/` | C | Operasyon arayüzü, dijital ikiz |
| `hardware/` | C | KiCad şeması, I/O, BOM, yerleşim, mekanik |
| `demo/` | C | Senaryo betikleri, sunum, video |
| `docs/` | dosya başına tek sahip | Jüriye teslim edilecek 17 doküman |

**Yol haritası, faz planı ve çalışma kuralları: [`PLAN.md`](PLAN.md)** · **Teknik analiz: [`HACKATHON_ANALIZ_RAPORU.md`](HACKATHON_ANALIZ_RAPORU.md)**

---

## Ekip

| Kulvar | Kişi | Alan |
|---|---|---|
| A | *(atanacak)* | Fizik, Kenar, Algoritma |
| B | *(atanacak)* | Platform, Entegrasyon, Ölçek |
| C | *(atanacak)* | Arayüz, Donanım Tasarımı, Teslim |
