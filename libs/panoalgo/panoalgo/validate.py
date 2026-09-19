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
  model      Senaryonun uretildigi fizik, dedektorun (detect.py) VARSAYDIGI fizikle
             ayni mi: `eslesen` / `uyumsuz`. Etiketteki `unmodelled_physics` alanindan
             okunur; alan yoksa `eslesen`. Bu ayrim olmadan "duyarlilik 1,00" cumlesi
             yaniltici olur, cunku eslesen modelde kestirici kendi ileri modelini ters
             ceviriyordur. Gerekce: contracts/changes/2026-09-19-model-uyumsuzlugu-senaryolari.md
  prognoz    Tahmin edilen kalan omur (min_ttl_h) ile GERCEK kalan omur
             (l0_breach_at - t) karsilastirilir: alfa-lambda, prognostic horizon,
             goreli dogruluk, yakinsama. Olcutlerin tanimi prognostics.py'dedir.

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

from . import prognostics
from .detect import default_contracts_dir

FIXED_THRESHOLD_CODE = "ALM-THR-TERM-ALM"  # sabit 70 K esigi
TTL_ALARM_CODE = "ALM-TTL-14D"  # ttl tahmininin ALARMA dondugu kod (sozlesme biti 6)

# Merkezde uretilen kodlar kenar fixture'inda ASLA gorunmez; recall'da "kacan" olarak
# sayilmalari yaniltici olur. ALM-COMMS-LOST'u backend/app/alarm_service.py heartbeat
# zaman asimindan uretir (kenar veriyi zaten gonderemiyordur).
CENTRE_ONLY_CODES = frozenset({"ALM-COMMS-LOST"})
SECONDS_PER_HOUR = 3600.0

# Etiket kokundeki alan adi (contracts/scenario-labels.schema.json). Bu modul
# panoalgo.scenarios'tan HICBIR SEY import etmez — olcum, ureteci taniyan koddan
# bagimsiz kalmalidir (modul basindaki durustluk notu). Bu yuzden "hangi senaryo
# uyumsuz" bilgisi senaryo kimliginden TURETILMEZ, ETIKETTEN OKUNUR.
UNMODELLED_PHYSICS_KEY = "unmodelled_physics"

# Insan okunur fizik adlari — docs/12 SAF ASCII'dir, bu tablo da oyle.
PHYSICS_TEXT: dict[str, str] = {
    "thermal_coupling": "terminal grubu ici isil kuplaj (dedektor: tek nokta)",
    "load_dependent_tau": "yuke bagli zaman sabiti (dedektor: tau sabit)",
    "second_time_constant": "ikinci (yavas) isil kutup (dedektor: birinci mertebe)",
    "sensor_nonlinearity": "olcum zinciri dogrusalsizligi (dedektor: dogrusal olcum)",
}


