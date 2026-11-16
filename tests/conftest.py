import importlib.util
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TRACE_PATH = ROOT / "skills" / "init-instance" / "templates" / "scripts" / "trace.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
TODAY = "2026-11-15"
DROP = object()
SERVED = (".pdf", ".html", ".htm")


def pytest_addoption(parser):
    parser.addoption("--no-pdftotext", action="store_true",
                     help="run as if pdftotext were not installed")


def pytest_configure(config):
    config.addinivalue_line("markers", "pdf: needs pdftotext installed")


def pytest_runtest_setup(item):
    if item.get_closest_marker("pdf") and (
            item.config.getoption("--no-pdftotext") or shutil.which("pdftotext") is None):
        pytest.skip("pdftotext not available")


@pytest.fixture(autouse=True)
def _no_pdftotext(request, monkeypatch):
    if request.config.getoption("--no-pdftotext"):
        hide_pdftotext(monkeypatch)


def hide_pdftotext(monkeypatch):
    real = shutil.which
    monkeypatch.setattr(shutil, "which", lambda cmd, *a, **k: None if cmd == "pdftotext" else real(cmd, *a, **k))


@pytest.fixture(scope="session")
def trace():
    # Not named "trace": the stdlib has a module with that name.
    spec = importlib.util.spec_from_file_location("strategy_trace", TRACE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class Result:
    code: int
    report: str

    def section(self, title):
        lines, inside = [], False
        for line in self.report.splitlines():
            if line.startswith("## "):
                inside = line == f"## {title}"
                continue
            if inside and line.strip():
                lines.append(line)
        return lines

    @property
    def errors(self):
        return [l[2:] for l in self.section("Validation") if l.startswith("- ")]

    def items(self, title):
        return [l for l in self.section(title) if l.startswith("- ")]

    @property
    def headings(self):
        return [l[3:] for l in self.report.splitlines() if l.startswith("## ")]


class Instance:
    def __init__(self, root, trace, monkeypatch, scaffold=True):
        self.root, self._trace, self._mp = root, trace, monkeypatch
        if scaffold:
            self.config()
            self.framing()

    def write(self, rel, content):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
        return p

    def _md(self, rel, fm, body):
        fm = {k: v for k, v in fm.items() if v is not DROP}
        self.write(rel, "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n" + body)

    def config(self, budgets=None):
        cfg = {"company": {"name": "Test Co"}, "language": "en"}
        if budgets:
            cfg["budgets"] = budgets
        self.write("strategy.config.yaml", yaml.safe_dump(cfg))

    def framing(self, gaps=(), questions=("First question? (status:: open)", "Second question? (status:: open)"),
                raw_gaps=()):
        """`raw_gaps` are lines written as they are under `## Gaps`, after the numbered gaps."""
        body = "# Framing\n\n## Strategic questions\n\n"
        body += "".join(f"- {q} ^q{i:02d}\n" for i, q in enumerate(questions, 1))
        if gaps or raw_gaps:
            body += "\n## Gaps\n\n" + "".join(f"- {g} ^g{i:02d}\n" for i, g in enumerate(gaps, 1))
            body += "".join(f"{line}\n" for line in raw_gaps)
        self._md("framing.md", {"type": "framing", "review": "2027-05-15"}, body)

    def source(self, stem="S-20261101-test", claims=("DATA: 1 unit, from a test table. (confidence:: low)",), **fm):
        base = {"type": "source", "origin": "Test publisher (fictional)", "url": DROP,
                "published": "2026-10-30", "captured": "2026-11-01", "review": "2027-05-01", "original": DROP}
        base.update(fm)
        body = "".join(f"- {c} ^c{i:02d}\n" for i, c in enumerate(claims, 1))
        self._md(f"sources/{stem}.md", base, body)
        return stem

    def original(self, name, content):
        return self.write(f"originals/{name}", content)

    def quoted(self, original_text, claims, ext=".txt", stem="S-20261101-quoted"):
        """A source with an original holding `original_text`, and a url only if the original is a served file."""
        self.original(f"{stem}{ext}", original_text)
        claims = [claims] if isinstance(claims, str) else claims
        url = "https://example.org/test" if ext.lower() in SERVED else DROP
        return self.source(stem, claims, url=url, original=f"originals/{stem}{ext}")

    def conclusion(self, name, supports, **fm):
        base = {"type": "conclusion", "framework": "custom", "question": "[[framing#^q01]]",
                "supports": supports, "against": [], "status": "current", "review": "2027-05-15"}
        base.update(fm)
        self._md(f"conclusions/{name}.md", base, "# Title\n\n## Fact\n## Interpretation\n## Implication\n")

    def decision(self, name, **fm):
        base = {"type": "decision", "status": "proposed", "conclusions": [], "hypotheses": [],
                "review": "2027-05-15"}
        base.update(fm)
        self._md(f"decisions/{name}.md", base, f"# {name}\n")

    def run(self, today=TODAY):
        self._mp.setattr(sys, "argv", ["trace.py", str(self.root), "--today", today])
        code = self._trace.main()
        report = (self.root / "reports" / f"impact-{today.replace('-', '')}.md").read_text(encoding="utf-8")
        return Result(code, report)


@pytest.fixture
def instance(tmp_path, trace, monkeypatch):
    return Instance(tmp_path / "instance", trace, monkeypatch)
