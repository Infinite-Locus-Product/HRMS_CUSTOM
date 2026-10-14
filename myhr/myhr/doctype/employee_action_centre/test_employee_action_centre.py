# Copyright (c) 2026, Abhay Nain and Contributors
# See license.txt

import json
import frappe
from frappe.tests.utils import FrappeTestCase


def _get_or_create_test_user(email):
    """Build/reuse a User row for tests. Returns the user name (email)."""
    if frappe.db.exists("User", email):
        return email
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": "AC",
        "last_name": "Tester",
        "send_welcome_email": 0,
        "user_type": "System User",
    })
    user.insert(ignore_permissions=True)
    return email


def _get_or_create_test_employee(user_email):
    """Build/reuse an Employee linked to a test user. Returns the employee name."""
    existing = frappe.db.get_value("Employee", {"user_id": user_email}, "name")
    if existing:
        return existing
    company = frappe.defaults.get_user_default("Company") or frappe.db.get_value("Company", {}, "name")
    emp = frappe.get_doc({
        "doctype": "Employee",
        "first_name": "AC",
        "last_name": "Tester",
        "user_id": user_email,
        "company": company,
        "date_of_joining": frappe.utils.today(),
        "date_of_birth": "1990-01-01",
        "gender": "Other",
        "status": "Active",
    })
    emp.insert(ignore_permissions=True)
    return emp.name


def _get_or_create_test_ac(employee_name):
    """Build/reuse an EAC for a test employee. Returns the AC name."""
    existing = frappe.db.get_value("Employee Action Centre", {"employee": employee_name}, "name")
    if existing:
        return existing
    ac = frappe.get_doc({
        "doctype": "Employee Action Centre",
        "employee": employee_name,
    })
    ac.insert(ignore_permissions=True)
    return ac.name


