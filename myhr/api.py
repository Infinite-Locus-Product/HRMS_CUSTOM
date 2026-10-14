"""
Whitelisted API endpoints for myHR.
"""

import json

import frappe
from frappe import _

from myhr.leave_optional_holiday import validate_optional_leave_dates
from myhr.myhr.doctype.employee_action_centre.employee_action_centre import (
	AC_DOCUMENT_ROWS,
	log_activity,
)


_HR_ROLES_THAT_CAN_SUBMIT_ANYTHING = {"HR Manager", "System Manager"}


@frappe.whitelist()
def submit_expense_claim_for_review(name):
	"""Mark an Expense Claim as "submitted for review" by its filer.

	ERPNext's docstatus 0→1 transition on Expense Claim is gated by
	`on_submit` requiring `approval_status in ("Approved", "Rejected")`
	— only the approver can flip docstatus. Our PWA flow needs an
	intermediate "employee is done editing, approver may now act"
	state, so we use a custom flag instead of touching docstatus.

	Sets `custom_submitted_for_review = 1` plus audit timestamps. Doc
	stays at docstatus=0 until the approver decides via approval_status.

	Permission rules:
	- Doc owner can submit their own draft (only when not already
	  submitted-for-review).
	- HR Manager / System Manager can submit on anyone's behalf.
	- Anyone else: PermissionError.
	"""
	doc = frappe.get_doc("Expense Claim", name)
	if doc.docstatus != 0:
		frappe.throw(
			_("This claim has already been decided and cannot be resubmitted."),
			title=_("Already decided"),
		)
	if doc.get("custom_submitted_for_review"):
		frappe.throw(
			_("This claim has already been submitted for review."),
			title=_("Already submitted"),
		)

	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	is_hr = bool(_HR_ROLES_THAT_CAN_SUBMIT_ANYTHING & roles)
	is_owner = doc.owner == user

	if not (is_owner or is_hr):
		frappe.throw(
			_("You can only submit your own drafts."),
			frappe.PermissionError,
		)

	doc.custom_submitted_for_review = 1
	doc.custom_submitted_on = frappe.utils.now_datetime()
	doc.custom_submitted_by = user
	doc.flags.ignore_permissions = True
	doc.save()
	return doc.as_dict()


@frappe.whitelist()
def submit_doc(doctype, name):
	"""Generic submit (docstatus 0 → 1) for non-EC submittable doctypes.

	Kept as a primitive for surfaces whose `on_submit` doesn't require
	an approval-status verdict. Not used by Expense Claim — see
	`submit_expense_claim_for_review` above for that flow.

	Permission rules: owner OR HR Manager / System Manager.
	"""
	doc = frappe.get_doc(doctype, name)
	if doc.docstatus != 0:
		frappe.throw(
			_("This document is not a draft and cannot be submitted again."),
			title=_("Already submitted"),
		)

	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	is_hr = bool(_HR_ROLES_THAT_CAN_SUBMIT_ANYTHING & roles)
	is_owner = doc.owner == user

	if not (is_owner or is_hr):
		frappe.throw(
			_("You can only submit your own drafts."),
			frappe.PermissionError,
		)

	doc.flags.ignore_permissions = True
	doc.submit()
	return doc.as_dict()


@frappe.whitelist()
def insert_and_submit(doc):
	"""Insert + submit in one round-trip.

	Kept as a primitive for surfaces that genuinely need the user to
	commit in one tap (no draft preview). The Expense Claim flow now
	prefers the save-then-submit-on-detail-view pattern instead — see
	`submit_doc` above and the design-system doc.

	Permissions: standard create + submit checks inside Document.insert()
	and Document.submit() — no additional gate needed here.
	"""
	if isinstance(doc, str):
		doc = json.loads(doc)
	if not isinstance(doc, dict):
		frappe.throw(_("`doc` must be a dict or JSON object."))

	cur = frappe.get_doc(doc)
	cur.insert()
	cur.submit()
	return cur.as_dict()


def _ac_employee_writable_fields():
	"""Fieldnames an employee (non-HR) is allowed to mutate via the AC API.

	HR-only fields (`*_approval_status`, `*_remarks`, `status`, `submitted_*`,
	`medical_insurance_policy`) are NOT included — those flow through HR's
	desk save or through the dedicated `submit_action_centre` endpoint.
	"""
	from myhr.myhr.doctype.employee_action_centre.employee_action_centre import (
		AC_DECLARATION_ROWS,
	)

	allowed = set()
	for prefix, _label, _mand, has_na, file_suffix in AC_DOCUMENT_ROWS:
		allowed.add(f"{prefix}{file_suffix}")
		if has_na:
			allowed.add(f"{prefix}_is_na")
	# Employer slot metadata. Slot 1 (Most Recent Employer) gets its own N/A
	# flag too — for freshers who have no prior employer to document.
	for slot in (1, 2, 3, 4, 5):
		allowed.update({f"employer_{slot}_name", f"employer_{slot}_from", f"employer_{slot}_till"})
	allowed.add("employer_1_is_na")
	# Declarations: employee writes the data field (Select) + is_na. The
	# linked policy (medical_insurance_policy) is HR-only and stays out.
	for prefix, _label, _mand, has_na, data_suffix in AC_DECLARATION_ROWS:
		allowed.add(f"{prefix}{data_suffix}")
		if has_na:
			allowed.add(f"{prefix}_is_na")
	# Medical insurance opt-out: employee uploads the signed declaration.
	# The blank template lives in `Medical Insurance Opt Out Declaration`
	# (HR-managed) and is never written through this surface.
	allowed.add("medical_insurance_signed_optout")

	# Personal / statutory / identity-number data fields. Pulled from the
	# canonical list in employee_action_centre.py so adding a new field
	# there auto-extends the whitelist.
	from myhr.myhr.doctype.employee_action_centre.employee_action_centre import (
		AC_PERSONAL_DATA_FIELDS,
	)
	for fieldname, _label, _mand in AC_PERSONAL_DATA_FIELDS:
		allowed.add(fieldname)
	return allowed


def _enforce_employee_field_whitelist(fieldnames):
	"""Throw if a non-HR caller is trying to mutate a non-whitelisted field."""
	if {"HR Manager", "System Manager"} & set(frappe.get_roles()):
		return
	allowed = _ac_employee_writable_fields()
	bad = [f for f in fieldnames if f not in allowed]
	if bad:
		frappe.throw(
			"You are not allowed to modify the following fields: " + ", ".join(bad),
			frappe.PermissionError,
		)


def _enforce_valid_ac_prefix(prefix):
	"""Reject calls that pass a prefix not in AC_DOCUMENT_ROWS — defends against
	smuggling arbitrary fieldnames through `reupload_document` / `reset_action_centre_field`.
	"""
	valid = {p for p, _l, _m, _h, _s in AC_DOCUMENT_ROWS}
	if prefix not in valid:
		frappe.throw(f"Invalid document prefix: {prefix!r}", frappe.PermissionError)


def _ac_belongs_to_session_user(ac_name):
	"""Return True if the AC's `employee` resolves to the calling user's own Employee."""
	if {"HR Manager", "System Manager"} & set(frappe.get_roles()):
		return True
	emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not emp:
		return False
	return frappe.db.get_value("Employee Action Centre", ac_name, "employee") == emp

# Derived from AC_DOCUMENT_ROWS — the PWA payload uses this to render Employer 1
# split docs. The mandatory flag for the 3 payslip rows is HR-tunable via
# HR Settings (`custom_ac_require_payslip_*`), so we resolve it on every call
# rather than caching a static list at module load. The PWA filters out rows
# where `show_in_pwa` is false; Desk continues to show all rows but the
# master status compute treats hidden rows as optional.
def _get_employer_1_doc_fields():
	from myhr.myhr.doctype.employee_action_centre.employee_action_centre import (
		get_effective_mandatory,
		is_payslip_shown_in_pwa,
	)
	return [
		(
			prefix,
			_(label),
			1 if get_effective_mandatory(prefix, default_mandatory) else 0,
			1 if is_payslip_shown_in_pwa(prefix) else 0,
		)
		for prefix, label, default_mandatory, _has_na, _suffix in AC_DOCUMENT_ROWS
		if prefix.startswith("employer_1_")
	]


def _derive_employer_1_status(doc):
	"""Derive employer_1 card status from its split document rows (PWA badge only).

	Most Recent Employer N/A short-circuits everything: the card shows the same
	"Awaiting HR" pill that other N/A slots show — the parent flag is the
	verdict, no sub-doc rows are evaluated."""
	if doc.get("employer_1_is_na"):
		return "Awaiting HR"

	from myhr.myhr.doctype.employee_action_centre.employee_action_centre import (
		get_effective_mandatory,
	)
	rows = [
		{
			"file": doc.get(f"{prefix}_doc"),
			"status": doc.get(f"{prefix}_approval_status") or "Pending",
			"mandatory": get_effective_mandatory(prefix, default_mandatory),
		}
		for prefix, _label, default_mandatory, _has_na, _suffix in AC_DOCUMENT_ROWS
		if prefix.startswith("employer_1_")
	]

	if any(r["status"] == "Rejected" for r in rows):
		return "Rejected"

	mandatory_rows = [r for r in rows if r["mandatory"]]
	if mandatory_rows and all(r["status"] == "Accepted" for r in mandatory_rows):
		return "Accepted"

	if any(r["file"] or r["status"] == "Awaiting HR" for r in rows):
		return "Awaiting HR"

	return "Pending"


@frappe.whitelist()
def get_employee_directory():
	"""Return all directory rows whose linked Employee is currently Active.

	Visibility is intentionally global — every authenticated user sees every Active
	colleague (this is a company contact book, not a personal record). The Active
	filter is enforced here as a safety net even though `validate_employee` already
	prunes inactive rows on save.
	"""
	return frappe.db.sql(
		"""
		select
			d.employee_id, d.employee_name, d.designation,
			d.department, d.mobile_number, d.employee_email,
			e.image as image
		from `tabEmployee Directory` d
		inner join `tabEmployee` e on e.name = d.employee_id
		where e.status = 'Active'
		order by d.employee_name asc
		""",
		as_dict=True,
	)


