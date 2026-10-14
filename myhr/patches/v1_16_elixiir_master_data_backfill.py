"""Backfill native Employee fields from Elixiir custom_* fields.

Phase 1 of the Elixiir → myhr merge introduced server-side syncers
(`myhr.employee_master_data`) that mirror Overview-tab custom_* fields onto
the native Employee fields. Existing rows predating those syncers may have
the custom_* fields set with the native fields blank — payroll / bank
flows would silently fail for them.

This patch runs once per site:
  - custom_age <- compute from date_of_birth (Y/M format)
  - notice_number_of_days <- custom_notice_period_days
  - bank_name / bank_ac_no / ifsc_code <- custom_bank_name / _account_number / _ifsc_code
  - salary_mode <- custom_payment_mode (Bank Transfer -> Bank)
  - holiday_list <- custom_holiday_list

Per-row try/except so a single bad row never aborts the patch.
`update_modified=False` so we don't churn timestamps or trigger hooks.
"""
import frappe
from frappe.utils import getdate


def _compute_age(dob):
    if not dob:
        return ""
    dob = getdate(dob)
    today = getdate()
    years = today.year - dob.year
    months = today.month - dob.month
    if today.day < dob.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    if years < 0:
        return ""
    return f"{years} Years {months} Months"


_PAYMENT_MODE_MAP = {"Bank Transfer": "Bank", "Cheque": "Cheque", "Cash": "Cash"}


def execute():
    # Materialize the elixiir custom_* columns first. Custom Field rows are
    # created by `myhr.setup._ensure_custom_fields()` which only runs in the
    # after_migrate phase — patches run BEFORE that, so on a fresh migrate
    # the custom_* columns don't exist on `tabEmployee` yet. Call the same
    # idempotent setup helper here so the SELECT below has columns to read.
    from myhr.setup import _ensure_custom_fields

    _ensure_custom_fields()
    frappe.db.commit()
    frappe.clear_cache(doctype="Employee")

    # Defensive guard — if any expected column is still missing (e.g. an
    # unrelated install threw mid-way), skip the backfill rather than crash.
    needed = (
        "custom_age",
        "custom_notice_period_days",
        "custom_bank_name",
        "custom_account_number",
        "custom_ifsc_code",
        "custom_payment_mode",
        "custom_holiday_list",
    )
    missing = [c for c in needed if not frappe.db.has_column("Employee", c)]
    if missing:
        print(
            "v1_16_elixiir_master_data_backfill: skipping — Employee table "
            f"is missing columns {missing}. Re-run after the next migrate."
        )
        return

    rows = frappe.db.sql(
        """
        SELECT
            name,
            date_of_birth,
            custom_age,
            custom_notice_period_days,
            notice_number_of_days,
            custom_bank_name,
            bank_name,
            custom_account_number,
            bank_ac_no,
            custom_ifsc_code,
            ifsc_code,
            custom_payment_mode,
            salary_mode,
            custom_holiday_list,
            holiday_list
        FROM `tabEmployee`
        """,
        as_dict=True,
    )

    updated = 0
    failed = 0
    for r in rows:
        try:
            updates = {}

            if not r.custom_age and r.date_of_birth:
                age = _compute_age(r.date_of_birth)
                if age:
                    updates["custom_age"] = age

            if (
                r.custom_notice_period_days
                and not (r.notice_number_of_days or 0)
            ):
                updates["notice_number_of_days"] = r.custom_notice_period_days

            if r.custom_bank_name and not r.bank_name:
                updates["bank_name"] = r.custom_bank_name
            if r.custom_account_number and not r.bank_ac_no:
                updates["bank_ac_no"] = r.custom_account_number
            if r.custom_ifsc_code and not r.ifsc_code:
                updates["ifsc_code"] = r.custom_ifsc_code

            if r.custom_payment_mode and not r.salary_mode:
                mapped = _PAYMENT_MODE_MAP.get(r.custom_payment_mode, r.custom_payment_mode)
                updates["salary_mode"] = mapped

            if r.custom_holiday_list and not r.holiday_list:
                updates["holiday_list"] = r.custom_holiday_list

            if updates:
                frappe.db.set_value(
                    "Employee", r.name, updates, update_modified=False
                )
                updated += 1
        except Exception:
            failed += 1
            frappe.log_error(
                title=f"v1_16_elixiir_master_data_backfill failed for {r.name}",
                message=frappe.get_traceback(),
            )

    frappe.db.commit()
    print(
        f"v1_16_elixiir_master_data_backfill: {updated} Employee rows updated, "
        f"{failed} failed (see Error Log) out of {len(rows)} scanned."
    )
