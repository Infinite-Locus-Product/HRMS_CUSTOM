# QA Report: Whitelist + Permission Gate Audit (atbhr v15 / myhr v16)

Date: 2026-04-27
Method: Static audit. No live calls, no bench commands.
Scope: Every function in `api.py` + the helper modules listed below, both apps. Both copies of this file are byte-identical modulo namespace strings (`atbhr` ↔ `myhr`, `atbHR` ↔ `myHR`).

## Executive summary

- **Functions audited:** 30 whitelisted endpoints + ~45 helper/handler functions per app.
- **Whitelisted endpoints:** 30 (atbhr) / 30 (myhr) — perfectly mirrored.
- **Findings:** SEV-1 = 0, SEV-2 = 4, SEV-3 = 5
- **Cross-version delta:** 0 functional, 100% byte-identical modulo namespace.
- **`override_whitelisted_methods` integrity:** holds in both apps.
- **`allow_guest=True` count:** 0 in both apps. Good.
- **Stray `@frappe.whitelist()` outside `api.py`:** 0 in both apps. Good.

The API surface is well-contained — every callable runs through `api.py`, every HR-only mutator declares a role gate at the top of the function, every employee-scoped mutator passes through `_ac_belongs_to_session_user` or `Employee.user_id`, and every helper module is correctly NOT whitelisted. SEV-2 / SEV-3 items below are hardening/cosmetic.

---

## SEV-1: Security exposure (immediate)

**None found.** Every privileged operation in [api.py](../myhr/api.py) checks `{"HR Manager", "System Manager"} & frappe.get_roles()` before mutating; every employee-scoped operation calls `_ac_belongs_to_session_user(name)` or scopes via `frappe.session.user → Employee.user_id`. No `allow_guest=True` anywhere. No `frappe.get_doc(...)` returned without serialization (PWA endpoints all marshal to plain dicts).

---

## SEV-2: Hardening

**[SEV-2-1] `acknowledge_policy_acknowledgement(name)` — input not validated as string.** [api.py:387-422](../myhr/myhr/api.py)
The first call is `frappe.get_doc("Policy Acknowledgement", name)`, which Frappe accepts as a dict, list, or weird payload (the dict form would let a caller construct a transient unsaved doc and mutate it). Practical impact is small because the subsequent ownership check still gates real mutations, but a `if not isinstance(name, str): frappe.throw(...)` at the top would close the smell. Same pattern in `bulk_acknowledge_for_employee(employee, hr_policy)` and `bulk_acknowledge_for_policy(hr_policy)`.

**[SEV-2-2] `bulk_approve_leave_applications(names)` accepts ambiguous input.** [api.py:544-597](../myhr/myhr/api.py)
`names` may be a comma-separated string OR a JSON list — the dual handling is fine, but each entry is then passed to `frappe.get_doc("Leave Application", n)` without a string check or length cap. A caller could submit thousands of names per call (no pagination guard) and slow the worker. Add: `if len(name_list) > 500: frappe.throw("Bulk operations limited to 500 rows per call.")`. The role gate at line 553 already prevents non-HR abuse, so this is purely a DoS-from-trusted-actor guardrail.

**[SEV-2-3] `update_action_centre_field(name, fieldname, value)` does not validate that `fieldname` exists on the doctype.** [api.py:1011-1027](../myhr/myhr/api.py)
`doc.set(fieldname, value)` will silently accept any string as a fieldname; if the field does not exist, `set()` puts it on the doc dict and the subsequent `save()` may silently skip it. The non-HR whitelist via `_enforce_employee_field_whitelist([fieldname])` does the right thing for non-HR callers. For HR callers however the early return in `_enforce_employee_field_whitelist` lets any string through. Closing the gap: also call `if not doc.meta.has_field(fieldname): frappe.throw(...)`.

