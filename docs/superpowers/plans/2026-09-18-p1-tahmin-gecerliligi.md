# P1 — Tahmin Geçerliliği ve Kanıt Kartı Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Her nokta/alarm için altı değerden birini taşıyan bir `gecerlilik` (validity) alanı ekle — `ogreniyor | veri_yetersiz | sensor_supheli | model_kapsami_disi | tahmin_gecerli | sinir_asildi` — ve S8 sensör arızasında (docs/05 §10, docs/12 §4.3) sınır hiç aşılmadan 99 sahte TTL tahmini üretilmesi hatasını kaynağında (panoalgo) düzeltir.

**Architecture:** Üç küçük, birbirinden bağımsız test edilebilir katman: (1) panoalgo'da tek satırlık bir uzlaştırma adımı, kalite bitleri (`q`) set olan bir noktanın `ttl_h`'ini gerçek kaynağında `None`'a çeker — bu S8 hatasının kök nedenidir (docs/05 §10: "edge.py kestirimi q hesabından önce yapar"); (2) backend'de mevcut `point_state()` ile aynı düzeyde yeni bir saf fonksiyon (`point_validity()`), ZATEN AÇIKTA duran alanlardan (`q`, `excited`, `ttl_h`, `state`, `health.baseline_day`) altı değerden birini türetir — hiçbir yeni ham alan icat edilmez; (3) bu değer, `AlarmReason.verify`'ın kullandığı AYNI desenle (backend'de hesapla, DONMUŞ ama AÇIK — `additionalProperties` kapalı değil — `contracts/openapi.yaml` nesnesine ek alan olarak koy) API'ye ve oradan frontend'e akar. `contracts/openapi.yaml`, `contracts/alarm-codes.yaml` ve `contracts/mqtt-telemetry.schema.json` dosyalarının HİÇBİRİ değişmez (17 Eylül özellik dondurması, `contracts/README.md:45-47`); firmware'e satır satır taşınan `time_to_limit()` (detect.py:384-414) imzası da değişmez (TA3 senkronizasyon riski).

**Tech Stack:** Python 3.13 (panoalgo, FastAPI backend), TypeScript/React (frontend, Vite/Vitest), pytest, vitest.

**Spec:** [INOVASYON-UYGULAMA-PLANI.md](../../../INOVASYON-UYGULAMA-PLANI.md) §4 (P1), doğrulama temeli [docs/20-p0-kanit-ve-sinir-raporu.md](../../20-p0-kanit-ve-sinir-raporu.md).

## Global Constraints

