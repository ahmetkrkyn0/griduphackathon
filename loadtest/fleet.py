#!/usr/bin/env python3
"""Sanal pano filosu yuk testi (TB3 Adim 4, Kisi B).

Olculenler: yayin hizi (mesaj/s), alim gecikmesi (yayin -> backend'in mesaji aldigi an), gorunme gecikmesi
(yayin -> son durumun veritabaninda okunabildigi an), backend / TimescaleDB / Mosquitto CPU ve RAM,
telemetri tablosunun buyumesi ve gun basina projeksiyonu, alarm acilma ve alarm -> SMS gecikmesi.
Sonuc: loadtest/results/<run_id>.json (git disi) + loadtest_metrics tablosu (Grafana "Olcek" panosu).

Yuk kaynagi SABLON'dur: sozlesmeye (contracts/mqtt-telemetry.schema.json) uyan, zamanla degisen ama fiziksel
model olmayan yuk. Platformu (broker -> ingest -> DB -> alarm -> bildirim) olcer; tespit basarisini OLCMEZ
(o docs/12, Kisi A). panoalgo uretecine gecis A'nin paketi geldiginde eklenecek (kod kopyalanmaz, import edilir).

Calistirma (yigin ayaktayken, repo kokunden):
    backend/.venv/Scripts/python loadtest/fleet.py --panels 1000 --duration 300
    backend/.venv/Scripts/python loadtest/fleet.py --cleanup-only

Test bitince SIM-* verisi silinir ve backend yeniden baslatilir (--keep ile kalir): bellekteki alarm yoneticisi
1.000 sessiz pano icin 5 dk sonra ALM-COMMS-LOST uretmesin.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import random
import re
import subprocess
import sys
import threading
import time
import urllib.request
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Contracts, load_contracts  # noqa: E402
from app.scada.map_loader import load_map  # noqa: E402

CONTAINERS = ("gridup-backend", "gridup-timescaledb", "gridup-mosquitto")
SIM_PREFIX = "SIM-"
RATED_INPUT_A = "main_input"
_MEM = re.compile(r"^([\d.]+)\s*([A-Za-z]+)$")
_MEM_TO_MIB = {"B": 1 / 1048576, "KiB": 1 / 1024, "MiB": 1.0, "GiB": 1024.0, "kB": 1e3 / 1048576, "MB": 1e6 / 1048576, "GB": 1e9 / 1048576}


# ================================================================== saf parcalar
class PayloadFactory:
    """Pano ve sira numarasina gore deterministik sablon telemetri (ayni tohum -> ayni filo)."""

    def __init__(self, contracts: Contracts, *, points: int, seed: int) -> None:
        names = load_map(ROOT / "contracts" / "modbus-map.yaml").points
        if not 4 <= points <= len(names):
            raise ValueError(f"nokta sayisi 4-{len(names)} olmali: {points}")
        self._points = names[:points]
        self._seed = seed
        self._rated = contracts.thresholds["rated_current_a"][RATED_INPUT_A]
        self._k_alarm = contracts.thresholds["k_ratio_alarm"]

    def payload(self, pano_id: str, seq: int, ts: datetime, *, alarm: bool = False) -> dict[str, Any]:
        panel = random.Random(f"{self._seed}:{pano_id}")
        rng = random.Random(f"{self._seed}:{pano_id}:{seq}")
        seconds = ts.hour * 3600 + ts.minute * 60 + ts.second
        daily = 0.5 + 0.5 * math.sin(2 * math.pi * seconds / 86400.0)
        load = (0.35 + 0.35 * panel.random()) * (0.7 + 0.3 * daily)
        i_base = self._rated * load
        t_amb = 22.0 + 6.0 * daily + rng.gauss(0.0, 0.3)
        k0 = 6.0e-6 * (0.8 + 0.4 * panel.random())

        points = []
        for index, pt in enumerate(self._points):
            neutral = pt.endswith("_N")
            current = i_base * (0.12 if neutral else 1.0 + 0.02 * (index % 3))
            dt_c = max(0.1, k0 * current**2 + rng.gauss(0.0, 0.4))
            k_ratio = 1.0 + rng.gauss(0.0, 0.01)
            if alarm and pt == "GIRIS_L2":
                k_ratio = self._k_alarm + 0.1
            points.append(
                {
                    "pt": pt,
                    "t_c": round(t_amb + dt_c, 2),
                    "dt_c": round(dt_c, 2),
                    "k": round(k0, 9),
                    "k_ratio": round(k_ratio, 3),
                    "tau_s": 900.0,
                    "ttl_h": 120.0 if alarm and pt == "GIRIS_L2" else None,
                    "excited": True,
                    "q": 0,
                }
            )
        i_ph = [round(i_base * (1.0 + rng.gauss(0.0, 0.02)), 1) for _ in range(3)]
        mean = sum(i_ph) / 3.0
        return {
            "v": 1,
            "ts": ts.isoformat(),
            "pano_id": pano_id,
            "seq": seq,
            "fw": "0.3.1",
            "t_conn": points,
            "elec": {
                "i_ph": i_ph,
                "i_n": round(0.1 * mean, 1),
                "u_ph": [round(230.0 + rng.gauss(0.0, 1.0), 1) for _ in range(3)],
                "thd_i": [round(4.0 + rng.gauss(0.0, 0.3), 2) for _ in range(3)],
                "cosphi": round(0.95 + rng.gauss(0.0, 0.005), 3),
                "unbal_pct": round(max(abs(i - mean) for i in i_ph) / mean * 100.0, 2),
            },
            "env": {
                "t_low_c": round(t_amb, 2),
                "rh_low_pct": 55.0,
                "td_low_c": round(t_amb - 9.0, 2),
                "td_margin_k": 9.0,
                "t_up_c": round(t_amb + 5.0, 2),
                "rh_up_pct": 48.0,
                "dt_air_k": 5.0,
                "voc_idx": None,
                "door_open": False,
            },
            "tvoc": {
                "state": 1, "trips": 0, "det_bits_low": 0, "det_bits_high": 0, "sensor_x2": 2, "sensor_x3": 2,
                "amb_light_x2": 10, "amb_light_x3": 10, "prot_health_ok": True, "comm_ok": True,
            },
            "pd": None,
            "risk": {
                "score": 70 if alarm else 5,
                "mode": "HYP-LOOSE-CONN" if alarm else "HYP-NORMAL",
                "ttl_h": 120.0 if alarm else None,
                "contributions": {"ALM-K-ALM": 1.0} if alarm else {},
            },
            "alarms": ["ALM-K-ALM"] if alarm else [],
            "health": {
                "uptime_s": 86400 + seq * 10,
                "nodes_ok": len(points) + 2,
                "nodes_total": len(points) + 2,
                "rssi_dbm": round(-70.0 + rng.gauss(0.0, 3.0), 1),
                "vbak_pct": 100.0,
                "buffered": 0,
                "maint_mode": False,
                "baseline_day": 7,
            },
        }


def phase_offsets(count: int, *, period_s: float, seed: int) -> list[float]:
    """Panolarin periyot icindeki yayin anlari: saha cihazlari ayni saniyede uyanmaz."""
    rng = random.Random(seed)
    return [rng.random() * period_s for _ in range(count)]


def parse_docker_stats(line: str) -> tuple[str, float, float]:
    """`docker stats --format '{{json .}}'` satiri -> (konteyner, CPU %, bellek MiB)."""
    data = json.loads(line)
    used = data["MemUsage"].split("/")[0].strip()
    match = _MEM.fullmatch(used)
    if match is None:
        raise ValueError(f"bellek ayristirilamadi: {data['MemUsage']!r}")
    return data["Name"], float(data["CPUPerc"].rstrip("%")), round(float(match[1]) * _MEM_TO_MIB[match[2]], 1)


def summarize(values: Sequence[float]) -> dict[str, float]:
    """n, p50, p95 (en yakin sira yontemi), max."""
    if not values:
        return {"n": 0}
    ordered = sorted(values)

    def rank(percentile: float) -> float:
        return round(ordered[max(1, math.ceil(percentile / 100.0 * len(ordered))) - 1], 1)

    return {"n": len(ordered), "p50": rank(50), "p95": rank(95), "max": round(ordered[-1], 1)}


def storage_projection(*, bytes_per_row: float, rows_per_message: float, period_s: float, panels: int) -> dict[str, float]:
    messages = round(panels * 86400 / period_s)
    rows = round(messages * rows_per_message)
    return {"messages_per_day": messages, "rows_per_day": rows, "gb_per_day": rows * bytes_per_row / 1e9}


# ================================================================== canli calistirma
@dataclass
class Config:
    panels: int = 1000
    period_s: float = 10.0
    duration_s: float = 300.0
    points: int = 7
    connections: int = 20
    alarm_panels: int = 5
    probe_panels: int = 50
    mqtt: str = "localhost:1883"
    db: str = "postgresql://postgres:gridup@localhost:5432/gridup"
    api: str = "http://localhost:8000"
    out_dir: str = str(ROOT / "loadtest" / "results")
    seed: int = 20260913
    keep: bool = False
    run_id: str = field(default_factory=lambda: "")


class Recorder:
    """Olcum orneklerini bellekte toplar ve loadtest_metrics tablosuna yazar."""

    def __init__(self, dsn: str, run_id: str) -> None:
        import psycopg

        self._conn = psycopg.connect(dsn, autocommit=True)
        self._conn.execute((ROOT / "deploy" / "initdb" / "004_loadtest.sql").read_text(encoding="utf-8"))
        self._run_id = run_id
        self._lock = threading.Lock()
        self.samples: dict[str, list[float]] = {}

    def record(self, metrics: dict[str, float], at: datetime | None = None) -> None:
        at = at or datetime.now(timezone.utc)
        with self._lock:
            for name, value in metrics.items():
                self.samples.setdefault(name, []).append(value)
            with self._conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO loadtest_metrics (ts, run_id, metric, value) VALUES (%s, %s, %s, %s)",
                    [(at, self._run_id, name, value) for name, value in metrics.items()],
                )

    def query(self, sql: str, params: Any = None) -> list[tuple]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def close(self) -> None:
        self._conn.close()


def _get_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


def clock_offset_s(recorder: Recorder) -> float:
    """Veritabani (Docker VM) saati - bu makinenin saati; en kisa gidis-donuslu olcum. WSL2 saati kayabilir."""
    best: tuple[float, float] | None = None
    for _ in range(5):
        before = time.time()
        [(db_now,)] = recorder.query("SELECT extract(epoch FROM clock_timestamp())")
        after = time.time()
        rtt = after - before
        if best is None or rtt < best[0]:
            best = (rtt, float(db_now) - (before + after) / 2.0)
    return best[1]


def telemetry_bytes(recorder: Recorder) -> int:
    [(size,)] = recorder.query("SELECT hypertable_size('telemetry')")
    return int(size)


def sim_counts(recorder: Recorder) -> tuple[int, int]:
    """SIM panolarinin (satir, mesaj) sayisi; mesaj = ayri (pano_id, ts). Canli simulatorun mesajlari karismaz."""
    [(rows, messages)] = recorder.query(
        "SELECT count(*), count(DISTINCT (pano_id, ts)) FROM telemetry WHERE pano_id LIKE %s", (f"{SIM_PREFIX}%",)
    )
    return int(rows), int(messages)


def sample_resources(recorder: Recorder, stop: threading.Event, api: str, interval_s: float = 5.0) -> None:
    last_written, last_at = None, None
    while not stop.is_set():
        metrics: dict[str, float] = {}
        try:
            output = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{json .}}", *CONTAINERS],
                capture_output=True, text=True, timeout=30, check=True,
            ).stdout
            for line in filter(None, output.splitlines()):
                name, cpu, mem = parse_docker_stats(line)
                short = name.removeprefix("gridup-")
                metrics[f"{short}_cpu_pct"] = cpu
                metrics[f"{short}_mem_mib"] = mem
        except (subprocess.SubprocessError, OSError, ValueError) as exc:
            print(f"  ! docker stats okunamadi: {exc}", file=sys.stderr)
        try:
            ingest = _get_json(f"{api}/health")["ingest"]
            now = time.monotonic()
            if last_written is not None:
                metrics["ingest_written_per_s"] = (ingest["written"] - last_written) / (now - last_at)
            last_written, last_at = ingest["written"], now
            metrics["telemetry_mb"] = telemetry_bytes(recorder) / 1e6
        except Exception as exc:  # olcum dongusu testi durdurmaz
            print(f"  ! saglik/DB olcumu basarisiz: {exc}", file=sys.stderr)
        if metrics:
            recorder.record(metrics)
        stop.wait(interval_s)


def probe_latency(recorder: Recorder, stop: threading.Event, probes: list[str], sent_at: dict, offset_s: float,
                  receive_ms: list[float], visible_ms: list[float], interval_s: float = 0.25) -> None:
    """Ornek panolarin son durumunu yoklar: yeni seq ilk goruldugunde gorunme ve alim gecikmesi."""
    seen: set[tuple[str, int]] = set()
    window_receive: list[float] = []
    last_flush = time.monotonic()
    while not stop.is_set():
        observed = time.time()
        for pano_id, seq, last_rx in recorder.query(
            "SELECT pano_id, seq, extract(epoch FROM last_rx) FROM panel_latest WHERE pano_id = ANY(%s)", (probes,)
        ):
            key = (pano_id, int(seq))
            published = sent_at.get(key)
            if published is None or key in seen:
                continue
            seen.add(key)
            visible_ms.append((observed - published) * 1000.0)
            receive = (float(last_rx) - offset_s - published) * 1000.0
            receive_ms.append(receive)
            window_receive.append(receive)
        if time.monotonic() - last_flush >= 10.0 and window_receive:
            recorder.record({"receive_p95_ms": summarize(window_receive)["p95"]})
            window_receive, last_flush = [], time.monotonic()
        stop.wait(interval_s)


def publish_fleet(config: Config, factory: PayloadFactory, recorder: Recorder, sent_at: dict, probes: set[str]) -> dict[str, Any]:
    import paho.mqtt.client as mqtt

    host, port = config.mqtt.rsplit(":", 1)
    clients = []
    for n in range(config.connections):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"gridup-loadtest-{config.run_id}-{n}")
        client.max_inflight_messages_set(1000)
        client.connect(host, int(port), keepalive=60)
        client.loop_start()
        clients.append(client)

    pano_ids = [f"{SIM_PREFIX}{n:05d}" for n in range(1, config.panels + 1)]
    offsets = phase_offsets(config.panels, period_s=config.period_s, seed=config.seed)
    alarm_ids = set(pano_ids[: config.alarm_panels])
    alarm_after = config.duration_s / 2.0
    start = time.monotonic()
    queue = [(offsets[i], i) for i in range(config.panels)]
    heapq.heapify(queue)
    seqs = [0] * config.panels
    alarmed: set[str] = set()
    sent = errors = 0
    window_sent, window_start = 0, start
    while queue:
        due, index = queue[0]
        if due > config.duration_s:
            break
        delay = start + due - time.monotonic()
        if delay > 0:
            time.sleep(min(delay, 0.05))
            continue
        heapq.heappop(queue)
        pano_id = pano_ids[index]
        alarm = pano_id in alarm_ids and pano_id not in alarmed and due >= alarm_after
        now = datetime.now(timezone.utc)
        body = json.dumps(factory.payload(pano_id, seqs[index], now, alarm=alarm), separators=(",", ":"))
        info = clients[index % len(clients)].publish(f"gridup/pano/{pano_id}/tel", body, qos=1)
        if info.rc == 0:
            sent += 1
            window_sent += 1
            if pano_id in probes:
                sent_at[(pano_id, seqs[index])] = now.timestamp()
            if alarm:
                alarmed.add(pano_id)
        else:
            errors += 1
        seqs[index] += 1
        heapq.heappush(queue, (due + config.period_s, index))
        if time.monotonic() - window_start >= 5.0:
            recorder.record({"publish_per_s": window_sent / (time.monotonic() - window_start)})
            window_sent, window_start = 0, time.monotonic()
    elapsed = time.monotonic() - start
    for client in clients:
        client.loop_stop()
        client.disconnect()
    return {"sent": sent, "errors": errors, "elapsed_s": round(elapsed, 1), "rate_msgs_per_s": round(sent / elapsed, 1),
            "alarm_panels": sorted(alarmed)}


def wait_for_drain(api: str, timeout_s: float = 60.0) -> None:
    """Ingest kuyrugu bosalana dek: yazilan mesaj sayisi 3 ardisik olcumde degismezse."""
    stable, last = 0, None
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline and stable < 3:
        written = _get_json(f"{api}/health")["ingest"]["written"]
        stable = stable + 1 if written == last else 0
        last = written
        time.sleep(1.0)


def alarm_latencies(recorder: Recorder, alarm_panels: list[str], offset_s: float) -> dict[str, Any]:
    if not alarm_panels:
        return {"injected": 0}
    raised = recorder.query(
        "SELECT id, extract(epoch FROM raised_at), extract(epoch FROM annunciated_at) FROM alarms "
        "WHERE pano_id = ANY(%s) AND code = 'ALM-K-ALM'",
        (alarm_panels,),
    )
    sms = recorder.query(
        "SELECT a.id, extract(epoch FROM a.raised_at), extract(epoch FROM min(n.sent_at)) FROM alarms a "
        "JOIN notifications n ON n.alarm_id = a.id AND n.ok AND n.channel = 'sms' "
        "WHERE a.pano_id = ANY(%s) AND a.code = 'ALM-K-ALM' GROUP BY a.id, a.raised_at",
        (alarm_panels,),
    )
    return {
        "injected": len(alarm_panels),
        "raised": len(raised),
        "raise_latency_ms": summarize([(float(ann) - offset_s - float(ts)) * 1000.0 for _, ts, ann in raised]),
        "sms_deliveries": len(sms),
        "sms_latency_ms": summarize([(float(sent) - offset_s - float(ts)) * 1000.0 for _, ts, sent in sms]),
    }


def resource_summary(samples: dict[str, list[float]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for container in CONTAINERS:
        short = container.removeprefix("gridup-")
        cpu, mem = samples.get(f"{short}_cpu_pct", []), samples.get(f"{short}_mem_mib", [])
        if cpu:
            summary[short] = {
                "cpu_pct_avg": round(sum(cpu) / len(cpu), 1), "cpu_pct_max": round(max(cpu), 1),
                "mem_mib_avg": round(sum(mem) / len(mem), 1), "mem_mib_max": round(max(mem), 1), "samples": len(cpu),
            }
    return summary


def cleanup(dsn: str, restart_backend: bool = True) -> None:
    import psycopg

    like = f"{SIM_PREFIX}%"
    with psycopg.connect(dsn, autocommit=True) as conn:
        mine = "SELECT id FROM alarms WHERE pano_id LIKE %s"
        for sql in (
            f"DELETE FROM alarm_journal WHERE alarm_id IN ({mine})",
            f"DELETE FROM notifications WHERE alarm_id IN ({mine})",
            "DELETE FROM alarms WHERE pano_id LIKE %s",
            "DELETE FROM events WHERE pano_id LIKE %s",
            "DELETE FROM telemetry WHERE pano_id LIKE %s",
            "DELETE FROM panel_latest WHERE pano_id LIKE %s",
            "DELETE FROM panels WHERE pano_id LIKE %s",
        ):
            conn.execute(sql, (like,))
        conn.execute("DELETE FROM quarantine WHERE topic LIKE %s", (f"gridup/pano/{SIM_PREFIX}%",))
    print("SIM-* verisi silindi")
    if restart_backend:
        subprocess.run(["docker", "restart", "gridup-backend"], check=True, capture_output=True, timeout=120)
        print("backend yeniden baslatildi (bellekteki SIM alarmlari ve haberlesme denetimi temizlendi)")


def run(config: Config) -> dict[str, Any]:
    contracts = load_contracts(ROOT / "contracts")
    factory = PayloadFactory(contracts, points=config.points, seed=config.seed)
    config.run_id = config.run_id or f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{config.panels}p"
    recorder = Recorder(config.db, config.run_id)
    offset = clock_offset_s(recorder)
    bytes_before, (rows_before, messages_before) = telemetry_bytes(recorder), sim_counts(recorder)
    health_before = _get_json(f"{config.api}/health")["ingest"]
    probes = [f"{SIM_PREFIX}{n:05d}" for n in range(1, config.panels + 1)][:: max(1, config.panels // config.probe_panels)]
    probes = probes[: config.probe_panels]
    sent_at: dict[tuple[str, int], float] = {}
    receive_ms: list[float] = []
    visible_ms: list[float] = []
    stop = threading.Event()
    threads = [
        threading.Thread(target=sample_resources, args=(recorder, stop, config.api), daemon=True),
        threading.Thread(target=probe_latency, args=(recorder, stop, probes, sent_at, offset, receive_ms, visible_ms), daemon=True),
    ]
    for thread in threads:
        thread.start()
    print(f"{config.run_id}: {config.panels} pano, {config.period_s:.0f} s periyot, {config.points} nokta, {config.duration_s:.0f} s")
    try:
        publish = publish_fleet(config, factory, recorder, sent_at, set(probes))
        wait_for_drain(config.api)
        time.sleep(3.0)  # yoklayici son mesajlari gorsun
    finally:
        stop.set()
        for thread in threads:
            thread.join(15)
    health_after = _get_json(f"{config.api}/health")["ingest"]
    rows_after, messages_after = sim_counts(recorder)
    rows, messages = rows_after - rows_before, messages_after - messages_before
    growth = telemetry_bytes(recorder) - bytes_before
    written = health_after["written"] - health_before["written"]  # canli simulatorun 3 panosu dahil
    rows_per_message = rows / messages if messages else 0.0
    bytes_per_row = growth / rows if rows else 0.0
    result = {
        "run_id": config.run_id,
        "config": {k: v for k, v in asdict(config).items() if k != "db"},
        "clock_offset_ms": round(offset * 1000.0, 1),
        "publish": publish,
        "ingest": {
            "written": written,
            "rejected": health_after["rejected"] - health_before["rejected"],
            "dropped": health_after["dropped"] - health_before["dropped"],
            "write_errors": health_after["write_errors"] - health_before["write_errors"],
            "receive_latency_ms": summarize(receive_ms),
            "visible_latency_ms": summarize(visible_ms),
            "written_per_s": summarize(recorder.samples.get("ingest_written_per_s", [])),
        },
        "resources": resource_summary(recorder.samples),
        "storage": {
            "telemetry_rows": rows,
            "sim_messages_stored": messages,
            "rows_per_message": round(rows_per_message, 1),
            "growth_mb": round(growth / 1e6, 1),
            "bytes_per_row_uncompressed": round(bytes_per_row, 1),
            "projection_100_panels": storage_projection(bytes_per_row=bytes_per_row, rows_per_message=rows_per_message, period_s=config.period_s, panels=100),
            "projection_1000_panels": storage_projection(bytes_per_row=bytes_per_row, rows_per_message=rows_per_message, period_s=config.period_s, panels=1000),
        },
        "alarms": alarm_latencies(recorder, publish["alarm_panels"], offset),
    }
    recorder.close()
    out = Path(config.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{config.run_id}.json").write_bytes(json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not config.keep:
        cleanup(config.db)
    return result


def main(argv: list[str] | None = None) -> int:
    defaults = Config()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--panels", type=int, default=defaults.panels)
    parser.add_argument("--period", type=float, default=defaults.period_s, help="pano basina yayin periyodu (s)")
    parser.add_argument("--duration", type=float, default=defaults.duration_s, help="yayin suresi (s)")
    parser.add_argument("--points", type=int, default=defaults.points, help="pano basina baglanti noktasi (4-25)")
    parser.add_argument("--connections", type=int, default=defaults.connections, help="MQTT baglanti sayisi")
    parser.add_argument("--alarm-panels", type=int, default=defaults.alarm_panels, help="yarida P2 alarm uretecek pano")
    parser.add_argument("--probe-panels", type=int, default=defaults.probe_panels)
    parser.add_argument("--mqtt", default=defaults.mqtt)
    parser.add_argument("--db", default=defaults.db)
    parser.add_argument("--api", default=defaults.api)
    parser.add_argument("--out", default=defaults.out_dir)
    parser.add_argument("--keep", action="store_true", help="SIM-* verisini silme")
    parser.add_argument("--cleanup-only", action="store_true", help="yalnizca SIM-* verisini sil, backend'i yeniden baslat")
    args = parser.parse_args(argv)
    if args.cleanup_only:
        cleanup(args.db)
        return 0
    run(Config(
        panels=args.panels, period_s=args.period, duration_s=args.duration, points=args.points,
        connections=args.connections, alarm_panels=args.alarm_panels, probe_panels=args.probe_panels,
        mqtt=args.mqtt, db=args.db, api=args.api, out_dir=args.out, keep=args.keep,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
