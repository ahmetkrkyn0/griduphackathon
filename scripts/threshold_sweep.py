#!/usr/bin/env python3
"""Ciy noktasi esik taramasi (F-06, Kisi A): esik -> saglikli panodaki operator yuku.

NEDEN SADECE CIY: docs/12 §3'te olculen tek gercek zayiflik bu. Saglikli panoda
(`S0_normal`) 71,4 yanlis alarm/100 pano/gun cikiyor ve TAMAMI `ALM-DEW-*`.
Sozlesme siniri 150 oldugu icin "geciyor", ama hicbir esigin "neden bu sayi"
sorusuna olculmus cevabi yoktu (KALAN-EKSIKLER.md D7).

ESIK DEGISMEZ. `contracts/alarm-codes.yaml` donmustur; bu betik esigi yalnizca
SAVUNUR ya da `contracts/changes/` altina bir oneri icin kanit uretir.

TARAMA NEYI YENIDEN KOSTURUYOR (backlog'un "KRITIK" notu):
  Ciy karari `limits._environment()` icinde TEK bir alan uzerinde, TEK bir kesin
  kucuktur karsilastirmasidir: `env.td_margin_k < esik`. Esik ne fizige, ne
  uretece, ne de `td_margin_k` degerine girer — yalnizca karsilastirmaya girer.
  Bu yuzden her izgara noktasinda fixture'i yeniden uretmek GEREKMEZ: fixture'daki
  `td_margin_k` sutunu uzerinde karar yeniden kosturulur (HIZLI YOL).
  Kestirme olmadigini betik kendisi kanitlar:
    --verify  sozlesmedeki esiklerle hesaplanan kodlarin fixture'in hazir `alarms`
              sutunuyla SATIR SATIR ayni oldugunu dogrular;
    --rerun   her izgara noktasi icin contracts/ dizininin gecici bir kopyasini
              o esikle yazar ve senaryoyu URETEC + KENAR BORU HATTINDAN bastan
              kosturur, sonucu hizli yolla karsilastirir.
  OLCULDU (bu makine, 168 h / 672 ornek, 11 noktali izgara): hizli yol 0,024 s,
  `--rerun` 30,9 s (nokta basina ~2,8 s) ve iki yol AYNI sonucu veriyor. Yani
  kestirme yol 1.300 kat ucuz ve bedava degil — kaniti yukaridaki iki bayrak.

CLI:
    python scripts/threshold_sweep.py                 # tablo ekrana
    python scripts/threshold_sweep.py --verify        # kestirme yolun kanitini yaz
    python scripts/threshold_sweep.py --rerun         # tespiti gercekten yeniden kostur
    python scripts/threshold_sweep.py --out rapor.md
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "libs" / "panoalgo"))

HEALTHY_SCENARIO = "S0_normal"
CONDENSE_SCENARIO = "S3_condense"
MARGIN_COLUMN = "td_margin_k"
WARN_CODE, ALARM_CODE = "ALM-DEW-WARN", "ALM-DEW-ALM"
WARN_KEY, ALARM_KEY = "dew_margin_warn_k", "dew_margin_alarm_k"
HOURS_PER_DAY = 24.0
SECONDS_PER_HOUR = 3600.0

# EEMUA 191: 24 saatten uzun sure ayakta duran alarm BAYAT (stale) sayilir. Tarama
# bunu ayrica raporlar, cunku "olay sayisi" olcutu ayakta duran tek bir alarmi UCUZ
# gosterir — operator icin en pahali alarm tam da odur.
STALE_ALARM_H = 24.0

# Taranan esik degerleri (K). Sozlesmedeki iki deger (3,0 ve 1,0) icerdedir; alt uc
# yogusmanin fiziksel siniri olan 0 K'nin altina, ust uc sozlesmenin iki katina kadar
# gider. Daha genis bir izgara yeni bilgi uretmiyor (bkz. docs/05 §11 tablosu).
GRID_K: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0)

# Sozlesme ciftini (3,0 / 1,0) karsilastirmak icin denenen aday ciftler.
CANDIDATE_PAIRS: tuple[tuple[float, float], ...] = (
    (6.0, 3.0),
    (5.0, 2.0),
    (4.0, 2.0),
    (3.0, 1.0),  # SOZLESME
    (2.0, 1.0),
    (2.0, 0.5),
    (1.5, 0.5),
    (1.0, 0.0),
    (0.5, 0.0),
)


@dataclass(frozen=True)
class MarginSeries:
    """Bir senaryonun ciy marji serisi ve olcegi."""

    scenario_id: str
    margins: tuple[float, ...]
    period_h: float
    duration_h: float

    @property
    def panel_days(self) -> float:
        return self.duration_h / HOURS_PER_DAY


@dataclass(frozen=True)
class SweepRow:
    """Tek bir esik degerinin saglikli panodaki sonucu."""

    threshold_k: float
    episodes: int
    per_100_panel_days: float
    duty_pct: float
    longest_run_h: float

    @property
    def stale(self) -> bool:
        """EEMUA 191 anlaminda bayat alarm uretiyor mu."""
        return self.longest_run_h > STALE_ALARM_H


@dataclass(frozen=True)
class SeasonRow:
    """Ayni SAGLIKLI senaryonun farkli mevsimdeki ciy yuku."""

    season: str
    min_margin_k: float
    median_margin_k: float
    max_margin_k: float
    warn_duty_pct: float
    alarm_duty_pct: float
    per_100_panel_days: float


@dataclass(frozen=True)
class PairRow:
    """Bir (uyari, alarm) ciftinin yuku ve yogusma senaryosundaki tespiti."""

    warn_k: float
    alarm_k: float
    episodes: int
    per_100_panel_days: float
    warn_duty_pct: float
    alarm_duty_pct: float
    longest_run_h: float
    detects_condensation: bool
    detection_delay_h: float | None


# --------------------------------------------------------------------- okuma


def read_margins(fixtures_dir: Path, scenario_id: str) -> MarginSeries:
    """Fixture'in `td_margin_k` sutununu ve olcegini okur (pandas'siz).

    Olcek etiket dosyasindan gelir: `duration_h` ve `sample_period_s`. Ornek
    sayisindan turetmek yanlis olurdu — haberlesme boslugu olan senaryolarda
    (S6) satir sayisi sureyi vermez.
    """
    csv_path = fixtures_dir / f"{scenario_id}.csv"
    labels_path = fixtures_dir / f"{scenario_id}.labels.json"
    if not csv_path.exists():
        raise FileNotFoundError(f"fixture yok: {csv_path}")

    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    margins = tuple(float(row[MARGIN_COLUMN]) for row in rows)
    return MarginSeries(
        scenario_id=scenario_id,
        margins=margins,
        period_h=float(labels["sample_period_s"]) / SECONDS_PER_HOUR,
        duration_h=float(labels["duration_h"]),
    )


def read_alarm_column(fixtures_dir: Path, scenario_id: str) -> tuple[frozenset[str], ...]:
    """Fixture'in hazir `alarms` sutunu; kestirme yolun dogrulanmasi icin."""
    csv_path = fixtures_dir / f"{scenario_id}.csv"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return tuple(frozenset(filter(None, (row["alarms"] or "").split(";"))) for row in rows)


