"""TVOC-2 simulatorunun SUNUCU davranisi (Kisi A, K4).

Register mantigi libs/panoalgo/tests/test_devices.py'de kilitli. Burada olculen
tek sey, PLAN.md TA3 kabul kriterinin ve docs/17 DH4'un iddiasidir:

    "Fabrika ayari ID 248 = haberlesme kapali; cihaz hicbir isteme cevap VERMEZ,
     istisna bile donmez."

Bu iddia 14 Eylul'e kadar DOGRULANMAMISTI ve yanlisti: pymodbus varsayilani
(ignore_missing_slaves=False) bilinmeyen birim icin 0x8B / kod 11 istisnasi
donduruyordu. Test ham soket kullanir, cunku bir Modbus istemcisi "cevap yok" ile
"istisna cevabi"ni ayni hataya cevirebilir — tam olarak ayirt etmek istedigimiz sey bu.
"""

from __future__ import annotations

import pytest

from helpers import free_port, read_holding_raw, run_sim, wait_for_port
from panoalgo.devices import TVOC2_FACTORY_SLAVE_ID, TVOC2_SYSTEM_STATE_REG

pytestmark = pytest.mark.slow


@pytest.fixture
def tvoc_server():
    """Istenen slave ID ile gercek sim/tvoc2_sim.py CLI'sini ayaga kaldirir."""
    started = []

    def start(slave_id: int):
        port = free_port()
        proc = run_sim(
            "tvoc2_sim.py",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--slave-id", str(slave_id),
        )
        started.append(proc)
        wait_for_port(port)
        return port

    yield start

    for proc in started:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:  # noqa: BLE001 - temizlik, testi dusurmemeli
            proc.kill()


def test_factory_id_248_sends_no_response_at_all(tvoc_server):
    """Kilavuz 1.3: haberlesme kapali -> istemci ZAMAN ASIMI alir, istisna degil."""
    port = tvoc_server(TVOC2_FACTORY_SLAVE_ID)

    answer = read_holding_raw(port, TVOC2_FACTORY_SLAVE_ID, TVOC2_SYSTEM_STATE_REG)

    assert answer is None, (
        "ID 248 cevap dondurdu; 'hicbir isteme cevap vermez' iddiasi cururdu. "
        f"Donen bayt: {answer!r}"
    )


def test_a_valid_id_on_the_same_server_answers(tvoc_server):
    """Ayni sunucu, gecerli ID ile: cevap gelir. Sessizlik 'sunucu bozuk' degildir."""
    port = tvoc_server(10)

    answer = read_holding_raw(port, 10, TVOC2_SYSTEM_STATE_REG)

    assert answer is not None, "gecerli ID 10 cevapsiz kaldi"
    # MBAP(7) + fonksiyon kodu; 0x03 = normal cevap, 0x83 = istisna
    assert answer[7] == 0x03, f"istisna cevabi geldi: 0x{answer[7]:02X} kod {answer[8]}"
    assert answer[8] == 2, "FC03 bayt sayisi 1 register icin 2 olmali"


def test_unknown_unit_on_an_open_server_is_also_silent(tvoc_server):
    """ID 10 acikken 99'a sorulursa yine SESSIZLIK olmali (ag gecidi istisnasi degil).

    Gercek bir RS485 hattinda da olmayan bir adrese sorarsaniz kimse konusmaz.
    """
    port = tvoc_server(10)

    answer = read_holding_raw(port, 99, TVOC2_SYSTEM_STATE_REG)

    assert answer is None, f"bilinmeyen birim cevap dondurdu: {answer!r}"
