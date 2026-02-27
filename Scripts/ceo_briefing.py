#!/usr/bin/env python3
"""
CEO Weekly Business Briefing Generator
--------------------------------------
Runs every Thursday at 12:00 PM via Windows Task Scheduler.

Collects data from:
  - Odoo (revenue, invoices, sales orders) via direct JSON-RPC
  - Done/          — completed tasks this week
  - Needs_Action/  — inbox depth / bottlenecks
  - Plans/         — stuck plans (idle > 48h)
  - Pending_Approval/ — waiting for human > 24h
  - Memory/business_goals.md — KPI targets

Generates:
  Briefings/YYYY-MM-DD_ceo_briefing.md

Also calls Claude CLI to generate proactive suggestions from the raw data.

Usage:
  python Scripts/ceo_briefing.py
  python Scripts/ceo_briefing.py --dry-run   (print to stdout, don't save)
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Workspace Paths ────────────────────────────────────────────────────────────
WORKSPACE       = Path(__file__).resolve().parent.parent
BRIEFINGS_DIR   = WORKSPACE / "Briefings"
DONE_DIR        = WORKSPACE / "Done"
NEEDS_DIR       = WORKSPACE / "Needs_Action"
PLANS_DIR       = WORKSPACE / "Plans"
PENDING_DIR     = WORKSPACE / "Pending_Approval"
LOGS_DIR        = WORKSPACE / "Logs"
GOALS_FILE      = WORKSPACE / "Memory" / "business_goals.md"

load_dotenv(WORKSPACE / ".env")

# ── Odoo Config ────────────────────────────────────────────────────────────────
ODOO_URL      = os.getenv("ODOO_URL",      "http://localhost:8069").rstrip("/")
ODOO_DB       = os.getenv("ODOO_DB",       "gold_business")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
ODOO_API_KEY  = os.getenv("ODOO_API_KEY",  "")

# ── Logging ────────────────────────────────────────────────────────────────────
LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOGS_DIR / f"{date.today()}_ceo_briefing.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ceo_briefing")


# ── Odoo JSON-RPC ──────────────────────────────────────────────────────────────

_uid: int | None = None
_rpc_id = 0


def _next_id() -> int:
    global _rpc_id
    _rpc_id += 1
    return _rpc_id


def _jsonrpc(service: str, method: str, args: list):
    payload = {
        "jsonrpc": "2.0", "method": "call", "id": _next_id(),
        "params": {"service": service, "method": method, "args": args},
    }
    resp = requests.post(f"{ODOO_URL}/jsonrpc", json=payload, timeout=30,
                         headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"Odoo error: {err.get('message')} — {err.get('data', {}).get('message', '')}")
    return data.get("result")


def _authenticate() -> int:
    global _uid
    if _uid is not None:
        return _uid
    uid = _jsonrpc("common", "authenticate", [ODOO_DB, ODOO_USERNAME, ODOO_API_KEY, {}])
    if not uid:
        raise RuntimeError("Odoo auth failed — check ODOO_USERNAME and ODOO_API_KEY in .env")
    _uid = uid
    return uid


def _execute(model: str, method: str, args=None, kwargs=None):
    uid = _authenticate()
    return _jsonrpc("object", "execute_kw",
                    [ODOO_DB, uid, ODOO_API_KEY, model, method, args or [], kwargs or {}])


# ── Odoo Data Collection ───────────────────────────────────────────────────────

def get_weekly_revenue() -> dict:
    """Invoices posted this week (Mon–now)."""
    today     = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_str   = week_start.strftime("%Y-%m-%d")

    try:
        invoices = _execute(
            "account.move", "search_read",
            [[
                ["move_type", "=", "out_invoice"],
                ["state",     "=", "posted"],
                ["invoice_date", ">=", week_str],
            ]],
            {"fields": ["name", "partner_id", "amount_total", "invoice_date", "payment_state"], "limit": 100},
        )
        total = sum(inv.get("amount_total", 0) for inv in invoices)
        return {
            "total":    total,
            "count":    len(invoices),
            "invoices": invoices,
            "week_start": week_str,
        }
    except Exception as exc:
        log.warning(f"Could not fetch weekly revenue: {exc}")
        return {"total": 0, "count": 0, "invoices": [], "error": str(exc)}


def get_overdue_invoices() -> list[dict]:
    """All posted invoices with outstanding balance and past due date."""
    today_str = date.today().strftime("%Y-%m-%d")
    try:
        return _execute(
            "account.move", "search_read",
            [[
                ["move_type",     "=",  "out_invoice"],
                ["state",         "=",  "posted"],
                ["payment_state", "in", ["not_paid", "partial"]],
                ["invoice_date_due", "<", today_str],
            ]],
            {"fields": ["name", "partner_id", "amount_total", "amount_residual",
                        "invoice_date_due", "payment_state"], "limit": 50},
        )
    except Exception as exc:
        log.warning(f"Could not fetch overdue invoices: {exc}")
        return []


def get_recent_sales() -> list[dict]:
    """Confirmed sales orders from the past 7 days."""
    since = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        return _execute(
            "sale.order", "search_read",
            [[["state", "in", ["sale", "done"]], ["date_order", ">=", since]]],
            {"fields": ["name", "partner_id", "amount_total", "state", "date_order"], "limit": 20},
        )
    except Exception as exc:
        log.warning(f"Could not fetch recent sales: {exc}")
        return []


def get_draft_invoices_count() -> int:
    """Number of unconfirmed draft invoices."""
    try:
        return _execute(
            "account.move", "search_count",
            [[["move_type", "=", "out_invoice"], ["state", "=", "draft"]]],
        ) or 0
    except Exception:
        return 0


# ── File System Scanning ───────────────────────────────────────────────────────

def scan_done_this_week() -> list[dict]:
    """Files moved to Done/ in the last 7 days."""
    cutoff = datetime.now() - timedelta(days=7)
    items  = []
    if not DONE_DIR.exists():
        return items
    for f in DONE_DIR.iterdir():
        if f.is_file() and not f.name.startswith("."):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime >= cutoff:
                items.append({"name": f.name, "completed": mtime.strftime("%Y-%m-%d %H:%M")})
    return sorted(items, key=lambda x: x["completed"], reverse=True)


def scan_bottlenecks() -> dict:
    """Find stuck/delayed items across the pipeline."""
    now    = datetime.now()
    result = {"needs_action": [], "plans_stuck": [], "pending_old": []}

    # Needs_Action/ — anything older than 24h is delayed
    if NEEDS_DIR.exists():
        for f in NEEDS_DIR.iterdir():
            if f.is_file() and not f.name.startswith("."):
                age_h = (now - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() / 3600
                if age_h > 24:
                    result["needs_action"].append({
                        "name":   f.name,
                        "age_h":  round(age_h, 1),
                    })

    # Plans/ — plans older than 48h not moved to Pending_Approval
    if PLANS_DIR.exists():
        for f in PLANS_DIR.iterdir():
            if f.is_file() and not f.name.startswith("."):
                age_h = (now - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() / 3600
                if age_h > 48:
                    result["plans_stuck"].append({
                        "name":   f.name,
                        "age_h":  round(age_h, 1),
                    })

    # Pending_Approval/ — waiting > 24h for human sign-off
    if PENDING_DIR.exists():
        for f in PENDING_DIR.iterdir():
            if f.is_file() and not f.name.startswith("."):
                age_h = (now - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() / 3600
                if age_h > 24:
                    result["pending_old"].append({
                        "name":   f.name,
                        "age_h":  round(age_h, 1),
                    })

    return result


def read_business_goals() -> str:
    if GOALS_FILE.exists():
        return GOALS_FILE.read_text(encoding="utf-8")
    return "No business goals file found."


# ── KPI Status ─────────────────────────────────────────────────────────────────

def kpi_status(value, green, yellow) -> str:
    """Return 🟢 🟡 🔴 based on thresholds. green/yellow are (min, max) tuples or simple comparison."""
    if value >= green:
        return "🟢"
    if value >= yellow:
        return "🟡"
    return "🔴"


# ── Claude Suggestions ─────────────────────────────────────────────────────────

def get_claude_suggestions(data_summary: str) -> str:
    """Call Claude CLI to generate proactive suggestions from the briefing data."""
    prompt = (
        "You are a business advisor reviewing a weekly performance snapshot for a small business. "
        "Based on the data below, write 3–5 specific, actionable suggestions. "
        "Focus on: revenue opportunities, operational improvements, risk reduction. "
        "Be concise — one sentence per suggestion. No filler.\n\n"
        f"BUSINESS DATA:\n{data_summary}"
    )
    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True, text=True,
            cwd=str(WORKSPACE), timeout=120,
        )
        return result.stdout.strip() if result.stdout else "Could not generate suggestions."
    except Exception as exc:
        log.warning(f"Claude suggestions failed: {exc}")
        return "Suggestions unavailable — Claude CLI error."


# ── Briefing Assembly ──────────────────────────────────────────────────────────

def build_briefing(dry_run: bool = False) -> str:
    log.info("Collecting data...")

    today_str  = date.today().strftime("%Y-%m-%d")
    now_str    = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Odoo data
    revenue    = get_weekly_revenue()
    overdue    = get_overdue_invoices()
    sales      = get_recent_sales()
    drafts     = get_draft_invoices_count()

    # File system data
    done_items   = scan_done_this_week()
    bottlenecks  = scan_bottlenecks()
    goals_text   = read_business_goals()

    log.info(f"Revenue: ${revenue['total']:,.2f} | Overdue: {len(overdue)} | Done this week: {len(done_items)}")

    # KPI signals
    rev_signal      = kpi_status(revenue["total"],  5000, 2500)
    overdue_signal  = kpi_status(len(overdue),      0,    2, )  # inverted — lower is better
    done_signal     = kpi_status(len(done_items),   5,    2)

    # For overdue: 0=green, 1-2=yellow, ≥3=red (invert logic)
    if len(overdue) == 0:
        overdue_signal = "🟢"
    elif len(overdue) <= 2:
        overdue_signal = "🟡"
    else:
        overdue_signal = "🔴"

    # Revenue table rows
    rev_rows = "\n".join(
        f"| {inv.get('name','?')} | {inv.get('partner_id', ['?'])[1] if isinstance(inv.get('partner_id'), list) else '?'} "
        f"| ${inv.get('amount_total', 0):,.2f} | {inv.get('invoice_date','?')} | {inv.get('payment_state','?')} |"
        for inv in revenue["invoices"][:10]
    ) or "| — | No invoices posted this week | — | — | — |"

    # Overdue table rows
    overdue_rows = "\n".join(
        f"| {inv.get('name','?')} | {inv.get('partner_id', ['?'])[1] if isinstance(inv.get('partner_id'), list) else '?'} "
        f"| ${inv.get('amount_residual', 0):,.2f} | {inv.get('invoice_date_due','?')} |"
        for inv in overdue[:10]
    ) or "| — | None — all invoices current ✓ | — | — |"

    # Sales rows
    sales_rows = "\n".join(
        f"| {s.get('name','?')} | {s.get('partner_id', ['?'])[1] if isinstance(s.get('partner_id'), list) else '?'} "
        f"| ${s.get('amount_total', 0):,.2f} | {s.get('state','?')} | {str(s.get('date_order','?'))[:10]} |"
        for s in sales[:8]
    ) or "| — | No confirmed sales this week | — | — | — |"

    # Done items
    done_rows = "\n".join(
        f"| {item['name']} | {item['completed']} |"
        for item in done_items[:15]
    ) or "| No tasks completed this week | — |"

    # Bottleneck sections
    def fmt_bottleneck(items, label):
        if not items:
            return f"✓ No {label}"
        return "\n".join(f"- `{i['name']}` — {i['age_h']}h idle" for i in items)

    bottleneck_needs   = fmt_bottleneck(bottlenecks["needs_action"], "overdue inbox items")
    bottleneck_plans   = fmt_bottleneck(bottlenecks["plans_stuck"],  "stuck plans")
    bottleneck_pending = fmt_bottleneck(bottlenecks["pending_old"],  "stale pending approvals")

    any_bottlenecks = (
        bottlenecks["needs_action"] or
        bottlenecks["plans_stuck"] or
        bottlenecks["pending_old"]
    )

    # Claude suggestions — pass a compact data summary
    data_summary = (
        f"Weekly revenue: ${revenue['total']:,.2f} ({revenue['count']} invoices)\n"
        f"Overdue invoices: {len(overdue)}\n"
        f"Draft invoices not yet posted: {drafts}\n"
        f"Sales orders this week: {len(sales)}\n"
        f"Tasks completed: {len(done_items)}\n"
        f"Inbox backlog (>24h): {len(bottlenecks['needs_action'])} items\n"
        f"Plans stuck (>48h): {len(bottlenecks['plans_stuck'])} items\n"
        f"Pending approvals (>24h): {len(bottlenecks['pending_old'])} items\n"
    )
    log.info("Requesting Claude suggestions...")
    suggestions = get_claude_suggestions(data_summary)

    # ── Assemble briefing markdown ─────────────────────────────────────────────
    briefing = f"""# CEO Weekly Briefing — {today_str}