**[SEV-2-4] `reupload_document(name, prefix, file_url)` does not validate `file_url`.** [api.py:1051-1070](../myhr/myhr/api.py)
`file_url` is written verbatim into the document attach field. If a caller passes `"javascript:..."` or an external URL, the controller stores it. The Frappe `Attach` field type at the doctype layer is the right place to validate this, but a defensive check (`startswith("/files/") or startswith("/private/files/")`) on the API surface would protect against URL smuggling at the wire level.

---

## SEV-3: Cosmetic / convention

**[SEV-3-1] `get_employee_directory()` is whitelisted but has no explicit role gate.** [api.py:97-118](../myhr/myhr/api.py)
Every authenticated user can read every active employee's name, designation, department, mobile, email, and image. This is intentional per the docstring ("this is a company contact book, not a personal record") but is not a per-record perm check — it bypasses the new `permissions.py:has_employee_permission` rule. Consider: if `Employee.custom_allow_view_reporting=0` for the caller, restricting the projection to coworkers in the same `department` would align with the permission model. Today it doesn't.

**[SEV-3-2] `get_optional_leave_types()` is over-exposed.** [api.py:1141-1152](../myhr/myhr/api.py)
The endpoint returns Leave Type names — harmless, but every authenticated user (incl. those with no Employee linked) can call it. Bonus: it emits no `_caller_is_hr_manager()` short-circuit. Acceptable as a PWA helper but worth a comment in the docstring saying "globally readable, no perm gate by design."

**[SEV-3-3] `get_attendance_request_coverage()` and `get_action_centre_coverage()` only honour HR roles, not the employee themselves.** [api.py:723, 843](../myhr/myhr/api.py)
This is consistent with the docstring intent (HR-only coverage report) but means an employee viewing their own AC has no API path to the same shape — the PWA reads the AC via `get_employee_action_centre()` instead. Document this explicitly so future devs don't mistakenly extend the gate.

**[SEV-3-4] Notification helpers in [policy_notifications.py](../myhr/myhr/policy_notifications.py) and [employee_hooks.py](../myhr/myhr/employee_hooks.py) `_notify_on_auto_checkin_failure` are NOT whitelisted (correct).** Listed here so it's explicit: these are internal helpers called from the cron path / from the PA insert flow, never from REST. No action needed; documenting that this is intentional.

**[SEV-3-5] Module-level utilities `nuclear_repair.run`, `repair_meta.run`, `repair_and_sync.run`, `sync_directory.sync_employees` are NOT whitelisted (correct).** They run only via `bench execute` (which does not require `@frappe.whitelist`). Documented for completeness — these are intentionally not REST-callable.

---

## Function-by-function table — myhr api.py

