# Pitch: AI Snake Oil

**To**: arvindn@cs.princeton.edu (Arvind Narayanan)
**From**: jason@airblackbox.ai
**Subject**: I scanned 8 popular AI frameworks for EU AI Act compliance. Average score: 24%.

---

Hi Arvind,

I built an open-source tool that scans Python AI codebases for EU AI Act compliance patterns, and the results are sobering.

AIR Blackbox maps static code patterns to EU AI Act Articles 9 through 15 (risk management, data governance, documentation, record-keeping, human oversight, security). It's a linter for AI governance, not a compliance certification tool. It identifies gaps, it does not certify anything.

I ran it against 8 popular open-source AI frameworks (342K+ combined GitHub stars). Average score: 24%. Some findings:

- Record-keeping (Art. 12) is the weakest area universally. Zero frameworks had tamper-evident audit chains.
- One major agent framework scored 0/9 on human oversight checks (no kill switch, no approval gates, no execution bounding).
- The highest-scoring framework (LiteLLM, 48%) still failed all runtime checks.

What I think makes this relevant to your work: the EU AI Act enforcement deadline is August 2, 2026, the fines are up to 7% of global turnover, and the frameworks that enterprises are actually building on have significant technical gaps. The compliance industry that springs up around this will inevitably include snake oil. A free, open-source scanner that anyone can run locally and verify is one way to keep the space honest.

The tool is Apache 2.0 and runs entirely locally:

```
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

If the data is interesting, I'm happy to run a scan on any framework your readers would find relevant.

Best,
Jason Shotwell
https://airblackbox.ai
https://github.com/air-blackbox/gateway
