"""The README's EU AI Act article claim must match the checks that exist.

This file exists because the README claimed coverage of Article 13
(transparency) that no check ever implemented. Nothing detected it: the claim
lived in prose, the checks lived in code, and the two drifted for months in a
sentence a regulator would read first.

Editing the number out fixes today. This fixes the next one, in both
directions: an article claimed with no check behind it fails here, and so does
a new check whose article never makes it into the docs. Overclaiming coverage
of a compliance obligation is the more serious failure, but silently
undershipping the docs is how the first one gets reintroduced.

Articles are read out of the source with `ast`, not a regex, because the word
"Article" appears throughout docstrings and evidence strings. Only the value
literally passed as `article=` to a finding constructor counts as a claim that
a check exists.
"""

import ast
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
README = REPO / "README.md"
COMPLIANCE = REPO / "sdk" / "air_blackbox" / "compliance"
PDF_REPORT = REPO / "sdk" / "air_blackbox" / "export" / "pdf_report.py"

#: Modules whose findings are EU AI Act findings. Deliberately not a glob over
#: compliance/: gdpr_scanner.py numbers its findings by GDPR article and
#: us_scanner.py builds USFinding for state law. All three regulations say
#: "article" and mean different documents.
EU_AI_ACT_SOURCES = ("code_scanner.py", "engine.py")

#: Values passed as article= that are not EU AI Act article numbers.
#:   0  - sentinel for "no Python files found", emitted before any check runs.
#:   16 - overflow bucket for US hiring law (Illinois HB 3773, NYC LL144,
#:        California FEHA). CodeFinding.article is an int, so these were filed
#:        under a spare number rather than given their own field; engine.py
#:        retitles the group "US Hiring AI Laws (context-specific)". EU AI Act
#:        Article 16 is provider obligations and is genuinely uncovered.
#: If either stops being a bucket and becomes a real article, this test fails
#: and the exclusion has to be justified again rather than inherited.
NON_ARTICLE_BUCKETS = frozenset({0, 16})

FINDING_FACTORIES = frozenset({"CodeFinding", "ComplianceCheck"})


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    return getattr(func, "attr", "") or ""


def declared_articles() -> set:
    """Every article number a finding constructor is actually called with."""
    found = set()
    for filename in EU_AI_ACT_SOURCES:
        path = COMPLIANCE / filename
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _call_name(node) not in FINDING_FACTORIES:
                continue
            for kw in node.keywords:
                if kw.arg != "article":
                    continue
                if not isinstance(kw.value, ast.Constant):
                    pytest.fail(
                        f"{filename}: article= is computed, not a literal. "
                        "This test can no longer see what is covered; give "
                        "the module an explicit article registry instead.")
                found.add(kw.value.value)
    return found


def claimed_articles() -> set:
    """The article numbers the README advertises to a reader."""
    text = README.read_text(encoding="utf-8")
    match = re.search(
        r"EU AI Act gap analysis\*\*:.*?across Articles ([\d,\s]+?)\.",
        text)
    assert match, (
        "Could not find the 'EU AI Act gap analysis' coverage sentence in "
        "README.md. If it was reworded, update this pattern - do not delete "
        "the test.")
    return {int(n) for n in re.findall(r"\d+", match.group(1))}


def pdf_report_labels() -> set:
    """Articles the regulator-facing PDF knows how to title."""
    tree = ast.parse(PDF_REPORT.read_text(encoding="utf-8"), str(PDF_REPORT))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "LABELS" not in targets or not isinstance(node.value, ast.Dict):
            continue
        return {k.value for k in node.value.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, int)}
    pytest.fail("LABELS dict not found in pdf_report.py")


def test_readme_claims_no_article_without_a_check():
    """An advertised article with nothing behind it is a false claim."""
    overclaimed = claimed_articles() - (declared_articles() - NON_ARTICLE_BUCKETS)
    assert not overclaimed, (
        f"README.md advertises EU AI Act Article(s) {sorted(overclaimed)}, but "
        f"no check in {', '.join(EU_AI_ACT_SOURCES)} declares them. Either "
        "implement the check or stop claiming the coverage.")


def test_readme_claims_every_article_that_has_a_check():
    """Shipping a check the docs never mention is how drift restarts."""
    unclaimed = (declared_articles() - NON_ARTICLE_BUCKETS) - claimed_articles()
    assert not unclaimed, (
        f"Checks declare EU AI Act Article(s) {sorted(unclaimed)} that the "
        "README coverage sentence omits. Add them to README.md.")


def test_non_article_buckets_are_still_buckets():
    """Guard the exclusions above so they cannot be inherited silently."""
    stale = NON_ARTICLE_BUCKETS - declared_articles()
    assert not stale, (
        f"{sorted(stale)} is excluded as a non-article bucket but no longer "
        "appears in the scanners. Remove it from NON_ARTICLE_BUCKETS so the "
        "exclusion list stays honest.")


def test_pdf_report_titles_match_the_readme_claim():
    """The PDF an auditor receives must not disagree with the README."""
    assert pdf_report_labels() == claimed_articles(), (
        f"pdf_report.LABELS covers {sorted(pdf_report_labels())} but README.md "
        f"claims {sorted(claimed_articles())}. An article with no LABELS entry "
        "falls back to a bare 'Article N' heading in the exported report.")
