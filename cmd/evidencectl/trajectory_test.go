package main

import (
	"testing"

	"github.com/airblackbox/gateway/pkg/trust"
)

func sampleSummary() trajectorySummary {
	return trajectorySummary{
		TrajectoryID: "run-test",
		RootGoalHash: "abcd",
		StepRoot:     "3003d4aaab5cda77114f0bc1764265d72fe7dff3d323f45978aeceb9aba83a39",
		StepCount:    3,
		Outcome:      "blocked",
	}
}

// buildBundle reproduces what runAnchorTrajectory does, with ephemeral keys.
func buildBundle(t *testing.T, sum trajectorySummary) anchorBundle {
	t.Helper()
	dir := t.TempDir()
	chain := trust.NewAuditChain("test-secret")
	entry := chain.Append(sum.TrajectoryID, canonicalSummaryRecord(sum))
	mldsa, err := trust.NewSigner(dir)
	if err != nil {
		t.Fatalf("mldsa signer: %v", err)
	}
	ed, err := trust.NewSignerEd25519(dir)
	if err != nil {
		t.Fatalf("ed signer: %v", err)
	}
	sc, err := trust.CreateCheckpoint(chain, mldsa, ed)
	if err != nil {
		t.Fatalf("checkpoint: %v", err)
	}
	return anchorBundle{Trajectory: sum, ChainEntry: entry, SignedCheckpoint: sc}
}

func TestAnchorVerifyRoundTrip(t *testing.T) {
	b := buildBundle(t, sampleSummary())
	if err := verifyBundle(b); err != nil {
		t.Fatalf("freshly anchored bundle should verify, got: %v", err)
	}
}

func TestVerifyDetectsTamperedStepRoot(t *testing.T) {
	b := buildBundle(t, sampleSummary())
	// Swap the step root after anchoring: the canonical record no longer
	// hashes to the entry's RecordHash, so verification must fail.
	b.Trajectory.StepRoot = "0000000000000000000000000000000000000000000000000000000000000000"
	if err := verifyBundle(b); err == nil {
		t.Fatal("verification accepted a tampered step root")
	}
}

func TestVerifyDetectsTamperedEntry(t *testing.T) {
	b := buildBundle(t, sampleSummary())
	// Mutate the entry's record hash: it no longer hashes to the checkpoint head.
	b.ChainEntry.RecordHash = "deadbeef"
	if err := verifyBundle(b); err == nil {
		t.Fatal("verification accepted a tampered chain entry")
	}
}

func TestCanonicalSummaryRecordDeterministic(t *testing.T) {
	s := sampleSummary()
	if string(canonicalSummaryRecord(s)) != string(canonicalSummaryRecord(s)) {
		t.Fatal("canonical record not deterministic")
	}
}
