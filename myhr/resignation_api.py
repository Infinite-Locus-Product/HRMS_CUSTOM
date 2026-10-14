"""PWA endpoints for the employee-initiated resignation (Stage A).

The employee never touches the Desk form — they use the Resignation screen in
the HRMS PWA, which talks to the two endpoints here. Everything these return is
scoped to `frappe.session.user`'s own Employee record; there is no `employee`
argument to tamper with.

Approval itself is NOT here. Once the record is filed, routing is owned by the
`Employee Separation Approval` workflow (Draft -> Pending L1 -> Pending L2 ->
Approved / Rejected), whose transitions carry per-person conditions.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, nowdate

from myhr.employee_separation_hooks import (
	ACTIVE_DOCSTATUSES,
	MAX_DETAILED_REASON_CHARS,
	_find_active_separation,
	_get_notice_period_days,
)

# Echoed to the form so the employee sees the same read-only figures the server
# will compute on save.
EMPLOYEE_EDITABLE_FIELDS = (
	"custom_resignation_reason",
	"custom_detailed_reason",
	"custom_requested_relieving_date",
	"custom_buyout_notice_period",
	"custom_buyout_amount",
)

READ_ONLY_FIELDS = (
	"custom_reporting_manager",
	"custom_reporting_manager_name",
	"custom_l2_manager",
	"custom_l2_manager_name",
	"custom_official_end_date",
	"custom_notice_period_shortfall",
	"custom_decision",
	"custom_approved_relieving_date",
	"custom_rejection_hold_reason",
	"custom_notice_period_waiver",
	"custom_retention_discussion_held",
	"custom_l1_approved",
	"custom_l2_approved",
)


def _my_employee():
	name = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not name:
		frappe.throw(
			_("Your user account is not linked to an Employee record. Please contact HR."),
			title=_("No Employee Record"),
		)
	return frappe.get_doc("Employee", name)


def _select_options(fieldname):
	options = frappe.get_meta("Employee Separation").get_field(fieldname).options or ""
	return [o for o in (opt.strip() for opt in options.split("\n")) if o]


@frappe.whitelist()
def get_my_resignation():
	"""Everything the Resignation screen needs in one round trip."""
	employee = _my_employee()
	notice_period_days = _get_notice_period_days(employee.name)
	anchor = getdate(employee.resignation_letter_date or nowdate())

	out = {
		"employee": {
			"name": employee.name,
			"employee_name": employee.employee_name,
			"department": employee.department,
			"designation": employee.designation,
			"company": employee.company,
			"date_of_joining": employee.date_of_joining,
			"notice_period_days": notice_period_days,
			"reporting_manager": frappe.db.get_value("Employee", employee.reports_to, "employee_name")
			if employee.reports_to
			else None,
			"l2_manager": frappe.db.get_value("Employee", employee.custom_l2_manager, "employee_name")
			if employee.custom_l2_manager
			else None,
		},
		"defaults": {
			"official_end_date": add_days(anchor, notice_period_days),
			"requested_relieving_date": add_days(anchor, notice_period_days),
			"min_relieving_date": nowdate(),
		},
		"options": {
			"resignation_reason": _select_options("custom_resignation_reason"),
			"buyout": _select_options("custom_buyout_notice_period"),
			"max_detailed_reason_chars": MAX_DETAILED_REASON_CHARS,
		},
		"existing": None,
	}

	existing = _find_active_separation(employee.name)
	if existing:
		out["existing"] = _serialize(frappe.get_doc("Employee Separation", existing))

	return out


def _serialize(doc):
	data = {
		"name": doc.name,
		"docstatus": doc.docstatus,
		"workflow_state": doc.get("workflow_state"),
		"editable": doc.get("workflow_state") in ("Draft", "Rejected"),
	}
	for fieldname in EMPLOYEE_EDITABLE_FIELDS + READ_ONLY_FIELDS:
		data[fieldname] = doc.get(fieldname)
	return data


@frappe.whitelist()
def save_my_resignation(payload, submit=False):
	"""Create or update the caller's own resignation, optionally filing it.

	`submit` moves it Draft -> Pending L1 Approval through the workflow. It is
	deliberately a workflow action, not `doc.submit()`: the record must stay a
	draft while under approval so a rejection can hand it back for editing.
	"""
	payload = frappe.parse_json(payload)
	employee = _my_employee()

	existing = _find_active_separation(employee.name)
	if existing:
		doc = frappe.get_doc("Employee Separation", existing)
		if doc.get("workflow_state") not in ("Draft", "Rejected"):
			frappe.throw(
				_("This resignation is already with your approver and can no longer be edited."),
				title=_("Locked"),
			)
	else:
		doc = frappe.new_doc("Employee Separation")
		doc.employee = employee.name
		doc.company = employee.company
		doc.boarding_begins_on = nowdate()

	for fieldname in EMPLOYEE_EDITABLE_FIELDS:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))

	doc.save()

	if cint(submit):
		from frappe.model.workflow import apply_workflow

		doc = apply_workflow(doc, "Submit")

	return _serialize(frappe.get_doc("Employee Separation", doc.name))


@frappe.whitelist()
def get_my_pending_approvals():
	"""Resignations waiting on the caller as L1 or L2.

	The permission query condition already limits the caller to records naming
	them, so this only has to filter by state.
	"""
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		return []

	rows = frappe.get_all(
		"Employee Separation",
		filters={"docstatus": ["in", ACTIVE_DOCSTATUSES]},
		or_filters={"custom_reporting_manager": employee, "custom_l2_manager": employee},
		fields=[
			"name", "employee", "employee_name", "workflow_state",
			"custom_requested_relieving_date", "custom_notice_period_shortfall",
			"custom_reporting_manager", "custom_l2_manager",
		],
		order_by="modified desc",
	)

	pending = []
	for row in rows:
		is_l1 = row.custom_reporting_manager == employee and row.workflow_state == "Pending L1 Approval"
		is_l2 = row.custom_l2_manager == employee and row.workflow_state == "Pending L2 Approval"
		if is_l1 or is_l2:
			row["my_level"] = "L1" if is_l1 else "L2"
			pending.append(row)
	return pending


# ---------------------------------------------------------------------------
# Approver side (L1 / L2)
# ---------------------------------------------------------------------------
# Fields the approver fills. `custom_decision` is NOT here: it is derived from
# the action they take, so the button and the stored decision can never disagree.
APPROVER_FIELDS = (
	"custom_approved_relieving_date",
	"custom_notice_period_waiver",
	"custom_retention_discussion_held",
	"custom_rejection_hold_reason",
)

ACTION_DECISION = {"Approve": "Approve", "Reject": "Reject"}


def _assert_can_act(doc):
	"""Confirm the caller is this record's approver for its CURRENT state.

	This is a guard for a clear error message, not the security boundary — that
	is the workflow transition condition, which `apply_workflow` re-derives
	server-side regardless of what this function says.
	"""
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		frappe.throw(_("Your user account is not linked to an Employee record."))

	state = doc.get("workflow_state")
	if state == "Pending L1 Approval" and doc.custom_reporting_manager == employee:
		return "L1"
	if state == "Pending L2 Approval" and doc.custom_l2_manager == employee:
		return "L2"

	frappe.throw(
		_("This resignation is not waiting on you. Its current state is {0}.").format(
			frappe.bold(state or _("Draft"))
		),
		title=_("Not Your Approval"),
	)


@frappe.whitelist()
def get_separation_for_approval(name):
	"""Full detail of one resignation, for the approver's screen."""
	doc = frappe.get_doc("Employee Separation", name)
	doc.check_permission("read")
	return _approval_view(doc)


