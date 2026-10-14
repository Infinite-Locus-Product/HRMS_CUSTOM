// Separation HR Clearance — the Release Relieving Letter control.
//
// The button is the only way to issue a relieving letter; nothing releases one
// automatically. It is a convenience only: `release_relieving_letter` re-checks
// every condition server-side, so hiding the button is not what enforces the
// gate.
//
// Whether it may be released is never worked out here. `get_release_status`
// returns `can_release` plus the list of blockers, so the form and the server
// can never disagree about why a letter is being withheld.

const RELEASE_METHOD =
	"myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance.release_relieving_letter";
const STATUS_METHOD =
	"myhr.myhr.doctype.separation_hr_clearance.separation_hr_clearance.get_release_status";

function _render_release_control(frm) {
	// Rebuilt from scratch on every refresh: both of these accumulate otherwise,
	// leaving duplicate buttons and a growing stack of stale blocker messages.
	frm.dashboard.clear_comment();

	if (frm.is_new()) {
		return;
	}

	frappe
		.call({ method: STATUS_METHOD, args: { name: frm.doc.name } })
		.then((r) => {
			const status = r && r.message;
			if (!status) {
				return;
			}

			if (status.released) {
				_show_released(frm, status);
				return;
			}

			if (status.can_release) {
				_add_release_button(frm);
			} else {
				_show_blockers(frm, status.blockers);
			}
		})
		// Never leave the form looking as though the letter is simply not ready:
		// a failed status call means we do not know.
		.catch(() => {
			frm.dashboard.add_comment(
				__("Could not check whether the relieving letter can be released."),
				"red",
				true,
			);
		});
}

function _show_released(frm, status) {
	frm.dashboard.add_comment(__("The relieving letter has been released."), "green", true);

	if (status.relieving_letter) {
		frm.add_custom_button(__("View Relieving Letter"), () => {
			window.open(status.relieving_letter, "_blank");
		});
	}
}

function _show_blockers(frm, blockers) {
	if (!blockers || !blockers.length) {
		return;
	}

	// Every blocker at once, not the first one: otherwise HR fixes one, refreshes,
	// and discovers the next.
	frm.dashboard.add_comment(
		__("The relieving letter cannot be released yet because {0}.", [blockers.join("; ")]),
		"orange",
		true,
	);
}

function _add_release_button(frm) {
	frm.add_custom_button(__("Release Relieving Letter"), () => {
		frappe.confirm(
			__(
				"This generates {0}'s relieving letter and attaches it to this record. It cannot be released a second time. Continue?",
				[frm.doc.employee_name || frm.doc.employee],
			),
			() => {
				frappe.call({
					method: RELEASE_METHOD,
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Generating the relieving letter..."),
					callback: () => {
						frappe.show_alert(
							{ message: __("Relieving letter released."), indicator: "green" },
							5,
						);
						// Reloaded rather than patched in: the release also stamps
						// Released On and Released By, and attaches the file.
						frm.reload_doc();
					},
				});
			},
		);
	}).addClass("btn-primary");
}

frappe.ui.form.on("Separation HR Clearance", {
	refresh(frm) {
		_render_release_control(frm);
	},
});
