"""Readiness check for the offboarding flow — run before testing on any site.

    bench --site <site> execute myhr.offboarding_preflight.check
    bench --site <site> execute myhr.offboarding_preflight.check --kwargs "{'employee': 'HR-EMP-00042'}"

Every failure this reports has bitten someone during development. The flow has a
lot of moving parts — two workflows, four doctypes, a permission grant, and
several fields that must be set on the Employee — and most of them fail late and
quietly. A missing Holiday List, for instance, does not surface until the second
approver clicks Approve, and the message it produces never mentions resignations.

Nothing here writes anything. It only looks and reports.
"""

import frappe
from frappe.utils import cint

CLEARANCE_DOCTYPES = (
	"Separation Manager Clearance",
	"Separation IT Clearance",
	"Separation HR Clearance",
)
WORKFLOWS = ("Employee Separation Approval", "Separation Manager Clearance")

OK, WARN, FAIL = "PASS", "WARN", "FAIL"


def check(employee=None):
	"""Print a readiness report. Optionally deep-check one employee."""
	results = []
	results += _check_schema()
	results += _check_workflows()
	results += _check_permissions()
	results += _check_settings()
	if employee:
		results += _check_employee(employee)
	else:
		results.append((WARN, "Employee", "No employee given — pass employee=<id> to check a leaver."))

	_report(results)
	return results


# ---------------------------------------------------------------------------
def _check_schema():
	out = []
	for doctype in (*CLEARANCE_DOCTYPES, "IT Asset Type", "Access Revocation System"):
		exists = bool(frappe.db.exists("DocType", doctype))
		out.append((OK if exists else FAIL, "Schema", f"{doctype} {'exists' if exists else 'MISSING — run bench migrate'}"))

	for dt, fieldname in (
		("Employee", "custom_l2_manager"),
		("Employee Separation", "custom_reporting_manager"),
		("Employee Separation", "custom_notice_period_shortfall"),
		("Full and Final Statement", "custom_net_payable"),
	):
		ok = bool(frappe.db.exists("Custom Field", f"{dt}-{fieldname}"))
		out.append((OK if ok else FAIL, "Schema", f"{dt}.{fieldname} {'present' if ok else 'MISSING — fixtures did not load'}"))

	# Seeded masters — empty lists make two clearance fields unusable.
	for doctype in ("IT Asset Type", "Access Revocation System"):
		if not frappe.db.exists("DocType", doctype):
			continue
		count = frappe.db.count(doctype)
		out.append((OK if count else WARN, "Seed data", f"{doctype}: {count} row(s)"))
	return out


def _check_workflows():
	out = []
	for name in WORKFLOWS:
		if not frappe.db.exists("Workflow", name):
			out.append((FAIL, "Workflow", f"{name} MISSING — fixtures did not load"))
			continue
		active = cint(frappe.db.get_value("Workflow", name, "is_active"))
		out.append((OK if active else FAIL, "Workflow", f"{name} {'active' if active else 'INACTIVE'}"))
	return out


def _check_permissions():
	"""The two grants that are invisible until someone is blocked by them."""
	out = []

	# Stock HRMS grants submit on Exit Interview to nobody at all, which makes
	# the relieving letter unreleasable by anyone but Administrator.
	can_submit = [
		p.role for p in frappe.get_meta("Exit Interview").permissions if p.submit
	]
	out.append((
		OK if can_submit else FAIL, "Permissions",
		f"Exit Interview submit: {', '.join(can_submit) or 'NOBODY — the relieving letter cannot be released'}",
	))

	# The Employee role needs create+submit on Employee Separation, or nobody
	# can raise their own resignation.
	emp = next(
		(p for p in frappe.get_meta("Employee Separation").permissions if p.role == "Employee"), None
	)
	ok = bool(emp and emp.create and emp.submit)
	out.append((
		OK if ok else FAIL, "Permissions",
		"Employee can raise a resignation" if ok else "Employee role LACKS create/submit on Employee Separation",
	))

	# Adding one Custom DocPerm to a doctype that had none silently revokes the
	# stock roles, so confirm the usual suspects survived.
	for doctype in ("Employee Separation", *CLEARANCE_DOCTYPES):
		roles = {p.role for p in frappe.get_meta(doctype).permissions}
		missing = {"HR Manager", "System Manager"} - roles
		out.append((
			OK if not missing else FAIL, "Permissions",
			f"{doctype}: {'HR Manager + System Manager present' if not missing else 'MISSING ' + ', '.join(sorted(missing))}",
		))
	return out


