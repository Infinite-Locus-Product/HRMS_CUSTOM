<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<!-- Detail / view flow uses the polished read-only DetailView. The
			     stock FormView surfaces every doctype field — including the
			     Approval Status / docstatus / payable account / clearance
			     metadata — which the employee should not be touching. -->
			<ExpenseClaimDetailView
				v-if="props.id"
				:id="props.id"
			/>

			<!-- New-claim flow: a context card pinned above the FormView so the
			     claimant sees who/when/which-currency at a glance, then the
			     stock FormView (tabs + child tables) keeps totals / advance
			     allocation / currency conversion logic as one source of truth.
			     Currency block is hidden when the employee currency matches
			     the company currency (~all single-currency demos). -->
			<div
				v-else-if="formFields.data"
				class="w-full sm:max-w-4xl sm:mx-auto bg-white"
			>
				<!-- Top bar: X exits the whole new-claim flow for the case
				     where the user opened it but doesn't want to file a
				     claim. Sticky so it survives scroll. -->
				<div
					class="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100 sticky top-0 z-40"
				>
					<button
						type="button"
						@click="onClose"
						:aria-label="__('Close')"
						class="h-9 w-9 rounded-xl bg-gray-100 text-gray-600 flex items-center justify-center hover:bg-gray-200 transition-colors"
					>
						<FeatherIcon name="x" class="h-5 w-5" />
					</button>
					<div class="text-sm font-extrabold text-gray-900 truncate px-3">
						{{ __("New Expense Claim") }}
					</div>
					<div class="h-9 w-9" />
				</div>

				<!-- Claim context — section blocks matching the leave-request
				     pattern (icon tile + uppercase title + subtitle). Replaces
				     the dense single-card layout so each input has its own
				     breathing room. -->
				<div class="px-4 pt-4 sm:px-5 sm:pt-5 space-y-5">
					<!-- Section: Claim for -->
					<section class="space-y-3">
						<div class="flex items-center gap-3">
							<div class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100">
								<FeatherIcon name="user" class="h-5 w-5" />
							</div>
							<div class="flex flex-col">
								<h3 class="text-sm font-black text-gray-900 uppercase tracking-[0.1em]">
									{{ __("Claim for") }}
								</h3>
								<span class="text-[10px] font-bold text-gray-400 uppercase tracking-[0.05em]">
									{{ __("Submitting employee") }}
								</span>
							</div>
						</div>
						<div class="rounded-2xl border border-gray-100 bg-white px-4 py-3 flex items-center gap-3">
							<div
								class="w-10 h-10 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-black text-sm shrink-0 border border-blue-200"
							>
								{{ initials(employeeFullName || currEmployee) }}
							</div>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-extrabold text-gray-900 truncate">
									{{ employeeFullName || currEmployee }}
								</div>
								<div v-if="employeeDept" class="text-[11px] font-bold text-gray-500 truncate">
									{{ employeeDept }}
								</div>
							</div>
						</div>
					</section>

					<!-- Section: When + currency -->
					<section class="space-y-3">
						<div class="flex items-center gap-3">
							<div class="p-2.5 rounded-xl bg-violet-50 text-violet-600 shadow-sm border border-violet-100">
								<FeatherIcon name="calendar" class="h-5 w-5" />
							</div>
							<div class="flex flex-col">
								<h3 class="text-sm font-black text-gray-900 uppercase tracking-[0.1em]">
									{{ __("Posting date") }}
								</h3>
								<span class="text-[10px] font-bold text-gray-400 uppercase tracking-[0.05em]">
									{{ __("When you're filing this claim") }}
								</span>
							</div>
						</div>
						<div class="grid grid-cols-2 gap-3">
							<div class="rounded-2xl border border-gray-100 bg-white px-4 py-3">
								<div class="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-1">
									{{ __("Date") }}
								</div>
								<div class="[&>div]:w-full [&_input]:!border-0 [&_input]:!shadow-none [&_input]:!bg-transparent [&_input]:!px-0 [&_input]:!text-sm [&_input]:!font-extrabold [&_input]:!text-gray-900 [&_input]:!h-auto [&_input]:!py-0 [&_input]:focus:!ring-0">
									<DatePicker
										:modelValue="expenseClaim.posting_date"
										:formatter="(v) => v ? dayjs(v).format('DD MMM YYYY') : ''"
										:placeholder="__('Pick a date')"
										@update:modelValue="(v) => {
											if (v && dayjs(v).isAfter(today)) v = today
											expenseClaim.posting_date = v
										}"
									/>
								</div>
							</div>
							<div class="rounded-2xl border border-gray-100 bg-white px-4 py-3">
								<div class="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-1">
									{{ __("Currency") }}
								</div>
								<div class="text-sm font-extrabold text-gray-900 leading-[1.5rem]">
									{{ expenseClaim.currency || companyCurrency }}
								</div>
							</div>
						</div>
					</section>

					<!-- Section: Approver — leave-form-style avatar card with
					     options when more than one approver is configured, or
					     a single AUTO-ASSIGNED chip when there's exactly one. -->
					<section v-if="approverField" class="space-y-3">
						<div class="flex items-center gap-3">
							<div class="p-2.5 rounded-xl bg-green-50 text-green-600 shadow-sm border border-green-100">
								<FeatherIcon name="user-check" class="h-5 w-5" />
							</div>
							<div class="flex flex-col">
								<h3 class="text-sm font-black text-gray-900 uppercase tracking-[0.1em]">
									{{ __("Approver") }}<span v-if="approverField.reqd" class="text-red-500 ml-0.5">*</span>
								</h3>
								<span class="text-[10px] font-bold text-gray-400 uppercase tracking-[0.05em]">
									{{ __("Who reviews this request") }}
								</span>
							</div>
						</div>

						<div v-if="approverOptions.length > 1" class="space-y-2">
							<button
								v-for="opt in approverOptions"
								:key="opt.value"
								type="button"
								@click="expenseClaim.expense_approver = opt.value"
								class="w-full rounded-2xl border-2 px-4 py-3 text-left transition-all flex items-center gap-3"
								:class="expenseClaim.expense_approver === opt.value
									? 'border-green-500 bg-green-50'
									: 'border-gray-100 bg-white hover:border-green-200'"
							>
								<div class="w-9 h-9 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-black text-sm shrink-0 border border-green-200">
									{{ initials(opt.label) }}
								</div>
								<div class="flex-1 min-w-0">
									<div class="text-sm font-extrabold text-gray-900 truncate">
										{{ approverNameOf(opt) }}
									</div>
									<div class="text-[11px] font-bold text-gray-500 truncate">
										{{ opt.value }}
									</div>
								</div>
								<FeatherIcon
									v-if="expenseClaim.expense_approver === opt.value"
									name="check-circle"
									class="h-5 w-5 text-green-600 shrink-0"
								/>
							</button>
						</div>

						<div
							v-else-if="approverOptions.length === 1"
							class="rounded-2xl border border-gray-100 bg-white px-4 py-3 flex items-center gap-3"
						>
							<div class="w-9 h-9 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-black text-sm shrink-0 border border-green-200">
								{{ initials(approverNameOf(approverOptions[0])) }}
							</div>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-extrabold text-gray-900 truncate">
									{{ approverNameOf(approverOptions[0]) }}
								</div>
								<div class="text-[11px] font-bold text-gray-500 truncate">
									{{ approverOptions[0].value }}
								</div>
							</div>
							<span class="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md bg-green-50 text-green-600 border border-green-100">
								{{ __("Auto-assigned") }}
							</span>
						</div>

						<!-- Edge case: backend returned no department_approvers
						     and the field is mandatory. Fall back to the stock
						     FormField so the user has a way to pick someone. -->
						<div v-else class="[&>div>span:first-of-type]:hidden">
							<FormField
								class="w-full"
								:label="__('Approver')"
								:fieldtype="approverField.fieldtype"
								:fieldname="approverField.fieldname"
								:options="approverField.options"
								:reqd="approverField.reqd"
								:documentList="approverField.documentList"
								v-model="expenseClaim.expense_approver"
							/>
						</div>
					</section>
				</div>

				<FormView
					doctype="Expense Claim"
					v-model="expenseClaim"
					:isSubmittable="true"
					postInsertEndpoint="myhr.api.submit_expense_claim_for_review"
					:successTitle="__('Claim requested!')"
					:successSubtitle="__('{0} will review the claim shortly.', [approverDisplayName])"
					:fields="formFields.data"
					:tabbedView="true"
					:tabs="tabs"
					:showAttachmentView="true"
					@validateForm="validateForm"
					:showDownloadPDFButton="true"
					@formReloaded="onFormReloaded"
				>
				<!-- Child Tables -->
				<template #expenses="{ isFormReadOnly }">
					<ExpensesTable
						v-model:expenseClaim="expenseClaim"
						:isReadOnly="isReadOnly || isFormReadOnly"
						@addExpenseItem="addExpenseItem"
						@updateExpenseItem="updateExpenseItem"
						@deleteExpenseItem="deleteExpenseItem"
					/>
				</template>

				<!-- Taxes hidden: company policy is no taxes on expense claims.
				     Slot kept (empty) so FormView's tab-boundary logic
				     (`lastField: 'taxes'`) still resolves. The
				     calculateTaxes()/calculateGrandTotal() script chain is
				     harmless when expenseClaim.taxes stays empty. -->
				<template #taxes="{ isFormReadOnly }">
					<!-- intentionally empty -->
				</template>

				<template #advances="{ isFormReadOnly }">
					<ExpenseAdvancesTable
						v-model:expenseClaim="expenseClaim"
						:isReadOnly="isReadOnly || isFormReadOnly"
					/>
				</template>
				</FormView>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { DatePicker, FeatherIcon, createResource } from "frappe-ui"