@frappe.whitelist()
def rebuild_employee_directory():
	"""Backfill directory rows from Employee. Admin-only.

	Iterates every Employee with `custom_emp_directory=1` and `status='Active'`,
	upserts a matching directory row, and removes rows whose Employee no longer
	qualifies. Returns a count summary.

	Sets `frappe.flags.allow_directory_write` so the EmployeeDirectory
	canonical-write guards (DIR-1 / DIR-2) recognise this as a sanctioned
	syncer. Always cleared in the finally block.
	"""
	if "System Manager" not in frappe.get_roles() and "HR Manager" not in frappe.get_roles():
		frappe.throw(_("Only HR can rebuild the directory."))

	added = updated = removed = 0

	target_employees = frappe.get_all(
		"Employee",
		filters={"custom_emp_directory": 1, "status": "Active"},
		fields=["name", "employee_name", "designation", "department", "cell_number", "company_email"],
	)
	target_names = {e.name for e in target_employees}

	frappe.flags.allow_directory_write = True
	try:
		for e in target_employees:
			payload = {
				"doctype": "Employee Directory",
				"employee_id": e.name,
				"employee_name": e.employee_name,
				"designation": e.designation,
				"department": e.department,
				"mobile_number": e.cell_number,
				"employee_email": e.company_email,
			}
			if frappe.db.exists("Employee Directory", e.name):
				d = frappe.get_doc("Employee Directory", e.name)
				d.update(payload)
				d.save(ignore_permissions=True)
				updated += 1
			else:
				frappe.get_doc(payload).insert(ignore_permissions=True)
				added += 1

		# Drop directory rows whose Employee no longer qualifies (inactive /
		# unticked / deleted).
		for d in frappe.get_all("Employee Directory", pluck="name"):
			if d not in target_names:
				frappe.delete_doc("Employee Directory", d, ignore_permissions=True)
				removed += 1
	finally:
		frappe.flags.allow_directory_write = False

	frappe.db.commit()
	return {"added": added, "updated": updated, "removed": removed}


@frappe.whitelist()
def get_directory_audit():
	"""HR-only: report inconsistencies between Employee + Employee Directory.

	Returns a dict with three lists:
	  - `orphan_directory_rows`: directory rows whose linked Employee is
	    missing or no longer Active or no longer ticked `custom_emp_directory`
	  - `missing_directory_rows`: Active employees with `custom_emp_directory=1`
	    who don't have a directory row
	  - `out_of_sync`: directory rows whose `employee_name / designation /
	    department / mobile_number / employee_email` differ from the source
	    Employee record (rare — would indicate a save path that bypasses the
	    canonical syncer)

	Closes DIR-3. After running, HR can call `rebuild_employee_directory` to
	auto-fix everything.
	"""
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can audit the directory.", frappe.PermissionError)

	# Pull both sides
	emps = frappe.get_all(
		"Employee",
		fields=["name", "employee_name", "designation", "department", "cell_number",
		        "company_email", "status", "custom_emp_directory"],
	)
	emp_by_name = {e.name: e for e in emps}
	directory = frappe.get_all(
		"Employee Directory",
		fields=["name", "employee_id", "employee_name", "designation", "department",
		        "mobile_number", "employee_email"],
	)

	orphans = []
	out_of_sync = []
	for d in directory:
		emp = emp_by_name.get(d.employee_id)
		if not emp:
			orphans.append({"directory_row": d.name, "reason": "Linked Employee missing"})
			continue
		if emp.status != "Active":
			orphans.append({"directory_row": d.name, "reason": f"Employee status = {emp.status}"})
			continue
		if not emp.custom_emp_directory:
			orphans.append({"directory_row": d.name, "reason": "Employee.custom_emp_directory = 0"})
			continue
		# Compare projected fields
		mismatches = []
		for d_field, e_field in [
			("employee_name", "employee_name"),
			("designation", "designation"),
			("department", "department"),
			("mobile_number", "cell_number"),
			("employee_email", "company_email"),
		]:
			if (d.get(d_field) or "") != (emp.get(e_field) or ""):
				mismatches.append({"field": d_field,
				                   "directory": d.get(d_field) or "",
				                   "employee": emp.get(e_field) or ""})
		if mismatches:
			out_of_sync.append({"directory_row": d.name, "mismatches": mismatches})

	directory_names = {d.employee_id for d in directory}
	missing = [
		{"employee": e.name, "employee_name": e.employee_name}
		for e in emps
		if e.status == "Active" and e.custom_emp_directory and e.name not in directory_names
	]

	return {
		"orphan_directory_rows": orphans,
		"missing_directory_rows": missing,
		"out_of_sync": out_of_sync,
		"summary": {
			"total_directory_rows": len(directory),
			"total_active_in_scope_employees": sum(
				1 for e in emps if e.status == "Active" and e.custom_emp_directory
			),
			"orphan_count": len(orphans),
			"missing_count": len(missing),
			"out_of_sync_count": len(out_of_sync),
		},
	}


@frappe.whitelist()
def get_blocking_policies():
	"""Return the current user's blocking policies (active + mandatory-check-in
	+ status=Pending).

	Used by the PWA pre-flight modal before Employee Checkin and Attendance
	Request. Empty list ⇒ user can proceed. Each row carries title + file so
	the modal can render names and link to the policy PDF directly.
	"""
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return {"employee": None, "blocking": []}

	from myhr.policy_gate import get_blocking_policies as _impl
	return {"employee": employee, "blocking": _impl(employee)}


@frappe.whitelist()
def can_open_attendance_request():
	"""Backwards-compatible wrapper around get_blocking_policies.

	Used by `Home.vue` to gate the Quick Link tap. Newer code should call
	`get_blocking_policies` directly and render its own modal — this endpoint
	is kept so the existing alert flow keeps working until that view is
	migrated to the modal.
	"""
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return {"allowed": False, "message": _("No employee record linked to this user.")}

	from myhr.policy_gate import get_blocking_policies as _impl
	pending = _impl(employee)
	if pending:
		return {
			"allowed": False,
			"message": _("Please acknowledge required HR policies first."),
			"pending_mandatory_policies": [p["name"] for p in pending],
			"blocking": pending,
		}
	return {"allowed": True}


@frappe.whitelist()
def get_employee_policies():
	"""Return the current session user's policies (pending + acknowledged) for the PWA."""
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return {"error": "no_employee", "message": _("No employee record linked to this user.")}

	from myhr.policy_hooks import query_employee_pas
	rows = query_employee_pas(employee, statuses=("Pending", "Acknowledged"))
	for r in rows:
		r["acknowledged_at"] = str(r.get("acknowledged_at") or "")

	return {"employee": employee, "policies": rows}


@frappe.whitelist()
def get_employee_policy_history(hr_policy):
	"""Return prior-version acknowledgements (Superseded + Withdrawn) for the
	session user + policy. Withdrawn rows surface here so the user can see
	'this policy was retired before I got to it' in history.
	"""
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return {"error": "no_employee"}

	rows = frappe.db.sql(
		"""
		SELECT pa.name, pa.policy_version, pa.status, pa.acknowledged_at
		FROM `tabPolicy Acknowledgement` pa
		WHERE pa.employee = %s AND pa.hr_policy = %s
		  AND pa.status IN ('Superseded', 'Withdrawn')
		ORDER BY pa.policy_version DESC, pa.creation DESC
		""",
		(employee, hr_policy),
		as_dict=True,
	)
	for r in rows:
		r["acknowledged_at"] = str(r.get("acknowledged_at") or "")
	return {"history": rows}


@frappe.whitelist()
def get_pending_policy_count():
	"""Quick count for the PWA home badge.

	Counts only Pending rows on active policies. Withdrawn / Superseded are
	excluded (the PWA doesn't surface them as actionable).
	"""
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return {"count": 0, "blocking_count": 0}

	# Direct aggregate query — `query_employee_pas` returns rows; aggregate
	# shape needs custom SQL. Same WHERE conventions though.
	row = frappe.db.sql(
		"""
		SELECT COUNT(*) AS cnt,
		       SUM(CASE WHEN hp.mandatory_check_in_block = 1 THEN 1 ELSE 0 END) AS blocking
		FROM `tabPolicy Acknowledgement` pa
		INNER JOIN `tabHR Policy` hp ON hp.name = pa.hr_policy
		WHERE pa.employee = %s
		  AND pa.status = 'Pending'
		  AND hp.is_active = 1
		""",
		employee,
		as_dict=True,
	)
	if not row:
		return {"count": 0, "blocking_count": 0}
	return {
		"count": int(row[0].get("cnt") or 0),
		"blocking_count": int(row[0].get("blocking") or 0),
	}


@frappe.whitelist()
def acknowledge_policy_acknowledgement(name):
	"""Acknowledge a single Policy Acknowledgement row (PWA).

	Idempotent on already-Acknowledged. Refuses if status is Superseded /
	Withdrawn or if the linked HR Policy is no longer active. Validates that
	the row belongs to the calling user — employees cannot acknowledge
	someone else's policy. The PA controller's `validate()` stamps
	`acknowledged_at` / `ip_address` on the Pending → Acknowledged
	transition; this endpoint just flips the status. The PA `on_update` hook
	writes the audit log row (`via='ORM'`); we annotate to `via='API'` here
	by setting a flag so the log accurately reflects the entry path.
	"""
	pa = frappe.get_doc("Policy Acknowledgement", name)
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		caller_emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if not caller_emp or pa.employee != caller_emp:
			frappe.throw("You can only acknowledge your own policies.", frappe.PermissionError)
	if pa.status == "Acknowledged":
		return {"status": "already_acknowledged"}
	if pa.status == "Superseded":
		frappe.throw(_("This policy version has been superseded. Please acknowledge the latest version."))
	if pa.status == "Withdrawn":
		frappe.throw(_("This policy was withdrawn. There is nothing to acknowledge."))
	# Closes C-3: refuse to ack a row whose policy has been deactivated.
	if not frappe.db.get_value("HR Policy", pa.hr_policy, "is_active"):
		frappe.throw(_("This policy is no longer active. There is nothing to acknowledge."))
	pa.status = "Acknowledged"
	frappe.flags.policy_audit_via = "API"
	try:
		pa.save(ignore_permissions=True)
	finally:
		frappe.flags.policy_audit_via = None
	frappe.db.commit()
	return {"status": "success"}


