#!/usr/bin/env python3
"""Create or upgrade a strategy workspace instance from the bundled templates.

Usage:
  python3 scaffold.py <target-dir> --company NAME [--unit NAME] [--language es]
  python3 scaffold.py <target-dir> --upgrade

Create never overwrites an existing file. Upgrade overwrites engine-owned files
(CLAUDE.md, _dashboard.md, .claude/rules/, scripts/) and adds any other template file that is missing
(for example requirements.txt), without overwriting it, and deletes engine-owned files a
previous version shipped (OBSOLETE). Configuration and content (strategy.config.yaml,
framing.md, strategy/, diagnosis/) are never created or touched by an upgrade.
"""
import argparse
import shutil
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent / "templates"
# _dashboard.md holds only generic queries, so it is engine-owned like the rules.
ENGINE_OWNED = ("CLAUDE.md", "_dashboard.md", ".claude/rules/", "scripts/")
# diagnosis/ is content, and its presence turns on its checks: an upgrade never creates it.
SEED_ONLY = ("strategy.config.yaml", "framing.md", "strategy/", "diagnosis/")
# Engine-owned files that earlier versions shipped and this one replaces.
OBSOLETE = ("scripts/trace.py",)
CONTENT_DIRS = ["sources", "originals", "conclusions", "hypotheses", "decisions", "strategy", "reports"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("target", type=Path)
    ap.add_argument("--company", default="")
    ap.add_argument("--unit", default="")
    ap.add_argument("--language", default="en")
    ap.add_argument("--upgrade", action="store_true")
    a = ap.parse_args()
    if not a.upgrade and not a.company:
        ap.error("--company is required when creating an instance")
    if a.upgrade and not (a.target / "strategy.config.yaml").exists():
        ap.error(f"{a.target} is not an instance (no strategy.config.yaml)")

    subs = {"{{company}}": a.company, "{{unit}}": a.unit, "{{language}}": a.language}
    written = []
    # Running the tests leaves __pycache__ next to templates/scripts/check.py.
    for src in sorted(p for p in TEMPLATES.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        rel = src.relative_to(TEMPLATES).as_posix()
        dst = a.target / rel
        owned = rel.startswith(ENGINE_OWNED)
        if a.upgrade and not owned and rel.startswith(SEED_ONLY):
            continue
        if dst.exists() and not (a.upgrade and owned):
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if owned:
            shutil.copyfile(src, dst)
        else:
            text = src.read_text(encoding="utf-8")
            for k, v in subs.items():
                text = text.replace(k, v)
            dst.write_text(text, encoding="utf-8")
        written.append(rel)
    removed = [rel for rel in OBSOLETE if a.upgrade and (a.target / rel).is_file()]
    for rel in removed:
        (a.target / rel).unlink()
    if not a.upgrade:
        for d in CONTENT_DIRS:
            (a.target / d).mkdir(parents=True, exist_ok=True)
            keep = a.target / d / ".gitkeep"
            if not any((a.target / d).iterdir()):
                keep.touch()
    print(f"{'upgraded' if a.upgrade else 'created'} {a.target}: {len(written)} files written")
    for rel in written:
        print(f"  {rel}")
    for rel in removed:
        print(f"  removed {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
