#!/usr/bin/env python3
"""Traceability check for a strategy workspace instance.

Reads the same wikilinks and properties Obsidian uses. Validates links, propagates
alerts upwards (claim -> conclusion -> decision -> direction/OKR), checks budgets and
review dates. Never changes a status: it writes reports/impact-YYYYMMDD.md.

Usage: python3 scripts/trace.py <instance-dir> [--today YYYY-MM-DD]
Exit 1 on validation errors or a hard budget exceeded. Requires PyYAML: run it from the
instance venv (see requirements.txt).
"""
import argparse
import datetime as dt
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("PyYAML not found. Activate the instance venv (source .venv/bin/activate) "
             "or create it: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")

SKIP_DIRS = {"reports", "originals", "scripts", "node_modules"}
LINK_FIELDS = ["supports", "against", "conclusions", "hypotheses", "decisions", "question", "supersedes"]
LINK = re.compile(r"\[\[([^\]#|]+)(?:#\^?([^\]|]+))?(?:\|[^\]]*)?\]\]")
BLOCK = re.compile(r"^\s*[-*]\s+(.*?)\s*\^([\w-]+)\s*$")
INLINE = re.compile(r"\((\w+)::\s*([^)]*)\)")
NUMBERED = re.compile(r"^([DH])-(\d+)")
LIVE = {"proposed", "active", "under_review"}
ROOT_TYPES = {"decision", "okr", "direction", "framing"}
DEFAULT_BUDGETS = {"open_questions": [5, 7], "live_decisions": [7, 12],
                   "hypotheses_per_decision": [3, 5], "conclusions_per_framework": [5, 8]}
ORDER = {"okr": 0, "direction": 1, "decision": 2, "conclusion": 3, "hypothesis": 4}


def to_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None


def links(value):
    for v in value if isinstance(value, list) else [value]:
        for m in LINK.finditer(str(v or "")):
            yield m.group(1).strip() + (f"#{m.group(2)}" if m.group(2) else "")


def show(ref):
    return f"[[{ref.replace('#', '#^')}]]"


