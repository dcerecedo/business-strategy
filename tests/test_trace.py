import hashlib
import re
import shutil

import pytest
import yaml

from conftest import DROP, FIXTURES, ROOT, Instance, hide_pdftotext

ACME = ROOT / "examples" / "acme"
CATALOG = ROOT / "skills" / "apply-framework" / "frameworks.md"
DATA = "DATA: 1 unit, from a test table. (confidence:: low)"
ORIGINS = ["internal", "customer", "installer", "purchase", "manual"]
CUT = "Quotes cut before a condition"
VALUES = "DATA values not found"
UNUSED = "Unused claims"
NOT_SERVED = "has a `url` but its `original` is not the file as served (.pdf, .html)"


def claim(text):
    return f'"{text}" (confidence:: high)'


# 1. Sources

@pytest.mark.parametrize("field", ["origin", "captured", "review"])
@pytest.mark.parametrize("value", ["missing", "empty"])
def test_source_required_field_missing_or_empty(instance, field, value):
    stem = instance.source(**{field: DROP if value == "missing" else None})
    assert f"[[{stem}]] is missing the `{field}` field" in instance.run().errors


def test_source_url_without_original(instance):
    stem = instance.source(url="https://example.org/x")
    assert f"[[{stem}]] has a `url` but no `original`: quotes cannot be checked" in instance.run().errors


def test_source_without_url_or_original_is_valid(instance):
    instance.source()
    result = instance.run()
    assert result.errors == []
    assert result.code == 0


def test_source_original_file_missing(instance):
    stem = instance.source(url="https://example.org/x", original="originals/S-20261101-test.pdf")
    assert (f"[[{stem}]] `original` points to `originals/S-20261101-test.pdf`, which does not exist"
            in instance.run().errors)


def test_source_original_stem_mismatch(instance):
    instance.original("S-20261101-other.txt", "text")
    stem = instance.source(original="originals/S-20261101-other.txt")
    assert (f"[[{stem}]] `original` is `originals/S-20261101-other.txt`: its name must be `{stem}` plus an extension"
            in instance.run().errors)


def test_source_original_outside_originals(instance):
    instance.write("docs/S-20261101-test.txt", "text")
    stem = instance.source(original="docs/S-20261101-test.txt")
    assert f"[[{stem}]] `original` must be under `originals/`" in instance.run().errors


# 1. Originals as served

def served_source(instance, ext, text="Alpha beta.", claims=(DATA,), url="https://example.org/x"):
    stem = "S-20261101-test"
    instance.original(f"{stem}{ext}", text)
    return instance.source(stem, list(claims), url=url, original=f"originals/{stem}{ext}")


@pytest.mark.parametrize("ext", [".md", ".txt", ".docx"])
def test_url_original_not_served(instance, ext):
    stem = served_source(instance, ext)
    result = instance.run()
    assert f"[[{stem}]] {NOT_SERVED}" in result.errors
    assert result.code == 1


@pytest.mark.parametrize("ext", [".md", ".txt"])
def test_no_url_md_or_txt_original_valid(instance, ext):
    served_source(instance, ext, url=DROP)
    assert instance.run().errors == []


@pytest.mark.parametrize("ext", [".html", ".htm", ".HTML"])
def test_url_original_served_valid(instance, ext):
    served_source(instance, ext, text="<p>Alpha beta.</p>", claims=[claim("Alpha beta.")])
    assert instance.run().errors == []


def test_url_missing_md_original_one_error(instance):
    stem = instance.source(url="https://example.org/x", original="originals/S-20261101-test.md")
    assert instance.run().errors == [
        f"[[{stem}]] `original` points to `originals/S-20261101-test.md`, which does not exist"]


def test_url_md_original_quotes_still_checked(instance):
    stem = served_source(instance, ".md", claims=[claim("Gamma delta.")])
    errors = instance.run().errors
    assert f"[[{stem}]] {NOT_SERVED}" in errors
    assert f"[[{stem}#^c01]] quote not found in `originals/{stem}.md`" in errors


# 2. Orphan originals

def test_orphan_original(instance):
    instance.original("S-20261101-lost.pdf", b"%PDF-1.4\n")
    assert "`originals/S-20261101-lost.pdf` is not the `original` of any source" in instance.run().errors


def test_orphan_in_subdirectory(instance):
    instance.original("sub/foo.pdf", b"%PDF-1.4\n")
    assert "`originals/sub/foo.pdf` is not the `original` of any source" in instance.run().errors


