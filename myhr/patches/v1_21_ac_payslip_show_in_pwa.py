"""v1.21 — HR Settings: AC payslip 'Show in PWA' toggles + repair existing
require_X Custom Field attrs.

Adds 3 new HR Settings Check fields ('Show ... in PWA' for each payslip)
and rewires the existing 3 require_X fields:
  * insert_after  → moved to the matching show_X field (so the desk form
    renders Show / Require pairs adjacent)
  * read_only_depends_on → set to disable the Require checkbox when the
    matching Show checkbox is unticked

Idempotent. Calls the same setup helpers that fire on every after_migrate
via `_setup()`. The patch exists so the repair + seed land the first time
on already-installed sites without waiting for the after_migrate hook.
"""
import frappe


def execute():
    from myhr.setup import (
        _ensure_custom_fields,
        _repair_ac_payslip_field_attrs,
        _seed_ac_payslip_show_defaults,
    )

    # 1. Make sure the new show_payslip_* Custom Fields are created. The
    # standard _ensure_custom_fields helper is skip-if-exists, so re-running
    # it is safe and creates any missing rows.
    _ensure_custom_fields()

    # 2. Repair the existing require_payslip_* fields' insert_after +
    # read_only_depends_on attrs.
    _repair_ac_payslip_field_attrs()

    # 3. Seed the new show toggles to 1 on the existing HR Settings row.
    _seed_ac_payslip_show_defaults()

    frappe.db.commit()
    frappe.clear_cache(doctype="HR Settings")
    print("v1_21_ac_payslip_show_in_pwa: applied")
