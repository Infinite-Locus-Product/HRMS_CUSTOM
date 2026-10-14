"""Seed canonical dummy/demo data for myhr (v16).

Mirrors atbhr.scripts.seed_v15 + atbhr.scripts.seed_policies (v15) so QA can
test feature parity across both apps with identical fixtures. See
docs/DUMMY_DATA.md for the canonical spec.

Entry points:
    bench --site <site> execute myhr.setup_dummies.run
    bench --site <site> execute myhr.setup_dummies.reset_and_seed

run() is idempotent — re-running on an already-seeded site is a no-op.
reset_and_seed() wipes the demo set first (see _wipe_demo_data) and re-runs.
"""

import frappe


# ---------------------------------------------------------------------------
# Canonical demo data — keep in sync with atbhr.scripts.seed_v15 / seed_policies
# ---------------------------------------------------------------------------

DEMO_EMPLOYEES = [
    # (emp_id, email, designation, reports_to, dept, auto_present, bypass_geo, in_directory)
    ("CEO",     "ceo@erpdemo.local",             "CEO",                  None,      None,         1, 1, 0),
    ("CFO",     "cfo@erpdemo.local",             "CFO",                  "CEO",     None,         1, 1, 1),
    ("HR-001",  "hrhead@erpdemo.local",          "HR Head",              "CEO",     "HR Test",    0, 0, 1),
    ("HR-002",  "hrmanager@erpdemo.local",       "HR Manager",           "HR-001",  "HR Test",    0, 0, 1),
    ("SAL-001", "salesmanager@erpdemo.local",    "Sales Manager",        "CEO",     "Sales",      0, 0, 1),
    ("SAL-002", "salesexec@erpdemo.local",       "Sales Executive",      "SAL-001", "Sales",      0, 0, 1),
    ("OPS-001", "opsmanager@erpdemo.local",      "Operations Manager",   "CEO",     "Operations", 0, 0, 1),
    ("OPS-002", "opsexec@erpdemo.local",         "Operations Executive", "OPS-001", "Operations", 0, 0, 1),
    ("MKT-001", "marketingmanager@erpdemo.local","Marketing Manager",    "CEO",     "Marketing",  0, 0, 1),
    ("MKT-002", "marketingexec@erpdemo.local",   "Marketing Executive",  "MKT-001", "Marketing",  0, 0, 1),
]

DEMO_EMPLOYEE_IDS = [row[0] for row in DEMO_EMPLOYEES]

DEMO_POLICIES = [
    # (policy_name, category, is_active, mandatory_check_in_block)
    ("Leave Policy 2024",               "Leave",    1, 0),
    ("POSH Policy (Mandatory)",         "POSH",     1, 1),
    ("Gratuity Policy",                 "Gratuity", 1, 0),
    ("Employee Data Protection Policy", "General",  1, 1),
    ("POSH 2026",                       "POSH",     1, 1),
]

DEMO_POLICY_NAMES = [row[0] for row in DEMO_POLICIES]

# Drives Employee.custom_allow_view_reporting via the new perm model in
# myhr.permissions. Replaces the older CUP-based approach.
# 7 managers (=1) see self + direct reports; 3 executives (=0) see only self.
VIEW_REPORTS_BY_EMPLOYEE_ID = {
    "CEO": 1, "CFO": 1, "HR-001": 1, "HR-002": 1,
    "SAL-001": 1, "SAL-002": 0,
    "OPS-001": 1, "OPS-002": 0,
    "MKT-001": 1, "MKT-002": 0,
}


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def run():
    """Seed canonical demo data (idempotent)."""
    company = _resolve_company()
    holiday_list = _resolve_holiday_list()
    if not company:
        print("  ❌ No Company found. Create a Company first.", flush=True)
        return

    print(f"Target company: {company}", flush=True)
    print(f"Holiday list: {holiday_list or '(none — will skip holiday_list field on employees)'}", flush=True)

    _seed_employees(company, holiday_list)
    _seed_policies()
    _acknowledge_pending_pas()
    _seed_leave_type_and_period(company, holiday_list)
    _seed_leave_allocations()
    _print_final_state(company, holiday_list)


