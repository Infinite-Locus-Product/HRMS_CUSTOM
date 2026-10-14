# Copyright (c) 2026, Abhay Nain and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeDirectory(Document):
	"""Employee Directory rows are an auto-managed projection of `Employee`.

	The single sanctioned writer is `myhr.employee_hooks.validate_employee`
	(plus the admin rebuild endpoint). Direct edits or deletions through
	Desk / API would be silently overwritten on the next Employee save,
	confusing users; the guards below make that explicit.

	Bypass for the sanctioned writers via:
	  - `frappe.flags.deleting_employee` (Employee `on_trash` cascade)
	  - `frappe.flags.allow_directory_write` (validate_employee + rebuild)
	"""

	def validate(self):
		# DIR-1: Block direct writes unless a sanctioned writer set the flag.
		# `is_new()` is allowed only when the flag is set (sanctioned insert
		# from validate_employee or rebuild). Otherwise direct creates from
		# Desk / API are blocked too, since Directory rows mirror Employee
		# and shouldn't be created independently.
		if not getattr(frappe.flags, "allow_directory_write", False):
			frappe.throw(
				"Employee Directory rows are auto-managed from Employee. "
				"Edit the source <b>Employee</b> record (name / designation / department / "
				"contact) instead — the directory will sync on the next save.",
				title="Directory is read-only",
			)

	def on_trash(self):
		# DIR-2: Block manual deletion unless the Employee is being trashed
		# (cascade) or HR explicitly set the rebuild override flag.
		if getattr(frappe.flags, "deleting_employee", False):
			return
		if getattr(frappe.flags, "allow_directory_write", False):
			return
		frappe.throw(
			"Employee Directory rows cannot be deleted directly. "
			"Either delete the linked Employee, untick <b>Add to Employee Directory</b> on "
			"the Employee record, or use <code>myhr.api.rebuild_employee_directory</code>.",
			title="Cannot delete Directory row",
		)
