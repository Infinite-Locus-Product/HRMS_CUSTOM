"""Ensure Shift Type.custom_auto_checkout_at_eod Custom Field exists.

The field is declared in `MYHR_CUSTOM_FIELDS` (setup.py) and ships via the
standard `_ensure_custom_fields` path on `after_migrate`. This patch is the
belt-and-braces guarantee for sites that miss the after_migrate hook
(install order quirks, partial-failed migrations, etc.). Idempotent.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


_FIELD_NAME = "Shift Type-custom_auto_checkout_at_eod"


def execute():
	if frappe.db.exists("Custom Field", _FIELD_NAME):
		print(f"v1_28: {_FIELD_NAME} already present, nothing to do.")
		return

	create_custom_fields(
		{
			"Shift Type": [
				{
					"fieldname": "custom_auto_checkout_at_eod",
					"label": "Auto Check-Out at End of Day",
					"fieldtype": "Check",
					"insert_after": "mark_auto_attendance_on_holidays",
					"default": "0",
					"description": (
						"When ticked, the daily 23:55 scheduler inserts an OUT "
						"Employee Checkin at 23:59 for every Active employee on "
						"this shift who has an IN today but no OUT. Skips holidays "
						"+ employees on approved Leave. Requires Enable Auto "
						"Attendance also ticked to have any effect."
					),
				}
			]
		},
		ignore_validate=True,
	)
	frappe.clear_cache(doctype="Shift Type")
	frappe.db.commit()
	print(f"v1_28: created Custom Field {_FIELD_NAME}.")
