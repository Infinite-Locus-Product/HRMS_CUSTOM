"""PWA endpoints for the separation clearances (stages 6 and 7).

Stage 6 (Manager Clearance) is a two-sided form: the leaver fills the handover
half, their reporting manager verifies and completes it. Both sides live here.

Stage 7 (IT Clearance) is read-only from the app. IT works in Desk; what the
leaver and their manager need on a phone is visibility of what was recorded
against them, because it drives a deduction from the final settlement.

Every endpoint is scoped to `frappe.session.user`'s own Employee record. None of
them take an employee argument, so there is nothing to tamper with, and the
permission hooks narrow the rows on top of that.
"""

import frappe
from frappe import _
from frappe.utils import cint

MANAGER_CLEARANCE = "Separation Manager Clearance"
IT_CLEARANCE = "Separation IT Clearance"

DRAFT = "Draft"
PENDING_MANAGER = "Pending Manager Clearance"

# Filled by the leaver, before their half is submitted.
EMPLOYEE_FIELDS = (
	"primary_successor",
	"project_client_status_summary",
	"downloaded_payslips",
	"downloaded_tax_slips",
	"cleared_personal_files",
)

# Filled by the reporting manager, before completing.
MANAGER_FIELDS = (
	"kt_handover_received",
	"client_handoff_complete",
	"code_repository_transferred",
	"access_revocation_not_applicable",
	"manager_remarks",
)


def _my_employee():
	name = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not name:
		frappe.throw(
			_("Your user account is not linked to an Employee record. Please contact HR."),
			title=_("No Employee Record"),
		)
	return name


def _select_options(doctype, fieldname):
	options = frappe.get_meta(doctype).get_field(fieldname).options or ""
	return [o for o in (opt.strip() for opt in options.split("\n")) if o]


# ---------------------------------------------------------------------------
# Stage 6 — Manager Clearance
# ---------------------------------------------------------------------------
def _clearance_view(doc):
	"""One payload for both sides of the form.

	`actions` is the workflow's transition list for THIS caller, so the screen
	derives its buttons from it rather than guessing from role or state. The act
	endpoint returns this same shape, so a decision can be swapped in directly
	instead of re-fetching into a cached copy.
	"""
	from frappe.model.workflow import get_transitions

	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	state = doc.get("workflow_state") or DRAFT

	data = {
		"name": doc.name,
		"docstatus": doc.docstatus,
		"workflow_state": state,
		"employee": doc.employee,
		"employee_name": doc.employee_name,
		"department": doc.department,
		"reporting_manager": doc.reporting_manager,
		"separation_status": doc.separation_status,
		"employee_separation": doc.employee_separation,
		# Which half of the form the caller is looking at.
		"my_role": "manager" if employee == doc.reporting_manager else "employee",
		"is_employee_half_editable": state in (DRAFT,) and employee == doc.employee,
		"handover_documents": [
			{
				"idx": row.idx,
				"title": row.title,
				"attachment": row.attachment,
				"file_name": row.file_name,
				"external_link": row.external_link,
				"notes": row.notes,
			}
			for row in doc.handover_documents or []
		],
		"access_revocation_requested": [
			row.access_system for row in doc.access_revocation_requested or []
		],
		# Resolved here so both screens can show a person rather than an ID.
		"primary_successor_name": frappe.db.get_value(
			"Employee", doc.primary_successor, "employee_name"
		) if doc.primary_successor else None,
		"actions": sorted({t.action for t in get_transitions(doc)}),
		"options": {
			"kt_handover_received": _select_options(MANAGER_CLEARANCE, "kt_handover_received"),
			"client_handoff_complete": _select_options(MANAGER_CLEARANCE, "client_handoff_complete"),
			"access_systems": frappe.get_all(
				"Access Revocation System", filters={"is_active": 1}, pluck="name", order_by="name"
			),
		},
	}
	for fieldname in EMPLOYEE_FIELDS + MANAGER_FIELDS:
		data[fieldname] = doc.get(fieldname)
	return data


@frappe.whitelist()
def get_my_clearance():
	"""The caller's own Manager Clearance, creating nothing."""
	employee = _my_employee()
	name = frappe.db.get_value(
		MANAGER_CLEARANCE, {"employee": employee, "docstatus": ["<", 2]}, "name"
	)
	if not name:
		return {"exists": False, "separation": _approved_separation_for(employee)}

	return {"exists": True, "clearance": _clearance_view(frappe.get_doc(MANAGER_CLEARANCE, name))}