# ------------------------------------------------------------------- sayaclar


def flags_below(margins: tuple[float, ...], threshold_k: float) -> tuple[bool, ...]:
    """`limits._environment()` ile AYNI karsilastirma: kesin kucuktur."""
    return tuple(margin < threshold_k for margin in margins)


def count_episodes(flags: tuple[bool, ...]) -> int:
    """Kesintisiz bir aralik TEK alarm sayilir (validate.py `_false_alarms` semantigi)."""
    episodes = 0
    previous = False
    for flag in flags:
        if flag and not previous:
            episodes += 1
        previous = flag
    return episodes


def longest_run(flags: tuple[bool, ...]) -> int:
    best = run = 0
    for flag in flags:
        run = run + 1 if flag else 0
        best = max(best, run)
    return best


def duty_pct(flags: tuple[bool, ...]) -> float:
    return 100.0 * sum(flags) / len(flags) if flags else 0.0


def first_true_index(flags: tuple[bool, ...]) -> int | None:
    for index, flag in enumerate(flags):
        if flag:
            return index
    return None


# -------------------------------------------------------------------- tarama


def sweep(series: MarginSeries, grid: tuple[float, ...] = GRID_K) -> list[SweepRow]:
    """Tek esik degerinin saglikli panodaki yukunu tarar."""
    rows = []
    for threshold in grid:
        flags = flags_below(series.margins, threshold)
        episodes = count_episodes(flags)
        rows.append(
            SweepRow(
                threshold_k=threshold,
                episodes=episodes,
                per_100_panel_days=episodes / series.panel_days * 100.0,
                duty_pct=duty_pct(flags),
                longest_run_h=longest_run(flags) * series.period_h,
            )
        )
    return rows


