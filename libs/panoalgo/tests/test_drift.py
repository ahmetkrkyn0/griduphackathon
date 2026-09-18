"""Yuk bagimsiz kayma (ALM-DQ-DRIFT, F-31) testleri — panoalgo/quality.py.

Kuralin tamami su fizige dayanir:

    dT = a * I^2 + b        fizik b = 0 der (yuk yoksa isinma yok)

  - BAGLANTI bozulursa `a` buyur, `b` sifirda kalir (dT her yukte ORANTILI artar).
  - SENSOR kayarsa `b` buyur, `a` degismez (dT yuk dusse bile dusmez).

Bu dosya once kurali sentetik (I^2, dT) serileriyle tek tek sinar, sonra ONEMLI OLANI
olcer: gercek bir gevsek baglanti (S1) ile kayan bir sensor (S8) birbirinden ayriliyor
mu? Bir gercek arizayi "kalibrasyon supheli" diye raporlamak en kotu yanlis yondur.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from panoalgo.quality import QualityTracker, codes_from_bits
from panoalgo.scenarios import SCENARIOS, iter_samples, plan

START = datetime(2026, 9, 1, tzinfo=timezone.utc)
PERIOD = timedelta(minutes=15)
POINT = "GIRIS_L1"


def _sample(index: int, current_a: float, dt_c: float, ambient: float = 20.0) -> dict:
    """Kuralin okudugu asgari yuk: zaman, akim ve nokta basina dT."""
    return {
        "pano_id": "SIM-00001",
        "ts": (START + index * PERIOD).isoformat(),
        "elec": {"i_ph": [current_a, current_a, current_a], "i_n": current_a / 6.0},
        "env": {"t_low_c": ambient},
        "t_conn": [{"pt": POINT, "t_c": ambient + dt_c, "dt_c": dt_c, "q": 0}],
    }


def _load(index: int) -> float:
    """Gunluk yuk cevrimi: 96 ornek = 24 saat. Uyarim sarti icin gercek degisim sart."""
    import math

    return 300.0 + 250.0 * (1.0 + math.sin(2.0 * math.pi * index / 96.0))


def _run(count: int, dt_for, tracker: QualityTracker | None = None) -> list[list[str]]:
    """Kurali `count` ornek boyunca kosturur; her ornekteki kodlari doner."""
    tracker = tracker or QualityTracker()
    out = []
    for index in range(count):
        current = _load(index)
        out.append(tracker.check(_sample(index, current, dt_for(index, current))).get(POINT, []))
    return out


def _flagged(codes: list[list[str]]) -> int:
    return sum(1 for entry in codes if "ALM-DQ-DRIFT" in entry)


# ------------------------------------------------------------------ kural kendisi


def test_saglikli_nokta_isaretlenmez():
    """dT = a*I^2, b = 0 ve sabit. Kayma yok."""
    a = 1.0e-4
    assert _flagged(_run(500, lambda _i, cur: a * cur * cur)) == 0


def test_yukten_bagimsiz_kayma_isaretlenir():
    """Ayni a, ama olcume tekdüze buyuyen bir OFSET ekleniyor (sensor kaymasi).

    0,025 K/ornek = 0,1 K/saat: tek adimda 10 K/dk sicrama esiginin cok altinda,
    deger her ornekte degistigi icin donmus degil, yukari kaydigi icin ortam altinda
    degil. Yani mevcut dort L-1 kuralinin dordunden de kacar.
    """
    a = 1.0e-4
    codes = _run(500, lambda i, cur: a * cur * cur + 0.025 * i)
    assert _flagged(codes) > 0


def test_gercek_baglanti_bozulmasi_kayma_sayilmaz():
    """`a` buyuyor (isil direnc artiyor), `b` sifirda. Bu bir ARIZADIR, kayma degil.

    Kuralin en onemli ozelligi budur: gercek bozulmayi "kalibrasyon supheli" diye
    raporlamak operatoru gercek arizadan uzaklastirirdi.
    """
    codes = _run(500, lambda i, cur: (1.0e-4 * (1.0 + 2.0 * i / 500.0)) * cur * cur)
    assert _flagged(codes) == 0


def test_sabit_yukte_karar_verilmez():
    """I^2 degismezse a ile b birbirinden AYRILAMAZ (kotu kosullanma).

    Boyle bir pencerede "kayma yok" demek olcmedigimiz bir sey iddia etmek olurdu;
    kural karar VERMEZ (GK10).
    """
    tracker = QualityTracker()
    out = []
    for index in range(500):
        # Sabit akim: uyarim yok.
        out.append(tracker.check(_sample(index, 500.0, 5.0 + 0.025 * index)).get(POINT, []))
    assert _flagged(out) == 0


def test_kisa_gecici_sapma_isaretlenmez():
    """Tek seferlik bir yuk basamagi uydurmanin iki yarisini kisa sureligine ayirir.
    Sureklilik sarti (ardisik ornek) bunu eler; kalici bir kayma elenmez.
    """
    a = 1.0e-4

    def dt(index: int, cur: float) -> float:
        bump = 6.0 if 250 <= index < 258 else 0.0  # 8 ornek = sureklilik esiginin alti
        return a * cur * cur + bump

    assert _flagged(_run(500, dt)) == 0


def test_pencere_dolmadan_karar_verilmez():
    """Kayma SAATLER boyunca birikir; pencere dolmadan iddia uretilmez."""
    a = 1.0e-4
    codes = _run(100, lambda i, cur: a * cur * cur + 0.025 * i)
    assert _flagged(codes) == 0


def test_dt_alani_olmayan_nokta_patlatmaz():
    """Kestirim yayinlanmamis nokta (edge.py alanlari siler) kurali dusurmemeli."""
    tracker = QualityTracker()
    sample = _sample(0, 500.0, 5.0)
    del sample["t_conn"][0]["dt_c"]
    assert tracker.check(sample).get(POINT, []) == []


# ------------------------------------- senaryo duzeyinde ayrim (olculmus basari)


@pytest.mark.parametrize("scenario_id", sorted(SCENARIOS))
def test_kayma_yalnizca_kayan_sensorde_isaretlenir(scenario_id):
    """ON senaryonun HEPSI kosulur: yalnizca S8'in suruklenen noktasi isaretlenmeli.

    Olculdu (seed 42, 168 saat): S8_sensor_fault'ta DSYA4_L3 230 kez, enjeksiyondan
    26,25 saat sonra ilk kez. Diger dokuz senaryoda — GERCEK gevsek baglanti
    (S1_loose_conn) ve saglikli taban (S0_normal) dahil — SIFIR isaretleme.

    GK10: bu ayrim TEK bir yorungeden (n = 1) ve sentetik veriden gelir. Uretec
    kaymayi sabit hizli ve tek noktaya enjekte eder; gercek bir sensorun kaymasi
    duzensiz olabilir. Buradaki "kusursuz ayrim" saha basarimi DEGILDIR.
    """
    flagged: dict[str, int] = {}
    for sample in iter_samples(plan(scenario_id, seed=42, duration_h=168.0)):
        if sample.payload is None:
            continue
        for point in sample.payload["t_conn"]:
            if "ALM-DQ-DRIFT" in codes_from_bits(point.get("q", 0)):
                flagged[point["pt"]] = flagged.get(point["pt"], 0) + 1

    if scenario_id == "S8_sensor_fault":
        assert set(flagged) == {"DSYA4_L3"}, f"beklenmeyen nokta: {sorted(flagged)}"
        assert flagged["DSYA4_L3"] > 100
    else:
        assert flagged == {}, f"{scenario_id} yanlis pozitif uretti: {flagged}"


def test_s8_de_uc_sensor_arizasi_birbirine_karismaz():
    """S8 uc ariza enjekte eder: DSYA6_L1 yerinden dusmus, DSYA5_L2 donmus,
    DSYA4_L3 kayiyor. Her biri KENDI koduyla teshis edilmeli — daha ozgul tani
    kazanir, aksi halde ayni noktaya iki kod birden asilirdi.
    """
    codes: dict[str, set[str]] = {}
    for sample in iter_samples(plan("S8_sensor_fault", seed=42, duration_h=168.0)):
        if sample.payload is None:
            continue
        for point in sample.payload["t_conn"]:
            found = {c for c in codes_from_bits(point.get("q", 0)) if c.startswith("ALM-DQ-")}
            if found:
                codes.setdefault(point["pt"], set()).update(found)

    assert codes.get("DSYA6_L1") == {"ALM-DQ-BELOW-AMBIENT"}
    assert codes.get("DSYA5_L2") == {"ALM-DQ-FROZEN"}
    assert codes.get("DSYA4_L3") == {"ALM-DQ-DRIFT"}
