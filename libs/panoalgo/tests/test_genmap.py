"""Modbus harita basligi ureteci — panoalgo/genmap.py (--check bayragi ve tazeligi).

Bu dosyanin varlik sebebi OLCULMUS bir bosluktur. Depoda bes uretec var:

    scripts/gen_modbus_doc.py        --check  + test  (backend/tests/test_gen_modbus_doc.py)
    scripts/gen_iec104_doc.py        --check  + test  (backend/tests/test_gen_iec104_doc.py)
    scripts/gen_grafana_dashboards.py --check + test  (backend/tests/test_grafana_dashboards.py)
    scripts/gen_alarm_doc.py         --check  + test  (backend/tests/test_gen_alarm_doc.py)
    panoalgo/genmap.py               --check  + BU DOSYA

Besincisi 16 Eylul'e kadar ne bayragi ne testi tasiyordu ve bosluk sessizdi:
firmware/tests/test_modbus_map.c uretilmis basligi KULLANIR ama guncelligini
SINAMAZ (kendi basligi da bunu yaziyor: "Bu dosyada elle yazilmis adres YOKTUR").
Yani contracts/modbus-map.yaml degisip baslik yeniden uretilmezse C testleri
BAYAT haritaya karsi yesil gecerdi ve kimse fark etmezdi.

Beklenen degerlerin kaynagi: contracts/modbus-map.yaml. Bu dosyada elle yazilmis
tek bir adres yoktur — testler de uretim kodu gibi sozlesmeden okur (kural 10).
"""

from __future__ import annotations

import yaml

from panoalgo.genmap import default_output, main, render

from helpers import CONTRACTS_DIR


def _contract() -> dict:
    return yaml.safe_load((CONTRACTS_DIR / "modbus-map.yaml").read_text(encoding="utf-8"))


def test_committed_header_is_up_to_date():
    """ASIL KILIT: depodaki baslik sozlesmenin bugunku halinden uretilmis olmali.

    Sozlesme degisip `python -m panoalgo.genmap` kosulmazsa bu test kirilir —
    diger dort uretecin testiyle ayni sozu verir.
    """
    assert main(["--check"]) == 0


def test_check_reports_stale_header(tmp_path, capsys):
    """Bayat baslik 1 ile cikmali; yoksa bayrak bir sey KORUMUYOR demektir."""
    stale = tmp_path / "modbus_map_generated.h"
    stale.write_bytes(b"#define PANO_BLK_HEALTH_START 999\n")

    assert main(["--out", str(stale), "--check"]) == 1

    out = capsys.readouterr().out
    assert "guncel degil" in out
    # Kullaniciya NE KOSACAGINI soylemeli (dort uretecin ortak davranisi).
    assert "panoalgo.genmap" in out


def test_check_reports_missing_header(tmp_path):
    """Dosya hic yoksa da 1 donmeli — `read_bytes` patlamamali."""
    assert main(["--out", str(tmp_path / "yok.h"), "--check"]) == 1


def test_check_never_writes(tmp_path):
    """Denetim kipi dosya sistemine DOKUNMAMALI.

    Yazsaydi `--check` kendi sikayetini susturur ve PR oncesi kontrol
    hicbir zaman kirilmazdi.
    """
    stale = tmp_path / "modbus_map_generated.h"
    stale.write_bytes(b"bayat\n")

    assert main(["--out", str(stale), "--check"]) == 1
    assert stale.read_bytes() == b"bayat\n"

    missing = tmp_path / "alt" / "yok.h"
    assert main(["--out", str(missing), "--check"]) == 1
    assert not missing.exists()
    assert not missing.parent.exists()


def test_regenerate_then_check_passes(tmp_path):
    """Yeniden uretim ile denetim AYNI baytlar uzerinden gitmeli.

    Yazma yolu ile denetim yolu ayri hesaplanirsa `--check` "guncel" derken
    dosya farkli olabilir; bu test o ihtimali kapatir.
    """
    out = tmp_path / "alt" / "modbus_map_generated.h"

    assert main(["--out", str(out)]) == 0
    assert main(["--out", str(out), "--check"]) == 0
    assert out.read_bytes() == render().encode("utf-8")


def test_render_is_deterministic():
    """Ciktida tarih/saat damgasi olmamali; olsaydi --check her kosuda kirilirdi."""
    assert render() == render()


def test_header_addresses_come_from_contract():
    """Uretilen sabitler sozlesmedeki bloklarla birebir ayni olmali."""
    header = render()
    blocks = _contract()["blocks"]
    assert blocks, "sozlesmede blok yok — test kendi varsayimini dogruluyor"

    for block in blocks:
        name = block["name"].upper()
        assert f"#define PANO_BLK_{name}_START {block['start']}\n" in header
        assert f"#define PANO_BLK_{name}_COUNT {block['count']}\n" in header


def test_header_version_follows_contract():
    """Sozlesmenin `version` alani baslikta gorunmeli — bayat baslik teshisi bundan baslar."""
    version = _contract()["version"]
    assert f"#define PANO_MAP_VERSION {version}\n" in render()
    assert f"(surum {version})" in render()


def test_default_output_points_at_firmware():
    """--out verilmediginde yazilacak yer firmware/core olmali."""
    path = default_output()
    assert path.name == "modbus_map_generated.h"
    assert path.parent.name == "core"
    assert path.parent.parent.name == "firmware"
