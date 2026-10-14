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
								{{ __("Full & Final Settlement") }}
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

					<div v-else-if="!settlement" class="flex-1 px-4 py-16 text-center">
						<FeatherIcon name="file-text" class="h-8 w-8 text-gray-300 mx-auto" />
						<p class="mt-3 text-sm font-bold text-gray-500">
							{{ __("Your settlement has not been prepared yet") }}
						</p>
						<p class="mt-1 text-xs text-gray-400 px-6">
							{{ __("Finance prepares this once your clearances are complete.") }}
						</p>
					</div>

					<div v-else class="flex-1 px-4 py-5 sm:p-5 space-y-5">
						<!-- The headline number -->
						<section
							class="rounded-2xl border p-5 text-center"
							:class="
								netPositive
									? 'border-emerald-200 bg-emerald-50'
									: 'border-amber-200 bg-amber-50'
							"
						>
							<div
								class="text-[10px] font-black uppercase tracking-widest"
								:class="netPositive ? 'text-emerald-700' : 'text-amber-700'"
							>
								{{
									netPositive ? __("Payable To You") : __("Recoverable From You")
								}}
							</div>
							<div
								class="mt-1 text-3xl font-black"
								:class="netPositive ? 'text-emerald-900' : 'text-amber-900'"
							>
								{{ money(Math.abs(settlement.net_payable || 0)) }}
							</div>
							<div
								v-if="!settlement.finalised"
								class="mt-2 text-[11px] font-bold text-gray-500"
							>
								{{ __("Provisional — Finance has not finalised this yet.") }}
							</div>
						</section>

						<!-- What you are owed -->
						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-2"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Owed To You") }}
							</h2>
							<LineItem v-for="(r, i) in settlement.payables" :key="i" :row="r" />
							<p
								v-if="!settlement.payables.length"
								class="text-xs text-gray-400 font-medium"
							>
								{{ __("Nothing listed yet.") }}
							</p>
							<div class="flex justify-between pt-2 border-t border-gray-100">
								<span
									class="text-xs font-black uppercase tracking-widest text-gray-500"
								>
									{{ __("Total") }}
								</span>
								<span class="text-sm font-black text-gray-900">
									{{ money(settlement.total_payable_amount) }}
								</span>
							</div>
						</section>

						<!-- What is being taken back -->
						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-2"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Recovered From You") }}
							</h2>
							<LineItem v-for="(r, i) in settlement.receivables" :key="i" :row="r" />
							<p
								v-if="!settlement.receivables.length"
								class="text-xs text-gray-400 font-medium"
							>
								{{ __("Nothing being recovered.") }}
							</p>
							<div class="flex justify-between pt-2 border-t border-gray-100">
								<span
									class="text-xs font-black uppercase tracking-widest text-gray-500"
								>
									{{ __("Total") }}
								</span>
								<span class="text-sm font-black text-gray-900">
									{{ money(settlement.total_receivable_amount) }}
								</span>
							</div>
							<p
								v-if="settlement.notice_period_shortfall_days"
								class="text-[11px] font-medium text-gray-400 pt-1"
							>
								{{
									__(
										"Includes a shortfall of {0} days against your approved relieving date.",
										[settlement.notice_period_shortfall_days],
									)
								}}
							</p>
						</section>

						<section
							v-if="settlement.finance_remarks"
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4"
						>
							<h2
								class="text-xs font-black uppercase tracking-widest text-gray-500 mb-2"
							>
								{{ __("Finance Note") }}
							</h2>
							<p class="text-sm text-gray-700">{{ settlement.finance_remarks }}</p>
						</section>

						<p class="text-[11px] text-gray-400 font-medium text-center px-6">
							{{
								__(
									"If anything here looks wrong, raise it with HR before your last working day.",
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

function money(value) {
	return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value || 0);
}

const LineItem = (props) =>
	h("div", { class: "flex items-start justify-between gap-3 py-1" }, [
		h("div", { class: "min-w-0" }, [
			h(
				"div",
				{ class: "text-sm font-semibold text-gray-900 truncate" },
				props.row.component,
			),
			props.row.remark
				? h("div", { class: "text-[11px] text-gray-400 truncate" }, props.row.remark)
				: null,
		]),
		h("div", { class: "text-right shrink-0" }, [
			h("div", { class: "text-sm font-bold text-gray-900" }, money(props.row.amount)),
			h(
				"div",
				{
					class:
						"text-[10px] font-black uppercase tracking-widest " +
						(props.row.status === "Settled" ? "text-emerald-600" : "text-gray-400"),
				},
				props.row.status,
			),
		]),
	]);
LineItem.props = ["row"];

const loading = ref(true);
const errorMsg = ref("");
const settlement = ref(null);

// Negative means the recoveries outweigh what is owed — rare, but it happens
// when someone leaves owing an advance, and the screen must not imply a payout.
const netPositive = computed(() => (settlement.value?.net_payable || 0) >= 0);

const statusLabel = computed(() => {
	if (!settlement.value) return __("Not prepared");
	return settlement.value.finalised
		? settlement.value.status || __("Finalised")
		: __("In progress");
});

function goBack() {
	if (window.history.length > 2) window.history.back();
	else ionRouter.push({ name: "Resignation" });
}

const resource = createResource({
	url: "myhr.clearance_api.get_my_settlement",
	onSuccess: (data) => {
		settlement.value = data?.exists ? data.settlement : null;
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