def _check_settings():
	out = []
	domains = (frappe.db.get_single_value("HR Settings", "custom_internal_email_domains") or "").strip()
	out.append((
		OK if domains else WARN, "Settings",
		f"Internal email domains: {domains or 'EMPTY — mailbox forwarding accepts any address'}",
	))

	if not _pdf_available():
		out.append((WARN, "Settings", "wkhtmltopdf not usable — the relieving letter PDF will not render"))
	else:
		out.append((OK, "Settings", "PDF rendering available"))
	return out


def _pdf_available():
	try:
		from frappe.utils.pdf import get_pdf

		get_pdf("<p>preflight</p>")
		return True
	except Exception:
		return False


def _check_employee(employee):
	"""The four fields that make a leaver's flow work, and the blockers."""
	out = []
	if not frappe.db.exists("Employee", employee):
		return [(FAIL, "Employee", f"{employee} does not exist")]

	emp = frappe.db.get_value(
		"Employee", employee,
		["employee_name", "user_id", "reports_to", "custom_l2_manager",
		 "custom_notice_period_days", "holiday_list", "company", "status"],
		as_dict=True,
	)
	out.append((OK, "Employee", f"{employee} — {emp.employee_name} ({emp.status})"))

	checks = (
		("user_id", emp.user_id, FAIL, "no User linked — they cannot open the app"),
		("reports_to", emp.reports_to, FAIL, "no L1 — the resignation cannot be routed"),
		("custom_l2_manager", emp.custom_l2_manager, FAIL, "no L2 — it will stall after L1"),
		("custom_notice_period_days", cint(emp.custom_notice_period_days) or None, WARN,
		 "notice period is 0 — shortfall will always be 0"),
	)
	for label, value, severity, problem in checks:
		out.append((OK, "Employee", f"{label}: {value}") if value
		           else (severity, "Employee", f"{label}: {problem}"))

	# A leaver with no resolvable holiday list cannot be approved at all.
	holiday_list = emp.holiday_list or frappe.db.get_value("Company", emp.company, "default_holiday_list")
	out.append((OK, "Employee", f"holiday list: {holiday_list}") if holiday_list
	           else (FAIL, "Employee", "no Holiday List on the employee or their company — L2 approval will fail"))

	# Each approver needs a User too, or the per-person workflow gate matches nobody.
	for label, manager in (("L1", emp.reports_to), ("L2", emp.custom_l2_manager)):
		if not manager:
			continue
		user = frappe.db.get_value("Employee", manager, "user_id")
		out.append((OK, "Approvers", f"{label} {manager} -> {user}") if user
		           else (FAIL, "Approvers", f"{label} {manager} has no User — they cannot approve"))

	live = frappe.db.get_value(
		"Employee Separation", {"employee": employee, "docstatus": ["<", 2]},
		["name", "workflow_state"], as_dict=True,
	)
	if live:
		out.append((WARN, "Existing", f"{live.name} is {live.workflow_state} — a new resignation will be blocked"))
	else:
		out.append((OK, "Existing", "no live separation — ready to file"))
	return out


# ---------------------------------------------------------------------------
def _report(results):
	width = max(len(area) for _, area, _ in results)
	for status, area, message in results:
		print(f"[{status}] {area.ljust(width)}  {message}")

	counts = {s: sum(1 for r in results if r[0] == s) for s in (OK, WARN, FAIL)}
	print(f"\n{counts[OK]} passed, {counts[WARN]} warnings, {counts[FAIL]} failures")
	if counts[FAIL]:
		print("Fix the failures before testing — each one blocks the flow partway through.")
