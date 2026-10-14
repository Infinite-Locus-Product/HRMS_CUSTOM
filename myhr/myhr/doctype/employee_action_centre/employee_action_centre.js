// Copyright (c) 2026, Abhay Nain and contributors
// For license information, please see license.txt
//
// Master status is computed server-side by `EmployeeActionCentre._compute_master_status()`
// on every save. This script only handles desk-form UX (read-only locks for non-HR users
// and a client-side guard against marking an empty doc as Accepted).

const HR_ONLY_FIELDS = [
    "status",
    "aadhar_approval_status", "aadhar_remarks",
    "pan_approval_status", "pan_remarks",
    "education_approval_status", "education_remarks",
    "form_1_wages_act_approval_status", "form_1_wages_act_remarks",
    "form_2_nomination_approval_status", "form_2_nomination_remarks",
    "form_f_gratuity_approval_status", "form_f_gratuity_remarks",
    "pf_form_11_revised_approval_status", "pf_form_11_revised_remarks",
    "employer_1_offer_letter_approval_status", "employer_1_offer_letter_remarks",
    "employer_1_increment_letter_approval_status", "employer_1_increment_letter_remarks",
    "employer_1_payslip_last_month_approval_status", "employer_1_payslip_last_month_remarks",
    "employer_1_payslip_last_to_last_month_approval_status", "employer_1_payslip_last_to_last_month_remarks",
    "employer_1_payslip_month_before_that_approval_status", "employer_1_payslip_month_before_that_remarks",
    "employer_1_relieving_or_resignation_approval_status", "employer_1_relieving_or_resignation_remarks",
    "employer_2_approval_status", "employer_2_remarks",
    "employer_3_approval_status", "employer_3_remarks",
    "employer_4_approval_status", "employer_4_remarks",
    "employer_5_approval_status", "employer_5_remarks"
];

// Mirrors AC_DOCUMENT_ROWS in the Python doctype — used only for the empty-Accepted guard.
const HR_DOC_CHECKS = [
    { upload: "aadhar_upload",                                       na: "aadhar_is_na",      status: "aadhar_approval_status",                                       label: "Aadhar" },
    { upload: "pan_upload",                                          na: "pan_is_na",         status: "pan_approval_status",                                          label: "PAN" },
    { upload: "education_upload",                                    na: "education_is_na",   status: "education_approval_status",                                    label: "Education" },
    { upload: "form_1_wages_act_upload", na: "form_1_wages_act_is_na", status: "form_1_wages_act_approval_status", label: "Form 1 Payment of Wages Act" },
    { upload: "form_2_nomination_upload", na: "form_2_nomination_is_na", status: "form_2_nomination_approval_status", label: "Form 2 Nomination" },
    { upload: "form_f_gratuity_upload", na: "form_f_gratuity_is_na", status: "form_f_gratuity_approval_status", label: "Form F Payment of Gratuity" },
    { upload: "pf_form_11_revised_upload", na: "pf_form_11_revised_is_na", status: "pf_form_11_revised_approval_status", label: "PF Form 11 Revised" },
    { upload: "employer_1_offer_letter_doc",                         na: "",                  status: "employer_1_offer_letter_approval_status",                      label: "Employer 1 Offer Letter" },
    { upload: "employer_1_increment_letter_doc",                     na: "",                  status: "employer_1_increment_letter_approval_status",                  label: "Employer 1 Increment Letter" },
    { upload: "employer_1_payslip_last_month_doc",                   na: "",                  status: "employer_1_payslip_last_month_approval_status",                label: "Employer 1 Pay Slip Last Month" },
    { upload: "employer_1_payslip_last_to_last_month_doc",           na: "",                  status: "employer_1_payslip_last_to_last_month_approval_status",        label: "Employer 1 Pay Slip Last-to-Last Month" },
    { upload: "employer_1_payslip_month_before_that_doc",            na: "",                  status: "employer_1_payslip_month_before_that_approval_status",         label: "Employer 1 Pay Slip Month Before That" },
    { upload: "employer_1_relieving_or_resignation_doc",             na: "",                  status: "employer_1_relieving_or_resignation_approval_status",          label: "Employer 1 Relieving / Resignation Letter" },
    { upload: "employer_2_doc",                                      na: "employer_2_is_na",  status: "employer_2_approval_status",                                   label: "Employer 2" },
    { upload: "employer_3_doc",                                      na: "employer_3_is_na",  status: "employer_3_approval_status",                                   label: "Employer 3" },
    { upload: "employer_4_doc",                                      na: "employer_4_is_na",  status: "employer_4_approval_status",                                   label: "Employer 4" },
    { upload: "employer_5_doc",                                      na: "employer_5_is_na",  status: "employer_5_approval_status",                                   label: "Employer 5" },
];

