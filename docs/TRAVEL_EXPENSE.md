# Travel & Expense Reimbursement — Feature Specification

> Authoritative spec for the **Travel & Expense Reimbursement** flow in myHR. Extends the existing `Expense Claim` override with per-diem caps by Grade × City Tier, per-km fuel-rate enforcement by Grade, a Submitted-for-Review window check, and an HR-Manager-routed cap-override path. Mirrors the layering pattern already used for Leave Application — see [`LEAVE_AND_ATTENDANCE.md`](LEAVE_AND_ATTENDANCE.md).

**App:** myHR
**Policy basis:** Elixiir Foods *Travel & Reimbursement Policy v1* (signed 20-03-2026)
**Compatibility:** Frappe 16.15.0 / ERPNext 16.14.0 / HRMS 16.5.0 (matches existing myHR matrix)

### Surfaces touched

| Surface | Owner | Action |
|---|---|---|
| `Expense Claim` (DocType) | stock HRMS | Already overridden by `myhr.overrides.expense_claim.ExpenseClaim`. **Extend the existing class** — do not replace it. |
| `Expense Claim Detail` (child) | stock HRMS | Custom fields only. No class override. |
| `Expense Claim Type` | stock HRMS | One custom field (`custom_per_diem_basis`) drives validation routing. |
| `Employee Grade` | stock Frappe | Two custom fields — fuel rate + default air class. |
| `Travel Request` | stock HRMS | Optional linkage from `Expense Claim`. No fields added. No validation gate. |
| `HR Settings` | stock HRMS | Section + four toggles in the existing "Expenses" tab. |
| `City Tier` | **NEW** myHR DocType | Holds the 19 seed cities + tier. HR-editable. |
| `Per Diem Cap Matrix` | **NEW** myHR DocType | Holds the 12 cap rows (Grade × Tier × Category). HR-editable. |

### Files

| Concern | File |
|---|---|
| Override class (extend) | [`apps/myhr/myhr/overrides/expense_claim.py`](../myhr/overrides/expense_claim.py) |
| Approval gate (extend) | [`apps/myhr/myhr/approval_gate.py`](../myhr/approval_gate.py) |
| Cap lookup helper (new) | `apps/myhr/myhr/expense_caps.py` |
| Custom-field declarations (extend) | [`apps/myhr/myhr/setup.py`](../myhr/setup.py) → `MYHR_CUSTOM_FIELDS` |
| Seed patches (new) | `apps/myhr/myhr/patches/v1_23_seed_city_tier.py`, `v1_24_seed_per_diem_caps.py`, `v1_25_seed_expense_claim_types.py` |
| Form-level JS (new) | `apps/myhr/myhr/public/js/expense_claim.js` (wire via `doctype_js` in `hooks.py`) |
| PWA Vue (extend) | `apps/myhr/myhr/frontend_changes/views/expense_claim/Form.vue` |

---

## 1. Purpose

Elixiir's Travel & Reimbursement Policy specifies four categories of spend (local conveyance, public transport, outstation travel, lodging/meals) with reimbursement rules that vary by **Grade** (CEO/COO, CXO, Others) and, for lodging and meals, by **City Tier** (1/2/3). myHR enforces these caps at the line-item level on `Expense Claim`, blocks submission of stale claims (>7 working days post-expense), and routes any cap-breach claim to HR Manager approval.

What myHR does **not** do (explicit non-goals):

- Enforce the 14-day air-advance-booking rule (policy is normative, not prescriptive; system has no flight-date data).
- Require a `Travel Request` to exist before an Expense Claim is filed (policy does not mandate system-level enforcement; HR handles via approval review).
- Enforce the "no journey <8 hours by air" rule (no flight-duration data source).
- Validate alcohol/personal/fines exclusion in the non-reimbursable list (descriptions are free-text; manual approver check).
- Enforce same/separate gender room-sharing combined-cap math (manual approver check).

These are deliberately out of scope — the policy itself doesn't make them system-enforceable.

---

## 2. User Stories

| # | As a … | I want to … | So that … |
|---|---|---|---|
| 1 | Employee | file an Expense Claim from the PWA with line items tagged to expense types | I can claim correctly per category |
| 2 | Employee | enter kilometres on a "Personal Vehicle" line and have the rupee amount auto-fill from my Grade | I don't have to remember the rate |
| 3 | Employee | pick a city on a Lodging line and see the daily cap appear inline | I know what the limit is before I submit |
| 4 | Employee | tap "Submit for Review" only once my draft is complete | the approver doesn't see half-finished claims |
| 5 | Employee | be told if I'm submitting >7 working days after the expense date | I can fix it before approval kicks back |
| 6 | Employee | request a cap override with a written justification when a legitimate breach occurred | I'm not blocked but the approval is escalated |
| 7 | Manager (named `expense_approver`) | approve normal claims as today | nothing changes for the routine path |
| 8 | HR Manager | be the only one able to approve cap-override claims | breaches receive the right level of scrutiny |
| 9 | HR Manager | edit the Per Diem Cap Matrix yearly when caps revise | I don't need a developer for the annual update |
| 10 | HR Manager | add a new city to City Tier when the company opens a new office | I can self-serve master data |

---

## 3. Data Model

### 3.1 New DocType — `City Tier`

**Path:** `apps/myhr/myhr/myhr/doctype/city_tier/`

| Attribute | Value |
|---|---|
| `name` (autoname) | field:city_name |
| `is_submittable` | 0 |
| `is_child_table` | 0 |
| `is_single` | 0 |
| `track_changes` | 1 |
| `module` | myHR |

#### Fields

| Fieldname | Label | Fieldtype | Options | Reqd | In List View | Description |
|---|---|---|---|:---:|:---:|---|
| `city_name` | City Name | Data | — | ✓ | ✓ | Unique. Used as the docname. |
| `tier` | Tier | Select | `1`<br>`2`<br>`3` | ✓ | ✓ | 1 / 2 / 3 per Elixiir policy. |
| `is_catchall` | Is Catch-all (Tier 3 default) | Check | — | — | — | Exactly one row should have this ticked — the row employees pick when the city isn't named. Default seed: "Other". |
| `notes` | Notes | Small Text | — | — | — | HR's free-text. |

#### Permissions

| Role | Read | Write | Create | Delete |
|---|:---:|:---:|:---:|:---:|
| System Manager | ✓ | ✓ | ✓ | ✓ |
| HR Manager | ✓ | ✓ | ✓ | ✓ |
| HR User | ✓ | — | — | — |
| Employee | ✓ | — | — | — |

Employees need read access so the Link dropdown on Expense Claim Detail resolves their selection.

#### Validation (`city_tier.py` controller)

```python
def validate(self):
    # Exactly one catch-all row across the table
    if self.is_catchall:
        existing = frappe.db.get_value(
            "City Tier",
            {"is_catchall": 1, "name": ("!=", self.name)},
            "name",
        )
        if existing:
            frappe.throw(
                _("Only one City Tier row can be marked Catch-all. {0} already is.").format(existing)
            )
```

