"""Canonical transition + audit infrastructure for Policy Acknowledgement.

Every status flip on a `Policy Acknowledgement` row should produce a row in
`Policy Audit Log`. Two paths feed the log:

1. **ORM saves** — `PolicyAcknowledgement.after_insert` and `.on_update` call
   `write_audit_log_for_change(...)` with `via="ORM"`.

2. **SQL bypass paths** (`after_save_hr_policy` supersede UPDATE, the
   deactivate-policy → Withdrawn UPDATE) — these go through
   `transition_pa_via_sql(...)` which performs the UPDATE *and* writes a log
   row in the same transaction. The state machine in `validate()` doesn't
   fire here, so the helper is the only thing keeping the audit honest.

If you find yourself reaching for raw `frappe.db.sql("UPDATE ... SET status =
... ")` on `Policy Acknowledgement`, route it through `transition_pa_via_sql`
instead.
"""
import frappe


_VALID_VIA = {"ORM", "API", "SQL", "Migration", "Reconcile", "BulkAck", "Deactivate", "VersionBump"}


def write_audit_log_for_change(pa_name, from_status, to_status, *, via, note=None):
	"""Insert a Policy Audit Log row for a single transition.

	`from_status` is `None` for fresh inserts. `via` must be one of the
	allow-listed values (matches the doctype Select options).
	"""
	if via not in _VALID_VIA:
		frappe.throw(f"Invalid `via` value for Policy Audit Log: {via!r}")

	pa = frappe.db.get_value(
		"Policy Acknowledgement", pa_name,
		["employee", "hr_policy", "policy_version"],
		as_dict=True,
	)
	if not pa:
		# PA was deleted before the log could be written. Nothing to record.
		return

	frappe.get_doc({
		"doctype": "Policy Audit Log",
		"policy_acknowledgement": pa_name,
		"employee": pa.employee,
		"hr_policy": pa.hr_policy,
		"policy_version": pa.policy_version,
		"from_status": from_status or "",
		"to_status": to_status,
		"via": via,
		"actor": frappe.session.user if hasattr(frappe, "session") else "Administrator",
		"actor_ip": getattr(frappe.local, "request_ip", None) or "",
		"note": note or "",
	}).insert(ignore_permissions=True)


def transition_pa_via_sql(pa_names, target_status, *, via, note=None):
	"""Bulk-transition rows via SQL UPDATE *and* write audit log entries.

	`pa_names` may be an iterable of names or a single name. Each row that
	actually changed status gets a log entry. Rows that already sit at
	`target_status` are no-ops (no UPDATE, no log).

	Returns the count of rows actually transitioned.
	"""
	if isinstance(pa_names, str):
		pa_names = [pa_names]
	pa_names = list(pa_names)
	if not pa_names:
		return 0

	# Snapshot prior status for log writing.
	rows = frappe.db.sql(
		"""
		SELECT name, status
		FROM `tabPolicy Acknowledgement`
		WHERE name IN %(n)s
		""",
		{"n": tuple(pa_names)},
		as_dict=True,
	)
	to_change = [r for r in rows if r.status != target_status]
	if not to_change:
		return 0

	frappe.db.sql(
		"""
		UPDATE `tabPolicy Acknowledgement`
		SET status = %(s)s, modified = NOW(), modified_by = %(u)s
		WHERE name IN %(n)s
		""",
		{
			"s": target_status,
			"n": tuple(r.name for r in to_change),
			"u": frappe.session.user if hasattr(frappe, "session") else "Administrator",
		},
	)
	for r in to_change:
		write_audit_log_for_change(r.name, r.status, target_status, via=via, note=note)
	return len(to_change)
