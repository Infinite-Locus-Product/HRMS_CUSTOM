app_name = "myhr"
app_title = "myHR"
app_publisher = "Abhay Nain"
app_description = "Custom HRMS Extensions"
app_email = "abhay.nain@example.com"
app_license = "mit"

# DocType JS overrides
doctype_js = {
    "Employee": "public/js/employee.js",
    # Appointment Letter: filter/preselect the linked Job Offer (custom_job_offer)
    "Appointment Letter": "public/js/appointment_letter.js",
    # Pre-fills the Expected Skillset of a new Interview Type with the default competencies
    "Interview Type": "public/js/interview_type.js",
    # Stage A resignation: relieving-date default + Detailed Reason char counter
    "Employee Separation": "public/js/employee_separation.js",
    # Stage 8: the Release Relieving Letter button (nothing else triggers one)
    "Separation HR Clearance": "public/js/separation_hr_clearance.js",
}

# ---------------------------------------------------------------------------
# Install / Migrate hooks — roles + permissions set automatically
# ---------------------------------------------------------------------------
after_install = "myhr.setup.after_install"
after_migrate = "myhr.setup.after_migrate"

# Fixtures for portability (exported via `bench export-fixtures`)
# NOTE: Most Custom Fields are created programmatically in setup.py with
# skip-if-exists logic (see MYHR_CUSTOM_FIELDS). The exception is Job Applicant:
# Job Opening and Job Offer: their fields are declared in fixtures/custom_field.json
# so the recruitment customisations are versioned alongside the schema.
fixtures = [
    {
        "doctype": "Role",
        "filters": [
            ["role_name", "in", ["HR Manager", "HR User", "Employee"]]
        ]
    },
    {
        "doctype": "Custom Field",
        "filters": [
            ["module", "=", "myHR"],
            ["dt", "in", ["Job Applicant", "Job Opening", "Job Offer", "Appointment Letter",
                          "Skill", "Interview Feedback",
                          # Stage A resignation fields (Employee.custom_l2_manager +
                          # the Employee Separation capture block). Safe to widen: the
                          # `module = myHR` filter above excludes every field created by
                          # setup.py:MYHR_CUSTOM_FIELDS, which leaves module unset.
                          "Employee", "Employee Separation", "HR Settings",
                          "Full and Final Statement"]],
        ]
    },
    # Employee Separation two-step approval (L1 Reporting Manager -> L2 Function
    # Head). The Workflow row carries its own states/transitions as child tables;
    # the two masters below must exist before it imports.
    {
        "doctype": "Workflow State",
        "filters": [
            ["name", "in", ["Draft", "Pending L1 Approval", "Pending L2 Approval",
                            "Rejected", "Approved",
                            "Pending Manager Clearance", "Complete"]],
        ]
    },
    {
        "doctype": "Workflow Action Master",
        "filters": [
            ["name", "in", ["Submit", "Approve", "Reject", "Resubmit", "Complete"]],
        ]
    },
    {
        "doctype": "Workflow",
        "filters": [
            ["document_type", "in", ["Employee Separation", "Separation Manager Clearance"]],
        ]
    },
]

override_doctype_class = {
	"Leave Application": "myhr.overrides.leave_application.LeaveApplication",
	"Employee Checkin": "myhr.overrides.employee_checkin.EmployeeCheckin",
	"Expense Claim": "myhr.overrides.expense_claim.ExpenseClaim",
}

