// Package trajectory commits an agent run (a DAG of steps) to a single
// Merkle root, so the existing audit chain can sign one entry per run instead
// of one per LLM call. See docs/SPEC-trajectory-chain.md.
//
// The root is computed over the steps in a canonical topological order, so two
// independent verifiers given the same steps always derive the same root,
// regardless of the order the steps were recorded in.
package trajectory

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
)

// StepKind classifies what a step did.
type StepKind string

const (
	KindLLMCall     StepKind = "llm_call"
	KindToolCall    StepKind = "tool_call"
	KindAction      StepKind = "action"
	KindObservation StepKind = "observation"
	KindSubAgent    StepKind = "sub_agent"
)

// GateVerdict is the policy decision recorded on an action or tool_call step.
type GateVerdict string

const (
	VerdictPermit          GateVerdict = "permit"
	VerdictRequireApproval GateVerdict = "require_approval"
	VerdictForbid          GateVerdict = "forbid"
	VerdictNA              GateVerdict = "n/a"
)

// Outcome is the terminal state of a trajectory.
type Outcome string

const (
	OutcomeCompleted Outcome = "completed"
	OutcomeAborted   Outcome = "aborted"
	OutcomeBlocked   Outcome = "blocked"
)

// Step is one node in a trajectory DAG.
type Step struct {
	StepID       string      `json:"step_id"`
	ParentIDs    []string    `json:"parent_ids"`
	Kind         StepKind    `json:"kind"`
	InputHash    string      `json:"input_hash"`
	OutputHash   string      `json:"output_hash"`
	GateVerdict  GateVerdict `json:"gate_verdict"`
	TimestampUTC string      `json:"timestamp"` // RFC3339 UTC
}

// canonical returns the deterministic byte encoding of a step that the leaf
// hash is computed over. ParentIDs are sorted so the set, not the recording
// order, is what the hash commits to.
func (s Step) canonical() []byte {
	c := s
	c.ParentIDs = append([]string(nil), s.ParentIDs...)
	sort.Strings(c.ParentIDs)
	b, _ := json.Marshal(c)
	return b
}

// Trajectory is the signed summary of an agent run.
type Trajectory struct {
	TrajectoryID string  `json:"trajectory_id"`
	RootGoalHash string  `json:"root_goal_hash"`
	StepRoot     string  `json:"step_root"` // Merkle root, hex
	StepCount    int     `json:"step_count"`
	Outcome      Outcome `json:"outcome"`
}

// Builder accumulates steps for one trajectory and commits them to a root.
type Builder struct {
	id       string
	goalHash string
	steps    map[string]Step
	order    []string // insertion order, only for error messages
}

// NewBuilder starts a trajectory. rootGoalHash is the sha256 (hex) of the
// initiating goal or prompt.
func NewBuilder(trajectoryID, rootGoalHash string) *Builder {
	return &Builder{
		id:       trajectoryID,
		goalHash: rootGoalHash,
		steps:    make(map[string]Step),
	}
}

// Add records a step. Duplicate step IDs are rejected.
func (b *Builder) Add(s Step) error {
	if s.StepID == "" {
		return fmt.Errorf("trajectory: step_id is required")
	}
	if _, dup := b.steps[s.StepID]; dup {
		return fmt.Errorf("trajectory: duplicate step_id %q", s.StepID)
	}
	b.steps[s.StepID] = s
	b.order = append(b.order, s.StepID)
	return nil
}

