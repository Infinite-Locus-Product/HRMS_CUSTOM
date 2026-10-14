# Copyright (c) 2026, Fixxly and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class SeparationITAsset(Document):
	"""One hardware item on an IT clearance.

	The spec lists Hardware Returned as a multi-checkbox and Asset Condition as
	a single dropdown, but also requires that EVERY ticked item carries its own
	condition. One dropdown cannot express that, so condition — and the recovery
	amount that follows from it — live per row.
	"""

	pass
