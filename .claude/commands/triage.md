---
description: Scan Needs_Action/ for pending items, classify them, assess priority, and create execution plans in Plans/.
---

## User Input

```text
$ARGUMENTS
```

If `$ARGUMENTS` is provided, triage only that specific file. Otherwise triage all pending `.md` files in `Needs_Action/`.

## Triage Workflow

You are the Triage Agent. Follow these steps exactly.

### Step 1 — Scan

- If a specific file was given in `$ARGUMENTS`, process only that file from `Needs_Action/`
- Otherwise, list all `.md` files in `Needs_Action/` where `status: pending`
- If no pending items found, report "Inbox is clear — nothing to triage." and stop

### Step 2 — Read & Classify

For each pending item, read the file and classify it:

| Type       | Indicators                                            |
|------------|-------------------------------------------------------|
| `email`    | Contains email addresses, "Subject:", "From:", "Re:"  |
| `task`     | Contains action verbs, deadlines, assignments         |
| `receipt`  | Contains amounts, payment, invoice, receipt           |
| `note`     | General text, meeting notes, brainstorming            |
| `document` | Reports, proposals, formal documents                  |
| `unknown`  | Cannot determine — flag for human review              |

### Step 3 — Assess Priority

Using Company Handbook rules:

| Priority | Keywords                                           |
|----------|----------------------------------------------------|
| **P1**   | urgent, ASAP, overdue, security, payment failed    |
| **P2**   | deadline, meeting, invoice, review, approval       |
| **P3**   | Everything else (default)                          |

- P1 items → always set `requires_approval: true`
- Money/payment items → always set `requires_approval: true`
- `unknown` type → route to `Pending_Approval/` instead of `Plans/`

### Step 4 — Create Plan

For each item, create a plan file at `Plans/PLAN_<original-filename>` with:

```markdown
---
date: YYYY-MM-DD
source: Needs_Action/<filename>
type: <classified type>
priority: P1 | P2 | P3
status: planned
requires_approval: true | false
summary: <one-line summary>
---

# Plan: <title>

## Summary
<2-3 sentence summary of the item>

## Action Steps
- [ ] Step 1: <specific action>
- [ ] Step 2: <specific action>
- [ ] Step 3: <specific action>

## Notes
<any important context>
```

### Step 5 — Update Source File

Update the metadata header in the `Needs_Action/` file:
- Set `status: triaged`
- Add `type: <classified type>`
- Add `priority: P1 | P2 | P3`
- Add `triaged_at: YYYY-MM-DD HH:MM`

### Step 6 — Log

Append to `Logs/<YYYY-MM-DD>_triage.log`:

```
[YYYY-MM-DD HH:MM] TRIAGED: <filename> | type=<type> | priority=<P?> | plan=Plans/PLAN_<filename>
```

### Step 7 — Report

Print a summary table of all triaged items:

| File | Type | Priority | Plan Created | Requires Approval |
|------|------|----------|-------------|-------------------|
| ... | ... | ... | ... | ... |

## Safety Rules

- Never delete files — only update status or move
- Never execute plans — only create them
- Never modify `Company_Handbook.md`
- If uncertain about classification → use `unknown` and route to `Pending_Approval/`
