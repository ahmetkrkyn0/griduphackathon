"""L2 filo akran karsilastirmasi ve taban gecerliligi testleri (F-32) — panoalgo/fleet.py.

Iki sey kilitlenir:
  1. Yontemin kendisi (MAD tabanli modifiye z, akran gruplamasi, uc kanitli taban karari).
  2. YONTEMIN SENTETIK VERIDEKI SINIRI — asagidaki
     `test_sentetik_filoda_saglikli_pano_asla_aykiri_cikamaz` GK10 uyarisini SAYIYLA
     olcer. O test gecmeye devam ettigi surece "filo karsilastirmasi sentetik veride
     kusursuz ayirdi" cumlesi bir yontem kaniti olarak sunulamaz.
"""

from __future__ import annotations

import random

from panoalgo.fleet import (
    DEFAULT_OUTLIER_Z,
    MAD_TO_SIGMA,
    MIN_PEERS,
    baseline_verdict,
    peer_scores,
    robust_z_scores,
)
from panoalgo.generator import K_SPREAD

POINT = "DSYA4_L3"


def _fleet(k0_values: list[float], point: str = POINT) -> dict[str, dict[str, float]]:
    return {f"TR-{index:03d}": {point: k0} for index, k0 in enumerate(k0_values)}


def _score_for(scores, pano_id: str, point: str = POINT):
    return next(score for score in scores if score.pano_id == pano_id and score.point == point)


# ------------------------------------------------------------------ robust z


def test_robust_z_elle_hesaplanmis_ornekle_uyusur():
    """values = [1, 1, 1, 1, 5] -> medyan 1; |x - 1| = [0,0,0,0,4] -> MAD 0.
    MAD sifir oldugu icin skor URETILMEZ (None): akranlarin yarisindan fazlasi birebir
    ayni degerse sapma olcusu yoktur ve her farki sonsuz z yapmak yaniltici olurdu.
    """
    assert robust_z_scores([1.0, 1.0, 1.0, 1.0, 5.0]) == [None] * 5


def test_robust_z_bilinen_dagilimda_dogru_olcekler():
    """values = [1, 2, 3, 4, 5] -> medyan 3; |x - 3| = [2,1,0,1,2] -> MAD 1.
    Olceklenmis sapma = 1,4826 x 1 = 1,4826; z(5) = (5 - 3) / 1,4826 = 1,349.
    """
    zs = robust_z_scores([1.0, 2.0, 3.0, 4.0, 5.0])
    assert zs[2] == 0.0
    assert abs(zs[4] - 2.0 / MAD_TO_SIGMA) < 1e-12
    assert abs(zs[4] - 1.3489) < 1e-3


def test_tek_bozuk_pano_medyani_ve_mad_i_kacirmaz():
    """Ortalama/standart sapma kullanilsaydi bozuk panonun kendisi olcuye girer ve
    aradigimiz seyi saklardi. Medyan ve MAD'de bir aykiri deger merkezi oynatmaz.
    """
    saglikli = [1.00, 1.02, 0.98, 1.01, 0.99, 1.03, 0.97, 1.00]
    scores = peer_scores(_fleet([*saglikli, 3.0]))
    bozuk = _score_for(scores, f"TR-{len(saglikli):03d}")
    assert abs(bozuk.peer_median - 1.0) < 0.02
    assert bozuk.robust_z > DEFAULT_OUTLIER_Z
    assert bozuk.outlier is True


# ------------------------------------------------------------------ akran gruplamasi


def test_akran_grubu_nokta_adina_gore_ayrilir():
    """GIRIS_L1 (2312 A) ile DSYA1_L1 (250 A) ayni torbaya konmamali: K0'lari
    mertebe farkliligindadir ve karistirildiklarinda her ikisi de aykiri gorunur.
    """
    fleet = {
        f"TR-{index:03d}": {"GIRIS_L1": 1.0e-5 + index * 1e-8, "DSYA1_L1": 9.0e-4 + index * 1e-6}
        for index in range(MIN_PEERS)
    }
    scores = peer_scores(fleet)
    assert {score.point for score in scores} == {"GIRIS_L1", "DSYA1_L1"}
    assert all(score.outlier is False for score in scores)
    assert all(score.n_peers == MIN_PEERS for score in scores)


