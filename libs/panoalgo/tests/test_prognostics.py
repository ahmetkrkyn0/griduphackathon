"""Prognoz geri testi olcutleri (F-04) — panoalgo/prognostics.py.

Beklenen degerlerin kaynagi:
  - Olcut tanimlari: Saxena ve ark., "Metrics for Offline Evaluation of Prognostic
    Performance" (IJPHM 2010); alfa-lambda, prognostic horizon, goreli dogruluk ve
    yakinsama tanimlari oradan birebir alindi.
  - Gercek kalan omur: data/fixtures/*.labels.json icindeki `l0_breach_at` alani
    (contracts/scenario-labels.schema.json ile donmus).

Sentetik testler olcutun MATEMATIGINI kilitler (elle hesaplanabilir sayilar);
son bolumdeki fixture testleri docs/12 §4'teki SAYILARI kilitler — dokuman betikle
uretildigi icin tek koruma budur (PLAN.md kural: uretilen dokuman elle duzenlenmez).
"""

from __future__ import annotations

import pytest

from panoalgo import prognostics as pg

ALPHA = pg.DEFAULT_ALPHA


def _series(pairs: list[tuple[float, float, float]]) -> tuple[pg.Prediction, ...]:
    """(saat, gercek kalan omur, tahmin) uclulerinden tahmin dizisi."""
    return tuple(pg.Prediction(h, true_h, pred_h) for h, true_h, pred_h in pairs)


def _perfect(count: int = 10, step_h: float = 1.0) -> tuple[pg.Prediction, ...]:
    """Kusursuz tahmin: her anda gercek kalan omru birebir soyluyor."""
    total = count * step_h
    return _series([(i * step_h, total - i * step_h, total - i * step_h) for i in range(count)])


# ------------------------------------------------------------------------ koni


def test_alpha_band_is_symmetric_around_the_true_remaining_life():
    assert pg.alpha_band(100.0, 0.20) == (80.0, 120.0)


def test_alpha_band_rejects_a_non_positive_remaining_life():
    """RUL* <= 0'da oran tanimsizdir; sessizce 0 donmek olcumu yalanlar."""
    with pytest.raises(ValueError):
        pg.alpha_band(0.0, ALPHA)


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.5])
def test_alpha_band_rejects_an_out_of_range_cone_width(alpha):
    with pytest.raises(ValueError):
        pg.alpha_band(100.0, alpha)


@pytest.mark.parametrize("predicted", [80.0, 100.0, 120.0])
def test_cone_boundaries_count_as_inside(predicted):
    assert pg.in_alpha_band(100.0, predicted, 0.20)


@pytest.mark.parametrize("predicted", [79.9, 120.1])
def test_just_outside_the_cone_is_outside(predicted):
    assert not pg.in_alpha_band(100.0, predicted, 0.20)


# -------------------------------------------------------------- goreli dogruluk


def test_relative_accuracy_is_one_for_an_exact_prediction():
    assert pg.relative_accuracy(50.0, 50.0) == 1.0


def test_relative_accuracy_is_zero_when_the_error_equals_the_true_life():
    assert pg.relative_accuracy(50.0, 100.0) == 0.0


def test_relative_accuracy_stays_negative_and_is_not_clipped():
    """Kirpma, iki kat hata ile yirmi kat hatayi ayni gosterirdi (modul notu)."""
    assert pg.relative_accuracy(10.0, 210.0) == pytest.approx(-19.0)


def test_relative_accuracy_rejects_a_non_positive_remaining_life():
    with pytest.raises(ValueError):
        pg.relative_accuracy(-1.0, 10.0)


# ------------------------------------------------------------------------ ufuk


def test_horizon_of_a_perfect_prediction_is_the_whole_window():
    predictions = _perfect(count=10, step_h=1.0)
    assert pg.prognostic_horizon(predictions, ALPHA) == predictions[0].rul_true_h


def test_horizon_starts_where_the_prediction_stops_leaving_the_cone():
    # Ilk iki tahmin konidan disarida, sonraki ucu icinde: ufuk ucuncu tahminin
    # gercek kalan omru, yani ihlalden 30 saat once.
    predictions = _series(
        [(0.0, 50.0, 500.0), (10.0, 40.0, 400.0), (20.0, 30.0, 30.0), (30.0, 20.0, 21.0), (40.0, 10.0, 9.0)]
    )
    assert pg.prognostic_horizon(predictions, ALPHA) == 30.0


def test_horizon_is_none_when_the_last_prediction_is_outside_the_cone():
    """None ile 0 ayri seydir: 0 'tam ihlal aninda tuttu' demektir."""
    predictions = _series([(0.0, 50.0, 50.0), (10.0, 40.0, 40.0), (20.0, 30.0, 300.0)])
    assert pg.prognostic_horizon(predictions, ALPHA) is None


def test_horizon_of_an_empty_series_is_none():
    assert pg.prognostic_horizon((), ALPHA) is None


