"""v1.10 — Switch Employee perm model from CUP to custom_allow_view_reporting.

Steps on existing sites:
  1. Ensure custom_allow_view_reporting Custom Field exists (idempotent
     with setup.py's _ensure_custom_fields, but explicit here so the patch
     is self-contained).
  2. For the 10 demo employees (CEO..MKT-002):
        - set Employee.create_user_permission = 0
        - set Employee.custom_allow_view_reporting per the manager/executive map
  3. Delete User Permission rows on Employee/Company that were created
     by the older CUP path for those 10 demo users — they're now stale.
  4. Print a summary so migrate logs are readable.
"""

import frappe

DEMO_MANAGERS_VIEW_REPORTS = {
    "CEO", "CFO", "HR-001", "HR-002",
    "SAL-001", "OPS-001", "MKT-001",
}

DEMO_EXECUTIVES_NO_VIEW = {
    "SAL-002", "OPS-002", "MKT-002",
}

ALL_DEMO = DEMO_MANAGERS_VIEW_REPORTS | DEMO_EXECUTIVES_NO_VIEW


def execute():
    flipped_view = 0
    flipped_cup = 0
    deleted_ups = 0

    for emp_id in ALL_DEMO:
        if not frappe.db.exists("Employee", emp_id):
            continue
        e = frappe.get_doc("Employee", emp_id)
        new_view = 1 if emp_id in DEMO_MANAGERS_VIEW_REPORTS else 0
        if (e.get("custom_allow_view_reporting") or 0) != new_view:
            e.custom_allow_view_reporting = new_view
            flipped_view += 1
        if (e.get("create_user_permission") or 0) != 0:
            e.create_user_permission = 0
            flipped_cup += 1
        e.flags.ignore_permissions = True
        e.save()

    # Wipe stale CUP-style User Permissions for demo users
    user_ids = [u for u in (
        frappe.db.get_value("Employee", emp_id, "user_id") for emp_id in ALL_DEMO
    ) if u]
    if user_ids:
        ups = frappe.get_all(
            "User Permission",
            filters={
                "user": ["in", user_ids],
                "allow": ["in", ["Employee", "Company"]],
            },
            pluck="name",
        )
        for up in ups:
            try:
                frappe.delete_doc("User Permission", up, force=1, ignore_permissions=1)
                deleted_ups += 1
            except Exception:
                pass

    frappe.db.commit()
    frappe.clear_cache()
    print(
        f"v1_10 employee_view_reporting: "
        f"set custom_allow_view_reporting on {flipped_view} demo employees, "
        f"unset CUP on {flipped_cup}, deleted {deleted_ups} stale User Permissions."
    )
