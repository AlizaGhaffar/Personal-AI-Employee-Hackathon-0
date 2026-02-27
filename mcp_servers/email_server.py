"""
Email MCP Server - Silver Tier
Exposes Gmail tools to Claude Code via Model Context Protocol.

Tools:
  - search_emails: Search Gmail inbox (read-only, no approval)
  - draft_email: Create draft + approval file in Pending_Approval/
  - send_email: Send email (requires approved file in Approved/)

All actions logged to Logs/. No print() calls (corrupts stdio).
"""

import os
import sys
import json
import base64
import logging
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from googleapiclient.discovery import build

# Add parent to path for gmail_auth import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gmail_auth import authenticate, PROJECT_ROOT

# --- Config ---
load_dotenv(PROJECT_ROOT / ".env")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

PENDING_APPROVAL = PROJECT_ROOT / "Pending_Approval"
APPROVED = PROJECT_ROOT / "Approved"
DONE = PROJECT_ROOT / "Done"
LOGS_DIR = PROJECT_ROOT / "Logs"

for d in [PENDING_APPROVAL, APPROVED, DONE, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- Logging (file only, never stdout) ---
logger = logging.getLogger("EmailMCP")
log_file = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_EmailMCP.log"
handler = logging.FileHandler(log_file, encoding="utf-8")
handler.setFormatter(logging.Formatter("[%(asctime)s] %(name)s: %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# --- Gmail service (lazy init) ---
_service = None


def get_service():
    global _service
    if _service is None:
        creds = authenticate(SCOPES)
        _service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail API service initialized")
    return _service


def _sanitize(name: str) -> str:
    for ch in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
        name = name.replace(ch, '_')
    return name[:60]


def _log_action(action: str, details: dict):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action,
        "actor": "email_mcp",
        **details,
    }
    logger.info(json.dumps(log_entry))

    daily_log = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_email_actions.json"
    entries = []
    if daily_log.exists():
        try:
            entries = json.loads(daily_log.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, Exception):
            entries = []
    entries.append(log_entry)
    daily_log.write_text(json.dumps(entries, indent=2), encoding="utf-8")


# --- MCP Server ---
mcp = FastMCP("email")


@mcp.tool()
def search_emails(query: str, max_results: int = 10) -> str:
    """
    Search Gmail for emails matching a query.
    Uses Gmail search syntax (e.g. 'from:alice subject:invoice is:unread').
    Returns a JSON array of email summaries.

    Args:
        query: Gmail search query string
        max_results: Maximum number of results (1-50, default 10)
    """
    max_results = min(max(max_results, 1), 50)
    service = get_service()

    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    summaries = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        summaries.append({
            "id": msg_ref["id"],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        })

    _log_action("search_emails", {"query": query, "results_count": len(summaries)})
    return json.dumps(summaries, indent=2)


@mcp.tool()
def draft_email(to: str, subject: str, body: str) -> str:
    """
    Create a Gmail draft and write an approval request to Pending_Approval/.
    The email is NOT sent. A human must move the approval file to Approved/
    before it can be sent.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body text (plain text)
    """
    service = get_service()

    # Create MIME message
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Save as Gmail draft
    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()
    draft_id = draft["id"]

    # Write approval file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    safe_subject = _sanitize(subject)
    approval_filename = f"EMAIL_DRAFT_{safe_subject}_{timestamp}.md"
    approval_path = PENDING_APPROVAL / approval_filename

    approval_path.write_text(f"""---
type: approval_request
action: send_email
to: "{to}"
subject: "{subject}"
draft_id: "{draft_id}"
created: "{datetime.now().isoformat()}"
status: pending
requires_approval: true
priority: P2
---

# Email Draft - Awaiting Approval

| Field   | Value |
|---------|-------|
| To      | {to} |
| Subject | {subject} |
| Draft ID| {draft_id} |

## Body

{body}

## To Approve
Move this file to `Approved/` folder, then run `/approve`.

## To Reject
Move this file to `Rejected/` folder.
""", encoding="utf-8")

    _log_action("draft_email", {
        "to": to, "subject": subject,
        "draft_id": draft_id,
        "approval_file": approval_filename,
    })

    return json.dumps({
        "status": "draft_created",
        "draft_id": draft_id,
        "approval_file": approval_filename,
        "message": f"Draft saved in Gmail. Approval file created at Pending_Approval/{approval_filename}. "
                   "Human must move it to Approved/ before sending.",
    })


@mcp.tool()
def send_email(to: str, subject: str, body: str, approved_file: str = "") -> str:
    """
    Send an email via Gmail. REQUIRES prior human approval.
    If no approved_file is provided, creates a draft instead (safety guard).

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body text
        approved_file: Filename from Approved/ folder proving human approval
    """
    # Safety guard: no approval = create draft instead
    if not approved_file:
        _log_action("send_email_REDIRECTED", {
            "to": to, "reason": "no_approval_file_provided",
        })
        return draft_email(to, subject, body)

    approval_path = APPROVED / approved_file
    if not approval_path.exists():
        _log_action("send_email_BLOCKED", {
            "to": to, "reason": "approval_file_not_found",
            "expected": str(approval_path),
        })
        return json.dumps({
            "status": "blocked",
            "error": f"Approval file not found in Approved/: {approved_file}. "
                     "Email NOT sent. Creating draft instead.",
        })

    # Approval verified - send
    service = get_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    sent = service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()

    # Move approval file to Done/
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    done_path = DONE / f"{date_prefix}_{approved_file}"
    approval_path.rename(done_path)

    _log_action("send_email", {
        "to": to, "subject": subject,
        "message_id": sent.get("id"),
        "approval_file": approved_file,
        "moved_to": str(done_path),
    })

    return json.dumps({
        "status": "sent",
        "message_id": sent.get("id"),
        "to": to,
        "subject": subject,
    })


if __name__ == "__main__":
    mcp.run(transport="stdio")
