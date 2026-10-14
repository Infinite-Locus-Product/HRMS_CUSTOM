# Dummy / Demo Data — Canonical Set

This document defines the canonical dummy/demo data set used to QA HR features on both v15 (`atbhr`) and v16 (`myhr`). Run the seed scripts on a fresh site and you should land in the same state on both versions.

The canonical set is the richer 10-employee org chart originally authored in v15 (`atbhr.scripts.seed_v15` + `atbhr.scripts.seed_policies`). v16 `myhr.setup_dummies` has been brought up to parity. Numbers/IDs/emails/flags are shared — only the company name and the holiday list name are environment-specific (v16 looks them up dynamically; v15 targets `ERP 15 Company Pvt Ltd` + `Holidays 2026`).

---

## Departments

These Department records must exist (under the target company) before seeding employees. Existing v15 sites already have them. v16 sites: create them by hand in the desk or rely on the script's department lookup (employees are seeded without a department link if the department row is missing — same row otherwise valid).

| Department Name |
|---|
| HR Test |
| Sales |
| Operations |
| Marketing |

> The CEO and CFO roles do not carry a department in this seed set.

---

## Employees

Ten Employees forming a CEO → C-suite → IC org chart. `custom_employee_id` is forced into `Employee.name` by atbhr/myhr — so the rows below land at `Employee.name == custom_employee_id`. `reports_to` is the manager's `Employee.name` (i.e. the manager's `custom_employee_id`). `leave_approver` is the manager's `user_id` email.

| Employee ID | Name (employee_name) | Designation | Department | Reports To | Leave Approver | Email (user_id) | CUP | custom_allow_view_reporting | custom_emp_directory | custom_add_to_action_centre | custom_auto_present | custom_bypass_geolocation_check | DOB | DOJ | Gender |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CEO | CEO (CEO) | CEO | — | — | — | ceo@erpdemo.local | 0 | 1 | 0 | 1 | 1 | 1 | 1990-01-01 | 2024-01-01 | Male |
| CFO | CFO (CFO) | CFO | — | CEO | ceo@erpdemo.local | cfo@erpdemo.local | 0 | 1 | 1 | 1 | 1 | 1 | 1990-01-01 | 2024-01-01 | Male |
| HR-001 | HR Head (HR-001) | HR Head | HR Test | CEO | ceo@erpdemo.local | hrhead@erpdemo.local | 0 | 1 | 1 | 1 | 0 | 0 | 1990-01-01 | 2024-01-01 | Male |
| HR-002 | HR Manager (HR-002) | HR Manager | HR Test | HR-001 | hrhead@erpdemo.local | hrmanager@erpdemo.local | 0 | 1 | 1 | 1 | 0 | 0 | 1990-01-01 | 2024-01-01 | Male |
| SAL-001 | Sales Manager (SAL-001) | Sales Manager | Sales | CEO | ceo@erpdemo.local | salesmanager@erpdemo.local | 0 | 1 | 1 | 1 | 0 | 0 | 1990-01-01 | 2024-01-01 | Male |
| SAL-002 | Sales Executive (SAL-002) | Sales Executive | Sales | SAL-001 | salesmanager@erpdemo.local | salesexec@erpdemo.local | 0 | 0 | 1 | 1 | 0 | 0 | 1990-01-01 | 2024-01-01 | Male |
| OPS-001 | Operations Manager (OPS-001) | Operations Manager | Operations | CEO | ceo@erpdemo.local | opsmanager@erpdemo.local | 0 | 1 | 1 | 1 | 0 | 0 | 1990-01-01 | 2024-01-01 | Male |
| OPS-002 | Operations Executive (OPS-002) | Operations Executive | Operations | OPS-001 | opsmanager@erpdemo.local | opsexec@erpdemo.local | 0 | 0 | 1 | 1 | 0 | 0 | 1990-01-01 | 2024-01-01 | Male |
| MKT-001 | Marketing Manager (MKT-001) | Marketing Manager | Marketing | CEO | ceo@erpdemo.local | marketingmanager@erpdemo.local | 0 | 1 | 1 | 1 | 0 | 0 | 1990-01-01 | 2024-01-01 | Male |
| MKT-002 | Marketing Executive (MKT-002) | Marketing Executive | Marketing | MKT-001 | marketingmanager@erpdemo.local | marketingexec@erpdemo.local | 0 | 0 | 1 | 1 | 0 | 0 | 1990-01-01 | 2024-01-01 | Male |

