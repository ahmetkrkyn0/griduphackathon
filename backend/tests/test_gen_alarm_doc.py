"""scripts/gen_alarm_doc.py — docs/06-alarm-matrisi.md sozlesmeden uretilir, elle duzenlenmez.

Dort dokuman ureteci `--check` bayragi tasiyor ama 16 Eylul'e kadar UCU testliydi:
gen_modbus_doc, gen_iec104_doc ve gen_grafana_dashboards'un "depodaki cikti guncel"
testi vardi, gen_alarm_doc'un yoktu. Bayrak tek basina bir sey korumaz — onu koskalan
bir test olmadan kimse kosturmaz (depoda CI yok, .github dizini bulunmuyor).

Bu dosya o bosluğu kapatir ve diger uc testle ayni sozu verir: contracts/alarm-codes.yaml
degisip `python scripts/gen_alarm_doc.py` kosulmazsa test kirilir.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest
import yaml

from helpers import REPO_ROOT


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("gen_alarm_doc", REPO_ROOT / "scripts" / "gen_alarm_doc.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


@pytest.fixture(scope="module")
def contract(gen) -> dict:
    return yaml.safe_load(gen.CONTRACT.read_text(encoding="utf-8"))


def test_committed_doc_is_up_to_date(gen):
    """ASIL KILIT — diger uc uretec testiyle ayni satir."""
    assert gen.main(["--check"]) == 0


def test_check_fails_when_doc_drifts_from_contract(gen, contract, monkeypatch, tmp_path, capsys):
    """Sozlesme degisip dokuman yenilenmezse --check 1 donmeli.

    Sozlesmeye DOKUNMADAN sinanir: dokumanin bir kopyasi bayatlatilir ve uretec
    o kopyaya bakacak sekilde yonlendirilir.
    """
    stale = tmp_path / "06-alarm-matrisi.md"
    stale.write_text(gen.DOC.read_text(encoding="utf-8").replace("| P1 |", "| P9 |", 1), encoding="utf-8")
    # ROOT da tasinir: uretec ekrana DOC.relative_to(ROOT) basiyor.
    monkeypatch.setattr(gen, "DOC", stale)
    monkeypatch.setattr(gen, "ROOT", tmp_path)

    assert gen.main(["--check"]) == 1
    assert "guncel degil" in capsys.readouterr().out


def test_check_does_not_rewrite_the_doc(gen, tmp_path, monkeypatch):
    """Denetim kipi dosyaya yazmamali; yazsaydi kendi sikayetini susturudu."""
    stale = tmp_path / "06-alarm-matrisi.md"
    original = gen.DOC.read_text(encoding="utf-8").replace("| P1 |", "| P9 |", 1)
    stale.write_text(original, encoding="utf-8")
    monkeypatch.setattr(gen, "DOC", stale)
    monkeypatch.setattr(gen, "ROOT", tmp_path)

    assert gen.main(["--check"]) == 1
    assert stale.read_text(encoding="utf-8") == original


def test_every_contract_alarm_code_reaches_the_doc(gen, contract):
    """Uretilen katalog sozlesmedeki TUM kodlari tasimali — sessizce dusen kod olmasin."""
    doc = gen.DOC.read_text(encoding="utf-8")
    codes = [alarm["code"] for alarm in contract["alarms"]]
    assert codes, "sozlesmede alarm kodu yok — test kendi varsayimini dogruluyor"
    missing = [code for code in codes if code not in doc]
    assert missing == []
