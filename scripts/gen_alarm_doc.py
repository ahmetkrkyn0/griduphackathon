#!/usr/bin/env python3
"""docs/06-alarm-matrisi.md icindeki URETILMIS tablolari contracts/alarm-codes.yaml'dan yeniler (Kisi B).

Dokumandaki anlati elle yazilir; oncelik matrisi ve alarm katalogu isaretli bloklar arasinda uretilir
ve ELLE DUZENLENMEZ (PLAN.md kural 10: ayni sabit iki yerde iki farkli deger olamaz).

    python scripts/gen_alarm_doc.py            # yeniler
    python scripts/gen_alarm_doc.py --check    # guncel degilse 1 ile cikar (PR oncesi)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "alarm-codes.yaml"
DOC = ROOT / "docs" / "06-alarm-matrisi.md"

PRIORITY_ORDER = ("P1", "P2", "P3", "SYS", "INFO")


def _yes(value) -> str:
    if value is True:
        return "evet"
    if value in (False, None):
        return "-"
    return str(value)


def priority_matrix(contract: dict) -> str:
    priorities = contract["priorities"]
    counts = {prio: sum(1 for a in contract["alarms"] if a["prio"] == prio) for prio in PRIORITY_ORDER}
    rows = [
        "| Oncelik | Ad | Kod sayisi | Ekran | Is emri | SMS | WhatsApp | Arama (dk) | Eskalasyon (dk) | SCADA | Yerel role | Bastirilabilir |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for prio in PRIORITY_ORDER:
        spec = priorities[prio]
        rows.append(
            f"| **{prio}** | {spec['name']} | {counts[prio]} | {_yes(spec.get('screen'))} | {_yes(spec.get('work_order'))} "
            f"| {_yes(spec.get('sms'))} | {_yes(spec.get('whatsapp'))} | {_yes(spec.get('call_after_min'))} "
            f"| {_yes(spec.get('escalate_after_min'))} | {_yes(spec.get('scada'))} | {_yes(spec.get('local_relay'))} "
            f"| {'evet' if spec.get('suppressible', True) else '**hayir**'} |"
        )
    return "\n".join(rows)


def alarm_catalog(contract: dict) -> str:
    thresholds = contract["thresholds"]
    evidence_of: dict[str, list[str]] = {}
    for hypothesis in contract["hypotheses"]:
        for code in hypothesis["evidence"]:
            evidence_of.setdefault(code, []).append(hypothesis["code"])
    rows = [
        "| Bit | Kod | Oncelik | Katman | Metin | Esik | Hipotez kaniti | Dayanak |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for alarm in sorted(contract["alarms"], key=lambda a: a["bit"]):
        threshold = ""
        if "threshold" in alarm:
            # Cok kosullu kural liste yazar (or. ALM-NEUTRAL-THD); ikisi de gosterilir.
            refs = alarm["threshold"]
            names = [ref.removeprefix("thresholds.") for ref in ([refs] if isinstance(refs, str) else refs)]
            threshold = " ve ".join(f"`{name}` = {thresholds[name]}" for name in names)
        rows.append(
            f"| {alarm['bit']} | `{alarm['code']}` | {alarm['prio']} | {alarm['layer']} | {alarm['text']} "
            f"| {threshold} | {', '.join(evidence_of.get(alarm['code'], [])) or '-'} | {alarm.get('basis', '-')} |"
        )
    return "\n".join(rows)


def render(doc: str, contract: dict) -> str:
    blocks = {"oncelik-matrisi": priority_matrix(contract), "alarm-katalogu": alarm_catalog(contract)}
    for name, table in blocks.items():
        pattern = re.compile(rf"(<!-- URETILMIS:{name} -->\n)(?:.*?\n)?(<!-- /URETILMIS:{name} -->)", re.S)
        if not pattern.search(doc):
            raise SystemExit(f"{DOC.name} icinde '{name}' blogu yok")
        doc = pattern.sub(lambda m: m[1] + table + "\n" + m[2], doc)
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="dokuman guncel degilse 1 ile cik")
    args = parser.parse_args(argv)

    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    current = DOC.read_text(encoding="utf-8")
    updated = render(current, contract)
    if args.check:
        if updated != current:
            print(f"{DOC.relative_to(ROOT)} guncel degil: python scripts/gen_alarm_doc.py")
            return 1
        print("guncel")
        return 0
    DOC.write_bytes(updated.encode("utf-8"))
    print(f"yenilendi: {DOC.relative_to(ROOT)} (sozlesme v{contract['version']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
