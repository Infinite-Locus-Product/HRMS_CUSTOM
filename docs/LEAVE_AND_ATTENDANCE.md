# Leave Application & Attendance Request — Feature Specification

> Authoritative spec for the **two PWA approval flows** in myHR — Leave Application and Attendance Request. Both share the same single-stage policy (manager **or** HR can approve), so they live together in this doc.

**App:** myHR

### Leave Application
**DocType:** `Leave Application` (standard HRMS, overridden by `myhr.overrides.leave_application.LeaveApplication`)
**Override file:** [`apps/myhr/myhr/overrides/leave_application.py`](../myhr/overrides/leave_application.py)
**Server validation helper:** [`apps/myhr/myhr/leave_optional_holiday.py`](../myhr/leave_optional_holiday.py)
**PWA inline validation:** `myhr.api.validate_optional_leave_for_application`
**Team Requests endpoint:** `myhr.api.get_leave_applications` (override of `hrms.api.get_leave_applications`)
**Optional-types lookup:** `myhr.api.get_optional_leave_types`
**PWA forms:** [`apps/myhr/myhr/frontend_changes/views/leave/Form.vue`](../myhr/frontend_changes/views/leave/Form.vue)

### Attendance Request
**DocType:** `Attendance Request` (standard HRMS — no override class needed)
**Team Requests endpoint:** `myhr.api.get_attendance_requests` (override of `hrms.api.get_attendance_requests`)
**Manager-pointer field on Employee:** `leave_approver` (reused — Attendance Request has no per-employee approver field of its own)
**PWA forms:** standard HRMS attendance views (no myHR-side override)

---

## 1. Purpose

myHR ships two PWA approval flows for absence-related requests:

| Feature | What an employee asks for | What the approver does |
|---|---|---|
| **Leave Application** | A future date range off, against an allocated Leave Type. | Approves or rejects. Approval auto-submits the doc and debits the leave balance. |
| **Attendance Request** | An exception to the daily attendance rule (e.g. Work From Home, On Duty travel) for past or future dates. | Submits or cancels the doc. Submission creates the Attendance entries. |

