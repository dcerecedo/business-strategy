#!/usr/bin/env python3
"""Traceability check for a strategy workspace instance.

Reads the same wikilinks and properties Obsidian uses. Validates links, sources and their
originals, literal quotes against the original, framework fields and gaps; propagates
alerts upwards (claim -> conclusion -> decision -> direction/OKR), checks budgets and
review dates. Never changes a status: it writes reports/impact-YYYYMMDD.md.

Usage: python3 scripts/trace.py <instance-dir> [--today YYYY-MM-DD]
Exit 1 on validation errors or a hard budget exceeded. Requires PyYAML: run it from the
instance venv (see requirements.txt). Quotes in PDFs need pdftotext (poppler-utils);
without it they are listed as not checked.
"""
import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import defaultdict, deque
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("PyYAML not found. Activate the instance venv (source .venv/bin/activate) "
             "or create it: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")

SKIP_DIRS = {"reports", "originals", "scripts", "node_modules"}
LINK_FIELDS = ["supports", "against", "conclusions", "hypotheses", "decisions", "question", "supersedes",
               "benefit", "barrier"]
LINK = re.compile(r"\[\[([^\]#|]+)(?:#\^?([^\]|]+))?(?:\|[^\]]*)?\]\]")
BLOCK = re.compile(r"^\s*[-*]\s+(.*?)\s*\^([\w-]+)\s*$")
INLINE = re.compile(r"\((\w+)::\s*([^)]*)\)")
NUMBERED = re.compile(r"^([DH])-(\d+)")
LIVE = {"proposed", "active", "under_review"}
ROOT_TYPES = {"decision", "okr", "direction", "framing"}
DEFAULT_BUDGETS = {"open_questions": [5, 7], "live_decisions": [7, 12],
                   "hypotheses_per_decision": [3, 5], "conclusions_per_framework": [5, 8],
                   "vital_gaps_per_question": [3, 5]}
# Extra frontmatter per framework, as in skills/apply-framework/frameworks.md.
FRAMEWORK_KEYS = {
    "porter": ["force", "intensity", "segment"],
    "jtbd": ["segment", "job", "current_alternative"],
    "sizing": ["method", "tam", "sam", "som"],
    "value_chain": ["activity", "effect", "compared_with"],
    "unit_economics": ["segment", "cac", "ltv", "gross_margin", "payback_months"],
    "seven_powers": ["power", "benefit", "barrier"],
    "pestel": ["factor", "horizon_years"],
    "positioning": ["axis_x", "axis_y"],
    "wardley": ["component", "stage", "movement"],
}
SOURCE_REQUIRED = ["origin", "captured", "review"]
GAP_ORIGINS = ["internal", "customer", "installer", "purchase", "manual"]
CHARS = str.maketrans({"\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
                       "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u00a0": " ",
                       "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl", "\ufb03": "ffi", "\ufb04": "ffl"})
SOFT_HYPHEN = re.compile("\u00ad\\s*")
SPACES = re.compile(r"\s+")
HYPHEN_BREAK = re.compile(r"(\w)-\s*\n\s*(\w)")
UNCLOSED = object()
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


def normalize(text):
    text = SOFT_HYPHEN.sub("", unicodedata.normalize("NFC", text))
    return SPACES.sub(" ", text.translate(CHARS)).strip()


