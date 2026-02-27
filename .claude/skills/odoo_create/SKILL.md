# Skill: /odoo_create

Create a new partner or draft invoice in Odoo. Always creates as DRAFT — routes to `Pending_Approval/` before any confirmation.

---

## Metadata

| Field       | Value                                              |
|-------------|----------------------------------------------------|
| Command     | `/odoo_create`                                     |
| Autonomy    | HITL — draft created autonomously, human confirms  |
| Log         | `Logs/odoo.log`                                    |

---

## When to Use This Skill

- User says "add a new customer" or "create a vendor in Odoo"
- User wants to onboard a new client or supplier into the system
- User asks to "create a draft invoice" with specific line items
- User provides contact details (name, email, phone) and wants them saved
- User says "register [Name] as a customer/vendor"

---

## Execution

### 1. Parse the request

Extract:
- **type** → `customer` | `vendor` | `invoice`
- For partner: name (required), email, phone, street, city
- For invoice: partner_id (required), line items, invoice_date, due_date, notes

If `type` is missing → ask before continuing.
If `name` is missing for a partner → ask before continuing.

### 2. Duplicate check (partners only)

Call `odoo_search_partners` with the name.
- If similar record found → warn user and wait for confirmation before proceeding.

### 3. Create the draft record

**Partner/Customer/Vendor** → `odoo_create_partner`
- name, email, phone, street, city
- is_customer=true for customer, is_vendor=true for vendor

**Invoice** → `odoo_create_invoice`
- partner_id, lines as JSON array, invoice_date, due_date, notes
- Example lines: `[{"name": "Consulting", "quantity": 1, "price_unit": 500.0}]`

Capture the returned ID as `new_id`.

### 4. Write approval plan

File: `Pending_Approval/PLAN_odoo_create_<slug>_<YYYYMMDD>.md`

```markdown
---
date: YYYY-MM-DD
type: odoo_create
entity: <type>
odoo_id: <new_id>
status: pending
requires_approval: true
priority: P2
summary: New <type> draft in Odoo — ID <new_id> — awaiting confirmation
---

# Odoo Create: <type> — <name>

| Field   | Value             |
|---------|-------------------|
| Type    | <type>            |
| Name    | <name>            |
| Email   | <email or N/A>    |
| Phone   | <phone or N/A>    |
| Odoo ID | <new_id> (DRAFT)  |

## Action Required
- [ ] Review details above
- [ ] Move to `Approved/` to confirm the record in Odoo
- [ ] Move to `Rejected/` to leave it as draft / cancel
```

### 5. Log to Logs/odoo.log

```
[YYYY-MM-DD HH:MM] CREATE | type=<type> | name=<name> | odoo_id=<new_id> | status=draft | approval=pending
```

### 6. Output

```
✓ Draft <type> created in Odoo (ID: <new_id>)
📋 Approval plan → Pending_Approval/PLAN_odoo_create_<slug>_<date>.md
📝 Logged to Logs/odoo.log
```

---

## Safety

- Never confirms or posts records automatically
- Always writes `Pending_Approval/` plan before reporting success
- On duplicate detected: stop and wait for user confirmation
- On any MCP error: log it, report to user, do not retry