def _approved_separation_for(employee):
	"""The separation a clearance could be raised against, if there is one."""
	return frappe.db.get_value(
		"Employee Separation",
		{"employee": employee, "workflow_state": "Approved", "docstatus": 1},
		"name",
	)


@frappe.whitelist()
def save_my_handover(payload, submit=False):
	"""Create or update the leaver's half, optionally sending it to the manager."""
	payload = frappe.parse_json(payload)
	employee = _my_employee()

	name = frappe.db.get_value(
		MANAGER_CLEARANCE, {"employee": employee, "docstatus": ["<", 2]}, "name"
	)
	if name:
		doc = frappe.get_doc(MANAGER_CLEARANCE, name)
		if doc.get("workflow_state") != DRAFT:
			frappe.throw(
				_("Your handover is already with your manager and can no longer be edited."),
				title=_("Locked"),
			)
	else:
		separation = _approved_separation_for(employee)
		if not separation:
			frappe.throw(
				_("You have no approved resignation, so there is nothing to hand over yet."),
				title=_("Nothing To Clear"),
			)
		doc = frappe.new_doc(MANAGER_CLEARANCE)
		doc.employee_separation = separation
		# Set these explicitly rather than leaving them to fetch_from. Frappe
		# checks create permission BEFORE validate runs, so at that moment a
		# fetched field is still empty — and the permission hook, which matches
		# the caller against `employee` / `reporting_manager`, would deny the
		# leaver access to their own new clearance. fetch_from then confirms
		# these same values on save.
		doc.employee = employee
		doc.reporting_manager = frappe.db.get_value(
			"Employee Separation", separation, "custom_reporting_manager"
		)

	for fieldname in EMPLOYEE_FIELDS:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))

	if "handover_documents" in payload:
		doc.handover_documents = []
		for index, row in enumerate(payload.get("handover_documents") or [], start=1):
			doc.append("handover_documents", {
				"title": _handover_title(row, index),
				"attachment": row.get("attachment"),
				"file_name": row.get("file_name"),
				"external_link": row.get("external_link"),
				"notes": row.get("notes"),
			})

	doc.save()

	if cint(submit):
		from frappe.model.workflow import apply_workflow

		doc = apply_workflow(doc, "Submit")

	return _clearance_view(frappe.get_doc(MANAGER_CLEARANCE, doc.name))


def _handover_title(row, index):
	"""A title for a handover row, derived when the caller did not give one.

	`title` is mandatory on the child table, and an untitled row therefore fails
	the whole save — which, on a form the employee has just spent time filling
	in, loses the lot. The app defaults it from the filename, but relying on the
	client to supply a value the server can work out itself means one stale
	bundle reintroduces the bug. Derived here so it cannot.
	"""
	title = (row.get("title") or "").strip()
	if title:
		return title

	# A file name reads best; then the tail of a link; then a plain ordinal.
	file_name = (row.get("file_name") or "").strip()
	if file_name:
		return file_name.rsplit(".", 1)[0]

	link = (row.get("external_link") or "").strip().rstrip("/")
	if link:
		return link.rsplit("/", 1)[-1][:140] or _("Handover link")

	attachment = (row.get("attachment") or "").strip()
	if attachment:
		return attachment.rsplit("/", 1)[-1].rsplit(".", 1)[0][:140]

	return _("Handover document {0}").format(index)


@frappe.whitelist()
def get_clearance_for_review(name):
	"""Full detail for the manager's review screen."""
	doc = frappe.get_doc(MANAGER_CLEARANCE, name)
	doc.check_permission("read")
	return _clearance_view(doc)


@frappe.whitelist()
def complete_clearance(name, payload=None):
	"""Record the manager's verification, then complete the clearance.

	Saved first, moved second: the controller's rules run on save, so an
	incomplete verification is refused BEFORE the workflow advances and the
	record stays where it was.
	"""
	doc = frappe.get_doc(MANAGER_CLEARANCE, name)
	doc.check_permission("write")

	payload = frappe.parse_json(payload) if payload else {}
	for fieldname in MANAGER_FIELDS:
		if fieldname in payload:
			doc.set(fieldname, payload.get(fieldname))

	if "access_revocation_requested" in payload:
		doc.access_revocation_requested = []
		for system in payload.get("access_revocation_requested") or []:
			doc.append("access_revocation_requested", {"access_system": system})

	doc.save()

	from frappe.model.workflow import apply_workflow

	doc = apply_workflow(doc, "Complete")
	return _clearance_view(frappe.get_doc(MANAGER_CLEARANCE, doc.name))


