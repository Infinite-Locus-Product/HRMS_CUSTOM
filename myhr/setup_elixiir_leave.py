"""Fixxly leave / payroll fixture installer.

HR runs `install_elixiir_leave_setup(company, year)` once per company.
Idempotent — re-running is safe and only creates missing artefacts.

Each helper is whitelisted-friendly (no global state mutation) and skips
artefacts that already exist. Failures collect into a `warnings` list so
HR can act on them; nothing here should ever raise.
"""

import frappe
from frappe import _

from myhr.config_payroll import (
    CL_MAX_CONTINUOUS_DAYS,
    CL_MAX_LEAVES,
    HOLIDAYS_2026,
    LEAVE_ENCASHMENT_ABBR,
    LEAVE_ENCASHMENT_COMPONENT,
    ML_APPLICABLE_AFTER_DAYS,
    ML_MAX_LEAVES,
    PL_ALLOCATE_ON_DAY,
    PL_EARNED_FREQUENCY,
    PL_MAX_CARRY_FORWARD,
    PL_MAX_ENCASHABLE,
    PL_MAX_LEAVES,
    PL_NON_ENCASHABLE,
    PL_ROUNDING,
    SL_MAX_LEAVES,
)


# ---------------------------------------------------------------------------
# Holiday list
# ---------------------------------------------------------------------------
def ensure_holiday_list(year, name=None, report=None):
    """Create `Fixxly Holiday List <year>` with Sat+Sun weekly offs.

    For 2026, also seed the 12 public holidays from config_payroll.HOLIDAYS_2026.
    Idempotent — returns the existing doc name if already present.
    """
    list_name = name or f"Fixxly Holiday List {year}"
    if frappe.db.exists("Holiday List", list_name):
        frappe.logger().info(f"myhr elixiir setup: holiday list {list_name} exists, skipping")
        if report is not None:
            report["skipped"].append(f"Holiday List: {list_name}")
        return list_name

    hl = frappe.new_doc("Holiday List")
    hl.holiday_list_name = list_name
    hl.from_date = f"{year}-01-01"
    hl.to_date = f"{year}-12-31"
    hl.country = "India"

    # weekly_off is a single Select; populate Sat then Sun via two passes.
    for off_day in ("Sunday", "Saturday"):
        hl.weekly_off = off_day
        hl.get_weekly_off_dates()
    # Final value left on the doc — pick Sunday so the form shows something
    # consistent if HR re-opens it.
    hl.weekly_off = "Sunday"

    if int(year) == 2026:
        existing_dates = {h.holiday_date for h in hl.holidays}
        for date_iso, description in HOLIDAYS_2026:
            from frappe.utils import getdate
            d = getdate(date_iso)
            if d in existing_dates:
                continue
            hl.append("holidays", {
                "holiday_date": d,
                "description": description,
                "weekly_off": 0,
            })

    hl.flags.ignore_permissions = True
    hl.insert(ignore_permissions=True)
    frappe.logger().info(f"myhr elixiir setup: created Holiday List {list_name}")
    if report is not None:
        report["created"].append(f"Holiday List: {list_name}")
    return list_name


# ---------------------------------------------------------------------------
# Leave Period
# ---------------------------------------------------------------------------
def ensure_leave_period(year, company, holiday_list_name=None, report=None):
    """Create `Fixxly <year>` Leave Period bound to the company."""
    period_name = f"Fixxly {year}"
    if frappe.db.exists("Leave Period", period_name):
        frappe.logger().info(f"myhr elixiir setup: leave period {period_name} exists, skipping")
        if report is not None:
            report["skipped"].append(f"Leave Period: {period_name}")
        return period_name

    lp = frappe.new_doc("Leave Period")
    lp.name = period_name
    lp.from_date = f"{year}-01-01"
    lp.to_date = f"{year}-12-31"
    lp.is_active = 1
    lp.company = company
    if holiday_list_name and frappe.db.exists("Holiday List", holiday_list_name):
        lp.optional_holiday_list = holiday_list_name
    lp.flags.ignore_permissions = True
    lp.insert(ignore_permissions=True)
    frappe.logger().info(f"myhr elixiir setup: created Leave Period {period_name}")
    if report is not None:
        report["created"].append(f"Leave Period: {period_name}")
    return period_name


# ---------------------------------------------------------------------------
# Leave Encashment salary component
# ---------------------------------------------------------------------------
def ensure_leave_encashment_component(company, report=None):
    """Create `Leave Encashment` Salary Component (Earning, taxable, days-independent)."""
    name = LEAVE_ENCASHMENT_COMPONENT
    if frappe.db.exists("Salary Component", name):
        frappe.logger().info(f"myhr elixiir setup: salary component {name} exists, skipping")
        if report is not None:
            report["skipped"].append(f"Salary Component: {name}")
        return name

    sc = frappe.new_doc("Salary Component")
    sc.salary_component = name
    sc.salary_component_abbr = LEAVE_ENCASHMENT_ABBR
    sc.type = "Earning"
    sc.is_tax_applicable = 1
    sc.depends_on_payment_days = 0
    sc.do_not_include_in_total = 0

    abbr = frappe.db.get_value("Company", company, "abbr")
    account_name = f"Salary - {abbr}" if abbr else None
    if account_name and frappe.db.exists("Account", account_name):
        sc.append("accounts", {
            "company": company,
            "account": account_name,
        })
    else:
        msg = (
            f"Salary Component {name} created without account mapping; "
            f"expected account 'Salary - {abbr}' was not found. HR should "
            f"map an account on the component before running payroll."
        )
        frappe.logger().info(f"myhr elixiir setup: {msg}")
        if report is not None:
            report["warnings"].append(msg)

    sc.flags.ignore_permissions = True
    sc.insert(ignore_permissions=True)
    frappe.logger().info(f"myhr elixiir setup: created Salary Component {name}")
    if report is not None:
        report["created"].append(f"Salary Component: {name}")
    return name


