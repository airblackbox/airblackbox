package trajectory

import "testing"

func step(id string, parents ...string) Step {
	return Step{
		StepID:       id,
		ParentIDs:    parents,
		Kind:         KindLLMCall,
		InputHash:    "in-" + id,
		OutputHash:   "out-" + id,
		GateVerdict:  VerdictNA,
		TimestampUTC: "2026-06-10T00:00:00Z",
	}
}

func build(t *testing.T, steps ...Step) Trajectory {
	t.Helper()
	b := NewBuilder("traj-1", "goalhash")
	for _, s := range steps {
		if err := b.Add(s); err != nil {
			t.Fatalf("add %s: %v", s.StepID, err)
		}
	}
	tr, err := b.Commit(OutcomeCompleted)
	if err != nil {
		t.Fatalf("commit: %v", err)
	}
	return tr
}

func TestSingleStep(t *testing.T) {
	tr := build(t, step("a"))
	if tr.StepCount != 1 || tr.StepRoot == "" {
		t.Fatalf("bad single-step trajectory: %+v", tr)
	}
}

func TestDeterministicAcrossInsertionOrder(t *testing.T) {
	// a -> b -> c, recorded in two different orders. Roots must match.
	r1 := build(t, step("a"), step("b", "a"), step("c", "b"))
	r2 := build(t, step("c", "b"), step("a"), step("b", "a"))
	if r1.StepRoot != r2.StepRoot {
		t.Fatalf("root depends on insertion order: %s vs %s", r1.StepRoot, r2.StepRoot)
	}
}

func TestParentIDOrderDoesNotMatter(t *testing.T) {
	// A step whose parent set is {a,b} must hash the same regardless of order.
	base := []Step{step("a"), step("b")}
	c1 := step("c", "a", "b")
	c2 := step("c", "b", "a")
	r1 := build(t, append(append([]Step{}, base...), c1)...)
	r2 := build(t, append(append([]Step{}, base...), c2)...)
	if r1.StepRoot != r2.StepRoot {
		t.Fatalf("parent_ids order changed root: %s vs %s", r1.StepRoot, r2.StepRoot)
	}
}

func TestTamperChangesRoot(t *testing.T) {
	orig := build(t, step("a"), step("b", "a"))
	tampered := step("b", "a")
	tampered.OutputHash = "out-b-MUTATED"
	mut := build(t, step("a"), tampered)
	if orig.StepRoot == mut.StepRoot {
		t.Fatal("mutating a step did not change the root")
	}
}

func TestBranchingDAG(t *testing.T) {
	// root a; parallel children b and c; join d depends on both.
	tr := build(t, step("a"), step("b", "a"), step("c", "a"), step("d", "b", "c"))
	if tr.StepCount != 4 {
		t.Fatalf("want 4 steps, got %d", tr.StepCount)
	}
	steps := []Step{step("a"), step("b", "a"), step("c", "a"), step("d", "b", "c")}
	ok, err := Verify(steps, tr.StepRoot)
	if err != nil || !ok {
		t.Fatalf("verify failed: ok=%v err=%v", ok, err)
	}
}

func TestOddLeafCount(t *testing.T) {
	// 3 steps exercises the odd-level duplication path.
	tr := build(t, step("a"), step("b", "a"), step("c", "b"))
	if tr.StepRoot == "" {
		t.Fatal("empty root for 3-step trajectory")
	}
}

func TestUnknownParentRejected(t *testing.T) {
	b := NewBuilder("t", "g")
	_ = b.Add(step("b", "does-not-exist"))
	if _, err := b.Commit(OutcomeCompleted); err == nil {
		t.Fatal("expected error for unknown parent")
	}
}

func TestCycleRejected(t *testing.T) {
	b := NewBuilder("t", "g")
	_ = b.Add(step("a", "b"))
	_ = b.Add(step("b", "a"))
	if _, err := b.Commit(OutcomeCompleted); err == nil {
		t.Fatal("expected cycle detection error")
	}
}

func TestDuplicateStepRejected(t *testing.T) {
	b := NewBuilder("t", "g")
	_ = b.Add(step("a"))
	if err := b.Add(step("a")); err == nil {
		t.Fatal("expected duplicate step_id error")
	}
}

func TestEmptyTrajectoryRejected(t *testing.T) {
	b := NewBuilder("t", "g")
	if _, err := b.Commit(OutcomeCompleted); err == nil {
		t.Fatal("expected error committing empty trajectory")
	}
}

func TestVerifyDetectsTampering(t *testing.T) {
	tr := build(t, step("a"), step("b", "a"))
	tampered := []Step{step("a"), step("b", "a")}
	tampered[1].GateVerdict = VerdictForbid // change a field
	ok, err := Verify(tampered, tr.StepRoot)
	if err != nil {
		t.Fatalf("verify err: %v", err)
	}
	if ok {
		t.Fatal("verify accepted tampered steps")
	}
}

func TestDomainSeparation(t *testing.T) {
	// Two leaves must not collide with a single leaf built from their
	// concatenation. We assert the prefixes are actually applied by checking
	// a 2-step root differs from a 1-step root with concatenated content.
	two := build(t, step("a"), step("b"))
	one := build(t, Step{StepID: "ab", Kind: KindLLMCall, GateVerdict: VerdictNA})
	if two.StepRoot == one.StepRoot {
		t.Fatal("domain separation failure: 2-leaf root collided with 1-leaf root")
	}
}

func TestCanonicalSummaryStable(t *testing.T) {
	tr := build(t, step("a"))
	if string(tr.CanonicalSummary()) != string(tr.CanonicalSummary()) {
		t.Fatal("summary not stable")
	}
}
