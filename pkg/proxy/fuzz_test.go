package proxy

import (
	"encoding/json"
	"strings"
	"testing"
)

// knownProviders is the closed set inferProvider may return. The fuzzer
// asserts the output never escapes this set, so a new model prefix can never
// silently route traffic to an unrecognized provider string.
var knownProviders = map[string]bool{
	"openai": true, "anthropic": true, "google": true, "mistral": true,
	"meta": true, "deepseek": true, "xai": true, "cohere": true,
	"alibaba": true, "groq": true, "together": true, "fireworks": true,
	"unknown": true,
}

// FuzzInferProvider feeds arbitrary model and provider-URL strings. Invariant:
// the function never panics and always returns a value from the known set.
func FuzzInferProvider(f *testing.F) {
	f.Add("gpt-4o", "https://api.openai.com")
	f.Add("claude-3-5-sonnet", "")
	f.Add("", "")
	f.Add("GPT-4O", "")
	f.Add("gpt\x00-4o", "")
	f.Add(strings.Repeat("a", 100000), "")
	f.Add("llama3.2", "https://together.xyz")

	f.Fuzz(func(t *testing.T, model, providerURL string) {
		got := inferProvider(model, providerURL)
		if !knownProviders[got] {
			t.Fatalf("inferProvider(%q, %q) = %q, not in known set", model, providerURL, got)
		}
	})
}

// FuzzExtractPromptText feeds arbitrary bytes as the messages JSON. Invariant:
// never panics on malformed JSON, and the returned text is never longer than
// the input (it is extracted, never synthesized or amplified).
func FuzzExtractPromptText(f *testing.F) {
	f.Add([]byte(`[{"role":"user","content":"hello"}]`))
	f.Add([]byte(`[{"role":"user","content":[{"type":"text","text":"hi"}]}]`))
	f.Add([]byte(`not json`))
	f.Add([]byte(`[]`))
	f.Add([]byte(`null`))
	f.Add([]byte(`[{"role":"user","content":{"deeply":{"nested":1}}}]`))
	f.Add([]byte(`[{"role":"user"}]`))

	f.Fuzz(func(t *testing.T, data []byte) {
		got := extractPromptText(json.RawMessage(data))
		if len(got) > len(data) {
			t.Fatalf("extracted text (%d bytes) longer than input (%d bytes)", len(got), len(data))
		}
	})
}

// FuzzExtractToolNames feeds arbitrary request bodies. Invariant: never panics,
// and every returned tool name is non-empty (empty names are filtered).
func FuzzExtractToolNames(f *testing.F) {
	f.Add([]byte(`{"tools":[{"function":{"name":"get_weather"}}]}`))
	f.Add([]byte(`{"tools":[{"function":{"name":""}}]}`))
	f.Add([]byte(`garbage`))
	f.Add([]byte(`{"tools":null}`))
	f.Add([]byte(`{"tools":[{}]}`))
	f.Add([]byte(`{}`))

	f.Fuzz(func(t *testing.T, body []byte) {
		names := extractToolNames(body)
		for i, n := range names {
			if n == "" {
				t.Fatalf("tool name %d is empty, should have been filtered", i)
			}
		}
	})
}

// FuzzExtractStreamTokens feeds arbitrary SSE stream bytes. Invariant: never
// panics on malformed stream data, regardless of how the chunks are framed.
func FuzzExtractStreamTokens(f *testing.F) {
	f.Add([]byte("data: {\"usage\":{\"prompt_tokens\":5,\"completion_tokens\":3,\"total_tokens\":8}}\n"))
	f.Add([]byte("data: [DONE]\n"))
	f.Add([]byte("garbage without data prefix"))
	f.Add([]byte("data: \n"))
	f.Add([]byte("data: {malformed"))
	f.Add([]byte(""))

	f.Fuzz(func(t *testing.T, data []byte) {
		_ = extractStreamTokens(data)
	})
}
