"""Dedupe duplicate Employee Action Centre rows and add a unique index on
`employee`.

Closes EAC-1. Without this index, the `frappe.db.exists` + `insert` pattern
in `myhr.employee_hooks._ensure_action_centre` is racy under concurrent
saves and can produce duplicate ACs that the application has no way to
merge.

Dedupe rule:
- Group by `employee`. Within a group, prefer the row with the strongest
  `status` (Accepted > To be Reviewed > Action Required > Ready to Submit >
  In Progress > Pending). Ties broken by latest `modified` so we keep the
  most-recently-touched receipt.
- Losers are deleted with their child rows (activity_logs).
"""
import frappe


_STATUS_RANK = {
	"Accepted": 6,
	"To be Reviewed": 5,
	"Action Required": 4,
	"Ready to Submit": 3,
	"In Progress": 2,
	"Pending": 1,
}


def execute():
	if not frappe.db.exists("DocType", "Employee Action Centre"):
		print("Employee Action Centre doctype not present; skipping.")
		return

	dupes = frappe.db.sql(
		"""
		SELECT employee, COUNT(*) c
		FROM `tabEmployee Action Centre`
		WHERE employee IS NOT NULL AND employee != ''
		GROUP BY employee
		HAVING c > 1
		""",
		as_dict=True,
	)
	deleted = 0
	for d in dupes:
		rows = frappe.db.sql(
			"""
			SELECT name, status, modified
			FROM `tabEmployee Action Centre`
			WHERE employee = %s
			ORDER BY modified DESC
			""",
			d.employee,
			as_dict=True,
		)
		keeper = max(rows, key=lambda r: (_STATUS_RANK.get(r.status or "Pending", 0), r.modified))
		for r in rows:
			if r.name == keeper.name:
				continue
			# Delete child activity log rows first
			frappe.db.sql("DELETE FROM `tabAction Centre Activity` WHERE parent=%s", r.name)
			frappe.db.sql("DELETE FROM `tabEmployee Action Centre` WHERE name=%s", r.name)
			deleted += 1
	if deleted:
		frappe.db.commit()
		print(f"Deduped {deleted} duplicate Employee Action Centre rows across {len(dupes)} groups.")
	else:
		print("No duplicate Employee Action Centre rows found.")

	# Add the unique index. `add_unique` is idempotent.
	try:
		frappe.db.add_unique(
			"Employee Action Centre",
			["employee"],
			constraint_name="unique_eac_employee",
		)
		frappe.db.commit()
		print("Added unique index on Employee Action Centre(employee).")
	except Exception as e:
		msg = str(e).lower()
		if "duplicate" in msg or "already exists" in msg:
			print(f"Unique index already present: {e}")
		else:
			raise
