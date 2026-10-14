"""Employee permission model for myhr.

Replaces the older Frappe `create_user_permission` (CUP) approach with a
simpler, code-driven rule:

  - HR Manager / HR User / System Manager / Administrator -> see all employees
  - Anyone else with an Employee linked via user_id:
      - if Employee.custom_allow_view_reporting = 1: see self + direct reports
      - if Employee.custom_allow_view_reporting = 0: see only self
  - Anyone without an Employee link: no access

Wired via `permission_query_conditions` and `has_permission` hooks in hooks.py.

Write/Submit/Delete is restricted to HR Manager + System Manager + Administrator
ONLY. Even HR User (read-only on Employee since 2026-04-27) and the user's own
record are blocked from writes — by design, "any info you want updated, ask
HR Manager." See `has_employee_permission` and
`myhr.setup._ensure_employee_perm_lockdown` for the two layers of enforcement.
"""
import frappe

_PRIVILEGED_ROLES = {"HR Manager", "HR User", "System Manager"}
# Subset of _PRIVILEGED_ROLES that may write/create/delete/submit Employee
# records. HR User reads-everyone but writes-nothing (lockdown 2026-04-27).
_FULL_ADMIN_ROLES = {"HR Manager", "System Manager"}


def _privileged(user):
    """User is Administrator, HR Manager, HR User, or System Manager."""
    if user == "Administrator":
        return True
    return bool(_PRIVILEGED_ROLES & set(frappe.get_roles(user)))


def _full_admin(user):
    """User is Administrator, HR Manager, or System Manager (write-class)."""
    if user == "Administrator":
        return True
    return bool(_FULL_ADMIN_ROLES & set(frappe.get_roles(user)))


def _user_employee(user):
    """Return (name, custom_allow_view_reporting) for the Employee linked
    to `user`. Cached per request via frappe.local for hot list views.

    Returns None if no Employee is linked to that user."""
    if user in (None, "", "Administrator", "Guest"):
        return None
    cache = getattr(frappe.local, "_myhr_user_emp_cache", None)
    if cache is None:
        cache = frappe.local._myhr_user_emp_cache = {}
    if user in cache:
        return cache[user]
    row = frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "custom_allow_view_reporting"],
        as_dict=True,
    )
    cache[user] = row
    return row


def employee_permission_query_conditions(user=None):
    """List-query SQL fragment for Employee.

    Wired in hooks.py under `permission_query_conditions["Employee"]`."""
    user = user or frappe.session.user
    if _privileged(user):
        return ""
    emp = _user_employee(user)
    if not emp:
        return "1=0"
    self_name = frappe.db.escape(emp.name)
    if emp.get("custom_allow_view_reporting"):
        return (
            f"(`tabEmployee`.`name` = {self_name} "
            f"OR `tabEmployee`.`reports_to` = {self_name})"
        )
    return f"`tabEmployee`.`name` = {self_name}"


def has_employee_permission(doc, ptype="read", user=None):
    """Record-level Employee perm check.

    Read-scope:
      - Administrator / HR Manager / System Manager: all records
      - HR User: all records (read only — write is denied below)
      - Else with Employee linked + custom_allow_view_reporting=1: self + direct reports
      - Else with Employee linked + custom_allow_view_reporting=0: self only
      - Else: nothing

    Write-scope (write/create/delete/submit/cancel/amend):
      - Administrator / HR Manager / System Manager: allowed (return None -> docperm)
      - Everyone else: DENIED. Even on own record. The rule is "ask HR Manager
        to update your info" -- self-edit is intentionally blocked to keep the
        audit chain clean and prevent users from changing their own department,
        designation, leave_approver, etc.

    Wired in hooks.py under `has_permission["Employee"]`."""
    user = user or frappe.session.user

    is_admin = user == "Administrator"
    roles = set(frappe.get_roles(user))
    is_full_admin = is_admin or bool(_FULL_ADMIN_ROLES & roles)
    is_hr_user = "HR User" in roles

    # Write-class ptypes: only full admins (HR Manager / System Manager / Administrator).
    write_ptypes = {"write", "create", "delete", "submit", "cancel", "amend", "import", "export"}
    if ptype in write_ptypes:
        return True if is_full_admin else False

    # Read / print / report / email: full admins + HR User see everything.
    if ptype in ("read", "print", "report", "email", "share"):
        if is_full_admin or is_hr_user:
            return True
        emp = _user_employee(user)
        if not emp:
            return False
        doc_name = doc.name if hasattr(doc, "name") else doc
        if doc_name == emp.name:
            return True
        if emp.get("custom_allow_view_reporting"):
            reports_to = doc.reports_to if hasattr(doc, "reports_to") else \
                frappe.db.get_value("Employee", doc_name, "reports_to")
            return reports_to == emp.name
        return False

    # Unknown ptype: be safe — defer to docperm
    return None


