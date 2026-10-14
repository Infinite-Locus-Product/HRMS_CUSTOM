# Leave Policy Auto-Assignment — Feature Specification

> Authoritative spec for the **one-form leave-policy assignment** flow in myHR. HR sets a Leave Policy directly on the Employee form; myHR auto-creates the Leave Policy Assignment, which materialises the Leave Allocations for the active Leave Period. A read-only balance widget on the same form surfaces current allocations and balances inline. Same layering pattern as [`LEAVE_AND_ATTENDANCE.md`](LEAVE_AND_ATTENDANCE.md) — extend stock HRMS, don't replace.

**App:** myHR
**Compatibility:** Frappe 16.15.0 / ERPNext 16.14.0 / HRMS 16.5.0

### Problem this solves

Stock ERPNext/HRMS requires two separate steps after creating an Employee:

1. Open `Leave Policy Assignment`
2. Pick the employee, pick the policy, pick the leave period, set effective dates
3. Save and submit

HR forgets step 2 half the time. Employees then can't apply for leave because they have no allocations. This spec collapses the flow to a single field on the Employee form — HR picks the policy, saves the employee, and allocations exist.

### Surfaces touched

| Surface | Owner | Action |
|---|---|---|
| `Employee` | stock Frappe | Two custom fields — Leave Policy picker (Overview tab) + Leave Balance HTML widget (Attendance & Leaves section) |
| `Employee` event hook `on_update` | myHR | Append `auto_assign_leave_policy` to existing chain |
| `Leave Policy Assignment` | stock HRMS | Created programmatically; no override needed |
| `Leave Allocation` | stock HRMS | Created automatically by `Leave Policy Assignment.submit()`; no myHR code touches them |
| Employee form JS | myHR | New render function in existing `public/js/employee.js` |

### Files

| Concern | File |
|---|---|
| Hook function (new) | [`apps/myhr/myhr/employee_hooks.py`](../myhr/employee_hooks.py) — append `auto_assign_leave_policy` |
| Custom-field declarations (extend) | [`apps/myhr/myhr/setup.py`](../myhr/setup.py) → `MYHR_CUSTOM_FIELDS` and `ELIXIIR_HR_ONLY_FIELDS` |
| API endpoint (new) | [`apps/myhr/myhr/api.py`](../myhr/api.py) — `get_employee_leave_balances` |
| Form JS (extend) | [`apps/myhr/myhr/public/js/employee.js`](../myhr/public/js/employee.js) |
| Migration patch (new) | `apps/myhr/myhr/patches/v1_26_backfill_employee_leave_policy.py` |

---

## 1. Purpose

When HR creates or updates an Employee, the Leave Policy dropdown on the Employee form is the single decision point that determines what leave types and how many days the employee gets. Saving the Employee:

- Creates a submitted `Leave Policy Assignment` (LPA) for the active Leave Period
- That LPA, on submit, creates one `Leave Allocation` per leave type in the policy bundle
- The Leave Balance widget on the Employee form refreshes to show the new allocations

When HR **changes** the policy (e.g., probation → confirmed):

- The prior LPA is end-dated at today − 1
- A new LPA is created effective today, running to the period end
- The widget reflects both old-and-new types correctly via standard `get_leave_balance_on` computation

When HR **clears** the policy (sets to blank):

- Nothing destructive happens. Existing allocations stay. This is deliberate — clearing a Link field shouldn't quietly destroy leave balances. HR cancels allocations explicitly if that's the intent.

### 1.1 Non-goals

The following are explicitly out of scope to keep this feature surgical:

- Bulk re-assignment (changing the policy on 100 employees at once). HR uses the standard Leave Policy Assignment "Grant Leaves" flow on `Leave Period` for that.
- Probation→Confirmed automation based on date arithmetic. The trigger for this feature is HR editing the Employee form. A separate scheduled job to auto-flip probationers at the 3-month mark is a Phase 2 ask, not this spec.
- Multi-policy assignment (an employee on two simultaneous policies). Out of scope; one policy at a time.
- Mid-period top-ups (employee gets bonus leaves). Use stock HRMS's manual `Leave Allocation` insert flow.
- Cross-company leave policies. The active Leave Period is scoped per company; same policy bundle assumed within company.

---

## 2. User Stories

