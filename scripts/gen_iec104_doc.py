#!/usr/bin/env python3
"""docs/04-iec104-haritasi.md tablolarini sozlesme + IEC 104 kodundan uretir (Kisi B, TB3 Adim 8).

Anlati elle yazilir; nokta plani, istasyon parametreleri ve zamanlayicilar isaretli bloklar arasinda uretilir ve ELLE DUZENLENMEZ
(PLAN.md kural 10). IOA plani backend/app/scada/iec104_points.py, zamanlayicilar iec104_server.py, alarm metin ve oncelikleri
contracts/alarm-codes.yaml'dan gelir.

    backend/.venv/Scripts/python scripts/gen_iec104_doc.py            # yeniler
    backend/.venv/Scripts/python scripts/gen_iec104_doc.py --check    # guncel degilse 1 ile cikar
"""

from __future__ import annotations

import argparse
import dataclasses
import inspect
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import load_contracts  # noqa: E402
from app.scada import iec104, iec104_points, iec104_server  # noqa: E402
from app.scada.encoder import PanelEncoder, source_docs  # noqa: E402
from app.scada.map_loader import load_map  # noqa: E402

DOC = ROOT / "docs" / "04-iec104-haritasi.md"


def _load():
    contracts = load_contracts(ROOT / "contracts")
    regmap = load_map(ROOT / "contracts" / "modbus-map.yaml")
    catalog = iec104_points.PointCatalog(regmap, PanelEncoder(regmap, contracts))
    return contracts, regmap, catalog


def _number(value: float) -> str:
    return format(value, "g")


def measured_rows() -> list[dict[str, Any]]:
    _, regmap, catalog = _load()
    sources = source_docs(regmap)
    rows = []
    for point in catalog.measured:
        register = regmap.register(point.name)
        rows.append({
            "ioa": point.ioa,
            "ad": point.name,
            "pdu": point.address,
            "birim": register.unit or "",
            "olcek": _number(point.scale),
            "olu_bant": _number(point.deadband),
            "gecersiz": f"ham 0x{point.na:04X}" if point.na is not None else "-",
            "kaynak": sources[point.name],
        })
    return rows


def single_rows() -> list[dict[str, Any]]:
    contracts, regmap, catalog = _load()
    sources = source_docs(regmap)
    rows = []
    for point in catalog.single:
        if point.kind == "alarm":
            alarm = contracts.alarm(point.name) or {}
            rows.append({"ioa": point.ioa, "ad": point.name, "tur": f"alarm biti {point.index}",
                         "oncelik": alarm.get("prio", "-"), "aciklama": alarm.get("text", "")})
        else:
            rows.append({"ioa": point.ioa, "ad": point.name, "tur": f"coil {point.index}", "oncelik": "-",
                         "aciklama": sources[f"coils.{point.name}"]})
    return rows


def _cell(value: Any) -> str:
    text = "-" if value in (None, "") else str(value)
    return text.replace("|", "\\|")


def table_station() -> str:
    timing = iec104_server.Timing()
    return "\n".join([
        "| Parametre | Deger |",
        "|---|---|",
        "| Rol | Kontrollu istasyon (slave), TCP 2404 |",
        "| Ortak adres (CA) | Modbus birim numarasi (`MODBUS_UNITS` veya otomatik) |",
        f"| Yayin adresi | `0x{iec104.BROADCAST_COMMON_ADDRESS:04X}` = tum istasyonlar; her istasyon KENDI ortak adresiyle cevaplar "
        "(IEC 60870-5-101/104 7.2.4); hic istasyon yoksa hemen ret (COT 46) |",
        "| IOA | 3 bayt |",
        f"| k / w | {timing.k} / {timing.w} |",
        f"| t1 / t2 / t3 | {_number(timing.t1)} s / {_number(timing.t2)} s / {_number(timing.t3)} s |",
        f"| Kendiliginden gonderim taramasi | {_number(timing.spontaneous)} s |",
        f"| Nesne / ASDU | zamansiz en cok {iec104_server.MONITOR_OBJECTS}, zaman etiketli en cok {iec104_server.TIME_TAGGED_OBJECTS} |",
    ])