### 3.2 New DocType — `Per Diem Cap Matrix`

**Path:** `apps/myhr/myhr/myhr/doctype/per_diem_cap_matrix/`

| Attribute | Value |
|---|---|
| `name` (autoname) | format:PDC-{grade}-T{city_tier}-{category} |
| `is_submittable` | 0 |
| `track_changes` | 1 |
| `module` | myHR |

#### Fields

| Fieldname | Label | Fieldtype | Options | Reqd | In List View | Description |
|---|---|---|---|:---:|:---:|---|
| `grade` | Grade | Link | Employee Grade | ✓ | ✓ | Pivot 1. |
| `city_tier` | City Tier | Select | `1`<br>`2`<br>`3` | ✓ | ✓ | Pivot 2. |
| `category` | Category | Select | `Lodging`<br>`Meal` | ✓ | ✓ | Pivot 3. |
| `daily_cap` | Daily Cap | Currency | INR | ✓ | ✓ | Per day, per employee. |
| `effective_from` | Effective From | Date | — | — | ✓ | When this row's value started applying. Used for audit, not for lookup. |
| `notes` | Notes | Small Text | — | — | — | HR's reasoning at the last revision. |

#### Validation

```python
def validate(self):
    # Composite uniqueness — grade × city_tier × category
    dupe = frappe.db.get_value(
        "Per Diem Cap Matrix",
        {
            "grade": self.grade,
            "city_tier": self.city_tier,
            "category": self.category,
            "name": ("!=", self.name),
        },
        "name",
    )
    if dupe:
        frappe.throw(
            _("A cap row already exists for {0} / Tier {1} / {2}: {3}").format(
                self.grade, self.city_tier, self.category, dupe
            )
        )
```

#### Permissions

Same as `City Tier` — HR-editable, Employee read-only.

### 3.3 Custom Fields — `Employee Grade` (2 new)

Appended to `MYHR_CUSTOM_FIELDS` in [`setup.py`](../myhr/setup.py).

```python
{
    "dt": "Employee Grade",
    "fieldname": "custom_per_km_fuel_rate",
    "label": "Per-km Fuel Reimbursement Rate",
    "fieldtype": "Currency",
    "options": "INR",
    "insert_after": "default_base_pay",
    "description": "Rupees per kilometre when an employee of this Grade uses their personal vehicle for official travel. Home-to-office commute excluded. Policy: CEO/COO ₹15, CXOs ₹10, Others ₹6.",
},
{
    "dt": "Employee Grade",
    "fieldname": "custom_default_air_class",
    "label": "Default Air Class",
    "fieldtype": "Select",
    "options": "\nEconomy\nPremium Economy\nBusiness\nFirst",
    "insert_after": "custom_per_km_fuel_rate",
    "description": "Default air-travel class for this Grade. Policy: CEO/COO Premium Economy, others Economy. Informational only — not enforced server-side; surfaces in form UI as a hint.",
},
```

### 3.4 Custom Fields — `Expense Claim Type` (1 new)

```python
{
    "dt": "Expense Claim Type",
    "fieldname": "custom_per_diem_basis",
    "label": "Per-Diem / Validation Basis",
    "fieldtype": "Select",
    "options": "\nLodging Cap\nMeal Cap\nPersonal Vehicle Fuel\nActuals",
    "insert_after": "deferred_expense_account",  # or last existing field — see install order
    "default": "Actuals",
    "description": (
        "How myHR validates lines of this expense type. "
        "'Lodging Cap' / 'Meal Cap' → lookup in Per Diem Cap Matrix by Grade × City Tier. "
        "'Personal Vehicle Fuel' → auto-fill amount from Grade × kilometres. "
        "'Actuals' → no system validation (Auto/Rickshaw, Bus/Metro, Cab, Office Purchases, Team Meals, etc.)."
    ),
},
```

This single Select drives the entire validation routing — see §5.

### 3.5 Custom Fields — `Expense Claim` (4 new, on top of the 4 already present)

Existing: `custom_rejection_reason`, `custom_submitted_for_review`, `custom_submitted_on`, `custom_submitted_by`.

New:

```python
{
    "dt": "Expense Claim",
    "fieldname": "custom_travel_request",
    "label": "Travel Request",
    "fieldtype": "Link",
    "options": "Travel Request",
    "insert_after": "department",
    "description": "Optional link to a pre-authorised Travel Request. Not enforced — policy treats pre-auth as an HR-review check.",
},
{
    "dt": "Expense Claim",
    "fieldname": "custom_cap_override",
    "label": "Request Cap Override",
    "fieldtype": "Check",
    "insert_after": "custom_submitted_by",
    "default": "0",
    "description": (
        "Tick when a line item breaches the Per Diem Cap and the employee believes the breach is justified. "
        "Ticking forces HR-Manager-only approval (the named Expense Approver cannot approve). "
        "Justification is mandatory."
    ),
},
{
    "dt": "Expense Claim",
    "fieldname": "custom_cap_override_justification",
    "label": "Cap Override Justification",
    "fieldtype": "Small Text",
    "insert_after": "custom_cap_override",
    "mandatory_depends_on": "eval:doc.custom_cap_override==1",
    "depends_on": "eval:doc.custom_cap_override==1",
    "description": "Written reason for the breach. Visible to HR Manager during review.",
},
{
    "dt": "Expense Claim",
    "fieldname": "custom_total_cap_breach_amount",
    "label": "Total Cap Breach (computed)",
    "fieldtype": "Currency",
    "options": "INR",
    "insert_after": "custom_cap_override_justification",
    "read_only": 1,
    "no_copy": 1,
    "description": "Sum of per-line overage across all child rows that exceed their daily cap. Server-computed in validate.",
},
```

### 3.6 Custom Fields — `Expense Claim Detail` (6 new)

