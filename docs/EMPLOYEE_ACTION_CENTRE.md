# Employee Action Centre — Audit & Spec

> **Decision log (2026-04-25)**:
> - **Policy rejection is not a feature.** Employees can only Acknowledge or leave Pending. (F-2 closed.)
> - **Master status engine unified** — single Python writer on the doctype class. (F-1, F-7, F-8, F-9 auto-resolved.)
> - **HR Policy will become non-deletable** (delete permission stripped + `is_active` flag + first-save warning modal). This makes orphan-policy-row cleanup (F-11) moot — dropped from scope.
> - **Doctype name stays as `Employee Action Centre`** (rename to `Documents Centre` was considered and **cancelled** — the existing name is accurate enough, parallels "Policy Centre" cleanly, and avoids a ~30-file rename + DB-level table rename). UI label is "Action Centre" (a one-line tweak if it ever needs to change).
> - **Policies have moved out** of this doctype into a standalone `Policy Acknowledgement` doctype, with rule-based scoping on `HR Policy` (CR-15/16/17). Phase 2 shipped.
> - **F-5 (permlevel-1 RW for Employee role)** closed with API ownership/whitelist hardening — see findings table.

> Companion to `EMPLOYEE_DIRECTORY.md`. Same QA pattern: spec the system as it is, mark findings, fix the broken parts, leave the trade-offs documented.

Scope: the Employee Action Centre (AC) is the per-employee onboarding hub — mandatory KYC docs (Aadhar/PAN/Education), previous-employer history (5 slots, with Employer 1 having a nested set of payslips/letters), and a policy-acknowledgement queue that **gates attendance check-ins**. Each doc and each policy carries its own status; an aggregate "master" status sits on the parent.

---

## 1. Where the logic lives

| Concern | File |
|---|---|
| Parent doctype schema | `apps/myhr/myhr/myhr/doctype/employee_action_centre/employee_action_centre.json` |
| Parent server class | `.../employee_action_centre.py` |
| Parent desk script | `.../employee_action_centre.js` |
| Policy child doctype | `.../doctype/policy_action_task/policy_action_task.json` |
| Activity log child (NEW, unused) | `.../doctype/action_centre_activity/action_centre_activity.json` |
| HR Policy doctype | `.../doctype/hr_policy/hr_policy.json` |
| Lifecycle hooks | `apps/myhr/myhr/employee_hooks.py` (`_ensure_action_centre`, `validate_checkin_action_centre`) |
| Hook wiring | `apps/myhr/myhr/hooks.py` |
| API endpoints | `apps/myhr/myhr/api.py` |
| PWA page | `apps/myhr/myhr/frontend_changes/views/EmployeeActionCentre.vue` |
| Pre-existing logic doc | `apps/myhr/myhr/EMPLOYEE_ACTION_CENTRE_LOGIC.md` |

> Note: there are **two** docs now — the older `EMPLOYEE_ACTION_CENTRE_LOGIC.md` lives inside the `myhr` package directory and reads as a how-it-works writeup. This doc (`docs/EMPLOYEE_ACTION_CENTRE.md`) is the audit/spec, intended to drive changes. Once findings are folded in, the older doc should be deleted to avoid drift.

---

## 2. Data model

### 2.1 Parent: `Employee Action Centre`

- **Identity**: `employee` (Link, reqd), `employee_name` (fetched), name = `AC-{####}`
- **Master status** (`status`, permlevel 1, read-only):
  `Pending`, `In Progress`, `To be Reviewed`, `Accepted`, `Action Required`
- **Mandatory docs** (×3 — Aadhar / PAN / Education), each with:
  - `<prefix>_upload` (Attach), `<prefix>_is_na` (Check)
  - `<prefix>_approval_status` (Select, permlevel 1): `Pending`, `Awaiting HR`, `Accepted`, `Rejected`
  - `<prefix>_remarks` (Small Text, permlevel 1)
- **Employer history** (×5 slots), each with:
  - `employer_N_name`, `employer_N_from`, `employer_N_till`
  - `employer_N_doc` (Attach), `employer_N_is_na`
  - `employer_N_approval_status`, `employer_N_remarks` (permlevel 1)
- **Employer 1 nested docs** (most recent employer breakup, ×6):
  `employer_1_offer_letter`, `employer_1_increment_letter`, `employer_1_payslip_last_month`, `employer_1_payslip_last_to_last_month`, `employer_1_payslip_month_before_that`, `employer_1_relieving_or_resignation`. Each has `_doc`, `_approval_status`, `_remarks`. Mandatory flag is in code only (`EMPLOYER_1_DOC_FIELDS` in `api.py`); only `increment_letter` is optional.
- **Children**:
  - `policies` (Table → Policy Action Task)
  - `activity_logs` (Table → Action Centre Activity) — **see Finding F-3, dead**

### 2.2 Child: `Policy Action Task`

- `hr_policy` (Link → HR Policy, read-only)
- `status` (Select, options = `Pending\nAcknowledged`) — **see Finding F-2: backend writes "Rejected" which is not in options**
- `acknowledged_at`, `ip_address`

### 2.3 Child: `Action Centre Activity` (NEW, 2026-04-20)

- `posted_on`, `user`, `action` (Select with 7 options), `details`
- Created by the recent rsync, **never written to** anywhere — dead doctype today (F-3).

### 2.4 `HR Policy`

- `policy_name`, `category` (Leave/POSH/Gratuity/General), `acknowledgement_required` (default 1, **never read anywhere** — F-4), `file` (reqd), `description`, `mandatory_check_in_block` (the field that actually drives the gate).

### 2.5 Permissions

- System Manager + HR Manager: full RW including permlevel 1
- Employee: full RW + `if_owner` on permlevel 0; permlevel 1 is **RW** for Employee too — meaning the row's HR-only fields are technically writable by the employee at the doctype level. The desk JS adds a client-side lock and the API uses a `status_map` to coerce values, but the permission model itself is permissive (F-5).

---

## 3. Status state machines

> **Engine refactor (resolved)**: master status is now computed by a single Python method, `EmployeeActionCentre._compute_master_status()`, called from `validate()` on every save. The desk JS no longer writes status. `sync_master_status` and the ghost-sweep workaround in `api.py` are deleted. `AC_DOCUMENT_ROWS` on the doctype module is the **single source of truth** for the row list (prefix, label, mandatory, has_na, file_suffix). Findings F-1, F-7, F-8, F-9 are auto-resolved by this refactor.

This is the heart of what was asked. There are still **two independent state machines** (per-doc HR status, and policy status), with master status now derived purely from those.

### 3.1 Per-document HR status (×11 docs: 3 mandatory + 5 employer slots + 6 employer-1 split docs)

