import sys

import pytest
import yaml

import check_diagnosis
import check_traceability
from conftest import TODAY

DATA = "DATA: 1 unit, from a test table. (confidence:: low)"
CLAIM = "[[S-20261101-test#^c01]]"
AREA_SECTIONS = ["Diagnosis areas", "Findings to classify", "Questions to revisit", "Synthesis to review",
                 "Stale knowledge", "Configuration"]
SEGMENT = {"profile": "", "criteria": "", "willingness_to_pay": "", "buying_process": "", "channels": "",
           "alternatives": [], "size": "", "served": "served", "basis": "working"}
COMPETITOR = {"segments": [], "proposition": "", "pricing": "", "size": "", "recent_move": ""}
OFFERING = {"segments": [], "proposition": "", "pricing": "", "stage": ""}
DEPENDENCY = {"role": "supplier", "dependency": "", "alternatives": ""}


def finding(text="Something changes.", kind="risk", status="raised", supports=CLAIM, extra=""):
    f = f"{text} (kind:: {kind}) (status:: {status})"
    if supports is not None:
        f += f" (supports:: {supports})"
    return f + extra


class Diagnosis:
    """Writes diagnosis/ into an Instance: every area pending, game.md empty, one source to cite."""

    def __init__(self, instance):
        self.i = instance
        instance.source(claims=(DATA, DATA))
        for area in check_diagnosis.AREAS:
            self.area(area)
        self.game()

    def area(self, name, status="pending", baseline=(), findings=(), prose="", updated=None, review=None, **fm):
        base = {"type": "area", "area": name, "block": check_diagnosis.AREAS.get(name, "context"),
                "status": status, "updated": updated, "review": review}
        base.update(fm)
        base = {k: v for k, v in base.items() if v is not DROP}
        body = f"# {name}\n\n{prose}\n\n## Baseline\n\n" + "".join(f"{l}\n" for l in baseline)
        body += "\n## Findings\n\n" + "".join(f"- {f} ^f{i:02d}\n" for i, f in enumerate(findings, 1))
        self.i._md(f"diagnosis/{name}.md", base, body)

    def entity(self, folder, stem, attrs, body=f"- Fact. {CLAIM}\n", **fm):
        base = {"type": "entity", "area": folder, "relevance": "high", "status": "active", "review": "2027-05-15"}
        base.update(attrs)
        base.update(fm)
        base = {k: v for k, v in base.items() if v is not DROP}
        self.i._md(f"diagnosis/{folder}/{stem}.md", base, body)

    def game(self, updated=None, review=None, body=""):
        self.i._md("diagnosis/game.md", {"type": "game", "updated": updated, "review": review}, f"# Game\n\n{body}")


DROP = object()


@pytest.fixture
def diag(instance):
    return Diagnosis(instance)


def pending_free(diag):
    """Every area covered by a baseline line, so only what a test adds shows up."""
    for area in check_diagnosis.AREAS:
        diag.area(area, status="covered", baseline=[f"State. {CLAIM}"], updated="2026-11-01")


# Gating

def test_no_diagnosis_folder_adds_nothing(instance):
    instance.source()
    result = instance.run()
    assert result.errors == []
    assert not set(AREA_SECTIONS) & set(result.headings)


def test_fresh_diagnosis_is_valid_and_lists_pending_areas(diag, instance):
    result = instance.run()
    assert result.errors == []
    assert result.code == 0
    assert result.headings[-6:] == AREA_SECTIONS
    assert result.items("Diagnosis areas") == [f"- [[{a}]] is pending" for a in check_diagnosis.AREAS]


def test_focus_diagnosis_puts_its_sections_first(diag, instance, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["check.py", str(instance.root), "--today", TODAY, "--focus", "diagnosis"])
    import check
    assert check.main() == 0
    report = (instance.root / "reports" / "impact-20261115.md").read_text(encoding="utf-8")
    headings = [l[3:] for l in report.splitlines() if l.startswith("## ")]
    assert headings[:7] == ["Validation"] + AREA_SECTIONS


# Areas

def test_missing_area_file(diag, instance):
    (instance.root / "diagnosis" / "results.md").unlink()
    result = instance.run()
    assert ("`diagnosis/results.md` is missing: every area is visited, even if only to say it is not material"
            in result.errors)
    assert result.code == 1


@pytest.mark.parametrize("status, error", [
    (DROP, "[[macro]] has no `status`"),
    ("done", "[[macro]] `status` is `done`: expected pending, covered, not_material or gap"),
])
def test_area_status_missing_or_invalid(diag, instance, status, error):
    diag.area("macro", status=status)
    assert error in instance.run().errors


def test_area_wrong_block(diag, instance):
    diag.area("macro", block="company")
    assert "[[macro]] needs `type: area`, `area: macro` and `block: context`" in instance.run().errors


