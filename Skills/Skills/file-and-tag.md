# Skill: File & Tag

> Move files through the pipeline and apply structured metadata tags.

---

## Overview

| Field         | Value                                        |
|---------------|----------------------------------------------|
| **Command**   | `/file-and-tag` (planned)                    |
| **Trigger**   | After triage classification                  |
| **Input**     | Files in any pipeline stage                  |
| **Output**    | Files moved to correct folder with metadata  |
| **Autonomy**  | Fully autonomous for standard pipeline flow  |
| **Status**    | Integrated into `/triage` and `/approve`     |

---

## What It Does

1. **Reads** file metadata (YAML front matter)
2. **Validates** required fields are present
3. **Applies** missing metadata using classification rules
4. **Moves** file to the correct pipeline stage folder
5. **Renames** file following naming convention
6. **Logs** the transition

---

## Metadata Standard

Every triaged file must have this YAML front matter:

```yaml
---
id: <auto-increment>
date: YYYY-MM-DD
type: email | task | note | meeting | payment
from: <source>
priority: P1 | P2 | P3
status: pending | in_progress | approved | rejected | done
requires_approval: true | false
tags: []
summary: <one-line summary>
---
```

## Naming Convention

```
YYYY-MM-DD_<type>_<short-description>.md

Examples:
2026-02-13_email_client-proposal-review.md
2026-02-13_task_update-weekly-report.md
2026-02-13_receipt_anthropic-claude-pro.md
```

---

## Pipeline Transitions

| From               | To                  | Condition                    |
|--------------------|---------------------|------------------------------|
| `Inbox/`           | `Needs_Action/`     | Watcher picks up new file    |
| `Needs_Action/`    | `Plans/`            | After triage classification  |
| `Plans/`           | `Pending_Approval/` | If requires_approval = true  |
| `Plans/`           | Execution           | If requires_approval = false |
| `Pending_Approval/`| `Approved/`         | Human approves               |
| `Pending_Approval/`| `Rejected/`         | Human rejects                |
| Any                | `Done/`             | After successful execution   |

---

## Safety Rules

- Never deletes files — only moves them
- Always preserves original content
- Logs every file transition with timestamp
- Batch moves of >5 files require human approval
