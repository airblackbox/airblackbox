package proxy

import (
	"bytes"
	"compress/gzip"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/airblackbox/gateway/pkg/recorder"
)

// These tests cover what a field test with the real provider SDKs found:
// how the gateway behaves as a transport, not what it records on the happy
// path.

// gatewayServer runs the handler on a real server: aborting a response
// (panic(http.ErrAbortHandler)) only means something over a real connection.
func gatewayServer(t *testing.T, cfg Config) (*httptest.Server, string) {
	t.Helper()
	dir := t.TempDir()
	rec, err := recorder.NewWriter(dir)
	if err != nil {
		t.Fatal(err)
	}
	cfg.Recorder = rec
	srv := httptest.NewServer(Handler(cfg))
	t.Cleanup(srv.Close)
	return srv, dir
}

func post(t *testing.T, url string, body string, headers map[string]string) *http.Response {
	t.Helper()
	req, _ := http.NewRequest("POST", url, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { resp.Body.Close() })
	return resp
}

func loadRecord(t *testing.T, dir string, resp *http.Response) recorder.Record {
	t.Helper()
	loaded, err := recorder.Load(waitForAIRRecord(t, dir, resp.Header.Get("x-run-id")))
	if err != nil {
		t.Fatal(err)
	}
	return loaded
}

const streamStart = "event: message_start\n" +
	`data: {"type":"message_start","message":{"id":"msg_01","type":"message","role":"assistant","model":"claude-sonnet-4-5","content":[],"usage":{"input_tokens":25,"output_tokens":1}}}` + "\n\n" +
	"event: content_block_delta\n" +
	`data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hel"}}` + "\n\n"

// An upstream that breaks mid-stream must not reach the client as a normal
// end of stream (its SDK would return a truncated answer as complete), and
// must not be recorded as a success.
func TestBrokenUpstreamStreamAbortsTheClientAndIsRecordedAsAnError(t *testing.T) {
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		io.WriteString(w, streamStart)
		w.(http.Flusher).Flush()
		panic(http.ErrAbortHandler) // drop the connection mid-stream
	}))
	t.Cleanup(up.Close)
	gw, dir := gatewayServer(t, Config{AnthropicURL: up.URL})

	resp := post(t, gw.URL+"/v1/messages", `{"model":"claude-sonnet-4-5","max_tokens":64,"stream":true,"messages":[]}`, nil)
	got, err := io.ReadAll(resp.Body)
	if err == nil {
		t.Fatalf("the client read a clean end of stream after the upstream broke (%d bytes)", len(got))
	}
	if !strings.Contains(string(got), "Hel") {
		t.Errorf("the part that did arrive was not forwarded: %q", got)
	}
	r := loadRecord(t, dir, resp)
	if r.Status != "error" || !strings.Contains(r.Error, "upstream stream broke") {
		t.Errorf("record status = %q, error = %q; want an error naming the broken stream", r.Status, r.Error)
	}
}

// Anthropic reports overload inside a stream that began with 200.
func TestErrorEventInsideAStreamIsRecordedAsAnError(t *testing.T) {
	stream := streamStart + "event: error\n" +
		`data: {"type":"error","error":{"type":"overloaded_error","message":"Overloaded"}}` + "\n\n"
	var c capture
	up := mockUpstream(t, &c, "text/event-stream", stream)
	gw, dir := gatewayServer(t, Config{AnthropicURL: up.URL})

	resp := post(t, gw.URL+"/v1/messages", `{"model":"claude-sonnet-4-5","max_tokens":64,"stream":true,"messages":[]}`, nil)
	got, err := io.ReadAll(resp.Body)
	if err != nil || string(got) != stream {
		t.Fatalf("stream not forwarded intact: err=%v", err)
	}
	r := loadRecord(t, dir, resp)
	if r.Status != "error" || r.Error != "provider error in stream: overloaded_error" {
		t.Errorf("record status = %q, error = %q", r.Status, r.Error)
	}
}

func TestStreamErrorEventShapes(t *testing.T) {
	for _, tc := range []struct{ name, stream, want string }{
		{"anthropic", `data: {"type":"error","error":{"type":"overloaded_error","message":"x"}}`, "overloaded_error"},
		{"responses error", `data: {"type":"error","code":"server_error","message":"x","sequence_number":3}`, "server_error"},
		{"responses failed", `data: {"type":"response.failed","response":{"status":"failed","error":{"code":"rate_limit_exceeded","message":"x"}}}`, "rate_limit_exceeded"},
		{"chat completions", `data: {"error":{"message":"x","type":"server_error"}}`, "server_error"},
		{"completed response with error null", `data: {"type":"response.completed","response":{"status":"completed","error":null}}`, ""},
		{"chat chunk", `data: {"id":"c","object":"chat.completion.chunk","choices":[{"delta":{"content":"error"}}]}`, ""},
	} {
		if got := streamErrorEvent([]byte(tc.stream + "\n\n")); got != tc.want {
			t.Errorf("%s: got %q, want %q", tc.name, got, tc.want)
		}
	}
}

