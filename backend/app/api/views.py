"""Depo kayitlarini contracts/openapi.yaml semalarina (PanelSummary, PanelDetail) cevirir.

Esikler alarm-codes.yaml'dan okunur; burada yalnizca sozlesmedeki alanlarin nasil
turetildigi yazilidir.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from ..config import PRIO_ORDER, Contracts
from ..models import PanelRecord

# Hic veri gondermemis pano: elektriksel ariza kaniti yok ama izleme calismiyor.
NEVER_REPORTED_MODE = "HYP-SELF-FAULT"
# Kenar risk hesaplamadiysa (risk alani yok) varsayilan.
UNSCORED_MODE = "HYP-NORMAL"
REQUIRED_HYPOTHESES = (NEVER_REPORTED_MODE, UNSCORED_MODE)

POINT_OPTIONAL_FIELDS = ("k", "k_ratio", "tau_s", "ttl_h")

_DSYA_POINT = re.compile(r"DSYA(\d)_(L\d)")


def is_comms_ok(record: PanelRecord, contracts: Contracts, now: datetime) -> bool:
    if record.last_rx is None:
        return False
    return now - record.last_rx <= timedelta(minutes=contracts.thresholds["heartbeat_timeout_min"])


def top_alarm(codes: list[str], contracts: Contracts) -> tuple[str | None, str | None]:
    """En yuksek oncelikli kod; esitlikte kenarin gonderdigi sira korunur."""
    best: tuple[int, str, str | None] | None = None
    for code in codes:
        prio = contracts.prio_of(code)
        rank = PRIO_ORDER.index(prio) if prio in PRIO_ORDER else len(PRIO_ORDER)
        if best is None or rank < best[0]:
            best = (rank, code, prio)
    return (best[1], best[2]) if best else (None, None)


def point_label(pt: str) -> str:
    """GIRIS_L2 -> 'Giriş L2', DSYA3_L2 -> 'DSYA-3 L2'."""
    if pt.startswith("GIRIS_"):
        return "Giriş " + pt.removeprefix("GIRIS_")
    match = _DSYA_POINT.fullmatch(pt)
    return f"DSYA-{match[1]} {match[2]}" if match else pt


def point_state(point: dict[str, Any], thresholds: dict[str, Any], comms_ok: bool) -> str:
    """Dijital ikiz rengi. Esik metinleri "... ustu" oldugu icin karsilastirma kesin buyuktur."""
    if not comms_ok or point.get("q", 0) != 0:
        return "stale"

    def above(value: float | None, limit_name: str) -> bool:
        return value is not None and value > thresholds[limit_name]

    dt_c, k_ratio = point["dt_c"], point.get("k_ratio")
    if above(dt_c, "bus_rise_alarm_k"):
        return "critical"
    if above(dt_c, "term_rise_alarm_k") or above(k_ratio, "k_ratio_alarm"):
        return "alarm"
    if above(dt_c, "term_rise_warn_k") or above(k_ratio, "k_ratio_warn"):
        return "warn"
    return "normal"


def _risk(payload: dict[str, Any] | None) -> tuple[int, str, float | None]:
    if payload is None:
        return 0, NEVER_REPORTED_MODE, None
    risk = payload.get("risk") or {}
    return int(risk.get("score", 0)), risk.get("mode", UNSCORED_MODE), risk.get("ttl_h")


def last_seen(record: PanelRecord) -> datetime:
    return record.last_rx or record.installed_at


def panel_summary(record: PanelRecord, contracts: Contracts, now: datetime) -> dict[str, Any]:
    payload = record.payload or {}
    score, mode, ttl_h = _risk(record.payload)
    alarm, prio = top_alarm(payload.get("alarms") or [], contracts)
    baseline_day = (payload.get("health") or {}).get("baseline_day")
    return {
        "pano_id": record.pano_id,
        "name": record.name,
        "lat": record.lat,
        "lon": record.lon,
        "pano_type": record.pano_type,
        "risk_score": score,
        "risk_mode": mode,
        "top_alarm": alarm,
        "top_prio": prio,
        "ttl_h": ttl_h,
        "last_seen": last_seen(record).isoformat(),
        "comms_ok": is_comms_ok(record, contracts, now),
        "baseline_day": record.baseline_day if baseline_day is None else baseline_day,
    }


def point_view(point: dict[str, Any], thresholds: dict[str, Any], comms_ok: bool) -> dict[str, Any]:
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
    view["state"] = point_state(point, thresholds, comms_ok)
    return view


def panel_detail(record: PanelRecord, contracts: Contracts, now: datetime) -> dict[str, Any]:
    score, mode, _ = _risk(record.payload)
    detail: dict[str, Any] = {
        "pano_id": record.pano_id,
        "name": record.name,
        "pano_type": record.pano_type,
        "risk_score": score,
        "risk_mode": mode,
        "active_alarms": [],  # TB2: alarm yoneticisi doldurur
    }
    payload = record.payload
    if payload is None:
        return {
            **detail,
            "ts": record.installed_at.isoformat(),
            "risk_contributions": {},
            "points": [],
            "env": {},
            "elec": {},
            "health": {},
        }

    comms_ok = is_comms_ok(record, contracts, now)
    health = dict(payload["health"])
    if "fw" in payload:
        health["fw"] = payload["fw"]
    detail.update(
        ts=payload["ts"],
        risk_contributions=(payload.get("risk") or {}).get("contributions", {}),
        points=[point_view(p, contracts.thresholds, comms_ok) for p in payload["t_conn"]],
        env=payload["env"],
        elec=payload["elec"],
        pd=payload.get("pd"),
        health=health,
    )
    if payload.get("tvoc") is not None:
        detail["tvoc"] = payload["tvoc"]
    return detail
