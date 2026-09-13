"""TB3 Adim 8 (Could) — Pano Beyni haritasi -> IEC 104 bilgi nesneleri (app.scada.iec104_points).

IOA plani (rapor 6.4c "Modbus bloklariyla ayni mantik"): olculen deger IOA = 1000 + Modbus PDU adresi,
alarm biti IOA = 2000 + alarm-codes.yaml biti, ozet bit IOA = 3000 + coil adresi. Degerler Modbus ile ayni kodlayicidan gelir;
fiziksel deger = isaretli ham x olcek. Beklentiler tel_valid.json'dan elle (encoder testleriyle ayni ham degerler).
"""

from __future__ import annotations

import pytest

from app.alarm_manager import Alarm
from app.scada import iec104
from app.scada.encoder import EventLog, PanelEncoder, PanelSnapshot
from app.scada.iec104_points import PointCatalog
from app.scada.map_loader import load_map
from helpers import CONTRACTS_DIR, utc

RX = utc(2026, 9, 13, 10, 0, 2)
NOW = utc(2026, 9, 13, 10, 1, 0)


@pytest.fixture(scope="module")
def regmap():
    return load_map(CONTRACTS_DIR / "modbus-map.yaml")


@pytest.fixture(scope="module")
def encoder(regmap, contracts):
    return PanelEncoder(regmap, contracts)


@pytest.fixture(scope="module")
def catalog(regmap, encoder):
    return PointCatalog(regmap, encoder)


def image(encoder, payload, alarms=()):
    snapshot = PanelSnapshot("ADM-00001", "1600kVA-dahili", payload, RX, tuple(alarms), 0, EventLog())
    return encoder.encode(snapshot, NOW)


def k_warn() -> Alarm:
    t = utc(2026, 9, 13, 9, 0)
    return Alarm(id=1, pano_id="ADM-00001", code="ALM-K-WARN", prio="P3", point="GIRIS_L2", event_id="EVT-1",
                 raised_at=t, last_true_at=t, annunciated_at=t)


def by_ioa(values):
    return {value.ioa: value for value in values}


def test_ioa_plan(catalog):
    measured = {point.name: point.ioa for point in catalog.measured}
    assert measured["conn_temp.GIRIS_L2"] == 1101
    assert measured["k_index.GIRIS_L2"] == 1201
    assert measured["environment.td_margin_k"] == 1303
    assert measured["arc_mirror.trip_count"] == 1501
    singles = {point.name: point.ioa for point in catalog.single}
    assert singles["ALM-K-WARN"] == 2004
    assert singles["ALM-COMMS-LOST"] == 2018
    assert singles["comms_ok"] == 3002


def test_write_and_alarm_blocks_are_not_measured_values(catalog):
    ioas = {point.ioa for point in catalog.measured}
    assert not any(1800 <= ioa < 1830 or 1900 <= ioa < 1910 for ioa in ioas)  # alarms: tek nokta, command: IEC 104'te komut yok


def test_every_measured_register_of_the_map_has_an_object(catalog, regmap):
    expected = sum(len(b.registers) for b in regmap.blocks if b.name not in ("alarms", "command"))
    assert len(catalog.measured) == expected
    assert len({p.ioa for p in catalog.measured} | {p.ioa for p in catalog.single}) == len(catalog.measured) + len(catalog.single)


def test_values_are_physical_and_signed(catalog, encoder, tel_payload):
    tel_payload["env"]["td_margin_k"] = -2.5
    values = by_ioa(catalog.values(image(encoder, tel_payload)))
    assert (values[1101].type_id, values[1101].value, values[1101].quality) == (iec104.M_ME_NC_1, 78.0, 0)
    assert values[1201].value == pytest.approx(145.0)  # K/K0 yuzde olarak (1,45 -> 145,0)
    assert values[1303].value == pytest.approx(-2.5)
    assert values[1410].value == pytest.approx(0.96)  # cosphi, olcek 0.001
    assert values[1501].value == 0.0  # trip sayaci


def test_missing_values_are_invalid_quality(catalog, encoder, tel_payload):
    values = by_ioa(catalog.values(image(encoder, tel_payload)))
    assert values[1104].quality == iec104.QDS_IV  # DSYA1_L1 telemetride yok (0x8000)
    assert values[1307].quality == iec104.QDS_IV  # voc_idx null (0xFFFF)
    assert (values[1601].value, values[1601].quality) == (0.0, 0)  # pd.amp_dbmv: sozlesme notu "AG panoda 0" gecerli deger


def test_alarm_bits_and_coils_are_single_points(catalog, encoder, tel_payload):
    values = by_ioa(catalog.values(image(encoder, tel_payload, alarms=(k_warn(),))))
    assert (values[2004].type_id, values[2004].value, values[2004].quality) == (iec104.M_SP_NA_1, True, 0)
    assert values[2000].value is False
    assert values[3002].value is True  # comms_ok
    assert values[3000].value is False  # critical_alarm


def test_alarm_bits_above_15_come_from_the_second_register(catalog, encoder, tel_payload):
    t = utc(2026, 9, 13, 9, 0)
    comms_lost = Alarm(id=2, pano_id="ADM-00001", code="ALM-COMMS-LOST", prio="SYS", point=None, event_id="EVT-2",
                       raised_at=t, last_true_at=t, annunciated_at=t)
    values = by_ioa(catalog.values(image(encoder, tel_payload, alarms=(comms_lost,))))
    assert values[2018].value is True  # bit 18
    assert values[2004].value is False


def test_panel_without_image_is_all_invalid(catalog):
    values = catalog.values(None)
    assert values and all(value.quality == iec104.QDS_IV for value in values)


@pytest.mark.parametrize("name,deadband", [("conn_temp.GIRIS_L2", 1.0), ("electrical_mirror.cosphi", 0.01), ("pd.trend_slope", 0.1), ("arc_mirror.trip_count", 1.0)])
def test_spontaneous_deadband_ten_raw_steps_or_any_change_when_unscaled(catalog, name, deadband):
    point = next(p for p in catalog.measured if p.name == name)
    assert point.deadband == pytest.approx(deadband)
