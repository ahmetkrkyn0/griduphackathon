"""TB2 Adim 7 — P3 gunluk ozeti ve SYS toplu ozeti (app.alarm_service -> app.notify.dispatcher).

Sozlesme (contracts/alarm-codes.yaml): P3 `daily_digest: true`, SYS `sms: digest_only`. Bu iki oncelik
aninda kimseyi aramaz, gunde bir kez (DIGEST_AT) TEK PARCA SMS ile ozetlenir.

Gercek parcalar: alarmlar uretim yolundan (AlarmManager -> depo) olusur, ozet saati alarm
zamanlayicisinin kendi tick'inden gelir, SMS uretim surucusuyle sanal GSM modeme gercek TCP uzerinden
gider. Ozetlenen alarm `notified` alanindan isaretlenir; yeniden baslatma testi ayni depoyla YENI bir
alarm servisi kurar, yani isaretin kaliciligi kanitlanir.
"""

from __future__ import annotations

import re
from datetime import time

import pytest

from app.alarm_manager import AlarmManager, Condition
from app.alarm_service import AlarmService
from app.api.stream import StreamHub
from app.config import parse_digest_at
from app.notify.dispatcher import NotifyConfig, Notifier
from app.notify.pdu import decode_submit, gsm7_septets
from app.notify.sms_modem import SmsModem
from app.notify.templates import SMS_LIMIT, digest_sms
from fakes import MemoryStore
from helpers import Clock, utc

DIGEST_AT = time(8, 0)
DUE = utc(2026, 9, 13, 8, 0, 0)  # ozet penceresi: [12 Eylul 08:00, 13 Eylul 08:00)
YESTERDAY = utc(2026, 9, 12, 0, 0, 0)
FIELD_TEAM = ("+905550000001", "+905550000002")
PORTAL = "http://gridup.local"

# Pencere icindeki alarmlar: ADM-00001'de ayni kod iki noktada (en cok alarm ureten pano odur),
# ADM-00002'de bir uyari, ADM-00003'te bir sistem alarmi. P2 telefonu zaten aninda caldirir: ozete girmez.
WINDOW = (
    ("ALM-K-WARN", "ADM-00001", "DSYA1_L1", 9),
    ("ALM-K-WARN", "ADM-00001", "DSYA3_L2", 10),
    ("ALM-DEW-WARN", "ADM-00001", None, 11),
    ("ALM-TTL-14D", "ADM-00002", None, 12),
    ("ALM-COMMS-LOST", "ADM-00003", None, 13),
    ("ALM-THR-TERM-ALM", "ADM-00001", "DSYA3_L2", 14),  # P2 — ozette olmamali
)


def sent_sms(modem_log) -> list[tuple[str, str]]:
    if not modem_log.exists():
        return []
    pdus = re.findall(r"SMS-GONDER .* pdu=([0-9A-F]+)", modem_log.read_text(encoding="utf-8"))
    return [(sms.number, sms.text) for sms in map(decode_submit, pdus)]


class DigestSink:
    """Bildirim ag gecidinin yerine gecen dinleyici: Notifier ile ayni imza (cagrilabilir + `digest`)."""

    def __init__(self, accept: bool = True) -> None:
        self.sent: list = []
        self.accept = accept

    def __call__(self, changes) -> None:  # degisiklik dinleyicisi; ozet testlerinde kullanilmaz
        pass

    def digest(self, summary) -> bool:
        self.sent.append(summary)
        return self.accept


class Rig:
    """Depo + alarm servisi; alarmlar uretimdeki gibi alarm yoneticisi uzerinden depoya yazilir."""

    def __init__(self, contracts, *, digest_at: time | None = DIGEST_AT) -> None:
        self.contracts = contracts
        self.store = MemoryStore()
        self.clock = Clock(DUE)
        self.manager = AlarmManager(contracts, first_id=1)
        self.sink = DigestSink()
        self.service = self.restart(digest_at=digest_at)

    def restart(self, *, digest_at: time | None = DIGEST_AT, sink: DigestSink | None = None) -> AlarmService:
        """Yeniden baslatma: ayni depo, sifirdan alarm servisi (bellekteki ozet durumu kaybolur)."""
        self.sink = sink or self.sink
        self.service = AlarmService(self.contracts, self.store, StreamHub(), clock=self.clock, digest_at=digest_at)
        self.service.add_listener(self.sink)
        return self.service

    def raise_alarm(self, code: str, pano_id: str, point: str | None, at) -> None:
        changes = self.manager.observe(pano_id, at, [Condition(code, point)], now=at)
        self.store.save_alarm_changes(changes, at)

    def fill_window(self) -> None:
        for code, pano_id, point, hour in WINDOW:
            self.raise_alarm(code, pano_id, point, YESTERDAY.replace(hour=hour))

    def tick(self, at) -> None:
        self.clock.now = at
        self.service.tick()

    def digested(self) -> dict[str, tuple[str, ...]]:
        return {f"{a.code}@{a.pano_id}": a.notified for a in self.store.alarms.values()}


