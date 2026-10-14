<template>
	<IonPage>
		<IonContent :fullscreen="true">
			<div class="bg-[#FBFBFC] min-h-screen pb-[120px]">
				<!-- Centred column, same width contract as the Leave Application form -->
				<div
					class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative"
				>
					<!-- Glassy sticky header (Action-Centre pattern) -->
					<div
						class="flex flex-row bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100 items-center gap-1"
					>
						<Button
							variant="ghost"
							class="!px-2 hover:bg-gray-100 transition-colors"
							@click="goBack"
						>
							<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
						</Button>
						<div class="flex flex-col ml-1 overflow-hidden">
							<h2
								class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1"
							>
								{{ __("Resignation") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span class="text-[10px] font-bold uppercase tracking-widest">
									{{ statusLabel }}
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
						<!-- Who is resigning -->
						<section
							class="rounded-2xl border border-gray-100 bg-gradient-to-br from-blue-600 to-blue-700 p-4 text-white shadow-sm"
						>
							<div class="flex items-center gap-3">
								<div
									class="h-11 w-11 rounded-full bg-white/20 flex items-center justify-center text-base font-black shrink-0"
								>
									{{ initials }}
								</div>
								<div class="min-w-0">
									<div
										class="text-[10px] font-bold uppercase tracking-widest opacity-75"
									>
										{{ info.name }}
									</div>
									<div class="text-lg font-extrabold truncate leading-tight">
										{{ info.employee_name }}
									</div>
									<div class="text-[11px] font-semibold opacity-80 truncate">
										{{
											[info.designation, info.department]
												.filter(Boolean)
												.join(" · ") || "—"
										}}
									</div>
								</div>
							</div>
							<div class="mt-3 pt-3 border-t border-white/20 grid grid-cols-2 gap-3">
								<div class="min-w-0">
									<div
										class="text-[10px] font-bold uppercase tracking-widest opacity-70"
									>
										{{ __("Date of Joining") }}
									</div>
									<div class="text-sm font-bold truncate">
										{{ info.date_of_joining || "—" }}
									</div>
								</div>
								<div class="min-w-0">
									<div
										class="text-[10px] font-bold uppercase tracking-widest opacity-70"
									>
										{{ __("Company") }}
									</div>
									<div class="text-sm font-bold truncate">
										{{ info.company || "—" }}
									</div>
								</div>
							</div>
						</section>

						<!-- Status banner once it is with an approver -->
						<div
							v-if="existing && !isEditable"
							class="rounded-2xl border p-4"
							:class="bannerClass"
						>
							<div class="flex items-center gap-2">
								<FeatherIcon :name="bannerIcon" class="h-5 w-5" />
								<span class="text-sm font-black">{{ statusLabel }}</span>
							</div>
							<p
								v-if="existing.custom_rejection_hold_reason"
								class="mt-2 text-xs font-medium"
							>
								{{ existing.custom_rejection_hold_reason }}
							</p>
						</div>

						<!-- Who this goes to -->
						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Approval Chain") }}
							</h2>
							<ReadOnlyRow
								:label="__('Reporting Manager (L1)')"
								:value="info.reporting_manager"
							/>
							<ReadOnlyRow
								:label="__('Function Head / L2')"
								:value="info.l2_manager"
							/>
							<ReadOnlyRow
								:label="__('Notice Period')"
								:value="`${info.notice_period_days || 0} ${__('days')}`"
							/>
						</section>

						<!-- The employee's part -->
						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-4"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Resignation Details") }}
							</h2>

							<div>
								<label class="block text-xs font-bold text-gray-600 mb-1">
									{{ __("Resignation Reason") }}
									<span class="text-red-500">*</span>
								</label>
								<select
									v-model="form.custom_resignation_reason"
									:disabled="!isEditable"
									class="w-full rounded-lg border-gray-300 text-sm disabled:bg-gray-50 disabled:text-gray-500"
								>
									<option value="">{{ __("Select a reason") }}</option>
									<option
										v-for="opt in options.resignation_reason"
										:key="opt"
										:value="opt"
									>
										{{ opt }}
									</option>
								</select>
							</div>

							<div>
								<label class="block text-xs font-bold text-gray-600 mb-1">
									{{ __("Detailed Reason") }}
								</label>
								<textarea
									v-model="form.custom_detailed_reason"
									:disabled="!isEditable"
									rows="4"
									:maxlength="maxChars"
									class="w-full rounded-lg border-gray-300 text-sm disabled:bg-gray-50 disabled:text-gray-500"
								/>
								<p
									class="mt-1 text-[11px] font-medium"
									:class="overLimit ? 'text-red-600' : 'text-gray-400'"
								>
									{{ charCount }} / {{ maxChars }}
								</p>
							</div>

							<div>
								<label class="block text-xs font-bold text-gray-600 mb-1">
									{{ __("Requested Relieving Date") }}
									<span class="text-red-500">*</span>
								</label>
								<input
									type="date"
									v-model="form.custom_requested_relieving_date"
									:disabled="!isEditable"
									:min="defaults.min_relieving_date"
									class="w-full rounded-lg border-gray-300 text-sm disabled:bg-gray-50 disabled:text-gray-500"
								/>
							</div>

							<div>
								<label class="block text-xs font-bold text-gray-600 mb-1">
									{{ __("Buy-out Notice Period?") }}
									<span class="text-red-500">*</span>
								</label>
								<select
									v-model="form.custom_buyout_notice_period"
									:disabled="!isEditable"
									class="w-full rounded-lg border-gray-300 text-sm disabled:bg-gray-50 disabled:text-gray-500"
								>
									<option value="">{{ __("Select") }}</option>
									<option v-for="opt in options.buyout" :key="opt" :value="opt">
										{{ opt }}
									</option>
								</select>
							</div>

							<div v-if="form.custom_buyout_notice_period === 'Yes'">
								<label class="block text-xs font-bold text-gray-600 mb-1">
									{{ __("Buy-out Amount") }} <span class="text-red-500">*</span>
								</label>
								<input
									type="number"
									min="0"
									v-model="form.custom_buyout_amount"
									:disabled="!isEditable"
									class="w-full rounded-lg border-gray-300 text-sm disabled:bg-gray-50 disabled:text-gray-500"
								/>
							</div>
						</section>

						<!-- What comes next, once the resignation is approved -->
						<section v-if="isApproved" class="space-y-3">
							<h2
								class="text-xs font-black uppercase tracking-widest text-gray-500 px-1"
							>
								{{ __("Your Clearances") }}
							</h2>
							<router-link
								v-for="link in clearanceLinks"
								:key="link.route"
								:to="{ name: link.route }"
								class="flex flex-row p-4 items-center justify-between rounded-2xl bg-white border border-gray-100 shadow-sm hover:bg-blue-50/60 active:bg-blue-100/60 transition-colors"
							>
								<div class="flex flex-row items-center gap-3 grow min-w-0">
									<div class="p-2 rounded-xl border shrink-0" :class="link.tile">
										<FeatherIcon
											:name="link.icon"
											class="h-4 w-4"
											:class="link.iconClass"
										/>
									</div>
									<div class="min-w-0">
										<div
											class="text-[15px] font-extrabold text-gray-900 truncate"
										>
											{{ link.title }}
										</div>
										<div
											class="text-[11px] font-semibold text-gray-400 truncate"
										>
											{{ link.subtitle }}
										</div>
									</div>
								</div>
								<FeatherIcon
									name="chevron-right"
									class="h-4 w-4 text-gray-300 shrink-0"
								/>
							</router-link>
						</section>

						<!-- Computed by the server; shown so the numbers are not a surprise -->
						<section
							v-if="existing"
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Calculated") }}
							</h2>
							<ReadOnlyRow
								:label="__('Official End Date')"
								:value="existing.custom_official_end_date"
							/>
							<ReadOnlyRow
								:label="__('Notice Period Shortfall')"
								:value="`${existing.custom_notice_period_shortfall || 0} ${__('days')}`"
							/>
						</section>

						<!-- Approver's part. Always read-only here. -->
						<section
							v-if="existing"
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Approval Decision") }}
							</h2>
							<ReadOnlyRow
								:label="__('Decision')"
								:value="existing.custom_decision"
							/>
							<ReadOnlyRow
								:label="__('Approved Relieving Date')"
								:value="existing.custom_approved_relieving_date"
							/>
							<ReadOnlyRow
								:label="__('Notice Period Waiver')"
								:value="existing.custom_notice_period_waiver"
							/>
							<ReadOnlyRow
								:label="__('L1 Approved')"
								:value="existing.custom_l1_approved ? __('Yes') : __('No')"
							/>
							<ReadOnlyRow
								:label="__('L2 Approved')"
								:value="existing.custom_l2_approved ? __('Yes') : __('No')"
							/>
						</section>
					</div>

					<!-- Actions -->
					<div
						v-if="!loading && !errorMsg && isEditable"
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
								class="w-full py-5"
								:loading="saving"
								@click="save(false)"
								variant="subtle"
							>
								{{ __("Save Draft") }}
							</Button>
							<Button
								class="w-full py-5"
								:loading="submitting"
								variant="solid"
								@click="save(true)"
							>
								{{ __("Submit") }}
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

