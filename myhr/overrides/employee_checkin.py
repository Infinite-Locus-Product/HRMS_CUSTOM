"""myHR overrides for Employee Checkin.

This file is the single place that orchestrates the order of validations
for Employee Checkin saves:

    1. _guard_reserved_device_id              — block non-cron callers from spoofing device_id
    2. _guard_backdating                      — non-HR users can't set time too far in the past
    3. ownership_gate.assert_self_or_hr       — non-HR users can only checkin for themselves
    4. policy_gate.assert_policies_acknowledged — mandatory HR policies must be Acknowledged
    5. _guard_minute_dedup                    — same employee + log_type within 60s blocks
    6. super().validate()                     — stock HRMS validations
        ├ validate_active_employee
        ├ validate_duplicate_log
        ├ validate_time_change
        ├ fetch_shift
        ├ set_geolocation                     — captures lat/long onto the doc
        └ validate_distance_from_shift_location  — overridden below
            ├ if device_id == AUTO_PRESENT_DEVICE → return (cron, no GPS)
            ├ if allow_geolocation_tracking is off → return (site-wide off)
            ├ require lat/long  ← ALWAYS, even with bypass flag
            └ if Employee.custom_bypass_geolocation_check → return  (skip radius only)
              else → super (radius check)

Auto-present cron checkins (`device_id == AUTO_PRESENT_DEVICE`) skip the
ownership + policy + minute-dedup + backdate gates AND the geolocation
checks — they're system-driven.
"""

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, now_datetime

from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin as HRMSEmployeeCheckin

from myhr.employee_hooks import AUTO_PRESENT_DEVICE


# CHK-2: how far in the past a non-HR user is allowed to backdate `time`.
# 5 minutes covers clock-skew + slow PWA save without enabling abuse.
_BACKDATE_TOLERANCE_SECONDS = 5 * 60

# CHK-1: minute-level dedup window (seconds).
_DEDUP_WINDOW_SECONDS = 60


