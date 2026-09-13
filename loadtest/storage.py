#!/usr/bin/env python3
"""Veri butcesi olcumu (TB3 Adim 6, Kisi B): depolama (sikistirmasiz / sikistirilmis) ve hucresel veri.

Kisa bir yuk testi TimescaleDB sikistirmasini oldugundan kotu gosterir (segmentler dolmaz). Bu betik BIR GUNLUK
sablon telemetriyi (loadtest/fleet.py PayloadFactory + ingest'in ayni duzlestirmesi) GECICI bir hypertable'a yazar,
uretimdekiyle ayni indeksle boyutu olcer, sonra pano+etiket segmentli sikistirir ve yeniden olcer. Uretim tablosuna
dokunmaz; gecici tablo sonunda silinir.

Hucresel veri: gercek JSON yuku + MQTT QoS 1 PUBLISH basligi (TCP/IP/TLS ek yuku haric; docs/09'da ayrica).

    backend/.venv/Scripts/python loadtest/storage.py --panels 5 --points 7
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "loadtest"))

SECONDS_PER_MONTH = 30 * 86400
TEST_TABLE = "gridup_storage_test"
DAY_START = datetime(2026, 9, 14, tzinfo=timezone.utc)  # tek gunluk parca (chunk) epoch gunune hizali


def mqtt_publish_bytes(*, payload_bytes: int, topic: str) -> int:
    """MQTT 3.1.1 QoS 1 PUBLISH: sabit baslik + kalan uzunluk (1-4 bayt) + topic alani + paket kimligi + yuk."""
    remaining = 2 + len(topic.encode("utf-8")) + 2 + payload_bytes
    length_bytes = 1 if remaining < 128 else 2 if remaining < 16384 else 3 if remaining < 2_097_152 else 4
    return 1 + length_bytes + remaining


def monthly_mb(*, bytes_per_message: float, period_s: float) -> float:
    return bytes_per_message * SECONDS_PER_MONTH / period_s / 1e6


def steady_state_gb(*, rows_per_day: float, raw_bytes_per_row: float, compressed_bytes_per_row: float, hot_days: int,
                    raw_retention_days: int, rollup_days: int, rollup_factor: int) -> dict[str, float]:
    """Kararli durum depolama: sicak (sikistirmasiz) + ilik (sikistirilmis ham) + uzun sureli ozet (rapor 6.8)."""
    hot = rows_per_day * hot_days * raw_bytes_per_row / 1e9
    warm = rows_per_day * (raw_retention_days - hot_days) * compressed_bytes_per_row / 1e9
    rollup = rows_per_day / rollup_factor * rollup_days * compressed_bytes_per_row / 1e9
    return {"hot_gb": hot, "warm_gb": warm, "rollup_gb": rollup, "total_gb": hot + warm + rollup}


def measure(dsn: str, *, panels: int, points: int, period_s: float) -> dict[str, Any]:
    import psycopg

    from app.config import load_contracts
    from app.ingest import flatten
    from fleet import PayloadFactory

    factory = PayloadFactory(load_contracts(ROOT / "contracts"), points=points, seed=20260914)
    messages_per_panel = int(86400 / period_s)
    sample = factory.payload("SIM-00001", 0, DAY_START)
    payload_bytes = len(json.dumps(sample, separators=(",", ":")).encode("utf-8"))

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")
        conn.execute(f"CREATE TABLE {TEST_TABLE} (LIKE telemetry INCLUDING DEFAULTS)")
        conn.execute(f"SELECT create_hypertable('{TEST_TABLE}', 'ts', chunk_time_interval => INTERVAL '1 day')")
        conn.execute(f"CREATE INDEX ON {TEST_TABLE} (pano_id, tag, ts DESC)")  # uretimdeki telemetry_pano_tag_ts_idx
        try:
            started = time.monotonic()
            rows = 0
            with conn.cursor() as cur, cur.copy(f"COPY {TEST_TABLE} (ts, pano_id, tag, value, q) FROM STDIN") as copy:
                for panel in range(1, panels + 1):
                    pano_id = f"SIM-{panel:05d}"
                    for seq in range(messages_per_panel):
                        ts = DAY_START + timedelta(seconds=seq * period_s)
                        for row in flatten(factory.payload(pano_id, seq, ts)):
                            copy.write_row((ts, pano_id, row.tag, row.value, row.q))
                            rows += 1
            load_s = time.monotonic() - started
            conn.execute(f"ANALYZE {TEST_TABLE}")
            [(raw_bytes,)] = conn.execute(f"SELECT hypertable_size('{TEST_TABLE}')").fetchall()
            conn.execute(
                f"ALTER TABLE {TEST_TABLE} SET (timescaledb.compress, "
                "timescaledb.compress_segmentby = 'pano_id, tag', timescaledb.compress_orderby = 'ts DESC')"
            )
            conn.execute(f"SELECT compress_chunk(c) FROM show_chunks('{TEST_TABLE}') c").fetchall()
            [(compressed_bytes,)] = conn.execute(f"SELECT hypertable_size('{TEST_TABLE}')").fetchall()
        finally:
            conn.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")

    raw_bpr, compressed_bpr = raw_bytes / rows, compressed_bytes / rows
    rows_per_message = rows / (panels * messages_per_panel)
    topic = "gridup/pano/SIM-00001/tel"
    wire = mqtt_publish_bytes(payload_bytes=payload_bytes, topic=topic)
    projections = {}
    for fleet in (100, 1000, 10000):
        rows_per_day = fleet * messages_per_panel * rows_per_message
        projections[str(fleet)] = {
            "rows_per_day": round(rows_per_day),
            "raw_gb_per_day": round(rows_per_day * raw_bpr / 1e9, 2),
            "compressed_gb_per_day": round(rows_per_day * compressed_bpr / 1e9, 3),
            "steady_state": {k: round(v, 1) for k, v in steady_state_gb(
                rows_per_day=rows_per_day, raw_bytes_per_row=raw_bpr, compressed_bytes_per_row=compressed_bpr,
                hot_days=7, raw_retention_days=90, rollup_days=730, rollup_factor=6).items()},
        }
    return {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "panels": panels,
        "points": points,
        "period_s": period_s,
        "rows": rows,
        "rows_per_message": round(rows_per_message, 1),
        "load_rows_per_s": round(rows / load_s),
        "raw_bytes_per_row": round(raw_bpr, 1),
        "compressed_bytes_per_row": round(compressed_bpr, 2),
        "compression_ratio": round(raw_bytes / compressed_bytes, 1),
        "projections": projections,
        "cellular": {
            "json_payload_bytes": payload_bytes,
            "mqtt_publish_bytes": wire,
            "mb_per_month_10s": round(monthly_mb(bytes_per_message=wire, period_s=10.0), 1),
            "mb_per_month_60s": round(monthly_mb(bytes_per_message=wire, period_s=60.0), 1),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--panels", type=int, default=5)
    parser.add_argument("--points", type=int, default=7)
    parser.add_argument("--period", type=float, default=10.0)
    parser.add_argument("--db", default="postgresql://postgres:gridup@localhost:5432/gridup")
    parser.add_argument("--out", default=str(ROOT / "loadtest" / "results"))
    args = parser.parse_args(argv)
    result = measure(args.db, panels=args.panels, points=args.points, period_s=args.period)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"storage-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{args.points}pt.json"
    (out / name).write_bytes(json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
