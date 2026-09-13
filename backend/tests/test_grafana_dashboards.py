"""TB3 Adim 5 — scripts/gen_grafana_dashboards.py: Grafana panolari sozlesmeden uretilir, sorgulari gercekten calisir.

PLAN.md kural 7: Grafana JSON'u elle duzenlenmez (merge edilemez); kural 10: EEMUA 191 esikleri ve haberlesme zaman
asimi contracts/alarm-codes.yaml'dan gelir. Her panelin SQL'i Grafana makrolari acilarak gercek TimescaleDB'de
calistirilir (TEST_DB_DSN): pano ekranda "query error" gostermesin.
"""

from __future__ import annotations

import copy
import importlib.util
import os
import re
import sys

import psycopg
import pytest

from helpers import REPO_ROOT

DSN = os.getenv("TEST_DB_DSN")
_GRAFANA_INTERVAL = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("gen_grafana_dashboards", REPO_ROOT / "scripts" / "gen_grafana_dashboards.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def panels_of(dashboard: dict) -> list[dict]:
    return [panel for panel in dashboard["panels"] if panel["type"] != "row"]


def expand_macros(sql: str) -> str:
    """Grafana PostgreSQL makrolarinin veritabanina giden karsiligi (son 6 saat)."""

    def interval(raw: str) -> str:
        number, unit = re.fullmatch(r"(\d+)([smhd])", raw).groups()
        return f"'{number} {_GRAFANA_INTERVAL[unit]}'::interval"

    sql = re.sub(r"\$__timeFilter\((\w+)\)", r"\1 BETWEEN now() - interval '6 hours' AND now()", sql)
    sql = re.sub(r"\$__timeGroupAlias\((\w+),\s*'([^']+)'\)", lambda m: f"time_bucket({interval(m[2])}, {m[1]}) AS \"time\"", sql)
    return sql.replace("$run", "yok-boyle-bir-kosu")


def test_committed_dashboards_are_up_to_date(gen):
    assert gen.main(["--check"]) == 0


def test_every_dashboard_uses_the_provisioned_datasource(gen, contracts):
    for dashboard in gen.build(contracts).values():
        for panel in panels_of(dashboard):
            assert panel["datasource"]["uid"] == "gridup-tsdb", panel["title"]
            assert all(target["datasource"]["uid"] == "gridup-tsdb" for target in panel["targets"])


def test_alarm_rate_thresholds_follow_the_contract(gen, contracts):
    changed = copy.deepcopy(contracts)
    changed.thresholds["alarms_per_operator_day_acceptable"] = 111
    changed.thresholds["alarms_per_operator_day_max"] = 222
    changed.thresholds["heartbeat_timeout_min"] = 9
    kpi = gen.build(changed)["alarm-kpi.json"]
    rate = next(p for p in panels_of(kpi) if p["title"].startswith("Günlük alarm"))
    steps = [step["value"] for step in rate["fieldConfig"]["defaults"]["thresholds"]["steps"]]
    assert steps == [None, 111, 222]
    comms = next(p for p in panels_of(kpi) if p["title"].startswith("Haberleşme"))
    assert "interval '9 minutes'" in comms["targets"][0]["rawSql"]


def test_distribution_targets_follow_the_contract(gen, contracts):
    changed = copy.deepcopy(contracts)
    changed.thresholds["target_distribution_pct"] = {"high": 1, "medium": 9, "low": 90}
    kpi = gen.build(changed)["alarm-kpi.json"]
    distribution = next(p for p in panels_of(kpi) if p["title"].startswith("Öncelik dağılımı"))
    sql = distribution["targets"][0]["rawSql"]
    assert "WHEN 'P1' THEN 1 WHEN 'P2' THEN 9 WHEN 'P3' THEN 90" in sql


@pytest.mark.integration
@pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
def test_every_panel_query_runs_on_timescaledb(gen, contracts):
    queries = []
    for name, dashboard in gen.build(contracts).items():
        queries += [(name, v["name"], v["query"]) for v in dashboard.get("templating", {}).get("list", [])]
        queries += [(name, panel["title"], t["rawSql"]) for panel in panels_of(dashboard) for t in panel["targets"]]
    assert queries
    with psycopg.connect(DSN, autocommit=True) as conn:
        for name, title, sql in queries:
            try:
                conn.execute(expand_macros(sql)).fetchall()
            except psycopg.Error as exc:
                pytest.fail(f"{name} / {title}: {exc}\n{expand_macros(sql)}")
