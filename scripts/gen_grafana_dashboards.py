#!/usr/bin/env python3
"""Grafana panolarini (deploy/grafana/dashboards/*.json) uretir (Kisi B, TB3 Adim 5).

PLAN.md kural 7: Grafana JSON'u elle duzenlenmez, birlestirilemez; bu betik tek kaynaktir. Kural 10: EEMUA 191
esikleri, oncelik dagilimi hedefi ve haberlesme zaman asimi contracts/alarm-codes.yaml'dan okunur.

    olcek.json      yuk testi (loadtest/fleet.py -> loadtest_metrics) + canli alim hizi (telemetry)
    alarm-kpi.json  ISA-18.2 / EEMUA 191 alarm performansi: gunluk alarm, dagilim, etkin alarm, bildirim gecikmesi

    backend/.venv/Scripts/python scripts/gen_grafana_dashboards.py            # yeniler
    backend/.venv/Scripts/python scripts/gen_grafana_dashboards.py --check    # guncel degilse 1 ile cikar
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Contracts, load_contracts  # noqa: E402

OUT_DIR = ROOT / "deploy" / "grafana" / "dashboards"
DS = {"type": "grafana-postgresql-datasource", "uid": "gridup-tsdb"}
PHONE_CHANNELS = "('sms', 'whatsapp')"  # app/db.py PHONE_CHANNELS ile ayni tanim (API /fleet/kpi)


# ------------------------------------------------------------------ panel yapicilari
class Layout:
    """Panelleri 24 sutunluk izgaraya soldan saga, satir satir yerlestirir."""

    def __init__(self) -> None:
        self.x = self.y = self.row_h = 0
        self.next_id = 1

    def place(self, w: int, h: int) -> tuple[int, dict[str, int]]:
        if self.x + w > 24:
            self.x, self.y, self.row_h = 0, self.y + self.row_h, 0
        pos = {"h": h, "w": w, "x": self.x, "y": self.y}
        self.x += w
        self.row_h = max(self.row_h, h)
        panel_id, self.next_id = self.next_id, self.next_id + 1
        return panel_id, pos


def _target(sql: str, fmt: str) -> dict[str, Any]:
    return {"datasource": DS, "editorMode": "code", "format": fmt, "rawQuery": True, "rawSql": sql.strip(), "refId": "A"}


def _panel(layout: Layout, kind: str, title: str, sql: str, *, w: int, h: int, fmt: str, description: str,
           defaults: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    panel_id, pos = layout.place(w, h)
    return {
        "id": panel_id,
        "type": kind,
        "title": title,
        "description": description,
        "datasource": DS,
        "gridPos": pos,
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": options,
        "targets": [_target(sql, fmt)],
    }


def timeseries(layout: Layout, title: str, sql: str, *, unit: str, description: str, w: int = 12, h: int = 8) -> dict[str, Any]:
    return _panel(
        layout, "timeseries", title, sql, w=w, h=h, fmt="time_series", description=description,
        defaults={"unit": unit, "custom": {"lineWidth": 2, "fillOpacity": 10, "spanNulls": False}},
        options={"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True}, "tooltip": {"mode": "multi", "sort": "none"}},
    )


def stat(layout: Layout, title: str, sql: str, *, unit: str, description: str, steps: list[tuple[str, float | None]],
         w: int = 6, h: int = 5, decimals: int | None = None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "unit": unit,
        "thresholds": {"mode": "absolute", "steps": [{"color": color, "value": value} for color, value in steps]},
    }
    if decimals is not None:
        defaults["decimals"] = decimals
    return _panel(
        layout, "stat", title, sql, w=w, h=h, fmt="table", description=description, defaults=defaults,
        options={"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}, "colorMode": "value",
                 "graphMode": "none", "justifyMode": "auto", "textMode": "auto"},
    )


def table(layout: Layout, title: str, sql: str, *, description: str, w: int = 12, h: int = 8) -> dict[str, Any]:
    return _panel(layout, "table", title, sql, w=w, h=h, fmt="table", description=description,
                  defaults={"custom": {"align": "auto"}}, options={"showHeader": True, "cellHeight": "sm"})


def dashboard(uid: str, title: str, description: str, panels: list[dict[str, Any]], *, time_from: str,
              templating: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "uid": uid,
        "title": title,
        "description": description,
        "tags": ["gridup", "TB3"],
        "timezone": "browser",
        "editable": True,
        "graphTooltip": 1,
        "refresh": "10s",
        "schemaVersion": 39,
        "version": 1,
        "time": {"from": time_from, "to": "now"},
        "templating": {"list": templating or []},
        "annotations": {"list": []},
        "panels": panels,
    }


# ------------------------------------------------------------------ panolar
def olcek(contracts: Contracts) -> dict[str, Any]:
    layout = Layout()
    metric = """