// Tiny presentational helper — a label/value line, used a dozen times above.
const ReadOnlyRow = (props) =>
	h("div", { class: "flex items-start justify-between gap-3" }, [
		h("span", { class: "text-xs font-bold text-gray-500 shrink-0" }, props.label),
		h("span", { class: "text-sm font-semibold text-gray-900 text-right" }, props.value || "—"),
	]);
ReadOnlyRow.props = ["label", "value"];

const loading = ref(true);
const saving = ref(false);
const submitting = ref(false);
const actionError = ref("");
const errorMsg = ref("");

const info = ref({});
const defaults = ref({});
const options = ref({ resignation_reason: [], buyout: [] });
const existing = ref(null);
const maxChars = ref(500);

const form = ref({
	custom_resignation_reason: "",
	custom_detailed_reason: "",
	custom_requested_relieving_date: "",
	custom_buyout_notice_period: "",
	custom_buyout_amount: null,
});

// Editable while the employee still owns it: before filing, or after a rejection.
const isEditable = computed(() => !existing.value || existing.value.editable);
const charCount = computed(() => (form.value.custom_detailed_reason || "").length);
const overLimit = computed(() => charCount.value > maxChars.value);

const initials = computed(
	() =>
		(info.value.employee_name || "")
			.split(" ")
			.filter(Boolean)
			.slice(0, 2)
			.map((part) => part[0].toUpperCase())
			.join("") || "—",
);