```python
{
    "dt": "Expense Claim Detail",
    "fieldname": "custom_expense_city",
    "label": "City",
    "fieldtype": "Link",
    "options": "City Tier",
    "insert_after": "expense_type",
    "mandatory_depends_on": "eval:['Lodging Cap','Meal Cap'].includes(parent.get_expense_type_basis(doc.expense_type))",
    "description": (
        "City where the expense was incurred. Required for Lodging and Meal lines. "
        "Tier is derived from the selected City Tier row."
    ),
},
{
    "dt": "Expense Claim Detail",
    "fieldname": "custom_is_personal_vehicle",
    "label": "Personal Vehicle",
    "fieldtype": "Check",
    "insert_after": "custom_expense_city",
    "default": "0",
    "depends_on": "eval:parent.get_expense_type_basis(doc.expense_type)==='Personal Vehicle Fuel'",
    "description": "Tick when reimbursing personal-vehicle fuel use. Reveals the kilometres field.",
},
{
    "dt": "Expense Claim Detail",
    "fieldname": "custom_kilometres",
    "label": "Kilometres",
    "fieldtype": "Float",
    "insert_after": "custom_is_personal_vehicle",
    "depends_on": "eval:doc.custom_is_personal_vehicle==1",
    "mandatory_depends_on": "eval:doc.custom_is_personal_vehicle==1",
    "precision": "2",
    "description": "Total kilometres driven (excluding home-to-office commute). Amount = kilometres × Grade fuel rate.",
},
{
    "dt": "Expense Claim Detail",
    "fieldname": "custom_fuel_rate_applied",
    "label": "Fuel Rate Applied",
    "fieldtype": "Currency",
    "options": "INR",
    "insert_after": "custom_kilometres",
    "read_only": 1,
    "no_copy": 1,
    "description": "Per-km rate from the employee's Grade at validate-time. Snapshotted for audit.",
},
{
    "dt": "Expense Claim Detail",
    "fieldname": "custom_daily_cap_applied",
    "label": "Daily Cap Applied",
    "fieldtype": "Currency",
    "options": "INR",
    "insert_after": "custom_fuel_rate_applied",
    "read_only": 1,
    "no_copy": 1,
    "description": "Cap looked up from Per Diem Cap Matrix at validate-time (only for Lodging Cap / Meal Cap lines).",
},
{
    "dt": "Expense Claim Detail",
    "fieldname": "custom_overage_amount",
    "label": "Overage",
    "fieldtype": "Currency",
    "options": "INR",
    "insert_after": "custom_daily_cap_applied",
    "read_only": 1,
    "no_copy": 1,
    "description": "max(0, sanctioned_amount − daily_cap_applied). Non-zero values count toward parent.custom_total_cap_breach_amount.",
},
```

### 3.7 Custom Fields — `HR Settings` (5 new — Travel & Expense policy)

The existing "Expenses" tab on `HR Settings` already holds the EC approver toggles ([setup.py:1150+](../myhr/setup.py)). Append a Travel & Expense section to the same tab.

```python
{
    "dt": "HR Settings",
    "fieldname": "custom_te_policy_section",
    "label": "Travel & Expense Policy",
    "fieldtype": "Section Break",
    "insert_after": "custom_ec_approver_accounts_manager",  # last existing EC toggle
    "collapsible": 1,
},
{
    "dt": "HR Settings",
    "fieldname": "custom_te_enforce_caps",
    "label": "Enforce Per-Diem Caps",
    "fieldtype": "Check",
    "insert_after": "custom_te_policy_section",
    "default": "1",
    "description": (
        "When ticked, lines exceeding their daily cap force the cap-override flow. "
        "Untick to disable cap enforcement company-wide (validation runs but no breach is logged). "
        "Useful during initial rollout while master data is being cleaned up."
    ),
},
{
    "dt": "HR Settings",
    "fieldname": "custom_te_enforce_fuel_rate",
    "label": "Enforce Personal-Vehicle Fuel Rate",
    "fieldtype": "Check",
    "insert_after": "custom_te_enforce_caps",
    "default": "1",
    "description": (
        "When ticked, personal-vehicle lines auto-compute amount = kilometres × Grade rate "
        "and overwrite any manual amount the employee entered. Untick to let employees enter amounts freely."
    ),
},
{
    "dt": "HR Settings",
    "fieldname": "custom_te_submission_window_days",
    "label": "Submission Window (Working Days)",
    "fieldtype": "Int",
    "insert_after": "custom_te_enforce_fuel_rate",
    "default": "7",
    "description": (
        "Days between latest expense_date in the claim and the Submit-for-Review action. "
        "Counted in working days (Mon–Fri, excluding the employee's Holiday List). "
        "Set to 0 to disable the check."
    ),
},
{
    "dt": "HR Settings",
    "fieldname": "custom_te_block_late_submission",
    "label": "Block Late Submission",
    "fieldtype": "Check",
    "insert_after": "custom_te_submission_window_days",
    "default": "0",
    "description": (
        "When ticked, the Submit-for-Review action hard-fails if the window is exceeded. "
        "Default OFF — myHR shows a warning but lets the employee submit, leaving the decision to the approver."
    ),
},
```

> **Why "warn, don't block" as default:** the policy doesn't explicitly state that late claims must be rejected. The cleaner UX is to flag late submissions to the approver and let them decide; HR can flip this toggle later if it proves too lenient.

---

## 4. Approval Policy — Cap Override

The existing single-stage approval pattern is preserved:

| Caller | Normal claim | Claim with `custom_cap_override = 1` |
|---|:---:|:---:|
| Applicant (self) | — | — |
| `expense_approver` (named on the claim) | ✓ (if `custom_ec_approver_designated` is on) | ✗ — blocked even if designated toggle is on |
| Accounts Manager role | ✓ (if `custom_ec_approver_accounts_manager` is on) | ✗ — blocked even if accounts toggle is on |
| HR Manager / System Manager role | ✓ (if `custom_ec_approver_hr_manager` is on) | ✓ — only path that approves an override claim |
| Administrator | ✓ | ✓ |

When `custom_cap_override = 1`, the only authorised approvers are HR Manager and System Manager — the designated and accounts-manager paths are temporarily neutralised for that document. Existing `prevent_self_expense_approval` still applies on top.

---

## 5. Backend Behaviour

### 5.1 Cap lookup helper module — `myhr/expense_caps.py` (new)

A thin module that wraps the four lookups the override needs. Centralised so the override class, the form JS endpoint, and the seed patches all use the same code path.

```python
"""Cap and rate lookups for Travel & Expense reimbursement.

Single source of truth for the four lookups the Expense Claim validator and
the PWA inline-validation API both need:

  - daily cap for (grade, tier, category) → Per Diem Cap Matrix
  - per-km fuel rate for a grade → Employee Grade.custom_per_km_fuel_rate
  - default air class for a grade → Employee Grade.custom_default_air_class
  - tier for a city → City Tier.tier (with catch-all fallback)

All four return None / 0 / "" when the lookup misses; callers decide what to
do with a miss (the override class treats a None cap as "no enforcement",
which is the correct behaviour for CEO/COO who have no cap rows seeded).
"""

import frappe


def get_daily_cap(grade: str, city_tier: str, category: str) -> float | None:
    """Return the daily cap for (grade, tier, category).

    `city_tier` is the string "1" / "2" / "3" (matching the Select options).
    `category` is "Lodging" or "Meal".

    Returns None when no matching row exists — callers (the override class)
    treat that as "no enforcement", which is correct for CEO/COO (policy:
    actuals, no cap, no rows seeded).
    """
    if not (grade and city_tier and category):
        return None
    val = frappe.db.get_value(
        "Per Diem Cap Matrix",
        {"grade": grade, "city_tier": city_tier, "category": category},
        "daily_cap",
    )
    return float(val) if val is not None else None


def get_fuel_rate(grade: str) -> float:
    """Return the per-km fuel rate for a Grade. 0 when missing."""
    if not grade:
        return 0.0
    val = frappe.db.get_value(
        "Employee Grade", grade, "custom_per_km_fuel_rate"
    )
    return float(val or 0)


def get_default_air_class(grade: str) -> str:
    if not grade:
        return ""
    return frappe.db.get_value(
        "Employee Grade", grade, "custom_default_air_class"
    ) or ""


def get_city_tier(city_name: str) -> str | None:
    """Return tier as "1" / "2" / "3", or the catch-all row's tier when the
    named city doesn't exist. Returns None only when neither the named city
    nor a catch-all exists (shouldn't happen post-seed).
    """
    if not city_name:
        return None
    tier = frappe.db.get_value("City Tier", city_name, "tier")
    if tier:
        return tier
    return frappe.db.get_value(
        "City Tier", {"is_catchall": 1}, "tier"
    )


def get_expense_type_basis(expense_type: str) -> str:
    """Return Expense Claim Type.custom_per_diem_basis (or 'Actuals' default)."""
    if not expense_type:
        return "Actuals"
    return frappe.db.get_value(
        "Expense Claim Type", expense_type, "custom_per_diem_basis"
    ) or "Actuals"
```

