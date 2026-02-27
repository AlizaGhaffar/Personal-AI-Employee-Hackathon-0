"""
Odoo MCP Server - Gold Tier
Exposes Odoo business tools to Claude Code via Model Context Protocol (JSON-RPC).

Tools:
  - odoo_search_partners    : Search customers/vendors
  - odoo_create_partner     : Create a new customer or vendor
  - odoo_search_invoices    : Search invoices/bills
  - odoo_get_invoice        : Get full invoice details
  - odoo_create_invoice     : Create a new customer invoice
  - odoo_search_sales       : Search sales orders
  - odoo_get_accounting_summary : Accounting overview (for CEO briefing)
  - odoo_execute_method     : Generic Odoo model method executor

Auth: JSON-RPC with username + API key (Odoo 14+).
Logging: File-only (never stdout — corrupts MCP stdio transport).
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path
from datetime import datetime, date
from typing import Any

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = PROJECT_ROOT / "Logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env")

# ── Config from .env ────────────────────────────────────────────────────────
ODOO_URL      = os.getenv("ODOO_URL", "http://localhost:8069").rstrip("/")
ODOO_DB       = os.getenv("ODOO_DB", "gold_business")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
ODOO_API_KEY  = os.getenv("ODOO_API_KEY", "")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", ODOO_API_KEY)  # API key acts as password

# ── Logging (file only — no stdout) ─────────────────────────────────────────
logger = logging.getLogger("OdooMCP")
log_file = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_OdooMCP.log"
_fh = logging.FileHandler(log_file, encoding="utf-8")
_fh.setFormatter(logging.Formatter("[%(asctime)s] %(name)s %(levelname)s: %(message)s"))
logger.addHandler(_fh)
logger.setLevel(logging.INFO)

# ── JSON-RPC Client ──────────────────────────────────────────────────────────
_uid: int | None = None
_rpc_id = 0


def _next_id() -> int:
    global _rpc_id
    _rpc_id += 1
    return _rpc_id


def _jsonrpc(service: str, method: str, args: list) -> Any:
    """Low-level JSON-RPC call to Odoo."""
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "id": _next_id(),
        "params": {
            "service": service,
            "method": method,
            "args": args,
        },
    }
    try:
        resp = requests.post(
            f"{ODOO_URL}/jsonrpc",
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            err = data["error"]
            raise RuntimeError(f"Odoo error {err.get('code')}: {err.get('message')} — {err.get('data', {}).get('message', '')}")
        return data.get("result")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Cannot connect to Odoo at {ODOO_URL}. Is Odoo running?")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Odoo request timed out after 30s.")


def _authenticate() -> int:
    """Authenticate and return uid. Cached after first call."""
    global _uid
    if _uid is not None:
        return _uid
    uid = _jsonrpc("common", "authenticate", [ODOO_DB, ODOO_USERNAME, ODOO_API_KEY, {}])
    if not uid:
        raise RuntimeError(
            f"Odoo authentication failed for user '{ODOO_USERNAME}'. "
            "Check ODOO_USERNAME and ODOO_API_KEY in .env"
        )
    _uid = uid
    logger.info(f"Authenticated as uid={uid} db={ODOO_DB}")
    return uid


def _execute(model: str, method: str, args: list = None, kwargs: dict = None) -> Any:
    """Execute an Odoo model method via JSON-RPC."""
    uid = _authenticate()
    args = args or []
    kwargs = kwargs or {}
    return _jsonrpc(
        "object",
        "execute_kw",
        [ODOO_DB, uid, ODOO_API_KEY, model, method, args, kwargs],
    )


def _log_action(action: str, details: dict):
    """Append action to daily audit log."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "actor": "odoo_mcp",
        **details,
    }
    logger.info(json.dumps(entry))
    daily = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_odoo_actions.json"
    records = []
    if daily.exists():
        try:
            records = json.loads(daily.read_text(encoding="utf-8"))
        except Exception:
            records = []
    records.append(entry)
    daily.write_text(json.dumps(records, indent=2), encoding="utf-8")