SELECT $__timeGroupAlias(ts, '10s'), metric, avg(value) AS value
FROM loadtest_metrics
WHERE $__timeFilter(ts) AND run_id = '$run' AND metric IN ({metrics})
GROUP BY 1, metric
ORDER BY 1
"""

    def series(title: str, metrics: tuple[str, ...], unit: str, description: str, w: int = 12) -> dict[str, Any]:
        return timeseries(layout, title, metric.format(metrics=", ".join(f"'{m}'" for m in metrics)), unit=unit, description=description, w=w)

    panels = [
        series("Yayın ve yazma hızı (mesaj/s)", ("publish_per_s", "ingest_written_per_s"), "short",
               "Yük aracının yayın hızı ile backend'in veritabanına yazdığı mesaj hızı. İkisi örtüşüyorsa kuyruk birikmiyor."),
        series("Alım gecikmesi p95 (ms)", ("receive_p95_ms",), "ms",
               "Yayından backend'in mesajı aldığı ana (broker + ağ + ayrıştırma), 10 s pencerelerde p95. Saat farkı düzeltilmiş."),
        series("CPU (%)", ("backend_cpu_pct", "timescaledb_cpu_pct", "mosquitto_cpu_pct"), "percent",
               "docker stats; %100 = bir çekirdek."),
        series("Bellek (MiB)", ("backend_mem_mib", "timescaledb_mem_mib", "mosquitto_mem_mib"), "decmbytes",
               "docker stats kullanılan bellek."),
        series("Telemetri tablosu (MB)", ("telemetry_mb",), "decmbytes",
               "hypertable_size('telemetry'): sıkıştırmasız, indeks dahil. Gün başına projeksiyon docs/09'da."),
        timeseries(layout, "Canlı alım (mesaj/s, telemetry tablosundan)", """
SELECT $__timeGroupAlias(ts, '10s'), count(DISTINCT (pano_id, ts)) / 10.0 AS "mesaj/s"
FROM telemetry
WHERE $__timeFilter(ts)
GROUP BY 1
ORDER BY 1
""", unit="short", description="Yük testinden bağımsız: veritabanına yazılmış farklı (pano, zaman) sayısı. Kısa zaman aralığıyla kullanın."),
    ]
    run_variable = {
        "name": "run",
        "label": "Yük testi",
        "type": "query",
        "datasource": DS,
        "definition": "SELECT DISTINCT run_id FROM loadtest_metrics ORDER BY run_id DESC",
        "query": "SELECT DISTINCT run_id FROM loadtest_metrics ORDER BY run_id DESC",
        "refresh": 2,
        "includeAll": False,
        "multi": False,
        "sort": 0,
        "hide": 0,
        "current": {},
        "options": [],
    }
    return dashboard("gridup-olcek", "Grid Up — Ölçek ve yük testi",
                     "loadtest/fleet.py ölçümleri (docs/09-olceklenebilirlik.md). Üstten koşu seçin, zaman aralığını koşuya göre ayarlayın.",
                     panels, time_from="now-6h", templating=[run_variable])


def alarm_kpi(contracts: Contracts) -> dict[str, Any]:
    thresholds = contracts.thresholds
    target = thresholds["target_distribution_pct"]
    acceptable, maximum = thresholds["alarms_per_operator_day_acceptable"], thresholds["alarms_per_operator_day_max"]
    timeout_min = thresholds["heartbeat_timeout_min"]
    layout = Layout()
    panels = [
        stat(layout, "Günlük alarm (son 24 saat)", "SELECT count(*) AS \"alarm\" FROM alarms WHERE raised_at >= now() - interval '24 hours'",
             unit="short", steps=[("green", None), ("orange", acceptable), ("red", maximum)],
             description=f"EEMUA 191: operatör başına günde ≤{acceptable} kabul edilebilir, {maximum} yönetilebilir üst sınır."),
        stat(layout, "Alarm / 100 pano / gün", """
SELECT count(*) * 100.0 / NULLIF((SELECT count(*) FROM panels), 0) AS "alarm/100 pano"
FROM alarms WHERE raised_at >= now() - interval '24 hours'
""", unit="short", decimals=1, steps=[("green", None)], description="Filo büyüklüğünden bağımsız alarm yükü (API /fleet/kpi ile aynı tanım)."),
        stat(layout, f"Haberleşme sağlam (%, son {timeout_min} dk)", f"""
