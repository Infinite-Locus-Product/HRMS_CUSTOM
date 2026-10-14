import frappe
from frappe.utils import cint, get_datetime, getdate

AUTO_PRESENT_DEVICE = "myHR Auto"


def validate_employee(doc, method):
    """Keep Employee Directory in sync with Employee.

    - On insert, if `custom_employee_id` is provided, force `Employee.name` to it.
    - If `custom_emp_directory` is checked AND the employee is Active, upsert directory row.
    - Otherwise, drop any existing directory row for this employee.
    """
    if doc.is_new() and doc.custom_employee_id:
        doc.name = doc.custom_employee_id

    _validate_auto_present_prereqs(doc)

    if not doc.name:
        return

    should_appear = bool(doc.custom_emp_directory) and (doc.status == "Active")

    # All Directory writes from this sanctioned syncer set the canonical-write
    # flag so the EmployeeDirectory.validate / on_trash guards don't trip.
    frappe.flags.allow_directory_write = True
    try:
        if should_appear:
            payload = {
                "doctype": "Employee Directory",
                "employee_id": doc.name,
                "employee_name": doc.employee_name,
                "designation": doc.designation,
                "department": doc.department,
                "mobile_number": doc.cell_number,
                "employee_email": doc.company_email,
            }
            if frappe.db.exists("Employee Directory", doc.name):
                directory_doc = frappe.get_doc("Employee Directory", doc.name)
                directory_doc.update(payload)
                directory_doc.save(ignore_permissions=True)
            else:
                frappe.get_doc(payload).insert(ignore_permissions=True)
        else:
            if frappe.db.exists("Employee Directory", doc.name):
                frappe.delete_doc("Employee Directory", doc.name, ignore_permissions=True)
    finally:
        frappe.flags.allow_directory_write = False


def _validate_auto_present_prereqs(doc):
    """Block save when `custom_auto_present=1` but the prereqs for the
    auto-attendance pipeline aren't satisfied — fail loudly here instead of
    letting the user discover later that "Auto Present is on but nothing's
    happening".

    The cron (`auto_present_in` / `auto_present_out`) inserts an Employee
    Checkin row, but creating the Attendance row downstream relies on HRMS's
    per-shift `process_auto_attendance` sweep. That sweep needs:
      1. A shift to scope the sweep — either `Employee.default_shift` set, or
         an active submitted Shift Assignment covering today.
      2. That Shift Type's `enable_auto_attendance` must be ticked.

    Without either, Checkins pile up but no Attendance is ever marked. So:
    we refuse to enable Auto Present until both are in place. HR fixes the
    pre-reqs once, then ticks Auto Present, and the cron Just Works.
    """
    if not cint(doc.get("custom_auto_present") or 0):
        return

    today = getdate()
    shift_name = doc.get("default_shift") or _find_active_shift_assignment(doc.name, today)
    if not shift_name:
        frappe.throw(
            "Auto Present cannot be enabled until this employee has a "
            "<b>Default Shift</b> set (Attendance and Leave Details tab) or "
            "an active Shift Assignment covering today. The daily cron needs "
            "a shift so HRMS's auto-attendance sweep knows which Checkins to "
            "process.",
            title="Auto Present prerequisites missing",
        )

    if not cint(frappe.db.get_value("Shift Type", shift_name, "enable_auto_attendance") or 0):
        frappe.throw(
            f"Auto Present cannot be enabled until Shift Type <b>{shift_name}</b> "
            "has <b>Enable Auto Attendance</b> ticked. Without that, the daily "
            "Checkins this cron creates never become Attendance rows.",
            title="Auto Present prerequisites missing",
        )


def _find_active_shift_assignment(employee, on_date):
    """Return the shift_type of an active Shift Assignment for `employee` on
    `on_date`, if any. An assignment is 'active' when its status is Active,
    docstatus is 1 (submitted), and `on_date` falls within [start_date,
    end_date] inclusive (end_date NULL means open-ended).
    """
    if not employee:
        return None
    row = frappe.db.sql(
        """SELECT shift_type FROM `tabShift Assignment`
           WHERE employee=%(emp)s AND docstatus=1 AND status='Active'
             AND start_date <= %(d)s
             AND (end_date IS NULL OR end_date >= %(d)s)
           ORDER BY start_date DESC LIMIT 1""",
        {"emp": employee, "d": on_date},
        as_dict=True,
    )
    return row[0]["shift_type"] if row else None


