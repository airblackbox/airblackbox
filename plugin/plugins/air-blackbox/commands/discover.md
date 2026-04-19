---
description: Discover AI components in your project and classify their EU AI Act risk level
---

# /air-discover

Discover and classify AI components in the current project.

## Steps

1. Run the AIR Blackbox discovery command:

```bash
air-blackbox discover . 2>&1 || echo "If air-blackbox is not installed, run: pip install air-blackbox"
```

2. Present the discovered components in a table showing:
   - File path
   - Component type (model, agent, pipeline, tool call)
   - Framework detected (LangChain, CrewAI, OpenAI SDK, etc.)
   - Risk classification (high-risk, limited-risk, minimal-risk per EU AI Act Annex III)

3. For any high-risk components, explain which Annex III category they fall under and what that means for compliance obligations.

4. Suggest running a full compliance scan on the project: `air-blackbox comply --scan .`