# ------------------------------------------------------------------ alfa-lambda


def test_alpha_lambda_reports_one_point_per_requested_fraction():
    points = pg.alpha_lambda(_perfect(count=20), ALPHA, (0.25, 0.50, 0.75))
    assert [p.lam for p in points] == [0.25, 0.50, 0.75]


def test_alpha_lambda_picks_the_sample_nearest_to_the_lambda_instant():
    # Ilk tahmin t=0, RUL* = 100 h; lambda 0.5 -> t = 50 h. En yakin ornek 48 h'tir.
    predictions = _series([(0.0, 100.0, 100.0), (48.0, 52.0, 52.0), (96.0, 4.0, 4.0)])
    point = pg.alpha_lambda(predictions, ALPHA, (0.5,))[0]
    assert point.hours_from_start == 48.0


def test_alpha_lambda_marks_a_point_outside_the_cone():
    predictions = _series([(0.0, 100.0, 100.0), (50.0, 50.0, 500.0)])
    point = pg.alpha_lambda(predictions, ALPHA, (0.5,))[0]
    assert not point.in_band
    assert point.relative_accuracy == pytest.approx(-8.0)


def test_alpha_lambda_of_an_empty_series_is_empty():
    assert pg.alpha_lambda((), ALPHA) == ()


# -------------------------------------------------------------------- yakinsama


def test_convergence_of_a_perfect_prediction_is_zero():
    assert pg.convergence(_perfect()) == (0.0, 0.0)


def test_convergence_needs_at_least_two_predictions():
    assert pg.convergence(_perfect(count=1)) == (None, None)


def test_error_that_shrinks_puts_the_centroid_in_the_first_half():
    predictions = _series([(0.0, 100.0, 400.0), (25.0, 75.0, 150.0), (50.0, 50.0, 55.0), (75.0, 25.0, 25.0)])
    _, fraction = pg.convergence(predictions)
    assert fraction is not None and fraction < 0.5


def test_error_that_grows_puts_the_centroid_in_the_second_half():
    predictions = _series([(0.0, 100.0, 100.0), (25.0, 75.0, 80.0), (50.0, 50.0, 200.0), (75.0, 25.0, 600.0)])
    _, fraction = pg.convergence(predictions)
    assert fraction is not None and fraction > 0.5


# ----------------------------------------------------------------------- kovalar


def test_buckets_partition_every_prediction_exactly_once():
    predictions = _series([(float(i), float(i + 1) * 20.0, 10.0) for i in range(30)])
    buckets = pg.rul_buckets(predictions, ALPHA)
    assert sum(b.count for b in buckets) == len(predictions)


def test_bucket_edges_come_from_the_module_defaults():
    buckets = pg.rul_buckets(_perfect(count=5), ALPHA)
    assert [b.low_h for b in buckets] == [0.0, *pg.DEFAULT_BUCKET_EDGES_H]
    assert buckets[-1].high_h is None


def test_an_empty_bucket_reports_zero_instead_of_raising():
    # Tum tahminler 0-12 h kovasina duser; ust kovalar bos kalir.
    predictions = _series([(0.0, 10.0, 10.0), (1.0, 9.0, 9.0)])
    buckets = pg.rul_buckets(predictions, ALPHA)
    assert buckets[0].count == 2
    assert all(b.count == 0 for b in buckets[1:])


def test_a_perfect_prediction_stays_inside_the_cone_in_every_bucket():
    buckets = pg.rul_buckets(_perfect(count=40, step_h=10.0), ALPHA)
    assert all(b.in_band_ratio == 1.0 for b in buckets if b.count)


# ------------------------------------------------------------------ seri kurma


def test_series_skips_samples_without_a_prediction():
    points, late = pg.predictions_from_series([0.0, 1.0, 2.0], [None, 5.0, None], eol_hours=10.0)
    assert len(points) == 1
    assert points[0].hours_from_start == 1.0
    assert late == 0


def test_predictions_after_the_breach_are_counted_but_not_scored():
    """Ihlalden sonra gercek kalan omur negatiftir; oran tanimsiz, sayim anlamli."""
    points, late = pg.predictions_from_series([0.0, 5.0, 10.0], [8.0, 3.0, 2.0], eol_hours=5.0)
    assert len(points) == 1
    assert late == 2


def test_series_of_different_lengths_is_rejected():
    with pytest.raises(ValueError):
        pg.predictions_from_series([0.0, 1.0], [1.0], eol_hours=5.0)


# ------------------------------------------------------------------- geri test


def test_backtest_of_an_empty_series_is_none():
    assert pg.backtest("S_test", ()) is None


def test_backtest_of_a_perfect_prediction_scores_perfectly():
    result = pg.backtest("S_test", _perfect(count=20, step_h=5.0))
    assert result is not None
    assert result.in_band_ratio == 1.0
    assert result.cumulative_relative_accuracy == 1.0
    assert result.median_ratio == 1.0
    assert result.horizon_h == result.first_prediction_h
    assert result.convergence_h == 0.0


