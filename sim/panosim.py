"""Pano simulatoru (TA1 Adim 7, Kisi A): fizik ureteci -> MQTT.

Faz 0'daki hello_publisher.py'nin yerini alir. Fark: yuk artik sabit bir sinus
degil, libs/panoalgo icindeki fizik modelidir (saat-of-hafta profili x mevsim x
AR(1) gurultu -> faz akimlari -> nokta basina isil model).

IKI KIP VARDIR:

  1. SUREKLI KIP (varsayilan) — saglikli filo trafigi, sonsuza kadar.
        python -m sim.panosim --panels 3 --speed 60 --mqtt mosquitto:1883
        python panosim.py --dry-run --panels 1 --max-messages 2     # broker olmadan

  2. SENARYO KIPI (--scenario) — etiketli bir ariza senaryosunu CANLI oynatir.
        python -m sim.panosim --scenario S1_loose_conn --point DSYA3_L2 \
               --pano SIM-00001 --duration 90
     Oynatilan fizik, data/fixtures/ altindaki etiketli CSV'leri ve docs/12
     dogrulama tablosunu ureten fizikle BIREBIR AYNIDIR: ikisi de
     panoalgo.scenarios.iter_samples() yurutucusunu kullanir. "Demoda baska,
     raporda baska" olmasi mumkun degildir. Senaryo katalogu: --list-scenarios.

Topic, QoS ve retain degerleri contracts/mqtt-telemetry.schema.json icindeki
x-topics blogundan okunur; bu dosyada topic metni YAZILI DEGILDIR (PLAN.md kural 10).

TA2'den itibaren yayinlanan yuk, kenar tespit boru hattindan (panoalgo.edge) gecer:
K/K0, tau, sinira kalan sure, veri kalitesi bitleri ve risk skoru gercek hesaplanir.
Taban ogrenme suresi (sozlesme: baseline_learning_days) SIMULE zamanda dolunca K0
sabitlenir; o ana kadar K/K0 = 1.0 doner ve devreye alma gununde sahte alarm olmaz.

ZAMAN DAMGASI KARARI (K3, 15 Eylul — daha once "ekibe sorulacak" diye asili duruyordu)
--------------------------------------------------------------------------------------
Fizik HIZLANDIRILMIS kalir, yayinlanan `ts` DUVAR SAATIDIR (--wall-clock, varsayilan).

Neden: --speed 60 ile simulasyon saati gercek zamandan 60 kat hizli akar. Eskiden
`ts` de simule zamandi, yani zaman damgalari duvar saatinin onune geciyordu —
11 dakikalik bir kosuda 10,5 saat ileri, 11.757 satir gelecege tarihli. Arayuzdeki
trend/K trendi/ciy grafikleri `to = new Date()` penceresi kullandigi icin yeni veri
grafige HIC girmiyordu (frontend/src/pages/TrendKorelasyon.tsx:52).

Sonuc: kenar alanlari (K/K0, tau, ttl_h) SIMULE zamanda hesaplanir — fizik dogrudur —
ama yayin ani duvar saatiyle damgalanir. Grafikte x ekseni gercek zamandir ve egri
60 kat sikistirilmistir. Bu bilincli bir sunum secimidir ve docs/14 §7'de yazilidir.

Eski davranis gerekiyorsa (or. uzun vadeli veri uretimi): --sim-clock.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import FrameType

import paho.mqtt.client as mqtt
import yaml
from jsonschema import Draft202012Validator

from panoalgo import reporting, scenarios
from panoalgo.edge import EdgePipeline
from panoalgo.generator import PanelSimulator, default_contracts_dir, format_pano_id

TEL_TOPIC_KIND = "tel"
PROFILE_ROTATION = ("konut", "ticari", "karma")
CONNECT_RETRY_S = 2.0
CONNECT_MAX_RETRIES = 30
STATS_EVERY = 6

# Senaryo kipi: iki yayin arasindaki duvar saati suresi. 1 s'den kisa olmamali,
# cunku `ts` saniye cozunurlugundedir (timespec="seconds") ve ayni saniyeye iki
# ornek dusmesi trend grafiginde ust uste biner.
REPLAY_MIN_PERIOD_S = 1.0
REPLAY_PERIOD_S = 1.0
DEFAULT_REPLAY_DURATION_S = 60.0

# Kenarin ASLA basmadigi, MERKEZDE uretilen kodlar. S6'nin etiketi bunu bekler ama
# alarmi backend/app/alarm_service.py:41 uretir (kenar sussa bile). Oynatma raporu
# "kacirildi" demesin diye ayri gosterilir; panoalgo/central.py ayni ayrimi yapar.
CENTRAL_ONLY_CODES = frozenset({"ALM-COMMS-LOST"})

_stop = False


def _request_stop(signum: int, frame: FrameType | None) -> None:
    global _stop
    _stop = True


def load_schema(contracts_dir: Path) -> dict:
    return json.loads((contracts_dir / "mqtt-telemetry.schema.json").read_text(encoding="utf-8"))


def telemetry_topic_spec(schema: dict) -> tuple[str, int, bool]:
    """x-topics icinden telemetri topic sablonu, QoS ve retain degerini cikarir."""
    topics = schema["x-topics"]
    for template, spec in topics.items():
        if template.rstrip("/").endswith("/" + TEL_TOPIC_KIND):
            return template, int(spec["qos"]), bool(spec["retain"])
    raise ValueError(f"x-topics icinde '{TEL_TOPIC_KIND}' topic'i bulunamadi: {list(topics)}")


def build_simulators(args: argparse.Namespace, contracts_dir: Path) -> list[PanelSimulator]:
    start = datetime.fromisoformat(args.start) if args.start else datetime.now(timezone.utc)
    if start.tzinfo is None:
        raise SystemExit("--start saat dilimi tasimali, ornek: 2026-09-16T00:00:00+00:00")

    return [
        PanelSimulator(
            pano_id=format_pano_id(args.prefix, index),
            seed=args.seed + index,
            profile=PROFILE_ROTATION[(index - 1) % len(PROFILE_ROTATION)],
            start=start,
            contracts_dir=contracts_dir,
        )
        for index in range(1, args.panels + 1)
    ]


def connect(host: str, port: int) -> mqtt.Client:
    """Broker hazir olmadan baslayabiliriz (compose depends_on: service_started)."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="panosim")
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    for attempt in range(1, CONNECT_MAX_RETRIES + 1):
        try:
            client.connect(host, port, keepalive=60)
        except OSError as exc:
            print(f"[panosim] {host}:{port} henuz yok ({exc}); {attempt}/{CONNECT_MAX_RETRIES}", flush=True)
            time.sleep(CONNECT_RETRY_S)
        else:
            client.loop_start()
            print(f"[panosim] {host}:{port} baglandi", flush=True)
            return client
    raise SystemExit(f"[panosim] {host}:{port} baglanti kurulamadi")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    host_port = os.getenv("MQTT_HOST", "mosquitto") + ":" + os.getenv("MQTT_PORT", "1883")
    parser = argparse.ArgumentParser(description="Fizik tabanli pano telemetri simulatoru")
    parser.add_argument("--mqtt", default=host_port, metavar="HOST:PORT")
    parser.add_argument("--panels", type=int, default=int(os.getenv("SIM_PANELS", "3")))
    parser.add_argument("--period", type=float, default=None,
                        help="iki yayin arasindaki GERCEK sure (s); surekli kipte varsayilan "
                             "SIM_PERIOD_S (10), senaryo kipinde 1")
    parser.add_argument("--speed", type=float, default=float(os.getenv("SIM_SPEED", "60")),
                        help="simulasyon hiz carpani; 60 = 1 gercek saniye 1 simule dakika")
    parser.add_argument("--seed", type=int, default=int(os.getenv("SIM_SEED", "1000")))
    parser.add_argument("--prefix", default=os.getenv("SIM_PREFIX", "ADM"), help="pano_id oneki (3 harf)")
    parser.add_argument("--start", default=os.getenv("SIM_START"), help="simulasyon baslangici (ISO 8601, ofsetli)")
    parser.add_argument("--max-messages", type=int, default=0, help="0 = sinirsiz (test icin)")
    parser.add_argument("--profile", default=os.getenv("SIM_PROFILE", "karma"),
                        help="ttl tahmininde kullanilan yuk profili")
    parser.add_argument("--dry-run", action="store_true", help="broker'a baglanma, ekrana yaz")

    adaptive = parser.add_argument_group(
        "uyarlanabilir raporlama (F-36)",
        "Yalnizca SUREKLI kipte gecerlidir. Seyrelen YAYINDIR: tespit (EdgePipeline) her "
        "turda aynen kosar. Senaryo kipi bu kapiyi HIC gormez, cunku orada seyreltme zaten "
        "vardir (bkz. _run_scenario 'her N. ornek').",
    )
    adaptive.add_argument("--adaptive", action="store_true",
                          help="olu bant + azami sessizlik + olayda aninda yayin (varsayilan KAPALI)")
    adaptive.add_argument("--deadband-fraction", type=float, default=reporting.DEADBAND_FRACTION,
                          help="olu bant, karar araliginin bu kesri (varsayilan %(default)s)")
    adaptive.add_argument("--max-silence", type=float, default=reporting.DEFAULT_MAX_SILENCE_S,
                          help="azami sessizlik (s); sozlesmedeki heartbeat_timeout_min'in "
                               "yarisini asamaz (varsayilan %(default)s)")

    clock = parser.add_mutually_exclusive_group()
    clock.add_argument("--wall-clock", dest="wall_clock", action="store_true", default=None,
                       help="yayinlanan ts duvar saati olsun (VARSAYILAN, bkz. K3 notu)")
    clock.add_argument("--sim-clock", dest="wall_clock", action="store_false",
                       help="eski davranis: yayinlanan ts SIMULE zaman (duvar saatinin onune gecer)")

    replay = parser.add_argument_group(
        "senaryo kipi",
        "Etiketli bir ariza senaryosunu canli oynatir (demo/senaryo/s*.sh bunu cagirir).",
    )
    replay.add_argument("--scenario", metavar="SCENARIO_ID",
                        help="oynatilacak senaryo; katalog icin --list-scenarios")
    replay.add_argument("--list-scenarios", action="store_true", help="senaryo katalogunu yaz ve cik")
    replay.add_argument("--pano", metavar="PANO_ID", help="senaryonun yayinlanacagi pano (or. SIM-00001)")
    replay.add_argument("--duration", type=float, default=DEFAULT_REPLAY_DURATION_S,
                        help="oynatmanin DUVAR SAATI suresi (s); varsayilan 60")
    replay.add_argument("--scenario-hours", type=float, default=None,
                        help="senaryonun SIMULE suresi (s); varsayilan senaryonun kendi degeri")
    replay.add_argument("--point", help="enjeksiyon noktasi (or. DSYA3_L2); senaryonunkini gecersiz kilar")
    replay.add_argument("--detector", help="S5 icin arizali TVOC-2 dedektoru (or. X2:4)")
    replay.add_argument("--baseline-hours", type=float, default=None,
                        help="taban ogrenme suresini KISALT (canli demo; sozlesme degeri 168 h)")
    replay.add_argument("--season", choices=("kis", "gecis", "yaz"), default=None,
                        help="senaryonun mevsimini gecersiz kil (CANLI demo icin; docs/12 fixture'lari "
                             "her zaman senaryonun kendi mevsimiyle uretilir)")
    return parser.parse_args(argv)