```
              ┌──────────────────────────────────────────────────────────────┐
              │                      Pending                                 │
              │  (no file, not N/A; or wiped via reset_action_centre_field)  │
              └───┬───────────────────────────────────────────────┬──────────┘
                  │ employee uploads file                          │ employee toggles N/A=1
                  │ (update_action_centre_field)                   │
                  ▼                                                ▼
              ┌──────────────────────────────────────────────────────────────┐
              │                    Awaiting HR                               │
              └───┬─────────────────────────────────┬────────────────────────┘
                  │ HR sets Accepted                │ HR sets Rejected
                  ▼                                 ▼
              ┌─────────────────┐               ┌──────────────────────────┐
              │    Accepted     │               │        Rejected          │
              │  (terminal-ish) │               │  (employee re-uploads →  │
              └─────────────────┘               │   Awaiting HR via        │
                                                │   reupload_document)     │
                                                └──────────────────────────┘
```

**Writers**:
- Employee → `update_action_centre_field` (auto-promotes Pending/Rejected → Awaiting HR when a file or N/A is set; `sync_master_status` then sweeps for "ghost Awaiting HR" rows that have no file/N/A and downgrades them back to Pending)
- Employee → `reupload_document` (forces Awaiting HR + clears remarks + writes a Comment for history)
- Employee → `reset_action_centre_field` (forces Pending, wipes file/N/A/remarks)
- HR → desk form (free-text Select edit; client JS blocks "Accepted" if no file and not N/A; **no equivalent server guard** — F-6)

### 3.2 Policy status (Policy Action Task)

```
   Pending  ─── acknowledge_policy ───▶  Acknowledged  (terminal)
        │
        └────── reject_policy ───────▶  Rejected (NOT in Select options — F-2)
```

The frontend only ever calls `acknowledge_policy`. `reject_policy` is unreachable from the PWA but exists on the server; it writes a status string that is not in the doctype's allowed options. The desk form has no UI for it either.

### 3.3 Master status on the parent (`Employee Action Centre.status`)

**One writer**: `EmployeeActionCentre._compute_master_status()`, called from `validate()`. Rules (top-down, first match wins):

| Verdict | Condition |
|---|---|
| `Action Required` | any row's HR status is `Rejected` |
| `Accepted` | every mandatory row is `Accepted` AND every uploaded optional row is `Accepted` |
| `To be Reviewed` | every mandatory row has file-or-N/A AND ≥1 row is `Awaiting HR` AND no row is `Rejected` |
| `In Progress` | any row has been touched (file/N-A set, or status moved off Pending) |
| `Pending` | nothing touched |

A separate sweep (`_sweep_ghost_statuses`) runs first to flip per-row Pending↔Awaiting-HR based on data presence; HR's terminal verdicts (Accepted/Rejected) are never auto-flipped.

```
    Pending  ──┐
               │ employee uploads anything
               ▼
    In Progress  ──┐
                   │ Aadhar+PAN+Edu all uploaded/N-A'd
                   ▼
    To be Reviewed  ──┐
                      │ HR reviews (desk only)
            ┌─────────┼─────────┐
            ▼                   ▼
       Accepted          Action Required
       (all HR             (any Rejected)
        statuses              │
        Accepted)             │ employee re-uploads
                              ▼
                        back to Awaiting HR rows
                        (master stays "Action Required"
                         until HR re-validates — F-8)
```

> **Permlevel trap**: `status` is permlevel 1, read-only. Only HR-level perms can write it from the desk. The API runs with `ignore_permissions=True` so it always wins. Desk-side JS calls `frm.set_value("status", ...)` which goes through the permission check — meaning the non-HR JS branch (`set_value("status", "To be Reviewed")`) **silently fails for employees on the desk**. It works in the PWA only because the PWA goes through the API. (F-9)

---

## 4. Lifecycle

1. **Employee insert/update** → `_ensure_action_centre(doc)`:
   - skips when `custom_add_to_action_centre` is unticked (default 1)
   - creates AC row if not existing
   - shares the doc with `doc.user_id` (write=1, share=0) — **only on first creation**, so a later `set_user_id` change doesn't get a share (F-10)
2. **AC validate** → `_sync_employee_name()` + `_ensure_policy_rows()`:
   - on every save, append a child row for any `HR Policy` not already linked. **Never removes** rows for deleted policies (F-11). On many saves with a churning policy list, you accumulate orphan rows pointing at non-existent policies.
3. **Employee Checkin validate** → `validate_checkin_action_centre`:
   - skips device `myHR Auto`
   - blocks check-in if any policy with `mandatory_check_in_block=1` is not Acknowledged
   - **does not check document statuses at all** — KYC can be "Action Required" and check-in still works as long as policies are acknowledged.

---

## 5. PWA behaviour summary

- Loads via `myhr.api.get_employee_action_centre` (session-user → Employee → AC)
- Three sections: Required Documents, Employment History (Employer 1 expandable with nested docs), Policy Acknowledgements
- Upload flow: file → File doctype → `update_action_centre_field` (or `reupload_document` if row was Rejected/has prior history)
- `is_na` toggle: writes via `update_action_centre_field`, then optimistically updates UI status to "Awaiting HR" — **but the server's `update_action_centre_field` only promotes when the value is truthy and the field is in `status_map`**; setting `is_na=1` when a file already exists doesn't clear the file (F-12)
- "Clear" calls `reset_action_centre_field` which wipes file/N-A/status/remarks atomically.
- `Acknowledge` button → `acknowledge_policy`. There is no Reject UI (F-13).
- Policy "Rejected" branch is rendered (red badge "Declined") but unreachable in current flow.
- The header status pill checks `acData.status === 'Completed'` — **`Completed` is not a valid master status value**, so the pill is always orange (F-14).

---

## 6. Findings — corruption, dead code, design issues

### Bugs / dead code

