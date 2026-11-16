"""Diagnosis checks: area files, findings, entities, game.md and the questions findings raise.

Runs only when the instance has a diagnosis/ folder: a question-first instance without one is valid.
"""
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from graph import BLOCK, INLINE, LINK, LIST_ITEM, links, show, to_date

# The fixed order of the walk: context first, then the company.
AREAS = {"macro": "context", "market": "context", "ecosystem": "context", "competition": "context",
         "segments": "company", "offering": "company", "go_to_market": "company",
         "business_model": "company", "capabilities": "company", "results": "company"}
AREA_STATUS = ["pending", "covered", "not_material", "gap"]
KINDS = ["game", "risk", "opportunity"]
FINDING_STATUS = ["new", "raised", "parked", "retired"]
FINDING_ID = re.compile(r"f\d{2,}")
BASELINE_LINES = 5
ENTITY_COMMON = ["area", "relevance", "status", "review"]
ENTITY_KEYS = {
    "market": ["profile", "criteria", "willingness_to_pay", "buying_process", "channels", "alternatives",
               "size", "served", "basis"],
    "competition": ["segments", "proposition", "pricing", "size", "recent_move"],
    "offering": ["segments", "proposition", "pricing", "stage"],
    "ecosystem": ["role", "dependency", "alternatives"],
}
ENTITY_VALUES = {"relevance": ["high", "medium", "low"], "status": ["active", "watch", "archived"],
                 "served": ["served", "not_served"], "basis": ["working", "evidenced"],
                 "role": ["supplier", "partner", "regulator"]}
EVIDENCED = ["criteria", "alternatives", "size"]
# Attributes holding links to other entities: (area of the entity, attribute) -> area of the target.
ENTITY_LINKS = {("market", "alternatives"): "competition", ("competition", "segments"): "market",
                ("offering", "segments"): "market"}
BUDGET_ENTITY_AREAS = ["offering", "ecosystem"]
DEFAULT_BUDGETS = {"findings_per_area": [3, 5], "entities_per_area": [5, 8]}
PURPOSE = ["why", "how", "what"]
KNOWLEDGE_TYPES = {"area", "entity", "game"}
SECTIONS = ["Diagnosis areas", "Findings to classify", "Questions to revisit", "Synthesis to review",
            "Stale knowledge", "Configuration"]


@dataclass
class Diagnosis:
    edges: dict = field(default_factory=lambda: defaultdict(set))
    used: set = field(default_factory=set)
    budget_items: list = field(default_factory=list)
    sections: dict = field(default_factory=lambda: {title: [] for title in SECTIONS})
    knowledge_types: frozenset = frozenset(KNOWLEDGE_TYPES)


def expect(value, allowed):
    return f"`{value}`: expected {', '.join(allowed[:-1])} or {allowed[-1]}"


def _cite(d, claim, item):
    """`item` rests on `claim`: alerts on the claim reach it, and the claim counts as used."""
    d.edges[claim].add(item)
    d.used.add(claim)


def check_links(g, owner, refs, label, errors):
    """Errors for links that do not exist. Returns the ones that do."""
    ok = []
    for dest in refs:
        if g.exists(dest):
            ok.append(dest)
        else:
            errors.append(f"{owner} {label} points to `{dest}`, which does not exist")
    return ok


def check_plain_links(owner, label, value, errors, must):
    """Errors for non-empty items of `value` that are not wikilinks: they would pass every link check."""
    for item in value if isinstance(value, list) else [value] if value else []:
        if str(item).strip() and not LINK.search(str(item)):
            errors.append(f"{owner} {label} must link {must}: `{item}` is not a link")


def is_entity(g, ref, area=None):
    return "#" not in ref and g.kind(ref) == "entity" and (area is None or g.nodes[ref].get("area") == area)


def check_entity_links(g, owner, key, value, area, errors):
    """`value` holds links to entities in `diagnosis/<area>/`, and only that."""
    where = f"`diagnosis/{area}/`"
    check_plain_links(owner, f"`{key}`", value, errors, f"entities in {where}")
    for dest in check_links(g, owner, list(links(value)), f"`{key}`", errors):
        if not is_entity(g, dest, area):
            errors.append(f"{owner} `{key}` points to `{dest}`, which is not an entity in {where}")


