# Pano/Hücre İçi Anomali Erken Uyarı Sistemi

**Grid Up Hackathon 2026** · ADM Elektrik & GDZ Elektrik · Patika.dev

1600 kVA'lık TEDAŞ tipi AG dağıtım panolarına kablo kalabalığını artırmadan eklenebilen, mevcut enerji analizörü ve ark korumasını da sensör olarak kullanan, **fizik tabanlı öngörücü uyarı** üreten, tamamı şirket içinde (on-premise) çalışan düşük maliyetli izleme platformu.

> **Gizlilik:** Bu repo **private** kalmalıdır. `Hackathon Verileri/` ve proje konusu PDF'i "Hizmete Özel | Restricted" etiketlidir; sosyal medyada, public demo videolarında veya public bir repoda paylaşılmaz.

---

## Jüri kanıt haritası

Dokuz değerlendirme kriteri → kanıt dosyası → o dosyada **ölçülmüş** sayı.

| # | Kriter | Kanıt dosyası | Ölçülmüş sayı |
|---|---|---|---|
| 1 | Problemin doğru anlaşılması | `docs/01-problem-analizi.md` · `docs/05-anomali-tespiti.md` §11 | Eşik sabitken aynı sağlıklı senaryoda çiy olayı kış **28,6** · geçiş **71,4** · yaz **0,0** olay/100 pano/gün (§11.4, `scripts/threshold_sweep.py --seasons`) — sorun eşik seçimi değil, panonun fiziği ve mevsimi. Aleyhimize çıkan ölçüm aynı taramada: eşiği **kısmak** yükü azaltmıyor, artırıyor — 1,0/0,0 çifti **171,4**, 0,5/0,0 çifti **228,6** olay/100 pano/gün, yani 150 bütçesini aşıyor (§11.3 ve §11.5). |
| 2 | Anomali ve risk tespit başarısı | `docs/12-dogrulama-sonuclari.md` §1–§2 | Beklenen alarmı olan 8 senaryonun hepsinde duyarlılık **1,00**, yasaklı alarm 10 senaryonun hiçbirinde yok; S1'de sabit 70 K eşiğinden **209,0 saat (8,7 gün)** önce uyarı. |
| 3 | Saha koşullarında uygulanabilirlik | `docs/12` §3 · `docs/08-kurulum-proseduru.md` · `docs/13-donanim-tasarimi.md` · `docs/19-tedas-sartname-uyumu.md` | Sağlıklı panoda operatör yükü **71,4** yanlış alarm/100 pano/gün (sözleşme hedefi 150, üst sınır 300); donanım satın alınmadı, tip testi yapılmadı (`docs/17` §6). |
| 4 | Uçtan uca sistem | `docs/17-donanimsiz-dogrulama.md` §4.2 · `docs/09-olceklenebilirlik.md` §4.3 | `panosim` → MQTT → ingest → TimescaleDB → API → arayüz canlı yığında koştu, **karantina 0**; alarm → SMS'te sensör anından **sanal modemin kabulüne** p95 **606 ms** (1.000 pano yükü altında; gerçek şebekede operatörün teslim süresi bunun üstüne eklenir — `docs/09` §4.3). |
| 5 | Mevcut sistemlerle entegrasyon | `docs/04-iec104-haritasi.md` §9 · `docs/17` §4.2 (nokta sayısı ve fark) · `docs/03-modbus-haritasi.md` §14 (canlı okuma kaydı) | IEC 104 = REST API (**87 kontrol**) = Modbus FC03 (**139 adres**), **0 fark**; `conn_temp` 25 noktanın tamamında Modbus değeri = API × 10, fark 0. |
| 6 | Ölçeklenebilirlik | `docs/09-olceklenebilirlik.md` §4–§5 | 1.000 panoda görünme p95 **657 ms**, kayıp **0**; 10.000 panoda veri kaybı yok ama sistem doyuyor ve darboğaz ölçüldü (mesaj başına 615 µs'in **501 µs**'i şema doğrulaması), depolama sıkıştırması **46–48×**. |
| 7 | Kullanıcı / operasyon deneyimi | `docs/16-ux-tasarim.md` · `frontend/` | 9 ekranın 7'si gerçek API ile Playwright'ta gezildi, **0 konsol hatası**; **85** frontend testi ve `tsc --noEmit` **0 hata**; gövde metni `--ink` #1f2224 / zemin `--bg` #ffffff → kontrast **16,0:1** (güncel `frontend/src/theme.css` token'larından WCAG 2.x göreli parlaklığıyla 16 Eylül'de hesaplandı). |
| 8 | Maliyet ve fayda | `docs/10-bom-maliyet-roi.md` · `hardware/pano-beyni/bom.csv` | Kontrolcü kartı adet 1'de **~56 USD**, adet 1.000'de **~37 USD** (sensör düğümleri, SIM/veri ve kurulum işçiliği hariç); fayda tarafı parametriktir, jüri kendi sayısını `scripts/tazminat_maruziyeti.py` ile girer. |
| 9 | Yenilikçilik | `docs/05` §3 · `firmware/akis-diyagramlari/ana-dongu.md` · `docs/12` §4 · `docs/18-konumlandirma-ve-standart-izi.md` | Sabit eşik yerine pano başına RLS ile öğrenilen ısıl direnç indeksi K/K₀ — aynı çekirdek C'de de koşuyor, Python ile fark K **1,36e-8** / τ **1,42e-8** (eşik 1e-6); prognozun başarısız olduğu yeri de yayımlıyoruz (S1'de 790 tahminin yalnızca **%5,2**'si α = 0,20 konisinde, **prognostik ufuk yok**). |