| # | As a … | I want to … | So that … |
|---|---|---|---|
| 1 | HR Manager | pick a Leave Policy on the Employee form when I create an employee | I don't have to navigate to a second DocType to allocate leaves |
| 2 | HR Manager | see the employee's current leave balances inline on their record | I don't have to run a separate report |
| 3 | HR Manager | change an employee's policy from Probation to Confirmed by editing one field | the transition is one tap, not five |
| 4 | Employee | see my balances on my own Employee record (PWA) | I trust what HR has allocated |
| 5 | HR Manager | be warned if no active Leave Period exists for the employee's company | I don't silently fail to allocate |
| 6 | Auditor | trace which Leave Policy Assignment created which Leave Allocation | normal Frappe linked-doc trail still works (`amended_from`, owner, creation timestamp) |

---

## 3. Data Model

### 3.1 Custom Field — `Employee.custom_leave_policy`

Appended to `MYHR_CUSTOM_FIELDS` in [`setup.py`](../myhr/setup.py).

```python
{
    "dt": "Employee",
    "fieldname": "custom_leave_policy",
    "label": "Leave Policy",
    "fieldtype": "Link",
    "options": "Leave Policy",
    "insert_after": "custom_holiday_list",
    "description": (
        "Leave Policy applicable to this employee. On save, myHR creates a "
        "Leave Policy Assignment for the active Leave Period and submits it — "
        "which in turn auto-allocates one Leave Allocation per Leave Type in "
        "the policy bundle. Changing this field end-dates the prior assignment "
        "and creates a new one effective today. Clearing it is a no-op (does "
        "not cancel existing allocations)."
    ),
},
```

**HR-only edit:** add `custom_leave_policy` to the existing `ELIXIIR_HR_ONLY_FIELDS` tuple in [`setup.py`](../myhr/setup.py). Leave policy decisions are policy-grade — the employee should not be able to self-modify.

```python
ELIXIIR_HR_ONLY_FIELDS = (
    "ctc",
    "salutation",
    # ... existing entries ...
    "custom_holiday_list",
    "custom_leave_policy",  # NEW — Leave Policy Auto-Assignment feature
)
```

The existing `_apply_elixiir_hr_only_permlevels()` function picks the new field up on the next migrate without code change.

### 3.2 Custom Field — `Employee.custom_leave_balance_html`

```python
{
    "dt": "Employee",
    "fieldname": "custom_leave_balance_html",
    "label": "Current Leave Balances",
    "fieldtype": "HTML",
    "insert_after": "leave_approver",
    "description": (
        "Read-only table rendered by the Employee form JS. Shows one row per "
        "active Leave Allocation for the current date: Leave Type, Allocated, "
        "Taken, Balance, Expires On. Empty state when no allocations exist."
    ),
},
```

Anchored at `insert_after: "leave_approver"` so it sits inside the existing "Attendance and Leave Details" section, immediately below the leave approver dropdown. No new section break needed.

### 3.3 No new fields on Leave Policy Assignment

The whole point of this feature is to use stock `Leave Policy Assignment` as-is. The auto-creator passes the same fields HR would fill in manually:

| Field | Source |
|---|---|
| `employee` | `Employee.name` |
| `leave_policy` | `Employee.custom_leave_policy` |
| `assignment_based_on` | hard-coded "Leave Period" |
| `leave_period` | resolved by company + today's date |
| `effective_from` | `max(today, Employee.date_of_joining)` |
| `effective_to` | `Leave Period.to_date` |
| `company` | `Employee.company` |

---

## 4. Backend Behaviour

### 4.1 New hook function — `myhr.employee_hooks.auto_assign_leave_policy`

Appended to the existing `on_update` chain on Employee. Wired in [`hooks.py`](../myhr/hooks.py):

```python
doc_events = {
    "Employee": {
        # ...existing entries unchanged...
        "on_update": [
            "myhr.employee_master_data.on_update_master_data",
            "myhr.employee_hooks.on_update_employee",
            "myhr.policy_hooks.reconcile_on_employee_update",
            "myhr.employee_hooks.auto_assign_leave_policy",  # NEW
        ],
        # ...
    },
    # ...
}
```

Function body (add to [`employee_hooks.py`](../myhr/employee_hooks.py)):

