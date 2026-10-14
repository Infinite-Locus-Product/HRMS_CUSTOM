# Offboarding — Testing Guide

How to test the employee separation flow end to end, on Desk and in the PWA.
Written for staging, but the same steps work on any site.

The flow spans **two workflows, six doctypes and three surfaces**, and most of
its failure modes surface late. This guide is ordered so that anything which
blocks a later stage is caught before you get there.

---

## 1. Preflight — always run this first

```bash
bench --site <site> execute myhr.offboarding_preflight.check --kwargs "{'employee': '<EMP-ID>'}"
```

Reads only; writes nothing. It checks the schema, both workflows, the two
permission grants that are invisible until someone is blocked by them, and the
four Employee fields the flow depends on.

**Any `FAIL` blocks the flow partway through — fix before testing.**

| Report line | What it means |
|---|---|
| `Exit Interview submit: NOBODY` | Stock HRMS grants submit to no role. The relieving letter can never be released. `bench migrate` grants it to HR Manager. |
| `MISSING HR Manager, System Manager` | A Custom DocPerm was added to a doctype that had none, silently revoking the stock roles. |
| `no Holiday List` | **L2 approval will fail.** HRMS builds the separation tasks on submit and needs one. |
| `no L1` / `no L2` | The resignation cannot be routed — the workflow gates on the person named on the record. |
| `notice period is 0` | Shortfall is always 0 and the buy-out logic is inert. Not fatal; the flow just proves nothing. |
| `Internal email domains: EMPTY` | Mailbox forwarding accepts *any* address, including gmail. That check will appear to pass when it is simply switched off. |
| `wkhtmltopdf not usable` | Expected on most dev machines. The relieving-letter gate still works; only the PDF render fails. |

---

## 2. Test data you need

One leaver and two managers, each with a **User** linked via `user_id` and the
**Employee** role. The workflow gates on the individual named on the record, so
an HR login cannot stand in for a manager.

On the leaver's Employee record:

- **Reports to** — the L1 approver
- **L2 / HR Manager** — the L2 approver
- **Notice Period (Days)** — non-zero
- **Holiday List** — on the employee, or a company default

Plus **HR Settings → Internal Email Domains** = your domain, e.g. `fixxly.in`.

> One live separation per employee. If preflight warns that one exists, cancel
> and delete it first — **and mind the order**: settlement, then HR clearance,
> then IT clearance, then manager clearance, then the separation. They link to
> each other and the reverse order fails.

### The relieving letter print format — once per site

The letter template is in git at
`myhr/myhr/print_format/fixxly_relieving_letter/fixxly_relieving_letter.html`,
but the **Print Format record is not shipped** — create it by hand in Desk on
every site, before anyone tries to release a letter:

| Field | Value |
|---|---|
| Name | `Fixxly Relieving Letter` — exact, the release action looks it up by name |
| DocType | `Separation HR Clearance` |
| Module | `myHR` |
| Custom Format | **ticked** |
| HTML | anything non-empty, e.g. `<p>Ignored — the template is in myhr/myhr/print_format/fixxly_relieving_letter/.</p>` |

The HTML field is never rendered: frappe reads the file off disk and only falls
back to the field. It still cannot be left blank — `Print Format.validate` throws
*"HTML is required"* when Custom Format is ticked — so put the note above in it.

**Do not edit the letter in Desk.** While the file exists, anything typed into
that field is ignored, so the edit looks applied and does nothing. Edit the file
in git.

Both ways this can go wrong are silent in frappe — a missing record, or one
without Custom Format ticked, falls back to the Standard format, which is a dump
of the clearance form's fields. So `release_relieving_letter` checks first and
refuses with *"Print Format Not Set Up"* rather than issuing the wrong document.

To change who signs the letter, the signature image or the settlement window,
edit the constants at the top of the template file.

---

## 3. The flow

Each step lists **who**, **where**, and what to verify. Expected values assume a
90-day notice period; recompute for yours.

### Stage A — the leaver files · PWA

**Leaver** → `/hrms/profile` → **Separation → Resignation**

Reason, detail, requested relieving date, buy-out yes/no → **Submit**.

- [ ] Official End Date = resignation date + notice period
- [ ] Shortfall = official end − requested date
- [ ] State `Pending L1 Approval`, **docstatus still 0**
- [ ] The form locks; re-saving is refused
- [ ] Detailed Reason blocks above 500 characters
- [ ] Buy-out = Yes demands an amount

### Stage B1 — L1 rejects, then approves · PWA

**L1** → Home → **Separation Approvals**

Reject with no reason first.

- [ ] Refused without a reason
- [ ] After rejecting: state `Rejected`, docstatus still 0, decision stamped
- [ ] The leaver can edit and re-submit

Then approve, **moving the relieving date** to something other than requested.

- [ ] `L1 Approved` ticked, state `Pending L2 Approval`
- [ ] Buttons disappear; a status banner replaces them
- [ ] **Shortfall recalculates against the approved date**, not the request
- [ ] L2's inbox now shows it; L1's is empty

### Stage B2 — L2 approves · PWA

**L2** → same inbox → **Approve**

