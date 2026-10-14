"""Tests for myHR's additions to HRMS's Full and Final Statement (stage 9).

The controller itself is HRMS's; what is tested here is the myHR layer — the
recoveries pushed in from the exit flow, the net, and the four gates on submit.

The managed receivable rows get the most attention, because they are the part
that silently corrupts a settlement if it goes wrong: a duplicated row
double-recovers, a stale row recovers money that was already written off.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, nowdate

from myhr.full_and_final_hooks import (
	IT_RECOVERY_COMPONENT,
	PHYSICAL_RECOVERY_COMPONENT,
	SHORTFALL_COMPONENT,
)
from myhr.tests.test_employee_separation import (
	_clear_separations,
	_ensure_employee,
	_ensure_hierarchy_employee,
	_ensure_user_for,
	_open_downstream,
)

FNF = "Full and Final Statement"
MANAGER_CLEARANCE = "Separation Manager Clearance"
IT_CLEARANCE = "Separation IT Clearance"


def _clear(doctype, employee):
	for name in frappe.get_all(doctype, filters={"employee": employee}, pluck="name"):
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete(ignore_permissions=True)


class TestFullAndFinalStatement(IntegrationTestCase):
	SEPARATION_WORKFLOW = "Employee Separation Approval"
	CLEARANCE_WORKFLOW = MANAGER_CLEARANCE

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._recovery_component = frappe.db.get_single_value(
			"HR Settings", "custom_notice_recovery_component"
		)
		cls._alerts = {}
		for wf in (cls.SEPARATION_WORKFLOW, cls.CLEARANCE_WORKFLOW):
			cls._alerts[wf] = frappe.db.get_value("Workflow", wf, "send_email_alert")
			frappe.db.set_value("Workflow", wf, "send_email_alert", 0)
		frappe.clear_cache()

		cls.l1 = _ensure_hierarchy_employee("fnf.l1@example.com", "_Fnf L1", with_user=True)
		cls.l2 = _ensure_hierarchy_employee("fnf.l2@example.com", "_Fnf L2", with_user=True)
		cls.successor = _ensure_hierarchy_employee("fnf.succ@example.com", "_Fnf Succ")
		cls.employee = _ensure_employee()
		cls.employee.reports_to = cls.l1.name
		cls.employee.custom_l2_manager = cls.l2.name
		cls.employee.save(ignore_permissions=True)
		cls.emp_user = _ensure_user_for(cls.employee)

	@classmethod
	def tearDownClass(cls):
		for wf, value in cls._alerts.items():
			frappe.db.set_value("Workflow", wf, "send_email_alert", value)
		frappe.db.set_single_value(
			"HR Settings", "custom_notice_recovery_component", cls._recovery_component
		)
		frappe.clear_cache()
		super().tearDownClass()

	def setUp(self):
		frappe.set_user("Administrator")
		# Shortfall pricing off by default: with no component configured the
		# recovery is zero, so the tests about row mechanics and totals are not
		# perturbed by whatever salary data happens to exist. The tests that
		# care switch it on through _priced_employee().
		frappe.db.set_single_value("HR Settings", "custom_notice_recovery_component", None)
		self._cleanup()
		self.separation = self._approved_separation()

	def tearDown(self):
		frappe.set_user("Administrator")
		self._cleanup()

	def _cleanup(self):
		# Cascades through all four downstream records in dependency order.
		_clear_separations(self.employee.name)

	# -- fixtures -----------------------------------------------------------
	def _approved_separation(self):
		from frappe.model.workflow import apply_workflow

		doc = frappe.new_doc("Employee Separation")
		doc.employee = self.employee.name
		doc.company = self.employee.company
		doc.boarding_begins_on = nowdate()
		doc.custom_resignation_reason = "Personal"
		doc.custom_buyout_notice_period = "No"
		doc.custom_requested_relieving_date = add_days(nowdate(), 30)
		doc.insert(ignore_permissions=True)

		approval = {
			"custom_decision": "Approve",
			"custom_approved_relieving_date": add_days(nowdate(), 30),
			"custom_notice_period_waiver": "No",
			"custom_retention_discussion_held": "Yes",
		}
		for user, action in ((self.emp_user, "Submit"), (self.l1.user_id, "Approve"),
		                     (self.l2.user_id, "Approve")):
			frappe.set_user(user)
			try:
				target = frappe.get_doc("Employee Separation", doc.name)
				if action == "Approve":
					target.update(approval)
					target.save()
				doc = apply_workflow(target, action)
			finally:
				frappe.set_user("Administrator")
		return doc.name

	def _it_clearance(self, recovery=18000, submit=True):
		doc = _open_downstream(IT_CLEARANCE, self.separation)
		doc.assets = []
		doc.append("assets", {"asset_type": "Laptop", "returned": 1, "asset_condition": "Good"})
		if recovery:
			doc.append("assets", {"asset_type": "Mobile", "returned": 0,
			                      "asset_condition": "Missing", "recovery_amount": recovery})
		doc.insert(ignore_permissions=True)
		if submit:
			doc.submit()
		return doc

	def _manager_clearance(self, complete=True):
		from frappe.model.workflow import apply_workflow

		doc = _open_downstream(MANAGER_CLEARANCE, self.separation)
		doc.handover_documents = []
		doc.append("handover_documents", {"title": "KT", "external_link": "https://kt"})
		doc.primary_successor = self.successor.name
		doc.downloaded_payslips = 1
		doc.downloaded_tax_slips = 1
		doc.cleared_personal_files = 1
		doc.insert(ignore_permissions=True)

		frappe.set_user(self.emp_user)
		try:
			doc = apply_workflow(frappe.get_doc(MANAGER_CLEARANCE, doc.name), "Submit")
		finally:
			frappe.set_user("Administrator")

		if complete:
			frappe.set_user(self.l1.user_id)
			try:
				target = frappe.get_doc(MANAGER_CLEARANCE, doc.name)
				target.kt_handover_received = "Yes"
				target.client_handoff_complete = "Not Applicable"
				target.code_repository_transferred = 1
				target.access_revocation_not_applicable = 1
				target.manager_remarks = "Released."
				target.save()
				doc = apply_workflow(target, "Complete")
			finally:
				frappe.set_user("Administrator")
		return doc

	def _statement(self, **overrides):
		# Approval raises one automatically; clear it so each test builds the
		# statement it needs. Auto-creation itself is tested elsewhere.
		name = frappe.db.get_value(FNF, {"employee": self.employee.name, "docstatus": 0}, "name")
		if name:
			frappe.delete_doc(FNF, name, force=True, ignore_permissions=True)
		doc = frappe.new_doc(FNF)
		doc.employee = self.employee.name
		doc.company = self.employee.company
		doc.transaction_date = nowdate()
		doc.update(overrides)
		return doc

	def _receivable(self, doc, component):
		return next((r for r in doc.receivables if r.component == component), None)

	# -- context ------------------------------------------------------------
	def test_the_separation_is_found_automatically(self):
		doc = self._statement()
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.custom_employee_separation, self.separation)

	def test_the_it_recovery_is_pulled_in(self):
		self._it_clearance(recovery=18000)
		doc = self._statement()
		doc.insert(ignore_permissions=True)
		self.assertEqual(flt(doc.custom_it_asset_recovery), 18000)

	def test_shortfall_days_are_copied_from_the_separation(self):
		"""Copied in code, because the link is assigned during the same validate."""
		expected = frappe.db.get_value(
			"Employee Separation", self.separation, "custom_notice_period_shortfall"
		)
		doc = self._statement()
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.custom_notice_period_shortfall_days, expected)

	# -- managed receivable rows -------------------------------------------
	def test_the_it_recovery_becomes_a_receivable_row(self):
		self._it_clearance(recovery=18000)
		doc = self._statement()
		doc.insert(ignore_permissions=True)

		row = self._receivable(doc, IT_RECOVERY_COMPONENT)
		self.assertIsNotNone(row)
		self.assertEqual(flt(row.amount), 18000)
		self.assertEqual(row.reference_document_type, IT_CLEARANCE)

	def test_no_shortfall_row_without_a_configured_component(self):
		"""The amount is calculated now, not typed. With nothing configured in
		HR Settings there is no rate, so nothing is recovered — and the row must
		not appear at all rather than appear as zero."""
		original = frappe.db.get_single_value("HR Settings", "custom_notice_recovery_component")
		frappe.db.set_single_value("HR Settings", "custom_notice_recovery_component", None)
		try:
			doc = self._statement()
			doc.insert(ignore_permissions=True)
			self.assertEqual(flt(doc.custom_notice_shortfall_recovery), 0)
			self.assertIsNone(self._receivable(doc, SHORTFALL_COMPONENT))
		finally:
			frappe.db.set_single_value(
				"HR Settings", "custom_notice_recovery_component", original
			)

	def test_resaving_updates_the_row_instead_of_adding_another(self):
		"""Duplicated rows would double-recover from the settlement."""
		self._it_clearance(recovery=18000)
		doc = self._statement()
		doc.insert(ignore_permissions=True)
		for _ in range(3):
			doc.save(ignore_permissions=True)

		rows = [r for r in doc.receivables if r.component == IT_RECOVERY_COMPONENT]
		self.assertEqual(len(rows), 1)
		self.assertEqual(flt(rows[0].amount), 18000)

	def test_a_recovery_dropped_to_zero_removes_its_row(self):
		"""A stale row would recover money that was written off."""
		# Draft, because a submitted clearance's asset table cannot be changed.
		it = self._it_clearance(recovery=18000, submit=False)
		doc = self._statement()
		doc.insert(ignore_permissions=True)
		self.assertIsNotNone(self._receivable(doc, IT_RECOVERY_COMPONENT))

		it.assets = [a for a in it.assets if a.asset_condition != "Missing"]
		it.save(ignore_permissions=True)
		doc.save(ignore_permissions=True)
		self.assertIsNone(self._receivable(doc, IT_RECOVERY_COMPONENT))

	def test_no_rows_when_there_is_nothing_to_recover(self):
		doc = self._statement()
		doc.insert(ignore_permissions=True)
		self.assertIsNone(self._receivable(doc, IT_RECOVERY_COMPONENT))
		self.assertIsNone(self._receivable(doc, SHORTFALL_COMPONENT))

	# -- the net ------------------------------------------------------------
	def test_the_net_is_payable_minus_receivable(self):
		self._it_clearance(recovery=18000)
		doc = self._statement()
		doc.append("payables", {"component": "Bonus", "amount": 85000, "status": "Unsettled"})
		doc.insert(ignore_permissions=True)

		self.assertEqual(flt(doc.total_payable_amount), 85000)
		self.assertEqual(flt(doc.total_receivable_amount), 18000)
		self.assertEqual(flt(doc.custom_net_payable), 67000)

	def test_a_hand_set_net_is_overwritten(self):
		self._it_clearance(recovery=1000)
		doc = self._statement(custom_net_payable=999999)
		doc.insert(ignore_permissions=True)
		self.assertEqual(flt(doc.custom_net_payable), -1000)

	# -- gates --------------------------------------------------------------
	def _settle_rows(self, doc):
		"""HRMS refuses to submit while any line is Unsettled.

		Its before_submit runs ahead of myHR's gates, so the lines have to be
		settled first for the gates below to be reachable at all.
		"""
		for row in list(doc.payables) + list(doc.receivables):
			row.status = "Settled"
		doc.save(ignore_permissions=True)
		return doc

	def _ready_to_submit(self):
		self._manager_clearance(complete=True)
		self._it_clearance(recovery=18000, submit=True)
		doc = self._statement(custom_finance_remarks="Settled and closed.")
		doc.append("payables", {"component": "Bonus", "amount": 85000, "status": "Unsettled"})
		doc.insert(ignore_permissions=True)
		return self._settle_rows(doc)

	def test_it_submits_once_everything_is_in_place(self):
		doc = self._ready_to_submit()
		doc.submit()
		self.assertEqual(doc.docstatus, 1)

	def test_blocked_while_the_manager_clearance_is_unfinished(self):
		self._manager_clearance(complete=False)
		self._it_clearance(submit=True)
		doc = self._statement(custom_finance_remarks="Ready.")
		doc.insert(ignore_permissions=True)
		self._settle_rows(doc)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.submit()
		self.assertIn("Manager Clearance", str(caught.exception))

	def test_blocked_while_the_it_clearance_is_unsubmitted(self):
		self._manager_clearance(complete=True)
		self._it_clearance(submit=False)
		doc = self._statement(custom_finance_remarks="Ready.")
		doc.insert(ignore_permissions=True)
		self._settle_rows(doc)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.submit()
		self.assertIn("IT Clearance", str(caught.exception))

	def test_blocked_without_a_finance_sign_off(self):
		doc = self._ready_to_submit()
		doc.custom_finance_remarks = "   "  # whitespace is not a sign-off
		self._settle_rows(doc)
		self.assertRaises(frappe.MandatoryError, doc.submit)

	def _hr_clearance(self, damage=500):
		name = frappe.db.get_value(
			"Separation HR Clearance",
			{"employee_separation": self.separation, "docstatus": ["<", 2]}, "name",
		)
		doc = frappe.get_doc("Separation HR Clearance", name)
		doc.rehire_eligibility = "Yes"
		doc.asset_damage_recovery_amount = damage
		doc.save(ignore_permissions=True)
		return doc

	def test_physical_damage_from_the_hr_clearance_is_recovered_too(self):
		"""IT recovers hardware; HR recovers the badge, keys and parking tag.
		Both are money off the settlement, and only one of them used to arrive."""
		self._it_clearance(recovery=1100)
		self._hr_clearance(damage=500)

		doc = self._statement()
		doc.insert(ignore_permissions=True)

		self.assertEqual(flt(doc.custom_it_asset_recovery), 1100)
		self.assertEqual(flt(doc.custom_physical_asset_recovery), 500)
		self.assertEqual(flt(self._receivable(doc, IT_RECOVERY_COMPONENT).amount), 1100)
		self.assertEqual(flt(self._receivable(doc, PHYSICAL_RECOVERY_COMPONENT).amount), 500)
		self.assertEqual(flt(doc.total_receivable_amount), 1600)

	def test_the_two_recoveries_stay_separate_rows(self):
		"""Merging them would make the settlement impossible to query later."""
		self._it_clearance(recovery=1100)
		self._hr_clearance(damage=500)
		doc = self._statement()
		doc.insert(ignore_permissions=True)

		components = [r.component for r in doc.receivables]
		self.assertIn(IT_RECOVERY_COMPONENT, components)
		self.assertIn(PHYSICAL_RECOVERY_COMPONENT, components)

	def test_opening_the_statement_picks_up_a_clearance_filled_in_later(self):
		"""The statement is raised before IT has listed anything, so it must not
		wait for a save to notice."""
		doc = self._statement()
		doc.insert(ignore_permissions=True)
		self.assertEqual(flt(doc.custom_it_asset_recovery), 0)

		self._it_clearance(recovery=1100)

		# Re-open it exactly as Desk does.
		fresh = frappe.get_doc(FNF, doc.name)
		fresh.run_method("onload")
		self.assertEqual(flt(fresh.custom_it_asset_recovery), 1100)
		self.assertEqual(flt(self._receivable(fresh, IT_RECOVERY_COMPONENT).amount), 1100)

	# -- the shortfall is priced, not typed ---------------------------------
	def _priced_employee(self):
		"""Give the leaver a salary structure so the shortfall can be priced."""
		from myhr.tests.test_notice_recovery import FIXED, STRUCTURE, TestNoticeRecovery

		TestNoticeRecovery.setUpClass.__func__(TestNoticeRecovery)
		frappe.db.set_single_value("HR Settings", "custom_notice_recovery_component", FIXED)
		frappe.db.set_single_value("HR Settings", "custom_notice_recovery_divisor", 30)
		if not frappe.db.exists(
			"Salary Structure Assignment", {"employee": self.employee.name, "docstatus": 1}
		):
			ssa = frappe.get_doc({
				"doctype": "Salary Structure Assignment", "employee": self.employee.name,
				"salary_structure": STRUCTURE, "company": self.employee.company,
				"from_date": add_days(nowdate(), -365), "base": 60000, "currency": "INR",
			})
			ssa.insert(ignore_permissions=True)
			ssa.submit()

	def test_the_shortfall_is_priced_from_the_settings(self):
		self._priced_employee()
		doc = self._statement()
		doc.insert(ignore_permissions=True)

		days = doc.custom_notice_period_shortfall_days
		self.assertTrue(days, "the fixture separation should have a shortfall")
		self.assertEqual(
			flt(doc.custom_notice_shortfall_recovery), flt(9000 / 30 * days, 2),
			"component 9000 / 30 days * shortfall",
		)
		self.assertEqual(
			flt(self._receivable(doc, SHORTFALL_COMPONENT).amount),
			flt(doc.custom_notice_shortfall_recovery),
		)

	def test_a_waived_notice_period_is_not_recovered(self):
		"""Waiving the notice period is exactly what stops the charge."""
		self._priced_employee()
		frappe.db.set_value(
			"Employee Separation", self.separation, "custom_notice_period_waiver", "Yes"
		)
		doc = self._statement()
		doc.insert(ignore_permissions=True)

		self.assertEqual(flt(doc.custom_notice_shortfall_recovery), 0)
		self.assertIsNone(self._receivable(doc, SHORTFALL_COMPONENT))

	def test_a_hand_set_recovery_is_overwritten(self):
		"""It is a deduction from final pay; only the settings decide it."""
		self._priced_employee()
		doc = self._statement(custom_notice_shortfall_recovery=999999)
		doc.insert(ignore_permissions=True)
		self.assertNotEqual(flt(doc.custom_notice_shortfall_recovery), 999999)
