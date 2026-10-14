"""
myHR app setup — runs on after_install and after_migrate.
Ensures all required roles exist and Employee Directory permissions are correct.
No manual ERPNext configuration needed.
"""

import os

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


# ---------------------------------------------------------------------------
# Roles managed by myHR
# ---------------------------------------------------------------------------
MYHR_ROLES = [
    {
        "role_name": "HR Manager",
        "desk_access": 1,
        "description": "Full access to HR documents and Employee Directory.",
    },
    {
        "role_name": "HR User",
        "desk_access": 1,
        "description": "Read access to all HR documents and Employee Directory.",
    },
    {
        "role_name": "Employee",
        "desk_access": 0,
        "description": "Portal access — sees only own Employee Directory record.",
    },
]

# DocType → list of permission rows to enforce
MYHR_PERMISSIONS = {
    "Employee Directory": [
        {
            "role": "System Manager",
            "read": 1, "write": 1, "create": 1, "delete": 1,
            "export": 1, "print": 1, "report": 1, "share": 1,
        },
        {
            "role": "HR Manager",
            "read": 1, "write": 1, "create": 1, "delete": 1,
            "export": 1, "print": 1, "report": 1, "share": 1,
        },
        {
            "role": "HR User",
            "read": 1, "write": 0, "create": 0, "delete": 0,
            "export": 1, "print": 1, "report": 1, "share": 0,
        },
        {
            "role": "Employee",
            "read": 1, "write": 0, "create": 0, "delete": 0,
            "export": 0, "print": 0, "report": 0, "share": 0,
        },
    ]
}

# Doctypes where myHR ADDS a perm row without wiping the rest of stock HRMS
# perms. (`MYHR_PERMISSIONS` above replaces all rows — that's wrong for stock
# doctypes like Attendance Request where we just need to extend a single role.)
MYHR_ADDITIVE_PERMISSIONS = {
    "Attendance Request": [
        {
            # Stock HRMS doesn't grant Leave Approver any perm on Attendance
            # Request — but myhr's RBAC model uses Employee.leave_approver as
            # the named manager who approves AR. Without this row, named
            # managers get PermissionError on submit even though the
            # myhr.approval_gate would allow them.
            "role": "Leave Approver",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 0, "delete": 0,
            "submit": 1, "cancel": 1, "amend": 0, "if_owner": 0,
        },
    ],
    "Exit Interview": [
        {
            # Stock HRMS ships Exit Interview as submittable but grants submit
            # to NOBODY — so only Administrator could ever submit one. The HR
            # clearance gate requires a submitted interview (a draft can claim
            # "Completed" with nothing done), which made the relieving letter
            # unreleasable. Cancel comes too: without it a mistakenly submitted
            # interview could not be corrected by anyone but Administrator.
            "role": "HR Manager",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1,
            "submit": 1, "cancel": 1,
        },
    ],
    "Employee Separation": [
        {
            # Stock HRMS grants this doctype to System Manager / HR Manager /
            # HR User only, so an employee cannot raise their own resignation
            # and a reporting manager cannot open one to approve it. `submit`
            # is needed because the workflow submits the document when L2
            # approves, and the acting user is the L2 manager.
            #
            # if_owner stays 0 on purpose: L1 and L2 are not the owner but must
            # read the record. The narrowing to "only the three people this
            # record concerns" is done by
            # myhr.permissions.employee_separation_query_conditions and its
            # has_permission twin, NOT by this row.
            "role": "Employee",
            "permlevel": 0,
            "read": 1, "write": 1, "create": 1, "delete": 0,
            "submit": 1, "cancel": 0, "amend": 0, "if_owner": 0,
        },
    ],
}


def after_install():
    _setup()
    # Build the PWA bundle on first install too — without this, the employee
    # /hrms route renders the stock HRMS UI until the next migrate. Same
    # non-fatal wrapper as after_migrate; respects MYHR_SKIP_FRONTEND_SYNC.
    _apply_custom_ui_safe()


def after_migrate():
    _setup()
    _apply_custom_ui_safe()


def _apply_custom_ui_safe():
    """Run HRMS frontend sync (overlay copy + yarn build + service-worker
    refresh). Called from both after_install and after_migrate so the PWA
    always reflects the current backend.

    Failures are logged and do NOT abort the install / migrate — yarn may
    not be on PATH on a CI host. Set MYHR_SKIP_FRONTEND_SYNC=1 to bypass
    the build entirely; in that case run the sync standalone via
    `bench --site <s> execute myhr.frontend_sync.apply_custom_ui` on a
    host that has yarn.
    """
    if os.environ.get("MYHR_SKIP_FRONTEND_SYNC", "").strip() in ("1", "true", "yes"):
        frappe.logger().info("myHR: skipping frontend sync (MYHR_SKIP_FRONTEND_SYNC)")
        return
    try:
        from myhr.frontend_sync import apply_custom_ui

        apply_custom_ui()
    except Exception:
        frappe.log_error(
            title="myHR: apply_custom_ui failed",
            message=frappe.get_traceback(),
        )


def _setup():
    _ensure_roles()
    _enforce_permissions()
    _ensure_additive_permissions()
    _ensure_employee_perm_lockdown()
    _ensure_leave_application_status_property_setter()
    _ensure_attendance_request_employee_ignore_user_permissions()
    _ensure_ssa_opening_balances_visible()
    _ensure_employee_leave_approver_labels()
    _ensure_custom_fields()
    _apply_elixiir_property_setters()
    _apply_elixiir_hr_only_permlevels()
    _apply_elixiir_mandatory_fields()
    _ensure_elixiir_hr_manager_permlevel_perm()
    _ensure_holiday_type_options()
    _seed_ar_approver_defaults()
    _seed_ec_approver_defaults()
    _seed_ac_payslip_mandatory_defaults()
    _repair_ac_payslip_field_attrs()
    _seed_ac_payslip_show_defaults()
    _ensure_employee_welcome_notification()
    _ensure_default_competencies()
    _ensure_access_revocation_systems()
    _ensure_it_asset_types()
    frappe.db.commit()
    frappe.clear_cache()


# The six universal competencies from the Fixxly HRMS Interview Feedback
# Questionnaire. Seeded as Skill records and flagged `custom_is_default_competency`,
# which is what `public/js/interview_type.js` pre-fills a new Interview Type from.
# From there stock HRMS copies them into every Interview Feedback's Skill Assessment.
DEFAULT_COMPETENCIES = (
    (
        "Role Knowledge & Execution",
        "Demonstrates essential technical/functional capability and understanding required for the position.",
    ),
    (
        "Problem-Solving & Critical Thinking",
        "Analyzes situations effectively, breaks down complex problems, and delivers pragmatic solutions.",
    ),
    (
        "Communication & Clarity",
        "Articulates ideas clearly, listens actively, and conveys technical/business concepts logically.",
    ),
    (
        "Teamwork & Interpersonal Alignment",
        "Collaborates productively, manages cross-functional interactions, and works well with diverse teams.",
    ),
    (
        "Adaptability & Growth Mindset",
        "Responds positively to feedback, embraces changes, and displays eagerness to learn and grow.",
    ),
    (
        "Cultural Alignment & Fixxly Values",
        "Demonstrates accountability, ownership, initiative, and alignment with Fixxly's core operating values.",
    ),
)


# Starting list for Separation Manager Clearance's access-revocation field.
# Seeded, NOT shipped as a fixture: HR maintains this list, and a fixture would
# overwrite their additions on every migrate. Seed-if-missing leaves them alone.
DEFAULT_ACCESS_REVOCATION_SYSTEMS = (
    "Project Repositories",
    "JIRA",
    "Drive Folders",
    "Shared Drives",
)


# Starting hardware list for Separation IT Clearance. Seeded, not fixtured, for
# the same reason as the access-revocation systems: IT maintains it.
DEFAULT_IT_ASSET_TYPES = (
    "Laptop",
    "Charger",
    "Adapter",
    "Monitors",
    "Mobile",
    "Access Card",
)


def _ensure_it_asset_types():
    if not frappe.db.exists("DocType", "IT Asset Type"):
        return
    for asset_type_name in DEFAULT_IT_ASSET_TYPES:
        if frappe.db.exists("IT Asset Type", asset_type_name):
            continue
        frappe.get_doc(
            {"doctype": "IT Asset Type", "asset_type_name": asset_type_name, "is_active": 1}
        ).insert(ignore_permissions=True)
        frappe.logger().info(f"myHR: Seeded IT Asset Type '{asset_type_name}'.")


def _ensure_access_revocation_systems():
    if not frappe.db.exists("DocType", "Access Revocation System"):
        return
    for system_name in DEFAULT_ACCESS_REVOCATION_SYSTEMS:
        if frappe.db.exists("Access Revocation System", system_name):
            continue
        frappe.get_doc(
            {"doctype": "Access Revocation System", "system_name": system_name, "is_active": 1}
        ).insert(ignore_permissions=True)
        frappe.logger().info(f"myHR: Seeded Access Revocation System '{system_name}'.")


def _ensure_default_competencies():
    """Seed the six standard interview competencies as Skill records.

    Skip-if-exists on the Skill name, so HR edits to an existing description are
    never overwritten. The `custom_is_default_competency` flag is only set on
    creation — unticking one to retire it from the pre-fill is a deliberate HR
    action and must survive the next migrate.
    """
    if not frappe.db.has_column("Skill", "custom_is_default_competency"):
        return  # custom field not created yet (pre-migrate run)

    created = 0
    for skill_name, description in DEFAULT_COMPETENCIES:
        if frappe.db.exists("Skill", skill_name):
            continue
        doc = frappe.new_doc("Skill")
        doc.skill_name = skill_name
        doc.description = description
        doc.custom_is_default_competency = 1
        doc.insert(ignore_permissions=True)
        created += 1

    if created:
        print(f"myhr: seeded {created} default interview competency Skill record(s)")


