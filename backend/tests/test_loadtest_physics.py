"""TB3 Adim 4 (Y8) — yuk testinin FIZIK ureteci: panoalgo kutuphane olarak import edilir.

fleet.py 14 Eylul'e kadar "panoalgo uretecine gecis A'nin paketi geldiginde eklenecek"
notunu tasiyordu ve sablon yuk uretiyordu. Paket birlesmeyle geldi; bu dosya gecisin
gercekten yapildigini ve uretilen yukun sozlesmeye uydugunu olcer.

Olculen iddialar:
  1. Uretec A'nin paketinden gelir (kod kopyalanmadi).
  2. Uretilen her mesaj telemetri semasina uyar.
  3. Alarm enjeksiyonu FIZIKSELDIR: sicaklik isil modelle yukselir ve sabit 70 K
     siniri gercekten asilir (sablon uretec alani dogrudan yazardi).
  4. Enjeksiyon gunun saatinden BAGIMSIZ ve tekrarlanabilir: yuk profili gercek
     oldugu icin baglanti artisi 0,5 K ile 26 K arasinda degisiyor; enjekte edilen
     pano yukunu dondurur ve carpan K0*I^2'den hesaplanir.
  5. Uretilen alarm, merkezin risk motorunca aciklanabilir bir alarma donusur.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.ingest import IngestPipeline
from app.risk import RiskEngine
from fakes import MemoryStore
from helpers import encode, utc

from test_loadtest_fleet import T0, fleet, validator  # noqa: F401 - fixture'lar paylasilir

POINTS = 7
SEED = 20260913


@pytest.fixture
def factory(fleet, contracts):
    return fleet.PhysicsPayloadFactory(contracts, points=POINTS, seed=SEED)


def test_the_generator_comes_from_panoalgo_not_a_local_copy(factory):
    """Kod kopyalanmadi: uretilen simulator A'nin paketinden geliyor."""
    sim = factory._sim("SIM-00001")

    assert type(sim).__module__ == "panoalgo.generator"
    assert type(sim).__name__ == "PanelSimulator"


def test_every_message_matches_the_frozen_telemetry_contract(factory, validator):
    payloads = [factory.payload(f"SIM-{n:05d}", n, T0 + timedelta(seconds=10 * n)) for n in range(1, 13)]

    for payload in payloads:
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
        assert not errors, f"{payload['pano_id']}: {[e.message for e in errors[:3]]}"
        assert len(payload["t_conn"]) == POINTS
        assert payload["health"]["nodes_ok"] == POINTS + 2


def test_the_same_seed_gives_the_same_fleet(fleet, contracts):
    """Tekrarlanabilirlik: iki kosu ayni veriyi uretmeli (sablon uretecin garantisi korunur)."""
    first = fleet.PhysicsPayloadFactory(contracts, points=POINTS, seed=SEED)
    second = fleet.PhysicsPayloadFactory(contracts, points=POINTS, seed=SEED)
    # Kurulus duvar saatini baslangic olarak alir; karsilastirma icin esitlenir.
    second._start = first._start
    second._sims.clear()

    a = [first.payload("SIM-00007", n, T0) for n in range(5)]
    b = [second.payload("SIM-00007", n, T0) for n in range(5)]

    assert a == b


def test_a_quiet_panel_raises_nothing(factory):
    """Enjeksiyon yoksa alarm da yok — yanlis alarm tabani bozulmamali."""
    codes = set()
    for n in range(12):
        codes.update(factory.payload("SIM-00042", n, T0).get("alarms") or [])

    assert "ALM-THR-TERM-ALM" not in codes