Bu tablo yeni hiçbir iş üretmiyor: her satırdaki sayı zaten kanıt dosyasında duruyor ve nasıl
ölçüldüğü orada yazılı; tablonun tek işi ölçülmüş olanı jürinin cetveline hizalamak. Her sayının
nasıl yeniden üretileceği aşağıdaki **"Nasıl doğrularsınız"** bölümündedir; neyin gerçek neyin
simüle olduğunun tek tek dökümü `docs/17`, bilinçli kapsam sınırlarının tam listesi `docs/17` §6'dadır.

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
| MQTT broker | `localhost:1883` | Kenar → merkez telemetri (anonim; **varsayılan demo yolu**) |
| MQTT broker — mTLS | `localhost:8883` | Yalnızca `--profile mtls` ile; istemci sertifikası zorunlu, cihaz başına topic ACL (F-27, `docs/15` §5.1) |

Durdurma: `docker compose -f deploy/compose.yaml down` · sıfırlama: `down -v`

**Arıza senaryolarını canlı oynatma** (yığın ayaktayken):

```bash
./demo/senaryo/s0.sh     # sağlıklı gün: filo yeşil kalır (canlı demo YAZ gününü oynatır)
./demo/senaryo/s1.sh     # gevşek bağlantı: K/K₀ sabit 70 K eşiğinden çok önce uyarır
./demo/senaryo/s2.sh     # aşırı yük: "arıza değil" — yanlış alarm önleme
./demo/senaryo/s4.sh     # ark olayı: P1 → sanal GSM modeme SMS + WhatsApp istemcisi, kara kutu
```

İki tanesinin küçük yazısı, jüri farkı sorsun diye burada:

- **`s0.sh` mevsim seçimi:** canlı demo `--season yaz` ile koşar (`demo/senaryo/s0.sh` satır 19) ve
  ölçülen yaz değeri **0,0** çiy alarmıdır; yani demoda sağlıklı pano hiç çiy uyarısı üretmez.
  Yukarıdaki kanıt haritasındaki **71,4** sayısı fixture'ların **geçiş** mevsiminde üretilmesinden
  gelir, eşik değişmedi ve o sayı aynen geçerlidir (`docs/12` §3, `docs/05` §11.4).