@pytest.fixture
def rig(contracts) -> Rig:
    return Rig(contracts)


# ------------------------------------------------------------------- icerik
def test_digest_counts_only_the_p3_and_sys_alarms_of_the_window(rig):
    """Sayilar ve etiketler oncelik tablosundan gelir; P2 (anlik yol) ve pencere disi alarm ozete girmez."""
    rig.raise_alarm("ALM-K-WARN", "ADM-00009", None, utc(2026, 9, 11, 9, 0, 0))  # 24 saatten eski
    rig.fill_window()

    rig.tick(DUE)

    [summary] = rig.sink.sent
    assert summary.day == DUE.date()
    assert summary.hours == 24
    assert summary.counts == (("uyari (P3)", 4), ("sistem (SYS)", 1))
    assert (summary.panels, summary.top_pano, summary.top_count) == (3, "ADM-00001", 3)
    assert summary.top_text == rig.contracts.alarm("ALM-K-WARN")["text"]


def test_digest_reaches_the_field_team_as_one_gsm7_sms(rig, contracts, modem_server, modem_log):
    """Uctan uca: alarm zamanlayicisinin tick'i -> ozet -> sanal GSM modem, tek parca (160 septet)."""
    rig.fill_window()
    sms = SmsModem(f"socket://127.0.0.1:{modem_server.port}", timeout_s=3.0)
    notifier = Notifier(
        contracts, NotifyConfig(recipients=FIELD_TEAM, portal_url=PORTAL, retry_base_s=0),
        sms=sms, whatsapp=None, on_delivery=lambda d: pytest.fail("ozet alarm kaydi yazmaz"),
        on_reply=lambda *a: None, clock=lambda: DUE,
    )
    rig.restart(sink=notifier)

    rig.tick(DUE)
    notifier.run_once()
    sms.close()

    delivered = sorted(sent_sms(modem_log))
    text = delivered[0][1]
    assert delivered == [(number, text) for number in FIELD_TEAM]
    assert text.startswith(
        "[GRIDUP OZET 13.09] 24 saat: 4 uyari (P3), 1 sistem (SYS), 3 pano. En cok ADM-00001 (3): Isil direnc"
    )
    assert text.endswith(f"{PORTAL}/alarmlar")
    septets = gsm7_septets(text)  # None = GSM-7 disi karakter, mesaj UCS-2'ye duser ve 70'te bolunur
    assert septets is not None and len(septets) <= SMS_LIMIT


def test_digest_message_stays_in_one_part_for_the_busiest_possible_day(contracts):
    """Sayilar dort haneye, portal adresi uzuna kacsa bile metin tek parcadir: sondan kisalir."""
    from app.alarm_service import Digest

    summary = Digest(
        day=DUE.date(), hours=24, counts=(("uyari (P3)", 9999), ("sistem (SYS)", 9999)), panels=9999,
        top_pano="ADM-99999", top_count=9999, top_text=contracts.alarm("ALM-K-WARN")["text"],
    )

    for portal in (PORTAL, "http://cok-uzun-kurumsal-portal-adresi.sirket.local:8443/gridup", "x" * 300):
        text = digest_sms(summary, portal)
        septets = gsm7_septets(text)
        assert septets is not None and len(septets) <= SMS_LIMIT, (portal, text)
        assert text.startswith("[GRIDUP OZET 13.09] 24 saat: 9999 uyari (P3), 9999 sistem (SYS), 9999 pano.")


# -------------------------------------------------------------- gunde bir kez
def test_digest_is_sent_once_a_day(rig):
    rig.fill_window()

    rig.tick(DUE)
    rig.tick(DUE.replace(second=5))
    rig.tick(DUE.replace(hour=20))

    assert len(rig.sink.sent) == 1


