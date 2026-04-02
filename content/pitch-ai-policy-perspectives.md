# Pitch: AI Policy Perspectives

**To**: aipolicyperspectives@google.com (Conor Griffin & Julian Jacobs)
**From**: jason@airblackbox.ai
**Subject**: Empirical data on EU AI Act technical compliance gaps in major AI frameworks

---

Hey Conor and Julian,

I built an open-source EU AI Act compliance scanner called AIR Blackbox that maps Python code patterns to Articles 9 through 15. I've scanned 8 popular open-source AI frameworks (342K+ combined GitHub stars) and the data reveals a significant implementation gap heading into the August 2026 enforcement deadline.

Average compliance score: 24%. The most striking pattern: record-keeping (Art. 12) and human oversight (Art. 14) are systematically the weakest areas, even in frameworks with otherwise strong engineering practices.

This has policy implications. The frameworks I scanned are the ones enterprises are actually building on. If the foundation layer has compliance gaps, every application built on top inherits them. That creates a systemic risk that individual company compliance efforts can't fully address.

The scanner is open source (Apache 2.0), runs locally, and identifies gaps without certifying compliance:

```
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

If the data is useful for a future edition, happy to share the full scan reports or discuss the policy implications of framework-level compliance gaps.

Best,
Jason Shotwell
https://airblackbox.ai
