# Handoff guide — myHR v16 → v15

You're handing the myHR app to a developer running **Frappe / ERPNext / HRMS v15**. This codebase was developed and verified on **v16** only. This doc walks you through the bench provisioning, the smoke test, and the 4 known risk surfaces — so the dev's day 1 is "build features", not "debug compat."

---

## 0. ⚠️ Result of an actual v15 bring-up (2026-04-26)

We provisioned a real v15 bench at `~/Desktop/Antigravity/ERP/ERP_Demov15` to verify this. **One critical finding**: the developer's exact tag-pinned stack from their screenshot — **Frappe 15.58.1 + ERPNext 15.54.4 + HRMS 15.58.4** — is **broken upstream, not because of myhr/atbhr**:

| Layer | Issue at exact pinned version |
|---|---|
| HRMS 15.58.4 calls `build_qb_match_conditions` | ❌ Function doesn't exist in ERPNext 15.54.4 (added later) |
| HRMS 15.58.4 calls `get_setup_wizard_completed_apps` | ❌ Function doesn't exist in Frappe 15.58.1 (added later) |

**This means**: the dev's bench either has those functions backported via custom patches, OR the install is sitting on later commits than the displayed tags suggest, OR they haven't yet exercised any HR feature that hits those imports.

**Working combo we verified**: Frappe **15.106.0** + ERPNext **15.105.0** + HRMS **15.59.1** + atbhr (the v16 → v15 fork). All 6 smoke checks pass on this combo. Recommend the dev bump all 3 to latest v15 before installing atbhr — they were going to hit these issues anyway as soon as they ran HR reports.

The fork (`atbhr` — copy of `myhr` with module renamed) installed cleanly on this combo: 11/11 patches landed, all 9 Custom Fields stamped with correct flags, both override classes (`LeaveApplication`, `EmployeeCheckin`) load, single-stage LA status pinned, all 11 atbhr doctypes synced.

> **Audience**: the developer (or you, doing the v15 bring-up before handoff). Read top-to-bottom on first run. Section 6 is the only piece worth re-reading later.

---

## 1. Why this doc exists

myHR overrides stock HRMS in several places. Stock HRMS itself changed between v15 and v16 (added APIs, renamed methods, restructured the PWA frontend). The override layer that works on v16 may or may not work on v15 — we don't know without testing.

The four override surfaces with real risk:

1. **HRMS API overrides** — `myhr.api.get_leave_applications` and `get_attendance_requests` override `hrms.api.*`. The latter is newer.
2. **HRMS override classes** — `HRMSLeaveApplication` and `HRMSEmployeeCheckin` parents are imported and `super()` is called on validate methods.
3. **HRMS frontend overlay** — `myhr/frontend_sync.py:files_to_sync` lists Vue file paths under `apps/hrms/frontend/src/`. Layout may have changed.
4. **`Leave Period.optional_holiday_list`** — used by stock HRMS to gate optional leave; should exist in v15 but unverified.

Everything else in myHR (Policy Acknowledgement state machine, Policy Audit Log doctype, Holiday sync hook, Custom Fields, all 11 patches) is myHR-internal and version-agnostic.

---

## 2. Pre-flight — what you need

| Item | Value |
|---|---|
| Target Frappe branch | `version-15` |
| Target ERPNext branch | `version-15` |
| Target HRMS branch | `version-15` |
| Python | 3.10 or 3.11 (check with `python3 --version`) |
| Node | 18 LTS (Frappe v15 requirement) |
| Yarn | latest classic (`yarn --version` → 1.22.x) |
| MariaDB or Postgres | per Frappe v15 docs |
| Disk space | ~3 GB for a fresh bench |
| Time | 1–3 hours total (most of which is downloads + v15 fixes if any) |

If you're on Mac (per the project), Python is via Homebrew (`brew install python@3.11`); same for Node (`brew install node@18`).

---

## 3. Provision a v15 bench

**Important**: do this in a directory that doesn't conflict with the existing v16 bench (`~/Desktop/Antigravity/ERP/ERP_Demo`).

```bash
# 1. New bench
cd ~
bench init erpdemo-v15 --frappe-branch version-15
cd erpdemo-v15

# 2. Add ERPNext + HRMS at v15
bench get-app erpnext --branch version-15
bench get-app hrms --branch version-15

# 3. Create a site
bench new-site dev.localhost --admin-password admin --mariadb-root-password <your-root-pw>
bench --site dev.localhost install-app erpnext
bench --site dev.localhost install-app hrms

# 4. Confirm versions
bench --site dev.localhost console
>>> import frappe
>>> from frappe import __version__ as fv
>>> import erpnext, hrms
>>> print(fv, erpnext.__version__, hrms.__version__)
# Expect: '15.x.x' for all three
>>> exit()
```

If those don't all say 15, stop and resolve before installing myHR.