# Document Events
doc_events = {
    "Job Applicant": {
        "validate": "myhr.job_applicant_hooks.validate",
    },
    "Job Opening": {
        "validate": "myhr.job_opening_hooks.validate",
    },
    "Job Offer": {
        "validate": "myhr.job_offer_hooks.validate",
    },
    # Stage 9 — extends HRMS's own Full and Final Statement rather than
    # replacing it: it already seeds payables/receivables and posts the
    # Journal Entry. myHR adds the exit-flow recoveries, the net, and the gates.
    "Full and Final Statement": {
        # onload too: the statement is raised before the clearances are filled
        # in, so without it Finance opens one showing nothing to recover.
        "onload": "myhr.full_and_final_hooks.onload",
        "validate": "myhr.full_and_final_hooks.validate",
        "before_submit": "myhr.full_and_final_hooks.before_submit",
    },
    # Keeps the HR clearance's view of the interview current. The clearance is
    # raised before the interview exists, so it cannot rely on its own save.
    "Exit Interview": {
        "on_update": "myhr.exit_interview_hooks.sync_to_clearance",
        "on_submit": "myhr.exit_interview_hooks.sync_to_clearance",
        "on_cancel": "myhr.exit_interview_hooks.sync_to_clearance",
    },
    "Employee Separation": {
        "validate": "myhr.employee_separation_hooks.validate",
        # Final approval mirrors the relieving date onto the Employee record —
        # HRMS needs it before an Exit Interview can exist.
        "on_submit": "myhr.employee_separation_hooks.on_submit",
        "on_cancel": "myhr.employee_separation_hooks.on_cancel",
    },
    "Employee": {
        "validate": [
            "myhr.employee_master_data.validate_master_data",
            "myhr.employee_hooks.validate_employee",
        ],
        "after_insert": [
            "myhr.employee_master_data.after_insert_master_data",
            "myhr.employee_hooks.after_employee_insert",
            "myhr.policy_hooks.reconcile_after_employee_insert",
        ],
        "on_update": [
            "myhr.employee_master_data.on_update_master_data",
            "myhr.employee_hooks.on_update_employee",
            "myhr.policy_hooks.reconcile_on_employee_update",
        ],
        "on_trash": "myhr.employee_hooks.on_trash_employee",
        "after_rename": "myhr.employee_hooks.after_rename_employee",
    },
    # Employee Checkin gates (ownership + policy) are handled inside
    # `myhr.overrides.employee_checkin.EmployeeCheckin.validate()` so they
    # fire BEFORE stock HRMS validations (policy first, then everything else).
    # Do NOT add a doc_events.validate here — it would double-fire the gate.
    "Attendance Request": {
        "validate": "myhr.employee_hooks.validate_attendance_request_policy_gate",
        "before_submit": "myhr.approval_gate.gate_attendance_request_submit",
        "on_submit": "myhr.employee_hooks.notify_employee_on_attendance_request_submit",
        "after_insert": "myhr.hr_review_notifications.notify_hr_managers_on_submit",
    },
    "Leave Application": {
        "validate": "myhr.approval_gate.gate_leave_application_approval",
        "after_insert": "myhr.hr_review_notifications.notify_hr_managers_on_submit",
    },
    "Expense Claim": {
        "validate": "myhr.approval_gate.gate_expense_claim_approval",
        "after_insert": "myhr.hr_review_notifications.notify_hr_managers_on_submit",
    },
    "HR Policy": {
        "validate": "myhr.policy_hooks.validate_hr_policy",
        "on_update": "myhr.policy_hooks.after_save_hr_policy",
        "on_trash": "myhr.policy_hooks.on_trash_hr_policy",
    },
    # Guarantee a notification fires when a Policy Acknowledgement is created
    # via any path — the helper in policy_hooks only covers the seeding paths.
    # Direct PA creation (Desk form / API / script) used to be silent.
    "Policy Acknowledgement": {
        "after_insert": "myhr.policy_notifications.notify_on_pa_creation",
    },
    # HOL-1/2/3: keep Holiday.custom_holiday_type in sync with weekly_off.
    # Both wired — the Holiday List parent validate is the dependable surface
    # (child-doctype doc_events don't reliably fire for table rows); the
    # Holiday hook covers the rare standalone-save path.
    "Holiday": {
        "validate": "myhr.leave_optional_holiday.validate_holiday",
    },
    "Holiday List": {
        "validate": "myhr.leave_optional_holiday.validate_holiday_list",
    },
    # AR-3: lockout guard for the configurable Attendance Request approver
    # toggles. Throws if all three are disabled at once.
    "HR Settings": {
        "validate": "myhr.approval_gate.gate_hr_settings_save",
    },
    # Holiday List Assignment reverse-sync — when an HLA is submitted via Desk,
    # mirror its holiday_list back onto Employee.custom_holiday_list + native
    # holiday_list (uses frappe.db.set_value to avoid Employee.on_update loop).
    "Holiday List Assignment": {
        "on_submit": "myhr.overrides.holiday_list_assignment.on_submit",
    },
    # Auto-fill SSA fields from the Employee record on `before_validate`, so
    # they land BEFORE HRMS's controller validate runs. `validate` would fire
    # too late — HRMS has already thrown (income_tax_slab) or already emitted
    # its "Missing Opening Entries" warning (opening balances) by then.
    "Salary Structure Assignment": {
        "before_validate": [
            "myhr.salary_structure_assignment_hooks.fill_income_tax_slab_from_employee",
            "myhr.salary_structure_assignment_hooks.fill_opening_balances_from_employee",
        ],
    },
}

