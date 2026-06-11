package trajectory_test

import (
	"crypto/sha256"
	"encoding/hex"
	"testing"

	"github.com/airblackbox/gateway/pkg/trajectory"
	"github.com/airblackbox/gateway/pkg/trust"
)

// TestTrajectoryRidesExistingChain proves the backward-compatible claim in the
// spec: a committed trajectory's summary hash appends to the unmodified
// AuditChain, and the chain still verifies. The chain commits one entry per
// agent run instead of one per call, with no chain code changes.
func TestTrajectoryRidesExistingChain(t *testing.T) {
	// Build a small agent run: an LLM call, a tool call it requested (gate
	// permitted), and an action (gate forbade), then a final answer.
	b := trajectory.NewBuilder("run-42", sha256Hex("summarize the inbox and archive spam"))
	mustAdd(t, b, trajectory.Step{StepID: "s1", Kind: trajectory.KindLLMCall,
		InputHash: "h-prompt", OutputHash: "h-plan", GateVerdict: trajectory.VerdictNA,
		TimestampUTC: "2026-06-10T00:00:00Z"})
	mustAdd(t, b, trajectory.Step{StepID: "s2", ParentIDs: []string{"s1"},
		Kind: trajectory.KindToolCall, InputHash: "h-search", OutputHash: "h-results",
		GateVerdict: trajectory.VerdictPermit, TimestampUTC: "2026-06-10T00:00:01Z"})
	mustAdd(t, b, trajectory.Step{StepID: "s3", ParentIDs: []string{"s2"},
		Kind: trajectory.KindAction, InputHash: "h-archive-all", OutputHash: "",
		GateVerdict: trajectory.VerdictForbid, TimestampUTC: "2026-06-10T00:00:02Z"})

	tr, err := b.Commit(trajectory.OutcomeBlocked)
	if err != nil {
		t.Fatalf("commit: %v", err)
	}

	// Append the trajectory summary to the EXISTING chain, unchanged.
	chain := trust.NewAuditChain("secret-key")
	entry := chain.Append(tr.TrajectoryID, tr.CanonicalSummary())

	// The chain entry's record hash is the hash of the trajectory summary,
	// which transitively commits the Merkle step root.
	wantHash := sha256Hex2(tr.CanonicalSummary())
	if entry.RecordHash != wantHash {
		t.Fatalf("chain entry does not commit trajectory summary: %s vs %s",
			entry.RecordHash, wantHash)
	}

	// The chain still verifies as a whole.
	valid, brokenAt, err := chain.Verify()
	if err != nil {
		t.Fatalf("verify error: %v", err)
	}
	if !valid {
		t.Fatalf("chain invalid at entry %d after appending trajectory", brokenAt)
	}

	// And a third party can independently re-derive the step root.
	steps := []trajectory.Step{
		{StepID: "s1", Kind: trajectory.KindLLMCall, InputHash: "h-prompt",
			OutputHash: "h-plan", GateVerdict: trajectory.VerdictNA,
			TimestampUTC: "2026-06-10T00:00:00Z"},
		{StepID: "s2", ParentIDs: []string{"s1"}, Kind: trajectory.KindToolCall,
			InputHash: "h-search", OutputHash: "h-results",
			GateVerdict: trajectory.VerdictPermit, TimestampUTC: "2026-06-10T00:00:01Z"},
		{StepID: "s3", ParentIDs: []string{"s2"}, Kind: trajectory.KindAction,
			InputHash: "h-archive-all", OutputHash: "",
			GateVerdict: trajectory.VerdictForbid, TimestampUTC: "2026-06-10T00:00:02Z"},
	}
	ok, err := trajectory.Verify(steps, tr.StepRoot)
	if err != nil || !ok {
		t.Fatalf("independent verify failed: ok=%v err=%v", ok, err)
	}
}

func mustAdd(t *testing.T, b *trajectory.Builder, s trajectory.Step) {
	t.Helper()
	if err := b.Add(s); err != nil {
		t.Fatalf("add %s: %v", s.StepID, err)
	}
}

func sha256Hex(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}

func sha256Hex2(b []byte) string {
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}
