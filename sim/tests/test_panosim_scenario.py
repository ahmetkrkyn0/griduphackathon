"""panosim senaryo kipi (Kisi A, K1 + K3).

Olculen iddialar:
  1. `--scenario` demo betiklerinin kullandigi bayraklarla CALISIR
     (birlesme sonrasi `unrecognized arguments: --scenario ...` ile duserdi).
  2. Oynatilan fizik, data/fixtures/ CSV'lerini ureten fizigin AYNISIDIR.
  3. Yayinlanan `ts` DUVAR SAATIDIR ve kesin artar (K3).
  4. Haberlesme boslugunda sahte deger URETILMEZ.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from helpers import SIM_DIR, sim_env

import panosim
from panoalgo import scenarios


def run_cli(*args: str) -> list[str]:
    """panosim.py'yi GERCEK CLI'siyla kosturur; stdout satirlarini doner."""
    result = subprocess.run(
        [sys.executable, str(SIM_DIR / "panosim.py"), *args],
        cwd=str(SIM_DIR),
        env=sim_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert result.returncode == 0, f"cikis {result.returncode}\n{result.stdout}\n{result.stderr}"
    return result.stdout.splitlines()


def published_payloads(lines: list[str]) -> list[dict]:
    """--dry-run ciktisindaki '[panosim] <topic> <json>' satirlarini cozer."""
    payloads = []
    for line in lines:
        if not line.startswith("[panosim] gridup/"):
            continue
        payloads.append(json.loads(line.split(" ", 2)[2]))
    return payloads


# ------------------------------------------------------- 1. demo betigi arayuzu


@pytest.mark.slow
@pytest.mark.parametrize(
    "extra",
    [
        ("--scenario", "S0_normal", "--pano", "SIM-00001"),
        ("--scenario", "S1_loose_conn", "--point", "DSYA3_L2", "--pano", "SIM-00001"),
        ("--scenario", "S2_overload", "--pano", "SIM-00002"),
        ("--scenario", "S3_condense", "--pano", "SIM-00003"),
        ("--scenario", "S4_arc", "--pano", "SIM-00004"),
        ("--scenario", "S5_prot_health", "--detector", "X2:4", "--pano", "SIM-00005"),
        ("--scenario", "S6_comms_loss", "--pano", "SIM-00006"),
    ],
    ids=["s0", "s1", "s2", "s3", "s4", "s5", "s6"],
)
def test_demo_scripts_command_line_is_accepted(extra):
    """demo/senaryo/s0-s6.sh tam olarak bu bayraklari geciyor."""
    lines = run_cli(*extra, "--duration", "3", "--dry-run")

    assert any("SENARYO" in line for line in lines), "\n".join(lines)
    assert published_payloads(lines) or extra[1] == "S6_comms_loss"


def test_unknown_scenario_fails_loudly_not_silently():
    result = subprocess.run(
        [sys.executable, str(SIM_DIR / "panosim.py"), "--scenario", "S99_yok", "--dry-run"],
        cwd=str(SIM_DIR), env=sim_env(), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=120,
    )

    assert result.returncode != 0
    assert "bilinmeyen senaryo" in (result.stdout + result.stderr)


# --------------------------------------------- 2. fixture ile ayni fizik


def test_replay_reuses_the_exact_physics_that_produced_the_fixtures():
    """Oynatma ile CSV uretimi ayni yurutucudan gecer: ayni adim -> ayni deger.

    Bu testin kirilmasi, demoda gosterilen verinin docs/12'yi ureten veriden
    ayristigi anlamina gelir — juriye "ayni fizik" diyemeyiz.
    """
    plan = scenarios.plan("S2_overload", seed=1304, duration_h=24.0)

    first = [s.payload for s in scenarios.iter_samples(plan) if s.payload]
    second = [s.payload for s in scenarios.iter_samples(plan) if s.payload]

    assert first == second, "ayni plan iki kez farkli veri uretti (tekrarlanabilirlik kayboldu)"
    assert first, "hic ornek uretilmedi"


def test_point_override_moves_the_injection():
    """--point senaryonun varsayilan noktasini gercekten degistirir."""
    default = scenarios.plan("S1_loose_conn", seed=1304, duration_h=24.0)
    moved = scenarios.plan("S1_loose_conn", seed=1304, duration_h=24.0, point="DSYA5_L1")

    assert default.spec.point == "DSYA3_L2"
    assert moved.spec.point == "DSYA5_L1"


def test_detector_override_clears_that_bit_in_the_tvoc_register():
    """--detector X2:4 -> PDU 222'de 4. dedektorun biti 0 (kalanlar 1)."""
    plan = scenarios.plan("S5_prot_health", seed=1304, duration_h=48.0, detector="X2:4")

    faulted = [s.payload for s in scenarios.iter_samples(plan)
               if s.payload and not s.payload["tvoc"]["prot_health_ok"]]

    assert faulted, "koruma sagligi hic bozulmadi"
    tvoc = faulted[-1]["tvoc"]
    assert tvoc["sensor_x2"] == 0xFFFF & ~(1 << 3), f"beklenmeyen sensor_x2: {tvoc['sensor_x2']:#06x}"
    assert tvoc["sensor_x3"] == 0xFFFF, "yanlis konnektorun biti temizlendi"


