import frappe
from frappe import _
from frappe.utils import flt, getdate


def validate_master_data(doc, method):
    validate_salary_structure_company(doc)
    sync_notice_period(doc)
    sync_bank_details(doc)
    sync_holiday_list(doc)
    compute_age(doc)


def compute_age(doc):
    """Set custom_age as '{years} Years {months} Months' from Date of Birth."""
    if not doc.get("date_of_birth"):
        doc.custom_age = ""
        return
    dob = getdate(doc.date_of_birth)
    today = getdate()
    years = today.year - dob.year
    months = today.month - dob.month
    if today.day < dob.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    if years < 0:
        doc.custom_age = ""
        return
    doc.custom_age = f"{years} Years {months} Months"


def sync_holiday_list(doc):
    """Mirror the Overview-tab custom_holiday_list into the native
    holiday_list field so HRMS attendance/leave flows pick it up."""
    if doc.get("custom_holiday_list"):
        doc.holiday_list = doc.custom_holiday_list


def sync_notice_period(doc):
    """Mirror the Overview-tab custom_notice_period_days into the native
    notice_number_of_days field so ERPNext's separation workflows still work."""
    if doc.get("custom_notice_period_days") is not None:
        doc.notice_number_of_days = doc.custom_notice_period_days


def sync_bank_details(doc):
    """Mirror the Bank & Payment tab custom fields into native Employee
    fields so payroll / bank-file generation continues to work."""
    if doc.get("custom_bank_name"):
        doc.bank_name = doc.custom_bank_name
    if doc.get("custom_account_number"):
        doc.bank_ac_no = doc.custom_account_number
    if doc.get("custom_ifsc_code"):
        doc.ifsc_code = doc.custom_ifsc_code
    if doc.get("custom_payment_mode"):
        # Native salary_mode uses "Bank" for transfer; map our "Bank Transfer".
        mode_map = {"Bank Transfer": "Bank", "Cheque": "Cheque", "Cash": "Cash"}
        doc.salary_mode = mode_map.get(doc.custom_payment_mode, doc.custom_payment_mode)


def after_insert_master_data(doc, method):
    if doc.custom_salary_structure and doc.date_of_joining:
        create_salary_structure_assignment(doc)
    if doc.custom_holiday_list:
        create_holiday_list_assignment(doc)


def on_update_master_data(doc, method):
    previous = doc.get_doc_before_save()

    structure_changed = bool(
        doc.custom_salary_structure
        and previous
        and previous.custom_salary_structure != doc.custom_salary_structure
    )
    ctc_changed = bool(
        doc.custom_salary_structure
        and previous
        and flt(previous.get("ctc")) != flt(doc.get("ctc"))
    )
    recreated = False
    if structure_changed or ctc_changed:
        end_date_existing_assignment(doc)
        create_salary_structure_assignment(doc)
        recreated = True

    if previous and not recreated:
        sync_opening_balances_to_assignment(doc, previous)

    if doc.custom_holiday_list and previous and (
        previous.get("custom_holiday_list") != doc.custom_holiday_list
    ):
        cancel_existing_holiday_list_assignment(doc)
        create_holiday_list_assignment(doc)


def create_holiday_list_assignment(doc):
    """Create and submit a Holiday List Assignment for this Employee.

    HRMS requires `from_date` to fall inside the Holiday List's own
    (from_date, to_date) range, so we clamp DOJ into that window.
    """
    existing = frappe.db.exists(
        "Holiday List Assignment",
        {
            "applicable_for": "Employee",
            "assigned_to": doc.name,
            "holiday_list": doc.custom_holiday_list,
            "docstatus": 1,
        },
    )
    if existing:
        return

    hl_from, hl_to = frappe.db.get_value(
        "Holiday List",
        doc.custom_holiday_list,
        ["from_date", "to_date"],
    ) or (None, None)

    doj = getdate(doc.date_of_joining) if doc.date_of_joining else getdate()
    from_date = doj
    if hl_from and getdate(doj) < getdate(hl_from):
        from_date = getdate(hl_from)
    elif hl_to and getdate(doj) > getdate(hl_to):
        from_date = getdate(hl_from) if hl_from else getdate()

    hla = frappe.new_doc("Holiday List Assignment")
    hla.applicable_for = "Employee"
    hla.assigned_to = doc.name
    hla.holiday_list = doc.custom_holiday_list
    hla.from_date = from_date
    hla.flags.ignore_permissions = True
    hla.insert(ignore_permissions=True)
    hla.submit()

    frappe.msgprint(
        _("Holiday List Assignment {0} created").format(hla.name),
        alert=True,
    )


