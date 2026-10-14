# Elixiir × myHR — Integration Scope & Plan

> **Direction (locked 2026-04-29):** Earlier thinking (see [`ELIXIIR_VS_MYHR.md`](ELIXIIR_VS_MYHR.md) §14) was to fork myhr into a separate `myElixxirHR` app. **That is superseded.** New direction: merge Elixiir's HR-side customizations directly into `apps/myhr` so myhr becomes the unified app for the Elixiir deployment. HR controls and settings remain user-configurable inside myhr.
>
> **No code changes in this pass.** This document is the inventory + plan only. Implementation begins after Phase 0 decisions are signed off.

---

## 0. Inputs read for this plan

| Source | What it gives us |
|---|---|
| `~/Downloads/elixiir app/elixiir/` | Elixiir custom Frappe app (Apr 2026 source) — code, custom fields, hooks |
| `~/Downloads/Leave Policy – Elixiir.pdf` | Original leave policy (no encashment) |
| `~/Downloads/Leave Policy & Holiday Calendar Elixiir Foods.pdf` | **Signed copy** — adds "Encashment at the time of Exit" for EL |
| `~/Downloads/Elixiir_ERPNext_Leave_Setup_Guide-3.docx` | Step-by-step ERPNext v16 leave/payroll setup walkthrough — most authoritative |
| `apps/myhr/` (this bench) | Current myhr v16 |
| [`ELIXIIR_VS_MYHR.md`](ELIXIIR_VS_MYHR.md) §1-13 | Existing technical gap analysis — still accurate, reused below |

---

## 1. What this document covers

Two distinct workstreams, both inside myhr:

- **A. App-code merge** — port the Elixiir custom-app's HRMS surfaces (Employee customizations, server hooks, JS, property setters) into `apps/myhr`.
- **B. Leave + Holiday + Salary Structure data** — codify the manual setup guide into installer/fixture code so a fresh deployment produces the policy out of the box (instead of a human clicking through 90 pages).

