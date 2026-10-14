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
								{{ __("Tax Exemption Declaration") }}
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

					<!-- No payroll period means nothing can be filed at all -->
					<div v-else-if="!period" class="flex-1 px-4 py-16 text-center">
						<FeatherIcon name="calendar" class="h-8 w-8 text-gray-300 mx-auto" />
						<p class="mt-3 text-sm font-bold text-gray-500">
							{{ __("No payroll period is open") }}
						</p>
						<p class="mt-1 text-xs text-gray-400 px-6">
							{{
								__(
									"Payroll has not set up a period covering today. Please contact HR.",
								)
							}}
						</p>
					</div>

					<div v-else class="flex-1 px-4 py-5 sm:p-5 space-y-5">
						<div
							v-if="submitted"
							class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 flex items-start gap-3 text-emerald-800"
						>
							<FeatherIcon name="check-circle" class="h-5 w-5 mt-0.5 shrink-0" />
							<div>
								<div class="text-sm font-black">{{ __("Submitted") }}</div>
								<p class="text-xs font-medium opacity-80 mt-0.5">
									{{
										__(
											"Your declaration for {0} is final. Contact HR to change it.",
											[period.name],
										)
									}}
								</p>
							</div>
						</div>

						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-2"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Payroll Period") }}
							</h2>
							<select
								v-model="chosenPeriod"
								class="w-full rounded-lg border-gray-300 text-sm"
								@change="loadPeriod"
							>
								<option v-for="p in periods" :key="p.name" :value="p.name">
									{{ p.name }}
								</option>
							</select>
							<div class="text-[11px] font-semibold text-gray-400">
								{{ period.start_date }} — {{ period.end_date }}
							</div>
							<p
								v-if="periods.length < 2"
								class="text-[11px] text-gray-400 font-medium"
							>
								{{ __("Only one period has been set up.") }}
							</p>
							<p
								v-if="!hasSalaryStructure"
								class="text-[11px] font-bold text-amber-700 pt-1"
							>
								{{
									__(
										"You had no salary structure during this period, so a declaration for it cannot be submitted. You can still save a draft.",
									)
								}}
							</p>
						</section>

						<!-- Declarations -->
						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<div class="flex items-center justify-between">
								<h2
									class="text-xs font-black uppercase tracking-widest text-gray-500"
								>
									{{ __("Declarations") }}
								</h2>
								<Button
									v-if="editable && subCategories.length"
									variant="subtle"
									size="sm"
									@click="addRow"
								>
									{{ __("Add") }}
								</Button>
							</div>

							<p
								v-if="!subCategories.length"
								class="text-xs font-bold text-amber-700"
							>
								{{
									__(
										"No exemption categories have been set up yet. Please contact HR.",
									)
								}}
							</p>

							<p v-else-if="!rows.length" class="text-xs text-gray-400 font-medium">
								{{ __("Add each exemption you intend to claim this year.") }}
							</p>

							<div
								v-for="(row, i) in rows"
								:key="i"
								class="rounded-xl border border-gray-100 bg-gray-50/60 p-3 space-y-2"
							>
								<div class="flex items-center gap-2">
									<select
										v-model="row.exemption_sub_category"
										:disabled="!editable"
										class="flex-1 rounded-lg border-gray-300 text-sm disabled:bg-gray-50"
										@change="onCategoryChange(row)"
									>
										<option value="">{{ __("Select a category") }}</option>
										<option
											v-for="sc in subCategories"
											:key="sc.name"
											:value="sc.name"
										>
											{{ sc.name }}
										</option>
									</select>
									<button
										v-if="editable"
										type="button"
										@click="rows.splice(i, 1)"
										class="p-2 text-gray-400 hover:text-red-600"
									>
										<FeatherIcon name="trash-2" class="h-4 w-4" />
									</button>
								</div>

								<div
									v-if="row.exemption_category"
									class="text-[11px] font-semibold text-gray-400"
								>
									{{ row.exemption_category }}
									<span v-if="row.max_amount">
										· {{ __("Max") }} {{ money(row.max_amount) }}
									</span>
								</div>

								<input
									type="number"
									min="0"
									v-model="row.amount"
									:disabled="!editable"
									:placeholder="__('Amount you will claim')"
									class="w-full rounded-lg border-gray-300 text-sm disabled:bg-gray-50"
								/>
								<p v-if="overMax(row)" class="text-[11px] font-bold text-amber-700">
									{{
										__("Above the {0} limit for this category.", [
											money(row.max_amount),
										])
									}}
								</p>
							</div>
						</section>

						<!-- HRA, only when payroll can compute it -->
						<section
							v-if="hraAvailable"
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-4"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("House Rent (HRA)") }}
							</h2>
							<div>
								<label class="block text-xs font-bold text-gray-600 mb-1">
									{{ __("Monthly House Rent") }}
								</label>
								<input
									type="number"
									min="0"
									v-model="form.monthly_house_rent"
									:disabled="!editable"
									class="w-full rounded-lg border-gray-300 text-sm disabled:bg-gray-50"
								/>
							</div>
							<label class="flex items-center gap-2 cursor-pointer">
								<input
									type="checkbox"
									:checked="!!form.rented_in_metro_city"
									:disabled="!editable"
									@change="
										form.rented_in_metro_city = $event.target.checked ? 1 : 0
									"
									class="h-4 w-4 rounded border-gray-300"
								/>
								<span class="text-sm font-semibold text-gray-800">
									{{ __("I rent in a metro city") }}
								</span>
							</label>
							<div v-if="declaration?.annual_hra_exemption" class="pt-1">
								<Row
									:label="__('Annual HRA Exemption')"
									:value="money(declaration.annual_hra_exemption)"
								/>
							</div>
						</section>

						<!-- Totals -->
						<section
							v-if="declaration"
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Totals") }}
							</h2>
							<Row
								:label="__('Total Declared')"
								:value="money(declaration.total_declared_amount)"
							/>
							<Row
								:label="__('Total Exemption')"
								:value="money(declaration.total_exemption_amount)"
							/>
							<p class="text-[11px] text-gray-400 font-medium pt-1">
								{{ __("Calculated by payroll from what you declared.") }}
							</p>
						</section>
					</div>

					<div
						v-if="!loading && period && editable"
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
						<div class="flex gap-3">
							<Button
								class="w-full py-5"
								variant="subtle"
								:loading="saving"
								@click="save(false)"
							>
								{{ __("Save Draft") }}
							</Button>
							<Button
								class="w-full py-5"
								variant="solid"
								:loading="submitting"
								:disabled="!canSubmit"
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