---

## 4. Bring myHR over

### Option A — Tarball drop (fastest)

From the v16 bench (where you have a tested copy):

```bash
cd ~/Desktop/Antigravity/ERP/ERP_Demo/apps
tar czf ~/myhr-v16-snapshot.tar.gz myhr/
```

Then on the v15 bench:

```bash
cd ~/erpdemo-v15/apps
tar xzf ~/myhr-v16-snapshot.tar.gz
cd ~/erpdemo-v15
echo "myhr" >> sites/apps.txt    # so bench knows about it
bench --site dev.localhost install-app myhr
```

### Option B — From git (if myHR is in a repo)

```bash
cd ~/erpdemo-v15
bench get-app myhr <repo-url> --branch <branch-name>
bench --site dev.localhost install-app myhr
```

### What `install-app` does

On install, Frappe runs:

1. **Schema sync** — creates myHR doctype tables (HR Policy, Policy Acknowledgement, Policy Audit Log, Employee Action Centre, Action Centre Activity, Employee Directory, 5 Policy Filter child doctypes).
2. **All 11 patches** in order (`v1_0..v1_9`). Most are no-ops on a fresh site (they're backfills) but they get marked applied in `Patch Log`.
3. **`after_install`** → `myhr.setup._setup()` → roles + perms + Property Setters + 9 Custom Fields.

This is the moment of truth. **If any of the 4 risk surfaces are incompatible with v15, the install errors here.** Read §5 next.

---

## 5. Smoke test — confirm install was clean

Run all four commands. Each one tests a specific outcome of the install.

```bash
bench --site dev.localhost console
```

Then in the console:

```python
import frappe

# === 1. All 11 patches landed ===
patches = [p.patch for p in frappe.get_all("Patch Log",
    filters={"patch": ("like", "%myhr%")}, fields=["patch"], order_by="creation")]
print(f"\nPatches applied: {len(patches)}")
for p in patches: print(f"  {p}")
# Expected: 11 entries v1_0_backfill_employee_directory through v1_9_repair_hr_controls_tab_placement

# === 2. Custom Fields with correct flags ===
import json
checks = {
    "Leave Application-custom_approved_by":  ["fieldtype", "read_only", "options"],
    "Leave Application-custom_approved_on":  ["fieldtype", "read_only"],
    "Employee-custom_emp_directory":         ["fieldtype", "default"],
    "Holiday-custom_holiday_type":           ["fieldtype", "options"],
}
print("\nCustom Field flags:")
for cf, cols in checks.items():
    val = frappe.db.get_value("Custom Field", cf, cols, as_dict=True)
    print(f"  {cf}: {val}")
# Expected:
#   Leave Application-custom_approved_by:  {'fieldtype':'Link','read_only':1,'options':'User'}
#   Leave Application-custom_approved_on:  {'fieldtype':'Datetime','read_only':1}
#   Employee-custom_emp_directory:         {'fieldtype':'Check','default':'1'}
#   Holiday-custom_holiday_type:           {'fieldtype':'Select','options':'Optional\nFixed\nWeekly Off'}

# === 3. Override classes loaded ===
print("\nOverride doctype classes:")
for dt, cls in (frappe.get_hooks("override_doctype_class") or {}).items():
    if "myhr" in str(cls).lower():
        print(f"  {dt}: {cls}")
# Expected: 'Leave Application' and 'Employee Checkin' both pointing at myhr.overrides.*

# === 4. Single-stage Leave Application status options ===
ps = frappe.db.get_value("Property Setter",
    {"doc_type":"Leave Application","field_name":"status","property":"options"}, "value")
print(f"\nLeave Application status options: {ps!r}")
# Expected: 'Open\nApproved\nRejected\nCancelled'
```

If all four print as expected, **stop here — myHR is happy on v15**. Update `pyproject.toml` to declare v15 (it already does, but confirm) and you're done.

If any one fails, jump to §6 and look up the corresponding risk surface.

---

## 6. The 4 known risk surfaces — detection + fix

### 6.1 HRMS API overrides (`get_attendance_requests`)

**Symptom**: `install-app` succeeds, but the PWA Team Requests screen for Attendance Requests shows nothing for HR Managers, OR you see `AttributeError: module 'hrms.api' has no attribute 'get_attendance_requests'` in the Error Log.

**Detection**:
```python
import hrms.api
print(hasattr(hrms.api, "get_attendance_requests"))
# v16: True
# v15: may be False
```

**Fix recipe** (only if `False`):

Open `apps/myhr/myhr/hooks.py` and either:

(a) Remove the override line:
```python
override_whitelisted_methods = {
    "hrms.api.get_leave_applications": "myhr.api.get_leave_applications",
    # "hrms.api.get_attendance_requests": "myhr.api.get_attendance_requests",  # removed for v15
}
```

(b) Or guard the import — open `apps/myhr/myhr/api.py` and wrap the body of `get_attendance_requests` to return early if the parent doesn't exist.

`bench --site dev.localhost migrate` after the change.

---

### 6.2 HRMS override classes (`super().validate()` failures)

**Symptom**: Saving a Leave Application or Employee Checkin throws `AttributeError: 'LeaveApplication' object has no attribute 'X'` or similar, where X is a method myHR's override calls via `super()`.

**Detection**:
```python
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin

for cls, methods in (
    (LeaveApplication, ["validate"]),
    (EmployeeCheckin, ["validate", "validate_distance_from_shift_location"]),
):
    for m in methods:
        print(f"{cls.__name__}.{m}: {hasattr(cls, m)}")
# All should print True
```

If any prints `False`, that method was renamed in v15.

**Fix recipe**:

Open `apps/myhr/myhr/overrides/leave_application.py` and `apps/myhr/myhr/overrides/employee_checkin.py`. For any `super().X()` call where X doesn't exist on the v15 parent, look up the equivalent method in `apps/hrms/hrms/hr/doctype/leave_application/leave_application.py` (v15 source on the local bench) and call that instead.

`bench --site dev.localhost migrate` to reload.

---

### 6.3 Frontend overlay file paths

**Symptom**: `bench --site dev.localhost execute myhr.frontend_sync.apply_custom_ui` fails with `FileNotFoundError: [...]/apps/hrms/frontend/src/views/X.vue`. This is the v15 PWA frontend not having the file path myHR expects.

**Detection** (after install but before running `apply_custom_ui` for the first time):
```python
import os
hrms_src = os.path.expanduser("~/erpdemo-v15/apps/hrms/frontend/src")
print(os.path.exists(hrms_src))
# Expect True; if False, v15 HRMS frontend has a different root.

# Check each path in files_to_sync exists in v15
from myhr.frontend_sync import apply_custom_ui  # don't call yet — read source
import inspect
print(inspect.getsourcefile(apply_custom_ui))
# Open that file and check the files_to_sync list manually against the v15 layout
```

**Fix recipe**:

Compare the file paths in `apps/myhr/myhr/frontend_sync.py:files_to_sync` against the v15 HRMS layout under `apps/hrms/frontend/src/`. For any v16-only path, either:

- Delete the row (if the v16 file's purpose doesn't apply to v15)
- Update the target path to the v15 equivalent
- Or, if the file path is identical but the underlying Vue component changed, copy the v16 source into the v15 layout — keeping in mind your overlay file may need adjustment for v15 frappe-ui props/imports

After fixing, run `bench --site dev.localhost execute myhr.frontend_sync.apply_custom_ui`. The yarn build at the end will surface any remaining import-or-prop incompatibilities.

If you want to skip the overlay entirely for v15 (e.g., dev is rebuilding the PWA from scratch), set `MYHR_SKIP_FRONTEND_SYNC=1` permanently in the bench `.env`.

---

### 6.4 `Leave Period.optional_holiday_list` field

**Symptom**: optional leave applications fail with `Optional Holiday List not set for leave period X`, or `frappe.db.get_value("Leave Period", {...}, "optional_holiday_list")` returns `None` everywhere.

**Detection**:
```python
import frappe
meta = frappe.get_meta("Leave Period")
field = next((f for f in meta.fields if f.fieldname == "optional_holiday_list"), None)
print(field)  # Expect a DocField; None means v15 HRMS doesn't ship this field
```

**Fix recipe** (only if `None`):

This field is HRMS-internal. v15 HRMS may not have it. Two options:

(a) **Add it via a Custom Field** — append to `MYHR_CUSTOM_FIELDS` in `setup.py`:
```python
{
    "dt": "Leave Period",
    "fieldname": "optional_holiday_list",
    "label": "Optional Holiday List",
    "fieldtype": "Link",
    "options": "Holiday List",
    "insert_after": "is_active",
    "description": "Holiday List used to source Optional leave dates for this period.",
},
```

Then `bench --site dev.localhost migrate` to create the field. The myHR optional-leave validator (`leave_optional_holiday.validate_optional_leave_dates`) doesn't read this field directly — it reads `Employee.holiday_list` — so adding the field is enough to satisfy stock HRMS's own validation gates.

(b) **Skip stock HRMS's gate**: ensure `Leave Type.include_holiday=0` for the optional leave types. This sidesteps the gate but also disables stock's own holiday filtering — myHR's filter still runs.

---

## 7. Going forward — single-fork vs dual-codebase

You'll have:
- The v16 myHR (the one you're handing over) — used by the original team's demo
- The v15 myHR — the dev's working copy

These will drift. Pick one strategy:

### Strategy A — Short-lived fork (recommended for a 3–6 month project)

The dev owns the v15 fork. They build features. At project end, they hand it back. You merge their changes into v16 main and retire v15.

Drift management: encourage the dev to keep their changes in narrow, mergeable commits (one feature per commit, clear titles). Avoid rebasing the v15 fork; merge from v16 main periodically.

### Strategy B — Long-lived dual fork

You + dev maintain both. Each cherry-picks fixes from the other. Works if both teams have ongoing roadmaps. Plan to spend 10-15% of dev time on cross-version syncing.

### Strategy C — Single dual-version codebase (most disciplined; biggest upfront cost)

Refactor myHR to feature-detect at runtime:

```python
try:
    from hrms.api import get_attendance_requests as _has_get_ar
    HAS_GET_AR = True
except ImportError:
    HAS_GET_AR = False
```

And gate the override:

```python
override_whitelisted_methods = {
    "hrms.api.get_leave_applications": "myhr.api.get_leave_applications",
}
if HAS_GET_AR:
    override_whitelisted_methods["hrms.api.get_attendance_requests"] = "myhr.api.get_attendance_requests"
```

This is what ERPNext itself does for cross-version compat. Worth the discipline if myHR is going to outlive the current project.

---

## 8. Working with Claude / Claude Code

The dev should use `apps/myhr/CLAUDE.md` as project context for any Claude Code session. From the bench root:

```bash
cd ~/erpdemo-v15
claude   # picks up apps/myhr/CLAUDE.md automatically
```

If the dev is using Claude.ai web or the API directly (not Claude Code), they should paste `apps/myhr/CLAUDE.md` content into the system prompt at the start of every session.

The CLAUDE.md tells Claude:
- Don't modify core apps (`apps/frappe`, `apps/erpnext`, `apps/hrms`, `apps/crm`)
- PWA changes flow through `myhr.frontend_sync.apply_custom_ui`
- PA state transitions flow through `myhr.policy_audit`
- Server-stamped audit fields are immutable post-set
- Where the 7 spec docs live (and which to read for which feature)

Tell the dev: when they hit a bug or change a feature, they should update the corresponding spec doc's findings table at the same time. Pattern is documented in `CLAUDE.md`.

---

## 9. Common gotchas during v15 bring-up

- **`bench install-app myhr` halts on `Could not find Default Assignee: pm@erp.localhost`** — that's a TicketNext after_migrate halt on the source bench. It does NOT travel with myHR. You won't see it on a fresh v15 bench unless you also installed TicketNext.
- **`yarn build` fails at apply_custom_ui** — usually means a v15 frappe-ui import path differs from v16. See §6.3.
- **`Leave Application` validate throws on the first save** — usually §6.2. Check `super()` calls.
- **Patches list shows fewer than 11 entries after install** — one or more patches errored. Look in `bench --site dev.localhost console`:
   ```python
   import frappe
   frappe.get_all("Error Log",
       filters={"creation": (">", frappe.utils.add_to_date(None, hours=-1))},
       fields=["error", "creation"], limit=5)
   ```
- **PWA looks unchanged after install** — `apply_custom_ui` didn't run (TicketNext halt skipped after_migrate). Run it manually: `bench --site dev.localhost execute myhr.frontend_sync.apply_custom_ui`.

---

## 10. Once it's working — final checklist before handoff

- [ ] All 4 smoke checks in §5 pass
- [ ] PWA login as a test employee → loads `/directory`, `/policies`, `/action-centre` without errors
- [ ] HR Manager Desk → can open HR Policy + see "Mark all as Acknowledged" / "Force Re-acknowledgement" buttons
- [ ] HR Manager Desk → can open Employee Action Centre + see "Accept all pending rows" / "Reject all pending rows" / "Reopen for re-edit" buttons
- [ ] Apply leave on an Optional date as the test employee → saves
- [ ] Apply leave on a Fixed date → throws "fixed company holiday"
- [ ] Apply leave on Sat/Sun → throws "weekly off"
- [ ] `bench --site dev.localhost migrate` runs cleanly twice in a row (idempotency check)
- [ ] `pyproject.toml` declares v15 in the `[tool.bench.frappe-dependencies]` section
- [ ] Run `pre-commit install` so the dev's editor catches lint issues

When all of these pass, tar the bench (or just `apps/myhr`) and hand it over.

---

## 11. What to give the developer

| Item | Path |
|---|---|
| The tested v15 myHR | `apps/myhr/` (tar from the v15 bench) |
| Install + smoke-test guide | [`README.md`](../README.md) |
| Claude project context | [`CLAUDE.md`](../CLAUDE.md) |
| Per-feature specs | [`docs/`](.) (7 files) |
| **This handoff guide** | [`docs/HANDOFF_V16_TO_V15.md`](HANDOFF_V16_TO_V15.md) |
| Optional: bench tarball | the whole `~/erpdemo-v15/` tree, if you want to ship a known-working dev environment |
