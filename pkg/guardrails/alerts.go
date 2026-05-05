package guardrails

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"
)

// AlertsConfig extends AlertConfig with multi-channel support.
type PagerDutyConfig struct {
	Enabled    bool   `yaml:"enabled"`
	RoutingKey string `yaml:"routing_key"` // PagerDuty Events API v2 integration key
	Severity   string `yaml:"severity"`    // critical, error, warning, info (default: error)
}

// slackMessage is the payload format for Slack incoming webhooks.
type slackMessage struct {
	Text string `json:"text"`
}

// pagerDutyEvent is the PagerDuty Events API v2 payload.
type pagerDutyEvent struct {
	RoutingKey  string          `json:"routing_key"`
	EventAction string          `json:"event_action"` // trigger, acknowledge, resolve
	Payload     pagerDutyPayload `json:"payload"`
}

type pagerDutyPayload struct {
	Summary   string                 `json:"summary"`
	Severity  string                 `json:"severity"` // critical, error, warning, info
	Source    string                 `json:"source"`
	Component string                 `json:"component"`
	Group     string                 `json:"group"`
	Timestamp string                 `json:"timestamp"`
	CustomDetails map[string]interface{} `json:"custom_details"`
}

// SendAlert dispatches a violation alert to all configured channels.
// This is the unified entry point -- replaces direct SendWebhookAlert calls.
func SendAlert(cfg *Config, v *Violation) {
	if cfg == nil || v == nil {
		return
	}

	// Slack webhook
	if cfg.Alerts.WebhookURL != "" {
		SendWebhookAlert(cfg.Alerts.WebhookURL, v)
	}

	// PagerDuty
	if cfg.Alerts.PagerDuty.Enabled && cfg.Alerts.PagerDuty.RoutingKey != "" {
		sendPagerDutyAlert(cfg.Alerts.PagerDuty, v)
	}
}

// SendWebhookAlert posts a narrative alert to a Slack webhook URL.
// Runs in its own goroutine so it never blocks the request path.
func SendWebhookAlert(webhookURL string, v *Violation) {
	if webhookURL == "" || v == nil {
		return
	}

	go func() {
		msg := buildNarrative(v)

		payload, err := json.Marshal(slackMessage{Text: msg})
		if err != nil {
			log.Printf("[guardrails] alert marshal error: %v", err)
			return
		}

		client := &http.Client{Timeout: 10 * time.Second}
		resp, err := client.Post(webhookURL, "application/json", bytes.NewReader(payload))
		if err != nil {
			log.Printf("[guardrails] alert send error: %v", err)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode >= 300 {
			log.Printf("[guardrails] alert webhook returned %d", resp.StatusCode)
		}
	}()
}

// sendPagerDutyAlert creates an incident via PagerDuty Events API v2.
func sendPagerDutyAlert(cfg PagerDutyConfig, v *Violation) {
	go func() {
		severity := cfg.Severity
		if severity == "" {
			severity = "error"
		}

		// Map specific rules to severity overrides
		switch v.Rule {
		case "injection":
			severity = "critical"
		case "prevention":
			if strings.Contains(v.Message, "PII") {
				severity = "critical"
			}
		}

		event := pagerDutyEvent{
			RoutingKey:  cfg.RoutingKey,
			EventAction: "trigger",
			Payload: pagerDutyPayload{
				Summary:   fmt.Sprintf("[AIR Blackbox] %s: %s", ruleDisplayName(v.Rule), truncate(v.Message, 200)),
				Severity:  severity,
				Source:    "air-blackbox-gateway",
				Component: "guardrails",
				Group:     v.Rule,
				Timestamp: time.Now().UTC().Format(time.RFC3339),
				CustomDetails: map[string]interface{}{
					"rule":       v.Rule,
					"session_id": v.SessionID,
					"details":    v.Details,
				},
			},
		}

		payload, err := json.Marshal(event)
		if err != nil {
			log.Printf("[pagerduty] marshal error: %v", err)
			return
		}

		client := &http.Client{Timeout: 10 * time.Second}
		resp, err := client.Post(
			"https://events.pagerduty.com/v2/enqueue",
			"application/json",
			bytes.NewReader(payload),
		)
		if err != nil {
			log.Printf("[pagerduty] send error: %v", err)
			return
		}
		defer resp.Body.Close()

		if resp.StatusCode >= 300 {
			log.Printf("[pagerduty] API returned %d", resp.StatusCode)
		} else {
			log.Printf("[pagerduty] incident created for %s (session=%s)", v.Rule, v.SessionID)
		}
	}()
}

// buildNarrative creates a human-readable incident report from a violation.
func buildNarrative(v *Violation) string {
	var msg string

	msg += "🚨 *AI AGENT GUARDRAIL TRIGGERED*\n\n"
	msg += fmt.Sprintf("*Rule:* %s\n", ruleDisplayName(v.Rule))
	msg += fmt.Sprintf("*Session:* %s\n", v.SessionID)
	msg += fmt.Sprintf("*Time:* %s\n\n", time.Now().UTC().Format(time.RFC3339))

	msg += "*What happened:*\n"
	msg += v.Message + "\n\n"

	if len(v.Details) > 0 {
		msg += "*Details:*\n"
		for k, val := range v.Details {
			msg += fmt.Sprintf("- %s: %v\n", k, val)
		}
		msg += "\n"
	}

	msg += "*Action taken:*\n"
	msg += "Request blocked\n"
	msg += "Session flagged\n\n"

	msg += "*Recommended:* Review the agent's error handling and prompt logic."

	return msg
}

// ruleDisplayName returns a human-friendly name for a rule ID.
func ruleDisplayName(rule string) string {
	switch rule {
	case "token_budget":
		return "Token Budget Exceeded"
	case "prompt_loop":
		return "Prompt Loop Detection"
	case "tool_retry_storm":
		return "Tool Retry Storm"
	case "error_spiral":
		return "Error Retry Spiral"
	case "injection":
		return "Prompt Injection Detected"
	case "prevention":
		return "Prevention Policy"
	case "killswitch":
		return "Kill-Switch Activated"
	default:
		return rule
	}
}

func truncate(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}
