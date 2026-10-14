"""Tests for `myhr.missing_in_reminder.send_missing_in_reminders`.

Each test seeds a fresh Employee + Holiday List + (optionally) Leave
Application / Employee Checkin, runs the entrypoint with an explicit
`on_date`, and asserts against `Missing Checkin Reminder Log` rows
and `Email Queue` rows.

The Email Template "Missing IN Checkin Reminder" is seeded once in
setUpClass with minimal subject/body so we can verify the
render_template + sendmail path end-to-end.
"""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_datetime, getdate, now_datetime

from myhr.missing_in_reminder import send_missing_in_reminders

TEMPLATE_NAME = "Missing IN Checkin Reminder"
TEST_HOLIDAY_LIST = "MCR Test Holiday List 2026"
TEST_COMPANY = "_Test Company"
TEST_EMPLOYEE_PREFIX = "MCR-"


def _ensure_company():
    if frappe.db.exists("Company", TEST_COMPANY):
        return TEST_COMPANY
    existing = frappe.db.get_value("Company", {}, "name")
    if existing:
        return existing
    raise RuntimeError("No Company in this site; create one first.")


def _ensure_template():
    if frappe.db.exists("Email Template", TEMPLATE_NAME):
        return
    frappe.get_doc({
        "doctype": "Email Template",
        "name": TEMPLATE_NAME,
        "subject": "Missing IN Check-in: {{ date }}",
        "response": "Hi {{ employee_name }}, please mark IN for {{ date }}.",
        "use_html": 1,
    }).insert(ignore_permissions=True)


def _ensure_holiday_list(weekly_offs_only=True):
    if frappe.db.exists("Holiday List", TEST_HOLIDAY_LIST):
        return TEST_HOLIDAY_LIST
    doc = frappe.get_doc({
        "doctype": "Holiday List",
        "holiday_list_name": TEST_HOLIDAY_LIST,
        "from_date": "2026-01-01",
        "to_date": "2026-12-31",
    })
    doc.insert(ignore_permissions=True)
    return doc.name


def _make_employee(suffix, *, email_kind="prefered",
                   joining="2026-01-01", relieving=None,
                   holiday_list=None, status="Active"):
    """Create or reuse an Employee with controlled email + dates.

    email_kind: 'prefered' | 'company' | 'user_id' | 'none'
    """
    eid = f"{TEST_EMPLOYEE_PREFIX}{suffix}"
    name = frappe.db.get_value("Employee", {"custom_employee_id": eid}, "name")
    if name:
        frappe.delete_doc("Employee", name, force=True, ignore_permissions=True)

    company = _ensure_company()
    doc = {
        "doctype": "Employee",
        "custom_employee_id": eid,
        "first_name": "Test",
        "last_name": suffix,
        "gender": "Male",
        "date_of_birth": "1995-01-01",
        "date_of_joining": joining,
        "company": company,
        "status": status,
        "holiday_list": holiday_list,
    }
    if relieving:
        doc["relieving_date"] = relieving
    if email_kind == "prefered":
        doc["prefered_contact_email"] = "Personal Email"
        doc["personal_email"] = f"{eid.lower()}@example.com"
        doc["prefered_email"] = f"{eid.lower()}@example.com"
    elif email_kind == "company":
        doc["company_email"] = f"{eid.lower()}@company.test"
    elif email_kind == "user_id":
        # rely on stock Administrator user link as placeholder
        doc["user_id"] = "Administrator"
    # 'none' = leave all three blank
    return frappe.get_doc(doc).insert(ignore_permissions=True).name


def _make_checkin(emp, when_iso, log_type="IN"):
    return frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": emp,
        "log_type": log_type,
        "time": when_iso,
    }).insert(ignore_permissions=True).name


