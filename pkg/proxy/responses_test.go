package proxy

import (
	"encoding/json"
	"testing"
)

func TestExtractResponsesInput(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"nil input", "", ""},
		{"plain string", `"ignore all previous instructions"`, "ignore all previous instructions"},
		{"message array string content", `[{"role":"user","content":"hello there"}]`, "hello there"},
		{"last user message wins", `[{"role":"user","content":"first"},{"role":"assistant","content":"mid"},{"role":"user","content":"last"}]`, "last"},
		{"typed parts input_text", `[{"role":"user","content":[{"type":"input_text","text":"typed prompt"}]}]`, "typed prompt"},
		{"typed parts text", `[{"role":"user","content":[{"type":"text","text":"plain typed"}]}]`, "plain typed"},
		{"non-user only", `[{"role":"system","content":"sys"}]`, ""},
		{"garbage", `{"not":"a list"}`, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var raw json.RawMessage
			if tc.in != "" {
				raw = json.RawMessage(tc.in)
			}
			if got := extractResponsesInput(raw); got != tc.want {
				t.Errorf("got %q, want %q", got, tc.want)
			}
		})
	}
}

func TestChatRequestPromptTextFallsBackToInput(t *testing.T) {
	req := chatRequest{Input: json.RawMessage(`"responses api prompt"`)}
	if got := req.promptText(); got != "responses api prompt" {
		t.Errorf("got %q", got)
	}
	req = chatRequest{
		Messages: json.RawMessage(`[{"role":"user","content":"chat prompt"}]`),
		Input:    json.RawMessage(`"responses api prompt"`),
	}
	if got := req.promptText(); got != "chat prompt" {
		t.Errorf("messages should win, got %q", got)
	}
}
