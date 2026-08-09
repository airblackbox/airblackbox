"""Non-EU findings must never be presented as EU AI Act articles.

Three defects motivated this file, all in the path between a scanner finding
and the document a regulator reads:

1. `CodeFinding.article` was an int with no room for anything but an EU AI Act
   article, so Illinois HB 3773, NYC LL144 and California FEHA findings were
   filed under `article=16`. EU AI Act Article 16 is "obligations of providers
   of high-risk AI systems" and has nothing to do with any of them.

2. `pdf_report` read a `"article"` key the compliance engine never emits (it
   emits `"number"`), so every section heading in the exported PDF rendered as
   a bare "Article " - and once the key was corrected it would have printed
   "Article 16" over the NYC bias-audit findings.

3. The CLI dropped every group whose number was not in a hardcoded map of six
   EU articles, so the model doing deep analysis never saw a single US state
   law, GDPR or bias finding.

An article number in a compliance report is a legal claim about which
obligation a finding maps to. Attaching the wrong one is worse than attaching
none.
"""

import ast
import pathlib
import textwrap

import pytest

from air_blackbox.compliance.code_scanner import (
    FRAMEWORK_EU_AI_ACT,
    FRAMEWORK_US_HIRING,
    scan_codebase,
)
from air_blackbox.export.pdf_report import LABELS, section_heading

REPO = pathlib.Path(__file__).resolve().parents[1]
CLI = REPO / "sdk" / "air_blackbox" / "cli.py"

#: Enough hiring signal to trip _has_hiring_context, plus a ZIP reference in
#: scoring context so the Illinois check has something to find.
HIRING_FIXTURE = textwrap.dedent('''
    """Candidate screening for job applicants."""

    def score_resume(candidate, job_posting):
        """Rank an applicant for this requisition."""
        zip_code = candidate["postal_code"]
        return rank_candidate(zip_code, job_posting)
''')


@pytest.fixture
def hiring_findings(tmp_path):
    (tmp_path / "screening.py").write_text(HIRING_FIXTURE, encoding="utf-8")
    findings = scan_codebase(str(tmp_path))
    hiring = [f for f in findings if f.framework == FRAMEWORK_US_HIRING]
    assert hiring, (
        "Fixture did not trigger the US hiring checks, so this module is "
        "asserting nothing. Check _has_hiring_context patterns.")
    return findings, hiring


def test_us_hiring_findings_carry_no_eu_article(hiring_findings):
    """The bug at its source: a state-law finding with an EU article number."""
    _, hiring = hiring_findings
    numbered = [f for f in hiring if f.article is not None]
    assert not numbered, (
        "US hiring findings carry an EU AI Act article number: "
        f"{[(f.name, f.article) for f in numbered]}. They belong to Illinois "
        "HB 3773 / NYC LL144 / California FEHA and have no EU article.")


def test_eu_findings_still_carry_an_article(hiring_findings):
    """The separation must not have cost the EU findings their numbers."""
    findings, _ = hiring_findings
    eu = [f for f in findings if f.framework == FRAMEWORK_EU_AI_ACT]
    assert eu, "No EU AI Act findings produced at all"
    unnumbered = [f.name for f in eu if f.article is None]
    assert not unnumbered, (
        f"EU AI Act findings with no article number: {unnumbered}")


@pytest.mark.parametrize("number,title,expected", [
    (9, "Risk Management", "Article 9 - Risk Management"),
    (12, "Record-Keeping", "Article 12 - Record-Keeping"),
])
def test_eu_groups_render_their_official_article_name(number, title, expected):
    assert section_heading({"number": number, "title": title}) == expected


@pytest.mark.parametrize("number,title", [
    ("US-HIRING", "US Hiring AI Laws (context-specific)"),
    ("IL", "Illinois HB 3773 (AI Employment)"),
    ("CA", "California AI Laws (FEHA ADS + SB 942 + ADMT)"),
    ("GDPR", "GDPR Data Protection"),
    ("BIAS", "Bias and Fairness"),
])
def test_non_eu_groups_are_never_labelled_as_articles(number, title):
    """A string-keyed group must render its own title, never "Article X"."""
    heading = section_heading({"number": number, "title": title})
    assert heading == title
    assert "Article" not in heading, (
        f"Group {number!r} rendered as {heading!r} in the exported report. "
        "That asserts an EU AI Act obligation this finding was never mapped "
        "to.")


def test_heading_never_renders_an_empty_article():
    """The original defect: a wrong key left every heading as "Article "."""
    group = {"number": 9, "title": "Risk Management", "checks": []}
    heading = section_heading(group)
    assert heading.strip() != "Article", (
        "section_heading produced a bare 'Article' - it is reading a key the "
        "compliance engine does not emit.")
    assert heading == LABELS[9]


def test_unlabelled_eu_article_still_names_itself():
    """A new article with no LABELS entry must not degrade to a bare number."""
    assert section_heading({"number": 13, "title": "Transparency"}) == (
        "Article 13 - Transparency")


def test_every_real_engine_group_renders_a_correct_heading(tmp_path):
    """End to end: the engine's own output through the report renderer.

    This is the assertion that would have caught all of it. Before the fix
    every one of these twelve groups rendered as a bare "Article ".
    """
    from air_blackbox.compliance.engine import run_all_checks
    from air_blackbox.gateway_client import GatewayStatus

    (tmp_path / "screening.py").write_text(HIRING_FIXTURE, encoding="utf-8")
    groups, _, _, _ = run_all_checks(GatewayStatus(), str(tmp_path), "all")
    assert groups, "Engine produced no compliance groups"

    numbers = {g.get("number") for g in groups}
    assert "US-HIRING" in numbers, (
        "The hiring group is missing or still keyed by an integer. It must "
        f"not share the EU article namespace. Got: {sorted(map(str, numbers))}")
    assert 16 not in numbers, "US hiring law is being numbered as EU Article 16"

    for group in groups:
        heading = section_heading(group)
        assert heading.strip() not in ("", "Article"), (
            f"Group {group.get('number')!r} rendered as {heading!r}")
        if not isinstance(group.get("number"), int):
            assert "Article" not in heading, (
                f"Non-EU group {group.get('number')!r} rendered as {heading!r}")


def test_cli_does_not_discard_non_eu_groups():
    """Guard the CLI skip that hid state law and GDPR from the model.

    Asserted on the source because the loop is embedded in a large command
    function with no seam to call. A structural check is worth more here than
    no check: the exact `continue` that caused the bug cannot come back.
    """
    tree = ast.parse(CLI.read_text(encoding="utf-8"), str(CLI))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not isinstance(node.ops[0], ast.NotIn):
            continue
        right = node.comparators[0]
        if isinstance(right, ast.Name) and right.id == "article_map":
            parent_is_skip = any(
                isinstance(n, ast.If) and n.test is node
                and any(isinstance(b, ast.Continue) for b in n.body)
                for n in ast.walk(tree))
            assert not parent_is_skip, (
                "cli.py skips groups missing from article_map again. That "
                "hides every US state law, GDPR and bias finding from the "
                "model; label them by title instead of dropping them.")
