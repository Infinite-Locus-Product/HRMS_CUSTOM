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
								{{ __("IT Clearance") }}
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
						<FeatherIcon name="monitor" class="h-8 w-8 text-gray-300 mx-auto" />
						<p class="mt-3 text-sm font-bold text-gray-500">
							{{ __("IT has not recorded anything yet") }}
						</p>
					</div>

					<div v-else class="flex-1 px-4 py-5 sm:p-5 space-y-5">
						<!-- The number that matters most to the reader -->
						<section
							v-if="clearance.total_recovery_amount"
							class="rounded-2xl border border-amber-200 bg-amber-50 p-4"
						>
							<div class="flex items-center gap-2 text-amber-800">
								<FeatherIcon name="alert-triangle" class="h-5 w-5 shrink-0" />
								<span class="text-xs font-black uppercase tracking-widest">
									{{ __("Recovery From Final Settlement") }}
								</span>
							</div>
							<div class="mt-2 text-2xl font-black text-amber-900">
								{{ formatCurrency(clearance.total_recovery_amount) }}
							</div>
							<p class="mt-1 text-xs font-medium text-amber-700">
								{{
									__("Raised against the items marked Damaged or Missing below.")
								}}
							</p>
						</section>

						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Hardware") }}
							</h2>
							<div
								v-for="(asset, i) in clearance.assets"
								:key="i"
								class="flex items-start justify-between gap-3 py-2 border-b border-gray-50 last:border-0"
							>
								<div class="min-w-0">
									<div class="text-sm font-extrabold text-gray-900">
										{{ asset.asset_type }}
									</div>
									<div class="text-[11px] font-semibold text-gray-400">
										{{ asset.returned ? __("Returned") : __("Not returned") }}
										<span v-if="asset.remarks"> · {{ asset.remarks }}</span>
									</div>
								</div>
								<div class="text-right shrink-0">
									<span
										class="px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest"
										:class="conditionClass(asset.asset_condition)"
									>
										{{ asset.asset_condition || __("—") }}
									</span>
									<div
										v-if="asset.recovery_amount"
										class="mt-1 text-xs font-bold text-amber-700"
									>
										{{ formatCurrency(asset.recovery_amount) }}
									</div>
								</div>
							</div>
							<p
								v-if="!clearance.assets.length"
								class="text-xs text-gray-400 font-medium"
							>
								{{ __("No hardware listed.") }}
							</p>
						</section>

						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Access & Mailbox") }}
							</h2>
							<Row
								:label="__('Last Working Day')"
								:value="clearance.last_working_day"
							/>
							<Row
								:label="__('Access Revoked At')"
								:value="clearance.access_revocation_datetime"
							/>
							<Row
								:label="__('Mail Forwarded To')"
								:value="clearance.mailbox_forwarding_address"
							/>
						</section>

						<p class="text-[11px] text-gray-400 font-medium text-center px-6">
							{{
								__(
									"Recorded by IT. If anything here looks wrong, raise it with HR before your last working day.",
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
import { computed, h, inject, ref } from "vue";
import { Button, FeatherIcon, LoadingIndicator, createResource } from "frappe-ui";
import { IonPage, IonContent, useIonRouter, onIonViewWillEnter } from "@ionic/vue";

const ionRouter = useIonRouter();
const __ = inject("$translate");

const Row = (props) =>
	h("div", { class: "flex items-start justify-between gap-3" }, [
		h("span", { class: "text-xs font-bold text-gray-500 shrink-0" }, props.label),
		h("span", { class: "text-sm font-semibold text-gray-900 text-right" }, props.value || "—"),
	]);
Row.props = ["label", "value"];

const loading = ref(true);
const errorMsg = ref("");
const clearance = ref(null);

const statusLabel = computed(() => {
	if (!clearance.value) return __("Nothing recorded");
	return clearance.value.finalised ? __("Finalised") : __("In progress");
});

function conditionClass(condition) {
	if (condition === "Good") return "bg-green-50 text-green-700 border border-green-200";
	if (condition === "Damaged") return "bg-amber-50 text-amber-700 border border-amber-200";
	if (condition === "Missing") return "bg-red-50 text-red-700 border border-red-200";
	return "bg-gray-50 text-gray-500 border border-gray-200";
}

function formatCurrency(value) {
	// Intentionally simple: this screen only ever shows company-currency totals.
	return new Intl.NumberFormat(undefined, {
		maximumFractionDigits: 2,
	}).format(value || 0);
}

function goBack() {
	if (window.history.length > 2) window.history.back();
	else ionRouter.push({ name: "Resignation" });
}

const resource = createResource({
	url: "myhr.clearance_api.get_my_it_clearance",
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
