# AIR Blackbox Visual Identity Guide

## Overview

AIR Blackbox is open-source EU AI Act compliance infrastructure for autonomous AI agents. This guide keeps our visual identity consistent, distinctive, and authentically developer-first across all touchpoints.

**Core principle:** We are infrastructure, not software. Think Stripe, Vercel, or Anthropic — builder tools for builders, not marketing products.

---

## 1. Brand Positioning

### What We Are
- **Compliance infrastructure for autonomous AI agents**
- Open-source, audit-ready tooling for production AI systems
- Developer-focused. CLI-first. Local-first.

### What We Are NOT
- Marketing software
- Enterprise SaaS
- Platform play
- Consumer-facing product

### Tone & Voice
- **Builder sharing work** — honest about what we built and why
- Technically direct — no hype, no spin
- Acknowledge limitations upfront
- Show code, not pitch

### Audience
- AI / ML engineers building agents
- CTO / platform leads evaluating risk
- Compliance officers needing audit trails
- Security teams designing AI governance

---

## 2. Color Palette

### Core Colors (Keep These)

| Role | Hex | Usage |
|------|-----|-------|
| Background | `#080b14` | Page background, dark theme |
| Surface | `#0d1117` | Cards, containers, code blocks |
| Border | `#21262d` | Lines, dividers, subtle boundaries |
| Text Primary | `#e6edf3` | Headings, body copy |
| Text Secondary | `#8b949e` | Descriptions, metadata, hints |

### New Distinctive Accent System

**Primary Accent: Amber/Gold** — `#fbbf24`
- **Why:** Signals authority, trust, compliance. Not generic tech-blue. Used in badges, highlights, trust indicators.
- Hover variant: `#f59e0b` (slightly darker for interaction)
- Light variant: `#fef3c7` (for backgrounds, use sparingly)

**Alternative option (if team prefers cooler tone):**
- **Teal accent:** `#14b8a6` — signals safety + modernity, pairs well with dark background

**Semantic/Status Colors**

| Status | Hex | Meaning |
|--------|-----|---------|
| Pass / Approved | `#22c55e` | Compliance check passed, action allowed |
| Fail / Blocked | `#ef4444` | Violation detected, action blocked |
| Warning / Pending | `#eab308` | Review required, action pending |
| Info / Notice | `#06b6d4` | Informational message |
| Muted / Disabled | `#6b7280` | Inactive, secondary context |

### Palette in Action

```
✓ Compliant: bright green (#22c55e) — signals safety
✗ Blocked: bright red (#ef4444) — clear danger
⚠ Warning: yellow (#eab308) — requires attention
✔ Auto-allowed: green (#22c55e) — trust earned
```

**Usage rule:** In terminal output and CLI tools, use these colors for visual feedback. In web UI, use them sparingly—don't overwhelm with color.

---

## 3. Typography

### Font Stack

| Use | Font | Weights | Notes |
|-----|------|---------|-------|
| Headings | Inter | 700, 800, 900 | Modern, clean, already in use |
| Body | Inter | 400, 500 | Readable at small sizes |
| Code / Terminal | JetBrains Mono | 400, 500 | Monospace, developer-friendly |

### Web Sizing Scale

```
H1: 2.5rem (40px) — 700 weight
H2: 2rem (32px) — 700 weight
H3: 1.5rem (24px) — 700 weight
H4: 1.25rem (20px) — 600 weight
Body: 1rem (16px) — 400 weight
Small: 0.875rem (14px) — 400 weight
Code: 0.875rem (14px) — 400 weight, monospace
```

### Terminal Output

Terminal text is always `JetBrains Mono` 400, output to stdout. For readability:
- Keep line length under 100 characters
- Use bold for section headers (if terminal supports it)
- Use color sparingly — reserve for status indicators only

---

## 4. Logo & Wordmark

### Current Wordmark Treatment

```
AIR Blackbox
^^^^^^^       white (#e6edf3), Inter 800
        ^^^^^^^  AMBER/GOLD accent (#fbbf24), Inter 800
```

