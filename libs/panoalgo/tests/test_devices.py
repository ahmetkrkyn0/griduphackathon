"""Cihaz register modeli testleri — PLAN.md TA3 Adim 1-2.

Beklenen degerlerin kaynagi, repo icindeki ORIJINAL kilavuzlardir:
  Hackathon Verileri/1SFC170017M0201_Rev_D_TVOC-2_Modbus_Manual.pdf
  Hackathon Verileri/MPR-53CS_Modbus_Register_Map_EN.pdf
ve HACKATHON_ANALIZ_RAPORU.md 3.5 / 3.6 / 15.1.

Kilavuzdaki SAYISAL ORNEKLER dogrudan test edilir: 0x42B6 -> 2016-10-04,
0x0922 -> 09:34, CT 500 ile 2309 A -> ham 4618. Juri QModMaster ile baglanip
okuyacagi icin adreslerin ve kodlamalarin kilavuzla birebir tutmasi sart.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from panoalgo.devices import (
    MPR_ADDR,
    MPR_CT_REGISTER,
    MPR_DIGITAL_IN,
    MPR_DIGITAL_OUT,
    TVOC2_EMPTY,
    TVOC2_FACTORY_SLAVE_ID,
    TVOC2_SENSOR_STATUS_X2,
    TVOC2_STATE_ACTIVE_ERROR,
    TVOC2_STATE_ACTIVE_TRIP,
    TVOC2_SYSTEM_STATE_REG,
    TVOC2_TRIP_BASE,
    TVOC2_TRIP_COUNT_REG,
    Mpr53csDevice,
    Tvoc2Device,
    days_since_epoch,
    decode_hhmm,
    encode_hhmm,
)


# ------------------------------------------------------ tarih/saat kodlamasi


def test_manual_date_example_decodes_to_the_documented_day():
    """Kilavuz ornegi: 0x42B6 = 17078 gun -> 4 Ekim 2016."""
    assert days_since_epoch(date(2016, 10, 4)) == 0x42B6 == 17078


def test_epoch_day_is_zero():
    assert days_since_epoch(date(1970, 1, 1)) == 0


def test_manual_time_example_is_binary_not_bcd():
    """Kilavuz ornegi: 0x0922 -> 09:34. Ondalik 2338'i '23:38' okumak YANLIS."""
    assert encode_hhmm(9, 34) == 0x0922
    assert decode_hhmm(0x0922) == (9, 34)


def test_time_encoding_rejects_impossible_clock_values():
    with pytest.raises(ValueError):
        encode_hhmm(24, 0)
    with pytest.raises(ValueError):
        encode_hhmm(9, 60)


# -------------------------------------------------- TVOC-2 haberlesme kapali


def test_factory_device_is_silent_because_communication_is_disabled():
    """Kilavuz 1.3: 'ID 248 ... indicates that the communication is DISABLED.'
    Cihaz istisna bile dondurmez, tamamen sessiz kalir."""
    device = Tvoc2Device()
    assert device.slave_id == TVOC2_FACTORY_SLAVE_ID
    assert device.communication_enabled is False
    assert device.read(TVOC2_SYSTEM_STATE_REG) is None


def test_device_answers_once_it_is_given_a_valid_id():
    """Gecerli ID araligi 1-247. Sahada en sik yasanan devreye alma hatasi budur."""
    device = Tvoc2Device(slave_id=10)
    assert device.communication_enabled is True
    assert device.read(TVOC2_SYSTEM_STATE_REG) == 0


@pytest.mark.parametrize("slave_id", [0, 248, 249, 255])
def test_ids_outside_the_valid_range_keep_the_device_silent(slave_id):
    assert Tvoc2Device(slave_id=slave_id).communication_enabled is False


# --------------------------------------------------------- TVOC-2 sakin durum


def test_calm_device_reports_no_trips():
    device = Tvoc2Device(slave_id=10)
    assert device.read(TVOC2_TRIP_COUNT_REG) == 0
    assert device.read(TVOC2_SYSTEM_STATE_REG) == 0


def test_empty_trip_slots_read_as_ffff_not_zero():
    """Kilavuz 4.4.1: 7'den az trip varsa ilgili registerlar 0xFFFF'tir.
    Sifir okunsaydi '1970-01-01'de trip olmus' gibi gorunurdu."""
    device = Tvoc2Device(slave_id=10)
    assert device.read(TVOC2_TRIP_BASE) == TVOC2_EMPTY
    assert device.read(TVOC2_TRIP_BASE + 3) == TVOC2_EMPTY


def test_sensor_status_is_zero_while_there_is_no_active_error():
    """Kilavuz 4.4.2: bu registerlar AKTIF HATA bilgisini tasir; hata yoksa 0x0000.
    '1 = OK' bit anlami yalnizca aktif hata varken gecerlidir."""
    device = Tvoc2Device(slave_id=10)
    assert device.read(TVOC2_SENSOR_STATUS_X2) == 0x0000


def test_the_gap_register_in_each_trip_block_is_undefined():
    """Her trip blogu 6 okunabilir register + 1 BOSLUK (stride 7)."""
    device = Tvoc2Device(slave_id=10)
    assert device.read(TVOC2_TRIP_BASE + 6) is None


# ------------------------------------------------------------ TVOC-2 olaylar


