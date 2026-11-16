"""Evidence checks: source fields, originals as served, and every quote against its original."""
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import PurePosixPath

from graph import INLINE, links, show

SOURCE_REQUIRED = ["origin", "captured", "review"]
SERVED = {".pdf", ".html", ".htm"}
CHARS = str.maketrans({"“": '"', "”": '"', "„": '"', "‟": '"',
                       "‘": "'", "’": "'", "‚": "'", "‛": "'", " ": " ",
                       "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"})
SOFT_HYPHEN = re.compile("­\\s*")
SPACES = re.compile(r"\s+")
SPACE_BEFORE = re.compile(r" ([,.;:)\]])")
SPACE_AFTER = re.compile(r"([(\[]) ")
FRAGMENT = re.compile(r'"([^"]+)"|“([^”]+)”|«([^»]+)»')
NUMBER = re.compile(r"\d[\d.,]*\d|\d")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
CONDITION = re.compile(r", (en cuyo caso|siempre que|excepto|salvo|cuando|a condición de"
                       r"|in which case|provided that|except|unless|when)\b")
HYPHEN_BREAK = re.compile(r"(\w)-\s*\n\s*(\w)")
UNCLOSED = object()


@dataclass
class Evidence:
    manual: list = field(default_factory=list)
    unchecked: list = field(default_factory=list)
    cut: list = field(default_factory=list)
    values: list = field(default_factory=list)
    relations: dict = field(default_factory=dict)


def normalize(text):
    text = SOFT_HYPHEN.sub("", unicodedata.normalize("NFC", text))
    text = SPACES.sub(" ", text.translate(CHARS)).strip()
    return SPACE_AFTER.sub(r"\1", SPACE_BEFORE.sub(r"\1", text))


def quote_of(text):
    """The quoted text of a claim, None if it is not a quote, UNCLOSED if it opens one and never closes it."""
    m = INLINE.search(text)
    head = (text[:m.start()] if m else text).strip()
    if not head or head[0] not in "\"“":
        return None
    return head[1:-1] if len(head) > 1 and head[-1] in "\"”" else UNCLOSED


def data_parts(text):
    """Quoted fragments of three words or more and numbers of a DATA line, ignoring its fields."""
    body = INLINE.sub(" ", text)
    fragments = [f for m in FRAGMENT.finditer(body) for f in m.groups() if f and len(f.split()) >= 3]
    numbers = list(dict.fromkeys(NUMBER.findall(ISO_DATE.sub(" ", body))))
    return fragments, numbers


def has_number(text, number):
    return re.search(rf"(?<!\d)(?<!\d[.,]){re.escape(number)}(?![.,]?\d)", text) is not None


def cut_after(text, quote):
    """The 15 words after the first occurrence of `quote` followed by a condition, or None."""
    start = text.find(quote)
    while start >= 0:
        tail = text[start + len(quote):]
        if quote.endswith(","):
            tail = "," + tail
        if CONDITION.match(tail):
            return " ".join(tail[2:].split()[:15])
        start = text.find(quote, start + 1)
    return None


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


def check_sources(g, errors):
    """Validate source fields and originals. Returns {source: original path} for readable originals."""
    readable, referenced = {}, set()
    for n, fm in g.nodes.items():
        if fm.get("type") != "source":
            continue
        for key in SOURCE_REQUIRED:
            if not str(fm.get(key) or "").strip():
                errors.append(f"[[{n}]] is missing the `{key}` field")
        original = str(fm.get("original") or "").strip()
        if not original:
            if str(fm.get("url") or "").strip():
                errors.append(f"[[{n}]] has a `url` but no `original`: quotes cannot be checked")
            continue
        rel = PurePosixPath(original)
        referenced.add(rel.as_posix())
        if rel.is_absolute() or len(rel.parts) < 2 or rel.parts[0] != "originals" or ".." in rel.parts:
            errors.append(f"[[{n}]] `original` must be under `originals/`")
        elif not (g.vault / rel).is_file():
            errors.append(f"[[{n}]] `original` points to `{original}`, which does not exist")
        else:
            readable[n] = original
            if str(fm.get("url") or "").strip() and rel.suffix.lower() not in SERVED:
                errors.append(f"[[{n}]] has a `url` but its `original` is not the file as served (.pdf, .html)")
            if rel.stem != n:
                errors.append(f"[[{n}]] `original` is `{original}`: its name must be `{n}` plus an extension")
    folder = g.vault / "originals"
    for p in sorted(folder.rglob("*")) if folder.is_dir() else []:
        inner = p.relative_to(folder)
        if not p.is_file() or any(part.startswith(".") for part in inner.parts):
            continue
        rel = p.relative_to(g.vault).as_posix()
        extract = p.suffix == ".txt" and g.nodes.get(p.stem, {}).get("type") == "source"
        if rel not in referenced and not extract:
            errors.append(f"`{rel}` is not the `original` of any source")
    return readable


def check_quotes(g, originals, errors, ev):
    """Check quotes, quoted DATA fragments and DATA values against the original."""
    texts = {}
    for key, b in g.blocks.items():
        source = b["parent"]
        if g.nodes[source].get("type") != "source":
            continue
        quote, numbers, error = quote_of(b["text"]), [], "quote not found"
        if quote is UNCLOSED:
            errors.append(f"{show(key)} starts with a quote but does not close it before its fields")
            continue
        if quote is not None:
            targets = [quote]
        elif b["text"].lstrip().startswith("DATA:"):
            targets, numbers = data_parts(b["text"])
            error = "quoted fragment not found"
        else:
            continue
        if not targets and not numbers:
            continue
        original = originals.get(source)
        if not original:
            if targets and not g.nodes[source].get("original"):
                ev.unchecked.append(f"- {show(key)}: no original")
            continue
        if source not in texts:
            texts[source] = readings(g.vault / original)
        candidates, why = texts[source]
        if why:
            ev.unchecked.append(f"- {show(key)} `{original}`: {why}")
            continue
        found = {}
        for target in targets:
            q = normalize(target)
            found[target] = next((text for text in candidates if q in text), None)
        if any(text is None for text in found.values()):
            if b["fields"].get("verified") == "manual":
                ev.manual.append(f"- {show(key)} in `{original}`")
            else:
                errors.append(f"{show(key)} {error} in `{original}`")
        tails = [cut_after(text, normalize(t)) for t, text in found.items() if text is not None]
        tail = next((t for t in tails if t), None)
        if tail:
            ev.cut.append(f'- {show(key)} in `{original}`: "{tail}"')
        missing = [n for n in numbers if not any(has_number(text, n) for text in candidates)]
        if missing:
            ev.values.append(f"- {show(key)} in `{original}`: {', '.join(missing)}")


def check_relations(g, errors, ev):
    """`confirms` and `contradicts` between claims must point to a claim that exists."""
    for key, b in g.blocks.items():
        for rel in ("confirms", "contradicts"):
            for dest in links(b["fields"].get(rel)):
                if not g.exists(dest):
                    errors.append(f"{show(key)} `{rel}` points to `{dest}`, which does not exist")
    ev.relations = {rel: sum(len(list(links(b["fields"].get(rel)))) for b in g.blocks.values())
                    for rel in ("confirms", "contradicts")}


def check(g, errors):
    ev = Evidence()
    originals = check_sources(g, errors)
    check_quotes(g, originals, errors, ev)
    check_relations(g, errors, ev)
    return ev
