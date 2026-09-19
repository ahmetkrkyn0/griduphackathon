"""Uyarlanabilir raporlama kapisi (F-36).

Bu dosyanin EN ONEMLI testleri "tespit periyodu" baslikli olanlardir: maddenin
sessizce yanlis yapilabilecegi tek yer, yayin seyreltmesinin ORNEKLEME periyoduna
sizmasidir. Sizarsa unutma faktorunun etkin hafizasi ve K kestirimi bozulur
(docs/05 §3.3) ve 209 saatlik one alma iddiasi cokerdi.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

import pytest

from panoalgo.detect import load_thresholds
from panoalgo.edge import EdgePipeline
from panoalgo.generator import PanelSimulator, default_contracts_dir
from panoalgo.reporting import (
    DEADBAND_FRACTION,
    DEFAULT_MAX_SILENCE_S,
    SILENCE_SAFETY_FRACTION,
    PolicyError,
    ReportGate,
    ReportPolicy,
    deadband_fields,
    deadband_for,
)

START = datetime(2026, 4, 6, tzinfo=timezone.utc)
PERIOD_S = 10.0


@pytest.fixture
def contracts_dir():
    return default_contracts_dir()


def _sim(contracts_dir, seed: int = 7):
    return PanelSimulator(pano_id="SIM-00001", seed=seed, profile="karma",
                          start=START, contracts_dir=contracts_dir)


def _stream(contracts_dir, turlar: int, seed: int = 7, dondur: int | None = None):
    """Gercek fizik uretecini TESPIT periyoduyla adimlar ve zengin yukleri verir."""
    sim = _sim(contracts_dir, seed)
    pipeline = EdgePipeline(profile="karma", contracts_dir=contracts_dir, period_s=PERIOD_S)
    for tur in range(turlar):
        if dondur is not None and tur == dondur and not pipeline.baseline_frozen:
            pipeline.freeze_baselines()
        yield tur, copy.deepcopy(pipeline.process(sim.step(PERIOD_S)))


# ---------------------------------------------------------------- tespit periyodu


def test_the_gate_sees_every_sample_even_the_ones_it_suppresses(contracts_dir):
    """Kapi BASTIRDIGI ornegi de gorur; yani yayin karari isleme ritmine bagli degil.

    DIKKAT - bu test ne kanitlar ne kanitlamaz: kapinin her ornegi GORDUGUNU
    kanitlar, uretim kodunun process()'i kosulsuz cagirdigini KANITLAMAZ (o,
    sim/tests/test_uyarlanabilir_raporlama.py'de gercek kabuk kosturularak
    olculur: tarama sayisi mesaj sayisindan bagimsiz buyur).
    """
    turlar = 200
    sim = _sim(contracts_dir)
    pipeline = EdgePipeline(profile="karma", contracts_dir=contracts_dir, period_s=PERIOD_S)
    gate = ReportGate(ReportPolicy.from_contracts(contracts_dir))
    for tur in range(turlar):
        gate.decide(pipeline.process(sim.step(PERIOD_S)), tur * PERIOD_S)

    assert gate.decided == turlar
    assert gate.suppressed > 0, "bu akista hic bastirma olmadi; test ayirt edici degil"
    assert gate.published + gate.suppressed == turlar
    assert pipeline.period_mismatch == {}


def test_processing_at_the_declared_period_reports_no_mismatch(contracts_dir):
    """Ritim beyan edildigi gibiyse sayac bos kalir (yanlis alarm uretmez)."""
    sim = _sim(contracts_dir)
    pipeline = EdgePipeline(profile="karma", contracts_dir=contracts_dir, period_s=PERIOD_S)
    for _ in range(50):
        pipeline.process(sim.step(PERIOD_S))
    assert pipeline.period_mismatch == {}


def test_thinning_the_processing_itself_is_caught(contracts_dir):
    """"Yayinlamiyorsak islemeye de gerek yok" sessiz kalamaz.

    Boru hattina beyan edilen periyottan SEYREK ornek verilirse (F-36'nin en
    dogal ve en yanlis optimizasyonu) sayac artar. Bu sayac olmasa RLS, 10 s'lik
    model katsayilariyla 60 s arayla gelen veriyi islemeye devam eder ve tau,
    k_slope ile unutma faktorunun etkin hafizasi sessizce kayardi.
    """
    sim = _sim(contracts_dir)
    pipeline = EdgePipeline(profile="karma", contracts_dir=contracts_dir, period_s=PERIOD_S)
    for tur in range(60):
        payload = sim.step(PERIOD_S)
        if tur % 6:          # yalnizca her 6. ornegi isle: 10 s beyan, 60 s gercek
            continue
        pipeline.process(payload)
    assert pipeline.period_mismatch, "seyreltilmis isleme fark edilmedi"


def test_the_panobeyni_style_declaration_gap_is_visible_not_silent(contracts_dir):
    """`sim/panobeyni_sim.py`nin beyan/gercek sapmasi OLCULEBILIR hale geldi.

    O kabuk 1 s'de bir isler ama periyodu 10 s beyan eder (period x report_every).
    Bu sapma F-36'DAN ONCE de vardi ve madde bilincli olarak DOKUNMADI: duzeltmek
    yayinlanan tau_s/ttl_h degerlerini degistirir, yani ayri bir maddedir. Test
    sapmanin varligini kayda geciriyor ki "sessiz" olmaktan ciksin; sayac
    sifirlanirsa da bu test duser ve durum yeniden degerlendirilir.
    """
    sim = _sim(contracts_dir)
    pipeline = EdgePipeline(profile="karma", contracts_dir=contracts_dir, period_s=10.0)
    for _ in range(30):
        pipeline.process(sim.step(1.0))
    assert pipeline.period_mismatch, "beyan/gercek sapmasi gorunmez kaldi"


def test_a_derived_period_never_reports_a_mismatch(contracts_dir):
    """Periyot damgalardan turetiliyorsa beyan yoktur, dolayisiyla kayma da yoktur."""
    sim = _sim(contracts_dir)
    pipeline = EdgePipeline(profile="karma", contracts_dir=contracts_dir)
    for _ in range(30):
        pipeline.process(sim.step(PERIOD_S))
    assert pipeline.period_mismatch == {}


def test_the_gate_never_mutates_the_payload(contracts_dir):
    """Kapi salt okunurdur: yuke dokunursa tespit ile yayin ayrimi kaybolur."""
    gate = ReportGate(ReportPolicy.from_contracts(contracts_dir))
    for tur, payload in _stream(contracts_dir, 30):
        onceki = copy.deepcopy(payload)
        gate.decide(payload, tur * PERIOD_S)
        assert payload == onceki, f"kapi yuku degistirdi (tur {tur})"


def test_the_estimated_k_is_identical_with_and_without_the_gate(contracts_dir):
    """Kapi K kestirimine DOKUNMAZ: ayni tohumla K/tau serisi birebir ayni cikar."""
    seriler = []
    for policy in (ReportPolicy.passthrough(), ReportPolicy.from_contracts(contracts_dir)):
        sim = _sim(contracts_dir)
        pipeline = EdgePipeline(profile="karma", contracts_dir=contracts_dir, period_s=PERIOD_S)
        gate = ReportGate(policy)
        seri = []
        for tur in range(150):
            payload = pipeline.process(sim.step(PERIOD_S))
            gate.decide(payload, tur * PERIOD_S)
            nokta = payload["t_conn"][0]
            seri.append((nokta.get("k"), nokta.get("tau_s")))
        seriler.append(seri)
    assert seriler[0] == seriler[1]


# ---------------------------------------------------------------- olu bant sozu


def test_zero_order_hold_error_stays_within_the_deadband(contracts_dir):
    """Olu bandin verdigi soz OLCULUR: yayinlanmayan ornekler sifirinci derece
    tutmayla geri kurulursa hata hicbir alanda olu bandi asmaz.
    """
    policy = ReportPolicy.from_contracts(contracts_dir)
    gate = ReportGate(policy)
    son_yayin: dict[str, float] = {}
    asim: list[tuple[str, float, float]] = []

    for tur, payload in _stream(contracts_dir, 400, dondur=120):
        simdi = deadband_fields(payload)
        if gate.decide(payload, tur * PERIOD_S).publish:
            son_yayin = simdi
            continue
        for anahtar, deger in simdi.items():
            if anahtar not in son_yayin:
                continue
            hata = abs(deger - son_yayin[anahtar])
            band = deadband_for(policy, anahtar)
            if hata > band + 1e-9:
                asim.append((anahtar, hata, band))

    assert not asim, f"geri kurma hatasi olu bandi asti: {asim[:5]}"


def test_a_change_in_the_alarm_set_publishes_immediately(contracts_dir):
    """Alarm kumesi degisti mi olu bant SUSTURAMAZ; hem belirme hem kalkma."""
    gate = ReportGate(ReportPolicy.from_contracts(contracts_dir))
    _, taban = next(_stream(contracts_dir, 1))
    gate.decide(taban, 0.0)

    alarmli = copy.deepcopy(taban)
    alarmli["alarms"] = ["ALM-ARC-TRIP"]
    karar = gate.decide(alarmli, 1.0)
    assert karar.publish and karar.reason == "olay" and "alarms" in karar.detail

    temiz = copy.deepcopy(taban)
    temiz["alarms"] = []
    karar = gate.decide(temiz, 2.0)
    assert karar.publish and karar.reason == "olay", "alarmin KALKMASI da olaydir"


@pytest.mark.parametrize(
    "yol, deger",
    [
        (("risk", "mode"), "acil"),
        (("tvoc", "comm_ok"), False),
        (("tvoc", "prot_health_ok"), False),
        (("tvoc", "trips"), 99),
        (("health", "nodes_ok"), 1),
    ],
)
def test_a_state_change_publishes_immediately(contracts_dir, yol, deger):
    """Sayisal bir olu bant bir DURUM degisimini gizleyemez."""
    gate = ReportGate(ReportPolicy.from_contracts(contracts_dir))
    _, taban = next(_stream(contracts_dir, 1))
    taban.setdefault("tvoc", {"comm_ok": True, "prot_health_ok": True, "state": 0, "trips": 0})
    gate.decide(taban, 0.0)

    degisen = copy.deepcopy(taban)
    blok, alan = yol
    degisen.setdefault(blok, {})[alan] = deger
    karar = gate.decide(degisen, 1.0)
    assert karar.publish and karar.reason == "olay", f"{blok}.{alan} degisimi bastirildi"


def test_a_quality_bit_change_publishes_immediately(contracts_dir):
    """Veri kalitesi bitleri karar bilgisidir; sessizce eskitilemez."""
    gate = ReportGate(ReportPolicy.from_contracts(contracts_dir))
    _, taban = next(_stream(contracts_dir, 1))
    gate.decide(taban, 0.0)

    degisen = copy.deepcopy(taban)
    degisen["t_conn"][0]["q"] = (degisen["t_conn"][0].get("q") or 0) ^ 0x8000
    assert gate.decide(degisen, 1.0).reason == "olay"


def test_an_unchanged_payload_is_suppressed_until_the_heartbeat(contracts_dir):
    """Hicbir sey degismiyorsa yayin susar, azami sessizlikte geri gelir."""
    policy = ReportPolicy.from_contracts(contracts_dir)
    gate = ReportGate(policy)
    _, taban = next(_stream(contracts_dir, 1))

    assert gate.decide(copy.deepcopy(taban), 0.0).reason == "ilk"
    for saniye in (10.0, 20.0, 30.0, 40.0, 50.0):
        assert not gate.decide(copy.deepcopy(taban), saniye).publish

    karar = gate.decide(copy.deepcopy(taban), policy.max_silence_s)
    assert karar.publish and karar.reason == "sessizlik"


def test_a_drift_smaller_than_the_deadband_still_publishes_before_the_heartbeat(contracts_dir):
    """Surunme son YAYINLANAN degere gore olculur: tur basina kucuk adimlar birikir."""
    policy = ReportPolicy.from_contracts(contracts_dir)
    gate = ReportGate(policy)
    _, taban = next(_stream(contracts_dir, 1))
    gate.decide(copy.deepcopy(taban), 0.0)

    adim = policy.dt_c_k / 4.0
    yayin = 0
    for n in range(1, 6):
        surunen = copy.deepcopy(taban)
        for nokta in surunen["t_conn"]:
            nokta["dt_c"] += adim * n
        if gate.decide(surunen, n * 1.0).publish:
            yayin += 1
    assert yayin >= 1, "surunme hicbir zaman yayin tetiklemedi (fotograf her turda guncelleniyor olmali degil)"


# ---------------------------------------------------------------- sozlesme bagi


def test_the_max_silence_cannot_enter_the_centres_comms_lost_window(contracts_dir):
    """Merkez heartbeat_timeout_min sonunda ALM-COMMS-LOST yazar (F-22 bunu kesintiye toplar).

    Uyarlanabilir raporlama o pencereye GIREMEZ; kapi kurulurken reddeder.
    """
    heartbeat_s = float(load_thresholds(contracts_dir)["heartbeat_timeout_min"]) * 60.0
    sinir = heartbeat_s * SILENCE_SAFETY_FRACTION

    ReportPolicy.from_contracts(contracts_dir, max_silence_s=sinir)  # tam sinir: gecer
    with pytest.raises(PolicyError, match="kesinti sanilir"):
        ReportPolicy.from_contracts(contracts_dir, max_silence_s=sinir + 1.0)
    with pytest.raises(PolicyError, match="kesinti sanilir"):
        ReportPolicy.from_contracts(contracts_dir, max_silence_s=heartbeat_s)


def test_the_default_max_silence_is_well_inside_the_contract_window(contracts_dir):
    heartbeat_s = float(load_thresholds(contracts_dir)["heartbeat_timeout_min"]) * 60.0
    assert DEFAULT_MAX_SILENCE_S < heartbeat_s * SILENCE_SAFETY_FRACTION


def test_every_deadband_is_derived_from_a_contract_threshold(contracts_dir):
    """Hicbir olu bant koda gomulu bir sayi DEGILDIR (PLAN.md kural 10)."""
    thresholds = load_thresholds(contracts_dir)
    policy = ReportPolicy.from_contracts(contracts_dir)
    f = DEADBAND_FRACTION

    assert policy.dt_c_k == pytest.approx(f * thresholds["term_rise_warn_k"])
    assert policy.t_c_k == pytest.approx(f * thresholds["term_rise_warn_k"])
    assert policy.k_ratio == pytest.approx(f * (thresholds["k_ratio_warn"] - 1.0))
    assert policy.ttl_h == pytest.approx(f * thresholds["ttl_warn_days"] * 24.0)
    assert policy.current_a == pytest.approx(
        f * thresholds["current_warn_ratio"] * thresholds["rated_current_a"]["main_input"]
    )
    assert policy.thd_pct == pytest.approx(f * thresholds["neutral_thd_warn_pct"])
    assert policy.env_t_k == pytest.approx(f * thresholds["panel_temp_warn_c"])
    assert policy.td_margin_k == pytest.approx(f * thresholds["dew_margin_warn_k"])


def test_no_deadband_can_hide_the_gap_between_warning_and_alarm(contracts_dir):
    """Olu bant, uyari ile alarm esigi arasindaki mesafeden kucuk olmali.

    Aksi halde tek bir bastirilmis ornek panoyu uyaridan alarma atlatabilirdi.
    """
    thresholds = load_thresholds(contracts_dir)
    policy = ReportPolicy.from_contracts(contracts_dir)
    assert policy.dt_c_k < thresholds["term_rise_alarm_k"] - thresholds["term_rise_warn_k"]
    assert policy.k_ratio < thresholds["k_ratio_alarm"] - thresholds["k_ratio_warn"]
    assert policy.env_t_k < thresholds["panel_temp_alarm_c"] - thresholds["panel_temp_warn_c"]
    assert policy.td_margin_k < thresholds["dew_margin_warn_k"] - thresholds["dew_margin_alarm_k"]


def test_the_two_percentage_fields_without_a_contract_threshold_use_full_scale(contracts_dir):
    """rh ve vbak'in sozlesmede sayisal esigi YOKTUR; tam olcekten turetilirler.

    Bu iki alan "her olu bant sozlesmeden gelir" kuralinin BILINEN istisnasidir
    ve modul docstring'indeki tablo da boyle yazar. Test istisnayi acikca
    kayda geciriyor ki sessiz bir bosluk olarak kalmasin.
    """
    policy = ReportPolicy.from_contracts(contracts_dir)
    assert policy.rh_pct == pytest.approx(DEADBAND_FRACTION * 100.0)
    assert policy.vbak_pct == pytest.approx(DEADBAND_FRACTION * 100.0)


def test_an_unknown_field_gets_no_silent_fallback_deadband(contracts_dir):
    """Bilinmeyen alan SESSIZCE bir varsayilana dusmez, istisna atar.

    Dusseydi yuke ileride eklenecek bir gerilim alani akim bandini (41,6) miras
    alir ve pratikte hic yayinlanmazdi.
    """
    policy = ReportPolicy.from_contracts(contracts_dir)
    for anahtar in ("elec.u_ph.0", "env.uydurma", "t_conn.X.bilinmeyen", "tamamen.uydurma"):
        with pytest.raises(KeyError):
            deadband_for(policy, anahtar)


def test_the_discrete_states_the_centre_reads_are_events_not_deadbands(contracts_dir):
    """Kapi acilmasi ve bakim kipi AYRIKTIR: sayisal bir bant onlari gizleyemez."""
    gate = ReportGate(ReportPolicy.from_contracts(contracts_dir))
    _, taban = next(_stream(contracts_dir, 1))
    taban.setdefault("env", {})["door_open"] = False
    taban.setdefault("health", {})["maint_mode"] = False
    gate.decide(taban, 0.0)

    for blok, alan in (("env", "door_open"), ("health", "maint_mode")):
        degisen = copy.deepcopy(taban)
        degisen[blok][alan] = True
        karar = gate.decide(degisen, 1.0)
        assert karar.publish and karar.reason == "olay", f"{blok}.{alan} bastirildi"
        gate.decide(taban, 2.0)  # durumu geri al ki sonraki dongu temiz baslasin


def test_the_backup_energy_percentage_is_under_a_deadband(contracts_dir):
    """health.vbak_pct merkezde ALM-LASTGASP'in kanitidir; olu bant disinda kalamaz."""
    policy = ReportPolicy.from_contracts(contracts_dir)
    _, taban = next(_stream(contracts_dir, 1))
    taban.setdefault("health", {})["vbak_pct"] = 100.0
    assert "health.vbak_pct" in deadband_fields(taban)
    assert deadband_for(policy, "health.vbak_pct") == pytest.approx(policy.vbak_pct)