function is_hr_user() {
    return (frappe.user_roles || []).some(role =>
        String(role || "").toLowerCase().includes("hr")
    );
}

function lock_hr_fields_for_employee(frm) {
    HR_ONLY_FIELDS.forEach(f => {
        frm.set_df_property(f, "read_only", 1);
    });
}

frappe.ui.form.on("Employee Action Centre", {

    onload: function(frm) {
        if (!is_hr_user()) {
            frappe.throw(__("You are not allowed to view Employee Action Centre in ERPNext Desk."), frappe.PermissionError);
            return;
        }
    },

    refresh: function(frm) {
        if (!is_hr_user()) {
            lock_hr_fields_for_employee(frm);
            if (["To be Reviewed", "Accepted"].includes(frm.doc.status)) {
                frm.set_read_only();
                frm.set_intro(
                    "✅ Documents submitted for HR review. No further edits allowed at this stage.",
                    "green"
                );
            }
            return;
        }

        // ----- HR Actions menu (EAC-11 / reopen) ---------------------------
        if (frm.is_new()) return;

        if (["To be Reviewed", "In Progress", "Action Required", "Ready to Submit"].includes(frm.doc.status)) {
            frm.add_custom_button(__("Accept all pending rows"), function () {
                frappe.confirm(
                    __("Mark every Pending / Awaiting HR row on this Action Centre as <b>Accepted</b>? "
                       + "Empty rows are skipped. Each row goes through the audit pipeline."),
                    () => {
                        frappe.call({
                            method: "myhr.api.hr_set_action_centre_verdict",
                            args: { name: frm.doc.name, verdict: "Accepted" },
                            freeze: true,
                            freeze_message: __("Accepting..."),
                            callback: (r) => {
                                if (r.message) {
                                    frappe.show_alert({
                                        message: __("Accepted {0} rows ({1} skipped).", [r.message.decided, r.message.skipped]),
                                        indicator: "green",
                                    });
                                    frm.reload_doc();
                                }
                            },
                        });
                    }
                );
            }, __("HR Actions"));

            frm.add_custom_button(__("Reject all pending rows"), function () {
                frappe.prompt(
                    [{
                        fieldname: "reason",
                        label: __("Rejection reason (applied to every row)"),
                        fieldtype: "Small Text",
                        reqd: 1,
                    }],
                    (values) => {
                        frappe.call({
                            method: "myhr.api.hr_set_action_centre_verdict",
                            args: { name: frm.doc.name, verdict: "Rejected", remarks: values.reason },
                            freeze: true,
                            freeze_message: __("Rejecting..."),
                            callback: (r) => {
                                if (r.message) {
                                    frappe.show_alert({
                                        message: __("Rejected {0} rows ({1} skipped).", [r.message.decided, r.message.skipped]),
                                        indicator: "orange",
                                    });
                                    frm.reload_doc();
                                }
                            },
                        });
                    },
                    __("Bulk reject pending rows"),
                    __("Reject")
                );
            }, __("HR Actions"));
        }

        if (frm.doc.submitted_for_review) {
            frm.add_custom_button(__("Reopen for re-edit"), function () {
                frappe.prompt(
                    [{
                        fieldname: "reason",
                        label: __("Reason for reopening"),
                        fieldtype: "Small Text",
                        reqd: 1,
                        description: __("Logged in the activity trail."),
                    }],
                    (values) => {
                        frappe.call({
                            method: "myhr.api.reopen_action_centre",
                            args: { name: frm.doc.name, reason: values.reason },
                            freeze: true,
                            freeze_message: __("Reopening..."),
                            callback: (r) => {
                                if (r.message && r.message.reopened) {
                                    frappe.show_alert({
                                        message: __("Reopened. Employee can edit again."),
                                        indicator: "blue",
                                    });
                                    frm.reload_doc();
                                }
                            },
                        });
                    },
                    __("Reopen Action Centre"),
                    __("Reopen")
                );
            }, __("HR Actions"));
        }
    },

    validate: function(frm) {
        if (!is_hr_user()) return;

        // Client-side guard: HR cannot mark a row Accepted with no file and not N/A.
        for (let check of HR_DOC_CHECKS) {
            if (frm.doc[check.status] === "Accepted" && !frm.doc[check.upload] && !frm.doc[check.na]) {
                frappe.throw(
                    `Cannot mark <b>${check.label}</b> as "Accepted" — no document uploaded and "Not Applicable" is not checked.`
                );
            }
        }
    }
});
