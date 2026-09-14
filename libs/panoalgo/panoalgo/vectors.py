"""Ortak test vektoru ureteci (TA3 Adim 3, Kisi A).

PLAN.md TA3 Adim 3: "firmware/tests/test_rls.c: Python tarafindaki test_k_index ile
AYNI test vektoru (data/fixtures/rls_vectors.csv), C ve Python ciktisi <=1e-6 farkla
ayni. Bu 'kenarda ve merkezde ayni algoritma' iddiasinin kanitidir."

Iddia sozle degil dosyayla kanitlanir: bu modul girdiyi VE Python'un adim adim
ciktisini yazar; C testi ayni girdiyi okur, kendi ciktisini uretir ve satir satir
karsilastirir. Iki taraftan biri degisirse test kirilir.

Vektor BILEREK deterministiktir (rastgele sayi yok): C tarafinda ayni rastgele sayi
uretecini yeniden kurmak imkansizdir, o yuzden gurultu girdinin icine gomulu gelir.

CLI:
    python -m panoalgo.vectors --out data/fixtures/rls_vectors.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

from .detect import KIndexEstimator

# Vektor parametreleri. Degerler PLAN.md TA2 Adim 1'deki test vektoruyle ayni
# buyukluk mertebesinde secildi; oradaki gibi isil modelin KENDISINDEN uretilir.
VECTOR_TS_S = 60.0
VECTOR_LAM = 0.998
VECTOR_TAU_S = 900.0
VECTOR_K_TRUE = 2.0e-4
VECTOR_STEPS = 240
VECTOR_CYCLE = 96          # yuk dalgasinin periyodu (ornek)
VECTOR_I_BASE = 200.0
VECTOR_I_SWING = 150.0

HEADER = ("step", "i_a", "dt_c", "k", "tau_s", "excited")


def _inputs() -> list[tuple[float, float]]:
    """Isil modelden deterministik (akim, sicaklik artisi) cifti uretir.

    Gurultu yok: C ile Python'un ayni sayiyi vermesi beklendigi icin girdi de
    tekrarlanabilir olmali. Yuk dalgasi RLS'i uyaracak kadar genis.
    """
    a = math.exp(-VECTOR_TS_S / VECTOR_TAU_S)
    dt = 0.0
    held = VECTOR_I_BASE
    rows = []
    for index in range(VECTOR_STEPS):
        i_a = VECTOR_I_BASE + VECTOR_I_SWING * math.sin(2.0 * math.pi * index / VECTOR_CYCLE)
        # Sifirinci derece tutucu: [k, k+1) araliginda BIR ONCEKI akim etkir.
        dt = a * dt + (1.0 - a) * VECTOR_K_TRUE * held * held
        held = i_a
        rows.append((i_a, dt))
    return rows


def build_vectors() -> list[dict]:
    """Girdi ciftlerini ve Python kestirimcisinin adim adim ciktisini uretir."""
    estimator = KIndexEstimator(ts=VECTOR_TS_S, lam=VECTOR_LAM)
    rows = []
    for step, (i_a, dt_c) in enumerate(_inputs()):
        state = estimator.update(i_a=i_a, dt_c=dt_c)
        rows.append(
            {
                "step": step,
                "i_a": f"{i_a:.9f}",
                "dt_c": f"{dt_c:.9f}",
                "k": f"{state.k:.12e}",
                "tau_s": f"{state.tau_s:.9f}",
                "excited": int(state.excited),
            }
        )
    return rows


def write_vectors(path: Path) -> Path:
    """Vektoru CSV olarak yazar (LF satir sonu, .gitattributes geregi)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(HEADER), lineterminator="\n")
        writer.writeheader()
        writer.writerows(build_vectors())
    return path


def default_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "fixtures" / "rls_vectors.csv"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RLS ortak test vektoru ureteci (Kisi A)")
    parser.add_argument("--out", default=None, help="cikti dosyasi")
    args = parser.parse_args(argv)

    path = write_vectors(Path(args.out) if args.out else default_path())
    print(f"{VECTOR_STEPS} adim -> {path} ({path.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
