"""Ciy noktasi esik taramasi (F-06) — scripts/threshold_sweep.py.

Beklenen degerlerin kaynagi:
  - Esikler: contracts/alarm-codes.yaml `dew_margin_warn_k` / `dew_margin_alarm_k`
    (DONMUS; bu is esigi DEGISTIRMEZ, yalnizca savunur veya oneri acar).
  - Operator yuku siniri: ayni dosyadaki `alarms_per_operator_day_acceptable`.
  - Olay sayma semantigi: panoalgo/validate.py `_false_alarms` (kesintisiz aralik
    TEK alarm sayilir) — docs/12 §3 ile ayni sayiyi uretmek zorunda.

Testlerin ikinci isi kestirme yolu KILITLEMEKTIR: tarama, fixture'i her izgara
noktasinda yeniden uretmek yerine `td_margin_k` sutunu uzerinde karari yeniden
kosturuyor. Bu ancak ciy kodlari YALNIZCA o alana bakarsa gecerlidir; asagida hem
fixture'in hazir alarm sutunuyla hem de gercek yeniden kosturmayla karsilastirilir.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys

import pytest
import yaml

from helpers import CONTRACTS_DIR, REPO_ROOT

FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"


@pytest.fixture(scope="module")
def sweep():
    spec = importlib.util.spec_from_file_location(
        "threshold_sweep", REPO_ROOT / "scripts" / "threshold_sweep.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


@pytest.fixture(scope="module")
def healthy(sweep):
    return sweep.read_margins(FIXTURES_DIR, sweep.HEALTHY_SCENARIO)


@pytest.fixture(scope="module")
def condense(sweep):
    return sweep.read_margins(FIXTURES_DIR, sweep.CONDENSE_SCENARIO)


def _row(rows, threshold_k: float):
    return next(row for row in rows if row.threshold_k == threshold_k)


def _pair(pairs, warn_k: float, alarm_k: float):
    return next(p for p in pairs if (p.warn_k, p.alarm_k) == (warn_k, alarm_k))


# ------------------------------------------------------------------- sayaclar


def test_an_uninterrupted_stretch_counts_as_one_episode(sweep):
    assert sweep.count_episodes((True, True, True, True)) == 1


def test_every_rising_edge_starts_a_new_episode(sweep):
    assert sweep.count_episodes((True, False, True, False, True)) == 3


def test_an_always_quiet_series_has_no_episodes(sweep):
    assert sweep.count_episodes((False, False)) == 0


def test_longest_run_measures_the_longest_uninterrupted_stretch(sweep):
    assert sweep.longest_run((True, False, True, True, True, False)) == 3


def test_the_comparison_is_strictly_less_than(sweep):
    """limits._environment() `margin < esik` kullanir; tam esikteki deger alarm URETMEZ."""
    assert sweep.flags_below((3.0, 2.99), 3.0) == (False, True)


# --------------------------------------------- kestirme yolun sadakati (KRITIK)


def test_recomputing_from_the_margin_column_reproduces_the_fixture_alarm_column(sweep):
    """Tarama fixture'i yeniden uretmiyor; bu testin gecmesi onun kosulu."""
    checked, mismatched = sweep.verify_shortcut(
        FIXTURES_DIR, sweep.HEALTHY_SCENARIO, CONTRACTS_DIR
    )
    assert checked == 672
    assert mismatched == 0


def test_rerunning_the_detection_gives_the_same_numbers_as_the_shortcut(sweep):
    """Iki izgara noktasinda tespit GERCEKTEN yeniden kosturulur (uretec + kenar)."""
    grid = (0.0, 1.0)
    fast = [_row(sweep.sweep(sweep.read_margins(FIXTURES_DIR, sweep.HEALTHY_SCENARIO), grid), t)
            for t in grid]
    slow, seconds = sweep.rerun_grid(seed=1304, grid=grid, contracts_dir=CONTRACTS_DIR)
    assert seconds > 0.0
    assert [(r.episodes, r.duty_pct) for r in fast] == [(r.episodes, r.duty_pct) for r in slow]


def test_rerunning_never_touches_the_frozen_contract(sweep):
    """Yeniden kosturma contracts/ dizininin GECICI kopyasini yazar, aslini degil."""
    path = CONTRACTS_DIR / "alarm-codes.yaml"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    sweep.rerun_grid(seed=1304, grid=(2.0,), contracts_dir=CONTRACTS_DIR)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


# ------------------------------------------------------------ olculmus sonuclar


def test_the_contract_pair_reproduces_the_published_false_alarm_load(sweep, healthy, condense):
    """docs/12 §3: S0'da 71,4 yanlis alarm/100 pano/gun, tamami ALM-DEW-*."""
    thresholds = yaml.safe_load((CONTRACTS_DIR / "alarm-codes.yaml").read_text(encoding="utf-8"))[
        "thresholds"
    ]
    pair = _pair(
        sweep.sweep_pairs(healthy, condense),
        float(thresholds[sweep.WARN_KEY]),
        float(thresholds[sweep.ALARM_KEY]),
    )
    assert pair.per_100_panel_days == pytest.approx(71.4, abs=0.1)


def test_lowering_the_thresholds_makes_the_operator_load_worse(sweep, healthy, condense):
    """Taramanin ana bulgusu: esigi kismak olay sayisini AZALTMIYOR, artiriyor."""
    pairs = sweep.sweep_pairs(healthy, condense)
    contract = _pair(pairs, 3.0, 1.0)
    tighter = _pair(pairs, 1.0, 0.0)
    assert tighter.per_100_panel_days > contract.per_100_panel_days