def test_yetersiz_akranla_skor_uretilmez_ve_aykiri_degil_denmez():
    """"Olcemedik" ile "aykiri degil" ayni sey degildir (GK10). Az akranda robust_z
    None doner ve outlier False kalir — ikincisi bir iddia degil, iddia YOKLUGUDUR.
    """
    scores = peer_scores(_fleet([1.0, 1.02, 9.0]))
    assert len(scores) == 3
    assert all(score.robust_z is None for score in scores)
    assert all(score.outlier is False for score in scores)
    assert all(score.n_peers == 3 for score in scores)


def test_akranlarindan_dusuk_k0_aykiri_sayilmaz():
    """Akranlarindan belirgin DUSUK K0 iyi bir baglantidir, alarm konusu degil."""
    saglikli = [1.00, 1.02, 0.98, 1.01, 0.99, 1.03, 0.97, 1.00]
    scores = peer_scores(_fleet([*saglikli, 0.2]))
    dusuk = _score_for(scores, f"TR-{len(saglikli):03d}")
    assert dusuk.robust_z < -DEFAULT_OUTLIER_Z
    assert dusuk.outlier is False


# ------------------------------------------------- GK10: uretec artefakti siniri


def test_sentetik_filoda_saglikli_pano_asla_aykiri_cikamaz():
    """GK10 — "mukemmel ayrim" bir URETEC ARTEFAKTIDIR, yontem kaniti degildir.

    generator.py saglikli K0'i SINIRLI DUZGUN dagilimdan cekiyor:
        spread = 1.0 + rng.uniform(-K_SPREAD, K_SPREAD),  K_SPREAD = 0.15
    Duzgun dagilimin KUYRUGU YOKTUR. U(-0,15, +0,15) icin medyan ~1,0 ve MAD ~0,075;
    olceklenmis sapma 1,4826 x 0,075 = 0,111. Saglikli bir panonun ulasabilecegi en
    buyuk |z| = 0,15 / 0,111 = 1,35.

    Bu test o tavani OLCER. 500 saglikli panoda (seed 20260918) olculen en buyuk
    |z| = 1,534; analitik sinirdan biraz buyuk cunku sonlu orneklemde MAD gercek
    degerinin biraz altinda cikar ve boleni kucultur. Aykirilik esigi ise 3,5'tir.

    Sonuc: sentetik filoda saglikli bir pano esigin YARISINA bile ulasamiyor, yani
    1,6'nin ustundeki HER esik kusursuz ayrim verir. Bu, yontemin degil URETECIN
    ozelligidir. Gercek filoda K0 dagilimi kuyrukludur (montaj torku, oksitlenme
    gecmisi, kesit toleransi) ve ayrim bu kadar temiz olmaz; bu depodan cikan hicbir
    ayrim orani saha basarimi olarak sunulamaz.
    """
    rng = random.Random(20260918)
    k0_values = [1.0 + rng.uniform(-K_SPREAD, K_SPREAD) for _ in range(500)]
    zs = [z for z in robust_z_scores(k0_values) if z is not None]

    tavan = max(abs(z) for z in zs)
    analitik_tavan = K_SPREAD / (MAD_TO_SIGMA * (K_SPREAD / 2.0))
    assert abs(analitik_tavan - 1.3489) < 1e-3
    assert abs(tavan - 1.534) < 1e-3, f"olculen tavan {tavan:.3f}"
    assert tavan < DEFAULT_OUTLIER_Z / 2.0
    assert not any(z >= DEFAULT_OUTLIER_Z for z in zs)


# ------------------------------------------------------------- taban gecerliligi