@frappe.whitelist()
def bulk_acknowledge_for_employee(employee, hr_policy=None):
	"""Mark every Pending acknowledgement for `employee` as Acknowledged.

	Optional `hr_policy` filter restricts the bulk-ack to one policy. Only HR
	Manager / System Manager may call this — bulk-acking on someone else's
	behalf is an HR-only operation. Closes E-2.

	Returns `{acked: N, skipped: M, employee: …}`. Each Pending row is
	transitioned via the ORM so the state machine stamps audit fields and
	the audit log captures `via='BulkAck'`.
	"""
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can bulk-acknowledge.", frappe.PermissionError)
	if not frappe.db.exists("Employee", employee):
		frappe.throw(_("Employee {0} not found").format(employee))

	filters = {"employee": employee, "status": "Pending"}
	if hr_policy:
		filters["hr_policy"] = hr_policy

	candidates = frappe.get_all("Policy Acknowledgement", filters=filters, pluck="name")
	acked = skipped = 0
	for pa_name in candidates:
		# Skip rows whose linked policy is now inactive — same gate as the
		# single-row API; we don't want bulk-ack producing meaningless rows.
		hp = frappe.db.get_value("Policy Acknowledgement", pa_name, "hr_policy")
		if not frappe.db.get_value("HR Policy", hp, "is_active"):
			skipped += 1
			continue
		pa = frappe.get_doc("Policy Acknowledgement", pa_name)
		pa.status = "Acknowledged"
		frappe.flags.policy_audit_via = "BulkAck"
		try:
			pa.save(ignore_permissions=True)
		finally:
			frappe.flags.policy_audit_via = None
		acked += 1
	frappe.db.commit()
	return {"employee": employee, "acked": acked, "skipped": skipped, "total": len(candidates)}


@frappe.whitelist()
def bulk_acknowledge_for_policy(hr_policy):
	"""Mark every Pending acknowledgement on `hr_policy` as Acknowledged
	across all in-scope active employees. HR-only. Closes E-2.
	"""
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can bulk-acknowledge.", frappe.PermissionError)
	if not frappe.db.exists("HR Policy", hr_policy):
		frappe.throw(_("HR Policy {0} not found").format(hr_policy))
	if not frappe.db.get_value("HR Policy", hr_policy, "is_active"):
		frappe.throw(_("HR Policy {0} is not active.").format(hr_policy))

	candidates = frappe.get_all(
		"Policy Acknowledgement",
		filters={"hr_policy": hr_policy, "status": "Pending"},
		pluck="name",
	)
	acked = 0
	for pa_name in candidates:
		pa = frappe.get_doc("Policy Acknowledgement", pa_name)
		pa.status = "Acknowledged"
		frappe.flags.policy_audit_via = "BulkAck"
		try:
			pa.save(ignore_permissions=True)
		finally:
			frappe.flags.policy_audit_via = None
		acked += 1
	frappe.db.commit()
	return {"hr_policy": hr_policy, "acked": acked, "total": len(candidates)}


@frappe.whitelist()
def force_reacknowledgement_campaign(hr_policy, reason):
	"""Bump the policy `version` even though `file` hasn't changed, so every
	in-scope active employee gets a fresh Pending row at the new version
	(existing Pending/Acknowledged rows go to Superseded). Closes E-5.

	Use case: annual policy refresh where the document is unchanged but HR
	wants a fresh acknowledgement on file. `reason` is required and goes
	into the audit log.
	"""
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can run a re-ack campaign.", frappe.PermissionError)
	if not frappe.db.exists("HR Policy", hr_policy):
		frappe.throw(_("HR Policy {0} not found").format(hr_policy))
	if not (reason or "").strip():
		frappe.throw(_("Reason is required for a re-acknowledgement campaign."))

	doc = frappe.get_doc("HR Policy", hr_policy)
	if not doc.is_active:
		frappe.throw(_("Cannot run a re-ack campaign on an inactive policy."))

	# Force-bump the version and tag the audit `via`.
	doc.version = (doc.version or 1) + 1
	frappe.flags.policy_audit_via = "VersionBump"
	frappe.flags.policy_reack_reason = reason.strip()
	try:
		# Trigger save → validate_hr_policy will not double-bump (it only bumps
		# on `has_value_changed("file")`); after_save_hr_policy seeds + supersedes
		# at the new version.
		doc.save(ignore_permissions=True)
	finally:
		frappe.flags.policy_audit_via = None
		frappe.flags.policy_reack_reason = None
	frappe.db.commit()

	new_version = doc.version
	seeded = frappe.db.count(
		"Policy Acknowledgement",
		{"hr_policy": hr_policy, "policy_version": new_version, "status": "Pending"},
	)
	return {"hr_policy": hr_policy, "new_version": new_version, "seeded": seeded, "reason": reason.strip()}


@frappe.whitelist()
def bulk_approve_leave_applications(names):
	"""HR-only: bulk-approve a list of in-flight (docstatus=0) Leave
	Applications. Each row flips status='Approved' and the override class
	auto-submits via on_update. Closes LA-AR-bulk.

	`names`: comma-separated string or JSON list of Leave Application names.
	Returns `{approved, skipped, errors}`.
	"""
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can bulk-approve.", frappe.PermissionError)

	if isinstance(names, str):
		try:
			parsed = frappe.parse_json(names)
			if isinstance(parsed, list):
				name_list = parsed
			else:
				name_list = [n.strip() for n in names.split(",") if n.strip()]
		except Exception:
			name_list = [n.strip() for n in names.split(",") if n.strip()]
	else:
		name_list = list(names)

	approved = skipped = errors = 0
	error_log = []
	for n in name_list:
		try:
			la = frappe.get_doc("Leave Application", n)
			if la.docstatus != 0:
				skipped += 1
				continue
			if la.status == "Approved":
				skipped += 1
				continue
			la.status = "Approved"
			la.save(ignore_permissions=True)
			approved += 1
		except Exception as e:
			errors += 1
			error_log.append({"name": n, "error": str(e)[:200]})
			frappe.log_error(
				title=f"myHR bulk_approve_leave_applications failed: {n}",
				message=frappe.get_traceback(),
			)
	frappe.db.commit()
	return {
		"approved": approved,
		"skipped": skipped,
		"errors": errors,
		"error_log": error_log,
		"total": len(name_list),
	}


@frappe.whitelist()
def get_leave_coverage(employee=None):
	"""Coverage report for HR — leave application stats.

	Without `employee`: returns one row per leave_type with global counts
	(open / approved / rejected / cancelled in current calendar year).
	With `employee`: same shape but filtered to one employee's history.

	HR-only (or the employee themselves for the self-filtered case).
	"""
	user = frappe.session.user
	roles = set(frappe.get_roles())
	is_hr = bool({"HR Manager", "System Manager"} & roles)

	if employee:
		caller_emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
		if not is_hr and caller_emp != employee:
			frappe.throw("You can only view your own leave coverage.", frappe.PermissionError)
	else:
		if not is_hr:
			frappe.throw("Only HR can view global leave coverage.", frappe.PermissionError)

	year_start = f"{frappe.utils.getdate(frappe.utils.today()).year}-01-01"

	where = ["from_date >= %(ys)s"]
	params = {"ys": year_start}
	if employee:
		where.append("employee = %(emp)s")
		params["emp"] = employee

	rows = frappe.db.sql(
		f"""
		SELECT
		    leave_type,
		    SUM(CASE WHEN status='Open'      AND docstatus=0 THEN 1 ELSE 0 END) AS open,
		    SUM(CASE WHEN status='Approved'  AND docstatus=1 THEN 1 ELSE 0 END) AS approved,
		    SUM(CASE WHEN status='Rejected'                  THEN 1 ELSE 0 END) AS rejected,
		    SUM(CASE WHEN docstatus=2                        THEN 1 ELSE 0 END) AS cancelled,
		    SUM(CASE WHEN status='Approved' AND docstatus=1 THEN total_leave_days ELSE 0 END) AS days_approved,
		    COUNT(*) AS total
		FROM `tabLeave Application`
		WHERE {' AND '.join(where)}
		GROUP BY leave_type
		ORDER BY leave_type ASC
		""",
		params,
		as_dict=True,
	)
	return [
		{
			"leave_type": r.leave_type,
			"open": int(r.open or 0),
			"approved": int(r.approved or 0),
			"rejected": int(r.rejected or 0),
			"cancelled": int(r.cancelled or 0),
			"days_approved": float(r.days_approved or 0),
			"total": int(r.total or 0),
		}
		for r in rows
	]


@frappe.whitelist()
def get_checkin_coverage(date=None):
	"""HR-only: who's checked in today (or on `date`).

	Returns one row per Active employee with `{employee, employee_name,
	auto_present, in_time, out_time, status}` where status is one of:
	'Checked In' (has IN, no OUT), 'Checked Out' (has IN + OUT), 'Absent'
	(no IN), 'Auto-Present Pending' (custom_auto_present=1 but cron hasn't
	fired today). Sorted by status (Absent / pending first) then by name.

	Includes auto-present employees so HR can spot cron failures fast (an
	auto-present employee with no IN by 09:30 means the cron likely failed).
	"""
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can view check-in coverage.", frappe.PermissionError)

	target = date or frappe.utils.today()
	rows = frappe.db.sql(
		"""
		SELECT
		    e.name                            AS employee,
		    e.employee_name                   AS employee_name,
		    COALESCE(e.custom_auto_present, 0) AS auto_present,
		    MIN(CASE WHEN c.log_type = 'IN'  THEN c.time END) AS in_time,
		    MAX(CASE WHEN c.log_type = 'OUT' THEN c.time END) AS out_time
		FROM `tabEmployee` e
		LEFT JOIN `tabEmployee Checkin` c
		    ON c.employee = e.name AND DATE(c.time) = %(d)s
		WHERE e.status = 'Active'
		GROUP BY e.name, e.employee_name, e.custom_auto_present
		ORDER BY e.employee_name ASC
		""",
		{"d": target},
		as_dict=True,
	)
	out = []
	for r in rows:
		auto = bool(r.auto_present)
		if r.in_time and r.out_time:
			status = "Checked Out"
		elif r.in_time:
			status = "Checked In"
		elif auto:
			status = "Auto-Present Pending"
		else:
			status = "Absent"
		out.append({
			"employee": r.employee,
			"employee_name": r.employee_name,
			"auto_present": auto,
			"in_time": str(r.in_time or ""),
			"out_time": str(r.out_time or ""),
			"status": status,
		})
	# Sort: Absent + Auto-Present Pending first (HR's attention surface), then alpha.
	priority = {"Absent": 0, "Auto-Present Pending": 1, "Checked In": 2, "Checked Out": 3}
	out.sort(key=lambda x: (priority.get(x["status"], 9), (x["employee_name"] or "").lower()))
	return out


