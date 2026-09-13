"""TB3 Adim 1 — contracts/modbus-map.yaml -> register tablosu (app.scada.map_loader).

Adresler PDU adresidir (0 tabanli). Beklenen degerler sozlesme dosyasindan ELLE cikarilmistir:
nokta sirasi GIRIS_L1(0) GIRIS_L2(1) GIRIS_L3(2) GIRIS_N(3) DSYA1_L1..L3(4-6) DSYA2(7-9) DSYA3(10-12)...
"""

from __future__ import annotations

import copy

import pytest

from app.scada.map_loader import MapError, load_map, parse_map
from helpers import CONTRACTS_DIR


@pytest.fixture(scope="module")
def regmap():
    return load_map(CONTRACTS_DIR / "modbus-map.yaml")


def minimal_doc() -> dict:
    return {
        "version": 3,
        "endianness": "big",
        "mirror_fc03_fc04": True,
        "blocks": [
            {"name": "info", "start": 0, "count": 4, "items": [{"offset": 0, "name": "map_version", "type": "uint16"}]},
            {"name": "temp", "start": 10, "count": 4, "type": "int16", "scale": 0.1, "unit": "degC", "points": ["A", "B"]},
            {"name": "dt", "start": 20, "count": 4, "type": "int16", "scale": 0.1, "unit": "K", "points_ref": "temp"},
            {
                "name": "cmd",
                "start": 30,
                "count": 2,
                "access": "write",
                "functions": [6, 16],
                "items": [{"offset": 0, "name": "password", "type": "uint16"}],
            },
        ],
        "coils": {"items": [{"addr": 0, "name": "critical_alarm"}, {"addr": 1, "name": "comms_ok"}]},
    }


# ------------------------------------------------------------------ gercek sozlesme
@pytest.mark.parametrize(
    "name,address",
    [
        ("device_info.map_version", 0),
        ("health.heartbeat", 27),
        ("conn_temp.GIRIS_L1", 100),
        ("conn_temp.GIRIS_L2", 101),
        ("conn_temp.DSYA3_L2", 111),
        ("conn_temp.DSYA7_L3", 124),
        ("conn_dt.DSYA3_L2", 161),
        ("k_index.DSYA3_L2", 211),
        ("environment.td_margin_k", 303),
        ("electrical_mirror.cosphi", 410),
        ("arc_mirror.trip_count", 501),
        ("risk.ttl_hours", 702),
        ("alarms.latched_bits_0_15", 810),
        ("event.ts_lo", 833),
        ("command.password", 900),
        ("command.test_alarm", 904),
    ],
)
def test_contract_register_addresses(regmap, name, address):
    assert regmap.register(name).address == address


def test_block_type_scale_and_unit_are_inherited_by_items(regmap):
    td_margin = regmap.register("environment.td_margin_k")
    assert (td_margin.type, td_margin.scale, td_margin.unit) == ("int16", 0.1, "K")
    k_ratio = regmap.register("k_index.GIRIS_L2")
    assert (k_ratio.type, k_ratio.scale, k_ratio.unit, k_ratio.point) == ("int16", 0.1, "percent_of_baseline", "GIRIS_L2")


def test_item_type_and_scale_override_block(regmap):
    cosphi = regmap.register("electrical_mirror.cosphi")
    current = regmap.register("electrical_mirror.i_l1_a")
    assert (cosphi.type, cosphi.scale) == ("int16", 0.001)
    assert (current.type, current.scale) == ("uint16", 0.1)


def test_tvoc_mirror_is_read_only_and_keeps_source_pdu(regmap):
    """GK6: koruma devresine yazma yok; ag gecidi bu bayraga gore yazmayi reddeder."""
    assert regmap.block("arc_mirror").access == "read_only"
    assert regmap.register("arc_mirror.system_state").src_pdu == 1300
    assert regmap.register("arc_mirror.trip_count").access == "read_only"


