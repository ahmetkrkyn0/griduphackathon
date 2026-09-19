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


# --------------------------------------------------------- 8.1 parametre dosyasi + duyarlilik (K8)
ORNEK_PARAMS = REPO_ROOT / "scripts" / "roi-ornek-parametreler.yaml"


def test_ornek_parametre_dosyasi_uc_sutun_kuralina_uyuyor(calc):
    """Depodaki ornek dosya kendi denetiminden gecmeli; gecmezse juri ilk komutta hata alir."""
    params = calc.load_params(ORNEK_PARAMS)
    assert params, "parametre dosyasi bos"
    for name, entry in params.items():
        assert set(entry) == {"deger", "kaynak", "guven"}, name
        assert entry["guven"] in calc.GUVEN, name
        assert str(entry["kaynak"]).strip(), name
        # Erdem burada yasiyor: bos deger "isletmeci-doldurur", dolu deger baska bir etiket tasir.
        assert (entry["deger"] is None) == (entry["guven"] == calc.GUVEN_BOS), name


def test_ornek_dosyadaki_tarife_ve_esik_alanlari_hala_bos(calc):
    """Yonetmelik esigi ve dagitim bedeli depoda YOK; ornek dosya bunlari doldurmaya baslamamali."""
    params = calc.load_params(ORNEK_PARAMS)
    for name in ("dagitim_bedeli", "esik_saat", "esik_sayi", "kesinti_basi_tazminat",
                 "ortalama_talep_kw", "kesinti_saat", "kesinti_sayisi", "opex_yillik_usd",
                 "at_fiyat", "gerilim_fiyat", "ark_dedektor_fiyat", "ark_unite_fiyat"):
        assert params[name]["deger"] is None, f"{name} doldurulmus — bu sayi depoda yok"
        assert params[name]["guven"] == calc.GUVEN_BOS


def test_fayda_varsayimlari_varsayim_etiketi_tasiyor(calc):
    """Geri odemeyi belirleyen uc sayi olcum DEGILDIR; etiketleri bunu soylemeye devam etmeli."""
    params = calc.load_params(ORNEK_PARAMS)
    for name in ("ariza_olasiligi_yil", "ariza_basi_maliyet_usd", "tespit_orani"):
        assert params[name]["guven"] == "varsayim", name


def _yaz(tmp_path, govde: str):
    path = tmp_path / "p.yaml"
    path.write_text(govde, encoding="utf-8")
    return path


def test_isletmeci_doldurur_etiketli_alana_deger_yazilamaz(calc, tmp_path):
    """Uydurulmus bir sayinin kaynagini 'isletmeci' gostererek gecmesini engelleyen denetim."""
    path = _yaz(tmp_path, "parametreler:\n  dagitim_bedeli:\n    deger: 3.5\n    kaynak: x\n    guven: isletmeci-doldurur\n")
    with pytest.raises(SystemExit) as hata:
        calc.load_params(path)
    assert "isletmeci-doldurur" in str(hata.value)


def test_kaynaksiz_veya_taninmayan_guvenli_girdi_reddedilir(calc, tmp_path):
    kaynaksiz = _yaz(tmp_path, "parametreler:\n  abone:\n    deger: 10\n    kaynak: '  '\n    guven: ornek\n")
    with pytest.raises(SystemExit) as hata:
        calc.load_params(kaynaksiz)
    assert "kaynaksiz" in str(hata.value)
    uydurma = _yaz(tmp_path, "parametreler:\n  abone:\n    deger: 10\n    kaynak: x\n    guven: kesin\n")
    with pytest.raises(SystemExit) as hata:
        calc.load_params(uydurma)
    assert "guven etiketi taninmiyor" in str(hata.value)


def test_komut_satiri_parametre_dosyasini_ezer(calc):
    args = calc.build_parser().parse_args(["--dugum-sayisi", "25"])
    labels = calc.apply_params(args, calc.load_params(ORNEK_PARAMS))
    assert args.dugum_sayisi == 25  # dosyada 7 yaziyor, komut satiri kazandi
    assert labels["dugum_sayisi"] == "komut satiri"
    assert args.ariza_olasiligi_yil == 0.03 and labels["ariza_olasiligi_yil"] == "varsayim"