> Generated: {now_str} | Source: Odoo + Local Pipeline

---

## Executive Dashboard

| KPI                        | Value                          | Status          |
|----------------------------|--------------------------------|-----------------|
| Revenue this week          | ${revenue['total']:,.2f} ({revenue['count']} invoices) | {rev_signal}    |
| Overdue invoices           | {len(overdue)}                                          | {overdue_signal}|
| Draft invoices (unposted)  | {drafts}                                                | {'🟡' if drafts > 0 else '🟢'} |
| Tasks completed this week  | {len(done_items)}                                       | {done_signal}   |
| Pipeline bottlenecks       | {'⚠️ Yes — see below' if any_bottlenecks else '✓ None'} | {'🔴' if any_bottlenecks else '🟢'} |

---

## Revenue This Week ({revenue.get('week_start','?')} → {today_str})

**Total: ${revenue['total']:,.2f}** across {revenue['count']} posted invoice(s)

| Invoice | Customer | Amount | Date | Payment Status |
|---------|----------|--------|------|----------------|
{rev_rows}

---

## ⚠️ Overdue Invoices ({len(overdue)} unpaid)

| Invoice | Customer | Outstanding | Due Date |
|---------|----------|-------------|----------|
{overdue_rows}

---

## Sales Orders (last 7 days)

