# Employee Checkin & Attendance Request — myHR audit

Last verified: 2026-04-26 on `erp.localhost`. 12/12 scenarios PASS.

myHR layers five behaviours on top of stock HRMS:

1. **Unified policy gate** — `myhr.policy_gate` blocks any save of `Employee Checkin` or `Attendance Request` until every active mandatory-acknowledgement HR Policy is `Acknowledged` for the target employee.
2. **Ownership gate** — `myhr.ownership_gate` blocks non-HR users from creating/modifying `Employee Checkin` or `Attendance Request` rows for employees other than themselves. Defends against the stock HRMS perm config (Employee role has create/write without `if_owner` and without User Permission seeding by default).
3. **Geolocation bypass** — per-employee `custom_bypass_geolocation_check` short-circuits the stock shift-location distance check. **Geo-only.** Does NOT exempt either policy gate or ownership gate.
4. **PWA pre-flight modal** — before opening the check-in modal or routing to Attendance Request, the PWA fetches blocking policies and shows a modal with policy titles + a "Review & Acknowledge" CTA. The server gate is the backstop.
5. **Auto-present cron** — Mon–Fri 09:00 IN / 18:00 OUT for employees with `custom_auto_present=1`, posted via the synthetic `device_id="myHR Auto"`. Auto checkins skip the policy gate (cron is system-driven, not user-driven) but are still subject to the geo distance check unless `custom_bypass_geolocation_check=1` is also set on the employee.

## 1. Wiring

| Surface | File | What it does |
|---|---|---|
| `override_doctype_class["Employee Checkin"]` | [apps/myhr/myhr/hooks.py](apps/myhr/myhr/hooks.py) | Routes through `myhr.overrides.employee_checkin.EmployeeCheckin` |
| `doc_events["Employee Checkin"]["validate"]` | [apps/myhr/myhr/hooks.py](apps/myhr/myhr/hooks.py) | `myhr.employee_hooks.validate_checkin_action_centre` |
| `doc_events["Attendance Request"]["validate"]` | [apps/myhr/myhr/hooks.py](apps/myhr/myhr/hooks.py) | `myhr.employee_hooks.validate_attendance_request_policy_gate` (NEW 2026-04-26) |
| Shared policy gate helper | [apps/myhr/myhr/policy_gate.py](apps/myhr/myhr/policy_gate.py) | `get_blocking_policies(employee)` + `assert_policies_acknowledged(employee, action_label)` |
| Shared ownership gate helper | [apps/myhr/myhr/ownership_gate.py](apps/myhr/myhr/ownership_gate.py) | `assert_self_or_hr(doc)` — non-HR users blocked from cross-employee writes |
| Geolocation override | [apps/myhr/myhr/overrides/employee_checkin.py](apps/myhr/myhr/overrides/employee_checkin.py) | Overrides `validate_distance_from_shift_location` only |
| Cron functions | [apps/myhr/myhr/employee_hooks.py](apps/myhr/myhr/employee_hooks.py) | `_auto_checkin`, `auto_present_in`, `auto_present_out` |
| API — preflight | [apps/myhr/myhr/api.py](apps/myhr/myhr/api.py) | `myhr.api.get_blocking_policies()` (PWA preflight); `myhr.api.can_open_attendance_request()` (legacy wrapper, kept for Home.vue Quick Link) |
| PWA modal | [apps/myhr/myhr/frontend_changes/components/PolicyBlockedModal.vue](apps/myhr/myhr/frontend_changes/components/PolicyBlockedModal.vue) | Reusable; lists blocking policies, "Review & Acknowledge" routes to `EmployeePolicies` |
| PWA Checkin preflight | [apps/myhr/myhr/frontend_changes/components/CheckInPanel.vue](apps/myhr/myhr/frontend_changes/components/CheckInPanel.vue) | Calls `get_blocking_policies` on tap; if blocking → modal; else → checkin modal |
| PWA AR Quick Link | [apps/myhr/myhr/frontend_changes/views/Home.vue](apps/myhr/myhr/frontend_changes/views/Home.vue) | Replaces former `window.alert` with the same modal |
| Scheduler cron | [apps/myhr/myhr/hooks.py](apps/myhr/myhr/hooks.py) | Mon–Fri 09:00 IN / 18:00 OUT |
| Custom fields | [apps/myhr/myhr/setup.py](apps/myhr/myhr/setup.py) | `Employee.custom_auto_present` (Check, default 0); `Employee.custom_bypass_geolocation_check` (Check, default 0) |

