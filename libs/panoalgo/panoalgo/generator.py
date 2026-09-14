"""Fizik tabanli sentetik telemetri ureteci (TA1 Adim 5, Kisi A).

Neden ureteci: gercek bir pano 7-30 gunluk bir bozulmayi demo suresinde gosteremez.
Burada bozulma bir denklemle uretilir, bu yuzden hem hizlandirilabilir hem savunulabilir
(PLAN.md Bolum C, DH3).

Zincir (her adimda):
  yuk profili (saat-of-hafta) x mevsim x AR(1) gurultu
     -> faz akimlari (dengesizlik) -> notr akimi (dengesizlik + 3. harmonik)
     -> nokta basina ayrik isil model  dT[k+1] = a*dT[k] + (1-a)*K*I^2,  a = exp(-Ts/tau)
     -> ortam sicakligi (gunluk sinus + mevsim) ve ters iliskili nem
     -> Magnus ciy noktasi + yogusma marji
     -> contracts/mqtt-telemetry.schema.json'a uyan sozluk

Sozlesme kurallari (PLAN.md kural 10): nokta adlari contracts/modbus-map.yaml'dan,
esikler contracts/alarm-codes.yaml'dan, pano_id deseni telemetri semasindan okunur.
Bu dosyada 70 K / 2312 A / 0.998 gibi HICBIR sozlesme sayisi yazili degildir.

TA1 kapsam notu (durustluk kurali, PLAN.md Bolum C): bu surum SAGLIKLI panoyu (S0)
uretir. k_ratio her zaman 1.0'dir cunku RLS kestirimi ve ariza enjeksiyonu TA2'nin
isidir (detect.py / scenarios.py); `risk` blogu da orada gercek fuzyonla degisecek.

TA2 ICIN BULGU — ALM-DQ-BELOW-AMBIENT olu bant istiyor: hafif yuklu noktalar
(ozellikle GIRIS_N) fiziksel olarak ortam sicakliginda oturur; uzerine sigma 0,2 K
olcum gurultusu binince dt_c zaman zaman SIFIRIN ALTINA duser. Bu gercek bir sensor
davranisidir, uretec kusuru degil — bu yuzden kirpilmiyor. quality.py'deki
"ortam alti" kurali `t_c < T_ortam` degil `t_c < T_ortam - olu_bant` olmali
(olu bant >= 3*sigma), yoksa saglikli pano sahte SYS alarmi uretir.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from .physics import dew_point
from .profiles import (
    SEASON_AMPLITUDE,
    Ar1Noise,
    ProfileKind,
    ar1_phi,
    load_profile,
    season_factor,
)

SCHEMA_VERSION = 1
FW_VERSION = "0.1.0-ta1"

# backend/app/ingest.py:112 varsayilan siniri. Sozlesme degil, ingest korumasi —
# uretecin bu sinira yaklasmadigini test dogrular.
MAX_MESSAGE_BYTES = 64_000

# --- Asagidaki sayilar rapor 15.2'nin NITEL tarifinden TURETILMISTIR. --------------
# Rapor bu buyukluklere sayisal deger vermez; secimler docs/14-veri-ureteci.md'de
# gerekcelendirilecek (TA2).

# Pano anma akiminin ne kadari yaz tepe saatinde kullanilir. 1.0 secilseydi saglikli
# pano surekli ALM-I-OVER uretirdi; cok kucuk secilseydi 70 K'ya hic yaklasilamazdi.
PEAK_UTILISATION = 0.80

# Anma akiminda saglikli bir baglantinin ortam uzeri artisi. IEC 61439-1 terminal
# ALARM limiti 70 K, UYARI limiti 50 K'dir. 60 K secilmisti; olculdu ki bu deger
# saglikli panoyu yaz tepe yukunde 59 K'ya cikariyor ve ornekleri'nin %20'sinde
# ALM-THR-TERM-WARN uretiyordu — yani "saglikli" senaryo surekli uyari veriyordu.
# 40 K, hem uyari esigine pay birakir hem de K uc katina ciktiginda 70 K'nin
# asilmasini saglar (40 x 3 = 120 K).
DT_AT_RATED_K = 40.0
K_SPREAD = 0.15  # nokta basina K0 dagilimi (rapor 15.2: "nokta basina K0 (dagilimli)")

TAU_MIN_S = 600.0   # rapor 15.2: isil zaman sabiti 10-30 dk
TAU_MAX_S = 1800.0
TEMP_SENSOR_SIGMA_K = 0.2  # rapor 15.2: olcum gurultusu sigma ~ 0,2 degC

TAU_LOAD_S = 1800.0   # yuk dalgalanmasinin zaman sabiti -> AR(1) phi
LOAD_NOISE_SIGMA = 0.04
EXCITATION_WINDOW = 60  # kalici uyarim icin var(I^2) penceresi (ornek sayisi)

# Ortam: rapor 15.2 Izmir/Aydin -> yaz 35-42 degC, kis 0-10 degC; tepe ~15:00.
SUMMER_MEAN_C, SUMMER_AMP_K = 38.5, 3.5
WINTER_MEAN_C, WINTER_AMP_K = 5.0, 5.0
AMBIENT_PEAK_HOUR = 15.0
PANEL_INLET_RISE_K = 2.0   # pano alt bolme havasi disaridan biraz sicak
DT_AIR_MAX_K = 12.0        # tam yukte ust-alt hava farki (pano enerji dengesi)

# Nem: sartname Tablo 1 (rapor 3.1) — +40 degC'de %50, +20 degC'de %90 -> egim 2 %/K.
RH_REF_T_C, RH_AT_REF_PCT, RH_SLOPE_PCT_PER_K = 40.0, 50.0, 2.0
RH_MIN_PCT, RH_MAX_PCT = 20.0, 98.0

# Faz dengesizligi: rapor 15.2 -> %2-15, yavas degisen.
UNBAL_MIN, UNBAL_MAX = 0.025, 0.145
UNBAL_CENTER, UNBAL_SIGMA, UNBAL_TAU_S = 0.06, 0.03, 6 * 3600.0

# Harmonik / gerilim / guc katsayisi.
THD_BASE_PCT, THD_LIGHT_LOAD_SPAN_PCT = 4.0, 4.0
H3_SHARE_OF_THD = 0.7  # 3. harmonigin THD icindeki payi (rapor kapali form vermez)
U_PHASE_NOMINAL_V, U_PHASE_DROP_V, U_PHASE_SIGMA_V = 231.0, 6.0, 0.3
COSPHI_NO_LOAD, COSPHI_SPAN, COSPHI_MAX = 0.93, 0.05, 0.99

# --- Senaryo enjeksiyonu (TA2) --------------------------------------------------
# Uretec, ariza enjeksiyonunu FIZIKSEL PARAMETRE uzerinden yapar: "alarm uret" demez,
# K'yi buyutur / yuku artirir / sensoru bozar ve sonucu tespit katmanlarina biraktir.
# Boylece senaryolar tespit algoritmasini gercekten sinar, ona cevabi fisildamaz.
# Rapor 15.2 asiri yuku "gunlerce %110-130 In" diye tanimlar; carpanin bu bolgeye
# ulasabilmesi icin ust sinir anma akiminin iki katina kadar acik birakildi.
LOAD_MULTIPLIER_MAX = 2.0
SENSOR_DRIFT_K_PER_H = 2.0    # suruklenen sensorun saatlik kaymasi (TURETILMIS)
SENSOR_DROPPED_BELOW_AMBIENT_K = 8.0  # yerinden dusmus sensor ortamin altini olcer

# Kismi desarj (PD) yalnizca OG icin anlamlidir: rapor 3.7'ye gore 400 V AG panoda
# Paschen minimumunun (~327 V) altinda kalindigi icin PD BEKLENMEZ ve sema pd blogunu
# AG panoda null tanimlar. OG panolarda blok doldurulur.
PD_BASE_PPS = 2.0
PD_BASE_AMP_DBMV = 3.0
PD_NOISE_PHASE_CLUSTER = 0.15   # gurultude faz DUZGUN dagilir -> kumelenme dusuk
PD_FAULT_PHASE_CLUSTER = 0.85   # gercek PD'de faz kumelenir (PRPD imzasi)

# DSYA cikislarinin boy dagilimi (EK-I/8'de 7 cikis var; boy dagilimi TURETILMIS).
_TWO_BOY_FEEDERS = (1, 2, 3)

_DSYA_POINT = re.compile(r"^DSYA(?P<feeder>[1-7])_L(?P<phase>[1-3])$")
_GIRIS_POINT = re.compile(r"^GIRIS_(?P<phase>L1|L2|L3|N)$")

_PHASE_ANGLES_RAD = (0.0, -2.0 * math.pi / 3.0, 2.0 * math.pi / 3.0)


PANO_ID_PREFIX_LEN = 3
PANO_ID_DIGITS = 5
_PANO_PREFIX = re.compile(r"^[A-Z]{%d}$" % PANO_ID_PREFIX_LEN)


# TVOC-2 sensor durum register'i (PDU 222/223): her bit bir dedektor, 1 = OK.
# Fabrika cikisinda tum bitler 1'dir; bir dedektor arizalaninca kendi biti 0 olur.
ALL_DETECTORS_OK = 0xFFFF
DETECTOR_CONNECTORS = ("X2", "X3")
DETECTORS_PER_CONNECTOR = 16
_DETECTOR_RE = re.compile(r"^(X[23]):([0-9]{1,2})$")


def parse_detector(name: str | None) -> tuple[str, int] | None:
    """"X2:4" -> ("X2", 4). None girdi None doner; gecersiz ad ValueError.

    Ad bicimi TVOC-2 kilavuzundaki konnektor:dedektor gosterimidir; demo
    betigi (demo/senaryo/s5.sh) bu adi oldugu gibi gecirir.
    """
    if name is None:
        return None
    match = _DETECTOR_RE.match(name.strip().upper())
    if match is None:
        raise ValueError(
            f"dedektor adi 'X2:4' bicimimde olmali: {name!r} "
            f"(konnektorler: {', '.join(DETECTOR_CONNECTORS)})"
        )
    index = int(match[2])
    if not 1 <= index <= DETECTORS_PER_CONNECTOR:
        raise ValueError(f"dedektor sirasi 1-{DETECTORS_PER_CONNECTOR} araliginda olmali: {name!r}")
    return match[1], index


def contract_point_names(contracts_dir: Path | None = None) -> list[str]:
    """conn_temp nokta adlari — sozlesmeden, koda gomulmeden (PLAN.md kural 10)."""
    directory = contracts_dir or default_contracts_dir()
    blocks = yaml.safe_load((directory / "modbus-map.yaml").read_text(encoding="utf-8"))["blocks"]
    conn_temp = next(b for b in blocks if b["name"] == "conn_temp")
    return list(conn_temp["points"])


def format_pano_id(prefix: str, index: int) -> str:
    """Sozlesme desenine uyan pano kimligi: format_pano_id("adm", 1) -> "ADM-00001"."""
    upper = prefix.upper()
    if not _PANO_PREFIX.match(upper):
        raise ValueError(f"onek {PANO_ID_PREFIX_LEN} harf olmali (A-Z): {prefix!r}")
    if not 1 <= index < 10**PANO_ID_DIGITS:
        raise ValueError(f"index 1 ile {10 ** PANO_ID_DIGITS - 1} arasinda olmali: {index}")
    return f"{upper}-{index:0{PANO_ID_DIGITS}d}"


def default_contracts_dir() -> Path:
    """CONTRACTS_DIR ortam degiskeni, yoksa repo icindeki contracts/ dizini."""
    env = os.getenv("CONTRACTS_DIR")
    if env:
        return Path(env)
    in_repo = Path(__file__).resolve().parents[3] / "contracts"
    return in_repo if in_repo.is_dir() else Path("/contracts")


@dataclass(frozen=True)
class PointSpec:
    """Bir olcum noktasinin degismez fiziksel kimligi."""

    name: str
    rated_a: float      # noktanin bagli oldugu cikisin anma akimi
    share: float        # ana giris akiminin bu noktadan gecen orani
    phase: int | None   # 0/1/2 = L1/L2/L3, None = notr
    k0: float           # saglikli isil direnc indeksi (K = dT / I^2)
    tau_s: float        # isil zaman sabiti


class PanelSimulator:
    """Tek bir panonun kenar telemetrisini uretir.

    Ayni `seed` ayni diziyi verir: senaryolar tekrarlanabilir, testler kararlidir.
    """

    def __init__(
        self,
        pano_id: str,
        seed: int,
        profile: ProfileKind = "karma",
        start: datetime | None = None,
        contracts_dir: Path | None = None,
        medium_voltage: bool = False,
    ) -> None:
        self._contracts_dir = contracts_dir or default_contracts_dir()
        self._thresholds = self._load_thresholds()
        self._validate_pano_id(pano_id)
        if profile not in ("konut", "ticari", "karma"):
            raise ValueError(f"bilinmeyen profil turu: {profile!r}")

        self.pano_id = pano_id
        self.profile: ProfileKind = profile
        self.seed = seed
        self.medium_voltage = medium_voltage

        start_ts = start or datetime.now(timezone.utc)
        if start_ts.tzinfo is None:
            raise ValueError("start saat dilimi tasimali (ingest naive ts'i reddeder)")
        self._ts = start_ts.astimezone(timezone.utc)
        self._started_at = self._ts
        self._seq = 0
        self._frozen_load: float | None = None

        rng = random.Random(seed)
        self._points = self._build_points(rng)
        self._dt_c: dict[str, float] = {spec.name: 0.0 for spec in self._points}
        self._current_a: dict[str, float] = {spec.name: 0.0 for spec in self._points}
        self._held_current_a: dict[str, float] = {}
        self._i2_window: deque[float] = deque(maxlen=EXCITATION_WINDOW)

        # Senaryo enjeksiyonlari (TA2); varsayilan = saglikli pano (S0).
        self._k_multiplier: dict[str, float] = {}
        self._load_multiplier = 1.0
        self._humidity_offset_pct = 0.0
        self._thd_multiplier = 1.0
        self._tvoc_trips = 0
        self._prot_health_ok = True
        self._failed_detector: tuple[str, int] | None = None
        self._sensor_faults: dict[str, str] = {}
        self._pd_activity = 0.0   # 0 = taban gurultusu, 1 = belirgin PD
        self._fault_age_h: dict[str, float] = {}
        self._last_reported_t_c: dict[str, float] = {}

        self._heaviest_phase = rng.randrange(3)
        self._load_noise = Ar1Noise(phi=ar1_phi(10.0, TAU_LOAD_S), sigma=LOAD_NOISE_SIGMA, seed=seed + 1)
        self._unbal_noise = Ar1Noise(phi=ar1_phi(10.0, UNBAL_TAU_S), sigma=UNBAL_SIGMA, seed=seed + 2)
        self._sensor_rng = random.Random(seed + 3)

    # ------------------------------------------------------------ sozlesme okuma

    def _load_thresholds(self) -> dict:
        text = (self._contracts_dir / "alarm-codes.yaml").read_text(encoding="utf-8")
        return yaml.safe_load(text)["thresholds"]

    def _validate_pano_id(self, pano_id: str) -> None:
        schema_path = self._contracts_dir / "mqtt-telemetry.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        pattern = schema["properties"]["pano_id"]["pattern"]
        if not re.match(pattern, pano_id):
            raise ValueError(f"pano_id sozlesme desenine uymuyor ({pattern}): {pano_id!r}")

    def _contract_point_names(self) -> list[str]:
        return contract_point_names(self._contracts_dir)

    # ------------------------------------------------------------- kurulum

    def _build_points(self, rng: random.Random) -> tuple[PointSpec, ...]:
        rated = self._thresholds["rated_current_a"]
        names = self._contract_point_names()

        feeder_rated = {
            n: rated["dsya_2boy"] if n in _TWO_BOY_FEEDERS else rated["dsya_1boy"]
            for n in range(1, 8)
        }
        feeder_total = float(sum(feeder_rated.values()))

        specs: list[PointSpec] = []
        for name in names:
            giris = _GIRIS_POINT.match(name)
            dsya = _DSYA_POINT.match(name)
            if giris:
                phase_name = giris["phase"]
                point_rated = float(rated["main_input"])
                share = 1.0
                phase = None if phase_name == "N" else int(phase_name[1]) - 1
            elif dsya:
                feeder = int(dsya["feeder"])
                point_rated = float(feeder_rated[feeder])
                share = point_rated / feeder_total
                phase = int(dsya["phase"]) - 1
            else:  # pragma: no cover - sozlesme yeni bir nokta turu getirirse
                raise ValueError(f"nokta adi cozumlenemedi: {name}")

            spread = 1.0 + rng.uniform(-K_SPREAD, K_SPREAD)
            specs.append(
                PointSpec(
                    name=name,
                    rated_a=point_rated,
                    share=share,
                    phase=phase,
                    k0=DT_AT_RATED_K / point_rated**2 * spread,
                    tau_s=rng.uniform(TAU_MIN_S, TAU_MAX_S),
                )
            )
        return tuple(specs)

    # ------------------------------------------------------------- disa acilan

    @property
    def point_names(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in self._points)

    def point_k(self, name: str) -> float:
        return self._spec(name).k0

    def point_tau_s(self, name: str) -> float:
        return self._spec(name).tau_s

    def point_current(self, name: str) -> float:
        """Son adimda bu noktadan gecen akim (A)."""
        return self._current_a[name]

    def freeze_load(self, fraction: float) -> None:
        """Yuku sabitler: profil, mevsim ve gurultu devre disi kalir.

        Isil modelin kararli durumunu ve zaman sabitini test etmek icin.
        """
        if not 0.0 <= fraction <= 1.0:
            raise ValueError(f"fraction [0,1] araliginda olmali: {fraction}")
        self._frozen_load = fraction

    # ------------------------------------------------- senaryo enjeksiyonu (TA2)

    def set_k_multiplier(self, pt: str, multiplier: float) -> None:
        """Bir noktanin isil direnc indeksini K0'in katina cikarir (gevsek baglanti).

        Rapor 15.2: "K, 7-30 gun boyunca %0 -> %200 artis". multiplier=3.0 tam olarak
        bu ust siniri temsil eder.
        """
        if multiplier <= 0.0:
            raise ValueError(f"multiplier pozitif olmali: {multiplier}")
        self._spec(pt)  # bilinmeyen nokta adi burada patlasin
        self._k_multiplier[pt] = multiplier

    def set_load_multiplier(self, multiplier: float) -> None:
        """Yuku olcekler (asiri yuk senaryosu). K'ye DOKUNMAZ — ariza degil."""
        if not 0.0 <= multiplier <= LOAD_MULTIPLIER_MAX:
            raise ValueError(f"multiplier [0,{LOAD_MULTIPLIER_MAX}] araliginda olmali: {multiplier}")
        self._load_multiplier = multiplier

    def set_humidity_offset(self, percent: float) -> None:
        """Bagil nemi kaydirir (yogusma senaryosu)."""
        self._humidity_offset_pct = percent

    def set_thd_multiplier(self, multiplier: float) -> None:
        """Akim THD'sini olcekler; notr akimi da formul geregi birlikte artar."""
        if multiplier <= 0.0:
            raise ValueError(f"multiplier pozitif olmali: {multiplier}")
        self._thd_multiplier = multiplier

    def trigger_arc_trip(self) -> None:
        """TVOC-2 trip sayacini artirir (PDU 149). Sayac geri sayilmaz."""
        self._tvoc_trips += 1

    def set_protection_health(self, healthy: bool, detector: str | None = None) -> None:
        """Ark korumasi dedektor sagligi: False = pano sessizce korumasiz.

        `detector` verilirse ("X2:4" gibi) TVOC-2 sensor durum register'inda
        (PDU 222/223) O DEDEKTORUN biti temizlenir. Tespit bunu KULLANMAZ —
        ALM-PROT-HEALTH ozet bit `prot_health_ok` uzerinden cikar (limits.py:268) —
        ama operatore "hangi dedektor?" diye sorulunca cevap yukun icinde olur.
        """
        self._prot_health_ok = healthy
        self._failed_detector = None if healthy else parse_detector(detector)

    def set_pd_activity(self, level: float) -> None:
        """Kismi desarj etkinligi (0 = taban gurultusu, 1 = belirgin PD).

        Yalnizca OG panosunda anlamlidir; AG panoda pd blogu null kalir.
        """
        if not 0.0 <= level <= 1.0:
            raise ValueError(f"level [0,1] araliginda olmali: {level}")
        self._pd_activity = level

    def set_sensor_fault(self, pt: str, kind: str | None) -> None:
        """Sensor arizasi enjekte eder: frozen | drift | dropped; None = temizle."""
        if kind not in (None, "frozen", "drift", "dropped"):
            raise ValueError(f"bilinmeyen sensor arizasi: {kind!r}")
        self._spec(pt)
        if kind is None:
            self._sensor_faults.pop(pt, None)
            self._fault_age_h.pop(pt, None)
        else:
            self._sensor_faults[pt] = kind
            self._fault_age_h[pt] = 0.0

    def clear_injections(self) -> None:
        """Tum enjeksiyonlari kaldirir (senaryo penceresi bitince)."""
        self._k_multiplier.clear()
        self._sensor_faults.clear()
        self._fault_age_h.clear()
        self._load_multiplier = 1.0
        self._humidity_offset_pct = 0.0
        self._thd_multiplier = 1.0

    def _spec(self, name: str) -> PointSpec:
        for spec in self._points:
            if spec.name == name:
                return spec
        raise KeyError(f"bilinmeyen nokta: {name}")

    # ------------------------------------------------------------------ adim

    def step(self, dt_s: float) -> dict:
        """Simulasyonu dt_s kadar ilerletir ve sema-gecerli telemetri sozlugu doner."""
        if dt_s <= 0.0:
            raise ValueError(f"dt_s pozitif olmali: {dt_s}")

        self._ts += timedelta(seconds=dt_s)
        self._seq += 1

        i_ph, unbal = self._phase_currents()
        thd_i = self._thd(i_ph)
        i_n = self._neutral_current(i_ph, thd_i)
        points = self._advance_points(dt_s, i_ph, i_n)

        t_out = self._ambient_c()
        env = self._env_block(t_out, i_ph)
        t_conn = self._point_block(points, t_low_c=env["t_low_c"])

        return {
            "v": SCHEMA_VERSION,
            "ts": self._ts.isoformat(timespec="seconds"),
            "pano_id": self.pano_id,
            "seq": self._seq,
            "fw": FW_VERSION,
            "t_conn": t_conn,
            "elec": self._elec_block(i_ph, i_n, thd_i, unbal),
            "env": env,
            "tvoc": self._tvoc_block(),
            "pd": self._pd_block(),
            "risk": self._risk_block(t_conn),
            "alarms": [],
            "health": self._health_block(),
        }

    # ------------------------------------------------------------- ic hesaplar

    def _load_fraction(self) -> float:
        """Anma akiminin kullanilan orani (0-1)."""
        if self._frozen_load is not None:
            return self._frozen_load * self._load_multiplier
        shape = load_profile(self.profile, self._ts)
        scale = PEAK_UTILISATION / (self._profile_peak() * (1.0 + SEASON_AMPLITUDE))
        raw = shape * scale * season_factor(self._ts) * (1.0 + self._load_noise.step())
        return min(LOAD_MULTIPLIER_MAX, max(0.0, raw * self._load_multiplier))

    def _profile_peak(self) -> float:
        from .profiles import _TABLES  # tek kaynak: tablolar profiles.py'de yasar

        return max(_TABLES[self.profile])

    def _phase_currents(self) -> tuple[list[float], float]:
        i_main = float(self._thresholds["rated_current_a"]["main_input"]) * self._load_fraction()
        if self._frozen_load is not None:
            unbal = UNBAL_CENTER
        else:
            unbal = min(UNBAL_MAX, max(UNBAL_MIN, UNBAL_CENTER + self._unbal_noise.step()))

        # Toplami 3*i_main olacak sekilde dagit: bir faz +u, digerleri -u/2.
        factors = [1.0 - unbal / 2.0] * 3
        factors[self._heaviest_phase] = 1.0 + unbal
        return [round(i_main * f, 1) for f in factors], unbal

    def _thd(self, i_ph: list[float]) -> list[float]:
        """Hafif yukte THD yuksektir (dogrusal olmayan yukun payi buyur)."""
        rated = float(self._thresholds["rated_current_a"]["main_input"])
        light = 1.0 - min(1.0, sum(i_ph) / (3.0 * rated))
        base = THD_BASE_PCT + THD_LIGHT_LOAD_SPAN_PCT * light
        return [round((base + 0.2 * k) * self._thd_multiplier, 2) for k in range(3)]

    def _neutral_current(self, i_ph: list[float], thd_i: list[float]) -> float:
        """Dengesizlik fazor toplami + triplen harmoniklerin aritmetik toplami."""
        re_sum = sum(i * math.cos(a) for i, a in zip(i_ph, _PHASE_ANGLES_RAD))
        im_sum = sum(i * math.sin(a) for i, a in zip(i_ph, _PHASE_ANGLES_RAD))
        fundamental = math.hypot(re_sum, im_sum)

        i_avg = sum(i_ph) / 3.0
        thd_avg = sum(thd_i) / 3.0
        h3 = 3.0 * i_avg * (thd_avg / 100.0) * H3_SHARE_OF_THD
        return round(math.hypot(fundamental, h3), 1)

    def _advance_points(self, dt_s: float, i_ph: list[float], i_n: float) -> dict[str, float]:
        """Nokta basina ayrik isil model: dT[k+1] = a*dT[k] + (1-a)*K*I^2[k].

        SIFIRINCI DERECE TUTUCU: [k, k+1) araliginda etkiyen akim I[k]'dir, yani
        BIR ONCEKI ornegin akimi. Rapor 15.1 de ayni indisi kullanir
        (phi[k] = [dT[k], I^2[k]], hedef dT[k+1]).

        Indis bir kaysaydi (I[k+1] kullanilsaydi) uretec ile kestirimci farkli iki
        modeli cozerdi. 10 s ornekte fark gozle gorulmez ama 15 dakikalik disa
        aktarimda yuk ornekler arasinda cok degistigi icin K kestirimi belirgin
        sapar — olculdu: S1 senaryosunda K/K0 buyumesi gerekirken 0,47'ye dustu.
        """
        for spec in self._points:
            source = i_n if spec.phase is None else i_ph[spec.phase]
            current = source * spec.share
            held = self._held_current_a.get(spec.name, current)
            self._current_a[spec.name] = current
            self._held_current_a[spec.name] = current

            a = math.exp(-dt_s / spec.tau_s)
            steady = spec.k0 * self._k_multiplier.get(spec.name, 1.0) * held**2
            self._dt_c[spec.name] = a * self._dt_c[spec.name] + (1.0 - a) * steady

        self._i2_window.append(sum(i**2 for i in i_ph) / 3.0)
        for pt in self._fault_age_h:
            self._fault_age_h[pt] += dt_s / 3600.0
        return dict(self._dt_c)

    def _excited(self) -> bool:
        """Kalici uyarim kosulu: var(I^2) esigin altindaysa RLS guncellenmez."""
        if len(self._i2_window) < 3:
            return False
        values = list(self._i2_window)
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return variance >= float(self._thresholds["excitation_min_var_i2"])

    def _ambient_c(self) -> float:
        """Dis ortam: gunluk sinus + mevsim (rapor 15.2)."""
        season_position = (season_factor(self._ts) - (1.0 - SEASON_AMPLITUDE)) / (2.0 * SEASON_AMPLITUDE)
        mean = WINTER_MEAN_C + (SUMMER_MEAN_C - WINTER_MEAN_C) * season_position
        amp = WINTER_AMP_K + (SUMMER_AMP_K - WINTER_AMP_K) * season_position
        hour = self._ts.hour + self._ts.minute / 60.0 + self._ts.second / 3600.0
        return mean + amp * math.cos(2.0 * math.pi * (hour - AMBIENT_PEAK_HOUR) / 24.0)

    def _humidity_pct(self, t_c: float) -> float:
        """Nem sicaklikla ters iliskili (sartname Tablo 1'den turetilmis egim)."""
        rh = RH_AT_REF_PCT + RH_SLOPE_PCT_PER_K * (RH_REF_T_C - t_c) + self._humidity_offset_pct
        return min(RH_MAX_PCT, max(RH_MIN_PCT, rh))

    # ------------------------------------------------------------------ bloklar

    def _point_block(self, rises: dict[str, float], t_low_c: float) -> list[dict]:
        excited = self._excited()
        block = []
        for spec in self._points:
            measured_rise = rises[spec.name] + self._sensor_rng.gauss(0.0, TEMP_SENSOR_SIGMA_K)
            t_c = self._apply_sensor_fault(spec.name, t_low_c + measured_rise, t_low_c)
            self._last_reported_t_c[spec.name] = t_c
            block.append(
                {
                    "pt": spec.name,
                    "t_c": round(t_c, 2),
                    "dt_c": round(t_c - t_low_c, 2),
                    "k": round(spec.k0, 12),
                    "k_ratio": 1.0,  # TA1: saglikli taban; RLS kestirimi TA2'de
                    "tau_s": round(spec.tau_s, 1),
                    "ttl_h": None,  # tahmin TA2'de (detect.py)
                    "excited": excited,
                    "q": 0,
                }
            )
        return block

    def _apply_sensor_fault(self, pt: str, t_c: float, ambient_c: float) -> float:
        """Sensor arizasini OLCUME uygular; fiziksel sicaklik degismez.

        Ayrim onemli: ariza sensorde, panoda degil. L-1 katmani bunu ayirt edebilmeli,
        yoksa bozuk sensor sahte bir pano arizasi gibi gorunur (rapor 6.5 L-1).
        """
        kind = self._sensor_faults.get(pt)
        if kind is None:
            return t_c
        if kind == "frozen":
            return self._last_reported_t_c.get(pt, t_c)
        if kind == "drift":
            return t_c + SENSOR_DRIFT_K_PER_H * self._fault_age_h.get(pt, 0.0)
        return ambient_c - SENSOR_DROPPED_BELOW_AMBIENT_K  # dropped

    def _elec_block(self, i_ph: list[float], i_n: float, thd_i: list[float], unbal: float) -> dict:
        rated = float(self._thresholds["rated_current_a"]["main_input"])
        load = sum(i_ph) / (3.0 * rated)
        mean_i = sum(i_ph) / 3.0
        measured_unbal = max(abs(i - mean_i) for i in i_ph) / mean_i * 100.0
        return {
            "i_ph": i_ph,
            "i_n": i_n,
            "u_ph": [
                round(U_PHASE_NOMINAL_V - U_PHASE_DROP_V * load + self._sensor_rng.gauss(0.0, U_PHASE_SIGMA_V), 1)
                for _ in range(3)
            ],
            "thd_i": thd_i,
            "cosphi": round(min(COSPHI_MAX, COSPHI_NO_LOAD + COSPHI_SPAN * load), 3),
            "unbal_pct": round(measured_unbal, 2),
        }

    def _env_block(self, t_out: float, i_ph: list[float]) -> dict:
        rated = float(self._thresholds["rated_current_a"]["main_input"])
        load_sq = min(1.0, (sum(i_ph) / 3.0 / rated) ** 2)
        dt_air = DT_AIR_MAX_K * load_sq + 0.2  # yuksuzken bile dogal cekis var

        t_low = t_out + PANEL_INLET_RISE_K
        t_up = t_low + dt_air
        rh_low = self._humidity_pct(t_low)
        td_low = dew_point(t_low, rh_low)
        return {
            "t_low_c": round(t_low, 2),
            "rh_low_pct": round(rh_low, 1),
            "td_low_c": round(td_low, 2),
            # Yogusma soguk METAL uzerinde olur: referans yuzey dis ortam sicakligindadir.
            "td_margin_k": round(t_out - td_low, 2),
            "t_up_c": round(t_up, 2),
            "rh_up_pct": round(self._humidity_pct(t_up), 1),
            "dt_air_k": round(dt_air, 2),
            "voc_idx": None,  # TVOC-2'de gaz sensoru yok
            "door_open": False,
        }

    def _tvoc_block(self) -> dict:
        """Baslangicta sakin ark korumasi (PLAN.md TA1 Adim 5). SALT OKUNUR (GK6)."""
        sensor_x2, sensor_x3 = ALL_DETECTORS_OK, ALL_DETECTORS_OK
        if self._failed_detector is not None:
            connector, index = self._failed_detector
            mask = ALL_DETECTORS_OK & ~(1 << (index - 1))
            if connector == "X2":
                sensor_x2 = mask
            else:
                sensor_x3 = mask
        return {
            "state": 0 if self._prot_health_ok else 2,  # bit1 = aktif hata (PDU 1300)
            "trips": self._tvoc_trips,
            "det_bits_low": 0,
            "det_bits_high": 0,
            "sensor_x2": sensor_x2,
            "sensor_x3": sensor_x3,
            "amb_light_x2": 0,
            "amb_light_x3": 0,
            "prot_health_ok": self._prot_health_ok,
            "comm_ok": True,
        }

    def _pd_block(self) -> dict | None:
        """HFCT kismi desarj olcumu; AG panoda None (rapor 3.7).

        Ayirt edici, mutlak genlik DEGIL faz kumelenmesidir: gercek PD belirli faz
        acilarinda toplanir (PRPD imzasi), gurultu ise faza duzgun dagilir.
        """
        if not self.medium_voltage:
            return None
        level = self._pd_activity
        return {
            "pps": round(PD_BASE_PPS * (1.0 + 40.0 * level) + abs(self._sensor_rng.gauss(0.0, 0.3)), 2),
            "amp_dbmv": round(PD_BASE_AMP_DBMV + 18.0 * level + self._sensor_rng.gauss(0.0, 0.4), 2),
            "trend": round(level, 3),
            "phase_cluster": round(
                PD_NOISE_PHASE_CLUSTER + (PD_FAULT_PHASE_CLUSTER - PD_NOISE_PHASE_CLUSTER) * level, 3
            ),
        }

    def _risk_block(self, t_conn: list[dict]) -> dict:
        """TA1 yer tutucusu: risk yalnizca L0 uyari esigi asildiktan sonra yukselir.

        Gercek hipotez fuzyonu TA2'de panoalgo.fusion icinde yapilacak.
        """
        warn = float(self._thresholds["term_rise_warn_k"])
        alarm = float(self._thresholds["term_rise_alarm_k"])
        worst = max(point["dt_c"] for point in t_conn)
        score = 100.0 * (worst - warn) / (alarm - warn)
        return {
            "score": int(round(min(100.0, max(0.0, score)))),
            "mode": "HYP-NORMAL",
            "ttl_h": None,
            "contributions": {},
        }

    def _health_block(self) -> dict:
        uptime_s = int((self._ts - self._started_at).total_seconds())
        learning_days = int(self._thresholds["baseline_learning_days"])
        return {
            "uptime_s": uptime_s,
            "nodes_ok": len(self._points),
            "nodes_total": len(self._points),
            "rssi_dbm": -71.0,
            "vbak_pct": 100.0,
            "buffered": 0,
            "maint_mode": False,
            "baseline_day": min(learning_days, 1 + uptime_s // 86_400),
        }
