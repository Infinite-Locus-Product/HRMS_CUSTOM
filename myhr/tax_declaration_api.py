"""PWA endpoints for the Tax Declaration centre.

Two things an employee does for themselves once a year:

1. pick the income tax regime they want to be taxed under, which is stored on
   their Employee record as `custom_income_tax_slab`;
2. declare the exemptions they intend to claim, which is an
   `Employee Tax Exemption Declaration` for the current payroll period.

Both are scoped to `frappe.session.user`'s own Employee record. No endpoint
takes an employee argument, so there is nothing to tamper with.

Writes use `ignore_permissions` on purpose: these doctypes are HR/payroll-owned
and an ordinary employee has no rights over them, yet the whole point here is
that the employee fills their own in. The scoping above is what makes that safe,
not the doctype permissions.
"""

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

DECLARATION = "Employee Tax Exemption Declaration"


def _my_employee():
	"""The caller's own Employee record, as a dict of what the tax screens need."""
	employee = frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user},
		["name", "employee_name", "company", "department", "custom_income_tax_slab"],
		as_dict=True,
	)
	if not employee:
		frappe.throw(
			_("Your user account is not linked to an Employee record. Please contact HR."),
			title=_("No Employee Record"),
		)
	return employee


def _current_payroll_period(company, on=None):
	on = getdate(on or nowdate())
	return frappe.db.get_value(
		"Payroll Period",
		{"company": company, "start_date": ["<=", on], "end_date": [">=", on]},
		["name", "start_date", "end_date"],
		as_dict=True,
	)


def _payroll_periods(company):
	"""Every period this employee could file against, newest first."""
	return frappe.get_all(
		"Payroll Period",
		filters={"company": company},
		fields=["name", "start_date", "end_date"],
		order_by="start_date desc",
	)


def _resolve_period(company, requested):
	"""The period to work with: the one asked for, else the one covering today.

	A requested period is checked against the employee's own company — the
	argument comes from the client, so it is the one thing here that could be
	tampered with.
	"""
	if requested:
		period = frappe.db.get_value(
			"Payroll Period", {"name": requested, "company": company},
			["name", "start_date", "end_date"], as_dict=True,
		)
		if not period:
			frappe.throw(
				_("{0} is not a payroll period you can file against.").format(frappe.bold(requested)),
				title=_("Invalid Payroll Period"),
			)
		return period

	# Falling back to the latest keeps the screen usable between periods, when
	# nothing covers today.
	return _current_payroll_period(company) or (_payroll_periods(company) or [None])[0]


# ---------------------------------------------------------------------------
# 1. Income tax slab
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_income_tax_slabs():
	"""The regimes this employee may choose between, and their current choice."""
	employee = _my_employee()

	slabs = frappe.get_all(
		"Income Tax Slab",
		filters={"company": employee.company, "disabled": 0, "docstatus": 1},
		fields=["name", "currency", "effective_from", "allow_tax_exemption"],
		order_by="effective_from desc, name asc",
	)
	return {
		"employee": employee.name,
		"employee_name": employee.employee_name,
		"selected": employee.custom_income_tax_slab,
		"slabs": slabs,
	}


@frappe.whitelist()
def save_income_tax_slab(slab):
	"""Record the employee's chosen regime on their own Employee record.

	Written with `db_set` rather than a full save: an Employee document carries
	myHR's mandatory fields (employee_number, ctc, payroll_cost_center) and
	plenty of older records are missing them. Someone choosing a tax regime must
	not be blocked by unrelated gaps in their master data.
	"""
	employee = _my_employee()

	if slab:
		allowed = frappe.db.exists(
			"Income Tax Slab",
			{"name": slab, "company": employee.company, "disabled": 0, "docstatus": 1},
		)
		if not allowed:
			frappe.throw(
				_("{0} is not a tax slab you can choose.").format(frappe.bold(slab)),
				title=_("Invalid Tax Slab"),
			)

	frappe.db.set_value(
		"Employee", employee.name, "custom_income_tax_slab", slab or None, update_modified=False
	)
	return {"selected": slab or None}