```python
"""Auto-create / replace Leave Policy Assignment when Employee.custom_leave_policy changes.

Rules:
  - new policy set + no prior LPA for this employee × period → create submitted LPA
  - new policy differs from the prior LPA for this employee × period → end-date prior LPA
    at today-1, create new LPA effective today through period.to_date
  - same policy as prior LPA → no-op (idempotent)
  - cleared (None) → no-op; existing allocations are preserved (HR cancels manually if intended)
  - no active Leave Period covers today → no-op with msgprint warning; HR fixes the period first

Safety:
  - runs in the on_update chain AFTER the other Employee handlers so it sees the persisted state
  - uses ignore_permissions=True for the LPA insert+submit since HR triggered it via Employee save
  - the LPA's own validate runs as normal; if HRMS rejects (e.g., overlapping dates), the throw
    surfaces to the HR Manager naturally
"""

import frappe
from frappe import _
from frappe.utils import today, add_days, getdate


def auto_assign_leave_policy(doc, method=None):
    new_policy = doc.custom_leave_policy
    if not new_policy:
        # Cleared OR was never set. No destructive action.
        return

    previous = doc.get_doc_before_save()
    prev_policy = previous.custom_leave_policy if previous else None

    # Same value as before — nothing to do. Critical for the on_update loop:
    # any save that doesn't change the policy must be a no-op or we'd create
    # a fresh LPA on every Employee edit.
    if prev_policy == new_policy:
        return

    # Resolve the active Leave Period covering today, scoped to the
    # employee's company. There may be multiple periods historically;
    # we want the one that is currently in force.
    period = frappe.db.get_value(
        "Leave Period",
        {
            "is_active": 1,
            "from_date": ("<=", today()),
            "to_date": (">=", today()),
            "company": doc.company,
        },
        "name",
        order_by="from_date desc",
    )
    if not period:
        frappe.msgprint(
            _(
                "Leave Policy set to {0} but no active Leave Period covers today for "
                "company {1}. No Leave Policy Assignment was created. Please create a "
                "Leave Period first, then re-save this Employee."
            ).format(frappe.bold(new_policy), frappe.bold(doc.company)),
            title=_("Leave allocation skipped"),
            indicator="orange",
        )
        return

    period_doc = frappe.get_cached_doc("Leave Period", period)

    # End-date the prior LPA (if any) for this employee × period × prev_policy.
    # We deliberately only end-date assignments for the SAME period — historical
    # periods stay untouched (their allocations belong to a closed leave year).
    if prev_policy:
        prior_lpa_name = frappe.db.get_value(
            "Leave Policy Assignment",
            {
                "employee": doc.name,
                "leave_period": period,
                "leave_policy": prev_policy,
                "docstatus": 1,
            },
            "name",
        )
        if prior_lpa_name:
            yesterday = add_days(today(), -1)
            frappe.db.set_value(
                "Leave Policy Assignment", prior_lpa_name, "effective_to", yesterday
            )
            # Note: HRMS's standard Leave Allocation lifecycle handles the
            # already-allocated days — they stay on the employee's ledger up
            # to the new effective_to. The new LPA's allocations layer on top.

    # Create + submit the new LPA. HRMS's controller does the heavy lifting
    # (pro-rata math, allocation creation, carry-forward if configured).
    effective_from = max(
        getdate(today()),
        getdate(doc.date_of_joining or today()),
    )
    # Defensive — effective_from must not exceed period.to_date
    if effective_from > getdate(period_doc.to_date):
        frappe.msgprint(
            _(
                "Effective From ({0}) is past the active Leave Period end ({1}). "
                "Leave Policy Assignment skipped — create a Leave Period for the new range."
            ).format(effective_from, period_doc.to_date),
            title=_("Effective date past period end"),
            indicator="orange",
        )
        return

    lpa = frappe.get_doc({
        "doctype": "Leave Policy Assignment",
        "employee": doc.name,
        "leave_policy": new_policy,
        "assignment_based_on": "Leave Period",
        "leave_period": period,
        "effective_from": effective_from,
        "effective_to": period_doc.to_date,
        "company": doc.company,
    })
    lpa.flags.ignore_permissions = True
    lpa.insert()
    lpa.submit()

    frappe.msgprint(
        _(
            "Leave Policy <b>{0}</b> assigned for period <b>{1}</b>. "
            "Allocations created — see 'Current Leave Balances' below."
        ).format(new_policy, period),
        title=_("Leave Policy assigned"),
        indicator="green",
        alert=True,
    )
```