def test_an_invalid_fraction_is_refused(contracts_dir):
    for kesir in (0.0, 1.0, -0.1, 2.0):
        with pytest.raises(PolicyError):
            ReportPolicy.from_contracts(contracts_dir, fraction=kesir)


def test_the_default_policy_suppresses_nothing(contracts_dir):
    """Varsayilan saydamdir: bayrak verilmeden davranis DEGISMEZ."""
    gate = ReportGate()
    assert gate.policy.transparent
    for tur, payload in _stream(contracts_dir, 25):
        assert gate.decide(payload, tur * PERIOD_S).publish
    assert gate.suppressed == 0


# ---------------------------------------------------------------- alan kapsami


def test_every_alarm_driving_number_is_under_a_deadband(contracts_dir):
    """Alarm ureten her sayi olu banda tabi olmali.

    Aksi halde merkez, kenarin gordugu bir esik gecisini iki yayin arasinda
    kacirabilirdi (merkez ayni limits.evaluate'i yayinlanan yukten kosturur).
    """
    _, payload = next(_stream(contracts_dir, 1))
    alanlar = set(deadband_fields(payload))

    nokta = payload["t_conn"][0]["pt"]
    beklenen = {
        f"t_conn.{nokta}.dt_c", f"t_conn.{nokta}.t_c",
        "elec.i_ph.0", "elec.i_n", "elec.thd_i.0",
        "env.t_low_c", "env.t_up_c", "env.td_margin_k",
    }
    assert beklenen <= alanlar, f"olu bant disinda kalan alarm girdisi: {beklenen - alanlar}"
    for anahtar in alanlar:
        assert deadband_for(ReportPolicy.from_contracts(contracts_dir), anahtar) > 0.0
