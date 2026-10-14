"""Ownership gate — defensive layer enforcing that non-HR users may only
create/modify Employee Checkin / Attendance Request rows for their own
Employee.

Stock HRMS grants the `Employee` role create+write on both doctypes without an
`if_owner` flag, relying on per-user `User Permission` rows to scope visibility.
On sites that don't seed those (this one), an employee logged into the PWA can
post a check-in or AR with `employee = <someone else>` simply by editing the
payload. This module patches that with a server-side check.

Two flavours:

  - `assert_self_or_hr(doc)` — strict. Used for Employee Checkin: only the
    target employee themselves or HR can write. Managers cannot punch in
    on behalf of their reports.
  - `assert_writable_for_team(doc)` — relaxed. Used for Attendance Request:
    HR, the target employee themselves, OR the target employee's named
    `leave_approver` may write. This lets managers submit AR for their
    direct reports (which is the "approval" act for AR — submitting it
    creates the Attendance row).

HR Manager / System Manager / Administrator bypass both gates.
"""

import frappe


HR_ROLES = {"HR Manager", "System Manager"}


def _is_hr_or_admin(user: str) -> bool:
	if user == "Administrator":
		return True
	return bool(HR_ROLES & set(frappe.get_roles(user)))


def assert_self_or_hr(doc) -> None:
	"""Throw `frappe.PermissionError` unless caller is HR or the target employee.

	Used by Employee Checkin — strict ownership.
	"""
	if not doc or not doc.employee:
		return

	user = frappe.session.user
	if _is_hr_or_admin(user):
		return

	emp_user_id = frappe.db.get_value("Employee", doc.employee, "user_id")
	if emp_user_id != user:
		frappe.throw(
			f"You are not allowed to create or modify {doc.doctype} for "
			f"another employee.",
			frappe.PermissionError,
		)


def assert_writable_for_team(doc) -> None:
	"""Throw `frappe.PermissionError` unless caller is HR, the target employee,
	or the target employee's named `leave_approver`.

	Used by Attendance Request — relaxed ownership so the named manager can
	submit AR on their report's behalf (the submit act creates Attendance,
	which is functionally equivalent to approving the request).
	"""
	if not doc or not doc.employee:
		return

	user = frappe.session.user
	if _is_hr_or_admin(user):
		return

	emp = frappe.db.get_value(
		"Employee", doc.employee, ["user_id", "leave_approver"], as_dict=True,
	) or frappe._dict()

	if emp.user_id == user:
		return
	if emp.leave_approver and emp.leave_approver == user:
		return

	frappe.throw(
		f"You are not allowed to create or modify {doc.doctype} for "
		f"another employee.",
		frappe.PermissionError,
	)
