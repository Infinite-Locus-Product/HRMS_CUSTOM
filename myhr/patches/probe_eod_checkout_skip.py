"""Diagnostic — why the 23:55 EOD cron didn't insert an OUT for an
employee who had an IN today.

Standalone (not in patches.txt). Read-only.

Five reasons `auto_checkout_at_eod` will skip an employee:
  1. The shift doesn't have `enable_auto_attendance=1 AND
     custom_auto_checkout_at_eod=1`.
  2. The employee isn't on that shift (neither default_shift nor active
     Shift Assignment matches on the target date).
  3. Today is a holiday on the employee's holiday list.
  4. Today is covered by an approved Leave Application.
  5. *** Attendance row already exists for (employee, date) — most common
     cause of the silent skip when HRMS's hourly sweep ran earlier in the
     day and pre-created the Attendance from the IN-only state. ***

Usage — pass the IN Checkin row:

    bench --site staging.elixiirfoods.com execute \
      myhr.patches.probe_eod_checkout_skip.execute \
      --kwargs '{"checkin": "EMP-CKIN-05-2026-000001"}'
"""

import frappe


def execute(checkin: str | None = None, employee: str | None = None,
            on_date: str | None = None):
	print("=" * 72)
	print("EOD auto-checkout skip diagnostic")
	print("=" * 72)

	# Resolve employee + date
	if checkin:
		row = frappe.db.get_value(
			"Employee Checkin", checkin,
			["employee", "time", "log_type", "shift", "device_id"], as_dict=True,
		)
		if not row:
			print(f"[!] Checkin {checkin} not found.")
			return
		employee = row.employee
		on_date = frappe.utils.getdate(row.time)
		print(f"\n[input] checkin={checkin}")
		print(f"  log_type={row.log_type}  time={row.time}  shift={row.shift!r}  device={row.device_id!r}")
	elif not (employee and on_date):
		print("[!] Pass either checkin= OR (employee= + on_date=)")
		return
	else:
		on_date = frappe.utils.getdate(on_date)

	print(f"\n[resolved] employee={employee}  on_date={on_date}")

	# 1. All Checkins for this employee on this date
	checkins = frappe.db.sql(
		"""SELECT name, log_type, `time`, shift, device_id
		   FROM `tabEmployee Checkin`
		   WHERE employee=%(emp)s AND DATE(`time`)=%(d)s
		   ORDER BY `time`""",
		{"emp": employee, "d": on_date}, as_dict=True,
	)
	print(f"\n[1] Checkins on {on_date}: {len(checkins)}")
	for c in checkins:
		print(f"    {c.log_type:3s}  {c.time}  shift={c.shift!r}  device={c.device_id!r}  ({c.name})")

	# 2. Attendance row for this employee on this date
	att_rows = frappe.db.sql(
		"""SELECT name, status, docstatus, shift, in_time, out_time,
		          working_hours, creation, modified
		   FROM `tabAttendance`
		   WHERE employee=%(emp)s AND attendance_date=%(d)s""",
		{"emp": employee, "d": on_date}, as_dict=True,
	)
	print(f"\n[2] Attendance rows: {len(att_rows)}")
	for a in att_rows:
		print(f"    {a.name}  status={a.status}  docstatus={a.docstatus}  shift={a.shift!r}")
		print(f"      in={a.in_time}  out={a.out_time}  hrs={a.working_hours}")
		print(f"      created={a.creation}  modified={a.modified}")

	if att_rows and not any(c.log_type == "OUT" for c in checkins):
		print("    *** HYPOTHESIS MATCH ***")
		print("    Attendance exists + no OUT Checkin in audit log.")
		print("    The 23:55 EOD cron's `_attendance_exists` guard returned True")
		print("    so it skipped this employee. The Attendance was created by")
		print("    HRMS's hourly `process_auto_attendance` sweep earlier in the day.")

	# 3. Shift resolution + EOD toggles
	shift_name = None
	if checkins:
		shift_name = checkins[0].shift  # prefer the IN's resolved shift
	if not shift_name:
		shift_name = frappe.db.get_value("Employee", employee, "default_shift")
	print(f"\n[3] Resolved shift candidate: {shift_name!r}")
	if shift_name:
		st = frappe.db.get_value(
			"Shift Type", shift_name,
			["enable_auto_attendance", "custom_auto_checkout_at_eod",
			 "working_hours_threshold_for_absent",
			 "working_hours_threshold_for_half_day"],
			as_dict=True,
		)
		print(f"    enable_auto_attendance         = {st.enable_auto_attendance}")
		print(f"    custom_auto_checkout_at_eod    = {st.custom_auto_checkout_at_eod}")
		print(f"    working_hours_threshold_for_absent   = {st.working_hours_threshold_for_absent}")
		print(f"    working_hours_threshold_for_half_day = {st.working_hours_threshold_for_half_day}")
		if not st.custom_auto_checkout_at_eod:
			print("    [!] Toggle is OFF on this shift → cron never tried to OUT this employee.")

	# 4. Cron registration
	hooks = frappe.get_hooks("scheduler_events") or {}
	cron = (hooks.get("cron") or {})
	print(f"\n[4] Scheduler registration")
	for spec, fns in cron.items():
		if "auto_checkout_at_eod" in str(fns):
			print(f"    cron `{spec}`: {fns}")
			break
	else:
		print("    [!] No cron entry found for auto_checkout_at_eod. App not deployed yet?")

	# 5. Has the cron run today? Check Error Log for related failures.
	err = frappe.db.sql(
		"""SELECT name, creation
		   FROM `tabError Log`
		   WHERE method LIKE '%%auto_checkout_at_eod%%'
		      OR error LIKE '%%attendance_eod_checkout%%'
		   ORDER BY creation DESC LIMIT 5""",
		as_dict=True,
	)
	print(f"\n[5] Recent Error Log rows mentioning EOD cron: {len(err)}")
	for e in err:
		print(f"    {e.creation}  {e.name}")

	print("\n[suggestion]")
	if att_rows and not any(c.log_type == "OUT" for c in checkins):
		print("  Confirmed silent-skip bug. Fix: change _attendance_exists to ignore")
		print("  Attendance rows that have no out_time, so the cron still inserts")
		print("  the OUT Checkin and updates the Attendance.")
	else:
		print("  No clear silent-skip pattern. Inspect [3] Shift toggle + [4] cron registration.")
