"""Analiz uclari (TB3, Kisi B): zaman serisi, olay kara kutusu, filo KPI'lari. Sozlesme: contracts/openapi.yaml.

C'nin TC3 ekranlari (trend/korelasyon, olay analizi, cihaz sagligi) bunlari okur.

Seri kurallari (docs/02, docs/09):
  - Etiketler ingest'in uzun format adlaridir (`t_conn.GIRIS_L2.dt_c`, `elec.i_ph.1`); kisaltmalar:
    `k_index.<nokta>` -> `t_conn.<nokta>.k_ratio`, `t_conn.<nokta>` -> `t_conn.<nokta>.t_c`.
  - Kova Unix epoch'a hizali `step` araligidir; deger kovadaki TEMIZ (q = 0) olcumlerin ortalamasidir.
    Olcumu olmayan kova `null`: bosluk cizimde bosluk olarak gorunur, sifir olarak degil.
  - En kucuk adim 10 s (telemetri periyodu), etiket basina en fazla 2000 nokta, istek basina 12 etiket.

KPI tanimlari (ISA-18.2 / EEMUA 191):
  - alarms_per_100_panels_per_day: son 24 saatte olusan alarm (tum oncelikler) / pano sayisi x 100.
  - distribution_pct: son 7 gunde olusan P1/P2/P3 dagilimi (hedef %5 / %15 / %80; SYS ve INFO proses alarmi degil).
  - p95_end_to_end_ms: son 24 saatte olusan alarmlarin olay zamanindan telefona (SMS/WhatsApp) ilk basarili
    teslimine gecikmenin 95. yuzdeligi (en yakin sira yontemi). Teslim yoksa alan yazilmaz: "0 ms" yanlis olurdu.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..config import PRIO_ORDER, Contracts
from ..db import SERIES_ORIGIN
from ..models import JournalEntry
from .views import is_comms_ok, point_label

router = APIRouter(prefix="/api/v1")

MIN_STEP = timedelta(seconds=10)
MAX_POINTS_PER_TAG = 2000
MAX_TAGS = 12
_STEP = re.compile(r"^(\d{1,6})([smhd])$")
_STEP_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_TAG = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){1,3}$")

BLACKBOX_TAIL = timedelta(hours=1)  # olay sonrasi: onay, temizlenme, trip sonrasi sicaklik dususu
BLACKBOX_MAX_POINTS = 500
BLACKBOX_STEPS = tuple(timedelta(minutes=m) for m in (1, 5, 10, 15, 30, 60))
BLACKBOX_POINT_FIELDS = ("t_c", "dt_c", "k_ratio")
BLACKBOX_PANEL_TAGS = (
    "elec.i_ph.0", "elec.i_ph.1", "elec.i_ph.2", "elec.i_n",
    "env.t_low_c", "env.rh_low_pct", "env.td_margin_k",
    "tvoc.trips", "tvoc.prot_health_ok", "risk.score",
)
ARC_TRIP = "ALM-ARC-TRIP"

KPI_RATE_WINDOW = timedelta(days=1)
KPI_DISTRIBUTION_WINDOW = timedelta(days=7)
PROCESS_PRIOS = ("P1", "P2", "P3")
LIVE_STATES = ("active", "acked")


# ================================================================== yardimcilar
def parse_step(raw: str) -> timedelta:
    match = _STEP.fullmatch(raw.strip())
    if match is None:
        raise HTTPException(status_code=422, detail=f"gecersiz step: {raw!r} (or. 10s, 1m, 15m, 1h)")
    step = timedelta(seconds=int(match[1]) * _STEP_SECONDS[match[2]])
    if step < MIN_STEP:
        raise HTTPException(status_code=422, detail=f"step en az {MIN_STEP.total_seconds():.0f} s olmali (telemetri periyodu)")
    return step


def storage_tag(tag: str) -> str:
    parts = tag.split(".")
    if parts[0] == "k_index" and len(parts) == 2:
        return f"t_conn.{parts[1]}.k_ratio"
    if parts[0] == "t_conn" and len(parts) == 2:
        return f"t_conn.{parts[1]}.t_c"
    return tag


def bucket_starts(start: datetime, end: datetime, step: timedelta, limit: int) -> list[datetime]:
    first = SERIES_ORIGIN + ((start - SERIES_ORIGIN) // step) * step
    count = math.ceil((end - first) / step)
    if count > limit:
        raise HTTPException(status_code=422, detail=f"{count} nokta istendi, sinir {limit}: araligi daraltin veya step'i buyutun")
    return [first + index * step for index in range(count)]


def unix_ms(value: datetime) -> int:
    return (value - SERIES_ORIGIN) // timedelta(milliseconds=1)


def fill(buckets: Sequence[datetime], values: dict[datetime, float]) -> list[list[Any]]:
    return [[unix_ms(bucket), values.get(bucket)] for bucket in buckets]


def nearest_rank(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile / 100.0 * len(ordered)))
    return round(ordered[rank - 1], 1)


def _aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise HTTPException(status_code=422, detail=f"{name} saat dilimi icermeli (or. 2026-09-13T10:00:00Z)")
    return value


# ================================================================== /panels/{id}/series
@router.get("/panels/{pano_id}/series", tags=["panels"])
def panel_series(
    request: Request,
    pano_id: str,
    tags: str,
    start: datetime = Query(alias="from"),
    end: datetime = Query(alias="to"),
    step: str = "1m",
) -> dict[str, list[list[Any]]]:
    state = request.app.state
    if not state.contracts.pano_id_re.fullmatch(pano_id):
        raise HTTPException(status_code=422, detail=f"gecersiz pano_id bicimi: {pano_id}")
    start, end = _aware(start, "from"), _aware(end, "to")
    if start >= end:
        raise HTTPException(status_code=422, detail="from, to'dan once olmali")
    requested = list(dict.fromkeys(tag.strip() for tag in tags.split(",") if tag.strip()))
    if not requested or len(requested) > MAX_TAGS or any(not _TAG.fullmatch(tag) for tag in requested):
        raise HTTPException(status_code=422, detail=f"tags: 1-{MAX_TAGS} etiket, yalnizca harf/rakam/_ ve nokta")
    interval = parse_step(step)
    buckets = bucket_starts(start, end, interval, MAX_POINTS_PER_TAG)
    if not state.store.list_panels([pano_id]):
        raise HTTPException(status_code=404, detail=f"pano bulunamadi: {pano_id}")

    stored = {tag: storage_tag(tag) for tag in requested}
    data = state.store.series(pano_id, sorted(set(stored.values())), start, end, interval)
    return {tag: fill(buckets, data.get(stored[tag], {})) for tag in requested}


# ================================================================== /events/{id}/blackbox
@router.get("/events/{event_id}/blackbox", tags=["events"])
def event_blackbox(request: Request, event_id: str, window_h: int = Query(72, ge=1, le=336)) -> dict[str, Any]:
    # Ust sinir 336 sa (14 gun): docs/12 §2'de olculen en erken tespit, sabit 70 K esiginden
    # 209 saat once. 168 sa'lik eski sinirla bozulmanin baslangici pencereye hicbir ayarla
    # giremiyordu. Yuk artmaz: 336 sa + 1 sa kuyruk, 60 dk'lik en kaba kovada 338 nokta eder
    # (BLACKBOX_MAX_POINTS = 500), yani asagidaki adim secimi kendiliginden saatlige duser.
    state = request.app.state
    event = state.store.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"olay bulunamadi: {event_id}")
    start = event.occurred_at - timedelta(hours=window_h)
    end = event.occurred_at + BLACKBOX_TAIL
    interval = next((s for s in BLACKBOX_STEPS if math.ceil((end - start) / s) <= BLACKBOX_MAX_POINTS), BLACKBOX_STEPS[-1])
    buckets = bucket_starts(start, end, interval, limit=math.ceil((end - start) / interval) + 1)

    tags = list(BLACKBOX_PANEL_TAGS)
    if event.point:
        tags = [f"t_conn.{event.point}.{field}" for field in BLACKBOX_POINT_FIELDS] + tags
    data = state.store.series(event.pano_id, tags, start, end, interval)
    journal = state.store.panel_journal(event.pano_id, start, end)
    return {
        "event_id": event.event_id,
        "pano_id": event.pano_id,
        "occurred_at": event.occurred_at.isoformat(),
        "code": event.code,
        "det_label": event.det_label or (point_label(event.point) if event.point else None),
        "window_h": window_h,
        "series": {tag: fill(buckets, data.get(tag, {})) for tag in tags},
        "timeline": [timeline_entry(entry, state.contracts) for entry in journal],
    }


_ESCALATION_STEPS = {"call": "arama", "escalate": "ust amire eskalasyon"}


def timeline_entry(entry: JournalEntry, contracts: Contracts) -> dict[str, str]:
    where = f", {point_label(entry.point)}" if entry.point else ""
    subject = f"{entry.code} ({entry.prio}{where})"
    detail = f" - {entry.note}" if entry.note else ""
    kind, text = "alarm", f"{subject} {entry.action}"
    if entry.action == "raised":
        kind = "trip" if entry.code == ARC_TRIP else "alarm"
        text = f"{subject} olustu: {(contracts.alarm(entry.code) or {}).get('text', entry.code)}"
    elif entry.action == "acked":
        kind, text = "ack", f"{subject} onaylandi: {entry.by_user}{detail}"
    elif entry.action == "shelved":
        kind, text = "action", f"{subject} rafa alindi: {entry.by_user}{detail}"
    elif entry.action == "escalated":
        kind, text = "action", f"{subject} {_ESCALATION_STEPS.get(entry.note or '', entry.note)}"
    elif entry.action == "notified":
        kind, text = "action", f"{subject} bildirim iletildi: {entry.note}"
    elif entry.action == "unshelved":
        text = f"{subject} raf suresi doldu, yeniden duyuruldu"
    elif entry.action == "reactivated":
        text = f"{subject} yeniden alarma girdi"
    elif entry.action == "returned":
        text = f"{subject} normale dondu, onay bekliyor"
    elif entry.action == "cleared":
        text = f"{subject} temizlendi"
    return {"ts": entry.at.isoformat(), "kind": kind, "text": text}


# ================================================================== /fleet/kpi
@router.get("/fleet/kpi", tags=["system"])
def fleet_kpi(request: Request) -> dict[str, Any]:
    state = request.app.state
    now = state.clock()
    records = state.store.list_panels()
    total = len(records)
    comms_ok = sum(1 for record in records if is_comms_ok(record, state.contracts, now))
    day = state.store.alarm_counts(now - KPI_RATE_WINDOW)
    week = state.store.alarm_counts(now - KPI_DISTRIBUTION_WINDOW)
    process = sum(week.get(prio, 0) for prio in PROCESS_PRIOS)
    active = dict.fromkeys(PRIO_ORDER, 0)
    for alarm in state.alarms.load().open_alarms():
        if alarm.state in LIVE_STATES:
            active[alarm.prio] = active.get(alarm.prio, 0) + 1

    body: dict[str, Any] = {
        "panels_total": total,
        "comms_ok_pct": round(100.0 * comms_ok / total, 1) if total else 0.0,
        "alarms_per_100_panels_per_day": round(100.0 * sum(day.values()) / total, 2) if total else 0.0,
        "active_by_prio": active,
        "distribution_pct": {prio: round(100.0 * week.get(prio, 0) / process, 1) if process else 0.0 for prio in PROCESS_PRIOS},
        "ingest_msgs_per_s": round(state.pipeline.msgs_per_s(), 3),
    }
    latencies = state.store.delivery_latencies_ms(now - KPI_RATE_WINDOW)
    if latencies:
        body["p95_end_to_end_ms"] = nearest_rank(latencies, 95)
    return body
