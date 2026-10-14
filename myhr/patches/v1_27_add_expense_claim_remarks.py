"""Ensure Expense Claim Custom Fields exist (Remarks per line + Approver Name).

Two fields, both belt-and-braces with `_ensure_custom_fields` on after_migrate:

  - Expense Claim Detail.custom_remarks (Long Text) — claimant's note per row.
  - Expense Claim.expense_approver_name (Data, fetch_from User.full_name) —
    persisted mirror of the approver's name so PWA surfaces stop falling back
    to the email. Field name is intentionally unprefixed; the entire PWA
    already references it under this exact name.

Both inserts are idempotent (skip if Custom Field row already exists).

Numbering note: v1_23..v1_26 are reserved for the Leave Policy + Travel &
Expense feature work that currently lives on the `staging` branch (reverted
off main 2026-05-13). Skipping to v1_27 keeps that future merge collision-free.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def _ensure(field_name: str, dt: str, payload: dict) -> bool:
	"""Create a single Custom Field unless it already exists. Returns True iff created."""
	if frappe.db.exists("Custom Field", field_name):
		return False
	create_custom_fields({dt: [payload]}, ignore_validate=True)
	return True


def execute():
	created = []

	if _ensure(
		"Expense Claim Detail-custom_remarks",
		"Expense Claim Detail",
		{
			"fieldname": "custom_remarks",
			"label": "Remarks",
			"fieldtype": "Long Text",
			"insert_after": "description",
			"description": (
				"Claimant's free-text note to the approver for this line item."
			),
		},
	):
		created.append("Expense Claim Detail-custom_remarks")

	if _ensure(
		"Expense Claim-expense_approver_name",
		"Expense Claim",
		{
			"fieldname": "expense_approver_name",
			"label": "Expense Approver Name",
			"fieldtype": "Data",
			"insert_after": "expense_approver",
			"fetch_from": "expense_approver.full_name",
			"read_only": 1,
			"hidden": 1,
			"no_copy": 1,
			"description": (
				"Read-only mirror of expense_approver's User.full_name. "
				"Populated via fetch_from on validate."
			),
		},
	):
		created.append("Expense Claim-expense_approver_name")

	if created:
		frappe.clear_cache(doctype="Expense Claim")
		frappe.clear_cache(doctype="Expense Claim Detail")
		frappe.db.commit()
		print(f"v1_27: created Custom Field(s): {', '.join(created)}")
	else:
		print("v1_27: all Custom Fields already present, nothing to do.")
