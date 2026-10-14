# HR Policy + Policy Acknowledgement

Spec + audit for the policy-distribution surface in `apps/myhr`. This is the doctype pair that drives **compliance** for the whole product:

- **HR Policy** is the master document — the PDF, versioning state, who-gets-it-rules, and the "blocking" flag that hooks the Employee Checkin + Attendance Request gates.
- **Policy Acknowledgement (PA)** is the per-employee, per-version receipt — pending until the user taps Acknowledge in the PWA, frozen forever once they do, superseded automatically when HR uploads a new file.

Live verified on `erp.localhost` 2026-04-26 with the 10-user demo org chart. Findings in §6.

---

## 1. Doctypes

| Doctype | Path | Notes |
|---|---|---|
| **HR Policy** | [apps/myhr/myhr/myhr/doctype/hr_policy/hr_policy.json](../myhr/myhr/doctype/hr_policy/hr_policy.json) | Master. `autoname=POL-{####}`. `delete=0` for HR/SysMgr; `Employee` is read-only. Custom controller is empty `pass` — all behaviour lives in `policy_hooks.py`. |
| **Policy Acknowledgement** | [apps/myhr/myhr/myhr/doctype/policy_acknowledgement/policy_acknowledgement.json](../myhr/myhr/doctype/policy_acknowledgement/policy_acknowledgement.json) | Receipt. `autoname=PA-{####}`. `allow_rename=0`. HR/SysMgr have full perms; Employee read-only. **Controller enforces a state machine — see §4.** |
| Policy Filter Department | `policy_filter_department` | Child table — single `department: Link Department`. |
| Policy Filter Designation | `policy_filter_designation` | Child table — single `designation: Link Designation`. |
| Policy Filter Branch | `policy_filter_branch` | Child table — single `branch: Link Branch`. |
| Policy Filter Employment Type | `policy_filter_employment_type` | Child table — single `employment_type: Link Employment Type`. |
| Policy Filter Employee | `policy_filter_employee` | Child table — single `employee: Link Employee`. Manual override list. |
| ⚠️ Policy Action Task **(legacy)** | `policy_action_task` | Vestigial child table left on disk. **0 rows live**, no code path reads it (migrated to `Policy Acknowledgement` by [v1_1_split_policy_acknowledgement.py](../myhr/patches/v1_1_split_policy_acknowledgement.py)). Candidate for deletion — see F-PA-3. |

### HR Policy field model

| Field | Type | Default | Purpose |
|---|---|---|---|
| `policy_name` | Data | reqd | Display label (used everywhere instead of `name`). |
| `category` | Select | "General" | One of `Leave / POSH / Gratuity / General`. PWA renders this as a chip. |
| `is_active` | Check | 1 | Read-only deactivates the policy: no new Pending PAs are seeded; existing PAs are preserved as audit. The Checkin gate ignores inactive policies. |
| `version` | Int (read-only) | 1 | Auto-incremented when `file` changes. Drives supersession of old PAs. |
| `mandatory_check_in_block` | Check | 0 | If 1, employees in scope cannot Employee Checkin or Attendance Request until they ack. **This is the "blocking" flag the gates key off.** |
| `file` | Attach | reqd | The actual PDF/policy document. The hash of this field changing is what bumps `version`. |
| `description` | Small Text | — | Inline copy shown in the PWA Policy Centre under the title. |
| `applies_to_all_employees` | Check | 1 | Org-wide vs. scoped. When 1, every Active Employee gets this policy. |
| `applicability_logic` | Select (`OR` / `AND`) | "OR" | Combinator across the filter tables (only when `applies_to_all_employees=0`). |
| `applicable_departments` / `applicable_designations` / `applicable_branches` / `applicable_employment_types` / `applicable_employees` | Tables | empty | Five filter slots; each contributes a True/False to the combinator if it has any rows. |

### Policy Acknowledgement field model

| Field | Type | Notes |
|---|---|---|
| `employee` | Link Employee, reqd, **immutable post-insert** | The owner. |
| `employee_name` | Data, fetched | UI only. |
| `hr_policy` | Link HR Policy, reqd, **immutable post-insert** | The policy. |
| `policy_name` | Data, fetched | UI only. |
| `policy_version` | Int, default 1, read-only, **immutable post-insert** | Snapshot of the HR Policy version at the time of seeding. |
| `status` | Select (`Pending / Acknowledged / Superseded`), read-only | State machine, see §4. |
| `acknowledged_at` | Datetime, read-only | Set by `acknowledge_policy_acknowledgement`. Immutable once set. |
| `ip_address` | Data, read-only | Captured by `acknowledge_policy_acknowledgement` from `frappe.local.request_ip`. |
| `superseded_by` | Link PA, read-only | Currently **never written** by the supersede SQL — see F-PA-1. The field exists; the semantics aren't wired. |

---

## 2. Wiring (hooks.py)

```python
doc_events = {
    "HR Policy": {
        "validate":  "myhr.policy_hooks.validate_hr_policy",       # version bump on file change
        "on_update": "myhr.policy_hooks.after_save_hr_policy",     # supersede + reconcile
        "on_trash":  "myhr.policy_hooks.on_trash_hr_policy",       # blocks deletion
    },
    "Employee": {
        "after_insert": [
            "myhr.policy_hooks.reconcile_after_employee_insert",   # seed PAs on hire
            ...
        ],
        "on_update": [
            "myhr.policy_hooks.reconcile_on_employee_update",      # re-evaluate on scope-field change
            ...
        ],
    },
}
```

