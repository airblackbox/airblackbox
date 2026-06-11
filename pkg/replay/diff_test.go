package replay

import "testing"

func TestWordDiffIdentical(t *testing.T) {
	d := WordDiff("the quick brown fox", "the quick brown fox")
	if d.Stats.WordsAdded != 0 || d.Stats.WordsRemoved != 0 {
		t.Fatalf("identical text should have no changes, got %+v", d.Stats)
	}
	if d.Stats.WordsEqual != 4 {
		t.Fatalf("want 4 equal words, got %d", d.Stats.WordsEqual)
	}
}

func TestWordDiffSingleWordChange(t *testing.T) {
	d := WordDiff("the quick brown fox", "the quick red fox")
	if d.Stats.WordsRemoved != 1 || d.Stats.WordsAdded != 1 {
		t.Fatalf("one-word change should be 1 add + 1 remove, got %+v", d.Stats)
	}
	if d.Stats.WordsEqual != 3 {
		t.Fatalf("want 3 equal words, got %d", d.Stats.WordsEqual)
	}
	out := d.Render(false)
	if want := "[-brown-]"; !contains(out, want) {
		t.Fatalf("render missing %q: %s", want, out)
	}
	if want := "{+red+}"; !contains(out, want) {
		t.Fatalf("render missing %q: %s", want, out)
	}
}

func TestWordDiffEmptyOriginal(t *testing.T) {
	d := WordDiff("", "hello world")
	if d.Stats.WordsAdded != 2 || d.Stats.WordsRemoved != 0 {
		t.Fatalf("all-added case wrong: %+v", d.Stats)
	}
}

func TestWordDiffEmptyReplay(t *testing.T) {
	d := WordDiff("hello world", "")
	if d.Stats.WordsRemoved != 2 || d.Stats.WordsAdded != 0 {
		t.Fatalf("all-removed case wrong: %+v", d.Stats)
	}
}

func TestWordDiffBothEmpty(t *testing.T) {
	d := WordDiff("", "")
	if len(d.Segments) != 0 {
		t.Fatalf("empty/empty should have no segments, got %d", len(d.Segments))
	}
}

func TestWordDiffCoalescesRuns(t *testing.T) {
	// Two consecutive added words should coalesce into one segment.
	d := WordDiff("a d", "a b c d")
	var addSegs int
	for _, s := range d.Segments {
		if s.Op == OpAdd {
			addSegs++
			if s.Text != "b c" {
				t.Fatalf("expected coalesced 'b c', got %q", s.Text)
			}
		}
	}
	if addSegs != 1 {
		t.Fatalf("expected 1 coalesced add segment, got %d", addSegs)
	}
}

func TestRenderColorWraps(t *testing.T) {
	d := WordDiff("keep this", "keep that")
	colored := d.Render(true)
	if !contains(colored, "\x1b[32m") || !contains(colored, "\x1b[31m") {
		t.Fatalf("color render missing ANSI codes: %q", colored)
	}
	plain := d.Render(false)
	if contains(plain, "\x1b[") {
		t.Fatalf("plain render should have no ANSI codes: %q", plain)
	}
}

func contains(s, sub string) bool {
	return len(s) >= len(sub) && (indexOf(s, sub) >= 0)
}

func indexOf(s, sub string) int {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return i
		}
	}
	return -1
}