- `contracts/openapi.yaml`, `contracts/alarm-codes.yaml`, `contracts/mqtt-telemetry.schema.json` dosyaları DEĞİŞMEZ (dondu, `contracts/README.md:45-47`). Yeni alan yalnızca zaten açık olan yanıt nesnelerine (ConnPoint, AlarmReason) backend'de hesaplanıp eklenir — `AlarmReason.verify` (backend/app/risk.py `_verify`) ile birebir aynı desen.
- `libs/panoalgo/panoalgo/detect.py`'deki `time_to_limit()` (satır 384-414) imzası DEĞİŞMEZ — firmware'e (`firmware/core/rls.c`) 1e-6 toleransla satır satır taşınıyor.
- Yeni Python kodu Türkçe karakter kullanmaz (mevcut kod tabanı kuralı — dosya adlarında ve identifier'larda ASCII, yorum/docstring'lerde de ASCII, tıpkı `detect.py`/`edge.py`/`risk.py`'de olduğu gibi).
- Frontend testleri yalnızca `*.test.ts` (mantık katmanı) — bu projede `*.test.tsx`/React render testi YOK (`vite.config.ts`: `test.environment: "node"`, `include: ["src/**/*.test.ts"]`). Yeni JSX mantığı test edilebilir olması için saf fonksiyonlara (`lib/`) çıkarılır; JSX'in kendisi manuel tarayıcı kontrolüyle doğrulanır.
- Her commit sonrası ilgili test paketi (`pytest` panoalgo/backend, `npm run test` frontend, `npx tsc --noEmit`) yeşil olmalı.
- Alarm şiddeti (`state`, `prio`) ile tahmin geçerliliği (`gecerlilik`) AYRI alanlardır — biri diğerini gizlemez/değiştirmez.
- Kalibrasyonsuz güven oranı ("%95 güven" gibi) YOK — hiçbir yeni metin bir yüzde/olasılık uydurmaz; önce koşulun kendisi (`gecerlilik` metni) gösterilir.

---

## Task 1: panoalgo — S8 sahte-TTL hatasını kaynağında düzelt

**Files:**
- Modify: `libs/panoalgo/panoalgo/edge.py:103-122` (`EdgePipeline.process`)
- Test: `libs/panoalgo/tests/test_edge.py` (mevcut dosyaya ekle, `test_data_quality_is_reported_through_the_q_bit_field` testinin hemen altına)

**Interfaces:**
- Consumes: `point["q"]` (zaten `_update_quality`'nin yazdığı alan, `edge.py:217`), `point["ttl_h"]` (zaten `_update_points`'in yazdığı alan, `edge.py:172`).
- Produces: `EdgePipeline._suppress_ttl_when_quality_suspect(payload: dict) -> None` — sonraki görevler (`limits.evaluate`, backend `risk.py`, `views.py`) artık `ttl_h`'in `q != 0` olan hiçbir noktada asla sayı olmayacağına güvenebilir.

- [ ] **Step 1: Write the failing test**

`libs/panoalgo/tests/test_edge.py` dosyasında, `test_data_quality_is_reported_through_the_q_bit_field` fonksiyonunun (satır 87-100) hemen altına ekle:

```python
def test_ttl_is_suppressed_when_the_point_quality_is_suspect():
    """S8 bilinen siniri (docs/05 #10): surunen (drift) bir sensor, sinir hic
    asilmadan onlarca sahte TTL tahmini uretiyordu. Kok neden: _update_points,
    _update_quality'den ONCE calisiyor, yani TTL hesaplanirken q henuz yok.
    Bu test, uzlastirma adimindan SONRA ttl_h'in q ile tutarli olmasini ister."""
    pipeline = EdgePipeline()
    sim = _sim()
    _run(pipeline, sim, 400)
    pipeline.freeze_baselines()

    sim.set_k_multiplier("DSYA3_L2", 2.5)  # gercek bir TTL uretecek bir egilim yarat
    payload = _run(pipeline, sim, 300)
    point = next(p for p in payload["t_conn"] if p["pt"] == "DSYA3_L2")
    assert point["ttl_h"] is not None  # on-kosul: duzeltmeden once gercekten sayi var

    sim.set_sensor_fault("DSYA3_L2", "dropped")
    payload = _run(pipeline, sim, 20)
    point = next(p for p in payload["t_conn"] if p["pt"] == "DSYA3_L2")

    assert point["q"] != 0  # on-kosul: kalite bayragi gercekten set oldu
    assert point["ttl_h"] is None  # ASIL IDDIA: supheli veriden TTL uretilmez
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd libs/panoalgo && python -m pytest tests/test_edge.py::test_ttl_is_suppressed_when_the_point_quality_is_suspect -v`
Expected: FAIL — `assert point["ttl_h"] is None` başarısız olur çünkü `ttl_h` hâlâ eski (sensör arızasından önceki) sayıyı taşır.

- [ ] **Step 3: Write minimal implementation**

`libs/panoalgo/panoalgo/edge.py` içinde `process()` metodunu (satır 103-122) şu hale getir:

```python
    def process(self, payload: dict) -> dict:
        """Yuku YERINDE zenginlestirir ve ayni sozlugu doner."""
        pano_id = payload["pano_id"]
        ts = datetime.fromisoformat(payload["ts"])
        period_s = self._period_s(pano_id, ts)

        self._update_points(payload, pano_id, ts, period_s)
        self._update_quality(payload)
        self._suppress_ttl_when_quality_suspect(payload)

        previous = self._previous.get(pano_id)
        codes = [
            code
            for code in limits.evaluate(payload, previous, self._contracts_dir)
            if not code.startswith("ALM-DQ-")
        ]
        payload["alarms"] = codes
        payload["risk"] = self._risk_block(payload, codes)

        self._previous[pano_id] = {"tvoc": dict(payload.get("tvoc") or {}), "ts": payload["ts"]}
        return payload
```

Sonra, `_update_quality` metodunun (satır 213-217) hemen altına yeni metodu ekle:

```python
    def _suppress_ttl_when_quality_suspect(self, payload: dict) -> None:
        """S8 bilinen siniri (docs/05-anomali-tespiti.md #10): _update_points,
        _update_quality'den ONCE calisir, yani TTL kestirimi q'yu hic gormeden
        yapilir. Surunen (drift) bir sensor boylece sinir hic asilmadan sonlu
        bir "kalan omur" yayinlayabilir (docs/12 S8_sensor_fault: 99 sahte
        tahmin, 89'u ALM-TTL-14D alarmina donuyordu). Kalite bitleri set
        oldugunda TTL'i burada, kaynakta, None'a cekmek bu siniri kapatir."""
        for point in payload["t_conn"]:
            if point.get("q", 0) != 0:
                point["ttl_h"] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd libs/panoalgo && python -m pytest tests/test_edge.py -v`
Expected: PASS — yeni test dahil TÜM `test_edge.py` testleri geçer (özellikle `test_enriched_payload_still_matches_the_frozen_schema`, çünkü `ttl_h`'in tipi zaten `[number, null]`; sadece değeri değişiyor, şema alanı değişmiyor).

- [ ] **Step 5: Run the full panoalgo suite to confirm no regression**

Run: `cd libs/panoalgo && python -m pytest -v`
Expected: PASS — tüm suit (401+ test) yeşil kalır.

- [ ] **Step 6: Commit**

```bash
git add libs/panoalgo/panoalgo/edge.py libs/panoalgo/tests/test_edge.py
git commit -m "fix(panoalgo): suppress ttl_h when point quality is suspect (P1, S8 known limit)"
```

---

## Task 2: backend — `point_validity()` ve `ConnPoint.gecerlilik`

**Files:**
- Modify: `backend/app/api/views.py`
- Test: `backend/tests/test_api_panels.py` (mevcut dosyaya ekle, `test_point_state_uses_contract_thresholds` testinin hemen altına)

**Interfaces:**
- Consumes: `point_state(point, thresholds, comms_ok) -> str` (zaten var, `views.py:61-76`), `point: dict[str, Any]` (`q`, `excited`, `ttl_h` alanlarıyla), `payload["health"]["baseline_day"]`, `thresholds["baseline_learning_days"]`.
- Produces: `point_validity(point: dict[str, Any], state: str, thresholds: dict[str, Any], baseline_day: int | None) -> str` — Task 3 (risk.py) ve `point_view()` bunu çağıracak. Dönüş değeri altı sabitten biri: `"sensor_supheli" | "sinir_asildi" | "ogreniyor" | "veri_yetersiz" | "model_kapsami_disi" | "tahmin_gecerli"`.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_api_panels.py` dosyasında, `test_point_state_uses_contract_thresholds` testinin (satır 206-231) hemen altına ekle:

```python
@pytest.mark.parametrize(
    "dt_c, k_ratio, q, excited, ttl_h, baseline_day, expected",
    [
        (106.0, 1.0, 3, True, 12.0, 7, "sensor_supheli"),  # kalite bayragi her seyden once gelir
        (70.1, 1.0, 0, True, 5.0, 7, "sinir_asildi"),  # zaten alarm/kritik ise sure onemsiz
        (16.5, 1.02, 0, True, None, 3, "ogreniyor"),  # taban ogrenme tamamlanmadi (7 gunden az)
        (16.5, 1.02, 0, False, None, 7, "veri_yetersiz"),  # ogrenme bitti ama bu pencerede uyarim yok
        (16.5, 1.02, 0, True, None, 7, "model_kapsami_disi"),  # veri yeterli, egilim sinira dogru degil
        (16.5, 1.02, 0, True, 150.5, 7, "tahmin_gecerli"),  # her sey saglikli, sayi guvenilir
    ],
)
def test_point_validity_prioritises_sensor_suspicion_over_everything_else(
    contracts, tel_payload, dt_c, k_ratio, q, excited, ttl_h, baseline_day, expected
):
    point = tel_payload["t_conn"][0]
    point.update({"dt_c": dt_c, "t_c": 25.0 + dt_c, "q": q, "k_ratio": k_ratio, "excited": excited, "ttl_h": ttl_h})
    tel_payload["health"]["baseline_day"] = baseline_day
    store = MemoryStore(PANELS)
    ingest(contracts, store, tel_payload, received_at=NOW)
    app = create_app(Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=lambda: NOW)

    with TestClient(app) as client:
        points = client.get("/api/v1/panels/ADM-00001").json()["points"]

    assert points[0]["gecerlilik"] == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_api_panels.py::test_point_validity_prioritises_sensor_suspicion_over_everything_else -v`
Expected: FAIL — `KeyError: 'gecerlilik'` (alan henüz yok).

- [ ] **Step 3: Write minimal implementation**

`backend/app/api/views.py` içinde `point_state()` fonksiyonunun (satır 61-76) hemen altına ekle:

```python
def point_validity(
    point: dict[str, Any], state: str, comms_ok: bool, thresholds: dict[str, Any], baseline_day: int | None
) -> str:
    """Bir noktanin tahminine ne kadar guvenilebilecegini tek bir nedene indirger.

    Sozlesmede (contracts/openapi.yaml, DONMUS) yeni bir alan degil; AlarmReason.verify
    ornegindeki gibi (backend/app/risk.py _verify) acik nesneye eklenen turetilmis bir
    deger. Girdileri zaten sozlesmede aciktaki alanlardir (q, excited, ttl_h, state,
    health.baseline_day) — panoalgo'ya veya mqtt semasina yeni bir ham alan eklenmez.

    `state` tek basina yetmez: point_state() hem "comms koptu" hem "q != 0" durumunu
    AYNI "stale" degerine indirger (views.py:63-64), ama bunlar farkli nedenlerdir
    (veri hic gelmiyor vs. veri geliyor ama supheli) — comms_ok ayrica alinir.

    Oncelik sirasi: veri yetersiz (comms koptu) > sensor supheli (q != 0) >
    sinir asildi > ogreniyor > veri yetersiz (uyarim yok) > model kapsami disi >
    tahmin gecerli.
    """
    if not comms_ok:
        return "veri_yetersiz"
    if state == "stale":  # comms_ok=True iken stale yalnizca q != 0'dan gelir
        return "sensor_supheli"
    if state in ("alarm", "critical"):
        return "sinir_asildi"
    if baseline_day is not None and baseline_day < thresholds["baseline_learning_days"]:
        return "ogreniyor"
    if not point.get("excited", False):
        return "veri_yetersiz"
    if point.get("ttl_h") is None:
        return "model_kapsami_disi"
    return "tahmin_gecerli"
```

Sonra `point_view()`'ı (satır 132-145) güncelle — `baseline_day`'i parametre olarak al ve `view["gecerlilik"]`'i ekle:

```python
def point_view(point: dict[str, Any], thresholds: dict[str, Any], comms_ok: bool, baseline_day: int | None) -> dict[str, Any]:
    view = {
        "pt": point["pt"],
        "label": point_label(point["pt"]),
        "t_c": point["t_c"],
        "dt_c": point["dt_c"],
    }
    for field in POINT_OPTIONAL_FIELDS:
        view[field] = point.get(field)
    if "excited" in point:
        view["excited"] = point["excited"]
    view["q"] = point.get("q", 0)
    state = point_state(point, thresholds, comms_ok)
    view["state"] = state
    view["gecerlilik"] = point_validity(point, state, comms_ok, thresholds, baseline_day)
    return view
```

Son olarak, `panel_detail()`'ın (satır 178-217) `point_view(...)` çağrısını (satır 209) güncelle:

```python
        points=[point_view(p, contracts.thresholds, comms_ok, health.get("baseline_day")) for p in payload["t_conn"]],
```

(Bu satır zaten `health = dict(payload["health"])` — satır 203 — tanımından SONRA çalışıyor, yani `health.get("baseline_day")` orada hazır.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_api_panels.py -v`
Expected: PASS — yeni parametrize edilmiş test (6 durum) dahil tüm `test_api_panels.py` geçer. `test_panel_detail_points_carry_labels_states_and_measurements` (satır 169-203) testindeki `assert points[1] == {...}` ve `assert points[3] == {...}` sözlük eşitlik kontrolleri artık `"gecerlilik"` anahtarı eksik olduğu için FAIL verir — bu testin beklenen sözlüklerine de `"gecerlilik"` alanını ekle (points[1]/GIRIS_L2: `"gecerlilik": "tahmin_gecerli"`; points[3]/GIRIS_N: `"gecerlilik": "sensor_supheli"`) ve tekrar çalıştır.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python -m pytest -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/views.py backend/tests/test_api_panels.py
git commit -m "feat(backend): derive point-level gecerlilik (validity) from existing fields"
```

---

## Task 3: backend — alarm `reason.gecerlilik`

**Files:**
- Modify: `backend/app/risk.py:133-152` (`RiskEngine._condition`)
- Test: `backend/tests/test_risk.py` (mevcut dosyaya ekle, `test_verify_lists_the_evidence_of_the_hypothesis_that_is_still_missing` testinin hemen altına)

**Interfaces:**
- Consumes: `point_validity` ve `point_state` (Task 2'de `views.py`'de tanımlandı), `self._thresholds` (zaten `RiskEngine.__init__`'te var, `risk.py:66`).
- Produces: `Condition.reason["gecerlilik"]` — yalnızca `point is not None` iken (panel-geneli alarmlarda bu kavram yok, eklenmez). `frontend/src/components/AlarmNedeni.tsx`'in `alarm.reason?.gecerlilik` okuyacağı alan budur.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_risk.py` dosyasında, `test_verify_lists_the_evidence_of_the_hypothesis_that_is_still_missing` testinin (satır 255-269) hemen altına ekle:

```python
def test_condition_reason_carries_point_gecerlilik_alongside_verify(engine, contracts, tel_payload):
    """Alarm karti (AlarmNedeni.tsx "Ne kadar acil?") ile nokta tablosu (PanoDetay.tsx)
    AYNI kaynaktan okumali; ikisi de risk.py/views.py'deki tek point_validity()'den gelir."""
    conditions = by_key(engine.evaluate(to_sample(contracts, tel_payload)))

    condition = conditions[("ALM-K-WARN", "GIRIS_L2")]

    assert condition.reason["gecerlilik"] == "tahmin_gecerli"  # GIRIS_L2: q=0, excited, ttl_h=150.5, warn (alarm degil)


def test_panel_wide_conditions_do_not_carry_gecerlilik(engine, contracts, tel_payload):
    """Nokta kavramı olmayan panel-geneli alarmlarda (or. ALM-DEW-WARN) gecerlilik uydurulmaz."""
    tel_payload["env"]["td_margin_k"] = 1.0
    tel_payload["alarms"] = ["ALM-DEW-WARN"]

    [condition] = engine.evaluate(to_sample(contracts, tel_payload))

    assert "gecerlilik" not in condition.reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_risk.py::test_condition_reason_carries_point_gecerlilik_alongside_verify -v`
Expected: FAIL — `KeyError: 'gecerlilik'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/risk.py` başındaki import bloğuna (satır 21-23 civarı) ekle:

```python
from .views import point_state, point_validity
```

Sonra `_condition()` metodunu (satır 133-152) güncelle — `reason["verify"]` bloğunun hemen altına:

```python
    def _condition(
        self,
        code: str,
        payload: dict[str, Any],
        point: dict[str, Any] | None,
        signals: list[Signal],
        active: frozenset[str],
    ) -> Condition:
        alarm = self._contracts.alarm(code)
        point_name = point["pt"] if point else None
        reason: dict[str, Any] = {"signals": signals, "layer": alarm["layer"], "point": point_name}
        if "basis" in alarm:
            reason["basis"] = alarm["basis"]
        hypothesis = self._dominant_hypothesis(code, payload)
        verify = _verify(hypothesis, active)
        if verify is not None:
            reason["verify"] = verify
        if point is not None:
            state = point_state(point, self._thresholds, comms_ok=True)
            baseline_day = (payload.get("health") or {}).get("baseline_day")
            reason["gecerlilik"] = point_validity(point, state, True, self._thresholds, baseline_day)
        ttl_h = point.get("ttl_h") if point else (payload.get("risk") or {}).get("ttl_h")
        advice = hypothesis["advice"] if hypothesis else None
        return Condition(code=code, point=point_name, reason=reason, advice=advice, ttl_h=ttl_h)
```

(`comms_ok=True`: `RiskEngine.evaluate()` yalnızca YENİ gelen bir örnek üzerinde çalışır — o an haberleşme zaten sağlamdır; bayatlık `ALM-COMMS-LOST` üzerinden ayrıca ve merkezde ele alınır, bkz. `is_comms_ok`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_risk.py -v`
Expected: PASS — yeni iki test dahil tüm `test_risk.py` geçer. Bazı mevcut testler (`reason ==` şeklinde TAM sözlük eşitliği yapanlar varsa) `gecerlilik` anahtarı eklendiği için kırılabilir — `python -m pytest tests/test_risk.py -v` çıktısında FAIL olanları oku, her birinin beklenen sözlüğüne doğru `"gecerlilik"` değerini ekleyerek düzelt (kopyala-yapıştır değil — her noktanın kendi `q`/`excited`/`ttl_h`/`state` durumuna göre doğru değeri hesapla).

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python -m pytest -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/risk.py backend/tests/test_risk.py
git commit -m "feat(backend): surface gecerlilik on point-anchored alarm reasons"
```

---

## Task 4: backend — P1 kabul senaryoları (uçtan uca)

**Files:**
- Create: `backend/tests/test_p1_validity_scenarios.py`

**Interfaces:**
- Consumes: Task 1-3'ün tüm ürünleri (`EdgePipeline`, `point_validity`, `Condition.reason["gecerlilik"]`) — bu görev YENİ kod üretmez, yalnızca INOVASYON-UYGULAMA-PLANI.md §4 "Kabul senaryoları" tablosundaki 5 satırı gerçek uçtan-uca testlere döker (planın "Teslim kapısı" şartı).
- Produces: Hiçbir şey — bu bir doğrulama görevi, imza üretmez.

- [ ] **Step 1: Write the failing (or trivially passing) tests**

`backend/tests/test_p1_validity_scenarios.py` dosyasını oluştur:

```python
"""P1 kabul senaryolari — INOVASYON-UYGULAMA-PLANI.md #4 "Kabul senaryolari" tablosunun
birebir kodu. Bu dosya PLANIN KENDISI degisirse guncellenir; baska hicbir yerden import
edilmez (tamami uctan uca dogrulama, bkz. "Teslim kapisi": bu senaryolar gecmeden yeni
demo surumune alinmaz).

`ingest()` test_api_panels.py:26'daki ile AYNI govdedir — orada da paylasilan bir
helpers.py fonksiyonu degil, o dosyaya ozel bir yerel yardimcidir (helpers.py yalnizca
dusuk seviyeli `encode(payload) -> bytes` ve `utc(y, m, d, h, mi, s) -> datetime` tasir);
bu yuzden burada da yerel olarak tanimlanir, ithal edilmez."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.config import Settings
from app.ingest import IngestPipeline
from app.main import create_app
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, encode, utc

PANELS = [{"pano_id": "ADM-00001", "name": "Test Pano", "lat": 37.8450, "lon": 27.8396}]  # test_api_panels.py PANELS ile ayni sekil (4 anahtar)
NOW = utc(2026, 9, 18, 12, 0, 0)


def ingest(contracts, store, payload: dict, received_at: datetime) -> None:
    pipeline = IngestPipeline(contracts, store, clock=lambda: received_at)
    pipeline.handle_message(f"gridup/pano/{payload['pano_id']}/tel", encode(payload))
    assert pipeline.flush()


def _ingest_and_get_point(contracts, tel_payload, overrides: dict) -> dict:
    point = tel_payload["t_conn"][0]
    point.update(overrides.get("point", {}))
    if "baseline_day" in overrides:
        tel_payload["health"]["baseline_day"] = overrides["baseline_day"]
    store = MemoryStore(PANELS)
    ingest(contracts, store, tel_payload, received_at=NOW)
    app = create_app(Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=lambda: NOW)
    with TestClient(app) as client:
        return client.get("/api/v1/panels/ADM-00001").json()["points"][0]


def test_healthy_measurement_still_learning_shows_no_unverified_duration(contracts, tel_payload):
    """Satir 1: Saglikli olcum, ogrenme tamamlanmamis -> Ogrenme bilgisi; dogrulanmamis
    sure tahmini yok."""
    point = _ingest_and_get_point(
        contracts, tel_payload,
        {"point": {"dt_c": 16.5, "t_c": 41.5, "q": 0, "k_ratio": 1.02, "excited": True, "ttl_h": None}, "baseline_day": 3},
    )
    assert point["gecerlilik"] == "ogreniyor"
    assert point["ttl_h"] is None


def test_loose_connection_signature_keeps_early_warning_with_evidence(contracts, tel_payload):
    """Satir 2: Gevsek baglanti belirtisi, yeterli veri -> Erken uyari korunur, dayanaklar gorunur."""
    point = _ingest_and_get_point(
        contracts, tel_payload,
        {"point": {"dt_c": 53.0, "t_c": 78.0, "q": 0, "k_ratio": 1.45, "excited": True, "ttl_h": 150.5}, "baseline_day": 7},
    )
    assert point["state"] == "warn"  # esik henuz asilmadi, erken uyari asamasi
    assert point["gecerlilik"] == "tahmin_gecerli"
    assert point["ttl_h"] == 150.5  # dayanak (sayi) gorunur kaliyor


def test_sensor_drift_shows_suspicion_and_no_misleading_countdown(contracts, tel_payload):
    """Satir 3: Sensor sapmasi -> Supheli nedeni ve gecersiz tahmin durumu; yaniltici
    geri sayim yok (docs/05 #10, S8). NOT: bu test backend'in point_validity()'sini
    dogrular — girdi olarak DOGRU calisan bir kenarin (Task 1'den sonra) gonderecegi
    ttl_h=None + q!=0 kombinasyonunu verir. Task 1'in KENDI davranisi (q set olunca
    ttl_h'i gercekten None'a cekmesi) test_edge.py::test_ttl_is_suppressed_when_the_
    point_quality_is_suspect'te ayrica ve dogrudan test edilir; bu backend testi onu
    tekrar etmez, panoalgo'nun ciktisina zaten guvenir (sinir: bu test IngestPipeline'a
    dogrudan yazar, EdgePipeline'i hic calistirmaz)."""
    point = _ingest_and_get_point(
        contracts, tel_payload,
        {"point": {"dt_c": 16.5, "t_c": 41.5, "q": 1, "k_ratio": 1.02, "excited": True, "ttl_h": None}, "baseline_day": 7},
    )
    assert point["gecerlilik"] == "sensor_supheli"
    assert point["ttl_h"] is None


def test_data_loss_shows_last_seen_not_a_live_looking_value(contracts, tel_payload):
    """Satir 4: Veri kopmasi -> Son veri zamani ve izleme kaybi; son deger canli gibi
    gorunmez. NOT: comms_ok, payload["ts"]'den degil store'un last_rx'inden turer
    (bkz. test_api_panels.py:103-108 test_comms_ok_follows_contract_heartbeat_timeout);
    bu yuzden _ingest_and_get_point yerine last_rx'i acikca geri iten bir akis kullanilir."""
    store = MemoryStore(PANELS)
    ingest(contracts, store, tel_payload, received_at=NOW)
    store.set_last_rx("ADM-00001", NOW - timedelta(minutes=10))  # esik: heartbeat_timeout_min = 5
    app = create_app(Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False), store=store, clock=lambda: NOW)

    with TestClient(app) as client:
        point = client.get("/api/v1/panels/ADM-00001").json()["points"][0]

    assert point["state"] == "stale"
    assert point["gecerlilik"] == "veri_yetersiz"  # comms koptu: q'dan degil, haberlesme kaybindan gelir


def test_breached_limit_keeps_critical_alarm_independent_of_validity(contracts, tel_payload):
    """Satir 5: Sinir asilmis -> "Sinir asildi"; kritik olcum alarmi bagimsiz kalir."""
    point = _ingest_and_get_point(
        contracts, tel_payload,
        {"point": {"dt_c": 70.1, "t_c": 95.1, "q": 0, "k_ratio": 1.0, "excited": True, "ttl_h": 2.0}, "baseline_day": 7},
    )
    assert point["state"] == "alarm"
    assert point["gecerlilik"] == "sinir_asildi"
```

- [ ] **Step 2: Run tests to check current status**

Run: `cd backend && python -m pytest tests/test_p1_validity_scenarios.py -v`
Expected: Eğer Task 1-3 doğru uygulandıysa TÜMÜ PASS olmalı (bu görev yeni davranış eklemiyor, önceki üç görevi doğruluyor). Herhangi biri FAIL ise, hangi görevin çıktısının beklentiyle uyuşmadığını bul (`point_validity()`'nin öncelik sırası mı, `_suppress_ttl_when_quality_suspect`'in çalışma sırası mı) ve o görevin dosyasına dön — bu dosyaya YAMA yapma.

- [ ] **Step 3: Run the full backend suite**

Run: `cd backend && python -m pytest -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_p1_validity_scenarios.py
git commit -m "test(backend): encode P1 acceptance scenarios end to end"
```

---

## Task 5: frontend — `Gecerlilik` tipi ve metin karşılıkları

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/lib/labels.ts`
- Test: `frontend/src/lib/labels.test.ts` (mevcut dosyayı oku, aynı desenle bir test ekle)

**Interfaces:**
- Produces: `export type Gecerlilik = "sensor_supheli" | "sinir_asildi" | "ogreniyor" | "veri_yetersiz" | "model_kapsami_disi" | "tahmin_gecerli"`, `GECERLILIK_TEXT: Record<Gecerlilik, string>`, `validityHint(gecerlilik: Gecerlilik | undefined, prio: Prio): string`. Task 6-7 bunları kullanacak.

- [ ] **Step 1: Read the existing test pattern**

`frontend/src/lib/labels.test.ts` dosyasını oku (`labels.ts:3` yorumu: "labels.test.ts, sozlesmedeki her kodun burada karsiligi oldugunu denetler" — hangi desenle test ettiğini gör, örn. `STATE_TEXT`'in her `PointState` değeri için bir karşılığı olduğunu nasıl kontrol ediyor).

- [ ] **Step 2: Write the failing test**

`labels.test.ts`'e, `STATE_TEXT` için olan testin hemen altına, AYNI DESENLE (dosyayı okuduktan sonra gerçek söz dizimini kopyala) bir test ekle — `GECERLILIK_TEXT`'in altı `Gecerlilik` değerinin HEPSİ için bir karşılığı olduğunu doğrulayan.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/labels.test.ts`
Expected: FAIL — derleme hatası (`Gecerlilik`/`GECERLILIK_TEXT` henüz yok).

- [ ] **Step 4: Write minimal implementation**

`frontend/src/api/types.ts` içinde, `PointState` tanımının (satır 7) hemen altına ekle:

```ts
/** Sozlesme disi uzanti (contracts/openapi.yaml DONMUS): backend/app/api/views.py
 * point_validity() / risk.py _condition() tarafindan hesaplanir, ConnPoint ve
 * AlarmReason'in acik (additionalProperties kapali degil) govdesine eklenir —
 * AlarmReason.verify ile ayni desen. */
export type Gecerlilik = "sensor_supheli" | "sinir_asildi" | "ogreniyor" | "veri_yetersiz" | "model_kapsami_disi" | "tahmin_gecerli";
```

`ConnPoint` arayüzüne (satır 28-40) `gecerlilik?: Gecerlilik;` ekle. `AlarmReason` arayüzüne (satır 107-113) `gecerlilik?: Gecerlilik;` ekle.

`frontend/src/lib/labels.ts` içinde, `STATE_TEXT` (satır 15-21) tanımının hemen altına ekle:

```ts
import type { Gecerlilik, NotifyChannel, PointState, Prio } from "../api/types";

export const GECERLILIK_TEXT: Record<Gecerlilik, string> = {
  sensor_supheli: "Sensör şüpheli",
  sinir_asildi: "Sınır aşıldı",
  ogreniyor: "Öğreniyor",
  veri_yetersiz: "Veri yetersiz",
  model_kapsami_disi: "Model kapsamı dışı",
  tahmin_gecerli: "Tahmin geçerli",
};

const GECERLILIK_HINT: Record<Exclude<Gecerlilik, "tahmin_gecerli">, string> = {
  sensor_supheli: "Bu ölçümde veri kalitesi şüpheli; kalan ömür tahmini gösterilmiyor.",
  sinir_asildi: "Ölçüm zaten sınırın üstünde; kalan süre yerine acil müdahale önemli.",
  ogreniyor: "Taban sıcaklık öğrenimi sürüyor; doğrulanmamış süre tahmini gösterilmiyor.",
  veri_yetersiz: "Bu nokta için güncel veya yeterli veri yok; süre tahmini gösterilmiyor.",
  model_kapsami_disi: "Eğilim sınıra doğru sürekli kötüleşmiyor; tahmin modeli bu örüntüyü kapsamıyor.",
};

/** AlarmNedeni.tsx "Ne kadar acil?" dususu: ttl_h yoksa NEDEN yoksa gosterir,
 * "Sure tahmini yok" gibi bilgisiz bir cumleye duselmez. */
export function validityHint(gecerlilik: Gecerlilik | undefined, prio: Prio): string {
  if (gecerlilik && gecerlilik !== "tahmin_gecerli") return GECERLILIK_HINT[gecerlilik];
  return prio === "P1" ? "Hemen müdahale gerekir." : "Süre tahmini yok.";
}
```

(NOT: `import type { NotifyChannel, PointState, Prio }` satırı dosyada zaten var — satır 5 — oraya `Gecerlilik`'i EKLE, ikinci bir `import` satırı yazma.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/labels.test.ts`
Expected: PASS.

- [ ] **Step 6: Type-check and run the full frontend suite**

Run: `cd frontend && npx tsc --noEmit && npm run test`
Expected: PASS (henüz `.gecerlilik`'i okuyan bir JSX yok, o yüzden başka hiçbir yer kırılmaz).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/lib/labels.ts frontend/src/lib/labels.test.ts
git commit -m "feat(frontend): add Gecerlilik type and Turkish text mapping"
```

---

## Task 6: frontend — `AlarmNedeni.tsx` "Ne kadar acil?" geçerlilik-farkında

**Files:**
- Modify: `frontend/src/components/AlarmNedeni.tsx:44-135`

**Interfaces:**
- Consumes: `validityHint` (Task 5, `lib/labels.ts`), `alarm.reason?.gecerlilik` (Task 3'ün backend çıktısı).

- [ ] **Step 1: Modify the component**

`frontend/src/components/AlarmNedeni.tsx` içinde import satırını (satır 5) güncelle:

```tsx
import { CHANNEL_TEXT, adviceText, alarmText, hypText, signalLabel, unitText, validityHint } from "../lib/labels";
```

`AlarmNedeni` fonksiyonu içinde, `const ttl = ttlText(alarm.ttl_h);` satırının (satır 53) hemen altına ekle:

```tsx
  const gecerlilik = alarm.reason?.gecerlilik;
```

"Ne kadar acil?" bölümünü (satır 117-135) şu şekilde değiştir:

```tsx
      <section>
        <h3>Ne kadar acil?</h3>
        <div>
          {ttl ? (
            <div className="sig">
              <span>Sıcaklık sınırına tahmini</span>
              <b>{ttl}</b>
            </div>
          ) : (
            <p>{validityHint(gecerlilik, alarm.prio)}</p>
          )}
          {notified.length > 0 && (
            <p className="dim">
              Bildirildi: {notified.join(", ")}
              {alarm.escalation_level ? `, eskalasyon seviyesi ${alarm.escalation_level}` : ""}
            </p>
          )}
        </div>
      </section>
```

(Tek değişiklik: satır 126'daki `{alarm.prio === "P1" ? "Hemen müdahale gerekir." : "Süre tahmini yok."}` yerine `{validityHint(gecerlilik, alarm.prio)}` — geri kalan JSX AYNI.)

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Manual browser verification**

`cd frontend && npm run dev:mock` çalıştır, Chrome DevTools (veya benzeri) ile `/alarmlar` sayfasında bir alarm kartını aç, "Ne kadar acil?" bölümünün eskisi gibi göründüğünü doğrula (mock veri `gecerlilik` içermediği için `validityHint(undefined, prio)` eski davranışa düşer — bu BEKLENEN, regresyon değil). Ardından `frontend/src/api/mock.ts`'de GEÇİCİ olarak bir alarmın `reason.gecerlilik = "sensor_supheli"` yap, sayfayı yenile, yeni metnin göründüğünü doğrula, GEÇİCİ değişikliği geri al (commit etme).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/AlarmNedeni.tsx
git commit -m "feat(frontend): show validity-aware messaging in the urgency section"
```

---

## Task 7: frontend — `PanoDetay.tsx` ölçüm tablosuna Geçerlilik sütunu

**Files:**
- Modify: `frontend/src/pages/PanoDetay.tsx:571-630` (`OlcumTablosu`)

**Interfaces:**
- Consumes: `GECERLILIK_TEXT` (Task 5, `lib/labels.ts`), `p.gecerlilik` (Task 2'nin backend çıktısı, `ConnPoint.gecerlilik`).

- [ ] **Step 1: Modify the component**

`frontend/src/pages/PanoDetay.tsx` içinde import satırını (satır 24-30) güncelle:

```tsx
import {
  GECERLILIK_TEXT,
  STATE_TEXT,
  alarmText,
  hypText,
  panoTypeText,
  pointLabel,
} from "../lib/labels";
```

`OlcumTablosu` fonksiyonunun tablo başlığını (satır 586-594) güncelle:

```tsx
          <thead>
            <tr>
              <th>Nokta</th>
              <th className="r">Sıcaklık</th>
              <th className="r">Ortam üstü artış</th>
              <th className="r">K/K₀</th>
              <th className="r">Sınıra</th>
              <th>Durum</th>
              <th>Geçerlilik</th>
            </tr>
          </thead>
```

Ve satırları (satır 617-621, `<td>` bloğu) güncelle — `Durum` hücresinin hemen altına:

```tsx
                  <td>
                    <span className={`state st-${state}`}>
                      {STATE_TEXT[state]}
                    </span>
                  </td>
                  <td className="dim small">
                    {p.gecerlilik ? GECERLILIK_TEXT[p.gecerlilik] : "–"}
                  </td>
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 3: Manual browser verification**

`cd frontend && npm run dev:mock`, herhangi bir panonun `/pano/:id` sayfasını aç, "Tüm ölçüm noktaları" tablosunu genişlet, yeni "Geçerlilik" sütununun göründüğünü ve `gecerlilik` alanı mock veride yoksa "–" bastığını doğrula (regresyon yok — mevcut sütunlar aynı kalır).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/PanoDetay.tsx
git commit -m "feat(frontend): add Gecerlilik column to the measurement table"
```

---

## Task 8: SCADA ve bildirim tutarlılığı — doğrulama testleri

**Files:**
- Modify: `backend/tests/test_scada_encoder.py` (mevcut dosyaya ekle — dosyanın mevcut `None`/NA testinin hemen altına, gerçek deseni okuduktan sonra)
- Modify: `backend/tests/test_telegram.py` (mevcut dosyaya ekle — TTL testinin hemen altına, gerçek deseni okuduktan sonra)

**Interfaces:**
- Consumes: Task 1'in ürünü (artık `ttl_h`'in `q != 0` iken gerçekten `None` olması).
- Produces: Hiçbir yeni imza — bu görev, P1'in "API → UI → bildirim/SCADA temsillerindeki tutarlılığı kontrol et" maddesini KANITLAR; `docs/03-modbus-haritasi.md`/`docs/04-iec104-haritasi.md`'deki mevcut "Yok" (0x8000/0xFFFF, IEC104 IV) kuralının ve `templates.py:99-100`'deki `if ttl_h is not None` korumasının, Task 1'den sonra da hâlâ doğru çalıştığını gösterir. Prod kodu DEĞİŞMEZ (regresyon koruması).

- [ ] **Step 1: Read the existing patterns**

`backend/tests/test_scada_encoder.py` dosyasını aç, `None` değerli bir alanın NA sentinel'e (`0x8000`/`0xFFFF`) kodlandığını doğrulayan mevcut bir testi bul (yoksa `PanelEncoder`/`_raw` testlerinin genel desenini bul). `backend/tests/test_telegram.py` dosyasını aç, `ttl_h`'in mesaja dahil edildiği/edilmediği mevcut bir testi bul.

- [ ] **Step 2: Write the tests**

Bulduğun GERÇEK desenle (fixture adları, `PanelEncoder`/`RegisterMap` kurulumu, `telegram_alarm` çağrısı) birebir uyumlu iki test ekle:
- `test_scada_encoder.py`: bir noktanın `ttl_h=None` iken (q!=0 senaryosu simüle edilerek — Task 1'in ürettiği durum) ilgili Modbus register'ının `NA_UINT16`/`NA_INT16`'ya, IEC104 noktasının IV kalite bayrağına koştuğunu doğrula.
- `test_telegram.py`: `Alarm(..., ttl_h=None)` ile çağrıldığında üretilen mesaj metninde "Kalan Ömür (RUL)" ibaresinin GEÇMEDİĞİNİ doğrula.

- [ ] **Step 3: Run both test files**

Run: `cd backend && python -m pytest tests/test_scada_encoder.py tests/test_telegram.py -v`
Expected: PASS (prod kodu değişmedi; bu testler zaten doğru olan davranışı belgeliyor/kilitliyor).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_scada_encoder.py backend/tests/test_telegram.py
git commit -m "test(backend): lock in SCADA/Telegram consistency for null ttl_h"
```

---

## Task 9: Dokümantasyon — bilinen sınırı kapat, raporu tazele

**Files:**
- Modify: `docs/05-anomali-tespiti.md` (§10 "Bilinen sınırlar", S8 maddesi)
- Modify: `docs/12-dogrulama-sonuclari.md` (SCRIPT ile yeniden üretilir, elle düzenlenmez)
- Create: `docs/21-p1-tahmin-gecerliligi-tamamlandi.md`
- Modify: `INOVASYON-UYGULAMA-PLANI.md` (P1 kutucukları)

**Interfaces:** Yok — yalnızca dokümantasyon.

- [ ] **Step 1: Regenerate docs/12 and confirm the S8 numbers changed**

Run:
```bash
python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures
python scripts/validate.py --out docs/12-dogrulama-sonuclari.md
```
Beklenen: §4.3'teki "S8_sensor_fault: sınır HİÇ aşılmadığı halde 99 tahmin üretildi" cümlesindeki sayı DÜŞMELİ (ideal: 0'a yakın veya 0). Yeni üretim zamanı damgasını ve yeni sayıyı not al.

- [ ] **Step 2: Update docs/05 §10**

`docs/05-anomali-tespiti.md` §10'daki "Prognoz yanlış-alarmı (S8, sensör arızası)" maddesini, Adım 1'de ölçtüğün YENİ sayıyla ve "P1'de düzeltildi (`libs/panoalgo/panoalgo/edge.py` `_suppress_ttl_when_quality_suspect`)" notuyla güncelle. Madde tamamen 0'a düştüyse "artık üretilmiyor" diye yaz; hâlâ bir miktar kalıyorsa (örn. sınırın çok yakınında sürüklenme) dürüstçe kalan sayıyı yaz — uydurma.

- [ ] **Step 3: Write the P1 completion report**

`docs/21-p1-tahmin-gecerliligi-tamamlandi.md` dosyasını, [docs/20-p0-kanit-ve-sinir-raporu.md](../../20-p0-kanit-ve-sinir-raporu.md)'nin biçemini izleyerek yaz: hangi 6 görev (Task 1-8) hangi dosyalarda neyi değiştirdi, kabul senaryoları tablosunun 5 satırının hangi testte (Task 4) karşılandığı, docs/12'nin yeni S8 sayısı, ve P1'in "Teslim kapısı" şartının (bkz. plan §4) karşılandığının kanıtı (tüm testlerin yeşil olduğu komutlar).

- [ ] **Step 4: Check off the plan**

`INOVASYON-UYGULAMA-PLANI.md` §4'teki 6 P1 iş kutucuğunu `[x]` yap, "Çıktı" satırına `docs/21-p1-tahmin-gecerliligi-tamamlandi.md` linkini ekle (docs/20'deki desenle aynı).

- [ ] **Step 5: Final full-repo test sweep**

Run:
```bash
cd libs/panoalgo && python -m pytest -q
cd ../../backend && python -m pytest -q
cd ../frontend && npx tsc --noEmit && npm run test
```
Expected: Üç komut da PASS.

- [ ] **Step 6: Commit**

```bash
git add docs/05-anomali-tespiti.md docs/12-dogrulama-sonuclari.md docs/21-p1-tahmin-gecerliligi-tamamlandi.md INOVASYON-UYGULAMA-PLANI.md
git commit -m "docs: close S8 known-limit, regenerate validation report, record P1 completion"
```