There is **no** scheduled job for policy reconciliation — it runs entirely on the document hooks.

---

## 3. Scoping logic — `applies_to_employee(policy, employee)`

Source: [apps/myhr/myhr/policy_hooks.py](../myhr/policy_hooks.py).

```
SCOPE_FILTERS = (
    ("applicable_departments",      "Policy Filter Department",      "department",      "department"),
    ("applicable_designations",     "Policy Filter Designation",     "designation",     "designation"),
    ("applicable_branches",         "Policy Filter Branch",          "branch",          "branch"),
    ("applicable_employment_types", "Policy Filter Employment Type", "employment_type", "employment_type"),
    ("applicable_employees",        "Policy Filter Employee",        "employee",        "name"),
)
```

Decision tree, executed top-down:

1. Policy `is_active=0` → **False**.
2. Employee `status != 'Active'` → **False**.
3. `applies_to_all_employees=1` → **True** (short-circuit; filter tables ignored).
4. Employee record missing → **False** (defensive).
5. For each of the 5 filter tables: if it has rows, contribute a True/False (`emp.<attr> ∈ filter rows`). Empty tables don't contribute.
6. **No filter contributed (all 5 empty + applies_to_all=False)** → **False**. The policy applies to nobody. (Verified live: T3.)
7. Combinator: `OR` (any match) or `AND` (every contributing match).

**Important nuance:** in `AND` mode, only filter tables with rows are part of the AND. So if you set `applicable_departments=[Sales]` and leave the other four empty under `AND`, the result is "matches Sales". This may or may not be desired — see CR-2.

---

## 4. State machine on Policy Acknowledgement

Source: [policy_acknowledgement.py](../myhr/myhr/doctype/policy_acknowledgement/policy_acknowledgement.py). Codified 2026-04-26; extended with `Withdrawn` in Phase 2.

```
              ┌─────────┐
   create ───►│ Pending │──────────────► (deleted by HR — perms allow)
              └──┬──┬───┘
                 │  │ HR Policy is_active flips to 0
                 │  ▼
                 │ ┌────────────┐
                 │ │ Withdrawn  │  (frozen — policy retired before user acked)
                 │ └────────────┘
                 │
                 │ acknowledge_policy_acknowledgement (PWA / API / BulkAck)
                 ▼
              ┌──────────────┐
              │ Acknowledged │  (terminal for the user; no revert)
              └──────┬───────┘
                     │ HR uploads new file OR force_reacknowledgement_campaign
                     ▼
              ┌────────────┐
              │ Superseded │  (frozen audit row)
              └────────────┘
```

| From → To | Allowed? | Source |
|---|---|---|
| (insert) → Pending / Acknowledged / Superseded / Withdrawn | ✅ | `ensure_policy_acknowledgements_for_employee` seeds Pending; migration patches may seed any. |
| Pending → Pending / Acknowledged / Superseded / Withdrawn | ✅ | normal lifecycle. |
| **Acknowledged → Pending** | ❌ throws | the audit invariant — can't un-acknowledge. |
| Acknowledged → Acknowledged | ✅ (no-op resaves) | as long as `acknowledged_at` is unchanged. |
| Acknowledged → Superseded | ✅ | version-bump path only. |
| **Acknowledged → Withdrawn** | ❌ throws | acked rows are immutable receipts. Deactivating a policy after employees have acked them does NOT alter their Acknowledged rows. |
| **Superseded → anything** | ❌ throws | frozen. |
| **Withdrawn → anything** | ❌ throws | frozen. The policy was retired; this row is the audit receipt of "user never got the chance." |

### Other invariants

- `employee`, `hr_policy`, `policy_version` are **immutable** after insert. Throws if changed.
- `acknowledged_at` and `ip_address` cannot be set on Pending rows (validate strips them on insert + on Pending → Pending resaves). They are server-stamped on the Pending → Acknowledged transition only — closes the HR-backdating attack vector.
- `acknowledged_at` cannot be cleared or rewritten on a row that's already Acknowledged.
- The version-supersede + deactivate-withdraw paths use raw SQL — `validate()` doesn't fire, so they bypass the state machine on purpose. They MUST go through `myhr.policy_audit.transition_pa_via_sql(...)` so the audit log captures the move; otherwise `track_changes` would silently miss them.

### Live verification (2026-04-26)

| Scenario | Expected | Live result |
|---|---|---|
| Acknowledged → Pending via Desk save | throws | ✅ ValidationError "Cannot change Policy Acknowledgement status from 'Acknowledged' to 'Pending'." |
| Withdrawn → Pending via Desk save | throws | ✅ ValidationError "Cannot change Policy Acknowledgement status from 'Withdrawn' to 'Pending'." |
| Mutate `employee` post-insert | throws | ✅ ValidationError "Cannot change 'employee' on an existing Policy Acknowledgement…" |
| Clear `acknowledged_at` on Acked row | throws | ✅ ValidationError "Cannot modify acknowledged_at on a row that is already Acknowledged." |
| HR Policy is_active 1 → 0 with 1 Pending row | row goes to Withdrawn + audit log entry via=Deactivate | ✅ |
| Pending → Acknowledged via API (Pending row had pre-set `acknowledged_at='2020-01-01'`) | server overrides with now() | ✅ acknowledged_at = current timestamp |