def load(vault):
    nodes, blocks, errors = {}, {}, []
    for p in sorted(vault.rglob("*.md")):
        rel = p.relative_to(vault)
        dirs = rel.parts[:-1]
        if any(d.startswith(".") or d in SKIP_DIRS for d in dirs) or p.name.startswith("_"):
            continue
        text, fm = p.read_text(encoding="utf-8"), {}
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError as e:
                    errors.append(f"`{rel}` has invalid frontmatter: {str(e).splitlines()[0]}")
                text = parts[2]
        if p.stem in nodes:
            errors.append(f"duplicate file name `{p.stem}` (`{rel}`): wikilinks become ambiguous")
            continue
        nodes[p.stem] = fm if isinstance(fm, dict) else {}
        for line in text.splitlines():
            m = BLOCK.match(line)
            if m:
                key = f"{p.stem}#{m.group(2)}"
                if key in blocks:
                    errors.append(f"duplicate block id `^{m.group(2)}` in `{rel}`")
                blocks[key] = {"parent": p.stem, "fields": dict(INLINE.findall(m.group(1)))}
    return nodes, blocks, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vault", type=Path)
    ap.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    args = ap.parse_args()
    vault, today = args.vault, args.today

    cfg_path = vault / "strategy.config.yaml"
    cfg = (yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}) if cfg_path.exists() else {}
    budgets = {**DEFAULT_BUDGETS, **(cfg.get("budgets") or {})}

    nodes, blocks, errors = load(vault)
    if not cfg_path.exists():
        errors.append("`strategy.config.yaml` not found: using default budgets")
    kind = lambda n: nodes.get(n, {}).get("type")
    exists = lambda r: r in blocks if "#" in r else r in nodes

    # Validation
    numbered = defaultdict(list)
    for n in nodes:
        m = NUMBERED.match(n)
        if m:
            numbered[(m.group(1), int(m.group(2)))].append(n)
    for (prefix, num), names in sorted(numbered.items()):
        if len(names) > 1:
            errors.append(f"ID {prefix}-{num:03d} used by several files: {', '.join(sorted(names))}")

    reverse = defaultdict(set)
    for n, fm in nodes.items():
        for field in LINK_FIELDS:
            for dest in links(fm.get(field)):
                if not exists(dest):
                    errors.append(f"[[{n}]] `{field}` points to `{dest}`, which does not exist")
                reverse[dest].add(n)
        t = fm.get("type")
        if t == "conclusion":
            if not list(links(fm.get("supports"))):
                errors.append(f"[[{n}]] has no supporting claim (rule 5)")
            if "against" not in fm:
                errors.append(f"[[{n}]] is missing the `against` field")
            if not list(links(fm.get("question"))):
                errors.append(f"[[{n}]] is not tied to a framing question (rule 9)")
        if t == "hypothesis" and not (fm.get("metric") and fm.get("threshold")):
            errors.append(f"[[{n}]] has no metric and threshold: it is an assumption, not a hypothesis")
    for key, b in blocks.items():
        if kind(b["parent"]) == "framing" and b["fields"].get("status") == "answered":
            if not list(links(b["fields"].get("answered_by"))):
                errors.append(f"{show(key)} is answered but names no decision in `answered_by`")

    # Alert seeds
    seeds = []
    for n, fm in nodes.items():
        review = to_date(fm.get("review"))
        if fm.get("type") == "source" and review and review < today:
            seeds += [(k, f"source [[{n}]] expired on {review}") for k, b in blocks.items() if b["parent"] == n]
        if fm.get("type") == "hypothesis":
            deadline = to_date(fm.get("deadline"))
            if fm.get("status") == "refuted":
                seeds.append((n, f"[[{n}]] refuted"))
            elif fm.get("status") == "open" and deadline and deadline < today:
                seeds.append((n, f"[[{n}]] past its deadline ({deadline}) and not reviewed"))
    for key, b in blocks.items():
        for dest in links(b["fields"].get("contradicts")):
            if not exists(dest):
                errors.append(f"{show(key)} `contradicts` points to `{dest}`, which does not exist")
            seeds.append((dest, f"{show(dest)} contradicted by {show(key)}"))

    # Upward propagation
    affected = defaultdict(list)
    for origin, reason in seeds:
        queue, seen = deque([(origin, [origin])]), {origin}
        while queue:
            n, path = queue.popleft()
            for parent in sorted(reverse.get(n, ())):
                if parent not in seen:
                    seen.add(parent)
                    affected[parent].append((reason, " <- ".join(reversed(path + [parent]))))
                    queue.append((parent, path + [parent]))

    # Budgets
    rows, hard = [], False

    def budget(label, n, key):
        nonlocal hard
        soft, limit = budgets[key]
        state = "OVER HARD LIMIT" if n > limit else "over soft limit" if n > soft else "ok"
        hard |= n > limit
        rows.append(f"| {label} | {n} | {soft} | {limit} | {state} |")

    open_q = [k for k, b in blocks.items() if kind(b["parent"]) == "framing" and b["fields"].get("status") == "open"]
    budget("Open questions", len(open_q), "open_questions")
    live = sorted(n for n, f in nodes.items() if f.get("type") == "decision" and f.get("status") in LIVE)
    budget("Live decisions", len(live), "live_decisions")
    for d in live:
        budget(f"Hypotheses in [[{d}]]", len(list(links(nodes[d].get("hypotheses")))), "hypotheses_per_decision")
    per_fw = defaultdict(int)
    for f in nodes.values():
        if f.get("type") == "conclusion" and f.get("status") != "archived":
            per_fw[str(f.get("framework"))] += 1
    for fw, n in sorted(per_fw.items()):
        budget(f"Conclusions for {fw}", n, "conclusions_per_framework")

    # Reviews: only what a live decision relies on is reviewed; the rest is archived (rule 7)
    claimed, stack = set(), list(live)
    while stack:
        n = stack.pop()
        for field in LINK_FIELDS:
            for dest in links(nodes.get(n, {}).get(field)):
                stem = dest.split("#")[0]
                if stem not in claimed:
                    claimed.add(stem)
                    stack.append(stem)
    due, archive = [], []
    for n, fm in sorted(nodes.items()):
        review = to_date(fm.get("review"))
        if not review or review >= today or fm.get("status") in {"archived", "superseded"}:
            continue
        line = f"- [[{n}]] ({fm.get('type')}), review was due {review}"
        (due if fm.get("type") in ROOT_TYPES or n in claimed else archive).append(line)

    out = [f"# Impact report {today}", "",
           "Generated by `scripts/trace.py`. It changes no status: a person decides.", "",
           "## Validation", ""] + ([f"- {e}" for e in errors] or ["No errors."]) + [
           "", "## Affected", "", "| Item | Type | Reason | Path |", "| --- | --- | --- | --- |"]
    for n in sorted(affected, key=lambda k: (ORDER.get(kind(k), 9), k)):
        out += [f"| [[{n}]] | {kind(n)} | {reason} | {path} |" for reason, path in affected[n]]
    out += ["", "## Budgets", "", "| Budget | Current | Soft | Hard | State |", "| --- | --- | --- | --- | --- |"] + rows
    out += ["", "## Reviews due", ""] + (due or ["None."])
    out += ["", "## Archive candidates", "", "Expired and not relied on by any live decision.", ""] + (archive or ["None."])
    report = vault / "reports" / f"impact-{today:%Y%m%d}.md"
    report.parent.mkdir(exist_ok=True)
    report.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{report}: {len(errors)} errors, {len(affected)} affected, hard budget exceeded: {'yes' if hard else 'no'}")
    return 1 if errors or hard else 0


if __name__ == "__main__":
    sys.exit(main())
