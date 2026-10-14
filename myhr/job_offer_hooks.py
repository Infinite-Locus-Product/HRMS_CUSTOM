"""Job Offer doc_events — wired in hooks.py.

Computes the CTC breakdown stored on Job Offer (fields declared in
fixtures/custom_field.json, rows in the `Job Offer Salary Component` child
table). HR enters only the Monthly column and Variable Pay; everything else is
derived here on every save so the print format can read stored values.

Rules (agreed 2026-09-11):
- Gross CTC          = Σ Earning rows (components table)
- Total Fixed CTC    = Gross + Σ Employer Contribution rows (components table)
- Total Deductions   = Σ rows in the deductions table (employee-side only)
- Take Home          = Gross − Total Deductions
- Total Annual CTC   = Total Fixed CTC × 12 + Variable Pay (annual)
Employer contributions are never treated as deductions.
"""

import frappe
from frappe import _
from frappe.utils import flt

COMPONENTS_TABLE = "custom_ctc_components"
DEDUCTIONS_TABLE = "custom_ctc_deductions"
EARNING = "Earning"
DEDUCTION = "Deduction"
EMPLOYER = "Employer Contribution"
MONTHS = 12


def validate(doc, method=None):
	compute_ctc(doc)


def compute_ctc(doc):
	components = doc.get(COMPONENTS_TABLE) or []
	deductions = doc.get(DEDUCTIONS_TABLE) or []

	_prepare_rows(components, allowed={EARNING, EMPLOYER}, table_label=_("Components"))
	_prepare_rows(deductions, allowed={DEDUCTION}, table_label=_("Deductions"))

	gross_m = sum(flt(r.monthly) for r in components if r.component_type == EARNING)
	employer_m = sum(flt(r.monthly) for r in components if r.component_type == EMPLOYER)
	fixed_m = gross_m + employer_m
	ded_m = sum(flt(r.monthly) for r in deductions)

	doc.custom_gross_ctc_monthly = flt(gross_m, 2)
	doc.custom_gross_ctc_annual = flt(gross_m * MONTHS, 2)
	doc.custom_total_fixed_ctc_monthly = flt(fixed_m, 2)
	doc.custom_total_fixed_ctc_annual = flt(fixed_m * MONTHS, 2)
	doc.custom_total_deductions_monthly = flt(ded_m, 2)
	doc.custom_take_home_monthly = flt(gross_m - ded_m, 2)
	doc.custom_total_annual_ctc = flt(fixed_m * MONTHS + flt(doc.get("custom_variable_pay_annual")), 2)


def _prepare_rows(rows, allowed, table_label):
	"""Fill `annual` and `component_type`, and reject rows of the wrong type."""
	for row in rows:
		if not row.component_type and row.salary_component:
			row.component_type = frappe.db.get_value("Salary Component", row.salary_component, "type")
		if row.component_type not in allowed:
			frappe.throw(
				_("{0} row {1}: {2} is a {3} component and cannot be listed here. Allowed: {4}.").format(
					table_label,
					row.idx,
					frappe.bold(row.salary_component),
					row.component_type or _("unknown"),
					", ".join(sorted(allowed)),
				),
				title=_("Wrong component type"),
			)
		row.monthly = flt(row.monthly, 2)
		row.annual = flt(row.monthly * MONTHS, 2)
