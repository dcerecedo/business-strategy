"""Traceability checks: links and required fields along the chain, gaps, alert propagation, budgets and reviews."""
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field

from graph import BLOCK, LIST_ITEM, links, show, to_date

LINK_FIELDS = ["supports", "against", "conclusions", "hypotheses", "decisions", "question", "supersedes",
               "benefit", "barrier"]
NUMBERED = re.compile(r"^([DH])-(\d+)")
LIVE = {"proposed", "active", "under_review"}
ROOT_TYPES = {"decision", "okr", "direction", "framing"}
DEFAULT_BUDGETS = {"open_questions": [5, 7], "live_decisions": [7, 12],
                   "hypotheses_per_decision": [3, 5], "conclusions_per_framework": [5, 8],
                   "vital_gaps_per_question": [3, 3]}
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
GAP_ORIGINS = ["internal", "customer", "installer", "purchase", "manual"]
GAP_ID = re.compile(r"g\d{2,}")
ORDER = {"okr": 0, "direction": 1, "decision": 2, "conclusion": 3, "hypothesis": 4, "question": 5,
         "finding": 6, "game": 7, "area": 8, "entity": 9}


@dataclass
class Traceability:
    affected: dict = field(default_factory=dict)
    budgets: list = field(default_factory=list)
    hard: bool = False
    due: list = field(default_factory=list)
    archive: list = field(default_factory=list)
    unused: list = field(default_factory=list)


class Budgets:
    """Rows of the budget table. Soft limits warn; a hard limit makes the run fail."""

    def __init__(self, limits):
        self.limits, self.rows, self.hard = limits, [], False

    def add(self, label, n, key):
        soft, limit = self.limits[key]
        state = "OVER HARD LIMIT" if n > limit else "over soft limit" if n > soft else "ok"
        self.hard |= n > limit
        self.rows.append(f"| {label} | {n} | {soft} | {limit} | {state} |")


def check_ids(g, errors):
    numbered = defaultdict(list)
    for n in g.nodes:
        m = NUMBERED.match(n)
        if m:
            numbered[(m.group(1), int(m.group(2)))].append(n)
    for (prefix, num), names in sorted(numbered.items()):
        if len(names) > 1:
            errors.append(f"ID {prefix}-{num:03d} used by several files: {', '.join(sorted(names))}")


def check_notes(g, errors):
    """Links in frontmatter and the required fields of conclusions and hypotheses. Returns reverse links."""
    reverse = defaultdict(set)
    for n, fm in g.nodes.items():
        for key in LINK_FIELDS:
            for dest in links(fm.get(key)):
                if not g.exists(dest):
                    errors.append(f"[[{n}]] `{key}` points to `{dest}`, which does not exist")
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
            for dest in sorted(set(links(fm.get("benefit"))) & set(links(fm.get("against")))):
                errors.append(f"[[{n}]] {show(dest)} is both in `benefit` and in `against`")
        if t == "hypothesis" and not (fm.get("metric") and fm.get("threshold")):
            errors.append(f"[[{n}]] has no metric and threshold: it is an assumption, not a hypothesis")
    for key, b in g.blocks.items():
        if g.kind(key) != "framing":
            continue
        if b["fields"].get("status") == "answered":
            if not list(links(b["fields"].get("answered_by"))):
                errors.append(f"{show(key)} is answered but names no decision in `answered_by`")
        for dest in links(b["fields"].get("changed_by")):
            if g.kind(dest) != "decision" or "#" in dest:
                errors.append(f"{show(key)} `changed_by` points to `{dest}`, which is not a decision")
    return reverse


def check_gaps(g, errors):
    """Validate gaps in framing.md. Returns the number of vital gaps per question."""
    for stem in (n for n, fm in g.nodes.items() if fm.get("type") == "framing"):
        for line in g.section_lines(stem, "Gaps"):
            item = LIST_ITEM.match(line)
            if item:
                block = BLOCK.match(line)
                if not block or not GAP_ID.fullmatch(block.group(2)):
                    errors.append(f"`{g.paths[stem]}` has a gap without a `^gNN` id: {item.group(1)[:60]}")
    vital = defaultdict(int)
    for key, b in g.blocks.items():
        if g.kind(key) != "framing" or not b["id"].startswith("g"):
            continue
        fields = b["fields"]
        questions = list(links(fields.get("question")))
        if not questions:
            errors.append(f"{show(key)} has no `question`")
        for dest in questions:
            if not g.exists(dest):
                errors.append(f"{show(key)} `question` points to `{dest}`, which does not exist")
            elif fields.get("priority") == "vital":
                vital[dest] += 1
        origin = fields.get("origin")
        if not origin:
            errors.append(f"{show(key)} has no `origin`")
        elif origin not in GAP_ORIGINS:
            errors.append(f"{show(key)} `origin` is `{origin}`: expected {', '.join(GAP_ORIGINS[:-1])} or {GAP_ORIGINS[-1]}")
    return vital


def alert_seeds(g, today):
    """Expired sources, refuted or overdue hypotheses and contradicted claims, as (item, reason)."""
    seeds = []
    for n, fm in g.nodes.items():
        review = to_date(fm.get("review"))
        if fm.get("type") == "source" and review and review < today:
            seeds += [(k, f"source [[{n}]] expired on {review}") for k, b in g.blocks.items() if b["parent"] == n]
        if fm.get("type") == "hypothesis":
            deadline = to_date(fm.get("deadline"))
            if fm.get("status") == "refuted":
                seeds.append((n, f"[[{n}]] refuted"))
            elif fm.get("status") == "open" and deadline and deadline < today:
                seeds.append((n, f"[[{n}]] past its deadline ({deadline}) and not reviewed"))
    for key, b in g.blocks.items():
        for dest in links(b["fields"].get("contradicts")):
            seeds.append((dest, f"{show(dest)} contradicted by {show(key)}"))
    return seeds