@dataclass(frozen=True)
class ScenarioResult:
    """Bir senaryonun olcum sonucu."""

    scenario_id: str
    duration_h: float
    samples: int
    unmodelled_physics: tuple[str, ...]
    expected: int
    detected: int
    forbidden_fired: tuple[str, ...]
    missed: tuple[str, ...]
    centre_only: tuple[str, ...]
    lead_time_h: float | None
    l0_breach_at: str | None
    first_l1_at: str | None
    # `first_l1_at` anindaki L1 kodlari. AYRI BIR ALAN OLMASININ SEBEBI OLCULDU:
    # one alma suresi "ilk L1 kodu" ile tanimlidir ve ALM-TTL-14D de bir L1 kodudur
    # (contracts/alarm-codes.yaml). S1'de sayiyi tetikleyen kod ALM-TTL-14D'dir
    # (13 Tem 22:15), K indeksi 41 saat SONRA uyarir (ALM-K-WARN, 15 Tem 10:45).
    # Yani manset "209 saat" tespit katmanindan degil PROGNOZDAN gelir — ve docs/12
    # §4 ayni prognozun geri testinin KOTU oldugunu yayinliyor. Bu celiski sutunda
    # gorunmeden tablo dogru okunamaz.
    first_l1_codes: tuple[str, ...]
    false_alarm_codes: tuple[str, ...]
    false_alarms_per_100_panel_days: float
    prognosis: prognostics.PrognosisResult | None
    # Sinir hic asilmadigi halde uretilen ttl tahminlerinin sayisi. Bu bir PROGNOZ
    # YANLIS-ALARMIDIR ve saklanmaz; docs/05'in "bilinen sinirlar" bolumune girer.
    false_prognoses: int
    # Bu tahminlerin kacinin gercekten ALM-TTL-14D alarmina dondugu. §3'teki yanlis
    # alarm sayaci bunlari GORMEZ: etiket penceresinin ICINDE cikiyorlar.
    false_prognosis_alarms: int

    @property
    def recall(self) -> float | None:
        return None if self.expected == 0 else self.detected / self.expected

    @property
    def precision_ok(self) -> bool:
        return not self.forbidden_fired

    @property
    def model_match(self) -> bool:
        """Senaryo dedektorun varsaydigi fizikle mi uretildi?"""
        return not self.unmodelled_physics

    @property
    def model_text(self) -> str:
        return "eslesen" if self.model_match else "uyumsuz"


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
    first_l1_codes: tuple[str, ...] = ()

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
            mask = window["alarm_set"].map(lambda s: bool(s & l1_codes))
            hit = window.loc[mask, "ts"]
            if not hit.empty:
                first_l1_at = hit.iloc[0].isoformat()
                lead_time_h = (pd.Timestamp(breach) - hit.iloc[0]).total_seconds() / SECONDS_PER_HOUR
                first_l1_codes = tuple(sorted(window.loc[mask, "alarm_set"].iloc[0] & l1_codes))

    false_codes, per_100 = _false_alarms(frame, labels, duration_h)
    prognosis, false_prognoses, false_prognosis_alarms = _prognosis(
        frame, labels["scenario_id"], l0_breach_at
    )
    return ScenarioResult(
        scenario_id=labels["scenario_id"],
        duration_h=duration_h,
        samples=len(frame),
        unmodelled_physics=tuple(labels.get(UNMODELLED_PHYSICS_KEY, ())),
        expected=expected_total,
        detected=detected_total,
        forbidden_fired=tuple(sorted(forbidden)),
        missed=tuple(sorted(missed)),
        centre_only=tuple(sorted(centre)),
        lead_time_h=lead_time_h,
        l0_breach_at=l0_breach_at,
        first_l1_at=first_l1_at,
        first_l1_codes=first_l1_codes,
        false_alarm_codes=false_codes,
        false_alarms_per_100_panel_days=per_100,
        prognosis=prognosis,
        false_prognoses=false_prognoses,
        false_prognosis_alarms=false_prognosis_alarms,
    )


def _prognosis(frame, scenario_id: str, l0_breach_at: str | None):
    """(prognoz geri testi, prognoz yanlis-alarm sayisi, bunlarin alarma donen sayisi).

    Tahmin serisi fixture'in `min_ttl_h` sutunudur — kenarin O AN yayinladigi ttl_h.
    Gercek kalan omur etiketten gelir (`l0_breach_at`), yani tahminin kendisinden
    BAGIMSIZ bir kaynaktan; modulun basindaki durustluk notu burada da gecerlidir.

    Sinir hic asilmadiysa (l0_breach_at yok) hicbir tahmin DOGRU olamaz: gercek kalan
    omur sonsuzdur, oysa sistem sonlu bir sure soylemistir. Bu durumda geri test
    yapilmaz, tahminler SAYILIR ve yanlis-alarm olarak raporlanir.
    """
    import pandas as pd

    if "min_ttl_h" not in frame:
        return None, 0, 0

    ttl = frame["min_ttl_h"]
    if l0_breach_at is None:
        fired = frame["alarm_set"].map(lambda s: TTL_ALARM_CODE in s)
        return None, int(ttl.notna().sum()), int(fired.sum())

    start = frame["ts"].iloc[0]
    hours = ((frame["ts"] - start).dt.total_seconds() / SECONDS_PER_HOUR).tolist()
    values = [None if pd.isna(v) else float(v) for v in ttl]
    eol_hours = (pd.Timestamp(l0_breach_at) - start).total_seconds() / SECONDS_PER_HOUR
    points, late = prognostics.predictions_from_series(hours, values, eol_hours)
    return prognostics.backtest(scenario_id, points, late), 0, 0


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


