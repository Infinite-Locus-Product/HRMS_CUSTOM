# Copyright (c) 2026, Fixxly and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class AccessRevocationSystem(Document):
	"""Master list of systems a leaver's access must be revoked from.

	Editable by HR so a new system can be added without a schema change. Rows
	are referenced by `Separation Manager Clearance`, so retire a system with
	`is_active = 0` rather than deleting it — deleting would orphan the child
	rows on historical clearances.
	"""

	pass
