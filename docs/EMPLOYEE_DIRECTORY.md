# Employee Directory — Feature Specification

> Authoritative description of what the feature is, how it should behave, and what the data and code paths look like. Use this as the source of truth when reviewing PRs or changing the feature.

**App:** myHR
**DocType:** `Employee Directory`
**PWA route:** `/directory`
**API:** `myhr.api.get_employee_directory`

---

## 1. Purpose

A lightweight, employee-facing **company contact book** inside the HRMS PWA. Any logged-in employee can:

- Browse a single alphabetical list of currently-active colleagues.
- Search by name, designation, department, or employee ID.
- Tap any colleague to expand a card and see department, phone, and email.
- One-tap dial (`tel:`) or email (`mailto:`) without leaving the app.

The directory is **derived from the standard `Employee` doctype** — never manually maintained. HR controls who appears in it via a checkbox on each Employee record.

### Visibility policy (decided)

> **Everyone sees everyone.** Every authenticated user gets the full list of active employees. There is no row-level filter. This is intentional — a company contact book has no privacy reason to hide colleagues from each other.

### Active-only policy (decided)

> Only employees with `status = "Active"` appear in the directory. The moment an employee is marked `Left`, `Suspended`, or `Inactive`, their row is removed (on save) and is also filtered out at read time as a safety net.

---

## 2. User Stories

| # | As a … | I want to …                                          | So that …                                  |
|---|--------|------------------------------------------------------|---------------------------------------------|
| 1 | Employee | open the directory from the PWA home               | I can find a colleague's contact quickly    |
| 2 | Employee | search for a name, role, or team                    | I don't have to scroll the whole list       |
| 3 | Employee | tap a card to reveal phone and email                | the list stays compact                      |
| 4 | Employee | tap the phone number                                | my dialer opens with the number prefilled   |
| 5 | Employee | tap the email                                        | my mail app opens a new draft                |
| 6 | HR Manager | toggle a checkbox on Employee                      | I control who appears in the directory      |
| 7 | HR Manager | edit an Employee's phone/department                 | the directory entry refreshes automatically |
| 8 | HR Manager | mark an Employee as Left                            | their row drops out of the directory        |
| 9 | HR Manager | rebuild the directory after a bulk import           | I can seed everyone in one shot             |

---

## 3. Data Model

### 3.1 Doctype: `Employee Directory`

Defined in [`myhr/myhr/doctype/employee_directory/employee_directory.json`](../myhr/myhr/doctype/employee_directory/employee_directory.json).

| Property        | Value                       |
|-----------------|-----------------------------|
| Module          | `myHR`                      |
| Naming          | `field:employee_id`         |
| Track changes   | yes                         |
| Allow rename    | yes                         |

#### 3.1.1 Fields

| Order | Fieldname        | Type | Label          | Required | Unique | In list view | Source on `Employee`                                  |
|------:|------------------|------|----------------|:-------:|:------:|:------------:|-------------------------------------------------------|
| 1     | `employee_id`    | Data | Employee ID    | ✓        | ✓      | ✓            | `Employee.name` (= `custom_employee_id` after rename) |
| 2     | `employee_name`  | Data | Employee Name  | ✓        |        | ✓            | `Employee.employee_name`                              |
| 3     | `designation`    | Data | Designation    |          |        | ✓            | `Employee.designation`                                |
| 4     | `department`     | Data | Department     |          |        | ✓            | `Employee.department`                                 |
| 5     | `mobile_number`  | Data | Mobile Number  |          |        |              | `Employee.cell_number`                                |
| 6     | `employee_email` | Data | Company Email  |          |        |              | `Employee.company_email`                              |

> All fields are plain `Data` (string), not `Link` fields. The directory is an **independent flat record** — by design easy to query and cheap to read. `employee_id` is also the doc primary key (`name`) so each Employee maps 1:1.

### 3.2 Custom fields added to `Employee`

Created idempotently by [`myhr/setup.py → MYHR_CUSTOM_FIELDS`](../myhr/setup.py).

| Fieldname              | Type  | Default | Label                       | Effect                                                                |
|------------------------|-------|---------|-----------------------------|------------------------------------------------------------------------|
| `custom_employee_id`   | Data  | —       | Employee ID                 | On **insert**, forces `Employee.name` to this string. Read-only after. |
| `custom_emp_directory` | Check | `1`     | Add to Employee Directory   | When ticked **and** `status='Active'`, employee is upserted into the directory. Untick → row removed on next save. |

(Other myHR custom fields like `custom_add_to_action_centre`, `custom_auto_present`, `custom_bypass_geolocation_check` exist on Employee but are **not** related to Directory — they are documented in their own feature specs.)

---