// The clearances only mean anything once the resignation is fully approved.
const isApproved = computed(() => existing.value?.workflow_state === "Approved");

const clearanceLinks = computed(() => [
	{
		route: "Handover",
		icon: "package",
		title: __("Handover & Clearance"),
		subtitle: __("Documents, successor and your confirmations"),
		tile: "bg-blue-50 border-blue-200",
		iconClass: "text-blue-600",
	},
	{
		route: "ITClearance",
		icon: "monitor",
		title: __("IT Clearance"),
		subtitle: __("Hardware, access and any recovery amount"),
		tile: "bg-emerald-50 border-emerald-200",
		iconClass: "text-emerald-600",
	},
	{
		route: "HRClearance",
		icon: "award",
		title: __("HR Clearance"),
		subtitle: __("Exit interview, items to return, relieving letter"),
		tile: "bg-purple-50 border-purple-200",
		iconClass: "text-purple-600",
	},
	{
		route: "Settlement",
		icon: "file-text",
		title: __("Full & Final Settlement"),
		subtitle: __("What you are owed, and what is being recovered"),
		tile: "bg-amber-50 border-amber-200",
		iconClass: "text-amber-600",
	},
]);

const statusLabel = computed(() => {
	if (!existing.value) return __("Not yet filed");
	return existing.value.workflow_state || __("Draft");
});

