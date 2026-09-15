"""L3 hipotez fuzyonu testleri — PLAN.md TA2 Adim 6.

Beklenen degerlerin kaynagi:
  - Hipotezler, kanit listeleri ve ciddiyet agirliklari contracts/alarm-codes.yaml
    `hypotheses` blogundan okunur; bu dosyada elle yazili agirlik YOKTUR.
  - Formulun iskeleti rapor 6.5 L3: "her hipotez icin normalize kanit skorlari x
    ariza modunun ciddiyet agirligi; surekli artis hizina ek puan; en yuksek
    hipotez + toplam risk". Raporda kanit normalizasyonunun TANIMI YOK — ikili
    (var/yok) kanit secildi ve fusion.py'de gerekcelendirildi.
  - HYP-OVERLOAD'in `discriminator` alani sozlesmede yazili: "tum fazlarda uniform
    dT artisi VE K normal". Yani asiri akim tek basina "asiri yuk" demek degildir.
  - MONOTONLUK: CIGRE TB 858 varlik saglik indekslerinde monotonluk ilkesini koyar —
    daha fazla ya da daha agir kanit skoru ASLA dusuremez. Asagidaki uc ozellik testi
    bunu tek ornekle degil, sozlesmedeki kanit kodlarinin alt kume taramasiyla dogrular.
"""

from __future__ import annotations

import itertools

import pytest

from panoalgo.fusion import score


def test_no_alarm_means_normal_and_zero_risk():
    result = score([], {})
    assert result.mode == "HYP-NORMAL"
    assert result.score == 0
    assert result.contributions == {}


def test_result_score_is_an_integer_in_the_contract_range():
    """Sema: risk.score tamsayi, 0-100."""
    result = score(["ALM-K-WARN", "ALM-K-ALM", "ALM-THR-PHASE-DIF"], {})
    assert isinstance(result.score, int)
    assert 0 <= result.score <= 100


def test_mode_is_always_a_hypothesis_code_from_the_contract(alarm_codes):
    codes = {h["code"] for h in alarm_codes["hypotheses"]}
    for alarms in ([], ["ALM-ARC-TRIP"], ["ALM-DEW-ALM"], ["ALM-DQ-JUMP"], ["ALM-BILINMEYEN"]):
        assert score(alarms, {}).mode in codes


def test_loose_connection_wins_when_its_evidence_accumulates():
    result = score(["ALM-K-WARN", "ALM-K-ALM", "ALM-THR-PHASE-DIF", "ALM-TTL-14D"], {})
    assert result.mode == "HYP-LOOSE-CONN"


def test_more_corroborating_evidence_raises_the_score():
    """Tek sinyal 'suphe', dort sinyal 'kanit'. Filo siralamasi buna gore yapilir."""
    weak = score(["ALM-K-WARN"], {}).score
    strong = score(["ALM-K-WARN", "ALM-K-ALM", "ALM-THR-PHASE-DIF", "ALM-TTL-14D"], {}).score
    assert strong > weak


def test_an_arc_trip_is_immediately_a_maximum_risk_event(alarm_codes):
    """HYP-ARC'in tek kaniti ve ciddiyet agirligi 1.0 — tek trip tam risk demektir."""
    result = score(["ALM-ARC-TRIP"], {})
    assert result.mode == "HYP-ARC"
    assert result.score == 100


def test_protection_loss_is_also_a_maximum_risk_event():
    """Pano sessizce korumasiz kaldiysa ciddiyet 1.0 (alarm-codes.yaml)."""
    result = score(["ALM-PROT-HEALTH"], {})
    assert result.mode == "HYP-PROT-LOSS"
    assert result.score == 100


def test_monitoring_faults_rank_below_real_faults(alarm_codes):
    """HYP-SELF-FAULT ciddiyet agirligi 0.3: 'ARIZA ALARMI DEGIL' (sozlesme advice)."""
    self_fault = score(["ALM-DQ-JUMP"], {})
    arc = score(["ALM-ARC-TRIP"], {})
    assert self_fault.mode == "HYP-SELF-FAULT"
    assert self_fault.score < arc.score


# ------------------------------------------------------- asiri yuk ayirt edici


def test_overcurrent_alone_is_diagnosed_as_overload_not_a_fault():
    """Rapor 6.5 L3: 'Asiri yuk ... K normal (ariza degil!)'."""
    result = score(["ALM-I-OVER"], {"k_ratio": 1.0})
    assert result.mode == "HYP-OVERLOAD"


def test_overcurrent_with_a_climbing_k_index_is_not_overload(thresholds):
    """Ayirt edici kosul: K NORMAL olmali. K tirmaniyorsa bu asiri yuk degil,
    gercek bir baglanti bozulmasidir — yuk transferi onerisi yanlis olurdu."""
    features = {"k_ratio": thresholds["k_ratio_alarm"] + 0.1}
    result = score(["ALM-I-OVER", "ALM-K-ALM"], features)
    assert result.mode != "HYP-OVERLOAD"
    assert result.mode == "HYP-LOOSE-CONN"


def test_overload_hypothesis_is_suppressed_but_others_still_score(thresholds):
    features = {"k_ratio": thresholds["k_ratio_alarm"] + 0.1}
    result = score(["ALM-I-OVER"], features)
    assert result.mode != "HYP-OVERLOAD"


# --------------------------------------------------------------- artis hizi


def test_a_persistently_rising_index_adds_a_risk_bonus():
    """Rapor 6.5 L3: 'surekli artis hizina ek puan'."""
    flat = score(["ALM-K-WARN"], {"k_rising": False}).score
    rising = score(["ALM-K-WARN"], {"k_rising": True}).score
    assert rising > flat


