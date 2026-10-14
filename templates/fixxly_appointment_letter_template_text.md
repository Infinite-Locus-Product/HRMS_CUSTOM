# Appointment Letter Template — "Fixxly Employment Agreement"

Paste this into `/app/appointment-letter-template/new` on each server. Text is taken
verbatim from *Employment Agreement_Fixxly.pdf* (2026) with the bracketed blanks
replaced by placeholders. Placeholders are filled by the print format
(`templates/fixxly_appointment_letter.html`) from the applicant, the linked Job
Offer, and the Appointment Letter itself:

| Placeholder | Filled from |
|---|---|
| `{{ employee_name }}` | Appointment Letter → Applicant Name |
| `{{ salutation }}` / `{{ child_of }}` | Job Applicant → Gender (Mr./Ms., Son/Daughter) |
| `{{ father_name }}` | Job Applicant → Father's Name (collected on the `/apply` form) |
| `{{ address }}` | Job Applicant → Permanent Address (falls back to Current Address) |
| `{{ designation }}` | linked Job Offer → Designation |
| `{{ work_arrangement }}` | linked Job Offer → Offer Terms row **Work Arrangement** |
| `{{ place_of_posting }}` | linked Job Offer → Offer Terms row **Location** |
| `{{ doj }}` | Appointment Letter → Appointment Date |
| `{{ ctc_annual }}` / `{{ gross_monthly }}` | linked Job Offer → Total Annual CTC / Gross CTC (Monthly) |
| `{{ company }}` | Appointment Letter → Company |

> Review before use (carried over from the source PDF): clause **11.0** ends with a
> second "(f) Termination by notice" paragraph that duplicates clause 10.0(f) with a
> Basic-Salary variant; and clauses 10.0(e)/(f) and 18.0 refer to "clause 11a/11b/11"
> where the termination clause is actually 10.0. Legal/HR should settle the wording in
> the template — the print format prints whatever the rows contain.

---

## Template Name
`Fixxly Employment Agreement`

## Introduction (page 1 — welcome letter)

```
Website: https://fixxly.in/

Dear {{ employee_name }},

It gives us immense pleasure to welcome you to the Fixxly team as you begin your professional journey with us today. At Fixxly, we believe that true progress is achieved when bold ideas meet speed, operational rigor, and relentless execution.

We are on a mission to transform the quick-commerce landscape by delivering trade essentials and job-site materials rapidly through technology-enabled logistics, ensuring professionals save time and avoid costly downtime.

Fixxly's Culture - Here, you will join a high-growth, dynamic workforce driven by innovation, transparency, integrity, and a customer-first mindset. We take pride in building a collaborative environment where team members are empowered to solve complex, real-world problems, continuously learn, and enrich the professional growth of their colleagues.

You are a core part of the Fixxly team now!

{{ employee_name }}, we are thrilled to bring your skills and commitment onboard, and we are confident that your expertise will play a pivotal role in advancing our shared mission.

Please review the formal documentation enclosed with this letter. Should you have any questions regarding your terms of engagement, feel free to reach out to our HR Operations team.

Welcome aboard, and we wish you a rewarding, impactful, and successful career at Fixxly!
```

## Terms (one row per block — Title / Description)

**Row 1 — Title:** `Agreement`
```
This Employment Agreement ("Agreement") is entered into on this {{ doj }} at Bengaluru, Karnataka.

BY AND BETWEEN

{{ company }}, a company incorporated under the laws of India, having its registered office at Flat No. 533, Ranka Court Apts, 18 Cambridge Road, Ulsoor, Bengaluru, Karnataka - 560008 (hereinafter referred to as the "Company", which expression shall unless repulsive to the context or meaning thereof, include its successors, permitted assigns, and affiliates);

AND

{{ salutation }} {{ employee_name }}, {{ child_of }} of {{ father_name }}, residing at {{ address }} (hereinafter referred to as the "Employee", which expression shall unless repulsive to the context or meaning thereof, include his/her legal heirs, executors, and permitted assigns).

The Company and the Employee shall individually be referred to as a "Party" and collectively as the "Parties".

WHEREAS:
1. The Company is engaged in tech-enabled logistics and quick-commerce delivery of trade essentials and construction materials.
2. The Company desires to employ the Employee, and the Employee agrees to accept such employment with the Company, subject to the terms and conditions hereinafter set forth.

NOW, THEREFORE, THIS AGREEMENT WITNESSETH AS FOLLOWS:
```