def test_a_trip_raises_the_state_bit_and_the_counter():
    device = Tvoc2Device(slave_id=10)
    device.record_trip(datetime(2016, 10, 4, 9, 34, 12, tzinfo=timezone.utc))

    assert device.read(TVOC2_TRIP_COUNT_REG) == 1
    assert device.read(TVOC2_SYSTEM_STATE_REG) & TVOC2_STATE_ACTIVE_TRIP


def test_trip_log_records_the_documented_date_and_time_encoding():
    device = Tvoc2Device(slave_id=10)
    device.record_trip(datetime(2016, 10, 4, 9, 34, 12, tzinfo=timezone.utc))

    assert device.read(TVOC2_TRIP_BASE + 3) == 0x42B6   # tarih
    assert device.read(TVOC2_TRIP_BASE + 4) == 0x0922   # HHMM
    assert device.read(TVOC2_TRIP_BASE + 5) == 12       # saniye


def test_newest_trip_is_first_and_the_log_keeps_seven():
    device = Tvoc2Device(slave_id=10)
    for day in range(1, 10):
        device.record_trip(datetime(2026, 3, day, 8, 0, tzinfo=timezone.utc))

    assert device.read(TVOC2_TRIP_COUNT_REG) == 7
    assert device.read(TVOC2_TRIP_BASE + 3) == days_since_epoch(date(2026, 3, 9))


def test_reset_clears_the_active_trip_but_not_the_log():
    """PDU 1000 aktif tripi temizler; log silinmez, 149 azalmaz.
    (Bizim ag gecidimiz bu yazmayi zaten engeller — GK6.)"""
    device = Tvoc2Device(slave_id=10)
    device.record_trip(datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc))
    device.reset_trip()

    assert device.read(TVOC2_SYSTEM_STATE_REG) & TVOC2_STATE_ACTIVE_TRIP == 0
    assert device.read(TVOC2_TRIP_COUNT_REG) == 1


def test_sensor_error_fills_the_status_registers_and_the_state_bit():
    device = Tvoc2Device(slave_id=10)
    device.raise_sensor_error()

    assert device.read(TVOC2_SYSTEM_STATE_REG) & TVOC2_STATE_ACTIVE_ERROR
    assert device.read(TVOC2_SENSOR_STATUS_X2) != 0x0000


def test_clearing_errors_returns_the_status_registers_to_zero():
    device = Tvoc2Device(slave_id=10)
    device.raise_sensor_error()
    device.clear_errors()

    assert device.read(TVOC2_SENSOR_STATUS_X2) == 0x0000


def test_write_attempts_are_recorded_as_evidence():
    """Cihaz yazmayi kabul etse de ag gecidimiz engeller; deneme kaydi GK6 kanitidir."""
    device = Tvoc2Device(slave_id=10)
    device.note_write_attempt(1000, 1)
    assert device.write_attempts == [(1000, 1)]


# ----------------------------------------------------------------- MPR-53CS


def test_nominal_current_matches_the_report_worked_example():
    """Rapor 15.1: 2309 A, CT 500 -> ham 4618."""
    device = Mpr53csDevice(ct_ratio=500)
    assert device.current_raw(2309.0) == 4618


def test_current_conversion_round_trips():
    device = Mpr53csDevice(ct_ratio=500)
    assert device.current_from_raw(device.current_raw(1500.0)) == pytest.approx(1500.0, abs=0.5)


def test_secondary_five_amps_maps_to_the_transformer_primary():
    """ham 5000 -> 5.000 A sekonder -> x500 = 2500 A primer (AT nominali)."""
    device = Mpr53csDevice(ct_ratio=500)
    assert device.current_from_raw(5000) == pytest.approx(2500.0)


def test_scales_follow_the_manual():
    assert Mpr53csDevice.voltage_raw(231.0) == 2310      # 0.1 V
    assert Mpr53csDevice.thd_raw(24.5) == 245            # 0.1 %
    assert Mpr53csDevice.cosphi_raw(0.92) == 920         # 0.001
    assert Mpr53csDevice.cosphi_raw(-0.85) == -850       # isaretli
    assert Mpr53csDevice.frequency_raw(49.98) == 4998    # 0.01 Hz


def test_ct_ratio_is_published_at_the_manual_address():
    """Juri 0x8001'i okuyunca 500 gormeli."""
    device = Mpr53csDevice(ct_ratio=500)
    assert device.registers()[MPR_CT_REGISTER] == 500


def test_thirty_two_bit_values_use_high_word_first():
    """contracts/modbus-map.yaml word_order: high_first."""
    device = Mpr53csDevice(ct_ratio=500, i_ph=(2309.0, 0.0, 0.0))
    regs = device.registers()
    raw = (regs[MPR_ADDR["i_l1"]] << 16) | regs[MPR_ADDR["i_l1"] + 1]
    assert raw == 4618


def test_digital_io_registers_are_single_not_paired():
    """84/85 'her olcum 2 register' kuralinin TEK istisnasidir."""
    regs = Mpr53csDevice().registers()
    assert MPR_DIGITAL_OUT in regs
    assert MPR_DIGITAL_IN in regs
    assert MPR_DIGITAL_OUT + 1 == MPR_DIGITAL_IN   # aralarinda bosluk yok


def test_zero_ct_ratio_is_rejected():
    with pytest.raises(ValueError):
        Mpr53csDevice(ct_ratio=0).current_raw(100.0)
