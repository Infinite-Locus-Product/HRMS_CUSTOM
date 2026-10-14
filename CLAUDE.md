# myHR — Claude Code context

Drop this in front of Claude any time you're working on `apps/myhr`. It captures the rules, key files, and common operations a contributor needs without re-reading every spec doc.

---

## Branching

- `main`    — production. Deployed to production.
- `staging` — integration. Deployed to `staging.elixiirfoods.com`.

### Workflow

- Feature work:  `feat/<short-desc>` → PR into `staging`
- Bugfix work:   `fix/<short-desc>` → PR into `staging`
- Promotion:     `staging` → `main` via a "promotion PR" once verified on staging
- Hotfix:        cut from `main` as `hotfix/<short-desc>` → PR into `staging`
  (everything reaches prod via staging — no direct main commits)

### Default PR target

GitHub default branch is `main`. **Override the PR target to `staging` when opening feature / bugfix / hotfix PRs.** The promotion PR is the only PR that targets `main`.

---

## Hard rules — never break these

1. **Don't modify core apps.** `apps/frappe`, `apps/erpnext`, `apps/hrms`, `apps/crm` are read-only. All customizations live in `apps/myhr` (or sibling apps if applicable).
2. **HRMS PWA changes go through the overlay.** Edit files in `myhr/frontend_changes/` and run `bench --site <site> execute myhr.frontend_sync.apply_custom_ui` to copy them into `apps/hrms/frontend/src/` and rebuild. Never edit the synced copies directly — they get overwritten.
3. **The `frontend_overlay/` directory is dead** — files there are NOT synced. Anything that needs to ship to the PWA must be in `frontend_changes/` AND listed in `frontend_sync.files_to_sync`.
4. **Don't bypass the audit log.** When you write code that changes `Policy Acknowledgement.status`, route it through `myhr.policy_audit.transition_pa_via_sql` (for SQL paths) or rely on the controller's `validate` for ORM paths — both write to `Policy Audit Log`. Raw `frappe.db.sql UPDATE` on PA without the helper is a regression.
5. **Server-stamped audit fields are immutable post-set.** `custom_approved_by`, `custom_approved_on`, `submitted_by`, `submitted_on`, `acknowledged_at`, `ip_address`. The validate hooks throw if you try to overwrite them. To bypass for sanctioned reopen flows, set the documented `frappe.flags.allow_*` flag.

---

## Architecture map

| Concern | File |
|---|---|
| App entry / hooks | [`myhr/hooks.py`](myhr/hooks.py) |
| Setup (after_install + after_migrate) | [`myhr/setup.py`](myhr/setup.py) |
| Migration patches | [`myhr/patches/`](myhr/patches/) + [`myhr/patches.txt`](myhr/patches.txt) |
| Whitelisted API endpoints | [`myhr/api.py`](myhr/api.py) — includes `save_action_centre_draft(name, payload)` (partial-state save for Employee Action Centre, bypasses validate, employee-only) |
| Employee event handlers | [`myhr/employee_hooks.py`](myhr/employee_hooks.py) |
| Job Applicant / Job Opening hooks (public application form) | [`myhr/job_applicant_hooks.py`](myhr/job_applicant_hooks.py), [`myhr/job_opening_hooks.py`](myhr/job_opening_hooks.py) |
| Job Offer CTC totals | [`myhr/job_offer_hooks.py`](myhr/job_offer_hooks.py) |
| Letter assets (logo, CEO signature) | [`myhr/public/images/`](myhr/public/images/) |
| Offer / Appointment letter print templates (paste sources, NOT installed) | [`templates/`](templates/) — the live Print Formats are created by hand in Desk; see [`docs/STAGING_SETUP_RECRUITMENT.md`](docs/STAGING_SETUP_RECRUITMENT.md) |
| Public Job Application web form (`/apply`) | [`myhr/myhr/web_form/fixxly_job_application/`](myhr/myhr/web_form/fixxly_job_application/) |
| Policy doctype hooks | [`myhr/policy_hooks.py`](myhr/policy_hooks.py) |
| Canonical PA transition surface (audit log writer) | [`myhr/policy_audit.py`](myhr/policy_audit.py) |
| Notification helpers | [`myhr/policy_notifications.py`](myhr/policy_notifications.py) |
| Optional-leave date validator | [`myhr/leave_optional_holiday.py`](myhr/leave_optional_holiday.py) |
| Approval-authority gate (LA + AR) | [`myhr/approval_gate.py`](myhr/approval_gate.py) |
| Ownership gates (Checkin + AR) | [`myhr/ownership_gate.py`](myhr/ownership_gate.py) |
| Policy gate (mandatory ack check) | [`myhr/policy_gate.py`](myhr/policy_gate.py) |
| Stock HRMS overrides (LA + Checkin) | [`myhr/overrides/`](myhr/overrides/) |
| HRMS frontend overlay sync | [`myhr/frontend_sync.py`](myhr/frontend_sync.py) |
| PWA Vue source files | [`myhr/frontend_changes/`](myhr/frontend_changes/) |

