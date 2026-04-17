// Command evidencectl exports an AIR Blackbox evidence package as a PDF
// compliance report.
//
// Usage:
//
//	evidencectl pdf [--input evidence.json] [--output report.pdf] [--company "Acme Corp"]
//	evidencectl pdf --from-chain [--secret key] [--output report.pdf]
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/airblackbox/gateway/pkg/trust"
	"github.com/airblackbox/gateway/pkg/vault"
)

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	switch os.Args[1] {
	case "pdf":
		runPDFExport()
	case "export":
		runJSONExport()
	default:
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Fprintf(os.Stderr, `Usage:
  evidencectl pdf    [--input FILE] [--output FILE] [--company NAME]
  evidencectl export [--output FILE] [--secret KEY]

Commands:
  pdf     Generate a PDF compliance report from an evidence package JSON
  export  Export the current audit chain + compliance evaluation as JSON

Flags for 'pdf':
  --input     Path to evidence package JSON (default: stdin)
  --output    Path for PDF output (default: evidence-report.pdf)
  --company   Organization name shown on cover page

Flags for 'export':
  --output    Path for JSON output (default: evidence-package.json)
  --secret    HMAC signing secret (or set GATEWAY_SECRET env var)

Environment variables:
  GATEWAY_SECRET     HMAC signing key for evidence packages
  GATEWAY_ID         Gateway identifier
  VAULT_ENDPOINT     MinIO/S3 endpoint (default: localhost:9000)
  VAULT_ACCESS_KEY   (default: minioadmin)
  VAULT_SECRET_KEY   (default: minioadmin)
  VAULT_BUCKET       (default: air-runs)
`)
}

// runPDFExport reads an evidence package JSON and renders it as a PDF.
func runPDFExport() {
	inputPath := ""
	outputPath := "evidence-report.pdf"
	companyName := ""

	for i := 2; i < len(os.Args); i++ {
		switch os.Args[i] {
		case "--input":
			if i+1 < len(os.Args) {
				inputPath = os.Args[i+1]
				i++
			}
		case "--output":
			if i+1 < len(os.Args) {
				outputPath = os.Args[i+1]
				i++
			}
		case "--company":
			if i+1 < len(os.Args) {
				companyName = os.Args[i+1]
				i++
			}
		}
	}

	// Read evidence package JSON.
	var data []byte
	var err error

	if inputPath == "" || inputPath == "-" {
		data, err = readStdin()
		if err != nil {
			log.Fatalf("read stdin: %v", err)
		}
	} else {
		data, err = os.ReadFile(inputPath)
		if err != nil {
			log.Fatalf("read %s: %v", inputPath, err)
		}
	}

	var pkg trust.EvidencePackage
	if err := json.Unmarshal(data, &pkg); err != nil {
		log.Fatalf("parse evidence package: %v", err)
	}

	opts := trust.PDFOptions{
		CompanyName: companyName,
	}

	fmt.Printf("Generating PDF report → %s\n", outputPath)
	if err := trust.ExportPDF(&pkg, outputPath, opts); err != nil {
		log.Fatalf("generate PDF: %v", err)
	}

	fmt.Printf("Done. %d audit entries, %d compliance controls.\n",
		len(pkg.AuditEntries), countControls(&pkg))
}

// runJSONExport creates an evidence package from a live gateway and writes JSON.
func runJSONExport() {
	outputPath := "evidence-package.json"
	secret := envOr("GATEWAY_SECRET", "")
	gatewayID := envOr("GATEWAY_ID", "unknown")

	for i := 2; i < len(os.Args); i++ {
		switch os.Args[i] {
		case "--output":
			if i+1 < len(os.Args) {
				outputPath = os.Args[i+1]
				i++
			}
		case "--secret":
			if i+1 < len(os.Args) {
				secret = os.Args[i+1]
				i++
			}
		}
	}

	if secret == "" {
		log.Fatal("GATEWAY_SECRET or --secret required for evidence export")
	}

	// Connect to vault to get chain data.
	ctx := context.Background()
	_, err := vault.New(ctx, vault.Config{
		Endpoint:  envOr("VAULT_ENDPOINT", "localhost:9000"),
		AccessKey: envOr("VAULT_ACCESS_KEY", "minioadmin"),
		SecretKey: envOr("VAULT_SECRET_KEY", "minioadmin"),
		Bucket:    envOr("VAULT_BUCKET", "air-runs"),
		UseSSL:    envOr("VAULT_USE_SSL", "false") == "true",
	})
	if err != nil {
		log.Fatalf("vault connect: %v", err)
	}

	// Build a chain from scratch for demonstration — in production this would
	// load from the gateway's persistent chain store.
	chain := trust.NewAuditChain(secret)

	// Run compliance evaluation.
	compliance := trust.EvaluateCompliance(trust.ComplianceConfig{
		Frameworks: []string{"SOC2", "ISO27001"},
	}, chain.Len(), true, true, true)

	pkg := trust.GenerateEvidencePackage(chain, compliance, gatewayID, secret)

	data, err := json.MarshalIndent(pkg, "", "  ")
	if err != nil {
		log.Fatalf("marshal evidence: %v", err)
	}

	if err := os.WriteFile(outputPath, data, 0644); err != nil {
		log.Fatalf("write %s: %v", outputPath, err)
	}

	fmt.Printf("Evidence package exported → %s\n", outputPath)
	fmt.Printf("Chain: %d entries | Controls: %d | Attestation: %s...\n",
		pkg.ChainLength, len(pkg.ComplianceReport.Controls),
		truncateStr(pkg.Attestation, 16))
}

// ---- helpers ----

func readStdin() ([]byte, error) {
	stat, _ := os.Stdin.Stat()
	if (stat.Mode() & os.ModeCharDevice) != 0 {
		return nil, fmt.Errorf("no input on stdin (pipe a file or use --input)")
	}
	return os.ReadFile("/dev/stdin")
}

func countControls(pkg *trust.EvidencePackage) int {
	if pkg.ComplianceReport == nil {
		return 0
	}
	return len(pkg.ComplianceReport.Controls)
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return strings.TrimSpace(v)
	}
	return fallback
}

func truncateStr(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n]
}