# ── MCP Server ───────────────────────────────────────────────────────────────
mcp = FastMCP("odoo")


# ─────────────────────────────────────────────────────────────────────────────
# PARTNERS (Customers / Vendors)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def odoo_search_partners(
    name: str = "",
    is_customer: bool | None = None,
    is_vendor: bool | None = None,
    limit: int = 20,
) -> str:
    """
    Search Odoo customers and vendors (res.partner).

    Args:
        name: Filter by name (partial match). Leave empty for all.
        is_customer: True = customers only, False = non-customers, None = any
        is_vendor: True = vendors only, False = non-vendors, None = any
        limit: Max results (default 20)

    Returns: JSON array of partners with id, name, email, phone, is_customer, is_vendor
    """
    domain = []
    if name:
        domain.append(["name", "ilike", name])
    if is_customer is not None:
        domain.append(["customer_rank", ">" if is_customer else "=", 0])
    if is_vendor is not None:
        domain.append(["supplier_rank", ">" if is_vendor else "=", 0])

    partners = _execute(
        "res.partner", "search_read",
        [domain],
        {
            "fields": ["id", "name", "email", "phone", "mobile",
                       "customer_rank", "supplier_rank", "street",
                       "city", "country_id"],
            "limit": min(limit, 100),
        },
    )

    _log_action("search_partners", {"query": name, "count": len(partners)})
    return json.dumps(partners, indent=2, default=str)


@mcp.tool()
def odoo_create_partner(
    name: str,
    email: str = "",
    phone: str = "",
    is_customer: bool = True,
    is_vendor: bool = False,
    street: str = "",
    city: str = "",
) -> str:
    """
    Create a new customer or vendor in Odoo.

    Args:
        name: Full name of the partner (required)
        email: Email address
        phone: Phone number
        is_customer: Mark as customer (default True)
        is_vendor: Mark as vendor (default False)
        street: Street address
        city: City

    Returns: JSON with new partner id and name
    """
    vals = {
        "name": name,
        "customer_rank": 1 if is_customer else 0,
        "supplier_rank": 1 if is_vendor else 0,
    }
    if email:
        vals["email"] = email
    if phone:
        vals["phone"] = phone
    if street:
        vals["street"] = street
    if city:
        vals["city"] = city

    partner_id = _execute("res.partner", "create", [vals])
    _log_action("create_partner", {"name": name, "id": partner_id, "email": email})

    return json.dumps({
        "status": "created",
        "id": partner_id,
        "name": name,
        "message": f"Partner '{name}' created with id={partner_id}",
    })


# ─────────────────────────────────────────────────────────────────────────────
# INVOICES
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def odoo_search_invoices(
    state: str = "all",
    partner_name: str = "",
    limit: int = 20,
) -> str:
    """
    Search customer invoices in Odoo (account.move).

    Args:
        state: Filter by status — 'draft', 'posted' (confirmed), 'cancel', 'all' (default)
        partner_name: Filter by customer name (partial match)
        limit: Max results (default 20)

    Returns: JSON array of invoices with id, name, partner, amount, state, date
    """
    domain = [["move_type", "=", "out_invoice"]]  # customer invoices only
    if state != "all":
        domain.append(["state", "=", state])
    if partner_name:
        domain.append(["partner_id.name", "ilike", partner_name])

    invoices = _execute(
        "account.move", "search_read",
        [domain],
        {
            "fields": ["id", "name", "partner_id", "amount_total", "amount_residual",
                       "state", "invoice_date", "invoice_date_due", "currency_id"],
            "limit": min(limit, 100),
            "order": "invoice_date desc",
        },
    )

    _log_action("search_invoices", {"state": state, "partner": partner_name, "count": len(invoices)})
    return json.dumps(invoices, indent=2, default=str)


