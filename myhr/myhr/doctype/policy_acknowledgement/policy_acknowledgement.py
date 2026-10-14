# Copyright (c) 2026, Abhay Nain and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


# Allowed status transitions on save. Anything not listed throws.
# (None on the LHS means "this is a fresh insert".)
_ALLOWED_TRANSITIONS = {
	None:           {"Pending", "Acknowledged", "Superseded", "Withdrawn"},
	"Pending":      {"Pending", "Acknowledged", "Superseded", "Withdrawn"},
	"Acknowledged": {"Acknowledged", "Superseded"},   # NO going back to Pending
	"Superseded":   {"Superseded"},                    # frozen audit row
	"Withdrawn":    {"Withdrawn"},                     # frozen — policy was deactivated
}

# Identifier fields that must never change after insert.
_IMMUTABLE_FIELDS = ("employee", "hr_policy", "policy_version")


class PolicyAcknowledgement(Document):
	"""Audit-grade state machine for policy acknowledgements.

	Once a row is `Acknowledged`, it can only ever be superseded by a policy
	version bump — HR cannot revert it to `Pending` from Desk. Once
	`Superseded` or `Withdrawn`, the row is frozen.

	Immutable identifier fields (employee, hr_policy, policy_version) cannot
	be edited after insert — that would let someone re-target an existing
	acknowledgement at a different employee or policy.

	Audit fields are server-stamped on the Pending → Acknowledged transition
	and locked thereafter. HR Desk users cannot pre-set or backdate them.

	Every transition (insert + save) writes a `Policy Audit Log` row. System
	paths that bypass `validate()` (e.g., raw SQL UPDATE) MUST go through
	`myhr.policy_audit.transition_pa(...)` to keep the log honest.
	"""

	def validate(self):
		# Lazy import to avoid a circular import at module load.
		from myhr.policy_audit import write_audit_log_for_change

		if self.is_new():
			# On insert, only the four states are allowed.
			if self.status not in _ALLOWED_TRANSITIONS[None]:
				frappe.throw(
					f"Invalid initial status {self.status!r} for Policy Acknowledgement.",
				)
			# Pending rows must not carry an acknowledgement timestamp (closes
			# C-5: HR could otherwise pre-set acknowledged_at and backdate the
			# audit when the user later acknowledges).
			if self.status == "Pending":
				self.acknowledged_at = None
				self.ip_address = None
			# Audit log written from after_insert (we don't have a `name` yet).
			return

		previous = self.get_doc_before_save()
		if not previous:
			# Defensive: if Frappe didn't load the prior state, fall back to a
			# DB read so we don't silently let Acknowledged → Pending through.
			previous = frappe._dict(frappe.db.get_value(
				"Policy Acknowledgement", self.name,
				["status", "employee", "hr_policy", "policy_version", "acknowledged_at"],
				as_dict=True,
			) or {})

		# 1. Identifier fields are immutable
		for f in _IMMUTABLE_FIELDS:
			if previous.get(f) is not None and previous.get(f) != self.get(f):
				frappe.throw(
					f"Cannot change {f!r} on an existing Policy Acknowledgement "
					f"(was {previous.get(f)!r}, attempted {self.get(f)!r}).",
				)

		# 2. Status transition
		old = previous.get("status")
		new = self.status
		allowed = _ALLOWED_TRANSITIONS.get(old, set())
		if new not in allowed:
			frappe.throw(
				f"Cannot change Policy Acknowledgement status from "
				f"{old!r} to {new!r}. "
				f"Once an acknowledgement is recorded it cannot be reverted; "
				f"create a new HR Policy version if a re-acknowledgement is needed.",
			)

		# 3. Pending → Pending: keep audit fields clear so HR can't pre-stamp them.
		if old == "Pending" and new == "Pending":
			self.acknowledged_at = None
			self.ip_address = None

		# 4. Pending → Acknowledged: server-stamp the audit fields, ignoring any
		#    client-supplied values. Closes C-6 (Desk path was unstamped).
		if old == "Pending" and new == "Acknowledged":
			self.acknowledged_at = frappe.utils.now_datetime()
			self.ip_address = (
				getattr(frappe.local, "request_ip", None)
				or self.ip_address
				or ""
			)

		# 5. Acknowledged → Acknowledged: timestamp can't be cleared/rewritten.
		if old == "Acknowledged" and new == "Acknowledged":
			old_at = previous.get("acknowledged_at")
			if old_at:
				# Normalize to second precision: DB has microseconds, the
				# form re-posts a string without them, so a raw `!=`
				# misfires.
				old_at_norm = frappe.utils.get_datetime(old_at).replace(microsecond=0)
				new_at_norm = (
					frappe.utils.get_datetime(self.acknowledged_at).replace(microsecond=0)
					if self.acknowledged_at else None
				)
				if old_at_norm != new_at_norm:
					frappe.throw(
						"Cannot modify acknowledged_at on a row that is already Acknowledged.",
					)

	def after_insert(self):
		from myhr.policy_audit import write_audit_log_for_change
		write_audit_log_for_change(self.name, None, self.status, via="ORM",
			note="Initial insert")

	def on_update(self):
		# Only log status flips; ignore no-op resaves.
		from myhr.policy_audit import write_audit_log_for_change
		previous = self.get_doc_before_save()
		old = previous.status if previous else None
		if old and old != self.status:
			# Allow callers to override `via` (API endpoint, bulk-ack helper,
			# reconcile loop, etc.) by setting `frappe.flags.policy_audit_via`
			# on the request. Defaults to ORM for unannotated paths.
			via = getattr(frappe.flags, "policy_audit_via", None) or "ORM"
			write_audit_log_for_change(self.name, old, self.status, via=via,
				note=None)