def table_asdu() -> str:
    rows = [
        (iec104.M_ME_NC_1, "`M_ME_NC_1`", "izleme", "Olculen deger, kisa kayan nokta + QDS", "20 (sorgulama)"),
        (iec104.M_ME_TF_1, "`M_ME_TF_1`", "izleme", "Olculen deger + CP56Time2a (UTC)", "3 (kendiliginden)"),
        (iec104.M_SP_NA_1, "`M_SP_NA_1`", "izleme", "Tek nokta + SIQ", "20"),
        (iec104.M_SP_TB_1, "`M_SP_TB_1`", "izleme", "Tek nokta + CP56Time2a (UTC)", "3"),
        (iec104.C_IC_NA_1, "`C_IC_NA_1`", "komut", "Istasyon sorgulamasi (QOI 20): ACTCON -> veriler -> ACTTERM", "6 -> 7, 20, 10"),
        (iec104.C_CS_NA_1, "`C_CS_NA_1`", "komut", "Saat senkronu: istasyon saatiyle ACTCON (saat disaridan degistirilmez)", "6 -> 7"),
        (f"{iec104.C_SC_NA_1}, {iec104.C_DC_NA_1}, ...", "`C_SC_NA_1`, `C_DC_NA_1` ve diger tum tipler", "komut",
         "**Reddedilir** (istasyon salt okunur, GK6)", f"-> {iec104.COT_UNKNOWN_TYPE} + P/N"),
    ]
    lines = ["| Tip | Ad | Yon | Anlami | COT |", "|---|---|---|---|---|"]
    lines += [f"| {type_id} | {name} | {direction} | {meaning} | {cot} |" for type_id, name, direction, meaning, cot in rows]
    lines.append(f"| - | Bilinmeyen ortak adres | - | Reddedilir | -> {iec104.COT_UNKNOWN_COMMON_ADDRESS} + P/N |")
    lines.append(f"| - | Desteklenmeyen iletim nedeni | - | Reddedilir | -> {iec104.COT_UNKNOWN_CAUSE} + P/N |")
    return "\n".join(lines)


def table_measured() -> str:
    lines = ["| IOA | Ad | Modbus PDU | Birim | Olcek | Olu bant | IV (gecersiz) kosulu | Merkez kaynagi |", "|---|---|---|---|---|---|---|---|"]
    for row in measured_rows():
        lines.append(f"| {row['ioa']} | `{row['ad']}` | {row['pdu']} | {_cell(row['birim'])} | {row['olcek']} | {row['olu_bant']} "
                     f"| {row['gecersiz']} | {_cell(row['kaynak'])} |")
    return "\n".join(lines)


def table_single() -> str:
    lines = ["| IOA | Ad | Tur | Oncelik | Aciklama |", "|---|---|---|---|---|"]
    for row in single_rows():
        lines.append(f"| {row['ioa']} | `{row['ad']}` | {row['tur']} | {row['oncelik']} | {_cell(row['aciklama'])} |")
    return "\n".join(lines)


# ------------------------------------------------------------------ birlikte calisabilirlik (§7)
# IEC 60870-5-104 uygulayan her urun standardin ek formundaki BOLUM BASLIKLARIYLA bir birlikte calisabilirlik listesi
# yayimlar. Basliklar standarttan, satirlarin tamami bu istasyonun kodundan gelir; hicbir deger elle yazilmaz.
SCADA_DIR = ROOT / "backend" / "app" / "scada"
YES, NO = "X", "-"
PROBE_CA, PROBE_IOA, PROBE_ORIGINATOR = 0xBEEF, 0xABCDEF, 0x5A  # alan uzunluklarini olcmek icin sahte ASDU

