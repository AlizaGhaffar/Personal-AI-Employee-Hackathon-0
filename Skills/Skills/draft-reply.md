# Skill: Draft Reply

> Draft email and message responses for human review before sending.

---

## Overview

| Field         | Value                                        |
|---------------|----------------------------------------------|
| **Command**   | `/draft-reply` (planned)                     |
| **Trigger**   | Email items in pipeline, or on demand        |
| **Input**     | Email/message content from pipeline          |
| **Output**    | Draft in `Pending_Approval/` for review      |
| **Autonomy**  | Draft only — **never sends** without approval|
| **Status**    | Integrated into `/approve` email flow        |

---

## What It Does

1. **Reads** the original email/message content
2. **Analyzes** context, tone, and required response
3. **Drafts** a reply following Company Handbook tone rules
4. **Saves** draft to `Pending_Approval/` for human review
5. **Uses** Email MCP server for actual sending (after approval)

---

## Draft Rules

- Under 150 words (Company Handbook limit)
- Match formality to audience:
  - Internal → casual, brief
  - Client-facing → professional, warm
  - Escalations → formal, factual
- Always include clear subject line
- Use active voice ("Sent the invoice" not "The invoice was sent")
- No filler phrases

---

## Approval Flow

```
Email detected → Draft created → Pending_Approval/ → Human reviews
  → Approved/ → Email MCP sends → Done/
  → Rejected/ → Feedback added → Re-draft
```

---

## Safety Rules

- **NEVER** sends emails without explicit human approval
- **NEVER** auto-replies to any message
- All drafts go through `Pending_Approval/` pipeline
- Requires Email MCP server to be active for sending
- Human must move approval file from `Pending_Approval/` to `Approved/`
