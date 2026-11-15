#!/usr/bin/env python3
"""Create or upgrade a strategy workspace instance from the bundled templates.

Usage:
  python3 scaffold.py <target-dir> --company NAME [--unit NAME] [--language es]
  python3 scaffold.py <target-dir> --upgrade

Create never overwrites an existing file. Upgrade overwrites only engine-owned files
(CLAUDE.md, .claude/rules/, scripts/); configuration and content are never touched.
"""
import argparse
import shutil
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent / "templates"
ENGINE_OWNED = ("CLAUDE.md", ".claude/rules/", "scripts/")
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
    for src in sorted(p for p in TEMPLATES.rglob("*") if p.is_file()):
        rel = src.relative_to(TEMPLATES).as_posix()
        dst = a.target / rel
        owned = rel.startswith(ENGINE_OWNED)
        if a.upgrade and not owned:
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
    if not a.upgrade:
        for d in CONTENT_DIRS:
            (a.target / d).mkdir(parents=True, exist_ok=True)
            keep = a.target / d / ".gitkeep"
            if not any((a.target / d).iterdir()):
                keep.touch()
    print(f"{'upgraded' if a.upgrade else 'created'} {a.target}: {len(written)} files written")
    for rel in written:
        print(f"  {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