def sweep_pairs(
    healthy: MarginSeries,
    condense: MarginSeries | None,
    pairs: tuple[tuple[float, float], ...] = CANDIDATE_PAIRS,
) -> list[PairRow]:
    """(uyari, alarm) cifti basina yuk ve — varsa — yogusma senaryosundaki tespit.

    Yuk, docs/12 §3 ile AYNI sekilde toplanir: iki kodun olay sayilari toplanir
    (validate.py her kodun yukselen kenarini ayri sayar).
    """
    rows = []
    for warn_k, alarm_k in pairs:
        warn_flags = flags_below(healthy.margins, warn_k)
        alarm_flags = flags_below(healthy.margins, alarm_k)
        episodes = count_episodes(warn_flags) + count_episodes(alarm_flags)

        detects, delay = False, None
        if condense is not None:
            hit = first_true_index(flags_below(condense.margins, alarm_k))
            detects = hit is not None
            delay = None if hit is None else hit * condense.period_h

        rows.append(
            PairRow(
                warn_k=warn_k,
                alarm_k=alarm_k,
                episodes=episodes,
                per_100_panel_days=episodes / healthy.panel_days * 100.0,
                warn_duty_pct=duty_pct(warn_flags),
                alarm_duty_pct=duty_pct(alarm_flags),
                longest_run_h=longest_run(warn_flags) * healthy.period_h,
                detects_condensation=detects,
                detection_delay_h=delay,
            )
        )
    return rows


# ------------------------------------------------------- kestirme yolun kaniti


def verify_shortcut(fixtures_dir: Path, scenario_id: str, contracts_dir: Path) -> tuple[int, int]:
    """(kontrol edilen satir, uyusmayan satir) — marjdan hesap = fixture alarm sutunu.

    Kestirme yolun tek varsayimi sudur: ciy kodlari YALNIZCA `td_margin_k` alanina
    bakar. Varsayim dogruysa sozlesmedeki esiklerle hesaplanan kodlar, fixture'in
    hazir `alarms` sutunuyla satir satir ayni olmalidir. Uyusmazlik varsa kestirme
    yol gecersizdir ve tarama `--rerun` ile yapilmalidir.
    """
    import yaml

    thresholds = yaml.safe_load((contracts_dir / "alarm-codes.yaml").read_text(encoding="utf-8"))[
        "thresholds"
    ]
    series = read_margins(fixtures_dir, scenario_id)
    fixture_alarms = read_alarm_column(fixtures_dir, scenario_id)

    warn_flags = flags_below(series.margins, float(thresholds[WARN_KEY]))
    alarm_flags = flags_below(series.margins, float(thresholds[ALARM_KEY]))

    mismatched = 0
    for warn, alarm, fired in zip(warn_flags, alarm_flags, fixture_alarms, strict=True):
        computed = {code for code, flag in ((WARN_CODE, warn), (ALARM_CODE, alarm)) if flag}
        if computed != (fired & {WARN_CODE, ALARM_CODE}):
            mismatched += 1
    return len(series.margins), mismatched


