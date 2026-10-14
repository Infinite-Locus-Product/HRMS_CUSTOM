"""Single-stage Expense Claim: auto-submit on approver verdict.

Mirrors `myhr/overrides/leave_application.py`. Once an approver flips
`approval_status` to Approved or Rejected on a draft Expense Claim, the
document submits immediately so it leaves the Team Requests pending queue
and the GL entry posts in one continuous step. No second "Submit" tap.

Stock HRMS already permits docstatus 0 → 1 only when approval_status is
Approved or Rejected (the `before_submit` guard at expense_claim.py:148
throws if status is still Draft), so this lines up with the existing
state machine.

The pre-existing approval-authority gate
(`myhr.approval_gate.gate_expense_claim_approval`) fires on `validate`
*before* the auto-submit cascade, so an unauthorised user can't slip
through the fast path. The gate's own `previous == new` early-return
means the second validate inside submit() is a no-op.
"""

import frappe
from frappe import _
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim as HRMSExpenseClaim


class ExpenseClaim(HRMSExpenseClaim):
	def validate(self):
		super().validate()
		self._enforce_rejection_remarks()
		self._enforce_single_expense_row()

	def _enforce_single_expense_row(self):
		"""Company policy: one Expense Claim carries exactly one expense row.

		If multiple expenses need filing, each goes as its own claim — keeps
		the per-row approval / cap-override decision atomic for the approver.
		Fired on every save so the limit applies to insert, in-place edits
		via PWA / Desk, and any scripted bulk write.
		"""
		count = len(self.expenses or [])
		if count > 1:
			frappe.throw(
				_("Only one expense is allowed per Expense Claim. "
				  "Remove the extra rows ({0} found) or file additional claims separately.").format(count),
				title=_("Too many expense rows"),
			)

	def _enforce_rejection_remarks(self):
		"""EC-1: on the Draft → Rejected transition, require a non-empty
		`custom_rejection_reason`. Mirrors LA-4. The PWA Reject dialog
		captures the reason in the same setValue call that flips
		approval_status to Rejected, so by the time validate runs the
		reason is on the in-memory doc."""
		previous = self.get_doc_before_save()
		old_status = previous.approval_status if previous else None
		new_status = self.approval_status

		if new_status == "Rejected" and old_status != "Rejected":
			reason = (self.get("custom_rejection_reason") or "").strip()
			if not reason:
				frappe.throw(
					_("A rejection reason is required when rejecting an Expense Claim."),
					title=_("Rejection reason required"),
				)

	def on_update(self):
		super().on_update()
		# Single-stage: a finalised verdict (Approved or Rejected) auto-submits
		# so the claim leaves the Team Requests pending queue, posts the GL
		# entry, and becomes immutable in the same user gesture.
		if self.docstatus == 0 and self.approval_status in ("Approved", "Rejected"):
			self.submit()