# ---------------------------------------------------------------------------
# Stage 7 — IT Clearance (read-only in the app)
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_my_it_clearance():
	"""What IT recorded, for the leaver and their manager to see.

	Read-only on purpose: IT fills this in Desk. The value here is that the
	leaver sees a recovery amount before it reaches their settlement, not after.
	"""
	employee = _my_employee()
	name = frappe.db.get_value(IT_CLEARANCE, {"employee": employee, "docstatus": ["<", 2]}, "name")
	if not name:
		return {"exists": False}

	doc = frappe.get_doc(IT_CLEARANCE, name)
	doc.check_permission("read")
	return {
		"exists": True,
		"clearance": {
			"name": doc.name,
			"docstatus": doc.docstatus,
			"finalised": doc.docstatus == 1,
			"last_working_day": doc.last_working_day,
			"access_revocation_datetime": doc.access_revocation_datetime,
			"mailbox_forwarding_address": doc.mailbox_forwarding_address,
			"total_recovery_amount": doc.total_recovery_amount,
			"assets": [
				{
					"asset_type": row.asset_type,
					"returned": row.returned,
					"asset_condition": row.asset_condition,
					"recovery_amount": row.recovery_amount,
					"remarks": row.remarks,
				}
				for row in doc.assets or []
			],
		},
	}


# ---------------------------------------------------------------------------
# The combined inbox
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_my_separation_inbox():
	"""Everything across the exit flow waiting on the caller, in one list.

	Managers should not have to know which of several tiles holds their pending
	item, so resignations and clearances arrive together, each row tagged with
	what it is and where it routes.
	"""
	from myhr.resignation_api import get_my_pending_approvals

	items = []

	for row in get_my_pending_approvals():
		items.append({
			"kind": "resignation",
			"name": row["name"],
			"employee": row["employee"],
			"employee_name": row["employee_name"],
			"badge": row["my_level"],
			"subtitle": _("Relieving {0}").format(row.get("custom_requested_relieving_date") or "—"),
			"warning": (
				_("{0} days short of notice").format(row["custom_notice_period_shortfall"])
				if row.get("custom_notice_period_shortfall") else None
			),
		})

	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if employee:
		for row in frappe.get_all(
			MANAGER_CLEARANCE,
			filters={
				"reporting_manager": employee,
				"workflow_state": PENDING_MANAGER,
				"docstatus": ["<", 2],
			},
			fields=["name", "employee", "employee_name", "primary_successor"],
			order_by="modified desc",
		):
			items.append({
				"kind": "manager_clearance",
				"name": row.name,
				"employee": row.employee,
				"employee_name": row.employee_name,
				"badge": _("Handover"),
				"subtitle": (
					_("Successor: {0}").format(
						frappe.db.get_value("Employee", row.primary_successor, "employee_name")
						or row.primary_successor
					)
					if row.primary_successor else _("No successor named")
				),
				"warning": None if row.primary_successor else _("No successor named"),
			})

	return items


# ---------------------------------------------------------------------------
# Stage 9 — Full and Final Statement (read-only in the app)
# ---------------------------------------------------------------------------
FNF = "Full and Final Statement"


