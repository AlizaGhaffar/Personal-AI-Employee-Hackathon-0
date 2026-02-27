"""
One-time script to re-authenticate Gmail OAuth.
Run this directly: python mcp_servers/reauth.py
It will open your browser for consent and save a new token.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gmail_auth import authenticate

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

if __name__ == "__main__":
    print("Starting Gmail OAuth flow...")
    print("A browser window will open for Google sign-in.")
    creds = authenticate(SCOPES)
    print(f"Authentication successful! Token saved.")
    print(f"Scopes: {creds.scopes}")
