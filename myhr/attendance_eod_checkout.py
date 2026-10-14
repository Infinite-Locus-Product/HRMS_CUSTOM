"""Auto check-out at end of day for IN-only employees.

When a Shift Type has `custom_auto_checkout_at_eod=1` (and the standard
`enable_auto_attendance=1`), this daily scheduler ensures every Active employee
on that shift who logged an IN today but no matching OUT ends the day with:

  1. An OUT Employee Checkin at 23:59 (with shift attached) — audit closer.
  2. An Attendance row marked Present with `out_time=23:59`. The row is either
     created here, or — if HRMS's hourly auto-attendance sweep already created
     one earlier in the day from the IN-only state — updated in place so
     `out_time` + `working_hours` reflect the synthetic close.

The HRMS-sweep-ran-first race is the common case on any site with
`working_hours_threshold_for_absent = 0`: the sweep marks Present at the
first hourly run, and previously the EOD cron's "Attendance exists → skip"
guard then silently bailed without inserting the OUT, leaving an orphan
in-time-only Attendance row. Now we co-exist: the audit Checkin always lands
and the Attendance row gets its OUT regardless of who created it.

Skips:
  - Holidays on the employee's holiday_list.
  - Active approved Leave Applications covering today.
  - Days that already have a complete IN+OUT pair (count(OUT) >= count(IN)).
  - Days whose existing Attendance row already has `out_time` set.

Per-employee fault tolerance with savepoints (matches `_auto_checkin`):
one bad row doesn't abort the rest of the loop.
"""

import frappe
from frappe.utils import cint, get_datetime, getdate

AUTO_PRESENT_DEVICE = "myHR Auto"


def _shift_types_with_eod_enabled():
	return frappe.db.sql(
		"""SELECT name FROM `tabShift Type`
		   WHERE enable_auto_attendance=1 AND custom_auto_checkout_at_eod=1""",
		as_dict=True,
	)


def _employees_on_shift(shift_type, on_date):
	"""Active employees on `shift_type` for `on_date`.

	Match if `Employee.default_shift = shift_type` OR if there's an active
	submitted Shift Assignment covering `on_date`. Returns a deduped set of
	employee names.
	"""
	by_default = frappe.get_all(
		"Employee",
		filters={"status": "Active", "default_shift": shift_type},
		pluck="name",
	)
	by_assignment = frappe.db.sql_list(
		"""SELECT sa.employee
		   FROM `tabShift Assignment` sa
		   JOIN `tabEmployee` e ON e.name = sa.employee
		   WHERE sa.shift_type=%(st)s AND sa.docstatus=1 AND sa.status='Active'
		     AND sa.start_date <= %(d)s
		     AND (sa.end_date IS NULL OR sa.end_date >= %(d)s)
		     AND e.status='Active'""",
		{"st": shift_type, "d": on_date},
	)
	return set(by_default) | set(by_assignment)


def _is_holiday(employee, on_date):
	hol_list = frappe.db.get_value("Employee", employee, "holiday_list")
	if not hol_list:
		# Fallback to the company-level default holiday list.
		company = frappe.db.get_value("Employee", employee, "company")
		hol_list = frappe.db.get_value("Company", company, "default_holiday_list") if company else None
	if not hol_list:
		return False
	return bool(
		frappe.db.exists(
			"Holiday",
			{"parent": hol_list, "holiday_date": on_date},
		)
	)


def _is_on_leave(employee, on_date):
	"""True iff `employee` has a submitted approved Leave Application
	covering `on_date`. We don't distinguish half-day vs full-day — even a
	half-day leave is enough reason to skip the synthetic OUT (HR can revise
	manually if half-day + WFH is the intent)."""
	return bool(
		frappe.db.sql(
			"""SELECT 1 FROM `tabLeave Application`
			   WHERE employee=%(emp)s
			     AND docstatus=1
			     AND status='Approved'
			     AND from_date <= %(d)s AND to_date >= %(d)s
			   LIMIT 1""",
			{"emp": employee, "d": on_date},
		)
	)