---

## 5. Versioning + supersession

Source: [policy_hooks.py:118-169](../myhr/policy_hooks.py).

### Version bump (`validate_hr_policy`)

```python
if doc.has_value_changed("file"):
    doc.version = (doc.version or 1) + 1
```

Fires before save, so the persisted row reflects the new version. The `version` field is `read_only=1` in the doctype JSON — only this hook writes it.

### Supersede + reconcile (`after_save_hr_policy`)

After save, in order (post-2026-04-26 reorder per C-4):

1. **Seed at current version** (only if `is_active=1`) — for every Active Employee for whom `applies_to_employee(...)` is True, ensure a Pending PA exists at the new version. Existing rows are not touched. Done *before* supersede so the next step can JOIN-link old → new.
2. **Supersede** — if `version > 1`, raw-SQL UPDATE all PAs with `policy_version < doc.version` and `status IN (Pending, Acknowledged)` → `Superseded`. This is the bypass path mentioned in §4.
3. **Wire `superseded_by`** — JOIN-based UPDATE that backfills `superseded_by` on each Superseded row to the matching new PA's `name` (matched by `(employee, hr_policy)`). Employees who fell out of scope at the new version still get Superseded with `superseded_by=NULL` because no replacement row was seeded.

### Live verification (2026-04-26)

`POL-0567` was created with `applies_to_all=False, applicable_departments=[Operations - EDPL], OR`. Two Pending PAs (OPS-001, OPS-002) at v1. Then `file` was changed and saved:

| Stage | OPS-001 PA | OPS-002 PA |
|---|---|---|
| After create v1 | Pending v1 | Pending v1 |
| After file change → v2 | Superseded v1 + Pending v2 | Superseded v1 + Pending v2 |

✅ Both old rows superseded; both new Pending rows created at v2.

---

## 6. Reconcile triggers on Employee changes

Source: [policy_hooks.py:96-113](../myhr/policy_hooks.py).

| Trigger | Handler | Behaviour |
|---|---|---|
| `Employee.after_insert` | `reconcile_after_employee_insert` | Calls `ensure_policy_acknowledgements_for_employee(doc.name)` — seeds Pending PAs for every Active+applicable HR Policy at its current version. |
| `Employee.on_update` | `reconcile_on_employee_update` | Skips if `is_new()` (after_insert handler covers it). Else checks if any of `{status, department, designation, branch, employment_type}` changed — if so, re-runs the seed. |

**What it never does:** *delete* PAs when an employee moves out of scope. The historical fact that they acknowledged remains true. So the row count grows over a long-tenured employee's life, but never shrinks. Confirmed live (T8: SAL-002 moved into Operations → got Pending POL-0567 v2; moved back to Sales → row preserved).

**What it does for Inactive employees:** `ensure_policy_acknowledgements_for_employee` early-returns if `Employee.status != 'Active'`. Verified live (T10).

---

## 7. APIs (api.py)

All in [apps/myhr/myhr/api.py](../myhr/api.py):

| Endpoint | Caller | Purpose |
|---|---|---|
| `myhr.api.get_employee_policies` | PWA Policy Centre | Returns the calling user's `Pending + Acknowledged` PAs joined to active HR Policy. Sorts Pending first. |
| `myhr.api.get_employee_policy_history(hr_policy)` | PWA history toggle | Returns the calling user's `Superseded` rows for one policy. |
| `myhr.api.get_pending_policy_count` | PWA Home banner + Quick Link badge | `{count, blocking_count}` — count is all Pending+active; blocking_count is Pending+active+`mandatory_check_in_block=1`. |
| `myhr.api.acknowledge_policy_acknowledgement(name)` | PWA "Acknowledge" button | Idempotent on Acknowledged. Throws on Superseded / Withdrawn / inactive HR Policy. **Permission check:** caller's `user_id` must equal target's Employee, unless caller has HR Manager / System Manager. Audit fields are server-stamped by the PA controller's `validate()`, not by this endpoint. |
| `myhr.api.bulk_acknowledge_for_employee(employee, hr_policy=None)` | HR Desk action / `bench execute` | HR-only. Marks every Pending row for an employee (optionally one policy) as Acknowledged through the ORM. Skips inactive-policy rows. Returns `{acked, skipped, total}`. |
| `myhr.api.bulk_acknowledge_for_policy(hr_policy)` | HR Policy "Mark all as Acknowledged" button | HR-only. Marks every Pending row on the policy as Acknowledged across all in-scope active employees. |
| `myhr.api.force_reacknowledgement_campaign(hr_policy, reason)` | HR Policy "Force Re-acknowledgement" button | HR-only. Bumps `version` without changing the file; `reason` is required and goes into the audit log (`via='VersionBump'`). |
| `myhr.api.get_policy_coverage()` | HR coverage dashboard | HR-only. Returns one row per active policy with `total / acked / pending / withdrawn / coverage_pct`. |
| `myhr.api.get_blocking_policies` | PWA Checkin pre-flight | Returns the calling user's blocking policies (active + mandatory + Pending). Empty list ⇒ proceed. |
| `myhr.api.can_open_attendance_request` | PWA AR Quick Link | Backwards-compatible wrapper around `get_blocking_policies`. Returns `{allowed, blocking, message}`. |

