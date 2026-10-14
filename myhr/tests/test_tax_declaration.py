"""Tests for the PWA tax declaration endpoints.

Two things an employee does for themselves: choose a tax regime, and declare
the exemptions they intend to claim. Both write to doctypes they have no
permissions over, so the scoping — every endpoint resolves the employee from
the session, never from an argument — is what the tests lean on hardest.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, getdate, nowdate

from myhr.tax_declaration_api import (
	get_income_tax_slabs,
	get_my_tax_declaration,
	save_income_tax_slab,
	save_my_tax_declaration,
)
from myhr.tests.test_employee_separation import _ensure_hierarchy_employee, _ensure_user

DECLARATION = "Employee Tax Exemption Declaration"


class TestTaxDeclarationApi(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# The employee has to sit in a company that actually has a published tax
		# slab AND a payroll period covering today — otherwise both endpoints
		# correctly return nothing and the tests would be asserting against an
		# unconfigured company rather than against the code.
		cls.company = cls._configured_company()
		cls.employee = _ensure_hierarchy_employee("tax.decl@example.com", "_Test Tax Decl")
		cls.user = _ensure_user("tax.decl@example.com", "_Test Tax Decl")

		changed = False
		if not cls.employee.user_id:
			cls.employee.user_id = cls.user
			changed = True
		if cls.company and cls.employee.company != cls.company:
			cls.employee.company = cls.company
			changed = True
		if changed:
			cls.employee.save(ignore_permissions=True)

		cls.slab = frappe.db.get_value(
			"Income Tax Slab", {"company": cls.company, "disabled": 0, "docstatus": 1}, "name"
		) if cls.company else None

		cls._ensure_salary_structure()

	@classmethod
	def _ensure_salary_structure(cls):
		"""Give the employee an assignment so submission is possible.

		When the company computes HRA, HRMS refuses to submit a declaration for
		a period the employee had no salary structure in. Without one here the
		happy-path tests would only ever exercise the refusal.
		"""
		if not cls.company:
			return
		if frappe.db.exists(
			"Salary Structure Assignment", {"employee": cls.employee.name, "docstatus": 1}
		):
			return

		structure = frappe.db.get_value(
			"Salary Structure", {"company": cls.company, "docstatus": 1, "is_active": "Yes"}, "name"
		)
		if not structure:
			return

		# Start at the current period, not at joining: the earlier periods then
		# stay uncovered, which is what the "no salary structure" tests need.
		period = frappe.db.get_value(
			"Payroll Period",
			{"company": cls.company, "start_date": ("<=", nowdate()), "end_date": (">=", nowdate())},
			"start_date",
		)
		from_date = max(period, getdate(cls.employee.date_of_joining)) if period else cls.employee.date_of_joining

		ssa = frappe.get_doc({
			"doctype": "Salary Structure Assignment",
			"employee": cls.employee.name,
			"salary_structure": structure,
			"company": cls.company,
			"from_date": from_date,
			"base": 600000,
			"currency": "INR",
		})
		# Set explicitly: the employee's department may carry another company's
		# cost center, which HRMS would otherwise pull in and then reject.
		cost_center = frappe.db.get_value("Company", cls.company, "cost_center")
		if cost_center:
			ssa.append("payroll_cost_centers", {"cost_center": cost_center, "percentage": 100})
		ssa.insert(ignore_permissions=True)
		ssa.submit()

	@classmethod
	def _configured_company(cls):
		from frappe.utils import nowdate

		for slab in frappe.get_all(
			"Income Tax Slab", filters={"disabled": 0, "docstatus": 1}, pluck="company"
		):
			if frappe.db.exists("Payroll Period", {
				"company": slab, "start_date": ["<=", nowdate()], "end_date": [">=", nowdate()],
			}):
				return slab
		return None

	def setUp(self):
		if not self.company:
			self.skipTest("no company on this site has both a tax slab and a current payroll period")
		frappe.set_user("Administrator")
		self._clear()

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clear()

	def _clear(self):
		for name in frappe.get_all(
			DECLARATION, filters={"employee": self.employee.name}, pluck="name"
		):
			doc = frappe.get_doc(DECLARATION, name)
			if doc.docstatus == 1:
				doc.cancel()
			doc.delete(ignore_permissions=True)
		frappe.db.set_value(
			"Employee", self.employee.name, "custom_income_tax_slab", None, update_modified=False
		)

	def _as(self, fn, *args, **kwargs):
		frappe.set_user(self.employee.user_id)
		try:
			return fn(*args, **kwargs)
		finally:
			frappe.set_user("Administrator")

	# -- income tax slab ----------------------------------------------------
	def test_the_employee_sees_the_slabs_for_their_own_company(self):
		data = self._as(get_income_tax_slabs)
		self.assertEqual(data["employee"], self.employee.name)
		self.assertIsNone(data["selected"])
		self.assertTrue(data["slabs"], "the site has published slabs")
		for slab in data["slabs"]:
			self.assertIn("effective_from", slab)

	def test_choosing_a_slab_saves_it_to_the_employee_record(self):
		if not self.slab:
			self.skipTest("no income tax slab on this site")
		self._as(save_income_tax_slab, self.slab)
		self.assertEqual(
			frappe.db.get_value("Employee", self.employee.name, "custom_income_tax_slab"),
			self.slab,
		)

	def test_a_slab_from_another_company_is_refused(self):
		"""The endpoint takes a slab name, so it must check it is one they may pick."""
		self.assertRaises(
			frappe.ValidationError, self._as, save_income_tax_slab, "_Not A Real Slab"
		)

	def test_the_choice_can_be_cleared(self):
		if not self.slab:
			self.skipTest("no income tax slab on this site")
		self._as(save_income_tax_slab, self.slab)
		self._as(save_income_tax_slab, None)
		self.assertIsNone(
			frappe.db.get_value("Employee", self.employee.name, "custom_income_tax_slab")
		)

	# -- exemption declaration ----------------------------------------------
	def test_the_current_payroll_period_is_resolved(self):
		data = self._as(get_my_tax_declaration)
		self.assertEqual(data["employee"], self.employee.name)
		self.assertIsNotNone(data["payroll_period"], "a period covering today should exist")
		self.assertIsNone(data["declaration"], "nothing filed yet")

	def test_saving_creates_a_draft_for_this_period(self):
		data = self._as(get_my_tax_declaration)
		result = self._as(save_my_tax_declaration, frappe.as_json({"declarations": []}), 0)
		self.assertEqual(result["docstatus"], 0)
		self.assertFalse(result["submitted"])
		self.assertEqual(result["payroll_period"], data["payroll_period"]["name"])

	def test_saving_twice_updates_the_same_declaration(self):
		"""One declaration per employee per period — a second would be rejected
		by HRMS, so the endpoint must reuse the existing one."""
		first = self._as(save_my_tax_declaration, frappe.as_json({"declarations": []}), 0)
		second = self._as(save_my_tax_declaration, frappe.as_json({"declarations": []}), 0)
		self.assertEqual(first["name"], second["name"])
		self.assertEqual(
			frappe.db.count(DECLARATION, {"employee": self.employee.name, "docstatus": 0}), 1
		)

	def test_a_submitted_declaration_cannot_be_edited(self):
		self._as(save_my_tax_declaration, frappe.as_json({"declarations": []}), 1)
		self.assertRaises(
			frappe.ValidationError, self._as, save_my_tax_declaration,
			frappe.as_json({"declarations": []}), 0,
		)

	def test_submitting_marks_it_final(self):
		result = self._as(save_my_tax_declaration, frappe.as_json({"declarations": []}), 1)
		self.assertTrue(result["submitted"])
		self.assertEqual(result["docstatus"], 1)

	def test_rows_without_a_category_are_dropped(self):
		"""The app can leave a half-added row behind; it must not reach payroll."""
		payload = frappe.as_json({"declarations": [{"exemption_sub_category": "", "amount": 500}]})
		result = self._as(save_my_tax_declaration, payload, 0)
		self.assertEqual(result["declarations"], [])
		self.assertEqual(flt(result["total_declared_amount"]), 0)

	def test_hra_is_ignored_when_the_company_cannot_compute_it(self):
		"""HRMS throws 'set Basic and HRA component in Company' otherwise, which
		is not something the employee filling this in can fix."""
		basic, hra = frappe.db.get_value(
			"Company", self.company, ["basic_component", "hra_component"]
		) or (None, None)
		if basic and hra:
			self.skipTest("company has HRA components configured")

		result = self._as(
			save_my_tax_declaration, frappe.as_json({"monthly_house_rent": 15000}), 0
		)
		self.assertEqual(flt(result["monthly_house_rent"]), 0)

	def test_hra_is_computed_without_salary_slip_permission(self):
		"""Deriving HRA builds a preview Salary Slip, which an employee cannot
		create. That must not surface as a permission error on their own form."""
		basic, hra = frappe.db.get_value(
			"Company", self.company, ["basic_component", "hra_component"]
		) or (None, None)
		if not (basic and hra):
			self.skipTest("company cannot compute HRA")
		self.assertFalse(
			frappe.has_permission("Salary Slip", "create", user=self.user),
			"the test is meaningless if the employee can create salary slips",
		)

		result = self._as(
			save_my_tax_declaration,
			frappe.as_json({"monthly_house_rent": 15000, "rented_in_metro_city": 1}),
			0,
		)
		self.assertEqual(flt(result["monthly_house_rent"]), 15000)

	def test_the_declaration_is_owned_by_the_employee_not_administrator(self):
		"""The write runs as Administrator to reach the HRA calculation; the
		audit trail must still name whoever actually filed it."""
		result = self._as(save_my_tax_declaration, frappe.as_json({"declarations": []}), 0)
		owner, modified_by = frappe.db.get_value(
			"Employee Tax Exemption Declaration", result["name"], ["owner", "modified_by"]
		)
		self.assertEqual(owner, self.user)
		self.assertEqual(modified_by, self.user)

	# -- choosing the payroll period ----------------------------------------
	def test_the_selectable_periods_are_returned(self):
		data = self._as(get_my_tax_declaration)
		self.assertTrue(data["payroll_periods"], "the screen needs something to choose from")
		names = [p["name"] for p in data["payroll_periods"]]
		self.assertIn(data["payroll_period"]["name"], names)

	def test_a_specific_period_can_be_requested(self):
		periods = self._as(get_my_tax_declaration)["payroll_periods"]
		if len(periods) < 2:
			self.skipTest("only one payroll period on this company")

		other = next(
			p for p in periods if p["name"] != self._as(get_my_tax_declaration)["payroll_period"]["name"]
		)
		data = self._as(get_my_tax_declaration, other["name"])
		self.assertEqual(data["payroll_period"]["name"], other["name"])

	def test_a_period_from_another_company_is_refused(self):
		"""The period comes from the client, so it is the one tamperable input."""
		self.assertRaises(
			frappe.ValidationError, self._as, get_my_tax_declaration, "_Not A Real Period"
		)

	def test_declarations_are_kept_per_period(self):
		"""Each period has its own declaration; filing for one must not surface
		on another."""
		periods = self._as(get_my_tax_declaration)["payroll_periods"]
		if len(periods) < 2:
			self.skipTest("only one payroll period on this company")

		first, second = periods[0]["name"], periods[1]["name"]
		self._as(save_my_tax_declaration, frappe.as_json({"declarations": []}), 0, first)

		self.assertIsNotNone(self._as(get_my_tax_declaration, first)["declaration"])
		self.assertIsNone(self._as(get_my_tax_declaration, second)["declaration"])

	def test_saving_against_a_bogus_period_is_refused(self):
		self.assertRaises(
			frappe.ValidationError, self._as, save_my_tax_declaration,
			frappe.as_json({"declarations": []}), 0, "_Not A Real Period",
		)

	# -- periods the employee had no salary structure for --------------------
	def _period_without_structure(self):
		"""A period this employee cannot submit for.

		Only meaningful when the company computes HRA — otherwise HRMS never
		looks for a salary structure and every period is submittable.
		"""
		basic, hra = frappe.db.get_value(
			"Company", self.company, ["basic_component", "hra_component"]
		) or (None, None)
		if not (basic and hra):
			return None

		from hrms.hr.utils import get_salary_assignments

		for p in self._as(get_my_tax_declaration)["payroll_periods"]:
			if not get_salary_assignments(self.employee.name, p["name"]):
				return p["name"]
		return None

	def test_a_period_without_a_salary_structure_is_flagged(self):
		"""HRMS cannot work out HRA without one, so it refuses the submit. The
		screen needs to know before the employee fills the whole form in."""
		period = self._period_without_structure()
		if not period:
			self.skipTest("this company does not compute HRA, so no period is blocked")

		data = self._as(get_my_tax_declaration, period)
		self.assertFalse(data["has_salary_structure"])

	def test_submitting_for_such_a_period_is_refused_with_a_clear_message(self):
		period = self._period_without_structure()
		if not period:
			self.skipTest("this company does not compute HRA, so no period is blocked")

		with self.assertRaises(frappe.ValidationError) as caught:
			self._as(save_my_tax_declaration, frappe.as_json({"declarations": []}), 1, period)
		self.assertIn("salary structure", str(caught.exception).lower())

	def test_a_draft_can_still_be_saved_for_such_a_period(self):
		"""Only submission is blocked — the employee can keep their work."""
		period = self._period_without_structure()
		if not period:
			self.skipTest("this company does not compute HRA, so no period is blocked")

		result = self._as(save_my_tax_declaration, frappe.as_json({"declarations": []}), 0, period)
		self.assertEqual(result["docstatus"], 0)
		self.assertEqual(result["payroll_period"], period)