def _needs_synthetic_out(employee, on_date):
	"""True iff `employee` has more INs than OUTs on `on_date`. Counting
	rather than ordering keeps the logic simple even when a stray duplicate
	OUT sneaks in (defensive against bad device data)."""
	row = frappe.db.sql(
		"""SELECT
		     SUM(CASE WHEN log_type='IN'  THEN 1 ELSE 0 END) AS ins,
		     SUM(CASE WHEN log_type='OUT' THEN 1 ELSE 0 END) AS outs
		   FROM `tabEmployee Checkin`
		   WHERE employee=%(emp)s AND DATE(`time`)=%(d)s""",
		{"emp": employee, "d": on_date},
		as_dict=True,
	)
	if not row:
		return False
	ins = cint((row[0] or {}).get("ins") or 0)
	outs = cint((row[0] or {}).get("outs") or 0)
	return ins > outs


def _earliest_in_time(employee, on_date):
	"""Earliest IN Checkin time for `employee` on `on_date`, or None."""
	row = frappe.db.sql(
		"""SELECT MIN(`time`) AS t FROM `tabEmployee Checkin`
		   WHERE employee=%(emp)s AND log_type='IN' AND DATE(`time`)=%(d)s""",
		{"emp": employee, "d": on_date},
		as_dict=True,
	)
	return row[0]["t"] if row and row[0]["t"] else None


def _existing_attendance(employee, on_date):
	"""Return the (employee, on_date) Attendance row if one is on file, else
	None. Excludes Cancelled (docstatus=2). We pick the most recently
	modified row defensively in case two ended up alongside each other."""
	rows = frappe.db.sql(
		"""SELECT name, status, docstatus, in_time, out_time, shift, working_hours
		   FROM `tabAttendance`
		   WHERE employee=%(emp)s AND attendance_date=%(d)s AND docstatus != 2
		   ORDER BY modified DESC LIMIT 1""",
		{"emp": employee, "d": on_date}, as_dict=True,
	)
	return rows[0] if rows else None


def _close_existing_attendance(att_row, out_dt, in_time, shift_type):
	"""Update an existing Attendance row created by HRMS's sweep so the
	synthetic OUT actually closes the day. Handles both draft and submitted
	rows — submitted rows take `db_set` writes (no validate replay) which is
	fine because we're filling in fields, not changing structural state.

	Returns the Attendance name written."""
	working_hours = max(0, (out_dt - in_time).total_seconds() / 3600.0)
	doc = frappe.get_doc("Attendance", att_row.name)
	if doc.docstatus == 1:
		# Submitted row — use db_set so we don't trip the immutability guard
		# on a submitted Attendance.
		doc.db_set("out_time", out_dt, update_modified=False)
		doc.db_set("working_hours", working_hours, update_modified=False)
		# Promote status to Present only if HRMS left it Absent/Half Day from
		# the IN-only state. Leave it alone if HR already marked something
		# explicit (e.g. On Leave, Work From Home).
		if (doc.status or "") in ("Absent", "Half Day", "Present"):
			doc.db_set("status", "Present", update_modified=False)
		if shift_type and not doc.shift:
			doc.db_set("shift", shift_type, update_modified=False)
	else:
		doc.out_time = out_dt
		doc.working_hours = working_hours
		if (doc.status or "") in ("Absent", "Half Day", "Present", ""):
			doc.status = "Present"
		if shift_type and not doc.shift:
			doc.shift = shift_type
		doc.save(ignore_permissions=True)
		doc.submit()
	return doc.name