// canonicalOrder returns step IDs sorted by (causal depth, then step_id).
// Depth is the longest path from a root; it is stable and independent of
// insertion order. Returns an error if a parent is unknown or a cycle exists.
func (b *Builder) canonicalOrder() ([]string, error) {
	depth := make(map[string]int, len(b.steps))
	visiting := make(map[string]bool)

	var resolve func(id string) (int, error)
	resolve = func(id string) (int, error) {
		if d, ok := depth[id]; ok {
			return d, nil
		}
		s, ok := b.steps[id]
		if !ok {
			return 0, fmt.Errorf("trajectory: step %q references unknown parent", id)
		}
		if visiting[id] {
			return 0, fmt.Errorf("trajectory: cycle detected at step %q", id)
		}
		visiting[id] = true
		max := -1
		for _, p := range s.ParentIDs {
			pd, err := resolve(p)
			if err != nil {
				return 0, err
			}
			if pd > max {
				max = pd
			}
		}
		visiting[id] = false
		d := max + 1 // roots (no parents) get depth 0
		depth[id] = d
		return d, nil
	}

	for id := range b.steps {
		if _, err := resolve(id); err != nil {
			return nil, err
		}
	}

	ids := make([]string, 0, len(b.steps))
	for id := range b.steps {
		ids = append(ids, id)
	}
	sort.Slice(ids, func(i, j int) bool {
		di, dj := depth[ids[i]], depth[ids[j]]
		if di != dj {
			return di < dj
		}
		return ids[i] < ids[j]
	})
	return ids, nil
}

// leafHash domain-separates leaves (0x00 prefix) so a leaf can never be
// confused with an internal node (0x01 prefix). This is standard Merkle
// second-preimage hardening (cf. RFC 6962).
func leafHash(canonical []byte) []byte {
	h := sha256.New()
	h.Write([]byte{0x00})
	h.Write(canonical)
	return h.Sum(nil)
}

func internalHash(left, right []byte) []byte {
	h := sha256.New()
	h.Write([]byte{0x01})
	h.Write(left)
	h.Write(right)
	return h.Sum(nil)
}

// merkleRoot builds a binary Merkle tree over ordered leaves. An odd level
// duplicates its last node. A single leaf is its own root.
func merkleRoot(leaves [][]byte) []byte {
	if len(leaves) == 0 {
		return nil
	}
	level := leaves
	for len(level) > 1 {
		var next [][]byte
		for i := 0; i < len(level); i += 2 {
			if i+1 < len(level) {
				next = append(next, internalHash(level[i], level[i+1]))
			} else {
				next = append(next, internalHash(level[i], level[i])) // duplicate last
			}
		}
		level = next
	}
	return level[0]
}

// Commit computes the trajectory summary, including the Merkle step root.
func (b *Builder) Commit(outcome Outcome) (Trajectory, error) {
	if len(b.steps) == 0 {
		return Trajectory{}, fmt.Errorf("trajectory: no steps to commit")
	}
	order, err := b.canonicalOrder()
	if err != nil {
		return Trajectory{}, err
	}
	leaves := make([][]byte, len(order))
	for i, id := range order {
		leaves[i] = leafHash(b.steps[id].canonical())
	}
	root := merkleRoot(leaves)
	return Trajectory{
		TrajectoryID: b.id,
		RootGoalHash: b.goalHash,
		StepRoot:     hex.EncodeToString(root),
		StepCount:    len(b.steps),
		Outcome:      outcome,
	}, nil
}

// CanonicalSummary returns the deterministic JSON encoding of a committed
// trajectory. Its sha256 is what the existing audit chain commits to, so a
// trajectory rides on the current chain with no chain changes (the chain's
// record hash becomes the hash of this summary).
func (t Trajectory) CanonicalSummary() []byte {
	b, _ := json.Marshal(t)
	return b
}

// Verify recomputes the Merkle root from the given steps and reports whether
// it matches claimedRoot. A third party uses this to confirm a trajectory
// summary was not altered after signing.
func Verify(steps []Step, claimedRoot string) (bool, error) {
	b := NewBuilder("", "")
	for _, s := range steps {
		if err := b.Add(s); err != nil {
			return false, err
		}
	}
	order, err := b.canonicalOrder()
	if err != nil {
		return false, err
	}
	leaves := make([][]byte, len(order))
	for i, id := range order {
		leaves[i] = leafHash(b.steps[id].canonical())
	}
	return hex.EncodeToString(merkleRoot(leaves)) == claimedRoot, nil
}
