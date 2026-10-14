# Copyright (c) 2026, Fixxly and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SeparationHandoverDocument(Document):
	"""One handover item: a file, a link, or a note.

	The spec asks for "KT docs, project links, or handover notes", so a row is
	valid with any one of the three. The parent's validate enforces that a row
	is not entirely empty.
	"""

	pass
