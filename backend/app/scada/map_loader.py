"""contracts/modbus-map.yaml -> Pano Beyni register tablosu (TB3 Adim 1, Kisi B).

Harita TEK KAYNAKTIR (PLAN.md kural 10): Modbus TCP ag gecidi ve docs/03 ureteci adresleri
buradan alir, hicbiri adres yazmaz. Bozuk harita (cakisan blok, blok disina tasan kayit, tipsiz
register) yuklenirken MapError atar: yanlis adresle yayin yapmaktansa servis hic kalkmaz.

Adresler PDU adresidir (0 tabanli). Register numarasi = adres + 1 (Modicon 40001/30001 gosterimi).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REGISTER_TYPES = ("int16", "uint16")
ACCESS_MODES = ("read", "read_only", "write")
WRITE_FUNCTIONS = (6, 16)


class MapError(ValueError):
    """Harita sozlesmesi kendi icinde tutarsiz."""


@dataclass(frozen=True)
class Register:
    address: int
    name: str  # "<blok>.<kayit>" veya "<blok>.<nokta>"
    block: str
    type: str
    scale: float | None
    unit: str | None
    access: str
    note: str | None = None
    point: str | None = None
    src_pdu: int | None = None


@dataclass(frozen=True)
class Block:
    name: str
    start: int
    count: int
    access: str
    registers: tuple[Register, ...]
    functions: tuple[int, ...] = ()
    source: str | None = None
    note: str | None = None

    @property
    def end(self) -> int:
        """Blogun ilk bos adresi (dahil degil)."""
        return self.start + self.count

    def contains(self, address: int, count: int = 1) -> bool:
        return self.start <= address and address + count <= self.end


@dataclass(frozen=True)
class Coil:
    address: int
    name: str
    note: str | None = None


@dataclass(frozen=True)
class RegisterMap:
    version: int
    mirror_fc03_fc04: bool
    blocks: tuple[Block, ...]
    coils: tuple[Coil, ...]
    points: tuple[str, ...]

    def __post_init__(self) -> None:
        index = {register.name: register for block in self.blocks for register in block.registers}
        object.__setattr__(self, "_registers", index)
        object.__setattr__(self, "_blocks", {block.name: block for block in self.blocks})

    def block(self, name: str) -> Block:
        return self._blocks[name]

    def register(self, name: str) -> Register:
        return self._registers[name]

    def block_for(self, address: int, count: int = 1) -> Block | None:
        """Araligin tamamini iceren blok; iki bloga veya bosluga tasan aralikta None."""
        for block in self.blocks:
            if block.contains(address, count):
                return block
        return None


def load_map(path: Path) -> RegisterMap:
    return parse_map(yaml.safe_load(path.read_text(encoding="utf-8")))


def parse_map(doc: Mapping[str, Any]) -> RegisterMap:
    blocks_doc = list(doc["blocks"])
    _check_overlaps(blocks_doc)

    # Nokta listesi olan bloklar (sozlesmede conn_temp); diger nokta bloklari points_ref ile ayni sirayi kullanir.
    point_lists = {block["name"]: list(block["points"]) for block in blocks_doc if "points" in block}
    for block in blocks_doc:
        ref = block.get("points_ref")
        if ref is not None and ref not in point_lists:
            raise MapError(f"blok '{block['name']}': points_ref '{ref}' nokta listesi olan bir blok degil")

    blocks = tuple(_parse_block(block, point_lists) for block in blocks_doc)
    return RegisterMap(
        version=int(doc["version"]),
        mirror_fc03_fc04=bool(doc.get("mirror_fc03_fc04", False)),
        blocks=blocks,
        coils=_parse_coils(doc.get("coils") or {}),
        points=tuple(next(iter(point_lists.values()), ())),
    )


def _check_overlaps(blocks_doc: list[Mapping[str, Any]]) -> None:
    ordered = sorted(blocks_doc, key=lambda b: b["start"])
    for previous, current in zip(ordered, ordered[1:]):
        if previous["start"] + previous["count"] > current["start"]:
            raise MapError(
                f"adres cakismasi: '{previous['name']}' ({previous['start']}-{previous['start'] + previous['count'] - 1}) "
                f"ile '{current['name']}' ({current['start']}-{current['start'] + current['count'] - 1})"
            )


def _parse_block(block: Mapping[str, Any], point_lists: dict[str, list[str]]) -> Block:
    name, start, count = block["name"], int(block["start"]), int(block["count"])
    access = block.get("access", "read")
    if access not in ACCESS_MODES:
        raise MapError(f"blok '{name}': bilinmeyen erisim '{access}'")
    functions = tuple(int(fc) for fc in block.get("functions", ()))
    if access == "write" and (not functions or any(fc not in WRITE_FUNCTIONS for fc in functions)):
        raise MapError(f"blok '{name}': yazilabilir blok yalnizca {WRITE_FUNCTIONS} fonksiyonlarini tanimlayabilir: {functions}")

    points = point_lists.get(block.get("points_ref") or name)
    if points is not None:
        if len(points) > count:
            raise MapError(f"blok '{name}': {len(points)} nokta, yalnizca {count} register var")
        items = [{"offset": offset, "name": point, "point": point} for offset, point in enumerate(points)]
    else:
        items = list(block.get("items", ()))

    registers: list[Register] = []
    seen_offsets: dict[int, str] = {}
    for item in items:
        offset, item_name = int(item["offset"]), item["name"]
        if not 0 <= offset < count:
            raise MapError(f"blok '{name}': '{item_name}' offset {offset} blok disinda (count {count})")
        if offset in seen_offsets:
            raise MapError(f"blok '{name}': '{item_name}' ile '{seen_offsets[offset]}' ayni offset {offset}")
        seen_offsets[offset] = item_name
        register_type = item.get("type", block.get("type"))
        if register_type is None:
            raise MapError(f"blok '{name}': '{item_name}' icin tip yok (kayitta veya blokta 'type' gerekli)")
        if register_type not in REGISTER_TYPES:
            raise MapError(f"blok '{name}': '{item_name}' bilinmeyen tip '{register_type}'")
        scale = item.get("scale", block.get("scale"))
        registers.append(
            Register(
                address=start + offset,
                name=f"{name}.{item_name}",
                block=name,
                type=register_type,
                scale=float(scale) if scale is not None else None,
                unit=item.get("unit", block.get("unit")),
                access=access,
                note=item.get("note"),
                point=item.get("point"),
                src_pdu=item.get("src_pdu"),
            )
        )
    return Block(
        name=name,
        start=start,
        count=count,
        access=access,
        registers=tuple(sorted(registers, key=lambda r: r.address)),
        functions=functions,
        source=block.get("source"),
        note=block.get("note"),
    )


def _parse_coils(coils_doc: Mapping[str, Any]) -> tuple[Coil, ...]:
    coils: dict[int, Coil] = {}
    for item in coils_doc.get("items", ()):
        address = int(item["addr"])
        if address in coils:
            raise MapError(f"coil adresi {address} iki kez tanimli: '{coils[address].name}' ve '{item['name']}'")
        coils[address] = Coil(address=address, name=item["name"], note=item.get("note"))
    return tuple(coils[address] for address in sorted(coils))
