#!/usr/bin/env python3
"""Mesaj basina ingest maliyetini olcer ve KANIT DOSYASI birakir.

    # konteyner icinde (backend ile AYNI calisma zamani — tercih edilen):
    docker cp loadtest/ingest_maliyeti.py gridup-backend:/tmp/
    docker exec gridup-backend python /tmp/ingest_maliyeti.py --out /tmp/m.json
    docker cp gridup-backend:/tmp/m.json loadtest/results/

    # host'tan (backend/.venv ile; calisma zamani FARKLIDIR, sayilar karsilastirilamaz):
    backend/.venv/Scripts/python loadtest/ingest_maliyeti.py --no-db

NEDEN VAR (20 Eylul):
    docs/09 §4.4 "mesaj basina 615 us, bunun 501 us'i sema dogrulamasi" diyordu.
    Sayi dogru olabilir — ama onu ureten BETIK depoda yoktu. Yani kimse, yazanlar
    dahil, o sayiyi yeniden turetemezdi: hangi calisma zamaninda, hangi yukle,
    kac tekrarla olculdugu kayitli degildi. Bir hafta sonra sayi degistiginde
    "yavasladi mi yoksa farkli mi olctuk" sorusu CEVAPSIZ kaldi.

    Bu betik o boslugu kapatir. Ayrica bilerek TEK SAYI yerine ARALIK basar:
    20 Eylul'de ayni makinede ayni olcum 941 us ile 1.717 us arasinda oynadi.
    Tek sayi yayimlamak, o oynamayi gizlemek olurdu.

OLCULEN ADIMLAR — hepsi backend/app/ingest.py `_parse` icindeki GERCEK cagrilar:
    json.loads          ham bayt -> dict
    _contains_nul       NUL taramasi (yukun tamamini gezer)
    sema dogrulamasi    best_match(validator.iter_errors(payload)) — `validate()`
                        DEGIL, cunku uretim kodu bunu kullanir
    flatten             dict -> uzun format TelemetryRow demeti
    write_batch         (--db ile) gercek COPY + upsert yolu, parti 500
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _kokler() -> tuple[Path, Path]:
    """(sema yolu, app'in bulundugu dizin) — konteynerde ve depoda calisir."""
    if Path("/contracts/mqtt-telemetry.schema.json").is_file():
        return Path("/contracts/mqtt-telemetry.schema.json"), Path("/srv")
    kok = Path(__file__).resolve().parents[1]
    return kok / "contracts" / "mqtt-telemetry.schema.json", kok / "backend"


def _ornek_yuk(nokta: int) -> dict:
    """Fikstur yerine SOZLESMEDEN turetilmis sentetik yuk: betik veriye bagli olmasin.

    Alanlar contracts/mqtt-telemetry.schema.json'daki `required` listelerinden
    birebir gelir; sema `additionalProperties: false` oldugu icin fazlasi da
    yazilamaz. Betik main()'de kendi yukunu DOGRULAR: uymazsa hata verip cikar,
    yanlis bir sayi basmaz.
    """
    simdi = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "v": 1,
        "ts": simdi,
        "pano_id": "SIM-90001",
        "seq": 1,
        "fw": "0.0.0",
        "t_conn": [
            {
                "pt": f"DSYA{i}_L{(i % 3) + 1}",
                "t_c": 44.0 + i,
                "dt_c": 23.0 + i,
                "k": 0.00012,
                "k_ratio": 1.0 + i / 100,
                "tau_s": 1800.0,
                "ttl_h": None,
                "excited": True,
                "q": 0,
            }
            for i in range(1, nokta + 1)
        ],
        "elec": {
            "i_ph": [612.0, 655.0, 598.0],
            "i_n": 48.0,
            "u_ph": [229.5, 229.9, 230.1],
            "thd_i": [6.8, 6.1, 5.9],
            "cosphi": 0.96,
            "unbal_pct": 1.2,
        },
        "env": {
            "t_low_c": 21.0,
            "rh_low_pct": 55.0,
            "t_up_c": 26.0,
            "rh_up_pct": 48.0,
            "td_low_c": 11.6,
            "td_margin_k": 7.9,
        },
        "health": {"uptime_s": 86400, "nodes_ok": nokta, "nodes_total": nokta, "rssi_dbm": -71},
    }