import { computed, ref, watch, inject } from "vue"
import { useRouter } from "vue-router"

import FormView from "@/components/FormView.vue"
import FormField from "@/components/FormField.vue"
import ExpenseClaimDetailView from "@/components/ExpenseClaimDetailView.vue"
import ExpensesTable from "@/components/ExpensesTable.vue"
import ExpenseTaxesTable from "@/components/ExpenseTaxesTable.vue"
import ExpenseAdvancesTable from "@/components/ExpenseAdvancesTable.vue"
import { getCompanyCurrency } from "@/data/currencies"
import { useCurrencyConversion } from "@/composables/useCurrencyConversion"


const dayjs = inject("$dayjs")
const __ = inject("$translate")

const today = dayjs().format("YYYY-MM-DD")
const isReadOnly = ref(false)
const router = useRouter()

function onClose() {
	// `router.back()` returns to the previous in-app screen (typically the
	// Expense Claims list). Falls back to the claims dashboard when there's
	// no history entry — covers deep-link opens of the new-claim URL.
	if (window.history.state?.back) {
		router.back()
	} else {
		router.push({ name: "ExpenseClaimsDashboard" })
	}
}

const sessionEmployee = inject("$employee")
const currEmployee = ref(sessionEmployee.data.name)
const employeeCompany = ref(sessionEmployee.data.company)
const employeeFullName = ref(
	sessionEmployee.data.employee_name || sessionEmployee.data.first_name || ""
)
const employeeDept = ref(sessionEmployee.data.department || "")


