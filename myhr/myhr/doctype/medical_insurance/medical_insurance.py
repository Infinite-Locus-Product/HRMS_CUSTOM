# Copyright (c) 2026, Abhay Nain and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class MedicalInsurance(Document):
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
