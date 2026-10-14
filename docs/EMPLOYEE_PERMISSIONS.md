# Employee Permissions — myHR

Authoritative spec for who can read / write `Employee` records on the desk Employee list. Replaces the previous CUP-based (`create_user_permission`) approach with a code-driven model that supports the manager-views-direct-reports use case.

**App:** myHR
**DocType:** `Employee` (standard ERPNext)
**Implementation:** [`apps/myhr/myhr/permissions.py`](../myhr/permissions.py)
**Hooks wiring:** [`apps/myhr/myhr/hooks.py`](../myhr/hooks.py) (`permission_query_conditions["Employee"]`, `has_permission["Employee"]`)
**Custom Field:** `Employee.custom_allow_view_reporting` (declared in [`setup.py:MYHR_CUSTOM_FIELDS`](../myhr/setup.py))
**Migration patch:** [`apps/myhr/myhr/patches/v1_10_employee_view_reporting.py`](../myhr/patches/v1_10_employee_view_reporting.py)

---

## 1. Purpose

Stock Frappe / ERPNext lets you restrict an end-user's view of the `Employee` list to their own record by ticking `create_user_permission` on the Employee, which inserts a `User Permission` row (`User → allow:Employee, for_value:<that employee>`). That works for "user sees self only" but breaks down the moment you need "user sees self **plus** their direct reports": there's no built-in way to express that without enumerating one User Permission row per direct report and re-enumerating every time the org chart changes.

myHR replaces the CUP approach with a tiny code-driven model: a single Custom Field (`custom_allow_view_reporting`) on the manager's Employee record, plus a pair of Frappe permission hooks that read `reports_to` live. Org chart changes are picked up immediately without User Permission row maintenance.

---

## 2. The rule

| User | Read | Write |
|---|---|---|
| Administrator | all | all |
| HR Manager / System Manager | all | all |
| HR User | all | **none** (locked down by `_ensure_employee_perm_lockdown` + `has_employee_permission`) |
| Has Employee linked, `custom_allow_view_reporting = 1` | self + **direct reports** (`reports_to == self`) | none |
| Has Employee linked, `custom_allow_view_reporting = 0` | self only | none |
| No Employee linked | none | none |

**Direct reports only** — not the whole sub-tree (descendants). See finding `PERM-1` in §8.

**Read-only** for everyone except HR Manager / System Manager / Administrator. Even users opening their own Employee record cannot save changes — see §6 "Write lockdown" and finding `PERM-2`.

---

## 3. Implementation

Two Frappe permission hooks, both pointing at functions in [`myhr/permissions.py`](../myhr/permissions.py).

### 3.1 `permission_query_conditions["Employee"]`

```python
permission_query_conditions = {
    "Employee": "myhr.permissions.employee_permission_query_conditions",
}
```

`employee_permission_query_conditions(user)` returns a SQL WHERE fragment that Frappe ANDs into every `Employee` list query (`frappe.get_list`, `frappe.get_all`, the desk list view, REST list endpoints). It returns:

- `""` (empty string — no restriction) for Administrator, HR Manager, System Manager, HR User.
- `"`tabEmployee`.name = '<self>'"` for an Employee-linked user with `custom_allow_view_reporting = 0`.
- `"`tabEmployee`.name IN ('<self>', '<direct-report-1>', ...)"` for an Employee-linked user with `custom_allow_view_reporting = 1`.
- `"1=0"` (returns no rows) for users with no linked Employee and no HR role.

### 3.2 `has_permission["Employee"]`

```python
has_permission = {
    "Employee": "myhr.permissions.has_employee_permission",
}
```

`has_employee_permission(doc, ptype, user)` returns `True` / `False` for record-level checks (opening a single Employee form, programmatic `frappe.has_permission("Employee", doc=...)` calls). It mirrors the WHERE-fragment logic: HR roles short-circuit to `True` for any `ptype`; other users get `True` only on their own Employee or, when `custom_allow_view_reporting=1`, their direct reports — and only for `ptype="read"`. Writes return `False` for non-HR users.

The two hooks must agree — Frappe runs the WHERE fragment for list views and `has_permission` for single-doc opens. If they disagree you get the classic "row appears in the list but throws on click" symptom.

---

## 4. The Custom Field

Declared in [`setup.py:MYHR_CUSTOM_FIELDS`](../myhr/setup.py):