| # | Severity | Finding |
|---|---|---|
| F-1 | ✅ Resolved | `status_map` and the entire `update_action_centre_field` mapping logic are gone — the engine refactor moved per-row status promotion into `_sweep_ghost_statuses` which iterates `AC_DOCUMENT_ROWS` (no employer_1 ghost key exists). |
| F-2 | ✅ Resolved | **Decision: policy rejection is not a feature.** Employees can only Acknowledge or leave Pending. Resolved by: deleting `reject_policy` endpoint, deleting dead `policy_action` branch in `update_action_centre_field`, removing `row.remarks = ""` (no `remarks` field on Policy Action Task), stripping the Rejected/Declined branches from PWA Policy section. Read-only protections on the child table already prevent un-acknowledging once signed. |
| F-3 | ✅ Resolved | `log_activity(doc, action, details)` helper added on the doctype module. Wired into every mutation path: `update_action_centre_field` (classified as Document Uploaded / Cleared / HR Status Updated / Field Updated), `reupload_document` (Document Reuploaded with old status + remarks in details), `reset_action_centre_field` (Document Cleared), `acknowledge_policy` (Policy Acknowledged with policy id). The legacy Comment-as-history in `reupload_document` was removed — single source of truth. Doctype Select options trimmed: `Document Uploaded\|Document Reuploaded\|Document Cleared\|HR Status Updated\|Policy Acknowledged\|Field Updated`. |
| F-4 | Med | **`HR Policy.acknowledgement_required` (default 1) is read by no code.** The actual gate is `mandatory_check_in_block`. The field is misleading — either delete it or wire it to control whether a child row is appended in `_ensure_policy_rows`. |
| F-5 | ✅ Resolved | (1) Removed `write: 1` from the Employee permlevel-1 row in the doctype JSON — `frappe.client.set_value` from a browser console is now blocked at the framework level. (2) Added explicit field whitelist + ownership check on the API endpoints (`update_action_centre_field`, `bulk_update_action_centre_fields`, `reupload_document`, `reset_action_centre_field`, `submit_action_centre`). Non-HR callers can only mutate `*_upload`/`*_doc`/`*_is_na`/employer-metadata fields, and only on their own AC. (3) `acknowledge_policy_acknowledgement` now also checks the row belongs to the calling user — closes a related cross-employee privacy hole found while fixing F-5. **Verified live** with 5/5 attack vectors blocked: HR-only field write blocked, cross-employee AC write blocked, cross-employee policy ack blocked, bulk update with smuggled forbidden field blocked, legitimate self-write still works. |
| F-6 | ✅ Resolved | Added `_guard_accepted_rows_have_data` to the doctype's validate chain. For every row whose status is `Accepted`, the guard requires either a file or `_is_na=1`. Throws on violation. Mirrors the existing desk-JS guard so script-level patches can't bypass it. |
| F-7 | ✅ Resolved | `_compute_master_status` consults `AC_DOCUMENT_ROWS` directly — Employer 1 split docs participate in the calc with their correct mandatory flags (offer letter / payslips / relieving = mandatory; increment letter = optional). |
| F-8 | ✅ Resolved | Re-upload triggers `validate()` → `_compute_master_status()`; once no row is Rejected, the parent drops out of "Action Required" automatically. |
| F-9 | ✅ Resolved | Desk JS no longer writes status — server is the only writer. The permlevel-1 race is gone. |
| F-10 | Low | Re-share on Employee `user_id` change: `_ensure_action_centre` only inserts the share when first creating the AC. If the linked user is later replaced, the new user has no share. |
| F-11 | 🚫 Dropped | Mooted by the decision to make HR Policy non-deletable (Phase 2 / CR-16). Orphans cannot exist if policies cannot be deleted. |
| F-12 | ✅ Resolved | `_enforce_data_invariants` runs in validate before the sweep: if `<prefix>_is_na=1`, the file field is wiped in the same save. N/A wins on conflict. PWA's optimistic UI was already correct; the bug only existed for server-script callers. |
| F-13 | Low | No Reject UI for policies in the PWA. |
| F-14 | ✅ Resolved | PWA header pill now compares `acData.status === 'Accepted'`. |
| F-15 | ✅ Resolved (auto) | The "Portal" fallback string lived inside the `policy_action` branch deleted in F-2. Only `acknowledge_policy` writes IP now, and it consistently uses `frappe.local.request_ip or ""`. |

### Dead code to delete

- `_derive_employer_1_status` is computed in `get_employee_action_centre` and returned as `employer_1.status` for the PWA header. It is never persisted. The PWA uses it for badge colour. Fine — but it diverges from `HR_DOC_CHECKS` / `sync_master_status`, making it a third opinion on Employer 1 status.
- `reject_policy` (F-2 — until UI exists)
- `HR Policy.acknowledgement_required` (F-4)
- `Action Centre Activity` doctype + `activity_logs` field (F-3 — until populated)

---

## 7. Critical / contrarian thinking on design

This is the part you asked for. The current design works for the happy path but is structurally fragile in a way that will keep generating bugs. Three big issues:

### 7.1 Three-headed status writer is the root cause of half the bugs

The master status is computed by:
- `sync_master_status` in `api.py` (knows about Aadhar/PAN/Education only)
- non-HR branch of desk JS (knows trio + sentinel)
- HR branch of desk JS (knows all 13 doc rows but ignores Employer 1 nested mandatory flags)

There is **no single source of truth**. Adding a new mandatory document means editing all three places. Forgetting one (you will) gives drift. The "ghost Awaiting HR" sweep in `sync_master_status` is itself a workaround for the fact that other writers can leave the doc in inconsistent states.

**Contrarian take**: master status should not be a stored field at all. It should be a **derived property** computed in one place — a Python `@property` on the doctype class, called by the API and by a single, thin desk-form JS call. Once derived, persist it on `validate()` if you need to filter on it. Today, the field is permlevel-1 read-only, set by three writers, and the only consumers are display badges that could just as easily read the underlying rows.

If you want it stored for reporting/filtering, do it once in `EmployeeActionCentre.validate()`:
```python
def validate(self):
    self._sync_employee_name()
    self._ensure_policy_rows()
    self.status = self._compute_master_status()  # ONE function, all rules here
```
Then delete `sync_master_status` from `api.py` and the JS branches. `update_action_centre_field` already calls `doc.save(...)` after every patch, so `validate()` runs and recomputes. Net code drops by ~80 lines.

### 7.2 The wide schema is the bigger structural mistake

The doctype has ~80 fields. Adding a new required document = schema migration + JSON + desk JS array + API status_map + PWA section. Removing one is worse. Look at Employer 1: it has 6 doc-prefix triplets (`_doc`, `_approval_status`, `_remarks`) blown out as flat fields. That's 18 fields just for one employer's split docs. Employer 2–5 use a single doc each, so the design is inconsistent within itself.

**Contrarian take**: this should be a child table, not flat fields.

```
Employee Action Centre
├── employee, employee_name, status
├── documents (child: AC Document Item)
│     fields: doc_type (Select: aadhar / pan / education / employer_1_offer_letter / ...),
│             file, is_na, hr_status, remarks, employer_slot (1..5, null for personal)
├── policies (child: Policy Action Task)  -- already exists
└── activity_logs (child: Action Centre Activity)  -- already exists, just empty
```

Adding a new mandatory doc becomes "insert a row in a config table" instead of a schema migration. The PWA renders a list, the API iterates a list, master status iterates a list. `HR_DOC_CHECKS` and `EMPLOYER_1_DOC_FIELDS` and `status_map` collapse into a single child-table query.

This is a bigger change and probably out of scope for the audit, but it's the root reason the codebase has three lookup tables (`HR_DOC_CHECKS` in JS, `EMPLOYER_1_DOC_FIELDS` in py, `status_map` in py) that all encode the same field-list relationship.

### 7.3 The check-in gate scope is too narrow / too wide depending on intent

Today: check-in is blocked iff any policy with `mandatory_check_in_block=1` is unacknowledged. Documents are not checked at all.

Two failure modes:
- **Too narrow**: someone with `Action Required` Aadhar (HR rejected it) can still check in indefinitely. If the goal is "compliance gate before workday starts", documents matter.
- **Too wide**: tying the check-in workflow to the policy-acknowledgement workflow couples two separate concerns. A new mandatory policy added on a Tuesday morning blocks every employee from checking in until they read the PDF. That's fine if intentional, but `_ensure_policy_rows` makes it implicit — every save of the AC doc auto-attaches every policy.

