"""Pano Beyni haritasi -> IEC 60870-5-104 bilgi nesneleri (TB3 Adim 8, Could, Kisi B).

Merkez, IEC 104'te de Modbus'taki aynı veriyi sunar: her pano bir ortak adres (= Modbus birim numarası), degerler ayni
kodlayicidan (encoder.py) gelir. Nokta plani rapor 6.4c'deki "Modbus bloklariyla ayni mantik" ilkesine uyar:

    olculen deger (M_ME_NC_1 / M_ME_TF_1)  IOA = 1000 + Modbus PDU adresi     (conn_temp.GIRIS_L2 -> 1101)
    alarm biti   (M_SP_NA_1 / M_SP_TB_1)   IOA = 2000 + alarm-codes.yaml biti (ALM-K-WARN -> 2004)
    ozet bit     (M_SP_NA_1 / M_SP_TB_1)   IOA = 3000 + coil adresi           (comms_ok -> 3002)

`alarms` blogu register olarak degil tek nokta olarak, `command` blogu hic sunulmaz: IEC 104 yolu SALT OKUNURDUR (GK6).
Fiziksel deger = isaretli ham x olcek (olcegin ondalik basamagina yuvarlanir). Kodlayicinin "yok" degeri (0x8000 / 0xFFFF)
IV kalite bayragina donusur; sozlesme notunda "yok = 0" olan alanlarda (pd blogu) 0 gecerli deger sayilir.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from . import iec104
from .encoder import NA_INT16, NA_UINT16, PanelEncoder, PanelImage
from .map_loader import RegisterMap

MEASURED_BASE = 1000
ALARM_BIT_BASE = 2000
COIL_BASE = 3000
EXCLUDED_BLOCKS = ("alarms", "command")
INVALID_RAW = (NA_INT16, NA_UINT16)
DEADBAND_STEPS = 10  # kendiliginden gonderim: olcekli deger 10 ham adim degisince (0,1 olcekte 1,0)
LIVE_BITS = ("alarms.alarm_bits_0_15", "alarms.alarm_bits_16_31")


@dataclass(frozen=True)
class MeasuredPoint:
    ioa: int
    name: str
    address: int
    signed: bool
    scale: float
    decimals: int
    na: int | None
    deadband: float


@dataclass(frozen=True)
class SinglePoint:
    ioa: int
    name: str
    kind: str  # "alarm" | "coil"
    index: int


@dataclass(frozen=True)
class PointValue:
    ioa: int
    type_id: int
    value: float | bool
    quality: int


class PointCatalog:
    def __init__(self, regmap: RegisterMap, encoder: PanelEncoder) -> None:
        measured = []
        for block in regmap.blocks:
            if block.name in EXCLUDED_BLOCKS:
                continue
            for register in block.registers:
                na = encoder.na_raw(register.name)
                scale = register.scale if register.scale is not None else 1.0
                measured.append(
                    MeasuredPoint(
                        ioa=MEASURED_BASE + register.address,
                        name=register.name,
                        address=register.address,
                        signed=register.type == "int16",
                        scale=scale,
                        decimals=max(0, -math.floor(math.log10(scale) + 1e-9)),
                        na=na if na in INVALID_RAW else None,
                        deadband=DEADBAND_STEPS * scale if register.scale is not None else 1.0,
                    )
                )
        self.measured: tuple[MeasuredPoint, ...] = tuple(measured)
        bits = sorted((bit, code) for code, bit in encoder.bits.items() if bit < 32)
        singles = [SinglePoint(ALARM_BIT_BASE + bit, code, "alarm", bit) for bit, code in bits]
        singles += [SinglePoint(COIL_BASE + coil.address, coil.name, "coil", coil.address) for coil in regmap.coils]
        self.single: tuple[SinglePoint, ...] = tuple(singles)
        self._live_addresses = tuple(regmap.register(name).address for name in LIVE_BITS)

    def values(self, image: PanelImage | None) -> list[PointValue]:
        if image is None:
            return [PointValue(p.ioa, iec104.M_ME_NC_1, 0.0, iec104.QDS_IV) for p in self.measured] + [
                PointValue(p.ioa, iec104.M_SP_NA_1, False, iec104.QDS_IV) for p in self.single
            ]
        values = []
        for point in self.measured:
            raw = image.registers[point.address]
            if point.na is not None and raw == point.na:
                values.append(PointValue(point.ioa, iec104.M_ME_NC_1, 0.0, iec104.QDS_IV))
                continue
            signed = raw - 0x10000 if point.signed and raw >= 0x8000 else raw
            values.append(PointValue(point.ioa, iec104.M_ME_NC_1, round(signed * point.scale, point.decimals), 0))
        low, high = (image.registers[address] for address in self._live_addresses)
        live = low | (high << 16)
        for point in self.single:
            on = bool((live >> point.index) & 1) if point.kind == "alarm" else image.coils[point.index]
            values.append(PointValue(point.ioa, iec104.M_SP_NA_1, on, 0))
        return values

    def deadbands(self) -> dict[int, float]:
        return {point.ioa: point.deadband for point in self.measured}


def group_objects(values: Sequence[PointValue], limit: int = 30) -> list[tuple[int, list[PointValue]]]:
    """Ayni tipteki ardisik degerleri ASDU basina en cok `limit` nesnelik gruplara ayirir (249 bayt siniri)."""
    groups: list[tuple[int, list[PointValue]]] = []
    for value in values:
        if not groups or groups[-1][0] != value.type_id or len(groups[-1][1]) >= limit:
            groups.append((value.type_id, []))
        groups[-1][1].append(value)
    return groups
