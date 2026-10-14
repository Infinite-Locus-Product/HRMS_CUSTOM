"""Move the AR approval section out of the Expenses tab and onto its own
`Approvals` tab on HR Settings.

Closes the AR-3 layout follow-up. The original AR-3 patch landed the three
approver toggles under the Expenses tab (anchored after
`prevent_self_expense_approval`) which crowded an unrelated tab. This patch
repoints `Custom Field "HR Settings-custom_ar_approval_section".insert_after`
to the new Tab Break `custom_la_ar_approval_tab`. The new Tab Break itself is
created by `setup.py:_ensure_custom_fields` in the same migrate run.

Idempotent: skips if already pointing at the new tab.
"""
import frappe


_CF = "HR Settings-custom_ar_approval_section"
_NEW_ANCHOR = "custom_la_ar_approval_tab"


def execute():
    if not frappe.db.exists("Custom Field", _CF):
        print(f"v1_14: {_CF} not present; skipping (will be created fresh by _ensure_custom_fields).")
        return

    current = frappe.db.get_value("Custom Field", _CF, "insert_after")
    if current == _NEW_ANCHOR:
        print(f"v1_14: {_CF}.insert_after already points at {_NEW_ANCHOR}; nothing to do.")
        return

    frappe.db.set_value("Custom Field", _CF, "insert_after", _NEW_ANCHOR)
    frappe.db.commit()
    print(f"v1_14: repointed {_CF}.insert_after  {current!r}  {_NEW_ANCHOR!r}")