def _scenario_order(scenario_id: str) -> tuple[int, str]:
    """S10 -> 10, S2 -> 2. SAYISAL siralama sart.

    Duz metin siralamasinda "S10_coupling" < "S1_loose_conn" cikar ('0' = 48 <
    '_' = 95), yani uyumsuz senaryolar eslesen bloklarin ORTASINA serpilirdi.
    """
    head = scenario_id.split("_", 1)[0]
    return (int(head[1:]), scenario_id) if head[1:].isdigit() else (10**6, scenario_id)


def order_results(results: list[ScenarioResult]) -> list[ScenarioResult]:
    """Once ESLESEN blok, sonra UYUMSUZ blok; her blok kendi icinde sayisal sirada.

    Siralama RENDERER'IN ISIDIR, cagiranin degil: docs/12'nin blok yapisi bir
    sunum karari ve tek bir yerde yasamali. validate_all dosya adina gore glob
    sirasi verir; oradan gelen sira burada yeniden kurulur.
    """
    return sorted(results, key=lambda r: (not r.model_match, _scenario_order(r.scenario_id)))


def render_markdown(results: list[ScenarioResult], contracts_dir: Path | None = None) -> str:
    """docs/12-dogrulama-sonuclari.md govdesini uretir."""
    results = order_results(results)
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
        "Tablo IKI BLOKTUR. `eslesen` satirlarda uretec ile dedektor AYNI isil",
        "denklemi kullanir; `uyumsuz` satirlarda uretece dedektorun varsaymadigi bir",
        "fizik eklenmistir (bkz. Bolum 1.1). Ikisi ayni sayi degildir ve birlikte",
        "okunmalidir: eslesen blok yontemin TAVANINI, uyumsuz blok SINIRINI olcer.",
        "",
        "| Senaryo | Model | Sure (s) | Ornek | Beklenen | Yakalanan | Recall | Yasakli alarm | Kacan |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        recall = "-" if r.recall is None else f"{r.recall:.2f}"
        forbidden = ", ".join(r.forbidden_fired) or "yok"
        missed = ", ".join(r.missed) or "yok"
        if r.centre_only:
            missed += f" (merkezde: {', '.join(r.centre_only)})"
        lines.append(
            f"| `{r.scenario_id}` | {r.model_text} | {r.duration_h:.0f} | {r.samples} | {r.expected} | "
            f"{r.detected} | {recall} | {forbidden} | {missed} |"
        )

    lines += _model_mismatch_section(results)

    lines += [
        "",
        "## 2. Sabit 70 K esigi ile karsilastirma",
        "",
        f"Sabit esik = `thresholds.term_rise_alarm_k` = {thresholds['term_rise_alarm_k']} K "
        f"(`{FIXED_THRESHOLD_CODE}`). Fizik katmani (L1) bu esikten kac saat once uyardi?",
        "",
        "| Senaryo | Model | Ilk L1 tespiti | Tetikleyen kod | 70 K ihlali | One alma (saat) | One alma (gun) |",
        "|---|---|---|---|---|---:|---:|",
    ]
    ttl_driven = []
    for r in results:
        if r.l0_breach_at is None:
            continue
        lead_h = "-" if r.lead_time_h is None else f"{r.lead_time_h:.1f}"
        lead_d = "-" if r.lead_time_h is None else f"{r.lead_time_h / 24.0:.1f}"
        codes = ", ".join(f"`{c}`" for c in r.first_l1_codes) or "-"
        if TTL_ALARM_CODE in r.first_l1_codes:
            ttl_driven.append(r.scenario_id)
        lines.append(
            f"| `{r.scenario_id}` | {r.model_text} | {r.first_l1_at or 'tespit yok'} | {codes} | "
            f"{r.l0_breach_at} | {lead_h} | {lead_d} |"
        )
    if ttl_driven:
        lines += [
            "",
            f"**Durustluk kaydi — sayiyi tetikleyen kod.** `{TTL_ALARM_CODE}` de bir L1",
            "kodudur (`contracts/alarm-codes.yaml`), dolayisiyla \"ilk L1 tespiti\" onu da",
            "sayar. Yukaridaki senaryolarda one alma suresini tetikleyen kod TESPIT degil",
            f"PROGNOZ: {', '.join('`' + i + '`' for i in ttl_driven)}. Ayni prognozun geri",
            "testi Bolum 4'te yayimlaniyor ve **kotu** (koni icinde kalma orani dusuk,",
            "ufuk yok). Yani bu satirlardaki sure, guvenilirligi ayni dosyada olculup",
            "zayif bulunmus bir tahminden geliyor. K indeksi esiginin (`ALM-K-WARN`)",
            "kendi uyari ani ayri bir sayidir ve daha gectir; ikisi karistirilmamalidir.",
        ]
    absent = [r for r in results if r.l0_breach_at is None and not r.model_match]
    if absent:
        lines += [
            "",
            "Bu tabloda YER ALMAYAN uyumsuz senaryolar sabit esigi HIC tetiklemedi "
            f"({', '.join('`' + r.scenario_id + '`' for r in absent)}): sabit esik o",
            "senaryolarda ariziyi tamamen kacirdi, dolayisiyla 'one alma' tanimsizdir.",
            "Bu bir olcum eksigi degil, olcumun kendisidir.",
        ]

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
        "| Senaryo | Model | Yanlis alarm / 100 pano / gun | Cikan kodlar |",
        "|---|---|---:|---|",
    ]
    for r in results:
        codes = ", ".join(r.false_alarm_codes) or "yok"
        lines.append(
            f"| `{r.scenario_id}` | {r.model_text} | "
            f"{r.false_alarms_per_100_panel_days:.1f} | {codes} |"
        )

    lines += _prognosis_section(results)

    lines += ["", "## 5. Nasil yeniden uretilir", "", "```bash",
              "python -m panoalgo.scenarios --all --seed 1304 --out data/fixtures",
              "python scripts/validate.py --out docs/12-dogrulama-sonuclari.md", "```", ""]
    return "\n".join(lines)