### 5.2 Override class — extend `ExpenseClaim`

The existing override at [`overrides/expense_claim.py`](../myhr/overrides/expense_claim.py) already handles `_enforce_rejection_remarks()` and the single-stage auto-submit. Append four new validations.

```python
"""Single-stage Expense Claim + per-diem caps + fuel rate + submission window.

Extends the existing override:
- `_enforce_rejection_remarks` (already present, EC-1)
- single-stage auto-submit in `on_update` (already present)
- NEW: `_enforce_fuel_rate` (TE-1) — auto-fill personal-vehicle line amounts
- NEW: `_enforce_per_line_caps` (TE-2) — daily-cap lookup, write computed fields,
  drive cap-breach total
- NEW: `_enforce_cap_override` (TE-3) — require justification + signal HR-only path
- NEW: `_check_submission_window` (TE-4) — warn or block on stale claims
"""

import frappe
from frappe import _
from frappe.utils import getdate, today, get_datetime
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim as HRMSExpenseClaim

from myhr import expense_caps


class ExpenseClaim(HRMSExpenseClaim):
    def validate(self):
        # The order matters: super().validate() computes sanctioned_amount;
        # we then snapshot cap/rate state into the child rows; THEN the gate
        # in approval_gate.py (wired via doc_events.validate) reads those fields.
        super().validate()
        self._enforce_rejection_remarks()
        self._enforce_fuel_rate()       # TE-1
        self._enforce_per_line_caps()   # TE-2
        self._enforce_cap_override()    # TE-3
        self._check_submission_window() # TE-4

    # -------- TE-1: personal-vehicle fuel auto-fill --------

    def _enforce_fuel_rate(self):
        """Auto-compute amount = kilometres × Grade fuel rate on personal-vehicle
        lines. Snapshots the applied rate onto the line for audit.

        Controlled by HR Settings.custom_te_enforce_fuel_rate — when off, the
        line's amount field is left as the employee entered it (legacy paths
        / accounts adjustments)."""
        if not frappe.db.get_single_value("HR Settings", "custom_te_enforce_fuel_rate"):
            return

        grade = frappe.db.get_value("Employee", self.employee, "grade")
        rate = expense_caps.get_fuel_rate(grade)

        for row in self.expenses or []:
            basis = expense_caps.get_expense_type_basis(row.expense_type)
            if basis != "Personal Vehicle Fuel":
                # Clear stale snapshot if expense_type changed
                row.custom_fuel_rate_applied = 0
                continue
            if not row.custom_is_personal_vehicle:
                continue
            if not row.custom_kilometres:
                frappe.throw(
                    _("Row {0}: Kilometres is required for a Personal Vehicle line.").format(row.idx)
                )
            if not rate:
                frappe.throw(
                    _(
                        "No per-km fuel rate is configured for the employee's Grade ({0}). "
                        "Ask HR to set Employee Grade → {0} → Per-km Fuel Reimbursement Rate."
                    ).format(grade or "<missing>")
                )
            row.custom_fuel_rate_applied = rate
            row.amount = round(float(row.custom_kilometres) * rate, 2)
            # sanctioned_amount mirrors amount unless approver edits it down
            if not row.sanctioned_amount or row.sanctioned_amount > row.amount:
                row.sanctioned_amount = row.amount

    # -------- TE-2: per-line daily caps --------

    def _enforce_per_line_caps(self):
        """For each Lodging / Meal line, look up the daily cap from
        Per Diem Cap Matrix by (Grade, City Tier, Category) and snapshot
        cap + overage onto the row. Aggregate parent's total breach amount.

        A NULL cap (e.g. CEO/COO — no rows seeded) means no enforcement and
        no overage. A zero cap means HR explicitly set it to zero (which
        WOULD be an overage); use is_null check, not falsy.

        Controlled by HR Settings.custom_te_enforce_caps.
        """
        # Reset parent breach total — recomputed every validate
        self.custom_total_cap_breach_amount = 0

        if not frappe.db.get_single_value("HR Settings", "custom_te_enforce_caps"):
            for row in self.expenses or []:
                row.custom_daily_cap_applied = 0
                row.custom_overage_amount = 0
            return

        grade = frappe.db.get_value("Employee", self.employee, "grade")
        total_breach = 0.0

        for row in self.expenses or []:
            basis = expense_caps.get_expense_type_basis(row.expense_type)
            if basis not in ("Lodging Cap", "Meal Cap"):
                row.custom_daily_cap_applied = 0
                row.custom_overage_amount = 0
                continue

            if not row.custom_expense_city:
                frappe.throw(
                    _(
                        "Row {0}: City is required for a {1} line — used to look up the "
                        "applicable daily cap."
                    ).format(row.idx, basis)
                )

            tier = expense_caps.get_city_tier(row.custom_expense_city)
            category = "Lodging" if basis == "Lodging Cap" else "Meal"
            cap = expense_caps.get_daily_cap(grade, tier, category)

            if cap is None:
                # No row seeded for this (grade, tier, category) → no cap → no enforcement.
                # Correct for CEO/COO. Wrong for others = means HR forgot to seed; we
                # log it but don't block (treat as actuals).
                row.custom_daily_cap_applied = 0
                row.custom_overage_amount = 0
                continue

            row.custom_daily_cap_applied = cap
            sanctioned = float(row.sanctioned_amount or row.amount or 0)
            overage = max(0.0, sanctioned - cap)
            row.custom_overage_amount = overage
            total_breach += overage

        self.custom_total_cap_breach_amount = round(total_breach, 2)

    # -------- TE-3: cap-override gate --------

    def _enforce_cap_override(self):
        """If any line has overage and the employee hasn't ticked cap-override,
        block submission. If they have, require justification.

        Note: this runs on every validate, including the auto-submit cascade.
        The gate is checked at Submit-for-Review (when custom_submitted_for_review
        is being set from 0 → 1) and at docstatus 0 → 1 (final submit).
        It is NOT checked on plain Draft saves so the employee can iterate.
        """
        breach = float(self.custom_total_cap_breach_amount or 0)
        if breach <= 0:
            return

        previous = self.get_doc_before_save()
        prev_submitted = bool(previous.custom_submitted_for_review) if previous else False
        is_submitting_for_review = (
            bool(self.custom_submitted_for_review) and not prev_submitted
        )
        is_final_submit = self.docstatus == 1

        if not (is_submitting_for_review or is_final_submit):
            return  # Plain Draft save with overage — let the employee continue editing

        if not self.custom_cap_override:
            frappe.throw(
                _(
                    "Total cap breach is ₹{0:,.2f} across {1} line(s). "
                    "Tick 'Request Cap Override' and add a justification to submit, "
                    "or reduce the breaching line amounts to within cap."
                ).format(
                    breach,
                    sum(1 for r in self.expenses if (r.custom_overage_amount or 0) > 0),
                ),
                title=_("Cap breach — override required"),
            )

        if not (self.custom_cap_override_justification or "").strip():
            frappe.throw(
                _("Cap Override Justification is required when 'Request Cap Override' is ticked."),
                title=_("Justification required"),
            )

    # -------- TE-4: submission window --------

    def _check_submission_window(self):
        """When the employee taps Submit-for-Review (custom_submitted_for_review
        0 → 1), check the gap between today and the latest expense_date in the
        child table.

        Working days are counted using the employee's effective Holiday List
        (custom_holiday_list, falling back to native holiday_list, falling back
        to the Company default). If the window is 0, the check is disabled.
        """
        previous = self.get_doc_before_save()
        prev_submitted = bool(previous.custom_submitted_for_review) if previous else False
        is_submitting_for_review = (
            bool(self.custom_submitted_for_review) and not prev_submitted
        )
        if not is_submitting_for_review:
            return

        window = int(frappe.db.get_single_value("HR Settings", "custom_te_submission_window_days") or 0)
        if window <= 0:
            return

        latest_expense_date = max(
            (getdate(r.expense_date) for r in self.expenses if r.expense_date),
            default=None,
        )
        if not latest_expense_date:
            return

        working_days_elapsed = _working_days_between(
            self.employee, latest_expense_date, getdate(today())
        )
        if working_days_elapsed <= window:
            return

        block = bool(
            frappe.db.get_single_value("HR Settings", "custom_te_block_late_submission")
        )
        msg = _(
            "This claim is being submitted {0} working day(s) after the latest expense date ({1}). "
            "Policy: submission within {2} working days."
        ).format(working_days_elapsed, latest_expense_date, window)
        if block:
            frappe.throw(msg, title=_("Late submission"))
        else:
            frappe.msgprint(msg, title=_("Late submission — flagged for approver"), indicator="orange")

    # -------- single-stage auto-submit (UNCHANGED from existing override) --------

    def on_update(self):
        super().on_update()
        if self.docstatus == 0 and self.approval_status in ("Approved", "Rejected"):
            self.submit()

    # -------- existing rejection-remarks enforcement (UNCHANGED) --------

    def _enforce_rejection_remarks(self):
        previous = self.get_doc_before_save()
        old_status = previous.approval_status if previous else None
        new_status = self.approval_status
        if new_status == "Rejected" and old_status != "Rejected":
            reason = (self.get("custom_rejection_reason") or "").strip()
            if not reason:
                frappe.throw(
                    _("A rejection reason is required when rejecting an Expense Claim."),
                    title=_("Rejection reason required"),
                )


def _working_days_between(employee: str, start, end) -> int:
    """Count working days (excluding weekends + the employee's Holiday List)
    between start and end, inclusive of end, exclusive of start.

    Reuses the same Holiday List resolution myHR uses elsewhere:
      custom_holiday_list → holiday_list → Company default
    """
    if start >= end:
        return 0

    holiday_list = (
        frappe.db.get_value("Employee", employee, "custom_holiday_list")
        or frappe.db.get_value("Employee", employee, "holiday_list")
    )
    if not holiday_list:
        company = frappe.db.get_value("Employee", employee, "company")
        holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")

    holidays = set()
    if holiday_list:
        holidays = {
            h.holiday_date
            for h in frappe.get_all(
                "Holiday",
                filters={"parent": holiday_list},
                fields=["holiday_date"],
                limit_page_length=0,
            )
        }

    days = 0
    cursor = start
    from datetime import timedelta
    while cursor < end:
        cursor = cursor + timedelta(days=1)
        if cursor.weekday() >= 5:  # Saturday=5, Sunday=6
            continue
        if cursor in holidays:
            continue
        days += 1
    return days
```

