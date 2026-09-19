"""Yayin karari katmani (F-36): tespit her turda kosar, seyrelen yalnizca YAYIN.

NE YAPAR
--------
Zenginlestirilmis bir telemetri yukunu alir ve TEK bir soruya cevap verir:
"bu yuk merkeze gonderilsin mi?" Uc kural birlikte calisir:

    1. OLAY            -> aninda yayinla. Alarm kumesi, risk kipi, koruma durumu,
                          veri kalitesi bitleri ya da dugum sayisi degistiyse
                          gecikme yoktur.
    2. OLU BANT        -> izlenen bir buyukluk son YAYINLANAN degerinden esikten
                          fazla uzaklastiysa yayinla.
    3. AZAMI SESSIZLIK -> hicbiri olmasa bile son yayindan bu yana gecen sure
                          `max_silence_s`i astiysa yayinla (heartbeat).

NEDEN VAR
---------
Depoda 18 Eylul'e kadar SABIT ORANLI bir seyreltme vardi: `sim/panobeyni_sim.py`
1 s'de bir tarar, her 10 taramada bir yayinlardi (`--report-every`). Katman
vardi ama UYARLANABILIR degildi: hicbir seyin degismedigi bir gecede de,
baglanti isinirken de ayni hizda yayin yapiyordu. docs/09 §4.4 ve §6 "60 s +
olayda aninda" kaldiracini TAHMIN olarak tasiyor ve "uygulanmadi" isaretliyordu.
Bu modul o kaldiraci olculebilir hale getirir.

TESPITE DOKUNMAZ - MADDENIN CAN DAMARI
--------------------------------------
Bu kapi `EdgePipeline.process()`ten SONRA calisir ve yuku DEGISTIRMEZ. Ornekleme
periyoduna dokunmak fizik motorunu bozardi: unutma faktoru periyoda tasinir
(`detect.lambda_for_period`, docs/05 §3.3) ve ayni lam farkli periyotta farkli
ZAMAN hafizasi demektir. 10 s yerine 60 s'de bir ORNEKLENSEYDI K kestiriminin
etkin hafizasi alti kat uzar, one alma suresi sahte olarak kisalir ve 209
saatlik mansetin altindaki olcum cokerdi. Bu yuzden kapi:

  * hicbir fizik durumu TUTMAZ (yalnizca son yayinlanan degerlerin fotografi),
  * boru hattina referans ALMAZ, ona hicbir sey soylemez,
  * yuku DEGISTIRMEZ (`decide()` salt okunurdur).

Regresyon testi bunu dogrudan sinar: kapi acikken de kapali iken de
EdgePipeline'in gordugu ornek sayisi ve periyot AYNIDIR
(tests/test_reporting.py, "tespit periyodu" baslikli testler).

OLU BANTLAR UYDURULMAZ, SOZLESMEDEN TURETILIR
---------------------------------------------
Her olu bant, ilgili buyuklugun KARAR ARALIGININ sabit bir kesridir
(`DEADBAND_FRACTION`). Karar araligi = normal calisma degeri ile
`contracts/alarm-codes.yaml` icindeki UYARI esigi arasindaki mesafe. Boylece
sozlesmeye YENI bir alan eklenmez ve hicbir esik ikinci kez yazilmaz:

    buyukluk          karar araligi                         varsayilan (%2)
    ---------------   -----------------------------------   ---------------
    t_conn[].dt_c     term_rise_warn_k           (0 -> 50)   1,0 K
    t_conn[].t_c      term_rise_warn_k           (0 -> 50)   1,0 K
    t_conn[].k_ratio  k_ratio_warn            (1,0 -> 1,3)   0,006
    t_conn[].ttl_h    ttl_warn_days x 24    (0 -> 336 saat)   6,72 saat
    elec.i_ph / i_n   current_warn_ratio x rated_current_a   41,6 A
    elec.thd_i        neutral_thd_warn_pct       (0 -> 15)   0,30 %
    env.t_low / t_up  panel_temp_warn_c          (0 -> 40)   0,80 K
    env.td_margin_k   dew_margin_warn_k         (0 -> 3,0)   0,06 K
    env.rh_*          esigi yok; tam olcek      (0 -> 100)   2,0 %
    health.vbak_pct   esigi yok; tam olcek      (0 -> 100)   2,0 %

Bunun ISPATLANABILIR bir sonucu var: yayinlanmayan ornekler sifirinci derece
tutmayla (zero-order hold) geri kurulursa, geri kurulan seri hicbir noktada
gercek degerden olu banttan fazla sapamaz - yani karar araliginin %2'sinden
fazla. Test bunu OLCER, varsaymaz.

AZAMI SESSIZLIK SOZLESMEYE BAGLIDIR
-----------------------------------
Merkez, bir panodan `heartbeat_timeout_min` (5 dk) boyunca veri almazsa
ALM-COMMS-LOST uretir (backend/app/alarm_service.py) ve F-22 ayni fiderde es
zamanli susan panolari TEK kesinti olayina toplar. Uyarlanabilir raporlama bu
yuzden merkezin sessizlik penceresine GIREMEZ: `ReportPolicy` kurulurken
`max_silence_s` sozlesmedeki zaman asiminin YARISINI asarsa hata verir.
Varsayilan 60 s, 300 s'lik zaman asiminin besde biridir.

KAPSAM - NE YAPMAZ
------------------
  * Yuku sikistirmaz, ikili kodlamaz (o ayri bir kaldiractir, docs/09 §6).
  * Kismi yuk (yalnizca degisen alanlar) gondermez: sozlesme tam nesne bekler
    (`mqtt-telemetry.schema.json` required alanlari). Seyreltme MESAJ
    duzeyindedir, ALAN duzeyinde degil.
  * Alarm mandali TUTMAZ: alarm kumesinin her degisimi -belirmesi de kalkmasi
    da- zaten aninda yayin tetikler, yani mandala gerek kalmaz.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .detect import load_thresholds

# Olu bant = karar araliginin bu kesri. Tek sayi, tek yerde; her buyuklugun
# esigi bundan TURETILIR. Buyutmek yayini seyreltir ve geri kurma hatasini ayni
# oranda buyutur; docs/09 olculmus egriyi tasir.
DEADBAND_FRACTION = 0.02

# Varsayilan azami sessizlik (s). docs/09 §4.4 ve §6 "normalde 60 s" der; bu
# modul o TAHMINI olculebilir bir VARSAYILANA cevirir.
DEFAULT_MAX_SILENCE_S = 60.0

# Merkezin sessizlik penceresine karsi guvenlik payi: azami sessizlik,
# heartbeat_timeout_min'in en cok bu kesri olabilir.
SILENCE_SAFETY_FRACTION = 0.5

# Bagimsiz bir sozlesme esigi olmayan yuzde buyuklukleri icin tam olcek.
PERCENT_FULL_SCALE = 100.0

# Yayin gerekcesi etiketleri (olcum ciktilarinda ve kutukte gorunur).
REASON_FIRST = "ilk"
REASON_EVENT = "olay"
REASON_DEADBAND = "olu-bant"
REASON_SILENCE = "sessizlik"
REASON_TRANSPARENT = "saydam"
REASON_SUPPRESSED = ""


class PolicyError(ValueError):
    """Sozlesmeyle celisen bir raporlama politikasi."""


@dataclass(frozen=True)
class ReportPolicy:
    """Olu bantlar (mutlak birimde) ve azami sessizlik suresi.

    `from_contracts()` disinda elle kurulmasi beklenmez: sayilar sozlesmeden
    turetilir ki depoda ikinci bir esik kopyasi olusmasin.
    """

    max_silence_s: float
    dt_c_k: float
    t_c_k: float
    k_ratio: float
    ttl_h: float
    current_a: float
    thd_pct: float
    env_t_k: float
    td_margin_k: float
    rh_pct: float
    vbak_pct: float

    @property
    def transparent(self) -> bool:
        """Saydam politika: hicbir sey bastirilmaz (bugunku sabit oranli davranis)."""
        return self.max_silence_s <= 0.0

    @classmethod
    def passthrough(cls) -> "ReportPolicy":
        """Hicbir seyi bastirmayan politika. VARSAYILAN budur.

        Sebep: `--report-every` ile kurulmus mevcut davranis AYNEN korunur ve
        uyarlanabilir kip acikca secilir (`--adaptive`). Bir teslim oncesinde
        yayin davranisini sessizce degistirmek dogru olmazdi; ayrica olcum de
        ancak iki kip yan yana kosabildiginde durust olur.
        """
        return cls(
            max_silence_s=0.0, dt_c_k=0.0, t_c_k=0.0, k_ratio=0.0, ttl_h=0.0,
            current_a=0.0, thd_pct=0.0, env_t_k=0.0, td_margin_k=0.0, rh_pct=0.0,
            vbak_pct=0.0,
        )

    @classmethod
    def from_contracts(
        cls,
        contracts_dir: Path | None = None,
        *,
        max_silence_s: float = DEFAULT_MAX_SILENCE_S,
        fraction: float = DEADBAND_FRACTION,
    ) -> "ReportPolicy":
        """Olu bantlari sozlesme esiklerinden turetir (modul docstring'indeki tablo)."""
        if not 0.0 < fraction < 1.0:
            raise PolicyError(f"olu bant kesri (0,1) araliginda olmali: {fraction}")
        thresholds = load_thresholds(contracts_dir)

        heartbeat_s = float(thresholds["heartbeat_timeout_min"]) * 60.0
        limit_s = heartbeat_s * SILENCE_SAFETY_FRACTION
        if max_silence_s <= 0.0:
            raise PolicyError(f"azami sessizlik pozitif olmali: {max_silence_s}")
        if max_silence_s > limit_s:
            # Bu bir zevk meselesi degil: merkez bu sureyi asan panoya
            # ALM-COMMS-LOST yazar ve F-22 onu kesinti olayina toplar.
            raise PolicyError(
                f"azami sessizlik {max_silence_s:.0f} s, merkezin sessizlik zaman asiminin "
                f"({heartbeat_s:.0f} s) yarisini ({limit_s:.0f} s) asiyor; pano kesinti sanilir"
            )

        rated_a = float(thresholds["rated_current_a"]["main_input"])
        return cls(
            max_silence_s=max_silence_s,
            dt_c_k=fraction * float(thresholds["term_rise_warn_k"]),
            t_c_k=fraction * float(thresholds["term_rise_warn_k"]),
            k_ratio=fraction * (float(thresholds["k_ratio_warn"]) - 1.0),
            ttl_h=fraction * float(thresholds["ttl_warn_days"]) * 24.0,
            current_a=fraction * float(thresholds["current_warn_ratio"]) * rated_a,
            thd_pct=fraction * float(thresholds["neutral_thd_warn_pct"]),
            env_t_k=fraction * float(thresholds["panel_temp_warn_c"]),
            td_margin_k=fraction * float(thresholds["dew_margin_warn_k"]),
            # rh ve vbak'in sozlesmede SAYISAL esigi yok (ALM-DOOR-UNAUTH ve
            # ALM-LASTGASP merkezde olay olarak degerlendirilir), bu yuzden tam
            # olcek kullanilir. Modul docstring'indeki tablo bunu boyle yazar.
            rh_pct=fraction * PERCENT_FULL_SCALE,
            vbak_pct=fraction * PERCENT_FULL_SCALE,
        )


@dataclass(frozen=True)
class ReportDecision:
    """Kapinin karari. `publish=False` ise `reason` bostur."""

    publish: bool
    reason: str
    detail: str = ""

    def __bool__(self) -> bool:
        return self.publish


def deadband_fields(payload: dict) -> dict[str, float]:
    """Olu banda tabi TUM skaler buyuklukleri tek duz sozlukte toplar.

    Anahtar alanin yuk icindeki yolu, deger sayinin kendisi. Duz sozluk olmasi
    onemli: kapinin baktigi alanlar ile geri kurma hatasini olcen testin
    baktigi alanlar AYNI listeden gelir, yani ikisi sessizce ayrisamaz.
    """
    flat: dict[str, float] = {}

    for point in payload.get("t_conn") or []:
        name = point.get("pt")
        # ttl_h None olabilir (egim henuz kalici degil) ve o durumda listeye HIC
        # girmez: alanin belirmesi/kaybolmasi sayisal bir surunme degil, olaydir.
        for field in ("dt_c", "t_c", "k_ratio", "ttl_h"):
            value = point.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                flat[f"t_conn.{name}.{field}"] = float(value)

    elec = payload.get("elec") or {}
    for index, value in enumerate(elec.get("i_ph") or []):
        flat[f"elec.i_ph.{index}"] = float(value)
    if isinstance(elec.get("i_n"), (int, float)):
        flat["elec.i_n"] = float(elec["i_n"])
    for index, value in enumerate(elec.get("thd_i") or []):
        flat[f"elec.thd_i.{index}"] = float(value)

    env = payload.get("env") or {}
    for field in ("t_low_c", "t_up_c", "rh_low_pct", "rh_up_pct", "td_margin_k"):
        value = env.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            flat[f"env.{field}"] = float(value)

    # vbak_pct merkezde ALM-LASTGASP'in KANITIDIR (backend/app/risk.py); olu bant
    # disinda kalsaydi yedek enerjinin dusus egrisi iki yayin arasinda kaybolurdu.
    health = payload.get("health") or {}
    vbak = health.get("vbak_pct")
    if isinstance(vbak, (int, float)) and not isinstance(vbak, bool):
        flat["health.vbak_pct"] = float(vbak)

    return flat


class UnknownFieldError(KeyError):
    """Olu bandi tanimlanmamis bir alan."""


def deadband_for(policy: ReportPolicy, key: str) -> float:
    """Duz alan anahtarini politikadaki olu banda esler.

    Bilinmeyen anahtar SESSIZCE bir varsayilana DUSMEZ. Dusseydi, ileride yuke
    eklenen bir alan (ornegin gerilim) yanlis birimdeki bir bandi miras alirdi:
    "elec.u_ph" akim bandina (41,6 A) duser ve gerilim pratikte hic yayinlanmazdi.
    Gurultulu bir istisna, sessiz bir yanlis banttan iyidir.
    """
    if key.startswith("t_conn."):
        field = key.rsplit(".", 1)[-1]
        bands = {
            "dt_c": policy.dt_c_k, "t_c": policy.t_c_k,
            "k_ratio": policy.k_ratio, "ttl_h": policy.ttl_h,
        }
        if field not in bands:
            raise UnknownFieldError(key)
        return bands[field]
    if key.startswith("elec.thd_i"):
        return policy.thd_pct
    if key.startswith("elec.i_"):
        return policy.current_a
    if key == "env.td_margin_k":
        return policy.td_margin_k
    if key.startswith("env.rh_"):
        return policy.rh_pct
    if key in ("env.t_low_c", "env.t_up_c"):
        return policy.env_t_k
    if key == "health.vbak_pct":
        return policy.vbak_pct
    raise UnknownFieldError(key)


# Olay fotografindaki alanlarin adlari (kutuk satirinda hangisinin degistigini soyler).
STATE_FIELDS = (
    "alarms", "risk.mode", "tvoc.comm_ok", "tvoc.prot_health_ok", "tvoc.state",
    "tvoc.trips", "health.nodes_ok", "health.nodes_total",
    # env.door_open ve health.maint_mode merkezde okunur (ALM-DOOR-UNAUTH kaniti
    # ve bakim bastirmasi). Ikisi de AYRIK: sayisal bir olu bandin gizleyemeyecegi
    # yerde durmalilar, yoksa kapi acilmasi bir sonraki heartbeat'e kadar beklerdi.
    "env.door_open", "health.maint_mode",
    "t_conn.q",
)


def event_state(payload: dict) -> tuple:
    """Olay sayilan TUM ayrik durumlarin fotografi.

    Buradaki herhangi bir degisim GECIKMESIZ yayin demektir. Liste bilincli
    olarak genistir: sayisal bir olu bandin bir DURUM degisimini gizlemesi,
    bu maddenin sessizce yanlis yapilabilecegi yerdir.
    """
    tvoc = payload.get("tvoc") or {}
    health = payload.get("health") or {}
    risk = payload.get("risk") or {}
    return (
        tuple(sorted(payload.get("alarms") or [])),
        risk.get("mode"),
        tvoc.get("comm_ok"),
        tvoc.get("prot_health_ok"),
        tvoc.get("state"),
        tvoc.get("trips"),
        health.get("nodes_ok"),
        health.get("nodes_total"),
        (payload.get("env") or {}).get("door_open"),
        health.get("maint_mode"),
        tuple(
            (point.get("pt"), point.get("q"), point.get("excited"))
            for point in (payload.get("t_conn") or [])
        ),
    )


def _state_diff(before: tuple | None, after: tuple) -> str:
    """Olayin hangi alandan geldigini tek satirda soyler (kutuk icin)."""
    if before is None:
        return "durum yok"
    changed = [name for name, a, b in zip(STATE_FIELDS, before, after) if a != b]
    return ", ".join(changed) if changed else "durum"


class ReportGate:
    """Pano basina yayin karari; durum pano_id ile anahtarlanir.

    Tek bir kapi yuk testindeki binlerce sanal panoyu da besleyebilir
    (EdgePipeline ile ayni desen).
    """

    def __init__(self, policy: ReportPolicy | None = None) -> None:
        self._policy = policy or ReportPolicy.passthrough()
        self._last_fields: dict[str, dict[str, float]] = {}
        self._last_state: dict[str, tuple] = {}
        self._last_at: dict[str, float] = {}
        self.decided = 0
        self.published = 0
        self.suppressed = 0
        self.by_reason: dict[str, int] = {}

    @property
    def policy(self) -> ReportPolicy:
        return self._policy

    def decide(self, payload: dict, at_s: float) -> ReportDecision:
        """Yuku YAYINLAMADAN once cagrilir. Yuku DEGISTIRMEZ (salt okunur).

        `at_s` monoton bir saniye sayacidir (duvar saati ya da simule zaman);
        kapi onu yalnizca fark almak icin kullanir.
        """
        self.decided += 1
        pano_id = payload["pano_id"]
        fields = deadband_fields(payload)
        state = event_state(payload)

        decision = self._decide(pano_id, fields, state, at_s)
        if decision.publish:
            # Fotograf YALNIZCA yayinlandiginda guncellenir: olu bant, son
            # YAYINLANAN degere gore olculur. Her turda guncellenseydi yavas ama
            # surekli bir surunme (drift) hicbir zaman yayin tetiklemez, sinira
            # kadar sessizce yurunurdu.
            self._last_fields[pano_id] = fields
            self._last_state[pano_id] = state
            self._last_at[pano_id] = at_s
            self.published += 1
        else:
            self.suppressed += 1
        self.by_reason[decision.reason] = self.by_reason.get(decision.reason, 0) + 1
        return decision

    def _decide(self, pano_id: str, fields: dict[str, float], state: tuple,
                at_s: float) -> ReportDecision:
        previous = self._last_fields.get(pano_id)
        if previous is None:
            return ReportDecision(True, REASON_FIRST, "ilk ornek")

        last_state = self._last_state.get(pano_id)
        if state != last_state:
            return ReportDecision(True, REASON_EVENT, _state_diff(last_state, state))

        policy = self._policy
        if policy.transparent:
            # Taban kip: gerekce ayri etiketlenir ki olcum ciktisinda "olu bant
            # tetikledi" ile "hicbir kural yok" karismasin.
            return ReportDecision(True, REASON_TRANSPARENT, "saydam politika")

        for key, value in fields.items():
            before = previous.get(key)
            if before is None:
                # Alan yeni belirdi (ornegin K kestirimi ilk kez olustu): bu bir
                # durum degisimidir, sayisal bir surunme degil.
                return ReportDecision(True, REASON_EVENT, f"{key} belirdi")
            band = deadband_for(policy, key)
            if abs(value - before) > band:
                return ReportDecision(
                    True, REASON_DEADBAND, f"{key} {abs(value - before):.4g} > {band:.4g}"
                )

        for key in previous:
            if key not in fields:
                return ReportDecision(True, REASON_EVENT, f"{key} kayboldu")

        silent_s = at_s - self._last_at.get(pano_id, at_s)
        if silent_s >= policy.max_silence_s:
            return ReportDecision(True, REASON_SILENCE, f"{silent_s:.0f} s sessiz")

        return ReportDecision(False, REASON_SUPPRESSED, f"{silent_s:.0f} s sessiz")
