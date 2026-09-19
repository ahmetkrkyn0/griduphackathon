"""MQTT/TLS ayarlari ve merkez istemcisinin mTLS yolu (F-27).

Buradaki testler AYARLARIN ve KOD YOLUNUN dogrulugunu kilitler: hangi ortam degiskeni
kombinasyonunda TLS acilir, paho'ya ne verilir, /health ne soyler.

YETKILENDIRMENIN KENDISI BURADA OLCULMEZ. "Bir panonun sertifikasiyla baska bir panonun
topic'ine yayin reddedilir" iddiasinin kaniti canli olcumdedir: scripts/mtls_yetki_testi.py.

Testlerin cogu, yanlis yapilandirmanin SESSIZ KALMAMASI uzerine. Uc olculmus tuzak var:
  * compose'daki `${MQTT_TLS_CA:-}` her zaman TANIMLI ve BOS bir dize uretir, None degil;
  * `tls_set(ca_certs="")` paho'da OSError atar (backend acilista coker, sonsuz restart);
  * `tls_set(None, None, None)` HIC hata vermez ve TLS'i sistem guven deposuyla ACAR
    (backend 1883'e TLS el sikismasi dener, hata ag thread'inde kalir, /health "ok" der).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import MQTT_TLS_ENV, MqttTls, Settings, mqtt_tls_from_env
from app.ingest import MqttSubscriber
from app.main import create_app
from fakes import MemoryStore
from helpers import CONTRACTS_DIR, Clock, utc

CA, CERT, KEY = "/certs/ca.crt", "/certs/backend/gridup-backend.crt", "/certs/backend/gridup-backend.key"


@pytest.fixture
def temiz_ortam(monkeypatch):
    for ad in MQTT_TLS_ENV:
        monkeypatch.delenv(ad, raising=False)
    return monkeypatch


class FakePahoClient:
    """paho.mqtt.client.Client'in MqttSubscriber'in kullandigi yuzeyi + tls_set."""

    def __init__(self) -> None:
        self.on_connect = None
        self.on_message = None
        self.on_disconnect = None
        self.tls_cagrilari: list[dict] = []

    def tls_set(self, **kwargs) -> None:
        self.tls_cagrilari.append(kwargs)

    def subscribe(self, topics):
        return (0, 1)

    def publish(self, topic, payload=None, qos=0, retain=False):
        return SimpleNamespace(rc=0)


# ------------------------------------------------------------------ ayar okuma


def test_uc_degisken_de_tanimsizsa_tls_kapalidir(temiz_ortam):
    """Varsayilan demo yolu: 1883, anonim. F-27 buna DOKUNMAZ."""
    assert mqtt_tls_from_env() is None


def test_uc_degisken_de_BOS_DIZE_ise_tls_kapalidir(temiz_ortam):
    """En kritik vaka: compose `${MQTT_TLS_CA:-}` yazdiginda degisken TANIMLI ve BOS gelir.

    Kapi `is not None` ile kurulsaydi bos dize TLS'i acmaya calisir, paho OSError atar
    ve backend acilista coker; `unless-stopped` onu sonsuz yeniden baslatirdi.
    """
    for ad in MQTT_TLS_ENV:
        temiz_ortam.setenv(ad, "")
    assert mqtt_tls_from_env() is None


def test_ucu_de_doluysa_yollar_aynen_tasinir(temiz_ortam):
    for ad, deger in zip(MQTT_TLS_ENV, (CA, CERT, KEY)):
        temiz_ortam.setenv(ad, deger)
    assert mqtt_tls_from_env() == MqttTls(ca=CA, certfile=CERT, keyfile=KEY)


def test_bosluk_kirpilir(temiz_ortam):
    """.env dosyasinda satir sonu boslugu kalmis bir yol sessizce FileNotFound uretmesin."""
    for ad, deger in zip(MQTT_TLS_ENV, (f"  {CA}  ", CERT, KEY)):
        temiz_ortam.setenv(ad, deger)
    assert mqtt_tls_from_env().ca == CA


@pytest.mark.parametrize("eksik", MQTT_TLS_ENV)
def test_yarim_yapilandirma_acilista_yuksek_sesle_olur(temiz_ortam, eksik):
    """Ucunden biri bos ise ValueError. Sessiz kalsaydi operator TLS actigini sanirdi."""
    for ad, deger in zip(MQTT_TLS_ENV, (CA, CERT, KEY)):
        temiz_ortam.setenv(ad, "" if ad == eksik else deger)
    with pytest.raises(ValueError) as hata:
        mqtt_tls_from_env()
    assert eksik in str(hata.value)


def test_settings_from_env_tls_alanini_tasir(temiz_ortam):
    for ad, deger in zip(MQTT_TLS_ENV, (CA, CERT, KEY)):
        temiz_ortam.setenv(ad, deger)
    assert Settings.from_env().mqtt_tls == MqttTls(ca=CA, certfile=CERT, keyfile=KEY)


def test_settings_varsayilani_tls_kapali():
    """Yeni alan varsayilani DEGISTIRMEZ: mevcut testler ve duman testi duz yolda kalir."""
    assert Settings(contracts_dir=CONTRACTS_DIR).mqtt_tls is None
    assert Settings(contracts_dir=CONTRACTS_DIR).mqtt_port == 1883


# ------------------------------------------------------------------ istemci yolu


def test_tls_verilmezse_paho_tls_set_HIC_cagrilmaz(contracts):
    """`tls_set(None, None, None)` bile TLS'i ACAR; bu yuzden cagri hic yapilmamali."""
    client = FakePahoClient()
    sub = MqttSubscriber("broker", 1883, contracts, lambda t, p: None, client=client)
    assert client.tls_cagrilari == []
    assert sub.tls_enabled is False


