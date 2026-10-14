"""HR Policy + Policy Acknowledgement lifecycle hooks.

Owns the rule-based scoping (`applies_to_all_employees` + filter tables) and the
versioning behaviour (file change → bump version → supersede old acknowledgements).
"""

import frappe


SCOPE_FILTERS = (
	# (table_field on HR Policy, child doctype, row link field, Employee attribute)
	("applicable_departments", "Policy Filter Department", "department", "department"),
	("applicable_designations", "Policy Filter Designation", "designation", "designation"),
	("applicable_branches", "Policy Filter Branch", "branch", "branch"),
	("applicable_employment_types", "Policy Filter Employment Type", "employment_type", "employment_type"),
	("applicable_employees", "Policy Filter Employee", "employee", "name"),
)


# ----- Shared query helper (C-8) ---------------------------------------------

def query_employee_pas(employee, *, statuses, blocking_only=False, fields=None):
	"""Single shared query for PA × HR Policy joins, used by every consumer
	(`policy_gate.get_blocking_policies`, `api.get_employee_policies`,
	`api.get_pending_policy_count`).

	- `statuses`: required iterable, e.g. `("Pending",)` or `("Pending","Acknowledged")`.
	- `blocking_only`: if True, also filter `mandatory_check_in_block=1`.
	- `fields`: optional override (default returns the rich projection).

	Always filters `hp.is_active = 1`. Withdrawn / Superseded rows are
	excluded unless explicitly listed in `statuses`.
	"""
	if not employee:
		return []
	if not statuses:
		return []

	default_fields = [
		"pa.name",
		"pa.hr_policy",
		"pa.policy_version",
		"pa.status",
		"pa.acknowledged_at",
		"hp.policy_name",
		"hp.file",
		"hp.category",
		"hp.mandatory_check_in_block",
		"hp.description",
	]
	field_list = fields or default_fields

	where = ["pa.employee = %s", "hp.is_active = 1", "pa.status IN %s"]
	params = [employee, tuple(statuses)]
	if blocking_only:
		where.append("hp.mandatory_check_in_block = 1")

	sql = (
		f"SELECT {', '.join(field_list)} "
		"FROM `tabPolicy Acknowledgement` pa "
		"INNER JOIN `tabHR Policy` hp ON hp.name = pa.hr_policy "
		f"WHERE {' AND '.join(where)} "
		"ORDER BY (pa.status = 'Pending') DESC, hp.policy_name ASC"
	)
	return frappe.db.sql(sql, params, as_dict=True)


def _load_policy_filters(policy_name):
	"""Read all five filter tables for a policy in one pass.

	Returns a dict keyed by `emp_attr` → set of allowed values. Used by
	`applies_to_employee` directly (single call) and by `_load_policy_filters_bulk`
	indirectly through caching for batch reconcile loops (closes C-9 perf gap).
	"""
	out = {}
	for _table_field, child_doctype, row_link_field, emp_attr in SCOPE_FILTERS:
		rows = frappe.get_all(
			child_doctype,
			filters={"parent": policy_name, "parenttype": "HR Policy"},
			fields=[row_link_field],
		)
		out[emp_attr] = {r.get(row_link_field) for r in rows if r.get(row_link_field)}
	return out


def applies_to_employee(policy_name, employee_name, *, _prefetch=None):
	"""Return True if `policy_name` applies to `employee_name` per scoping rules.

	Inactive policies and inactive employees never match. The optional
	`_prefetch` arg lets callers (e.g., `after_save_hr_policy` looping over a
	whole company) supply a pre-loaded `{emp_attr: set(values)}` filter map
	so we avoid five `frappe.get_all` round-trips per call (C-9).
	"""
	policy = frappe.db.get_value(
		"HR Policy", policy_name,
		["is_active", "applies_to_all_employees", "applicability_logic"],
		as_dict=True,
	)
	if not policy or not policy.is_active:
		return False
	if frappe.db.get_value("Employee", employee_name, "status") != "Active":
		return False
	if policy.applies_to_all_employees:
		return True

	emp = frappe.db.get_value(
		"Employee", employee_name,
		["name", "department", "designation", "branch", "employment_type"],
		as_dict=True,
	)
	if not emp:
		return False

	filters_by_attr = _prefetch if _prefetch is not None else _load_policy_filters(policy_name)

	# Each filter that HAS rows contributes a True/False match.
	# Empty filters don't contribute (they're not filters, just unused).
	matches = []
	for _table_field, _child_doctype, _row_link_field, emp_attr in SCOPE_FILTERS:
		allowed = filters_by_attr.get(emp_attr) or set()
		if not allowed:
			continue
		matches.append(emp.get(emp_attr) in allowed)

	if not matches:
		# applies_to_all=False but no filters defined → policy applies to nobody.
		return False

	logic = policy.applicability_logic or "OR"
	return all(matches) if logic == "AND" else any(matches)


