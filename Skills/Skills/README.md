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

### Watchers (Automated Detection)

| Skill            | Script                          | Trigger              | Autonomy     | Definition                              |
|------------------|---------------------------------|----------------------|--------------|-----------------------------------------|
| LinkedIn Watcher | `Watchers/linkedin_watcher.py`  | Unread LinkedIn msgs | Autonomous   | [linkedin-watcher.md](linkedin-watcher.md) |

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
