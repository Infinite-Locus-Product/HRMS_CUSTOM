"""Tests for Stage A of the resignation flow (`myhr.employee_separation_hooks`).

Covers the four rules that cannot be expressed declaratively: the recomputed
notice-period figures, the relieving-date guards, the Detailed Reason cap, and
one-active-separation-per-employee.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

NOTICE_DAYS = 60
TEST_EMAIL = "separation.stage.a@example.com"


def _get_company():
	company = frappe.db.get_value("Company", {}, "name")
	if not company:
		raise RuntimeError("No Company in this site; create one first.")
	return company


def _get_cost_center(company):
	"""myHR makes payroll_cost_center mandatory on Employee (Elixiir merge)."""
	return frappe.db.get_value("Company", company, "cost_center") or frappe.db.get_value(
		"Cost Center", {"company": company, "is_group": 0}, "name"
	)


def _get_holiday_list():
	"""Submitting a separation resolves a holiday list for the employee."""
	today = getdate(nowdate())
	for name in frappe.get_all("Holiday List", pluck="name"):
		from_date, to_date = frappe.db.get_value("Holiday List", name, ["from_date", "to_date"])
		if from_date and to_date and getdate(from_date) <= today <= getdate(to_date):
			return name
	return None


def _apply_myhr_mandatory_fields(doc, company, employee_number):
	"""employee_number / ctc / payroll_cost_center are reqd via _apply_elixiir_mandatory_fields."""
	doc.employee_number = employee_number
	doc.ctc = 600000
	doc.payroll_cost_center = _get_cost_center(company)
	holiday_list = _get_holiday_list()
	if holiday_list:
		doc.holiday_list = holiday_list
		doc.custom_holiday_list = holiday_list


def _ensure_employee(notice_days=NOTICE_DAYS, date_of_joining=None):
	"""An Employee with a known notice period and joining date."""
	name = frappe.db.get_value("Employee", {"personal_email": TEST_EMAIL}, "name")
	if name:
		doc = frappe.get_doc("Employee", name)
	else:
		doc = frappe.new_doc("Employee")
		doc.first_name = "_Test Separation"
		doc.personal_email = TEST_EMAIL
		doc.gender = "Male"
		doc.date_of_birth = "1990-01-01"
		doc.company = _get_company()

	company = _get_company()
	doc.company = company
	doc.status = "Active"
	doc.date_of_joining = date_of_joining or add_days(nowdate(), -900)
	doc.custom_notice_period_days = notice_days
	_apply_myhr_mandatory_fields(doc, company, "_TEST-SEP-001")
	doc.save(ignore_permissions=True)
	return doc


def _ensure_user(email, first_name):
	"""A User carrying the plain Employee role — no elevated permissions.

	The workflow transitions are `allowed` to the Employee role, so these users
	deliberately hold nothing more: anything they can or cannot do in the tests
	is decided by the transition condition, not by privilege.
	"""
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.email = email
		user.first_name = first_name
		user.send_welcome_email = 0
		user.insert(ignore_permissions=True)
	else:
		user = frappe.get_doc("User", email)

	if "Employee" not in {r.role for r in user.roles}:
		user.add_roles("Employee")
	return user.name


def _ensure_user_for(employee):
	"""Link a User to an existing Employee and return the email."""
	if employee.user_id:
		return employee.user_id
	email = f"user.{employee.name.lower()}@example.com"
	employee.user_id = _ensure_user(email, employee.employee_name or "Test")
	employee.save(ignore_permissions=True)
	return employee.user_id


def _ensure_hierarchy_employee(email, first_name, with_user=False):
	"""A bare Active employee used only as a reporting/L2 target."""
	name = frappe.db.get_value("Employee", {"personal_email": email}, "name")
	if name:
		doc = frappe.get_doc("Employee", name)
		if with_user and not doc.user_id:
			doc.user_id = _ensure_user(email, first_name)
			doc.save(ignore_permissions=True)
		return doc

	doc = frappe.new_doc("Employee")
	doc.first_name = first_name
	doc.personal_email = email
	doc.gender = "Male"
	doc.date_of_birth = "1990-01-01"
	doc.date_of_joining = add_days(nowdate(), -1200)
	company = _get_company()
	doc.company = company
	_apply_myhr_mandatory_fields(doc, company, f"_TEST-SEP-{abs(hash(email)) % 10000:04d}")
	if with_user:
		doc.user_id = _ensure_user(email, first_name)
	doc.save(ignore_permissions=True)
	return doc


# Raised automatically when a separation is approved, and they link back to it —
# so they have to go before the separation can be deleted (LinkExistsError).
DOWNSTREAM_DOCTYPES = (
	"Full and Final Statement",
	"Separation HR Clearance",
	"Separation IT Clearance",
	"Separation Manager Clearance",
)


def _clear_downstream(employee):
	for doctype in DOWNSTREAM_DOCTYPES:
		for name in frappe.get_all(doctype, filters={"employee": employee}, pluck="name"):
			doc = frappe.get_doc(doctype, name)
			if doc.docstatus == 1:
				doc.cancel()
			doc.delete(ignore_permissions=True)


def _open_downstream(doctype, separation):
	"""An empty record to build on, replacing any auto-raised draft.

	Approval raises all four downstream drafts and the separation link is
	unique, so a test inserting its own would collide. These per-doctype tests
	are about that doctype's own rules, and construct exactly the record they
	need — auto-creation is covered separately in this module, so the stub is
	simply cleared out of the way here.
	"""
	name = frappe.db.get_value(
		doctype, {"employee_separation": separation, "docstatus": ["<", 2]}, "name"
	)
	if name:
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)

	doc = frappe.new_doc(doctype)
	doc.employee_separation = separation
	return doc


def _clear_separations(employee):
	_clear_downstream(employee)
	for name in frappe.get_all("Employee Separation", filters={"employee": employee}, pluck="name"):
		doc = frappe.get_doc("Employee Separation", name)
		if doc.docstatus == 1:
			doc.cancel()
		doc.delete(ignore_permissions=True)


def _new_separation(employee, **kwargs):
	doc = frappe.new_doc("Employee Separation")
	doc.employee = employee.name
	doc.company = employee.company
	doc.boarding_begins_on = nowdate()
	doc.custom_resignation_reason = "Personal"
	doc.custom_buyout_notice_period = "No"
	doc.custom_requested_relieving_date = add_days(nowdate(), NOTICE_DAYS)
	doc.update(kwargs)
	return doc


class TestEmployeeSeparationStageA(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.employee = _ensure_employee()

	def setUp(self):
		_clear_separations(self.employee.name)

	def tearDown(self):
		_clear_separations(self.employee.name)

	# -- fetch_from wiring --------------------------------------------------
	def test_manager_and_l2_are_fetched_from_the_employee(self):
		"""Reporting Manager and L2 fill declaratively — no controller code."""
		manager = _ensure_hierarchy_employee("separation.l1@example.com", "_Test Sep L1")
		l2 = _ensure_hierarchy_employee("separation.l2@example.com", "_Test Sep L2")

		self.employee.reports_to = manager.name
		self.employee.custom_l2_manager = l2.name
		self.employee.save(ignore_permissions=True)

		doc = _new_separation(self.employee)
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.custom_reporting_manager, manager.name)
		self.assertEqual(doc.custom_reporting_manager_name, manager.employee_name)
		self.assertEqual(doc.custom_l2_manager, l2.name)
		self.assertEqual(doc.custom_l2_manager_name, l2.employee_name)

	# -- rule 1: recompute, never trust -------------------------------------
	def test_official_end_date_and_shortfall_are_computed(self):
		requested = add_days(nowdate(), 10)
		doc = _new_separation(self.employee, custom_requested_relieving_date=requested)
		doc.insert(ignore_permissions=True)

		expected_end = getdate(add_days(nowdate(), NOTICE_DAYS))
		self.assertEqual(getdate(doc.custom_official_end_date), expected_end)
		self.assertEqual(doc.custom_notice_period_shortfall, NOTICE_DAYS - 10)

	def test_shortfall_is_floored_at_zero_when_full_notice_is_served(self):
		doc = _new_separation(
			self.employee, custom_requested_relieving_date=add_days(nowdate(), NOTICE_DAYS + 30)
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.custom_notice_period_shortfall, 0)

	def test_hand_set_shortfall_is_overwritten_on_save(self):
		"""read_only is a UI flag; an API write must not survive validate."""
		doc = _new_separation(self.employee, custom_requested_relieving_date=add_days(nowdate(), 10))
		doc.custom_notice_period_shortfall = 0
		doc.custom_official_end_date = add_days(nowdate(), 1)
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.custom_notice_period_shortfall, NOTICE_DAYS - 10)
		self.assertEqual(getdate(doc.custom_official_end_date), getdate(add_days(nowdate(), NOTICE_DAYS)))

	def test_shortfall_recalculates_when_relieving_date_moves(self):
		doc = _new_separation(self.employee, custom_requested_relieving_date=add_days(nowdate(), 10))
		doc.insert(ignore_permissions=True)

		doc.custom_requested_relieving_date = add_days(nowdate(), 20)
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.custom_notice_period_shortfall, NOTICE_DAYS - 20)

	# -- rule 2: relieving date guards --------------------------------------
	def test_past_relieving_date_is_rejected(self):
		doc = _new_separation(self.employee, custom_requested_relieving_date=add_days(nowdate(), -1))
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_relieving_date_before_joining_is_rejected(self):
		employee = _ensure_employee(date_of_joining=add_days(nowdate(), 30))
		_clear_separations(employee.name)
		doc = _new_separation(employee, custom_requested_relieving_date=add_days(nowdate(), 5))
		try:
			self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)
		finally:
			_ensure_employee()  # restore the shared joining date

	def test_unchanged_past_date_does_not_block_a_later_save(self):
		"""Editing an old separation must not re-litigate a date valid when filed."""
		doc = _new_separation(self.employee, custom_requested_relieving_date=add_days(nowdate(), 10))
		doc.insert(ignore_permissions=True)

		frappe.db.set_value(
			"Employee Separation", doc.name, "custom_requested_relieving_date", add_days(nowdate(), -5)
		)
		reloaded = frappe.get_doc("Employee Separation", doc.name)
		reloaded.exit_interview = "<p>notes</p>"
		reloaded.save(ignore_permissions=True)  # must not throw

		self.assertEqual(reloaded.custom_notice_period_shortfall, NOTICE_DAYS + 5)

	# -- rule 3: detailed reason cap ----------------------------------------
	def test_detailed_reason_over_500_chars_is_rejected(self):
		doc = _new_separation(self.employee, custom_detailed_reason="x" * 501)
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_detailed_reason_at_exactly_500_chars_is_accepted(self):
		doc = _new_separation(self.employee, custom_detailed_reason="x" * 500)
		doc.insert(ignore_permissions=True)
		self.assertEqual(len(doc.custom_detailed_reason), 500)

	# -- rule 4: one active separation --------------------------------------
	def test_second_active_separation_is_rejected(self):
		_new_separation(self.employee).insert(ignore_permissions=True)
		second = _new_separation(self.employee)
		self.assertRaises(frappe.ValidationError, second.insert, ignore_permissions=True)

	def test_a_cancelled_separation_does_not_block_a_new_one(self):
		first = _new_separation(self.employee)
		first.insert(ignore_permissions=True)
		first.submit()
		first.cancel()

		second = _new_separation(self.employee)
		second.insert(ignore_permissions=True)  # must not throw
		self.assertTrue(second.name)

	# -- buy-out conditional ------------------------------------------------
	def test_buyout_amount_is_mandatory_when_buyout_is_yes(self):
		"""mandatory_depends_on runs client-side only, so validate enforces it too."""
		doc = _new_separation(self.employee, custom_buyout_notice_period="Yes")
		self.assertRaises(frappe.MandatoryError, doc.insert, ignore_permissions=True)

	def test_buyout_amount_is_accepted_when_provided(self):
		doc = _new_separation(
			self.employee, custom_buyout_notice_period="Yes", custom_buyout_amount=45000
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.custom_buyout_amount, 45000)

	# -- Stage B: approval fields -------------------------------------------
	def test_approval_fields_are_not_required_before_a_decision(self):
		"""The employee must be able to file without the approver's fields."""
		doc = _new_separation(self.employee)
		doc.insert(ignore_permissions=True)
		self.assertFalse(doc.custom_decision)
		self.assertFalse(doc.custom_approved_relieving_date)

	def test_approved_relieving_date_defaults_to_the_request(self):
		requested = add_days(nowdate(), 30)
		doc = _new_separation(self.employee, custom_requested_relieving_date=requested)
		doc.insert(ignore_permissions=True)

		doc.custom_decision = "Approve"
		doc.custom_notice_period_waiver = "No"
		doc.custom_retention_discussion_held = "Yes"
		doc.save(ignore_permissions=True)

		self.assertEqual(getdate(doc.custom_approved_relieving_date), getdate(requested))

	def test_reject_without_a_reason_is_blocked(self):
		doc = _new_separation(self.employee)
		doc.insert(ignore_permissions=True)
		doc.custom_decision = "Reject"
		self.assertRaises(frappe.MandatoryError, doc.save, ignore_permissions=True)

	def test_hold_without_a_reason_is_blocked(self):
		doc = _new_separation(self.employee)
		doc.insert(ignore_permissions=True)
		doc.custom_decision = "Hold"
		self.assertRaises(frappe.MandatoryError, doc.save, ignore_permissions=True)

	def test_reject_with_a_reason_is_accepted(self):
		doc = _new_separation(self.employee)
		doc.insert(ignore_permissions=True)
		doc.custom_decision = "Reject"
		doc.custom_rejection_hold_reason = "Counter-offer accepted."
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.custom_decision, "Reject")

	def test_approve_without_the_approver_fields_is_blocked(self):
		doc = _new_separation(self.employee)
		doc.insert(ignore_permissions=True)
		doc.custom_decision = "Approve"
		self.assertRaises(frappe.MandatoryError, doc.save, ignore_permissions=True)

	def test_waiver_does_not_block_approval(self):
		"""The HR Ops flag is visibility, not a gate."""
		doc = _new_separation(self.employee)
		doc.insert(ignore_permissions=True)
		doc.custom_decision = "Approve"
		doc.custom_notice_period_waiver = "Yes"
		doc.custom_retention_discussion_held = "Yes"
		doc.save(ignore_permissions=True)
		doc.submit()
		self.assertEqual(doc.docstatus, 1)