def ensure_policy_acknowledgements_for_employee(employee_name):
	"""For every active HR Policy that applies, make sure the employee has a
	pending Acknowledgement at the policy's current version. Existing rows are
	left alone (acknowledgements preserve audit history).

	Newly-created Pending rows fire a `Notification Log` entry to the
	employee's user (E-1) so they are not surprised by a silent block at 9am.
	"""
	from myhr.policy_notifications import notify_employee_of_new_pending

	if frappe.db.get_value("Employee", employee_name, "status") != "Active":
		return

	for policy in frappe.get_all("HR Policy", filters={"is_active": 1}, fields=["name", "version"]):
		if not applies_to_employee(policy.name, employee_name):
			continue
		current_version = policy.version or 1
		existing = frappe.db.exists(
			"Policy Acknowledgement",
			{"employee": employee_name, "hr_policy": policy.name, "policy_version": current_version},
		)
		if existing:
			continue
		new_pa = frappe.get_doc({
			"doctype": "Policy Acknowledgement",
			"employee": employee_name,
			"hr_policy": policy.name,
			"policy_version": current_version,
			"status": "Pending",
		}).insert(ignore_permissions=True)
		notify_employee_of_new_pending(new_pa.name)


# ----- Employee event handlers (delegated from employee_hooks) ----------------

def reconcile_after_employee_insert(doc, method):
	"""On Employee insert, attach all currently-applicable policies as Pending."""
	ensure_policy_acknowledgements_for_employee(doc.name)


def reconcile_on_employee_update(doc, method):
	"""On Employee update, re-evaluate applicability when scope-relevant fields change.

	Newly-applicable policies get fresh Pending rows. Existing acknowledgements
	stay (audit). Newly *non*-applicable policies do NOT get their rows wiped —
	the historical fact that the employee acknowledged remains true.
	"""
	if doc.is_new():
		return  # after_insert handler covers this
	scope_fields = {"status", "department", "designation", "branch", "employment_type"}
	if not any(doc.has_value_changed(f) for f in scope_fields):
		return
	ensure_policy_acknowledgements_for_employee(doc.name)


# ----- HR Policy event handlers ----------------------------------------------

def validate_hr_policy(doc, method):
	"""Bump `version` when the policy file changes, and refuse mutation of frozen fields.

	The validate fires before save; we set the new version here so the persisted
	row reflects it. Supersession of old Acknowledgement rows happens in
	`after_save_hr_policy` once the file change is committed.
	"""
	if doc.is_new():
		if not doc.version:
			doc.version = 1
		return
	if doc.has_value_changed("file"):
		doc.version = (doc.version or 1) + 1