TYPE_NOTES = {
    "M_SP_NA_1": "Tek nokta + SIQ; sorgulama cevabi",
    "M_ME_NC_1": "Olculen deger, kisa kayan nokta + QDS; sorgulama cevabi",
    "M_SP_TB_1": "Tek nokta + CP56Time2a (UTC); kendiliginden",
    "M_ME_TF_1": "Olculen deger + CP56Time2a (UTC); kendiliginden",
    "M_EI_NA_1": "Baslatma sonu: kodekte tanimli, istasyon GONDERMEZ (oturum STARTDT ile baslar)",
    "C_IC_NA_1": "Istasyon sorgulamasi, yalnizca QOI 20 (grup sorgulamasi yok)",
    "C_CS_NA_1": "Saat senkronu: istasyon saatiyle ACTCON, merkez saati degismez",
    "C_SC_NA_1": "Tek komut: cozulur, calistirilmaz (istasyon salt okunur, GK6)",
    "C_DC_NA_1": "Cift komut: cozulur, calistirilmaz (istasyon salt okunur, GK6)",
}

# Standardin "temel uygulama fonksiyonlari" basliklari; her satirin isareti kodun kendisinden hesaplanir.
FUNCTION_ROWS = (
    ("Istasyon baslatma (baslatma sonu bildirimi)", "M_EI_NA_1", "type"),
    ("Istasyon sorgulamasi", "C_IC_NA_1", "type"),
    ("Saat senkronizasyonu", "C_CS_NA_1", "type"),
    ("Komut iletimi", "C_SC_NA_1", "type"),
    ("Sayac (integrated totals) sorgulamasi", "C_CI_NA_1", "type"),
    ("Parametre yukleme", "P_ME_NA_1", "type"),
    ("Test yordami (test komutu)", "C_TS_NA_1", "type"),
    ("Dosya transferi", "F_FR_NA_1", "type"),
    ("Nokta bazli okuma (okuma yordami)", "C_RD_NA_1", "type"),
    ("Kendiliginden gonderim", "_spontaneous", "method"),
    ("Baglanti canliligi denetimi (TESTFR)", "_timers", "method"),
)

FUNCTION_NOTES = {
    "M_EI_NA_1": "tip tanimli ama hicbir yerde uretilmiyor; baslatma yerine STARTDT/STOPDT kullanilir",
    "C_IC_NA_1": "ACTCON -> tum noktalar (COT 20) -> ACTTERM; yayin adresinde istasyon basina ayri",
    "C_CS_NA_1": "yalnizca onay: NTP disindan saat oynatilmaz",
    "C_SC_NA_1": "tum kontrol ASDU'lari reddedilir; koruma cihazina yol yoktur (GK6)",
    "C_CI_NA_1": "sayac nesnesi sunulmuyor, sorgulanacak sayac yok",
    "P_ME_NA_1": "esik/parametre uzaktan yazilmaz; esikler contracts/ dizininden gelir",
    "C_TS_NA_1": "canlilik denetimi APCI duzeyinde TESTFR ile yapilir",
    "F_FR_NA_1": "kayit/dosya aktarimi yok; olay kaydi REST ucundan alinir",
    "C_RD_NA_1": "nokta bazli okuma yok; bu yuzden bilinmeyen IOA reddi (COT 47) hic kullanilmaz",
    "_spontaneous": "olu bant asilinca M_ME_TF_1, tek nokta degisince M_SP_TB_1",
    "_timers": "t3 sonunda TESTFR gonderilir, t1 icinde cevap gelmezse baglanti kapanir",
}

# Tip -> istasyonun o tiple kullandigi iletim nedenleri. Nedenler kodun sabitlerinden okunur.
COT_COLUMNS = ("COT_SPONTANEOUS", "COT_ACTIVATION", "COT_ACTIVATION_CON", "COT_ACTIVATION_TERM", "COT_INTERROGATED",
               "COT_UNKNOWN_TYPE", "COT_UNKNOWN_CAUSE", "COT_UNKNOWN_COMMON_ADDRESS")
