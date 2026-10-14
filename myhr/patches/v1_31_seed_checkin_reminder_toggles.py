"""Seed defaults for the Missing IN Checkin Reminder opt-out flags.

Two Custom Fields shipped with this version (created by `setup.py` on
`bench migrate`):
  - `Employee.custom_send_checkin_reminder` (Check, default 1)
  - `HR Settings.custom_enable_checkin_reminder` (Check, default 1)

Frappe's default attr on Custom Field populates new docs, but it does
NOT backfill existing rows when the SQL column is added. This patch
ensures every Employee row defaults to ticked AND the HR Settings
Single doc has a value, so the cron's NULL-tolerant check is belt-
and-braces only.

Also reloads the `Missing Checkin Reminder Log` DocType from JSON to
pick up the new `opt_out` value on the `skip_reason` Select.

Idempotent: safe to re-run.
"""

import frappe


def execute():
    # 0. Custom Fields are normally created in `after_migrate`, AFTER patches
    # run. Force-ensure them here so the rest of the patch can rely on
    # both columns / Custom Field rows existing on installed sites.
    try:
        from myhr.setup import _ensure_custom_fields
        _ensure_custom_fields()
        frappe.clear_cache(doctype="Employee")
        frappe.clear_cache(doctype="HR Settings")
    except Exception as exc:
        print(f"v1_31: _ensure_custom_fields failed ({exc}); continuing.")

    # 1. Backfill Employee per-row opt-in flag on existing rows.
    if frappe.db.has_column("Employee", "custom_send_checkin_reminder"):
        affected = frappe.db.sql(
            """UPDATE `tabEmployee`
               SET custom_send_checkin_reminder = 1
               WHERE custom_send_checkin_reminder IS NULL"""
        )
        print(
            f"v1_31: backfilled custom_send_checkin_reminder=1 on Employee "
            f"({frappe.db.sql('SELECT ROW_COUNT()')[0][0]} rows touched)."
        )
    else:
        print(
            "v1_31: Employee.custom_send_checkin_reminder column not present "
            "yet — skipping backfill (will be created on next migrate)."
        )

    # 2. Force HR Settings global toggle to 1.
    #
    # We always set to 1 here (not conditional on NULL). Reason: Frappe's
    # Custom Field auto-create on a Single doctype lands a `tabSingles` row
    # with value '0' (not NULL) under some code paths, which would make a
    # "leave-as-is if not NULL" guard skip the seed and ship the feature
    # globally OFF — opposite of the intended default. Since patches are
    # guarded by `Patch Log` (this body runs exactly once on installed
    # sites), an unconditional set is safe and matches the spec default.
    cf_exists = frappe.db.exists("Custom Field", {
        "dt": "HR Settings",
        "fieldname": "custom_enable_checkin_reminder",
    })
    if cf_exists:
        frappe.db.set_single_value(
            "HR Settings", "custom_enable_checkin_reminder", 1
        )
        print(
            "v1_31: set HR Settings.custom_enable_checkin_reminder=1."
        )
    else:
        print(
            "v1_31: Custom Field HR Settings.custom_enable_checkin_reminder "
            "not yet present — skipping seed (next migrate will create it "
            "and the cron's NULL-tolerant check will treat it as ticked)."
        )

    # 3. Re-sync the log DocType so the new opt_out Select option lands.
    if frappe.db.exists("DocType", "Missing Checkin Reminder Log"):
        frappe.reload_doc("myhr", "doctype", "missing_checkin_reminder_log")
        frappe.clear_cache(doctype="Missing Checkin Reminder Log")
        print(
            "v1_31: re-synced Missing Checkin Reminder Log "
            "(opt_out added to skip_reason)."
        )
