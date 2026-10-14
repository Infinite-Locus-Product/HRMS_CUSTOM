"""Tests for Separation IT Clearance (exit flow stage 7).

The money rules get the most attention: this form decides what is deducted from
someone's final settlement, so both directions are tested — a charge that should
be required, and a charge that should not be allowed to exist.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, add_to_date, get_datetime, nowdate

from myhr.tests.test_employee_separation import (
	_clear_separations,
	_ensure_employee,
	_ensure_hierarchy_employee,
	_ensure_user_for,
	_open_downstream,
)

CLEARANCE = "Separation IT Clearance"
DOMAIN_FIELD = "custom_internal_email_domains"


def _clear_it_clearances(employee):
	for name in frappe.get_all(CLEARANCE, filters={"employee": employee}, pluck="name"):
		doc = frappe.get_doc(CLEARANCE, name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete(ignore_permissions=True)


class TestSeparationITClearance(IntegrationTestCase):
	SEPARATION_WORKFLOW = "Employee Separation Approval"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._alert = frappe.db.get_value("Workflow", cls.SEPARATION_WORKFLOW, "send_email_alert")
		frappe.db.set_value("Workflow", cls.SEPARATION_WORKFLOW, "send_email_alert", 0)
		cls._domains = frappe.db.get_single_value("HR Settings", DOMAIN_FIELD)
		frappe.db.set_single_value("HR Settings", DOMAIN_FIELD, "fixxly.in")
		frappe.clear_cache()

		cls.l1 = _ensure_hierarchy_employee("itc.l1@example.com", "_Itc L1", with_user=True)
		cls.l2 = _ensure_hierarchy_employee("itc.l2@example.com", "_Itc L2", with_user=True)
		cls.employee = _ensure_employee()
		cls.employee.reports_to = cls.l1.name
		cls.employee.custom_l2_manager = cls.l2.name
		cls.employee.save(ignore_permissions=True)
		cls.emp_user = _ensure_user_for(cls.employee)

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_value("Workflow", cls.SEPARATION_WORKFLOW, "send_email_alert", cls._alert)
		frappe.db.set_single_value("HR Settings", DOMAIN_FIELD, cls._domains)
		frappe.clear_cache()
		super().tearDownClass()

	def setUp(self):
		frappe.set_user("Administrator")
		# `_clear_separations` cascades through the four downstream records in
		# dependency order; they are auto-raised on approval and link to each
		# other, so deleting them piecemeal hits LinkExistsError.
		_clear_separations(self.employee.name)
		self.relieving_date = add_days(nowdate(), 30)
		self.separation = self._approved_separation()

	def tearDown(self):
		frappe.set_user("Administrator")
		_clear_separations(self.employee.name)

	def _approved_separation(self):
		from frappe.model.workflow import apply_workflow

		doc = frappe.new_doc("Employee Separation")
		doc.employee = self.employee.name
		doc.company = self.employee.company
		doc.boarding_begins_on = nowdate()
		doc.custom_resignation_reason = "Personal"
		doc.custom_buyout_notice_period = "No"
		doc.custom_requested_relieving_date = self.relieving_date
		doc.insert(ignore_permissions=True)

		approval = {
			"custom_decision": "Approve",
			"custom_approved_relieving_date": self.relieving_date,
			"custom_notice_period_waiver": "No",
			"custom_retention_discussion_held": "Yes",
		}
		for user, action, payload in (
			(self.emp_user, "Submit", None),
			(self.l1.user_id, "Approve", approval),
			(self.l2.user_id, "Approve", approval),
		):
			frappe.set_user(user)
			try:
				target = frappe.get_doc("Employee Separation", doc.name)
				if payload:
					target.update(payload)
					target.save()
				doc = apply_workflow(target, action)
			finally:
				frappe.set_user("Administrator")
		return doc.name

	def _new_clearance(self, rows=None, **overrides):
		doc = _open_downstream(CLEARANCE, self.separation)
		doc.assets = []
		for row in rows if rows is not None else [{"asset_type": "Laptop", "returned": 1,
		                                           "asset_condition": "Good"}]:
			doc.append("assets", row)
		doc.update(overrides)
		return doc

	# -- context + defaults -------------------------------------------------
	def test_last_working_day_comes_from_the_approved_date(self):
		doc = self._new_clearance()
		doc.insert(ignore_permissions=True)
		self.assertEqual(str(doc.last_working_day), str(self.relieving_date))

	def test_revocation_defaults_to_end_of_the_last_working_day(self):
		doc = self._new_clearance()
		doc.insert(ignore_permissions=True)
		self.assertEqual(
			get_datetime(doc.access_revocation_datetime),
			get_datetime(f"{self.relieving_date} 23:59:59"),
		)

	def test_only_one_it_clearance_per_separation(self):
		self._new_clearance().insert(ignore_permissions=True)
		# Built directly, not through the fixture: the fixture clears any
		# existing record, which is the opposite of what this test needs.
		second = frappe.new_doc(CLEARANCE)
		second.employee_separation = self.separation
		second.access_revocation_datetime = f"{self.relieving_date} 09:00:00"
		self.assertRaises(frappe.UniqueValidationError, second.insert, ignore_permissions=True)

	# -- revocation ceiling -------------------------------------------------
	def test_revocation_cannot_be_pushed_past_the_last_working_day(self):
		doc = self._new_clearance(
			access_revocation_datetime=add_to_date(f"{self.relieving_date} 23:59:59", minutes=1)
		)
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_revocation_can_be_brought_forward(self):
		earlier = f"{add_days(self.relieving_date, -5)} 09:00:00"
		doc = self._new_clearance(access_revocation_datetime=earlier)
		doc.insert(ignore_permissions=True)
		self.assertEqual(get_datetime(doc.access_revocation_datetime), get_datetime(earlier))

	# -- hardware -----------------------------------------------------------
	def test_a_returned_item_must_be_classified(self):
		doc = self._new_clearance(rows=[{"asset_type": "Laptop", "returned": 1}])
		self.assertRaises(frappe.MandatoryError, doc.insert, ignore_permissions=True)

	def test_an_unreturned_item_needs_no_condition(self):
		doc = self._new_clearance(rows=[{"asset_type": "Laptop", "returned": 0}])
		doc.insert(ignore_permissions=True)
		self.assertFalse(doc.assets[0].asset_condition)

	def test_the_same_asset_cannot_be_listed_twice(self):
		doc = self._new_clearance(rows=[
			{"asset_type": "Laptop", "returned": 1, "asset_condition": "Good"},
			{"asset_type": "Laptop", "returned": 1, "asset_condition": "Good"},
		])
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	# -- money --------------------------------------------------------------
	def test_damaged_requires_a_recovery_amount(self):
		doc = self._new_clearance(rows=[
			{"asset_type": "Laptop", "returned": 1, "asset_condition": "Damaged"}
		])
		self.assertRaises(frappe.MandatoryError, doc.insert, ignore_permissions=True)

	def test_missing_requires_a_recovery_amount(self):
		doc = self._new_clearance(rows=[
			{"asset_type": "Mobile", "returned": 0, "asset_condition": "Missing"}
		])
		self.assertRaises(frappe.MandatoryError, doc.insert, ignore_permissions=True)

	def test_a_good_item_cannot_carry_a_charge(self):
		"""Nothing should be deducted from a settlement without a reason."""
		doc = self._new_clearance(rows=[
			{"asset_type": "Laptop", "returned": 1, "asset_condition": "Good",
			 "recovery_amount": 5000}
		])
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_the_total_is_the_sum_of_the_rows(self):
		doc = self._new_clearance(rows=[
			{"asset_type": "Laptop", "returned": 1, "asset_condition": "Damaged",
			 "recovery_amount": 12000},
			{"asset_type": "Mobile", "returned": 0, "asset_condition": "Missing",
			 "recovery_amount": 8000},
			{"asset_type": "Charger", "returned": 1, "asset_condition": "Good"},
		])
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.total_recovery_amount, 20000)

	def test_a_hand_set_total_is_overwritten(self):
		doc = self._new_clearance(rows=[
			{"asset_type": "Laptop", "returned": 1, "asset_condition": "Damaged",
			 "recovery_amount": 12000}
		])
		doc.total_recovery_amount = 0
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.total_recovery_amount, 12000)

	# -- mailbox ------------------------------------------------------------
	def test_an_external_forwarding_address_is_rejected(self):
		doc = self._new_clearance(mailbox_forwarding_address="someone@gmail.com")
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_an_internal_forwarding_address_is_accepted(self):
		doc = self._new_clearance(mailbox_forwarding_address="manager@fixxly.in")
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.mailbox_forwarding_address, "manager@fixxly.in")

	def test_forwarding_is_optional(self):
		doc = self._new_clearance()
		doc.insert(ignore_permissions=True)
		self.assertFalse(doc.mailbox_forwarding_address)

	def test_the_domain_check_is_skipped_when_nothing_is_configured(self):
		frappe.db.set_single_value("HR Settings", DOMAIN_FIELD, "")
		try:
			doc = self._new_clearance(mailbox_forwarding_address="someone@gmail.com")
			doc.insert(ignore_permissions=True)
			self.assertEqual(doc.mailbox_forwarding_address, "someone@gmail.com")
		finally:
			frappe.db.set_single_value("HR Settings", DOMAIN_FIELD, "fixxly.in")

	# -- gating -------------------------------------------------------------
	def test_cannot_submit_until_the_separation_is_approved(self):
		# Cascades through the downstream records too; deleting the clearance on
		# its own now fails, because the auto-raised settlement links it.
		_clear_separations(self.employee.name)

		sep = frappe.new_doc("Employee Separation")
		sep.employee = self.employee.name
		sep.company = self.employee.company
		sep.boarding_begins_on = nowdate()
		sep.custom_resignation_reason = "Personal"
		sep.custom_buyout_notice_period = "No"
		sep.custom_requested_relieving_date = self.relieving_date
		sep.insert(ignore_permissions=True)
		self.separation = sep.name

		doc = self._new_clearance(access_revocation_datetime=f"{self.relieving_date} 09:00:00")
		doc.insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, doc.submit)
		self.assertEqual(frappe.db.get_value(CLEARANCE, doc.name, "docstatus"), 0)

	def test_it_submits_once_the_separation_is_approved(self):
		doc = self._new_clearance()
		doc.insert(ignore_permissions=True)
		doc.submit()
		self.assertEqual(doc.docstatus, 1)
