"""Tests for Separation HR Clearance (exit flow stage 8).

Most of the weight is on the relieving-letter gate: it decides when someone's
letter may be issued, so every blocker is tested on its own, and the release is
tested with the PDF renderer patched out (rendering needs wkhtmltopdf, which is
not installed on every dev machine — the same gap that broke L2 approval).

Note: HRMS requires `Employee.relieving_date` before an Exit Interview can exist
at all. That field is written by `employee_separation_hooks.on_submit` when the
resignation is finally approved, so these tests rely on that wiring rather than
setting it themselves — if it regresses, the exit-interview tests here fail.
"""

from __future__ import annotations

import re
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, formatdate, nowdate

from myhr.tests.test_employee_separation import (
	_clear_separations,
	_ensure_employee,
	_ensure_hierarchy_employee,
	_ensure_user,
	_ensure_user_for,
	_open_downstream,
)

CLEARANCE = "Separation HR Clearance"
RENDER = "myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance._render_letter"
TEMPLATE_FILE = frappe.get_app_path("myhr", "..", "templates", "fixxly_relieving_letter.html")


def _ensure_print_format():
	"""Put the relieving-letter format into the state Desk setup produces.

	The record is not shipped in the app -- it is created by hand, once per site
	(docs/OFFBOARDING_TESTING_GUIDE.md) -- so a fresh test database has none, and
	`release_relieving_letter` refuses without it. Creating it here with exactly
	the documented flags also proves those steps are enough: module myHR and
	Custom Format ticked, html left empty so the template file is read off disk.

	Idempotent and corrective, not skip-if-exists: the guard test below breaks the
	record on purpose and restores it through this.
	"""
	from myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance import (
		RELIEVING_LETTER_FORMAT,
	)

	if frappe.db.exists("Print Format", RELIEVING_LETTER_FORMAT):
		frappe.delete_doc("Print Format", RELIEVING_LETTER_FORMAT, force=1, ignore_permissions=True)

	with open(TEMPLATE_FILE) as f:
		template = f.read()

	frappe.get_doc({
		"doctype": "Print Format",
		"name": RELIEVING_LETTER_FORMAT,
		"doc_type": CLEARANCE,
		"module": "myHR",
		"print_format_type": "Jinja",
		"custom_format": 1,
		# Pasted, not referenced. templates/ is not a path printview looks in, so
		# the record's own html is what renders -- the same paste step the setup
		# guide describes for a real site. Reading it from the file keeps these
		# tests honest about the template in git; it cannot tell you whether a
		# given site's paste is current, which is the cost of this arrangement.
		"html": template,
	}).insert(ignore_permissions=True)
	# get_print reads the record through the cache.
	frappe.clear_cache()