def after_save_hr_policy(doc, method):
	"""After save, propagate version bumps and applicability changes.

	Order is deliberately:
	  1. Seed new Pending rows at the current version (only when the policy is
	     active). This must happen BEFORE we mark old rows Superseded so the
	     `superseded_by` JOIN can link old → new.
	  2. Mark all rows at older versions as Superseded (logged via the
	     canonical SQL helper so the audit trail captures the bypass path).
	  3. Backfill `superseded_by` on those Superseded rows to point at the new
	     row when one exists for the same (employee, policy). Employees who
	     fell out of scope at the new version get Superseded with a NULL
	     `superseded_by` — there is no replacement row to link.
	  4. If the policy just became inactive, transition all currently-Pending
	     rows to Withdrawn so the PWA stops showing them as actionable
	     (E-4 — closes the dead-policy ghost issue).
	"""
	from myhr.policy_audit import transition_pa_via_sql
	from myhr.policy_notifications import notify_employee_of_new_pending

	current_version = doc.version or 1

	# 1. Inactive → skip seeding (existing rows preserved, no new ones added).
	if doc.is_active:
		# Prefetch filter rows once (C-9): avoids 5 child-table queries per
		# employee in the loop below. For an org with 1000 employees and a
		# fully-scoped policy, this drops the seed pass from O(5 * 1000) DB
		# calls to O(5 + 1000).
		prefetch = _load_policy_filters(doc.name)
		for emp_name in frappe.get_all("Employee", filters={"status": "Active"}, pluck="name"):
			if not applies_to_employee(doc.name, emp_name, _prefetch=prefetch):
				continue
			exists = frappe.db.exists(
				"Policy Acknowledgement",
				{"employee": emp_name, "hr_policy": doc.name, "policy_version": current_version},
			)
			if exists:
				continue
			new_pa = frappe.get_doc({
				"doctype": "Policy Acknowledgement",
				"employee": emp_name,
				"hr_policy": doc.name,
				"policy_version": current_version,
				"status": "Pending",
			}).insert(ignore_permissions=True)
			notify_employee_of_new_pending(new_pa.name)

	# 2. Supersede + 3. wire superseded_by — only if a new version was minted.
	if current_version > 1:
		# Snapshot the old rows BEFORE flipping their status, so the canonical
		# helper can capture the from_status correctly.
		old_pa_names = frappe.db.sql_list(
			"""
			SELECT name FROM `tabPolicy Acknowledgement`
			WHERE hr_policy = %(p)s
			  AND policy_version < %(v)s
			  AND status IN ('Pending', 'Acknowledged')
			""",
			{"p": doc.name, "v": current_version},
		)
		if old_pa_names:
			transition_pa_via_sql(old_pa_names, "Superseded", via="VersionBump",
				note=f"Auto-superseded by version {current_version} of {doc.name}")

		# Wire `superseded_by` where a new row exists at the current version.
		# JOIN-based UPDATE — touches no audit-relevant fields, so no log entry.
		frappe.db.sql(
			"""
			UPDATE `tabPolicy Acknowledgement` old_pa
			INNER JOIN `tabPolicy Acknowledgement` new_pa
			    ON new_pa.employee       = old_pa.employee
			   AND new_pa.hr_policy       = old_pa.hr_policy
			   AND new_pa.policy_version  = %(v)s
			SET old_pa.superseded_by = new_pa.name
			WHERE old_pa.hr_policy = %(p)s
			  AND old_pa.policy_version < %(v)s
			  AND old_pa.status = 'Superseded'
			  AND old_pa.superseded_by IS NULL
			""",
			{"p": doc.name, "v": current_version},
		)

	# 4. Deactivate → Withdraw any still-Pending rows (E-4).
	#    is_active flipped 1 → 0 OR it was 0 on insert with seeded Pendings.
	#    Both lead to the same no-op-or-change path.
	if not doc.is_active:
		pending_names = frappe.db.sql_list(
			"""
			SELECT name FROM `tabPolicy Acknowledgement`
			WHERE hr_policy = %(p)s AND status = 'Pending'
			""",
			{"p": doc.name},
		)
		if pending_names:
			transition_pa_via_sql(pending_names, "Withdrawn", via="Deactivate",
				note=f"HR Policy {doc.name} deactivated; Pending acknowledgements withdrawn.")


def on_trash_hr_policy(doc, method):
	"""Block all deletion of HR Policies. Use the `is_active` flag to retire instead."""
	frappe.throw(
		"HR Policies cannot be deleted (acknowledgements depend on this row for audit). "
		"Uncheck <b>Active</b> to retire the policy instead — existing acknowledgements stay intact, "
		"and new employees won't be assigned this policy."
	)
