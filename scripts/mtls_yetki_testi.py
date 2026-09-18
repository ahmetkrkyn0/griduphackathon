#!/usr/bin/env python3
"""mTLS ve cihaz basina topic yetkisinin CANLI OLCUMU (F-27, Kisi B).

    bash scripts/sertifika-uret.sh
    docker compose -f deploy/compose.yaml --profile mtls up -d mosquitto-mtls
    backend/.venv/Scripts/python scripts/mtls_yetki_testi.py
    backend/.venv/Scripts/python scripts/mtls_yetki_testi.py --mutasyon-yok   # hizli kosu

Cikis kodu: 0 butun vakalar beklendigi gibi olculdu, 1 en az bir vaka ayristi,
2 olcum yapilamadi (broker yok, sertifika yok, baglanti kurulamadi) = KARARSIZ.

NEDEN AYRI BIR BETIK: ayni gerekce scripts/verify_journal.py'dekiyle aynidir. Yetkiyi
UYGULAYAN broker'dir; onu kendi kodumuzdan dogrulamak "kendi kendini onaylayan" bir
kanit olurdu. Bu betik broker'i CALISTIRMAZ, ona disaridan baglanir ve dort sinyalin
ayni seyi soyleyip soylemedigine bakar.

NE KANITLAR
  Backlog'un kabul olcutu tek cumledir: "bir panonun sertifikasiyla BASKA bir panonun
  topic'ine yayin denemesinin broker tarafindan REDDEDILMESI". Bu betik onu dort ayri
  sinyalle olcer ve HERHANGI IKISI ayrisirsa KIRMIZI doner:
      A) MQTT 5.0 PUBACK reason code 135 "Not authorized" — broker'in kendi agzindan.
      B) Abonenin mesaji ALMAMASI — davranissal kanit.
      C) Broker logundaki "Denied PUBLISH from <kosuya ozgu istemci kimligi>" satiri.
      D) Broker imajinin KENDI mosquitto_pub araciyla alinan ikinci PUBACK (paho disi).

  SINYALLERIN BAGIMSIZLIK DERECESI — abartilmamali: A ile C ayni yetki denetiminin
  IKI FARKLI CIKTI KANALIDIR (ayni surec, ayni karar), dolayisiyla birbirini bagimsiz
  teyit ETMEZLER; ayrismalari ancak brokerin loglamasi ile donus yolu celisirse olur.
  Gercekten farkli bir sey olcen ikisi B (teslim edilmemesi) ve D'dir (paho yerine
  brokerin kendi C istemcisi). Dordunu birden istemek yine de degerlidir: her biri
  farkli bir yazilim hatasi sinifini yakalar.

NE KANITLAMAZ — docs/15 §5.1'de de aynen yazili:
  * Pano kimliginin TAKLIT EDILEMEZ oldugunu kanitlamaz. CA ve butun ozel anahtarlar
    ayni makinede, deploy/certs/ icinde duz durur; o dizini okuyan gecerli sertifika basar.
    Olculen sey "broker kurali uyguluyor"dur, "kimlik guvenli"dir DEGIL.
  * Cihazlarin birbirinden YALITILDIGINI kanitlamaz: bu betik tek surecte butun
    panolarin anahtarlarini okur. Sahada her pano ayri bir cihazdir; burada degil.
  * IPTAL edilmis bir sertifikanin reddedildigini kanitlamaz — iptal mekanizmasi YOK.
  * Duz demo yolu (1883, anonim) hakkinda hicbir sey soylemez; o yol degismedi.

YANLIS NEDENLE GECMEYE KARSI ALINAN ONLEMLER (her biri bir sahte-gecis sinifini kapatir):
  * POZITIF KONTROL: her ret iddiasindan ONCE, AYNI baglanti uzerinden kendi topic'ine
    yapilan yayinin gozlemciye ULASTIGI gorulur. Ulasmazsa sonuc PASS degil KARARSIZ'dir.
    Broker kapali / TLS patlamis / ACL hic yuklenmemis durumlarini tek basina kapatir.
  * KONTROL GRUBU: reddedilen topic'in AYNISINA sahibi olan pano yayin yapar ve mesaj
    ULASIR. Topic'in gercek ve ulasilabilir oldugunu kanitlar (yanlis yazilmis topic
    de "gelmedi" uretirdi).
  * SANDVIC BARIYERI: kendi(A) -> hedef(X) -> kendi(B) sirasiyla yayin. Broker ayni
    istemcinin ayni QoS akisinda sirayi korur; gozlemci B'yi aldigi anda X'in HIC
    GELMEYECEGI kesinlesir. Sabit `sleep` ile "gelmedi" karari VERILMEZ.
  * NONCE: her yuk benzersiz bir uuid tasir; onceki kosudan kalan retained/kuyruk
    mesaji pozitif kontrolu sahte geciremez.
  * KOSUYA OZGU ISTEMCI KIMLIGI: canli backend'in client_id'si ele gecirilmez ve
    broker logundaki satir baska bir istemciye atfedilemez.
  * RET KATMANI AYRIMI: TLS el sikismasi reddi, CONNACK reddi ve PUBLISH reddi ayri
    ayri siniflandirilir; beklenenden BASKA katmanda gelen ret gecersiz sayilir.
  * MUTASYON KOSUSU: ACL kurali gecici olarak gevsetilir, broker'a SIGHUP gonderilir
    ve ayni vaka bu kez IZINLI olculmelidir. Testin kirmiziya donebildigi gosterilmeden
    "negatif test gecti" cumlesi hicbir sey ifade etmez.
  * BEKLENEN vs OLCULEN: beklenti scripts/mqtt_acl.py'den gelir (o bir broker DEGILDIR).
    Iki sutun ayrisirsa kosu KIRMIZI doner ve duzeltilecek olan mqtt_acl.py'dir.
    DIKKAT — bunun kapatMADIGI sinif: modul ile vaka tablosu AYNI yanlisi paylasirsa
    ayrisma gorunmez. Model hatalari boyle bulundu ve boyle bulunmaya devam edecek:
    modulu canli brokerla karsilastirarak (bkz. mqtt_acl.py semantik 2 ve 9).
  * BAGLANTI VAKALARINDA DA POZITIF KONTROL: "sertifikasiz baglanti reddedildi" demeden
    once GECERLI bir kimligin baglanabildigi gorulur. Yoksa kapali bir broker da,
    yanlis bir port da "reddedildi" uretirdi.
  * KOSU SONU CANLILIK DENETIMI: broker olcum ORTASINDA olurse kopan el sikismalari
    "reddedildi" gibi okunur; bu yuzden sonda yeniden baglanilir.
  * KILIT: es zamanli ikinci bir kosu ayni ACL dosyasini ve ayni brokeri paylasir.
  * MUTASYON YEDEGI: ACL bayt kopyasi diske yazilir; SIGTERM `finally` blogunu
    kosturmaz ve bellekteki dize tek basina yeterli degildi (olculdu).
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import ssl
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import paho.mqtt.client as mqtt  # noqa: E402

from app.config import MqttTls, load_contracts, topic_filter  # noqa: E402
from app.ingest import MqttSubscriber  # noqa: E402
from mqtt_acl import load_acl  # noqa: E402

CERT_DIR = REPO_ROOT / "deploy" / "certs"
ACL_PATH = REPO_ROOT / "deploy" / "mosquitto.acl"
#: Mutasyon kosusunun bayt kopyasi. VARLIGI "kosu yarim kaldi" demektir (git disi).
ACL_YEDEK = REPO_ROOT / "deploy" / "certs" / "mosquitto.acl.mutasyon-yedegi"
#: Es zamanli iki kosu ayni ACL dosyasini ve ayni brokeri paylasir; biri digerinin
#: mutasyon penceresine denk gelirse yanlis sonuc uretir ve dosyayi bozabilir (olculdu).
KILIT = REPO_ROOT / "deploy" / "certs" / ".mtls-yetki-testi.kilit"
CONTRACTS_DIR = REPO_ROOT / "contracts"
KONTEYNER = "gridup-mosquitto-mtls"
HOST, PORT = "127.0.0.1", 8883

BAGLANTI_ZAMAN_ASIMI_S = 15.0
BARIYER_ZAMAN_ASIMI_S = 20.0

#: MQTT 5.0 PUBACK reason code'lari (olculen degerler).
RC_BASARILI = 0
RC_ABONE_YOK = 16  # "No matching subscribers" — KABUL, yalnizca dinleyen yok
RC_YETKISIZ = 135  # "Not authorized" — ACL reddi
KABUL_EDILEN_RC = (RC_BASARILI, RC_ABONE_YOK)


class Kararsiz(RuntimeError):
    """Olcum yapilamadi. Bu bir BASARISIZLIK degil, SONUCSUZLUK'tur (cikis 2)."""