**Contrarian take**: split the gate into a configurable rule set. `HR Policy.mandatory_check_in_block` is fine but only one axis. Add `EmployeeActionCentre.required_for_checkin = (any_rejected_doc | unacknowledged_mandatory_policy | both)` as a system setting. And rate-limit the gate — block once per session with a "you have 3 days to comply" grace, not every check-in.

This is a policy decision, not a code decision — but the current code locks you into one answer.

### 7.4 Smaller design smells

- **`employer_1_name` as a sentinel for "user has started filling employers"** in the non-HR validate JS — abusing a data field as a signal. Use a real `last_modified_by_employee_at` or just check `In Progress` from a derived state.
- **Comments doctype as audit trail** in `reupload_document` — but only there. Either commit to Comment-as-audit (and write Comments from acknowledge/reject/reset/N-A as well) or commit to `Action Centre Activity`. Don't have two audit systems where one is empty.
- **`if_owner` permission on Employee role + share on user_id** — redundant. Either trust `if_owner` matching (Employee.user_id == AC.owner) or share. Currently it's both, and `_ensure_action_centre` runs `insert(ignore_permissions=True)` so the owner is set to whoever happens to be saving the Employee record (often Administrator), making `if_owner` meaningless. The share is what actually grants access. Document this and drop the `if_owner` permission, or set `ac.owner = user_id` explicitly on insert.
- **N/A vs file as mutually exclusive — but enforced only in the PWA**. The schema allows both to be set; nothing on the server checks. Add a `validate()` rule on the parent: `if file and is_na: raise`.
- **`HR_DOC_CHECKS` + `EMPLOYER_1_DOC_FIELDS` + `status_map` are three encodings of the same relationship**. Pick one source of truth. With the child-table refactor this disappears entirely.

---

## 8. Proposed fix plan (in priority order)

### Phase 1 — without changing schema (cheap wins)

1. **F-3** — write `Action Centre Activity` rows from `update_action_centre_field`, `reupload_document`, `reset_action_centre_field`, `acknowledge_policy`. Single helper `_log_activity(doc, action, details)`.
2. **F-2** — add `Rejected` to `Policy Action Task.status` options (or delete `reject_policy` until UI exists). My recommendation: add it now since the PWA renders the Declined badge already.
3. **F-6** — server guard: in `update_action_centre_field`, if the field is an `*_approval_status` and the new value is `Accepted`, verify the corresponding `_upload`/`_doc` is set or `_is_na=1`. Reject otherwise.
4. **F-8** — when re-upload happens, recompute master status: if no rows are `Rejected`, drop `Action Required` and recompute (`Awaiting HR` rows present → `To be Reviewed` if all mandatory done, else `In Progress`).
5. **F-11** — in `_ensure_policy_rows`, also remove rows whose `hr_policy` no longer exists.
6. **F-14** — fix the PWA header pill comparison (`Accepted` not `Completed`).
7. **F-12** — in `update_action_centre_field`, if `fieldname == '<prefix>_is_na' and value == 1`, clear `<prefix>_(upload|doc)` in the same transaction.
8. **F-15** — pick one `request_ip` fallback string and use it everywhere.

### Phase 2 — single source of truth for status

9. Move master-status calc to `EmployeeActionCentre._compute_master_status()` on the Python class. Delete `sync_master_status` from `api.py`. Replace desk JS validate branches with a no-op (or a refresh trigger that re-reads `doc.status` after save).
10. Audit the three encodings (`HR_DOC_CHECKS`, `EMPLOYER_1_DOC_FIELDS`, `status_map`) and unify into one Python list with a `(prefix, label, mandatory, has_na)` tuple, exposed to JS via `frappe.boot` or a whitelisted endpoint.

### Phase 3 — schema (only if phase 1+2 expose the pain)

11. Migrate `Aadhar/PAN/Education + 5 employers + 6 employer-1 split docs` flat fields → `documents` child table with a backfill patch, similar to the directory backfill we just did.
12. Strip permlevel 1 RW from Employee role; rely on whitelisted endpoints for HR-only mutation.

### Phase 2 — Policy split shipped 2026-04-25 (round 4)

The biggest architectural change in this audit. **Policies are no longer part of Employee Action Centre.** They live in a standalone `Policy Acknowledgement` doctype with rule-based scoping on `HR Policy`.

#### New doctypes
- **`Policy Acknowledgement`** — one row per `(employee, hr_policy, version)`. Status: Pending / Acknowledged / Superseded. Holds `acknowledged_at` + `ip_address`. Read-only after acknowledgement.
- **5 child doctypes for HR Policy filter tables**: `Policy Filter Department`, `Policy Filter Designation`, `Policy Filter Branch`, `Policy Filter Employment Type`, `Policy Filter Employee`.

#### HR Policy schema additions
- `is_active` (default 1) — uncheck to retire a policy. Inactive policies don't apply to new employees and are skipped by the check-in gate; existing acknowledgements stay.
- `version` (default 1, read-only) — auto-incremented when `file` changes. Existing acks at the old version flip to `Superseded`; matching employees get fresh Pending rows at the new version.
- `applies_to_all_employees` (default 1) — when unchecked, scope is computed from the filter tables.
- `applicability_logic` (OR / AND, default OR) — combines the filter tables.
- 5 filter tables: `applicable_departments`, `applicable_designations`, `applicable_branches`, `applicable_employment_types`, `applicable_employees` (manual override).
- **Delete permission stripped** for HR Manager + System Manager (only Administrator can delete via console). Deletion attempts throw with a "Use Mark Inactive" message.
- Removed dead `acknowledgement_required` field (F-4 — was never read).
- Desk JS shows a first-save modal warning that the policy is permanent.

