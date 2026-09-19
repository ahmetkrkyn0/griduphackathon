"""Uyarlanabilir raporlamanin sim/ tarafi (F-36).

Buradaki asil iddia sudur: `--adaptive` acildiginda TARAMA (tespit) sayisi aynen
kalir, yalnizca MESAJ sayisi duser. Kutuphane tarafi
`libs/panoalgo/tests/test_reporting.py`de olculur; bu dosya kabuklarin gercek
CLI'siyla ayni seyi ucdan uca gosterir.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

from helpers import CONTRACTS_DIR, REPO_ROOT, SIM_DIR, free_port, run_sim, sim_env, wait_for_port

import panosim

DURDU = re.compile(r"durdu; (\d+) tarama, (\d+) mesaj")


def _run(script: str, *args: str, timeout_s: float = 180.0) -> list[str]:
    proc = run_sim(script, *args)
    out, _ = proc.communicate(timeout=timeout_s)
    assert proc.returncode == 0, out
    return out.splitlines()


def _published(lines: list[str], prefix: str) -> list[dict]:
    mark = f"[{prefix}] gridup/"
    return [json.loads(line.split(" ", 2)[2]) for line in lines if line.startswith(mark)]


# ---------------------------------------------------------------- panobeyni


@pytest.fixture
def cihazlar():
    started = []

    def start():
        mpr_port, tvoc_port = free_port(), free_port()
        started.append(run_sim("mpr53cs_sim.py", "--host", "127.0.0.1",
                               "--port", str(mpr_port), "--slave-id", "1", "--ct", "500"))
        started.append(run_sim("tvoc2_sim.py", "--host", "127.0.0.1",
                               "--port", str(tvoc_port), "--slave-id", "10"))
        wait_for_port(mpr_port)
        wait_for_port(tvoc_port)
        return mpr_port, tvoc_port

    yield start
    for proc in started:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.slow
def test_publishing_never_throttles_detection(cihazlar):
    """Uyarlanabilir kip ayni sayida mesaj icin EN AZ o kadar tarama yapar.

    NE OLCER: kapinin tespit ritmini KISALTMADIGINI. Sabit kipte her
    `--report-every` taramada bir mesaj cikar; uyarlanabilir kipte mesaj ancak bir
    sey degisince ya da azami sessizlik dolunca cikar, yani tarama/mesaj orani
    ASLA kucülmez. Bu, F-36'nin "seyrelen yalnizca yayindir" sartinin ucdan uca,
    gercek CLI ile alinmis kanitidir.

    NE OLCMEZ - ve NEDEN: bastirma ORANINI burada sinamiyoruz. Denendi ve
    KIRILGAN cikti (ayni makinede ayni komut 16, 20, 22 tarama verdi). Sebep
    olculdu: kisa bir kosuda mesajlarin tamami ISINMA olaylarindan cikabiliyor
    (veri kalitesi bitleri oturur, K kestirimi alanlari belirir/kaybolur) ve
    heartbeat'e hic sira gelmiyor. Kapi bu ornekleri DOGRU sekilde yayinliyor;
    yanlis olan, birkac saniyelik bir kosudan oran cikarmaya calismakti.

    Bastirma orani deterministik olarak `loadtest/veri_butcesi.py` ile olculur:
    gercek fizik ureteci, 10 s tespit periyodu, 86.400 ornek -> %2 olu bantta
    %41,0 bastirma (docs/09 §6.1). Zayif bir zamanlama testi, guclu bir olcumun
    yerine gecemez.
    """
    mpr_port, tvoc_port = cihazlar()
    ortak = (
        "--mpr", f"127.0.0.1:{mpr_port}", "--tvoc", f"127.0.0.1:{tvoc_port}",
        "--tvoc-unit", "10", "--period", "0.05", "--report-every", "2",
        "--max-messages", "8", "--dry-run",
    )

    sabit = _run("panobeyni_sim.py", *ortak)
    uyarlanabilir = _run("panobeyni_sim.py", *ortak, "--adaptive", "--max-silence", "2")

    def sayilar(lines: list[str]) -> tuple[int, int]:
        eslesme = DURDU.search("\n".join(lines))
        assert eslesme, "\n".join(lines[-10:])
        return int(eslesme.group(1)), int(eslesme.group(2))

    sabit_tarama, sabit_mesaj = sayilar(sabit)
    uyar_tarama, uyar_mesaj = sayilar(uyarlanabilir)

    assert sabit_mesaj == uyar_mesaj == 8, (sabit_mesaj, uyar_mesaj)
    # Sabit kip tanimi geregi tam olarak report_every x mesaj kadar tarar.
    assert sabit_tarama == 2 * sabit_mesaj, f"sabit kip beklenmedik: {sabit_tarama}/{sabit_mesaj}"
    # Asil sart: kapi tespit turlarini AZALTAMAZ.
    assert uyar_tarama >= sabit_tarama, (
        f"uyarlanabilir kip tespiti seyreltmis: {uyar_tarama} tarama / {uyar_mesaj} mesaj "
        f"(sabit: {sabit_tarama}/{sabit_mesaj})"
    )


@pytest.mark.slow
def test_adaptive_messages_still_match_the_frozen_contract(cihazlar):
    """Seyreltme sozlesmeyi DEGISTIRMEZ: cikan her mesaj yine sema-gecerlidir."""
    mpr_port, tvoc_port = cihazlar()
    lines = _run(
        "panobeyni_sim.py", "--mpr", f"127.0.0.1:{mpr_port}", "--tvoc", f"127.0.0.1:{tvoc_port}",
        "--tvoc-unit", "10", "--period", "0.05", "--report-every", "2", "--max-messages", "2",
        "--dry-run", "--adaptive", "--max-silence", "10",
    )
    payloads = _published(lines, "panobeyni")
    assert payloads, "\n".join(lines[-15:])

    schema = json.loads((CONTRACTS_DIR / "mqtt-telemetry.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for payload in payloads:
        assert not list(validator.iter_errors(payload)), payload


@pytest.mark.slow
def test_the_adaptive_flag_announces_that_the_scan_period_did_not_change(cihazlar):
    mpr_port, tvoc_port = cihazlar()
    lines = _run(
        "panobeyni_sim.py", "--mpr", f"127.0.0.1:{mpr_port}", "--tvoc", f"127.0.0.1:{tvoc_port}",
        "--tvoc-unit", "10", "--period", "0.05", "--report-every", "2", "--max-messages", "1",
        "--dry-run", "--adaptive", "--max-silence", "10",
    )
    banner = [line for line in lines if "uyarlanabilir raporlama" in line]
    assert banner, "\n".join(lines[:10])
    assert "tarama periyodu DEGISMEDI" in banner[0]


# ---------------------------------------------------------------- panosim


@pytest.mark.slow
def test_the_stream_mode_publishes_schema_valid_messages_when_adaptive(tmp_path):
    lines = _run(
        "panosim.py", "--panels", "1", "--period", "0.02", "--speed", "1",
        "--max-messages", "3", "--dry-run", "--adaptive", "--max-silence", "10",
    )
    payloads = _published(lines, "panosim")
    assert len(payloads) == 3, "\n".join(lines[-15:])

    schema = json.loads((CONTRACTS_DIR / "mqtt-telemetry.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for payload in payloads:
        assert not list(validator.iter_errors(payload)), payload

    banner = [line for line in lines if "uyarlanabilir raporlama" in line]
    assert banner and "tespit periyodu DEGISMEDI" in banner[0]


def test_the_gate_is_transparent_unless_the_flag_is_given():
    """Bayrak yoksa hicbir sey bastirilmaz: mevcut davranis aynen korunur."""
    args = panosim.parse_args(["--panels", "1", "--dry-run"])
    gate = panosim._build_gate(args, CONTRACTS_DIR)
    assert gate.policy.transparent


def test_the_gate_reads_its_deadbands_from_the_contract():
    args = panosim.parse_args(["--panels", "1", "--dry-run", "--adaptive"])
    gate = panosim._build_gate(args, CONTRACTS_DIR)
    assert not gate.policy.transparent
    assert gate.policy.dt_c_k > 0.0 and gate.policy.max_silence_s > 0.0


def test_a_max_silence_inside_the_centres_comms_window_is_refused():
    """Sozlesmedeki heartbeat penceresine giren bir deger CLI'da reddedilir."""
    args = panosim.parse_args(["--panels", "1", "--dry-run", "--adaptive", "--max-silence", "600"])
    with pytest.raises(SystemExit, match="kesinti sanilir"):
        panosim._build_gate(args, CONTRACTS_DIR)


def test_adaptive_is_refused_in_scenario_mode():
    """Senaryo kipinde seyreltme ZATEN var; ikinci bir kapi demoyu bosaltirdi."""
    proc = subprocess.run(
        [sys.executable, str(SIM_DIR / "panosim.py"), "--scenario", "S0_normal",
         "--adaptive", "--dry-run"],
        cwd=str(SIM_DIR), env=sim_env(), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    assert proc.returncode != 0
    assert "yalnizca surekli kipte" in (proc.stdout + proc.stderr)
