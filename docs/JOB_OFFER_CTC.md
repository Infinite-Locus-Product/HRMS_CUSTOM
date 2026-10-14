# Job Offer — CTC breakdown

Captures the HR compensation sheet on **Job Offer** so a print format can
render it. Configuration-first: one child doctype, custom fields via fixture,
and a single validate hook that does the arithmetic.

## Where things live

| Concern | Path |
|---|---|
| Child rows (component, type, monthly, annual) | `myhr/myhr/doctype/job_offer_salary_component/` |
| Compensation tab, two Tables, summary fields on Job Offer | `myhr/fixtures/custom_field.json` (`dt = Job Offer`) |
| Totals hook | `myhr/job_offer_hooks.py` (`doc_events["Job Offer"]["validate"]`) |
| Tests | `myhr/tests/test_job_offer_ctc.py` |

## Fields on Job Offer (Compensation tab)

- `custom_ctc_components` — Table. Earning and Employer Contribution rows.
- `custom_ctc_deductions` — Table. Deduction rows only (employee side).
- Summary (read-only, computed): `custom_gross_ctc_monthly/annual`,
  `custom_total_fixed_ctc_monthly/annual`, `custom_total_deductions_monthly`,
  `custom_take_home_monthly`, `custom_total_annual_ctc`.
- Input: `custom_variable_pay_annual`.

Each row: `salary_component` (Link), `component_type` (fetched from
`Salary Component.type`), `monthly` (HR input), `annual` (= monthly × 12).

## Formulas

```
Gross CTC (m)        = Σ monthly of Earning rows
Total Fixed CTC (m)  = Gross + Σ monthly of Employer Contribution rows
Total Deductions (m) = Σ monthly of deductions table
Take Home (m)        = Gross − Total Deductions
Annual values        = monthly × 12
Total Annual CTC     = Total Fixed CTC (annual) + Variable Pay (annual)
```

Employer contributions are **never** counted as deductions (decided
2026-09-11). A Deduction-type component in the components table, or an
Earning/Employer row in the deductions table, is rejected on save.

## Worked example (HR sheet)

| | Monthly | Annual |
|---|---|---|
| Earnings (Basic 25,313 + HRA 12,656 + Bonus 0 + LTA 5,063 + Special 5,644) | 48,676 | 584,112 |
| Employer PF 1,950 + ESI 0 | 1,950 | 23,400 |
| **Total Fixed CTC** | 50,626 | 607,512 |
| Variable Pay | | 67,500 |
| **Total Annual CTC** | | 675,012 |
| Deductions (PF 1,800 + ESI 0 + PT 200 + TDS 0) | 2,000 | |
| **Take Home** | 46,676 | |

The original sheet prints Gross 48,675 / Fixed 50,625 because each line was
rounded before summing. We store the exact sum of the entered monthly values.

## Print format

The offer-letter print format is **maintained in Desk, not in this repo**
(decision 2026-09-11). Create it as a Jinja *Custom Format* on Job Offer and
paste the template HTML. It reads: the Job Offer Terms table for the terms
list, the Compensation tab for Annexure A, and the Letter Head for header and
footer. The logo and CEO signature it references ship with the app at
`myhr/public/images/` (served as `/assets/myhr/images/...`).

## Not yet done

- Optional CTC template per grade with a "fetch" button.
- Live on-screen totals; today they appear after Save.
