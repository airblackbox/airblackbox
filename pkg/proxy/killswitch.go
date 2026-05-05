package proxy

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"
)

// KillSwitch implements California SB 942's 72-hour shutdown requirement.
// When armed, it blocks all proxied requests after the deadline.
// The gateway continues serving /health and kill-switch management endpoints.
type KillSwitch struct {
	mu       sync.RWMutex
	armed    bool
	armedAt  time.Time
	deadline time.Time
	reason   string
	armedBy  string // who triggered it
}

// NewKillSwitch creates a disarmed kill-switch.
func NewKillSwitch() *KillSwitch {
	return &KillSwitch{}
}

// Arm activates the kill-switch with a 72-hour countdown.
// All proxy requests will be blocked after the deadline.
func (ks *KillSwitch) Arm(reason, armedBy string) {
	ks.mu.Lock()
	defer ks.mu.Unlock()
	ks.armed = true
	ks.armedAt = time.Now().UTC()
	ks.deadline = ks.armedAt.Add(72 * time.Hour)
	ks.reason = reason
	ks.armedBy = armedBy
	log.Printf("[killswitch] ARMED by=%s reason=%s deadline=%s", armedBy, reason, ks.deadline.Format(time.RFC3339))
}

// ArmImmediate activates the kill-switch with immediate effect (deadline = now).
func (ks *KillSwitch) ArmImmediate(reason, armedBy string) {
	ks.mu.Lock()
	defer ks.mu.Unlock()
	ks.armed = true
	ks.armedAt = time.Now().UTC()
	ks.deadline = ks.armedAt // immediate
	ks.reason = reason
	ks.armedBy = armedBy
	log.Printf("[killswitch] ARMED IMMEDIATE by=%s reason=%s", armedBy, reason)
}

// Disarm deactivates the kill-switch.
func (ks *KillSwitch) Disarm(reason, disarmedBy string) {
	ks.mu.Lock()
	defer ks.mu.Unlock()
	ks.armed = false
	log.Printf("[killswitch] DISARMED by=%s reason=%s", disarmedBy, reason)
}

// IsActive returns true if the kill-switch is armed (regardless of deadline).
func (ks *KillSwitch) IsActive() bool {
	ks.mu.RLock()
	defer ks.mu.RUnlock()
	return ks.armed
}

// ShouldBlock returns true if the kill-switch is armed AND the deadline has passed.
func (ks *KillSwitch) ShouldBlock() bool {
	ks.mu.RLock()
	defer ks.mu.RUnlock()
	return ks.armed && time.Now().UTC().After(ks.deadline)
}

// Deadline returns the shutdown deadline.
func (ks *KillSwitch) Deadline() time.Time {
	ks.mu.RLock()
	defer ks.mu.RUnlock()
	return ks.deadline
}

// Status returns the kill-switch state as a JSON-friendly map.
func (ks *KillSwitch) Status() map[string]interface{} {
	ks.mu.RLock()
	defer ks.mu.RUnlock()

	status := map[string]interface{}{
		"armed": ks.armed,
	}
	if ks.armed {
		remaining := time.Until(ks.deadline)
		if remaining < 0 {
			remaining = 0
		}
		status["armed_at"] = ks.armedAt.Format(time.RFC3339)
		status["deadline"] = ks.deadline.Format(time.RFC3339)
		status["remaining_hours"] = remaining.Hours()
		status["remaining_human"] = formatDuration(remaining)
		status["reason"] = ks.reason
		status["armed_by"] = ks.armedBy
		status["blocking"] = time.Now().UTC().After(ks.deadline)
	}
	return status
}

func formatDuration(d time.Duration) string {
	if d <= 0 {
		return "shutdown active"
	}
	hours := int(d.Hours())
	minutes := int(d.Minutes()) % 60
	if hours > 0 {
		return fmt.Sprintf("%dh %dm remaining", hours, minutes)
	}
	return fmt.Sprintf("%dm remaining", minutes)
}

// RegisterKillSwitchRoutes adds kill-switch management endpoints to the mux.
func RegisterKillSwitchRoutes(mux *http.ServeMux, ks *KillSwitch, gatewayKey string) {
	// GET /v1/killswitch - status
	mux.HandleFunc("/v1/killswitch", func(w http.ResponseWriter, r *http.Request) {
		if !authenticateGateway(w, r, gatewayKey) {
			return
		}
		if r.Method != http.MethodGet {
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(ks.Status())
	})

	// POST /v1/killswitch/arm - arm with 72h countdown
	mux.HandleFunc("/v1/killswitch/arm", func(w http.ResponseWriter, r *http.Request) {
		if !authenticateGateway(w, r, gatewayKey) {
			return
		}
		if r.Method != http.MethodPost {
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
			return
		}
		var body struct {
			Reason    string `json:"reason"`
			ArmedBy   string `json:"armed_by"`
			Immediate bool   `json:"immediate"`
		}
		json.NewDecoder(r.Body).Decode(&body)
		if body.Reason == "" {
			body.Reason = "manual trigger"
		}
		if body.ArmedBy == "" {
			body.ArmedBy = "api"
		}
		if body.Immediate {
			ks.ArmImmediate(body.Reason, body.ArmedBy)
		} else {
			ks.Arm(body.Reason, body.ArmedBy)
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(ks.Status())
	})

	// POST /v1/killswitch/disarm - disarm
	mux.HandleFunc("/v1/killswitch/disarm", func(w http.ResponseWriter, r *http.Request) {
		if !authenticateGateway(w, r, gatewayKey) {
			return
		}
		if r.Method != http.MethodPost {
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
			return
		}
		var body struct {
			Reason     string `json:"reason"`
			DisarmedBy string `json:"disarmed_by"`
		}
		json.NewDecoder(r.Body).Decode(&body)
		if body.Reason == "" {
			body.Reason = "manual disarm"
		}
		if body.DisarmedBy == "" {
			body.DisarmedBy = "api"
		}
		ks.Disarm(body.Reason, body.DisarmedBy)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(ks.Status())
	})
}
