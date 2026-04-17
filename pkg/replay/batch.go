// Package replay — batch replay support.
// RunBatch loads .air.json files from a directory, replays each through the
// provider, and returns an aggregate report with per-trace drift flags.
package replay

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/airblackbox/gateway/pkg/recorder"
)

// BatchResult is the aggregate output of a batch replay run.
type BatchResult struct {
	// Summary fields.
	TotalTraces  int     `json:"total_traces"`
	Replayed     int     `json:"replayed"`
	Drifted      int     `json:"drifted"`
	Errored      int     `json:"errored"`
	PassRate     float64 `json:"pass_rate"`     // 0.0–1.0
	MeanSimilar  float64 `json:"mean_similarity"`
	OverallDrift bool    `json:"overall_drift"` // true if ANY trace drifted

	// Per-trace results, ordered by original timestamp.
	Traces []TraceResult `json:"traces"`

	// Timing.
	StartedAt  time.Time     `json:"started_at"`
	FinishedAt time.Time     `json:"finished_at"`
	DurationMS int64         `json:"duration_ms"`
}

// TraceResult wraps a single replay Result with extra metadata for the
// batch report.
type TraceResult struct {
	FilePath string  `json:"file_path"`
	Result   *Result `json:"result,omitempty"`  // nil when Error is set
	Error    string  `json:"error,omitempty"`
}

// BatchOptions extends Options with batch-specific settings.
type BatchOptions struct {
	Options            // embedded — provider URL, vault client, API key
	Last    int        // replay only the N most recent traces (0 = all)
}

// RunBatch scans dir for .air.json files, replays each, and returns a
// BatchResult with per-trace results and aggregate statistics.
func RunBatch(ctx context.Context, dir string, opts BatchOptions) (BatchResult, error) {
	br := BatchResult{StartedAt: time.Now()}

	// 1. Discover .air.json files.
	records, err := loadAllRecords(dir)
	if err != nil {
		return br, fmt.Errorf("batch: load records: %w", err)
	}
	if len(records) == 0 {
		return br, fmt.Errorf("batch: no .air.json files found in %s", dir)
	}

	// 2. Sort by timestamp descending (newest first) so --last N takes the
	//    most recent traces.
	sort.Slice(records, func(i, j int) bool {
		return records[i].rec.Timestamp.After(records[j].rec.Timestamp)
	})

	// 3. Trim to last N if requested.
	if opts.Last > 0 && opts.Last < len(records) {
		records = records[:opts.Last]
	}

	br.TotalTraces = len(records)

	// 4. Replay each trace sequentially (provider rate limits make parallel
	//    replay risky without explicit concurrency controls).
	var similaritySum float64

	for _, entry := range records {
		// Check for context cancellation between traces.
		if ctx.Err() != nil {
			break
		}

		tr := TraceResult{FilePath: entry.path}

		result, err := Run(ctx, entry.rec, opts.Options)
		if err != nil {
			tr.Error = err.Error()
			br.Errored++
		} else {
			tr.Result = &result
			br.Replayed++
			similaritySum += result.Similarity
			if result.Drift {
				br.Drifted++
			}
		}

		br.Traces = append(br.Traces, tr)
	}

	// 5. Compute aggregate stats.
	if br.Replayed > 0 {
		br.MeanSimilar = similaritySum / float64(br.Replayed)
		br.PassRate = float64(br.Replayed-br.Drifted) / float64(br.Replayed)
	}
	br.OverallDrift = br.Drifted > 0

	br.FinishedAt = time.Now()
	br.DurationMS = br.FinishedAt.Sub(br.StartedAt).Milliseconds()

	return br, nil
}

// JSON renders the BatchResult as indented JSON bytes.
func (br BatchResult) JSON() ([]byte, error) {
	return json.MarshalIndent(br, "", "  ")
}

// Text renders a human-readable summary of the batch result.
func (br BatchResult) Text() string {
	out := fmt.Sprintf("Batch Replay Report\n")
	out += fmt.Sprintf("===================\n")
	out += fmt.Sprintf("Traces:     %d\n", br.TotalTraces)
	out += fmt.Sprintf("Replayed:   %d\n", br.Replayed)
	out += fmt.Sprintf("Drifted:    %d\n", br.Drifted)
	out += fmt.Sprintf("Errored:    %d\n", br.Errored)
	out += fmt.Sprintf("Pass rate:  %.0f%%\n", br.PassRate*100)
	out += fmt.Sprintf("Mean sim:   %.2f\n", br.MeanSimilar)
	out += fmt.Sprintf("Duration:   %dms\n", br.DurationMS)
	out += "\n"

	for i, tr := range br.Traces {
		out += fmt.Sprintf("[%d] %s\n", i+1, filepath.Base(tr.FilePath))
		if tr.Error != "" {
			out += fmt.Sprintf("    ERROR: %s\n", tr.Error)
			continue
		}
		status := "PASS"
		if tr.Result.Drift {
			status = "DRIFT"
		}
		out += fmt.Sprintf("    %s  similarity=%.2f  model=%s→%s\n",
			status, tr.Result.Similarity,
			tr.Result.OriginalModel, tr.Result.ReplayModel)
		if tr.Result.Drift {
			out += fmt.Sprintf("    %s\n", tr.Result.DriftSummary)
		}
	}

	if br.OverallDrift {
		out += "\nOVERALL: DRIFT DETECTED\n"
	} else {
		out += "\nOVERALL: NO DRIFT\n"
	}

	return out
}

// --- internal helpers ---

type recordEntry struct {
	path string
	rec  recorder.Record
}

// loadAllRecords walks dir (non-recursive) and loads every .air.json file.
func loadAllRecords(dir string) ([]recordEntry, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("read dir %s: %w", dir, err)
	}

	var records []recordEntry
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		if filepath.Ext(e.Name()) != ".json" {
			continue
		}
		// Match *.air.json specifically.
		if len(e.Name()) < 9 || e.Name()[len(e.Name())-9:] != ".air.json" {
			continue
		}

		path := filepath.Join(dir, e.Name())
		rec, err := recorder.Load(path)
		if err != nil {
			// Skip malformed files but don't abort the whole batch.
			continue
		}
		records = append(records, recordEntry{path: path, rec: rec})
	}

	return records, nil
}
