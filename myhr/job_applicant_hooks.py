"""Job Applicant doc_events — wired in hooks.py.

The Job Applicant custom fields (Gender, DOB, Age, photo, experience, location,
addresses) are declared in `fixtures/custom_field.json` and exposed on the
public Job Application web form. This module holds the only server-side logic
those fields need: keeping `custom_age` in sync with `custom_date_of_birth`.
"""

import frappe
from frappe.utils import getdate


WEBSITE_SOURCE = "Website Listing"  # seeded by hrms/setup.py


def validate(doc, method=None):
	compute_age(doc)
	mirror_permanent_address(doc)
	if frappe.flags.in_web_form and doc.is_new():
		# web_form.accept copies every listed field from the client payload,
		# using "" when absent — so the read-only Status field arrives blank
		# unless the browser happened to post its default. Force it here.
		doc.status = "Open"
		reconcile_screening_responses(doc)
		if not doc.get("source") and frappe.db.exists("Job Applicant Source", WEBSITE_SOURCE):
			doc.source = WEBSITE_SOURCE


def reconcile_screening_responses(doc):
	"""Rebuild `custom_screening_responses` from the opening's question list.

	Everything the public web form posts is client-controlled: hidden and
	read-only web form fields are copied verbatim by `web_form.accept`, and there
	is no server-side whitelist of child-table columns. So the submitted rows are
	treated only as `{source_question: answer}` lookups. Question text and the
	mandatory flag are always re-read from the Job Opening, unknown rows are
	dropped, and missing mandatory answers raise.

	Runs only for new docs created through a web form; HR edits in Desk are
	never touched.
	"""
	if not doc.get("job_title"):
		frappe.throw(frappe._("Please apply through a specific Job Opening."))

	opening = frappe.db.get_value(
		"Job Opening", doc.job_title, ["publish", "status"], as_dict=True
	)
	if not opening:
		frappe.throw(frappe._("Job Opening {0} does not exist.").format(doc.job_title))
	if not opening.publish or opening.status != "Open":
		frappe.throw(
			frappe._("This Job Opening is no longer accepting applications."),
			title=frappe._("Not Allowed"),
		)

	questions = frappe.get_all(
		"Job Opening Question",
		filters={"parent": doc.job_title, "parenttype": "Job Opening"},
		fields=["name", "question", "is_mandatory", "idx"],
		order_by="idx asc",
	)

	answers = {}
	for row in doc.get("custom_screening_responses") or []:
		key = (row.get("source_question") or "").strip()
		if key:
			answers[key] = (row.get("answer") or "").strip()

	doc.set("custom_screening_responses", [])
	missing = []
	for q in questions:
		answer = answers.get(q.name, "")
		if q.is_mandatory and not answer:
			missing.append(q.question)
		doc.append(
			"custom_screening_responses",
			{
				"source_question": q.name,
				"question": q.question,
				"is_mandatory": q.is_mandatory,
				"answer": answer,
			},
		)

	if missing:
		frappe.throw(
			frappe._("Please answer the following required questions:")
			+ "<br>"
			+ "<br>".join(frappe.utils.escape_html(m) for m in missing),
			title=frappe._("Missing Answers"),
		)


def mirror_permanent_address(doc):
	"""Copy Permanent Address into Current Address while the "same as" box is ticked.

	The web form marks Current Address read-only when the box is ticked, but
	read_only is a UI affordance only — the browser posts whatever the field
	holds — so the copy is re-applied here on every save, Desk included.
	"""
	if doc.get("custom_same_as_permanent_address"):
		doc.custom_current_address = doc.get("custom_permanent_address") or ""


def compute_age(doc):
	"""Set `custom_age` as '{years} Years {months} Months' from `custom_date_of_birth`.

	Same format as `myhr.employee_master_data.compute_age` so the value reads the
	same once the applicant becomes an Employee. Blank DOB or a future DOB clears
	the field instead of raising — the web form is filled by Guests and a hard
	error there is unhelpful.
	"""
	dob_val = doc.get("custom_date_of_birth")
	if not dob_val:
		doc.custom_age = ""
		return
	dob = getdate(dob_val)
	today = getdate()
	if dob > today:
		frappe.throw(frappe._("Date of Birth cannot be a future date."))
	years = today.year - dob.year
	months = today.month - dob.month
	if today.day < dob.day:
		months -= 1
	if months < 0:
		years -= 1
		months += 12
	doc.custom_age = f"{years} Years {months} Months"
