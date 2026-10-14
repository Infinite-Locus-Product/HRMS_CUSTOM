"""Tests for the public Job Application web form (`/apply`) and its
screening-question flow.

Exercises the real `web_form.accept` entry point so the whole chain runs:
web form field copy -> Job Applicant validate hook (age + response
reconciliation) -> insert. The rate limiter on `accept` is a no-op without an
HTTP request, so calling it directly is fine.
"""

from __future__ import annotations

import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.website.doctype.web_form.web_form import accept

from myhr.job_opening_hooks import APPLY_ROUTE

WEB_FORM = "fixxly-job-application"
TEST_COMPANY = "_Test Company"
JOB_TITLE = "_Test Screening Opening"
DESIGNATION = "_Test Screening Designation"
APPLICANT_EMAIL = "screening.applicant@example.com"


def _ensure_company():
	if frappe.db.exists("Company", TEST_COMPANY):
		return TEST_COMPANY
	existing = frappe.db.get_value("Company", {}, "name")
	if existing:
		return existing
	raise RuntimeError("No Company in this site; create one first.")


def _ensure_designation():
	if not frappe.db.exists("Designation", DESIGNATION):
		frappe.get_doc({"doctype": "Designation", "designation_name": DESIGNATION}).insert(
			ignore_permissions=True
		)
	return DESIGNATION


def _ensure_department():
	company = _ensure_company()
	name = frappe.db.get_value("Department", {"company": company, "is_group": 0}, "name")
	if name:
		return name
	dep = frappe.get_doc({"doctype": "Department", "department_name": "_Test Screening Dept", "company": company})
	dep.insert(ignore_permissions=True)
	return dep.name


