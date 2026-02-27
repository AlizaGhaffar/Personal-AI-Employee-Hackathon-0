# Skill: /social-post

Draft, review, and publish posts to Facebook and Instagram. All posts require human approval before going live — fully HITL.

---

## Metadata

| Field      | Value                                                    |
|------------|----------------------------------------------------------|
| Command    | `/social-post`                                           |
| Poster     | `Skills/social_media_poster.py`                          |
| Watcher    | `Watchers/facebook_watcher.py`                           |
| MCP Server | `mcp_servers/facebook-mcp/facebook_server.py`            |
| Autonomy   | HITL — drafts autonomously, human approves before post   |
| Log        | `Logs/social.log`                                        |

---

## When to Use This Skill

- User says "post this to Facebook" or "share this on Instagram"
- User wants to respond to a Facebook message with a public post
- User says "draft a social media post about [topic]"
- A Facebook message in `Needs_Action/` needs a public reply
- User wants to schedule or review upcoming social content

---

## HITL Flow

```
User request / Facebook message
        ↓
[Claude] social_draft_post MCP tool
        ↓
Pending_Approval/SOCIAL_*.md  ← human reviews here
        ↓ move to Approved/
[Skills/social_media_poster.py]
        ↓
Facebook Page / Instagram post published
        ↓
Done/  +  Logs/social.log
```

---

## Platforms

| Platform    | Supported Post Types          | Requires                         |
|-------------|-------------------------------|----------------------------------|
| Facebook    | Text, text + link, photo      | FACEBOOK_PAGE_ID + ACCESS_TOKEN  |
| Instagram   | Image with caption only       | INSTAGRAM_ACCOUNT_ID + linked FB Page |
| Both        | Image with caption            | All of the above                 |

> Note: Instagram does NOT support text-only posts via the API. An `image_url` is always required for Instagram posts.

---

## Execution

### 1. Draft a post (always first step)

Call `social_draft_post` MCP tool:
- `platform`: facebook | instagram | both
- `caption`: post text (required)
- `image_url`: public image URL (required for Instagram)
- `link_url`: optional link for Facebook posts
- `notes`: internal reviewer notes

Creates: `Pending_Approval/SOCIAL_<platform>_<timestamp>.md`

### 2. Human reviews

Open the file in `Pending_Approval/` — it contains:
- Full post preview
- Platform, caption, image URL
- Action checklist

Move to `Approved/` to publish, or `Rejected/` to cancel.

### 3. Execute (after human approval)

```bash
# Process all approved social posts
python Skills/social_media_poster.py

# Process a specific file
python Skills/social_media_poster.py --file Approved/SOCIAL_FB_20260219.md

# Validate without posting
python Skills/social_media_poster.py --dry-run
```

---

## Draft File Format (Pending_Approval/)

```markdown
---
type: social_post
platform: facebook
caption: "Your post text here"
image_url: "https://example.com/image.jpg"
link_url: ""
---
```

---

## Facebook Watcher

`Watchers/facebook_watcher.py` monitors the Facebook Page inbox:
- Polls every 120 seconds (configurable via `FACEBOOK_CHECK_INTERVAL_SECONDS`)
- Creates `Needs_Action/FACEBOOK_<conv_id>_<sender>.md` for new messages
- Tracks processed conversations in `.facebook_processed.json`

```bash
python Watchers/facebook_watcher.py
```

---

## .env Variables Required

```dotenv
FACEBOOK_PAGE_ID=123456789
FACEBOOK_ACCESS_TOKEN=EAAxxxx...   # Long-lived Page Access Token
INSTAGRAM_ACCOUNT_ID=987654321     # IG Business Account (optional)
FACEBOOK_GRAPH_VERSION=v20.0
FACEBOOK_CHECK_INTERVAL_SECONDS=120
```

**Getting a Facebook Page Access Token:**
1. Go to developers.facebook.com → Graph API Explorer
2. Select your App + Page
3. Add permissions: `pages_messaging`, `pages_read_engagement`, `pages_manage_posts`
4. Generate token → extend to 60 days via Token Debugger

---

## Safety

- `social_draft_post` never makes API calls — safe to call anytime
- `fb_post_text`, `fb_post_photo`, `ig_post_image` post immediately — only call after approval
- All posts logged to `Logs/social.log` with timestamp and post ID
- Approved files moved to `Done/` after successful post
- On API error: logged, file stays in `Approved/` for retry
