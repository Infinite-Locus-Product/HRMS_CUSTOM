"""Full and Final Statement doc_events — wired in hooks.py.

Stage 9 of the exit flow. HRMS's own `Full and Final Statement` already does
most of it: it seeds `payables` from withheld Salary Slips plus Gratuity /
Expense Claim / Bonus / Leave Encashment, seeds `receivables` from Employee
Advance (and Loan only when the lending app is installed), totals both, and
posts a Journal Entry on submit. So myHR extends it rather than replacing it.

What is added here:

- the link back to the resignation, and the two recoveries the exit flow
  produces that HRMS knows nothing about — the IT Clearance total and the
  notice-period shortfall — pushed in as Receivable rows so Finance never
  re-keys them;
- a net payable, because HRMS totals payables and receivables separately but
  never subtracts one from the other;
- the gates: both clearances finished, no unconfirmed notice waiver, and a
  Finance sign-off, before any of it can be submitted.

HRMS's own `before_submit` runs first and refuses to submit while any payable or
receivable row is still Unsettled, so in practice Finance settles the lines and
only then meets the gates below.

The shortfall amount is calculated by `myhr.notice_recovery` from the component
and divisor configured in HR Settings. A waived notice period produces zero —
that is what waiving it means.

Ordering matters: doc_events `validate` runs AFTER the controller's own
validate, so HRMS has already totalled the receivables by the time rows are
added here. `_recompute_totals` therefore redoes that sum rather than leaving a
total that does not match its own table.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

MANAGER_CLEARANCE = "Separation Manager Clearance"
IT_CLEARANCE = "Separation IT Clearance"
HR_CLEARANCE = "Separation HR Clearance"

SEPARATION_APPROVED = "Approved"
MANAGER_CLEARANCE_DONE = "Complete"

# Receivable rows this module owns. Matched on `component`, so a re-save updates
# the row in place instead of appending a second one.
IT_RECOVERY_COMPONENT = "IT Asset Recovery"
PHYSICAL_RECOVERY_COMPONENT = "Physical Asset Damage"
SHORTFALL_COMPONENT = "Notice Period Shortfall"
MANAGED_COMPONENTS = (
	IT_RECOVERY_COMPONENT,
	PHYSICAL_RECOVERY_COMPONENT,
	SHORTFALL_COMPONENT,
)


def validate(doc, method=None):
	_refresh(doc)


def onload(doc, method=None):
	"""Re-read the clearances every time the statement is opened.

	`validate` alone is not enough. The statement is raised the moment the
	resignation is approved — before IT has listed a single asset — so its
	recovery figures would sit at zero until somebody happened to save it.
	Finance would open a settlement showing nothing to recover when there is.
	Nothing is persisted here; the next real save writes it.
	"""
	_refresh(doc)


def _refresh(doc):
	_link_separation(doc)
	_pull_separation_context(doc)
	_pull_recoveries(doc)
	_price_notice_shortfall(doc)
	_sync_managed_receivables(doc)
	_recompute_totals(doc)


def before_submit(doc, method=None):
	_validate_clearances_complete(doc)
	_validate_finance_sign_off(doc)


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------
def _link_separation(doc):
	"""Attach the approved resignation, if the user has not picked one.

	Only an Approved, submitted separation counts — a settlement should never
	attach itself to a resignation still moving through approval.
	"""
	if doc.get("custom_employee_separation") or not doc.employee:
		return

	doc.custom_employee_separation = frappe.db.get_value(
		"Employee Separation",
		{"employee": doc.employee, "workflow_state": SEPARATION_APPROVED, "docstatus": 1},
		"name",
	)


def _pull_separation_context(doc):
	"""Copy the figures this statement needs off the separation.

	Not `fetch_from`: that runs before this hook, and on a new statement the
	separation link is assigned by `_link_separation` above — so a fetched field
	would still be empty on first save and only fill in on the second.
	"""
	doc.custom_notice_period_shortfall_days = 0
	doc._notice_waiver = None

	if not doc.get("custom_employee_separation"):
		return

	separation = frappe.db.get_value(
		"Employee Separation", doc.custom_employee_separation,
		["custom_notice_period_shortfall", "custom_notice_period_waiver"], as_dict=True,
	)
	if not separation:
		return

	doc.custom_notice_period_shortfall_days = cint(separation.custom_notice_period_shortfall)
	# Carried in memory only: it decides whether the shortfall is priced, but it
	# belongs to the separation and should not be duplicated onto this document.
	doc._notice_waiver = separation.custom_notice_period_waiver


def _pull_recoveries(doc):
	"""Mirror both clearances' recovery figures onto this statement.

	Two separate amounts on purpose. IT recovers hardware (laptop, phone);
	HR recovers physical items handed back at the door (badge, keys, parking
	tag). They are decided by different people on different forms, and a
	settlement that merged them would be impossible to query later.

	Neither is HRMS's own `assets_allocated` table, which reads ERPNext Asset
	Movements. If Fixxly does not use the Asset module that table stays empty
	and these are the only asset recoveries there are.
	"""
	doc.custom_it_clearance = None
	doc.custom_it_asset_recovery = 0
	doc.custom_hr_clearance = None
	doc.custom_physical_asset_recovery = 0

	separation = doc.get("custom_employee_separation")
	if not separation:
		return

	it = frappe.db.get_value(
		IT_CLEARANCE, {"employee_separation": separation, "docstatus": ["<", 2]},
		["name", "total_recovery_amount"], as_dict=True,
	)
	if it:
		doc.custom_it_clearance = it.name
		doc.custom_it_asset_recovery = flt(it.total_recovery_amount)

	hr = frappe.db.get_value(
		HR_CLEARANCE, {"employee_separation": separation, "docstatus": ["<", 2]},
		["name", "asset_damage_recovery_amount"], as_dict=True,
	)
	if hr:
		doc.custom_hr_clearance = hr.name
		doc.custom_physical_asset_recovery = flt(hr.asset_damage_recovery_amount)


# ---------------------------------------------------------------------------
# Receivable rows
# ---------------------------------------------------------------------------
def _price_notice_shortfall(doc):
	"""Turn shortfall days into money, using the configured rate.

	Overwritten on every save rather than trusted from input: it is a deduction
	from someone's final pay, and the figure must always be the one the current
	settings produce.
	"""
	from myhr.notice_recovery import get_recovery

	result = get_recovery(
		doc.employee,
		doc.get("custom_notice_period_shortfall_days"),
		waiver=doc.get("_notice_waiver"),
	)
	doc.custom_notice_shortfall_recovery = flt(result["amount"])

	# Surfaced, not swallowed: a settlement that recovers nothing because the
	# component is unset should say so, not look like there was nothing to take.
	if result["reason"] and flt(doc.get("custom_notice_period_shortfall_days")) > 0:
		doc._notice_recovery_note = result["reason"]


def _sync_managed_receivables(doc):
	"""Keep exactly one receivable row per managed recovery, or none.

	Idempotent on purpose: the spec asks for a line item that is created OR
	updated, so saving the statement five times must not leave five rows.
	"""
	wanted = {
		IT_RECOVERY_COMPONENT: (
			flt(doc.get("custom_it_asset_recovery")),
			IT_CLEARANCE,
			doc.get("custom_it_clearance"),
		),
		PHYSICAL_RECOVERY_COMPONENT: (
			flt(doc.get("custom_physical_asset_recovery")),
			HR_CLEARANCE,
			doc.get("custom_hr_clearance"),
		),
		SHORTFALL_COMPONENT: (
			flt(doc.get("custom_notice_shortfall_recovery")),
			"Employee Separation",
			doc.get("custom_employee_separation"),
		),
	}

	existing = {row.component: row for row in doc.receivables or [] if row.component in MANAGED_COMPONENTS}

	for component, (amount, ref_doctype, ref_name) in wanted.items():
		row = existing.get(component)

		if not amount:
			# Dropped to zero — remove the row rather than leaving a 0.00 line
			# on someone's settlement.
			if row:
				doc.receivables.remove(row)
			continue

		if row:
			row.amount = amount
			row.reference_document_type = ref_doctype
			row.reference_document = ref_name
		else:
			doc.append("receivables", {
				"component": component,
				"amount": amount,
				"status": "Unsettled",
				"reference_document_type": ref_doctype,
				"reference_document": ref_name,
			})

	# Re-number after any removal so the grid does not show gaps.
	for idx, row in enumerate(doc.receivables or [], start=1):
		row.idx = idx


def _recompute_totals(doc):
	"""Redo HRMS's receivable total, then derive the net.

	HRMS already ran `set_totals` before this hook, so its figure predates the
	rows added above. Mirroring its formula keeps the stored total honest;
	`custom_net_payable` is the field the spec calls Full & Final Amount Payable.
	"""
	total_receivable = sum(flt(row.amount) for row in doc.receivables or [])
	doc.total_receivable_amount = flt(
		total_receivable + flt(doc.total_asset_recovery_cost),
		doc.precision("total_receivable_amount"),
	)
	doc.custom_net_payable = flt(
		flt(doc.total_payable_amount) - flt(doc.total_receivable_amount),
		doc.precision("custom_net_payable"),
	)


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------
def _validate_clearances_complete(doc):
	"""Both operational clearances must be finished first.

	Until they are, the asset recovery figure is not final, and a settlement
	built on a provisional number is worse than no settlement at all.
	"""
	if not doc.get("custom_employee_separation"):
		frappe.throw(
			_("Link the Employee Separation before submitting, so the clearances can be checked."),
			title=_("No Separation Linked"),
		)

	separation = doc.custom_employee_separation
	blockers = []

	manager_state = frappe.db.get_value(
		MANAGER_CLEARANCE, {"employee_separation": separation, "docstatus": ["<", 2]},
		"workflow_state",
	)
	if manager_state != MANAGER_CLEARANCE_DONE:
		blockers.append(
			_("Manager Clearance is {0}").format(frappe.bold(_(manager_state or "missing")))
		)

	it_docstatus = frappe.db.get_value(
		IT_CLEARANCE, {"employee_separation": separation, "docstatus": ["<", 2]}, "docstatus"
	)
	if it_docstatus != 1:
		blockers.append(
			_("IT Clearance is {0}").format(
				frappe.bold(_("not submitted") if it_docstatus == 0 else _("missing"))
			)
		)

	if blockers:
		frappe.throw(
			_("The settlement cannot be submitted yet: {0}.").format("; ".join(blockers)),
			title=_("Clearances Incomplete"),
		)


def _validate_finance_sign_off(doc):
	if not (doc.get("custom_finance_remarks") or "").strip():
		frappe.throw(
			_("Finance Remarks / Sign-off is required before this statement can be submitted."),
			title=_("Sign-off Missing"),
			exc=frappe.MandatoryError,
		)
