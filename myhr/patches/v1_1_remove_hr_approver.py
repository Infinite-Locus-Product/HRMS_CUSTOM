"""Remove the two-stage 'hr_approver' scaffolding.

Drops:
- `Custom Field` Employee-hr_approver
- `Custom Field` Leave Application-hr_approver
- Any leftover `Property Setter` rows referencing the field
- The legacy `Approved by Manager` value in Leave Application status — flipped to Approved

Then re-runs the status-options Property Setter helper so the doctype select
field is pinned to `Open\\nApproved\\nRejected\\nCancelled`. Idempotent.
"""

import frappe


def execute():
	# 1. Flip any in-flight 'Approved by Manager' rows to 'Approved' so dropping
	#    the option from the select doesn't strand them in an invalid state.
	if frappe.db.exists("DocType", "Leave Application"):
		legacy = frappe.db.count("Leave Application", {"status": "Approved by Manager"})
		if legacy:
			frappe.db.sql(
				"UPDATE `tabLeave Application` SET `status` = 'Approved' WHERE `status` = 'Approved by Manager'"
			)
			frappe.logger().info(
				f"myHR v1_1: migrated {legacy} Leave Application row(s) Approved by Manager -> Approved"
			)

	# 2. Drop the two custom fields.
	for cf in ("Employee-hr_approver", "Leave Application-hr_approver"):
		if frappe.db.exists("Custom Field", cf):
			frappe.delete_doc("Custom Field", cf, ignore_permissions=True, force=True)
			frappe.logger().info(f"myHR v1_1: deleted Custom Field {cf}")

	# 3. Wipe Property Setters that referenced hr_approver.
	for ps in frappe.get_all(
		"Property Setter",
		filters={"field_name": "hr_approver"},
		pluck="name",
	):
		frappe.delete_doc("Property Setter", ps, ignore_permissions=True, force=True)
		frappe.logger().info(f"myHR v1_1: deleted Property Setter {ps}")

	# 4. Re-pin the Leave Application status options Property Setter.
	from myhr.setup import _ensure_leave_application_status_property_setter
	_ensure_leave_application_status_property_setter()

	frappe.db.commit()
	frappe.clear_cache()
