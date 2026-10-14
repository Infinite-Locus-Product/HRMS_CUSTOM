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
								{{ __("Tax Declaration") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span class="text-[10px] font-bold uppercase tracking-widest">
									{{ __("Your choices for this year") }}
								</span>
							</div>
						</div>
					</div>

					<div class="flex-1 px-4 py-5 sm:p-5 space-y-3">
						<router-link
							v-for="option in options"
							:key="option.route"
							:to="{ name: option.route }"
							class="flex flex-row p-4 items-center justify-between rounded-2xl bg-white border border-gray-100 shadow-sm hover:bg-blue-50/60 active:bg-blue-100/60 transition-colors"
						>
							<div class="flex flex-row items-center gap-3 grow min-w-0">
								<div class="p-2 rounded-xl border shrink-0" :class="option.tile">
									<FeatherIcon
										:name="option.icon"
										class="h-4 w-4"
										:class="option.iconClass"
									/>
								</div>
								<div class="min-w-0">
									<div class="text-[15px] font-extrabold text-gray-900 truncate">
										{{ option.title }}
									</div>
									<div class="text-[11px] font-semibold text-gray-400 truncate">
										{{ option.subtitle }}
									</div>
								</div>
							</div>
							<FeatherIcon
								name="chevron-right"
								class="h-4 w-4 text-gray-300 shrink-0"
							/>
						</router-link>

						<p class="text-[11px] text-gray-400 font-medium text-center px-6 pt-2">
							{{
								__(
									"Your regime choice and declared exemptions decide how much tax is deducted each month.",
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
import { computed, inject } from "vue";
import { Button, FeatherIcon } from "frappe-ui";
import { IonPage, IonContent, useIonRouter } from "@ionic/vue";

const ionRouter = useIonRouter();
const __ = inject("$translate");

const options = computed(() => [
	{
		route: "IncomeTaxSlab",
		icon: "percent",
		title: __("Income Tax Slab"),
		subtitle: __("Choose the regime you want to be taxed under"),
		tile: "bg-blue-50 border-blue-200",
		iconClass: "text-blue-600",
	},
	{
		route: "TaxExemptionDeclaration",
		icon: "file-text",
		title: __("Tax Exemption Declaration"),
		subtitle: __("Declare the exemptions you intend to claim"),
		tile: "bg-emerald-50 border-emerald-200",
		iconClass: "text-emerald-600",
	},
]);

function goBack() {
	if (window.history.length > 2) window.history.back();
	else ionRouter.push({ name: "Home" });
}
</script>
