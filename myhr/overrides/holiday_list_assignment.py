import frappe


def on_submit(doc, method=None):
    """
    When a Holiday List Assignment is submitted for an Employee, mirror the
    holiday_list back onto that Employee's Overview proxy field (and the
    native holiday_list) so the form reflects the current active assignment.

    We use frappe.db.set_value so Employee validate/on_update do NOT fire —
    that avoids the sync loop where Employee.on_update would try to cancel
    the HLA we just submitted.
    """
    if doc.applicable_for != "Employee":
        return
    if not doc.assigned_to or not doc.holiday_list:
        return

    current = frappe.db.get_value(
        "Employee", doc.assigned_to, "custom_holiday_list"
    )
    if current == doc.holiday_list:
        return

    frappe.db.set_value(
        "Employee",
        doc.assigned_to,
        {
            "custom_holiday_list": doc.holiday_list,
            "holiday_list": doc.holiday_list,
        },
        update_modified=False,
    )