const bannerClass = computed(() => {
	const state = existing.value?.workflow_state;
	if (state === "Rejected") return "bg-red-50 border-red-200 text-red-800";
	if (state === "Approved") return "bg-green-50 border-green-200 text-green-800";
	return "bg-blue-50 border-blue-200 text-blue-800";
});

const bannerIcon = computed(() => {
	const state = existing.value?.workflow_state;
	if (state === "Rejected") return "x-circle";
	if (state === "Approved") return "check-circle";
	return "clock";
});

function goBack() {
	if (window.history.length > 2) window.history.back();
	else ionRouter.push({ name: "Profile" });
}

function hydrate(data) {
	info.value = data?.employee || {};
	defaults.value = data?.defaults || {};
	options.value = data?.options || { resignation_reason: [], buyout: [] };
	maxChars.value = data?.options?.max_detailed_reason_chars || 500;
	existing.value = data?.existing || null;

	if (existing.value) {
		for (const key of Object.keys(form.value)) {
			form.value[key] = existing.value[key] ?? form.value[key];
		}
	} else if (defaults.value.requested_relieving_date) {
		form.value.custom_requested_relieving_date = defaults.value.requested_relieving_date;
	}
	loading.value = false;
}

const resignation = createResource({
	url: "myhr.resignation_api.get_my_resignation",
	onSuccess: hydrate,
	onError: (err) => {
		loading.value = false;
		errorMsg.value = err?.messages?.[0] || err?.message || String(err);
	},
});

const saveResource = createResource({
	url: "myhr.resignation_api.save_my_resignation",
});
// One place that decides what the user is told when something fails. Frappe
// puts the useful sentence in `messages[0]`; `message` is often a bare
// exception. The banner and the toast get the same words.
function reportError(err, fallback) {
	const message = err?.messages?.[0] || err?.message || fallback;
	actionError.value = message;
	notify(__("Something went wrong"), message, false);
	return message;
}

function validate(isSubmit) {
	if (overLimit.value) return __("Detailed Reason is over the character limit.");
	if (!isSubmit) return null;
	if (!form.value.custom_resignation_reason) return __("Please choose a Resignation Reason.");
	if (!form.value.custom_requested_relieving_date)
		return __("Please choose a Requested Relieving Date.");
	if (!form.value.custom_buyout_notice_period) return __("Please answer Buy-out Notice Period.");
	if (form.value.custom_buyout_notice_period === "Yes" && !form.value.custom_buyout_amount)
		return __("Buy-out Amount is required when buying out the notice period.");
	return null;
}

async function save(isSubmit) {
	const problem = validate(isSubmit);
	if (problem) {
		notify(__("Not ready"), problem, false);
		return;
	}

	const busy = isSubmit ? submitting : saving;
	busy.value = true;
	try {
		const result = await saveResource.submit({
			payload: JSON.stringify(form.value),
			submit: isSubmit ? 1 : 0,
		});
		existing.value = result;
		notify(
			isSubmit ? __("Submitted") : __("Draft saved"),
			isSubmit ? __("Sent to your manager for approval.") : __("You can come back to it."),
		);
		if (isSubmit) resignation.reload();
	} catch (err) {
		// Server-side validate() owns the real rules; surface its message verbatim.
		reportError(err, __("Could not save."));
	} finally {
		busy.value = false;
	}
}

onIonViewWillEnter(() => {
	loading.value = true;
	actionError.value = "";
	resignation.reload();
});
</script>
