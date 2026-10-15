package proxy

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"github.com/airblackbox/gateway/pkg/guardrails"
	"github.com/airblackbox/gateway/pkg/recorder"
)

// capture records what an upstream mock received.
type capture struct {
	mu      sync.Mutex
	path    string
	headers http.Header
	body    []byte
	calls   int
}

func (c *capture) snapshot() (string, http.Header, []byte, int) {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.path, c.headers.Clone(), append([]byte(nil), c.body...), c.calls
}

func mockUpstream(t *testing.T, c *capture, contentType, response string) *httptest.Server {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		c.mu.Lock()
		c.path, c.headers, c.body = r.URL.Path, r.Header.Clone(), body
		c.calls++
		c.mu.Unlock()
		w.Header().Set("Content-Type", contentType)
		w.Header().Set("request-id", "req_anthropic_123")
		io.WriteString(w, response)
	}))
	t.Cleanup(srv.Close)
	return srv
}

const anthropicResponse = `{"id":"msg_01","type":"message","role":"assistant","model":"claude-sonnet-4-5",
"content":[{"type":"tool_use","id":"toolu_1","name":"lookup_order","input":{"id":"991"}}],
"stop_reason":"tool_use","usage":{"input_tokens":25,"output_tokens":15,"cache_read_input_tokens":10,"cache_creation_input_tokens":0}}`

const anthropicStream = "event: message_start\n" +
	`data: {"type":"message_start","message":{"id":"msg_01","type":"message","role":"assistant","model":"claude-sonnet-4-5","content":[],"usage":{"input_tokens":25,"output_tokens":1}}}` + "\n\n" +
	"event: content_block_start\n" +
	`data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}` + "\n\n" +
	"event: content_block_delta\n" +
	`data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}` + "\n\n" +
	"event: message_delta\n" +
	`data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":15}}` + "\n\n" +
	"event: message_stop\n" +
	`data: {"type":"message_stop"}` + "\n\n"

func messagesRequest(t *testing.T, h http.Handler, body string, headers map[string]string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest("POST", "/v1/messages", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, req)
	return w
}

func TestMessagesProxiesToAnthropicWithItsHeaders(t *testing.T) {
	var c capture
	up := mockUpstream(t, &c, "application/json", anthropicResponse)
	dir := t.TempDir()
	rec, _ := recorder.NewWriter(dir)
	h := Handler(Config{ProviderURL: "http://openai.invalid", AnthropicURL: up.URL, Recorder: rec})

	body := `{"model":"claude-sonnet-4-5","max_tokens":1024,"messages":[{"role":"user","content":"hi"}],
"tools":[{"name":"lookup_order","description":"look up","input_schema":{"type":"object"}}]}`
	w := messagesRequest(t, h, body, map[string]string{
		"x-api-key": "sk-ant-test", "anthropic-version": "2023-06-01", "anthropic-beta": "tools-2024-04-04",
	})
	if w.Code != 200 {
		t.Fatalf("status = %d, body = %s", w.Code, w.Body.String())
	}
	if w.Body.String() != anthropicResponse {
		t.Errorf("response was altered in transit")
	}
	if got := w.Header().Get("request-id"); got != "req_anthropic_123" {
		t.Errorf("request-id header not passed back: %q", got)
	}
	path, hdr, sent, _ := c.snapshot()
	if path != "/v1/messages" {
		t.Errorf("upstream path = %q, want /v1/messages", path)
	}
	for k, want := range map[string]string{"X-Api-Key": "sk-ant-test", "Anthropic-Version": "2023-06-01", "Anthropic-Beta": "tools-2024-04-04"} {
		if got := hdr.Get(k); got != want {
			t.Errorf("upstream %s = %q, want %q", k, got, want)
		}
	}
	if string(sent) != body {
		t.Errorf("request body was altered in transit")
	}

	loaded, err := recorder.Load(waitForAIRRecord(t, dir, w.Header().Get("x-run-id")))
	if err != nil {
		t.Fatal(err)
	}
	if loaded.Endpoint != "/v1/messages" || loaded.Provider != "anthropic" || loaded.Model != "claude-sonnet-4-5" {
		t.Errorf("record = endpoint %q provider %q model %q", loaded.Endpoint, loaded.Provider, loaded.Model)
	}
	// Cache reads are input tokens too: 25 + 10.
	if loaded.Tokens != (recorder.Tokens{Prompt: 35, Completion: 15, Total: 50}) {
		t.Errorf("tokens = %+v, want {35 15 50}", loaded.Tokens)
	}
}