### 4.2 New API endpoint — `myhr.api.get_employee_leave_balances`

Whitelisted endpoint that returns active allocations + computed balances. Used by the form JS to render the widget. Add to [`api.py`](../myhr/api.py):

```python
@frappe.whitelist()
def get_employee_leave_balances(employee: str):
    """Return active Leave Allocations for the employee + computed balance per type.

    Used by the Employee form's Leave Balance widget. Permissioned: the caller
    must either be HR (read all) or the employee themselves (read self).
    """
    if not employee:
        return []

    # Permission check — match the existing Employee permission rule
    roles = set(frappe.get_roles())
    if not ({"HR Manager", "HR User", "System Manager"} & roles):
        emp_user = frappe.db.get_value("Employee", employee, "user_id")
        if emp_user != frappe.session.user:
            frappe.throw(
                _("You can only view your own leave balances."),
                frappe.PermissionError,
            )

    today_str = frappe.utils.today()

    allocations = frappe.get_all(
        "Leave Allocation",
        filters={
            "employee": employee,
            "from_date": ("<=", today_str),
            "to_date": (">=", today_str),
            "docstatus": 1,
        },
        fields=[
            "leave_type",
            "total_leaves_allocated",
            "from_date",
            "to_date",
            "carry_forwarded_leaves_count",
        ],
        order_by="leave_type",
    )

    # get_leave_balance_on is the canonical HRMS computation —
    # accounts for consumed Leave Applications, half-days, encashment.
    from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

    result = []
    for a in allocations:
        balance = get_leave_balance_on(
            employee=employee,
            leave_type=a.leave_type,
            date=today_str,
            to_date=a.to_date,
            consider_all_leaves_in_the_allocation_period=True,
        )
        balance = float(balance or 0)
        allocated = float(a.total_leaves_allocated or 0)
        result.append({
            "leave_type": a.leave_type,
            "total_leaves_allocated": allocated,
            "carry_forwarded": float(a.carry_forwarded_leaves_count or 0),
            "leaves_taken": round(allocated - balance, 2),
            "balance": balance,
            "from_date": a.from_date,
            "to_date": a.to_date,
        })
    return result
```

---

## 5. Frontend Behaviour

### 5.1 Form JS — `public/js/employee.js` (extend)

The existing `employee.js` is wired via `doctype_js` in [`hooks.py`](../myhr/hooks.py). Append a refresh handler:

```javascript
// ... existing form handlers preserved ...

frappe.ui.form.on('Employee', {
    refresh(frm) {
        // ... any existing refresh logic ...
        render_leave_balance_widget(frm);
    },

    custom_leave_policy(frm) {
        // When the user changes the policy in-form, hint that saving will
        // trigger the auto-assignment. This is UX-only — the server hook
        // is what actually does the work on save.
        if (frm.doc.custom_leave_policy && !frm.is_new()) {
            frm.set_intro(
                __('Saving will assign the {0} policy and create leave allocations for the active Leave Period.',
                   [frm.doc.custom_leave_policy]),
                'blue'
            );
        }
    },
});

function render_leave_balance_widget(frm) {
    const field = frm.fields_dict.custom_leave_balance_html;
    if (!field) return;

    if (frm.is_new() || !frm.doc.name) {
        field.$wrapper.html(
            `<div class="text-muted" style="padding: 8px 0;">
                ${__('Save the employee first to see leave balances.')}
            </div>`
        );
        return;
    }

    field.$wrapper.html(
        `<div class="text-muted" style="padding: 8px 0;">${__('Loading…')}</div>`
    );

    frappe.call({
        method: 'myhr.api.get_employee_leave_balances',
        args: { employee: frm.doc.name },
        callback(r) {
            const balances = r.message || [];
            if (!balances.length) {
                const msg = frm.doc.custom_leave_policy
                    ? __("Leave Policy is set but no active allocations were found. Check the Leave Period exists for {0}.", [frm.doc.company])
                    : __("No Leave Policy assigned. Pick one in the Overview tab and save.");
                field.$wrapper.html(
                    `<div class="text-muted" style="padding: 8px 0;">${msg}</div>`
                );
                return;
            }

            const rows = balances.map(b => `
                <tr>
                    <td>${frappe.utils.escape_html(b.leave_type)}</td>
                    <td class="text-right">${b.total_leaves_allocated}</td>
                    <td class="text-right">${b.carry_forwarded}</td>
                    <td class="text-right">${b.leaves_taken}</td>
                    <td class="text-right"><b>${b.balance}</b></td>
                    <td>${frappe.format(b.to_date, { fieldtype: 'Date' })}</td>
                </tr>
            `).join('');

            field.$wrapper.html(`
                <table class="table table-bordered table-sm" style="margin-top: 8px; margin-bottom: 0;">
                    <thead style="background: #f5f5f5;">
                        <tr>
                            <th>${__('Leave Type')}</th>
                            <th class="text-right">${__('Allocated')}</th>
                            <th class="text-right">${__('Carry Fwd')}</th>
                            <th class="text-right">${__('Taken')}</th>
                            <th class="text-right">${__('Balance')}</th>
                            <th>${__('Expires On')}</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            `);
        },
    });
}
```

