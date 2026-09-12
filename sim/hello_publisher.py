"""Faz 0 duman testi yayincisi (Kisi A).

Amaci tek sey: sozlesmenin gercekten isledigini ILK GUNDEN kanitlamak.
Her mesaj yayinlanmadan once contracts/mqtt-telemetry.schema.json ile dogrulanir;
sema ile kod arasinda bir fark varsa burada, Faz 0'da patlar — M1 kapisinda degil.

Faz 1'de (TA1) bu dosyanin yerini libs/panoalgo tabanli gercek fizik ureteci alir:
  - tau*dDT/dt + DT = K*I^2 isil modeli
  - saat-of-hafta yuk profili + AR(1) gurultu (verilen Excel'in lag-1 = 0,00'ina karsit)
  - etiketli ariza enjeksiyonu (S0-S9)
"""

from __future__ import annotations

import json
import math
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
from jsonschema import Draft202012Validator

CONTRACTS_DIR = Path(os.getenv("CONTRACTS_DIR", "/contracts"))
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
PANELS = int(os.getenv("SIM_PANELS", "3"))
PERIOD_S = float(os.getenv("SIM_PERIOD_S", "10"))
SPEED = float(os.getenv("SIM_SPEED", "60"))  # 60 = 1 saniye gercek zamanda 1 dakika

PANO_IDS = ["ADM-00001", "ADM-00002", "GDZ-00001"]
POINTS = ["GIRIS_L1", "GIRIS_L2", "GIRIS_L3", "GIRIS_N"]


def build_payload(pano_id: str, seq: int, sim_minutes: float) -> dict:
    """Sema-gecerli, fiziksel olarak MAKUL bir telemetri yuku uretir."""
    # Gunluk yuk profili (kaba): sabah ve aksam pikleri
    hour = (sim_minutes / 60.0) % 24.0
    load = 0.45 + 0.35 * math.sin((hour - 7.0) / 24.0 * 2 * math.pi) ** 2
    i_base = 400.0 * load

    t_amb_low = 24.0 + 6.0 * math.sin((hour - 15.0) / 24.0 * 2 * math.pi)
    rh_low = max(25.0, min(98.0, 70.0 - 1.8 * (t_amb_low - 24.0)))

    points = []
    for idx, pt in enumerate(POINTS):
        i_pt = i_base * (1.0 + 0.05 * idx) if pt != "GIRIS_N" else i_base * 0.12
        k0 = 1.6e-4
        dt_c = k0 * i_pt**2 + random.gauss(0, 0.2)
        points.append(
            {
                "pt": pt,
                "t_c": round(t_amb_low + dt_c, 2),
                "dt_c": round(dt_c, 2),
                "k": round(k0, 9),
                "k_ratio": 1.0,
                "tau_s": 900.0,
                "ttl_h": None,
                "excited": True,
                "q": 0,
            }
        )

    # Magnus (rapor 15.1) — ayni formul libs/panoalgo/physics.py icinde test edilecek
    gamma = math.log(rh_low / 100.0) + 17.62 * t_amb_low / (243.12 + t_amb_low)
    td_low = 243.12 * gamma / (17.62 - gamma)

    return {
        "v": 1,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pano_id": pano_id,
        "seq": seq,
        "fw": "0.0.1-faz0",
        "t_conn": points,
        "elec": {
            "i_ph": [round(i_base * f, 1) for f in (1.0, 1.05, 0.97)],
            "i_n": round(i_base * 0.12, 1),
            "u_ph": [round(231.0 + random.gauss(0, 1.2), 1) for _ in range(3)],
            "thd_i": [round(4.0 + random.gauss(0, 0.5), 1) for _ in range(3)],
            "cosphi": 0.96,
            "unbal_pct": 4.1,
        },
        "env": {
            "t_low_c": round(t_amb_low, 2),
            "rh_low_pct": round(rh_low, 1),
            "td_low_c": round(td_low, 2),
            "td_margin_k": round(t_amb_low - td_low, 2),
            "t_up_c": round(t_amb_low + 6.5, 2),
            "rh_up_pct": round(max(20.0, rh_low - 8.0), 1),
            "dt_air_k": 6.5,
            "voc_idx": None,
            "door_open": False,
        },
        "tvoc": {
            "state": 0,
            "trips": 0,
            "sensor_x2": 0xFFFF,
            "sensor_x3": 0xFFFF,
            "prot_health_ok": True,
            "comm_ok": True,
        },
        "pd": None,
        "risk": {"score": 3, "mode": "HYP-NORMAL", "ttl_h": None, "contributions": {}},
        "alarms": [],
        "health": {
            "uptime_s": seq * int(PERIOD_S),
            "nodes_ok": len(POINTS),
            "nodes_total": len(POINTS),
            "rssi_dbm": -71.0,
            "vbak_pct": 100.0,
            "buffered": 0,
            "maint_mode": False,
            "baseline_day": 7,
        },
    }


def main() -> None:
    schema = json.loads(
        (CONTRACTS_DIR / "mqtt-telemetry.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    print(f"[panosim] sema yuklendi: {schema['title']}", flush=True)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="panosim-faz0")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()
    print(f"[panosim] {MQTT_HOST}:{MQTT_PORT} baglandi, {PANELS} pano yayinlaniyor", flush=True)

    seq = 0
    sim_minutes = 0.0
    while True:
        seq += 1
        sim_minutes += PERIOD_S * SPEED / 60.0
        for pano_id in PANO_IDS[:PANELS]:
            payload = build_payload(pano_id, seq, sim_minutes)

            # SOZLESME KAPISI: gecersiz mesaj yayinlanmaz.
            errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
            if errors:
                for err in errors[:3]:
                    print(f"[panosim] SEMA HATASI {list(err.path)}: {err.message}", flush=True)
                raise SystemExit(1)

            client.publish(f"gridup/pano/{pano_id}/tel", json.dumps(payload), qos=1)

        if seq % 6 == 1:
            print(
                f"[panosim] seq={seq} sim_saat={sim_minutes / 60:.1f} "
                f"pano={PANELS} (sema gecerli)",
                flush=True,
            )
        time.sleep(PERIOD_S)


if __name__ == "__main__":
    main()