def _insert_eod_artifacts(employee, on_date, shift_type, existing_att):
	"""Close the day for an IN-only employee: synthetic OUT Checkin + either
	a fresh Attendance row, or an in-place update to one HRMS's sweep already
	created. Caller owns the savepoint + rollback.

	OUT Checkin: HRMS's `Employee Checkin.validate()` calls `fetch_shift()`
	which nullifies any shift we pre-set because 23:59 falls outside the
	shift window — so we `db_set` shift after insert.

	Attendance: HRMS's `process_auto_attendance` only pairs Checkins inside
	the shift window; a 23:59 OUT would be ignored and the day would fall
	through to Absent under any non-zero `working_hours_threshold_for_absent`.
	So we own the Attendance row directly.
	"""
	out_dt = get_datetime(f"{on_date} 23:59:00")
	in_time = _earliest_in_time(employee, on_date) or get_datetime(f"{on_date} 00:00:00")

	# 1. Synthetic OUT Checkin for audit
	ck = frappe.get_doc({
		"doctype": "Employee Checkin",
		"employee": employee,
		"log_type": "OUT",
		"time": out_dt,
		"device_id": AUTO_PRESENT_DEVICE,
	})
	ck.insert(ignore_permissions=True)
	ck.db_set("shift", shift_type, update_modified=False)

	# 2. Attendance — update existing or insert new
	if existing_att:
		att_name = _close_existing_attendance(existing_att, out_dt, in_time, shift_type)
	else:
		working_hours = max(0, (out_dt - in_time).total_seconds() / 3600.0)
		att = frappe.get_doc({
			"doctype": "Attendance",
			"employee": employee,
			"attendance_date": on_date,
			"shift": shift_type,
			"status": "Present",
			"in_time": in_time,
			"out_time": out_dt,
			"working_hours": working_hours,
		})
		att.insert(ignore_permissions=True)
		att.submit()
		att_name = att.name
	return ck.name, att_name


def auto_checkout_at_eod(on_date=None):
	"""Daily cron entrypoint. Iterates eligible Shift Types and inserts the
	synthetic OUT for each IN-only employee.

	`on_date` defaults to today (the cron's natural meaning). Pass an explicit
	date string ('YYYY-MM-DD') to backfill a specific past day — useful when
	the row to repair predates a code fix:

	    bench --site <s> execute myhr.attendance_eod_checkout.auto_checkout_at_eod \\
	      --kwargs '{"on_date": "2026-05-14"}'
	"""
	on_date = getdate(on_date) if on_date else getdate()
	shifts = _shift_types_with_eod_enabled()
	if not shifts:
		return

	inserted = updated = skipped_holiday = skipped_leave = skipped_complete = skipped_paired = failed = 0
	for st in shifts:
		shift_name = st["name"]
		for emp in _employees_on_shift(shift_name, on_date):
			savepoint = f"eod_out_{emp}".replace("-", "_").replace(" ", "_")[:60]
			try:
				frappe.db.savepoint(savepoint)
				if _is_holiday(emp, on_date):
					skipped_holiday += 1
					continue
				if _is_on_leave(emp, on_date):
					skipped_leave += 1
					continue

				# If the day is already closed (OUT paired with INs, or
				# Attendance has out_time set), there's nothing to do.
				if not _needs_synthetic_out(emp, on_date):
					skipped_paired += 1
					continue
				existing_att = _existing_attendance(emp, on_date)
				if existing_att and existing_att.out_time:
					skipped_complete += 1
					continue

				ck_name, att_name = _insert_eod_artifacts(
					emp, on_date, shift_name, existing_att,
				)
				if existing_att:
					updated += 1
				else:
					inserted += 1
				frappe.db.commit()
				frappe.logger().info(
					f"myhr.attendance_eod_checkout: Checkin {ck_name} + "
					f"Attendance {att_name} ({'updated' if existing_att else 'inserted'}) "
					f"for {emp} on shift {shift_name}"
				)
			except Exception:
				failed += 1
				try:
					frappe.db.rollback(save_point=savepoint)
				except Exception:
					pass
				frappe.log_error(
					title=f"myHR attendance_eod_checkout failed for {emp}",
					message=frappe.get_traceback(),
				)

	frappe.logger().info(
		"myhr.attendance_eod_checkout summary: "
		f"inserted={inserted} updated={updated} holiday={skipped_holiday} "
		f"leave={skipped_leave} complete={skipped_complete} paired={skipped_paired} "
		f"failed={failed}"
	)