### Cross-employee acknowledge guard (live verified 2026-04-26)

Marketing Exec (MKT-002) calling `acknowledge_policy_acknowledgement` against an OPS-002 Pending row throws:

```
PermissionError: You can only acknowledge your own policies.
```

✅ matches the controller code; the doctype perms alone wouldn't catch this (Employee has read-only on PA, but `ignore_permissions=True` is used inside the function — so the explicit caller check is what does the work).

---

## 8. Gate integration (Employee Checkin + Attendance Request)

The "blocking" semantic that connects HR Policy to attendance lives in [policy_gate.py](../myhr/policy_gate.py):

```python
def get_blocking_policies(employee):
    SELECT pa.hr_policy AS name, hp.policy_name, hp.file
    FROM `tabPolicy Acknowledgement` pa
    INNER JOIN `tabHR Policy` hp ON hp.name = pa.hr_policy
    WHERE pa.employee = %s
      AND pa.status = 'Pending'
      AND hp.is_active = 1
      AND hp.mandatory_check_in_block = 1
```

`assert_policies_acknowledged(employee, action_label)` throws a `Policy Acknowledgement Required` error listing `policy_name` titles (not internal IDs) when the gate fires server-side.

| Caller | Where | Bypass |
|---|---|---|
| `EmployeeCheckin.validate()` (override) | Before `super().validate()` so the gate fires before geo-distance | `device_id == AUTO_PRESENT_DEVICE` skips both gates. |
| `validate_attendance_request_policy_gate` (Attendance Request `validate`) | `myhr.employee_hooks` | Same auto-present bypass. |
| PWA pre-flight | `CheckInPanel.vue` and `Home.vue` Quick Link | Calls `get_blocking_policies` / `can_open_attendance_request`; opens `<PolicyBlockedModal />` if non-empty. |

Filters in `get_blocking_policies` confirmed live (T9):

| Setup | Expected | Live |
|---|---|---|
| Pending + active + mandatory | row returned | ✅ |
| Pending + **inactive** + mandatory | empty | ✅ |
| Pending + active + **non-mandatory** | empty | ✅ |

---

## 9. PWA Policy Centre

Source: [EmployeePolicies.vue](../myhr/frontend_changes/views/EmployeePolicies.vue), [PolicyBlockedModal.vue](../myhr/frontend_changes/components/PolicyBlockedModal.vue).

### Routes

```js
{ path: "/policies", name: "EmployeePolicies", component: EmployeePolicies.vue }
```

Wired in [router/index.js:79](../myhr/frontend_changes/router/index.js).

### Home surface

- **Pending policies banner** at the top of `Home.vue` — shown if `policyCounts.count > 0`. Red when `blocking_count > 0`, amber otherwise. Tapping it routes to `/policies`.
- **Quick Link "Policy Centre"** in the QuickLinks grid with a numeric badge equal to `policyCounts.count`.
- **AR Quick Link pre-flight** — `Home.vue:handleAttendanceRequestClick()` calls `can_open_attendance_request` first; if blocked, opens `<PolicyBlockedModal>` listing the blocking titles + PDF links + Review CTA.

### Policy Centre page (`/policies`)

- Reloads on `onIonViewWillEnter` so newly-published policies appear without manual refresh.
- One card per Pending+Acknowledged active policy, with:
  - Title + category chip + version chip (`v{n}` for v > 1) + status badge (PENDING / ACKNOWLEDGED).
  - "Required for Check-in" red chip when `mandatory_check_in_block=1`.
  - "View Policy" → opens `hp.file` in a new tab.
  - "Acknowledge" → calls `myhr.api.acknowledge_policy_acknowledgement(name)`, shows toast on success, refetches the list.
  - "History" toggle (only for `version > 1`) → calls `get_employee_policy_history(hr_policy)`, lists the user's prior-version Acknowledged rows.
- Empty state ("No policies assigned"), error state, loading state all handled.

### Bulk-acknowledge: not exposed

There is **no UI surface** for HR to bulk-ack Pending PAs (or for an employee to "ack all"). The PWA card is per-row. Desk users with HR Manager perm can flip status by hand row by row, but the state machine forbids reverting to Pending — so a "tick everyone Acked" SQL pattern (used by the demo reset) is the only practical bulk path. See CR-1.

---

## 10. Findings

Codes use the `F-PA-N` prefix to keep them distinct from Checkin's F-N findings.

