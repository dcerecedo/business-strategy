"""The instance as Obsidian reads it: notes with their frontmatter, blocks with their inline fields, and links."""
import datetime as dt
import re
import sys

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("PyYAML not found. Activate the instance venv (source .venv/bin/activate) "
             "or create it: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")

SKIP_DIRS = {"reports", "originals", "scripts", "node_modules"}
LINK = re.compile(r"\[\[([^\]#|]+)(?:#\^?([^\]|]+))?(?:\|[^\]]*)?\]\]")
BLOCK = re.compile(r"^\s*[-*]\s+(.*?)\s*\^([\w-]+)\s*$")
INLINE = re.compile(r"\((\w+)::\s*([^)]*)\)")
LIST_ITEM = re.compile(r"^[-*]\s+(.*)$")


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
    """Link targets in a value or list of values, as `note` or `note#block` (without the caret)."""
    for v in value if isinstance(value, list) else [value]:
        for m in LINK.finditer(str(v or "")):
            yield m.group(1).strip() + (f"#{m.group(2)}" if m.group(2) else "")


def show(ref):
    return f"[[{ref.replace('#', '#^')}]]"


class Graph:
    """Every note outside hidden and engine folders. File stems are the link targets, so they must be unique."""

    def __init__(self, vault):
        self.vault = vault
        self.nodes, self.paths, self.bodies, self.blocks, self.errors = {}, {}, {}, {}, []
        for p in sorted(vault.rglob("*.md")):
            rel = p.relative_to(vault)
            if any(d.startswith(".") or d in SKIP_DIRS for d in rel.parts[:-1]) or p.name.startswith("_"):
                continue
            self._read(p, rel)

    def _read(self, p, rel):
        text, fm = p.read_text(encoding="utf-8"), {}
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError as e:
                    self.errors.append(f"`{rel}` has invalid frontmatter: {str(e).splitlines()[0]}")
                text = parts[2]
        if p.stem in self.nodes:
            self.errors.append(f"duplicate file name `{p.stem}` (`{rel}`): wikilinks become ambiguous")
            return
        self.nodes[p.stem] = fm if isinstance(fm, dict) else {}
        self.paths[p.stem] = rel
        self.bodies[p.stem] = text
        section = None
        for line in text.splitlines():
            if line.startswith("#"):
                section = line.lstrip("#").strip()
            m = BLOCK.match(line)
            if m:
                key = f"{p.stem}#{m.group(2)}"
                if key in self.blocks:
                    self.errors.append(f"duplicate block id `^{m.group(2)}` in `{rel}`")
                self.blocks[key] = {"parent": p.stem, "id": m.group(2), "section": section, "text": m.group(1),
                                    "fields": {k: v.strip() for k, v in INLINE.findall(m.group(1))}}

    def kind(self, ref):
        """The type of a note, or for a block the type of the note it is in."""
        return self.nodes.get(ref.split("#")[0], {}).get("type")

    def exists(self, ref):
        return ref in self.blocks if "#" in ref else ref in self.nodes

    def is_claim(self, ref):
        return "#" in ref and ref in self.blocks and self.kind(ref) == "source"

    def is_question(self, ref):
        return "#" in ref and ref in self.blocks and self.kind(ref) == "framing" and self.blocks[ref]["id"].startswith("q")

    def section_lines(self, stem, heading):
        """Lines under a `## heading` of a note, up to the next heading."""
        out, inside = [], False
        for line in self.bodies.get(stem, "").splitlines():
            if line.startswith("#"):
                inside = line.lstrip("#").strip() == heading
                continue
            if inside:
                out.append(line)
        return out
