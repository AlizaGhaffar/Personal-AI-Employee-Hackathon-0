# Skill: /odoo_report

Pull live Odoo data and generate a business report. Read-only — no approval required.

---

## Metadata

| Field       | Value                                              |
|-------------|----------------------------------------------------|
| Command     | `/odoo_report`                                     |
| Autonomy    | Fully autonomous — read-only                       |
| Log         | `Logs/odoo.log`                                    |

---

## When to Use This Skill

- User asks "what's our revenue this month?" or "show me the business summary"
- User wants to see overdue invoices or unpaid bills
- User asks for a sales report or accounting overview
- User says "pull a report from Odoo" or "give me a snapshot"
- Preparing for a weekly briefing, CEO review, or financial check-in

---

## Execution

### 1. Determine report type

Parse from user input (default: `accounting`):
- `accounting` → full overview via `odoo_get_accounting_summary`
- `sales` → recent sales via `odoo_search_sales`
- `invoices` → invoice breakdown via `odoo_search_invoices`
- `overdue` → unpaid invoices past due date
- `customers` → top customers via `odoo_search_partners`
- `full` → all sections combined

Flags:
- `--save` → write to `Briefings/YYYY-MM-DD_odoo_<type>_report.md`
- `--title "..."` → use as report title

### 2. Fetch data

| Type          | MCP Tool                               |
|---------------|----------------------------------------|
| `accounting`  | `odoo_get_accounting_summary`          |
| `sales`       | `odoo_search_sales` state=sale limit=20|
| `invoices`    | `odoo_search_invoices` state=all       |
| `overdue`     | `odoo_search_invoices` state=posted    |
| `customers`   | `odoo_search_partners` is_customer=true|

For `full`, call all tools above.

### 3. Format the report

```markdown
## Odoo Business Report — YYYY-MM-DD
**Type:** <type> | **Generated:** HH:MM

---

### Accounting Overview
| Metric               | Value      |
|----------------------|------------|
| Draft Invoices       | X ($X)     |
| Posted / Confirmed   | X ($X)     |
| Total Outstanding    | $X,XXX.XX  |
| Overdue              | X          |

### Recent Sales
| ID   | Customer   | Amount    | Status    | Date       |
|------|------------|-----------|-----------|------------|

### ⚠️ Overdue Invoices
| ID   | Customer   | Amount   | Due Date   | Days Late |
|------|------------|----------|------------|-----------|
[If none: ✓ No overdue invoices]

### Customers
| ID  | Customer   | Email              |
|-----|------------|--------------------|

---
*Source: Odoo live data | Logged: Logs/odoo.log*
```

Mark invoices 30+ days overdue with ⚠️.
Days overdue = today (2026-02-19) minus due_date.

### 4. Save if --save flag

Write to `Briefings/YYYY-MM-DD_odoo_<type>_report.md`

### 5. Log to Logs/odoo.log

```
[YYYY-MM-DD HH:MM] REPORT | type=<type> | saved=<yes/no>
```

### 6. Output

Display the full report. Then:
```
📝 Logged to Logs/odoo.log
[if saved] 💾 Saved → Briefings/<filename>
```

---

## Safety

- Never modifies any Odoo data
- Totals shown exactly as returned — never estimated
- If a MCP call fails, show partial results with a warning
- Saved reports go to `Briefings/` only
