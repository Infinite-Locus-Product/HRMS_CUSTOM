"""Fan-out PWA Notifications to every HR Manager when an employee submits a
document that needs HR review (Leave Application, Attendance Request, Expense
Claim).

Stock HRMS already notifies the *named approver* on the document
(`leave_approver` / `expense_approver`) via `PWANotificationsMixin.notify_approver`.
This module is the parallel surface for the **HR Manager role pool** — any
user who can review submissions in general, not just the specific person
listed on the doc.

Policy Acknowledgement is intentionally NOT wired here. Acknowledging a
policy is an employee-side action with no HR action required, so HR Managers
should not be paged for it.
"""
import frappe
from frappe import bold


# Doctypes whose insert by an employee should fan out to HR Managers.
# Keep this in lock-step with `hooks.py`.
HR_REVIEW_DOCTYPES = ("Leave Application", "Attendance Request", "Expense Claim")


def _hr_manager_users() -> list[str]:
	"""Return all enabled User records with the HR Manager role.

	Excludes Administrator and Guest. Cached per-request — the hook can fire
	repeatedly in a bulk import and we don't want a fresh JOIN every time.
	"""
	cache_key = "myhr:hr_manager_users"
	cached = frappe.local.cache.get(cache_key) if hasattr(frappe.local, "cache") else None
	if cached is not None:
		return cached
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT u.name
		FROM `tabUser` u
		INNER JOIN `tabHas Role` r ON r.parent = u.name AND r.parenttype = 'User'
		WHERE r.role = 'HR Manager'
		  AND u.enabled = 1
		  AND u.name NOT IN ('Administrator', 'Guest')
		""",
		as_dict=False,
	)
	users = [r[0] for r in rows]
	if hasattr(frappe.local, "cache"):
		frappe.local.cache[cache_key] = users
	return users


def _doc_label(doc) -> str:
	"""Friendly label per doctype, falls back to the docname."""
	if doc.doctype == "Leave Application":
		return f"Leave Application ({doc.get('leave_type') or 'leave'})"
	if doc.doctype == "Attendance Request":
		return f"Attendance Request ({doc.get('reason') or 'attendance'})"
	if doc.doctype == "Expense Claim":
		return f"Expense Claim"
	return doc.doctype


def notify_hr_managers_on_submit(doc, method=None):
	"""after_insert hook — create one PWA Notification per HR Manager.

	Skip when:
	  - the submitter IS an HR Manager (don't self-notify),
	  - the HR Manager IS the employee on the doc (already notified by the
	    standard approver flow if they're also the approver),
	  - the doc has no employee field set (defensive).

	Best-effort — wrapped in try/except so notification failure never blocks
	the actual document submit.
	"""
	try:
		if doc.doctype not in HR_REVIEW_DOCTYPES:
			return
		employee = doc.get("employee")
		if not employee:
			return

		hr_managers = _hr_manager_users()
		if not hr_managers:
			return

		submitter = frappe.session.user
		submitter_name = frappe.db.get_value("User", submitter, "full_name", cache=True) or submitter
		employee_name = doc.get("employee_name") or employee
		label = _doc_label(doc)
		message = (
			f"{bold(employee_name)} submitted a new {bold(label)} for HR review: {bold(doc.name)}"
		)

		employee_user = frappe.db.get_value("Employee", employee, "user_id", cache=True)

		for hr_user in hr_managers:
			# Don't notify the submitter (an HR Manager filing their own claim).
			if hr_user == submitter:
				continue
			# Don't notify the employee on the doc (avoids self-ping if the
			# employee themselves holds the HR Manager role).
			if hr_user == employee_user:
				continue
			frappe.get_doc({
				"doctype": "PWA Notification",
				"to_user": hr_user,
				"from_user": submitter,
				"message": message,
				"reference_document_type": doc.doctype,
				"reference_document_name": doc.name,
				"read": 0,
			}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(
			title="myHR notify_hr_managers_on_submit failed",
			message=frappe.get_traceback(),
		)
