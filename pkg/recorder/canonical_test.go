package recorder

import "testing"

// Golden outputs generated with:
//
//	python3 -c 'import json; print(json.dumps(json.loads(SRC), sort_keys=True))'
//
// If canonicalPythonJSON drifts from Python's serialization, chain hashes stop
// verifying in the Python SDK, so these must match byte-for-byte.
func TestCanonicalPythonJSONGoldens(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{"sorted keys", `{"b":"x","a":1}`, `{"a": 1, "b": "x"}`},
		{"nested sort", `{"tokens":{"prompt":64,"completion":48,"total":112},"model":"gpt-4"}`,
			`{"model": "gpt-4", "tokens": {"completion": 48, "prompt": 64, "total": 112}}`},
		{"short escapes", `{"s":"quote \" backslash \\ slash / tab \t newline \n"}`,
			`{"s": "quote \" backslash \\ slash / tab \t newline \n"}`},
		{"non-ascii", "{\"unicode\":\"héllo wörld\"}", `{"unicode": "h\u00e9llo w\u00f6rld"}`},
		{"astral surrogate pair", "{\"emoji\":\"😀 ok\"}", `{"emoji": "\ud83d\ude00 ok"}`},
		{"control chars", `{"ctrl":"\u0001\u001f"}`, `{"ctrl": "\u0001\u001f"}`},
		{"del char", `{"d":"\u007f"}`, `{"d": "\u007f"}`},
		{"nested mixed", `{"nested":{"z":[1,2,{"y":null,"t":true,"f":false}],"a":""}}`,
			`{"nested": {"a": "", "z": [1, 2, {"f": false, "t": true, "y": null}]}}`},
		{"numbers incl big int", `{"num":0,"neg":-5,"big":9007199254740993,"flt":0.5}`,
			`{"big": 9007199254740993, "flt": 0.5, "neg": -5, "num": 0}`},
		{"empties", `{"empty_obj":{},"empty_arr":[]}`, `{"empty_arr": [], "empty_obj": {}}`},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, err := canonicalPythonJSON([]byte(tc.in))
			if err != nil {
				t.Fatalf("canonicalPythonJSON: %v", err)
			}
			if string(got) != tc.want {
				t.Errorf("mismatch\n got: %s\nwant: %s", got, tc.want)
			}
		})
	}
}

func TestCanonicalPythonJSONRealRecord(t *testing.T) {
	// A realistic AIR record as the gateway marshals it.
	in := `{"version":"1.0.0","run_id":"384def2a-3aa2-4300-82d2-9b12ea69cb42","trace_id":"","timestamp":"2026-07-03T01:24:20.707732101Z","model":"gpt-4","provider":"openai","endpoint":"/v1/chat/completions","request_vault_ref":"","response_vault_ref":"","request_checksum":"","response_checksum":"","tokens":{"prompt":64,"completion":48,"total":112},"duration_ms":2,"status":"success","chain_seq":1}`
	want := `{"chain_seq": 1, "duration_ms": 2, "endpoint": "/v1/chat/completions", "model": "gpt-4", "provider": "openai", "request_checksum": "", "request_vault_ref": "", "response_checksum": "", "response_vault_ref": "", "run_id": "384def2a-3aa2-4300-82d2-9b12ea69cb42", "status": "success", "timestamp": "2026-07-03T01:24:20.707732101Z", "tokens": {"completion": 48, "prompt": 64, "total": 112}, "trace_id": "", "version": "1.0.0"}`
	got, err := canonicalPythonJSON([]byte(in))
	if err != nil {
		t.Fatalf("canonicalPythonJSON: %v", err)
	}
	if string(got) != want {
		t.Errorf("mismatch\n got: %s\nwant: %s", got, want)
	}
}
