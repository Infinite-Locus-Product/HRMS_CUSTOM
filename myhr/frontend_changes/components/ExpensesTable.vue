<template>
	<!-- Header -->
	<div class="flex flex-row justify-between items-center mt-2">
		<div class="flex flex-col">
			<h2 class="text-base font-extrabold text-gray-900">
				{{ __("Expenses") }}
			</h2>
			<span
				v-if="expenseClaim.expenses?.length"
				class="text-[10px] font-bold uppercase tracking-widest text-gray-400 mt-0.5"
			>
				{{ expenseClaim.expenses.length }}
				{{ expenseClaim.expenses.length === 1 ? __("item") : __("items") }}
			</span>
		</div>
		<div class="flex flex-row gap-3 items-center">
			<span class="text-base font-extrabold text-gray-900">
				{{ formatCurrency(expenseClaim.total_claimed_amount, expenseClaim.currency) }}
			</span>
			<!-- One-expense-per-claim limit: hide the + add button once a row
			     exists. The server-side validate also rejects >1 row, this
			     is the matching UX so users don't tap a button that throws. -->
			<Button
				v-if="!isReadOnly && !expenseClaim.expenses?.length"
				id="add-expense-modal"
				class="!rounded-xl"
				icon="plus"
				variant="subtle"
				theme="blue"
				@click="openModal()"
			/>
		</div>
	</div>

	<!-- Table -->
	<div
		v-if="expenseClaim.expenses?.length"
		class="flex flex-col bg-white mt-3 rounded-2xl border border-gray-100 shadow-sm overflow-hidden"
	>
		<div class="divide-y divide-gray-100">
			<div
				class="flex flex-row p-4 items-center justify-between cursor-pointer hover:bg-blue-50/40 active:bg-blue-100/40 transition-colors"
				v-for="(item, idx) in expenseClaim.expenses"
				:key="idx"
				@click="openModal(item, idx)"
			>
				<div class="flex flex-row items-center gap-3 flex-1 min-w-0">
					<div
						class="h-9 w-9 rounded-xl flex items-center justify-center shrink-0"
						:class="`${getExpenseTypeMeta(item.expense_type).bg} ${getExpenseTypeMeta(item.expense_type).text}`"
					>
						<FeatherIcon
							:name="getExpenseTypeMeta(item.expense_type).icon"
							class="h-4 w-4"
						/>
					</div>
					<div class="flex flex-col gap-1 min-w-0">
						<div class="text-sm font-bold text-gray-900 truncate">
							{{ __(item.expense_type) || __("Expense") }}
						</div>
						<div class="text-[11px] font-semibold text-gray-500 truncate">
							<span v-if="item.expense_date">{{ dayjs(item.expense_date).format("D MMM") }}</span>
							<span v-if="item.expense_date && item.sanctioned_amount != null"> · </span>
							<span v-if="item.sanctioned_amount != null">
								{{ __("Sanctioned") }} {{ formatCurrency(item.sanctioned_amount || 0, expenseClaim.currency) }}
							</span>
						</div>
					</div>
				</div>
				<div class="flex flex-row items-center gap-2 shrink-0">
					<span class="text-sm font-extrabold text-gray-900 whitespace-nowrap">
						{{ formatCurrency(item.amount, expenseClaim.currency) }}
					</span>
					<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400" />
				</div>
			</div>
		</div>
	</div>

	<!-- Empty state — single bold CTA, oversized + icon so it reads as a
	     primary action rather than a placeholder. -->
	<button
		v-else
		type="button"
		:disabled="isReadOnly"
		@click="!isReadOnly && openModal()"
		class="mt-3 w-full rounded-2xl border border-dashed border-gray-200 bg-gray-50/60 p-8 flex flex-col items-center justify-center gap-3 transition-colors"
		:class="!isReadOnly && 'hover:border-blue-300 hover:bg-blue-50/60 cursor-pointer'"
	>
		<div
			class="h-16 w-16 rounded-3xl bg-white border border-gray-200 flex items-center justify-center text-gray-500 shadow-sm"
		>
			<FeatherIcon name="plus" class="h-9 w-9" stroke-width="2.5" />
		</div>
		<div class="text-base font-bold text-gray-800">
			{{ isReadOnly ? __("No expenses") : __("Claim expense") }}
		</div>
	</button>

	<!-- Full-screen modal — replaces the bottom-sheet drawer with a
	     proper page experience. Each editable concern (category, when,
	     why, how much) is its own section, mirroring the leave-request
	     form pattern. -->
	<ion-modal
		:is-open="isModalOpen"
		@didDismiss="resetSelectedItem()"
	>
		<div class="bg-gray-50 w-full h-full flex flex-col">
			<!-- Top bar -->
			<div class="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100 shrink-0">
				<button
					type="button"
					@click="resetSelectedItem()"
					class="h-9 w-9 rounded-xl bg-gray-100 text-gray-600 flex items-center justify-center hover:bg-gray-200 transition-colors"
				>
					<FeatherIcon name="x" class="h-5 w-5" />
				</button>
				<div class="text-sm font-extrabold text-gray-900 truncate px-3">
					{{ modalTitle }}
				</div>
				<div class="h-9 w-9" />
			</div>

			<!-- Scrollable body. `min-h-0` is required: in a flex-col, items
			     default to `min-height: auto` which lets them grow past the
			     parent's bounded height, so `overflow-y-auto` never triggers
			     and the modal becomes unscrollable when content exceeds the
			     viewport. -->
			<div class="flex-1 min-h-0 overflow-y-auto px-4 py-5">
				<div class="w-full sm:max-w-2xl sm:mx-auto space-y-6">
					<!-- Section: Category -->
					<section v-if="typeChips.length" class="space-y-3">
						<div class="flex items-center gap-3">
							<div class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100">
								<FeatherIcon name="tag" class="h-5 w-5" />
							</div>
							<div class="flex flex-col">
								<h3 class="text-sm font-black text-gray-900 uppercase tracking-[0.1em]">
									{{ __("Category") }}<span class="text-red-500 ml-0.5">*</span>
								</h3>
								<span class="text-[10px] font-bold text-gray-400 uppercase tracking-[0.05em]">
									{{ __("What was this expense for") }}
								</span>
							</div>
						</div>
						<div class="grid grid-cols-3 sm:grid-cols-5 gap-2">
							<button
								v-for="chip in typeChips"
								:key="chip.value"
								type="button"
								:disabled="isReadOnly"
								@click="expenseItem.expense_type = chip.value"
								class="flex flex-col items-center justify-center gap-1.5 py-3 px-2 rounded-2xl border-2 bg-white transition-all"
								:class="[
									expenseItem.expense_type === chip.value
										? `${chip.activeBg} ${chip.activeText} ${chip.activeBorder} shadow-sm`
										: 'border-gray-100 text-gray-600 hover:border-gray-200',
									isReadOnly && 'opacity-60 cursor-not-allowed',
								]"
							>
								<FeatherIcon :name="chip.icon" class="h-5 w-5" />
								<span class="text-[11px] font-bold leading-none">{{ __(chip.label) }}</span>
							</button>
						</div>
					</section>

					<!-- Section: When -->
					<section class="space-y-3">
						<div class="flex items-center gap-3">
							<div class="p-2.5 rounded-xl bg-violet-50 text-violet-600 shadow-sm border border-violet-100">
								<FeatherIcon name="calendar" class="h-5 w-5" />
							</div>
							<div class="flex flex-col">
								<h3 class="text-sm font-black text-gray-900 uppercase tracking-[0.1em]">
									{{ __("When") }}
								</h3>
								<span class="text-[10px] font-bold text-gray-400 uppercase tracking-[0.05em]">
									{{ __("Date the expense occurred") }}
								</span>
							</div>
						</div>
						<div class="rounded-2xl border border-gray-100 bg-white p-3">
							<FormField
								v-if="dateField"
								:label="''"
								:fieldtype="dateField.fieldtype"
								:fieldname="dateField.fieldname"
								:default="dateField.default"
								:readOnly="dateField.read_only || isReadOnly"
								v-model="expenseItem[dateField.fieldname]"
							/>
						</div>
					</section>

					<!-- Section: About — read-only blurb auto-filled from the
					     Expense Claim Type's static description. Hidden entirely
					     when the picked category has no description (or none
					     picked yet) — there's nothing to read. -->
					<section v-if="descField && expenseItem[descField.fieldname]" class="space-y-3">
						<div class="flex items-center gap-3">
							<div class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100">
								<FeatherIcon name="info" class="h-5 w-5" />
							</div>
							<div class="flex flex-col">
								<h3 class="text-sm font-black text-gray-900 uppercase tracking-[0.1em]">
									{{ __("About") }}
								</h3>
							</div>
						</div>
						<div
							class="w-full rounded-2xl border border-gray-200 bg-gray-50 p-4 text-sm font-medium text-gray-700 whitespace-pre-line"
						>
							{{ expenseItem[descField.fieldname] }}
						</div>
					</section>

					<!-- Section: Remarks — writable counterpart to About. Saves
					     to Expense Claim Detail.custom_remarks. -->
					<section v-if="remarksField" class="space-y-3">
						<div class="flex items-center gap-3">
							<div class="p-2.5 rounded-xl bg-amber-50 text-amber-600 shadow-sm border border-amber-100">
								<FeatherIcon name="message-square" class="h-5 w-5" />
							</div>
							<div class="flex flex-col">
								<h3 class="text-sm font-black text-gray-900 uppercase tracking-[0.1em]">
									{{ __("Remarks") }}
								</h3>
								<span class="text-[10px] font-bold text-gray-400 uppercase tracking-[0.05em]">
									{{ __("Your note to the approver") }}
								</span>
							</div>
						</div>
						<textarea
							v-model="expenseItem[remarksField.fieldname]"
							:disabled="isReadOnly"
							:placeholder="__('e.g. Cab to client meeting at HQ')"
							rows="3"
							class="w-full rounded-2xl border border-gray-200 bg-white p-4 text-sm font-medium text-gray-800 focus:border-blue-300 focus:ring-2 focus:ring-blue-100 transition-all resize-none outline-none placeholder:text-gray-400"
						/>
					</section>

					<!-- Section: Amount -->
					<section v-if="amountField" class="space-y-3">
						<div class="flex items-center gap-3">
							<!-- Render the actual currency symbol (₹ / $ / € / …) so the
							     tile reflects the form's currency. Feather doesn't ship a
							     rupee glyph, and a static dollar-sign confused users. -->
							<div class="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 shadow-sm border border-emerald-100 h-10 w-10 flex items-center justify-center">
								<span class="text-lg font-black leading-none">{{ currencySymbol }}</span>
							</div>
							<div class="flex flex-col">
								<h3 class="text-sm font-black text-gray-900 uppercase tracking-[0.1em]">
									{{ __("Amount") }}<span class="text-red-500 ml-0.5">*</span>
								</h3>
								<span class="text-[10px] font-bold text-gray-400 uppercase tracking-[0.05em]">
									{{ __("In") }} {{ props.expenseClaim.currency || "INR" }}
								</span>
							</div>
						</div>
						<div
							class="flex items-center gap-3 rounded-2xl border-2 border-gray-100 bg-white px-5 py-4 focus-within:border-emerald-300 focus-within:ring-4 focus-within:ring-emerald-50 transition-all"
							:class="isReadOnly && 'opacity-60'"
						>
							<span class="text-3xl font-black text-gray-300">{{ currencySymbol }}</span>
							<input
								type="number"
								inputmode="decimal"
								step="0.01"
								:disabled="isReadOnly"
								:value="expenseItem.amount"
								@input="expenseItem.amount = $event.target.value === '' ? null : parseFloat($event.target.value)"
								placeholder="0"
								class="w-full bg-transparent border-0 text-3xl font-black text-gray-900 placeholder-gray-300 focus:outline-none focus:ring-0 p-0"
							/>
						</div>
						<div v-if="!isReadOnly" class="flex flex-wrap gap-2">
							<button
								v-for="qa in quickAmounts"
								:key="qa"
								type="button"
								@click="expenseItem.amount = (parseFloat(expenseItem.amount) || 0) + qa"
								class="px-3.5 py-2 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold hover:bg-emerald-100 transition-colors"
							>
								+ {{ currencySymbol }}{{ qa.toLocaleString() }}
							</button>
							<button
								v-if="expenseItem.amount"
								type="button"
								@click="expenseItem.amount = null"
								class="px-3.5 py-2 rounded-full bg-gray-100 text-gray-500 text-xs font-bold hover:bg-gray-200 transition-colors"
							>
								{{ __("Clear") }}
							</button>
						</div>
					</section>
				</div>
			</div>

			<!-- Footer actions — sticky at the bottom of the screen.
		     Brand-blue primary + neutral outline secondary
		     (see docs/DESIGN_SYSTEM.md §Buttons). -->
			<div
				v-if="!isReadOnly"
				class="px-4 py-3 bg-white border-t border-gray-100 flex flex-row items-center gap-3 shrink-0"
				:style="{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }"
			>
				<button
					v-if="editingIdx !== null"
					type="button"
					@click="deleteExpenseItem()"
					class="px-5 py-4 rounded-2xl bg-red-50 text-red-600 border border-red-100 font-black text-xs uppercase tracking-widest hover:bg-red-100 active:scale-[0.98] transition-all flex items-center justify-center gap-2 shrink-0"
				>
					<FeatherIcon name="trash-2" class="h-4 w-4" />
					{{ __("Delete") }}
				</button>
				<button
					type="button"
					@click="updateExpenseItem()"
					:disabled="addButtonDisabled"
					class="w-full py-4 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<FeatherIcon
						:name="editingIdx === null ? 'plus' : 'check'"
						class="h-4 w-4"
					/>
					{{ editingIdx === null ? __("Add Expense") : __("Update Expense") }}
				</button>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { Button, FeatherIcon, createResource } from "frappe-ui"
