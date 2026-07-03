// Command gateway starts the AIR Blackbox Gateway — an OpenAI-compatible
// reverse proxy that records every LLM call for audit and replay.
package main

import (
	"context"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/airblackbox/gateway/pkg/guardrails"
	"github.com/airblackbox/gateway/pkg/proxy"
	"github.com/airblackbox/gateway/pkg/recorder"
	"github.com/airblackbox/gateway/pkg/trust"
	"github.com/airblackbox/gateway/pkg/vault"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
)

func main() {
	addr := flag.String("addr", envOr("LISTEN_ADDR", ":8080"), "listen address")
	providerURL := flag.String("provider", envOr("PROVIDER_URL", "https://api.openai.com"), "upstream LLM provider")
	runsDir := flag.String("runs", envOr("RUNS_DIR", "./runs"), "AIR record output directory")
	flag.Parse()

	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	// --- OTel tracing setup ---
	tp, err := initTracer(ctx)
	if err != nil {
		log.Printf("WARN: OTel tracing disabled: %v", err)
	} else if tp != nil {
		defer tp.Shutdown(ctx)
	}

	// --- Vault setup (best-effort; gateway works without it) ---
	var vc *vault.Client
	vaultEndpoint := envOr("VAULT_ENDPOINT", "")
	if vaultEndpoint != "" {
		vc, err = vault.New(ctx, vault.Config{
			Endpoint:  vaultEndpoint,
			AccessKey: envOr("VAULT_ACCESS_KEY", "minioadmin"),
			SecretKey: envOr("VAULT_SECRET_KEY", "minioadmin"),
			Bucket:    envOr("VAULT_BUCKET", "air-runs"),
			UseSSL:    envOr("VAULT_USE_SSL", "false") == "true",
		})
		if err != nil {
			log.Printf("WARN: vault disabled: %v (gateway will proxy without recording)", err)
		} else {
			log.Printf("Vault connected: %s", vaultEndpoint)
		}
	} else {
		log.Println("WARN: VAULT_ENDPOINT not set — vault storage disabled")
	}

	// --- Signing key resolution (env → guardrails config → generated keyfile) ---
	// Used for both the on-disk record chain and the trust layer, so records
	// are tamper-evident even when the trust layer is disabled.
	signingKey := envOr("TRUST_SIGNING_KEY", "")
	keySource := "TRUST_SIGNING_KEY"

	// --- Recorder setup ---
	rec, err := recorder.NewWriter(*runsDir)
	if err != nil {
		log.Printf("WARN: AIR recording disabled: %v", err)
	} else {
		log.Printf("AIR records: %s", *runsDir)
	}

	// --- Gateway authentication ---
	gatewayKey := envOr("GATEWAY_KEY", "")
	if gatewayKey != "" {
		log.Println("Gateway authentication: enabled (X-Gateway-Key header required)")
	} else {
		log.Println("Gateway authentication: disabled (set GATEWAY_KEY to require auth)")
	}

	// --- Guardrails setup (opt-in) ---
	var grCfg *guardrails.Config
	var grMgr *guardrails.Manager
	guardrailsPath := envOr("GUARDRAILS_CONFIG", "")
	if guardrailsPath != "" {
		grCfg, err = guardrails.LoadConfig(guardrailsPath)
		if err != nil {
			log.Fatalf("guardrails config: %v", err)
		}
		grMgr = guardrails.NewManager(5 * time.Minute)
		log.Printf("Guardrails: enabled (%s)", guardrailsPath)
	} else {
		log.Println("Guardrails: disabled (set GUARDRAILS_CONFIG to enable)")
	}

	// Override webhook URL from env if set.
	webhookURL := envOr("WEBHOOK_URL", "")
	if webhookURL != "" && grCfg != nil {
		grCfg.Alerts.WebhookURL = webhookURL
	}

	// --- Optimization analytics (opt-in, enabled when guardrails are loaded) ---
	var analytics *guardrails.PerformanceTracker
	if grCfg != nil && grCfg.Optimization.Analytics.Enabled {
		analytics = guardrails.NewPerformanceTracker()
		log.Println("Optimization analytics: enabled")
	} else {
		log.Println("Optimization analytics: disabled")
	}

	// Finish key resolution now that the guardrails config is loaded.
	if signingKey == "" && grCfg != nil && grCfg.Trust.SigningKey != "" {
		signingKey = grCfg.Trust.SigningKey
		keySource = "guardrails config"
	}
	if signingKey == "" {
		keyPath := filepath.Join(*runsDir, ".air-signing-key")
		signingKey, err = trust.LoadOrGenerateKey(keyPath)
		if err != nil {
			log.Fatalf("signing key: %v", err)
		}
		keySource = keyPath
	}
	log.Printf("Signing key: %s", keySource)

	// --- Record chaining ---
	// Every AIR record gets a chain_seq + chain_hash verifiable by the Python
	// SDK (air-blackbox replay --verify) and the evidence bundle tooling.
	if rec != nil {
		resumedAt, err := rec.EnableChaining(signingKey)
		if err != nil {
			log.Printf("WARN: record chaining disabled: %v", err)
		} else if resumedAt > 0 {
			log.Printf("Record chain: resumed at sequence %d", resumedAt)
		} else {
			log.Println("Record chain: started")
		}
	}

	// --- Trust layer setup (opt-in) ---
	var auditChain *trust.AuditChain
	if grCfg != nil && grCfg.Trust.Enabled {
		grCfg.Trust.SigningKey = signingKey // store resolved key for export endpoint
		chainPath := filepath.Join(*runsDir, "audit-chain.jsonl")
		auditChain, err = trust.NewPersistentAuditChain(signingKey, chainPath)
		if err != nil {
			log.Printf("WARN: audit chain persistence unavailable (%v); using in-memory chain", err)
			auditChain = trust.NewAuditChain(signingKey)
		} else {
			log.Printf("Audit chain: persisted to %s (%d entries loaded)", chainPath, auditChain.Len())
		}
		log.Printf("Trust layer: enabled (frameworks: %v)", grCfg.Trust.Compliance.Frameworks)
	} else {
		log.Println("Trust layer: disabled (enable in guardrails.yaml trust section)")
	}

	// --- Proxy handler ---
	handler := proxy.Handler(proxy.Config{
		ProviderURL: *providerURL,
		Vault:       vc,
		Recorder:    rec,
		GatewayKey:  gatewayKey,
		Guardrails:  grCfg,
		Sessions:    grMgr,
		Analytics:   analytics,
		AuditChain:  auditChain,
	})

	srv := &http.Server{
		Addr:         *addr,
		Handler:      handler,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 180 * time.Second, // Allow time for slow LLM streaming responses.
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		log.Printf("AIR Blackbox Gateway listening on %s → %s", *addr, *providerURL)
		if err := srv.ListenAndServe(); err != http.ErrServerClosed {
			log.Fatalf("server: %v", err)
		}
	}()

	<-ctx.Done()
	log.Println("Shutting down...")

	shutCtx, shutCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutCancel()
	srv.Shutdown(shutCtx)
}

func initTracer(ctx context.Context) (*sdktrace.TracerProvider, error) {
	endpoint := envOr("OTEL_EXPORTER_OTLP_ENDPOINT", "")
	if endpoint == "" {
		return nil, nil
	}

	// Use OTel SDK options instead of manual gRPC connection.
	// This handles DNS resolution correctly in Docker networking.
	exporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint(endpoint),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		return nil, err
	}

	res := resource.NewWithAttributes(
		semconv.SchemaURL,
		semconv.ServiceName("air-blackbox-gateway"),
		semconv.ServiceVersion("0.1.0"),
	)

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(tp)
	log.Printf("OTel tracing: enabled (endpoint: %s)", endpoint)
	return tp, nil
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
