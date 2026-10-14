"""Seed the AR approver toggles on HR Settings to their declared defaults.

Closes AR-3. Custom Field `default` attrs only apply when a *new* doc is
created — adding a Check field to a singleton's existing row leaves the column
NULL. The runtime gate (`myhr.approval_gate._ar_settings`) already falls back
to declared defaults when reading NULL, so the security model is correct
either way; this patch is purely so the Desk form for HR Settings shows the
toggles in their default state without the admin having to touch them.

Idempotent: only writes when the column is NULL. If an admin has already set
their company policy via the form, this patch leaves their values alone.
"""
import frappe


_DEFAULTS = {
    "custom_ar_approver_hr_manager": 1,
    "custom_ar_approver_leave_approver": 1,
    "custom_ar_allow_self_submit": 0,
}


def execute():
    if not frappe.db.exists("DocType", "HR Settings"):
        print("v1_13: HR Settings doctype not present; skipping.")
        return

    meta = frappe.get_meta("HR Settings")
    fields_present = {f.fieldname for f in meta.fields}

    # Read once; HR Settings is a singleton.
    name = "HR Settings"
    updates = {}
    for fieldname, default_val in _DEFAULTS.items():
        if fieldname not in fields_present:
            print(f"v1_13: field '{fieldname}' not yet on HR Settings; skipping.")
            continue
        current = frappe.db.get_single_value("HR Settings", fieldname)
        if current is None:
            updates[fieldname] = default_val

    if not updates:
        print("v1_13: HR Settings AR toggles already populated; nothing to seed.")
        return

    for fieldname, value in updates.items():
        frappe.db.set_single_value("HR Settings", fieldname, value)
    frappe.db.commit()
    print(f"v1_13: seeded HR Settings AR toggles → {updates}")
