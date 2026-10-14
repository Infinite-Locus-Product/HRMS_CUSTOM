"""v1.19 — Action Centre: backfill Personal Details / Identity numbers /
Statutory & Bank from Employee for existing AC rows.

The new fields are declared with `fetch_from = "employee.<field>"` +
`fetch_if_empty: 1`, which auto-populates on Employee link change. But
existing AC rows already have the link set, so the fetch_from won't fire
retroactively. This patch pulls the Employee values once.

Idempotent and conservative — only writes when the AC field is currently
empty so any value the employee already typed via the PWA is preserved.
"""
import frappe


# (ac_field, employee_field) — when both exist on their respective doctypes
# AND the AC field is empty, copy Employee → AC.
_BACKFILL_MAP = [
    ("personal_full_name", "employee_name"),
    ("personal_dob", "date_of_birth"),
    ("personal_gender", "gender"),
    ("personal_marital_status", "marital_status"),
    ("personal_mobile", "cell_number"),
    ("personal_blood_group", "blood_group"),
    ("personal_father_name", "custom_father_name"),
    ("personal_mother_name", "custom_mother_name"),
    ("personal_emergency_contact_name", "person_to_be_contacted"),
    ("personal_emergency_contact_number", "emergency_phone_number"),
    ("aadhar_number", "custom_aadhar_number"),
    ("pan_number", "pan_number"),
    ("education_name", "custom_highest_qualification"),
    ("statutory_pf_number", "provident_fund_account"),
    ("statutory_uan_number", "custom_uan"),
    ("bank_name", "custom_bank_name"),
    ("bank_account_number", "custom_account_number"),
    ("bank_ifsc_code", "custom_ifsc_code"),
]


def execute():
    frappe.reload_doctype("Employee Action Centre")

    # Skip the columns that haven't been materialized yet (defensive — avoids
    # a column-missing crash if this patch races ahead of the schema sync).
    available_pairs = []
    for ac_field, emp_field in _BACKFILL_MAP:
        if not frappe.db.has_column("Employee Action Centre", ac_field):
            continue
        if not frappe.db.has_column("Employee", emp_field):
            continue
        available_pairs.append((ac_field, emp_field))

    if not available_pairs:
        print("v1_19_action_centre_personal_details: no columns ready, skipping.")
        return

    ac_fields_str = ", ".join(f"`{f}`" for f, _ in available_pairs)
    rows = frappe.db.sql(
        f"""
        SELECT name, employee, {ac_fields_str}
        FROM `tabEmployee Action Centre`
        WHERE employee IS NOT NULL AND employee != ''
        """,
        as_dict=True,
    )

    updated = 0
    for r in rows:
        emp_name = r["employee"]
        emp_fields = [emp_field for _ac_field, emp_field in available_pairs]
        emp_data = frappe.db.get_value(
            "Employee", emp_name, emp_fields, as_dict=True
        ) or {}
        if not emp_data:
            continue

        updates = {}
        for ac_field, emp_field in available_pairs:
            ac_val = (r.get(ac_field) or "")
            if isinstance(ac_val, str):
                ac_val = ac_val.strip()
            if ac_val:
                continue  # employee already filled / migrated — leave alone
            emp_val = emp_data.get(emp_field)
            if emp_val in (None, ""):
                continue
            updates[ac_field] = emp_val

        if updates:
            frappe.db.set_value(
                "Employee Action Centre", r["name"], updates, update_modified=False
            )
            updated += 1

    frappe.db.commit()
    print(
        f"v1_19_action_centre_personal_details: backfilled {updated} of "
        f"{len(rows)} AC rows from their linked Employee."
    )
