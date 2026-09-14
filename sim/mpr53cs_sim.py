"""ENTES MPR-53CS Modbus simulatoru (TA3 Adim 2, Kisi A).

Cihazin GERCEK register adreslerinde cevap verir; olcek ve donusum mantigi
libs/panoalgo/panoalgo/devices.py icindedir ve orada testlerle kilitlenmistir.

DONUSUM (rapor 15.1):
    I_primer = ham x 0.001 x CT      CT register 0x8001 (32769), 2500/5 AT icin 500
Dogrulama: 1600 kVA / 400 V nominal 2309 A -> ham 4618. Juri 0x8001'i okuyunca 500,
6 numarali register'i okuyunca 4618 gormeli.

KILAVUZ BELIRSIZLIGI (juriye acikca soylenecek): kilavuzun RANGE kolonu "(0-6000)xCT"
yazar ve iki turlu okunabilir — (a) ham deger 0-6000, CT ile MASTER carpar; (b) ham
deger zaten carpilmis gelir. Proje sozlesmesi (rapor 15.1, contracts/modbus-map.yaml)
(a) yorumunu dondurmustur ve simulator ona gore yazilmistir. Bu belirsizligi
sunumda soylemek zayiflik degil olgunluk gostergesidir.

Veri kaynagi: istege bagli olarak panoalgo ureteci beslenir, yani analizor
"gercek" bir panonun akimlarini gosterir (sim/panosim.py ile ayni fizik).

Kullanim:
    python mpr53cs_sim.py --port 5020 --slave-id 1
    modpoll -m tcp -0 -a 1 -r 6 -c 2 127.0.0.1:5020        # L1 faz akimi (32 bit)
    modpoll -m tcp -0 -a 1 -r 32769 -c 1 127.0.0.1:5020    # CT orani
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from datetime import datetime, timezone

from pymodbus.datastore import ModbusServerContext, ModbusSlaveContext, ModbusSparseDataBlock
from pymodbus.server import StartTcpServer

from panoalgo.devices import MPR_CT_REGISTER, Mpr53csDevice
from panoalgo.generator import PanelSimulator

LIVE_STEP_S = 1.0


class MprBlock(ModbusSparseDataBlock):
    """Register okumalarini canli cihaz modeline yonlendirir."""

    def __init__(self, device: Mpr53csDevice) -> None:
        super().__init__({0: 0})
        self._device = device

    def validate(self, address, count=1):  # noqa: N802 - pymodbus arayuzu
        registers = self._device.registers()
        return all((address + i) in registers for i in range(count))

    def getValues(self, address, count=1):  # noqa: N802 - pymodbus arayuzu
        registers = self._device.registers()
        return [registers.get(address + i, 0) for i in range(count)]

    def setValues(self, address, values):  # noqa: N802 - pymodbus arayuzu
        """Enerji sayaclari ve min/max gercek cihazda yazilabilir (sifirlama), ama
        bizim ag gecidimiz analizore de yazmaz — deneme kaydedilir."""
        for offset, value in enumerate(values):
            self._device.note_write_attempt(address + offset, value)
            print(f"[mpr53cs] YAZMA DENEMESI: PDU {address + offset} = {value} — UYGULANMADI.",
                  flush=True)


def _feed_from_generator(device: Mpr53csDevice, sim: PanelSimulator, speed: float) -> None:
    """Analizoru panoalgo uretecinin akimlariyla besler (panosim ile ayni fizik)."""
    while True:
        payload = sim.step(LIVE_STEP_S * speed)
        elec = payload["elec"]
        device.i_ph = tuple(elec["i_ph"])
        device.i_n = elec["i_n"]
        device.u_ph = tuple(elec["u_ph"])
        device.thd_i = tuple(elec["thd_i"])
        device.cosphi = elec["cosphi"]
        time.sleep(LIVE_STEP_S)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ENTES MPR-53CS Modbus simulatoru (Kisi A)")
    parser.add_argument("--port", type=int, default=5020)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--slave-id", type=int, default=1)
    parser.add_argument("--ct", type=int, default=500, help="akim trafosu orani (2500/5 -> 500)")
    parser.add_argument("--static", action="store_true",
                        help="sabit degerler yayinla (uretec baglanmaz)")
    parser.add_argument("--speed", type=float, default=60.0, help="uretec hiz carpani")
    parser.add_argument("--seed", type=int, default=1000)
    args = parser.parse_args(argv)

    device = Mpr53csDevice(slave_id=args.slave_id, ct_ratio=args.ct)

    if args.static:
        device.i_ph = (2309.0, 2280.0, 2295.0)
        device.i_n = 180.0
        print("[mpr53cs] sabit mod: L1 = 2309 A (1600 kVA / 400 V nominal)", flush=True)
    else:
        sim = PanelSimulator(
            pano_id="ADM-00001", seed=args.seed, profile="karma",
            start=datetime.now(timezone.utc),
        )
        threading.Thread(target=_feed_from_generator, args=(device, sim, args.speed),
                         daemon=True).start()
        print(f"[mpr53cs] canli mod: panoalgo ureteci, hiz x{args.speed}", flush=True)

    print(f"[mpr53cs] slave ID {device.slave_id} | CT {device.ct_ratio} "
          f"(PDU {MPR_CT_REGISTER} = 0x{MPR_CT_REGISTER:04X}) | TCP {args.host}:{args.port}",
          flush=True)
    print(f"[mpr53cs] ornek: modpoll -m tcp -0 -a {device.slave_id} -r 6 -c 2 "
          f"127.0.0.1:{args.port}   # L1 faz akimi (32 bit)", flush=True)

    block = MprBlock(device)
    store = ModbusSlaveContext(hr=block, ir=block, zero_mode=True)
    context = ModbusServerContext(slaves={device.slave_id: store}, single=False)
    StartTcpServer(context=context, address=(args.host, args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
