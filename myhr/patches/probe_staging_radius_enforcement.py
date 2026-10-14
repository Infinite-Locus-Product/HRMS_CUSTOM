"""Diagnostic — why an Employee Checkin didn't trip the radius enforcement.

NOT a migration patch. NOT registered in patches.txt. Stand-alone diagnostic.

Stock HRMS's `validate_distance_from_shift_location` (apps/hrms/hrms/hr/
doctype/employee_checkin/employee_checkin.py) returns silently (no radius
enforced) on five branches. Two are explicit policy (geolocation tracking off,
employee bypass flag). The other three are configuration gaps that look
identical to "no check happened" with no error in the log:

  - Active Shift Assignment with `shift_location` set must exist for the
    employee + the shift resolved on the checkin. Not the same as
    `Employee.default_shift`.
  - The checkin's `shift` must have been resolved (via Shift Assignment lookup
    on the checkin time). Empty `shift` → empty assignment query → silent skip.
  - `Shift Location.checkin_radius <= 0` → silent skip.

Run via:

    bench --site staging.elixiirfoods.com execute \
      myhr.patches.probe_staging_radius_enforcement.execute \
      --kwargs '{"employee": "HR-EMP-XXXX"}'

Or, to inspect a specific Employee Checkin row (most precise):

    bench --site staging.elixiirfoods.com execute \
      myhr.patches.probe_staging_radius_enforcement.execute \
      --kwargs '{"checkin": "EMP-CKIN-XXXX"}'
"""

import frappe


def _site_setting(key: str):
	v = frappe.db.get_single_value("HR Settings", key)
	return v


def _check_employee_flags(employee: str) -> None:
	emp = frappe.db.get_value(
		"Employee",
		employee,
		[
			"name",
			"employee_name",
			"status",
			"default_shift",
			"custom_bypass_geolocation_check",
		],
		as_dict=True,
	)
	if not emp:
		print(f"[!] Employee {employee} not found.")
		return None
	print(f"\n[2] Employee under test")
	print(f"    name             = {emp.name}")
	print(f"    employee_name    = {emp.employee_name}")
	print(f"    status           = {emp.status}")
	print(f"    default_shift    = {emp.default_shift}  (NOT used by radius check — see Shift Assignment)")
	bypass = bool(emp.custom_bypass_geolocation_check)
	print(f"    custom_bypass_geolocation_check = {emp.custom_bypass_geolocation_check}  -> bypass active: {bypass}")
	return emp


def _check_shift_assignments(employee: str, shift_type: str | None = None) -> list:
	filters = {
		"employee": employee,
		"docstatus": 1,
		"status": "Active",
	}
	if shift_type:
		filters["shift_type"] = shift_type
	rows = frappe.get_all(
		"Shift Assignment",
		filters=filters,
		fields=["name", "shift_type", "shift_location", "start_date", "end_date", "status"],
		order_by="start_date desc",
		limit=10,
	)
	print(f"\n[3] Active submitted Shift Assignment rows for {employee}"
	      f"{(' with shift_type=' + shift_type) if shift_type else ''}: {len(rows)}")
	for r in rows:
		marker = "  ← geofence linked" if r.shift_location else "  ← NO shift_location (radius will not enforce)"
		print(f"    {r.name}  shift={r.shift_type}  loc={r.shift_location!r}  {r.start_date}..{r.end_date or '∞'}  {r.status}{marker}")
	return rows


def _check_shift_locations(names: list[str]) -> None:
	if not names:
		return
	rows = frappe.db.sql(
		"""SELECT name, checkin_radius, latitude, longitude
		   FROM `tabShift Location`
		   WHERE name IN %(names)s""",
		{"names": tuple(names)},
		as_dict=True,
	)
	print(f"\n[4] Shift Location rows referenced above ({len(rows)}):")
	for r in rows:
		bad_radius = (r.checkin_radius or 0) <= 0
		bad_coords = not (r.latitude and r.longitude)
		warn = ""
		if bad_radius:
			warn = "  ← radius <= 0 → silent skip"
		elif bad_coords:
			warn = "  ← no centre coordinates → radius cannot enforce"
		print(f"    {r.name}  radius={r.checkin_radius}m  centre=({r.latitude},{r.longitude}){warn}")


