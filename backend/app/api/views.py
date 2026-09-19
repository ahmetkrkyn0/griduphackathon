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


def _risk(payload: dict[str, Any] | None) -> tuple[int, str, float | None]:
    if payload is None:
        return 0, NEVER_REPORTED_MODE, None
    risk = payload.get("risk") or {}
    return int(risk.get("score", 0)), risk.get("mode", UNSCORED_MODE), risk.get("ttl_h")


def last_seen(record: PanelRecord) -> datetime:
    return record.last_rx or record.installed_at


def _iso(value: datetime | None) -> str | None:
    """None KORUNUR: "olcmedik/almadik" ile bir tarih arasindaki fark kaybolmamali."""
    return value.isoformat() if value is not None else None


def asset_view(record: PanelRecord) -> dict[str, Any] | None:
    """AssetRegistry semasi; kunye ice aktarilmamissa None (F-21).

    Bos kunyeyi "hepsi null olan bir sozluk" olarak dondurmek, ekranda bos hucre uretirdi
    ve bos hucre "degeri sifir/bilinmiyor" gibi okunurdu. `null` donmek ekrani
    "CBS'den ice aktarilmadi" yazmaya ZORLAR.
    """
    if not record.has_asset:
        return None
    return {
        "cbs_kodu": record.cbs_kodu,
        "fider_id": record.fider_id,
        "il": record.il,
        "ilce": record.ilce,
        "abone_sayisi": record.abone_sayisi,
        "trafo_kva": record.trafo_kva,
        "kritiklik": record.kritiklik,
        # UYDURULMAZ: aktarim doldurmadiysa null kalir (backlog F-21 "Dikkat" satiri).
        "uretici": record.uretici,
        "seri_no": record.seri_no,
        "son_bakim_at": _iso(record.son_bakim_at),
        "sonraki_bakim_at": _iso(record.sonraki_bakim_at),
        "kunye_kaynak": record.kunye_kaynak,
        "kunye_at": _iso(record.kunye_at),
    }


def asset_coverage(records: Iterable[PanelRecord]) -> dict[str, int]:
    """Kapsama SAYIYLA verilir ki eksiklik gizlenemesin (GK10)."""
    records = list(records)
    return {
        "panolar": len(records),
        "kunyeli": sum(1 for r in records if r.has_asset),
        "fiderli": sum(1 for r in records if r.fider_id is not None),
        "aboneli": sum(1 for r in records if r.abone_sayisi is not None),
    }


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
        # Varlik kutugu (F-21) — ozete YALNIZCA uc alan girer: etki ekseni, onceliklendirme
        # ve bakim vadesi rozeti. Kunyenin tamami panel_detail'dedir.
        "abone_sayisi": record.abone_sayisi,
        "kritiklik": record.kritiklik,
        "sonraki_bakim_at": _iso(record.sonraki_bakim_at),
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


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def alarm_view(alarm: Alarm, contracts: Contracts, outages: Any = None) -> dict[str, Any]:
    """contracts/openapi.yaml Alarm semasi. Kimlik metin olarak dondurulur.

    `outages` verilirse (api/outages.OutageIndex) alarm bir ust sebeke kesintisine baglanir
    (F-22). Verilmezse alan HIC YAZILMAZ — "baglanti yok" ile "baginti sorgulanmadi" ayni
    sey degildir ve sozlesmede alan zaten zorunlu degildir.
    """
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
    if outages is not None:
        outage_id = outages.of(alarm.pano_id, alarm.raised_at)
        if outage_id is not None:
            view["outage_id"] = outage_id
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
        "asset": asset_view(record),
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
    baseline_day = health.get("baseline_day")
    if baseline_day is None:
        baseline_day = record.baseline_day
    detail.update(
        ts=payload["ts"],
        risk_contributions=(payload.get("risk") or {}).get("contributions", {}),
        points=[point_view(p, contracts.thresholds, comms_ok, baseline_day) for p in payload["t_conn"]],
        env=payload["env"],
        elec=payload["elec"],
        pd=payload.get("pd"),
        health=health,
    )
    if payload.get("tvoc") is not None:
        detail["tvoc"] = payload["tvoc"]
    return detail