# ---------------------------------------------------------------------------
# Leave Types
# ---------------------------------------------------------------------------
def _ensure_leave_type(name, payload, report=None):
    if frappe.db.exists("Leave Type", name):
        frappe.logger().info(f"myhr elixiir setup: leave type {name} exists, skipping")
        if report is not None:
            report["skipped"].append(f"Leave Type: {name}")
        return name
    lt = frappe.new_doc("Leave Type")
    lt.leave_type_name = name
    for k, v in payload.items():
        lt.set(k, v)
    lt.flags.ignore_permissions = True
    lt.insert(ignore_permissions=True)
    frappe.logger().info(f"myhr elixiir setup: created Leave Type {name}")
    if report is not None:
        report["created"].append(f"Leave Type: {name}")
    return name


def ensure_leave_types(report=None):
    """Create the four Fixxly leave types (PL / CL / SL / ML)."""
    _ensure_leave_type("Privilege Leave", {
        "max_leaves_allowed": PL_MAX_LEAVES,
        "is_earned_leave": 1,
        "allocate_on_day": PL_ALLOCATE_ON_DAY,
        "earned_leave_frequency": PL_EARNED_FREQUENCY,
        "rounding": PL_ROUNDING,
        "is_carry_forward": 1,
        "maximum_carry_forwarded_leaves": PL_MAX_CARRY_FORWARD,
        "allow_encashment": 1,
        "max_encashable_leaves": PL_MAX_ENCASHABLE,
        "non_encashable_leaves": PL_NON_ENCASHABLE,
        "earning_component": LEAVE_ENCASHMENT_COMPONENT,
    }, report=report)

    _ensure_leave_type("Casual Leave", {
        "max_leaves_allowed": CL_MAX_LEAVES,
        "max_continuous_days_allowed": CL_MAX_CONTINUOUS_DAYS,
    }, report=report)

    _ensure_leave_type("Sick Leave", {
        "max_leaves_allowed": SL_MAX_LEAVES,
    }, report=report)

    _ensure_leave_type("Maternity Leave", {
        "max_leaves_allowed": ML_MAX_LEAVES,
        "applicable_after": ML_APPLICABLE_AFTER_DAYS,
        "allow_over_allocation": 1,
        "include_holiday": 1,
    }, report=report)


# ---------------------------------------------------------------------------
# Leave Policies
# ---------------------------------------------------------------------------
def _ensure_leave_policy(title, allocations, report=None):
    if frappe.db.exists("Leave Policy", {"title": title}):
        frappe.logger().info(f"myhr elixiir setup: leave policy {title} exists, skipping")
        if report is not None:
            report["skipped"].append(f"Leave Policy: {title}")
        return title
    lp = frappe.new_doc("Leave Policy")
    lp.title = title
    for leave_type, annual in allocations:
        if not frappe.db.exists("Leave Type", leave_type):
            msg = f"Leave Policy {title}: Leave Type {leave_type} missing, skipping row"
            frappe.logger().info(f"myhr elixiir setup: {msg}")
            if report is not None:
                report["warnings"].append(msg)
            continue
        lp.append("leave_policy_details", {
            "leave_type": leave_type,
            "annual_allocation": annual,
        })
    lp.flags.ignore_permissions = True
    lp.insert(ignore_permissions=True)
    frappe.logger().info(f"myhr elixiir setup: created Leave Policy {title}")
    if report is not None:
        report["created"].append(f"Leave Policy: {title}")
    return title


def ensure_leave_policies(company, report=None):
    """Create the Probation + Confirmed leave policies."""
    _ensure_leave_policy("Fixxly Probation Leave Policy", [
        ("Casual Leave", CL_MAX_LEAVES),
        ("Sick Leave", SL_MAX_LEAVES),
        ("Maternity Leave", ML_MAX_LEAVES),
    ], report=report)

    _ensure_leave_policy("Fixxly Confirmed Leave Policy", [
        ("Privilege Leave", PL_MAX_LEAVES),
        ("Casual Leave", CL_MAX_LEAVES),
        ("Sick Leave", SL_MAX_LEAVES),
        ("Maternity Leave", ML_MAX_LEAVES),
    ], report=report)


# ---------------------------------------------------------------------------
# Salary Structure
# ---------------------------------------------------------------------------
# The Salary Structure is now standard ERPNext: HR builds it in Desk with
# standard Formula components (driven by `base`) and enters the base/gross on
# the Salary Structure Assignment. The former code-generated structure with
# hardcoded formula strings has been removed intentionally.


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------
@frappe.whitelist()
def install_elixiir_leave_setup(company, year=2026):
    """Idempotent one-shot installer. HR-only.

    Returns a dict report with `created`, `skipped`, `warnings` lists. Safe
    to re-run; existing artefacts are preserved.
    """
    roles = set(frappe.get_roles())
    if not ({"HR Manager", "System Manager"} & roles):
        frappe.throw(
            _("Only HR Manager / System Manager can install Fixxly leave setup."),
            frappe.PermissionError,
        )

    if not company or not frappe.db.exists("Company", company):
        frappe.throw(_("Valid Company is required."))

    year = int(year)
    report = {"created": [], "skipped": [], "warnings": []}

    holiday_list = ensure_holiday_list(year, report=report)
    ensure_leave_period(year, company, holiday_list_name=holiday_list, report=report)
    ensure_leave_encashment_component(company, report=report)
    ensure_leave_types(report=report)
    ensure_leave_policies(company, report=report)

    frappe.db.commit()
    return report