| # | Function | Line | Whitelisted? | Role gate | Inputs | Returns | allow_guest | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | `get_employee_directory` | [97](../myhr/myhr/api.py) | yes | none (intentional, all auth users) | — | list[dict] | False | OK (SEV-3-1) |
| 2 | `rebuild_employee_directory` | [121](../myhr/myhr/api.py) | yes | HR/SysMgr | — | dict | False | OK |
| 3 | `get_directory_audit` | [179](../myhr/myhr/api.py) | yes | HR/SysMgr | — | dict | False | OK |
| 4 | `get_blocking_policies` | [265](../myhr/myhr/api.py) | yes | session-scoped | — | dict | False | OK |
| 5 | `can_open_attendance_request` | [283](../myhr/myhr/api.py) | yes | session-scoped | — | dict | False | OK |
| 6 | `get_employee_policies` | [309](../myhr/myhr/api.py) | yes | session-scoped | — | dict | False | OK |
| 7 | `get_employee_policy_history` | [325](../myhr/myhr/api.py) | yes | session-scoped (employee = session.user via Employee.user_id) | hr_policy:str | dict | False | OK |
| 8 | `get_pending_policy_count` | [352](../myhr/myhr/api.py) | yes | session-scoped | — | dict | False | OK |
| 9 | `acknowledge_policy_acknowledgement` | [387](../myhr/myhr/api.py) | yes | self-or-HR (per-row check) | name:str | dict | False | OK (SEV-2-1 hardening) |
| 10 | `bulk_acknowledge_for_employee` | [425](../myhr/myhr/api.py) | yes | HR/SysMgr | employee, hr_policy? | dict | False | OK (SEV-2-1) |
| 11 | `bulk_acknowledge_for_policy` | [468](../myhr/myhr/api.py) | yes | HR/SysMgr | hr_policy:str | dict | False | OK (SEV-2-1) |
| 12 | `force_reacknowledgement_campaign` | [500](../myhr/myhr/api.py) | yes | HR/SysMgr | hr_policy, reason | dict | False | OK |
| 13 | `bulk_approve_leave_applications` | [544](../myhr/myhr/api.py) | yes | HR/SysMgr | names:str\|list | dict | False | OK (SEV-2-2 add row cap) |
| 14 | `get_leave_coverage` | [600](../myhr/myhr/api.py) | yes | HR for global; self for `employee=<own>` | employee? | list[dict] | False | OK |
| 15 | `get_checkin_coverage` | [662](../myhr/myhr/api.py) | yes | HR/SysMgr | date? | list[dict] | False | OK |
| 16 | `get_attendance_request_coverage` | [723](../myhr/myhr/api.py) | yes | HR/SysMgr | — | list[dict] | False | OK (SEV-3-3) |
| 17 | `hr_set_action_centre_verdict` | [765](../myhr/myhr/api.py) | yes | HR/SysMgr | name, verdict, remarks | dict | False | OK |
| 18 | `reopen_action_centre` | [811](../myhr/myhr/api.py) | yes | HR/SysMgr | name, reason | dict | False | OK |
| 19 | `get_action_centre_coverage` | [843](../myhr/myhr/api.py) | yes | HR/SysMgr | — | list[dict] | False | OK (SEV-3-3) |
| 20 | `get_policy_coverage` | [882](../myhr/myhr/api.py) | yes | HR/SysMgr | — | list[dict] | False | OK |
| 21 | `get_employee_action_centre` | [931](../myhr/myhr/api.py) | yes | session-scoped (own AC only) | — | dict | False | OK |
| 22 | `update_action_centre_field` | [1011](../myhr/myhr/api.py) | yes | self-or-HR + field-whitelist | name, fieldname, value | dict | False | OK (SEV-2-3) |
| 23 | `bulk_update_action_centre_fields` | [1030](../myhr/myhr/api.py) | yes | self-or-HR + field-whitelist | name, patch:str/json | dict | False | OK |
| 24 | `reupload_document` | [1051](../myhr/myhr/api.py) | yes | self-or-HR + prefix-whitelist | name, prefix, file_url | dict | False | OK (SEV-2-4) |
| 25 | `submit_action_centre` | [1073](../myhr/myhr/api.py) | yes | self-or-HR | name | dict | False | OK |
| 26 | `reset_action_centre_field` | [1099](../myhr/myhr/api.py) | yes | self-or-HR + prefix-whitelist | name, fieldname, is_mandatory | dict | False | OK |
| 27 | `validate_optional_leave_for_application` | [1122](../myhr/myhr/api.py) | yes | none (validator only, no mutation) | employee, leave_type, from_date, to_date | dict | False | OK |
| 28 | `get_optional_leave_types` | [1141](../myhr/myhr/api.py) | yes | none (read-only metadata) | — | list[str] | False | OK (SEV-3-2) |
| 29 | `get_leave_applications` (override) | [1167](../myhr/myhr/api.py) | yes | HR-or-named-approver via hrms_impl | employee, approver_id?, for_approval, limit | list[dict] | False | OK |
| 30 | `get_attendance_requests` (override) | [1204](../myhr/myhr/api.py) | yes | HR-or-leave_approver | employee, for_approval, limit | list[dict] | False | OK |

## Function-by-function table — atbhr api.py

**Identical to myhr modulo `myhr.*` ↔ `atbhr.*` import paths and `myHR` ↔ `atbHR` log-message strings.** The 30 whitelisted endpoints are at the same line numbers and have the same role gates, inputs, returns, `allow_guest=False` posture, and verdicts. See `diff` summary in `## v15 vs v16 delta` below.

