"""F-05 — scripts/tazminat_maruziyeti.py: parametre yoksa "veri yok", parametre varsa aritmetigi dogru (GK10).

Betik hicbir sayiyi kendi uydurmaz: yonetmelik esikleri ve tarife disaridan gelir, BOM farkinin adetleri
contracts/modbus-map.yaml'dan, odenen arayuzun fiyati hardware/pano-beyni/bom.csv'den okunur.
"""

from __future__ import annotations

import csv
import importlib.util
import sys

import pytest

from helpers import REPO_ROOT


@pytest.fixture(scope="module")
def calc():
    spec = importlib.util.spec_from_file_location("tazminat_maruziyeti", REPO_ROOT / "scripts" / "tazminat_maruziyeti.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def test_parametresiz_calisinca_hicbir_sayi_uretmez(calc, capsys):
    assert calc.main([]) == 1  # veri yoksa sessizce sifir dondurmez
    text = capsys.readouterr().out
    assert "veri yok: hesap icin gereken parametreler girilmedi" in text
    assert "--dagitim-bedeli" in text and "--ortalama-talep-kw" in text
    assert "TOPLAM MARUZIYET" not in text
    assert "onledi" not in text.lower()  # onlenen ariza iddia edilmez (GK10)


def test_exposure_aritmetigi_esigi_asan_kismi_hesaplar(calc):
    values = calc.exposure(abone=10, kesinti_saat=8, esik_saat=4, ortalama_talep_kw=2.0, dagitim_bedeli=0.5,
                           kesinti_sayisi=6, esik_sayi=4, kesinti_basi_tazminat=3.0)
    assert values["asilan_saat"] == 4 and values["asilan_sayi"] == 2
    assert values["sure"] == pytest.approx(10 * 2.0 * 0.5 * 4)  # 40
    assert values["sayi"] == pytest.approx(10 * 2 * 3.0)  # 60
    assert values["toplam"] == pytest.approx(100.0)


def test_esigin_altinda_kalan_kesinti_tazminat_dogurmaz(calc):
    values = calc.exposure(abone=10, kesinti_saat=3, esik_saat=4, ortalama_talep_kw=2.0, dagitim_bedeli=0.5,
                           kesinti_sayisi=4, esik_sayi=4, kesinti_basi_tazminat=3.0)
    assert (values["asilan_saat"], values["asilan_sayi"], values["toplam"]) == (0.0, 0, 0.0)


def test_cli_ciktisi_ayni_aritmetigi_maruziyet_dilinde_yazar(calc, capsys):
    code = calc.main(["--yalniz", "maruziyet", "--pano", "ADM-00001", "--abone", "10", "--kesinti-saat", "8",
                      "--esik-saat", "4", "--ortalama-talep-kw", "2", "--dagitim-bedeli", "0.5",
                      "--kesinti-sayisi", "6", "--esik-sayi", "4", "--kesinti-basi-tazminat", "3"])
    text = capsys.readouterr().out
    assert code == 0
    assert "TOPLAM MARUZIYET: 100.00 TL" in text
    assert "tazminat DOGAR" in text  # maruziyet dili: "su kadar ariza onledik" degil
    assert "onledi" not in text.lower()


def test_bom_farkinin_adetleri_sozlesme_haritasindan_sayilir(calc):
    items = {item["kalem"]: item for item in calc.avoided_items()}
    assert (items["Akim trafosu (faz + notr)"]["adet"], items["Akim trafosu (faz + notr)"]["cihaz"]) == (4, "MPR-53CS")
    assert items["Gerilim olcum girisi"]["adet"] == 3
    assert (items["Ark dedektoru"]["adet"], items["Ark dedektoru"]["cihaz"]) == (2, "ABB TVOC-2")
    assert items["Ark koruma merkez unitesi"]["adet"] == 1


def test_odenen_arayuz_fiyati_bom_csv_satirindan_gelir(calc):
    with (REPO_ROOT / "hardware" / "pano-beyni" / "bom.csv").open(encoding="utf-8", newline="") as handle:
        row = next(row for row in csv.DictReader(handle) if "RS485" in row["parca"])
    paid = calc.paid_interface()
    assert (paid["adet1"], paid["adet1000"]) == (float(row["birim_fiyat_usd_adet1"]), float(row["birim_fiyat_usd_adet1000"]))
    assert paid["bom_adet"] == 2 and paid["adet"] == 1  # ikinci arayuz SCADA slave portu


def test_bom_farki_fiyatsiz_calisinca_veri_yok_der(calc, capsys):
    calc.main(["--yalniz", "bom"])
    text = capsys.readouterr().out
    assert "Kacinilan toplam: veri yok" in text and "Net fark: veri yok" in text


def test_docs_10_bom_farki_tablosu_koddaki_sayilarla_ayni(calc):
    """Dokumana elle yazilan adet ve fiyatlar betigin turettikleriyle ayni kalmali."""
    doc = (REPO_ROOT / "docs" / "10-bom-maliyet-roi.md").read_text(encoding="utf-8")
    section = doc[doc.index("### 5.2"):]
    items = {item["kalem"]: item["adet"] for item in calc.avoided_items()}
    assert f"| Akım trafosu (faz + nötr) | {items['Akim trafosu (faz + notr)']} |" in section
    assert f"| Ark dedektörü | {items['Ark dedektoru']} |" in section
    paid = calc.paid_interface()
    assert f"**{paid['adet1']:.2f}".replace(".", ",") in section
    assert f"**{paid['adet1000']:.2f}".replace(".", ",") in section
