"""SCADA ag gecidi (TB3 Adim 2, Kisi B): Modbus birimi -> pano, register goruntusu, yazma politikasi.

Merkez, SCADA/RTU icin her panoyu bir Modbus birimi (unit id 1-247) olarak sunar; her birimde kenardaki
Pano Beyni'nin haritasi birebir bulunur (contracts/modbus-map.yaml). Birim eslemesi:
  - MODBUS_UNITS="1=ADM-00001,2=ADM-00002" -> sabit. Sahada ZORUNLU: SCADA veritabani birim numarasina baglidir.
  - bos -> otomatik: pano kimligi sirasiyla ilk 247 pano. Yalnizca demo kolayligi; araya yeni pano girerse
    numaralar kayar.

Veri yolu: ingest dinleyicisi panonun son yukunu, alarm dinleyicisi mandal ve olay sayacini bellekte tutar;
okuma istegi veritabanina gitmez. Backend yeniden basladiginda son durum `refresh()` ile depodan yuklenir.

Istisna kodlari (docs/03):
  0x0A birim eslenmemis · 0x02 adres harita bloklari disinda (yazmada: komut blogu disinda)
  0x0B panonun verisi yok, alarm durumu yuklenmedi veya komut kenara iletilemedi
  0x01 yazma kapali, baglanti kilidi acilmamis veya istemci kilitli · 0x03 yanlis sifre ya da gecersiz komut

Yazma politikasi (rapor 7.4 "salt okunur varsayilan", GK6 "koruma devresine yazma yok"):
  - MODBUS_WRITE_PASSWORD bos -> ag gecidi SALT OKUNUR.
  - Yazma yalnizca `command` blogunda; TVOC-2 aynasi dahil diger her adres 0x02.
  - Sifre 900'e yazilir: dogruysa bu BAGLANTI `unlock_s` sure acilir (ayni FC16 istegindeki komutlar da calisir);
    yanlissa 0x03. Ayni IP'den `max_password_failures` yanlis sifre -> `lockout_s` yazma kilidi (16 bit sifre
    kaba kuvvete tek basina dayanmaz).
  - Istek once tamamen dogrulanir, sonra calisir: tek gecersiz deger tum istegi reddeder.
  - 901 ack_alarm: 0 yok, bit+1 o koddaki alarmlar, 0xFFFF panonun tum onaylanabilir alarmlari. Merkez alarm
    yoneticisinde onaylanir; denetim izine "SCADA Modbus <ip> (birim N)" olarak yazilir.
  - 902 reset_latch: 1 -> mandalli bitler silinir (kosulu suren/onaysiz alarmlarin biti yine gorunur).
  - 903 maint_mode (1 ac, 2 kapat) ve 904 test_alarm (1): MQTT cmd topic'i ile KENARA iletilir; bakim modu
    kenarin durumudur ve yeniden telemetriyle (`health.maint_mode`) geri okunur.
  - 905-909 yedek: yalnizca 0 yazilabilir.
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from ..alarm_manager import Alarm, AlarmNotFound, AlarmStateConflict, Change
from ..config import Contracts
from ..db import Store
from ..models import Sample
from .encoder import EventLog, PanelEncoder, PanelImage, PanelSnapshot
from .map_loader import RegisterMap
from .modbus_tcp import READ_INPUT_REGISTERS, ExceptionCode, ModbusError, Session

log = logging.getLogger("gridup.scada")

MAX_UNIT = 247
ACK_ALL = 0xFFFF
ACK_MAX_BIT_VALUE = 32  # ack_alarm = bit + 1 (bit 0-31)
MAINT_ON, MAINT_OFF = 1, 2
UNLOCK_S = 60.0
MAX_PASSWORD_FAILURES = 3
LOCKOUT_S = 300.0
ACKABLE_STATES = ("active", "shelved")  # alarm_manager.ack ile ayni
LATCHING_CHANGES = ("raised", "reactivated")

CommandSink = Callable[[str, str, dict[str, Any]], bool]


class AlarmAccess(Protocol):
    def open_alarms(self, pano_id: str) -> list[Alarm] | None: ...

    def ack(self, alarm_id: int, *, by: str, note: str | None = None) -> Alarm: ...


@dataclass
class _Panel:
    pano_type: str | None = None
    payload: Mapping[str, Any] | None = None
    ts: datetime | None = None
    last_rx: datetime | None = None
    latched: int = 0
    events: EventLog = field(default_factory=EventLog)

    def offer(self, payload: Mapping[str, Any], ts: datetime, received_at: datetime | None) -> None:
        """Yalnizca daha yeni olcum son durumu degistirir (backfill ezmez); son alim zamani her zaman ilerler."""
        if self.ts is None or ts >= self.ts:
            self.payload, self.ts = payload, ts
        if received_at is not None and (self.last_rx is None or received_at > self.last_rx):
            self.last_rx = received_at


class ScadaGateway:
    def __init__(
        self,
        regmap: RegisterMap,
        contracts: Contracts,
        *,
        alarms: AlarmAccess,
        store: Store,
        clock: Callable[[], datetime],
        units: Mapping[int, str] | None = None,
        password: int | None = None,
        command_sink: CommandSink | None = None,
        unlock_s: float = UNLOCK_S,
        max_password_failures: int = MAX_PASSWORD_FAILURES,
        lockout_s: float = LOCKOUT_S,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._regmap = regmap
        self._encoder = PanelEncoder(regmap, contracts)
        self._alarms = alarms
        self._store = store
        self._clock = clock
        self._auto_units = units is None
        self._units: dict[int, str] = dict(units or {})
        self._fixed_ids = frozenset(self._units.values())
        self._password = password
        self._sink = command_sink
        self._unlock_s = unlock_s
        self._max_failures = max_password_failures
        self._lockout_s = lockout_s
        self._monotonic = monotonic
        self._command_names = {r.address: r.name.split(".", 1)[1] for r in regmap.block("command").registers}
        self._coil_count = max((coil.address + 1 for coil in regmap.coils), default=0)

        self._lock = threading.Lock()
        self._panels: dict[str, _Panel] = {}
        self._failures: dict[str, int] = {}
        self._locked_until: dict[str, float] = {}
        if self._auto_units:
            log.warning("MODBUS_UNITS bos: birimler pano kimligi sirasiyla otomatik atanir (yalnizca demo)")

    # ------------------------------------------------------------ esleme
    def units(self) -> dict[int, str]:
        with self._lock:
            return dict(self._units)

    def status(self) -> dict[str, Any]:
        """/health icin ozet: eslenen birim, bellekte izlenen pano, yazma durumu, kilitli istemci."""
        now = self._monotonic()
        with self._lock:
            return {
                "units": len(self._units),
                "auto_units": self._auto_units,
                "tracked_panels": len(self._panels),
                "writes_enabled": self._password is not None,
                "locked_clients": sum(1 for until in self._locked_until.values() if until > now),
            }

    def _tracked(self, pano_id: str) -> _Panel | None:
        """Kilit altinda: panonun kaydi; sabit eslemede eslenmemis pano izlenmez."""
        panel = self._panels.get(pano_id)
        if panel is None and (self._auto_units or pano_id in self._fixed_ids):
            panel = self._panels[pano_id] = _Panel()
            if self._auto_units:
                self._units = {unit: pid for unit, pid in enumerate(sorted(self._panels)[:MAX_UNIT], start=1)}
        return panel

    # ------------------------------------------------------------ dinleyiciler
    def on_samples(self, samples: list[Sample]) -> None:
        """Ingest dinleyicisi (yazici thread'i)."""
        with self._lock:
            for sample in samples:
                panel = self._tracked(sample.pano_id)
                if panel is not None:
                    panel.offer(sample.payload, sample.ts, sample.received_at)

    def on_alarm_changes(self, changes: list[Change]) -> None:
        """Alarm servisi dinleyicisi: mandal bitleri ve olay blogu (alarm servisinin kilidi altinda, kisa tutulur)."""
        with self._lock:
            for change in changes:
                if change.kind not in LATCHING_CHANGES:
                    continue
                alarm = change.alarm
                bit = self._encoder.bits.get(alarm.code)
                panel = self._tracked(alarm.pano_id)
                if panel is None or bit is None or bit >= 32:
                    continue
                panel.latched |= 1 << bit
                if change.kind == "raised":
                    panel.events = EventLog((panel.events.count + 1) & 0xFFFF, bit, alarm.raised_at)

    def refresh(self) -> None:
        """Depodan pano listesi, tip ve (bellekte olmayan) son durum. Engelleyicidir; StoreError yukselir."""
        records = self._store.list_panels()
        with self._lock:
            for record in records:
                panel = self._tracked(record.pano_id)
                if panel is None:
                    continue
                panel.pano_type = record.pano_type
                if record.last_rx is not None and (panel.last_rx is None or record.last_rx > panel.last_rx):
                    panel.last_rx = record.last_rx
            missing = [pid for pid in self._units.values() if self._panels.get(pid) is None or self._panels[pid].payload is None]
        for pano_id in missing:
            record = self._store.get_panel(pano_id)
            if record is None or record.payload is None:
                continue
            with self._lock:
                panel = self._tracked(pano_id)
                if panel is not None:
                    panel.pano_type = record.pano_type
                    panel.offer(record.payload, datetime.fromisoformat(record.payload["ts"]), record.last_rx)

    # ------------------------------------------------------------ okuma
    def read_registers(self, unit: int, address: int, count: int, function: int) -> Sequence[int]:
        if function == READ_INPUT_REGISTERS and not self._regmap.mirror_fc03_fc04:
            raise ModbusError(ExceptionCode.ILLEGAL_FUNCTION, "FC04 aynasi haritada kapali")
        pano_id = self._pano_of(unit)
        if self._regmap.block_for(address, count) is None:
            raise ModbusError(ExceptionCode.ILLEGAL_DATA_ADDRESS, f"{address}-{address + count - 1} tek bir harita blogunda degil")
        return self._image(pano_id).registers[address : address + count]

    def read_bits(self, unit: int, address: int, count: int, function: int) -> Sequence[bool]:
        pano_id = self._pano_of(unit)
        if address + count > self._coil_count:
            raise ModbusError(ExceptionCode.ILLEGAL_DATA_ADDRESS, f"coil {address}-{address + count - 1} tanimsiz")
        return self._image(pano_id).coils[address : address + count]

    def _pano_of(self, unit: int) -> str:
        with self._lock:
            pano_id = self._units.get(unit)
        if pano_id is None:
            raise ModbusError(ExceptionCode.GATEWAY_PATH_UNAVAILABLE, f"birim {unit} bir panoya eslenmemis")
        return pano_id

    def _image(self, pano_id: str) -> PanelImage:
        with self._lock:
            panel = self._panels.get(pano_id)
            if panel is None or panel.payload is None:
                raise ModbusError(ExceptionCode.GATEWAY_TARGET_FAILED, f"{pano_id} icin veri yok")
            snapshot_fields = (panel.pano_type, panel.payload, panel.last_rx, panel.latched, panel.events)
        alarms = self._alarms.open_alarms(pano_id)
        if alarms is None:
            raise ModbusError(ExceptionCode.GATEWAY_TARGET_FAILED, "alarm durumu henuz yuklenmedi")
        pano_type, payload, last_rx, latched, events = snapshot_fields
        snapshot = PanelSnapshot(pano_id, pano_type, payload, last_rx, tuple(alarms), latched, events)
        return self._encoder.encode(snapshot, self._clock())

    # ------------------------------------------------------------ yazma
    async def write_registers(self, unit: int, address: int, values: Sequence[int], session: Session) -> None:
        if self._password is None:
            raise ModbusError(ExceptionCode.ILLEGAL_FUNCTION, "yazma kapali (MODBUS_WRITE_PASSWORD bos)")
        pano_id = self._pano_of(unit)
        block = self._regmap.block_for(address, len(values))
        if block is None or block.access != "write":
            log.warning("SCADA yazmasi reddedildi: %s adres %d-%d komut blogu disinda (birim %d)",
                        session.peer, address, address + len(values) - 1, unit)
            raise ModbusError(ExceptionCode.ILLEGAL_DATA_ADDRESS, "yazma yalnizca komut blogunda")
        now = self._monotonic()
        with self._lock:
            locked_until = self._locked_until.get(session.peer)
        if locked_until is not None and now < locked_until:
            raise ModbusError(ExceptionCode.ILLEGAL_FUNCTION, f"{session.peer} yazma kilidinde")

        named: dict[str, int] = {}
        reserved_nonzero = False
        for offset, value in enumerate(values):
            name = self._command_names.get(address + offset)
            if name is None:
                reserved_nonzero |= value != 0
            else:
                named[name] = value
        if "password" in named:
            if named.pop("password") != self._password:
                session.unlocked_until = None
                self._password_failed(session.peer, now)
                raise ModbusError(ExceptionCode.ILLEGAL_DATA_VALUE, "yanlis sifre")
            with self._lock:
                self._failures.pop(session.peer, None)
                self._locked_until.pop(session.peer, None)
            session.unlocked_until = now + self._unlock_s
        elif session.unlocked_until is None or now > session.unlocked_until:
            raise ModbusError(ExceptionCode.ILLEGAL_FUNCTION, "once sifre register'ina yazin")

        ack = named.get("ack_alarm", 0)
        reset = named.get("reset_latch", 0)
        maint = named.get("maint_mode", 0)
        test = named.get("test_alarm", 0)
        if (
            reserved_nonzero
            or not (ack in (0, ACK_ALL) or 1 <= ack <= ACK_MAX_BIT_VALUE)
            or reset not in (0, 1)
            or maint not in (0, MAINT_ON, MAINT_OFF)
            or test not in (0, 1)
        ):
            raise ModbusError(ExceptionCode.ILLEGAL_DATA_VALUE, f"gecersiz komut degeri: {named}")
        edge = ([("maint_mode", {"on": maint == MAINT_ON})] if maint else []) + ([("test_alarm", {})] if test else [])
        if edge and self._sink is None:
            raise ModbusError(ExceptionCode.GATEWAY_TARGET_FAILED, "kenar komut kanali yok")
        alarms = self._alarms.open_alarms(pano_id) if ack else []
        if alarms is None:
            raise ModbusError(ExceptionCode.GATEWAY_TARGET_FAILED, "alarm durumu henuz yuklenmedi")

        for cmd, args in edge:
            if not self._sink(pano_id, cmd, args):
                raise ModbusError(ExceptionCode.GATEWAY_TARGET_FAILED, f"{cmd} kenara iletilemedi")
            log.info("SCADA komutu kenara iletildi: %s %s pano=%s istemci=%s birim=%d", cmd, args, pano_id, session.peer, unit)
        if ack:
            await self._ack(unit, pano_id, ack, alarms, session)
        if reset:
            with self._lock:
                panel = self._panels.get(pano_id)
                if panel is not None:
                    panel.latched = 0
            log.info("SCADA mandal sifirlama: pano=%s istemci=%s birim=%d", pano_id, session.peer, unit)

    def _password_failed(self, peer: str, now: float) -> None:
        with self._lock:
            count = self._failures.get(peer, 0) + 1
            if count >= self._max_failures:
                self._failures.pop(peer, None)
                self._locked_until[peer] = now + self._lockout_s
            else:
                self._failures[peer] = count
        if count >= self._max_failures:
            log.warning("SCADA: %s art arda %d yanlis sifre, yazma %.0f s kilitlendi", peer, count, self._lockout_s)
        else:
            log.warning("SCADA: %s yanlis sifre (%d/%d)", peer, count, self._max_failures)

    async def _ack(self, unit: int, pano_id: str, value: int, alarms: list[Alarm], session: Session) -> None:
        targets = [
            alarm
            for alarm in alarms
            if alarm.state in ACKABLE_STATES and (value == ACK_ALL or self._encoder.bits.get(alarm.code) == value - 1)
        ]
        by = f"SCADA Modbus {session.peer} (birim {unit})"
        for alarm in targets:
            try:
                await asyncio.to_thread(self._alarms.ack, alarm.id, by=by, note="Modbus komut register'i ack_alarm")
            except (AlarmNotFound, AlarmStateConflict):
                continue  # istek ile onay arasinda temizlendi veya baskasi onayladi
        log.info("SCADA onayi: %d alarm, pano=%s, %s", len(targets), pano_id, by)


_UNIT_ENTRY = re.compile(r"^(\d+)\s*=\s*(\S+)$")


def parse_units(spec: str, pano_id_re: re.Pattern[str]) -> dict[int, str]:
    """MODBUS_UNITS: '1=ADM-00001, 2=GDZ-00123' -> {1: 'ADM-00001', 2: 'GDZ-00123'}; bos -> {} (otomatik)."""
    units: dict[int, str] = {}
    for entry in filter(None, (part.strip() for part in spec.split(","))):
        match = _UNIT_ENTRY.match(entry)
        if match is None:
            raise ValueError(f"MODBUS_UNITS girdisi 'birim=pano_id' olmali: {entry!r}")
        unit, pano_id = int(match[1]), match[2]
        if not 1 <= unit <= MAX_UNIT:
            raise ValueError(f"MODBUS_UNITS: birim 1-{MAX_UNIT} araliginda olmali: {entry!r}")
        if not pano_id_re.fullmatch(pano_id):
            raise ValueError(f"MODBUS_UNITS: gecersiz pano_id: {entry!r}")
        if unit in units or pano_id in units.values():
            raise ValueError(f"MODBUS_UNITS: birim veya pano iki kez eslenmis: {entry!r}")
        units[unit] = pano_id
    return units
