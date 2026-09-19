#!/usr/bin/env python3
"""Mosquitto ACL dosyasinin BEKLENTI URETECI (F-27, Kisi B).

    python scripts/mqtt_acl.py                             # kural ozeti + yetki matrisi
    python scripts/mqtt_acl.py --acl deploy/mosquitto.acl
    python scripts/mqtt_acl.py --sor ADM-00001 write gridup/pano/ADM-00002/tel

Cikis kodu: 0 dosya ayristirildi, 2 ayristirilamadi / kullanim hatasi.

BU MODUL BIR BROKER DEGILDIR — ve bu yuzden TEK BASINA F-27'nin kaniti DEGILDIR.
Burada yazan sey, mosquitto 2.0.22'nin ACL semantiginin BIZIM OKUMAMIZDIR. Bir birim
testi yalnizca "okumamiz kendi icinde tutarli" der; "broker boyle davraniyor" DEMEZ.
Ikisi celisirse HAKLI OLAN BROKER'DIR ve duzeltilecek olan bu dosyadir.

Modulun mesru tek rolu sudur: canli olcumun (scripts/mtls_yetki_testi.py) BEKLENTI
sutununu uretmek. Olcum her vaka icin uc sutun basar:

    kural (ACL dosyasindan) | beklenen (bu modul) | OLCULEN (canli broker)

Karar sutunu OLCULEN'dir. Iki sutun ayrisirsa olcum KIRMIZI doner.

SEMANTIK — hepsi bu depoda konteynerle olculdu (docs/15 §5.1):
  1. `pattern` satirlari TUM kimliklere uygulanir; bir `user` blogu onlari gecersiz
     kilmaz, uzerine EKLER.
  2. Degerlendirme ONCE kullanicinin kendi `user` listesine bakar, SONRA `pattern`
     listesine. Bir liste ancak KARAR URETIRSE durdurur:
        * eslesen bir `deny` varsa            -> REDDEDILIR (o listede biter)
        * eslesen ve ISTENEN ERISIMI VEREN bir kural varsa -> IZINLI (o listede biter)
        * eslesme var ama hicbiri istenen erisimi vermiyorsa -> KARAR YOK, sonraki listeye
     Ucuncu sik kolayca gozden kacar ve ilk yazimda YANLIS yazilmisti: `user` blogunda
     `topic read gridup/pano/+/tel` varken YAZMA sorulursa o kural eslesir ama yazma
     vermez; karar orada bitmemeli, `pattern write gridup/pano/%u/tel` kalibina
     dusmelidir. Canli brokerda olculdu — broker IZIN veriyordu, modul REDDEDIYORDU.
  3. Bir listenin ICINDE `deny` dosya sirasindan bagimsiz olarak izni yener.
  4. Anonim istemci `%u` iceren bir kalibi hicbir sekilde eslestiremez.
  5. `acl_file` tanimliysa hicbir kurala uymayan topic VARSAYILAN OLARAK REDDEDILIR.
  6. Hicbir `user` satirindan ONCE gelen `topic` satirlari yalnizca ANONIM istemcilere
     uygulanir.
  7. Fiil yazilmazsa varsayilan `readwrite`.
  8. `%` yer tutuculari yalnizca `pattern` satirlarinda yorumlanir.
  9. `#` ve `+` joker karakterleri `$` ile BASLAYAN bir topic'i ESLESTIRMEZ ($SYS gibi
     broker ic topic'leri joker bir kuralla acilmaz). Olculdu: `topic write #` kurali
     altinda `$custom/x` yayini RC 135 ile reddedildi.

BU MODUL ILE BROKER AYRISIRSA HAKLI OLAN BROKER'DIR. Yukaridaki 2. ve 9. maddeler
tam olarak boyle bulundu: modul yazildi, canli brokerla karsilastirildi, MODUL duzeltildi.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACL = REPO_ROOT / "deploy" / "mosquitto.acl"

#: Mosquitto'nun kabul ettigi fiiller. Yanlis fiil broker'i ACMAZ
#: ("Invalid topic access type"), bu yuzden burada da hata olmali.
VERBS = ("read", "write", "readwrite", "deny")
DEFAULT_VERB = "readwrite"

#: Anonim istemcinin kullanici adi. `%u` kaliplari bununla ESLESMEZ.
ANONYMOUS = None


class AclError(ValueError):
    """ACL dosyasi ayristirilamadi. Broker da bu dosyayla ACILMAZ."""


@dataclass(frozen=True)
class Rule:
    verb: str
    topic: str
    line_no: int
    #: True ise `pattern` satiri (%u/%c yorumlanir ve herkese uygulanir).
    is_pattern: bool

    def grants(self, access: str) -> bool:
        if self.verb == "deny":
            return False
        return self.verb == "readwrite" or self.verb == access


class Acl:
    """Ayristirilmis ACL dosyasi: anonim kurallari + kullanici bloklari + kaliplar."""

    def __init__(self, anonymous: list[Rule], users: dict[str, list[Rule]], patterns: list[Rule]) -> None:
        self.anonymous = anonymous
        self.users = users
        self.patterns = patterns

    @property
    def usernames(self) -> tuple[str, ...]:
        return tuple(self.users)

    def allows(self, user: str | None, access: str, topic: str, *, client_id: str = "") -> bool:
        """`user` kimligi `topic` uzerinde `access` yapabilir mi?

        access: "read" veya "write". Donus True = izinli, False = reddedilir.
        """
        if access not in ("read", "write"):
            raise ValueError(f"access 'read' ya da 'write' olmali, bulunan {access!r}")

        own = self.anonymous if user is ANONYMOUS else self.users.get(user, [])
        decided = _decide(own, access, topic, user=user, client_id=client_id)
        if decided is not None:
            return decided
        # Kendi listesinde eslesme yok: kaliplara gecilir (semantik 2).
        decided = _decide(self.patterns, access, topic, user=user, client_id=client_id)
        # acl_file tanimliyken hicbir kurala uymayan topic reddedilir (semantik 5).
        return bool(decided)


def _decide(rules: list[Rule], access: str, topic: str, *, user: str | None, client_id: str) -> bool | None:
    """Tek bir listede karar: None = bu liste KARAR URETMEDI (sonraki listeye gecilir).

    "Eslesme yok" ile "eslesti ama istenen erisimi vermedi" AYNI SEYDIR: ikisi de
    karar uretmez (semantik 2). Ikincisini False saymak modulu brokerdan ayirir —
    `topic read X` kurali YAZMA sorusunu cevaplamaz, yalnizca sessiz kalir.
    """
    matched = [rule for rule in rules if _matches(rule, topic, user=user, client_id=client_id)]
    # Liste icinde `deny` sirasindan bagimsiz olarak kazanir (semantik 3).
    if any(rule.verb == "deny" for rule in matched):
        return False
    if any(rule.grants(access) for rule in matched):
        return True
    return None


def _matches(rule: Rule, topic: str, *, user: str | None, client_id: str) -> bool:
    pattern = rule.topic
    if rule.is_pattern:
        if "%u" in pattern:
            if user is ANONYMOUS:
                return False  # semantik 4
            pattern = pattern.replace("%u", user)
        pattern = pattern.replace("%c", client_id)
    return topic_matches(pattern, topic)


def topic_matches(filter_: str, topic: str) -> bool:
    """MQTT topic filtresi eslesmesi: '+' tek seviye, '#' sondan itibaren hepsi."""
    f_parts = filter_.split("/")
    t_parts = topic.split("/")
    # Semantik 9: joker karakterler `$` ile baslayan bir topic'i eslestirmez.
    # `topic write #` kurali $SYS/... ya da $custom/... yayinina IZIN VERMEZ (olculdu).
    if topic.startswith("$") and f_parts[0] in ("+", "#"):
        return False
    for index, part in enumerate(f_parts):
        if part == "#":
            # '#' en az sifir seviye eslesir ve yalnizca SON parca olabilir.
            return index == len(f_parts) - 1
        if index >= len(t_parts):
            return False
        if part != "+" and part != t_parts[index]:
            return False
    return len(f_parts) == len(t_parts)


def parse_acl(text: str) -> Acl:
    """ACL metnini ayristirir. Bozuk satir SESSIZCE ATLANMAZ: broker da acilmaz."""
    anonymous: list[Rule] = []
    users: dict[str, list[Rule]] = {}
    patterns: list[Rule] = []
    current: list[Rule] | None = None  # None = henuz `user` gorulmedi -> anonim blok

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        head, _, rest = line.partition(" ")
        head = head.lower()
        rest = rest.strip()

        if head == "user":
            if not rest:
                raise AclError(f"{line_no}. satir: `user` satirinda kullanici adi yok")
            current = users.setdefault(rest, [])
            continue

        if head not in ("topic", "pattern"):
            raise AclError(f"{line_no}. satir: bilinmeyen anahtar {head!r} (topic / pattern / user)")

        verb, topic = _verb_and_topic(rest, line_no)
        rule = Rule(verb=verb, topic=topic, line_no=line_no, is_pattern=head == "pattern")
        if head == "pattern":
            if "%u" not in topic and "%c" not in topic:
                # Mosquitto bunu uyari olarak gecer ama kural HERKESE uygulanir;
                # kalibi yer tutucusuz yazmak neredeyse her zaman bir hatadir.
                raise AclError(f"{line_no}. satir: `pattern` icinde %u ya da %c yok: {topic!r}")
            patterns.append(rule)
        elif current is None:
            anonymous.append(rule)  # semantik 6
        else:
            current.append(rule)

    return Acl(anonymous=anonymous, users=users, patterns=patterns)


def _verb_and_topic(rest: str, line_no: int) -> tuple[str, str]:
    """`[fiil] topic` ayristirir.

    Iki jeton varsa BIRINCISI fiil OLMAK ZORUNDADIR: `topic publish a/b` mosquitto'da
    `Invalid topic access type "publish"` ile dosyayi acmayi REDDETTIRIR (olculdu).
    Burada da hata atmazsak "publish a/b" sessizce bir topic sanilir ve kural hicbir
    seyle eslesmez — yani bir yetki kurali sessizce kaybolur.
    """
    if not rest:
        raise AclError(f"{line_no}. satir: topic yok")
    first, _, tail = rest.partition(" ")
    tail = tail.strip()
    if first.lower() in VERBS:
        if not tail:
            raise AclError(f"{line_no}. satir: fiilden sonra topic yok")
        return first.lower(), tail
    if tail:
        raise AclError(f"{line_no}. satir: gecersiz erisim turu {first!r} (gecerli: {', '.join(VERBS)})")
    return DEFAULT_VERB, first  # semantik 7


def load_acl(path: Path) -> Acl:
    return parse_acl(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--acl", default=str(DEFAULT_ACL), help=f"varsayilan: {DEFAULT_ACL}")
    parser.add_argument("--sor", nargs=3, metavar=("KULLANICI", "ERISIM", "TOPIC"),
                        help="tek soru sorar: izinliyse 0, reddedilirse 1 ile cikar")
    args = parser.parse_args(argv)

    try:
        acl = load_acl(Path(args.acl))
    except (OSError, AclError) as exc:
        print(f"ACL okunamadi: {exc}", file=sys.stderr)
        return 2

    if args.sor:
        user, access, topic = args.sor
        try:
            izinli = acl.allows(user, access, topic)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(f"{user} {access} {topic} -> {'IZINLI' if izinli else 'REDDEDILIR'}")
        return 0 if izinli else 1

    print(f"ACL: {args.acl}")
    print(f"  kalip kurali : {len(acl.patterns)}")
    print(f"  kullanici    : {', '.join(acl.usernames) or '(yok)'}")
    print(f"  anonim kurali: {len(acl.anonymous)}")
    print("\nNOT: asagidakiler BEKLENTIDIR, olcum degildir. Karar canli brokerdadir.")
    print("     scripts/mtls_yetki_testi.py beklenen ile olculeni yan yana basar.\n")
    for user in ("ADM-00001", *acl.usernames):
        for access, topic in (
            ("write", "gridup/pano/ADM-00001/tel"),
            ("write", "gridup/pano/ADM-00002/tel"),
            ("read", "gridup/pano/ADM-00001/cmd"),
            ("write", "gridup/pano/ADM-00001/cmd"),
            ("read", "gridup/pano/ADM-00002/tel"),
        ):
            karar = "IZINLI    " if acl.allows(user, access, topic) else "REDDEDILIR"
            print(f"  {user:<16} {access:<5} {topic:<32} {karar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
