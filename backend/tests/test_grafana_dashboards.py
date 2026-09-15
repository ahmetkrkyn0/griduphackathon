"""TB3 Adim 5 — scripts/gen_grafana_dashboards.py: Grafana panolari sozlesmeden uretilir, sorgulari gercekten calisir.

PLAN.md kural 7: Grafana JSON'u elle duzenlenmez (merge edilemez); kural 10: EEMUA 191 esikleri ve haberlesme zaman
asimi contracts/alarm-codes.yaml'dan gelir. Her panelin SQL'i Grafana makrolari acilarak gercek TimescaleDB'de
calistirilir (TEST_DB_DSN): pano ekranda "query error" gostermesin.

F-07 ile gelen iki yeni koruma:
  * GK10: bir panelin ACIKLAMASI, SORGUSUNUN hesaplamadigi bir pencere iddia edemez (sel panelinin
    eski hali "10 dakikada 10 alarm" diyordu ama saatlik kova kullaniyordu).
  * EEMUA 191 panelleri (sel / bayat / chattering / kod bazinda kotu aktor) bilinen bir alarm
    desenine karsi GERCEKTEN olculur: sorgunun "calismasi" yetmez, dogru satiri bulmasi gerekir.
"""

from __future__ import annotations

import copy
import importlib.util
import itertools
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from helpers import REPO_ROOT

DSN = os.getenv("TEST_DB_DSN")
_GRAFANA_INTERVAL = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}

# Aciklamadaki "<sayi> <birim>" iddiasinin SQL'de gorunmesi gereken karsiligi (GK10 denetimi).
# Grafana kovasi ('10m') veya PostgreSQL araligi (interval '10 minutes') kabul edilir.
_CLAIM_UNITS = {"dakika": ("m", "minutes"), "saat": ("h", "hours"), "gün": ("d", "days")}
_CLAIM = re.compile(r"(\d+)\s*(dakika|saat|gün)")
# Panel bir tanimi ANMAK ama hesaplamamak zorunda kalabilir; o cumle acikca boyle isaretlenir.
_DISCLAIMER = "HESAPLAMAZ"


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


def test_no_panel_claims_a_window_it_does_not_compute(gen, contracts):
    """GK10 gerilemesi: aciklamada gecen her pencere sorguda da olmali.

    Sel paneli eskiden "10 dakikada 10'dan fazla alarm sel sayilir" diyordu ama SAATLIK kova
    kullaniyordu; panel hesaplamadigi bir tanimi iddia ediyordu. Bir panel bir tanimi anip
    hesaplamiyorsa bunu aciklamasinda acikca yazmali (HESAPLAMAZ).
    """
    for name, dashboard in gen.build(contracts).items():
        for panel in panels_of(dashboard):
            sql = " ".join(target["rawSql"] for target in panel["targets"])
            claims = " ".join(s for s in panel["description"].split(". ") if _DISCLAIMER not in s)
            for number, unit in _CLAIM.findall(claims):
                short, long = _CLAIM_UNITS[unit]
                computed = f"'{number}{short}'" in sql or f"interval '{number} {long}'" in sql
                assert computed, f"{name} / {panel['title']}: aciklama {number} {unit} diyor, sorgu demiyor"


def test_eemua_definitions_reach_both_the_query_and_the_description(gen, contracts):
    """EEMUA 191 sayilari tek sabitten gelir: sorgu ile aciklama bir daha ayrisamaz (GK10)."""
    original = (gen.FLOOD_WINDOW_MIN, gen.STALE_ALARM_H)
    try:
        gen.FLOOD_WINDOW_MIN, gen.STALE_ALARM_H = 7, 48
        kpi = gen.build(contracts)["alarm-kpi.json"]
        flood = next(p for p in panels_of(kpi) if p["title"].startswith("Alarm seli"))
        assert "'7m'" in flood["targets"][0]["rawSql"]
        assert "7 dakikalık" in flood["description"] and "10 dakika" not in flood["description"]
        stale = next(p for p in panels_of(kpi) if p["title"].startswith("Bayat"))
        assert "interval '48 hours'" in stale["targets"][0]["rawSql"]
        assert "48 saat" in stale["title"] and "48 saatten" in stale["description"]
    finally:
        gen.FLOOD_WINDOW_MIN, gen.STALE_ALARM_H = original


def test_distribution_targets_follow_the_contract(gen, contracts):
    changed = copy.deepcopy(contracts)
    changed.thresholds["target_distribution_pct"] = {"high": 1, "medium": 9, "low": 90}
    kpi = gen.build(changed)["alarm-kpi.json"]
    distribution = next(p for p in panels_of(kpi) if p["title"].startswith("Öncelik dağılımı"))
    sql = distribution["targets"][0]["rawSql"]
    assert "WHEN 'P1' THEN 1 WHEN 'P2' THEN 9 WHEN 'P3' THEN 90" in sql


def _panel_sql(gen, contracts, prefix: str) -> str:
    kpi = gen.build(contracts)["alarm-kpi.json"]
    panel = next(p for p in panels_of(kpi) if p["title"].startswith(prefix))
    return expand_macros(panel["targets"][0]["rawSql"])