class TestEmployeeSeparationWorkflow(IntegrationTestCase):
	"""Stage B routing: Draft -> L1 -> L2 -> Approved, gated per person.

	Frappe's `allowed` on a transition is role-based, so every one of these
	people holds the plain Employee role. The gate that stops a manager acting
	on somebody else's resignation is the transition `condition`, and
	`apply_workflow` re-derives conditions server-side before allowing the
	action — so these tests assert real enforcement, not UI hiding.
	"""

	WORKFLOW = "Employee Separation Approval"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# The workflow emails the next approver with the document attached as a
		# PDF. That is wanted behaviour, but rendering the PDF needs wkhtmltopdf,
		# which is not installed on every dev machine — so the alert is muted for
		# the duration of this class and restored afterwards. Routing itself is
		# unaffected; only the notification is suppressed.
		cls._email_alert = frappe.db.get_value("Workflow", cls.WORKFLOW, "send_email_alert")
		frappe.db.set_value("Workflow", cls.WORKFLOW, "send_email_alert", 0)
		frappe.clear_cache()

		cls.l1 = _ensure_hierarchy_employee("wf.l1@example.com", "_Test WF L1", with_user=True)
		cls.l2 = _ensure_hierarchy_employee("wf.l2@example.com", "_Test WF L2", with_user=True)
		cls.employee = _ensure_employee()
		cls.employee.reports_to = cls.l1.name
		cls.employee.custom_l2_manager = cls.l2.name
		cls.employee.save(ignore_permissions=True)
		cls.emp_user = _ensure_user_for(cls.employee)

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_value("Workflow", cls.WORKFLOW, "send_email_alert", cls._email_alert)
		frappe.clear_cache()
		super().tearDownClass()

	def setUp(self):
		frappe.set_user("Administrator")
		_clear_separations(self.employee.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		_clear_separations(self.employee.name)

	def _file(self):
		doc = _new_separation(self.employee)
		doc.insert(ignore_permissions=True)
		return doc

	def _actions_for(self, doc, user):
		from frappe.model.workflow import get_transitions

		frappe.set_user(user)
		try:
			return {t.action for t in get_transitions(frappe.get_doc(doc.doctype, doc.name))}
		finally:
			frappe.set_user("Administrator")

	def _apply(self, doc, action, user):
		from frappe.model.workflow import apply_workflow

		frappe.set_user(user)
		try:
			return apply_workflow(frappe.get_doc(doc.doctype, doc.name), action)
		finally:
			frappe.set_user("Administrator")

	def test_new_record_starts_in_draft(self):
		doc = self._file()
		self.assertEqual(doc.workflow_state, "Draft")
		self.assertEqual(doc.docstatus, 0)

	def test_full_route_draft_to_l1_to_l2_to_approved(self):
		doc = self._file()

		self._apply(doc, "Submit", self.emp_user)
		doc.reload()
		self.assertEqual(doc.workflow_state, "Pending L1 Approval")
		self.assertEqual(doc.docstatus, 0, "must stay a draft while under approval")

		self._apply(doc, "Approve", self.l1.user_id)
		doc.reload()
		self.assertEqual(doc.workflow_state, "Pending L2 Approval")
		self.assertEqual(doc.custom_l1_approved, 1)
		self.assertEqual(doc.docstatus, 0)

		self._apply(doc, "Approve", self.l2.user_id)
		doc.reload()
		self.assertEqual(doc.workflow_state, "Approved")
		self.assertEqual(doc.custom_l2_approved, 1, "the L2 Approve button ticks this")
		self.assertEqual(doc.docstatus, 1, "only L2 approval actually submits the document")

	def test_l2_cannot_approve_before_l1(self):
		doc = self._file()
		self._apply(doc, "Submit", self.emp_user)
		self.assertNotIn("Approve", self._actions_for(doc, self.l2.user_id))

	def test_another_manager_cannot_act_on_this_record(self):
		"""A manager who is not this record's L1 or L2 gets nothing.

		The block lands one layer earlier than the workflow condition: the
		permission hook means a stranger fails the read check, so
		`apply_workflow` never gets as far as evaluating the transition. That is
		the stronger of the two guarantees, so this asserts PermissionError
		rather than merely "no Approve button".

		The check is made through `get_transitions` (which calls
		`doc.check_permission`) rather than `frappe.get_doc`: get_doc does NOT
		run permission checks by itself, so asserting on it would pass for the
		wrong reason.
		"""
		stranger = _ensure_hierarchy_employee("wf.stranger@example.com", "_Test WF Other", with_user=True)
		doc = self._file()
		self._apply(doc, "Submit", self.emp_user)

		self.assertRaises(frappe.PermissionError, self._actions_for, doc, stranger.user_id)

	def test_l1_reject_returns_it_to_the_employee(self):
		doc = self._file()
		self._apply(doc, "Submit", self.emp_user)

		frappe.set_user(self.l1.user_id)
		try:
			target = frappe.get_doc(doc.doctype, doc.name)
			target.custom_rejection_hold_reason = "Discuss retention first."
			target.save()
			from frappe.model.workflow import apply_workflow

			apply_workflow(target, "Reject")
		finally:
			frappe.set_user("Administrator")

		doc.reload()
		self.assertEqual(doc.workflow_state, "Rejected")
		self.assertEqual(doc.custom_decision, "Reject", "the Rejected state stamps the decision")
		self.assertEqual(doc.docstatus, 0, "must stay editable so the employee can re-submit")

	def test_employee_can_resubmit_after_rejection(self):
		doc = self._file()
		self._apply(doc, "Submit", self.emp_user)

		frappe.set_user(self.l1.user_id)
		try:
			target = frappe.get_doc(doc.doctype, doc.name)
			target.custom_rejection_hold_reason = "Needs a later date."
			target.save()
			from frappe.model.workflow import apply_workflow

			apply_workflow(target, "Reject")
		finally:
			frappe.set_user("Administrator")

		self._apply(doc, "Resubmit", self.emp_user)
		doc.reload()
		self.assertEqual(doc.workflow_state, "Pending L1 Approval")


class TestResignationApi(IntegrationTestCase):
	"""The PWA path, exercised as the employee themselves.

	This class exists because TestEmployeeSeparationWorkflow inserts its records
	as Administrator, which makes Administrator the document owner. In production
	the employee creates their own record and IS the owner — and Frappe treats an
	owner applying a transition as "self approval". That difference hid a bug
	where nobody could file a resignation at all, so these tests go through
	myhr.resignation_api exactly as the frontend does.
	"""

	WORKFLOW = "Employee Separation Approval"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._email_alert = frappe.db.get_value("Workflow", cls.WORKFLOW, "send_email_alert")
		frappe.db.set_value("Workflow", cls.WORKFLOW, "send_email_alert", 0)
		frappe.clear_cache()

		cls.l1 = _ensure_hierarchy_employee("api.l1@example.com", "_Api L1", with_user=True)
		cls.l2 = _ensure_hierarchy_employee("api.l2@example.com", "_Api L2", with_user=True)
		cls.employee = _ensure_employee()
		cls.employee.reports_to = cls.l1.name
		cls.employee.custom_l2_manager = cls.l2.name
		cls.employee.save(ignore_permissions=True)
		cls.emp_user = _ensure_user_for(cls.employee)

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_value("Workflow", cls.WORKFLOW, "send_email_alert", cls._email_alert)
		frappe.clear_cache()
		super().tearDownClass()

	def setUp(self):
		frappe.set_user("Administrator")
		_clear_separations(self.employee.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		_clear_separations(self.employee.name)

	def _payload(self, **overrides):
		data = {
			"custom_resignation_reason": "Better Opportunity",
			"custom_detailed_reason": "Moving on.",
			"custom_requested_relieving_date": add_days(nowdate(), 30),
			"custom_buyout_notice_period": "No",
		}
		data.update(overrides)
		return frappe.as_json(data)

	def test_filing_stamps_the_resignation_date(self):
		"""The relieving letter opens with "your resignation dated ...", and the
		notice-period rules anchor on this. Nothing else ever sets it."""
		frappe.set_user(self.emp_user)
		try:
			from myhr.resignation_api import save_my_resignation

			result = save_my_resignation(self._payload(), 0)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(
			getdate(frappe.db.get_value("Employee Separation", result["name"], "resignation_letter_date")),
			getdate(nowdate()),
		)

	def test_get_returns_the_chain_and_defaults(self):
		frappe.set_user(self.emp_user)
		try:
			from myhr.resignation_api import get_my_resignation

			data = get_my_resignation()
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(data["employee"]["reporting_manager"], self.l1.employee_name)
		self.assertEqual(data["employee"]["l2_manager"], self.l2.employee_name)
		self.assertIn("Better Opportunity", data["options"]["resignation_reason"])
		self.assertIsNone(data["existing"])

	def test_employee_can_file_their_own_resignation(self):
		"""The regression: the employee owns the doc, so Submit is self-approval."""
		frappe.set_user(self.emp_user)
		try:
			from myhr.resignation_api import save_my_resignation

			result = save_my_resignation(self._payload(), submit=1)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["workflow_state"], "Pending L1 Approval")
		self.assertEqual(result["docstatus"], 0, "must stay a draft while under approval")
		self.assertFalse(result["editable"], "locked once it is with the manager")

	def test_saving_a_draft_does_not_route_it(self):
		frappe.set_user(self.emp_user)
		try:
			from myhr.resignation_api import save_my_resignation

			result = save_my_resignation(self._payload(), submit=0)
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(result["workflow_state"], "Draft")
		self.assertTrue(result["editable"])

	def test_a_filed_resignation_can_no_longer_be_edited(self):
		frappe.set_user(self.emp_user)
		try:
			from myhr.resignation_api import save_my_resignation

			save_my_resignation(self._payload(), submit=1)
			self.assertRaises(
				frappe.ValidationError, save_my_resignation, self._payload(), 0
			)
		finally:
			frappe.set_user("Administrator")

	def test_it_lands_in_the_l1_inbox_and_not_the_l2_inbox(self):
		frappe.set_user(self.emp_user)
		try:
			from myhr.resignation_api import save_my_resignation

			save_my_resignation(self._payload(), submit=1)
		finally:
			frappe.set_user("Administrator")

		from myhr.resignation_api import get_my_pending_approvals

		frappe.set_user(self.l1.user_id)
		try:
			inbox = get_my_pending_approvals()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(len(inbox), 1)
		self.assertEqual(inbox[0]["my_level"], "L1")

		frappe.set_user(self.l2.user_id)
		try:
			self.assertEqual(get_my_pending_approvals(), [], "L2 waits until L1 has acted")
		finally:
			frappe.set_user("Administrator")

	def test_server_rules_still_apply_through_the_api(self):
		frappe.set_user(self.emp_user)
		try:
			from myhr.resignation_api import save_my_resignation

			self.assertRaises(
				frappe.ValidationError,
				save_my_resignation,
				self._payload(custom_detailed_reason="x" * 501),
				0,
			)
		finally:
			frappe.set_user("Administrator")


class TestResignationApprovalApi(IntegrationTestCase):
	"""The L1/L2 approver endpoints behind the PWA approvals screen."""

	WORKFLOW = "Employee Separation Approval"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._email_alert = frappe.db.get_value("Workflow", cls.WORKFLOW, "send_email_alert")
		frappe.db.set_value("Workflow", cls.WORKFLOW, "send_email_alert", 0)
		frappe.clear_cache()

		cls.l1 = _ensure_hierarchy_employee("appr.l1@example.com", "_Appr L1", with_user=True)
		cls.l2 = _ensure_hierarchy_employee("appr.l2@example.com", "_Appr L2", with_user=True)
		cls.employee = _ensure_employee()
		cls.employee.reports_to = cls.l1.name
		cls.employee.custom_l2_manager = cls.l2.name
		cls.employee.save(ignore_permissions=True)
		cls.emp_user = _ensure_user_for(cls.employee)

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_value("Workflow", cls.WORKFLOW, "send_email_alert", cls._email_alert)
		frappe.clear_cache()
		super().tearDownClass()

	def setUp(self):
		frappe.set_user("Administrator")
		_clear_separations(self.employee.name)
		self.doc_name = self._file()

	def tearDown(self):
		frappe.set_user("Administrator")
		_clear_separations(self.employee.name)

	def _file(self):
		frappe.set_user(self.emp_user)
		try:
			from myhr.resignation_api import save_my_resignation

			result = save_my_resignation(
				frappe.as_json({
					"custom_resignation_reason": "Personal",
					"custom_requested_relieving_date": add_days(nowdate(), 30),
					"custom_buyout_notice_period": "No",
				}),
				submit=1,
			)
		finally:
			frappe.set_user("Administrator")
		return result["name"]

	def _as(self, user, fn, *args, **kwargs):
		frappe.set_user(user)
		try:
			return fn(*args, **kwargs)
		finally:
			frappe.set_user("Administrator")

	def _approval_payload(self, **overrides):
		data = {
			"custom_approved_relieving_date": add_days(nowdate(), 30),
			"custom_notice_period_waiver": "No",
			"custom_retention_discussion_held": "Yes",
		}
		data.update(overrides)
		return frappe.as_json(data)

	def test_detail_gives_l1_the_employee_filing_and_their_actions(self):
		from myhr.resignation_api import get_separation_for_approval

		data = self._as(self.l1.user_id, get_separation_for_approval, self.doc_name)
		self.assertEqual(data["custom_resignation_reason"], "Personal")
		self.assertEqual(data["workflow_state"], "Pending L1 Approval")
		self.assertIn("Approve", data["actions"])
		self.assertIn("Reject", data["actions"])

	def test_l2_has_no_actions_while_it_sits_with_l1(self):
		from myhr.resignation_api import get_separation_for_approval

		data = self._as(self.l2.user_id, get_separation_for_approval, self.doc_name)
		self.assertNotIn("Approve", data["actions"])

	def test_l1_approve_moves_it_to_l2_and_stamps_the_checkbox(self):
		from myhr.resignation_api import act_on_separation

		result = self._as(
			self.l1.user_id, act_on_separation, self.doc_name, "Approve", self._approval_payload()
		)
		self.assertEqual(result["workflow_state"], "Pending L2 Approval")
		self.assertEqual(result["custom_l1_approved"], 1)
		self.assertEqual(result["custom_l2_approved"], 0)
		self.assertEqual(result["docstatus"], 0)

	def test_l2_approve_finalises_and_submits(self):
		from myhr.resignation_api import act_on_separation

		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", self._approval_payload())
		result = self._as(
			self.l2.user_id, act_on_separation, self.doc_name, "Approve", self._approval_payload()
		)
		self.assertEqual(result["workflow_state"], "Approved")
		self.assertEqual(result["custom_l2_approved"], 1)
		self.assertEqual(result["docstatus"], 1)

	def test_approve_without_the_mandatory_fields_is_refused(self):
		"""And critically, the document must NOT have moved."""
		from myhr.resignation_api import act_on_separation

		self.assertRaises(
			frappe.MandatoryError,
			self._as,
			self.l1.user_id,
			act_on_separation,
			self.doc_name,
			"Approve",
			frappe.as_json({}),
		)
		self.assertEqual(
			frappe.db.get_value("Employee Separation", self.doc_name, "workflow_state"),
			"Pending L1 Approval",
		)

	def test_reject_without_a_reason_is_refused(self):
		from myhr.resignation_api import act_on_separation

		self.assertRaises(
			frappe.MandatoryError,
			self._as,
			self.l1.user_id,
			act_on_separation,
			self.doc_name,
			"Reject",
			frappe.as_json({}),
		)

	def test_reject_returns_it_to_the_employee_for_editing(self):
		from myhr.resignation_api import act_on_separation

		result = self._as(
			self.l1.user_id,
			act_on_separation,
			self.doc_name,
			"Reject",
			frappe.as_json({"custom_rejection_hold_reason": "Let us talk first."}),
		)
		self.assertEqual(result["workflow_state"], "Rejected")
		self.assertEqual(result["custom_decision"], "Reject")
		self.assertTrue(result["editable"])
		self.assertEqual(result["docstatus"], 0)

	def test_l2_cannot_act_while_it_is_with_l1(self):
		from myhr.resignation_api import act_on_separation

		self.assertRaises(
			frappe.ValidationError,
			self._as,
			self.l2.user_id,
			act_on_separation,
			self.doc_name,
			"Approve",
			self._approval_payload(),
		)

	def test_an_unrelated_employee_cannot_open_it(self):
		from myhr.resignation_api import get_separation_for_approval

		stranger = _ensure_hierarchy_employee("appr.other@example.com", "_Appr Other", with_user=True)
		self.assertRaises(
			frappe.PermissionError,
			self._as,
			stranger.user_id,
			get_separation_for_approval,
			self.doc_name,
		)

	def test_l1_has_no_actions_once_they_have_approved(self):
		"""Drives the PWA hiding the buttons and showing the status instead."""
		from myhr.resignation_api import act_on_separation, get_separation_for_approval

		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", self._approval_payload())

		data = self._as(self.l1.user_id, get_separation_for_approval, self.doc_name)
		self.assertEqual(data["workflow_state"], "Pending L2 Approval")
		self.assertEqual(data["actions"], [], "L1 is done; the screen must offer them nothing")

	def test_l2_gains_actions_once_l1_has_approved(self):
		from myhr.resignation_api import act_on_separation, get_separation_for_approval

		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", self._approval_payload())

		data = self._as(self.l2.user_id, get_separation_for_approval, self.doc_name)
		self.assertIn("Approve", data["actions"])
		self.assertIn("Reject", data["actions"])

	def test_no_actions_remain_once_fully_approved(self):
		from myhr.resignation_api import act_on_separation, get_separation_for_approval

		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", self._approval_payload())
		self._as(self.l2.user_id, act_on_separation, self.doc_name, "Approve", self._approval_payload())

		for user in (self.l1.user_id, self.l2.user_id):
			data = self._as(user, get_separation_for_approval, self.doc_name)
			self.assertEqual(data["workflow_state"], "Approved")
			self.assertEqual(data["actions"], [])

	def test_l2_approve_without_a_holiday_list_fails_legibly(self):
		"""Submitting builds the separation tasks, which need a Holiday List.

		Without the guard this surfaces as a markup-laden HRMS message about
		Holiday List Assignment that never mentions the resignation, and the
		approver just sees the button fail with no useful explanation.

		The resolver is patched rather than the data cleared: it falls back from
		the employee to the company, so clearing one field proves nothing.
		"""
		from unittest.mock import patch

		from myhr.resignation_api import act_on_separation

		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", self._approval_payload())

		with patch("hrms.utils.holiday_list.get_holiday_list_for_employee", return_value=None):
			with self.assertRaises(frappe.ValidationError) as caught:
				self._as(
					self.l2.user_id, act_on_separation, self.doc_name, "Approve",
					self._approval_payload(),
				)

		self.assertIn("Holiday List", str(caught.exception))
		self.assertEqual(
			frappe.db.get_value("Employee Separation", self.doc_name, "workflow_state"),
			"Pending L2 Approval",
			"the record must not move when the submit would fail",
		)

	def test_l1_approve_skips_the_submit_precheck(self):
		"""L1's approval does not submit, so a missing Holiday List must not block it."""
		from unittest.mock import patch

		from myhr.resignation_api import act_on_separation

		with patch("hrms.utils.holiday_list.get_holiday_list_for_employee", return_value=None):
			result = self._as(
				self.l1.user_id, act_on_separation, self.doc_name, "Approve",
				self._approval_payload(),
			)
		self.assertEqual(result["workflow_state"], "Pending L2 Approval")

	def test_the_action_response_carries_the_new_state_and_actions(self):
		"""The screen swaps this payload in directly, so it must be complete.

		If `actions` were missing or stale the approver would keep seeing live
		Approve/Reject buttons on a record they have already decided.
		"""
		from myhr.resignation_api import act_on_separation

		result = self._as(
			self.l1.user_id, act_on_separation, self.doc_name, "Approve", self._approval_payload()
		)
		self.assertEqual(result["workflow_state"], "Pending L2 Approval")
		self.assertEqual(result["actions"], [], "L1 is done, so their buttons must go")
		self.assertIn("options", result)
		self.assertEqual(result["employee_name"], self.employee.employee_name)

		final = self._as(
			self.l2.user_id, act_on_separation, self.doc_name, "Approve", self._approval_payload()
		)
		self.assertEqual(final["workflow_state"], "Approved")
		self.assertEqual(final["actions"], [])
		self.assertEqual(final["docstatus"], 1)

	def test_final_approval_pushes_the_relieving_date_onto_the_employee(self):
		"""Without this, HRMS refuses to create an Exit Interview at all.

		Stage 8 (HR clearance / relieving letter) is then unreachable, so this
		one field write is what keeps the back half of the exit flow possible.
		"""
		from myhr.resignation_api import act_on_separation

		frappe.db.set_value("Employee", self.employee.name, "relieving_date", None)
		approved_on = add_days(nowdate(), 45)
		payload = self._approval_payload(custom_approved_relieving_date=approved_on)

		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", payload)
		self.assertIsNone(
			frappe.db.get_value("Employee", self.employee.name, "relieving_date"),
			"L1 approval does not submit, so nothing should be written yet",
		)

		self._as(self.l2.user_id, act_on_separation, self.doc_name, "Approve", payload)
		self.assertEqual(
			getdate(frappe.db.get_value("Employee", self.employee.name, "relieving_date")),
			getdate(approved_on),
		)

	def test_cancelling_the_separation_clears_the_relieving_date(self):
		from myhr.resignation_api import act_on_separation

		frappe.db.set_value("Employee", self.employee.name, "relieving_date", None)
		payload = self._approval_payload()
		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", payload)
		self._as(self.l2.user_id, act_on_separation, self.doc_name, "Approve", payload)
		self.assertTrue(frappe.db.get_value("Employee", self.employee.name, "relieving_date"))

		frappe.get_doc("Employee Separation", self.doc_name).cancel()
		self.assertIsNone(frappe.db.get_value("Employee", self.employee.name, "relieving_date"))

	def test_a_hand_entered_relieving_date_survives_cancellation(self):
		"""Only a date this document set is cleared; HR's own entry wins."""
		from myhr.resignation_api import act_on_separation

		payload = self._approval_payload()
		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", payload)
		self._as(self.l2.user_id, act_on_separation, self.doc_name, "Approve", payload)

		hr_entered = add_days(nowdate(), 90)
		frappe.db.set_value("Employee", self.employee.name, "relieving_date", hr_entered)

		frappe.get_doc("Employee Separation", self.doc_name).cancel()
		self.assertEqual(
			getdate(frappe.db.get_value("Employee", self.employee.name, "relieving_date")),
			getdate(hr_entered),
		)

	def test_shortfall_follows_the_approved_date_not_the_request(self):
		"""The worked example: requested 31 Oct, approved 14 Nov, end 24 Nov.

		Measured against the request it reads 24 days; against the date actually
		approved it is 10. Finance Clearance multiplies this by a daily rate, so
		the difference is real money taken from a final settlement.
		"""
		from myhr.resignation_api import act_on_separation

		requested = add_days(nowdate(), 10)
		approved = add_days(nowdate(), 24)

		frappe.db.set_value(
			"Employee Separation", self.doc_name, "custom_requested_relieving_date", requested
		)
		doc = frappe.get_doc("Employee Separation", self.doc_name)
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.custom_notice_period_shortfall, NOTICE_DAYS - 10)

		self._as(
			self.l1.user_id, act_on_separation, self.doc_name, "Approve",
			self._approval_payload(custom_approved_relieving_date=approved),
		)
		doc.reload()
		self.assertEqual(
			doc.custom_notice_period_shortfall,
			NOTICE_DAYS - 24,
			"once approved, the shortfall must follow the approved date",
		)

	def test_an_approver_can_wipe_the_shortfall_by_moving_the_date_out(self):
		"""Approving the full notice period leaves nothing to recover."""
		from myhr.resignation_api import act_on_separation

		self._as(
			self.l1.user_id, act_on_separation, self.doc_name, "Approve",
			self._approval_payload(custom_approved_relieving_date=add_days(nowdate(), NOTICE_DAYS)),
		)
		self.assertEqual(
			frappe.db.get_value(
				"Employee Separation", self.doc_name, "custom_notice_period_shortfall"
			),
			0,
		)

	# -- downstream drafts --------------------------------------------------
	def _downstream(self):
		return {
			dt: frappe.db.get_value(dt, {"employee_separation": self.doc_name}, "name")
			for dt in ("Separation Manager Clearance", "Separation IT Clearance",
			           "Separation HR Clearance")
		}

	def test_final_approval_raises_all_four_downstream_drafts(self):
		"""L2 approval should leave every owner a record already waiting."""
		from myhr.resignation_api import act_on_separation

		payload = self._approval_payload()
		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", payload)
		self.assertEqual(
			[v for v in self._downstream().values() if v], [],
			"L1 approval does not submit, so nothing should exist yet",
		)

		self._as(self.l2.user_id, act_on_separation, self.doc_name, "Approve", payload)

		for doctype, name in self._downstream().items():
			self.assertIsNotNone(name, f"{doctype} was not raised")
			self.assertEqual(frappe.db.get_value(doctype, name, "docstatus"), 0)

		self.assertTrue(
			frappe.db.get_value(
				"Full and Final Statement",
				{"employee": self.employee.name, "docstatus": 0},
				"name",
			),
			"the settlement was not raised",
		)

	def test_the_manager_clearance_starts_in_its_draft_state(self):
		from myhr.resignation_api import act_on_separation

		payload = self._approval_payload()
		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", payload)
		self._as(self.l2.user_id, act_on_separation, self.doc_name, "Approve", payload)

		name = self._downstream()["Separation Manager Clearance"]
		doc = frappe.get_doc("Separation Manager Clearance", name)
		self.assertEqual(doc.workflow_state, "Draft")
		self.assertEqual(doc.employee, self.employee.name)
		self.assertEqual(doc.reporting_manager, self.l1.name)

	def test_raising_the_drafts_twice_does_not_duplicate_them(self):
		"""Amending a cancelled separation must not produce a second set."""
		from myhr.employee_separation_hooks import create_downstream_records
		from myhr.resignation_api import act_on_separation

		payload = self._approval_payload()
		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", payload)
		self._as(self.l2.user_id, act_on_separation, self.doc_name, "Approve", payload)

		before = self._downstream()
		create_downstream_records(frappe.get_doc("Employee Separation", self.doc_name))
		self.assertEqual(self._downstream(), before)

		for doctype in before:
			self.assertEqual(
				frappe.db.count(doctype, {"employee_separation": self.doc_name}), 1, doctype
			)

	def test_a_failing_draft_does_not_roll_back_the_approval(self):
		"""Two levels of approval must not be undone by a downstream problem."""
		from unittest.mock import patch

		from myhr.resignation_api import act_on_separation

		payload = self._approval_payload()
		self._as(self.l1.user_id, act_on_separation, self.doc_name, "Approve", payload)

		with patch(
			"myhr.employee_separation_hooks._create_it_clearance",
			side_effect=Exception("boom"),
		):
			result = self._as(self.l2.user_id, act_on_separation, self.doc_name, "Approve", payload)

		self.assertEqual(result["workflow_state"], "Approved")
		self.assertEqual(result["docstatus"], 1)
		# The others still went out.
		self.assertIsNotNone(self._downstream()["Separation Manager Clearance"])
		self.assertIsNone(self._downstream()["Separation IT Clearance"])

