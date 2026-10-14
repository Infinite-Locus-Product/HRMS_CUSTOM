<template>
	<IonPage>
		<IonContent :fullscreen="true">
			<div class="bg-[#FBFBFC] min-h-screen pb-[120px]">
				<div
					class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative"
				>
					<!-- Header -->
					<div
						class="flex flex-row bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100 items-center gap-1"
					>
						<Button variant="ghost" class="!px-2 hover:bg-gray-100" @click="goBack">
							<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
						</Button>
						<div class="flex flex-col ml-1 overflow-hidden">
							<h2
								class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1"
							>
								{{
									selected ? __("Review Resignation") : __("Separation Approvals")
								}}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span class="text-[10px] font-bold uppercase tracking-widest">
									{{ headerSubtitle }}
								</span>
							</div>
						</div>
					</div>

					<div v-if="loading" class="flex justify-center py-16">
						<LoadingIndicator class="w-6 h-6 text-gray-500" />
					</div>

					<div
						v-else-if="errorMsg"
						class="m-4 p-4 rounded-2xl bg-red-50 border border-red-200"
					>
						<p class="text-sm font-semibold text-red-800">{{ errorMsg }}</p>
					</div>

					<!-- LIST -->
					<div v-else-if="!selected" class="flex-1 px-4 py-5 sm:p-5">
						<div
							v-if="!pending.length"
							class="rounded-2xl border border-gray-100 bg-gray-50 p-8 text-center"
						>
							<FeatherIcon
								name="check-circle"
								class="h-8 w-8 text-gray-300 mx-auto"
							/>
							<p class="mt-3 text-sm font-bold text-gray-500">
								{{ __("Nothing waiting on you") }}
							</p>
						</div>

						<div v-else class="space-y-3">
							<button
								v-for="row in pending"
								:key="row.name"
								type="button"
								@click="openRow(row)"
								class="w-full text-left rounded-2xl bg-white border border-gray-100 shadow-sm p-4 hover:bg-blue-50/60 active:bg-blue-100/60 transition-colors"
							>
								<div class="flex items-center justify-between gap-3">
									<div class="min-w-0">
										<div
											class="text-[15px] font-extrabold text-gray-900 truncate"
										>
											{{ row.employee_name }}
										</div>
										<div
											class="text-[11px] font-semibold text-gray-400 truncate"
										>
											{{ row.employee }} · {{ row.subtitle }}
										</div>
									</div>
									<div class="flex items-center gap-2 shrink-0">
										<span
											class="px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest"
											:class="
												row.kind === 'manager_clearance'
													? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
													: row.badge === 'L1'
														? 'bg-blue-50 text-blue-700 border border-blue-200'
														: 'bg-purple-50 text-purple-700 border border-purple-200'
											"
										>
											{{ row.badge }}
										</span>
										<FeatherIcon
											name="chevron-right"
											class="h-4 w-4 text-gray-300"
										/>
									</div>
								</div>
								<div
									v-if="row.warning"
									class="mt-2 inline-flex items-center gap-1 text-[11px] font-bold text-amber-700"
								>
									<FeatherIcon name="alert-triangle" class="h-3 w-3" />
									{{ row.warning }}
								</div>
							</button>
						</div>
					</div>

					<!-- DETAIL -->
					<div v-else class="flex-1 px-4 py-5 sm:p-5 space-y-5">
						<!-- A decision replaces the whole screen rather than adding a note
						     at the top of it. The buttons are at the bottom of a long form, so
						     a banner above the fold is something the approver never sees. -->
						<div
							v-if="justActed"
							class="flex-1 flex flex-col items-center justify-center px-6 py-16 text-center"
						>
							<div
								class="h-16 w-16 rounded-full flex items-center justify-center"
								:class="justActed === 'Approve' ? 'bg-emerald-100' : 'bg-red-100'"
							>
								<FeatherIcon
									:name="justActed === 'Approve' ? 'check' : 'x'"
									class="h-8 w-8"
									:class="
										justActed === 'Approve'
											? 'text-emerald-600'
											: 'text-red-600'
									"
								/>
							</div>
							<h3
								class="mt-4 text-lg font-black"
								:class="
									justActed === 'Approve' ? 'text-emerald-900' : 'text-red-900'
								"
							>
								{{ justActed === "Approve" ? __("Approved") : __("Rejected") }}
							</h3>
							<p class="mt-1 text-sm font-semibold text-gray-600">
								{{ selected.employee_name }}
							</p>
							<p class="mt-3 text-xs font-medium text-gray-500 max-w-xs">
								{{ outcomeHint }}
							</p>
							<Button
								class="mt-6 w-full max-w-xs py-5"
								variant="solid"
								@click="backToList"
							>
								{{ __("Back to approvals") }}
							</Button>
						</div>

						<template v-else>
							<!-- Shown when the record has moved on for any other reason — opened
						     after someone else acted, or already finished. -->
							<div
								v-if="!canAct && !justActed"
								class="rounded-2xl border p-4 flex items-start gap-3"
								:class="statusTone"
							>
								<FeatherIcon :name="statusIcon" class="h-5 w-5 mt-0.5 shrink-0" />
								<div>
									<div class="text-sm font-black">
										{{ selected.workflow_state }}
									</div>
									<p class="text-xs font-medium opacity-80 mt-0.5">
										{{ statusHint }}
									</p>
								</div>
							</div>

							<section
								class="rounded-2xl border border-gray-100 bg-gradient-to-br from-blue-600 to-blue-700 p-4 text-white shadow-sm"
							>
								<div
									class="text-[10px] font-bold uppercase tracking-widest opacity-75"
								>
									{{ selected.name }}
								</div>
								<div class="text-lg font-extrabold truncate leading-tight">
									{{ selected.employee_name }}
								</div>
								<div class="text-[11px] font-semibold opacity-80 truncate">
									{{
										[selected.designation, selected.department]
											.filter(Boolean)
											.join(" · ") || "—"
									}}
								</div>
							</section>

							<section
								class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
							>
								<h2
									class="text-xs font-black uppercase tracking-widest text-gray-500"
								>
									{{ __("What They Filed") }}
								</h2>
								<Row
									:label="__('Reason')"
									:value="selected.custom_resignation_reason"
								/>
								<Row
									:label="__('Detail')"
									:value="selected.custom_detailed_reason"
								/>
								<Row
									:label="__('Requested Relieving Date')"
									:value="selected.custom_requested_relieving_date"
								/>
								<Row
									:label="__('Official End Date')"
									:value="selected.custom_official_end_date"
								/>
								<Row
									:label="__('Notice Period Shortfall')"
									:value="`${selected.custom_notice_period_shortfall || 0} ${__('days')}`"
								/>
								<Row
									:label="__('Buy-out Notice Period?')"
									:value="selected.custom_buyout_notice_period"
								/>
								<Row
									v-if="selected.custom_buyout_notice_period === 'Yes'"
									:label="__('Buy-out Amount')"
									:value="selected.custom_buyout_amount"
								/>
							</section>

							<section
								v-if="canAct"
								class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-4"
							>
								<h2
									class="text-xs font-black uppercase tracking-widest text-gray-500"
								>
									{{ __("Your Decision") }}
								</h2>

								<div>
									<label class="block text-xs font-bold text-gray-600 mb-1">
										{{ __("Approved Relieving Date") }}
										<span class="text-red-500">*</span>
									</label>
									<input
										type="date"
										v-model="decision.custom_approved_relieving_date"
										class="w-full rounded-lg border-gray-300 text-sm"
									/>
									<p class="mt-1 text-[11px] text-gray-400 font-medium">
										{{
											__(
												"Defaults to what the employee asked for. You may move it.",
											)
										}}
									</p>
								</div>

								<div>
									<label class="block text-xs font-bold text-gray-600 mb-1">
										{{ __("Notice Period Waiver") }}
										<span class="text-red-500">*</span>
									</label>
									<select
										v-model="decision.custom_notice_period_waiver"
										class="w-full rounded-lg border-gray-300 text-sm"
									>
										<option value="">{{ __("Select") }}</option>
										<option
											v-for="o in selected.options.waiver"
											:key="o"
											:value="o"
										>
											{{ o }}
										</option>
									</select>
									<p
										v-if="decision.custom_notice_period_waiver === 'Yes'"
										class="mt-1 text-[11px] font-bold text-amber-700"
									>
										{{
											__(
												"HR Ops will be flagged for confirmation. This does not block approval.",
											)
										}}
									</p>
								</div>

								<div>
									<label class="block text-xs font-bold text-gray-600 mb-1">
										{{ __("Retention Discussion Held?") }}
										<span class="text-red-500">*</span>
									</label>
									<select
										v-model="decision.custom_retention_discussion_held"
										class="w-full rounded-lg border-gray-300 text-sm"
									>
										<option value="">{{ __("Select") }}</option>
										<option
											v-for="o in selected.options.retention"
											:key="o"
											:value="o"
										>
											{{ o }}
										</option>
									</select>
								</div>

								<div>
									<label class="block text-xs font-bold text-gray-600 mb-1">
										{{ __("Reason for Rejection / Hold") }}
									</label>
									<textarea
										v-model="decision.custom_rejection_hold_reason"
										rows="3"
										class="w-full rounded-lg border-gray-300 text-sm"
									/>
									<p class="mt-1 text-[11px] text-gray-400 font-medium">
										{{ __("Required if you reject.") }}
									</p>
								</div>
							</section>
						</template>
					</div>

					<!-- Action bar -->
					<div
						v-if="selected && !loading && canAct"
						class="fixed bottom-0 inset-x-0 sm:max-w-4xl sm:mx-auto bg-white border-t p-4 flex flex-col standalone:pb-safe-bottom z-30"
					>
						<!-- Errors stay on screen until the next successful action. A toast
						     is not enough: the save that follows a file upload happens in the
						     background, and its toast fires where nobody is looking. -->
						<div
							v-if="actionError"
							class="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 flex items-start gap-2"
						>
							<FeatherIcon
								name="alert-circle"
								class="h-4 w-4 text-red-600 mt-0.5 shrink-0"
							/>
							<p class="text-xs font-semibold text-red-800 flex-1">
								{{ actionError }}
							</p>
							<button
								type="button"
								@click="actionError = ''"
								class="p-0.5 text-red-400 hover:text-red-700"
							>
								<FeatherIcon name="x" class="h-3.5 w-3.5" />
							</button>
						</div>
						<div class="flex gap-3">
							<Button
								v-if="allowedActions.includes('Reject')"
								class="w-full py-5"
								theme="red"
								variant="subtle"
								:loading="rejecting"
								:disabled="!canReject"
								@click="act('Reject')"
							>
								{{ __("Reject") }}
							</Button>
							<Button
								v-if="allowedActions.includes('Approve')"
								class="w-full py-5"
								variant="solid"
								:loading="approving"
								:disabled="!canApprove"
								@click="act('Approve')"
							>
								{{ __("Approve") }}
							</Button>
						</div>
					</div>
				</div>
			</div>
		</IonContent>
	</IonPage>
