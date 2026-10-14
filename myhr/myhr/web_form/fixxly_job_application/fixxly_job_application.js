// Rendered server-side as a Jinja template (see fixxly_job_application.py), so
// the three values below are baked in per request.
frappe.ready(function () {
	const questions = {{ screening_questions | tojson }};
	const openingOk = {{ opening_ok | tojson }};
	const openingMessage = {{ opening_message | tojson }};
	const openingTitle = {{ opening_title | tojson }};
	const openingDesignation = {{ opening_designation | tojson }};
	const openingDepartment = {{ opening_department | tojson }};

	const SLOT_FIELD = "screening_questions_html";
	const TABLE_FIELD = "custom_screening_responses";
	const SAME_ADDR = "custom_same_as_permanent_address";
	const PERM_ADDR = "custom_permanent_address";
	const CURR_ADDR = "custom_current_address";

	function whenFormReady(fn, tries = 0) {
		const ready =
			window.frappe &&
			frappe.web_form &&
			frappe.web_form.fields_dict &&
			frappe.web_form.fields_dict[SLOT_FIELD];
		if (ready) return fn();
		if (tries < 100) setTimeout(() => whenFormReady(fn, tries + 1), 50);
	}

	function slot() {
		return frappe.web_form.fields_dict[SLOT_FIELD].$wrapper;
	}

	function render() {
		const $slot = slot();
		$slot.empty();

		if (!openingOk) {
			$slot.append(
				`<div class="alert alert-warning" role="alert">${frappe.utils.escape_html(openingMessage)}</div>`
			);
			$(".web-form-footer .submit-btn").hide();
			return;
		}

		if (!questions.length) {
			$slot.closest(".form-section").hide();
			return;
		}

		const $list = $('<div class="screening-questions"></div>');
		questions.forEach((q) => {
			const required = cint(q.is_mandatory);
			const $item = $(`
				<div class="frappe-control form-group screening-question">
					<label class="control-label ${required ? "reqd" : ""}"></label>
					<textarea class="form-control screening-answer" rows="3" data-question=""></textarea>
				</div>
			`);
			$item.find("label").text(q.question);
			$item.find("textarea").attr("data-question", q.name);
			$list.append($item);
		});
		$slot.append($list);
	}

	function collect() {
		const rows = [];
		const missing = [];
		questions.forEach((q) => {
			const answer = ($(`textarea.screening-answer[data-question="${q.name}"]`).val() || "").trim();
			if (cint(q.is_mandatory) && !answer) missing.push(q.question);
			rows.push({
				source_question: q.name,
				question: q.question,
				is_mandatory: cint(q.is_mandatory),
				answer: answer,
			});
		});
		return { rows, missing };
	}

	// Current address mirrors permanent address while the box is ticked, and the
	// control is locked so the two cannot drift. read_only is cosmetic on a web
	// form (the browser still posts whatever it holds), so job_applicant_hooks
	// re-applies the copy server-side.
	function syncAddress() {
		const same = cint(frappe.web_form.get_value(SAME_ADDR));
		if (same) frappe.web_form.set_value(CURR_ADDR, frappe.web_form.get_value(PERM_ADDR) || "");
		frappe.web_form.set_df_property(CURR_ADDR, "read_only", same ? 1 : 0);
	}

	whenFormReady(() => {
		render();

		if (frappe.web_form.fields_dict[SAME_ADDR]) {
			frappe.web_form.on(SAME_ADDR, syncAddress);
			frappe.web_form.on(PERM_ADDR, syncAddress);
			syncAddress();
		}

		if (openingOk) {
			// job_title / designation / department are read-only Data fields (a
			// read-only Link control has no input in web forms). Show the
			// human-readable title under the ID and fill designation/department
			// for display; the server re-fetches both from the opening on insert.
			frappe.web_form.set_df_property("job_title", "description", openingTitle);
			frappe.web_form.set_value("designation", openingDesignation);
			frappe.web_form.set_value("custom_department", openingDepartment);
		}

		frappe.web_form.validate = () => {
			if (!openingOk) {
				frappe.msgprint(openingMessage);
				return false;
			}
			const { rows, missing } = collect();
			if (missing.length) {
				frappe.msgprint({
					title: __("Missing Answers"),
					indicator: "red",
					message:
						__("Please answer the following required questions:") +
						"<br>" +
						missing.map((m) => frappe.utils.escape_html(m)).join("<br>"),
				});
				return false;
			}
			// Hidden Table controls are not serialised by get_values(); the
			// payload is built from frappe.web_form.doc, so write the rows there.
			frappe.web_form.doc[TABLE_FIELD] = rows;
			if (cint(frappe.web_form.get_value(SAME_ADDR))) {
				frappe.web_form.doc[CURR_ADDR] = frappe.web_form.get_value(PERM_ADDR) || "";
			}
			return true;
		};
	});
});