def _make_opening(publish=1, status="Open", questions=None):
	"""Fresh Job Opening each call; the test transaction rolls it back."""
	doc = frappe.get_doc(
		{
			"doctype": "Job Opening",
			"job_title": f"{JOB_TITLE} {frappe.generate_hash(length=6)}",
			"company": _ensure_company(),
			"designation": _ensure_designation(),
			"department": _ensure_department(),
			"status": status,
			"publish": publish,
			"description": "Screening test opening",
			"custom_screening_questions": [
				{"question": q, "is_mandatory": m}
				for q, m in (questions if questions is not None else [("Why do you want this role?", 1), ("Notice period?", 0)])
			],
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _payload(opening, responses=None, **overrides):
	data = {
		"doctype": "Job Applicant",
		"web_form_name": WEB_FORM,
		"job_title": opening.name,
		"applicant_name": "Screening Applicant",
		"email_id": APPLICANT_EMAIL,
		"custom_date_of_birth": "1990-06-15",
		"custom_screening_responses": responses if responses is not None else [],
	}
	data.update(overrides)
	return json.dumps(data)


def _submit(opening, responses=None, **overrides):
	frappe.set_user("Guest")
	try:
		return accept(WEB_FORM, _payload(opening, responses, **overrides))
	finally:
		frappe.set_user("Administrator")
		frappe.flags.in_web_form = False


def _latest_applicant():
	name = frappe.db.get_value(
		"Job Applicant", {"job_title": ["like", "%"], "email_id": APPLICANT_EMAIL}, "name", order_by="creation desc"
	)
	return frappe.get_doc("Job Applicant", name)


class TestJobApplicationForm(IntegrationTestCase):
	def test_web_form_is_installed_and_public(self):
		wf = frappe.get_doc("Web Form", WEB_FORM)
		self.assertEqual(wf.route, APPLY_ROUTE)
		self.assertEqual(wf.doc_type, "Job Applicant")
		self.assertTrue(wf.published)
		self.assertFalse(wf.login_required)
		fieldnames = {f.fieldname for f in wf.web_form_fields if f.fieldname}
		# every candidate-facing value field on Job Applicant is on the form.
		# Excluded: Desk-only widgets and HR-side fields (kept off the public form).
		meta = frappe.get_meta("Job Applicant")
		skip = {
			"resume_preview_html", "open_resume_button",
			"status", "applicant_rating", "notes", "source", "source_name", "employee_referral",
		}
		expected = {
			df.fieldname
			for df in meta.fields
			if df.fieldtype not in frappe.model.no_value_fields and df.fieldname not in skip
		}
		self.assertEqual(expected - fieldnames, set())

	def test_valid_submission_creates_applicant_with_snapshot_rows(self):
		opening = _make_opening()
		q1, q2 = opening.custom_screening_questions
		_submit(
			opening,
			[
				{"source_question": q1.name, "question": "tampered text", "answer": "Because I like it"},
				{"source_question": q2.name, "answer": "30 days"},
			],
		)
		ja = _latest_applicant()
		self.assertEqual(ja.job_title, opening.name)
		self.assertEqual(ja.custom_age.split(" ")[1], "Years")
		self.assertEqual(ja.source, "Website Listing")
		self.assertEqual(ja.status, "Open")
		self.assertEqual(ja.custom_department, opening.department)
		rows = ja.custom_screening_responses
		self.assertEqual([r.question for r in rows], [q1.question, q2.question])
		self.assertEqual([r.answer for r in rows], ["Because I like it", "30 days"])
		self.assertEqual([r.is_mandatory for r in rows], [1, 0])
		self.assertEqual([r.source_question for r in rows], [q1.name, q2.name])

	def test_missing_mandatory_answer_is_rejected(self):
		opening = _make_opening()
		q1, q2 = opening.custom_screening_questions
		before = frappe.db.count("Job Applicant", {"email_id": APPLICANT_EMAIL})
		with self.assertRaises(frappe.ValidationError) as ctx:
			_submit(opening, [{"source_question": q2.name, "answer": "immediate"}])
		self.assertIn(q1.question, str(ctx.exception))
		# rows from earlier tests in this class survive (rollback is per class), so compare counts
		self.assertEqual(frappe.db.count("Job Applicant", {"email_id": APPLICANT_EMAIL}), before)

	def test_unknown_rows_are_dropped_and_optional_left_blank(self):
		opening = _make_opening()
		q1, q2 = opening.custom_screening_questions
		_submit(
			opening,
			[
				{"source_question": q1.name, "answer": "yes"},
				{"source_question": "not-a-real-row", "question": "injected", "answer": "x"},
			],
		)
		ja = _latest_applicant()
		self.assertEqual(len(ja.custom_screening_responses), 2)
		self.assertEqual({r.source_question for r in ja.custom_screening_responses}, {q1.name, q2.name})
		self.assertEqual(ja.custom_screening_responses[1].answer, "")

	def test_opening_without_questions_creates_plain_applicant(self):
		opening = _make_opening(questions=[])
		_submit(opening)
		ja = _latest_applicant()
		self.assertEqual(ja.custom_screening_responses, [])

	def test_unpublished_opening_is_rejected(self):
		opening = _make_opening(publish=0)
		with self.assertRaises(frappe.ValidationError):
			_submit(opening)

	def test_submission_without_opening_is_rejected(self):
		opening = _make_opening()
		with self.assertRaises(frappe.ValidationError):
			_submit(opening, job_title="")

	def test_job_opening_defaults_route_and_strips_blank_questions(self):
		opening = _make_opening(questions=[("Real question", 0), ("   ", 0)])
		self.assertEqual(opening.job_application_route, APPLY_ROUTE)
		self.assertEqual([q.question for q in opening.custom_screening_questions], ["Real question"])

	def test_desk_edit_by_hr_does_not_rewrite_responses(self):
		opening = _make_opening()
		q1, q2 = opening.custom_screening_questions
		_submit(opening, [{"source_question": q1.name, "answer": "a"}, {"source_question": q2.name, "answer": "b"}])
		ja = _latest_applicant()
		ja.custom_screening_responses[0].answer = "edited by HR"
		ja.save(ignore_permissions=True)
		ja.reload()
		self.assertEqual(ja.custom_screening_responses[0].answer, "edited by HR")