def test_parametre_dosyasindaki_taninmayan_alan_sessizce_yutulmaz(calc, tmp_path):
    path = _yaz(tmp_path, "parametreler:\n  kur_usd_try:\n    deger: 40\n    kaynak: x\n    guven: varsayim\n")
    args = calc.build_parser().parse_args([])
    with pytest.raises(SystemExit) as hata:
        calc.apply_params(args, calc.load_params(path))
    assert "taninmayan alan" in str(hata.value)


# --------------------------------------------------------- 8.3 pano basina maliyet (BOM'dan olculur)
def test_bom_toplami_csv_toplam_satirindaki_metinle_ayni(calc):
    """Uc BOM'un dipnotu satir toplamindan sapmamali — bu depoda bir kez sapmisti (56/37 vs 70,73/47,68)."""
    for anahtar, beklenen in (("kontrolcu", (70.73, 47.68)), ("dugum", (23.25, 13.95)), ("pd", (19.80, 11.79))):
        path, sutun = calc.BOM_FILES[anahtar]
        hesap = (calc.bom_total(path, sutun, "adet1"), calc.bom_total(path, sutun, "adet1000"))
        assert hesap == pytest.approx(beklenen, abs=0.005), anahtar
        dipnot = path.read_text(encoding="utf-8").strip().splitlines()[-1]
        assert f"{beklenen[0]:.2f}" in dipnot and f"{beklenen[1]:.2f}" in dipnot, anahtar


def test_pano_maliyeti_dugum_sayisiyla_dogrusal_buyur(calc):
    yedi = calc.panel_cost(7, False, "adet1000")
    assert yedi["toplam"] == pytest.approx(47.68 + 7 * 13.95)
    yirmibes = calc.panel_cost(25, False, "adet1000")
    assert yirmibes["toplam"] == pytest.approx(47.68 + 25 * 13.95)
    og = calc.panel_cost(25, True, "adet1000")
    assert og["toplam"] - yirmibes["toplam"] == pytest.approx(11.79)  # PD karti yalnizca OG'de


def test_dugum_sayisi_verilmezse_toplam_veri_yok_der(calc, capsys):
    assert calc.main(["--yalniz", "maliyet"]) == 0
    text = capsys.readouterr().out
    assert "TOPLAM: veri yok" in text and "--dugum-sayisi" in text
    assert "GERI ODEME: veri yok" in text
    assert "47.68 USD" in text  # olculen kalem gizlenmez


def test_dugum_sayisi_sozlesme_sinirlarinin_disinda_reddedilir(calc):
    for disarida in ("3", "26"):
        with pytest.raises(SystemExit) as hata:
            calc.main(["--yalniz", "maliyet", "--dugum-sayisi", disarida])
        assert "dugum-sayisi" in str(hata.value)


def test_geri_odeme_aritmetigi_ve_opex_harici_etiketi(calc):
    maliyet = calc.panel_cost(7, False, "adet1000")["toplam"]
    ay = calc.payback_months(maliyet, 0.03, 8000.0, 0.70, 0.0)
    assert ay == pytest.approx(12 * maliyet / (0.03 * 8000 * 0.70))
    # Net fayda sifir veya negatifse sayi UYDURULMAZ: None doner, rapor "HICBIR ZAMAN" yazar.
    assert calc.payback_months(maliyet, 0.03, 8000.0, 0.70, 168.0) is None
    assert calc.payback_months(maliyet, 0.03, 8000.0, 0.70, 500.0) is None


def test_opex_brut_faydayi_asinca_rapor_hicbir_zaman_der(calc, capsys):
    calc.main(["--yalniz", "maliyet", "--dugum-sayisi", "7", "--ariza-olasiligi-yil", "0.03",
               "--ariza-basi-maliyet-usd", "8000", "--tespit-orani", "0.7", "--opex-yillik-usd", "200"])
    assert "GERI ODEME: HICBIR ZAMAN" in capsys.readouterr().out


# --------------------------------------------------------- 8.1 duyarlilik tablosu
def test_duyarlilik_parametresiz_calisinca_oynatacak_girdi_bulamaz(calc, capsys):
    assert calc.main(["--duyarlilik"]) == 1  # erdem korunur: veri yoksa 0 donmez
    text = capsys.readouterr().out
    assert "DUYARLILIK" in text
    assert "Maruziyet toplami: veri yok" in text and "Geri odeme (ay): veri yok" in text


