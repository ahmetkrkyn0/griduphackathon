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
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .detect import load_thresholds
from .edge import EdgePipeline
from .generator import (
    ModelMismatch,
    PanelSimulator,
    contract_point_names,
    format_pano_id,
    parse_detector,
)
from .quality import codes_from_bits

EXPORT_PERIOD_S = 900.0          # 15 dk (rapor 15.2 Excel uyumu)
SECONDS_PER_HOUR = 3600.0
DEFAULT_PANO_INDEX = 1
LV_PANEL_TYPE = "1600kVA-dahili"
MV_PANEL_TYPE = "OG-hucre"

# Mevsim baslangiclari: yogusma kis gecelerinde, isil senaryolar yaz yukunde anlamli.
SUMMER_START = datetime(2026, 7, 6, 0, 0, tzinfo=timezone.utc)   # Pazartesi
WINTER_START = datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)   # Pazartesi
# Gecis mevsimi, ISIL OLMAYAN senaryolarin varsayilanidir. Sebep olculmustur: Ege
# yazinda ortam 35-42 degC'ye ciktigi icin pano ic havasi 45 degC esigini gercekten
# asar ve ALM-PANEL-TEMP orneklerin yarisinda dogru bir sekilde cikar. Bu bir yanlis
# alarm degildir — sartname ortam varsayimi 40 degC'dir ve asilmaktadir — ama yanlis
# alarm TABANI olcmek istedigimiz S0 gibi senaryolarda algoritmayi degil iklimi
# olcerdi. Yaz kosulunun kendisi docs/12'de ayrica raporlanir.
SHOULDER_START = datetime(2026, 4, 6, 0, 0, tzinfo=timezone.utc)  # Pazartesi

# Mevsim -> senaryonun baslangic ani. Tek kaynak: plan() ve scripts/threshold_sweep.py
# ayni esleme uzerinden calisir, yoksa "yaz" iki dosyada ayri tarihe kayabilir.
SEASON_STARTS: dict[str, datetime] = {
    "kis": WINTER_START,
    "gecis": SHOULDER_START,
    "yaz": SUMMER_START,
}


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
    season: str = "gecis"
    profile: str = "karma"
    medium_voltage: bool = False
    params: dict = field(default_factory=dict)
    # Dedektorun VARSAYMADIGI fizikler (Yapilacaklar 2.1). None = eslesen model,
    # yani uretec ile detect.py ayni denklemi cozer. Bu bir ARIZA DEGILDIR: panonun
    # ve olcum zincirinin kendi ozelligidir, bu yuzden _inject() icinde surulmez,
    # PanelSimulator kurulurken verilir ve TABAN OGRENME PENCERESINDE DE ACIKTIR.
    # Ortada acilsaydi dedektor model uyumsuzlugunu degil bir basamak degisimini
    # yakalardi — yani senaryo cevabi fisildamis olurdu.
    mismatch: ModelMismatch | None = None

    @property
    def unmodelled_physics(self) -> tuple[str, ...]:
        """Acik uyumsuzluklarin sozlesme adlari; eslesen modelde bos demet."""
        return () if self.mismatch is None else self.mismatch.names()


TARGET_POINT = "DSYA3_L2"

