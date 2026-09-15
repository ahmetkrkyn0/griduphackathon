"""sim/ testleri icin ortak yardimcilar (Kisi A)."""

from __future__ import annotations

import os
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SIM_DIR.parent
CONTRACTS_DIR = REPO_ROOT / "contracts"


def free_port() -> int:
    """Isletim sisteminden bos bir port ister ve hemen birakir."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def sim_env() -> dict[str, str]:
    """Alt surecin panoalgo'yu ve sozlesmeleri bulabilmesi icin ortam."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "libs" / "panoalgo"), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    env["CONTRACTS_DIR"] = str(CONTRACTS_DIR)
    env["PYTHONUNBUFFERED"] = "1"
    return env


def run_sim(script: str, *args: str) -> subprocess.Popen:
    """sim/<script> dosyasini GERCEK CLI'siyla alt surec olarak baslatir."""
    return subprocess.Popen(
        [sys.executable, str(SIM_DIR / script), *args],
        cwd=str(SIM_DIR),
        env=sim_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def wait_for_port(port: int, timeout_s: float = 20.0, host: str = "127.0.0.1") -> None:
    """Port dinlemeye baslayana kadar bekler; acilmazsa testi dusurur."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.15)
    raise AssertionError(f"{host}:{port} {timeout_s} s icinde dinlemeye baslamadi")


def read_holding_raw(
    port: int, unit: int, address: int, count: int = 1, timeout_s: float = 3.0
) -> bytes | None:
    """Ham Modbus TCP FC03 istegi gonderir; cevabi doner, cevap yoksa None.

    pymodbus istemcisi kullanilmaz: "cevap yok" ile "istisna cevabi" arasindaki
    farki gormek istiyoruz, istemci ikisini de tek bir hataya cevirebilir.
    """
    frame = struct.pack(">HHHBBHH", 1, 0, 6, unit, 3, address, count)
    with socket.create_connection(("127.0.0.1", port), timeout=timeout_s) as sock:
        sock.settimeout(timeout_s)
        sock.sendall(frame)
        try:
            return sock.recv(256) or None
        except socket.timeout:
            return None