def test_carpimsal_girdilerin_kaldiraci_esit_cikar(calc):
    """Geri odeme = maliyet / (P x L x r): uc carpanin kaldiraci ZORUNLU olarak esittir.

    Bu bir tesadufu degil modelin yapisini olcer; tabloyu okuyan 'sonucu su varsayim belirliyor'
    diyemez, cunku ucu de ayni oranda belirler. Rapor bunu 'BERABERE' diye yazar.
    """
    args = calc.build_parser().parse_args(
        ["--dugum-sayisi", "7", "--ariza-olasiligi-yil", "0.03", "--ariza-basi-maliyet-usd", "8000",
         "--tespit-orani", "0.7"])
    table = calc.sensitivity(args, calc.PAYBACK_ARGS, calc._payback_of)
    genislikler = [row["genislik"] for row in table["satirlar"]]
    assert len(genislikler) == 3
    assert genislikler[0] == pytest.approx(4 / 3)  # (2 - 2/3) = 4/3, carpimsal modelin imzasi
    assert all(g == pytest.approx(genislikler[0]) for g in genislikler)


def test_dugum_sayisinin_kaldiraci_carpanlardan_KUCUK_cikar(calc):
    """Maliyet bir TOPLAMDIR (kontrolcu + N x dugum), yani N oransal etki etmez — olculdu, varsayilmadi."""
    args = calc.build_parser().parse_args(
        ["--dugum-sayisi", "7", "--ariza-olasiligi-yil", "0.03", "--ariza-basi-maliyet-usd", "8000",
         "--tespit-orani", "0.7"])
    table = calc.sensitivity(args, ("dugum_sayisi",) + calc.PAYBACK_ARGS, calc._payback_of)
    satir = {row["girdi"]: row["genislik"] for row in table["satirlar"]}
    assert satir["dugum_sayisi"] < satir["tespit_orani"]
    assert table["satirlar"][0]["girdi"] != "dugum_sayisi"  # siralama genislige gore


def test_duyarlilik_ciktisi_beraberligi_gizlemez(calc, capsys):
    calc.main(["--yalniz", "maliyet", "--duyarlilik", "--parametreler", str(ORNEK_PARAMS)])
    text = capsys.readouterr().out
    assert "BERABERE" in text
    assert "Yapilandirma araligi (DUYARLILIK DEGIL, SECIM)" in text
    assert "onledi" not in text.lower()  # GK10 her bolumde gecerli


# --------------------------------------------------------- 8.4 basa bas esigi (fiyat gerektirmez)
def test_basa_bas_esigi_odenen_arayuzden_turetilir(calc):
    items = calc.avoided_items()
    paid = calc.paid_interface()
    be = calc.breakeven(items, paid)
    assert be["adet"] == 10  # 4 akim trafosu + 3 gerilim girisi + 2 ark dedektoru + 1 merkez unitesi
    assert be["adet1000"] == pytest.approx(paid["adet1000"] * paid["adet"] / 10)
    assert be["adet1000"] < 0.40  # kacinilan kalemlerin hicbiri bu fiyata bulunmaz; arguman buradan gelir


def test_basa_bas_esigi_fiyat_verilmeden_de_basilir(calc, capsys):
    calc.main(["--yalniz", "bom"])
    text = capsys.readouterr().out
    assert "BASA BAS ESIGI" in text and "Kacinilan toplam: veri yok" in text


# ------------------------- maruziyet duyarliliginin YAPISAL sinirlari (ornek degil)
def _maruziyet_kaldiraclari(calc, **kw):
    taban = {"abone": 412, "kesinti_saat": 8, "esik_saat": 4, "ortalama_talep_kw": 2,
             "dagitim_bedeli": 3, "kesinti_sayisi": 6, "esik_sayi": 4, "kesinti_basi_tazminat": 50}
    taban.update(kw)
    argv = []
    for ad, deger in taban.items():
        argv += [f"--{ad.replace('_', '-')}", str(deger)]
    args = calc.build_parser().parse_args(argv)
    table = calc.sensitivity(args, calc.DURATION_ARGS + calc.COUNT_ARGS[1:], calc._exposure_total)
    kalemler = calc.exposure(taban["abone"], taban["kesinti_saat"], taban["esik_saat"],
                             taban["ortalama_talep_kw"], taban["dagitim_bedeli"], taban["kesinti_sayisi"],
                             taban["esik_sayi"], taban["kesinti_basi_tazminat"])
    return {row["girdi"]: row["genislik"] for row in table["satirlar"]}, kalemler


