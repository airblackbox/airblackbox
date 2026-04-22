# Tuesday Morning Launch Checklist

**Date**: Tuesday, March 31, 2026
**Window**: 8-10am EST

---

## Order of Operations

### Step 1: Publish Dev.to Article (8:00am EST)
- Go to dev.to/new
- Paste the article from devto-scan-results-article.md
- Tags: #ai #python #opensource #euaiact
- Hit Publish

### Step 2: Submit to Hacker News (8:15am EST)
- Go to news.ycombinator.com/submit
- Title: "Show HN: I scanned 5 popular Python AI projects for EU AI Act compliance (avg: 17%)"
- URL: paste the Dev.to article link
- Immediately post the first comment from hn-show-post.md
- Stay in the comments for the first 2 hours, answer everything

### Step 3: Twitter Thread (8:30am EST)
- Tweet 1: "I scanned 5 popular open-source Python AI projects for EU AI Act compliance. Average score: 17%. The August 2026 deadline is 17 months away. Thread:"
- Tweet 2: "Browser Use (79K stars): 9.4%. RAGFlow (76K stars): 7.9%. LiteLLM (23K stars): 48%. Superlinked (15K stars): 2.5%. AIR Blackbox (self-scan): 91%."
- Tweet 3: "The weakest area across all projects: record-keeping (Art. 12). Most have basic logging but zero structured audit trails. One project had 0.3% of files with audit logging."
- Tweet 4: "The scanner is open source (Apache 2.0). Runs locally, no API keys. pip install air-blackbox. Full results and methodology: [Dev.to link]"
- Tag: @gregpr07 @mamagnus00 @LiteLLM

### Step 4: LinkedIn Post (9:00am EST)
- Post:

I scanned 5 popular open-source Python AI projects for EU AI Act technical compliance.

Average score: 17%.

These aren't obscure projects. They have a combined 193K+ GitHub stars. They're used by thousands of companies building AI products that will need to comply with the EU AI Act by August 2026.

The biggest gap across all five projects: record-keeping (Article 12). Most have basic logging, but almost none have the structured, tamper-evident audit trails the regulation expects.

The good news: these gaps are fixable. I built AIR Blackbox to help teams find and close them. It's a linter for AI governance, open source, and runs entirely on your machine.

Full results: [Dev.to link]

#AIGovernance #EUAIAct #OpenSource #Python #AICompliance

---

## After Launch

- Monitor HN comments every 15-30 minutes for the first 3 hours
- Respond to every technical question with specifics
- If anyone challenges the methodology, be honest about limitations
- Pre-empt the "you scored yourself highest" criticism by pointing to the 9% gap and explaining what's left
- Check if any of the 4 outreach targets (LiteLLM, Superlinked, Browser Use, RAGFlow) have responded to emails
- Track PyPI download numbers throughout the day at pypistats.org/packages/air-blackbox