class EmployeeCheckin(HRMSEmployeeCheckin):
	def validate(self):
		"""Run myHR gates BEFORE stock HRMS validations.

		The user-facing rule is "policy first, then everything else": if an
		employee hasn't acknowledged their mandatory policies, they should be
		blocked at the gate without ever finding out their shift / lat /
		duplicate-log status.
		"""
		# CHK-5: must come first — checked even for the cron path so the cron
		# itself succeeds (Administrator) and so a spoofed device_id is caught
		# before any other gate is evaluated.
		self._guard_reserved_device_id()

		if self.device_id != AUTO_PRESENT_DEVICE and self.employee:
			from myhr.ownership_gate import assert_self_or_hr
			from myhr.policy_gate import assert_policies_acknowledged

			self._guard_backdating()
			assert_self_or_hr(self)
			assert_policies_acknowledged(self.employee, action_label="check in")
			self._guard_minute_dedup()

		super().validate()

	# ----- CHK-5: device_id spoof guard ------------------------------------
	def _guard_reserved_device_id(self):
		"""Block non-cron / non-HR callers from setting `device_id` to the
		reserved AUTO_PRESENT_DEVICE string. Otherwise an API caller could
		spoof the cron path and bypass every myhr gate.

		Allowed setters:
		  - Administrator (the cron runs as Administrator)
		  - HR Manager / System Manager (manual maintenance)
		"""
		if self.device_id != AUTO_PRESENT_DEVICE:
			return
		user = frappe.session.user
		if user == "Administrator":
			return
		roles = set(frappe.get_roles(user))
		if {"HR Manager", "System Manager"} & roles:
			return
		frappe.throw(
			_("`device_id` value <b>{0}</b> is reserved for the auto-present cron and cannot be set by non-HR users.").format(AUTO_PRESENT_DEVICE),
			frappe.PermissionError,
		)

	# ----- CHK-2: backdate guard -------------------------------------------
	def _guard_backdating(self):
		"""Non-HR users cannot set `time` further into the past than the
		tolerance window. Future timestamps are allowed within the same
		tolerance (clock skew). HR Manager / System Manager are exempt
		because they may post-correct attendance for legitimate reasons.
		"""
		if not self.time:
			return
		roles = set(frappe.get_roles(frappe.session.user))
		if {"HR Manager", "System Manager"} & roles:
			return
		if frappe.session.user == "Administrator":
			return

		t = get_datetime(self.time)
		now = now_datetime()
		drift = (now - t).total_seconds()
		if drift > _BACKDATE_TOLERANCE_SECONDS:
			frappe.throw(
				_("Cannot record a check-in more than {0} minutes in the past. Contact HR for back-dated entries.").format(
					_BACKDATE_TOLERANCE_SECONDS // 60,
				),
				title=_("Back-dated check-in"),
			)
		if -drift > _BACKDATE_TOLERANCE_SECONDS:
			frappe.throw(
				_("Cannot record a check-in more than {0} minutes in the future.").format(
					_BACKDATE_TOLERANCE_SECONDS // 60,
				),
				title=_("Future-dated check-in"),
			)

	# ----- CHK-1: minute-level dedup ---------------------------------------
	def _guard_minute_dedup(self):
		"""Throw if the same employee + log_type already has a check-in within
		`_DEDUP_WINDOW_SECONDS` of the requested time. Stock HRMS's
		`validate_duplicate_log` only catches exact-same time; this catches
		the common double-tap / slow-network double-submit pattern."""
		if not (self.employee and self.time and self.log_type):
			return
		t = get_datetime(self.time)
		# Stock validate_duplicate_log catches exact-time dupes; we look for
		# anything within the window EXCLUDING our own row (re-saves).
		existing = frappe.db.sql(
			"""
			SELECT name, time
			FROM `tabEmployee Checkin`
			WHERE employee = %(e)s
			  AND log_type = %(l)s
			  AND name != %(n)s
			  AND ABS(TIMESTAMPDIFF(SECOND, time, %(t)s)) < %(w)s
			LIMIT 1
			""",
			{
				"e": self.employee,
				"l": self.log_type,
				"n": self.name or "",
				"t": t,
				"w": _DEDUP_WINDOW_SECONDS,
			},
			as_dict=True,
		)
		if existing:
			frappe.throw(
				_("A {0} check-in for {1} was already recorded within the last minute (at {2}). Please wait before retrying.").format(
					self.log_type, self.employee, existing[0].time,
				),
				title=_("Duplicate check-in"),
			)

	# ----- Stock geo override (unchanged) ----------------------------------
	def validate_distance_from_shift_location(self):
		"""Override the stock geo check.

		Auto-present cron checkins skip entirely (no GPS captured).
		Otherwise: lat/long is REQUIRED so the location is logged for audit.
		Bypass flag short-circuits only the radius enforcement, not the
		lat/long capture.
		"""
		# 1. Cron path — system writes, no GPS.
		if self.device_id == AUTO_PRESENT_DEVICE:
			return

		# 2. Geolocation tracking off site-wide → stock does nothing either.
		if not frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"):
			return

		# 3. Lat/long is REQUIRED for any human check-in (even bypass=1
		#    employees) so we keep an audit trail of where they checked in.
		if not (self.latitude or self.longitude):
			frappe.throw(_("Latitude and longitude values are required for checking in."))

		# 4. Bypass flag → skip radius enforcement, but the lat/long was
		#    already captured by `set_geolocation()` and required above.
		if self._myhr_should_bypass_geolocation():
			return

		# 5. Standard radius check.
		return super().validate_distance_from_shift_location()

	def _myhr_should_bypass_geolocation(self) -> bool:
		if not self.employee:
			return False
		bypass_enabled = frappe.db.get_value(
			"Employee", self.employee, "custom_bypass_geolocation_check"
		)
		return cint(bypass_enabled) == 1
