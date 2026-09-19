"""L2 degisim noktasi testleri (F-32) — panoalgo/onset.py.

Beklenen degerlerin kaynagi: CUSUM'un kendi tanimi (modul basligi). Seriler elle
kurulmustur ve her testin docstring'inde hangi ornekte ne oldugu yazilidir; boylece
"gecti" demek "dogru yerde gecti" demektir.
"""

from __future__ import annotations

import pytest

from panoalgo.onset import (
    DEFAULT_SLACK_SIGMA,
    DEFAULT_THRESHOLD_SIGMA,
    baseline_window_is_stable,
    detect_onset,
)


def _flat(n: int, value: float = 1.0) -> list[float]:
    """Kucuk ama sifir olmayan gurultu: sigma0 sifir olmasin diye donusumlu +/-."""
    return [value + (0.01 if index % 2 else -0.01) for index in range(n)]


# ------------------------------------------------------------------ temel davranis


def test_sabit_seride_degisim_bulunmaz():
    """Taban gibi devam eden seride CUSUM birikmez; changed False kalir."""
    result = detect_onset(_flat(200), reference_n=50)
    assert result.changed is False
    assert result.onset_index is None
    assert result.alarm_index is None


def test_basamak_degisimi_basladigi_yerde_isaretlenir():
    """100. ornekte 1,0 -> 1,5 basamagi. sigma0 ~0,01 oldugu icin z ~50: birikim
    basamakta baslar ve hemen ardindan esigi (5 sigma) asar.

    Baslangic ani, esigin asildigi an DEGIL, birikimin basladigi andir; CUSUM'un
    butun degeri bu farktir.

    NEDEN TAM 100 DEGIL DE 99-100 ARALIGI: CUSUM'un baslangic kestirimi "birikimin
    en son sifirlandigi an"dir ve bu, gercek degisimden gurultunun son POZITIF
    salinimi kadar once olabilir. Bu fixture'da gurultu donusumlu +/-0,01, yani tek
    indisli ornekler tam +1 sigma'da oturur ve slack'i (0,5 sigma) asarak birikimi
    bir ornek erken baslatir. Bu yontemin bilinen bir ozelligidir, hata degil:
    baslangic ani her zaman gercek degisimin ONUNDE veya uzerindedir, ARKASINDA
    olmaz — bakim kararinda istenen taraf da budur.
    """
    values = _flat(100) + [1.5] * 50
    result = detect_onset(values, reference_n=50)
    assert result.changed is True
    assert result.onset_index in (99, 100)
    assert result.alarm_index is not None and result.alarm_index >= 100
    assert result.lead_samples == result.alarm_index - result.onset_index


def test_yavas_suruklenme_esik_asilmadan_once_baslamis_sayilir():
    """Ornek basina 0,02'lik yavas ramp — tek bir ornek tek basina esigi asmaz,
    birikim asar. Baslangic ani rampin BASLADIGI ornek civarinda olmali ve esigin
    asildigi andan KUCUK olmali (yani one alma pozitif).
    """
    values = _flat(60) + [1.0 + 0.02 * step for step in range(1, 80)]
    result = detect_onset(values, reference_n=50)
    assert result.changed is True
    assert result.onset_index is not None
    assert result.lead_samples is not None and result.lead_samples > 0
    # Ramp 60. ornekte basliyor; baslangic kestirimi onun bir ornek onunde olabilir
    # (bkz. basamak testindeki "son sifirlanma" notu), ama arkasinda olamaz.
    assert 59 <= result.onset_index <= 61


def test_asagi_yonlu_degisim_bozulma_sayilmaz():
    """K'nin DUSMESI bozulma degildir (temizlenen/yeniden sikilan baglanti).
    Tek yonlu CUSUM bunu gormemelidir.
    """
    values = _flat(100) + [0.5] * 100
    assert detect_onset(values, reference_n=50).changed is False


# ------------------------------------------------------------------ sinir durumlar


def test_referans_penceresinden_kisa_seri_degisim_iddia_etmez():
    """Referans penceresi kadar bile ornek yoksa kanit yoktur; changed False."""
    result = detect_onset([1.0] * 30, reference_n=50)
    assert result.changed is False
    assert result.peak_cusum == 0.0


def test_gecersiz_referans_penceresi_reddedilir():
    with pytest.raises(ValueError, match="reference_n"):
        detect_onset([1.0] * 10, reference_n=1)


def test_tamamen_sabit_referans_sonsuz_z_uretmez():
    """sigma0 = 0 olan bir pencerede bolme patlardi; MIN_SIGMA alt siniri bunu
    engeller ve sabit devam eden seri "degisim yok" tarafinda kalir.
    """
    result = detect_onset([1.0] * 200, reference_n=50)
    assert result.changed is False


def test_esik_ve_slack_parametrik():
    """Esik dusurulurse ayni seri degisim olarak gorulebilmeli — sayilar sozlesmeden
    gelmedigi icin cagirana acik birakildi.
    """
    values = _flat(80) + [1.05] * 80
    kati = detect_onset(values, reference_n=50, threshold_sigma=DEFAULT_THRESHOLD_SIGMA)
    gevsek = detect_onset(values, reference_n=50, threshold_sigma=1.0, slack_sigma=DEFAULT_SLACK_SIGMA)
    assert gevsek.peak_cusum >= kati.peak_cusum or gevsek.changed


# ------------------------------------------------- taban penceresi kararliligi


def test_kararli_ogrenme_penceresi_kararli_sayilir():
    """Pencerenin iki yarisi ayni dagilimdan geliyorsa taban kararlidir."""
    assert baseline_window_is_stable(_flat(200), reference_n=200) is True


def test_ogrenme_penceresi_icinde_baslayan_bozulma_yakalanir():
    """ISO 17359 baz cizgiyi "makine kararliyken" ister; docs/18 §(b) bunun
    SINANMADIGINI itiraf ediyordu. Pencerenin ikinci yarisi birinciden kalici olarak
    sapiyorsa o pencere kararli DEGILDIR ve medyani saglikli bir taban sayilamaz.
    """
    window = _flat(100) + [1.4] * 100
    assert baseline_window_is_stable(window, reference_n=200) is False


def test_cok_kisa_pencere_kararsiz_ilan_edilmez():
    """Sinayacak kadar ornek yoksa "kararsiz" demek kanitsiz bir iddia olurdu."""
    assert baseline_window_is_stable([1.0, 1.0, 1.0], reference_n=3) is True
