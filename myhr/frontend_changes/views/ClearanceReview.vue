<template>
	<IonPage>
		<IonContent :fullscreen="true">
			<div class="bg-[#FBFBFC] min-h-screen pb-[120px]">
				<div
					class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative"
				>
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
								{{ __("Review Handover") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span class="text-[10px] font-bold uppercase tracking-widest">
									{{ clearance?.workflow_state || "" }}
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

					<div v-else class="flex-1 px-4 py-5 sm:p-5 space-y-5">
						<!-- Replaces the screen rather than sitting above it: the Complete
						     button is at the bottom of a long form. -->
						<div
							v-if="justCompleted"
							class="flex-1 flex flex-col items-center justify-center px-6 py-16 text-center"
						>
							<div
								class="h-16 w-16 rounded-full bg-emerald-100 flex items-center justify-center"
							>
								<FeatherIcon name="check" class="h-8 w-8 text-emerald-600" />
							</div>
							<h3 class="mt-4 text-lg font-black text-emerald-900">
								{{ __("Completed") }}
							</h3>
							<p class="mt-1 text-sm font-semibold text-gray-600">
								{{ clearance.employee_name }}
							</p>
							<p class="mt-3 text-xs font-medium text-gray-500 max-w-xs">
								{{
									__(
										"The handover is signed off. Nothing further is needed from you.",
									)
								}}
							</p>
							<Button
								class="mt-6 w-full max-w-xs py-5"
								variant="solid"
								@click="goBack"
							>
								{{ __("Back to approvals") }}
							</Button>
						</div>

						<template v-else>
							<!-- Opened after it was already finished, or by someone with no action. -->
							<div
								v-if="!canAct"
								class="rounded-2xl border border-green-200 bg-green-50 p-4 flex items-start gap-3 text-green-800"
							>
								<FeatherIcon name="check-circle" class="h-5 w-5 mt-0.5 shrink-0" />
								<div>
									<div class="text-sm font-black">
										{{ clearance.workflow_state }}
									</div>
									<p class="text-xs font-medium opacity-80 mt-0.5">
										{{ __("Nothing further is needed from you.") }}
									</p>
								</div>
							</div>

							<section
								class="rounded-2xl border border-gray-100 bg-gradient-to-br from-blue-600 to-blue-700 p-4 text-white shadow-sm"
							>
								<div
									class="text-[10px] font-bold uppercase tracking-widest opacity-75"
								>
									{{ clearance.employee }}
								</div>
								<div class="text-lg font-extrabold truncate leading-tight">
									{{ clearance.employee_name }}
								</div>
								<div class="text-[11px] font-semibold opacity-80 truncate">
									{{ clearance.department || "—" }}
								</div>
							</section>

							<!-- What they handed over -->
							<section
								class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
							>
								<h2
									class="text-xs font-black uppercase tracking-widest text-gray-500"
								>
									{{ __("What They Handed Over") }}
								</h2>
								<div
									v-for="(row, i) in clearance.handover_documents"
									:key="i"
									class="rounded-xl border border-gray-100 bg-gray-50/60 p-3"
								>
									<div class="text-sm font-extrabold text-gray-900">
										{{ row.title || __("Untitled") }}
									</div>
									<a
										v-if="row.external_link"
										:href="row.external_link"
										target="_blank"
										rel="noopener"
										class="text-xs font-semibold text-blue-700 break-all"
									>
										{{ row.external_link }}
									</a>
									<a
										v-if="row.attachment"
										:href="row.attachment"
										target="_blank"
										rel="noopener"
										class="block text-xs font-semibold text-blue-700 break-all"
									>
										{{ __("Open attachment") }}
									</a>
									<p v-if="row.notes" class="text-xs text-gray-600 mt-1">
										{{ row.notes }}
									</p>
								</div>
								<p
									v-if="!clearance.handover_documents.length"
									class="text-xs font-bold text-red-600"
								>
									{{ __("Nothing was attached.") }}
								</p>

								<Row
									:label="__('Primary Successor')"
									:value="
										clearance.primary_successor_name ||
										clearance.primary_successor
									"
								/>
								<Row
									:label="__('Project / Client Status')"
									:value="clearance.project_client_status_summary"
								/>
							</section>

							<!-- Verification -->
							<section
								v-if="canAct"
								class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-4"
							>
								<h2
									class="text-xs font-black uppercase tracking-widest text-gray-500"
								>
									{{ __("Your Verification") }}
								</h2>

								<div>
									<label class="block text-xs font-bold text-gray-600 mb-1">
										{{ __("KT / Handover Received?") }}
										<span class="text-red-500">*</span>
									</label>
									<select
										v-model="decision.kt_handover_received"
										class="w-full rounded-lg border-gray-300 text-sm"
									>
										<option value="">{{ __("Select") }}</option>
										<option
											v-for="o in clearance.options.kt_handover_received"
											:key="o"
											:value="o"
											:disabled="o === 'Yes' && !handoverProvided"
										>
											{{ o }}
										</option>
									</select>
									<p
										v-if="!handoverProvided"
										class="mt-1 text-[11px] font-bold text-amber-700"
									>
										{{
											__(
												"Yes is unavailable until they attach a document and name a successor.",
											)
										}}
									</p>
								</div>

								<div>
									<label class="block text-xs font-bold text-gray-600 mb-1">
										{{ __("Project Access Revocation Requested") }}
									</label>
									<label
										v-for="system in clearance.options.access_systems"
										:key="system"
										class="flex items-center gap-2 py-1 cursor-pointer"
									>
										<input
											type="checkbox"
											:value="system"
											v-model="decision.access_revocation_requested"
											:disabled="decision.access_revocation_not_applicable"
											class="h-4 w-4 rounded border-gray-300"
										/>
										<span class="text-sm font-semibold text-gray-800">{{
											system
										}}</span>
									</label>
									<label class="flex items-center gap-2 py-1 mt-1 cursor-pointer">
										<input
											type="checkbox"
											:checked="!!decision.access_revocation_not_applicable"
											@change="toggleNotApplicable($event.target.checked)"
											class="h-4 w-4 rounded border-gray-300"
										/>
										<span class="text-sm font-semibold text-gray-600">
											{{ __("Not applicable") }}
										</span>
									</label>
								</div>

								<div>
									<label class="block text-xs font-bold text-gray-600 mb-1">
										{{ __("Client / External Handoff Complete?") }}
									</label>
									<select
										v-model="decision.client_handoff_complete"
										class="w-full rounded-lg border-gray-300 text-sm"
									>
										<option value="">{{ __("Select") }}</option>
										<option
											v-for="o in clearance.options.client_handoff_complete"
											:key="o"
											:value="o"
										>
											{{ o }}
										</option>
									</select>
								</div>

								<label class="flex items-center gap-2 cursor-pointer">
									<input
										type="checkbox"
										:checked="!!decision.code_repository_transferred"
										@change="
											decision.code_repository_transferred = $event.target
												.checked
												? 1
												: 0
										"
										class="h-4 w-4 rounded border-gray-300"
									/>
									<span class="text-sm font-semibold text-gray-800">
										{{ __("Code / document repositories transferred") }}
									</span>
								</label>

								<div>
									<label class="block text-xs font-bold text-gray-600 mb-1">
										{{ __("Manager Remarks / Sign-off") }}
										<span class="text-red-500">*</span>
									</label>
									<textarea
										v-model="decision.manager_remarks"
										rows="3"
										class="w-full rounded-lg border-gray-300 text-sm"
									/>
								</div>
							</section>
						</template>
					</div>

					<div
						v-if="!loading && canAct"
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
						<Button
							class="w-full py-5"
							variant="solid"
							:loading="completing"
							:disabled="!canComplete"
							@click="complete"
						>
							{{ __("Complete Clearance") }}
						</Button>
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
import { useRoute } from "vue-router";

const route = useRoute();
const ionRouter = useIonRouter();
const __ = inject("$translate");

const Row = (props) =>
	h("div", { class: "flex items-start justify-between gap-3 pt-1" }, [
		h("span", { class: "text-xs font-bold text-gray-500 shrink-0" }, props.label),
		h(
			"span",
			{ class: "text-sm font-semibold text-gray-900 text-right break-words" },
			props.value || "—",
		),
	]);
Row.props = ["label", "value"];

const loading = ref(true);
const completing = ref(false);
const actionError = ref("");
const errorMsg = ref("");
const clearance = ref(null);

const decision = ref({
	kt_handover_received: "",
	client_handoff_complete: "",
	code_repository_transferred: 0,
	access_revocation_requested: [],
	access_revocation_not_applicable: 0,
	manager_remarks: "",
});

const canAct = computed(() => (clearance.value?.actions || []).includes("Complete"));

// Set only by this user's own click, cleared on re-entry, so it never claims
// credit for a decision somebody else made.
const justCompleted = ref(false);

// Mirrors the controller rule so the option is not offered and then refused.
const handoverProvided = computed(
	() =>
		!!(clearance.value?.handover_documents || []).length &&
		!!clearance.value?.primary_successor,
);

const canComplete = computed(() => {
	const d = decision.value;
	const revocationAnswered =
		d.access_revocation_not_applicable || d.access_revocation_requested.length > 0;
	return !!d.kt_handover_received && revocationAnswered && !!(d.manager_remarks || "").trim();
});

function toggleNotApplicable(checked) {
	decision.value.access_revocation_not_applicable = checked ? 1 : 0;
	// The server rejects listing systems AND marking N/A, so clear one here.
	if (checked) decision.value.access_revocation_requested = [];
}

function goBack() {
	if (window.history.length > 2) window.history.back();
	else ionRouter.push({ name: "ResignationApprovals" });
}

const detail = createResource({
	url: "myhr.clearance_api.get_clearance_for_review",
	onSuccess: (data) => {
		clearance.value = data;
		decision.value = {
			kt_handover_received: data.kt_handover_received || "",
			client_handoff_complete: data.client_handoff_complete || "",
			code_repository_transferred: data.code_repository_transferred || 0,
			access_revocation_requested: [...(data.access_revocation_requested || [])],
			access_revocation_not_applicable: data.access_revocation_not_applicable || 0,
			manager_remarks: data.manager_remarks || "",
		};
		loading.value = false;
	},
	onError: (err) => {
		loading.value = false;
		errorMsg.value = err?.messages?.[0] || err?.message || String(err);
	},
});

const completeResource = createResource({ url: "myhr.clearance_api.complete_clearance" });
// One place that decides what the user is told when something fails. Frappe
// puts the useful sentence in `messages[0]`; `message` is often a bare
// exception. The banner and the toast get the same words.
function reportError(err, fallback) {
	const message = err?.messages?.[0] || err?.message || fallback;
	actionError.value = message;
	notify(__("Something went wrong"), message, false);
	return message;
}

async function complete() {
	completing.value = true;
	try {
		// The response is the refreshed view, including the now-empty action
		// list — swapped in directly so the button disappears without a re-fetch.
		clearance.value = await completeResource.submit({
			name: clearance.value.name,
			payload: JSON.stringify(decision.value),
		});
		// State first, notification second — see ResignationApprovals.
		justCompleted.value = true;
		notify(__("Completed"), __("The handover is signed off."));
	} catch (err) {
		reportError(err, __("Could not complete."));
	} finally {
		completing.value = false;
	}
}

onIonViewWillEnter(() => {
	loading.value = true;
	errorMsg.value = "";
	actionError.value = "";
	justCompleted.value = false;
	detail.submit({ name: route.params.name });
});
</script>