def _clear_hr_clearances(employee):
	for name in frappe.get_all(CLEARANCE, filters={"employee": employee}, pluck="name"):
		doc = frappe.get_doc(CLEARANCE, name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete(ignore_permissions=True)


def _clear_exit_interviews(employee):
	for name in frappe.get_all("Exit Interview", filters={"employee": employee}, pluck="name"):
		doc = frappe.get_doc("Exit Interview", name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete(ignore_permissions=True)


class TestSeparationHRClearance(IntegrationTestCase):
	SEPARATION_WORKFLOW = "Employee Separation Approval"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_ensure_print_format()
		cls._alert = frappe.db.get_value("Workflow", cls.SEPARATION_WORKFLOW, "send_email_alert")
		frappe.db.set_value("Workflow", cls.SEPARATION_WORKFLOW, "send_email_alert", 0)
		frappe.clear_cache()

		cls.l1 = _ensure_hierarchy_employee("hrc.l1@example.com", "_Hrc L1", with_user=True)
		cls.l2 = _ensure_hierarchy_employee("hrc.l2@example.com", "_Hrc L2", with_user=True)
		cls.employee = _ensure_employee()
		cls.employee.reports_to = cls.l1.name
		cls.employee.custom_l2_manager = cls.l2.name
		cls.employee.save(ignore_permissions=True)
		cls.emp_user = _ensure_user_for(cls.employee)

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_value("Workflow", cls.SEPARATION_WORKFLOW, "send_email_alert", cls._alert)
		frappe.clear_cache()
		super().tearDownClass()

	def setUp(self):
		frappe.set_user("Administrator")
		# `_clear_separations` cascades through the four downstream records in
		# dependency order; they are auto-raised on approval and link to each
		# other, so deleting them piecemeal hits LinkExistsError.
		# Separations (and the clearances they raised) first: the HR clearance
		# links the exit interview, so the interview cannot be deleted before it.
		_clear_separations(self.employee.name)
		_clear_exit_interviews(self.employee.name)
		# Today, not earlier: the last-working-day gate is "today >= last working
		# day", so today opens it, while an earlier date would trip the stage-A
		# rule that an approved relieving date cannot precede the resignation.
		self.relieving_date = nowdate()
		self.separation = self._approved_separation()

	def tearDown(self):
		frappe.set_user("Administrator")
		# Separations (and the clearances they raised) first: the HR clearance
		# links the exit interview, so the interview cannot be deleted before it.
		_clear_separations(self.employee.name)
		_clear_exit_interviews(self.employee.name)

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
		# Stamped by resignation_api on the real path; set here because these
		# fixtures build the separation directly.
		doc.resignation_letter_date = nowdate()
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

	def _exit_interview(self, status="Completed", submit=True):
		# No fixture write here on purpose. HRMS refuses to create an Exit
		# Interview unless Employee.relieving_date is set, and the separation's
		# own on_submit is what sets it. If that wiring regresses, every test
		# below fails with HRMS's "Please set the relieving date" error — which
		# is exactly the breakage we want to catch.
		doc = frappe.new_doc("Exit Interview")
		doc.employee = self.employee.name
		doc.company = self.employee.company
		doc.date = nowdate()
		doc.status = status
		doc.insert(ignore_permissions=True)
		if submit:
			doc.submit()
		return doc

	def _clearance(self, **overrides):
		doc = _open_downstream(CLEARANCE, self.separation)
		doc.rehire_eligibility = "Yes"
		doc.physical_id_badge_returned = "Yes"
		doc.cabinet_desk_keys_returned = "Not Applicable"
		doc.parking_tag_returned = "Not Applicable"
		doc.update(overrides)
		return doc

	# -- exit interview -----------------------------------------------------
	def test_exit_interview_is_found_automatically(self):
		interview = self._exit_interview()
		doc = self._clearance()
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.exit_interview, interview.name)
		self.assertEqual(doc.exit_interview_status, "Completed")

	def test_no_exit_interview_leaves_the_field_blank(self):
		doc = self._clearance()
		doc.insert(ignore_permissions=True)
		self.assertIsNone(doc.exit_interview)
		self.assertFalse(doc.exit_interview_is_done)

	def test_a_draft_interview_marked_completed_does_not_count(self):
		"""HRMS lets a draft claim Completed; that must not open the gate."""
		self._exit_interview(status="Completed", submit=False)
		doc = self._clearance()
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.exit_interview_status, "Completed")
		self.assertFalse(doc.exit_interview_is_done)

	# -- re-hire ------------------------------------------------------------
	def test_rehire_no_requires_a_reason(self):
		doc = self._clearance(rehire_eligibility="No")
		self.assertRaises(frappe.MandatoryError, doc.insert, ignore_permissions=True)

	def test_rehire_no_with_a_reason_is_accepted(self):
		doc = self._clearance(rehire_eligibility="No",
		                      rehire_ineligibility_reason="Performance concerns.")
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.rehire_eligibility, "No")

	def test_rehire_yes_needs_no_reason(self):
		doc = self._clearance(rehire_eligibility="Yes")
		doc.insert(ignore_permissions=True)
		self.assertFalse(doc.rehire_ineligibility_reason)

	def test_the_internal_reason_never_reaches_the_letter(self):
		"""print_hide is what keeps it off the printed relieving letter."""
		meta = frappe.get_meta(CLEARANCE)
		self.assertTrue(meta.get_field("rehire_ineligibility_reason").print_hide)

	# -- the release gate ---------------------------------------------------
	def _ready(self):
		self._exit_interview()
		doc = self._clearance()
		doc.insert(ignore_permissions=True)
		return doc

	def test_everything_in_place_means_it_can_be_released(self):
		self.assertTrue(self._ready().can_release_letter())

	def test_blocked_without_a_completed_exit_interview(self):
		doc = self._clearance()
		doc.insert(ignore_permissions=True)
		self.assertFalse(doc.can_release_letter())
		self.assertIn("exit interview", " ".join(doc.blockers_for_letter()))

	def test_blocked_before_the_last_working_day(self):
		self._exit_interview()
		doc = self._clearance()
		doc.insert(ignore_permissions=True)
		doc.last_working_day = add_days(nowdate(), 7)
		self.assertFalse(doc.can_release_letter())
		self.assertIn("last working day", " ".join(doc.blockers_for_letter()))

	def test_blocked_while_a_physical_asset_is_unanswered(self):
		self._exit_interview()
		doc = self._clearance(parking_tag_returned=None)
		doc.insert(ignore_permissions=True)
		self.assertFalse(doc.can_release_letter())
		self.assertIn("Parking Tag", " ".join(doc.blockers_for_letter()))

	def test_every_blocker_is_reported_at_once(self):
		doc = self._clearance(physical_id_badge_returned=None, parking_tag_returned=None)
		doc.insert(ignore_permissions=True)
		doc.last_working_day = add_days(nowdate(), 7)
		blockers = doc.blockers_for_letter()
		self.assertEqual(len(blockers), 3, blockers)

	# -- releasing ----------------------------------------------------------
	def test_release_stamps_who_and_when(self):
		doc = self._ready()
		with patch(RENDER, return_value="/private/files/letter.pdf"):
			from myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance import (
				release_relieving_letter,
			)

			release_relieving_letter(doc.name)

		doc.reload()
		self.assertEqual(doc.relieving_letter, "/private/files/letter.pdf")
		self.assertTrue(doc.relieving_letter_released_on)
		self.assertEqual(doc.relieving_letter_released_by, "Administrator")

	def test_release_is_refused_while_blocked(self):
		from myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance import (
			release_relieving_letter,
		)

		doc = self._clearance()  # no exit interview
		doc.insert(ignore_permissions=True)
		with patch(RENDER, return_value="/private/files/letter.pdf") as render:
			self.assertRaises(frappe.ValidationError, release_relieving_letter, doc.name)
			render.assert_not_called()
		doc.reload()
		self.assertFalse(doc.relieving_letter)

	def test_a_letter_cannot_be_released_twice(self):
		from myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance import (
			release_relieving_letter,
		)

		doc = self._ready()
		with patch(RENDER, return_value="/private/files/letter.pdf"):
			release_relieving_letter(doc.name)
			self.assertRaises(frappe.ValidationError, release_relieving_letter, doc.name)

	# -- misc ---------------------------------------------------------------
	# -- what the Desk button reads -----------------------------------------
	def test_the_status_endpoint_tells_the_button_what_to_show(self):
		"""public/js/separation_hr_clearance.js renders entirely from these four
		keys, so the button and the server can never disagree about why a letter
		is being withheld."""
		from myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance import (
			get_release_status,
		)

		blocked = self._clearance()
		blocked.insert(ignore_permissions=True)
		status = get_release_status(blocked.name)
		self.assertEqual(
			set(status), {"released", "relieving_letter", "can_release", "blockers"}
		)
		self.assertFalse(status["released"])
		self.assertFalse(status["can_release"])
		self.assertTrue(status["blockers"], "the button needs a reason to show")

	def test_the_status_endpoint_opens_the_button_once_ready(self):
		from myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance import (
			get_release_status,
		)

		status = get_release_status(self._ready().name)
		self.assertTrue(status["can_release"])
		self.assertEqual(status["blockers"], [])
		self.assertFalse(status["released"])

	def test_the_status_endpoint_reports_a_released_letter(self):
		from myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance import (
			get_release_status,
			release_relieving_letter,
		)

		doc = self._ready()
		with patch(RENDER, return_value="/private/files/letter.pdf"):
			release_relieving_letter(doc.name)

		status = get_release_status(doc.name)
		self.assertTrue(status["released"])
		self.assertEqual(status["relieving_letter"], "/private/files/letter.pdf")

	def test_only_one_hr_clearance_per_separation(self):
		self._clearance().insert(ignore_permissions=True)
		# Built directly, not through the fixture: the fixture clears any
		# existing record, which is the opposite of what this test needs.
		second = frappe.new_doc(CLEARANCE)
		second.employee_separation = self.separation
		second.rehire_eligibility = "Yes"
		self.assertRaises(frappe.UniqueValidationError, second.insert, ignore_permissions=True)


	# -- permissions --------------------------------------------------------
	def test_an_hr_manager_can_submit_an_exit_interview(self):
		"""Stock HRMS grants submit on Exit Interview to nobody at all.

		It is a submittable doctype with submit=0 on every role, so only
		Administrator could submit one — which made this clearance's gate
		(interview Completed AND submitted) impossible to satisfy, and the
		relieving letter unreleasable. myHR grants it to HR Manager.
		"""
		hr_user = _ensure_user("hrc.hrmanager@example.com", "_Hrc HRM")
		frappe.get_doc("User", hr_user).add_roles("HR Manager")

		interview = self._exit_interview(submit=False)

		frappe.set_user(hr_user)
		try:
			doc = frappe.get_doc("Exit Interview", interview.name)
			doc.status = "Completed"
			doc.save()
			doc.submit()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(frappe.db.get_value("Exit Interview", interview.name, "docstatus"), 1)

	def test_the_letter_is_releasable_by_an_hr_manager_end_to_end(self):
		"""The whole point of the permission above."""
		from unittest.mock import patch

		from myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance import (
			release_relieving_letter,
		)

		hr_user = _ensure_user("hrc.hrmanager2@example.com", "_Hrc HRM2")
		frappe.get_doc("User", hr_user).add_roles("HR Manager")

		interview = self._exit_interview(submit=False)
		frappe.set_user(hr_user)
		try:
			doc = frappe.get_doc("Exit Interview", interview.name)
			doc.status = "Completed"
			doc.save()
			doc.submit()
		finally:
			frappe.set_user("Administrator")

		clearance = self._clearance()
		clearance.insert(ignore_permissions=True)

		frappe.set_user(hr_user)
		try:
			with patch(RENDER, return_value="/private/files/letter.pdf"):
				release_relieving_letter(clearance.name)
		finally:
			frappe.set_user("Administrator")

		clearance.reload()
		self.assertEqual(clearance.relieving_letter, "/private/files/letter.pdf")
		self.assertEqual(clearance.relieving_letter_released_by, hr_user)

	# -- keeping the interview link current ---------------------------------
	def test_submitting_an_interview_updates_an_existing_clearance(self):
		"""The clearance is raised before the interview exists, so it cannot
		rely on its own save to notice one — especially as that save is blocked
		by its own mandatory Re-hire Eligibility."""
		clearance = self._clearance()
		clearance.insert(ignore_permissions=True)
		frappe.db.set_value("Separation HR Clearance", clearance.name,
		                    {"exit_interview": None, "exit_interview_status": None})

		interview = self._exit_interview()

		self.assertEqual(
			frappe.db.get_value("Separation HR Clearance", clearance.name, "exit_interview"),
			interview.name,
		)
		self.assertEqual(
			frappe.db.get_value(
				"Separation HR Clearance", clearance.name, "exit_interview_status"
			),
			"Completed",
		)

	def test_opening_the_form_picks_up_an_interview_created_later(self):
		"""onload refreshes it without needing a save."""
		clearance = self._clearance()
		clearance.insert(ignore_permissions=True)
		self._exit_interview()
		frappe.db.set_value("Separation HR Clearance", clearance.name,
		                    {"exit_interview": None, "exit_interview_status": None})

		fresh = frappe.get_doc("Separation HR Clearance", clearance.name)
		fresh.onload()
		self.assertTrue(fresh.exit_interview)
		self.assertEqual(fresh.exit_interview_status, "Completed")

	def test_cancelling_an_interview_clears_it_from_the_clearance(self):
		clearance = self._clearance()
		clearance.insert(ignore_permissions=True)
		interview = self._exit_interview()
		self.assertTrue(
			frappe.db.get_value("Separation HR Clearance", clearance.name, "exit_interview")
		)

		frappe.get_doc("Exit Interview", interview.name).cancel()

		self.assertIsNone(
			frappe.db.get_value("Separation HR Clearance", clearance.name, "exit_interview")
		)