# ---------------------------------------------------------------------------
# Employee Separation — the resignation record
#
# Stock HRMS grants Employee Separation only to System Manager / HR Manager /
# HR User, so a plain employee cannot raise their own resignation and a
# reporting manager cannot open one to approve it. `MYHR_ADDITIVE_PERMISSIONS`
# adds an Employee row; on its own that would let EVERY employee read EVERY
# resignation, so the two functions below narrow it to the three people the
# record actually concerns: the employee, their L1, and their L2.
#
# This is the read/list gate. It deliberately does not decide who may APPROVE —
# that is the workflow transition `condition`, re-derived server-side by
# `frappe.model.workflow.apply_workflow`.
# ---------------------------------------------------------------------------
def employee_separation_query_conditions(user=None):
	user = user or frappe.session.user
	if _privileged(user):
		return ""

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		# No Employee link -> no rows at all. Returning "" here would mean
		# "no restriction", which is the opposite of what we want.
		return "1=0"

	employee = frappe.db.escape(employee)
	return (
		f"(`tabEmployee Separation`.`employee` = {employee}"
		f" or `tabEmployee Separation`.`custom_reporting_manager` = {employee}"
		f" or `tabEmployee Separation`.`custom_l2_manager` = {employee})"
	)


def has_employee_separation_permission(doc, ptype="read", user=None):
	"""Document-level twin of the query condition above.

	The query condition only filters list views and reports; a direct
	`frappe.get_doc(...)` bypasses it entirely, so the same rule is repeated
	here. Both layers are required.
	"""
	user = user or frappe.session.user
	if _privileged(user):
		return True

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return False

	return employee in {
		doc.get("employee"),
		doc.get("custom_reporting_manager"),
		doc.get("custom_l2_manager"),
	}


# ---------------------------------------------------------------------------
# Separation Manager Clearance
#
# The doctype's own perms grant the Employee role read/write/create/submit; on
# their own that would let every employee see every leaver's handover. These two
# narrow it to the two people the record concerns: the leaver and their manager.
#
# Who may COMPLETE it is a separate question, answered by the workflow's
# transition condition, not here.
# ---------------------------------------------------------------------------
def separation_manager_clearance_query_conditions(user=None):
	user = user or frappe.session.user
	if _privileged(user):
		return ""

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		# "" would mean "no restriction", which is the opposite of what we want.
		return "1=0"

	employee = frappe.db.escape(employee)
	return (
		f"(`tabSeparation Manager Clearance`.`employee` = {employee}"
		f" or `tabSeparation Manager Clearance`.`reporting_manager` = {employee})"
	)


def has_separation_manager_clearance_permission(doc, ptype="read", user=None):
	"""Document-level twin — a direct get_doc bypasses the query condition."""
	user = user or frappe.session.user
	if _privileged(user):
		return True

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return False

	return employee in {doc.get("employee"), doc.get("reporting_manager")}


# ---------------------------------------------------------------------------
# Separation IT Clearance
#
# HR/IT own this form; the Employee role has read-only perms so a leaver and
# their manager can see what was recorded against them (it drives a deduction).
# These narrow that read to their own rows.
# ---------------------------------------------------------------------------
def separation_it_clearance_query_conditions(user=None):
	user = user or frappe.session.user
	if _privileged(user):
		return ""

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return "1=0"

	employee = frappe.db.escape(employee)
	return (
		f"(`tabSeparation IT Clearance`.`employee` = {employee}"
		f" or `tabSeparation IT Clearance`.`reporting_manager` = {employee})"
	)


def has_separation_it_clearance_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if _privileged(user):
		return True

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return False

	return employee in {doc.get("employee"), doc.get("reporting_manager")}


# ---------------------------------------------------------------------------
# Separation HR Clearance
#
# HR owns this one. The Employee role gets read-only so a leaver and their
# manager can see the clearance and the released letter; these narrow that to
# their own rows. Note the internal re-hire reason is print_hide, so it never
# reaches the letter — but it IS readable here by the two of them, which is why
# the field is worded as an internal HR note rather than a private one.
# ---------------------------------------------------------------------------
def separation_hr_clearance_query_conditions(user=None):
	user = user or frappe.session.user
	if _privileged(user):
		return ""

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return "1=0"

	employee = frappe.db.escape(employee)
	return (
		f"(`tabSeparation HR Clearance`.`employee` = {employee}"
		f" or `tabSeparation HR Clearance`.`reporting_manager` = {employee})"
	)


def has_separation_hr_clearance_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if _privileged(user):
		return True

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return False

	return employee in {doc.get("employee"), doc.get("reporting_manager")}
