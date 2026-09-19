"""HTTP kimlik dogrulama ve rol (F-19, on-prem).

NEDEN VAR
Onay ve raf istekleri kullanici adini ISTEK GOVDESINDEN aliyordu (`by: str`), yani
denetim izindeki "kim yapti" alanini istemci kendisi yaziyordu. Alarm onayi bir
operator eylemidir ve ISA-18.2 denetim izinin tasidigi kimlik dogrulanabilir olmali.

Bu dosya, depoda ZATEN IKI KEZ uygulanmis bir ilkeyi ucuncu kanala tasir:

    SCADA  -> scada/gateway.py: by, TCP oturumunun peer adresinden turetilir
    SMS    -> notify/dispatcher.py: gonderen numara beyaz listeye dogrulanir,
              kayitsiz numara yok sayilir; by = "sms:<maskeli numara>"
    HTTP   -> BU DOSYA: by, dogrulanmis Authorization basligindan turetilir

NEDEN BOYLE BIR MEKANIZMA (ve neden OIDC/SSO degil)
GK4 public cloud yasakliyor: Auth0 / Entra / Cognito gibi bulut kimlik saglayicilari
kullanilamaz. On-prem bir OIDC saglayicisi (Keycloak vb.) kurmak yeni bir servis,
yeni bir bagimlilik ve yeni bir isletim yuku demektir; backend/requirements.txt de
kilitli bir dosyadir. Bu yuzden burada YENI BAGIMLILIK YOK: tasiyici (bearer) belirteci
yapilandirmadan okunan bir operator tablosuna karsi dogrulanir, karsilastirma
`hmac.compare_digest` ile sabit zamanlidir.

BUNUN OLMADIGI SEY — acikca yazilir, docs/15 §5'te de durur:
  * Kurumsal SSO / OIDC / LDAP degildir. Belirtecler yapilandirmada duran PAYLASILAN
    SIRLARDIR; kullanici parolasi, parola ozeti, oturum suresi, belirtec yenileme,
    iptal listesi ve hesap kilitleme YOKTUR.
  * Yalnizca YAZMA uclarini korur (onay / raf). Okuma uclari aciktir — filo listesi,
    pano detayi, seri ve WebSocket akisi kimlik istemez.
  * Operator tablosu bos birakilirsa kimlik dogrulama KAPALIDIR. Bu, kablosuz
    calisan demo yolunu (GK4) bozmamak icindir ve /health uzerinde GORUNUR:
    `auth` alani "disabled" doner ve baslangicta uyari loglanir. Sessiz bir
    varsayilan degildir.
"""

from __future__ import annotations

import hmac
import logging
import os
from dataclasses import dataclass
from typing import Callable

from fastapi import HTTPException, Request

log = logging.getLogger(__name__)

#: docs/15-guvenlik-kvkk.md §2 C4 satirindaki uc rol, dusukten yuksege.
#: izleyici = yalnizca okur · operator = alarm onaylar ve rafa alir · muhendis = hepsi.
ROLES = ("izleyici", "operator", "muhendis")
_RANK = {role: index for index, role in enumerate(ROLES)}

_ENV_VAR = "GRIDUP_OPERATORS"
_BEARER = "bearer"


@dataclass(frozen=True)
class Identity:
    """Dogrulanmis cagirici. `by` alani BUNDAN turer, istek govdesinden degil."""

    user: str
    role: str

    def can(self, minimum: str) -> bool:
        return _RANK[self.role] >= _RANK[minimum]


class OperatorTable:
    """Belirtec -> kimlik eslemesi. Bos tablo = kimlik dogrulama kapali."""

    def __init__(self, entries: dict[str, Identity] | None = None) -> None:
        self._entries = dict(entries or {})

    @property
    def enabled(self) -> bool:
        return bool(self._entries)

    @property
    def users(self) -> tuple[str, ...]:
        return tuple(sorted(identity.user for identity in self._entries.values()))

    def lookup(self, token: str) -> Identity | None:
        """Sabit zamanli arama.

        Sozluk anahtari olarak aramak, belirtecin ilk baytlarinin dogru olup
        olmadigini zamanlamayla sizdirabilirdi. Tablo birkac satirlik oldugu icin
        tamamini gezip compare_digest kullanmak bedava sayilir; dongu ERKEN
        KESILMEZ, yoksa sabit zamanlilik bozulur.
        """
        found: Identity | None = None
        for candidate, identity in self._entries.items():
            if hmac.compare_digest(token, candidate):
                found = identity
        return found


