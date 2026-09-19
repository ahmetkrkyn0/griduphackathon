"""F-20 — denetim izinde kurcalama kaniti (app/journal_chain.py + scripts/verify_journal.py).

Maddenin OLCULEBILIR iddiasi: bir satir bozuldugunda dogrulayici KACINCI halkada durur.
Bunu uc negatif test kanitliyor ve ucu de "kirilmis olmali" degil, "SU halkada kirilmis
olmali" diyor — sadece "hata verdi" demek, dogrulayicinin dogru yeri gosterdigini
kanitlamazdi.

PgStore'un ayni zinciri gercek TimescaleDB'de urettigi tests/test_alarm_store.py'de;
betigin uctan uca kosumu tests/test_verify_journal.py'de.
"""

from __future__ import annotations

import pytest

from app.journal_chain import GENESIS, ChainBreak, link_hash, verify
from helpers import utc

T0 = utc(2026, 9, 13, 10, 0, 0)


def row(index: int, prev: str, **over) -> dict:
    """Zincirin bir halkasi; `hash` icerikten hesaplanir."""
    fields = {
        "alarm_id": 100 + index,
        "at": T0,
        "action": "raised",
        "state": "active",
        "by_user": None,
        "note": None,
    }
    fields.update(over)
    return {"id": index, "prev_hash": prev, "hash": link_hash(prev, **fields), **fields}


def chain(length: int) -> list[dict]:
    rows, prev = [], GENESIS
    for index in range(1, length + 1):
        current = row(index, prev)
        rows.append(current)
        prev = current["hash"]
    return rows


# ------------------------------------------------------------------ ozet fonksiyonu
def test_hash_is_deterministic_and_64_hex():
    args = dict(alarm_id=7, at=T0, action="acked", state="acked", by_user="a", note=None)
    first = link_hash(GENESIS, **args)
    assert first == link_hash(GENESIS, **args)
    assert len(first) == 64 and all(c in "0123456789abcdef" for c in first)


@pytest.mark.parametrize(
    "change",
    [
        {"alarm_id": 999},
        {"at": T0.replace(minute=1)},
        {"action": "cleared"},
        {"state": "cleared"},
        {"by_user": "baskasi"},
        {"note": "eklenmis not"},
    ],
)
def test_any_field_change_changes_the_hash(change):
    base = dict(alarm_id=7, at=T0, action="acked", state="acked", by_user="a", note=None)
    assert link_hash(GENESIS, **base) != link_hash(GENESIS, **{**base, **change})


def test_none_and_empty_string_hash_differently():
    """'not yok' ile 'operator bos not girdi' ayni sey degildir."""
    base = dict(alarm_id=7, at=T0, action="acked", state="acked", by_user="a")
    assert link_hash(GENESIS, **base, note=None) != link_hash(GENESIS, **base, note="")


def test_field_boundaries_cannot_be_shifted():
    """('ab', None) ile ('a', 'b') AYNI ozeti uretmemeli (uzunluk-kaydirma)."""
    base = dict(alarm_id=7, at=T0, action="acked", state="acked")
    assert link_hash(GENESIS, **base, by_user="ab", note=None) != link_hash(GENESIS, **base, by_user="a", note="b")


def test_timezone_is_normalized():
    """Ayni an, farkli ofsette saklandiginda AYNI ozeti vermeli."""
    import datetime as dt

    other = T0.astimezone(dt.timezone(dt.timedelta(hours=3)))
    base = dict(alarm_id=7, action="acked", state="acked", by_user="a", note=None)
    assert link_hash(GENESIS, at=T0, **base) == link_hash(GENESIS, at=other, **base)


# --------------------------------------------------------------------- dogrulama
def test_intact_chain_verifies():
    assert verify(chain(5)) == 5


def test_empty_journal_verifies_as_zero_links():
    assert verify([]) == 0


def test_rows_without_hash_are_counted_as_pre_migration():
    """Goc oncesi satirlarin hash'i NULL: zincire dahil degiller, hata da degiller."""
    rows = [
        {"id": 1, "alarm_id": 1, "at": T0, "action": "raised", "state": "active",
         "by_user": None, "note": None, "prev_hash": None, "hash": None},
        *chain(3),
    ]
    rows[1]["prev_hash"] = GENESIS  # zincir gocten sonra basliyor
    assert verify(rows) == 3


# ------------------------------------------------------- ASIL KILIT: negatif testler
def test_modified_row_breaks_at_that_exact_link():
    rows = chain(5)
    rows[2]["by_user"] = "sahte.operator"  # 3. halka

    with pytest.raises(ChainBreak) as caught:
        verify(rows)

    assert caught.value.position == 3
    assert caught.value.row_id == 3
    assert caught.value.kind == "degismis"
    assert "DEGISTIRILMIS" in caught.value.detail


def test_deleted_row_breaks_at_the_next_link():
    """Silinen satir, KENDINDEN SONRAKI halkada yakalanir: prev_hash artik denk gelmez."""
    rows = chain(5)
    del rows[2]  # 3. satiri sessizce sil

    with pytest.raises(ChainBreak) as caught:
        verify(rows)

    assert caught.value.position == 3   # eski 4. satir, artik 3. sirada
    assert caught.value.row_id == 4
    assert caught.value.kind == "kopuk"
    assert "SILINMIS" in caught.value.detail


def test_inserted_row_is_caught():
    """Araya uydurma bir satir eklemek de zinciri koparir."""
    rows = chain(5)
    fake = row(99, rows[1]["hash"], by_user="uydurma")
    rows.insert(2, fake)

    with pytest.raises(ChainBreak) as caught:
        verify(rows)

    # Uydurma satirin KENDI ozeti tutarlidir (saldirgan hesaplayabilir), ama ondan
    # SONRAKI gercek satirin prev_hash'i artik uydurmanin ozetine denk gelmez.
    assert caught.value.position == 4
    assert caught.value.kind == "kopuk"


def test_unhashed_row_after_chain_start_is_caught():
    """Zincir baslamisken hash'siz satir: goc oncesi olamaz, kurcalama belirtisidir."""
    rows = chain(3)
    rows.insert(2, {"id": 99, "alarm_id": 1, "at": T0, "action": "raised", "state": "active",
                    "by_user": None, "note": None, "prev_hash": None, "hash": None})

    with pytest.raises(ChainBreak) as caught:
        verify(rows)

    assert caught.value.position == 3
    assert caught.value.kind == "kopuk"


def test_tail_truncation_is_NOT_detected():
    """DURUSTLUK TESTI: zincirin bilinen sinirini kilitler.

    Son satirlar silinirse kalan zincir kendi icinde tutarlidir ve dogrulayici
    "saglam" der. Bu bir hata degil, hash zincirinin dogasidir; kapatmak icin zincir
    basinin disariya yayinlanmasi gerekir ve bu YAPILMADI. Testin varlik sebebi,
    iddianin gercekte olduğundan guclu sunulmasini engellemektir.
    """
    rows = chain(5)
    assert verify(rows[:3]) == 3  # son iki satir silindi, yine "saglam"
