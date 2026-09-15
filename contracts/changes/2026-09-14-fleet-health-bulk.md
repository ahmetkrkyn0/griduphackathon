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

- [ ] A — bu sürümde uygula
- [ ] B — bu sürümde uygula
- [ ] C — bu sürümde uygula

veya

- [ ] Üçü birden: **sonraki sürüme ertele** (önerilen)
