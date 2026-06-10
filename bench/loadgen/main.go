// Command loadgen benchmarks AIR Blackbox Gateway overhead.
//
// It sends OpenAI-style chat completion requests to a baseline URL (the mock
// provider, directly) and a target URL (the gateway, which proxies to the same
// mock provider), then reports added latency at p50/p90/p99 and throughput.
// Pure Go standard library. No dependencies.
//
// Usage:
//
//	go run ./bench/loadgen \
//	  -baseline http://mockllm:9100 \
//	  -target   http://gateway:8080 \
//	  -requests 2000 -concurrency 1,8,32 -warmup 200
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

var requestBody = []byte(`{
  "model": "bench-model",
  "messages": [
    {"role": "system", "content": "You are a benchmark assistant used to measure proxy overhead."},
    {"role": "user", "content": "Summarize the quarterly incident report and list the three highest-severity items with their root causes."}
  ]
}`)

type result struct {
	Label       string  `json:"label"`
	Concurrency int     `json:"concurrency"`
	Requests    int     `json:"requests"`
	Errors      int     `json:"errors"`
	RPS         float64 `json:"rps"`
	P50ms       float64 `json:"p50_ms"`
	P90ms       float64 `json:"p90_ms"`
	P99ms       float64 `json:"p99_ms"`
	MaxMs       float64 `json:"max_ms"`
}

func main() {
	baseline := flag.String("baseline", "", "baseline URL (mock provider, direct)")
	target := flag.String("target", "", "target URL (gateway)")
	requests := flag.Int("requests", 2000, "requests per concurrency level")
	concurrency := flag.String("concurrency", "1,8,32", "comma-separated concurrency levels")
	warmup := flag.Int("warmup", 200, "warmup requests before each measured run")
	apiKey := flag.String("key", "", "optional bearer token (GATEWAY_KEY)")
	out := flag.String("out", "results.json", "JSON results output path")
	flag.Parse()

	if *target == "" {
		log.Fatal("-target is required (gateway URL)")
	}

	levels := parseLevels(*concurrency)
	client := &http.Client{
		Timeout: 60 * time.Second,
		Transport: &http.Transport{
			MaxIdleConns:        256,
			MaxIdleConnsPerHost: 256,
		},
	}

	var all []result

	for _, c := range levels {
		var baseRes *result
		if *baseline != "" {
			r := run(client, "direct", *baseline, *apiKey, c, *requests, *warmup)
			all = append(all, r)
			baseRes = &r
		}
		gw := run(client, "gateway", *target, *apiKey, c, *requests, *warmup)
		all = append(all, gw)

		fmt.Printf("\n== concurrency %d ==\n", c)
		if baseRes != nil {
			printRow(*baseRes)
		}
		printRow(gw)
		if baseRes != nil {
			fmt.Printf("ADDED LATENCY  p50 %+.2f ms   p90 %+.2f ms   p99 %+.2f ms\n",
				gw.P50ms-baseRes.P50ms, gw.P90ms-baseRes.P90ms, gw.P99ms-baseRes.P99ms)
		}
	}

	writeResults(*out, all)
	fmt.Println("\nMarkdown table (paste into BENCHMARKS.md):")
	fmt.Println(markdown(all))
}

func run(client *http.Client, label, url, key string, concurrency, total, warmup int) result {
	endpoint := strings.TrimRight(url, "/") + "/v1/chat/completions"

	// Warmup: fill connection pools, JIT vault/recorder paths.
	doN(client, endpoint, key, min(warmup, total), max(concurrency, 1), nil)

	latencies := make([]float64, 0, total)
	var mu sync.Mutex
	var errs int64

	start := time.Now()
	doN(client, endpoint, key, total, concurrency, func(d time.Duration, ok bool) {
		if !ok {
			atomic.AddInt64(&errs, 1)
			return
		}
		mu.Lock()
		latencies = append(latencies, float64(d.Microseconds())/1000.0)
		mu.Unlock()
	})
	elapsed := time.Since(start)

	sort.Float64s(latencies)
	r := result{
		Label:       label,
		Concurrency: concurrency,
		Requests:    total,
		Errors:      int(errs),
		RPS:         float64(total) / elapsed.Seconds(),
		P50ms:       pct(latencies, 50),
		P90ms:       pct(latencies, 90),
		P99ms:       pct(latencies, 99),
	}
	if n := len(latencies); n > 0 {
		r.MaxMs = latencies[n-1]
	}
	return r
}

func doN(client *http.Client, endpoint, key string, total, concurrency int, record func(time.Duration, bool)) {
	if total <= 0 {
		return
	}
	jobs := make(chan struct{}, total)
	for i := 0; i < total; i++ {
		jobs <- struct{}{}
	}
	close(jobs)

	var wg sync.WaitGroup
	for w := 0; w < concurrency; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for range jobs {
				t0 := time.Now()
				ok := once(client, endpoint, key)
				if record != nil {
					record(time.Since(t0), ok)
				}
			}
		}()
	}
	wg.Wait()
}

func once(client *http.Client, endpoint, key string) bool {
	req, err := http.NewRequest("POST", endpoint, bytes.NewReader(requestBody))
	if err != nil {
		return false
	}
	req.Header.Set("Content-Type", "application/json")
	if key != "" {
		req.Header.Set("Authorization", "Bearer "+key)
	}
	resp, err := client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)
	return resp.StatusCode == http.StatusOK
}

func pct(sorted []float64, p int) float64 {
	if len(sorted) == 0 {
		return 0
	}
	idx := (len(sorted)*p + 99) / 100
	if idx > 0 {
		idx--
	}
	return sorted[idx]
}

func parseLevels(s string) []int {
	var out []int
	for _, part := range strings.Split(s, ",") {
		n, err := strconv.Atoi(strings.TrimSpace(part))
		if err != nil || n < 1 {
			log.Fatalf("bad concurrency value: %q", part)
		}
		out = append(out, n)
	}
	return out
}

func printRow(r result) {
	fmt.Printf("%-8s req=%d err=%d rps=%.0f  p50=%.2fms p90=%.2fms p99=%.2fms max=%.2fms\n",
		r.Label, r.Requests, r.Errors, r.RPS, r.P50ms, r.P90ms, r.P99ms, r.MaxMs)
}

func markdown(all []result) string {
	var b strings.Builder
	b.WriteString("| Path | Concurrency | RPS | p50 (ms) | p90 (ms) | p99 (ms) | Errors |\n")
	b.WriteString("|------|-------------|-----|----------|----------|----------|--------|\n")
	for _, r := range all {
		fmt.Fprintf(&b, "| %s | %d | %.0f | %.2f | %.2f | %.2f | %d |\n",
			r.Label, r.Concurrency, r.RPS, r.P50ms, r.P90ms, r.P99ms, r.Errors)
	}
	return b.String()
}

func writeResults(path string, all []result) {
	f, err := os.Create(path)
	if err != nil {
		log.Printf("warning: could not write %s: %v", path, err)
		return
	}
	defer f.Close()
	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	enc.Encode(all)
	log.Printf("results written to %s", path)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
