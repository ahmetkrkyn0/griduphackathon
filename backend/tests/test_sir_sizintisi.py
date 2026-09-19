"""Sertifika ve ozel anahtar sizintisina karsi kilit (F-27).

NEDEN PYTEST: depoda CI ve pre-commit kancasi YOKTUR (`.git/hooks` tamami `.sample`) ve
kancalar klonla gelmez. Ekip zaten pytest kosturuyor, bu yuzden asil kilit burasidir;
scripts/sir_taramasi.py ayni mantigi tasiyan CLI'dir (depo deseni: test_verify_journal,
test_gen_alarm_doc).

F-27 depoya bir yerel sertifika otoritesi soktu. Olculen taban cizgisi: `deploy/certs/`
altina tipik bir CA ciktisi konuldugunda mevcut `.gitignore` (yalnizca *.pem ve *.key)
DOKUZ dosyayi disarida birakiyordu — `.crt .csr .srl .p12 index.txt serial openssl.cnf`
kapsam disiydi. Ustelik `git status` untracked bir DIZINI tek satirda ozetler, yani
"commit etmeden once status'e bakarim" savunmasi o senaryoda calismaz.

Bu dosya uc sey iddia eder:
  1. ignore sozlesmesi duruyor (uretilen materyalin tamami git disinda);
  2. izlenen hicbir dosyanin govdesinde PEM ozel anahtari yok — bunu .gitignore ASLA
     yakalayamaz (bir anahtarin bir .md dosyasina yapistirilmasi);
  3. ignore FAZLA yutmuyor (izlenen bir kaynak dosyasi sessizce kaybolmamis).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys

import pytest

from helpers import REPO_ROOT


@pytest.fixture(scope="module")
def tarama():
    spec = importlib.util.spec_from_file_location("sir_taramasi", REPO_ROOT / "scripts" / "sir_taramasi.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["sir_taramasi"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def izlenenler(tarama):
    return tarama.izlenen_dosyalar(staged=False)


def test_uretilen_sertifika_materyali_git_disinda(tarama):
    """Betigin urettigi (ve uretebilecegi) her yol ignore edilmeli."""
    assert tarama.ignore_disinda_kalanlar() == []


def test_certs_dizininin_kendi_ignore_dosyasi_yerinde():
    """BIRINCIL koruma budur ve uzantidan bagimsizdir.

    Silinirse `git status` ` D deploy/certs/.gitignore` gosterir; bu test onu
    sessizce gecirmemek icin var. Uretim betigi bu dosyaya DOKUNMAZ.
    """
    yol = REPO_ROOT / "deploy" / "certs" / ".gitignore"
    assert yol.is_file(), "deploy/certs/.gitignore silinmis — sertifika korumasi kalkti"
    satirlar = [s.strip() for s in yol.read_text(encoding="utf-8").splitlines() if s.strip() and not s.startswith("#")]
    assert satirlar == ["*", "!.gitignore"]


def test_izlenen_dosyalarda_ozel_anahtar_govdesi_yok(tarama, izlenenler):
    """`.gitignore`'un yakalayamayacagi sinif: anahtarin bir metin dosyasina yapistirilmasi."""
    anahtarlar, _ = tarama.govdede_pem_arayanlar(izlenenler)
    assert anahtarlar == [], f"izlenen dosyalarda ozel anahtar govdesi: {anahtarlar}"


def test_izlenen_dosyalarda_sertifika_govdesi_yok(tarama, izlenenler):
    """Sertifika sir degildir ama repoda durmamali: yanindaki anahtari davet eder."""
    _, sertifikalar = tarama.govdede_pem_arayanlar(izlenenler)
    assert sertifikalar == [], f"izlenen dosyalarda sertifika govdesi: {sertifikalar}"


def test_ignore_kurallari_izlenen_bir_dosyayi_yutmuyor(izlenenler):
    """Ters yon: yeni desenler (or. *.crt) mevcut bir kaynak dosyasini gizlemesin.

    Bastaki '/' olmadan yazilan "certs/" her derinlikteki certs dizinini gizlerdi;
    "*.conf" ise deploy/mosquitto.conf ve frontend/nginx.conf'u. Bu test o siniftaki
    her hatayi yakalar.
    """
    yutulan = [
        yol for yol in izlenenler
        if subprocess.run(["git", "check-ignore", "-q", yol], cwd=REPO_ROOT).returncode == 0
    ]
    assert yutulan == [], f"ignore kurallari izlenen dosyalari gizliyor: {yutulan}"


@pytest.mark.parametrize(
    "yol",
    [
        "deploy/mosquitto.acl",
        "deploy/mosquitto-mtls.conf",
        "deploy/compose.mtls.yaml",
        "deploy/certs/.gitignore",
        "deploy/mosquitto.conf",
        "frontend/nginx.conf",
    ],
)
def test_commit_edilmesi_gereken_dosyalar_gizlenmiyor(yol):
    """ACL kanitin bir parcasidir: gizlenirse F-27'nin kurali depodan kaybolur."""
    assert subprocess.run(["git", "check-ignore", "-q", yol], cwd=REPO_ROOT).returncode != 0, (
        f"{yol} .gitignore tarafindan gizleniyor"
    )


def test_gecmiste_de_sertifika_materyali_yok():
    """Bir kerelik taban cizgisi: eklenmis hicbir .pem/.key/.crt/... gecmiste yok.

    Sizan bir dosyayi gecmisten temizlemek `filter-repo` + force-push demektir; bu test
    o gunun geldigini ERKEN soyler. Yavas degildir: --diff-filter=A yalnizca EKLEME
    commit'lerini gezer.
    """
    sonuc = subprocess.run(
        ["git", "log", "--all", "--diff-filter=A", "--name-only", "--pretty=format:"],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert sonuc.returncode == 0, sonuc.stderr
    uzantilar = (".pem", ".key", ".crt", ".csr", ".p12", ".pfx", ".der", ".jks")
    bulunan = sorted({
        satir.strip() for satir in sonuc.stdout.splitlines()
        if satir.strip().lower().endswith(uzantilar)
    })
    assert bulunan == [], f"gecmiste sertifika/anahtar materyali var: {bulunan}"