# ---------------------------------------------------------------------------
# 2. Exemption declaration
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_my_tax_declaration(payroll_period=None):
	"""Everything the declaration screen needs in one round trip.

	`payroll_period` lets the employee look at — and file for — a period other
	than the current one, which matters at a year boundary and for reviewing
	what they declared last year.
	"""
	employee = _my_employee()
	period = _resolve_period(employee.company, payroll_period)

	out = {
		"employee": employee.name,
		"employee_name": employee.employee_name,
		"department": employee.department,
		"company": employee.company,
		"payroll_period": period,
		"payroll_periods": _payroll_periods(employee.company),
		"sub_categories": _sub_categories(),
		"declaration": None,
		# Surfaced so the screen can explain itself rather than show an empty
		# picker: without sub categories there is nothing anyone can declare.
		"can_declare": bool(period),
		# HRMS refuses to SUBMIT a declaration for a period in which the
		# employee had no salary structure — it cannot work out the HRA
		# exemption without one. Surfaced so the screen can say so up front
		# rather than letting someone fill the form and fail at the last step.
		"has_salary_structure": _has_salary_structure(employee.name, period, employee.company),
		# HRA exemption is computed from the company's Basic and HRA salary
		# components. Without them HRMS refuses the save outright, so the screen
		# hides the house-rent fields instead of letting someone fill them in
		# and hit a message about company setup they cannot act on.
		"hra_available": _hra_configured(employee.company),
	}

	if not period:
		return out

	name = frappe.db.get_value(
		DECLARATION,
		{"employee": employee.name, "payroll_period": period.name, "docstatus": ["<", 2]},
		"name",
	)
	if name:
		out["declaration"] = _serialize(frappe.get_doc(DECLARATION, name))
	return out


def _has_salary_structure(employee, period, company):
	"""Whether a submit would survive HRMS's salary-structure check.

	The check only bites when HRA is actually computed, which only happens when
	the company has Basic and HRA components set. Without them HRMS never looks
	for an assignment, so neither should this — being stricter than the rule it
	mirrors would block submissions that would otherwise work.
	"""
	if not period:
		return False
	if not _hra_configured(company):
		return True

	from hrms.hr.utils import get_salary_assignments

	return bool(get_salary_assignments(employee, period.name))


def _hra_configured(company):
	basic, hra = frappe.db.get_value("Company", company, ["basic_component", "hra_component"]) or (None, None)
	return bool(basic and hra)


def _sub_categories():
	"""Exemption sub categories, each carrying its category and ceiling.

	The employee picks a sub category and types an amount; the category and the
	maximum come along with it, which is how the Desk form behaves.
	"""
	return frappe.get_all(
		"Employee Tax Exemption Sub Category",
		filters={"is_active": 1},
		fields=["name", "exemption_category", "max_amount"],
		order_by="exemption_category asc, name asc",
	)


def _serialize(doc):
	return {
		"name": doc.name,
		"docstatus": doc.docstatus,
		"submitted": doc.docstatus == 1,
		"payroll_period": doc.payroll_period,
		"currency": doc.currency,
		"total_declared_amount": doc.total_declared_amount,
		"total_exemption_amount": doc.total_exemption_amount,
		"monthly_house_rent": doc.get("monthly_house_rent"),
		"rented_in_metro_city": cint(doc.get("rented_in_metro_city")),
		"annual_hra_exemption": doc.get("annual_hra_exemption"),
		"monthly_hra_exemption": doc.get("monthly_hra_exemption"),
		"declarations": [
			{
				"exemption_sub_category": row.exemption_sub_category,
				"exemption_category": row.exemption_category,
				"max_amount": row.max_amount,
				"amount": row.amount,
			}
			for row in doc.declarations or []
		],
	}