def test_uyarim_gormemis_taban_guvenilmez_sayilir():
    """RLS uyarim yokken GUNCELLENMEZ (detect.py update()). Uyarim orani cok
    dusukse K0 fiziksel baglantiyi degil baslangic onselini kodlar.
    """
    verdict = baseline_verdict(
        pano_id="TR-001", point=POINT,
        k_history=[1.0] * 200, reference_n=100, excited_ratio=0.01,
    )
    assert verdict.trustworthy is False
    assert verdict.rebaseline_suggested is True
    assert any("uyarim orani dusuk" in reason for reason in verdict.reasons)


def test_ogrenme_penceresi_icinde_baslayan_bozulma_tabani_gecersiz_kilar():
    """ISO 17359 baz cizgiyi "makine kararliyken" ister; docs/18 §(b) bunun
    sinanmadigini itiraf ediyordu. Pencerenin ikinci yarisi kalici olarak sapiyorsa
    bozulma taban ogrenilirken baslamistir.
    """
    history = [1.0 + (0.01 if index % 2 else -0.01) for index in range(100)] + [1.6] * 100
    verdict = baseline_verdict(
        pano_id="TR-001", point=POINT,
        k_history=history, reference_n=200, excited_ratio=0.9,
    )
    assert verdict.trustworthy is False
    assert any("kararsiz" in reason for reason in verdict.reasons)


def test_akranlarindan_aykiri_k0_devreye_almada_bozuk_baglantiyi_ele_verir():
    """K/K0'in TEK basina goremedigi durum: devreye alma aninda zaten gevsek bir
    baglanti. K yuksek, K0 ayni oranda yuksek, k_ratio 1,0 — nokta omru boyunca
    saglikli gorunur. Akran karsilastirmasi bunu gorur.
    """
    saglikli = [1.00, 1.02, 0.98, 1.01, 0.99, 1.03, 0.97, 1.00]
    scores = peer_scores(_fleet([*saglikli, 3.0]))
    bozuk = _score_for(scores, f"TR-{len(saglikli):03d}")

    kararli = [1.0 + (0.01 if index % 2 else -0.01) for index in range(200)]
    verdict = baseline_verdict(
        pano_id=bozuk.pano_id, point=POINT,
        k_history=kararli, reference_n=200, excited_ratio=0.9, peer=bozuk,
    )
    assert verdict.trustworthy is False
    assert verdict.rebaseline_suggested is True
    assert any("akranlarindan yukari aykiri" in reason for reason in verdict.reasons)


def test_saglikli_taban_guvenilir_sayilir_ve_yeniden_baz_alma_onerilmez():
    """Uc kanitin ucu de temizse taban guvenilirdir; gereksiz yeniden baz alma
    onerisi operatoru yorar ve oneriyi degersizlestirir.
    """
    saglikli = [1.00, 1.02, 0.98, 1.01, 0.99, 1.03, 0.97, 1.00]
    scores = peer_scores(_fleet(saglikli))
    kararli = [1.0 + (0.01 if index % 2 else -0.01) for index in range(200)]
    verdict = baseline_verdict(
        pano_id="TR-000", point=POINT,
        k_history=kararli, reference_n=200, excited_ratio=0.85,
        peer=_score_for(scores, "TR-000"),
    )
    assert verdict.trustworthy is True
    assert verdict.rebaseline_suggested is False
    assert verdict.reasons == []


def test_yeniden_baz_alma_yalnizca_oneridir():
    """Otomatik yeniden baz alma gercek bozulmayi susturur (docs/07b Y11).
    Bu modul K0'a DOKUNMAZ; ciktisi bir bayrak ve gerekcedir, bir eylem degil.
    """
    verdict = baseline_verdict(
        pano_id="TR-001", point=POINT,
        k_history=[1.0] * 200, reference_n=100, excited_ratio=0.0,
    )
    assert verdict.rebaseline_suggested is True
    assert not hasattr(verdict, "apply")
    assert verdict.reasons, "oneri her zaman gerekcesiyle birlikte gelmeli"