def on_trash_employee(doc, method):
    """Remove the directory row when an Employee is deleted, and cascade-delete
    the Action Centre + Policy Acknowledgements (compliance trail keyed to the
    employee's existence). The `deleting_employee` flag lets the AC's on_trash
    guard recognise this is a sanctioned cascade, not an HR maintenance wipe."""
    frappe.flags.deleting_employee = True
    try:
        if doc.name and frappe.db.exists("Employee Directory", doc.name):
            frappe.delete_doc("Employee Directory", doc.name, ignore_permissions=True)

        # Cascade: every AC row tied to this Employee. There should only be one
        # post-EAC-1 (unique index), but we loop defensively.
        for ac in frappe.get_all("Employee Action Centre", filters={"employee": doc.name}, pluck="name"):
            frappe.delete_doc("Employee Action Centre", ac, ignore_permissions=True, force=1)
    finally:
        frappe.flags.deleting_employee = False


def after_rename_employee(doc, method, old_name=None, new_name=None, merge=False):
    """Rename the directory row to track Employee renames."""
    if old_name and new_name and frappe.db.exists("Employee Directory", old_name):
        frappe.flags.allow_directory_write = True
        try:
            frappe.rename_doc(
                "Employee Directory", old_name, new_name,
                force=True, merge=merge, ignore_permissions=True,
            )
        finally:
            frappe.flags.allow_directory_write = False


def _ensure_action_centre(doc):
    if not cint(doc.get("custom_add_to_action_centre", 1)):
        return
    if frappe.db.exists("Employee Action Centre", {"employee": doc.name}):
        return
    ac = frappe.get_doc({
        "doctype": "Employee Action Centre",
        "employee": doc.name,
        "employee_name": doc.employee_name,
    })
    ac.insert(ignore_permissions=True)
    if doc.user_id:
        frappe.share.add("Employee Action Centre", ac.name, doc.user_id, write=1, share=0)


def after_employee_insert(doc, method):
    _ensure_action_centre(doc)


def on_update_employee(doc, method):
    _ensure_action_centre(doc)


