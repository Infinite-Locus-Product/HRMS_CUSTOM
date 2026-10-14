"""F-7: Move the four HR-control flags into a new "HR Controls" tab next to
Overview, refresh their descriptions, and (re)apply on every install /
migrate. Idempotent — safe to run multiple times.

The Tab Break field itself is created by `setup._ensure_custom_fields` (it's
in `MYHR_CUSTOM_FIELDS`); this patch only fixes up `insert_after` and
`description` on existing rows so older installs catch up.
"""
import frappe


LAYOUT = [
	# (fieldname, insert_after, label, description)
	("custom_hr_controls_tab", "branch", "HR Controls", ""),
	("custom_emp_directory", "custom_hr_controls_tab", "Add to Employee Directory",
	 "When checked, this employee appears in the company-wide Employee "
	 "Directory (PWA + Desk). Uncheck to hide this employee — typically used "
	 "for confidential roles like CEO. Existing directory rows are "
	 "auto-removed when this flag is cleared."),
	("custom_add_to_action_centre", "custom_emp_directory", "Add to Employee Action Centre",
	 "When checked, an Employee Action Centre row is auto-created on insert. "
	 "The Action Centre tracks the employee's mandatory document uploads "
	 "(Aadhar, PAN, education), employer history, and policy "
	 "acknowledgements. Uncheck only for system accounts that don't onboard."),
	("custom_auto_present", "custom_add_to_action_centre", "Auto Present",
	 "When checked, the scheduler auto-marks this employee Present every "
	 "weekday: IN at 09:00, OUT at 18:00 (device_id='myHR Auto'). The cron "
	 "path bypasses the policy-acknowledgement gate AND the geolocation "
	 "distance check (HR is responsible for compliance separately). "
	 "Attendance is created downstream via HRMS's hourly auto-attendance "
	 "sweep — requires the Shift Type to have 'Enable Auto Attendance' "
	 "ticked. Use for founders / senior staff who don't manually check in."),
	("custom_bypass_geolocation_check", "custom_auto_present",
	 "Bypass Geolocation Checkin Validation",
	 "When checked, this employee's manual check-ins skip the Shift "
	 "Location radius enforcement — they can check in from anywhere. "
	 "Latitude and longitude are still required and captured on every "
	 "check-in for audit. Use for founders, WFH staff, or road warriors "
	 "whose location should still be logged but who aren't tied to a fixed "
	 "office radius. Does NOT exempt the policy-acknowledgement gate or the "
	 "ownership gate — both still apply."),
]


def execute():
	for fieldname, insert_after, label, desc in LAYOUT:
		cf_name = f"Employee-{fieldname}"
		if not frappe.db.exists("Custom Field", cf_name):
			# setup._ensure_custom_fields will create it; nothing to do here.
			continue
		updates = {
			"insert_after": insert_after,
			"label": label,
			"description": desc,
		}
		frappe.db.set_value("Custom Field", cf_name, updates)
	frappe.db.commit()
	frappe.clear_cache()