def test_dot_entries_in_originals_ignored(instance):
    instance.original(".gitkeep", "")
    instance.original(".cache/x.pdf", b"%PDF-1.4\n")
    assert instance.run().errors == []


def test_txt_extract_beside_source_not_orphan(instance):
    instance.quoted("Alpha beta.", claim("Alpha beta."), ext=".html", stem="S-20261101-page")
    instance.original("S-20261101-page.txt", "Alpha beta.")
    assert instance.run().errors == []


def test_txt_without_matching_source_is_orphan(instance):
    instance.source()
    instance.original("S-20261101-nosource.txt", "text")
    assert "`originals/S-20261101-nosource.txt` is not the `original` of any source" in instance.run().errors


# 3. Quote detection: the original never contains "gamma", so a detected quote fails

@pytest.mark.parametrize("text, detected", [
    ('"gamma" (confidence:: high)', True),
    ('"gamma"', True),
    ('"gamma"   (confidence:: high) (confirms:: [[S-20261101-quoted#^c02]])', True),
    ("“gamma” (confidence:: high)", True),
    ('DATA: "gamma" counted from table 2. (confidence:: low)', False),
    ("Plain note without quotes. (confidence:: low)", False),
])
def test_quote_detection(instance, text, detected):
    stem = instance.quoted("Alpha beta.", [text, DATA])
    errors = instance.run().errors
    assert (f"[[{stem}#^c01]] quote not found in `originals/{stem}.txt`" in errors) is detected


def test_quote_with_inner_quotes(instance):
    instance.quoted('He said "no" today.', claim('He said "no" today.'))
    assert instance.run().errors == []


def test_unclosed_quote_is_error(instance):
    stem = instance.quoted("Brand says alpha.", '"Brand" says alpha. (confidence:: low)')
    assert (f"[[{stem}#^c01]] starts with a quote but does not close it before its fields"
            in instance.run().errors)


def test_data_line_not_checked(instance):
    instance.quoted("Alpha beta.", "DATA: 1,240 units in 2025, summed from table 3. (confidence:: medium)")
    result = instance.run()
    assert result.errors == []
    assert result.items("Quotes not checked automatically") == []


# 3. Normalization

@pytest.mark.parametrize("raw, expected", [
    ("café", "café"),
    ("substi­\n  tution", "substitution"),
    ("substi­tution", "substitution"),
    ("“quoted” and ‘single’ „pl‟", "\"quoted\" and 'single' \"pl\""),
    ("39 EUR", "39 EUR"),
    ("62 %", "62 %"),
    ("alpha \n\t  beta", "alpha beta"),
    ("ﬁnal ﬂow ﬀ ﬃ ﬄ", "final flow ff ffi ffl"),
    ("a , b", "a, b"),
    ("a . b", "a. b"),
    ("a ; b : c", "a; b: c"),
    ("( x )", "(x)"),
    ("[ x ]", "[x]"),
    ("f( x ) , y", "f(x), y"),
])
def test_normalize(trace, raw, expected):
    assert trace.normalize(raw) == expected


# 3. Matching

def test_quote_exact(instance):
    instance.quoted("Intro. 62% of venues plan in a spreadsheet. Outro.", claim("62% of venues plan in a spreadsheet."))
    assert instance.run().errors == []


def test_quote_soft_hyphen_linebreak(instance):
    instance.quoted("The substi­\ntution rate is high.", claim("The substitution rate is high."))
    assert instance.run().errors == []


def test_quote_different_whitespace(instance):
    instance.quoted("alpha\n   beta\tgamma delta", claim("alpha beta gamma delta"))
    assert instance.run().errors == []


def test_quote_hyphenated_linebreak(instance):
    instance.quoted("The substi-\n  tution rate is high.", claim("The substitution rate is high."))
    assert instance.run().errors == []


def test_quote_absent_is_error(instance):
    stem = instance.quoted("Alpha beta.", claim("Gamma delta."))
    result = instance.run()
    assert f"[[{stem}#^c01]] quote not found in `originals/{stem}.txt`" in result.errors
    assert result.code == 1


def test_quote_absent_verified_manual(instance):
    stem = instance.quoted("Alpha beta.", '"Gamma delta." (confidence:: high) (verified:: manual)')
    result = instance.run()
    assert result.errors == []
    assert result.items("Quotes verified manually") == [f"- [[{stem}#^c01]] in `originals/{stem}.txt`"]


def test_quote_found_verified_manual_not_listed(instance):
    instance.quoted("Alpha beta.", '"Alpha beta." (confidence:: high) (verified:: manual)')
    result = instance.run()
    assert result.errors == []
    assert result.items("Quotes verified manually") == []


