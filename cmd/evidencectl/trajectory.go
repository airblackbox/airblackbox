package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/airblackbox/gateway/pkg/trust"
)

func sha256Hex(b []byte) string {
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}

// trajectorySummary is the shape Tombstone's TrajectoryRecorder.commit() emits.
type trajectorySummary struct {
	TrajectoryID string `json:"trajectory_id"`
	RootGoalHash string `json:"root_goal_hash"`
	StepRoot     string `json:"step_root"`
	StepCount    int    `json:"step_count"`
	Outcome      string `json:"outcome"`
}

// canonicalSummaryRecord encodes a summary as a language-neutral, newline
// delimited record. The anchored hash is computed over THIS, not the Python
// JSON, so it does not depend on Go-vs-Python JSON key order or whitespace.
// A verifier reproduces these bytes from the summary fields and confirms the
// hash matches the record in the anchored chain entry.
const summaryVersion = "TRAJ-SUMMARY-v1"

func canonicalSummaryRecord(s trajectorySummary) []byte {
	fields := []string{
		summaryVersion,
		s.TrajectoryID,
		s.RootGoalHash,
		s.StepRoot,
		strconv.Itoa(s.StepCount),
		s.Outcome,
	}
	return []byte(strings.Join(fields, "\n"))
}

// anchorBundle is the self-contained output: the trajectory summary plus the
// signed (and optionally Rekor-anchored) checkpoint that commits its root.
type anchorBundle struct {
	Trajectory       trajectorySummary      `json:"trajectory"`
	ChainEntry       trust.ChainEntry       `json:"chain_entry"`
	SignedCheckpoint trust.SignedCheckpoint `json:"signed_checkpoint"`
}

// runAnchorTrajectory takes a trajectory summary from Tombstone's Python
// capture and anchors its Merkle step root with the Go evidence stack:
// it commits the root to an audit chain, cuts a dual-signed (ML-DSA-65 +
// Ed25519) checkpoint, and optionally publishes it to Rekor.
//
//	evidencectl anchor-trajectory --input summary.json [--rekor] [--keys DIR] [--out FILE] [--secret KEY]
func runAnchorTrajectory(args []string) {
	inputPath := ""
	outPath := "trajectory-anchor.json"
	keysDir := defaultKeysDir()
	secret := os.Getenv("TRUST_SIGNING_KEY")
	if secret == "" {
		secret = "evidencectl-local"
	}
	doRekor := false
	server := trust.DefaultRekorServer

	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--input":
			if i+1 < len(args) {
				i++
				inputPath = args[i]
			}
		case "--out":
			if i+1 < len(args) {
				i++
				outPath = args[i]
			}
		case "--keys":
			if i+1 < len(args) {
				i++
				keysDir = args[i]
			}
		case "--secret":
			if i+1 < len(args) {
				i++
				secret = args[i]
			}
		case "--rekor":
			doRekor = true
		default:
			fmt.Fprintf(os.Stderr, "unknown flag: %s\n", args[i])
			os.Exit(2)
		}
	}
	if inputPath == "" {
		fmt.Fprintln(os.Stderr, "anchor-trajectory: --input summary.json is required")
		os.Exit(2)
	}

	raw, err := os.ReadFile(inputPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "anchor-trajectory: read input: %v\n", err)
		os.Exit(1)
	}
	var sum trajectorySummary
	if err := json.Unmarshal(raw, &sum); err != nil {
		fmt.Fprintf(os.Stderr, "anchor-trajectory: parse summary: %v\n", err)
		os.Exit(1)
	}
	if sum.StepRoot == "" || sum.TrajectoryID == "" {
		fmt.Fprintln(os.Stderr, "anchor-trajectory: summary missing trajectory_id or step_root")
		os.Exit(1)
	}
	if len(sum.StepRoot) != 64 {
		fmt.Fprintf(os.Stderr, "anchor-trajectory: step_root is not a sha256 hex digest: %q\n", sum.StepRoot)
		os.Exit(1)
	}

	// Commit the trajectory root to an audit chain via a language-neutral
	// record, then cut a dual-signed checkpoint over the head.
	chain := trust.NewAuditChain(secret)
	entry := chain.Append(sum.TrajectoryID, canonicalSummaryRecord(sum))

	mldsa, err := trust.NewSigner(keysDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "anchor-trajectory: load ML-DSA signer: %v\n", err)
		os.Exit(1)
	}
	ed, err := trust.NewSignerEd25519(keysDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "anchor-trajectory: load Ed25519 signer: %v\n", err)
		os.Exit(1)
	}
	sc, err := trust.CreateCheckpoint(chain, mldsa, ed)
	if err != nil {
		fmt.Fprintf(os.Stderr, "anchor-trajectory: checkpoint: %v\n", err)
		os.Exit(1)
	}

	if doRekor {
		anchor, err := trust.AnchorToRekor(server, sc)
		if err != nil {
			fmt.Fprintf(os.Stderr, "anchor-trajectory: Rekor anchor: %v\n", err)
			os.Exit(1)
		}
		sc.Anchors = append(sc.Anchors, anchor)
		fmt.Printf("Anchored to Rekor: log index %d\n", anchor.LogIndex)
	}

	bundle := anchorBundle{Trajectory: sum, ChainEntry: entry, SignedCheckpoint: sc}
	out, err := json.MarshalIndent(bundle, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "anchor-trajectory: marshal output: %v\n", err)
		os.Exit(1)
	}
	if err := os.WriteFile(outPath, out, 0644); err != nil {
		fmt.Fprintf(os.Stderr, "anchor-trajectory: write output: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Trajectory:   %s (%d steps, %s)\n", sum.TrajectoryID, sum.StepCount, sum.Outcome)
	fmt.Printf("Step root:    %s\n", sum.StepRoot)
	fmt.Printf("Checkpoint:   head %s, %d signatures\n", sc.Checkpoint.HeadHash[:16]+"...", len(sc.Signatures))
	fmt.Printf("Written:      %s\n", outPath)
}

