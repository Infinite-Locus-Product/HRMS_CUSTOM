# myHR

Custom HRMS extension for ERPNext / Frappe v16. Adds an employee-facing PWA
onboarding hub (Employee Action Centre), policy acknowledgement compliance
gate, employee directory, single-stage leave / attendance / expense approval
flows, geo-aware check-in, master-data + payroll automation (auto SSA + auto
HLA on Employee), Medical Insurance Opt-Out workflow, and a configurable
Action Centre via HR Settings.

For detailed feature specs, see [`docs/`](docs/) — start with
[`CLAUDE.md`](CLAUDE.md) for the architecture map.

---

## 1. Compatibility

| Dependency | Tested on | Declared in `pyproject.toml` |
|---|---|---|
| **Frappe** | 16.15.0 | `>=15.0.0,<16.0.0` (manifest lags reality — see §1.1) |
| **ERPNext** | 16.14.0 | `>=15.0.0,<16.0.0` |
| **HRMS** | 16.5.0 | `>=15.0.0,<16.0.0` |
| Python | 3.10+ | declared |
| Node + Yarn | required on host for the PWA build step | not declared (system tool) |

### 1.1 v15 vs v16 — known risk surfaces

This app was developed and verified on Frappe / ERPNext / HRMS **v16**. It has
**not been tested on v15** in this current state. If you're targeting v15,
read [`docs/HANDOFF_V16_TO_V15.md`](docs/HANDOFF_V16_TO_V15.md) first — it
lists the four surfaces (HRMS API method names, override-class super calls,
frontend file paths, Leave Period field shape) that may need recipe-style
fixes.

---

## 2. Install (fresh site)

Prerequisite: `yarn` must be on the host's PATH so the PWA build step
succeeds. Verify with `yarn --version` before proceeding.

```bash
cd ~/frappe-bench

# 1. Pull the app onto the bench
bench get-app myhr <repo-url-or-tar>

# 2. Install on the target site
bench --site <your-site> install-app myhr
```

`install-app` triggers `after_install`, which calls
[`myhr.setup._setup()`](myhr/setup.py) and ends with
[`myhr.frontend_sync.apply_custom_ui`](myhr/frontend_sync.py) — so a fresh
install also rebuilds the HRMS frontend bundle. **No separate migrate is
needed for a fresh install.**

What `_setup()` does on every fresh install + every migrate (see §3):

1. Creates `HR Manager`, `HR User`, `Employee` roles if missing.
2. Sets canonical permissions on `Employee Directory`.
3. Adds `Leave Approver` perm row on `Attendance Request` (additive).
4. Pins `Leave Application.status` options to `Open / Approved / Rejected / Cancelled`.
5. Creates ~100 Custom Fields across Employee, Holiday, Leave Application,
   Attendance Request, Expense Claim, HR Settings, and Employee Action Centre
   (declared in `MYHR_CUSTOM_FIELDS`, idempotent / skip-if-exists).
6. Applies HR-only permlevel locking on 13 sensitive Employee fields
   (`ctc`, `salutation`, `designation`, `department`, `reports_to`,
   `employment_type`, `grade`, `company_email`, `custom_notice_period_days`,
   `custom_salary_structure`, `custom_total_experience_years`,
   `custom_employee_location`, `custom_holiday_list`).
7. Hides the native Employee "Joining" tab + 8 native bank/holiday-list
   fields via Property Setter (Elixiir master-data merge — bank fields are
   surfaced on a custom Bank tab and synced server-side).
8. Seeds default values for the 6 HR-Settings AR / EC / Action Centre
   payslip toggles.
9. Repairs the Action Centre payslip Show/Require Custom-Field attrs
   (idempotent re-anchor + `read_only_depends_on`).
10. Locks down `Employee` writes — strips write/create/delete from non-HR
    roles at permlevel 0.
11. Runs all post-model-sync patches (v1_0 .. v1_21) — see
    [`docs/SETUP_AND_PATCHES.md`](docs/SETUP_AND_PATCHES.md).
12. Calls `apply_custom_ui` — copies the Vue overlay into
    `apps/hrms/frontend/src/`, runs `yarn build`, refreshes the service
    worker.

---

## 3. Migrate (existing site upgrade) — REQUIRED to see PWA changes

```bash
bench --site <your-site> migrate
```

**Migrate is required after every backend code change** for the PWA to
reflect those changes. The flow:

1. Frappe schema sync materialises any new / changed Custom Fields.
2. Post-model-sync patches run (v1_0 .. v1_21).
3. `after_migrate` hook fires →
   [`myhr.setup.after_migrate`](myhr/setup.py) →
   `_setup()` (re-applies steps 1-11 from §2 for drift correction)
   → `_apply_custom_ui_safe()` →
   [`myhr.frontend_sync.apply_custom_ui`](myhr/frontend_sync.py) →
   copies Vue overlay into HRMS frontend → runs `yarn build` →
   regenerates the service worker.

