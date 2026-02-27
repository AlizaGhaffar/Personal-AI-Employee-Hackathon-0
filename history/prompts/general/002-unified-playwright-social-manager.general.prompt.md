---
id: "002"
title: "Unified Playwright Social Media Manager"
stage: green
date: 2026-02-26
surface: agent
model: claude-sonnet-4-6
feature: none
branch: master
user: operator
command: none
labels: ["social-media","playwright","linkedin","facebook","instagram","twitter","orchestrator","hitl"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - Skills/social_login.py
  - Skills/social_orchestrator.py
  - Watchers/file_watcher.py
  - Pending_Approval/POST_example_template.md
tests:
  - dry-run: python Skills/social_orchestrator.py --dry-run --file <spec>
  - session check: python Skills/social_login.py --check
---

## Prompt

Create a single social media manager that handles all platforms (LinkedIn, Facebook, Instagram, Twitter) for my Gold Tier AI Employee.

Use Playwright with persistent sessions (login once, save forever).

Folder structure:
/Pending_Approval/ - AI drafts go here
/Approved/ - I move files here to approve
/Done/ - After posting
/sessions/ - Browser sessions for all platforms
/Logs/ - Error logs + screenshots

Workflow:
1. Run once to log in to all platforms → sessions saved
2. Trigger script creates POST_*.md in Pending_Approval/
3. I review and move to Approved/
4. Orchestrator detects → auto-posts to correct platform
5. Moves to Done/, logs everything

Platform-specific:
- LinkedIn: "Start a post" → editor → "Post"
- Facebook: "What's on your mind?" → "Post"
- Instagram: "Create" → image upload → caption → share
- Twitter: "Post" → tweet → "Post"

Retry 3 times, take screenshots on failure.

Keep it simple but robust.

## Response snapshot

Created two new files and updated the dispatcher:

1. **Skills/social_login.py** — Interactive login for all 4 platforms. Saves Playwright persistent contexts to `sessions/{platform}/`. Supports `--platform` flag for individual login and `--check` to verify existing sessions without opening a browser.

2. **Skills/social_orchestrator.py** — Unified watchdog-based orchestrator. Watches `Approved/` for `type: social_post` (and legacy `type: twitter_post`) files. Dispatches to platform-specific Playwright handlers with 3 retries and screenshots on failure. Moves successful posts to `Done/`. Also handles files already sitting in `Approved/` at startup.

3. **Watchers/file_watcher.py** — Updated `ApprovedFolderHandler` to route both `social_post` and `twitter_post` types through `social_orchestrator.py` instead of the deprecated API posters.

4. **Pending_Approval/POST_example_template.md** — Reusable template showing all YAML fields.

## Outcome

- ✅ Impact: Replaces fragmented API-based posters (social_media_poster.py, twitter_poster.py) with a single Playwright-based system. No API keys required. Sessions persist forever after one-time manual login.
- 🧪 Tests: Run with --dry-run to validate parsing without posting. Run python Skills/social_login.py --check to verify sessions.
- 📁 Files: 3 created (social_login.py, social_orchestrator.py, POST_example_template.md), 1 modified (file_watcher.py)
- 🔁 Next prompts: Test login flow for each platform; verify selectors with --dry-run first; add NSSM service wrapper for always-on operation
- 🧠 Reflection: Platform UI selectors are the fragile part — Instagram and LinkedIn change their DOM most frequently. Multiple fallback selectors per action provide resilience.

## Evaluation notes (flywheel)

- Failure modes observed: Platform DOM changes break selectors; Instagram text-only posts not supported via browser automation
- Graders run and results (PASS/FAIL): Not yet run — pending first real login test
- Prompt variant (if applicable): none
- Next experiment: Add selector version pinning or a self-healing selector refresh mechanism
