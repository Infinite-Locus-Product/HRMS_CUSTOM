"""Server context for the public Job Application web form (route `/apply`).

The candidate lands on `/apply/new?job_title=<Job Opening>` from the careers
page. We look the opening up here and hand its screening questions to the
companion `.js`, which Frappe renders as a Jinja template with this context.
Nothing else about the opening is exposed. Web forms are served with
`no_cache=1`, so this runs on every page view.
"""

import frappe
from frappe import _


def get_context(context):
	context.screening_questions = []
	context.opening_ok = False
	context.opening_message = ""
	context.opening_title = ""
	context.opening_designation = ""
	context.opening_department = ""

	job_title = frappe.form_dict.get("job_title")
	if not job_title:
		context.opening_message = _("Please open this form from a job listing so we know which role you are applying for.")
		return

	opening = frappe.db.get_value(
		"Job Opening", job_title, ["name", "publish", "status", "job_title", "designation", "department"], as_dict=True
	)
	if not opening or not opening.publish or opening.status != "Open":
		context.opening_message = _("This job opening is no longer accepting applications.")
		return

	context.opening_ok = True
	context.opening_title = opening.job_title or ""
	context.opening_designation = opening.designation or ""
	context.opening_department = opening.department or ""
	context.screening_questions = frappe.get_all(
		"Job Opening Question",
		filters={"parent": opening.name, "parenttype": "Job Opening"},
		fields=["name", "question", "is_mandatory"],
		order_by="idx asc",
	)
