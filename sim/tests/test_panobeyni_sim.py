"""Pano Beyni tasima kabugu (Kisi A, Y2): Modbus master -> kenar -> MQTT.

TA3 Adim 6 `[x]` isaretliydi ama `sim/panobeyni_sim.py` HICBIR DALDA VAR OLMAMISTI;
depoda hicbir Modbus ISTEMCISI yoktu, yani cihaz simulatorleri tek baslarina
duruyordu ve `tvoc2_sim.py --trip-after` ile uretilen gercek bir ark tripi MQTT'ye
hic ulasmiyordu.

Bu dosya, kabugun GERCEK cihaz simulatorlerine karsi calistigini olcer: testler
`mpr53cs_sim.py` ve `tvoc2_sim.py`'yi alt surec olarak ayaga kaldirir ve kabugu
onlara baglar. Sahte Modbus yok.
"""

from __future__ import annotations

import json

import pytest

from helpers import free_port, run_sim, sim_env, wait_for_port

import panobeyni_sim
from panobeyni_sim import DeviceReader, RingBuffer, _target
from panoalgo.devices import TVOC2_FACTORY_SLAVE_ID

pytestmark = pytest.mark.slow


@pytest.fixture
def cihazlar():
    """Gercek MPR-53CS ve TVOC-2 simulatorlerini ayaga kaldirir."""
    started = []

    def start(*, tvoc_slave: int = 10, trip_after: float = 0.0, sensor_error: bool = False):
        mpr_port, tvoc_port = free_port(), free_port()
        started.append(run_sim("mpr53cs_sim.py", "--host", "127.0.0.1",
                               "--port", str(mpr_port), "--slave-id", "1", "--ct", "500"))
        tvoc_args = ["--host", "127.0.0.1", "--port", str(tvoc_port), "--slave-id", str(tvoc_slave)]
        if trip_after:
            tvoc_args += ["--trip-after", str(trip_after)]
        if sensor_error:
            tvoc_args += ["--sensor-error"]
        started.append(run_sim("tvoc2_sim.py", *tvoc_args))
        wait_for_port(mpr_port)
        wait_for_port(tvoc_port)
        return mpr_port, tvoc_port

    yield start

    for proc in started:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001 - temizlik testi dusurmemeli
            proc.kill()


def reader_for(mpr_port: int, tvoc_port: int, tvoc_unit: int = 10) -> DeviceReader:
    reader = DeviceReader(("127.0.0.1", mpr_port), ("127.0.0.1", tvoc_port), 1, tvoc_unit)
    reader.connect()
    return reader


# ---------------------------------------------------------------- Modbus master


def test_it_reads_the_ct_ratio_from_the_real_device_register(cihazlar):
    """Kilavuz register'i 0x8001; kabuk olcegi cihazdan OGRENIR, koda gommez."""
    mpr_port, tvoc_port = cihazlar()

    reader = reader_for(mpr_port, tvoc_port)
    try:
        assert reader.ct_ratio == 500
    finally:
        reader.close()


def test_it_reads_phase_currents_over_real_modbus(cihazlar):
    """Akimlar 32-bit, iki register, high_first — cozum kilavuza uygun olmali."""
    mpr_port, tvoc_port = cihazlar()

    reader = reader_for(mpr_port, tvoc_port)
    try:
        elec = reader.read_electrical()
    finally:
        reader.close()

    assert elec is not None
    assert len(elec["i_ph"]) == 3
    # 1600 kVA / 400 V panonun akimlari makul aralikta olmali (anma 2309 A).
    assert all(0.0 <= value < 6000.0 for value in elec["i_ph"]), elec["i_ph"]
    assert any(value > 0.0 for value in elec["i_ph"]), "tum fazlar sifir; okuma calismiyor"
    assert 0.0 <= elec["i_n"] < 6000.0


def test_a_silent_factory_id_248_is_reported_as_no_comms_not_as_a_fault(cihazlar):
    """ID 248 sessizdir; bu 'koruma arizali' DEGIL 'haberlesme yok'tur."""
    mpr_port, tvoc_port = cihazlar(tvoc_slave=TVOC2_FACTORY_SLAVE_ID)

    reader = DeviceReader(("127.0.0.1", mpr_port), ("127.0.0.1", tvoc_port), 1, TVOC2_FACTORY_SLAVE_ID)
    reader.connect()
    try:
        protection = reader.read_protection()
    finally:
        reader.close()

    assert protection["comm_ok"] is False
    assert protection["trips"] == 0


def test_an_open_device_reports_its_state_and_trip_counter(cihazlar):
    mpr_port, tvoc_port = cihazlar(tvoc_slave=10)

    reader = reader_for(mpr_port, tvoc_port)
    try:
        protection = reader.read_protection()
    finally:
        reader.close()

    assert protection["comm_ok"] is True
    assert protection["trips"] == 0


# ---------------------------------------------------------------- uctan uca


def published(lines: list[str]) -> list[dict]:
    return [json.loads(line.split(" ", 2)[2]) for line in lines if line.startswith("[panobeyni] gridup/")]


def run_shell(mpr_port: int, tvoc_port: int, *extra: str, messages: int = 2,
              period: str = "0.05") -> list[str]:
    proc = run_sim(
        "panobeyni_sim.py",
        "--mpr", f"127.0.0.1:{mpr_port}",
        "--tvoc", f"127.0.0.1:{tvoc_port}",
        "--period", period,
        "--report-every", "2",
        "--max-messages", str(messages),
        "--dry-run",
        *extra,
    )
    out, _ = proc.communicate(timeout=180)
    assert proc.returncode == 0, out
    return out.splitlines()