import { computed, ref, watch, inject } from "vue"
import { IonModal } from "@ionic/vue"

import FormField from "@/components/FormField.vue"

import { claimTypesByID } from "@/data/claims"
import {
	EXPENSE_TYPE_META,
	getExpenseTypeMeta,
	getCurrencySymbol,
} from "@/data/expenseClaimMeta"
import { formatCurrency } from "@/utils/formatters"

import { useCurrencyConversion } from "@/composables/useCurrencyConversion"

const props = defineProps({
	expenseClaim: {
		type: Object,
		required: true,
	},
	isReadOnly: {
		type: Boolean,
		default: false,
	},
})
const emit = defineEmits([
	"add-expense-item",
	"update-expense-item",
	"delete-expense-item",
])
const dayjs = inject("$dayjs")
const __ = inject("$translate")
const expenseItem = ref({})
const editingIdx = ref(null)

const isModalOpen = ref(false)
const isFirstRender = ref(false)

const openModal = async (item, idx) => {
	if (item) {
		expenseItem.value = { ...item }
		editingIdx.value = idx
	}
	isFirstRender.value = true
	isModalOpen.value = true
}

const deleteExpenseItem = () => {
	emit("delete-expense-item", editingIdx.value)
	resetSelectedItem()
}

const updateExpenseItem = () => {
	if (editingIdx.value === null) {
		emit("add-expense-item", expenseItem.value)
	} else {
		emit("update-expense-item", expenseItem.value, editingIdx.value)
	}
	resetSelectedItem()
}