const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

const tabs = [
	{ name: "Expenses", lastField: "taxes" },
	{ name: "Advances", lastField: "advances" },
	{ name: "Totals", lastField: "cost_center" },
]

// object to store form data
const expenseClaim = ref({
	employee: currEmployee,
	company: employeeCompany,
	doctype: "Expense Claim",
	posting_date: today,
})

const companyCurrency = computed(() => getCompanyCurrency(expenseClaim.value.company))

// get form fields
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Expense Claim" },
	transform(data) {
		let fields = getFilteredFields(data)

		return fields.map((field) => {
			if (field.fieldname === "posting_date") field.default = today
			// expense_approver is rendered explicitly in the context card
			// at the top of the screen; hide the duplicate inside FormView.
			if (field.fieldname === "expense_approver" && !props.id) {
				field.hidden = 1
			}
			return applyFilters(field)
		})
	},
	onSuccess(_data) {
		expenseApproverDetails.reload()
		if (!expenseClaim.value.currency) {
			employeeCurrency.reload()
		}
		companyDetails.reload()
	},
})
formFields.reload()

// Live reference to the approver field metadata so the context-card FormField
// reuses the same documentList / reqd flag that setExpenseApprover writes back
// onto formFields.data. Both card and FormView point at the same object.
const approverField = computed(() =>
	formFields.data?.find((f) => f.fieldname === "expense_approver")
)