def season_load(
    seed: int,
    warn_k: float,
    alarm_k: float,
    contracts_dir: Path | None = None,
    seasons: tuple[str, ...] = ("kis", "gecis", "yaz"),
) -> list[SeasonRow]:
    """Ayni saglikli senaryoyu uc mevsimde kosturur; ciy yuku esige mi havaya mi bagli.

    Senaryo katalogu DEGISTIRILMEZ (`scenarios.py` bu kulvarin disinda): plan nesnesi
    kopyalanir ve yalnizca mevsimi ile baslangic tarihi degistirilir. Fixture da
    yazilmaz — seri bellekte olculur.
    """
    from dataclasses import replace

    from panoalgo.scenarios import (
        SCENARIOS,
        SHOULDER_START,
        SUMMER_START,
        WINTER_START,
        iter_samples,
        plan,
    )

    starts = {"kis": WINTER_START, "gecis": SHOULDER_START, "yaz": SUMMER_START}
    duration_h = SCENARIOS[HEALTHY_SCENARIO].default_duration_h
    panel_days = duration_h / HOURS_PER_DAY

    rows = []
    for season in seasons:
        base = plan(HEALTHY_SCENARIO, seed, duration_h, contracts_dir=contracts_dir)
        scenario = replace(base, spec=replace(base.spec, season=season), start=starts[season])
        margins = tuple(
            sample.payload["env"]["td_margin_k"]
            for sample in iter_samples(scenario)
            if sample.payload is not None
        )
        warn_flags = flags_below(margins, warn_k)
        alarm_flags = flags_below(margins, alarm_k)
        episodes = count_episodes(warn_flags) + count_episodes(alarm_flags)
        ordered = sorted(margins)
        rows.append(
            SeasonRow(
                season=season,
                min_margin_k=ordered[0],
                median_margin_k=_median(ordered),
                max_margin_k=ordered[-1],
                warn_duty_pct=duty_pct(warn_flags),
                alarm_duty_pct=duty_pct(alarm_flags),
                per_100_panel_days=episodes / panel_days * 100.0,
            )
        )
    return rows


def rerun_grid(
    seed: int,
    grid: tuple[float, ...],
    contracts_dir: Path,
    scenario_id: str = HEALTHY_SCENARIO,
) -> tuple[list[SweepRow], float]:
    """Her izgara noktasinda tespiti GERCEKTEN yeniden kosturur; (satirlar, saniye).

    Sozlesme dosyasi DEGISTIRILMEZ: contracts/ dizininin gecici bir kopyasi yazilir
    ve yalnizca `dew_margin_alarm_k` degeri o kopyada degistirilir. Tarama bittiginde
    kopya silinir. Amac esik onermek degil, kestirme yolun sadakatini olcmektir.
    """
    import yaml

    from panoalgo.scenarios import SCENARIOS, build

    duration_h = SCENARIOS[scenario_id].default_duration_h
    panel_days = duration_h / HOURS_PER_DAY
    rows: list[SweepRow] = []
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="dew-sweep-") as workspace:
        for threshold in grid:
            staged = Path(workspace) / f"t{threshold:.1f}"
            shutil.copytree(contracts_dir, staged)
            path = staged / "alarm-codes.yaml"
            contract = yaml.safe_load(path.read_text(encoding="utf-8"))
            contract["thresholds"][ALARM_KEY] = threshold
            path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8", newline="\n")

            frame, _ = build(scenario_id, seed, duration_h, contracts_dir=staged)
            flags = tuple(
                ALARM_CODE in str(value or "").split(";") for value in frame["alarms"].fillna("")
            )
            episodes = count_episodes(flags)
            period_h = duration_h / len(flags)
            rows.append(
                SweepRow(
                    threshold_k=threshold,
                    episodes=episodes,
                    per_100_panel_days=episodes / panel_days * 100.0,
                    duty_pct=duty_pct(flags),
                    longest_run_h=longest_run(flags) * period_h,
                )
            )
    return rows, time.perf_counter() - started


