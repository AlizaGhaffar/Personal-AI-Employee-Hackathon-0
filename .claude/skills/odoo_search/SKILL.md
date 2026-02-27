# Skill: /odoo_search

Search Odoo for customers, vendors, invoices, sales orders, or products. Read-only — no approval required.

---

## Metadata

| Field       | Value                                              |
|-------------|----------------------------------------------------|
| Command     | `/odoo_search`                                     |
| Autonomy    | Fully autonomous — read-only                       |
| Log         | `Logs/odoo.log`                                    |

---

## When to Use This Skill

- User asks to "find a customer" or "look up a contact"
- User wants to check if an invoice exists or see its status
- User says "search Odoo for…" or "do we have a record of…"
- User needs a partner ID before creating an invoice
- User asks "who are our customers?" or "show me open orders"

---

## Execution

### 1. Parse the query

Extract from user input:
- **entity** → `partner` | `invoice` | `sale` | `product` (default: `partner`)
- **name filter** → partial name to search
- **status filter** → draft / posted / confirmed / etc.

Infer entity from keywords:
- "customer", "vendor", "contact", "client" → `partner`
- "invoice", "bill" → `invoice`
- "sale", "order", "SO" → `sale`
- "product", "item", "service" → `product`

### 2. Call the right MCP tool

| Entity    | Tool                   | Key params                              |
|-----------|------------------------|-----------------------------------------|
| `partner` | `odoo_search_partners` | name, is_customer, is_vendor, limit=20  |
| `invoice` | `odoo_search_invoices` | partner_name, state, limit=20           |
| `sale`    | `odoo_search_sales`    | partner_name, state, limit=20           |
| `product` | `odoo_execute_method`  | model=product.product, method=search_read, domain=[["name","ilike","<name>"]], fields=["id","name","list_price","type"] |

### 3. Format results as markdown table

- Partners: ID, Name, Email, Phone, Customer, Vendor
- Invoices: ID, Customer, Amount, Status, Date
- Sales: ID, Name, Customer, Amount, Status, Date
- Products: ID, Name, Price, Type

If 0 results: `No results found for "<query>". Try a broader search.`

### 4. Log to Logs/odoo.log

Append:
```
[YYYY-MM-DD HH:MM] SEARCH | entity=<entity> | query=<filter> | results=<N>
```
If file doesn't exist, create it with header `# Odoo Action Log`.

### 5. Output

Display the table. Confirm: `Logged to Logs/odoo.log`

---

## Safety

- Never creates, edits, or deletes any Odoo record
- Results shown in terminal only — not persisted unless user asks
