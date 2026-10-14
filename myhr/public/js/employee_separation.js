// Employee Separation — Stage A (resignation initiation) form behaviour.
//
// Reporting Manager and Function Head / L2 fill themselves via `fetch_from`,
// so nothing here touches them. This file only covers the two things
// fetch_from cannot do: defaulting the Requested Relieving Date from the
// notice-period policy, and showing the 500-char limit while the user types
// rather than throwing it at them on save.

const MAX_DETAILED_REASON_CHARS = 500;

function _prefill_relieving_date(frm) {
	// Never overwrite a date the user already chose, and never touch a
	// submitted document.
	if (!frm.doc.employee || frm.doc.custom_requested_relieving_date || frm.doc.docstatus !== 0) {
		return;
	}

	frappe
		.call({
			method: "myhr.employee_separation_hooks.get_relieving_date_default",
			args: { employee: frm.doc.employee },
		})
		.then((r) => {
			const official_end = r && r.message && r.message.official_end_date;
			if (official_end && !frm.doc.custom_requested_relieving_date) {
				frm.set_value("custom_requested_relieving_date", official_end);
			}
		});
}

function _update_reason_counter(frm) {
	const used = (frm.doc.custom_detailed_reason || "").length;
	const over = used > MAX_DETAILED_REASON_CHARS;
	frm.set_df_property(
		"custom_detailed_reason",
		"description",
		__("{0} / {1} characters{2}", [
			used,
			MAX_DETAILED_REASON_CHARS,
			over ? __(" — over the limit, this will be rejected on save") : "",
		]),
	);
}

frappe.ui.form.on("Employee Separation", {
	refresh(frm) {
		_update_reason_counter(frm);
	},

	employee(frm) {
		_prefill_relieving_date(frm);
	},

	custom_detailed_reason(frm) {
		_update_reason_counter(frm);
	},
});
