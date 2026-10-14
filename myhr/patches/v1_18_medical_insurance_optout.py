"""v1.18 — Medical Insurance: rename Yes/No -> Opt In/Opt Out + add signed_optout column.

The Action Centre's Medical Insurance opt-in originally used a Yes/No Select.
Per the Elixiir spec, employees must explicitly Opt In (use company policy)
or Opt Out (sign and upload a declaration). This patch:

  1. Re-maps any saved values: Yes -> "Opt In", No -> "Opt Out".
  2. Materializes the new `medical_insurance_signed_optout` column (Attach).
     The Custom Field is declared in the Employee Action Centre JSON; calling
     `_ensure_custom_fields` is unnecessary here (it's a doctype-level field,
     not a Custom Field), but we DO need to make sure the column is present
     before we run any post-migration smoke checks.

Idempotent. Safe to re-run.
"""
import frappe


def execute():
    frappe.reload_doctype("Employee Action Centre")
    frappe.reload_doc("myhr", "doctype", "medical_insurance_opt_out_declaration")

    # 1. Migrate existing values. SQL is the simplest path here — Frappe's
    # Select doctype validation will refuse to load old "Yes"/"No" values
    # once the options change, so an ORM `set_value` loop would 422.
    if frappe.db.has_column("Employee Action Centre", "medical_insurance_opt_in"):
        yes_count = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabEmployee Action Centre` WHERE medical_insurance_opt_in = 'Yes'"
        )[0][0]
        no_count = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabEmployee Action Centre` WHERE medical_insurance_opt_in = 'No'"
        )[0][0]
        if yes_count:
            frappe.db.sql(
                "UPDATE `tabEmployee Action Centre` SET medical_insurance_opt_in = 'Opt In' "
                "WHERE medical_insurance_opt_in = 'Yes'"
            )
        if no_count:
            frappe.db.sql(
                "UPDATE `tabEmployee Action Centre` SET medical_insurance_opt_in = 'Opt Out' "
                "WHERE medical_insurance_opt_in = 'No'"
            )
        frappe.db.commit()
        print(
            f"v1_18: migrated medical_insurance_opt_in — Yes->Opt In x{yes_count}, "
            f"No->Opt Out x{no_count}"
        )

    print("v1_18_medical_insurance_optout: applied.")