| Order | Customer | Amount | Status | Date |
|-------|----------|--------|--------|------|
{sales_rows}

---

## Completed Tasks This Week ({len(done_items)} items)

| Item | Completed At |
|------|--------------|
{done_rows}

---

## Pipeline Bottlenecks

### Inbox (Needs_Action/ > 24h)
{bottleneck_needs}

### Stuck Plans (Plans/ > 48h)
{bottleneck_plans}

### Stale Approvals (Pending_Approval/ > 24h)
{bottleneck_pending}

---

## Proactive Suggestions

{suggestions}

---

## Upcoming Actions Needed

- [ ] Review and post {drafts} draft invoice(s) in Odoo
- [ ] Follow up on {len(overdue)} overdue invoice(s)
{"".join(f"- [ ] Clear stuck item: `{i['name']}`\\n" for i in bottlenecks['plans_stuck'][:3])}
{"".join(f"- [ ] Approve pending: `{i['name']}`\\n" for i in bottlenecks['pending_old'][:3])}

---

*Auto-generated by `Scripts/ceo_briefing.py` | Logged: `Logs/{today_str}_ceo_briefing.log`*
"""

    # ── Save or print ──────────────────────────────────────────────────────────
    if dry_run:
        print(briefing)
    else:
        BRIEFINGS_DIR.mkdir(exist_ok=True)
        out_path = BRIEFINGS_DIR / f"{today_str}_ceo_briefing.md"
        out_path.write_text(briefing, encoding="utf-8")
        log.info(f"Briefing saved → {out_path}")
        # Also append to odoo log
        odoo_log = LOGS_DIR / "odoo.log"
        with odoo_log.open("a", encoding="utf-8") as f:
            f.write(f"[{now_str}] BRIEFING | revenue=${revenue['total']:.2f} | overdue={len(overdue)} | done={len(done_items)}\n")

    return briefing


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CEO Weekly Briefing Generator")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print briefing to stdout without saving")
    args = parser.parse_args()

    log.info("=" * 55)
    log.info("CEO BRIEFING — START")
    log.info("=" * 55)

    try:
        build_briefing(dry_run=args.dry_run)
        log.info("CEO BRIEFING — COMPLETE")
    except Exception as exc:
        log.error(f"Briefing failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
