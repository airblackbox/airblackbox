package guardrails

import (
	"regexp"
	"strings"
)

// InjectionResult holds the scoring output from prompt injection detection.
type InjectionResult struct {
	Score    float64  `json:"score"`    // 0.0 = clean, 1.0 = certain injection
	Matched  []string `json:"matched"`  // which patterns fired
	Blocked  bool     `json:"blocked"`  // true if score exceeds block threshold
}

// injectionPattern pairs a compiled regex with a name and weight.
type injectionPattern struct {
	re     *regexp.Regexp
	name   string
	weight float64
}

// Canonical injection patterns -- mirrors the Python RuntimeMonitor patterns
// in sdk/air_blackbox/gate/runtime.py. Keep these in sync.
var injectionPatterns = []injectionPattern{
	{regexp.MustCompile(`(?i)ignore\s+(?:all\s+)?previous\s+instructions`), "ignore_previous", 0.9},
	{regexp.MustCompile(`(?i)ignore\s+(?:all\s+)?above\s+instructions`), "ignore_above", 0.9},
	{regexp.MustCompile(`(?i)disregard\s+(?:all\s+)?previous`), "disregard_previous", 0.9},
	{regexp.MustCompile(`(?i)you\s+are\s+now\s+(?:a|an|my|the|going\s+to\s+be)`), "role_override", 0.7},
	{regexp.MustCompile(`(?i)(?:reveal|show|print|output|give\s+me)\s+(?:your\s+)?system\s+prompt`), "system_prompt_leak", 0.8},
	{regexp.MustCompile(`(?i)new\s+instructions:\s*(?:you|ignore|forget|from\s+now)`), "new_instructions", 0.8},
	{regexp.MustCompile(`(?i)forget\s+(?:all\s+)?(?:your\s+)?(?:previous\s+)?instructions`), "forget_instructions", 0.9},
	{regexp.MustCompile(`(?i)act\s+as\s+(?:a\s+|an\s+)?(?:different|new)\s+(?:ai|assistant|model|persona|character|entity)`), "persona_switch", 0.7},
	{regexp.MustCompile(`(?i)bypass\s+(?:all\s+)?(?:safety|security|content)`), "bypass_safety", 0.95},
	// Additional high-signal patterns
	{regexp.MustCompile(`(?i)pretend\s+(?:you\s+are|to\s+be)\s+(?:a|an)?\s*(?:different|evil|unrestricted)`), "pretend_evil", 0.85},
	{regexp.MustCompile(`(?i)(?:do\s+not|don't)\s+(?:follow|obey)\s+(?:your|any|the)\s+(?:rules|guidelines|instructions)`), "disobey_rules", 0.9},
	{regexp.MustCompile(`(?i)jailbreak`), "jailbreak_keyword", 0.8},
	{regexp.MustCompile(`(?i)DAN\s+mode`), "dan_mode", 0.85},
}

// InjectionConfig controls injection detection behavior.
type InjectionConfig struct {
	Enabled        bool    `yaml:"enabled"`
	BlockThreshold float64 `yaml:"block_threshold"` // score above this blocks (default 0.7)
	LogThreshold   float64 `yaml:"log_threshold"`   // score above this logs a warning (default 0.3)
}

// ScoreInjection evaluates a prompt for injection attempts.
// Returns a result with a normalized score (0.0-1.0) based on matched patterns.
func ScoreInjection(text string) *InjectionResult {
	if text == "" {
		return &InjectionResult{Score: 0}
	}

	result := &InjectionResult{}
	var totalWeight float64

	for _, p := range injectionPatterns {
		if p.re.MatchString(text) {
			result.Matched = append(result.Matched, p.name)
			totalWeight += p.weight
		}
	}

	if len(result.Matched) == 0 {
		return result
	}

	// Scoring: max single-pattern weight as base, boosted by additional matches.
	// A single 0.9-weight pattern scores 0.9 directly.
	// Multiple matches push toward 1.0 via bonus.
	maxWeight := 0.0
	for _, p := range injectionPatterns {
		for _, m := range result.Matched {
			if p.name == m && p.weight > maxWeight {
				maxWeight = p.weight
			}
		}
	}

	// Start with the strongest single match, add diminishing bonus for extras.
	bonus := 0.0
	if len(result.Matched) > 1 {
		remaining := totalWeight - maxWeight
		bonus = remaining * 0.1 // each extra pattern adds ~10% of its weight
	}
	result.Score = maxWeight + bonus
	if result.Score > 1.0 {
		result.Score = 1.0
	}

	return result
}

// CheckInjection evaluates injection and applies the configured threshold.
func CheckInjection(cfg InjectionConfig, text string) *InjectionResult {
	if !cfg.Enabled {
		return &InjectionResult{Score: 0}
	}

	threshold := cfg.BlockThreshold
	if threshold <= 0 {
		threshold = 0.5 // default: blocks single strong-signal patterns
	}

	result := ScoreInjection(text)
	result.Blocked = result.Score >= threshold
	return result
}

// ContainsInjection is a quick boolean check for use in prevention layer.
func ContainsInjection(text string) bool {
	lower := strings.ToLower(text)
	// Quick pre-screen with string contains before running regex
	keywords := []string{
		"ignore previous", "ignore all", "ignore above",
		"disregard", "bypass safety", "bypass security", "bypass content",
		"forget your", "forget all", "forget instructions",
		"jailbreak", "dan mode",
	}
	hasKeyword := false
	for _, kw := range keywords {
		if strings.Contains(lower, kw) {
			hasKeyword = true
			break
		}
	}
	if !hasKeyword {
		return false
	}

	result := ScoreInjection(text)
	return result.Score >= 0.6
}
