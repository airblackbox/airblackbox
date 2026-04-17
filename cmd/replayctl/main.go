// Command replayctl replays AIR records against the LLM provider
// and reports behavioral drift.
//
// Usage:
//
//	replayctl replay <path/to/run.air.json>          — single trace
//	replayctl batch  <dir> [--last N] [--format json] — batch replay
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strconv"

	"github.com/airblackbox/gateway/pkg/recorder"
	"github.com/airblackbox/gateway/pkg/replay"
	"github.com/airblackbox/gateway/pkg/vault"
)

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	switch os.Args[1] {
	case "replay":
		runSingleReplay()
	case "batch":
		runBatchReplay()
	default:
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Fprintf(os.Stderr, `Usage:
  replayctl replay <path/to/run.air.json>
  replayctl batch  <directory> [--last N] [--format json|text]

Environment variables:
  OPENAI_API_KEY     (required) Provider API key for replay
  PROVIDER_URL       Provider endpoint (default: https://api.openai.com)
  VAULT_ENDPOINT     MinIO/S3 endpoint (default: localhost:9000)
  VAULT_ACCESS_KEY   (default: minioadmin)
  VAULT_SECRET_KEY   (default: minioadmin)
  VAULT_BUCKET       (default: air-runs)
  VAULT_USE_SSL      (default: false)
`)
}

// --- Single replay (existing behavior) ---

func runSingleReplay() {
	if len(os.Args) < 3 {
		fmt.Fprintf(os.Stderr, "Usage: replayctl replay <path/to/run.air.json>\n")
		os.Exit(1)
	}

	airPath := os.Args[2]

	rec, err := recorder.Load(airPath)
	if err != nil {
		log.Fatalf("load AIR record: %v", err)
	}

	fmt.Printf("Run ID:    %s\n", rec.RunID)
	fmt.Printf("Model:     %s\n", rec.Model)
	fmt.Printf("Provider:  %s\n", rec.Provider)
	fmt.Printf("Endpoint:  %s\n", rec.Endpoint)
	fmt.Printf("Tokens:    %d\n", rec.Tokens.Total)
	fmt.Printf("Status:    %s\n", rec.Status)
	fmt.Println()

	vc, ctx := connectVault()

	apiKey := requireAPIKey()

	fmt.Println("Replaying...")
	result, err := replay.Run(ctx, rec, replay.Options{
		ProviderURL: envOr("PROVIDER_URL", "https://api.openai.com"),
		VaultClient: vc,
		APIKey:      apiKey,
	})
	if err != nil {
		log.Fatalf("replay failed: %v", err)
	}

	fmt.Println()
	fmt.Printf("Similarity: %.2f\n", result.Similarity)

	if result.Drift {
		fmt.Printf("DRIFT DETECTED: %s\n", result.DriftSummary)
		data, _ := json.MarshalIndent(result, "", "  ")
		fmt.Println(string(data))
		os.Exit(1)
	}

	fmt.Println("NO DRIFT — replay matches original within threshold.")
}

// --- Batch replay (new) ---

func runBatchReplay() {
	if len(os.Args) < 3 {
		fmt.Fprintf(os.Stderr, "Usage: replayctl batch <directory> [--last N] [--format json|text]\n")
		os.Exit(1)
	}

	dir := os.Args[2]

	// Parse optional flags (simple manual parsing — no external deps).
	last := 0
	format := "text"

	for i := 3; i < len(os.Args); i++ {
		switch os.Args[i] {
		case "--last":
			if i+1 < len(os.Args) {
				n, err := strconv.Atoi(os.Args[i+1])
				if err != nil || n < 1 {
					log.Fatal("--last requires a positive integer")
				}
				last = n
				i++ // skip the value
			} else {
				log.Fatal("--last requires a value")
			}
		case "--format":
			if i+1 < len(os.Args) {
				format = os.Args[i+1]
				if format != "json" && format != "text" {
					log.Fatal("--format must be json or text")
				}
				i++
			} else {
				log.Fatal("--format requires a value")
			}
		default:
			log.Fatalf("unknown flag: %s", os.Args[i])
		}
	}

	vc, ctx := connectVault()

	apiKey := requireAPIKey()

	opts := replay.BatchOptions{
		Options: replay.Options{
			ProviderURL: envOr("PROVIDER_URL", "https://api.openai.com"),
			VaultClient: vc,
			APIKey:      apiKey,
		},
		Last: last,
	}

	result, err := replay.RunBatch(ctx, dir, opts)
	if err != nil {
		log.Fatalf("batch replay failed: %v", err)
	}

	// Output based on format.
	switch format {
	case "json":
		data, err := result.JSON()
		if err != nil {
			log.Fatalf("marshal result: %v", err)
		}
		fmt.Println(string(data))
	default:
		fmt.Print(result.Text())
	}

	// Exit 1 if any drift detected (CI-friendly).
	if result.OverallDrift {
		os.Exit(1)
	}
}

// --- Shared helpers ---

func connectVault() (*vault.Client, context.Context) {
	ctx := context.Background()
	vc, err := vault.New(ctx, vault.Config{
		Endpoint:  envOr("VAULT_ENDPOINT", "localhost:9000"),
		AccessKey: envOr("VAULT_ACCESS_KEY", "minioadmin"),
		SecretKey: envOr("VAULT_SECRET_KEY", "minioadmin"),
		Bucket:    envOr("VAULT_BUCKET", "air-runs"),
		UseSSL:    envOr("VAULT_USE_SSL", "false") == "true",
	})
	if err != nil {
		log.Fatalf("vault connect: %v", err)
	}
	return vc, ctx
}

func requireAPIKey() string {
	apiKey := envOr("OPENAI_API_KEY", "")
	if apiKey == "" {
		log.Fatal("OPENAI_API_KEY required for replay")
	}
	return apiKey
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
