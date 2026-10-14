# Copyright (c) 2026, Abhay Nain and contributors
# For license information, please see license.txt

import os

import frappe
from frappe.model.document import Document


_FILTER_TABLES = (
	"applicable_departments",
	"applicable_designations",
	"applicable_branches",
	"applicable_employment_types",
	"applicable_employees",
)

# Closes C-15: HR Policy file extension allow-list. Frappe's Attach field is
# permissive — `.exe` / `.html` / `.js` would be accepted by default. HR
# policies are documents; restrict to the document MIME family.
_ALLOWED_FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt"}


class HRPolicy(Document):
	def validate(self):
		# Closes C-12: a policy with `applies_to_all_employees=0` and zero filter
		# rows applies to nobody. `after_save_hr_policy` would silently create 0
		# acknowledgements, leaving HR with a "published" policy that no
		# employee ever sees. Refuse the save.
		if not self.applies_to_all_employees:
			has_any_filter = any(
				bool(self.get(table_field))
				for table_field in _FILTER_TABLES
			)
			if not has_any_filter:
				frappe.throw(
					"This policy is scoped (Applies to All Employees is unticked) but no "
					"filter rows are set. Either tick <b>Applies to All Employees</b> or add "
					"at least one row in Departments / Designations / Branches / Employment "
					"Types / Manual Employee Override.",
					title="Empty policy scope",
				)

		# C-15: file extension guard (skip if file unset — `reqd=1` in the JSON
		# already covers that on save, but be defensive for partial flows).
		if self.file:
			# `file` is a URL like "/files/policy.pdf" or "/private/files/...";
			# we only need the last path component to read the extension.
			path = (self.file or "").split("?")[0]
			ext = os.path.splitext(path)[1].lower()
			if ext and ext not in _ALLOWED_FILE_EXTENSIONS:
				allowed = ", ".join(sorted(_ALLOWED_FILE_EXTENSIONS))
				frappe.throw(
					f"Policy files must be one of: {allowed}. Got <b>{ext}</b>.",
					title="Disallowed file type",
				)
