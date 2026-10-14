# Job Application web form + screening questions

Public application form at `/apply`, owned by myhr. Replaces the stock HRMS
`/job_application` form for our openings without touching `apps/hrms`.

## Flow

1. Recruiter creates a **Job Opening**, fills the **Screening Questions** tab
   (free-text questions, optional *Mandatory* tick), sets Publish, saves.
   `myhr.job_opening_hooks.validate` defaults *Application Web Form Route* to
   `apply` when blank, so the careers page links to
   `/apply/new?job_title=<opening>`.
2. Candidate opens that link as Guest. The web form shows every
   candidate-facing field on Job Applicant plus one textarea per question.
   Job Opening, Designation and Department are read-only and filled from the
   opening. HR-side fields (Status, Applicant Rating, Notes, Source, Source
   Name, Employee Referral) are **not** on the form; the server sets Status and
   Source.
3. On submit, the client script validates mandatory answers and writes the
   answers into the hidden `custom_screening_responses` Table field. Frappe's
   standard `web_form.accept` inserts one **Job Applicant**.
4. `myhr.job_applicant_hooks.validate` runs inside that insert: computes Age,
   forces Status = Open, sets Source = *Website Listing*, and rebuilds the
   response rows from the opening (see Security). HR sees the answers on the
   applicant's **Screening Questions** tab.

## Files

| Concern | Path |
|---|---|
| Question rows on the opening | `myhr/myhr/doctype/job_opening_question/` (child) |
| Answer rows on the applicant | `myhr/myhr/doctype/job_applicant_question_response/` (child) |
| Tab + Table custom fields on Job Opening / Job Applicant, `custom_department` (fetched from the opening, sits below Status), `custom_father_name` (collected for the appointment letter), and the 8 applicant data fields | `myhr/fixtures/custom_field.json` (loaded via `fixtures` in hooks.py) |
| Web form definition, per-request context, client script | `myhr/myhr/web_form/fixxly_job_application/` |
| Job Applicant validate hook (age, status, reconciliation) | `myhr/job_applicant_hooks.py` |
| Job Opening validate hook (route default, blank-question strip) | `myhr/job_opening_hooks.py` |
| Tests | `myhr/tests/test_job_application_form.py` |

Questions reach the browser server-side: `fixxly_job_application.py::get_context`
reads `frappe.form_dict.job_title`, checks the opening is published and Open,
and exposes only `name / question / is_mandatory` per row. The `.js` is a Jinja
template rendered with that context on every request (web forms are
`no_cache=1`). **No `allow_guest` API endpoint exists** for this feature.

## Security notes

- `web_form.accept` copies every listed web form field from the client payload
  verbatim. `read_only` and `hidden` are UI-only. There is no server whitelist
  of child-table columns. Therefore nothing posted is trusted:
  - Response rows are used only as `{source_question -> answer}` lookups.
    Question text and the mandatory flag are re-read from the opening; rows
    whose `source_question` is not one of the opening's rows are dropped;
    missing mandatory answers raise.
  - Status is forced to Open. Age is recomputed.
  - Unpublished or non-Open openings are rejected (HRMS only blocks Closed).
- Reconciliation runs only when `frappe.flags.in_web_form and doc.is_new()`,
  so HR edits to responses in Desk are never rewritten.
- `accept` is rate limited by Frappe at 10 submissions / 60 s / IP.
- Repeat applications from one email are allowed (HRMS appends `-1`, `-2`).

## Operations

- Add a question: edit the opening's Screening Questions tab. Existing
  applicants keep their snapshot text.
- Point an opening at the stock HRMS form instead: set its Application Web
  Form Route to `job_application`.
- Test as Guest: private window, `/apply/new?job_title=<opening name>`.
  `/apply/new` without a valid opening shows a notice and hides Submit.

## Findings

| # | Issue | Status |
|---|---|---|
| JAF-1 | Client omitting Status made `accept` post `""`, failing the mandatory check on insert. | **RESOLVED 2026-09-10** — hook forces `status = "Open"` for web form inserts; covered by tests. |