#### Server hooks (`policy_hooks.py`)
- `applies_to_employee(policy, employee)` — single source of truth for scoping.
- `ensure_policy_acknowledgements_for_employee(employee)` — creates Pending rows for every applicable active policy.
- `reconcile_after_employee_insert` — wired to Employee `after_insert` (replaces the AC's lazy `_ensure_policy_rows`).
- `reconcile_on_employee_update` — fires only when scope-relevant fields (`status`, `department`, `designation`, `branch`, `employment_type`) change. Existing acks are never wiped — newly-applicable policies get new rows; newly-non-applicable policies leave their historical rows alone (audit preserved).
- `validate_hr_policy` — bumps `version` when `file` changes.
- `after_save_hr_policy` (wired as `on_update`) — supersedes old PA rows + creates fresh Pending rows for matching employees at the new version.
- `on_trash_hr_policy` — blocks deletion.

#### Action Centre changes
- `policies` child table removed from doctype field_order. `_ensure_policy_rows` deleted.
- `_notify_hr_on_completion` no longer checks policies (they're independent now). Notification fires purely on the document Submit transition.
- `acknowledge_policy` API endpoint removed (replaced by `acknowledge_policy_acknowledgement`).
- `get_employee_action_centre` no longer returns a `policies` block.

#### Check-in gate (`validate_checkin_action_centre`)
Now reads from `Policy Acknowledgement` directly via SQL. Joins to `HR Policy` for `is_active=1` and `mandatory_check_in_block=1`. Throws "Check-in blocked" listing pending policies.

#### `can_open_attendance_request` API
Same SQL join shape, used by the PWA's attendance request gate.

#### New APIs
- `get_employee_policies()` — returns the session user's pending + acknowledged rows with policy metadata.
- `get_employee_policy_history(hr_policy)` — returns Superseded rows for the "View history" UI.
- `get_pending_policy_count()` — `{count, blocking_count}` for the home banner badge.
- `acknowledge_policy_acknowledgement(name)` — single endpoint to acknowledge.

#### PWA changes
- **New page `/policies`** (`EmployeePolicies.vue`) — lists pending + acknowledged policies grouped by status, with category + "Required for Check-in" + version badges. Acknowledge button per Pending row. "View History" button reveals previously-acknowledged versions inline. Sticky red banner at top if any blocking policies are pending.
- **Home page banner** — appears when employee has unacknowledged policies. Red variant if any are blocking. Tap → opens `/policies`.
- **Home Quick Links** — new "HR Policies" tile with pending-count badge.
- **Action Centre page** — Policy section completely removed. Action Centre header `expandedSections.policies` reactive entry removed.

#### Migration patch (`v1_1_split_policy_acknowledgement.py`)
- Defaults `version=1`, `is_active=1`, `applies_to_all_employees=1`, `applicability_logic=OR` on every existing HR Policy.
- For every legacy `Policy Action Task` child row in any AC, creates an equivalent `Policy Acknowledgement` (same status/timestamp/IP). Idempotent — re-running creates no duplicates.
- Old `Policy Action Task` rows are NOT deleted from the DB; the doctype is left in place as a dormant historical record. A future patch can clean up.

#### Live verification (smoke test, all passing)
| Assertion | Result |
|---|---|
| `applies_to_employee` returns True for `applies_to_all_employees=1` | ✅ |
| `ensure_policy_acknowledgements_for_employee` creates Pending rows | ✅ |
| Acknowledge → status flips to Acknowledged | ✅ |
| File change → version bump → 15 rows superseded + 111 new Pending rows at v6 | ✅ |
| Delete HR Policy → blocked with "cannot be deleted" error | ✅ |
| Pending count query matches actual data | ✅ |
| Migration: 49 Policy Acknowledgement rows backfilled from legacy AC.policies | ✅ |

#### Rename — cancelled (2026-04-25)
The rename `Employee Action Centre` → `Documents Centre` was considered then **cancelled**. Doctype name and PWA label both stay as Action Centre. Parallels "Policy Centre" naming, avoids a high-blast-radius rename, no functional cost. If the UI label ever needs to change, it's a one-line tweak in `EmployeeActionCentre.vue` and the Home tile.

### Submit gate (decided + shipped 2026-04-25, round 3)

- **Auto-save stays.** Every PWA action persists immediately. There is no manual Save button — the only decisive action is **Submit**.
- **New status `Ready to Submit`** added to the master status enum. Comes between `In Progress` and `To be Reviewed`. Means: every mandatory row has file/N-A but the employee hasn't tapped Submit yet.
- **Two new fields on AC**: `submitted_for_review` (Check, default 0) + `submitted_on` (Datetime). Both read-only.
- **New endpoint `submit_action_centre(name)`** — validates current status is `Ready to Submit`, sets the flags, saves. The save flips master status to `To be Reviewed` and fires `_notify_hr_on_completion`.
- **HR notification trigger moved**: now fires only on the Submit transition, never on auto-completion. HR doesn't get pinged when the employee hits the threshold; only when they explicitly submit.
- **Lock-after-Submit**: `_guard_locked_rows_immutable_for_employee` (renamed from `_guard_accepted_rows_immutable_for_employee`) now blocks the employee from mutating any row that's NOT currently Rejected after submission. Rejected rows remain replaceable. HR Manager / System Manager are exempt.
- **PWA**:
  - Sticky bottom bar with **Submit for Review** button — only visible when `acData.status === 'Ready to Submit'`
  - Modal confirmation showing files-uploaded + N-A counts + "you can re-upload only if HR rejects" disclaimer
  - Success animation (green check + "HR has been notified") before reload
  - State banners at top of AC: Ready to Submit (amber), Submitted (blue), Action Required (red), Verified by HR (green)
  - Per-row buttons collapsed via `isDocRowLocked(row)` and updated `isEmployerCardLocked(emp)` — verified rows show only View; post-submit rows show only View; Rejected rows still show Replace File
- **CR-1 (bulk update)** shipped alongside: `bulk_update_action_centre_fields(name, patch)` endpoint. PWA `saveEmployer` now uses one round-trip instead of three.
- **Live verified**: 5/5 assertions passed (bulk update; Ready to Submit gate; Submit flips to To be Reviewed + notifies 6 HR users; double-submit blocked; "Submitted for Review" appears in activity log).

### Edge-case sweep + final hardening (2026-04-26)

Proactive search for state contradictions and failure modes after the main audit closed. Real fixes shipped, lower-priority items documented for awareness.

#### Real contradiction found and fixed: pre-Accept bypass

**Symptom**: HR Manager opens AC in Desk during onboarding (helping a new employee) and Accepts every row before the employee taps Submit. Master status compute returned `Accepted` because the branch only checked `all_mandatory_accepted` — not whether the employee had submitted. Result: AC reaches terminal `Accepted` state with `submitted_for_review=0` and `submitted_on=None`. Activity log has no `Submitted for Review` entry. Employee can never explicitly submit (endpoint requires `status == "Ready to Submit"`).

**Fix** (`employee_action_centre.py:_compute_master_status`): added `submitted` to the `Accepted` branch's condition. Now if HR pre-Accepts all rows pre-submit, master stays at `Ready to Submit` until the employee formally submits, then the next save cleanly returns `Accepted`. **Verified live** with a 3-step test: filled mandatory → Ready to Submit → HR pre-Accepts → still Ready to Submit (was Accepted before fix) → employee submits → Accepted with `submitted_for_review=1`, `submitted_on` populated.

#### Other edge cases considered and dispositioned

| Scenario | Disposition |
|---|---|
| HR pre-Rejects pre-submit | Status correctly returns `Action Required`; employee re-uploads → returns to `In Progress` (since not all rows have file/N-A in some sub-cases) or `Ready to Submit`. Acceptable. |
| Two HR users open same AC simultaneously and Accept different rows | Frappe's default optimistic concurrency (`modified` timestamp check) throws `TimestampMismatchError` on the second save. Last save wins, but no silent overwrite. |
| Employee uploads file → immediately marks N/A=1 (race) | Server's `_enforce_data_invariants` runs in validate; whichever save lands last wins. Both end states are coherent (file present + na=0, or file empty + na=1). |
| Submit pressed twice rapidly | Endpoint throws on second call (`already submitted`). PWA's `isSubmitting` ref prevents double-tap. |
| HR rejects → employee re-uploads → master back to To be Reviewed → HR notified again | Intentional. HR should know fresh material is in their queue. |
| HR Policy deleted via console (admin override) | PA rows reference becomes dangling. Check-in gate INNER JOINs HR Policy, so dangling rows are silently filtered out. Admin acted; acceptable. |
| Employee status flipped to Left | `ensure_policy_acknowledgements_for_employee` early-returns for non-Active. Existing PA rows preserved (audit). Cosmetic clutter only. |
| Inactive HR Policy with existing acknowledgements | Check-in gate filters by `hp.is_active=1`, skipping inactive policies. Existing PAs preserved. |

#### Lower-priority items (documented, not fixed)

| Item | Reason for deferring |
|---|---|
| `is_hr_user()` in desk JS uses substring `.includes("hr")` | Could match unintended roles if anyone creates one with "hr" in the name. Defensive cleanup; not currently exploitable. |
| N/A toggle creates a redundant `Document Cleared` activity log entry alongside the `Field Updated` entry | Cosmetic — accurately reflects what happened (file was wiped + na flipped). Could be merged into a single "Marked Not Applicable" entry but adds complexity. |
| HR notification per Submit fans out to every HR Manager + System Manager user | At small headcount (~6 HR users) it's fine. At scale, would want a routing config (per-employee HR partner, or broadcast vs targeted). |
| Activity log has no retention policy | Grows linearly with employee activity. Not a concern at current scale. |

### Decisions captured 2026-04-25 (round 2)

- **Lock-after-Accepted**: once HR accepts a row, the employee role can no longer mutate the file/N-A/remarks (and for employer slots, also name/from/till). Enforced server-side via `_guard_accepted_rows_immutable_for_employee` in validate. HR Manager / System Manager can still revise. PWA-side: every `'Approved'` string compare was bugged (backend never returns that value); replaced with `'Accepted'` which now correctly hides the action buttons for verified rows. **Verified live.**
- **N/A clears the whole subsection (employer slots only)**: toggling `employer_N_is_na=1` wipes file + name + from + till in the same save. For mandatory personal docs (Aadhar/PAN/Education), N/A only wipes the file (there's no name/from/till to clear). **Verified live.**
- **HR notifications — single completion event**: HR is **not** notified per upload. They get a single in-PWA `Notification Log` entry when `AC.status` flips to `To be Reviewed` AND every policy is acknowledged. One notification per HR Manager / System Manager user. **Verified live (6 HR users notified in test).**
- **Master status semantics confirmed**:
  - `Pending` — nothing touched
  - `In Progress` — partial work; some employee uploads or HR statuses but mandatory not all complete
  - `To be Reviewed` — all mandatory rows have file-or-N-A AND ≥1 row is `Awaiting HR`
  - `Accepted` — all mandatory rows are `Accepted` AND no uploaded optional row is unaccepted
- **Optional rows can be left blank without N/A**. The increment letter (employer 1) and employer slots 2-5 (when employee never had a job there) require no action. `_compute_master_status` ignores empty optional rows.
- **Mandatory rows show a red asterisk** in the PWA (Aadhar/PAN/Education + the 5 mandatory employer-1 split docs). Optional rows have no star — and Employer 1 splits keep the existing REQUIRED/OPTIONAL pill below the label as a secondary indicator.

### Decisions captured 2026-04-25 (consultant section follow-ups)

- **Past policy versions**: previous-version acknowledgements remain visible to the employee on demand (collapsed "View history" affordance), never deleted. New version of a policy → new `Policy Acknowledgement` row; old rows immutable.
- **Notifications on HR action**: in-PWA notification on **Rejection only** (Frappe `Notification Log` → bell icon). No notification on Acceptance (less noise). No email at all.
- **Sticky banner for pending policies**: shown on PWA home when `pending_count > 0`. Red variant if any pending policy has `mandatory_check_in_block=1`. Dismissable per session. Subsumes CR-6.
- **CR-1 (bulk update endpoint)**: confirmed — collapses 3 network calls to 1 for employer save / N/A toggle. ~30 lines.
- **CR-2 (button collapse)**: confirmed — single "Upload Document" / "Replace File" button (intent-driven, not state-driven). "Remove File" hidden when status=Accepted.

### Phase 2 (decided 2026-04-25) — split policies out + rename

The policies child table mixes two structurally different things: a **finite onboarding artifact** (KYC + employer history) and an **ongoing compliance ledger** (policy acknowledgements). `AC.status = "Accepted"` while a brand-new mandatory policy sits unack'd in the same doc is the smoking gun.

| ID | Item |
|---|---|
| **CR-15** | Extract `policies` child → standalone `Policy Acknowledgement` doctype, one row per (employee, policy, version). Backfill patch + repoint `validate_checkin_action_centre` and `can_open_attendance_request` to the new doctype. |
| **CR-16** | `HR Policy` gains rule-based scoping: `applies_to_all_employees` (Check, default 1) + four filter tables (`applicable_departments`, `applicable_designations`, `applicable_branches`, `applicable_employment_types`) + manual `applicable_employees` override + `applicability_logic` (OR / AND, default OR). Adds `is_active` Check. **Delete permission stripped**. First-save modal: *"Once saved, this policy cannot be deleted. Use 'Mark Inactive' to retire it. Continue?"* This kills F-11 entirely. |
| **CR-17** | PWA home gets a dedicated **Policies** card with a pending counter (red badge if any pending policy has `mandatory_check_in_block=1`). Removes the Policies section from inside the Centre. Doubles as the proactive check-in gate (CR-6). |
| **Rename** | `Employee Action Centre` → `Documents Centre`. Future-proofs for ongoing post-onboarding doc uploads, not just initial KYC. Bundled with CR-15 since both touch the same files. |

### Phase 4 — policy/check-in coupling

13. Make the check-in gate's rule set configurable (system setting + per-policy override). Decide whether `Action Required` documents should also block.

---

## 9. Open questions for the user

These should be answered before Phase 2/3:

- **Q1**: Should `Action Required` documents block check-ins? (Currently no.)
- **Q2**: Should the master status be derived (not stored), or stored but write-locked to a single function? (Either is better than today.)
- **Q3**: Is the Employer 1 split design (offer letter + 3 payslips + relieving) intentional and stable, or experimental? Refactoring to a child table is much easier if this is finalised.
- **Q4**: Should employees be able to reject their own policy? (No real-world reason, but the endpoint exists.)
- **Q5**: When an HR Policy is deleted, should existing acknowledgements be preserved or wiped?

---

## 10. Live QA — to be filled in next session

Pattern from EMPLOYEE_DIRECTORY:
- create a fresh Employee → assert AC row created and shared
- toggle `mandatory_check_in_block` policy → expect check-in to fail
- upload mandatory trio + N/A others → expect master `To be Reviewed`
- HR rejects one → expect `Action Required` + employee re-uploads → assert master goes back to `To be Reviewed` (currently broken — F-8)
- HR accepts all → expect `Accepted`
- delete a policy → expect orphan child row (currently broken — F-11)

Findings get appended below as `[QA-N]` once run.

---

## 11. Phase 2 hardening (2026-04-26)

Same pattern applied to EAC as the HR Policy / Policy Acknowledgement Phase 2 sweep. 15 issues identified in code review (`EAC-1` through `EAC-15`); 14 fixed and verified live. The site is now production-grade on the EAC surface.

### 11.1 Findings table

| # | Issue | Status |
|---|---|---|
| **EAC-1** | No DB-level uniqueness on `Employee Action Centre.employee`. `_ensure_action_centre`'s `frappe.db.exists` + `insert` pattern is racy under concurrent saves and could produce duplicate ACs. | **RESOLVED.** New patch [v1_6_dedupe_eac_and_add_unique_index.py](../myhr/patches/v1_6_dedupe_eac_and_add_unique_index.py) dedupes by status rank (Accepted > To be Reviewed > Action Required > Ready to Submit > In Progress > Pending; ties broken by latest `modified`) then adds unique index `unique_eac_employee`. Verified live: dup insert → `IntegrityError: Duplicate entry 'OPS-001' for key 'unique_eac_employee'`. |
| **EAC-2** | `submitted_for_review` could be flipped 1 → 0 silently with no state-machine guard. | **RESOLVED.** Controller `_guard_submission_audit_fields()` throws on un-submit unless `frappe.flags.allow_unsubmit_ac` is explicitly set. The sanctioned un-submit path is the new `myhr.api.reopen_action_centre(name, reason)` endpoint (HR-only, requires reason, logs to activity_logs). Verified: direct save with `submitted_for_review=0` throws "Once an Action Centre is submitted for review, it cannot be un-submitted." |
| **EAC-3** | `submitted_on` was mutable post-submission; HR could backdate. | **RESOLVED.** Locked once set in `_guard_submission_audit_fields`. The `reopen_action_centre` endpoint clears it for re-stamping. Verified: backdating throws "`Submitted On` is the audit timestamp and cannot be modified." |
| **EAC-4** | No `submitted_by` field — audit couldn't tell *who* submitted. | **RESOLVED.** New field `submitted_by: Link User, read-only`. Server-stamped in `_stamp_submission_audit_fields()` to `frappe.session.user` on the not-submitted → submitted transition. Locked thereafter (same guard as `submitted_on`). Verified: a save with a tampered `submitted_by` throws. |
| **EAC-5** | No `on_trash` guard; HR or System Manager could delete an AC and wipe its audit history. | **RESOLVED.** New `EmployeeActionCentre.on_trash()` throws unless either `frappe.flags.deleting_employee` (cascade from `on_trash_employee`) or `frappe.flags.allow_eac_delete` (one-shot maintenance) is set. The Employee `on_trash` hook in `employee_hooks.on_trash_employee` now sets the cascade flag and deletes the AC explicitly. Verified: direct `delete_doc` throws; cascade path with the override flag works. |
| **EAC-6** | No file-extension allow-list on the 13 doc upload fields. `.exe / .html / .js` would be accepted by Frappe's Attach default. | **RESOLVED.** `_ALLOWED_FILE_EXTENSIONS = {.pdf, .doc, .docx, .odt, .rtf, .txt, .jpg, .jpeg, .png}` enforced in `_validate_uploaded_file_extensions()`. Verified: `.exe` upload throws "<b>Aadhar</b>: file type .exe is not allowed." |
| **EAC-7** | No date-order sanity on employer history (`from > till`). | **RESOLVED.** `_validate_employer_dates()` throws if either side has both dates set and `from > till`. Verified: `from=2025-01-01, till=2024-01-01` throws. |
| **EAC-8** | `_emit_audit_log` missed remark-only HR edits (HR adding a note without flipping status). | **RESOLVED.** Added a remark-diff branch capturing every change as `Remark Updated` activity row. Verified: editing only the remark on an Aadhar row produced one new activity log: `("Remark Updated", "aadhar: …revised")`. |
| **EAC-9** | No notification to employee on HR Reject — employee learned silently by checking the PWA. | **RESOLVED.** `_notify_employee_on_verdict_changes()` fires a `Notification Log` entry to the employee's user on every Pending/Awaiting → Rejected transition with the rejection remarks in the body. Verified live: rejecting Aadhar produced "[myHR Action Centre] Aadhar rejected — re-upload required". Best-effort (failures log to Error Log, never raise). |
| **EAC-10** | No notification to employee on full-set Accepted — the milestone the employee actually cares about. | **RESOLVED.** Same helper fires a single notification on the master-status `Accepted` transition: "[myHR Action Centre] All documents accepted — onboarding complete". Verified live. |
| **EAC-11** | No HR-side bulk Accept / Reject Desk action. HR had to click each row. | **RESOLVED.** New whitelisted endpoint `myhr.api.hr_set_action_centre_verdict(name, verdict, remarks)` (HR-only). Verdict must be `Accepted` or `Rejected`; rejection requires remarks; empty rows are skipped (can't accept an empty row by design). Surfaced in [employee_action_centre.js](../myhr/myhr/doctype/employee_action_centre/employee_action_centre.js) as "Accept all pending rows" + "Reject all pending rows" custom buttons under the HR Actions menu. Verified live: 8 mandatory rows accepted, 5 empty optional rows skipped, master status flipped to Accepted. |
| **EAC-12** | No HR-side coverage / completion report endpoint. | **RESOLVED.** New whitelisted endpoint `myhr.api.get_action_centre_coverage()` returns one row per AC with `{employee, employee_name, status, submitted_on, submitted_by, mandatory_acked, total_mandatory, coverage_pct}` sorted by descending coverage. HR-only. Verified live: 10 employee ACs returned. |
| **EAC-13** | An Inactive / Left employee could still have their AC mutated by their (still-logged-in) user session — no mutation lock. | **RESOLVED.** New `_guard_inactive_employee_immutable()` throws on saves where `Employee.status != 'Active'` unless caller has HR Manager / System Manager role. Verified live with leaf employee MKT-002: setting `status='Left'` then saving the AC as the employee user throws "Employee <b>MKT-002</b> is currently <b>Left</b>. Their Action Centre cannot be modified. Contact HR." |
| **EAC-14** | `Action Centre Activity.action` Select options didn't include the new audit verbs the controller now writes (`Remark Updated`, `Reopened by HR`, `Bulk Verdict Applied`). | **RESOLVED.** [action_centre_activity.json](../myhr/myhr/doctype/action_centre_activity/action_centre_activity.json) options extended. |
| **EAC-15** | When the employee marked Most Recent Employer as **No prior employer** (fresher), `_enforce_data_invariants` wiped the Previous Employer (slot 2-5) data fields but left their `_is_na` flags at 0. The per-row sweep then settled their status at `Pending`, so the Home page Action Centre badge kept counting them as outstanding tasks even though the slots were hidden in the UI and the user had nothing to do. | **RESOLVED 2026-04-27.** Three-part fix: (1) `_enforce_data_invariants` now propagates `is_na=1` to slots 2-5 when `employer_1_is_na=1`, and reverse-clears them on the 1→0 transition; (2) `_row_inherits_parent_na` extended to cover slots 2-5 in fresher mode so master-status compute treats them as auto-accepted (no per-slot HR Accept needed); (3) `Home.vue::actionCentrePendingCount` only counts slot 2-5 once the user has started filling that slot — defence in depth so already-submitted ACs in the bad state stop showing a phantom badge on next reload, before any save backfills the data. |
| **EAC-16** | `_guard_submission_audit_fields` compared `submitted_on` from the desk form against `get_doc_before_save()`. Two type/precision mismatches misfired on every HR save of an already-submitted AC: (a) DB returned a `datetime`, the form re-posted a string; (b) DB stored microseconds (DATETIME(6)), the form's `YYYY-MM-DD HH:MM:SS` string did not. Result: HR Manager opened AC-0561 in Desk, tried any edit, hit "Audit field locked". The original live verification used Python value-mutation tests (datetime on both sides, microseconds preserved) so the bug only surfaced via the desk form. | **RESOLVED 2026-04-28.** Normalized both sides with `frappe.utils.get_datetime(...).replace(microsecond=0)` before comparing in [`employee_action_centre.py:_guard_submission_audit_fields`](../myhr/myhr/doctype/employee_action_centre/employee_action_centre.py). Same bug pattern fixed in [`leave_application.py`](../myhr/overrides/leave_application.py) (`custom_approved_on`) and [`policy_acknowledgement.py`](../myhr/myhr/doctype/policy_acknowledgement/policy_acknowledgement.py) (`acknowledged_at`). The `submitted_by` / `custom_approved_by` Link comparisons did not need normalization (string both ways). **Verified live on AC-0561**: HR same-value re-save passes, backdating still throws "audit timestamp cannot be modified". |

### 11.2 New endpoints (api.py)

| Endpoint | Caller | Purpose |
|---|---|---|
| `hr_set_action_centre_verdict(name, verdict, remarks="")` | EAC Desk "Accept all" / "Reject all" buttons | HR-only. Bulk-decide every Pending / Awaiting HR row. Empty rows skipped; rejection requires remarks. |
| `reopen_action_centre(name, reason)` | EAC Desk "Reopen for re-edit" button | HR-only. Sanctioned un-submit. Sets `frappe.flags.allow_unsubmit_ac` to bypass the controller lock; clears `submitted_on / submitted_by`; logs `Reopened by HR` to activity_logs with the reason. |
| `get_action_centre_coverage()` | HR coverage view | HR-only. Returns one row per AC with `{employee, employee_name, status, submitted_on, submitted_by, mandatory_acked, total_mandatory, coverage_pct}`. |

### 11.3 New PA-side audit log integration

EAC's `activity_logs` child table is the audit trail; `Policy Audit Log` is the parallel structure on PA. The two are deliberately separate — they record different objects — but the conventions match (canonical writer, append-only, every status flip captured).

### 11.4 Live verification (13/13 pass — 2026-04-26)

| # | Test | Result |
|---|---|---|
| T-1 | Duplicate AC insert blocked by unique index | ✅ `IntegrityError: Duplicate entry 'OPS-001' for key 'unique_eac_employee'` |
| T-2 | Submit via API stamps `submitted_for_review=1, submitted_on=now, submitted_by=session.user` | ✅ |
| T-2a | Direct save with `submitted_for_review=0` throws | ✅ |
| T-2b | Backdating `submitted_on` throws | ✅ |
| T-2c | Changing `submitted_by` throws | ✅ |
| T-3 | `reopen_action_centre(name, reason)` clears all 3 fields cleanly | ✅ |
| T-4 | `.exe` file upload blocked by MIME guard | ✅ |
| T-5 | `from > till` date order on employer slot blocked | ✅ |
| T-6 | `hr_set_action_centre_verdict` accepts 8/8 mandatory rows, skips 5 empty optional rows, master flips to Accepted | ✅ |
| T-6b | Employee gets "All documents accepted" notification on master Accepted | ✅ |
| T-7 | Employee gets per-row rejection notification with HR's remark | ✅ |
| T-8 | Remark-only HR edit produces a `Remark Updated` activity log row | ✅ |
| T-9 | `get_action_centre_coverage` returns 10 employee ACs | ✅ |
| T-10 | Direct AC delete blocked by `on_trash` | ✅ |
| T-11 | Cascade delete via `frappe.flags.deleting_employee` flag works | ✅ |
| T-12 | Mutation as Left employee throws "Their Action Centre cannot be modified" | ✅ (verified with leaf employee MKT-002) |

### 11.5 Site state at end of pass

5 active HR Policies · 50 Acknowledged PAs · 10 Employee Action Centres (status=Pending after teardown reset) · 0 audit log orphans · all unique indices in place.

## 12. Personal / family / passport field extension (2026-09-10)

Fields added to `Employee Action Centre` from the HR onboarding sheet. All are pure data capture (no per-row HR approval), `read_only` on Desk, written by the employee through the PWA via `save_action_centre_draft`. Every new field is registered in `AC_PERSONAL_DATA_FIELDS` (whitelist + audit + submit-gate) and in the `get_action_centre` payload in `api.py`. **All are currently optional** — mandatory flags to be decided.

| Desk tab / section | Field | Type | Notes |
|---|---|---|---|
| Personal Details / Basic Information | `personal_date_of_joining` | Date | Fetched from `Employee.date_of_joining`; read-only in PWA too (not whitelisted). |
| Personal Details / Basic Information | `personal_preferred_contact_email` | Select | Company Email / Personal Email / User ID — mirrors `Employee.prefered_contact_email`. |
| Personal Details / Family | `personal_father_dob`, `personal_mother_dob` | Date | |
| Personal Details / Family | `personal_spouse_name` / `_gender` / `_dob` | Small Text / Select / Date | |
| Personal Details / Family | `personal_child_{1,2}_name` / `_gender` / `_dob` | Small Text / Select / Date | Flat fields (sheet fixes two children); no child table. |
| Personal Details / Emergency Contact | `personal_emergency_relation` | Small Text | Fetched from `Employee.relation`. |
| Identity Documents / Passport | `passport_number`, `passport_valid_upto`, `passport_date_of_issue`, `passport_place_of_issue` | Small Text / Date / Date / Small Text | Fetched from the Employee passport fields. On the PWA they render inside the Personal Details bucket (no dedicated section yet). |
| Statutory & Bank / Bank Details | `bank_account_holder_name` | Small Text | "Name as per Bank Records". |

No Vue change was required: the PWA renders `personal_details` / `statutory_bank` rows generically by `kind` (`text`, `date`, `select`, `readonly`).
