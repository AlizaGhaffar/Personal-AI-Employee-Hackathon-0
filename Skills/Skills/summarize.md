# Skill: Summarize

> Summarize documents, emails, and notes into concise, actionable summaries.

---

## Overview

| Field         | Value                                        |
|---------------|----------------------------------------------|
| **Command**   | `/summarize` (planned)                       |
| **Trigger**   | On demand, or as part of triage/approve flow |
| **Input**     | Any `.md` or text file                       |
| **Output**    | Summary appended to `Memory/summaries.md`    |
| **Autonomy**  | Fully autonomous                             |
| **Status**    | Integrated into `/triage` and `/approve`     |

---

## What It Does

1. **Reads** the target document or file
2. **Extracts** key points, decisions, and action items
3. **Generates** a concise summary (3 sentences max per Company Handbook)
4. **Stores** summary in `Memory/summaries.md` with metadata
5. **Extracts** any action items into new `Needs_Action/` files

---

## Summary Format

```markdown
### <Date> — <Document Title>
- **Source:** `<file path>`
- **Type:** <document type>
- **Key Points:**
  - Point 1
  - Point 2
  - Point 3
- **Action Items:** <count> extracted
- **Summarized At:** <timestamp>
```

---

## Rules

- Preserve original content — never modify source files
- Use Company Handbook formatting rules (tables, bullets, no walls of text)
- Summaries must be under 3 sentences for the brief version
- Extract ALL action items found in the document
- Tag extracted action items with priority using handbook rules
