"""Approval-authority gate for Leave Application, Attendance Request, and Expense Claim.

Rule (matches the user's RBAC model):

  - Leave Application:
      - HR Manager / System Manager → unconditional approve.
      - Anyone else (incl. HR User) → may approve ONLY if their session user
        matches the named approver field on the doctype.
      - The employee themselves cannot approve their own LA.
  - Attendance Request:
      - Configurable per install via three Check toggles on `HR Settings`:
        `custom_ar_approver_hr_manager` (default 1),
        `custom_ar_approver_leave_approver` (default 1),
        `custom_ar_allow_self_submit` (default 0).
      - At least one must remain enabled — `gate_hr_settings_save` throws
        otherwise to prevent total lockout.
      - Administrator always passes (system paths).
  - Expense Claim:
      - Configurable per install via three Check toggles on `HR Settings`:
        `custom_ec_approver_hr_manager` (default 1),
        `custom_ec_approver_designated` (default 1),
        `custom_ec_approver_accounts_manager` (default 0).
      - Stock `prevent_self_expense_approval` is respected: when ticked,
        even an authorised user cannot approve their own claim.
      - At least one must remain enabled — `gate_hr_settings_save` throws
        otherwise to prevent total lockout.
      - Administrator always passes (system paths).

Trigger surfaces:

  - Leave Application: `validate` hook detects the status transition to
    'Approved' and gates it. The myhr override auto-submits on Approved,
    so this gate fires before the submit fans out the leave allocation.
  - Attendance Request: `before_submit` hook gates the docstatus 0 → 1
    transition (which creates the Attendance row).
  - Expense Claim: `validate` hook detects the approval_status transition
    to 'Approved' or 'Rejected' and gates it. Submit on Expense Claim is
    blocked while approval_status is 'Draft' (stock HRMS rule), so
    catching it on validate fires before any GL impact.
  - HR Settings: `validate` hook enforces the at-least-one-toggle invariant
    for both AR and EC toggle groups.
"""

import frappe


HR_APPROVAL_ROLES = {"HR Manager", "System Manager"}

# Defaults applied when an HR Settings field is missing or NULL — matches the
# `default` attr declared in `MYHR_CUSTOM_FIELDS`. Hardcoding the defaults here
# means the gate keeps working on a fresh migrate even if the seed patch hasn't
# run yet (Custom Field defaults only apply when a new doc is created, not when
# a column is added to an existing singleton row).
_AR_DEFAULTS = {
	"custom_ar_approver_hr_manager": 1,
	"custom_ar_approver_leave_approver": 1,
	"custom_ar_allow_self_submit": 0,
}

_EC_DEFAULTS = {
	"custom_ec_approver_hr_manager": 1,
	"custom_ec_approver_designated": 1,
	"custom_ec_approver_accounts_manager": 0,
}


def _is_hr_approval_role() -> bool:
	return bool(HR_APPROVAL_ROLES & set(frappe.get_roles(frappe.session.user)))


def _ar_settings():
	"""Return (hr_manager_ok, leave_approver_ok, allow_self_submit) from HR Settings.

	Falls back to the declared defaults if the field is missing or NULL on the
	row — see `_AR_DEFAULTS` for why.
	"""
	s = frappe.get_cached_doc("HR Settings")

	def _get(key):
		val = s.get(key)
		return _AR_DEFAULTS[key] if val is None else val

	return (
		bool(_get("custom_ar_approver_hr_manager")),
		bool(_get("custom_ar_approver_leave_approver")),
		bool(_get("custom_ar_allow_self_submit")),
	)


def _ec_settings():
	"""Return EC approver toggles + the stock self-approval block from HR Settings.

	Falls back to declared defaults when the custom-field column hasn't
	materialised yet on the singleton row.

	Returns dict so the gate / error-message builder can reference fields by
	name (three-tuple gets unwieldy once `prevent_self` joins the party).
	"""
	s = frappe.get_cached_doc("HR Settings")

	def _get(key, default):
		val = s.get(key)
		return default if val is None else val

	return {
		"hr_manager_ok": bool(_get("custom_ec_approver_hr_manager", _EC_DEFAULTS["custom_ec_approver_hr_manager"])),
		"designated_ok": bool(_get("custom_ec_approver_designated", _EC_DEFAULTS["custom_ec_approver_designated"])),
		"accounts_manager_ok": bool(_get("custom_ec_approver_accounts_manager", _EC_DEFAULTS["custom_ec_approver_accounts_manager"])),
		# Stock HR Settings field — kept in this dict so the gate can read all
		# EC-related policy state from one place.
		"prevent_self": bool(s.get("prevent_self_expense_approval") or 0),
	}