| Attribute | Value |
|---|---|
| `dt` | `Employee` |
| `fieldname` | `custom_allow_view_reporting` |
| `label` | Allow to see Reporting Employees |
| `fieldtype` | Check |
| `default` | `0` |
| `insert_after` | (lands on the **HR Controls** tab — sibling of `custom_emp_directory`, `custom_add_to_action_centre`, etc.) |
| `description` | When ticked, this employee can see the Employee records of their direct reports (anyone whose `reports_to` is this employee) on the desk Employee list, in addition to their own row. Read-only access. Has no effect on users with the HR Manager / HR User / System Manager role — those see everyone regardless. |

Setup creates the field on first migrate. Subsequent migrates skip-if-exists (per `_ensure_custom_fields`). If you change a flag on the dict after first migrate, clone the v1_8 repair pattern.

---

## 5. Migration path

Patch [`v1_10_employee_view_reporting`](../myhr/patches/v1_10_employee_view_reporting.py), registered in [`patches.txt`](../myhr/patches.txt), runs once per site:

1. Ensures the `custom_allow_view_reporting` Custom Field exists (defensive — `_ensure_custom_fields` should have created it on the same migrate, but the patch retries).
2. For each of the 10 demo Employees (`CEO`, `CFO`, `HR-001`, `HR-002`, `SAL-001`, `SAL-002`, `OPS-001`, `OPS-002`, `MKT-001`, `MKT-002`):
   - Deletes any stale `User Permission` rows of the form `User=<demo user>, allow=Employee, for_value=<demo employee>` left over from the old CUP-based seed.
   - Sets `create_user_permission = 0` on the Employee row.
3. Sets `custom_allow_view_reporting = 1` on the 7 managers (`CEO`, `CFO`, `HR-001`, `HR-002`, `SAL-001`, `OPS-001`, `MKT-001`).
4. Sets `custom_allow_view_reporting = 0` on the 3 executives (`SAL-002`, `OPS-002`, `MKT-002`).
5. `frappe.db.commit()` and prints a summary line.

**Idempotent.** Re-running the patch is safe: `frappe.db.delete` is a no-op when the rows are already gone, `set_value` writes the same flags, and the print line just repeats. Patch Log tracks "applied" status so Frappe skips it on subsequent migrates anyway.

---

## 6. Write lockdown

**Only HR Manager + System Manager + Administrator can write `Employee` records.** Everyone else — including HR User, Employee, Leave Approver, and any other role — is strictly read-only on the doctype, even on their own record. Per the user's policy: *"any info you want updated, ask HR Manager."*

### Why even self-edit is blocked

Self-edit is intentionally disabled for non-HR users to keep the audit chain clean and prevent users from changing their own department, designation, `leave_approver`, contact info, or any other field that affects downstream gates. If someone needs a field changed, HR Manager makes the change — that becomes the canonical record. This is a deliberate UX trade-off; the friction is the feature.

### Implementation — defense in depth

Two independent layers enforce the lockdown so that a regression in one does not compromise the other:

1. **Code gate (canonical).** [`myhr/permissions.py:has_employee_permission`](../myhr/permissions.py) intercepts every record-level perm check. Write-class ptypes (`write` / `create` / `delete` / `submit` / `cancel` / `amend` / `import` / `export`) return `False` for any user that is not Administrator + HR Manager + System Manager. Read-class ptypes still flow through the existing self / reports / HR User logic in §3.
2. **DocPerm gate (visual).** [`myhr/setup.py:_ensure_employee_perm_lockdown`](../myhr/setup.py) inserts a `Custom DocPerm` row at permlevel 0 for every non-exempt role that stock ERPNext or HRMS grants any write flag on Employee (notably HR User). The Custom DocPerm forces `write/create/delete/submit/cancel/amend = 0` and keeps `read = 1`. Frappe AND-merges Custom DocPerm with stock DocPerm, so the most-restrictive flag wins.

### Why both layers

- The **code gate** is the canonical answer. Someone reading `permissions.py` sees the rule clearly and the gate runs even if a third-party app added a stray Custom DocPerm granting writes.
- The **DocPerm gate** makes the **Role Permission Manager UI in Desk** look correct. Without it, an HR Manager opening Role Permission Manager would see HR User listed with `write=1, create=1, delete=1` on Employee — which would be confusing ("but we said HR User can't write?"). The Custom DocPerm row makes the matrix visually match the runtime rule.

### Migration