def test_restart_after_the_digest_hour_does_not_send_a_second_digest(rig):
    """Isaret alarms tablosundadir: yeni alarm servisi bellekteki gunu bilmese de ikinci mesaj cikmaz."""
    rig.fill_window()
    rig.tick(DUE)
    assert len(rig.sink.sent) == 1

    rig.restart()
    rig.tick(DUE.replace(minute=10))

    assert len(rig.sink.sent) == 1


def test_digest_waits_for_the_configured_hour(contracts):
    """Ozet saati yapilandirilabilir: 21:30'a ayarli servis 21:29'da hic kimseye yazmaz."""
    rig = Rig(contracts, digest_at=time(21, 30))
    rig.raise_alarm("ALM-K-WARN", "ADM-00001", None, utc(2026, 9, 13, 10, 0, 0))

    rig.tick(utc(2026, 9, 13, 21, 29, 0))
    assert rig.sink.sent == []

    rig.tick(utc(2026, 9, 13, 21, 30, 0))
    assert len(rig.sink.sent) == 1


def test_digest_is_disabled_when_digest_at_is_empty(contracts, monkeypatch):
    """DIGEST_AT="" -> ozet kapali; alarm servisi Settings olmadan kuruldugu icin ayari ortamdan okur."""
    monkeypatch.setenv("DIGEST_AT", "")
    rig = Rig(contracts, digest_at=None)
    rig.fill_window()

    rig.tick(DUE)

    assert rig.sink.sent == []
    assert rig.digested()["ALM-K-WARN@ADM-00001"] == ()


def test_alarms_raised_after_the_digest_hour_go_into_the_next_days_digest(rig):
    rig.fill_window()
    rig.tick(DUE)
    rig.raise_alarm("ALM-DEW-WARN", "ADM-00004", None, DUE.replace(hour=9))

    rig.tick(DUE.replace(day=14))

    assert [summary.counts for summary in rig.sink.sent] == [
        (("uyari (P3)", 4), ("sistem (SYS)", 1)),
        (("uyari (P3)", 1),),
    ]
    assert rig.sink.sent[-1].top_pano == "ADM-00004"


# -------------------------------------------------------------- kalicilik / hata
def test_digest_marks_only_the_alarms_it_reported(rig):
    """Rozet sozlesmedeki kanal adidir (Alarm.notified: sms); P2 alarmi anlik yolun kaydini tasir."""
    rig.fill_window()

    rig.tick(DUE)

    digested = rig.digested()
    assert digested["ALM-K-WARN@ADM-00001"] == ("sms",)
    assert digested["ALM-COMMS-LOST@ADM-00003"] == ("sms",)
    assert digested["ALM-THR-TERM-ALM@ADM-00001"] == ()  # P2: telefonu aninda calar, ozete girmez


def test_digest_that_cannot_be_sent_does_not_mark_the_alarms(contracts):
    """SMS kanali ya da alici yoksa alarm 'gonderildi' gorunmez (konsolda yanlis rozet olmaz)."""
    rig = Rig(contracts)
    rig.restart(sink=DigestSink(accept=False))
    rig.fill_window()

    rig.tick(DUE)

    assert len(rig.sink.sent) == 1
    assert rig.digested()["ALM-K-WARN@ADM-00001"] == ()


def test_digest_is_retried_on_the_next_tick_when_the_store_is_unavailable(rig):
    rig.fill_window()
    rig.tick(DUE.replace(hour=7))  # alarm durumu yuklensin, depo sonra kopsun
    rig.store.unavailable = True

    rig.tick(DUE)
    assert rig.sink.sent == []

    rig.store.unavailable = False
    rig.tick(DUE.replace(minute=5))
    assert len(rig.sink.sent) == 1


# ------------------------------------------------------------------- ayar
@pytest.mark.parametrize(
    ("value", "expected"), [(None, time(8, 0)), ("", None), ("  ", None), ("21:30", time(21, 30)), ("5:00", time(5, 0))]
)
def test_digest_hour_is_read_from_the_environment(value, expected):
    assert parse_digest_at(value) == expected


@pytest.mark.parametrize("value", ["08", "sabah", "25:00", "08:61"])
def test_invalid_digest_hour_is_refused_loudly(value):
    """Yanlis ayarla sessizce calismaz: servis acilirken gurultulu hata verir."""
    with pytest.raises(ValueError):
        parse_digest_at(value)