**Styling:**
- Stack on two lines: "AIR" above "Blackbox"
- Use consistent kerning (Inter handles this well)
- Minimum size: 32px height for "AIR"
- Never compress or italicize

### Icon Mark (Favicon / Avatar)

**Concept:** Simple, geometric, memorable

**Option A: Nested Boxes**
```
An open square (representing "open" compliance) 
with an inner checkmark or circuit pattern
Colors: outline in amber, inner detail in white
Favicon size: 32x32, 64x64
```

**Option B: Shield with Circuit**
```
Classic shield shape (trust, protection)
with subtle circuit/grid overlay (compliance automation)
Colors: outline amber, inner white
```

**Recommendation:** Go with Nested Boxes — more distinctive, instantly recognizable at small sizes.

### Favicon Specifications

- **Sizes needed:** 16x16, 32x32, 64x64, 192x192 (for web), 512x512 (for social)
- **Format:** PNG with transparency, or SVG
- **Color:** Amber accent (#fbbf24) on transparent background for dark mode override
- **Padding:** 1-2px internal padding at smallest sizes to prevent distortion

### GitHub Avatar / Social Profile

- Use 64x64 or 256x256 icon mark
- Round corners (8px radius)
- Place on transparent or very dark background
- Ensure readable at thumbnail size (32x32)

---

## 5. Terminal/CLI Output Style

### Color Scheme for Terminal Output

The CLI IS your product UI. Use color intentionally:

```bash
# Status indicators
✓ PASS   → bright green (#22c55e)
✗ FAIL   → bright red (#ef4444)
⚠ WARN   → yellow (#eab308)
ℹ INFO   → cyan (#06b6d4)
○ MUTED  → dim gray (#6b7280)
```

### Box Drawing for Tables & Reports

Use Unicode box-drawing characters for clean, professional output:

```
╔════════════════════════════════════════╗
║  AIR Blackbox Compliance Report        ║
╠════════════════════════════════════════╣
║ Status: PASS                      ✓    ║
║ Scan: Article 9 (Risk Management)      ║
╠════════════════════════════════════════╣
║ Findings: 0 critical                   ║
╚════════════════════════════════════════╝
```

**Box characters:**
- Horizontal: `═` (double), `─` (single)
- Vertical: `║` (double), `│` (single)
- Corners: `╔ ╗ ╚ ╝` (double), `┌ ┐ └ ┘` (single)
- Tees: `╠ ╣ ╦ ╩` (double), `├ ┤ ┬ ┴` (single)
- Cross: `╬` (double), `┼` (single)

### Banner Style for Headers

Always use double-line boxes for scan headers:

```
╔══════════════════════════════════════════════════════╗
║                  AIR Blackbox Scan                   ║
║              EU AI Act Compliance Check              ║
╚══════════════════════════════════════════════════════╝
```

Use this for any major scan operation output.

### Progressive Disclosure in CLI

Show minimal output by default, detailed on `--verbose`:

```bash
$ air scan myagent.py
✓ PASS — 5 findings, 0 critical

$ air scan myagent.py --verbose
✓ PASS — Article 9 (Risk Management)
  ✓ Try-catch blocks detected
  ✓ Fallback patterns found
  ✓ Error handling present
...
```

---

## 6. GitHub README Template

Use this structure across all 21 repositories for consistency.

### Template Structure

```markdown
# [Repo Name]

[One-sentence description — 10 words max]

<p align="center">
  <img src="demo.gif" alt="[repo name] demonstration" width="800">
</p>

[2-3 sentence expanded description. What problem does it solve? Who is it for?]

## Quick Start

\`\`\`bash
pip install [package-name]
# or
docker run -it [image-name]
\`\`\`

## What It Does

- Feature one
- Feature two
- Feature three

## Part of AIR Blackbox

AIR Blackbox is compliance infrastructure for autonomous AI agents. [Link to main docs/website]

[Standard footer with license, contributing, support links]
```

### Real Example (for air-blackbox/scan-code repo)

```markdown
# air-blackbox/scan-code

Scan Python AI agent code for EU AI Act compliance.

<p align="center">
  <img src="demo.gif" alt="scan-code demo" width="800">
</p>

Detects frameworks (LangChain, CrewAI, OpenAI), checks for trust layer presence, evaluates compliance across Articles 9–15 of the EU AI Act.

## Quick Start

\`\`\`bash
pip install air-blackbox
air scan myagent.py
\`\`\`

## What It Does

- Framework detection (LangChain, CrewAI, AutoGen, OpenAI, Haystack, LlamaIndex)
- Trust layer status check
- 6-article compliance scoring (Articles 9, 10, 11, 12, 14, 15)
- Actionable fix recommendations
- JSON output for automation

## Part of AIR Blackbox

AIR Blackbox is compliance infrastructure for autonomous AI agents. Learn more at [airblackbox.ai](https://airblackbox.ai).

---

**License:** Apache-2.0 | **Status:** Beta | **Python:** 3.10+ | **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)
```

---

## 7. Badge & Shield Standards

### Badge Set (for every repo README)

Use shields.io or similar for consistency. Place in header after title:

```markdown
# [Repo Name]

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/air-blackbox.svg)](https://pypi.org/project/air-blackbox/)
[![Status: Beta](https://img.shields.io/badge/Status-Beta-yellow.svg)](#)
```

### Badge Colors (Override shields.io defaults)

- **License:** `#4B8BBE` (Python blue)
- **Python:** `#4B8BBE` (Python blue)
- **PyPI:** `#fbbf24` (AIR amber accent)
- **Status Alpha:** `#eab308` (yellow)
- **Status Beta:** `#fbbf24` (amber)
- **Status Stable:** `#22c55e` (green)

### When to Use Each Badge

| Badge | When |
|-------|------|
| License | Every repo, top-right of README |
| Python version | Every Python repo |
| PyPI version | Only if published to PyPI |
| Status | Every repo (Alpha/Beta/Stable) |

---

## 8. Content Voice Rules

### Words We Use

- **shipped** — "We've shipped compliance scanning"
- **built** — "Built from the ground up for CI/CD"
- **open-source** — Always hyphenated, always mentioned
- **audit-ready** — Describes our output quality
- **local-first** — Describes architecture approach
- **scan, check, pass, fail** — Precise compliance language

### Words We Avoid

- ~~revolutionary~~ (We're not)
- ~~game-changing~~ (Overused, vague)
- ~~excited to announce~~ (Too marketing-speak)
- ~~proud to share~~ (Too marketing-speak)
- ~~leverage~~ (Corporate jargon)
- ~~synergy~~ (Corporate jargon)
- ~~best-in-class~~ (Vague marketing)
- ~~enterprise-grade~~ (Meaningless)

### Core Rules

1. **Always acknowledge limitations first.** If your tool doesn't catch something, say it. Builds trust.
   - "Scan catches 95% of common patterns. Here's what it misses: [list]"

2. **Code examples beat marketing copy.** Show, don't tell.
   - Bad: "Powerful compliance automation"
   - Good: `air scan myagent.py --framework langchain`

3. **Be specific about what we do.** Use concrete nouns.
   - Bad: "Provides insights into your code"
   - Good: "Detects missing error handling in tool definitions"

4. **Honest about scope.** We're not replacing legal review.
   - "AIR Blackbox flags compliance risks. A lawyer confirms interpretation."

---

## 9. Social Media Visual Style

### Screenshot Guidelines

- **Always dark theme** — use terminal aesthetic (black/dark gray background)
- **Include cursor** — shows it's interactive, real output
- **Highlight key lines** — use color boxes or arrows to draw attention
- **Keep text legible** — use terminal font at 14-16px minimum
- **Add context** — show input command + output together

### Example Screenshot

```
[Dark background - #080b14]
[Terminal prompt visible]

$ air scan myagent.py --framework langchain

╔════════════════════════════════════════╗
║  AIR Blackbox Compliance Report        ║
╠════════════════════════════════════════╣
║ Status: PASS                      ✓    ║
║ Articles 9-15: All passing             ║
╚════════════════════════════════════════╝

[Arrow pointing to green checkmark with label "Pass status"]
```

### GIFs > Static Images

GIFs show movement, real output, and are more engaging. Always provide:
- Recording of actual CLI tool running
- Duration: 3-8 seconds (shorter is better)
- 800px width (readable on mobile)
- Silent (no audio needed)

### Tools for GIFs

- **MacOS:** QuickTime + ScreenFlow, or `asciinema` (captures terminal directly)
- **Linux:** `asciinema` or `SimpleScreenRecorder`
- **Convert to GIF:** `ffmpeg` or `gifcap`

Example asciinema setup:
```bash
asciinema rec demo.cast
# Run your commands
exit
asciinema upload demo.cast
```

### Terminal Output IS Visual Identity

Don't design fancy web screenshots. Your product lives in the terminal. Terminal output is your brand asset:
- Clean, colored status indicators
- Box-drawn reports
- Readable typography
- Intentional spacing

### Social Media Post Template

```
AIR Blackbox: Compliance infrastructure for AI agents

[GIF of scan running, 4-6 seconds]

[2-3 sentence description]
- What it does
- Who uses it
- Why it matters

🔗 GitHub: [link]
📖 Docs: [link]
```

---

## 10. Implementation Checklist

### For Each New Repository

- [ ] Use standard GitHub README template (Section 6)
- [ ] Add badge row with License, Python, PyPI (if applicable), Status
- [ ] Set background colors in code blocks: `#080b14` (if possible)
- [ ] Use box-drawing characters for table headers in CLI output
- [ ] Test terminal output colors on dark + light terminals
- [ ] Add favicon (nested box icon, Section 4)
- [ ] Set GitHub avatar to icon mark (64x64, Section 4)

### For Documentation Sites

- [ ] Background: `#080b14`
- [ ] Surface (cards): `#0d1117`
- [ ] Borders: `#21262d`
- [ ] Text: `#e6edf3` (primary), `#8b949e` (secondary)
- [ ] Accent primary: `#fbbf24` (amber) for links, highlights, CTAs
- [ ] Accent hover: `#f59e0b` (darker amber)
- [ ] Use Inter for headings/body, JetBrains Mono for code
- [ ] Status indicators: green pass, red fail, yellow warning

### For CLI Tools

- [ ] Use color codes for status (green/red/yellow/cyan)
- [ ] Box-draw all major output (╔═══╗ style)
- [ ] Keep output to <100 chars per line
- [ ] Add `--verbose` flag for detailed output
- [ ] Terminal colors tested in light + dark modes

### For Marketing/Social

- [ ] GIFs of real CLI output (prefer over screenshots)
- [ ] Amber accent (#fbbf24) for highlights in images
- [ ] Dark background (#080b14) for all visuals
- [ ] Use "scan," "check," "pass," "fail" language
- [ ] Avoid marketing words (see Section 8)

---

## 11. Design System Summary (Quick Reference)

### Colors
```
Dark BG:      #080b14
Surface:      #0d1117
Border:       #21262d
Text primary: #e6edf3
Text muted:   #8b949e
Accent:       #fbbf24 (amber)
Pass:         #22c55e (green)
Fail:         #ef4444 (red)
Warn:         #eab308 (yellow)
```

### Fonts
```
Headings: Inter 700/800/900
Body:     Inter 400/500
Code:     JetBrains Mono 400/500
```

### Logo
```
AIR (white) + Blackbox (amber)
Icon: nested box, amber accent
```

### Terminal Output
```
✓ = green (#22c55e)
✗ = red (#ef4444)
⚠ = yellow (#eab308)
ℹ = cyan (#06b6d4)
```

---

## Questions? Inconsistencies?

If you find a visual element not covered here, it's probably missing. Open an issue or PR to update this guide.

**Remember:** We're infrastructure for builders. Clean, honest, technically direct. No hype.
