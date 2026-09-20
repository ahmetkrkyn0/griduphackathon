#!/usr/bin/env python3
"""Sanal pano filosu yuk testi (TB3 Adim 4, Kisi B).

Olculenler: yayin hizi (mesaj/s), alim gecikmesi (yayin -> backend'in mesaji aldigi an), gorunme gecikmesi
(yayin -> son durumun veritabaninda okunabildigi an), backend / TimescaleDB / Mosquitto CPU ve RAM,
telemetri tablosunun buyumesi ve gun basina projeksiyonu, alarm acilma ve alarm -> SMS gecikmesi.
Sonuc: loadtest/results/<run_id>.json (git disi) + loadtest_metrics tablosu (Grafana "Olcek" panosu).

YUK KAYNAGI (TB3 Adim 4) — iki uretec, varsayilan FIZIK:

  --generator physics   A'nin fizik uretecini KUTUPHANE OLARAK import eder
                        (panoalgo.generator.PanelSimulator; kod kopyalanmaz).
                        Yuk profili, isil model ve AR(1) gurultu gercektir.
  --generator template  Sozlesmeye uyan ama fiziksel model olmayan sablon yuk.
                        Cok buyuk kosularda (>= 5.000 pano) uretecin kendisi
                        darbogaz olmasin diye korunur; bkz. asagidaki olcum.

Her iki halde de olculen sey PLATFORMDUR (broker -> ingest -> DB -> alarm -> bildirim);
tespit basarisi burada OLCULMEZ (o docs/12, Kisi A).

OLCULEN URETEC MALIYETI (tek cekirdek, bu makine):
    PanelSimulator.step()         ~3.900 mesaj/s   (filo buyuklugunden bagimsiz)
    limits.evaluate()             ~9.800 cagri/s
    (karsilastirma) EdgePipeline    ~540 mesaj/s   100 panoda, ~130 mesaj/s 1.000 panoda
1.000 pano 10 s periyotla 100 mesaj/s ister; uretec bunun ~%3'unu kullanir, yani olculen
platformla CPU icin yarismaz. Tam kenar boru hatti (RLS + K/K0) bilerek KULLANILMAZ:
7 gunluk taban ogrenmesi gerektirir, 300 saniyelik bir kosuda anlamli sonuc vermez ve
1.000 panoda darbogaza donusurdu.

Calistirma (yigin ayaktayken, repo kokunden):
    backend/.venv/Scripts/python loadtest/fleet.py --panels 1000 --duration 300
    backend/.venv/Scripts/python loadtest/fleet.py --panels 10000 --generator template
    backend/.venv/Scripts/python loadtest/fleet.py --cleanup-only

Test bitince SIM-* verisi silinir ve backend yeniden baslatilir (--keep ile kalir): bellekteki alarm yoneticisi
1.000 sessiz pano icin 5 dk sonra ALM-COMMS-LOST uretmesin.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import os
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
# A'nin paketi KURULU DEGILSE de calissin: kod kopyalanmaz, yola eklenir (PLAN.md TB3 Adim 4).
sys.path.insert(0, str(ROOT / "libs" / "panoalgo"))

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

    ALARM_CODE = "ALM-K-ALM"   # enjeksiyonun urettigi kod (bkz. alarm_latencies)

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


class PhysicsPayloadFactory:
    """A'nin fizik uretecini kutuphane olarak kullanir (PLAN.md TB3 Adim 4).

    PayloadFactory ile AYNI arayuz: payload(pano_id, seq, ts, alarm=...).
    Kod KOPYALANMAZ; panoalgo.generator ve panoalgo.limits import edilir.

    SIMULE ADIM 15 DAKIKADIR, duvar saati periyodu degil. Yuk testi panolari 10 s'de
    bir yayinlar; her yayinda fizik 15 simule dakika ilerler. Sebep: 300 saniyelik bir
    kosuda 10 s'lik fizik adimlariyla hicbir sey degismez (isil zaman sabiti dakikalar
    mertebesinde), yuk profili duz cizgi olur ve olculen sey gercek bir gunun degiskenligini
    hic gormez. Yayinlanan `ts` yine duvar saatidir (asagida uzerine yazilir) — sim/panosim.py
    --wall-clock ile ayni karar (docs/14 §7).

    TESPIT TABAN OGRENMESI OLMADAN: `alarms` alanini panoalgo.limits.evaluate() doldurur.
    Bu, merkez dedektorun (panoalgo.central) kullandigi kodun ta kendisidir ve yalnizca
    SABIT sozlesme esiklerine bakar — K/K0 gibi 7 gunluk taban ogrenmesi gerektiren
    katmanlara DEGIL. 300 saniyelik bir yuk testi o 7 gunu bekleyemez; k_ratio bu yuzden
    1,0 kalir ve bu DURUSTTUR: yeni devreye alinmis bir filonun ilk haftasi boyle gorunur.
    Olculdu: limits.evaluate ~9.800 cagri/s, uretec ~3.900 mesaj/s — ikisi de darbogaz degil.

    ALARM ENJEKSIYONU FIZIKSELDIR: sablon uretec k_ratio alanini dogrudan esigin ustune
    YAZIYORDU. Burada noktanin isil direnc indeksi buyutulur, sicaklik isil modelle
    (tau*d(dT)/dt + dT = K*I^2) gercekten yukselir ve sabit 70 K siniri asilir; alarmi
    limits.evaluate bulur.

    Enjeksiyon HESAPLANIR, denenerek bulunmaz, ve iki adimdir:
      1) Panonun yuku ALARM_LOAD_FRACTION'da dondurulur. Sebep olculdu: gercek yuk
         profiliyle baglanti artisi gunun saatine gore 0,5 K ile 26 K arasinda degisiyor.
         Sabit bir carpan bazi saatlerde 70 K sinirini HIC gecirmiyor (saat 09: 37,8 K'da
         kaliyordu), carpani her mesajda ayarlayan bir dongu ise isil gecikme yuzunden
         asiri tepiyordu (saat 18: 2.629 K). Yuk dondurulunca I sabittir.
      2) Carpan dogrudan hesaplanir: M = hedef / (K0 * I^2). Sicaklik oraya isil zaman
         sabitiyle (tau) yumusakca yurur; asiri tepme yoktur, saatten bagimsizdir.

    DURUSTLUK NOTU: yuku dondurmak yalnizca enjekte edilen BES panoda gunluk profili
    kaldirir; filonun kalani gercek profille yayin yapar. Yuk testi tespit basarisini degil
    ALARM GECIKMESINI olcer ve bunun tekrarlanabilir olmasi gerekir. Tespit gercekligi
    iddiasi docs/12'dedir.
    """

    ALARM_CODE = "ALM-THR-TERM-ALM"   # enjeksiyonun urettigi kod (bkz. alarm_latencies)

    SIM_STEP_S = 900.0            # 15 simule dakika / yayin
    SETTLE_STEPS = 40             # kurulusta isil rejime oturma (~10 simule saat)
    MIN_ALARM_K_MULTIPLIER = 4.0  # rapor 15.2 tavani 3x; taban olarak biraz ustu
    ALARM_LIMIT_MARGIN = 1.5      # kalici artis sinirin bu kati olacak sekilde hesaplanir
    MAX_K_MULTIPLIER = 500.0      # saglik siniri; normalde cok altinda kalir
    ALARM_LOAD_FRACTION = 0.75    # enjekte edilen panonun yuku burada dondurulur

    def __init__(
        self,
        contracts: Contracts,
        *,
        points: int,
        seed: int,
        period_s: float = 0.0,
        edge_ids: Sequence[str] = (),
    ) -> None:
        from panoalgo import limits as panoalgo_limits
        from panoalgo.generator import PanelSimulator

        names = load_map(ROOT / "contracts" / "modbus-map.yaml").points
        if not 4 <= points <= len(names):
            raise ValueError(f"nokta sayisi 4-{len(names)} olmali: {points}")
        self._point_count = points
        self._seed = seed
        self._alarm_point = names[1]           # GIRIS_L2 — kesilmis listede de var
        self._alarm_limit = float(contracts.thresholds["term_rise_alarm_k"])
        self._limits = panoalgo_limits
        self._contracts_dir = ROOT / "contracts"
        self._make_sim = PanelSimulator
        self._start = datetime.now(timezone.utc).replace(microsecond=0)
        self._sims: dict[str, Any] = {}
        self._previous: dict[str, dict[str, Any]] = {}
        self._detect_ids = set(edge_ids)       # bos = TUM panolarda tespit kosar
        # pano -> uygulanan K carpani; 0.0 = yuk donduruldu, carpan bir sonraki mesajda hesaplanir
        self._injected: dict[str, float] = {}

    def _sim(self, pano_id: str):
        """Pano ilk kez yayinlayinca kurulur ve isil rejime oturtulur (deterministik)."""
        sim = self._sims.get(pano_id)
        if sim is None:
            index = int(pano_id[-5:])
            sim = self._make_sim(
                pano_id=pano_id,
                seed=self._seed + index,
                profile=("konut", "ticari", "karma")[index % 3],
                start=self._start,
            )
            for _ in range(self.SETTLE_STEPS):
                sim.step(self.SIM_STEP_S)
            self._sims[pano_id] = sim
        return sim

    def _trim(self, payload: dict[str, Any]) -> dict[str, Any]:
        """--points ile istenen nokta sayisina indirir (az sensorlu pano)."""
        payload["t_conn"] = payload["t_conn"][: self._point_count]
        payload["health"]["nodes_ok"] = len(payload["t_conn"]) + 2
        payload["health"]["nodes_total"] = len(payload["t_conn"]) + 2
        return payload

    def _drive_loose_connection(self, sim, pano_id: str) -> None:
        """Dondurulmus yukte 70 K sinirini gecirecek K carpanini hesaplar (bkz. sinif notu)."""
        if self._injected.get(pano_id, 0.0) > 0.0:
            return  # carpan hesaplandi; ariza oldugu yerde kalir, geri donmez
        current = sim.point_current(self._alarm_point)
        if current <= 0.0:
            return  # akim henuz olculmedi; bir sonraki mesajda dondurulmus yuku yansitir
        target = self._alarm_limit * self.ALARM_LIMIT_MARGIN
        multiplier = target / (sim.point_k(self._alarm_point) * current * current)
        multiplier = min(max(multiplier, self.MIN_ALARM_K_MULTIPLIER), self.MAX_K_MULTIPLIER)
        sim.set_k_multiplier(self._alarm_point, multiplier)
        self._injected[pano_id] = multiplier

    def payload(self, pano_id: str, seq: int, ts: datetime, *, alarm: bool = False) -> dict[str, Any]:
        sim = self._sim(pano_id)
        if alarm and pano_id not in self._injected:
            # 1. adim: yuku dondur. Carpan BU MESAJDA hesaplanmaz — olculen akim henuz
            # dondurulmemis yuku yansitir ve hesap saatlerce sapar (olculdu: 5.495 K tepe).
            sim.freeze_load(self.ALARM_LOAD_FRACTION)
            self._injected[pano_id] = 0.0
        elif pano_id in self._injected:
            # 2. adim: akim artik dondurulmus yuku yansitiyor, carpan hesaplanabilir.
            self._drive_loose_connection(sim, pano_id)
        payload = self._trim(sim.step(self.SIM_STEP_S))
        if not self._detect_ids or pano_id in self._detect_ids:
            payload["alarms"] = self._limits.evaluate(
                payload, self._previous.get(pano_id), self._contracts_dir
            )
        self._previous[pano_id] = payload
        # Zaman damgasi ve sira numarasi yuk testinindir: gecikme olcumu bunlara dayanir.
        payload["ts"] = ts.isoformat()
        payload["seq"] = seq
        return payload


def phase_offsets(count: int, *, period_s: float, seed: int) -> list[float]:
    """Panolarin periyot icindeki yayin anlari: saha cihazlari ayni saniyede uyanmaz."""
    rng = random.Random(seed)
    return [rng.random() * period_s for _ in range(count)]


def kosum_makinesi() -> dict:
    """Kosumun KOSTUGU DONANIMI esere yazar.

    NEDEN (20 Eylul): eser CPU/bellek KULLANIMINI kaydediyordu ama KAPASITESINI
    kaydetmiyordu. Duzenek yalnizca docs/09 #3'te, elle, tek sefer yazilmisti.
    Sonuc: 20 Eylul'de ayni tablo farkli bir makinede (28 -> 8 is parcacigi)
    kosuldu ve aradaki fark once "performans gerilemesi" diye okundu. Iki kosumu
    sessizce farkli donanimda karsilastirmak bir daha mumkun olmasin diye bu blok
    eklendi. Hicbir alan tahmin degildir; okunamayan alan None birakilir.
    """
    import platform
    import shutil
    import subprocess

    bilgi: dict = {
        "islemci": platform.processor() or None,
        "isletim_sistemi": f"{platform.system()} {platform.release()}",
        "mantiksal_cpu": os.cpu_count(),
        "fiziksel_cekirdek": None,
        "ram_gb": None,
        "docker_cpu": None,
        "docker_bellek_gb": None,
        "docker_surum": None,
    }
    try:  # psutil zorunlu degil: yoksa alan None kalir, betik durmaz
        import psutil

        bilgi["fiziksel_cekirdek"] = psutil.cpu_count(logical=False)
        bilgi["ram_gb"] = round(psutil.virtual_memory().total / 1024**3, 1)
    except Exception:
        pass
    if shutil.which("docker"):
        try:
            cikti = subprocess.run(
                ["docker", "info", "--format", "{{.NCPU}}\t{{.MemTotal}}\t{{.ServerVersion}}"],
                capture_output=True, text=True, timeout=20, check=True,
            ).stdout.strip().split("\t")
            if len(cikti) == 3:
                bilgi["docker_cpu"] = int(cikti[0])
                bilgi["docker_bellek_gb"] = round(int(cikti[1]) / 1024**3, 2)
                bilgi["docker_surum"] = cikti[2]
        except Exception:
            pass
    return bilgi


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
    generator: str = "physics"   # physics | template (bkz. modul docstring)
    edge_all: bool = False       # kenar boru hattini TUM panolarda kostur
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


def alarm_latencies(recorder: Recorder, alarm_panels: list[str], offset_s: float,
                    code: str = "ALM-K-ALM") -> dict[str, Any]:
    """`code`: enjeksiyonun URETTIGI alarm kodu; ureticiye gore degisir.

    Sablon uretec k_ratio'yu dogrudan esigin ustune yazar -> ALM-K-ALM.
    Fizik ureteci K'yi buyutur, sicaklik isil modelle 70 K'yi asar -> ALM-THR-TERM-ALM
    (K/K0 katmani 7 gunluk taban ogrenmesi ister, yuk testinde anlamsizdir).
    """
    if not alarm_panels:
        return {"injected": 0}
    raised = recorder.query(
        "SELECT id, extract(epoch FROM raised_at), extract(epoch FROM annunciated_at) FROM alarms "
        "WHERE pano_id = ANY(%s) AND code = %s",
        (alarm_panels, code),
    )
    sms = recorder.query(
        "SELECT a.id, extract(epoch FROM a.raised_at), extract(epoch FROM min(n.sent_at)) FROM alarms a "
        "JOIN notifications n ON n.alarm_id = a.id AND n.ok AND n.channel = 'sms' "
        "WHERE a.pano_id = ANY(%s) AND a.code = %s GROUP BY a.id, a.raised_at",
        (alarm_panels, code),
    )
    return {
        "injected": len(alarm_panels),
        "code": code,
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


def build_factory(config: Config, contracts: Contracts, detect_ids: Sequence[str]):
    """Yapilandirmaya gore uretici kurar (fizik = varsayilan, sablon = buyuk kosular)."""
    if config.generator == "template":
        return PayloadFactory(contracts, points=config.points, seed=config.seed)
    if config.generator != "physics":
        raise ValueError(f"--generator physics ya da template olmali: {config.generator!r}")
    return PhysicsPayloadFactory(
        contracts,
        points=config.points,
        seed=config.seed,
        period_s=config.period_s,
        edge_ids=detect_ids,
    )


def run(config: Config) -> dict[str, Any]:
    contracts = load_contracts(ROOT / "contracts")
    config.run_id = config.run_id or f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{config.panels}p"
    recorder = Recorder(config.db, config.run_id)
    offset = clock_offset_s(recorder)
    bytes_before, (rows_before, messages_before) = telemetry_bytes(recorder), sim_counts(recorder)
    health_before = _get_json(f"{config.api}/health")["ingest"]
    pano_ids_all = [f"{SIM_PREFIX}{n:05d}" for n in range(1, config.panels + 1)]
    probes = pano_ids_all[:: max(1, config.panels // config.probe_panels)]
    probes = probes[: config.probe_panels]
    # Tespit (limits.evaluate) varsayilan olarak TUM panolarda kosar — ucuz olculdu.
    # --edge-all=False ise yalnizca olcum yapilan panolar: alarm panolari + yoklayicilar.
    detect_ids = [] if config.edge_all else sorted(set(pano_ids_all[: config.alarm_panels]) | set(probes))
    factory = build_factory(config, contracts, detect_ids)
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
    print(
        f"{config.run_id}: {config.panels} pano, {config.period_s:.0f} s periyot, {config.points} nokta, "
        f"{config.duration_s:.0f} s, uretec={config.generator}"
        + (f", tespit {len(detect_ids) or config.panels} panoda" if config.generator == "physics" else "")
    )
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
        "detect_panels": (len(detect_ids) or config.panels) if config.generator == "physics" else 0,
        "clock_offset_ms": round(offset * 1000.0, 1),
        "makine": kosum_makinesi(),
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
        "alarms": alarm_latencies(recorder, publish["alarm_panels"], offset, factory.ALARM_CODE),
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
    parser.add_argument("--generator", choices=("physics", "template"), default=defaults.generator,
                        help="physics = panoalgo fizik ureteci (varsayilan), template = sablon yuk")
    parser.add_argument("--edge-all", action="store_true",
                        help="tespiti TUM panolarda kostur (varsayilan: yalnizca olculen panolar)")
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
        generator=args.generator, edge_all=args.edge_all,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
