"""TB3 Adim 2 — pano son durumu + alarm yoneticisi -> Pano Beyni register goruntusu (app.scada.encoder).

Beklenen ham degerler tests/fixtures/tel_valid.json'dan ELLE hesaplanmistir (olcek = sozlesmedeki
`scale`; ham = fiziksel / olcek). Negatif int16 degerler Modbus'ta ikiye tumleyen uint16 olarak gider
(-25 -> 65511). "Yok" degerleri: int16 -> 0x8000 (32768), uint16 -> 0xFFFF (65535).
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.alarm_manager import Alarm
from app.scada.encoder import EventLog, PanelEncoder, PanelSnapshot
from app.scada.map_loader import load_map
from helpers import CONTRACTS_DIR, utc

RX = utc(2026, 9, 13, 10, 0, 2)
NOW = utc(2026, 9, 13, 10, 1, 0)  # son veriden 58 s sonra
NA16 = 0x8000
NAU16 = 0xFFFF

COILS = ("critical_alarm", "warning_active", "comms_ok", "maint_mode", "prot_health_ok", "data_quality_ok")


@pytest.fixture(scope="module")
def regmap():
    return load_map(CONTRACTS_DIR / "modbus-map.yaml")


@pytest.fixture(scope="module")
def encoder(regmap, contracts):
    return PanelEncoder(regmap, contracts)


def alarm(code: str, prio: str, *, state: str = "active", returned: bool = False, alarm_id: int = 1) -> Alarm:
    return Alarm(
        id=alarm_id,
        pano_id="ADM-00001",
        code=code,
        prio=prio,
        point=None,
        event_id=f"EVT-{alarm_id}",
        raised_at=utc(2026, 9, 13, 9, 0),
        last_true_at=utc(2026, 9, 13, 9, 0),
        annunciated_at=utc(2026, 9, 13, 9, 0),
        state=state,
        cleared_at=utc(2026, 9, 13, 9, 30) if returned else None,
    )


def snapshot(payload: dict, **overrides) -> PanelSnapshot:
    fields = {
        "pano_id": "ADM-00001",
        "pano_type": "1600kVA-dahili",
        "payload": payload,
        "last_rx": RX,
        "alarms": (),
        "latched_bits": 0,
        "events": EventLog(),
    }
    fields.update(overrides)
    return PanelSnapshot(**fields)


def read(image, regmap, name: str) -> int:
    return image.registers[regmap.register(name).address]


def coils(image) -> dict[str, bool]:
    return dict(zip(COILS, image.coils))


# ------------------------------------------------------------------ olcumler
@pytest.mark.parametrize(
    "name,raw",
    [
        ("device_info.map_version", 1),
        ("device_info.fw_version", 0x0100),  # "0.1.0"
        ("device_info.serial_hi", NAU16),  # telemetride seri no yok
        ("device_info.pano_type", 1),
        ("device_info.point_count", 5),
        ("health.uptime_h", 24),
        ("health.last_sync_m", 0),
        ("health.supply_state", NAU16),
        ("health.backup_pct", 100),
        ("health.rssi_dbm_neg", 71),
        ("health.nodes_ok", 5),
        ("health.nodes_total", 5),
        ("health.heartbeat", 42),
        ("health.buffered_msgs", 0),
        ("health.baseline_day", 7),
        ("conn_temp.GIRIS_L1", 415),
        ("conn_temp.GIRIS_L2", 780),
        ("conn_temp.GIRIS_N", 271),
        ("conn_temp.DSYA3_L2", 482),
        ("conn_temp.DSYA1_L1", NA16),  # tanimli nokta, telemetride yok
        ("conn_dt.GIRIS_L2", 530),
        ("conn_dt.DSYA3_L2", 232),
        ("k_index.GIRIS_L1", 1020),
        ("k_index.GIRIS_L2", 1450),
        ("k_index.GIRIS_N", NA16),  # noktada k_ratio yok
        ("k_index.DSYA3_L2", 1100),
        ("environment.t_low_c", 250),
        ("environment.rh_low_pct", 600),
        ("environment.td_low_c", 167),
        ("environment.td_margin_k", 83),
        ("environment.t_up_c", 315),
        ("environment.dt_air_k", 65),
        ("environment.voc_idx", NAU16),  # sozlesme notu: 65535 = sensor yok
        ("electrical_mirror.i_l1_a", 4000),
        ("electrical_mirror.i_l2_a", 4200),
        ("electrical_mirror.i_l3_a", 3880),
        ("electrical_mirror.i_n_a", 480),
        ("electrical_mirror.u_l1_v", 2312),
        ("electrical_mirror.thd_i_l2_pct", 43),
        ("electrical_mirror.cosphi", 960),
        ("electrical_mirror.unbal_pct", 41),
        ("electrical_mirror.mpr_comm_ok", 1),
        ("arc_mirror.system_state", 1),
        ("arc_mirror.trip_count", 0),
        ("arc_mirror.sensor_status_x2", 2),
        ("arc_mirror.amb_light_x3", 15),
        ("arc_mirror.last_trip_date", NAU16),  # kenar merkeze gondermiyor
        ("arc_mirror.prot_health_ok", 1),
        ("arc_mirror.tvoc_comm_ok", 1),
        ("pd.pulses_per_s", NAU16),  # AG pano: pd null -> sozlesme notu 65535/0
        ("pd.amp_dbmv", 0),
        ("pd.phase_cluster", NAU16),
        ("risk.risk_score", 38),
        ("risk.fault_mode", 1),  # HYP-LOOSE-CONN
        ("risk.ttl_hours", 151),  # 150.5 yukari yuvarlanir
        ("risk.worst_point", 1),  # GIRIS_L2: dT 53 K > 50 ve K/K0 1,45 > 1,3
        ("command.password", 0),  # sifre asla okunmaz
        ("command.maint_mode", 0),
    ],
)
def test_measurements_are_scaled_into_registers(encoder, regmap, tel_payload, name, raw):
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, name) == raw


def test_reserved_registers_read_zero(encoder, regmap, tel_payload):
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert image.registers[125] == 0  # conn_temp: 25 noktadan sonraki yedek register
    assert image.registers[30] == 0  # health blogunda tanimsiz offset


def test_negative_values_are_twos_complement(encoder, regmap, tel_payload):
    tel_payload["env"]["td_margin_k"] = -2.5
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "environment.td_margin_k") == 65511  # -25


def test_out_of_range_values_saturate_instead_of_wrapping(encoder, regmap, tel_payload):
    tel_payload["t_conn"][0]["t_c"] = 5000.0  # 50000 int16'ya sigmaz
    tel_payload["health"]["rssi_dbm"] = 5.0  # pozitif RSSI -> negatif uint16 olmaz
    tel_payload["elec"]["i_ph"][0] = 9000.0  # 90000 > 65534
    tel_payload["env"]["td_margin_k"] = -5000.0  # -50000 -> -32767 (-32768 "yok" icin ayrildi)
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "conn_temp.GIRIS_L1") == 32767
    assert read(image, regmap, "environment.td_margin_k") == 32769  # -32767 ikiye tumleyen
    assert read(image, regmap, "health.rssi_dbm_neg") == 0
    assert read(image, regmap, "electrical_mirror.i_l1_a") == 65534  # 65535 "yok" anlamina ayrildi


def test_decimal_scale_rounds_half_up_without_float_error(encoder, regmap, tel_payload):
    """4.35 / 0.1 kayan noktada 43.4999... olur; dogru ham deger 44."""
    tel_payload["env"]["t_up_c"] = 4.35
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "environment.t_up_c") == 44


def test_worst_point_ignores_bad_quality_points(encoder, regmap, tel_payload):
    tel_payload["t_conn"][3]["dt_c"] = 90.0  # GIRIS_N alarm seviyesinde AMA q = 4 (guvenilmez)
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "risk.worst_point") == 1  # hala GIRIS_L2


def test_last_gasp_sets_supply_state(encoder, regmap, tel_payload):
    image = encoder.encode(snapshot(tel_payload, alarms=(alarm("ALM-LASTGASP", "P2"),)), NOW)
    assert read(image, regmap, "health.supply_state") == 2


def test_tvoc_without_comm_flag_is_assumed_reachable(encoder, regmap, tel_payload):
    del tel_payload["tvoc"]["comm_ok"]
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "arc_mirror.tvoc_comm_ok") == 1


def test_counters_wrap_like_a_device_counter(encoder, regmap, tel_payload):
    tel_payload["seq"] = 65538
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "health.heartbeat") == 2


def test_firmware_version_encoding(encoder, regmap, tel_payload):
    tel_payload["fw"] = "1.2.3"
    assert read(encoder.encode(snapshot(tel_payload), NOW), regmap, "device_info.fw_version") == 0x1203
    tel_payload["fw"] = "gelistirme"
    assert read(encoder.encode(snapshot(tel_payload), NOW), regmap, "device_info.fw_version") == NAU16
    tel_payload["fw"] = "16.0.0"  # major bir nibble'a sigmaz
    assert read(encoder.encode(snapshot(tel_payload), NOW), regmap, "device_info.fw_version") == NAU16


def test_panel_without_tvoc_reports_unprotected(encoder, regmap, tel_payload):
    tel_payload["tvoc"] = None
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "arc_mirror.trip_count") == NAU16
    assert read(image, regmap, "arc_mirror.prot_health_ok") == 0
    assert read(image, regmap, "arc_mirror.tvoc_comm_ok") == 0
    assert coils(image)["prot_health_ok"] is False


def test_pd_values_when_present(encoder, regmap, tel_payload):
    tel_payload["pd"] = {"pps": 12.0, "amp_dbmv": -35.0, "trend": 0.25, "phase_cluster": 0.8}
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "pd.pulses_per_s") == 12
    assert read(image, regmap, "pd.amp_dbmv") == 65501  # -35
    assert read(image, regmap, "pd.trend_slope") == 25
    assert read(image, regmap, "pd.phase_cluster") == 80


def test_unknown_ttl_and_hypothesis(encoder, regmap, tel_payload):
    tel_payload["risk"] = {"score": 5, "mode": "HYP-UYDURMA", "ttl_h": None}
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "risk.fault_mode") == NAU16
    assert read(image, regmap, "risk.ttl_hours") == NAU16


def test_ttl_suppressed_for_quality_encodes_as_na(encoder, regmap, tel_payload):
    """P1 Task 1 (S8 bilinen siniri, docs/05-anomali-tespiti.md #10): kalite bayragi (q)
    set olan bir noktanin ttl_h'i artik panoalgo'da kaynaginda None'a cekiliyor
    (EdgePipeline._suppress_ttl_when_quality_suspect, libs/panoalgo/panoalgo/edge.py).
    O fonksiyonun kendisi libs/panoalgo/tests/test_edge.py::test_ttl_is_suppressed_when_
    the_point_quality_is_suspect'te ayrica dogrulanir; bu test EdgePipeline'i calistirmaz,
    onun ciktisina guvenir (test_p1_validity_scenarios.py'deki S8 senaryosuyla ayni sinir).
    Burada kilitlenen, Task 1'in urettigi payload seklini (en kotu nokta GIRIS_L2'nin q'su
    set, ttl_h'i None) elle kurup, ZATEN DOGRU CALISAN SCADA kodlayicisinin (encoder.py
    _raw: "value is None -> na sentinel") bu None'i eski/sahte bir sayi olarak degil,
    sozlesmedeki "yok" sentinel'ine (uint16 0xFFFF) kodladigidir -- o None-ise-NA kurali
    bozulursa (veya risk.ttl_hours icin atlanirsa) risk.ttl_h sayisal/0 kalir ve bu
    register artik NAU16 donmez, test kirilir."""
    tel_payload["t_conn"][1]["q"] = 1  # GIRIS_L2: taban veride worst_point/risk.ttl_h bu noktadan gelir
    tel_payload["t_conn"][1]["ttl_h"] = None  # Task 1'in kaynakta urettigi durum
    tel_payload["risk"]["ttl_h"] = None  # ayni supheye bagli panel-geneli risk blogu yansimasi
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "risk.ttl_hours") == NAU16


def test_unknown_panel_type(encoder, regmap, tel_payload):
    image = encoder.encode(snapshot(tel_payload, pano_type=None), NOW)
    assert read(image, regmap, "device_info.pano_type") == 0


# ------------------------------------------------------------------ haberlesme
def test_comms_timeout_clears_comms_coil(encoder, regmap, tel_payload, contracts):
    timeout = contracts.thresholds["heartbeat_timeout_min"]
    image = encoder.encode(snapshot(tel_payload), RX + timedelta(minutes=timeout, seconds=1))
    assert coils(image)["comms_ok"] is False
    assert read(image, regmap, "health.last_sync_m") == timeout


def test_comms_ok_just_inside_timeout(encoder, regmap, tel_payload, contracts):
    timeout = contracts.thresholds["heartbeat_timeout_min"]
    image = encoder.encode(snapshot(tel_payload), RX + timedelta(minutes=timeout))
    assert coils(image)["comms_ok"] is True


# ------------------------------------------------------------------ alarmlar
def test_alarm_bits_follow_live_alarm_state(encoder, regmap, tel_payload):
    alarms = (
        alarm("ALM-K-WARN", "P3", alarm_id=1),  # bit 4, onaysiz
        alarm("ALM-THR-TERM-WARN", "P3", state="acked", alarm_id=2),  # bit 0, onayli ama kosul suruyor
        alarm("ALM-DEW-WARN", "P3", state="shelved", alarm_id=3),  # bit 7, rafta: SCADA'ya da duyurulmaz
        alarm("ALM-ARC-TRIP", "P1", returned=True, alarm_id=4),  # bit 11, normale donmus onaysiz P1
    )
    image = encoder.encode(snapshot(tel_payload, alarms=alarms, latched_bits=1 << 18), NOW)
    assert read(image, regmap, "alarms.alarm_bits_0_15") == 0b10001  # bit 4 + bit 0
    assert read(image, regmap, "alarms.alarm_bits_16_31") == 0
    assert read(image, regmap, "alarms.latched_bits_0_15") == 2065  # canli (0,4) + onaysiz normale donmus P1 (11)
    assert read(image, regmap, "alarms.latched_bits_16_31") == 4  # saklanan mandal: bit 18 (ALM-COMMS-LOST)
    assert read(image, regmap, "alarms.active_alarm_count") == 2
    assert read(image, regmap, "alarms.highest_prio") == 3
    assert coils(image)["critical_alarm"] is False
    assert coils(image)["warning_active"] is True


def test_live_p1_sets_critical_coil_and_priority(encoder, regmap, tel_payload):
    alarms = (alarm("ALM-K-WARN", "P3", alarm_id=1), alarm("ALM-PROT-HEALTH", "P1", state="acked", alarm_id=2))
    image = encoder.encode(snapshot(tel_payload, alarms=alarms), NOW)
    assert read(image, regmap, "alarms.highest_prio") == 1
    assert coils(image)["critical_alarm"] is True


def test_highest_priority_ranks_sys_above_info(encoder, regmap, tel_payload):
    """Kayit kodu 4=INFO, 5=SYS; ama aciliyet sirasi P1 > P2 > P3 > SYS > INFO."""
    alarms = (alarm("ALM-PANEL-TEMP", "INFO", alarm_id=1), alarm("ALM-COMMS-LOST", "SYS", alarm_id=2))
    image = encoder.encode(snapshot(tel_payload, alarms=alarms), NOW)
    assert read(image, regmap, "alarms.highest_prio") == 5
    assert read(image, regmap, "alarms.alarm_bits_16_31") == (1 << 2) | (1 << 5)  # bit 18 + bit 21
    assert coils(image)["warning_active"] is False  # SYS/INFO elektriksel uyari degildir


def test_no_alarms(encoder, regmap, tel_payload):
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "alarms.highest_prio") == 0
    assert read(image, regmap, "alarms.active_alarm_count") == 0


def test_event_block(encoder, regmap, tel_payload):
    events = EventLog(count=3, last_bit=4, last_at=utc(2026, 9, 13, 9, 59, 0))
    image = encoder.encode(snapshot(tel_payload, events=events), NOW)
    assert read(image, regmap, "event.event_count") == 3
    assert read(image, regmap, "event.last_code") == 4
    assert (read(image, regmap, "event.ts_hi"), read(image, regmap, "event.ts_lo")) == (27302, 29668)  # 1789293540


def test_event_block_without_events(encoder, regmap, tel_payload):
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert read(image, regmap, "event.last_code") == NAU16
    assert (read(image, regmap, "event.ts_hi"), read(image, regmap, "event.ts_lo")) == (0, 0)


# ------------------------------------------------------------------ coil'ler
def test_summary_coils(encoder, regmap, tel_payload):
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert coils(image) == {
        "critical_alarm": False,
        "warning_active": False,
        "comms_ok": True,
        "maint_mode": False,
        "prot_health_ok": True,
        "data_quality_ok": False,  # GIRIS_N noktasinda q = 4
    }


def test_data_quality_ok_when_all_points_clean(encoder, regmap, tel_payload):
    tel_payload["t_conn"][3]["q"] = 0
    assert coils(encoder.encode(snapshot(tel_payload), NOW))["data_quality_ok"] is True


def test_live_data_quality_alarm_clears_quality_coil(encoder, regmap, tel_payload):
    tel_payload["t_conn"][3]["q"] = 0
    image = encoder.encode(snapshot(tel_payload, alarms=(alarm("ALM-DQ-FROZEN", "SYS"),)), NOW)
    assert coils(image)["data_quality_ok"] is False


def test_maintenance_mode(encoder, regmap, tel_payload):
    tel_payload["health"]["maint_mode"] = True
    image = encoder.encode(snapshot(tel_payload), NOW)
    assert coils(image)["maint_mode"] is True
    assert read(image, regmap, "command.maint_mode") == 1


# ------------------------------------------------------------------ kapsam korumasi
def test_register_without_central_source_refuses_to_build(contracts):
    """Sozlesmeye register eklenip kaynak tablosu unutulursa SCADA'ya sessizce 0 gitmemeli."""
    from app.scada.map_loader import parse_map

    doc = {
        "version": 1,
        "blocks": [{"name": "health", "start": 20, "count": 20, "items": [{"offset": 12, "name": "fan_rpm", "type": "uint16"}]}],
    }
    with pytest.raises(ValueError, match="health.fan_rpm"):
        PanelEncoder(parse_map(doc), contracts)
