#!/usr/bin/env python3
"""Uyarlanabilir raporlamanin veri butcesi olcumu (F-36, Kisi B araci).

NE OLCER
--------
Gercek fizik uretecini (`panoalgo.generator.PanelSimulator`) TESPIT PERIYODUYLA
(10 s) adimlar, her ornegi tam kenar boru hattindan (`EdgePipeline`: RLS + K/K0 +
esikler + risk) gecirir ve AYNI ornek akisina birden cok yayin politikasini
(`panoalgo.reporting.ReportGate`) paralel uygular. Her politika icin sayilir:

    mesaj sayisi · JSON bayti · MQTT tel bayti · faturalanan bayt (TAHMIN)

Ayrica iki sey OLCULUR, varsayilmaz:
  * GERI KURMA HATASI  - yayinlanmayan ornekler sifirinci derece tutmayla geri
    kurulursa her alanin gercek degerden en cok ne kadar saptigi. Olu bandin
    verdigi soz budur; test degil bu arac da olcer.
  * ALARM ANI          - her alarm kodunun ILK YAYINLANDIGI tur. Sabit ve
    uyarlanabilir kipte ayni tur cikmazsa uyarlanabilir raporlama alarmi
    geciktiriyor demektir ve madde basarisiz olmustur.

NEDEN AYRI BIR ARAC (loadtest/fleet.py NEDEN CEVAP VEREMEZ)
-----------------------------------------------------------
`fleet.py` fizik uretecini kullanir ama her yayinda fizigi 15 SIMULE DAKIKA
ilerletir (PhysicsPayloadFactory.SIM_STEP_S = 900) — 300 saniyelik bir kosuda
10 s'lik adimlarla hicbir seyin degismemesi icin bilincli bir karar. Bu, PLATFORM
olcumu icin dogrudur ama VERI BUTCESI icin yanlis bir olcu aletidir: 15 dakikada
bir baglanti sicakligi olu bandi zaten asar, yani bastirma olcumu sistematik
olarak KUCUK cikar. Olu bant rejimi ancak gercek 10 s'lik ornekleme ile olculur.
Bu yuzden olcum burada yapilir; platform olcumu `fleet.py`de kalir.

Bu arac BROKER, VERITABANI VE BACKEND ISTEMEZ: tek surecte, deterministiktir ve
ayni tohumla ayni sayilari verir.

DURUSTLUK
---------
  * "Filo toplami aylik maliyet" bir CARPIMDIR, olcum degildir: pano basina
    olculen aylik bayt x pano sayisi. Cikti bunu `carpim` anahtari altinda ayri
    tutar ve `olculen` ile karistirmaz (GK10).
  * Faturalanan bayt TAHMINDIR: TCP/IP + TLS + ACK icin mesaj basina sabit bir
    ek yuk varsayilir (docs/09 §6 ile ayni sayi). Olculen JSON ve MQTT baytidir.
  * Olcum iki rejimde yapilir. Aylik maliyet S0'dan (normal isletme) turetilir,
    cunku filonun buyuk cogunlugu zamanin buyuk cogunlugunda oradadir. Ariza
    rejimi alarm aninin degismedigini gostermek icindir, butce icin degil.

Calistirma (repo kokunden; yigin AYAKTA OLMAK ZORUNDA DEGIL):
    backend/.venv/Scripts/python loadtest/veri_butcesi.py
    backend/.venv/Scripts/python loadtest/veri_butcesi.py --panolar 5 --gun 9 --hizli
Sonuc: loadtest/results/veri-butcesi-<run_id>.json (git disi).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "libs" / "panoalgo"))
sys.path.insert(0, str(ROOT / "loadtest"))

# MQTT cerceve hesabi KOPYALANMAZ: loadtest/storage.py'deki testli fonksiyon
# kullanilir (backend/tests/test_loadtest_storage.py). Iki kopya olsaydi biri
# degistiginde docs/09'un iki tablosu sessizce celisirdi.
from storage import mqtt_publish_bytes  # noqa: E402

from panoalgo.detect import load_thresholds  # noqa: E402
from panoalgo.edge import EdgePipeline  # noqa: E402
from panoalgo.generator import PanelSimulator, default_contracts_dir  # noqa: E402
from panoalgo.reporting import (  # noqa: E402
    DEADBAND_FRACTION,
    DEFAULT_MAX_SILENCE_S,
    ReportGate,
    ReportPolicy,
    deadband_fields,
    deadband_for,
)

# Kenarin TESPIT periyodu. Bu sayi F-36'nin dokunmadigi sabittir: seyrelen
# yalnizca yayindir (bkz. reporting.py "TESPITE DOKUNMAZ").
DETECTION_PERIOD_S = 10.0

# TCP/IP (40) + TLS kaydi (29) + ACK (~40). TAHMINDIR, olcum degildir (docs/09 §6).
BILLABLE_OVERHEAD_B = 110

TOPIC_TEMPLATE = "gridup/pano/{pano_id}/tel"
SECONDS_PER_MONTH = 30.0 * 24.0 * 3600.0

# Olculen olu bant kesirleri: %2 teslim edilen varsayilan, digerleri egriyi verir.
FRACTIONS = (0.01, 0.02, 0.05, 0.10)


@dataclass
class Sayac:
    """Tek bir yayin politikasinin muhasebesi."""

    ad: str
    kapi: ReportGate
    mesaj: int = 0
    json_b: int = 0
    mqtt_b: int = 0

    # Alarm kodu -> kodun ILK YAYINLANDIGI tur numarasi.
    alarm_turu: dict[str, int] = None
    # Alan -> sifirinci derece tutmayla geri kurmada gorulen en buyuk mutlak hata.
    kurma_hatasi: dict[str, float] = None
    # Pano -> son yayinlanan alan fotografi (geri kurma hatasi icin).
    _son: dict[str, dict[str, float]] = None

    def __post_init__(self) -> None:
        self.alarm_turu = {}
        self.kurma_hatasi = {}
        self._son = {}

    @property
    def faturalanan_b(self) -> int:
        return self.mqtt_b + self.mesaj * BILLABLE_OVERHEAD_B

    def gozle(self, payload: dict, body: bytes, topic: str, tur: int, yayinla: bool) -> None:
        """Bir turu isler: yayinlandiysa sayar, yayinlanmadiysa geri kurma hatasini buyutur."""
        pano_id = payload["pano_id"]
        simdi = deadband_fields(payload)

        if yayinla:
            self.mesaj += 1
            self.json_b += len(body)
            self.mqtt_b += mqtt_publish_bytes(payload_bytes=len(body), topic=topic)
            self._son[pano_id] = simdi
            for kod in payload.get("alarms") or []:
                self.alarm_turu.setdefault(kod, tur)
            return

        # Yayinlanmadi: merkez son yayinlanan degeri gormeye devam eder. Aradaki
        # fark, uyarlanabilir raporlamanin merkeze ODETTIGI hatanin ta kendisidir.
        onceki = self._son.get(pano_id) or {}
        for anahtar, deger in simdi.items():
            before = onceki.get(anahtar)
            if before is None:
                continue
            hata = abs(deger - before)
            if hata > self.kurma_hatasi.get(anahtar, 0.0):
                self.kurma_hatasi[anahtar] = hata

    def ozet(self, sure_s: float, panolar: int) -> dict[str, Any]:
        aylik = SECONDS_PER_MONTH / sure_s if sure_s > 0 else 0.0
        return {
            "ad": self.ad,
            "mesaj": self.mesaj,
            "json_mb": round(self.json_b / 1e6, 3),
            "mqtt_mb": round(self.mqtt_b / 1e6, 3),
            "faturalanan_mb": round(self.faturalanan_b / 1e6, 3),
            "pano_basina_aylik_mb": round(self.faturalanan_b * aylik / panolar / 1e6, 1),
            "bastirilan_oran": round(self.kapi.suppressed / max(1, self.kapi.decided), 4),
            "gerekce_dagilimi": dict(sorted(self.kapi.by_reason.items())),
            "alarm_turu": dict(sorted(self.alarm_turu.items())),
            "azami_geri_kurma_hatasi": {
                k: round(v, 6) for k, v in sorted(self.kurma_hatasi.items(), key=lambda x: -x[1])[:8]
            },
        }


def _kapilar(contracts_dir: Path, max_silence_s: float) -> list[Sayac]:
    """Sabit (bugunku davranis) + her olu bant kesri icin bir kapi."""
    sayaclar = [Sayac("sabit-10s", ReportGate(ReportPolicy.passthrough()))]
    for fraction in FRACTIONS:
        policy = ReportPolicy.from_contracts(
            contracts_dir, max_silence_s=max_silence_s, fraction=fraction
        )
        sayaclar.append(Sayac(f"uyarlanabilir-%{fraction * 100:g}", ReportGate(policy)))
    return sayaclar


def _ariza_surer(sim: PanelSimulator, nokta: str, carpan: float) -> None:
    """Baglantinin isil direncini kademeli buyutur (gevsek baglanti benzetimi).

    fleet.py'deki enjeksiyonla AYNI mekanizma (`set_k_multiplier`), farki kademeli
    olmasi: F-36 icin onemli olan alarmin ATLAMA ile degil SURUNME ile gelmesidir;
    olu bandin bir surunmeyi gizleyip gizlemedigi ancak boyle olculur.
    """
    sim.set_k_multiplier(nokta, carpan)


def kosu(
    *,
    panolar: int,
    gun: float,
    isinma_gun: float,
    period_s: float,
    max_silence_s: float,
    tohum: int,
    ariza: bool,
    contracts_dir: Path,
    _adim_s: float | None = None,
) -> dict[str, Any]:
    """Tek bir rejimi kosturur ve tum politikalarin muhasebesini doner.

    `_adim_s` yalnizca TEST icindir: uretec adimini beyan edilen periyottan
    ayirir ve asagidaki emniyet kontrolunun gercekten calistigini gosterir.
    Uretimde her zaman `period_s`e esittir.
    """
    adim_s = period_s if _adim_s is None else _adim_s
    baslangic = datetime(2026, 4, 6, 0, 0, tzinfo=timezone.utc)  # Pazartesi, gecis mevsimi
    sims = [
        PanelSimulator(
            pano_id=f"SIM-{n + 1:05d}",
            seed=tohum + n,
            profile=("konut", "ticari", "karma")[n % 3],
            start=baslangic,
            contracts_dir=contracts_dir,
        )
        for n in range(panolar)
    ]
    pipeline = EdgePipeline(profile="karma", contracts_dir=contracts_dir, period_s=period_s)
    sayaclar = _kapilar(contracts_dir, max_silence_s)

    turlar = int(gun * 24.0 * 3600.0 / period_s)
    isinma_turu = int(isinma_gun * 24.0 * 3600.0 / period_s)
    olcum_turu = turlar - isinma_turu
    if olcum_turu <= 0:
        raise SystemExit("olcum penceresi bos: --gun, --isinma-gun'den buyuk olmali")

    ariza_noktasi = "DSYA3_L2"
    olculen = 0
    bosluklu = [0, 0]   # [bosluklu bayt, sikistirilmis bayt] - kodlama farki icin

    for tur in range(turlar):
        simule_s = tur * period_s
        if not pipeline.baseline_frozen and tur >= isinma_turu:
            # Taban K0 burada sabitlenir: oncesi devreye alma penceresidir ve
            # k_ratio 1,0 kalir. Butceyi taban DONDUKTAN sonra olcuyoruz, cunku
            # k_ratio'nun hic oynamadigi bir pencerede bastirma YAPAY olarak
            # yuksek cikardi (GK10: olculen sey gercek rejim olmali).
            pipeline.freeze_baselines()

        for index, sim in enumerate(sims):
            if ariza and index == 0 and tur >= isinma_turu:
                ilerleme = (tur - isinma_turu) / max(1, olcum_turu)
                _ariza_surer(sim, ariza_noktasi, 1.0 + 6.0 * ilerleme)

            payload = pipeline.process(sim.step(adim_s))
            if tur < isinma_turu:
                continue

            topic = TOPIC_TEMPLATE.format(pano_id=payload["pano_id"])
            body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
            # Kodlama farki OLCULUR, varsayilmaz: depodaki simulator yayincisi
            # (sim/panosim.py Publisher.send) bosluklu json.dumps kullanir ve daha
            # buyuktur. Butce SIKISTIRILMIS bicimle raporlanir (saha cihazinin
            # yapacagi sey ve docs/09 §6'nin mevcut tabani budur); fark ciktida
            # ayrica yazilir ki iki sayi karistirilmasin.
            bosluklu[0] += len(json.dumps(payload, allow_nan=False).encode("utf-8"))
            bosluklu[1] += len(body)
            for sayac in sayaclar:
                karar = sayac.kapi.decide(payload, simule_s)
                sayac.gozle(payload, body, topic, tur - isinma_turu, karar.publish)

        if tur >= isinma_turu:
            olculen += 1

    # OLCUMUN KENDI EMNIYETI: boru hatti, beyan ettigi periyotla islendi mi?
    # Bos degilse yayin karari islemeyi seyreltmis demektir ve olculen oran
    # gecersizdir — sayilari yazdirmak yerine patlamak dogrusu (GK10).
    if pipeline.period_mismatch:
        raise SystemExit(
            f"tespit periyodu kaydi: {pipeline.period_mismatch}; "
            "yayin karari isleme ritmini degistirmis, olcum gecersiz"
        )

    sure_s = olculen * period_s
    nokta_sayisi = len(payload["t_conn"])
    return {
        "panolar": panolar,
        "olcum_penceresi_saat": round(sure_s / 3600.0, 1),
        "isinma_gun": isinma_gun,
        "tespit_periyodu_s": period_s,
        "azami_sessizlik_s": max_silence_s,
        "ariza_rejimi": ariza,
        "ornek": olculen * panolar,
        "nokta_sayisi": nokta_sayisi,
        "json_kodlama_farki": {
            "not": "Butce SIKISTIRILMIS JSON ile raporlanir; sim/panosim.py bosluklu yayinlar.",
            "bosluklu_buyume_orani": round(bosluklu[0] / bosluklu[1], 4) if bosluklu[1] else None,
        },
        "politikalar": [s.ozet(sure_s, panolar) for s in sayaclar],
    }


def _olu_bant_tablosu(contracts_dir: Path, max_silence_s: float) -> dict[str, float]:
    """Teslim edilen varsayilan politikanin olu bantlari (docs/09 tablosu icin)."""
    policy = ReportPolicy.from_contracts(contracts_dir, max_silence_s=max_silence_s)
    ornek = {
        "t_conn.X.dt_c": policy.dt_c_k, "t_conn.X.t_c": policy.t_c_k,
        "t_conn.X.k_ratio": policy.k_ratio, "t_conn.X.ttl_h": policy.ttl_h,
        "elec.i_ph.0": policy.current_a, "elec.thd_i.0": policy.thd_pct,
        "env.t_low_c": policy.env_t_k, "env.td_margin_k": policy.td_margin_k,
        "env.rh_low_pct": policy.rh_pct,
    }
    return {k: round(v, 6) for k, v in ornek.items()}


def alarm_gecikmesi(rejim: dict[str, Any]) -> dict[str, Any]:
    """Her alarm kodunun ILK YAYINLANDIGI turu politikalar arasinda karsilastirir.

    F-36'nin en riskli iddiasi "olu bant hicbir alarmi geciktirmez"dir. Burada
    VARSAYILMAZ, olculur: sabit kipte kod hangi turda ilk kez yayinlandiysa
    uyarlanabilir kipte de ayni turda yayinlanmis olmali. Fark varsa `gecikenler`
    dolar ve cikti bunu saklamaz.
    """
    politikalar = rejim["politikalar"]
    taban = next(p for p in politikalar if p["ad"] == "sabit-10s")["alarm_turu"]
    gecikenler = []
    for p in politikalar:
        if p["ad"] == "sabit-10s":
            continue
        for kod, tur in taban.items():
            gorulen = p["alarm_turu"].get(kod)
            if gorulen != tur:
                gecikenler.append(
                    {"politika": p["ad"], "kod": kod, "sabit_tur": tur, "uyarlanabilir_tur": gorulen}
                )
    return {
        "karsilastirilan_kod": sorted(taban),
        "gecikenler": gecikenler,
        "sonuc": "alarm ani DEGISMEDI" if not gecikenler else "ALARM GECIKTI",
    }


def _carpim(normal: dict[str, Any], filo: int) -> dict[str, Any]:
    """Filo toplami: OLCUM DEGIL CARPIM. Ayri anahtar altinda tutulur (GK10)."""
    sabit = next(p for p in normal["politikalar"] if p["ad"] == "sabit-10s")
    uyar = next(p for p in normal["politikalar"] if p["ad"] == f"uyarlanabilir-%{DEADBAND_FRACTION * 100:g}")
    return {
        "not": "Bu bir CARPIMDIR, olcum degildir: pano basina olculen aylik bayt x pano sayisi.",
        "filo_panosu": filo,
        "sabit_10s_gb_ay": round(sabit["pano_basina_aylik_mb"] * filo / 1000.0, 1),
        "uyarlanabilir_gb_ay": round(uyar["pano_basina_aylik_mb"] * filo / 1000.0, 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F-36 veri butcesi olcumu")
    parser.add_argument("--panolar", type=int, default=5)
    parser.add_argument("--gun", type=float, default=9.0, help="toplam simule gun")
    parser.add_argument("--isinma-gun", type=float, default=7.0,
                        help="taban ogrenme penceresi; butce BUNDAN SONRASI icin olculur")
    parser.add_argument("--period", type=float, default=DETECTION_PERIOD_S,
                        help="TESPIT periyodu (s); F-36 buna dokunmaz")
    parser.add_argument("--azami-sessizlik", type=float, default=DEFAULT_MAX_SILENCE_S)
    parser.add_argument("--tohum", type=int, default=20260918)
    parser.add_argument("--filo", type=int, default=1000, help="carpim icin pano sayisi")
    parser.add_argument("--hizli", action="store_true",
                        help="kisa kosu (duman testi); sayilar RAPORLANMAZ")
    parser.add_argument("--out", default=str(ROOT / "loadtest" / "results"))
    args = parser.parse_args(argv)

    if args.hizli:
        args.gun, args.isinma_gun, args.panolar = 0.06, 0.03, 2

    contracts_dir = default_contracts_dir()
    ortak = dict(
        panolar=args.panolar, gun=args.gun, isinma_gun=args.isinma_gun,
        period_s=args.period, max_silence_s=args.azami_sessizlik,
        tohum=args.tohum, contracts_dir=contracts_dir,
    )

    print(f"[butce] normal rejim: {args.panolar} pano x {args.gun} gun, {args.period} s tespit", flush=True)
    normal = kosu(ariza=False, **ortak)
    print(f"[butce] ariza rejimi: ayni kurulum, 1 panoda surunen gevsek baglanti", flush=True)
    arizali = kosu(ariza=True, **ortak)

    thresholds = load_thresholds(contracts_dir)
    sonuc = {
        "arac": "loadtest/veri_butcesi.py",
        "surum": 1,
        "tohum": args.tohum,
        "olu_bant_kesri_varsayilan": DEADBAND_FRACTION,
        "olu_bantlar": _olu_bant_tablosu(contracts_dir, args.azami_sessizlik),
        "sozlesme_sessizlik_zaman_asimi_s": float(thresholds["heartbeat_timeout_min"]) * 60.0,
        "bayt_muhasebesi": {
            "json": "compact JSON (separators=',',':'), UTF-8 — OLCULDU",
            "mqtt": "loadtest/storage.py mqtt_publish_bytes (QoS 1 PUBLISH cercevesi) — OLCULDU",
            "faturalanan": f"+{BILLABLE_OVERHEAD_B} B/mesaj TCP/IP+TLS+ACK — TAHMIN, olcum degil",
        },
        "normal_rejim": normal,
        "ariza_rejimi": arizali,
        "alarm_gecikmesi": {
            "normal": alarm_gecikmesi(normal),
            "ariza": alarm_gecikmesi(arizali),
        },
        "filo_carpimi": _carpim(normal, args.filo),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    run_id = f"veri-butcesi-{args.panolar}p-{args.gun:g}g-{args.tohum}"
    hedef = out / f"{run_id}.json"
    hedef.write_bytes(json.dumps(sonuc, indent=2, ensure_ascii=False).encode("utf-8"))

    for rejim, veri in (("normal", normal), ("ariza", arizali)):
        print(f"\n=== {rejim} rejim ({veri['olcum_penceresi_saat']} saat, {veri['ornek']} ornek) ===")
        for p in veri["politikalar"]:
            print(f"  {p['ad']:22s} mesaj {p['mesaj']:7d}  faturalanan {p['faturalanan_mb']:8.2f} MB"
                  f"  pano/ay {p['pano_basina_aylik_mb']:7.1f} MB  bastirilan %{p['bastirilan_oran'] * 100:.1f}")
    print(f"\n[butce] yazildi: {hedef}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
