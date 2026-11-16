import importlib.util
import sys

import pytest

from conftest import ROOT

SCAFFOLD_PATH = ROOT / "skills" / "init-instance" / "scaffold.py"
TEMPLATE_FILES = {
    "CLAUDE.md": "# Engine\n",
    "requirements.txt": "PyYAML\n",
    "strategy.config.yaml": "company:\n  name: \"{{company}}\"\n",
    "scripts/trace.py": "print('trace')\n",
    "scripts/__pycache__/trace.cpython-312.pyc": b"\x00\x01",
}


@pytest.fixture
def scaffold(tmp_path, monkeypatch):
    """Runs scaffold.py against a small templates folder holding a stray __pycache__."""
    spec = importlib.util.spec_from_file_location("strategy_scaffold", SCAFFOLD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    templates = tmp_path / "templates"
    for rel, content in TEMPLATE_FILES.items():
        p = templates / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content) if isinstance(content, bytes) else p.write_text(content, encoding="utf-8")
    monkeypatch.setattr(module, "TEMPLATES", templates)

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["scaffold.py", *map(str, args)])
        return module.main()
    return run


def test_create_skips_pycache(scaffold, tmp_path):
    target = tmp_path / "instance"
    assert scaffold(target, "--company", "Test Co") == 0
    assert (target / "scripts" / "trace.py").is_file()
    assert not (target / "scripts" / "__pycache__").exists()


def test_upgrade_skips_pycache(scaffold, tmp_path):
    target = tmp_path / "instance"
    target.mkdir()
    (target / "strategy.config.yaml").write_text("company:\n  name: \"Test Co\"\n", encoding="utf-8")
    assert scaffold(target, "--upgrade") == 0
    assert (target / "scripts" / "trace.py").is_file()
    assert not (target / "scripts" / "__pycache__").exists()
