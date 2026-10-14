"""Works out what a notice-period shortfall costs the leaver.

    recovery = (monthly component / days per month) * shortfall days

Both the component and the divisor are configured in HR Settings, because the
answer to "what is a day of notice worth" is a policy decision, not a constant:
some companies charge against basic, some against gross, some divide by 30 and
some by 26.

The component amount comes from the employee's active Salary Structure
Assignment. Salary structures rarely store a plain number — components are
usually formulas, and those formulas reference each other (`BS * 0.5`,
`(base / 12) - BS - HRA`). So the structure's earnings are evaluated in order
with each result exposed under its abbreviation, which is how payroll itself
resolves them.

Nothing is guessed. If the component is not configured, the employee has no
assignment, or a formula cannot be evaluated, the recovery is zero and the
reason is returned alongside it — a settlement should say "we could not work
this out" rather than quietly recover nothing.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

WAIVED = "Yes"


def get_recovery(employee, shortfall_days, waiver=None, as_on=None):
	"""Return {"amount", "per_day", "component", "days", "reason"}.

	`reason` is None when the amount was calculated, and a human sentence when
	it could not be — the caller decides whether to show it.
	"""
	blank = {"amount": 0.0, "per_day": 0.0, "component": None, "days": cint(shortfall_days),
	         "reason": None}

	# A waived notice period is the whole point of waiving it: nothing is owed.
	if waiver == WAIVED:
		blank["reason"] = _("The notice period was waived, so nothing is recovered.")
		return blank

	days = cint(shortfall_days)
	if days <= 0:
		return blank

	settings = _settings()
	if not settings["component"]:
		blank["reason"] = _(
			"No recovery component is set in HR Settings, so the shortfall cannot be priced."
		)
		return blank

	blank["component"] = settings["component"]

	monthly, reason = get_component_amount(employee, settings["component"], as_on=as_on)
	if reason:
		blank["reason"] = reason
		return blank

	per_day = flt(monthly) / settings["divisor"]
	return {
		"amount": flt(per_day * days, 2),
		"per_day": flt(per_day, 2),
		"component": settings["component"],
		"days": days,
		"reason": None,
	}


def _settings():
	divisor = cint(frappe.db.get_single_value("HR Settings", "custom_notice_recovery_divisor"))
	return {
		"component": frappe.db.get_single_value("HR Settings", "custom_notice_recovery_component"),
		# Guard the divisor: a zero here would be a ZeroDivisionError on a form
		# somebody is trying to settle.
		"divisor": divisor if divisor > 0 else 30,
	}


def get_component_amount(employee, component, as_on=None):
	"""The monthly value of one salary component for one employee.

	Returns (amount, reason). `reason` is set only when the amount could not be
	determined, and is phrased for whoever is looking at the settlement.
	"""
	as_on = getdate(as_on or nowdate())

	assignment = frappe.db.get_value(
		"Salary Structure Assignment",
		{"employee": employee, "docstatus": 1, "from_date": ["<=", as_on]},
		["name", "salary_structure", "base", "variable"],
		order_by="from_date desc",
		as_dict=True,
	)
	if not assignment:
		return 0.0, _("{0} has no active Salary Structure Assignment.").format(employee)

	rows = frappe.get_all(
		"Salary Detail",
		filters={"parent": assignment.salary_structure, "parentfield": "earnings"},
		fields=["salary_component", "abbr", "amount", "amount_based_on_formula", "formula",
		        "condition"],
		order_by="idx asc",
	)
	if not any(r.salary_component == component for r in rows):
		return 0.0, _("{0} is not an earning on {1}.").format(
			component, assignment.salary_structure
		)

	# Seed with what the assignment carries, then let each component see the
	# ones evaluated before it — the order payroll relies on.
	data = frappe._dict(base=flt(assignment.base), variable=flt(assignment.variable))
	found = None

	for row in rows:
		amount, reason = _evaluate(row, data)
		if reason and row.salary_component == component:
			return 0.0, reason
		if amount is not None:
			data[row.abbr] = flt(amount)
		if row.salary_component == component:
			found = flt(amount or 0)

	if found is None:
		return 0.0, _("{0} did not evaluate to an amount.").format(component)
	return found, None


def _evaluate(row, data):
	"""One component's amount. Returns (amount, reason)."""
	from hrms.payroll.doctype.salary_slip.salary_slip import _safe_eval

	try:
		if row.condition and not _safe_eval(row.condition, None, data):
			return 0.0, None
		if row.amount_based_on_formula and row.formula:
			return flt(_safe_eval(row.formula, None, data)), None
		return flt(row.amount), None
	except Exception as exc:
		# Deliberately not re-raised: one unevaluable component should not stop a
		# settlement being opened. The caller surfaces this instead.
		return None, _("Could not evaluate {0} on the salary structure: {1}").format(
			row.salary_component, str(exc)[:120]
		)
