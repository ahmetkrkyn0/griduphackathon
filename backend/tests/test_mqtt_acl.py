"""scripts/mqtt_acl.py — mosquitto ACL semantiginin BIZIM OKUMAMIZ (F-27).

BU DOSYA F-27'NIN KABUL KANITI DEGILDIR ve oyle sunulmamalidir.

Kabul olcutu "broker bir panonun baska panonun topic'ine yayinini REDDEDER"dir ve onu
yalnizca canli olcum kanitlar: scripts/mtls_yetki_testi.py. Buradaki testler yalnizca
"okumamiz kendi icinde tutarli ve deploy/mosquitto.acl bozulmamis" der. Depodaki
diger uretec testleri (test_gen_alarm_doc vb.) bizim urettigimiz bir ciktinin kendi
kurallarina uygunlugunu denetler; burada denetlenmesi gereken UCUNCU BIR TARAFIN
(mosquitto) davranisidir — bu yuzden bu testler emsal DEGIL, yalnizca regresyon kilidi.

Modul ile broker celisirse HAKLI OLAN BROKER'DIR: mtls_yetki_testi.py "beklenen" ve
"olculen" sutunlarini yan yana basar ve ayrisirlarsa 1 ile cikar; duzeltilecek olan
scripts/mqtt_acl.py'dir.

Asagidaki semantik iddialarinin HEPSI konteynerle olculdu (docs/15 §5.1).
"""

from __future__ import annotations

import importlib.util
import sys

import pytest

from helpers import REPO_ROOT

ACL_PATH = REPO_ROOT / "deploy" / "mosquitto.acl"


