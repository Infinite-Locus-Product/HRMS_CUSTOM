"""One-shot seeder: create two demo HR Policies that apply to all employees.

Run via:
    bench --site erp.localhost execute myhr.seed_demo_policies.run

Idempotent — re-running will skip policies that already exist by policy_name.
"""
import frappe


DEMO_POLICIES = [
	{
		"policy_name": "Demo: Code of Conduct (Notification Test)",
		"category": "General",
		"description": (
			"<p>Demo policy seeded to verify PWA notifications. "
			"Acknowledge to clear from Policy Centre.</p>"
		),
		"mandatory_check_in_block": 0,
		"file_name": "demo_code_of_conduct.txt",
		"file_body": (
			"DEMO POLICY — CODE OF CONDUCT\n\n"
			"This is a demo policy used to verify the myHR PWA notification "
			"pipeline. Please acknowledge in Policy Centre.\n"
		),
	},
	{
		"policy_name": "Demo: Data Security (Notification Test)",
		"category": "General",
		"description": (
			"<p>Demo data-security policy seeded to verify PWA notifications "
			"and the Clear-all flow.</p>"
		),
		"mandatory_check_in_block": 0,
		"file_name": "demo_data_security.txt",
		"file_body": (
			"DEMO POLICY — DATA SECURITY\n\n"
			"This is a demo policy used to verify the myHR PWA notification "
			"pipeline (clear-all path).\n"
		),
	},
]


def _ensure_file(file_name: str, body: str) -> str:
	"""Create a public File doc once; return its file_url."""
	existing = frappe.db.get_value("File", {"file_name": file_name}, "file_url")
	if existing:
		return existing
	f = frappe.get_doc({
		"doctype": "File",
		"file_name": file_name,
		"is_private": 0,
		"content": body,
	}).insert(ignore_permissions=True)
	return f.file_url


def _seed_pwa_notification_for_pa(pa_name: str) -> bool:
	"""Mirror Notification Log into a PWA Notification so the myHR PWA's
	Notifications view (which queries PWA Notification, not Notification Log)
	actually shows the policy alert. Idempotent per (to_user, ref doc).
	"""
	pa = frappe.db.get_value(
		"Policy Acknowledgement", pa_name,
		["employee", "hr_policy", "policy_version"],
		as_dict=True,
	)
	if not pa:
		return False
	user = frappe.db.get_value("Employee", pa.employee, "user_id")
	if not user:
		return False
	if frappe.db.exists("PWA Notification", {
		"to_user": user,
		"reference_document_type": "Policy Acknowledgement",
		"reference_document_name": pa_name,
	}):
		return False
	policy_label = frappe.db.get_value("HR Policy", pa.hr_policy, "policy_name") or pa.hr_policy
	frappe.get_doc({
		"doctype": "PWA Notification",
		"to_user": user,
		"from_user": "Administrator",
		"message": f"<b>{policy_label}</b> (v{pa.policy_version}) needs your acknowledgement. Open Policy Centre.",
		"reference_document_type": "Policy Acknowledgement",
		"reference_document_name": pa_name,
		"read": 0,
	}).insert(ignore_permissions=True)
	return True


def run():
	created = []
	skipped = []
	# Track every policy this run touched (created or already-present), so we
	# can still backfill PWA Notifications on idempotent re-runs.
	target_policies = []
	for spec in DEMO_POLICIES:
		existing = frappe.db.get_value("HR Policy", {"policy_name": spec["policy_name"]}, "name")
		if existing:
			skipped.append(spec["policy_name"])
			target_policies.append(existing)
			continue
		file_url = _ensure_file(spec["file_name"], spec["file_body"])
		policy = frappe.get_doc({
			"doctype": "HR Policy",
			"policy_name": spec["policy_name"],
			"category": spec["category"],
			"is_active": 1,
			"applies_to_all_employees": 1,
			"mandatory_check_in_block": spec["mandatory_check_in_block"],
			"file": file_url,
			"description": spec["description"],
		}).insert(ignore_permissions=True)
		created.append(policy.name)
		target_policies.append(policy.name)

	# Mirror every Pending PA we just seeded into PWA Notification so the PWA
	# Notifications view actually shows them. Covers the gap that
	# myhr.policy_notifications only writes Notification Log (Frappe bell),
	# while the PWA reads from PWA Notification.
	pwa_seeded = 0
	pa_names = []
	if target_policies:
		pa_names = frappe.get_all(
			"Policy Acknowledgement",
			filters={"hr_policy": ["in", target_policies], "status": "Pending"},
			pluck="name",
		)
		for pa_name in pa_names:
			if _seed_pwa_notification_for_pa(pa_name):
				pwa_seeded += 1

	frappe.db.commit()

	# Report what landed.
	pa_total = frappe.db.count("Policy Acknowledgement", {
		"hr_policy": ["in", target_policies or [""]],
	})
	notif_total = frappe.db.count("Notification Log", {
		"document_type": "Policy Acknowledgement",
		"document_name": ["in", pa_names or [""]],
	})
	print(f"created={created}")
	print(f"skipped={skipped}")
	print(f"policy_acknowledgements_for_created={pa_total}")
	print(f"notification_logs_for_created={notif_total}")
	print(f"pwa_notifications_seeded={pwa_seeded}")
	return {
		"created": created,
		"skipped": skipped,
		"pa_count": pa_total,
		"notif_count": notif_total,
		"pwa_seeded": pwa_seeded,
	}
