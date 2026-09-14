"""Pano simulatoru (TA1 Adim 7, Kisi A): fizik ureteci -> MQTT.

Faz 0'daki hello_publisher.py'nin yerini alir. Fark: yuk artik sabit bir sinus
degil, libs/panoalgo icindeki fizik modelidir (saat-of-hafta profili x mevsim x
AR(1) gurultu -> faz akimlari -> nokta basina isil model).

Kullanim:
    python -m sim.panosim --panels 3 --speed 60 --mqtt mosquitto:1883
    python panosim.py --dry-run --panels 1 --max-messages 2     # broker olmadan

Topic, QoS ve retain degerleri contracts/mqtt-telemetry.schema.json icindeki
x-topics blogundan okunur; bu dosyada topic metni YAZILI DEGILDIR (PLAN.md kural 10).

TA2'den itibaren yayinlanan yuk, kenar tespit boru hattindan (panoalgo.edge) gecer:
K/K0, tau, sinira kalan sure, veri kalitesi bitleri ve risk skoru gercek hesaplanir.
Taban ogrenme suresi (sozlesme: baseline_learning_days) SIMULE zamanda dolunca K0
sabitlenir; o ana kadar K/K0 = 1.0 doner ve devreye alma gununde sahte alarm olmaz.

ZAMAN NOTU (13:00 entegrasyon penceresinde ekibe sorulacak): yayinlanan `ts`
SIMULE ZAMANDIR. --speed 60 ile simulasyon saati gercek zamandan 60 kat hizli
akar, yani zaman damgalari duvar saatinin ONUNE gecer. Fizigin anlamli hizda
evrilmesi icin boyle; duvar saatiyle hizali demo isteniyorsa --speed 1 kullanin.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import FrameType

import paho.mqtt.client as mqtt
import yaml
from jsonschema import Draft202012Validator

from panoalgo.edge import EdgePipeline
from panoalgo.generator import PanelSimulator, default_contracts_dir, format_pano_id

TEL_TOPIC_KIND = "tel"
PROFILE_ROTATION = ("konut", "ticari", "karma")
CONNECT_RETRY_S = 2.0
CONNECT_MAX_RETRIES = 30
STATS_EVERY = 6

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
    parser.add_argument("--period", type=float, default=float(os.getenv("SIM_PERIOD_S", "10")),
                        help="iki yayin arasindaki GERCEK sure (s)")
    parser.add_argument("--speed", type=float, default=float(os.getenv("SIM_SPEED", "60")),
                        help="simulasyon hiz carpani; 60 = 1 gercek saniye 1 simule dakika")
    parser.add_argument("--seed", type=int, default=int(os.getenv("SIM_SEED", "1000")))
    parser.add_argument("--prefix", default=os.getenv("SIM_PREFIX", "ADM"), help="pano_id oneki (3 harf)")
    parser.add_argument("--start", default=os.getenv("SIM_START"), help="simulasyon baslangici (ISO 8601, ofsetli)")
    parser.add_argument("--max-messages", type=int, default=0, help="0 = sinirsiz (test icin)")
    parser.add_argument("--profile", default=os.getenv("SIM_PROFILE", "karma"),
                        help="ttl tahmininde kullanilan yuk profili")
    parser.add_argument("--dry-run", action="store_true", help="broker'a baglanma, ekrana yaz")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.panels < 1:
        raise SystemExit("--panels en az 1 olmali")
    if args.speed <= 0 or args.period <= 0:
        raise SystemExit("--speed ve --period pozitif olmali")

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    contracts_dir = default_contracts_dir()
    schema = load_schema(contracts_dir)
    validator = Draft202012Validator(schema)
    topic_template, qos, retain = telemetry_topic_spec(schema)
    print(f"[panosim] sema: {schema['title']} | topic: {topic_template} (qos={qos}, retain={retain})", flush=True)

    sims = build_simulators(args, contracts_dir)
    pipeline = EdgePipeline(profile=args.profile, contracts_dir=contracts_dir)
    baseline_h = _baseline_hours(contracts_dir)
    print(
        f"[panosim] {len(sims)} pano | periyot {args.period} s | hiz x{args.speed} | seed {args.seed}",
        flush=True,
    )
    print(f"[panosim] taban ogrenme: {baseline_h:.0f} simule saat sonra K0 sabitlenir", flush=True)

    client = None if args.dry_run else connect(*_split_host_port(args.mqtt))
    sim_step_s = args.period * args.speed
    published = 0
    rounds = 0
    sim_hours = 0.0

    try:
        while not _stop:
            rounds += 1
            sim_hours += sim_step_s / 3600.0
            if not pipeline.baseline_frozen and sim_hours >= baseline_h:
                pipeline.freeze_baselines()
                print(f"[panosim] taban ogrenme tamamlandi ({sim_hours:.0f} simule saat)", flush=True)

            for sim in sims:
                payload = pipeline.process(sim.step(sim_step_s))

                # SOZLESME KAPISI: gecersiz mesaj yayinlanmaz.
                errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
                if errors:
                    for err in errors[:3]:
                        print(f"[panosim] SEMA HATASI {list(err.absolute_path)}: {err.message}", flush=True)
                    return 1

                topic = topic_template.format(pano_id=payload["pano_id"])
                # allow_nan=False: NaN/Infinity backend'de karantinaya duser (ingest.py:252).
                body = json.dumps(payload, allow_nan=False)
                if client is None:
                    print(f"[panosim] {topic} {body}", flush=True)
                else:
                    client.publish(topic, body, qos=qos, retain=retain)
                published += 1

                if args.max_messages and published >= args.max_messages:
                    _report(sims, published)
                    return 0

            if rounds % STATS_EVERY == 1:
                _report(sims, published)
            time.sleep(args.period)
    finally:
        if client is not None:
            client.loop_stop()
            client.disconnect()
    print(f"[panosim] durduruldu; {published} mesaj yayinlandi", flush=True)
    return 0


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
