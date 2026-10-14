"""v1.11 — Lock writes on Employee to HR Manager + System Manager only.

Strips write/create/delete/submit/cancel/amend from any role's DocPerm on
Employee at permlevel=0 EXCEPT HR Manager + System Manager + Administrator.

Idempotent. Calls myhr.setup._ensure_employee_perm_lockdown() which lives
in setup.py and runs on every after_migrate via _setup().

This patch exists because Patch Log gates fresh migrations: once it's run,
Frappe records it; subsequent migrates re-run only the post-model-sync that
HASN'T been recorded. The lockdown lives in setup.py so it survives a fresh
install AND a migrate, but the patch is what guarantees it lands the first
time on existing v1_x sites that already ran prior migrations.
"""
import frappe


def execute():
    from myhr.setup import _ensure_employee_perm_lockdown
    _ensure_employee_perm_lockdown()
    frappe.db.commit()
    frappe.clear_cache()
    print("v1_11 employee_write_lockdown: applied")
