"""Backfill `Holiday.custom_holiday_type` to match `weekly_off`.

Closes HOL-4. On at least one demo site, all 52 Sunday entries on
`Holidays 2026` are `weekly_off=1` but `custom_holiday_type='Optional'`.
That's wrong — Sundays are not optional leave dates. With the data in
that state, `validate_optional_leave_dates` would accept Sunday as a
valid optional-leave target, defeating the gate.

The new `validate_holiday` hook fixes new saves, but pre-existing rows
were never re-saved. This patch sweeps every Holiday row and corrects
the type:

  - weekly_off=1 → custom_holiday_type='Weekly Off' (fix Sundays mislabel)
  - weekly_off=0 + custom_holiday_type blank → 'Fixed' (conservative default)
  - weekly_off=0 + custom_holiday_type='Weekly Off' → 'Fixed'
    (rare contradiction; pick the safer side and let HR re-label if needed)
"""
import frappe


def execute():
	if not frappe.db.exists("DocType", "Holiday"):
		print("Holiday doctype not present; skipping.")
		return

	# Defensive: only proceed if `custom_holiday_type` exists on the schema
	# (myhr provides this Custom Field via setup.py:_ensure_custom_fields).
	if not frappe.db.exists("Custom Field", "Holiday-custom_holiday_type"):
		print("Custom Field Holiday-custom_holiday_type not yet installed; skipping.")
		return

	# 1. weekly_off=1, type != 'Weekly Off' → fix
	bad_weekly = frappe.db.sql(
		"""
		SELECT name FROM `tabHoliday`
		WHERE weekly_off = 1 AND (custom_holiday_type IS NULL OR custom_holiday_type != 'Weekly Off')
		"""
	)
	if bad_weekly:
		frappe.db.sql(
			"""
			UPDATE `tabHoliday`
			SET custom_holiday_type = 'Weekly Off', modified = NOW()
			WHERE weekly_off = 1 AND (custom_holiday_type IS NULL OR custom_holiday_type != 'Weekly Off')
			"""
		)

	# 2. weekly_off=0, type blank → Fixed
	bad_blank = frappe.db.sql(
		"""
		SELECT name FROM `tabHoliday`
		WHERE (weekly_off IS NULL OR weekly_off = 0)
		  AND (custom_holiday_type IS NULL OR custom_holiday_type = '')
		"""
	)
	if bad_blank:
		frappe.db.sql(
			"""
			UPDATE `tabHoliday`
			SET custom_holiday_type = 'Fixed', modified = NOW()
			WHERE (weekly_off IS NULL OR weekly_off = 0)
			  AND (custom_holiday_type IS NULL OR custom_holiday_type = '')
			"""
		)

	# 3. weekly_off=0, type='Weekly Off' → Fixed (contradiction)
	bad_contra = frappe.db.sql(
		"""
		SELECT name FROM `tabHoliday`
		WHERE (weekly_off IS NULL OR weekly_off = 0)
		  AND custom_holiday_type = 'Weekly Off'
		"""
	)
	if bad_contra:
		frappe.db.sql(
			"""
			UPDATE `tabHoliday`
			SET custom_holiday_type = 'Fixed', modified = NOW()
			WHERE (weekly_off IS NULL OR weekly_off = 0)
			  AND custom_holiday_type = 'Weekly Off'
			"""
		)

	frappe.db.commit()
	print(
		f"Holiday Type backfill: weekly-off-relabeled={len(bad_weekly)}, "
		f"blanks-defaulted={len(bad_blank)}, contradictions-cleared={len(bad_contra)}."
	)
