"""Bildirim metinleri (TB2 Adim 6, Kisi B).

Kural (rapor 6.6c): yalnizca saha kodu, oncelik, tek satir aciklama ve ic portal baglantisi. Telemetri,
pano adi, konum, kisi adi YOK — WhatsApp sirket disina cikan tek kanaldir (PLAN.md GK4).

SMS tek parca GSM-7 (160 karakter): Turkce karakter UCS-2'ye dusurup siniri 70'e indirmesin ve alarm
metni parcalanmasin diye ASCII'ye katlanir. Yanit kodlari cift yonlu onayi besler (1 = gordum,
2 = ekip yolda).

Gunluk ozet (P3 daily_digest + SYS digest_only) ayni sinira uyar: sigmayan parcalar sondan atilir,
once portal baglantisi, sonra alarm metni kisalir.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..alarm_manager import Alarm
from .pdu import gsm7_septets

if TYPE_CHECKING:
    from ..alarm_service import Digest

SMS_LIMIT = 160
ELLIPSIS = "..."
DIGEST_MIN_BODY = 20  # portal baglantisi govdeye bu kadar yer birakmiyorsa baglanti yazilmaz

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


def digest_sms(summary: Digest, portal_url: str) -> str:
    """Gunluk ozet, tek parca GSM-7: sayilar + en cok alarm ureten pano + portal baglantisi.

    Bas kisim (tarih, sayilar, pano adedi) her zaman yazilir ve dort haneli sayilarla bile 80 septeti
    gecmez (olculdu: 78); kalan yer once govdeye, sonra portal baglantisina gider. Toplam 160 septeti asmaz.
    """
    counts = ", ".join(f"{count} {label}" for label, count in summary.counts)
    head = _gsm7_safe(f"[GRIDUP OZET {summary.day:%d.%m}] {summary.hours} saat: {counts}, {summary.panels} pano. ")
    link = f" {portal_url.rstrip('/')}/alarmlar"
    tail = link if _septets(head) + _septets(link) + DIGEST_MIN_BODY <= SMS_LIMIT else ""
    return _fit(head, f"En cok {summary.top_pano} ({summary.top_count}): {summary.top_text}", tail)


def whatsapp_alarm(alarm: Alarm, text: str, portal_url: str) -> str:
    link = f"{portal_url.rstrip('/')}/alarmlar/{alarm.id}"
    return f"GRIDUP {alarm.prio} alarm: {alarm.pano_id} - {fold(text).rstrip('. ')}. Detay (VPN): {link}"


def telegram_alarm(alarm: Alarm, text: str, portal_url: str) -> str:
    point_val = getattr(alarm, "point", None)
    point = f" (Nokta: <code>{point_val}</code>)" if point_val else ""
    link = f"{portal_url.rstrip('/')}/alarmlar"
    ttl_h = getattr(alarm, "ttl_h", None)
    ttl_info = f"\n⏱ <b>Kalan Ömür (RUL):</b> {ttl_h:.1f} saat" if ttl_h is not None else ""
    advice = getattr(alarm, "advice", None)
    advice_info = f"\n💡 <b>Öneri:</b> {advice}" if advice else ""
    prio = getattr(alarm, "prio", getattr(alarm, "priority", "P2"))
    pano = getattr(alarm, "pano_id", getattr(alarm, "panel_id", "BILINMEYEN"))
    code = getattr(alarm, "code", "UNKNOWN")
    state = getattr(alarm, "state", "ACTIVE")
    prio_icon = "🔴" if prio == "P1" else ("🟠" if prio == "P2" else "🟡")
    return (
        f"{prio_icon} <b>[GRIDUP {prio} ALARM]</b>\n"
        f"<b>Pano:</b> <code>{pano}</code>{point}\n"
        f"<b>Alarm Kodu:</b> <code>{code}</code>\n"
        f"<b>Açıklama:</b> {text}\n"
        f"<b>Durum:</b> {state.upper()}{ttl_info}{advice_info}\n\n"
        f"🔗 <a href='{link}'>GridUp İzleme Konsolunu Aç</a>"
    )

