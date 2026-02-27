# Skill: Triage & Classify

> Automatically classify incoming items, assess priority, and create execution plans.

---

## Overview

| Field         | Value                                        |
|---------------|----------------------------------------------|
| **Command**   | `/triage`                                    |
| **Trigger**   | New items land in `Needs_Action/`            |
| **Input**     | `.md` files in `Needs_Action/` with `status: pending` |
| **Output**    | Plan files in `Plans/`, updated metadata     |
| **Autonomy**  | Fully autonomous (no approval needed)        |
| **Source**     | `.claude/commands/triage.md`                 |

---

## What It Does

1. **Scans** `Needs_Action/` for pending `.md` files
2. **Reads** metadata and companion data files
3. **Classifies** item type: `email`, `task`, `receipt`, `note`, `document`, `unknown`
4. **Assesses priority** using Company Handbook rules (P1/P2/P3)
5. **Creates plan** in `Plans/PLAN_<name>.md` with action steps
6. **Updates metadata** on source file (status, type, timestamp)
7. **Logs** action to `Logs/<date>_triage.log`

---

## Classification Rules

| Type       | Indicators                                           |
|------------|------------------------------------------------------|
| `email`    | Contains email addresses, "Subject:", "From:", "Re:"  |
| `task`     | Contains action verbs, deadlines, assignments         |
| `receipt`  | Contains amounts, payment, invoice, receipt           |
| `note`     | General text, meeting notes, brainstorming            |
| `document` | Reports, proposals, formal documents                  |
| `unknown`  | Cannot determine — flag for human review             |

## Priority Rules

| Priority | Keywords                                          |
|----------|---------------------------------------------------|
| **P1**   | urgent, ASAP, overdue, security, payment failed   |
| **P2**   | deadline, meeting, invoice, review, approval       |
| **P3**   | Everything else (default)                          |

---

## Pipeline Position

```
Inbox → Needs_Action → [/triage] → Plans/ → Pending_Approval → Approved → Done
```

---

## Example Usage

```bash
# Triage all pending items
/triage

# Triage a specific file
/triage expense_report.md
```

---

## Safety Rules

- Never deletes files — only moves or updates status
- Never executes plans — only creates them
- P1 items always set `requires_approval: true`
- Money-related items always set `requires_approval: true`
- Unknown type items route to `Pending_Approval/` instead
