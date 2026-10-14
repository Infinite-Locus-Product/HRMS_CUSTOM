"""Single-stage Leave Application: validate + auto-submit on approval.

Phase 2 hardening (2026-04-26):
  - LA-1: server-stamp `custom_approved_by` / `custom_approved_on` on the
    Open → Approved transition. Locked thereafter.
  - LA-2: state machine guard against Approved → Open reversal in-flight
    (docstatus=0). HR Manager bypass via `frappe.flags.allow_la_status_revert`.
  - LA-3: in-app Notification Log entry to the employee on
    Approved / Rejected verdicts.
"""

import frappe
from frappe import _
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication as HRMSLeaveApplication

from myhr.leave_optional_holiday import validate_optional_leave_dates


class LeaveApplication(HRMSLeaveApplication):
	def validate(self):
		self._guard_status_reversal()
		super().validate()
		self._validate_optional_leave_rules()
		self._stamp_approval_audit()
		self._enforce_rejection_remarks()
		# Snapshot the verdict transition for the post-save notification.
		# Auto-submit's second save cycle confuses get_doc_before_save (the
		# nested save sees the post-save state as 'previous'), so we capture
		# the transition during validate (before super.on_update + auto-submit
		# kick in) and fire the notification in on_update against this flag.
		previous = self.get_doc_before_save()
		old_status = previous.status if previous else None
		if old_status != self.status and self.status in ("Approved", "Rejected"):
			self._verdict_to_notify = self.status
		else:
			self._verdict_to_notify = None

	def _guard_status_reversal(self):
		"""LA-2: once status='Approved' on a draft (docstatus=0), don't let it
		flip back to Open silently. Stock HRMS plus the auto-submit on Approved
		means in practice the row submits immediately, but a save-with-status-
		Open after approval (e.g., HR editing the row in Desk before the
		auto-submit on_update fires) would un-stamp the audit fields.

		HR Manager / System Manager may bypass via the flag for the rare
		reopen path."""
		if self.docstatus != 0:
			return
		previous = self.get_doc_before_save()
		if not previous:
			return
		old = previous.status
		new = self.status
		# Approved and Rejected are both terminal verdicts — both auto-submit on
		# on_update, but if the submit ever fails the row could linger at
		# docstatus=0 with the verdict set. Block silent reversal in that window
		# so the audit trail (custom_approved_by / custom_rejection_reason)
		# stays consistent with the visible status.
		if old in ("Approved", "Rejected") and new != old:
			if getattr(frappe.flags, "allow_la_status_revert", False):
				return
			frappe.throw(
				_("Cannot revert a Leave Application from <b>{0}</b> to {1} once a verdict has been recorded. "
				  "If a correction is needed, cancel the submitted leave instead.").format(old, new),
				title=_("Verdict is locked"),
			)

	def _validate_optional_leave_rules(self):
		if not (self.leave_type and self.from_date and self.to_date):
			return
		# Skip optional-leave date checks on the way OUT of the queue — a row
		# being moved to Rejected or Cancelled has no future calendar impact,
		# and re-running the validator would otherwise see the row itself as a
		# colliding application of the same date.
		if self.status in ("Rejected", "Cancelled"):
			return
		if not frappe.db.get_value("Leave Type", self.leave_type, "is_optional_leave"):
			return
		if self.half_day:
			frappe.throw(_("Optional leaves can only be applied as full-day; half-day is not supported."))
		validate_optional_leave_dates(self.employee, self.from_date, self.to_date)

	def _stamp_approval_audit(self):
		"""LA-1: stamp custom_approved_by / custom_approved_on on the Open →
		Approved transition. Locked once set — clearing or rewriting throws
		unless `frappe.flags.allow_la_audit_edit` is set."""
		previous = self.get_doc_before_save()
		old_status = previous.status if previous else None
		new_status = self.status

		# Stamp on transition into Approved
		if new_status == "Approved" and old_status != "Approved":
			if not self.get("custom_approved_by"):
				self.custom_approved_by = frappe.session.user
			if not self.get("custom_approved_on"):
				self.custom_approved_on = frappe.utils.now_datetime()

		# Lock once set (idempotent self-saves are fine; only mismatches throw)
		if previous and not getattr(frappe.flags, "allow_la_audit_edit", False):
			old_by = previous.get("custom_approved_by")
			old_on = previous.get("custom_approved_on")
			if old_by and self.get("custom_approved_by") != old_by:
				frappe.throw(_("`Approved By` is the audit record and cannot be modified."))
			# Normalize to second precision: DB has microseconds, the form
			# re-posts a string without them, so a raw `!=` misfires.
			if old_on:
				new_on = self.get("custom_approved_on")
				old_on_norm = frappe.utils.get_datetime(old_on).replace(microsecond=0)
				new_on_norm = (
					frappe.utils.get_datetime(new_on).replace(microsecond=0)
					if new_on else None
				)
				if old_on_norm != new_on_norm:
					frappe.throw(_("`Approved On` is the audit timestamp and cannot be modified."))

	def _enforce_rejection_remarks(self):
		"""LA-4: on the Open → Rejected transition, require a non-empty
		`custom_rejection_reason`. Locked once set so the audit trail can't be
		retroactively edited (HR Manager bypass via the same audit-edit flag
		used by the approval stamps)."""
		previous = self.get_doc_before_save()
		old_status = previous.status if previous else None
		new_status = self.status

		if new_status == "Rejected" and old_status != "Rejected":
			reason = (self.get("custom_rejection_reason") or "").strip()
			if not reason:
				frappe.throw(
					_("A rejection reason is required when rejecting a Leave Application."),
					title=_("Rejection reason missing"),
				)

		if previous and not getattr(frappe.flags, "allow_la_audit_edit", False):
			old_reason = (previous.get("custom_rejection_reason") or "").strip()
			new_reason = (self.get("custom_rejection_reason") or "").strip()
			if old_reason and new_reason != old_reason:
				frappe.throw(_("`Rejection Reason` is part of the audit record and cannot be modified."))

	def on_update(self):
		super().on_update()
		# Fire the verdict notification BEFORE auto-submit. Auto-submit
		# triggers a nested save cycle and we don't want to double-notify or
		# misinterpret previous status.
		self._notify_employee_on_verdict()
		self._verdict_to_notify = None  # consumed; clear before nested submit

		# Single-stage: a finalised verdict (Approved or Rejected) auto-submits
		# so the LA leaves the Team Requests pending queue and goes immutable.
		# Stock HRMS allows docstatus 0→1 only when status is Approved/Rejected,
		# which lines up with this gate.
		if self.docstatus == 0 and self.status in ("Approved", "Rejected"):
			self.submit()

	def _notify_employee_on_verdict(self):
		"""LA-3: ping the employee on Approved / Rejected. Reads the
		`_verdict_to_notify` flag set in validate() so it fires reliably even
		under the auto-submit cascade. Best-effort — failures log to Error Log,
		never raise."""
		try:
			verdict = getattr(self, "_verdict_to_notify", None)
			if verdict not in ("Approved", "Rejected"):
				return

			emp_user = frappe.db.get_value("Employee", self.employee, "user_id")
			if not emp_user:
				return

			if verdict == "Approved":
				subject = f"[myHR Leave] Approved — {self.leave_type} ({self.from_date} to {self.to_date})"
				body = (
					f"<p>Your leave application has been <b>approved</b>.</p>"
					f"<p><b>Type:</b> {self.leave_type}<br>"
					f"<b>From:</b> {self.from_date}<br>"
					f"<b>To:</b> {self.to_date}<br>"
					f"<b>Days:</b> {self.total_leave_days}</p>"
				)
			else:
				reason = (self.get("rejection_reason") or "").strip()
				subject = f"[myHR Leave] Rejected — {self.leave_type} ({self.from_date} to {self.to_date})"
				body = (
					f"<p>Your leave application has been <b>rejected</b>.</p>"
					f"<p><b>Type:</b> {self.leave_type}<br>"
					f"<b>From:</b> {self.from_date}<br>"
					f"<b>To:</b> {self.to_date}</p>"
					+ (f"<p><b>Reason:</b> {reason}</p>" if reason else "")
				)

			frappe.get_doc({
				"doctype": "Notification Log",
				"for_user": emp_user,
				"type": "Alert",
				"subject": subject,
				"email_content": body,
				"document_type": "Leave Application",
				"document_name": self.name,
				"from_user": "Administrator",
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(
				title="myHR LA _notify_employee_on_verdict failed",
				message=frappe.get_traceback(),
			)
