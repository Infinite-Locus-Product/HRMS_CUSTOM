"""Fixxly Travel & Expense — one-shot ERPNext setup (Step 1 of the guide).

Creates the Expense Claim Types for the Fixxly Travel & Expense Policy (effective
1 Aug 2026) and maps each to a company expense account. Idempotent — existing
types are kept; a missing company-account row is added to them. Standard ERPNext
only; no code customization.

NOTE: stock ERPNext cannot enforce the rupee caps (food ₹800/₹1,200 by band,
airfare ₹10,000) — those stay manual/approver-checked. See the guide.

RUN (on the target site):
    printf "%s\\n" \\
      "p='/abs/path/to/setup_fixxly_travel_expense.py'" \\
      "exec(compile(open(p).read(), p, 'exec'), {'__name__':'__main__'})" \\
      | bench --site <your-site> console

Edit CONFIG below before running.
"""

import frappe

# ---------------------------------------------------------------------------
# CONFIG — edit for your site
# ---------------------------------------------------------------------------
CONFIG = {
	"company": "FIXXLY PRIVATE LIMITED",
	"default_expense_account": None,   # None = auto-resolve the company's "Travel Expenses" account
}

log = []

# Expense Claim Types to ensure (the account defaults to the resolved travel account).
EXPENSE_TYPES = [
	("Airfare", "Air travel (one-way cap ₹10,000 — enforce manually)"),
	("Rail / Road Travel", "Preferred mode under 500 km below AGM"),
	("Local Conveyance", "Airport transfers + intra-city (metro / shared cab / Ola / Uber)"),
	("Accommodation", "Approved hotels only"),
	("Food", "Meals on actuals; daily cap ₹800 / ₹1,200 by band — enforce manually"),
	("Private Vehicle", "Reimbursed at bus-fare equivalent for intercity"),
	("Miscellaneous Travel", "Other approved trip costs"),
]


def resolve_travel_account():
	company = CONFIG["company"]
	if CONFIG["default_expense_account"]:
		return CONFIG["default_expense_account"]
	# Preferred: the standard "Travel Expenses" ledger.
	acc = frappe.db.get_value("Account",
		{"company": company, "account_name": "Travel Expenses", "is_group": 0}, "name")
	if acc:
		return acc
	# Any expense account whose name mentions travel.
	acc = frappe.db.get_value("Account",
		{"company": company, "root_type": "Expense", "is_group": 0,
		 "account_name": ["like", "%Travel%"]}, "name")
	if acc:
		return acc
	# Last resort: first non-group expense account.
	acc = frappe.db.get_value("Account",
		{"company": company, "root_type": "Expense", "is_group": 0}, "name")
	return acc


def ensure_expense_claim_type(name, description, account):
	company = CONFIG["company"]
	if frappe.db.exists("Expense Claim Type", name):
		# Ensure a Default Account row exists for this company.
		ect = frappe.get_doc("Expense Claim Type", name)
		if not any(r.company == company for r in ect.accounts):
			ect.append("accounts", {"company": company, "default_account": account})
			ect.flags.ignore_permissions = True
			ect.save(ignore_permissions=True)
			log.append(f"added {company} account to existing Expense Claim Type: {name}")
		else:
			log.append(f"skip Expense Claim Type (exists w/ account): {name}")
		return
	ect = frappe.new_doc("Expense Claim Type")
	ect.expense_type = name
	ect.description = description
	ect.append("accounts", {"company": company, "default_account": account})
	ect.flags.ignore_permissions = True
	ect.insert(ignore_permissions=True)
	log.append(f"created Expense Claim Type: {name}  (account: {account})")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if not frappe.db.exists("Company", CONFIG["company"]):
	raise SystemExit(f"Company not found: {CONFIG['company']!r} — fix CONFIG['company'].")

travel_account = resolve_travel_account()
if not travel_account:
	raise SystemExit(
		f"No expense account found for {CONFIG['company']!r}. "
		f"Set CONFIG['default_expense_account'] explicitly.")
log.append(f"using expense account: {travel_account}")

for name, desc in EXPENSE_TYPES:
	ensure_expense_claim_type(name, desc, travel_account)

frappe.db.commit()

print("=== Fixxly Travel & Expense setup ===")
for line in log:
	print("  -", line)
print("=== done (committed) ===")
print("Reminder: rupee caps (food ₹800/₹1,200, airfare ₹10,000), approval chain,")
print("booking-ID reference, and budgets are process/approver steps — see the guide.")
