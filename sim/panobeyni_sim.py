"""Pano Beyni tasima kabugu (TA3 Adim 6, Kisi A): Modbus master -> kenar -> MQTT.

NE YAPAR
--------
Sahadaki Pano Beyni'nin VERI YOLUNU birebir kurar:

    MPR-53CS  (Modbus TCP) --+
                             +--> olculen akimlar --> panoalgo kenar boru hatti --> MQTT
    TVOC-2    (Modbus TCP) --+        (isil model + RLS + esikler)

Yani elektriksel buyuklukler ve ark korumasi durumu UYDURULMAZ; iki cihaz
simulatorunden GERCEK MODBUS PROTOKOLUYLE, kilavuzdaki register adreslerinden
okunur. Baglanti sicakliklari kablosuz dugumlerden gelir ve onlarin Modbus
karsiligi yoktur; olculen akimdan isil modelle (tau*d(dT)/dt + dT = K*I^2)
turetilir — MCU'daki C cekirdeginin yaptigi hesabin AYNISI (firmware/core/).

NEDEN VAR
---------
14 Eylul'e kadar depoda hicbir Modbus ISTEMCISI yoktu: `mpr-sim` ve `tvoc-sim`
tek baslarina duruyordu, kimse okumuyordu. Bu yuzden `tvoc2_sim.py --trip-after`
ile uretilen gercek bir ark tripi Modbus duzeyinde goruluyor ama MQTT'ye ve alarm
konsoluna HIC ULASMIYORDU. Bu dosya o boslugu kapatir: artik cihaz duzeyinde
uretilen bir olay uctan uca akar.

KAPSAM — NE YAPMAZ (durustluk notu, PLAN.md TA3 Adim 6 ile fark)
----------------------------------------------------------------
  * Sanal SERI PORT degil, Modbus TCP kullanilir. Cihaz simulatorleri TCP sunucu
    (sahada RS485; ag gecidi degisir, protokol cercevesi ayni kalir).
  * Modbus SLAVE sunumu burada yapilmaz. Ayni harita merkezde zaten sunuluyor
    (backend/app/scada/, :502) ve sozlesmesi contracts/modbus-map.yaml'dir.
  * Hesap C degil Python'dur. Ayni matematik oldugu OLCULMUSTUR: C ile Python
    RLS ciktilari ayni test vektorunde K 1,36e-8 / tau 1,42e-8 farkla eslesiyor
    (esik 1e-6, firmware/akis-diyagramlari/ana-dongu.md).

Bu ucu docs/17 DH2'de de acikca yazilidir.

HALKA TAMPON
------------
Broker erisilemezse mesajlar bellekte sinirli bir halkada bekler ve baglanti
gelince sirayla gonderilir (kenarin `buffered` alani bunu bildirir). Halka dolarsa
EN ESKI mesaj dusurulur ve sayilir — sessizce degil, ekrana yazilarak.

Kullanim:
    python panobeyni_sim.py --mpr localhost:5020 --tvoc localhost:5021 \\
           --pano ADM-00007 --mqtt localhost:1883
    python panobeyni_sim.py --dry-run --max-messages 3        # broker olmadan
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from types import FrameType

import paho.mqtt.client as mqtt
from jsonschema import Draft202012Validator
from pymodbus.client import ModbusTcpClient

from panoalgo.devices import (
    MPR_ADDR,
    MPR_CT_REGISTER,
    MPR_CURRENT_SCALE,
    MPR_THD_SCALE,
    TVOC2_STATE_ACTIVE_ERROR,
    TVOC2_SYSTEM_STATE_REG,
    TVOC2_TRIP_COUNT_REG,
)
from panoalgo.edge import EdgePipeline
from panoalgo.generator import PanelSimulator, default_contracts_dir

from panosim import Publisher, Stamper, load_schema

# Sahada kenar 1 s isler, merkeze 10 s ozet gonderir (docs/02). Modbus okuma da 1 s.
POLL_PERIOD_S = 1.0
REPORT_EVERY = 10
RING_CAPACITY = 5000          # ~14 saat, 10 s'lik ozetle; bellekte ~10 MB'in altinda
CONNECT_TIMEOUT_S = 5.0

_stop = False


def _request_stop(signum: int, frame: FrameType | None) -> None:
    global _stop
    _stop = True


# ------------------------------------------------------------------ Modbus master


class ModbusReadError(RuntimeError):
    """Cihaz cevap vermedi ya da istisna dondurdu."""


class DeviceReader:
    """Iki cihaz simulatorunden okuyan Modbus master dongusu."""

    def __init__(self, mpr: tuple[str, int] | None, tvoc: tuple[str, int] | None,
                 mpr_unit: int, tvoc_unit: int) -> None:
        self._mpr_target, self._tvoc_target = mpr, tvoc
        self._mpr_unit, self._tvoc_unit = mpr_unit, tvoc_unit
        self._mpr = ModbusTcpClient(mpr[0], port=mpr[1], timeout=CONNECT_TIMEOUT_S) if mpr else None
        self._tvoc = ModbusTcpClient(tvoc[0], port=tvoc[1], timeout=CONNECT_TIMEOUT_S) if tvoc else None
        self.ct_ratio = 0

    def connect(self) -> None:
        if self._mpr is not None:
            if not self._mpr.connect():
                raise ModbusReadError(f"MPR-53CS {self._mpr_target} baglanti kurulamadi")
            self.ct_ratio = self._read_words(self._mpr, self._mpr_unit, MPR_CT_REGISTER, 1)[0]
            print(f"[panobeyni] MPR-53CS baglandi, CT orani {self.ct_ratio} (register 0x8001)", flush=True)
        if self._tvoc is not None:
            # ID 248 sessizdir ve BU BEKLENEN bir durumdur: baglanti kurulur, okuma
            # zaman asimina duser. Cihazi "bozuk" ilan etmeyiz, comm_ok=False deriz.
            self._tvoc.connect()
            print(f"[panobeyni] TVOC-2 {self._tvoc_target} (birim {self._tvoc_unit})", flush=True)

    def close(self) -> None:
        for client in (self._mpr, self._tvoc):
            if client is not None:
                client.close()

    @staticmethod
    def _read_words(client: ModbusTcpClient, unit: int, address: int, count: int) -> list[int]:
        answer = client.read_holding_registers(address, count=count, slave=unit)
        if answer.isError():
            raise ModbusReadError(f"PDU {address} okunamadi: {answer}")
        return list(answer.registers)

    @staticmethod
    def _u32(words: list[int]) -> int:
        """Kilavuz: 32-bit olcum iki register, word_order high_first."""
        return (words[0] << 16) | words[1]

    def read_electrical(self) -> dict[str, object] | None:
        """MPR-53CS'ten faz/notr akimlari ve akim THD'si (gercek register adresleri)."""
        if self._mpr is None:
            return None
        scale = MPR_CURRENT_SCALE * self.ct_ratio
        currents = [
            self._u32(self._read_words(self._mpr, self._mpr_unit, MPR_ADDR[key], 2)) * scale
            for key in ("i_l1", "i_l2", "i_l3")
        ]
        neutral = self._u32(self._read_words(self._mpr, self._mpr_unit, MPR_ADDR["i_n"], 2)) * scale
        thd = [
            self._u32(self._read_words(self._mpr, self._mpr_unit, MPR_ADDR[key], 2)) * MPR_THD_SCALE
            for key in ("thd_i_l1", "thd_i_l2", "thd_i_l3")
        ]
        return {"i_ph": currents, "i_n": neutral, "thd_i": thd}

    def read_protection(self) -> dict[str, object]:
        """TVOC-2'den sistem durumu ve trip sayaci; cevap yoksa comm_ok=False."""
        if self._tvoc is None:
            return {"comm_ok": True, "state": 0, "trips": 0}
        try:
            state = self._read_words(self._tvoc, self._tvoc_unit, TVOC2_SYSTEM_STATE_REG, 1)[0]
            trips = self._read_words(self._tvoc, self._tvoc_unit, TVOC2_TRIP_COUNT_REG, 1)[0]
        except (ModbusReadError, OSError):
            # Fabrika ID 248: cihaz sessiz. Bu, "koruma arizali" DEGIL "haberlesme yok"tur;
            # ikisi farkli alarmlardir (limits.py: comm_ok=False -> ALM-PROT-HEALTH).
            return {"comm_ok": False, "state": 0, "trips": 0}
        return {"comm_ok": True, "state": state, "trips": trips}


