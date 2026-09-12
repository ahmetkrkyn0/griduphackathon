"""GET /api/v1/alarms (TB1: sozlesme filtrelerini kabul eden bos liste).

Alarm yoneticisi, onay (ack) ve raf (shelve) uclari TB2'de gelir.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["alarms"])


@router.get("/alarms")
def list_alarms(
    state: str = "active,acked",
    prio: str | None = None,
    pano_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    return []
