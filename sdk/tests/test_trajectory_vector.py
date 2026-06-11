import json
import os

from air_blackbox.trajectory import Step, commit_root, leaf_hex

VECTOR = os.path.join(os.path.dirname(__file__), "..", "..",
                      "pkg", "trajectory", "testdata", "canonical_vector.json")


def test_python_matches_cross_language_vector():
    with open(VECTOR) as f:
        vec = json.load(f)
    steps = [
        Step(step_id=s["step_id"], kind=s["kind"],
             input_hash=s.get("input_hash", ""), output_hash=s.get("output_hash", ""),
             gate_verdict=s.get("gate_verdict", "n/a"), timestamp=s.get("timestamp", ""),
             parent_ids=s.get("parent_ids") or [])
        for s in vec["steps"]
    ]
    # Per-leaf agreement localizes any drift to a specific step.
    for s, expected in zip(steps, vec["leaf_hashes"]):
        assert leaf_hex(s) == expected, f"leaf mismatch at {s.step_id}"
    # Root agreement is the cross-language contract.
    assert commit_root(steps) == vec["expected_root"]