# ---------------------------------------------------------------------------
# Leave Application — gate on status='Approved' transition
# ---------------------------------------------------------------------------

def gate_leave_application_approval(doc, method=None):
	"""Block status='Approved' transitions unless the caller is authorised.

	Authorised:
	  - HR Manager / System Manager — blanket approve.
	  - The user listed in `Leave Application.leave_approver`.
	  - System paths (frappe.session.user == 'Administrator') keep working.
	"""
	if doc.status != "Approved":
		return
	# Only fire when status is *transitioning* to Approved, not on every save
	# of an already-Approved row.
	previous = doc.get_doc_before_save()
	if previous and previous.status == "Approved":
		return

	user = frappe.session.user
	if user == "Administrator":
		return
	if _is_hr_approval_role():
		return
	if doc.leave_approver and doc.leave_approver == user:
		return

	# Block self-approval
	if doc.employee:
		emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")
		if emp_user == user:
			frappe.throw(
				"You cannot approve your own Leave Application. "
				"It must be approved by your Leave Approver or by HR.",
				frappe.PermissionError,
			)

	frappe.throw(
		"Only HR or the named Leave Approver "
		f"({doc.leave_approver or 'none set'}) can approve this Leave Application.",
		frappe.PermissionError,
	)


# ---------------------------------------------------------------------------
# Attendance Request — gate on submit
# ---------------------------------------------------------------------------

def gate_attendance_request_submit(doc, method=None):
	"""Block AR submit (docstatus 0 → 1) unless the caller is authorised.

	Authorisation is read from `HR Settings`. Each install can independently
	enable/disable the three approval paths:

	  - HR Manager / System Manager (`custom_ar_approver_hr_manager`)
	  - The employee's named Leave Approver (`custom_ar_approver_leave_approver`)
	  - The employee themselves (`custom_ar_allow_self_submit`)

	Administrator always passes (system paths). The save-time guard on HR
	Settings (`gate_hr_settings_save`) prevents all three toggles from being
	disabled at once.
	"""
	user = frappe.session.user
	if user == "Administrator":
		return

	hr_manager_ok, leave_approver_ok, allow_self_submit = _ar_settings()

	if hr_manager_ok and _is_hr_approval_role():
		return

	approver = None
	if leave_approver_ok and doc.employee:
		approver = frappe.db.get_value("Employee", doc.employee, "leave_approver")
		if approver and approver == user:
			return

	emp_user = None
	if doc.employee:
		emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")

	if allow_self_submit and emp_user and emp_user == user:
		return

	# Build a human-readable list of who CAN approve, based on the toggles.
	# Wording is end-user-facing — collapse "HR Manager / System Manager" to
	# just "HR" so the PWA error doesn't surface internal role names.
	allowed = []
	if hr_manager_ok:
		allowed.append("HR")
	if leave_approver_ok:
		allowed.append(f"the employee's Leave Approver ({approver or 'none set'})")
	if allow_self_submit:
		allowed.append("the employee themselves")
	allowed_str = ", ".join(allowed) if allowed else "(no approver type is enabled — fix HR Settings)"

	# Distinguish the self-submit blocker for a clearer error.
	if emp_user and emp_user == user:
		frappe.throw(
			"You cannot submit your own Attendance Request — your company policy "
			f"requires it to be submitted by: {allowed_str}.",
			frappe.PermissionError,
		)

	frappe.throw(
		f"Only {allowed_str} can submit this Attendance Request.",
		frappe.PermissionError,
	)


# ---------------------------------------------------------------------------
# Expense Claim — gate on approval_status transition to Approved / Rejected
# ---------------------------------------------------------------------------

ACCOUNTS_MANAGER_ROLE = "Accounts Manager"


def _is_self_expense_claim(doc, user) -> bool:
	"""True iff `user` is the User linked to the claim's Employee."""
	if not doc.employee:
		return False
	emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	return bool(emp_user) and emp_user == user


def _ec_allowed_label(settings, doc) -> str:
	"""Human-readable list of who CAN approve, based on enabled toggles.

	Surfaces in PWA / Desk error messages — names are end-user-facing so we
	collapse internal role names ('HR Manager / System Manager' → 'HR') and
	point at the named approver explicitly when the designated path is on.
	"""
	allowed = []
	if settings["hr_manager_ok"]:
		allowed.append("HR")
	if settings["designated_ok"]:
		allowed.append(
			f"the named Expense Approver ({doc.expense_approver or 'none set'})"
		)
	if settings["accounts_manager_ok"]:
		allowed.append("an Accounts Manager")
	return (
		", ".join(allowed)
		if allowed
		else "(no approver type is enabled — fix HR Settings → Expenses)"
	)