def notify_employee_on_attendance_request_submit(doc, method=None):
    """AR-1: in-app Notification Log to the employee when their AR is
    submitted. Submit creates Attendance rows for the requested dates —
    the employee deserves a ping.

    Best-effort — failures log to Error Log, never raise.
    """
    try:
        if doc.docstatus != 1:
            return
        emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")
        if not emp_user:
            return
        subject = f"[myHR Attendance] Request approved — {doc.from_date} to {doc.to_date}"
        body = (
            "<p>Your Attendance Request has been approved and recorded.</p>"
            f"<p><b>From:</b> {doc.from_date}<br>"
            f"<b>To:</b> {doc.to_date}<br>"
            f"<b>Reason:</b> {doc.reason or '—'}</p>"
            "<p>Attendance entries have been generated for the dates above.</p>"
        )
        frappe.get_doc({
            "doctype": "Notification Log",
            "for_user": emp_user,
            "type": "Alert",
            "subject": subject,
            "email_content": body,
            "document_type": "Attendance Request",
            "document_name": doc.name,
            "from_user": "Administrator",
        }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(
            title="myHR notify_employee_on_attendance_request_submit failed",
            message=frappe.get_traceback(),
        )


def validate_attendance_request_policy_gate(doc, method):
    """Block Attendance Request save unless:
      - the calling user is HR / the target employee themselves / the target's
        named leave_approver (relaxed ownership — managers may write AR on
        behalf of their direct reports), AND
      - every mandatory-check-in HR Policy is acknowledged for the target.

    `custom_bypass_geolocation_check` does NOT exempt either gate.

    Note: the actual *submit* (docstatus 0 → 1) is gated separately by
    `myhr.approval_gate.gate_attendance_request_submit` which enforces that
    only HR Manager or the named approver can submit. The relaxed
    ownership gate here lets the manager *load and edit* a report's draft AR
    before they submit it.
    """
    if not doc.employee:
        return

    from myhr.ownership_gate import assert_writable_for_team
    from myhr.policy_gate import assert_policies_acknowledged
    assert_writable_for_team(doc)
    assert_policies_acknowledged(doc.employee, action_label="submit an attendance request")


def _auto_checkin(log_type: str, hour: int, minute: int):
    """Insert one Employee Checkin per `custom_auto_present=1` employee.

    Per-employee fault tolerance: each insert runs in its own savepoint and is
    committed individually. A failure for one employee (duplicate log,
    validation error, hook throw, etc.) is logged and the loop continues for
    the rest. Without this, a single bad row would abort the whole batch and
    nobody would get auto-marked.

    CHK-3: on failure, notify (a) the affected employee that their auto
    check-in didn't happen and (b) HR Manager / System Manager users so they
    can investigate. Without notifications, cron failures sat silently in the
    Error Log.
    """
    d = getdate()
    if d.weekday() >= 5:
        return
    dt = get_datetime(f"{d} {hour:02d}:{minute:02d}:00")
    for emp in frappe.get_all(
        "Employee",
        filters={"status": "Active", "custom_auto_present": 1},
        pluck="name",
    ):
        savepoint = f"auto_checkin_{emp}_{log_type}".replace("-", "_")
        frappe.db.savepoint(savepoint)
        try:
            frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": emp,
                "log_type": log_type,
                "time": dt,
                "device_id": AUTO_PRESENT_DEVICE,
            }).insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback(save_point=savepoint)
            error_trace = frappe.get_traceback()
            frappe.log_error(
                title=f"myHR auto_checkin failed for {emp} ({log_type})",
                message=error_trace,
            )
            _notify_on_auto_checkin_failure(emp, log_type, dt, error_trace)


def _notify_on_auto_checkin_failure(employee, log_type, dt, error_trace):
    """Best-effort notifications for an auto-checkin cron failure.

    Notifies the affected employee (so they don't show up Monday and find
    they're 'absent' for last week) and every HR Manager / System Manager
    user (so the gap is acted on). Wrapped in try/except so notification
    plumbing failures never fail the cron.
    """
    try:
        emp_name = frappe.db.get_value("Employee", employee, "employee_name") or employee
        emp_user = frappe.db.get_value("Employee", employee, "user_id")
        # Truncate the traceback so the body stays readable.
        snippet = (error_trace or "")[-500:].replace("\n", " ")

        # Employee: brief, actionable.
        if emp_user:
            frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": emp_user,
                "type": "Alert",
                "subject": f"[myHR Attendance] Auto check-in did NOT fire — {log_type} {dt}",
                "email_content": (
                    f"<p>Your scheduled auto check-in ({log_type} at {dt}) failed to record.</p>"
                    "<p>Please check in manually if needed, or contact HR.</p>"
                ),
                "document_type": "Employee",
                "document_name": employee,
                "from_user": "Administrator",
            }).insert(ignore_permissions=True)

        # HR fan-out
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
                "subject": f"[myHR Attendance] Auto check-in failed for {emp_name} — {log_type}",
                "email_content": (
                    f"<p>The auto-present cron failed to record a {log_type} check-in for "
                    f"<b>{emp_name}</b> ({employee}) at {dt}.</p>"
                    f"<p><b>Error tail:</b><br><code>{snippet}</code></p>"
                    "<p>See the Error Log for full details.</p>"
                ),
                "document_type": "Employee",
                "document_name": employee,
                "from_user": "Administrator",
            }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        # Notification plumbing failed; swallow so the cron continues.
        try:
            frappe.log_error(
                title="myHR _notify_on_auto_checkin_failure failed",
                message=frappe.get_traceback(),
            )
        except Exception:
            pass


def auto_present_in():
    _auto_checkin("IN", 9, 0)


def auto_present_out():
    _auto_checkin("OUT", 18, 0)
