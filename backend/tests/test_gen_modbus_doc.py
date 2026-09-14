"""TB3 Adim 3 — scripts/gen_modbus_doc.py: contracts/modbus-map.yaml -> docs/03 + CSV (elle yazilmaz, kural 10).

Betik kontrollu girdiyle calistirilir ve ciktisi sinanir. Hat butcesi beklentileri rapor 6.4d tablosundan
(19200 baud, 8E1 = 11 bit/karakter): 10 register 33 karakter ~23 ms, 50 -> 113 / ~69 ms, 100 -> 213 / ~126 ms.
"""

from __future__ import annotations

import csv
import importlib.util
import io

import pytest

from app.scada.map_loader import load_map, parse_map
from helpers import CONTRACTS_DIR, REPO_ROOT


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("gen_modbus_doc", REPO_ROOT / "scripts" / "gen_modbus_doc.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def regmap():
    return load_map(CONTRACTS_DIR / "modbus-map.yaml")


def test_line_budget_reproduces_report_table(gen):
    rows = {count: (chars, round(ms)) for count, chars, ms in gen.line_budget(baud=19200, bits_per_char=11)}
    assert rows[10] == (33, 23)
    assert rows[50] == (113, 69)
    assert rows[100] == (213, 126)


def test_register_rows_carry_modicon_numbers_and_central_source(gen, regmap):
    rows = {row["ad"]: row for row in gen.register_rows(regmap)}
    l2 = rows["conn_temp.GIRIS_L2"]
    assert (l2["pdu"], l2["holding"], l2["input"]) == (101, 40102, 30102)
    assert (l2["tip"], l2["olcek"], l2["birim"]) == ("int16", "0.1", "degC")
    assert l2["merkez_kaynagi"] == "`t_conn[GIRIS_L2].t_c`"
    trips = rows["arc_mirror.trip_count"]
    assert (trips["erisim"], trips["tvoc2_pdu"]) == ("read_only", "149")
    assert len(rows) == sum(len(block.registers) for block in regmap.blocks)


def test_csv_is_excel_friendly(gen, regmap):
    data = gen.csv_bytes(gen.register_rows(regmap))
    assert data.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM: Excel Turkce karakterleri dogru acar
    table = list(csv.reader(io.StringIO(data.decode("utf-8-sig")), delimiter=";"))  # TR Excel liste ayiraci
    header, body = table[0], table[1:]
    assert header[:3] == ["pdu", "holding", "input"]
    first = dict(zip(header, body[0]))
    assert (first["pdu"], first["ad"]) == ("0", "device_info.map_version")


def test_render_fills_marked_blocks_and_keeps_narrative(gen):
    regmap = parse_map(
        {
            "version": 7,
            "endianness": "big",
            "mirror_fc03_fc04": True,
            "blocks": [{"name": "info", "start": 10, "count": 2, "items": [{"offset": 0, "name": "map_version", "type": "uint16"}]}],
            "coils": {"items": [{"addr": 0, "name": "critical_alarm", "note": "P1 aktif"}]},
        }
    )
    doc = "# Baslik\n\nElle yazilmis anlati.\n\n<!-- URETILMIS:bloklar -->\neski\n<!-- /URETILMIS:bloklar -->\n"
    rendered = gen.render(doc, regmap, {"line_budget": {"baud": 19200, "bits_per_char": 11}}, only=("bloklar",))
    assert "Elle yazilmis anlati." in rendered
    assert "eski" not in rendered
    assert "| `info` | 10-11 | 40011-40012 | 2 |" in rendered


def test_render_rejects_missing_block(gen, regmap):
    with pytest.raises(SystemExit, match="bloklar"):
        gen.render("# bos belge\n", regmap, {}, only=("bloklar",))


def test_committed_doc_and_csv_are_up_to_date(gen):
    """Sozlesme degisip dokuman yeniden uretilmediyse (kural 10 ihlali) burada patlar."""
    assert gen.main(["--check"]) == 0
