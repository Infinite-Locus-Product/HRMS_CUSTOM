"""Tests for the PWA clearance endpoints (stages 6 and 7).

These sit in front of the controllers already covered by
test_separation_manager_clearance / test_separation_it_clearance, so the focus
here is the API contract the Vue screens depend on: who may see what, which
actions come back, and that the combined inbox shows each person exactly the
items waiting on them.
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
from myhr.tests.test_separation_manager_clearance import _clear_clearances

MANAGER_CLEARANCE = "Separation Manager Clearance"
IT_CLEARANCE = "Separation IT Clearance"


def _clear_fnf(employee):
	"""Settlements link to the separation, so they must go first or the
	separation cannot be deleted (LinkExistsError)."""
	for name in frappe.get_all(
		"Full and Final Statement", filters={"employee": employee}, pluck="name"
	):
		doc = frappe.get_doc("Full and Final Statement", name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete(ignore_permissions=True)


def _clear_it(employee):
	for name in frappe.get_all(IT_CLEARANCE, filters={"employee": employee}, pluck="name"):
		doc = frappe.get_doc(IT_CLEARANCE, name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete(ignore_permissions=True)


class TestClearanceApi(IntegrationTestCase):
	SEPARATION_WORKFLOW = "Employee Separation Approval"
	CLEARANCE_WORKFLOW = MANAGER_CLEARANCE

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._alerts = {}
		for wf in (cls.SEPARATION_WORKFLOW, cls.CLEARANCE_WORKFLOW):
			cls._alerts[wf] = frappe.db.get_value("Workflow", wf, "send_email_alert")
			frappe.db.set_value("Workflow", wf, "send_email_alert", 0)
		frappe.clear_cache()

		cls.l1 = _ensure_hierarchy_employee("capi.l1@example.com", "_Capi L1", with_user=True)
		cls.l2 = _ensure_hierarchy_employee("capi.l2@example.com", "_Capi L2", with_user=True)
		cls.successor = _ensure_hierarchy_employee("capi.succ@example.com", "_Capi Succ")
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
		self._cleanup()

	def tearDown(self):
		frappe.set_user("Administrator")
		self._cleanup()

	def _cleanup(self):
		# Cascades through all four downstream records in dependency order.
		_clear_separations(self.employee.name)

	# -- helpers ------------------------------------------------------------
	def _as(self, user, fn, *args, **kwargs):
		frappe.set_user(user)
		try:
			return fn(*args, **kwargs)
		finally:
			frappe.set_user("Administrator")

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

	def _handover_payload(self, **overrides):
		data = {
			"primary_successor": self.successor.name,
			"project_client_status_summary": "Nothing outstanding.",
			"downloaded_payslips": 1,
			"downloaded_tax_slips": 1,
			"cleared_personal_files": 1,
			"handover_documents": [{"title": "KT notes", "external_link": "https://drive/kt"}],
		}
		data.update(overrides)
		return frappe.as_json(data)

	# -- stage 6: the leaver's half -----------------------------------------
	def test_nothing_to_clear_without_an_approved_resignation(self):
		from myhr.clearance_api import get_my_clearance, save_my_handover

		result = self._as(self.emp_user, get_my_clearance)
		self.assertFalse(result["exists"])
		self.assertIsNone(result["separation"])

		self.assertRaises(
			frappe.ValidationError, self._as, self.emp_user, save_my_handover,
			self._handover_payload(), 0,
		)

	def test_approval_leaves_a_handover_draft_waiting(self):
		"""Approval raises the draft, so the leaver finds it already started."""
		self._approved_separation()
		from myhr.clearance_api import get_my_clearance

		result = self._as(self.emp_user, get_my_clearance)
		self.assertTrue(result["exists"])
		self.assertEqual(result["clearance"]["workflow_state"], "Draft")
		self.assertTrue(result["clearance"]["is_employee_half_editable"])

	def test_saving_a_draft_keeps_it_editable(self):
		self._approved_separation()
		from myhr.clearance_api import save_my_handover

		view = self._as(self.emp_user, save_my_handover, self._handover_payload(), 0)
		self.assertEqual(view["workflow_state"], "Draft")
		self.assertTrue(view["is_employee_half_editable"])
		self.assertEqual(len(view["handover_documents"]), 1)
		self.assertIn("Submit", view["actions"])

	def test_submitting_hands_it_to_the_manager_and_locks_it(self):
		self._approved_separation()
		from myhr.clearance_api import save_my_handover

		view = self._as(self.emp_user, save_my_handover, self._handover_payload(), 1)
		self.assertEqual(view["workflow_state"], "Pending Manager Clearance")
		self.assertFalse(view["is_employee_half_editable"])
		self.assertEqual(view["actions"], [], "the leaver has nothing left to do")

		self.assertRaises(
			frappe.ValidationError, self._as, self.emp_user, save_my_handover,
			self._handover_payload(), 0,
		)

	def test_submitting_without_the_confirmations_is_refused(self):
		self._approved_separation()
		from myhr.clearance_api import save_my_handover

		self.assertRaises(
			frappe.MandatoryError, self._as, self.emp_user, save_my_handover,
			self._handover_payload(cleared_personal_files=0), 1,
		)

	# -- stage 6: the manager's half ----------------------------------------
	def _submitted(self):
		from myhr.clearance_api import save_my_handover

		self._approved_separation()
		return self._as(self.emp_user, save_my_handover, self._handover_payload(), 1)

	def test_the_manager_sees_the_review_and_their_actions(self):
		from myhr.clearance_api import get_clearance_for_review

		view = self._as(self.l1.user_id, get_clearance_for_review, self._submitted()["name"])
		self.assertEqual(view["my_role"], "manager")
		self.assertIn("Complete", view["actions"])
		self.assertEqual(view["primary_successor"], self.successor.name)
		self.assertIn("JIRA", view["options"]["access_systems"])

	def test_completing_returns_the_finished_state_with_no_actions_left(self):
		from myhr.clearance_api import complete_clearance

		name = self._submitted()["name"]
		view = self._as(self.l1.user_id, complete_clearance, name, frappe.as_json({
			"kt_handover_received": "Yes",
			"client_handoff_complete": "Not Applicable",
			"code_repository_transferred": 1,
			"manager_remarks": "Released.",
			"access_revocation_requested": ["JIRA"],
		}))
		self.assertEqual(view["workflow_state"], "Complete")
		self.assertEqual(view["docstatus"], 1)
		self.assertEqual(view["actions"], [], "buttons must disappear once completed")
		self.assertEqual(view["access_revocation_requested"], ["JIRA"])

	def test_an_incomplete_verification_does_not_move_the_record(self):
		from myhr.clearance_api import complete_clearance

		name = self._submitted()["name"]
		self.assertRaises(
			frappe.MandatoryError, self._as, self.l1.user_id, complete_clearance, name,
			frappe.as_json({"kt_handover_received": "Yes"}),  # no remarks, no revocation answer
		)
		self.assertEqual(
			frappe.db.get_value(MANAGER_CLEARANCE, name, "workflow_state"),
			"Pending Manager Clearance",
		)

	def test_an_unrelated_employee_cannot_open_the_review(self):
		from myhr.clearance_api import get_clearance_for_review

		stranger = _ensure_hierarchy_employee("capi.other@example.com", "_Capi Other", with_user=True)
		name = self._submitted()["name"]
		self.assertRaises(
			frappe.PermissionError, self._as, stranger.user_id, get_clearance_for_review, name
		)

	# -- the combined inbox -------------------------------------------------
	def test_the_inbox_carries_both_kinds_of_item(self):
		from myhr.clearance_api import get_my_separation_inbox

		self._submitted()
		inbox = self._as(self.l1.user_id, get_my_separation_inbox)
		self.assertEqual([i["kind"] for i in inbox], ["manager_clearance"])
		self.assertEqual(inbox[0]["employee_name"], self.employee.employee_name)

	def test_a_completed_clearance_leaves_the_inbox(self):
		"""The inbox is what the Separation Approvals tab lists. A finished item
		that stays in it reads as still needing action."""
		from myhr.clearance_api import complete_clearance, get_my_separation_inbox

		name = self._submitted()["name"]
		self.assertTrue(self._as(self.l1.user_id, get_my_separation_inbox))

		self._as(self.l1.user_id, complete_clearance, name, frappe.as_json({
			"kt_handover_received": "Yes",
			"client_handoff_complete": "Not Applicable",
			"code_repository_transferred": 1,
			"manager_remarks": "Released.",
			"access_revocation_requested": ["JIRA"],
		}))

		self.assertEqual(self._as(self.l1.user_id, get_my_separation_inbox), [])

	def test_the_inbox_is_empty_for_someone_with_nothing_pending(self):
		from myhr.clearance_api import get_my_separation_inbox

		self._submitted()
		self.assertEqual(self._as(self.l2.user_id, get_my_separation_inbox), [])

	def test_a_pending_resignation_shows_up_alongside(self):
		from myhr.clearance_api import get_my_separation_inbox
		from myhr.resignation_api import save_my_resignation

		self._as(self.emp_user, save_my_resignation, frappe.as_json({
			"custom_resignation_reason": "Personal",
			"custom_requested_relieving_date": add_days(nowdate(), 30),
			"custom_buyout_notice_period": "No",
		}), 1)

		inbox = self._as(self.l1.user_id, get_my_separation_inbox)
		self.assertEqual([i["kind"] for i in inbox], ["resignation"])
		self.assertEqual(inbox[0]["badge"], "L1")

	# -- stage 7: read-only -------------------------------------------------
	def test_it_clearance_is_absent_until_it_records_one(self):
		from myhr.clearance_api import get_my_it_clearance

		self.assertFalse(self._as(self.emp_user, get_my_it_clearance)["exists"])

	def test_the_leaver_sees_what_it_recorded_including_the_recovery(self):
		from myhr.clearance_api import get_my_it_clearance

		separation = self._approved_separation()
		doc = _open_downstream(IT_CLEARANCE, separation)
		doc.append("assets", {"asset_type": "Laptop", "returned": 1, "asset_condition": "Good"})
		doc.append("assets", {"asset_type": "Mobile", "returned": 0,
		                      "asset_condition": "Missing", "recovery_amount": 18000})
		doc.insert(ignore_permissions=True)

		view = self._as(self.emp_user, get_my_it_clearance)["clearance"]
		self.assertEqual(view["total_recovery_amount"], 18000)
		self.assertEqual(len(view["assets"]), 2)
		self.assertFalse(view["finalised"])

	# -- stage 9: the settlement, read-only and leaver-only -----------------
	def test_no_settlement_until_finance_prepares_one(self):
		from myhr.clearance_api import get_my_settlement

		self.assertFalse(self._as(self.emp_user, get_my_settlement)["exists"])

	def test_the_leaver_sees_their_own_settlement(self):
		from myhr.clearance_api import get_my_settlement

		self._approved_separation()
		doc = frappe.new_doc("Full and Final Statement")
		doc.employee = self.employee.name
		doc.company = self.employee.company
		doc.transaction_date = nowdate()
		doc.append("payables", {"component": "Bonus", "amount": 85000, "status": "Unsettled"})
		doc.insert(ignore_permissions=True)

		view = self._as(self.emp_user, get_my_settlement)["settlement"]
		self.assertEqual(view["total_payable_amount"], 85000)
		self.assertEqual(view["net_payable"], 85000)
		self.assertFalse(view["finalised"])
		self.assertEqual([r["component"] for r in view["payables"]], ["Bonus"])

	def test_a_manager_does_not_get_their_reports_settlement(self):
		"""It itemises pay. A manager has no business seeing it."""
		from myhr.clearance_api import get_my_settlement

		self._approved_separation()
		doc = frappe.new_doc("Full and Final Statement")
		doc.employee = self.employee.name
		doc.company = self.employee.company
		doc.transaction_date = nowdate()
		doc.insert(ignore_permissions=True)

		self.assertFalse(self._as(self.l1.user_id, get_my_settlement)["exists"])

	# -- stage 8: HR clearance, read-only and leaver-only -------------------
	def _hr_clearance(self, **overrides):
		name = frappe.db.get_value(
			"Separation HR Clearance",
			{"employee_separation": self.separation_name, "docstatus": ["<", 2]}, "name",
		)
		doc = frappe.get_doc("Separation HR Clearance", name)
		# The stub is raised with ignore_mandatory, so the first real save has to
		# supply Re-hire Eligibility — exactly what HR will hit on the form.
		doc.rehire_eligibility = "Yes"
		doc.update(overrides)
		doc.save(ignore_permissions=True)
		return doc

	def test_hr_clearance_is_absent_until_a_separation_is_approved(self):
		from myhr.clearance_api import get_my_hr_clearance

		self.assertFalse(self._as(self.emp_user, get_my_hr_clearance)["exists"])

	def test_the_leaver_sees_their_hr_clearance(self):
		from myhr.clearance_api import get_my_hr_clearance

		self.separation_name = self._approved_separation()
		self._hr_clearance(physical_id_badge_returned="Yes", rehire_eligibility="Yes")

		view = self._as(self.emp_user, get_my_hr_clearance)["clearance"]
		self.assertFalse(view["letter_ready"])
		self.assertEqual(len(view["physical_assets"]), 3)
		self.assertEqual(view["physical_assets"][0]["value"], "Yes")

	def test_rehire_eligibility_never_reaches_the_leaver(self):
		"""'Would we hire them again, and why not' is an HR record about a
		person, not something to hand that person on their phone."""
		from myhr.clearance_api import get_my_hr_clearance

		self.separation_name = self._approved_separation()
		self._hr_clearance(
			rehire_eligibility="No", rehire_ineligibility_reason="Performance concerns."
		)

		view = self._as(self.emp_user, get_my_hr_clearance)["clearance"]
		blob = frappe.as_json(view)
		self.assertNotIn("rehire", blob.lower())
		self.assertNotIn("Performance concerns", blob)

	def test_a_manager_does_not_get_their_reports_hr_clearance(self):
		from myhr.clearance_api import get_my_hr_clearance

		self.separation_name = self._approved_separation()
		self.assertFalse(self._as(self.l1.user_id, get_my_hr_clearance)["exists"])

	def test_the_letter_appears_once_released(self):
		from myhr.clearance_api import get_my_hr_clearance

		self.separation_name = self._approved_separation()
		doc = self._hr_clearance()
		doc.db_set("relieving_letter", "/private/files/letter.pdf")

		view = self._as(self.emp_user, get_my_hr_clearance)["clearance"]
		self.assertTrue(view["letter_ready"])
		self.assertEqual(view["relieving_letter"], "/private/files/letter.pdf")

	# -- the successor picker ----------------------------------------------
	def test_the_picker_finds_colleagues_the_employee_cannot_otherwise_read(self):
		"""Employee is locked down per-user, so a plain Link search returns
		nothing. This endpoint is what makes the picker work at all."""
		from myhr.clearance_api import search_colleagues

		results = self._as(self.emp_user, search_colleagues, self.l1.employee_name[:6])
		self.assertTrue(results, "the picker would appear broken")
		self.assertIn(self.l1.name, [r["name"] for r in results])

	def test_the_picker_never_offers_the_leaver_themselves(self):
		from myhr.clearance_api import search_colleagues

		results = self._as(self.emp_user, search_colleagues, None, 50)
		self.assertNotIn(self.employee.name, [r["name"] for r in results])

	def test_the_picker_returns_only_public_fields(self):
		"""Same four fields the company directory already shows everyone."""
		from myhr.clearance_api import search_colleagues

		results = self._as(self.emp_user, search_colleagues, None, 5)
		self.assertTrue(results)
		self.assertEqual(
			set(results[0].keys()), {"name", "employee_name", "designation", "department"}
		)

	def test_the_successor_is_returned_as_a_name_not_an_id(self):
		from myhr.clearance_api import save_my_handover

		self._approved_separation()
		view = self._as(self.emp_user, save_my_handover, self._handover_payload(), 0)
		self.assertEqual(view["primary_successor"], self.successor.name)
		self.assertEqual(view["primary_successor_name"], self.successor.employee_name)

	def test_an_untitled_row_is_titled_rather_than_rejected(self):
		"""`title` is mandatory on the child row, so an untitled one used to fail
		the entire save — losing a form the employee had just filled in. The app
		defaults it from the filename, but the server derives it too: one stale
		bundle must not be able to reintroduce that."""
		self._approved_separation()
		from myhr.clearance_api import save_my_handover

		payload = frappe.as_json({
			"primary_successor": self.successor.name,
			"downloaded_payslips": 1,
			"downloaded_tax_slips": 1,
			"cleared_personal_files": 1,
			"handover_documents": [
				{"title": "", "attachment": "/private/files/Screenshot.png",
				 "file_name": "Screenshot 2026-09-11.png"},
				{"title": "", "external_link": "https://drive.example.com/kt-notes"},
				{"title": "", "notes": "Verbal handover done on Friday."},
			],
		})
		view = self._as(self.emp_user, save_my_handover, payload, 1)

		self.assertEqual(view["workflow_state"], "Pending Manager Clearance")
		titles = [d["title"] for d in view["handover_documents"]]
		self.assertEqual(titles[0], "Screenshot 2026-09-11", "a filename reads best")
		self.assertEqual(titles[1], "kt-notes", "fall back to the tail of the link")
		self.assertTrue(titles[2], "a note-only row still needs some title")

	def test_a_typed_title_is_never_overwritten(self):
		self._approved_separation()
		from myhr.clearance_api import save_my_handover

		payload = frappe.as_json({
			"primary_successor": self.successor.name,
			"downloaded_payslips": 1,
			"downloaded_tax_slips": 1,
			"cleared_personal_files": 1,
			"handover_documents": [
				{"title": "Client X notes", "file_name": "Screenshot.png",
				 "attachment": "/private/files/x.png"}
			],
		})
		view = self._as(self.emp_user, save_my_handover, payload, 0)
		self.assertEqual(view["handover_documents"][0]["title"], "Client X notes")

	def test_a_titled_row_with_an_attachment_saves_and_submits(self):
		self._approved_separation()
		from myhr.clearance_api import save_my_handover

		payload = frappe.as_json({
			"primary_successor": self.successor.name,
			"downloaded_payslips": 1,
			"downloaded_tax_slips": 1,
			"cleared_personal_files": 1,
			"handover_documents": [
				{"title": "Screenshot", "attachment": "/private/files/x.png",
				 "file_name": "Screenshot.png"}
			],
		})
		view = self._as(self.emp_user, save_my_handover, payload, 1)
		self.assertEqual(view["workflow_state"], "Pending Manager Clearance")
		self.assertEqual(view["handover_documents"][0]["file_name"], "Screenshot.png")
