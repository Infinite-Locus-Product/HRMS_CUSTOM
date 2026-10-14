"""Employee Separation doc_events — wired in hooks.py.

Stage A of the resignation flow. Stock `Employee Separation` is an offboarding
CHECKLIST (it inherits EmployeeBoardingController) and carries no resignation
intent, so myHR adds the capture fields in setup.py:MYHR_CUSTOM_FIELDS and the
rules below.

Reporting Manager and Function Head / L2 need no code here — they fill via
`fetch_from` off the `employee` link.

Rules:
- Official End Date and Notice Period Shortfall are RECOMPUTED on every save
  and never read from input. `read_only` is a UI flag only: the REST API, Data
  Import and `bench console` all write straight past it, and the shortfall may
  drive a salary deduction.
- The notice-period shortfall is measured against the APPROVED relieving date
  once one exists, falling back to the requested date before approval. See
  `_effective_relieving_date`.
- Requested Relieving Date cannot be before today or before Date of Joining —
  checked only when the value is set or changed, so updating an old document's
  activity checklist does not re-litigate a date that was valid when filed.
- Detailed Reason is capped at 500 chars. `Small Text` maps to a `text` column
  and the `length` attr only applies to `Data`, so this has to be a check.
- One active Employee Separation per employee.
- On final approval the four downstream records are created as drafts, so the
  clearances and the settlement are waiting for their owners rather than having
  to be raised by hand. See `create_downstream_records`.
- On final approval the approved relieving date is pushed onto the Employee
  record. HRMS refuses to create an Exit Interview until `Employee.relieving_date`
  is set, so without this the exit interview — and therefore the HR clearance and
  the relieving letter — can never happen.
- Stage B approval fields are conditionally mandatory: Reason for Rejection / Hold
  when the Decision is Reject or Hold, and the three approver fields when it is
  Approve. They cannot be `reqd=1` on the field itself — the employee submits the
  document before any approver sees it, so a hard reqd would block their submit.
- Buy-out Amount is mandatory when Buy-out Notice Period = Yes. `mandatory_depends_on`
  is evaluated CLIENT-SIDE ONLY — frappe has no server-side equivalent (grep the
  framework: it only ever appears in DocField/Custom Field schemas). Since this
  field feeds a recovery amount, the rule is enforced here too.

KNOWN GAP: the spec defines "active" as non-Rejected / non-Cancelled, but stock
`boarding_status` is only Pending / In Process / Completed — there is no
Rejected state, because there is no approval workflow yet. Until the approval
stages are built, "active" means docstatus < 2 (draft or submitted). When a
Workflow lands, change ACTIVE_DOCSTATUSES / _find_active_separation only.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, nowdate

MAX_DETAILED_REASON_CHARS = 500

APPROVE = "Approve"
REJECT = "Reject"
HOLD = "Hold"
BLOCKING_DECISIONS = (REJECT, HOLD)

# Filled by the approver, not the employee, so they cannot be reqd=1 on the
# field — that would block the employee's own submit. They are required only
# once a decision is actually recorded. See _validate_approval.
APPROVAL_REQUIRED_ON_APPROVE = (
	("custom_approved_relieving_date", "Approved Relieving Date"),
	("custom_notice_period_waiver", "Notice Period Waiver"),
	("custom_retention_discussion_held", "Retention Discussion Held?"),
)

# Draft + Submitted. Cancelled (2) is not active, so an amended document is fine.
ACTIVE_DOCSTATUSES = (0, 1)


def validate(doc, method=None):
	_validate_single_active_separation(doc)
	# Before the two below: both anchor on resignation_letter_date.
	_stamp_resignation_letter_date(doc)
	_validate_detailed_reason(doc)
	_validate_requested_relieving_date(doc)
	_validate_buyout(doc)
	compute_notice_period(doc)
	_apply_approval_defaults(doc)
	_validate_approval(doc)


# ---------------------------------------------------------------------------
# Notice period
# ---------------------------------------------------------------------------
def _stamp_resignation_letter_date(doc):
	"""Record when the resignation was filed, on the Employee record.

	`Employee Separation.resignation_letter_date` is read-only with
	`fetch_from: employee.resignation_letter_date` and no `fetch_if_empty`, so a
	value written on the separation is overwritten from the Employee on every
	save. The Employee record is the field's real home.

	Nothing else sets it. Left alone, a resignation filed from the PWA leaves it
	blank forever -- and the relieving letter opens with "with reference to your
	resignation dated ...", while the notice-period rules below anchor on it and
	silently fall back to today.

	Overwritten rather than filled-only-if-empty: a new separation is a new
	resignation, so any date from a previous cycle is stale. Only one separation
	can be active at a time (`_validate_single_active_separation`).

	Written directly for the same reason as `_set_employee_relieving_date` -- a
	full Employee save re-runs validations that older master-data rows fail.
	"""
	if not doc.employee or not doc.is_new():
		return

	filed_on = nowdate()
	frappe.db.set_value(
		"Employee", doc.employee, "resignation_letter_date", filed_on, update_modified=False
	)
	# Also on the document in hand, so this save prints and validates correctly
	# whichever side of the fetch it lands on.
	doc.resignation_letter_date = filed_on


def compute_notice_period(doc):
	"""Overwrite Official End Date and Notice Period Shortfall from source data.

	Anchor is the employee's Resignation Letter Date (fetched read-only from the
	Employee record). It is routinely blank, so fall back to today — the day the
	separation is being raised.
	"""
	anchor = getdate(doc.resignation_letter_date or nowdate())
	official_end = add_days(anchor, _get_notice_period_days(doc.employee))
	doc.custom_official_end_date = official_end

	leaving_on = _effective_relieving_date(doc)
	if not leaving_on:
		doc.custom_notice_period_shortfall = 0
		return

	# Floored at 0: serving MORE than the notice period is not a negative
	# shortfall, and a negative would flip a buy-out deduction into a payment.
	shortfall = date_diff(official_end, getdate(leaving_on))
	doc.custom_notice_period_shortfall = max(0, cint(shortfall))


def _effective_relieving_date(doc):
	"""The date the shortfall is measured against: approved if there is one.

	Once an approver has moved the date, THAT is the day the employee actually
	leaves, so it is the only honest basis for "how much notice was missed".
	Measuring against what they originally requested overstates the shortfall by
	however far the approver pushed the date out — harmless while the number is
	only displayed, but it is intended to drive a recovery from the final
	settlement, and there it would take money the employee does not owe.

	Falls back to the requested date because before approval that is all there
	is, and the employee should still see an indicative figure when they file.
	"""
	return doc.get("custom_approved_relieving_date") or doc.get("custom_requested_relieving_date")


def _get_notice_period_days(employee):
	"""myHR's custom_notice_period_days is the source of truth.

	`employee_master_data.py` mirrors it into the native `notice_number_of_days`
	on save, so the custom field is read first and the native one is only a
	fallback for rows that predate the mirror.
	"""
	if not employee:
		return 0

	custom, native = frappe.db.get_value(
		"Employee", employee, ["custom_notice_period_days", "notice_number_of_days"]
	) or (None, None)

	return cint(custom if custom is not None else native)


# ---------------------------------------------------------------------------
# Validations
# ---------------------------------------------------------------------------
def _validate_requested_relieving_date(doc):
	if not doc.custom_requested_relieving_date:
		return  # reqd=1 already blocks an empty value

	# Only judge the date when it is actually set or changed. Without this,
	# editing a months-old separation's activity checklist would throw because
	# its (correct) relieving date is now in the past.
	if not doc.has_value_changed("custom_requested_relieving_date"):
		return

	requested = getdate(doc.custom_requested_relieving_date)

	if requested < getdate(nowdate()):
		frappe.throw(
			_("Requested Relieving Date {0} is in the past. It cannot be earlier than today.").format(
				frappe.bold(frappe.format(requested, {"fieldtype": "Date"}))
			),
			title=_("Invalid Relieving Date"),
		)

	date_of_joining = (
		frappe.db.get_value("Employee", doc.employee, "date_of_joining") if doc.employee else None
	)
	if date_of_joining and requested < getdate(date_of_joining):
		frappe.throw(
			_("Requested Relieving Date {0} is before the employee's Date of Joining {1}.").format(
				frappe.bold(frappe.format(requested, {"fieldtype": "Date"})),
				frappe.bold(frappe.format(getdate(date_of_joining), {"fieldtype": "Date"})),
			),
			title=_("Invalid Relieving Date"),
		)


def _validate_detailed_reason(doc):
	length = len(doc.custom_detailed_reason or "")
	if length > MAX_DETAILED_REASON_CHARS:
		frappe.throw(
			_("Detailed Reason is {0} characters. The limit is {1}.").format(
				length, MAX_DETAILED_REASON_CHARS
			),
			title=_("Detailed Reason Too Long"),
		)


def _validate_buyout(doc):
	"""Buy-out Amount is required when buying out. Mirrors mandatory_depends_on.

	The declarative flag only runs in the browser, so an API or import write
	would otherwise land a buy-out with no amount against it.
	"""
	if doc.custom_buyout_notice_period != "Yes":
		return

	if not flt(doc.custom_buyout_amount):
		frappe.throw(
			_("Buy-out Amount is required when Buy-out Notice Period is set to Yes."),
			title=_("Buy-out Amount Missing"),
			exc=frappe.MandatoryError,
		)


# ---------------------------------------------------------------------------
# Approval (Stage B)
# ---------------------------------------------------------------------------
def _apply_approval_defaults(doc):
	"""Approved Relieving Date starts at whatever the employee asked for."""
	if doc.custom_decision and not doc.custom_approved_relieving_date:
		doc.custom_approved_relieving_date = doc.custom_requested_relieving_date


def _validate_approval(doc):
	"""Enforce the conditional-mandatory rules once a decision is recorded.

	Nothing here fires while the document is still the employee's to fill in —
	`custom_decision` is empty until an approver acts.
	"""
	if not doc.custom_decision:
		return

	if doc.custom_decision in BLOCKING_DECISIONS and not (doc.custom_rejection_hold_reason or "").strip():
		frappe.throw(
			_("Reason for Rejection / Hold is required when the Decision is {0}.").format(
				frappe.bold(_(doc.custom_decision))
			),
			title=_("Reason Required"),
			exc=frappe.MandatoryError,
		)

	if doc.custom_decision != APPROVE:
		return

	missing = [label for fieldname, label in APPROVAL_REQUIRED_ON_APPROVE if not doc.get(fieldname)]
	if missing:
		frappe.throw(
			_("The approver must fill {0} before approving.").format(
				frappe.bold(", ".join(_(label) for label in missing))
			),
			title=_("Approval Incomplete"),
			exc=frappe.MandatoryError,
		)

	if getdate(doc.custom_approved_relieving_date) < getdate(doc.resignation_letter_date or nowdate()):
		frappe.throw(
			_("Approved Relieving Date cannot be earlier than the resignation date."),
			title=_("Invalid Approved Relieving Date"),
		)


def _validate_single_active_separation(doc):
	existing = _find_active_separation(doc.employee, exclude=doc.name)
	if not existing:
		return

	frappe.throw(
		_("{0} already has an active Employee Separation ({1}). Cancel it before raising another.").format(
			frappe.bold(doc.employee_name or doc.employee), frappe.bold(existing)
		),
		title=_("Separation Already In Progress"),
	)


def _find_active_separation(employee, exclude=None):
	"""Name of an existing non-cancelled separation for `employee`, if any."""
	if not employee:
		return None

	filters = {"employee": employee, "docstatus": ["in", ACTIVE_DOCSTATUSES]}
	if exclude:
		filters["name"] = ["!=", exclude]

	names = frappe.get_all("Employee Separation", filters=filters, pluck="name", limit=1)
	return names[0] if names else None


# ---------------------------------------------------------------------------
# Client helper
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_relieving_date_default(employee):
	"""Official end date for `employee`, for the form to prefill on employee select.

	Server-side on purpose: `custom_notice_period_days` sits at permlevel 1, so
	a plain `frappe.db.get_value` from the client would be filtered out for
	non-HR users. The db layer here reads it without that filtering, and the
	only thing returned is a single derived date.
	"""
	frappe.has_permission("Employee Separation", "create", throw=True)

	if not employee:
		return {}

	resignation_letter_date = frappe.db.get_value("Employee", employee, "resignation_letter_date")
	anchor = getdate(resignation_letter_date or nowdate())
	notice_period_days = _get_notice_period_days(employee)

	return {
		"official_end_date": add_days(anchor, notice_period_days),
		"notice_period_days": notice_period_days,
	}



# ---------------------------------------------------------------------------
# Relieving date -> Employee
# ---------------------------------------------------------------------------
def on_submit(doc, method=None):
	"""Final approval submits the separation; mirror its date onto the Employee.

	HRMS's Exit Interview throws "Please set the relieving date for employee ..."
	unless `Employee.relieving_date` is filled, so stage 8 is unreachable without
	this. The workflow's Approved state is the one that submits, which makes
	on_submit the moment the date becomes final.
	"""
	# Order matters: the settlement refuses to exist without a relieving date on
	# the Employee, and that is what the line above writes.
	_set_employee_relieving_date(doc, _approved_relieving_date(doc))
	create_downstream_records(doc)


def on_cancel(doc, method=None):
	"""Undo it, so a cancelled resignation does not leave a leaver behind.

	Only clears a date this document set: if HR has since entered a different
	one by hand, theirs wins.
	"""
	approved = _approved_relieving_date(doc)
	current = frappe.db.get_value("Employee", doc.employee, "relieving_date")
	if approved and current and getdate(current) == getdate(approved):
		_set_employee_relieving_date(doc, None)


def _approved_relieving_date(doc):
	"""What the approver signed off, falling back to what was requested."""
	return doc.get("custom_approved_relieving_date") or doc.get("custom_requested_relieving_date")


def _set_employee_relieving_date(doc, value):
	"""Write the single field directly, deliberately not through doc.save().

	A full Employee save re-runs every validation on that record, including
	myHR's mandatory `employee_number` / `ctc` / `payroll_cost_center`. Plenty of
	older Employee rows are missing those, and a separation approval must not
	fail because of unrelated gaps in someone's master data. This writes one
	derived date and nothing else.
	"""
	if not doc.employee:
		return

	current = frappe.db.get_value("Employee", doc.employee, "relieving_date")
	if (current or None) == (value or None):
		return

	frappe.db.set_value("Employee", doc.employee, "relieving_date", value, update_modified=False)
	frappe.logger().info(
		f"myHR: Employee {doc.employee} relieving_date set to {value} by separation {doc.name}."
	)


# ---------------------------------------------------------------------------
# Downstream drafts
# ---------------------------------------------------------------------------
# Raised as drafts the moment L2 approves, so each owner finds the record
# waiting instead of having to create it. Every creator is skip-if-exists, so a
# cancel-and-amend cycle does not produce duplicates.
DOWNSTREAM_LABELS = {
	"Separation Manager Clearance": "Manager Clearance",
	"Separation IT Clearance": "IT Clearance",
	"Separation HR Clearance": "HR Clearance",
	"Full and Final Statement": "Full & Final Statement",
}


def create_downstream_records(doc, method=None):
	"""Create the four follow-on drafts, without letting any of them break approval.

	Each is attempted independently. A failure is logged and surfaced as a
	warning rather than raised: a resignation that has cleared two levels of
	approval must not be rolled back because, say, a company has no default
	payroll account. The approval is the important thing; a missing draft can be
	raised by hand.

	Failures are deliberately NOT silent — they land in the Error Log and the
	approver sees a message — because a stub nobody notices is missing is worse
	than one that was never promised.
	"""
	created, failed = [], []

	for doctype, creator in _downstream_creators():
		try:
			name = creator(doc)
			if name:
				created.append(name)
		except Exception:
			failed.append(DOWNSTREAM_LABELS.get(doctype, doctype))
			frappe.log_error(
				title=f"myHR: could not raise {doctype} for {doc.name}",
				message=frappe.get_traceback(),
			)

	if failed:
		frappe.msgprint(
			_("The resignation is approved, but {0} could not be started automatically. Raise {1} by hand — the reason is in the Error Log.").format(
				frappe.bold(", ".join(failed)),
				_("it") if len(failed) == 1 else _("them"),
			),
			title=_("Some Clearances Not Created"),
			indicator="orange",
		)

	return created


def _downstream_creators():
	"""(doctype, callable) pairs, resolved at call time.

	Looked up through the module rather than held as direct references so that
	patching a creator in a test still goes through this loop — and so the
	doctype label survives, which a mocked function would not carry.
	"""
	import sys

	module = sys.modules[__name__]
	return (
		("Separation Manager Clearance", module._create_manager_clearance),
		("Separation IT Clearance", module._create_it_clearance),
		("Separation HR Clearance", module._create_hr_clearance),
		("Full and Final Statement", module._create_settlement),
	)


def _existing(doctype, separation):
	"""A live record already linked to this separation, if any."""
	return frappe.db.get_value(doctype, {"employee_separation": separation, "docstatus": ["<", 2]}, "name")


def _insert(doc):
	"""Insert a system-raised stub.

	`ignore_permissions` because the person approving is an ordinary employee
	acting as someone's manager — they have no rights over IT or HR clearances,
	and should not need any to trigger one. `ignore_mandatory` because these are
	empty shells: the fields their owners must fill in are, by definition, not
	filled in yet.
	"""
	doc.insert(ignore_permissions=True, ignore_mandatory=True)
	return doc.name


def _create_manager_clearance(separation):
	doctype = "Separation Manager Clearance"
	if _existing(doctype, separation.name):
		return None

	doc = frappe.new_doc(doctype)
	doc.employee_separation = separation.name
	# Set explicitly rather than relying on fetch_from: the permission hook for
	# this doctype matches on these two fields, and fetched values are not
	# populated yet when permissions are checked on insert.
	doc.employee = separation.employee
	doc.reporting_manager = separation.get("custom_reporting_manager")
	return _insert(doc)



def _create_it_clearance(separation):
	doctype = "Separation IT Clearance"
	if _existing(doctype, separation.name):
		return None

	doc = frappe.new_doc(doctype)
	doc.employee_separation = separation.name
	doc.employee = separation.employee
	doc.reporting_manager = separation.get("custom_reporting_manager")

	# access_revocation_datetime is mandatory and normally defaulted from the
	# fetched last working day, which is not available this early. Set it here
	# so the stub is valid; IT can still bring it forward.
	last_working_day = _approved_relieving_date(separation)
	if last_working_day:
		doc.last_working_day = last_working_day
		doc.access_revocation_datetime = f"{getdate(last_working_day)} 23:59:59"
	return _insert(doc)



def _create_hr_clearance(separation):
	doctype = "Separation HR Clearance"
	if _existing(doctype, separation.name):
		return None

	doc = frappe.new_doc(doctype)
	doc.employee_separation = separation.name
	doc.employee = separation.employee
	doc.reporting_manager = separation.get("custom_reporting_manager")
	# rehire_eligibility is mandatory on the form but genuinely unknown now —
	# that is HR's call later, which is what ignore_mandatory is for.
	return _insert(doc)



def _create_settlement(separation):
	"""The Full and Final Statement — HRMS's, not ours.

	Creating it early is worth it: `before_insert` seeds the payables and
	receivables from withheld salary slips, gratuity, expense claims and
	advances, so Finance opens a statement that is already populated.
	"""
	doctype = "Full and Final Statement"
	if frappe.db.get_value(
		doctype, {"employee": separation.employee, "docstatus": ["<", 2]}, "name"
	):
		return None

	doc = frappe.new_doc(doctype)
	doc.employee = separation.employee
	doc.company = separation.company
	doc.transaction_date = nowdate()
	doc.relieving_date = _approved_relieving_date(separation)
	doc.custom_employee_separation = separation.name
	return _insert(doc)

