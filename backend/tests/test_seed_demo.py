"""F-01 — scripts/seed_demo.py: altin demo veritabani TEKRAR URETILEBILIR olmali.

Betigin tek sozu var: ayni tohum + ayni pencere -> ayni veritabani. Bu dosya o sozu iki ayri
duzeyde kanitlar: once veritabanina dokunmadan (uretecin kendisi deterministik mi), sonra gercek
TimescaleDB'de (yazma yolu da deterministik mi, ve demo veritabani gercekten "rapor ureten
maddelerin bekledigi" zemin mi: >=7 gunluk gecmis, taban ogrenme tamam, gelecege tarihli satir yok).
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from helpers import REPO_ROOT

DSN = os.getenv("TEST_DB_DSN")
DAYS = "8"          # 7 gun taban ogrenme + 1 gun temiz veri: sozlesmenin izin verdigi en kisa demo
PANELS = "1"        # tekrar uretilebilirligi tek pano da kanitlar; testin suresi uc katina cikmasin


@pytest.fixture(scope="module")
def seeder():
    spec = importlib.util.spec_from_file_location("seed_demo", REPO_ROOT / "scripts" / "seed_demo.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


@pytest.fixture(scope="module")
def window(seeder) -> str:
    """Sabit bir pencere sonu: iki kosunun ozeti ancak ayni pencerede birebir ayni olabilir."""
    period = seeder.scenarios.EXPORT_PERIOD_S
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    return datetime.fromtimestamp(yesterday.timestamp() // period * period, tz=timezone.utc).isoformat()


def run(seeder, *args: str) -> dict:
    """Betigi CLI'sinden kosar ve --json ozetini doner (contextlib: modul kapsamli donatilardan da cagrilir)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = seeder.main(["--json", *args])
    assert code == 0, out.getvalue()
    return json.loads(out.getvalue().strip().splitlines()[-1])


@pytest.fixture(scope="module")
def dry_summary(seeder, window) -> dict:
    """Veritabanina dokunmadan uretilen ozet; uretimin kendisi bir kez kosar (her kosu ~5 s)."""
    return run(seeder, "--dry-run", "--panels", PANELS, "--days", DAYS, "--end", window)


@pytest.fixture(scope="module")
def seeded_twice(seeder, window) -> tuple[list[dict], list[dict]]:
    """Ayni argumanlarla ARKA ARKAYA iki kez tohumlar; ozetleri ve satir sayilarini biriktirir.

    Modul kapsamli: tohumlama pahalidir (~20 s), iki entegrasyon testi ayni kosuyu paylasir.
    """
    if not DSN:
        pytest.skip("TEST_DB_DSN tanimli degil")
    summaries, counts = [], []
    for _ in range(2):
        summaries.append(run(seeder, "--dsn", DSN, "--reset", "--panels", PANELS,
                             "--days", DAYS, "--end", window))
        with psycopg.connect(DSN, autocommit=True) as conn:
            counts.append({
                table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("telemetry", "alarms", "alarm_journal", "events", "panel_latest")
            })
    yield summaries, counts
    with psycopg.connect(DSN, autocommit=True) as conn:  # demo verisi baska testlere sizmasin
        conn.execute("TRUNCATE alarm_journal, notifications, alarms, events, panel_latest, telemetry, "
                     "demo_seed RESTART IDENTITY")


def test_same_seed_and_window_give_the_same_summary(seeder, window, dry_summary):
    again = run(seeder, "--dry-run", "--panels", PANELS, "--days", DAYS, "--end", window)
    assert again == dry_summary
    assert again["samples"] > 0 and again["telemetry_rows"] > 0


def test_a_different_seed_produces_different_data(seeder, window, dry_summary):
    other = run(seeder, "--dry-run", "--panels", PANELS, "--days", DAYS, "--end", window,
                "--seed", str(seeder.DEFAULT_SEED + 1))
    assert other["digest"] != dry_summary["digest"]
    assert other["samples"] == dry_summary["samples"]  # ayni pencere, ayni ornekleme: yalnizca fizik degisir


def test_history_never_reaches_into_the_future(seeder):
    """Gelecege tarihli satir canli veriyi backfill kuraline takar (app/db.py _UPSERT_LATEST).

    Varsayilan pencere "simdi"de biter ve ornekleme adimina asagi yuvarlanir; ileri sarkmaz.
    """
    period = seeder.scenarios.EXPORT_PERIOD_S
    end = seeder._window_end(None, period)
    now = datetime.now(timezone.utc)
    assert end <= now and now - end < timedelta(seconds=period)
    assert end.timestamp() % period == 0


def test_a_window_shorter_than_baseline_learning_is_refused(seeder, contracts):
    learning_days = int(contracts.thresholds["baseline_learning_days"])
    with pytest.raises(SystemExit):
        seeder.main(["--dry-run", "--days", str(learning_days)])


@pytest.mark.integration
@pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
def test_seeding_twice_writes_the_same_database(seeded_twice):
    """Tekrar uretilebilirlik: yazma yolu da (COPY + upsert + alarm yoneticisi) deterministik."""
    summaries, counts = seeded_twice
    assert summaries[0] == summaries[1]
    assert counts[0] == counts[1]
    assert counts[0]["telemetry"] == summaries[0]["telemetry_rows"]
    assert counts[0]["alarms"] == summaries[0]["alarms"]


@pytest.mark.integration
@pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
def test_seeded_database_is_the_ground_reports_expect(contracts, seeded_twice):
    learning_days = int(contracts.thresholds["baseline_learning_days"])
    summary = seeded_twice[0][-1]
    span = datetime.fromisoformat(summary["window_end"]) - datetime.fromisoformat(summary["window_start"])
    assert span >= timedelta(days=learning_days)

    with psycopg.connect(DSN, autocommit=True) as conn:
        latest = conn.execute("SELECT (payload -> 'health' ->> 'baseline_day')::int FROM panel_latest").fetchall()
        assert latest and all(day == learning_days for (day,) in latest)
        assert conn.execute("SELECT count(*) FROM telemetry WHERE ts > now()").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM telemetry WHERE q <> 0").fetchone()[0] == 0  # temiz veri
        origin, digest = conn.execute("SELECT origin, digest FROM demo_seed ORDER BY id DESC LIMIT 1").fetchone()
        assert "sentetik" in origin and digest == summary["digest"]          # GK10 kunyesi
        notes = conn.execute("SELECT notes FROM panels WHERE baseline_day = %s", (learning_days,)).fetchall()
        assert notes and all("sentetik" in (note or "") for (note,) in notes)