function resetSelectedItem() {
	isFirstRender.value = false
	isModalOpen.value = false
	expenseItem.value = {}
	editingIdx.value = null
}

const expensesTableFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Expense Claim Detail" },
	transform(data) {
		// Strip the modal down to what the claimant actually decides:
		// date, type, description, amount. Everything else is either
		// auto-managed (cost_center, sanctioned_amount, default_account,
		// base_*) or out-of-scope for an expense (project), so it just
		// adds visual noise.
		const excludeFields = [
			"description_sb",
			"amounts_sb",
			"base_amount",
			"base_sanctioned_amount",
			"sanctioned_amount",
			"default_account",
			"cost_center",
			"project",
			"accounting_dimensions_section",
			"dimension_col_break",
			"column_break_2",
			"column_break_8",
		]
		return data
			.filter((field) => !excludeFields.includes(field.fieldname))
			.map((field) => {
				// Description ships as Text Editor — the rich-text toolbar
				// dwarfs the input. A plain textarea matches the design
				// language of the rest of the modal.
				if (field.fieldname === "description") {
					return { ...field, fieldtype: "Small Text" }
				}
				return field
			})
	},
})
expensesTableFields.reload()

// Each section renders one specific field; we look them up by name so
// the modal can stay declarative + the field metadata (reqd, default,
// fieldtype) keeps coming from the backend's get_doctype_fields call.
function findField(name) {
	return (expensesTableFields.data || []).find((f) => f.fieldname === name)
}