- **`s4.sh` bildirimi gerçek telefona gitmez:** SMS sanal GSM modeme düşer ve
  `deploy/runtime/sms-log.txt`'e yazılır (`deploy/.env.example`: demo numaraları hayalidir);
  gerçek bir telefona WhatsApp teslimi hâlâ açık bir eksiktir (`docs/17` DH5).

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
| 4 | Örnek normal ve anormal çalışma senaryoları | `demo/senaryo/s0–s8.sh` (`s0`–`s7` koşar; `s8` SCADA okuma adımlarını yazdırır — harici grafik istemci ister); `data/fixtures/` (10 etiketli senaryo + etiketler); `frontend/src/api/mock.ts` | ✅ `s0`–`s6` etiketli senaryoları gerçek yığına canlı oynatır (`panosim --scenario`); oynatılan fizik `docs/12`'yi üreten fiziğin birebir aynısıdır |
| 5 | Alarm oluşması ve bildirim mekanizması | `backend/app/alarm_manager.py`, `backend/app/notify/` (✅; alarm + bildirim test dosyalarında **132** test fonksiyonu — 16 Eylül'de `backend/tests/` üzerinde sayıldı, 661 backend testinin içindedir), `frontend/src/pages/AlarmKonsolu.tsx` (✅) | ✅ |
| 6 | Sistem mimarisi | `docs/02-mimari.md` | ✅ |
| 7 | Gerçek saha uygulaması ve ölçeklendirme | `docs/08-kurulum-proseduru.md`, `docs/09-olceklenebilirlik.md`, `docs/13-donanim-tasarimi.md` | ✅ |

**Bilinçli sınırlar** (sunumda da böyle anlatılır, ayrıntı: `docs/17`):
donanım satın alınmadı — ölçüm uçları fizik tabanlı veri üreteciyle simüle edilir, merkez
yazılımı ise sahadakiyle **aynı koddur**; 9 arayüz ekranının 7'si yapıldı (mobil PWA ve
devreye alma sihirbazı bilinçli olarak kapsam dışı); KiCad şeması yerine blok diyagram +
I/O tablosu + BOM üçlüsü seçildi (gerekçe: `hardware/pano-beyni/README.md`); **varsayılan demo
yolu** büyük ölçüde kimlik doğrulamasızdır — REST yazma uçları operatör belirteci ister (F-19) ve MQTT için
ayrı bir mTLS profili vardır (F-27, `--profile mtls`, varsayılan kapalı), ama okuma uçları, WebSocket,
Modbus ve IEC 104 açıktır. Üretim farkları `docs/15` §5'te listelidir.
Tam liste: `docs/17` §6.

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
| `docs/` | dosya başına tek sahip | Jüriye teslim edilecek **20 doküman** (01–17 + 07b, artı `18-konumlandirma-ve-standart-izi.md` ve `19-tedas-sartname-uyumu.md`), tamamı hazır |

---

## Nasıl doğrularsınız

```bash
cd libs/panoalgo && pytest                              # 401 test — fizik, tespit, senaryolar
cd backend && pytest                                    # 661 test (TEST_DB_DSN ile gerçek TimescaleDB testleri dahil)
cd sim && pytest                                        # 21 test — simülatörler, senaryo oynatma
cd frontend && npm ci && npm test && npm run build      # 85 test + tsc --noEmit 0 hata + üretim derlemesi
cmake -S firmware -B build && cmake --build build && ctest --test-dir build   # C çekirdeği 5/5
```

`panoalgo` · `backend` · `frontend` · `firmware` sayıları 16 Eylül 2026'da bu depoda ölçüldü.
`sim` satırındaki **21** depoda yazılı olan sayıdır, o gün yeniden doğrulanmadı.

Rapordaki sayılar elle yazılmadı — betikle yeniden üretilebilirler. Betik `panoalgo`'yu import
ediyorsa `libs/panoalgo/.venv`, backend'i import ediyorsa `backend/.venv` ile koşar
(Windows'ta `.venv/Scripts/python`, Linux/macOS'ta `.venv/bin/python`):

```bash
# libs/panoalgo/.venv
python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures   # 10 etiketli senaryo
python scripts/validate.py --out docs/12-dogrulama-sonuclari.md      # doğrulama tablosu (recall, öne alma, yanlış alarm)
python scripts/threshold_sweep.py --seasons                          # çiy eşiği taraması (docs/05 §11): kış 28,6 · geçiş 71,4 · yaz 0,0

# backend/.venv
python scripts/seed_demo.py --dsn postgresql://postgres:gridup@localhost:5432/gridup --reset
#   altın demo veritabanı: 3 pano / 21 gün / tohum 1304 → 1.142.265 telemetri satırı, 2 dk 08 sn;
#   aynı tohum aynı özeti verir, taban öğrenmesi tamamlanmış ≥7 günlük geçmişle açılır
python scripts/tazminat_maruziyeti.py --help                         # EPDK kalemleriyle tazminat maruziyeti (docs/10 §5)
```

### Aynı değeri üç protokolden kendiniz okuyun

Aşağıdaki üç komutun **beklenen çıktısı 13 Eylül 2026'da canlı yığında ölçülmüş bir kayıttır**
(`docs/03` §14 ve `docs/04` §9); adresler sözleşmeden üretilen `docs/03`/`docs/04` tablolarından
alınmıştır. Komutları koşturmak için yığın **sizin makinenizde ayakta olmalıdır**:
`docker compose -f deploy/compose.yaml up -d --build` yığını kaldırır, `scripts/duman-testi.sh`
ise `:502` ve `:2404` dahil tüm portların dinlediğini doğrular.

Üçü de aynı dört noktayı okur: `conn_temp.GIRIS_L1…GIRIS_N` (birim/istasyon 1 = `ADM-00001`).

