// Interview Type — keep the standard Fixxly competencies in the Expected Skillset.
//
// Which skills count as defaults is data, not code: any Skill with
// "Default Competency" ticked (seeded by setup.py:DEFAULT_COMPETENCIES). HR can
// add or retire one without a release.
//
// Why this is more than a one-shot onload:
// HRMS's own interview_type.js has a `designation` handler that calls
// frappe.model.clear_table("expected_skill_set") and refills it from the
// Designation's skills — asynchronously, so it lands after ours. Picking a
// Designation therefore wipes anything we added on load. We re-assert after that
// settles. `ensureDefaults` only ever APPENDS missing competencies, so running it
// repeatedly is free and Designation-derived skills survive alongside ours.
//
// Only runs on an unsaved Interview Type; an existing record is never touched.
// Nothing is written until the user saves.

const DEFAULT_SKILL_LIMIT = 50;
// Re-assert after HRMS's async designation handler. Idempotent, so several
// attempts just cover a slow round-trip.
const REASSERT_DELAYS_MS = [0, 400, 1200];

let defaultsPromise = null;

function getDefaultCompetencies() {
	if (!defaultsPromise) {
		defaultsPromise = frappe.db
			.get_list("Skill", {
				filters: { custom_is_default_competency: 1 },
				fields: ["name", "description"],
				order_by: "name asc",
				limit: DEFAULT_SKILL_LIMIT,
			})
			.then((rows) => rows || []);
	}
	return defaultsPromise;
}

function ensureDefaults(frm) {
	if (!frm.is_new()) return;

	return getDefaultCompetencies().then((skills) => {
		if (!skills.length || !frm.is_new()) return;

		const present = new Set((frm.doc.expected_skill_set || []).map((r) => r.skill));
		let added = 0;

		skills.forEach((s) => {
			if (present.has(s.name)) return;
			frm.add_child("expected_skill_set", { skill: s.name, description: s.description });
			added += 1;
		});

		if (added) frm.refresh_field("expected_skill_set");
	});
}

frappe.ui.form.on("Interview Type", {
	onload(frm) {
		ensureDefaults(frm);
	},

	designation(frm) {
		REASSERT_DELAYS_MS.forEach((ms) => setTimeout(() => ensureDefaults(frm), ms));
	},
});