const dateField = computed(() => findField("expense_date"))
const descField = computed(() => findField("description"))
const remarksField = computed(() => findField("custom_remarks"))
const amountField = computed(() => findField("amount"))

// Visual chips for the Expense Claim Type Link field. Iconography +
// colour mapping live in @/data/expenseClaimMeta so the chip in this
// modal, the row icon below, and the dashboard list icon stay in sync.
const typeChips = computed(() => {
	const ids = Object.keys(claimTypesByID || {})
	if (!ids.length) return []
	return ids.map((id) => {
		const meta = EXPENSE_TYPE_META[id] || EXPENSE_TYPE_META.Others
		return { value: id, label: id, ...meta }
	})
})

const currencySymbol = computed(() =>
	getCurrencySymbol(props.expenseClaim.currency),
)

// Quick-add chips. INR scale (100/500/1k/5k); other currencies get a
// proportionally smaller scale.
const quickAmounts = computed(() => {
	const code = props.expenseClaim.currency || "INR"
	if (code === "INR") return [100, 500, 1000, 5000]
	return [10, 50, 100, 500]
})

const expenseClaimRef = computed(() => props.expenseClaim)
useCurrencyConversion(
	expensesTableFields,
	expenseClaimRef,
	["amount", "sanctioned_amount"]
)