@frappe.whitelist()
def get_attendance_request_coverage():
	"""HR-only: counts of Attendance Requests by docstatus + employee.

	Returns `[{employee, employee_name, draft, submitted, cancelled, total}]`
	for the current calendar year. Helpful for HR to spot stale drafts.
	"""
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can view AR coverage.", frappe.PermissionError)

	year_start = f"{frappe.utils.getdate(frappe.utils.today()).year}-01-01"
	rows = frappe.db.sql(
		"""
		SELECT
		    employee,
		    employee_name,
		    SUM(CASE WHEN docstatus=0 THEN 1 ELSE 0 END) AS draft,
		    SUM(CASE WHEN docstatus=1 THEN 1 ELSE 0 END) AS submitted,
		    SUM(CASE WHEN docstatus=2 THEN 1 ELSE 0 END) AS cancelled,
		    COUNT(*) AS total
		FROM `tabAttendance Request`
		WHERE from_date >= %s
		GROUP BY employee, employee_name
		ORDER BY draft DESC, employee_name ASC
		""",
		year_start,
		as_dict=True,
	)
	return [
		{
			"employee": r.employee,
			"employee_name": r.employee_name,
			"draft": int(r.draft or 0),
			"submitted": int(r.submitted or 0),
			"cancelled": int(r.cancelled or 0),
			"total": int(r.total or 0),
		}
		for r in rows
	]


@frappe.whitelist()
def hr_set_action_centre_verdict(name, verdict, remarks=""):
	"""HR-only convenience endpoint: mark every Pending / Awaiting HR row on
	an Action Centre as Accepted (or Rejected with `remarks`). Closes EAC-11.

	Skips Accepted/Rejected rows (already-decided) and skips rows with no
	file/N-A (those would fail `_guard_accepted_rows_have_data` if marked
	Accepted; explicit per-row review is the right path for Rejected too).

	Returns `{decided: N, skipped: M, ac: ...}`.
	"""
	if verdict not in ("Accepted", "Rejected"):
		frappe.throw(_("Verdict must be 'Accepted' or 'Rejected'."))
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can set verdicts.", frappe.PermissionError)
	if verdict == "Rejected" and not (remarks or "").strip():
		frappe.throw(_("Rejection requires remarks."))

	from myhr.myhr.doctype.employee_action_centre.employee_action_centre import AC_DOCUMENT_ROWS

	doc = frappe.get_doc("Employee Action Centre", name, ignore_cache=True)
	decided = skipped = 0
	for prefix, _label, _mand, has_na, file_suffix in AC_DOCUMENT_ROWS:
		current = doc.get(f"{prefix}_approval_status") or "Pending"
		if current in ("Accepted", "Rejected"):
			skipped += 1
			continue
		file_val = doc.get(f"{prefix}{file_suffix}") or ""
		is_na = bool(doc.get(f"{prefix}_is_na")) if has_na else False
		if verdict == "Accepted" and not file_val and not is_na:
			# Cannot accept an empty row. Skip and let HR review it manually.
			skipped += 1
			continue
		doc.set(f"{prefix}_approval_status", verdict)
		if verdict == "Rejected":
			doc.set(f"{prefix}_remarks", remarks)
		decided += 1
	if decided == 0:
		return {"ac": name, "decided": 0, "skipped": skipped, "note": "Nothing to decide."}

	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ac": name, "decided": decided, "skipped": skipped}


@frappe.whitelist()
def reopen_action_centre(name, reason):
	"""HR-only: un-submit an AC for re-edit. Sets `submitted_for_review=0`
	and clears `submitted_on / submitted_by`. Logs to activity_logs.
	`frappe.flags.allow_unsubmit_ac` lets the controller's lock pass for
	exactly this call. `reason` is required."""
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can reopen.", frappe.PermissionError)
	if not (reason or "").strip():
		frappe.throw(_("Reason is required to reopen an Action Centre."))

	doc = frappe.get_doc("Employee Action Centre", name, ignore_cache=True)
	if not doc.submitted_for_review:
		return {"ac": name, "reopened": False, "note": "Already not submitted."}

	doc.submitted_for_review = 0
	doc.submitted_on = None
	doc.submitted_by = None

	from myhr.myhr.doctype.employee_action_centre.employee_action_centre import log_activity
	log_activity(doc, "Reopened by HR", f"Reason: {reason.strip()[:500]}")

	frappe.flags.allow_unsubmit_ac = True
	try:
		doc.save(ignore_permissions=True)
	finally:
		frappe.flags.allow_unsubmit_ac = False
	frappe.db.commit()
	return {"ac": name, "reopened": True}


@frappe.whitelist()
def get_action_centre_coverage():
	"""Coverage report for HR — for every active employee with an AC, returns
	`{employee, employee_name, status, submitted_on, mandatory_acked, total_mandatory, coverage_pct}`.

	HR-only. Closes EAC-12.
	"""
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can view coverage.", frappe.PermissionError)

	from myhr.myhr.doctype.employee_action_centre.employee_action_centre import AC_DOCUMENT_ROWS
	mandatory_prefixes = [p for p, _l, m, _h, _s in AC_DOCUMENT_ROWS if m]
	total_mandatory = len(mandatory_prefixes)

	rows = frappe.get_all(
		"Employee Action Centre",
		filters={"employee": ("!=", "")},
		fields=["name", "employee", "employee_name", "status", "submitted_on", "submitted_by"]
		       + [f"{p}_approval_status" for p in mandatory_prefixes],
	)
	out = []
	for r in rows:
		acked = sum(1 for p in mandatory_prefixes if (r.get(f"{p}_approval_status") or "Pending") == "Accepted")
		out.append({
			"name": r.name,
			"employee": r.employee,
			"employee_name": r.employee_name,
			"status": r.status,
			"submitted_on": str(r.submitted_on or ""),
			"submitted_by": r.submitted_by,
			"mandatory_acked": acked,
			"total_mandatory": total_mandatory,
			"coverage_pct": round((acked / total_mandatory) * 100, 1) if total_mandatory else 0.0,
		})
	out.sort(key=lambda x: (-x["coverage_pct"], x["employee_name"] or ""))
	return out


@frappe.whitelist()
def get_policy_coverage():
	"""Coverage report for HR — for every active policy, returns
	`{name, policy_name, version, total, acked, pending, coverage_pct}`.

	HR-only (System Manager / HR Manager). Closes E-6.
	"""
	roles = set(frappe.get_roles())
	if not ({"HR Manager", "System Manager"} & roles):
		frappe.throw("Only HR can view coverage.", frappe.PermissionError)

	rows = frappe.db.sql(
		"""
		SELECT
		    hp.name,
		    hp.policy_name,
		    hp.version,
		    hp.mandatory_check_in_block,
		    hp.category,
		    SUM(CASE WHEN pa.policy_version = hp.version AND pa.status = 'Acknowledged' THEN 1 ELSE 0 END) AS acked,
		    SUM(CASE WHEN pa.policy_version = hp.version AND pa.status = 'Pending'      THEN 1 ELSE 0 END) AS pending,
		    SUM(CASE WHEN pa.policy_version = hp.version AND pa.status = 'Withdrawn'    THEN 1 ELSE 0 END) AS withdrawn,
		    SUM(CASE WHEN pa.policy_version = hp.version THEN 1 ELSE 0 END) AS total
		FROM `tabHR Policy` hp
		LEFT JOIN `tabPolicy Acknowledgement` pa ON pa.hr_policy = hp.name
		WHERE hp.is_active = 1
		GROUP BY hp.name, hp.policy_name, hp.version, hp.mandatory_check_in_block, hp.category
		ORDER BY hp.policy_name ASC
		""",
		as_dict=True,
	)
	out = []
	for r in rows:
		total = int(r.total or 0)
		acked = int(r.acked or 0)
		out.append({
			"name": r.name,
			"policy_name": r.policy_name,
			"version": r.version,
			"category": r.category,
			"mandatory_check_in_block": int(r.mandatory_check_in_block or 0),
			"total": total,
			"acked": acked,
			"pending": int(r.pending or 0),
			"withdrawn": int(r.withdrawn or 0),
			"coverage_pct": round((acked / total) * 100, 1) if total else 0.0,
		})
	return out