@pytest.mark.parametrize("status, why", [("not_material", "the reason it is not material"),
                                         ("gap", "the evidence that is missing")])
def test_area_without_reason(diag, instance, status, why):
    diag.area("macro", status=status)
    assert f"[[macro]] is `{status}` but does not say {why}" in instance.run().errors


@pytest.mark.parametrize("status", ["not_material", "gap"])
def test_area_with_reason(diag, instance, status):
    diag.area("macro", status=status, prose="No regulation applies to shift software.")
    assert instance.run().errors == []


def test_baseline_line_without_claim(diag, instance):
    diag.area("market", status="covered", baseline=["Big market.", f"Growing. {CLAIM}"])
    assert "[[market]] Baseline line cites no claim: Big market." in instance.run().errors


def test_baseline_broken_link(diag, instance):
    diag.area("market", status="covered", baseline=["Big. [[S-20261101-test#^c09]]"])
    errors = instance.run().errors
    assert "[[market]] Baseline points to `S-20261101-test#c09`, which does not exist" in errors


def test_long_baseline_warns(diag, instance):
    diag.area("market", status="covered", baseline=[f"Line {i}. {CLAIM}" for i in range(6)])
    result = instance.run()
    assert result.errors == []
    assert "- [[market]] has a baseline of 6 lines (at most 5)" in result.items("Diagnosis areas")


def test_claims_cited_by_diagnosis_are_used(diag, instance):
    diag.area("market", status="covered", baseline=[f"State. {CLAIM}"],
              findings=[finding(supports="[[S-20261101-test#^c02]]")])
    assert instance.run().section("Unused claims") == ["None."]


def test_stale_area_is_not_an_archive_candidate(diag, instance):
    diag.area("market", review="2026-10-01")
    result = instance.run()
    assert "- [[market]] (area), review was due 2026-10-01" in result.items("Stale knowledge")
    assert result.items("Archive candidates") == []


# Findings

def test_finding_without_supports(diag, instance):
    diag.area("competition", findings=[finding(supports=None)])
    result = instance.run()
    assert "[[competition#^f01]] has no `supports`: a finding rests on claims" in result.errors
    assert result.code == 1


def test_finding_supports_broken_or_not_a_claim(diag, instance):
    diag.area("competition", findings=[finding(supports="[[S-20261101-test#^c09]]"),
                                       finding(supports="[[S-20261101-test]]")])
    errors = instance.run().errors
    assert "[[competition#^f01]] `supports` points to `S-20261101-test#c09`, which does not exist" in errors
    assert "[[competition#^f02]] `supports` points to `S-20261101-test`, which is not a claim" in errors


@pytest.mark.parametrize("kind, status, error", [
    ("threat", "raised", "[[competition#^f01]] `kind` is `threat`: expected game, risk or opportunity"),
    ("risk", "open", "[[competition#^f01]] `status` is `open`: expected new, raised, parked or retired"),
])
def test_finding_invalid_values(diag, instance, kind, status, error):
    diag.area("competition", findings=[finding(kind=kind, status=status)])
    assert error in instance.run().errors


def test_finding_without_id(diag, instance):
    diag.area("competition")
    path = instance.root / "diagnosis" / "competition.md"
    path.write_text(path.read_text(encoding="utf-8") + f"- {finding()}\n", encoding="utf-8")
    assert any(e.startswith("[[competition]] has a finding without a `^fNN` id") for e in instance.run().errors)


def test_new_finding_listed_to_classify(diag, instance):
    diag.area("competition", findings=[finding("A rival cut prices.", status="new"), finding()])
    result = instance.run()
    assert result.errors == []
    assert result.items("Findings to classify") == ["- [[competition#^f01]] (risk): A rival cut prices."]


def test_finding_about_must_be_entity(diag, instance):
    diag.entity("competition", "rival", COMPETITOR)
    diag.area("competition", findings=[finding(extra=" (about:: [[rival]])"),
                                       finding(extra=" (about:: [[S-20261101-test]])")])
    errors = instance.run().errors
    assert "[[competition#^f02]] `about` points to `S-20261101-test`, which is not an entity" in errors
    assert not any("^f01" in e for e in errors)


def test_findings_budget(diag, instance):
    diag.area("competition", findings=[finding()] * 4 + [finding(status="retired")] * 3)
    result = instance.run()
    assert "| Findings in [[competition]] | 4 | 3 | 5 | over soft limit |" in result.section("Budgets")
    assert result.code == 0
    diag.area("competition", findings=[finding()] * 6)
    assert instance.run().code == 1


# Questions

def test_question_kind_and_raised_by_valid(diag, instance):
    diag.area("competition", findings=[finding()])
    instance.framing(questions=["Do we follow? (status:: open) (kind:: risk) (raised_by:: [[competition#^f01]])"])
    assert instance.run().errors == []