def _approval_view(doc):
	"""The approver screen's payload, including the caller's available actions.

	`act_on_separation` returns this same shape so the screen can swap in the
	post-decision state directly. Re-fetching instead would hand back a cached
	copy (same endpoint, same argument) still showing the old state and buttons.
	"""
	from frappe.model.workflow import get_transitions

	data = _serialize(doc)
	data.update(
		{
			"employee_name": doc.employee_name,
			"department": doc.department,
			"designation": doc.designation,
			"company": doc.company,
			"date_of_joining": frappe.db.get_value("Employee", doc.employee, "date_of_joining"),
			"resignation_letter_date": doc.resignation_letter_date,
			"actions": sorted({t.action for t in get_transitions(doc)}),
			"options": {
				"waiver": _select_options("custom_notice_period_waiver"),
				"retention": _select_options("custom_retention_discussion_held"),
			},
		}
	)
	return data


@frappe.whitelist()
def act_on_separation(name, action, payload=None):
	"""Record the approver's fields, then move the document.

	The two steps are deliberately in this order: `doc.save()` runs
	`_validate_approval`, so an Approve with the mandatory approver fields
	missing is rejected BEFORE the workflow advances. Doing it the other way
	round could move the record and then fail, leaving it in the next state
	with half its data.
	"""
	if action not in ACTION_DECISION:
		frappe.throw(_("{0} is not a valid action.").format(action))

	doc = frappe.get_doc("Employee Separation", name)
	doc.check_permission("read")
	_assert_can_act(doc)

	payload = frappe.parse_json(payload) if payload else {}
	for fieldname in APPROVER_FIELDS:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))

	doc.custom_decision = ACTION_DECISION[action]
	doc.save()

	if action == "Approve":
		_assert_submittable(doc)

	from frappe.model.workflow import apply_workflow

	doc = apply_workflow(doc, action)
	# Full view, not just the fields: the screen needs the caller's NEW action
	# list so the buttons disappear once they are done.
	return _approval_view(frappe.get_doc("Employee Separation", doc.name))


def _assert_submittable(doc):
	"""Fail early, and legibly, if the final approval would blow up on submit.

	Approving at L2 moves the record to `Approved`, which is docstatus 1. Stock
	HRMS's EmployeeBoardingController.on_submit then builds the separation
	activity tasks, and that resolves a Holiday List for the employee. If there
	isn't one, it throws a message full of markup from deep inside HRMS that
	says nothing about resignations — the approver just sees the button do
	nothing useful. Checking here turns it into an actionable sentence, before
	anything moves.
	"""
	if doc.get("workflow_state") != "Pending L2 Approval":
		return  # L1's approval does not submit, so nothing to pre-check

	from hrms.utils.holiday_list import get_holiday_list_for_employee

	if get_holiday_list_for_employee(doc.employee, raise_exception=False):
		return

	frappe.throw(
		_(
			"{0} has no Holiday List, and neither does {1}. Approving would create the "
			"separation tasks, which needs one. Ask HR to assign a Holiday List to the "
			"employee or the company, then approve again."
		).format(frappe.bold(doc.employee_name or doc.employee), frappe.bold(doc.company)),
		title=_("Holiday List Missing"),
	)
