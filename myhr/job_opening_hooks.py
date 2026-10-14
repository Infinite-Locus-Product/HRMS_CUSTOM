"""Job Opening doc_events — wired in hooks.py.

Two small jobs:
1. Default `job_application_route` to our web form so the careers page links to
   `/apply/new?job_title=<opening>` instead of the stock HRMS form.
2. Drop whitespace-only screening question rows before save.
"""

APPLY_ROUTE = "apply"


def validate(doc, method=None):
	if not (doc.get("job_application_route") or "").strip():
		doc.job_application_route = APPLY_ROUTE

	rows = doc.get("custom_screening_questions") or []
	kept = [r for r in rows if (r.get("question") or "").strip()]
	if len(kept) != len(rows):
		doc.set("custom_screening_questions", kept)
	for r in kept:
		r.question = r.question.strip()
