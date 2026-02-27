# Skill: Approve & Execute

> Review plans, get human approval, execute action steps, and archive completed work.

---

## Overview

| Field         | Value                                        |
|---------------|----------------------------------------------|
| **Command**   | `/approve`                                   |
| **Trigger**   | Plans ready in `Plans/`                      |
| **Input**     | `.md` plan files in `Plans/` with `status: planned` |
| **Output**    | Executed results in `Done/`, updated logs    |
| **Autonomy**  | HITL — requires human confirmation           |
| **Source**     | `.claude/commands/approve.md`                |

---

## What It Does

1. **Lists** available plans in `Plans/` with status `planned`
2. **Presents** each plan summary for human review
3. **Waits** for human approval (yes / no / skip)
4. **Executes** approved plan steps one-by-one
5. **Moves** completed items to `Done/` with timestamps
6. **Logs** all actions to `Logs/<date>_actions.log`

---

## Execution by Type

| Type     | Actions                                              |
|----------|------------------------------------------------------|
| Receipt  | Extract data, log to `Memory/expenses.md`, archive   |
| Email    | Draft reply, route to `Pending_Approval/` for send   |
| Task     | Execute subtasks in order, create deliverables        |
| Note     | Summarize to `Memory/summaries.md`, extract actions   |
| Document | Summarize, extract decisions, identify follow-ups     |
| Unknown  | Move to `Pending_Approval/`, STOP                    |

---

## Pipeline Position

```
Plans/ → [/approve] → Done/
                    → Rejected/ (if human says no)
```

---

## Approval Logic

- `Requires Approval: Yes` → **Must** have explicit human "yes"
- `Requires Approval: No` → Present summary, can proceed after brief confirmation
- Payments of any kind → Always route to `Pending_Approval/`
- External communication → Always require approval

---

## Example Usage

```bash
# List and process all plans
/approve

# Approve a specific plan
/approve PLAN_expense_report.md

# Process all at once
/approve all
```

---

## Safety Rules

- Never deletes files — always moves (copy to Done/, remove from source)
- Never sends emails/messages without explicit human approval + MCP server
- Never makes payments — always routes to `Pending_Approval/`
- If any step fails, stops execution and reports to user
- Always updates plan checkboxes as steps complete
