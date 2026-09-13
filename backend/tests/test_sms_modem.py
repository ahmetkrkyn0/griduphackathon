"""TB2 Adim 5 — uretim SMS surucusu (app.notify.sms_modem) + sanal GSM modem (scripts/virtual_gsm_modem.py).

Surucu sanal modeme GERCEK bir TCP soketi uzerinden pyserial `socket://` URL'siyle baglanir: veri
merkezinde terminal sunucusu (ser2net vb.) arkasindaki modemin baglanis bicimi budur. USB modemde
yalnizca URL degisir (SMS_DEVICE=/dev/ttyUSB2), surucu kodu ayni kalir.

Sanal modemin kayit dosyasi demodaki "AT komut kaydi"dir; testler dogrudan o dosyayi okur.
"""

from __future__ import annotations

import re
import socket
import threading
import time

import pytest

from app.notify.pdu import decode_submit
from app.notify.sms_modem import ModemError, SmsModem

NUMBER = "+905550000001"
MASKED = "+90******0001"


@pytest.fixture
def server(modem_server):
    return modem_server


@pytest.fixture
def log_path(modem_log):
    return modem_log


@pytest.fixture
def modem(server):
    driver = SmsModem(f"socket://127.0.0.1:{server.port}", timeout_s=3.0)
    driver.connect()
    yield driver
    driver.close()


def sent_pdus(log_path) -> list[str]:
    return re.findall(r"SMS-GONDER .* pdu=([0-9A-F]+)", log_path.read_text(encoding="utf-8"))


def test_sms_is_sent_in_pdu_mode_and_logged_with_its_pdu(modem, log_path):
    references = modem.send_sms(NUMBER, "[GRIDUP P2] ADM-00001 GIRIS_L2: test")

    assert references == [1]  # modemin +CMGS yanitindaki mesaj referansi
    log = log_path.read_text(encoding="utf-8")
    assert "AT+CMGF=0" in log
    [pdu] = sent_pdus(log_path)
    decoded = decode_submit(pdu)
    assert (decoded.number, decoded.text) == (NUMBER, "[GRIDUP P2] ADM-00001 GIRIS_L2: test")
    assert f"no={MASKED}" in log
    assert NUMBER not in log  # KVKK: kayitta acik numara yok (PDU yari-sekizli kodludur)


def test_long_turkish_text_is_sent_as_concatenated_parts(modem, log_path):
    text = "Isıl direnç indeksi yükseldi; bağlantı gevşek olabilir. " * 2  # UCS-2, 67 karakterlik parcalar

    references = modem.send_sms(NUMBER, text)

    decoded = [decode_submit(pdu) for pdu in sent_pdus(log_path)]
    assert len(references) == len(decoded) == 2
    assert [d.concat[1:] for d in decoded] == [(2, 1), (2, 2)]
    assert "".join(d.text for d in decoded) == text


def test_rejected_send_raises_and_the_next_send_succeeds(modem, server):
    server.fail_next(1)

    with pytest.raises(ModemError, match="CMS ERROR"):
        modem.send_sms(NUMBER, "ilk deneme")
    assert len(modem.send_sms(NUMBER, "ikinci deneme")) == 1


def test_incoming_sms_injected_from_the_control_port_reaches_the_driver(modem, server, vgm):
    exit_code = vgm.main(["inject", "--control", f"127.0.0.1:{server.control_port}", "--sender", NUMBER, "--text", "1 42"])

    assert exit_code == 0
    [sms] = modem.poll(timeout_s=2.0)
    assert (sms.number, sms.text) == (NUMBER, "1 42")


def test_incoming_sms_arriving_during_a_send_is_not_lost(modem, server):
    server.inject(NUMBER, "2 42")
    time.sleep(0.2)  # URC, surucu AT+CMGS yanitini beklerken okunur

    modem.send_sms(NUMBER, "alarm")

    assert [(s.number, s.text) for s in modem.poll()] == [(NUMBER, "2 42")]


def test_connect_cancels_a_half_finished_sms_left_by_a_dropped_session(server, log_path):
    """Onceki oturum AT+CMGS yazip PDU'yu yazamadan koptu: modem hala '> ' isteminde bekliyor.
    Yeni oturumun AT komutlari SMS govdesi sanilmamali (ser2net yeniden baslamasi, kablo cikmasi)."""
    with socket.create_connection(("127.0.0.1", server.port), timeout=3) as dropped:
        dropped.sendall(b"ATE0\rAT+CMGF=0\rAT+CMGS=23\r")
        received = b""
        while b"> " not in received:
            received += dropped.recv(1024)

    driver = SmsModem(f"socket://127.0.0.1:{server.port}", timeout_s=2.0)
    try:
        driver.connect()
        assert driver.send_sms(NUMBER, "yeniden baglandi") != []
    finally:
        driver.close()
    assert [decode_submit(pdu).text for pdu in sent_pdus(log_path)] == ["yeniden baglandi"]


