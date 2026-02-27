# Personal AI Employee — Hackathon Project

> A fully autonomous AI-powered personal employee built with Claude Code, Python watchers, and MCP integrations. Monitors inboxes, triages tasks, drafts responses, manages business data, and posts to social media — all through a human-in-the-loop approval pipeline.

---

## Tier Achievement

| Tier | Status |
|------|--------|
| Bronze — Foundation (Vault, 1 watcher, folder structure, agent skills) | ✅ Complete |
| Silver — Functional Assistant (5 watchers, social posting, MCP servers, HITL workflow, scheduling) | ✅ Complete |
| Gold — Autonomous Employee (Full cross-domain automation, ERP integration, CEO briefing, autonomous loop) | ✅ Complete |

---

## Overview

**Personal AI Employee (Gold Tier: Autonomous Employee)** is a hackathon project that turns Claude Code into a working AI employee. It continuously monitors communication channels, classifies incoming items by priority, generates execution plans, and waits for human approval before taking action. The system integrates with Gmail, LinkedIn, Facebook, Twitter, and Odoo (ERP) to cover email, social media, and business operations in one unified workspace.

---

## Key Features

| Feature | Description |
|---|---|
| **Email Monitoring** | Gmail watcher reads and triages incoming emails automatically |
| **Social Media** | Posts to Facebook, Instagram, and Twitter with human approval |
| **LinkedIn Watcher** | Monitors LinkedIn activity via browser automation |
| **Odoo ERP Integration** | Creates and manages invoices, customers, and sales orders |
| **AI Pipeline** | Items flow through a structured approval pipeline before any action |
| **Skill System** | Modular skills: triage, approve, summarize, draft-reply, and more |
| **Dashboard** | Real-time markdown dashboard showing system health and metrics |
| **Audit Logs** | Every action is timestamped and logged in `Logs/` |

---

## Architecture

```
hack0aliza-gold/
├── Dashboard.md            # Live nerve center — system health & metrics
├── Company_Handbook.md     # AI employee operating rules & preferences
│
├── Watchers/               # Background monitoring scripts (Python)
│   ├── file_watcher.py     # Monitors local folders for new items
│   ├── gmail_watcher.py    # Polls Gmail inbox via OAuth
│   ├── linkedin_watcher.py # LinkedIn activity monitor (browser automation)
│   ├── facebook_watcher.py # Facebook page message monitor
│   └── twitter_watcher.py  # Twitter/X mention monitor
│
├── mcp_servers/            # Model Context Protocol servers
│   ├── email_server.py     # Gmail MCP server
│   ├── facebook-mcp/       # Facebook & Instagram MCP server
│   └── twitter-mcp/        # Twitter/X MCP server
│
├── Skills/                 # Executable AI skill scripts
│   ├── social_orchestrator.py   # Coordinates multi-platform posting
│   ├── social_media_poster.py   # Handles individual platform posts
│   └── twitter_poster.py        # Twitter-specific posting logic
│
├── .claude/commands/       # Claude Code slash commands (SpecKit Plus)
│   ├── sp.specify.md       # Feature specification workflow
│   ├── sp.plan.md          # Architecture planning workflow
│   ├── sp.tasks.md         # Task generation workflow
│   └── sp.implement.md     # Implementation workflow
│
├── Needs_Action/           # Triaged items waiting for Claude
├── Plans/                  # Claude-generated execution plans
├── Pending_Approval/       # Awaiting human review before action
├── Approved/               # Human-approved — AI executes
├── Rejected/               # Human-rejected with feedback
├── Done/                   # Completed work archive
├── Logs/                   # Full audit trail
└── Memory/                 # Persistent AI memory & conversation log
```

---

## Item Pipeline

```
Inbox → Needs_Action → Plans → Pending_Approval → Approved → Done
                                                 ↘ Rejected
```

| Stage | Owner | What Happens |
|---|---|---|
| `Needs_Action/` | AI | Triage skill classifies items, adds metadata |
| `Plans/` | AI | Claude generates step-by-step execution plans |
| `Pending_Approval/` | Human | Plan waits for human review |
| `Approved/` | AI | AI executes the approved plan |
| `Rejected/` | Human | Feedback added, loops back for revision |
| `Done/` | System | Completed work archived with timestamp |
| `Logs/` | System | Every stage transition logged |

---

## Integrations

| Tool | Purpose | Auth |
|---|---|---|
| **Gmail API** | Email monitoring and drafting | OAuth 2.0 |
| **Facebook Graph API** | Page posts and inbox messages | Page Access Token |
| **Twitter/X API v2** | Tweet posting and mention monitoring | Bearer Token + OAuth |
| **Odoo ERP** | Invoices, customers, sales orders | XML-RPC |
| **Claude Code** | Core AI reasoning and generation | Anthropic API Key |
| **LinkedIn** | Activity monitoring | Browser session |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Claude Code CLI installed
- API keys configured in `.env` (see `.env.example`)

### Setup

```bash
# Clone the repository
git clone https://github.com/AlizaGhaffar/Personal-AI-Employee-Hackathon-0
cd Personal-AI-Employee-Hackathon-0

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# Start watchers
python Watchers/file_watcher.py
python Watchers/gmail_watcher.py
```

### Claude Code Slash Commands

```bash
/triage              # Classify and plan all pending items in Needs_Action/
/approve             # Review and execute plans from Plans/
/triage <file>       # Triage a specific file
/approve all         # Process all plans at once
```

---

## Priority System

| Level | Label | Response Time | AI Autonomy |
|---|---|---|---|
| P1 | Critical | Immediate | Alert owner first |
| P2 | Important | < 4 hours | Plan then ask |
| P3 | Routine | < 24 hours | Act autonomously |

---

## Approval Thresholds

- **Always requires approval:** Sending emails to clients, scheduling meetings, sharing data externally
- **AI acts autonomously:** Triage, summarization, drafting replies, moving files through pipeline, logging

---

## Tech Stack

- **AI Engine:** Claude Code (claude-sonnet-4-6) via Anthropic API
- **Language:** Python 3
- **Protocol:** Model Context Protocol (MCP) for tool integrations
- **ERP:** Odoo (local instance on port 8069)
- **Automation:** Browser automation via Playwright (LinkedIn)
- **Dev Framework:** Spec-Driven Development (SDD) via SpecKit Plus

---

## Project Structure Standards

This project follows **Spec-Driven Development (SDD)**:

- `.specify/memory/constitution.md` — Project principles
- `history/prompts/` — Full Prompt History Records (PHRs) for every AI interaction
- `history/adr/` — Architecture Decision Records

---

## Hackathon Context

Built for **Hackathon 0** — demonstrating how an AI employee can:

1. Replace manual inbox monitoring with automated watchers
2. Apply consistent business rules via the Company Handbook
3. Generate and execute plans with human oversight
4. Integrate across email, social media, and ERP in a single workspace
5. Maintain a full audit trail of every action taken

---

*Powered by Claude Code · Built with MCP · Human-in-the-loop by design*