@contextmanager
def _as_system():
	"""Run a write as Administrator, restoring the caller afterwards.

	Deriving HRA builds a preview Salary Slip (hrms.regional.india.utils), and
	that goes through get_mapped_doc, which checks create permission on a
	document we never get a chance to set a flag on -- frappe.flags does not
	reach it, only the document's own. An ordinary employee cannot create a
	Salary Slip, so the whole write has to run system-side.

	Authorisation has already happened by this point: the document is the
	caller's own, resolved from their session, and the only fields written come
	off the payload. Authorship is corrected by the caller afterwards.
	"""
	caller = frappe.session.user
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(caller)


@frappe.whitelist()
def save_my_tax_declaration(payload, submit=False, payroll_period=None):
	"""Create or update the caller's declaration for the chosen period."""
	payload = frappe.parse_json(payload)
	employee = _my_employee()

	period = _resolve_period(employee.company, payroll_period)
	if not period:
		frappe.throw(
			_("No payroll period has been set up, so a declaration cannot be filed."),
			title=_("No Payroll Period"),
		)

	name = frappe.db.get_value(
		DECLARATION,
		{"employee": employee.name, "payroll_period": period.name, "docstatus": ["<", 2]},
		"name",
	)
	if name:
		doc = frappe.get_doc(DECLARATION, name)
		if doc.docstatus == 1:
			frappe.throw(
				_("Your declaration for {0} has already been submitted and cannot be changed.").format(
					period.name
				),
				title=_("Already Submitted"),
			)
	else:
		doc = frappe.new_doc(DECLARATION)
		doc.employee = employee.name
		doc.payroll_period = period.name
		doc.company = employee.company

	doc.declarations = []
	for row in payload.get("declarations") or []:
		if not row.get("exemption_sub_category"):
			continue
		doc.append("declarations", {
			"exemption_sub_category": row.get("exemption_sub_category"),
			# category and max_amount are read-only fetches; the controller
			# fills them, so whatever the client sent is ignored.
			"amount": flt(row.get("amount")),
		})

	# Only when the company can actually compute it — otherwise HRMS throws
	# "Please set Basic and HRA component in Company", which is not something
	# the employee filling this in can do anything about.
	if _hra_configured(employee.company):
		for field in ("monthly_house_rent", "rented_in_metro_city"):
			if field in payload:
				doc.set(field, payload.get(field))

	# HRA is derived by building a preview Salary Slip, which an ordinary
	# employee has no create permission for. Passing ignore_permissions to save()
	# only covers the declaration itself, not that nested document, so the whole
	# write runs system-side. Authorisation already happened: _my_employee()
	# resolved the caller's own record, and the only fields written are the ones
	# read off the payload above.
	with _as_system():
		doc.save(ignore_permissions=True)

	if cint(submit):
		# Checked before submitting so the message names the real problem.
		# HRMS's own is "Salary Structure must be submitted before submission
		# of Employee Tax Exemption Declaration", which reads like the employee
		# has to do something they cannot.
		if not _has_salary_structure(employee.name, period, employee.company):
			frappe.throw(
				_("You had no salary structure during {0}, so a declaration for that period cannot be submitted. Pick a different period, or ask HR to assign one.").format(
					frappe.bold(period.name)
				),
				title=_("No Salary Structure For This Period"),
			)
		doc.flags.ignore_permissions = True
		with _as_system():
			doc.submit()

	# set_user_and_timestamp stamps both of these with the session user, and on
	# insert it overwrites owner unconditionally -- so having run as
	# Administrator, they have to be put back for the audit trail to name
	# whoever actually filed this. Always the caller's own document, so there is
	# no other value either field could correctly hold.
	frappe.db.set_value(
		DECLARATION,
		doc.name,
		{"owner": frappe.session.user, "modified_by": frappe.session.user},
		update_modified=False,
	)

	return _serialize(frappe.get_doc(DECLARATION, doc.name))