// verifyBundle checks an anchor bundle's full chain of custody and returns nil
// if every link holds. It needs no secret and no running gateway.
func verifyBundle(b anchorBundle) error {
	// 1. The summary's canonical record must hash to the entry's RecordHash.
	if got := sha256Hex(canonicalSummaryRecord(b.Trajectory)); got != b.ChainEntry.RecordHash {
		return fmt.Errorf("summary does not match chain entry record hash: got %s want %s",
			got, b.ChainEntry.RecordHash)
	}
	// 2. The entry must hash to the checkpoint's HeadHash.
	entryJSON, _ := json.Marshal(b.ChainEntry)
	if got := sha256Hex(entryJSON); got != b.SignedCheckpoint.Checkpoint.HeadHash {
		return fmt.Errorf("chain entry does not match checkpoint head: got %s want %s",
			got, b.SignedCheckpoint.Checkpoint.HeadHash)
	}
	// 3. The checkpoint signatures must be valid.
	return trust.VerifySignedCheckpoint(b.SignedCheckpoint)
}

// runVerifyTrajectory independently verifies an anchor bundle's full chain of
// custody, without needing the HMAC secret or any running gateway:
//
//	summary -> canonical record -> RecordHash in the chain entry
//	         -> sha256(entry) -> HeadHash in the checkpoint
//	         -> checkpoint signatures (ML-DSA-65 + Ed25519)
//
//	evidencectl verify-trajectory --input bundle.json
func runVerifyTrajectory(args []string) {
	inputPath := ""
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--input":
			if i+1 < len(args) {
				i++
				inputPath = args[i]
			}
		default:
			fmt.Fprintf(os.Stderr, "unknown flag: %s\n", args[i])
			os.Exit(2)
		}
	}
	if inputPath == "" {
		fmt.Fprintln(os.Stderr, "verify-trajectory: --input bundle.json is required")
		os.Exit(2)
	}
	raw, err := os.ReadFile(inputPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "verify-trajectory: read: %v\n", err)
		os.Exit(1)
	}
	var b anchorBundle
	if err := json.Unmarshal(raw, &b); err != nil {
		fmt.Fprintf(os.Stderr, "verify-trajectory: parse: %v\n", err)
		os.Exit(1)
	}
	if err := verifyBundle(b); err != nil {
		fmt.Printf("FAIL: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("VERIFIED: trajectory %s (%d steps, %s)\n",
		b.Trajectory.TrajectoryID, b.Trajectory.StepCount, b.Trajectory.Outcome)
	fmt.Printf("  step root %s is committed by a checkpoint with %d valid signatures\n",
		b.Trajectory.StepRoot, len(b.SignedCheckpoint.Signatures))
	algs := make([]string, 0, len(b.SignedCheckpoint.Signatures))
	for _, sg := range b.SignedCheckpoint.Signatures {
		algs = append(algs, string(sg.Algorithm))
	}
	fmt.Printf("  signatures: %s\n", strings.Join(algs, ", "))
	if len(b.SignedCheckpoint.Anchors) > 0 {
		fmt.Printf("  Rekor: log index %d at %s\n",
			b.SignedCheckpoint.Anchors[0].LogIndex, b.SignedCheckpoint.Anchors[0].Server)
	}
}