def _model_mismatch_section(results: list[ScenarioResult]) -> list[str]:
    """docs/12 Bolum 1.1 — model uyumsuzlugu blogunun okunmasi.

    BOLUM NUMARASI 1.1'DIR VE ARAYA YENI BIR ANA BOLUM GIRMEZ: docs/10 Bolum 1'e,
    juri kartlari Bolum 3'e atif veriyor (bkz. _prognosis_section docstring'i).
    Alt bolum eklemek bu atiflari bozmaz.

    Buradaki HER SAYI olculen sonuclardan turetilir; elle yazilan tek sey cumlelerin
    kendisidir. Uyumsuz senaryo yoksa bolum HIC basilmaz, boylece S0-S9'dan ibaret
    bir fixture dizini eski ciktiyi aynen verir.
    """
    mismatched = [r for r in results if not r.model_match]
    if not mismatched:
        return []

    matched = [r for r in results if r.model_match and r.recall is not None]
    scored = [r for r in mismatched if r.recall is not None]

    def toplam(rows: list[ScenarioResult]) -> tuple[int, int]:
        return sum(r.detected for r in rows), sum(r.expected for r in rows)

    m_det, m_exp = toplam(matched)
    u_det, u_exp = toplam(scored)
    oran = lambda d, e: "-" if e == 0 else f"{d / e:.2f}"

    lines = [
        "",
        "### 1.1 Model uyumsuzlugu — yontemin siniri",
        "",
        "Dedektor (`libs/panoalgo/panoalgo/detect.py`) isil davranisi su ayrik",
        "denklemle kestirir: `dT[k+1] = a*dT[k] + beta*I2[k]`, `K = beta/(1-a)`.",
        "Uretec S0-S9'da AYNI denklemi kullanir. Bu, tespit basarisinin bir kismini",
        "yapisal olarak garanti eder: kestirici kendi ileri modelini ters ceviriyordur.",
        "Asagidaki senaryolar uretece dedektorun VARSAYMADIGI bir fizik ekler ve ayni",
        "tespit boru hattini yeniden olcer. Dedektor DEGISTIRILMEDI — amac onu",
        "guclendirmek degil, sinirini olcmektir.",
        "",
        "| Senaryo | Eklenen fizik | Dedektorun varsayimi |",
        "|---|---|---|",
    ]
    for r in mismatched:
        for name in r.unmodelled_physics:
            text = PHYSICS_TEXT.get(name, name)
            eklenen, _, varsayim = text.partition(" (dedektor: ")
            lines.append(
                f"| `{r.scenario_id}` | {eklenen} | "
                f"{varsayim.rstrip(')') if varsayim else '-'} |"
            )

    lines += [
        "",
        f"**Olculen.** Eslesen modelde beklenen alarmlarin {m_det}/{m_exp}'i yakalandi "
        f"(recall {oran(m_det, m_exp)}); dedektorun varsaymadigi fizik eklendiginde "
        f"{u_det}/{u_exp} (recall {oran(u_det, u_exp)}).",
        "",
    ]

    kacan: dict[str, list[str]] = {}
    for r in mismatched:
        for code in r.missed:
            kacan.setdefault(code, []).append(r.scenario_id)
    if kacan:
        lines.append("Uyumsuz blokta kacan kodlar ve hangi senaryoda kactiklari:")
        lines.append("")
        for code, ids in sorted(kacan.items()):
            lines.append(f"- `{code}` — {', '.join('`' + i + '`' for i in ids)}")
        lines.append("")
    else:
        lines += [
            "Uyumsuz blokta HICBIR beklenen kod kacmadi. Bu, olcumun basarisizligi",
            "degil sonucudur ve nedeni yapisaldir: alarm kurallari K'yi degil K/K0",
            "ORANINI okur (`contracts/alarm-codes.yaml`, `k_ratio_warn`/`k_ratio_alarm`)",
            "ve taban K0 ayni uyumsuz fizikle ogrenildigi icin duragan bir yanlilik",
            "payda ile birlikte sadelesir. Uyumsuzlugun bedeli duyarlilikta degil",
            "Bolum 2 (one alma), Bolum 3 (yanlis alarm) ve Bolum 4 (prognoz)",
            "sutunlarinda gorunur — oraya bakin.",
            "",
        ]

    yasakli = [r for r in mismatched if r.forbidden_fired]
    if yasakli:
        lines.append("Uyumsuz blokta YASAKLI alarm cikan senaryolar (yanlis teshis):")
        lines.append("")
        for r in yasakli:
            lines.append(f"- `{r.scenario_id}` — {', '.join(r.forbidden_fired)}")
        lines.append("")

    lines += [
        "**Nasil okunmali.** Eslesen bloktaki sayi yontemin TAVANIDIR ve tek basina",
        "yayimlanirsa yaniltir. Uyumsuz bloktaki sayi ayni algoritmanin, ayni",
        "esiklerle, dedektorun bilmedigi bir fizik altindaki davranisidir. Ikisinin",
        "farki bu calismada olculebilir hale getirilen seydir.",
    ]
    return lines