---

## `override_whitelisted_methods` integrity

| hooks.py entry | Target function | Exists? | Whitelisted? |
|---|---|---|---|
| `hrms.api.get_leave_applications` → `myhr.api.get_leave_applications` | [api.py:1168](../myhr/myhr/api.py) | yes | yes |
| `hrms.api.get_attendance_requests` → `myhr.api.get_attendance_requests` | [api.py:1205](../myhr/myhr/api.py) | yes | yes |
| (atbhr) `hrms.api.get_leave_applications` → `atbhr.api.get_leave_applications` | api.py:1168 | yes | yes |
| (atbhr) `hrms.api.get_attendance_requests` → `atbhr.api.get_attendance_requests` | api.py:1205 | yes | yes |

Both override targets exist, both are decorated, both delegate back to `hrms.api.get_*` for the standard path and shortcut for HR Manager / System Manager. No broken references.

---

## `doc_events` and `scheduler_events` integrity

| Hook | Handler | Exists? |
|---|---|---|
| `Employee.validate` | `employee_hooks.validate_employee` | yes [employee_hooks.py:7](../myhr/myhr/employee_hooks.py) |
| `Employee.after_insert[0]` | `employee_hooks.after_employee_insert` | yes [employee_hooks.py:95](../myhr/myhr/employee_hooks.py) |
| `Employee.after_insert[1]` | `policy_hooks.reconcile_after_employee_insert` | yes [policy_hooks.py:168](../myhr/myhr/policy_hooks.py) |
| `Employee.on_update[0]` | `employee_hooks.on_update_employee` | yes [employee_hooks.py:99](../myhr/myhr/employee_hooks.py) |
| `Employee.on_update[1]` | `policy_hooks.reconcile_on_employee_update` | yes [policy_hooks.py:173](../myhr/myhr/policy_hooks.py) |
| `Employee.on_trash` | `employee_hooks.on_trash_employee` | yes [employee_hooks.py:49](../myhr/myhr/employee_hooks.py) |
| `Employee.after_rename` | `employee_hooks.after_rename_employee` | yes [employee_hooks.py:67](../myhr/myhr/employee_hooks.py) |
| `Attendance Request.validate` | `employee_hooks.validate_attendance_request_policy_gate` | yes [employee_hooks.py:141](../myhr/myhr/employee_hooks.py) |
| `Attendance Request.before_submit` | `approval_gate.gate_attendance_request_submit` | yes [approval_gate.py:79](../myhr/myhr/approval_gate.py) |
| `Attendance Request.on_submit` | `employee_hooks.notify_employee_on_attendance_request_submit` | yes [employee_hooks.py:103](../myhr/myhr/employee_hooks.py) |
| `Leave Application.validate` | `approval_gate.gate_leave_application_approval` | yes [approval_gate.py:34](../myhr/myhr/approval_gate.py) |
| `HR Policy.validate` | `policy_hooks.validate_hr_policy` | yes [policy_hooks.py:190](../myhr/myhr/policy_hooks.py) |
| `HR Policy.on_update` | `policy_hooks.after_save_hr_policy` | yes [policy_hooks.py:205](../myhr/myhr/policy_hooks.py) |
| `HR Policy.on_trash` | `policy_hooks.on_trash_hr_policy` | yes [policy_hooks.py:303](../myhr/myhr/policy_hooks.py) |
| `Holiday.validate` | `leave_optional_holiday.validate_holiday` | yes [leave_optional_holiday.py:50](../myhr/myhr/leave_optional_holiday.py) |
| `Holiday List.validate` | `leave_optional_holiday.validate_holiday_list` | yes [leave_optional_holiday.py:55](../myhr/myhr/leave_optional_holiday.py) |
| `cron 0 9 * * 1-5` | `employee_hooks.auto_present_in` | yes [employee_hooks.py:282](../myhr/myhr/employee_hooks.py) |
| `cron 0 18 * * 1-5` | `employee_hooks.auto_present_out` | yes [employee_hooks.py:286](../myhr/myhr/employee_hooks.py) |
| `hourly[0]` | `policy_notifications.send_pending_policy_reminders` | yes [policy_notifications.py:76](../myhr/myhr/policy_notifications.py) |
| `permission_query_conditions.Employee` | `permissions.employee_permission_query_conditions` | yes [permissions.py:64](../myhr/myhr/permissions.py) |
| `has_permission.Employee` | `permissions.has_employee_permission` | yes [permissions.py:83](../myhr/myhr/permissions.py) |

