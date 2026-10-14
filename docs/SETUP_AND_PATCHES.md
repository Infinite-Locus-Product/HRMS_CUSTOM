# myHR Setup & Patches Infrastructure

The migration plumbing — what runs `after_install` and `after_migrate`, what each registered patch does, and the conventions every new patch should follow. This is the spec the previous five surface-specific docs depend on.

---

## 1. Entry points

Wired in [hooks.py](../myhr/hooks.py):

```python
after_install = "myhr.setup.after_install"
after_migrate = "myhr.setup.after_migrate"
```

| Hook | Calls | When it runs |
|---|---|---|
| `after_install` | `_setup()` | Once, on `bench install-app myhr`. |
| `after_migrate` | `_setup()` + `_apply_custom_ui_safe()` | Every `bench migrate`. The TicketNext `LinkValidationError: pm@erp.localhost` halt that's been showing up across this session blocks `_apply_custom_ui_safe` from running here, but `_setup()` lands every time before the halt because Frappe runs registered after_migrate functions in order. |

`_apply_custom_ui_safe` runs the HRMS-overlay frontend sync ([frontend_sync.apply_custom_ui](../myhr/frontend_sync.py)) which copies myhr's Vue files into `apps/hrms/frontend/src/` and runs `yarn build`. Failures are caught and logged — they never abort migrate. Skippable via `MYHR_SKIP_FRONTEND_SYNC=1` (CI / test envs).

---

## 2. `_setup()` — what it does

[setup.py:_setup](../myhr/setup.py) runs in this order on every install + migrate:

1. **`_ensure_roles()`** — creates `HR Manager`, `HR User`, `Employee` roles if missing. Idempotent.
2. **`_enforce_permissions()`** — for every doctype in `MYHR_PERMISSIONS`, **wipes all Custom DocPerm rows** for that doctype and re-inserts the canonical set. Currently only `Employee Directory`. The wipe-then-replace pattern means HR-side perm edits via Desk get reverted on next migrate — *intentional*; myHR owns the perms on its own doctypes.
3. **`_ensure_additive_permissions()`** — for stock doctypes where myHR needs to ADD a perm row (currently `Attendance Request → Leave Approver`), inserts the row only if missing. Doesn't touch the rest of stock HRMS perms.
4. **`_ensure_leave_application_status_property_setter()`** — pins `Leave Application.status` options to `Open\nApproved\nRejected\nCancelled` (single-stage, removes the `Approved by Manager` two-stage option that earlier myHR code introduced).
5. **`_ensure_attendance_request_employee_ignore_user_permissions()`** — sets `Attendance Request.employee.ignore_user_permissions=1` via Property Setter. Stock HRMS does this on Leave Application but missed Attendance Request; without it, managers with `Create User Permission=1` can't see their team's draft AR rows.
6. **`_ensure_employee_leave_approver_labels()`** — pins the `Employee.leave_approver` field label to "Leave Approver" (no two-stage suffix).
7. **`_ensure_custom_fields()`** — creates every Custom Field declared in `MYHR_CUSTOM_FIELDS` if missing. **Skip-if-exists** — does NOT update existing fields whose declared attrs drift. The v1_8 patch repairs drift.
8. **`_ensure_holiday_type_options()`** — merges `Weekly Off` into the `Holiday.custom_holiday_type` Select options for installs created before that option was added.
9. `frappe.db.commit()` + `frappe.clear_cache()`.

---

## 3. `MYHR_PERMISSIONS` vs `MYHR_ADDITIVE_PERMISSIONS`

The two patterns serve different purposes:

| Pattern | Used for | Behaviour |
|---|---|---|
| `MYHR_PERMISSIONS` | Doctypes myHR **owns** (e.g., Employee Directory) | Wipes all Custom DocPerm + re-inserts. HR-side perm edits get reverted on migrate. |
| `MYHR_ADDITIVE_PERMISSIONS` | Stock HRMS doctypes where myHR adds ONE row (e.g., AR for Leave Approver) | Insert-if-missing. Doesn't touch the rest of stock perms. |

Don't put a doctype in both maps; the wipe in `_enforce_permissions` would clobber the additive insert.

---

## 4. `MYHR_CUSTOM_FIELDS`

Fields myHR declares on stock doctypes. Each entry is a dict; honoured attrs are listed in `setup.py:_CUSTOM_FIELD_PASSTHROUGH_ATTRS`. As of v1_8:

```
label, fieldtype, insert_after, options, default, description,
bold, in_list_view, in_standard_filter, unique,
read_only, reqd, hidden, no_copy, print_hide,
permlevel, translatable, non_negative, ignore_user_permissions,
depends_on, mandatory_depends_on, read_only_depends_on,
fetch_from, fetch_if_empty, length, precision
```

