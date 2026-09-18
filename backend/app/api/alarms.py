"""Alarm konsolu uclari (TB2): GET /api/v1/alarms, POST .../ack, POST .../shelve.

Sozlesme: contracts/openapi.yaml. Is kurallari (raf siniri, P1 rafa alinamaz, gerekce zorunlu)
alarm yoneticisindedir ve esikleri alarm-codes.yaml'dan okur; burada yalnizca HTTP durum kodlarina
cevrilir: 403 bastirilamaz, 404 yok, 409 durum uygun degil, 422 gecersiz istek.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..alarm_manager import AlarmNotFound, AlarmNotSuppressible, AlarmStateConflict
from ..auth import Identity, require
from ..config import PRIO_ORDER
from .outages import OutageIndex
from .views import alarm_view

router = APIRouter(prefix="/api/v1", tags=["alarms"])

ALARM_STATES = ("active", "acked", "shelved", "cleared")


# F-19: `by` alani govdeden KALDIRILDI. Onaylayanin kimligi artik dogrulanmis
# Authorization basligindan gelir (app/auth.py). Govdede kalsaydi istemci denetim
# izine istedigi adi yazabilirdi. Govdeye elle `by` eklemek sessizce yok sayilir —
# Pydantic varsayilani fazladan alani gormezden gelir ve bu davranis testle kilitli
# (test_api_alarms: govdedeki by YOK SAYILIR).
class AckRequest(BaseModel):
    note: str | None = None
    channel: Literal["ui", "sms", "scada"] = "ui"


class ShelveRequest(BaseModel):
    minutes: int
    reason: str


def _csv(raw: str, allowed: tuple[str, ...], name: str) -> list[str]:
    values = [value.strip() for value in raw.split(",") if value.strip()]
    invalid = [value for value in values if value not in allowed]
    if invalid or not values:
        raise HTTPException(status_code=422, detail=f"gecersiz {name}: {raw!r} (gecerli: {', '.join(allowed)})")
    return values


def _alarm_id(raw: str) -> int:
    if not raw.isdigit():
        raise HTTPException(status_code=404, detail=f"alarm bulunamadi: {raw}")
    return int(raw)


@router.get("/alarms")
def list_alarms(
    request: Request,
    state: str = "active,acked",
    prio: str | None = None,
    pano_id: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[dict[str, Any]]:
    states = _csv(state, ALARM_STATES, "state")
    prios = _csv(prio, PRIO_ORDER, "prio") if prio is not None else None
    app_state = request.app.state
    alarms = app_state.alarms.list_alarms(states, prios, pano_id, limit)
    # F-22: alt alarmi ust sebeke kesintisine BAGLAR (bastirmaz). Baglanti saklanmaz,
    # pano + zaman penceresinden turetilir — bkz. api/outages.py OutageIndex.
    index = OutageIndex(app_state.store.list_outages(only_open=False))
    return [alarm_view(alarm, app_state.contracts, outages=index) for alarm in alarms]


@router.post("/alarms/{alarm_id}/ack")
def ack_alarm(
    request: Request,
    alarm_id: str,
    body: AckRequest,
    identity: Identity = Depends(require("operator")),
) -> dict[str, bool]:
    try:
        request.app.state.alarms.ack(_alarm_id(alarm_id), by=identity.user, note=body.note)
    except AlarmNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AlarmStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/alarms/{alarm_id}/shelve")
def shelve_alarm(
    request: Request,
    alarm_id: str,
    body: ShelveRequest,
    identity: Identity = Depends(require("operator")),
) -> dict[str, bool]:
    try:
        request.app.state.alarms.shelve(
            _alarm_id(alarm_id), by=identity.user, minutes=body.minutes, reason=body.reason
        )
    except AlarmNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AlarmNotSuppressible as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AlarmStateConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}
