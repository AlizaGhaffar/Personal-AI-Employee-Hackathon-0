# Skill: /ceo-briefing

Generate the Thursday weekly CEO briefing — revenue, completed work, bottlenecks, and proactive suggestions — from live Odoo data and the local pipeline.

---

## Metadata

| Field      | Value                                              |
|------------|----------------------------------------------------|
| Command    | `/ceo-briefing`                                    |
| Script     | `Scripts/ceo_briefing.py`                          |
| Autonomy   | Fully autonomous — read-only, no approval required |
| Schedule   | Every Thursday 12:00 PM (Windows Task Scheduler)   |
| Output     | `Briefings/YYYY-MM-DD_ceo_briefing.md`             |
| Log        | `Logs/YYYY-MM-DD_ceo_briefing.log` + `Logs/odoo.log` |

---

## When to Use This Skill

- It's Thursday and you want the weekly business snapshot
- You want to check revenue performance vs targets before a call
- You need a quick summary of what the team completed this week
- You want to find bottlenecks before they become problems
- You want Claude to proactively suggest business improvements

---

## What It Generates

### 1. Executive Dashboard
KPI table with 🟢🟡🔴 traffic-light indicators:
- Revenue this week vs $5,000 target
- Overdue invoice count
- Draft (unposted) invoices
- Tasks completed this week
- Pipeline bottleneck flag

### 2. Revenue This Week
Posted invoices from Monday → today, total and itemised.

### 3. Overdue Invoices
All posted invoices with outstanding balance past due date.

### 4. Sales Orders
Confirmed orders from the past 7 days.

### 5. Completed Tasks
Files moved to `Done/` in the past 7 days.

### 6. Pipeline Bottlenecks
- `Needs_Action/` items idle > 24h (not triaged)
- `Plans/` items idle > 48h (not actioned)
- `Pending_Approval/` items waiting > 24h for human sign-off

### 7. Proactive Suggestions
Claude CLI analyses the snapshot and generates 3–5 specific suggestions.

### 8. Action Checklist
Auto-generated list of items needing attention.

---

## Data Sources

| Section              | Source                                |
|----------------------|---------------------------------------|
| Revenue              | Odoo — `account.move` (posted)        |
| Overdue invoices     | Odoo — posted + past due date         |
| Sales orders         | Odoo — `sale.order` (last 7 days)     |
| Completed tasks      | `Done/` folder — files modified < 7d  |
| Bottlenecks          | `Needs_Action/`, `Plans/`, `Pending_Approval/` |
| KPI targets          | `Memory/business_goals.md`            |
| Suggestions          | Claude CLI (`claude --print`)         |

---

## Usage

```bash
# Generate and save to Briefings/
python Scripts/ceo_briefing.py

# Preview without saving
python Scripts/ceo_briefing.py --dry-run

# Register Thursday 12pm schedule (run as Admin, once)
Scripts\schedule_briefing.bat
```

---

## Schedule Setup

Run `Scripts\schedule_briefing.bat` as Administrator once to register:

```
Task name : GoldTier_CEO_Briefing
Runs      : Every Thursday at 12:00 PM
Launcher  : Scripts\run_ceo_briefing.bat
Log       : Logs\task_scheduler.log
```

Manage it:
```bat
schtasks /query  /tn "GoldTier_CEO_Briefing"   :: check status
schtasks /run    /tn "GoldTier_CEO_Briefing"   :: run now
schtasks /delete /tn "GoldTier_CEO_Briefing" /f :: remove
```

---

## KPI Thresholds (from Memory/business_goals.md)

| KPI                   | 🟢 Green   | 🟡 Yellow     | 🔴 Red      |
|-----------------------|------------|---------------|-------------|
| Weekly revenue        | ≥ $5,000   | $2,500–$4,999 | < $2,500    |
| Overdue invoices      | 0          | 1–2           | ≥ 3         |
| Tasks completed/week  | ≥ 5        | 2–4           | 0–1         |

Update targets in `Memory/business_goals.md`.

---

## Safety

- Read-only — never modifies Odoo data
- Never posts invoices or sends emails
- Saves to `Briefings/` only — no pipeline folders touched
- Odoo connection errors are caught and logged — partial briefing still generated