**Row 2 — Title:** `1.0 Position & Placement Details`
```
We are pleased to offer you the position of "{{ designation }}". Your employment details are as follows:
● Designation: {{ designation }}
● Work Arrangement: {{ work_arrangement }}
● Place of Posting: {{ place_of_posting }}
● Date of Joining: {{ doj }}
```

**Row 3 — Title:** `2.0 Salary & Remuneration`
```
Your Cost to Company (CTC) per annum will be INR {{ ctc_annual }}/- wherein your monthly gross will be INR {{ gross_monthly }}/- per month. You are required to keep your salary information confidential at all times and not disclose it to anybody else in the Company.
```

**Row 4 — Title:** `3.0 Probation & Leave`
```
3.1 You will be on probation for a period of three (3) months from the date of joining the Company. You will be eligible for leave as per the leave rules of the Company from your date of joining.
3.2 During the Probation period, your service may be terminated at the discretion of the Company, with or without assigning any reason, with fifteen (15) days' notice or payment of Basic Salary in lieu of notice. In case you decide to resign from the Company during the Probation period, you will be liable to give fifteen (15) days' notice in writing or pay Basic Salary in lieu thereof. Any recovery or payout in lieu of notice period will be calculated strictly on your Basic Salary and is subject to acceptance by the Company. Post probation notice period will be one (1) month (30 days).
On satisfactory completion of probation, you may be considered for regular employment in the Company and a Letter of Confirmation will be issued to you. Your period of probation may be modified at the discretion of the Company, depending on your performance and other factors.
```

**Row 5 — Title:** `4.0 Work Location & Operational Schedules`
```
4.1 Store & Field Operations Teams (On-Site): Employees assigned to store locations, fulfillment hubs, or field operations are required to work on-site. You are expected to strictly adhere to store operational hours, shift rosters, punctuality standards, and safety guidelines.
4.2 Remote/Hybrid Roles: For roles approved for remote or hybrid working, you must maintain a private, secure workspace, connect through secure access networks, and comply with all company data security protocols. The Company reserves the right to modify work arrangements or require full-time on-site presence based on operational needs.
```

**Row 6 — Title:** `5.0 Confidentiality`
```
During the term of your employment, and at any time thereafter, you shall maintain strict confidentiality and not divulge, disclose, or impart to any person/organization "Confidential Information" about {{ company }} (the "Company") which may be your personal privilege to be aware of, by virtue of your employment in the Company. You may access and retain copies (either in physical or electronic format) of, all such Confidential Information, only to the extent required for the effective discharge of your duties. In any case, you will not be permitted to transmit such Confidential Information, in any format whatsoever, outside the facilities of the Company.

Para II: "Confidential Information" shall include, but shall not be limited to, information which is not generally known to the competitors of the Company concerning the Company's business and operations, trade secrets, customer identity and lists, sales and management, supplier lists, employee effectiveness and compensation, market strategies and plans, profit and loss information, product cost, gross margins, credit and other sales terms and conditions, computer programs, source code, formats and algorithms, other technical information and know-how, systems and procedures, trade secrets, databases, systems, and generally the Company's goodwill with its customers. Confidential Information shall also include information contained in projects executed by the Company (such as scope of work, Company's client information, questions, responses, analyses, costs, pricing, methods, and reports), marketing surveys, manuals, memoranda, price lists, employee programs, records, training methods, personnel information, and all other proprietary information, whether or not designated, legended, or otherwise identified by the Company as Confidential Information. Confidential Information shall also include all names and addresses of employees of the Company, comparable confidential information of the Company's clients, including without limitations all survey questions and responses; and you shall specifically acknowledge that as a general matter, all client-supplied information is considered as Confidential Information.
```