# --------------------------------------------------------------------- rapor


def render_markdown(
    healthy: MarginSeries,
    condense: MarginSeries | None,
    rows: list[SweepRow],
    pairs: list[PairRow],
    contract_warn_k: float,
    contract_alarm_k: float,
    seasons: list[SeasonRow] | None = None,
) -> str:
    """Taramayi docs/05'e yapistirilabilir markdown olarak dondurur."""
    ordered = sorted(healthy.margins)
    lines = [
        f"### Ciy marji dagilimi — `{healthy.scenario_id}` ({healthy.duration_h:.0f} h, "
        f"{len(healthy.margins)} ornek)",
        "",
        f"- en dusuk {ordered[0]:.2f} K · medyan {_median(ordered):.2f} K · "
        f"en yuksek {ordered[-1]:.2f} K",
        f"- marjin negatif oldugu ornek orani: "
        f"%{duty_pct(flags_below(healthy.margins, 0.0)):.1f}",
    ]
    if condense is not None:
        other = sorted(condense.margins)
        lines.append(
            f"- karsilastirma `{condense.scenario_id}` (yogusma enjekte edilmis): "
            f"en dusuk {other[0]:.2f} K · medyan {_median(other):.2f} K · "
            f"en yuksek {other[-1]:.2f} K"
        )

    lines += [
        "",
        f"### Tek esik taramasi — `{healthy.scenario_id}`",
        "",
        "| Esik (K) | Olay | Olay/100 pano/gun | Ayakta kalma | En uzun kesintisiz | Bayat? |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        mark = ""
        if row.threshold_k == contract_warn_k:
            mark = " **(sozlesme: uyari)**"
        elif row.threshold_k == contract_alarm_k:
            mark = " **(sozlesme: alarm)**"
        lines.append(
            f"| {row.threshold_k:.1f}{mark} | {row.episodes} | {row.per_100_panel_days:.1f} | "
            f"%{row.duty_pct:.1f} | {row.longest_run_h:.1f} h | "
            f"{'evet' if row.stale else 'hayir'} |"
        )

    lines += [
        "",
        "### Cift taramasi (uyari + alarm birlikte)",
        "",
        "| Uyari (K) | Alarm (K) | Olay/100 pano/gun | Uyari ayakta | Alarm ayakta | "
        "Yogusma yakalandi mi |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for pair in pairs:
        contract = pair.warn_k == contract_warn_k and pair.alarm_k == contract_alarm_k
        detection = "-" if condense is None else ("evet" if pair.detects_condensation else "HAYIR")
        if condense is not None and pair.detects_condensation and pair.detection_delay_h is not None:
            detection += f" ({pair.detection_delay_h:.2f} h gecikme)"
        lines.append(
            f"| {pair.warn_k:.1f}{' **(sozlesme)**' if contract else ''} | {pair.alarm_k:.1f} | "
            f"{pair.per_100_panel_days:.1f} | %{pair.warn_duty_pct:.1f} | "
            f"%{pair.alarm_duty_pct:.1f} | {detection} |"
        )

    if seasons:
        lines += [
            "",
            f"### Mevsim taramasi — ayni saglikli senaryo, esik sabit "
            f"({contract_warn_k:.1f} / {contract_alarm_k:.1f} K)",
            "",
            "| Mevsim | En dusuk marj | Medyan marj | En yuksek marj | Uyari ayakta | "
            "Alarm ayakta | Olay/100 pano/gun |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for row in seasons:
            lines.append(
                f"| {row.season} | {row.min_margin_k:.2f} K | {row.median_margin_k:.2f} K | "
                f"{row.max_margin_k:.2f} K | %{row.warn_duty_pct:.1f} | "
                f"%{row.alarm_duty_pct:.1f} | {row.per_100_panel_days:.1f} |"
            )

    lines.append("")
    return "\n".join(lines)


def _median(ordered: list[float]) -> float:
    n = len(ordered)
    mid = n // 2
    return ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0


# ----------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ciy noktasi esik taramasi (Kisi A)")
    parser.add_argument("--fixtures", default=None, help="fixture dizini (varsayilan data/fixtures)")
    parser.add_argument("--contracts", default=None, help="sozlesme dizini (varsayilan contracts)")
    parser.add_argument("--out", default=None, help="markdown ciktisi; verilmezse ekrana")
    parser.add_argument("--verify", action="store_true", help="kestirme yolun kanitini yaz")
    parser.add_argument("--rerun", action="store_true", help="tespiti gercekten yeniden kostur")
    parser.add_argument("--seasons", action="store_true", help="ayni senaryoyu uc mevsimde kostur")
    parser.add_argument("--seed", type=int, default=1304)
    args = parser.parse_args(argv)

    import yaml

    fixtures_dir = Path(args.fixtures) if args.fixtures else REPO_ROOT / "data" / "fixtures"
    contracts_dir = Path(args.contracts) if args.contracts else REPO_ROOT / "contracts"
    thresholds = yaml.safe_load((contracts_dir / "alarm-codes.yaml").read_text(encoding="utf-8"))[
        "thresholds"
    ]
    contract_warn_k = float(thresholds[WARN_KEY])
    contract_alarm_k = float(thresholds[ALARM_KEY])

    try:
        healthy = read_margins(fixtures_dir, HEALTHY_SCENARIO)
    except FileNotFoundError as error:
        print(f"{error}\nonce: python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures",
              file=sys.stderr)
        return 1
    try:
        condense: MarginSeries | None = read_margins(fixtures_dir, CONDENSE_SCENARIO)
    except FileNotFoundError:
        condense = None

    if args.verify:
        checked, mismatched = verify_shortcut(fixtures_dir, HEALTHY_SCENARIO, contracts_dir)
        verdict = "GECERLI" if mismatched == 0 else "GECERSIZ"
        print(
            f"kestirme yol {verdict}: {checked} satirin {mismatched} tanesi fixture'in "
            f"hazir alarm sutunuyla uyusmuyor"
        )
        if mismatched:
            return 1

    rows = sweep(healthy)
    if args.rerun:
        rerun_rows, seconds = rerun_grid(args.seed, GRID_K, contracts_dir)
        fast = [(r.threshold_k, r.episodes, round(r.duty_pct, 6)) for r in rows]
        slow = [(r.threshold_k, r.episodes, round(r.duty_pct, 6)) for r in rerun_rows]
        same = "AYNI" if fast == slow else "FARKLI"
        print(f"tam yeniden kosturma: {len(GRID_K)} nokta, {seconds:.1f} s; hizli yolla {same}")
        if fast != slow:
            for quick, slowly in zip(rows, rerun_rows, strict=True):
                if (quick.episodes, quick.duty_pct) != (slowly.episodes, slowly.duty_pct):
                    print(f"  esik {quick.threshold_k}: hizli {quick.episodes} / "
                          f"yeniden {slowly.episodes}", file=sys.stderr)
            return 1

    seasons = (
        season_load(args.seed, contract_warn_k, contract_alarm_k, contracts_dir)
        if args.seasons
        else None
    )
    report = render_markdown(healthy, condense, rows, sweep_pairs(healthy, condense),
                             contract_warn_k, contract_alarm_k, seasons)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8", newline="\n")
        print(f"tarama yazildi -> {out_path}")
        return 0

    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
