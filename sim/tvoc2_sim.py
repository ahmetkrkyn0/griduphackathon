"""ABB TVOC-2 Modbus simulatoru (TA3 Adim 1, Kisi A).

Cihazin GERCEK register adreslerinde cevap verir; register mantigi
libs/panoalgo/panoalgo/devices.py icindedir ve orada testlerle kilitlenmistir.
Bu dosya yalnizca pymodbus sunucusudur.

DEMODA GOSTERILECEK DETAY — fabrika ayari ID 248:
    Kilavuz (bolum 1.3): "Modbus ID 248 is not a valid id for a Modbus system but is
    used to indicate that the communication is DISABLED."
    Yani kutudan cikan TVOC-2 hicbir isteme cevap VERMEZ — istisna bile dondurmez.
    Sahada en sik yasanan devreye alma hatasi budur; "cihaz bozuk" sanilir.

    python tvoc2_sim.py --slave-id 248     -> QModMaster timeout alir
    python tvoc2_sim.py --slave-id 10      -> ayni istek cevap doner

YAZMA: gercek cihaz PDU 1000 (trip reset) ve 213 (diagnostik) yazmalarini kabul eder.
Simulator bunlari KAYDEDER ama uygulamaz ve ekrana "olmamasi gereken" diye basar:
PLAN.md GK6 geregi bizim ag gecidimiz bu yazmalari zaten engeller
(firmware/core/modbus_map.c), alarm-codes.yaml HYP-ARC tavsiyesi de
"Reset SAHADA yapilir" der.

Kullanim:
    python tvoc2_sim.py --port 5021 --slave-id 10
    python tvoc2_sim.py --port 5021 --slave-id 10 --trip-after 20
    modpoll -m tcp -0 -a 10 -r 1300 -c 1 127.0.0.1:5021
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from datetime import datetime, timezone

from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSparseDataBlock
from pymodbus.server import StartTcpServer

from panoalgo.devices import (
    TVOC2_DIAGNOSTICS_REG,
    TVOC2_FACTORY_SLAVE_ID,
    TVOC2_RESET_TRIP_REG,
    TVOC2_SYSTEM_STATE_REG,
    TVOC2_TRIP_COUNT_REG,
    Tvoc2Device,
)


class Tvoc2Block(ModbusSparseDataBlock):
    """Register okumalarini canli cihaz modeline yonlendirir.

    Tanimsiz adres icin validate() False doner -> pymodbus ILLEGAL DATA ADDRESS
    (exception 02) uretir. Gercek cihaz da trip bloklarindaki BOSLUK register'i
    icin ayni sekilde davranir.
    """

    def __init__(self, device: Tvoc2Device) -> None:
        super().__init__({0: 0})
        self._device = device

    def validate(self, address, count=1):  # noqa: N802 - pymodbus arayuzu
        return all(self._device.read(address + i) is not None for i in range(count))

    def getValues(self, address, count=1):  # noqa: N802 - pymodbus arayuzu
        return [self._device.read(address + i) or 0 for i in range(count)]

    def setValues(self, address, values):  # noqa: N802 - pymodbus arayuzu
        for offset, value in enumerate(values):
            target = address + offset
            self._device.note_write_attempt(target, value)
            label = {
                TVOC2_RESET_TRIP_REG: "trip reset",
                TVOC2_DIAGNOSTICS_REG: "diagnostik",
            }.get(target, "tanimsiz")
            print(
                f"[tvoc2] YAZMA DENEMESI: PDU {target} ({label}) = {value} — "
                f"UYGULANMADI. Koruma devresine yazma yok (PLAN.md GK6).",
                flush=True,
            )


def build_context(device: Tvoc2Device) -> ModbusServerContext:
    """ID 248 ise HICBIR slave kaydedilmez -> sunucu sessiz kalir.

    pymodbus, istenen unit id baglamda yoksa cevap URETMEZ. "Haberlesme kapali"
    davranisinin birebir karsiligi budur; sahte bir istisna dondurmek yaniltici olurdu.
    """
    if not device.communication_enabled:
        return ModbusServerContext(slaves={}, single=False)

    block = Tvoc2Block(device)
    store = ModbusSlaveContext(hr=block, ir=block, zero_mode=True)
    return ModbusServerContext(slaves={device.slave_id: store}, single=False)


def _trip_after(device: Tvoc2Device, delay_s: float) -> None:
    time.sleep(delay_s)
    device.record_trip(datetime.now(timezone.utc))
    print(
        f"[tvoc2] ARK TRIPI: trip sayaci {device.read(TVOC2_TRIP_COUNT_REG)}, "
        f"system state 0x{device.read(TVOC2_SYSTEM_STATE_REG):04X}",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ABB TVOC-2 Modbus simulatoru (Kisi A)")
    parser.add_argument("--port", type=int, default=5021)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--slave-id", type=int, default=TVOC2_FACTORY_SLAVE_ID,
                        help="fabrika ayari 248 = haberlesme KAPALI; gecerli aralik 1-247")
    parser.add_argument("--trip-after", type=float, default=0.0,
                        help="saniye sonra bir ark tripi enjekte et (0 = yok)")
    parser.add_argument("--sensor-error", action="store_true",
                        help="dedektor arizasi ile basla (pano sessizce korumasiz)")
    args = parser.parse_args(argv)

    device = Tvoc2Device(slave_id=args.slave_id)
    if args.sensor_error:
        device.raise_sensor_error()

    if device.communication_enabled:
        print(f"[tvoc2] slave ID {device.slave_id} | 19200 8E1 esdegeri | TCP {args.host}:{args.port}",
              flush=True)
        print(f"[tvoc2] ornek: modpoll -m tcp -0 -a {device.slave_id} -r {TVOC2_SYSTEM_STATE_REG} "
              f"-c 1 127.0.0.1:{args.port}", flush=True)
    else:
        print(f"[tvoc2] slave ID {device.slave_id} = HABERLESME KAPALI (kilavuz 1.3).", flush=True)
        print("[tvoc2] Cihaz hicbir isteme cevap vermeyecek — istisna bile donmez.", flush=True)
        print("[tvoc2] Acmak icin: --slave-id 10 (gecerli aralik 1-247)", flush=True)

    if args.trip_after > 0.0:
        threading.Thread(target=_trip_after, args=(device, args.trip_after), daemon=True).start()

    StartTcpServer(context=build_context(device), address=(args.host, args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
