#!/usr/bin/env python3
"""Altin demo veritabani ureteci (F-01, Kisi B).

Tek komutla: bekleyen tum sema gocleri + >=7 gunluk gecmis + taban ogrenmesi TAMAMLANMIS,
tekrar uretilebilir (tohumlu) bir demo veritabani.

    backend/.venv/Scripts/python scripts/seed_demo.py --dsn postgresql://postgres:gridup@localhost:5432/gridup --reset
    backend/.venv/Scripts/python scripts/seed_demo.py --dry-run          # veritabanina dokunmaz, ozet basar

NEDEN GEREKLI
-------------
Taban ogrenme sozlesmede 7 gundur (thresholds.baseline_learning_days: K0 = 7 gunluk medyan) ve canli
yiginda GERCEK saatler surer. Taze bir `down -v` sonrasi K/K0 bir hafta boyunca 1,0 doner: erken uyari
hikayesinin tamami olculemez. Rapor ureten her madde sessizce "en az bir hafta temiz veri" varsayar;
bu betik o zemini bir kez, tekrar uretilebilir bicimde uretir.

VERITABANINA DOGRUDAN YAZIYORUZ, MQTT'DEN AKITMIYORUZ — NEDEN
-------------------------------------------------------------
1) BACKFILL KURALI. app/db.py `_UPSERT_LATEST` ve alarm_manager.observe, panonun son islenen ts'inden
   ESKI ornegin canli durumu degistirmesine izin vermez (observe onu `backfill_ignored` sayar). MQTT'den
   akitirken sim/panosim.py varsayilan olarak `ts`i DUVAR SAATIyle damgalar (K3 karari): gecmis diye
   yayinladigimiz her mesaj "su an" olarak yazilir, 7 gunluk gecmis olusmaz. `--sim-clock` ile simule
   zaman damgasi yayinlansa bile ornekler duvar saatinin ONUNE gecer (ileri tarihli satirlar) ve bu kez
   sonradan gelen CANLI veri backfill kuralina takilir.
2) TEKRAR URETILEBILIRLIK. Broker + kuyruk + toplu yazma yolu kayipli ve zamanlamaya baglidir
   (ingest kuyrugu dolarsa mesaj DUSURULUR). "Ayni tohum -> ayni satir sayisi" sozunu ancak
   deterministik bir yazma yolu verebilir.
3) SURE. 21 gunluk gecmis 15 dk'lik ornekleme ile pano basina 2.016 mesajdir; broker uzerinden
   gercek zamanli akitmak demoyu bir tesliminden uzun surdururdu.

Buna karsilik URETIM YOLUNDAN SAPMIYORUZ: yuk panoalgo fizik ureteci + kenar tespit boru hattindan
(EdgePipeline) cikar, contracts/mqtt-telemetry.schema.json'a karsi DOGRULANIR, etiketlere
app.ingest.flatten ile ayrilir, app.db.PgStore.write_batch ile yazilir; alarmlar uretimdeki
app.risk.RiskEngine + app.alarm_manager.AlarmManager ile uretilip PgStore.save_alarm_changes ile
kaydedilir. Yani bu betik veriyi UYDURMAZ, MQTT adimini atlar.

PENCERE. Uretilen gecmis `--end` aninda biter (varsayilan: simdi, ornekleme adimina yuvarlanmis).
Gelecege tarihli satir URETILMEZ: aksi halde canli simulatorun sonraki mesajlari backfill kuralina
takilir ve arayuz gunlerce guncellenmez.

GK10. Uretilen her satir sentetiktir. Kunye `demo_seed` tablosunda (deploy/initdb/006_demo_seed.sql) ve
her panonun `panels.notes` alanindadir; betik bitiste ayni cumleyi ekrana basar.

NE URETMEZ. `notifications` tablosu BOS kalir: teslim gecikmesi ancak gercek bir bildirim ag gecidi
(sanal GSM modem) calistiginda olculur, uydurulmaz. "Uctan uca bildirim p95" paneli bu yuzden demo
veritabaninda bos gorunur; canli yigin acilinca dolar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "libs" / "panoalgo"))

import psycopg  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

from app.alarm_manager import AlarmManager, Change  # noqa: E402
from app.config import PANO_ID_PLACEHOLDER, Contracts, load_contracts  # noqa: E402
from app.db import PgStore  # noqa: E402
from app.ingest import flatten  # noqa: E402
from app.models import Sample  # noqa: E402
from app.risk import RiskEngine  # noqa: E402
from panoalgo import scenarios  # noqa: E402

INITDB_DIR = ROOT / "deploy" / "initdb"
CONTRACTS_DIR = ROOT / "contracts"

SCRIPT = "scripts/seed_demo.py"
ORIGIN = "sentetik: fizik tabanli uretecten (libs/panoalgo), sahadan olculmus degildir"
SCENARIO = "S0_normal"          # saglikli filo: demo zemini "temiz veri" olmali (F-01)
DEFAULT_SEED = 1304
DEFAULT_DAYS = 21
WRITE_BATCH = 500               # app/ingest.py max_batch ile ayni parti buyuklugu

# Yazilan tablolar. `--reset` bunlari bosaltir; panels KORUNUR (yabanci anahtar ebeveyni, ustune yazilir).
SEEDED_TABLES = ("alarm_journal", "notifications", "alarms", "events", "panel_latest", "telemetry", "demo_seed")


@dataclass(frozen=True)
class DemoPanel:
    """001_schema.sql'deki baslangic panolariyla ayni kimlikler: demo hep ayni filoyu gosterir."""

    pano_id: str
    name: str
    lat: float
    lon: float
    seed_offset: int