# ------------------------------------------------------------------ halka tampon


class RingBuffer:
    """Broker yokken mesajlari bekletir; dolunca EN ESKIyi dusurur ve sayar."""

    def __init__(self, capacity: int = RING_CAPACITY) -> None:
        self._items: deque = deque(maxlen=capacity)
        self.dropped = 0

    def __len__(self) -> int:
        return len(self._items)

    @property
    def capacity(self) -> int:
        return self._items.maxlen

    def add(self, payload: dict) -> None:
        if len(self._items) == self._items.maxlen:
            self.dropped += 1
        self._items.append(payload)

    def drain(self, send) -> int:
        """Bekleyenleri sirayla gonderir; ilk basarisizlikta durur ve kalani tutar."""
        sent = 0
        while self._items:
            payload = self._items[0]
            if not send(payload):
                break
            self._items.popleft()
            sent += 1
        return sent


# ------------------------------------------------------------------ yuk kurulumu


def build_payload(sim: PanelSimulator, pipeline: EdgePipeline, reader: DeviceReader,
                  period_s: float) -> dict:
    """Olculen buyuklukleri isil modelle birlestirip sema-gecerli telemetri uretir.

    `sim` burada bir "senaryo" degil, MCU'daki durum makinesinin Python karsiligidir:
    baglanti sicakliklarini olculen akimdan turetir. Elektriksel alanlar ve ark
    korumasi durumu OLCULEN degerlerle EZILIR — uydurulmaz.
    """
    payload = sim.step(period_s)

    electrical = reader.read_electrical()
    if electrical is not None:
        payload["elec"]["i_ph"] = [round(v, 1) for v in electrical["i_ph"]]
        payload["elec"]["i_n"] = round(float(electrical["i_n"]), 1)
        payload["elec"]["thd_i"] = [round(v, 2) for v in electrical["thd_i"]]

    protection = reader.read_protection()
    tvoc = payload.get("tvoc")
    if tvoc is not None:
        tvoc["comm_ok"] = bool(protection["comm_ok"])
        if protection["comm_ok"]:
            state = int(protection["state"])
            tvoc["state"] = state
            tvoc["trips"] = int(protection["trips"])
            tvoc["prot_health_ok"] = not bool(state & TVOC2_STATE_ACTIVE_ERROR)
        else:
            tvoc["prot_health_ok"] = False

    return pipeline.process(payload)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pano Beyni tasima kabugu (Kisi A)")
    parser.add_argument("--mqtt", default=os.getenv("MQTT_HOST", "mosquitto") + ":" + os.getenv("MQTT_PORT", "1883"))
    parser.add_argument("--mpr", default=os.getenv("MPR_TARGET", "mpr-sim:5020"), help="HOST:PORT ya da 'yok'")
    parser.add_argument("--tvoc", default=os.getenv("TVOC_TARGET", "tvoc-sim:5021"), help="HOST:PORT ya da 'yok'")
    parser.add_argument("--mpr-unit", type=int, default=int(os.getenv("MPR_UNIT", "1")))
    parser.add_argument("--tvoc-unit", type=int, default=int(os.getenv("TVOC_UNIT", "248")))
    parser.add_argument("--pano", default=os.getenv("PANO_ID", "ADM-00007"))
    parser.add_argument("--seed", type=int, default=int(os.getenv("SIM_SEED", "7000")))
    parser.add_argument("--period", type=float, default=POLL_PERIOD_S, help="Modbus tarama periyodu (s)")
    parser.add_argument("--report-every", type=int, default=REPORT_EVERY, help="kac taramada bir MQTT ozeti")
    parser.add_argument("--ring", type=int, default=RING_CAPACITY, help="halka tampon kapasitesi")
    parser.add_argument("--max-messages", type=int, default=0, help="0 = sinirsiz (test icin)")
    parser.add_argument("--dry-run", action="store_true", help="broker'a baglanma, ekrana yaz")
    return parser.parse_args(argv)