def gate_expense_claim_approval(doc, method=None):
	"""Block approval_status transitions to Approved/Rejected unless authorised.

	Authorisation paths (each independently toggleable in HR Settings →
	Expenses → Expense Claim Approval Authority):

	  - HR Manager / System Manager (`custom_ec_approver_hr_manager`)
	  - The user listed on the claim's `expense_approver` field
	    (`custom_ec_approver_designated`)
	  - Accounts Manager role (`custom_ec_approver_accounts_manager`)

	Stock `prevent_self_expense_approval` is honoured: when ticked, a user
	cannot approve / reject a claim raised by their own Employee record,
	regardless of which authorisation path they qualify under. Administrator
	always passes (system paths). The save-time guard on HR Settings
	(`gate_hr_settings_save`) prevents all three toggles from being disabled
	at once.
	"""
	# Only fire on transitions INTO Approved / Rejected. Plain Draft saves,
	# already-finalised rows, and on_submit re-runs are no-ops.
	if doc.approval_status not in ("Approved", "Rejected"):
		return
	previous = doc.get_doc_before_save()
	if previous and previous.approval_status == doc.approval_status:
		return

	user = frappe.session.user
	if user == "Administrator":
		return

	settings = _ec_settings()

	# Self-approval check first — it overrides every authorisation path,
	# so block early with a tailored error rather than letting the user
	# discover they don't qualify and *then* finding out they're also
	# blocked from self-approving.
	if settings["prevent_self"] and _is_self_expense_claim(doc, user):
		frappe.throw(
			"You cannot approve your own Expense Claim — your company policy "
			"prevents self-approval. Ask your Expense Approver, HR, or an "
			"Accounts Manager to approve it.",
			frappe.PermissionError,
		)

	if settings["hr_manager_ok"] and _is_hr_approval_role():
		return

	if (
		settings["designated_ok"]
		and doc.expense_approver
		and doc.expense_approver == user
	):
		return

	if (
		settings["accounts_manager_ok"]
		and ACCOUNTS_MANAGER_ROLE in frappe.get_roles(user)
	):
		return

	allowed_str = _ec_allowed_label(settings, doc)
	frappe.throw(
		f"Only {allowed_str} can approve this Expense Claim.",
		frappe.PermissionError,
	)


# ---------------------------------------------------------------------------
# HR Settings — lockout guard for the AR + EC approver toggles
# ---------------------------------------------------------------------------

def gate_hr_settings_save(doc, method=None):
	"""Refuse saving HR Settings if all approver toggles in either group are off.

	Two invariants enforced together (one per toggle group):

	  - AR: at least one of `custom_ar_approver_hr_manager`,
	    `custom_ar_approver_leave_approver`, `custom_ar_allow_self_submit`
	    must be ticked — otherwise nobody (except Administrator) can submit
	    Attendance Requests.
	  - EC: at least one of `custom_ec_approver_hr_manager`,
	    `custom_ec_approver_designated`, `custom_ec_approver_accounts_manager`
	    must be ticked — otherwise nobody can approve Expense Claims.

	Throwing on save keeps the model honest: we'd rather the admin see a
	clear error here than discover the lockout the next time someone tries
	to file an expense.
	"""
	ar_hr_manager = bool(doc.get("custom_ar_approver_hr_manager"))
	ar_leave_approver = bool(doc.get("custom_ar_approver_leave_approver"))
	ar_self_submit = bool(doc.get("custom_ar_allow_self_submit"))
	if not (ar_hr_manager or ar_leave_approver or ar_self_submit):
		frappe.throw(
			"At least one Attendance Request approval path must remain enabled — "
			"tick HR Manager, Leave Approver, or Employee Self-Submit. "
			"Disabling all three would block every user (except Administrator) "
			"from submitting Attendance Requests.",
			title="Invalid AR approval policy",
		)

	ec_hr_manager = bool(doc.get("custom_ec_approver_hr_manager"))
	ec_designated = bool(doc.get("custom_ec_approver_designated"))
	ec_accounts_manager = bool(doc.get("custom_ec_approver_accounts_manager"))
	if not (ec_hr_manager or ec_designated or ec_accounts_manager):
		frappe.throw(
			"At least one Expense Claim approval path must remain enabled — "
			"tick HR Manager, named Expense Approver, or Accounts Manager. "
			"Disabling all three would leave no one able to approve "
			"Expense Claims.",
			title="Invalid Expense Claim approval policy",
		)
