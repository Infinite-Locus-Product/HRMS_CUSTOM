"""Tests for myhr.notice_recovery — pricing a notice-period shortfall.

    recovery = (monthly component / days per month) * shortfall days

This decides money taken out of someone's final pay, so the cases that produce
ZERO matter as much as the arithmetic: a waived notice period, an unconfigured
component, an employee with no salary structure. Each must come back with a
reason rather than a silent nought.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, nowdate

from myhr.notice_recovery import get_component_amount, get_recovery

STRUCTURE = "_Test Notice Recovery Structure"
FIXED = "_Test Fixed Component"
FORMULA = "_Test Formula Component"
DERIVED = "_Test Derived Component"


def _component(name, abbr, depends_on_payment_days=1):
	"""Create (or correct) a Salary Component.

	`depends_on_payment_days` matters: Salary Structure copies it from the
	component master onto the row, and refuses a formula-based component that
	depends on payment days when its formula references another such component.
	"""
	if frappe.db.exists("Salary Component", name):
		frappe.db.set_value(
			"Salary Component", name, "depends_on_payment_days", depends_on_payment_days
		)
		return name
	frappe.get_doc({
		"doctype": "Salary Component", "salary_component": name,
		"salary_component_abbr": abbr, "type": "Earning",
		"depends_on_payment_days": depends_on_payment_days,
	}).insert(ignore_permissions=True)
	return name


class TestNoticeRecovery(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = frappe.db.get_value("Company", {}, "name")
		cls._settings = {
			"component": frappe.db.get_single_value("HR Settings", "custom_notice_recovery_component"),
			"divisor": frappe.db.get_single_value("HR Settings", "custom_notice_recovery_divisor"),
		}

		_component(FIXED, "TFC")
		_component(FORMULA, "TFM")
		_component(DERIVED, "TDC", depends_on_payment_days=0)

		if not frappe.db.exists("Salary Structure", STRUCTURE):
			doc = frappe.get_doc({
				"doctype": "Salary Structure", "name": STRUCTURE, "company": cls.company,
				"payroll_frequency": "Monthly", "currency": "INR",
				"earnings": [
					{"salary_component": FIXED, "abbr": "TFC", "amount": 9000},
					# Exercises the formula path, as real structures use.
					{"salary_component": FORMULA, "abbr": "TFM",
					 "amount_based_on_formula": 1, "formula": "base * 0.5"},
					# Exercises a formula that references an earlier component.
					# depends_on_payment_days off: HRMS refuses a formula-based
					# component that also depends on payment days when its
					# formula already references one.
					{"salary_component": DERIVED, "abbr": "TDC",
					 "amount_based_on_formula": 1, "formula": "TFM * 0.1",
					 "depends_on_payment_days": 0},
				],
			})
			doc.insert(ignore_permissions=True)
			doc.submit()

		cls.employee = cls._employee_with_structure()

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_single_value(
			"HR Settings", "custom_notice_recovery_component", cls._settings["component"]
		)
		frappe.db.set_single_value(
			"HR Settings", "custom_notice_recovery_divisor", cls._settings["divisor"]
		)
		super().tearDownClass()

	@classmethod
	def _employee_with_structure(cls):
		from myhr.tests.test_employee_separation import _ensure_hierarchy_employee

		emp = _ensure_hierarchy_employee("notice.recovery@example.com", "_Test Notice Recovery")
		if not frappe.db.exists(
			"Salary Structure Assignment", {"employee": emp.name, "docstatus": 1}
		):
			ssa = frappe.get_doc({
				"doctype": "Salary Structure Assignment", "employee": emp.name,
				"salary_structure": STRUCTURE, "company": emp.company,
				"from_date": add_days(nowdate(), -365), "base": 60000, "currency": "INR",
			})
			ssa.insert(ignore_permissions=True)
			ssa.submit()
		return emp

	def setUp(self):
		frappe.db.set_single_value("HR Settings", "custom_notice_recovery_component", FIXED)
		frappe.db.set_single_value("HR Settings", "custom_notice_recovery_divisor", 30)

	# -- reading the component ---------------------------------------------
	def test_a_fixed_amount_is_read_straight_off_the_structure(self):
		amount, reason = get_component_amount(self.employee.name, FIXED)
		self.assertIsNone(reason)
		self.assertEqual(flt(amount), 9000)

	def test_a_formula_is_evaluated_against_the_assignment_base(self):
		amount, reason = get_component_amount(self.employee.name, FORMULA)
		self.assertIsNone(reason)
		self.assertEqual(flt(amount), 30000, "base 60000 * 0.5")

	def test_a_formula_can_reference_an_earlier_component(self):
		"""Real structures do this — `BS * 0.5`, `(base/12) - BS - HRA`."""
		amount, reason = get_component_amount(self.employee.name, DERIVED)
		self.assertIsNone(reason)
		self.assertEqual(flt(amount), 3000, "TFM 30000 * 0.1")

	def test_a_component_absent_from_the_structure_explains_itself(self):
		amount, reason = get_component_amount(self.employee.name, "Basic")
		self.assertEqual(flt(amount), 0)
		self.assertIn("not an earning", reason)

	# -- the recovery -------------------------------------------------------
	def test_the_recovery_is_per_day_times_days(self):
		result = get_recovery(self.employee.name, 16)
		self.assertEqual(result["per_day"], 300, "9000 / 30")
		self.assertEqual(result["amount"], 4800, "300 * 16")
		self.assertIsNone(result["reason"])

	def test_the_divisor_changes_the_rate(self):
		frappe.db.set_single_value("HR Settings", "custom_notice_recovery_divisor", 26)
		result = get_recovery(self.employee.name, 26)
		self.assertEqual(result["per_day"], flt(9000 / 26, 2))
		self.assertEqual(result["amount"], 9000, "a full month's worth of days")

	def test_a_zero_divisor_falls_back_rather_than_dividing_by_zero(self):
		frappe.db.set_single_value("HR Settings", "custom_notice_recovery_divisor", 0)
		result = get_recovery(self.employee.name, 30)
		self.assertEqual(result["amount"], 9000, "treated as 30")

	# -- the cases that must produce zero -----------------------------------
	def test_a_waived_notice_period_recovers_nothing(self):
		"""The entire point of waiving it."""
		result = get_recovery(self.employee.name, 16, waiver="Yes")
		self.assertEqual(result["amount"], 0)
		self.assertIn("waived", result["reason"])

	def test_no_shortfall_means_no_recovery(self):
		result = get_recovery(self.employee.name, 0)
		self.assertEqual(result["amount"], 0)
		self.assertIsNone(result["reason"], "nothing owed is not a problem to report")

	def test_an_unconfigured_component_says_so(self):
		frappe.db.set_single_value("HR Settings", "custom_notice_recovery_component", None)
		result = get_recovery(self.employee.name, 16)
		self.assertEqual(result["amount"], 0)
		self.assertIn("HR Settings", result["reason"])

	def test_an_employee_without_a_salary_structure_says_so(self):
		from myhr.tests.test_employee_separation import _ensure_hierarchy_employee

		bare = _ensure_hierarchy_employee("notice.nossa@example.com", "_Test No SSA")
		result = get_recovery(bare.name, 16)
		self.assertEqual(result["amount"], 0)
		self.assertIn("Salary Structure Assignment", result["reason"])