def test_question_raised_by_broken(diag, instance):
    instance.framing(questions=["Do we follow? (status:: open) (raised_by:: [[competition#^f07]])"])
    result = instance.run()
    assert "[[framing#^q01]] `raised_by` points to `competition#f07`, which does not exist" in result.errors
    assert result.code == 1


def test_question_raised_by_not_a_finding(diag, instance):
    instance.framing(questions=[f"Do we follow? (status:: open) (raised_by:: {CLAIM})"])
    assert ("[[framing#^q01]] `raised_by` points to `S-20261101-test#c01`, which is not a finding"
            in instance.run().errors)


def test_question_kind_invalid(diag, instance):
    instance.framing(questions=["Do we follow? (status:: open) (kind:: threat)"])
    assert "[[framing#^q01]] `kind` is `threat`: expected game, risk or opportunity" in instance.run().errors


def test_question_raised_by_retired_finding(diag, instance):
    diag.area("competition", findings=[finding(status="retired")])
    instance.framing(questions=["Do we follow? (status:: open) (raised_by:: [[competition#^f01]])"])
    result = instance.run()
    assert result.errors == []
    assert result.items("Questions to revisit") == ["- [[framing#^q01]]: [[competition#^f01]] is retired"]


def test_expired_claim_reaches_question_and_stops(diag, instance):
    instance.source(review="2026-11-01", claims=(DATA, DATA))
    diag.area("competition", findings=[finding()])
    instance.framing(questions=["Do we follow? (status:: open) (raised_by:: [[competition#^f01]])"])
    instance.conclusion("C-custom-01", ["[[S-20261101-test#^c02]]"])
    result = instance.run()
    affected = result.section("Affected")
    assert any(r.startswith("| [[framing#^q01]] | question | source [[S-20261101-test]] expired") for r in affected)
    assert any(r.startswith("| [[competition#^f01]] | finding |") for r in affected)
    # C-custom-01 answers q01 but is reached only through its own claim, never through the question.
    assert not any("<- framing#q01" in r for r in affected)
    [line] = [l for l in result.items("Questions to revisit") if "expired" in l]
    assert line.startswith("- [[framing#^q01]]: source [[S-20261101-test]] expired on 2026-11-01")


# Entities

def test_entity_valid(diag, instance):
    diag.entity("market", "independents", SEGMENT)
    diag.entity("competition", "rival", {**COMPETITOR, "segments": ["[[independents]]"]})
    diag.entity("market", "groups", {**SEGMENT, "alternatives": ["[[rival]]"]})
    assert instance.run().errors == []


def test_entity_missing_field(diag, instance):
    diag.entity("competition", "rival", {**COMPETITOR, "pricing": DROP})
    result = instance.run()
    assert "[[rival]] is missing the `pricing` field" in result.errors
    assert result.code == 1


@pytest.mark.parametrize("key, value", [("relevance", "top"), ("status", "dead")])
def test_entity_invalid_common_value(diag, instance, key, value):
    diag.entity("competition", "rival", COMPETITOR, **{key: value})
    assert any(e.startswith(f"[[rival]] `{key}` is `{value}`") for e in instance.run().errors)


def test_entity_without_claim(diag, instance):
    diag.entity("competition", "rival", COMPETITOR, body="Known rival.\n")
    assert "[[rival]] cites no claim: an entity describes what sources say" in instance.run().errors


def test_archived_entity_without_claim(diag, instance):
    diag.entity("competition", "rival", COMPETITOR, body="Closed down.\n", status="archived")
    assert instance.run().errors == []


def test_entity_in_area_without_entities(diag, instance):
    diag.entity("results", "q3", {})
    assert any(e.startswith("[[q3]] is an entity outside `diagnosis/<area>/`") for e in instance.run().errors)


def test_entity_area_must_match_folder(diag, instance):
    diag.entity("competition", "rival", COMPETITOR, area="market")
    assert "[[rival]] `area` must be `competition`, the folder it is in" in instance.run().errors


def test_evidenced_segment_needs_criteria_alternatives_size(diag, instance):
    diag.entity("market", "independents", SEGMENT, basis="evidenced")
    errors = instance.run().errors
    for key in ("criteria", "alternatives", "size"):
        assert f"[[independents]] is evidenced but `{key}` is empty" in errors


def test_segment_invalid_served(diag, instance):
    diag.entity("market", "independents", SEGMENT, served="maybe")
    assert "[[independents]] `served` is `maybe`: expected served or not_served" in instance.run().errors