# ----------------------------------------------------------------------- yardimcilar


def kabuk(*komut: str, girdi: str | None = None) -> subprocess.CompletedProcess:
    ortam = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    return subprocess.run(komut, capture_output=True, text=True, input=girdi, env=ortam, encoding="utf-8",
                          errors="replace")


def openssl_alan(crt: Path, *bayraklar: str) -> str:
    sonuc = kabuk("openssl", "x509", "-in", str(crt), "-noout", *bayraklar)
    if sonuc.returncode != 0:
        raise Kararsiz(f"{crt} okunamadi: {sonuc.stderr.strip()}")
    return sonuc.stdout.strip()


def cn_oku(crt: Path) -> str:
    satir = openssl_alan(crt, "-subject")
    _, _, kuyruk = satir.partition("CN")
    return kuyruk.lstrip(" =").split(",")[0].strip()


def parmak_izi(crt: Path) -> str:
    return openssl_alan(crt, "-fingerprint", "-sha256").partition("=")[2]


# ----------------------------------------------------------------------- kimlikler


@dataclass(frozen=True)
class Kimlik:
    """Bir mTLS istemcisi: ad (= sertifikanin CN'i) ve uc dosya."""

    ad: str
    tls: MqttTls
    crt: Path

    @staticmethod
    def pano(pano_id: str) -> Kimlik:
        dizin = CERT_DIR / "pano" / pano_id
        return Kimlik(
            ad=pano_id,
            tls=MqttTls(str(CERT_DIR / "ca.crt"), str(dizin / f"{pano_id}.crt"), str(dizin / f"{pano_id}.key")),
            crt=dizin / f"{pano_id}.crt",
        )

    @staticmethod
    def merkez() -> Kimlik:
        dizin = CERT_DIR / "backend"
        return Kimlik(
            ad="gridup-backend",
            tls=MqttTls(str(CERT_DIR / "ca.crt"), str(dizin / "gridup-backend.crt"), str(dizin / "gridup-backend.key")),
            crt=dizin / "gridup-backend.crt",
        )


# ----------------------------------------------------------------------- on ucus


def on_ucus(kimlikler: list[Kimlik]) -> dict:
    """Olcumden ONCE ortami dogrular. Burada duran her sey sahte bir 'ret' uretirdi."""
    if not CERT_DIR.exists():
        raise Kararsiz("deploy/certs yok: once `bash scripts/sertifika-uret.sh` kosun")

    durum = kabuk("docker", "inspect", "-f", "{{.State.Running}}|{{.Image}}", KONTEYNER)
    if durum.returncode != 0 or not durum.stdout.startswith("true"):
        raise Kararsiz(
            f"{KONTEYNER} calismiyor. Kaldirin:\n"
            "  docker compose -f deploy/compose.yaml --profile mtls up -d mosquitto-mtls"
        )
    imaj = durum.stdout.strip().split("|", 1)[1]
    surum = kabuk("docker", "logs", KONTEYNER)
    surum_satiri = next(
        (s.split(": ", 1)[-1] for s in surum.stdout.splitlines() if "mosquitto version" in s and "running" in s),
        "(okunamadi)",
    )

    for kimlik in kimlikler:
        for yol in (Path(kimlik.tls.ca), Path(kimlik.tls.certfile), Path(kimlik.tls.keyfile)):
            if not yol.is_file():
                raise Kararsiz(f"{kimlik.ad}: {yol} yok (sertifika-uret.sh kosuldu mu?)")
        dogrula = kabuk("openssl", "verify", "-CAfile", kimlik.tls.ca, kimlik.tls.certfile)
        if dogrula.returncode != 0:
            raise Kararsiz(f"{kimlik.ad}: sertifika zinciri dogrulanmadi — {dogrula.stdout.strip()}")
        # Sabit dize degil, SERTIFIKADAN okunan CN karsilastirilir: yanlis sertifikayla
        # olcup "A -> B reddedildi" sanmak bu satirda yakalanir.
        okunan = cn_oku(kimlik.crt)
        if okunan != kimlik.ad:
            raise Kararsiz(f"sertifika CN'i beklenenden farkli: {okunan!r} != {kimlik.ad!r}")
        bitis = openssl_alan(kimlik.crt, "-enddate").partition("=")[2]
        if kabuk("openssl", "x509", "-in", str(kimlik.crt), "-noout", "-checkend", "0").returncode != 0:
            raise Kararsiz(f"{kimlik.ad}: sertifikanin suresi DOLMUS ({bitis}) — ret ACL'den degil saatten gelirdi")

    return {"imaj": imaj, "mosquitto": surum_satiri}


# ----------------------------------------------------------------------- gozlemci