</template>

<script setup>
import { computed, h, inject, ref } from "vue";
import { Button, FeatherIcon, LoadingIndicator, createResource, toast } from "frappe-ui";

// frappe-ui exports `toast(options)` here — there is no `toast.success`.
// Calling one threw mid-handler and skipped everything after it, which is how a
// successful approval ended up showing no confirmation at all.
function notify(title, text, ok = true) {
	toast({
		title,
		text,
		icon: ok ? "check" : "alert-triangle",
		iconClasses: ok ? "text-green-500" : "text-red-500",
	});
}

import { IonPage, IonContent, useIonRouter, onIonViewWillEnter } from "@ionic/vue";

const ionRouter = useIonRouter();
const __ = inject("$translate");

const Row = (props) =>
	h("div", { class: "flex items-start justify-between gap-3" }, [
		h("span", { class: "text-xs font-bold text-gray-500 shrink-0" }, props.label),
		h(
			"span",
			{ class: "text-sm font-semibold text-gray-900 text-right break-words" },
			props.value === 0 || props.value ? String(props.value) : "—",
		),
	]);
Row.props = ["label", "value"];

const loading = ref(true);
const errorMsg = ref("");
const pending = ref([]);
const selected = ref(null);
const approving = ref(false);
const rejecting = ref(false);
const actionError = ref("");