function money(value) {
	return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value || 0);
}

const Row = (props) =>
	h("div", { class: "flex items-start justify-between gap-3" }, [
		h("span", { class: "text-xs font-bold text-gray-500 shrink-0" }, props.label),
		h("span", { class: "text-sm font-bold text-gray-900 text-right" }, props.value),
	]);
Row.props = ["label", "value"];

const loading = ref(true);
const saving = ref(false);
const submitting = ref(false);
const errorMsg = ref("");
const actionError = ref("");

const period = ref(null);
const periods = ref([]);
const chosenPeriod = ref(null);
const subCategories = ref([]);
const declaration = ref(null);
const hraAvailable = ref(false);
const hasSalaryStructure = ref(true);
const rows = ref([]);
const form = ref({ monthly_house_rent: 0, rented_in_metro_city: 0 });

const submitted = computed(() => !!declaration.value?.submitted);
const editable = computed(() => !submitted.value);
const statusLabel = computed(() => {
	if (!period.value) return __("Unavailable");
	if (submitted.value) return __("Submitted");
	return declaration.value ? __("Draft") : __("Not started");
});

// At least one complete row, or some rent — otherwise there is nothing to file.
const canSubmit = computed(() => {
	// No salary structure for the period means HRMS will refuse the submit, so
	// the button stays disabled rather than offering an action that cannot work.
	if (!hasSalaryStructure.value) return false;
	const complete = rows.value.some((r) => r.exemption_sub_category && Number(r.amount) > 0);
	return complete || Number(form.value.monthly_house_rent) > 0;
});