class Gozlemci:
    """Merkez kimligiyle filoyu dinler.

    Backend'in KENDI sinifini (app.ingest.MqttSubscriber) kullanir: boylece merkezin
    mTLS kod yolu da canli olcume girer, ayri bir test istemcisi yazilmis olmaz.
    """

    def __init__(self, merkez: Kimlik, kosu: str) -> None:
        contracts = load_contracts(CONTRACTS_DIR)
        self.filtreler = [topic_filter(t) for t in contracts.ingest_topics]
        self.gelen: list[tuple[str, dict]] = []
        self._sub = MqttSubscriber(
            HOST, PORT, contracts, self._al,
            # Kosuya ozgu kimlik: canli backend'in oturumunu ELE GECIRMEZ (ayni
            # client_id ile ikinci bir baglanti mosquitto'da birincisini dusururdu).
            client_id=f"gridup-acltest-gozlemci-{kosu}",
            tls=merkez.tls,
        )

    def _al(self, topic: str, ham: bytes) -> None:
        try:
            self.gelen.append((topic, json.loads(ham)))
        except ValueError:
            pass

    def basla(self) -> None:
        self._sub.start()
        son = time.monotonic() + BAGLANTI_ZAMAN_ASIMI_S
        while time.monotonic() < son:
            if self._sub.connected:
                return
            time.sleep(0.1)
        raise Kararsiz(
            "gozlemci brokera baglanamadi. TLS 1.3'te istemci sertifikasi reddi istisna "
            "ATMAZ, yalnizca baglanti kurulmaz — sebep sertifika, CA ya da kapali broker olabilir."
        )

    def dur(self) -> None:
        self._sub.stop()

    def nonce_var_mi(self, nonce: str) -> bool:
        return any(yuk.get("nonce") == nonce for _, yuk in self.gelen)

    def bariyeri_bekle(self, nonce: str) -> bool:
        """Sandvicin SON diliminin gelmesini bekler. False = bariyer hic gelmedi."""
        son = time.monotonic() + BARIYER_ZAMAN_ASIMI_S
        while time.monotonic() < son:
            if self.nonce_var_mi(nonce):
                return True
            time.sleep(0.05)
        return False


class KomutGozlemci:
    """Bir panonun KENDI komut topic'ini dinler (ACL: `pattern read gridup/pano/%u/cmd`).

    NEDEN GEREKLI: merkez kimliginin (gridup-backend) yazabildigi tek topic turu `cmd`,
    okuyabildigi tek topic turu ise `tel/evt/hb`'dir — en az yetki geregi KESISMEZLER.
    Bu yuzden merkezin pozitif kontrolu kendi aboneligiyle GORULEMEZ. Panonun kendi
    komut aboneligi bu boslugu ACL'i esnetmeden kapatir: merkez ADM-00001'in komut
    topic'ine yayinlar, ADM-00001 onu okur.
    """

    def __init__(self, pano: Kimlik, kosu: str) -> None:
        self.topic = f"gridup/pano/{pano.ad}/cmd"
        self.gelen: list[dict] = []
        self.suback: list[int] = []
        self._c = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=f"gridup-acltest-cmd-{kosu}", protocol=mqtt.MQTTv5
        )
        self._c.tls_set(ca_certs=pano.tls.ca, certfile=pano.tls.certfile, keyfile=pano.tls.keyfile)
        self._c.on_message = self._al
        self._c.on_subscribe = lambda cl, u, mid, rcs, props: self.suback.extend(
            int(getattr(r, "value", r)) for r in rcs
        )

    def _al(self, client, userdata, message) -> None:
        try:
            self.gelen.append(json.loads(message.payload))
        except ValueError:
            pass

    def basla(self) -> None:
        self._c.connect(HOST, PORT, keepalive=30)
        self._c.loop_start()
        self._c.subscribe(self.topic, qos=1)
        son = time.monotonic() + BAGLANTI_ZAMAN_ASIMI_S
        while time.monotonic() < son and not self.suback:
            time.sleep(0.05)
        if not self.suback:
            raise Kararsiz("komut gozlemcisi abone olamadi")
        # SUBACK 0x80 = abonelik reddi. Olculen davranis: mosquitto 2.0.22 yetkisiz
        # aboneligi SUBACK'te REDDETMEZ (Granted QoS doner, yalnizca teslim etmez).
        # Yine de denetleniyor: bir gun reddederse sessizce butun negatifler gecerdi.
        if any(rc >= 0x80 for rc in self.suback):
            raise Kararsiz(f"komut gozlemcisinin aboneligi reddedildi: SUBACK {self.suback}")

    def dur(self) -> None:
        self._c.loop_stop()
        self._c.disconnect()

    def nonce_var_mi(self, nonce: str) -> bool:
        return any(yuk.get("nonce") == nonce for yuk in self.gelen)

    def bariyeri_bekle(self, nonce: str) -> bool:
        son = time.monotonic() + BARIYER_ZAMAN_ASIMI_S
        while time.monotonic() < son:
            if self.nonce_var_mi(nonce):
                return True
            time.sleep(0.05)
        return False


# ----------------------------------------------------------------------- yayinci


class Yayinci:
    """Tek bir kimligin MQTT 5.0 baglantisi. Ret PUBACK reason code'undan okunur."""

    def __init__(self, kimlik: Kimlik, kosu: str) -> None:
        self.kimlik = kimlik
        self.client_id = f"gridup-acltest-{kimlik.ad}-{kosu}"
        self._rc: dict[int, int] = {}
        self._baglandi: int | None = None
        self.tls_surumu = "(olculemedi)"
        self._c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id, protocol=mqtt.MQTTv5)
        self._c.tls_set(ca_certs=kimlik.tls.ca, certfile=kimlik.tls.certfile, keyfile=kimlik.tls.keyfile)
        self._c.on_connect = self._on_connect
        self._c.on_publish = self._on_publish

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        self._baglandi = int(getattr(reason_code, "value", reason_code))

    def _on_publish(self, client, userdata, mid, reason_code, properties) -> None:
        self._rc[mid] = int(getattr(reason_code, "value", reason_code))

    def bagla(self) -> str:
        """Donus: '' = baglandi; aksi halde ret katmanini anlatan metin.

        TLS 1.3 TUZAGI: istemci sertifikasi reddedilirse `connect()` 0 doner ve
        `on_connect` HIC ates almaz; yalnizca `on_disconnect` gelir. Bu yuzden karar
        istisnaya degil, on_connect'in SURESINDE gelip gelmedigine baglanir.
        """
        try:
            self._c.connect(HOST, PORT, keepalive=30)
        except ssl.SSLError as exc:
            return f"TLS el sikismasi reddedildi: {exc.__class__.__name__}"
        except OSError as exc:
            return f"soket acilamadi: {exc}"
        self._c.loop_start()
        son = time.monotonic() + BAGLANTI_ZAMAN_ASIMI_S
        while time.monotonic() < son:
            if self._baglandi is not None:
                break
            time.sleep(0.05)
        if self._baglandi is None:
            return "TLS el sikismasi reddedildi (CONNACK gelmedi; TLS 1.3'te sertifika reddi boyle gorunur)"
        if self._baglandi != 0:
            return f"CONNACK reddi: reason_code {self._baglandi}"
        sok = self._c.socket()
        if sok is not None and hasattr(sok, "version"):
            self.tls_surumu = sok.version() or self.tls_surumu
        return ""

    def yayinla(self, topic: str, nonce: str) -> int:
        """QoS 1 yayin; donus PUBACK reason code. -1 = PUBACK hic gelmedi."""
        yuk = json.dumps({"nonce": nonce, "kaynak": self.kimlik.ad}, ensure_ascii=False)
        bilgi = self._c.publish(topic, yuk, qos=1, retain=False)
        son = time.monotonic() + 10.0
        while time.monotonic() < son:
            if bilgi.mid in self._rc:
                return self._rc[bilgi.mid]
            time.sleep(0.02)
        return -1

    def dur(self) -> None:
        self._c.loop_stop()
        self._c.disconnect()