## 4. UI Specification (PWA)

Source: [`myhr/frontend_changes/views/EmployeeDirectory.vue`](../myhr/frontend_changes/views/EmployeeDirectory.vue), synced via `myhr.frontend_sync.apply_custom_ui` into `apps/hrms/frontend/src/views/EmployeeDirectory.vue` and built into HRMS's frontend bundle.

### 4.1 Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Header (sticky, white, shadow-sm, border-b)                │
│  [‹]  Employee Directory                  [🔔]   [Avatar]   │
├─────────────────────────────────────────────────────────────┤
│  ┌─ Search bar ──────────────────────────────────────┐     │
│  │ 🔍  Search employees…                             │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌─ Directory list (white card) ─────────────────────┐     │
│  │ [Avatar] Arjun Sharma                       [v]   │     │
│  │          Software Engineer                         │     │
│  │ ─────────────────────────────────────────────     │     │
│  │ [Avatar] Priya Patel                        [^]   │     │
│  │          HR Manager                                │     │
│  │ ┌─ expanded panel (gray-50/40 bg) ────────────┐  │     │
│  │ │ DEPARTMENT                                   │  │     │
│  │ │ Human Resources – EDPLD                      │  │     │
│  │ │ ┌ ☎ +91 98765 00002 ┐                        │  │     │
│  │ │ ┌ ✉ priya@sample.com ┐                       │  │     │
│  │ └────────────────────────────────────────────┘  │     │
│  │ ─────────────────────────────────────────────     │     │
│  │ [Avatar] Rahul Verma                        [v]   │     │
│  │          Product Manager                           │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

- **Container width:** full-width on mobile; capped at `max-w-4xl` and centered on `sm+` screens.
- **Background:** body `bg-gray-50`, content card `bg-white` with subtle border.

### 4.2 Header

| Element        | Behaviour                                                                                  |
|----------------|--------------------------------------------------------------------------------------------|
| Back chevron   | `goBack()` → `window.history.back()`. Always visible.                                      |
| Title          | "Employee Directory" (translatable via `__()`); `text-xl font-bold`.                       |
| Bell icon      | Routes to `Notifications`. Red dot overlay (`bg-red-600` 8 px circle) when `unreadNotificationsCount.data` is truthy. |
| Profile avatar | Routes to `Profile`. Shows the current user's `user_image` if set, else first-name initial. Size: `xl`. |

Sticky to top inside the scroll container (`sticky top-0 z-10`).

### 4.3 Search bar

- Bound to `searchQuery` (`v-model`).
- Placeholder: **"Search employees…"** (translatable).
- Magnifying-glass icon left-padded inside the input.
- Visual: rounded, `bg-white`, `border-gray-200`, focus ring `focus:ring-2 focus:ring-gray-300`.
- **Filtering is client-side** (see §5.3). Empty query → full list.

### 4.4 List rows (collapsed state)

Each row is a single `<button>` that toggles expansion:

| Element           | Detail                                                                                        |
|-------------------|-----------------------------------------------------------------------------------------------|
| Avatar            | `Avatar` component, `size="xl"`, `label={employee_name}` → renders **initials** (no photo).  |
| Name              | `text-base font-semibold text-gray-900`, single-line truncate.                                |
| Designation       | Below name, `text-sm font-normal text-gray-500`, single-line truncate. Hidden if empty.       |
| Trailing chevron  | `chevron-down` collapsed / `chevron-up` expanded; right-aligned.                              |
| Hover             | `hover:bg-gray-50/80` (desktop only — keeps tap cleanliness on touch).                        |
| Divider           | 1 px `border-b border-gray-100` between rows; the last row has no border.                     |

### 4.5 Expanded panel (per-row)

Rendered with `v-show` (kept in DOM) so toggling is instant; multiple rows may be expanded at once.

| Element           | Detail                                                                                                  |
|-------------------|---------------------------------------------------------------------------------------------------------|
| Container         | `bg-gray-50/40`, `border-t border-gray-50`; left-aligned with the avatar on `sm+`, indented on mobile.  |
| Department block  | Tiny uppercase label ("DEPARTMENT") + value below in `text-sm text-gray-600`. Hidden if empty.          |
| Phone button      | `<a href="tel:{mobile_number}">`, phone icon + number. Hidden if `mobile_number` empty.                |
| Email button      | `<a href="mailto:{employee_email}">`, mail icon + address. Hidden if `employee_email` empty.            |
| Style             | Both buttons: rounded, `border-gray-200`, `bg-white`, full-width up to `max-w-sm`. `@click.stop` so they don't collapse the parent row. |

### 4.6 Expand / collapse behaviour

State held in a `Set<employee_id>` (`expandedIds`) — **not a single value**, so:

