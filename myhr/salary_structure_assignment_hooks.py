"""Salary Structure Assignment hooks owned by myhr."""

import frappe
from frappe.utils import flt

# Employee field -> SSA field, for the opening-balance seed below.
_OPENING_BALANCE_FIELDS = {
    "custom_taxable_earnings_till_date": "taxable_earnings_till_date",
    "custom_tax_deducted_till_date": "tax_deducted_till_date",
}


def fill_income_tax_slab_from_employee(doc, method=None):
    """Propagate Employee.custom_income_tax_slab onto SSA.income_tax_slab.

    Wired on `before_validate` so this runs BEFORE HRMS's controller
    `validate_income_tax_slab` (salary_structure_assignment.py:75-80) which
    throws "Income Tax Slab is mandatory ..." when the assigned Salary
    Structure has an Income Tax component but SSA's slab is empty. With
    this hook, HR sets the slab once on Employee and every new SSA picks
    it up automatically.

    Won't overwrite an explicit slab on SSA — user choice on the SSA form
    always wins. If both Employee and SSA are empty, HRMS's native
    validation still fires (correct: someone needs to set it somewhere).
    """
    if doc.income_tax_slab:
        return
    if not doc.employee:
        return
    emp_slab = frappe.db.get_value("Employee", doc.employee, "custom_income_tax_slab")
    if emp_slab:
        doc.income_tax_slab = emp_slab


def fill_opening_balances_from_employee(doc, method=None):
    """Seed SSA opening balances from the Employee record.

    `Taxable Earnings Till Date` / `Tax Deducted Till Date` are HRMS fields on
    SSA only, and HRMS warns ("Missing Opening Entries") when an assignment
    starts mid payroll period with both blank. myHR builds the SSA
    programmatically from the Employee form
    (`employee_master_data.create_salary_structure_assignment`), so without this
    hook there is no way to answer that warning up front — HR has to reopen each
    generated assignment afterwards.

    Seeds on insert only. An explicit figure already on the SSA always wins, and
    later edits to the SSA (both fields are `allow_on_submit`) are never
    overwritten from Employee — the SSA is the record payroll actually reads, so
    a correction made there has to stick.
    """
    if not doc.is_new() or not doc.employee:
        return

    emp = frappe.db.get_value(
        "Employee", doc.employee, list(_OPENING_BALANCE_FIELDS), as_dict=True
    )
    if not emp:
        return

    for emp_field, ssa_field in _OPENING_BALANCE_FIELDS.items():
        if flt(doc.get(ssa_field)):
            continue
        if flt(emp.get(emp_field)):
            doc.set(ssa_field, flt(emp.get(emp_field)))