@frappe.whitelist()
def get_employee_action_centre():
	"""Returns the current employee's action centre document"""
	user = frappe.session.user
	emp_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not emp_id:
		return {"error": "no_employee", "message": "No employee record linked to this user"}
	
	ac_name = frappe.db.get_value("Employee Action Centre", {"employee": emp_id}, "name")
	if not ac_name:
		return {"error": "no_action_centre", "message": "No Action Centre found for this employee"}
	
	doc = frappe.get_doc("Employee Action Centre", ac_name)
	
	# Build structured response for the frontend.
	# Each identity document row also carries the matching number/name text
	# field (Aadhar number, PAN number, Degree name) so the PWA can show one
	# unified card with both fields side-by-side.
	documents = []
	doc_fields = [
		("aadhar", _("Aadhar"), "aadhar_number", _("Aadhar Number"), "12-digit"),
		("pan", _("PAN"), "pan_number", _("PAN Number"), "ABCDE1234F"),
		("education", _("Highest Educational Qualification Certificate"), "education_name", _("Degree / Qualification Name"), ""),
	]
	for prefix, label, num_field, num_label, num_hint in doc_fields:
		documents.append({
			"key": prefix,
			"label": label,
			"mandatory": 1,
			"file": getattr(doc, f"{prefix}_upload", None),
			"is_na": getattr(doc, f"{prefix}_is_na", 0),
			"status": getattr(doc, f"{prefix}_approval_status", "Pending"),
			"remarks": getattr(doc, f"{prefix}_remarks", ""),
			"number_field": num_field,
			"number_label": num_label,
			"number_value": getattr(doc, num_field, "") or "",
			"number_hint": num_hint,
		})

	# Declarations tab — Tax Regime, Medical Insurance opt-in, Bank Statement
	# (6 Months). Tax Regime + Medical Insurance use a Select-based "data_field"
	# (employee picks a value). Bank Statement is a file upload. The PWA
	# renders these together under the Declarations section.
	declarations = []
	declarations.append({
		"key": "tax_regime",
		"label": _("Tax Regime"),
		"kind": "select",
		"data_field": "tax_regime",
		"value": getattr(doc, "tax_regime", "") or "",
		"options": ["New Tax Regime", "Old Tax Regime"],
		"mandatory": 1,
		"is_na": int(getattr(doc, "tax_regime_is_na", 0) or 0),
		"status": getattr(doc, "tax_regime_approval_status", "Pending"),
		"remarks": getattr(doc, "tax_regime_remarks", ""),
		"description": _("Choose your income-tax regime for the financial year. HR will review your selection."),
	})
	# Resolve the active opt-out declaration template (HR-managed). Surfaced
	# read-only to employees who pick "Opt Out" so they can download the blank
	# PDF, sign it, and upload via `medical_insurance_signed_optout`.
	from myhr.myhr.doctype.medical_insurance_opt_out_declaration.medical_insurance_opt_out_declaration import (
		get_active_declaration,
	)
	active_optout = get_active_declaration() or {}

	declarations.append({
		"key": "medical_insurance",
		"label": _("Medical Insurance"),
		"kind": "select",
		"data_field": "medical_insurance_opt_in",
		"value": getattr(doc, "medical_insurance_opt_in", "") or "",
		"options": ["Opt In", "Opt Out"],
		"mandatory": 1,
		"is_na": int(getattr(doc, "medical_insurance_is_na", 0) or 0),
		"status": getattr(doc, "medical_insurance_approval_status", "Pending"),
		"remarks": getattr(doc, "medical_insurance_remarks", ""),
		"linked_policy": getattr(doc, "medical_insurance_policy", "") or "",
		"linked_policy_url": (
			f"/app/medical-insurance/{getattr(doc, 'medical_insurance_policy', '')}"
			if getattr(doc, "medical_insurance_policy", "") else ""
		),
		# Opt-out flow: blank template (read-only) + employee's signed upload.
		"optout_template_name": active_optout.get("declaration_name") or "",
		"optout_template_url": active_optout.get("template_document") or "",
		"signed_optout_file": getattr(doc, "medical_insurance_signed_optout", "") or "",
		"signed_optout_field": "medical_insurance_signed_optout",
		"description": _("Opt In to the company medical insurance, or Opt Out by downloading, signing, and uploading the declaration."),
	})
	declarations.append({
		"key": "bank_statement_6m",
		"label": _("Bank Statement (Last 6 Months)"),
		"kind": "file",
		"data_field": "bank_statement_6m_upload",
		"file": getattr(doc, "bank_statement_6m_upload", None),
		"mandatory": 1,
		"is_na": int(getattr(doc, "bank_statement_6m_is_na", 0) or 0),
		"status": getattr(doc, "bank_statement_6m_approval_status", "Pending"),
		"remarks": getattr(doc, "bank_statement_6m_remarks", ""),
		"description": _("Upload the last 6 months of your bank statement (PDF preferred)."),
	})

	employers = []
	for i in range(1, 6):
		name_val = getattr(doc, f"employer_{i}_name", None)
		is_na = getattr(doc, f"employer_{i}_is_na", 0)
		row = {
			"key": f"employer_{i}",
			"label": f"Employer {i}",
			"name": name_val or "",
			"from_date": str(getattr(doc, f"employer_{i}_from", "") or ""),
			"till_date": str(getattr(doc, f"employer_{i}_till", "") or ""),
			"file": getattr(doc, f"employer_{i}_doc", None),
			"is_na": is_na,
			"status": getattr(doc, f"employer_{i}_approval_status", "Pending"),
			"remarks": getattr(doc, f"employer_{i}_remarks", ""),
		}

		if i == 1:
			employer_docs = []
			for prefix, label, mandatory, show_in_pwa in _get_employer_1_doc_fields():
				if not show_in_pwa:
					continue  # filtered from the PWA — HR has hidden this payslip
				employer_docs.append(
					{
						"key": prefix,
						"label": label,
						"mandatory": mandatory,
						"file": getattr(doc, f"{prefix}_doc", None),
						"status": getattr(doc, f"{prefix}_approval_status", "Pending"),
						"remarks": getattr(doc, f"{prefix}_remarks", ""),
					}
				)

			row["documents"] = employer_docs
			row["status"] = _derive_employer_1_status(doc)
			row["file"] = ""
			row["is_na"] = int(getattr(doc, "employer_1_is_na", 0) or 0)
			row["remarks"] = ""

		employers.append(row)
	
	# Personal Details bucket — basic info, family, emergency contact.
	# Pure data capture (no per-row HR approval). Each entry exposes
	# (key, label, value, kind, options [for select], mandatory, hint).
	personal_details = [
		{"key": "personal_full_name", "label": _("Full Name"), "value": getattr(doc, "personal_full_name", "") or "", "kind": "text", "mandatory": 1, "hint": _("Alphabets only")},
		{"key": "personal_dob", "label": _("Date of Birth"), "value": str(getattr(doc, "personal_dob", "") or ""), "kind": "date", "mandatory": 1, "hint": _("Cannot be a future date")},
		{"key": "personal_age", "label": _("Age"), "value": getattr(doc, "personal_age", "") or "", "kind": "readonly", "mandatory": 0, "hint": _("Auto-computed from Date of Birth")},
		{"key": "personal_date_of_joining", "label": _("Date of Joining"), "value": getattr(doc, "personal_date_of_joining", "") or "", "kind": "readonly", "mandatory": 0, "hint": _("From your Employee record")},
		{"key": "personal_gender", "label": _("Gender"), "value": getattr(doc, "personal_gender", "") or "", "kind": "select", "options": ["Male", "Female", "Other"], "mandatory": 1},
		{"key": "personal_marital_status", "label": _("Marital Status"), "value": getattr(doc, "personal_marital_status", "") or "", "kind": "select", "options": ["Single", "Married", "Other"], "mandatory": 1},
		{"key": "personal_mobile", "label": _("Mobile Number"), "value": getattr(doc, "personal_mobile", "") or "", "kind": "tel", "mandatory": 1, "hint": _("10-digit number")},
		{"key": "personal_blood_group", "label": _("Blood Group"), "value": getattr(doc, "personal_blood_group", "") or "", "kind": "select", "options": ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"], "mandatory": 0},
		{"key": "personal_father_name", "label": _("Father's Name"), "value": getattr(doc, "personal_father_name", "") or "", "kind": "text", "mandatory": 1, "hint": _("Alphabets only")},
		{"key": "personal_mother_name", "label": _("Mother's Name"), "value": getattr(doc, "personal_mother_name", "") or "", "kind": "text", "mandatory": 1, "hint": _("Alphabets only")},
		{"key": "personal_emergency_contact_name", "label": _("Emergency Contact Name"), "value": getattr(doc, "personal_emergency_contact_name", "") or "", "kind": "text", "mandatory": 1, "hint": _("Alphabets only")},
		{"key": "personal_emergency_contact_number", "label": _("Emergency Contact Number"), "value": getattr(doc, "personal_emergency_contact_number", "") or "", "kind": "tel", "mandatory": 1, "hint": _("10-digit number")},
		{"key": "personal_emergency_relation", "label": _("Emergency Contact Relation"), "value": getattr(doc, "personal_emergency_relation", "") or "", "kind": "text", "mandatory": 0},
		{"key": "personal_preferred_contact_email", "label": _("Preferred Contact Email"), "value": getattr(doc, "personal_preferred_contact_email", "") or "", "kind": "select", "options": ["Company Email", "Personal Email", "User ID"], "mandatory": 0},
		{"key": "personal_father_dob", "label": _("Father's DOB"), "value": str(getattr(doc, "personal_father_dob", "") or ""), "kind": "date", "mandatory": 0},
		{"key": "personal_mother_dob", "label": _("Mother's DOB"), "value": str(getattr(doc, "personal_mother_dob", "") or ""), "kind": "date", "mandatory": 0},
		{"key": "personal_spouse_name", "label": _("Spouse Name"), "value": getattr(doc, "personal_spouse_name", "") or "", "kind": "text", "mandatory": 0},
		{"key": "personal_spouse_gender", "label": _("Spouse Gender"), "value": getattr(doc, "personal_spouse_gender", "") or "", "kind": "select", "options": ["Male", "Female", "Other"], "mandatory": 0},
		{"key": "personal_spouse_dob", "label": _("Spouse DOB"), "value": str(getattr(doc, "personal_spouse_dob", "") or ""), "kind": "date", "mandatory": 0},
		{"key": "personal_child_1_name", "label": _("Child 1 - Name"), "value": getattr(doc, "personal_child_1_name", "") or "", "kind": "text", "mandatory": 0},
		{"key": "personal_child_1_gender", "label": _("Child 1 - Gender"), "value": getattr(doc, "personal_child_1_gender", "") or "", "kind": "select", "options": ["Male", "Female", "Other"], "mandatory": 0},
		{"key": "personal_child_1_dob", "label": _("Child 1 - DOB"), "value": str(getattr(doc, "personal_child_1_dob", "") or ""), "kind": "date", "mandatory": 0},
		{"key": "personal_child_2_name", "label": _("Child 2 - Name"), "value": getattr(doc, "personal_child_2_name", "") or "", "kind": "text", "mandatory": 0},
		{"key": "personal_child_2_gender", "label": _("Child 2 - Gender"), "value": getattr(doc, "personal_child_2_gender", "") or "", "kind": "select", "options": ["Male", "Female", "Other"], "mandatory": 0},
		{"key": "personal_child_2_dob", "label": _("Child 2 - DOB"), "value": str(getattr(doc, "personal_child_2_dob", "") or ""), "kind": "date", "mandatory": 0},
		{"key": "passport_number", "label": _("Passport Number"), "value": getattr(doc, "passport_number", "") or "", "kind": "text", "mandatory": 0},
		{"key": "passport_valid_upto", "label": _("Passport Valid Up To"), "value": str(getattr(doc, "passport_valid_upto", "") or ""), "kind": "date", "mandatory": 0},
		{"key": "passport_date_of_issue", "label": _("Passport Date of Issue"), "value": str(getattr(doc, "passport_date_of_issue", "") or ""), "kind": "date", "mandatory": 0},
		{"key": "passport_place_of_issue", "label": _("Passport Place of Issue"), "value": getattr(doc, "passport_place_of_issue", "") or "", "kind": "text", "mandatory": 0},
	]

	# Statutory forms — signed statutory forms uploaded under Statutory & Bank.
	# Same shape as the file-kind declaration row (Bank Statement 6m) so the
	# PWA reuses the upload / N-A / HR-status card.
	from myhr.myhr.doctype.employee_action_centre.employee_action_centre import (
		AC_STATUTORY_FORM_PREFIXES,
	)
	statutory_forms = [
		{
			"key": prefix,
			"label": _(label),
			"kind": "file",
			"data_field": f"{prefix}{file_suffix}",
			"file": getattr(doc, f"{prefix}{file_suffix}", None),
			"mandatory": 1 if mandatory else 0,
			"is_na": int(getattr(doc, f"{prefix}_is_na", 0) or 0),
			"status": getattr(doc, f"{prefix}_approval_status", "Pending") or "Pending",
			"remarks": getattr(doc, f"{prefix}_remarks", "") or "",
		}
		for prefix, label, mandatory, _has_na, file_suffix in AC_DOCUMENT_ROWS
		if prefix in AC_STATUTORY_FORM_PREFIXES
	]

	# Statutory & Bank bucket — PF / UAN + bank account info.
	statutory_bank = [
		{"key": "statutory_pf_number", "label": _("PF Number"), "value": getattr(doc, "statutory_pf_number", "") or "", "kind": "text", "mandatory": 0, "hint": _("Optional")},
		{"key": "statutory_uan_number", "label": _("UAN Number"), "value": getattr(doc, "statutory_uan_number", "") or "", "kind": "tel", "mandatory": 0, "hint": _("12-digit UAN")},
		{"key": "bank_account_holder_name", "label": _("Name as per Bank Records"), "value": getattr(doc, "bank_account_holder_name", "") or "", "kind": "text", "mandatory": 0},
		{"key": "bank_name", "label": _("Bank Name"), "value": getattr(doc, "bank_name", "") or "", "kind": "text", "mandatory": 1},
		{"key": "bank_account_number", "label": _("Bank Account Number"), "value": getattr(doc, "bank_account_number", "") or "", "kind": "text", "mandatory": 1},
		{"key": "bank_ifsc_code", "label": _("IFSC Code"), "value": getattr(doc, "bank_ifsc_code", "") or "", "kind": "text", "mandatory": 1},
	]

	return {
		"name": doc.name,
		"employee": doc.employee,
		"status": doc.status,
		"submitted_for_review": int(doc.submitted_for_review or 0),
		"submitted_on": str(doc.submitted_on or ""),
		"custom_last_saved_at": (
			frappe.utils.get_datetime_str(doc.custom_last_saved_at)
			if doc.custom_last_saved_at else None
		),
		"personal_details": personal_details,
		"documents": documents,
		"declarations": declarations,
		"statutory_bank": statutory_bank,
		"statutory_forms": statutory_forms,
		"employers": employers,
	}

@frappe.whitelist()
def update_action_centre_field(name, fieldname, value):
	"""Update a single field on Employee Action Centre.

	Status transitions and data invariants are enforced by
	`EmployeeActionCentre.validate()` on save. An audit row is appended to
	`activity_logs` describing the change. Non-HR callers can only mutate
	whitelisted employee-owned fields (file/N-A/employer metadata).
	"""
	if not _ac_belongs_to_session_user(name):
		frappe.throw("You can only update your own Action Centre.", frappe.PermissionError)
	_enforce_employee_field_whitelist([fieldname])
	doc = frappe.get_doc("Employee Action Centre", name, ignore_cache=True)
	doc.set(fieldname, value)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"status": "success"}