| # | Finding | Status |
|---|---|---|
| **F-PA-1** | `Policy Acknowledgement.superseded_by` field exists in the JSON but is **never written**. The `after_save_hr_policy` SQL UPDATE only flips `status`; it doesn't link the old row to the new one. | **RESOLVED 2026-04-26 (C-4).** [policy_hooks.after_save_hr_policy](../myhr/policy_hooks.py) reordered: now seeds new Pending PAs at the new version FIRST, then runs the supersede UPDATE, then a JOIN-based UPDATE that backfills `superseded_by` to the matching new PA name. Employees who fell out of scope at the new version still get Superseded with NULL `superseded_by` (no replacement to link). Verified live (V-7): 10/10 v1 rows linked to their v2 successors. |
| **F-PA-2** (was **F-13** in EMPLOYEE_CHECKIN.md) | `PolicyAcknowledgement` had no state-machine guard — its controller was empty `pass`. | **RESOLVED 2026-04-26.** Added `validate()` (see §4). Verified by 7/7 scenario tests + V-3 / V-3b. |
| **F-PA-3** | Legacy `Policy Action Task` doctype is still on disk but **0 rows live** and **0 code paths read it**. | **RESOLVED 2026-04-26 (C-13).** New patch `myhr/patches/v1_4_drop_policy_action_task.py` (registered in `patches.txt`) `frappe.delete_doc`s the doctype defensively (refuses if rows exist). Source directory `apps/myhr/myhr/myhr/doctype/policy_action_task/` deleted. Verified live: `frappe.db.exists("DocType","Policy Action Task")` returns `False`. |
| **F-PA-4** | Bulk-acknowledge path was **only** the demo reset SQL. No patch, no Desk button, no console helper. | **RESOLVED 2026-04-26 (E-2).** New whitelisted endpoints `myhr.api.bulk_acknowledge_for_employee` and `myhr.api.bulk_acknowledge_for_policy` (HR-only). HR Policy form has a "Mark all as Acknowledged" custom button under HR Actions. Each row flows through the ORM so the state machine stamps `acknowledged_at` / `ip_address` and the audit log captures `via='BulkAck'`. Inactive-policy rows are skipped. Verified live: 10 Pending → 10 Acked + 10 audit log rows. |
| **F-PA-5** | `applies_to_all_employees=False` + every filter table empty → policy applies to nobody, silently. | **RESOLVED 2026-04-26 (C-12).** Server-controller `validate()` on [HRPolicy](../myhr/myhr/doctype/hr_policy/hr_policy.py) now throws "Empty policy scope" when `applies_to_all_employees=0` and all 5 filter tables are empty. Verified live (V-6). |
| **F-PA-6** | `AND` combinator across the 5 filter tables only ANDs *contributing* tables — single-populated-table `AND` is indistinguishable from `OR`. | **Documented.** Field description on `applicability_logic` already explains "must fit every filter that has rows" — keeping current semantics. Adjusting them would be a breaking change on existing scoped policies. |
| **F-PA-7** | `validate_hr_policy` bumps `version` on `has_value_changed("file")` — same physical file re-uploaded under a new URL still bumps. No content-hash check. | **Open — minor.** Not worth the complexity for current volume. |
| **F-PA-8** | Policy deletion blocked by both `on_trash_hr_policy` and `delete=0` perm. | **Cosmetic.** No action. |
| **F-PA-9** | Test data left on demo site from this audit. | **RESOLVED 2026-04-26.** Cleaned up 8 zombie test policies (POL-0567/0570/0573/0585/0596/0600-RN/0611/0622) + 25 orphan PA rows. Site back to baseline (50 Acked PAs, 5 active policies, 0 orphans). |
| **F-PA-10** (NEW from deeper test pass) | **No DB-level uniqueness on `(employee, hr_policy, policy_version)`.** `frappe.db.exists` + `insert` is racy under concurrent saves. Verified live: duplicate insert succeeded silently. | **RESOLVED 2026-04-26 (C-1).** New patch `myhr/patches/v1_3_dedupe_pa_and_add_unique_index.py` (a) dedupes existing duplicates by status rank (Acknowledged > Superseded > Pending, ties broken by earliest creation), (b) adds unique index `unique_pa_employee_policy_version` via `frappe.db.add_unique`. Verified live (V-5): duplicate insert now throws `UniqueValidationError`. |
| **F-PA-11** (NEW) | `acknowledge_policy_acknowledgement` didn't check `hp.is_active` — let employees ack rows on deactivated policies, producing semantically meaningless audit entries. | **RESOLVED 2026-04-26 (C-3).** [api.py acknowledge_policy_acknowledgement](../myhr/api.py) now early-throws if the linked HR Policy is `is_active=0`. Verified live (V-4). |
| **F-PA-12** (NEW) | `acknowledged_at` was mutable on Pending rows. HR Desk users with write perm could pre-set a future or past timestamp, then ack — silently backdating compliance. | **RESOLVED 2026-04-26 (C-5 + C-6).** Validate now: (a) on insert with `status=Pending`, force `acknowledged_at=None, ip_address=None`; (b) on Pending → Pending resaves, force them clear; (c) on Pending → Acknowledged transition, server-stamp `acknowledged_at=now()` and `ip_address=request_ip`, ignoring any client value. The Desk "type the date and flip status" path is now sealed — same audit fields whether the user goes through PWA, Desk, or any API path. Verified live (V-1, V-2, V-3, V-3b). |
| **F-PA-13** (NEW) | `mandatory_check_in_block` field description claimed it only blocked check-in, but the gate also blocks Attendance Request. HR-misleading. | **RESOLVED 2026-04-26 (C-11).** Description updated to "If checked, employees in scope cannot Employee Check-in **or submit Attendance Requests** until they acknowledge this policy. The auto-present cron path is always exempt." |
| **F-PA-14** (NEW) | `<a target="_blank">` on the View Policy file link in `EmployeePolicies.vue` had no `rel="noopener noreferrer"` — reverse-tabnabbing risk. PolicyBlockedModal already had it; surfaces inconsistent. | **RESOLVED 2026-04-26 (C-7).** Added `rel="noopener noreferrer"`. Verified live in the synced HRMS frontend file (V-8). |
| **F-PA-15** (Phase 2) | State machine bypassable via `frappe.db.set_value` / raw SQL. `track_changes` only captured ORM saves. Compliance audit could not answer "who flipped this row, when, via which path?" for SQL UPDATEs. | **RESOLVED 2026-04-26 (E-10 + C-2).** New `Policy Audit Log` doctype (append-only, all-roles read=1 / write=create=delete=0) records every transition with `from_status / to_status / via / actor / actor_ip / note`. New module `myhr.policy_audit` defines the canonical paths: `write_audit_log_for_change` (called from PA `after_insert` and `on_update`) for ORM, and `transition_pa_via_sql` (used by `after_save_hr_policy` supersede UPDATE + the deactivate-Withdraw flow) for bypass paths. `frappe.flags.policy_audit_via` lets API endpoints / bulk-ack helpers tag the entry path. Every state flip in Phase 2 verification produced a log row. |
| **F-PA-16** (Phase 2) | Stale Pending rows on deactivated policies sat in the PWA Policy Centre indefinitely showing "Pending" with no explanation; users could still tap Acknowledge on a meaningless row (closed by F-PA-11) but the row itself was never cleared. | **RESOLVED 2026-04-26 (E-4).** Added `Withdrawn` to the PA status options (terminal). When `after_save_hr_policy` runs with `is_active=0`, all currently-Pending rows transition to `Withdrawn` via the canonical SQL helper (`via='Deactivate'`). PWA queries (`get_employee_policies`, `get_pending_policy_count`, `policy_gate.get_blocking_policies`) already filter `IN ('Pending','Acknowledged')`, so Withdrawn rows naturally disappear from active surfaces. They surface in the per-policy History toggle. Backfill patch `v1_5_withdraw_pending_on_inactive_policies.py` cleans up legacy stale rows. State machine forbids `Withdrawn → anything`. |
| **F-PA-17** (Phase 2) | No proactive notification when a Pending PA was seeded; employees discovered policies by tapping the PWA. Mandatory ones could silently lock people out of check-in at 9 am the morning HR published a new policy. | **RESOLVED 2026-04-26 (E-1 + E-3).** New module `myhr.policy_notifications`. `notify_employee_of_new_pending(pa_name)` is called from every Pending-row insertion path (`ensure_policy_acknowledgements_for_employee`, `after_save_hr_policy` seed loop). Subject prefixes with `[myHR Policy]` and tags `[Required for Check-in]` for mandatory rows. Hourly cron `send_pending_policy_reminders` re-pings users with mandatory Pending rows older than 24h, deduped against Notification Log so users see at most one reminder per row per 24h cycle. Wired in `hooks.py → scheduler_events.hourly`. Verified live: seed creates 1 notification; cron skips during the dedupe window; cron sends after backdating. |
| **F-PA-18** (Phase 2) | No HR-side compliance dashboard. Could not answer "how many people have acknowledged POSH 2026?" without writing custom SQL. | **RESOLVED 2026-04-26 (E-6).** New whitelisted endpoint `myhr.api.get_policy_coverage` (HR-only). Returns one row per active policy with `total / acked / pending / withdrawn / coverage_pct` at the current version. Single rollup query, no schema change. |
| **F-PA-19** (Phase 2) | Annual policy refresh required HR to re-upload the same physical file just to bump version (UX papering over the file-change-bumps-version mechanism). | **RESOLVED 2026-04-26 (E-5).** New whitelisted endpoint `myhr.api.force_reacknowledgement_campaign(hr_policy, reason)` (HR-only). Bumps `version` directly without a file change, runs the supersede + reseed pipeline, logs `via='VersionBump'` with the reason. Surfaced in the HR Policy form as a "Force Re-acknowledgement Campaign" custom button under HR Actions. |
| **F-PA-20** (Phase 2) | `applies_to_employee` ran 5 child-table queries per call. For a 1000-employee scoped policy the seed loop was O(5000) DB calls. | **RESOLVED 2026-04-26 (C-9).** New helper `_load_policy_filters(policy_name)` reads all 5 filter tables in 5 queries once. `applies_to_employee` accepts an optional `_prefetch` arg; `after_save_hr_policy` passes the prefetch into the loop. Verified live: 100 calls without prefetch = 171ms, with prefetch = 51ms (3.4× speedup; the speedup grows linearly with employee count). |
| **F-PA-21** (Phase 2) | HR Policy `file` field accepted any extension (`.exe`, `.html`, `.js`). | **RESOLVED 2026-04-26 (C-15).** `HRPolicy.validate()` now allow-lists the extension to `{.pdf, .doc, .docx, .odt, .rtf, .txt}`. Verified live: `.exe` upload throws "Disallowed file type"; `.pdf` saves cleanly. |
| **F-PA-22** (Phase 2) | Three call sites duplicated the same PA × HR Policy join WHERE clause. Adding a filter (e.g., excluding `Withdrawn`) had to be done in three places. | **RESOLVED 2026-04-26 (C-8).** New helper `myhr.policy_hooks.query_employee_pas(employee, *, statuses, blocking_only=False, fields=None)` is the single source for PA-side queries. `policy_gate.get_blocking_policies` and `api.get_employee_policies` route through it. `api.get_pending_policy_count` keeps its custom aggregate query but follows the same WHERE conventions. |

