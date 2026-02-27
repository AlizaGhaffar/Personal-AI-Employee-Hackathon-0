# AI Employee Dashboard

> **Nerve Center** | Personal AI Employee — Bronze Tier
> Last refreshed: `2026-02-26 13:45`

---

## Real-Time Summary

| Metric              | Value           |
|----------------------|-----------------|
| Bank Balance         | `$0.00`         |
| Pending Messages     | `0`             |
| Inbox Items          | `0`             |
| Needs Action         | `0`             |
| Pending Approval     | `0`             |
| Done (this week)     | `0`             |

<!-- UPDATE: Watcher scripts refresh these counts automatically -->

---

## System Health

| Component        | Status  | Last Updated |
|------------------|---------|--------------|
| Folder Structure | Active  | 2026-02-13   |
| File Watcher     | Offline | --           |
| Gmail Watcher    | Offline | --           |
| LinkedIn Watcher | Offline | --           |
| Claude Code Link | Active  | 2026-02-13   |

---

## Active Projects

| # | Project | Status | Priority | Next Step |
|---|---------|--------|----------|-----------|
| 1 | AI Employee Hackathon | In Progress | P1 | Build file watcher |
<!-- Add rows as projects come in -->

---

## Pipeline

```
Inbox → Needs_Action → Plans → Pending_Approval → Approved → Done
                                                 ↘ Rejected
```

### Inbox
<!-- Auto-updated by watcher scripts -->
_Empty_

### Needs Action
_Empty_

### Plans
_Empty_

### Pending Approval
_Empty_

### Approved
_Empty_

### Rejected
_Empty_

### Done
_Empty_

---

## Odoo — Live Business Data

| Metric                  | Value                          |
|-------------------------|--------------------------------|
| Draft Invoices          | `1`                            |
| Total Invoiced (posted) | `Rs. 0`                        |
| Outstanding             | `Rs. 0`                        |
| Total Customers         | `1`                            |
| Recent Sales Orders     | `0`                            |

### Latest Invoice

| Field        | Detail                        |
|--------------|-------------------------------|
| Invoice #    | `INV/2026/00001`              |
| Customer     | Test Customer Hello World     |
| Line 1       | Web Design Service × 2 = Rs. 30,000 |
| Line 2       | SEO Optimization × 1 = Rs. 8,000  |
| **Total**    | **Rs. 38,000**                |
| Status       | `Draft` (confirm in Odoo UI)  |
| Due Date     | 2026-03-26                    |

> 🔗 Open Odoo: http://localhost:8069/web#action=account.action_move_out_invoice_type

---

## Recent Activity

| Timestamp           | Action                                      | Actor  |
|---------------------|---------------------------------------------|--------|
| 2026-02-26 13:45    | Invoice INV/2026/00001 created — Rs. 38,000 | Claude |
| 2026-02-26 13:43    | Odoo Hello World — partners listed & customer created | Claude |
| 2026-02-13 00:00    | Workspace initialized — folders created     | Claude |
| 2026-02-13 00:00    | Dashboard.md and Company_Handbook.md created | Claude |
| 2026-02-13 00:00    | Full pipeline folders added                 | Claude |
<!-- New entries prepend above this line -->

---

## Agent Skills

| Skill       | Command           | Trigger              | Status   | Definition                  |
|-------------|-------------------|----------------------|----------|-----------------------------|
| Triage      | `/triage`         | New `Needs_Action/` items | Active   | [Skills/triage.md](Skills/triage.md) |
| Approve     | `/approve`        | Plans ready in `Plans/` | Active   | [Skills/approve.md](Skills/approve.md) |
| Summarize   | `/summarize`      | On demand / triage   | Integrated | [Skills/summarize.md](Skills/summarize.md) |
| Draft Reply | `/draft-reply`    | Email in pipeline    | Integrated | [Skills/draft-reply.md](Skills/draft-reply.md) |
| File & Tag  | `/file-and-tag`   | After triage         | Integrated | [Skills/file-and-tag.md](Skills/file-and-tag.md) |
| Refresh     | `/refresh-dashboard` | After pipeline changes | Planned  | [Skills/refresh-dashboard.md](Skills/refresh-dashboard.md) |

---

## Quick Commands

```bash
# Start file watcher
python Watchers/file_watcher.py

# Start Gmail watcher
python Watchers/gmail_watcher.py

# Start LinkedIn watcher (first run: log in manually)
python Watchers/linkedin_watcher.py

# Claude Code slash commands (run in Claude Code terminal)
/triage              # Classify and plan all pending items
/approve             # Review and execute plans
/triage <file>       # Triage a specific file
/approve all         # Process all plans at once
```

---

## Knowledge Base

- [Company Handbook](Company_Handbook.md) — Operating procedures and preferences
- [Conversation Log](Memory/conversation_log.md) — Action history
- [Preferences](Memory/preferences.md) — Owner and processing config

---

## Architecture

```
hack0aliza/
├── Dashboard.md            # This file — nerve center
├── Company_Handbook.md     # AI employee knowledge base
├── Inbox/                  # Raw incoming items
├── Needs_Action/           # Triaged items awaiting Claude
├── Plans/                  # Step-by-step execution plans
├── Pending_Approval/       # Awaiting human review
├── Approved/               # Human-approved items
├── Rejected/               # Human-rejected (with feedback)
├── Done/                   # Completed work archive
├── Logs/                   # Audit trails
├── Skills/                 # Agent Skill scripts (Python)
├── Watchers/               # Monitoring scripts
└── Memory/                 # Persistent AI memory
```