**Out of scope** (stays in Elixiir's existing main custom app, not in myhr):
- Gate Entry, Return Request, Item / Material Request / Purchase Order / Purchase Receipt customizations.

---

## 2. Inventory — where we stand today

### 2.1 What myhr already provides (don't re-build)

| Surface | What's there |
|---|---|
| **Employee custom fields** | `custom_employee_id`, `custom_hr_controls_tab` (anchors HR Controls tab), `custom_emp_directory`, `custom_add_to_action_centre`, `custom_auto_present`, `custom_bypass_geolocation_check`, `custom_allow_view_reporting` |
| **Holiday custom field** | `custom_holiday_type` (Optional / Fixed / Weekly Off) — drives optional-leave guardrails |
| **Leave Application custom fields** | `custom_approved_by`, `custom_approved_on`, `custom_rejection_reason`, `custom_cancellation_reason` |
| **Attendance Request custom fields** | `custom_rejection_reason`, `custom_cancellation_reason`, `custom_submitted_for_review`, `custom_submitted_on`, `custom_submitted_by` |
| **HR Settings custom fields** | `custom_la_ar_approval_tab` + `custom_ar_approver_*` toggles (HR Manager / Leave Approver / self-submit), `custom_ec_approver_*` toggles |
| **myhr-owned doctypes** | HR Policy + 5 child filter doctypes; Policy Acknowledgement; Policy Audit Log; Employee Action Centre + Action Centre Activity; Employee Directory |
| **Server hooks** | Employee.validate / after_insert / on_update / on_trash / after_rename → AC + Directory + auto-present; Attendance Request validate + before_submit + on_submit + after_insert; Leave Application validate + after_insert; Expense Claim validate + after_insert; HR Policy lifecycle; Policy Acknowledgement after_insert; Holiday/Holiday List validate; HR Settings validate (lockout guard) |
| **Permission model** | `permission_query_conditions` + `has_permission` on Employee → HR roles see all, others see self (+ direct reports if `custom_allow_view_reporting`) |
| **Whitelisted method overrides** | `hrms.api.get_leave_applications` / `get_attendance_requests` / `get_expense_claims` re-routed through myhr |
| **Scheduler** | 09:00 + 18:00 Mon-Fri auto-IN/OUT for `custom_auto_present` employees; hourly stale-PA reminder |
| **Frontend (PWA)** | Vue overlay sync via `frontend_changes/` + `frontend_sync.apply_custom_ui` (NOT `frontend_overlay/` — that dir is dead) |

> **Source of truth:** [`apps/myhr/CLAUDE.md`](../CLAUDE.md), [`docs/SETUP_AND_PATCHES.md`](SETUP_AND_PATCHES.md), [`myhr/setup.py`](../myhr/setup.py).

### 2.2 What the Elixiir custom app adds (HR slice only)

Detailed gap analysis already lives in [`ELIXIIR_VS_MYHR.md`](ELIXIIR_VS_MYHR.md) §1-9. Headline summary:

| Surface | Net additions |
|---|---|
| **Doctype** | `Elixiir Child` (child table — `child_name`, `dob`) |
| **Employee custom fields (~27)** | **Overview**: salary_structure, employee_location, notice_period_days, holiday_list, age (auto), pan_attachment, aadhar_number, aadhar_attachment, total_experience_years. **Bank tab** (new tab `custom_bank_tab`): bank_name, account_number, ifsc_code, account_type, payment_mode, account_holder_name, name_as_per_bank. **Personal Details**: father_name, mother_name, custom_children (Elixiir Child table), uan, highest_qualification, highest_qualification_institute, highest_qualification_attachment. **Profile**: appointment_letter, resignation_email, relieving_letter, bank_statement_6m |
| **Property Setters** | Hide native Joining tab (`employment_details`); hide native bank fields individually (`salary_mode`, `bank_details_section`, `bank_name`, `bank_ac_no`, `ifsc_code`, `micr_code`, `iban`, `holiday_list`); Salary Slip `default_print_format = "Elixiir Salary Slip"` |
| **HR-only permlevel locking** | 13 fields bumped to `permlevel=1`: ctc, salutation, designation, department, reports_to, employment_type, grade, company_email, custom_notice_period_days, custom_salary_structure, custom_total_experience_years, custom_employee_location, custom_holiday_list. Custom DocPerm rows: HR Manager R+W; Employee + Employee Self Service R-only |
| **Server `Employee.validate` chain** | validate_salary_structure_company → sync_notice_period → sync_bank_details → sync_holiday_list → compute_age |
| **Server `Employee.after_insert`** | Auto-create submitted **Salary Structure Assignment** (base = (CTC − 21,600) / 1.02405) + submitted **Holiday List Assignment** (clamps `from_date` into HL's own window) |
| **Server `Employee.on_update`** | Cancel + recreate SSA on structure or CTC change; cancel + recreate HLA on holiday-list change |
| **Server `Holiday List Assignment.on_submit`** | Reverse-sync `holiday_list` onto Employee.custom_holiday_list + native holiday_list via `frappe.db.set_value` (avoids on_update loop) |
| **Client JS (`Employee`)** | PDF-only restriction + 5 MB cap on 7 Attach fields (monkey-patches `set_upload_options`, disables webcam / web link / Google Drive); live DOB → custom_age preview; `custom_salary_structure` filtered by `company + is_active=Yes + docstatus=1` |

### 2.3 What the Elixiir Leave Policy + Setup Guide require (currently manual)

The setup guide is a 90-page click-through. The artefacts it produces:

| Artefact | Spec |
|---|---|
| **Holiday List "Elixiir Holiday List 2026"** | 01-Jan-2026 → 31-Dec-2026, country=India, Sat+Sun weekly off, 12 public holidays (full list in §2.4 below) |
| **Leave Period "Elixiir 2026"** | Same date window, `is_active=1`, `optional_holidays_list = Elixiir Holiday List 2026` |
| **Salary Component "Leave Encashment"** | Type=Earning, taxable, NOT depends on payment days, NOT statistical. Account mapping per company → `Salary - <abbr>` (or dedicated ledger if accountant prefers) |
| **Leave Type "Privilege Leave"** | Max=14, Applicable After=0, Max Continuous=0, **Is Earned Leave=✓**, Allocate on Day=Last Day, Earned Frequency=Monthly, Rounding=0.5, Is Carry Forward=✓, Max CF=30, Allow Encashment=✓, Earning Component=Leave Encashment, Max Encashable=0 (no cap), Non-Encashable=0, Include Holidays=✗ |
| **Leave Type "Casual Leave"** | Max=7, Max Continuous Days=2, Is Earned=✗, Is CF=✗, Allow Encashment=✗ |
| **Leave Type "Sick Leave"** | Max=7, Max Continuous=0, Is Earned=✗, Is CF=✗, Allow Encashment=✗ |
| **Leave Type "Maternity Leave"** | Max=182, **Applicable After (Working Days)=80**, Max Continuous=182, Allow Over Allocation=✓, **Include Holidays=✓**, Is Earned=✗, Is CF=✗ |
| **Leave Without Pay** | Built-in — verify only, do not recreate |
| **Leave Policy "Elixiir Probation Leave Policy"** | CL(7) + SL(7) + ML(182) — **no PL** |
| **Leave Policy "Elixiir Confirmed Leave Policy"** | PL(14) + CL(7) + SL(7) + ML(182) |
| **Per-employee Leave Policy Assignment** | Granted via Leave Period bulk grant, filtered by Employment Type (Probation vs Permanent). Pro-rates non-earned types by days-in-period |
| **Salary Structure "Elixiir Standard Salary Structure 2026"** | Earnings: BASIC=`base*0.40`, HRA=`BASIC*0.50`, LTA=`BASIC*0.0833`, SPECIAL=`base - BASIC - HRA - LTA - EMPLOYER_PF - GRATUITY - INSURANCE`, EMPLOYER PF=`min(BASIC,15000)*0.12`, GRATUITY=`BASIC*0.0481`, INSURANCE=fixed, Leave Encashment=0. Deductions: Employee PF=`min(BASIC,15000)*0.12`, Professional Tax=200, Income Tax=auto |
| **Per-employee Salary Structure Assignment** | Already auto-created by Elixiir's Employee server hook (§2.2) once `custom_salary_structure` + DOJ are set |

### 2.4 Holiday calendar 2026 (per Annexure A)

| # | Date | Day | Name |
|---|---|---|---|
| 1 | 01-01-2026 | Thu | New Year |
| 2 | 26-01-2026 | Mon | Republic Day |
| 3 | 04-03-2026 | Wed | Holi |
| 4 | 03-04-2026 | Fri | Good Friday |
| 5 | 28-05-2026 | Thu | Bakra Id / Eid-Ul-Adha (tentative) |
| 6 | 15-08-2026 | Sat | Independence Day |
| 7 | 21-08-2026 | Fri | Rakshabandhan |
| 8 | 02-10-2026 | Fri | Gandhi Jayanti |
| 9 | 20-10-2026 | Tue | Dussehra |
| 10 | 09-11-2026 | Mon | Diwali |
| 11 | 24-11-2026 | Tue | Gurupurab |
| 12 | 25-12-2026 | Fri | Christmas |

### 2.5 Open / deferred policy questions (from setup guide §18)

These are **not technical** — each needs a written decision from Elixiir HR/Management before the system goes live. Recording here so they don't get lost.

| # | Question | Default we'd ship |
|---|---|---|
| 18.1 | Does `Max Leaves Allowed = 14` cap annual **consumption** or only **allocation**? (Carry-forward of 30 means a holder can stack 44.) | Cap allocation only (ERPNext default) |
| 18.2 | At separation, encash the **full balance** or cap at 30? | Full balance (Maximum Encashable Leaves = 0) |
| 18.3 | Probation pro-rata for CL/SL — days-based or months-based? | Days-based (ERPNext default) |
| 18.4 | Maternity 80-day rule — uniform across miscarriage/tubectomy/illness add-ons? Are add-ons additive to 182 or shared bucket? | Additive via Allow Over Allocation, 80-day gate only on primary ML |
| 18.5 | CL "max consecutive 2" — per instance or per year? | Per instance (universally standard) |
| 18.6 | SL >2 days without medical cert — reject, convert to CL/LWP, or grant with grace? | Grant; HR converts manually if needed |
| 18.7 | Encashment rate basis — Basic only, Basic+DA, Basic+DA+HRA, Gross? | Basic + DA (ERPNext default; aligns with §10(10AA)) |
| 18.8 | Bakra Id confirmation owner — who edits the date when it's announced? | HR, ~30 days before |
| 18.9 | Probation duration — uniform 3 months, or by grade? | Uniform 3 months |
| 18.10 | Optional / floater holidays — offered? How many? | None today; can add later via Leave Period.optional_holidays_list |
| 18.11 | LWP impact on PF/gratuity/incentives? | Pro-rata Basic (ERPNext default) |
| 18.12 | EL Allocate on Day — First Day or Last Day? | Last Day |
| 18.13 | EL rounding — 0.5 / 0.25 / exact? | 0.5 |
| 18.16 | Maternity Leave shows on **male** employees' balance (cosmetic). Fix now (4 gender-based policies) or defer to 2027 rollover? | Defer (current Elixiir choice) |
| 18.17 | Maternity Benefit Act 1961 compliance — medical bonus, commissioning mother, nursing breaks, Form register? | Out of scope this round; legal review pending |

---

## 3. Gap = what we add to myhr

### 3.1 Employee form (code-level)

- **Net-new doctype**: `Elixiir Child` child table (Data + Date).
- **Net-new custom fields**: ~27 fields per §2.2 above. Append to `MYHR_CUSTOM_FIELDS`.
- **Net-new Property Setters**: hide Joining tab + hide native bank fields. (Defer Salary Slip default print until print format exists — see Issue 8 below.)
- **Net-new permlevel locking**: 13 fields → `permlevel=1` + 3 Custom DocPerm rows (HR Manager R+W; Employee + Employee Self Service R-only).
- **Net-new doctype_js**: Employee — PDF restriction + DOB→age preview + salary_structure company filter. (myhr currently ships no `doctype_js` for Employee.)

### 3.2 Server-side hooks (code-level)

- **Net-new** `myhr/employee_master_data.py` (new module): `validate_salary_structure_company`, `sync_notice_period`, `sync_bank_details`, `sync_holiday_list`, `compute_age`, `create_salary_structure_assignment`, `cancel_existing_ssa`, `create_holiday_list_assignment`, `cancel_existing_hla`. Plus the CTC→base helper.
- **Layer into existing `Employee.validate` chain** *before* `myhr.employee_hooks.validate_employee` (master-data sync first; AC/Directory upsert second).
- **Layer into `Employee.after_insert`** before `employee_hooks.after_employee_insert` and `policy_hooks.reconcile_after_employee_insert`.
- **Layer into `Employee.on_update`** before existing handlers.
- **Net-new** `Holiday List Assignment.on_submit` reverse-sync handler (no existing myhr override on this doctype — clean addition).

### 3.3 Client JS (code-level)

- **Net-new** `myhr/public/js/employee.js` registered via `doctype_js` in `hooks.py`. Mirrors elixiir's three behaviors.

### 3.4 Leave + Holiday + Salary Structure (data / installer)

Today the setup guide is a manual click-through. To make myhr self-installing for a new Elixiir-style deployment, codify each artefact as an idempotent installer step (skip-if-exists pattern, same as `MYHR_CUSTOM_FIELDS`):

1. `ensure_holiday_list(year)` — creates `Elixiir Holiday List <year>` with weekly_off Sat+Sun + holiday rows. Driven from a static dict; HR can amend rows post-install via Desk.
2. `ensure_leave_period(year)` — creates `Elixiir <year>` linked to the holiday list above as `optional_holidays_list`.
3. `ensure_leave_encashment_component(company)` — creates Salary Component "Leave Encashment" + maps Account = `Salary - <abbr>` (configurable; warn if account doesn't exist).
4. `ensure_leave_types()` — creates the 4 types per the §2.3 matrix. Verifies built-in `Leave Without Pay` exists.
5. `ensure_leave_policies(company)` — creates `Elixiir Probation Leave Policy` and `Elixiir Confirmed Leave Policy`.
6. `ensure_salary_structure(company, year)` — creates `Elixiir Standard Salary Structure <year>` with the 7 earning components + 3 deduction components (formulas from setup guide §13.3).
7. `grant_leaves_for_period(period_name, policy_name, employment_type_filter)` — bulk-grants Leave Policy Assignments for a filtered employee set (HR-triggered; safer than auto-running on every install).
8. **Year-end rollover helper** — single entry point that creates next year's HL + LP, clones the SS, optionally re-runs Grant Leaves. Mirrors setup guide §14.

Per-employee SSA + HLA continue to be created automatically by the Employee hook from §3.2 once `custom_salary_structure` and `custom_holiday_list` are set.

### 3.5 Settings / configurability

Elixiir's source code hard-codes several numbers (CTC_PF_DEDUCTION = 21600, gratuity factor 1.02405, salary % splits, leave-day counts, max-CF=30). The user explicitly asked that "all the settings hr controls etc are kept in this way" — i.e. HR-editable. Two options:

| Option | Approach | Trade-off |
|---|---|---|
| **A — Hardcoded constants in myhr** | Mirror elixiir verbatim; magic numbers in code. | Simplest; code change required to tune. |
| **B — `myHR Payroll Settings` Single doctype** | All numeric knobs (PF deduction, gratuity factor, salary % splits, leave day caps, CF caps, encashment caps) live in a single doctype. Code reads from there. | More work upfront; HR can tune without a deploy. **Recommended given the user's stated intent.** |

Decision lives in Phase 0 below.

---

## 4. Conflict / risk register (must address during Phase 1)

| # | Issue | Action |
|---|---|---|
| 1 | `custom_hr_controls_tab` (myhr) and `custom_total_experience_years` (elixiir) both anchor on `insert_after: grade`. | Re-anchor `custom_total_experience_years` after `branch` (or any other Overview-tab field), or move the HR Controls tab anchor. Pick one before Phase 1 step 2. |
| 2 | `Employee.validate` chain — myhr already wires `validate_employee`. Elixiir's chain calls 5 functions. | Define explicit order: master-data sync → AC/Directory upsert → policy gate. Single hook entry that calls both modules in sequence. |
| 3 | `Employee.after_insert` order — elixiir creates SSA + HLA; myhr creates Action Centre + reconciles policy. | Run elixiir first so AC reconciliation sees the assignments. |
| 4 | PDF/5MB restriction — elixiir scopes it to 7 fields. myhr's Action Centre uploads accept any type/size today. | Phase 0 decision: apply same restriction to AC uploads (consistency) or scope only to elixiir's 7 fields. |
| 5 | permlevel=1 locking on Employee — must verify it doesn't collide with myhr's `permission_query_conditions` on Employee. | Smoke-test together: row-level filter + field-level lock. |
| 6 | Property Setter "hide bank fields" + AC bank-doc card. | AC's bank-doc card writes via PA workflow, not directly to native fields. Verify the elixiir custom proxies still receive the data and `sync_bank_details` mirrors back to natives. |
| 7 | `Holiday List Assignment.on_submit` reverse-sync vs myhr's Holiday/Holiday List validate hooks. | Different doctypes, no overlap, but verify together once. |
| 8 | Salary Slip default print format = `Elixiir Salary Slip`. myhr does not ship that print format. | Either bundle the print format inside myhr or skip the property setter until print format exists (do not point at a missing format — Frappe will silently fall back). |
| 9 | Maternity-Leave-on-male-employees cosmetic issue (setup guide §18.16). | Phase 0 decision: ship 4 gender-based Leave Policies on Day 1, or accept the cosmetic visual and defer. |
| 10 | Leave Encashment Salary Component requires per-company Account mapping. | Installer must either prompt for the account or default to `Salary - <abbr>` and warn if missing. |
| 11 | If Settings Option B chosen: every elixiir hard-coded constant must read from the doctype, including in the Employee hook. | Implementation note for Phase 1, not a Phase 0 blocker. |
| 12 | Patches must repair already-installed sites — backfill `custom_age`, mirror notice_period to native, etc. | Use existing `myhr/patches/` pattern (e.g. clone `v1_8_repair_custom_field_flags.py`). |

---

## 5. Phased plan (no code yet)

### Phase 0 — Decisions to lock before coding

Sign-offs required:

- [ ] Direction: merge into myhr (vs fork to `myElixxirHR`) — **captured here, awaiting user confirm**
- [ ] Settings model: hardcoded constants (Option A) vs `myHR Payroll Settings` Single doctype (Option B)
- [ ] Gender-based Leave Policies on Day 1 (yes / no — defer to 2027 rollover)
- [ ] Apply PDF/5MB restriction to existing Action Centre uploads? (yes / no — keep AC permissive)
- [ ] Source the `Elixiir Salary Slip` print format — bundle inside myhr or build separately?
- [ ] Resolve setup guide §18 open questions — which interpretations are authoritative for Elixiir? (At minimum: §18.1, §18.2, §18.7. The rest can ship at the listed defaults.)

### Phase 1 — Employee form code merge

1. Add `Elixiir Child` child doctype.
2. Append elixiir Employee custom fields to `MYHR_CUSTOM_FIELDS` (resolving Issue 1).
3. Add Property Setters (hide Joining + bank fields). Defer Salary Slip print (Issue 8) until format exists.
4. Add HR-only permlevel patch + Custom DocPerm rows.
5. Add `myhr/public/js/employee.js` + register via `doctype_js` in hooks.
6. Add new module `myhr/employee_master_data.py` — sync chain + auto SSA + auto HLA + CTC→base helper.
7. Wire master-data callables into the existing `Employee` doc_events lists (validate / after_insert / on_update) — order per Issues 2 and 3.
8. Add `Holiday List Assignment.on_submit` reverse-sync.
9. Idempotent migration patch — backfill `custom_age`, mirror existing bank fields to natives, mirror notice_period, etc.

### Phase 2 — Leave + Holiday + Salary Structure installer

10. New module `myhr/setup_elixiir_leave.py` — implements the 7 `ensure_*` steps from §3.4 + the rollover helper.
11. Make every step idempotent (skip-if-exists). Adopt the same pattern as `_ensure_custom_fields`.
12. Optional: `myhr.api.grant_leaves_for_period` whitelisted endpoint (HR-only) so HR can re-trigger the bulk grant from Desk.

### Phase 3 — Settings doctype (only if Option B chosen in Phase 0)

13. New Single doctype `myHR Payroll Settings` with PF deduction, gratuity factor, EL/CL/SL/ML day counts, max-CF, max-encashable-leaves, % splits for SS earnings.
14. Refactor Phase 1 + 2 callables to read from the doctype instead of constants.

### Phase 4 — Verification + polish

15. Smoke matrix:
    - Insert employee with structure + DOJ → submitted SSA created
    - Insert employee with holiday list → submitted HLA created with from_date clamped
    - Change CTC → previous SSA cancelled, new SSA created
    - Change holiday list → previous HLA cancelled, new HLA created
    - HLA submitted via Desk → Employee.custom_holiday_list reverse-synced
    - Employee role tries to edit `ctc` → blocked (permlevel)
    - Employee uploads `.png` to PAN attachment → rejected
    - DOB change → custom_age preview updates
    - Apply 3-day Casual Leave → blocked ("Maximum Continuous Days")
    - Apply 5-day EL spanning a weekend → 3 working days deducted
    - Apply Maternity Leave with <80 days service → blocked ("Applicable After")
    - Run Grant Leaves on test Leave Period → allocations created, pro-rated for mid-year joiners
16. Update docs: refresh [`ELIXIIR_VS_MYHR.md`](ELIXIIR_VS_MYHR.md) (close out the gap items), and add references from [`LEAVE_AND_ATTENDANCE.md`](LEAVE_AND_ATTENDANCE.md) + [`HOLIDAY.md`](HOLIDAY.md) to the new installer module.

### Phase 5 — Rollout & v15 port

17. Deploy on v16 myhr first (per existing dual-bench rule from memory).
18. User hand-ports to v15 atbhr after v16 is green.

---

## 6. Out of scope for this round

- Gate Entry / Return Request / Item / MR / PO / GRN customizations — stay in the Elixiir main custom app (not myhr's responsibility).
- Maternity Benefit Act 1961 deeper compliance items — medical bonus salary component, commissioning-mother leave type, nursing breaks, Form L-K-M-N register. Track separately per setup guide §18.17, pending legal review.
- Tax slab configuration (Old vs New regime), per-employee declarations, full payroll batch run procedures — payroll-team responsibility, not myhr.
- "Additional requirements" the user mentioned for later — captured but deferred until Phases 1-2 land.

---

## 7. References

- Existing technical gap doc: [`ELIXIIR_VS_MYHR.md`](ELIXIIR_VS_MYHR.md) (sections 1-13 still authoritative; section 14 superseded by this document)
- Source policy PDFs: `~/Downloads/Leave Policy – Elixiir.pdf`, `~/Downloads/Leave Policy & Holiday Calendar Elixiir Foods.pdf`
- Source setup guide: `~/Downloads/Elixiir_ERPNext_Leave_Setup_Guide-3.docx`
- Source app: `~/Downloads/elixiir app/elixiir/`
- myhr architecture: [`apps/myhr/CLAUDE.md`](../CLAUDE.md), [`docs/SETUP_AND_PATCHES.md`](SETUP_AND_PATCHES.md)
