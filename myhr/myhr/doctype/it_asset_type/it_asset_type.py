# Copyright (c) 2026, Fixxly and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ITAssetType(Document):
	"""Master list of hardware IT collects back from a leaver.

	Editable by HR/IT so a new asset type needs no schema change. Retire with
	`is_active = 0` rather than deleting — deleting orphans the rows on
	historical clearances.
	"""

	pass
