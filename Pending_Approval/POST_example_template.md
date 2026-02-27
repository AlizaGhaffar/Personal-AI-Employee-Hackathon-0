---
type: social_post
platform: linkedin
caption: "Your post text goes here. For Twitter, keep it under 280 characters."
image_path: ""
link_url: ""
status: pending
requires_approval: true
priority: P2
tags: [social, linkedin, post]
summary: "Example post template — copy and rename to POST_YYYYMMDD_platform.md"
---

# Social Post Draft — Example Template

## Post Content

**Platform:** linkedin ← change to: linkedin | facebook | instagram | twitter
**Caption:**

> Your post text goes here.

**Image Path:** (empty = no image; Instagram REQUIRES an image)

## Instructions

1. Edit platform and caption above
2. For Instagram: set `image_path: Images/your-image.jpg`
3. Move this file to `Approved/` to trigger posting
4. Watch `Logs/YYYY-MM-DD_social_orchestrator.log` for results
5. File moves to `Done/` automatically after successful post

## Platform Notes

| Platform  | Text Limit | Image Required | Notes                          |
|-----------|-----------|----------------|-------------------------------|
| linkedin  | ~3000     | Optional       | Rich text, no API key needed  |
| facebook  | ~63k      | Optional       | Personal feed or Page         |
| instagram | ~2200     | REQUIRED       | Set image_path                |
| twitter   | 280       | Optional       | Count characters carefully    |

---
*Template — rename and edit before approving*
