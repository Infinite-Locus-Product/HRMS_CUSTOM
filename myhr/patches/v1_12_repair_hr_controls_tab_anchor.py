"""v1.12 — re-anchor HR Controls Tab Break after `grade`.

Anchors `custom_hr_controls_tab.insert_after` at `grade` (instead of
`branch`) so that the stock ERPNext `grade` field stays inside the
Overview tab. With the old anchor at `branch`, `grade` fell under HR
Controls because no stock Tab Break sits between `branch` and `grade`
in the v15/v16 Employee form.

Also re-asserts the full HR Controls field chain in case any earlier
repair (v1_2 / v1_9) didn't persist due to migrate-time transaction
quirks. Uses raw `frappe.db.sql UPDATE` plus an explicit read-back
verification + retry — `frappe.db.set_value` was observed to silently
fail on this row during a real migrate run (printed REPAIR but the
`modified` column never changed).

Idempotent. Safe to re-run. Prints a per-field summary so migrate logs
surface exactly what shifted.
"""
import frappe


CHAIN = [
    ("Employee-custom_hr_controls_tab",          "grade"),
    ("Employee-custom_emp_directory",            "custom_hr_controls_tab"),
    ("Employee-custom_add_to_action_centre",     "custom_emp_directory"),
    ("Employee-custom_auto_present",             "custom_add_to_action_centre"),
    ("Employee-custom_bypass_geolocation_check", "custom_auto_present"),
    ("Employee-custom_allow_view_reporting",     "custom_bypass_geolocation_check"),
]


def _force_set(cf_name, expected):
    """Force-set insert_after via raw SQL + verify. Returns ('ok', 'noop',
    'repaired', 'missing', 'failed') describing the outcome."""
    if not frappe.db.exists("Custom Field", cf_name):
        return "missing"
    current = frappe.db.get_value("Custom Field", cf_name, "insert_after")
    if current == expected:
        return "noop"
    # Use raw SQL (bypasses any controller / set_value quirks) and force
    # `modified` to NOW() so we can verify persistence by timestamp.
    frappe.db.sql(
        """UPDATE `tabCustom Field`
           SET insert_after = %s, modified = NOW()
           WHERE name = %s""",
        (expected, cf_name),
    )
    frappe.db.commit()
    # Read back to confirm
    actual = frappe.db.get_value("Custom Field", cf_name, "insert_after")
    if actual != expected:
        # Retry once with set_value as fallback
        frappe.db.set_value("Custom Field", cf_name, "insert_after", expected)
        frappe.db.commit()
        actual = frappe.db.get_value("Custom Field", cf_name, "insert_after")
        if actual != expected:
            return "failed"
    return "repaired"


def execute():
    counts = {"repaired": 0, "noop": 0, "missing": 0, "failed": 0}
    for cf_name, expected in CHAIN:
        result = _force_set(cf_name, expected)
        counts[result] = counts.get(result, 0) + 1
        if result == "repaired":
            print(f"  REPAIR {cf_name} -> {expected!r}")
        elif result == "missing":
            print(f"  SKIP missing: {cf_name}")
        elif result == "failed":
            print(f"  ❌ FAILED: {cf_name} could not be set to {expected!r}")

    if counts["repaired"] or counts["failed"]:
        frappe.clear_cache()

    print(
        f"v1_12 repair_hr_controls_tab_anchor done: "
        f"repaired={counts['repaired']} noop={counts['noop']} "
        f"missing={counts['missing']} failed={counts['failed']}"
    )