@mcp.tool()
def odoo_get_invoice(invoice_id: int) -> str:
    """
    Get full details of a specific invoice including line items.

    Args:
        invoice_id: Odoo invoice ID (integer)

    Returns: JSON with full invoice details and line items
    """
    invoices = _execute(
        "account.move", "read",
        [[invoice_id]],
        {
            "fields": ["id", "name", "partner_id", "amount_untaxed", "amount_tax",
                       "amount_total", "amount_residual", "state", "invoice_date",
                       "invoice_date_due", "invoice_line_ids", "currency_id",
                       "payment_state", "narration"],
        },
    )
    if not invoices:
        return json.dumps({"error": f"Invoice {invoice_id} not found"})

    invoice = invoices[0]

    # Fetch line items
    if invoice.get("invoice_line_ids"):
        lines = _execute(
            "account.move.line", "read",
            [invoice["invoice_line_ids"]],
            {"fields": ["name", "quantity", "price_unit", "price_subtotal", "tax_ids"]},
        )
        invoice["lines"] = lines

    _log_action("get_invoice", {"invoice_id": invoice_id, "name": invoice.get("name")})
    return json.dumps(invoice, indent=2, default=str)


@mcp.tool()
def odoo_create_invoice(
    partner_id: int,
    lines: str,
    invoice_date: str = "",
    due_date: str = "",
    notes: str = "",
) -> str:
    """
    Create a new customer invoice in Odoo (draft state — not confirmed).

    Args:
        partner_id: Odoo partner/customer ID (get from odoo_search_partners)
        lines: JSON array of line items. Each item:
               [{"name": "Service", "quantity": 1, "price_unit": 100.0}]
        invoice_date: Date in YYYY-MM-DD format (default: today)
        due_date: Payment due date in YYYY-MM-DD format
        notes: Optional notes/narration for the invoice

    Returns: JSON with new invoice id and name
    """
    try:
        line_items = json.loads(lines)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid lines JSON. Expected array of {name, quantity, price_unit}"})

    today = date.today().isoformat()
    invoice_vals = {
        "move_type": "out_invoice",
        "partner_id": partner_id,
        "invoice_date": invoice_date or today,
        "invoice_line_ids": [
            (0, 0, {
                "name": line.get("name", "Service"),
                "quantity": float(line.get("quantity", 1)),
                "price_unit": float(line.get("price_unit", 0)),
            })
            for line in line_items
        ],
    }
    if due_date:
        invoice_vals["invoice_date_due"] = due_date
    if notes:
        invoice_vals["narration"] = notes

    invoice_id = _execute("account.move", "create", [invoice_vals])

    # Read back name
    result = _execute("account.move", "read", [[invoice_id]], {"fields": ["name", "amount_total"]})
    inv_name = result[0]["name"] if result else f"INV/{invoice_id}"
    amount = result[0]["amount_total"] if result else 0

    _log_action("create_invoice", {
        "invoice_id": invoice_id, "name": inv_name,
        "partner_id": partner_id, "amount": amount,
    })

    return json.dumps({
        "status": "created",
        "id": invoice_id,
        "name": inv_name,
        "amount_total": amount,
        "state": "draft",
        "message": f"Invoice {inv_name} created (draft). Confirm in Odoo UI or use odoo_execute_method.",
    })