---

## Doctypes myHR owns

- `HR Policy` + child filter doctypes (`Policy Filter Department / Designation / Branch / Employment Type / Employee`)
- `Policy Acknowledgement`
- `Policy Audit Log` (append-only)
- `Employee Action Centre` + `Action Centre Activity` (child)
- `Job Opening Question` (child of Job Opening) + `Job Applicant Question Response` (child of Job Applicant)
- `Job Offer Salary Component` (child of Job Offer, used by both CTC tables)
- `Employee Directory`
- `Missing Checkin Reminder Log` (audit log for daily 11:00 IN-reminder cron)

---

## Custom Fields myHR adds (declared in `setup.py:MYHR_CUSTOM_FIELDS`)

| DocType | Field | Why |
|---|---|---|
| Employee | `custom_employee_id` | Business Employee ID forced into `Employee.name` |
| Employee | `custom_hr_controls_tab` | Anchors the HR Controls tab |
| Employee | `custom_emp_directory` | Show in PWA directory? |
| Employee | `custom_add_to_action_centre` | Auto-create AC on insert? |
| Employee | `custom_auto_present` | Cron auto-checkin? |
| Employee | `custom_bypass_geolocation_check` | Skip geo radius (lat/long still required) |
| Holiday | `custom_holiday_type` | Optional / Fixed / Weekly Off |
| Leave Application | `custom_approved_by` | Server-stamped Link User on Open → Approved |
| Leave Application | `custom_approved_on` | Server-stamped Datetime on the same transition |
| Employee Action Centre | `custom_last_saved_at` | Server-stamped Datetime on every Save Draft API call; NULL = never saved (drives 'Start your details' vs 'Draft saved' label on home card) |
| Employee | `custom_taxable_earnings_till_date` | Opening taxable earnings for the current payroll period (permlevel 1). Seeded onto every new SSA by `salary_structure_assignment_hooks.fill_opening_balances_from_employee`; edits push to the active SSA via `employee_master_data.sync_opening_balances_to_assignment` |
| Employee | `custom_tax_deducted_till_date` | Opening TDS for the same period (permlevel 1). Seeded and synced the same way |
| Employee | `custom_send_checkin_reminder` | Per-employee opt-out (Check, default 1) for the 11:00 Missing IN Checkin Reminder cron |
| HR Settings | `custom_enable_checkin_reminder` | Global kill-switch (Check, default 1) for the 11:00 Missing IN Checkin Reminder cron |

**Exception — Job Applicant, Job Opening, Job Offer, Appointment Letter, Skill and Interview Feedback.** Their Custom Fields live in [`myhr/fixtures/custom_field.json`](myhr/fixtures/custom_field.json), not `setup.py`, and are loaded via the `fixtures` hook: the eight applicant data fields (`custom_gender`, `custom_date_of_birth`, `custom_age`, `custom_passport_size_photo`, `custom_total_years_of_experience`, `custom_employee_location`, `custom_current_address`, `custom_permanent_address`, `custom_department`, `custom_father_name`), plus a Screening Questions tab + Table on each doctype (`custom_screening_questions` on Job Opening, `custom_screening_responses` on Job Applicant). They back the public Job Application web form at `/apply` — see [`docs/JOB_APPLICATION_FORM.md`](docs/JOB_APPLICATION_FORM.md). Job Offer carries a Compensation tab (two `custom_ctc_*` Tables + computed summary fields) — see [`docs/JOB_OFFER_CTC.md`](docs/JOB_OFFER_CTC.md). Appointment Letter gets `custom_job_offer` (Link, filtered/preselected by `public/js/appointment_letter.js`) and `custom_applicant_email` (Data/Email fetched from the applicant — a Notification recipient can only read fields on its own document, so without it the only option is `owner`).