def quote_of(text):
    """The quoted text of a claim, None if it is not a quote, UNCLOSED if it opens one and never closes it."""
    m = INLINE.search(text)
    head = (text[:m.start()] if m else text).strip()
    if not head or head[0] not in "\"\u201c":
        return None
    return head[1:-1] if len(head) > 1 and head[-1] in "\"\u201d" else UNCLOSED


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    # Every tag becomes a space so that adjacent blocks (</p><p>) do not glue words together.
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def read_original(path):
    """(text, None) or (None, why it cannot be read)."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        exe = shutil.which("pdftotext")
        if not exe:
            return None, "pdftotext not installed"
        # No -layout: it interleaves the columns of two-column documents.
        run = subprocess.run([exe, "-enc", "UTF-8", str(path), "-"], capture_output=True)
        if run.returncode:
            why = (run.stderr.decode("utf-8", "replace").strip().splitlines() or [f"exit {run.returncode}"])[0]
            return None, f"pdftotext failed: {why}"
        return run.stdout.decode("utf-8", "replace"), None
    if suffix in (".html", ".htm"):
        parser = _HTMLText()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        parser.close()
        return "".join(parser.parts), None
    if suffix in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="replace"), None
    return None, "unsupported extension"


def readings(path):
    """Normalized texts a quote may match, or ((), why the original cannot be read).

    The second reading joins words split by a hyphen at the end of a line."""
    raw, why = read_original(path)
    if why:
        return (), why
    return (normalize(raw), normalize(HYPHEN_BREAK.sub(r"\1\2", raw))), None


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
                blocks[key] = {"parent": p.stem, "text": m.group(1),
                               "fields": {k: v.strip() for k, v in INLINE.findall(m.group(1))}}
    return nodes, blocks, errors


def check_sources(vault, nodes, errors):
    """Validate source fields and originals. Returns {source: original path} for readable originals."""
    readable, referenced = {}, set()
    for n, fm in nodes.items():
        if fm.get("type") != "source":
            continue
        for field in SOURCE_REQUIRED:
            if not str(fm.get(field) or "").strip():
                errors.append(f"[[{n}]] is missing the `{field}` field")
        original = str(fm.get("original") or "").strip()
        if not original:
            if str(fm.get("url") or "").strip():
                errors.append(f"[[{n}]] has a `url` but no `original`: quotes cannot be checked")
            continue
        rel = PurePosixPath(original)
        referenced.add(rel.as_posix())
        if rel.is_absolute() or len(rel.parts) < 2 or rel.parts[0] != "originals" or ".." in rel.parts:
            errors.append(f"[[{n}]] `original` must be under `originals/`")
        elif not (vault / rel).is_file():
            errors.append(f"[[{n}]] `original` points to `{original}`, which does not exist")
        else:
            readable[n] = original
            if rel.stem != n:
                errors.append(f"[[{n}]] `original` is `{original}`: its name must be `{n}` plus an extension")
    folder = vault / "originals"
    for p in sorted(folder.rglob("*")) if folder.is_dir() else []:
        inner = p.relative_to(folder)
        if not p.is_file() or any(part.startswith(".") for part in inner.parts):
            continue
        rel = p.relative_to(vault).as_posix()
        extract = p.suffix == ".txt" and nodes.get(p.stem, {}).get("type") == "source"
        if rel not in referenced and not extract:
            errors.append(f"`{rel}` is not the `original` of any source")
    return readable


def check_quotes(vault, nodes, blocks, originals, errors):
    """Check every literal quote against its original. Returns the manual and unchecked report lines."""
    manual, unchecked, texts = [], [], {}
    for key, b in blocks.items():
        source = b["parent"]
        if nodes[source].get("type") != "source":
            continue
        quote = quote_of(b["text"])
        if quote is None:
            continue
        if quote is UNCLOSED:
            errors.append(f"{show(key)} starts with a quote but does not close it before its fields")
            continue
        original = originals.get(source)
        if not original:
            if not nodes[source].get("original"):
                unchecked.append(f"- {show(key)}: no original")
            continue
        if source not in texts:
            texts[source] = readings(vault / original)
        candidates, why = texts[source]
        if why:
            unchecked.append(f"- {show(key)} `{original}`: {why}")
        elif not any(normalize(quote) in text for text in candidates):
            if b["fields"].get("verified") == "manual":
                manual.append(f"- {show(key)} in `{original}`")
            else:
                errors.append(f"{show(key)} quote not found in `{original}`")
    return manual, unchecked


def check_gaps(blocks, kind, exists, errors):
    """Validate gaps in framing.md. Returns the number of vital gaps per question."""
    vital = defaultdict(int)
    for key, b in blocks.items():
        if kind(b["parent"]) != "framing" or not key.split("#")[1].startswith("g"):
            continue
        fields = b["fields"]
        questions = list(links(fields.get("question")))
        if not questions:
            errors.append(f"{show(key)} has no `question`")
        for dest in questions:
            if not exists(dest):
                errors.append(f"{show(key)} `question` points to `{dest}`, which does not exist")
            elif fields.get("priority") == "vital":
                vital[dest] += 1
        origin = fields.get("origin")
        if not origin:
            errors.append(f"{show(key)} has no `origin`")
        elif origin not in GAP_ORIGINS:
            errors.append(f"{show(key)} `origin` is `{origin}`: expected {', '.join(GAP_ORIGINS[:-1])} or {GAP_ORIGINS[-1]}")
    return vital


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
            for key in FRAMEWORK_KEYS.get(str(fm.get("framework")), []):
                if key not in fm:
                    errors.append(f"[[{n}]] is missing the `{key}` field (framework {fm.get('framework')})")
            if fm.get("framework") == "seven_powers" and "benefit" in fm and not list(links(fm.get("benefit"))):
                errors.append(f"[[{n}]] has an empty `benefit`: a power needs a cited benefit")
        if t == "hypothesis" and not (fm.get("metric") and fm.get("threshold")):
            errors.append(f"[[{n}]] has no metric and threshold: it is an assumption, not a hypothesis")
    for key, b in blocks.items():
        if kind(b["parent"]) == "framing" and b["fields"].get("status") == "answered":
            if not list(links(b["fields"].get("answered_by"))):
                errors.append(f"{show(key)} is answered but names no decision in `answered_by`")
    originals = check_sources(vault, nodes, errors)
    manual, unchecked = check_quotes(vault, nodes, blocks, originals, errors)
    vital = check_gaps(blocks, kind, exists, errors)

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
    for dest, n in sorted(vital.items()):
        budget(f"Vital gaps for {show(dest)}", n, "vital_gaps_per_question")

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
           "", "## Quotes verified manually", ""] + (manual or ["None."]) + [
           "", "## Quotes not checked automatically", ""] + (unchecked or ["None."]) + [
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