def _ensure_employee_welcome_notification():
    """Seed the welcome-email Notification fired on Employee insert.

    The Notification doctype is HR-editable in Desk. We only create it if it
    doesn't already exist so HR's subject/body edits aren't clobbered on
    every after_migrate. To regenerate from this seed, delete the Notification
    via Desk and re-run `bench migrate`.

    Recipients: tries `user_id`, `personal_email`, `company_email` in that
    order. Frappe gathers all non-empty addresses and dedupes — at least one
    must be set on the Employee at insert time for an email to actually go
    out.
    """
    name = "Employee Welcome"
    if frappe.db.exists("Notification", name):
        return
    if not frappe.db.exists("DocType", "Notification"):
        return

    body = (
        "<p>Dear {{ doc.employee_name }},</p>\n"
        "<p>We are pleased to inform you that your employee account has been "
        "successfully created in our HR management system.</p>\n"
        "<p>You have been added to Frappe HRMS.</p>\n"
        "<p>You can log in using your Microsoft account credentials.</p>\n"
        "<p>Through this platform, you will be able to:</p>\n"
        "<ul>\n"
        "<li>Complete and update your personal details</li>\n"
        "<li>Mark your attendance</li>\n"
        "<li>Apply for leaves</li>\n"
        "<li>Access your organizational and role-related information</li>\n"
        "</ul>\n"
        "<p>The system is also accessible on your mobile device for your "
        "convenience.</p>\n"
        "<p>In case you face any issues while logging in or accessing the "
        "platform, please reach out to the HR team.</p>\n"
        "<p>&nbsp;</p>\n"
        "<p>Best Regards,<br>\nHR Team</p>"
    )

    doc = frappe.get_doc({
        "doctype": "Notification",
        "name": name,
        "subject": "Welcome to Fixxly HRMS — Your Account Is Ready",
        "channel": "Email",
        "enabled": 1,
        "is_standard": 0,
        "document_type": "Employee",
        "event": "New",
        "send_system_notification": 0,
        "message": body,
        "recipients": [
            {"receiver_by_document_field": "user_id"},
            {"receiver_by_document_field": "personal_email"},
            {"receiver_by_document_field": "company_email"},
        ],
    })
    doc.flags.ignore_permissions = True
    doc.insert()
    print(f"myhr: created Notification {name!r} (Employee → New event)")


def _seed_ar_approver_defaults():
    """Seed declared defaults onto the HR Settings AR approver toggles when
    the row is in the broken 'all three zero' state.

    Frappe adds new Check columns to existing singleton rows with the SQL
    default 0 — so the Custom Field's `default: 1` attr on
    `custom_ar_approver_hr_manager` / `custom_ar_approver_leave_approver` never
    materialises on the existing HR Settings row. Without this seed, the AR
    submit gate (which reads these toggles) would deny every path on fresh
    migrates because all three would read as 0.

    Idempotent: only seeds when *all three* are 0. Once the admin has saved
    HR Settings through the form, `gate_hr_settings_save` enforces that at
    least one toggle remain enabled, so all-zero unambiguously means
    'never seeded'.
    """
    if not frappe.db.exists("DocType", "HR Settings"):
        return
    meta = frappe.get_meta("HR Settings")
    fieldnames = {f.fieldname for f in meta.fields}
    needed = {
        "custom_ar_approver_hr_manager",
        "custom_ar_approver_leave_approver",
        "custom_ar_allow_self_submit",
    }
    if not needed.issubset(fieldnames):
        return  # Custom Fields not yet created (e.g., this is a pre-migrate run)

    hr_mgr = frappe.db.get_single_value("HR Settings", "custom_ar_approver_hr_manager")
    leave_app = frappe.db.get_single_value("HR Settings", "custom_ar_approver_leave_approver")
    self_sub = frappe.db.get_single_value("HR Settings", "custom_ar_allow_self_submit")
    if hr_mgr or leave_app or self_sub:
        return  # admin has touched at least one — leave their policy alone

    frappe.db.set_single_value("HR Settings", "custom_ar_approver_hr_manager", 1)
    frappe.db.set_single_value("HR Settings", "custom_ar_approver_leave_approver", 1)
    frappe.db.set_single_value("HR Settings", "custom_ar_allow_self_submit", 0)
    frappe.logger().info("myHR: seeded HR Settings AR approver defaults (1, 1, 0).")


def _seed_ec_approver_defaults():
    """Seed declared defaults onto the HR Settings EC approver toggles when
    the row is in the broken 'all three zero' state.

    Same problem as `_seed_ar_approver_defaults`: when Frappe adds new Check
    columns to the singleton row, the SQL default is 0 — so the Custom Field
    `default: 1` attrs never materialise on existing installs. Without this
    seed, `gate_expense_claim_approval` would deny every path on a fresh
    migrate because all three toggles read as 0.

    Idempotent: only seeds when *all three* are 0. Once an admin has saved
    HR Settings through the form, `gate_hr_settings_save` enforces that at
    least one EC toggle remains enabled, so all-zero unambiguously means
    'never seeded'.
    """
    if not frappe.db.exists("DocType", "HR Settings"):
        return
    meta = frappe.get_meta("HR Settings")
    fieldnames = {f.fieldname for f in meta.fields}
    needed = {
        "custom_ec_approver_hr_manager",
        "custom_ec_approver_designated",
        "custom_ec_approver_accounts_manager",
    }
    if not needed.issubset(fieldnames):
        return  # Custom Fields not yet created (e.g., this is a pre-migrate run)

    hr_mgr = frappe.db.get_single_value("HR Settings", "custom_ec_approver_hr_manager")
    designated = frappe.db.get_single_value("HR Settings", "custom_ec_approver_designated")
    accounts_mgr = frappe.db.get_single_value("HR Settings", "custom_ec_approver_accounts_manager")
    if hr_mgr or designated or accounts_mgr:
        return  # admin has touched at least one — leave their policy alone

    frappe.db.set_single_value("HR Settings", "custom_ec_approver_hr_manager", 1)
    frappe.db.set_single_value("HR Settings", "custom_ec_approver_designated", 1)
    frappe.db.set_single_value("HR Settings", "custom_ec_approver_accounts_manager", 0)


def _seed_ac_payslip_mandatory_defaults():
    """Seed defaults for the 3 Action Centre payslip mandatory toggles.

    Same materialisation issue as the AR / EC seeders: Frappe adds new Check
    columns to the HR Settings singleton row with SQL default 0, ignoring
    the Custom Field `default: 1` attr. Without this seed, fresh migrates
    would silently flip every payslip to OPTIONAL — defeating the original
    'all three required' policy that was hardcoded before this slice.

    Idempotent: only seeds when *all three* read as 0 (the unambiguous
    'never touched' state). Once an admin saves HR Settings via Desk to
    flip any of these, leave their choice alone.
    """
    if not frappe.db.exists("DocType", "HR Settings"):
        return
    meta = frappe.get_meta("HR Settings")
    fieldnames = {f.fieldname for f in meta.fields}
    needed = {
        "custom_ac_require_payslip_last_month",
        "custom_ac_require_payslip_last_to_last_month",
        "custom_ac_require_payslip_month_before_that",
    }
    if not needed.issubset(fieldnames):
        return  # Custom Fields not yet created (pre-migrate run)

    last = frappe.db.get_single_value("HR Settings", "custom_ac_require_payslip_last_month")
    last_to_last = frappe.db.get_single_value(
        "HR Settings", "custom_ac_require_payslip_last_to_last_month"
    )
    before_that = frappe.db.get_single_value(
        "HR Settings", "custom_ac_require_payslip_month_before_that"
    )
    if last or last_to_last or before_that:
        return  # admin has touched at least one — leave their policy alone

    frappe.db.set_single_value("HR Settings", "custom_ac_require_payslip_last_month", 1)
    frappe.db.set_single_value(
        "HR Settings", "custom_ac_require_payslip_last_to_last_month", 1
    )
    frappe.db.set_single_value(
        "HR Settings", "custom_ac_require_payslip_month_before_that", 1
    )
    frappe.logger().info(
        "myHR: seeded HR Settings AC payslip mandatory defaults (1, 1, 1)."
    )


def _seed_ac_payslip_show_defaults():
    """Seed defaults for the 3 'Show in PWA' payslip toggles. Same all-zero
    materialisation issue as the require seeders. Idempotent — only seeds
    when all three are 0 (the unambiguous 'never touched' state)."""
    if not frappe.db.exists("DocType", "HR Settings"):
        return
    meta = frappe.get_meta("HR Settings")
    fieldnames = {f.fieldname for f in meta.fields}
    needed = {
        "custom_ac_show_payslip_last_month",
        "custom_ac_show_payslip_last_to_last_month",
        "custom_ac_show_payslip_month_before_that",
    }
    if not needed.issubset(fieldnames):
        return

    last = frappe.db.get_single_value("HR Settings", "custom_ac_show_payslip_last_month")
    last_to_last = frappe.db.get_single_value(
        "HR Settings", "custom_ac_show_payslip_last_to_last_month"
    )
    before_that = frappe.db.get_single_value(
        "HR Settings", "custom_ac_show_payslip_month_before_that"
    )
    if last or last_to_last or before_that:
        return  # admin has touched at least one — leave their policy alone

    frappe.db.set_single_value("HR Settings", "custom_ac_show_payslip_last_month", 1)
    frappe.db.set_single_value(
        "HR Settings", "custom_ac_show_payslip_last_to_last_month", 1
    )
    frappe.db.set_single_value(
        "HR Settings", "custom_ac_show_payslip_month_before_that", 1
    )
    frappe.logger().info(
        "myHR: seeded HR Settings AC payslip show-in-PWA defaults (1, 1, 1)."
    )