const decision = ref({
	custom_approved_relieving_date: "",
	custom_notice_period_waiver: "",
	custom_retention_discussion_held: "",
	custom_rejection_hold_reason: "",
});

const headerSubtitle = computed(() => {
	if (selected.value) return selected.value.workflow_state || "";
	return pending.value.length
		? `${pending.value.length} ${__("awaiting you")}`
		: __("Nothing pending");
});

// `actions` is the workflow's own transition list for THIS user on THIS record,
// computed server-side. Deriving the buttons from it means a record that has
// moved on (L1 approved, so it now sits with L2) shows its status instead of
// buttons that would fail on click.
const allowedActions = computed(() => selected.value?.actions || []);
const canAct = computed(
	() => allowedActions.value.includes("Approve") || allowedActions.value.includes("Reject"),
);

// Set only by this user's own click, and cleared whenever the screen is
// re-entered or another record is opened — so it never claims credit for a
// decision somebody else made.
const justActed = ref(null);

const outcomeHint = computed(() => {
	if (justActed.value === "Reject") {
		return __("Returned to the employee. They can amend it and send it again.");
	}
	return selected.value?.workflow_state === "Approved"
		? __("Fully approved. The clearances have been raised automatically.")
		: __("Sent on to the Function Head for the second approval.");
});

const statusTone = computed(() => {
	const state = selected.value?.workflow_state;
	if (state === "Rejected") return "bg-red-50 border-red-200 text-red-800";
	if (state === "Approved") return "bg-green-50 border-green-200 text-green-800";
	return "bg-blue-50 border-blue-200 text-blue-800";
});