Notes:
- All employees: `status="Active"`, `holiday_list="Holidays 2026"` (v15) or the site's first available Holiday List (v16).
- `first_name = designation.split()[0]`, `last_name = custom_employee_id`.
- `user_id` set to the email; the seed pre-creates the matching `User` row (System User, role `Employee`, welcome email suppressed) **before** inserting the Employee — without that the ERPNext employee controller's `add_user_permission` call silently no-ops.
- Leave Approver is auto-resolved via `frappe.db.get_value("Employee", reports_to, "user_id")` at seed time.
- `CUP` = `create_user_permission` (stock Check field on Employee). **`CUP` is now `0` on all 10 demo employees** — the new visibility model (see below) replaces it. The column is kept in the table for traceability.
- `custom_allow_view_reporting` = atbhr/myhr-added Check field on Employee. `1` means the user can see their own Employee record **plus** their direct reports (`reports_to == self`); `0` means self only. See [Employee Visibility Policy](#employee-visibility-policy) below and [`EMPLOYEE_PERMISSIONS.md`](EMPLOYEE_PERMISSIONS.md) for the full spec.

---

## HR Policies

Five active HR Policies; PAs are auto-seeded via `after_save_hr_policy` for every active employee.

| Policy Name | Category | is_active | mandatory_check_in_block | applies_to_all_employees | applicability_logic | file |
|---|---|---|---|---|---|---|
| Leave Policy 2024 | Leave | 1 | 0 | 1 | OR | /files/sample_policy.pdf |
| POSH Policy (Mandatory) | POSH | 1 | 1 | 1 | OR | /files/sample_policy.pdf |
| Gratuity Policy | Gratuity | 1 | 0 | 1 | OR | /files/sample_policy.pdf |
| Employee Data Protection Policy | General | 1 | 1 | 1 | OR | /files/sample_policy.pdf |
| POSH 2026 | POSH | 1 | 1 | 1 | OR | /files/sample_policy.pdf |

All policies are inserted with `version=1` and the `file` field pointing at `/files/sample_policy.pdf` (the upload itself is not part of the seed — point the file URL at any uploaded asset, or accept that the link target is dangling for QA purposes).

---

## Leave Type & Leave Period

A single optional leave type and a 2026-calendar-year Leave Period.

| Doctype | Field | Value |
|---|---|---|
| Leave Type | leave_type_name | Optional Holiday Leave |
| Leave Type | is_optional_leave | 1 |
| Leave Type | max_continuous_days_allowed | 1 |
| Leave Type | include_holiday | 1 |
| Leave Period | name | Leave Period 2026 |
| Leave Period | from_date | 2026-01-01 |
| Leave Period | to_date | 2026-12-31 |
| Leave Period | is_active | 1 |
| Leave Period | company | (target company — `ERP 15 Company Pvt Ltd` on v15, looked up on v16) |
| Leave Period | optional_holiday_list | Holidays 2026 (v15) / first available Holiday List (v16) |

---

## Leave Allocations

Submitted Leave Allocation rows for every active Employee:

| Field | Value |
|---|---|
| leave_type | Optional Holiday Leave |
| from_date | 2026-01-01 |
| to_date | 2026-12-31 |
| new_leaves_allocated | 10 |
| docstatus | 1 (submitted) |

Total expected after seeding the 10 demo employees: 10 submitted Leave Allocations.

---

## Policy Acknowledgements

PAs are NOT inserted manually by the seed scripts. Instead:

1. The HR Policy `after_save` hook (`atbhr.policy_hooks.after_save_hr_policy` / `myhr.policy_hooks.after_save_hr_policy`) auto-creates a `Policy Acknowledgement` (status `Pending`) for every active Employee whenever an HR Policy is saved.
2. After all five policies are inserted, the seed script bulk-acknowledges all `Pending` PAs by setting `status="Acknowledged"` and saving — so the demo starts "all green".

Expected counts after seeding:
- 10 employees × 5 active policies = **50** Policy Acknowledgements
- All 50 in `status="Acknowledged"` (0 Pending)

---

## Holidays

- **Holiday List name**: `Holidays 2026` (v15). v16 uses whatever is the first/site-default Holiday List.
- **Custom field**: every Holiday row carries `custom_holiday_type` ∈ {`Optional`, `Fixed`, `Weekly Off`}. The optional-leave gate (`validate_optional_leave_dates`) only accepts Optional dates from the employee's holiday list.
- **Sundays**: 52 Sundays of 2026, `weekly_off=1`, `custom_holiday_type="Weekly Off"`. Patch `v1_7_fix_holiday_type_for_weekly_off` enforced this on existing rows; the `validate_holiday_list` hook keeps it in sync going forward.
- **Optional days**: at least one row tagged `custom_holiday_type="Optional"` is required for QA of optional leave allocation/use. The seed scripts do NOT create the Holiday List or its rows — they assume `Holidays 2026` was created out-of-band (typical Frappe HR setup) and reference it by name. See the Holiday List in the desk for the explicit holiday rows on the site.

If the Holiday List is missing on a fresh v16 site, the seed will skip the `holiday_list` field on the Employee (and the Leave Period seed will also skip itself). Create a Holiday List manually first.

---

## Employee Visibility Policy

Who can see whose `Employee` record on the desk Employee list. The previous demo set used the stock `create_user_permission` (CUP) Check field, which created `User Permission` rows that locked each user to their own Employee record. That approach has been retired in favour of a code-driven model that lets a manager see **self + direct reports** without per-row User Permission maintenance.

Live spec: [`EMPLOYEE_PERMISSIONS.md`](EMPLOYEE_PERMISSIONS.md). Implementation: [`atbhr/permissions.py`](../atbhr/permissions.py) wired via `permission_query_conditions["Employee"]` + `has_permission["Employee"]` in [`atbhr/hooks.py`](../atbhr/hooks.py).

**The rule**

| User | Read | Write |
|---|---|---|
| Administrator | all | all |
| HR Manager / System Manager | all | all |
| HR User | all | none (stock docperm) |
| Has Employee linked, `custom_allow_view_reporting = 1` | self + **direct reports** (`reports_to == self`) | none |
| Has Employee linked, `custom_allow_view_reporting = 0` | self only | none |
| No Employee linked | none | none |

Direct reports only — not the whole sub-tree. Read-only for non-HR users.

**Demo split**

| `custom_allow_view_reporting` | Count | Employees | Purpose |
|---|---|---|---|
| 1 (managers) | 7 | CEO, CFO, HR-001, HR-002, SAL-001, OPS-001, MKT-001 | Sees self + direct reports — needed so the Action Request / Leave dashboards render the team list for approval flows |
| 0 (executives) | 3 | SAL-002, OPS-002, MKT-002 | Sees only their own Employee record — simulates a regular employee's PWA experience |

`create_user_permission` is `0` on **all 10** demo employees. The patch [`v1_10_employee_view_reporting`](../atbhr/patches/v1_10_employee_view_reporting.py) migrates existing sites: deletes the stale CUP-driven `User Permission` rows on the 10 demo employees, sets `create_user_permission=0` on all of them, and sets `custom_allow_view_reporting=1` on the 7 managers / `0` on the 3 executives. Idempotent.

**UI test matrix**

Login each user via Switch User from the desk and load `/desk/employee` — expected count of visible Employee rows:

| Login | View flag | Expected employee count visible |
|---|---|---|
| Administrator | — | 10 (all) |
| HR Manager (any user with that role on a non-Employee user, e.g. fresh System Manager) | — | 10 (all) |
| CEO (`ceo@erpdemo.local`) | 1 | 6 (self + 5 direct reports: CFO, HR-001, SAL-001, OPS-001, MKT-001) |
| CFO (`cfo@erpdemo.local`) | 1 | 1 (self; no reports) |
| HR-001 (`hrhead@erpdemo.local`) | 1 | 2 (self + HR-002) |
| HR-002 (`hrmanager@erpdemo.local`) | 1 | 1 (self; no reports) |
| SAL-001 (`salesmanager@erpdemo.local`) | 1 | 2 (self + SAL-002) |
| SAL-002 (`salesexec@erpdemo.local`) | 0 | 1 (self only) |
| OPS-001 (`opsmanager@erpdemo.local`) | 1 | 2 (self + OPS-002) |
| OPS-002 (`opsexec@erpdemo.local`) | 0 | 1 (self only) |
| MKT-001 (`marketingmanager@erpdemo.local`) | 1 | 2 (self + MKT-002) |
| MKT-002 (`marketingexec@erpdemo.local`) | 0 | 1 (self only) |

> Note: HR-002 has the `HR Manager` role in the demo seed; logging in as HR-002 via Desk will show all 10 because role beats Employee link. Numbers above assume the role grant is removed for the test (or test as a non-HR-Manager user with the same Employee link).

Server-side approval gates ([`atbhr/approval_gate.py`](../atbhr/approval_gate.py) / `myhr/approval_gate.py`) enforce **who can approve** independently of Employee visibility — `custom_allow_view_reporting=1` does *not* let a manager approve someone else's leave; the gate still requires they be the named `leave_approver`.

Cross-references: [`LEAVE_AND_ATTENDANCE.md` F-LA-AR-1](LEAVE_AND_ATTENDANCE.md#f-la-ar-1) (the original CUP-based fix) and the F-LA-AR-1 follow-up note describing this rollout.

**Wipe behaviour**

`reset_and_seed` deletes any stale `User Permission` rows tied to demo employees (and any Company UPs the controller created on demo users) **before** deleting the Employee rows. This is required because Frappe's linked-doc check otherwise blocks the Employee delete. The new model doesn't insert User Permission rows so the count should be 0 after a fresh seed.

---

## How to seed

### v15 — fresh seed

```bash
bench --site dev.localhost execute atbhr.scripts.seed_v15.run
bench --site dev.localhost execute atbhr.scripts.seed_policies.run
```

### v15 — wipe and reseed

```bash
bench --site dev.localhost execute atbhr.scripts.seed_v15.reset_and_seed
```

This deletes the 10 demo employees + their PAs/EACs/Directory/Leave Allocations + the 5 demo HR Policies + Leave Period 2026 + Optional Holiday Leave type, then runs `run()` and `seed_policies.run()`.

### v16 — fresh seed

```bash
bench --site erp.localhost execute myhr.setup_dummies.run
```

### v16 — wipe and reseed

```bash
bench --site erp.localhost execute myhr.setup_dummies.reset_and_seed
```

---

## What state you should see after seeding

```
Active Employees: 10
Active HR Policies: 5
PAs (Acknowledged): 50
PAs (Pending): 0
Employee Action Centres: 10
Employee Directory rows: 9   # CEO has custom_emp_directory=0
Leave Allocations submitted: 10
Employees with custom_allow_view_reporting=1: 7   # CEO, CFO, HR-001, HR-002, SAL-001, OPS-001, MKT-001
Employees with create_user_permission=1: 0       # CUP retired by the new visibility model
User Permissions on Employee: 0                   # the new model doesn't use User Permission rows
Holidays in Holidays 2026: depends on the Holiday List rows on the site
```

(EAC count assumes the `custom_add_to_action_centre=1` flag on every employee triggers exactly one EAC per insert, which is the documented `employee_hooks.py` behaviour. Directory count is 9 because the CEO row has `custom_emp_directory=0`. The 7/3 split on `custom_allow_view_reporting` matches the manager / executive split in the org chart — see [Employee Visibility Policy](#employee-visibility-policy) above.)