def test_measured_currents_reach_the_published_telemetry(cihazlar):
    """Elektriksel alanlar UYDURULMAZ: MQTT'ye giden deger Modbus'tan okunandir."""
    mpr_port, tvoc_port = cihazlar(tvoc_slave=10)

    lines = run_shell(mpr_port, tvoc_port, "--tvoc-unit", "10")
    payloads = published(lines)

    assert payloads, "\n".join(lines[-15:])
    reader = reader_for(mpr_port, tvoc_port)
    try:
        elec = reader.read_electrical()
    finally:
        reader.close()
    # Yuk zamanla degisir; buyukluk mertebesi ayni olmali (uydurma bir sabit degil).
    yayinlanan = max(payloads[-1]["elec"]["i_ph"])
    okunan = max(elec["i_ph"])
    assert abs(yayinlanan - okunan) < max(50.0, okunan * 0.25), (yayinlanan, okunan)


def test_a_real_arc_trip_over_modbus_becomes_an_alarm_in_the_payload(cihazlar):
    """--trip-after ile uretilen GERCEK trip, MQTT yukunde ALM-ARC-TRIP'e donusur.

    Bu tam olarak 14 Eylul'e kadar mumkun olmayan seydi: cihaz duzeyindeki olay
    Modbus'ta goruluyordu ama hicbir yere akmiyordu.

    Trip, kabuk OKUMAYA BASLADIKTAN SONRA olmali: ALM-ARC-TRIP sayacin DEGISIMINDEN
    cikar (limits.py:272-276). Kabuk baglandiginda sayac zaten 1 ise bu yeni bir olay
    degildir ve dogru olarak alarm uretilmez.
    """
    mpr_port, tvoc_port = cihazlar(tvoc_slave=10, trip_after=6.0)

    lines = run_shell(mpr_port, tvoc_port, "--tvoc-unit", "10", messages=60, period="0.1")
    payloads = published(lines)

    trips = [p["tvoc"]["trips"] for p in payloads]
    assert trips[0] == 0, f"trip kabuk baslamadan once olmus; test gecisi gozlemleyemez: {trips[:5]}"
    assert max(trips) >= 1, f"trip sayaci hic artmadi: {trips}"
    kodlar = {code for p in payloads for code in p["alarms"]}
    assert "ALM-ARC-TRIP" in kodlar, f"ark tripi alarma donusmedi; cikanlar: {kodlar}"


def test_a_failed_detector_reaches_the_payload_as_protection_health_loss(cihazlar):
    """--sensor-error: TVOC-2 hata biti -> prot_health_ok=False -> ALM-PROT-HEALTH."""
    mpr_port, tvoc_port = cihazlar(tvoc_slave=10, sensor_error=True)

    lines = run_shell(mpr_port, tvoc_port, "--tvoc-unit", "10", messages=3)
    payloads = published(lines)

    assert payloads
    assert payloads[-1]["tvoc"]["prot_health_ok"] is False
    assert "ALM-PROT-HEALTH" in payloads[-1]["alarms"]


def test_published_messages_match_the_frozen_telemetry_contract(cihazlar, ):
    """Sozlesme kapisi: gecersiz mesaj yayinlanmaz (Publisher panosim ile ortak)."""
    from jsonschema import Draft202012Validator

    from helpers import CONTRACTS_DIR

    mpr_port, tvoc_port = cihazlar(tvoc_slave=10)
    schema = json.loads((CONTRACTS_DIR / "mqtt-telemetry.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    payloads = published(run_shell(mpr_port, tvoc_port, "--tvoc-unit", "10", messages=3))

    assert payloads
    for payload in payloads:
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
        assert not errors, [e.message for e in errors[:3]]


# ---------------------------------------------------------------- halka tampon


def test_the_ring_buffer_drops_the_oldest_and_counts_it():
    ring = RingBuffer(capacity=3)

    for n in range(5):
        ring.add({"seq": n})

    assert len(ring) == 3
    assert ring.dropped == 2
    kalan = []
    ring.drain(lambda p: kalan.append(p) or True)
    assert [p["seq"] for p in kalan] == [2, 3, 4], "en eski dusurulmeli, en yeni kalmali"


def test_the_ring_buffer_keeps_everything_when_sending_fails():
    """Broker yoksa hicbir sey kaybolmaz; sira bozulmaz."""
    ring = RingBuffer(capacity=10)
    for n in range(4):
        ring.add({"seq": n})

    assert ring.drain(lambda p: False) == 0
    assert len(ring) == 4

    gonderilen = []
    assert ring.drain(lambda p: gonderilen.append(p) or True) == 4
    assert [p["seq"] for p in gonderilen] == [0, 1, 2, 3]
    assert len(ring) == 0


def test_the_ring_buffer_stops_at_the_first_failure_and_keeps_the_rest():
    ring = RingBuffer(capacity=10)
    for n in range(4):
        ring.add({"seq": n})

    ring.drain(lambda p: p["seq"] < 2)

    assert len(ring) == 2, "basarisiz olan ve sonrasi tamponda kalmali"


def test_a_device_can_be_switched_off_with_yok():
    assert _target("yok") is None
    assert _target("localhost:5020") == ("localhost", 5020)
    with pytest.raises(SystemExit):
        _target("bozuk")