- Tapping a collapsed row adds its `employee_id` to the set → row expands.
- Tapping an expanded row removes it → row collapses.
- **Multiple rows can be expanded simultaneously** (intentional: lets users compare two contacts side-by-side).

### 4.7 Empty / loading states

| State      | When                                                  | What is shown                                                                       |
|------------|-------------------------------------------------------|-------------------------------------------------------------------------------------|
| Loading    | `loading === true` (initial fetch in flight).         | Centered `LoadingIndicator` spinner (`py-20`).                                      |
| No results | `!loading && filteredEmployees.length === 0`          | `users` icon + text. "No matching employees found" if `searchQuery` is set, else "Directory is empty". |
| Populated  | `filteredEmployees.length > 0`                        | The list as described above.                                                        |

### 4.8 Entry points (how a user reaches `/directory`)

| Surface                 | File                                                        | Trigger                          |
|-------------------------|-------------------------------------------------------------|-----------------------------------|
| PWA Home Quick Link     | `frontend_changes/views/Home.vue`                           | Quick-link grid item with `route: "EmployeeDirectory"` |
| Quick-link registry     | `frontend_changes/components/QuickLinks.vue`                | Lists `EmployeeDirectory` as a registered link |
| Desktop sidebar         | `frontend_changes/components/DesktopSidebar.vue`            | Sidebar entry pointing at `/directory` |
| Direct URL              | `/directory` (router name `EmployeeDirectory`)              | Type / paste / link-share         |

Router: [`frontend_changes/router/index.js`](../myhr/frontend_changes/router/index.js) → `{ path: "/directory", name: "EmployeeDirectory", component: () => import("@/views/EmployeeDirectory.vue") }`.

---

## 5. Backend Behaviour

### 5.1 Sync hook — `Employee.validate`

[`myhr/employee_hooks.py:validate_employee`](../myhr/employee_hooks.py)

```python
def validate_employee(doc, method):
    # 1. Force Employee primary key on insert only (never on subsequent saves).
    if doc.is_new() and doc.custom_employee_id:
        doc.name = doc.custom_employee_id

    if not doc.name:
        return

    should_appear = bool(doc.custom_emp_directory) and (doc.status == "Active")

    if should_appear:
        # upsert directory row from current Employee fields
        ...
    else:
        # untick or non-Active → remove directory row if it exists
        if frappe.db.exists("Employee Directory", doc.name):
            frappe.delete_doc("Employee Directory", doc.name, ignore_permissions=True)
```

**Decision matrix on save:**

| `custom_emp_directory` | `status`   | Existing row | Action                        |
|------------------------|------------|--------------|-------------------------------|
| `1`                    | `Active`   | no           | Insert new row                |
| `1`                    | `Active`   | yes          | Update existing row           |
| `1`                    | `Left/…`   | yes          | **Delete** existing row       |
| `1`                    | `Left/…`   | no           | Nothing                       |
| `0`                    | any        | yes          | **Delete** existing row       |
| `0`                    | any        | no           | Nothing                       |

### 5.2 Rename / delete propagation

| Hook                        | Function                              | Effect                                                                |
|-----------------------------|---------------------------------------|------------------------------------------------------------------------|
| `Employee` `after_rename`   | `myhr.employee_hooks.after_rename_employee` | `frappe.rename_doc` on the matching `Employee Directory` row.   |
| `Employee` `on_trash`       | `myhr.employee_hooks.on_trash_employee`     | `frappe.delete_doc` on the matching `Employee Directory` row.   |

### 5.3 Read API — `myhr.api.get_employee_directory`

[`myhr/api.py`](../myhr/api.py)

```python
@frappe.whitelist()
def get_employee_directory():
    return frappe.db.sql("""
        select d.employee_id, d.employee_name, d.designation,
               d.department, d.mobile_number, d.employee_email
        from `tabEmployee Directory` d
        inner join `tabEmployee` e on e.name = d.employee_id
        where e.status = 'Active'
        order by d.employee_name asc
    """, as_dict=True)
```

| Property        | Behaviour                                                              |
|-----------------|-------------------------------------------------------------------------|
| Auth            | `@frappe.whitelist()` — any logged-in session.                          |
| Filtering       | **Inner join on `Employee.status='Active'`** — defense-in-depth filter. |
| Sort            | Alphabetical by `employee_name` ascending.                              |
| Permissions     | Global (no row-level filter — directory is a contact book).             |

### 5.4 Admin rebuild — `myhr.api.rebuild_employee_directory`

```python
@frappe.whitelist()
def rebuild_employee_directory():
    """HR/Admin only. Reseed directory from Employee. Returns {added, updated, removed}."""
```

