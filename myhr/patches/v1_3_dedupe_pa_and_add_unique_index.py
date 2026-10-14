"""Dedupe duplicate Policy Acknowledgement rows and add a unique index on
`(employee, hr_policy, policy_version)`.

Closes C-1 from the 2026-04-26 audit. Without this index, the
`frappe.db.exists` + `insert` pattern in `ensure_policy_acknowledgements_for_employee`
and `after_save_hr_policy` is racy under concurrent saves and can produce
duplicate Pending rows that the application has no way to merge.

Dedupe rule (deterministic, audit-preserving):
- Group rows by `(employee, hr_policy, policy_version)`.
- Within a group, prefer the row with the strongest status:
  Acknowledged > Superseded > Pending. If multiple rows share the strongest
  status, keep the earliest `creation` (first-write-wins).
- Delete the losers via raw SQL (bypasses validate; deletion is a sanctioned
  cleanup path and the row is unreachable anyway).
"""
import frappe


_STATUS_RANK = {"Acknowledged": 3, "Superseded": 2, "Pending": 1}


def execute():
	if not frappe.db.exists("DocType", "Policy Acknowledgement"):
		print("Policy Acknowledgement doctype not present; skipping.")
		return

	# 1. Find duplicate groups
	dupes = frappe.db.sql(
		"""
		SELECT employee, hr_policy, policy_version, COUNT(*) c
		FROM `tabPolicy Acknowledgement`
		GROUP BY employee, hr_policy, policy_version
		HAVING c > 1
		""",
		as_dict=True,
	)
	deleted = 0
	for d in dupes:
		rows = frappe.db.sql(
			"""
			SELECT name, status, creation
			FROM `tabPolicy Acknowledgement`
			WHERE employee=%(e)s AND hr_policy=%(p)s AND policy_version=%(v)s
			ORDER BY creation ASC
			""",
			{"e": d.employee, "p": d.hr_policy, "v": d.policy_version},
			as_dict=True,
		)
		# Pick the keeper: highest status rank, ties broken by earliest creation.
		keeper = max(rows, key=lambda r: (_STATUS_RANK.get(r.status, 0), -r.creation.timestamp()))
		for r in rows:
			if r.name == keeper.name:
				continue
			frappe.db.sql("DELETE FROM `tabPolicy Acknowledgement` WHERE name=%s", r.name)
			deleted += 1
	if deleted:
		frappe.db.commit()
		print(f"Deduped {deleted} duplicate Policy Acknowledgement rows across {len(dupes)} groups.")
	else:
		print("No duplicate Policy Acknowledgement rows found.")

	# 2. Add the unique index. `add_unique` is idempotent (Frappe checks for existence).
	try:
		frappe.db.add_unique(
			"Policy Acknowledgement",
			["employee", "hr_policy", "policy_version"],
			constraint_name="unique_pa_employee_policy_version",
		)
		frappe.db.commit()
		print("Added unique index on Policy Acknowledgement(employee, hr_policy, policy_version).")
	except Exception as e:
		# If a future migration already added the index, swallow the duplicate-key error.
		msg = str(e).lower()
		if "duplicate" in msg or "already exists" in msg:
			print(f"Unique index already present: {e}")
		else:
			raise
