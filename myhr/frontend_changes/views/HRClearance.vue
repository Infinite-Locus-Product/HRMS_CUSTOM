<template>
	<IonPage>
		<IonContent :fullscreen="true">
			<div class="bg-[#FBFBFC] min-h-screen pb-10">
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
								{{ __("HR Clearance") }}
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

					<div v-else-if="!clearance" class="flex-1 px-4 py-16 text-center">
						<FeatherIcon name="award" class="h-8 w-8 text-gray-300 mx-auto" />
						<p class="mt-3 text-sm font-bold text-gray-500">
							{{ __("HR has not started your clearance yet") }}
						</p>
					</div>

					<div v-else class="flex-1 px-4 py-5 sm:p-5 space-y-5">
						<!-- The thing the leaver actually came for -->
						<section
							class="rounded-2xl border p-5 text-center"
							:class="
								clearance.letter_ready
									? 'border-emerald-200 bg-emerald-50'
									: 'border-gray-200 bg-gray-50'
							"
						>
							<FeatherIcon
								:name="clearance.letter_ready ? 'check-circle' : 'clock'"
								class="h-7 w-7 mx-auto"
								:class="
									clearance.letter_ready ? 'text-emerald-600' : 'text-gray-400'
								"
							/>
							<div
								class="mt-2 text-sm font-black"
								:class="
									clearance.letter_ready ? 'text-emerald-900' : 'text-gray-700'
								"
							>
								{{ __("Relieving Letter") }}
							</div>

							<template v-if="clearance.letter_ready">
								<p class="mt-1 text-[11px] font-semibold text-emerald-700">
									{{
										__("Released {0}", [
											formatDate(clearance.relieving_letter_released_on),
										])
									}}
								</p>
								<a
									:href="clearance.relieving_letter"
									target="_blank"
									rel="noopener"
									class="mt-3 inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-white text-sm font-bold"
								>
									<FeatherIcon name="download" class="h-4 w-4" />
									{{ __("Download") }}
								</a>
							</template>

							<p v-else class="mt-1 text-[11px] font-medium text-gray-500 px-4">
								{{ pendingMessage }}
							</p>
						</section>

						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Exit Interview") }}
							</h2>
							<div class="flex items-center justify-between">
								<span class="text-sm font-semibold text-gray-800">
									{{ clearance.exit_interview_status || __("Not scheduled") }}
								</span>
								<span
									class="px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest"
									:class="
										clearance.exit_interview_done
											? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
											: 'bg-gray-50 text-gray-500 border border-gray-200'
									"
								>
									{{ clearance.exit_interview_done ? __("Done") : __("Pending") }}
								</span>
							</div>
						</section>

						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Items To Return") }}
							</h2>
							<div
								v-for="item in clearance.physical_assets"
								:key="item.label"
								class="flex items-center justify-between"
							>
								<span class="text-sm font-semibold text-gray-800">{{
									item.label
								}}</span>
								<span
									class="px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest"
									:class="statusClass(item.value)"
								>
									{{ item.value || __("Pending") }}
								</span>
							</div>
							<div
								v-if="clearance.asset_damage_recovery_amount"
								class="flex items-center justify-between pt-2 border-t border-gray-100"
							>
								<span class="text-xs font-bold text-amber-700">
									{{ __("Damage Recovery") }}
								</span>
								<span class="text-sm font-black text-amber-800">
									{{ money(clearance.asset_damage_recovery_amount) }}
								</span>
							</div>
						</section>

						<p class="text-[11px] text-gray-400 font-medium text-center px-6">
							{{
								__(
									"Questions about any of this? Speak to HR before your last working day.",
								)
							}}
						</p>
					</div>
				</div>
			</div>
		</IonContent>
	</IonPage>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import { Button, FeatherIcon, LoadingIndicator, createResource } from "frappe-ui";
import { IonPage, IonContent, useIonRouter, onIonViewWillEnter } from "@ionic/vue";

const ionRouter = useIonRouter();
const __ = inject("$translate");
// The app provides a configured dayjs (plugins, locale); use it rather than a
// fresh import, as every other view here does.
const dayjs = inject("$dayjs");

const loading = ref(true);
const errorMsg = ref("");
const clearance = ref(null);

function money(value) {
	return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value || 0);
}

function formatDate(value) {
	return value ? dayjs(value).format("D MMM YYYY") : "";
}

function statusClass(value) {
	if (value === "Yes") return "bg-emerald-50 text-emerald-700 border border-emerald-200";
	if (value === "No") return "bg-red-50 text-red-700 border border-red-200";
	if (value) return "bg-gray-50 text-gray-500 border border-gray-200";
	return "bg-amber-50 text-amber-700 border border-amber-200";
}

const statusLabel = computed(() => {
	if (!clearance.value) return __("Not started");
	return clearance.value.letter_ready ? __("Released") : __("In progress");
});

// Deliberately vague about WHY. The internal blockers — a re-hire field HR has
// not filled in, for instance — are none of the leaver's business; the date is.
const pendingMessage = computed(() => {
	const lwd = clearance.value?.last_working_day;
	if (lwd && dayjs().isBefore(dayjs(lwd), "day")) {
		return __("Available from {0}, once your clearances are complete.", [formatDate(lwd)]);
	}
	return __("HR is completing your clearance. It will appear here once released.");
});

function goBack() {
	if (window.history.length > 2) window.history.back();
	else ionRouter.push({ name: "Resignation" });
}

const resource = createResource({
	url: "myhr.clearance_api.get_my_hr_clearance",
	onSuccess: (data) => {
		clearance.value = data?.exists ? data.clearance : null;
		loading.value = false;
	},
	onError: (err) => {
		loading.value = false;
		errorMsg.value = err?.messages?.[0] || err?.message || String(err);
	},
});

onIonViewWillEnter(() => {
	loading.value = true;
	errorMsg.value = "";
	resource.reload();
});
</script>