SCENARIOS: dict[str, ScenarioSpec] = {
    "S0_normal": ScenarioSpec(
        text="Saglikli pano — yanlis alarm olcumunun tabani",
        default_duration_h=168.0,
    ),
    "S1_loose_conn": ScenarioSpec(
        text="Gevsek baglanti: K yavasca %200 artar (rapor 15.2)",
        default_duration_h=720.0,
        season="yaz",
        label_type="loose_connection",
        point=TARGET_POINT,
        severity="P2",
        expect=("ALM-K-WARN", "ALM-K-ALM", "ALM-THR-TERM-WARN", "ALM-THR-TERM-ALM"),
        not_expect=("ALM-I-OVER",),
        # load_multiplier 0.95 iki kisiti birlikte saglar ve OLCULEREK secilmistir:
        #   (a) sabit 70 K esigi gercekten asilmali, yoksa "sabit esikle karsilastirma"
        #       yapilamaz  -> K x3 iken tepe artis 70 K'yi gecmeli;
        #   (b) K/K0 = 1.6 esigi ile 70 K ihlali arasinda en az 48 saat olmali
        #       (PLAN.md TA2 kabul kriteri).
        # Tarama (720 h, seed 1304): yuk 0.85 -> 63 K, ihlal YOK · 0.90 -> 71 K, one
        # alma 149 h · 0.95 -> 79 K, one alma 125 h · 1.00 -> 88 K, one alma 73 h.
        # 0.95 secildi: ihlal payi rahat (79 K) ve one alma kriterin iki katindan fazla.
        params={"k_growth_pct": 200, "load_multiplier": 0.95},
    ),
    "S2_overload": ScenarioSpec(
        text="Asiri yuk: akim anma degerinin ustunde, K SABIT (ariza degil)",
        default_duration_h=168.0,
        label_type="overload",
        point="PANEL",
        severity="P2",
        expect=("ALM-I-OVER",),
        not_expect=("ALM-K-ALM", "ALM-K-WARN"),
        params={"load_multiplier": 1.8},
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
    # --- S10-S13: model uyumsuzlugu (Yapilacaklar 2.1) --------------------------
    # DORDU DE S1_loose_conn'un KONTROLLU KLONUDUR: ayni sure (720 h), ayni nokta
    # (DSYA3_L2), ayni mevsim (yaz), ayni yuk carpani (0,95), ayni K buyumesi (%200)
    # ve ayni `expect`. TEK degisken `mismatch` alanidir, yani olculen her farkin
    # tek acikamasi o fizik terimidir. Tohum da ayni tutulur (fixture uretimi 1304).
    #
    # `expect` NEDEN GEVSETILMEDI: ariza gercekten oradadir, dolayisiyla beklenen
    # kodlar degismez. Recall = yakalanan/beklenen oldugu icin paydayi kucultmek
    # uyumsuzlugu ODULLENDIRIRDI — "daha az bekle, daha yuksek recall al". Payda
    # sabit kalinca tablo dogru soruyu cevaplar: ayni ariza, ayni esikler, farkli
    # fizik — kac tanesi hala yakalaniyor?
    #
    # `ALM-DQ-DRIFT` her dordunun `not_expect`indedir ve bu BILINCLI bir sinavdir:
    # kayma kurali (quality.py) "dT = a*I^2 + b"de b'nin buyumesini sensor kaymasi
    # sayar. Yavas kutup ve kuplaj da yukten bagimsiz gorunen bir bilesen uretir;
    # kural bunlari sensor arizasi sanirsa GERCEK bir isil olayi "kalibrasyon
    # supheli" diye yanlis etiketler. Cikarsa tabloda YASAKLI ALARM olarak gorunur.
    "S10_coupling": ScenarioSpec(
        text="Model uyumsuzlugu: terminal grubu ici isil kuplaj (dedektor tek nokta varsayar)",
        default_duration_h=720.0,
        season="yaz",
        label_type="loose_connection",
        point=TARGET_POINT,
        severity="P2",
        expect=("ALM-K-WARN", "ALM-K-ALM", "ALM-THR-TERM-WARN", "ALM-THR-TERM-ALM"),
        not_expect=("ALM-I-OVER", "ALM-DQ-DRIFT"),
        params={"k_growth_pct": 200, "load_multiplier": 0.95},
        # 0,15 OLCULEREK secildi (720 h, seed 1304, eslesen ikizle ayni kosul).
        # Tarama — tepe k_ratio / tepe dT / esik ustu nokta sayisi / yayimlanan tau:
        #   0,05 -> 2,90 · 76,7 K · 1 nokta ·  755 s
        #   0,10 -> 2,82 · 74,7 K · 1 nokta ·  826 s
        #   0,15 -> 2,74 · 73,0 K · 2 NOKTA ·  903 s   <- secildi
        #   0,25 -> 2,62 · 70,0 K · 1 nokta · 1039 s
        # Iki kisit birlikte saglanmali: (a) 70 K sinirinin HALA asilmasi gerekir,
        # yoksa "one alma" tanimsiz kalir ve olculen sey kuplaj degil sogumadir —
        # 0,25'te tepe tam 70,0 K, yani olcum gurultusu (sigma 0,2 K) mertebesinde
        # yazi-tura; (b) kuplajin ASIL etkisi gorunmeli, o da YANLIS YERELLESTIRME:
        # 0,15'te k_ratio esigini asan nokta sayisi 1'den 2'ye cikiyor, yani arizasiz
        # bir komsu terminal de suclanmaya basliyor. Saha ekibi yanlis uca gider.
        mismatch=ModelMismatch(coupling_k=0.15),
    ),
    "S11_load_tau": ScenarioSpec(
        text="Model uyumsuzlugu: yuke bagli zaman sabiti (dedektor tau'yu sabit varsayar)",
        default_duration_h=720.0,
        season="yaz",
        label_type="loose_connection",
        point=TARGET_POINT,
        severity="P2",
        expect=("ALM-K-WARN", "ALM-K-ALM", "ALM-THR-TERM-WARN", "ALM-THR-TERM-ALM"),
        not_expect=("ALM-I-OVER", "ALM-DQ-DRIFT"),
        params={"k_growth_pct": 200, "load_multiplier": 0.95},
        # Isaret NEGATIF secildi: dogal tasinimda h, dT ile buyur ve tau = C/(h*A)
        # KUCULUR. Buyukluk 0,8 -> anma akiminda tau exp(-0,8) = 0,45 katina iner.
        # OLCULDU (720 h, seed 1304) — yayimlanan tau ve tespit sonucu:
        #   c = -0,8 -> tau 689 s -> 481 s (0,70x) · k_ratio 3,00 · 4/4 kod cikti
        #   c = -0,4 -> tau 689 s -> 569 s (0,83x) · k_ratio 3,01 · 4/4 kod cikti
        #   c = +1,0 -> tau 689 s -> 1223 s (1,8x) · k_ratio 3,02 · 4/4 kod cikti
        # Yani SONUC ISARETTEN BAGIMSIZDIR ve bu senaryonun bulgusu tam olarak budur:
        # tau kestirimi belirgin sekilde saprken tespit HIC bozulmuyor, cunku alarm
        # K'yi degil K/K0 oranini okur ve taban ayni uyumsuz fizikle ogrenilmistir.
        # Bu senaryo tabloda "uyumsuz ama recall 1,00" satiridir; blogun secmeci
        # olmadiginin kanitidir.
        mismatch=ModelMismatch(tau_load_coeff=-0.8),
    ),
    "S12_two_pole": ScenarioSpec(
        text="Model uyumsuzlugu: ikinci (yavas) isil kutup (dedektor birinci mertebe varsayar)",
        default_duration_h=720.0,
        season="yaz",
        label_type="loose_connection",
        point=TARGET_POINT,
        severity="P2",
        expect=("ALM-K-WARN", "ALM-K-ALM", "ALM-THR-TERM-WARN", "ALM-THR-TERM-ALM"),
        not_expect=("ALM-I-OVER", "ALM-DQ-DRIFT"),
        params={"k_growth_pct": 200, "load_multiplier": 0.95},
        # 0,45 OLCULEREK secildi. Tarama (720 h, seed 1304) — yayimlanan tau /
        # tepe dT / 70 K asildi mi / ALM-DQ-DRIFT cikti mi:
        #   0,30 ->  4129 s · 74,3 K · evet · EVET
        #   0,45 ->  6576 s · 72,3 K · evet · EVET   <- secildi
        #   0,60 ->  9338 s · 70,7 K · evet · EVET
        #   0,75 -> 12440 s · 69,1 K · HAYIR · EVET
        # 0,75 reddedildi: 70 K hic asilmiyor, yani sabit esik ariziyi kaciriyor ve
        # bu senaryo iki seyi birden olcmeye baslar. 0,45 yavas kutbu belirgin kilar
        # (yayimlanan tau 689 s -> 6576 s, 9,5 KAT) ama sinir ihlalini korur.
        # ASIL BULGU BURADA: ALM-DQ-DRIFT tetikleniyor ve bu senaryonun not_expect
        # listesindedir. Kayma kurali (quality.py) "dT = a*I^2 + b"de b'nin buyumesini
        # SENSOR kaymasi sayar; yavas isil kutup da yukten bagimsiz gorunen bir bilesen
        # uretir. Yani GERCEK bir isil olay "kalibrasyon supheli" diye etiketleniyor.
        mismatch=ModelMismatch(slow_share=0.45),
    ),
    "S13_sensor_nonlin": ScenarioSpec(
        text="Model uyumsuzlugu: olcum zinciri dogrusalsizligi (dedektor dogrusal olcum varsayar)",
        default_duration_h=720.0,
        season="yaz",
        label_type="loose_connection",
        point=TARGET_POINT,
        severity="P2",
        expect=("ALM-K-WARN", "ALM-K-ALM", "ALM-THR-TERM-WARN", "ALM-THR-TERM-ALM"),
        not_expect=("ALM-I-OVER", "ALM-DQ-DRIFT"),
        params={"k_growth_pct": 200, "load_multiplier": 0.95},
        # 0,008 1/K OLCULEREK secildi. Tarama (720 h, seed 1304) — tepe OLCULEN dT /
        # 70 K asildi mi / kacan kodlar (gercek tepe artis her satirda 79,0 K'dir):
        #   0,004 -> 60,0 K · HAYIR · ALM-THR-TERM-ALM
        #   0,008 -> 48,5 K · HAYIR · ALM-THR-TERM-ALM + ALM-THR-TERM-WARN  <- secildi
        #   0,015 -> 36,3 K · HAYIR · ayni ikisi (+ faz farki da kayboluyor)
        #   0,025 -> 26,8 K · HAYIR · ayni ikisi, ayrica sahte ALM-DQ-DRIFT
        # 0,008 secildi: IKI L0 esigini de korlestiriyor ama kayma kuralini yanlis
        # tetiklemiyor, yani olculen tek sey olcum zinciri dogrusalsizligidir.
        # BU SENARYO CALISMANIN EN NET SONUCUDUR: pano eslesen ikiziyle TAM OLARAK
        # AYNI DERECEDE SICAK (gercek artis 79,0 K); yalan soyleyen alettir. Sabit
        # 70 K esigi tamamen korlesirken oran tabanli K tespiti AYAKTA KALIYOR
        # (k_ratio 3,01 > 1,6). "Neden sabit esik yetmiyor" sorusunun deneysel cevabi.
        mismatch=ModelMismatch(sensor_gain_per_k=0.008),
    ),
}


def list_scenarios() -> list[dict]:
    """Katalog: kimlik, aciklama, varsayilan sure."""
    return [
        {"scenario_id": key, "text": spec.text, "default_duration_h": spec.default_duration_h}
        for key, spec in SCENARIOS.items()
    ]


@dataclass(frozen=True)
class ScenarioPlan:
    """Bir senaryo kosusunun degismez parametreleri.

    CSV fixture uretimi (build) ve CANLI OYNATMA (sim/panosim.py --scenario) ayni
    plani ve ayni yurutucuyu kullanir. Boylece demoda gosterilen fizik, docs/12'yi
    ureten fizigin BIREBIR aynisidir — "demoda baska, raporda baska" olamaz.
    """

    scenario_id: str
    spec: ScenarioSpec
    seed: int
    pano_id: str
    duration_h: float
    baseline_h: float
    start: datetime
    steps: int
    l0_limit: float
    contracts_dir: Path | None = None


@dataclass(frozen=True)
class ScenarioSample:
    """Yurutucunun her adimda verdigi sonuc."""

    index: int
    hours: float                      # senaryo baslangicindan itibaren SIMULE saat
    payload: dict | None              # None = haberlesme boslugu; veri YOK
    injected_from: datetime | None    # enjeksiyonun basladigi an (basladiysa)


def plan(
    scenario_id: str,
    seed: int,
    duration_h: float | None = None,
    *,
    contracts_dir: Path | None = None,
    pano_id: str | None = None,
    point: str | None = None,
    detector: str | None = None,
    baseline_h: float | None = None,
    season: str | None = None,
) -> ScenarioPlan:
    """Senaryoyu dogrular ve kosturulabilir bir plana cevirir.

    `point` / `detector` / `pano_id` demo icin gecersiz kilinabilir (bkz. demo/senaryo).
    `baseline_h` yalnizca CANLI demoda kisaltilir (Y1); fixture uretimi asla vermez.
    `season` de yalnizca CANLI demo icindir ve fixture uretimi ASLA vermez: docs/12'deki
    yanlis alarm tabani senaryonun kendi mevsimiyle (S0: gecis) olculur ve oyle kalir.
    """
    spec = SCENARIOS.get(scenario_id)
    if spec is None:
        raise ValueError(f"bilinmeyen senaryo: {scenario_id!r}; gecerli: {sorted(SCENARIOS)}")

    duration = spec.default_duration_h if duration_h is None else duration_h
    if duration <= 0.0:
        raise ValueError(f"duration_h pozitif olmali: {duration}")

    if season is not None:
        if season not in SEASON_STARTS:
            raise ValueError(f"bilinmeyen mevsim: {season!r}; gecerli: {sorted(SEASON_STARTS)}")
        spec = replace(spec, season=season)
    if point is not None:
        spec = replace(spec, point=_validated_point(point, contracts_dir))
    if detector is not None:
        # parse_detector burada patlasin: gecersiz ad 30 sn'lik demoda degil, ilk saniyede.
        parse_detector(detector)
        spec = replace(spec, params={**spec.params, "detector": detector})

    thresholds = load_thresholds(contracts_dir)
    learned = min(float(thresholds["baseline_learning_days"]) * 24.0, duration / 3.0)
    return ScenarioPlan(
        scenario_id=scenario_id,
        spec=spec,
        seed=seed,
        pano_id=pano_id or format_pano_id("SIM", DEFAULT_PANO_INDEX),
        duration_h=duration,
        baseline_h=learned if baseline_h is None else min(max(baseline_h, 0.0), duration),
        start=SEASON_STARTS[spec.season],
        steps=int(duration * SECONDS_PER_HOUR / EXPORT_PERIOD_S),
        l0_limit=float(thresholds["term_rise_alarm_k"]),
        contracts_dir=contracts_dir,
    )


def iter_samples(scenario: ScenarioPlan):
    """Plani adim adim kosturur; her adimda bir ScenarioSample verir.

    Adim suresi EXPORT_PERIOD_S'dir (15 dk) ve DUVAR SAATINDEN bagimsizdir:
    yurutucu hiz bilmez. Canli oynatmada araya bekleme koymak cagiranin isidir
    (sim/panosim.py), fixture uretiminde hic beklenmez.
    """
    spec = scenario.spec
    sim = PanelSimulator(
        pano_id=scenario.pano_id,
        seed=scenario.seed,
        profile=spec.profile,
        start=scenario.start,
        contracts_dir=scenario.contracts_dir,
        medium_voltage=spec.medium_voltage,
        mismatch=spec.mismatch,
    )
    pipeline = EdgePipeline(profile=spec.profile, contracts_dir=scenario.contracts_dir)
    injected_from: datetime | None = None

    for index in range(scenario.steps):
        hours = index * EXPORT_PERIOD_S / SECONDS_PER_HOUR
        if not pipeline.baseline_frozen and hours >= scenario.baseline_h:
            pipeline.freeze_baselines()

        if hours >= scenario.baseline_h:
            if injected_from is None:
                injected_from = scenario.start + timedelta(hours=hours)
            _inject(spec, sim, hours, scenario.baseline_h, scenario.duration_h)

        payload = pipeline.process(sim.step(EXPORT_PERIOD_S))

        if _in_comms_gap(spec, hours, scenario.baseline_h):
            # veri YOK; sahte deger uretmiyoruz. Canli oynatmada da YAYINLANMAZ.
            yield ScenarioSample(index, hours, None, injected_from)
            continue

        yield ScenarioSample(index, hours, payload, injected_from)


def _validated_point(point: str, contracts_dir: Path | None) -> str:
    """Nokta adini sozlesmedeki conn_temp listesine karsi dogrular."""
    if point in ("PANEL", "SYSTEM"):
        return point
    names = contract_point_names(contracts_dir)
    if point not in names:
        raise ValueError(f"bilinmeyen nokta: {point!r}; gecerli: {', '.join(names)}")
    return point


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

    scenario = plan(scenario_id, seed, duration_h, contracts_dir=contracts_dir)
    spec = scenario.spec

    rows: list[dict] = []
    l0_breach_at: str | None = None
    injected_from: datetime | None = None

    for sample in iter_samples(scenario):
        injected_from = sample.injected_from
        if sample.payload is None:
            continue
        row = _row(sample.payload, spec)
        rows.append(row)
        if l0_breach_at is None and row["worst_dt_c"] > scenario.l0_limit:
            l0_breach_at = row["ts"]

    frame = pd.DataFrame(rows)
    labels = _labels(
        spec, scenario_id, seed, scenario.pano_id, duration_h, scenario.start,
        injected_from, l0_breach_at, generated_at,
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
        sim.set_protection_health(False, detector=params.get("detector"))
    elif spec.label_type == "harmonic":
        sim.set_thd_multiplier(params["thd_multiplier"])
    elif spec.label_type == "sensor_dropped":
        sim.set_sensor_fault("DSYA6_L1", "dropped")
        sim.set_sensor_fault("DSYA5_L2", "frozen")
        sim.set_sensor_fault("DSYA4_L3", "drift")
    elif spec.label_type == "pd_trend":
        sim.set_pd_activity(min(1.0, progress))


# Rampanin pencerenin bu kadarlik kisminda tamamlanmasi, kalani tam bozulmada gecer.
# Rapor 15.2 bozulmayi "7-30 gun boyunca %0 -> %200 artis; ILERI EVREDE ARALIKLI
# SICRAMALAR" diye tarif eder — yani K sonsuza kadar dogrusal buyumez, bir plato
# vardir. Plato ayrica sabit 70 K esiginin gercekten asilmasina zaman birakir.
#
# Plato UZUN olmali: en yuksek sicaklik artisi, en yuksek K ile en yuksek YUKUN ayni
# ana denk gelmesini gerektirir. Yuk gunden gune degistigi icin kisa bir plato (0.7)
# ile olculdu ki tepe artis 53 K'da kaliyor, 70 K'ya hic ulasilmiyordu: K 3.0'a
# ciktiginda o gunlerin yuku dusuktu. 0.5 ile plato ~11 gun surer ve icine birden
# cok yuk tepesi girer.
RAMP_COMPLETES_AT = 0.5


def _progress(hours: float, baseline_h: float, duration_h: float) -> float:
    """Enjeksiyon penceresi icinde 0 -> 1 ilerleme (rampa erken tamamlanir, sonra plato)."""
    span = max(duration_h - baseline_h, 1e-9)
    raw = (hours - baseline_h) / span
    return min(1.0, max(0.0, raw / RAMP_COMPLETES_AT))


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
        # Veri kalitesi kodlari alarms[] icinde DEGIL q bit alanindadir (cift alarm
        # onlemi, bkz. edge.py). Dogrulama betigi icin ayri sutunda geri cozuluyor.
        "dq_codes": ";".join(sorted({c for p in points for c in codes_from_bits(p["q"])})),
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

    root = {
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
    # KOSULLU YAZIM: eslesen senaryolarda anahtar HIC olusmaz, boylece S0-S9'un
    # on etiket dosyasi bayt duzeyinde korunur (bos liste yazmak bile onlari
    # degistirirdi). scripts/validate.py alanin yoklugunu "eslesen" okur.
    if spec.unmodelled_physics:
        root["unmodelled_physics"] = list(spec.unmodelled_physics)
    return root


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
    # newline="\n": Windows'ta write_text varsayilani CRLF uretir, .gitattributes LF ister.
    labels_path.write_text(
        json.dumps(labels, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
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
            print(f"{entry['scenario_id']:<20} {entry['default_duration_h']:>7.0f} h  {entry['text']}")
        return 0

    targets = list(SCENARIOS) if args.all else ([args.build] if args.build else [])
    if not targets:
        parser.print_help()
        return 1

    out_dir = Path(args.out) if args.out else None
    for scenario_id in targets:
        csv_path, labels_path = write_fixture(scenario_id, args.seed, args.duration_h, out_dir)
        size_kb = csv_path.stat().st_size / 1024
        print(f"{scenario_id:<20} -> {csv_path.name} ({size_kb:.0f} KB), {labels_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
