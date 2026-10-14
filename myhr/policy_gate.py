"""Single source of truth for the "have you acknowledged your mandatory HR
policies" gate.

Used by Employee Checkin (validate) and Attendance Request (validate). Reads
from the standalone `Policy Acknowledgement` doctype — `Policy Action Task`
on `Employee Action Centre` is the legacy source and is no longer consulted.
"""

import frappe


def get_blocking_policies(employee: str) -> list[dict]:
	"""Return active, mandatory-checkin HR Policies the employee has NOT
	acknowledged at the current version.

	Each row: {"name": "POL-XXXX", "policy_name": "<title>", "file": "<url>"}.
	Empty list means the employee is clear to proceed.
	"""
	from myhr.policy_hooks import query_employee_pas

	rows = query_employee_pas(
		employee,
		statuses=("Pending",),
		blocking_only=True,
		fields=["pa.hr_policy AS name", "hp.policy_name", "hp.file"],
	)
	return rows


def assert_policies_acknowledged(employee: str, action_label: str = "proceed") -> None:
	"""Throw if the employee has any blocking pending acknowledgements.

	The thrown message lists policy *titles* (not internal names) so the
	server-side fallback is human-readable. The PWA's pre-flight modal is the
	primary UX; this throw is the backstop for any path that bypasses the
	pre-flight (Desk save, REST API, scheduled job, etc.).
	"""
	pending = get_blocking_policies(employee)
	if not pending:
		return

	titles = ", ".join(p["policy_name"] or p["name"] for p in pending)
	frappe.throw(
		f"Cannot {action_label} until the following HR policies are acknowledged: {titles}",
		title="Policy Acknowledgement Required",
	)