# ─────────────────────────────────────────────────────────────────────────────
# SALES ORDERS
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def odoo_search_sales(
    state: str = "all",
    partner_name: str = "",
    limit: int = 20,
) -> str:
    """
    Search sales orders in Odoo (sale.order).

    Args:
        state: Filter — 'draft', 'sent', 'sale' (confirmed), 'done', 'cancel', 'all'
        partner_name: Filter by customer name (partial match)
        limit: Max results (default 20)

    Returns: JSON array of sales orders
    """
    domain = []
    if state != "all":
        domain.append(["state", "=", state])
    if partner_name:
        domain.append(["partner_id.name", "ilike", partner_name])

    orders = _execute(
        "sale.order", "search_read",
        [domain],
        {
            "fields": ["id", "name", "partner_id", "amount_total", "state",
                       "date_order", "validity_date", "invoice_status"],
            "limit": min(limit, 100),
            "order": "date_order desc",
        },
    )

    _log_action("search_sales", {"state": state, "partner": partner_name, "count": len(orders)})
    return json.dumps(orders, indent=2, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# ACCOUNTING SUMMARY (CEO Briefing)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def odoo_get_accounting_summary() -> str:
    """
    Get a business accounting overview for CEO briefing and weekly audit.
    Pulls: invoice totals by status, overdue invoices, recent sales, top customers.

    Returns: JSON with full accounting summary
    """
    today = date.today().isoformat()

    # Total invoiced (posted)
    posted = _execute(
        "account.move", "search_read",
        [[["move_type", "=", "out_invoice"], ["state", "=", "posted"]]],
        {"fields": ["amount_total", "amount_residual", "invoice_date_due", "partner_id"]},
    )

    total_invoiced = sum(inv["amount_total"] for inv in posted)
    total_outstanding = sum(inv["amount_residual"] for inv in posted)

    # Overdue invoices
    overdue = [
        inv for inv in posted
        if inv.get("amount_residual", 0) > 0
        and inv.get("invoice_date_due")
        and str(inv["invoice_date_due"]) < today
    ]

    # Draft invoices count
    drafts = _execute(
        "account.move", "search_count",
        [[["move_type", "=", "out_invoice"], ["state", "=", "draft"]]],
    )

    # Recent sales orders (last 30 days)
    sales = _execute(
        "sale.order", "search_read",
        [[["state", "in", ["sale", "done"]]]],
        {
            "fields": ["name", "partner_id", "amount_total", "date_order", "state"],
            "limit": 10,
            "order": "date_order desc",
        },
    )

    # Customer count
    customer_count = _execute(
        "res.partner", "search_count",
        [[["customer_rank", ">", 0]]],
    )

    summary = {
        "generated_at": datetime.now().isoformat(),
        "db": ODOO_DB,
        "invoicing": {
            "total_posted_invoices": len(posted),
            "total_invoiced_amount": round(total_invoiced, 2),
            "total_outstanding": round(total_outstanding, 2),
            "total_collected": round(total_invoiced - total_outstanding, 2),
            "draft_invoices": drafts,
            "overdue_count": len(overdue),
            "overdue_amount": round(sum(inv["amount_residual"] for inv in overdue), 2),
        },
        "sales": {
            "recent_confirmed_orders": len(sales),
            "recent_orders_total": round(sum(s["amount_total"] for s in sales), 2),
            "recent_orders": [
                {
                    "name": s["name"],
                    "customer": s["partner_id"][1] if s["partner_id"] else "Unknown",
                    "amount": s["amount_total"],
                    "date": str(s["date_order"]),
                }
                for s in sales
            ],
        },
        "customers": {
            "total_customers": customer_count,
        },
    }

    _log_action("get_accounting_summary", {
        "total_invoiced": total_invoiced,
        "overdue_count": len(overdue),
    })
    return json.dumps(summary, indent=2, default=str)


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC EXECUTOR
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def odoo_execute_method(
    model: str,
    method: str,
    args: str = "[]",
    kwargs: str = "{}",
) -> str:
    """
    Execute any Odoo model method via JSON-RPC (power tool).
    Use when other specific tools don't cover your need.

    Args:
        model: Odoo model name (e.g. 'account.move', 'res.partner', 'sale.order')
        method: Method name (e.g. 'search_read', 'create', 'write', 'action_post')
        args: JSON array of positional arguments (default '[]')
        kwargs: JSON object of keyword arguments (default '{}')

    Example — confirm an invoice:
        model='account.move', method='action_post', args='[[42]]'

    Returns: Raw JSON result from Odoo
    """
    try:
        parsed_args = json.loads(args)
        parsed_kwargs = json.loads(kwargs)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON args/kwargs: {e}"})

    result = _execute(model, method, parsed_args, parsed_kwargs)
    _log_action("execute_method", {"model": model, "method": method})
    return json.dumps(result, indent=2, default=str)


if __name__ == "__main__":
    mcp.run(transport="stdio")
