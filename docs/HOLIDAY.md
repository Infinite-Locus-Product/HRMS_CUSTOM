# Holiday + Optional Holiday Flow

Spec for the Holiday taxonomy myHR overlays on top of stock Frappe `Holiday` rows, and the Optional-Leave validation that rides on it. Audited + Phase-2 hardened on 2026-04-26.

---

## 1. The data model

| Doctype | Source | myHR-added field |
|---|---|---|
| **Holiday List** | Frappe (stock) | — |
| **Holiday** (child of Holiday List) | Frappe (stock) — `holiday_date, description, weekly_off` | `custom_holiday_type: Select(Optional / Fixed / Weekly Off)` (Custom Field declared in `setup.py:MYHR_CUSTOM_FIELDS`) |
| **Leave Type** | Stock HRMS — `is_optional_leave: Check` | — |
| **Employee** | Stock HRMS — `holiday_list: Link Holiday List` | — |

The taxonomy:
- **Optional** — employee may apply optional leave on this date (typically a regional / cultural holiday).
- **Fixed** — company-wide closed day; nobody works, nobody applies leave (it's already off).
- **Weekly Off** — recurring weekly closure (Sundays / Saturdays). `weekly_off=1` MUST imply this type.

The single non-stock rule: the optional-leave gate (`validate_optional_leave_dates`) only accepts dates whose row carries `custom_holiday_type='Optional'` *and* lives on the employee's `Employee.holiday_list`. Anything else throws.

---

## 2. Where the logic lives

| Concern | File |
|---|---|
| Holiday `custom_holiday_type` field declaration | [setup.py MYHR_CUSTOM_FIELDS](../myhr/setup.py) |
| Sync rule (weekly_off ↔ type) | [leave_optional_holiday.py `validate_holiday_list` / `validate_holiday`](../myhr/leave_optional_holiday.py) |
| Hook wiring | [hooks.py doc_events](../myhr/hooks.py) |
| Optional-leave date validator | [leave_optional_holiday.py `validate_optional_leave_dates`](../myhr/leave_optional_holiday.py) |
| Public PWA endpoint | [api.py `validate_optional_leave_for_application`](../myhr/api.py) |
| Optional Leave Type listing | [api.py `get_optional_leave_types`](../myhr/api.py) |
| Backfill patches | [v1_2_holiday_type](../myhr/patches/) (initial) + [v1_7_fix_holiday_type_for_weekly_off](../myhr/patches/v1_7_fix_holiday_type_for_weekly_off.py) (Phase 2) |

---

## 3. Sync rule (the contract)

`validate_holiday_list` runs on every `Holiday List` save and applies the rule per child row:

| Input row state | Output row state | Reason |
|---|---|---|
| `weekly_off=1`, type ≠ 'Weekly Off' | type forced to **'Weekly Off'** | Closes HOL-1 — fixes the common HR-builder mistake of leaving Sunday auto-fills tagged Optional. Hard override; HR can't keep a weekly-off entry as Optional. |
| `weekly_off=0`, type='Weekly Off' | **throws** | Contradictory — HR must either tick Weekly Off or pick Optional/Fixed. |
| `weekly_off=0`, type blank | type set to **'Fixed'** | Conservative default. Note: in practice Frappe pre-fills the field with the first Select option ("Optional"), so HR usually sees Optional unless they explicitly clear the field. |
| Anything else | unchanged | HR's choice respected. |

The hook is wired on **Holiday List** (not Holiday) because child-doctype `validate` doc_events don't reliably fire on table-row inserts in Frappe — the parent's validate is the dependable surface. A Holiday-level hook is also wired for the rare standalone-save path.

---

## 4. Optional-Leave validation flow

Source: [leave_optional_holiday.validate_optional_leave_dates](../myhr/leave_optional_holiday.py).

```
1. Resolve Employee.holiday_list  → throw if unset
2. Resolve [from_date, to_date]   → throw if from > to (LA-6 sanity check)
3. Single batched fetch: every Holiday in [from, to] on that list
4. For each day in range:
     - missing → throw NotAnOptionalHoliday (stock HRMS error class)
     - blank type → throw "set to Optional / Fixed / Weekly Off"
     - 'Fixed' → throw "fixed company holiday"
     - 'Weekly Off' → throw "weekly off; optional leave cannot be applied"
     - 'Optional' → accepted
     - anything else → throw "unsupported Holiday Type"
```

Optimization (Phase 2 / LA-6): the loop used to do one `frappe.get_all` per day. For a 30-day leave this was 30 round-trips. Now: 1 batched `BETWEEN` query + in-memory dict lookup per day.

Wired into `Leave Application.validate` via [LeaveApplication._validate_optional_leave_rules](../myhr/overrides/leave_application.py) (only fires when `Leave Type.is_optional_leave=1`). Also exposed as a non-throwing PWA endpoint (`myhr.api.validate_optional_leave_for_application`) so the form can show inline errors before submit.

---

## 5. Findings + Phase 2 hardening

| # | Issue | Status |
|---|---|---|
| **HOL-1** | All 52 Sundays in `Holidays 2026` were `weekly_off=1` *but* `custom_holiday_type='Optional'`. Optional leave on Sundays would have been accepted by the validator — defeating the gate. | **RESOLVED 2026-04-26.** Backfill patch [v1_7_fix_holiday_type_for_weekly_off.py](../myhr/patches/v1_7_fix_holiday_type_for_weekly_off.py) re-tagged 52 rows. Live verified. |
| **HOL-2** | No save-time hook to keep `custom_holiday_type` in sync with `weekly_off`. New sites would drift back into HOL-1. | **RESOLVED 2026-04-26.** New `validate_holiday_list` hook (parent-side) applies the sync rule on every save. `weekly_off=1` rows are forced to `Weekly Off` type unconditionally. Verified live: a deliberately mislabeled `Optional` Sunday is auto-corrected on next save. |
| **HOL-3** | `custom_holiday_type` could be left blank entirely (the `validate_optional_leave_dates` throws downstream, but the Holiday row itself accepted blank). | **RESOLVED 2026-04-26.** Same hook defaults blank `weekly_off=0` rows to `Fixed`. Note: in practice Frappe's Select field pre-fills "Optional" (the first option), so blank rarely materialises — HR usually sees Optional unless they explicitly clear. The hook covers the genuine-blank case for completeness. |
| **HOL-4** | Demo data state: 52 rows mislabeled. | **RESOLVED 2026-04-26 via the v1_7 backfill patch.** |
| **HOL-5** | `weekly_off=0` row tagged 'Weekly Off' is a contradiction; previously silently accepted. | **RESOLVED 2026-04-26.** Hook throws on contradiction with a clear message. Verified live. |
| **HOL-6** | `validate_optional_leave_dates` did one `frappe.get_all` per day in the [from, to] loop. | **RESOLVED 2026-04-26 (LA-6).** Single batched `BETWEEN` query + dict lookup. |
| **HOL-7** (open) | Stock HRMS doesn't require `Employee.holiday_list`. Without it, optional leave can't be applied (validator throws "Please set Holiday List"). On the demo site, 0/10 employees have a holiday list set. | **Open — data state.** Setting holiday_list is HR's responsibility on the Employee form; not a code bug. Could be addressed by: (a) HR Settings default Holiday List, or (b) auto-assign on Employee insert if a "Default Holiday List" is configured on Company. Future work. |

---

## 6. Live verification (2026-04-26, 6/7 effective)

| Test | Result |
|---|---|
| T-1 baseline: 52 Sundays = Weekly Off after backfill | ✅ |
| T-2 Mislabel Sunday → save → auto-corrected back to Weekly Off | ✅ |
| T-3 weekly_off=0 + type='Weekly Off' contradiction → throws | ✅ |
| T-4 New row, weekly_off=1, no type → defaults to Weekly Off | ✅ |
| T-5 New row, weekly_off=0, no type → Frappe pre-fills "Optional" (NOT "Fixed") | Documented as Frappe-default behaviour. The Fixed default branch only triggers on explicit-blank inserts which Frappe's Select field doesn't produce. |
| T-6 Optional leave on a Sunday → throws "weekly off; optional leave cannot be applied" | ✅ |
| T-7 Optional leave on a real Optional date → accepted | ✅ |

---

## 7. PWA + Desk surfaces

- **HR Desk**: Holiday List form. HR adds rows, ticks `weekly_off` for Sundays, picks `custom_holiday_type` for non-weekly entries. Save → hook normalises.
- **PWA Apply Leave form**: when `Leave Type.is_optional_leave=1`, the form calls `myhr.api.validate_optional_leave_for_application` on date-pick to show inline errors before submit. Form also hides the half-day toggle for optional leaves (LA-only-full-day rule).
- **PWA → server**: same validator runs server-side via `LeaveApplication.validate` so direct API submits can't bypass.

---

## 8. Recommendations (deferred)

| # | Item | Why |
|---|---|---|
| **CR-1** | HR Settings → "Default Holiday List" used for new Employee inserts | Closes HOL-7. Today new employees have `holiday_list=None` and can't apply optional leave until HR sets it manually. |
| **CR-2** | Reorder Select options to `Fixed / Optional / Weekly Off` so the Frappe-default for blanks is Fixed (matches the stated conservative-default rule) | Cosmetic alignment; current behavior surfaces Optional as the field's pre-fill, which contradicts the rule's intent. |
| **CR-3** | Auto-mark national/regional holidays as Fixed via a seeded import (e.g., upload an ICS file) | Onboarding ergonomics for new sites. |
| **CR-4** | Coverage report `myhr.api.get_holiday_coverage()` — for HR to see which employees have / don't have a holiday list set | Pairs with CR-1 to fully close HOL-7. |