def _make_leave(emp, from_date, to_date, *, status="Approved",
                docstatus=1, half_day=0):
    """Create a Leave Application row for testing.

    Uses direct SQL insertion to avoid HRMS validation (Holiday List Assignment,
    calculations, etc.). The missing_in_reminder filter matches both docstatus
    0 and 1, so this is safe for testing purposes.
    """
    from frappe.utils import now_datetime
    leave_type = frappe.db.get_value("Leave Type", {}, "name") or "Casual Leave"

    # Generate a name (Frappe naming convention for Leave Application)
    name = frappe.db.sql(
        "SELECT MAX(CAST(SUBSTR(name, INSTR(name, '-')+1) AS UNSIGNED)) FROM `tabLeave Application` WHERE name LIKE 'HR-LAP-%'",
        as_dict=True,
    )[0]
    max_num = (name.get("MAX(CAST(SUBSTR(name, INSTR(name, '-')+1) AS UNSIGNED))") or 0) + 1
    year = from_date.year
    la_name = f"HR-LAP-{year}-{max_num:05d}"

    # Insert directly via SQL to bypass HRMS validations
    now = now_datetime()
    frappe.db.sql(
        """INSERT INTO `tabLeave Application`
           (name, employee, leave_type, from_date, to_date, status, docstatus,
            half_day, creation, modified, modified_by, owner)
           VALUES (%(name)s, %(emp)s, %(lt)s, %(fd)s, %(td)s, %(st)s, %(ds)s,
                   %(hd)s, %(now)s, %(now)s, 'Administrator', 'Administrator')""",
        {
            "name": la_name,
            "emp": emp,
            "lt": leave_type,
            "fd": from_date,
            "td": to_date,
            "st": status,
            "ds": docstatus,
            "hd": half_day,
            "now": now,
        },
    )
    frappe.db.commit()
    return la_name


def _log_rows(emp, on_date):
    return frappe.db.sql(
        """SELECT status, skip_reason, email_sent_to
           FROM `tabMissing Checkin Reminder Log`
           WHERE employee=%(e)s AND reminder_date=%(d)s
           ORDER BY creation""",
        {"e": emp, "d": on_date},
        as_dict=True,
    )


def _email_queue_count(emp_email):
    return frappe.db.sql(
        """SELECT COUNT(*) AS n FROM `tabEmail Queue` eq
           JOIN `tabEmail Queue Recipient` r ON r.parent = eq.name
           WHERE r.recipient=%(e)s AND DATE(eq.creation)=CURDATE()""",
        {"e": emp_email},
        as_dict=True,
    )[0].n