// Approver options as the avatar card needs them. setExpenseApprover already
// shaped them as `{ label: "user@x.com : Full Name", value: "user@x.com" }`,
// so we split label back out for display.
const approverOptions = computed(() => approverField.value?.documentList || [])

function approverNameOf(opt) {
	if (!opt) return ""
	// label format from setExpenseApprover: "<email> : <Full Name>"
	const sep = " : "
	const idx = opt.label?.indexOf(sep)
	if (idx > -1) return opt.label.slice(idx + sep.length)
	return opt.label || opt.value
}

// Display name for the success modal subtitle ("X will review shortly").
const approverDisplayName = computed(() => {
	const v = expenseClaim.value.expense_approver
	const opt = approverOptions.value.find((o) => o.value === v)
	return approverNameOf(opt) || __("your approver")
})

function initials(name) {
	if (!name) return "?"
	return name
		.split(/[\s@.]+/)
		.filter(Boolean)
		.map((s) => s[0])
		.slice(0, 2)
		.join("")
		.toUpperCase()
}

useCurrencyConversion(
	formFields,
	expenseClaim,
	[
		"total_sanctioned_amount",
		"total_taxes_and_charges",
		"total_advance_amount",
		"grand_total",
		"total_claimed_amount"
	]
)

// resources & helper functions
const advances = createResource({
	url: "hrms.hr.doctype.expense_claim.expense_claim.get_advances",
	makeParams() {
		return { expense_claim: expenseClaim.value }
	},
	onSuccess(data) {
		selectAllocatedAdvances()
		addUnallocatedAdvances(data)
	},
})

function selectAllocatedAdvances() {
	if (props.id) {
		expenseClaim.value?.advances?.map((advance) => (advance.selected = true))
	} else {
		expenseClaim.value.advances = []
	}
}

function addUnallocatedAdvances(data) {
	// only show advances for selection in a draft claim
	const isDraft = expenseClaim.value?.docstatus == 0 || !expenseClaim.value?.docstatus
	if (!isDraft) return

	const allocatedAdvances = new Set(
		expenseClaim.value?.advances?.map((advance) => advance.employee_advance)
	)

	return data.forEach((advance) => {
		if (props.id && allocatedAdvances.has(advance.employee_advance)) return

		expenseClaim.value?.advances?.push({
			...advance,
			selected: false,
			allocated_amount: 0,
		})
	})
}

function onFormReloaded() {
	advances.reload()
}

const expenseApproverDetails = createResource({
	url: "hrms.api.get_expense_approval_details",
	params: { employee: currEmployee.value },
	onSuccess(data) {
		setExpenseApprover(data)
	},
})

const employeeCurrency = createResource({
	url: "frappe.client.get_value",
	makeParams() {
		return {
			doctype: "Employee",
			fieldname: ["salary_currency"],
			filters: { name: currEmployee.value },
		};
	},
	onSuccess(data) {
		// Always end up with a currency: prefer the employee's salary currency,
		// fall back to the company currency. Without a fallback the field stays
		// blank and the (now hidden) mandatory check blocks Save silently.
		const resolved = data?.salary_currency || companyCurrency.value
		if (resolved) {
			expenseClaim.value.currency = resolved
			if (resolved === companyCurrency.value) {
				expenseClaim.value.exchange_rate = 1
			}
		}
	}
});

const companyDetails = createResource({
	url: "hrms.api.get_company_cost_center_and_expense_account",
	params: { company: expenseClaim.value.company },
	onSuccess(data) {
		expenseClaim.value.cost_center = data?.cost_center
		expenseClaim.value.payable_account =
			data?.default_expense_claim_payable_account
	},
})

const exchangeRate = createResource({
	url: "erpnext.setup.utils.get_exchange_rate",
	onSuccess(data) {
		expenseClaim.value.exchange_rate = data
	},
})

// form scripts
watch(
	() => expenseClaim.value.employee,
	(employee_id) => {
		if (props.id && employee_id !== currEmployee.value) {
			// if employee is not the current user, set form as read only
			setFormReadOnly()
		}
		currEmployee.value = employee_id
		expenseApproverDetails.fetch({ employee: currEmployee.value })
		employeeCurrency.fetch()
	},
)

