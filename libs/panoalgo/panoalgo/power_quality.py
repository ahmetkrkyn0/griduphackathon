"""EN 50160 standardina gore guc kalitesi (gerilim toleransi ve dengesizlik) degerlendiricisi.

Toplanan fakat daha once kurallarda tuketilmeyen `u_ph` (faz gerilimleri) ve
`unbal_pct` (faz dengesizligi) olcumlerini EN 50160'a gore analiz eder.

Referans:
  - EN 50160:2010 + A1:2015 "Voltage characteristics of electricity supplied by public electricity networks"
  - Nominal faz-notr gerilimi: Un = 230 V
  - Normal calisma araligi: Un +- 10% (207.0 V .. 253.0 V) haftanin %95'inde
  - Genisletilmis alt sinir: Un - 15% (195.5 V)
  - Dengesizlik siniri: unbal_pct <= 2.0% (uyari: >2.0%, kritik: >5.0%)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

NOMINAL_VOLTAGE_V = 230.0
TOLERANCE_NORMAL_PCT = 0.10   # +-10% (207.0 - 253.0 V)
TOLERANCE_EXTREME_PCT = 0.15  # -15% (195.5 V)

V_MIN_NORMAL = NOMINAL_VOLTAGE_V * (1.0 - TOLERANCE_NORMAL_PCT)   # 207.0 V
V_MAX_NORMAL = NOMINAL_VOLTAGE_V * (1.0 + TOLERANCE_NORMAL_PCT)   # 253.0 V
V_MIN_EXTREME = NOMINAL_VOLTAGE_V * (1.0 - TOLERANCE_EXTREME_PCT) # 195.5 V

UNBALANCE_WARN_PCT = 2.0  # EN 50160 standardi %2 siniri
UNBALANCE_ALARM_PCT = 5.0 # Kritik dengesizlik siniri

QualityStatus = Literal["COMPLIANT", "WARN", "VIOLATION"]


@dataclass(frozen=True)
class VoltageEvaluation:
    phase_index: int
    voltage_v: float
    deviation_pct: float
    status: Literal["NORMAL", "VOLTAGE_SAG", "VOLTAGE_SWELL"]


@dataclass(frozen=True)
class PowerQualityReport:
    compliant: bool
    status: QualityStatus
    score: int  # 0 - 100
    u_ph: tuple[float, float, float]
    phases: tuple[VoltageEvaluation, VoltageEvaluation, VoltageEvaluation]
    unbal_pct: float
    unbal_status: Literal["NORMAL", "UNBALANCE_WARN", "UNBALANCE_ALARM"]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "compliant": self.compliant,
            "status": self.status,
            "score": self.score,
            "u_ph": list(self.u_ph),
            "phases": [
                {
                    "phase": p.phase_index + 1,
                    "voltage_v": p.voltage_v,
                    "deviation_pct": round(p.deviation_pct, 2),
                    "status": p.status,
                }
                for p in self.phases
            ],
            "unbal_pct": self.unbal_pct,
            "unbal_status": self.unbal_status,
            "notes": self.notes,
        }


def evaluate_power_quality(
    u_ph: tuple[float, float, float] | list[float],
    unbal_pct: float = 0.0,
    thd_i: tuple[float, float, float] | list[float] | None = None,
) -> PowerQualityReport:
    """EN 50160 standartlarina gore gerilim ve dengesizlik degerlendirmesi yapar."""
    if len(u_ph) != 3:
        raise ValueError(f"u_ph tam olarak 3 faz gerilimi icermelidir, alinan: {len(u_ph)}")

    phase_evals: list[VoltageEvaluation] = []
    notes: list[str] = []
    penalty = 0

    for i, v in enumerate(u_ph):
        dev = ((v - NOMINAL_VOLTAGE_V) / NOMINAL_VOLTAGE_V) * 100.0
        if v < V_MIN_NORMAL:
            v_status: Literal["NORMAL", "VOLTAGE_SAG", "VOLTAGE_SWELL"] = "VOLTAGE_SAG"
            penalty += 25 if v >= V_MIN_EXTREME else 40
            notes.append(f"L{i+1} gerilim cokmesi ({v:.1f} V < {V_MIN_NORMAL:.1f} V, %{dev:.1f})")
        elif v > V_MAX_NORMAL:
            v_status = "VOLTAGE_SWELL"
            penalty += 35
            notes.append(f"L{i+1} asiri gerilim ({v:.1f} V > {V_MAX_NORMAL:.1f} V, +%{dev:.1f})")
        else:
            v_status = "NORMAL"

        phase_evals.append(
            VoltageEvaluation(
                phase_index=i,
                voltage_v=round(float(v), 2),
                deviation_pct=round(dev, 2),
                status=v_status,
            )
        )

    # Dengesizlik (unbalance) kontrolu
    if unbal_pct > UNBALANCE_ALARM_PCT:
        unbal_status = "UNBALANCE_ALARM"
        penalty += 30
        notes.append(f"Kritik akim dengesizligi (%{unbal_pct:.1f} > %{UNBALANCE_ALARM_PCT:.1f})")
    elif unbal_pct > UNBALANCE_WARN_PCT:
        unbal_status = "UNBALANCE_WARN"
        penalty += 15
        notes.append(f"EN 50160 dengesizlik esigi asildi (%{unbal_pct:.1f} > %{UNBALANCE_WARN_PCT:.1f})")
    else:
        unbal_status = "NORMAL"

    score = max(0, 100 - penalty)
    if penalty == 0:
        status: QualityStatus = "COMPLIANT"
        compliant = True
    elif penalty <= 25:
        status = "WARN"
        compliant = True
    else:
        status = "VIOLATION"
        compliant = False

    return PowerQualityReport(
        compliant=compliant,
        status=status,
        score=score,
        u_ph=(float(u_ph[0]), float(u_ph[1]), float(u_ph[2])),
        phases=(phase_evals[0], phase_evals[1], phase_evals[2]),
        unbal_pct=round(float(unbal_pct), 2),
        unbal_status=unbal_status,
        notes=notes,
    )
