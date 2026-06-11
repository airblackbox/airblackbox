package trajectory

import (
	"encoding/json"
	"os"
	"testing"
)

// TestCanonicalVector asserts the package reproduces the frozen cross-language
// test vector in testdata/canonical_vector.json. The same vector is checked by
// the Python implementation (sdk/air_blackbox/trajectory.py), so if both pass,
// Go and Python commit byte-identical roots and the Go anchoring stack can sign
// what Tombstone's Python capture produced. Do not edit the vector to make a
// changed encoding pass; bump canonicalStepVersion instead.
func TestCanonicalVector(t *testing.T) {
	raw, err := os.ReadFile("testdata/canonical_vector.json")
	if err != nil {
		t.Fatalf("read vector: %v", err)
	}
	var vec struct {
		Steps        []Step   `json:"steps"`
		LeafHashes   []string `json:"leaf_hashes"`
		ExpectedRoot string   `json:"expected_root"`
		TrajectoryID string   `json:"trajectory_id"`
		RootGoalHash string   `json:"root_goal_hash"`
	}
	if err := json.Unmarshal(raw, &vec); err != nil {
		t.Fatalf("parse vector: %v", err)
	}

	b := NewBuilder(vec.TrajectoryID, vec.RootGoalHash)
	for _, s := range vec.Steps {
		if err := b.Add(s); err != nil {
			t.Fatalf("add %s: %v", s.StepID, err)
		}
	}
	tr, err := b.Commit(OutcomeCompleted)
	if err != nil {
		t.Fatalf("commit: %v", err)
	}
	if tr.StepRoot != vec.ExpectedRoot {
		t.Fatalf("root mismatch:\n got  %s\n want %s", tr.StepRoot, vec.ExpectedRoot)
	}

	// Per-leaf check, so a drift localizes to a step rather than just the root.
	for i, s := range vec.Steps {
		got := hexLeaf(s)
		if got != vec.LeafHashes[i] {
			t.Fatalf("leaf %d (%s) mismatch:\n got  %s\n want %s",
				i, s.StepID, got, vec.LeafHashes[i])
		}
	}
}