---

## 11. Consultant-style read

### 11.1 Actor + stream map

| Actor | Stream they touch | What they do |
|---|---|---|
| **HR Manager / System Manager** | HR Policy CRUD | Create, set scope, upload/replace file (auto-bumps version), flip `is_active`, never deletes. |
| **HR Manager / System Manager** | Policy Acknowledgement | Read-all visibility. Can manually delete (perm allows). Can set status forward (Pending → Ack'd) but state machine blocks reverts. |
| **Employee (PWA)** | Policy Centre `/policies` | Sees own Pending + Acknowledged active policies. Taps Acknowledge. Optionally taps History to see prior-version receipts. |
| **Employee (Desk)** | HR Policy + Policy Acknowledgement | Read-only, both doctypes. Will rarely visit Desk; PWA is the primary surface. |
| **System (event hooks)** | HR Policy → PA seeding | `validate_hr_policy` bumps version on file change; `after_save_hr_policy` raw-SQL supersedes old PAs and seeds Pending at new version; reconcile hooks on Employee insert/update keep the matrix coherent. |
| **System (gate)** | Employee Checkin + Attendance Request validate | Reads `Policy Acknowledgement` for blocking pending rows; throws or pre-flight-blocks the user via `<PolicyBlockedModal>`. |

### 11.2 Scenario flows

| # | Trigger | User steps | Server actions | Resulting state | Friction |
|---|---|---|---|---|---|
| S1 | New employee hire | HR creates Employee record (Active) | `after_employee_insert` runs `reconcile_after_employee_insert` → `ensure_policy_acknowledgements_for_employee` | Pending PA at current version for every applicable active policy | Employee sees the badge on next PWA login. **No notification fired** — they have to discover it. |
| S2 | HR uploads new policy version | Open POL-XXXX, replace `file`, Save | `validate_hr_policy` bumps `version`. `after_save_hr_policy` raw-SQL supersedes all PAs with `version < new`. Then seeds new Pending at new version for every in-scope Active employee | All applicable employees get a fresh Pending row at v2; their old v1 row → Superseded | No outbound email/notification to employees. The PWA badge updates on next refresh. |
| S3 | HR deactivates a policy | Open POL-XXXX, untick `is_active`, Save | `after_save_hr_policy` returns early after the supersede block (no reconcile) | All existing PAs preserved as audit; gates skip the policy because of the `is_active=1` filter | Pending rows for that policy remain in the user's PWA list **but aren't blocking** anymore. They show "Pending" until the user happens to ack them (which is now meaningless). See CR-3. |
| S4 | HR retires a policy permanently | Wants to delete | `on_trash_hr_policy` throws | Forced into deactivate path (S3) | Throw message tells them to deactivate; reasonable. |
| S5 | Employee taps Acknowledge in PWA | `acknowledge_policy_acknowledgement(name)` | Permission check (caller-emp == target). State machine accepts Pending → Acknowledged. Sets `acknowledged_at=now, ip_address=request_ip`. | PA → Acknowledged; counts on Home banner + Quick Link badge update on next refetch. | None on the happy path. |
| S6 | Employee tries to ack someone else's PA | API call with `name=PA-XXX` for another emp | Caller check throws PermissionError | None | None for benign user; defends against payload-tampered API calls. |
| S7 | Employee changes department | HR saves Employee | `reconcile_on_employee_update` → seed new Pending PAs for newly-applicable policies | New Pending rows appear; old rows preserved | If the new dept has more mandatory policies, the user can be **silently locked out of checkin** until they ack. They get no proactive ping — they just discover the modal at 9am. |
| S8 | Employee leaves / status=Left | HR saves Employee | `ensure_policy_acknowledgements_for_employee` early-returns. No PAs deleted. | All PAs preserved as audit. | Existing PAs still show in the joined query for `status IN (Pending, Acknowledged)`. If the user is reactivated later, no new seeding fires until a scope field changes. See CR-4. |
| S9 | HR opens an Acknowledged PA in Desk and tries to flip it to Pending | Desk save | State machine throws | None | ✅ Compliance preserved. |
| S10 | HR moves a PA's `employee` link | Desk save | State machine throws | None | ✅. |
| S11 | Demo reset / one-time mass ack | SQL UPDATE direct on `tabPolicy Acknowledgement` | Bypasses `validate()` (SQL doesn't fire it) | All rows flip silently | This is a foot-gun: any Server Script or admin can mass-revert compliance with one query. Mitigated by `delete=0` for HR Manager on PA + state machine for ORM paths. See CR-5. |
| S12 | New HR Policy published with `applies_to_all=False` and zero filter rows | Save | `after_save_hr_policy` runs but `applies_to_employee` returns False for everyone → 0 PAs created | The policy exists, blocks no one, applies to no one | Silent. HR thinks they shipped a policy; no employee sees it. See F-PA-5 / CR-6. |

### 11.3 What's actually unnecessary

- **`Policy Action Task` doctype + directory.** Migration is done; 0 rows; 0 code paths. Drop the doctype + delete the folder. The split patch can stay (idempotent if doctype is gone). See F-PA-3.
- **`Policy Acknowledgement.superseded_by` field.** Not written by any code path. Either wire it (one extra UPDATE in the supersede SQL) or remove it from the JSON. See F-PA-1.
- **Two HR Policy desk-form effects with overlapping intent.** `before_save` confirm dialog ("once saved, this policy cannot be deleted") and the `file()` headline ("Saving will publish version N+1 of this policy"). Both fire on the desk form, in slightly different language. Pick one warning channel; today both fire and feel chatty.
- **`refresh()` indicator** "Version N" — duplicates the `version` field already shown read-only on the form. Keeping it is fine but adds nothing.

### 11.4 Recommendations

| # | Theme | Recommendation | Effort | Why |
|---|---|---|---|---|
| **CR-1** | Notifications | When `after_save_hr_policy` seeds Pending PAs (whether on a new policy, new version, or new in-scope employee), fire an in-PWA notification or email to the affected employees. Today they discover pending rows by tapping the app. For mandatory-check-in policies this means people show up to work and can't punch in cold. | M | Closes the "silent block" failure mode in S2/S7. |
| **CR-2** | HR ergonomics | Add a "Bulk acknowledge for employee" Desk action (HR Manager only) on `Employee` and on `HR Policy`. Backed by a `bulk_ack_for_employee(employee)` / `bulk_ack_for_policy(policy)` helper that flips Pending → Acknowledged through the ORM (so the state machine stamps `acknowledged_at`). Closes F-PA-4. | M | The reset script's `UPDATE … SET status='Acknowledged'` is the only bulk-ack path today, and it bypasses every audit field. |
| **CR-3** | UX | When a policy goes inactive, mark its still-Pending PAs as a terminal state (e.g., introduce `Status='Withdrawn'`) instead of leaving them sitting Pending. Today the PWA still shows them as "Pending" indefinitely; an employee tapping Acknowledge on a withdrawn policy would update the audit row meaningfully but the gate already ignores them. | M | Cleans up S3's stale Pending rows. |
| **CR-4** | Lifecycle | On Employee status flip Active ↔ Inactive, treat reactivation as an `after_insert`-equivalent for reconcile purposes — re-seed any policies that became applicable while they were out (today only scope-field changes trigger reconcile, status doesn't). Specifically: in `reconcile_on_employee_update` add `status` to the watched set (it's already in `scope_fields`!) and verify the `status='Active'` short-circuit in `ensure_policy_acknowledgements_for_employee` doesn't no-op a returning employee. ✅ verified: `status` *is* in `scope_fields` → already handled. So S8 reactivation does work. **Downgrade: this is just a documentation point, not a code change.** | S | Verified live. Documenting closes a confusing gap. |
| **CR-5** | Audit | Add a `before_change` trigger on the `tabPolicy Acknowledgement` table at the DB level (or a wrapping `frappe.db.sql` interceptor in `myhr`) that logs every status flip — incl. the SQL bypass. Or, formalise the supersede path as a dedicated `myhr.policy_hooks.supersede_acknowledgement(pa_name, by_pa_name)` ORM helper that explicitly calls `db.set_value` with no validate, and write to an audit log table. | L | Compliance audits will ask "who flipped this row, when, why?" and today the only evidence is `track_changes=1` on the doctype which doesn't capture raw-SQL paths. |
| **CR-6** | UX (Desk) | Add a `validate()` (server controller) on HR Policy that throws if `applies_to_all_employees=0` AND zero filter rows total. Closes F-PA-5. | XS | Single-line guard; saves HR from publishing dead policies. |
| **CR-7** | Schema cleanup | Drop `Policy Action Task` doctype + directory; remove `Policy Acknowledgement.superseded_by` (or wire it). | XS | Closes F-PA-1, F-PA-3. |
| **CR-8** | Visibility | Add a "Coverage" badge on the HR Policy desk list — shows `<acked>/<total>` PAs at the current version. Drives at-a-glance compliance reporting. Cheap rollup query. | S | HR has no current view of "how many people have acknowledged POSH 2026." Today they'd open Policy Acknowledgement list and filter — possible but un-discoverable. |
| **CR-9** | Approval workflow | Today there's no review step — HR uploads a file and it's live. Consider requiring `HR Manager` to publish (a `published` checkbox + `published_on` timestamp) to keep an HR User from accidentally pushing a draft to 200 inboxes. Optional. | M | Common ask; not urgent for the demo. |
| **CR-10** | API hardening | `acknowledge_policy_acknowledgement` uses `ignore_permissions=True` after a manual caller check. If the manual check ever has a bug, doctype perms don't catch it. Consider replacing with explicit `frappe.has_permission("Policy Acknowledgement", "write", pa)` so the doctype perm is the second line of defence. | S | Defence in depth. |

### 11.5 Top-5 ranked

| Rank | Item | Why now |
|---|---|---|
| 1 | **CR-1 Notifications** | Highest user-visible impact. Mandatory-check-in policies will silently lock people out at 9am unless they get pinged. |
| 2 | **CR-2 Bulk-ack Desk action** | Removes the SQL foot-gun (CR-5) for the most common bulk path. Closes F-PA-4. Without this, HR onboarding for a new mandatory policy is "tap 200 times in PWA" or "ask sysadmin to write SQL". |
| 3 | **CR-6 Empty-scope guard** | One-line fix, prevents publishing a dead policy. F-PA-5. |
| 4 | **CR-7 Drop Policy Action Task + decide on superseded_by** | Schema cleanup. Closes F-PA-1, F-PA-3. Makes the doctype set legible to a future reader. |
| 5 | **CR-8 Coverage badge** | Cheap; fills an obvious HR ergonomics gap. |
