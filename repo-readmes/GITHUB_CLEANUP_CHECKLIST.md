# AIR Blackbox GitHub Cleanup — Execution Checklist

Every action below is specific. Copy-paste the commands and text. Check off as you go.

---

## Phase 1: Immediate (Do Today)

### 1.1 — Publish Org Profile README

The new org profile README is at `~/Desktop/gateway/repo-readmes/org-profile-README.md`.

```bash
git clone https://github.com/airblackbox/.github.git
cd .github
mkdir -p profile
cp ~/Desktop/gateway/repo-readmes/org-profile-README.md profile/README.md
git add profile/README.md
git commit -m "docs: add org profile README"
git push origin main
```

### 1.2 — Update Repo Descriptions

Go to each repo → Settings → "About" section (gear icon on the repo page, top right). Paste these one-liners:

| Repo | Description to paste |
|---|---|
| `air-trust` | `Tamper-evident audit chain for AI agents — HMAC-SHA256 integrity + Ed25519 signed handoffs` |
| `gateway` | `EU AI Act compliance scanner — 39 checks, 7 framework trust layers. pip install air-blackbox` |
| `air-blackbox-mcp` | `MCP server — EU AI Act compliance tools for Claude Desktop, Cursor, and Claude Code` |
| `air-platform` | `Docker Compose — run the full AIR Blackbox compliance stack locally` |
| `compliance-action` | `GitHub Action — EU AI Act compliance checks on every pull request` |
| `air-gate` | `Human-in-the-loop tool gating for AI agents — HMAC-SHA256 audit trail (Article 14)` |
| `airblackbox-site` | `AIR Blackbox website — airblackbox.ai` |
| `air-controls` | `Runtime visibility for AI agents — LangChain, CrewAI, AutoGen dashboards` |
| `air-controls-mcp` | `MCP server for AIR Controls — agent runtime visibility in Cursor, Claude Code` |

For ALL repos, also set:
- **Website**: `https://airblackbox.ai`
- **Topics**: `eu-ai-act`, `ai-compliance`, `python`, `audit-chain` (plus repo-specific ones)

### 1.3 — Add Second Org Owner

Go to github.com/airblackbox → Settings → Member privileges.
Invite a trusted person (even a personal alt account) as Owner. GitHub is flagging the single-owner risk.

### 1.4 — Fix Forks

| Fork | Action |
|---|---|
| `mcp-servers-fork` | **Delete or make private.** The description has AIR Blackbox marketing copy — bad etiquette. |
| `Roo-Code` | **Make private** unless actively modified. |
| `browser-use` | **Make private** unless actively modified. |
| `litellm` | **Make private** unless actively modified. |

To privatize: Repo → Settings → Danger Zone → Change visibility → Private.
To delete: Repo → Settings → Danger Zone → Delete this repository.

---

## Phase 2: Push README Updates (Today/Tomorrow)

### 2.1 — Push air-trust README (PRIORITY)

This is the repo your Twitter/LinkedIn/Dev.to posts link to.

```bash
cd ~/Desktop/gateway
rm -f .git/index.lock
git add README.md
git commit -m "docs: rewrite README to describe air-trust, not air-blackbox"
git push origin main
```

### 2.2 — Push air-blackbox-mcp README

```bash
cd ~/Desktop/air-blackbox-mcp
git add README.md
git commit -m "docs: add air-trust reference, tighten differentiators"
git push origin main
```

### 2.3 — Push air-platform README

```bash
cd ~/Desktop/air-platform  # clone first if needed: git clone https://github.com/airblackbox/air-platform.git
cp ~/Desktop/gateway/repo-readmes/air-platform-README.md README.md
git add README.md
git commit -m "docs: rewrite README — remove fictional repos, honest framing"
git push origin main
```

### 2.4 — Push gateway README

```bash
cd ~/Desktop
git clone https://github.com/airblackbox/gateway.git gateway-real
cp ~/Desktop/gateway/repo-readmes/gateway-README.md ~/Desktop/gateway-real/README.md
cd ~/Desktop/gateway-real
git add README.md
git commit -m "docs: rewrite README — describe the Go proxy"
git push origin main
```

### 2.5 — Push compliance-action README

```bash
cd ~/Desktop
git clone https://github.com/airblackbox/compliance-action.git
cp ~/Desktop/gateway/repo-readmes/compliance-action-README.md ~/Desktop/compliance-action/README.md
cd ~/Desktop/compliance-action
git add README.md
git commit -m "docs: rewrite README — practical workflow YAML"
git push origin main
```

### 2.6 — Push air-gate README