# Pairs needed to repair existing installs: (require fieldname, new
# insert_after target, read_only_depends_on eval). Adding the new show
# fields above didn't reorder the existing require fields — `_ensure_custom_fields`
# is skip-if-exists. This repair function updates the require fields in
# place: re-anchors them after the matching show field and adds the
# read_only_depends_on so the require checkbox disables when the show
# checkbox is unticked.
_AC_REQUIRE_FIELD_REPAIRS = [
    (
        "custom_ac_require_payslip_last_month",
        "custom_ac_show_payslip_last_month",
        "eval:!doc.custom_ac_show_payslip_last_month",
    ),
    (
        "custom_ac_require_payslip_last_to_last_month",
        "custom_ac_show_payslip_last_to_last_month",
        "eval:!doc.custom_ac_show_payslip_last_to_last_month",
    ),
    (
        "custom_ac_require_payslip_month_before_that",
        "custom_ac_show_payslip_month_before_that",
        "eval:!doc.custom_ac_show_payslip_month_before_that",
    ),
]


def _repair_ac_payslip_field_attrs():
    """Idempotent repair for the require_X Custom Fields' insert_after +
    read_only_depends_on attrs. Runs on every after_install / after_migrate;
    quietly no-ops when the field already has the desired values."""
    touched = 0
    for fieldname, target_after, depends_on in _AC_REQUIRE_FIELD_REPAIRS:
        cf_name = f"HR Settings-{fieldname}"
        if not frappe.db.exists("Custom Field", cf_name):
            continue
        current = frappe.db.get_value(
            "Custom Field", cf_name,
            ["insert_after", "read_only_depends_on"],
            as_dict=True,
        ) or {}
        updates = {}
        if (current.get("insert_after") or "") != target_after:
            updates["insert_after"] = target_after
        if (current.get("read_only_depends_on") or "") != depends_on:
            updates["read_only_depends_on"] = depends_on
        if updates:
            frappe.db.set_value(
                "Custom Field", cf_name, updates, update_modified=False
            )
            touched += 1
    if touched:
        frappe.clear_cache(doctype="HR Settings")
        frappe.logger().info(
            f"myHR: repaired {touched} require_payslip_* Custom Field attrs."
        )
    frappe.logger().info("myHR: seeded HR Settings EC approver defaults (1, 1, 0).")


_PERM_FLAGS = ("read", "write", "create", "delete", "submit", "cancel", "amend")


def _grant_missing_perm_flags(name, doctype, row):
    """Turn on the declared flags an existing Custom DocPerm is missing."""
    current = frappe.db.get_value("Custom DocPerm", name, _PERM_FLAGS, as_dict=True)
    granted = [f for f in _PERM_FLAGS if row.get(f) and not current.get(f)]
    if not granted:
        return

    for flag in granted:
        frappe.db.set_value("Custom DocPerm", name, flag, 1)
    frappe.logger().info(
        f"myHR: Granted {', '.join(granted)} on {doctype} to {row['role']}."
    )


def _ensure_additive_permissions():
    """Add per-role perm rows to stock doctypes without wiping the rest.

    Used to grant the `Leave Approver` role submit/cancel on Attendance
    Request so that named managers can submit AR for their reports — stock
    HRMS doesn't ship with this perm row, but the myhr RBAC model relies
    on it, and to grant the Employee role access to Employee Separation.

    "Additive" is only true if the stock rows are copied into Custom DocPerm
    first — see the comment in the loop.
    """
    from frappe.permissions import setup_custom_perms

    for doctype, perm_rows in MYHR_ADDITIVE_PERMISSIONS.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        # Frappe uses Custom DocPerm rows EXCLUSIVELY once any exist for a
        # doctype — the DocType's own permissions are then ignored entirely.
        # So on a doctype with no Custom DocPerm yet, adding a single row would
        # silently REVOKE every stock role (System Manager, HR Manager, ...).
        # setup_custom_perms copies the stock rows across first; it is a no-op
        # when Custom DocPerms already exist. Attendance Request happened to
        # already have a full set, which is why this was not caught earlier.
        setup_custom_perms(doctype)
        for row in perm_rows:
            if not frappe.db.exists("Role", row["role"]):
                continue
            existing = frappe.db.exists(
                "Custom DocPerm",
                {"parent": doctype, "role": row["role"], "permlevel": row.get("permlevel", 0)},
            )
            if existing:
                # The role already has a row — often because setup_custom_perms
                # just copied the stock one. Grant any flag we declare that it
                # does not have yet. Only ever turned ON: a flag this dict does
                # not mention is left exactly as it was, so this can extend a
                # stock permission but never quietly take one away.
                _grant_missing_perm_flags(existing, doctype, row)
                continue
            cp = frappe.new_doc("Custom DocPerm")
            cp.parent = doctype
            cp.parenttype = "DocType"
            cp.parentfield = "permissions"
            cp.role = row["role"]
            cp.permlevel = row.get("permlevel", 0)
            cp.read = row.get("read", 0)
            cp.write = row.get("write", 0)
            cp.create = row.get("create", 0)
            cp.delete = row.get("delete", 0)
            cp.submit = row.get("submit", 0)
            cp.cancel = row.get("cancel", 0)
            cp.amend = row.get("amend", 0)
            cp.if_owner = row.get("if_owner", 0)
            cp.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Employee write-lockdown — only HR Manager + System Manager + Administrator
# can write/create/delete/submit Employee records. Everyone else (including
# HR User, Employee, Leave Approver) is read-only on Employee, even on their
# own record. Per the user's policy: "any info they want to update they will
# ask HR Manager."
#
# Implementation: scans both stock DocPerm and Custom DocPerm at permlevel=0
# for non-(HR Manager / System Manager / Administrator) roles that carry any
# write-class flag. For each such role, ensures a Custom DocPerm exists with
# the write flags forced to 0. Defense in depth: `has_employee_permission`
# also denies write-class ptypes for these users; this function makes the
# perm matrix in Role Permission Manager visually correct so admins reading
# the UI don't get confused.
# ---------------------------------------------------------------------------
_EMPLOYEE_WRITE_FLAGS = ("write", "create", "delete", "submit", "cancel", "amend")
_EMPLOYEE_LOCKDOWN_EXEMPT_ROLES = {"HR Manager", "System Manager", "Administrator"}


def _ensure_employee_perm_lockdown():
    """Strip write/create/delete/submit/cancel/amend from any non-exempt role's
    DocPerm on Employee at permlevel=0. Idempotent.

    For each non-exempt role that has any write-class flag set on Employee
    (in either stock DocPerm or an existing Custom DocPerm at permlevel=0),
    ensures a Custom DocPerm row exists for that role with read kept on but
    every write-class flag forced to 0. Already-locked-down rows are no-ops.

    Stock DocPerm rows are NEVER mutated (that would touch core ERPNext
    JSON state). Instead we layer a Custom DocPerm on top — Frappe AND-merges
    them so the most-restrictive flag wins.
    """
    if not frappe.db.exists("DocType", "Employee"):
        return

    # Gather every role that currently has a permlevel=0 row on Employee
    # carrying any write-class flag, scanning both stock + custom perms.
    candidate_roles = set()
    write_cols = ", ".join(f"`{f}`" for f in _EMPLOYEE_WRITE_FLAGS)
    for table in ("tabDocPerm", "tabCustom DocPerm"):
        try:
            rows = frappe.db.sql(
                f"""
                SELECT role, {write_cols}
                FROM `{table}`
                WHERE parent = 'Employee' AND permlevel = 0
                """,
                as_dict=True,
            )
        except Exception:
            rows = []
        for row in rows:
            if not row.get("role"):
                continue
            if row["role"] in _EMPLOYEE_LOCKDOWN_EXEMPT_ROLES:
                continue
            if any(row.get(f) for f in _EMPLOYEE_WRITE_FLAGS):
                candidate_roles.add(row["role"])

    n_locked = 0
    for role in sorted(candidate_roles):
        if not frappe.db.exists("Role", role):
            continue
        existing_name = frappe.db.get_value(
            "Custom DocPerm",
            {"parent": "Employee", "role": role, "permlevel": 0},
            "name",
        )
        if existing_name:
            # Idempotent: only update flags that drift from locked-down state.
            current = frappe.db.get_value(
                "Custom DocPerm", existing_name,
                list(_EMPLOYEE_WRITE_FLAGS), as_dict=True,
            ) or {}
            updates = {}
            for f in _EMPLOYEE_WRITE_FLAGS:
                if current.get(f):
                    updates[f] = 0
            if updates:
                frappe.db.set_value("Custom DocPerm", existing_name, updates)
                n_locked += 1
        else:
            # No Custom DocPerm yet — insert a fully-locked-down row that
            # masks the stock DocPerm's write flags.
            cp = frappe.new_doc("Custom DocPerm")
            cp.parent = "Employee"
            cp.parenttype = "DocType"
            cp.parentfield = "permissions"
            cp.role = role
            cp.permlevel = 0
            cp.read = 1
            cp.write = 0
            cp.create = 0
            cp.delete = 0
            cp.submit = 0
            cp.cancel = 0
            cp.amend = 0
            cp.print = 1
            cp.email = 1
            cp.report = 1
            cp.export = 1
            cp.share = 0
            # `import` is a Python keyword — set via .set() to avoid SyntaxError.
            cp.set("import", 0)
            cp.insert(ignore_permissions=True)
            n_locked += 1

    print(f"myhr: Employee perm lockdown applied — locked write on {n_locked} role(s)")