# ----------------------------------------------------------------------- vakalar


@dataclass
class Vaka:
    baslik: str
    kimlik_adi: str
    topic: str
    #: True = ACL'in izin vermesi bekleniyor.
    beklenen: bool
    #: Bu kimligin yazabildigi VE bir gozlemcinin gordugu topic (pozitif kontrol + bariyer).
    kontrol_topic: str
    sinyaller: dict = field(default_factory=dict)
    karar: str = ""


def vakalari_kur(acl) -> list[Vaka]:
    """Beklenen sutunu scripts/mqtt_acl.py'den gelir — olcum degil, BEKLENTI.

    `kontrol_topic`, o kimligin ACL'de YAZMAYA YETKILI oldugu ve bir gozlemcinin
    gordugu bir topic'tir; sandvicin iki ucunu o olusturur. Panolar icin kendi
    telemetrisi, merkez icin ADM-00001'in komut topic'i.
    """
    pano_kontrol = "gridup/pano/{}/tel"
    merkez_kontrol = "gridup/pano/ADM-00001/cmd"
    ham = [
        ("POZITIF KONTROL — pano kendi telemetrisini yayinlar",
         "ADM-00001", "gridup/pano/ADM-00001/tel", True, pano_kontrol.format("ADM-00001")),
        ("KABUL OLCUTU — pano BASKA panonun telemetrisine yayinlar",
         "ADM-00001", "gridup/pano/ADM-00002/tel", False, pano_kontrol.format("ADM-00001")),
        ("KONTROL GRUBU — ayni topic, sahibi yayinlarsa ULASIR",
         "ADM-00002", "gridup/pano/ADM-00002/tel", True, pano_kontrol.format("ADM-00002")),
        ("pano kendi komut topic'ine YAZAMAZ (komut yonu merkezden kenara)",
         "ADM-00001", "gridup/pano/ADM-00001/cmd", False, pano_kontrol.format("ADM-00001")),
        ("merkez pano telemetrisine YAZAMAZ (uydurma olcum sokamaz)",
         "gridup-backend", "gridup/pano/ADM-00001/tel", False, merkez_kontrol),
        ("merkez komut yazar", "gridup-backend", merkez_kontrol, True, merkez_kontrol),
        ("merkez kendi adina telemetri YAZAMAZ (ACL'deki deny satiri)",
         "gridup-backend", "gridup/pano/gridup-backend/tel", False, merkez_kontrol),
    ]
    vakalar = []
    for baslik, kim, topic, beklenen, kontrol in ham:
        hesaplanan = acl.allows(kim, "write", topic)
        if hesaplanan != beklenen:
            raise Kararsiz(
                f"vaka tablosu ACL ile celisiyor: {kim} write {topic} -> mqtt_acl.py {hesaplanan}, "
                f"tabloda {beklenen}. Once hangisinin yanlis oldugunu bulun."
            )
        if not acl.allows(kim, "write", kontrol):
            raise Kararsiz(f"pozitif kontrol topic'i {kim} icin ACL'de yetkili degil: {kontrol}")
        vakalar.append(Vaka(baslik, kim, topic, beklenen, kontrol_topic=kontrol))
    return vakalar


# ----------------------------------------------------------------------- olcum


def broker_logunu_al(satirdan_sonra: int) -> list[str]:
    sonuc = kabuk("docker", "logs", KONTEYNER)
    return sonuc.stdout.splitlines()[satirdan_sonra:]


def bagimsiz_olcum(kimlik: Kimlik, topic: str) -> str:
    """Ikinci, paho'dan BAGIMSIZ olcum: broker imajinin kendi mosquitto_pub'i.

    Kendi sarmalayicimizin yalan soyleme ihtimalini kapatir. Sertifikalar konteynere
    zaten bagli degil; yalnizca broker/ dizini bagli, bu yuzden merkez ve pano
    sertifikalari stdin ile degil, gecici bir kopya ile verilemez -> bu olcum yalnizca
    broker konteynerinin GORDUGU sertifikalarla yapilabilir. Bunun yerine ayni olcumu
    ayri bir konteynerden, host'taki sertifika dizinini baglayarak yapiyoruz.
    """
    sonuc = kabuk(
        "docker", "run", "--rm", "--network", "host",
        "-v", f"{CERT_DIR}:/certs:ro",
        "eclipse-mosquitto:2.0@sha256:212f89e1eaeb2c322d6441b64396e3346026674db8fa9c27beac293405c32b3c",
        "mosquitto_pub", "-h", HOST, "-p", str(PORT),
        "--cafile", "/certs/ca.crt",
        "--cert", "/certs" + str(Path(kimlik.tls.certfile)).replace(str(CERT_DIR), "").replace("\\", "/"),
        "--key", "/certs" + str(Path(kimlik.tls.keyfile)).replace(str(CERT_DIR), "").replace("\\", "/"),
        "-V", "5", "-q", "1", "-d", "-t", topic, "-m", '{"bagimsiz":1}',
    )
    ciktilar = (sonuc.stdout + sonuc.stderr).splitlines()
    for satir in ciktilar:
        if "PUBACK" in satir and "RC:" in satir:
            return satir.strip()
    if sonuc.returncode != 0:
        return f"baglanti kurulamadi (cikis {sonuc.returncode})"
    return "(PUBACK satiri bulunamadi)"


def _gozlemci_sec(topic: str, tel: Gozlemci, cmd: KomutGozlemci):
    """Topic'i hangi gozlemci dinliyor? None = kimse (o sinyal OLCULMEZ, uydurulmaz)."""
    if topic.endswith(("/tel", "/evt")):
        return tel
    if topic == cmd.topic:
        return cmd
    return None