Anything outside this list in a `MYHR_CUSTOM_FIELDS` entry is silently ignored. **If you add a new attr to the dict, add it to `_CUSTOM_FIELD_PASSTHROUGH_ATTRS` too.**

### Currently declared (8 fields)

| DocType | Field | Type | Notes |
|---|---|---|---|
| Employee | `custom_employee_id` | Data, unique=1 | The business Employee ID; `validate_employee` forces `Employee.name` to this on insert. |
| Employee | `custom_hr_controls_tab` | Tab Break | Anchors the "HR Controls" tab. |
| Employee | `custom_emp_directory` | Check, default=1 | When 1 + status=Active → row appears in Employee Directory. |
| Employee | `custom_add_to_action_centre` | Check, default=1 | When 1 → AC auto-created on insert. |
| Employee | `custom_auto_present` | Check, default=0 | Cron auto-checks-in this employee. |
| Employee | `custom_bypass_geolocation_check` | Check, default=0 | Skip radius enforcement (lat/long still required). |
| Holiday | `custom_holiday_type` | Select(Optional / Fixed / Weekly Off) | The whole Optional Leave gate keys off this. |
| Leave Application | `custom_approved_by` | Link User, **read_only=1** | Server-stamped on Open → Approved (LA-1). |
| Leave Application | `custom_approved_on` | Datetime, **read_only=1** | Server-stamped on the same transition. |

### Skip-if-exists nuance

`_ensure_custom_fields` doesn't update existing fields. If you change an attr in `MYHR_CUSTOM_FIELDS` (e.g., flip `read_only` from 0 to 1), the runtime function won't repair the on-DB row — you need a one-shot patch. v1_8 does this for the entire map; clone its pattern for future drifts.

---

## 5. Patches registered (v1_0 → v1_12)

[patches.txt](../myhr/patches.txt) lists every patch in execution order. Frappe runs them once per site (tracked in `Patch Log`). Re-running a patch on a fresh site or on a re-installed app re-executes it; idempotency is the patch's responsibility, not Frappe's.

| Patch | Closes | One-line description |
|---|---|---|
| `v1_0_backfill_employee_directory` | F-1 (Directory) | Backfills `Employee Directory` rows from existing Employees with `custom_emp_directory=1`. |
| `v1_1_remove_hr_approver` | F-1 (L&A) | Removes the legacy `hr_approver` Custom Field (was for two-stage approval), migrates `status='Approved by Manager'` → `'Approved'`. |
| `v1_1_split_policy_acknowledgement` | F-PA-* setup | Migrates legacy `Policy Action Task` child rows on `Employee Action Centre` into the standalone `Policy Acknowledgement` doctype. |
| `v1_2_hr_controls_tab` | F-7 (Checkin) | Moves the `custom_hr_controls_tab` Tab Break + four flag fields onto the HR Controls tab. |
| `v1_3_dedupe_pa_and_add_unique_index` | F-PA-10 | Dedupes duplicate Policy Acknowledgement rows by status rank, then adds the `unique_pa_employee_policy_version` index. |
| `v1_4_drop_policy_action_task` | F-PA-3 | `frappe.delete_doc("DocType", "Policy Action Task")` + `DROP TABLE` the underlying SQL table. |
| `v1_5_withdraw_pending_on_inactive_policies` | F-PA-16 | Backfills `status='Withdrawn'` on Pending PAs whose HR Policy is `is_active=0` (legacy data state). |
| `v1_6_dedupe_eac_and_add_unique_index` | EAC-1 | Dedupes duplicate Employee Action Centre rows by status rank + latest modified, then adds `unique_eac_employee` index. |
| `v1_7_fix_holiday_type_for_weekly_off` | HOL-1 / HOL-4 | SQL UPDATE: `weekly_off=1` → `Weekly Off` type; blank type → `Fixed`; `weekly_off=0`+`Weekly Off` → `Fixed`. |
| `v1_8_repair_custom_field_flags` | SET-1 | Sweeps `MYHR_CUSTOM_FIELDS`, finds existing rows with drift on any honoured attr, repairs via `frappe.db.set_value`. |
| `v1_9_repair_hr_controls_tab_placement` | SET-6 | Re-asserts `insert_after` on `custom_hr_controls_tab` + the 4 HR-control flag fields so they land under the **HR Controls** tab instead of **Overview** on existing v15 sites where the chain drifted. Idempotent. |
| `v1_10_employee_view_reporting` | SET-7 / F-LA-AR-1 follow-up | Migrates demo data off the CUP-based Employee visibility model onto the new `custom_allow_view_reporting` model. Deletes stale CUP-driven `User Permission` rows on the 10 demo employees, sets `create_user_permission=0` on all of them, sets `custom_allow_view_reporting=1` on the 7 managers / `0` on the 3 executives. Idempotent. See [`EMPLOYEE_PERMISSIONS.md`](EMPLOYEE_PERMISSIONS.md). |
| `v1_11_employee_write_lockdown` | SET-8 / PERM-2 | Locks writes on `Employee` to HR Manager + System Manager + Administrator only. Calls `_ensure_employee_perm_lockdown` which scans permlevel=0 rows on Employee, identifies any non-exempt role with a write-class flag (notably HR User), and inserts a Custom DocPerm row forcing `write/create/delete/submit/cancel/amend = 0` while keeping `read = 1`. Idempotent — already-locked rows are no-ops; the same function re-runs every `after_migrate` so the lockdown self-heals. See [`EMPLOYEE_PERMISSIONS.md`](EMPLOYEE_PERMISSIONS.md) §6 "Write lockdown". |
| `v1_12_repair_hr_controls_tab_anchor` | SET-9 | Re-anchors `custom_hr_controls_tab.insert_after` from the legacy value `branch` to `grade` so that the stock ERPNext `grade` field stays inside the **Overview** tab (it was previously leaking into HR Controls because no stock Tab Break sits between `branch` and `grade`). Also re-asserts the full HR Controls field chain. Hardened: uses raw `frappe.db.sql UPDATE` plus a read-back verification + retry — `frappe.db.set_value` was observed to silently fail on this specific row during a real migrate run. Idempotent. |

