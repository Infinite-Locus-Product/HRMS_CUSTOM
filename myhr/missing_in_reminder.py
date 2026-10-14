"""Daily 11:00 AM reminder for employees missing an IN Employee Checkin.

Cron entrypoint: `send_missing_in_reminders` — fires from
`scheduler_events.cron['0 11 * * *']` in `hooks.py`. Short-circuits
when the global `HR Settings.custom_enable_checkin_reminder` flag is
unticked. Otherwise iterates Active employees in scope today, applies
a short-circuiting filter chain (dedup → opt_out → holiday → leave →
IN-exists → email-resolve), and queues one templated email per
pending employee via `frappe.sendmail`. Per-employee opt-out lives on
`Employee.custom_send_checkin_reminder` (default ticked).

Per-employee savepoint isolates failures so one bad row does not
abort the entire run. Each employee outcome is persisted as a
`Missing Checkin Reminder Log` row (Sent / Skipped / Failed).
"""

from __future__ import annotations

import frappe
from frappe.utils import formatdate, get_datetime, getdate, now_datetime

TEMPLATE_NAME = "Missing IN Checkin Reminder"


def _candidate_employees(on_date):
    return frappe.db.sql(
        """SELECT name, employee_name, holiday_list, company,
                  prefered_email, company_email, user_id,
                  custom_send_checkin_reminder
           FROM `tabEmployee`
           WHERE status='Active'
             AND date_of_joining <= %(d)s
             AND (relieving_date IS NULL OR relieving_date >= %(d)s)""",
        {"d": on_date},
        as_dict=True,
    )


def _global_reminder_enabled():
    # NULL on a freshly-added Check column → treat as ticked (default=1).
    val = frappe.db.get_single_value("HR Settings", "custom_enable_checkin_reminder")
    return val is None or int(val) == 1


def _employee_opted_in(emp_row):
    val = emp_row.get("custom_send_checkin_reminder")
    return val is None or int(val) == 1


def _resolve_email(emp_row):
    if emp_row.prefered_email:
        return emp_row.prefered_email
    if emp_row.company_email:
        return emp_row.company_email
    if emp_row.user_id:
        return frappe.db.get_value("User", emp_row.user_id, "email")
    return None


def _already_sent(employee, on_date):
    return bool(frappe.db.exists(
        "Missing Checkin Reminder Log",
        {"employee": employee, "reminder_date": on_date, "status": "Sent"},
    ))


def _is_holiday(holiday_list, company, on_date):
    hl = holiday_list or frappe.db.get_value("Company", company, "default_holiday_list")
    if not hl:
        return False
    return bool(frappe.db.exists(
        "Holiday", {"parent": hl, "holiday_date": on_date},
    ))


def _is_on_leave_or_pending(employee, on_date):
    return bool(frappe.db.sql(
        """SELECT 1 FROM `tabLeave Application`
           WHERE employee=%(e)s
             AND docstatus IN (0, 1)
             AND status IN ('Open', 'Approved')
             AND from_date <= %(d)s AND to_date >= %(d)s
           LIMIT 1""",
        {"e": employee, "d": on_date},
    ))


def _has_in_checkin_before(employee, cutoff_dt):
    return bool(frappe.db.sql(
        """SELECT 1 FROM `tabEmployee Checkin`
           WHERE employee=%(e)s AND log_type='IN' AND `time` <= %(c)s
             AND DATE(`time`) = DATE(%(c)s)
           LIMIT 1""",
        {"e": employee, "c": cutoff_dt},
    ))


def _insert_log(employee, on_date, status, skip_reason="none",
                email=None, sent_at=None, error=None):
    frappe.get_doc({
        "doctype": "Missing Checkin Reminder Log",
        "employee": employee,
        "reminder_date": on_date,
        "status": status,
        "skip_reason": skip_reason,
        "email_sent_to": email,
        "sent_at": sent_at,
        "error_message": error,
    }).insert(ignore_permissions=True)


