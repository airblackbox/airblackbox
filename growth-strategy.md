# AIR Blackbox Growth Strategy
## From 13 Stars to 1,000 — The 90-Day Playbook

**Current State (April 13, 2026)**
- GitHub stars: 13
- PyPI downloads: ~14,000+
- Production users: 5
- Org members: 1 (Jason)
- Repos: 23
- Interactive demos: 6 (live scan, trust layer, audit chain, before/after, signed handoff, narrated walkthrough)
- Show HN post: drafted, ready to ship
- EU AI Act deadline: August 2, 2026 (113 days away)

**Target State (July 13, 2026)**
- GitHub stars: 500+
- PyPI downloads: 50,000+
- Production users: 25+
- Contributors: 5-10
- Email list: 500+
- Monthly site visitors: 5,000+

---

## The Core Insight

AIR Blackbox has a distribution problem, not a product problem. 14K downloads and 5 production users prove the tool works. The August 2026 deadline creates urgency that money cannot buy. Every company running AI in the EU is about to panic. You need to be the thing they find when they start searching.

The strategy has three layers: **Awareness** (get found), **Activation** (get tried), **Community** (get contributions).

---

## LAYER 1: AWARENESS — Get Found

### Channel 1: Hacker News (Week 1)

Your Show HN post is ready. This is the single highest-leverage action available right now.

**Timing**: Post Tuesday-Thursday between 8-10am EST. Tuesday or Wednesday is ideal. Avoid Mondays (crowded) and Fridays (low engagement).

**Execution checklist**:
1. Post the Show HN title: "Show HN: Open-source CLI that scans Python AI code for EU AI Act compliance"
2. Immediately post the first comment (the pre-written one addressing skepticism)
3. Stay online for 2 hours to reply to every comment personally
4. If it hits the front page, post a follow-up comment with the demo link (airblackbox.ai/demo/hub)
5. Do NOT ask friends to upvote. HN detects and penalizes vote rings.

**Expected outcome**: 20-100 stars if it hits front page. 5-15 stars if it stays in /new. Either way, you get feedback from the most technical audience on the internet.

**Follow-up**: If it does well, write a standalone HN post 2-3 weeks later with a different angle (e.g., "The EU AI Act requires audit trails for AI agents. Here is what that looks like in code").

### Channel 2: Dev.to Articles (Weeks 1-4, then ongoing)

Your competitor ark-forge/mcp-eu-ai-act is actively publishing on Dev.to. You need to be there too, and your content needs to be better because your tool is more mature.

**Publishing cadence**: 1 article per week for the first month, then biweekly.

**Article sequence**:

Week 1: "How to Check if Your Python AI Code Is EU AI Act Compliant (In 30 Seconds)"
- Tutorial format. pip install, run scan, interpret results.
- Include screenshots of the CLI output.
- Link to the live-scan demo.
- Tags: #python #ai #compliance #opensource

Week 2: "I Added EU AI Act Compliance to My LangChain App in 2 Lines of Code"
- Before/after code comparison.
- Link to the before-after demo.
- Tags: #langchain #ai #python #tutorial

Week 3: "What the EU AI Act Actually Requires From Your AI Code (Articles 9-15 Explained for Developers)"
- Educational piece. Position yourself as the expert.
- Reference AIR Blackbox as the tool that automates these checks.
- Tags: #ai #regulation #webdev #beginners

Week 4: "Building Tamper-Evident Audit Trails for AI Agents with HMAC-SHA256"
- Deep technical piece. Show the audit chain demo.
- This targets the security-minded developer audience.
- Tags: #security #ai #python #opensource

**Why this works**: Dev.to articles rank well on Google. Someone searching "EU AI Act Python compliance" in June will find your articles. Every article is a permanent inbound channel.

### Channel 3: LinkedIn (Ongoing, 3x/week)

LinkedIn is where compliance officers, CTOs, and engineering managers live. These are the people who will approve budget for compliance tooling.

**Post types (rotate)**:

Type A - Countdown posts: "113 days until the EU AI Act enforcement deadline. Here is what Article 12 requires from your AI systems." (Include a code snippet showing AIR Blackbox output.)

Type B - Technical nuggets: "Most AI governance tools cost $50K+/year. We built an open-source scanner that checks 7 frameworks for EU AI Act compliance. It is free. Here is how it works." (Link to demo.)

Type C - Engagement bait: "Poll: Is your company prepared for the EU AI Act deadline? (a) Yes, fully compliant (b) Working on it (c) What deadline? (d) We do not operate in the EU" (Follow up with how AIR Blackbox helps.)

Type D - Builds-in-public: "Just shipped multi-framework compliance mapping for AIR Blackbox. Now covers LangChain, CrewAI, OpenAI, Haystack, AutoGen, Google ADK, and Claude Agent SDK. Here is what the scan output looks like."

**Why this works**: LinkedIn organic reach for technical/regulatory content is still strong. Compliance content gets shared by legal and risk teams.

### Channel 4: Reddit (Weeks 2-4)

Target subreddits where AI developers hang out:

