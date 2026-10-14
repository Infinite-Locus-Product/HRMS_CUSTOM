"""One-time backfill: seed Employee Directory from existing Active employees.

Idempotent — safe to re-run. Uses the same upsert logic as
`myhr.api.rebuild_employee_directory` but bypasses the role check since
patches run as Administrator.
"""

import frappe


def execute():
	target_employees = frappe.get_all(
		"Employee",
		filters={"custom_emp_directory": 1, "status": "Active"},
		fields=["name", "employee_name", "designation", "department", "cell_number", "company_email"],
	)
	target_names = {e.name for e in target_employees}

	added = updated = removed = 0

	for e in target_employees:
		payload = {
			"doctype": "Employee Directory",
			"employee_id": e.name,
			"employee_name": e.employee_name,
			"designation": e.designation,
			"department": e.department,
			"mobile_number": e.cell_number,
			"employee_email": e.company_email,
		}
		if frappe.db.exists("Employee Directory", e.name):
			d = frappe.get_doc("Employee Directory", e.name)
			d.update(payload)
			d.save(ignore_permissions=True)
			updated += 1
		else:
			frappe.get_doc(payload).insert(ignore_permissions=True)
			added += 1

	for d in frappe.get_all("Employee Directory", pluck="name"):
		if d not in target_names:
			frappe.delete_doc("Employee Directory", d, ignore_permissions=True)
			removed += 1

	frappe.db.commit()
	frappe.logger().info(
		f"myHR backfill_employee_directory: added={added} updated={updated} removed={removed}"
	)
