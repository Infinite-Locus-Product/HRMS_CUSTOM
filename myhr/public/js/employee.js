// Elixiir custom Attach fields must be PDF and <= 5 MB.
const PDF_ONLY_ATTACH_FIELDS = [
	"custom_pan_attachment",
	"custom_aadhar_attachment",
	"custom_highest_qualification_attachment",
	"custom_appointment_letter",
	"custom_resignation_email",
	"custom_relieving_letter",
	"custom_bank_statement_6m",
];
const MAX_ATTACH_BYTES = 5 * 1024 * 1024;

function _apply_pdf_restrictions(frm) {
	PDF_ONLY_ATTACH_FIELDS.forEach((fname) => {
		const ctl = frm.fields_dict[fname];
		if (!ctl || ctl._elixiir_patched) return;
		// Monkey-patch set_upload_options so restrictions apply every time
		// the attach dialog is opened — not just once at setup.
		const original = ctl.set_upload_options.bind(ctl);
		ctl.set_upload_options = function () {
			original();
			this.upload_options = Object.assign(this.upload_options || {}, {
				allow_take_photo: false,
				allow_web_link: false,
				allow_google_drive: false,
				restrictions: {
					allowed_file_types: [".pdf"],
					max_file_size: MAX_ATTACH_BYTES,
				},
			});
		};
		ctl._elixiir_patched = true;
	});
}

frappe.ui.form.on("Employee", {
	setup(frm) {
		frm.set_query("custom_salary_structure", function (doc) {
			return {
				filters: {
					is_active: "Yes",
					docstatus: 1,
					company: doc.company,
				},
			};
		});
	},

	refresh(frm) {
		_apply_pdf_restrictions(frm);
	},

	company(frm) {
		if (frm.doc.custom_salary_structure) {
			frm.set_value("custom_salary_structure", "");
		}
	},

	date_of_birth(frm) {
		if (!frm.doc.date_of_birth) {
			frm.set_value("custom_age", "");
			return;
		}
		const dob = frappe.datetime.str_to_obj(frm.doc.date_of_birth);
		const today = new Date();
		let years = today.getFullYear() - dob.getFullYear();
		let months = today.getMonth() - dob.getMonth();
		if (today.getDate() < dob.getDate()) months -= 1;
		if (months < 0) {
			years -= 1;
			months += 12;
		}
		if (years < 0) {
			frm.set_value("custom_age", "");
		} else {
			frm.set_value("custom_age", `${years} Years ${months} Months`);
		}
	},
});

// Post-upload extension check — catches non-PDF slip-throughs
PDF_ONLY_ATTACH_FIELDS.forEach((fname) => {
	frappe.ui.form.on("Employee", fname, function (frm) {
		const val = frm.doc[fname];
		if (!val) return;
		if (!/\.pdf($|\?)/i.test(val)) {
			frappe.msgprint({
				message: __("Only PDF files are allowed for {0}.", [
					frm.fields_dict[fname]?.df?.label || fname,
				]),
				indicator: "red",
			});
			frm.set_value(fname, "");
		}
	});
});