func TestMessagesStreamingIsForwardedAndCounted(t *testing.T) {
	var c capture
	up := mockUpstream(t, &c, "text/event-stream", anthropicStream)
	dir := t.TempDir()
	rec, _ := recorder.NewWriter(dir)
	h := Handler(Config{AnthropicURL: up.URL, Recorder: rec})

	w := messagesRequest(t, h, `{"model":"claude-sonnet-4-5","max_tokens":64,"stream":true,"messages":[{"role":"user","content":"hi"}]}`,
		map[string]string{"x-api-key": "sk-ant-test", "anthropic-version": "2023-06-01"})
	if w.Code != 200 {
		t.Fatalf("status = %d", w.Code)
	}
	if w.Body.String() != anthropicStream {
		t.Errorf("stream was altered in transit")
	}
	loaded, err := recorder.Load(waitForAIRRecord(t, dir, w.Header().Get("x-run-id")))
	if err != nil {
		t.Fatal(err)
	}
	if loaded.Tokens != (recorder.Tokens{Prompt: 25, Completion: 15, Total: 40}) {
		t.Errorf("tokens = %+v, want {25 15 40}", loaded.Tokens)
	}
}

func TestOneGatewayServesBothUpstreams(t *testing.T) {
	var openai, anthropic capture
	upOpenAI := mockUpstream(t, &openai, "application/json", `{"id":"x","model":"gpt-4o","usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}`)
	upAnthropic := mockUpstream(t, &anthropic, "application/json", anthropicResponse)
	h := Handler(Config{ProviderURL: upOpenAI.URL, AnthropicURL: upAnthropic.URL})

	req := httptest.NewRequest("POST", "/v1/chat/completions", strings.NewReader(`{"model":"gpt-4o","messages":[]}`))
	h.ServeHTTP(httptest.NewRecorder(), req)
	messagesRequest(t, h, `{"model":"claude-sonnet-4-5","messages":[]}`, map[string]string{"x-api-key": "k"})

	if _, _, _, n := openai.snapshot(); n != 1 {
		t.Errorf("openai upstream calls = %d, want 1", n)
	}
	if _, _, _, n := anthropic.snapshot(); n != 1 {
		t.Errorf("anthropic upstream calls = %d, want 1", n)
	}
	if _, hdr, _, _ := openai.snapshot(); hdr.Get("X-Api-Key") != "" {
		t.Errorf("x-api-key must not be forwarded on the OpenAI route")
	}
}