def vakalari_olc(vakalar: list[Vaka], kimlikler: dict[str, Kimlik], tel_gozlemci: Gozlemci,
                 cmd_gozlemci: KomutGozlemci, kosu: str, *, bagimsiz: bool) -> None:
    log_basi = len(kabuk("docker", "logs", KONTEYNER).stdout.splitlines())

    for sira, vaka in enumerate(vakalar):
        kimlik = kimlikler[vaka.kimlik_adi]
        yayinci = Yayinci(kimlik, f"{kosu}-{sira}")
        ret = yayinci.bagla()
        if ret:
            vaka.karar = "KARARSIZ"
            vaka.sinyaller = {"baglanti": ret}
            yayinci.dur()
            continue

        kontrol_gozlemci = _gozlemci_sec(vaka.kontrol_topic, tel_gozlemci, cmd_gozlemci)
        hedef_gozlemci = _gozlemci_sec(vaka.topic, tel_gozlemci, cmd_gozlemci)

        # SANDVIC: kontrol(A) -> hedef(X) -> kontrol(B). Broker ayni istemcinin ayni
        # QoS akisinda sirayi korur; gozlemci B'yi aldigi anda X'in HIC gelmeyecegi
        # kesinlesir. Sabit `sleep` ile "gelmedi" karari verilmez.
        nonce_a, nonce_x, nonce_b = (uuid.uuid4().hex for _ in range(3))
        rc_a = yayinci.yayinla(vaka.kontrol_topic, nonce_a)
        rc_x = yayinci.yayinla(vaka.topic, nonce_x)
        rc_b = yayinci.yayinla(vaka.kontrol_topic, nonce_b)

        sinyaller: dict = {
            "tls": yayinci.tls_surumu,
            "puback_rc": rc_x,
            "client_id": yayinci.client_id,
            "kontrol_topic": vaka.kontrol_topic,
            "kontrol_puback_rc": (rc_a, rc_b),
        }
        if kontrol_gozlemci is not None:
            sinyaller["bariyer_geldi"] = kontrol_gozlemci.bariyeri_bekle(nonce_b)
            sinyaller["pozitif_kontrol"] = kontrol_gozlemci.nonce_var_mi(nonce_a)
        if hedef_gozlemci is not None:
            # Kontrol topic'i hedefle AYNIYSA nonce_x zaten sandvicin ortasidir.
            sinyaller["hedef_ulasti"] = hedef_gozlemci.nonce_var_mi(nonce_x)
        yayinci.dur()

        if bagimsiz:
            sinyaller["mosquitto_pub"] = bagimsiz_olcum(kimlik, vaka.topic)

        # TAM JETON eslesmesi: alt dize aramasi vaka sayisi 10'u gecince "...-1" ile
        # "...-10" kimliklerini karistirir ve log satirini YANLIS vakaya atfeder.
        log = [
            satir for satir in broker_logunu_al(log_basi)
            if "Denied" in satir and yayinci.client_id in satir.split()
        ]
        sinyaller["broker_logu"] = log[0].strip() if log else ""
        vaka.sinyaller = sinyaller
        vaka.karar = _karar(vaka, sinyaller)


def _karar(vaka: Vaka, s: dict) -> str:
    """Uc sinyali birlestirir. Ayrisma = KIRMIZI, cunku 'muhtemelen reddedildi' yazilmaz."""
    rc = s["puback_rc"]
    if rc == -1:
        return "KARARSIZ"  # PUBACK hic gelmedi

    # POZITIF KONTROL: ayni baglanti uzerinden yetkili bir yayin gercekten ulasmadan
    # hicbir ret iddiasi raporlanmaz. Broker kapali / TLS patlamis / ACL hic yuklenmemis
    # durumlarinda bu kontrol duser ve sonuc PASS degil KARARSIZ olur.
    if not all(kod in KABUL_EDILEN_RC for kod in s["kontrol_puback_rc"]):
        return "KARARSIZ"
    if "bariyer_geldi" in s and not (s["bariyer_geldi"] and s["pozitif_kontrol"]):
        return "KARARSIZ"

    puback_reddetti = rc == RC_YETKISIZ
    if not (puback_reddetti or rc in KABUL_EDILEN_RC):
        return "KARARSIZ"  # beklenmeyen reason code

    sinyal_reddetti = [puback_reddetti]
    if "hedef_ulasti" in s:
        sinyal_reddetti.append(not s["hedef_ulasti"])
    # Log seviyesi "all" oldugu icin ret satiri BEKLENIR; ret varken log yoksa sinyaller
    # ayrismistir ve bu bir KIRMIZIDIR (satirin adi degismis olabilir).
    sinyal_reddetti.append(bool(s.get("broker_logu")))
    # Paho'dan BAGIMSIZ ikinci olcum (broker imajinin kendi mosquitto_pub'i) da karara
    # GIRER. Ilk yazimda yalnizca raporda basiliyordu: paho ile TAM TERS sonuc verse bile
    # kosu yesil kaliyordu (olculdu) — yani "kendi sarmalayicimizin yalan soyleme
    # ihtimalini kapatir" cumlesi kendini kapatmiyordu.
    bagimsiz = s.get("mosquitto_pub")
    if bagimsiz:
        if f"RC:{RC_YETKISIZ}" in bagimsiz:
            sinyal_reddetti.append(True)
        elif any(f"RC:{kod}" in bagimsiz for kod in KABUL_EDILEN_RC):
            sinyal_reddetti.append(False)
        else:
            return "KARARSIZ"  # bagimsiz olcum sonuc uretemedi

    if len(set(sinyal_reddetti)) != 1:
        return "SINYALLER AYRISTI"
    olculen_ret = sinyal_reddetti[0]
    return "GECTI" if olculen_ret != vaka.beklenen else "KALDI"


# ----------------------------------------------------------------------- okuma vakasi


def okuma_vakasi(kosu: str) -> dict:
    """Pano BASKA panonun telemetrisine abone olabilir mi?

    Olculen davranis: mosquitto 2.0.22 SUBACK'te reddetmez, "Granted QoS 1" doner —
    ama mesaji TESLIM ETMEZ. Yani abonelik reddini SUBACK'ten okumaya guvenilemez;
    kanit teslim edilmemesidir. Bu, kabul olcutunun disinda ama olcmeye degen bir
    gercektir (ele gecirilen pano komsusunun verisini okuyabilir mi?).

    POZITIF KONTROL ZORUNLU — ve ilk yazimda YOKTU: `main()` yalnizca teslim sayisinin
    0 olmasina bakiyordu, dolayisiyla ABONELIK HIC KURULMASA da vaka geciyordu (olculdu:
    subscribe no-op'a cevrildiginde sonuc yine "gecti"). Artik ADM-00001 ayni kosuda
    KENDI KOMUT topic'ine de abone olur ve merkezin oraya yazdigi mesaji ALMALIDIR;
    almazsa sonuc "komsusunu okuyamiyor" degil, "olcum yapilamadi"dir.
    """
    pano1, pano2 = Kimlik.pano("ADM-00001"), Kimlik.pano("ADM-00002")
    gelen: list[dict] = []
    suback: list[int] = []
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"gridup-acltest-okuma-{kosu}", protocol=mqtt.MQTTv5)
    c.tls_set(ca_certs=pano1.tls.ca, certfile=pano1.tls.certfile, keyfile=pano1.tls.keyfile)

    def _al(cl, u, m):
        try:
            gelen.append(json.loads(m.payload))
        except ValueError:
            pass

    c.on_message = _al
    c.on_subscribe = lambda cl, u, mid, rcs, props: suback.extend(int(getattr(r, "value", r)) for r in rcs)
    c.connect(HOST, PORT, keepalive=30)
    c.loop_start()
    # Ikisine birden abone: komsusunun telemetrisi (okuyamamali) + KENDI KOMUT topic'i.
    # Pozitif kontrol neden `cmd`? Cunku ACL panoya kendi TELEMETRISINI okuma yetkisi de
    # VERMEZ — en az yetki: cihaz telemetriyi yayinlar, okumaz. Panonun okuyabildigi tek
    # topic kendi komut topic'idir (`pattern read gridup/pano/%u/cmd`), oraya da yalnizca
    # merkez yazabilir. Ilk yazimda pozitif kontrol kendi telemetrisine kurulmustu ve
    # dogru sebeple dustu; olcum bunu yakaladi.
    c.subscribe([("gridup/pano/ADM-00002/tel", 1), ("gridup/pano/ADM-00001/cmd", 1)])
    son = time.monotonic() + BAGLANTI_ZAMAN_ASIMI_S
    while time.monotonic() < son and len(suback) < 2:
        time.sleep(0.05)

    komsu_nonce, kendi_nonce = uuid.uuid4().hex, uuid.uuid4().hex
    komsu_yayinci = Yayinci(pano2, f"{kosu}-okuma-komsu")
    rc = komsu_yayinci.yayinla("gridup/pano/ADM-00002/tel", komsu_nonce) if not komsu_yayinci.bagla() else -1
    komsu_yayinci.dur()
    merkez_yayinci = Yayinci(Kimlik.merkez(), f"{kosu}-okuma-kendi")
    kendi_rc = merkez_yayinci.yayinla("gridup/pano/ADM-00001/cmd", kendi_nonce) if not merkez_yayinci.bagla() else -1
    merkez_yayinci.dur()

    # Bariyer: kendi mesajimiz geldiginde komsununkinin HIC gelmeyecegi kesinlesir.
    son = time.monotonic() + BARIYER_ZAMAN_ASIMI_S
    while time.monotonic() < son:
        if any(y.get("nonce") == kendi_nonce for y in gelen):
            break
        time.sleep(0.05)
    c.loop_stop()
    c.disconnect()
    return {
        "suback": suback,
        "yayin_rc": rc,
        "kendi_yayin_rc": kendi_rc,
        "pozitif_kontrol": any(y.get("nonce") == kendi_nonce for y in gelen),
        "teslim_edilen": sum(1 for y in gelen if y.get("nonce") == komsu_nonce),
    }


