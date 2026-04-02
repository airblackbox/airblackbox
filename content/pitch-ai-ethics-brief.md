# Pitch: The AI Ethics Brief (Montreal AI Ethics Institute)

**To**: Montreal AI Ethics Institute (via montrealethics.ai/contact)
**From**: jason@airblackbox.ai
**Subject**: Open-source EU AI Act compliance scanner with scan data from 8 major AI frameworks

---

Hi Renjie,

I'm Jason Shotwell, the maintainer of AIR Blackbox, an open-source (Apache 2.0) EU AI Act compliance scanner for Python AI projects.

I've scanned 8 popular open-source AI frameworks (342K+ combined GitHub stars) and quantified their compliance gaps against EU AI Act Articles 9 through 15. The average score is 24%, and the patterns reveal systemic issues in how AI frameworks approach governance:

- Record-keeping infrastructure is almost universally absent (no tamper-evident logs)
- Human oversight mechanisms are missing from multiple major agent frameworks
- Documentation coverage varies wildly (44% to 98% type hint coverage depending on the project)
- Data governance is the second-weakest area across all scanned projects

The tool is designed as a practical bridge between AI ethics principles and engineering implementation. It doesn't certify compliance. It identifies where the technical gaps are so teams can prioritize, which is what makes it useful rather than performative.

It runs locally with zero data exfiltration:

```
pip install air-blackbox
air-blackbox comply --scan . --no-llm --format table --verbose
```

I think this would be relevant for the AI Ethics Brief or the next State of AI Ethics report. The scan data provides empirical evidence of the gap between AI ethics principles and actual implementation in widely-used frameworks. Happy to share full scan reports or contribute a piece.

Best,
Jason Shotwell
https://airblackbox.ai
https://github.com/air-blackbox/gateway