def parse_operators(raw: str) -> OperatorTable:
    """`kullanici:rol:belirtec` uclulerini virgul veya satirbasiyla ayrilmis okur.

    Ornek: "tuna:muhendis:s3cret,ahmet:operator:t0ken"

    Bozuk satir SESSIZCE ATLANMAZ, ValueError atar: yanlis yazilmis bir satir
    yuzunden bir operatorun sessizce yetkisiz kalmasi, servisin hic acilmamasindan
    daha kotudur (sozlesme bozuksa servis baslamaz kuralinin ayni mantigi).
    """
    entries: dict[str, Identity] = {}
    for chunk in raw.replace("\n", ",").split(","):
        line = chunk.strip()
        if not line:
            continue
        parts = line.split(":")
        if len(parts) != 3:
            raise ValueError(f"{_ENV_VAR}: 'kullanici:rol:belirtec' bekleniyordu, bulunan {line!r}")
        user, role, token = (part.strip() for part in parts)
        if not user or not token:
            raise ValueError(f"{_ENV_VAR}: kullanici ve belirtec bos olamaz ({line!r})")
        if role not in _RANK:
            raise ValueError(f"{_ENV_VAR}: bilinmeyen rol {role!r}; gecerli roller: {', '.join(ROLES)}")
        if token in entries:
            raise ValueError(f"{_ENV_VAR}: ayni belirtec iki kullaniciya verilmis ({user!r})")
        entries[token] = Identity(user=user, role=role)
    return OperatorTable(entries)


def operators_from_env() -> OperatorTable:
    table = parse_operators(os.getenv(_ENV_VAR, ""))
    if table.enabled:
        log.info("kimlik dogrulama ACIK: %d operator (%s)", len(table.users), ", ".join(table.users))
    else:
        log.warning(
            "kimlik dogrulama KAPALI: %s tanimsiz. Onay/raf istekleri kimlik dogrulamadan "
            "kabul edilir ve denetim izine 'anonim' yazilir. Uretimde tanimlayin.",
            _ENV_VAR,
        )
    return table


#: Kimlik dogrulama kapaliyken denetim izine yazilan ad. "operator" gibi gercek bir
#: kullanici adina BENZEMEMESI kasitlidir: kayda bakan biri bunun dogrulanmamis
#: oldugunu gormeli.
ANONYMOUS = Identity(user="anonim (kimlik dogrulama kapali)", role="muhendis")


def _token_from_header(header: str | None) -> str:
    if not header:
        raise HTTPException(
            status_code=401,
            detail="kimlik dogrulama gerekli: Authorization: Bearer <belirtec>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = header.partition(" ")
    if scheme.lower() != _BEARER or not token.strip():
        raise HTTPException(
            status_code=401,
            detail="desteklenmeyen yetkilendirme bicimi; 'Bearer <belirtec>' bekleniyor",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token.strip()


def require(minimum: str) -> Callable[[Request], Identity]:
    """`minimum` rolunu (veya ustunu) isteyen FastAPI bagimliligi uretir."""
    if minimum not in _RANK:
        raise ValueError(f"bilinmeyen rol {minimum!r}")

    def dependency(request: Request) -> Identity:
        table: OperatorTable = request.app.state.operators
        if not table.enabled:
            return ANONYMOUS

        identity = table.lookup(_token_from_header(request.headers.get("Authorization")))
        if identity is None:
            raise HTTPException(
                status_code=401,
                detail="gecersiz belirtec",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not identity.can(minimum):
            raise HTTPException(
                status_code=403,
                detail=f"bu islem '{minimum}' rolu gerektiriyor; '{identity.user}' rolu '{identity.role}'",
            )
        return identity

    return dependency