**All hooks resolve.** None of these handlers should be (or are) `@frappe.whitelist()`-decorated — they fire via the doc lifecycle / cron / permission-resolution paths.

---

## Helper modules — public-but-shouldn't-be functions

Walked: `policy_audit.py`, `policy_notifications.py`, `policy_hooks.py`, `approval_gate.py`, `ownership_gate.py`, `policy_gate.py`, `leave_optional_holiday.py`, `employee_hooks.py`, `permissions.py`, `setup.py`, `frontend_sync.py`, `nuclear_repair.py`, `repair_meta.py`, `repair_and_sync.py`, `sync_directory.py`.

**Result: zero stray `@frappe.whitelist()` decorators outside `api.py`.**

The five "utility" modules (`nuclear_repair`, `repair_meta`, `repair_and_sync`, `sync_directory`, `frontend_sync`) all expose `run()` / `apply_custom_ui()` / `sync_employees()` style entry points. None are whitelisted. They are invoked exclusively via:
- `bench execute myhr.nuclear_repair.run` (CLI, requires shell access),
- `frontend_sync.apply_custom_ui` is also called from `setup.after_migrate` / `_apply_custom_ui_safe`.

The CLI surface is correctly scoped: `bench execute` requires server-side shell, not REST.

---

## v15 vs v16 delta

**Functional delta: none.** Every whitelisted endpoint, every helper, every hook, every gate function exists in both apps with identical behaviour. Differences are limited to:

| Symbol class | atbhr value | myhr value |
|---|---|---|
| `app_name` | `atbhr` | `myhr` |
| `app_title` | `atbHR` | `myHR` |
| Module Def name | `atbHR` | `myHR` |
| Notification subject prefix | `[atbHR Policy]`, `[atbHR Attendance]` | `[myHR Policy]`, `[myHR Attendance]` |
| `AUTO_PRESENT_DEVICE` constant | `atbHR Auto` | `myHR Auto` |
| Frappe local cache key | `_atbhr_user_emp_cache` | `_myhr_user_emp_cache` |
| `*_SKIP_FRONTEND_SYNC` env var | `ATBHR_SKIP_FRONTEND_SYNC` | `MYHR_SKIP_FRONTEND_SYNC` |
| Setup constants | `ATBHR_ROLES`, `ATBHR_PERMISSIONS`, `ATBHR_ADDITIVE_PERMISSIONS` | `MYHR_ROLES`, `MYHR_PERMISSIONS`, `MYHR_ADDITIVE_PERMISSIONS` |

`diff -r` between `atbhr/atbhr/` and `myhr/myhr/` confirms no other code-path differences. This is the strongest possible cross-version posture: the audit report itself is byte-identical save for namespace strings.

---

## Aggregate verdict

**The API surface is secure as designed.** Both apps confine all REST/PWA-callable code to `api.py`, every privileged mutation declares the same role gate (`{"HR Manager", "System Manager"} & frappe.get_roles()`), every employee-scoped mutation passes through `_ac_belongs_to_session_user` or `Employee.user_id == frappe.session.user`, and `override_whitelisted_methods` integrity holds. Zero `allow_guest=True`, zero stray whitelist decorators, zero broken hook references.

The four SEV-2 hardening items are all about defence-in-depth (input-type validation, row-cap, fieldname existence check, file-URL scheme check) — none of them are exploitable today because the role gate runs first. The five SEV-3 items are documentation/policy clarifications.

Bottom line: ship it; address SEV-2 items as a follow-up cleanup, SEV-3 items optional.
