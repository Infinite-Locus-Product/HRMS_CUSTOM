# Employee Action Centre Logic (Backend + App)

This document explains how `Employee Action Centre` works across backend, Desk, and PWA frontend in `myhr`.

## 1) Where Logic Lives

- **DocType schema**: `apps/myhr/myhr/myhr/doctype/employee_action_centre/employee_action_centre.json`
- **DocType server class**: `apps/myhr/myhr/myhr/doctype/employee_action_centre/employee_action_centre.py`
- **Backend APIs**: `apps/myhr/myhr/api.py`
- **Employee lifecycle + check-in gate hooks**: `apps/myhr/myhr/employee_hooks.py`
- **Hook wiring**: `apps/myhr/myhr/hooks.py`
- **Desk form script**: `apps/myhr/myhr/myhr/doctype/employee_action_centre/employee_action_centre.js`
- **PWA Action Centre page**: `apps/myhr/myhr/frontend_changes/views/EmployeeActionCentre.vue`

---

## 2) Data Model Summary

The parent doctype `Employee Action Centre` stores:

- Employee identity:
  - `employee`
  - `employee_name`
  - `status` (master status: `Pending`, `In Progress`, `To be Reviewed`, `Accepted`, `Action Required`)
- Mandatory personal docs:
  - `aadhar_upload`, `aadhar_is_na`, `aadhar_approval_status`, `aadhar_remarks`
  - `pan_upload`, `pan_is_na`, `pan_approval_status`, `pan_remarks`
  - `education_upload`, `education_is_na`, `education_approval_status`, `education_remarks`
- Employer history (`employer_1` to `employer_5`) with name/from/till + doc approval fields
- Employer 1 split previous-employer docs (most recent org):
  - Offer letter (mandatory)
  - Increment letter (optional)
  - Last month payslip (mandatory)
  - Last-to-last month payslip (mandatory)
  - Month-before-that payslip (mandatory)
  - Relieving/resignation doc (mandatory)
- Policies child table:
  - `policies` (child doctype `Policy Action Task`)
- Activity logs:
  - `activity_logs`

`Policy Action Task` rows track:
- `hr_policy`
- `status` (`Pending` or `Acknowledged`)
- `acknowledged_at`
- `ip_address`

---

## 3) Record Creation and Auto-Maintenance

### Employee-side hooks

`employee_hooks.py` does this:

1. On Employee validate (`validate_employee`):
   - syncs/creates `Employee Directory`
2. On Employee insert/update:
   - `_ensure_action_centre()` creates `Employee Action Centre` if missing
   - shares it with employee user if `user_id` exists

### Action Centre server validation

`employee_action_centre.py`:

- `validate()` calls:
  - `_sync_employee_name()` to keep `employee_name` aligned with Employee
  - `_ensure_policy_rows()` to auto-add rows for all `HR Policy` records

This guarantees policy coverage in Action Centre even when new policies are created later.

---

## 4) Backend API Flows (`api.py`)

## 4.1 Read API

`get_employee_action_centre()`:
- Resolves current session user to Employee.
- Loads employee's Action Centre doc.
- Returns structured payload:
  - `documents` (Aadhar/PAN/Education)
  - `employers` (1..5, with Employer 1 containing nested split doc rows)
  - `policies`

## 4.2 Update APIs

### `update_action_centre_field(name, fieldname, value)`
- Generic field patch endpoint.
- Uses `status_map` to map changed file/N-A fields to corresponding `*_approval_status`.
- If a file/N-A value is set and current status is `Pending/Rejected`, moves row to `Awaiting HR`.
- Calls `sync_master_status(doc)` then saves atomically.

### `reupload_document(name, prefix, file_url)`
- Used for rejected doc re-upload.
- Logs previous status/remarks as comment.
- Sets file field + status `Awaiting HR` + clears remarks.
- Calls `sync_master_status(doc)` and saves.

### `reset_action_centre_field(name, fieldname, is_mandatory=0)`
- Clears target file.
- Clears N/A (if field exists for that prefix).
- Resets status to `Pending`.
- Clears remarks.
- Calls `sync_master_status(doc)` and saves.

### `acknowledge_policy(ac_name, row_name)` / `reject_policy(ac_name, row_name, reason)`
- Updates policy row status in child table.

---

## 5) Master Status Engine (`sync_master_status`)

`sync_master_status(doc)` is the central status calculator.

Current behavior:

1. Mandatory set used for master completion:
   - `aadhar`, `pan`, `education`
2. For each mandatory prefix:
   - if both file and N/A are empty, row is treated incomplete
   - if row had ghost `Awaiting HR` without data, it is corrected to `Pending`
   - if row has data but status still `Pending`, corrected to `Awaiting HR`
3. Employer rows are sanity-corrected (avoid stale `Awaiting HR` without file)
4. Final parent status:
   - `To be Reviewed` if all mandatory rows complete
   - else `In Progress`

Important: parent `To be Reviewed` is currently tied to Aadhar/PAN/Education completeness, not all employer records.

---

## 6) Policy-Based Attendance Gating

`validate_checkin_action_centre()` in `employee_hooks.py`:

- skips system-generated auto check-ins (`device_id == "myHR Auto"`)
- loads employee's Action Centre policies
- checks linked `HR Policy.mandatory_check_in_block`
- blocks check-in if any mandatory policy row is not `Acknowledged`

This is the runtime gate ensuring mandatory policy compliance before attendance action.

---

## 7) Desk Form Behavior (`employee_action_centre.js`)

For non-HR users:
- HR-only fields are forced read-only
- if parent status is `To be Reviewed` or `Accepted`, full form is read-only
- on validate:
  - if Aadhar/PAN/Education mandatory trio completed -> sets `To be Reviewed`
  - else if some data exists and status was `Pending` -> sets `In Progress`

For HR users:
- prevents marking a row `Accepted` when neither file nor N/A exists
- aggregates row statuses:
  - any `Rejected` -> parent `Action Required`
  - all accepted -> parent `Accepted`

---

## 8) PWA Frontend Flow (`EmployeeActionCentre.vue`)

Page behavior:

- loads Action Centre via `myhr.api.get_employee_action_centre`
- renders sections:
  - Required docs
  - Employer records
  - Policy acknowledgements
- upload flow:
  - uploads to File doctype first
  - then calls update/reupload endpoint
- clear flow:
  - calls `reset_action_centre_field`
- policy acknowledge flow:
  - calls `acknowledge_policy`

UI status badges are derived from row status and row data (`Pending`, `Awaiting HR`, `Accepted/Approved`, `Rejected`).

---

## 9) Hook Wiring and Scheduling

`hooks.py` wires:

- employee event handlers in `employee_hooks.py`
- check-in validation gate
- scheduler events:
  - weekday 09:00 auto IN
  - weekday 18:00 auto OUT

These auto check-ins are tagged with device id `myHR Auto` to bypass policy gate.

---

## 10) Operational Notes

- Backend APIs are atomic and call `sync_master_status` after field-level transitions.
- Parent status can be influenced by both API layer and Desk script logic.
- Policy rows are auto-expanded by `EmployeeActionCentre.validate()`, so policy set stays current.
- If you change mandatory definition for parent completion, update both:
  - `sync_master_status` in `api.py`
  - non-HR validate branch in `employee_action_centre.js`