- **Auth:** caller must hold `System Manager` or `HR Manager` role; otherwise `frappe.throw`.
- **Behaviour:** upserts every Employee with `custom_emp_directory=1, status='Active'` and removes any directory row that no longer qualifies.
- **Use cases:** post-bulk-import seeding, recovery from mass renames, manual refresh after data fixes.

### 5.5 Backfill patch (one-time)

`myhr/patches/v1_0_backfill_employee_directory.py` (registered in `patches.txt → post_model_sync`).

Runs on the next `bench migrate` after this version installs and seeds the directory from existing Employees. Idempotent — re-running is a no-op for already-synced rows.

### 5.6 Search (client-side)

In `EmployeeDirectory.vue` (`filteredEmployees` computed):

- Lowercases & trims the query.
- Substring-matches against `employee_name | designation | department | employee_id`.
- Re-evaluates synchronously on every keystroke.

### 5.7 Permissions (declared on the doctype)

| Role            | read | write | create | delete | export | print | report | share |
|-----------------|:----:|:-----:|:------:|:------:|:------:|:-----:|:------:|:-----:|
| System Manager  |  ✓   |   ✓   |   ✓    |   ✓    |   ✓    |   ✓   |   ✓    |   ✓   |
| HR Manager      |  ✓   |   ✓   |   ✓    |   ✓    |   ✓    |   ✓   |   ✓    |   ✓   |
| HR User (added by `setup.py`) | ✓ |   |        |        |   ✓    |   ✓   |   ✓    |       |
| Employee        |  ✓   |       |        |        |        |       |        |       |

These cover **desk** access. The PWA bypasses them by calling the whitelisted API. Directory writes happen only through `validate_employee` / patches running with `ignore_permissions=True`, so end-users never write to the doctype directly.

---

## 6. End-to-End Flows

### 6.1 HR adds a new employee

```
HR opens Employee form
  → fills in name, designation, department, cell, email
  → custom_emp_directory is pre-checked (default = 1)
  → status = Active
  → Save
        │
        ▼
Employee.validate fires → validate_employee()
        │
        ├─ if is_new(): doc.name := custom_employee_id (if provided)
        ├─ should_appear = True
        └─ upsert Employee Directory row
        │
Save commits.

Next PWA fetch → new colleague visible in /directory.
```

### 6.2 Employee browses & calls a colleague

```
PWA loads → Home → tap "Employee Directory"
        │
        ▼
View mounts → createResource auto-fires
        → GET /api/method/myhr.api.get_employee_directory
        → loading = true, employees = []
        ▼
Server returns only Active employees → employees = [...]; loading = false
        ▼
User types "priya" in search → filteredEmployees recomputes
        ▼
User taps Priya's row → expandedIds.add("EMP-002") → panel slides open
        ▼
User taps the phone button → navigator.dialer opens with +91… prefilled
```

### 6.3 HR marks an employee as Left

```
HR opens Employee form for EMP-099
  → status: Active → Left
  → Save
        │
        ▼
validate_employee → should_appear = False → delete_doc("Employee Directory", "EMP-099")
        │
PWA next refresh → employee no longer in list.
```

### 6.4 HR renames or deletes an employee

```
Rename:
  Employee renamed (e.g. EMP-099 → EMP-100)
        │
        ▼
after_rename_employee → frappe.rename_doc("Employee Directory", "EMP-099", "EMP-100")

Delete:
  Employee trashed
        │
        ▼
on_trash_employee → frappe.delete_doc("Employee Directory", "EMP-099")
```

### 6.5 HR runs a bulk rebuild

```
HR (or admin) calls /api/method/myhr.api.rebuild_employee_directory
        │
        ▼
For every Active employee with the flag → upsert
For every directory row whose Employee no longer qualifies → delete
        │
Returns { "added": 17, "updated": 94, "removed": 3 }.
```

---

## 7. Configuration / Setup

| Step                                | Where                                       | Idempotent | Notes                                                                          |
|-------------------------------------|---------------------------------------------|:----------:|---------------------------------------------------------------------------------|
| Create `Employee Directory` doctype | doctype JSON, applied by migrate            | ✓          | Standard Frappe doctype sync.                                                   |
| Add custom fields on Employee       | `setup.py → MYHR_CUSTOM_FIELDS`             | ✓          | Runs in `after_install` and `after_migrate`.                                    |
| Enforce permissions                 | `setup.py → MYHR_PERMISSIONS`               | ✓          | Adds the `HR User` row missing from the doctype JSON.                           |
| Backfill existing Employees         | `patches/v1_0_backfill_employee_directory`  | ✓          | Runs once on next migrate; safe to re-run.                                      |
| Wire `Employee` doc events          | `hooks.py → doc_events`                     | n/a        | `validate`, `after_insert`, `on_update`, `on_trash`, `after_rename`.            |
| Sync PWA frontend                   | `frontend_sync.apply_custom_ui()`           | ✓          | Triggered by `_apply_custom_ui_safe` in `after_migrate`. Skip with `MYHR_SKIP_FRONTEND_SYNC=1`. |