class TestRelievingLetterTemplate(TestSeparationHRClearance):
	"""The letter itself, rendered through the real print format.

	Separate from the release-gate tests, which patch the renderer out: these
	render the HTML (no wkhtmltopdf needed -- that is only the HTML-to-PDF step)
	so a template that stops resolving a name or a date is caught here rather
	than by someone reading their own relieving letter.
	"""

	def _letter(self, **overrides):
		from myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance import (
			RELIEVING_LETTER_FORMAT,
			_letter_head_for,
		)

		self._exit_interview()
		doc = self._clearance(**overrides)
		doc.insert(ignore_permissions=True)
		html = frappe.get_print(
			CLEARANCE, doc.name, print_format=RELIEVING_LETTER_FORMAT, doc=doc,
			letterhead=_letter_head_for(doc),
		)
		# Just the letter, not the print page wrapped around it: that carries
		# frappe's own stylesheet and scripts, which are full of brackets and
		# dashes and would make the assertions below meaningless.
		html = re.sub(r"<(style|script)\b.*?</\1>", " ", html, flags=re.S | re.I)
		_, _, body = html.partition('<div class="relieving">')
		self.assertTrue(body.strip(), "the letter did not render")
		return doc, re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))

	def test_it_names_the_leaver_and_their_dates(self):
		doc, text = self._letter()
		joined = frappe.db.get_value("Employee", doc.employee, "date_of_joining")
		for value in (
			doc.employee_name,
			doc.employee,
			formatdate(self.relieving_date, "dd/MM/yyyy"),
			formatdate(joined, "dd/MM/yyyy"),
			formatdate(nowdate(), "dd/MM/yyyy"),
		):
			self.assertIn(str(value), text)

	def test_no_placeholder_survives(self):
		"""The source document is a template full of [Employee Name] style
		placeholders; none of them may reach a released letter."""
		_, text = self._letter()
		self.assertNotIn("[", text)
		self.assertNotIn("\u2014", text, "an em dash means a value did not resolve")

	def test_the_settlement_window_is_stated(self):
		_, text = self._letter()
		self.assertIn("within 45 working days", text)

	def test_the_internal_rehire_reason_is_not_printed(self):
		"""It is an internal note. print_hide covers the standard format; this
		covers ours, which does not go through fields at all."""
		secret = "Repeated policy breaches"
		_, text = self._letter(rehire_eligibility="No", rehire_ineligibility_reason=secret)
		self.assertNotIn(secret, text)

	def test_release_is_refused_when_the_format_is_not_set_up(self):
		"""Both failure modes are silent in frappe, so the release checks them."""
		from myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance import (
			RELIEVING_LETTER_FORMAT,
			release_relieving_letter,
		)

		doc = self._ready()
		for value in (0, None):
			with self.subTest(custom_format=value):
				if value is None:
					frappe.delete_doc("Print Format", RELIEVING_LETTER_FORMAT, force=1)
				else:
					frappe.db.set_value("Print Format", RELIEVING_LETTER_FORMAT, "custom_format", 0)
				frappe.clear_cache()
				try:
					with self.assertRaises(frappe.ValidationError) as caught:
						release_relieving_letter(doc.name)
					self.assertIn("print format", str(caught.exception).lower())
					self.assertFalse(
						frappe.db.get_value(CLEARANCE, doc.name, "relieving_letter"),
						"nothing may be stamped when the letter was never generated",
					)
				finally:
					_ensure_print_format()

	def test_the_letter_renders_at_all(self):
		"""The template in git is valid Jinja against a real clearance.

		Everything below asserts a detail of the letter; this says the thing
		rendered in the first place, so a template-level break reads as one
		failure rather than five."""
		_, text = self._letter()
		self.assertIn("Subject: Relieving Letter", text)
