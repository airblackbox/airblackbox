package proxy

import (
	"encoding/json"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/airblackbox/gateway/pkg/recorder"
)

func recordsRequest(t *testing.T, cfg Config, target string, key string) (int, map[string]json.RawMessage) {
	t.Helper()
	req := httptest.NewRequest("GET", target, nil)
	if key != "" {
		req.Header.Set("X-Gateway-Key", key)
	}
	w := httptest.NewRecorder()
	Handler(cfg).ServeHTTP(w, req)
	var body map[string]json.RawMessage
	if w.Code == 200 {
		if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
			t.Fatalf("response is not JSON: %v: %s", err, w.Body.String())
		}
	}
	return w.Code, body
}

// A CLI on another machine reads the gateway's records through /v1/records,
// so it needs the key, gets the newest records first, and never the files
// that sit beside them.
func TestRecordsServesNewestRecordsBehindTheKey(t *testing.T) {
	dir := t.TempDir()
	rec, err := recorder.NewWriter(dir)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := rec.EnableChaining("records-test-key"); err != nil {
		t.Fatal(err)
	}
	for i, id := range []string{"run-old", "run-mid", "run-new"} {
		if err := rec.Write(recorder.Record{RunID: id, Model: "air-compliance", Status: "success",
			Timestamp: time.Date(2026, 11, 15, 0, 0, i, 0, time.UTC)}); err != nil {
			t.Fatal(err)
		}
		mod := time.Date(2026, 11, 15, 0, 0, i, 0, time.UTC)
		if err := os.Chtimes(filepath.Join(dir, id+".air.json"), mod, mod); err != nil {
			t.Fatal(err)
		}
	}
	// Secrets and non-record files live in the same directory.
	os.WriteFile(filepath.Join(dir, ".air-signing-key"), []byte("do-not-serve"), 0600)
	os.WriteFile(filepath.Join(dir, "audit-chain.jsonl"), []byte(`{"x":1}`), 0600)
	os.WriteFile(filepath.Join(dir, "broken.air.json"), []byte(`{not json`), 0600)

	cfg := Config{Recorder: rec, GatewayKey: "gw-secret", OTelEnabled: true}

	if code, _ := recordsRequest(t, cfg, "/v1/records", ""); code != 401 {
		t.Fatalf("no key: status = %d, want 401", code)
	}
	if code, _ := recordsRequest(t, cfg, "/v1/records", "wrong"); code != 401 {
		t.Fatalf("wrong key: status = %d, want 401", code)
	}

	code, body := recordsRequest(t, cfg, "/v1/records", "gw-secret")
	if code != 200 {
		t.Fatalf("status = %d, want 200", code)
	}
	var total int
	json.Unmarshal(body["total"], &total)
	if total != 4 { // three records and the unreadable one
		t.Errorf("total = %d, want 4", total)
	}
	var records []recorder.Record
	if err := json.Unmarshal(body["records"], &records); err != nil {
		t.Fatal(err)
	}
	if len(records) != 3 {
		t.Fatalf("got %d records, want 3", len(records))
	}
	if records[0].RunID != "run-new" || records[2].RunID != "run-old" {
		t.Errorf("order = %s, %s, %s; want newest first", records[0].RunID, records[1].RunID, records[2].RunID)
	}
	if records[0].ChainHash == "" {
		t.Errorf("records must keep their chain hash")
	}
	var features map[string]bool
	json.Unmarshal(body["features"], &features)
	if !features["chain"] || !features["otel"] || features["vault"] || features["guardrails"] {
		t.Errorf("features = %v", features)
	}
	raw, _ := json.Marshal(body)
	if strings.Contains(string(raw), "do-not-serve") {
		t.Fatal("the signing key was served")
	}

	code, body = recordsRequest(t, cfg, "/v1/records?limit=1", "gw-secret")
	json.Unmarshal(body["records"], &records)
	if code != 200 || len(records) != 1 || records[0].RunID != "run-new" {
		t.Errorf("limit=1: status %d, %d records", code, len(records))
	}
	if code, _ := recordsRequest(t, cfg, "/v1/records?limit=-1", "gw-secret"); code != 400 {
		t.Errorf("limit=-1: status = %d, want 400", code)
	}
}

func TestRecordsWithoutARecorderIs404(t *testing.T) {
	if code, _ := recordsRequest(t, Config{}, "/v1/records", ""); code != 404 {
		t.Errorf("status = %d, want 404", code)
	}
}