DEMO_FLEET = (
    DemoPanel("ADM-00001", "Efeler TM-14", 37.8450, 27.8396, 0),
    DemoPanel("ADM-00002", "Nazilli TM-07", 37.9150, 28.3200, 1),
    DemoPanel("GDZ-00001", "Bornova TM-22", 38.4700, 27.2200, 2),
)


@dataclass(frozen=True)
class Summary:
    """Tekrar uretilebilirlik kaniti: ayni tohum + ayni pencere -> bu sozlugun tamami ayni."""

    scenario: str
    seed: int
    days: float
    panels: int
    samples: int
    telemetry_rows: int
    alarms: int
    journal_entries: int
    baseline_day: int
    sample_period_s: float
    window_start: str
    window_end: str
    digest: str


# --------------------------------------------------------------------- uretim
def _telemetry_topic(contracts: Contracts, pano_id: str) -> str:
    """Sozlesmedeki periyodik telemetri topic'i; topic metni burada YAZILI DEGILDIR (PLAN.md kural 10)."""
    template = next(t for t in contracts.ingest_topics if t.rstrip("/").endswith("/tel"))
    return template.replace(PANO_ID_PLACEHOLDER, pano_id)


def _window_end(raw: str | None, period_s: float) -> datetime:
    """Pencerenin bitisi; ornekleme adimina yuvarlanir. Gelecege tarihli satir uretilmez."""
    end = datetime.now(timezone.utc) if raw is None else datetime.fromisoformat(raw)
    if end.tzinfo is None:
        raise SystemExit("--end saat dilimi tasimali, ornek: 2026-09-15T12:00:00+00:00")
    end = end.astimezone(timezone.utc)
    return datetime.fromtimestamp(end.timestamp() // period_s * period_s, tz=timezone.utc)


def _plan(panel: DemoPanel, seed: int, days: float, baseline_h: float) -> scenarios.ScenarioPlan:
    """Taban ogrenme suresi SOZLESMEDEN gelir, senaryonun `duration/3` kisaltmasindan degil.

    scenarios.plan kisa fixture'lar sucuk kalmasin diye tabani `min(sozlesme, sure/3)` ile kisaltir;
    burada tam tersini istiyoruz: demo veritabaninin sozu "taban ogrenmesi TAMAMLANDI"dir, yani
    K0 tam 7 gunluk medyandan donmus olmalidir.
    """
    return scenarios.plan(
        SCENARIO,
        seed=seed + panel.seed_offset,
        duration_h=days * 24.0,
        contracts_dir=CONTRACTS_DIR,
        pano_id=panel.pano_id,
        baseline_h=baseline_h,
    )


def generate(contracts: Contracts, fleet: tuple[DemoPanel, ...], seed: int, days: float,
             end: datetime) -> Iterator[list[Sample]]:
    """Filonun gecmisini ZAMAN SIRASINDA verir: her adimda tum panolarin o andaki ornegi.

    Panolar adim adim ic ice gecer, pano pano degil — gercek bir filoda alarm kimlikleri de
    zamanda artar, tek panonun tum gecmisi digerinden once yazilmaz.
    """
    baseline_h = float(contracts.thresholds["baseline_learning_days"]) * 24.0
    validator = Draft202012Validator(contracts.telemetry_schema)
    plans = [_plan(panel, seed, days, baseline_h) for panel in fleet]
    topics = {panel.pano_id: _telemetry_topic(contracts, panel.pano_id) for panel in fleet}
    step = timedelta(seconds=scenarios.EXPORT_PERIOD_S)
    steps = plans[0].steps

    for row in zip(*(scenarios.iter_samples(plan) for plan in plans)):
        samples = []
        for sample in row:
            if sample.payload is None:     # haberlesme boslugu: sahte deger URETILMEZ
                continue
            ts = end - (steps - 1 - sample.index) * step
            payload = dict(sample.payload)
            payload["ts"] = ts.isoformat(timespec="seconds")
            errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
            if errors:
                raise SystemExit(f"[seed] sema ihlali {list(errors[0].absolute_path)}: {errors[0].message}")
            pano_id = payload["pano_id"]
            samples.append(Sample(
                pano_id=pano_id, ts=ts, seq=payload["seq"], received_at=ts,
                topic=topics[pano_id], payload=payload, rows=flatten(payload),
            ))
        yield samples


def _digest_sample(digest: "hashlib._Hash", sample: Sample) -> None:
    digest.update(json.dumps(sample.payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _digest_changes(digest: "hashlib._Hash", changes: list[Change]) -> None:
    for change in changes:
        alarm = change.alarm
        digest.update(f"|{change.kind}:{alarm.id}:{alarm.code}:{alarm.point}:{alarm.state}".encode("utf-8"))


# ------------------------------------------------------------------ veritabani
def apply_migrations(conn: psycopg.Connection) -> list[str]:
    """deploy/initdb/*.sql dosyalarinin TAMAMINI sirayla uygular.

    initdb yalnizca BOS bir volume'de ilk acilista calisir; yerel veritabanlari bu yuzden eksik
    kalir. Dosyalarin hepsi tekrar calistirilabilir yazilmistir (IF NOT EXISTS / ON CONFLICT /
    if_not_exists => TRUE), yani bu "bekleyen gocleri uygula" adimidir — `down -v` gerekmez.
    """
    applied = []
    for path in sorted(INITDB_DIR.glob("*.sql")):
        conn.execute(path.read_text(encoding="utf-8"))
        applied.append(path.name)
    return applied


def reset(conn: psycopg.Connection) -> None:
    """Demo verisini bosaltir. panels korunur; alarm kimlikleri 1'den yeniden baslar."""
    conn.execute(f"TRUNCATE {', '.join(SEEDED_TABLES)} RESTART IDENTITY")


def already_seeded(conn: psycopg.Connection) -> int:
    (rows,) = conn.execute("SELECT count(*) FROM telemetry").fetchone()
    return int(rows)


def upsert_panels(conn: psycopg.Connection, fleet: tuple[DemoPanel, ...], start: datetime, note: str,
                  baseline_day: int) -> None:
    """Pano kimligi + GK10 kunyesi. baseline_day sozlesme degeridir (7 = taban ogrenme tamam)."""
    for panel in fleet:
        conn.execute(
            """
            INSERT INTO panels (pano_id, name, lat, lon, installed_at, baseline_day, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pano_id) DO UPDATE SET
                name = EXCLUDED.name, lat = EXCLUDED.lat, lon = EXCLUDED.lon,
                installed_at = EXCLUDED.installed_at, baseline_day = EXCLUDED.baseline_day,
                notes = EXCLUDED.notes
            """,
            (panel.pano_id, panel.name, panel.lat, panel.lon, start, baseline_day, note),
        )


def sync_alarm_sequence(conn: psycopg.Connection) -> None:
    """alarms.id dizisini yazilan en buyuk kimlige cekerek birakir.

    Alarm kimligini tek yazici olan alarm yoneticisi verir (003_alarms.sql: acilista max(id)+1), yani
    BIGSERIAL dizisi hic ilerlemez. Uretim bunu hic kullanmaz ama demo veritabaninda elle atilan
    `INSERT INTO alarms` (senaryo denemesi, test verisi) dizinin verdigi 1, 2, 3... ile cakisirdi.
    """
    conn.execute("SELECT setval(pg_get_serial_sequence('alarms', 'id'), COALESCE(max(id), 1)) FROM alarms")


def record_summary(conn: psycopg.Connection, summary: Summary) -> None:
    conn.execute(
        """
        INSERT INTO demo_seed (origin, script, scenario, seed, window_start, window_end, sample_period_s,
                               panels, samples, telemetry_rows, alarms, journal_entries, baseline_day, digest)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (ORIGIN, SCRIPT, summary.scenario, summary.seed, summary.window_start, summary.window_end,
         summary.sample_period_s, summary.panels, summary.samples, summary.telemetry_rows,
         summary.alarms, summary.journal_entries, summary.baseline_day, summary.digest),
    )


def verify(conn: psycopg.Connection, contracts: Contracts, summary: Summary) -> int:
    """Betigin verdigi sozu VERITABANINDAN dogrular; tutmuyorsa yuksek sesle dusulur (GK10).

    Kontrol edilen uc soz: (1) gecmis en az `baseline_learning_days` kadar uzun, (2) her panonun son
    yukunde taban ogrenme tamamlanmis, (3) hicbir satir gelecege tarihli degil.
    """
    learning_days = int(contracts.thresholds["baseline_learning_days"])
    problems: list[str] = []

    span_days = (datetime.fromisoformat(summary.window_end) - datetime.fromisoformat(summary.window_start)).days
    if span_days < learning_days:
        problems.append(f"gecmis {span_days} gun, taban ogrenme {learning_days} gun istiyor")

    rows = conn.execute(
        "SELECT pano_id, (payload -> 'health' ->> 'baseline_day')::int FROM panel_latest ORDER BY pano_id"
    ).fetchall()
    for pano_id, baseline_day in rows:
        if baseline_day != learning_days:
            problems.append(f"{pano_id}: baseline_day {baseline_day}, beklenen {learning_days}")

    (future,) = conn.execute("SELECT count(*) FROM telemetry WHERE ts > now()").fetchone()
    if future:
        problems.append(f"{future} satir gelecege tarihli (canli veri backfill kuralina takilir)")

    for problem in problems:
        print(f"[seed] DOGRULAMA HATASI: {problem}", flush=True)
    return 1 if problems else 0


# ----------------------------------------------------------------------- akis
def seed(dsn: str | None, contracts: Contracts, fleet: tuple[DemoPanel, ...], *, seed_value: int,
         days: float, end: datetime, do_reset: bool, quiet: bool = False) -> tuple[Summary, int]:
    """Gecmisi uretir ve (dsn verilmisse) yazar; (ozet, cikis kodu) doner."""
    engine = RiskEngine(contracts)
    digest = hashlib.sha256()
    learning_days = int(contracts.thresholds["baseline_learning_days"])
    step = timedelta(seconds=scenarios.EXPORT_PERIOD_S)
    start = end - (int(days * 24.0 * 3600.0 / scenarios.EXPORT_PERIOD_S) - 1) * step
    note = f"{ORIGIN}; {SCRIPT} --seed {seed_value}"

    store = conn = None
    manager = AlarmManager(contracts, first_id=1)
    if dsn is not None:
        conn = psycopg.connect(dsn, autocommit=True)
        applied = apply_migrations(conn)
        if not quiet:
            print(f"[seed] sema gocleri uygulandi: {', '.join(applied)}", flush=True)
        existing = already_seeded(conn)
        if existing and not do_reset:
            conn.close()
            raise SystemExit(f"[seed] veritabaninda {existing} telemetri satiri var; ustune yazmak tekrar "
                             f"uretilebilirligi bozar. Temizlemek icin --reset verin.")
        if do_reset:
            reset(conn)
        upsert_panels(conn, fleet, start, note, learning_days)
        store = PgStore(dsn)
        manager = AlarmManager(contracts, first_id=store.next_alarm_id())

    samples = telemetry_rows = alarms = journal_entries = 0
    batch: list[Sample] = []
    try:
        for step_samples in generate(contracts, fleet, seed_value, days, end):
            for sample in step_samples:
                _digest_sample(digest, sample)
                samples += 1
                telemetry_rows += len(sample.rows)
                batch.append(sample)
            if len(batch) >= WRITE_BATCH:
                if store is not None:
                    store.write_batch(batch, ())
                batch = []
            for sample in step_samples:
                changes = manager.observe(sample.pano_id, sample.ts, engine.evaluate(sample),
                                          now=sample.ts, maint_mode=False)
                changes += manager.tick(sample.ts)
                if not changes:
                    continue
                _digest_changes(digest, changes)
                alarms += sum(1 for c in changes if c.kind == "raised")
                journal_entries += len(changes)
                if store is not None:
                    store.save_alarm_changes(changes, sample.ts)
        if batch and store is not None:
            store.write_batch(batch, ())
    finally:
        if store is not None:
            store.close()

    summary = Summary(
        scenario=SCENARIO, seed=seed_value, days=days, panels=len(fleet), samples=samples,
        telemetry_rows=telemetry_rows, alarms=alarms, journal_entries=journal_entries,
        baseline_day=learning_days, sample_period_s=scenarios.EXPORT_PERIOD_S,
        window_start=start.isoformat(), window_end=end.isoformat(), digest=digest.hexdigest(),
    )

    code = 0
    if conn is not None:
        sync_alarm_sequence(conn)
        record_summary(conn, summary)
        code = verify(conn, contracts, summary)
        conn.close()
    return summary, code


def report(summary: Summary, wrote: bool) -> None:
    print(f"[seed] senaryo {summary.scenario} | tohum {summary.seed} | {summary.panels} pano | "
          f"{summary.days:g} gun | ornekleme {summary.sample_period_s:g} s", flush=True)
    print(f"[seed] pencere {summary.window_start} -> {summary.window_end}", flush=True)
    print(f"[seed] {summary.samples} mesaj, {summary.telemetry_rows} telemetri satiri, "
          f"{summary.alarms} alarm, {summary.journal_entries} denetim izi kaydi"
          + ("" if wrote else " (URETILDI, YAZILMADI: --dry-run)"), flush=True)
    print(f"[seed] taban ogrenme: baseline_day = {summary.baseline_day} (tamamlandi)", flush=True)
    print(f"[seed] ozet sha256 = {summary.digest}", flush=True)
    print(f"[seed] {ORIGIN}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dsn", default=None, help="hedef veritabani (varsayilan: DB_DSN ortam degiskeni)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="ayni tohum -> ayni veri")
    parser.add_argument("--days", type=float, default=DEFAULT_DAYS,
                        help=f"uretilecek gecmisin gun sayisi (varsayilan {DEFAULT_DAYS}; en az 8)")
    parser.add_argument("--panels", type=int, default=len(DEMO_FLEET),
                        help=f"kac pano (1-{len(DEMO_FLEET)})")
    parser.add_argument("--end", default=None, help="pencerenin bitisi (ISO 8601, ofsetli); varsayilan simdi")
    parser.add_argument("--reset", action="store_true", help="demo tablolarini once bosalt")
    parser.add_argument("--dry-run", action="store_true", help="veritabanina dokunma, yalnizca uret ve ozetle")
    parser.add_argument("--json", action="store_true", help="ozeti JSON olarak bas (testler icin)")
    args = parser.parse_args(argv)

    contracts = load_contracts(CONTRACTS_DIR)
    learning_days = int(contracts.thresholds["baseline_learning_days"])
    if args.days < learning_days + 1:
        raise SystemExit(f"--days en az {learning_days + 1} olmali: {learning_days} gun taban ogrenmeye gider, "
                         f"uzerine en az bir gun temiz veri kalmali")
    if not 1 <= args.panels <= len(DEMO_FLEET):
        raise SystemExit(f"--panels 1 ile {len(DEMO_FLEET)} arasinda olmali")

    dsn = None if args.dry_run else (args.dsn or os.getenv("DB_DSN", ""))
    if not args.dry_run and not dsn:
        raise SystemExit("--dsn verin ya da DB_DSN ortam degiskenini tanimlayin (--dry-run ile veritabani gerekmez)")

    end = _window_end(args.end, scenarios.EXPORT_PERIOD_S)
    summary, code = seed(dsn, contracts, DEMO_FLEET[: args.panels], seed_value=args.seed, days=args.days,
                         end=end, do_reset=args.reset, quiet=args.json)
    if args.json:
        print(json.dumps(asdict(summary), sort_keys=True))
    else:
        report(summary, wrote=dsn is not None)
    return code


if __name__ == "__main__":
    sys.exit(main())
