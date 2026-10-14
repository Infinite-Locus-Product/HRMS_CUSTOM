# DocType Layout Manifest — myHR v16

> **Mirror of:** `apps/atbhr/docs/DOCTYPE_LAYOUT_MANIFEST.md` (v15). Both copies are byte-identical modulo namespace (`atbhr` ↔ `myhr`, `atbHR` ↔ `myHR`).
>
> **Generated:** 2026-04-27. **Source:** read-only audit of `apps/atbhr/atbhr/` and `apps/myhr/myhr/`. No source files modified.

This manifest enumerates every HR-related doctype touched by atbhr/myhr — both **owned** doctypes (defined in `atbhr/atbhr/doctype/` or `myhr/myhr/doctype/`) and **stock** doctypes (Frappe / ERPNext / HRMS) extended via Custom Fields, Property Setters, or `override_doctype_class`.

The "Tab" column is the user-visible tab the field renders under (derived by walking the `field_order` from the nearest preceding Tab Break). The "Section" column is the Section Break label within that tab. Custom Fields not present in the JSON are placed by walking `insert_after` against the stock JSON.

---

## Table of contents

1. [Owned doctypes — atbhr / myhr](#owned-doctypes--atbhr--myhr)
   - [HR Policy](#hr-policy)
   - [Policy Acknowledgement](#policy-acknowledgement)
   - [Policy Audit Log](#policy-audit-log)
   - [Policy Filter Department](#policy-filter-department)
   - [Policy Filter Designation](#policy-filter-designation)
   - [Policy Filter Branch](#policy-filter-branch)
   - [Policy Filter Employment Type](#policy-filter-employment-type)
   - [Policy Filter Employee](#policy-filter-employee)
   - [Employee Directory](#employee-directory)
   - [Employee Action Centre](#employee-action-centre)
   - [Action Centre Activity](#action-centre-activity)
2. [Stock doctypes extended by atbhr / myhr](#stock-doctypes-extended-by-atbhr--myhr)
   - [Employee (ERPNext)](#employee-erpnext)
   - [Holiday (ERPNext, used by HRMS)](#holiday-erpnext-used-by-hrms)
   - [Leave Application (HRMS)](#leave-application-hrms)
   - [Attendance Request (HRMS)](#attendance-request-hrms)
   - [Employee Checkin (HRMS)](#employee-checkin-hrms)
   - [Holiday List / Leave Period / Leave Type (HRMS)](#holiday-list--leave-period--leave-type-hrms)
3. [Cross-verification: atbhr v15 vs myhr v16](#cross-verification-atbhr-v15-vs-myhr-v16)
4. [Property Setters declared by atbhr / myhr](#property-setters-declared-by-atbhr--myhr)
5. [Override class wiring](#override-class-wiring)
6. [Aggregate verdict](#aggregate-verdict)

---

# Owned doctypes — atbhr / myhr

## HR Policy

**Source:** atbhr-owned / myhr-owned
**File (v15):** [`hr_policy.json`](../myhr/myhr/doctype/hr_policy/hr_policy.json) · **(v16):** `myhr/myhr/doctype/hr_policy/hr_policy.json`
**Naming:** `format:POL-{####}` · **Module:** `atbHR` (v15) / `myHR` (v16) · **No tabs** (single-tab form)

### Field-by-field layout

| # | Fieldname | Label | Fieldtype | Tab | Section | Options/Default | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `policy_name` | Policy Name | Data | — | (default) | reqd | in_list_view |
| 2 | `category` | Category | Select | — | (default) | `Leave\nPOSH\nGratuity\nGeneral` (default `General`) | in_list_view |
| 3 | `is_active` | Active | Check | — | (default) | default `1` | in_list_view |
| 4 | `version` | Version | Int | — | (default) | default `1`, read_only | auto-bumped on file change |
| 5 | `column_break_meta` | — | Column Break | — | (default) | — | — |
| 6 | `mandatory_check_in_block` | Mandatory Check-in Block | Check | — | (default) | default `0` | gates Checkin & AR submit |
| 7 | `section_break_file` | Policy Document | Section Break | — | Policy Document | — | — |
| 8 | `file` | Policy File | Attach | — | Policy Document | reqd | — |
| 9 | `description` | Description | Small Text | — | Policy Document | — | — |
| 10 | `section_break_scope` | Applicability | Section Break | — | Applicability | — | — |
| 11 | `applies_to_all_employees` | Applies to All Employees | Check | — | Applicability | default `1` | — |
| 12 | `applicability_logic` | Applicability Logic | Select | — | Applicability | `OR\nAND` (default `OR`) | depends_on `!applies_to_all_employees` |
| 13 | `applicable_departments` | Applicable Departments | Table | — | Applicability | child: `Policy Filter Department` | depends_on `!applies_to_all_employees` |
| 14 | `applicable_designations` | Applicable Designations | Table | — | Applicability | child: `Policy Filter Designation` | depends_on `!applies_to_all_employees` |
| 15 | `applicable_branches` | Applicable Branches | Table | — | Applicability | child: `Policy Filter Branch` | depends_on `!applies_to_all_employees` |
| 16 | `applicable_employment_types` | Applicable Employment Types | Table | — | Applicability | child: `Policy Filter Employment Type` | depends_on `!applies_to_all_employees` |
| 17 | `applicable_employees` | Manual Employee Override | Table | — | Applicability | child: `Policy Filter Employee` | depends_on `!applies_to_all_employees` |

### Permissions (in JSON, identical v15/v16)

| Role | read | write | create | delete | export | print | report | share | email |
|---|---|---|---|---|---|---|---|---|---|
| System Manager | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 |
| HR Manager | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 |
| Employee | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

---

## Policy Acknowledgement

**Source:** atbhr-owned / myhr-owned
**File (v15):** [`policy_acknowledgement.json`](../myhr/myhr/doctype/policy_acknowledgement/policy_acknowledgement.json)
**Naming:** `format:PA-{####}` · single-tab form

### Field-by-field layout

| # | Fieldname | Label | Fieldtype | Tab | Section | Options/Default | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `employee` | Employee | Link | — | (default) | options `Employee`, reqd | in_list_view, in_standard_filter |
| 2 | `employee_name` | Employee Name | Data | — | (default) | read_only | fetch_from `employee.employee_name` |
| 3 | `column_break_1` | — | Column Break | — | (default) | — | — |
| 4 | `hr_policy` | HR Policy | Link | — | (default) | options `HR Policy`, reqd | in_list_view, in_standard_filter |
| 5 | `policy_name` | Policy Name | Data | — | (default) | read_only | fetch_from `hr_policy.policy_name` |
| 6 | `section_break_status` | Status | Section Break | — | Status | — | — |
| 7 | `policy_version` | Policy Version | Int | — | Status | default `1`, read_only | in_list_view |
| 8 | `status` | Status | Select | — | Status | `Pending\nAcknowledged\nSuperseded\nWithdrawn` (default `Pending`), read_only | in_list_view, in_standard_filter |
| 9 | `column_break_2` | — | Column Break | — | Status | — | — |
| 10 | `acknowledged_at` | Acknowledged At | Datetime | — | Status | read_only | server-stamped, immutable post-set |
| 11 | `ip_address` | IP Address | Data | — | Status | read_only | server-stamped, immutable post-set |
| 12 | `section_break_super` | Versioning | Section Break | — | Versioning | depends_on `status==='Superseded' \|\| superseded_by` | — |
| 13 | `superseded_by` | Superseded By | Link | — | Versioning | options `Policy Acknowledgement`, read_only | self-link to newer PA |

### Permissions

| Role | read | write | create | delete | export | print | report | share | email |
|---|---|---|---|---|---|---|---|---|---|
| System Manager | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| HR Manager | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Employee | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

---

## Policy Audit Log

**Source:** atbhr-owned / myhr-owned (append-only)
**File (v15):** [`policy_audit_log.json`](../myhr/myhr/doctype/policy_audit_log/policy_audit_log.json)
**Naming:** `format:PAL-{####}` · single-tab form · `track_changes: 0`

### Field-by-field layout

| # | Fieldname | Label | Fieldtype | Tab | Section | Options/Default | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `policy_acknowledgement` | Policy Acknowledgement | Link | — | (default) | options `Policy Acknowledgement`, read_only, reqd | in_list_view, in_standard_filter |
| 2 | `employee` | Employee | Link | — | (default) | options `Employee`, read_only | in_list_view, in_standard_filter |
| 3 | `hr_policy` | HR Policy | Link | — | (default) | options `HR Policy`, read_only | in_standard_filter |
| 4 | `policy_version` | Policy Version | Int | — | (default) | read_only | — |
| 5 | `column_break_1` | — | Column Break | — | (default) | — | — |
| 6 | `from_status` | From Status | Data | — | (default) | read_only | empty on initial-insert row |
| 7 | `to_status` | To Status | Data | — | (default) | read_only, reqd | in_list_view, in_standard_filter |
| 8 | `via` | Via | Select | — | (default) | `ORM\nAPI\nSQL\nMigration\nReconcile\nBulkAck\nDeactivate\nVersionBump`, read_only, reqd | in_list_view, in_standard_filter |
| 9 | `section_break_who` | Actor | Section Break | — | Actor | — | — |
| 10 | `actor` | Actor | Link | — | Actor | options `User`, read_only | — |
| 11 | `actor_ip` | Actor IP | Data | — | Actor | read_only | — |
| 12 | `note` | Note | Small Text | — | Actor | read_only | — |

### Permissions (read-only for HR / SysMgr — no create/write/delete)

| Role | read | write | create | delete | export | print | report | share | email |
|---|---|---|---|---|---|---|---|---|---|
| System Manager | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 |
| HR Manager | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 |

---

## Policy Filter Department

**Source:** atbhr-owned / myhr-owned · **Child table** of `HR Policy.applicable_departments`
**File (v15):** [`policy_filter_department.json`](../myhr/myhr/doctype/policy_filter_department/policy_filter_department.json)
**`istable: 1`**, no permissions block (inherits from parent)

| # | Fieldname | Label | Fieldtype | Options | Notes |
|---|---|---|---|---|---|
| 1 | `department` | Department | Link | `Department` | reqd, in_list_view; parent: `HR Policy.applicable_departments` |

---

## Policy Filter Designation

**Source:** atbhr-owned / myhr-owned · **Child table** of `HR Policy.applicable_designations`
**File (v15):** [`policy_filter_designation.json`](../myhr/myhr/doctype/policy_filter_designation/policy_filter_designation.json) · `istable: 1`

| # | Fieldname | Label | Fieldtype | Options | Notes |
|---|---|---|---|---|---|
| 1 | `designation` | Designation | Link | `Designation` | reqd, in_list_view; parent: `HR Policy.applicable_designations` |

---

## Policy Filter Branch

**Source:** atbhr-owned / myhr-owned · **Child table** of `HR Policy.applicable_branches`
**File (v15):** [`policy_filter_branch.json`](../myhr/myhr/doctype/policy_filter_branch/policy_filter_branch.json) · `istable: 1`

| # | Fieldname | Label | Fieldtype | Options | Notes |
|---|---|---|---|---|---|
| 1 | `branch` | Branch | Link | `Branch` | reqd, in_list_view; parent: `HR Policy.applicable_branches` |

---

## Policy Filter Employment Type

**Source:** atbhr-owned / myhr-owned · **Child table** of `HR Policy.applicable_employment_types`
**File (v15):** [`policy_filter_employment_type.json`](../myhr/myhr/doctype/policy_filter_employment_type/policy_filter_employment_type.json) · `istable: 1`

| # | Fieldname | Label | Fieldtype | Options | Notes |
|---|---|---|---|---|---|
| 1 | `employment_type` | Employment Type | Link | `Employment Type` | reqd, in_list_view; parent: `HR Policy.applicable_employment_types` |

---

## Policy Filter Employee

**Source:** atbhr-owned / myhr-owned · **Child table** of `HR Policy.applicable_employees`
**File (v15):** [`policy_filter_employee.json`](../myhr/myhr/doctype/policy_filter_employee/policy_filter_employee.json) · `istable: 1`

| # | Fieldname | Label | Fieldtype | Options | Notes |
|---|---|---|---|---|---|
| 1 | `employee` | Employee | Link | `Employee` | reqd, in_list_view; parent: `HR Policy.applicable_employees` |
| 2 | `employee_name` | Employee Name | Data | — | read_only, in_list_view; fetch_from `employee.employee_name` |

---

## Employee Directory

**Source:** atbhr-owned / myhr-owned
**File (v15):** [`employee_directory.json`](../myhr/myhr/doctype/employee_directory/employee_directory.json)
**Naming:** `field:employee_id` (so the doc `name` IS the Employee ID) · single-tab form
**Perm strategy:** JSON ships baseline; runtime perms re-applied every migrate via `setup.py:_enforce_permissions` (SysMgr/HR Manager full, HR User read+report, Employee read-only).

### Field-by-field layout

| # | Fieldname | Label | Fieldtype | Tab | Section | Notes |
|---|---|---|---|---|---|---|
| 1 | `employee_id` | Employee ID | Data | — | (default) | reqd, unique, in_list_view |
| 2 | `employee_name` | Employee Name | Data | — | (default) | reqd, in_list_view |
| 3 | `designation` | Designation | Data | — | (default) | in_list_view |
| 4 | `department` | Department | Data | — | (default) | in_list_view |
| 5 | `mobile_number` | Mobile Number | Data | — | (default) | — |
| 6 | `employee_email` | Company Email | Data | — | (default) | — |

### Permissions (JSON baseline, then enforced by `setup.py:35`)

| Role | read | write | create | delete | export | print | report | share |
|---|---|---|---|---|---|---|---|---|
| System Manager | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| HR Manager | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| HR User | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 |
| Employee | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

---

## Employee Action Centre

**Source:** atbhr-owned / myhr-owned
**File (v15):** [`employee_action_centre.json`](../myhr/myhr/doctype/employee_action_centre/employee_action_centre.json)
**Naming:** `format:AC-{####}` · **Multi-tab form** with permlevel-1 fields

### Tab inventory

| Tab | Tab fieldname | Anchors |
|---|---|---|
| (default — header strip) | — | `employee` … `submitted_by` |
| Required Documents | `tab_required_docs` | Aadhar, PAN, Education |
| Most Recent Employer | `tab_recent_employer` | employer_1_* |
| Previous Employers | `tab_previous_employers` | employer_2..5_* |
| Activity Log | `tab_activity` | `activity_logs` |

### Field-by-field layout (grouped by tab)

#### Header strip (above first Tab Break)

| # | Fieldname | Label | Fieldtype | Section | Options/Default | Notes |
|---|---|---|---|---|---|---|
| 1 | `employee` | Employee | Link | (default) | options `Employee`, reqd | in_list_view |
| 2 | `employee_name` | Employee Name | Data | (default) | read_only | fetch_from `employee.employee_name`; in_list_view |
| 3 | `status` | Status | Select | (default) | `Pending\nIn Progress\nReady to Submit\nTo be Reviewed\nAccepted\nAction Required` (default `Pending`), read_only, **permlevel 1** | in_list_view; HR-only edit |
| 4 | `submitted_for_review` | Submitted for Review | Check | (default) | default `0`, read_only | — |
| 5 | `submitted_on` | Submitted On | Datetime | (default) | read_only | server-stamped, immutable |
| 6 | `submitted_by` | Submitted By | Link | (default) | options `User`, read_only | server-stamped, immutable |

#### Tab: Required Documents (`tab_required_docs`)

| # | Fieldname | Label | Fieldtype | Section | Options/Default | Notes |
|---|---|---|---|---|---|---|
| 7 | `sb_aadhar` | Aadhar | Section Break | Aadhar | — | — |
| 8 | `aadhar_upload` | Aadhar Upload | Attach | Aadhar | — | — |
| 9 | `aadhar_is_na` | Not Applicable | Check | Aadhar | default `0` | — |
| 10 | `cb_aadhar_status` | — | Column Break | Aadhar | — | — |
| 11 | `aadhar_approval_status` | HR Status | Select | Aadhar | `Pending\nAwaiting HR\nAccepted\nRejected` (default `Pending`), **permlevel 1** | HR-only edit |
| 12 | `aadhar_remarks` | HR Remarks | Small Text | Aadhar | **permlevel 1** | HR-only edit |
| 13 | `sb_pan` | PAN | Section Break | PAN | — | — |
| 14 | `pan_upload` | PAN Upload | Attach | PAN | — | — |
| 15 | `pan_is_na` | Not Applicable | Check | PAN | default `0` | — |
| 16 | `cb_pan_status` | — | Column Break | PAN | — | — |
| 17 | `pan_approval_status` | HR Status | Select | PAN | `Pending\nAwaiting HR\nAccepted\nRejected`, **permlevel 1** | HR-only edit |
| 18 | `pan_remarks` | HR Remarks | Small Text | PAN | **permlevel 1** | HR-only edit |
| 19 | `sb_education` | Highest Educational Qualification Certificate | Section Break | Education | — | — |
| 20 | `education_upload` | Education Certificate | Attach | Education | — | — |
| 21 | `education_is_na` | Not Applicable | Check | Education | default `0` | — |
| 22 | `cb_education_status` | — | Column Break | Education | — | — |
| 23 | `education_approval_status` | HR Status | Select | Education | `Pending\nAwaiting HR\nAccepted\nRejected`, **permlevel 1** | HR-only edit |
| 24 | `education_remarks` | HR Remarks | Small Text | Education | **permlevel 1** | HR-only edit |

#### Tab: Most Recent Employer (`tab_recent_employer`)

Six section blocks: Employment Period, Offer Letter, Increment Letter, Pay Slip — Last Month, Pay Slip — Last-to-Last Month, Pay Slip — Month Before That, Relieving Letter / Resignation Acceptance. Pattern repeats per section: `<section_break> → <attach doc> → <column_break> → <approval_status Select permlevel 1> → <remarks Small Text permlevel 1>`. Period section just has 3 Date/Data fields.

| # | Fieldname | Label | Fieldtype | Section | Options/Default | Notes |
|---|---|---|---|---|---|---|
| 25 | `sb_e1_period` | Employment Period | Section Break | Employment Period | — | — |
| 26 | `employer_1_name` | Employer Name | Data | Employment Period | — | — |
| 27 | `employer_1_from` | From | Date | Employment Period | — | — |
| 28 | `employer_1_till` | Till | Date | Employment Period | — | — |
| 29 | `sb_e1_offer` | Offer Letter | Section Break | Offer Letter | — | — |
| 30 | `employer_1_offer_letter_doc` | Offer Letter | Attach | Offer Letter | — | — |
| 31 | `cb_e1_offer` | — | Column Break | Offer Letter | — | — |
| 32 | `employer_1_offer_letter_approval_status` | HR Status | Select | Offer Letter | `Pending\nAwaiting HR\nAccepted\nRejected`, **permlevel 1** | HR-only edit |
| 33 | `employer_1_offer_letter_remarks` | HR Remarks | Small Text | Offer Letter | **permlevel 1** | HR-only edit |
| 34 | `sb_e1_increment` | Increment Letter | Section Break | Increment Letter | — | — |
| 35 | `employer_1_increment_letter_doc` | Increment Letter | Attach | Increment Letter | — | — |
| 36 | `cb_e1_increment` | — | Column Break | Increment Letter | — | — |
| 37 | `employer_1_increment_letter_approval_status` | HR Status | Select | Increment Letter | `Pending\nAwaiting HR\nAccepted\nRejected`, **permlevel 1** | HR-only edit |
| 38 | `employer_1_increment_letter_remarks` | HR Remarks | Small Text | Increment Letter | **permlevel 1** | HR-only edit |
| 39 | `sb_e1_pay_lm` | Pay Slip — Last Month | Section Break | Pay Slip — Last Month | — | — |
| 40 | `employer_1_payslip_last_month_doc` | Pay Slip - Last Month | Attach | Pay Slip — Last Month | — | — |
| 41 | `cb_e1_pay_lm` | — | Column Break | Pay Slip — Last Month | — | — |
| 42 | `employer_1_payslip_last_month_approval_status` | HR Status | Select | Pay Slip — Last Month | `Pending\nAwaiting HR\nAccepted\nRejected`, **permlevel 1** | HR-only edit |
| 43 | `employer_1_payslip_last_month_remarks` | HR Remarks | Small Text | Pay Slip — Last Month | **permlevel 1** | HR-only edit |
| 44 | `sb_e1_pay_llm` | Pay Slip — Last-to-Last Month | Section Break | Pay Slip — Last-to-Last Month | — | — |
| 45 | `employer_1_payslip_last_to_last_month_doc` | Pay Slip - Last-to-Last Month | Attach | Pay Slip — Last-to-Last Month | — | — |
| 46 | `cb_e1_pay_llm` | — | Column Break | Pay Slip — Last-to-Last Month | — | — |
| 47 | `employer_1_payslip_last_to_last_month_approval_status` | HR Status | Select | Pay Slip — Last-to-Last Month | `Pending\nAwaiting HR\nAccepted\nRejected`, **permlevel 1** | HR-only edit |
| 48 | `employer_1_payslip_last_to_last_month_remarks` | HR Remarks | Small Text | Pay Slip — Last-to-Last Month | **permlevel 1** | HR-only edit |
| 49 | `sb_e1_pay_mbt` | Pay Slip — Month Before That | Section Break | Pay Slip — Month Before That | — | — |
| 50 | `employer_1_payslip_month_before_that_doc` | Pay Slip - Month Before That | Attach | Pay Slip — Month Before That | — | — |
| 51 | `cb_e1_pay_mbt` | — | Column Break | Pay Slip — Month Before That | — | — |
| 52 | `employer_1_payslip_month_before_that_approval_status` | HR Status | Select | Pay Slip — Month Before That | `Pending\nAwaiting HR\nAccepted\nRejected`, **permlevel 1** | HR-only edit |
| 53 | `employer_1_payslip_month_before_that_remarks` | HR Remarks | Small Text | Pay Slip — Month Before That | **permlevel 1** | HR-only edit |
| 54 | `sb_e1_relieving` | Relieving Letter / Resignation Acceptance | Section Break | Relieving | — | — |
| 55 | `employer_1_relieving_or_resignation_doc` | Relieving Letter / Resignation Acceptance | Attach | Relieving | — | — |
| 56 | `cb_e1_relieving` | — | Column Break | Relieving | — | — |
| 57 | `employer_1_relieving_or_resignation_approval_status` | HR Status | Select | Relieving | `Pending\nAwaiting HR\nAccepted\nRejected`, **permlevel 1** | HR-only edit |
| 58 | `employer_1_relieving_or_resignation_remarks` | HR Remarks | Small Text | Relieving | **permlevel 1** | HR-only edit |

#### Tab: Previous Employers (`tab_previous_employers`)

Repeating pattern per employer (2..5): `emp{N}_sb` (Section) → `employer_{N}_name` (Data) → `employer_{N}_from` (Date) → `employer_{N}_till` (Date) → `employer_{N}_doc` (Attach) → `employer_{N}_is_na` (Check default 0) → `cb_e{N}_status` (Column Break) → `employer_{N}_approval_status` (Select permlevel 1) → `employer_{N}_remarks` (Small Text permlevel 1).

| # range | Pattern | Section label |
|---|---|---|
| 59–67 | Previous Employer 2 (9 fields) | `Previous Employer 2` |
| 68–76 | Previous Employer 3 (9 fields) | `Previous Employer 3` |
| 77–85 | Previous Employer 4 (9 fields) | `Previous Employer 4` |
| 86–94 | Previous Employer 5 (9 fields) | `Previous Employer 5` |

#### Tab: Activity Log (`tab_activity`)

| # | Fieldname | Label | Fieldtype | Section | Options/Default | Notes |
|---|---|---|---|---|---|---|
| 95 | `tab_activity` | Activity Log | Tab Break | — | — | — |
| 96 | `activity_logs` | Activity Logs | Table | (default) | options `Action Centre Activity`, read_only | child table |

### Permissions (with permlevel-1 rows for HR-only fields)

| Role | permlevel | read | write | create | delete | print | report | share | email | export | if_owner |
|---|---|---|---|---|---|---|---|---|---|---|---|
| System Manager | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | — |
| System Manager | 1 | 1 | 1 | — | 1 | 1 | 1 | 1 | 1 | 1 | — |
| HR Manager | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | — |
| HR Manager | 1 | 1 | 1 | — | 1 | 1 | 1 | 1 | 1 | 1 | — |
| Employee | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Employee | 1 | 1 | — | — | — | 1 | 1 | 1 | 1 | 1 | — |

---

## Action Centre Activity

**Source:** atbhr-owned / myhr-owned · **Child table** of `Employee Action Centre.activity_logs`
**File (v15):** [`action_centre_activity.json`](../myhr/myhr/doctype/action_centre_activity/action_centre_activity.json) · `istable: 1`

| # | Fieldname | Label | Fieldtype | Options/Default | Notes |
|---|---|---|---|---|---|
| 1 | `posted_on` | Posted On | Datetime | default `Now`, read_only | in_list_view |
| 2 | `user` | User | Link | options `User`, read_only | in_list_view |
| 3 | `action` | Action | Select | `Document Uploaded\nDocument Reuploaded\nDocument Cleared\nHR Status Updated\nPolicy Acknowledged\nField Updated\nSubmitted for Review\nRemark Updated\nReopened by HR\nBulk Verdict Applied`, read_only | in_list_view |
| 4 | `details` | Details | Small Text | read_only | — |

Parent: `Employee Action Centre.activity_logs`. No JSON permissions (inherits parent).

---

# Stock doctypes extended by atbhr / myhr

## Employee (ERPNext)

**Source:** stock-erpnext, extended via `setup.py:ATBHR_CUSTOM_FIELDS` / `MYHR_CUSTOM_FIELDS`
**Stock JSON (v15):** `apps/erpnext/erpnext/setup/doctype/employee/employee.json`
**Stock JSON (v16):** `apps/erpnext/erpnext/setup/doctype/employee/employee.json` (different field_order — see drift note below)

### Tab inventory

#### v15 ERPNext stock tab order (top-level field_order):
1. `basic_details_tab` (label: Overview) → contains `basic_information` SB, `erpnext_user` SB, `company_details_section` SB
2. **`employment_details`** (TAB) ← v15 puts this here, right after `branch`
3. `contact_details` (TAB)
4. `attendance_and_leave_details` (TAB)
5. `salary_information` (TAB) → contains `bank_details_section` SB
6. `personal_details` (TAB) → contains `passport_details_section` SB
7. `profile_tab` (TAB) → contains `educational_qualification`, `previous_work_experience`, `history_in_company` SBs
8. `exit` (TAB) → contains `feedback_section` SB; also has `lft`/`rgt`/`old_parent`
9. `connections_tab` (TAB)

#### v16 ERPNext stock tab order:
1. `basic_details_tab` (Overview)
2. **`contact_details` (TAB)** ← v16 jumps straight to contact_details after `branch`
3. `attendance_and_leave_details`
4. `salary_information`
5. `personal_details`
6. `profile_tab`
7. **`employment_details`** ← v16 moved this tab to after `internal_work_history` (inside profile area)
8. `exit`
9. `connections_tab`

> **DRIFT FINDING — STOCK ERPNEXT, NOT atbhr/myhr CODE:** v15's stock Employee places the `employment_details` tab right after `branch`; v16 moves it deep inside the profile area. This affects rendering of the atbhr/myhr `custom_hr_controls_tab` Tab Break which inserts after `branch`.

### atbhr/myhr Custom Fields on Employee (insertion chain)

All declared in [`setup.py:ATBHR_CUSTOM_FIELDS`](../myhr/setup.py#L396) / [`setup.py:MYHR_CUSTOM_FIELDS`](../myhr/setup.py#L396).

| # | Fieldname | Label | Fieldtype | insert_after | Tab anchor (v15) | Tab anchor (v16) | Default | Notes |
|---|---|---|---|---|---|---|---|---|
| C1 | `custom_employee_id` | Employee ID | Data | `naming_series` | Overview / Basic Information | Overview / Basic Information | — | bold, in_list_view, **unique**; atbhr/myhr Custom Field |
| C2 | `custom_hr_controls_tab` | HR Controls | Tab Break | `branch` | **HR Controls** (new tab #2, before `employment_details`) | **HR Controls** (new tab #2, before `contact_details`) | — | atbhr/myhr Custom Field — anchors the new tab |
| C3 | `custom_emp_directory` | Add to Employee Directory | Check | `custom_hr_controls_tab` | HR Controls | HR Controls | `1` | atbhr/myhr Custom Field |
| C4 | `custom_add_to_action_centre` | Add to Employee Action Centre | Check | `custom_emp_directory` | HR Controls | HR Controls | `1` | atbhr/myhr Custom Field |
| C5 | `custom_auto_present` | Auto Present | Check | `custom_add_to_action_centre` | HR Controls | HR Controls | `0` | atbhr/myhr Custom Field |
| C6 | `custom_bypass_geolocation_check` | Bypass Geolocation Checkin Validation | Check | `custom_auto_present` | HR Controls | HR Controls | `0` | atbhr/myhr Custom Field |
| C7 | `custom_allow_view_reporting` | Allow to see Reporting Employees | Check | `custom_bypass_geolocation_check` | HR Controls | HR Controls | `0` | atbhr/myhr Custom Field |

### Stock Employee field-by-field layout — Overview tab (`basic_details_tab`)

> Section: `basic_information` (no label, top of form)

| # | Fieldname | Label | Fieldtype | Section | Notes |
|---|---|---|---|---|---|
| 1 | `naming_series` | Series | Select | basic_information | options `HR-EMP-`, set_only_once; stock |
| **C1** | **`custom_employee_id`** | **Employee ID** | **Data** | **basic_information** | **atbhr/myhr Custom Field — bold, unique, in_list_view** |
| 2 | `first_name` | First Name | Data | basic_information | reqd; stock |
| 3 | `middle_name` | Middle Name | Data | basic_information | stock |
| 4 | `last_name` | Last Name | Data | basic_information | stock |
| 5 | `employee_name` | Full Name | Data | basic_information | read_only; stock |
| 6 | `column_break_9` | — | Column Break | basic_information | stock |
| 7 | `gender` | Gender | Link | basic_information | stock |
| 8 | `date_of_birth` | Date of Birth | Date | basic_information | stock |
| 9 | `salutation` | Salutation | Link | basic_information | stock |
| 10 | `column_break1` | — | Column Break | basic_information | stock |
| 11 | `date_of_joining` | Date of Joining | Date | basic_information | stock |
| 12 | `image` | Image | Attach Image | basic_information | stock |
| 13 | `status` | Status | Select | basic_information | stock |

> Section: `erpnext_user` (collapsible_depends_on `__islocal` in v16)

| # | Fieldname | Label | Fieldtype | Notes |
|---|---|---|---|---|
| 14 | `user_id` | ERPNext User ID | Link `User` | depends_on differs v15/v16 (see stock drift below) |
| 15 (v15-only) | `create_user` | Create User (Button) | Button | **REMOVED in v16** — replaced by `create_user_automatically` (Check) |
| 16 | `create_user_permission` | Create User Permission | Check | stock |
| 16a (v16-only) | `column_break_xwnm` | — | Column Break | v16-added |
| 16b (v16-only) | `create_user_automatically` | Create User Automatically | Check | v16-added (default 0, set_only_once) |

> Section: `company_details_section`

| # | Fieldname | Label | Fieldtype | Notes |
|---|---|---|---|---|
| 17 | `company` | Company | Link `Company` | reqd; stock |
| 18 | `department` | Department | Link `Department` | stock; **in_list_view added in v16** |
| 19 | `employee_number` | Employee Number | Data | stock (note: `custom_employee_id` is the atbhr/myhr business ID) |
| 20 | `column_break_25` | — | Column Break | stock |
| 21 | `designation` | Designation | Link `Designation` | stock; **in_list_view added in v16** |
| 22 | `reports_to` | Reports to | Link `Employee` | stock |
| 23 | `column_break_18` | — | Column Break | stock |
| 24 | `branch` | Branch | Link `Branch` | stock — **anchor for `custom_hr_controls_tab`** |

### atbhr/myhr Custom Tab — HR Controls (anchored after `branch`)

| # | Fieldname | Label | Fieldtype | Default | Notes |
|---|---|---|---|---|---|
| **C2** | `custom_hr_controls_tab` | HR Controls | **Tab Break** | — | atbhr/myhr Custom Field |
| **C3** | `custom_emp_directory` | Add to Employee Directory | Check | `1` | atbhr/myhr Custom Field |
| **C4** | `custom_add_to_action_centre` | Add to Employee Action Centre | Check | `1` | atbhr/myhr Custom Field |
| **C5** | `custom_auto_present` | Auto Present | Check | `0` | atbhr/myhr Custom Field |
| **C6** | `custom_bypass_geolocation_check` | Bypass Geolocation Checkin Validation | Check | `0` | atbhr/myhr Custom Field |
| **C7** | `custom_allow_view_reporting` | Allow to see Reporting Employees | Check | `0` | atbhr/myhr Custom Field |

### Stock Employee — remaining tabs (summary, no atbhr/myhr customizations)

> The remaining tabs (`employment_details`, `contact_details`, `address_section` SB, `emergency_contact_details` SB, `attendance_and_leave_details`, `salary_information` w/ `bank_details_section` SB, `personal_details` w/ `passport_details_section` SB, `profile_tab` w/ `educational_qualification`/`previous_work_experience`/`history_in_company` SBs, `exit` w/ `feedback_section` SB, `connections_tab`) are pure stock ERPNext. atbhr/myhr does **not** add Custom Fields, Property Setters, or Override classes to any of these surfaces. Field counts: ~80 stock fields across these tabs in v15 (~80 in v16, modulo the v15→v16 drifts noted above: `create_user` removal, `create_user_automatically` addition, `column_break_xwnm` addition, `employment_details` tab repositioning, `Prefered → Preferred` label correction on `prefered_contact_email`/`prefered_email`, `Valid Upto → Valid Up To` on `valid_upto`, `Employee Exit → Exit` on `exit`).

#### Property Setters on Employee

| Field | Property | Value | Reason | Declared in |
|---|---|---|---|---|
| `leave_approver` | `label` | `Leave Approver` | Pin label to single-stage approval (no HR-stage suffix) | [`setup.py:370`](../myhr/setup.py#L370) `_ensure_employee_leave_approver_labels` |

#### Override class on Employee

None directly; behaviour is hooked via `doc_events` in [`hooks.py`](../myhr/hooks.py) (validate / after_insert / on_update / on_trash / after_rename) — not via `override_doctype_class`.

---

## Holiday (ERPNext, used by HRMS)

**Source:** stock-erpnext, extended via `setup.py:ATBHR_CUSTOM_FIELDS[7]` / `MYHR_CUSTOM_FIELDS[7]`
**Stock JSON (v15):** `apps/erpnext/erpnext/setup/doctype/holiday/holiday.json` (5 fields)
**Stock JSON (v16):** `apps/erpnext/erpnext/setup/doctype/holiday/holiday.json` (6 fields — v16 added `is_half_day`)
**Type:** child table (`istable: 1`) — used inside `Holiday List.holidays`. No tabs.

### Stock fields (v15)

| # | Fieldname | Label | Fieldtype | Options/Default | Notes |
|---|---|---|---|---|---|
| 1 | `holiday_date` | Date | Date | reqd | in_list_view; stock |
| 2 | `description` | Description | Text Editor | reqd | in_list_view; stock |
| 3 | `weekly_off` | Weekly Off | Check | default `0` | stock — **anchor for `custom_holiday_type`** |
| 4 | `column_break_2` | — | Column Break | — | stock |
| 5 | `section_break_4` | — | Section Break | — | stock |

### v16-only stock additions

| # | Fieldname | Label | Fieldtype | Notes |
|---|---|---|---|---|
| 6 | `is_half_day` | Is Half Day | Check | default `0`, in_list_view, in_preview; v16 stock add |

### atbhr/myhr Custom Field

| # | Fieldname | Label | Fieldtype | Options | insert_after | Notes |
|---|---|---|---|---|---|---|
| C8 | `custom_holiday_type` | Holiday Type | Select | `Optional\nFixed\nWeekly Off` | `weekly_off` | atbhr/myhr Custom Field; declared in [`setup.py:498`](../myhr/setup.py#L498); options-merge patch in `_ensure_holiday_type_options` |

---

## Leave Application (HRMS)

**Source:** stock-hrms, extended via Custom Fields + Property Setter + override class
**Stock JSON:** `apps/hrms/hrms/hr/doctype/leave_application/leave_application.json` (identical layout v15 vs v16; v16 only changes meta/permissions: dropped `set_user_permissions:1` on two perm rows + `amend:1` on one row)

### Stock field structure (relevant region)

| # | Fieldname | Label | Fieldtype | Section | Notes |
|---|---|---|---|---|---|
| … | `leave_approver` | Leave Approver | Link `User` | section_break_7 (label dropped) | stock |
| … | `leave_approver_name` | Leave Approver Name | Data | section_break_7 | read_only; stock — **anchor for `custom_approved_by`** |
| … | `column_break_18` | — | Column Break | section_break_7 | stock |
| … | `status` | Status | Select | section_break_7 | options Property-Set by atbhr/myhr (see below) |

### atbhr/myhr Custom Fields on Leave Application

| # | Fieldname | Label | Fieldtype | Options | insert_after | Read-only | Notes |
|---|---|---|---|---|---|---|---|
| C9 | `custom_approved_by` | Approved By | Link | `User` | `leave_approver_name` | yes | Server-stamped on Open→Approved by override class. atbhr/myhr Custom Field — declared in [`setup.py:513`](../myhr/setup.py#L513) |
| C10 | `custom_approved_on` | Approved On | Datetime | — | `custom_approved_by` | yes | Server-stamped on Open→Approved. atbhr/myhr Custom Field — declared in [`setup.py:523`](../myhr/setup.py#L523) |

### Property Setters on Leave Application

| Field | Property | Value | Type | Declared in |
|---|---|---|---|---|
| `status` | `options` | `Open\nApproved\nRejected\nCancelled` | Text | [`setup.py:315`](../myhr/setup.py#L315) `_ensure_leave_application_status_property_setter` |

### Override class

| Override class (v15) | Override class (v16) | Wired in | Functionality |
|---|---|---|---|
| `atbhr.overrides.leave_application.LeaveApplication` | `myhr.overrides.leave_application.LeaveApplication` | [`hooks.py:28`](../myhr/hooks.py#L28) | super().validate + `_guard_status_reversal` (forbid Approved→Open) + `_validate_optional_leave_rules` + `_stamp_approval_audit` (sets `custom_approved_by`/`custom_approved_on`) + `_notify_employee_on_verdict` |

---

## Attendance Request (HRMS)

**Source:** stock-hrms, extended via additive Custom DocPerm + Property Setter (no Custom Fields)
**Stock JSON:** identical v15 vs v16 (byte-identical, both files end without trailing newline in v15).

### Custom DocPerm (additive, NOT replacing stock perms)

Declared in [`setup.py:63`](../myhr/setup.py#L63) `ATBHR_ADDITIVE_PERMISSIONS` / `MYHR_ADDITIVE_PERMISSIONS`. Applied via `_ensure_additive_permissions`.

| Role | permlevel | read | write | create | delete | submit | cancel | amend | if_owner |
|---|---|---|---|---|---|---|---|---|---|
| Leave Approver | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |

### Property Setters

| Field | Property | Value | Type | Declared in |
|---|---|---|---|---|
| `employee` | `ignore_user_permissions` | `1` | Check | [`setup.py:343`](../myhr/setup.py#L343) `_ensure_attendance_request_employee_ignore_user_permissions` |

### Stock layout (key fields)

Stock single-tab form (no Tab Break in stock JSON). Section breaks: `(default)` → `reason_section`. Fields: `employee`, `employee_name`, `department`, `company`, `column_break_5`, `from_date`, `to_date`, `half_day`, `half_day_date`, `reason_section` SB, `reason`, `column_break_4`, `explanation`, `amended_from`, `shift`, `include_holidays`. atbhr/myhr does not change layout, only permissions and the `employee.ignore_user_permissions` Property Setter.

---

## Employee Checkin (HRMS)

**Source:** stock-hrms, extended via override class (no Custom Fields, no Property Setters)
**Stock JSON:** v16 added `overtime_type` (hidden Link to `Overtime Type`); otherwise identical layout. v15 stock has no `overtime_type` field.

### Stock layout (key fields, v15)

Single-tab form. Sections: `(default)`, `location_section`, `shift_timings_section`, `section_break_ksbo`. Fields incl.: `employee`, `employee_name`, `log_type`, `shift`, `column_break_4`, `time`, `device_id`, `skip_auto_attendance`, `attendance`, `shift_start`, `shift_end`, `shift_actual_start`, `shift_actual_end`, `location_section`, `geolocation`, `shift_timings_section`, `column_break_vyyt`, `latitude`, `longitude`, `column_break_yqpi`, `section_break_ksbo`, `fetch_geolocation`, `offshift`, …

### v16-only stock addition

| # | Fieldname | Label | Fieldtype | Options | Notes |
|---|---|---|---|---|---|
| (v16) | `overtime_type` | Overtime Type | Link | `Overtime Type` | hidden; v16 stock add — **not** referenced by atbhr/myhr |

### Override class

| Override class (v15) | Override class (v16) | Wired in | Functionality |
|---|---|---|---|
| `atbhr.overrides.employee_checkin.EmployeeCheckin` | `myhr.overrides.employee_checkin.EmployeeCheckin` | [`hooks.py:29`](../myhr/hooks.py#L29) | super().validate + `_guard_reserved_device_id` (only Admin/HR can use `device_id="atbHR Auto"`/`"myHR Auto"`) + `_guard_backdating` + `_guard_minute_dedup` + override of `validate_distance_from_shift_location` (honours `Employee.custom_bypass_geolocation_check`) |

---

## Holiday List / Leave Period / Leave Type (HRMS)

**Source:** stock-erpnext (Holiday List) / stock-hrms (Leave Period, Leave Type)
**Customization by atbhr/myhr:** **none** — referenced only.

| Doctype | Used by atbhr/myhr code path | Reference |
|---|---|---|
| Holiday List | `Employee.holiday_list` (stock) — used by [`leave_optional_holiday.py`](../myhr/leave_optional_holiday.py) to compute optional dates | stock-erpnext |
| Leave Period | `Leave Period.optional_holiday_list` consulted by `validate_optional_leave_dates` (LA override) | stock-hrms; v15-vs-v16 risk (see `HANDOFF_V16_TO_V15.md`) |
| Leave Type | `include_holiday`, `is_optional_leave` flags consulted by `validate_optional_leave_dates` | stock-hrms |

No Custom Fields, no Property Setters, no override classes from atbhr/myhr touch these doctypes.

---

# Cross-verification: atbhr v15 vs myhr v16

## Owned doctypes — JSON parity

For every owned doctype, the JSON files at `apps/atbhr/atbhr/atbhr/doctype/<dt>/<dt>.json` and `apps/myhr/myhr/myhr/doctype/<dt>/<dt>.json` were diffed. **Every diff reduces to a single line: the `module` field (`"atbHR"` ↔ `"myHR"`).** No structural / field / permission differences.

| Doctype | atbhr fields | myhr fields | Match? | Divergences |
|---|---|---|---|---|
| HR Policy | 17 | 17 | YES | only `module` |
| Policy Acknowledgement | 13 | 13 | YES | only `module` |
| Policy Audit Log | 12 | 12 | YES | only `module` |
| Policy Filter Department | 1 | 1 | YES | only `module` |
| Policy Filter Designation | 1 | 1 | YES | only `module` |
| Policy Filter Branch | 1 | 1 | YES | only `module` |
| Policy Filter Employment Type | 1 | 1 | YES | only `module` |
| Policy Filter Employee | 2 | 2 | YES | only `module` |
| Employee Directory | 6 | 6 | YES | only `module` |
| Employee Action Centre | 96 | 96 | YES | only `module` |
| Action Centre Activity | 4 | 4 | YES | only `module` |

## Stock-extended doctypes — Custom Field parity

For every entry in `ATBHR_CUSTOM_FIELDS` ([`setup.py:396`](../myhr/setup.py#L396)) the corresponding entry in `MYHR_CUSTOM_FIELDS` ([`setup.py:396`](../myhr/setup.py#L396)) was compared attribute-by-attribute.

| # | DocType | Fieldname | Match? | Divergence (modulo namespace) |
|---|---|---|---|---|
| 1 | Employee | `custom_employee_id` | YES | description: `"Custom business Employee ID used by atbHR."` ↔ `"Custom business Employee ID used by myHR."` (namespace-only) |
| 2 | Employee | `custom_hr_controls_tab` | YES | identical |
| 3 | Employee | `custom_emp_directory` | YES | identical |
| 4 | Employee | `custom_add_to_action_centre` | YES | identical |
| 5 | Employee | `custom_auto_present` | YES | description references `device_id='atbHR Auto'` ↔ `device_id='myHR Auto'` (namespace-only) |
| 6 | Employee | `custom_bypass_geolocation_check` | YES | identical |
| 7 | Employee | `custom_allow_view_reporting` | YES | identical |
| 8 | Holiday | `custom_holiday_type` | YES | identical |
| 9 | Leave Application | `custom_approved_by` | YES | identical |
| 10 | Leave Application | `custom_approved_on` | YES | identical |

Total: **10 Custom Fields**, 100% parity (modulo namespace strings in descriptions).

## Setup.py file diff summary

`diff atbhr/setup.py myhr/setup.py` returns ONLY namespace renames (`atbHR`↔`myHR`, `atbhr`↔`myhr`, `ATBHR_*`↔`MYHR_*`). No logic, ordering, attribute, or default differences.

---

# Property Setters declared by atbhr / myhr

| # | Doctype | Field | Property | Value | Field Type | atbhr | myhr | Declared in |
|---|---|---|---|---|---|---|---|---|
| 1 | Leave Application | `status` | `options` | `Open\nApproved\nRejected\nCancelled` | Text | YES | YES | [`setup.py:315`](../myhr/setup.py#L315) |
| 2 | Attendance Request | `employee` | `ignore_user_permissions` | `1` | Check | YES | YES | [`setup.py:343`](../myhr/setup.py#L343) |
| 3 | Employee | `leave_approver` | `label` | `Leave Approver` | Data | YES | YES | [`setup.py:370`](../myhr/setup.py#L370) |

All three Property Setters declared in both apps with byte-identical values. **Parity: 3/3.**

---

# Override class wiring

| Doctype | atbhr override class | myhr override class | Wired in | Functionality |
|---|---|---|---|---|
| Leave Application | `atbhr.overrides.leave_application.LeaveApplication` (extends `hrms.hr.doctype.leave_application.leave_application.LeaveApplication`) | `myhr.overrides.leave_application.LeaveApplication` (extends same HRMS class) | [`hooks.py:28`](../myhr/hooks.py#L28) | super().validate + status-reversal guard + optional-leave date rules + Open→Approved audit stamping + verdict notifications |
| Employee Checkin | `atbhr.overrides.employee_checkin.EmployeeCheckin` (extends `hrms.hr.doctype.employee_checkin.employee_checkin.EmployeeCheckin`) | `myhr.overrides.employee_checkin.EmployeeCheckin` (extends same HRMS class) | [`hooks.py:29`](../myhr/hooks.py#L29) | super().validate + reserved device_id guard (`atbHR Auto` / `myHR Auto`) + backdating guard + minute-dedup guard + geolocation distance bypass for `Employee.custom_bypass_geolocation_check` |

Both override classes are named `LeaveApplication` and `EmployeeCheckin` (no namespace suffix in the class name itself); only the **module path** differs by namespace.

---

# Aggregate verdict

**Total doctypes covered:** 19
- atbhr/myhr-owned: **11** (HR Policy, Policy Acknowledgement, Policy Audit Log, 5× Policy Filter children, Employee Directory, Employee Action Centre, Action Centre Activity)
- Stock-extended (Custom Fields and/or Property Setters and/or override class): **5** (Employee, Holiday, Leave Application, Attendance Request, Employee Checkin)
- Stock-referenced (no extension, depended-on at runtime): **3** (Holiday List, Leave Period, Leave Type)

**Total Custom Fields declared:** 10 (7 on Employee, 1 on Holiday, 2 on Leave Application).
**Total Property Setters declared:** 3 (Leave Application.status.options, Attendance Request.employee.ignore_user_permissions, Employee.leave_approver.label).
**Total override classes:** 2 (Leave Application, Employee Checkin) — Employee uses `doc_events` only.
**Total additive Custom DocPerm rows:** 1 (Leave Approver on Attendance Request).

**v15 atbhr ↔ v16 myhr layout parity:** **YES — full parity at the atbhr/myhr surface.** Every owned doctype JSON is byte-identical modulo `module` field. Every Custom Field dict in `setup.py` is byte-identical modulo namespace strings (`atbHR`↔`myHR`, `atbhr`↔`myhr`). Every Property Setter is byte-identical. Every override class signature and registered hook is byte-identical modulo namespace.

**Drift NOT in atbhr/myhr code, but in stock layers (informational, may affect rendering):**

1. **Stock ERPNext Employee `field_order`** — v15 places `employment_details` tab right after `branch`; v16 moves it deep inside the profile area (after `internal_work_history`). atbhr/myhr's `custom_hr_controls_tab` (Tab Break, `insert_after: "branch"`) lands in different visual neighbourhoods on v15 vs v16. **Severity:** cosmetic; the HR Controls tab still renders as a top-level tab in both, just with different "what tab is to the right" outcomes. (Source: `apps/erpnext/erpnext/setup/doctype/employee/employee.json` field_order lines 12-121 in v15 vs v16.)
2. **Stock ERPNext Employee `create_user` button removed in v16** and replaced with `create_user_automatically` Check + `column_break_xwnm`. atbhr/myhr does not touch either; this is pure stock churn. **Severity:** none for atbhr/myhr.
3. **Stock ERPNext Employee label corrections in v16** — `Prefered Contact Email`→`Preferred Contact Email`, `Prefered Email`→`Preferred Email`, `Valid Upto`→`Valid Up To`, `Employee Exit`→`Exit`. **Severity:** none.
4. **Stock ERPNext Employee `in_list_view` added in v16** for `department` and `designation`. **Severity:** none.
5. **Stock ERPNext Holiday `is_half_day` field added in v16.** atbhr/myhr's `custom_holiday_type` still anchors at `weekly_off` and lands cleanly in both. **Severity:** none.
6. **Stock HRMS Leave Application v16** dropped `set_user_permissions:1` on two perm rows and `amend:1` on one — pure perm churn, atbhr/myhr does not depend on these. **Severity:** none.
7. **Stock HRMS Employee Checkin v16** added a hidden `overtime_type` Link field. **Severity:** none for atbhr/myhr.

**Verdict:** atbhr v15 and myhr v16 are layout-equivalent at the atbhr/myhr customization surface. No atbhr-only or myhr-only fields. No mismatched `insert_after`. No mismatched defaults / read_only / unique flags. The only deltas are cosmetic v15-vs-v16 differences that originate in **stock ERPNext / HRMS upstream** and are out of scope for atbhr/myhr.
