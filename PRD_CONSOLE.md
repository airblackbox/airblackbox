# AIR Blackbox Console -- Product Requirements Document

**Author:** Jason Shotwell
**Date:** April 22, 2026
**Status:** Draft

## Problem Statement

Companies have built AI agents using LangChain, CrewAI, OpenAI, Anthropic, or custom code. The EU AI Act high-risk deadline is August 2, 2026 (102 days away). Most teams have no visibility into whether their AI systems meet technical requirements. The CLI scanner solves this for developers. The Console solves it for everyone else: governance leads, CTOs, compliance managers, and recruiters who built AI tools without realizing they need to comply.

## Success Metrics

- 500 free scans in first 30 days
- 50 Pro subscribers ($49/mo) by day 90
- 10 Team accounts ($199/mo) by day 90
- Target: $4,400 MRR by day 90

## User Stories

As a CTO, I want to connect my GitHub repos and see a compliance score so I can report readiness to my board.

As a governance lead, I want findings explained in plain English so I can create remediation plans without reading code.

As a recruiter who built an AI screening tool, I want to know if my tool complies with the EU AI Act so I can avoid fines.

As a team lead, I want to track compliance progress over time so I can show improvement to stakeholders.

## Scope

### IN SCOPE (MVP)

1. Landing page with pricing at /console
2. GitHub OAuth repo connection (Pro/Team)
3. Paste/upload code input (Free tier)
4. Scan dashboard showing compliance score, pass/fail by article, and plain-English findings
5. Findings detail view with explanation + suggested fix
6. Export scan report as PDF
7. Stripe payment integration (Free / Pro $49 / Team $199)
8. Scan history (last 10 for Pro, unlimited for Team)

### OUT OF SCOPE (v2)

- Multi-user team management
- Slack/Teams notifications
- Custom policy rules
- API access
- GitLab/Bitbucket connectors
- CI/CD integration from Console
- Fine-tuned model analysis (use rule-based for MVP)

## Technical Architecture

### Frontend
- Static HTML/CSS/JS (matches existing airblackbox.ai style)
- No framework needed for MVP (vanilla JS, progressive enhancement)
- Hosted on Vercel alongside existing site

### Backend
- Vercel serverless functions (Python) for scan execution
- GitHub OAuth app for repo access
- Stripe Checkout for payments
- SQLite or Vercel KV for scan history and user state

### Scan Engine
- Reuse air-blackbox Python scanner (already on PyPI)
- Run scans server-side in Vercel serverless functions
- Return structured JSON results
- Frontend renders plain-English explanations from finding codes

### Auth Flow
1. User signs up (email or GitHub OAuth)
2. Free tier: paste code or upload .py file, get one scan/month
3. Pro tier: connect GitHub repos, unlimited scans, scan history
4. Team tier: everything in Pro + team dashboard + priority support

## Pricing

| Tier | Price | Scans | Features |
|------|-------|-------|----------|
| Free | $0 | 1/month | Paste/upload only, basic report |
| Pro | $49/mo | Unlimited | GitHub connect, scan history, PDF export, plain-English findings |
| Team | $199/mo | Unlimited | Everything in Pro + 5 seats, team dashboard, priority email support |

Annual pricing: 2 months free ($490/yr Pro, $1,990/yr Team).

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Vercel serverless timeout on large repos | High | Limit scan to 50 files for Free, 500 for Pro |
| GitHub OAuth complexity | Medium | Use existing OAuth libraries, start with read-only repo access |
| Low conversion from free to paid | High | Make free scan genuinely useful, gate PDF export and history |
| Scanner accuracy concerns | Medium | Clearly state "starting point, not legal certification" |

## Security Requirements

### Code Handling
- User code is processed in memory only. Never written to disk, never stored in a database.
- Vercel serverless functions process the scan and return results. The function terminates and memory is reclaimed.
- All code input is treated as untrusted. HTML-escaped before rendering in the frontend.
- Input size limits enforced: 500KB for free tier, 5MB for Pro/Team.
- File uploads validated by extension AND content (check for Python syntax, reject binaries).

### Authentication and Tokens
- GitHub OAuth tokens encrypted at rest using AES-256-GCM before storage.
- Tokens stored in Vercel KV (encrypted) with per-user encryption keys derived from user ID + server secret.
- GitHub tokens scoped to minimum permissions: read-only repo content access.
- OAuth tokens rotated on each session. Refresh tokens stored encrypted, never in plaintext.
- All auth flows use PKCE (Proof Key for Code Exchange) for OAuth.

### Payment Security
- Stripe Checkout handles all payment processing. No card data touches our servers.
- Stripe webhook signatures verified on every callback using webhook signing secret.
- Subscription status checked server-side on every API call (never trust client-side plan info).

### API Security
- Rate limiting: Free tier 1 scan/month (enforced server-side), Pro 100 scans/day, Team 500 scans/day.
- All API endpoints require authentication (session token or API key).
- CSRF tokens required on all state-changing requests.
- Content Security Policy headers on all pages.
- All responses include: X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Strict-Transport-Security.

### XSS Prevention
- All scanner output HTML-escaped before rendering in the frontend.
- No innerHTML with unsanitized data. Use textContent or a sanitization function.
- CSP headers restrict script sources to 'self' only (no external script loading).

### Data Retention
- Scan results (scores and findings, NOT source code) retained for 90 days on Pro, 1 year on Team.
- Users can delete their scan history at any time.
- Account deletion removes all stored data within 24 hours.

## Timeline

Phase 1 (Week 1): Landing page + pricing + waitlist
Phase 2 (Week 2-3): Paste/upload scan flow (free tier working)
Phase 3 (Week 3-4): GitHub OAuth + Stripe + Pro tier
Phase 4 (Week 5): Team features + PDF export

## Open Questions

- Should the free tier require email signup or allow anonymous scans?
- What's the file size limit for paste/upload?
- Should we show competitor comparison on the pricing page?