func TestMessagesGatewayKeyComesOnlyFromXGatewayKey(t *testing.T) {
	var c capture
	up := mockUpstream(t, &c, "application/json", anthropicResponse)
	h := Handler(Config{AnthropicURL: up.URL, GatewayKey: "gw-secret"})

	// The Anthropic key in x-api-key is not the gateway key: rejected, and nothing is forwarded.
	if w := messagesRequest(t, h, `{"model":"claude-sonnet-4-5","messages":[]}`, map[string]string{"x-api-key": "sk-ant-test"}); w.Code != 401 {
		t.Errorf("status = %d, want 401", w.Code)
	}
	// Even the gateway key itself is not accepted from x-api-key here, so it can never be forwarded upstream.
	if w := messagesRequest(t, h, `{"model":"claude-sonnet-4-5","messages":[]}`, map[string]string{"x-api-key": "gw-secret"}); w.Code != 401 {
		t.Errorf("gateway key in x-api-key: status = %d, want 401", w.Code)
	}
	if _, _, _, n := c.snapshot(); n != 0 {
		t.Fatalf("upstream was called %d times on rejected requests", n)
	}

	w := messagesRequest(t, h, `{"model":"claude-sonnet-4-5","messages":[]}`, map[string]string{"X-Gateway-Key": "gw-secret", "x-api-key": "sk-ant-test"})
	if w.Code != 200 {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	_, hdr, _, _ := c.snapshot()
	if hdr.Get("X-Api-Key") != "sk-ant-test" {
		t.Errorf("forwarded x-api-key = %q, want the Anthropic key", hdr.Get("X-Api-Key"))
	}
	if hdr.Get("X-Gateway-Key") != "" {
		t.Errorf("the gateway key must never be forwarded upstream")
	}

	// The OpenAI routes keep accepting the gateway key from X-Api-Key, as before.
	var oc capture
	upO := mockUpstream(t, &oc, "application/json", `{}`)
	hO := Handler(Config{ProviderURL: upO.URL, GatewayKey: "gw-secret"})
	req := httptest.NewRequest("POST", "/v1/chat/completions", strings.NewReader(`{"model":"gpt-4o","messages":[]}`))
	req.Header.Set("X-Api-Key", "gw-secret")
	wO := httptest.NewRecorder()
	hO.ServeHTTP(wO, req)
	if wO.Code != 200 {
		t.Errorf("chat completions with gateway key in X-Api-Key: status = %d, want 200", wO.Code)
	}
}

func toolNamesSent(t *testing.T, body []byte) []string {
	t.Helper()
	var req struct {
		Tools []json.RawMessage `json:"tools"`
	}
	if err := json.Unmarshal(body, &req); err != nil {
		t.Fatalf("upstream body: %v", err)
	}
	var names []string
	for _, raw := range req.Tools {
		names = append(names, guardrails.ToolName(raw))
	}
	return names
}

// The tool filter must read tool names in all three shapes. Before, it read
// only function.name: Responses API tools slipped past it unfiltered, and an
// Anthropic tool list would have been emptied.
func TestToolFilterHandlesAllThreeToolShapes(t *testing.T) {
	cfg := &guardrails.Config{}
	cfg.Prevention.Tools.Enabled = true
	cfg.Prevention.Tools.Blocklist = []string{"delete_records"}

	cases := []struct {
		endpoint string
		body     string
	}{
		{"/v1/chat/completions", `{"model":"gpt-4o","messages":[{"role":"user","content":"x"}],"tools":[
			{"type":"function","function":{"name":"lookup_order"}},{"type":"function","function":{"name":"delete_records"}}]}`},
		{"/v1/responses", `{"model":"gpt-4o","input":"x","tools":[
			{"type":"function","name":"lookup_order"},{"type":"function","name":"delete_records"}]}`},
		{"/v1/messages", `{"model":"claude-sonnet-4-5","messages":[{"role":"user","content":"x"}],"tools":[
			{"name":"lookup_order","input_schema":{"type":"object"}},{"name":"delete_records","input_schema":{"type":"object"}}]}`},
	}
	for _, tc := range cases {
		t.Run(tc.endpoint, func(t *testing.T) {
			var c capture
			up := mockUpstream(t, &c, "application/json", `{}`)
			h := Handler(Config{ProviderURL: up.URL, AnthropicURL: up.URL, Guardrails: cfg})
			req := httptest.NewRequest("POST", tc.endpoint, strings.NewReader(tc.body))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()
			h.ServeHTTP(w, req)
			if w.Code != 200 {
				t.Fatalf("status = %d, body = %s", w.Code, w.Body.String())
			}
			_, _, sent, _ := c.snapshot()
			got := toolNamesSent(t, sent)
			if len(got) != 1 || got[0] != "lookup_order" {
				t.Errorf("tools sent upstream = %v, want [lookup_order]", got)
			}
		})
	}
}

func TestResponsesAPITokensAreRecorded(t *testing.T) {
	var c capture
	up := mockUpstream(t, &c, "application/json", `{"id":"resp_1","model":"gpt-4.1","usage":{"input_tokens":30,"output_tokens":12,"total_tokens":42}}`)
	dir := t.TempDir()
	rec, _ := recorder.NewWriter(dir)
	h := Handler(Config{ProviderURL: up.URL, Recorder: rec})
	req := httptest.NewRequest("POST", "/v1/responses", strings.NewReader(`{"model":"gpt-4.1","input":"hi"}`))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, req)
	loaded, err := recorder.Load(waitForAIRRecord(t, dir, w.Header().Get("x-run-id")))
	if err != nil {
		t.Fatal(err)
	}
	if loaded.Tokens != (recorder.Tokens{Prompt: 30, Completion: 12, Total: 42}) {
		t.Errorf("tokens = %+v, want {30 12 42}", loaded.Tokens)
	}
}