---

## 8. Manual Test Checklist

- [ ] Create new Active Employee with `custom_emp_directory = 1` → row appears in Directory after save.
- [ ] Edit the Employee's `cell_number` → expanded panel shows the new number on next fetch.
- [ ] Untick `custom_emp_directory`, save → row removed from Directory.
- [ ] Set Employee `status = Left` → row removed from Directory.
- [ ] Set Employee back to `Active` and re-tick the flag → row re-appears.
- [ ] Rename Employee in desk → directory row name follows.
- [ ] Trash Employee in desk → directory row is deleted.
- [ ] Log in as a regular `Employee` user → sees the full directory list (everyone-sees-everyone).
- [ ] Log in as `HR Manager` → also sees the full list.
- [ ] Run `bench execute myhr.api.rebuild_employee_directory` (as admin) → returns `{added, updated, removed}` summary.
- [ ] Search "engineer" → list narrows to designation match.
- [ ] Search clears → full list returns.
- [ ] Tap Phone button → dialer opens with the number prefilled.
- [ ] Tap Email button → mail composer opens with `to:` filled.
- [ ] Tap a card → expands; tap again → collapses.
- [ ] Expand two cards → both stay open simultaneously.
- [ ] Open `/directory` directly via URL → renders without bouncing through Home.

---

## 9. Live QA — Active-only behaviour (2026-04-25)

End-to-end verification that non-Active employees are dropped from the directory and from the API response (which is what the PWA renders).

### 9.1 Setup

- Site: `erp.localhost`
- Initial state: **111** Active employees with `custom_emp_directory=1` → **111** rows in `Employee Directory`.
- Test subjects (Active before the test):
  - `HR-EMP-00111` Rahul Singh
  - `HR-EMP-00110` Sanya Nair
  - `HR-EMP-00109` Tarun Rao

### 9.2 Steps & observed results

| Step | Action                                                       | Expected                                                                  | Observed                                                                  | ✅ / ❌ |
|------|--------------------------------------------------------------|---------------------------------------------------------------------------|---------------------------------------------------------------------------|:----:|
| 1    | `HR-EMP-00111`: status `Active → Left` + relieving_date set  | Directory row removed; absent from API.                                   | Row deleted (`exists` → None). API returned 108 rows; subject absent.     | ✅   |
| 2    | `HR-EMP-00110`: status `Active → Suspended`                  | Directory row removed; absent from API.                                   | Row deleted (`exists` → None). API still 108 rows; subject absent.        | ✅   |
| 3    | `HR-EMP-00109`: status `Active → Inactive`                   | Directory row removed; absent from API.                                   | Row deleted (`exists` → None). API still 108 rows; subject absent.        | ✅   |
| 4    | Aggregate row count after the 3 flips                        | 111 − 3 = **108** rows.                                                   | **108** rows.                                                             | ✅   |
| 5    | API call (`myhr.api.get_employee_directory`)                 | 108 rows; none of the 3 subjects present.                                 | 108 rows; all 3 subjects filtered out.                                    | ✅   |
| 6    | Restore all 3 to status `Active` and save                    | All 3 directory rows recreated; total back to 111.                        | All 3 rows present again; total **111**.                                  | ✅   |

### 9.3 What this confirms

- **`validate_employee` deletes the directory row** when status flips from Active → {Left, Suspended, Inactive}. Save-time pruning works for all three non-Active values.
- **The API's `INNER JOIN ... where e.status = 'Active'` filter holds** — independent defense layer behaved identically to the row count, so the API would still hide ex-employees even if a save-time deletion ever missed.
- **Re-Activating an Employee re-creates the directory row** via the same `validate_employee` upsert path. No backfill needed for re-hires / status-toggles.

### 9.4 PWA visibility (inferred, not browser-clicked)

The PWA view calls `myhr.api.get_employee_directory` directly (`createResource` with that URL — see [`frontend_changes/views/EmployeeDirectory.vue`](../myhr/frontend_changes/views/EmployeeDirectory.vue)). Since the API returned the filtered 108-row payload during step 5, the PWA list **will** render exactly those 108 rows. The 3 non-Active subjects cannot appear unless the API is changed.

### 9.5 Edge cases not covered yet