def test_injection_pushes_the_temperature_over_the_fixed_limit(factory, contracts):
    """Sicaklik ISIL MODELLE yukselir; alani elle yazmiyoruz."""
    limit = float(contracts.thresholds["term_rise_alarm_k"])
    for n in range(4):
        before = factory.payload("SIM-00001", n, T0)
    assert before["t_conn"][1]["dt_c"] < limit, "enjeksiyon oncesi zaten sinirin ustunde"

    after = None
    for n in range(4, 12):
        after = factory.payload("SIM-00001", n, T0, alarm=(n == 4))

    assert after["t_conn"][1]["dt_c"] > limit
    assert factory.ALARM_CODE in after["alarms"]


@pytest.mark.parametrize("hour", [0, 4, 9, 13, 18, 22], ids=lambda h: f"saat{h:02d}")
def test_injection_works_at_every_hour_of_the_day(fleet, contracts, hour):
    """Sabit carpan gece yarisi siniri gecmezdi; dondurulmus yukte hesaplanan carpan her saatte geciyor."""
    made = fleet.PhysicsPayloadFactory(contracts, points=POINTS, seed=SEED)
    made._start = utc(2026, 9, 15, hour, 0, 0)
    made._sims.clear()

    for n in range(4):
        made.payload("SIM-00001", n, T0)
    last = None
    for n in range(4, 14):
        last = made.payload("SIM-00001", n, T0, alarm=(n == 4))

    assert made.ALARM_CODE in last["alarms"], (
        f"saat {hour:02d}: dt_c={last['t_conn'][1]['dt_c']:.1f} K, alarm cikmadi"
    )


def test_detection_can_be_limited_to_the_measured_panels(fleet, contracts):
    """--edge-all kapaliyken tespit yalnizca olculen panolarda kosar (CPU butcesi)."""
    limited = fleet.PhysicsPayloadFactory(contracts, points=POINTS, seed=SEED, edge_ids=["SIM-00001"])

    for n in range(4):
        watched = limited.payload("SIM-00001", n, T0)
        other = limited.payload("SIM-00002", n, T0)

    assert watched["alarms"] == [] or isinstance(watched["alarms"], list)
    assert other["alarms"] == [], "listede olmayan pano icin tespit kosmamali"


def test_the_injected_alarm_becomes_an_explained_console_alarm(factory, contracts):
    """Merkez, uretilen alarmi Neden/Ne yapmali/Ne kadar acil ile aciklayabilmeli."""
    for n in range(4):
        factory.payload("SIM-00001", n, T0)
    payload = None
    for n in range(4, 12):
        payload = factory.payload("SIM-00001", n, T0, alarm=(n == 4))

    store = MemoryStore()
    pipeline = IngestPipeline(contracts, store, clock=lambda: T0 + timedelta(seconds=2))
    pipeline.handle_message(f"gridup/pano/{payload['pano_id']}/tel", encode(payload))
    assert pipeline.flush()
    assert not store.quarantined, store.quarantined[:1]
    [batch] = store.batches
    [sample] = batch[0]

    conditions = RiskEngine(contracts).evaluate(sample)

    match = next(c for c in conditions if c.code == factory.ALARM_CODE)
    assert match.reason.get("signals"), "Neden? bolumu bos"
    assert match.point == "GIRIS_L2"


def test_the_two_generators_report_which_code_they_inject(fleet, contracts):
    """alarm_latencies dogru kodu sorgulayabilsin diye uretici kodu bildirir."""
    template = fleet.PayloadFactory(contracts, points=POINTS, seed=SEED)
    physics = fleet.PhysicsPayloadFactory(contracts, points=POINTS, seed=SEED)

    assert template.ALARM_CODE == "ALM-K-ALM"
    assert physics.ALARM_CODE == "ALM-THR-TERM-ALM"
    assert template.ALARM_CODE != physics.ALARM_CODE


def test_physics_is_the_default_generator(fleet):
    assert fleet.Config().generator == "physics"


def test_an_unknown_generator_name_is_rejected(fleet, contracts):
    with pytest.raises(ValueError, match="physics"):
        fleet.build_factory(fleet.Config(generator="yok"), contracts, [])