const statusIcon = computed(() => {
	const state = selected.value?.workflow_state;
	if (state === "Rejected") return "x-circle";
	if (state === "Approved") return "check-circle";
	return "clock";
});

const statusHint = computed(() => {
	const state = selected.value?.workflow_state;
	if (state === "Pending L2 Approval")
		return __("Waiting on the Function Head. Nothing to do here.");
	if (state === "Pending L1 Approval") return __("Waiting on the Reporting Manager.");
	if (state === "Approved") return __("Fully approved. The separation is final.");
	if (state === "Rejected") return __("Returned to the employee to amend and re-submit.");
	return __("No action is available to you on this record.");
});

// Mirrors the server rules so the buttons disable instead of round-tripping
// to a validation error. The server still enforces both independently.
const canApprove = computed(
	() =>
		!!decision.value.custom_approved_relieving_date &&
		!!decision.value.custom_notice_period_waiver &&
		!!decision.value.custom_retention_discussion_held,
);
const canReject = computed(() => !!(decision.value.custom_rejection_hold_reason || "").trim());

function goBack() {
	if (selected.value) {
		backToList();
		return;
	}
	if (window.history.length > 2) window.history.back();
	else ionRouter.push({ name: "Home" });
}

// One inbox for the whole exit flow: resignations awaiting this user as L1/L2
// AND handovers awaiting them as reporting manager. A manager should not have to
// know which tile holds their pending item.
const list = createResource({
	url: "myhr.clearance_api.get_my_separation_inbox",
	onSuccess: (data) => {
		pending.value = data || [];
		loading.value = false;
	},
	onError: (err) => {
		loading.value = false;
		errorMsg.value = err?.messages?.[0] || err?.message || String(err);
	},
});

const detail = createResource({
	url: "myhr.resignation_api.get_separation_for_approval",
	onSuccess: (data) => {
		selected.value = data;
		decision.value = {
			// Pre-fill with the employee's requested date, per the spec.
			custom_approved_relieving_date:
				data.custom_approved_relieving_date || data.custom_requested_relieving_date || "",
			custom_notice_period_waiver: data.custom_notice_period_waiver || "",
			custom_retention_discussion_held: data.custom_retention_discussion_held || "",
			custom_rejection_hold_reason: "",
		};
		loading.value = false;
	},
	onError: (err) => {
		loading.value = false;
		errorMsg.value = err?.messages?.[0] || err?.message || String(err);
	},
});

const actResource = createResource({ url: "myhr.resignation_api.act_on_separation" });
// One place that decides what the user is told when something fails. Frappe
// puts the useful sentence in `messages[0]`; `message` is often a bare
// exception. The banner and the toast get the same words.
function reportError(err, fallback) {
	const message = err?.messages?.[0] || err?.message || fallback;
	actionError.value = message;
	notify(__("Something went wrong"), message, false);
	return message;
}

function openRow(row) {
	// Clearances are a separate screen; resignations open inline here.
	if (row.kind === "manager_clearance") {
		ionRouter.push({ name: "ClearanceReview", params: { name: row.name } });
		return;
	}
	open(row.name);
}

function backToList() {
	selected.value = null;
	justActed.value = null;
	list.reload();
}

function open(name) {
	loading.value = true;
	errorMsg.value = "";
	actionError.value = "";
	justActed.value = null;
	detail.submit({ name });
}

async function act(action) {
	const busy = action === "Approve" ? approving : rejecting;
	busy.value = true;
	try {
		const result = await actResource.submit({
			name: selected.value.name,
			action,
			payload: JSON.stringify(decision.value),
		});
		// State first, notification second. The other way round, anything that
		// throws while notifying skips the lines that show the result — which is
		// exactly how a successful approval ended up looking like it had failed.
		//
		// The payload the action returned is swapped in rather than re-fetched:
		// `detail` is the same endpoint with the same argument, so frappe-ui
		// would serve its cached copy and the screen would keep showing the old
		// state with live buttons. The action's own response is authoritative.
		selected.value = result;
		justActed.value = action;
		notify(
			action === "Approve" ? __("Approved") : __("Rejected"),
			action === "Approve"
				? result.workflow_state === "Approved"
					? __("The separation is now final.")
					: __("Sent to the Function Head.")
				: __("Returned to the employee."),
			action === "Approve",
		);
		decision.value.custom_rejection_hold_reason = "";
		list.reload();
	} catch (err) {
		reportError(err, __("Could not record your decision."));
	} finally {
		busy.value = false;
	}
}

onIonViewWillEnter(() => {
	loading.value = true;
	errorMsg.value = "";
	selected.value = null;
	justActed.value = null;
	list.reload();
});
</script>
