# AI Employee Dashboard

> **Nerve Center** | Personal AI Employee — **Gold Tier: Autonomous Employee**
> Last refreshed: `2026-02-27`

---

## Tier Achievement

| Tier | Status | Requirements Met |
|------|--------|-----------------|
| Bronze — Foundation | ✅ Complete | Vault, 1 watcher, folder structure, agent skills |
| Silver — Functional Assistant | ✅ Complete | 5 watchers, social posting, MCP servers, HITL workflow |
| Gold — Autonomous Employee | ✅ Complete | Full cross-domain automation, ERP, CEO briefing, autonomous loop |

---

## Real-Time Summary

| Metric              | Value           |
|----------------------|-----------------|
| Pending Messages     | `0`             |
| Inbox Items          | `0`             |
| Needs Action         | `1`             |
| Pending Approval     | `3`             |
| Done (this week)     | `5`             |

<!-- UPDATE: Watcher scripts refresh these counts automatically -->

---

## System Health

| Component             | Status  | Last Updated |
|-----------------------|---------|--------------|
| Folder Structure      | ✅ Active | 2026-02-13   |
| File Watcher          | ✅ Active | 2026-02-27   |
| Gmail Watcher         | ✅ Active | 2026-02-27   |
| LinkedIn Watcher      | ✅ Active | 2026-02-27   |
| Facebook Watcher      | ✅ Active | 2026-02-27   |
| Twitter Watcher       | ✅ Active | 2026-02-27   |
| Email MCP Server      | ✅ Active | 2026-02-27   |
| Facebook MCP Server   | ✅ Active | 2026-02-27   |
| Twitter MCP Server    | ✅ Active | 2026-02-27   |
| Odoo MCP Server       | ✅ Active | 2026-02-27   |
| Claude Code Link      | ✅ Active | 2026-02-27   |
| CEO Briefing Script   | ✅ Active | 2026-02-27   |
| Ralph Autonomous Loop | ✅ Active | 2026-02-27   |

---

## Active Projects

| # | Project | Status | Priority | Next Step |
|---|---------|--------|----------|-----------|
| 1 | AI Employee Hackathon | ✅ Complete | P1 | Submission |

---

## Pipeline

```
Inbox → Needs_Action → Plans → Pending_Approval → Approved → Done
                                                 ↘ Rejected
```

### Needs Action
- [2026-02-21 — Client Inquiry Email](Needs_Action/2026-02-21_email_client-inquiry.md)

### Plans
- [PLAN — Client Inquiry Response](Plans/PLAN_2026-02-21_email_client-inquiry.md)

### Pending Approval
- [POST — Twitter 27 Feb](Pending_Approval/POST_twitter_27feb.md)
- [POST — Example Template](Pending_Approval/POST_example_template.md)
- [SOCIAL — Facebook Action](Pending_Approval/SOCIAL_FA_20260221_142043.md)

### Approved
_Empty_

### Rejected
_Empty_