def check_areas(g, today, errors, d):
    updated = {}
    for area, block in AREAS.items():
        rel = PurePosixPath("diagnosis", f"{area}.md")
        fm = g.nodes.get(area)
        if fm is None or PurePosixPath(g.paths[area].as_posix()) != rel:
            errors.append(f"`{rel}` is missing: every area is visited, even if only to say it is not material")
            continue
        owner = f"[[{area}]]"
        if fm.get("type") != "area" or fm.get("area") != area or fm.get("block") != block:
            errors.append(f"{owner} needs `type: area`, `area: {area}` and `block: {block}`")
        status = fm.get("status")
        if not status:
            errors.append(f"{owner} has no `status`")
        elif status not in AREA_STATUS:
            errors.append(f"{owner} `status` is {expect(status, AREA_STATUS)}")
        if status == "pending":
            d.sections["Diagnosis areas"].append(f"- {owner} is pending")
        if status in ("not_material", "gap"):
            # The reason is prose of its own, outside the baseline and the findings.
            prose, heading = [], None
            for line in g.bodies[area].splitlines():
                if line.startswith("#"):
                    heading = line.lstrip("#").strip()
                elif line.strip() and heading not in ("Baseline", "Findings"):
                    prose.append(line)
            if not prose:
                why = "the reason it is not material" if status == "not_material" else "the evidence that is missing"
                errors.append(f"{owner} is `{status}` but does not say {why}")
        baseline = [l for l in g.section_lines(area, "Baseline") if l.strip()]
        if len(baseline) > BASELINE_LINES:
            d.sections["Diagnosis areas"].append(f"- {owner} has a baseline of {len(baseline)} lines (at most {BASELINE_LINES})")
        for line in baseline:
            refs = check_links(g, owner, list(links(line)), "Baseline", errors)
            claims = [r for r in refs if g.is_claim(r)]
            if not claims:
                errors.append(f"{owner} Baseline line cites no claim: {line.strip()[:60]}")
            for c in claims:
                _cite(d, c, area)
        for b in (b for b in g.blocks.values() if b["parent"] == area and FINDING_ID.fullmatch(b["id"])):
            if b["section"] != "Findings":
                errors.append(f"{owner} has a finding `^{b['id']}` outside `## Findings`")
        for line in g.section_lines(area, "Findings"):
            item = LIST_ITEM.match(line)
            block = BLOCK.match(line)
            if item and (not block or not FINDING_ID.fullmatch(block.group(2))):
                errors.append(f"{owner} has a finding without a `^fNN` id: {item.group(1)[:60]}")
        review = to_date(fm.get("review"))
        if review and review < today:
            d.sections["Stale knowledge"].append(f"- {owner} (area), review was due {review}")
        if to_date(fm.get("updated")):
            updated[area] = to_date(fm.get("updated"))
    return updated


def check_findings(g, errors, d):
    """Returns the findings by id."""
    findings, per_area = {}, defaultdict(int)
    for key, b in g.blocks.items():
        if g.kind(key) != "area" or not FINDING_ID.fullmatch(b["id"]) or b["section"] != "Findings":
            continue
        findings[key] = b
        f, owner = b["fields"], show(key)
        kind, status = f.get("kind"), f.get("status")
        if kind not in KINDS:
            errors.append(f"{owner} `kind` is {expect(kind, KINDS)}" if kind else f"{owner} has no `kind`")
        if status not in FINDING_STATUS:
            errors.append(f"{owner} `status` is {expect(status, FINDING_STATUS)}" if status else f"{owner} has no `status`")
        supports = list(links(f.get("supports")))
        if not supports:
            errors.append(f"{owner} has no `supports`: a finding rests on claims")
        check_plain_links(owner, "`supports`", f.get("supports"), errors, "claims")
        for dest in check_links(g, owner, supports, "`supports`", errors):
            if not g.is_claim(dest):
                errors.append(f"{owner} `supports` points to `{dest}`, which is not a claim")
            elif status != "retired":
                # A retired finding no longer rests on its claims: alerts on them are not its concern.
                _cite(d, dest, key)
        check_plain_links(owner, "`about`", f.get("about"), errors, "entities")
        for dest in check_links(g, owner, list(links(f.get("about"))), "`about`", errors):
            if not is_entity(g, dest):
                errors.append(f"{owner} `about` points to `{dest}`, which is not an entity")
        if status == "new":
            text = INLINE.sub("", b["text"]).strip()
            d.sections["Findings to classify"].append(f"- {owner} ({kind}): {text[:80]}")
        if status != "retired":
            per_area[b["parent"]] += 1
    for area, n in sorted(per_area.items()):
        d.budget_items.append((f"Findings in [[{area}]]", n, "findings_per_area"))
    return findings


def check_questions(g, findings, errors, d):
    for key, b in g.blocks.items():
        if g.kind(key) != "framing" or not b["id"].startswith("q"):
            continue
        f, owner = b["fields"], show(key)
        if "kind" in f and f["kind"] not in KINDS:
            errors.append(f"{owner} `kind` is {expect(f['kind'], KINDS)}")
        check_plain_links(owner, "`raised_by`", f.get("raised_by"), errors, "findings")
        for dest in check_links(g, owner, list(links(f.get("raised_by"))), "`raised_by`", errors):
            if dest not in findings:
                errors.append(f"{owner} `raised_by` points to `{dest}`, which is not a finding")
                continue
            d.edges[dest].add(key)
            if findings[dest]["fields"].get("status") == "retired":
                d.sections["Questions to revisit"].append(f"- {owner}: {show(dest)} is retired")