@frappe.whitelist()
def bulk_update_action_centre_fields(name, patch):
	"""Apply many field updates atomically in one save.

	`patch` is a JSON object mapping fieldname → value. Cuts the 3-call dance
	for employer detail saves (and similar) down to a single round-trip and
	a single `validate()` run. Non-HR callers can only mutate whitelisted
	fields.
	"""
	if not _ac_belongs_to_session_user(name):
		frappe.throw("You can only update your own Action Centre.", frappe.PermissionError)
	patch_dict = frappe.parse_json(patch) or {}
	_enforce_employee_field_whitelist(list(patch_dict.keys()))
	doc = frappe.get_doc("Employee Action Centre", name, ignore_cache=True)
	for k, v in patch_dict.items():
		doc.set(k, v)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"status": "success"}


@frappe.whitelist()
def reupload_document(name, prefix, file_url):
	"""Re-upload a previously rejected document.

	Sets the new file, forces the row back to Awaiting HR, and logs the prior
	status/remarks into the activity log. Master status is recomputed by
	`EmployeeActionCentre.validate()` on save — including dropping
	"Action Required" once no rows remain Rejected.
	"""
	if not _ac_belongs_to_session_user(name):
		frappe.throw("You can only update your own Action Centre.", frappe.PermissionError)
	_enforce_valid_ac_prefix(prefix)
	doc = frappe.get_doc("Employee Action Centre", name, ignore_cache=True)
	file_field = f"{prefix}_upload" if not prefix.startswith("employer_") else f"{prefix}_doc"
	doc.set(file_field, file_url)
	doc.set(f"{prefix}_approval_status", "Awaiting HR")
	doc.set(f"{prefix}_remarks", "")
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"status": "success"}


@frappe.whitelist()
def submit_action_centre(name):
	"""Mark the AC as submitted for HR review.

	Allowed only when the master status is 'Ready to Submit' (every mandatory
	row has a file or is N/A, no Rejected rows). Sets `submitted_for_review=1`
	and `submitted_on=now`. The save triggers `_notify_hr_on_completion`,
	which fires the in-PWA notification to all HR Manager / System Manager
	users when status flips to 'To be Reviewed'.
	"""
	if not _ac_belongs_to_session_user(name):
		frappe.throw("You can only submit your own Action Centre.", frappe.PermissionError)
	doc = frappe.get_doc("Employee Action Centre", name, ignore_cache=True)
	if doc.submitted_for_review:
		frappe.throw(_("This Action Centre has already been submitted for review."))
	if doc.status != "Ready to Submit":
		frappe.throw(
			_("All required documents must be uploaded (or marked Not Applicable) before you can submit.")
		)
	doc.submitted_for_review = 1
	doc.submitted_on = frappe.utils.now_datetime()
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"status": "success", "submitted_on": str(doc.submitted_on)}


@frappe.whitelist()
def reset_action_centre_field(name, fieldname, is_mandatory=0):
	"""Wipe file/N-A/status/remarks for one document or employer card.

	Master status is recomputed by `EmployeeActionCentre.validate()` on save.
	"""
	if not _ac_belongs_to_session_user(name):
		frappe.throw("You can only update your own Action Centre.", frappe.PermissionError)
	prefix = fieldname.replace("_doc", "").replace("_upload", "").replace("_is_na", "")
	_enforce_valid_ac_prefix(prefix)
	doc = frappe.get_doc("Employee Action Centre", name, ignore_cache=True)
	file_field = f"{prefix}_doc" if prefix.startswith("employer_") else f"{prefix}_upload"

	doc.set(file_field, "")
	if doc.meta.has_field(f"{prefix}_is_na"):
		doc.set(f"{prefix}_is_na", 0)
	doc.set(f"{prefix}_approval_status", "Pending")
	doc.set(f"{prefix}_remarks", "")
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"status": "success"}


@frappe.whitelist()
def validate_optional_leave_for_application(employee, leave_type, from_date, to_date):
	"""
	PWA: validate optional leave dates against Employee Holiday List + Optional/Fixed.
	Returns { valid, skipped?, message? } without throwing so the UI can show inline errors.
	"""
	if not leave_type or not from_date or not to_date:
		return {"valid": True, "skipped": True}
	if not frappe.db.get_value("Leave Type", leave_type, "is_optional_leave"):
		return {"valid": True, "skipped": True}


	try:
		validate_optional_leave_dates(employee, from_date, to_date)
	except frappe.ValidationError as e:
		return {"valid": False, "message": str(e)}
	return {"valid": True}


@frappe.whitelist()
def get_optional_leave_types():
	"""Return the set of Leave Type names whose `is_optional_leave` flag is true.

	The PWA uses this to disable the half-day toggle when an optional leave type
	is selected (full-day-only rule).
	"""
	return frappe.get_all(
		"Leave Type",
		filters={"is_optional_leave": 1},
		pluck="name",
	)


@frappe.whitelist()
def get_leave_calendar_data(employee, from_date, to_date):
	"""Holidays + existing leave applications in a single round-trip.

	Powers the New Leave Application calendar so dates can be tinted by their
	state (holiday / optional / pending / approved) without three separate
	fetches. The window is bounded so we don't ship a year of rows for a single
	month-grid view.

	Returns:
	  {
	    "holidays": [{"date", "type": "fixed|optional|weekly_off", "description"}],
	    "leave_applications": [{"from_date", "to_date", "status", "leave_type", "name"}]
	  }
	"""
	from hrms.hr.utils import get_holiday_list_for_employee

	if not (employee and from_date and to_date):
		return {"holidays": [], "leave_applications": []}

	holidays_out = []
	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
	if holiday_list:
		rows = frappe.get_all(
			"Holiday",
			filters={
				"parent": holiday_list,
				"holiday_date": ["between", [from_date, to_date]],
			},
			fields=["holiday_date", "description", "weekly_off", "custom_holiday_type"],
			order_by="holiday_date asc",
			limit_page_length=0,
		)
		for r in rows:
			if r.weekly_off:
				htype = "weekly_off"
			elif (r.custom_holiday_type or "").lower() == "optional":
				htype = "optional"
			else:
				htype = "fixed"
			holidays_out.append(
				{
					"date": str(r.holiday_date),
					"type": htype,
					# Holiday.description is a Long Text field rendered via Quill in
					# Desk; values stored include the Quill wrapper markup
					# (<div class="ql-editor read-mode"><p>...</p></div>). The PWA
					# renders {{ description }} via Vue's mustache (escapes HTML),
					# so the raw markup ends up shown as literal text. Strip
					# server-side so the API contract is "description = plain text"
					# for all consumers (Holidays.vue preview + HolidayList.vue full list).
					"description": frappe.utils.strip_html_tags(r.description or "").strip(),
				}
			)

	la_rows = frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee,
			"docstatus": ["<", 2],
			"status": ["in", ["Open", "Approved"]],
			"from_date": ["<=", to_date],
			"to_date": [">=", from_date],
		},
		fields=["name", "from_date", "to_date", "status", "leave_type"],
		order_by="from_date asc",
		limit_page_length=0,
	)
	leave_apps_out = [
		{
			"name": r.name,
			"from_date": str(r.from_date),
			"to_date": str(r.to_date),
			"status": r.status,
			"leave_type": r.leave_type,
		}
		for r in la_rows
	]

	return {"holidays": holidays_out, "leave_applications": leave_apps_out}


# ---------------------------------------------------------------------------
# Override of `hrms.api.get_leave_applications`
# Wired via `override_whitelisted_methods` in hooks.py — keeps the URL stable
# for the PWA's `teamLeaves` resource while extending visibility to HR Managers.
# ---------------------------------------------------------------------------
_HR_APPROVAL_ROLES = {"HR Manager", "System Manager"}