- **Race between desk save and an in-flight PWA fetch.** If a user has the directory open and HR marks someone Left, the user keeps the stale list until they refresh. No realtime invalidation. *Acceptable for v1; revisit if needed.*
- **Employee deleted entirely** (not just status-flipped): covered by the separate `on_trash_employee` hook — not part of this run, see test checklist item "Trash Employee in desk → directory row is deleted".
- **Renaming an Active employee mid-test:** covered by `after_rename_employee` — not exercised here.

---

## 10. Consultant-style read

> Backfilled retroactively (2026-04-25). Same shape as the Action Centre consultant section: who does what, scenario tables, friction points with numbered recommendations, and a ranked top-N. The technical spec above is "what is"; this section is "what should change".

### 10.1 Actors & streams

| Actor | What they do | Where |
|---|---|---|
| **Employee (any logged-in user)** | Browse, search, expand, tap-to-call, tap-to-email | PWA `/directory` |
| **HR Manager / System Manager** | Control who appears via the `custom_emp_directory` tick + Employee record fields; rebuild after bulk imports | ERPNext Desk |
| **System (hooks + scheduled patches)** | Auto-sync directory on Employee insert / update / status-flip / rename / trash | Server-side (no UI) |

Three independent streams of work flow through the feature:

1. **Visibility lifecycle** — who appears in the directory and when they drop out
2. **Discovery** — how an employee finds the colleague they're looking for
3. **Contact action** — what they do once they've found that colleague

### 10.2 Scenario flows

#### Stream 1: Visibility lifecycle

