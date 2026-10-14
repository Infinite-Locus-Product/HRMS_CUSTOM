"""Drop the legacy `Policy Action Task` child doctype AND its underlying SQL table.

Closes C-13 from the 2026-04-26 audit. The split-migration patch
(`v1_1_split_policy_acknowledgement.py`) moved every row to the standalone
`Policy Acknowledgement` doctype. No code path reads `Policy Action Task` any
more; live row count is 0. Keeping the doctype on disk is dead weight and
muddies the schema.

`frappe.delete_doc("DocType", ...)` only removes the metadata. We also need to
drop the SQL table itself; otherwise `tabPolicy Action Task` lingers as a
vestige forever. Defensive: refuse to drop if any rows remain.
"""
import frappe


def execute():
	doctype_present = frappe.db.exists("DocType", "Policy Action Task")
	table_present = bool(frappe.db.sql("SHOW TABLES LIKE 'tabPolicy Action Task'"))

	if not doctype_present and not table_present:
		print("Policy Action Task already gone; nothing to do.")
		return

	# Defensive: refuse to drop if any rows remain (covers re-introduced sites).
	if table_present:
		row_count = frappe.db.sql("SELECT COUNT(*) FROM `tabPolicy Action Task`")[0][0]
		if row_count:
			print(
				f"Refusing to drop Policy Action Task — table still has {row_count} rows. "
				"Re-run v1_1_split_policy_acknowledgement first, then this patch."
			)
			return

	if doctype_present:
		frappe.delete_doc("DocType", "Policy Action Task", force=1, ignore_permissions=True)
		print("Removed Policy Action Task DocType metadata.")

	# Drop the SQL table after the metadata is gone (so Frappe can't try to
	# reference the doctype during the DDL).
	if table_present:
		frappe.db.sql_ddl("DROP TABLE `tabPolicy Action Task`")
		print("Dropped tabPolicy Action Task table.")

	frappe.db.commit()