def reset_and_seed():
    """Wipe demo data, then re-seed from scratch.

    Deletion order respects FKs:
      Leave Allocation (cancel-then-delete) →
      Policy Audit Log → Policy Acknowledgement →
      Action Centre Activity → Employee Action Centre →
      Employee Directory → Employee (demo IDs) →
      HR Policy (demo names) → Leave Period 2026 → Leave Type Optional Holiday Leave
    """
    print("=== WIPE phase ===", flush=True)
    _wipe_demo_data()
    print("\n=== SEED phase ===", flush=True)
    run()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_company():
    return frappe.db.get_value("Company", {}, "name")


def _resolve_holiday_list():
    """Use Holidays 2026 if present, else first available, else None."""
    if frappe.db.exists("Holiday List", "Holidays 2026"):
        return "Holidays 2026"
    return frappe.db.get_value("Holiday List", {}, "name")


def _dept_lookup(company):
    return {
        d.department_name: d.name
        for d in frappe.get_all(
            "Department",
            fields=["name", "department_name"],
            filters={"company": company},
        )
    }


def _ensure_user(email, first_name, last_name, roles=None):
    """Idempotently create a System User. Without this, the Employee
    controller's add_user_permission call silently no-ops because the
    User doesn't exist yet."""
    if frappe.db.exists("User", email):
        return email
    user = frappe.new_doc("User")
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    user.send_welcome_email = 0
    user.user_type = "System User"
    user.enabled = 1
    user.flags.ignore_permissions = True
    user.flags.no_welcome_mail = True
    for role in (roles or ["Employee"]):
        user.append("roles", {"role": role})
    user.insert(ignore_permissions=True)
    return email


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------