const modalTitle = computed(() => {
	if (props.isReadOnly) return __("Expense Item")

	return editingIdx.value === null ? __("New Expense Item") : __("Edit Expense Item")
})

const addButtonDisabled = computed(() => {
	return expensesTableFields.data?.some((field) => {
		if (field.reqd && !expenseItem.value[field.fieldname]) {
			return true
		}
	})
})

// child table form scripts
watch(
	() => expenseItem.value.expense_type,
	(value) => {
		// Description is now the read-only About blurb, fully derived from
		// the picked category — always overwrite on category change so a
		// prior category's text doesn't linger.
		expenseItem.value.description = claimTypesByID[value]?.description || ""
		expenseItem.value.cost_center = props.expenseClaim.cost_center
	}
)

// Mirror amount → sanctioned_amount. Without this the GL posting on
// approve+submit silently skips the row (HRMS expense_claim.py:204
// guards on `total_sanctioned_amount > 0`). The approver can still
// reduce sanctioned in their app if they want to part-pay.
//
// First-render handling: when *editing* an existing item we don't want
// to clobber the already-stored sanctioned with the freshly-loaded
// amount. For *new* items there's nothing to preserve, so we propagate
// the very first amount entry too.
watch(
	() => expenseItem.value.amount,
	(value) => {
		const isEditingExisting = editingIdx.value !== null
		if (isEditingExisting && isFirstRender.value) {
			isFirstRender.value = false
			return
		}
		isFirstRender.value = false
		expenseItem.value.sanctioned_amount = parseFloat(value)
	}
)
</script>

<style scoped>
/* Force ion-modal to viewport height. Without this, Ionic was letting the
 * shadow `.modal-wrapper` grow to content height (e.g. 864px on a 700px
 * viewport), which made the modal's `flex-1 overflow-y-auto` body fit its
 * content exactly with nothing to clip. The whole modal overflowed the
 * viewport but couldn't scroll because modals are positioned overlays.
 * Setting `--height: 100%` caps the wrapper at viewport, the body becomes
 * shorter than its content, and `overflow-y-auto` finally engages. */
ion-modal {
	--height: 100%;
	--width: 100%;
}
</style>