Both share **one approval policy** (§1.1). They differ in their data model — Leave Application has a `status` field and an explicit `leave_approver`; Attendance Request has neither (it's docstatus-only, no per-employee approver field).

### 1.1 Single-stage approval policy (shared)

> Whichever of these acts first wins:
> - The user named on `Employee.leave_approver` (set up by HR on the Employee form, **"Attendance and Leaves"** section), or
> - **Any** user holding the `HR Manager` (or `System Manager`) role.
>
> No two-stage workflow. No `hr_approver` field. No "Approved by Manager" intermediate status.
>
> **`leave_approver` doubles as the Attendance Request approver too.** myHR does NOT use `Employee.reports_to` (the chain-of-command field) and does NOT use a separate `attendance_request_approver` field. There is one approver pointer per employee, set in **Attendance & Leaves → Leave Approver**, and it drives both Leave Application and Attendance Request approvals.
>
> The `Expense Approver` and `Shift Request Approver` fields visible on the same tab are unchanged from stock HRMS and continue to drive Expense Claim and Shift Request workflows respectively — those are out of scope here.

### 1.2 Leave-Application-only behaviour

In addition to the shared policy, Leave Application also gets:

1. **Optional-leave guardrails** — when a leave type is marked `is_optional_leave`, dates must come from the employee's Holiday List with `custom_holiday_type = "Optional"` (no Fixed days, no weekly offs), and the application must be full-day (no half-days).
2. **Auto-submit on approval** — when an approver flips status to `Approved`, the document is submitted in the same save (no separate "Submit" button click needed).

### 1.3 Attendance-Request-only behaviour

Attendance Request has no `status` field and no workflow. The approver clicking **Submit** *is* the approval (creates `docstatus=1` and the corresponding Attendance entries). Rejection is implicit (the approver leaves the draft alone, deletes it, or asks the employee to amend).

---

## 2. User Stories

| # | As a … | I want to …                                                                 | So that …                                                          |
|---|--------|------------------------------------------------------------------------------|---------------------------------------------------------------------|
| 1 | Employee | apply for leave from the PWA                                               | I don't need a desk login                                          |
| 2 | Employee | see my own leaves and balances                                              | I track what's left in my pool                                     |
| 3 | Manager  | see pending requests from my team in PWA "My Team Requests"                 | I can decide quickly                                                |
| 4 | HR Manager | see pending requests from **anyone** in PWA "My Team Requests"             | I can step in even if I'm not the named approver                   |
| 5 | Manager / HR Manager | approve a request → the application auto-submits                  | one click, not two                                                 |
| 6 | Manager / HR Manager | reject a request                                                  | the employee gets the rejection without it being submitted         |
| 7 | Employee | apply for an Optional Leave only on dates from my Holiday List              | the rule is enforced server-side, not bypassable                   |
| 8 | Employee | NOT be able to half-day an Optional Leave                                   | optional leaves are full-day-only by policy                        |

---

## 3. Data Model

### 3.1 Doctype

Standard HRMS `Leave Application`. myHR doesn't add any custom fields to this doctype (the legacy `hr_approver` field has been removed — see §9).

### 3.2 Property Setter — `status` options

myHR pins the `status` Select field options to:

```
Open
Approved
Rejected
Cancelled
```

Pinned by `setup.py → _ensure_leave_application_status_property_setter()`, runs every migrate so drift is auto-corrected.

### 3.3 Custom fields touched on `Employee`

| Field | Type | Origin | Purpose |
|---|---|---|---|
| `leave_approver` | Link → User | core HRMS | The named manager who approves this employee's leaves. **Set in the Employee form → "Attendance and Leaves" section.** |

myHR adds **no** Employee custom fields for leave approval. HR Manager authority comes from the **role**, not from a per-Employee field.

### 3.4 Holiday-related custom field

`Holiday.custom_holiday_type` (Select: `Optional` / `Fixed` / `Weekly Off`) — added by myHR to support the optional-leave validation.

---

## 4. Approval Policy — Decision Matrix

### 4.1 Leave Application

| Caller's role / relationship to applicant     | Can approve? | Can reject? | Can cancel a submitted leave?                     |
|------------------------------------------------|:------------:|:-----------:|:-------------------------------------------------:|
| Applicant (themselves)                         | —            | —           | — (cancel via standard HRMS rules)                |
| Named in `Employee.leave_approver` (manager)   | ✓            | ✓           | ✓ (per HRMS DocPerm)                              |
| `HR Manager` role                              | ✓            | ✓           | ✓                                                 |
| `System Manager` role                          | ✓            | ✓           | ✓                                                 |
| Any other user                                 | ✗            | ✗           | ✗                                                 |

The Employee/HR-Manager rules apply on **desk** via standard HRMS DocPerm and on **PWA** via the `myhr.api.get_leave_applications` override (§5.3).

### 4.2 Attendance Request

| Caller's role / relationship to applicant     | Sees the draft in PWA Team Requests? | Can submit (= approve)? | Can cancel a submitted request? |
|------------------------------------------------|:----------:|:-------:|:----:|
| Applicant (themselves)                         | — (sees in own list) | — | ✓ (own doc) |
| Named in `Employee.leave_approver` (manager)   | ✓ — only their direct reports | ✓ (via DocPerm) | ✓ |
| `HR Manager` role                              | ✓ — every draft | ✓ | ✓ |
| `System Manager` role                          | ✓ — every draft | ✓ | ✓ |
| Any other user                                 | ✗            | ✗ | ✗ |

> **Note — change vs. stock HRMS:** the standard HRMS filter for `for_approval=true` on Attendance Request was just `docstatus=0, employee != self`, with **no approver-id check** because the doctype has no approver field. Net effect: every employee saw every other employee's drafts. The myHR override tightens this to "manager-of-record + HR roles" via `Employee.leave_approver` lookup.

---

## 5. Backend Behaviour

### 5.1 Override class

[`overrides/leave_application.py`](../myhr/overrides/leave_application.py) — extends `hrms.hr.doctype.leave_application.leave_application.LeaveApplication`.

```python
class LeaveApplication(HRMSLeaveApplication):
    def validate(self):
        super().validate()
        self._validate_optional_leave_rules()

    def _validate_optional_leave_rules(self):
        if not (self.leave_type and self.from_date and self.to_date):
            return
        if not frappe.db.get_value("Leave Type", self.leave_type, "is_optional_leave"):
            return
        if self.half_day:
            frappe.throw(_("Optional leaves can only be applied as full-day; half-day is not supported."))
        validate_optional_leave_dates(self.employee, self.from_date, self.to_date)

    def on_update(self):
        super().on_update()
        if self.docstatus == 0 and self.status == "Approved":
            self.submit()
```

Wired in `hooks.py`:

```python
override_doctype_class = {
    "Leave Application": "myhr.overrides.leave_application.LeaveApplication",
    ...
}
```

### 5.2 Optional-leave validation

[`leave_optional_holiday.py:validate_optional_leave_dates()`](../myhr/leave_optional_holiday.py)

- Iterates each day in `from_date..to_date` inclusive.
- For every day:
  - The Employee's `holiday_list` **must** contain a Holiday for that date.
  - That Holiday's `custom_holiday_type` must be `"Optional"`.
  - `Fixed`, `Weekly Off`, or unset → throws.
- Now invoked from the override's `validate()` (was previously only called by the PWA inline API, leaving desk users unchecked).

### 5.3 Team Requests override

[`api.py:get_leave_applications()`](../myhr/api.py)

```python
@frappe.whitelist()
def get_leave_applications(employee, approver_id=None, for_approval=False, limit=None):
    from hrms.api import get_leave_applications as hrms_impl

    if for_approval and _caller_is_hr_manager():
        return frappe.get_all(
            "Leave Application",
            filters={"docstatus": 0, "status": "Open", "employee": ("!=", employee)},
            fields=["name", "employee", "employee_name", "leave_type",
                    "from_date", "to_date", "total_leave_days", "status",
                    "leave_approver", "posting_date", "description"],
            order_by="posting_date desc, modified desc",
            limit_page_length=int(limit) if limit else 0,
        )
    return hrms_impl(employee=employee, approver_id=approver_id, for_approval=for_approval, limit=limit)
```

| Caller                                  | Behaviour                                                                                                                       |
|------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| User with `HR Manager` / `System Manager` role, `for_approval=1` | Sees ALL `docstatus=0, status='Open'` leave applications from other employees, regardless of who is named on `leave_approver`. |
| Anyone else, `for_approval=1`            | Sees only leave applications where they are the named `leave_approver` (standard HRMS).                                          |
| `for_approval=0`                          | Standard HRMS — returns the caller's own leave applications.                                                                    |

Wired via `hooks.py → override_whitelisted_methods` so the PWA's existing `teamLeaves` resource (which calls `hrms.api.get_leave_applications`) automatically goes through this without any frontend change.

### 5.3a Attendance Request — Team Requests override

[`api.py:get_attendance_requests()`](../myhr/api.py)

```python
@frappe.whitelist()
def get_attendance_requests(employee, for_approval=False, limit=None):
    from hrms.api import get_attendance_requests as hrms_impl

    if not for_approval:
        return hrms_impl(employee=employee, for_approval=False, limit=limit)

    user = frappe.session.user
    if _caller_is_hr_manager():
        # HR sees ALL drafts.
        return frappe.get_all(
            "Attendance Request",
            filters={"docstatus": 0, "employee": ("!=", employee)},
            fields=[...],
            order_by="creation desc",
            limit_page_length=int(limit) if limit else 0,
        )

    # Manager view: only drafts whose applicant lists me as their leave_approver.
    team_employees = frappe.get_all("Employee", filters={"leave_approver": user}, pluck="name")
    if not team_employees:
        return []
    return frappe.get_all(
        "Attendance Request",
        filters={"docstatus": 0, "employee": ("in", team_employees)},
        fields=[...],
        order_by="creation desc",
        limit_page_length=int(limit) if limit else 0,
    )
```

| Caller                                       | Behaviour                                                                                                       |
|----------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `HR Manager` / `System Manager`, `for_approval=1` | All `docstatus=0` Attendance Requests from other employees.                                                |
| Manager (anyone with at least one direct report — `leave_approver=current user`), `for_approval=1` | Only drafts from their reports. Returns `[]` if they have no reports. |
| Anyone else, `for_approval=1`                 | Empty list.                                                                                                      |
| `for_approval=0`                              | Standard HRMS — caller's own attendance requests.                                                                |

Wired the same way as Leave Application — `hooks.py → override_whitelisted_methods` re-routes `hrms.api.get_attendance_requests` → `myhr.api.get_attendance_requests`.

### 5.4 Inline PWA validation API

[`api.py:validate_optional_leave_for_application()`](../myhr/api.py)

Thin wrapper that catches `frappe.ValidationError` from `validate_optional_leave_dates` and returns a `{valid, message?}` dict so the form can show inline errors instead of throwing.

### 5.5 Optional-types lookup API

[`api.py:get_optional_leave_types()`](../myhr/api.py)

Returns the list of Leave Type names whose `is_optional_leave` flag is set. Used by the PWA to disable the half-day toggle when an optional leave type is selected.

### 5.6 Auto-submit logic

When an approver flips `status` to `"Approved"` and the document is still unsubmitted (`docstatus == 0`), `on_update` calls `self.submit()` in the same save → leave allocation is debited immediately, no second click.

`Rejected` does not auto-submit; the document stays at `docstatus=0` so the employee can withdraw / re-apply / discuss.

---

## 6. UI Specification

### 6.1 PWA — Apply Leave form (`views/leave/Form.vue`)

| Concern                  | Behaviour                                                                                                                                                                  |
|---------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Doctype source            | `hrms.api.get_doctype_fields("Leave Application")`. `naming_series`, `salary_slip`, `letter_head`, and HRMS's now-removed `hr_approver` references are filtered out client-side. |
| Approver picker           | `hrms.api.get_leave_approval_details(employee)` → standard HRMS department-approver list. The applicant picks their manager here. (HR Managers don't need to be in the list — they get visibility automatically via §5.3.) |
| Date range validation     | Reactive `myhr.api.validate_optional_leave_for_application` call on every change to `(employee, leave_type, from_date, to_date)`. Errors render inline on the date fields. |
| Half-day toggle           | Hidden + read-only when the selected `leave_type` is in the `myhr.api.get_optional_leave_types` set. Auto-resets `half_day=0` if it was set before the type changed.        |
| Read-only mode            | If opening someone else's draft and the current user is not the named `leave_approver`, all fields are set to read-only.                                                  |
| Posting date              | Defaults to today.                                                                                                                                                          |

### 6.2 PWA — My Team Requests

Standard HRMS view (`teamLeaves` resource) — calls the now-overridden `hrms.api.get_leave_applications` with `for_approval=1`. Requires no frontend change to surface HR Manager visibility.

### 6.3 Desk

Standard HRMS desk form. The override class still applies, so the optional-leave + half-day rules are enforced even via desk save / `frappe.client.save` / direct API.

---

## 7. End-to-End Flows

### 7.1 Employee applies for leave (manager-approved)

```
Employee opens PWA → "Apply Leave"
  Form pre-fills employee, posting_date.
  Picks leave_type, from_date, to_date.
    (PWA calls myhr.api.validate_optional_leave_for_application reactively.)
  Picks approver (default = Employee.leave_approver).
  Submit.
        ▼
LeaveApplication.validate (myhr override):
  super().validate()
  _validate_optional_leave_rules() — passes or throws.
        ▼
Record saved with docstatus=0, status='Open'.
        ▼
Manager opens PWA → "My Team Requests"
  Sees the request because leave_approver=manager.
  Sets status to 'Approved'.
        ▼
on_update fires → self.submit() → docstatus=1, leave allocation debited.
```

### 7.2 HR Manager approves on behalf of an absent manager

```
Employee submits leave; manager is on holiday.
        ▼
HR Manager opens PWA → "My Team Requests"
  myhr.api.get_leave_applications detects HR Manager role
    → returns ALL docstatus=0, status='Open' leaves regardless of leave_approver.
  HR Manager sets status to 'Approved'.
        ▼
on_update → self.submit(). Same outcome as 7.1.
```

### 7.3 Reject

```
Approver opens the request.
  Sets status to 'Rejected' (with optional reason).
        ▼
on_update fires; docstatus stays 0 (auto-submit only fires on 'Approved').
Employee can re-apply.
```

### 7.4 Optional-leave full-day (success)

```
Holiday List for the employee has 25 Dec, custom_holiday_type='Optional'.
Employee picks "Optional Leave", from_date=25 Dec, to_date=25 Dec, half_day=0.
        ▼
validate() → _validate_optional_leave_rules() → passes (Optional, full-day).
Record saved.
```

### 7.5 Optional-leave on a fixed holiday (rejection)

```
26 Jan is on the Holiday List with custom_holiday_type='Fixed'.
Employee picks "Optional Leave", to=26 Jan.
        ▼
validate() → throws "26 Jan is a fixed company holiday; optional leave cannot be applied on this date."
PWA: same error rendered inline on the date field via the reactive validation API.
```

### 7.6 Optional-leave half-day (rejection)

```
Employee somehow posts half_day=1 on an optional leave (e.g. stale client).
        ▼
validate() → throws "Optional leaves can only be applied as full-day; half-day is not supported."
PWA: half-day toggle is hidden in the first place when an optional type is selected (defence in depth).
```

### 7.7 Attendance Request — manager submits

```
Employee opens PWA → Attendance Request form
  Picks reason (Work From Home / On Duty / etc.), from_date, to_date.
  Save → docstatus=0 (Draft).
        ▼
Manager opens PWA → "My Team Requests"
  myhr.api.get_attendance_requests detects: not HR, but applicant.leave_approver = me.
  Manager taps Submit.
        ▼
docstatus=1 → HRMS creates the Attendance entries for the date range.
```

### 7.8 Attendance Request — HR Manager approves on behalf of an absent manager

```
Employee submits Attendance Request; their manager is on leave.
        ▼
HR Manager opens PWA → "My Team Requests"
  myhr.api.get_attendance_requests detects HR Manager role
    → returns ALL docstatus=0 Attendance Requests, regardless of leave_approver.
  HR Manager taps Submit.
        ▼
Same outcome as 7.7 — Attendance entries created.
```

### 7.9 Attendance Request — non-manager visibility (negative test)

```
Random employee X (not HR, has no direct reports) opens PWA → "My Team Requests".
        ▼
myhr.api.get_attendance_requests:
  not HR Manager → look up team_employees = Employee where leave_approver=X → []
  → returns [].
PWA list is empty for the attendance section. (Standard HRMS would have leaked all drafts.)
```

---

## 8. Setup / Configuration

| Step                                              | Where                                                                                                  | Idempotent | Notes                                                                                                                  |
|---------------------------------------------------|---------------------------------------------------------------------------------------------------------|:----------:|-------------------------------------------------------------------------------------------------------------------------|
| Pin Leave Application status options               | `setup.py → _ensure_leave_application_status_property_setter`                                          | ✓          | Runs every migrate; locks options to `Open\nApproved\nRejected\nCancelled`.                                            |
| Pin Employee.leave_approver label                  | `setup.py → _ensure_employee_leave_approver_labels`                                                    | ✓          | Sets label = "Leave Approver".                                                                                          |
| Holiday.custom_holiday_type field                  | `setup.py → MYHR_CUSTOM_FIELDS`                                                                         | ✓          | `Optional / Fixed / Weekly Off` Select.                                                                                |
| Drop legacy `hr_approver` scaffolding              | `patches/v1_1_remove_hr_approver.py`                                                                   | ✓          | Runs once; deletes the two custom fields, wipes leftover Property Setters, flips any `Approved by Manager` rows to `Approved`. |
| Override `Leave Application` class                 | `hooks.py → override_doctype_class`                                                                    | n/a        | Activates `myhr.overrides.leave_application.LeaveApplication`.                                                          |
| Override `hrms.api.get_leave_applications`         | `hooks.py → override_whitelisted_methods`                                                              | n/a        | Activates the broader Team Requests query for HR Managers (Leave Application).                                          |
| Override `hrms.api.get_attendance_requests`        | `hooks.py → override_whitelisted_methods`                                                              | n/a        | Tightens the previously-permissive Attendance Request Team Requests filter and broadens it for HR Managers.            |
| Sync PWA frontend                                  | `frontend_sync.apply_custom_ui()` (after_migrate)                                                      | ✓          | Rebuilds the HRMS Vue bundle with the myhr leave Form changes.                                                          |

---

## 9. Resolved Findings

| ID  | Finding                                                                                                                                        | Status                                                                                          |
|-----|-------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| F-1 | Two-stage scaffolding (`Approved by Manager` status, `hr_approver` custom fields on Employee + Leave Application) contradicted the requirement. | **Fixed** — Phase A: status options pinned to 4-state, both Custom Fields deleted via patch v1_1, all legacy "Approved by Manager" rows migrated to "Approved". Live verified: 0 of each. |
| F-2 | Server-side optional-holiday validation was bypassed (override's `validate()` was a pass-through; only PWA inline check fired).                  | **Fixed** — Phase B: `_validate_optional_leave_rules()` runs in `validate()`, covers desk + API + PWA paths uniformly. |
| F-3 | Legacy data migration helper `_migrate_pending_hr_status_values` was permanent code rather than a one-shot patch.                              | **Fixed** — Phase A: function deleted; one-shot replacement is `patches/v1_1_remove_hr_approver.py`. |
| F-4 | `on_update` did a redundant `frappe.get_doc(...)` re-fetch before submit.                                                                       | **Fixed** — Phase B: tightened to `self.submit()`.                                              |
| F-5 | PWA Team Requests showed leaves only to the named approver — HR Managers couldn't approve on behalf of someone else from PWA.                  | **Fixed** — Phase C: `hrms.api.get_leave_applications` overridden via `override_whitelisted_methods`. HR Manager role expands the filter to all open requests. |
| F-6 | No enforcement of full-day-only optional leaves.                                                                                                | **Fixed** — Phase B server-side throw + Phase D PWA hide-and-disable on optional leave types.   |
| F-7 | **Attendance Request:** stock HRMS Team Requests filter leaked every employee's draft to every other employee (no approver-id check, no workflow). | **Fixed** — Phase F: `hrms.api.get_attendance_requests` overridden. HR Managers see all drafts; non-HR users see only drafts whose applicant lists them as `leave_approver`. |
| **F-LA-AR-1** (was F-14 in EMPLOYEE_CHECKIN.md) | No server-side gate on **the act of approving** a Leave Application or submitting an Attendance Request. Stock HRMS perms granted submit to HR User and Employee for both doctypes; once the perm-framework let them in, anyone with the role could approve any leave or submit any AR regardless of who the named approver was. Compounded by: (a) all 10 demo users having `create_user_permission=1` which restricted HR users to their own Employee record; (b) `Leave Approver` role had **zero** doctype perms on Attendance Request, so even named managers couldn't submit. | **Fixed 2026-04-26.** New [apps/myhr/myhr/approval_gate.py](../myhr/approval_gate.py): `gate_leave_application_approval` (validate hook, fires when `status='Approved'` is set) and `gate_attendance_request_submit` (before_submit hook). Rule: HR Manager / System Manager / Administrator unconditional; named approver (LA's `leave_approver` field, AR's target `Employee.leave_approver`) allowed; everyone else throws `PermissionError`. Self-approval explicitly blocked. `ownership_gate.assert_writable_for_team` introduced as the AR companion that *also* allows the named manager to write the draft (so they can submit it). `Leave Approver` role granted submit/cancel/read/write on Attendance Request via a new additive perm in `setup.py:_ensure_additive_permissions` (`MYHR_ADDITIVE_PERMISSIONS`) so it survives migrate. CUP unticked on the 7 demo users who need org-wide visibility (CEO, CFO, HR Head, HR Manager, Sales/Ops/Marketing Managers); kept on the 3 executives. Verified 10/10 scenario tests across Employee / Manager / HR-User / HR-Manager / other-manager combinations for both LA and AR. <br><br>**Update 2026-04-27 (F-LA-AR-1 follow-up):** the CUP-based approach was simplified further. New Custom Field `Employee.custom_allow_view_reporting` plus a code-driven `permission_query_conditions` + `has_permission` hook in [`myhr/permissions.py`](../myhr/permissions.py) replaces CUP entirely on demo data. CUP is now `0` on all 10 demo employees. The 7 managers (CEO, CFO, HR-001, HR-002, SAL-001, OPS-001, MKT-001) have `custom_allow_view_reporting=1` (sees self + direct reports, read-only). The 3 executives (SAL-002, OPS-002, MKT-002) have `custom_allow_view_reporting=0` (sees self only). Patch [`v1_10_employee_view_reporting`](../myhr/patches/v1_10_employee_view_reporting.py) migrates existing sites. See [`EMPLOYEE_PERMISSIONS.md`](EMPLOYEE_PERMISSIONS.md) for the full spec. |
| **LA-1** (Phase 2) | After approval, `leave_approver` was the *intended* approver but no field captured *who actually clicked Approve* and *when*. Audit was incomplete. | **RESOLVED 2026-04-26.** New Custom Fields `Leave Application.custom_approved_by: Link User` and `custom_approved_on: Datetime` (declared in `setup.py:MYHR_CUSTOM_FIELDS`). Server-stamped in [LeaveApplication.validate](../myhr/overrides/leave_application.py)'s `_stamp_approval_audit()` on the Open → Approved transition. Locked once set; mutation throws unless `frappe.flags.allow_la_audit_edit=True`. Verified live: approval as MKT manager stamped `marketingmanager@erpdemo.local` + current timestamp; subsequent edit attempts throw. |
| **LA-2** (Phase 2) | No state-machine guard against `Approved → Open` reversal in-flight (docstatus=0). HR could un-approve silently between the user's Approve click and the auto-submit's effect, leaving stale audit. | **RESOLVED 2026-04-26.** [LeaveApplication.validate](../myhr/overrides/leave_application.py) `_guard_status_reversal()` throws on any docstatus=0 row where previous.status='Approved' and new.status differs. HR-side bypass via `frappe.flags.allow_la_status_revert=True`. |
| **LA-3** (Phase 2) | No in-app notification to the employee on Approved/Rejected. Stock HRMS may send email; the PWA Notification Log was silent. | **RESOLVED 2026-04-26.** `_notify_employee_on_verdict()` reads a `_verdict_to_notify` snapshot captured in validate (the auto-submit cascade confuses `get_doc_before_save`, so we capture once + replay) and inserts a `Notification Log` entry with subject `[myHR Leave] Approved — <Type> (<from> to <to>)` or `Rejected`. Best-effort (failures log, never raise). Verified live: approval produced 1 notification on the employee's user. |
| **LA-6** (Phase 2) | `validate_optional_leave_dates` issued one `frappe.get_all` per day in the [from, to] range. A 30-day leave application meant 30 sequential queries. | **RESOLVED 2026-04-26.** [validate_optional_leave_dates](../myhr/leave_optional_holiday.py) now does one batched `frappe.get_all` for the whole range and an in-memory dict lookup. Plus a date-order sanity check (`from > to` throws). |
| **AR-1** (Phase 2) | No employee notification when their AR is submitted (= attendance recorded for them). | **RESOLVED 2026-04-26.** New `myhr.employee_hooks.notify_employee_on_attendance_request_submit` wired as `Attendance Request.on_submit` doc_event in `hooks.py`. Subject `[myHR Attendance] Request approved — <from> to <to>` with the reason in the body. Verified live: manager-submitted AR triggered 1 notification on the employee. |
| **LA-AR-bulk** (Phase 2) | No HR-side bulk-approve action on Leave Application. HR had to open each LA and click Approve. | **RESOLVED 2026-04-26.** New whitelisted endpoint `myhr.api.bulk_approve_leave_applications(names)` (HR-only). Accepts a list (or comma-string) of LA names; flips `status='Approved'` on each via the override (which auto-submits). Returns `{approved, skipped, errors, error_log, total}`. Verified live: 3 in-flight LAs all approved + audit-stamped + notifications fired. |
| **LA-AR-cov** (Phase 2) | No coverage / completion report endpoints for HR. | **RESOLVED 2026-04-26.** Two new HR-only endpoints. `myhr.api.get_leave_coverage(employee=None)` returns one row per leave_type with `{open, approved, rejected, cancelled, days_approved, total}` for the current calendar year (employee-scoped if `employee` arg passed; HR-only otherwise). `myhr.api.get_attendance_request_coverage()` returns one row per employee with `{draft, submitted, cancelled, total}` so HR can spot stale drafts. Verified live: both return expected shapes. |
| **AR-3** | AR submit authority was hardcoded to `HR Manager / System Manager OR Employee.leave_approver`. Different clients have different policies — some want HR-only, some want self-marked attendance allowed — but changing the rule meant a code drop. | **RESOLVED 2026-04-28.** Three Check toggles on `HR Settings` (declared in `MYHR_CUSTOM_FIELDS`): `custom_ar_approver_hr_manager` (default 1), `custom_ar_approver_leave_approver` (default 1), `custom_ar_allow_self_submit` (default 0). [`approval_gate.gate_attendance_request_submit`](../myhr/approval_gate.py) reads these on every AR submit and admits each path independently; `Administrator` always passes. [`approval_gate.gate_hr_settings_save`](../myhr/approval_gate.py) wired as `HR Settings.validate` throws if all three are unticked (would otherwise lock everyone out). Defaults are seeded onto the existing singleton row from `setup.py:_seed_ar_approver_defaults` (after_migrate, after `_ensure_custom_fields`) — required because Frappe adds new Check columns to existing singleton rows with SQL default 0, so the Custom Field's declared `default: 1` never materialises. Defaults match pre-existing hardcoded behaviour, so existing sites don't change semantics on migrate. Verified live (v16 + v15): `_ar_settings()` reads `(True, True, False)`; `gate_hr_settings_save` throws `ValidationError` when all three flipped to 0. |

---

## 10. Verification (live)

Run on `erp.localhost` after migrate.

```python
# bench --site erp.localhost console
import frappe
assert not frappe.db.exists("Custom Field", "Employee-hr_approver")
assert not frappe.db.exists("Custom Field", "Leave Application-hr_approver")
assert frappe.db.count("Property Setter", {"field_name": "hr_approver"}) == 0
assert frappe.db.count("Leave Application", {"status": "Approved by Manager"}) == 0
assert frappe.db.get_value("Property Setter",
    {"doc_type": "Leave Application", "field_name": "status", "property": "options"},
    "value") == "Open\nApproved\nRejected\nCancelled"
assert frappe.db.exists("Patch Log", {"patch": "myhr.patches.v1_1_remove_hr_approver"})
hooks = frappe.get_hooks("override_whitelisted_methods")
assert hooks.get("hrms.api.get_leave_applications") == ["myhr.api.get_leave_applications"]
assert hooks.get("hrms.api.get_attendance_requests") == ["myhr.api.get_attendance_requests"]
print("Phase A–F verification: PASS")
```

This block was executed during the 2026-04-26 deploy and all assertions passed.

---

## 11. Manual Test Checklist (browser)

### 11.1 Leave Application

- [ ] Employee logs into the PWA and applies for a non-optional leave on a future date → record created, status=Open.
- [ ] Manager logs in → sees the request in "My Team Requests".
- [ ] Manager taps Approve → record auto-submits, balance debited.
- [ ] Employee applies again → manager rejects with reason → record stays unsubmitted, employee notified.
- [ ] Employee applies an Optional Leave on a Fixed holiday → date field shows inline error, save blocked.
- [ ] Employee selects an Optional Leave type → half-day toggle is hidden / disabled.
- [ ] Employee tries to half-day an optional leave via desk → throws full-day-only error.
- [ ] HR Manager (not the named approver) opens PWA → sees the same Open request → approves → submitted.
- [ ] Cancel an approved leave from the desk as HR Manager → standard HRMS cancel + balance restore.
- [ ] Drilling into Property Setters via desk: status options shown are exactly 4 (`Open / Approved / Rejected / Cancelled`).

### 11.2 Attendance Request

- [ ] Employee creates an Attendance Request from the PWA → record at docstatus=0 (Draft).
- [ ] Their manager (a user named on `Employee.leave_approver`) opens "My Team Requests" → sees the draft.
- [ ] A different non-HR employee with no direct reports opens Team Requests → sees nothing in the attendance section.
- [ ] HR Manager (no managerial relationship to the applicant) opens Team Requests → sees the draft.
- [ ] Manager taps Submit → docstatus=1, attendance entries created for the date range.
- [ ] HR Manager cancels a submitted Attendance Request → docstatus=2, attendance entries reversed (standard HRMS).

---

## 12. Files (final)

### Leave Application
- `apps/myhr/myhr/overrides/leave_application.py` — single-stage override class
- `apps/myhr/myhr/leave_optional_holiday.py` — optional-leave date validation helper
- `apps/myhr/myhr/patches/v1_1_remove_hr_approver.py` — one-shot cleanup of the legacy two-stage scaffolding
- `apps/myhr/myhr/frontend_changes/views/leave/Form.vue` — half-day disable for optional types

### Attendance Request
- `apps/myhr/myhr/api.py → get_attendance_requests` — override that tightens for non-HR users and broadens for HR Managers
- (No override class — Attendance Request submit/cancel logic is stock HRMS.)
- (No PWA frontend change — the existing `teamAttendanceRequests` resource keeps calling `hrms.api.get_attendance_requests`, now routed through myHR.)

### Shared
- `apps/myhr/myhr/api.py` — `get_leave_applications`, `get_attendance_requests`, `get_optional_leave_types`, `validate_optional_leave_for_application`
- `apps/myhr/myhr/hooks.py` — `override_doctype_class`, `override_whitelisted_methods`
- `apps/myhr/myhr/setup.py` — Property Setter pins, Holiday custom field