func TestExtractStreamTokensAllShapes(t *testing.T) {
	cases := map[string]struct {
		stream string
		want   recorder.Tokens
	}{
		"chat completions": {
			"data: {\"choices\":[{\"delta\":{\"content\":\"hi\"}}]}\n\ndata: {\"choices\":[],\"usage\":{\"prompt_tokens\":10,\"completion_tokens\":5,\"total_tokens\":15}}\n\ndata: [DONE]\n\n",
			recorder.Tokens{Prompt: 10, Completion: 5, Total: 15},
		},
		"responses": {
			"event: response.output_text.delta\ndata: {\"type\":\"response.output_text.delta\",\"delta\":\"hi\"}\n\n" +
				"event: response.completed\ndata: {\"type\":\"response.completed\",\"response\":{\"id\":\"r\",\"usage\":{\"input_tokens\":30,\"output_tokens\":12,\"total_tokens\":42}}}\n\n",
			recorder.Tokens{Prompt: 30, Completion: 12, Total: 42},
		},
		"anthropic": {anthropicStream, recorder.Tokens{Prompt: 25, Completion: 15, Total: 40}},
		"anthropic, no space after data:": {
			"data:{\"type\":\"message_start\",\"message\":{\"usage\":{\"input_tokens\":7,\"output_tokens\":1}}}\n\ndata:{\"type\":\"message_delta\",\"usage\":{\"output_tokens\":3}}\n\n",
			recorder.Tokens{Prompt: 7, Completion: 3, Total: 10},
		},
		"no usage": {"data: {\"choices\":[]}\n\ndata: [DONE]\n\n", recorder.Tokens{}},
	}
	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			if got := extractStreamTokens([]byte(tc.stream)); got != tc.want {
				t.Errorf("got %+v, want %+v", got, tc.want)
			}
		})
	}
}

func TestToolNameAllShapes(t *testing.T) {
	for raw, want := range map[string]string{
		`{"type":"function","function":{"name":"a"}}`: "a",
		`{"type":"function","name":"b"}`:              "b",
		`{"name":"c","input_schema":{}}`:              "c",
		`{"type":"web_search_preview"}`:               "",
		`not json`:                                    "",
	} {
		if got := guardrails.ToolName(json.RawMessage(raw)); got != want {
			t.Errorf("ToolName(%s) = %q, want %q", raw, got, want)
		}
	}
}

func TestMessagesProviderComesFromTheAnthropicUpstream(t *testing.T) {
	// A model name inferProvider does not recognise falls back to the
	// upstream URL, which for /v1/messages is the Anthropic upstream.
	cfg := Config{ProviderURL: "https://api.openai.com", AnthropicURL: "https://api.anthropic.com"}
	if got := inferProvider("some-custom-model", upstreamBase(cfg, "/v1/messages")); got != "anthropic" {
		t.Errorf("provider for /v1/messages = %q, want anthropic", got)
	}
	if got := inferProvider("some-custom-model", upstreamBase(cfg, "/v1/chat/completions")); got != "openai" {
		t.Errorf("provider for chat completions = %q, want openai", got)
	}
	if got := upstreamBase(Config{}, "/v1/messages"); got != DefaultAnthropicURL {
		t.Errorf("default Anthropic upstream = %q", got)
	}
}
