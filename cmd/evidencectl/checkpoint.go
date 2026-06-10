package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/airblackbox/gateway/pkg/trust"
)

// runCheckpoint cuts a dual-signed checkpoint from the gateway's audit chain.
//
//	evidencectl checkpoint [--gateway URL] [--keys DIR] [--out FILE]
func runCheckpoint(args []string) {
	gateway := "http://localhost:8080"
	keysDir := defaultKeysDir()
	outPath := "checkpoint.json"
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--gateway":
			if i+1 < len(args) {
				gateway = args[i+1]
				i++
			}
		case "--keys":
			if i+1 < len(args) {
				keysDir = args[i+1]
				i++
			}
		case "--out":
			if i+1 < len(args) {
				outPath = args[i+1]
				i++
			}
		}
	}

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Get(gateway + "/v1/audit/export")
	if err != nil {
		fatalf("fetch evidence export: %v\nIs the gateway running at %s?", err, gateway)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		fatalf("gateway returned HTTP %d: %s", resp.StatusCode, body)
	}

	var pkg trust.EvidencePackage
	if err := json.NewDecoder(resp.Body).Decode(&pkg); err != nil {
		fatalf("parse evidence package: %v", err)
	}
	if len(pkg.AuditEntries) == 0 {
		fatalf("audit chain is empty; route some traffic through the gateway first")
	}

	mldsa, err := trust.NewSigner(keysDir)
	if err != nil {
		fatalf("ML-DSA signer: %v", err)
	}
	ed, err := trust.NewSignerEd25519(keysDir)
	if err != nil {
		fatalf("Ed25519 signer: %v", err)
	}

	sc, err := trust.CheckpointFromEntries(pkg.AuditEntries, mldsa, ed)
	if err != nil {
		fatalf("create checkpoint: %v", err)
	}

	data, _ := json.MarshalIndent(sc, "", "  ")
	if err := os.WriteFile(outPath, data, 0644); err != nil {
		fatalf("write %s: %v", outPath, err)
	}

	fmt.Printf("Checkpoint cut at chain length %d\n", sc.Checkpoint.ChainLength)
	fmt.Printf("  head hash:  %s\n", sc.Checkpoint.HeadHash)
	fmt.Printf("  signatures: %s + %s\n", sc.Signatures[0].Algorithm, sc.Signatures[1].Algorithm)
	fmt.Printf("  saved to:   %s\n", outPath)
	fmt.Printf("\nAnchor it to the public transparency log:\n  evidencectl anchor --checkpoint %s\n", outPath)
}

// runAnchor publishes a checkpoint's Ed25519 signature to Rekor.
//
//	evidencectl anchor [--checkpoint FILE] [--server URL]
func runAnchor(args []string) {
	cpPath := "checkpoint.json"
	server := trust.DefaultRekorServer
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--checkpoint":
			if i+1 < len(args) {
				cpPath = args[i+1]
				i++
			}
		case "--server":
			if i+1 < len(args) {
				server = args[i+1]
				i++
			}
		}
	}

	sc := loadCheckpoint(cpPath)
	if err := trust.VerifySignedCheckpoint(sc); err != nil {
		fatalf("refusing to anchor: %v", err)
	}

	anchor, err := trust.AnchorToRekor(server, sc)
	if err != nil {
		fatalf("%v", err)
	}

	sc.Anchors = append(sc.Anchors, anchor)
	data, _ := json.MarshalIndent(sc, "", "  ")
	if err := os.WriteFile(cpPath, data, 0644); err != nil {
		fatalf("write anchor receipt: %v", err)
	}

	if anchor.AlreadyExisted {
		fmt.Println("This exact checkpoint was already in the log.")
	} else {
		fmt.Printf("Anchored to %s\n", server)
		fmt.Printf("  log index: %d\n", anchor.LogIndex)
	}
	fmt.Printf("  uuid:      %s\n", anchor.UUID)
	fmt.Printf("  verify:    https://search.sigstore.dev/?uuid=%s\n", anchor.UUID)
	fmt.Println("\nThe chain head is now provable to third parties without trusting this machine.")
}

// runVerifyCheckpoint verifies signatures locally and optionally confirms
// anchors still exist in the public log.
//
//	evidencectl verify-checkpoint [--checkpoint FILE] [--rekor]
func runVerifyCheckpoint(args []string) {
	cpPath := "checkpoint.json"
	checkRekor := false
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--checkpoint":
			if i+1 < len(args) {
				cpPath = args[i+1]
				i++
			}
		case "--rekor":
			checkRekor = true
		}
	}

	sc := loadCheckpoint(cpPath)
	if err := trust.VerifySignedCheckpoint(sc); err != nil {
		fatalf("%v", err)
	}
	for _, sd := range sc.Signatures {
		fmt.Printf("  %s signature: VALID\n", sd.Algorithm)
	}

	if checkRekor {
		if len(sc.Anchors) == 0 {
			fatalf("no anchors recorded in %s; run: evidencectl anchor", cpPath)
		}
		for _, a := range sc.Anchors {
			if _, err := trust.FetchRekorEntry(a.Server, a.UUID); err != nil {
				fatalf("anchor %s: %v", a.UUID, err)
			}
			fmt.Printf("  rekor anchor %s: PRESENT in public log (index %d)\n", a.UUID, a.LogIndex)
		}
	}
	fmt.Println("Checkpoint verified.")
}

func loadCheckpoint(path string) trust.SignedCheckpoint {
	data, err := os.ReadFile(path)
	if err != nil {
		fatalf("read %s: %v", path, err)
	}
	var sc trust.SignedCheckpoint
	if err := json.Unmarshal(data, &sc); err != nil {
		fatalf("parse %s: %v", path, err)
	}
	return sc
}

func defaultKeysDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return ".air-keys"
	}
	return home + "/.airblackbox/keys"
}

func fatalf(format string, a ...any) {
	fmt.Fprintf(os.Stderr, "error: "+format+"\n", a...)
	os.Exit(1)
}