def _caller_is_hr_manager() -> bool:
	return bool(_HR_APPROVAL_ROLES & set(frappe.get_roles()))


@frappe.whitelist()
def get_leave_applications(employee, approver_id=None, for_approval=False, limit=None):
	"""Single-stage Team Requests query.

	HR Manager / System Manager → sees ALL open, unsubmitted leave applications
	from other employees (the role itself authorises approval).
	Everyone else → standard HRMS behaviour (filtered by `leave_approver`).
	"""
	from hrms.api import get_leave_applications as hrms_impl

	if for_approval and _caller_is_hr_manager():
		filters = {
			"docstatus": 0,
			"status": "Open",
			"employee": ("!=", employee),
		}
		fields = [
			"name", "employee", "employee_name", "leave_type",
			"from_date", "to_date", "total_leave_days", "status",
			"leave_approver", "posting_date", "description",
		]
		return frappe.get_all(
			"Leave Application",
			filters=filters,
			fields=fields,
			order_by="posting_date desc, modified desc",
			limit_page_length=int(limit) if limit else 0,
		)

	return hrms_impl(
		employee=employee,
		approver_id=approver_id,
		for_approval=for_approval,
		limit=limit,
	)


@frappe.whitelist()
def get_attendance_requests(employee, for_approval=False, limit=None):
	"""Single-stage Team Requests query for Attendance Request.

	HR Manager / System Manager → sees every draft (docstatus=0) attendance
	request from other employees.
	Anyone else → sees only drafts where they are the applicant's
	`Employee.leave_approver` (we reuse the leave approver field as the manager
	pointer; Attendance Request has no per-employee approver field of its own).
	"""
	from hrms.api import get_attendance_requests as hrms_impl

	if not for_approval:
		return hrms_impl(employee=employee, for_approval=False, limit=limit)

	user = frappe.session.user
	if _caller_is_hr_manager():
		return frappe.get_all(
			"Attendance Request",
			filters={"docstatus": 0, "employee": ("!=", employee)},
			fields=[
				"name", "reason", "employee", "employee_name",
				"from_date", "to_date", "include_holidays", "shift",
				"docstatus", "creation",
			],
			order_by="creation desc",
			limit_page_length=int(limit) if limit else 0,
		)

	# Manager view: only drafts whose applicant lists me as their leave_approver.
	team_employees = frappe.get_all(
		"Employee",
		filters={"leave_approver": user},
		pluck="name",
	)
	if not team_employees:
		return []

	return frappe.get_all(
		"Attendance Request",
		filters={
			"docstatus": 0,
			"employee": ("in", team_employees),
		},
		fields=[
			"name", "reason", "employee", "employee_name",
			"from_date", "to_date", "include_holidays", "shift",
			"docstatus", "creation",
		],
		order_by="creation desc",
		limit_page_length=int(limit) if limit else 0,
	)


@frappe.whitelist()
def get_expense_claims(employee, approver_id=None, for_approval=False, limit=None):
	"""Single-stage Team Requests query for Expense Claim.

	HR Manager / System Manager → sees ALL pending (docstatus=0,
	approval_status=Draft) expense claims from other employees. Authorisation
	to actually approve them is gated separately by
	`gate_expense_claim_approval` reading the HR Settings toggles, so this
	override only widens VISIBILITY, not approval rights.

	Anyone else → standard HRMS behaviour (filtered by `expense_approver`).

	Field shape mirrors `hrms.api.get_expense_claims` exactly so the PWA's
	team-requests resource keeps decoding the response without changes.
	"""
	from hrms.api import get_expense_claims as hrms_impl, get_workflow_state_field

	if for_approval and _caller_is_hr_manager():
		filters = {
			"docstatus": 0,
			"approval_status": "Draft",
			"employee": ("!=", employee),
		}
		fields = [
			"`tabExpense Claim`.name",
			"`tabExpense Claim`.posting_date",
			"`tabExpense Claim`.employee",
			"`tabExpense Claim`.employee_name",
			"`tabExpense Claim`.currency",
			"`tabExpense Claim`.approval_status",
			"`tabExpense Claim`.status",
			"`tabExpense Claim`.expense_approver",
			"`tabExpense Claim`.total_claimed_amount",
			"`tabExpense Claim`.company",
			"`tabExpense Claim`.creation",
			"`tabExpense Claim Detail`.expense_type",
			{"COUNT": "`tabExpense Claim Detail`.expense_type", "as": "total_expenses"},
		]

		workflow_state_field = get_workflow_state_field("Expense Claim")
		if workflow_state_field:
			fields.append(workflow_state_field)

		claims = frappe.get_list(
			"Expense Claim",
			fields=fields,
			filters=filters,
			order_by="`tabExpense Claim`.posting_date desc",
			group_by="`tabExpense Claim`.name",
			limit=limit,
		)

		if workflow_state_field:
			for claim in claims:
				claim["workflow_state_field"] = workflow_state_field

		return claims

	return hrms_impl(
		employee=employee,
		approver_id=approver_id,
		for_approval=for_approval,
		limit=limit,
	)


@frappe.whitelist()
def can_approve_expense_claim(name: str) -> dict:
	"""Return whether the caller may approve/reject the named Expense Claim.

	Mirrors `myhr.approval_gate.gate_expense_claim_approval` exactly so the PWA
	can hide the Approve/Reject buttons before the user taps them — same source
	of truth, no UI-vs-server skew. Returns `{can_approve: bool, reason: str}`.

	Reasons surface in the UI (a small inline notice replaces the buttons), so
	keep them user-facing — no internal role names.
	"""
	from myhr.approval_gate import (
		ACCOUNTS_MANAGER_ROLE,
		_ec_settings,
		_is_hr_approval_role,
		_is_self_expense_claim,
	)

	doc = frappe.get_doc("Expense Claim", name)
	user = frappe.session.user
	if user == "Administrator":
		return {"can_approve": True, "reason": ""}

	settings = _ec_settings()

	if settings["prevent_self"] and _is_self_expense_claim(doc, user):
		return {
			"can_approve": False,
			"reason": (
				"Company policy prevents you from approving your own Expense Claim. "
				"Your Expense Approver, HR, or an Accounts Manager must approve it."
			),
		}

	if settings["hr_manager_ok"] and _is_hr_approval_role():
		return {"can_approve": True, "reason": ""}

	if (
		settings["designated_ok"]
		and doc.expense_approver
		and doc.expense_approver == user
	):
		return {"can_approve": True, "reason": ""}

	if (
		settings["accounts_manager_ok"]
		and ACCOUNTS_MANAGER_ROLE in frappe.get_roles(user)
	):
		return {"can_approve": True, "reason": ""}

	return {
		"can_approve": False,
		"reason": "You are not authorised to approve this Expense Claim.",
	}


@frappe.whitelist()
def clear_all_notifications():
	"""Bulk-delete every PWA Notification belonging to the current user.

	Powers the "Clear all" button in the PWA Notifications view. Uses
	`frappe.db.delete` so a user wiping a long list doesn't loop through
	delete_doc one row at a time. Scoped to `to_user = session.user` —
	users cannot clear anyone else's notifications.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw("You must be logged in to clear notifications.", frappe.PermissionError)
	frappe.db.delete("PWA Notification", {"to_user": user})
	# Frappe's standard Notification Log feeds the bell icon for desk-style
	# alerts (policy assignment etc.). Clear those too so the bell empties.
	frappe.db.delete("Notification Log", {"for_user": user})
	frappe.db.commit()
	return {"cleared": True}


@frappe.whitelist()
def mark_notification_read(notification=None):
	"""Set read=1 on a single PWA Notification owned by the current user.

	Powers the per-row tick button. Goes through `frappe.db.set_value` with
	server-side ownership check because the Employee role only has read perm
	on PWA Notification — `frappe.client.set_value` from the frontend
	otherwise throws PermissionError. Param is `notification` (not `name`)
	to avoid collisions with Frappe's request-level `name` handling.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw("You must be logged in.", frappe.PermissionError)
	if not notification:
		frappe.throw("Missing notification id.")
	owner = frappe.db.get_value("PWA Notification", notification, "to_user")
	if owner is None:
		return {"updated": False, "reason": "not_found"}
	if owner != user:
		frappe.throw("You can only update your own notifications.", frappe.PermissionError)
	frappe.db.set_value("PWA Notification", notification, "read", 1, update_modified=False)
	frappe.db.commit()
	return {"updated": True, "notification": notification}


