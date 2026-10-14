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
								{{ __("Income Tax Slab") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span class="text-[10px] font-bold uppercase tracking-widest">
									{{ selected || __("Not chosen") }}
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

					<div v-else-if="!slabs.length" class="flex-1 px-4 py-16 text-center">
						<FeatherIcon name="percent" class="h-8 w-8 text-gray-300 mx-auto" />
						<p class="mt-3 text-sm font-bold text-gray-500">
							{{ __("No tax slabs are set up yet") }}
						</p>
						<p class="mt-1 text-xs text-gray-400 px-6">
							{{ __("Payroll has not published any regimes for your company.") }}
						</p>
					</div>

					<div v-else class="flex-1 px-4 py-5 sm:p-5 space-y-3">
						<button
							v-for="slab in slabs"
							:key="slab.name"
							type="button"
							@click="choice = slab.name"
							class="w-full text-left rounded-2xl border p-4 transition-colors"
							:class="
								choice === slab.name
									? 'border-blue-500 bg-blue-50'
									: 'border-gray-100 bg-white hover:bg-gray-50'
							"
						>
							<div class="flex items-start justify-between gap-3">
								<div class="min-w-0">
									<div class="text-[15px] font-extrabold text-gray-900">
										{{ slab.name }}
									</div>
									<div class="text-[11px] font-semibold text-gray-400">
										{{ __("Effective from") }} {{ slab.effective_from }}
									</div>
									<div
										class="mt-1 text-[11px] font-bold"
										:class="
											slab.allow_tax_exemption
												? 'text-emerald-700'
												: 'text-amber-700'
										"
									>
										{{
											slab.allow_tax_exemption
												? __("Exemptions can be claimed")
												: __("No exemptions under this regime")
										}}
									</div>
								</div>
								<FeatherIcon
									v-if="choice === slab.name"
									name="check-circle"
									class="h-5 w-5 text-blue-600 shrink-0"
								/>
							</div>
						</button>

						<p class="text-[11px] text-gray-400 font-medium px-1 pt-2">
							{{
								__(
									"Saved to your employee record and used for tax on every payslip.",
								)
							}}
						</p>
					</div>

					<div
						v-if="!loading && slabs.length"
						class="fixed bottom-0 inset-x-0 sm:max-w-4xl sm:mx-auto bg-white border-t p-4 flex flex-col standalone:pb-safe-bottom z-30"
					>
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
								class="p-0.5 text-red-400"
							>
								<FeatherIcon name="x" class="h-3.5 w-3.5" />
							</button>
						</div>
						<Button
							class="w-full py-5"
							variant="solid"
							:loading="saving"
							:disabled="!choice || choice === selected"
							@click="save"
						>
							{{ choice === selected ? __("Saved") : __("Save Choice") }}
						</Button>
					</div>
				</div>
			</div>
		</IonContent>
	</IonPage>
</template>

<script setup>
import { inject, ref } from "vue";
import { Button, FeatherIcon, LoadingIndicator, createResource, toast } from "frappe-ui";
import { IonPage, IonContent, useIonRouter, onIonViewWillEnter } from "@ionic/vue";

const ionRouter = useIonRouter();
const __ = inject("$translate");

// frappe-ui exports `toast(options)` here — there is no `toast.success`.
function notify(title, text, ok = true) {
	toast({
		title,
		text,
		icon: ok ? "check" : "alert-triangle",
		iconClasses: ok ? "text-green-500" : "text-red-500",
	});
}

const loading = ref(true);
const saving = ref(false);
const errorMsg = ref("");
const actionError = ref("");
const slabs = ref([]);
const selected = ref(null);
const choice = ref(null);

function goBack() {
	if (window.history.length > 2) window.history.back();
	else ionRouter.push({ name: "TaxDeclaration" });
}

const resource = createResource({
	url: "myhr.tax_declaration_api.get_income_tax_slabs",
	onSuccess: (data) => {
		slabs.value = data?.slabs || [];
		selected.value = data?.selected || null;
		choice.value = data?.selected || null;
		loading.value = false;
	},
	onError: (err) => {
		loading.value = false;
		errorMsg.value = err?.messages?.[0] || err?.message || String(err);
	},
});

const saveResource = createResource({ url: "myhr.tax_declaration_api.save_income_tax_slab" });

async function save() {
	saving.value = true;
	actionError.value = "";
	try {
		const result = await saveResource.submit({ slab: choice.value });
		// State first, notification second.
		selected.value = result.selected;
		notify(__("Saved"), __("{0} is now your tax regime.", [result.selected]));
	} catch (err) {
		const message = err?.messages?.[0] || err?.message || __("Could not save your choice.");
		actionError.value = message;
		notify(__("Something went wrong"), message, false);
	} finally {
		saving.value = false;
	}
}

onIonViewWillEnter(() => {
	loading.value = true;
	errorMsg.value = "";
	actionError.value = "";
	resource.reload();
});
</script>