@pytest.fixture(scope="module")
def acl_modulu():
    spec = importlib.util.spec_from_file_location("mqtt_acl", REPO_ROOT / "scripts" / "mqtt_acl.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["mqtt_acl"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def depo_acl(acl_modulu):
    """Depoda duran gercek ACL dosyasi."""
    return acl_modulu.load_acl(ACL_PATH)


# --------------------------------------------------------------- topic eslesmesi


@pytest.mark.parametrize(
    ("filtre", "topic", "eslesir"),
    [
        ("gridup/pano/ADM-00001/tel", "gridup/pano/ADM-00001/tel", True),
        ("gridup/pano/ADM-00001/tel", "gridup/pano/ADM-00002/tel", False),
        ("gridup/pano/+/tel", "gridup/pano/ADM-00001/tel", True),
        ("gridup/pano/+/tel", "gridup/pano/ADM-00001/evt", False),
        # '+' TEK seviye eslesir: iki seviyeyi yutmaz.
        ("gridup/+/tel", "gridup/pano/ADM-00001/tel", False),
        ("gridup/pano/ADM-00001/#", "gridup/pano/ADM-00001/tel", True),
        ("gridup/pano/ADM-00001/#", "gridup/pano/ADM-00001/a/b/c", True),
        ("gridup/pano/ADM-00001/#", "gridup/pano/ADM-00002/tel", False),
        # Seviye sayisi tutmazsa eslesmez (jokersiz).
        ("gridup/pano/ADM-00001", "gridup/pano/ADM-00001/tel", False),
    ],
)
def test_topic_filtresi_mqtt_kurallarina_uyar(acl_modulu, filtre, topic, eslesir):
    assert acl_modulu.topic_matches(filtre, topic) is eslesir


# --------------------------------------------------------------- semantik


def test_kalip_kurallari_tum_kimliklere_uygulanir(acl_modulu):
    """Semantik 1: `pattern` herkese uygulanir, bir `user` blogu onu gecersiz KILMAZ."""
    acl = acl_modulu.parse_acl(
        "pattern write veri/%u/telemetri\n"
        "user pano1\n"
        "topic write ozel/pano1\n"
    )
    assert acl.allows("pano1", "write", "veri/pano1/telemetri") is True
    assert acl.allows("pano2", "write", "veri/pano2/telemetri") is True
    assert acl.allows("pano2", "write", "ozel/pano1") is False


def test_kullanici_blogu_once_bakilir_ve_kalip_deny_iptal_etmez(acl_modulu):
    """Semantik 2 (olculdu): kullanicinin kendi listesi IZIN URETIRSE kalibi hic gormez."""
    acl = acl_modulu.parse_acl(
        "pattern deny capraz/%u/gizli\n"
        "user pano1\n"
        "topic write capraz/pano1/gizli\n"
    )
    assert acl.allows("pano1", "write", "capraz/pano1/gizli") is True
    # pano2'nin kendi blogu yok: kalip deny devreye girer.
    assert acl.allows("pano2", "write", "capraz/pano2/gizli") is False


def test_eslesen_ama_izin_vermeyen_kural_karar_URETMEZ_kalibi_engellemez(acl_modulu):
    """Semantik 2'nin en kolay gozden kacan sik — ve ilk yazimda YANLIS yazilmisti.

    `topic read .../tel` kurali YAZMA sorusuna eslesir ama yazma VERMEZ. Karar orada
    bitmemeli; kalip listesine dusmelidir. Canli brokerda olculdu: broker IZIN verirken
    modul REDDEDIYORDU. Bu test o ayrismayi bir daha olusmasin diye kilitler.
    """
    acl = acl_modulu.parse_acl(
        "pattern write gridup/pano/%u/tel\n"
        "user ADM-00001\n"
        "topic read gridup/pano/ADM-00001/tel\n"
    )
    assert acl.allows("ADM-00001", "write", "gridup/pano/ADM-00001/tel") is True
    assert acl.allows("ADM-00001", "read", "gridup/pano/ADM-00001/tel") is True


def test_kullaniciya_okuma_istisnasi_eklemek_yazma_cevabini_degistirmez(acl_modulu):
    """Ayni hatanin depodaki ACL uzerinden hali: bir gun eklenecek makul bir satir.

    Bir panoya okuma istisnasi eklemek, o panonun YAZMA yetkisi hakkindaki cevabi
    sessizce tersine cevirmemeli (broker cevirmiyor).
    """
    temel = (ACL_PATH).read_text(encoding="utf-8")
    genisletilmis = acl_modulu.parse_acl(
        temel + "\nuser ADM-00003\ntopic read gridup/pano/ADM-00003/tel\n"
    )
    assert genisletilmis.allows("ADM-00003", "write", "gridup/pano/ADM-00003/tel") is True
    assert genisletilmis.allows("ADM-00003", "write", "gridup/pano/ADM-00001/tel") is False


@pytest.mark.parametrize("topic", ["$SYS/broker/uptime", "$custom/x", "$share/g/a"])
@pytest.mark.parametrize("kural", ["#", "+/x", "+/broker/uptime"])
def test_joker_dolar_ile_baslayan_topici_eslestirmez(acl_modulu, kural, topic):
    """Semantik 9 (olculdu): `topic write #` kurali altinda `$custom/x` yayini RC 135 aldi.

    Modul bunu bilmezse FAZLA yetki rapor eder — yani broker'in reddettigi bir seye
    "izinli" der. Ayrismanin yonu tehlikeli olan yondur.
    """
    acl = acl_modulu.parse_acl(f"user p\ntopic write {kural}\n")
    assert acl.allows("p", "write", topic) is False


def test_dolarli_topic_acikca_yazilmissa_eslesir(acl_modulu):
    """Kisit yalnizca JOKER icindir: acik yazilmis bir $-topic kurali calisir."""
    acl = acl_modulu.parse_acl("user p\ntopic read $SYS/broker/uptime\n")
    assert acl.allows("p", "read", "$SYS/broker/uptime") is True


def test_kullanicinin_kendi_deny_satiri_kalibi_yener(acl_modulu):
    """Semantik 2 tersi (olculdu): istisna ancak o kullanicinin kendi blogunda yazilabilir."""
    acl = acl_modulu.parse_acl(
        "pattern write acik/%u/veri\n"
        "user pano1\n"
        "topic deny acik/pano1/veri\n"
    )
    assert acl.allows("pano1", "write", "acik/pano1/veri") is False
    assert acl.allows("pano2", "write", "acik/pano2/veri") is True


def test_deny_liste_icinde_sira_bagimsiz_kazanir(acl_modulu):
    """Semantik 3 (olculdu): dosya sirasi degistirmez, `deny` izni yener."""
    once_izin = acl_modulu.parse_acl("user p\ntopic readwrite a/#\ntopic deny a/gizli\n")
    once_deny = acl_modulu.parse_acl("user p\ntopic deny a/gizli\ntopic readwrite a/#\n")
    assert once_izin.allows("p", "write", "a/gizli") is False
    assert once_deny.allows("p", "write", "a/gizli") is False
    assert once_izin.allows("p", "write", "a/acik") is True


def test_anonim_istemci_yer_tutuculu_kalibi_eslestiremez(acl_modulu):
    """Semantik 4 (olculdu): kullanici adi yoksa %u hicbir sey eslestirmez."""
    acl = acl_modulu.parse_acl("pattern write veri/%u/x\n")
    assert acl.allows(None, "write", "veri//x") is False
    assert acl.allows(None, "write", "veri/pano1/x") is False


def test_hicbir_kurala_uymayan_topic_reddedilir(acl_modulu):
    """Semantik 5 (olculdu): acl_file tanimliyken varsayilan REDDETMEKTIR."""
    acl = acl_modulu.parse_acl("pattern write veri/%u/x\n")
    assert acl.allows("pano1", "write", "baska/yer") is False
    assert acl.allows("pano1", "read", "baska/yer") is False


def test_user_satirindan_once_gelen_kurallar_yalnizca_anonimedir(acl_modulu):
    """Semantik 6 (olculdu): basliksiz `topic` satirlari anonim istemciye aittir."""
    acl = acl_modulu.parse_acl("topic write anon/alan\nuser pano1\ntopic write veri/pano1\n")
    assert acl.allows(None, "write", "anon/alan") is True
    assert acl.allows("pano1", "write", "anon/alan") is False


def test_fiil_yazilmazsa_readwrite(acl_modulu):
    """Semantik 7 (olculdu)."""
    acl = acl_modulu.parse_acl("user p\ntopic serbest/alan\n")
    assert acl.allows("p", "read", "serbest/alan") is True
    assert acl.allows("p", "write", "serbest/alan") is True


def test_read_ve_write_ayri_ayri_degerlendirilir(acl_modulu):
    acl = acl_modulu.parse_acl("user p\ntopic read yalniz/okunur\ntopic write yalniz/yazilir\n")
    assert acl.allows("p", "read", "yalniz/okunur") is True
    assert acl.allows("p", "write", "yalniz/okunur") is False
    assert acl.allows("p", "write", "yalniz/yazilir") is True
    assert acl.allows("p", "read", "yalniz/yazilir") is False


# --------------------------------------------------------------- ayristirma hatalari


@pytest.mark.parametrize(
    "metin",
    [
        "user\n",                              # kullanici adi yok
        "user p\ntopic publish a/b\n",         # gecersiz fiil (broker da acilmaz)
        "bilinmeyen a/b\n",                    # bilinmeyen anahtar
        "pattern write sabit/topic\n",         # kalipta %u/%c yok -> herkese acilirdi
        "user p\ntopic write\n",               # fiilden sonra topic yok
    ],
)
def test_bozuk_satir_sessizce_atlanmaz(acl_modulu, metin):
    """Bozuk bir satir SESSIZCE gecilirse bir kural sessizce kaybolur; broker da acilmaz."""
    with pytest.raises(acl_modulu.AclError):
        acl_modulu.parse_acl(metin)


def test_yorum_ve_bos_satirlar_atlanir(acl_modulu):
    acl = acl_modulu.parse_acl("# yorum\n\n  \npattern write veri/%u/x\n")
    assert len(acl.patterns) == 1


def test_gecersiz_erisim_turu_hata_verir(depo_acl):
    with pytest.raises(ValueError):
        depo_acl.allows("ADM-00001", "subscribe", "gridup/pano/ADM-00001/tel")


# --------------------------------------------------------------- depodaki ACL kilidi


def test_deploy_acl_ayristirilabilir(depo_acl):
    """deploy/mosquitto.acl bozulursa broker ACILMAZ; test once burada kirilir."""
    assert depo_acl.patterns, "kalip kurali kalmamis"
    assert "gridup-backend" in depo_acl.usernames


@pytest.mark.parametrize(
    ("kimlik", "erisim", "topic", "izinli"),
    [
        # KABUL OLCUTUNUN BEKLENTI HALI. Kaniti canli olcumdedir.
        ("ADM-00001", "write", "gridup/pano/ADM-00001/tel", True),
        ("ADM-00001", "write", "gridup/pano/ADM-00002/tel", False),
        ("ADM-00001", "write", "gridup/pano/ADM-00001/evt", True),
        ("ADM-00001", "write", "gridup/pano/ADM-00001/hb", True),
        # Kenar cihaz KOMUT YAZAMAZ: komut yonu merkezden kenaradir.
        ("ADM-00001", "write", "gridup/pano/ADM-00001/cmd", False),
        ("ADM-00001", "read", "gridup/pano/ADM-00001/cmd", True),
        ("ADM-00001", "read", "gridup/pano/ADM-00002/cmd", False),
        # Komsusunun telemetrisini OKUYAMAZ.
        ("ADM-00001", "read", "gridup/pano/ADM-00002/tel", False),
        # Merkez filoyu okur, yalnizca komut yazar.
        ("gridup-backend", "read", "gridup/pano/ADM-00001/tel", True),
        ("gridup-backend", "read", "gridup/pano/ADM-00002/evt", True),
        ("gridup-backend", "write", "gridup/pano/ADM-00001/cmd", True),
        ("gridup-backend", "write", "gridup/pano/ADM-00001/tel", False),
        # ACL'deki `deny` satiri: merkez kendi adina telemetri uretemez.
        ("gridup-backend", "write", "gridup/pano/gridup-backend/tel", False),
        ("gridup-backend", "read", "gridup/pano/gridup-backend/cmd", False),
        # Sozlesme disi bir topic hicbir kimlige acik degil.
        ("ADM-00001", "write", "gridup/sistem/komut", False),
        ("gridup-backend", "write", "$SYS/broker/uptime", False),
    ],
)
def test_depodaki_acl_beklenen_yetkiyi_verir(depo_acl, kimlik, erisim, topic, izinli):
    assert depo_acl.allows(kimlik, erisim, topic) is izinli


def test_yeni_pano_eklemek_acl_dosyasini_degistirmez(depo_acl):
    """Yetki kurali KALIPTIR: filoya pano eklemek deploy/mosquitto.acl'e dokunmaz.

    Bu, F-27'nin yazilabilir olumlu iddialarindan biridir ve testle kilitlidir.
    (Sertifika uretimi ve dagitimi hala ELLEDIR — o F-28'in konusu.)
    """
    for yeni in ("ADM-04242", "GDZ-00001", "XYZ-99999"):
        assert depo_acl.allows(yeni, "write", f"gridup/pano/{yeni}/tel") is True
        assert depo_acl.allows(yeni, "write", "gridup/pano/ADM-00001/tel") is False


def test_anonim_istemci_hicbir_sozlesme_topicine_erisemez(depo_acl):
    """allow_anonymous false zaten kapatir; ACL ikinci savunma hattidir."""
    for erisim, topic in (
        ("write", "gridup/pano/ADM-00001/tel"),
        ("read", "gridup/pano/ADM-00001/tel"),
        ("read", "gridup/pano/ADM-00001/cmd"),
    ):
        assert depo_acl.allows(None, erisim, topic) is False