def _ensure_roles():
    """Create any myHR roles that don't already exist."""
    for role_def in MYHR_ROLES:
        if frappe.db.exists("Role", role_def["role_name"]):
            continue
        role = frappe.new_doc("Role")
        role.role_name = role_def["role_name"]
        role.desk_access = role_def.get("desk_access", 0)
        role.description = role_def.get("description", "")
        role.insert(ignore_permissions=True)
        frappe.logger().info(f"myHR: created role '{role_def['role_name']}'")


def _enforce_permissions():
    """
    Set permissions on myHR-managed doctypes programmatically.
    This mirrors what's in employee_directory.json but runs every migrate,
    so drift is auto-corrected.
    """
    for doctype, perm_rows in MYHR_PERMISSIONS.items():
        if not frappe.db.exists("DocType", doctype):
            continue

        # Wipe existing custom perms for this doctype so we start clean
        frappe.db.delete("Custom DocPerm", {"parent": doctype})

        for row in perm_rows:
            # Only insert if the role exists
            if not frappe.db.exists("Role", row["role"]):
                continue
            cp = frappe.new_doc("Custom DocPerm")
            cp.parent = doctype
            cp.parenttype = "DocType"
            cp.parentfield = "permissions"
            cp.role = row["role"]
            cp.read = row.get("read", 0)
            cp.write = row.get("write", 0)
            cp.create = row.get("create", 0)
            cp.delete = row.get("delete", 0)
            cp.export = row.get("export", 0)
            cp.print = row.get("print", 0)
            cp.report = row.get("report", 0)
            cp.share = row.get("share", 0)
            cp.insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Custom Fields — skip-if-exists (safe to run on any system)
# ---------------------------------------------------------------------------
def _ensure_leave_application_status_property_setter():
    """Pin Leave Application status options to the single-stage set."""
    if not frappe.db.exists("DocType", "Leave Application"):
        return
    desired = "Open\nApproved\nRejected\nCancelled"
    existing = frappe.db.get_value(
        "Property Setter",
        {"doc_type": "Leave Application", "field_name": "status", "property": "options"},
        ["name", "value"],
        as_dict=True,
    )
    if existing:
        if existing.value != desired:
            frappe.db.set_value("Property Setter", existing.name, "value", desired)
            frappe.logger().info("myHR: Updated Leave Application status options Property Setter.")
    else:
        make_property_setter(
            "Leave Application",
            "status",
            "options",
            desired,
            "Text",
            for_doctype=False,
            validate_fields_for_doctype=False,
        )
        frappe.logger().info("myHR: Created Property Setter for Leave Application status.")


# Doctypes whose stock `employee` field must ignore User Permissions.
#
# Linking a User to an Employee creates a User Permission for that one Employee
# record. Any document naming a DIFFERENT employee then fails the document-level
# check outright — so a manager cannot open a report's row to approve it. Stock
# HRMS sets this on Leave Application but misses it elsewhere.
_EMPLOYEE_FIELD_IGNORES_USER_PERMISSIONS = (
    "Attendance Request",
    # Without this an L1/L2 manager gets PermissionError opening a report's
    # resignation, so the whole approval route is unreachable for them.
    "Employee Separation",
)


def _ensure_attendance_request_employee_ignore_user_permissions():
    """Property Setter `employee.ignore_user_permissions = 1` on each doctype in
    `_EMPLOYEE_FIELD_IGNORES_USER_PERMISSIONS`. See that tuple for the why.
    """
    for doctype in _EMPLOYEE_FIELD_IGNORES_USER_PERMISSIONS:
        _set_employee_field_ignores_user_permissions(doctype)


def _set_employee_field_ignores_user_permissions(doctype):
    if not frappe.db.exists("DocType", doctype):
        return
    desired = "1"
    existing = frappe.db.get_value(
        "Property Setter",
        {"doc_type": doctype, "field_name": "employee",
         "property": "ignore_user_permissions"},
        ["name", "value"], as_dict=True,
    )
    if existing:
        if existing.value != desired:
            frappe.db.set_value("Property Setter", existing.name, "value", desired)
    else:
        make_property_setter(
            doctype, "employee", "ignore_user_permissions",
            desired, "Check",
            for_doctype=False, validate_fields_for_doctype=False,
        )


def _ensure_ssa_opening_balances_visible():
    """Unhide the Salary Structure Assignment "Opening Balances" section.

    `Taxable Earnings Till Date` / `Tax Deducted Till Date` live in a section
    that ships with `hidden: 1` in the HRMS doctype JSON. Stock HRMS only
    reveals it from client JS (`toggle_opening_balances_section`, which calls
    `are_opening_entries_required` on form refresh) — so if those assets are
    stale, or any earlier form script throws, HR gets the "Missing Opening
    Entries" warning on save with no field anywhere on the form to answer it.

    Flipping the section to `hidden: 0` makes it reachable regardless of JS.
    When the JS *does* run it still calls `set_df_property` on top of this at
    runtime, so the section keeps auto-hiding for assignments that start on the
    payroll period boundary and genuinely need no opening figures.
    """
    if not frappe.db.exists("DocType", "Salary Structure Assignment"):
        return
    desired = "0"
    ps = frappe.db.get_value(
        "Property Setter",
        {
            "doc_type": "Salary Structure Assignment",
            "field_name": "opening_balances_section",
            "property": "hidden",
        },
        ["name", "value"],
        as_dict=True,
    )
    if ps:
        if ps.value != desired:
            frappe.db.set_value("Property Setter", ps.name, "value", desired)
            frappe.logger().info(
                "myHR: Updated SSA opening_balances_section hidden Property Setter."
            )
    else:
        make_property_setter(
            "Salary Structure Assignment",
            "opening_balances_section",
            "hidden",
            desired,
            "Check",
            for_doctype=False,
            validate_fields_for_doctype=False,
        )
        frappe.logger().info(
            "myHR: Created Property Setter unhiding SSA opening_balances_section."
        )


def _ensure_employee_leave_approver_labels():
    """Pin the Employee.leave_approver label (single-stage approval, no HR-stage suffix)."""
    if not frappe.db.exists("DocType", "Employee"):
        return
    desired = "Leave Approver"
    ps = frappe.db.get_value(
        "Property Setter",
        {"doc_type": "Employee", "field_name": "leave_approver", "property": "label"},
        ["name", "value"],
        as_dict=True,
    )
    if ps:
        if ps.value != desired:
            frappe.db.set_value("Property Setter", ps.name, "value", desired)
    else:
        make_property_setter(
            "Employee",
            "leave_approver",
            "label",
            desired,
            "Data",
            for_doctype=False,
            validate_fields_for_doctype=False,
        )


# ---------------------------------------------------------------------------
# Elixiir Phase 1 merge — property setters that hide native Joining tab and
# native bank/holiday fields. The custom Bank tab + custom_holiday_list carry
# the same data; sync writes back to the natives so payroll / bank-file
# generation continues to work.
#
# The Salary Slip default_print_format setter from elixiir's install.py is
# intentionally skipped here — we don't have the "Elixiir Salary Slip" print
# format in myhr yet, so setting a non-existent format would break printing.
# ---------------------------------------------------------------------------
_ELIXIIR_HIDDEN_EMPLOYEE_FIELDS = (
    "employment_details",       # Joining tab — surfaced via Overview tab instead
    "salary_mode",
    "bank_details_section",
    "bank_name",
    "bank_ac_no",
    "ifsc_code",
    "micr_code",
    "iban",
    "holiday_list",
)


def _apply_elixiir_property_setters():
    """Hide the native Joining tab + 8 native bank/holiday fields on Employee.

    Frappe's `hidden` flag on a Section Break does NOT cascade to its
    contained fields — each field has to be hidden individually. The custom
    "Bank and Payment Details" tab and `custom_holiday_list` carry the same
    data; downstream syncs (payroll, bank-file generation, holiday-list
    assignment) write back to these natives so business logic still works.
    """
    if not frappe.db.exists("DocType", "Employee"):
        return
    for fname in _ELIXIIR_HIDDEN_EMPLOYEE_FIELDS:
        existing = frappe.db.get_value(
            "Property Setter",
            {"doc_type": "Employee", "field_name": fname, "property": "hidden"},
            ["name", "value"],
            as_dict=True,
        )
        if existing:
            if existing.value != "1":
                frappe.db.set_value("Property Setter", existing.name, "value", "1")
            continue
        make_property_setter(
            "Employee",
            fname,
            "hidden",
            1,
            "Check",
            for_doctype=False,
            validate_fields_for_doctype=False,
        )


# ---------------------------------------------------------------------------
# Elixiir Phase 1 merge — HR-only field permlevels.
#
# These Employee fields are sensitive (compensation, hierarchy, structural
# HR data). They live at permlevel=1; only HR Manager has read+write at
# permlevel=1. Employee + Employee Self Service get read-only at permlevel=1
# so the values render but can't be edited. Everyone else inherits no
# permlevel=1 access at all — fields stay invisible to them.
# ---------------------------------------------------------------------------
ELIXIIR_HR_ONLY_FIELDS = (
    "ctc",
    "salutation",
    "designation",
    "department",
    "reports_to",
    "employment_type",
    "grade",
    "company_email",
    "custom_notice_period_days",
    "custom_salary_structure",
    "custom_total_experience_years",
    "custom_employee_location",
    "custom_holiday_list",
)