# Bes farkli parametre seti: biri dokumandaki ornek, digerleri onu kiran setler.
MARUZIYET_SETLERI = (
    {},
    {"kesinti_basi_tazminat": 5},
    {"kesinti_basi_tazminat": 10},
    {"kesinti_saat": 40, "kesinti_sayisi": 5},
    {"kesinti_saat": 5, "kesinti_sayisi": 5},
)


def test_maruziyet_kaldiraclarinin_yapisal_sinirlari(calc):
    """Ornegi degil OZELLIGI kilitler — cunku ORNEGI kilitleyen ilk test yaniltici bir iddiaya izin verdi.

    Ilk yazilan iddia "siralama degismez" idi ve YANLISTI: kesinti_basi_tazminat 5 alindiginda
    dagitim_bedeli 0,71x'e cikip esik_sayi'yi (0,59x) geciyor. Yapisal olan siralama degil, su uc sinir:

      1. abone HER ZAMAN tam 1,00x — iki kalemi birden carpan tek girdi.
      2. Duz carpanlarin kaldiraci kendi kaleminin toplamdaki PAYINA birebir esittir, yani <= 1,00x.
      3. Esik kalemleri (max(0, kesinti - esik) icindekiler) bu sinira tabi DEGILDIR.
    """
    esik_asanlar = []
    for kw in MARUZIYET_SETLERI:
        g, kalemler = _maruziyet_kaldiraclari(calc, **kw)
        sure_payi = kalemler["sure"] / kalemler["toplam"]
        sayi_payi = kalemler["sayi"] / kalemler["toplam"]

        assert g["abone"] == pytest.approx(1.0), kw  # (1)
        # (2) duz carpanlar: kaldirac = kendi kaleminin payi, ve 1,00x'i ASLA gecmez
        assert g["dagitim_bedeli"] == pytest.approx(sure_payi), kw
        assert g["ortalama_talep_kw"] == pytest.approx(sure_payi), kw
        assert g["kesinti_basi_tazminat"] == pytest.approx(sayi_payi), kw
        for duz in ("dagitim_bedeli", "ortalama_talep_kw", "kesinti_basi_tazminat"):
            assert g[duz] <= 1.0 + 1e-9, (kw, duz)

        esik_asanlar += [g[ad] for ad in ("kesinti_saat", "esik_saat", "kesinti_sayisi", "esik_sayi")]

    # (3) esik kalemleri duz carpanlarin tavanini gercekten asabiliyor: aksi halde "sinirsiz" demek bos olurdu
    assert max(esik_asanlar) > 1.0, "esik kalemi hicbir sette 1,00x'i asmadi — iddia dayanaksiz kalir"


def test_tarife_hicbir_sette_en_belirleyici_girdi_olmuyor(calc):
    """Yayimlanan cumle: 'tarife bu hesabin baskin belirsizligi OLAMAZ'. Sinirdan turer, ornekten degil."""
    for kw in MARUZIYET_SETLERI:
        g, _ = _maruziyet_kaldiraclari(calc, **kw)
        en_yuksek = max(g.values())
        assert g["dagitim_bedeli"] < en_yuksek or g["dagitim_bedeli"] == pytest.approx(en_yuksek) and en_yuksek <= 1.0, kw
        assert g["dagitim_bedeli"] <= 1.0 + 1e-9, kw


def test_siralama_ornekten_ornege_DEGISIYOR(calc):
    """Yanlislanan iddiayi kilitler: siralamanin degismez OLMADIGINI testle sabitler.

    Biri ileride yine "siralama yapisaldir" diye yazarsa bu test onu yakalar.
    """
    taban, _ = _maruziyet_kaldiraclari(calc)
    kirik, _ = _maruziyet_kaldiraclari(calc, kesinti_basi_tazminat=5)
    assert taban["dagitim_bedeli"] < taban["esik_sayi"]      # dokumandaki ornekte tarife altta
    assert kirik["dagitim_bedeli"] > kirik["esik_sayi"]      # baska bir makul sette ustte


