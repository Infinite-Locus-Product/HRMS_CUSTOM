# Copyright (c) 2026, Fixxly and contributors
# For license information, please see license.txt

"""Stage 7 of the exit flow — IT clearance.

Hardware, access revocation and mailbox forwarding. Every rule lives here
rather than in the UI, because `depends_on` and `mandatory_depends_on` are
browser-only and this form decides how much money is recovered from someone's
final settlement.

Asset Condition is per row, not one dropdown for the whole form: the spec
requires every returned item to carry its own condition, which a single field
cannot express. Recovery Amount follows the condition, so it lives per row too,
and the parent stores their total.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, getdate

CHARGEABLE_CONDITIONS = ("Damaged", "Missing")
SEPARATION_APPROVED = "Approved"

# End of the last working day. Access may be cut earlier, never later.
LAST_MOMENT = "23:59:59"


class SeparationITClearance(Document):
	def validate(self):
		self.set_default_revocation_datetime()
		self.validate_assets()
		self.compute_total_recovery()
		self.validate_revocation_not_after_last_working_day()
		self.validate_forwarding_address()

	def before_submit(self):
		self.validate_separation_is_approved()

	# -- access revocation --------------------------------------------------
	def set_default_revocation_datetime(self):
		"""Default to 23:59 on the last working day, per the spec."""
		if self.access_revocation_datetime or not self.last_working_day:
			return
		self.access_revocation_datetime = f"{getdate(self.last_working_day)} {LAST_MOMENT}"

	def validate_revocation_not_after_last_working_day(self):
		if not (self.access_revocation_datetime and self.last_working_day):
			# No approved relieving date yet means no ceiling to check against.
			# before_submit blocks submission until the separation is Approved,
			# by which point the date exists.
			return

		ceiling = get_datetime(f"{getdate(self.last_working_day)} {LAST_MOMENT}")
		if get_datetime(self.access_revocation_datetime) > ceiling:
			frappe.throw(
				_("Access Revocation cannot be later than {0}. IT may bring it forward, but not push it back.").format(
					frappe.bold(frappe.format(ceiling, {"fieldtype": "Datetime"}))
				),
				title=_("Revocation Too Late"),
			)

	# -- hardware -----------------------------------------------------------
	def validate_assets(self):
		seen = set()
		for row in self.assets or []:
			if row.asset_type in seen:
				frappe.throw(
					_("{0} is listed more than once. Use a single row per asset.").format(
						frappe.bold(row.asset_type)
					),
					title=_("Duplicate Asset"),
				)
			seen.add(row.asset_type)

			# "The form will not save with a returned item left unclassified."
			if row.returned and not row.asset_condition:
				frappe.throw(
					_("Row {0}: {1} is marked Returned but has no Condition.").format(
						row.idx, frappe.bold(row.asset_type)
					),
					title=_("Unclassified Asset"),
					exc=frappe.MandatoryError,
				)

			if row.asset_condition in CHARGEABLE_CONDITIONS:
				if not flt(row.recovery_amount):
					frappe.throw(
						_("Row {0}: {1} is {2}, so a Recovery Amount is required.").format(
							row.idx, frappe.bold(row.asset_type), frappe.bold(_(row.asset_condition))
						),
						title=_("Recovery Amount Missing"),
						exc=frappe.MandatoryError,
					)
			elif flt(row.recovery_amount):
				# Good (or unclassified) cannot carry a charge — otherwise money
				# comes out of a settlement with nothing justifying it.
				frappe.throw(
					_("Row {0}: {1} has a Recovery Amount but its Condition is {2}. Recovery applies only to {3}.").format(
						row.idx, frappe.bold(row.asset_type),
						frappe.bold(_(row.asset_condition or "blank")),
						" / ".join(_(c) for c in CHARGEABLE_CONDITIONS),
					),
					title=_("Unjustified Recovery Amount"),
				)

	def compute_total_recovery(self):
		"""Always derived. Never trusted from input — it drives a deduction."""
		self.total_recovery_amount = flt(
			sum(flt(row.recovery_amount) for row in self.assets or []), 2
		)

	# -- mailbox ------------------------------------------------------------
	def validate_forwarding_address(self):
		"""Optional, but if given it must be an internal address."""
		address = (self.mailbox_forwarding_address or "").strip()
		if not address:
			return

		domains = get_internal_email_domains()
		if not domains:
			# Nothing configured: the address still has to be well formed, but
			# there is no domain list to check it against.
			return

		domain = address.rsplit("@", 1)[-1].lower()
		if domain not in domains:
			frappe.throw(
				_("{0} is not an internal address. Allowed domains: {1}.").format(
					frappe.bold(address), frappe.bold(", ".join(sorted(domains)))
				),
				title=_("External Forwarding Address"),
			)

	# -- gating -------------------------------------------------------------
	def validate_separation_is_approved(self):
		state = frappe.db.get_value("Employee Separation", self.employee_separation, "workflow_state")
		if state == SEPARATION_APPROVED:
			return
		frappe.throw(
			_("{0} is {1}, not {2}. IT clearance cannot be finalised before the resignation is approved.").format(
				frappe.bold(self.employee_separation), frappe.bold(_(state or "Draft")),
				frappe.bold(_(SEPARATION_APPROVED)),
			),
			title=_("Separation Not Approved Yet"),
		)


def get_internal_email_domains():
	"""Domains counted as internal, from HR Settings.

	Stored as a newline/comma separated list so HR can add one without a code
	change. Empty means the check is skipped rather than everything failing.
	"""
	raw = frappe.db.get_single_value("HR Settings", "custom_internal_email_domains") or ""
	parts = raw.replace(",", "\n").split("\n")
	return {p.strip().lstrip("@").lower() for p in parts if p.strip()}