**Row 7 — Title:** `6.0 Intellectual Property`
```
The rights to any inventions, improvements, discoveries, concepts, ideas, systems, methods, computer programs, proprietary models, databases, computer software and works of authorship related to the Company's operations and arising out of any work done in the course of your employment would automatically vest with the Company. In this connection, where required, the Company may obtain patent rights in its name (or jointly with others) based on your invention, discovery, or other creative effort. You are specifically made aware that you will not be liable to any compensation for such acts, and that any rewards which the Company may choose to bestow will not be deemed to confer any rights towards that invention, discovery, or improvement in the above for you.
```

**Row 8 — Title:** `7.0 Continuing Integrity`
```
You shall not at any time after the termination or cessation of employment for any reason whatsoever of your employment with the company for whatever cause, either personally or by your agent, directly or indirectly:
(a) Represent yourself as being in any way connected with, or interested in, the business of the company whether orally, through the internet, media, any social, professional networking sites, blogs, or portals or as embodied in tangible materials.
(b) Either on your own account or for any person, firm or company, solicit orders or business from any customer or client of the company whether past, present, or potential whether orally, through the internet, media, any social, professional networking sites, blogs or portals or as embodied in tangible materials.
(c) Either on your own account or for any person, firm or company, solicit, interfere with or endeavor to entice away from the company any employee of the company whether orally, through the internet, media, any social, professional networking sites, blogs, or portals or as embodied in tangible materials.
(d) Do any other act or thing calculated to prejudice the interest of the business activities of the company whether present or contemplated.
```

**Row 9 — Title:** `8.0 Software Copyright Act`
```
We enforce the copyright act and any unauthorized copying of software, documentation, manuals etc. is an infringement of this act and is a disciplinary offence.
```

**Row 10 — Title:** `9.0 Job Assignments`
```
During the course of your employment, you may be given any assignment arising out of the Company's business that the management, in its judgment, reasonably feels is suited to your background, qualifications or experience. You will not refuse to carry out any assignment solely on the grounds that it has not been part of your usual duties during your employment.
```

**Row 11 — Title:** `10.0 Termination of Regular Employment`
```
(a) Termination on insolvency: If you become bankrupt or be adjudged insolvent or compound with your creditors, the Company shall be entitled to terminate forthwith without any notice or payment in lieu of notice.
(b) Termination on discovery and/ or identification of criminal records: If the Company, at any time during the subsistence of your employment, discovers and/ or identifies that you were convicted or are being convicted of any criminal offence or have had any past criminal records, the Company shall be entitled to terminate forthwith without any notice or payment in lieu of notice.
(c) Termination on incorrect past records: Your appointment is substantially based on the information provided by you. If it is found at any stage that the information provided by you is incorrect or that some information is suppressed, such act shall make you liable to immediate removal from the services of the Company. In such events, it would not be necessary for the Company to give you any notice, or payment in lieu thereof, whatsoever.
(d) Termination on misconduct or breach of the service conditions or provisions of this letter: If you shall at any time be guilty of misconduct, commit any breach of the service conditions or refuse or willfully neglect to perform to the satisfaction of the Company any of the duties entrusted upon you or commit any other act which in the opinion of the Company is prejudicial to the interest of or is an act of misconduct, the Company may at once, without any previous notice, terminate your services, apart from any action which the Company may take against you for breach of contract as deemed appropriate. In such events it would not be necessary for the Company to give you any notice, or payment in lieu thereof, whatsoever.
(e) Company's decision on termination to be final and binding: The Company's decision as to the occurrence of any events mentioned to clause 11a and 11b above shall be final and binding on you and you shall not be entitled to question the same on any ground whatsoever.
(f) Termination by notice: Without prejudice to clause 11a, 11b, 11c, 11d above, on being confirmed as a permanent employee, your appointment is terminable by either side giving thirty (30) days' notice in writing or payment in lieu thereof. However, in case of termination on the ground of gross misconduct, no notice period is required to be given by the Company. Your payment in lieu of notice period will however be subject to acceptance by the Company. You shall be governed by the resignation/ separation policy of the Company as applicable from time to time. In the event you serve a notice of termination of employment, any unauthorized shortfall in notice will be viewed as breach of contract and the Company reserves the right to take appropriate legal action against such person.
All notices under this letter shall be in writing and shall be served by sending the same by Registered Post addressed to either party at the address hereinbefore written and in proving service, it shall be sufficient to show that the same has been properly addressed and posted.
```

