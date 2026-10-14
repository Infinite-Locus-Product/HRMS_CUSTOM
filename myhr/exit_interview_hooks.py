"""Exit Interview doc_events — wired in hooks.py.

Nothing about the HRMS doctype changes; this only pushes its status onto the
Separation HR Clearance that depends on it.

Why it exists: the clearance is raised automatically when a resignation is
approved, and the exit interview is usually created afterwards. The clearance
reads the interview in `validate`, so without this the link only appears when
somebody saves the clearance — and that save is blocked by its own mandatory
Re-hire Eligibility. HR would have to answer that question before they could
even see whether the interview had happened.
"""

import frappe

HR_CLEARANCE = "Separation HR Clearance"


def sync_to_clearance(doc, method=None):
	"""Mirror this interview onto the employee's live HR clearance.

	Written with `db_set` rather than a full save on purpose: the clearance has
	mandatory fields that are legitimately empty while HR is still working, and
	a save would fail on them. Only two derived fields are touched.
	"""
	if not doc.employee:
		return

	clearance = frappe.db.get_value(
		HR_CLEARANCE, {"employee": doc.employee, "docstatus": ["<", 2]}, "name"
	)
	if not clearance:
		return

	cancelled = doc.docstatus == 2
	frappe.db.set_value(
		HR_CLEARANCE,
		clearance,
		{
			"exit_interview": None if cancelled else doc.name,
			"exit_interview_status": None if cancelled else doc.status,
		},
		update_modified=False,
	)
