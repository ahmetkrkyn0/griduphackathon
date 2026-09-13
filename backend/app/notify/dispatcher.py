"""Bildirim ag gecidi (TB2 Adim 5-7, Kisi B): alarm degisikligi -> kanal isleri -> SMS / WhatsApp / arama.

Kanal kurali kodda degil, contracts/alarm-codes.yaml `priorities` tablosundadir:
    raised / unshelved (notify=True)  sms: true -> SMS, whatsapp: true -> WhatsApp   -> ALERT_RECIPIENTS
    escalated step=call               sesli arama (P1 call_after_min)                -> ALERT_RECIPIENTS
    escalated step=escalate           SMS (+ oncelik izin veriyorsa WhatsApp)         -> ALERT_ESCALATION
    P3 (daily_digest) ve SYS (sms: digest_only) aninda kimseyi aramaz.

Isler kendi thread'inde yurur: alarm servisi ve ingest modemi ya da HTTP'yi beklemez. Gecici hata (modem
kopuk, sebeke reddi, internet yok, 5xx/429) ussel geri cekilmeyle tekrar denenir; kalici hata (yetki,
WhatsApp penceresi disi) bir kez kaydedilir. Her deneme `on_delivery` ile maskeli aliciyla denetim izine
yazilir (KVKK).

Cift yonlu onay: gelen SMS "1 <id>" (gordum) / "2 <id>" (ekip yonlendirildi); kimliksiz "1"/"2" o numaraya
en son giden alarmi onaylar. Yalnizca kayitli alici numaralarindan kabul edilir.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from ..alarm_manager import Alarm, Change
from ..config import Contracts
from .pdu import Sms
from .privacy import mask_number
from .sms_modem import ModemError, SmsModem
from .templates import escalation_sms, fold, sms_alarm, whatsapp_alarm
from .whatsapp import WhatsAppClient, WhatsAppError

log = logging.getLogger("gridup.notify")

REPLY = re.compile(r"\s*([12])(?:\s+(\d+))?\s*")
REPLY_NOTES = {"1": "gordum", "2": "ekip yonlendirildi"}


def _numbers(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def normalize_msisdn(number: str) -> str:
    """Karsilastirma icin: yalnizca rakamlar, ulusal 0 onekli Turkiye numarasi 90 ile."""
    digits = "".join(char for char in number if char.isdigit())
    return "90" + digits[1:] if digits.startswith("0") and len(digits) == 11 else digits


@dataclass(frozen=True)
class NotifyConfig:
    recipients: tuple[str, ...] = ()  # saha / bolge ekibi
    escalation: tuple[str, ...] = ()  # vardiya amiri / ust amir
    portal_url: str = "http://gridup.local"
    call_ring_s: float = 20.0
    retry_max_attempts: int = 5
    retry_base_s: float = 5.0

    @classmethod
    def from_env(cls) -> NotifyConfig:
        return cls(
            recipients=_numbers(os.getenv("ALERT_RECIPIENTS", "")),
            escalation=_numbers(os.getenv("ALERT_ESCALATION", "")),
            portal_url=os.getenv("PORTAL_URL", "http://gridup.local"),
            call_ring_s=float(os.getenv("CALL_RING_S", "20")),
        )


@dataclass(frozen=True)
class Delivery:
    """notifications tablosu satiri: alici maskelidir."""

    alarm_id: int
    channel: str
    recipient: str
    sent_at: datetime
    ok: bool
    detail: str


@dataclass
class _Job:
    alarm: Alarm
    channel: str  # sms | whatsapp | call
    recipient: str
    text: str = ""
    params: tuple[str, ...] = ()
    attempts: int = 0
    not_before: float = field(default_factory=time.monotonic)


class Notifier:
    def __init__(
        self,
        contracts: Contracts,
        config: NotifyConfig,
        *,
        sms: SmsModem | None,
        whatsapp: WhatsAppClient | None,
        on_delivery: Callable[[Delivery], None],
        on_reply: Callable[[int, str, str], None],
        clock: Callable[[], datetime],
    ) -> None:
        self._contracts = contracts
        self._config = config
        self._sms = sms
        self._whatsapp = whatsapp
        self._on_delivery = on_delivery
        self._on_reply = on_reply
        self._clock = clock
        self._authorized = {normalize_msisdn(n) for n in (*config.recipients, *config.escalation)}
        self._last_alarm_for: dict[str, int] = {}
        self._jobs: list[_Job] = []
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------ alarm servisi
    def __call__(self, changes: list[Change]) -> None:
        """Alarm servisi dinleyicisi: yalnizca is kuyruguna ekler, beklemez."""
        jobs = [job for change in changes for job in self._jobs_for(change)]
        if jobs:
            with self._lock:
                self._jobs.extend(jobs)
            self._wake.set()

    def _jobs_for(self, change: Change) -> list[_Job]:
        alarm = change.alarm
        spec = self._contracts.alarm_codes["priorities"][alarm.prio]
        text = (self._contracts.alarm(alarm.code) or {}).get("text", alarm.code)
        jobs: list[_Job] = []
        if change.kind in ("raised", "unshelved") and change.notify:
            if spec.get("sms") is True and self._sms is not None:
                jobs += [_Job(alarm, "sms", n, sms_alarm(alarm, text)) for n in self._config.recipients]
            if spec.get("whatsapp") is True and self._whatsapp is not None:
                jobs += [self._whatsapp_job(alarm, n, text) for n in self._config.recipients]
        elif change.kind == "escalated" and change.step == "call" and self._sms is not None:
            jobs += [_Job(alarm, "call", n) for n in self._config.recipients]
        elif change.kind == "escalated" and change.step == "escalate":
            minutes = int(spec["escalate_after_min"])
            if self._sms is not None:
                jobs += [_Job(alarm, "sms", n, escalation_sms(alarm, text, minutes)) for n in self._config.escalation]
            if spec.get("whatsapp") is True and self._whatsapp is not None:
                jobs += [self._whatsapp_job(alarm, n, text) for n in self._config.escalation]
        return jobs

    def _whatsapp_job(self, alarm: Alarm, number: str, text: str) -> _Job:
        body = whatsapp_alarm(alarm, text, self._config.portal_url)
        return _Job(alarm, "whatsapp", number, body, params=(alarm.prio, alarm.pano_id, fold(text)))

    # ---------------------------------------------------------------- isci
    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="notifier", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 5.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout_s)
            self._thread = None
        if self._sms is not None:
            self._sms.close()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_once(wait_s=0.5)
            except Exception:  # isci thread'i asla olmez
                log.exception("bildirim dongusu hata verdi")
            if self._sms is None:
                self._wake.wait(0.5)
                self._wake.clear()

    def run_once(self, wait_s: float = 0.0) -> None:
        """Vadesi gelen isleri bir kez gonderir, ardindan gelen SMS yanitlarini `wait_s` boyunca okur."""
        now = time.monotonic()
        with self._lock:
            due = [job for job in self._jobs if job.not_before <= now]
            self._jobs = [job for job in self._jobs if job.not_before > now]
        for job in due:
            self._deliver(job)
        if self._sms is not None:
            self._read_replies(wait_s)

    # ------------------------------------------------------------- ic isler
    def _deliver(self, job: _Job) -> None:
        retryable = False
        try:
            if job.channel == "whatsapp":
                self._whatsapp.send(job.recipient, job.text, job.params)
            else:
                self._ensure_modem()
                if job.channel == "sms":
                    self._sms.send_sms(job.recipient, job.text)
                else:
                    self._sms.call(job.recipient, ring_s=self._config.call_ring_s)
            ok, detail = True, "gonderildi"
        except ModemError as exc:
            ok, detail, retryable = False, str(exc), True
            self._sms.close()  # sonraki denemede yeniden baglanir
        except WhatsAppError as exc:
            ok, detail, retryable = False, str(exc), exc.retryable

        masked = mask_number(job.recipient)
        self._on_delivery(Delivery(job.alarm.id, job.channel, masked, self._clock(), ok, detail))
        if ok:
            if job.channel in ("sms", "call"):
                self._last_alarm_for[normalize_msisdn(job.recipient)] = job.alarm.id
            return
        job.attempts += 1
        if retryable and job.attempts < self._config.retry_max_attempts:
            job.not_before = time.monotonic() + self._config.retry_base_s * 2 ** (job.attempts - 1)
            with self._lock:
                self._jobs.append(job)
            log.warning("%s -> %s basarisiz (%d. deneme), tekrar denenecek: %s", job.channel, masked, job.attempts, detail)
        else:
            log.error("%s -> %s gonderilemedi, birakildi: %s", job.channel, masked, detail)

    def _ensure_modem(self) -> None:
        if not self._sms.connected:
            self._sms.connect()

    def _read_replies(self, wait_s: float) -> None:
        try:
            self._ensure_modem()
            messages = self._sms.poll(wait_s)
        except ModemError as exc:
            log.warning("gelen SMS okunamadi: %s", exc)
            self._sms.close()
            return
        for sms in messages:
            self._handle_reply(sms)

    def _handle_reply(self, sms: Sms) -> None:
        sender = normalize_msisdn(sms.number)
        masked = mask_number(sms.number)
        if sender not in self._authorized:
            log.warning("kayitli olmayan numaradan yanit yok sayildi: %s", masked)
            return
        match = REPLY.fullmatch(sms.text)
        target = (int(match[2]) if match[2] else self._last_alarm_for.get(sender)) if match else None
        if target is None:
            log.warning("anlasilamayan SMS yaniti (%s): %r", masked, sms.text)
            return
        try:
            self._on_reply(target, f"sms:{masked}", REPLY_NOTES[match[1]])
        except Exception as exc:  # onaylanmis/temizlenmis alarm: kayit yeterli
            log.warning("SMS yaniti alarm %s icin islenemedi: %s", target, exc)
