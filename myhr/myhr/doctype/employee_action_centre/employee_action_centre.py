# Copyright (c) 2026, Abhay Nain and contributors
# For license information, please see license.txt

import os

import frappe
from frappe.model.document import Document

# Source of truth for every reviewable document row on Employee Action Centre.
# Tuple shape: (prefix, label, mandatory, has_na, file_suffix)
#   prefix       — shared by file/status/remarks/(is_na) fields
#   label        — human label (used by API payload + JS guard)
#   mandatory    — gates parent "To be Reviewed" / "Accepted"
#   has_na       — whether <prefix>_is_na exists on the schema
#   file_suffix  — "_upload" for personal docs, "_doc" for employer slots/splits
AC_DOCUMENT_ROWS = [
	("aadhar", "Aadhar", True, True, "_upload"),
	("pan", "PAN", True, True, "_upload"),
	("education", "Highest Educational Qualification Certificate", True, True, "_upload"),
	("bank_statement_6m", "Bank Statement (Last 6 Months)", True, True, "_upload"),
	("form_1_wages_act", "Form 1 Payment of Wages Act", True, True, "_upload"),
	("form_2_nomination", "Form 2 Nomination", True, True, "_upload"),
	("form_f_gratuity", "Form F Payment of Gratuity", True, True, "_upload"),
	("pf_form_11_revised", "PF Form 11 Revised", True, True, "_upload"),
	("employer_1_offer_letter", "Offer Letter", True, False, "_doc"),
	("employer_1_increment_letter", "Increment Letter", False, False, "_doc"),
	("employer_1_payslip_last_month", "Pay Slip — Last Month", True, False, "_doc"),
	("employer_1_payslip_last_to_last_month", "Pay Slip — Last-to-Last Month", True, False, "_doc"),
	("employer_1_payslip_month_before_that", "Pay Slip — Month Before That", True, False, "_doc"),
	("employer_1_relieving_or_resignation", "Relieving Letter / Resignation Acceptance", True, False, "_doc"),
	("employer_2", "Employer 2", False, True, "_doc"),
	("employer_3", "Employer 3", False, True, "_doc"),
	("employer_4", "Employer 4", False, True, "_doc"),
	("employer_5", "Employer 5", False, True, "_doc"),
]

# Statutory forms — the four signed statutory forms the employee uploads in the
# PWA "Statutory & Bank" section. They are ordinary AC_DOCUMENT_ROWS entries
# (upload / N-A / HR status / remarks); this set only tells the PWA payload
# builder which rows to surface under `statutory_forms`.
AC_STATUTORY_FORM_PREFIXES = (
	"form_1_wages_act",
	"form_2_nomination",
	"form_f_gratuity",
	"pf_form_11_revised",
)

# Declaration rows — same approval pipeline (Pending / Awaiting HR / Accepted /
# Rejected + remarks), but the "data" the employee provides is a Select value
# instead of an uploaded file. Tuple shape:
#   (prefix, label, mandatory, has_na, data_field_suffix)
#   data_field_suffix — appended to prefix to get the data fieldname. Empty
#                       string means the data field IS the prefix (e.g. tax_regime).
AC_DECLARATION_ROWS = [
	("tax_regime", "Tax Regime", True, True, ""),
	("medical_insurance", "Medical Insurance", True, True, "_opt_in"),
]


# HR Settings toggles that control the 3 Most Recent Employer payslip rows.
# Each row is configurable on two axes:
#   * `show_in_pwa` — whether the PWA renders the card at all
#   * `require`    — whether (when shown) the row is mandatory or optional
# Hidden rows are forced optional. HR cannot mark a hidden row mandatory
# (the require checkbox is `read_only_depends_on` the show checkbox).
# Only these 3 payslips are configurable; everything else in AC_DOCUMENT_ROWS
# keeps the hardcoded values.
_AC_PAYSLIP_TOGGLES = {
	"employer_1_payslip_last_month": {
		"show_in_pwa": "custom_ac_show_payslip_last_month",
		"require": "custom_ac_require_payslip_last_month",
	},
	"employer_1_payslip_last_to_last_month": {
		"show_in_pwa": "custom_ac_show_payslip_last_to_last_month",
		"require": "custom_ac_require_payslip_last_to_last_month",
	},
	"employer_1_payslip_month_before_that": {
		"show_in_pwa": "custom_ac_show_payslip_month_before_that",
		"require": "custom_ac_require_payslip_month_before_that",
	},
}


def is_payslip_shown_in_pwa(prefix):
	"""Return True if the payslip row is shown in the PWA.

	For non-payslip prefixes always returns True (rows are always shown).
	For payslip prefixes, reads the HR Settings show toggle. Defaults to
	True when the column doesn't exist yet (mid-migrate guard).
	"""
	config = _AC_PAYSLIP_TOGGLES.get(prefix)
	if not config:
		return True
	val = frappe.db.get_single_value("HR Settings", config["show_in_pwa"])
	if val is None:
		return True
	return bool(val)


def get_effective_mandatory(prefix, default_mandatory):
	"""Resolve the mandatory flag for an AC document row.

	Payslip rows consult HR Settings; everything else returns the hardcoded
	default from AC_DOCUMENT_ROWS. A hidden payslip is always optional —
	the require toggle is ignored when show_in_pwa is off. Result is the
	single source of truth used by _compute_master_status,
	_validate_employer_required_fields, the API payload, and the PWA
	submitBlockers gate.
	"""
	config = _AC_PAYSLIP_TOGGLES.get(prefix)
	if not config:
		return bool(default_mandatory)
	# Hidden rows can never be mandatory.
	if not is_payslip_shown_in_pwa(prefix):
		return False
	# Defaults to the hardcoded value if the toggle column doesn't exist yet.
	val = frappe.db.get_single_value("HR Settings", config["require"])
	if val is None:
		return bool(default_mandatory)
	return bool(val)


def _row_has_data(doc, prefix, file_or_data_suffix, has_na):
	"""Uniform 'has data' check across documents and declarations.

	A document row has data when the file is uploaded OR the row is N/A.
	A declaration row has data when the Select carries any non-empty value
	OR the row is N/A. The two cases collapse to the same predicate because
	`bool("")` is False for both empty file paths and empty Select values.
	"""
	val = doc.get(f"{prefix}{file_or_data_suffix}") or ""
	is_na = bool(doc.get(f"{prefix}_is_na")) if has_na else False
	return bool(val) or is_na


