// Command mockllm is a mock OpenAI-compatible provider used for benchmarking.
//
// It answers /v1/chat/completions and /v1/responses with a canned payload so
// that load tests measure AIR Blackbox Gateway overhead, not provider latency.
// Pure Go standard library. No dependencies.
//
// Env:
//
//	MOCK_LISTEN      listen address (default :9100)
//	MOCK_LATENCY_MS  artificial provider latency per request (default 0)
package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"
)

const completionBody = `{
  "id": "chatcmpl-bench000000000000000000",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "bench-model",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "This is a canned benchmark completion. It is intentionally a realistic length so that response handling, hashing, and vaulting in the gateway are exercised with a plausible payload size rather than an empty string."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 64, "completion_tokens": 48, "total_tokens": 112}
}`

func main() {
	addr := envOr("MOCK_LISTEN", ":9100")
	latency := time.Duration(envInt("MOCK_LATENCY_MS", 0)) * time.Millisecond

	mux := http.NewServeMux()

	handler := func(w http.ResponseWriter, r *http.Request) {
		if latency > 0 {
			time.Sleep(latency)
		}
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, completionBody)
	}

	mux.HandleFunc("/v1/chat/completions", handler)
	mux.HandleFunc("/v1/responses", handler)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, "ok")
	})

	srv := &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	log.Printf("mockllm listening on %s (latency=%s)", addr, latency)
	if err := srv.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func envInt(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}