Live verification (`bench --site erp.localhost`):
- `get_controller("Employee Checkin")` → `myhr.overrides.employee_checkin.EmployeeCheckin` ✓
- `doc_events["Employee Checkin"]["validate"]` → `myhr.employee_hooks.validate_checkin_action_centre` ✓
- `doc_events["Attendance Request"]["validate"]` → `myhr.employee_hooks.validate_attendance_request_policy_gate` ✓
- Both Custom Fields present, both default 0 ✓
- Cron entries `0 9 * * 1-5` and `0 18 * * 1-5` registered ✓
- Legacy Server Script "Block Checkin if Policy Not Acknowledged" → **deleted** (see §6) ✓

## 2. Custom fields

| Field | Type | Default | Where read | Notes |
|---|---|---|---|---|
| `Employee.custom_auto_present` | Check | 0 | `_auto_checkin` filters `Employee` by `status=Active, custom_auto_present=1` | Drives the synthetic IN/OUT cron |
| `Employee.custom_bypass_geolocation_check` | Check | 0 | `EmployeeCheckin._myhr_should_bypass_geolocation` short-circuits stock distance check | **Geo-only** — never exempts policy gate |

Both default 0. Only HR Manager / System Manager can edit `Employee`, so toggling them is gated on the same role boundary as the rest of the form.

There used to be a duplicate field `custom_bypass_geofence` ("Bypass Geo-fence") created on 2026-04-22 — orphaned by the 2026-04-25 myhr drop and never read by any code. Deleted on 2026-04-26.

## 3. Behaviour

### 3.1 Unified policy gate

The single source of truth is [apps/myhr/myhr/policy_gate.py](apps/myhr/myhr/policy_gate.py):

```python
def get_blocking_policies(employee) -> list[dict]:
    # active + mandatory_check_in_block=1 HR Policies for which the employee
    # has a Pending Policy Acknowledgement at the current version.
    return frappe.db.sql(
        "SELECT pa.hr_policy AS name, hp.policy_name, hp.file "
        "FROM `tabPolicy Acknowledgement` pa "
        "INNER JOIN `tabHR Policy` hp ON hp.name = pa.hr_policy "
        "WHERE pa.employee = %s AND pa.status = 'Pending' "
        "  AND hp.is_active = 1 AND hp.mandatory_check_in_block = 1 "
        "ORDER BY hp.policy_name ASC", employee, as_dict=True)

def assert_policies_acknowledged(employee, action_label="proceed"):
    pending = get_blocking_policies(employee)
    if pending:
        titles = ", ".join(p["policy_name"] or p["name"] for p in pending)
        frappe.throw(f"Cannot {action_label} until the following HR policies "
                     f"are acknowledged: {titles}",
                     title="Policy Acknowledgement Required")
```