### 5.3 Approval gate — extend `gate_expense_claim_approval`

Replace the existing function body (existing logic unchanged for non-override claims; new branch for override claims).

```python
def gate_expense_claim_approval(doc, method=None):
    """Existing logic (unchanged): block Approved/Rejected transitions unless
    authorised, honour prevent_self_expense_approval.

    NEW: when custom_cap_override == 1, neutralise the designated and
    accounts-manager paths. Only HR Manager / System Manager / Administrator
    can approve such a claim.
    """
    if doc.approval_status not in ("Approved", "Rejected"):
        return
    previous = doc.get_doc_before_save()
    if previous and previous.approval_status == doc.approval_status:
        return

    user = frappe.session.user
    if user == "Administrator":
        return

    settings = _ec_settings()

    if settings["prevent_self"] and _is_self_expense_claim(doc, user):
        frappe.throw(
            "You cannot approve your own Expense Claim — your company policy "
            "prevents self-approval. Ask your Expense Approver, HR, or an "
            "Accounts Manager to approve it.",
            frappe.PermissionError,
        )

    # NEW: cap-override route — only HR / System Manager.
    if doc.get("custom_cap_override"):
        if settings["hr_manager_ok"] and _is_hr_approval_role():
            return
        frappe.throw(
            "This Expense Claim has a Cap Override request and can only be "
            "approved by HR Manager or System Manager — not by the named "
            "Expense Approver. Justification:\n\n{}".format(
                doc.get("custom_cap_override_justification") or "(none provided)"
            ),
            frappe.PermissionError,
        )

    # Existing paths (unchanged) -------------------------------------------
    if settings["hr_manager_ok"] and _is_hr_approval_role():
        return

    if settings["designated_ok"] and doc.expense_approver and doc.expense_approver == user:
        return

    if settings["accounts_manager_ok"] and ACCOUNTS_MANAGER_ROLE in frappe.get_roles(user):
        return

    allowed_str = _ec_allowed_label(settings, doc)
    frappe.throw(
        f"Only {allowed_str} can approve this Expense Claim.",
        frappe.PermissionError,
    )
```

---

## 6. Frontend Behaviour

### 6.1 Desk — form-level JS

New file `apps/myhr/myhr/public/js/expense_claim.js`. Wire via `hooks.py`:

```python
doctype_js = {
    "Employee": "public/js/employee.js",   # existing
    "Expense Claim": "public/js/expense_claim.js",  # NEW
}
```

Responsibilities (Desk form only — PWA handled separately):

