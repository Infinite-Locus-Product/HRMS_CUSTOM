"""Fixxly Leave Policy — one-shot ERPNext/HRMS setup (Steps 1-3 of the guide).

Creates the Leave Types, Leave Period and Leave Policy described in the Fixxly
Leave Policy (effective 1 Aug 2026). Idempotent — re-running skips anything that
already exists. Standard ERPNext only; no code customization.

RUN (on the target site):
    printf "%s\\n" \\
      "p='/abs/path/to/setup_fixxly_leave_policy.py'" \\
      "exec(compile(open(p).read(), p, 'exec'), {'__name__':'__main__'})" \\
      | bench --site <your-site> console

Edit CONFIG below before running.
"""

import frappe

# ---------------------------------------------------------------------------
# CONFIG — edit these for your site
# ---------------------------------------------------------------------------
CONFIG = {
	"company": "FIXXLY PRIVATE LIMITED",
	"year": 2026,
	"holiday_list": None,            # e.g. "Fixxly Holiday List 2026"; None = skip linking
	"effective_from": "2026-08-01",  # policy start; used only if ASSIGN_TO_ALL_ACTIVE
	"encashment_component": "Leave Encashment",
	"ASSIGN_TO_ALL_ACTIVE": False,   # True -> also create+submit assignments for all active employees
}

POLICY_TITLE = f"Fixxly Leave Policy {CONFIG['year']}"
# Leave Period autonames (HR-LPR-YYYY-#####), so its real name can't be forced;
# ensure_leave_period() resolves/creates it and returns the actual name.
log = []

# ---------------------------------------------------------------------------
# Leave Types — (name, {fields})
# ---------------------------------------------------------------------------
LEAVE_TYPES = [
	("Casual / Sick Leave", {
		"max_leaves_allowed": 12,
		"max_continuous_days_allowed": 2,
		"is_earned_leave": 1,
		"earned_leave_frequency": "Monthly",
		"allocate_on_day": "First Day",
		"rounding": "0.5",
		"is_carry_forward": 0,
		"allow_encashment": 0,
	}),
	("Earned Leave", {
		"max_leaves_allowed": 18,
		"is_earned_leave": 1,
		"earned_leave_frequency": "Monthly",
		"allocate_on_day": "First Day",
		"rounding": "0.5",
		"is_carry_forward": 1,
		"maximum_carry_forwarded_leaves": 30,
		"allow_encashment": 1,
		"max_encashable_leaves": 30,
		"earning_component": CONFIG["encashment_component"],
	}),
	("Maternity Leave", {
		"max_leaves_allowed": 182,
		"applicable_after": 90,
		"include_holiday": 1,
		"allow_over_allocation": 1,
	}),
	("Paternity Leave", {
		"max_leaves_allowed": 12,
		"include_holiday": 0,
	}),
	("Bereavement Leave", {
		"max_leaves_allowed": 5,
		"max_continuous_days_allowed": 5,
	}),
	("Marriage Leave", {
		"max_leaves_allowed": 5,
	}),
	("Compensatory Off", {
		"is_compensatory": 1,
	}),
]

# Annual allocations that go into the Leave Policy (Compensatory Off / LWP excluded).
POLICY_ALLOCATIONS = [
	("Casual / Sick Leave", 12),
	("Earned Leave", 18),
	("Maternity Leave", 182),
	("Paternity Leave", 12),
	("Bereavement Leave", 5),
	("Marriage Leave", 5),
]


def ensure_encashment_component():
	name = CONFIG["encashment_component"]
	if frappe.db.exists("Salary Component", name):
		return
	sc = frappe.new_doc("Salary Component")
	sc.salary_component = name
	sc.salary_component_abbr = "LE"
	sc.type = "Earning"
	sc.is_tax_applicable = 1
	sc.flags.ignore_permissions = True
	sc.insert(ignore_permissions=True)
	log.append(f"created Salary Component: {name}")


def ensure_leave_types():
	# Confirm the built-in LWP type exists (do not create/modify it here).
	if not frappe.db.exists("Leave Type", {"is_lwp": 1}):
		log.append("WARNING: no 'Leave Without Pay' (is_lwp) Leave Type found — create one in Desk.")
	for name, fields in LEAVE_TYPES:
		if frappe.db.exists("Leave Type", name):
			log.append(f"skip Leave Type (exists): {name}")
			continue
		lt = frappe.new_doc("Leave Type")
		lt.leave_type_name = name
		for k, v in fields.items():
			lt.set(k, v)
		lt.flags.ignore_permissions = True
		lt.insert(ignore_permissions=True)
		log.append(f"created Leave Type: {name}")


