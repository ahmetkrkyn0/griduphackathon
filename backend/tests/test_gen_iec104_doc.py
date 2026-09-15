"""TB3 Adim 8 (Could) — scripts/gen_iec104_doc.py: IEC 104 nokta plani sozlesme + koddan uretilir (elle yazilmaz, kural 10)."""

from __future__ import annotations

import dataclasses
import importlib.util
import sys

import pytest

from helpers import REPO_ROOT


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("gen_iec104_doc", REPO_ROOT / "scripts" / "gen_iec104_doc.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def test_measured_rows_carry_modbus_address_unit_deadband_and_invalid_rule(gen):
    rows = {row["ad"]: row for row in gen.measured_rows()}
    l2 = rows["conn_temp.GIRIS_L2"]
    assert (l2["ioa"], l2["pdu"], l2["birim"], l2["olu_bant"], l2["gecersiz"]) == (1101, 101, "degC", "1", "ham 0x8000")
    cosphi = rows["electrical_mirror.cosphi"]
    assert (cosphi["ioa"], cosphi["olu_bant"]) == (1410, "0.01")
    assert rows["pd.amp_dbmv"]["gecersiz"] == "-"  # sozlesme notu: AG panoda 0 gecerli deger
    assert "command.password" not in rows


def test_single_point_rows_use_contract_priority_and_text(gen, contracts):
    rows = {row["ad"]: row for row in gen.single_rows()}
    k_warn = rows["ALM-K-WARN"]
    assert (k_warn["ioa"], k_warn["tur"], k_warn["oncelik"]) == (2004, "alarm biti 4", "P3")
    assert k_warn["aciklama"] == contracts.alarm("ALM-K-WARN")["text"]
    assert (rows["comms_ok"]["ioa"], rows["comms_ok"]["tur"]) == (3002, "coil 2")


def test_interop_field_widths_and_apdu_limits_are_measured_from_the_codec(gen):
    """Birlikte calisabilirlik listesinin (§7) alan uzunluklari sabitten degil, kodlayicinin urettigi bayttan olculur."""
    assert gen.field_widths() == {"tip": 1, "vsq": 1, "cot": 2, "ca": 2, "ioa": 3}  # COT = neden + kaynak adres
    block = gen.table_interop()
    assert f"| Azami APDU (uzunluk alani: kontrol alani + ASDU) | {gen.iec104.MAX_LENGTH} |" in block
    assert f"| Azami APDU (hat uzerinde, baslangic + uzunluk dahil) | {2 + gen.iec104.MAX_LENGTH} |" in block
    assert f"| Azami ASDU | {gen.iec104.MAX_ASDU} |" in block
    assert "| Iletim nedeni (COT) | 2 |" in block and "| Bilgi nesnesi adresi (IOA) | 3 |" in block


def test_interop_marks_control_asdus_and_absent_functions_as_unsupported(gen):
    """GK6: kontrol ASDU'lari, sayac sorgulamasi ve dosya transferi standardin formunda ACIKCA desteklenmiyor isaretlenir."""
    iec104 = gen.iec104
    assert gen.served_types() == (iec104.C_IC_NA_1, iec104.C_CS_NA_1)  # sunucunun islev bagladigi tek iki tip
    assert not {iec104.C_SC_NA_1, iec104.C_DC_NA_1} & set(gen.served_types())
    assert "t0" not in {field.name for field in dataclasses.fields(gen.iec104_server.Timing)}
    block = gen.table_interop()
    for label in ("Komut iletimi", "Sayac (integrated totals) sorgulamasi", "Parametre yukleme", "Dosya transferi",
                  "Nokta bazli okuma (okuma yordami)", "Istasyon baslatma (baslatma sonu bildirimi)"):
        assert f"| {label} | - |" in block
    assert "| t0 (baglanti kurma) | - |" in block
    assert f"| {iec104.C_SC_NA_1} | `C_SC_NA_1` | kontrol | - |" in block


def test_committed_doc_is_up_to_date(gen):
    assert gen.main(["--check"]) == 0
