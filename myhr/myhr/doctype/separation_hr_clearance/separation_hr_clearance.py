# Copyright (c) 2026, Fixxly and contributors
# For license information, please see license.txt

"""Stage 8 of the exit flow — HR clearance and the relieving letter.

Two halves on one form: the HR sign-off (exit interview, re-hire eligibility,
relieving letter) and the physical assets HR collects at the door (badge, keys,
parking tag, and any damage recovered on them).

The relieving letter is released by an explicit action rather than a field, so
there is one place that decides whether it may be issued. `can_release_letter`
answers that question and `release_relieving_letter` acts on it — deliberately
separate, so the gate can be tested without rendering a PDF (which needs
wkhtmltopdf and is not available on every machine).

Nothing here modifies the HRMS `Exit Interview` doctype. It is upstream and
read-only; this reads its status and nothing more.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate

EXIT_INTERVIEW_COMPLETED = "Completed"
SEPARATION_APPROVED = "Approved"
NOT_REHIRABLE = "No"

# Created by hand in Desk, once per site -- see docs/OFFBOARDING_TESTING_GUIDE.md.
# The record is a stub (module myHR, Custom Format ticked); the body is read off
# myhr/myhr/print_format/fixxly_relieving_letter/fixxly_relieving_letter.html at
# print time, so the letter itself stays in git.
RELIEVING_LETTER_FORMAT = "Fixxly Relieving Letter"

# Physical items HR must account for before the letter goes out.
PHYSICAL_ASSET_FIELDS = (
	("physical_id_badge_returned", "Physical ID Badge Returned"),
	("cabinet_desk_keys_returned", "Cabinet / Desk Keys Returned"),
	("parking_tag_returned", "Parking Tag / Access Returned"),
)


class SeparationHRClearance(Document):
	def onload(self):
		"""Refresh the interview status every time the form is opened.

		`validate` alone is not enough: the exit interview is usually created
		AFTER this clearance (which is raised automatically when the resignation
		is approved), so the fields stay blank until someone saves. And saving is
		blocked by the mandatory Re-hire Eligibility — leaving HR unable to see
		the interview until they answer a question they may not be ready to
		answer. Reading it on load breaks that deadlock. Nothing is persisted
		here; `validate` still writes the values on the next real save.
		"""
		self.sync_exit_interview()

	def validate(self):
		self.sync_exit_interview()
		self.validate_rehire_reason()

	def before_submit(self):
		self.validate_separation_is_approved()

	# -- exit interview -----------------------------------------------------
	def sync_exit_interview(self):
		"""Find the employee's exit interview and mirror its status.

		Derived rather than chosen: HRMS allows only one non-cancelled Exit
		Interview per employee, so there is never a question of WHICH one. A
		Link the user picks could be pointed at somebody else's completed
		interview, which would open the relieving-letter gate on a leaver who
		never sat one.
		"""
		if not self.employee:
			return

		interview = frappe.db.get_value(
			"Exit Interview",
			{"employee": self.employee, "docstatus": ["!=", 2]},
			["name", "status", "docstatus"],
			as_dict=True,
		)
		self.exit_interview = interview.name if interview else None
		self.exit_interview_status = interview.status if interview else None

	@property
	def exit_interview_is_done(self):
		"""Completed AND submitted.

		HRMS refuses to submit an interview whose status is not Completed, but
		the reverse does not hold: a draft can sit there saying Completed with
		nothing finished. Requiring docstatus 1 closes that.
		"""
		if not self.exit_interview:
			return False
		docstatus = frappe.db.get_value("Exit Interview", self.exit_interview, "docstatus")
		return self.exit_interview_status == EXIT_INTERVIEW_COMPLETED and docstatus == 1

	# -- re-hire ------------------------------------------------------------
	def validate_rehire_reason(self):
		if self.rehire_eligibility != NOT_REHIRABLE:
			return
		if not (self.rehire_ineligibility_reason or "").strip():
			frappe.throw(
				_("Re-hire Eligibility is No, so an internal reason is required."),
				title=_("Reason Required"),
				exc=frappe.MandatoryError,
			)

	# -- gating -------------------------------------------------------------
	def validate_separation_is_approved(self):
		state = frappe.db.get_value("Employee Separation", self.employee_separation, "workflow_state")
		if state == SEPARATION_APPROVED:
			return
		frappe.throw(
			_("{0} is {1}, not {2}. HR clearance cannot be finalised before the resignation is approved.").format(
				frappe.bold(self.employee_separation), frappe.bold(_(state or "Draft")),
				frappe.bold(_(SEPARATION_APPROVED)),
			),
			title=_("Separation Not Approved Yet"),
		)

	def blockers_for_letter(self):
		"""Every reason the relieving letter may not be released yet.

		Returns a list so the UI can show all of them at once instead of the
		user fixing one and discovering the next.
		"""
		blockers = []

		if not self.exit_interview_is_done:
			blockers.append(_("the exit interview must be completed and submitted"))

		if not self.rehire_eligibility:
			blockers.append(_("Re-hire Eligibility must be set"))

		if not self.last_working_day:
			blockers.append(_("the separation has no approved relieving date"))
		elif getdate(nowdate()) < getdate(self.last_working_day):
			blockers.append(
				_("the last working day ({0}) has not arrived").format(
					frappe.format(getdate(self.last_working_day), {"fieldtype": "Date"})
				)
			)

		missing = [label for fieldname, label in PHYSICAL_ASSET_FIELDS if not self.get(fieldname)]
		if missing:
			blockers.append(_("these are unanswered: {0}").format(", ".join(_(m) for m in missing)))

		return blockers

	def can_release_letter(self):
		return not self.blockers_for_letter()


@frappe.whitelist()
def release_relieving_letter(name):
	"""Generate the relieving letter PDF and stamp who released it.

	The gate is checked here, server-side. Hiding the button is a convenience;
	this is what actually stops an early or unearned release.
	"""
	doc = frappe.get_doc("Separation HR Clearance", name)
	doc.check_permission("write")

	if doc.relieving_letter:
		frappe.throw(
			_("The relieving letter was already released on {0}.").format(
				frappe.format(doc.relieving_letter_released_on, {"fieldtype": "Datetime"})
			),
			title=_("Already Released"),
		)

	_assert_print_format_exists()

	blockers = doc.blockers_for_letter()
	if blockers:
		frappe.throw(
			_("The relieving letter cannot be released yet because {0}.").format(
				"; ".join(blockers)
			),
			title=_("Not Ready For Release"),
		)

	file_url = _render_letter(doc)

	doc.db_set(
		{
			"relieving_letter": file_url,
			"relieving_letter_released_on": now_datetime(),
			"relieving_letter_released_by": frappe.session.user,
		}
	)
	return {"relieving_letter": file_url}


def _assert_print_format_exists():
	"""Refuse to release rather than quietly issue the wrong document.

	Both ways this can be wrong are silent. A missing Print Format is swallowed
	by `get_print_format_doc`, which catches DoesNotExistError and falls back to
	Standard. A record created without "Custom Format" ticked never reaches the
	file lookup at all -- printview only reads the template off disk when
	`custom_format` is set or `standard` is Yes, and a Desk-created record is
	neither by default. Either way the Standard format renders, which for this
	doctype is a dump of the form's fields, and it would be released, attached
	and emailed as somebody's relieving letter with nothing to show for it.
	"""
	fmt = frappe.db.get_value(
		"Print Format", RELIEVING_LETTER_FORMAT, ["custom_format", "standard"], as_dict=True
	)
	if fmt and (fmt.custom_format or fmt.standard == "Yes"):
		return

	problem = (
		_("does not exist on this site")
		if not fmt
		else _('exists but does not have "Custom Format" ticked, so the letter template is ignored')
	)
	frappe.throw(
		_("The print format {0} {1}, so the relieving letter cannot be generated. See the offboarding testing guide for the one-time setup.").format(
			frappe.bold(RELIEVING_LETTER_FORMAT), problem
		),
		title=_("Print Format Not Set Up"),
	)


def _letter_head_for(doc):
	"""The company's letter head, which carries the logo, CIN and registered office.

	This doctype has no letter_head field, so without being told, printing falls
	back to whichever Letter Head happens to be flagged default on the site --
	that may belong to another company entirely.
	"""
	company = frappe.db.get_value("Employee Separation", doc.employee_separation, "company")
	return frappe.db.get_value("Company", company, "default_letter_head") if company else None


def _render_letter(doc):
	"""Render the letter and save it as a private File, returning its URL.

	Split out from the gate above so the release rules can be tested without a
	working PDF toolchain: rendering needs wkhtmltopdf, which is not installed
	on every development machine.
	"""
	from frappe.utils.pdf import get_pdf

	# Named explicitly. Left to default this renders the Standard format, which
	# is a dump of this form's fields rather than a letter.
	html = frappe.get_print(
		doc.doctype,
		doc.name,
		print_format=RELIEVING_LETTER_FORMAT,
		doc=doc,
		letterhead=_letter_head_for(doc),
	)
	pdf = get_pdf(html)

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"Relieving Letter - {doc.employee_name or doc.employee}.pdf",
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
			"attached_to_field": "relieving_letter",
			"is_private": 1,
			"content": pdf,
		}
	).insert(ignore_permissions=True)
	return file_doc.file_url


@frappe.whitelist()
def get_release_status(name):
	"""What the form needs to enable or explain the Release button."""
	doc = frappe.get_doc("Separation HR Clearance", name)
	doc.check_permission("read")
	return {
		"released": bool(doc.relieving_letter),
		"relieving_letter": doc.relieving_letter,
		"can_release": doc.can_release_letter(),
		"blockers": doc.blockers_for_letter(),
	}
