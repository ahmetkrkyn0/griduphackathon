#!/usr/bin/env python3
"""Sanal GSM modem (TB2 Adim 5, Kisi B) — donanim alinmadan uretim SMS surucusunu uctan uca calistirir.

Gercek bir GSM modemin AT komut arayuzunu (3GPP TS 27.005 / 27.007) TCP uzerinden taklit eder.
Backend'deki surucu (backend/app/notify/sms_modem.py) portu pyserial `serial_for_url` ile acar:

    USB/seri modem:               SMS_DEVICE=/dev/ttyUSB2
    terminal sunucusu arkasinda:  SMS_DEVICE=socket://ser2net-host:7000
    bu sanal modem:               SMS_DEVICE=socket://gsm-modem:7000

Surucu kodu uc durumda da AYNIDIR; modem takildiginda yalnizca bu satir degisir.

Gercek modem gibi davranir: yanki (ATE), PDU/metin modu (AT+CMGF), AT+CMGS uzunlugu tutmayan PDU'yu
+CMS ERROR 304 ile reddeder, gelen SMS'i AT+CNMI=2,2 ile +CMT olarak dogrudan iletir, ATD/ATH arama.

Kayit dosyasi (--log) demodaki "AT komut kaydi"dir: her komut ve yanit, gonderilen her SMS'in PDU
dokumu ve cozulmus metni, arama ve gelen SMS zaman damgasiyla yazilir. Numara maskelenir (KVKK);
PDU numarayi yari-sekizli kodlu tasir. Dosya varsayilan olarak git disi deploy/runtime/ altindadir.

Kullanim:
    python scripts/virtual_gsm_modem.py serve --port 7000 --control-port 7001 --log deploy/runtime/sms-log.txt
    python scripts/virtual_gsm_modem.py inject --control localhost:7001 --sender +905550000001 --text "1 42"
    python scripts/virtual_gsm_modem.py fail --control localhost:7001 --count 1     # sebeke reddi
"""

from __future__ import annotations

import argparse
import socket
import socketserver
import sys
import threading
from datetime import datetime
from pathlib import Path

try:
    from app.notify.pdu import decode_submit, encode_deliver
    from app.notify.privacy import mask_number
except ImportError:  # repo icinden calistirma: backend paketini yola ekle
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    from app.notify.pdu import decode_submit, encode_deliver
    from app.notify.privacy import mask_number

CTRL_Z, ESC = 0x1A, 0x1B
CMS_INVALID_PDU = 304
CMS_UNKNOWN = 500
DEFAULT_LOG = Path(__file__).resolve().parents[1] / "deploy" / "runtime" / "sms-log.txt"


class FileLog:
    """Zaman damgali, satir satir kayit (dosya + standart cikti)."""

    def __init__(self, path: Path | None) -> None:
        self._path = path
        self._lock = threading.Lock()
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, kind: str, text: str) -> None:
        line = f"{datetime.now().astimezone().isoformat(timespec='seconds')} {kind:<10} {text}"
        with self._lock:
            print(line, flush=True)
            if self._path is not None:
                with self._path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")


def _ok(*info: str) -> bytes:
    return "".join(f"\r\n{line}\r\n" for line in info).encode() + b"\r\nOK\r\n"


def _error(code: int | None = None) -> bytes:
    return b"\r\nERROR\r\n" if code is None else f"\r\n+CMS ERROR: {code}\r\n".encode()


