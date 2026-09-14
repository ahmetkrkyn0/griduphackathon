"""Etiketli senaryo ureteci (TA2 Adim 7, Kisi A): S0-S9 + dogrulama etiketleri.

Bu modul, tespit basarisini SAYIYLA olculebilir kilan seydir. Her senaryo
  (a) fiziksel bir ariza ENJEKTE eder (alarm uretmez!),
  (b) uretilen veriyi kenar tespit boru hattindan gecirir,
  (c) contracts/scenario-labels.schema.json'a uyan bir ETIKET dosyasi yazar.

Etiket, "ne zaman ne olmasi gerekiyordu"yu soyler; algoritmanin ne buldugu ise
verinin kendisindedir. Ikisini karsilastiran scripts/validate.py recall, precision
ve ONE ALMA SURESINI hesaplar (PLAN.md T4.1).

ENJEKSIYON FELSEFESI: senaryo hicbir yerde "su alarm ciksin" demez; K'yi buyutur,
yuku artirir, sensoru bozar. Alarm cikacak mi, ne zaman cikacak — bunu tespit
katmanlari belirler. Aksi halde test, algoritmaya cevabi fisildamis olurdu.

ORNEKLEME: disa aktarim 15 dakikadir (rapor 15.2: "Excel formatiyla uyum icin
15 dk disa aktarim"). Kenar gercekte 1 s isler, merkeze 10 s ozet gonderir; fixture
boyutu (PLAN.md kural 4: <= 1 MB) bu cozunurlukle tutturulur.

CLI:
    python -m panoalgo.scenarios --list
    python -m panoalgo.scenarios --build S1_loose_conn --seed 1304
    python -m panoalgo.scenarios --all --out data/fixtures
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .detect import load_thresholds
from .edge import EdgePipeline
from .generator import PanelSimulator, format_pano_id

EXPORT_PERIOD_S = 900.0          # 15 dk (rapor 15.2 Excel uyumu)
SECONDS_PER_HOUR = 3600.0
DEFAULT_PANO_INDEX = 1
LV_PANEL_TYPE = "1600kVA-dahili"
MV_PANEL_TYPE = "OG-hucre"

# Mevsim baslangiclari: yogusma kis gecelerinde, isil senaryolar yaz yukunde anlamli.
SUMMER_START = datetime(2026, 7, 6, 0, 0, tzinfo=timezone.utc)   # Pazartesi
WINTER_START = datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)   # Pazartesi


@dataclass(frozen=True)
class ScenarioSpec:
    """Bir senaryonun enjeksiyonu ve beklenen tespiti."""

    text: str
    default_duration_h: float
    label_type: str | None = None          # None = etiketsiz (S0)
    point: str = "PANEL"
    severity: str | None = None
    expect: tuple[str, ...] = ()
    not_expect: tuple[str, ...] = ()
    season: str = "yaz"
    profile: str = "karma"
    medium_voltage: bool = False
    params: dict = field(default_factory=dict)


TARGET_POINT = "DSYA3_L2"

SCENARIOS: dict[str, ScenarioSpec] = {
    "S0_normal": ScenarioSpec(
        text="Saglikli pano — yanlis alarm olcumunun tabani",
        default_duration_h=168.0,
    ),
    "S1_loose_conn": ScenarioSpec(
        text="Gevsek baglanti: K yavasca %200 artar (rapor 15.2)",
        default_duration_h=720.0,
        label_type="loose_connection",
        point=TARGET_POINT,
        severity="P2",
        expect=("ALM-K-WARN", "ALM-K-ALM", "ALM-THR-TERM-WARN", "ALM-THR-TERM-ALM"),
        not_expect=("ALM-I-OVER",),
        # load_multiplier 0.8: senaryo NORMAL yukte kurulur, yaz tepe yukunde degil.
        # Sebep fiziksel: sabit 70 K esigi ancak dT o sinira dayaninca uyarir; pano
        # surekli tepe yukte kosuyorsa saglikli dT zaten 40 K'ya yakindir ve K'nin
        # 1.6'yi gecmesi ile 70 K'nin asilmasi neredeyse ayni ana duser. Gercek
        # sahada panolar yilin cogunu tepe yukun altinda gecirir; erken uyarinin
        # degeri tam olarak bu bolgede ortaya cikar.
        params={"k_growth_pct": 200, "load_multiplier": 0.8},
    ),
    "S2_overload": ScenarioSpec(
        text="Asiri yuk: akim anma degerinin ustunde, K SABIT (ariza degil)",
        default_duration_h=168.0,
        label_type="overload",
        point="PANEL",
        severity="P2",
        expect=("ALM-I-OVER",),
        not_expect=("ALM-K-ALM", "ALM-K-WARN"),
        params={"load_multiplier": 1.35},
    ),
    "S3_condense": ScenarioSpec(
        text="Yogusma: kis gecesi nem yukselir, yuzey ciy noktasinin altina iner",
        default_duration_h=168.0,
        label_type="condensation",
        point="PANEL",
        severity="P2",
        expect=("ALM-DEW-WARN", "ALM-DEW-ALM"),
        not_expect=("ALM-K-ALM",),
        season="kis",
        params={"humidity_offset_pct": 25},
    ),
    "S4_arc": ScenarioSpec(
        text="Ark olayi: TVOC-2 trip sayaci artar",
        default_duration_h=72.0,
        label_type="arc",
        point="PANEL",
        severity="P1",
        expect=("ALM-ARC-TRIP",),
        params={"trips": 1},
    ),
    "S5_prot_health": ScenarioSpec(
        text="Koruma sagligi kaybi: pano sessizce korumasiz",
        default_duration_h=72.0,
        label_type="protection_health_loss",
        point="PANEL",
        severity="P1",
        expect=("ALM-PROT-HEALTH",),
    ),
    "S6_comms_loss": ScenarioSpec(
        text="Haberlesme kopmasi: saatler suren veri boslugu",
        default_duration_h=168.0,
        label_type="comms_loss",
        point="SYSTEM",
        severity="SYS",
        # ALM-COMMS-LOST merkezde uretilir (alarm_service.py); kenar onu basmaz.
        expect=("ALM-COMMS-LOST",),
        params={"gap_h": 6},
    ),
    "S7_harmonic": ScenarioSpec(
        text="Harmonik: akim THD ve notr akimi birlikte artar",
        default_duration_h=168.0,
        label_type="harmonic",
        point="GIRIS_N",
        severity="P3",
        expect=("ALM-NEUTRAL-THD",),
        not_expect=("ALM-K-ALM",),
        params={"thd_multiplier": 3.5},
    ),
    "S8_sensor_fault": ScenarioSpec(
        text="Sensor arizalari: donma, suruklenme, yerinden dusme (ariza DEGIL)",
        default_duration_h=168.0,
        label_type="sensor_dropped",
        point="DSYA6_L1",
        severity="SYS",
        expect=("ALM-DQ-BELOW-AMBIENT",),
        not_expect=("ALM-THR-TERM-ALM", "ALM-K-ALM"),
    ),
    "S9_pd_trend": ScenarioSpec(
        text="PD trendi (OG): darbe sayisi ve faz kumelenmesi artar",
        default_duration_h=168.0,
        label_type="pd_trend",
        point="PANEL",
        severity="P3",
        expect=("ALM-PD-TREND",),
        medium_voltage=True,
    ),
}


def list_scenarios() -> list[dict]:
    """Katalog: kimlik, aciklama, varsayilan sure."""
    return [
        {"scenario_id": key, "text": spec.text, "default_duration_h": spec.default_duration_h}
        for key, spec in SCENARIOS.items()
    ]


def build(
    scenario_id: str,
    seed: int,
    duration_h: float,
    contracts_dir: Path | None = None,
    generated_at: datetime | None = None,
):
    """Senaryoyu kosturur; (DataFrame, etiket sozlugu) doner.

    Etiket sozlugu contracts/scenario-labels.schema.json'a uyar.
    """
    import pandas as pd

    spec = SCENARIOS.get(scenario_id)
    if spec is None:
        raise ValueError(f"bilinmeyen senaryo: {scenario_id!r}; gecerli: {sorted(SCENARIOS)}")
    if duration_h <= 0.0:
        raise ValueError(f"duration_h pozitif olmali: {duration_h}")

    thresholds = load_thresholds(contracts_dir)
    l0_limit = float(thresholds["term_rise_alarm_k"])
    baseline_h = min(float(thresholds["baseline_learning_days"]) * 24.0, duration_h / 3.0)

    start = WINTER_START if spec.season == "kis" else SUMMER_START
    pano_id = format_pano_id("SIM", DEFAULT_PANO_INDEX)
    sim = PanelSimulator(
        pano_id=pano_id,
        seed=seed,
        profile=spec.profile,
        start=start,
        contracts_dir=contracts_dir,
        medium_voltage=spec.medium_voltage,
    )
    pipeline = EdgePipeline(profile=spec.profile, contracts_dir=contracts_dir)

    rows: list[dict] = []
    l0_breach_at: str | None = None
    injected_from: datetime | None = None
    steps = int(duration_h * SECONDS_PER_HOUR / EXPORT_PERIOD_S)

    for index in range(steps):
        hours = index * EXPORT_PERIOD_S / SECONDS_PER_HOUR
        if not pipeline.baseline_frozen and hours >= baseline_h:
            pipeline.freeze_baselines()

        if hours >= baseline_h:
            if injected_from is None:
                injected_from = start + timedelta(hours=hours)
            _inject(spec, sim, hours, baseline_h, duration_h)

        payload = pipeline.process(sim.step(EXPORT_PERIOD_S))

        if _in_comms_gap(spec, hours, baseline_h):
            continue  # veri YOK; sahte deger uretmiyoruz

        row = _row(payload, spec)
        rows.append(row)
        if l0_breach_at is None and row["worst_dt_c"] > l0_limit:
            l0_breach_at = row["ts"]

    frame = pd.DataFrame(rows)
    labels = _labels(
        spec, scenario_id, seed, pano_id, duration_h, start, injected_from, l0_breach_at, generated_at
    )
    return frame, labels


# --------------------------------------------------------------- enjeksiyon


def _inject(spec: ScenarioSpec, sim: PanelSimulator, hours: float, baseline_h: float, duration_h: float) -> None:
    """Fiziksel parametreyi senaryoya gore surer. Alarm URETMEZ."""
    params = spec.params
    progress = _progress(hours, baseline_h, duration_h)

    if "load_multiplier" in params:
        sim.set_load_multiplier(params["load_multiplier"])

    if spec.label_type == "loose_connection":
        growth = 1.0 + (params["k_growth_pct"] / 100.0) * progress
        sim.set_k_multiplier(spec.point, growth)
    elif spec.label_type == "condensation":
        sim.set_humidity_offset(params["humidity_offset_pct"])
    elif spec.label_type == "arc":
        if sim._tvoc_trips < params["trips"]:  # noqa: SLF001 - ayni kulvarin modulu
            sim.trigger_arc_trip()
    elif spec.label_type == "protection_health_loss":
        sim.set_protection_health(False)
    elif spec.label_type == "harmonic":
        sim.set_thd_multiplier(params["thd_multiplier"])
    elif spec.label_type == "sensor_dropped":
        sim.set_sensor_fault("DSYA6_L1", "dropped")
        sim.set_sensor_fault("DSYA5_L2", "frozen")
        sim.set_sensor_fault("DSYA4_L3", "drift")
    elif spec.label_type == "pd_trend":
        sim.set_pd_activity(min(1.0, progress))


def _progress(hours: float, baseline_h: float, duration_h: float) -> float:
    """Enjeksiyon penceresi icinde 0 -> 1 ilerleme."""
    span = max(duration_h - baseline_h, 1e-9)
    return min(1.0, max(0.0, (hours - baseline_h) / span))


def _in_comms_gap(spec: ScenarioSpec, hours: float, baseline_h: float) -> bool:
    if spec.label_type != "comms_loss":
        return False
    gap_h = float(spec.params["gap_h"])
    return baseline_h <= hours < baseline_h + gap_h


# ------------------------------------------------------------------- cikti


def _row(payload: dict, spec: ScenarioSpec) -> dict:
    points = payload["t_conn"]
    worst = max(points, key=lambda p: p["dt_c"])
    ratios = [p["k_ratio"] for p in points if p.get("k_ratio") is not None]
    ttls = [p["ttl_h"] for p in points if p.get("ttl_h") is not None]
    target = next((p for p in points if p["pt"] == spec.point), None)
    elec, env, pd_block = payload["elec"], payload["env"], payload.get("pd")

    return {
        "ts": payload["ts"],
        "seq": payload["seq"],
        "i_ph_max": max(elec["i_ph"]),
        "i_n": elec["i_n"],
        "thd_i_mean": sum(elec["thd_i"]) / len(elec["thd_i"]),
        "t_low_c": env["t_low_c"],
        "td_margin_k": env["td_margin_k"],
        "worst_point": worst["pt"],
        "worst_dt_c": worst["dt_c"],
        "max_k_ratio": max(ratios) if ratios else 1.0,
        "min_ttl_h": min(ttls) if ttls else None,
        "target_dt_c": target["dt_c"] if target else None,
        "target_k_ratio": target.get("k_ratio") if target else None,
        "q_any": max(p["q"] for p in points),
        "pd_pps": pd_block["pps"] if pd_block else 0.0,
        "risk_score": payload["risk"]["score"],
        "risk_mode": payload["risk"]["mode"],
        "alarms": ";".join(payload["alarms"]),
    }


def _labels(
    spec: ScenarioSpec,
    scenario_id: str,
    seed: int,
    pano_id: str,
    duration_h: float,
    start: datetime,
    injected_from: datetime | None,
    l0_breach_at: str | None,
    generated_at: datetime | None,
) -> dict:
    stamped = (generated_at or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    labels: list[dict] = []

    if spec.label_type is not None and injected_from is not None:
        entry = {
            "t_start": injected_from.isoformat(timespec="seconds"),
            "t_end": (start + timedelta(hours=duration_h)).isoformat(timespec="seconds"),
            "type": spec.label_type,
            "point": spec.point,
            "expect": list(spec.expect),
        }
        if spec.severity:
            entry["severity"] = spec.severity
        if spec.not_expect:
            entry["not_expect"] = list(spec.not_expect)
        if spec.params:
            entry["params"] = dict(spec.params)
        entry["l0_breach_at"] = l0_breach_at
        labels.append(entry)

    return {
        "scenario_id": scenario_id,
        "seed": seed,
        "pano_id": pano_id,
        "pano_type": MV_PANEL_TYPE if spec.medium_voltage else LV_PANEL_TYPE,
        "duration_h": duration_h,
        "sample_period_s": EXPORT_PERIOD_S,
        "generated_at": stamped,
        "profile": spec.profile,
        "season": spec.season,
        "data_file": f"{scenario_id}.csv",
        "labels": labels,
    }


def write_fixture(
    scenario_id: str,
    seed: int,
    duration_h: float | None = None,
    out_dir: Path | None = None,
    contracts_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Senaryoyu uretip CSV + etiket JSON olarak yazar; (csv, labels) yolunu doner."""
    spec = SCENARIOS[scenario_id]
    duration = duration_h if duration_h is not None else spec.default_duration_h
    frame, labels = build(scenario_id, seed, duration, contracts_dir)

    directory = Path(out_dir) if out_dir else _default_fixture_dir()
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / f"{scenario_id}.csv"
    labels_path = directory / f"{scenario_id}.labels.json"

    frame.to_csv(csv_path, index=False, lineterminator="\n", float_format="%.4g")
    labels_path.write_text(json.dumps(labels, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return csv_path, labels_path


def _default_fixture_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "fixtures"


# --------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Etiketli senaryo ureteci (Kisi A)")
    parser.add_argument("--list", action="store_true", help="senaryo katalogunu yaz")
    parser.add_argument("--build", metavar="SCENARIO_ID", help="tek senaryo uret")
    parser.add_argument("--all", action="store_true", help="tum senaryolari uret")
    parser.add_argument("--seed", type=int, default=1304)
    parser.add_argument("--duration-h", type=float, default=None)
    parser.add_argument("--out", default=None, help="cikti dizini (varsayilan data/fixtures)")
    args = parser.parse_args(argv)

    if args.list:
        for entry in list_scenarios():
            print(f"{entry['scenario_id']:<16} {entry['default_duration_h']:>7.0f} h  {entry['text']}")
        return 0

    targets = list(SCENARIOS) if args.all else ([args.build] if args.build else [])
    if not targets:
        parser.print_help()
        return 1

    out_dir = Path(args.out) if args.out else None
    for scenario_id in targets:
        csv_path, labels_path = write_fixture(scenario_id, args.seed, args.duration_h, out_dir)
        size_kb = csv_path.stat().st_size / 1024
        print(f"{scenario_id:<16} -> {csv_path.name} ({size_kb:.0f} KB), {labels_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