- r/MachineLearning (2.9M members) - Share as a project showcase
- r/Python (1.2M members) - Tutorial-style post
- r/artificial (500K members) - Discussion about EU AI Act compliance
- r/LangChain (50K members) - Integration-focused post
- r/LocalLLaMA (200K members) - If you add local model scanning

**Rules**: Do NOT spam. One post per subreddit, spaced out over weeks. Frame as "I built this, here is what I learned" not "check out my product." Reddit users will destroy you if it feels like marketing.

### Channel 5: Twitter/X (Ongoing)

**Strategy**: Build-in-public thread format.

- Thread 1: "I am building an open-source EU AI Act compliance scanner. Here is what I have learned about what the regulation actually requires from AI code." (Thread with 5-7 tweets breaking down Articles 9-15)
- Thread 2: "I scanned 5 real LangChain apps for EU AI Act compliance. Here is what I found." (Share anonymized scan results)
- Thread 3: "The EU AI Act deadline is [X] days away. Here is the fastest way to check if your Python AI code is compliant." (Tutorial thread)

**Engagement**: Follow and reply to people posting about EU AI Act, AI governance, AI safety. Do not pitch. Add value. When someone asks "how do I prepare for the EU AI Act?" reply with a helpful answer and mention AIR Blackbox naturally.

---

## LAYER 2: ACTIVATION — Get Tried

Awareness means nothing if people do not install and run the tool. The goal is to reduce friction to zero.

### The 30-Second Experience

The README and every piece of content should drive to this:

```
pip install air-blackbox
air-blackbox comply --scan .
```

That is it. Two commands. If someone cannot go from "never heard of this" to "seeing scan results" in under 30 seconds, you lose them.

### Demo Hub as the Landing Page

Your new demo hub (airblackbox.ai/demo/hub) is a powerful activation tool. Use it everywhere:

- Every Dev.to article ends with: "Try it in your browser: airblackbox.ai/demo/hub"
- Every LinkedIn post links to a specific demo
- The Show HN post links to the live-scan demo
- The README links to the demo hub

### GitHub README Optimization

Your README is your storefront. It needs to do three things in the first 10 seconds:

1. **What it is**: One sentence. "Open-source CLI that scans Python AI code for EU AI Act compliance."
2. **Why you need it**: "The EU AI Act enforcement deadline is August 2, 2026. Does your AI code comply?"
3. **How to try it**: The two-command install + scan.

Below the fold:
- Animated GIF of the CLI in action (record with asciinema or vhs)
- Framework support badges (LangChain, CrewAI, OpenAI, etc.)
- Link to demo hub
- Quick comparison table: what you get free vs. what is coming in Pro

### Starred Repo Tactics

Things that directly increase GitHub stars:

1. **Add "Star this repo" CTA to README** - A simple "If this helps you, star the repo" with a badge. Sounds basic, works surprisingly well.
2. **Release frequently** - Every release shows up in followers' feeds. Ship v1.11, v1.12, etc. on a regular cadence.
3. **Good first issues** - Label 5-10 issues as "good first issue." Contributors who fix them often star the repo.
4. **GitHub Topics** - Add topics to the repo: eu-ai-act, compliance, ai-governance, python, langchain, security, audit. These make you discoverable in GitHub search.

---

## LAYER 3: COMMUNITY — Get Contributions

Stars are vanity. Contributors are the moat.

### Creating Contribution Pathways

**Easy wins (no code required)**:
- Documentation improvements
- Typo fixes
- Adding compliance check descriptions
- Translating docs (EU regulation = multilingual audience)
- Testing on different Python versions/OS

**Medium contributions**:
- Adding new compliance checks
- Writing tests
- Improving CLI output formatting
- Adding new framework integrations

**Hard contributions (core team)**:
- ML-DSA-65 signing implementation
- Evidence bundle format
- Performance optimization
- New scanner rules

### CONTRIBUTING.md

Create a CONTRIBUTING.md that makes it dead simple:

1. Fork the repo
2. Create a branch
3. Make your change
4. Run `pytest tests/`
5. Submit a PR

Include a "Development Setup" section that gets contributors running in under 5 minutes.

### Discord or GitHub Discussions

You need a place for the community to talk. Options:

- **GitHub Discussions** (free, zero maintenance, already integrated) - START HERE
- **Discord** (more engagement but requires moderation) - Add later when you have 20+ active contributors

Enable GitHub Discussions on the gateway repo. Create categories: General, Show Your Scan Results, Feature Requests, EU AI Act Questions.

---

## THE 90-DAY EXECUTION CALENDAR

### Week 1 (April 14-20)
- [ ] Post Show HN (Tuesday or Wednesday, 8-10am EST)
- [ ] Publish Dev.to article #1 (tutorial: scan your code in 30 seconds)
- [ ] Enable GitHub Discussions on gateway repo
- [ ] Add GitHub Topics to all repos
- [ ] Add "Star this repo" CTA to README
- [ ] First LinkedIn post (countdown to deadline)
- [ ] Record asciinema GIF of CLI in action for README