def _seed_alarm(cur, ids, pano_id: str, code: str, prio: str, point: str | None, at: datetime,
                repeats: list[timedelta], state: str = "cleared") -> None:
    """Bir alarmi ve duyurularini denetim izine yazar; her tekrar yeni bir alarm satiridir (alarm_manager.py).

    Kimligi uretimdeki gibi CAGIRAN verir (alarm yoneticisi max(id)+1'den sayar), BIGSERIAL degil:
    depoda acikca yazilmis kimlikler varken dizinin varsayilani onlarla cakisir.
    """
    for offset in repeats:
        moment = at + offset
        alarm_id = next(ids)
        cur.execute(
            "INSERT INTO alarms (id, pano_id, code, prio, state, point, raised_at, annunciated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (alarm_id, pano_id, code, prio, state, point, moment, moment),
        )
        cur.execute(
            "INSERT INTO alarm_journal (alarm_id, at, action, state) VALUES (%s, %s, 'raised', %s)",
            (alarm_id, moment, state),
        )


@pytest.fixture
def eemua_rows(gen, contracts):
    """Bilinen bir alarm deseni: sel, bayat, chattering ve sakin bir alarm. Test sonunda geri alinir."""
    now = datetime.now(timezone.utc)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO panels (pano_id, name) VALUES ('TST-EEMUA', 'EEMUA testi') "
                    "ON CONFLICT (pano_id) DO NOTHING")
        ids = itertools.count(cur.execute("SELECT COALESCE(max(id), 0) + 1 FROM alarms").fetchone()[0])
        # Sel: TEK bir sel kovasina 12 duyuru (tanim: >10). time_bucket kovalari Unix epoch'a
        # hizalidir; duyurular kova sinirinin iki yanina dagilirsa hicbir kova tanimi asmaz.
        window_s = gen.FLOOD_WINDOW_MIN * 60
        edge = (now - timedelta(hours=2)).timestamp() // window_s * window_s
        flood_at = datetime.fromtimestamp(edge + 60, tz=timezone.utc)
        _seed_alarm(cur, ids, "TST-EEMUA", "ALM-DEW-WARN", "P3", "PANEL", flood_at,
                    [timedelta(seconds=20 * i) for i in range(12)])
        # Chattering: 10 saniye arayla 6 duyuru -> run-length 10 s, chatter indeksi 0,1.
        chatter_at = now - timedelta(hours=3)
        _seed_alarm(cur, ids, "TST-EEMUA", "ALM-K-WARN", "P3", "DSYA3_L2", chatter_at,
                    [timedelta(seconds=10 * i) for i in range(6)])
        # Sakin alarm: 2 saat arayla 3 duyuru -> chatter indeksi ~0,0001, listelenmemeli.
        _seed_alarm(cur, ids, "TST-EEMUA", "ALM-I-OVER", "P2", "PANEL", now - timedelta(days=1),
                    [timedelta(hours=2 * i) for i in range(3)])
        # Bayat: 30 saattir temizlenmemis alarm.
        _seed_alarm(cur, ids, "TST-EEMUA", "ALM-PROT-HEALTH", "P1", "PANEL", now - timedelta(hours=30),
                    [timedelta(0)], state="active")
        yield conn
        conn.rollback()


@pytest.mark.integration
@pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
def test_flood_panel_counts_the_ten_minute_window(gen, contracts, eemua_rows):
    """Sel paneli 10 dakikalik kovayi gercekten sayar: 12 duyuru tek kovada gorunur."""
    rows = eemua_rows.execute(_panel_sql(gen, contracts, "Alarm seli")).fetchall()
    assert max(count for _, count in rows) >= gen.FLOOD_ALARM_COUNT + 1, rows
    # Ayni veri SAATLIK kovada da vardir; sel tanimini gosteren kova 10 dakikaliktir.
    assert sum(count for _, count in rows) >= 12


@pytest.mark.integration
@pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
def test_stale_panel_lists_only_alarms_older_than_the_limit(gen, contracts, eemua_rows):
    rows = eemua_rows.execute(_panel_sql(gen, contracts, "Bayat")).fetchall()
    ours = [r for r in rows if r[0] == "TST-EEMUA"]
    assert [r[1] for r in ours] == ["ALM-PROT-HEALTH"], ours
    assert float(ours[0][5]) >= gen.STALE_ALARM_H


@pytest.mark.integration
@pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
def test_chatter_panel_separates_chattering_from_a_calm_alarm(gen, contracts, eemua_rows):
    rows = eemua_rows.execute(_panel_sql(gen, contracts, "Chattering")).fetchall()
    ours = {row[1]: row for row in rows if row[0] == "TST-EEMUA"}
    assert "ALM-K-WARN" in ours, rows                  # 10 s arayla: chattering
    assert "ALM-I-OVER" not in ours, rows              # 2 saat arayla: degil
    _, _, _, count, index, shortest = ours["ALM-K-WARN"]
    assert count == 6 and float(index) == pytest.approx(0.1, abs=0.001) and float(shortest) == pytest.approx(0.2)


@pytest.mark.integration
@pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
def test_bad_actor_by_code_shares_add_up(gen, contracts, eemua_rows):
    rows = eemua_rows.execute(_panel_sql(gen, contracts, "En çok alarm üreten kodlar")).fetchall()
    assert len(rows) <= gen.BAD_ACTOR_LIMIT
    counts = [row[2] for row in rows]
    assert counts == sorted(counts, reverse=True)
    by_code = {row[0]: row for row in rows}
    assert by_code["ALM-DEW-WARN"][2] >= 12                       # 12 duyuru ekledik
    assert float(rows[-1][5]) <= 100.0                            # kumulatif pay taşmaz
    assert float(rows[0][4]) == pytest.approx(float(rows[0][5]))  # ilk satirda pay = kumulatif


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