If you change any flag here, **clone the v1_8 patch pattern** to repair existing rows — `_ensure_custom_fields` is skip-if-exists.

---

## Common operations

### Make a code change → ship it

```bash
# Backend / Python / hooks / patches
bench --site <site> migrate

# Vue / PWA changes (after editing files in myhr/frontend_changes/)
bench --site <site> execute myhr.frontend_sync.apply_custom_ui
# OR set MYHR_SKIP_FRONTEND_SYNC=1 to skip yarn build during migrate, then run apply_custom_ui by hand.

# Verify a single patch ran
bench --site <site> console
>>> import frappe
>>> frappe.db.exists("Patch Log", {"patch": "myhr.patches.v1_8_repair_custom_field_flags"})
```

### Add a new patch

1. Create `myhr/patches/v1_X_<short_desc>.py`
2. Make it idempotent (check existence before insert; use `add_unique` for indices; safe SQL guards)
3. `print()` a summary line so the migrate log captures the outcome
4. Register in `myhr/patches.txt` under `[post_model_sync]`
5. Run `bench --site <site> migrate` to apply

See [`docs/SETUP_AND_PATCHES.md`](docs/SETUP_AND_PATCHES.md) §6 for full conventions.

### Add a new Custom Field

1. Append a dict to `MYHR_CUSTOM_FIELDS` in `setup.py`
2. Honoured attrs are listed in `_CUSTOM_FIELD_PASSTHROUGH_ATTRS` (top of `setup.py`). If you need an attr outside this list, add it there.
3. `bench migrate` creates the field on first run.
4. **If you ever change a flag on an existing field**, clone `myhr/patches/v1_8_repair_custom_field_flags.py` to repair it on installed sites.

### Add a new HR-only API endpoint

```python
@frappe.whitelist()
def my_endpoint():
    roles = set(frappe.get_roles())
    if not ({"HR Manager", "System Manager"} & roles):
        frappe.throw("HR-only.", frappe.PermissionError)
    # ... implementation ...
```

Whitelisted endpoints in `myhr/api.py` are auto-loaded; no extra registration needed.

### Run the smoke test (after every install / before every PR)

See [`README.md`](README.md) §5 for the 4-step smoke test.

### Missing IN Check-in Reminder — admin ops

Cron: `0 11 * * *` (site TZ) → `myhr.missing_in_reminder.send_missing_in_reminders`
Template: Email Template `Missing IN Checkin Reminder` (rename breaks the job — must exist on the site)
Log: `Missing Checkin Reminder Log` (HR Manager read-only)
Dedup: `SELECT` on `(employee, reminder_date, status='Sent')`

Global kill-switch: `HR Settings.custom_enable_checkin_reminder` (default ticked). When unticked, the cron logs an info line and returns — zero log rows written.

Per-employee opt-out: `Employee.custom_send_checkin_reminder` (default ticked). Unticked → row logged as `Skipped` with `skip_reason='opt_out'`.

Filter chain (per employee, short-circuiting): dedup → opt_out → holiday → leave (Approved + Open, incl half-day) → IN-Checkin before cutoff → email-resolve → send.

Disable:
- Comment out the `"0 11 * * *"` entry in `hooks.py` `scheduler_events.cron`, OR
- Delete the Email Template (job aborts with a single error log).

Backfill a past day:
```bash
bench --site <s> execute myhr.missing_in_reminder.send_missing_in_reminders \
  --kwargs '{"on_date": "YYYY-MM-DD"}'
```