Patch [`v1_11_employee_write_lockdown`](../myhr/patches/v1_11_employee_write_lockdown.py), registered in [`patches.txt`](../myhr/patches.txt), runs `_ensure_employee_perm_lockdown()` once on existing sites. After v1_11 lands, every subsequent `bench migrate` re-runs the same function via `after_migrate` → `_setup()`, so the lockdown self-heals if anyone manually edits the Custom DocPerm row to re-enable writes.

---

## 7. Why this replaces CUP

| Trade-off | CUP-based (old) | Code-driven (new) |
|---|---|---|
| Built-in vs custom | Stock ERPNext field + controller | myHR Custom Field + 2 Python hooks (~80 LOC) |
| "Self only" support | Yes (one User Permission row per user) | Yes |
| "Self + direct reports" support | **No** without per-report User Permission rows; re-enumerate on every org change | Yes — reads `reports_to` live |
| Write-vs-read split | All-or-nothing per UP row (UPs gate read AND match-link checks) | Read-only for non-HR; write reserved to HR roles |
| HR Manager bypass | Implicit via role docperm | Explicit short-circuit in both hooks |
| Migrate-time work | None on a fresh seed; large amount on org-chart changes | None ever (`reports_to` is read at query time) |
| Discoverability | Field is on every Employee form; CUPs hide in the User Permission desk list | Field is named clearly + has a UI description; hooks are documented here |