// SDK retries follow the provider's retry-after and x-should-retry; the
// gateway used to pass back only request ids, so they retried blind.
func TestProviderResponseHeadersReachTheClient(t *testing.T) {
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		for k, v := range map[string]string{
			"retry-after": "4", "x-should-retry": "false", "request-id": "req_1",
			"anthropic-ratelimit-requests-remaining": "0", "x-ratelimit-remaining-requests": "0",
			"Content-Type": "application/json",
		} {
			w.Header().Set(k, v)
		}
		w.WriteHeader(http.StatusTooManyRequests)
		io.WriteString(w, `{"type":"error","error":{"type":"rate_limit_error","message":"about the prompt: SECRET-PROMPT-TEXT"}}`)
	}))
	t.Cleanup(up.Close)
	gw, dir := gatewayServer(t, Config{AnthropicURL: up.URL})

	resp := post(t, gw.URL+"/v1/messages", `{"model":"claude-sonnet-4-5","max_tokens":8,"messages":[]}`, nil)
	if resp.StatusCode != http.StatusTooManyRequests {
		t.Fatalf("status = %d", resp.StatusCode)
	}
	for _, h := range []string{"retry-after", "x-should-retry", "request-id", "anthropic-ratelimit-requests-remaining", "x-ratelimit-remaining-requests"} {
		if resp.Header.Get(h) == "" {
			t.Errorf("%s not passed back", h)
		}
	}
	r := loadRecord(t, dir, resp)
	if r.Status != "error" || r.Error != "upstream HTTP 429 rate_limit_error" {
		t.Errorf("record error = %q; want the status and the error type", r.Error)
	}
	raw, _ := json.Marshal(r)
	if bytes.Contains(raw, []byte("SECRET-PROMPT-TEXT")) {
		t.Error("the provider's error message, which can quote the request, reached the record")
	}
}

// What upstream receives: the SDK's headers and query string, never the
// gateway's own headers or the gateway key.
func TestClientHeadersAndQueryReachTheProvider(t *testing.T) {
	var mu sync.Mutex
	var gotHeaders http.Header
	var gotQuery string
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		gotHeaders, gotQuery = r.Header.Clone(), r.URL.RawQuery
		mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		io.WriteString(w, `{"id":"x","model":"m","usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}`)
	}))
	t.Cleanup(up.Close)
	gw, _ := gatewayServer(t, Config{ProviderURL: up.URL, AnthropicURL: up.URL, GatewayKey: "gw-secret"})
	seen := func() (http.Header, string) {
		mu.Lock()
		defer mu.Unlock()
		return gotHeaders, gotQuery
	}

	post(t, gw.URL+"/v1/chat/completions?api-version=2024-10-21", `{"model":"gpt-4o","messages":[]}`, map[string]string{
		"Authorization": "Bearer sk-openai", "OpenAI-Organization": "org-1", "OpenAI-Project": "proj-1",
		"User-Agent": "OpenAI/Python 2.0", "X-Gateway-Key": "gw-secret", "X-Air-Config-Hash": "abc", "X-Session-ID": "s1",
	})
	h, q := seen()
	if q != "api-version=2024-10-21" {
		t.Errorf("query = %q", q)
	}
	for k, want := range map[string]string{"Authorization": "Bearer sk-openai", "Openai-Organization": "org-1", "Openai-Project": "proj-1", "User-Agent": "OpenAI/Python 2.0"} {
		if got := h.Get(k); got != want {
			t.Errorf("upstream %s = %q, want %q", k, got, want)
		}
	}
	for _, k := range []string{"X-Gateway-Key", "X-Air-Config-Hash", "X-Session-Id"} {
		if h.Get(k) != "" {
			t.Errorf("gateway header %s reached the provider", k)
		}
	}

	// X-Api-Key standing in for the gateway key must not be forwarded.
	post(t, gw.URL+"/v1/chat/completions", `{"model":"gpt-4o","messages":[]}`, map[string]string{
		"Authorization": "Bearer sk-openai", "X-Api-Key": "gw-secret",
	})
	if h, _ := seen(); h.Get("X-Api-Key") != "" {
		t.Error("the gateway key, sent as X-Api-Key, reached the provider")
	}

	// On /v1/messages x-api-key is the Anthropic key, and the SDK's ?beta=true goes through.
	post(t, gw.URL+"/v1/messages?beta=true", `{"model":"claude-sonnet-4-5","max_tokens":8,"messages":[]}`, map[string]string{
		"X-Api-Key": "sk-ant", "X-Gateway-Key": "gw-secret", "Anthropic-Version": "2023-06-01",
	})
	if h, q := seen(); h.Get("X-Api-Key") != "sk-ant" || q != "beta=true" || h.Get("X-Gateway-Key") != "" {
		t.Errorf("messages: x-api-key %q, query %q, gateway key forwarded: %v", h.Get("X-Api-Key"), q, h.Get("X-Gateway-Key") != "")
	}
}