> **Windows'ta:** `backend/.venv/bin/python` yerine `backend/.venv/Scripts/python` yazın ve üç komutu
> da **Git Bash**'te koşturun — 2. komuttaki `<<'PY'` heredoc'u PowerShell'de çalışmaz.

**1 — Modbus TCP `:502`** (FC03, PDU 100–103; `docs/03` §4 ve §6):

```bash
backend/.venv/bin/python -c "
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient('127.0.0.1', port=502, timeout=3); c.connect()
print(c.read_holding_registers(100, count=4, slave=1).registers)
c.close()"
```

**2 — IEC 60870-5-104 `:2404`** (STARTDT → `C_IC_NA_1` genel sorgulama, QOI 20; IOA = 1000 + Modbus
PDU, yani 1100–1103; `docs/04` §2 ve §4). Bu akış `backend/tests/test_scada_app.py` içindeki
`iec104_interrogate` yardımcısının aynısıdır:

```bash
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import socket, struct
from app.scada import iec104
s = socket.create_connection(("127.0.0.1", 2404), timeout=5)
def exactly(n):
    b = b""
    while len(b) < n:
        b += s.recv(n - len(b))
    return b
def read():
    head = exactly(2)
    return iec104.decode_apdu(head + exactly(head[1]))
s.sendall(iec104.encode_u(iec104.UFunction.STARTDT_ACT))
assert read() == iec104.UFrame(iec104.UFunction.STARTDT_CON)
s.sendall(iec104.encode_i(0, 0, iec104.encode_asdu(
    iec104.Asdu(iec104.C_IC_NA_1, iec104.COT_ACTIVATION, 1, ((0, bytes([20])),)))))
points = {}
while True:
    frame = read()
    if not isinstance(frame, iec104.IFrame):
        continue
    asdu = iec104.decode_asdu(frame.asdu)
    if asdu.cot == iec104.COT_INTERROGATED:
        points.update(dict(asdu.objects))
    if asdu.cot == iec104.COT_ACTIVATION_TERM:
        break
s.close()
print([round(struct.unpack("<fB", points[ioa])[0], 1) for ioa in range(1100, 1104)])
PY
```

**3 — REST API `:8000`** (pano detay ucu; `contracts/openapi.yaml`):

```bash
curl -s http://localhost:8000/api/v1/panels/ADM-00001 | backend/.venv/bin/python -c "
import json, sys
p = {x['pt']: x['t_c'] for x in json.load(sys.stdin)['points']}
print([p[k] for k in ('GIRIS_L1', 'GIRIS_L2', 'GIRIS_L3', 'GIRIS_N')])"
```

Beklenen çıktı — kanıt tek tek sayılar değil, **eşitliktir**:

```
1  Modbus FC03 100–103   → [t1×10, t2×10, t3×10, tN×10]   int16, °C × 10 (docs/03 §5: 250 = 25,0 °C)
2  IEC 104 IOA 1100–1103 → [t1,    t2,    t3,    tN   ]   kısa kayan nokta, °C
3  REST points[].t_c     → [t1,    t2,    t3,    tN   ]   °C
```

Yani Modbus listesi = REST listesi × 10 (yarım yukarı yuvarlanır, `docs/03` §5) ve IEC 104 listesi
= REST listesi. Değerler panonun o anki sıcaklığıdır; 13 Eylül'de canlı yığında bunun tamamı ölçüldü:

| Ne ölçüldü | Nerede kayıtlı | Sonuç |
|---|---|---|
| Modbus `conn_temp` = API × 10, 25 noktanın tamamı | `docs/17` §4.2 (nokta sayısı ve fark) · `docs/03` §14 (canlı okuma kaydı) | **fark 0** |
| IEC 104 = REST API (sıcaklık, ΔT, K/K₀, ortam, elektrik, sağlık, TVOC-2) | `docs/04` §9 | 87 kontrol, **0 fark** |
| IEC 104 = Modbus FC03 ham × ölçek | `docs/04` §9 | 139 adres, **0 fark** |
| Tek istasyon sorgulaması (CA 1) | `docs/04` §9 | 167 nokta (139 ölçülen + 28 tek nokta), 8 I çerçevesi, 2 ms |

Grafik arayüz tercih ederseniz aynı Modbus okuması QModMaster ile adım adım: `docs/03` §11.

**Bu kart neyi kanıtlamaz:** üç protokolün aynı veriyi aynı değerle sunduğunu, yani protokol
eşdeğerliğini kanıtlar; sıcaklığın **fiziksel olarak doğru ölçüldüğünü kanıtlamaz** — sensör
tarafı simülasyondur (`docs/17` §2).

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
