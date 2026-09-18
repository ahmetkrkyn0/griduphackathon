"""Depo kayitlarini contracts/openapi.yaml semalarina (PanelSummary, PanelDetail) cevirir.

Esikler alarm-codes.yaml'dan okunur; burada yalnizca sozlesmedeki alanlarin nasil
turetildigi yazilidir.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from ..config import PRIO_ORDER, Contracts
from ..models import PanelRecord

if TYPE_CHECKING:
    from ..alarm_manager import Alarm

# Hic veri gondermemis pano: elektriksel ariza kaniti yok ama izleme calismiyor.
NEVER_REPORTED_MODE = "HYP-SELF-FAULT"
# Kenar risk hesaplamadiysa (risk alani yok) varsayilan.
UNSCORED_MODE = "HYP-NORMAL"
REQUIRED_HYPOTHESES = (NEVER_REPORTED_MODE, UNSCORED_MODE)

POINT_OPTIONAL_FIELDS = ("k", "k_ratio", "tau_s", "ttl_h")

_DSYA_POINT = re.compile(r"DSYA(\d)_(L\d)")


def comms_ok_since(last_rx: datetime | None, contracts: Contracts, now: datetime) -> bool:
    """Merkez panodan son `heartbeat_timeout_min` icinde veri aldiysa haberlesme saglamdir."""
    if last_rx is None:
        return False
    return now - last_rx <= timedelta(minutes=contracts.thresholds["heartbeat_timeout_min"])


def is_comms_ok(record: PanelRecord, contracts: Contracts, now: datetime) -> bool:
    return comms_ok_since(record.last_rx, contracts, now)


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


#: GET /fleet/health satirinin `health` blogundan gelen alanlari — DeviceHealth ile AYNI adlar.
#: `fw` bu listede YOK: yukun KOK seviyesinde durur (bkz. panel_detail, asagida).
#: `baseline_day` de yok: panels tablosunda ayri bir karsiligi var ve
#: panel_summary'deki gibi telemetri degeri onceliklidir.
HEALTH_FIELDS = ("nodes_ok", "nodes_total", "rssi_dbm", "vbak_pct", "buffered", "maint_mode")


def panel_health(record: PanelRecord, contracts: Contracts, now: datetime) -> dict[str, Any]:
    """Cihaz sagligi satiri (TC3). panel_summary ile ayni turetme deseni.

    Telemetri hic gelmemis panoda saglik alanlari None doner — 0 YAZILMAZ:
    0 dBm gecerli bir RSSI'dir, "bilinmiyor" degildir ve ekran ikisini
    ayirt edebilmek zorundadir (bkz. CihazSagligi.tsx `isBad`).

    `fw`, panel_detail ile AYNI sekilde yukun kokunden yukseltilir; iki uc
    ayni alan icin farkli deger dondurmemeli (test_fleet_health_matches_panel_detail).
    """
    payload = record.payload or {}
    health = payload.get("health") or {}
    view: dict[str, Any] = {"pano_id": record.pano_id, "name": record.name}
    for field in HEALTH_FIELDS:
        view[field] = health.get(field)
    view["fw"] = payload.get("fw")
    baseline_day = health.get("baseline_day")
    view["baseline_day"] = record.baseline_day if baseline_day is None else baseline_day
    view["last_seen"] = last_seen(record).isoformat()
    view["comms_ok"] = is_comms_ok(record, contracts, now)
    return view


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


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def alarm_view(alarm: Alarm, contracts: Contracts) -> dict[str, Any]:
    """contracts/openapi.yaml Alarm semasi. Kimlik metin olarak dondurulur."""
    spec = contracts.alarm(alarm.code) or {}
    view: dict[str, Any] = {
        "id": str(alarm.id),
        "event_id": alarm.event_id,
        "pano_id": alarm.pano_id,
        "code": alarm.code,
        "text": spec.get("text", alarm.code),
        "prio": alarm.prio,
        "state": alarm.state,
        "raised_at": alarm.raised_at.isoformat(),
        "cleared_at": _iso(alarm.cleared_at),
        "acked_at": _iso(alarm.acked_at),
        "acked_by": alarm.acked_by,
        "shelved_until": _iso(alarm.shelved_until),
        "escalation_level": alarm.escalation_level,
        "notified": list(alarm.notified),
        "reason": alarm.reason,
        "ttl_h": alarm.ttl_h,
    }
    if alarm.advice is not None:
        view["advice"] = alarm.advice
    return view


def panel_detail(
    record: PanelRecord, contracts: Contracts, now: datetime, active_alarms: Iterable[Alarm] = ()
) -> dict[str, Any]:
    score, mode, _ = _risk(record.payload)
    detail: dict[str, Any] = {
        "pano_id": record.pano_id,
        "name": record.name,
        "pano_type": record.pano_type,
        "risk_score": score,
        "risk_mode": mode,
        "active_alarms": [alarm_view(alarm, contracts) for alarm in active_alarms],
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
