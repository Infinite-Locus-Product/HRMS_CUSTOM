# Copyright (c) 2026, Abhay Nain and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PolicyAuditLog(Document):
	"""Append-only log of every Policy Acknowledgement state transition.

	Doctype perms forbid create/write/delete for every role. Rows are inserted
	via `frappe.get_doc(...).insert(ignore_permissions=True)` from
	`myhr.policy_audit` only. The companion validate below makes that explicit.
	"""

	def validate(self):
		# Block edits at the document level too (perms already say write=0,
		# but defensive layering — the SQL bypass concern that motivated this
		# doctype could equally apply to PAL itself).
		if not self.is_new() and not getattr(frappe.flags, "allow_audit_log_edit", False):
			frappe.throw("Policy Audit Log entries are append-only.")
