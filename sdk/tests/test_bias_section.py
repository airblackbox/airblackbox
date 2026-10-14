"""The Bias and Fairness section of `comply`.

It used to be fed the scan path directly: a directory raised and was swallowed
(section never shown), and a single file crashed the whole run.
"""

from air_blackbox.compliance.engine import run_all_checks
from air_blackbox.gateway_client import GatewayStatus

SCREENER = '''
def screen(candidate):
    """Score a job applicant's resume for the hiring pipeline."""
    if candidate["gender"] == "female":
        pass
    threshold = 0.7
    return candidate["score"] > threshold
'''

NOT_ABOUT_PEOPLE = '''
def render(console):
    """Draw a progress bar."""
    console.print("done", style="white on black")
'''


def _bias(results):
    return [a for a in results if a.get("number") == "BIAS"]


def test_single_file_scan_does_not_crash(tmp_path):
    f = tmp_path / "screener.py"
    f.write_text(SCREENER)
    results, *_ = run_all_checks(GatewayStatus(), str(f), standard="all")
    (section,) = _bias(results)
    assert {c["name"] for c in section["checks"]} >= {
        "Protected attribute references",
        "Decision thresholds without fairness validation",
    }


def test_directory_scan_shows_the_section(tmp_path):
    (tmp_path / "screener.py").write_text(SCREENER)
    results, *_ = run_all_checks(GatewayStatus(), str(tmp_path), standard="eu")
    (section,) = _bias(results)
    for check in section["checks"]:
        assert check["status"] == "warn"
        assert "screener.py" in check["evidence"]


def test_test_files_are_not_counted(tmp_path):
    (tmp_path / "screener.py").write_text(SCREENER.replace('"gender"', '"x"')
                                          .replace('"female"', '"y"'))
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_screener.py").write_text('race = "asian"\ngender = "male"\n')
    results, *_ = run_all_checks(GatewayStatus(), str(tmp_path), standard="all")
    names = {c["name"] for a in _bias(results) for c in a["checks"]}
    assert "Gender term references" not in names
    assert "Race/ethnicity term references" not in names


def test_code_that_decides_nothing_about_people_gets_no_section(tmp_path):
    (tmp_path / "ui.py").write_text(NOT_ABOUT_PEOPLE)
    results, *_ = run_all_checks(GatewayStatus(), str(tmp_path), standard="all")
    assert _bias(results) == []