def _target(value: str) -> tuple[str, int] | None:
    if value.strip().lower() in ("", "yok", "none", "off"):
        return None
    host, _, port = value.partition(":")
    if not host or not port.isdigit():
        raise SystemExit(f"HOST:PORT biciminde olmali: {value!r}")
    return host, int(port)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.period <= 0 or args.report_every < 1:
        raise SystemExit("--period pozitif, --report-every en az 1 olmali")

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    contracts_dir = default_contracts_dir()
    schema = load_schema(contracts_dir)
    reader = DeviceReader(_target(args.mpr), _target(args.tvoc), args.mpr_unit, args.tvoc_unit)
    reader.connect()

    sim = PanelSimulator(pano_id=args.pano, seed=args.seed, contracts_dir=contracts_dir)
    pipeline = EdgePipeline(profile="karma", contracts_dir=contracts_dir, period_s=args.period * args.report_every)
    ring = RingBuffer(args.ring)

    client = None
    if not args.dry_run:
        from panosim import connect as mqtt_connect

        host, port = _target(args.mqtt)
        client = mqtt_connect(host, port)
    publisher = Publisher(schema, client, Stamper(enabled=True), prefix="panobeyni")
    print(
        f"[panobeyni] {args.pano} | tarama {args.period} s | ozet her {args.report_every} taramada "
        f"| halka {ring.capacity}",
        flush=True,
    )

    scans = 0
    # OLAY MANDALI: kenar her taramada (1 s) isler ama merkeze her N taramada bir ozet
    # gonderir. ALM-ARC-TRIP gibi KENAR TETIKLEMELI kodlar tek bir ornekte dogrudur
    # (trip sayaci degistigi an); o ornek raporlanmayan bir taramaya denk gelirse olay
    # kaybolurdu. Rapor penceresi icinde gorulen kodlar mandallanir ve ozetle gonderilir.
    # Olculdu: mandal olmadan --trip-after ile uretilen gercek trip MQTT'ye hic ulasmiyordu.
    pending: set[str] = set()
    try:
        while not _stop:
            scans += 1
            try:
                payload = build_payload(sim, pipeline, reader, args.period)
            except (ModbusReadError, OSError) as exc:
                print(f"[panobeyni] Modbus okuma hatasi, tarama atlandi: {exc}", flush=True)
                time.sleep(args.period)
                continue

            pending.update(payload["alarms"])
            if scans % args.report_every == 0:
                payload["alarms"] = sorted(pending)
                pending.clear()
                payload["health"]["buffered"] = len(ring)
                ring.add(payload)
                sent = ring.drain(publisher.send)
                if sent == 0 and len(ring):
                    print(f"[panobeyni] broker yok, {len(ring)} mesaj bekliyor", flush=True)
                if payload["alarms"]:
                    print(f"[panobeyni] alarm: {', '.join(payload['alarms'])}", flush=True)
                if args.max_messages and publisher.published >= args.max_messages:
                    break
            time.sleep(args.period)
    finally:
        reader.close()
        if client is not None:
            client.loop_stop()
            client.disconnect()

    print(
        f"[panobeyni] durdu; {scans} tarama, {publisher.published} mesaj, "
        f"{len(ring)} bekleyen, {ring.dropped} dusen",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