### Done (This Week)
- [Twitter Test Post — 27 Feb](Done/20260227_124528_TWITTER_test_post.md)
- [LinkedIn Post — 27 Feb](Done/20260227_133753_POST_linkedin_27feb.md)
- [Instagram Post — 27 Feb](Done/20260227_141227_POST_instagram_27feb.md)
- [Facebook Post — 27 Feb](Done/20260227_141717_POST_facebook_27feb.md)
- [Twitter Post #2 — 27 Feb](Done/20260227_144304_POST_twitter_27feb_2.md)

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

> Open Odoo: http://localhost:8069/web#action=account.action_move_out_invoice_type

---

## Recent Activity

| Timestamp           | Action                                                  | Actor  |
|---------------------|---------------------------------------------------------|--------|
| 2026-02-27 14:43    | Twitter Post #2 published successfully                  | Claude |
| 2026-02-27 14:17    | Facebook Post published successfully                    | Claude |
| 2026-02-27 14:12    | Instagram Post published successfully                   | Claude |
| 2026-02-27 13:37    | LinkedIn Post published successfully                    | Claude |
| 2026-02-27 12:45    | Twitter test post published successfully                | Claude |
| 2026-02-26 13:45    | Invoice INV/2026/00001 created — Rs. 38,000             | Claude |
| 2026-02-26 13:43    | Odoo Hello World — partners listed & customer created   | Claude |
| 2026-02-13 00:00    | Workspace initialized — all folders and skills created  | Claude |
<!-- New entries prepend above this line -->

---

## Agent Skills

| Skill            | Command              | Trigger                         | Status      | Script |
|------------------|----------------------|---------------------------------|-------------|--------|
| Triage           | `/triage`            | New items in `Needs_Action/`    | ✅ Active    | [triage.md](.claude/commands/triage.md) |
| Approve          | `/approve`           | Plans ready in `Plans/`         | ✅ Active    | [approve.md](.claude/commands/approve.md) |
| Social Poster    | `/social_poster`     | On demand                       | ✅ Active    | [SKILL.md](.claude/skills/social_poster/SKILL.md) |
| CEO Briefing     | `/ceo_briefing`      | Scheduled / on demand           | ✅ Active    | [SKILL.md](.claude/skills/ceo_briefing/SKILL.md) |
| Ralph Loop       | `/ralph_loop`        | Autonomous reasoning trigger    | ✅ Active    | [SKILL.md](.claude/skills/ralph_loop/SKILL.md) |
| Odoo Invoice     | `/odoo_invoice`      | Invoice request                 | ✅ Active    | [SKILL.md](.claude/skills/odoo_invoice/SKILL.md) |
| Odoo Create      | `/odoo_create`       | New customer/partner            | ✅ Active    | [SKILL.md](.claude/skills/odoo_create/SKILL.md) |
| Odoo Report      | `/odoo_report`       | Business summary request        | ✅ Active    | [SKILL.md](.claude/skills/odoo_report/SKILL.md) |
| Odoo Search      | `/odoo_search`       | Lookup customer/invoice         | ✅ Active    | [SKILL.md](.claude/skills/odoo_search/SKILL.md) |
| Summarize        | `/summarize`         | On demand / triage              | ✅ Integrated | Skills/Skills/ |
| Draft Reply      | `/draft-reply`       | Email in pipeline               | ✅ Integrated | Skills/Skills/ |
| File & Tag       | `/file-and-tag`      | After triage                    | ✅ Integrated | Skills/Skills/ |
| LinkedIn Watcher | `/linkedin-watcher`  | Background monitor              | ✅ Integrated | Skills/Skills/ |

---

## MCP Servers

| Server       | Port / Command                              | Integrates With         | Status      |
|--------------|---------------------------------------------|-------------------------|-------------|
| Email MCP    | `python mcp_servers/email_server.py`        | Gmail (OAuth 2.0)       | ✅ Active    |
| Facebook MCP | `python mcp_servers/facebook-mcp/facebook_server.py` | Facebook + Instagram | ✅ Active |
| Twitter MCP  | `python mcp_servers/twitter-mcp/twitter_server.py`   | Twitter/X API v2        | ✅ Active    |
| Odoo MCP     | `python mcp_servers/odoo/odoo_server.py`    | Odoo ERP (localhost:8069) | ✅ Active  |

---

## Watcher Scripts

| Watcher          | Monitors                   | Trigger          | Status      |
|------------------|----------------------------|------------------|-------------|
| `file_watcher.py`    | Local folder changes       | File created/modified | ✅ Active |
| `gmail_watcher.py`   | Gmail inbox               | New email         | ✅ Active    |
| `linkedin_watcher.py`| LinkedIn notifications    | Mentions/messages | ✅ Active    |
| `facebook_watcher.py`| Facebook page inbox       | New messages      | ✅ Active    |
| `twitter_watcher.py` | Twitter/X mentions        | New mentions      | ✅ Active    |

---

## Quick Commands

```bash
# Start all watchers
python Watchers/file_watcher.py
python Watchers/gmail_watcher.py
python Watchers/linkedin_watcher.py
python Watchers/facebook_watcher.py
python Watchers/twitter_watcher.py

# Run CEO briefing
python Scripts/ceo_briefing.py

# Schedule briefing (Windows Task Scheduler)
Scripts/schedule_briefing.bat

# Claude Code slash commands
/triage              # Classify and plan all pending Needs_Action/ items
/approve             # Review and execute plans from Plans/
/triage <file>       # Triage a specific file
/approve all         # Process all plans at once
```

---

## Knowledge Base

- [Company Handbook](Company_Handbook.md) — Operating procedures and preferences
- [Conversation Log](Memory/Memory/conversation_log.md) — Action history
- [Business Goals](Memory/business_goals.md) — Strategic objectives

---

## Architecture

```
hack0aliza-gold/
├── Dashboard.md                # This file — nerve center
├── Company_Handbook.md         # AI employee operating rules
│
├── Watchers/                   # 5 background monitoring scripts
│   ├── file_watcher.py
│   ├── gmail_watcher.py
│   ├── linkedin_watcher.py
│   ├── facebook_watcher.py
│   └── twitter_watcher.py
│
├── mcp_servers/                # 4 MCP servers for external actions
│   ├── email_server.py         # Gmail integration
│   ├── facebook-mcp/           # Facebook + Instagram
│   ├── twitter-mcp/            # Twitter/X
│   └── odoo/                   # Odoo ERP
│
├── Skills/                     # Python skill scripts
│   ├── social_orchestrator.py  # Multi-platform post coordinator
│   ├── social_media_poster.py  # Platform-specific posting
│   └── twitter_poster.py       # Twitter posting logic
│
├── .claude/skills/             # Agent skill definitions
│   ├── ceo_briefing/           # Automated CEO briefing
│   ├── ralph_loop/             # Autonomous reasoning loop
│   ├── social_poster/          # Social media posting skill
│   ├── odoo_invoice/           # Invoice management
│   ├── odoo_create/            # Partner/customer creation
│   ├── odoo_report/            # Business reporting
│   └── odoo_search/            # Data lookup
│
├── Scripts/                    # Utility and scheduling scripts
│   ├── ceo_briefing.py
│   ├── run_ceo_briefing.bat
│   └── schedule_briefing.bat
│
├── Needs_Action/               # Triaged items awaiting Claude
├── Plans/                      # Claude-generated execution plans
├── Pending_Approval/           # Awaiting human review
├── Approved/                   # Human-approved — AI executes
├── Rejected/                   # Human-rejected with feedback
├── Done/                       # Completed work archive
├── Logs/                       # Full audit trail
├── Memory/                     # Persistent AI memory
└── Ralph/                      # Autonomous agent loop
```