def cancel_existing_holiday_list_assignment(doc):
    """Cancel any active Holiday List Assignment for this Employee whose
    holiday list differs from the one now set on the Employee."""
    existing = frappe.get_all(
        "Holiday List Assignment",
        filters={
            "applicable_for": "Employee",
            "assigned_to": doc.name,
            "docstatus": 1,
            "holiday_list": ["!=", doc.custom_holiday_list],
        },
        pluck="name",
    )
    for name in existing:
        d = frappe.get_doc("Holiday List Assignment", name)
        d.flags.ignore_permissions = True
        d.cancel()
        frappe.msgprint(
            _("Previous Holiday List Assignment {0} cancelled").format(d.name),
            alert=True,
        )


def validate_salary_structure_company(doc):
    if not doc.custom_salary_structure:
        return

    ss_company = frappe.db.get_value(
        "Salary Structure", doc.custom_salary_structure, "company"
    )
    if ss_company and ss_company != doc.company:
        frappe.throw(
            _("Salary Structure {0} belongs to company {1}, not {2}").format(
                doc.custom_salary_structure, ss_company, doc.company
            )
        )


def create_salary_structure_assignment(doc):
    """Create and submit a Salary Structure Assignment for the employee.

    Idempotent on after_insert: skip if an active SSA already matches both
    the structure and the base. on_update path always cancels the prior
    active SSA before calling here, so this guard is for first-save re-runs
    only.

    The base is the gross/base amount entered on the Employee (native `ctc`
    field), copied verbatim to SSA.base. ERPNext's standard Salary Structure
    formulas then derive the breakup from `base` — no custom formula here.
    """
    new_base = flt(doc.get("ctc"))
    existing = frappe.db.get_value(
        "Salary Structure Assignment",
        {
            "employee": doc.name,
            "salary_structure": doc.custom_salary_structure,
            "docstatus": 1,
        },
        "base",
    )
    if existing is not None and flt(existing) == new_base:
        return

    ssa = frappe.new_doc("Salary Structure Assignment")
    ssa.employee = doc.name
    ssa.salary_structure = doc.custom_salary_structure
    ssa.from_date = doc.date_of_joining or getdate()
    ssa.company = doc.company
    ssa.base = new_base
    ssa.insert(ignore_permissions=True)
    ssa.submit()

    frappe.msgprint(
        _("Salary Structure Assignment {0} created").format(ssa.name),
        alert=True,
    )


# Employee field -> SSA field. Mirrors _OPENING_BALANCE_FIELDS in
# salary_structure_assignment_hooks, which seeds these onto *new* assignments.
_OPENING_BALANCE_FIELDS = {
    "custom_taxable_earnings_till_date": "taxable_earnings_till_date",
    "custom_tax_deducted_till_date": "tax_deducted_till_date",
}


def sync_opening_balances_to_assignment(doc, previous):
    """Push edited opening balances onto the employee's active assignment.

    The SSA hook only seeds these on insert, so editing them on an Employee
    whose assignment already exists would otherwise change nothing — and
    neither field is one of the triggers (structure / CTC) that makes
    `on_update_master_data` cancel and rebuild the assignment.

    Only fields the user actually changed in *this* save are pushed, and only
    onto the latest submitted assignment. That keeps a figure corrected
    directly on the SSA intact: nothing is overwritten unless HR deliberately
    edits the Employee value again. Both fields are `allow_on_submit`, so the
    submitted assignment takes the update without a cancel/amend.
    """
    changed = {
        ssa_field: flt(doc.get(emp_field))
        for emp_field, ssa_field in _OPENING_BALANCE_FIELDS.items()
        if flt(previous.get(emp_field)) != flt(doc.get(emp_field))
    }
    if not changed:
        return

    latest = frappe.get_all(
        "Salary Structure Assignment",
        filters={"employee": doc.name, "docstatus": 1},
        order_by="from_date desc, creation desc",
        limit=1,
        pluck="name",
    )
    if not latest:
        return

    ssa = frappe.get_doc("Salary Structure Assignment", latest[0])
    for ssa_field, value in changed.items():
        ssa.set(ssa_field, value)
    ssa.flags.ignore_permissions = True
    ssa.save()

    frappe.msgprint(
        _("Opening balances updated on Salary Structure Assignment {0}").format(ssa.name),
        alert=True,
    )


def end_date_existing_assignment(doc):
    """Cancel any active Salary Structure Assignment for this employee.

    Called when either the salary structure or the CTC changes — both cases
    need the prior assignment cancelled so a fresh one can be created.
    """
    assignments = frappe.get_all(
        "Salary Structure Assignment",
        filters={
            "employee": doc.name,
            "docstatus": 1,
        },
        order_by="from_date desc",
        pluck="name",
    )
    for name in assignments:
        old_ssa = frappe.get_doc("Salary Structure Assignment", name)
        old_ssa.flags.ignore_permissions = True
        old_ssa.cancel()
        frappe.msgprint(
            _("Previous Salary Structure Assignment {0} cancelled").format(
                old_ssa.name
            ),
            alert=True,
        )
