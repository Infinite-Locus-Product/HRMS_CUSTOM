# Copyright (c) 2026, Abhay Nain and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class MedicalInsuranceOptOutDeclaration(Document):
    def validate(self):
        self._validate_date_range()

    def _validate_date_range(self):
        if self.effective_from and self.effective_to:
            if getdate(self.effective_from) > getdate(self.effective_to):
                frappe.throw(
                    _("Effective From ({0}) cannot be after Effective To ({1}).").format(
                        self.effective_from, self.effective_to
                    )
                )


def get_active_declaration():
    """Return the most recent Active opt-out declaration, or None.

    Used by the Action Centre API to surface the blank PDF to employees who
    pick 'Opt Out' on the medical insurance question.
    """
    name = frappe.db.get_value(
        "Medical Insurance Opt Out Declaration",
        {"is_active": 1},
        "name",
        order_by="modified desc",
    )
    if not name:
        return None
    return frappe.db.get_value(
        "Medical Insurance Opt Out Declaration",
        name,
        ["name", "declaration_name", "template_document"],
        as_dict=True,
    )
