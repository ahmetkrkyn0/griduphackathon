"""Bildirim metinleri (TB2 Adim 6, Kisi B).

Kural (rapor 6.6c): yalnizca saha kodu, oncelik, tek satir aciklama ve ic portal baglantisi. Telemetri,
pano adi, konum, kisi adi YOK — WhatsApp sirket disina cikan tek kanaldir (PLAN.md GK4).

SMS tek parca GSM-7 (160 karakter): Turkce karakter UCS-2'ye dusurup siniri 70'e indirmesin ve alarm
metni parcalanmasin diye ASCII'ye katlanir. Yanit kodlari cift yonlu onayi besler (1 = gordum,
2 = ekip yolda).
"""

from __future__ import annotations

from ..alarm_manager import Alarm
from .pdu import gsm7_septets

SMS_LIMIT = 160
ELLIPSIS = "..."

_FOLD = str.maketrans(
    {
        "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G", "ı": "i", "İ": "I", "ç": "c", "Ç": "C",
        "ö": "o", "Ö": "O", "ü": "u", "Ü": "U", "â": "a", "Â": "A", "î": "i", "Î": "I", "û": "u", "Û": "U",
        "—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"',
    }
)


def fold(text: str) -> str:
    return text.translate(_FOLD)


def _septets(text: str) -> int:
    """GSM-7 uzunlugu: uzanti tablosu karakterleri ([ ] { } ~ ^ | \\ EUR) iki septet tutar."""
    septets = gsm7_septets(text)
    return len(septets) if septets is not None else 2 * len(text)


def _gsm7_safe(text: str) -> str:
    """Katlamadan sonra GSM-7'de olmayan karakter tum SMS'i UCS-2'ye dusurmesin."""
    return "".join(char if gsm7_septets(char) is not None else "?" for char in fold(text))


def _reply_codes(alarm: Alarm) -> str:
    return f" Yanit: 1 {alarm.id}=gordum 2 {alarm.id}=ekip yolda"


def _fit(head: str, body: str, tail: str) -> str:
    """Govdeyi tek SMS'e (160 septet) sigacak sekilde kisaltir; bas ve kuyruk (yanit kodlari) korunur."""
    body = _gsm7_safe(body).rstrip(". ")
    budget = SMS_LIMIT - _septets(head) - _septets(tail)
    if _septets(body) + 1 <= budget:  # 1 = govde sonundaki nokta
        return head + body + "." + tail
    while body and _septets(body) + len(ELLIPSIS) > budget:
        body = body[:-1]
    return head + body.rstrip() + ELLIPSIS + tail


def sms_alarm(alarm: Alarm, text: str) -> str:
    point = f" {alarm.point}" if alarm.point else ""
    return _fit(f"[GRIDUP {alarm.prio}] {alarm.pano_id}{point}: ", text, _reply_codes(alarm))


def escalation_sms(alarm: Alarm, text: str, minutes: int) -> str:
    head = f"[GRIDUP {alarm.prio} ESKALASYON] {alarm.pano_id}: "
    return _fit(head, f"{fold(text).rstrip('. ')}. {minutes} dk onaysiz", _reply_codes(alarm))


def whatsapp_alarm(alarm: Alarm, text: str, portal_url: str) -> str:
    link = f"{portal_url.rstrip('/')}/alarmlar/{alarm.id}"
    return f"GRIDUP {alarm.prio} alarm: {alarm.pano_id} - {fold(text).rstrip('. ')}. Detay (VPN): {link}"