def test_the_rate_bonus_cannot_push_the_score_over_one_hundred():
    result = score(["ALM-ARC-TRIP"], {"k_rising": True})
    assert result.score == 100


# ------------------------------------------------------------------ katkilar


def test_contributions_name_the_alarm_codes_that_drove_the_score():
    """Arayuzdeki 'Neden?' bolumu bunu besler (sema: alarm kodu -> katki 0-1)."""
    result = score(["ALM-K-WARN", "ALM-K-ALM", "ALM-BILGISIZ"], {})
    assert set(result.contributions) == {"ALM-K-WARN", "ALM-K-ALM"}


def test_contributions_sum_to_one():
    result = score(["ALM-K-WARN", "ALM-K-ALM", "ALM-THR-PHASE-DIF"], {})
    assert sum(result.contributions.values()) == pytest.approx(1.0)


def test_contributions_are_within_the_schema_range():
    result = score(["ALM-K-WARN", "ALM-K-ALM"], {})
    assert all(0.0 <= v <= 1.0 for v in result.contributions.values())


def test_unknown_codes_do_not_contribute():
    """Sozlesmede olmayan kod skora katilmamali, sessizce yok sayilmali."""
    known = score(["ALM-K-WARN"], {}).score
    noisy = score(["ALM-K-WARN", "ALM-UYDURMA-KOD"], {}).score
    assert known == noisy


# ----------------------------------------------------------- sinira kalan sure


def test_time_to_limit_is_passed_through_from_the_features():
    assert score(["ALM-K-ALM"], {"ttl_h": 150.5}).ttl_h == 150.5


def test_time_to_limit_is_none_when_no_estimate_is_available():
    assert score(["ALM-K-ALM"], {}).ttl_h is None


# ------------------------------------------------------------- dayaniklilik


def test_score_never_raises_on_unexpected_input():
    assert score(None, None).mode == "HYP-NORMAL"


def test_result_is_json_serialisable_for_the_risk_block():
    """risk blogu dogrudan MQTT yukune girer; NaN/Infinity karantinaya duser."""
    import json

    result = score(["ALM-K-WARN", "ALM-K-ALM"], {"ttl_h": 12.5})
    json.dumps(
        {"score": result.score, "mode": result.mode, "ttl_h": result.ttl_h,
         "contributions": result.contributions},
        allow_nan=False,
    )


# ------------------------------------------------- monotonluk (CIGRE TB 858)


def _contract_evidence(alarm_codes: dict) -> list[str]:
    """Sozlesmedeki tum hipotezlerin kanit kodlari: tekrarsiz, sozlesme sirasinda."""
    codes: list[str] = []
    for hypothesis in alarm_codes["hypotheses"]:
        codes.extend(code for code in hypothesis["evidence"] if code not in codes)
    return codes


@pytest.mark.parametrize(
    "make_features",
    [
        lambda t: {},
        lambda t: {"k_rising": True},
        lambda t: {"k_ratio": t["k_ratio_alarm"] + 0.1},
    ],
    ids=["ozelliksiz", "artis-bonuslu", "asiri-yuk-ayirt-edicisi-kapali"],
)
def test_adding_evidence_never_lowers_the_score(alarm_codes, thresholds, make_features):
    """Kanit ekseninde monotonluk: bir kanit EKLEMEK skoru asla dusurmez.

    Tarama: sozlesmedeki kanit kodlarinin 0-3 elemanli TUM alt kumeleri taban alinir ve
    her tabana kalan her kod tek tek eklenir. Ozellikler sabit tutulur, cunku monotonluk
    iddiasi kanit ekseninde kuruludur. Ayirt edici kapaliyken de (K tirmaniyor) gecmeli:
    bastirilan hipotez, kalan hipotezlerin monotonlugunu bozamaz.
    """
    codes = _contract_evidence(alarm_codes)
    features = make_features(thresholds)
    for size in range(4):
        for base in itertools.combinations(codes, size):
            before = score(list(base), features).score
            for extra in codes:
                if extra in base:
                    continue
                after = score([*base, extra], features).score
                assert after >= before, f"{list(base)} + {extra}: {before} -> {after}"


def test_a_heavier_failure_mode_never_scores_below_a_lighter_one(alarm_codes):
    """Agirlik ekseninde monotonluk: ciddiyet agirligi buyuyunce tam kanitli skor da
    buyumeli. Esitlik serbest (ayni agirlikli iki hipotez ayni skoru verir), dususe izin yok."""
    ranked = sorted(
        (h for h in alarm_codes["hypotheses"] if h["evidence"]),
        key=lambda h: h["severity_w"],
    )
    scores = [score(list(h["evidence"]), {}).score for h in ranked]
    assert scores == sorted(scores), dict(zip([h["code"] for h in ranked], scores, strict=True))


def test_the_rate_bonus_never_lowers_the_score(alarm_codes):
    """Artis hizi ekseninde monotonluk: 'surekli artis' bilgisi eklemek (rapor 6.5 L3 ek
    puani) hicbir kanit kumesinde skoru dusurmemeli — kirpma 100'de olsa bile."""
    codes = _contract_evidence(alarm_codes)
    for size in range(4):
        for base in itertools.combinations(codes, size):
            flat = score(list(base), {"k_rising": False}).score
            rising = score(list(base), {"k_rising": True}).score
            assert rising >= flat, f"{list(base)}: {flat} -> {rising}"
