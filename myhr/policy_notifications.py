"""Notification surfaces for Policy Acknowledgement.

E-1: When a Pending row is seeded (via `ensure_policy_acknowledgements_for_employee`,
     `after_save_hr_policy`, or any other path that creates a Pending PA),
     fire a `Notification Log` row for the employee's user, with stronger
     copy + a "Required for Check-in" badge for mandatory-block policies.

E-3: A scheduled cron (`send_pending_policy_reminders`) finds Pending
     mandatory rows older than `REMINDER_AGE_HOURS` and re-pings the user.
     De-duplicated by checking whether a reminder Notification Log was
     already created in the same cycle — the `subject` is namespaced so we
     can grep our own prior pings cleanly.
"""
import frappe
from frappe.utils import now_datetime, add_to_date


REMINDER_AGE_HOURS = 24
REMINDER_RE_PING_HOURS = 24
NOTIFICATION_SUBJECT_PREFIX = "[myHR Policy]"


def _employee_user(employee):
	return frappe.db.get_value("Employee", employee, "user_id")


def notify_employee_of_new_pending(pa_name):
	"""Fire a single Notification Log entry telling the employee they have a
	new Pending policy. Called from `ensure_policy_acknowledgements_for_employee`
	right after each `insert`, AND from the `Policy Acknowledgement.after_insert`
	doc_event so direct PA creation (Desk form / API) also notifies.

	Idempotent — if a Notification Log already exists for this PA + user, it's a
	no-op so the two callers can't double-notify. Best-effort — exceptions are
	logged, never raised (notification failure must not block PA seeding)."""
	try:
		pa = frappe.db.get_value(
			"Policy Acknowledgement", pa_name,
			["employee", "hr_policy", "policy_version", "status"],
			as_dict=True,
		)
		if not pa or pa.status != "Pending":
			return
		hp = frappe.db.get_value(
			"HR Policy", pa.hr_policy,
			["policy_name", "mandatory_check_in_block", "is_active"],
			as_dict=True,
		)
		if not hp or not hp.is_active:
			return
		user = _employee_user(pa.employee)
		if not user:
			return

		# Idempotence: skip if we already notified this user for this PA.
		# Keyed on (document_type, document_name, for_user) — the only triple
		# guaranteed unique per assignment notification.
		if frappe.db.exists("Notification Log", {
			"document_type": "Policy Acknowledgement",
			"document_name": pa_name,
			"for_user": user,
		}):
			return

		mandatory = bool(hp.mandatory_check_in_block)
		mandatory_tag = " [Required for Check-in]" if mandatory else ""
		subject = f"{NOTIFICATION_SUBJECT_PREFIX}{mandatory_tag} {hp.policy_name}: action required"
		body = (
			f"<p>{hp.policy_name} (v{pa.policy_version}) needs your acknowledgement.</p>"
			+ (f"<p><b>You will not be able to check in until you acknowledge this policy.</b></p>" if mandatory else "")
			+ "<p>Open <b>Policy Centre</b> in the myHR PWA to review and acknowledge.</p>"
		)
		frappe.get_doc({
			"doctype": "Notification Log",
			"for_user": user,
			"type": "Alert",
			"subject": subject,
			"email_content": body,
			"document_type": "Policy Acknowledgement",
			"document_name": pa_name,
			"from_user": "Administrator",
		}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(
			title="myHR notify_employee_of_new_pending failed",
			message=frappe.get_traceback(),
		)


def notify_on_pa_creation(doc, method=None):
	"""doc_event hook bound to `Policy Acknowledgement.after_insert` so any path
	that creates a PA (Desk form, API, script, bulk import) ends up notifying
	the employee — not just the seeding helper. Idempotent via
	`notify_employee_of_new_pending`'s dedupe check."""
	if doc and getattr(doc, "status", "") == "Pending":
		notify_employee_of_new_pending(doc.name)


def send_pending_policy_reminders():
	"""Hourly cron — re-ping employees with Pending mandatory PAs older than
	REMINDER_AGE_HOURS. De-duplicated against the user's recent Notification
	Log entries so we don't spam every hour.

	Wired in `hooks.py → scheduler_events.cron`.
	"""
	cutoff = add_to_date(now_datetime(), hours=-REMINDER_AGE_HOURS)
	stale = frappe.db.sql(
		"""
		SELECT pa.name, pa.employee, pa.hr_policy, pa.policy_version,
		       hp.policy_name, hp.mandatory_check_in_block
		FROM `tabPolicy Acknowledgement` pa
		INNER JOIN `tabHR Policy` hp ON hp.name = pa.hr_policy
		WHERE pa.status = 'Pending'
		  AND hp.is_active = 1
		  AND hp.mandatory_check_in_block = 1
		  AND pa.creation < %(cutoff)s
		""",
		{"cutoff": cutoff},
		as_dict=True,
	)
	if not stale:
		return {"sent": 0, "skipped": 0, "reason": "nothing_stale"}

	repump_cutoff = add_to_date(now_datetime(), hours=-REMINDER_RE_PING_HOURS)
	sent = skipped = errors = 0
	for r in stale:
		try:
			user = _employee_user(r.employee)
			if not user:
				skipped += 1
				continue
			# De-dupe: did we already ping this user about THIS PA in the last
			# REMINDER_RE_PING_HOURS hours?
			recent = frappe.db.exists(
				"Notification Log",
				{
					"for_user": user,
					"document_name": r.name,
					"creation": (">", repump_cutoff),
				},
			)
			if recent:
				skipped += 1
				continue
			subject = f"{NOTIFICATION_SUBJECT_PREFIX} REMINDER [Required for Check-in] {r.policy_name}"
			body = (
				f"<p><b>You still need to acknowledge {r.policy_name} (v{r.policy_version}).</b></p>"
				"<p>Until you do, you cannot record attendance via Employee Check-in or Attendance Request.</p>"
				"<p>Open <b>Policy Centre</b> in the myHR PWA.</p>"
			)
			frappe.get_doc({
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"subject": subject,
				"email_content": body,
				"document_type": "Policy Acknowledgement",
				"document_name": r.name,
				"from_user": "Administrator",
			}).insert(ignore_permissions=True)
			sent += 1
		except Exception:
			errors += 1
			frappe.log_error(
				title="myHR send_pending_policy_reminders row failed",
				message=frappe.get_traceback(),
			)
	frappe.db.commit()
	return {"sent": sent, "skipped": skipped, "errors": errors, "stale_total": len(stale)}
