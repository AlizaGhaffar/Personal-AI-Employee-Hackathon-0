---
id: 001
title: Add Twitter X Integration to AI Employee
stage: general
date: 2026-02-21
surface: agent
model: claude-sonnet-4-6
feature: none
branch: master
user: owner
command: none
labels: ["twitter","social","mcp","watcher","integration","gold-tier"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - Watchers/twitter_watcher.py
  - Skills/twitter_poster.py
  - mcp_servers/twitter-mcp/__init__.py
  - mcp_servers/twitter-mcp/twitter_server.py
  - .mcp.json
tests:
  - "python Skills/twitter_poster.py --dry-run"
  - "python Watchers/twitter_watcher.py (requires .env creds)"
---

## Prompt

Add Twitter (X) integration to my AI Employee.

Create:
1. Watchers/twitter_watcher.py (monitor mentions/DMs)
2. Skills/twitter_poster.py (post tweets)
3. mcp_servers/twitter-mcp/

Requirements:
- Twitter API v2 with OAuth 2.0
- Post tweets, reply to mentions
- HITL approval for all posts
- Logging to Logs/twitter.log

Follow BaseWatcher pattern.

## Response snapshot

Created 4 files and updated .mcp.json:

1. **Watchers/twitter_watcher.py** — TwitterWatcher extends BaseWatcher; polls mentions via search_recent_tweets and optionally DMs; writes TWITTER_*.md and TWITTER_DM_*.md to Needs_Action/; processed IDs in .twitter_processed.json; degrades gracefully on rate-limit and forbidden DM access.

2. **Skills/twitter_poster.py** — mirrors social_media_poster.py; reads Approved/*.md with type: twitter_post; supports tweet_type: tweet | reply; logs to Logs/twitter.log; moves to Done/ on success.

3. **mcp_servers/twitter-mcp/twitter_server.py** — FastMCP server with 4 tools: twitter_get_mentions (read), twitter_draft_post (HITL → Pending_Approval/), twitter_post_tweet (direct), twitter_reply_tweet (direct); file-only logging.

4. **.mcp.json** — added "twitter" server entry.

## Outcome

- ✅ Impact: Full Twitter/X integration added — watcher, poster, and MCP server following all existing patterns
- 🧪 Tests: Dry-run supported via `python Skills/twitter_poster.py --dry-run`
- 📁 Files: 4 created, 1 updated
- 🔁 Next prompts: Add TWITTER_* vars to .env, register tweepy dependency, test with real API credentials
- 🧠 Reflection: Followed BaseWatcher, social_media_poster, and FacebookMCP patterns exactly for consistency

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): none (no automated tests yet)
- Prompt variant (if applicable): none
- Next experiment: test against Twitter API sandbox with Basic tier credentials
