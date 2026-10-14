# Copyright (c) 2026, Fixxly and contributors
# For license information, please see license.txt

"""Stage 6 of the exit flow — the reporting manager's KT / handover clearance.

The form has two halves with different owners. The employee fills the handover
side and submits it; their reporting manager then verifies and completes it.
Which half is editable is decided by the `Separation Manager Clearance` workflow
(Draft -> Pending Manager Clearance -> Complete), and every rule below is
enforced here rather than in the UI, because `depends_on` and
`mandatory_depends_on` run only in the browser.

The rules are keyed off `workflow_state` rather than docstatus: Frappe sets the
new state on the document and then saves it, so `validate` already sees the
state the transition is moving INTO. That means a rule written for Complete
blocks the transition itself, leaving the record where it was.
"""

import frappe
from frappe import _
from frappe.model.document import Document

DRAFT = "Draft"
PENDING_MANAGER = "Pending Manager Clearance"
COMPLETE = "Complete"

# The linked resignation must have cleared both approval levels first.
SEPARATION_APPROVED = "Approved"

EMPLOYEE_CONFIRMATIONS = (
	("downloaded_payslips", "Downloaded Payslips?"),
	("downloaded_tax_slips", "Downloaded Tax Slips / Form 16?"),
	("cleared_personal_files", "Cleared Personal Files from Drive?"),
)


class SeparationManagerClearance(Document):
	def validate(self):
		self.validate_handover_rows()
		self.validate_kt_handover_prerequisites()

		state = self.get("workflow_state") or DRAFT

		# Past Draft means the employee has submitted their half, so it must be
		# complete. Checked on state rather than on save so a part-filled draft
		# can still be saved.
		if state != DRAFT:
			self.validate_employee_half()

		if state == COMPLETE:
			self.validate_access_revocation()
			self.validate_manager_sign_off()
			self.validate_separation_is_approved()

	# -- employee's half ----------------------------------------------------
	def validate_handover_rows(self):
		"""A row must actually carry something — a file, a link or a note."""
		for row in self.handover_documents or []:
			if not (row.attachment or row.external_link or (row.notes or "").strip()):
				frappe.throw(
					_("Handover Documents row {0} ({1}) is empty. Attach a file, add a link, or write a note.").format(
						row.idx, frappe.bold(row.title or _("untitled"))
					),
					title=_("Empty Handover Row"),
				)

	def validate_employee_half(self):
		missing = [label for fieldname, label in EMPLOYEE_CONFIRMATIONS if not self.get(fieldname)]
		if missing:
			frappe.throw(
				_("Tick {0} before submitting your handover.").format(
					frappe.bold(", ".join(_(label) for label in missing))
				),
				title=_("Confirmations Incomplete"),
				exc=frappe.MandatoryError,
			)

	# -- manager's half -----------------------------------------------------
	def validate_kt_handover_prerequisites(self):
		"""'KT / Handover Received? = Yes' needs something to have been handed over.

		Enforced at save time on the field itself, not on a transition: the
		manager must not be able to record receipt of a handover that was never
		provided, whatever state the record is in.
		"""
		if self.kt_handover_received != "Yes":
			return

		missing = []
		if not (self.handover_documents or []):
			missing.append(_("a Handover Document"))
		if not self.primary_successor:
			missing.append(_("a Primary Successor"))

		if missing:
			frappe.throw(
				_("KT / Handover Received cannot be Yes until the employee has provided {0}.").format(
					frappe.bold(_(" and ").join(missing))
				),
				title=_("Nothing Handed Over"),
			)

	def validate_access_revocation(self):
		"""Never blank by omission: either systems are listed, or N/A is explicit."""
		selected = self.access_revocation_requested or []
		not_applicable = bool(self.access_revocation_not_applicable)

		if not selected and not not_applicable:
			frappe.throw(
				_("List the systems under Project Access Revocation Requested, or tick Access Revocation Not Applicable."),
				title=_("Access Revocation Not Answered"),
				exc=frappe.MandatoryError,
			)

		if selected and not_applicable:
			frappe.throw(
				_("Access Revocation is marked Not Applicable but {0} system(s) are listed. Clear one or the other.").format(
					len(selected)
				),
				title=_("Contradictory Access Revocation"),
			)

	def validate_manager_sign_off(self):
		if not (self.manager_remarks or "").strip():
			frappe.throw(
				_("Manager Remarks / Sign-off is required before this clearance can be completed."),
				title=_("Sign-off Missing"),
				exc=frappe.MandatoryError,
			)

	def validate_separation_is_approved(self):
		state = frappe.db.get_value("Employee Separation", self.employee_separation, "workflow_state")
		if state == SEPARATION_APPROVED:
			return

		frappe.throw(
			_("{0} is {1}, not {2}. The resignation must clear both approval levels before this clearance can be completed.").format(
				frappe.bold(self.employee_separation),
				frappe.bold(_(state or "Draft")),
				frappe.bold(_(SEPARATION_APPROVED)),
			),
			title=_("Separation Not Approved Yet"),
		)