**Row 12 — Title:** `11.0 Non-Solicitation`
```
For the duration of your employment at the Company, and for a period of twelve (12) months thereafter, you shall not directly or indirectly either for yourself or as an agent of or in conjunction with any person or entity:
a) Solicit employment with, nor respond to the solicitation of your employment by, any of the Company's clients, either directly or indirectly.
b) Solicit and enter into any business relationship for the purpose of offering or selling quick-commerce trade essentials logistics, Information Technology Enabled Services, computer software development and support and professional services, to any customer, client, licensor, licensee, or any other business associate of the Company to the detriment of the Company.
c) Solicit, recruit, attempt to recruit, hire, attempt to hire, encourage, or support any employee of the Company to leave the employment of the Company.
d) Solicit, encourage, or support any supplier of goods or services, contractor, or consultant of the Company to discontinue supplies, contracting or providing services to the Company.
(f) Termination by notice: Without prejudice to clause 11a, 11b, 11c, 11d above, on being confirmed as a permanent employee, your appointment is terminable by either side giving thirty (30) days' notice in writing or payment of Basic Salary in lieu thereof. However, in case of termination on the ground of gross misconduct, no notice period or compensation is required to be given by the Company. Any notice period recovery or payment in lieu of notice shall be calculated exclusively on the Basic Salary component of your compensation structure and will be subject to final acceptance by the Company. You shall be governed by the resignation/ separation policy of the Company as applicable from time to time. In the event you serve a notice of termination of employment, any unauthorized shortfall in notice will be viewed as breach of contract and the Company reserves the right to recover the equivalent Basic Salary for the shortfall period or take appropriate legal action.
```

**Row 13 — Title:** `12.0 Guiding Principles / Policies & Procedures`
```
12.1 Working Hours: The standard work week for employees will be governed by the rules of the Company in this regard. The exact work timings will however be based on and may vary as per business needs and may require you to work in shifts. You are expected to report to work promptly at the scheduled time each workday.
12.2 Leave: You will be entitled for leave as per the leave rules of the Company from your date of joining.
12.3 Retirement: The employee shall retire on his/her reaching the age of fifty-eight (58) years or earlier if found medically unfit for the job assigned to him/ her at the sole discretion of the Company. The age or date of birth already given by the employee in his/her application or provident fund declaration, whichever is earlier shall be treated as binding and final. The Company may at its discretion extend the term of employment beyond the age of retirement on such terms specifically decided and agreed.
12.4 External Work: You will not take any direct/ indirect business or work, honorary or remunerators except with the prior written permission of the management in each case.
12.5 Profile Updates: You will keep us informed of any change in your residential address, civil or marital status and other such matters.
12.6 Statutory Deductions: Taxes and Deductions such as Income Tax, Professional Tax, and or any other statutory payments would be to your account.
12.7 Public Bodies: You will not seek membership of any local/ public body without obtaining prior permission of the Management in each case.
12.8 IT & Equipment Safety Policy: You are required to strictly adhere to the policies of the Company governing the use of the computing and telecommunication facilities which prohibits, among other things, the usage, download, storage and distribution of pornographic material, job sites, and viruses or any other material, from the internet or any other source, that may be potentially harmful to the business of the Company.
12.9 Asset Management & Return: You will be responsible for safe keeping and return in good condition/order, whenever demanded by the Company all Company owned/leased/hired property (including laptops, POS hardware, scanners, mobile devices, security tokens, and keys), which is/will be in your use, custody or charge for the business purpose of the Company during the course of your employment and shall return all such property to the Company prior to relinquishment of your charge, failing which the cost of the same will be recovered from the employee by the Company. You will always abide by the instructions given to you for their handling, legal, commercial and insurance related matters pertaining to the said property.
12.10 Company Decorum: You will observe general decorum and discipline and will be governed by policies and procedures and its guidelines as in force from time to time. The Company shall have the right to vary or modify any of the terms and conditions of service at any time, which shall be binding on you and shall override this letter to that extent.
12.11 Non-Representation: You agree that you will not at any time after the termination of your employment, either personally or by your agent directly or indirectly represent yourself as being in anyway connected with or interested in the business of the Company.
12.12 Entire Agreement: This letter sets forth the entire understanding of the Parties with respect to the subject matter hereof and supersedes all prior agreements between them relating thereto.
12.13 Further Acts: Each of the Parties agree to execute and deliver all such further instruments, and to do and perform all such further acts and things, as shall be necessary or convenient to carry out the provisions of this letter.
```

