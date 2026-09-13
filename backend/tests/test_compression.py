"""TB3 Adim 6 — telemetri sikistirmasi (deploy/initdb/005_compression.sql) gercek TimescaleDB'de.

Olcum (loadtest/storage.py, 1 gun, 7 nokta): sikistirmasiz 198 B/satir -> sikistirilmis 4,09 B/satir (48 kat); sikistirma
olmadan 100 pano gunde 13,9 GB buyur (docs/09 §5). Burada iki sey sinanir:
  1) sema ayari ve politika kurulu (bos volume'da initdb, mevcut veritabaninda elle uygulama),
  2) uygulamanin yazma ve okuma yollari SIKISTIRILMIS parcada da dogru calisir: /series ortalamasi ayni kalir,
     kenarin tamponundan gec gelen olcum sikistirilmis parcaya yazilir ve sonuca girer, temizlik silebilir.

Yigin ayaktayken:  TEST_DB_DSN=postgresql://postgres:gridup@localhost:5432/gridup pytest -m integration
Parca 2099-02-01'dedir: canli verinin ve diger testlerin parcalarina dokunmaz; politika gelecekteki parcayi sikistirmaz.
"""

from __future__ import annotations

import copy
import os
import random
from datetime import timedelta

import psycopg
import pytest

from app.db import PgStore
from app.ingest import IngestPipeline
from helpers import encode, utc

DSN = os.getenv("TEST_DB_DSN")
needs_db = pytest.mark.skipif(not DSN, reason="TEST_DB_DSN tanimli degil (gercek veritabani gerekir)")
pytestmark = [pytest.mark.integration, needs_db]

DAY = utc(2099, 2, 1, 0, 0, 0)
T0 = utc(2099, 2, 1, 10, 0, 0)
TAG = "t_conn.GIRIS_L2.dt_c"


@pytest.fixture
def pano_id() -> str:
    return f"TST-{random.randrange(100_000):05d}"


@pytest.fixture
def db(pano_id):
    with psycopg.connect(DSN, autocommit=True) as conn:
        yield conn
        conn.execute("DELETE FROM telemetry WHERE pano_id = %s", (pano_id,))
        conn.execute("DELETE FROM panel_latest WHERE pano_id = %s", (pano_id,))
        conn.execute("DELETE FROM panels WHERE pano_id = %s", (pano_id,))


@pytest.fixture
def store(db):
    pg = PgStore(DSN)
    yield pg
    pg.close()


def ingest(contracts, store, tel_payload, pano_id, ts, seq, dt_l2):
    payload = copy.deepcopy(tel_payload)
    payload.update(pano_id=pano_id, ts=ts.isoformat(), seq=seq)
    payload["t_conn"][1]["dt_c"] = dt_l2
    pipeline = IngestPipeline(contracts, store, clock=lambda: ts + timedelta(seconds=2))
    pipeline.handle_message(f"gridup/pano/{pano_id}/tel", encode(payload))
    assert pipeline.flush()


def test_telemetry_is_segmented_by_panel_and_tag_and_compressed_after_a_day(db):
    settings = db.execute(
        "SELECT segmentby, orderby FROM timescaledb_information.hypertable_compression_settings "
        "WHERE hypertable = 'telemetry'::regclass"
    ).fetchall()
    assert settings and settings[0][0] is not None, "telemetry sikistirmasi acik degil: deploy/initdb/005_compression.sql uygulanmali"
    [(segmentby, orderby)] = settings  # TimescaleDB 2.30 gorunumu metin dondurur
    assert segmentby == "pano_id,tag"
    assert orderby == "ts DESC"

    policies = db.execute(
        "SELECT config ->> 'compress_after' FROM timescaledb_information.jobs "
        "WHERE hypertable_name = 'telemetry' AND proc_name = 'policy_compression'"
    ).fetchall()
    assert policies == [("1 day",)]


def test_writes_and_series_work_on_a_compressed_chunk(contracts, store, db, tel_payload, pano_id):
    for seq, (offset_s, dt) in enumerate(((0, 50.0), (30, 52.0))):
        ingest(contracts, store, tel_payload, pano_id, T0 + timedelta(seconds=offset_s), seq, dt)
    [(chunk,)] = db.execute(
        "SELECT c FROM show_chunks('telemetry', newer_than => %s, older_than => %s) c", (DAY, DAY + timedelta(days=1))
    ).fetchall()
    db.execute("SELECT compress_chunk(%s::regclass, if_not_compressed => true)", (chunk,))
    [(compressed,)] = db.execute(
        "SELECT is_compressed FROM timescaledb_information.chunks WHERE format('%%I.%%I', chunk_schema, chunk_name)::regclass = %s::regclass",
        (chunk,),
    ).fetchall()
    assert compressed is True

    window = (T0, T0 + timedelta(minutes=2), timedelta(minutes=1))
    assert store.series(pano_id, [TAG], *window) == {TAG: {T0: 51.0}}

    ingest(contracts, store, tel_payload, pano_id, T0 + timedelta(seconds=45), 2, 60.0)  # kenar tamponundan gec gelen
    ingest(contracts, store, tel_payload, pano_id, T0 + timedelta(minutes=1), 3, 40.0)
    assert store.series(pano_id, [TAG], *window) == {TAG: {T0: 54.0, T0 + timedelta(minutes=1): 40.0}}
