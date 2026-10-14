// Copyright (c) 2026, Abhay Nain and contributors
// For license information, please see license.txt
//
// HR Policy desk script — version + active flags are read-only; first-save shows a
// no-undo warning so HR doesn't accidentally create a permanent record. Deletion is
// blocked at the doctype-permission level (delete=0); use `is_active=0` to retire.

frappe.ui.form.on("HR Policy", {
    refresh(frm) {
        if (!frm.is_new()) {
            // Show a banner if the policy is currently inactive
            if (!frm.doc.is_active) {
                frm.set_intro(
                    __("This policy is <b>Inactive</b>. New employees will not be assigned it. Existing acknowledgements remain on record."),
                    "orange"
                );
            }
            // Surface the version next to the title for HR clarity
            frm.dashboard.add_indicator(
                __("Version {0}", [frm.doc.version || 1]),
                "blue"
            );

            // HR-only actions live under one menu group.
            const has_hr = frappe.user_roles.includes("HR Manager") ||
                frappe.user_roles.includes("System Manager");

            if (has_hr && frm.doc.is_active) {
                // E-5 — force a version bump without changing the file (e.g., annual re-ack).
                frm.add_custom_button(__("Force Re-acknowledgement Campaign"), function () {
                    frappe.prompt(
                        [{
                            fieldname: "reason",
                            label: __("Reason"),
                            fieldtype: "Small Text",
                            reqd: 1,
                            description: __("Recorded against the version bump in the audit log."),
                        }],
                        (values) => {
                            frappe.call({
                                method: "myhr.api.force_reacknowledgement_campaign",
                                args: { hr_policy: frm.doc.name, reason: values.reason },
                                freeze: true,
                                freeze_message: __("Bumping version + seeding fresh Pending rows..."),
                                callback: (r) => {
                                    if (r.message) {
                                        frappe.show_alert({
                                            message: __("Bumped to v{0}. Seeded {1} fresh Pending rows.", [
                                                r.message.new_version,
                                                r.message.seeded,
                                            ]),
                                            indicator: "blue",
                                        });
                                        frm.reload_doc();
                                    }
                                },
                            });
                        },
                        __("Force re-acknowledgement"),
                        __("Bump version")
                    );
                }, __("HR Actions"));
            }
        }
    },

    before_save(frm) {
        if (!frm.is_new()) return;
        return new Promise((resolve, reject) => {
            frappe.confirm(
                __(
                    "<b>Heads up:</b> once saved, this policy cannot be deleted (only set Inactive). " +
                    "Acknowledgements will be created for every matching active employee. " +
                    "Continue?"
                ),
                () => resolve(),
                () => reject()
            );
        });
    },

    file(frm) {
        if (frm.is_new() || !frm.doc.__islocal === false) return;
        // Local hint only; server-side validate bumps the version on save.
        if (frm.doc.file && frm.doc.file !== frm.doc.__last_sync_on) {
            frm.dashboard.set_headline(
                __("Saving will publish version {0} of this policy. Existing acknowledgements will be marked Superseded; matching employees will get a fresh Pending row.", [(frm.doc.version || 1) + 1])
            );
        }
    },
});