def _apply_elixiir_hr_only_permlevels():
    """Bump the 13 HR-only Employee fields to permlevel=1 via Property Setter.

    Paired with `_ensure_elixiir_hr_manager_permlevel_perm` which grants the
    matching Custom DocPerm rows at permlevel=1.
    """
    if not frappe.db.exists("DocType", "Employee"):
        return
    for fname in ELIXIIR_HR_ONLY_FIELDS:
        existing = frappe.db.get_value(
            "Property Setter",
            {"doc_type": "Employee", "field_name": fname, "property": "permlevel"},
            ["name", "value"],
            as_dict=True,
        )
        if existing:
            if existing.value != "1":
                frappe.db.set_value("Property Setter", existing.name, "value", "1")
            continue
        make_property_setter(
            "Employee",
            fname,
            "permlevel",
            1,
            "Int",
            for_doctype=False,
            validate_fields_for_doctype=False,
        )


# ---------------------------------------------------------------------------
# Mandatory payroll fields on Employee.
#
# Enforced via Property Setter (property `reqd`) rather than the Custom Field
# dict so the flag also lands on already-installed sites — `_ensure_custom_fields`
# is skip-if-exists and won't flip attrs on an existing field. Currently the two
# native payroll fields (ctc, payroll_cost_center); Salary Structure and Income
# Tax Slab are intentionally left optional. Same idempotent-update pattern as the
# permlevel setters.
# ---------------------------------------------------------------------------
ELIXIIR_MANDATORY_FIELDS = (
    "payroll_cost_center",
    "ctc",
)

# Fields myHR made mandatory in an earlier version but that must now stay
# OPTIONAL. The helper actively clears any `reqd` Property Setter on these so a
# stale override can't keep them mandatory after this reverts to only the two
# above. If you ever re-mandate one, move it to ELIXIIR_MANDATORY_FIELDS.
ELIXIIR_OPTIONAL_FIELDS = (
    "custom_salary_structure",
    "custom_income_tax_slab",
)


def _apply_elixiir_mandatory_fields():
    """Enforce the exact mandatory set: reqd=1 for ELIXIIR_MANDATORY_FIELDS,
    and reqd cleared for ELIXIIR_OPTIONAL_FIELDS (self-healing both ways)."""
    if not frappe.db.exists("DocType", "Employee"):
        return
    for fname in ELIXIIR_MANDATORY_FIELDS:
        existing = frappe.db.get_value(
            "Property Setter",
            {"doc_type": "Employee", "field_name": fname, "property": "reqd"},
            ["name", "value"],
            as_dict=True,
        )
        if existing:
            if existing.value != "1":
                frappe.db.set_value("Property Setter", existing.name, "value", "1")
            continue
        make_property_setter(
            "Employee",
            fname,
            "reqd",
            1,
            "Check",
            for_doctype=False,
            validate_fields_for_doctype=False,
        )
    # Force the delisted fields back to optional.
    for fname in ELIXIIR_OPTIONAL_FIELDS:
        ps = frappe.db.get_value(
            "Property Setter",
            {"doc_type": "Employee", "field_name": fname, "property": "reqd"},
            "name",
        )
        if ps:
            frappe.delete_doc("Property Setter", ps, ignore_permissions=True, force=True)
        cf = f"Employee-{fname}"
        if frappe.db.exists("Custom Field", cf) and frappe.db.get_value("Custom Field", cf, "reqd"):
            frappe.db.set_value("Custom Field", cf, "reqd", 0)


def _ensure_elixiir_hr_manager_permlevel_perm():
    """Ensure HR Manager has read+write at permlevel=1 on Employee, and
    Employee + Employee Self Service have read-only at permlevel=1.

    Without these Custom DocPerm rows the permlevel=1 fields would be
    invisible / uneditable to everyone (including HR), defeating the
    HR-only-field design. Idempotent — checks for existing rows first.
    """
    if not frappe.db.exists("DocType", "Employee"):
        return

    # HR Manager: full access at permlevel=1
    if frappe.db.exists("Role", "HR Manager") and not frappe.db.exists(
        "Custom DocPerm",
        {"parent": "Employee", "role": "HR Manager", "permlevel": 1},
    ):
        dp = frappe.new_doc("Custom DocPerm")
        dp.parent = "Employee"
        dp.parenttype = "DocType"
        dp.parentfield = "permissions"
        dp.role = "HR Manager"
        dp.permlevel = 1
        dp.read = 1
        dp.write = 1
        dp.insert(ignore_permissions=True)

    # Employee + Employee Self Service: read-only at permlevel=1
    for role in ("Employee", "Employee Self Service"):
        if not frappe.db.exists("Role", role):
            continue
        if frappe.db.exists(
            "Custom DocPerm",
            {"parent": "Employee", "role": role, "permlevel": 1},
        ):
            continue
        dp = frappe.new_doc("Custom DocPerm")
        dp.parent = "Employee"
        dp.parenttype = "DocType"
        dp.parentfield = "permissions"
        dp.role = role
        dp.permlevel = 1
        dp.read = 1
        dp.write = 0
        dp.insert(ignore_permissions=True)


