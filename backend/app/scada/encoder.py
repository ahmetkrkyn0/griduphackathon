"""Pano son durumu + alarm yoneticisi -> Pano Beyni register goruntusu (TB3 Adim 2, Kisi B).

Merkezdeki Modbus TCP ag gecidi, kenardaki Pano Beyni'nin sundugu haritanin AYNISINI sunar
(contracts/modbus-map.yaml): SCADA icin merkez de "bir Pano Beyni"dir. Degerlerin kaynagi:
  - olcumler       -> panonun en son telemetri yuku (ingest / panel_latest)
  - alarm bitleri  -> merkezdeki ISA-18.2 alarm yoneticisi (onay, raf ve ALM-COMMS-LOST dahil)
  - haberlesme     -> merkezin panodan son veri aldigi an (thresholds.heartbeat_timeout_min)

Kodlama kurallari (docs/03'e de basilir):
  - ham = fiziksel / scale, yarim yukari yuvarlanir; negatif int16 ikiye tumleyen uint16 olarak gider.
  - Aralik disi olcum DOYAR (int16 +-32767, uint16 0..65534), sarmaz. Sayac ve bit alani 16 bitle sarar.
  - "Yok" (kenar gondermiyor, sensor yok): int16 -> 0x8000, uint16 -> 0xFFFF. Sozlesme notu baska bir
    deger soyluyorsa (voc_idx, pd blogu) not kazanir. Tanimsiz (yedek) register 0 okunur.

Her tanimli register'in kaynagi SOURCES / POINT_SOURCES tablosundadir. Tabloda karsiligi olmayan register
varsa kodlayici hic kurulmaz: sozlesmeye register eklenip burasi unutulursa SCADA'ya sessizce 0 gitmesin.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from typing import Any

from ..alarm_manager import Alarm
from ..api.views import comms_ok_since, point_state
from ..config import PRIO_ORDER, Contracts
from .map_loader import Register, RegisterMap

NA_INT16 = 0x8000
NA_UINT16 = 0xFFFF
INT16_LIMIT = 0x7FFF  # -32768 "yok" icin ayrildi
UINT16_LIMIT = 0xFFFE  # 65535 "yok" icin ayrildi

MEASURE, RAW, FLAG = "measure", "raw", "flag"

# modbus-map.yaml notlari: device_info.pano_type "1 = 1600 kVA dahili", alarms.highest_prio kodlari
PANEL_TYPE_CODES = {"1600kVA-dahili": 1}
PRIO_CODES = {"P1": 1, "P2": 2, "P3": 3, "INFO": 4, "SYS": 5}

LIVE_STATES = ("active", "acked")  # rafa alinmis alarm SCADA'ya da duyurulmaz
WARNING_PRIOS = frozenset({"P2", "P3"})
DQ_PREFIX = "ALM-DQ-"
POINT_STATE_RANK = {"normal": 0, "warn": 1, "alarm": 2, "critical": 3}


@dataclass(frozen=True)
class EventLog:
    """Ag gecidinin gordugu son alarm acilislari (event blogu)."""

    count: int = 0
    last_bit: int | None = None
    last_at: datetime | None = None


@dataclass(frozen=True)
class PanelSnapshot:
    pano_id: str
    pano_type: str | None
    payload: Mapping[str, Any]
    last_rx: datetime | None
    alarms: Sequence[Alarm] = ()
    latched_bits: int = 0
    events: EventLog = field(default_factory=EventLog)


@dataclass(frozen=True)
class PanelImage:
    registers: tuple[int, ...]  # PDU adresi -> ham uint16
    coils: tuple[bool, ...]


@dataclass(frozen=True)
class Source:
    doc: str
    get: Callable[[_Facts], Any]
    kind: str = MEASURE
    na: int | None = None  # sozlesme notundaki "yok" degeri; None -> tipin varsayilani


def _missing(_: _Facts) -> None:
    return None


def _zero(_: _Facts) -> int:
    return 0


def _get(section: str, key: str) -> Callable[[_Facts], Any]:
    return lambda f: (getattr(f, section) or {}).get(key)


def _item(section: str, key: str, index: int) -> Callable[[_Facts], Any]:
    def get(f: _Facts) -> Any:
        values = (getattr(f, section) or {}).get(key)
        return values[index] if values is not None and len(values) > index else None

    return get


def _section(section: str, key: str, kind: str = MEASURE, na: int | None = None) -> Source:
    return Source(f"`{section}.{key}`", _get(section, key), kind, na)


def _phases(section: str, key: str, name: str) -> dict[str, Source]:
    return {name.format(n=n + 1): Source(f"`{section}.{key}[{n}]`", _item(section, key, n)) for n in range(3)}


NOT_SENT = "- (kenar merkeze gondermiyor; hep 'yok')"

SOURCES: dict[str, Source] = {
    # device_info
    "device_info.map_version": Source("modbus-map.yaml `version`", lambda f: f.map_version, RAW),
    "device_info.fw_version": Source("`fw` 'M.m.p' -> 0xMmpp", lambda f: f.fw_code, RAW),
    "device_info.serial_hi": Source(NOT_SENT, _missing, RAW),
    "device_info.serial_lo": Source(NOT_SENT, _missing, RAW),
    "device_info.pano_type": Source("`panels.pano_type` (1600kVA-dahili = 1, bilinmeyen = 0)", lambda f: f.pano_type_code, RAW),
    "device_info.point_count": Source("`t_conn` nokta sayisi", lambda f: len(f.points_list)),
    # health
    "health.uptime_h": Source("`health.uptime_s` / 3600", lambda f: f.uptime_h),
    "health.last_sync_m": Source("merkezin panodan son veri aldigi andan beri gecen dakika", lambda f: f.last_sync_m),
    "health.supply_state": Source("canli ALM-LASTGASP -> 2; aksi halde 'yok'", lambda f: f.supply_state, RAW),
    "health.backup_pct": _section("health", "vbak_pct"),
    "health.rssi_dbm_neg": Source("-`health.rssi_dbm`", lambda f: f.rssi_neg),
    "health.nodes_ok": _section("health", "nodes_ok"),
    "health.nodes_total": _section("health", "nodes_total"),
    "health.heartbeat": Source("`seq` (16 bit sarar; donarsa kenar sessiz)", lambda f: f.payload.get("seq"), RAW),
    "health.buffered_msgs": _section("health", "buffered"),
    "health.baseline_day": _section("health", "baseline_day"),
    # environment
    **{f"environment.{key}": _section("env", key) for key in ("t_low_c", "rh_low_pct", "td_low_c", "td_margin_k", "t_up_c", "rh_up_pct", "dt_air_k")},
    "environment.voc_idx": _section("env", "voc_idx", na=NA_UINT16),
    # electrical_mirror (MPR-53CS)
    **_phases("elec", "i_ph", "electrical_mirror.i_l{n}_a"),
    "electrical_mirror.i_n_a": _section("elec", "i_n"),
    **_phases("elec", "u_ph", "electrical_mirror.u_l{n}_v"),
    **_phases("elec", "thd_i", "electrical_mirror.thd_i_l{n}_pct"),
    "electrical_mirror.cosphi": _section("elec", "cosphi"),
    "electrical_mirror.unbal_pct": _section("elec", "unbal_pct"),
    "electrical_mirror.mpr_comm_ok": Source("`elec` geldiyse 1", lambda f: f.elec is not None, FLAG),
    # arc_mirror (TVOC-2, salt okunur)
    "arc_mirror.system_state": _section("tvoc", "state", RAW),
    "arc_mirror.trip_count": _section("tvoc", "trips", RAW),
    "arc_mirror.last_det_low": _section("tvoc", "det_bits_low", RAW),
    "arc_mirror.last_det_high": _section("tvoc", "det_bits_high", RAW),
    **{f"arc_mirror.{key}": Source(NOT_SENT, _missing, RAW) for key in ("last_trip_relay", "last_trip_date", "last_trip_hhmm", "last_trip_sec", "active_dtc_1")},
    "arc_mirror.sensor_status_x2": _section("tvoc", "sensor_x2", RAW),
    "arc_mirror.sensor_status_x3": _section("tvoc", "sensor_x3", RAW),
    "arc_mirror.amb_light_x2": _section("tvoc", "amb_light_x2", RAW),
    "arc_mirror.amb_light_x3": _section("tvoc", "amb_light_x3", RAW),
    "arc_mirror.prot_health_ok": Source("`tvoc.prot_health_ok` (TVOC-2 yoksa 0)", lambda f: f.prot_health_ok, FLAG),
    "arc_mirror.tvoc_comm_ok": Source("`tvoc.comm_ok` (TVOC-2 yoksa 0)", lambda f: f.tvoc_comm_ok, FLAG),
    # pd (OG eklentisi; sozlesme notu: AG panoda 65535/0)
    "pd.pulses_per_s": _section("pd", "pps"),
    "pd.amp_dbmv": _section("pd", "amp_dbmv", na=0),
    "pd.trend_slope": _section("pd", "trend", na=0),
    "pd.phase_cluster": _section("pd", "phase_cluster"),
    # risk
    "risk.risk_score": _section("risk", "score"),
    "risk.fault_mode": Source("`risk.mode` -> hypotheses[].id", lambda f: f.fault_mode, RAW),
    "risk.ttl_hours": _section("risk", "ttl_h"),
    "risk.worst_point": Source("en kotu nokta: durum > K/K0 > dT (yalnizca q = 0)", lambda f: f.worst_point, RAW),
    # alarms (merkez alarm yoneticisi)
    "alarms.alarm_bits_0_15": Source("canli alarmlar (active/acked, kosul suruyor), bit 0-15", lambda f: f.live_bits, RAW),
    "alarms.alarm_bits_16_31": Source("canli alarmlar, bit 16-31", lambda f: f.live_bits >> 16, RAW),
    "alarms.latched_bits_0_15": Source("canli | onaysiz | mandal (reset_latch'e kadar), bit 0-15", lambda f: f.latched_bits, RAW),
    "alarms.latched_bits_16_31": Source("mandalli kopya, bit 16-31", lambda f: f.latched_bits >> 16, RAW),
    "alarms.active_alarm_count": Source("canli alarm sayisi", lambda f: f.live_count),
    "alarms.highest_prio": Source("canli alarmlarin en acili (P1>P2>P3>SYS>INFO)", lambda f: f.highest_prio, RAW),
    # event
    "event.event_count": Source("ag gecidinin gordugu alarm acilislari (16 bit sarar)", lambda f: f.events.count, RAW),
    "event.last_code": Source("son acilan alarmin bit numarasi", lambda f: f.events.last_bit, RAW),
    "event.ts_hi": Source("son acilisin olay zamani, Unix s yuksek word", lambda f: f.event_ts_hi, RAW, na=0),
    "event.ts_lo": Source("son acilisin olay zamani, Unix s dusuk word", lambda f: f.event_ts_lo, RAW, na=0),
    # command (okumada)
    "command.password": Source("okumada her zaman 0", _zero, RAW),
    "command.ack_alarm": Source("komut; okumada 0", _zero, RAW),
    "command.reset_latch": Source("komut; okumada 0", _zero, RAW),
    "command.maint_mode": Source("komut; okumada `health.maint_mode`", lambda f: f.maint, FLAG),
    "command.test_alarm": Source("komut; okumada 0", _zero, RAW),
}

# nokta bloklari: (belge, t_conn alani, carpan)
POINT_SOURCES: dict[str, tuple[str, str, float]] = {
    "conn_temp": ("`t_conn[{pt}].t_c`", "t_c", 1.0),
    "conn_dt": ("`t_conn[{pt}].dt_c`", "dt_c", 1.0),
    "k_index": ("`t_conn[{pt}].k_ratio` x 100", "k_ratio", 100.0),
}

COIL_SOURCES: dict[str, tuple[str, Callable[[_Facts], bool]]] = {
    "critical_alarm": ("canli P1 alarm var", lambda f: f.critical),
    "warning_active": ("canli P2 veya P3 alarm var", lambda f: f.warning),
    "comms_ok": ("son veri heartbeat_timeout_min icinde", lambda f: f.comms_ok),
    "maint_mode": ("`health.maint_mode`", lambda f: f.maint),
    "prot_health_ok": ("`tvoc.prot_health_ok` (TVOC-2 yoksa 0)", lambda f: f.prot_health_ok),
    "data_quality_ok": ("tum noktalarda q = 0 ve canli ALM-DQ-* yok", lambda f: f.data_quality_ok),
}


def _point_value(pt: str, key: str, factor: float, f: _Facts) -> float | None:
    point = f.points.get(pt)
    value = point.get(key) if point is not None else None
    return None if value is None else value * factor


def _plan(regmap: RegisterMap) -> list[tuple[Register, Source]]:
    plan: list[tuple[Register, Source]] = []
    missing: list[str] = []
    for block in regmap.blocks:
        for register in block.registers:
            if register.point is not None and block.name in POINT_SOURCES:
                doc, key, factor = POINT_SOURCES[block.name]
                source = Source(doc.format(pt=register.point), partial(_point_value, register.point, key, factor))
            else:
                source = SOURCES.get(register.name)
            if source is None:
                missing.append(register.name)
            else:
                plan.append((register, source))
    missing += [coil.name for coil in regmap.coils if coil.name not in COIL_SOURCES]
    if missing:
        raise ValueError(f"merkez kaynagi tanimsiz register/coil: {missing} (app/scada/encoder.py SOURCES)")
    return plan


def source_docs(regmap: RegisterMap) -> dict[str, str]:
    """Register/coil adi -> merkezdeki kaynagi (docs/03 ureteci icin)."""
    docs = {register.name: source.doc for register, source in _plan(regmap)}
    docs.update({f"coils.{coil.name}": COIL_SOURCES[coil.name][0] for coil in regmap.coils})
    return docs


class PanelEncoder:
    def __init__(self, regmap: RegisterMap, contracts: Contracts) -> None:
        self._regmap = regmap
        self._contracts = contracts
        self._plan = tuple(_plan(regmap))
        self._size = max((block.end for block in regmap.blocks), default=0)
        self._coils = tuple((coil.address, COIL_SOURCES[coil.name][1]) for coil in regmap.coils)
        self._coil_size = max((coil.address + 1 for coil in regmap.coils), default=0)
        self.bits = {alarm["code"]: int(alarm["bit"]) for alarm in contracts.alarm_codes["alarms"]}
        self._hypothesis_ids = {h["code"]: int(h["id"]) for h in contracts.alarm_codes["hypotheses"]}
        self._point_index = {pt: index for index, pt in enumerate(regmap.points)}

    def encode(self, snapshot: PanelSnapshot, now: datetime) -> PanelImage:
        facts = _Facts(self, snapshot, now)
        registers = [0] * self._size
        for register, source in self._plan:
            registers[register.address] = _raw(source.get(facts), register, source)
        coils = [False] * self._coil_size
        for address, get in self._coils:
            coils[address] = bool(get(facts))
        return PanelImage(tuple(registers), tuple(coils))

    def bitmask(self, alarms: Sequence[Alarm]) -> int:
        mask = 0
        for alarm in alarms:
            bit = self.bits.get(alarm.code)
            if bit is not None and bit < 32:
                mask |= 1 << bit
        return mask

    def worst_point(self, points: Sequence[Mapping[str, Any]]) -> int | None:
        best: tuple[int, tuple] | None = None
        thresholds = self._contracts.thresholds
        for point in points:
            index = self._point_index.get(point["pt"])
            if index is None or point.get("q", 0) != 0:
                continue
            key = (POINT_STATE_RANK[point_state(point, thresholds, True)], point.get("k_ratio") or 0.0, point["dt_c"])
            if best is None or key > best[1]:
                best = (index, key)
        return best[0] if best is not None else None


class _Facts:
    """Tek kodlamada bir kez turetilen degerler (kaynak tablosundaki islevler bunlari okur)."""

    def __init__(self, encoder: PanelEncoder, snapshot: PanelSnapshot, now: datetime) -> None:
        payload = snapshot.payload
        self.payload = payload
        self.map_version = encoder._regmap.version
        self.health = payload.get("health") or {}
        self.env = payload.get("env") or {}
        self.elec = payload.get("elec")
        self.tvoc = payload.get("tvoc")
        self.pd = payload.get("pd")
        self.risk = payload.get("risk")
        self.points_list = list(payload.get("t_conn") or ())
        self.points = {point["pt"]: point for point in self.points_list}

        self.pano_type_code = PANEL_TYPE_CODES.get(snapshot.pano_type or "", 0)
        self.fw_code = _firmware_code(payload.get("fw"))
        uptime_s = self.health.get("uptime_s")
        self.uptime_h = None if uptime_s is None else uptime_s // 3600
        rssi = self.health.get("rssi_dbm")
        self.rssi_neg = None if rssi is None else -rssi
        self.comms_ok = comms_ok_since(snapshot.last_rx, encoder._contracts, now)
        self.last_sync_m = None if snapshot.last_rx is None else int((now - snapshot.last_rx).total_seconds() // 60)

        live = [a for a in snapshot.alarms if a.state in LIVE_STATES and a.cleared_at is None]
        unacked = [a for a in snapshot.alarms if a.state == "active"]
        live_prios = {alarm.prio for alarm in live}
        self.live_codes = {alarm.code for alarm in live}
        self.live_bits = encoder.bitmask(live)
        self.latched_bits = snapshot.latched_bits | self.live_bits | encoder.bitmask(unacked)
        self.live_count = len(live)
        ranked = [prio for prio in PRIO_ORDER if prio in live_prios]
        self.highest_prio = PRIO_CODES[ranked[0]] if ranked else 0
        self.critical = "P1" in live_prios
        self.warning = bool(live_prios & WARNING_PRIOS)
        self.supply_state = 2 if "ALM-LASTGASP" in self.live_codes else None

        self.maint = bool(self.health.get("maint_mode", False))
        self.prot_health_ok = self.tvoc is not None and self.tvoc.get("prot_health_ok") is True
        self.tvoc_comm_ok = self.tvoc is not None and bool(self.tvoc.get("comm_ok", True))
        self.data_quality_ok = all(p.get("q", 0) == 0 for p in self.points_list) and not any(
            code.startswith(DQ_PREFIX) for code in self.live_codes
        )
        self.fault_mode = encoder._hypothesis_ids.get(self.risk.get("mode")) if self.risk else None
        self.worst_point = encoder.worst_point(self.points_list)

        self.events = snapshot.events
        event_ts = int(snapshot.events.last_at.timestamp()) if snapshot.events.last_at is not None else None
        self.event_ts_hi = None if event_ts is None else event_ts >> 16
        self.event_ts_lo = None if event_ts is None else event_ts & 0xFFFF


def _firmware_code(version: Any) -> int | None:
    """'0.3.1' -> 0x0301 (modbus-map.yaml notu): ust nibble major, alt nibble minor, dusuk bayt yama."""
    try:
        major, minor, patch = (int(part) for part in str(version).split("."))
    except ValueError:
        return None
    if not (0 <= major <= 15 and 0 <= minor <= 15 and 0 <= patch <= 255):
        return None
    return (major << 12) | (minor << 8) | patch


def _scaled(value: float, scale: float | None) -> int:
    """Yarim yukari yuvarlama. 0.1 gibi olceklerde bolmek yerine tam sayi carpanla carpar (4.35 -> 44)."""
    if scale is None:
        return math.floor(value + 0.5)
    factor = 1.0 / scale
    nearest = round(factor)
    if abs(factor - nearest) < 1e-9:
        return math.floor(value * nearest + 0.5)
    return math.floor(value / scale + 0.5)


def _raw(value: Any, register: Register, source: Source) -> int:
    if value is None:
        if source.na is not None:
            return source.na
        return NA_INT16 if register.type == "int16" else NA_UINT16
    if source.kind == FLAG:
        return 1 if value else 0
    if source.kind == RAW:
        return int(value) & 0xFFFF
    low, high = (-INT16_LIMIT, INT16_LIMIT) if register.type == "int16" else (0, UINT16_LIMIT)
    return min(max(_scaled(float(value), register.scale), low), high) & 0xFFFF
