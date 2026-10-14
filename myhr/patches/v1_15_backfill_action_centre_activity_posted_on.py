"""Backfill `posted_on` on existing Action Centre Activity rows.

Closes EAC-15. `log_activity` (employee_action_centre.py) was appending
audit rows with only `user`, `action`, `details` set — relying on the
child doctype's `posted_on` schema default of "Now". That default is
only evaluated on `db_insert` of a brand-new doc; child rows appended to
an already-saved parent are inserted via `save_new_table_rows()` which
sets `creation` / `modified` but does not re-apply field defaults. The
result was a "Posted On" column that rendered blank in the activity log
grid for every row across the system.

The controller has been fixed to set `posted_on = now_datetime()` at
append time, but rows already in the DB stay NULL forever unless we
backfill. The row's own `creation` is the closest available proxy for
when the activity actually happened (rows are immutable after insert).
"""
import frappe


def execute():
	updated = frappe.db.sql(
		"""
		UPDATE `tabAction Centre Activity`
		SET posted_on = creation
		WHERE posted_on IS NULL
		""",
	)
	frappe.db.commit()
	# Mariadb returns rowcount via the cursor; recompute for the log line.
	remaining = frappe.db.sql(
		"SELECT COUNT(*) FROM `tabAction Centre Activity` WHERE posted_on IS NULL"
	)[0][0]
	total = frappe.db.sql("SELECT COUNT(*) FROM `tabAction Centre Activity`")[0][0]
	print(
		f"Backfilled posted_on on Action Centre Activity rows; "
		f"{total - remaining}/{total} now have a timestamp."
	)