def test_only_command_block_is_writable(regmap):
    writable = [block.name for block in regmap.blocks if block.access == "write"]
    assert writable == ["command"]
    assert regmap.block("command").functions == (6, 16)


def test_points_follow_conn_temp_order(regmap):
    assert regmap.points[:5] == ("GIRIS_L1", "GIRIS_L2", "GIRIS_L3", "GIRIS_N", "DSYA1_L1")
    assert len(regmap.points) == 25


def test_coils(regmap):
    assert [(c.address, c.name) for c in regmap.coils] == [
        (0, "critical_alarm"),
        (1, "warning_active"),
        (2, "comms_ok"),
        (3, "maint_mode"),
        (4, "prot_health_ok"),
        (5, "data_quality_ok"),
    ]


@pytest.mark.parametrize(
    "address,count,block",
    [
        (100, 50, "conn_temp"),  # blogun tamami
        (149, 1, "conn_temp"),  # son register
        (150, 1, "conn_dt"),
        (900, 10, "command"),
        (148, 4, None),  # conn_temp -> conn_dt sinirini asar
        (40, 1, None),  # health (20-39) ile conn_temp (100) arasindaki bosluk
        (905, 10, None),  # command blogunun sonunu asar
    ],
)
def test_block_for_range(regmap, address, count, block):
    found = regmap.block_for(address, count)
    assert (found.name if found else None) == block


def test_version_and_flags(regmap):
    assert regmap.version == 1
    assert regmap.mirror_fc03_fc04 is True


# ------------------------------------------------------------------ dogrulama
def test_minimal_doc_parses():
    regmap = parse_map(minimal_doc())
    assert regmap.register("dt.B").address == 21
    assert regmap.register("cmd.password").access == "write"


def test_overlapping_blocks_rejected():
    doc = minimal_doc()
    doc["blocks"][2]["start"] = 12  # dt 12-15, temp 10-13 ile cakisir
    with pytest.raises(MapError, match=r"temp.*dt|dt.*temp"):
        parse_map(doc)


def test_item_offset_outside_block_rejected():
    doc = minimal_doc()
    doc["blocks"][0]["items"].append({"offset": 4, "name": "late", "type": "uint16"})
    with pytest.raises(MapError, match="late"):
        parse_map(doc)


def test_duplicate_offset_rejected():
    doc = minimal_doc()
    doc["blocks"][0]["items"].append({"offset": 0, "name": "twin", "type": "uint16"})
    with pytest.raises(MapError, match="twin"):
        parse_map(doc)


def test_more_points_than_registers_rejected():
    doc = minimal_doc()
    doc["blocks"][1]["points"] = ["A", "B", "C", "D", "E"]
    with pytest.raises(MapError, match="temp"):
        parse_map(doc)


def test_unknown_points_ref_rejected():
    doc = minimal_doc()
    doc["blocks"][2]["points_ref"] = "nope"
    with pytest.raises(MapError, match="nope"):
        parse_map(doc)


def test_register_without_type_rejected():
    doc = minimal_doc()
    del doc["blocks"][0]["items"][0]["type"]
    with pytest.raises(MapError, match="map_version"):
        parse_map(doc)


def test_unknown_register_type_rejected():
    doc = minimal_doc()
    doc["blocks"][0]["items"][0]["type"] = "float32"
    with pytest.raises(MapError, match="float32"):
        parse_map(doc)


def test_write_block_with_read_function_rejected():
    doc = minimal_doc()
    doc["blocks"][3]["functions"] = [3, 16]
    with pytest.raises(MapError, match="cmd"):
        parse_map(doc)


def test_duplicate_coil_address_rejected():
    doc = minimal_doc()
    doc["coils"]["items"][1]["addr"] = 0
    with pytest.raises(MapError, match="coil"):
        parse_map(doc)


def test_parse_does_not_mutate_input():
    doc = minimal_doc()
    before = copy.deepcopy(doc)
    parse_map(doc)
    assert doc == before