| # | When | Action |
|---|---|---|
| 1 | Child table `expense_type` change | Fetch `Expense Claim Type.custom_per_diem_basis` and toggle visibility of `custom_expense_city`, `custom_is_personal_vehicle`, `custom_kilometres` accordingly. |
| 2 | Child table `custom_kilometres` change | Inline-compute `amount = kilometres × fuel_rate` for visual feedback. Server validates on save anyway, but the live preview matters on Desk. |
| 3 | Parent `employee` change | Fetch the employee's Grade and display a banner: "Grade: CXO. Fuel rate: ₹10/km. Default Air Class: Economy." |
| 4 | Parent `custom_cap_override` toggle | Show/hide the justification field (Frappe handles via `depends_on`, but add a focus call so the cursor lands in the field). |

Lightweight — no AJAX calls except the Grade banner fetch (single `frappe.db.get_doc` call on `Employee Grade`).

### 6.2 PWA — Vue overlay

The PWA Expense Claim flow lives in [`frontend_changes/views/expense_claim/`](../myhr/frontend_changes/views/expense_claim/) — already redesigned during the night session (see [`PROGRESS.md`](../PROGRESS.md) Phase 2). Three additions:

| Component | Change |
|---|---|
| `views/expense_claim/Form.vue` | Add City picker on each line item (only shown when basis is Lodging/Meal). Add Kilometres input (only shown when basis is Personal Vehicle Fuel). Add the cap-override toggle + justification textarea at the parent level. Add an inline overage indicator on each breaching line. |
| `components/ExpenseClaimItem.vue` | Show a small "⚠ Cap Override" pill on rows where `custom_cap_override == 1`. |
| `views/expense_claim/Dashboard.vue` | Add a "Cap Breach" stat tile (count of claims with `custom_total_cap_breach_amount > 0` in last 30 days). |

PWA inline-validation API (new whitelisted endpoint in `myhr/api.py`):

```python
@frappe.whitelist()
def get_expense_caps_context(employee: str):
    """Bundle the lookups the PWA Form.vue needs to show caps/rates inline.

    Returns:
      {
        "grade": "CXO",
        "fuel_rate": 10.0,
        "default_air_class": "Economy",
        "cap_matrix": {
          "1": {"Lodging": 5000, "Meal": 1000},
          "2": {"Lodging": 4000, "Meal": 1000},
          "3": {"Lodging": 3000, "Meal": 1000}
        }
      }
    Read-only — no permission check needed beyond the @whitelist (employees see
    their own caps; HR sees any employee's caps when reviewing on Desk).
    """
    # implementation in myhr/api.py
```

---

## 7. Migration & Seed Data

Three new patches, registered in [`patches.txt`](../myhr/patches.txt) under `[post_model_sync]`, in this order.

### 7.1 `v1_23_seed_city_tier` — seed City Tier (19 rows)

```python
"""Seed the 19 City Tier rows: 8 Tier-1, 10 Tier-2, 1 catch-all (Tier 3).

Idempotent: only inserts when the row doesn't already exist by name.
Editable post-seed — HR can rename, retier, or add rows freely.
"""

import frappe

_TIER_1 = ["Mumbai", "Delhi", "Bangalore", "Chennai",
           "Hyderabad", "Kolkata", "Pune", "Ahmedabad"]
_TIER_2 = ["Jaipur", "Lucknow", "Surat", "Indore", "Chandigarh",
           "Kochi", "Coimbatore", "Nagpur", "Bhopal", "Visakhapatnam"]
_CATCHALL = ("Other", "3", 1)


def execute():
    if not frappe.db.exists("DocType", "City Tier"):
        print("v1_23: City Tier DocType not present — skipping seed.")
        return

    created = 0
    for city in _TIER_1:
        created += _ensure(city, "1", 0)
    for city in _TIER_2:
        created += _ensure(city, "2", 0)
    created += _ensure(*_CATCHALL)
    frappe.db.commit()
    print(f"v1_23: City Tier seeded ({created} new row(s); existing rows untouched).")


def _ensure(city_name: str, tier: str, is_catchall: int) -> int:
    if frappe.db.exists("City Tier", city_name):
        return 0
    doc = frappe.get_doc({
        "doctype": "City Tier",
        "city_name": city_name,
        "tier": tier,
        "is_catchall": is_catchall,
    })
    doc.insert(ignore_permissions=True)
    return 1
```

### 7.2 `v1_24_seed_per_diem_caps` — seed Per Diem Cap Matrix (12 rows)

```python
"""Seed the 12 Per Diem Cap Matrix rows per Elixiir policy v1.

CEO/COO has NO rows (policy: actuals, no cap — a null lookup = no enforcement).

Idempotent: skips rows that already exist for (grade, tier, category).
"""

import frappe
from frappe.utils import getdate

_EFFECTIVE_FROM = "2026-01-01"

# (grade_name, tier, category, daily_cap)
_ROWS = [
    # CXO grade
    ("CXO", "1", "Lodging", 5000), ("CXO", "1", "Meal", 1000),
    ("CXO", "2", "Lodging", 4000), ("CXO", "2", "Meal", 1000),
    ("CXO", "3", "Lodging", 3000), ("CXO", "3", "Meal", 1000),
    # Others grade
    ("Others", "1", "Lodging", 4000), ("Others", "1", "Meal", 800),
    ("Others", "2", "Lodging", 3000), ("Others", "2", "Meal", 800),
    ("Others", "3", "Lodging", 2500), ("Others", "3", "Meal", 800),
]


def execute():
    if not frappe.db.exists("DocType", "Per Diem Cap Matrix"):
        print("v1_24: Per Diem Cap Matrix DocType not present — skipping seed.")
        return

    # Confirm the two Grade master rows exist; if missing, log and skip
    # those rows (rather than failing the whole patch — HR can re-run after
    # creating the Grades).
    missing = []
    for grade in ("CXO", "Others"):
        if not frappe.db.exists("Employee Grade", grade):
            missing.append(grade)
    if missing:
        print(f"v1_24: Employee Grade(s) missing: {missing}. Create them first, then "
              f"re-run via: bench --site <s> execute myhr.patches.v1_24_seed_per_diem_caps.execute")

    created = 0
    for grade, tier, category, cap in _ROWS:
        if not frappe.db.exists("Employee Grade", grade):
            continue
        if frappe.db.exists(
            "Per Diem Cap Matrix",
            {"grade": grade, "city_tier": tier, "category": category},
        ):
            continue
        frappe.get_doc({
            "doctype": "Per Diem Cap Matrix",
            "grade": grade,
            "city_tier": tier,
            "category": category,
            "daily_cap": cap,
            "effective_from": getdate(_EFFECTIVE_FROM),
            "notes": "Seeded from Elixiir Travel & Reimbursement Policy v1.",
        }).insert(ignore_permissions=True)
        created += 1
    frappe.db.commit()
    print(f"v1_24: Per Diem Cap Matrix seeded ({created} new row(s); 12 expected on fresh install).")
```

