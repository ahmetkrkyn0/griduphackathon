"""F-20 uctan uca — scripts/verify_journal.py GERCEK TimescaleDB'ye karsi.

Bu dosya maddenin "Ne uretir" satirini karsilar: *negatif testle **olculmus** bir iddia:
bir satir bozuldugunda dogrulayicinin kacinci halkada durdugu.*

Birim testler (tests/test_journal_chain.py) zinciri elde kurulmus satirlarla olcer.
Burada ise satirlar GERCEK alarm servisi tarafindan gercek veritabanina yazilir, sonra
psql ile kurcalanir ve BAGIMSIZ betik calistirilir — yani "kendi kendini onaylama" yok.
"""

from __future__ import annotations

import copy
import importlib.util
import os
import subprocess
import sys
from datetime import timedelta

import pytest

from app.config import Settings
from app.db import PgStore
from app.main import create_app
from fastapi.testclient import TestClient
from helpers import CONTRACTS_DIR, Clock, encode, utc

DSN = os.getenv("TEST_DB_DSN")
needs_db = pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil")

T0 = utc(2026, 9, 13, 10, 0, 0)
NOW = T0 + timedelta(seconds=5)
PANO = "ADM-09901"  # bu dosyaya ozel; diger testlerin panolariyla karismasin

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def verifier():
    spec = importlib.util.spec_from_file_location("verify_journal", REPO_ROOT / "scripts" / "verify_journal.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


@pytest.fixture
def db():
    import psycopg

    with psycopg.connect(DSN, autocommit=True) as conn:
        yield conn


@pytest.fixture
def written(db, tel_payload):
    """Gercek alarm servisiyle gercek DB'ye birkac denetim izi satiri yazar."""
    db.execute("DELETE FROM alarm_journal")
    db.execute("DELETE FROM notifications")
    db.execute("DELETE FROM alarms")
    db.execute("DELETE FROM events")

    store = PgStore(DSN)
    clock = Clock(NOW)
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False, central_detector_enabled=False),
        store=store,
        clock=clock,
    )
    try:
        with TestClient(app) as client:
            message = copy.deepcopy(tel_payload)
            message["pano_id"] = PANO
            message["ts"] = T0.isoformat()
            app.state.pipeline.handle_message(f"gridup/pano/{PANO}/tel", encode(message))
            assert app.state.pipeline.flush()

            # Onay: zincire ucuncu bir halka daha ekler.
            alarms = client.get("/api/v1/alarms", params={"pano_id": PANO}).json()
            assert alarms, "test en az bir alarm bekliyor"
            assert client.post(f"/api/v1/alarms/{alarms[0]['id']}/ack", json={"note": "ekip yolda"}).status_code == 200
            yield client
    finally:
        store.close()


def run_script(*args: str) -> subprocess.CompletedProcess:
    """Betigi AYRI BIR SUREC olarak kosturur — backend'i hic ayaga kaldirmadan."""
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "verify_journal.py"), "--dsn", DSN, *args],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )


def rows(db) -> list[tuple]:
    return db.execute("SELECT id, hash FROM alarm_journal ORDER BY id").fetchall()


# ------------------------------------------------------------------ saglam zincir
@needs_db
def test_real_writes_produce_a_verifiable_chain(written, db):
    stored = rows(db)
    assert len(stored) >= 2, "en az bir raised + bir acked halkasi bekleniyor"
    assert all(h is not None for _, h in stored), "gercek yazma yolu hash uretmeli"

    result = run_script()

    assert result.returncode == 0, result.stderr
    assert "ZINCIR SAGLAM" in result.stdout
    assert f"{len(stored)} halka" in result.stdout


@needs_db
def test_chain_links_to_the_previous_row(db, written):
    stored = db.execute("SELECT id, prev_hash, hash FROM alarm_journal ORDER BY id").fetchall()
    for (_, _, prev_hash_of_row), (_, next_prev, _) in zip(stored, stored[1:]):
        assert next_prev == prev_hash_of_row, "her satir bir oncekinin hash'ini tasimali"


# ------------------------------------------------- ASIL KILIT: olculmus red kaniti
@needs_db
def test_a_modified_row_is_caught_at_its_exact_link(written, db):
    """Yetkili bir DB kullanicisi bir satiri sessizce degistiriyor."""
    stored = rows(db)
    target_id = stored[1][0]  # ikinci halka
    db.execute("UPDATE alarm_journal SET by_user = %s WHERE id = %s", ("sahte.operator", target_id))

    result = run_script()

    assert result.returncode == 1
    assert "ZINCIR KOPUK" in result.stderr
    assert f"halka 2 (alarm_journal.id={target_id})" in result.stderr
    assert "degismis" in result.stderr
    assert "saglam    : 1 halka" in result.stderr  # oncesi dogrulandi


@needs_db
def test_a_deleted_row_is_caught_at_the_next_link(written, db):
    """Yetkili bir DB kullanicisi bir satiri sessizce siliyor."""
    stored = rows(db)
    assert len(stored) >= 3, "silme testi en az uc halka ister"
    db.execute("DELETE FROM alarm_journal WHERE id = %s", (stored[1][0],))

    result = run_script()

    assert result.returncode == 1
    assert "ZINCIR KOPUK" in result.stderr
    assert f"alarm_journal.id={stored[2][0]}" in result.stderr  # silinenin ARDINDAKI satir
    assert "kopuk" in result.stderr
    assert "SILINMIS" in result.stderr


@needs_db
def test_quiet_mode_still_reports_the_break(written, db):
    """--quiet cikis kodunu sessizlestirmez: 1'in sebebi gorunur kalmali."""
    db.execute("UPDATE alarm_journal SET note = %s WHERE id = %s", ("kurcalandi", rows(db)[0][0]))

    result = run_script("--quiet")

    assert result.returncode == 1
    assert result.stdout == ""            # saglam ciktisi susturuldu
    assert "ZINCIR KOPUK" in result.stderr  # kirilma susturulmadi


@needs_db
def test_missing_dsn_is_a_usage_error_not_a_false_pass(verifier, monkeypatch):
    """DSN yoksa 0 DONMEMELI: 'dogrulanamadi' ile 'saglam' karistirilmamali."""
    monkeypatch.delenv("DB_DSN", raising=False)
    monkeypatch.delenv("TEST_DB_DSN", raising=False)
    assert verifier.main([]) == 2


@needs_db
def test_unreachable_database_returns_two_not_zero(verifier):
    assert verifier.main(["--dsn", "postgresql://yok:yok@127.0.0.1:1/yokdb"]) == 2