```bash
cd ~/Desktop
git clone https://github.com/airblackbox/air-gate.git
cp ~/Desktop/gateway/repo-readmes/air-gate-README.md ~/Desktop/air-gate/README.md
cd ~/Desktop/air-gate
git add README.md
git commit -m "docs: rewrite README — tool gating + audit chain"
git push origin main
```

---

## Phase 3: Pin the Right Repos

Go to github.com/airblackbox → "Customize your pins"

**Unpin:** `scanner`

**Pin (in this order):**
1. `air-trust` — your strongest technical piece
2. `gateway` — most stars (13), the scanner
3. `air-blackbox-mcp` — MCP discoverability
4. `air-platform` — 9 stars, Docker stack
5. `compliance-action` — practical CI tool
6. `air-gate` — Article 14 compliance

---

## Phase 4: Archive/Delete Empty Repos

For each repo below, go to Settings → Danger Zone.

**Archive these** (keeps them visible but clearly marked as inactive):

| Repo | Why |
|---|---|
| `scanner` | Superseded by `air-blackbox` CLI. JavaScript, 1 star. |
| `air-quality-gate` | 1 commit, no description, no stars. |
| `openclaw-air-trust` | 0 stars, overlaps with `air-trust`. |
| `air-compliance-action` | Superseded by `compliance-action`. |
| `air-compliance-checker` | Superseded by `air-blackbox` CLI. |
| `python-sdk` | Superseded by `air-blackbox` SDK. |
| `agent-episode-store` | Concept folded into `air-platform`. |
| `agent-policy-engine` | Concept folded into `air-gate`. |
| `agent-vcr` | Unreleased, 0 engagement. |
| `eval-harness` | Unreleased, 0 engagement. |
| `trace-regression-harness` | Unreleased, 0 engagement. |
| `docs` | Content lives in individual repo READMEs now. |

**Delete or make private** (truly empty/unused):
- Any repo with 0 commits or only an auto-generated initial commit
- Any fork you're not actively modifying

---

## Phase 5: Naming Convention

Target pattern: `air-<component>` for core, `air-<framework>-trust` for integrations.

| Current Name | Rename To | Why |
|---|---|---|
| `trust-crewai` | `air-crewai-trust` | Match `air-langchain-trust`, `air-adk-trust` pattern |

To rename: Repo → Settings → Repository name → Change.

**Don't rename** `gateway` or `air-trust` — they have stars/forks and renaming breaks links.

---

## Phase 6: Create GitHub Releases

For repos with tags but no releases:

```bash
# air-trust (has 7 tags)
gh release create air-trust-v0.6.1 --repo airblackbox/air-trust \
  --title "air-trust v0.6.1" \
  --notes "Security hardening + quality fixes. See CHANGELOG.md for details."

# gateway (has 4 tags) — create release for latest
gh release create v1.8.1 --repo airblackbox/gateway \
  --title "air-blackbox v1.8.1" \
  --notes "Fix version mismatch in __init__.py"
```

Repeat for `air-gate`, `air-platform`, `compliance-action` if they have tags.

---

## Phase 7: Monorepo Strategy Decision

**The core question:** Your local `gateway` folder pushes to `airblackbox/air-trust`. This means the air-trust repo contains the entire monorepo (sdk/, cmd/, collector/, training/, etc.) plus the air-trust package in a subfolder.

**Two options:**

**Option A — air-trust becomes the monorepo (current state, just own it):**
- Keep air-trust as the monorepo
- The root README describes air-trust (already done)
- Other packages (sdk, cmd, etc.) live as subdirectories
- gateway repo becomes just the Go proxy

**Option B — Separate them properly:**
- Create a clean air-trust repo with ONLY the air-trust package files
- Keep the monorepo as gateway
- This is cleaner but requires migrating git history

**Recommendation:** Option A for now. It's working. Splitting repos mid-momentum loses time. Revisit when you have contributors who need clarity.

---

## Summary of Files I've Created

All saved in `~/Desktop/gateway/repo-readmes/`:

| File | For Repo |
|---|---|
| `org-profile-README.md` | `.github/profile/README.md` (org overview page) |
| `air-platform-README.md` | `airblackbox/air-platform` |
| `gateway-README.md` | `airblackbox/gateway` |
| `compliance-action-README.md` | `airblackbox/compliance-action` |
| `air-gate-README.md` | `airblackbox/air-gate` |

Plus the root `~/Desktop/gateway/README.md` is the air-trust README (push to `airblackbox/air-trust`).

And `~/Desktop/air-blackbox-mcp/README.md` is already edited in place (push to `airblackbox/air-blackbox-mcp`).
