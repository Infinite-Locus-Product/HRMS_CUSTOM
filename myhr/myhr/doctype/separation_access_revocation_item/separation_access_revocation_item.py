# Copyright (c) 2026, Fixxly and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SeparationAccessRevocationItem(Document):
	"""One selected system on a clearance's Project Access Revocation field.

	A Table MultiSelect needs a child doctype carrying exactly one Link field;
	this is that child.
	"""

	pass
