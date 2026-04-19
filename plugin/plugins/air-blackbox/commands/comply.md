---
description: Run a full EU AI Act compliance scan on your Python AI project
---

# /air-comply

Run a full compliance scan against EU AI Act Articles 9-15.

## Steps

1. Check if air-blackbox is installed:

```bash
pip show air-blackbox 2>/dev/null && echo "INSTALLED" || pip install air-blackbox
```

2. Run the scan with verbose output:

```bash
air-blackbox comply --scan . -v
```

3. Present results as a summary table showing each article, its status (PASS/WARN/FAIL), and the check count.

4. For any FAIL results, explain what's missing and show the fix hint from the scanner output.

5. Calculate the overall compliance score (passed checks / total checks) and tell the user where they stand.

6. Offer to help fix the highest-priority failures first, starting with Article 12 (record-keeping) and Article 14 (human oversight).

7. After fixes, offer to re-run: `air-blackbox comply --scan . -v`
