# myHR — Complete Technical Documentation

> **App:** `myhr`  
> **Bench path:** `apps/myhr/`  
> **Site:** `erp.localhost`  
> **Built on top of:** Frappe HRMS (the `hrms` app)

---

## Table of Contents

1. [What is myHR?](#1-what-is-myhr)
2. [App Architecture Overview](#2-app-architecture-overview)
3. [File Structure](#3-file-structure)
4. [Custom DocTypes](#4-custom-doctypes)
   - 4.1 Employee Action Centre
   - 4.2 Employee Directory
   - 4.3 HR Policy
   - 4.4 Policy Action Task (child table)
5. [Custom Fields on Employee](#5-custom-fields-on-employee)
6. [Backend Logic — Python Files](#6-backend-logic--python-files)
   - 6.1 hooks.py
   - 6.2 setup.py
   - 6.3 employee_hooks.py
   - 6.4 api.py
   - 6.5 permissions.py
7. [Document Approval Workflow — Complete Logic](#7-document-approval-workflow--complete-logic)
   - 7.1 Status fields and their values
   - 7.2 Employee uploads a document
   - 7.3 Employee marks N/A
   - 7.4 Employee re-uploads a rejected document
   - 7.5 HR approves or rejects
   - 7.6 Master status sync
8. [HR Policy Acknowledgement Workflow](#8-hr-policy-acknowledgement-workflow)
9. [Badge Count / Notification Logic](#9-badge-count--notification-logic)
10. [Check-in Blocking Logic](#10-check-in-blocking-logic)
11. [Employee Directory](#11-employee-directory)
12. [Frontend — Shadow Pattern](#12-frontend--shadow-pattern)
    - 12.1 What the Shadow Pattern is
    - 12.2 Files that are overridden
    - 12.3 How to rebuild
13. [Frontend Views](#13-frontend-views)
    - 13.1 Home.vue
    - 13.2 EmployeeActionCentre.vue
    - 13.3 EmployeeDirectory.vue
14. [Frontend Components](#14-frontend-components)
15. [Role & Permission System](#15-role--permission-system)
16. [PWA / File Upload Approach](#16-pwa--file-upload-approach)
17. [Features Added vs Native Frappe HRMS](#17-features-added-vs-native-frappe-hrms)
18. [How to Install myHR on a New Bench](#18-how-to-install-myhr-on-a-new-bench)
19. [Build & Deploy Workflow](#19-build--deploy-workflow)
20. [Known Gotchas & Important Notes](#20-known-gotchas--important-notes)

---

## 1. What is myHR?

myHR is a **custom Frappe app** that sits on top of `frappe/erpnext/hrms` and extends the default HRMS mobile PWA with:

- **Employee Action Centre** — a document onboarding and compliance hub where employees upload mandatory documents, provide previous employer records, and acknowledge HR policies. HR admins can approve or reject each document.
- **Employee Directory** — a curated employee phonebook filtered by role.
- **Geo-fence bypass & present-by-default** — per-employee attendance control flags.
- **Policy-gated check-in** — employees cannot clock in until all mandatory documents are submitted and all HR policies are acknowledged.
- **Badge count** — the Action Centre quick link on the home screen shows a live count of pending actions.
- **PWA-first design** — all UI runs as a Progressive Web App on mobile and desktop browsers.

---

## 2. App Architecture Overview

```
User (browser/mobile)
      │
      ▼
Frappe HRMS PWA  ←── myHR overrides specific Vue files (Shadow Pattern)
      │
      ▼
Frappe backend (Python)
      │
      ├── myhr/api.py          ← Whitelisted API endpoints
      ├── myhr/employee_hooks.py ← Doc event hooks (validate, after_insert)
      ├── myhr/setup.py        ← Roles, permissions, custom fields (on install/migrate)
      └── myhr/hooks.py        ← Frappe hook registration
```

**Key principle:** myHR does not fork the HRMS frontend. It maintains its own `frontend_changes/` folder as the source of truth, and a sync script (`frontend_sync.py`) copies these files into the HRMS source tree before rebuilding. This means **every change must be made in `frontend_changes/`, never directly in `apps/hrms/`**.

---

## 3. File Structure

```
apps/myhr/
└── myhr/
    ├── hooks.py                     # Frappe app hooks (events, install, fixtures)
    ├── setup.py                     # Roles, permissions, custom fields setup
    ├── api.py                       # All @frappe.whitelist() API endpoints
    ├── employee_hooks.py            # Document event handlers (Employee, Employee Checkin)
    ├── permissions.py               # Role-based query conditions (currently inactive)
    ├── frontend_sync.py             # Copies frontend_changes → hrms and rebuilds
    │
    ├── frontend_changes/            # SOURCE OF TRUTH for all UI overrides
    │   ├── views/
    │   │   ├── Home.vue             # Home screen with quick links + badge count
    │   │   ├── EmployeeActionCentre.vue  # Full Action Centre UI
    │   │   ├── EmployeeDirectory.vue     # Employee phonebook
    │   │   └── TabbedView.vue       # Tab container layout
    │   ├── components/
    │   │   ├── BaseLayout.vue       # App shell with sidebar/bottom nav
    │   │   ├── BottomTabs.vue       # Mobile bottom navigation bar
    │   │   ├── QuickLinks.vue       # Quick link list with badge support
    │   │   ├── DesktopSidebar.vue   # Desktop left sidebar nav
    │   │   ├── InstallPrompt.vue    # PWA install banner
    │   │   └── icons/
    │   │       ├── ActionCentreIcon.vue
    │   │       ├── DirectoryIcon.vue
    │   │       └── ExpenseIcon.vue
    │   └── router/
    │       └── index.js             # Vue Router — adds custom routes
    │
    └── myhr/
        └── doctype/
            ├── employee_action_centre/   # Main onboarding DocType
            ├── employee_directory/       # Directory DocType
            ├── hr_policy/               # HR Policy DocType
            └── policy_action_task/      # Child table for policy acknowledgements
```

---

## 4. Custom DocTypes

### 4.1 Employee Action Centre

**Auto-name:** `AC-{####}` (e.g. AC-0009)  
**Auto-created:** on `after_insert` of Employee (via `employee_hooks.py`)

This is the core document. One record per employee. It tracks:

#### Mandatory Documents (3 cards)
| Field prefix | Document name |
|---|---|
| `aadhar` | Aadhar Card |
| `pan` | PAN Card |
| `education` | Highest Educational Qualification Certificate |

Each document card has 4 fields:
- `{prefix}_upload` — Attach field (stores file URL)
- `{prefix}_is_na` — Check (marks document as Not Applicable)
- `{prefix}_approval_status` — Select: `Pending / Awaiting HR / Accepted / Rejected`
- `{prefix}_remarks` — Text (HR's rejection reason)

#### Employer Records (5 slots, optional)
| Field prefix | Meaning |
|---|---|
| `employer_1` through `employer_5` | Previous employer history |

Each employer slot has:
- `employer_N_name` — Data
- `employer_N_from` — Date
- `employer_N_till` — Date
- `employer_N_doc` — Attach (Relieving / Experience Letter)
- `employer_N_is_na` — Check
- `employer_N_approval_status` — Select: `Pending / Awaiting HR / Accepted / Rejected`
- `employer_N_remarks` — Text

#### Policy Acknowledgements (child table)
- Child table field: `policies`
- Child DocType: `Policy Action Task`

#### Master Status Field
`status` — Select: `Pending / In Progress / To be Reviewed / Accepted / Action Required`

This rolls up from all individual card statuses (see Section 7.6).

---

### 4.2 Employee Directory

A lightweight phonebook DocType. **Auto-synced** whenever an Employee is saved with `custom_emp_directory = 1`.

Fields:
- `employee_id` — the `custom_employee_id` from Employee (also the document name)
- `employee_name`
- `designation`
- `department`
- `mobile_number`
- `employee_email`

Permissions are set via ERPNext's built-in role permissions (not via code hooks). HR Manager and HR User see all records; Employee role sees only their own.

---

### 4.3 HR Policy

Stores an HR policy document (PDF/file) that employees must acknowledge.

Fields:
- `policy_name` — Name of the policy
- `file` — Attach (the PDF file URL)

When an HR Policy is added to an Employee Action Centre's `policies` child table, the file URL is fetched from this DocType and served to the frontend for viewing.

---

### 4.4 Policy Action Task (child table)

Child of: Employee Action Centre (field: `policies`)

Fields:
- `hr_policy` — Link to HR Policy
- `status` — Select: `Pending / Acknowledged / Rejected`
- `acknowledged_at` — Datetime
- `ip_address` — Data (auto-captured on acknowledgement)
- `remarks` — Text (reason if rejected)

---

## 5. Custom Fields on Employee

All custom fields are created programmatically in `setup.py` using skip-if-exists logic. They are **not** in fixtures (to avoid overwriting fields on other developers' systems).

### Tab: HR Controls
A new tab added to the Employee form after the `bio` field.

| Fieldname | Label | Type | Default | Purpose |
|---|---|---|---|---|
| `custom_employee_id` | Employee ID | Data | — | Business-facing employee ID. Used as the Employee Directory document name. Must be unique. |
| `custom_emp_directory` | Add to Employee Directory | Check | 1 | When checked, this employee appears in the Employee Directory. When unchecked, they are excluded. |
| `custom_auto_present` | Present by Default | Check | 0 | For founders/senior management. Attendance is auto-marked Present daily unless a leave is applied. (Logic to be wired to attendance scheduler.) |
| `custom_bypass_geofence` | Bypass Geo-fence | Check | 0 | When checked, the employee can check in from any location. Location is still captured but the geo-fence radius is not enforced. |

---

## 6. Backend Logic — Python Files

### 6.1 hooks.py

Registers all Frappe hooks:

```python
after_install = "myhr.setup.after_install"
after_migrate = "myhr.setup.after_migrate"

doc_events = {
    "Employee": {
        "validate": "myhr.employee_hooks.validate_employee",
        "after_insert": "myhr.employee_hooks.after_employee_insert"
    },
    "Employee Checkin": {
        "validate": "myhr.employee_hooks.validate_checkin_action_centre"
    }
}
```

Fixtures export only Roles (not Custom Fields — those are managed by setup.py).

`permission_query_conditions` and `has_permission` are present in code but **commented out**. Permissions are managed via ERPNext's built-in Role Permissions Manager instead.

---

### 6.2 setup.py

Runs automatically on `bench install-app myhr` and every `bench migrate`.

Three responsibilities:

**a) `_ensure_roles()`**  
Creates three roles if they don't exist: `HR Manager`, `HR User`, `Employee`.

**b) `_enforce_permissions()`**  
Sets Custom DocPerm rows on `Employee Directory`:
- System Manager / HR Manager — full CRUD + export + share
- HR User — read + export + print only
- Employee — read only

Wipes and re-creates these rows on every migrate, so permission drift is auto-corrected.

**c) `_ensure_custom_fields()`**  
Creates all custom fields on Employee with skip-if-exists check:
```python
if frappe.db.exists("Custom Field", field_name):
    continue  # skip, don't overwrite
```
This makes it safe to install myHR on a system that already has some of these fields.

---

### 6.3 employee_hooks.py

**`validate_employee(doc, method)`**  
Fires on every Employee save. If `custom_emp_directory = 1` and `custom_employee_id` is set, it upserts the Employee Directory record with the latest name, designation, department, mobile, and company email.

**`after_employee_insert(doc, method)`**  
Fires once when a new Employee is created. Does two things:
1. Auto-creates an `Employee Action Centre` record linked to this employee.
2. If the employee has a `user_id`, adds a Frappe share on the Action Centre giving that user write access (so they can see and edit their own record in the portal).

**`validate_checkin_action_centre(doc, method)`**  
Fires on every `Employee Checkin` save (before it is committed to DB). This is the gate that blocks check-in. It does:

1. **Geo-fence bypass:** Reads `custom_bypass_geofence` from the Employee. If true, sets `doc.flags.skip_geofence = True` so downstream geo-fence validators know to skip the radius check for this employee.

2. **Mandatory document check:** Fetches the employee's Action Centre and checks Aadhar, PAN, and Education. If any of these has no file AND is not marked N/A, it collects them into a `missing_docs` list and calls `frappe.throw()` to abort the check-in with a user-visible error message.

3. **Policy acknowledgement check:** Counts any `Policy Action Task` rows where `status != "Acknowledged"`. If any exist, calls `frappe.throw()` with a count of pending policies.

Both throws prevent the `Employee Checkin` document from being saved.

---

### 6.4 api.py

All endpoints decorated with `@frappe.whitelist()` and called from the frontend via `createResource`.

---

#### `get_employee_directory()`
Returns all Employee Directory records (name, designation, department, mobile, email), ordered by name ascending. Uses `ignore_permissions=True` because permission filtering is done at the ERPNext role level.

---

#### `get_pending_actions_count()`
Returns:
```json
{ "count": 3, "has_pending_policies": false }
```

Logic:
1. Looks up the logged-in user's Employee record.
2. Looks up their Action Centre.
3. Counts missing mandatory documents: Aadhar, PAN, Education — each counts as 1 if no file AND not N/A.
4. Counts unacknowledged policies.
5. Returns total count + boolean for whether any policies are pending.

Used by the Home screen to show the badge bubble on the Action Centre quick link.

---

#### `get_employee_action_centre()`
Returns the full structured data for the current employee's Action Centre. Response shape:
```json
{
  "name": "AC-0009",
  "employee": "EMP-0001",
  "status": "In Progress",
  "documents": [
    {
      "key": "aadhar",
      "label": "Aadhar",
      "file": null,
      "is_na": 0,
      "status": "Pending",
      "remarks": ""
    }
  ],
  "employers": [
    {
      "key": "employer_1",
      "label": "Employer 1",
      "name": "Previous Tech Corp",
      "from_date": "2020-01-01",
      "till_date": "2023-12-31",
      "file": null,
      "is_na": 0,
      "status": "Pending",
      "remarks": ""
    }
  ],
  "policies": [
    {
      "name": "row-name",
      "hr_policy": "POSH 2026",
      "policy_name": "POSH 2026",
      "file": "/files/posh2026.pdf",
      "status": "Acknowledged",
      "acknowledged_at": "2026-04-08 13:53:05"
    }
  ]
}
```

---

#### `update_action_centre_field(name, fieldname, value)`
The main atomic save endpoint. Called every time an employee changes a single field (uploads a file, toggles N/A, etc.).

Special case: if `fieldname == "policy_action"`, it is routed to policy handling (deprecated path — now handled by dedicated `acknowledge_policy` / `reject_policy`).

For document fields:
1. Loads the Action Centre doc.
2. Sets the field.
3. If the field is in `status_map` (upload/NA fields), updates the corresponding `*_approval_status`:
   - If value is truthy and current status is `Pending` / `Rejected` / `""` → set to `Awaiting HR`
4. Calls `sync_master_status(doc)` to recalculate the master `status`.
5. Saves and commits.

---

#### `sync_master_status(doc)` _(internal function, not whitelisted)_
Recalculates document-level statuses and the master status field. Called after every field change.

For each mandatory prefix (aadhar, pan, education):
- If no file and not N/A: set approval_status to `Pending` (clear ghost `Awaiting HR`). Set `all_done = False`.
- If has data but status is `Pending`: promote to `Awaiting HR`.

For each employer slot (1–5):
- If empty and showing `Awaiting HR`: reset to `Pending`.

Final master status:
- All mandatory docs filled or N/A → `"To be Reviewed"`
- Otherwise → `"In Progress"`

---

#### `reupload_document(name, prefix, file_url)`
Called when an employee re-uploads a document that HR has already Rejected.

1. Reads the current status and remarks.
2. Creates a `Comment` on the Action Centre with the previous status/remarks as history (visible in Frappe's activity timeline).
3. Atomically updates:
   - File field → new file URL
   - Approval status → `Awaiting HR`
   - Remarks → `""` (cleared)
4. Calls `sync_master_status` and saves.

---

#### `acknowledge_policy(ac_name, row_name)`
Marks a specific policy row as `Acknowledged`. Records:
- `status = "Acknowledged"`
- `acknowledged_at = datetime.now()`
- `ip_address = frappe.local.request_ip`
- `remarks = ""` (clears any previous rejection reason)

---

#### `reject_policy(ac_name, row_name, reason)`
Marks a policy row as `Rejected`. Records:
- `status = "Rejected"`
- `remarks = reason`
- Clears `acknowledged_at` and `ip_address`

---

#### `reset_action_centre_field(name, fieldname, is_mandatory=0)`
Called when an employee clicks "Clear" on a card. Atomically wipes:
- File field → `""`
- `{prefix}_is_na` → `0`
- `{prefix}_approval_status` → `"Pending"`
- `{prefix}_remarks` → `""`

Then recalculates master status and saves.

---

### 6.5 permissions.py

Contains `get_employee_directory_conditions()` and `has_employee_directory_permission()`. These implement SQL-level row filtering so that:
- HR Manager / HR User / System Manager → see all Employee Directory records
- All others → see only the record where `employee_id` matches their linked Employee

**Currently inactive** — the hooks in `hooks.py` that register these are commented out. Permissions are instead managed through ERPNext's built-in Role Permissions Manager.

---

## 7. Document Approval Workflow — Complete Logic

### 7.1 Status fields and their values

Each document card (aadhar, pan, education, employer_1 … employer_5) has an `*_approval_status` field with these valid options:

| Value | Meaning |
|---|---|
| `Pending` | No file uploaded, not marked N/A |
| `Awaiting HR` | Employee has uploaded or marked N/A — waiting for HR to review |
| `Accepted` | HR has approved this document |
| `Rejected` | HR has rejected this document with a reason |

The master `status` field on the Action Centre has these valid options:

| Value | Meaning |
|---|---|
| `Pending` | Nothing started yet |
| `In Progress` | Some documents submitted but mandatory ones still missing |
| `To be Reviewed` | All mandatory documents submitted or marked N/A |
| `Accepted` | HR has fully accepted all documents |
| `Action Required` | HR has flagged something (used for manual HR communication) |

---

### 7.2 Employee uploads a document

**Flow:**
```
Employee taps Upload
  → triggerUpload(key, isMandatory) sets pending state, clicks hidden <input type="file">
  → onFileChosen(e) picks up the file
  → new FileAttachment(file).upload("Employee Action Centre", ac_name, "") 
       calls hrms.api.upload_base64_file (base64 encoded, no CSRF needed)
  → returns { file_url: "/private/files/..." }
  → handleDocSync(key, { file_url }, isMandatory) is called
  → update_action_centre_field(name, "{prefix}_upload", file_url) is called on backend
  → status_map triggers: approval_status → "Awaiting HR"
  → sync_master_status recalculates master status
  → Frontend reloads Action Centre data (acResource.reload())
```

**Why FileAttachment instead of frappe-ui FileUploader?**  
The frappe-ui `FileUploader` component uses XHR with `window.csrf_token`. In PWA mode, `csrf_token` is not reliably set on the window. `FileAttachment` (from `@/composables`) uses a Frappe API call that goes through `createResource`, avoiding this issue entirely.

---

### 7.3 Employee marks N/A

```
Employee checks "Not Applicable"
  → toggleNA(key, isMandatory, value) 
  → update_action_centre_field(name, "{prefix}_is_na", 1)
  → status_map triggers: approval_status → "Awaiting HR"
  → sync_master_status recalculates
```

Unchecking N/A (value = 0): status is set back through `reset_action_centre_field` or field sync, status reverts to `Pending`.

---

### 7.4 Employee re-uploads a rejected document

```
Employee taps Upload on a Rejected card
  → triggerUpload(key, isMandatory)
  → onFileChosen → FileAttachment.upload()
  → handleDocSync detects doc.status === "Rejected" for this key
  → calls reupload_document(name, prefix, file_url) instead of update_action_centre_field
  → Backend: creates Comment with previous status+remarks for history
  → Sets file = new URL, approval_status = "Awaiting HR", remarks = ""
  → sync_master_status recalculates
```

---

### 7.5 HR approves or rejects

HR does this through the **Frappe Desk** (not the PWA). They open the `Employee Action Centre` document and set individual `*_approval_status` fields to `Accepted` or `Rejected`, adding remarks if rejecting.

When an employee next opens their Action Centre:
- `Rejected` cards show a red border, the rejection reason, and a re-upload button.
- `Accepted` cards show a green badge.
- `Awaiting HR` cards show a clock icon in blue.

---

### 7.6 Master status sync

`sync_master_status(doc)` is called on every save. The logic:

```
all_done = True

For each mandatory prefix (aadhar, pan, education):
  if no file AND not N/A:
    if status was "Awaiting HR" → reset to "Pending"  (ghost cleanup)
    all_done = False
  elif status is "Pending" but has data:
    promote to "Awaiting HR"

For each employer slot (1-5):
  if empty AND status is "Awaiting HR":
    reset to "Pending"

master status = "To be Reviewed" if all_done else "In Progress"
```

**Important:** `sync_master_status` does NOT automatically set status to `Accepted`. That final step is done manually by HR on the Desk.

---

## 8. HR Policy Acknowledgement Workflow

### Setup (HR side)
1. HR creates an `HR Policy` record on Frappe Desk with a `policy_name` and attaches the PDF to `file`.
2. HR opens the employee's `Employee Action Centre` on Desk.
3. In the `Policy Acknowledgements` child table, HR adds a row linking to the HR Policy.

### Employee experience
1. Employee opens Action Centre → Policies section shows each linked policy with its status.
2. For each policy, the file URL is fetched from the `HR Policy` DocType in `get_employee_action_centre()`.
3. Employee taps **View** → opens the PDF.
4. Employee taps **Acknowledge** → `acknowledge_policy(ac_name, row_name)` is called.
   - Sets `status = "Acknowledged"`, records timestamp and IP address.
5. Employee taps **Decline** → enters a reason → `reject_policy(ac_name, row_name, reason)` is called.
   - Sets `status = "Rejected"`, stores reason in `remarks`.

### Check-in gate
Until all policies are Acknowledged, `validate_checkin_action_centre` blocks every check-in attempt with:
> "You have N unacknowledged HR Policies. Please acknowledge all policies in the Action Centre before checking in."

---

## 9. Badge Count / Notification Logic

### How count is calculated (`get_pending_actions_count`)

```
count = 0

For each of [aadhar_upload/aadhar_is_na, pan_upload/pan_is_na, education_upload/education_is_na]:
  if no file AND not N/A:
    count += 1          ← missing mandatory document

For each policy row:
  if status != "Acknowledged":
    count += 1          ← unacknowledged policy

return { count, has_pending_policies: (unacknowledged > 0) }
```

### Where it shows

**Home screen — Quick Links badge:**
- `Home.vue` fetches `get_pending_actions_count` on mount (`auto: true` createResource).
- The `quickLinks` computed array passes `badge: pendingActions.data?.count || 0` to the Action Centre item.
- `QuickLinks.vue` renders a red bubble badge next to the link title when `link.badge > 0`.

**Home screen — Policy warning banner:**
- If `pendingActions.data?.has_pending_policies` is true, an amber banner is shown above the Check-In panel telling the employee to go to Action Centre.

The badge does not auto-refresh (it loads once on mount). Navigating away and back to Home will re-trigger the resource.

---

## 10. Check-in Blocking Logic

Hooked at: `Employee Checkin → validate`  
File: `employee_hooks.py → validate_checkin_action_centre`

**Order of checks:**

1. **Geo-fence bypass flag:** If `custom_bypass_geofence = 1` on the Employee, set `doc.flags.skip_geofence = True`. This flag is read by geo-fence validators (e.g., the HRMS check-in handler) to skip radius enforcement for this employee.

2. **Missing mandatory documents:** Check Aadhar, PAN, Education. If any are missing (no file AND not N/A), throw:
   > "Please complete your Action Centre before checking in. Missing: Aadhar Card, PAN Card"

3. **Unacknowledged policies:** If any Policy Action Task row has `status != "Acknowledged"`, throw:
   > "You have 2 unacknowledged HR Policies. Please acknowledge all policies in the Action Centre before checking in."

Both `frappe.throw()` calls abort the document save, so the check-in is never created.

---

## 11. Employee Directory

### How records get into the Directory

When an Employee is saved (`validate` event):
- If `custom_emp_directory = 1` AND `custom_employee_id` is set:
  - If a Directory record with that employee_id exists → update it.
  - If not → create it.

The directory syncs: `employee_id`, `employee_name`, `designation`, `department`, `mobile_number` (from `cell_number`), `employee_email` (from `company_email`).

### How the frontend displays it

`get_employee_directory()` returns all records with `ignore_permissions=True`. ERPNext's built-in role permissions control visibility:
- HR Manager / HR User → see all employees
- Employee role → sees only their own record (configured in Role Permission Manager)

The `EmployeeDirectory.vue` view shows a searchable list with name, designation, department, email, and phone (tap-to-call).

---

## 12. Frontend — Shadow Pattern

### 12.1 What the Shadow Pattern is

The HRMS PWA frontend lives at `apps/hrms/frontend/src/`. myHR does **not** fork this or modify it directly. Instead:

- myHR keeps its modified versions of specific Vue/JS files in `apps/myhr/myhr/frontend_changes/`.
- A Python script (`frontend_sync.py`) copies these files over the originals in `apps/hrms/frontend/src/`, then triggers a Vite production build.
- The build output goes to `apps/hrms/public/frontend/` which is served by Frappe.

This means:
- **`frontend_changes/` is the only place you should edit.** Never edit files in `apps/hrms/frontend/src/` directly — they will be overwritten on next sync.
- The original HRMS files that are NOT overridden continue to work normally.

### 12.2 Files that are overridden

| myHR source | Overwrites in hrms |
|---|---|
| `views/Home.vue` | `src/views/Home.vue` |
| `views/EmployeeActionCentre.vue` | `src/views/EmployeeActionCentre.vue` |
| `views/EmployeeDirectory.vue` | `src/views/EmployeeDirectory.vue` |
| `views/TabbedView.vue` | `src/views/TabbedView.vue` |
| `components/BaseLayout.vue` | `src/components/BaseLayout.vue` |
| `components/BottomTabs.vue` | `src/components/BottomTabs.vue` |
| `components/QuickLinks.vue` | `src/components/QuickLinks.vue` |
| `components/DesktopSidebar.vue` | `src/components/DesktopSidebar.vue` |
| `components/InstallPrompt.vue` | `src/components/InstallPrompt.vue` |
| `components/icons/ActionCentreIcon.vue` | `src/components/icons/ActionCentreIcon.vue` |
| `components/icons/DirectoryIcon.vue` | `src/components/icons/DirectoryIcon.vue` |
| `components/icons/ExpenseIcon.vue` | `src/components/icons/ExpenseIcon.vue` |
| `router/index.js` | `src/router/index.js` |

### 12.3 How to rebuild

From the bench root (`ERP_Demo/`):

```bash
export PATH="$HOME/.local/bin:$PATH"
python3 apps/myhr/myhr/frontend_sync.py
bench --site erp.localhost clear-cache
```

The sync script:
1. Copies all override files from `frontend_changes/` → `apps/hrms/frontend/src/`
2. Runs `yarn build` inside `apps/hrms/frontend/`
3. Copies `index.html` → `hrms.html` (Frappe's entry point)

After running, hard-refresh the browser to get the new build.

---

## 13. Frontend Views

### 13.1 Home.vue

**What it does:**
- Renders the Check-In panel, Quick Links, and My Requests panel.
- On mount, fetches `get_pending_actions_count` via `createResource(auto: true)`.
- Passes a `badge` prop (the pending count) to the Action Centre item in `quickLinks`.
- Shows an amber warning banner above Check-In if `has_pending_policies` is true.
- `quickLinks` is a computed array (not static) so it reactively updates when the count loads.

**Key state:**
```javascript
const pendingActions = createResource({
  url: "myhr.api.get_pending_actions_count",
  auto: true,
})
const quickLinks = computed(() => [
  { icon: ActionCentreIcon, title: "Action Centre", route: "EmployeeActionCentre", badge: pendingActions.data?.count || 0 },
  ...
])
```

---

### 13.2 EmployeeActionCentre.vue

This is the most complex view. Key internals:

**Data loading:**
```javascript
const acResource = createResource({ url: "myhr.api.get_employee_action_centre", auto: true })
const acData = computed(() => acResource.data)
```

**File upload (native FileAttachment):**
```javascript
// One hidden input for all uploads
const fileInputRef = ref(null)
const pendingUploadKey = ref(null)
const pendingUploadIsMandatory = ref(false)

function triggerUpload(key, isMandatory) {
  pendingUploadKey.value = key
  pendingUploadIsMandatory.value = isMandatory
  fileInputRef.value.value = ""
  fileInputRef.value.click()
}

async function onFileChosen(e) {
  const file = e.target.files?.[0]
  const attachment = new FileAttachment(file)
  const fileDoc = await attachment.upload("Employee Action Centre", acData.value.name, "")
  await handleDocSync(pendingUploadKey.value, { file_url: fileDoc.file_url }, pendingUploadIsMandatory.value)
}
```

**Section collapsing:**
- `expandedSections` ref tracks which sections (docs, employers, policies) are open/closed.

**Policy actions:**
```javascript
const acknowledgeSync = createResource({ url: "myhr.api.acknowledge_policy" })
const rejectSync = createResource({ url: "myhr.api.reject_policy" })

async function handlePolicyAction(rowName, status) {
  if (status === 'Acknowledged') {
    await acknowledgeSync.submit({ ac_name, row_name: rowName })
  } else if (status === 'Rejected') {
    await rejectSync.submit({ ac_name, row_name: rowName, reason: rejectionReason.value })
  }
  acResource.reload()
}
```

---

### 13.3 EmployeeDirectory.vue

- Fetches all employees from `get_employee_directory()`.
- Client-side search filtering by name, designation, department.
- Each card shows avatar initials, name, designation, department, email (tap to mailto), phone (tap to tel).

---

## 14. Frontend Components

### QuickLinks.vue

Renders a list of cards. Each card has:
- Icon + title
- Optional badge bubble (red circle with count) — shown when `link.badge > 0`
- Chevron or download icon

Navigation: routes in `fullNavRoutes` (currently `EmployeeActionCentre` and `EmployeeDirectory`) use `window.location.href` for full-page navigation instead of Vue Router push. This ensures the Ionic page stack is cleared and the view loads fresh.

### BottomTabs.vue

5-tab mobile bottom bar: Home, Attendance, Leaves, Expenses, Salary.  
**Note:** The last tab was changed from Directory to Salary. The native HRMS did not have a Salary tab in the bottom bar.

### BaseLayout.vue

Wraps every page. Shows the Desktop Sidebar on large screens and the BottomTabs on mobile.

---

## 15. Role & Permission System

Three roles managed by myHR:

| Role | Desk Access | Purpose |
|---|---|---|
| `HR Manager` | Yes | Full CRUD on all HR documents. Can approve/reject Action Centre documents. |
| `HR User` | Yes | Read-only access to HR documents and directory. |
| `Employee` | No (portal only) | Can view own Action Centre and Employee Directory record. |

Roles are created on `after_install` and `after_migrate` if they don't already exist.

Employee Directory permissions (set via Custom DocPerm):
- System Manager → full
- HR Manager → full
- HR User → read/export/print only
- Employee → read only

**Important:** The `Employee` role alone does not restrict which records they see in the Directory. That filtering is done by ERPNext's built-in Role Permission Manager. If you want code-driven row-level filtering, uncomment `permission_query_conditions` in `hooks.py` and the corresponding functions in `permissions.py`.

---

## 16. PWA / File Upload Approach

### Why we use FileAttachment, not frappe-ui FileUploader

The frappe-ui `<FileUploader>` component uploads files via XHR and attaches `window.csrf_token` to the request header. In PWA mode (especially when the app is installed as a standalone PWA or accessed on mobile), `window.csrf_token` is often `undefined` because the token is injected into the page template but may not be available when the Vue component mounts.

The `FileAttachment` class (imported from `@/composables`) uses a different approach:
1. Reads the file as base64 using `FileReader`.
2. Calls `hrms.api.upload_base64_file` via Frappe's standard `createResource` (which uses the session cookie, no CSRF header needed).
3. Returns `{ file_url }` which is then saved to the Action Centre.

This works reliably in both PWA and browser modes.

### File type restrictions

The hidden file input uses:
```html
accept="image/jpeg,image/png,image/gif,image/webp,application/pdf,
        application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,
        text/plain,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
```

This matches Frappe's `ALLOWED_MIMETYPES` on the backend.

---

## 17. Features Added vs Native Frappe HRMS

| Feature | Native HRMS | myHR |
|---|---|---|
| Employee Action Centre (document onboarding) | ❌ | ✅ |
| Document upload with HR approval workflow | ❌ | ✅ |
| Previous employer records (5 slots) | ❌ | ✅ |
| HR Policy acknowledgement with timestamp + IP | ❌ | ✅ |
| Check-in blocked until documents + policies complete | ❌ | ✅ |
| Badge count on Action Centre quick link | ❌ | ✅ |
| Policy warning banner on home screen | ❌ | ✅ |
| Employee Directory (phonebook) | ❌ | ✅ |
| Directory auto-sync on Employee save | ❌ | ✅ |
| Geo-fence bypass flag per employee | ❌ | ✅ |
| Present by Default flag per employee | ❌ | ✅ |
| PWA install prompt | ❌ | ✅ |
| Desktop sidebar navigation | Limited | ✅ Enhanced |
| Salary tab in bottom bar | ❌ | ✅ |
| Role + permission auto-setup on install | ❌ | ✅ |

---

## 18. How to Install myHR on a New Bench

```bash
# 1. Get the app into the bench
bench get-app myhr /path/to/myhr  # or from git

# 2. Install on site
bench --site your-site install-app myhr

# 3. Run migrate (triggers setup.py — creates roles, permissions, custom fields)
bench --site your-site migrate

# 4. Build the frontend
python3 apps/myhr/myhr/frontend_sync.py

# 5. Clear cache and restart
bench --site your-site clear-cache
bench restart
```

**Safe on existing systems:** If `custom_employee_id` or other custom fields already exist on the Employee DocType, `setup.py` will skip them (skip-if-exists logic) and leave them untouched.

---

## 19. Build & Deploy Workflow

### Making a frontend change

1. Edit the file in `apps/myhr/myhr/frontend_changes/` — this is the only place.
2. Run the sync + build:
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   python3 apps/myhr/myhr/frontend_sync.py
   bench --site erp.localhost clear-cache
   ```
3. Hard-refresh the browser (Cmd+Shift+R / Ctrl+Shift+R).

### Making a backend change (Python)

1. Edit the file (`api.py`, `employee_hooks.py`, `setup.py`, etc.).
2. Restart the web process (Python is not hot-reloaded):
   ```bash
   pkill -f "bench serve"
   bench serve --port 8000
   ```
   Or if using `bench start`: restart the whole stack.
3. For DocType changes: run `bench migrate`.

### Adding a new custom field

Add it to `MYHR_CUSTOM_FIELDS` in `setup.py` and run `bench migrate`. Do NOT add it to fixtures — fixtures use upsert (overwrite) behavior and will clobber other developers' fields.

---

## 20. Known Gotchas & Important Notes

### 1. Frappe uses HTTP 417 for validation errors
Frappe's Python `frappe.throw()` returns a 417 status, not 500 or 422. The frontend `createResource` treats 417 as an error. If you see 417 responses, read the error message — it's a server-side validation error, not a client bug.

### 2. Select field option mismatch causes 417
If you try to save a value to a Select field that is not in the field's Options list, Frappe throws ValidationError (417). All `*_approval_status` fields must have `"Awaiting HR"` in their options. The `status` field must have `"To be Reviewed"` (NOT `"Completed"`). If you add new status values, update both the JSON and run `bench migrate`.

### 3. bench serve must be restarted for Python changes
`bench clear-cache` does NOT reload Python files. You must kill and restart the web process after any Python change.

### 4. frontend_changes is the source of truth — never edit hrms directly
Files in `apps/hrms/frontend/src/` that correspond to myHR overrides will be overwritten on every `frontend_sync.py` run. Any edits made there directly will be lost.

### 5. Custom fields safe on multi-developer systems
Custom fields are NOT in fixtures. They are created by `setup.py` with:
```python
if frappe.db.exists("Custom Field", field_name):
    continue
```
This means installing myHR on a system that already has these fields will not overwrite them.

### 6. Currency display
Currency is displayed dynamically using `formatCurrency(amount, doc.currency)`. The symbol shown (`$`, `₹`, etc.) is determined by the ERPNext Company's Default Currency setting. To display ₹, set the company's Default Currency to INR in ERPNext → Company settings.

### 7. Ionic Vue routing
The app uses Ionic Vue for page transitions. Tab-level routes (Attendance, Leaves, etc.) use `router.push()`. Routes that need a clean load (Action Centre, Employee Directory) use `window.location.href` to force a full navigation. This is by design — Ionic's route stack can cause stale state with Vue Router push for these views.

### 8. Policy acknowledgement IP capture
The employee's IP address is captured at acknowledgement time via `frappe.local.request_ip`. This is stored in the `Policy Action Task` row for audit purposes.

### 9. Auto-share on Employee creation
When an Employee is created with a `user_id`, `after_employee_insert` automatically adds a Frappe share on their `Employee Action Centre` giving that user write access. This is what allows them to see and edit their own record on the portal. If the Employee is created without `user_id` first, you must manually add the share or re-trigger the hook.

### 10. bench serve PATH issue
The `frontend_sync.py` script calls `bench clear-cache` via subprocess, which fails if `bench` is not on PATH. The build still succeeds. Run clear-cache manually:
```bash
export PATH="$HOME/.local/bin:$PATH"
bench --site erp.localhost clear-cache
```