function overMax(row) {
	return row.max_amount && Number(row.amount) > Number(row.max_amount);
}

function addRow() {
	rows.value.push({
		exemption_sub_category: "",
		exemption_category: "",
		max_amount: 0,
		amount: 0,
	});
}

function onCategoryChange(row) {
	// Mirror the Desk form: picking a sub category brings its category and
	// ceiling with it. The server fetches these again on save, so this is only
	// so the employee can see the limit before they type an amount.
	const picked = subCategories.value.find((sc) => sc.name === row.exemption_sub_category);
	row.exemption_category = picked?.exemption_category || "";
	row.max_amount = picked?.max_amount || 0;
}

function goBack() {
	if (window.history.length > 2) window.history.back();
	else ionRouter.push({ name: "TaxDeclaration" });
}

function hydrate(data) {
	period.value = data?.payroll_period || null;
	periods.value = data?.payroll_periods || [];
	chosenPeriod.value = period.value?.name || null;
	subCategories.value = data?.sub_categories || [];
	hraAvailable.value = !!data?.hra_available;
	hasSalaryStructure.value = !!data?.has_salary_structure;
	declaration.value = data?.declaration || null;

	rows.value = (declaration.value?.declarations || []).map((r) => ({ ...r }));
	form.value = {
		monthly_house_rent: declaration.value?.monthly_house_rent || 0,
		rented_in_metro_city: declaration.value?.rented_in_metro_city || 0,
	};
	loading.value = false;
}

// Switching period reloads everything: a declaration belongs to one period, so
// the rows, totals and submitted state all change with it.
function loadPeriod() {
	loading.value = true;
	actionError.value = "";
	resource.submit({ payroll_period: chosenPeriod.value });
}

const resource = createResource({
	url: "myhr.tax_declaration_api.get_my_tax_declaration",
	onSuccess: hydrate,
	onError: (err) => {
		loading.value = false;
		errorMsg.value = err?.messages?.[0] || err?.message || String(err);
	},
});

const saveResource = createResource({ url: "myhr.tax_declaration_api.save_my_tax_declaration" });

async function save(isSubmit) {
	const incomplete = rows.value.findIndex(
		(r) => r.exemption_sub_category && !(Number(r.amount) > 0),
	);
	if (incomplete !== -1) {
		const message = __("Give declaration {0} an amount.", [incomplete + 1]);
		actionError.value = message;
		notify(__("Not ready"), message, false);
		return;
	}

	const busy = isSubmit ? submitting : saving;
	busy.value = true;
	actionError.value = "";
	try {
		const result = await saveResource.submit({
			payload: JSON.stringify({
				declarations: rows.value.filter((r) => r.exemption_sub_category),
				...form.value,
			}),
			submit: isSubmit ? 1 : 0,
			payroll_period: chosenPeriod.value,
		});
		// State first, notification second.
		declaration.value = result;
		rows.value = (result.declarations || []).map((r) => ({ ...r }));
		notify(
			isSubmit ? __("Submitted") : __("Draft saved"),
			isSubmit ? __("Your declaration is final.") : __("You can come back to it."),
		);
	} catch (err) {
		const message = err?.messages?.[0] || err?.message || __("Could not save.");
		actionError.value = message;
		notify(__("Something went wrong"), message, false);
	} finally {
		busy.value = false;
	}
}

onIonViewWillEnter(() => {
	loading.value = true;
	errorMsg.value = "";
	actionError.value = "";
	resource.reload();
});
</script>
