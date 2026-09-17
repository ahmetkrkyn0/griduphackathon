"""GET /api/v1/panels, GET /api/v1/panels/{pano_id} (TB1)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request

from .views import last_seen, panel_detail, panel_health_summary, panel_summary

router = APIRouter(prefix="/api/v1", tags=["panels"])


@router.get("/fleet/health")
def get_fleet_health(request: Request, limit: int = Query(2000, ge=0, le=5000)) -> list[dict[str, Any]]:
    state = request.app.state
    now = state.clock()
    records = state.store.list_panels()
    records.sort(key=lambda r: r.pano_id)
    return [panel_health_summary(r, state.contracts, now) for r in records[:limit]]


@router.get("/panels")
def list_panels(
    request: Request,
    sort: Literal["risk", "last_seen", "pano_id"] = "risk",
    min_risk: int | None = Query(None, ge=0, le=100),
    limit: int = Query(200, ge=0, le=2000),
) -> list[dict[str, Any]]:
    state = request.app.state
    now = state.clock()
    pairs = [(record, panel_summary(record, state.contracts, now)) for record in state.store.list_panels()]
    if min_risk is not None:
        pairs = [(r, s) for r, s in pairs if s["risk_score"] >= min_risk]

    pairs.sort(key=lambda pair: pair[0].pano_id)  # esitliklerde kararli sira
    if sort == "risk":
        pairs.sort(key=lambda pair: pair[1]["risk_score"], reverse=True)
    elif sort == "last_seen":
        pairs.sort(key=lambda pair: last_seen(pair[0]), reverse=True)
    return [summary for _, summary in pairs[:limit]]


@router.get("/panels/{pano_id}")
def get_panel(request: Request, pano_id: str) -> dict[str, Any]:
    state = request.app.state
    if not state.contracts.pano_id_re.fullmatch(pano_id):
        raise HTTPException(status_code=422, detail=f"gecersiz pano_id bicimi: {pano_id}")
    record = state.store.get_panel(pano_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"pano bulunamadi: {pano_id}")
    return panel_detail(record, state.contracts, state.clock(), state.alarms.active_for_panel(pano_id))


@router.get("/panels/{pano_id}/power-quality")
def get_panel_power_quality(request: Request, pano_id: str) -> dict[str, Any]:
    from panoalgo.power_quality import evaluate_power_quality

    state = request.app.state
    if not state.contracts.pano_id_re.fullmatch(pano_id):
        raise HTTPException(status_code=422, detail=f"gecersiz pano_id bicimi: {pano_id}")
    record = state.store.get_panel(pano_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"pano bulunamadi: {pano_id}")

    payload = record.payload or {}
    elec = payload.get("elec") or {}
    u_ph = elec.get("u_ph") or [230.0, 230.0, 230.0]
    unbal = float(elec.get("unbal_pct", 0.0))
    thd_i = elec.get("thd_i")
    report = evaluate_power_quality(u_ph, unbal, thd_i)
    return {
        "pano_id": pano_id,
        "ts": payload.get("ts"),
        "power_quality": report.to_dict(),
    }