def _seed_employees(company, holiday_list):
    dept_lookup = _dept_lookup(company)
    print(f"Departments: {dept_lookup}", flush=True)

    for emp_id, email, desig, reports_to, dept, auto_p, bypass, in_dir in DEMO_EMPLOYEES:
        if frappe.db.exists("Employee", emp_id):
            print(f"  {emp_id} already exists", flush=True)
            continue
        first_name = desig.split()[0] if " " in desig else desig
        # Pre-create the User row BEFORE inserting the Employee, so the
        # ERPNext employee controller's add_user_permission call has a
        # User to attach the User Permission to. Without this, the
        # controller silently no-ops on first insert.
        try:
            _ensure_user(email, first_name, emp_id)
        except Exception as e:
            print(f"  ⚠️  Could not pre-create User {email}: {type(e).__name__}: {str(e)[:160]}", flush=True)
        emp_data = {
            "doctype": "Employee",
            "first_name": first_name,
            "last_name": emp_id,
            "employee_name": f"{desig} ({emp_id})",
            "company": company,
            "designation": desig,
            "date_of_joining": "2024-01-01",
            "date_of_birth": "1990-01-01",
            "gender": "Male",
            "status": "Active",
            "user_id": email,
            "custom_employee_id": emp_id,
            "custom_emp_directory": in_dir,
            "custom_add_to_action_centre": 1,
            "custom_auto_present": auto_p,
            "custom_bypass_geolocation_check": bypass,
            "custom_allow_view_reporting": VIEW_REPORTS_BY_EMPLOYEE_ID.get(emp_id, 0),
            "create_user_permission": 0,
        }
        if holiday_list:
            emp_data["holiday_list"] = holiday_list
        if dept and dept in dept_lookup:
            emp_data["department"] = dept_lookup[dept]
        if reports_to:
            emp_data["reports_to"] = reports_to
            approver_email = frappe.db.get_value("Employee", reports_to, "user_id")
            if approver_email:
                emp_data["leave_approver"] = approver_email
        try:
            emp = frappe.get_doc(emp_data).insert(ignore_permissions=True)
            frappe.db.commit()
            print(
                f"  ✅ {emp_id} → {emp.name} "
                f"(view_reports={emp_data['custom_allow_view_reporting']})",
                flush=True,
            )
        except Exception as e:
            print(f"  ❌ {emp_id} FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
            frappe.db.rollback()


# ---------------------------------------------------------------------------
# HR Policies
# ---------------------------------------------------------------------------

def _seed_policies():
    for name, cat, active, mandatory in DEMO_POLICIES:
        existing = frappe.db.exists("HR Policy", {"policy_name": name})
        if existing:
            print(f"  HR Policy '{name}' already exists ({existing})", flush=True)
            continue
        try:
            p = frappe.get_doc({
                "doctype": "HR Policy",
                "policy_name": name,
                "category": cat,
                "is_active": active,
                "version": 1,
                "mandatory_check_in_block": mandatory,
                "applies_to_all_employees": 1,
                "applicability_logic": "OR",
                "file": "/files/sample_policy.pdf",
            }).insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"  ✅ HR Policy: {p.name} ({name})", flush=True)
        except Exception as e:
            print(f"  ❌ HR Policy {name} FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
            frappe.db.rollback()

    print(f"Total active HR Policies: {frappe.db.count('HR Policy', {'is_active': 1})}", flush=True)
    print(f"PAs auto-seeded: {frappe.db.count('Policy Acknowledgement')}", flush=True)


def _acknowledge_pending_pas():
    pending = frappe.get_all("Policy Acknowledgement", filters={"status": "Pending"}, pluck="name")
    acked = 0
    for pa_name in pending:
        try:
            pa = frappe.get_doc("Policy Acknowledgement", pa_name)
            pa.status = "Acknowledged"
            pa.save(ignore_permissions=True)
            acked += 1
        except Exception as e:
            print(f"  Ack failed {pa_name}: {str(e)[:120]}", flush=True)
    frappe.db.commit()
    print(f"  Acknowledged: {acked} rows", flush=True)


# ---------------------------------------------------------------------------
# Leave Type / Leave Period / Leave Allocations
# ---------------------------------------------------------------------------

def _seed_leave_type_and_period(company, holiday_list):
    if not frappe.db.exists("Leave Type", "Optional Holiday Leave"):
        frappe.get_doc({
            "doctype": "Leave Type",
            "leave_type_name": "Optional Holiday Leave",
            "is_optional_leave": 1,
            "max_continuous_days_allowed": 1,
            "include_holiday": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        print("  Created Leave Type: Optional Holiday Leave", flush=True)

    if not frappe.db.exists("Leave Period", {"is_active": 1}):
        period_data = {
            "doctype": "Leave Period",
            "name": "Leave Period 2026",
            "from_date": "2026-01-01",
            "to_date": "2026-12-31",
            "is_active": 1,
            "company": company,
        }
        if holiday_list:
            period_data["optional_holiday_list"] = holiday_list
        try:
            lp = frappe.get_doc(period_data).insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"  Created Leave Period: {lp.name}", flush=True)
        except Exception as e:
            print(f"  ❌ Leave Period FAILED: {type(e).__name__}: {str(e)[:200]}", flush=True)
            frappe.db.rollback()


def _seed_leave_allocations():
    for emp in frappe.get_all("Employee", filters={"status": "Active"}, pluck="name"):
        existing = frappe.db.exists("Leave Allocation", {
            "employee": emp,
            "leave_type": "Optional Holiday Leave",
            "docstatus": 1,
        })
        if existing:
            continue
        try:
            alloc = frappe.get_doc({
                "doctype": "Leave Allocation",
                "employee": emp,
                "leave_type": "Optional Holiday Leave",
                "from_date": "2026-01-01",
                "to_date": "2026-12-31",
                "new_leaves_allocated": 10,
            })
            alloc.insert(ignore_permissions=True)
            alloc.submit()
            frappe.db.commit()
            print(f"  ✅ Allocation for {emp}: {alloc.name}", flush=True)
        except Exception as e:
            print(f"  ❌ Allocation {emp} FAILED: {str(e)[:200]}", flush=True)
            frappe.db.rollback()


# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------

def _print_final_state(company, holiday_list):
    print("", flush=True)
    print("=== FINAL v16 DEMO STATE ===", flush=True)
    print(f"Company: {company}", flush=True)
    print(f"Active Employees: {frappe.db.count('Employee', {'status': 'Active'})}", flush=True)
    print(f"Active HR Policies: {frappe.db.count('HR Policy', {'is_active': 1})}", flush=True)
    print(f"PAs (Acknowledged): {frappe.db.count('Policy Acknowledgement', {'status': 'Acknowledged'})}", flush=True)
    print(f"PAs (Pending): {frappe.db.count('Policy Acknowledgement', {'status': 'Pending'})}", flush=True)
    print(f"Employee Action Centres: {frappe.db.count('Employee Action Centre')}", flush=True)
    print(f"Employee Directory rows: {frappe.db.count('Employee Directory')}", flush=True)
    print(f"Leave Allocations submitted: {frappe.db.count('Leave Allocation', {'docstatus': 1})}", flush=True)
    view_count = frappe.db.count(
        "Employee",
        {"name": ["in", DEMO_EMPLOYEE_IDS], "custom_allow_view_reporting": 1},
    )
    print(f"Employees with custom_allow_view_reporting=1 (demo): {view_count}", flush=True)
    ups_count = frappe.db.count(
        "User Permission",
        {"allow": "Employee", "for_value": ["in", DEMO_EMPLOYEE_IDS]},
    )
    print(f"User Permissions on Employee (demo): {ups_count}", flush=True)
    if holiday_list:
        print(f"Holidays in {holiday_list}: {frappe.db.count('Holiday', {'parent': holiday_list})}", flush=True)


# ---------------------------------------------------------------------------
# Wipe
# ---------------------------------------------------------------------------

def _wipe_demo_data():
    """Best-effort delete in FK-safe order. Each step is wrapped to keep going."""

    # 0. User Permissions for demo employees (must run BEFORE Employee delete —
    #    otherwise Frappe's linked-doc check blocks the Employee delete).
    ups = frappe.get_all(
        "User Permission",
        filters={"allow": "Employee", "for_value": ["in", DEMO_EMPLOYEE_IDS]},
        pluck="name",
    )
    for up in ups:
        try:
            frappe.delete_doc("User Permission", up, force=1, ignore_permissions=1)
        except Exception:
            pass
    if ups:
        frappe.db.commit()
        print(f"  Wiped User Permissions: {len(ups)}", flush=True)

    # 0b. Company UPs that the Employee controller may have created on the demo users
    demo_emails = [row[1] for row in DEMO_EMPLOYEES]
    company_ups = frappe.get_all(
        "User Permission",
        filters={"allow": "Company", "user": ["in", demo_emails]},
        pluck="name",
    )
    for up in company_ups:
        try:
            frappe.delete_doc("User Permission", up, force=1, ignore_permissions=1)
        except Exception:
            pass
    if company_ups:
        frappe.db.commit()
        print(f"  Wiped Company User Permissions: {len(company_ups)}", flush=True)

    # 1. Cancel + delete Leave Allocations for demo employees
    allocs = frappe.get_all(
        "Leave Allocation",
        filters={"employee": ["in", DEMO_EMPLOYEE_IDS]},
        fields=["name", "docstatus"],
    )
    for a in allocs:
        try:
            doc = frappe.get_doc("Leave Allocation", a.name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Leave Allocation", a.name, force=1, ignore_permissions=1)
        except Exception as e:
            print(f"  Skip Leave Allocation {a.name}: {str(e)[:120]}", flush=True)
    if allocs:
        frappe.db.commit()
        print(f"  Wiped Leave Allocations: {len(allocs)}", flush=True)

    # 2. Policy Audit Log entries (free-form — wipe everything tied to demo PAs/policies)
    audit_logs = frappe.get_all(
        "Policy Audit Log",
        filters={"policy": ["in", DEMO_POLICY_NAMES]},
        pluck="name",
    ) if frappe.db.table_exists("Policy Audit Log") else []
    for n in audit_logs:
        try:
            frappe.delete_doc("Policy Audit Log", n, force=1, ignore_permissions=1)
        except Exception:
            pass
    if audit_logs:
        frappe.db.commit()
        print(f"  Wiped Policy Audit Log: {len(audit_logs)}", flush=True)

    # 3. Policy Acknowledgements for demo employees / demo policies
    pas = frappe.get_all(
        "Policy Acknowledgement",
        filters={"employee": ["in", DEMO_EMPLOYEE_IDS]},
        pluck="name",
    )
    pas += frappe.get_all(
        "Policy Acknowledgement",
        filters={"policy": ["in", DEMO_POLICY_NAMES]},
        pluck="name",
    )
    pas = list(set(pas))
    for n in pas:
        try:
            frappe.delete_doc("Policy Acknowledgement", n, force=1, ignore_permissions=1)
        except Exception as e:
            print(f"  Skip PA {n}: {str(e)[:120]}", flush=True)
    if pas:
        frappe.db.commit()
        print(f"  Wiped Policy Acknowledgements: {len(pas)}", flush=True)

    # 4. Employee Action Centre + Action Centre Activity (children deleted via parent)
    eacs = frappe.get_all(
        "Employee Action Centre",
        filters={"employee": ["in", DEMO_EMPLOYEE_IDS]},
        pluck="name",
    )
    for n in eacs:
        try:
            frappe.delete_doc("Employee Action Centre", n, force=1, ignore_permissions=1)
        except Exception as e:
            print(f"  Skip EAC {n}: {str(e)[:120]}", flush=True)
    if eacs:
        frappe.db.commit()
        print(f"  Wiped Employee Action Centres: {len(eacs)}", flush=True)

    # 5. Employee Directory rows
    dirs = frappe.get_all(
        "Employee Directory",
        filters={"employee": ["in", DEMO_EMPLOYEE_IDS]},
        pluck="name",
    )
    for n in dirs:
        try:
            frappe.delete_doc("Employee Directory", n, force=1, ignore_permissions=1)
        except Exception as e:
            print(f"  Skip Directory {n}: {str(e)[:120]}", flush=True)
    if dirs:
        frappe.db.commit()
        print(f"  Wiped Employee Directory rows: {len(dirs)}", flush=True)

    # 6. Employees (the 10 demo IDs)
    for emp_id in DEMO_EMPLOYEE_IDS:
        if frappe.db.exists("Employee", emp_id):
            try:
                frappe.delete_doc("Employee", emp_id, force=1, ignore_permissions=1)
                print(f"  Wiped Employee: {emp_id}", flush=True)
            except Exception as e:
                print(f"  Skip Employee {emp_id}: {str(e)[:120]}", flush=True)
    frappe.db.commit()

    # 7. HR Policies (5 demo ones)
    for pname in DEMO_POLICY_NAMES:
        existing = frappe.db.get_value("HR Policy", {"policy_name": pname}, "name")
        if existing:
            try:
                frappe.delete_doc("HR Policy", existing, force=1, ignore_permissions=1)
                print(f"  Wiped HR Policy: {pname}", flush=True)
            except Exception as e:
                print(f"  Skip HR Policy {pname}: {str(e)[:120]}", flush=True)
    frappe.db.commit()

    # 8. Leave Period 2026
    if frappe.db.exists("Leave Period", "Leave Period 2026"):
        try:
            frappe.delete_doc("Leave Period", "Leave Period 2026", force=1, ignore_permissions=1)
            print("  Wiped Leave Period: Leave Period 2026", flush=True)
        except Exception as e:
            print(f"  Skip Leave Period: {str(e)[:120]}", flush=True)

    # 9. Leave Type Optional Holiday Leave (only if no allocations remain)
    if frappe.db.exists("Leave Type", "Optional Holiday Leave"):
        remaining = frappe.db.count("Leave Allocation", {"leave_type": "Optional Holiday Leave"})
        if not remaining:
            try:
                frappe.delete_doc("Leave Type", "Optional Holiday Leave", force=1, ignore_permissions=1)
                print("  Wiped Leave Type: Optional Holiday Leave", flush=True)
            except Exception as e:
                print(f"  Skip Leave Type: {str(e)[:120]}", flush=True)
        else:
            print(f"  Kept Leave Type Optional Holiday Leave ({remaining} non-demo allocations remain)", flush=True)

    frappe.db.commit()


if __name__ == "__main__":
    run()
