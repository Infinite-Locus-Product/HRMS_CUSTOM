"""Probe script — diagnose why `prevent_self_expense_approval` fails to block on staging.

NOT a migration patch. NOT registered in patches.txt. Standalone diagnostic
that prints the live state of every input the gate consults, and attempts a
controlled self-approval against an actual employee. Run via:

    bench --site staging.elixiirfoods.com execute \
        myhr.patches.probe_staging_self_approval.execute --kwargs '{"employee": "HR-EMP-XXXX"}'

Or, if you want it to auto-pick an active employee with a user_id:

    bench --site staging.elixiirfoods.com execute \
        myhr.patches.probe_staging_self_approval.execute

The probe never modifies HR Settings. It DOES create + delete one Expense
Claim under the picked employee's user — every operation rolls back.
"""

import frappe


def _setting(key, default=None):
	v = frappe.db.get_single_value("HR Settings", key)
	return default if v is None else v


def execute(employee: str | None = None):
	print("=" * 72)
	print("Self-approval gate diagnostic — staging probe")
	print("=" * 72)

	# 1. HR Settings — what the gate reads
	print("\n[1] HR Settings — values the gate reads at validate time")
	print(f"    prevent_self_expense_approval       = {_setting('prevent_self_expense_approval')!r}  (must be 1)")
	print(f"    custom_ec_approver_hr_manager       = {_setting('custom_ec_approver_hr_manager')!r}")
	print(f"    custom_ec_approver_designated       = {_setting('custom_ec_approver_designated')!r}")
	print(f"    custom_ec_approver_accounts_manager = {_setting('custom_ec_approver_accounts_manager')!r}")

	# 2. Hook registration
	print("\n[2] Hook registration — gate must be wired to Expense Claim.validate")
	hooks = frappe.get_hooks("doc_events", {}).get("Expense Claim", {}).get("validate", [])
	gate_wired = "myhr.approval_gate.gate_expense_claim_approval" in (hooks if isinstance(hooks, list) else [hooks])
	print(f"    Expense Claim.validate hooks: {hooks}")
	print(f"    Gate registered: {gate_wired}  (must be True)")

	# 3. Pick the employee under test
	if not employee:
		row = frappe.db.sql(
			"SELECT name, employee_name, user_id, company, expense_approver "
			"FROM `tabEmployee` WHERE status='Active' AND user_id IS NOT NULL "
			"AND user_id != '' AND user_id != 'Administrator' ORDER BY creation LIMIT 1",
			as_dict=True,
		)
		if not row:
			print("\nNo active employee with user_id found. Pass employee= explicitly.")
			return
		employee = row[0]["name"]

	emp = frappe.db.get_value(
		"Employee",
		employee,
		["name", "employee_name", "user_id", "company", "expense_approver"],
		as_dict=True,
	)
	if not emp:
		print(f"\n[!] Employee {employee} not found.")
		return

	print(f"\n[3] Employee under test")
	print(f"    name             = {emp.name}")
	print(f"    employee_name    = {emp.employee_name}")
	print(f"    user_id          = {emp.user_id!r}  (must match the user attempting approval)")
	print(f"    expense_approver = {emp.expense_approver!r}")
	print(f"    company          = {emp.company}")

	# 4. Verify user_id resolves to an actual User
	user_exists = bool(emp.user_id and frappe.db.exists("User", emp.user_id))
	print(f"\n[4] User existence: {user_exists}  (must be True for _is_self_expense_claim to match)")

	# 5. Build a draft EC and probe the gate as the employee's user
	print(f"\n[5] Live self-approval probe (as user={emp.user_id})")
	if not user_exists:
		print("    SKIPPED — user does not exist; cannot impersonate.")
		return

	cc = frappe.db.get_value("Cost Center", {"company": emp.company, "is_group": 0}, "name")
	payable = frappe.db.get_value(
		"Account",
		{"company": emp.company, "account_type": "Payable", "is_group": 0},
		"name",
	)
	currency = frappe.db.get_value("Company", emp.company, "default_currency")

	# Find any Expense Claim Type that has a default account configured for this company.
	ect = frappe.db.sql(
		"SELECT parent FROM `tabExpense Claim Account` WHERE company=%s LIMIT 1",
		(emp.company,),
		as_dict=True,
	)
	if not ect:
		print(f"    SKIPPED — no Expense Claim Type has a default_account for {emp.company}.")
		print("    Configure one via Expense Claim Type → Accounts and re-run.")
		return
	type_name = ect[0]["parent"]
	print(f"    using Expense Claim Type: {type_name}")
	print(f"    cost_center={cc} payable={payable} currency={currency}")

	frappe.set_user(emp.user_id)
	print(f"    session.user = {frappe.session.user}")

	verdict = None
	error_text = None
	try:
		ec = frappe.get_doc({
			"doctype": "Expense Claim",
			"employee": emp.name,
			"company": emp.company,
			"posting_date": frappe.utils.today(),
			"expense_approver": emp.user_id,  # self as approver, worst case
			"approval_status": "Draft",
			"cost_center": cc,
			"payable_account": payable,
			"currency": currency,
			"exchange_rate": 1,
			"expenses": [{
				"expense_date": frappe.utils.today(),
				"expense_type": type_name,
				"amount": 1,
				"sanctioned_amount": 1,
				"cost_center": cc,
			}],
		})
		ec.insert(ignore_permissions=False)
		print(f"    inserted draft: {ec.name}")

		try:
			ec.approval_status = "Approved"
			ec.save()
			verdict = "BUG_REPRODUCED"
			error_text = "Save succeeded — gate did not block self-approval."
		except frappe.PermissionError as e:
			verdict = "GATE_FIRED_AS_EXPECTED"
			error_text = str(e)
		except Exception as e:
			verdict = "OTHER_ERROR"
			error_text = f"{type(e).__name__}: {e}"
	finally:
		# Cleanup even when something went sideways
		try:
			if "ec" in locals() and ec.name and frappe.db.exists("Expense Claim", ec.name):
				if ec.docstatus == 1:
					ec.cancel()
				frappe.delete_doc("Expense Claim", ec.name, force=True, ignore_permissions=True)
				frappe.db.commit()
		except Exception as cleanup_err:
			print(f"    cleanup failed: {cleanup_err}")
		frappe.set_user("Administrator")

	print(f"\n[VERDICT] {verdict}")
	print(f"    detail: {error_text}")

	# 6. Interpretation
	print("\n[INTERPRETATION]")
	if verdict == "GATE_FIRED_AS_EXPECTED":
		print("    Gate works on this site. If staging users still bypass:")
		print("      - Make sure the user logged in matches Employee.user_id EXACTLY (case + domain).")
		print("      - Restart the web + worker processes after toggling HR Settings (get_cached_doc).")
		print("      - Confirm staging is actually running myhr's `gate_expense_claim_approval` build.")
	elif verdict == "BUG_REPRODUCED":
		print("    The gate DID NOT block. Likely causes (in order):")
		print("      - Toggle was already 0 (re-check [1] above — should read 1).")
		print("      - Employee.user_id mismatch with session user (see [3] vs [5]).")
		print("      - Stale cache on HR Settings — restart workers + bench --site <s> clear-cache.")
		print("      - Older myhr build deployed; pull latest and `bench migrate`.")
	else:
		print("    Probe could not reach the gate path. Fix the [OTHER_ERROR] then re-run.")