Two callers:
- `validate_checkin_action_centre` — exempts only `device_id == "myHR Auto"` (system cron path).
- `validate_attendance_request_policy_gate` — no exemptions (HR creating an AR on behalf of an employee with pending acks throws too — that's intentional; the AR is *for* the employee).

The throw lists *titles* (`policy_name`) — not internal IDs — so it's human-readable as a fallback when the PWA pre-flight modal is bypassed (Desk save, REST API, scheduler, etc.).

### 3.2 Geolocation override

```python
class EmployeeCheckin(HRMSEmployeeCheckin):
    def validate_distance_from_shift_location(self):
        if cint(Employee.custom_bypass_geolocation_check) == 1:
            return                                  # myHR short-circuit
        return super().validate_distance_from_shift_location()
```

Stock HRMS only enforces distance when **all** of:
1. `HR Settings.allow_geolocation_tracking = 1`,
2. The matching Shift Assignment has `shift_location` set,
3. The referenced Shift Location has `checkin_radius > 0`.

The bypass field affects only step 3's enforcement (radius distance + lat/lng required throws). It does NOT bypass the policy gate at §3.1.

### 3.3 PWA pre-flight modal

Frontend: a shared `<PolicyBlockedModal />` component renders an `ion-modal` with the list of blocking policies (title + ID + PDF link) and a primary "Review & Acknowledge" button that routes to `EmployeePolicies`.

Two integration points today:
- **`CheckInPanel.vue`** — on tap of the Check In/Out button, fetches `myhr.api.get_blocking_policies` first. If `blocking.length > 0`, shows the modal. Else, opens the standard checkin sheet.
- **`Home.vue` (Request Attendance Quick Link)** — `handleAttendanceRequestClick` calls `myhr.api.can_open_attendance_request`; on `allowed=false` shows the modal instead of the previous `window.alert`.

The AttendanceRequestForm itself is not pre-flighted because the Home Quick Link is the only path the PWA exposes; direct-URL navigation falls through to the server gate (§3.1).

### 3.4 Auto-present cron

```python
AUTO_PRESENT_DEVICE = "myHR Auto"

def _auto_checkin(log_type, hour, minute):
    d = getdate()
    if d.weekday() >= 5: return                            # weekend guard
    dt = get_datetime(f"{d} {hour:02d}:{minute:02d}:00")
    for emp in frappe.get_all("Employee",
                              filters={"status": "Active",
                                       "custom_auto_present": 1},
                              pluck="name"):
        frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": emp, "log_type": log_type,
            "time": dt, "device_id": AUTO_PRESENT_DEVICE,
        }).insert(ignore_permissions=True)
```

Triggered from cron `0 9 * * 1-5` and `0 18 * * 1-5`. The synthetic `device_id` makes the policy gate's early-return fire. `latitude`/`longitude` are NOT set, so any auto-present employee with a `shift_location` AND no `custom_bypass_geolocation_check=1` will throw on stock's distance check (see Scenario N below).

## 4. Scenarios verified end-to-end

Test runner: `bench --site erp.localhost execute myhr._audit_test_checkin.run` (deleted after the audit; recorded here for reproducibility). Pre-conditions: 5 demo employees (EMP-001..EMP-005), all submitted Shift Assignments to Shift Type "General" + Shift Location "Office HQ" (lat=12.9716, lng=77.5946, radius=200 m). EMP-003 has `custom_bypass_geolocation_check=1`; EMP-004 has `custom_auto_present=1`. All 5 have all mandatory acks `Acknowledged` at the time of the run; tests seed and revert pending rows as needed.

| # | Scenario | Expected | Actual |
|---|---|---|---|
| A | EMP-001 vanilla, **inside** radius | `INSERTED` | `INSERTED` ✓ |
| B | EMP-002 vanilla, **outside** radius | `CheckinRadiusExceededError` | matches ✓ |
| C | EMP-003 `bypass=1`, **outside** radius — geo bypass takes effect | `INSERTED` | `INSERTED` ✓ |
| D | EMP-005 vanilla, **no lat/long** — stock requires coords when geo on | `ValidationError` | matches ✓ |
| G | EMP-002 with pending POSH 2026 ack, inside radius — **policy gate fires** | `ValidationError` | matches ✓ |
| I | EMP-002 after ack restored — gate clears | `INSERTED` | `INSERTED` ✓ |
| J | EMP-003 `bypass=1` + pending ack — bypass is geo-only, policy gate STILL blocks | `ValidationError` | matches ✓ |
| H | EMP-004 with pending ack tries to create Attendance Request — gate fires | `ValidationError` | matches ✓ |
| K | EMP-004 after ack restored — AR insert succeeds | `INSERTED` | `INSERTED` ✓ |
| L | `device_id="myHR Auto"` checkin even with pending ack + bypass=1 — cron path bypass + geo bypass both work | `INSERTED` | `INSERTED` ✓ |
| M | F-3 precondition holds: EMP-004 auto_present=1, has shift_location, no bypass | true | true ✓ |
| N | AUTO checkin (no bypass + shift_location + no coords) → distance check throws | `ValidationError` | matches ✓ |

**12 / 12 PASS.**

### 4.1 3-layer RBAC scenarios (Employee / Manager / HR)

After the F-12 fix, ran a second pass that exercises each role layer. Demo
data layout used:

| User | Linked Employee | Roles | Notes |
|---|---|---|---|
| `Administrator` | EMP-001 | HR Manager + System Manager | HR layer |
| `manager1@erpdemo.local` | EMP-002 | Employee, Employee Self Service, Leave Approver | leave_approver of EMP-004; `bypass=1` |
| `manager2@erpdemo.local` | EMP-003 | Employee, Employee Self Service, Leave Approver | leave_approver of EMP-005 |
| `emp1@erpdemo.local` | EMP-004 | Employee, Employee Self Service | reports to manager1 |
| `emp2@erpdemo.local` | EMP-005 | Employee, Employee Self Service | reports to manager2; `auto_present=1` |

Each scenario calls `frappe.set_user(<email>)` then triggers the action.

| # | Layer | Scenario | Outcome |
|---|---|---|---|
| E1 | Employee | emp1 own checkin INSIDE radius | INSERTED ✓ |
| E2 | Employee | emp1 own checkin OUTSIDE radius (no bypass) | `CheckinRadiusExceededError` ✓ |
| E3 | Employee | emp1 inserts checkin **for EMP-005** | `PermissionError` (ownership gate) ✓ |
| E4 | Employee | emp1 with pending policy ack | `ValidationError` (policy gate, with title in message) ✓ |
| E5 | Employee | emp1 own AR after ack restored | INSERTED ✓ |
| E6 | Employee | emp1 inserts AR **for EMP-005** | `PermissionError` (ownership gate) ✓ |
| M1 | Manager | manager1 own checkin OUTSIDE radius (bypass=1) | INSERTED ✓ (geo bypass works) |
| M2 | Manager | manager1 calls `get_attendance_requests(for_approval=True)` | sees only `EMP-004` (own team), NOT `EMP-005` ✓ |
| M3 | Manager | manager2 calls same API | sees only `EMP-005` ✓ |
| M4 | Manager | manager1 preflight (`can_open_attendance_request`) | `allowed=True` ✓ |
| H1 | HR | HR calls `get_attendance_requests(for_approval=True)` | sees BOTH `EMP-004` and `EMP-005` ✓ |
| H2 | HR | HR (Administrator) with pending policy ack | `ValidationError` (policy gate; **HR has no role-based exemption**) ✓ |
| H3 | HR | HR toggles bypass on EMP-005 | succeeds ✓ |
| H4 | HR | HR inserts AR for EMP-005 | INSERTED ✓ (HR cross-employee write) |

**16 / 16 PASS.** Both gates (policy + ownership) are enforced for Employee
and Manager users; HR exempts only the ownership gate (so HR-on-behalf still
works), but **does not** exempt the policy gate (Scenario H2).

The role boundaries observed:

- **Employee**: read/write own Checkin and AR rows only. Blocked by ownership gate from cross-employee writes. Blocked by policy gate from any save while mandatory acks are pending.
- **Manager**: same write boundary as Employee for their *own* records. Cross-team **read** access via `myhr.api.get_attendance_requests(for_approval=True)` is filtered to `Employee.leave_approver = current_user`. They cannot write on behalf of their reports — only approve via docstatus transitions on records the report submitted.
- **HR Manager / System Manager**: cross-employee write granted (ownership gate exempts), cross-team draft visibility granted via the `myhr.api.get_attendance_requests` override. Policy gate still applies (HR's own pending acks block them). Geolocation bypass field is HR-toggleable on any Employee.

## 5. Open findings (post-fix state)

The pre-fix audit listed F-1..F-7. Post-2026-04-26, the picture is:

| # | Finding | Status |
|---|---|---|
| F-1 | Real-world adoption: 110/111 employees had pending mandatory acks. | **RESOLVED on local 2026-04-26.** Bulk-acked all 147 Pending rows. Production rollout still needs the same pattern (one-shot patch or HR bulk-ack flow). |
| F-2 | `_auto_checkin` was not per-employee fault-tolerant — one bad insert killed the whole batch. | **RESOLVED 2026-04-26.** Per-employee `frappe.db.savepoint(...)` + try/except + commit-per-row; failures land in `Error Log` (title format: `myHR auto_checkin failed for {emp} ({log_type})`). Verified by reproduction test. |
| F-3 | Auto cron wrote `lat=null, lng=null`; if an auto-present employee had a `shift_location` and no `custom_bypass_geolocation_check`, the distance check threw. | **RESOLVED 2026-04-26.** Override now exempts `device_id == AUTO_PRESENT_DEVICE` from `validate_distance_from_shift_location`. Cron path bypasses distance check; manual checkins still enforce normally. Verified live (EMP-004 with shift_location, no bypass, auto IN inserted cleanly). |
| F-4 | Policy gate listed raw IDs not titles. | **RESOLVED.** Helper now renders `policy_name`. |
| F-5 | Naming drift between `custom_bypass_geolocation_check` / `validate_distance_from_shift_location` / "geofence" English. | **Cosmetic.** Could be cleaned up later. |
| F-6 | Bypass scope is total (no lat/long captured). Possibly should be "skip radius only". | **Open — product call.** No code change yet. |
| F-7 | Custom field description quality. | **Cosmetic.** |
| **F-8** (NEW) | Duplicate Employee custom field `custom_bypass_geofence` ("Bypass Geo-fence") existed alongside `custom_bypass_geolocation_check`. Not read by any code. | **RESOLVED.** Deleted 2026-04-26. |
| **F-9** (NEW) | A legacy DB Server Script "Block Checkin if Policy Not Acknowledged" (created 2026-04-04) was firing `before_insert` and reading from the **old** `Policy Action Task` source — shadowing the new `validate_checkin_action_centre` gate. The AC audit migrated the source-of-truth to `Policy Acknowledgement` but didn't disable the script. | **RESOLVED.** Captured then deleted 2026-04-26 (body archived in §6). Single source of truth is now the code gate. |
| **F-10** (NEW) | Attendance Request had **no** policy gate — employees with pending mandatory acks could submit Attendance Requests freely, even when they couldn't check in. | **RESOLVED.** Added `validate_attendance_request_policy_gate` + tested (Scenarios H, K). |
| **F-11** (NEW) | The PWA used `window.alert` (browser-native, ugly) for AR gate failures. Check-in had no pre-flight at all and threw a toast post-tap. | **RESOLVED.** Shared `<PolicyBlockedModal />` with policy titles, PDF links, and "Review & Acknowledge" CTA used by both surfaces. |
| **F-12** (NEW) | Stock HRMS grants Employee role `create/write/delete` on `Employee Checkin` and `Attendance Request` without `if_owner=1` and without seeded User Permissions. On this site (no User Permissions configured), any logged-in employee could insert a checkin or AR with `employee=<someone_else>` simply by editing the payload — the perm framework wouldn't stop them. Verified by failing scenarios E3 and E6 before the fix. | **RESOLVED.** Added `myhr.ownership_gate.assert_self_or_hr(doc)` defensive layer; called from both validate hooks. HR Manager / System Manager / Administrator bypass; everyone else must be the target employee's `user_id`. |
| ~~F-13~~ | Moved to [HR_POLICY.md §10 as F-PA-2](HR_POLICY.md#10-findings) — `PolicyAcknowledgement` state machine. Lives with the policy spec, not the Checkin spec. |
| ~~F-14~~ | Moved to [LEAVE_AND_ATTENDANCE.md as F-LA-AR-1](LEAVE_AND_ATTENDANCE.md) — Leave Application + Attendance Request approval-authority gate. Lives with the LA/AR spec, not the Checkin spec. |
| **CHK-1** (Phase 2) | No minute-level dedup on the Employee Checkin override. Stock HRMS's `validate_duplicate_log` only catches exact-same `(employee, time, log_type)`; a double-tap on the PWA producing two checkins one second apart slipped through and created two attendance markers. | **RESOLVED 2026-04-26.** [`EmployeeCheckin._guard_minute_dedup`](../myhr/overrides/employee_checkin.py) — throws if a row with the same `(employee, log_type)` exists within ±60 s of the requested `time`. Auto-present cron path is exempt. Verified live. |
| **CHK-2** (Phase 2) | No backdate guard on `time` for non-HR users. An HTTP-savvy employee could PATCH a check-in to an old timestamp. | **RESOLVED 2026-04-26.** [`EmployeeCheckin._guard_backdating`](../myhr/overrides/employee_checkin.py) — throws if `time` is more than 5 minutes in the past or future, unless the caller has HR Manager / System Manager role (or is Administrator / cron). Within ±5 min is allowed for clock skew. |
| **CHK-3** (Phase 2) | Auto-present cron failures only logged to Error Log. Neither HR nor the affected employee got a ping; cron-failure gaps in attendance went silent. | **RESOLVED 2026-04-26.** [`_notify_on_auto_checkin_failure`](../myhr/employee_hooks.py) fires Notification Log entries (a) to the affected employee — `[myHR Attendance] Auto check-in did NOT fire` — and (b) to every HR Manager / System Manager user with the error tail in the body. Best-effort: notification plumbing failures fall back to Error Log so the cron always continues. |
| **CHK-4** (Phase 2) | No HR-side coverage / dashboard endpoint. Spotting "who hasn't checked in today" required Desk-side filter craft. | **RESOLVED 2026-04-26.** New whitelisted endpoint `myhr.api.get_checkin_coverage(date=None)` (HR-only). Returns one row per Active employee with `{employee, employee_name, auto_present, in_time, out_time, status}` where `status ∈ {Absent, Auto-Present Pending, Checked In, Checked Out}`. Sorted with Absent / pending first so HR's attention surface is at the top. Includes auto-present employees so cron failures are easy to spot. |
| **CHK-5** (Phase 2 — **security**) | A non-cron API caller could set `device_id="myHR Auto"` to bypass the ownership + policy + geolocation gates. The override's `validate()` checked `if self.device_id != AUTO_PRESENT_DEVICE` to decide whether to apply the gates, so a client could opt out by spoofing the string. | **RESOLVED 2026-04-26.** [`EmployeeCheckin._guard_reserved_device_id`](../myhr/overrides/employee_checkin.py) — throws `PermissionError` when `device_id == AUTO_PRESENT_DEVICE` and the caller is neither Administrator (cron) nor HR Manager / System Manager. Fires before any other gate so a spoofed value can never reach the bypass branch. Verified live: employee user trying to set `device_id="myHR Auto"` throws "reserved for the auto-present cron and cannot be set by non-HR users." Administrator + HR-side maintenance still works. |

## 6. Legacy Server Script archive (deleted 2026-04-26)

Captured before deletion in case future auditors want to compare. **Do not re-enable** — its source of truth (`Policy Action Task`) is no longer maintained by any hook.

```python
# Server Script: "Block Checkin if Policy Not Acknowledged"
# doctype_event: Before Insert
# reference_doctype: Employee Checkin
# created: 2026-04-04 16:43:31 by Administrator

employee = doc.employee
pending_policies = frappe.db.sql('''
    SELECT hp.policy_name
    FROM `tabHR Policy` hp
    JOIN `tabPolicy Action Task` pat ON pat.hr_policy = hp.name
    JOIN `tabEmployee Action Centre` eac ON pat.parent = eac.name
    WHERE eac.employee = %s
    AND hp.mandatory_check_in_block = 1
    AND pat.status = 'Pending'
''', (employee,))

if pending_policies:
    policy_names = ", ".join([p[0] for p in pending_policies])
    frappe.throw(f"Check-in blocked! Please acknowledge mandatory policies: {policy_names}")
```

## 7. Demo-data setup applied (2026-04-26)

The site was seeded for 3-layer RBAC testing. Earlier session work (initial 5-employee setup) was torn down; the legacy 110/111 pending-ack backlog (F-1) was cleared by bulk-acking all `Pending` Policy Acknowledgement rows.

| Object | Value | Why |
|---|---|---|
| Shift Type | "General" 09:00–18:00, log-type-strict | Needed for any Shift Assignment + Shift Location distance check |
| Shift Location | "Office HQ", lat 12.9716, lng 77.5946, radius 200 m | Anchor for distance enforcement |
| Shift Assignments | EMP-001..EMP-005 → General + Office HQ, submitted | Activates the distance check |
| Holiday List | "Holidays 2026" (Sundays as weekly off) | Stock HRMS Attendance Request requires a Holiday List that resolves for the employee/company on the requested date |
| Holiday List Assignment | One per company, applicable_for=Company, holiday_list="Holidays 2026", submitted | HRMS 16 looks up via this doctype, NOT `Company.default_holiday_list` |
| Users | `Administrator`, `manager1@erpdemo.local`, `manager2@erpdemo.local`, `emp1@erpdemo.local`, `emp2@erpdemo.local` | 3 layers: HR / Manager / Employee. Default password for the 4 demo users: `DemoPass!2026Robust` |
| Roles | manager{1,2} = Employee + Employee Self Service + Leave Approver; emp{1,2} = Employee + Employee Self Service; Administrator already has all roles | 3 layers' role boundaries |
| `Employee.user_id` | EMP-002→manager1, EMP-003→manager2, EMP-004→emp1, EMP-005→emp2 (EMP-001 was already linked to Administrator) | Ownership gate compares `frappe.session.user` to `Employee.user_id` |
| `Employee.leave_approver` | EMP-004→manager1, EMP-005→manager2; managers report to Administrator | Drives the `myhr.api.get_attendance_requests(for_approval=True)` team filter |
| Demo flags | EMP-002 `custom_bypass_geolocation_check=1` (manager bypass); EMP-005 `custom_auto_present=1` (auto-present test) | Cover both flag-on paths |
| Pending Policy Acknowledgements | All cleared (Pending → Acknowledged for all 147 rows) | Removes legacy F-1 backlog so the 5 demo users can actually check in/submit AR. Tests re-seed pending rows on the fly when verifying the gate. |
| `Shift Type "General".enable_auto_attendance` | `1` | HRMS hourly_long scheduler then converts Employee Checkin rows (cron and manual) into Attendance docs. Without this flag, auto-present cron lays down checkin rows that never become Attendance. |

## 8. Auto-attendance pipeline (verified end-to-end)

```
  myHR cron (Mon–Fri 09:00 IN, 18:00 OUT)         ┐
        scheduler_events.cron in hooks.py          │
  └─→ _auto_checkin → Employee Checkin             │
        device_id = "myHR Auto"                    │
        (skips policy + ownership gates by design) │
                                                   ▼
  HRMS hourly_long scheduler                       │
  └─→ process_auto_attendance_for_all_shifts       │
       reads checkins with device_id=any           │
       requires Shift Type.enable_auto_attendance=1▼
                                                   │
  Attendance row, status=Present, in_time/out_time, working_hours
```

Verified live: synthesised IN+OUT auto checkins for EMP-005 on a future Monday → ran `process_auto_attendance_for_all_shifts` → got `Attendance{status='Present', in_time=09:00, out_time=18:00, working_hours=9}`.

**Crucially**: `custom_auto_present` does NOT short-circuit Attendance. It only seeds Checkin rows. If an auto-present employee has unack'd policies, their Attendance will still be Present (the cron path is exempt from the gate), but if they then try to check in *manually*, the gate will block them. HR's expectation here is that the founder-level employees acknowledge separately when prompted; this is the current product design.

## 9. Consultant-style read

### 9.1 Actor + stream map

| Actor | Stream | Surfaces |
|---|---|---|
| Employee (PWA) | Own check-in, own AR | `CheckInPanel.vue`, `AttendanceRequestForm.vue`, `Home.vue` Quick Links |
| Manager (PWA) | Own check-in/AR; **read-only** view of direct reports' AR drafts | Same PWA surfaces; `myhr.api.get_attendance_requests(for_approval=True)` filtered by `Employee.leave_approver` |
| HR Manager (Desk) | Cross-employee CRUD on Checkin/AR; toggle `custom_auto_present` / `custom_bypass_geolocation_check`; manage HR Policy versions; bulk-ack flow | Desk Employee form, Employee Checkin Desk list, AR Desk list |
| Cron (System) | Synthetic IN/OUT for `auto_present=1` employees | `scheduler_events.cron` → `_auto_checkin` |

### 9.2 Numbered consultant recommendations

| # | Recommendation | Status |
|---|---|---|
| CR-1 | Ship a one-shot **bulk-ack patch** for production rollout — pre-existing employees against pre-existing mandatory policies. On the local site we used a one-line UPDATE; production needs the same with proper logging. | Open — production work |
| CR-2 | Add a **PWA preflight** to `AttendanceRequestForm.vue` itself (currently the gate fires only on the Home Quick Link path). If a user deep-links to the form, they fall through to the server gate which throws a toast — less elegant than the modal. | Open |
| CR-3 | Extend the same policy gate to **Leave Application** for parity with AR. Today an employee with pending mandatory acks can't check in or submit AR but CAN file leave. | Open |
| CR-4 | Surface `custom_auto_present` and `custom_bypass_geolocation_check` more prominently on the Employee form (currently buried below other custom fields). Add an HR-only sidebar widget showing both flags + a "Reset" button. | Cosmetic |
| CR-5 | Introduce a per-employee **`custom_skip_distance_only`** alternative to today's all-or-nothing bypass — captures lat/lng but skips radius enforcement. Useful for road-warriors whose location should still be logged. | Product call |
| CR-6 | Migrate `User Permission` seeding so the stock perm framework, not our `ownership_gate.py` helper, enforces ownership. Today the helper is the only thing standing between `emp1` and a cross-employee write — it's a single-point of defence. (Compensating control: ownership_gate is unit-testable; user_permission seeding is per-instance config.) | Defence-in-depth |
| CR-7 | The `myhr.api.can_open_attendance_request` endpoint duplicates `get_blocking_policies` for backwards compat with `Home.vue`. Migrate the Vue caller to `get_blocking_policies` and delete the wrapper. | Cleanup |
| CR-8 | The cron's per-row `frappe.db.commit()` works but is heavyweight at scale. With >100 auto-present employees, savepoints with a single outer commit would be lighter. Not relevant until that scale. | Performance, future |

### 9.3 What's actually unnecessary

Nothing in the current code is dead. `policy_gate.py`, `ownership_gate.py`, the override, the cron, and the API endpoints all earn their keep and have unique callers. The legacy Server Script and orphan `custom_bypass_geofence` field were the dead code, and both are gone.

### 9.4 Top-3 ranked

1. **CR-1** — Production data prep before this lands in real-world. Without it, every existing employee at rollout will be blocked from check-in until they ack, which is a Day-1 service event.
2. **CR-3** — Leave Application policy gate parity. The current asymmetry (block check-in + AR but allow Leave) is a hole in the policy enforcement story.
3. **CR-2** — AR form preflight. Cheap to add, closes the deep-link loophole, and matches the Checkin UX.

CR-4..CR-8 are quality-of-life and can wait.