COT_LABELS = {"COT_SPONTANEOUS": "kendiliginden", "COT_ACTIVATION": "etkinlestirme", "COT_ACTIVATION_CON": "etkinlestirme onayi",
              "COT_ACTIVATION_TERM": "etkinlestirme sonu", "COT_INTERROGATED": "sorgulama cevabi",
              "COT_UNKNOWN_TYPE": "bilinmeyen tip", "COT_UNKNOWN_CAUSE": "bilinmeyen neden",
              "COT_UNKNOWN_COMMON_ADDRESS": "bilinmeyen ortak adres"}
COT_MATRIX = {
    "M_SP_NA_1": ("COT_INTERROGATED",),
    "M_ME_NC_1": ("COT_INTERROGATED",),
    "M_SP_TB_1": ("COT_SPONTANEOUS",),
    "M_ME_TF_1": ("COT_SPONTANEOUS",),
    "C_IC_NA_1": ("COT_ACTIVATION", "COT_ACTIVATION_CON", "COT_ACTIVATION_TERM", "COT_UNKNOWN_CAUSE",
                  "COT_UNKNOWN_COMMON_ADDRESS"),
    "C_CS_NA_1": ("COT_ACTIVATION", "COT_ACTIVATION_CON", "COT_UNKNOWN_CAUSE", "COT_UNKNOWN_COMMON_ADDRESS"),
}


def field_widths() -> dict[str, int]:
    """ASDU alan uzunluklari: sabitten degil, kodlayicinin urettigi bayt dizisinden olculur."""
    probe = iec104.encode_asdu(iec104.Asdu(iec104.M_SP_NA_1, iec104.COT_INTERROGATED, PROBE_CA,
                                           ((PROBE_IOA, b"\x00"),), originator=PROBE_ORIGINATOR))
    if probe[0] != iec104.M_SP_NA_1 or probe[1] != 1 or probe[3] != PROBE_ORIGINATOR:
        raise SystemExit("ASDU basligi beklenen bicimde degil: tip | VSQ | neden | kaynak adres")
    at_ca = probe.index(PROBE_CA.to_bytes(2, "little"))
    at_ioa = probe.index(PROBE_IOA.to_bytes(3, "little"))
    return {"tip": 1, "vsq": 1, "cot": at_ca - 2, "ca": at_ioa - at_ca,
            "ioa": len(probe) - at_ioa - iec104.ELEMENT_SIZE[iec104.M_SP_NA_1]}


def type_names() -> dict[int, str]:
    return {value: name for name, value in vars(iec104).items() if re.fullmatch(r"[MC]_[A-Z]{2}_[A-Z]{2}_1", name)}


def served_types() -> tuple[int, ...]:
    """Uygulama katmaninda islev baglanmis tipler: sunucunun _on_asdu icinde karsilastirdigi sabitler."""
    source = inspect.getsource(iec104_server._Connection._on_asdu)
    return tuple(getattr(iec104, name) for name in re.findall(r"type_id == iec104\.(\w+)", source))


def emitted_types() -> tuple[int, ...]:
    """Izleme yonunde uretilen tipler: nokta katalogu + kendiliginden gonderimin zaman etiketli karsiliklari."""
    _, _, catalog = _load()
    types = {value.type_id for value in catalog.values(None)}
    types |= {getattr(iec104, name) for name in re.findall(r"iec104\.(M_\w+)", inspect.getsource(iec104_server._Connection._spontaneous))}
    return tuple(sorted(types))


def unused_constants() -> tuple[str, ...]:
    """Kodekte tanimli olup SCADA modullerinin hicbirinde gecmeyen tip/neden sabitleri."""
    others = [path.read_text(encoding="utf-8") for path in sorted(SCADA_DIR.glob("*.py")) if path.name != "iec104.py"]
    names = [name for name in vars(iec104) if re.fullmatch(r"([MC]_[A-Z]{2}_[A-Z]{2}_1|COT_[A-Z_]+)", name)]
    return tuple(name for name in names if not any(name in text for text in others))


def _default(name: str) -> Any:
    return inspect.signature(iec104_server.Iec104Server.__init__).parameters[name].default


