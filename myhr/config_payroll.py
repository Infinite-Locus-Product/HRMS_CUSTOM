"""Centralized payroll / leave constants for myhr.

Single source of truth for the numeric knobs the Elixiir customizations rely
on. Kept as plain Python constants for now (Phase 0 Option A). If HR ever
needs to tune these from Desk, migrate to a `myHR Payroll Settings` Single
doctype — only this module + its readers change.

See docs/ELIXIIR_MYHR_INTEGRATION.md for the rationale.
"""

# ---------------------------------------------------------------------------
# NOTE: Salary Structure breakup is now standard ERPNext. HR builds the
# Salary Structure in Desk with standard Formula components driven by `base`,
# and enters the base/gross on the Salary Structure Assignment. The former
# hardcoded CTC->base formula (compute_base_from_ctc) and SS_* breakup ratios
# have been removed — the auto-assigner copies Employee.ctc straight to
# SSA.base with no formula.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Leave Type defaults — match the Elixiir 2026 leave policy.
# These are used by the installer when it creates the four Leave Types.
# Once installed, HR can edit them on the Leave Type form directly.
# ---------------------------------------------------------------------------
PL_MAX_LEAVES = 14
PL_MAX_CARRY_FORWARD = 30
PL_ROUNDING = 0.5
PL_EARNED_FREQUENCY = "Monthly"
PL_ALLOCATE_ON_DAY = "Last Day"

CL_MAX_LEAVES = 7
CL_MAX_CONTINUOUS_DAYS = 2

SL_MAX_LEAVES = 7

ML_MAX_LEAVES = 182
ML_APPLICABLE_AFTER_DAYS = 80

# Encashment caps for Privilege Leave. 0 = no cap (default per setup guide
# section 18.2 Interpretation 1 = full balance encashment at separation).
PL_MAX_ENCASHABLE = 0
PL_NON_ENCASHABLE = 0

# ---------------------------------------------------------------------------
# Salary Component fixtures used by the installer.
# ---------------------------------------------------------------------------
LEAVE_ENCASHMENT_COMPONENT = "Leave Encashment"
LEAVE_ENCASHMENT_ABBR = "LE"

# ---------------------------------------------------------------------------
# Holiday calendar 2026 — Annexure A of the Elixiir leave policy. Edit here
# (or via Desk after install) when the new year's calendar is published.
# Format: (date_iso, description). Bakra Id is tentative until announced.
# ---------------------------------------------------------------------------
HOLIDAYS_2026 = [
    ("2026-01-01", "New Year"),
    ("2026-01-26", "Republic Day"),
    ("2026-03-04", "Holi"),
    ("2026-04-03", "Good Friday"),
    ("2026-05-28", "Bakra Id / Eid-Ul-Adha (tentative)"),
    ("2026-08-15", "Independence Day"),
    ("2026-08-21", "Rakshabandhan"),
    ("2026-10-02", "Gandhi Jayanti"),
    ("2026-10-20", "Dussehra"),
    ("2026-11-09", "Diwali"),
    ("2026-11-24", "Gurupurab"),
    ("2026-12-25", "Christmas"),
]
