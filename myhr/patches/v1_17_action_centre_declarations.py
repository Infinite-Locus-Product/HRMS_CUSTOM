"""v1.17 — Action Centre: Declarations tab + Bank Statement (6 Months) row.

Adds three new approval-gated rows to every existing Employee Action Centre:

  - Tax Regime (employee declares "New" or "Old")
  - Medical Insurance opt-in (employee picks Yes / No; HR links the policy
    from the new Medical Insurance master doctype)
  - Bank Statement (Last 6 Months) — file upload

The new fields are declared in the Employee Action Centre doctype JSON, so
schema sync materializes the columns automatically. This patch just seeds the
default approval_status = "Pending" on existing AC rows so they don't appear
as NULL on the desk form, and it ensures the new Medical Insurance doctype is
in sync (rare race-condition guard for fresh installs).

Idempotent. Safe to re-run.
"""
import frappe


_DECLARATION_PREFIXES = ("tax_regime", "medical_insurance", "bank_statement_6m")


def execute():
    # 1. Force a reload so the meta picks up the new fields if the migrate
    # hadn't already cached the doctype.
    frappe.reload_doctype("Employee Action Centre")
    frappe.reload_doc("myhr", "doctype", "medical_insurance")

    # 2. Backfill default approval_status on existing AC rows. The JSON sets
    # default="Pending" but Frappe only applies that on row INSERT, not on
    # existing rows when a new column is added — those rows get NULL.
    for prefix in _DECLARATION_PREFIXES:
        col = f"{prefix}_approval_status"
        if not frappe.db.has_column("Employee Action Centre", col):
            print(f"v1_17: skipping {col} — column not yet materialized.")
            continue
        # Backfill NULL/empty -> "Pending" via direct SQL (no hooks).
        frappe.db.sql(
            f"""
            UPDATE `tabEmployee Action Centre`
            SET `{col}` = 'Pending'
            WHERE `{col}` IS NULL OR `{col}` = ''
            """
        )

    # 3. Preserve master status for ACs that were already Accepted or in HR
    # review — these employees onboarded before declarations existed, so the
    # new mandatory rows shouldn't retroactively pull them out of their
    # current state. Mark the new rows is_na=1 + approval_status=Accepted on
    # already-completed/under-review ACs only. New and in-flight onboarding
    # ACs (Pending / In Progress / Ready to Submit / Action Required) are
    # left at defaults so the employee gets prompted for the new declarations.
    completed_states = ("Accepted", "To be Reviewed")
    for prefix in _DECLARATION_PREFIXES:
        is_na_col = f"{prefix}_is_na"
        status_col = f"{prefix}_approval_status"
        if not (
            frappe.db.has_column("Employee Action Centre", is_na_col)
            and frappe.db.has_column("Employee Action Centre", status_col)
        ):
            continue
        frappe.db.sql(
            f"""
            UPDATE `tabEmployee Action Centre`
            SET `{is_na_col}` = 1, `{status_col}` = 'Accepted'
            WHERE `status` IN %(states)s
              AND (`{is_na_col}` IS NULL OR `{is_na_col}` = 0)
            """,
            {"states": completed_states},
        )

    frappe.db.commit()
    print(
        "v1_17_action_centre_declarations: applied — Declarations tab + Bank "
        "Statement row; approval_status seeded; pre-existing Accepted / "
        "To be Reviewed ACs auto-marked N/A on the 3 new rows to preserve "
        "their state."
    )
