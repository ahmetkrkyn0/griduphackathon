#!/usr/bin/env python3
"""Dogrulama betigi girisi (PLAN.md T4.2, Kisi A).

Asil mantik libs/panoalgo/panoalgo/validate.py icindedir; bu dosya yalnizca PLAN.md
T4.1/T4.2'nin adiyla cagrilabilmesi icin bir giristir:

    python scripts/validate.py --out docs/12-dogrulama-sonuclari.md

SAHIPLIK NOTU (Kisi B'nin dikkatine): CODEOWNERS `/scripts/` dizinini Kisi B'ye
veriyor, ama PLAN.md T4.2 bu dosyayi acikca Kisi A'ya atiyor. Catismayi buyutmemek
icin dosya olabilecek en ince haliyle birakildi — icerik degisiklikleri
libs/panoalgo tarafinda yapilir, burasi bir daha degismez. Itirazin varsa
13:00 penceresinde konusalim; alternatif `python -m panoalgo.validate` ile bu
dosyaya hic gerek kalmamasidir.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "libs" / "panoalgo"))

from panoalgo.validate import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
