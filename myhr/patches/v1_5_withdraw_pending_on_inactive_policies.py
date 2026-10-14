"""Backfill `Withdrawn` status on Pending PAs that point at inactive HR Policies.

Closes E-4. Before this change, deactivating a policy left Pending PAs in
that state forever — they showed in the PWA Policy Centre as Pending without
a reason and confused users. Now: when HR deactivates a policy, all its
Pending rows transition to Withdrawn (terminal, non-blocking, surfaced via
the history toggle in the PWA).

This patch closes the gap on existing data: on any site where a policy was
deactivated before this code shipped, find the orphan Pending rows and
transition them via the canonical helper so the audit log captures the move.
"""
import frappe


def execute():
	if not frappe.db.exists("DocType", "Policy Acknowledgement"):
		print("Policy Acknowledgement doctype not present; skipping.")
		return
	# Defensive: the PA Select options need to include 'Withdrawn'. The JSON
	# update should have synced before patches run, but check anyway.
	options = (
		frappe.db.get_value(
			"DocField",
			{"parent": "Policy Acknowledgement", "fieldname": "status"},
			"options",
		)
		or ""
	)
	if "Withdrawn" not in options:
		print("Policy Acknowledgement.status options not yet synced; skipping. "
			"Run `bench migrate` after JSON update.")
		return

	# `Policy Audit Log` doctype must exist before the canonical helper can write.
	if not frappe.db.exists("DocType", "Policy Audit Log"):
		print("Policy Audit Log doctype not present yet; skipping.")
		return

	from myhr.policy_audit import transition_pa_via_sql

	rows = frappe.db.sql_list(
		"""
		SELECT pa.name
		FROM `tabPolicy Acknowledgement` pa
		INNER JOIN `tabHR Policy` hp ON hp.name = pa.hr_policy
		WHERE pa.status = 'Pending' AND hp.is_active = 0
		"""
	)
	if not rows:
		print("No Pending rows on inactive policies; nothing to withdraw.")
		return

	count = transition_pa_via_sql(
		rows, "Withdrawn", via="Migration",
		note="v1_5 backfill: HR Policy deactivated before Withdrawn state existed.",
	)
	frappe.db.commit()
	print(f"Withdrew {count} stale Pending rows on inactive HR Policies.")