The `after_migrate` hook is wired in [`hooks.py`](myhr/hooks.py):

```python
after_install = "myhr.setup.after_install"
after_migrate = "myhr.setup.after_migrate"
```

`after_migrate` is non-fatal — if `yarn build` fails (e.g. on a CI host
without node), the migrate still completes. Always verify the bundle
afterwards (§5).

### 3.1 Common migrate flags

```bash
# Skip the yarn build step (CI / containers without node)
MYHR_SKIP_FRONTEND_SYNC=1 bench --site <your-site> migrate
```

When you do this, run `apply_custom_ui` separately on a host that has yarn:

```bash
bench --site <your-site> execute myhr.frontend_sync.apply_custom_ui
```

---

## 4. PWA frontend overlay — **how to see your changes in the PWA**

Every backend change that affects the PWA (new field on Action Centre, new
Vue section, new HR Settings toggle that gates a row, etc.) needs the
overlay rebuilt before the employee sees it. **Three ways to trigger it:**

| Trigger | When |
|---|---|
| `bench --site <s> migrate` | Standard path. `after_migrate` runs the sync. |
| `bench --site <s> execute myhr.frontend_sync.apply_custom_ui` | Standalone — when migrate isn't needed but you tweaked a Vue file. |
| `bench --site <s> install-app myhr` | First-time install only. |

What `apply_custom_ui` does:

1. Copies every file listed in `frontend_sync.files_to_sync` (in
   [`frontend_sync.py`](myhr/frontend_sync.py)) from
   `apps/myhr/myhr/frontend_changes/` → `apps/hrms/frontend/src/`.
2. Runs `yarn build` inside `apps/hrms/frontend/` — produces a fresh
   bundle in `apps/hrms/hrms/public/frontend/assets/`.
3. Copies the generated `index.html` → `apps/hrms/www/hrms.html` so the
   web route serves the new bundle.
4. Regenerates the service worker (`sw.js`) so PWA installs pick up
   updates on next launch.

After it succeeds, **hard-refresh the browser** (Cmd+Shift+R / Ctrl+F5)
to bypass the service-worker cache.

> **Note**: `frontend_overlay/` (different directory) is NOT synced —
> files there are dead unless explicitly added to
> `files_to_sync` in [`frontend_sync.py`](myhr/frontend_sync.py).

### 4.1 Verify the overlay actually deployed

After install / migrate, confirm the bundle has your changes:

```bash
# The HRMS source tree should contain myHR's overlay markers
grep -c "myhr.api\|Action Centre\|Policy Centre" \
    apps/hrms/frontend/src/views/Home.vue
# Expected: ≥ 5. Zero means the sync didn't run (or `bench update` of hrms
# overwrote it — re-run apply_custom_ui).

# The built bundle should contain those markers too
grep -l "Action Centre" \
    apps/hrms/hrms/public/frontend/assets/Home-*.js
# Expected: at least one matching file. None = stale bundle.
```

If either returns 0, run `apply_custom_ui` and hard-refresh.

### 4.2 After `bench update` of `apps/hrms`

`bench update` overwrites the synced files in `apps/hrms/frontend/src/`.
You **must** re-run `apply_custom_ui` after every `bench update` of
`apps/hrms` or the PWA reverts to stock HRMS UI. The `after_migrate`
hook handles this if you run `bench --site <s> migrate` afterwards.

---

## 5. Smoke test (run this after install / migrate)

```bash
bench --site <your-site> console
```