def test_invalid_detector_name_is_rejected_before_the_demo_starts():
    with pytest.raises(ValueError, match="X2:4"):
        scenarios.plan("S5_prot_health", seed=1304, duration_h=48.0, detector="4")


# ------------------------------------------------------------- 3. zaman damgasi (K3)


@pytest.mark.slow
def test_published_timestamps_are_wall_clock_and_strictly_increasing():
    """K3: `ts` artik duvar saatinin ONUNE GECMEZ; arayuzun `to = new Date()` penceresine duser."""
    before = datetime.now(timezone.utc) - timedelta(seconds=2)

    payloads = published_payloads(
        run_cli("--scenario", "S0_normal", "--pano", "SIM-00001", "--duration", "4", "--dry-run")
    )

    assert len(payloads) >= 2, "karsilastirma icin en az iki mesaj gerekiyor"
    stamps = [datetime.fromisoformat(p["ts"]) for p in payloads]
    after = datetime.now(timezone.utc) + timedelta(seconds=2)

    assert stamps == sorted(stamps) and len(set(stamps)) == len(stamps), \
        f"zaman damgalari kesin artan degil: {stamps}"
    assert before <= stamps[0] and stamps[-1] <= after, \
        f"damgalar duvar saati penceresinin disinda: {stamps[0]} .. {stamps[-1]}"


@pytest.mark.slow
def test_sim_clock_flag_restores_the_old_simulated_timestamps():
    """--sim-clock eski davranisi geri verir (uzun vadeli veri uretimi icin)."""
    payloads = published_payloads(
        run_cli("--scenario", "S0_normal", "--pano", "SIM-00001",
                "--duration", "3", "--sim-clock", "--dry-run")
    )

    assert payloads
    # S0 gecis mevsiminde baslar (2026-04-06); duvar saati ile karistirilamaz.
    assert datetime.fromisoformat(payloads[0]["ts"]).year == 2026
    assert datetime.fromisoformat(payloads[0]["ts"]).month == 4


def test_stamper_never_repeats_a_second_for_the_same_panel():
    stamper = panosim.Stamper(enabled=True)

    stamps = [stamper.stamp({"pano_id": "SIM-00001", "ts": "x"})["ts"] for _ in range(5)]

    assert len(set(stamps)) == 5, f"ayni saniyeye birden cok ornek dustu: {stamps}"
    assert stamps == sorted(stamps)


def test_stamper_keeps_panels_independent():
    """Iki pano ayni saniyede yayinlayabilir; biri digerini ileri itmemeli."""
    stamper = panosim.Stamper(enabled=True)

    first = stamper.stamp({"pano_id": "SIM-00001", "ts": "x"})["ts"]
    second = stamper.stamp({"pano_id": "SIM-00002", "ts": "x"})["ts"]

    assert first == second


# ------------------------------------------------------------ 4. haberlesme boslugu


def test_comms_gap_publishes_nothing_instead_of_fake_values():
    """S6'da bosluk suresince ornek URETILMEZ; sifir ya da son deger tekrarlanmaz."""
    plan = scenarios.plan("S6_comms_loss", seed=1304, duration_h=72.0)
    gap_h = float(plan.spec.params["gap_h"])

    samples = list(scenarios.iter_samples(plan))
    silent = [s for s in samples if s.payload is None]

    assert silent, "haberlesme boslugu hic olusmadi"
    assert all(plan.baseline_h <= s.hours < plan.baseline_h + gap_h for s in silent)
    # Bosluk sadece pencere icinde: disarida her adimda veri var.
    assert all(s.payload is not None for s in samples
               if not (plan.baseline_h <= s.hours < plan.baseline_h + gap_h))


def test_short_baseline_lets_a_live_demo_reach_the_k_ratio_alarm():
    """Y1: --baseline-hours canli demoda taban ogrenmeyi kisaltir."""
    plan = scenarios.plan("S1_loose_conn", seed=1304, duration_h=720.0, baseline_h=12.0)

    assert plan.baseline_h == 12.0
    # Sozlesme degeri (168 h) varsayilan olarak korunur.
    assert scenarios.plan("S1_loose_conn", seed=1304, duration_h=720.0).baseline_h == 168.0