watch(
	() => expenseClaim.value.company,
	(company) => {
		employeeCompany.value = company
		companyDetails.fetch({ company: employeeCompany.value })
	}
)

watch(
	() => expenseClaim.value.currency,
	() => setExchangeRate()
)

watch(
	() => expenseClaim.value.name,
	() => {
		advances.reload()
	},
	{ immediate: true }
)

watch(
	() => expenseClaim.value.advances,
	(_value) => {
		calculateTotalAdvance()
	},
	{ deep: true }
)

watch(
	() => expenseClaim.value.cost_center,
	() => {
		expenseClaim?.value?.expenses?.forEach((expense) => {
			expense.cost_center = expenseClaim.value.cost_center
		})
	}
)

// helper functions
function getFilteredFields(fields) {
	// reduce noise from the form view by excluding unnecessary fields
	// eg: employee and other details can be fetched from the session user
	const excludeFields = [
		"naming_series",
		"task",
		"taxes_and_charges_sb",
		"advance_payments_sb",
	]
	const extraFields = [
		"employee",
		"employee_name",
		"department",
		"company",
		"remark",
		"is_paid",
		"mode_of_payment",
		"clearance_date",
		"approval_status",
		// Currency block is auto-managed: defaulted from employee.salary_currency
		// (or company currency as fallback) and exchange_rate is forced to 1 in
		// the single-currency case. Surfacing empty mandatory fields here just
		// blocks Save without giving the claimant a real decision to make.
		"currency_section",
		"currency",
		"column_break_imlz",
		"exchange_rate",
		// Posting date is rendered in the context card at the top of the form.
		"posting_date",
	]

	if (!props.id) excludeFields.push(...extraFields)

	return fields.filter((field) => {
		if (excludeFields.includes(field.fieldname)) return false

		if (field.fieldname?.startsWith("base_")) return false
		return true
	})
}

function applyFilters(field) {
	if (field.fieldname === "payable_account") {
		field.linkFilters = {
			report_type: "Balance Sheet",
			account_type: "Payable",
			company: expenseClaim.value.company,
			is_group: 0,
			account_currency: expenseClaim.value.currency,
		}
	} else if (field.fieldname === "cost_center") {
		field.linkFilters = {
			company: expenseClaim.value.company,
			is_group: 0,
		}
	} else if (field.fieldname === "project") {
		field.linkFilters = {
			company: expenseClaim.value.company,
		}
	}

	return field
}

function setExpenseApprover(data) {
	const expense_approver = formFields.data?.find(
		(field) => field.fieldname === "expense_approver"
	)
	expense_approver.reqd = data?.is_mandatory
	expense_approver.documentList = data?.department_approvers.map(
		(approver) => ({
			label: approver.full_name
				? `${approver.name} : ${approver.full_name}`
				: approver.name,
			value: approver.name,
		})
	)

	expenseClaim.value.expense_approver = data?.expense_approver
	expenseClaim.value.expense_approver_name = data?.expense_approver_name
}

function addExpenseItem(item) {
	if (!expenseClaim.value.expenses) expenseClaim.value.expenses = []
	expenseClaim.value.expenses.push(item)
	calculateTotals()
	calculateTaxes()
	allocateAdvanceAmount()
}

function updateExpenseItem(item, idx) {
	expenseClaim.value.expenses[idx] = item
	calculateTotals()
	calculateTaxes()
	allocateAdvanceAmount()
}

function deleteExpenseItem(idx) {
	expenseClaim.value.expenses.splice(idx, 1)
	calculateTotals()
	calculateTaxes()
	allocateAdvanceAmount()
}

function addExpenseTax(item) {
	if (!expenseClaim.value.taxes) expenseClaim.value.taxes = []
	expenseClaim.value.taxes.push(item)
	calculateTaxes()
	allocateAdvanceAmount()
}

function updateExpenseTax(item, idx) {
	expenseClaim.value.taxes[idx] = item
	calculateTaxes()
	allocateAdvanceAmount()
}

function deleteExpenseTax(idx) {
	expenseClaim.value.taxes.splice(idx, 1)
	calculateTaxes()
	allocateAdvanceAmount()
}

