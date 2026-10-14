# Staging setup — recruitment features (branch `feat/job-applicant-action-centre-fields`)

What ships with the code versus what must be configured by hand in Desk after
deploying this branch. Written 2026-09-11.

## 1. Deploy steps (server)

```bash
bench --site <staging-site> migrate          # doctypes, custom fields, web form, hooks
bench build --app myhr                       # serves /assets/myhr/images/* (logo, signature)
bench --site <staging-site> clear-cache
```

Ensure `wkhtmltopdf` is installed on the server (Frappe Cloud has it) or PDF
download of the offer letter fails; browser print preview still works.

## 2. Installed automatically by migrate — do NOT recreate

| Area | What arrives |
|---|---|
| Job Applicant | Gender, DOB, Age (computed), **Father's Name**, Passport Size Photo, Total Years of Experience, Employee Location, Current/Permanent Address, **Department** (below Status, fetched from the opening), Screening Questions tab |
| Job Opening | Screening Questions tab + table; Application Web Form Route defaults to `apply` on save |
| Job Offer | Compensation tab: Components table, Deductions table, computed summary (Gross / Fixed / Deductions / Take Home / Total Annual CTC), Variable Pay input |
| Employee Action Centre | Date of Joining, Preferred Contact Email, family fields (father/mother DOB, spouse, 2 children), Emergency Relation, Passport section, Name as per Bank Records |
| Appointment Letter | **Job Offer** link (filtered to the applicant's offers, accepted one preselected) — feeds designation, CTC, annexure, Location and Work Arrangement into the print; **Applicant Email** (fetched from the Job Applicant) so a Notification can address the candidate |
| Skill | Six standard competencies seeded as Skill records with `Default Competency` ticked (see `setup.py:DEFAULT_COMPETENCIES`); a new Interview Type pre-fills its Expected Skillset from them |
| Interview Feedback | Qualitative Assessment section: Key Strengths, Areas for Development, Overall Hiring Decision, Suggested Next Steps |
| Web Form | `/apply` — public Job Application form with dynamic screening questions (incl. Father's Name) |
| Reference templates | `apps/myhr/templates/` — `fixxly_offer_letter.html`, `fixxly_appointment_letter.html`, `fixxly_appointment_letter_template_text.md` (paste sources; NOT installed by migrate) |
| Assets | `/assets/myhr/images/fixxly-logo.png`, `/assets/myhr/images/ceo-signature.png` |

## 3. Configure by hand in Desk (once per site)

### 3.1 Letter Head — `/app/letter-head/new`
- Name: `Fixxly Private Limited`; tick **Is Default**.
- Header Source: **HTML** →

```html
<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #222; padding-bottom:10px; margin-bottom:16px;">
  <img src="/assets/myhr/images/fixxly-logo.png" style="height:56px;">
  <div style="text-align:right; font-size:9pt; line-height:1.4; color:#333;">
    <div style="font-weight:700; color:#1f2a44; font-size:10pt;">FIXXLY PRIVATE LIMITED</div>
    <div>4th Floor, Mantri Junction, JP Nagar,</div>
    <div>Beginest Suite 42, Bangalore — 560041</div>
  </div>
</div>
```

- Footer Source: **HTML** →

```html
<div style="border-top:1px solid #bbb; padding-top:6px; text-align:center; font-size:8.5pt; color:#666;">
  Fixxly Private Limited &nbsp;|&nbsp; CIN: U46901KA2026PTC221154 &nbsp;|&nbsp; GSTIN: 29AAHCF0452B1Z0
</div>
```

- If Fixxly Retail Private Limited also issues offers, create a second Letter Head for it.

### 3.2 Print Formats — `/app/print-format/new` (one per letter)
Maintained in Desk on purpose (not installed by migrate). The paste sources live in
the repo at **`apps/myhr/templates/`** — open the `.html` in a text editor, copy all,
paste into the HTML field.

| Print Format name | DocType | Paste source |
|---|---|---|
| `Fixxly Offer Letter` | Job Offer | `templates/fixxly_offer_letter.html` |
| `Fixxly Appointment Letter` | Appointment Letter | `templates/fixxly_appointment_letter.html` |

For each: Module myHR · Standard **No** · Print Format Type **Jinja** · tick
**Custom Format** · paste HTML · margins 12/12/15/15, Page Number Hide (optional).
Both read the Letter Head for header/footer and the two asset images above; the
appointment letter additionally reads the linked Job Offer (designation, CTC,
annexure, Location / Work Arrangement terms) and the Job Applicant (gender,
father's name, address).

### 3.2a Appointment Letter Template — `/app/appointment-letter-template/new`
Name `Fixxly Employment Agreement`. Copy Introduction, the 22 Terms rows and the
Closing Notes **exactly** from `templates/fixxly_appointment_letter_template_text.md`
— the `{{ … }}` placeholders in that text are what the print format fills in.
Review the two legal wording issues flagged at the top of that file with HR/legal.

### 3.3 Print Settings — `/app/print-settings`
- **Repeat Header and Footer**: ON (letter head on every PDF page).

### 3.4 Salary Components — `/app/salary-component`
The **Type** decides which Job Offer table accepts the row.

| Type | Components |
|---|---|
| Earning | Basic + DA, HRA, Statutory Bonus, LTA Reimbursement, Special Allowance |
| Employer Contribution | PF + EDLI Employer Contribution, ESI Employer |
| Deduction | PF Employee Contribution, ESI Employee, Professional Tax, Income Tax |

### 3.5 Offer Terms + Job Offer Term Template — `/app/job-offer-term-template/new`
Create the template HR will pick on each offer. Rows (create missing Offer Terms inline):
Remuneration (CTC) = "As per Annexure-1" · Statutory Deductions = "Will be applicable as
specified by the relevant Central or State Law" · Date of Joining (per candidate) ·
**Location** (per candidate) · **Work Arrangement** (On-Site / Hybrid / Remote, per candidate) ·
Probation Period = "3 Months" · Notice Period = "1 Month" ·
Working Hours = "As per company Policy." · Working Days = "As per company Policy."

The Offer Term names **Location** and **Work Arrangement** must match exactly — the
appointment letter reads *Place of Posting* and *Work Arrangement* from those rows.

### 3.5a Emailing the letters to the candidate

Fully configurational. Prerequisites: an Email Account with **Enable Outgoing** +
**Default Outgoing** at `/app/email-account`, and **Allow Print for Draft** ticked in
Print Settings (Appointment Letter is never submitted, so without it the PDF
attachment throws).

**Automatic — one Notification per letter** (`/app/notification/new`):

| | Offer letter | Appointment letter |
|---|---|---|
| Document Type | Job Offer | Appointment Letter |
| Send Alert On | Submit | Save |
| Receiver By Document Field | `applicant_email` | `custom_applicant_email` |
| Attach Print → Print Format | Fixxly Offer Letter | Fixxly Appointment Letter |

Channel Email, Enabled ticked, **Message Type: HTML** (the default Markdown
collapses line breaks). The message context exposes only `doc`, so placeholders
must be `{{ doc.applicant_name }}`, `{{ doc.designation }}` — a bare
`{{ candidate_name }}` renders empty. Offer-letter body used today:

```html
<p>Dear {{ doc.applicant_name }},</p>
<p>Greetings from Fixxly!</p>
<p>We are pleased to offer you the position of <b>{{ doc.designation }}</b> at Fixxly.
Please find your Offer Letter attached for your review.</p>
<p>Kindly review the details and confirm your acceptance.</p>
<p>We look forward to welcoming you to the Fixxly team!</p>
<p>Best Regards,<br>HR Team<br>Fixxly</p>
```

**Manual** — on the document, Menu → Email, tick *Attach Document Print*, pick the
format. Reusable wording lives in an Email Template (`/app/email-template`).

**Blank forms the candidate returns** (PF nomination, bank mandate …): upload each
once at `/app/file` with **Is Public** ticked and put the `/files/<name>.pdf` links in
the Notification body — Notification cannot attach a fixed library of files, only the
document's own print and its own attachments.

Verify the first send in `/app/email-queue`.

### 3.6 Job Applicant Source — `/app/job-applicant-source`
Confirm **Website Listing** exists (HRMS seeds it). The web form stamps it on every applicant.

### 3.7 Existing Job Openings
Openings created before this deploy have an empty Application Web Form Route.
Open and save each live opening (or set the route to `apply`) so the careers page
links to the new form.

## 3.8 Interview competencies — nothing to configure, but know how it works

The six competencies from the *HRMS Interview Feedback Questionnaire* are seeded as
**Skill** records by `bench migrate` and flagged **Default Competency**.

- Opening a **new** Interview Type pre-fills its Expected Skillset with every
  flagged Skill. The rows are left unsaved — HR edits, removes, or adds
  round-specific skills (e.g. GAP ANALYSIS for a BA round) before saving.
  It never touches an Interview Type that already exists or already has rows.
- Stock HRMS then copies that skillset into every Interview Feedback's Skill
  Assessment when the Interview Type is chosen, each with a 1–5 star rating.
- To retire a competency, untick **Default Competency** on its Skill record. To add
  one, create a Skill and tick the box. No release needed; migrate will not
  re-tick or overwrite what HR changed.

**Hiring decision.** Interview Feedback keeps the stock **Result** field
(Cleared / Rejected) because `Interview.status` and the Job Applicant status chain
depend on those exact values. The questionnaire's four-way call lives in the
separate **Overall Hiring Decision** field and is advisory only.

## 4. Smoke test
1. Create a Job Opening with department + two screening questions (one mandatory), Publish, Save → route shows `apply`.
2. Private window: `/apply/new?job_title=<opening id>` → opening/designation/department prefilled, questions visible, no Status section. Submit without the mandatory answer → blocked. Answer → submitted.
3. `/app/job-applicant` → new record has Age, Department, Status Open, Source Website Listing, answers under Screening Questions.
4. Create a Job Offer for that applicant: pick the term template, fill Components / Deductions / Variable Pay, Save → summary fields populate.
5. Print → "Fixxly Offer Letter" with Letter Head on → logo header, terms list, Annexure A, acknowledgement at the end.
6. `/apply/new` with no opening → notice shown, no Submit button.
7. Mark the offer Accepted and submit it. Create an Appointment Letter: pick the applicant → Job Offer preselects; pick the template → introduction/terms/closing copy in; set Appointment Date; Save. Print → "Fixxly Appointment Letter": welcome page, agreement with name / father's name / address / designation / posting / CTC filled, acceptance block, Salary Annexure.

## 5. Local dev gotcha

`bench migrate` exits with *"Cannot run bench migrate without the services running"*
when the bench redis instances are down — and that message contains neither "error"
nor "traceback", so it is easy to mistake for a clean run. Always check the exit code.
Fix with `bench start`, or start just the two instances:

```bash
redis-server config/redis_cache.conf --daemonize yes   # port 13000
redis-server config/redis_queue.conf --daemonize yes   # port 11000
```

## 6. Not configured yet / open items
- Mandatory flags for the new Employee Action Centre fields (all optional today).
- Optional CTC template per grade; live on-screen totals (today totals appear after Save).