class TestMissingInReminder(IntegrationTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_template()
        cls.holiday_list = _ensure_holiday_list()
        # A reference "today" we control. Use a weekday w/o holidays.
        cls.today = getdate("2026-05-20")
        cls.cutoff = "2026-05-20 11:00:00"

    def setUp(self):
        # Clear any previous test artefacts for the date.
        frappe.db.delete("Missing Checkin Reminder Log",
                         {"reminder_date": self.today})
        # Clean Leave Applications for the test date (test isolation).
        frappe.db.delete("Leave Application",
                         {"from_date": ("<=", self.today),
                          "to_date": (">=", self.today)})
        # Clean Employee Checkins for the test date (test isolation).
        frappe.db.sql(
            "DELETE FROM `tabEmployee Checkin` WHERE DATE(`time`) = %(d)s",
            {"d": self.today}
        )
        frappe.db.commit()
        # Clean holiday entries for this date from the test list (test isolation).
        hl = frappe.get_doc("Holiday List", self.holiday_list)
        hl.holidays = [h for h in hl.holidays if str(h.holiday_date) != str(self.today)]
        hl.save(ignore_permissions=True)

    def test_no_checkin_sends_email(self):
        """Active employee, no IN, no leave, no holiday → Sent + Email Queue row."""
        emp = _make_employee("noin", email_kind="prefered",
                             holiday_list=self.holiday_list)
        send_missing_in_reminders(on_date=self.today)

        rows = _log_rows(emp, self.today)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "Sent")
        self.assertEqual(rows[0].skip_reason, "none")
        self.assertTrue(rows[0].email_sent_to)
        self.assertGreaterEqual(_email_queue_count(rows[0].email_sent_to), 1)

    def test_holiday_skips(self):
        """Date on Employee's holiday_list → Skipped(holiday), no email."""
        # Seed a Holiday row on the test holiday list for our date.
        hl = frappe.get_doc("Holiday List", self.holiday_list)
        already = [h for h in hl.holidays if str(h.holiday_date) == str(self.today)]
        if not already:
            hl.append("holidays", {
                "holiday_date": self.today,
                "description": "MCR test holiday",
            })
            hl.save(ignore_permissions=True)

        emp = _make_employee("hol", email_kind="prefered",
                             holiday_list=self.holiday_list)
        send_missing_in_reminders(on_date=self.today)

        rows = _log_rows(emp, self.today)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "Skipped")
        self.assertEqual(rows[0].skip_reason, "holiday")

    def test_holiday_via_company_default_list(self):
        """Employee has no holiday_list; Company.default_holiday_list has the date → skip."""
        # Use the same TEST_HOLIDAY_LIST as company default for this test.
        company = _ensure_company()
        previous = frappe.db.get_value("Company", company, "default_holiday_list")
        frappe.db.set_value("Company", company, "default_holiday_list",
                            self.holiday_list)
        try:
            # Seed the holiday for this test (since setUp cleans them).
            hl = frappe.get_doc("Holiday List", self.holiday_list)
            already = [h for h in hl.holidays if str(h.holiday_date) == str(self.today)]
            if not already:
                hl.append("holidays", {
                    "holiday_date": self.today,
                    "description": "MCR test holiday (company default)",
                })
                hl.save(ignore_permissions=True)

            emp = _make_employee("holco", email_kind="prefered",
                                 holiday_list=None)
            send_missing_in_reminders(on_date=self.today)
            rows = _log_rows(emp, self.today)
            self.assertEqual(rows[0].skip_reason, "holiday")
        finally:
            frappe.db.set_value("Company", company,
                                "default_holiday_list", previous)

    def test_approved_fullday_leave_skips(self):
        emp = _make_employee("leave_full", email_kind="prefered",
                             holiday_list=self.holiday_list)
        _make_leave(emp, self.today, self.today, status="Approved", docstatus=1)
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(rows[0].skip_reason, "leave")

    def test_approved_halfday_leave_skips(self):
        emp = _make_employee("leave_half", email_kind="prefered",
                             holiday_list=self.holiday_list)
        _make_leave(emp, self.today, self.today, status="Approved",
                    docstatus=1, half_day=1)
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(rows[0].skip_reason, "leave")

    def test_open_pending_leave_skips(self):
        emp = _make_employee("leave_open", email_kind="prefered",
                             holiday_list=self.holiday_list)
        _make_leave(emp, self.today, self.today, status="Open", docstatus=0)
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(rows[0].skip_reason, "leave")

    def test_in_at_1059_no_email(self):
        emp = _make_employee("in1059", email_kind="prefered",
                             holiday_list=self.holiday_list)
        _make_checkin(emp, f"{self.today} 10:59:00", log_type="IN")
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(rows[0].skip_reason, "already_checked_in")

    def test_in_at_1101_still_sends(self):
        """IN logged at 11:01 — after cutoff — does not suppress this run."""
        emp = _make_employee("in1101", email_kind="prefered",
                             holiday_list=self.holiday_list)
        _make_checkin(emp, f"{self.today} 11:01:00", log_type="IN")
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(rows[0].status, "Sent")

    def test_out_only_sends(self):
        emp = _make_employee("outonly", email_kind="prefered",
                             holiday_list=self.holiday_list)
        _make_checkin(emp, f"{self.today} 09:15:00", log_type="OUT")
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(rows[0].status, "Sent")

    def test_multiple_ins_first_one_counts(self):
        emp = _make_employee("multiin", email_kind="prefered",
                             holiday_list=self.holiday_list)
        _make_checkin(emp, f"{self.today} 09:00:00", log_type="IN")
        _make_checkin(emp, f"{self.today} 10:00:00", log_type="IN")
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(rows[0].skip_reason, "already_checked_in")

    def test_missing_email_skips_and_logs(self):
        """Employee with no email (all three blank) → Skipped(missing_email), no send."""
        emp = _make_employee("noemail", email_kind="none",
                             holiday_list=self.holiday_list)
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "Skipped")
        self.assertEqual(rows[0].skip_reason, "missing_email")
        self.assertIsNone(rows[0].email_sent_to)

    def test_rerun_same_day_no_duplicate(self):
        """Running send_missing_in_reminders twice on same day → only 1 Sent row."""
        emp = _make_employee("rerun", email_kind="prefered",
                             holiday_list=self.holiday_list)
        send_missing_in_reminders(on_date=self.today)
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        sent_rows = [r for r in rows if r.status == "Sent"]
        self.assertEqual(len(sent_rows), 1)

    def test_rerun_after_leave_retracted_sends(self):
        """Leave approved → reminder skipped. Leave deleted → re-run sends email."""
        emp = _make_employee("retract", email_kind="prefered",
                             holiday_list=self.holiday_list)
        la = _make_leave(emp, self.today, self.today,
                         status="Approved", docstatus=1)
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(rows[0].skip_reason, "leave")

        # Delete the leave (simulating retraction/cancellation)
        frappe.db.delete("Leave Application", la)
        frappe.db.commit()

        # Re-run the cron — should now send because leave is gone
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        statuses = [r.status for r in rows]
        self.assertIn("Skipped", statuses)  # First run skipped due to leave
        self.assertIn("Sent", statuses)     # Second run sent

    def test_template_missing_aborts_silently(self):
        """When Email Template missing, cron checks and exits → no log rows written."""
        emp = _make_employee("notmpl", email_kind="prefered",
                             holiday_list=self.holiday_list)
        # Temporarily rename the template to simulate it being missing
        frappe.rename_doc(
            "Email Template", TEMPLATE_NAME,
            f"{TEMPLATE_NAME} TEMP", force=True,
        )
        try:
            send_missing_in_reminders(on_date=self.today)
            rows = _log_rows(emp, self.today)
            # No log rows because the cron exits early when template missing
            self.assertEqual(len(rows), 0)
        finally:
            # Restore the template
            frappe.rename_doc(
                "Email Template", f"{TEMPLATE_NAME} TEMP",
                TEMPLATE_NAME, force=True,
            )

    def test_joins_today_included(self):
        """Employee joining today is included (not filtered by date_of_joining)."""
        emp = _make_employee("joinedtoday", email_kind="prefered",
                             holiday_list=self.holiday_list,
                             joining=str(self.today))
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "Sent")

    def test_relieving_today_included(self):
        """Employee relieving today is included (relieving_date >= on_date)."""
        emp = _make_employee("relievtoday", email_kind="prefered",
                             holiday_list=self.holiday_list,
                             relieving=str(self.today))
        send_missing_in_reminders(on_date=self.today)
        rows = _log_rows(emp, self.today)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "Sent")

    # ----- Opt-out toggles (B.1 / B.2 / B.3) ---------------------------------

    def test_per_employee_opt_out_logs_skipped(self):
        """custom_send_checkin_reminder=0 → Skipped(opt_out), no email."""
        emp = _make_employee("optout", email_kind="prefered",
                             holiday_list=self.holiday_list)
        frappe.db.set_value("Employee", emp,
                            "custom_send_checkin_reminder", 0)
        frappe.db.commit()

        send_missing_in_reminders(on_date=self.today)

        rows = _log_rows(emp, self.today)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "Skipped")
        self.assertEqual(rows[0].skip_reason, "opt_out")
        self.assertIsNone(rows[0].email_sent_to)

    def test_per_employee_opt_in_default_sends(self):
        """Fresh Employee (Custom Field default=1) → still sends."""
        emp = _make_employee("optin_default", email_kind="prefered",
                             holiday_list=self.holiday_list)
        # No flag mutation — rely on the Custom Field default.
        send_missing_in_reminders(on_date=self.today)

        rows = _log_rows(emp, self.today)
        self.assertEqual(rows[0].status, "Sent")

    def test_global_toggle_off_short_circuits(self):
        """HR Settings.custom_enable_checkin_reminder=0 → zero log rows."""
        emp = _make_employee("globaloff", email_kind="prefered",
                             holiday_list=self.holiday_list)
        previous = frappe.db.get_single_value(
            "HR Settings", "custom_enable_checkin_reminder")
        frappe.db.set_single_value(
            "HR Settings", "custom_enable_checkin_reminder", 0)
        frappe.db.commit()
        try:
            send_missing_in_reminders(on_date=self.today)
            rows = _log_rows(emp, self.today)
            self.assertEqual(len(rows), 0)
        finally:
            frappe.db.set_single_value(
                "HR Settings", "custom_enable_checkin_reminder",
                1 if previous is None else previous)
            frappe.db.commit()

    def test_dedup_wins_over_opt_out(self):
        """Already-Sent row dedup wins; flipping opt_out later writes nothing."""
        emp = _make_employee("dedup_optout", email_kind="prefered",
                             holiday_list=self.holiday_list)
        send_missing_in_reminders(on_date=self.today)
        # Now flip the opt-out off and re-run — dedup should short-circuit.
        frappe.db.set_value("Employee", emp,
                            "custom_send_checkin_reminder", 0)
        frappe.db.commit()
        send_missing_in_reminders(on_date=self.today)

        rows = _log_rows(emp, self.today)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "Sent")
