// Package proxy implements an OpenAI-compatible reverse proxy that intercepts
// LLM calls, vaults content, emits OTel spans, and writes AIR records.
package proxy

import (
	"bytes"
	"context"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/airblackbox/gateway/pkg/guardrails"
	"github.com/airblackbox/gateway/pkg/recorder"
	"github.com/airblackbox/gateway/pkg/trust"
	"github.com/airblackbox/gateway/pkg/vault"
	"github.com/google/uuid"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

var tracer = otel.Tracer("air-blackbox-gateway")

// upstreamClient is an HTTP client with explicit timeouts for LLM provider calls.
// The default Go http.Client has no timeout, which can hang goroutines forever.
var upstreamClient = &http.Client{
	Timeout: 120 * time.Second, // LLM calls can be slow; 2 min is generous but safe.
}

// DefaultAnthropicURL is where /v1/messages is forwarded when AnthropicURL is unset.
const DefaultAnthropicURL = "https://api.anthropic.com"

// Config holds proxy configuration.
type Config struct {
	ProviderURL  string                         // e.g. https://api.openai.com (chat completions, responses)
	AnthropicURL string                         // upstream for /v1/messages ("" = DefaultAnthropicURL)
	Vault        *vault.Client                  // S3 vault for content (nil = disabled)
	Recorder     *recorder.Writer               // AIR file writer (nil = disabled)
	GatewayKey   string                         // optional API key required to use the gateway
	Guardrails   *guardrails.Config             // guardrails configuration (nil = disabled)
	Sessions     *guardrails.Manager            // session state for guardrails (nil = disabled)
	Analytics    *guardrails.PerformanceTracker // optimization analytics (nil = disabled)
	AuditChain   *trust.AuditChain              // cryptographic audit chain (nil = disabled)
	ConfigHash   string                         // agent config bundle hash stamped into records ("" = unset)
}

// Handler returns an http.Handler that proxies OpenAI-compatible requests.
func Handler(cfg Config) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("/v1/chat/completions", func(w http.ResponseWriter, r *http.Request) {
		if !authenticateGateway(w, r, cfg.GatewayKey) {
			return
		}
		handleProxy(w, r, cfg, "/v1/chat/completions")
	})

	mux.HandleFunc("/v1/responses", func(w http.ResponseWriter, r *http.Request) {
		if !authenticateGateway(w, r, cfg.GatewayKey) {
			return
		}
		handleProxy(w, r, cfg, "/v1/responses")
	})

	// Anthropic Messages API. The Anthropic SDK sends its API key as
	// x-api-key, so the gateway key may only come from X-Gateway-Key here:
	// accepting x-api-key would compare (and, if it matched, forward) the
	// wrong secret.
	mux.HandleFunc("/v1/messages", func(w http.ResponseWriter, r *http.Request) {
		if !authenticateGatewayHeader(w, r, cfg.GatewayKey, false) {
			return
		}
		handleProxy(w, r, cfg, "/v1/messages")
	})

	mux.HandleFunc("/v1/analytics", func(w http.ResponseWriter, r *http.Request) {
		if !authenticateGateway(w, r, cfg.GatewayKey) {
			return
		}
		handleAnalytics(w, r, cfg)
	})

	mux.HandleFunc("/v1/audit", func(w http.ResponseWriter, r *http.Request) {
		if !authenticateGateway(w, r, cfg.GatewayKey) {
			return
		}
		handleAudit(w, r, cfg)
	})

	mux.HandleFunc("/v1/audit/export", func(w http.ResponseWriter, r *http.Request) {
		if !authenticateGateway(w, r, cfg.GatewayKey) {
			return
		}
		handleAuditExport(w, r, cfg)
	})

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"status":"ok"}`))
	})

	return mux
}

// authenticateGateway checks the x-gateway-key header if a key is configured.
// Returns true if auth passes (or no key is configured), false if rejected.
func authenticateGateway(w http.ResponseWriter, r *http.Request, gatewayKey string) bool {
	return authenticateGatewayHeader(w, r, gatewayKey, true)
}

// authenticateGatewayHeader is authenticateGateway with control over the
// X-Api-Key fallback, which must be off for APIs that use x-api-key as the
// provider credential (Anthropic).
func authenticateGatewayHeader(w http.ResponseWriter, r *http.Request, gatewayKey string, allowAPIKeyHeader bool) bool {
	if gatewayKey == "" {
		return true // no gateway auth configured
	}
	provided := r.Header.Get("X-Gateway-Key")
	if provided == "" && allowAPIKeyHeader {
		provided = r.Header.Get("X-Api-Key")
	}
	if subtle.ConstantTimeCompare([]byte(provided), []byte(gatewayKey)) != 1 {
		http.Error(w, `{"error":"unauthorized: invalid or missing gateway key"}`, http.StatusUnauthorized)
		return false
	}
	return true
}

// chatRequest is the minimal OpenAI chat completion request we need to parse.
// Input carries the Responses API equivalent of Messages.
type chatRequest struct {
	Model    string          `json:"model"`
	Messages json.RawMessage `json:"messages"`
	Input    json.RawMessage `json:"input"`
	Stream   bool            `json:"stream,omitempty"`
}

// promptText returns the last user prompt regardless of API shape: chat
// completions carry it in messages, the Responses API in input.
func (r chatRequest) promptText() string {
	if text := extractPromptText(r.Messages); text != "" {
		return text
	}
	return extractResponsesInput(r.Input)
}

// chatResponse is the minimal response structure for token extraction.
type chatResponse struct {
	ID    string     `json:"id"`
	Model string     `json:"model"`
	Usage *usageJSON `json:"usage"`
}

// usageJSON reads token usage in any of the three API shapes: chat
// completions (prompt_tokens / completion_tokens / total_tokens), the
// Responses API (input_tokens / output_tokens / total_tokens) and the
// Anthropic Messages API (input_tokens / output_tokens, no total; cache
// reads and writes are counted separately and are part of the input).
type usageJSON struct {
	PromptTokens             int `json:"prompt_tokens"`
	CompletionTokens         int `json:"completion_tokens"`
	TotalTokens              int `json:"total_tokens"`
	InputTokens              int `json:"input_tokens"`
	OutputTokens             int `json:"output_tokens"`
	CacheCreationInputTokens int `json:"cache_creation_input_tokens"`
	CacheReadInputTokens     int `json:"cache_read_input_tokens"`
}

func (u *usageJSON) tokens() recorder.Tokens {
	if u == nil {
		return recorder.Tokens{}
	}
	prompt := u.PromptTokens
	if prompt == 0 {
		prompt = u.InputTokens + u.CacheCreationInputTokens + u.CacheReadInputTokens
	}
	completion := u.CompletionTokens
	if completion == 0 {
		completion = u.OutputTokens
	}
	total := u.TotalTokens
	if total == 0 {
		total = prompt + completion
	}
	return recorder.Tokens{Prompt: prompt, Completion: completion, Total: total}
}

func handleProxy(w http.ResponseWriter, r *http.Request, cfg Config, endpoint string) {
	start := time.Now()

	// Per-request config attestation overrides the gateway-wide hash.
	// cfg is a value copy, so this mutation is request-local.
	if h := r.Header.Get("X-Air-Config-Hash"); h != "" {
		cfg.ConfigHash = h
	}

	// Generate run ID.
	runID := uuid.New().String()

	ctx, span := tracer.Start(r.Context(), "llm.call",
		trace.WithAttributes(
			attribute.String("gen_ai.run.id", runID),
			attribute.String("gen_ai.request.endpoint", endpoint),
		),
	)
	defer span.End()

	// Read request body.
	reqBody, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, `{"error":"failed to read request"}`, http.StatusBadRequest)
		return
	}
	r.Body.Close()

	// Parse model name and check for streaming.
	var req chatRequest
	if err := json.Unmarshal(reqBody, &req); err == nil {
		span.SetAttributes(
			attribute.String("gen_ai.request.model", req.Model),
			attribute.String("gen_ai.operation.name", "chat"),
		)
		if req.Model != "" {
			span.SetName("chat " + req.Model)
		}
	}

	// Determine provider from model name.
	provider := inferProvider(req.Model, upstreamBase(cfg, endpoint))
	span.SetAttributes(
		attribute.String("gen_ai.system", provider),
		attribute.String("gen_ai.provider.name", provider),
	)

	// --- Prevention layer (opt-in) ---
	// Runs BEFORE detection. May modify the request body (PII redaction, tool filtering,
	// model downgrade) or block entirely. Returns 403 for policy blocks.
	if cfg.Guardrails != nil {
		sessionID := extractSessionID(r)
		promptText := req.promptText()
		toolNames := extractToolNames(reqBody)
		sessionTokens := 0
		if cfg.Sessions != nil {
			sessionTokens = cfg.Sessions.GetSessionTokens(sessionID)
		}

		prevResult := guardrails.EvaluatePrevention(cfg.Guardrails, reqBody, promptText, toolNames, req.Model, sessionTokens)
		if prevResult.Blocked {
			log.Printf("[prevention] blocked: %s (session=%s)", prevResult.BlockReason, sessionID)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusForbidden)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"error": map[string]interface{}{
					"type":    "prevention_policy_blocked",
					"message": prevResult.BlockReason,
				},
			})
			go guardrails.SendWebhookAlert(cfg.Guardrails.Alerts.WebhookURL, &guardrails.Violation{
				Rule:      "prevention",
				Message:   prevResult.BlockReason,
				SessionID: sessionID,
			})
			return
		}
		if prevResult.ModifiedBody != nil {
			reqBody = prevResult.ModifiedBody
			// Re-parse the modified body so downstream uses the updated model/messages.
			json.Unmarshal(reqBody, &req)
			log.Printf("[prevention] request modified: pii_redacted=%v tools_filtered=%v model_downgraded=%s",
				prevResult.PIIRedacted, prevResult.ToolsFiltered, prevResult.ModelDowngraded)
		}
	}

	// --- Optimization: model routing (opt-in) ---
	// Checks analytics data and auto-routes to a better model if the current one is struggling.
	if cfg.Guardrails != nil && cfg.Analytics != nil {
		decision := guardrails.EvaluateRouting(cfg.Guardrails.Optimization, cfg.Analytics, req.Model)
		if decision.RoutedModel != decision.OriginalModel {
			log.Printf("[optimization] model routed: %s → %s (%s: %s)",
				decision.OriginalModel, decision.RoutedModel, decision.Rule, decision.Reason)
			req.Model = decision.RoutedModel
			// Rewrite the model in the request body so upstream gets the routed model.
			var raw map[string]interface{}
			if err := json.Unmarshal(reqBody, &raw); err == nil {
				raw["model"] = decision.RoutedModel
				if rewritten, err := json.Marshal(raw); err == nil {
					reqBody = rewritten
				}
			}
			w.Header().Set("X-Model-Routed", decision.RoutedModel)
		}
	}

	// --- Detection layer (opt-in) ---
	// Catches runaway agents: token budgets, prompt loops, tool retry storms, error spirals.
	// Returns 429 for guardrail violations. Approval webhook can override blocks.
	if cfg.Guardrails != nil && cfg.Sessions != nil {
		sessionID := extractSessionID(r)
		cfg.Sessions.GetOrCreate(sessionID)

		promptText := req.promptText()
		toolNames := extractToolNames(reqBody)
		cfg.Sessions.RecordRequest(sessionID, promptText, toolNames)

		evalReq := &guardrails.EvalRequest{
			PromptText: promptText,
			ToolNames:  toolNames,
			Model:      req.Model,
		}
		if v := guardrails.Evaluate(cfg.Guardrails, cfg.Sessions, sessionID, evalReq); v != nil {
			// Check approval webhook before blocking.
			approved, _ := guardrails.RequestApproval(r.Context(), cfg.Guardrails.Prevention.Approval, v)
			if approved {
				log.Printf("[guardrails] %s: approved via webhook (session=%s)", v.Rule, sessionID)
			} else {
				log.Printf("[guardrails] %s: %s (session=%s)", v.Rule, v.Message, sessionID)
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusTooManyRequests)
				json.NewEncoder(w).Encode(map[string]interface{}{
					"error": map[string]interface{}{
						"type":       "agent_guardrail_triggered",
						"rule":       v.Rule,
						"message":    v.Message,
						"session_id": v.SessionID,
						"details":    v.Details,
					},
				})
				go guardrails.SendWebhookAlert(cfg.Guardrails.Alerts.WebhookURL, v)
				cfg.Sessions.Remove(sessionID)
				return
			}
		}
	}

	// Forward to upstream provider.
	upstream := upstreamBase(cfg, endpoint) + endpoint
	proxyReq, err := http.NewRequestWithContext(ctx, "POST", upstream, bytes.NewReader(reqBody))
	if err != nil {
		http.Error(w, `{"error":"failed to create upstream request"}`, http.StatusInternalServerError)
		return
	}

	// Copy relevant headers.
	proxyReq.Header.Set("Content-Type", "application/json")
	if auth := r.Header.Get("Authorization"); auth != "" {
		proxyReq.Header.Set("Authorization", auth)
	}
	if endpoint == "/v1/messages" {
		// Anthropic's credential and protocol headers. Never the gateway key:
		// /v1/messages authenticates the gateway with X-Gateway-Key only.
		for _, h := range []string{"X-Api-Key", "Anthropic-Version", "Anthropic-Beta"} {
			if v := r.Header.Get(h); v != "" {
				proxyReq.Header.Set(h, v)
			}
		}
	}

	resp, err := upstreamClient.Do(proxyReq)
	if err != nil {
		span.SetAttributes(attribute.String("error", err.Error()))
		http.Error(w, fmt.Sprintf(`{"error":"upstream: %s"}`, err), http.StatusBadGateway)

		// --- Optimization: record upstream failure ---
		if cfg.Analytics != nil {
			errorType := guardrails.ClassifyFailure(502, err.Error())
			duration := time.Since(start)
			cfg.Analytics.RecordCall(req.Model, duration.Milliseconds(), 0, 0, 0, "error", errorType)
		}

		// Fire-and-forget: vault + AIR record for failed requests.
		go backgroundRecord(cfg, runID, span, req.Model, provider, endpoint,
			reqBody, nil, start, "error", err.Error())
		return
	}
	defer resp.Body.Close()

	// Set run_id header early so the client gets it even for streaming responses.
	w.Header().Set("x-run-id", runID)
	for _, h := range []string{"x-request-id", "openai-organization", "request-id"} {
		if v := resp.Header.Get(h); v != "" {
			w.Header().Set(h, v)
		}
	}

	// --- Streaming vs non-streaming response handling ---
	var tokens recorder.Tokens
	if req.Stream && strings.HasPrefix(resp.Header.Get("Content-Type"), "text/event-stream") {
		tokens = handleStreamingResponse(w, resp, cfg, runID, span, req, provider, endpoint, reqBody, start)
	} else {
		tokens = handleBufferedResponse(w, resp, cfg, runID, span, req, provider, endpoint, reqBody, start)
	}

	// Update guardrails session state after response.
	if cfg.Guardrails != nil && cfg.Sessions != nil {
		sessionID := extractSessionID(r)
		isError := resp.StatusCode >= 400
		cfg.Sessions.RecordResponse(sessionID, tokens.Total, isError)
	}
}

// handleStreamingResponse forwards SSE chunks to the client in real-time while
// capturing the full response in the background for vault storage.
// It returns the token usage extracted from the stream (zero if unavailable).
func handleStreamingResponse(w http.ResponseWriter, resp *http.Response,
	cfg Config, runID string, span trace.Span, req chatRequest,
	provider, endpoint string, reqBody []byte, start time.Time) recorder.Tokens {

	// Set streaming headers.
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.WriteHeader(resp.StatusCode)

	flusher, canFlush := w.(http.Flusher)

	// Buffer the full response for vault/recording while streaming to client.
	var fullResponse bytes.Buffer
	buf := make([]byte, 4096)

	for {
		n, err := resp.Body.Read(buf)
		if n > 0 {
			fullResponse.Write(buf[:n])
			w.Write(buf[:n])
			if canFlush {
				flusher.Flush()
			}
		}
		if err != nil {
			if err != io.EOF {
				log.Printf("[%s] stream read error: %v", runID, err)
			}
			break
		}
	}

	duration := time.Since(start)
	span.SetAttributes(attribute.Int64("gen_ai.duration_ms", duration.Milliseconds()))
	span.SetAttributes(attribute.Bool("gen_ai.stream", true))

	// Parse token usage from the final SSE chunk if available.
	// OpenAI includes usage in the last data chunk when stream_options.include_usage=true.
	respBytes := fullResponse.Bytes()
	tokens := extractStreamTokens(respBytes)
	if tokens.Total > 0 {
		span.SetAttributes(
			attribute.Int("gen_ai.usage.prompt_tokens", tokens.Prompt),
			attribute.Int("gen_ai.usage.completion_tokens", tokens.Completion),
			attribute.Int("gen_ai.usage.input_tokens", tokens.Prompt),
			attribute.Int("gen_ai.usage.output_tokens", tokens.Completion),
		)
	}

	status := "success"
	if resp.StatusCode >= 400 {
		status = "error"
	}

	log.Printf("[%s] %s model=%s tokens=%d duration=%dms status=%s stream=true",
		runID, endpoint, req.Model, tokens.Total, duration.Milliseconds(), status)

	// --- Optimization: record metrics + classify failures ---
	if cfg.Analytics != nil {
		errorType := ""
		if resp.StatusCode >= 400 {
			errorType = guardrails.ClassifyFailure(resp.StatusCode, string(respBytes))
		}
		cfg.Analytics.RecordCall(req.Model, duration.Milliseconds(),
			tokens.Prompt, tokens.Completion, tokens.Total, status, errorType)
	}

	// Fire-and-forget: vault + AIR record in background.
	go backgroundRecord(cfg, runID, span, req.Model, provider, endpoint,
		reqBody, respBytes, start, status, "")
	return tokens
}

// handleBufferedResponse handles traditional (non-streaming) responses.
// It returns the token usage extracted from the response (zero if unavailable).
func handleBufferedResponse(w http.ResponseWriter, resp *http.Response,
	cfg Config, runID string, span trace.Span, req chatRequest,
	provider, endpoint string, reqBody []byte, start time.Time) recorder.Tokens {

	// Read response body.
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, `{"error":"failed to read upstream response"}`, http.StatusBadGateway)
		return recorder.Tokens{}
	}

	// Extract token usage.
	var tokens recorder.Tokens
	var respParsed chatResponse
	if err := json.Unmarshal(respBody, &respParsed); err == nil && respParsed.Usage != nil {
		tokens = respParsed.Usage.tokens()
		span.SetAttributes(
			attribute.Int("gen_ai.usage.prompt_tokens", tokens.Prompt),
			attribute.Int("gen_ai.usage.completion_tokens", tokens.Completion),
			attribute.Int("gen_ai.usage.input_tokens", tokens.Prompt),
			attribute.Int("gen_ai.usage.output_tokens", tokens.Completion),
			attribute.String("gen_ai.response.model", respParsed.Model),
		)
	}

	duration := time.Since(start)
	span.SetAttributes(attribute.Int64("gen_ai.duration_ms", duration.Milliseconds()))

	status := "success"
	if resp.StatusCode >= 400 {
		status = "error"
	}

	// Return response to caller.
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(resp.StatusCode)
	w.Write(respBody)

	log.Printf("[%s] %s model=%s tokens=%d duration=%dms status=%s",
		runID, endpoint, req.Model, tokens.Total, duration.Milliseconds(), status)

	// --- Optimization: record metrics + classify failures ---
	if cfg.Analytics != nil {
		errorType := ""
		if resp.StatusCode >= 400 {
			errorType = guardrails.ClassifyFailure(resp.StatusCode, string(respBody))
			w.Header().Set("X-Error-Class", errorType)
		}
		cfg.Analytics.RecordCall(req.Model, duration.Milliseconds(),
			tokens.Prompt, tokens.Completion, tokens.Total, status, errorType)
	}

	// Fire-and-forget: vault + AIR record in background.
	go backgroundRecord(cfg, runID, span, req.Model, provider, endpoint,
		reqBody, respBody, start, status, "")
	return tokens
}

// backgroundRecord handles vault storage and AIR record writing off the hot path.
// Failures are logged but never block the response to the caller.
func backgroundRecord(cfg Config, runID string, span trace.Span,
	model, provider, endpoint string,
	reqBody, respBody []byte, start time.Time, status, errMsg string) {

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Vault the request (best-effort).
	reqRef, err := vaultStore(ctx, cfg.Vault, runID, "request.json", reqBody)
	if err != nil {
		log.Printf("[%s] vault request (background): %v", runID, err)
	}

	// Vault the response (best-effort).
	var respRef vault.Ref
	if respBody != nil {
		respRef, err = vaultStore(ctx, cfg.Vault, runID, "response.json", respBody)
		if err != nil {
			log.Printf("[%s] vault response (background): %v", runID, err)
		}
	}

	// Extract tokens from response if we have it.
	var tokens recorder.Tokens
	if respBody != nil {
		var respParsed chatResponse
		if err := json.Unmarshal(respBody, &respParsed); err == nil && respParsed.Usage != nil {
			tokens = respParsed.Usage.tokens()
		} else {
			// Try extracting from SSE stream.
			tokens = extractStreamTokens(respBody)
		}
	}

	// Write AIR record (best-effort).
	writeAIRRecord(cfg.Recorder, runID, span, model, provider, endpoint,
		reqRef, respRef, tokens, start, status, errMsg, cfg.ConfigHash)

	// Append to cryptographic audit chain (best-effort).
	if cfg.AuditChain != nil {
		recordJSON, _ := json.Marshal(map[string]interface{}{
			"run_id":    runID,
			"model":     model,
			"provider":  provider,
			"endpoint":  endpoint,
			"status":    status,
			"tokens":    tokens,
			"timestamp": start.UTC(),
		})
		cfg.AuditChain.Append(runID, recordJSON)
	}
}

// extractStreamTokens extracts token usage from an SSE stream in any of the
// three API shapes:
//   - chat completions: usage on the last data chunk (when the request set
//     stream_options.include_usage=true)
//   - Responses API: response.usage on the response.completed event
//   - Anthropic Messages: input tokens on message_start's message.usage,
//     the final output count on the last message_delta's usage
func extractStreamTokens(data []byte) recorder.Tokens {
	var anthropicIn *usageJSON
	var anthropicOut *usageJSON
	var last recorder.Tokens
	found := false
	for _, raw := range strings.Split(string(data), "\n") {
		line := strings.TrimSpace(raw)
		if !strings.HasPrefix(line, "data:") {
			continue
		}
		payload := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
		if payload == "" || payload == "[DONE]" {
			continue
		}
		var chunk struct {
			Type    string     `json:"type"`
			Usage   *usageJSON `json:"usage"`
			Message *struct {
				Usage *usageJSON `json:"usage"`
			} `json:"message"`
			Response *struct {
				Usage *usageJSON `json:"usage"`
			} `json:"response"`
		}
		if err := json.Unmarshal([]byte(payload), &chunk); err != nil {
			continue
		}
		switch {
		case chunk.Type == "message_start" && chunk.Message != nil && chunk.Message.Usage != nil:
			anthropicIn = chunk.Message.Usage
		case chunk.Type == "message_delta" && chunk.Usage != nil:
			anthropicOut = chunk.Usage
		case chunk.Response != nil && chunk.Response.Usage != nil:
			last, found = chunk.Response.Usage.tokens(), true
		case chunk.Usage != nil:
			last, found = chunk.Usage.tokens(), true
		}
	}
	if anthropicIn != nil || anthropicOut != nil {
		merged := &usageJSON{}
		if anthropicIn != nil {
			*merged = *anthropicIn
		}
		if anthropicOut != nil {
			// message_delta carries the cumulative output count; when it also
			// repeats input counts, they match message_start's.
			merged.OutputTokens = anthropicOut.OutputTokens
			if anthropicOut.InputTokens > 0 {
				merged.InputTokens = anthropicOut.InputTokens
			}
		}
		return merged.tokens()
	}
	if found {
		return last
	}
	return recorder.Tokens{}
}

// upstreamBase is where an endpoint is forwarded: /v1/messages to the
// Anthropic upstream, everything else to ProviderURL.
func upstreamBase(cfg Config, endpoint string) string {
	if endpoint == "/v1/messages" {
		return anthropicURL(cfg)
	}
	return cfg.ProviderURL
}

func anthropicURL(cfg Config) string {
	if cfg.AnthropicURL != "" {
		return strings.TrimRight(cfg.AnthropicURL, "/")
	}
	return DefaultAnthropicURL
}

func vaultStore(ctx context.Context, vc *vault.Client, runID, name string, data []byte) (vault.Ref, error) {
	if vc == nil {
		return vault.Ref{}, nil
	}
	key := runID + "/" + name
	return vc.Store(ctx, key, data)
}

func writeAIRRecord(w *recorder.Writer, runID string, span trace.Span, model, provider, endpoint string,
	reqRef, respRef vault.Ref, tokens recorder.Tokens, start time.Time, status, errMsg, configHash string) {

	if w == nil {
		return
	}

	traceID := ""
	if sc := span.SpanContext(); sc.HasTraceID() {
		traceID = sc.TraceID().String()
	}

	rec := recorder.Record{
		RunID:            runID,
		TraceID:          traceID,
		Timestamp:        start.UTC(),
		Model:            model,
		Provider:         provider,
		Endpoint:         endpoint,
		RequestVaultRef:  reqRef.URI,
		ResponseVaultRef: respRef.URI,
		RequestChecksum:  reqRef.Checksum,
		ResponseChecksum: respRef.Checksum,
		Tokens:           tokens,
		DurationMS:       time.Since(start).Milliseconds(),
		Status:           status,
		Error:            errMsg,
		ConfigHash:       configHash,
	}

	if err := w.Write(rec); err != nil {
		log.Printf("[%s] write AIR record: %v", runID, err)
	}
}

// extractSessionID derives a session identifier from the request.
// Checks X-Session-ID header first, then falls back to a hash of the Authorization header.
func extractSessionID(r *http.Request) string {
	if sid := r.Header.Get("X-Session-ID"); sid != "" {
		return sid
	}
	auth := r.Header.Get("Authorization")
	if auth != "" {
		h := sha256.Sum256([]byte(auth))
		return fmt.Sprintf("auth_%x", h[:8])
	}
	return "anonymous"
}

// extractPromptText pulls the last user message content from raw messages JSON.
func extractPromptText(messages json.RawMessage) string {
	if messages == nil {
		return ""
	}
	var msgs []struct {
		Role    string          `json:"role"`
		Content json.RawMessage `json:"content"`
	}
	if err := json.Unmarshal(messages, &msgs); err != nil {
		return ""
	}
	// Walk backwards to find the last user message.
	for i := len(msgs) - 1; i >= 0; i-- {
		if msgs[i].Role == "user" {
			// Content can be a string or an array of content parts.
			var text string
			if err := json.Unmarshal(msgs[i].Content, &text); err == nil {
				return text
			}
			// Try array of content parts.
			var parts []struct {
				Type string `json:"type"`
				Text string `json:"text"`
			}
			if err := json.Unmarshal(msgs[i].Content, &parts); err == nil {
				for _, p := range parts {
					if p.Type == "text" {
						return p.Text
					}
				}
			}
		}
	}
	return ""
}

// extractResponsesInput pulls the last user prompt from a Responses API
// input field, which is either a plain string or an array of messages whose
// content is a string or an array of typed parts.
func extractResponsesInput(input json.RawMessage) string {
	if input == nil {
		return ""
	}
	var text string
	if err := json.Unmarshal(input, &text); err == nil {
		return text
	}
	var items []struct {
		Role    string          `json:"role"`
		Content json.RawMessage `json:"content"`
	}
	if err := json.Unmarshal(input, &items); err != nil {
		return ""
	}
	for i := len(items) - 1; i >= 0; i-- {
		if items[i].Role != "user" {
			continue
		}
		var content string
		if err := json.Unmarshal(items[i].Content, &content); err == nil {
			return content
		}
		var parts []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		}
		if err := json.Unmarshal(items[i].Content, &parts); err == nil {
			for _, p := range parts {
				if p.Type == "input_text" || p.Type == "text" {
					return p.Text
				}
			}
		}
	}
	return ""
}

// extractToolNames pulls tool names from the request body. Chat completions
// nest the name under "function"; the Responses API and the Anthropic
// Messages API put it at the top level of each tool.
func extractToolNames(body []byte) []string {
	var req struct {
		Tools []json.RawMessage `json:"tools"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		return nil
	}
	var names []string
	for _, raw := range req.Tools {
		if name := guardrails.ToolName(raw); name != "" {
			names = append(names, name)
		}
	}
	return names
}