def test_tls_verilirse_uc_yol_da_paho_ya_gecer(contracts):
    client = FakePahoClient()
    sub = MqttSubscriber(
        "broker", 8883, contracts, lambda t, p: None, client=client,
        tls=MqttTls(ca=CA, certfile=CERT, keyfile=KEY),
    )
    assert client.tls_cagrilari == [{"ca_certs": CA, "certfile": CERT, "keyfile": KEY}]
    assert sub.tls_enabled is True


def test_cert_reqs_ve_tls_insecure_acikca_verilmez(contracts):
    """paho'nun varsayilani sunucu sertifikasini DOGRULAR ve hostname'i denetler.

    `cert_reqs=CERT_NONE` yazmak paho'da otomatik olarak tls_insecure_set(True) yapar
    ve dogrulamayi komple kapatirdi. Bu testin amaci o bayragin bir gun "hata aliyoruz"
    diye eklenmesini engellemektir.
    """
    client = FakePahoClient()
    MqttSubscriber(
        "broker", 8883, contracts, lambda t, p: None, client=client,
        tls=MqttTls(ca=CA, certfile=CERT, keyfile=KEY),
    )
    [cagri] = client.tls_cagrilari
    assert "cert_reqs" not in cagri
    assert "tls_insecure" not in cagri


def test_abonelik_ve_yayin_yolu_tls_ile_degismez(contracts):
    """TLS yalnizca TASIMAYI degistirir: topic'ler, QoS ve komut yolu aynen kalir.

    Sozlesme donmus (F-27 tasima katmanidir): mTLS acildiginda abone olunan topic'ler
    ve komut topic'i BIT DUZEYINDE ayni olmali.
    """
    kayitlar: dict[str, FakePahoClient] = {}
    for ad, port, tls in (("duz", 1883, None), ("guvenli", 8883, MqttTls(ca=CA, certfile=CERT, keyfile=KEY))):
        client = FakePahoClient()
        client.abonelikler = []
        client.yayinlar = []
        client.subscribe = lambda topics, c=client: (c.abonelikler.append(list(topics)), (0, 1))[1]
        client.publish = lambda topic, payload=None, qos=0, retain=False, c=client: (
            c.yayinlar.append((topic, qos, retain)),
            SimpleNamespace(rc=0),
        )[1]
        sub = MqttSubscriber("b", port, contracts, lambda t, p: None, client=client, tls=tls)
        client.on_connect(client, None, {}, SimpleNamespace(is_failure=False), None)
        assert sub.publish_command("ADM-00001", "maint_mode", {"on": True}, ts=utc(2026, 9, 18, 10, 0, 0)) is True
        kayitlar[ad] = client

    assert kayitlar["duz"].abonelikler == kayitlar["guvenli"].abonelikler
    assert kayitlar["duz"].yayinlar == kayitlar["guvenli"].yayinlar
    assert kayitlar["guvenli"].yayinlar == [("gridup/pano/ADM-00001/cmd", 1, False)]


# ------------------------------------------------------------------ /health


def test_health_tasimanin_sifresiz_oldugunu_soyler():
    """Sessiz varsayilan olmasin (F-19'daki auth.enabled emsali).

    ingest_enabled=False iken abone hic kurulmaz; /health o durumda da mqtt_tls: false
    demeli — "bilinmiyor" diye bir deger dondurmek okuyucuyu yaniltirdi.
    """
    app = create_app(
        Settings(contracts_dir=CONTRACTS_DIR, ingest_enabled=False, central_detector_enabled=False),
        store=MemoryStore({}),
        clock=Clock(utc(2026, 9, 18, 10, 0, 0)),
    )
    with TestClient(app) as client:
        govde = client.get("/health").json()
    assert govde["mqtt_tls"] is False
    assert govde["mqtt"] is False
