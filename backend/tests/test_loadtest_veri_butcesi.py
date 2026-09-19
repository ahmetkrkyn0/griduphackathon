"""F-36 — loadtest/veri_butcesi.py veri butcesi olcumu.

Bu arac bir SAYI URETIYOR ve o sayi docs/09'a giriyor. Dolayisiyla aracin kendi
muhasebesi sinanmali: yanlis sayan bir olcek, olculmemis bir iddiadan daha
kotudur (GK10).
"""

from __future__ import annotations

import importlib.util
import json
import sys

import pytest

from helpers import REPO_ROOT


@pytest.fixture(scope="module")
def butce():
    spec = importlib.util.spec_from_file_location(
        "loadtest_veri_butcesi", REPO_ROOT / "loadtest" / "veri_butcesi.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


@pytest.fixture(scope="module")
def kisa_kosu(butce):
    """Kisa ama GERCEK bir kosu: fizik ureteci + tam kenar boru hatti."""
    from panoalgo.generator import default_contracts_dir

    return butce.kosu(
        panolar=2, gun=0.05, isinma_gun=0.02, period_s=10.0,
        max_silence_s=60.0, tohum=4242, ariza=False,
        contracts_dir=default_contracts_dir(),
    )


def _politika(kosu: dict, ad: str) -> dict:
    return next(p for p in kosu["politikalar"] if p["ad"] == ad)


def test_the_fixed_policy_publishes_every_single_sample(kisa_kosu):
    """Taban kip hicbir seyi bastirmaz; karsilastirmanin sifir noktasi budur."""
    sabit = _politika(kisa_kosu, "sabit-10s")
    assert sabit["mesaj"] == kisa_kosu["ornek"]
    assert sabit["bastirilan_oran"] == 0.0


def test_adaptive_policies_publish_fewer_messages_than_the_fixed_one(kisa_kosu):
    sabit = _politika(kisa_kosu, "sabit-10s")
    for politika in kisa_kosu["politikalar"]:
        if politika["ad"] == "sabit-10s":
            continue
        assert politika["mesaj"] <= sabit["mesaj"], politika["ad"]
        assert politika["faturalanan_mb"] <= sabit["faturalanan_mb"], politika["ad"]


def test_every_policy_sees_exactly_the_same_physics(butce, kisa_kosu):
    """Butun politikalar AYNI ornek akisini gorur: karsilastirma gecerliligi budur.

    Iki ayri kosu yapilsaydi (biri sabit, biri uyarlanabilir) fizik ayni olmaz ve
    "yayin %X azaldi" cumlesi olcume degil iki farkli deneye dayanirdi.
    """
    for politika in kisa_kosu["politikalar"]:
        karar = sum(politika["gerekce_dagilimi"].values())
        assert karar == kisa_kosu["ornek"], politika["ad"]


def test_a_measurement_that_drifted_the_detection_period_is_refused(butce):
    """Olcum kendi tespit ritmini bozduysa sayi YAZMAZ, patlar.

    Beyan 10 s ama ornekler 30 s arayla geliyor: bu tam olarak "yayinlamiyorsak
    islemeye de gerek yok" optimizasyonunun birakacagi izdir. Bu emniyet olmasa
    olcum, RLS'i 3 kat yanlis periyotla kosturup sayilari yine de yazardi.
    """
    from panoalgo.generator import default_contracts_dir

    with pytest.raises(SystemExit, match="olcum gecersiz"):
        butce.kosu(
            panolar=1, gun=0.01, isinma_gun=0.004, period_s=10.0,
            max_silence_s=60.0, tohum=1, ariza=False,
            contracts_dir=default_contracts_dir(),
            _adim_s=30.0,
        )


def test_the_fleet_total_is_labelled_as_a_multiplication(butce, kisa_kosu):
    """'Filo toplami aylik maliyet' OLCUM DEGIL CARPIMDIR ve cikti bunu soyler (GK10)."""
    carpim = butce._carpim(kisa_kosu, 1000)
    assert "CARPIMDIR" in carpim["not"]
    assert carpim["filo_panosu"] == 1000

    uyar = _politika(kisa_kosu, f"uyarlanabilir-%{butce.DEADBAND_FRACTION * 100:g}")
    assert carpim["uyarlanabilir_gb_ay"] == pytest.approx(
        uyar["pano_basina_aylik_mb"] * 1000 / 1000.0, rel=1e-6
    )


def test_the_billable_overhead_is_declared_as_an_estimate(butce):
    """Faturalanan bayt tahmindir; JSON ve MQTT olculur. Ikisi karistirilmaz."""
    assert butce.BILLABLE_OVERHEAD_B == 110


def test_it_reuses_the_tested_mqtt_frame_helper(butce):
    """MQTT cerceve hesabi kopyalanmaz, loadtest/storage.py'den gelir."""
    assert butce.mqtt_publish_bytes(payload_bytes=1000, topic="gridup/pano/SIM-00001/tel") == 1032