def test_call_is_dialled_and_hung_up(modem, log_path):
    modem.call("+905550000009", ring_s=0)

    log = log_path.read_text(encoding="utf-8")
    assert re.search(r"ARAMA\s+no=\+90\*{6}0009", log)
    assert re.search(r"AT-RX\s+ATH", log)


def test_unreachable_modem_raises_instead_of_hanging():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
    driver = SmsModem(f"socket://127.0.0.1:{free_port}", timeout_s=1.0)

    with pytest.raises(ModemError):
        driver.connect()


def test_modem_that_accepts_the_connection_but_never_answers_times_out():
    """Takilmis modem bildirim thread'ini sonsuza dek kilitlememeli. connect() ayri thread'de kosar:
    zaman asimi bozulursa test paketi kilitlenmez, bu test hizla duser."""
    outcome: list[BaseException | None] = []

    def attempt(url: str) -> None:
        driver = SmsModem(url, timeout_s=0.5)
        try:
            driver.connect()
            outcome.append(None)
        except BaseException as exc:  # noqa: BLE001 - sonucu ana thread degerlendirir
            outcome.append(exc)
        finally:
            driver.close()

    with socket.socket() as silent:
        silent.bind(("127.0.0.1", 0))
        silent.listen(1)
        worker = threading.Thread(target=attempt, args=(f"socket://127.0.0.1:{silent.getsockname()[1]}",), daemon=True)
        worker.start()
        worker.join(timeout=5.0)

    assert not worker.is_alive(), "surucu yanit vermeyen modemde kilitlendi"
    [error] = outcome
    assert isinstance(error, ModemError) and "zamaninda" in str(error)


class PromptCheckingPort:
    """pyserial port cifti: AT+CMGS'e '> ' istemiyle yanit verir, istem OKUNMADAN yazilan PDU'yu ihlal sayar.

    TCP uzerindeki sanal modem bu sirayi belirlenimci sinayamaz (baytlar sirayla islenir); gercek modem
    ise istemden once gelen karakterleri dusurebilir. Siranin kendisi sozlesme oldugu icin burada cift var.
    """

    def __init__(self) -> None:
        self.timeout = 0.05
        self.violations: list[str] = []
        self._outgoing = bytearray()
        self._prompt_read = False

    @property
    def in_waiting(self) -> int:
        return len(self._outgoing)

    def write(self, data: bytes) -> int:
        text = data.decode("ascii")
        if text.startswith("AT+CMGS="):
            self._prompt_read = False
            self._outgoing += b"\r\n> "
        elif text.endswith("\x1a"):
            if not self._prompt_read:
                self.violations.append(text)
            self._outgoing += b"\r\n+CMGS: 7\r\n\r\nOK\r\n"
        else:
            self._outgoing += b"\r\nOK\r\n"
        return len(data)

    def read(self, size: int = 1) -> bytes:
        chunk = bytes(self._outgoing[:size])
        del self._outgoing[:size]
        if b">" in chunk:
            self._prompt_read = True
        return chunk

    def close(self) -> None:
        pass


def test_pdu_is_written_only_after_the_prompt_has_been_read():
    port = PromptCheckingPort()
    driver = SmsModem("sahte://", open_port=lambda url, **options: port)
    driver.connect()

    assert driver.send_sms(NUMBER, "Isil direnc indeksi yukseldi " * 8) == [7, 7]  # iki parca

    assert port.violations == []


def test_virtual_modem_rejects_a_pdu_whose_length_does_not_match(server):
    """Gercek modem gibi: AT+CMGS uzunlugu tutmazsa +CMS ERROR 304 (surucu hesabini gercekten sinar)."""
    with socket.create_connection(("127.0.0.1", server.port), timeout=3) as raw:
        raw.sendall(b"ATE0\rAT+CMGF=0\rAT+CMGS=5\r")
        received = b""
        while b"> " not in received:
            received += raw.recv(1024)
        raw.sendall(b"0011000B916407281553F80000AA0AE8329BFD4697D9EC37\x1a")
        while b"ERROR" not in received and b"+CMGS" not in received:
            received += raw.recv(1024)

    assert b"+CMS ERROR: 304" in received