### 5.2 PWA — Vue overlay (optional, Phase 2)

The PWA Employee profile view ([`views/Profile.vue`](../myhr/frontend_changes/views/Profile.vue)) already shows the employee's name, role, department, etc. A natural enhancement is to add a "My Leave Balances" section calling the same `get_employee_leave_balances` endpoint. **Not in scope for this spec** — flag as Phase 2 if HR wants it. Desk-form widget alone satisfies the original requirement.

---

## 6. Migration — Patch `v1_26_backfill_employee_leave_policy`

For sites with existing Employees and existing Leave Policy Assignments, backfill `custom_leave_policy` from the most recent submitted LPA so the field reflects reality on first install.

```python
"""Backfill Employee.custom_leave_policy from the most recent submitted LPA.

On a fresh install, all existing employees already have leave allocations
from prior LPAs but the new field is empty. This patch reads each
employee's latest submitted LPA and writes the leave_policy onto Employee.

Idempotent: only writes when the field is currently empty AND a prior
submitted LPA exists. Does NOT re-create allocations — those already exist.
"""

import frappe


def execute():
    if not frappe.db.exists("DocType", "Leave Policy Assignment"):
        print("v1_26: Leave Policy Assignment DocType not present — skipping.")
        return

    # Fetch the custom_leave_policy column exists check — guards against
    # running this patch before v1_23+24+25+the new custom-field declaration
    # have landed.
    if not frappe.db.has_column("tabEmployee", "custom_leave_policy"):
        print("v1_26: Employee.custom_leave_policy column not present yet — "
              "wait for the custom-field sync, then re-run via "
              "`bench --site <s> execute myhr.patches.v1_26_backfill_employee_leave_policy.execute`.")
        return

    employees = frappe.get_all(
        "Employee",
        filters={"custom_leave_policy": ("in", ("", None))},
        fields=["name"],
    )
    backfilled = 0
    for emp in employees:
        latest = frappe.db.get_value(
            "Leave Policy Assignment",
            {"employee": emp.name, "docstatus": 1},
            "leave_policy",
            order_by="effective_from desc",
        )
        if latest:
            frappe.db.set_value(
                "Employee", emp.name, "custom_leave_policy", latest,
                update_modified=False,
            )
            backfilled += 1
    frappe.db.commit()
    print(f"v1_26: backfilled custom_leave_policy on {backfilled} Employee(s).")
```

Register in [`patches.txt`](../myhr/patches.txt) under `[post_model_sync]`:

```
myhr.patches.v1_26_backfill_employee_leave_policy
```

---

## 7. Edge Cases & Decision Log

### 7.1 What if there is no active Leave Period?

HR sets the policy, saves. Server hook detects no period covers today. Shows a `msgprint` warning but does NOT block the save — the Employee record still updates. HR creates the Leave Period and re-saves the Employee; the hook fires again and succeeds. This is the right trade-off because forcing a Leave Period to exist before any Employee can be saved is too aggressive.

### 7.2 What if the policy is set on Employee creation (`after_insert`)?

The `on_update` hook fires after `after_insert` in Frappe's sequence. By the time `auto_assign_leave_policy` runs, the Employee.name exists in the DB and the LPA can reference it. **Confirmed working** — same pattern used elsewhere in myhr.

### 7.3 What if HR changes the policy mid-year (e.g., probation → confirmed)?

Prior LPA gets `effective_to = today - 1`. New LPA created with `effective_from = today`. Standard HRMS behaviour kicks in for the new allocations:

