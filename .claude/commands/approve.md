---
description: Review plans in Plans/, get human approval, execute action steps, and archive completed work to Done/.
---

## User Input

```text
$ARGUMENTS
```

If `$ARGUMENTS` is a specific filename, process only that plan. If `$ARGUMENTS` is `all`, process all plans without pausing between them. Otherwise, list all plans and process one at a time.

## Approve Workflow

You are the Approve & Execute Agent. Follow these steps exactly.

### Step 1 — Scan Plans

- List all `.md` files in `Plans/` with `status: planned`
- If no plans found, report "No plans waiting for approval." and stop
- If a specific file given in `$ARGUMENTS`, process only that one

### Step 2 — Present Plan for Review

For each plan, display:
- **File:** `Plans/<filename>`
- **Summary:** from plan metadata
- **Type:** email / task / receipt / note / document / unknown
- **Priority:** P1 / P2 / P3
- **Requires Approval:** Yes / No
- **Action Steps:** list all checkboxes

Then ask: **"Approve this plan? (yes / no / skip)"**

- `yes` → execute (Step 3)
- `no` → move to `Rejected/` with timestamp, log it, continue to next
- `skip` → leave in `Plans/`, continue to next

### Step 3 — Execute by Type

| Type     | Actions                                                          |
|----------|------------------------------------------------------------------|
| `receipt`  | Extract amount/vendor/date, append to `Memory/Memory/expenses.md`, archive to `Done/` |
| `email`    | Draft reply using context, save to `Pending_Approval/`, wait for human to send |
| `task`     | Execute each subtask step-by-step, create any deliverables       |
| `note`     | Summarize key points, extract action items, archive to `Done/`   |
| `document` | Summarize, extract decisions/follow-ups, archive to `Done/`      |
| `unknown`  | Move to `Pending_Approval/`, do NOT execute — STOP               |

**Safety overrides (always apply regardless of type):**
- Any payment/money action → route to `Pending_Approval/`, never execute directly
- Any external communication (email, message, post) → route to `Pending_Approval/`, never send directly
- Any file deletion → ask explicit confirmation first

### Step 4 — Update Plan Checkboxes

As each step completes, update the plan file:
- Mark completed steps: `- [x] Step N: ...`
- If a step fails: stop, report the error, leave remaining steps unchecked

### Step 5 — Archive to Done

When all steps complete successfully:
- Move the plan file to `Done/DONE_<YYYY-MM-DD>_<filename>`
- Move the original `Needs_Action/` source file to `Done/` as well (if it exists)
- Update both files' metadata: `status: done`, `completed_at: YYYY-MM-DD HH:MM`

### Step 6 — Log

Append to `Logs/<YYYY-MM-DD>_actions.log`:

```
[YYYY-MM-DD HH:MM] EXECUTED: <plan-filename> | type=<type> | result=done | archived=Done/<filename>
[YYYY-MM-DD HH:MM] REJECTED: <plan-filename> | moved=Rejected/
```

### Step 7 — Report

Print final summary:

| Plan | Action Taken | Result |
|------|-------------|--------|
| ... | approved / rejected / skipped | done / pending_approval / failed |

## Safety Rules

- Never delete files — always move
- Never send emails or messages directly — always route to `Pending_Approval/`
- Never make payments — always route to `Pending_Approval/`
- If any step fails, stop execution immediately and report to user
- Always update plan checkboxes as steps complete
