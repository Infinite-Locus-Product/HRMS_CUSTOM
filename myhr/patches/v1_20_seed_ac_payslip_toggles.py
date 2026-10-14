"""v1.20 — Seed defaults for the new HR Settings AC payslip mandatory toggles.

The Custom Field `default: 1` on each toggle doesn't materialise on the
existing HR Settings singleton row when Frappe adds the column (SQL default
is 0). Without this seed, the 3 payslip rows would silently flip to OPTIONAL
on a fresh migrate — defeating the original 'all required' policy.

Idempotent. Calls `myhr.setup._seed_ac_payslip_mandatory_defaults()` which
also runs on every after_migrate via `_setup()`. The patch exists so the
seed runs the first time on already-installed sites without waiting for
the after_migrate hook (which fires AFTER patches).
"""
import frappe


def execute():
    from myhr.setup import _seed_ac_payslip_mandatory_defaults
    _seed_ac_payslip_mandatory_defaults()
    frappe.db.commit()
    frappe.clear_cache(doctype="HR Settings")
    print("v1_20_seed_ac_payslip_toggles: applied")