@frappe.whitelist()
def get_my_settlement():
	"""The caller's own final settlement, for them alone.

	Note the difference from the other clearance endpoints: this one is NOT
	shared with the reporting manager. The statement itemises salary, gratuity,
	leave encashment and bonus — someone's pay. A manager needs to know that a
	laptop was not returned; they have no business seeing what their report is
	being paid on the way out. Finance and HR reach it through Desk.

	`frappe.get_doc` does not run permission checks by itself, so the read is
	scoped by looking the statement up from the caller's own Employee record
	rather than by trusting an argument.
	"""
	employee = _my_employee()
	name = frappe.db.get_value(FNF, {"employee": employee, "docstatus": ["<", 2]}, "name")
	if not name:
		return {"exists": False}

	doc = frappe.get_doc(FNF, name)

	return {
		"exists": True,
		"settlement": {
			"name": doc.name,
			"docstatus": doc.docstatus,
			"finalised": doc.docstatus == 1,
			"status": doc.status,
			"relieving_date": doc.relieving_date,
			"payables": [
				{"component": r.component, "amount": r.amount, "status": r.status,
				 "remark": r.remark}
				for r in doc.payables or []
			],
			"receivables": [
				{"component": r.component, "amount": r.amount, "status": r.status,
				 "remark": r.remark}
				for r in doc.receivables or []
			],
			"total_payable_amount": doc.total_payable_amount,
			"total_receivable_amount": doc.total_receivable_amount,
			"net_payable": doc.get("custom_net_payable"),
			"notice_period_shortfall_days": doc.get("custom_notice_period_shortfall_days"),
			"payroll_cutoff_processed": doc.get("custom_payroll_cutoff_processed"),
			"finance_remarks": doc.get("custom_finance_remarks"),
		},
	}


# ---------------------------------------------------------------------------
# Stage 8 — HR Clearance (read-only in the app, and leaver-only)
# ---------------------------------------------------------------------------
HR_CLEARANCE = "Separation HR Clearance"


@frappe.whitelist()
def get_my_hr_clearance():
	"""The leaver's own HR clearance — chiefly, their relieving letter.

	Two things are deliberately NOT returned: `rehire_eligibility` and the
	internal reason behind it. "Would we hire them again, and why not" is an HR
	record about a person, not something to hand that person on their phone. The
	reason field is already `print_hide` so it cannot reach the letter; leaving
	it out here closes the other door.

	Not shared with the reporting manager either, for the same reason.

	Rather than list the internal blockers, the screen is told only whether the
	letter is ready and from when. An employee does not need to hear that HR has
	not filled in a re-hire field yet.
	"""
	employee = _my_employee()
	name = frappe.db.get_value(HR_CLEARANCE, {"employee": employee, "docstatus": ["<", 2]}, "name")
	if not name:
		return {"exists": False}

	doc = frappe.get_doc(HR_CLEARANCE, name)

	return {
		"exists": True,
		"clearance": {
			"name": doc.name,
			"docstatus": doc.docstatus,
			"finalised": doc.docstatus == 1,
			"last_working_day": doc.last_working_day,
			"exit_interview_done": bool(doc.exit_interview_is_done),
			"exit_interview_status": doc.exit_interview_status,
			"physical_assets": [
				{"label": _("Physical ID Badge"), "value": doc.physical_id_badge_returned},
				{"label": _("Cabinet / Desk Keys"), "value": doc.cabinet_desk_keys_returned},
				{"label": _("Parking Tag / Access"), "value": doc.parking_tag_returned},
			],
			"asset_damage_recovery_amount": doc.asset_damage_recovery_amount,
			"relieving_letter": doc.relieving_letter,
			"relieving_letter_released_on": doc.relieving_letter_released_on,
			"letter_ready": bool(doc.relieving_letter),
		},
	}


@frappe.whitelist()
def search_colleagues(query=None, limit=20):
	"""Active employees, for the successor picker in the app.

	Needed because the Employee doctype is locked down: `myhr.permissions`
	restricts a normal user to their own record (plus direct reports), so the
	framework's own Link search would return almost nothing and the picker would
	look broken.

	Visibility matches the Employee Directory, which is deliberately company-wide
	("a company contact book, not a personal record"). Only the same four public
	fields are returned — no contact details, no salary, no status beyond Active.
	Searching Employee directly rather than the directory table means nobody is
	missing because their directory flag is off.
	"""
	employee = _my_employee()
	limit = cint(limit) or 20

	filters = {"status": "Active", "name": ["!=", employee]}
	fields = ["name", "employee_name", "designation", "department"]

	if query:
		rows = frappe.get_all(
			"Employee",
			filters=filters,
			or_filters={"employee_name": ["like", f"%{query}%"], "name": ["like", f"%{query}%"]},
			fields=fields,
			order_by="employee_name asc",
			limit=min(limit, 50),
			ignore_permissions=True,
		)
	else:
		rows = frappe.get_all(
			"Employee", filters=filters, fields=fields,
			order_by="employee_name asc", limit=min(limit, 50), ignore_permissions=True,
		)
	return rows
