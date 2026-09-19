# 2026-09-14 — Toplu cihaz sağlığı ucu (öneri)

**Dosya:** contracts/openapi.yaml
**Öneren:** Kişi C
**Ne değişiyor:** Yeni uç eklenecek: `GET /api/v1/fleet/health` → `[{pano_id, nodes_ok, nodes_total,
rssi_dbm, vbak_pct, buffered, fw, comms_ok, last_seen}]` (tüm filo için tek istekte, `PanelSummary`
gibi hafif bir liste; `PanelDetail`'in tamamını çekmeye gerek kalmaz).
**Neden:** `frontend/src/pages/CihazSagligi.tsx` (TC3) şu an görünen her pano için ayrı ayrı
`GET /api/v1/panels/{id}` çağırıyor (sınırlı eşzamanlılıkla). 20 panoda sorun değil; 100+ panoda
(GK7 hedefi) bu ekran yavaşlar ve backend'e gereksiz yük biner. Tek bir toplu uç, filo listesiyle
aynı mantıkta (`panel_summary` türetme deseni) düşük maliyetli olur. Ayrıca `BolgeHaritasi.tsx`
il/ilçe bazlı kırılım için konum alanına ihtiyaç duyuyor — bu öneri kabul edilirse aynı PR'da
`lat`/`lon` yerine (çoğu zaman boş) gerçek `il`/`ilce` alanları da eklenebilir.
**Etkilenen kulvarlar:** B (uç: `backend/app/api/panels.py` veya `insights.py`'ye eklenir), C (istemci)
**Geri uyumlu mu:** evet (yalnızca ekleme, mevcut hiçbir alan/uç değişmiyor)
**Onaylar:** [ ] A  [ ] B  [ ] C

## Önerilen yanıt şeması (taslak)

```json
[
  {
    "pano_id": "ADM-00014",
    "nodes_ok": 25,
    "nodes_total": 25,
    "rssi_dbm": -71.0,
    "vbak_pct": 100.0,
    "buffered": 0,
    "fw": "0.3.1",
    "comms_ok": true,
    "last_seen": "2026-09-14T10:00:00+00:00"
  }
]
```

## Onaylanana kadar geçici çözüm

`CihazSagligi.tsx` görünen panoları sınırlı eşzamanlılıkla (6) tek tek çeker; sayfa içinde bu
sınırlama açıkça belirtilir. `BolgeHaritasi.tsx` gerçek il/ilçe verisi olmadığı için pano_id
önekindeki dağıtım şirketine (ADM/GDZ) göre gruplar.

## 15 Eylül güncellemesi — önerilen karar: **sonraki sürüme**

Gerekçe, öneriyi zayıflatmıyor; zamanlama:

- `contracts/` Faz 3 sonrası donmuştur (PLAN.md Bölüm F). Özellik dondurma **17 Eylül 23:59**.
  Bu uç, sözleşme + backend ucu + frontend istemcisi + testler demektir ve dondurmadan önceki
  iki güne sığdırılırsa diğer kritik maddelerin (K1, K5, video, prova) zamanını yer.
- Mevcut geçici çözüm **ölçülen kullanımda yeterli**: demo filosu 3–20 pano, sınırlı
  eşzamanlılık 6. GK7 hedefi olan 100+ pano bu teslimde canlı gösterilmiyor.
- Sapma zaten açıkça yazılı: `docs/17` §6 madde 7 ve sunum "bilinçli sapmalar" listesi
  ("Cihaz Sağlığı ekranı pano başına istek atıyor").

Yani **reddedilmiyor, ertelenir**: kabul edilirse `version: 2` ile bir sonraki milestone'un ilk
işidir. Üç onay dondurmadan önce gelirse ve K1–K5 kapanmışsa bu teslimde de uygulanabilir.

## Onaylar (karar toplantısında)

- [x] A — uygula
- [x] B — uygula
- [x] C — uygula

---

## Karar — 18 Eylül 2026: **kabul edildi ve uygulandı**

15 Eylül'deki "sonraki sürüme ertele" önerisinin tek gerekçesi **zamanlamaydı** (özellik
dondurma 17 Eylül 23:59, GK2). O tarih geçti; gerekçe düştü, öneri aynen uygulandı.

### Ne yapıldı

| Katman | Değişiklik |
|---|---|
| Sözleşme | `contracts/openapi.yaml` **1.0.0 → 1.1.0**: `GET /api/v1/fleet/health` + `PanelHealth` şeması. **Yalnızca ekleme** — mevcut hiçbir uç/alan değişmedi |
| Backend | `db.py` `_HEALTH_PAYLOAD` + `list_panel_health()`; `api/views.py` `panel_health()`; `api/insights.py` `GET /fleet/health` |
| Frontend | `api/types.ts` `PanelHealth`, `api/client.ts` + `api/mock.ts` `fleetHealth()`; `pages/CihazSagligi.tsx` artık **tek istek** atıyor |

### Taslak şemadan iki sapma — ikisi de uygulama sırasında ölçülerek bulundu

**1. `fw` yükün kökünde, `health` bloğunun içinde değil.** İlk SQL projeksiyonu yalnızca
`l.payload -> 'health'` çekiyordu ve `fw` null geliyordu. `GET /panels/{id}` bunu zaten
kökten yükseltiyordu (`api/views.py`); toplu uç de aynısını yapmak zorunda. Bunu **test
yakaladı**, gözden geçirme değil: `test_fleet_health_matches_panel_detail` iki ucun aynı
alan için aynı değeri döndürmesini kilitliyor.

**2. `maint_mode` ve `baseline_day` taslakta yoktu, eklendi.** Ekran ikisini de gösteriyor
(`baseline_day` "Taban öğrenme" sütunu); onlarsız uç, yerini aldığı çağrıyı tam
karşılamazdı ve ekran yine pano-başına isteğe muhtaç kalırdı.

### `lat`/`lon` teklifi: **uygulanmadı**

Öneri "aynı PR'da `lat`/`lon` yerine gerçek `il`/`ilçe` alanları da eklenebilir" diyordu.
Eklenmedi, çünkü **veri yok**: `panels` tablosunda il/ilçe kolonu yoktur ve bu depoda
doldurulacak gerçek bir kaynak da yoktur (GK3 — CBS içe aktarımı yapılmadı). Alan açıp boş
bırakmak ya da pano_id önekinden il uydurmak GK10 ihlali olurdu. Bu iş varlık künyesi
maddesine (`GELISTIRME-BACKLOGU.md` F-21) aittir ve orada kalıyor. `lat`/`lon` 15 Eylül'den
beri sözleşmede zaten var ve Bölge Haritası onu kullanıyor.

### Ölçülen

- `scripts/check_contracts.py`: **9 uç → 10 uç**, "SOZLESMELER TUTARLI".
- Yeni testler: backend'de 6 uç testi + 2 gerçek TimescaleDB projeksiyon testi.
- İstek sayısı: ekran başına **N istek → 1 istek** (N = görünen pano sayısı). Bu bir kod
  özelliğidir, ölçülmüş bir gecikme iyileştirmesi **değildir**: demo filosu 3–20 pano ve
  bu ölçekte fark zaten görünmüyordu. 100+ panoda beklenen kazanç **ölçülmedi**.
