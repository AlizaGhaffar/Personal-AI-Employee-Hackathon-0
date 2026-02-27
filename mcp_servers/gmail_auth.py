"""
Shared Gmail OAuth2 Authentication
Extracted from Watchers/gmail_watcher.py for reuse across
both the Gmail Watcher and Email MCP Server.
"""

import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

CREDENTIALS_FILE = PROJECT_ROOT / os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE = PROJECT_ROOT / os.getenv("GMAIL_TOKEN_FILE", "token.json")

logger = logging.getLogger("GmailAuth")


def authenticate(scopes: list[str]) -> Credentials:
    """
    Authenticate with Gmail API using OAuth2.
    Reuses saved token if valid, refreshes if expired,
    or opens browser for new consent.
    """
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                logger.error(f"Credentials file not found: {CREDENTIALS_FILE}")
                sys.exit(1)

            logger.info("Opening browser for Google OAuth consent...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), scopes
            )
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
            logger.info("Authentication successful!")

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        logger.info(f"Token saved to {TOKEN_FILE}")

    return creds