def ensure_leave_period():
	"""Resolve or create the calendar-year Leave Period; return its actual
	(auto-generated) name. Matched by company + from_date since the name is
	system-assigned (HR-LPR-YYYY-#####)."""
	existing = frappe.db.get_value(
		"Leave Period",
		{"company": CONFIG["company"], "from_date": f"{CONFIG['year']}-01-01"},
		"name",
	)
	if existing:
		log.append(f"skip Leave Period (exists): {existing}")
		return existing
	lp = frappe.new_doc("Leave Period")
	lp.from_date = f"{CONFIG['year']}-01-01"
	lp.to_date = f"{CONFIG['year']}-12-31"
	lp.company = CONFIG["company"]
	lp.is_active = 1
	if CONFIG["holiday_list"] and frappe.db.exists("Holiday List", CONFIG["holiday_list"]):
		lp.optional_holiday_list = CONFIG["holiday_list"]
	lp.flags.ignore_permissions = True
	lp.insert(ignore_permissions=True)
	log.append(f"created Leave Period: {lp.name}")
	return lp.name


def ensure_leave_policy():
	if frappe.db.exists("Leave Policy", {"title": POLICY_TITLE}):
		log.append(f"skip Leave Policy (exists): {POLICY_TITLE}")
		return frappe.db.get_value("Leave Policy", {"title": POLICY_TITLE}, "name")
	pol = frappe.new_doc("Leave Policy")
	pol.title = POLICY_TITLE
	for leave_type, annual in POLICY_ALLOCATIONS:
		if not frappe.db.exists("Leave Type", leave_type):
			log.append(f"WARNING: Leave Type missing, skipped policy row: {leave_type}")
			continue
		pol.append("leave_policy_details", {
			"leave_type": leave_type,
			"annual_allocation": annual,
		})
	pol.flags.ignore_permissions = True
	pol.insert(ignore_permissions=True)
	log.append(f"created Leave Policy: {POLICY_TITLE} ({pol.name})")
	return pol.name


def assign_to_all_active(policy_name, leave_period_name):
	emps = frappe.get_all("Employee",
		filters={"status": "Active", "company": CONFIG["company"]}, pluck="name")
	made = 0
	skipped = 0
	for i, emp in enumerate(emps):
		if frappe.db.exists("Leave Policy Assignment", {
			"employee": emp, "leave_policy": policy_name, "docstatus": 1,
		}):
			skipped += 1
			continue
		# Per-employee savepoint: a conflict (e.g. employee already has an
		# overlapping assignment) skips that one employee without aborting
		# the whole batch or corrupting the transaction.
		sp = f"lpa_{i}"
		frappe.db.savepoint(sp)
		try:
			a = frappe.new_doc("Leave Policy Assignment")
			a.employee = emp
			a.company = CONFIG["company"]
			a.leave_policy = policy_name
			a.assignment_based_on = "Leave Period"
			a.leave_period = leave_period_name
			a.effective_from = CONFIG["effective_from"]
			a.flags.ignore_permissions = True
			a.insert(ignore_permissions=True)
			a.submit()
			made += 1
		except Exception as e:
			frappe.db.rollback(save_point=sp)
			skipped += 1
			log.append(f"  skip assignment for {emp}: {str(e)[:80]}")
	log.append(f"assignments submitted: {made}, skipped: {skipped} (of {len(emps)} active employees)")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if not frappe.db.exists("Company", CONFIG["company"]):
	raise SystemExit(f"Company not found: {CONFIG['company']!r} — fix CONFIG['company'].")

ensure_encashment_component()
ensure_leave_types()
period_name = ensure_leave_period()
policy = ensure_leave_policy()
if CONFIG["ASSIGN_TO_ALL_ACTIVE"] and policy and period_name:
	assign_to_all_active(policy, period_name)

frappe.db.commit()

print("=== Fixxly Leave Policy setup ===")
for line in log:
	print("  -", line)
print("=== done (committed) ===")