- Pro-rated Casual / Sick / Maternity from the new effective_from to period end
- Earned Leave starts accruing monthly from the new effective date

This is exactly what the Leave Policy Setup Guide §11.3 (probation → confirmation transition) describes — now done in one Employee save instead of three manual steps.

### 7.4 What if HR sets the same policy twice (saves the Employee with no policy change)?

`prev_policy == new_policy` → early return. **Idempotent.** No duplicate LPA created.

### 7.5 What if HR clears the policy field?

`new_policy is None` → early return. **Non-destructive.** Existing allocations stay valid. To actually remove allocations, HR cancels the LPA via the standard Frappe UI. Rationale: a Link field clearance is too low-friction an action to trigger destructive consequences silently.

### 7.6 What if the Leave Policy has been edited (bundle changed) since assignment?

The auto-assignment uses the policy bundle **at submit time**. If HR edits the Leave Policy later (adds a Leave Type, changes annual allocation), already-created allocations are unaffected — that matches standard HRMS behaviour. To propagate the new bundle to an employee, HR changes their `custom_leave_policy` to something else and back, OR explicitly creates a new LPA via the standard form.

### 7.7 What if two HR users edit the same Employee concurrently?

Last write wins on the Employee row. The auto-assignment hook fires for each save. The second one detects no policy change (if both saved the same value) → no-op. If they saved different policies → the second save's policy wins, the LPA from the first save gets end-dated, and a new LPA is created for the second.

### 7.8 What if the Employee has no `date_of_joining` set?

`effective_from = max(today, doc.date_of_joining or today)` falls back to today. Allocations start from today; pro-rata math is based on `effective_from → period.to_date`.

### 7.9 What if `custom_leave_policy` points at a Leave Policy that has been deleted?

Frappe Link validation refuses to save the Employee in that state — the user gets a "Could not find Leave Policy: X" error before the hook even runs. No special handling needed.

### 7.10 Does this work for multi-company setups?

Yes. The Leave Period lookup is scoped to `doc.company`. Two companies can have separate Leave Periods of the same year and the hook resolves each employee's policy against their own company's period.

---

## 8. Acceptance Tests

Tests live in `apps/myhr/myhr/tests/test_leave_policy_autowire.py`.

| # | Test | Expected |
|---|---|---|
| **LP-01** | Create a new Employee with `custom_leave_policy = "Elixiir Confirmed Leave Policy"`, save. | LPA created (docstatus=1) for the active Leave Period. Leave Allocations created for every Leave Type in the policy. |
| **LP-02** | Update an Employee, change `custom_leave_policy` from probation to confirmed. | Prior LPA's `effective_to` set to today-1. New LPA created with `effective_from = today`. Old allocations remain valid through today-1; new allocations begin today. |
| **LP-03** | Save an Employee without changing `custom_leave_policy`. | `auto_assign_leave_policy` returns early; no new LPA created (idempotent). |
| **LP-04** | Clear `custom_leave_policy` on an Employee with prior allocations and save. | Hook returns early; existing LPA and allocations preserved. |
| **LP-05** | Set `custom_leave_policy` on an Employee whose company has no active Leave Period. | Employee saves successfully. `msgprint` warning shown. No LPA created. |
| **LP-06** | Set `custom_leave_policy` on an Employee where the policy references a non-existent Leave Policy. | Frappe's Link validation rejects the Employee save with "Could not find Leave Policy". Hook never fires. |
| **LP-07** | Call `myhr.api.get_employee_leave_balances` as the employee themselves. | Returns their balances. |
| **LP-08** | Call `myhr.api.get_employee_leave_balances` as a different non-HR user. | PermissionError. |
| **LP-09** | Call `myhr.api.get_employee_leave_balances` as HR Manager for any employee. | Returns the target employee's balances. |
| **LP-10** | Open an Employee form in Desk after policy assignment. | Leave Balance widget renders the table with allocated/carry-fwd/taken/balance/expires. |
| **LP-11** | Open a new (unsaved) Employee form. | Widget shows "Save the employee first..." placeholder. |
| **LP-12** | Open an Employee with policy set but no period (LP-05 state). | Widget shows "Leave Policy is set but no active allocations were found. Check the Leave Period exists for ..." |
| **LP-13** | Run `bench migrate` on a site with 50 existing employees each with a submitted LPA. | Patch v1_26 backfills `custom_leave_policy` on all 50. Re-running migrate reports 0 backfills (idempotent). |
| **LP-14** | Employee permlevel — non-HR user opens their own Employee form. | `custom_leave_policy` field is visible but read-only (HR-only edit, permlevel 1). |
| **LP-15** | HR Manager edits the policy via the API (`frappe.db.set_value`). | Hook fires only if going through `frappe.get_doc(...).save()`. Direct `db.set_value` bypasses validate/on_update — documented behaviour, not a bug. HR should use the form. |
| **LP-16** | Multi-company — Employee in Company A with active Leave Period A; Employee in Company B with active Leave Period B. | Each gets their own company's period. |
| **LP-17** | Employee's `date_of_joining` is in the future. | Hook calculates `effective_from = max(today, date_of_joining)`. Allocation effective_from = the joining date. |
| **LP-18** | Effective from > period.to_date (e.g. employee joins in last week of period). | Hook shows a "Effective date past period end" warning, skips assignment. HR creates next-period LPA manually or waits. |