MYHR_CUSTOM_FIELDS = [
    {
        "dt": "Employee",
        "fieldname": "custom_employee_id",
        "label": "Employee ID",
        "fieldtype": "Data",
        "insert_after": "naming_series",
        "bold": 1,
        "in_list_view": 1,
        "unique": 1,
        "description": "Custom business Employee ID used by myHR.",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_title",
        "label": "Title",
        "fieldtype": "Data",
        "insert_after": "designation",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_income_tax_slab",
        "label": "Income Tax Slab",
        "fieldtype": "Link",
        "options": "Income Tax Slab",
        "insert_after": "payroll_cost_center",
    },
    # ----- Salary tab: opening balances seeded onto the SSA ------------------
    # HRMS keeps these two figures on Salary Structure Assignment only, and
    # warns ("Missing Opening Entries") when an assignment starts mid payroll
    # period without them. myHR creates the SSA programmatically from the
    # Employee form, so HR needs somewhere to enter them up front — these get
    # copied onto every new SSA by
    # `salary_structure_assignment_hooks.fill_opening_balances_from_employee`.
    # permlevel=1 to match `ctc` / `custom_salary_structure`: compensation data
    # is HR-Manager-writable only.
    {
        "dt": "Employee",
        "fieldname": "custom_opening_balances_section",
        "label": "Opening Balances (Current Payroll Period)",
        "fieldtype": "Section Break",
        "insert_after": "custom_income_tax_slab",
        "description": (
            "Earnings and TDS already on record for this payroll period — from a "
            "previous employer, or from payroll run outside ERPNext. Needed for "
            "correct tax projection on mid-year joiners; leave blank for anyone "
            "with no earlier earnings this period."
        ),
    },
    {
        "dt": "Employee",
        "fieldname": "custom_taxable_earnings_till_date",
        "label": "Taxable Earnings Till Date",
        "fieldtype": "Currency",
        "insert_after": "custom_opening_balances_section",
        "permlevel": 1,
        "non_negative": 1,
        "description": "Taxable salary already earned this payroll period.",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_opening_balances_cb",
        "fieldtype": "Column Break",
        "insert_after": "custom_taxable_earnings_till_date",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_tax_deducted_till_date",
        "label": "Tax Deducted Till Date",
        "fieldtype": "Currency",
        "insert_after": "custom_opening_balances_cb",
        "permlevel": 1,
        "non_negative": 1,
        "description": "TDS already deducted against those earnings.",
    },
    # ----- HR Controls tab (sits next to Overview) -----------------------
    # The Tab Break anchors at "grade" so that `grade` (a stock ERPNext
    # Overview field) stays inside the Overview tab. If we anchored at
    # "branch" instead, `grade` would fall under HR Controls because
    # there's no intervening stock Tab Break between branch and grade.
    {
        "dt": "Employee",
        "fieldname": "custom_hr_controls_tab",
        "label": "HR Controls",
        "fieldtype": "Tab Break",
        "insert_after": "grade",
        "description": "",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_emp_directory",
        "label": "Add to Employee Directory",
        "fieldtype": "Check",
        "insert_after": "custom_hr_controls_tab",
        "default": "1",
        "description": (
            "When checked, this employee appears in the company-wide Employee "
            "Directory (PWA + Desk). Uncheck to hide this employee — typically "
            "used for confidential roles like CEO. Existing directory rows "
            "are auto-removed when this flag is cleared."
        ),
    },
    {
        "dt": "Employee",
        "fieldname": "custom_add_to_action_centre",
        "label": "Add to Employee Action Centre",
        "fieldtype": "Check",
        "insert_after": "custom_emp_directory",
        "default": "1",
        "description": (
            "When checked, an Employee Action Centre row is auto-created on "
            "insert. The Action Centre tracks the employee's mandatory "
            "document uploads (Aadhar, PAN, education), employer history, "
            "and policy acknowledgements. Uncheck only for system accounts "
            "that don't onboard."
        ),
    },
    {
        "dt": "Employee",
        "fieldname": "custom_auto_present",
        "label": "Auto Present",
        "fieldtype": "Check",
        "insert_after": "custom_add_to_action_centre",
        "default": "0",
        "description": (
            "When checked, the scheduler auto-marks this employee Present "
            "every weekday: IN at 09:00, OUT at 18:00 (device_id='myHR Auto'). "
            "The cron path bypasses the policy-acknowledgement gate AND the "
            "geolocation distance check (HR is responsible for compliance "
            "separately). Attendance is created downstream via HRMS's hourly "
            "auto-attendance sweep — requires the Shift Type to have "
            "'Enable Auto Attendance' ticked. Use for founders / senior "
            "staff who don't manually check in."
        ),
    },
    {
        "dt": "Employee",
        "fieldname": "custom_bypass_geolocation_check",
        "label": "Bypass Geolocation Checkin Validation",
        "fieldtype": "Check",
        "insert_after": "custom_auto_present",
        "default": "0",
        "description": (
            "When checked, this employee's manual check-ins skip the Shift "
            "Location radius enforcement — they can check in from anywhere. "
            "Latitude and longitude are still required and captured on every "
            "check-in for audit. Use for founders, WFH staff, or road "
            "warriors whose location should still be logged but who aren't "
            "tied to a fixed office radius. Does NOT exempt the policy-"
            "acknowledgement gate or the ownership gate — both still apply."
        ),
    },
    {
        "dt": "Employee",
        "fieldname": "custom_allow_view_reporting",
        "fieldtype": "Check",
        "default": "0",
        "label": "Allow to see Reporting Employees",
        "insert_after": "custom_bypass_geolocation_check",
        "description": (
            "When ticked, this employee can view (read-only) the Employee "
            "records of their direct reports. HR Manager / HR User / System "
            "Manager always see everyone regardless of this flag. Unticked "
            "means the user only sees their own Employee record."
        ),
    },
    {
        "dt": "Employee",
        "fieldname": "custom_send_checkin_reminder",
        "fieldtype": "Check",
        "default": "1",
        "label": "Send Check-in Reminder",
        "insert_after": "custom_allow_view_reporting",
        "description": (
            "When ticked, the 11:00 daily Missing IN Checkin Reminder job "
            "emails this employee if they have not marked an IN check-in by "
            "the cutoff. Untick to exempt founders / senior staff / "
            "auto-present employees from the reminder. The global "
            "'Enable Check-in Reminder' toggle on HR Settings overrides this "
            "for the entire site."
        ),
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_enable_checkin_reminder",
        "fieldtype": "Check",
        "default": "1",
        "label": "Enable Check-in Reminder",
        "insert_after": "send_birthday_reminders",
        "description": (
            "Global kill-switch for the 11:00 daily Missing IN Checkin "
            "Reminder job (myhr.missing_in_reminder.send_missing_in_reminders). "
            "When unticked, the cron short-circuits and no emails are sent "
            "site-wide; per-employee 'Send Check-in Reminder' flags are "
            "ignored. Default ticked."
        ),
    },
    {
        "dt": "Holiday",
        "fieldname": "custom_holiday_type",
        "label": "Holiday Type",
        "fieldtype": "Select",
        "options": "Optional\nFixed\nWeekly Off",
        "insert_after": "weekly_off",
        "description": "Categorization for holiday entries.",
    },
    # ----- LA-1: Approval audit on Leave Application ------------------------
    # Stamped server-side on the Open → Approved transition by the override
    # class. Read-only; HR Manager bypass via `frappe.flags.allow_la_audit_edit`
    # for the rare reopen path. Captures *who actually approved + when*, which
    # the stock `leave_approver` field doesn't (that's the *intended* approver).
    {
        "dt": "Leave Application",
        "fieldname": "custom_approved_by",
        "label": "Approved By",
        "fieldtype": "Link",
        "options": "User",
        "insert_after": "leave_approver_name",
        "read_only": 1,
        "description": "User who actually clicked Approve. Server-stamped; immutable once set.",
    },
    {
        "dt": "Leave Application",
        "fieldname": "custom_approved_on",
        "label": "Approved On",
        "fieldtype": "Datetime",
        "insert_after": "custom_approved_by",
        "read_only": 1,
        "description": "Timestamp of the Open → Approved transition. Server-stamped; immutable once set.",
    },
    # ----- LA-4: Rejection remarks (mandatory in PWA Reject action) -----------
    # The PWA Reject button opens a textarea and stamps this field; the override
    # also enforces it on the Open → Rejected transition. Rejected leaves
    # auto-submit (parallel to Approved) so they leave the Team Requests queue.
    {
        "dt": "Leave Application",
        "fieldname": "custom_rejection_reason",
        "label": "Rejection Reason",
        "fieldtype": "Small Text",
        "insert_after": "custom_approved_on",
        "depends_on": "eval:doc.status==='Rejected'",
        "read_only": 1,
        "description": "Remarks captured when the leave was rejected. Visible to the employee so they know why.",
    },
    # ----- LA-5: Cancellation remarks (mandatory in PWA Cancel action) --------
    # Used by the employee-side cancel flow. Allowed only while the LA is still
    # Open (un-approved); HR cancels post-approval through Desk.
    {
        "dt": "Leave Application",
        "fieldname": "custom_cancellation_reason",
        "label": "Cancellation Reason",
        "fieldtype": "Small Text",
        "insert_after": "custom_rejection_reason",
        "depends_on": "eval:doc.status==='Cancelled'",
        "read_only": 1,
        "description": "Remarks captured when the employee cancelled their own pending leave application.",
    },
    # ----- AR-1/AR-2: Rejection + Cancellation remarks on Attendance Request --
    {
        "dt": "Attendance Request",
        "fieldname": "custom_rejection_reason",
        "label": "Rejection Reason",
        "fieldtype": "Small Text",
        "insert_after": "reason",
        "read_only": 1,
        "description": "Remarks captured when the attendance request was rejected.",
    },
    {
        "dt": "Attendance Request",
        "fieldname": "custom_cancellation_reason",
        "label": "Cancellation Reason",
        "fieldtype": "Small Text",
        "insert_after": "custom_rejection_reason",
        "read_only": 1,
        "description": "Remarks captured when the employee cancelled their own pending attendance request.",
    },
    # ----- EC-1: Rejection remarks on Expense Claim (mandatory in PWA Reject) -
    # Mirrors LA-4. The PWA Reject button stamps this field on the Open →
    # Rejected transition; the override at `myhr.overrides.expense_claim`
    # enforces it server-side and the rejection banner in RequestActionSheet
    # surfaces the reason to the filer.
    {
        "dt": "Expense Claim",
        "fieldname": "custom_rejection_reason",
        "label": "Rejection Reason",
        "fieldtype": "Small Text",
        "insert_after": "approval_status",
        "depends_on": "eval:doc.approval_status==='Rejected'",
        "read_only": 1,
        "description": "Remarks captured when the expense claim was rejected. Visible to the employee so they know why.",
    },
    # ----- AR-3: Configurable Attendance Request approver policy --------------
    # Lets each install decide who may submit (i.e. approve, since AR submit
    # creates the Attendance row) an Attendance Request. Defaults match the
    # pre-existing hardcoded behaviour so existing sites don't change semantics
    # on migrate. The lockout guard in `myhr.approval_gate.gate_hr_settings_save`
    # prevents all three from being unticked at once.
    #
    # Layout: the toggles live on a dedicated `Approvals` tab on HR Settings
    # so they don't clutter the Expenses tab. Future Leave Application approval
    # toggles will land in the same tab. Patch `v1_14_move_ar_approval_to_own_tab`
    # repoints the section on already-installed sites.
    {
        "dt": "HR Settings",
        "fieldname": "custom_la_ar_approval_tab",
        "label": "Approvals",
        "fieldtype": "Tab Break",
        "insert_after": "recruitment_tab",
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ar_approval_section",
        "label": "Attendance Request Approval",
        "fieldtype": "Section Break",
        "insert_after": "custom_la_ar_approval_tab",
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ar_approver_hr_manager",
        "label": "Allow HR Manager / System Manager to approve Attendance Requests",
        "fieldtype": "Check",
        "insert_after": "custom_ar_approval_section",
        "default": "1",
        "description": (
            "When ticked, users with the HR Manager or System Manager role "
            "can submit (approve) any Attendance Request. Untick to restrict "
            "approval authority to the named Leave Approver only."
        ),
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ar_approver_leave_approver",
        "label": "Allow employee's Leave Approver to approve Attendance Requests",
        "fieldtype": "Check",
        "insert_after": "custom_ar_approver_hr_manager",
        "default": "1",
        "description": (
            "When ticked, the User listed on Employee.leave_approver can submit "
            "(approve) that employee's Attendance Requests. Untick to centralise "
            "AR approval with HR only."
        ),
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ar_allow_self_submit",
        "label": "Allow employees to submit their own Attendance Requests",
        "fieldtype": "Check",
        "insert_after": "custom_ar_approver_leave_approver",
        "default": "0",
        "description": (
            "When ticked, an employee may submit their own Attendance Request "
            "without an approver. AR submit creates the Attendance row, so "
            "leave this off unless your company policy explicitly allows "
            "self-marked attendance via this surface."
        ),
    },
    # -----------------------------------------------------------------------
    # Expense Claim approver toggles (HR Settings → Expenses tab)
    # -----------------------------------------------------------------------
    # Stock HRMS has no business-logic gate on Expense Claim approval — any
    # user with the doctype-level submit perm (HR Manager / HR User /
    # Expense Approver role) can flip approval_status to Approved on any
    # claim. These toggles let each install pick its own RBAC model:
    # blanket HR, only the named approver, only Accounts Manager — or any
    # combination. The gate `myhr.approval_gate.gate_expense_claim_approval`
    # reads them and enforces. Defaults preserve pre-existing behaviour
    # (HR + named approver = on, Accounts Manager = off).
    {
        "dt": "HR Settings",
        "fieldname": "custom_ec_approval_section",
        "label": "Expense Claim Approval Authority",
        "fieldtype": "Section Break",
        "insert_after": "unlink_payment_on_cancellation_of_employee_advance",
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ec_approver_hr_manager",
        "label": "Allow HR Manager / System Manager to approve any Expense Claim",
        "fieldtype": "Check",
        "insert_after": "custom_ec_approval_section",
        "default": "1",
        "description": (
            "When ticked, users with the HR Manager or System Manager role "
            "can approve / reject any Expense Claim regardless of who is "
            "named on the claim. Untick to restrict approval authority to "
            "the named Expense Approver and / or Accounts Manager only."
        ),
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ec_approver_designated",
        "label": "Allow employee's named Expense Approver to approve their Expense Claim",
        "fieldtype": "Check",
        "insert_after": "custom_ec_approver_hr_manager",
        "default": "1",
        "description": (
            "When ticked, the User listed on Expense Claim.expense_approver "
            "(or Employee.expense_approver) can approve / reject that "
            "claim. This is the standard delegation path — untick only "
            "if your company centralises all expense approvals with HR "
            "or Accounts."
        ),
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ec_approver_accounts_manager",
        "label": "Allow Accounts Manager to approve any Expense Claim",
        "fieldtype": "Check",
        "insert_after": "custom_ec_approver_designated",
        "default": "0",
        "description": (
            "When ticked, users with the Accounts Manager role can approve "
            "/ reject any Expense Claim. Use this if your finance team "
            "owns expense sign-off rather than line managers."
        ),
    },

    # ----- Action Centre — Most Recent Employer payslip mandatory toggles -----
    # The Action Centre asks the employee to upload three payslips from their
    # most recent employer. Whether each is REQUIRED or OPTIONAL is HR-tunable
    # here so different company policies can ship without a code change. The
    # other rows under "Most Recent Employer" (Offer Letter / Increment /
    # Relieving) stay hardcoded — only the payslips are configurable per the
    # original product requirement.
    {
        "dt": "HR Settings",
        "fieldname": "custom_ac_tab",
        "label": "Action Centre",
        "fieldtype": "Tab Break",
        "insert_after": "custom_ec_approver_accounts_manager",
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ac_payslips_section",
        "label": "Most Recent Employer — Pay Slip Requirements",
        "fieldtype": "Section Break",
        "insert_after": "custom_ac_tab",
        "description": (
            "Each payslip toggle controls whether the row appears as REQUIRED "
            "or OPTIONAL in the employee's Action Centre. Toggling OFF makes "
            "that payslip optional — the employee can submit without it. "
            "The other Most Recent Employer documents (Offer Letter, "
            "Increment Letter, Relieving Letter) follow the hardcoded policy "
            "and are not configurable here."
        ),
    },
    # Each payslip pair: "Show in PWA" first, then "Require". The require
    # checkbox is read-only when show_in_pwa is unchecked — a hidden row
    # cannot be mandatory.
    {
        "dt": "HR Settings",
        "fieldname": "custom_ac_show_payslip_last_month",
        "label": "Show Pay Slip — Last Month in PWA",
        "fieldtype": "Check",
        "insert_after": "custom_ac_payslips_section",
        "default": "1",
        "description": (
            "When ticked (default), the PWA renders this payslip card to the "
            "employee. Untick to hide entirely — the row stays in Desk mode "
            "marked OPTIONAL and HR cannot then mark it mandatory."
        ),
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ac_require_payslip_last_month",
        "label": "Require Pay Slip — Last Month",
        "fieldtype": "Check",
        "insert_after": "custom_ac_show_payslip_last_month",
        "default": "1",
        "read_only_depends_on": "eval:!doc.custom_ac_show_payslip_last_month",
        "description": (
            "When ticked (default), the most-recent-month payslip is REQUIRED "
            "in the Action Centre. Untick to mark it OPTIONAL. Disabled when "
            "the row is hidden from the PWA."
        ),
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ac_show_payslip_last_to_last_month",
        "label": "Show Pay Slip — Last-to-Last Month in PWA",
        "fieldtype": "Check",
        "insert_after": "custom_ac_require_payslip_last_month",
        "default": "1",
        "description": (
            "When ticked (default), the PWA renders this payslip card. "
            "Untick to hide entirely from the employee view."
        ),
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ac_require_payslip_last_to_last_month",
        "label": "Require Pay Slip — Last-to-Last Month",
        "fieldtype": "Check",
        "insert_after": "custom_ac_show_payslip_last_to_last_month",
        "default": "1",
        "read_only_depends_on": "eval:!doc.custom_ac_show_payslip_last_to_last_month",
        "description": (
            "When ticked (default), the second-most-recent-month payslip is "
            "REQUIRED. Untick to mark it OPTIONAL. Disabled when hidden."
        ),
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ac_show_payslip_month_before_that",
        "label": "Show Pay Slip — Month Before That in PWA",
        "fieldtype": "Check",
        "insert_after": "custom_ac_require_payslip_last_to_last_month",
        "default": "1",
        "description": (
            "When ticked (default), the PWA renders this payslip card. "
            "Untick to hide entirely from the employee view."
        ),
    },
    {
        "dt": "HR Settings",
        "fieldname": "custom_ac_require_payslip_month_before_that",
        "label": "Require Pay Slip — Month Before That",
        "fieldtype": "Check",
        "insert_after": "custom_ac_show_payslip_month_before_that",
        "default": "1",
        "read_only_depends_on": "eval:!doc.custom_ac_show_payslip_month_before_that",
        "description": (
            "When ticked (default), the third-most-recent-month payslip is "
            "REQUIRED. Untick to mark it OPTIONAL. Disabled when hidden."
        ),
    },

    # ----- Expense Claim "Submit for Review" audit fields -------------------
    # ERPNext's docstatus 0→1 transition on Expense Claim requires the
    # approver to set approval_status first — only the approver can flip
    # docstatus. Our PWA flow needs an intermediate "employee is done
    # editing, approver may now act" state. Mirror the EAC pattern with
    # a custom flag + audit timestamps; docstatus stays 0 until the
    # approver decides.
    {
        "dt": "Expense Claim",
        "fieldname": "custom_submitted_for_review",
        "label": "Submitted for Review",
        "fieldtype": "Check",
        "insert_after": "approval_status",
        "default": "0",
        "read_only": 1,
        "no_copy": 1,
        "description": (
            "Set by the PWA's Submit-for-Review action. Signals that the "
            "employee is done editing and the approver may now decide. "
            "Server-stamped, immutable once set (cleared via HR Reopen)."
        ),
    },
    {
        "dt": "Expense Claim",
        "fieldname": "custom_submitted_on",
        "label": "Submitted On",
        "fieldtype": "Datetime",
        "insert_after": "custom_submitted_for_review",
        "read_only": 1,
        "no_copy": 1,
        "description": "Server-stamped on the not-submitted → submitted transition.",
    },
    {
        "dt": "Expense Claim",
        "fieldname": "custom_submitted_by",
        "label": "Submitted By",
        "fieldtype": "Link",
        "options": "User",
        "insert_after": "custom_submitted_on",
        "read_only": 1,
        "no_copy": 1,
        "description": "User who tapped Submit for Review. Server-stamped, immutable.",
    },

    # ----- Elixiir master-data fields (Phase 1 merge) -------------------------
    # Ported from elixiir/setup/install.py::create_elixiir_custom_fields().
    # Item / Material Request / Purchase Order / Purchase Receipt sections are
    # OUT OF SCOPE for this phase — only the Employee block is mirrored here.
    #
    # Conflict note: elixiir originally anchored `custom_total_experience_years`
    # at insert_after="grade", but myhr already anchors `custom_hr_controls_tab`
    # there. To avoid the collision we move custom_total_experience_years to
    # insert_after="branch" (still on the Overview tab, just earlier in the
    # field order). See ELIXIIR_MYHR_INTEGRATION.md Issue 1.

    # ---- Overview tab additions: salary structure, location, notice, holidays
    {
        "dt": "Employee",
        "fieldname": "custom_salary_structure",
        "label": "Salary Structure",
        "fieldtype": "Link",
        "options": "Salary Structure",
        "insert_after": "salary_information",
        "description": "Select the applicable salary structure for payroll",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_employee_location",
        "label": "Employee Location",
        "fieldtype": "Link",
        "options": "Location",
        "insert_after": "branch",
        "description": "Branch or office location (Overview tab)",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_notice_period_days",
        "label": "Notice Period (Days)",
        "fieldtype": "Int",
        "insert_after": "custom_employee_location",
        "description": "Notice period duration in days. Synced to the native notice_number_of_days field.",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_holiday_list",
        "label": "Holiday List",
        "fieldtype": "Link",
        "options": "Holiday List",
        "insert_after": "custom_notice_period_days",
        "description": "Applicable holiday calendar. On save, a Holiday List Assignment is auto-created.",
    },

    # ---- Bank tab break + 7 bank fields --------------------------------------
    {
        "dt": "Employee",
        "fieldname": "custom_bank_tab",
        "label": "Bank and Payment Details",
        "fieldtype": "Tab Break",
        "insert_after": "iban",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_bank_name",
        "label": "Bank Name",
        "fieldtype": "Link",
        "options": "Bank",
        "insert_after": "custom_bank_tab",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_account_number",
        "label": "Account Number",
        "fieldtype": "Data",
        "insert_after": "custom_bank_name",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_ifsc_code",
        "label": "IFSC / Routing Code",
        "fieldtype": "Data",
        "insert_after": "custom_account_number",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_account_type",
        "label": "Account Type",
        "fieldtype": "Select",
        "options": "\nSavings\nCurrent",
        "insert_after": "custom_ifsc_code",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_payment_mode",
        "label": "Payment Mode",
        "fieldtype": "Select",
        "options": "\nBank Transfer\nCheque\nCash",
        "insert_after": "custom_account_type",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_account_holder_name",
        "label": "Account Holder Name",
        "fieldtype": "Data",
        "insert_after": "custom_payment_mode",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_name_as_per_bank",
        "label": "Name as per Bank Records",
        "fieldtype": "Data",
        "insert_after": "custom_account_holder_name",
    },

    # ---- Overview tab additions: age, PAN/Aadhar attachments, experience -----
    {
        "dt": "Employee",
        "fieldname": "custom_age",
        "label": "Age",
        "fieldtype": "Data",
        "read_only": 1,
        "insert_after": "date_of_birth",
        "description": "Auto-computed from Date of Birth as '{Years} Years {Months} Months'.",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_pan_attachment",
        "label": "PAN Card Attachment",
        "fieldtype": "Attach",
        "insert_after": "pan_number",
        "description": "PDF, max 5MB.",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_aadhar_number",
        "label": "Aadhar Number",
        "fieldtype": "Data",
        "insert_after": "custom_pan_attachment",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_aadhar_attachment",
        "label": "Aadhar Card Attachment",
        "fieldtype": "Attach",
        "insert_after": "custom_aadhar_number",
        "description": "PDF, max 5MB.",
    },
    {
        # NOTE: elixiir's install.py anchored this at insert_after="grade", but
        # myhr's `custom_hr_controls_tab` already owns that anchor. Anchoring
        # both at "grade" would push one of them into the wrong tab. Move this
        # to insert_after="branch" — still on the Overview tab, just earlier
        # in the field order. See ELIXIIR_MYHR_INTEGRATION.md Issue 1.
        "dt": "Employee",
        "fieldname": "custom_total_experience_years",
        "label": "Total Years of Experience",
        "fieldtype": "Float",
        "insert_after": "branch",
        "description": "Total prior work experience in years (HR-set).",
    },

    # ---- Personal Details additions: UAN, education, parents, children -------
    {
        "dt": "Employee",
        "fieldname": "custom_uan",
        "label": "UAN Number",
        "fieldtype": "Data",
        "insert_after": "provident_fund_account",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_highest_qualification",
        "label": "Highest Education Qualification",
        "fieldtype": "Data",
        "insert_after": "education",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_highest_qualification_institute",
        "label": "Highest Education Institute",
        "fieldtype": "Data",
        "insert_after": "custom_highest_qualification",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_highest_qualification_attachment",
        "label": "Degree Attachment",
        "fieldtype": "Attach",
        "insert_after": "custom_highest_qualification_institute",
        "description": "PDF, max 5MB.",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_father_name",
        "label": "Father's Name",
        "fieldtype": "Data",
        "insert_after": "personal_details",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_mother_name",
        "label": "Mother's Name",
        "fieldtype": "Data",
        "insert_after": "custom_father_name",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_children",
        "label": "Children",
        "fieldtype": "Table",
        "options": "Elixiir Child",
        "insert_after": "custom_mother_name",
    },

    # ---- Profile tab: past-company + bank-statement attachments --------------
    {
        "dt": "Employee",
        "fieldname": "custom_appointment_letter",
        "label": "Previous Company Appointment Letter",
        "fieldtype": "Attach",
        "insert_after": "bio",
        "description": "PDF, max 5MB.",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_resignation_email",
        "label": "Previous Company Resignation Email",
        "fieldtype": "Attach",
        "insert_after": "custom_appointment_letter",
        "description": "PDF, max 5MB.",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_relieving_letter",
        "label": "Previous Company Relieving Letter",
        "fieldtype": "Attach",
        "insert_after": "custom_resignation_email",
        "description": "PDF, max 5MB.",
    },
    {
        "dt": "Employee",
        "fieldname": "custom_bank_statement_6m",
        "label": "Bank Statement (Last 6 Months)",
        "fieldtype": "Attach",
        "insert_after": "custom_relieving_letter",
        "description": "PDF, max 5MB.",
    },
    # ----- AC-1: Save Draft audit timestamp on Employee Action Centre --------
    # Stamped by the save_action_centre_draft API on every user-initiated Save
    # Draft call. Server-side only; read-only + no_copy. NULL = never saved by
    # user (auto-created AC). Drives the home-card label: "Start your details"
    # (NULL) vs "Draft saved <time>" (set). Spec: docs/superpowers/specs/
    # 2026-05-01-ac-save-draft-design.md §5.1
    {
        "dt": "Employee Action Centre",
        "fieldname": "custom_last_saved_at",
        "label": "Last Saved At",
        "fieldtype": "Datetime",
        "insert_after": "submitted_on",
        "read_only": 1,
        "no_copy": 1,
        "description": (
            "Server-stamped timestamp on every Save Draft. "
            "NULL means the AC was created but never saved by the user."
        ),
    },
    # ----- Expense Claim Detail: free-text Remarks per line ------------------
    # The PWA modal renders the stock `description` field as a read-only "About"
    # block populated from the Expense Claim Type's static description. Remarks
    # is the writable counterpart — the claimant's own note to the approver.
    {
        "dt": "Expense Claim Detail",
        "fieldname": "custom_remarks",
        "label": "Remarks",
        "fieldtype": "Long Text",
        "insert_after": "description",
        "description": "Claimant's free-text note to the approver for this line item.",
    },
    # ----- Shift Type: auto-checkout at end-of-day --------------------------
    # When ticked, the scheduler at 23:55 inserts an OUT Employee Checkin at
    # 23:59 for every Active employee on this shift who has an IN today but
    # no OUT. Skips holidays + approved leaves. HRMS's per-shift auto-
    # attendance sweep then sees the IN+OUT pair on the next run and creates
    # the Present Attendance row. No-op unless `enable_auto_attendance` is
    # also ticked on the same Shift Type.
    {
        "dt": "Shift Type",
        "fieldname": "custom_auto_checkout_at_eod",
        "label": "Auto Check-Out at End of Day",
        "fieldtype": "Check",
        "insert_after": "mark_auto_attendance_on_holidays",
        "default": "0",
        "description": (
            "When ticked, the daily 23:55 scheduler inserts an OUT "
            "Employee Checkin at 23:59 for every Active employee on this "
            "shift who has an IN today but no OUT. Skips holidays + "
            "employees on approved Leave. Auto-attendance sweep then "
            "marks the day Present. Requires Enable Auto Attendance also "
            "ticked to have any effect."
        ),
    },
    # ----- Expense Claim: persist approver name (fetched from User) ----------
    # The PWA references `expense_approver_name` everywhere (list rows,
    # success modal, status banner subtitle, detail header) but stock HRMS
    # never persists it — `setExpenseApprover` writes it to the in-memory
    # claim and it gets silently dropped on save. Result: every surface
    # falls back to displaying the email. `fetch_from` auto-populates it
    # from `expense_approver.full_name` on validate, no controller code.
    # NOTE: fieldname is intentionally unprefixed because the entire PWA
    # codebase already references `expense_approver_name`. Renaming it
    # would touch every claim surface.
    {
        "dt": "Expense Claim",
        "fieldname": "expense_approver_name",
        "label": "Expense Approver Name",
        "fieldtype": "Data",
        "insert_after": "expense_approver",
        "fetch_from": "expense_approver.full_name",
        "read_only": 1,
        "hidden": 1,
        "no_copy": 1,
        "description": (
            "Read-only mirror of expense_approver's User.full_name. Populated "
            "via fetch_from on validate so PWA surfaces show the approver's "
            "full name instead of their email."
        ),
    },
]