func inferProvider(model, providerURL string) string {
	model = strings.ToLower(model)
	switch {
	case strings.HasPrefix(model, "gpt"), strings.HasPrefix(model, "o1"), strings.HasPrefix(model, "o3"),
		strings.HasPrefix(model, "chatgpt"), strings.HasPrefix(model, "dall-e"):
		return "openai"
	case strings.HasPrefix(model, "claude"):
		return "anthropic"
	case strings.HasPrefix(model, "gemini"):
		return "google"
	case strings.HasPrefix(model, "mistral"), strings.HasPrefix(model, "mixtral"),
		strings.HasPrefix(model, "codestral"), strings.HasPrefix(model, "pixtral"):
		return "mistral"
	case strings.HasPrefix(model, "llama"), strings.HasPrefix(model, "meta-llama"):
		return "meta"
	case strings.HasPrefix(model, "deepseek"):
		return "deepseek"
	case strings.HasPrefix(model, "grok"):
		return "xai"
	case strings.HasPrefix(model, "command"), strings.HasPrefix(model, "embed-"),
		strings.HasPrefix(model, "rerank-"):
		return "cohere"
	case strings.HasPrefix(model, "qwen"):
		return "alibaba"
	case strings.Contains(providerURL, "openai.com"):
		return "openai"
	case strings.Contains(providerURL, "anthropic.com"):
		return "anthropic"
	case strings.Contains(providerURL, "groq.com"):
		return "groq"
	case strings.Contains(providerURL, "together.xyz"), strings.Contains(providerURL, "together.ai"):
		return "together"
	case strings.Contains(providerURL, "fireworks.ai"):
		return "fireworks"
	default:
		return "unknown"
	}
}