def test_competitor_segments_must_link_segments(diag, instance):
    diag.entity("competition", "other", COMPETITOR)
    diag.entity("competition", "rival", {**COMPETITOR, "segments": ["independents", "[[other]]", "[[ghost]]"]})
    errors = instance.run().errors
    assert "[[rival]] `segments` must link entities in `diagnosis/market/`: `independents` is not a link" in errors
    assert "[[rival]] `segments` points to `other`, which is not an entity in `diagnosis/market/`" in errors
    assert "[[rival]] `segments` points to `ghost`, which does not exist" in errors


def test_stale_entity_is_knowledge_not_archive(diag, instance):
    diag.entity("competition", "rival", COMPETITOR, review="2026-10-01")
    result = instance.run()
    assert "- [[rival]] (entity), review was due 2026-10-01" in result.items("Stale knowledge")
    assert result.items("Archive candidates") == []


def test_entity_budget_only_for_offering_and_ecosystem(diag, instance):
    for i in range(9):
        diag.entity("competition", f"rival-{i}", COMPETITOR)
    for i in range(6):
        diag.entity("offering", f"line-{i}", OFFERING)
    diag.entity("ecosystem", "payroll", DEPENDENCY)
    diag.entity("ecosystem", "old", DEPENDENCY, status="archived")
    result = instance.run()
    budgets = result.section("Budgets")
    assert "| Entities in [[offering]] | 6 | 5 | 8 | over soft limit |" in budgets
    assert "| Entities in [[ecosystem]] | 1 | 5 | 8 | ok |" in budgets
    assert not any("competition" in r for r in budgets)


# Segment field in conclusions

def test_conclusion_segment_must_be_link_with_diagnosis(diag, instance):
    instance.conclusion("C-porter-01", [CLAIM], framework="porter", force="rivalry", intensity="high",
                        segment="independents")
    assert ("[[C-porter-01]] `segment` must link a segment in `diagnosis/market/`: `independents` is not a link"
            in instance.run().errors)


def test_conclusion_segment_link_to_segment(diag, instance):
    diag.entity("market", "independents", SEGMENT)
    diag.entity("competition", "rival", COMPETITOR)
    instance.conclusion("C-porter-01", [CLAIM], framework="porter", force="rivalry", intensity="high",
                        segment="[[independents]]")
    instance.conclusion("C-porter-02", [CLAIM], framework="porter", force="rivalry", intensity="high",
                        segment="[[rival]]")
    errors = instance.run().errors
    assert errors == ["[[C-porter-02]] `segment` points to `rival`, which is not a segment in `diagnosis/market/`"]


def test_conclusion_segment_text_without_diagnosis(instance):
    instance.source()
    instance.conclusion("C-porter-01", [CLAIM], framework="porter", force="rivalry", intensity="high",
                        segment="independents")
    assert instance.run().errors == []


# game.md

def test_missing_game(diag, instance):
    (instance.root / "diagnosis" / "game.md").unlink()
    assert "`diagnosis/game.md` is missing" in instance.run().errors


def test_game_older_than_an_area(diag, instance):
    pending_free(diag)
    diag.area("competition", status="covered", baseline=[f"State. {CLAIM}"], updated="2026-11-10")
    purpose = "[[framing#^why]] [[framing#^how]] [[framing#^what]]"
    diag.game(updated="2026-11-05", body=purpose)
    result = instance.run()
    assert result.items("Synthesis to review") == [
        "- [[game]] updated 2026-11-05, before [[competition]] updated 2026-11-10"]


def test_game_never_written(diag, instance):
    pending_free(diag)
    assert instance.run().items("Synthesis to review") == [
        "- [[game]] has not been written since the areas were"]


def test_game_without_purpose_links(diag, instance):
    pending_free(diag)
    diag.game(updated="2026-11-12", body="We win on price. [[framing#^why]]")
    assert instance.run().items("Synthesis to review") == [
        "- [[game]] does not set the game against the purpose: no link to [[framing#^how]], [[framing#^what]]"]


# Purpose and configuration

def test_purpose_changed_by_must_be_decision(diag, instance):
    instance.decision("D-001-test")
    instance.write("framing.md", "---\ntype: framing\n---\n# Framing\n\n## Purpose\n\n"
                   "- Why we exist. (changed_by:: [[D-001-test]]) ^why\n"
                   f"- How we win. (changed_by:: {CLAIM}) ^how\n")
    errors = instance.run().errors
    assert errors == ["[[framing#^how]] `changed_by` points to `S-20261101-test#c01`, which is not a decision"]


def test_segments_key_in_config_warns(diag, instance):
    instance.write("strategy.config.yaml", yaml.safe_dump({"company": {"name": "T"}, "segments": ["a"]}))
    result = instance.run()
    assert result.errors == []
    [line] = result.items("Configuration")
    assert line.startswith("- `strategy.config.yaml` still has `segments`")


def test_defaults_cover_config_budgets():
    assert set(check_diagnosis.DEFAULT_BUDGETS).isdisjoint(check_traceability.DEFAULT_BUDGETS)