def _inspect_checkin(checkin_name: str) -> None:
	doc = frappe.db.get_value(
		"Employee Checkin",
		checkin_name,
		["name", "employee", "time", "log_type", "device_id", "shift",
		 "latitude", "longitude"],
		as_dict=True,
	)
	if not doc:
		print(f"[!] Employee Checkin {checkin_name} not found.")
		return
	print(f"\n[5] Inspected Employee Checkin row")
	print(f"    name      = {doc.name}")
	print(f"    employee  = {doc.employee}")
	print(f"    time      = {doc.time}")
	print(f"    log_type  = {doc.log_type}")
	print(f"    device_id = {doc.device_id!r}")
	print(f"    shift     = {doc.shift!r}  (must be non-empty for stock HRMS to do the radius lookup)")
	print(f"    lat/long  = {doc.latitude}, {doc.longitude}")

	# Re-run the exact stock HRMS Shift Assignment query to show what it
	# would have found.
	if not doc.shift:
		print("    [!] shift is empty → stock HRMS's Shift Assignment filter "
		      "`shift_type = self.shift` matches nothing → silent skip, "
		      "no radius enforced.")
		return
	rows = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": doc.employee,
			"shift_type": doc.shift,
			"start_date": ["<=", doc.time],
			"shift_location": ["is", "set"],
			"docstatus": 1,
			"status": "Active",
		},
		or_filters=[["end_date", ">=", doc.time], ["end_date", "is", "not set"]],
		pluck="shift_location",
	)
	print(f"    stock HRMS Shift Assignment match (shift_location-bearing) → {rows}")
	if not rows:
		print("    [!] No Shift Assignment with shift_location covers this checkin "
		      "→ stock HRMS returns silently, no radius enforced.")
	else:
		loc = frappe.db.get_value(
			"Shift Location", rows[0],
			["checkin_radius", "latitude", "longitude"], as_dict=True,
		)
		print(f"    Shift Location {rows[0]} → radius={loc.checkin_radius}m centre=({loc.latitude},{loc.longitude})")
		if (loc.checkin_radius or 0) <= 0:
			print("    [!] checkin_radius <= 0 → stock HRMS returns silently.")


def execute(employee: str | None = None, checkin: str | None = None) -> None:
	print("=" * 72)
	print("Employee Checkin radius enforcement diagnostic")
	print("=" * 72)

	# 1. Site-wide settings
	print(f"\n[1] Site-wide settings (HR Settings)")
	allow_geo = _site_setting("allow_geolocation_tracking")
	print(f"    allow_geolocation_tracking = {allow_geo!r}")
	if not allow_geo:
		print("    [!] tracking OFF site-wide → stock HRMS returns immediately. "
		      "Radius is never enforced for anyone.")

	if checkin:
		_inspect_checkin(checkin)
		return

	if not employee:
		# Pick the most recently created Active employee with user_id for the
		# generic case.
		row = frappe.db.sql(
			"SELECT name FROM `tabEmployee` WHERE status='Active' AND user_id "
			"IS NOT NULL AND user_id != '' ORDER BY creation DESC LIMIT 1",
			as_dict=True,
		)
		if row:
			employee = row[0]["name"]
			print(f"\n[note] No employee= passed; using most recent active employee: {employee}")
		else:
			print("\n[!] Pass employee= or checkin= to continue.")
			return

	emp = _check_employee_flags(employee)
	if not emp:
		return
	if emp.get("custom_bypass_geolocation_check"):
		print("    [!] bypass flag is ON for this employee → myhr's override "
		      "short-circuits the radius check. lat/long still required + captured.")
	assignments = _check_shift_assignments(employee, emp.get("default_shift"))
	with_loc = [a for a in assignments if a.get("shift_location")]
	if not with_loc:
		print("    [!] NO assignment carries a shift_location → stock HRMS "
		      "returns silently. Configure Shift Assignment.shift_location on "
		      "the employee's active assignment to enforce a radius.")
	_check_shift_locations([a["shift_location"] for a in with_loc])

	print("\n[checklist] If employees check in outside the radius:")
	print("  1. HR Settings → allow_geolocation_tracking must be ticked.")
	print("  2. Employee.custom_bypass_geolocation_check must be OFF for the affected employee.")
	print("  3. Employee must have a submitted Shift Assignment whose shift_location is set.")
	print("  4. Shift Location.checkin_radius must be > 0 metres.")
	print("  5. The latest Employee Checkin row's `shift` field must be populated (auto-resolved by HRMS from Shift Assignment).")
	print("  6. Lat/long captured on the Checkin (always required — even bypass=1 employees must send coords).")
