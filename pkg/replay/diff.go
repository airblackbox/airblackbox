package replay

import (
	"fmt"
	"strings"
)

// DiffOp is the kind of change for a diff segment.
type DiffOp string

const (
	OpEqual  DiffOp = "equal"
	OpAdd    DiffOp = "add"    // present in replay, not in original
	OpRemove DiffOp = "remove" // present in original, not in replay
)

// DiffSegment is a run of words sharing one operation.
type DiffSegment struct {
	Op   DiffOp `json:"op"`
	Text string `json:"text"`
}

// DiffStats summarizes a semantic diff at a glance.
type DiffStats struct {
	WordsEqual   int `json:"words_equal"`
	WordsAdded   int `json:"words_added"`   // in replay only
	WordsRemoved int `json:"words_removed"` // in original only
}

// SemanticDiff is the structured comparison of an original response against
// its replay: an ordered list of segments plus summary counts.
type SemanticDiff struct {
	Segments []DiffSegment `json:"segments"`
	Stats    DiffStats     `json:"stats"`
}

// WordDiff computes a word-level diff of original vs replay using a longest
// common subsequence. Words are the semantic unit for LLM text: a one-word
// change shows as one add/remove pair, not a whole rewritten line.
func WordDiff(original, replay string) SemanticDiff {
	a := splitWords(original)
	b := splitWords(replay)

	// LCS length table. Responses are hundreds of words, so O(n*m) is fine.
	n, m := len(a), len(b)
	lcs := make([][]int, n+1)
	for i := range lcs {
		lcs[i] = make([]int, m+1)
	}
	for i := n - 1; i >= 0; i-- {
		for j := m - 1; j >= 0; j-- {
			if a[i] == b[j] {
				lcs[i][j] = lcs[i+1][j+1] + 1
			} else if lcs[i+1][j] >= lcs[i][j+1] {
				lcs[i][j] = lcs[i+1][j]
			} else {
				lcs[i][j] = lcs[i][j+1]
			}
		}
	}

	var raw []DiffSegment
	i, j := 0, 0
	for i < n && j < m {
		switch {
		case a[i] == b[j]:
			raw = append(raw, DiffSegment{OpEqual, a[i]})
			i++
			j++
		case lcs[i+1][j] >= lcs[i][j+1]:
			raw = append(raw, DiffSegment{OpRemove, a[i]})
			i++
		default:
			raw = append(raw, DiffSegment{OpAdd, b[j]})
			j++
		}
	}
	for ; i < n; i++ {
		raw = append(raw, DiffSegment{OpRemove, a[i]})
	}
	for ; j < m; j++ {
		raw = append(raw, DiffSegment{OpAdd, b[j]})
	}

	// Coalesce adjacent same-op words into segments, and tally stats.
	var stats DiffStats
	var segs []DiffSegment
	for _, s := range raw {
		switch s.Op {
		case OpEqual:
			stats.WordsEqual++
		case OpAdd:
			stats.WordsAdded++
		case OpRemove:
			stats.WordsRemoved++
		}
		if len(segs) > 0 && segs[len(segs)-1].Op == s.Op {
			segs[len(segs)-1].Text += " " + s.Text
		} else {
			segs = append(segs, DiffSegment{s.Op, s.Text})
		}
	}
	return SemanticDiff{Segments: segs, Stats: stats}
}

// splitWords tokenizes on whitespace, preserving order. Punctuation stays
// attached to words, which is fine for surfacing meaningful changes.
func splitWords(s string) []string {
	return strings.Fields(s)
}

// Render produces a human-readable inline diff. Removed words are wrapped in
// [-...-] and added words in {+...+}, so it is legible in a plain terminal,
// a log, or a code review. useColor adds ANSI red/green when true.
func (d SemanticDiff) Render(useColor bool) string {
	var b strings.Builder
	for i, s := range d.Segments {
		if i > 0 {
			b.WriteString(" ")
		}
		switch s.Op {
		case OpEqual:
			b.WriteString(s.Text)
		case OpRemove:
			if useColor {
				b.WriteString("\x1b[31m[-" + s.Text + "-]\x1b[0m")
			} else {
				b.WriteString("[-" + s.Text + "-]")
			}
		case OpAdd:
			if useColor {
				b.WriteString("\x1b[32m{+" + s.Text + "+}\x1b[0m")
			} else {
				b.WriteString("{+" + s.Text + "+}")
			}
		}
	}
	return b.String()
}

// StatLine is a one-line summary of the diff stats.
func (d SemanticDiff) StatLine() string {
	return fmt.Sprintf("%d unchanged, %d added, %d removed",
		d.Stats.WordsEqual, d.Stats.WordsAdded, d.Stats.WordsRemoved)
}