def check_entities(g, today, errors, d):
    active = defaultdict(int)
    for n, fm in sorted(g.nodes.items()):
        if fm.get("type") != "entity":
            continue
        owner, parts = f"[[{n}]]", g.paths[n].parts
        area = parts[1] if len(parts) == 3 and parts[0] == "diagnosis" else None
        if area not in ENTITY_KEYS:
            errors.append(f"{owner} is an entity outside `diagnosis/<area>/`, for areas {', '.join(ENTITY_KEYS)}")
            continue
        if fm.get("area") != area:
            errors.append(f"{owner} `area` must be `{area}`, the folder it is in")
        for key in ENTITY_COMMON + ENTITY_KEYS[area]:
            if key not in fm:
                errors.append(f"{owner} is missing the `{key}` field")
        for key, allowed in ENTITY_VALUES.items():
            value = fm.get(key)
            if key in ENTITY_COMMON + ENTITY_KEYS[area] and value not in (None, "") and value not in allowed:
                errors.append(f"{owner} `{key}` is {expect(value, allowed)}")
        if area == "market" and fm.get("basis") == "evidenced":
            for key in EVIDENCED:
                if not fm.get(key):
                    errors.append(f"{owner} is evidenced but `{key}` is empty")
        for key, value in fm.items():
            target = ENTITY_LINKS.get((area, key))
            if target:
                check_entity_links(g, owner, key, value, target, errors)
            else:
                check_links(g, owner, list(links(value)), f"`{key}`", errors)
        archived = fm.get("status") == "archived"
        claims = [r for r in check_links(g, owner, list(links(g.bodies[n])), "body", errors) if g.is_claim(r)]
        if not claims and not archived:
            errors.append(f"{owner} cites no claim: an entity describes what sources say")
        for c in claims if not archived else []:
            _cite(d, c, n)
        review = to_date(fm.get("review"))
        if not archived:
            active[area] += 1
            if review and review < today:
                d.sections["Stale knowledge"].append(f"- {owner} (entity), review was due {review}")
    for area in BUDGET_ENTITY_AREAS:
        if active[area]:
            d.budget_items.append((f"Entities in [[{area}]]", active[area], "entities_per_area"))


def check_segment_field(g, errors):
    """With a diagnosis, segments are only defined as entities in diagnosis/market/."""
    for n, fm in sorted(g.nodes.items()):
        if fm.get("type") != "conclusion" or not fm.get("segment"):
            continue
        check_entity_links(g, f"[[{n}]]", "segment", fm["segment"], "market", errors)


def check_game(g, updated, today, errors, d):
    fm = g.nodes.get("game")
    if fm is None or g.paths["game"].as_posix() != "diagnosis/game.md":
        errors.append("`diagnosis/game.md` is missing")
        return
    if fm.get("type") != "game":
        errors.append("[[game]] needs `type: game`")
    synthesis = d.sections["Synthesis to review"]
    written = to_date(fm.get("updated"))
    if updated and not written:
        synthesis.append("- [[game]] has not been written since the areas were")
    for area, date in sorted(updated.items()):
        if written and date > written:
            synthesis.append(f"- [[game]] updated {written}, before [[{area}]] updated {date}")
    if written:
        missing = [p for p in PURPOSE if f"framing#{p}" not in set(links(g.bodies["game"]))]
        if missing:
            synthesis.append(f"- [[game]] does not set the game against the purpose: no link to "
                             + ", ".join(show(f"framing#{p}") for p in missing))
    review = to_date(fm.get("review"))
    if review and review < today:
        d.sections["Stale knowledge"].append(f"- [[game]] (game), review was due {review}")


def check(g, cfg, today, errors):
    if not (g.vault / "diagnosis").is_dir():
        return None
    d = Diagnosis()
    updated = check_areas(g, today, errors, d)
    findings = check_findings(g, errors, d)
    check_questions(g, findings, errors, d)
    check_entities(g, today, errors, d)
    check_segment_field(g, errors)
    check_game(g, updated, today, errors, d)
    if "segments" in cfg:
        d.sections["Configuration"].append(
            "- `strategy.config.yaml` still has `segments`: segments are entities in `diagnosis/market/`; "
            "move them there and delete the key")
    return d


def revisit(g, d, affected):
    """Questions an alert reached through the findings that raised them."""
    for key in sorted(affected):
        if g.is_question(key):
            for reason, path in affected[key]:
                d.sections["Questions to revisit"].append(f"- {show(key)}: {reason} ({path})")