```python
import frappe

# 1. All patches landed (v1_0 .. v1_21 — 23 entries)
patches = [p.patch for p in frappe.get_all(
    "Patch Log",
    filters={"patch": ("like", "myhr.%")},
    fields=["patch"],
    order_by="creation",
)]
print(f"Patch count: {len(patches)}")
print(patches[-3:])  # last 3
# Expected: ≥ 23 patches; last entries include v1_19, v1_20, v1_21.

# 2. Roles + Employee Directory perms
print(frappe.db.exists("Role", "HR Manager"),
      frappe.db.exists("Role", "HR User"),
      frappe.db.exists("Role", "Employee"))
# Expected: name name name

# 3. Custom Fields representative spot-check
for f in (
    "Employee-custom_employee_id",
    "Employee-custom_salary_structure",
    "Employee-custom_pan_attachment",
    "Employee Action Centre-tax_regime",
    "Employee Action Centre-medical_insurance_signed_optout",
    "Employee Action Centre-personal_full_name",
    "Employee Action Centre-bank_name",
    "HR Settings-custom_ac_show_payslip_last_month",
    "HR Settings-custom_ac_require_payslip_last_month",
):
    print(f, "->", bool(frappe.db.exists("Custom Field", f)))
# Expected: every one True

# 4. Master-data hook resolution + chain ordering
hooks = frappe.get_hooks("doc_events", {}).get("Employee", {})
print(hooks.get("validate"))
# Expected: list with 'myhr.employee_master_data.validate_master_data'
# BEFORE 'myhr.employee_hooks.validate_employee'

# 5. doctype_js wired
print(frappe.get_hooks("doctype_js").get("Employee"))
# Expected: list containing 'public/js/employee.js'

# 6. HR Settings AC payslip toggles seeded
for f in (
    "custom_ac_show_payslip_last_month",
    "custom_ac_require_payslip_last_month",
    "custom_ac_show_payslip_last_to_last_month",
    "custom_ac_require_payslip_last_to_last_month",
    "custom_ac_show_payslip_month_before_that",
    "custom_ac_require_payslip_month_before_that",
):
    print(f, "->", frappe.db.get_single_value("HR Settings", f))
# Expected: every one 1

# 7. Auxiliary doctypes exist
for dt in (
    "Employee Action Centre",
    "Employee Directory",
    "HR Policy",
    "Policy Acknowledgement",
    "Policy Audit Log",
    "Elixiir Child",
    "Medical Insurance",
    "Medical Insurance Opt Out Declaration",
):
    print(dt, "->", bool(frappe.db.exists("DocType", dt)))
# Expected: every one True
```

If any check fails, see [`docs/SETUP_AND_PATCHES.md`](docs/SETUP_AND_PATCHES.md).

---

## 6. Manual verification — PWA flow

1. Open `<site>/hrms` in a browser, log in as an employee whose Employee
   record has `custom_add_to_action_centre = 1` (the default).
2. Tap **Action Centre** from the home screen.
3. You should see seven sections, in order:
   1. **Personal Details** (Full Name, DOB, Age auto-computed, Gender
      dropdown with indigo popover, Marital Status, Mobile, Blood Group,
      Father's / Mother's Names, Emergency Contact Name + Number)
   2. **Identity Documents** (Aadhar / PAN / Education — each with both a
      number/text field AND an Attach upload)
   3. **Declarations** (Tax Regime — indigo button group, Medical Insurance
      Opt In / Opt Out — Opt Out shows the HR-uploaded blank declaration
      template + an Upload Signed Declaration button, Bank Statement Last
      6 Months file upload)
   4. **Statutory & Bank** (PF, UAN, Bank Name, Account Number, IFSC)
   5. **Most Recent Employer** (Employment Period dates + Offer Letter,
      Increment Letter, 3 Pay Slips, Relieving Letter)
   6. **Previous Employers** (slots 2-5)
   7. **Activity Log**
4. The **Submit** button at the bottom is enabled only when every mandatory
   row is filled (or marked Not Applicable).
5. As HR Manager on Desk, open the same Action Centre — every employee-data
   field is **read-only** (you can see but not edit). Only HR Status +
   HR Remarks fields are writable.

### 6.1 Configure the Action Centre payslip rows from HR Settings

1. Open `<site>/app/hr-settings`. Switch to the **Action Centre** tab.
2. For each of the three payslips you'll see two checkboxes:
   - **Show Pay Slip — ... in PWA** (default ticked)
   - **Require Pay Slip — ...** (default ticked)
3. Untick **Show in PWA** for any payslip → that row disappears from the
   employee's PWA AND its Require checkbox auto-disables (a hidden row
   cannot be mandatory).
4. Untick **Require** but keep **Show** ticked → the row still renders in
   the PWA but as `OPTIONAL` instead of `REQUIRED`; the employee can
   submit without uploading it.
5. Save HR Settings and hard-refresh the PWA — the row count and
   pill labels update immediately (no rebuild needed; the API payload
   reads HR Settings on every request).

---

## 7. Known operational quirks

- **Migrate may halt on `LinkValidationError: pm@erp.localhost`** — this is
  a TicketNext (different app) `after_migrate` hook on the demo site. **Our
  setup runs before the halt** and patches land cleanly. Verify via the
  Patch Log smoke test above.
- **Yarn build is non-fatal during migrate** — if it fails (e.g. yarn not
  on PATH), migrate completes but the PWA bundle may be stale. Run
  `apply_custom_ui` separately on a host with yarn.
- **Service worker caches the PWA aggressively** — always Cmd+Shift+R after
  a frontend rebuild, or uninstall + reinstall the PWA on mobile.
- **`frontend_overlay/` directory is dead** — anything there is NOT
  synced. Use `frontend_changes/` and add the file to `files_to_sync`.
- **`device_id="myHR Auto"` is reserved** — only Administrator + HR Manager
  + System Manager can set it. Used by the auto-present scheduler.

---

## 8. Documentation