Inspect a day's run:
```bash
bench --site <s> mariadb -e "SELECT employee, status, skip_reason, sent_at
  FROM \`tabMissing Checkin Reminder Log\` WHERE reminder_date='YYYY-MM-DD'"
```

Spec + plan: [`docs/superpowers/specs/2026-05-18-missing-in-checkin-reminder-design.md`](docs/superpowers/specs/2026-05-18-missing-in-checkin-reminder-design.md), [`docs/superpowers/plans/2026-05-18-missing-in-checkin-reminder.md`](docs/superpowers/plans/2026-05-18-missing-in-checkin-reminder.md).

---

## Spec docs (read these before changing the corresponding feature)

| Feature | Spec |
|---|---|
| Employee Directory | [`docs/EMPLOYEE_DIRECTORY.md`](docs/EMPLOYEE_DIRECTORY.md) |
| Employee Action Centre | [`docs/EMPLOYEE_ACTION_CENTRE.md`](docs/EMPLOYEE_ACTION_CENTRE.md) |
| Job Application form + screening questions | [`docs/JOB_APPLICATION_FORM.md`](docs/JOB_APPLICATION_FORM.md) |
| Job Offer CTC breakdown | [`docs/JOB_OFFER_CTC.md`](docs/JOB_OFFER_CTC.md) |
| Staging manual configuration (recruitment) | [`docs/STAGING_SETUP_RECRUITMENT.md`](docs/STAGING_SETUP_RECRUITMENT.md) |
| Employee Checkin | [`docs/EMPLOYEE_CHECKIN.md`](docs/EMPLOYEE_CHECKIN.md) |
| Leave & Attendance | [`docs/LEAVE_AND_ATTENDANCE.md`](docs/LEAVE_AND_ATTENDANCE.md) |
| HR Policy + Policy Acknowledgement | [`docs/HR_POLICY.md`](docs/HR_POLICY.md) |
| Holiday + Optional Leave | [`docs/HOLIDAY.md`](docs/HOLIDAY.md) |
| Setup + Patches infrastructure | [`docs/SETUP_AND_PATCHES.md`](docs/SETUP_AND_PATCHES.md) |
| Offboarding / employee separation | [`docs/OFFBOARDING_TESTING_GUIDE.md`](docs/OFFBOARDING_TESTING_GUIDE.md) — end-to-end test script, roles matrix, preflight |
| **v15 bring-up handoff** | [`docs/HANDOFF_V16_TO_V15.md`](docs/HANDOFF_V16_TO_V15.md) — read first if a v15 dev is installing this |

When you change a feature, update its spec doc's findings table at the same time. The patterns:
- New code-level finding → `<SURFACE>-N` row in the findings table (e.g., `LA-7`, `CHK-6`)
- New feature gap → `E-<SURFACE>-N` if the surface uses that pattern
- Resolved → mark `**RESOLVED <date>**` with verification evidence (live test result or commit ref)

---

## v15 vs v16 — what to watch

The app was tested on v16. If you're on v15, four surfaces have risk:
1. `hrms.api.get_attendance_requests` may not exist
2. `HRMSLeaveApplication.validate()` / `HRMSEmployeeCheckin.validate_distance_from_shift_location()` parent methods may differ
3. HRMS frontend overlay paths in `frontend_sync.files_to_sync`
4. `Leave Period.optional_holiday_list` field

See [`README.md`](README.md) §1.1 for details. Run the smoke test after install — failures will point at one of these.

---

## Known operational quirks

- **`LinkValidationError: pm@erp.localhost` halts migrate** — pre-existing TicketNext after_migrate issue, not myHR. Patches land before the halt; verify via `Patch Log`.
- **Stock HRMS rejects optional leave on holiday dates** unless `Leave Type.include_holiday=1` AND `Leave Period.optional_holiday_list` is set. myHR's `validate_optional_leave_dates` filters within those.
- **Auto-present cron skips weekends** (`weekday() >= 5` short-circuits) — by design.
- **`device_id="myHR Auto"` is reserved** — only Administrator + HR Manager + System Manager can set it. Validates in [`employee_checkin.py`](myhr/overrides/employee_checkin.py).