# ----------------------------------------------------------------------- baglanti vakalari


def baglanti_vakalari(gecici: Path, gecerli: Kimlik, kosu: str) -> list[tuple[str, str]]:
    """Sertifikasiz ve YABANCI CA imzali baglantilarin reddini olcer.

    POZITIF KONTROL ZORUNLU — ve ilk yazimda YOKTU. `except (ssl.SSLError, OSError)`
    her hatayi "REDDEDILDI" sayiyordu; broker tamamen kapaliyken ya da hic dinleyici
    olmayan bir porta baglanildiginda da "2/2 baglanti vakasi gecti" yaziyordu (olculdu:
    ConnectionRefusedError -> "REDDEDILDI"). Yani bu eksen bir olcum degil, bir baglanti
    hatasi sayaciydi. Artik once GECERLI bir kimligin baglanabildigi gorulur; baglanamazsa
    hicbir ret iddiasi raporlanmaz.
    """
    sonuclar: list[tuple[str, str]] = []

    onculu = Yayinci(gecerli, f"{kosu}-baglanti-onculu")
    ret = onculu.bagla()
    onculu.dur()
    if ret:
        raise Kararsiz(
            f"baglanti vakalari icin pozitif kontrol gecmedi ({gecerli.ad} baglanamadi: {ret}). "
            "Broker ayakta degilse 'sertifikasiz baglanti reddedildi' sonucu anlamsizdir."
        )

    sertifikasiz = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    sertifikasiz.tls_set(ca_certs=str(CERT_DIR / "ca.crt"))
    baglandi: list[int] = []
    sertifikasiz.on_connect = lambda cl, u, f, rc, p: baglandi.append(int(getattr(rc, "value", rc)))
    try:
        sertifikasiz.connect(HOST, PORT, keepalive=10)
        sertifikasiz.loop_start()
        time.sleep(4.0)
        sertifikasiz.loop_stop()
        sertifikasiz.disconnect()
    except (ssl.SSLError, OSError) as exc:
        sonuclar.append(("sertifikasiz baglanti", f"REDDEDILDI — {exc.__class__.__name__}"))
    else:
        sonuclar.append((
            "sertifikasiz baglanti",
            "REDDEDILDI — CONNACK gelmedi (TLS 1.3)" if not baglandi else f"KABUL EDILDI (reason_code {baglandi[0]}) !!!",
        ))

    # Yabanci CA: deploy/certs'e DEGIL, gecici dizine uretilir (repo kirletilmez).
    ortam = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    adimlar = [
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-sha256", "-days", "2", "-nodes",
         "-keyout", "sahte-ca.key", "-out", "sahte-ca.crt", "-subj", "/CN=sahte-ca"],
        ["openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", "sahte.key", "-out", "sahte.csr",
         "-subj", "/CN=ADM-00001"],
        ["openssl", "x509", "-req", "-in", "sahte.csr", "-CA", "sahte-ca.crt", "-CAkey", "sahte-ca.key",
         "-CAcreateserial", "-out", "sahte.crt", "-days", "2", "-sha256"],
    ]
    for adim in adimlar:
        if subprocess.run(adim, cwd=gecici, capture_output=True, env=ortam).returncode != 0:
            sonuclar.append(("yabanci CA sertifikasi", "OLCULEMEDI (openssl)"))
            return sonuclar

    sahte = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    sahte.tls_set(ca_certs=str(CERT_DIR / "ca.crt"), certfile=str(gecici / "sahte.crt"),
                  keyfile=str(gecici / "sahte.key"))
    sahte_baglandi: list[int] = []
    sahte.on_connect = lambda cl, u, f, rc, p: sahte_baglandi.append(int(getattr(rc, "value", rc)))
    try:
        sahte.connect(HOST, PORT, keepalive=10)
        sahte.loop_start()
        time.sleep(4.0)
        sahte.loop_stop()
        sahte.disconnect()
    except (ssl.SSLError, OSError) as exc:
        sonuclar.append(("yabanci CA imzali CN=ADM-00001", f"REDDEDILDI — {exc.__class__.__name__}"))
    else:
        sonuclar.append((
            "yabanci CA imzali CN=ADM-00001",
            "REDDEDILDI — CONNACK gelmedi (TLS 1.3)" if not sahte_baglandi
            else f"KABUL EDILDI (reason_code {sahte_baglandi[0]}) !!!",
        ))
    return sonuclar


# ----------------------------------------------------------------------- mutasyon


def _acl_geri_yukle(sebep: str) -> None:
    """Yedekten BAYT BAYT geri yukler. Yedek yoksa sessizce gecer."""
    if not ACL_YEDEK.exists():
        return
    ACL_PATH.write_bytes(ACL_YEDEK.read_bytes())
    ACL_YEDEK.unlink(missing_ok=True)
    kabuk("docker", "kill", "-s", "HUP", KONTEYNER)
    print(f"\n  deploy/mosquitto.acl yedekten geri yuklendi ({sebep}).", file=sys.stderr)


def yarim_kalmis_mutasyonu_topla() -> str | None:
    """Onceki bir kosu oldurulmusse ACL GEVSEK kalmis olabilir; acilista toparla.

    Gevsek kural (`pattern write gridup/pano/+/tel`) her cihazin her panonun topic'ine
    yazabilmesi demektir ve SIGHUP zaten gonderilmis oldugu icin CALISAN broker da onu
    yuklu tasir. Bu yuzden temizlik bir sonraki kosunun ILK isi olmali.
    """
    if not ACL_YEDEK.exists():
        return None
    _acl_geri_yukle("onceki kosu yarim kalmis")
    return "onceki kosudan kalan gevsek ACL geri yuklendi"


