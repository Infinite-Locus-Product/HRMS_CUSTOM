"""Tests for the Job Offer CTC breakdown (`myhr.job_offer_hooks.compute_ctc`).

Uses the numbers from the HR CTC sheet as the worked example.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from myhr.job_offer_hooks import COMPONENTS_TABLE, DEDUCTIONS_TABLE

TEST_COMPANY = "_Test Company"
APPLICANT_EMAIL = "ctc.applicant@example.com"
DESIGNATION = "_Test CTC Designation"

# (name, type, monthly)
SHEET_COMPONENTS = [
	("_Test Basic + DA", "Earning", 25313),
	("_Test HRA", "Earning", 12656),
	("_Test Statutory Bonus", "Earning", 0),
	("_Test LTA Reimbursement", "Earning", 5063),
	("_Test Special Allowance", "Earning", 5644),
	("_Test PF Employer", "Employer Contribution", 1950),
	("_Test ESI Employer", "Employer Contribution", 0),
]
SHEET_DEDUCTIONS = [
	("_Test PF Employee", "Deduction", 1800),
	("_Test ESI Employee", "Deduction", 0),
	("_Test Professional Tax", "Deduction", 200),
	("_Test Income Tax", "Deduction", 0),
]


def _ensure_company():
	if frappe.db.exists("Company", TEST_COMPANY):
		return TEST_COMPANY
	existing = frappe.db.get_value("Company", {}, "name")
	if existing:
		return existing
	raise RuntimeError("No Company in this site; create one first.")


def _ensure_salary_component(name, component_type):
	if frappe.db.exists("Salary Component", name):
		return name
	sc = frappe.new_doc("Salary Component")
	sc.salary_component = name
	sc.salary_component_abbr = "T" + frappe.generate_hash(length=4).upper()
	sc.type = component_type
	sc.depends_on_payment_days = 0
	sc.insert(ignore_permissions=True)
	return name


def _ensure_designation():
	if not frappe.db.exists("Designation", DESIGNATION):
		frappe.get_doc({"doctype": "Designation", "designation_name": DESIGNATION}).insert(ignore_permissions=True)
	return DESIGNATION


def _make_applicant():
	"""One applicant per offer — HRMS rejects a second Job Offer for the same applicant,
	and the test transaction only rolls back per class."""
	email = APPLICANT_EMAIL.replace("@", f"+{frappe.generate_hash(length=6)}@")
	ja = frappe.get_doc({"doctype": "Job Applicant", "applicant_name": "CTC Applicant", "email_id": email, "status": "Open"})
	ja.insert(ignore_permissions=True)
	return ja.name


def _make_offer(components=SHEET_COMPONENTS, deductions=SHEET_DEDUCTIONS, variable=0):
	offer = frappe.get_doc(
		{
			"doctype": "Job Offer",
			"job_applicant": _make_applicant(),
			"applicant_name": "CTC Applicant",
			"status": "Awaiting Response",
			"offer_date": frappe.utils.today(),
			"designation": _ensure_designation(),
			"company": _ensure_company(),
			"custom_variable_pay_annual": variable,
			COMPONENTS_TABLE: [
				{"salary_component": _ensure_salary_component(n, t), "monthly": m} for n, t, m in components
			],
			DEDUCTIONS_TABLE: [
				{"salary_component": _ensure_salary_component(n, t), "monthly": m} for n, t, m in deductions
			],
		}
	)
	offer.insert(ignore_permissions=True)
	return offer


class TestJobOfferCTC(IntegrationTestCase):
	# NOTE: the HR sheet shows Gross 48,675 because each line was rounded before
	# summing; the exact component sum is 48,676 and that is what we store.
	def test_sheet_example_totals(self):
		offer = _make_offer(variable=67500)
		self.assertEqual(offer.custom_gross_ctc_monthly, 48676)
		self.assertEqual(offer.custom_gross_ctc_annual, 584112)
		self.assertEqual(offer.custom_total_fixed_ctc_monthly, 50626)
		self.assertEqual(offer.custom_total_fixed_ctc_annual, 607512)
		self.assertEqual(offer.custom_total_deductions_monthly, 2000)
		self.assertEqual(offer.custom_take_home_monthly, 46676)
		self.assertEqual(offer.custom_total_annual_ctc, 675012)
		for row in offer.get(COMPONENTS_TABLE) + offer.get(DEDUCTIONS_TABLE):
			self.assertEqual(row.annual, row.monthly * 12)
			self.assertTrue(row.component_type)

	def test_employer_contribution_not_in_gross_or_deductions(self):
		offer = _make_offer(
			components=[("_Test Basic + DA", "Earning", 10000), ("_Test PF Employer", "Employer Contribution", 1200)],
			deductions=[],
		)
		self.assertEqual(offer.custom_gross_ctc_monthly, 10000)
		self.assertEqual(offer.custom_total_fixed_ctc_monthly, 11200)
		self.assertEqual(offer.custom_total_deductions_monthly, 0)
		self.assertEqual(offer.custom_take_home_monthly, 10000)

	def test_wrong_type_in_components_table_throws(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			_make_offer(components=[("_Test PF Employee", "Deduction", 1800)], deductions=[])
		self.assertIn("cannot be listed here", str(ctx.exception))

	def test_wrong_type_in_deductions_table_throws(self):
		with self.assertRaises(frappe.ValidationError):
			_make_offer(components=[], deductions=[("_Test HRA", "Earning", 100)])

	def test_empty_tables_give_zero_summary(self):
		offer = _make_offer(components=[], deductions=[])
		for f in (
			"custom_gross_ctc_monthly", "custom_gross_ctc_annual", "custom_total_fixed_ctc_monthly",
			"custom_total_fixed_ctc_annual", "custom_total_deductions_monthly", "custom_take_home_monthly",
			"custom_total_annual_ctc",
		):
			self.assertEqual(offer.get(f), 0, f)

	def test_resave_recomputes(self):
		offer = _make_offer(variable=0)
		offer.get(COMPONENTS_TABLE)[0].monthly = 26000  # Basic 25,313 -> 26,000
		offer.custom_variable_pay_annual = 12000
		offer.save(ignore_permissions=True)
		self.assertEqual(offer.custom_gross_ctc_monthly, 49363)
		self.assertEqual(offer.custom_total_fixed_ctc_monthly, 51313)
		self.assertEqual(offer.custom_take_home_monthly, 47363)
		self.assertEqual(offer.custom_total_annual_ctc, 51313 * 12 + 12000)