### Week 2 (April 21-27)
- [ ] Publish Dev.to article #2 (LangChain integration, 2 lines of code)
- [ ] Post to r/Python (tutorial angle)
- [ ] 3 LinkedIn posts
- [ ] Twitter thread #1 (what the EU AI Act requires from code)
- [ ] Create 5 "good first issue" labels on GitHub
- [ ] Write CONTRIBUTING.md

### Week 3 (April 28 - May 4)
- [ ] Publish Dev.to article #3 (Articles 9-15 explained for developers)
- [ ] Post to r/MachineLearning (project showcase)
- [ ] 3 LinkedIn posts
- [ ] Cross-post Dev.to articles to Medium
- [ ] Reach out to 3 AI/ML newsletter curators for inclusion

### Week 4 (May 5-11)
- [ ] Publish Dev.to article #4 (HMAC-SHA256 audit trails deep dive)
- [ ] Post to r/LangChain
- [ ] 3 LinkedIn posts
- [ ] Twitter thread #2 (scan results from real apps)
- [ ] Ship v1.11.0 with CHANGELOG (release = visibility)

### Weeks 5-8 (May 12 - June 7)
- [ ] Biweekly Dev.to articles
- [ ] Consistent LinkedIn (3x/week)
- [ ] Submit talk proposals to PyCon, AI conferences, local meetups
- [ ] Pitch guest posts to Python/AI blogs
- [ ] Reach out to Julian Risch (Haystack) about co-marketing
- [ ] Contact LangChain team about official integration listing
- [ ] "100 days to EU AI Act" campaign push

### Weeks 9-12 (June 8 - July 13)
- [ ] "60 days to deadline" content blitz
- [ ] Case studies from production users (anonymized if needed)
- [ ] Launch compliance consulting offer on LinkedIn
- [ ] Second HN post with different angle
- [ ] Target: 500 stars, 50K downloads, 25 production users

---

## GROWTH EXPERIMENTS

### Experiment #1: HN Title A/B (Natural experiment)

```
HYPOTHESIS: A question-format title will outperform a statement title on HN
CONTROL: "Show HN: Open-source CLI that scans Python AI code for EU AI Act compliance"
VARIANT: Save for second post: "Ask HN: How are you preparing your AI code for the EU AI Act deadline?"
METRIC: Upvotes and comments within 24 hours
TIMELINE: Posts spaced 3-4 weeks apart
```

### Experiment #2: Dev.to Article Format

```
HYPOTHESIS: Tutorial-style articles ("How to X in Y minutes") will drive 
more pip installs than opinion/explainer articles
CONTROL: Week 3 explainer article (Articles 9-15 explained)
VARIANT: Week 1 tutorial article (scan your code in 30 seconds)
METRIC: Click-through to GitHub repo + PyPI download spike in 48 hours after publish
TIMELINE: Compare after both are published (2 weeks)
```

### Experiment #3: LinkedIn Post Type

```
HYPOTHESIS: Countdown posts with code snippets will get more engagement 
than pure text posts
CONTROL: Text-only posts about the deadline
VARIANT: Posts with CLI output screenshots or code snippets
METRIC: Impressions, likes, comments, profile visits
TIMELINE: 2 weeks (6 posts, alternating types)
```

### Experiment #4: README Star CTA

```
HYPOTHESIS: Adding an explicit "Star this repo" call-to-action in the 
README will increase star rate by 20%+
CONTROL: Current star rate (track stars/unique visitors via GitHub traffic)
VARIANT: Add star CTA badge at top of README
METRIC: Stars per week (before vs. after)
TIMELINE: 2 weeks baseline, then add CTA, measure 2 more weeks
```

---

## COMPETITIVE RESPONSE: ark-forge/mcp-eu-ai-act

They are posting aggressively on Dev.to. Here is how to respond without getting into a mud fight:

1. **Do not mention them by name.** Ever. In any content.
2. **Out-ship them.** Your tool covers 7 frameworks. Emphasize breadth.
3. **Out-content them.** They post articles? You post articles with working demos.
4. **Differentiate on trust.** Your HMAC-SHA256 audit chain and ML-DSA-65 signing are technical moats they do not have.
5. **Differentiate on production usage.** You have 5 production deployments. Lead with social proof.

---

## METRICS TO TRACK WEEKLY

| Metric | Where to Check | Target Trend |
|--------|---------------|--------------|
| GitHub stars | github.com/airblackbox/airblackbox | +20/week |
| PyPI downloads | pypistats.org | +2,000/week |
| Site visitors | Vercel Analytics | +500/week |
| Demo page views | Vercel Analytics | +200/week |
| Dev.to article views | Dev.to dashboard | +500/article |
| LinkedIn impressions | LinkedIn analytics | +2,000/week |
| GitHub issues opened | GitHub | +3/week (sign of engagement) |
| Contributors | GitHub | +1/month |

---

## THE ONE THING THAT MATTERS MOST

If you do nothing else from this document, do this:

**Post the Show HN this week.**

One well-timed HN post can generate more awareness than a month of other activities combined. The post is written. The demos are live. The deadline is real. Ship it.

---

*Strategy built April 13, 2026. Review and update weekly.*
