"""Drop orphan Custom Fields + DocTypes + Property Setters left behind by the
Leave Policy auto-assign and Travel & Expense features.

Context: those features shipped via v1_23..v1_26 patches and the matching code
in setup.py + employee_hooks.py. On 2026-05-13 the feature code was reverted
off `main` (and `staging` after the 2026-05-14 merge), but Frappe doesn't
auto-drop the schema rows the patches created. Result: the PWA New Expense
Claim form still surfaces "Travel Request", "Request Cap Override", "Cap
Override Justification", and the HR Controls tab still shows the LP fields,
even though no code touches any of them.

This patch removes the dead schema. Idempotent.

KEEPING by design:
  - The 13 seeded Expense Claim Types (Air Travel, Calls, Food, ...) — these
    are the visible category list in the PWA chip picker and any existing
    Expense Claim rows reference them.

Numbering: v1_28 is the Shift Type EOD checkout patch; v1_29 is this cleanup.
"""

import frappe


# (DocType, fieldname) pairs created by the T&E feature. Field names verified
# against `tabCustom Field` rows that survived the 2026-05-13 code revert.
_TE_CUSTOM_FIELDS = [
	("Expense Claim", "custom_travel_request"),
	("Expense Claim", "custom_cap_override"),
	("Expense Claim", "custom_cap_override_justification"),
	("Expense Claim", "custom_total_cap_breach_amount"),
	("Expense Claim Detail", "custom_expense_city"),
	("Expense Claim Detail", "custom_is_personal_vehicle"),
	("Expense Claim Detail", "custom_kilometres"),
	("Expense Claim Detail", "custom_fuel_rate_applied"),
	("Expense Claim Detail", "custom_daily_cap_applied"),
	("Expense Claim Detail", "custom_overage_amount"),
	("Expense Claim Type", "custom_per_diem_basis"),
	("Employee Grade", "custom_per_km_fuel_rate"),
	("Employee Grade", "custom_default_air_class"),
	("HR Settings", "custom_te_policy_section"),
	("HR Settings", "custom_te_enforce_caps"),
	("HR Settings", "custom_te_enforce_fuel_rate"),
	("HR Settings", "custom_te_submission_window_days"),
	("HR Settings", "custom_te_block_late_submission"),
]

# Custom Fields created by the LP feature.
_LP_CUSTOM_FIELDS = [
	("Employee", "custom_leave_policy"),
	("Employee", "custom_leave_balance_html"),
]

# Orphan DocTypes (the underlying tables + JSON metadata + permissions).
_ORPHAN_DOCTYPES = ["Per Diem Cap Matrix", "City Tier"]

# Patches whose code no longer exists in the app — keep the migrate log clean.
_DEAD_PATCH_LOG = [
	"myhr.patches.v1_23_seed_city_tier",
	"myhr.patches.v1_24_seed_per_diem_caps",
	"myhr.patches.v1_25_seed_expense_claim_types",
	"myhr.patches.v1_26_backfill_employee_leave_policy",
]


def _drop_custom_field(doctype: str, fieldname: str) -> bool:
	cf_name = f"{doctype}-{fieldname}"
	if not frappe.db.exists("Custom Field", cf_name):
		return False
	# delete_doc cascades the DB column drop via Frappe's Custom Field
	# on_trash hook, and removes any Property Setter that references this
	# field (permlevel, options, etc.).
	frappe.delete_doc("Custom Field", cf_name, force=True, ignore_permissions=True)
	return True


def _drop_property_setters_for_fieldname(field_name: str) -> int:
	"""Some Property Setters survive the Custom Field delete (Frappe's cascade
	is field-name-keyed, but stale rows can linger from previous installs).
	Belt-and-braces scan."""
	rows = frappe.db.sql_list(
		"SELECT name FROM `tabProperty Setter` WHERE field_name = %s",
		(field_name,),
	)
	for name in rows:
		frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True)
	return len(rows)


def _drop_orphan_doctype(doctype: str) -> bool:
	if not frappe.db.exists("DocType", doctype):
		return False
	# Cancel-then-delete any submittable data rows first to avoid the
	# "cannot delete a DocType with linked data" guard. None of these are
	# submittable in practice but be defensive.
	if frappe.db.count(doctype):
		for n in frappe.db.sql_list(f"SELECT name FROM `tab{doctype}`"):
			try:
				frappe.delete_doc(doctype, n, force=True, ignore_permissions=True)
			except Exception:
				# Best-effort row delete; the doctype delete below will fail
				# loudly if rows survive, and that's the right signal.
				pass
	frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
	return True


def _drop_patch_log_row(patch: str) -> bool:
	name = frappe.db.get_value("Patch Log", {"patch": patch}, "name")
	if not name:
		return False
	frappe.delete_doc("Patch Log", name, force=True, ignore_permissions=True)
	return True


def execute():
	dropped_cf = []
	for dt, fn in _TE_CUSTOM_FIELDS + _LP_CUSTOM_FIELDS:
		if _drop_custom_field(dt, fn):
			dropped_cf.append(f"{dt}.{fn}")

	# Sweep any lingering Property Setter rows keyed on these field names.
	ps_swept = 0
	for _dt, fn in _TE_CUSTOM_FIELDS + _LP_CUSTOM_FIELDS:
		ps_swept += _drop_property_setters_for_fieldname(fn)

	dropped_dt = []
	for dt in _ORPHAN_DOCTYPES:
		if _drop_orphan_doctype(dt):
			dropped_dt.append(dt)

	dropped_pl = []
	for p in _DEAD_PATCH_LOG:
		if _drop_patch_log_row(p):
			dropped_pl.append(p)

	for dt in {dt for dt, _ in _TE_CUSTOM_FIELDS + _LP_CUSTOM_FIELDS}:
		frappe.clear_cache(doctype=dt)
	frappe.db.commit()

	print(f"v1_29: removed Custom Fields ({len(dropped_cf)}): {', '.join(dropped_cf) or '(none)'}")
	print(f"v1_29: swept Property Setter rows: {ps_swept}")
	print(f"v1_29: removed DocTypes ({len(dropped_dt)}): {', '.join(dropped_dt) or '(none)'}")
	print(f"v1_29: removed dead Patch Log entries ({len(dropped_pl)}): {', '.join(dropped_pl) or '(none)'}")