def _ensure_holiday_type_options():
    """Merge Weekly Off into Holiday custom_holiday_type options for existing installs."""
    if not frappe.db.exists("Custom Field", "Holiday-custom_holiday_type"):
        return
    cf_name = "Holiday-custom_holiday_type"
    cur = frappe.db.get_value("Custom Field", cf_name, "options") or ""
    opts = [o.strip() for o in cur.split("\n") if o.strip()]
    if "Weekly Off" in opts:
        return
    opts.append("Weekly Off")
    frappe.db.set_value("Custom Field", cf_name, "options", "\n".join(opts))
    frappe.logger().info("myHR: Updated Holiday custom_holiday_type options (Weekly Off).")


# Every attr we honour from MYHR_CUSTOM_FIELDS entries on Custom Field create.
# Old code only set a subset; SET-1 extended this to cover read_only, reqd,
# permlevel, hidden, etc. — without these, fields like `custom_approved_by`
# silently land as editable on the Desk form even though the dict says
# `read_only:1`.
_CUSTOM_FIELD_PASSTHROUGH_ATTRS = (
    "label", "fieldtype", "insert_after", "options", "default", "description",
    "bold", "in_list_view", "in_standard_filter", "unique",
    "read_only", "reqd", "hidden", "no_copy", "print_hide",
    "permlevel", "translatable", "non_negative", "ignore_user_permissions",
    "depends_on", "mandatory_depends_on", "read_only_depends_on",
    "fetch_from", "fetch_if_empty", "length", "precision",
)


def _ensure_custom_fields():
    """
    Creates myHR custom fields only if they don't already exist.
    If another app/developer has already created these fields, we leave them
    untouched (skip-if-exists). Use the v1_8 patch to repair already-installed
    fields that drift from the declared attrs.

    Honoured attrs are listed in `_CUSTOM_FIELD_PASSTHROUGH_ATTRS`. Anything
    extra in the dict is ignored.
    """
    for field_def in MYHR_CUSTOM_FIELDS:
        field_name = "{dt}-{fieldname}".format(**field_def)
        if frappe.db.exists("Custom Field", field_name):
            frappe.logger().info(
                f"myHR: Custom Field '{field_name}' already exists — skipping."
            )
            continue

        cf = frappe.new_doc("Custom Field")
        cf.dt = field_def["dt"]
        cf.fieldname = field_def["fieldname"]
        for attr in _CUSTOM_FIELD_PASSTHROUGH_ATTRS:
            if attr in field_def:
                setattr(cf, attr, field_def[attr])
        cf.insert(ignore_permissions=True)
        frappe.logger().info(f"myHR: Created Custom Field '{field_name}'.")