**Row 14 — Title:** `13.0 Loss of Lien`
```
In case of your overstaying sanctioned leave, or any absence without permission of more than 5 (five) consecutive working days, you shall lose lien of your services and the Company will be entitled to strike off your name from its rolls, without any reference to you.
```

**Row 15 — Title:** `14.0 Indemnity`
```
You expressly agree to defend, indemnify, and hold the Company harmless from and against any and all claims, demands, damages, injuries, expenses and liability arising from your acts of omissions or negligence.
```

**Row 16 — Title:** `15.0 Jurisdiction`
```
Any dispute arising out of the employment or terms of service shall be subject to the jurisdiction of competent court in Bengaluru, Karnataka.
```

**Row 17 — Title:** `16.0 Severability`
```
All terms and provisions of this letter are severable and any term or provision of this letter or any application thereof which may be prohibited or unenforceable by law shall be ineffective to the extent of such prohibition or unenforceability without affecting the remainder of this letter or any other application of such term or provision.
```

**Row 18 — Title:** `17.0 Successors and Assigns`
```
The Company shall have the right to assign its rights, obligations, and privileges hereunder to an assignee that agrees in writing to be bound by the terms and conditions of this letter Agreement. The terms and conditions of this Agreement shall also bind and inure to the benefit of the permitted successors of the Company. You shall not assign any of your rights, obligations or hereunder without the prior written consent of the Company.
```

**Row 19 — Title:** `18.0 Survival`
```
Upon the termination of your employment with the Company, due to the provision of clause 11 above or otherwise, clauses 5, 6, 7 and 12 above shall survive and continue in effect.
```

**Row 20 — Title:** `19.0 Acceptance`
```
The terms and conditions of your appointment will remain valid till the Company informs you about any change/ modifications and the said changes will override the terms and conditions of this letter from that date onwards. If the terms and conditions of offer enumerated in this letter of appointment, including its annexure, are acceptable to you, please confirm your acceptance by signing on the duplicate copy of this letter and returning it to the Company.
```

**Row 21 — Title:** `20.0 Force Majeure`
```
Neither Party shall be liable to the other for any delay or failure in the performance of any of its duties and obligations under this letter to the extent that such delay or failure is caused by any event or circumstances beyond its control including any Acts of God.
```

**Row 22 — Title:** `21.0 Submission of Documents`
```
IN WITNESS WHEREOF, the Parties hereto have executed this Agreement on the date and year first above written.
```

## Closing Notes (employee acceptance block)

```
Employee Acceptance:
Name: {{ employee_name }}
{{ child_of }} of: {{ father_name }}

Signature: …………………………………………… Date: …………………………………
```