The code-driven model has more code to read, but it has **zero per-row maintenance** as the org chart evolves, and it cleanly separates "who can read what" from "who can write what" (CUP can't do the latter — User Permissions gate both reads and link-validation writes).

HR Managers / HR Users / System Managers bypass everything (they need org-wide visibility for HR work). That bypass is unconditional in both hooks; you can't accidentally lock HR out of the Employee table.

---

## 8. Findings

| ID | Finding | Status |
|---|---|---|
| **PERM-1** | The model shows **direct reports only** — not the whole sub-tree (descendants). A 3-level org chart (CEO → VP → Manager → IC) means the CEO sees only the VP, not the Manager or the IC. | **Open — by design (2026-04-27).** Direct reports cover the demo data set's needs. If sub-tree visibility is needed later, extend `employee_permission_query_conditions` to use a recursive CTE on `reports_to` (`WITH RECURSIVE descendants AS (SELECT name FROM `tabEmployee` WHERE name = '<self>' UNION ALL SELECT e.name FROM `tabEmployee` e JOIN descendants d ON e.reports_to = d.name) SELECT name FROM descendants`). MariaDB 10.2+ and Postgres support this; check the bench's DB version before shipping. |
| **PERM-2** | Self-edit blocked. Users cannot update their own Employee record (department, designation, contact info, etc.) — must request HR Manager. | **By design, RESOLVED 2026-04-27.** Write-class ptypes (`write` / `create` / `delete` / `submit` / `cancel` / `amend` / `import` / `export`) in [`has_employee_permission`](../myhr/permissions.py) return `False` for any user that is not Administrator + HR Manager + System Manager. HR User's stock DocPerm write flags are additionally stripped via [`_ensure_employee_perm_lockdown`](../myhr/setup.py) so the Role Permission Manager UI matches the runtime rule. Migration: patch [`v1_11_employee_write_lockdown`](../myhr/patches/v1_11_employee_write_lockdown.py). See §6 "Write lockdown". |

---

## 9. Test plan

### 9.1 Bench-console one-liner

Run on a freshly-migrated site after `v1_10_employee_view_reporting` has applied. Expected counts derived from the seed_v15 org chart (CEO at the top; CFO/HR-001/SAL-001/OPS-001/MKT-001 reporting to CEO; HR-002 → HR-001; SAL-002/OPS-002/MKT-002 reporting to their respective managers):

```python
import frappe

cases = [
    ("ceo@erpdemo.local",                 6),  # self + 5 direct reports
    ("cfo@erpdemo.local",                 1),  # self; no reports
    ("hrhead@erpdemo.local",              2),  # self + HR-002
    ("hrmanager@erpdemo.local",           1),  # self; no reports (NB: also has HR Manager role in seed → may show 10; remove role for this test)
    ("salesmanager@erpdemo.local",        2),  # self + SAL-002
    ("salesexec@erpdemo.local",           1),  # self only (custom_allow_view_reporting=0)
    ("opsmanager@erpdemo.local",          2),  # self + OPS-002
    ("opsexec@erpdemo.local",             1),  # self only
    ("marketingmanager@erpdemo.local",    2),  # self + MKT-002 — the user-demoed case; should now show 2, not 10
    ("marketingexec@erpdemo.local",       1),  # self only
]

print(f"{'user':40s}  {'expected':>8}  {'got':>4}  {'pass':>5}")
for user, expected in cases:
    frappe.set_user(user)
    got = len(frappe.get_list("Employee", fields=["name"], limit_page_length=0))
    ok = "PASS" if got == expected else "FAIL"
    print(f"{user:40s}  {expected:>8}  {got:>4}  {ok:>5}")
    frappe.set_user("Administrator")
```

### 9.2 Expected list-counts per login

| Login | View flag | Expected employee count visible |
|---|---|---|
| Administrator | — | 10 (all) |
| HR Manager via role on any user | — | 10 (all) |
| CEO (`ceo@erpdemo.local`) | 1 | 6 (self + 5 direct reports: CFO, HR-001, SAL-001, OPS-001, MKT-001) |
| CFO (`cfo@erpdemo.local`) | 1 | 1 (self; no reports) |
| HR-001 (`hrhead@erpdemo.local`) | 1 | 2 (self + HR-002) |
| HR-002 (`hrmanager@erpdemo.local`) | 1 | 1 (self; no reports) |
| SAL-001 (`salesmanager@erpdemo.local`) | 1 | 2 (self + SAL-002) |
| SAL-002 (`salesexec@erpdemo.local`) | 0 | 1 (self only) |
| OPS-001 (`opsmanager@erpdemo.local`) | 1 | 2 (self + OPS-002) |
| OPS-002 (`opsexec@erpdemo.local`) | 0 | 1 (self only) |
| MKT-001 (`marketingmanager@erpdemo.local`) | 1 | 2 (self + MKT-002) — this is the case the user demoed; should now show 2, not 10 |
| MKT-002 (`marketingexec@erpdemo.local`) | 0 | 1 (self only) |

> Note: HR-002 carries the `HR Manager` role in the demo seed, so logging in as `hrmanager@erpdemo.local` actually shows all 10. The "1" in the table above is the count you'd see if HR-002 didn't have the role — useful as a bound when testing the hook in isolation.

### 9.3 UI tests

- Login as `marketingmanager@erpdemo.local` (MKT-001) → desk Employee list → expect 2 rows (`MKT-001`, `MKT-002`). Open `MKT-002` → expect read-only form (no Save button for non-HR). Try editing → expect `PermissionError`.
- Login as `marketingexec@erpdemo.local` (MKT-002) → desk Employee list → expect 1 row (`MKT-002`).
- Login as Administrator → expect 10 rows.
- Login as a user with no linked Employee + no HR role → expect 0 rows + permission error on direct URL access.

### 9.4 Verify the hooks are wired

```python
import frappe
print(frappe.get_hooks("permission_query_conditions").get("Employee"))
# Expected: ['myhr.permissions.employee_permission_query_conditions']
print(frappe.get_hooks("has_permission").get("Employee"))
# Expected: ['myhr.permissions.has_employee_permission']
```

### 9.5 Verify the migration ran

```python
import frappe
assert frappe.db.exists("Patch Log", {"patch": "myhr.patches.v1_10_employee_view_reporting"})
assert frappe.db.count("Employee", {"create_user_permission": 1, "name": ("in", [
    "CEO","CFO","HR-001","HR-002","SAL-001","SAL-002","OPS-001","OPS-002","MKT-001","MKT-002"
])}) == 0
assert frappe.db.count("Employee", {"custom_allow_view_reporting": 1}) == 7
print("v1_10 verification: PASS")
```

---

## 10. Quick verify on a live site

After `bench --site <site> migrate` has applied `v1_11_employee_write_lockdown`, run this in the bench console to confirm the lockdown is live and a non-HR user genuinely cannot save their own Employee record:

```python
# bench --site <site> console
import frappe

# 1. HR User now has no write on Employee
hr_user_row = frappe.db.get_value("Custom DocPerm",
    {"parent": "Employee", "role": "HR User", "permlevel": 0},
    ["read", "write", "create", "delete"], as_dict=True)
print(hr_user_row)  # expect {'read': 1, 'write': 0, 'create': 0, 'delete': 0}

# 2. Logged in as Pooja (MKT-002) — try to write her own record
frappe.set_user("marketingexec@erpdemo.local")
e = frappe.get_doc("Employee", "MKT-002")
e.gender = "Female"  # she's already Female; tries to "update"
try:
    e.save()
    print("FAIL: write succeeded — should have thrown")
except frappe.PermissionError:
    print("OK: write blocked")
frappe.set_user("Administrator")
```