@frappe.whitelist()
def dismiss_notification(notification=None):
	"""Delete a single PWA Notification owned by the current user.

	Powers the per-row cross button in the PWA Notifications view. Scoped to
	`to_user = session.user` — users cannot dismiss anyone else's row.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw("You must be logged in.", frappe.PermissionError)
	if not notification:
		frappe.throw("Missing notification id.")
	owner = frappe.db.get_value("PWA Notification", notification, "to_user")
	if owner is None:
		return {"dismissed": False, "reason": "not_found"}
	if owner != user:
		frappe.throw("You can only dismiss your own notifications.", frappe.PermissionError)
	frappe.db.delete("PWA Notification", {"name": notification})
	frappe.db.commit()
	return {"dismissed": True, "notification": notification}


# ---------------------------------------------------------------------------
# Employee-side cancel for own pending Leave / Attendance Request
# ---------------------------------------------------------------------------
# Owner-only. Allowed strictly while the request is still pending review
# (status=Open, docstatus=0). Once an approver has touched it, cancellation
# falls back to HR via Desk — that's the rule the user signed off on.

def _cancel_pending_request(doctype: str, name: str, reason: str) -> dict:
	"""Shared body for LA + AR cancel. Sets status=Cancelled with the supplied
	reason, locks the audit field, and pings the named approver via a PWA
	Notification so the row visibly drops out of their Team Requests queue."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw("You must be logged in.", frappe.PermissionError)

	reason = (reason or "").strip()
	# LA + AR require a reason (the dialog enforces this on the client too) so
	# the approver gets a meaningful audit trail. EC owner-cancel is a "rescind
	# my own draft" gesture — no approver action has been taken, the row is
	# being deleted, and there's no durable audit row for the reason to land
	# on. So we accept an empty reason on EC and surface a default in the
	# approver Notification.
	if not reason and doctype != "Expense Claim":
		frappe.throw("A cancellation reason is required.")
	if doctype == "Expense Claim" and not reason:
		reason = "Cancelled by employee."

	if not name:
		frappe.throw("Missing request id.")

	doc = frappe.get_doc(doctype, name)

	# Owner gate — Frappe stamps `owner` on insert; that's the employee who
	# filed the request via the PWA. We don't fall back to employee_user_id
	# because some HR scripts create LAs on behalf of an employee, and those
	# should not be cancellable by the employee through this surface.
	if doc.owner != user:
		frappe.throw(
			"You can only cancel a request you filed yourself.",
			frappe.PermissionError,
		)

	# docstatus gate — only un-touched pending rows. Stock HRMS's Attendance
	# Request doesn't carry a `status` field (its lifecycle is docstatus-only:
	# draft → submitted), so we only enforce the LA-style status check on LA.
	if doc.docstatus != 0:
		frappe.throw(
			"This request has already been finalised. Ask HR to cancel it from Desk."
		)
	if doctype == "Leave Application":
		if (doc.status or "").strip() != "Open":
			frappe.throw(
				f"This request is in status '{doc.status}' and can no longer be cancelled by the employee. "
				"Ask HR to cancel it from Desk."
			)
		doc.status = "Cancelled"
	elif doctype == "Expense Claim":
		# Approver-touched gate: once approval_status leaves Draft, the approver
		# has already acted (Approved / Rejected). Employee can no longer rescind.
		if (doc.approval_status or "").strip() != "Draft":
			frappe.throw(
				f"This claim is in approval status '{doc.approval_status}' and "
				"can no longer be cancelled by the employee. Ask HR to cancel "
				"it from Desk."
			)

	# LA: Open → Cancelled status flip, audit reason persists on the row, doc
	# stays at docstatus=0 (no balance was ever deducted, nothing to undo).
	# AR + EC: no pre-submit Cancelled status, so we delete the draft. The
	# reason still surfaces to the approver via the Notification Log entry
	# below.
	if doctype == "Leave Application":
		doc.custom_cancellation_reason = reason
		doc.save(ignore_permissions=True)
	else:
		doc.delete(ignore_permissions=True)
	frappe.db.commit()

	# Notify the named approver so their Team Requests pile reflects the
	# cancellation in real time. Best-effort — never block the cancel itself.
	try:
		approver_user = None
		if doctype == "Leave Application":
			approver_user = doc.get("leave_approver")
		elif doctype == "Attendance Request":
			emp = doc.get("employee")
			if emp:
				approver_user = frappe.db.get_value("Employee", emp, "leave_approver")
		elif doctype == "Expense Claim":
			# Claim carries `expense_approver` directly (Link to User), unlike
			# AR which has to look up Employee.leave_approver.
			approver_user = doc.get("expense_approver")
		if approver_user and approver_user != user:
			employee_name = doc.get("employee_name") or doc.get("employee") or ""
			frappe.get_doc({
				"doctype": "PWA Notification",
				"to_user": approver_user,
				"from_user": user,
				"message": (
					f"<b>{employee_name}</b> cancelled their {doctype} <b>{doc.name}</b>. "
					f"Reason: {reason}"
				),
				"reference_document_type": doctype,
				"reference_document_name": doc.name,
				"read": 0,
			}).insert(ignore_permissions=True)
			frappe.db.commit()
	except Exception:
		frappe.log_error(
			title=f"myHR cancel notify approver failed ({doctype})",
			message=frappe.get_traceback(),
		)

	return {"cancelled": True, "name": doc.name, "status": doc.status}


@frappe.whitelist()
def cancel_leave_application(name=None, reason=None):
	"""Owner-only cancel for an Open Leave Application. See
	`_cancel_pending_request` for the gates."""
	return _cancel_pending_request("Leave Application", name, reason)


@frappe.whitelist()
def cancel_attendance_request(name=None, reason=None):
	"""Owner-only cancel for an Open Attendance Request. See
	`_cancel_pending_request` for the gates."""
	return _cancel_pending_request("Attendance Request", name, reason)


@frappe.whitelist()
def cancel_expense_claim(name=None, reason=None):
	"""Owner-only cancel for a draft Expense Claim. Allowed strictly while
	`docstatus=0` AND `approval_status='Draft'` — once an approver has
	flipped approval_status to Approved/Rejected the claim is out of the
	owner's reach. The draft row is deleted; the named approver gets a
	PWA Notification carrying the cancellation reason. See
	`_cancel_pending_request` for the shared gates."""
	return _cancel_pending_request("Expense Claim", name, reason)


@frappe.whitelist()
def reject_attendance_request(name=None, reason=None):
	"""Approver-side reject for a pending Attendance Request.

	Behaviourally identical to a cancel (the row is deleted — stock HRMS has no
	Cancelled state for AR and the rejection_reason field would be unreachable
	post-delete anyway). Capturing the reason on a PWA Notification to the
	original filer is what makes this distinct from the silent employee-side
	cancel.

	Authorisation reuses `gate_attendance_request_submit` so only users who
	would be allowed to *approve* this AR can also reject it. That lines up with
	the HR Settings AR approver toggles (HR / leave approver) and avoids a
	second policy surface to keep in sync.
	"""
	from myhr.approval_gate import gate_attendance_request_submit

	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw("You must be logged in.", frappe.PermissionError)

	reason = (reason or "").strip()
	if not reason:
		frappe.throw("A rejection reason is required.")

	if not name:
		frappe.throw("Missing request id.")

	doc = frappe.get_doc("Attendance Request", name)

	if doc.docstatus != 0:
		frappe.throw("This request has already been finalised.")

	# Reuse the approve-side gate. It throws PermissionError with a human
	# message if the caller can't approve this AR; we want the same set of
	# users to be able to reject.
	gate_attendance_request_submit(doc)

	# Stamp the reason on the in-memory doc so the notification body has a
	# consistent record. Field is read_only on the form but free to set
	# server-side. The row is about to be deleted, so this is purely for the
	# notification copy below.
	doc.custom_rejection_reason = reason

	filer = doc.owner  # employee who filed via the PWA
	employee_name = doc.get("employee_name") or doc.get("employee") or ""
	doc_name = doc.name

	doc.delete(ignore_permissions=True)
	frappe.db.commit()

	# Notify the original filer so they see "Rejected — <reason>" in their
	# notifications. Best-effort — never block the reject itself.
	try:
		if filer and filer != user:
			frappe.get_doc({
				"doctype": "PWA Notification",
				"to_user": filer,
				"from_user": user,
				"message": (
					f"Your Attendance Request <b>{doc_name}</b> was rejected. "
					f"Reason: {reason}"
				),
				"reference_document_type": "Attendance Request",
				"reference_document_name": doc_name,
				"read": 0,
			}).insert(ignore_permissions=True)
			frappe.db.commit()
	except Exception:
		frappe.log_error(
			title="myHR reject_attendance_request notify filer failed",
			message=frappe.get_traceback(),
		)


# ---------------------------------------------------------------------------
# Action Centre — Save Draft
# ---------------------------------------------------------------------------

# Field allow-list for save_action_centre_draft. Anything not editable here
# is silently dropped from the payload. Approval / remarks fields are HR-only;
# submitted_*/status are workflow-controlled; system fields are never client-
# writable.
_AC_RESTRICTED_SUFFIXES = ("_approval_status", "_remarks")
_AC_RESTRICTED_EXACT = {
	"submitted_for_review",
	"submitted_on",
	"submitted_by",
	"status",
	"custom_last_saved_at",
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"parent",
	"parenttype",
	"parentfield",
	"idx",
	"employee",
	"employee_name",
}

# Fieldtypes where MariaDB rejects empty string and requires NULL.
_AC_NULLABLE_EMPTY_FIELDTYPES = {
	"Date", "Datetime", "Time",
	"Int", "Float", "Currency", "Percent",
	"Link",
}


def _coerce_value_for_db(meta, fieldname, value):
	"""Convert empty string to None for fieldtypes MariaDB can't store as ''."""
	if value != "":
		return value
	df = meta.get_field(fieldname)
	if df and df.fieldtype in _AC_NULLABLE_EMPTY_FIELDTYPES:
		return None
	return value


def _is_field_editable_by_employee(fieldname):
	if fieldname in _AC_RESTRICTED_EXACT:
		return False
	for suffix in _AC_RESTRICTED_SUFFIXES:
		if fieldname.endswith(suffix):
			return False
	return True


@frappe.whitelist()
def save_action_centre_draft(name, payload):
	"""Save partial Employee Action Centre state without triggering review.

	Bypasses the doctype's validate hook by using `frappe.db.set_value` per
	field. Only employee-editable fields (per allow-list) are honored.

	Args:
		name: Employee Action Centre document name.
		payload: dict (or JSON-encoded string) of {fieldname: value}.

	Returns:
		{"ok": True, "saved_at": <ISO datetime>, "applied_fields": [...]}.
	"""
	if not frappe.db.exists("Employee Action Centre", name):
		frappe.throw(_("Action Centre not found"), frappe.DoesNotExistError)

	employee = frappe.db.get_value("Employee Action Centre", name, "employee")
	owner_user = frappe.db.get_value("Employee", employee, "user_id") if employee else None
	caller = frappe.session.user
	if caller != owner_user and caller != "Administrator":
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	eac_state = frappe.db.get_value(
		"Employee Action Centre",
		name,
		["submitted_for_review", "status"],
		as_dict=True,
	)
	if eac_state.submitted_for_review or eac_state.status == "Accepted":
		frappe.throw(_("Cannot save draft — Action Centre is locked"))

	if isinstance(payload, str):
		try:
			payload = json.loads(payload)
		except (ValueError, TypeError):
			frappe.throw(_("Invalid payload"))

	if not isinstance(payload, dict):
		frappe.throw(_("Payload must be an object"))

	meta = frappe.get_meta("Employee Action Centre")
	applied = []
	for fieldname, value in payload.items():
		if not _is_field_editable_by_employee(fieldname):
			continue
		if not meta.get_field(fieldname):
			# Field doesn't exist on the doctype — skip silently. Client may have
			# leftover ghost entries; server quietly ignores rather than crashing.
			continue
		coerced = _coerce_value_for_db(meta, fieldname, value)
		frappe.db.set_value(
			"Employee Action Centre",
			name,
			fieldname,
			coerced,
			update_modified=False,
		)
		applied.append(fieldname)

	saved_at = frappe.utils.now_datetime()
	frappe.db.set_value(
		"Employee Action Centre",
		name,
		{"custom_last_saved_at": saved_at, "modified": saved_at, "modified_by": caller},
		update_modified=False,
	)

	frappe.db.commit()

	return {
		"ok": True,
		"saved_at": frappe.utils.get_datetime_str(saved_at),
		"applied_fields": applied,
	}