def propagate(seeds, reverse, stop=lambda n: False):
    """Every item that relies, directly or through others, on an alert seed, with the path.

    Items for which `stop` is true are reported but the alert goes no further."""
    affected = defaultdict(list)
    for origin, reason in seeds:
        queue, seen = deque([(origin, [origin])]), {origin}
        while queue:
            n, path = queue.popleft()
            for parent in sorted(reverse.get(n, ())):
                if parent not in seen:
                    seen.add(parent)
                    affected[parent].append((reason, " <- ".join(reversed(path + [parent]))))
                    if not stop(parent):
                        queue.append((parent, path + [parent]))
    return affected


def is_question(g, ref):
    return "#" in ref and g.kind(ref) == "framing" and ref in g.blocks and g.blocks[ref]["id"].startswith("q")


def check_budgets(g, budgets, vital):
    open_q = [k for k, b in g.blocks.items() if g.kind(k) == "framing" and b["fields"].get("status") == "open"]
    budgets.add("Open questions", len(open_q), "open_questions")
    live = sorted(n for n, f in g.nodes.items() if f.get("type") == "decision" and f.get("status") in LIVE)
    budgets.add("Live decisions", len(live), "live_decisions")
    for d in live:
        budgets.add(f"Hypotheses in [[{d}]]", len(list(links(g.nodes[d].get("hypotheses")))), "hypotheses_per_decision")
    per_fw = defaultdict(int)
    for f in g.nodes.values():
        if f.get("type") == "conclusion" and f.get("status") != "archived":
            per_fw[str(f.get("framework"))] += 1
    for fw, n in sorted(per_fw.items()):
        budgets.add(f"Conclusions for {fw}", n, "conclusions_per_framework")
    for dest, n in sorted(vital.items()):
        budgets.add(f"Vital gaps for {show(dest)}", n, "vital_gaps_per_question")
    return live


def check_reviews(g, live, today, tr, skip=frozenset()):
    """Only what a live decision relies on is reviewed; the rest is archived (rule 7).

    Types in `skip` are kept by design (the diagnosis) and reported elsewhere when stale."""
    claimed, stack = set(), list(live)
    while stack:
        n = stack.pop()
        for key in LINK_FIELDS:
            for dest in links(g.nodes.get(n, {}).get(key)):
                stem = dest.split("#")[0]
                if stem not in claimed:
                    claimed.add(stem)
                    stack.append(stem)
    for n, fm in sorted(g.nodes.items()):
        review = to_date(fm.get("review"))
        if not review or review >= today or fm.get("status") in {"archived", "superseded"} or fm.get("type") in skip:
            continue
        line = f"- [[{n}]] ({fm.get('type')}), review was due {review}"
        (tr.due if fm.get("type") in ROOT_TYPES or n in claimed else tr.archive).append(line)


def unused_claims(g, also_used=frozenset()):
    used = {dest for fm in g.nodes.values() if fm.get("type") == "conclusion"
            for key in LINK_FIELDS for dest in links(fm.get(key))} | set(also_used)
    unused = defaultdict(list)
    for key, b in g.blocks.items():
        if g.kind(key) == "source" and key not in used:
            unused[b["parent"]].append(f"^{b['id']}")
    return [f"- [[{n}]]: {', '.join(ids)}" for n, ids in sorted(unused.items())]


def check(g, cfg, today, errors, defaults=DEFAULT_BUDGETS, diagnosis=None):
    """`diagnosis` adds the links from findings, baselines, entities and questions to claims and findings,
    its budgets and the knowledge types that are not reviewed here."""
    tr = Traceability()
    check_ids(g, errors)
    reverse = check_notes(g, errors)
    vital = check_gaps(g, errors)
    if diagnosis:
        for dest, items in diagnosis.edges.items():
            reverse[dest] |= items
    # A question is reported but the alert stops there: whether the decision answering it is affected
    # is for a person to judge.
    tr.affected = propagate(alert_seeds(g, today), reverse, stop=lambda n: is_question(g, n))
    budgets = Budgets({**defaults, **(cfg.get("budgets") or {})})
    live = check_budgets(g, budgets, vital)
    for label, n, key in diagnosis.budget_items if diagnosis else []:
        budgets.add(label, n, key)
    tr.budgets, tr.hard = budgets.rows, budgets.hard
    check_reviews(g, live, today, tr, skip=diagnosis.knowledge_types if diagnosis else frozenset())
    tr.unused = unused_claims(g, diagnosis.used if diagnosis else frozenset())
    return tr


def item_type(g, ref):
    if "#" not in ref:
        return g.kind(ref)
    return {"framing": "question", "area": "finding"}.get(g.kind(ref), "block")


def affected_rows(g, affected):
    rows = []
    for n in sorted(affected, key=lambda k: (ORDER.get(item_type(g, k), 9), k)):
        rows += [f"| {show(n)} | {item_type(g, n)} | {reason} | {path} |" for reason, path in affected[n]]
    return rows
