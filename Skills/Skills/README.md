# Agent Skills

> All AI functionality is implemented as Claude Code Agent Skills (slash commands).
> Each skill is documented here and defined in `.claude/commands/`.

---

## Skill Registry

### Active Skills (Working)

| Skill     | Command     | Trigger                    | Autonomy     | Definition          |
|-----------|-------------|----------------------------|--------------|---------------------|
| Triage    | `/triage`   | New items in `Needs_Action/` | Autonomous   | [triage.md](triage.md) |
| Approve   | `/approve`  | Plans ready in `Plans/`      | HITL         | [approve.md](approve.md) |

### Social Media Skills

| Skill           | Command         | Trigger                                    | Autonomy | Definition                                                              |
|-----------------|-----------------|--------------------------------------------|----------|-------------------------------------------------------------------------|
| Social Poster   | `/social-post`  | "post to Facebook/Instagram", FB message   | HITL     | [social_poster/SKILL.md](../../.claude/skills/social_poster/SKILL.md)  |

### Reporting & Briefing Skills

| Skill          | Command          | Trigger                                     | Autonomy     | Definition                                                                |
|----------------|------------------|---------------------------------------------|--------------|---------------------------------------------------------------------------|
| CEO Briefing   | `/ceo-briefing`  | Thursday 12pm (scheduled) or on demand      | Autonomous   | [ceo_briefing/SKILL.md](../../.claude/skills/ceo_briefing/SKILL.md)       |

### Autonomous Loop Skills

| Skill        | Command        | Trigger                                      | Autonomy     | Definition                                                            |
|--------------|----------------|----------------------------------------------|--------------|-----------------------------------------------------------------------|
| Ralph Loop   | `/ralph-loop`  | Multi-step task, "keep going until done"     | Autonomous   | [ralph_loop/SKILL.md](../../.claude/skills/ralph_loop/SKILL.md)       |

### Odoo Skills

| Skill          | Command          | Trigger                                      | Autonomy     | Definition                                                          |
|----------------|------------------|----------------------------------------------|--------------|---------------------------------------------------------------------|
| Odoo Search    | `/odoo_search`   | "find customer", "look up invoice"           | Autonomous   | [odoo_search/SKILL.md](../../.claude/skills/odoo_search/SKILL.md)   |
| Odoo Create    | `/odoo_create`   | "add new customer", "register vendor"        | HITL         | [odoo_create/SKILL.md](../../.claude/skills/odoo_create/SKILL.md)   |
| Odoo Invoice   | `/odoo_invoice`  | "bill [Name]", email invoice request         | HITL         | [odoo_invoice/SKILL.md](../../.claude/skills/odoo_invoice/SKILL.md) |
| Odoo Report    | `/odoo_report`   | "show revenue", "weekly summary"             | Autonomous   | [odoo_report/SKILL.md](../../.claude/skills/odoo_report/SKILL.md)   |

### Watchers (Automated Detection)

| Skill             | Script                           | Trigger               | Autonomy   | Definition                                    |
|-------------------|----------------------------------|-----------------------|------------|-----------------------------------------------|
| LinkedIn Watcher  | `Watchers/linkedin_watcher.py`   | Unread LinkedIn msgs  | Autonomous | [linkedin-watcher.md](linkedin-watcher.md)    |
| Facebook Watcher  | `Watchers/facebook_watcher.py`   | New Page inbox msgs   | Autonomous | [social_poster/SKILL.md](../../.claude/skills/social_poster/SKILL.md) |

### Integrated Skills (Built into Triage/Approve)

| Skill        | Command            | Trigger                 | Autonomy     | Definition                    |
|--------------|--------------------|-------------------------|--------------|-------------------------------|
| Summarize    | `/summarize`       | On demand / after triage | Autonomous   | [summarize.md](summarize.md) |
| Draft Reply  | `/draft-reply`     | Email items in pipeline  | Draft only   | [draft-reply.md](draft-reply.md) |
| File & Tag   | `/file-and-tag`    | After triage             | Autonomous   | [file-and-tag.md](file-and-tag.md) |
| Refresh Dashboard | `/refresh-dashboard` | After pipeline changes | Autonomous | [refresh-dashboard.md](refresh-dashboard.md) |

---

## Pipeline Flow

```
Inbox/ → [file_watcher] → Needs_Action/
                              ↓
                        [/triage] ← classifies, tags, creates plan
                              ↓
                          Plans/
                              ↓
                    [/approve] ← human reviews
                     ↙        ↘
               Approved/    Rejected/
                  ↓
            [execute plan]
                  ↓
               Done/
```

## Skill Architecture

```
Skills/                          # Skill definitions & documentation
├── README.md                    # This file — skill registry
├── triage.md                    # Triage & Classify skill
├── approve.md                   # Approve & Execute skill
├── summarize.md                 # Summarize skill
├── draft-reply.md               # Draft Reply skill
├── file-and-tag.md              # File & Tag skill
└── refresh-dashboard.md         # Refresh Dashboard skill

.claude/commands/                # Slash command implementations
├── triage.md                    # /triage command
├── approve.md                   # /approve command
└── sp.*.md                      # SpecKit Plus framework commands

.claude/skills/                  # Odoo Agent Skills (self-contained)
├── odoo_search/SKILL.md         # /odoo_search — read-only lookup
├── odoo_create/SKILL.md         # /odoo_create — draft records, HITL
├── odoo_invoice/SKILL.md        # /odoo_invoice — generate invoices, HITL
└── odoo_report/SKILL.md         # /odoo_report — business summaries

Ralph/
└── ralph_loop.py                # Autonomous loop orchestrator script

Skills/                          # Executable skill scripts
└── social_media_poster.py       # HITL Facebook/Instagram poster

mcp_servers/facebook-mcp/        # Facebook + Instagram MCP tools
└── facebook_server.py           # fb_get_messages, social_draft_post, fb_post_*, ig_post_*
```

---

## How Skills Work

1. **Slash commands** live in `.claude/commands/` — Claude Code loads them as `/command`
2. **Skill definitions** live in `Skills/` — human-readable documentation of what each skill does
3. **Watchers** (`Watchers/`) detect events and prepare items for skills to process
4. **Company Handbook** defines the rules skills follow (priority, approval thresholds, tone)

## Adding New Skills

1. Create the slash command: `.claude/commands/<skill-name>.md`
2. Create the skill definition: `Skills/<skill-name>.md`
3. Document it in this README's Skill Registry table
4. Follow the pattern: read input → process → write output → log action
5. Define: trigger, autonomy level, input/output, safety rules
