"""Tests for Separation Manager Clearance (exit flow stage 6).

Covers the five rules in the spec's validations section. They are keyed off
`workflow_state` rather than docstatus, because Frappe sets the new state on the
document and then saves it — so a rule written for Complete blocks the
transition itself and leaves the record where it was.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from myhr.tests.test_employee_separation import (
	_clear_separations,
	_ensure_employee,
	_ensure_hierarchy_employee,
	_ensure_user_for,
	_open_downstream,
)

CLEARANCE = "Separation Manager Clearance"


def _clear_clearances(employee):
	for name in frappe.get_all(CLEARANCE, filters={"employee": employee}, pluck="name"):
		doc = frappe.get_doc(CLEARANCE, name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete(ignore_permissions=True)


class TestSeparationManagerClearance(IntegrationTestCase):
	SEPARATION_WORKFLOW = "Employee Separation Approval"
	CLEARANCE_WORKFLOW = CLEARANCE

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Both workflows attach the document to the approver's email as a PDF,
		# which needs wkhtmltopdf. Muted here; restored in tearDownClass.
		cls._alerts = {}
		for wf in (cls.SEPARATION_WORKFLOW, cls.CLEARANCE_WORKFLOW):
			cls._alerts[wf] = frappe.db.get_value("Workflow", wf, "send_email_alert")
			frappe.db.set_value("Workflow", wf, "send_email_alert", 0)
		frappe.clear_cache()

		cls.l1 = _ensure_hierarchy_employee("smc.l1@example.com", "_Smc L1", with_user=True)
		cls.l2 = _ensure_hierarchy_employee("smc.l2@example.com", "_Smc L2", with_user=True)
		cls.successor = _ensure_hierarchy_employee("smc.succ@example.com", "_Smc Succ")
		cls.employee = _ensure_employee()
		cls.employee.reports_to = cls.l1.name
		cls.employee.custom_l2_manager = cls.l2.name
		cls.employee.save(ignore_permissions=True)
		cls.emp_user = _ensure_user_for(cls.employee)

	@classmethod
	def tearDownClass(cls):
		for wf, value in cls._alerts.items():
			frappe.db.set_value("Workflow", wf, "send_email_alert", value)
		frappe.clear_cache()
		super().tearDownClass()

	def setUp(self):
		frappe.set_user("Administrator")
		# `_clear_separations` cascades through the four downstream records in
		# dependency order; they are auto-raised on approval and link to each
		# other, so deleting them piecemeal hits LinkExistsError.
		_clear_separations(self.employee.name)
		self.separation = self._file_separation()

	def tearDown(self):
		frappe.set_user("Administrator")
		_clear_separations(self.employee.name)

	# -- helpers ------------------------------------------------------------
	def _file_separation(self, approved=False):
		from frappe.model.workflow import apply_workflow

		doc = frappe.new_doc("Employee Separation")
		doc.employee = self.employee.name
		doc.company = self.employee.company
		doc.boarding_begins_on = nowdate()
		doc.custom_resignation_reason = "Personal"
		doc.custom_buyout_notice_period = "No"
		doc.custom_requested_relieving_date = add_days(nowdate(), 30)
		doc.insert(ignore_permissions=True)

		if approved:
			# Each step must be driven by the person the workflow condition
			# names — Administrator matches none of them, so approving as
			# Administrator simply yields no available transition.
			approval = {
				"custom_decision": "Approve",
				"custom_approved_relieving_date": add_days(nowdate(), 30),
				"custom_notice_period_waiver": "No",
				"custom_retention_discussion_held": "Yes",
			}
			steps = (
				(self.emp_user, "Submit", None),
				(self.l1.user_id, "Approve", approval),
				(self.l2.user_id, "Approve", approval),
			)
			for user, action, payload in steps:
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

	def _new_clearance(self, **overrides):
		doc = _open_downstream(CLEARANCE, self.separation)
		doc.handover_documents = []
		doc.append("handover_documents", {"title": "KT notes", "external_link": "https://drive/kt"})
		doc.primary_successor = self.successor.name
		doc.downloaded_payslips = 1
		doc.downloaded_tax_slips = 1
		doc.cleared_personal_files = 1
		doc.project_client_status_summary = "Nothing outstanding."
		doc.update(overrides)
		return doc

	def _complete_ready(self, doc):
		doc.kt_handover_received = "Yes"
		doc.client_handoff_complete = "Not Applicable"
		doc.code_repository_transferred = 1
		doc.append("access_revocation_requested", {"access_system": "JIRA"})
		doc.manager_remarks = "Released operationally."
		return doc

	# -- context ------------------------------------------------------------
	def test_context_is_pulled_from_the_separation(self):
		doc = self._new_clearance()
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.employee, self.employee.name)
		self.assertEqual(doc.reporting_manager, self.l1.name)

	def test_only_one_clearance_per_separation(self):
		self._new_clearance().insert(ignore_permissions=True)
		# Built directly, not through the fixture: the fixture clears any
		# existing record, which is the opposite of what this test needs.
		second = frappe.new_doc(CLEARANCE)
		second.employee_separation = self.separation
		self.assertRaises(frappe.UniqueValidationError, second.insert, ignore_permissions=True)

	# -- rule: empty handover rows -----------------------------------------
	def test_a_handover_row_with_nothing_in_it_is_rejected(self):
		doc = self._new_clearance()
		doc.append("handover_documents", {"title": "Empty one"})
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	# -- rule: KT Received = Yes prerequisites ------------------------------
	def test_kt_received_yes_needs_a_handover_document(self):
		doc = self._new_clearance()
		doc.handover_documents = []
		doc.kt_handover_received = "Yes"
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_kt_received_yes_needs_a_primary_successor(self):
		doc = self._new_clearance(primary_successor=None)
		doc.kt_handover_received = "Yes"
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_kt_received_no_is_allowed_without_either(self):
		doc = self._new_clearance(primary_successor=None)
		doc.handover_documents = []
		doc.kt_handover_received = "No"
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.kt_handover_received, "No")

	# -- rule: three confirmations before submitting ------------------------
	def test_a_partial_draft_can_still_be_saved(self):
		doc = self._new_clearance(downloaded_payslips=0, downloaded_tax_slips=0)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.workflow_state, "Draft")

	def test_submitting_without_all_three_confirmations_is_blocked(self):
		from frappe.model.workflow import apply_workflow

		doc = self._new_clearance(cleared_personal_files=0)
		doc.insert(ignore_permissions=True)
		frappe.set_user(self.emp_user)
		try:
			self.assertRaises(
				frappe.MandatoryError, apply_workflow, frappe.get_doc(CLEARANCE, doc.name), "Submit"
			)
		finally:
			frappe.set_user("Administrator")

	def test_the_employee_can_submit_once_all_three_are_ticked(self):
		from frappe.model.workflow import apply_workflow

		doc = self._new_clearance()
		doc.insert(ignore_permissions=True)
		frappe.set_user(self.emp_user)
		try:
			moved = apply_workflow(frappe.get_doc(CLEARANCE, doc.name), "Submit")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(moved.workflow_state, "Pending Manager Clearance")
		self.assertEqual(moved.docstatus, 0)

	# -- Complete stage -----------------------------------------------------
	def _submitted_clearance(self, separation_approved=False):
		"""A clearance sitting with the manager, ready to be completed."""
		from frappe.model.workflow import apply_workflow

		if separation_approved:
			_clear_clearances(self.employee.name)
			_clear_separations(self.employee.name)
			self.separation = self._file_separation(approved=True)

		doc = self._new_clearance()
		doc.insert(ignore_permissions=True)
		frappe.set_user(self.emp_user)
		try:
			doc = apply_workflow(frappe.get_doc(CLEARANCE, doc.name), "Submit")
		finally:
			frappe.set_user("Administrator")
		return doc

	def _complete_as_manager(self, doc):
		from frappe.model.workflow import apply_workflow

		frappe.set_user(self.l1.user_id)
		try:
			target = self._complete_ready(frappe.get_doc(CLEARANCE, doc.name))
			target.save()
			return apply_workflow(target, "Complete")
		finally:
			frappe.set_user("Administrator")

	def test_cannot_complete_while_the_separation_is_unapproved(self):
		doc = self._submitted_clearance()
		with self.assertRaises(frappe.ValidationError) as caught:
			self._complete_as_manager(doc)
		self.assertIn("Approved", str(caught.exception))
		self.assertEqual(
			frappe.db.get_value(CLEARANCE, doc.name, "workflow_state"),
			"Pending Manager Clearance",
			"a refused completion must leave the record where it was",
		)

	def test_the_manager_can_complete_once_the_separation_is_approved(self):
		doc = self._submitted_clearance(separation_approved=True)
		done = self._complete_as_manager(doc)
		self.assertEqual(done.workflow_state, "Complete")
		self.assertEqual(done.docstatus, 1)

	def test_completing_without_manager_remarks_is_blocked(self):
		from frappe.model.workflow import apply_workflow

		doc = self._submitted_clearance(separation_approved=True)
		frappe.set_user(self.l1.user_id)
		try:
			target = self._complete_ready(frappe.get_doc(CLEARANCE, doc.name))
			target.manager_remarks = "   "  # whitespace must not count as sign-off
			target.save()
			self.assertRaises(frappe.MandatoryError, apply_workflow, target, "Complete")
		finally:
			frappe.set_user("Administrator")

	def test_completing_without_answering_access_revocation_is_blocked(self):
		from frappe.model.workflow import apply_workflow

		doc = self._submitted_clearance(separation_approved=True)
		frappe.set_user(self.l1.user_id)
		try:
			target = self._complete_ready(frappe.get_doc(CLEARANCE, doc.name))
			target.access_revocation_requested = []
			target.access_revocation_not_applicable = 0
			target.save()
			self.assertRaises(frappe.MandatoryError, apply_workflow, target, "Complete")
		finally:
			frappe.set_user("Administrator")

	def test_explicit_not_applicable_satisfies_access_revocation(self):
		from frappe.model.workflow import apply_workflow

		doc = self._submitted_clearance(separation_approved=True)
		frappe.set_user(self.l1.user_id)
		try:
			target = self._complete_ready(frappe.get_doc(CLEARANCE, doc.name))
			target.access_revocation_requested = []
			target.access_revocation_not_applicable = 1
			target.save()
			done = apply_workflow(target, "Complete")
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(done.workflow_state, "Complete")

	def test_listing_systems_and_ticking_not_applicable_is_contradictory(self):
		from frappe.model.workflow import apply_workflow

		doc = self._submitted_clearance(separation_approved=True)
		frappe.set_user(self.l1.user_id)
		try:
			target = self._complete_ready(frappe.get_doc(CLEARANCE, doc.name))
			target.access_revocation_not_applicable = 1  # plus the JIRA row already there
			target.save()
			self.assertRaises(frappe.ValidationError, apply_workflow, target, "Complete")
		finally:
			frappe.set_user("Administrator")

	# -- who may act --------------------------------------------------------
	def test_someone_who_is_not_the_manager_cannot_complete_it(self):
		doc = self._submitted_clearance(separation_approved=True)
		stranger = _ensure_hierarchy_employee("smc.other@example.com", "_Smc Other", with_user=True)
		frappe.set_user(stranger.user_id)
		try:
			self.assertRaises(frappe.PermissionError, frappe.get_doc(CLEARANCE, doc.name).check_permission, "read")
		finally:
			frappe.set_user("Administrator")

	def test_the_l2_manager_has_no_say_in_this_clearance(self):
		"""Stage 6 is the reporting manager's. L2 is not named on it."""
		from frappe.model.workflow import get_transitions

		doc = self._submitted_clearance(separation_approved=True)
		frappe.set_user(self.l2.user_id)
		try:
			self.assertRaises(frappe.PermissionError, get_transitions, frappe.get_doc(CLEARANCE, doc.name))
		finally:
			frappe.set_user("Administrator")