def _render_and_send(emp_row, email, on_date, template):
    context = {
        "doc": emp_row,
        "employee_name": emp_row.employee_name,
        "employee_id": emp_row.name,
        "date": formatdate(on_date),
    }
    subject = frappe.render_template(template.subject, context)
    body = frappe.render_template(template.response, context)
    frappe.sendmail(
        recipients=[email],
        subject=subject,
        message=body,
        reference_doctype="Employee",
        reference_name=emp_row.name,
        now=False,
        delayed=True,
        header=["Missing Check-in Reminder", "blue"],
    )


def send_missing_in_reminders(on_date=None, cutoff_hour=11):
    """Daily 11:00 cron. Sends one reminder per eligible employee missing IN.

    Args:
        on_date: 'YYYY-MM-DD' (defaults today). Backfill:
            bench --site <s> execute myhr.missing_in_reminder.send_missing_in_reminders \\
              --kwargs '{"on_date": "2026-05-17"}'
        cutoff_hour: int. Default 11. Testability handle only.
    """
    on_date = getdate(on_date) if on_date else getdate()
    cutoff_dt = get_datetime(f"{on_date} {cutoff_hour:02d}:00:00")

    if not _global_reminder_enabled():
        frappe.logger().info(
            f"myhr.missing_in_reminder: global HR Settings flag "
            f"'custom_enable_checkin_reminder' is OFF — short-circuiting "
            f"run on {on_date}."
        )
        return

    if not frappe.db.exists("Email Template", TEMPLATE_NAME):
        frappe.log_error(
            title="myHR missing_in_reminder: template missing",
            message=f"Email Template '{TEMPLATE_NAME}' not found; aborting run.",
        )
        return
    template = frappe.get_doc("Email Template", TEMPLATE_NAME)

    sent = skipped_holiday = skipped_leave = skipped_in = skipped_email = 0
    skipped_opt_out = failed = 0

    for emp_row in _candidate_employees(on_date):
        savepoint = f"mcr_{emp_row.name}".replace("-", "_").replace(" ", "_")[:60]
        try:
            frappe.db.savepoint(savepoint)
            if _already_sent(emp_row.name, on_date):
                continue
            if not _employee_opted_in(emp_row):
                _insert_log(emp_row.name, on_date, "Skipped", "opt_out")
                skipped_opt_out += 1
                frappe.db.commit()
                continue
            if _is_holiday(emp_row.holiday_list, emp_row.company, on_date):
                _insert_log(emp_row.name, on_date, "Skipped", "holiday")
                skipped_holiday += 1
                frappe.db.commit()
                continue
            if _is_on_leave_or_pending(emp_row.name, on_date):
                _insert_log(emp_row.name, on_date, "Skipped", "leave")
                skipped_leave += 1
                frappe.db.commit()
                continue
            if _has_in_checkin_before(emp_row.name, cutoff_dt):
                _insert_log(emp_row.name, on_date, "Skipped",
                            "already_checked_in")
                skipped_in += 1
                frappe.db.commit()
                continue
            email = _resolve_email(emp_row)
            if not email:
                _insert_log(emp_row.name, on_date, "Skipped", "missing_email")
                skipped_email += 1
                frappe.db.commit()
                continue
            _render_and_send(emp_row, email, on_date, template)
            _insert_log(emp_row.name, on_date, "Sent", "none",
                        email=email, sent_at=now_datetime())
            sent += 1
            frappe.db.commit()
        except Exception:
            failed += 1
            try:
                frappe.db.rollback(save_point=savepoint)
            except Exception:
                pass
            frappe.log_error(
                title=f"myHR missing_in_reminder failed for {emp_row.name}",
                message=frappe.get_traceback(),
            )
            try:
                _insert_log(emp_row.name, on_date, "Failed", "none",
                            error=frappe.get_traceback()[-1000:])
                frappe.db.commit()
            except Exception:
                pass

    frappe.logger().info(
        f"myhr.missing_in_reminder summary on {on_date}: "
        f"sent={sent} skipped(opt_out={skipped_opt_out} holiday={skipped_holiday} "
        f"leave={skipped_leave} in={skipped_in} email={skipped_email}) "
        f"failed={failed}"
    )