def olc(fn, tekrar: int, tur: int) -> dict:
    """Her turu ayri olcer ve ARALIGI dondurur — tek sayi yaniltir."""
    turlar = []
    for _ in range(tur):
        t0 = time.perf_counter()
        for _ in range(tekrar):
            fn()
        turlar.append((time.perf_counter() - t0) / tekrar * 1e6)
    return {
        "us_medyan": round(statistics.median(turlar), 1),
        "us_min": round(min(turlar), 1),
        "us_maks": round(max(turlar), 1),
        "tur": tur,
        "tekrar": tekrar,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--points", type=int, default=7, help="pano basina baglanti noktasi")
    p.add_argument("--repeat", type=int, default=1500, help="tur basina tekrar")
    p.add_argument("--rounds", type=int, default=5, help="tur sayisi (aralik icin)")
    p.add_argument("--no-db", action="store_true", help="write_batch olcumunu atla")
    p.add_argument("--out", default="", help="JSON kanit dosyasi yolu")
    a = p.parse_args(argv)

    sema_yolu, app_kok = _kokler()
    sys.path.insert(0, str(app_kok))
    import jsonschema
    from jsonschema.exceptions import best_match

    from app.ingest import _contains_nul, flatten  # noqa: PLC0415
    from app.models import Sample  # noqa: PLC0415

    sema = json.loads(sema_yolu.read_text(encoding="utf-8"))
    dogrulayici = jsonschema.validators.validator_for(sema)(sema)

    payload = _ornek_yuk(a.points)
    ham = json.dumps(payload, separators=(",", ":")).encode()
    if best_match(dogrulayici.iter_errors(payload)) is not None:
        print("HATA: uretilen ornek yuk semaya UYMUYOR — betik bozuk", file=sys.stderr)
        return 1
    satirlar = flatten(payload)

    sonuc: dict = {
        "arac": "loadtest/ingest_maliyeti.py",
        "surum": 1,
        "calisma_zamani": {
            "python": sys.version.split()[0],
            "jsonschema": getattr(jsonschema, "__version__", "?"),
            "konteyner_icinde": app_kok == Path("/srv"),
        },
        "yuk": {"bayt": len(ham), "nokta": a.points, "satir_mesaj_basina": len(satirlar)},
        "adimlar": {},
    }

    sonuc["adimlar"]["json_loads"] = olc(lambda: json.loads(ham), a.repeat, a.rounds)
    sonuc["adimlar"]["contains_nul"] = olc(lambda: _contains_nul(payload), a.repeat, a.rounds)
    sonuc["adimlar"]["sema_dogrulamasi"] = olc(
        lambda: best_match(dogrulayici.iter_errors(payload)), a.repeat, a.rounds
    )
    sonuc["adimlar"]["flatten"] = olc(lambda: flatten(payload), a.repeat, a.rounds)

    toplam = sum(v["us_medyan"] for v in sonuc["adimlar"].values())
    sonuc["parse_toplami_us"] = round(toplam, 1)
    sonuc["tek_thread_tavani_msj_s"] = round(1e6 / toplam)

    if not a.no_db:
        dsn = os.environ.get("DB_DSN") or os.environ.get("GRIDUP_DB_DSN")
        if not dsn:
            print("uyari: DB_DSN yok, write_batch olcumu atlandi", file=sys.stderr)
        else:
            from app.db import PgStore  # noqa: PLC0415

            store = PgStore(dsn)
            simdi = datetime.now(timezone.utc)
            N = 500
            sureler = []
            for tur in range(a.rounds):
                grup = [
                    Sample(
                        pano_id="SIM-9%04d" % (i % 200),
                        ts=simdi,
                        seq=tur * 100000 + i,
                        received_at=simdi,
                        topic="gridup/telemetry/SIM-9%04d" % (i % 200),
                        payload=payload,
                        rows=satirlar,
                    )
                    for i in range(N)
                ]
                t0 = time.perf_counter()
                store.write_batch(grup, [])
                sureler.append(time.perf_counter() - t0)
            medyan = statistics.median(sureler)
            sonuc["write_batch"] = {
                "parti": N,
                "tur": a.rounds,
                "parti_ms_medyan": round(medyan * 1000, 1),
                "mesaj_basina_us": round(medyan / N * 1e6, 1),
                "tavan_msj_s": round(N / medyan),
                "not": "SIM-9xxxx kimlikleri yazildi; 'fleet.py --cleanup-only' temizler",
            }

    metin = json.dumps(sonuc, ensure_ascii=False, indent=1)
    if a.out:
        Path(a.out).write_text(metin, encoding="utf-8")
        print(f"yazildi: {a.out}")
    print(metin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