def _prognosis_section(results: list[ScenarioResult]) -> list[str]:
    """docs/12 §4: prognoz geri testi (F-04).

    Bolum numarasi 4'tur ve §1-§3 YERINDE KALIR: docs/10 §1'e, jury kartlari §3'e
    atif veriyor, araya bolum eklemek o atiflari sessizce bozardi.
    """
    alpha = prognostics.DEFAULT_ALPHA
    scored = [r for r in results if r.prognosis is not None]
    breached = [r for r in results if r.l0_breach_at is not None]

    lines = [
        "",
        "## 4. Prognoz geri testi",
        "",
        "Gercek kalan omur ETIKETTEN turetilir: `RUL* = l0_breach_at - t`. Tahmin,",
        "verideki `min_ttl_h` sutunudur (kenarin o an yayinladigi `ttl_h`). Koni",
        f"genisligi alfa = {alpha:.2f} (Saxena ve ark. 2010): tahmin",
        "`[(1-alfa)RUL*, (1+alfa)RUL*]` araligindaysa koni icinde sayilir.",
        "",
        "| Senaryo | Tahmin | Ilk tahmin (RUL*) | Koni icinde | Ufuk (PH) | CRA | "
        "Medyan tahmin/gercek | Hata agirlik merkezi |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in breached:
        p = r.prognosis
        if p is None:
            lines.append(f"| `{r.scenario_id}` | 0 | - | - | - | - | - | - |")
            continue
        horizon = "yok" if p.horizon_h is None else f"{p.horizon_h:.1f} h"
        centre = "-" if p.convergence_fraction is None else f"{p.convergence_fraction:.2f}"
        lines.append(
            f"| `{p.scenario_id}` | {p.count} | {p.first_prediction_h:.1f} h | "
            f"{p.in_band_ratio * 100:.1f}% | {horizon} | "
            f"{p.cumulative_relative_accuracy:.2f} | {p.median_ratio:.2f} | {centre} |"
        )

    lines += [
        "",
        "**Ufuk (PH)** = tahminin o andan ihlale kadar BIR DAHA konidan cikmadigi ilk an.",
        "**CRA** = ortalama goreli dogruluk, `1 - |RUL* - tahmin| / RUL*`; 1,00 kusursuz,",
        "0 hata gercek omur kadar buyuk, negatif daha da buyuk. **Hata agirlik merkezi**",
        "0'a yakinsa hata pencerenin BASINDA toplanmis, 1'e yakinsa SONUNDA — tek basina",
        "okunmaz, cunku hata her yerde buyukse merkez de ortalarda cikar; koni icinde",
        "kalma orani ile birlikte okunur.",
    ]

    if scored:
        lines += [
            "",
            "### 4.1 alfa-lambda noktalari",
            "",
            "lambda, ilk tahmin ile ihlal ani arasindaki yolun kesridir; lambda = 0,50",
            "\"omrun yarisinda tahmin tutuyor muydu\" demektir.",
            "",
            "| Senaryo | lambda | RUL* (h) | Tahmin (h) | Koni icinde | RA |",
            "|---|---:|---:|---:|---|---:|",
        ]
        for r in scored:
            for point in r.prognosis.alpha_lambda:
                lines.append(
                    f"| `{r.scenario_id}` | {point.lam:.2f} | {point.rul_true_h:.1f} | "
                    f"{point.rul_pred_h:.1f} | {'evet' if point.in_band else 'hayir'} | "
                    f"{point.relative_accuracy:.2f} |"
                )

        lines += [
            "",
            "### 4.2 Tahmin ne zaman guvenilir hale geldi",
            "",
            "Saglikli bir prognozda ariza yaklastikca (kucuk RUL*) koni icinde kalma",
            "orani 1'e dogru gitmelidir.",
            "",
            "| Senaryo | Kalan omur araligi | Tahmin | Koni icinde | Medyan tahmin/gercek |",
            "|---|---|---:|---:|---:|",
        ]
        for r in scored:
            for bucket in r.prognosis.buckets:
                span = (
                    f"{bucket.low_h:.0f} h ustu"
                    if bucket.high_h is None
                    else f"{bucket.low_h:.0f}-{bucket.high_h:.0f} h"
                )
                if bucket.count == 0:
                    lines.append(f"| `{r.scenario_id}` | {span} | 0 | - | - |")
                    continue
                lines.append(
                    f"| `{r.scenario_id}` | {span} | {bucket.count} | "
                    f"{bucket.in_band_ratio * 100:.1f}% | {bucket.median_ratio:.2f} |"
                )

    lines += ["", "### 4.3 Durustluk kayitlari", ""]
    matched_scored = [r for r in scored if r.model_match]
    mismatched_scored = [r for r in scored if not r.model_match]
    if mismatched_scored:
        lines.append(
            f"- **Sonuc {len(scored)} olcumden geliyor ama n HALA 1'DIR.** Guven araligi "
            f"YOKTUR. Bunlarin {len(matched_scored)} tanesi eslesen, "
            f"{len(mismatched_scored)} tanesi uyumsuz modeldendir; hepsi AYNI tohumun "
            "AYNI bozulma yorungesidir, yalnizca farkli model dunyalarinda okunmustur. "
            "Yani dort sayi birbirinin BAGIMSIZ tekrari degildir ve ortalamalari bir "
            "populasyon istatistigi vermez. Bagimsiz tekrar icin coklu tohum gerekir "
            "(Yapilacaklar 2.2); bu is onu KAPSAMAZ."
        )
    else:
        lines.append(
            f"- **Sonuc {len(scored)} yorungeden geliyor (n = {len(scored)}).** Guven araligi "
            "YOKTUR; tek bir seed'li senaryonun tek bir bozulma yorungesi olculmustur. "
            "Yukaridaki yuzdeler bu yorungenin ozellikleridir, populasyon istatistigi degildir."
        )
    for r in breached:
        if r.prognosis is None:
            lines.append(
                f"- **`{r.scenario_id}`: sinir asildi ama hic tahmin uretilmedi.** "
                "Kalici uyarim ve surekli pozitif egim kosullari saglanmadigi icin "
                "`ttl_h` null kaldi; prognoz olcumu bu senaryoda YAPILAMAZ."
            )
        elif r.prognosis.late_count:
            lines.append(
                f"- **`{r.scenario_id}`: ihlalden SONRA {r.prognosis.late_count} tahmin daha "
                "uretildi.** Sinir zaten asilmisken sistem hala sonlu bir kalan omur "
                "soyluyor; bu tahminler geri testin disinda tutuldu (gercek kalan omur "
                "negatif, oran tanimsiz)."
            )
    for r in results:
        if r.false_prognoses:
            lines.append(
                f"- **`{r.scenario_id}`: sinir HIC asilmadigi halde {r.false_prognoses} "
                "tahmin uretildi — bu bir PROGNOZ YANLIS-ALARMIDIR.** Bunlarin "
                f"{r.false_prognosis_alarms} tanesi `{TTL_ALARM_CODE}` alarmina dondu ve "
                "§3'teki yanlis alarm sayaci bunlari GORMEZ: etiket penceresinin icinde "
                "cikiyorlar. Nedeni "
                "[05-anomali-tespiti.md](05-anomali-tespiti.md) \"bilinen sinirlar\" "
                "bolumundedir."
            )
    return lines


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

    for r in order_results(results):
        recall = "-" if r.recall is None else f"{r.recall:.2f}"
        lead = "-" if r.lead_time_h is None else f"{r.lead_time_h:7.1f} h"
        flag = "" if r.precision_ok else f"  YASAKLI: {', '.join(r.forbidden_fired)}"
        if not r.model_match:
            flag += f"  UYUMSUZ: {', '.join(r.unmodelled_physics)}"
        print(
            f"{r.scenario_id:<20} {r.model_text:<8} recall={recall:<5} one alma={lead:<10} "
            f"yanlis/100pano/gun={r.false_alarms_per_100_panel_days:6.1f}{flag}"
        )
    return 0


def _default_fixtures_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "fixtures"


if __name__ == "__main__":
    sys.exit(main())