def test_quote_is_case_sensitive(instance):
    stem = instance.quoted("Alpha beta.", claim("alpha beta."))
    assert f"[[{stem}#^c01]] quote not found in `originals/{stem}.txt`" in instance.run().errors


# 3. Readers

HTML = """<!doctype html><html><head><title>T</title>
<style>p { color: red; }</style>
<script>var x = "secret phrase";</script>
</head><body><!-- hidden comment -->
<p>Price from 39&nbsp;&euro; per site</p><p>Next paragraph about R&amp;D.</p>
</body></html>"""


def test_html_entities_and_tags(instance):
    instance.quoted(HTML, [claim("Price from 39 € per site"), claim("per site Next paragraph about R&D.")], ext=".html")
    assert instance.run().errors == []


@pytest.mark.parametrize("text", ["secret phrase", "color: red", "hidden comment"])
def test_html_script_style_comments_ignored(instance, text):
    stem = instance.quoted(HTML, claim(text), ext=".html")
    assert f"[[{stem}#^c01]] quote not found in `originals/{stem}.html`" in instance.run().errors


def test_htm_extension(instance):
    instance.quoted(HTML, claim("Price from 39 € per site"), ext=".htm")
    assert instance.run().errors == []


def test_quote_across_strong_comma(instance):
    instance.quoted("<p>Price <strong>39 EUR</strong>, per site.</p>", claim("Price 39 EUR, per site."), ext=".html")
    assert instance.run().errors == []


def test_quote_across_paragraphs(instance):
    instance.quoted("<p>First paragraph.</p><p>Second paragraph.</p>",
                    claim("First paragraph. Second paragraph."), ext=".html")
    assert instance.run().errors == []


def test_quote_parenthesis_spacing(instance):
    instance.quoted("Total ( texto ) aquí.", claim("Total (texto) aquí."))
    assert instance.run().errors == []


def test_md_original(instance):
    instance.quoted("# Notes\n\nAlpha *beta* gamma.\n", claim("Alpha *beta* gamma."), ext=".md")
    assert instance.run().errors == []


def test_unsupported_extension_not_checked(instance):
    stem = instance.quoted(b"PK\x03\x04binary", claim("Alpha."), ext=".docx")
    result = instance.run()
    assert result.errors == []
    assert result.items("Quotes not checked automatically") == [
        f"- [[{stem}#^c01]] `originals/{stem}.docx`: unsupported extension"]


def test_source_without_original_quote_not_checked(instance):
    stem = instance.source(claims=[claim("Alpha."), DATA])
    result = instance.run()
    assert result.errors == []
    assert result.items("Quotes not checked automatically") == [f"- [[{stem}#^c01]]: no original"]


def pdf_source(instance, *claims):
    return instance.quoted((FIXTURES / "minimal.pdf").read_bytes(), list(claims), ext=".pdf")


@pytest.mark.pdf
def test_pdf_quote_found(instance):
    pdf_source(instance, claim("Hand-written fixture for the quote check."), claim("Second line of plain text."))
    result = instance.run()
    assert result.errors == []
    assert result.items("Quotes not checked automatically") == []


@pytest.mark.pdf
def test_pdf_quote_absent_is_error(instance):
    stem = pdf_source(instance, claim("Third line of plain text."))
    assert f"[[{stem}#^c01]] quote not found in `originals/{stem}.pdf`" in instance.run().errors


def test_pdf_without_pdftotext_not_checked(instance, monkeypatch):
    hide_pdftotext(monkeypatch)
    stem = pdf_source(instance, claim("Third line of plain text."))
    result = instance.run()
    assert result.errors == []
    assert result.items("Quotes not checked automatically") == [
        f"- [[{stem}#^c01]] `originals/{stem}.pdf`: pdftotext not installed"]


@pytest.mark.pdf
def test_pdftotext_failure_not_checked(instance):
    stem = instance.quoted(b"%PDF-1.4\nnot a pdf\n", claim("Alpha."), ext=".pdf")
    result = instance.run()
    assert result.errors == []
    [line] = result.items("Quotes not checked automatically")
    assert line.startswith(f"- [[{stem}#^c01]] `originals/{stem}.pdf`: pdftotext failed: ")


def test_missing_original_reports_one_error(instance):
    stem = instance.source(claims=[claim("Alpha."), claim("Beta.")], url="https://example.org/x",
                           original="originals/S-20261101-test.txt")
    assert instance.run().errors == [
        f"[[{stem}]] `original` points to `originals/S-20261101-test.txt`, which does not exist"]