| # | Scenario | Trigger | Steps | Server | Result |
|---|---|---|---|---|---|
| A1 | New active employee created with flag ticked | HR creates Employee record | Save | `validate_employee` → `should_appear=True` → upsert directory row | Appears in next PWA fetch |
| A2 | Employee transferred to different department | HR edits Employee | Save | `validate_employee` → upsert (updates existing row) | Department field updates on next fetch |
| A3 | Employee marked Left | HR sets `status=Left` | Save | `should_appear=False` → delete directory row | Disappears on next fetch + filtered by API's INNER JOIN as defense |
| A4 | Employee restored to Active | HR sets `status=Active` again | Save | upsert recreates directory row | Reappears |
| A5 | HR unticks `custom_emp_directory` | HR opens Employee, unchecks the flag | Save | delete directory row | Disappears (intentional — for contractors, freelancers, etc. who shouldn't be in the contact book) |
| A6 | Employee renamed (e.g., merge of two records) | `rename_doc` | n/a | `after_rename_employee` → renames directory row | Same person, new ID; row tracks |
| A7 | Employee fully deleted | `frappe.delete_doc` | n/a | `on_trash_employee` → deletes directory row | Removed |
| A8 | Bulk import of 200 new employees | HR runs Data Import | Each save fires the validate hook | 200 rows inserted via per-save logic | Works, but slow; for clean reseed, HR can call `rebuild_employee_directory` |

#### Stream 2: Discovery

| # | Scenario | Steps | Server | UX notes |
|---|---|---|---|---|
| B1 | Open `/directory` from PWA home | Tap quick link | API returns full filtered list, sorted alphabetically | One round-trip fetches everyone |
| B2 | Search "priya" | Type in search bar | None — purely client-side filter | Instant. Substring across name/designation/dept/id |
| B3 | Search "9876" (phone fragment) | Type in search bar | None | **Currently doesn't match** — phone/email aren't in the search corpus (CR-4) |
| B4 | Tap a row to expand | Single tap | None | Expansion is local state; multiple rows can be expanded at once (intentional) |
| B5 | Browse without search | Scroll | None | At 100 employees, fine. At 1000+, no virtualization (CR-3) |

#### Stream 3: Contact action

| # | Scenario | Steps | What happens |
|---|---|---|---|
| C1 | Tap the phone button | Single tap on `tel:` link | Native dialer opens with the number prefilled |
| C2 | Tap the email button | Single tap on `mailto:` link | Native mail composer opens with `to:` prefilled |
| C3 | Phone number is mis-formatted | Display follows raw `cell_number` | Most dialers accept any format; aesthetics inconsistent (CR-6) |
| C4 | Want to share a colleague's contact externally | (Not implemented) | No "share to WhatsApp / copy contact card" affordance (CR-11) |

### 10.3 Friction points & recommendations

Numbered for reference. Grouped by theme.

#### Discovery & search

| ID | Problem | Recommendation |
|---|---|---|
| **CR-1** | No real-time refresh. If HR marks someone Left while a user has the directory open, the user keeps the stale list until manual refresh. | Subscribe to `Employee Directory` events via Frappe's pub/sub (`frappe.realtime.publish_realtime`). Re-trigger `acResource.reload()` on update. Low-cost; matches the realtime pattern used elsewhere in the HRMS app. |
| **CR-4** | Search ignores phone numbers and email addresses. Users sometimes have only a phone fragment ("9876…") or partial email ("@finance"). | Extend the substring match in `filteredEmployees` to also include `mobile_number` and `employee_email`. ~3 lines of Vue. No backend change. |
| **CR-7** | When the user has 5–6 rows expanded, finding new content requires scrolling. No "Collapse all" affordance. | Tiny "Collapse all" pill above the list, visible only when `expandedIds.size > 0`. One handler, one button. |
| **CR-8** | No department filter. Users currently search "engineering" but that's a text match — typos, sub-departments ("engineering – platform") fail. | Chip row of distinct departments at the top (computed from the API result). Tap a chip = filter; tap again = clear. Combinable with text search. |
| **CR-10** | No favourites. Daily users who chat with the same 5 colleagues scroll 100+ entries every time. | localStorage-backed starred contacts pinned at the top. No backend; just a `Set<employee_id>` in the browser. Star icon overlays the avatar. |

#### Visual & UX

| ID | Problem | Recommendation |
|---|---|---|
| **CR-2** | Avatars show initials only. `Employee.image` exists in standard Frappe — never surfaced. | Add `image` to the API SQL select; pass `image` through to the Vue `Avatar` component as the `image` prop. Falls back to initials when null. High delight, low cost. |
| **CR-5** | No on-leave indicator. Calling someone who's on PTO is small friction users learn the hard way. | Pull "is on approved Leave today" from the `Leave Application` doctype during `get_employee_directory`. Render a tiny "On leave" badge on the row. |
| **CR-6** | Phone number formatting is whatever HR typed in. Some are "+91 98765 43210", others "9876543210", others have dashes. Dialers handle all, but the visual is messy. | Normalise display only with `libphonenumber-js` (`format: 'INTERNATIONAL'`). The `tel:` href stays as the raw value (which dialers prefer). |

#### Adjacent features

| ID | Problem | Recommendation |
|---|---|---|
| **CR-9** | No org-chart / hierarchy view. `Employee.reports_to` exists but the directory is a flat list. | Out of scope for the directory itself. Worth a separate "Org Chart" feature using the same dataset. |
| **CR-11** | No quick "share contact" or "copy v-card" action. Common request when wanting to introduce a colleague to a vendor. | Long-press or three-dot menu on a row → "Share" (Web Share API) / "Copy contact". Falls back to clipboard on desktop. |
| **CR-12** | Employee can't update their own phone/email. Today they have to ask HR. | Allow the employee to edit their own `cell_number` and `company_email` from the `/profile` page; this auto-syncs into the directory via the existing `validate_employee` hook. Permissions tweak + Profile UI change. |

#### Scale (only when needed)

| ID | Problem | Recommendation |
|---|---|---|
| **CR-3** | All-rows fetch on every PWA load. Fine at current size; with 2000+ employees the payload (~600 KB) and render cost rise. (Same as F-8 in the audit findings.) | Server-side pagination + virtual scroll on the client. Defer until headcount > ~500 or until a real complaint surfaces. Premature today. |

### 10.4 What's actually unnecessary

Things to consider deleting or simplifying — they exist today but earn no keep:

1. **Mismatch between doctype JSON permissions and `setup.py → MYHR_PERMISSIONS`** (F-9). The `HR User` row is added by setup but missing from the JSON. Either add it to the JSON (one line, single source of truth) or drop the setup-script addition. Cosmetic, but every audit raises it.
2. **Print / Report / Export permissions on the directory doctype**. The directory is consumed entirely by the PWA via the API. Desk reports/exports of "Employee Directory" duplicate what `Employee` already supports. Could trim to just `read`/`write`/`create`/`delete` for HR roles and `read` for Employee — keep the surface tighter.
3. **`Employee Directory` track_changes is on**. Every edit logs a Version row. The directory is a derived projection of `Employee`; the source of truth tracking already lives on `Employee`. Turning off `track_changes` halves the row writes during bulk imports without losing audit value.

### 10.5 What NOT to change

These are decided trade-offs that look like friction but aren't:

- **Multiple-row simultaneous expansion** — intentional for side-by-side comparison; users explicitly liked it.
- **Client-side search** — responsive, no server load. Don't push to backend until scale forces it.
- **Everyone-sees-everyone visibility** — decided in §1. The directory is a contact book, not a personal record.
- **Belt-and-suspenders filter** (`validate_employee` deletion + INNER JOIN on Active) — looks redundant but each layer covers a different failure mode. Keep both.

### 10.6 Top 5 recommendations, ranked

If only some of these get done, do them in this order:

1. **CR-2** — Photos. ✅ **Shipped 2026-04-25.** `get_employee_directory` API now selects `Employee.image`; PWA Avatar consumes it. Currently 0/111 employees have a photo set on their Employee record — fall-back to initials still works. Photos appear automatically when HR uploads them.
2. **CR-4** — Search by phone/email. ✅ **Shipped 2026-04-25.** Filter now matches `employee_name + designation + department + employee_id + mobile_number + employee_email`. Placeholder updated to *"Search by name, role, dept, phone, email…"*.
3. **CR-12** — Self-service profile editing. 🚫 **Decided no** (2026-04-25). Phone / email lives on the `Employee` doctype which is HR-controlled. Employees route updates through HR, no self-edit affordance.
4. **CR-8** — Department filter chips. ✅ **Shipped 2026-04-25.** Single-select chip row above the search bar (hidden if ≤1 distinct department). "All" chip resets. Each chip shows the head-count. Combinable with text search. Empty-state has a "Clear filters" link when filters return zero.
5. **CR-10** — Starred contacts. 🚫 **Decided no** (2026-04-25).

Everything else (CR-1 realtime, CR-3 pagination, CR-5 on-leave, CR-6 phone formatting, CR-7 collapse-all, CR-9 org chart, CR-11 share contact) is reasonable but lower payoff. Defer until use-case data justifies them.

---

## 11. Resolved Findings (for the audit trail)

| ID  | Finding                                                                          | Status                                                                                         |
|-----|----------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| F-1 | Backfill missing (5 of 111 in directory).                                        | **Fixed** — `patches/v1_0_backfill_employee_directory.py` registered. Live count: 111/111.     |
| F-2 | Permission lie (docstring vs `ignore_permissions`).                              | **Fixed** — visibility decided as everyone-sees-everyone. `permissions.py` deleted. Docstring updated. Commented hooks block removed from `hooks.py`. |
| F-3 | `doc.name = custom_employee_id` ran on every save.                               | **Fixed** — gated by `if doc.is_new()`.                                                        |
| F-4 | No rename/trash propagation.                                                     | **Fixed** — `after_rename` + `on_trash` Employee hooks added.                                  |
| F-5 | Dead `frontend_overlay/EmployeeDirectory.vue` calling a non-existent endpoint.    | **Fixed** — file deleted.                                                                      |
| F-6 | No deletion path on flag-untick / non-Active.                                    | **Fixed** — `validate_employee` deletes the row when `should_appear` is False; API also filters by `Employee.status='Active'`. |
| F-7 | Magic `cell_number` field reference.                                             | **Open** — accepted as low risk; standard ERPNext field on v15 + v16.                          |
| F-8 | All-rows fetch on every PWA load.                                                | **Open** — fine at current headcount; revisit if list exceeds ~2000.                           |
| F-9 | `HR User` row inconsistency between doctype JSON and `setup.py`.                  | **Open** — cosmetic; documented in §5.7.                                                       |
| **DIR-1** (Phase 2) | HR-side direct edits to Directory rows (changing the displayed name, designation, department, mobile, or email) were silently overwritten on the next Employee save — Directory is auto-managed but write wasn't blocked. HR could spend time editing rows that wouldn't stick. | **RESOLVED 2026-04-26.** [`EmployeeDirectory.validate`](../myhr/myhr/doctype/employee_directory/employee_directory.py) throws unless `frappe.flags.allow_directory_write` is set by the sanctioned writers (`validate_employee`, `after_rename_employee`, `rebuild_employee_directory`). Verified live: direct save throws "Directory rows are auto-managed from Employee. Edit the source Employee record instead." |
| **DIR-2** (Phase 2) | No `on_trash` guard on Directory; HR could delete rows from Desk and the PWA would temporarily lose them until the next Employee save re-created them. | **RESOLVED 2026-04-26.** [`EmployeeDirectory.on_trash`](../myhr/myhr/doctype/employee_directory/employee_directory.py) refuses unless `frappe.flags.deleting_employee` (cascade from Employee `on_trash`) or `frappe.flags.allow_directory_write` (rebuild path) is set. Verified live: direct delete throws "Directory rows cannot be deleted directly". |
| **DIR-3** (Phase 2) | No HR-side audit endpoint for spotting orphan / missing / out-of-sync directory rows. | **RESOLVED 2026-04-26.** New whitelisted endpoint `myhr.api.get_directory_audit()` (HR-only). Returns `{orphan_directory_rows, missing_directory_rows, out_of_sync, summary}`. After running, HR can call `rebuild_employee_directory()` to auto-fix everything. Verified live: 9 directory rows, 0 orphans, 0 missing, 0 out-of-sync on the demo site. |