### 7.3 `v1_25_seed_expense_claim_types` — seed 11 Expense Claim Types

```python
"""Seed 11 Expense Claim Types aligned to Elixiir policy taxonomy.

Each type carries a custom_per_diem_basis that drives the validation routing
in myhr.overrides.expense_claim.ExpenseClaim.

Idempotent: skips types that already exist by name.

The Account mapping (per-Company) is NOT set here — HR/Finance must map each
type to a GL account post-install via Expense Claim Type → Accounts table.
Mapping convention: 'Travel - EF' / 'Staff Welfare - EF' / 'Office Expenses - EF'
(suffix matches the Company abbreviation pattern from the existing Leave
Policy setup).
"""

import frappe

# (name, description, custom_per_diem_basis)
_TYPES = [
    ("Local Conveyance - Personal Vehicle",
     "Reimbursement for personal-vehicle fuel; amount = kilometres × Grade rate.",
     "Personal Vehicle Fuel"),
    ("Local Conveyance - Auto Rickshaw",
     "Auto/rickshaw fare — actuals with receipt.",
     "Actuals"),
    ("Local Conveyance - Bus or Metro",
     "Local bus or metro fare — actuals with ticket copy.",
     "Actuals"),
    ("Local Conveyance - Cab",
     "Ola/Uber/similar — actuals with bill.",
     "Actuals"),
    ("Air Travel",
     "Air ticket — economy by default; Premium Economy for CEO/COO.",
     "Actuals"),
    ("Rail Travel",
     "Rail ticket — CC for <8hr trips, 2AC otherwise.",
     "Actuals"),
    ("Lodging - Hotel",
     "Hotel/lodging — daily cap by Grade × City Tier.",
     "Lodging Cap"),
    ("Per-Diem Meal",
     "Meals during outstation travel — daily cap by Grade × City Tier.",
     "Meal Cap"),
    ("Office Purchase",
     "Office supplies, stationery, printing, sampling — actuals via Admin In-charge.",
     "Actuals"),
    ("Team Meal",
     "Team meals/lunches/dinners — actuals with prior CEO approval.",
     "Actuals"),
    ("Miscellaneous",
     "Other reimbursable expenses not covered above.",
     "Actuals"),
]


def execute():
    if not frappe.db.exists("DocType", "Expense Claim Type"):
        return

    created = 0
    for name, description, basis in _TYPES:
        if frappe.db.exists("Expense Claim Type", name):
            # Existing row — update the basis only (idempotent reseed in case
            # this patch is re-run after a basis change).
            current = frappe.db.get_value(
                "Expense Claim Type", name, "custom_per_diem_basis"
            )
            if current != basis:
                frappe.db.set_value(
                    "Expense Claim Type", name, "custom_per_diem_basis", basis
                )
                print(f"  v1_25: updated basis on {name}: {current!r} → {basis!r}")
            continue
        frappe.get_doc({
            "doctype": "Expense Claim Type",
            "name": name,
            "description": description,
            "custom_per_diem_basis": basis,
        }).insert(ignore_permissions=True)
        created += 1
    frappe.db.commit()
    print(f"v1_25: seeded {created} new Expense Claim Type(s); 11 expected on fresh install.")
```

### 7.4 Required manual setup (post-migrate, by HR Manager)

The patches seed master data but cannot guess GL accounts. Document this in the post-install runbook:

1. **Employee Grade** — create the three grades if not present: `CEO/COO`, `CXO`, `Others`. Set `custom_per_km_fuel_rate` and `custom_default_air_class` per the policy. (`v1_24` skips cap rows for missing grades and logs a re-run command.)
2. **Expense Claim Type → Accounts** — for each of the 11 types, map the appropriate GL account per Company. Suggested mapping in [`docs/TRAVEL_EXPENSE_ACCOUNT_MAP.md`](TRAVEL_EXPENSE_ACCOUNT_MAP.md) (TODO).
3. **HR Settings → Expenses tab** — review the four new Travel & Expense toggles and confirm defaults (caps on, fuel-rate on, 7-day window, no hard block).

---

## 8. Acceptance Tests

Tests live in `apps/myhr/myhr/tests/test_travel_expense.py` (new file). Each test cites the FR/policy clause it validates.

| # | Test | Expected |
|---|---|---|
| **T-01** | CXO employee files Lodging claim in Mumbai, ₹4500/day, 2 nights = ₹9000. | Submitted normally. `custom_daily_cap_applied = 5000`, `custom_overage_amount = 0`. No breach. |
| **T-02** | CXO employee files Lodging claim in Mumbai, ₹6000/day, 1 night = ₹6000. | Validate computes `custom_overage_amount = 1000`. Submit-for-Review blocks unless cap-override is ticked. |
| **T-03** | Same as T-02, with `custom_cap_override = 1` + justification. | Submit-for-Review succeeds. Approval gate blocks the designated `expense_approver`. HR Manager approves successfully. |
| **T-04** | Others employee files Meal claim in Indore (Tier 2), ₹850. | `custom_daily_cap_applied = 800`, `custom_overage_amount = 50`. |
| **T-05** | CEO/COO files Lodging claim in Mumbai, ₹15000. | No cap row exists for CEO/COO → `custom_daily_cap_applied = 0` (interpreted as no enforcement). No breach. Submits normally. |
| **T-06** | Employee files Personal Vehicle line with kilometres=100, no manual amount. | Amount auto-computed to `100 × grade.custom_per_km_fuel_rate`. Snapshot `custom_fuel_rate_applied` matches the rate at save-time. |
| **T-07** | Employee leaves kilometres empty on a Personal Vehicle line. | Throws `Row 1: Kilometres is required for a Personal Vehicle line.` |
| **T-08** | Employee files Lodging line without selecting a City. | Throws `Row 1: City is required for a Lodging Cap line — used to look up the applicable daily cap.` |
| **T-09** | Employee submits claim 5 working days after expense (window = 7). | Submits silently — within window. |
| **T-10** | Employee submits claim 10 working days after expense (window = 7, `block = 0`). | Warning toast: "submitted 10 working day(s) after the latest expense date." Submission succeeds. |
| **T-11** | Same as T-10 with `custom_te_block_late_submission = 1`. | Throws — submission blocked. |
| **T-12** | Cap-override ticked, justification empty. | Throws `Cap Override Justification is required when 'Request Cap Override' is ticked.` |
| **T-13** | Cap-override ticked, breach > 0; `expense_approver` tries to approve. | `PermissionError`: "This Expense Claim has a Cap Override request and can only be approved by HR Manager or System Manager." |
| **T-14** | Cap-override ticked, breach > 0; HR Manager approves. | Approval succeeds; `approval_status = Approved`; `on_update` auto-submits. GL entry posts. |
| **T-15** | Employee picks unknown city (not in City Tier dropdown). | Cannot happen — field is a Link. Validates server-side that catch-all "Other" row is present (covered by patch v1_23). |
| **T-16** | HR turns off `custom_te_enforce_caps`. Employee files claim with breach. | No `custom_overage_amount` calculated; no cap-override required; submits normally. |
| **T-17** | HR turns off `custom_te_enforce_fuel_rate`. Employee enters kilometres + a manual amount. | Manual amount preserved; `custom_fuel_rate_applied = 0`. |
| **T-18** | Rejection without remarks. | Existing `_enforce_rejection_remarks` throws (regression check — TE-1 changes must not break EC-1). |
| **T-19** | Self-approval blocked (`prevent_self_expense_approval = 1`). | Existing self-approval block fires (regression check). |
| **T-20** | After-migrate idempotency. Run migrate twice on a fresh site. | `v1_23/24/25` patches each report 0 new rows on second run. No errors. |