---

## 9. Open Questions

None known — every behaviour above is locked. Two items flagged for HR awareness, not blocking:

| # | Item | Note |
|---|---|---|
| 1 | Should PWA Profile show the leave balance widget too? | Phase 2. Same API endpoint; small Vue component in `frontend_changes/views/Profile.vue`. |
| 2 | Should a scheduled job auto-flip probationer policies to confirmed at 3-month mark? | Phase 2. Trivial cron job that reads probation start date + 90 days, sets `custom_leave_policy = "Elixiir Confirmed Leave Policy"`. Not in this spec because the policy decision should stay with HR for now. |

---

## 10. File Reference Map

| Path | Status | Purpose |
|---|---|---|
| [`employee_hooks.py`](../myhr/employee_hooks.py) | **MODIFY** | Append `auto_assign_leave_policy()` function. |
| [`hooks.py`](../myhr/hooks.py) | **MODIFY** | Append `auto_assign_leave_policy` to the Employee `on_update` chain. |
| [`setup.py`](../myhr/setup.py) → `MYHR_CUSTOM_FIELDS` | **MODIFY** | Append 2 new field dicts (Employee × 2). |
| [`setup.py`](../myhr/setup.py) → `ELIXIIR_HR_ONLY_FIELDS` | **MODIFY** | Append `custom_leave_policy` to the permlevel-1 tuple. |
| [`api.py`](../myhr/api.py) | **MODIFY** | Append `get_employee_leave_balances(employee)` whitelisted endpoint. |
| [`public/js/employee.js`](../myhr/public/js/employee.js) | **MODIFY** | Append `render_leave_balance_widget()` function and `refresh` / `custom_leave_policy` form handlers. |
| `patches/v1_26_backfill_employee_leave_policy.py` | **NEW** | Backfill from existing LPAs. |
| [`patches.txt`](../myhr/patches.txt) | **MODIFY** | Register v1_26. |
| `tests/test_leave_policy_autowire.py` | **NEW** | 18 acceptance tests (LP-01 to LP-18). |
| [`docs/LEAVE_POLICY_AUTO_ASSIGN.md`](LEAVE_POLICY_AUTO_ASSIGN.md) | **NEW** | This document. |

---

## 11. Implementation Order

This is a smaller feature than Travel & Expense — should land in **1–1.5 person-days**:

| Step | Time | Deliverable |
|---|---|---|
| 1 | 30 min | Append 2 custom fields + 1 entry to `ELIXIIR_HR_ONLY_FIELDS`. `bench migrate`. Verify the fields appear on Employee form. |
| 2 | 2 hours | Write `auto_assign_leave_policy()`. Wire into hooks.py. Manual test: create an Employee with a policy and confirm an LPA is created and submitted. |
| 3 | 1 hour | Write `get_employee_leave_balances` API. Test via `bench console`. |
| 4 | 2 hours | Extend `employee.js` with the widget render function. Hard-refresh the Desk form; visually verify. |
| 5 | 30 min | Write patch v1_26. Run migrate on a copy of staging with existing LPAs; verify backfill count. |
| 6 | 2 hours | Write the 18 acceptance tests. Run them; fix anything that fails. |
| 7 | 30 min | Update docs/SETUP_AND_PATCHES.md and CLAUDE.md to reference the new feature. |

Total: ~8.5 hours of focused work.

---

*— End of Specification —*