class VirtualModem:
    """AT komut motoru; tasima katmanindan bagimsiz (bayt girer, bayt cikar)."""

    def __init__(self, log: FileLog) -> None:
        self.log = log
        self.echo = True
        self.pdu_mode = True
        self.direct_delivery = False
        self._buffer = bytearray()
        self._pending: tuple[str, int | str] | None = None  # ("pdu", uzunluk) | ("text", numara)
        self._message_ref = 0
        self._fail = 0
        self._queued: list[bytes] = []

    def fail_next(self, count: int) -> None:
        self._fail += count
        self.log.write("SEBEKE", f"siradaki {count} gonderim reddedilecek")

    def feed(self, data: bytes) -> bytes:
        self._buffer += data
        out = bytearray()
        while True:
            if self._pending is not None:
                end = next((i for i, b in enumerate(self._buffer) if b in (CTRL_Z, ESC)), -1)
                if end < 0:
                    break
                body, terminator = bytes(self._buffer[:end]), self._buffer[end]
                del self._buffer[: end + 1]
                self.log.write("AT-RX", body.decode(errors="replace") + ("<^Z>" if terminator == CTRL_Z else "<ESC>"))
                out += self._reply(self._finish_send(body, terminator))
                continue
            end = self._buffer.find(b"\r")
            if end < 0:
                break
            # Komut modunda basibos kontrol karakterleri (or. surucunun iptal icin gonderdigi ESC) yok sayilir
            line = "".join(c for c in self._buffer[:end].decode(errors="replace") if c >= " ").strip()
            del self._buffer[: end + 1]
            if not line:
                continue
            self.log.write("AT-RX", line)
            if self.echo:
                out += line.encode() + b"\r"
            out += self._reply(self._command(line))
        return bytes(out)

    def inject_sms(self, sender: str, text: str) -> bytes:
        pdu = encode_deliver(sender, text, datetime.now().astimezone())
        self.log.write("SMS-GELEN", f'no={mask_number(sender)} metin="{text}" pdu={pdu}')
        urc = f"\r\n+CMT: ,{len(pdu) // 2 - 1}\r\n{pdu}\r\n".encode()
        if self.direct_delivery:
            return urc
        self._queued.append(urc)  # host AT+CNMI ile istemeden iletilmez
        return b""

    # ---------------------------------------------------------------- ic isler
    def _reply(self, data: bytes) -> bytes:
        if data:
            self.log.write("AT-TX", " | ".join(part for part in data.decode(errors="replace").split("\r\n") if part))
        return data

    def _command(self, line: str) -> bytes:
        upper = line.upper()
        if upper == "AT":
            return _ok()
        if upper in ("ATE0", "ATE1"):
            self.echo = upper == "ATE1"
            return _ok()
        if upper.startswith("AT+CMEE="):
            return _ok()
        if upper == "AT+CMGF?":
            return _ok(f"+CMGF: {0 if self.pdu_mode else 1}")
        if upper.startswith("AT+CMGF="):
            value = upper.split("=", 1)[1]
            if value not in ("0", "1"):
                return _error()
            self.pdu_mode = value == "0"
            return _ok()
        if upper.startswith("AT+CNMI="):
            params = upper.split("=", 1)[1].split(",")
            self.direct_delivery = len(params) >= 2 and params[0] in ("1", "2") and params[1] == "2"
            queued = b"".join(self._queued) if self.direct_delivery else b""
            if self.direct_delivery:
                self._queued.clear()
            return _ok() + queued
        if upper == "AT+CSQ":
            return _ok("+CSQ: 21,99")
        if upper == "AT+CREG?":
            return _ok("+CREG: 0,1")
        if upper == "AT+CPIN?":
            return _ok("+CPIN: READY")
        if upper in ("ATI", "AT+CGMI", "AT+CGMM"):
            return _ok("GRIDUP Sanal GSM Modem")
        if upper.startswith("AT+CMGS="):
            argument = line.split("=", 1)[1].strip()
            if self.pdu_mode:
                if not argument.isdigit():
                    return _error()
                self._pending = ("pdu", int(argument))
            else:
                self._pending = ("text", argument.strip('"'))
            return b"\r\n> "
        if upper.startswith("ATD"):
            number = line[3:].rstrip(";")
            self.log.write("ARAMA", f"no={mask_number(number)}")
            return _ok()
        if upper in ("ATH", "ATH0"):
            self.log.write("KAPAT", "arama sonlandirildi")
            return _ok()
        return _error()

    def _finish_send(self, body: bytes, terminator: int) -> bytes:
        kind, argument = self._pending
        self._pending = None
        if terminator == ESC:
            return _ok()
        if self._fail:
            self._fail -= 1
            return _error(CMS_UNKNOWN)
        if kind == "pdu":
            text = body.decode(errors="replace").strip()
            try:
                data = bytes.fromhex(text)
                if len(data) - 1 - data[0] != argument:
                    return _error(CMS_INVALID_PDU)
                sms = decode_submit(text)
            except (ValueError, IndexError):
                return _error(CMS_INVALID_PDU)
            parts = f"{sms.concat[2]}/{sms.concat[1]} ref={sms.concat[0]}" if sms.concat else "1/1"
            self.log.write("SMS-GONDER", f'no={mask_number(sms.number)} parca={parts} metin="{sms.text}" pdu={text.upper()}')
        else:
            self.log.write("SMS-GONDER", f'no={mask_number(str(argument))} parca=1/1 metin="{body.decode(errors="replace")}" (metin modu)')
        self._message_ref = (self._message_ref + 1) % 256
        return _ok(f"+CMGS: {self._message_ref}")


