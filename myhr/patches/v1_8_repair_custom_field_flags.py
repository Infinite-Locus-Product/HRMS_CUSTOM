"""Repair existing Custom Field flags to match MYHR_CUSTOM_FIELDS declarations.

Closes SET-1. Before this patch, `myhr.setup._ensure_custom_fields` only
applied a subset of attrs on insert (label, fieldtype, insert_after, options,
default, description, bold, in_list_view, unique). That left `read_only`,
`reqd`, `hidden`, `permlevel`, etc. silently dropped — Custom Fields that
*should* have been read-only landed as editable.

For installs created before this fix, the field rows persist with the wrong
flags. The skip-if-exists logic in `_ensure_custom_fields` won't repair them
on subsequent migrates. This patch sweeps `MYHR_CUSTOM_FIELDS`, finds
existing fields, and aligns the on-DB row to the declared dict using
`frappe.db.set_value` for each attr that drifts.
"""
import frappe


# Same list as setup.py — duplicated here so this patch survives even if
# setup.py is refactored later. Don't import from setup; that creates a
# patch ↔ setup runtime coupling.
_HONOURED_ATTRS = (
    "label", "fieldtype", "insert_after", "options", "default", "description",
    "bold", "in_list_view", "in_standard_filter", "unique",
    "read_only", "reqd", "hidden", "no_copy", "print_hide",
    "permlevel", "translatable", "non_negative", "ignore_user_permissions",
    "depends_on", "mandatory_depends_on", "read_only_depends_on",
    "fetch_from", "fetch_if_empty", "length", "precision",
)


def execute():
    try:
        from myhr.setup import MYHR_CUSTOM_FIELDS
    except ImportError:
        print("Could not import MYHR_CUSTOM_FIELDS; skipping.")
        return

    repaired = 0
    for field_def in MYHR_CUSTOM_FIELDS:
        cf_name = "{dt}-{fieldname}".format(**field_def)
        if not frappe.db.exists("Custom Field", cf_name):
            continue

        existing = frappe.db.get_value(
            "Custom Field", cf_name,
            list(_HONOURED_ATTRS) + ["dt", "fieldname"],
            as_dict=True,
        ) or {}

        updates = {}
        for attr in _HONOURED_ATTRS:
            if attr not in field_def:
                continue
            declared = field_def[attr]
            current = existing.get(attr)
            # Coerce both sides to strings for comparison so 1 != "1" doesn't
            # trip us up; Frappe stores Check fields as int but dicts often
            # carry strings.
            if str(current or "") != str(declared or ""):
                updates[attr] = declared
        if updates:
            frappe.db.set_value("Custom Field", cf_name, updates)
            repaired += 1
            print(f"  repaired {cf_name}: {updates}")

    if repaired:
        frappe.db.commit()
        print(f"Custom Field flags repaired on {repaired} field(s).")
    else:
        print("No Custom Field flag drift detected.")