def test_esigin_altindaki_panoda_kaldirac_sifir_degil_veri_yok(calc):
    """Maruziyet 0 ise kaldirac TANIMSIZDIR; 0 yazmak "etkisiz" demek olurdu, oysa olculemiyor."""
    g, kalemler = _maruziyet_kaldiraclari(calc, kesinti_saat=2, kesinti_sayisi=3)
    assert kalemler["toplam"] == 0.0
    assert all(deger is None for deger in g.values())


def test_dugum_sayisi_oynatilirken_sozlesme_sinirlari_korunur(calc):
    """+-%50 duz uygulanirsa 7 dugum 3,5'e iner — betigin KENDI reddettigi bir yapilandirma.

    Duyarlilik tablosu boyle bir noktadan sayi turetemez: deger once yuvarlanir, sonra 4-25'e kirpilir.
    """
    assert calc.perturbed_value("dugum_sayisi", 7, 0.5) == calc.NODE_MIN   # 3,5 -> 4 (kirpildi)
    assert calc.perturbed_value("dugum_sayisi", 7, 1.5) == 11              # 10,5 -> 11 (tam sayi)
    assert calc.perturbed_value("dugum_sayisi", 20, 1.5) == calc.NODE_MAX  # 30 -> 25 (kirpildi)
    assert calc.perturbed_value("dagitim_bedeli", 3.0, 0.5) == pytest.approx(1.5)  # sinirsiz girdi dokunulmaz

    args = calc.build_parser().parse_args(
        ["--dugum-sayisi", "7", "--ariza-olasiligi-yil", "0.03", "--ariza-basi-maliyet-usd", "8000",
         "--tespit-orani", "0.7"])
    satir = next(r for r in calc.sensitivity(args, ("dugum_sayisi",), calc._payback_of)["satirlar"])
    assert satir["kirpildi"] is True and (satir["alt_deger"], satir["ust_deger"]) == (calc.NODE_MIN, 11)


def test_carpanlardan_biri_sifirsa_rapor_cokmez_hicbir_zaman_der(calc, capsys):
    """Regresyon: tespit orani 0 verildiginde betik TypeError ile cokuyordu (None bicimlendirme)."""
    calc.main(["--yalniz", "maliyet", "--dugum-sayisi", "7", "--ariza-olasiligi-yil", "0.03",
               "--ariza-basi-maliyet-usd", "8000", "--tespit-orani", "0"])
    text = capsys.readouterr().out
    assert "GERI ODEME: HICBIR ZAMAN" in text
    assert "brut yillik fayda sifir" in text


def test_loadtest_varsayilani_gercekten_yedi(calc):
    """Rapor "7 (loadtest varsayilani)" diye etiket basiyor; etiketin dayanagi KAYNAKTA dogrulanir."""
    metin = (REPO_ROOT / "loadtest" / "fleet.py").read_text(encoding="utf-8")
    assert "points: int = 7" in metin, "loadtest varsayilani degismis — rapordaki etiket yalan soyler"
    assert f"if not {calc.NODE_MIN} <= points <= len(names):" in metin  # alt sinir da kaynaktan


def test_docs_10_pano_maliyeti_tablosu_betikle_ayni(calc):
    """§7.2'nin dort toplami ve §5.3'un basa bas esigi dokumana ELLE yazildi; betikle ayni kalmali.

    Gerekcesi bu deponun kendi gecmisidir: elle yazilmis bir toplam (56/37) bir kez satir toplamindan
    sapti ve bes dosyaya kopyalandi. Ayni sey bu oturumun sayilarinda tekrarlanmasin.
    """
    doc = (REPO_ROOT / "docs" / "10-bom-maliyet-roi.md").read_text(encoding="utf-8")

    def gecer(deger: float) -> bool:
        """Nesirde ondalik VIRGUL, yapistirilan betik ciktisinda NOKTA kullanilir; ikisi de sayilir."""
        return f"{deger:.2f}" in doc or f"{deger:.2f}".replace(".", ",") in doc

    for n, pd_karti in ((4, False), (7, False), (25, False), (25, True)):
        assert gecer(calc.panel_cost(n, pd_karti, "adet1000")["toplam"]), (n, pd_karti)
    be = calc.breakeven(calc.avoided_items(), calc.paid_interface())
    assert gecer(be["adet1000"]) and gecer(be["adet1"])