# Personal-details + statutory + identity-number fields. These are pure data
# capture (no per-row HR approval), and HR sees them on Desk read-only. The
# tuple shape is (fieldname, label, mandatory). Mandatory entries are added
# to `submit_blockers` so the employee must fill them before submitting.
AC_PERSONAL_DATA_FIELDS = [
	# Personal Details bucket
	("personal_full_name", "Full Name", True),
	("personal_dob", "Date of Birth", True),
	("personal_gender", "Gender", True),
	("personal_marital_status", "Marital Status", True),
	("personal_mobile", "Mobile Number", True),
	("personal_blood_group", "Blood Group", False),
	("personal_father_name", "Father's Name", True),
	("personal_mother_name", "Mother's Name", True),
	("personal_emergency_contact_name", "Emergency Contact Name", True),
	("personal_emergency_contact_number", "Emergency Contact Number", True),
	("personal_emergency_relation", "Relation", False),
	("personal_preferred_contact_email", "Preferred Contact Email", False),
	# Family (2026-09-10 sheet) — mandatory flags TBD, all optional for now
	("personal_father_dob", "Father's DOB", False),
	("personal_mother_dob", "Mother's DOB", False),
	("personal_spouse_name", "Spouse Name", False),
	("personal_spouse_gender", "Spouse Gender", False),
	("personal_spouse_dob", "Spouse DOB", False),
	("personal_child_1_name", "Child 1 - Name", False),
	("personal_child_1_gender", "Child 1 - Gender", False),
	("personal_child_1_dob", "Child 1 - DOB", False),
	("personal_child_2_name", "Child 2 - Name", False),
	("personal_child_2_gender", "Child 2 - Gender", False),
	("personal_child_2_dob", "Child 2 - DOB", False),
	# Passport (Identity Documents tab on Desk; surfaced in Personal Details on PWA)
	("passport_number", "Passport Number", False),
	("passport_valid_upto", "Passport Valid Up To", False),
	("passport_date_of_issue", "Passport Date of Issue", False),
	("passport_place_of_issue", "Passport Place of Issue", False),
	# Identity numbers (alongside the existing aadhar/pan/education uploads)
	("aadhar_number", "Aadhar Number", True),
	("pan_number", "PAN Number", True),
	("education_name", "Degree / Qualification Name", True),
	# Statutory & Bank bucket
	("statutory_pf_number", "PF Number", False),
	("statutory_uan_number", "UAN Number", False),
	("bank_account_holder_name", "Name as per Bank Records", False),
	("bank_name", "Bank Name", True),
	("bank_account_number", "Bank Account Number", True),
	("bank_ifsc_code", "IFSC Code", True),
]


# Server-side format validators. None = skip pattern check. Each value is a
# tuple (regex_pattern, description) — the description is used in the error
# message when the pattern fails.
AC_FIELD_FORMAT_VALIDATORS = {
	"personal_mobile": (r"^\d{10}$", "10 digits, digits only"),
	"personal_emergency_contact_number": (r"^\d{10}$", "10 digits, digits only"),
	"aadhar_number": (r"^\d{12}$", "12 digits, digits only"),
	"pan_number": (r"^[A-Z]{5}\d{4}[A-Z]$", "10 characters in PAN format ABCDE1234F"),
	"statutory_uan_number": (r"^\d{12}$", "12 digits, digits only"),
}

# Document file extension allow-list (closes EAC-6). HR documents are
# documents — `.exe / .html / .js` should never get attached.
_ALLOWED_FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".jpg", ".jpeg", ".png"}

# Status flips that warrant a Notification Log entry to the employee.
_VERDICT_STATUSES_TO_NOTIFY = {"Rejected"}  # individual rejection per row


def log_activity(doc, action, details=""):
	"""Append an Action Centre Activity row to the parent's audit log.

	The caller is responsible for ensuring a downstream save() persists the row.

	`posted_on` has `default: "Now"` in the child doctype JSON, but Frappe only
	evaluates that default during `db_insert` of a brand-new doc — child rows
	appended to an already-saved parent are inserted via
	`save_new_table_rows()` which sets `creation`/`modified` on the row but
	does not re-apply schema defaults. Set the timestamp explicitly so the
	desk activity-log grid renders a "Posted On" value.
	"""
	doc.append("activity_logs", {
		"posted_on": frappe.utils.now_datetime(),
		"user": frappe.session.user,
		"action": action,
		"details": (details or "")[:1000],
	})


