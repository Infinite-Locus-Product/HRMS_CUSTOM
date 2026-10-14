"""One-shot seeder: drop a variety of unread PWA Notifications onto every
active employee so the PWA Notifications view has enough rows to exercise
tick / cross / mark-all-read / clear-all.

Run via:
    bench --site erp.localhost execute myhr.seed_demo_notifications.run

Each employee gets one of every flavour. Re-running adds a fresh batch
(rows are not deduped — you want fresh test data on each run).
"""
import frappe
from frappe import bold
from frappe.utils import add_to_date, now_datetime


# (message, reference_document_type) — reference_document_type maps into the
# REFERENCE_TYPE_ROUTES table in Notifications.vue, so tapping the row
# navigates to the right section. Empty type = stay on /notifications.
DEMO_NOTIFICATIONS = [
	(
		f"{bold('Welcome to myHR')} — your dashboard is ready. Start with the Home tab.",
		None,
	),
	(
		f"{bold('Reminder')}: please complete your Code of Conduct acknowledgement.",
		"Policy Acknowledgement",
	),
	(
		f"{bold('Holiday list updated')} for the next quarter — review under Leaves.",
		"Leave Application",
	),
	(
		f"{bold('New Expense Claim policy')} effective from next month — cap raised to ₹5,000.",
		"Expense Claim",
	),
	(
		f"{bold('Attendance reminder')}: don't forget to mark your check-in today.",
		"Attendance Request",
	),
]


def run(target_user: str | None = None):
	"""Seed notifications.

	If `target_user` is provided, only that user gets the batch (handy when
	you're testing as one specific employee). Otherwise all active employees
	with a linked user_id get the batch.
	"""
	if target_user:
		users = [target_user]
	else:
		users = [
			r.user_id for r in frappe.get_all(
				"Employee",
				filters={"status": "Active", "user_id": ["is", "set"]},
				fields=["user_id"],
			)
			if r.user_id
		]

	if not users:
		print("No target users found.")
		return {"created": 0, "users": 0}

	created = 0
	now = now_datetime()
	for idx, user in enumerate(users):
		for offset, (message, ref_type) in enumerate(DEMO_NOTIFICATIONS):
			doc = frappe.get_doc({
				"doctype": "PWA Notification",
				"to_user": user,
				"from_user": "Administrator",
				"message": message,
				"reference_document_type": ref_type,
				"reference_document_name": None,
				"read": 0,
			})
			doc.insert(ignore_permissions=True)
			# Stagger creation timestamps so "X minutes ago" reads vary.
			frappe.db.set_value(
				"PWA Notification", doc.name, "creation",
				add_to_date(now, minutes=-(offset * 5 + idx)),
				update_modified=False,
			)
			created += 1

	frappe.db.commit()
	print(f"users={len(users)} notifications_created={created}")
	if target_user:
		print(f"target_user={target_user}")
	return {"users": len(users), "created": created}
