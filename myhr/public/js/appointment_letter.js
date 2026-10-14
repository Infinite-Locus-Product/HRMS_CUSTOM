// Appointment Letter — link the accepted Job Offer (custom_job_offer, declared in
// fixtures/custom_field.json). The print format reads designation, CTC, salary
// annexure, and the Location / Work Arrangement offer terms from that offer.
frappe.ui.form.on("Appointment Letter", {
	setup(frm) {
		frm.set_query("custom_job_offer", () => ({
			filters: frm.doc.job_applicant ? { job_applicant: frm.doc.job_applicant } : {},
		}));
	},

	job_applicant(frm) {
		if (!frm.doc.job_applicant) {
			frm.set_value("custom_job_offer", null);
			return;
		}
		// Preselect the latest Accepted offer; HR can still change it.
		frappe.db
			.get_list("Job Offer", {
				filters: { job_applicant: frm.doc.job_applicant, status: "Accepted", docstatus: ["<", 2] },
				fields: ["name"],
				order_by: "offer_date desc, creation desc",
				limit: 1,
			})
			.then((rows) => {
				frm.set_value("custom_job_offer", rows.length ? rows[0].name : null);
			});
	},
});
