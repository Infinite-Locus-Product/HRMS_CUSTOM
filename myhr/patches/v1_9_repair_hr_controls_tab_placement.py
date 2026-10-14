"""v1.9 — repair HR Controls tab placement on Employee form.

Re-asserts that the four HR-control flags (`custom_emp_directory`,
`custom_add_to_action_centre`, `custom_auto_present`, and
`custom_bypass_geolocation_check`) sit under the **HR Controls** tab anchored
by `custom_hr_controls_tab`, instead of leaking into **Overview**.

Why a fresh patch is needed: `_ensure_custom_fields` is skip-if-exists, and
the older `v1_2` patch is already marked done in `Patch Log` on installed
sites — so neither path can repair pre-existing rows whose `insert_after`
drifted (typically from a stale `fixtures/custom_field.json` import or a
manual Custom Field edit). Bumping to a new patch number forces re-execution.

Idempotent: rows already at the canonical value are skipped. Fresh installs
hit `_ensure_custom_fields` first, then `v1_2`, then `v1_9` — all converge.
"""
import frappe


# Source of truth: must match the `insert_after` values in
# `MYHR_CUSTOM_FIELDS` (myhr.setup) for these 5 fields. Duplicated here so
# the patch survives a setup.py refactor — same convention as v1_8.
REPAIR = {
    "Employee-custom_hr_controls_tab":         "branch",
    "Employee-custom_emp_directory":           "custom_hr_controls_tab",
    "Employee-custom_add_to_action_centre":    "custom_emp_directory",
    "Employee-custom_auto_present":            "custom_add_to_action_centre",
    "Employee-custom_bypass_geolocation_check": "custom_auto_present",
}


def execute():
    repaired = 0
    skipped = 0
    missing = 0
    for cf_name, expected in REPAIR.items():
        if not frappe.db.exists("Custom Field", cf_name):
            missing += 1
            print(f"  SKIP missing: {cf_name}")
            continue
        current = frappe.db.get_value("Custom Field", cf_name, "insert_after")
        if current == expected:
            skipped += 1
            continue
        frappe.db.set_value("Custom Field", cf_name, "insert_after", expected)
        repaired += 1
        print(f"  REPAIR {cf_name}: '{current}' -> '{expected}'")

    if repaired:
        frappe.db.commit()
        frappe.clear_cache()
    print(
        f"v1_9 repair_hr_controls_tab_placement done: "
        f"repaired={repaired} skipped={skipped} missing={missing}"
    )
