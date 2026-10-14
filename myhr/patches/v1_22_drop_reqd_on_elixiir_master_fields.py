"""Drop reqd=1 on the 9 elixiir master-data Employee Custom Fields.

These fields were imported from elixiir's HR scope (Phase 1 merge) with
`reqd=1`. On staging, existing Employee records predate the install and
have NULL values in these columns — every save now blocks on the
"Missing Fields" dialog (Salary Structure / Employee Location / 7 Bank
fields). Decision: relax these to optional. HR fills them in over time
without blocking other Employee edits.

`v1_8_repair_custom_field_flags` only repairs attrs that are still
declared in MYHR_CUSTOM_FIELDS — removing `reqd` from the dict won't
flip an already-set DB row. Hence this explicit one-shot patch.

Idempotent: only updates rows where reqd is currently 1.
"""

import frappe


_FIELDS_TO_RELAX = (
    "custom_salary_structure",
    "custom_employee_location",
    "custom_bank_name",
    "custom_account_number",
    "custom_ifsc_code",
    "custom_account_type",
    "custom_payment_mode",
    "custom_account_holder_name",
    "custom_name_as_per_bank",
)


def execute():
    relaxed = 0
    for fieldname in _FIELDS_TO_RELAX:
        cf_name = f"Employee-{fieldname}"
        if not frappe.db.exists("Custom Field", cf_name):
            continue
        current = frappe.db.get_value("Custom Field", cf_name, "reqd")
        if int(current or 0) == 0:
            continue
        frappe.db.set_value("Custom Field", cf_name, "reqd", 0)
        relaxed += 1
        print(f"  relaxed {cf_name}: reqd 1 -> 0")
    if relaxed:
        frappe.clear_cache(doctype="Employee")
        frappe.db.commit()
        print(f"v1_22: dropped reqd on {relaxed} elixiir master-data field(s).")
    else:
        print("v1_22: no fields needed relaxing (reqd already 0 everywhere).")