def mutasyon_kosusu(kimlikler: dict[str, Kimlik], gozlemci: Gozlemci, kosu: str) -> str:
    """ACL kuralini gecici olarak gevsetir ve ayni vakanin IZINLI olculdugunu gosterir.

    Bu olmadan "negatif test gecti" cumlesi hicbir sey ifade etmez: ACL hic yuklenmemis
    olsaydi da butun negatifler gecerdi.

    GERI YUKLEME UC KATMANLI — cunku try/finally TEK BASINA YETMEZ (olculdu):
      1. Mutasyondan ONCE dosyanin BAYT KOPYASI yedege yazilir. Bellekteki bir dize
         yeterli degildi: surec `terminate()` / SIGTERM ile oldurulurse `finally`
         HIC KOSMAZ ve ACL gevsek kalir (3/3 denemede olculdu; Ctrl-C dogru calisiyordu).
      2. SIGTERM (ve Windows'ta SIGBREAK) yakalanir, yedekten geri yuklenir, cikilir.
      3. Bir sonraki kosu acilista yedegi gorurse toparlar (yarim_kalmis_mutasyonu_topla).
    Okuma/yazma BAYT duzeyindedir: `write_text` Windows'ta LF'i CRLF'e cevirir ve
    `.gitattributes` `eol=lf` dedigi icin bu dosyanin satir sonlarini sessizce degistirirdi;
    `read_text` de bunu normalize ettigi icin ozet karsilastirmasi farki GOREMEZDI (olculdu).
    """
    ozgun = ACL_PATH.read_bytes()
    gevsek = ozgun.replace(b"pattern write gridup/pano/%u/tel", b"pattern write gridup/pano/+/tel")
    if gevsek == ozgun:
        return "ATLANDI (mutasyon satiri bulunamadi)"
    try:
        ACL_YEDEK.write_bytes(ozgun)
        ACL_PATH.write_bytes(gevsek)
        if kabuk("docker", "kill", "-s", "HUP", KONTEYNER).returncode != 0:
            return "ATLANDI (SIGHUP gonderilemedi)"
        time.sleep(1.5)
        yayinci = Yayinci(kimlikler["ADM-00001"], f"{kosu}-mutasyon")
        if yayinci.bagla():
            return "ATLANDI (mutasyon kosusunda baglanti kurulamadi)"
        nonce = uuid.uuid4().hex
        rc = yayinci.yayinla("gridup/pano/ADM-00002/tel", nonce)
        yayinci.dur()
        ulasti = gozlemci.bariyeri_bekle(nonce)
        if rc in KABUL_EDILEN_RC and ulasti:
            return f"GECTI — kural gevsetilince AYNI yayin kabul edildi (PUBACK rc {rc}, mesaj ulasti)"
        return f"KALDI — kural gevsetildigi halde ret surdu (PUBACK rc {rc}, ulasti={ulasti})"
    finally:
        ACL_PATH.write_bytes(ozgun)
        ACL_YEDEK.unlink(missing_ok=True)
        kabuk("docker", "kill", "-s", "HUP", KONTEYNER)
        time.sleep(1.5)
        if ACL_PATH.read_bytes() != ozgun:
            print(f"\n  !!! deploy/mosquitto.acl GERI YUKLENEMEDI — elle duzeltin: "
                  f"25. satir `pattern write gridup/pano/%u/tel` olmali", file=sys.stderr)


# ----------------------------------------------------------------------- rapor


def rapor(ortam: dict, vakalar: list[Vaka], baglanti: list[tuple[str, str]], okuma: dict,
          mutasyon: str, kimlikler: dict[str, Kimlik]) -> None:
    print("\n" + "=" * 100)
    print("F-27 — mTLS ve cihaz basina topic yetkisi: CANLI OLCUM")
    print("=" * 100)
    print(f"  broker imaji : {ortam['imaj']}")
    print(f"  surum        : {ortam['mosquitto']}")
    tls_surumleri = {v.sinyaller.get("tls") for v in vakalar if v.sinyaller.get("tls")}
    print(f"  TLS          : {', '.join(sorted(s for s in tls_surumleri if s)) or '(olculemedi)'}")
    print("  kimlikler    :")
    for ad, kimlik in kimlikler.items():
        print(f"    {ad:<16} {parmak_izi(kimlik.crt)}")

    print("\n-- Yayin yetkisi (beklenen: mqtt_acl.py, KARAR: canli broker) " + "-" * 38)
    print(f"  {'vaka':<58} {'beklenen':<10} {'PUBACK':<8} {'ulasti':<7} {'log':<4} karar")
    for vaka in vakalar:
        s = vaka.sinyaller
        rc = s.get("puback_rc", "-")
        ulasti = "-" if "hedef_ulasti" not in s else ("evet" if s["hedef_ulasti"] else "hayir")
        log = "var" if s.get("broker_logu") else "-"
        print(f"  {vaka.baslik[:58]:<58} {'IZIN' if vaka.beklenen else 'RET':<10} {str(rc):<8} {ulasti:<7} {log:<4} {vaka.karar}")

    print("\n-- Uc sinyalin ham hali (kabul olcutu vakasi) " + "-" * 54)
    olcut = vakalar[1]
    for anahtar, deger in olcut.sinyaller.items():
        print(f"  {anahtar:<18} {deger}")

    print("\n-- Baglanti katmani " + "-" * 79)
    for ad, sonuc in baglanti:
        print(f"  {ad:<40} {sonuc}")

    print("\n-- Okuma yetkisi (kabul olcutunun disinda, olculdu) " + "-" * 48)
    print(f"  pozitif kontrol (merkezin yazdigi kendi komutunu okuyabiliyor mu): {okuma['pozitif_kontrol']} "
          f"(PUBACK {okuma['kendi_yayin_rc']})")
    print(f"  ADM-00001 -> ADM-00002/tel aboneligi: SUBACK {okuma['suback']}, "
          f"sahibinin yayini PUBACK {okuma['yayin_rc']}, ADM-00001'e teslim edilen mesaj: {okuma['teslim_edilen']}")

    print("\n-- Mutasyon kosusu (test kirmiziya donebiliyor mu?) " + "-" * 48)
    print(f"  {mutasyon}")


