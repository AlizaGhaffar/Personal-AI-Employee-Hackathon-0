# Skill: /odoo_invoice

Parse an invoice request from email or natural language, create a draft invoice in Odoo, and route to `Pending_Approval/`. Never posts automatically.

---

## Metadata

| Field       | Value                                                    |
|-------------|----------------------------------------------------------|
| Command     | `/odoo_invoice`                                          |
| Autonomy    | HITL — draft created autonomously, human approves post   |
| Log         | `Logs/odoo.log`                                          |

---

## When to Use This Skill

- User says "generate an invoice for [customer]" or "bill [Name]"
- An email arrives requesting an invoice or payment
- User provides a customer name + services/amounts and wants an invoice created
- User says "invoice [Name] for [X hours / X amount]"
- Triage classifies a pipeline item as type `invoice` and routes it here

---

## Execution

### 1. Parse the request

Input can be: natural language string, or a file path to an email in `Needs_Action/`.
If a file path is given, read the file first.

Extract:
| Field         | How to find it                                           |
|---------------|----------------------------------------------------------|
| customer_name | "for [Name]", "bill [Name]", "charge [Name]"            |
| line_items    | services/products with qty and price                     |
| invoice_date  | today if not stated                                      |
| due_date      | "due [date]", "net 30" = today+30 days                  |
| notes         | reference numbers, PO numbers, special instructions      |

If `customer_name` is missing → ask before continuing.
If line items are ambiguous → list assumptions and ask to confirm.

### 2. Find or create the customer

Call `odoo_search_partners` with name, is_customer=true, limit=5.
- **1 match** → use that partner's id
- **Multiple matches** → show list, ask "Which customer? (enter ID)"
- **No match** → call `odoo_create_partner` (name, is_customer=true) → note new partner needs approval too

### 3. Build line items

Construct JSON array:
```json
[{"name": "Description", "quantity": N, "price_unit": X.XX}]
```

### 4. Create the draft invoice

Call `odoo_create_invoice`:
- partner_id, lines, invoice_date, due_date, notes

Then call `odoo_get_invoice` with the returned id to get full details.

### 5. Write approval plan

File: `Pending_Approval/PLAN_invoice_<customer-slug>_<YYYYMMDD>.md`

```markdown
---
date: YYYY-MM-DD
type: odoo_invoice
partner: <customer_name>
invoice_id: <id>
amount_total: <total>
status: pending
requires_approval: true
priority: P2
summary: Draft invoice for <customer_name> $<total> — awaiting approval to post
---

# Invoice Approval: <customer_name> — $<total>

| Field          | Value               |
|----------------|---------------------|
| Customer       | <name> (ID: <id>)  |
| Invoice Date   | <date>              |
| Due Date       | <due_date or N/A>  |
| Odoo Draft ID  | <invoice_id>        |
| Status         | DRAFT — not posted  |

## Line Items
| Description | Qty | Unit Price | Subtotal  |
|-------------|-----|------------|-----------|
| <item>      | N   | $X.XX      | $X.XX     |
| **TOTAL**   |     |            | **$X.XX** |

## Action Required
- [ ] Verify customer and line items
- [ ] Move to `Approved/` → AI will POST invoice in Odoo
- [ ] Move to `Rejected/` → draft stays unposted

⚠️ Posting makes it official. Sending to customer needs separate email approval.
```

### 6. Log to Logs/odoo.log

```
[YYYY-MM-DD HH:MM] INVOICE | customer=<name> | invoice_id=<id> | amount=<total> | status=draft | approval=pending
```

### 7. Output

```
✓ Draft invoice created in Odoo (ID: <id>)
   Customer: <name> | Amount: $<total> | Due: <date>

📋 Approval plan → Pending_Approval/PLAN_invoice_<slug>_<date>.md
📝 Logged to Logs/odoo.log
```

---

## Safety

- Never calls `action_post` — posting reserved for the approve flow
- Never emails the invoice — requires separate `/draft-reply` + approval
- New customer created during this flow also requires approval (flag in plan)
- On any MCP error: log and report, do not retry