- [ ] State `Approved`, **docstatus 1**, both checkboxes ticked
- [ ] `Employee.relieving_date` is now set
- [ ] **Four drafts exist**: Manager Clearance, IT Clearance, HR Clearance, Full and Final Statement
- [ ] The leaver's Resignation screen now shows **Your Clearances**

> If a draft fails to create you get an orange message naming it, the approval
> still stands, and the reason is in the Error Log. That is intended: two levels
> of approval must not be undone by a downstream problem.

### Stage 6 — Manager Clearance · PWA, both halves

**Leaver** → Resignation → **Handover & Clearance**

- [ ] A row accepts a **file**, a link, or a note — a row with none of the three is refused
- [ ] Attaching on a fresh handover saves a draft first, then uploads
- [ ] Draft saves while incomplete; **Submit** is disabled until all three confirmations are ticked

**L1** → Separation Approvals → the green **Handover** row

- [ ] *KT Received = Yes* is **disabled** until a document and a successor exist
- [ ] Complete is refused without remarks
- [ ] Complete is refused with the access-revocation question unanswered
- [ ] Listing systems **and** ticking Not Applicable is rejected as contradictory
- [ ] Complete is refused while the separation is not Approved

### Stage 7 — IT Clearance · Desk

**IT** (HR Manager or HR User today — there is no IT role yet)

One row per asset. Try each of these; all should be refused:

- [ ] A returned item with no condition
- [ ] Damaged or Missing with no recovery amount
- [ ] **A Good item carrying a recovery amount**
- [ ] The same asset listed twice
- [ ] Access revocation later than 23:59 on the last working day
- [ ] Mailbox forwarding to an external domain

Then:

- [ ] Total recovery is computed and cannot be typed
- [ ] Revocation defaulted to 23:59 on the last working day; earlier is accepted
- [ ] Leaver sees it all read-only at Resignation → **IT Clearance**

### Stage 8 — HR Clearance and the relieving letter · Desk

**HR Manager**

Create the **Exit Interview**, status Completed, and **submit it**.

- [ ] The first save on the clearance demands **Re-hire Eligibility** (the stub was raised with mandatory fields skipped)
- [ ] Re-hire = No demands an internal reason
- [ ] **Release** lists *every* blocker at once, not one at a time
- [ ] A **draft** interview marked Completed does **not** open the gate
- [ ] Release is refused before the last working day
- [ ] Leaver sees status and a Download button — and **never** re-hire eligibility

> Without `wkhtmltopdf` the PDF will not render. Hitting the render error means
> the gate passed, which is the part under test.

### Stage 9 — Full & Final · Desk

**Finance — must hold HR Manager.** System Manager cannot submit this; stock
HRMS grants submit to HR Manager only.

- [ ] Payables pre-seeded from withheld salary slips, gratuity, expense claims
- [ ] **IT Asset Recovery already present as a receivable row**
- [ ] Net = payable − receivable, read-only
- [ ] Saving repeatedly leaves **one** recovery row, not several
- [ ] Zeroing a recovery removes its row
- [ ] Submit refused while either clearance is unfinished
- [ ] Submit refused while the HR Ops waiver flag is set
- [ ] Submit refused without Finance Remarks
- [ ] HRMS separately refuses while any line is Unsettled
- [ ] Leaver sees the breakdown; **their manager does not**

---

## 4. Who can do what

| Doctype | Employee | HR User | HR Manager | System Manager |
|---|---|---|---|---|
| Employee Separation | read, write, create, submit | read, write, create | read, write, create | full |
| Manager Clearance | read, write, create, submit | read, write, create | full | full |
| IT Clearance | **read only** | read, write, create, submit | full | full |
| HR Clearance | **read only** | read, write, create | full | full |
| Full and Final Statement | — | read, write, create | + **submit, cancel** | read, write, create |
| Exit Interview | — | read | + **submit, cancel** | read, write, create |

Employee rows are narrowed further by permission hooks: an employee sees only
their own records, a manager only the ones naming them. The **settlement and HR
clearance are leaver-only** — a manager cannot see either, because they itemise
pay and carry re-hire eligibility.

---

## 5. Automated tests

```bash
bench --site <site> run-tests --app myhr
bench --site <site> run-tests --module myhr.tests.test_employee_separation
```

| Module | Covers |
|---|---|
| `test_employee_separation` | Stage A rules, the approval workflow, per-person gating, downstream draft creation |
| `test_separation_manager_clearance` | Stage 6 rules and its workflow |
| `test_separation_it_clearance` | Stage 7 — hardware, revocation ceiling, mailbox domain |
| `test_separation_hr_clearance` | Stage 8 — the release gate, and the Exit Interview permission |
| `test_full_and_final` | Stage 9 — recovery rows, the net, the submit gates |
| `test_clearance_api` | The PWA endpoints and what each role is allowed to see |

`test_missing_in_reminder` fails on sites where older Employee records lack
myHR's mandatory fields. That is pre-existing and unrelated.

---

## 6. Known gaps

- **No IT role.** IT needs HR Manager or HR User to fill stage 7.
- **The relieving letter has no print template** — it renders with Frappe's default layout.
- **The notice-period shortfall recovery is entered by hand.** The per-day rate is undefined, so the field exists and the calculation does not.
- **Cancelling a separation leaves the four drafts behind.**
- **Deleting a separation** requires deleting the settlement, then HR, IT and manager clearances first.
