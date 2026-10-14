# myhr — Developer Handover

> Single doc to onboard a new developer onto the `myhr` Frappe + HRMS customisation app. Read this first; then drill into the per-feature spec docs in this `docs/` folder.

Last refreshed: 2026-05-18.

---

## 1. What this app is

`myhr` is a **custom Frappe app that customises ERPNext + HRMS** for Elixiir Foods. It is the vendor-delivered replacement for HR scope that used to live in the `elixiir` app (HR was dropped from `elixiir` on 2026-04-29 — workspace ADR-005).

Scope owned by this app:
- All Employee customisations (custom fields, write lockdown, master data)
- HR Policy framework (HR Policy DocType + Policy Acknowledgement + audit log)
- Employee Action Centre (onboarding-style flow with policy + declarations + payslip toggles)
- Employee Directory (PWA-facing roster)
- Employee Checkin (geo-radius gate, auto-present cron, EOD checkout cron)
- Leave Application (approver gate, optional-leave validation, ownership gate)
- Attendance Request (approver gate, list-tab parity)
- Expense Claim (single-expense rule, remarks field, cancel flow, approver gating)
- Holiday list (custom types: Optional / Fixed / Weekly Off)
- HRMS PWA frontend overlay (Vue source files in `frontend_changes/` synced into HRMS's PWA build)
- The daily "Missing IN Checkin Reminder" job

Out of scope: anything ERP-side (Gate Entry, MR, PO, GRN, Returns, Replenishment) — that's `elixiir`.

Owner: Sameer Yadav (sameer.yadav@infinitelocus.com).

---

## 2. Tech + environments

| Thing | Value |
|---|---|
| Framework | Frappe v16 + HRMS (overlaid PWA) |
| Python | 3.14 |
| Frontend | Vue 3 SFCs under `myhr/frontend_changes/` synced into `apps/hrms/frontend/src/` |
| Local dev site | `elixiir.localhost` (dev container `devcontainer-example-frappe-1`) |
| Staging site | `staging.elixiirfoods.com` |
| Prod site | `elixiirfoods.com` |
| Default git branch | `main` (production) |
| Integration branch | `staging` (deploys to staging.elixiirfoods.com) |
| Repo URL | `Infinite-Locus-Product/custom_hrms` (the local folder name is `myhr/`) |

### Branching workflow

```
feat/<short-desc>  ──► PR into staging  ──► verify on staging  ──► promotion PR staging → main
fix/<short-desc>   ──► PR into staging  ──► same
hotfix/<short-desc> ──► cut from main ──► PR into staging (still reaches prod via staging)
```

**GitHub default branch is `main`.** When opening a feature / bugfix / hotfix PR you must **override the target to `staging`**. The promotion PR is the only PR that targets `main`.

As of 2026-05-18 there are ~9 merge commits + their feature commits sitting on `staging` that are NOT yet on `main`. A promotion PR is queued.

---

## 3. Hard rules — never break these

1. **Don't modify core apps.** `apps/frappe`, `apps/erpnext`, `apps/hrms`, `apps/crm` are read-only. All customisations live here in `apps/myhr` (or sibling apps if applicable).
2. **HRMS PWA changes go through the overlay.** Edit files in `myhr/frontend_changes/` and run `bench --site <site> execute myhr.frontend_sync.apply_custom_ui` to copy them into `apps/hrms/frontend/src/` and rebuild. **Never edit the synced copies directly** — they get overwritten on next sync.
3. **`frontend_overlay/` is dead.** Files in that directory are NOT synced. Anything that needs to ship to the PWA must live in `frontend_changes/` AND be listed in `frontend_sync.files_to_sync`.
4. **Don't bypass the Policy Audit Log.** All `Policy Acknowledgement.status` transitions must go through `myhr.policy_audit.transition_pa_via_sql` (for SQL paths) or the controller's `validate` hook (for ORM paths). Raw `frappe.db.sql UPDATE` on PA without the helper is a regression.
5. **Server-stamped audit fields are immutable post-set.** `custom_approved_by`, `custom_approved_on`, `submitted_by`, `submitted_on`, `acknowledged_at`, `ip_address`. The validate hooks throw if you try to overwrite them. To bypass for sanctioned reopen flows, set the documented `frappe.flags.allow_*` flag.
6. **Never `git push` without explicit user confirmation per push.**

---

## 4. Repo layout

```
myhr/
├── myhr/                          # Python package
│   ├── hooks.py                   # app entry + scheduler crons + doc events
│   ├── setup.py                   # after_install + after_migrate + MYHR_CUSTOM_FIELDS list
│   ├── api.py                     # whitelisted endpoints (cancel_*, can_approve_*, save_action_centre_draft, etc.)
│   ├── employee_hooks.py          # Employee validate / on_update / Auto-Present cron entry
│   ├── policy_hooks.py            # HR Policy + Policy Acknowledgement events
│   ├── policy_audit.py            # canonical PA transition surface (writes Policy Audit Log)
│   ├── policy_notifications.py    # PWA-bound notifications for policy changes
│   ├── policy_gate.py             # mandatory-ack gate (used by Action Centre + dashboards)
│   ├── approval_gate.py           # approval authority gate for LA + AR
│   ├── ownership_gate.py          # ownership gate for Checkin + AR
│   ├── leave_optional_holiday.py  # optional-leave date validator
│   ├── missing_in_reminder.py     # daily 11:00 IN-reminder cron + Missing Checkin Reminder Log
│   ├── attendance_eod_checkout.py # daily 23:55 EOD checkout cron (added 2026-05-13)
│   ├── overrides/                 # stock HRMS overrides
│   │   ├── employee_checkin.py    # geo-radius + auto-present + Reserved device IDs
│   │   ├── leave_application.py
│   │   ├── expense_claim.py       # single-expense enforcement (2026-05-15)
│   │   ├── holiday_list_assignment.py
│   │   └── salary_slip.py
│   ├── frontend_sync.py           # files_to_sync list + apply_custom_ui entrypoint
│   ├── frontend_changes/          # Vue source — App.vue + components/ + views/ + router/ + data/
│   ├── frontend_overlay/          # DEAD — do not edit
│   ├── patches/                   # ~30 migration patches, see patches.txt for ordering
│   ├── myhr/doctype/              # custom DocTypes (see §6)
│   └── tests/                     # myhr-side test suite
└── docs/                          # specs, PRDs, this doc
```

---

## 5. Day-to-day code-change loops

### 5.1 Backend change (Python / hooks / patches)

```bash
bench --site <site> migrate
```

That's it. Migrate runs patches + reloads the app. Patches in `patches.txt` are idempotent.

### 5.2 Frontend change (Vue / PWA)

```bash
# Edit files under myhr/frontend_changes/
bench --site <site> execute myhr.frontend_sync.apply_custom_ui
```

This copies the edited files into `apps/hrms/frontend/src/` and runs `yarn build`. To skip the build step (e.g., during fast iteration) set `MYHR_SKIP_FRONTEND_SYNC=1` before `bench migrate`, then run `apply_custom_ui` manually when ready.

### 5.3 Verify a single patch ran

```bash
bench --site <site> console
>>> import frappe
>>> frappe.db.exists("Patch Log", {"patch": "myhr.patches.v1_8_repair_custom_field_flags"})
```

### 5.4 Smoke test

After every install / before every PR: run the 4-step smoke test in `README.md` §5. Always pass before opening a PR.

---

## 6. Custom DocTypes myhr owns

| DocType | Type | Purpose |
|---|---|---|
| `HR Policy` | Submittable | Versioned policy document; targets via 5 child filter doctypes (Department / Designation / Branch / Employment Type / Employee). Inactivating policies fans out withdrawals to pending acks. |
| `Policy Filter Department/Designation/Branch/Employment Type/Employee` | Child tables on `HR Policy` | Audience targeting rules. |
| `Policy Acknowledgement` | Submittable | Per-employee, per-policy-version ack record. Status: Open / Pending / Acknowledged / Withdrawn. Has a `(policy, employee, version)` unique index added by patch v1_3. |
| `Policy Audit Log` | Submittable, append-only | Every PA status transition writes here with old_status / new_status / actor / reason / timestamp. |
| `Employee Action Centre` | Normal (one per Employee, auto-created on Employee insert when `custom_add_to_action_centre`=1) | Multi-section onboarding shell: declarations, payslip toggles, master-data fields, etc. Has `custom_last_saved_at` for "Draft saved" vs "Start your details" home-card label. |
| `Action Centre Activity` | Child of `Employee Action Centre` | Per-activity row; tracks completion state + `custom_posted_on`. |
| `Employee Directory` | Normal | PWA-facing roster row, one per Employee with `custom_emp_directory`=1. Backfilled by patch v1_0. |
| `Missing Checkin Reminder Log` | Normal | Append-only audit log for the 11:00 IN-reminder cron (one row per (employee, reminder_date)). HR Manager read-only. |

---

## 7. Custom fields myhr adds

Declared in `setup.py:MYHR_CUSTOM_FIELDS`. Honoured attribute names listed in `_CUSTOM_FIELD_PASSTHROUGH_ATTRS` at the top of `setup.py` — add to that list if you need a non-standard attr.

| DocType | Field | Why |
|---|---|---|
| `Employee` | `custom_employee_id` | Business Employee ID forced into `Employee.name` |
| `Employee` | `custom_hr_controls_tab` | Anchors the HR Controls tab |
| `Employee` | `custom_emp_directory` | Show in PWA Employee Directory? |
| `Employee` | `custom_add_to_action_centre` | Auto-create Employee Action Centre on insert? |
| `Employee` | `custom_auto_present` | Cron auto-checkin? (Requires `default_shift` + `enable_auto_attendance=1`; validated on save) |
| `Employee` | `custom_bypass_geolocation_check` | Skip geo radius (lat/long still required) |
| `Holiday` | `custom_holiday_type` | Optional / Fixed / Weekly Off (drives optional-leave gating) |
| `Leave Application` | `custom_approved_by` | Server-stamped Link → User on Open → Approved transition |
| `Leave Application` | `custom_approved_on` | Server-stamped Datetime on the same transition |
| `Employee Action Centre` | `custom_last_saved_at` | Server-stamped Datetime on every Save Draft API call; NULL = never saved |
| `Expense Claim Detail` | `custom_remarks` | Long Text per-line remarks (added 2026-05-13) |
| `Expense Claim` | `expense_approver_name` | Data, `fetch_from=expense_approver.full_name`, hidden. **Unprefixed** because the entire PWA references it that way — renaming would touch every claim surface. Documented in setup.py + this doc. |
| `Shift Type` | `custom_auto_checkout_at_eod` | Enables the 23:55 EOD-checkout cron for shifts opting in (added 2026-05-13) |
| `Employee` | `custom_send_checkin_reminder` | Per-employee opt-out (Check, default 1) for the 11:00 Missing IN reminder cron. Anchored in HR Controls tab. (Added 2026-05-19) |
| `HR Settings` | `custom_enable_checkin_reminder` | Global site-wide kill-switch (Check, default 1) for the 11:00 Missing IN reminder cron. Anchored in Reminders section. (Added 2026-05-19) |

**Rule:** if you change a flag on an existing Custom Field, clone the `v1_8_repair_custom_field_flags` patch pattern to repair installed sites (`_ensure_custom_fields` skips if exists).

---

## 8. Custom API endpoints (`api.py`)

All `@frappe.whitelist()`, auto-loaded — no extra registration. Notable ones:

| Endpoint | Caller | What |
|---|---|---|
| `save_action_centre_draft(name, payload)` | PWA | Partial-state save for Employee Action Centre. Bypasses `validate`. Employee-only (writes to `custom_last_saved_at`). |
| `cancel_expense_claim(name, reason=None)` | PWA | Owner-only cancel while `docstatus=0` AND `approval_status='Draft'`. Deletes the row. Approver notified via PWA Notification. Mirrors AR (Attendance Request) cancel pattern. |
| `can_approve_expense_claim(name)` | PWA | Mirrors the server `gate_expense_claim_approval` for the UI. Returns `{allowed: bool, reason?: str}`. |

HR-only endpoint pattern:

```python
@frappe.whitelist()
def my_endpoint():
    roles = set(frappe.get_roles())
    if not ({"HR Manager", "System Manager"} & roles):
        frappe.throw("HR-only.", frappe.PermissionError)
    # ...
```

---

## 9. Key flows + gates

### 9.1 Policy Acknowledgement state machine
```
       insert (HR Policy submit)            ack (employee from PWA)
Open ──────────────────────────► Pending ──────────────────────────► Acknowledged
  ▲                                  │
  │           policy.is_active=0     │
  └──────────────────────── Withdrawn (mass)
```
All transitions route through `policy_audit.transition_pa_via_sql` or the controller's `validate`. Both write a `Policy Audit Log` row.

### 9.2 Approval-authority gate (Leave Application + Attendance Request)
`approval_gate.gate_leave_approval(la_name)` and the AR counterpart. Resolves the approver chain from Employee → `leave_approver` (LA) / `attendance_request_approver` (AR), enforces "self-approval blocked" (configurable), and "approver must be Active". Backs the PWA's grey-out logic and is enforced server-side on submit.

### 9.3 Ownership gate (Employee Checkin + Attendance Request)
`ownership_gate.*` enforces "an employee can only Checkin for themselves" and "AR cancel/edit only by owner". Stops admin spoofing without explicit `flags.allow_*`.

### 9.4 Expense Claim — single expense + cancel + self-approval
- `overrides/expense_claim._enforce_single_expense_row` throws if `len(self.expenses) > 1`. PWA hides the `+ add expense` button after the first row.
- Self-approval is blocked when `prevent_self_expense_approval` is set on Employee or HR Settings. The PWA replaces Approve/Reject with an amber notice; server enforces in `gate_expense_claim_approval`.
- Cancel: see `cancel_expense_claim` in §8. Deletes the row pre-submit (no Cancelled state for drafts — matches AR pattern). Trade-off accepted: no per-claim audit trail of the cancellation (only the approver's PWA Notification persists).

### 9.5 Auto-Present cron (Employee Checkin)
Daily cron iterates Active employees with `custom_auto_present=1`, **skips weekends** (`weekday() >= 5` short-circuits), inserts a synthetic IN Checkin with `device_id="myHR Auto"`. The `device_id="myHR Auto"` value is reserved — only Administrator + HR Manager + System Manager can write it; validated in `overrides/employee_checkin.py`.

**Prereqs validated on Employee save** (`_validate_auto_present_prereqs`): ticking `custom_auto_present` throws unless the employee has a `default_shift` (or active Shift Assignment for today) AND that shift has `enable_auto_attendance=1`. Closes the silent-failure path where Auto Present looked on but no Attendance was ever marked.

### 9.6 EOD checkout cron (added 2026-05-13, post-race-fix 2026-05-15)
Cron `"55 23 * * *"` → `myhr.attendance_eod_checkout.auto_checkout_at_eod`. For Shift Types with `custom_auto_checkout_at_eod=1`:
1. For each Active employee on that shift, check if the day is "closed" (out_time set OR `count(OUT) >= count(IN)`)
2. If closed → skip
3. If not closed → insert a 23:59 OUT Checkin AND directly insert/update an Attendance row (HRMS's hourly sweep can't pair Checkins outside the shift window, so we own the Attendance directly)
4. Skip branches: holiday, approved leave, day already complete

Race-fix detail (2026-05-15): HRMS's hourly `process_auto_attendance` can run during the day and create an Attendance row with `out_time=NULL` when `working_hours_threshold_for_absent=0`. The original guard "Attendance exists → skip" was wrong. New guard: "day already **closed** → skip". When Attendance exists without out_time, EOD cron now inserts OUT and `db_set`s the existing row's `out_time` + `working_hours` + promotes status to Present (only when prior status was Absent / Half Day / Present — On Leave / Work From Home are not overwritten).

Backfill recipe:
```bash
bench --site <s> execute myhr.attendance_eod_checkout.auto_checkout_at_eod \
  --kwargs '{"on_date": "2026-05-14"}'
```

### 9.7 Missing IN Checkin Reminder (daily 11:00)
Cron `"0 11 * * *"` (site TZ) → `myhr.missing_in_reminder.send_missing_in_reminders`.

**Two opt-out toggles** (both default ticked, added 2026-05-19 — FRES-548 follow-up):
- **Global:** `HR Settings.custom_enable_checkin_reminder`. When unticked, the cron logs one info line and returns — zero log rows, zero emails.
- **Per-employee:** `Employee.custom_send_checkin_reminder`. When unticked for an employee, that row is logged as `Skipped` with `skip_reason='opt_out'`.

Filter chain per employee (short-circuiting): dedup → opt_out → holiday → leave (Approved + Open, incl half-day) → IN-Checkin before cutoff → email-resolve → send.

Template: Email Template named `Missing IN Checkin Reminder` (renaming it breaks the job — must exist on the site).
Log: `Missing Checkin Reminder Log` (HR Manager read-only).
Dedup: `SELECT` on `(employee, reminder_date, status='Sent')`.

Disable: comment out the cron entry in `hooks.py` OR delete the Email Template (job aborts with a single error log).

Backfill:
```bash
bench --site <s> execute myhr.missing_in_reminder.send_missing_in_reminders \
  --kwargs '{"on_date": "YYYY-MM-DD"}'
```

### 9.8 Optional-leave validation
`leave_optional_holiday.validate_optional_leave_dates`. Stock HRMS rejects optional leave on holiday dates unless `Leave Type.include_holiday=1` AND `Leave Period.optional_holiday_list` is set. myhr filters within those.

### 9.9 PWA Cancel-flow uniformity
`RequestActionSheet.vue`'s `CANCELLABLE_DOCTYPES` + `cancelMethods` maps each doctype to its server cancel endpoint. As of 2026-05-15: AR, Leave Application, Expense Claim all routed; reason textarea is hidden for EC (`cancelRequiresReason` computed) since server treats `reason` as optional for EC and defaults to "Cancelled by employee.".

### 9.10 List-row action sheet (PWA)
`ListView.vue::openActionSheet(link)`: tapping a row in the View All page for any non-Checkin doctype opens the `RequestActionSheet` modal (same as the home dashboard tile tap) instead of routing to the per-doctype DetailView. Approvers get Approve/Reject + Attachments at the list-row tap surface. DetailView routes still work for direct URL deep-links.

### 9.11 Attendance Request List — Team tab fix (2026-05-16)
Stock HRMS's `AttendanceRequestList.vue` omitted `:tabButtons` while LA / EC / Shift Request pass them, so the ListView's `defaultFilters` hard-coded `employee == current_employee` with no flip. Fixed by an overlay file in `frontend_changes/views/attendance/AttendanceRequestList.vue` that passes `TAB_BUTTONS = ["My Requests", "Team Requests"]`. Registered in `frontend_sync.files_to_sync`.

---

## 10. Patches (`patches/`, registered in `patches.txt`)

All run under `[post_model_sync]`. Naming: `v1_<N>_<short_desc>.py`. Notable ones:

| # | Patch | What |
|---|---|---|
| v1_0 | `backfill_employee_directory` | Inserts Employee Directory rows for existing employees |
| v1_1 | `remove_hr_approver` | Drops the legacy `hr_approver` Employee field |
| v1_1 | `split_policy_acknowledgement` | One-time PA model split |
| v1_2 | `hr_controls_tab` | Adds the HR Controls tab anchor on Employee |
| v1_3 | `dedupe_pa_and_add_unique_index` | Dedupes Policy Acknowledgement + adds `(policy, employee, version)` unique idx |
| v1_4 | `drop_policy_action_task` | Removes a deprecated child DocType |
| v1_5 | `withdraw_pending_on_inactive_policies` | Mass-withdraws Pending PAs whose HR Policy is now inactive |
| v1_6 | `dedupe_eac_and_add_unique_index` | Dedupes Employee Action Centre + adds unique idx |
| v1_7 | `fix_holiday_type_for_weekly_off` | Backfills `custom_holiday_type` on existing Holidays |
| v1_8 | `repair_custom_field_flags` | Reference pattern for repairing Custom Field flag changes on installed sites |
| v1_9–v1_22 | Various | Tab placement repairs, AR approval tab move, Action Centre seeding for declarations / payslip / personal-details / medical-insurance, drop reqd flags on elixiir master fields, etc. |
| v1_27 | `add_expense_claim_remarks` | Adds `Expense Claim Detail.custom_remarks` + `Expense Claim.expense_approver_name` (2026-05-13) |
| v1_28 | `add_shift_type_eod_checkout` | Adds `Shift Type.custom_auto_checkout_at_eod` (2026-05-13) |
| v1_29 | `drop_lpte_orphans` | Removes 20 Custom Fields + 2 DocTypes + 1 PS + 4 dead Patch Log entries left over from the LP+T&E revert (2026-05-15) |
| v1_30 | `seed_missing_in_reminder_log` | Seeds Missing Checkin Reminder Log DocType (2026-05-18) |

Diagnostic probes (NOT in `patches.txt`, run on demand via `bench execute`):
- `probe_staging_self_approval.py` — walks the gate's branches for a given employee
- `probe_staging_radius_enforcement.py` — walks the five silent-return branches in stock `validate_distance_from_shift_location`
- `probe_eod_checkout_skip.py` — walks the five skip causes for a given IN Checkin row

**Adding a new patch:**
1. Create `myhr/patches/v1_X_<short_desc>.py`
2. Make it idempotent (existence checks; `add_unique` for indices; safe SQL guards)
3. `print()` a summary line so the migrate log captures the outcome
4. Register in `myhr/patches.txt` under `[post_model_sync]`
5. Run `bench --site <site> migrate` to apply

See `docs/SETUP_AND_PATCHES.md` §6 for full conventions.

---

## 11. Known operational quirks

- **`LinkValidationError: pm@erp.localhost` halts migrate.** Pre-existing TicketNext `after_migrate` issue, NOT myhr. Patches land before the halt; verify via `Patch Log`.
- **Stock HRMS rejects optional leave on holiday dates** unless `Leave Type.include_holiday=1` AND `Leave Period.optional_holiday_list` is set. myhr's `validate_optional_leave_dates` filters within those.
- **Auto-Present cron skips weekends** — by design (`weekday() >= 5` short-circuits).
- **`device_id="myHR Auto"` is reserved.** Only Administrator + HR Manager + System Manager can set it. Validates in `overrides/employee_checkin.py`.
- **`expense_approver_name` is unprefixed** (no `custom_`). Documented in setup.py.
- **Service worker on the PWA caches aggressively.** A `router.go(0)` re-mounts the route but doesn't bust the SW cache. Use the new ⟳ refresh button (added 2026-05-15, top of `BaseLayout.vue`) which calls `window.location.reload()` for a hard reload.
- **CTC field on Salary Slip ≠ CTC on Employee.** HRMS design — Salary Slip's `ctc` is snapshotted differently. myhr overrides via `set_ctc_snapshot` on main. Documented in `reference_hrms_salary_slip_ctc.md` (memory).

---

## 12. v15 vs v16 — what to watch

The app was tested on v16. If you're on v15, four surfaces have risk:
1. `hrms.api.get_attendance_requests` may not exist
2. `HRMSLeaveApplication.validate()` / `HRMSEmployeeCheckin.validate_distance_from_shift_location()` parent methods may differ
3. HRMS frontend overlay paths in `frontend_sync.files_to_sync`
4. `Leave Period.optional_holiday_list` field

See `README.md` §1.1 + `docs/HANDOFF_V16_TO_V15.md` for the bring-up playbook. Run the smoke test after install — failures will point at one of these.

---

## 13. Where to look for context

| Need | Path |
|---|---|
| Current app state + branching | `myhr/CLAUDE.md` |
| Project-level architecture | `../CLAUDE.md` (workspace root) |
| Recent session work | `../docs/worklog.md` (newest entry first) |
| Per-feature specs | `myhr/docs/*.md` (see §13.1) |
| Setup + patch conventions | `docs/SETUP_AND_PATCHES.md` |
| Smoke test | `README.md` §5 |

### 13.1 Per-feature spec docs (read before changing the feature)

| Feature | Spec |
|---|---|
| Employee Directory | `docs/EMPLOYEE_DIRECTORY.md` |
| Employee Action Centre | `docs/EMPLOYEE_ACTION_CENTRE.md` + `docs/EMPLOYEE_ACTION_CENTRE_LOGIC.md` |
| Employee Checkin | `docs/EMPLOYEE_CHECKIN.md` |
| Leave & Attendance | `docs/LEAVE_AND_ATTENDANCE.md` |
| Leave Policy Auto-Assign | `docs/LEAVE_POLICY_AUTO_ASSIGN.md` |
| HR Policy + Policy Ack | `docs/HR_POLICY.md` |
| Holiday + Optional Leave | `docs/HOLIDAY.md` |
| Setup + Patches | `docs/SETUP_AND_PATCHES.md` |
| Employee Permissions | `docs/EMPLOYEE_PERMISSIONS.md` |
| Travel & Expense PRD (LP+T&E was reverted but PRD is reference) | `docs/Elixiir_Travel_Expense_PRD_v2.docx` |
| myhr ↔ elixiir overlap | `docs/ELIXIIR_MYHR_INTEGRATION.md` + `docs/ELIXIIR_VS_MYHR.md` |
| **v15 bring-up handoff** | `docs/HANDOFF_V16_TO_V15.md` (read first if a v15 dev is installing this) |

When you change a feature, update its spec doc's findings table at the same time. Pattern:
- New code-level finding → `<SURFACE>-N` row (e.g., `LA-7`, `CHK-6`)
- New feature gap → `E-<SURFACE>-N`
- Resolved → mark `**RESOLVED <date>**` with verification evidence (live test result or commit ref)

---

## 14. First-day checklist for a new dev

1. Clone `Infinite-Locus-Product/custom_hrms` into the workspace folder as `myhr/`
2. Read `../CLAUDE.md`, then this doc, then `myhr/CLAUDE.md`
3. Read the last 2-3 entries of `../docs/worklog.md` — the 2026-05-13→18 arc covers the most recent work
4. Skim spec docs for the features you'll touch (§13.1)
5. Install the app on the dev site:
   ```bash
   bench get-app myhr <repo-url>
   bench --site elixiir.localhost install-app myhr
   bench --site elixiir.localhost migrate
   bench --site elixiir.localhost execute myhr.frontend_sync.apply_custom_ui
   ```
   Build the PWA with a 4 GB Node heap if it OOMs:
   ```bash
   cd apps/hrms/frontend && NODE_OPTIONS="--max_old_space_size=4096" yarn build
   ```
6. Run the smoke test (README.md §5)
7. Open the HRMS PWA, log in as a test employee, walk through: Action Centre home card, file an Expense Claim (note single-expense + remarks), file a Leave Application, file an Attendance Request, see the Team Requests tab populated for an approver
8. Pick a small ticket from the open-items list in `../docs/worklog.md` and follow the §5 code-change loop end-to-end
9. Open a feature PR — remember to target `staging`, not `main`