class Stamper:
    """Yayinlanan `ts`i duvar saatine hizalar (K3); kip kapaliysa hicbir sey yapmaz.

    Saniye cozunurlugunde KESIN ARTAN damga uretir: ayni saniyede iki ornek
    yayinlanirsa ikincisi bir saniye ileri kaydirilir. Aksi halde trend grafiginde
    ust uste binerler ve TimescaleDB'de (ts, pano_id, tag) tekrar eder.
    """

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self._last: dict[str, datetime] = {}

    def stamp(self, payload: dict) -> dict:
        if not self.enabled:
            return payload
        pano_id = payload["pano_id"]
        now = datetime.now(timezone.utc).replace(microsecond=0)
        previous = self._last.get(pano_id)
        if previous is not None and now <= previous:
            now = previous + timedelta(seconds=1)
        self._last[pano_id] = now
        payload["ts"] = now.isoformat(timespec="seconds")
        return payload


class Publisher:
    """Sozlesme kapisi + topic cozumu + yayin. Iki kip de bunu kullanir."""

    def __init__(self, schema: dict, client: mqtt.Client | None, stamper: Stamper,
                 prefix: str = "panosim") -> None:
        self._validator = Draft202012Validator(schema)
        self._template, self._qos, self._retain = telemetry_topic_spec(schema)
        self._client = client
        self._stamper = stamper
        self._prefix = prefix   # log satirlari cagiran araci gostersin (panosim / panobeyni)
        self.published = 0

    @property
    def topic_template(self) -> str:
        return self._template

    @property
    def qos_retain(self) -> tuple[int, bool]:
        return self._qos, self._retain

    def send(self, payload: dict) -> bool:
        """Yayinlar; sema ihlalinde False doner (ve mesaj YAYINLANMAZ)."""
        payload = self._stamper.stamp(payload)
        errors = sorted(self._validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
        if errors:
            for err in errors[:3]:
                print(f"[{self._prefix}] SEMA HATASI {list(err.absolute_path)}: {err.message}", flush=True)
            return False

        topic = self._template.format(pano_id=payload["pano_id"])
        # allow_nan=False: NaN/Infinity backend'de karantinaya duser (ingest.py:252).
        body = json.dumps(payload, allow_nan=False)
        if self._client is None:
            print(f"[{self._prefix}] {topic} {body}", flush=True)
        else:
            self._client.publish(topic, body, qos=self._qos, retain=self._retain)
        self.published += 1
        return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list_scenarios:
        for entry in scenarios.list_scenarios():
            print(f"{entry['scenario_id']:<16} {entry['default_duration_h']:>7.0f} h  {entry['text']}")
        return 0
    if args.panels < 1:
        raise SystemExit("--panels en az 1 olmali")
    if args.period is not None and args.period <= 0:
        raise SystemExit("--period pozitif olmali")
    if args.speed <= 0:
        raise SystemExit("--speed pozitif olmali")
    if args.adaptive and args.scenario:
        # Senaryo kipinde seyreltme ZATEN var ("her N. ornek", asagida) ve betik
        # kac mesaj yayinlayacagini basarken soz veriyor. Ikinci bir kapi o sozu
        # yalan yapar ve S0/S1 demolarinin trend grafigini bosaltir.
        raise SystemExit("--adaptive yalnizca surekli kipte gecerlidir (--scenario ile kullanilamaz)")

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    contracts_dir = default_contracts_dir()
    schema = load_schema(contracts_dir)
    # Varsayilan duvar saati (K3). --sim-clock ile eski davranisa donulur.
    stamper = Stamper(_wants_wall_clock(args))
    client = None if args.dry_run else connect(*_split_host_port(args.mqtt))
    publisher = Publisher(schema, client, stamper)
    print(
        f"[panosim] sema: {schema['title']} | topic: {publisher.topic_template} "
        f"(qos={publisher.qos_retain[0]}, retain={publisher.qos_retain[1]})",
        flush=True,
    )
    print(f"[panosim] zaman damgasi: {'DUVAR SAATI' if stamper.enabled else 'SIMULE ZAMAN'}", flush=True)

    try:
        if args.scenario:
            return _run_scenario(args, publisher, contracts_dir)
        return _run_stream(args, publisher, contracts_dir)
    finally:
        if client is not None:
            client.loop_stop()
            client.disconnect()


def _wants_wall_clock(args: argparse.Namespace) -> bool:
    if args.wall_clock is not None:
        return args.wall_clock
    return os.getenv("SIM_WALL_CLOCK", "1").strip().lower() not in ("0", "false", "hayir", "no")


# ------------------------------------------------------------------ surekli kip


def _build_gate(args: argparse.Namespace, contracts_dir: Path) -> reporting.ReportGate:
    """Yayin kapisi. Bayrak verilmediyse HICBIR SEYI bastirmaz (bugunku davranis).

    Varsayilanin saydam olmasi bilincli: teslim oncesi yayin davranisini sessizce
    degistirmek yerine uyarlanabilir kip acikca secilir. Olcum de ancak iki kip
    yan yana kosabildiginde durust olur (loadtest/veri_butcesi.py).
    """
    if not getattr(args, "adaptive", False):
        return reporting.ReportGate(reporting.ReportPolicy.passthrough())
    try:
        policy = reporting.ReportPolicy.from_contracts(
            contracts_dir, max_silence_s=args.max_silence, fraction=args.deadband_fraction
        )
    except reporting.PolicyError as exc:
        raise SystemExit(f"uyarlanabilir raporlama kurulamadi: {exc}") from exc
    print(
        f"[panosim] uyarlanabilir raporlama: olu bant %{args.deadband_fraction * 100:g}, "
        f"azami sessizlik {policy.max_silence_s:.0f} GERCEK s (tespit periyodu DEGISMEDI)",
        flush=True,
    )
    if abs(args.speed - 1.0) > 1e-9:
        # Hizlandirilmis simulasyonda fizik gercek saniye basina --speed kat hizli
        # degisir; olu bantlar hemen asilir ve seyrelme gorunmez olur. Bu bir hata
        # DEGIL, olcegin kendisidir: banner'in seyrelme vaat edip etmedigi
        # karistirilmasin diye acikca soylenir. Olculen oran docs/09'dadir ve
        # loadtest/veri_butcesi.py ile x1 hizda alinmistir.
        print(
            f"[panosim] UYARI: --speed x{args.speed:g} ile fizik gercek zamandan hizli akar; "
            "uyarlanabilir raporlama bu kipte az seyreltir. Olculen oran icin "
            "loadtest/veri_butcesi.py kullanin.",
            flush=True,
        )
    return reporting.ReportGate(policy)


def _run_stream(args: argparse.Namespace, publisher: Publisher, contracts_dir: Path) -> int:
    period = args.period if args.period is not None else float(os.getenv("SIM_PERIOD_S", "10"))
    if period <= 0:
        raise SystemExit("SIM_PERIOD_S pozitif olmali")
    args.period = period
    sims = build_simulators(args, contracts_dir)
    pipeline = EdgePipeline(profile=args.profile, contracts_dir=contracts_dir)
    gate = _build_gate(args, contracts_dir)
    baseline_h = args.baseline_hours if args.baseline_hours is not None else _baseline_hours(contracts_dir)
    print(
        f"[panosim] {len(sims)} pano | periyot {args.period} s | hiz x{args.speed} | seed {args.seed}",
        flush=True,
    )
    print(f"[panosim] taban ogrenme: {baseline_h:.0f} simule saat sonra K0 sabitlenir", flush=True)

    sim_step_s = args.period * args.speed
    rounds = 0
    sim_hours = 0.0
    started = time.monotonic()

    while not _stop:
        rounds += 1
        sim_hours += sim_step_s / 3600.0
        if not pipeline.baseline_frozen and sim_hours >= baseline_h:
            pipeline.freeze_baselines()
            print(f"[panosim] taban ogrenme tamamlandi ({sim_hours:.0f} simule saat)", flush=True)

        for sim in sims:
            # TESPIT HER TURDA KOSAR. Kapi yalnizca YAYINI eler ve process()
            # cagrisini kosullu hale GETIRMEZ; getirseydi RLS'in ornekleme
            # periyodu sessizce degisir ve K kestirimi bozulurdu (F-36).
            payload = pipeline.process(sim.step(sim_step_s))

            # Kapi GERCEK saate bakar, simule saate DEGIL. Sebep sozlesmededir:
            # azami sessizlik, merkezin heartbeat_timeout_min penceresine karsi
            # guvenli olsun diye secilir ve merkez GERCEK zamanla olcer
            # (backend/app/alarm_service.py). Simule saniye kullanilsaydi --speed
            # carpani emniyet payini tek basina belirlerdi: x60'ta 60 s'lik azami
            # sessizlik 1 gercek saniye olur (hicbir sey seyrelmez), x0,1'de ise
            # 150 s'lik ust sinir 1500 gercek saniyeye cikip merkezin 300 s'lik
            # esigini asar ve pano KESINTI sanilirdi.
            if not gate.decide(payload, time.monotonic() - started).publish:
                continue

            # send()'in False'u "SEMA IHLALI"dir ve olumculdur; "yayinlamadim"
            # ile ayni kanaldan tasinmaz (bu yuzden kapi send'in DISINDA durur).
            if not publisher.send(payload):
                return 1
            if args.max_messages and publisher.published >= args.max_messages:
                _report(sims, publisher.published)
                return 0

        if rounds % STATS_EVERY == 1:
            _report(sims, publisher.published)
        time.sleep(args.period)

    print(f"[panosim] durduruldu; {publisher.published} mesaj yayinlandi", flush=True)
    return 0


# ------------------------------------------------------------------ senaryo kipi


def _run_scenario(args: argparse.Namespace, publisher: Publisher, contracts_dir: Path) -> int:
    """Etiketli senaryoyu duvar saatine yayarak canli oynatir."""
    try:
        plan = scenarios.plan(
            args.scenario,
            seed=args.seed,
            duration_h=args.scenario_hours,
            contracts_dir=contracts_dir,
            pano_id=args.pano,
            point=args.point,
            detector=args.detector,
            baseline_h=args.baseline_hours,
            season=args.season,
        )
    except ValueError as exc:
        raise SystemExit(f"[panosim] {exc}") from exc

    if args.duration <= 0.0:
        raise SystemExit("--duration pozitif olmali")

    # Senaryo kipi SIM_PERIOD_S'i (surekli kipin 10 s'i) MIRAS ALMAZ: 60 sn'lik bir
    # demoda 10 s'lik periyot yalnizca 6 nokta cizerdi. Acikca --period verilirse o gecerlidir.
    period = max(args.period if args.period is not None else REPLAY_PERIOD_S, REPLAY_MIN_PERIOD_S)
    wanted = max(1, round(args.duration / period))
    # SEYRELTME: fizik 15 dakikalik adimlarla kosar (gercek kenar da boyle ozetler),
    # ama hepsini yayinlamayiz. Gercek kenarin "1 s isle, 10 s'de bir ozet gonder"
    # davranisinin ta kendisi; yalnizca oran demo suresine gore secilir.
    every = max(1, round(plan.steps / wanted))
    emits = len(range(0, plan.steps, every))

    print(
        f"[panosim] SENARYO {plan.scenario_id} | pano {plan.pano_id} | nokta {plan.spec.point}"
        + (f" | dedektor {args.detector}" if args.detector else ""),
        flush=True,
    )
    print(f"[panosim] {plan.spec.text}", flush=True)
    print(
        f"[panosim] {plan.duration_h:.0f} simule saat -> ~{emits * period:.0f} s duvar saati "
        f"({emits} mesaj, her {every}. ornek, {period:.0f} s arayla)",
        flush=True,
    )
    print(
        f"[panosim] taban ogrenme {plan.baseline_h:.1f} simule saat, sonra enjeksiyon baslar; "
        f"beklenen alarmlar: {', '.join(plan.spec.expect) or '(yok — S0 tabani)'}",
        flush=True,
    )

    seen: dict[str, float] = {}
    silent = 0
    slots = 0
    # HIZ AYARI son teslim tarihine gore: fizik hesabi ne kadar surerse sursun
    # oynatma --duration'da biter. Sabit sleep(period) olsaydi 2880 adimlik S1
    # istenen 90 s yerine 100 s'nin uzerine tasardi (demo suresi tutmazdi).
    began = time.monotonic()
    for sample in scenarios.iter_samples(plan):
        if _stop:
            break
        if sample.index % every:
            continue
        if sample.payload is None:
            # Haberlesme boslugu: sahte deger URETILMEZ, hicbir sey yayinlanmaz.
            silent += 1
        else:
            for code in sample.payload["alarms"]:
                if code not in seen:
                    seen[code] = sample.hours
                    print(f"[panosim]   -> {code} ({sample.hours:.1f}. simule saat)", flush=True)
            if not publisher.send(sample.payload):
                return 1
            if args.max_messages and publisher.published >= args.max_messages:
                break
        slots += 1
        time.sleep(max(0.0, began + slots * period - time.monotonic()))

    print(f"[panosim] senaryo bitti; {publisher.published} mesaj yayinlandi", flush=True)
    if silent:
        print(f"[panosim] {silent} ornek haberlesme boslugunda YAYINLANMADI (bilincli)", flush=True)
    _report_scenario(plan, seen)
    return 0


def _report_scenario(plan: scenarios.ScenarioPlan, seen: dict[str, float]) -> None:
    """Beklenen / cikan alarm karsilastirmasi — demoda ekrana okunur sekilde."""
    expected = set(plan.spec.expect)
    forbidden = set(plan.spec.not_expect)
    if seen:
        print("[panosim] cikan alarmlar: " + ", ".join(
            f"{code} ({hours:.1f} h)" for code, hours in sorted(seen.items(), key=lambda kv: kv[1])
        ), flush=True)
    else:
        print("[panosim] hic alarm cikmadi", flush=True)

    central = sorted(expected & CENTRAL_ONLY_CODES)
    if central:
        print(
            f"[panosim] {', '.join(central)} kenarda URETILMEZ; merkez heartbeat denetimi basar "
            f"(backend, heartbeat_timeout_min) — arayuzun alarm konsolunda gorunur",
            flush=True,
        )
    edge_expected = expected - CENTRAL_ONLY_CODES
    if edge_expected:
        missing = sorted(edge_expected - set(seen))
        print(
            f"[panosim] beklenenlerden {len(edge_expected) - len(missing)}/{len(edge_expected)} gorundu"
            + (f"; kisa oynatmada gorunmeyen: {', '.join(missing)}" if missing else ""),
            flush=True,
        )
    fired = sorted(forbidden & set(seen))
    if fired:
        print(f"[panosim] DIKKAT — cikmamasi gereken alarm cikti: {', '.join(fired)}", flush=True)


def _baseline_hours(contracts_dir: Path) -> float:
    """Taban ogrenme suresi sozlesmeden okunur (baseline_learning_days)."""
    data = yaml.safe_load((contracts_dir / "alarm-codes.yaml").read_text(encoding="utf-8"))
    return float(data["thresholds"]["baseline_learning_days"]) * 24.0


def _split_host_port(value: str) -> tuple[str, int]:
    host, _, port = value.partition(":")
    if not host or not port.isdigit():
        raise SystemExit(f"--mqtt HOST:PORT biciminde olmali: {value!r}")
    return host, int(port)


def _report(sims: list[PanelSimulator], published: int) -> None:
    head = sims[0]
    print(
        f"[panosim] {published} mesaj | {len(sims)} pano | ilk pano {head.pano_id} "
        f"profil={head.profile} (sema gecerli)",
        flush=True,
    )


if __name__ == "__main__":
    sys.exit(main())
