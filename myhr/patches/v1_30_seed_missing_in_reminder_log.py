"""Idempotent guard for the Missing Checkin Reminder Log DocType.

The DocType ships via the standard `bench migrate` DocType-sync path.
This patch is the belt-and-braces guarantee for sites where the DocType
row didn't sync (install-order quirks, partial-failed migrations). It
re-syncs the DocType definition from JSON via `frappe.reload_doc` to
catch any drift in field flags.

Idempotent: safe to re-run on installed sites.
"""

import frappe


def execute():
    if not frappe.db.exists("DocType", "Missing Checkin Reminder Log"):
        print(
            "v1_30: Missing Checkin Reminder Log DocType not yet synced - "
            "skipping."
        )
        return

    frappe.reload_doc("myhr", "doctype", "missing_checkin_reminder_log")
    frappe.clear_cache(doctype="Missing Checkin Reminder Log")
    print("v1_30: re-synced Missing Checkin Reminder Log from JSON.")
