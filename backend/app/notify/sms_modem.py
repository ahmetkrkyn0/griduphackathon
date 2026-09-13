"""GSM modem SMS surucusu (TB2 Adim 5, Kisi B) — URETIM surucusudur.

AT komutlari (3GPP TS 27.005/27.007), PDU modu. Port pyserial `serial_for_url` ile acilir:
    SMS_DEVICE=/dev/ttyUSB2                 USB/seri GSM modem
    SMS_DEVICE=socket://ser2net-host:7000   veri merkezinde terminal sunucusu arkasindaki modem
    SMS_DEVICE=socket://gsm-modem:7000      scripts/virtual_gsm_modem.py (donanimsiz demo)
Surucu kodu uc durumda da aynidir.

Tek thread'den kullanilir (bildirim isci thread'i). Komut yanitini beklerken gelen istenmeyen sonuc
kodlari (URC: +CMT gelen SMS) kaybolmaz, tamponlanir ve `poll()` ile teslim edilir.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from itertools import count

import serial

from .pdu import Sms, decode_deliver, encode_submit

INIT_COMMANDS = ("AT", "ATE0", "AT+CMEE=1", "AT+CMGF=0", "AT+CNMI=2,2,0,0,0")
FINAL_ERRORS = ("ERROR", "+CMS ERROR", "+CME ERROR", "NO CARRIER", "BUSY", "NO ANSWER", "NO DIALTONE")
URC_PREFIXES = ("RING", "+CMTI:", "+CREG:", "+CIEV:")
PROMPT = "> "
CR, LF, CTRL_Z = "\r", "\n", "\x1a"
READ_SLICE_S = 0.05


class ModemError(RuntimeError):
    """Modem erisilemiyor, yanit vermedi ya da komutu reddetti."""


class SmsModem:
    def __init__(
        self,
        url: str,
        *,
        baudrate: int = 115200,
        timeout_s: float = 10.0,
        open_port: Callable[..., serial.SerialBase] = serial.serial_for_url,
    ) -> None:
        self._url = url
        self._baudrate = baudrate
        self._timeout_s = timeout_s
        self._open_port = open_port
        self._port: serial.SerialBase | None = None
        self._buffer = bytearray()
        self._incoming: list[Sms] = []
        self._references = count(1)

    # ------------------------------------------------------------- yasam
    def connect(self) -> None:
        self.close()
        try:
            self._port = self._open_port(self._url, baudrate=self._baudrate, timeout=READ_SLICE_S)
        except (serial.SerialException, OSError, ValueError) as exc:
            raise ModemError(f"modem acilamadi ({self._url}): {exc}") from exc
        for command in INIT_COMMANDS:
            self._command(command)

    def close(self) -> None:
        if self._port is not None:
            try:
                self._port.close()
            finally:
                self._port = None
                self._buffer.clear()

    @property
    def connected(self) -> bool:
        return self._port is not None

    # ---------------------------------------------------------- islemler
    def send_sms(self, number: str, text: str) -> list[int]:
        """Metni gerekirse birlesik parcalar halinde gonderir; parca basina modem mesaj referansi."""
        reference = next(self._references) & 0xFF
        message_refs = []
        for part in encode_submit(number, text, reference=reference):
            command = f"AT+CMGS={part.tpdu_length}"
            self._write(command + CR)
            self._wait_prompt(command)
            self._write(part.pdu + CTRL_Z)
            info = self._collect(command)
            message_refs.append(next((int(line.split(":")[1]) for line in info if line.startswith("+CMGS:")), -1))
        return message_refs

    def call(self, number: str, *, ring_s: float = 20.0) -> None:
        """Sesli arama (P1 eskalasyonu): ceviri, `ring_s` saniye caldirir, kapatir."""
        self._command(f"ATD{number};")
        deadline = time.monotonic() + ring_s
        while (remaining := deadline - time.monotonic()) > 0:
            self._drain(min(remaining, 0.5))
        self._command("ATH")

    def poll(self, timeout_s: float = 0.0) -> list[Sms]:
        """Tamponlanan ve `timeout_s` icinde gelen SMS'leri teslim eder."""
        if self._port is not None:
            deadline = time.monotonic() + timeout_s
            while True:
                self._drain(min(max(deadline - time.monotonic(), 0.0), READ_SLICE_S))
                if self._incoming or time.monotonic() >= deadline:
                    break
        received, self._incoming = self._incoming, []
        return received

    # ------------------------------------------------------------- ic isler
    def _command(self, command: str) -> list[str]:
        self._write(command + CR)
        return self._collect(command)

    def _write(self, text: str) -> None:
        if self._port is None:
            raise ModemError("modem bagli degil")
        try:
            self._port.write(text.encode("ascii"))
        except (serial.SerialException, OSError) as exc:
            raise ModemError(f"modeme yazilamadi: {exc}") from exc

    def _collect(self, command: str) -> list[str]:
        """Son sonuc koduna (OK / hata) kadar bilgi satirlari; yanki ve istem ayiklanir."""
        deadline = time.monotonic() + self._timeout_s
        info: list[str] = []
        while True:
            line = self._next_line(deadline)
            if line in (command, PROMPT):
                continue
            if line == "OK":
                return info
            if line.startswith(FINAL_ERRORS):
                raise ModemError(f"{command}: {line}")
            info.append(line)

    def _wait_prompt(self, command: str) -> None:
        deadline = time.monotonic() + self._timeout_s
        while (line := self._next_line(deadline)) != PROMPT:
            if line.startswith(FINAL_ERRORS):
                raise ModemError(f"{command}: {line}")

    def _next_line(self, deadline: float) -> str:
        """Bir sonraki anlamli satir. Gelen SMS (+CMT basligi + PDU satiri) burada tamponlanir."""
        while True:
            line = self._pop_line()
            if line is None:
                self._fill(deadline)
            elif line.startswith("+CMT:"):
                self._incoming.append(decode_deliver(self._next_raw_line(deadline)))
            elif line and not line.startswith(URC_PREFIXES):
                return line

    def _next_raw_line(self, deadline: float) -> str:
        while (line := self._pop_line()) is None:
            self._fill(deadline)
        return line

    def _drain(self, wait_s: float) -> None:
        """Komut beklenmezken (poll, calma suresi) gelenleri okur; gelen SMS'ler tamponlanir."""
        self._read_available(wait_s)
        while (line := self._pop_line()) is not None:
            if line.startswith("+CMT:"):
                self._incoming.append(decode_deliver(self._next_raw_line(time.monotonic() + self._timeout_s)))

    def _pop_line(self) -> str | None:
        """Tampondan tamamlanmis bir satir; '> ' istemi satir sonu beklemeden tek basina doner."""
        while self._buffer[:1] in (CR.encode(), LF.encode()):
            del self._buffer[:1]
        if self._buffer.startswith(PROMPT.encode()):
            del self._buffer[: len(PROMPT)]
            return PROMPT
        end = self._buffer.find(LF.encode())
        if end < 0:
            return None
        line = bytes(self._buffer[:end]).decode("ascii", errors="replace").strip()
        del self._buffer[: end + 1]
        return line

    def _fill(self, deadline: float) -> None:
        if time.monotonic() > deadline:
            raise ModemError("modem zamaninda yanit vermedi")
        self._read_available(READ_SLICE_S)

    def _read_available(self, wait_s: float) -> None:
        if self._port is None:
            raise ModemError("modem bagli degil")
        try:
            self._port.timeout = max(wait_s, 0.001)
            self._buffer += self._port.read(max(1, self._port.in_waiting))
        except (serial.SerialException, OSError) as exc:
            raise ModemError(f"modemden okunamadi: {exc}") from exc