// With client headers forwarded, compression must stay the transport's
// business: a gzip response is decoded, counted and passed on decoded.
func TestCompressedProviderResponseIsDecodedAndCounted(t *testing.T) {
	body := `{"id":"x","model":"gpt-4o","usage":{"prompt_tokens":7,"completion_tokens":3,"total_tokens":10}}`
	up := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if strings.Contains(r.Header.Get("Accept-Encoding"), "gzip") {
			w.Header().Set("Content-Encoding", "gzip")
			zw := gzip.NewWriter(w)
			io.WriteString(zw, body)
			zw.Close()
			return
		}
		io.WriteString(w, body)
	}))
	t.Cleanup(up.Close)
	gw, dir := gatewayServer(t, Config{ProviderURL: up.URL})

	resp := post(t, gw.URL+"/v1/chat/completions", `{"model":"gpt-4o","messages":[]}`, map[string]string{"Accept-Encoding": "br"})
	got, _ := io.ReadAll(resp.Body)
	if string(got) != body || resp.Header.Get("Content-Encoding") != "" {
		t.Errorf("client got %q with Content-Encoding %q", got, resp.Header.Get("Content-Encoding"))
	}
	if r := loadRecord(t, dir, resp); r.Tokens.Total != 10 {
		t.Errorf("tokens = %+v", r.Tokens)
	}
}

func TestUnreachableUpstreamIsAJSONError(t *testing.T) {
	gw, dir := gatewayServer(t, Config{AnthropicURL: "http://127.0.0.1:1"})
	resp := post(t, gw.URL+"/v1/messages", `{"model":"claude-sonnet-4-5","max_tokens":8,"messages":[]}`, nil)
	var parsed struct {
		Error struct{ Type, Message string } `json:"error"`
	}
	if resp.StatusCode != http.StatusBadGateway || json.NewDecoder(resp.Body).Decode(&parsed) != nil || parsed.Error.Type != "upstream_unreachable" {
		t.Errorf("status %d, error %+v", resp.StatusCode, parsed.Error)
	}
	if n := waitForAIRRecords(t, dir, 1); n != 1 {
		t.Errorf("records = %d, want 1", n)
	}
}

func TestMessagesProviderDefaultsToAnthropic(t *testing.T) {
	var c capture
	up := mockUpstream(t, &c, "application/json", anthropicResponse)
	gw, dir := gatewayServer(t, Config{AnthropicURL: up.URL}) // an internal URL, not *.anthropic.com
	for _, model := range []string{"sonnet", "us.anthropic.claude-sonnet-4-6"} {
		resp := post(t, gw.URL+"/v1/messages", `{"model":"`+model+`","max_tokens":8,"messages":[]}`, nil)
		if r := loadRecord(t, dir, resp); r.Provider != "anthropic" {
			t.Errorf("%s: provider = %q", model, r.Provider)
		}
	}
	for model, want := range map[string]string{"o4-mini": "openai", "codex-mini-latest": "openai", "text-embedding-3-small": "openai"} {
		if got := inferProvider(model, "http://internal-proxy"); got != want {
			t.Errorf("%s: provider = %q, want %q", model, got, want)
		}
	}
}

// A streamed answer can run for many minutes; only the caller's timeout
// should end it.
func TestUpstreamClientHasNoOverallTimeout(t *testing.T) {
	if upstreamClient.Timeout != 0 {
		t.Errorf("upstream client timeout = %v; an overall timeout cuts long streams", upstreamClient.Timeout)
	}
	tr := upstreamClient.Transport.(*http.Transport)
	if tr.ResponseHeaderTimeout < 10*time.Minute || tr.MaxIdleConnsPerHost < 100 {
		t.Errorf("transport: response header timeout %v, idle conns per host %d", tr.ResponseHeaderTimeout, tr.MaxIdleConnsPerHost)
	}
}