class _TcpServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    # Linux'ta hizli yeniden baslatma icin; Windows'ta SO_REUSEADDR kullanimdaki porta baglanmaya izin verir.
    allow_reuse_address = sys.platform != "win32"


class ModemServer:
    """Modem portu (tek host) + denetim portu (gelen SMS enjeksiyonu, sebeke reddi)."""

    def __init__(self, modem: VirtualModem, host: str = "0.0.0.0", port: int = 7000, control_port: int = 7001) -> None:
        self.modem = modem
        self._lock = threading.Lock()
        self._host_socket: socket.socket | None = None
        owner = self

        class HostHandler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                owner._attach(self.request)
                try:
                    while data := self.request.recv(4096):
                        with owner._lock:
                            reply = owner.modem.feed(data)
                            if reply:
                                self.request.sendall(reply)
                except OSError:
                    pass
                finally:
                    owner._detach(self.request)

        class ControlHandler(socketserver.StreamRequestHandler):
            def handle(self) -> None:
                for raw in self.rfile:
                    command, _, rest = raw.decode("utf-8", errors="replace").strip().partition(" ")
                    if command == "SMS":
                        sender, _, text = rest.partition(" ")
                        ok = owner.inject(sender, text)
                        self.wfile.write(b"OK\n" if ok else b"OK kuyrukta\n")
                    elif command == "FAIL" and rest.isdigit():
                        owner.fail_next(int(rest))
                        self.wfile.write(b"OK\n")
                    elif command == "RESET":
                        owner.disconnect_host()
                        self.wfile.write(b"OK\n")
                    else:
                        self.wfile.write(b"ERR komut: SMS <numara> <metin> | FAIL <adet> | RESET\n")

        self._servers = [_TcpServer((host, port), HostHandler), _TcpServer((host, control_port), ControlHandler)]
        self.port = self._servers[0].server_address[1]
        self.control_port = self._servers[1].server_address[1]

    def start(self) -> None:
        for server in self._servers:
            threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.modem.log.write("MODEM", f"dinleniyor: modem :{self.port}, denetim :{self.control_port}")

    def stop(self) -> None:
        for server in self._servers:
            server.shutdown()
            server.server_close()

    def inject(self, sender: str, text: str) -> bool:
        with self._lock:
            urc = self.modem.inject_sms(sender, text)
            if urc and self._host_socket is not None:
                self._host_socket.sendall(urc)
                return True
            return False

    def fail_next(self, count: int) -> None:
        with self._lock:
            self.modem.fail_next(count)

    def disconnect_host(self) -> None:
        """Modem resetini / terminal sunucusu yeniden baslamasini taklit eder: host baglantisi kopar."""
        with self._lock:
            sock, self._host_socket = self._host_socket, None
        if sock is not None:
            self.modem.log.write("MODEM", "baglanti koparildi (reset)")
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def _attach(self, sock: socket.socket) -> None:
        with self._lock:
            self._host_socket = sock
        self.modem.log.write("MODEM", "host baglandi")

    def _detach(self, sock: socket.socket) -> None:
        with self._lock:
            if self._host_socket is sock:
                self._host_socket = None
        self.modem.log.write("MODEM", "host ayrildi")


def _control(address: str, line: str) -> int:
    host, _, port = address.rpartition(":")
    with socket.create_connection((host or "localhost", int(port)), timeout=5) as sock:
        sock.sendall((line + "\n").encode("utf-8"))
        reply = sock.makefile("r", encoding="utf-8").readline().strip()
    print(reply)
    return 0 if reply.startswith("OK") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sanal GSM modem (AT komutlari, PDU modu)")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="modemi calistir")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=7000)
    serve.add_argument("--control-port", type=int, default=7001)
    serve.add_argument("--log", type=Path, default=DEFAULT_LOG)
    inject = commands.add_parser("inject", help="gelen SMS enjekte et (cift yonlu onay)")
    inject.add_argument("--control", default="localhost:7001")
    inject.add_argument("--sender", required=True)
    inject.add_argument("--text", required=True)
    fail = commands.add_parser("fail", help="siradaki gonderimleri sebeke reddiyle dusur")
    fail.add_argument("--control", default="localhost:7001")
    fail.add_argument("--count", type=int, default=1)
    args = parser.parse_args(argv)

    if args.command == "inject":
        return _control(args.control, f"SMS {args.sender} {args.text}")
    if args.command == "fail":
        return _control(args.control, f"FAIL {args.count}")

    server = ModemServer(VirtualModem(FileLog(args.log)), args.host, args.port, args.control_port)
    server.start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