# 4. Framework fields

def catalog_keys():
    keys = {}
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        if line.startswith("| `"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            keys[cells[0].strip("`")] = set(re.findall(r"`([^`]+)`", cells[2]))
    return keys


def test_framework_keys_match_catalog(trace):
    assert len(catalog_keys()) == 9
    assert {fw: set(k) for fw, k in trace.FRAMEWORK_KEYS.items()} == catalog_keys()


@pytest.mark.parametrize("framework, fields, missing", [
    ("porter", {"intensity": "high", "segment": "groups"}, "force"),
    ("jtbd", {"segment": "independents", "current_alternative": "spreadsheet"}, "job"),
])
def test_conclusion_missing_framework_key(instance, framework, fields, missing):
    stem = instance.source()
    instance.conclusion(f"C-{framework}-01", [f"[[{stem}#^c01]]"], framework=framework, **fields)
    assert (f"[[C-{framework}-01]] is missing the `{missing}` field (framework {framework})"
            in instance.run().errors)


def test_framework_keys_may_be_empty(instance):
    stem = instance.source()
    instance.conclusion("C-porter-01", [f"[[{stem}#^c01]]"], framework="porter",
                        force=None, intensity=None, segment="")
    assert instance.run().errors == []


def test_framework_not_in_catalog_unchecked(instance):
    stem = instance.source()
    instance.conclusion("C-custom-01", [f"[[{stem}#^c01]]"], framework="custom")
    assert instance.run().errors == []


def seven_powers(instance, benefit, barrier):
    stem = instance.source()
    instance.conclusion("C-seven_powers-01", [f"[[{stem}#^c01]]"], framework="seven_powers",
                        power="scale economies", benefit=benefit, barrier=barrier)


def test_seven_powers_empty_benefit(instance):
    seven_powers(instance, [], [])
    assert ("[[C-seven_powers-01]] has an empty `benefit`: a power needs a cited benefit"
            in instance.run().errors)


@pytest.mark.parametrize("field", ["benefit", "barrier"])
def test_seven_powers_broken_link(instance, field):
    links = {"benefit": ["[[S-20261101-test#^c01]]"], "barrier": []}
    links[field] = ["[[S-20261101-test#^c09]]"]
    seven_powers(instance, **links)
    assert ("[[C-seven_powers-01]] `%s` points to `S-20261101-test#c09`, which does not exist" % field
            in instance.run().errors)


def test_contradicted_benefit_claim_propagates(instance):
    instance.source("S-20261101-benefit")
    instance.source("S-20261102-rival", claims=[
        "DATA: 2 units, from another table. (confidence:: low) (contradicts:: [[S-20261101-benefit#^c01]])"])
    stem = instance.source()
    instance.conclusion("C-seven_powers-01", [f"[[{stem}#^c01]]"], framework="seven_powers",
                        power="scale economies", benefit=["[[S-20261101-benefit#^c01]]"], barrier=[])
    result = instance.run()
    assert result.errors == []
    assert any(r.startswith("| [[C-seven_powers-01]] | conclusion | [[S-20261101-benefit#^c01]] contradicted by")
               for r in result.section("Affected"))


# 5. Gaps

def gap(question="[[framing#^q01]]", origin="internal", priority=None):
    g = "Missing figure. Would change: the answer to q01."
    if question is not None:
        g += f" (question:: {question})"
    if origin is not None:
        g += f" (origin:: {origin})"
    if priority:
        g += f" (priority:: {priority})"
    return g


@pytest.mark.parametrize("origin", ORIGINS)
def test_valid_gap(instance, origin):
    instance.framing(gaps=[gap(origin=origin, priority="vital")])
    assert instance.run().errors == []


def test_gap_question_missing(instance):
    instance.framing(gaps=[gap(question=None)])
    assert "[[framing#^g01]] has no `question`" in instance.run().errors


def test_gap_question_dangling(instance):
    instance.framing(gaps=[gap(question="[[framing#^q09]]")])
    assert "[[framing#^g01]] `question` points to `framing#q09`, which does not exist" in instance.run().errors


def test_gap_origin_missing(instance):
    instance.framing(gaps=[gap(origin=None)])
    assert "[[framing#^g01]] has no `origin`" in instance.run().errors


def test_gap_origin_invalid(instance):
    instance.framing(gaps=[gap(origin="press")])
    assert ("[[framing#^g01]] `origin` is `press`: expected internal, customer, installer, purchase or manual"
            in instance.run().errors)


def test_gap_question_may_be_decision(instance):
    instance.decision("D-001-test")
    instance.framing(gaps=[gap(question="[[D-001-test]]", priority="vital")])
    result = instance.run()
    assert result.errors == []
    assert "| Vital gaps for [[D-001-test]] | 1 | 3 | 3 | ok |" in result.section("Budgets")


def test_q_blocks_are_not_gaps(instance):
    instance.framing(questions=["A question without gap fields? (status:: open)"])
    assert instance.run().errors == []


def vital_rows(result):
    return [r for r in result.section("Budgets") if r.startswith("| Vital gaps")]


def test_vital_gaps_budget_rows(instance):
    instance.framing(gaps=[
        gap(priority="vital"), gap(priority="vital"), gap(),
        gap(question="[[framing#^q02]]", priority="vital"),
        gap(question="[[framing#^q09]]", priority="vital"),
    ])
    assert vital_rows(instance.run()) == [
        "| Vital gaps for [[framing#^q01]] | 2 | 3 | 3 | ok |",
        "| Vital gaps for [[framing#^q02]] | 1 | 3 | 3 | ok |",
    ]


def test_vital_gaps_budget_override(instance):
    instance.config(budgets={"vital_gaps_per_question": [1, 2]})
    instance.framing(gaps=[gap(priority="vital"), gap(priority="vital")])
    result = instance.run()
    assert vital_rows(result) == ["| Vital gaps for [[framing#^q01]] | 2 | 1 | 2 | over soft limit |"]
    assert result.code == 0


def test_vital_gaps_over_hard_limit_exits_1(instance):
    instance.framing(gaps=[gap(priority="vital")] * 6)
    result = instance.run()
    assert vital_rows(result) == ["| Vital gaps for [[framing#^q01]] | 6 | 3 | 3 | OVER HARD LIMIT |"]
    assert result.errors == []
    assert result.code == 1


def test_gap_without_id(instance):
    text = "Share of independents that already pay for a shift tool, by region. (question:: [[framing#^q01]]) (origin:: purchase)"
    instance.framing(raw_gaps=[f"- {text}"])
    result = instance.run()
    assert f"`framing.md` has a gap without a `^gNN` id: {text[:60]}" in result.errors
    assert result.code == 1


@pytest.mark.parametrize("block_id", ["c01", "g1"])
def test_gap_with_wrong_id(instance, block_id):
    instance.framing(raw_gaps=[f"- {gap()} ^{block_id}"])
    assert f"`framing.md` has a gap without a `^gNN` id: {gap()[:60]}" in instance.run().errors


def test_indented_line_under_gaps_ignored(instance):
    instance.framing(gaps=[gap()], raw_gaps=["  - Note under the gap, without an id."])
    assert instance.run().errors == []


def test_three_vital_gaps_default_ok(instance):
    instance.framing(gaps=[gap(priority="vital")] * 3)
    result = instance.run()
    assert vital_rows(result) == ["| Vital gaps for [[framing#^q01]] | 3 | 3 | 3 | ok |"]
    assert result.errors == []
    assert result.code == 0


def test_four_vital_gaps_default_hard_limit(instance):
    instance.framing(gaps=[gap(priority="vital")] * 4)
    result = instance.run()
    assert vital_rows(result) == ["| Vital gaps for [[framing#^q01]] | 4 | 3 | 3 | OVER HARD LIMIT |"]
    assert result.errors == []
    assert result.code == 1


@pytest.mark.parametrize("config", [ROOT / "skills" / "init-instance" / "templates" / "strategy.config.yaml",
                                    ACME / "strategy.config.yaml"], ids=["template", "acme"])
def test_config_budgets_match_defaults(trace, config):
    # The template has {{placeholders}} that are not valid YAML.
    text = re.sub(r"\{\{\w+\}\}", "x", config.read_text(encoding="utf-8"))
    assert yaml.safe_load(text)["budgets"] == trace.DEFAULT_BUDGETS


# 4. Quoted fragments in DATA lines

def data_fragment(fragment, extra=""):
    return f"DATA: panel wording {fragment}, from the minutes. (confidence:: medium){extra}"


def test_data_fragment_found(instance):
    instance.quoted("The panel said alpha beta gamma today.", data_fragment('"alpha beta gamma"'))
    assert instance.run().errors == []


def test_data_fragment_absent(instance):
    stem = instance.quoted("The panel said alpha beta gamma today.", data_fragment('"delta epsilon zeta"'))
    result = instance.run()
    assert f"[[{stem}#^c01]] quoted fragment not found in `originals/{stem}.txt`" in result.errors
    assert result.code == 1


def test_data_fragment_two_words_not_checked(instance):
    instance.quoted("The panel said alpha beta gamma today.", data_fragment('"delta epsilon"'))
    assert instance.run().errors == []


def test_data_fragment_absent_verified_manual(instance):
    stem = instance.quoted("The panel said alpha beta gamma today.",
                           data_fragment('"delta epsilon zeta"', " (verified:: manual)"))
    result = instance.run()
    assert result.errors == []
    assert result.items("Quotes verified manually") == [f"- [[{stem}#^c01]] in `originals/{stem}.txt`"]


@pytest.mark.parametrize("fragment", ['"delta epsilon zeta"', "“delta epsilon zeta”", "«delta epsilon zeta»"])
def test_data_fragment_quote_styles(instance, fragment):
    stem = instance.quoted("The panel said alpha beta gamma today.", data_fragment(fragment))
    assert f"[[{stem}#^c01]] quoted fragment not found in `originals/{stem}.txt`" in instance.run().errors


def test_data_several_absent_fragments_one_error(instance):
    stem = instance.quoted("The panel said alpha beta gamma today.",
                           data_fragment('"delta epsilon zeta" and "eta theta iota"'))
    assert instance.run().errors == [f"[[{stem}#^c01]] quoted fragment not found in `originals/{stem}.txt`"]


def test_data_fragment_inside_field_ignored(instance):
    instance.quoted("The panel said alpha beta gamma today.",
                    'DATA: counted from the minutes. (confidence:: medium) (locator:: "delta epsilon zeta")')
    assert instance.run().errors == []


def test_data_fragment_no_original(instance):
    stem = instance.source(claims=[data_fragment('"delta epsilon zeta"')])
    result = instance.run()
    assert result.errors == []
    assert result.items("Quotes not checked automatically") == [f"- [[{stem}#^c01]]: no original"]


def test_data_fragment_pdf_without_pdftotext(instance, monkeypatch):
    hide_pdftotext(monkeypatch)
    stem = pdf_source(instance, data_fragment('"delta epsilon zeta"'))
    result = instance.run()
    assert result.errors == []
    assert result.items("Quotes not checked automatically") == [
        f"- [[{stem}#^c01]] `originals/{stem}.pdf`: pdftotext not installed"]


# 5. Quotes cut before a condition

TAIL = "the venue signs for two full years at the listed price and pays upfront every month in advance. End."
MARKERS = [", en cuyo caso", ", siempre que", ", excepto", ", salvo", ", cuando", ", a condición de",
           ", in which case", ", provided that", ", except", ", unless", ", when"]


def cut_line(stem, words, ext=".txt"):
    return f'- [[{stem}#^c01]] in `originals/{stem}{ext}`: "{" ".join(words.split()[:15])}"'


@pytest.mark.parametrize("marker", MARKERS)
def test_quote_cut_before_condition(instance, marker):
    stem = instance.quoted(f"Intro. The fee is waived{marker} {TAIL}", claim("The fee is waived"))
    result = instance.run()
    assert result.errors == []
    assert result.code == 0
    assert result.items(CUT) == [cut_line(stem, f"{marker[2:]} {TAIL}")]


def test_quote_followed_by_period_not_listed(instance):
    instance.quoted(f"Intro. The fee is waived. {TAIL}", claim("The fee is waived"))
    assert instance.run().section(CUT) == ["None."]


def test_quote_ending_in_comma_before_condition(instance):
    stem = instance.quoted(f"Intro. The fee is waived, en cuyo caso {TAIL}", claim("The fee is waived,"))
    assert instance.run().items(CUT) == [cut_line(stem, f"en cuyo caso {TAIL}")]


def test_quote_cut_fewer_than_15_words(instance):
    stem = instance.quoted("The fee is waived, unless the venue cancels.", claim("The fee is waived"))
    assert instance.run().items(CUT) == [cut_line(stem, "unless the venue cancels.")]


def test_data_fragment_cut_before_condition(instance):
    stem = instance.quoted(f"Terms: the fee is waived, salvo {TAIL}",
                           'DATA: terms say "the fee is waived", from the contract page. (confidence:: high)')
    result = instance.run()
    assert result.errors == []
    assert result.items(CUT) == [cut_line(stem, f"salvo {TAIL}")]


# 6. DATA values

def values_line(stem, numbers, ext=".txt"):
    return f"- [[{stem}#^c01]] in `originals/{stem}{ext}`: {numbers}"


def test_data_value_present(instance):
    instance.quoted("Sales were 1,240 units.", "DATA: 1,240 units, from the sales table. (confidence:: medium)")
    assert instance.run().section(VALUES) == ["None."]


def test_data_value_absent(instance):
    stem = instance.quoted("Table 3: 140 north, 240 south.",
                           "DATA: 140 + 240 = 380 units, summed from table 3. (confidence:: medium)")
    result = instance.run()
    assert result.errors == []
    assert result.code == 0
    assert result.items(VALUES) == [values_line(stem, "380")]


def test_data_iso_date_not_counted(instance):
    instance.quoted("Sales were 1,240 units.",
                    "DATA: 1,240 units as of 2026-10-30, from the sales table. (confidence:: medium)")
    assert instance.run().section(VALUES) == ["None."]


def test_data_value_bounded(instance):
    stem = instance.quoted("Sales were 1,240 units in table 3.",
                           "DATA: 240 units, from table 3. (confidence:: medium)")
    assert instance.run().items(VALUES) == [values_line(stem, "240")]


def test_data_locator_numbers_ignored(instance):
    instance.quoted("Sales were 1,240 units.",
                    "DATA: 1,240 units, from the sales table. (confidence:: medium) (locator:: p. 4, table 7)")
    assert instance.run().section(VALUES) == ["None."]


def test_data_values_unreadable_original(instance, monkeypatch):
    hide_pdftotext(monkeypatch)
    stem = pdf_source(instance, 'DATA: 380 units, worded "delta epsilon zeta" in the minutes. (confidence:: medium)')
    result = instance.run()
    assert result.items("Quotes not checked automatically") == [
        f"- [[{stem}#^c01]] `originals/{stem}.pdf`: pdftotext not installed"]
    assert result.section(VALUES) == ["None."]


def test_data_values_no_original_skipped(instance):
    instance.source(claims=["DATA: 380 units, from interview notes. (confidence:: low)"])
    result = instance.run()
    assert result.section(VALUES) == ["None."]
    assert result.section("Quotes not checked automatically") == ["None."]


# 7. benefit and against

def test_claim_in_benefit_and_against(instance):
    stem = instance.source()
    link = f"[[{stem}#^c01]]"
    instance.conclusion("C-seven_powers-01", [link], framework="seven_powers", power="scale economies",
                        benefit=[link], barrier=[], against=[link])
    result = instance.run()
    assert f"[[C-seven_powers-01]] {link} is both in `benefit` and in `against`" in result.errors
    assert result.code == 1


def test_claim_only_in_benefit(instance):
    stem = instance.source()
    link = f"[[{stem}#^c01]]"
    instance.conclusion("C-seven_powers-01", [link], framework="seven_powers", power="scale economies",
                        benefit=[link], barrier=[])
    assert instance.run().errors == []


# 8. Unused claims and relations

def test_unused_claims_grouped(instance):
    stem = instance.source(claims=[DATA, DATA, DATA])
    instance.source("S-20261102-other")
    instance.conclusion("C-custom-01", [f"[[{stem}#^c01]]"])
    assert instance.run().items(UNUSED) == [f"- [[{stem}]]: ^c02, ^c03", "- [[S-20261102-other]]: ^c01"]


def test_claim_used_only_in_against_not_unused(instance):
    stem = instance.source(claims=[DATA, DATA])
    instance.conclusion("C-custom-01", [f"[[{stem}#^c01]]"], against=[f"[[{stem}#^c02]]"])
    assert instance.run().section(UNUSED) == ["None."]


def test_claim_used_by_archived_conclusion_not_unused(instance):
    stem = instance.source()
    instance.conclusion("C-custom-01", [f"[[{stem}#^c01]]"], status="archived")
    assert instance.run().section(UNUSED) == ["None."]


def test_whole_source_link_does_not_use_claims(instance):
    stem = instance.source()
    instance.conclusion("C-custom-01", [f"[[{stem}]]"])
    assert instance.run().items(UNUSED) == [f"- [[{stem}]]: ^c01"]


@pytest.mark.parametrize("field", ["confirms", "contradicts"])
def test_relation_dangling(instance, field):
    stem = instance.source(claims=[f"{DATA} ({field}:: [[S-20261101-test#^c09]])"])
    result = instance.run()
    assert f"[[{stem}#^c01]] `{field}` points to `S-20261101-test#c09`, which does not exist" in result.errors
    assert result.code == 1


def test_relations_count_in_header(instance):
    instance.source("S-20261101-a")
    instance.source("S-20261102-b")
    instance.source("S-20261103-c", claims=[
        f"{DATA} (contradicts:: [[S-20261101-a#^c01]], [[S-20261102-b#^c01]])",
        f"{DATA} (confirms:: [[S-20261101-a#^c01]])",
        f"{DATA} (confirms:: [[S-20261102-b#^c01]])",
    ])
    result = instance.run()
    assert result.errors == []
    assert "Relations marked: 2 confirms, 2 contradicts." in result.report.splitlines()


# Report and general behaviour

def test_report_sections_order_and_empty(instance):
    stem = instance.source()
    result = instance.run()
    assert result.headings == ["Validation", "Quotes verified manually", "Quotes not checked automatically",
                               CUT, VALUES, "Affected", "Budgets", "Reviews due", "Archive candidates", UNUSED]
    assert result.section("Quotes verified manually") == ["None."]
    assert result.section("Quotes not checked automatically") == ["None."]
    assert result.section(CUT) == ["None."]
    assert result.section(VALUES) == ["None."]
    assert result.items(UNUSED) == [f"- [[{stem}]]: ^c01"]
    lines = result.report.splitlines()
    assert lines.index("Relations marked: 0 confirms, 0 contradicts.") < lines.index("## Validation")


def test_exit_code_on_quote_error(instance):
    instance.quoted("Alpha beta.", claim("Alpha beta."))
    assert instance.run().code == 0
    instance.quoted("Alpha beta.", claim("Gamma."))
    assert instance.run().code == 1


def tree_hashes(root):
    return {p.relative_to(root): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and "reports" not in p.relative_to(root).parts}


def test_changes_nothing_but_report(instance):
    instance.quoted(HTML, claim("Gamma."), ext=".html")
    instance.original("S-20261101-lost.pdf", b"%PDF-1.4\n")
    instance.framing(gaps=[gap(origin="press")])
    before = tree_hashes(instance.root)
    instance.run()
    assert tree_hashes(instance.root) == before
    assert [p.name for p in (instance.root / "reports").iterdir()] == ["impact-20261115.md"]


# acme

ACME_ALERTS = [
    "[[H-002-gap-cover-usage]] past its deadline (2026-10-31) and not reviewed",
    "source [[S-20260512-trade-barometer]] expired on 2026-11-12",
    "[[S-20260512-trade-barometer#^c01]] contradicted by [[S-20261110-meridian-report#^c01]]",
]


@pytest.fixture
def acme(tmp_path, trace, monkeypatch):
    root = tmp_path / "acme"
    shutil.copytree(ACME, root, ignore=shutil.ignore_patterns("impact-*.md", ".venv", "__pycache__"))
    return Instance(root, trace, monkeypatch, scaffold=False)


def assert_acme_alerts(result):
    assert result.errors == []
    assert result.code == 0
    affected = result.section("Affected")
    for item in ["D-001-prioritise-independents", "direction", "OKR-2027"]:
        for reason in ACME_ALERTS:
            assert any(r.startswith(f"| [[{item}]] |") and f"| {reason} |" in r for r in affected), (item, reason)
    assert "- [[S-20260301-hotel-survey]] (source), review was due 2026-09-01" in result.items("Archive candidates")
    assert "| Vital gaps for [[framing#^q01]] | 1 | 3 | 3 | ok |" in result.section("Budgets")
    assert result.section(CUT) == ["None."]
    assert result.section(VALUES) == ["None."]
    assert result.items(UNUSED) == ["- [[S-20260301-hotel-survey]]: ^c01"]
    assert "Relations marked: 0 confirms, 1 contradicts." in result.report.splitlines()


@pytest.mark.pdf
def test_acme_clean_run(acme):
    result = acme.run()
    assert_acme_alerts(result)
    assert result.items("Quotes not checked automatically") == ["- [[S-20260301-hotel-survey#^c01]]: no original"]
    assert result.section("Quotes verified manually") == ["None."]


def test_acme_without_pdftotext(acme, monkeypatch):
    hide_pdftotext(monkeypatch)
    result = acme.run()
    assert_acme_alerts(result)
    assert result.items("Quotes not checked automatically") == [
        "- [[S-20260301-hotel-survey#^c01]]: no original",
        "- [[S-20260512-trade-barometer#^c01]] `originals/S-20260512-trade-barometer.pdf`: pdftotext not installed",
        "- [[S-20261110-meridian-report#^c01]] `originals/S-20261110-meridian-report.pdf`: pdftotext not installed",
    ]