def test_the_tightest_candidate_breaks_the_contract_acceptance_limit(sweep, healthy, condense):
    """1,0/0,0 cifti sozlesmenin kabul edilebilir gunluk alarm butcesini asiyor."""
    thresholds = yaml.safe_load((CONTRACTS_DIR / "alarm-codes.yaml").read_text(encoding="utf-8"))[
        "thresholds"
    ]
    limit = float(thresholds["alarms_per_operator_day_acceptable"])
    tighter = _pair(sweep.sweep_pairs(healthy, condense), 1.0, 0.0)
    assert tighter.per_100_panel_days > limit


def test_raising_the_threshold_leaves_the_warning_permanently_standing(sweep, healthy):
    """Esigi yukseltmek olay sayisini dusuruyor ama alarmi kalici olarak ayakta birakiyor."""
    rows = sweep.sweep(healthy)
    for threshold in (3.0, 4.0, 5.0, 6.0):
        row = _row(rows, threshold)
        assert row.duty_pct == 100.0
        assert row.stale, f"{threshold} K'de bayat alarm bekleniyordu"


def test_the_contract_warning_threshold_stands_for_the_whole_healthy_week(sweep, healthy):
    """Olculdu: 3,0 K esiginde uyari 168 saat boyunca kesintisiz ayakta (EEMUA 191 bayat)."""
    row = _row(sweep.sweep(healthy), 3.0)
    assert row.episodes == 1
    assert row.longest_run_h == pytest.approx(168.0)


def test_the_healthy_panel_is_below_the_dew_point_most_of_the_week(sweep, healthy):
    """Alarmlarin kaynagi esik degil hava: marj orneklerin %65,6'sinda NEGATIF."""
    negative = sweep.duty_pct(sweep.flags_below(healthy.margins, 0.0))
    assert negative == pytest.approx(65.6, abs=0.1)


def test_the_healthy_and_the_condensing_panel_overlap_in_margin(sweep, healthy, condense):
    """Ayirma esikle yapilamaz: saglikli panonun en dusuk marji yogusma senaryosuyla ayni."""
    assert min(healthy.margins) >= min(condense.margins)
    assert min(healthy.margins) <= max(condense.margins)


def test_the_contract_pair_sits_on_the_measured_efficient_frontier(sweep, healthy, condense):
    """Butcenin altinda kalan VE alarmi hala temizlenen adaylarin en dusuk yuku 71,4.

    Ayakta kalma %100 olan bir alarm hic temizlenmez, yani bilgi tasimaz (EEMUA 191
    bayat alarm); olay metrigi onu ucuz gosterdigi icin ayrica elenir.
    """
    thresholds = yaml.safe_load((CONTRACTS_DIR / "alarm-codes.yaml").read_text(encoding="utf-8"))[
        "thresholds"
    ]
    budget = float(thresholds["alarms_per_operator_day_acceptable"])
    usable = [
        p
        for p in sweep.sweep_pairs(healthy, condense)
        if p.per_100_panel_days <= budget and p.alarm_duty_pct < 100.0
    ]
    best = min(p.per_100_panel_days for p in usable)
    assert best == pytest.approx(71.4, abs=0.1)
    assert any((p.warn_k, p.alarm_k) == (3.0, 1.0) for p in usable
               if p.per_100_panel_days == pytest.approx(best, abs=0.1))


def test_the_same_healthy_panel_raises_no_dew_alarm_in_summer(sweep):
    """Surucu esik degil mevsim: yaz kosulunda ciy alarmi HIC cikmiyor (docs/05 §11.4)."""
    row = sweep.season_load(seed=1304, warn_k=3.0, alarm_k=1.0, contracts_dir=CONTRACTS_DIR,
                            seasons=("yaz",))[0]
    assert row.season == "yaz"
    assert row.warn_duty_pct == 0.0
    assert row.per_100_panel_days == 0.0
    assert row.min_margin_k > 3.0


def test_no_candidate_pair_loses_the_condensation_detection(sweep, healthy, condense):
    """Tespit hicbir adayda kaybolmuyor — enjekte edilen yogusma marji doyuruyor."""
    for pair in sweep.sweep_pairs(healthy, condense):
        assert pair.detects_condensation
        assert pair.detection_delay_h == pytest.approx(0.0)


# ------------------------------------------------------------- sozlesme kilidi


def test_the_dew_thresholds_in_the_contract_are_unchanged():
    """Bu is esigi SAVUNUR; degistirmek 17 Eylul'den sonra imkansiz (donmus sozlesme)."""
    thresholds = yaml.safe_load((CONTRACTS_DIR / "alarm-codes.yaml").read_text(encoding="utf-8"))[
        "thresholds"
    ]
    assert (thresholds["dew_margin_warn_k"], thresholds["dew_margin_alarm_k"]) == (3.0, 1.0)


def test_the_rendered_table_marks_the_contract_values(sweep, healthy, condense):
    report = sweep.render_markdown(
        healthy, condense, sweep.sweep(healthy), sweep.sweep_pairs(healthy, condense), 3.0, 1.0
    )
    assert "**(sozlesme: uyari)**" in report
    assert "**(sozlesme: alarm)**" in report
    assert "**(sozlesme)**" in report