---

## 6. Conventions every new patch should follow

1. **Idempotent.** Re-running the patch must be a no-op or repeat safely. Use `frappe.db.exists` before insert; use `add_unique` (which is idempotent) for indices; use raw SQL with appropriate WHERE clauses.
2. **Defensive on missing dependencies.** Check `frappe.db.exists("DocType", X)` before reading/writing — patches register at the app level and might land on a site that's missing the doctype (e.g., older HRMS, partial install).
3. **Print a one-line summary.** Every patch should `print()` what it did so the migrate log captures it. Counts > silence.
4. **Don't import from `setup.py` runtime symbols** unless you're OK with the patch ↔ setup coupling. Cleanest: duplicate the constant or accept that the import is a versioning trade-off (v1_8 imports `MYHR_CUSTOM_FIELDS` because that's the source of truth being repaired).
5. **Commit explicitly.** `frappe.db.commit()` at the end of the patch — Frappe doesn't auto-commit between patches.
6. **Naming**: `v{major}_{minor}_{short_description}.py`. Numbers don't need to match a real version; they're an execution order.
7. **Register**: add the patch to `patches.txt` in the `[post_model_sync]` block. Order matters when patches depend on each other.

---

## 7. SET-* findings

| # | Issue | Status |
|---|---|---|
| **SET-1** | `_ensure_custom_fields` only honoured a subset of dict attrs (label / fieldtype / insert_after / options / default / description / bold / in_list_view / unique). `read_only`, `reqd`, `hidden`, `permlevel`, etc. were silently dropped. The LA Phase-2 audit fields `custom_approved_by` + `custom_approved_on` declared `read_only:1` but landed editable on the Desk form. | **RESOLVED 2026-04-26.** Refactored `_ensure_custom_fields` to iterate `_CUSTOM_FIELD_PASSTHROUGH_ATTRS` (24 attrs). New patch [v1_8_repair_custom_field_flags.py](../myhr/patches/v1_8_repair_custom_field_flags.py) sweeps `MYHR_CUSTOM_FIELDS`, finds drift on existing rows, repairs via `set_value`. Verified live: 6 fields repaired (4 Employee descriptions + 2 LA `read_only` flags). Post-patch `Leave Application-custom_approved_by.read_only=1`, `custom_approved_on.read_only=1`. |
| **SET-2** | `_enforce_permissions` does an unconditional wipe-then-replace of `Custom DocPerm` for every doctype in `MYHR_PERMISSIONS`. Direct HR-side perm edits get silently reverted on every migrate. | **Documented as intentional.** myHR owns perms on its own doctypes (only `Employee Directory` today); HR-side edits would drift across migrates anyway. The pattern is correct; just non-obvious without the spec. |
| **SET-3** | `_ensure_holiday_type_options` is the only "options-merge" helper that runs for an existing field. Other Custom Field option lists drift the same way (e.g., if we ever extend `Action Centre Activity.action`). | **Open — generic option-merge helper not built.** Today every option list extension is a one-off helper or a one-off patch. A `_merge_select_options(field, new_options)` utility would centralise the pattern. |
| **SET-4** | `_apply_custom_ui_safe` runs `yarn build` on every migrate. Adds 5–10 s to every migrate even when no Vue files changed. | **Open — opt-in mode could skip when overlay timestamps are unchanged.** Today the env var `MYHR_SKIP_FRONTEND_SYNC=1` is a blunt-instrument off switch. A `--smart` mode that compares mtimes would be cheaper. |
| **SET-5** | No way to inspect "what does after_migrate do?" without reading the code. | **Open.** A `myhr.setup.print_setup_summary()` helper that prints a manifest of what would run could be useful as a `bench execute` debug tool. |
| **SET-6** | On existing v15 myhr sites, the four HR-control flag fields rendered under the Employee form's **Overview** tab instead of **HR Controls**. Root cause: `_ensure_custom_fields` is skip-if-exists, so once an early install set the wrong `insert_after` on a Custom Field, subsequent migrates couldn't repair it — even though the v1_2 patch attempted to fix it. setup.py and v1_2 already declare the correct chain (matches v16 myhr); the breakage is purely on rows that existed before the chain was finalised. | **RESOLVED 2026-04-27.** New patch [v1_9_repair_hr_controls_tab_placement.py](../myhr/patches/v1_9_repair_hr_controls_tab_placement.py) re-asserts `insert_after` on `custom_hr_controls_tab` + the 4 child fields unconditionally. Idempotent. Mirror copy registered in v16 myhr defensively. Verify on a live site with `frappe.db.get_value("Custom Field", "Employee-custom_emp_directory", "insert_after")` — should return `custom_hr_controls_tab`. |
| **SET-7** | Stock CUP-based Employee visibility (`create_user_permission`) couldn't express "manager sees self + direct reports" — only "user sees self only". The demo set worked around this by leaving CUP=0 on managers (so they saw all 10 employees), which leaked org-wide visibility to anyone with a manager-flag Employee record. Compounded: changing the org chart required re-enumerating per-row `User Permission` rows. | **RESOLVED 2026-04-27.** New Custom Field `Employee.custom_allow_view_reporting` (Check, default 0) declared in `MYHR_CUSTOM_FIELDS`. New module [`myhr/permissions.py`](../myhr/permissions.py) exposes `employee_permission_query_conditions` + `has_employee_permission`, wired in [`myhr/hooks.py`](../myhr/hooks.py) as `permission_query_conditions["Employee"]` and `has_permission["Employee"]`. The two hooks short-circuit HR Manager / HR User / System Manager / Administrator to "see all"; Employee-linked users with the flag=1 see self + direct reports (read-only); flag=0 see self only. New patch [`v1_10_employee_view_reporting.py`](../myhr/patches/v1_10_employee_view_reporting.py) deletes stale CUP `User Permission` rows on the 10 demo employees, sets `create_user_permission=0` on all of them, sets `custom_allow_view_reporting=1` on the 7 managers / `0` on the 3 executives. Idempotent. See [`EMPLOYEE_PERMISSIONS.md`](EMPLOYEE_PERMISSIONS.md) for the full spec. |
| **SET-8** | Stock ERPNext grants HR User full r/w/c/d on `Employee`. The user's policy is "any info to update, ask HR Manager" — so HR User must be read-only too, and even users opening their own Employee record must be blocked from saving. The previous code-driven model (SET-7) only enforced read-scope; writes still leaked through stock DocPerm + the implicit "Employee role can read self" rule. | **RESOLVED 2026-04-27.** Tightened [`has_employee_permission`](../myhr/permissions.py) so write-class ptypes (`write` / `create` / `delete` / `submit` / `cancel` / `amend` / `import` / `export`) return `False` for any user that is not Administrator + HR Manager + System Manager — including the user's own record. New helper [`_ensure_employee_perm_lockdown`](../myhr/setup.py) inserts a Custom DocPerm row at permlevel 0 for every non-exempt role with a write flag on Employee (notably HR User), forcing the write flags to 0 while keeping `read = 1`. Wired into `_setup()` so it runs on every `after_migrate`. New patch [`v1_11_employee_write_lockdown.py`](../myhr/patches/v1_11_employee_write_lockdown.py) lands the lockdown on existing sites. Defense in depth: the code gate is canonical; the DocPerm gate makes Role Permission Manager visually correct. See [`EMPLOYEE_PERMISSIONS.md`](EMPLOYEE_PERMISSIONS.md) §6 "Write lockdown" for the full spec and `PERM-2` finding. |
| **SET-9** | The stock ERPNext `grade` field rendered under HR Controls instead of Overview. Root cause: `custom_hr_controls_tab` Tab Break was anchored at `branch`, but no stock Tab Break sits between `branch` and `grade` in either v15 or v16 ERPNext — so `grade` (and any field between it and the next stock Tab Break) was pulled into HR Controls. Two failure surfaces compounded: (a) the v1_9 patch's `frappe.db.set_value` call silently failed during real migrate runs (`modified` timestamp unchanged despite "REPAIR" log line); (b) the stale `fixtures/custom_field.json` carried an old broken chain that could be re-imported via `bench import-fixtures`. | **RESOLVED 2026-04-27.** Re-anchored `custom_hr_controls_tab.insert_after = "grade"` in `setup.py` so HR Controls opens AFTER `grade`, leaving `grade` inside Overview. New patch [`v1_12_repair_hr_controls_tab_anchor.py`](../myhr/patches/v1_12_repair_hr_controls_tab_anchor.py) lands the change on existing sites with hardened semantics: raw `frappe.db.sql UPDATE` (bypasses controller quirks) plus read-back verification + retry-with-set_value fallback. Stale `myhr/fixtures/custom_field.json` deleted (not in `hooks.py.fixtures`, was dead code at install time but a footgun for `bench import-fixtures`). Verified live on both v15 myhr (`v15.localhost`) and v16 myhr (`erp.localhost`): Employee form Overview tab now contains Branch + Grade; HR Controls tab contains only the 5 Custom Field checkboxes; Joining / Address & Contacts tab follows naturally. |

---

## 8. Operational runbook

### Fresh install

```bash
bench install-app myhr
# after_install runs _setup() → roles + perms + property setters + Custom Fields
# All registered patches run automatically (Frappe's installer applies them before marking site ready).
```

### Existing site upgrade

```bash
bench --site <site> migrate
# 1. Schema sync: doctype JSON changes (new fields, new doctypes, new options) land first.
# 2. Patches: v1_0..v1_9 run in order. Already-applied ones are skipped via Patch Log.
# 3. after_migrate hooks: _setup() runs; _apply_custom_ui_safe() runs (or fails non-fatally).
```

### Troubleshooting

- **PWA at `/<site>/hrms` shows stock HRMS UI (no Action Centre / Policy Centre / Employee Directory QuickLinks, no pending-policies banner)** — the frontend overlay didn't deploy, which means the rest of the backend works (gates, doctypes, patches) but the user-facing PWA is plain HRMS. Cause: either `apply_custom_ui` never ran, or it ran but a subsequent `bench update` of `apps/hrms` overwrote the synced files in `apps/hrms/frontend/src/`. Fix: `bench --site X execute myhr.frontend_sync.apply_custom_ui`, then hard-refresh the browser (Cmd+Shift+R / Ctrl+F5). Verify with: `grep -c "myhr.api" apps/hrms/frontend/src/views/Home.vue` (should be ≥ 1) and `grep -l "Action Centre" apps/hrms/hrms/public/frontend/assets/Home-*.js` (should match at least one chunk). See README §4 for the full check.
- **Migrate halts on `LinkValidationError: pm@erp.localhost`** — the TicketNext `after_migrate` halt across all our sessions. Pre-existing demo-data issue; **myhr's `_setup()` runs before that point**. To verify your changes landed: `bench --site X console`, then check `frappe.db.exists("Patch Log", {"patch": "myhr.patches.v1_X..."})`.
- **Custom Field flags don't match what's declared** — re-run the v1_8 patch: `bench --site X execute myhr.patches.v1_8_repair_custom_field_flags.execute`.
- **HR Controls fields appear under Overview tab on the Employee form** — re-run the v1_9 patch: `bench --site X execute myhr.patches.v1_9_repair_hr_controls_tab_placement.execute`, then hard-reload the Employee form (Ctrl+F5) to refresh the cached form meta.
- **Need to skip frontend sync (CI / containers without yarn)** — `MYHR_SKIP_FRONTEND_SYNC=1 bench --site X migrate`.
- **`_ensure_custom_fields` says "skipping" for a field whose attr you changed** — that's expected; it's skip-if-exists. Use a v1_X patch to repair existing rows.
- **Need to drop and re-create Custom DocPerm on a doctype outside `MYHR_PERMISSIONS`** — don't add it to `MYHR_PERMISSIONS` (that nukes HRMS-owned perms). Use `MYHR_ADDITIVE_PERMISSIONS` instead.
