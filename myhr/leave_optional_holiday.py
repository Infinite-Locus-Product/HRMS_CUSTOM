"""Optional leave: dates must be on Employee's Holiday List with Holiday Type = Optional.

Also home of the `Holiday` doc_event validator that keeps `custom_holiday_type`
in sync with `weekly_off`. Without this, HR list-builders that set
`weekly_off=1` (the standard "auto-fill weekly offs" pattern in Frappe) leave
`custom_holiday_type` as Optional or blank — which silently breaks the
optional-leave gate (Sundays would be acceptable optional leave dates).
"""

import frappe
from frappe import _
from frappe.utils import add_days, formatdate, getdate

from hrms.hr.doctype.leave_application.leave_application import NotAnOptionalHoliday


def _normalize_holiday_row(row):
	"""Apply the HOL-1/2/3 sync rules to a single Holiday row in-place.

	Rules:
	  - `weekly_off=1` → force `custom_holiday_type='Weekly Off'` (overrides any
	    other value, fixing the common HR-builder mistake of leaving the type
	    as 'Optional' on Sunday auto-fills).
	  - `weekly_off=0` and `custom_holiday_type` blank → default to 'Fixed'
	    (the conservative choice; HR can flip to 'Optional' explicitly when
	    publishing optional-leave dates).
	  - `weekly_off=0` and `custom_holiday_type='Weekly Off'` → throw; that's
	    a contradiction.
	"""
	wo = bool(row.get("weekly_off"))
	current = row.get("custom_holiday_type") or ""

	if wo:
		if current != "Weekly Off":
			row.custom_holiday_type = "Weekly Off"
		return

	if current == "Weekly Off":
		frappe.throw(
			_("Holiday {0}: Holiday Type cannot be 'Weekly Off' on a non-weekly-off date. "
			  "Set the Weekly Off flag, or change Holiday Type to Optional or Fixed.").format(
				formatdate(row.holiday_date) if row.get("holiday_date") else ""
			),
			title=_("Holiday Type / Weekly Off mismatch"),
		)
	if not current:
		row.custom_holiday_type = "Fixed"


def validate_holiday(doc, method=None):
	"""Holiday `validate` hook (covers standalone Holiday saves, rare path)."""
	_normalize_holiday_row(doc)


def validate_holiday_list(doc, method=None):
	"""Holiday List `validate` hook (HOL-1/2/3): runs the row-normalize on
	every child row. This is the path that actually fires reliably — child
	doctype `validate` doc_events don't always fire for table-doctype rows;
	the parent's validate is the dependable hook surface.
	"""
	for row in (doc.holidays or []):
		_normalize_holiday_row(row)


def validate_optional_leave_dates(employee: str, from_date, to_date) -> None:
	"""
	Inputs: employee id, from_date, to_date (date or str).
	Side effects: frappe.throw on validation failure.
	Requires Employee.holiday_list; each day in range must exist on that list with custom_holiday_type = Optional.

	Phase 2 (LA-6): all holidays in the [from, to] range are fetched in one
	query rather than one query per day. For a 30-day leave the old code
	issued 30 round-trips; this is a single round-trip + in-memory dict lookup.
	"""
	if not employee:
		frappe.throw(_("Employee is required."))

	holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
	if not holiday_list:
		frappe.throw(
			_("Please set Holiday List on the Employee record before applying for optional leave."),
			title=_("Holiday List missing"),
		)

	from_d = getdate(from_date)
	to_d = getdate(to_date)
	if from_d > to_d:
		frappe.throw(
			_("`From` date ({0}) cannot be after `To` date ({1}).").format(formatdate(from_d), formatdate(to_d)),
			title=_("Invalid date range"),
		)

	# Single batched query: fetch every Holiday row in the range for this list.
	rows = frappe.get_all(
		"Holiday",
		filters={"parent": holiday_list, "holiday_date": ("between", [from_d, to_d])},
		fields=["holiday_date", "custom_holiday_type"],
	)
	by_date = {getdate(r.holiday_date): (r.get("custom_holiday_type") or "") for r in rows}

	day = from_d
	while day <= to_d:
		holiday_type = by_date.get(day)
		if holiday_type is None:
			frappe.throw(
				_("{0} is not in your Holiday List").format(formatdate(day)),
				NotAnOptionalHoliday,
			)

		if holiday_type == "":
			frappe.throw(
				_(
					"{0}: Holiday Type is not set on the Holiday List. Set it to Optional, Fixed, or Weekly Off."
				).format(formatdate(day)),
				title=_("Holiday type required"),
			)

		if holiday_type == "Fixed":
			frappe.throw(
				_("{0} is a fixed company holiday; optional leave cannot be applied on this date.").format(
					formatdate(day)
				),
				title=_("Fixed holiday"),
			)

		if holiday_type == "Weekly Off":
			frappe.throw(
				_("{0} is a weekly off; optional leave cannot be applied on this date.").format(
					formatdate(day)
				),
				title=_("Weekly off"),
			)

		if holiday_type != "Optional":
			frappe.throw(
				_("{0}: unsupported Holiday Type {1}").format(formatdate(day), holiday_type),
				title=_("Optional leave"),
			)

		day = add_days(day, 1)