---

## 9. Open Questions — Resolved in Conversation

These were ambiguous in the source policy and resolved during spec design. Documented here so the next reader doesn't re-litigate.

| # | Question | Resolution |
|---|---|---|
| 1 | Should missing Travel Request block an Expense Claim? | **No.** Policy does not mandate system-level enforcement. `custom_travel_request` is an optional Link for traceability only. |
| 2 | Should cap-breach hard-block or allow with override? | **Allow with override.** `custom_cap_override` + justification routes the doc to HR Manager only. |
| 3 | Late-submission default behaviour? | **Warn, don't block.** Defaults: window = 7 working days, `custom_te_block_late_submission = 0`. HR can flip to hard-block via HR Settings. |
| 4 | City Tier as DocType or Python dict? | **DocType.** HR-editable; ~22 seed rows; new cities expected over time. |
| 5 | New "CEO Approver" role for overrides? | **No.** Use existing HR Manager / System Manager. No new RBAC surface. |
| 6 | 14-day air-advance booking enforcement? | **Not enforced.** No flight-date data source. Policy treats this as guidance. |
| 7 | <8hr journey by rail rule? | **Not enforced.** No journey-duration data source. |
| 8 | Air class enforcement (Premium Economy CEO/COO, Economy others)? | **Not enforced.** Surfaces in form UI as a hint via `Employee Grade.custom_default_air_class`. Approver checks at review. |
| 9 | Alcohol / personal / fines exclusion? | **Not enforced.** Descriptions are free-text. Approver review. |
| 10 | Same/different gender room-sharing combined-cap math? | **Not enforced.** Approver review. |

---

## 10. File Reference Map

| Path | Status | Purpose |
|---|---|---|
| [`overrides/expense_claim.py`](../myhr/overrides/expense_claim.py) | **MODIFY** | Add four new `_enforce_*` and `_check_*` methods + `_working_days_between` helper. |
| [`approval_gate.py`](../myhr/approval_gate.py) | **MODIFY** | Add cap-override branch in `gate_expense_claim_approval`. |
| `expense_caps.py` | **NEW** | Lookup helpers (`get_daily_cap`, `get_fuel_rate`, `get_default_air_class`, `get_city_tier`, `get_expense_type_basis`). |
| [`setup.py`](../myhr/setup.py) → `MYHR_CUSTOM_FIELDS` | **MODIFY** | Append ~18 new field dicts (Employee Grade ×2, Expense Claim Type ×1, Expense Claim ×4, Expense Claim Detail ×6, HR Settings ×5). |
| [`hooks.py`](../myhr/hooks.py) | **MODIFY** | Add `Expense Claim` to `doctype_js`. |
| [`api.py`](../myhr/api.py) | **MODIFY** | Add `get_expense_caps_context(employee)` whitelisted endpoint. |
| `myhr/doctype/city_tier/` | **NEW** | DocType + controller + test. |
| `myhr/doctype/per_diem_cap_matrix/` | **NEW** | DocType + controller + test. |
| `patches/v1_23_seed_city_tier.py` | **NEW** | 19 seed rows. |
| `patches/v1_24_seed_per_diem_caps.py` | **NEW** | 12 seed rows. |
| `patches/v1_25_seed_expense_claim_types.py` | **NEW** | 11 seed types. |
| [`patches.txt`](../myhr/patches.txt) | **MODIFY** | Append v1_23, v1_24, v1_25 under `[post_model_sync]`. |
| `public/js/expense_claim.js` | **NEW** | Desk form behaviours (banner, child-table toggles, inline preview). |
| `frontend_changes/views/expense_claim/Form.vue` | **MODIFY** | PWA form additions (city picker, km input, cap-override block, overage indicator). |
| `frontend_changes/components/ExpenseClaimItem.vue` | **MODIFY** | Cap-override pill. |
| `frontend_changes/views/expense_claim/Dashboard.vue` | **MODIFY** | Cap-breach stat tile. |
| `tests/test_travel_expense.py` | **NEW** | 20 acceptance tests (T-01 to T-20). |
| [`docs/TRAVEL_EXPENSE.md`](TRAVEL_EXPENSE.md) | **NEW** | This document. |
| `docs/TRAVEL_EXPENSE_ACCOUNT_MAP.md` | **NEW (later)** | Per-type GL account mapping suggestion for Finance. |

---

## 11. Implementation Order (suggested)

1. **Day 1 — Master data scaffolding**
   - Create the two new DocTypes (`City Tier`, `Per Diem Cap Matrix`) under `myhr/doctype/`.
   - Append the 18 custom-field dicts to `MYHR_CUSTOM_FIELDS`.
   - Write `expense_caps.py`.
   - Write patches v1_23 / v1_24 / v1_25 and register in `patches.txt`.
   - `bench --site <s> migrate` — verify all 18 fields created, 19 + 12 + 11 rows seeded.

2. **Day 2 — Server-side validation**
   - Extend `overrides/expense_claim.py` with TE-1 through TE-4.
   - Extend `approval_gate.py` with the cap-override branch.
   - Wire `get_expense_caps_context` in `api.py`.
   - Run smoke test on a sample employee (create draft, hit cap, tick override, get HR approval).

3. **Day 3 — Desk JS + PWA Vue**
   - Write `public/js/expense_claim.js`.
   - Modify the three Vue files in `frontend_changes/views/expense_claim/`.
   - Run `bench --site <s> execute myhr.frontend_sync.apply_custom_ui`.
   - Manually walk through the PWA flow on a phone simulator.

4. **Day 4 — Tests + docs**
   - Write `tests/test_travel_expense.py` with the 20 acceptance tests.
   - Add `docs/TRAVEL_EXPENSE_ACCOUNT_MAP.md` with the GL mapping suggestion.
   - Update `CLAUDE.md` and `README.md` to reference the new spec doc.
   - Update `docs/SETUP_AND_PATCHES.md` to document the three new patches.

5. **Day 5 — Buffer / cap-breach UAT**
   - Sit with HR Manager. Walk through the cap-override flow end-to-end on staging. Confirm the rejection message is readable and the breach computation matches expectations. Hand over.

**Estimated effort: 4–5 person-days for a developer who already knows myHR.**

---

*— End of Specification —*

*This document supersedes the conceptual PRD (Word docx) for implementation. The docx PRD remains the management-facing summary and is generated from this spec.*