class EmployeeActionCentre(Document):
	def validate(self):
		self._sync_employee_name()
		self._guard_inactive_employee_immutable()
		self._guard_submission_audit_fields()
		self._guard_locked_rows_immutable_for_employee()
		self._enforce_data_invariants()
		self._validate_employer_dates()
		self._validate_employer_no_overlap()
		self._validate_employer_required_fields()
		self._validate_uploaded_file_extensions()
		self._validate_personal_data_formats()
		self._compute_personal_age()
		self._sweep_ghost_statuses()
		self._guard_accepted_rows_have_data()
		self._stamp_submission_audit_fields()
		self._emit_audit_log()
		self.status = self._compute_master_status()
		self._notify_hr_on_completion()
		self._notify_employee_on_verdict_changes()

	# ----- Personal data ------------------------------------------------------

	def _validate_personal_data_formats(self):
		"""Enforce the format rules from AC_FIELD_FORMAT_VALIDATORS on
		personal/statutory text fields. Empty values pass — mandatory-fill
		gating happens via the submit blocker check, not here.
		"""
		import re
		for fieldname, (pattern, desc) in AC_FIELD_FORMAT_VALIDATORS.items():
			val = (self.get(fieldname) or "").strip()
			if not val:
				continue
			# Coerce PAN to upper-case before checking — common employee
			# convenience, also matches how PAN is canonically stored.
			if fieldname == "pan_number":
				val_norm = val.upper()
				if val_norm != val:
					self.set(fieldname, val_norm)
					val = val_norm
			if not re.match(pattern, val):
				label = next(
					(lbl for fn, lbl, _m in AC_PERSONAL_DATA_FIELDS if fn == fieldname),
					fieldname,
				)
				frappe.throw(
					f"<b>{label}</b> must be {desc}.",
					title="Invalid format",
				)

	def _compute_personal_age(self):
		"""Auto-populate `personal_age` from `personal_dob` (Y/M format).

		Mirrors `myhr.employee_master_data.compute_age` so the AC form shows
		the same string the Employee form does. Future enhancement noted in
		the doc-level TODO: when HR Accepts the row, sync personal_dob /
		personal_blood_group / etc. back to the Employee record.
		"""
		from frappe.utils import getdate
		dob_val = self.get("personal_dob")
		if not dob_val:
			self.set("personal_age", "")
			return
		dob = getdate(dob_val)
		today = getdate()
		years = today.year - dob.year
		months = today.month - dob.month
		if today.day < dob.day:
			months -= 1
		if months < 0:
			years -= 1
			months += 12
		if years < 0:
			self.set("personal_age", "")
			return
		self.set("personal_age", f"{years} Years {months} Months")

	# ----- Mutation guards ----------------------------------------------------

	def _guard_inactive_employee_immutable(self):
		"""Closes EAC-13: an Employee on Left/Inactive/Suspended status should
		not have their AC mutated except by HR (e.g., to retire it). Without
		this, a stale Vue session or bench script could keep modifying.
		"""
		if not self.employee:
			return
		old = self.get_doc_before_save()
		if not old:
			return  # creation path — covered by _ensure_action_centre's flow
		emp_status = frappe.db.get_value("Employee", self.employee, "status")
		if emp_status in (None, "Active"):
			return
		roles = set(frappe.get_roles())
		if {"HR Manager", "System Manager"} & roles:
			return
		frappe.throw(
			f"Employee <b>{self.employee}</b> is currently <b>{emp_status}</b>. "
			"Their Action Centre cannot be modified. Contact HR.",
			title="Employee not Active",
		)

	def _guard_submission_audit_fields(self):
		"""Closes EAC-2 / EAC-3 / EAC-4: lock the submission audit fields once
		set so HR cannot backdate submission or quietly un-submit.

		- `submitted_for_review` 1 → 0 throws (only HR Manager can un-submit
		  via the explicit `unsubmit_action_centre` API path, which sets
		  `frappe.flags.allow_unsubmit_ac` to bypass this guard).
		- `submitted_on` and `submitted_by`, once set, become immutable.
		"""
		old = self.get_doc_before_save()
		if not old:
			return  # insert path — stamping happens in _stamp_submission_audit_fields

		old_submitted = bool(old.get("submitted_for_review"))
		new_submitted = bool(self.submitted_for_review)
		if old_submitted and not new_submitted:
			if not getattr(frappe.flags, "allow_unsubmit_ac", False):
				frappe.throw(
					"Once an Action Centre is submitted for review, it cannot be un-submitted. "
					"HR Manager may use the explicit Reopen action if a re-submission is needed.",
					title="Submission is locked",
				)

		# Normalize datetimes to second precision before comparing. The DB
		# stores microseconds (DATETIME(6)); the desk form re-posts the
		# value as a no-microsecond string ("YYYY-MM-DD HH:MM:SS"). A raw
		# `!=` misfires on every HR save of an already-submitted AC.
		old_on = old.get("submitted_on")
		new_on = self.submitted_on
		if old_on and not getattr(frappe.flags, "allow_unsubmit_ac", False):
			old_on_norm = frappe.utils.get_datetime(old_on).replace(microsecond=0)
			new_on_norm = (
				frappe.utils.get_datetime(new_on).replace(microsecond=0)
				if new_on else None
			)
			if old_on_norm != new_on_norm:
				frappe.throw(
					"`Submitted On` is the audit timestamp and cannot be modified after submission.",
					title="Audit field locked",
				)

		old_by = old.get("submitted_by")
		new_by = self.submitted_by
		if old_by and old_by != new_by and not getattr(frappe.flags, "allow_unsubmit_ac", False):
			frappe.throw(
				"`Submitted By` records who submitted the Action Centre and cannot be modified.",
				title="Audit field locked",
			)

	def _stamp_submission_audit_fields(self):
		"""Server-side stamp `submitted_on` / `submitted_by` on the
		not-submitted → submitted transition. Closes EAC-3 / EAC-4 alongside
		_guard_submission_audit_fields above. Idempotent: re-stamping is a no-op."""
		old = self.get_doc_before_save()
		old_submitted = bool(old.get("submitted_for_review")) if old else False
		new_submitted = bool(self.submitted_for_review)
		if not old_submitted and new_submitted:
			# Server-stamp regardless of what the client sent.
			self.submitted_on = frappe.utils.now_datetime()
			self.submitted_by = frappe.session.user

	# ----- Data invariants ----------------------------------------------------

	def _validate_employer_dates(self):
		"""Closes EAC-7: employer date order. `from_date > till_date` is
		nonsensical. We accept equal dates (single-day stints) and either side
		being null."""
		for slot in (1, 2, 3, 4, 5):
			f = self.get(f"employer_{slot}_from")
			t = self.get(f"employer_{slot}_till")
			if f and t and frappe.utils.getdate(f) > frappe.utils.getdate(t):
				frappe.throw(
					f"Employer {slot}: <b>From</b> date ({f}) cannot be after <b>Till</b> date ({t}).",
					title="Invalid employer date range",
				)

	def _validate_employer_no_overlap(self):
		"""Reject submissions where two employer stints have overlapping
		[from, till] windows. Two full-time roles on the same calendar day is
		a data error — usually a typo'd date that the employee should fix
		before HR review.

		**Only fires on the submit-for-review transition** (matching
		`_validate_employer_required_fields`). During draft saves we let
		half-typed ranges through so users can edit slot 2 without the slot
		1 dates briefly colliding mid-edit. The PWA mirrors this rule in
		`submitBlockers` so the Submit button is disabled before the user
		even taps it.

		N/A slots are excluded — they're semantically empty.
		"""
		old = self.get_doc_before_save()
		old_submitted = bool(old.get("submitted_for_review")) if old else False
		new_submitted = bool(self.submitted_for_review)
		if old_submitted or not new_submitted:
			return

		slot_labels = {
			1: "Most Recent Employer",
			2: "Previous Employer 1",
			3: "Previous Employer 2",
			4: "Previous Employer 3",
			5: "Previous Employer 4",
		}
		ranges = []
		for slot in (1, 2, 3, 4, 5):
			if self.get(f"employer_{slot}_is_na"):
				continue
			f = self.get(f"employer_{slot}_from")
			t = self.get(f"employer_{slot}_till")
			if not (f and t):
				continue
			fd = frappe.utils.getdate(f)
			td = frappe.utils.getdate(t)
			if fd > td:
				continue  # _validate_employer_dates already throws on this
			ranges.append((slot, fd, td))

		conflicts = []
		for i in range(len(ranges)):
			for j in range(i + 1, len(ranges)):
				slot_a, fa, ta = ranges[i]
				slot_b, fb, tb = ranges[j]
				# Inclusive overlap: [fa, ta] ∩ [fb, tb] ≠ ∅
				if fa <= tb and fb <= ta:
					conflicts.append(
						f"<b>{slot_labels[slot_a]}</b> ({fa} → {ta}) "
						f"and <b>{slot_labels[slot_b]}</b> ({fb} → {tb})"
					)

		if conflicts:
			frappe.throw(
				"Previous employer tenure details overlapping. Please check, "
				"correct and update and then Submit.<br><br>"
				+ "<br>".join(conflicts),
				title="Overlapping employer tenures",
			)

	def _validate_employer_required_fields(self):
		"""If a slot has *any* started data — file uploaded, name typed, dates
		set — the user has committed to that employer, so Employer Name + From +
		Till must all be present. Empty slots and slots toggled N/A are skipped
		(N/A wipes the data fields in `_enforce_data_invariants` first, so by
		the time we get here an N/A slot looks empty).

		**Only fires on the submit-for-review transition.** During draft saves
		(field-by-field updates while the user is still uploading docs) we
		intentionally let partial state through — otherwise a single file
		upload before the dates are set would throw and break the upload flow.
		The client-side `canSubmitForReview` gate keeps the user from clicking
		Submit while the form is incomplete; this server check is defence-in-
		depth on the actual submission write.
		"""
		old = self.get_doc_before_save()
		old_submitted = bool(old.get("submitted_for_review")) if old else False
		new_submitted = bool(self.submitted_for_review)
		# Skip on draft saves and on edits to already-submitted docs (those have
		# their own locked-row guard). Only the False -> True transition gates.
		if old_submitted or not new_submitted:
			return

		# Display labels for the slots in error messages.
		slot_labels = {
			1: "Most Recent Employer",
			2: "Previous Employer 1",
			3: "Previous Employer 2",
			4: "Previous Employer 3",
			5: "Previous Employer 4",
		}
		# Document file fields keyed by slot. Employer 1 has split docs; 2-5
		# share a single relieving-letter file at `<prefix>_doc`.
		slot_file_fields = {1: [], 2: [], 3: [], 4: [], 5: []}
		for prefix, _label, _mand, _has_na, file_suffix in AC_DOCUMENT_ROWS:
			for slot in (1, 2, 3, 4, 5):
				slot_key = f"employer_{slot}"
				if prefix == slot_key or prefix.startswith(f"{slot_key}_"):
					slot_file_fields[slot].append(f"{prefix}{file_suffix}")
					break

		for slot in (1, 2, 3, 4, 5):
			# Every slot now exposes an N/A toggle (slot 1 added so freshers
			# can mark "no prior employer"). When set, the row is semantically
			# empty (data was wiped by _enforce_data_invariants).
			if self.get(f"employer_{slot}_is_na"):
				continue

			name = (self.get(f"employer_{slot}_name") or "").strip()
			f = self.get(f"employer_{slot}_from")
			t = self.get(f"employer_{slot}_till")
			any_file = any(bool(self.get(field)) for field in slot_file_fields[slot])

			if not (name or f or t or any_file):
				continue  # genuinely empty slot — nothing to enforce

			missing = []
			if not name:
				missing.append("<b>Employer Name</b>")
			if not f:
				missing.append("<b>From</b>")
			if not t:
				missing.append("<b>Till</b>")
			if missing:
				frappe.throw(
					f"{slot_labels[slot]}: {', '.join(missing)} cannot be left blank "
					f"once you've started filling this slot. Either complete the "
					f"details or clear them"
					+ (" / mark <b>Not Applicable</b>" if slot >= 2 else "")
					+ ".",
					title="Incomplete employer details",
				)

	def _validate_uploaded_file_extensions(self):
		"""Closes EAC-6: allow-list document extensions on every uploaded file."""
		allowed = ", ".join(sorted(_ALLOWED_FILE_EXTENSIONS))
		for prefix, label, _mand, _has_na, file_suffix in AC_DOCUMENT_ROWS:
			path = (self.get(f"{prefix}{file_suffix}") or "").split("?")[0]
			if not path:
				continue
			ext = os.path.splitext(path)[1].lower()
			if ext and ext not in _ALLOWED_FILE_EXTENSIONS:
				frappe.throw(
					f'<b>{label}</b>: file type {ext} is not allowed. Allowed: {allowed}.',
					title="Disallowed file type",
				)

	def _enforce_data_invariants(self):
		"""N/A wins on conflict — clears the row's data fields in the same save.

		For mandatory personal docs (aadhar/pan/education/bank statement): just clears the file.
		For declarations (tax regime, medical insurance): clears the Select value(s).
		For employer slots 2-5: also clears name/from/till — toggling N/A means
		"this employer doesn't exist", so leaving stale name+dates is misleading.
		For Most Recent Employer (slot 1): N/A wipes name/from/till AND every
		sub-document file (Offer Letter, 3 Pay Slips, Increment, Relieving) —
		the whole block is "no prior employer" when the parent flag is set.
		"""
		for prefix, _label, _mand, has_na, file_suffix in AC_DOCUMENT_ROWS:
			if not (has_na and self.get(f"{prefix}_is_na")):
				continue
			self.set(f"{prefix}{file_suffix}", "")
			if prefix in ("employer_2", "employer_3", "employer_4", "employer_5"):
				self.set(f"{prefix}_name", "")
				self.set(f"{prefix}_from", None)
				self.set(f"{prefix}_till", None)

		# Declaration N/A wipes the data field. For medical insurance also clears
		# the linked policy (HR-set) and the employee's signed opt-out upload —
		# all three pieces are tied to a non-N/A row.
		for prefix, _label, _mand, has_na, data_suffix in AC_DECLARATION_ROWS:
			if not (has_na and self.get(f"{prefix}_is_na")):
				continue
			self.set(f"{prefix}{data_suffix}", "")
			if prefix == "medical_insurance":
				self.set("medical_insurance_policy", "")
				self.set("medical_insurance_signed_optout", "")

		# Switching from "Opt Out" -> "Opt In" should clear the signed opt-out
		# upload (it's only meaningful when opting out). Mirror the same drop
		# for the opposite switch on the linked policy. Idempotent: clearing
		# already-empty fields is a no-op.
		if (self.get("medical_insurance_opt_in") or "") == "Opt In":
			if self.get("medical_insurance_signed_optout"):
				self.set("medical_insurance_signed_optout", "")
		elif (self.get("medical_insurance_opt_in") or "") == "Opt Out":
			if self.get("medical_insurance_policy"):
				self.set("medical_insurance_policy", "")
		# Most Recent Employer (slot 1) — parent-level N/A propagates to every
		# sub-doc file. Sub-doc rows don't have their own is_na column; the
		# parent flag is the single source of "this employer doesn't exist".
		# Logically, if there's no most-recent employer there can't be any
		# previous employers either, so slots 2-5 get wiped too AND auto-marked
		# N/A — without flipping `employer_X_is_na`, the per-row status sweep
		# leaves them as "Pending" and the Action Centre badge keeps counting
		# them as outstanding tasks even though the user has nothing to do.
		old = self.get_doc_before_save()
		if self.get("employer_1_is_na"):
			self.set("employer_1_name", "")
			self.set("employer_1_from", None)
			self.set("employer_1_till", None)
			for prefix, _label, _mand, _has_na, file_suffix in AC_DOCUMENT_ROWS:
				if prefix.startswith("employer_1_"):
					self.set(f"{prefix}{file_suffix}", "")
			# No prior employer => no previous employers. Wipe slots 2-5.
			for slot in (2, 3, 4, 5):
				self.set(f"employer_{slot}_name", "")
				self.set(f"employer_{slot}_from", None)
				self.set(f"employer_{slot}_till", None)
				self.set(f"employer_{slot}_doc", "")
				self.set(f"employer_{slot}_is_na", 1)
		elif old and old.get("employer_1_is_na"):
			# employer_1_is_na flipped 1 → 0 in this save: clear the auto-N/A
			# propagation on slots 2-5 so the user can fill them from a clean
			# state (data was already wiped by the prior fresher save).
			for slot in (2, 3, 4, 5):
				self.set(f"employer_{slot}_is_na", 0)

	def _row_inherits_parent_na(self, prefix):
		"""True if this row's status should be treated as auto-Accepted because
		its parent slot is marked N/A.

		- Most Recent Employer's split sub-docs (employer_1_*) inherit from
		  `employer_1_is_na`.
		- Previous Employer slots (employer_2..5) also inherit from
		  `employer_1_is_na`: a fresher with no most-recent employer logically
		  has no previous employers either, so the propagated N/A on those
		  slots is a derived verdict (not a separate HR claim) and shouldn't
		  require a per-slot HR Accept to clear master status."""
		if prefix.startswith("employer_1_") and bool(self.get("employer_1_is_na")):
			return True
		if prefix in ("employer_2", "employer_3", "employer_4", "employer_5") and bool(
			self.get("employer_1_is_na")
		):
			return True
		return False

	def _guard_locked_rows_immutable_for_employee(self):
		"""The employee role cannot mutate rows that are locked.

		A row is locked when:
		  - HR has marked it Accepted (verified — only HR can revise), OR
		  - The AC has been submitted AND the row is not currently Rejected
		    (everything else is in HR's queue; only rejected rows are still
		    actionable by the employee).

		HR Manager / System Manager are exempt.
		"""
		old = self.get_doc_before_save()
		if not old:
			return  # new document

		roles = set(frappe.get_roles())
		if {"HR Manager", "System Manager"} & roles:
			return

		is_submitted = bool(old.get("submitted_for_review"))

		for prefix, label, _mand, has_na, file_suffix in AC_DOCUMENT_ROWS:
			old_status = old.get(f"{prefix}_approval_status") or "Pending"
			if old_status == "Accepted":
				lock_reason = "verified by HR"
			elif is_submitted and old_status != "Rejected":
				lock_reason = "submitted for HR review"
			else:
				continue

			watched = [f"{prefix}{file_suffix}", f"{prefix}_remarks"]
			if has_na:
				watched.append(f"{prefix}_is_na")
			if prefix in ("employer_2", "employer_3", "employer_4", "employer_5"):
				watched.extend([f"{prefix}_name", f"{prefix}_from", f"{prefix}_till"])
			for field in watched:
				if (old.get(field) or "") != (self.get(field) or ""):
					frappe.throw(
						f'<b>{label}</b> has been {lock_reason} and cannot be modified. '
						f'Contact HR if a correction is needed.'
					)

		# Declarations follow the same lock rule. Watched: data field + remarks
		# + is_na. medical_insurance_policy is permlevel=1 (HR-only) so doesn't
		# need a row-lock guard here — the perm system already blocks employees.
		for prefix, label, _mand, has_na, data_suffix in AC_DECLARATION_ROWS:
			old_status = old.get(f"{prefix}_approval_status") or "Pending"
			if old_status == "Accepted":
				lock_reason = "verified by HR"
			elif is_submitted and old_status != "Rejected":
				lock_reason = "submitted for HR review"
			else:
				continue

			watched = [f"{prefix}{data_suffix}", f"{prefix}_remarks"]
			if has_na:
				watched.append(f"{prefix}_is_na")
			# Medical insurance has an additional employee-uploaded signed
			# declaration. Once the row is locked, that file is immutable too.
			if prefix == "medical_insurance":
				watched.append("medical_insurance_signed_optout")
			for field in watched:
				if (old.get(field) or "") != (self.get(field) or ""):
					frappe.throw(
						f'<b>{label}</b> has been {lock_reason} and cannot be modified. '
						f'Contact HR if a correction is needed.'
					)
		# Most Recent Employer parent-level fields (name/from/till + N/A flag).
		# AC_DOCUMENT_ROWS only iterates over sub-docs, so the parent fields
		# need their own lock check once the AC has been submitted.
		if is_submitted:
			parent_watched = (
				"employer_1_name", "employer_1_from", "employer_1_till", "employer_1_is_na",
			)
			for field in parent_watched:
				if (old.get(field) or "") != (self.get(field) or ""):
					frappe.throw(
						"<b>Most Recent Employer</b> details have been submitted for HR review and cannot be modified. "
						"Contact HR if a correction is needed."
					)

	def _guard_accepted_rows_have_data(self):
		"""Server-side mirror of the desk client's empty-Accepted guard.

		HR cannot mark a row Accepted with no file uploaded and N/A unchecked.
		Rows whose parent slot is N/A (employer_1 sub-docs under a parent N/A)
		are auto-handled in master-status compute and shouldn't be touched at
		the row level — skip those.
		"""
		for prefix, label, _mand, has_na, file_suffix in AC_DOCUMENT_ROWS:
			if (self.get(f"{prefix}_approval_status") or "Pending") != "Accepted":
				continue
			if self._row_inherits_parent_na(prefix):
				continue
			file_val = self.get(f"{prefix}{file_suffix}") or ""
			is_na = bool(self.get(f"{prefix}_is_na")) if has_na else False
			if not file_val and not is_na:
				frappe.throw(
					f'Cannot mark "<b>{label}</b>" as Accepted — no document uploaded and "Not Applicable" is not checked.'
				)

		# Same guard for declarations: HR cannot Accept a declaration with no
		# value picked AND N/A unchecked.
		for prefix, label, _mand, has_na, data_suffix in AC_DECLARATION_ROWS:
			if (self.get(f"{prefix}_approval_status") or "Pending") != "Accepted":
				continue
			val = self.get(f"{prefix}{data_suffix}") or ""
			is_na = bool(self.get(f"{prefix}_is_na")) if has_na else False
			if not val and not is_na:
				frappe.throw(
					f'Cannot mark "<b>{label}</b>" as Accepted — employee has not declared a value and "Not Applicable" is not checked.'
				)

	def _row_state(self, prefix, has_na, file_suffix):
		"""Return (file_value, is_na, hr_status) for a row, with empty values normalised."""
		return (
			self.get(f"{prefix}{file_suffix}") or "",
			bool(self.get(f"{prefix}_is_na")) if has_na else False,
			self.get(f"{prefix}_approval_status") or "Pending",
		)

	def _sweep_ghost_statuses(self):
		"""Reconcile per-row status with the row's data.

		Only Pending↔Awaiting-HR transitions are auto-flipped. HR's terminal
		verdicts (Accepted / Rejected) are never overwritten here.
		"""
		for prefix, _label, _mandatory, has_na, file_suffix in AC_DOCUMENT_ROWS:
			file_val, is_na, status = self._row_state(prefix, has_na, file_suffix)
			has_data = bool(file_val) or is_na
			if has_data and status == "Pending":
				self.set(f"{prefix}_approval_status", "Awaiting HR")
			elif not has_data and status == "Awaiting HR":
				self.set(f"{prefix}_approval_status", "Pending")

		# Same Pending↔Awaiting HR sweep for declarations (Select-based rows).
		for prefix, _label, _mandatory, has_na, data_suffix in AC_DECLARATION_ROWS:
			val = self.get(f"{prefix}{data_suffix}") or ""
			is_na = bool(self.get(f"{prefix}_is_na")) if has_na else False
			status = self.get(f"{prefix}_approval_status") or "Pending"
			has_data = bool(val) or is_na
			if has_data and status == "Pending":
				self.set(f"{prefix}_approval_status", "Awaiting HR")
			elif not has_data and status == "Awaiting HR":
				self.set(f"{prefix}_approval_status", "Pending")

	def _sync_employee_name(self):
		if not self.employee:
			self.employee_name = ""
			return
		self.employee_name = (
			frappe.db.get_value("Employee", self.employee, "employee_name")
			or self.employee_name
		)

	# ----- Audit log ----------------------------------------------------------

	def _emit_audit_log(self):
		"""Compare against the last saved version and append activity_logs rows.

		Catches every writer — API endpoints, HR desk edits, server scripts —
		because validate() runs on every save path. Closes EAC-8 by also
		capturing remark-only HR edits (HR adding a note without flipping
		status).
		"""
		old = self.get_doc_before_save()
		if not old:
			return  # first save; skip noise

		for prefix, _label, _mand, has_na, file_suffix in AC_DOCUMENT_ROWS:
			old_file = (old.get(f"{prefix}{file_suffix}") or "") if old else ""
			new_file = self.get(f"{prefix}{file_suffix}") or ""
			if old_file != new_file:
				if new_file:
					action = "Document Reuploaded" if old_file else "Document Uploaded"
					log_activity(self, action, prefix)
				else:
					log_activity(self, "Document Cleared", prefix)

			if has_na:
				old_na = bool(old.get(f"{prefix}_is_na")) if old else False
				new_na = bool(self.get(f"{prefix}_is_na"))
				if old_na != new_na:
					log_activity(self, "Field Updated", f"{prefix}: N/A {'on' if new_na else 'off'}")

			old_st = (old.get(f"{prefix}_approval_status") or "Pending") if old else "Pending"
			new_st = self.get(f"{prefix}_approval_status") or "Pending"
			if old_st != new_st and new_st in ("Accepted", "Rejected"):
				details = f"{prefix}: {new_st}"
				remarks = self.get(f"{prefix}_remarks") or ""
				if new_st == "Rejected" and remarks:
					details += f" — {remarks}"
				log_activity(self, "HR Status Updated", details)

			# EAC-8: capture remark-only changes (no status flip). HR can leave
			# a note on a Pending or Awaiting HR row without acting; that note
			# matters for audit even though the verdict didn't change.
			old_rem = (old.get(f"{prefix}_remarks") or "") if old else ""
			new_rem = self.get(f"{prefix}_remarks") or ""
			if old_rem != new_rem and old_st == new_st:
				log_activity(
					self, "Remark Updated",
					f"{prefix}: {(new_rem or '(cleared)')[:200]}",
				)

		# Declarations — same audit pattern (data change / status flip / remark).
		for prefix, _label, _mand, has_na, data_suffix in AC_DECLARATION_ROWS:
			data_field = f"{prefix}{data_suffix}"
			old_val = (old.get(data_field) or "") if old else ""
			new_val = self.get(data_field) or ""
			if old_val != new_val:
				if new_val:
					action = "Declaration Updated" if old_val else "Declaration Made"
					log_activity(self, action, f"{prefix}: {new_val}")
				else:
					log_activity(self, "Declaration Cleared", prefix)

			if has_na:
				old_na = bool(old.get(f"{prefix}_is_na")) if old else False
				new_na = bool(self.get(f"{prefix}_is_na"))
				if old_na != new_na:
					log_activity(self, "Field Updated", f"{prefix}: N/A {'on' if new_na else 'off'}")

			old_st = (old.get(f"{prefix}_approval_status") or "Pending") if old else "Pending"
			new_st = self.get(f"{prefix}_approval_status") or "Pending"
			if old_st != new_st and new_st in ("Accepted", "Rejected"):
				details = f"{prefix}: {new_st}"
				remarks = self.get(f"{prefix}_remarks") or ""
				if new_st == "Rejected" and remarks:
					details += f" — {remarks}"
				log_activity(self, "HR Status Updated", details)

			old_rem = (old.get(f"{prefix}_remarks") or "") if old else ""
			new_rem = self.get(f"{prefix}_remarks") or ""
			if old_rem != new_rem and old_st == new_st:
				log_activity(
					self, "Remark Updated",
					f"{prefix}: {(new_rem or '(cleared)')[:200]}",
				)

		# Personal / statutory / identity-number fields — single-line audit per
		# changed value. Same "Field Updated" action used elsewhere for plain
		# field edits.
		for fieldname, label, _mand in AC_PERSONAL_DATA_FIELDS:
			old_val = (old.get(fieldname) or "") if old else ""
			new_val = self.get(fieldname) or ""
			if str(old_val).strip() != str(new_val).strip():
				preview = (str(new_val) or "(cleared)")[:120]
				log_activity(self, "Field Updated", f"{fieldname}: {preview}")

		if not bool(old.get("submitted_for_review")) and bool(self.submitted_for_review):
			log_activity(self, "Submitted for Review", f"by {frappe.session.user}")

	# ----- Notifications ------------------------------------------------------

	def _notify_hr_on_completion(self):
		"""Send an in-app notification to HR Managers when employee submits the AC.

		Trigger: master status flipped *into* 'To be Reviewed' on this save (which
		only happens when the employee taps Submit on a fully-filled AC).
		"""
		old = self.get_doc_before_save()
		old_status = (old.get("status") if old else "Pending") or "Pending"
		if not (self.status == "To be Reviewed" and old_status != "To be Reviewed"):
			return

		hr_users = {
			r.parent
			for r in frappe.get_all(
				"Has Role",
				filters={
					"role": ["in", ["HR Manager", "System Manager"]],
					"parenttype": "User",
				},
				fields=["parent"],
			)
			if r.parent not in ("Administrator", "Guest")
		}
		for user in hr_users:
			if not frappe.db.exists("User", user):
				continue
			frappe.get_doc({
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"subject": f"[myHR Action Centre] {self.employee_name or self.employee} completed Action Centre",
				"email_content": f"{self.employee_name or self.employee} has submitted all documents and acknowledged all policies. Ready for HR review.",
				"document_type": "Employee Action Centre",
				"document_name": self.name,
				"from_user": "Administrator",
			}).insert(ignore_permissions=True)

	def _notify_employee_on_verdict_changes(self):
		"""Closes EAC-9 / EAC-10: ping the employee when HR rejects a row, or
		when the master status flips into Accepted (the milestone the
		employee actually cares about). Best-effort — exceptions never raise."""
		try:
			old = self.get_doc_before_save()
			if not old:
				return
			emp_user = frappe.db.get_value("Employee", self.employee, "user_id")
			if not emp_user:
				return

			# 1. Per-row Rejected transitions (documents + declarations)
			for prefix, label, _mand, _has_na, _file_suffix in AC_DOCUMENT_ROWS + tuple(AC_DECLARATION_ROWS):
				old_st = old.get(f"{prefix}_approval_status") or "Pending"
				new_st = self.get(f"{prefix}_approval_status") or "Pending"
				if old_st != "Rejected" and new_st == "Rejected":
					remark = (self.get(f"{prefix}_remarks") or "").strip()
					body = (
						f"<p>HR has rejected your <b>{label}</b> in the Action Centre.</p>"
						+ (f"<p><b>Reason:</b> {remark}</p>" if remark else "")
						+ "<p>Open the Action Centre in the myHR PWA to re-upload.</p>"
					)
					frappe.get_doc({
						"doctype": "Notification Log",
						"for_user": emp_user,
						"type": "Alert",
						"subject": f"[myHR Action Centre] {label} rejected — re-upload required",
						"email_content": body,
						"document_type": "Employee Action Centre",
						"document_name": self.name,
						"from_user": "Administrator",
					}).insert(ignore_permissions=True)

			# 2. Master status flipped into Accepted
			old_master = (old.get("status") if old else "Pending") or "Pending"
			if self.status == "Accepted" and old_master != "Accepted":
				frappe.get_doc({
					"doctype": "Notification Log",
					"for_user": emp_user,
					"type": "Alert",
					"subject": "[myHR Action Centre] All documents accepted — onboarding complete",
					"email_content": (
						"<p>HR has reviewed and accepted every document in your Action Centre. "
						"Your onboarding paperwork is complete.</p>"
					),
					"document_type": "Employee Action Centre",
					"document_name": self.name,
					"from_user": "Administrator",
				}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(
				title="myHR _notify_employee_on_verdict_changes failed",
				message=frappe.get_traceback(),
			)

	# ----- on_trash (EAC-5) ---------------------------------------------------

	def on_trash(self):
		"""Refuse deletion unless the linked Employee is also being trashed
		(set `frappe.flags.deleting_employee` from the Employee on_trash hook)
		or an explicit override is active. Closes EAC-5: ACs hold compliance
		audit history and shouldn't be deletable on a whim."""
		if getattr(frappe.flags, "deleting_employee", False):
			return
		if getattr(frappe.flags, "allow_eac_delete", False):
			return
		# System Manager / HR Manager could otherwise wipe an AC outright.
		# Force them through the explicit override flag.
		frappe.throw(
			"Employee Action Centre rows hold compliance audit history and cannot be deleted. "
			"To retire an AC, deactivate the linked Employee instead. (System overrides "
			"may set <code>frappe.flags.allow_eac_delete=1</code> for one-shot maintenance.)",
			title="Cannot delete Action Centre",
		)

	# ----- Master status ------------------------------------------------------

	def _compute_master_status(self):
		"""Single source of truth for the parent status field.

		Rules (evaluated top-down, first match wins):
		  Action Required  — any row is Rejected (regardless of submitted state — HR can pre-reject before submit)
		  Accepted         — submitted AND every mandatory row Accepted AND every uploaded optional row Accepted
		  To be Reviewed   — submitted AND every mandatory row has file/N-A AND ≥1 Awaiting HR
		  Ready to Submit  — every mandatory row has file/N-A but employee hasn't submitted yet
		  In Progress      — any row touched but mandatory not all complete
		  Pending          — nothing touched

		`Accepted` is gated on `submitted_for_review=1`. Without this gate, HR could
		pre-Accept all rows before the employee tapped Submit, jumping master state to
		`Accepted` while `submitted_*` fields stayed empty — a contradiction. With the
		gate, pre-Accept by HR keeps the master at `Ready to Submit` until the employee
		formally submits, then the next save cleanly returns `Accepted`.
		"""
		any_data = False
		any_rejected = False
		any_awaiting = False
		all_mandatory_done = True
		all_mandatory_accepted = True
		any_optional_pending_review = False

		# Identify employer slots where the employee has started entering details
		# (any of name / from / till). For Previous Employers (2-5) this promotes
		# the relieving doc from optional to required — dropping "Optional" wording
		# from the UI alone isn't enough; the master state machine has to enforce it.
		started_employer_slots = set()
		for slot in (1, 2, 3, 4, 5):
			prefix = f"employer_{slot}"
			if (
				(self.get(f"{prefix}_name") or "").strip()
				or self.get(f"{prefix}_from")
				or self.get(f"{prefix}_till")
			):
				started_employer_slots.add(prefix)
				any_data = True

		for prefix, _label, default_mandatory, has_na, file_suffix in AC_DOCUMENT_ROWS:
			file_val, is_na, status = self._row_state(prefix, has_na, file_suffix)
			parent_na = self._row_inherits_parent_na(prefix)
			# Parent-level N/A propagation: a Most Recent Employer marked N/A
			# auto-satisfies all its sub-docs without needing per-row HR review.
			if parent_na:
				is_na = True
			has_data = bool(file_val) or is_na

			# HR Settings can override the mandatory flag for the 3 payslip rows
			# (REQUIRED ↔ OPTIONAL). Other rows return the hardcoded default.
			mandatory = get_effective_mandatory(prefix, default_mandatory)

			# Conditional mandatory: a Previous Employer (2-5) becomes mandatory the
			# moment the employee fills any detail for it. They satisfy it by either
			# uploading the relieving doc or marking the slot Not Applicable.
			if (
				prefix in ("employer_2", "employer_3", "employer_4", "employer_5")
				and prefix in started_employer_slots
			):
				mandatory = True

			if has_data or status not in ("Pending", ""):
				any_data = True
			# Suppress raw status signals when parent N/A — the parent flag is
			# the verdict; stale per-row Rejected/Awaiting from before the N/A
			# toggle should not bubble up to the master status.
			if status == "Rejected" and not parent_na:
				any_rejected = True
			if status == "Awaiting HR" and not parent_na:
				any_awaiting = True

			if mandatory:
				if not has_data:
					all_mandatory_done = False
				# parent_na auto-accepts (the N/A flag IS the HR verdict).
				if not parent_na and status != "Accepted":
					all_mandatory_accepted = False
			else:
				if has_data and not parent_na and status != "Accepted":
					any_optional_pending_review = True

		# Declarations participate in master status the same way as documents:
		# rejected -> Action Required, accepted -> contributes to Accepted, etc.
		# No parent_na concept here.
		for prefix, _label, mandatory, has_na, data_suffix in AC_DECLARATION_ROWS:
			val = self.get(f"{prefix}{data_suffix}") or ""
			is_na = bool(self.get(f"{prefix}_is_na")) if has_na else False
			status = self.get(f"{prefix}_approval_status") or "Pending"
			has_data = bool(val) or is_na

			if has_data or status not in ("Pending", ""):
				any_data = True
			if status == "Rejected":
				any_rejected = True
			if status == "Awaiting HR":
				any_awaiting = True

			if mandatory:
				if not has_data:
					all_mandatory_done = False
				if status != "Accepted":
					all_mandatory_accepted = False
			else:
				if has_data and status != "Accepted":
					any_optional_pending_review = True

		# Personal-detail / statutory / identity-number fields. These are pure
		# data capture (no per-row HR approval). They DO contribute to
		# all_mandatory_done — the employee can't reach "Ready to Submit"
		# until every mandatory personal field has a value.
		for fieldname, _label, mandatory in AC_PERSONAL_DATA_FIELDS:
			val = (self.get(fieldname) or "")
			if isinstance(val, str):
				val = val.strip()
			has_data = bool(val)
			if has_data:
				any_data = True
			if mandatory and not has_data:
				all_mandatory_done = False

		submitted = bool(self.submitted_for_review)

		if any_rejected:
			return "Action Required"
		if submitted and all_mandatory_accepted and not any_optional_pending_review:
			return "Accepted"
		if submitted and all_mandatory_done and any_awaiting:
			return "To be Reviewed"
		if all_mandatory_done and not submitted:
			return "Ready to Submit"
		if any_data:
			return "In Progress"
		return "Pending"