class TestEmployeeActionCentre(FrappeTestCase):
    def test_custom_last_saved_at_field_exists(self):
        meta = frappe.get_meta("Employee Action Centre")
        f = meta.get_field("custom_last_saved_at")
        self.assertIsNotNone(f, "custom_last_saved_at must exist on Employee Action Centre")
        self.assertEqual(f.fieldtype, "Datetime")
        self.assertEqual(f.read_only, 1)
        self.assertEqual(f.no_copy, 1)

    def test_save_draft_persists_partial(self):
        from myhr.api import save_action_centre_draft

        user = _get_or_create_test_user("ac_persist@test.local")
        emp = _get_or_create_test_employee(user)
        ac = _get_or_create_test_ac(emp)

        frappe.set_user(user)
        try:
            res = save_action_centre_draft(
                name=ac,
                payload=json.dumps({"aadhar_number": "123456789012"}),
            )
        finally:
            frappe.set_user("Administrator")

        self.assertTrue(res["ok"])
        reloaded = frappe.get_doc("Employee Action Centre", ac)
        self.assertEqual(reloaded.aadhar_number, "123456789012")
        self.assertIsNotNone(reloaded.custom_last_saved_at)

    def test_save_draft_skips_validate(self):
        """Save with empty mandatory-after-fill state succeeds — validate is bypassed."""
        from myhr.api import save_action_centre_draft

        user = _get_or_create_test_user("ac_skip@test.local")
        emp = _get_or_create_test_employee(user)
        ac = _get_or_create_test_ac(emp)

        frappe.set_user(user)
        try:
            res = save_action_centre_draft(name=ac, payload=json.dumps({"aadhar_number": ""}))
        finally:
            frappe.set_user("Administrator")

        self.assertTrue(res["ok"])

    def test_save_draft_rejects_after_submit(self):
        from myhr.api import save_action_centre_draft

        user = _get_or_create_test_user("ac_locked_submit@test.local")
        emp = _get_or_create_test_employee(user)
        ac = _get_or_create_test_ac(emp)

        frappe.db.set_value("Employee Action Centre", ac, {
            "submitted_for_review": 1,
            "submitted_on": frappe.utils.now_datetime(),
            "submitted_by": user,
        })
        frappe.db.commit()

        frappe.set_user(user)
        try:
            with self.assertRaises(frappe.ValidationError) as ctx:
                save_action_centre_draft(name=ac, payload=json.dumps({"aadhar_number": "999"}))
            self.assertIn("locked", str(ctx.exception).lower())
        finally:
            frappe.set_user("Administrator")

    def test_save_draft_rejects_when_accepted(self):
        from myhr.api import save_action_centre_draft

        user = _get_or_create_test_user("ac_locked_accepted@test.local")
        emp = _get_or_create_test_employee(user)
        ac = _get_or_create_test_ac(emp)

        frappe.db.set_value("Employee Action Centre", ac, "status", "Accepted")
        frappe.db.commit()

        frappe.set_user(user)
        try:
            with self.assertRaises(frappe.ValidationError) as ctx:
                save_action_centre_draft(name=ac, payload=json.dumps({"aadhar_number": "999"}))
            self.assertIn("locked", str(ctx.exception).lower())
        finally:
            frappe.set_user("Administrator")

    def test_save_draft_permission_denied_for_non_owner(self):
        from myhr.api import save_action_centre_draft

        owner_user = _get_or_create_test_user("ac_owner@test.local")
        owner_emp = _get_or_create_test_employee(owner_user)
        ac = _get_or_create_test_ac(owner_emp)

        intruder_user = _get_or_create_test_user("ac_intruder@test.local")
        _get_or_create_test_employee(intruder_user)

        frappe.set_user(intruder_user)
        try:
            with self.assertRaises(frappe.PermissionError):
                save_action_centre_draft(name=ac, payload=json.dumps({"aadhar_number": "999"}))
        finally:
            frappe.set_user("Administrator")

    def test_save_draft_filters_restricted_fields(self):
        """Approval-status fields are HR-only and must NOT be writable from save_draft."""
        from myhr.api import save_action_centre_draft

        user = _get_or_create_test_user("ac_filter@test.local")
        emp = _get_or_create_test_employee(user)
        ac = _get_or_create_test_ac(emp)

        original_status = frappe.db.get_value("Employee Action Centre", ac, "aadhar_approval_status")

        frappe.set_user(user)
        try:
            save_action_centre_draft(
                name=ac,
                payload=json.dumps({
                    "aadhar_number": "111111111111",
                    "aadhar_approval_status": "Accepted",
                    "aadhar_remarks": "I am HR",
                    "submitted_for_review": 1,
                }),
            )
        finally:
            frappe.set_user("Administrator")

        reloaded = frappe.get_doc("Employee Action Centre", ac)
        self.assertEqual(reloaded.aadhar_number, "111111111111")
        self.assertEqual(reloaded.aadhar_approval_status, original_status)
        self.assertNotEqual(reloaded.aadhar_remarks, "I am HR")
        self.assertEqual(reloaded.submitted_for_review, 0)

    def test_save_draft_updates_last_saved_at(self):
        """Two consecutive saves bump the timestamp."""
        import time
        from myhr.api import save_action_centre_draft

        user = _get_or_create_test_user("ac_ts@test.local")
        emp = _get_or_create_test_employee(user)
        ac = _get_or_create_test_ac(emp)

        frappe.set_user(user)
        try:
            save_action_centre_draft(name=ac, payload=json.dumps({"aadhar_number": "1"}))
            first = frappe.db.get_value("Employee Action Centre", ac, "custom_last_saved_at")
            time.sleep(1.1)
            save_action_centre_draft(name=ac, payload=json.dumps({"aadhar_number": "2"}))
            second = frappe.db.get_value("Employee Action Centre", ac, "custom_last_saved_at")
        finally:
            frappe.set_user("Administrator")

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertGreater(second, first)

    def test_get_employee_action_centre_exposes_summary_fields(self):
        """Home card needs submitted_for_review, status, custom_last_saved_at, name at top level."""
        from myhr.api import get_employee_action_centre

        user = _get_or_create_test_user("ac_home_summary@test.local")
        emp = _get_or_create_test_employee(user)
        _get_or_create_test_ac(emp)

        frappe.set_user(user)
        try:
            res = get_employee_action_centre()
        finally:
            frappe.set_user("Administrator")

        self.assertNotIn("error", res)
        for key in ("submitted_for_review", "status", "custom_last_saved_at", "name"):
            self.assertIn(key, res, f"Missing top-level field: {key}")

    def test_save_draft_coerces_empty_strings_for_date_fields(self):
        """Empty string for a Date field must be coerced to NULL — MariaDB rejects ''."""
        from myhr.api import save_action_centre_draft

        user = _get_or_create_test_user("ac_date_coerce@test.local")
        emp = _get_or_create_test_employee(user)
        ac = _get_or_create_test_ac(emp)

        frappe.set_user(user)
        try:
            res = save_action_centre_draft(
                name=ac,
                payload=json.dumps({
                    "employer_1_from": "",
                    "employer_1_till": "",
                    "employer_1_name": "",     # Data field — empty string is fine
                    "personal_dob": "",        # Date field on EAC
                }),
            )
        finally:
            frappe.set_user("Administrator")

        self.assertTrue(res["ok"])
        # Confirm Date columns are NULL, not '' (which would have raised at write time).
        for fn in ("employer_1_from", "employer_1_till", "personal_dob"):
            v = frappe.db.get_value("Employee Action Centre", ac, fn)
            self.assertIsNone(v, f"{fn} should be NULL after empty-string save, got {v!r}")