// handleAnalytics returns per-model performance stats as JSON.
// GET /v1/analytics — returns all models.
// GET /v1/analytics?model=gpt-4 — returns stats for a specific model.
func handleAnalytics(w http.ResponseWriter, r *http.Request, cfg Config) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if cfg.Analytics == nil {
		http.Error(w, `{"error":"analytics not enabled"}`, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")

	model := r.URL.Query().Get("model")
	if model != "" {
		stats := cfg.Analytics.GetModelStats(model)
		if stats == nil {
			http.Error(w, `{"error":"no data for model"}`, http.StatusNotFound)
			return
		}
		result := map[string]interface{}{
			"model":   stats.Model,
			"stats":   stats,
			"latency": stats.ComputeLatency(),
		}
		json.NewEncoder(w).Encode(result)
		return
	}

	// Return all models.
	allStats := cfg.Analytics.GetAllStats()
	result := map[string]interface{}{
		"models": allStats,
		"count":  len(allStats),
	}
	json.NewEncoder(w).Encode(result)
}

// handleAudit returns the audit chain status and compliance report.
// GET /v1/audit — chain integrity + compliance evaluation.
func handleAudit(w http.ResponseWriter, r *http.Request, cfg Config) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if cfg.AuditChain == nil {
		http.Error(w, `{"error":"trust layer not enabled"}`, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")

	// Verify chain integrity.
	valid, brokenAt, verifyErr := cfg.AuditChain.Verify()

	result := map[string]interface{}{
		"chain_length":    cfg.AuditChain.Len(),
		"chain_valid":     valid,
		"chain_broken_at": brokenAt,
	}
	if verifyErr != nil {
		result["chain_error"] = verifyErr.Error()
	}

	// Run compliance evaluation if guardrails config has frameworks.
	if cfg.Guardrails != nil && len(cfg.Guardrails.Trust.Compliance.Frameworks) > 0 {
		compCfg := trust.ComplianceConfig{
			Frameworks: cfg.Guardrails.Trust.Compliance.Frameworks,
		}
		hasVault := cfg.Vault != nil
		hasGuardrails := cfg.Guardrails != nil
		hasAnalytics := cfg.Analytics != nil
		report := trust.EvaluateCompliance(compCfg, cfg.AuditChain.Len(), hasVault, hasGuardrails, hasAnalytics)
		result["compliance"] = report
	}

	json.NewEncoder(w).Encode(result)
}

// handleAuditExport generates a full evidence package for regulators.
// GET /v1/audit/export — returns a signed evidence package JSON.
func handleAuditExport(w http.ResponseWriter, r *http.Request, cfg Config) {
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	if cfg.AuditChain == nil {
		http.Error(w, `{"error":"trust layer not enabled"}`, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")

	// Build compliance report.
	var compliance *trust.ComplianceReport
	if cfg.Guardrails != nil && len(cfg.Guardrails.Trust.Compliance.Frameworks) > 0 {
		compCfg := trust.ComplianceConfig{
			Frameworks: cfg.Guardrails.Trust.Compliance.Frameworks,
		}
		hasVault := cfg.Vault != nil
		hasGuardrails := cfg.Guardrails != nil
		hasAnalytics := cfg.Analytics != nil
		compliance = trust.EvaluateCompliance(compCfg, cfg.AuditChain.Len(), hasVault, hasGuardrails, hasAnalytics)
	}

	// Get signing key from guardrails config.
	signingKey := ""
	if cfg.Guardrails != nil {
		signingKey = cfg.Guardrails.Trust.SigningKey
	}

	gatewayID := "air-blackbox-gateway"
	pkg := trust.GenerateEvidencePackage(cfg.AuditChain, compliance, gatewayID, signingKey)

	json.NewEncoder(w).Encode(pkg)
}