SELECT 100.0 * count(*) FILTER (WHERE l.last_rx >= now() - interval '{timeout_min} minutes') / NULLIF(count(*), 0) AS "%"
FROM panels p LEFT JOIN panel_latest l ON l.pano_id = p.pano_id
""", unit="percent", decimals=1, steps=[("red", None), ("orange", 95), ("green", 99)],
             description=f"Son {timeout_min} dakikada (heartbeat_timeout_min) veri gelen panoların oranı."),
        stat(layout, "Uçtan uca bildirim p95 (ms, 24 saat)", f"""
SELECT percentile_disc(0.95) WITHIN GROUP (ORDER BY latency_ms) AS "p95 ms"
FROM (
  SELECT extract(epoch FROM min(n.sent_at) - a.raised_at) * 1000.0 AS latency_ms
  FROM alarms a JOIN notifications n ON n.alarm_id = a.id AND n.ok AND n.channel IN {PHONE_CHANNELS}
  WHERE a.raised_at >= now() - interval '24 hours'
  GROUP BY a.id, a.raised_at
) t
""", unit="ms", steps=[("green", None), ("orange", 5000), ("red", 30000)],
             description="Olay zamanından (sensör) telefona ilk başarılı SMS/WhatsApp teslimine; en yakın sıra yöntemi."),
        table(layout, "Öncelik dağılımı (7 gün) — hedefe göre", f"""
SELECT prio AS "Öncelik",
       count(*) AS "Alarm",
       round(100.0 * count(*) / NULLIF(sum(count(*)) OVER (), 0), 1) AS "Gerçekleşen %",
       CASE prio WHEN 'P1' THEN {target['high']} WHEN 'P2' THEN {target['medium']} WHEN 'P3' THEN {target['low']} END AS "Hedef %"
FROM alarms
WHERE raised_at >= now() - interval '7 days' AND prio IN ('P1', 'P2', 'P3')
GROUP BY prio
ORDER BY prio
""", description="EEMUA 191 hedef dağılımı (yüksek / orta / düşük). SYS ve INFO proses alarmı değildir."),
        table(layout, "Etkin alarmlar (öncelik)", """
SELECT prio AS "Öncelik", count(*) FILTER (WHERE state = 'active') AS "Onaysız",
       count(*) FILTER (WHERE state = 'acked') AS "Onaylı", count(*) FILTER (WHERE state = 'shelved') AS "Rafta"
FROM alarms WHERE state <> 'cleared'
GROUP BY prio ORDER BY prio
""", description="Temizlenmemiş alarmlar. Rafta olanlar ekrana ve SCADA'ya duyurulmaz."),
        timeseries(layout, "Oluşan alarmlar (saatlik)", """
SELECT $__timeGroupAlias(raised_at, '1h'), prio AS metric, count(*) AS value
FROM alarms
WHERE $__timeFilter(raised_at)
GROUP BY 1, prio
ORDER BY 1
""", unit="short", description="Alarm seli (flood) tespiti: ISA-18.2'de 10 dakikada 10'dan fazla alarm sel sayılır."),
        table(layout, "En çok alarm üreten panolar (7 gün)", """
SELECT pano_id AS "Pano", count(*) AS "Alarm", string_agg(DISTINCT code, ', ') AS "Kodlar"
FROM alarms WHERE raised_at >= now() - interval '7 days'
GROUP BY pano_id ORDER BY count(*) DESC LIMIT 10
""", description="ISA-18.2 'kötü aktör' analizi: alarm yükünün çoğu genellikle birkaç panodan gelir."),
    ]
    return dashboard("gridup-alarm-kpi", "Grid Up — Alarm KPI (ISA-18.2 / EEMUA 191)",
                     "Alarm performansı. Tanımlar docs/06-alarm-matrisi.md ve API /api/v1/fleet/kpi ile aynıdır.",
                     panels, time_from="now-7d")


def build(contracts: Contracts) -> dict[str, dict[str, Any]]:
    return {"olcek.json": olcek(contracts), "alarm-kpi.json": alarm_kpi(contracts)}


def render(dashboard_json: dict[str, Any]) -> bytes:
    return (json.dumps(dashboard_json, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="panolar guncel degilse 1 ile cik")
    args = parser.parse_args(argv)
    outputs = {OUT_DIR / name: render(content) for name, content in build(load_contracts(ROOT / "contracts")).items()}
    if args.check:
        stale = [path for path, data in outputs.items() if not path.exists() or path.read_bytes() != data]
        if stale:
            print("guncel degil:", ", ".join(p.name for p in stale), "-> python scripts/gen_grafana_dashboards.py")
            return 1
        print("guncel")
        return 0
    for path, data in outputs.items():
        path.write_bytes(data)
        print(f"yazildi: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