def _kilidi_al() -> None:
    """Es zamanli iki kosuyu engeller.

    ACL dosyasi ve broker PAYLASILAN KURESEL DURUMDUR. Iki kosu ust uste bindiginde
    biri digerinin ~1,5 saniyelik mutasyon penceresine denk gelir; olculdu: bir kosu
    "mutasyon satiri bulunamadi" diye SAHTE KIRMIZI dondu ve daha kotu bir siralamada
    gevsek metin "ozgun" diye geri yazilabilirdi.
    """
    try:
        fd = os.open(KILIT, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise Kararsiz(
            f"baska bir olcum kosuyor gibi gorunuyor ({KILIT}). Kosu yoksa dosyayi silin."
        ) from None
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mutasyon-yok", action="store_true", help="mutasyon kosusunu atla (hizli)")
    parser.add_argument("--bagimsiz-yok", action="store_true", help="mosquitto_pub ile ikinci olcumu atla")
    args = parser.parse_args(argv)

    kosu = uuid.uuid4().hex[:8]
    kimlikler = {
        "ADM-00001": Kimlik.pano("ADM-00001"),
        "ADM-00002": Kimlik.pano("ADM-00002"),
        "gridup-backend": Kimlik.merkez(),
    }

    # SIGTERM `finally` blogunu KOSTURMAZ (olculdu: 3/3 denemede ACL gevsek kaldi).
    # IDE'nin durdur dugmesi, taskkill, CI iptali hep bu yoldan gelir.
    def _sinyal(signum, frame):
        _acl_geri_yukle(f"sinyal {signum}")
        KILIT.unlink(missing_ok=True)
        sys.exit(2)

    for ad in ("SIGTERM", "SIGBREAK", "SIGINT"):
        if hasattr(signal, ad):
            try:
                signal.signal(getattr(signal, ad), _sinyal)
            except (ValueError, OSError):
                pass  # ana thread disi ya da desteklenmeyen platform

    gozlemci = None
    cmd_gozlemci = None
    kilit_alindi = False
    try:
        _kilidi_al()
        kilit_alindi = True
        toparlandi = yarim_kalmis_mutasyonu_topla()
        ortam = on_ucus(list(kimlikler.values()))
        try:
            acl = load_acl(ACL_PATH)
        except Exception as exc:
            # ACL ayristirilamiyorsa BROKER DA ACL'I DUSURUR ve FAIL-OPEN olur: her cihaz
            # her panonun topic'ine yazabilir hale gelir (olculdu, SIGHUP sonrasi RC:0).
            # Bu yuzden sessiz bir traceback degil, en yuksek sesli uyari basilir.
            raise Kararsiz(
                f"deploy/mosquitto.acl AYRISTIRILAMIYOR: {exc}\n"
                "       !!! BU BIR FAIL-OPEN RISKIDIR: mosquitto bozuk bir ACL dosyasini\n"
                "           yuklemez ve YETKILENDIRMEYI TAMAMEN DUSURUR — o anda her cihaz\n"
                "           her panonun topic'ine yazabilir. Once ACL dosyasini duzeltin."
            ) from None
        vakalar = vakalari_kur(acl)
        gozlemci = Gozlemci(kimlikler["gridup-backend"], kosu)
        gozlemci.basla()
        cmd_gozlemci = KomutGozlemci(kimlikler["ADM-00001"], kosu)
        cmd_gozlemci.basla()
        vakalari_olc(vakalar, kimlikler, gozlemci, cmd_gozlemci, kosu, bagimsiz=not args.bagimsiz_yok)
        okuma = okuma_vakasi(kosu)
        gecici = Path(os.environ.get("TEMP", "/tmp")) / f"gridup-mtls-{kosu}"
        gecici.mkdir(parents=True, exist_ok=True)
        baglanti = baglanti_vakalari(gecici, kimlikler["ADM-00001"], kosu)
        mutasyon = "ATLANDI (--mutasyon-yok)" if args.mutasyon_yok else mutasyon_kosusu(kimlikler, gozlemci, kosu)
        # KOSU SONU CANLILIK DENETIMI: on_ucus yalnizca BASTA bakiyordu, dolayisiyla
        # broker olcum ORTASINDA olduruldugunde kopan el sikismalari "REDDEDILDI" diye
        # okunuyor ve kosu YESIL bitiyordu (olculdu: docker stop -> 2/2, cikis 0).
        son_kontrol = Yayinci(kimlikler["ADM-00001"], f"{kosu}-son")
        son_ret = son_kontrol.bagla()
        son_kontrol.dur()
        if son_ret:
            raise Kararsiz(
                f"kosu SONUNDA broker'a baglanilamadi ({son_ret}). Olcum sirasinda broker "
                "durmus olabilir; kopan el sikismalari 'reddedildi' gibi okunur."
            )
    except Kararsiz as exc:
        print(f"\nKARARSIZ — olcum yapilamadi: {exc}", file=sys.stderr)
        return 2
    finally:
        if gozlemci is not None:
            gozlemci.dur()
        if cmd_gozlemci is not None:
            cmd_gozlemci.dur()
        if kilit_alindi:
            KILIT.unlink(missing_ok=True)

    rapor(ortam, vakalar, baglanti, okuma, mutasyon, kimlikler)
    if toparlandi:
        print(f"\n  NOT: {toparlandi}")

    # KARARSIZ bir vaka "kaldi" DEGILDIR: cikis kodu sozlesmesi 1'i "vaka ayristi",
    # 2'yi "olcum yapilamadi" diye ayirir. Ikisini karistirmak, gercek bir yetki
    # gerilemesini "altyapi flake'i" diye triyaj ettirirdi.
    kararsiz = [v for v in vakalar if v.karar == "KARARSIZ"]
    kaldi = [v for v in vakalar if v.karar not in ("GECTI", "KARARSIZ")]
    kabul_edilmeyen_baglanti = [ad for ad, sonuc in baglanti if not sonuc.startswith("REDDEDILDI")]
    mutasyon_kaldi = not (args.mutasyon_yok or mutasyon.startswith("GECTI"))
    okuma_kaldi = okuma["teslim_edilen"] != 0
    okuma_kararsiz = not okuma["pozitif_kontrol"] or len(okuma["suback"]) < 2

    print("\n" + "=" * 100)
    if kararsiz or okuma_kararsiz:
        for vaka in kararsiz:
            print(f"  KARARSIZ: {vaka.baslik} -> {vaka.sinyaller}", file=sys.stderr)
        if okuma_kararsiz:
            print(f"  KARARSIZ: okuma vakasinin pozitif kontrolu gecmedi -> {okuma}", file=sys.stderr)
        print("\n  SONUC: OLCUM YAPILAMADI — yukaridaki vakalarda pozitif kontrol gecmedi.", file=sys.stderr)
        return 2
    if kaldi or kabul_edilmeyen_baglanti or mutasyon_kaldi or okuma_kaldi:
        for vaka in kaldi:
            print(f"  KALDI: {vaka.baslik} -> {vaka.karar} {vaka.sinyaller}")
        for ad in kabul_edilmeyen_baglanti:
            print(f"  KALDI: {ad} reddedilmedi")
        if mutasyon_kaldi:
            print(f"  KALDI: mutasyon kosusu -> {mutasyon}")
        if okuma_kaldi:
            print(f"  KALDI: pano komsusunun {okuma['teslim_edilen']} mesajini okudu")
        print(f"\n  SONUC: {len(vakalar) - len(kaldi)}/{len(vakalar)} yayin vakasi gecti, EN AZ BIR KONTROL KALDI")
        return 1
    print(f"  SONUC: {len(vakalar)}/{len(vakalar)} yayin vakasi, {len(baglanti)}/{len(baglanti)} baglanti vakasi, "
          "okuma yetkisi ve mutasyon kosusu — hepsi beklendigi gibi olculdu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