function calculateTotals() {
	let total_claimed_amount = 0
	let total_sanctioned_amount = 0

	expenseClaim.value?.expenses?.forEach((item) => {
		total_claimed_amount += parseFloat(item.amount)
		total_sanctioned_amount += parseFloat(item.sanctioned_amount)
	})

	expenseClaim.value.total_claimed_amount = total_claimed_amount
	expenseClaim.value.total_sanctioned_amount = total_sanctioned_amount
	calculateGrandTotal()
}

function calculateTaxes() {
	let total_taxes_and_charges = 0

	expenseClaim.value?.taxes?.forEach((item) => {
		if (item.rate) {
			item.tax_amount =
				parseFloat(expenseClaim.value.total_sanctioned_amount) *
				parseFloat(item.rate / 100)
		}

		item.total =
			parseFloat(item.tax_amount) +
			parseFloat(expenseClaim.value.total_sanctioned_amount)
		total_taxes_and_charges += parseFloat(item.tax_amount)
	})
	expenseClaim.value.total_taxes_and_charges = total_taxes_and_charges
	calculateGrandTotal()
}

function calculateGrandTotal() {
	expenseClaim.value.grand_total =
		parseFloat(expenseClaim.value.total_sanctioned_amount || 0) +
		parseFloat(expenseClaim.value.total_taxes_and_charges || 0) -
		parseFloat(expenseClaim.value.total_advance_amount || 0)
}

function allocateAdvanceAmount() {
	// allocate reqd advance amount
	let amount_to_be_allocated =
		parseFloat(expenseClaim.value.total_sanctioned_amount) +
		parseFloat(expenseClaim.value.total_taxes_and_charges)

	if (!amount_to_be_allocated) return
	let total_advance_amount = 0

	expenseClaim?.value?.advances?.forEach((advance) => {
		if (amount_to_be_allocated >= parseFloat(advance.unclaimed_amount)) {
			advance.allocated_amount = parseFloat(advance.unclaimed_amount)
			amount_to_be_allocated -= parseFloat(advance.allocated_amount)
		} else {
			advance.allocated_amount = amount_to_be_allocated
			amount_to_be_allocated = 0
		}

		advance.selected = advance.allocated_amount > 0 ? true : false
		total_advance_amount += parseFloat(advance.allocated_amount)
	})
	expenseClaim.value.total_advance_amount = total_advance_amount
	calculateGrandTotal()
}

function calculateTotalAdvance() {
	// update total advance amount as per user selection & edited values
	let total_advance_amount = 0

	expenseClaim?.value?.advances?.forEach((advance) => {
		if (advance.selected || parseFloat(advance.allocated_amount) > 0) {
			total_advance_amount += parseFloat(advance.allocated_amount || 0)
		}
	})
	expenseClaim.value.total_advance_amount = total_advance_amount
	calculateGrandTotal()
}

function setFormReadOnly() {
	if (props.id && expenseClaim.value.expense_approver !== currEmployee.value) return
	formFields.data.map((field) => (field.read_only = true))
	isReadOnly.value = true
}

function validateForm() {
	// set selected advances
	if (!expenseClaim?.value?.advances) return

	expenseClaim.value.advances = expenseClaim?.value?.advances?.filter(
		(advance) => advance.selected
	)
	expenseClaim?.value?.expenses?.forEach((expense) => {
		expense.cost_center = expenseClaim.value.cost_center
	})
}

function setExchangeRate() {
	if (!expenseClaim.value.currency || !formFields.data) return
	const exchange_rate_field = formFields.data?.find(
		(field) => field.fieldname === "exchange_rate"
	)

	exchangeRate.fetch({
		from_currency: expenseClaim.value.currency,
		to_currency: companyCurrency.value,
	})
	if (exchange_rate_field) exchange_rate_field.hidden = 0
}
</script>

<style scoped>
/* New-claim flow stacks context cards above FormView. FormView's internal
 * `grow overflow-y-auto` (FormView.vue:58) creates a nested scroll trap whose
 * height isn't bounded here (no `h-full` chain to ion-content), leaving the
 * lower part of the form unscrollable. Disable that nested scroll so the
 * outer ion-content shadow scroll captures the whole page naturally. */
:deep(.grow.overflow-y-auto) {
	overflow-y: visible;
}
</style>