def test_backtest_carries_the_late_prediction_count_through():
    result = pg.backtest("S_test", _perfect(), late_count=7)
    assert result is not None and result.late_count == 7


# -------------------------------------------------- fixture: docs/12 §4 sayilari


@pytest.fixture(scope="module")
def measured():
    """data/fixtures uzerinde olculmus sonuclar (docs/12 bu listeden uretilir)."""
    from panoalgo.validate import validate_all

    from helpers import REPO_ROOT

    return {r.scenario_id: r for r in validate_all(REPO_ROOT / "data" / "fixtures")}


def test_only_the_loose_connection_trajectory_can_be_backtested(measured):
    """n = 1 durustluk kaydi: geri testi yapilabilen TEK yorunge var."""
    scored = [r.scenario_id for r in measured.values() if r.prognosis is not None]
    assert scored == ["S1_loose_conn"]


def test_the_overload_scenario_breaches_the_limit_without_any_prediction(measured):
    """S2'de sinir asiliyor ama ttl uretilmiyor — prognoz olcumu yapilamaz."""
    result = measured["S2_overload"]
    assert result.l0_breach_at is not None
    assert result.prognosis is None


def test_the_sensor_fault_scenario_produces_prognoses_without_any_breach(measured):
    """PROGNOZ YANLIS-ALARMI: sinir hic asilmadi, 183 tahmin uretildi (docs/12 §4.3).

    Bunlarin 86'si ALM-TTL-14D alarmina donuyor ve etiket penceresinin ICINDE
    ciktiklari icin docs/12 §3'teki yanlis alarm sayaci onlari gormuyor.

    SAYILAR 18 EYLUL'DE DEGISTI (99/89 -> 183/86), CUNKU URETEC DUZELDI (F-31):
    `set_sensor_fault` ayni arizayi her cagrida yeniden kuruyor ve yasi SIFIRLIYORDU;
    senaryo yurutucusu `_inject`'i her adimda cagirdigi icin "suruklenme" 112 saatlik
    enjeksiyon penceresi boyunca 0,5 K'da (tek adimlik) cakili kaliyordu. Yani depo
    "sensor suruklenmesi uretiyoruz" diyordu ama fiilen URETMIYORDU. Duzeltme sonrasi
    kayma gercekten birikiyor ve yanlis-alarm daha buyuk cikiyor.
    """
    result = measured["S8_sensor_fault"]
    assert result.l0_breach_at is None
    assert result.false_prognoses == 183
    assert result.false_prognosis_alarms == 86


def test_a_healthy_panel_produces_no_prognosis_at_all(measured):
    assert measured["S0_normal"].false_prognoses == 0


def test_the_measured_trajectory_never_stays_inside_the_cone(measured):
    """Olculmus sonuc: ufuk YOK ve koni icinde kalma orani %10'un altinda."""
    prognosis = measured["S1_loose_conn"].prognosis
    assert prognosis is not None
    assert prognosis.horizon_h is None
    assert prognosis.in_band_ratio < 0.10


def test_the_prediction_does_not_improve_as_the_breach_approaches(measured):
    """Son iki kova (48 h alti) koni icinde HIC kalmiyor — yakinsama yok."""
    prognosis = measured["S1_loose_conn"].prognosis
    assert prognosis is not None
    near = [b for b in prognosis.buckets if b.count and b.high_h is not None and b.high_h <= 48.0]
    assert near, "48 h altinda tahmin bulunamadi"
    assert all(b.in_band_ratio == 0.0 for b in near)


# ------------------------------------------------- docs/12 yeniden uretim testi


def test_docs_12_matches_what_the_generator_produces_now(measured):
    """docs/12 ELLE DUZENLENMEZ: diskteki dosya ureteci ile birebir ayni olmali.

    Uretim zamani satiri her kosuda degisir, karsilastirmadan cikarilir.
    """
    from panoalgo.validate import render_markdown

    from helpers import REPO_ROOT

    def body(text: str) -> list[str]:
        return [line for line in text.splitlines() if not line.startswith("Uretim zamani:")]

    on_disk = (REPO_ROOT / "docs" / "12-dogrulama-sonuclari.md").read_text(encoding="utf-8")
    generated = render_markdown(sorted(measured.values(), key=lambda r: r.scenario_id))
    assert body(on_disk) == body(generated), (
        "docs/12 guncel degil: python scripts/validate.py --out docs/12-dogrulama-sonuclari.md"
    )


def test_the_generated_report_has_the_prognosis_section(measured):
    from panoalgo.validate import render_markdown

    rendered = render_markdown(sorted(measured.values(), key=lambda r: r.scenario_id))
    assert "## 4. Prognoz geri testi" in rendered
    # §1-§3 yerinde kalmali: docs/10 §1'e, juri kartlari §3'e atif veriyor.
    assert "## 3. Yanlis alarm yuku" in rendered
    assert "## 5. Nasil yeniden uretilir" in rendered