def _fits(type_id: int) -> int:
    """Azami ASDU boyuna sigan nesne sayisi (SQ = 0: her nesne kendi adresiyle)."""
    return (iec104.MAX_ASDU - iec104.ASDU_HEADER) // (iec104.IOA_SIZE + iec104.ELEMENT_SIZE[type_id])


def _mark(flag: bool) -> str:
    return YES if flag else NO


def _table(header: tuple[str, ...], rows: list[tuple[Any, ...]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(_cell(value) for value in row) + " |" for row in rows]
    return "\n".join(lines)


def interop_general() -> str:
    classes = [name for name, value in vars(iec104_server).items() if isinstance(value, type) and name.startswith("Iec104")]
    return _table(("Satir", "Isaret", "Kaynak"), [
        ("Kontrollu istasyon (alt istasyon) tanimi", YES, f"`iec104_server.{'`, `'.join(classes)}`, salt okunur"),
        ("Kontrol eden istasyon (ana istasyon) tanimi", NO, "modulde istemci/ana istasyon sinifi yok; merkez baglanti kurmaz"),
        ("Uygulama katmani", YES, "IEC 60870-5-101 ASDU'lari, IEC 60870-5-104 ag erisimiyle (`iec104.py`)"),
        ("Yazma / kontrol yolu", NO, f"her kontrol ASDU'su COT {iec104.COT_UNKNOWN_TYPE} + P/N ile reddedilir (GK6)"),
    ])


def interop_network() -> str:
    return _table(("Ozellik", "Deger", "Kaynak"), [
        ("Ag erisimi", "TCP/IP uzerinde coklu istemci", "`asyncio.start_server`"),
        ("Es zamanli baglanti siniri", _default("max_connections"), "`Iec104Server(max_connections=...)`"),
        ("Istasyon basina ortak adres", "her pano bir CA (= Modbus birim numarasi)", "`iec104_points`, `gateway`"),
        ("Yedekli baglanti grubu", NO, "tek dinleyici soket; yedeklilik uygulanmadi"),
        ("Seri hat yapilandirmasi (noktadan noktaya, coklu nokta)", NO, "IEC 60870-5-104 seri hat kullanmaz"),
    ])


def interop_physical() -> str:
    networks = ", ".join(f"`{network}`" for network in iec104_server.DEFAULT_ALLOWED_NETWORKS)
    return _table(("Ozellik", "Deger", "Kaynak"), [
        ("Tasima", "TCP/IP", "`Iec104Server.start`"),
        ("Dinlenen port", f"{_default('port')} (`IEC104_PORT`)", "`Iec104Server(port=...)`"),
        ("Dinlenen arayuz", f"`{_default('host')}` (`IEC104_HOST`)", "`Iec104Server(host=...)`"),
        ("Izinli istemci aglari", f"{networks} (`IEC104_ALLOWED_CLIENTS` ile daraltilir)", "`DEFAULT_ALLOWED_NETWORKS`"),
        ("Iletim hizi, seri cerceve (FT 1.2), bagli katman adresi", NO, "ag erisiminde yok"),
    ])


def interop_link() -> str:
    names = type_names()
    fits = ", ".join(f"{names[type_id]}: {_fits(type_id)}" for type_id in emitted_types())
    return _table(("Ozellik", "Deger", "Kaynak"), [
        ("Baslangic bayti", f"0x{iec104.START:02X}", "`iec104.START`"),
        ("Kontrol alani", "4 bayt; I (veri), S (onay), U (STARTDT/STOPDT/TESTFR)", "`decode_apdu`"),
        ("Azami APDU (uzunluk alani: kontrol alani + ASDU)", iec104.MAX_LENGTH, "`iec104.MAX_LENGTH`"),
        ("Azami APDU (hat uzerinde, baslangic + uzunluk dahil)", 2 + iec104.MAX_LENGTH, "`0x68` + uzunluk bayti + APDU"),
        ("Azami ASDU", iec104.MAX_ASDU, "`iec104.MAX_ASDU`"),
        ("Sira numarasi modulu", iec104.SEQ_MODULO, "`iec104.SEQ_MODULO` (15 bit)"),
        ("Bir ASDU'ya sigan azami nesne", fits,
         f"azami ASDU / (IOA + eleman); istasyonun grup siniri {iec104_server.MONITOR_OBJECTS} / {iec104_server.TIME_TAGGED_OBJECTS} (§2)"),
        ("Dengeli / dengesiz iletim", "104'te yalnizca dengeli; yoklama yok", "-"),
    ])


def interop_application() -> str:
    widths = field_widths()
    return _table(("Alan", "Uzunluk (oktet)", "Not"), [
        ("Tip tanimlayici", widths["tip"], "`encode_asdu` ciktisinin ilk bayti"),
        ("Degisken yapi niteleyici (VSQ)", widths["vsq"], "SQ = 0 uretilir (her nesne kendi adresiyle); SQ = 1 cozulur"),
        ("Iletim nedeni (COT)", widths["cot"], "neden + kaynak adres; kaynak adres gelen cercevedeki degeriyle geri doner"),
        ("Ortak adres (ASDU adresi)", widths["ca"], f"yayin adresi 0x{iec104.BROADCAST_COMMON_ADDRESS:04X}"),
        ("Bilgi nesnesi adresi (IOA)", widths["ioa"], "1000 / 2000 / 3000 tabanli plan (§4)"),
        ("Zaman etiketi", iec104.ELEMENT_SIZE[iec104.M_SP_TB_1] - 1, "CP56Time2a, UTC, yaz saati biti 0"),
    ])


def interop_asdu_selection() -> str:
    names, served, emitted = type_names(), served_types(), emitted_types()
    monitor = [(type_id, name) for type_id, name in sorted(names.items()) if name.startswith("M_")]
    control = [(type_id, name) for type_id, name in sorted(names.items()) if name.startswith("C_")]
    rows = [(type_id, f"`{name}`", "izleme", _mark(type_id in emitted), TYPE_NOTES[name]) for type_id, name in monitor]
    rows.append((NO, "Cift nokta, adim konumu, bit dizisi, sayac, koruma olayi", "izleme", NO, "kodekte tanimli degil; sunulmaz"))
    rows += [(type_id, f"`{name}`", "kontrol", _mark(type_id in served), TYPE_NOTES[name]) for type_id, name in control]
    rows.append((NO, "Diger tum kontrol tipleri", "kontrol", NO,
                 f"kodek tanimadigi icin COT {iec104.COT_UNKNOWN_TYPE} + P/N"))
    return _table(("Tip", "Ad", "Yon", "Isaret", "Not"), rows)


def interop_cot_matrix() -> str:
    header = ("Tip",) + tuple(f"{getattr(iec104, cot)}<br>{COT_LABELS[cot]}" for cot in COT_COLUMNS)
    rows = [(f"`{name}`",) + tuple(_mark(cot in used) for cot in COT_COLUMNS) for name, used in COT_MATRIX.items()]
    rows.append(("Diger tum tipler",) + tuple(_mark(cot == "COT_UNKNOWN_TYPE") for cot in COT_COLUMNS))
    unknown = ", ".join(str(getattr(iec104, cot)) for cot in COT_COLUMNS if cot.startswith("COT_UNKNOWN"))
    note = (f"\n\nReddetme nedenleri ({unknown}) her zaman P/N biti kurulu dondurulur. Istasyon sorgulamasi QOI {iec104.QOI_STATION} "
            f"disinda bir nitelikle gelirse ACTCON P/N ile dondurulur; grup sorgulamasi yoktur. "
            f"Kodekte tanimli olup hicbir SCADA modulunde gecmeyen sabitler: {', '.join(f'`{name}`' for name in unused_constants())}.")
    return _table(header, rows) + note


def interop_functions() -> str:
    served = served_types()
    rows = []
    for label, key, kind in FUNCTION_ROWS:
        if kind == "method":
            supported = hasattr(iec104_server._Connection, key)
            source = f"`_Connection.{key}`"
        else:
            type_id = getattr(iec104, key, None)
            supported = type_id in served
            source = f"`{key}` = {type_id}" if type_id is not None else f"`{key}` kodekte tanimli degil"
        rows.append((label, _mark(supported), source, FUNCTION_NOTES[key]))
    return _table(("Fonksiyon", "Isaret", "Kaynak", "Not"), rows)


def interop_timers() -> str:
    timing = iec104_server.Timing()
    fields = tuple(field.name for field in dataclasses.fields(timing))
    rows = [("t0 (baglanti kurma)", _mark("t0" in fields),
             f"`Timing` alanlari: {', '.join(fields)}; t0 yok - baglantiyi ana istasyon acar, istasyon hicbir zaman baglanti kurmaz")]
    rows += [("t1 (gonderilen I / TESTFR icin onay suresi)", f"{_number(timing.t1)} s", "asilirsa baglanti kapatilir"),
             ("t2 (alinan cerceveleri S ile onaylama)", f"{_number(timing.t2)} s", "t1'den kucuk olmali"),
             ("t3 (bosta TESTFR gonderme)", f"{_number(timing.t3)} s", "sessiz baglanti canlilik denetimine girer"),
             ("k (onaysiz gonderilebilen I cercevesi)", timing.k, "pencere dolunca gonderim bekletilir, baglanti kapatilmaz"),
             ("w (onaylanmadan alinabilen I cercevesi)", timing.w, "w'inci cercevede S gonderilir"),
             ("Port", _default("port"), "TCP, `IEC104_PORT`"),
             ("Kendiliginden gonderim taramasi", f"{_number(timing.spontaneous)} s", "olu bant denetimi araligi"),
             ("Zamanlayici adimi", f"{_number(timing.tick)} s", "t1/t2/t3 denetim cozunurlugu")]
    return _table(("Parametre", "Deger", "Not"), rows)


def table_interop() -> str:
    parts = [
        f"> Isaretleme: **{YES}** = uygulandi, **{NO}** = uygulanmadi/desteklenmiyor. Satirlarin tamami "
        "`backend/app/scada/` kodundan okunur; bu blok elle duzenlenmez.",
        "### 7.1 Genel bilgi (sistem veya cihaz)", interop_general(),
        "### 7.2 Ag yapilandirmasi", interop_network(),
        "### 7.3 Fiziksel katman", interop_physical(),
        "### 7.4 Baglanti katmani (APCI)", interop_link(),
        "### 7.5 Uygulama katmani: alan uzunluklari", interop_application(),
        "### 7.6 Standartlastirilmis ASDU secimi", interop_asdu_selection(),
        "### 7.7 Tip - iletim nedeni matrisi", interop_cot_matrix(),
        "### 7.8 Temel uygulama fonksiyonlari", interop_functions(),
        "### 7.9 Zaman asimlari, pencere parametreleri ve port", interop_timers(),
    ]
    return "\n\n".join(parts)


BLOCKS = {"istasyon": table_station, "asdu": table_asdu, "olculen": table_measured, "tek-nokta": table_single,
          "birlikte-calisabilirlik": table_interop}


def render(doc: str) -> str:
    for name, build in BLOCKS.items():
        pattern = re.compile(rf"(<!-- URETILMIS:{name} -->\n)(?:.*?\n)?(<!-- /URETILMIS:{name} -->)", re.S)
        if not pattern.search(doc):
            raise SystemExit(f"{DOC.name} icinde '{name}' blogu yok")
        table = build()
        doc = pattern.sub(lambda m: m[1] + table + "\n" + m[2], doc)
    return doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="dokuman guncel degilse 1 ile cik")
    args = parser.parse_args(argv)
    current = DOC.read_bytes().decode("utf-8")
    updated = render(current)
    if args.check:
        if updated != current:
            print(f"{DOC.relative_to(ROOT)} guncel degil: python scripts/gen_iec104_doc.py")
            return 1
        print("guncel")
        return 0
    DOC.write_bytes(updated.encode("utf-8"))
    print(f"yenilendi: {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