# Whitelisted APIs are in api.py (auto loaded)

# Employee permission model — see myhr/permissions.py for the rule. This
# replaces the older `create_user_permission` (CUP) approach: HR roles see all,
# everyone else sees self (+ direct reports if custom_allow_view_reporting=1).
permission_query_conditions = {
    "Employee": "myhr.permissions.employee_permission_query_conditions",
    # An employee sees only their own resignation; L1/L2 see the ones naming them.
    "Employee Separation": "myhr.permissions.employee_separation_query_conditions",
    # Same rule for the clearance: the leaver and their manager, nobody else.
    "Separation Manager Clearance": "myhr.permissions.separation_manager_clearance_query_conditions",
    "Separation IT Clearance": "myhr.permissions.separation_it_clearance_query_conditions",
    "Separation HR Clearance": "myhr.permissions.separation_hr_clearance_query_conditions",
}

has_permission = {
    "Employee": "myhr.permissions.has_employee_permission",
    "Employee Separation": "myhr.permissions.has_employee_separation_permission",
    "Separation Manager Clearance": "myhr.permissions.has_separation_manager_clearance_permission",
    "Separation IT Clearance": "myhr.permissions.has_separation_it_clearance_permission",
    "Separation HR Clearance": "myhr.permissions.has_separation_hr_clearance_permission",
}

# Re-route HRMS Team Requests endpoints through myhr so:
#   - HR Managers see all open Leave Applications and all draft Attendance
#     Requests, regardless of who is the named approver / reports-to manager.
#   - Non-HR users see only their reports' Attendance Requests (HRMS default
#     was permissive — everyone saw all drafts).
override_whitelisted_methods = {
    "hrms.api.get_leave_applications": "myhr.api.get_leave_applications",
    "hrms.api.get_attendance_requests": "myhr.api.get_attendance_requests",
    "hrms.api.get_expense_claims": "myhr.api.get_expense_claims",
}

scheduler_events = {
    "cron": {
        "0 9 * * 1-5": ["myhr.employee_hooks.auto_present_in"],
        "0 18 * * 1-5": ["myhr.employee_hooks.auto_present_out"],
        # 23:55 daily — covers the "IN-only, mark Present" Shift Type toggle
        # by inserting a 23:59 OUT for any qualifying employee. HRMS's hourly
        # auto-attendance sweep then converts the IN+OUT pair into a Present
        # Attendance row.
        "55 23 * * *": ["myhr.attendance_eod_checkout.auto_checkout_at_eod"],
        # 11:00 daily — email reminder to employees missing IN Checkin.
        "0 11 * * *": ["myhr.missing_in_reminder.send_missing_in_reminders"],
    },
    # E-3: hourly reminder for stale Pending mandatory PAs (>=24h old). The
    # function de-dupes against Notification Log so users see at most one
    # ping every REMINDER_RE_PING_HOURS.
    "hourly": [
        "myhr.policy_notifications.send_pending_policy_reminders",
    ],
}
