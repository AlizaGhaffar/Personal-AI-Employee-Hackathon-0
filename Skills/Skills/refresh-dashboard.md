# Skill: Refresh Dashboard

> Update Dashboard.md with real-time counts and system health status.

---

## Overview

| Field         | Value                                        |
|---------------|----------------------------------------------|
| **Command**   | `/refresh-dashboard` (planned)               |
| **Trigger**   | On demand, or after pipeline changes         |
| **Input**     | Current state of all pipeline folders        |
| **Output**    | Updated `Dashboard.md`                       |
| **Autonomy**  | Fully autonomous                             |
| **Status**    | Planned                                      |

---

## What It Does

1. **Counts** files in each pipeline folder (Inbox, Needs_Action, Plans, etc.)
2. **Checks** watcher status (File Watcher, Gmail Watcher)
3. **Reads** recent log entries from `Logs/`
4. **Updates** Dashboard.md metrics table
5. **Updates** system health section
6. **Updates** pipeline section with current items
7. **Updates** recent activity with latest log entries

---

## Metrics Updated

| Metric              | Source                          |
|---------------------|---------------------------------|
| Inbox Items         | Count of files in `Inbox/`      |
| Needs Action        | Count of files in `Needs_Action/` |
| Pending Approval    | Count of files in `Pending_Approval/` |
| Done (this week)    | Count of files in `Done/` from this week |
| Pending Messages    | Count of unread emails (Gmail API) |

## System Health Checks

| Component        | Check                                    |
|------------------|------------------------------------------|
| Folder Structure | All pipeline folders exist               |
| File Watcher     | `Watchers/file_watcher.py` process alive |
| Gmail Watcher    | `Watchers/gmail_watcher.py` process alive|
| Claude Code Link | `.claude/` config present                |
| Email MCP        | MCP email server responding              |

---

## Safety Rules

- Read-only scan of folders — never modifies pipeline files
- Only modifies `Dashboard.md`
- No external calls needed
