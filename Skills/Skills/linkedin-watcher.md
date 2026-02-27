# Skill: LinkedIn Watcher

> Monitors LinkedIn messaging via Playwright for sales/business keywords and creates action files.

---

## Overview

| Field         | Value                                        |
|---------------|----------------------------------------------|
| **Script**    | `Watchers/linkedin_watcher.py`               |
| **Trigger**   | Polling every 60 seconds                     |
| **Input**     | Unread LinkedIn messages                     |
| **Output**    | `LINKEDIN_*.md` files in `Needs_Action/`     |
| **Autonomy**  | Fully autonomous detection                   |
| **Pattern**   | BaseWatcher + Playwright (same as WhatsApp)  |

---

## How It Works

1. **Launches** Playwright with persistent session (login saved)
2. **Navigates** to `https://www.linkedin.com/messaging/`
3. **Scans** unread conversations for keyword matches
4. **Clicks** into matched chats to read full conversation
5. **Creates** `.md` file in `Needs_Action/` with YAML frontmatter
6. **Logs** activity to `Logs/linkedin.log`

## Keywords Monitored

`sales`, `client`, `project`, `business`, `invoice`, `deal`, `partnership`, `proposal`, `pricing`, `budget`, `service`, `offer`

## First Run

First run opens a visible browser window. User must log in to LinkedIn manually once — the session is saved to `Watchers/.linkedin_session/` for all future runs.

## Pipeline Position

```
LinkedIn Messages → [linkedin_watcher] → Needs_Action/ → [/triage] → Plans/
```

## Start Command

```bash
python Watchers/linkedin_watcher.py
```

## Safety Rules

- Read-only — never sends messages or replies
- Persistent session stored locally (never synced)
- Keyword-only detection — ignores non-matching messages
- Deduplicates via `.linkedin_processed.json`
