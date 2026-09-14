"""Dogrulama ve olcum (T4.1/T4.2, Kisi A): senaryo + etiket -> sayilar.

PLAN.md T4.1: "10 senaryo x metrik tablosu: recall, precision, ONE ALMA SURESI
(saat), yanlis alarm/100 pano/gun. Ve sabit 70 K esigi vs L0+L1+L2+L3
karsilastirmasi: ayni veride kac saat once, kac yanlis alarmla."

Olculen seyler ve tanimlari:

  recall     Etiketin `expect` listesindeki kodlardan kaci pencere icinde gercekten
             cikti. 1.00 = beklenen her alarm cikti.
  precision  Cikan alarmlar icinde YASAKLI olan (`not_expect`) var mi. Bu metrik
             ozellikle S2 icin kritik: asiri yuk bir ariza DEGILDIR, K alarmi
             cikarsa sistem yanlis teshis koymus olur.
  one alma   l0_breach_at (sabit 70 K esiginin asildigi an) eksi ILK L1 TESPITI.
             Pozitif = fizik katmani sabit esikten bu kadar saat ONCE uyardi.
  yanlis     S0 (tamamen saglikli) senaryosunda cikan her alarm yanlis alarmdir.
             100 pano x gun olcegine tasinir, cunku operatorun gunluk alarm butcesi
             sozlesmede bu olcekte tanimli (alarms_per_operator_day_acceptable).

DURUSTLUK NOTU: bu betik etiket dosyasindaki "beklenen"i degil, VERIDEKI gercek
alarm sutununu okur. Etiket yalnizca "ne olmasi gerekiyordu"yu soyler; ne oldugu
senaryonun kendi ciktisindadir. Ikisi ayni dosyadan gelseydi olcum anlamsiz olurdu.

CLI:
    python -m panoalgo.validate --fixtures data/fixtures
    python -m panoalgo.validate --out docs/12-dogrulama-sonuclari.md
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from .detect import default_contracts_dir

FIXED_THRESHOLD_CODE = "ALM-THR-TERM-ALM"  # sabit 70 K esigi

# Merkezde uretilen kodlar kenar fixture'inda ASLA gorunmez; recall'da "kacan" olarak
# sayilmalari yaniltici olur. ALM-COMMS-LOST'u backend/app/alarm_service.py heartbeat
# zaman asimindan uretir (kenar veriyi zaten gonderemiyordur).
CENTRE_ONLY_CODES = frozenset({"ALM-COMMS-LOST"})
SECONDS_PER_HOUR = 3600.0


@dataclass(frozen=True)
class ScenarioResult:
    """Bir senaryonun olcum sonucu."""

    scenario_id: str
    duration_h: float
    samples: int
    expected: int
    detected: int
    forbidden_fired: tuple[str, ...]
    missed: tuple[str, ...]
    centre_only: tuple[str, ...]
    lead_time_h: float | None
    l0_breach_at: str | None
    first_l1_at: str | None
    false_alarm_codes: tuple[str, ...]
    false_alarms_per_100_panel_days: float

    @property
    def recall(self) -> float | None:
        return None if self.expected == 0 else self.detected / self.expected

    @property
    def precision_ok(self) -> bool:
        return not self.forbidden_fired


def load_layers(contracts_dir: Path | None = None) -> dict[str, str]:
    """Alarm kodu -> katman etiketi (contracts/alarm-codes.yaml alarms[].layer)."""
    directory = contracts_dir or default_contracts_dir()
    data = yaml.safe_load((directory / "alarm-codes.yaml").read_text(encoding="utf-8"))
    return {row["code"]: str(row["layer"]) for row in data["alarms"]}


def validate_scenario(
    csv_path: Path,
    labels_path: Path,
    contracts_dir: Path | None = None,
) -> ScenarioResult:
    """Tek bir senaryoyu olcer."""
    import pandas as pd

    layers = load_layers(contracts_dir)
    l1_codes = {code for code, layer in layers.items() if layer == "L1"}

    frame = pd.read_csv(csv_path)
    frame["ts"] = pd.to_datetime(frame["ts"])
    frame["alarm_set"] = frame["alarms"].fillna("").map(lambda v: set(filter(None, str(v).split(";"))))
    dq_column = frame["dq_codes"] if "dq_codes" in frame else pd.Series("", index=frame.index)
    frame["dq_set"] = dq_column.fillna("").map(lambda v: set(filter(None, str(v).split(";"))))
    labels = json.loads(labels_path.read_text(encoding="utf-8"))

    duration_h = float(labels["duration_h"])
    expected_total = detected_total = 0
    forbidden: set[str] = set()
    missed: set[str] = set()
    centre: set[str] = set()
    lead_time_h: float | None = None
    l0_breach_at: str | None = None
    first_l1_at: str | None = None

    for label in labels["labels"]:
        window = frame[
            (frame["ts"] >= pd.Timestamp(label["t_start"])) & (frame["ts"] <= pd.Timestamp(label["t_end"]))
        ]
        fired = set().union(*window["alarm_set"]) if len(window) else set()
        fired |= set().union(*window["dq_set"]) if len(window) else set()

        expect = set(label["expect"])
        centre |= expect & CENTRE_ONLY_CODES
        expect -= CENTRE_ONLY_CODES
        expected_total += len(expect)
        detected_total += len(expect & fired)
        missed |= expect - fired
        forbidden |= set(label.get("not_expect", [])) & fired

        breach = label.get("l0_breach_at")
        if breach and l0_breach_at is None:
            l0_breach_at = breach
            hit = window.loc[window["alarm_set"].map(lambda s: bool(s & l1_codes)), "ts"]
            if not hit.empty:
                first_l1_at = hit.iloc[0].isoformat()
                lead_time_h = (pd.Timestamp(breach) - hit.iloc[0]).total_seconds() / SECONDS_PER_HOUR

    false_codes, per_100 = _false_alarms(frame, labels, duration_h)
    return ScenarioResult(
        scenario_id=labels["scenario_id"],
        duration_h=duration_h,
        samples=len(frame),
        expected=expected_total,
        detected=detected_total,
        forbidden_fired=tuple(sorted(forbidden)),
        missed=tuple(sorted(missed)),
        centre_only=tuple(sorted(centre)),
        lead_time_h=lead_time_h,
        l0_breach_at=l0_breach_at,
        first_l1_at=first_l1_at,
        false_alarm_codes=false_codes,
        false_alarms_per_100_panel_days=per_100,
    )


def _false_alarms(frame, labels: dict, duration_h: float) -> tuple[tuple[str, ...], float]:
    """Etiket penceresi DISINDA cikan alarmlar yanlis alarmdir.

    Bir kodun kesintisiz gorundugu her aralik TEK bir alarm sayilir; aksi halde
    15 dakikalik her ornek ayri bir alarmmis gibi sayilir ve operator yuku
    olculemeyecek kadar sisirilir.
    """
    import pandas as pd

    inside = pd.Series(False, index=frame.index)
    for label in labels["labels"]:
        inside |= (frame["ts"] >= pd.Timestamp(label["t_start"])) & (
            frame["ts"] <= pd.Timestamp(label["t_end"])
        )

    outside = frame[~inside]
    episodes = 0
    codes: set[str] = set()
    active: set[str] = set()
    for alarm_set in outside["alarm_set"]:
        episodes += len(alarm_set - active)
        codes |= alarm_set
        active = alarm_set

    panel_days = duration_h / 24.0
    per_100 = (episodes / panel_days) * 100.0 if panel_days > 0 else 0.0
    return tuple(sorted(codes)), per_100


def validate_all(fixtures_dir: Path, contracts_dir: Path | None = None) -> list[ScenarioResult]:
    """Dizindeki tum senaryolari olcer (etiket dosyasi olanlar)."""
    results = []
    for labels_path in sorted(fixtures_dir.glob("*.labels.json")):
        csv_path = labels_path.with_name(labels_path.name.replace(".labels.json", ".csv"))
        if csv_path.exists():
            results.append(validate_scenario(csv_path, labels_path, contracts_dir))
    return results


# --------------------------------------------------------------------- rapor


def render_markdown(results: list[ScenarioResult], contracts_dir: Path | None = None) -> str:
    """docs/12-dogrulama-sonuclari.md govdesini uretir."""
    directory = contracts_dir or default_contracts_dir()
    thresholds = yaml.safe_load((directory / "alarm-codes.yaml").read_text(encoding="utf-8"))["thresholds"]
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")

    lines = [
        "# 12. Dogrulama Sonuclari",
        "",
        "> Bu dosya ELLE YAZILMAZ. `python scripts/validate.py --out docs/12-dogrulama-sonuclari.md`",
        "> komutu `data/fixtures/` altindaki seed'li senaryolari yeniden olcer ve bu tabloyu",
        "> uretir (PLAN.md T4.2). Asagidaki her sayi tekrar uretilebilir.",
        "",
        f"Uretim zamani: {stamp}",
        "",
        "## 1. Senaryo bazinda tespit basarisi",
        "",
        "| Senaryo | Sure (s) | Ornek | Beklenen | Yakalanan | Recall | Yasakli alarm | Kacan |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        recall = "-" if r.recall is None else f"{r.recall:.2f}"
        forbidden = ", ".join(r.forbidden_fired) or "yok"
        missed = ", ".join(r.missed) or "yok"
        if r.centre_only:
            missed += f" (merkezde: {', '.join(r.centre_only)})"
        lines.append(
            f"| `{r.scenario_id}` | {r.duration_h:.0f} | {r.samples} | {r.expected} | "
            f"{r.detected} | {recall} | {forbidden} | {missed} |"
        )

    lines += [
        "",
        "## 2. Sabit 70 K esigi ile karsilastirma",
        "",
        f"Sabit esik = `thresholds.term_rise_alarm_k` = {thresholds['term_rise_alarm_k']} K "
        f"(`{FIXED_THRESHOLD_CODE}`). Fizik katmani (L1) bu esikten kac saat once uyardi?",
        "",
        "| Senaryo | Ilk L1 tespiti | 70 K ihlali | One alma (saat) | One alma (gun) |",
        "|---|---|---|---:|---:|",
    ]
    for r in results:
        if r.l0_breach_at is None:
            continue
        lead_h = "-" if r.lead_time_h is None else f"{r.lead_time_h:.1f}"
        lead_d = "-" if r.lead_time_h is None else f"{r.lead_time_h / 24.0:.1f}"
        lines.append(
            f"| `{r.scenario_id}` | {r.first_l1_at or 'tespit yok'} | {r.l0_breach_at} | {lead_h} | {lead_d} |"
        )

    lines += [
        "",
        "## 3. Yanlis alarm yuku",
        "",
        "Etiket penceresi disinda cikan her alarm yanlis alarmdir. Kesintisiz bir aralik",
        "TEK alarm sayilir (operator yuku ornek sayisiyla degil olay sayisiyla olculur).",
        "",
        f"Sozlesme hedefi: gunde {thresholds['alarms_per_operator_day_acceptable']} kabul edilebilir, "
        f"{thresholds['alarms_per_operator_day_max']} ust sinir (100 pano olceginde).",
        "",
        "| Senaryo | Yanlis alarm / 100 pano / gun | Cikan kodlar |",
        "|---|---:|---|",
    ]
    for r in results:
        codes = ", ".join(r.false_alarm_codes) or "yok"
        lines.append(f"| `{r.scenario_id}` | {r.false_alarms_per_100_panel_days:.1f} | {codes} |")

    lines += ["", "## 4. Nasil yeniden uretilir", "", "```bash",
              "python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures",
              "python scripts/validate.py --out docs/12-dogrulama-sonuclari.md", "```", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Senaryo dogrulama olcumu (Kisi A)")
    parser.add_argument("--fixtures", default=None, help="fixture dizini (varsayilan data/fixtures)")
    parser.add_argument("--out", default=None, help="markdown ciktisi; verilmezse ekrana ozet")
    args = parser.parse_args(argv)

    fixtures_dir = Path(args.fixtures) if args.fixtures else _default_fixtures_dir()
    results = validate_all(fixtures_dir)
    if not results:
        print(f"fixture bulunamadi: {fixtures_dir}", file=sys.stderr)
        return 1

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_markdown(results), encoding="utf-8", newline="\n")
        print(f"{len(results)} senaryo olculdu -> {out_path}")
        return 0

    for r in results:
        recall = "-" if r.recall is None else f"{r.recall:.2f}"
        lead = "-" if r.lead_time_h is None else f"{r.lead_time_h:7.1f} h"
        flag = "" if r.precision_ok else f"  YASAKLI: {', '.join(r.forbidden_fired)}"
        print(
            f"{r.scenario_id:<16} recall={recall:<5} one alma={lead:<10} "
            f"yanlis/100pano/gun={r.false_alarms_per_100_panel_days:6.1f}{flag}"
        )
    return 0


def _default_fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "fixtures"


if __name__ == "__main__":
    sys.exit(main())
