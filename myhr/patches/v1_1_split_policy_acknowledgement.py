"""Backfill `Policy Acknowledgement` from the legacy `Policy Action Task` child rows.

Phase 2 of the policy split. Idempotent — re-running creates no duplicates because we check
`exists` before insert. Old `Policy Action Task` rows are NOT deleted; they remain in the DB
as historical reference until a future cleanup patch removes the table.
"""
import frappe


def execute():
	if not frappe.db.exists("DocType", "Policy Acknowledgement"):
		print("Policy Acknowledgement doctype not present yet; skipping.")
		return
	if not frappe.db.exists("DocType", "Policy Action Task"):
		print("Policy Action Task doctype not present (already cleaned up?); skipping.")
		return

	# Default version=1, is_active=1, applies_to_all_employees=1 on every existing HR Policy that lacks them.
	for policy in frappe.get_all(
		"HR Policy",
		fields=["name", "version", "is_active", "applies_to_all_employees", "applicability_logic"],
	):
		updates = {}
		if not policy.version:
			updates["version"] = 1
		if policy.is_active is None:
			updates["is_active"] = 1
		if policy.applies_to_all_employees is None:
			updates["applies_to_all_employees"] = 1
		if not policy.applicability_logic:
			updates["applicability_logic"] = "OR"
		if updates:
			frappe.db.set_value("HR Policy", policy.name, updates)

	# Move every Policy Action Task row to a standalone Policy Acknowledgement row.
	rows = frappe.db.sql(
		"""
		SELECT pat.name AS old_row, pat.hr_policy, pat.status, pat.acknowledged_at, pat.ip_address,
		       ac.employee
		FROM `tabPolicy Action Task` pat
		INNER JOIN `tabEmployee Action Centre` ac ON ac.name = pat.parent
		""",
		as_dict=True,
	)

	created = skipped = orphan = 0
	for r in rows:
		if not r.hr_policy or not r.employee:
			orphan += 1
			continue
		if not frappe.db.exists("HR Policy", r.hr_policy):
			orphan += 1
			continue
		if not frappe.db.exists("Employee", r.employee):
			orphan += 1
			continue
		if frappe.db.exists(
			"Policy Acknowledgement",
			{"employee": r.employee, "hr_policy": r.hr_policy, "policy_version": 1},
		):
			skipped += 1
			continue

		new_status = "Acknowledged" if (r.status or "").strip() == "Acknowledged" else "Pending"
		frappe.get_doc({
			"doctype": "Policy Acknowledgement",
			"employee": r.employee,
			"hr_policy": r.hr_policy,
			"policy_version": 1,
			"status": new_status,
			"acknowledged_at": r.acknowledged_at,
			"ip_address": r.ip_address or "",
		}).insert(ignore_permissions=True)
		created += 1

	frappe.db.commit()
	print(f"Policy split backfill: created={created}, skipped (already migrated)={skipped}, orphan rows={orphan}")