| Doc | What it covers |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Architecture map + hard rules + common operations (read first) |
| [`docs/EMPLOYEE_DIRECTORY.md`](docs/EMPLOYEE_DIRECTORY.md) | Auto-synced contact book (PWA + Desk) |
| [`docs/EMPLOYEE_ACTION_CENTRE.md`](docs/EMPLOYEE_ACTION_CENTRE.md) | Onboarding hub (Personal Details, Identity, Declarations, Statutory & Bank, Employer history) |
| [`docs/EMPLOYEE_CHECKIN.md`](docs/EMPLOYEE_CHECKIN.md) | Geo-aware checkin with policy gate + auto-present cron |
| [`docs/LEAVE_AND_ATTENDANCE.md`](docs/LEAVE_AND_ATTENDANCE.md) | Single-stage Leave Application + Attendance Request |
| [`docs/HR_POLICY.md`](docs/HR_POLICY.md) | HR Policy + Policy Acknowledgement state machine |
| [`docs/HOLIDAY.md`](docs/HOLIDAY.md) | Holiday taxonomy + Optional Leave validator |
| [`docs/SETUP_AND_PATCHES.md`](docs/SETUP_AND_PATCHES.md) | Migration plumbing — `_setup()`, all patches, troubleshooting |
| [`docs/HANDOFF_V16_TO_V15.md`](docs/HANDOFF_V16_TO_V15.md) | **Read first if installing on v15.** v15 risk-surface fix recipes |
| [`docs/ELIXIIR_VS_MYHR.md`](docs/ELIXIIR_VS_MYHR.md) | Gap analysis between this app and the upstream Elixiir custom app |
| [`docs/ELIXIIR_MYHR_INTEGRATION.md`](docs/ELIXIIR_MYHR_INTEGRATION.md) | Phased plan for the Elixiir master-data merge (Phase 1 + 2 already shipped) |

---

## 9. Quick install runbook (copy-paste for a new developer)

```bash
# 0. Confirm host has yarn
yarn --version

# 1. Pull the app
cd ~/frappe-bench
bench get-app myhr <repo-or-tarball>

# 2. Install on the site (runs after_install → _setup → apply_custom_ui)
bench --site <your-site> install-app myhr

# 3. (Existing sites only — fresh installs skip this) Migrate to apply
#    backend changes + sync the PWA overlay
bench --site <your-site> migrate

# 4. If yarn build was skipped or failed, run the PWA sync standalone
bench --site <your-site> execute myhr.frontend_sync.apply_custom_ui

# 5. Smoke test (see §5)
bench --site <your-site> console
# > paste the smoke-test snippet from §5

# 6. Verify the overlay reached the bundle (see §4.1)
grep -c "Action Centre" apps/hrms/frontend/src/views/Home.vue
grep -l "Action Centre" apps/hrms/hrms/public/frontend/assets/Home-*.js

# 7. Open <site>/hrms in a browser, log in as an employee, hard-refresh
#    (Cmd+Shift+R), and walk through the manual verification in §6.
```

### 9.1 If you change backend code and want to see it in the PWA

```bash
bench --site <your-site> migrate
```

That's it. `after_migrate` runs `_setup()` + `apply_custom_ui`, which
re-syncs the Vue files, runs `yarn build`, regenerates the service
worker. Then hard-refresh the browser.

If you only changed a Vue file in `frontend_changes/` and nothing on
the backend, you can skip migrate and run just:

```bash
bench --site <your-site> execute myhr.frontend_sync.apply_custom_ui
```

---

## 10. Hard rules — never break

1. **Don't edit core apps.** `apps/frappe`, `apps/erpnext`, `apps/hrms`,
   `apps/crm` are read-only. All customisations live in `apps/myhr`.
2. **Edit Vue files in `frontend_changes/`, not the synced copies.** The
   files inside `apps/hrms/frontend/src/` are deployment artefacts —
   they get overwritten on every `apply_custom_ui` run. Source of truth
   is `apps/myhr/myhr/frontend_changes/`.
3. **Don't bypass the Policy Acknowledgement audit log.** Route status
   changes through `myhr.policy_audit.transition_pa_via_sql` (SQL paths)
   or rely on the controller's `validate` (ORM paths) — both write to
   `Policy Audit Log`.
4. **Don't run destructive operations** (`DROP`, `DELETE FROM`, `--force`,
   `--no-verify`, `git reset --hard`) without explicit confirmation.
5. **Server-stamped audit fields are immutable post-set.**
   `custom_approved_by`, `custom_approved_on`, `submitted_by`,
   `submitted_on`, `acknowledged_at`, `ip_address` — the validate hooks
   throw if you try to overwrite them.

---

## 11. Contributing

```bash
cd apps/myhr
pre-commit install
```

Pre-commit configured for: ruff (Python lint + format), eslint (JS lint),
prettier (JS / Vue format), pyupgrade.

---

## 12. License

`license.txt` (MIT).
