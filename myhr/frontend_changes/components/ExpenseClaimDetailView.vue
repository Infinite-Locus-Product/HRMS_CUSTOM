<template>
	<div class="bg-[#FBFBFC] min-h-screen pb-[120px]">
		<div
			class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative"
		>
			<!-- Glassy sticky header -->
			<div
				class="flex flex-row bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100 items-center gap-2"
			>
				<Button
					variant="ghost"
					class="!px-2 hover:bg-gray-100 transition-colors"
					@click="router.back()"
				>
					<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
				</Button>
				<div class="flex flex-col ml-1 overflow-hidden flex-1 min-w-0">
					<h2
						class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1"
					>
						{{ __("Expense Claim") }}
					</h2>
					<div
						class="text-[10px] font-bold uppercase tracking-widest text-gray-400 truncate"
					>
						{{ props.id }}
						<span v-if="approverDisplay">
							· {{ __("Approver") }}: {{ approverDisplay }}
						</span>
					</div>
				</div>
				<Badge
					v-if="status"
					:label="__(status, null, 'Expense Claim')"
					:theme="statusTone.theme"
					variant="subtle"
					size="md"
				/>
			</div>

			<!-- Body -->
			<div v-if="ready" class="flex-1 px-4 py-5 sm:p-5 space-y-4">
				<!-- Status banner -->
				<div
					class="rounded-2xl border px-4 py-3 flex items-start gap-3"
					:class="statusTone.banner"
				>
					<FeatherIcon
						:name="statusTone.icon"
						class="h-5 w-5 mt-0.5 shrink-0"
						:class="statusTone.iconColor"
					/>
					<div class="flex-1 min-w-0">
						<div class="text-sm font-extrabold" :class="statusTone.title">
							{{ statusTone.heading }}
						</div>
						<div class="text-xs mt-0.5" :class="statusTone.body">
							{{ statusTone.subtitle }}
						</div>
					</div>
				</div>

				<!-- Grand total hero -->
				<div
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm"
				>
					<div
						class="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2"
					>
						{{ __("Grand Total") }}
					</div>
					<div class="text-2xl font-extrabold text-gray-900 leading-none">
						{{ formatMoney(doc.grand_total) }}
					</div>
					<div
						v-if="doc.posting_date"
						class="mt-2 text-[11px] font-bold text-gray-500"
					>
						{{ __("Posted") }} · {{ formatDate(doc.posting_date) }}
					</div>
				</div>

				<!-- Expense items -->
				<div
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm"
				>
					<div class="flex items-center justify-between mb-2">
						<div
							class="text-[10px] font-black uppercase tracking-widest text-gray-400"
						>
							{{ __("Expense Items") }}
						</div>
						<div
							class="text-[10px] font-black uppercase tracking-widest text-gray-300"
						>
							{{ (doc.expenses || []).length }}
						</div>
					</div>
					<div
						v-if="doc.expenses && doc.expenses.length"
						class="flex flex-col divide-y divide-gray-100"
					>
						<div
							v-for="(item, idx) in doc.expenses"
							:key="idx"
							class="py-2.5 first:pt-0 last:pb-0 flex items-start justify-between gap-3"
						>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-bold text-gray-900 truncate">
									{{ item.expense_type || __("Expense") }}
								</div>
								<div
									v-if="item.description || item.expense_date"
									class="text-[11px] text-gray-500 mt-0.5 truncate"
								>
									<span v-if="item.expense_date">{{ formatDate(item.expense_date) }}</span>
									<span v-if="item.expense_date && item.description"> · </span>
									<span v-if="item.description">{{ item.description }}</span>
								</div>
								<div
									v-if="item.custom_remarks"
									class="text-[11px] font-medium text-gray-600 mt-1 italic whitespace-pre-line break-words"
								>
									{{ item.custom_remarks }}
								</div>
							</div>
							<div
								class="text-sm font-extrabold text-gray-900 whitespace-nowrap"
							>
								{{ formatMoney(item.amount) }}
							</div>
						</div>
					</div>
					<p v-else class="text-xs text-gray-400 italic">
						{{ __("No expense items.") }}
					</p>
				</div>

				<!-- Totals -->
				<div
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm space-y-1.5"
				>
					<div
						class="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2"
					>
						{{ __("Totals") }}
					</div>
					<TotalsRow
						:label="__('Total claimed')"
						:value="formatMoney(doc.total_claimed_amount)"
					/>
					<TotalsRow
						:label="__('Total sanctioned')"
						:value="formatMoney(doc.total_sanctioned_amount)"
					/>
					<TotalsRow
						v-if="doc.total_taxes_and_charges"
						:label="__('Taxes & charges')"
						:value="formatMoney(doc.total_taxes_and_charges)"
					/>
					<TotalsRow
						v-if="doc.total_advance_amount"
						:label="__('Advance applied')"
						:value="`- ${formatMoney(doc.total_advance_amount)}`"
					/>
					<div class="border-t border-gray-100 mt-1.5 pt-1.5">
						<TotalsRow
							:label="__('Grand total')"
							:value="formatMoney(doc.grand_total)"
							strong
						/>
					</div>
				</div>

				<!-- Meta -->
				<div
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm space-y-2.5"
				>
					<MetaRow :label="__('Filed by')" :value="doc.employee_name || doc.employee" />
					<MetaRow :label="__('Department')" :value="doc.department" />
					<MetaRow :label="__('Approver')" :value="doc.expense_approver_name || doc.expense_approver" />
					<MetaRow :label="__('Cost center')" :value="doc.cost_center" />
					<MetaRow :label="__('Project')" :value="doc.project" />
				</div>
			</div>

			<div
				v-else
				class="flex-1 flex items-center justify-center py-20 text-gray-400"
			>
				<LoadingIndicator class="w-5 h-5" />
			</div>
		</div>

		<!-- Sticky Submit-for-Review CTA — shown only on draft claims
		     filed by the session user. Mirrors the EAC submit-for-review
		     pattern: save first, review on the detail screen, then
		     deliberately submit so the approver gets a single notification. -->
		<div
			v-if="canSubmit"
			class="fixed bottom-0 left-0 right-0 z-50 sm:max-w-4xl sm:mx-auto px-4 pb-4 pt-3 bg-gradient-to-t from-white via-white to-white/0"
		>
			<button
				type="button"
				@click="onSubmitForReview"
				:disabled="submitDoc.loading"
				class="w-full py-4 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50"
			>
				<LoadingIndicator
					v-if="submitDoc.loading"
					class="h-4 w-4 text-white"
				/>
				<FeatherIcon v-else name="send" class="h-4 w-4" />
				{{ submitDoc.loading ? __("Submitting") : __("Submit for Review") }}
			</button>
			<p
				class="text-[11px] font-semibold text-gray-400 text-center mt-2"
			>
				{{ __("{0} will review the claim once submitted.", [doc.expense_approver_name || doc.expense_approver || __("Your approver")]) }}
			</p>
		</div>

		<SuccessModal
			:isOpen="successOpen"
			:title="__('Claim submitted!')"
			:subtitle="__('{0} has been notified.', [doc.expense_approver_name || doc.expense_approver || __('Your approver')])"
			:reference="props.id"
			@dismiss="onSuccessDismissed"
		/>
	</div>
</template>

<script setup>
import { computed, h, inject, ref } from "vue"
import { useRouter } from "vue-router"
import {
	Badge,
	Button,
	FeatherIcon,
	LoadingIndicator,
	createDocumentResource,
	createResource,
} from "frappe-ui"
import dayjs from "@/utils/dayjs"
import { getCompanyCurrency } from "@/data/currencies"
import { formatCurrency } from "@/utils/formatters"
import SuccessModal from "@/components/SuccessModal.vue"
import { sessionUser } from "@/data/session"
import { showErrorFromException } from "@/data/errorModal"

const props = defineProps({
	id: { type: String, required: true },
})

const __ = inject("$translate")
const router = useRouter()

const document = createDocumentResource({
	doctype: "Expense Claim",
	name: props.id,
	auto: true,
})
const ready = computed(() => Boolean(document.doc))
const doc = computed(() => document.doc || {})

const currency = computed(
	() => doc.value.currency || (doc.value.company ? getCompanyCurrency(doc.value.company) : null)
)

const approverDisplay = computed(() => {
	if (!ready.value) return ""
	return doc.value.expense_approver_name || doc.value.expense_approver || ""
})

const status = computed(() => {
	if (!ready.value) return ""
	const a = doc.value.approval_status
	const ds = doc.value.docstatus
	if (a === "Approved") return ds === 1 ? "Approved" : "Approved (Draft)"
	if (a === "Rejected") return "Rejected"
	if (ds === 2) return "Cancelled"
	if (ds === 0) {
		// Save-flow chains submit-for-review, so the typical state is
		// "Requested". "Draft" only appears if the chained submit failed
		// — the user can retry via the detail-view CTA.
		return doc.value.custom_submitted_for_review ? "Requested" : "Draft"
	}
	return "Submitted"
})

// Submit-for-Review CTA visibility — owner only, only while the claim
// is a draft AND hasn't already been submitted for review. After a
// successful submit, the flag flips and the CTA disappears.
const canSubmit = computed(() => {
	if (!ready.value) return false
	if (doc.value.docstatus !== 0) return false
	if (doc.value.custom_submitted_for_review) return false
	const me = sessionUser()
	return Boolean(me) && doc.value.owner === me
})

const successOpen = ref(false)

const submitDoc = createResource({
	url: "myhr.api.submit_expense_claim_for_review",
	onSuccess() {
		successOpen.value = true
		document.reload()
	},
	onError(err) {
		console.error("Error submitting Expense Claim", err)
		showErrorFromException(err, __("Could not submit the claim"))
	},
})

function onSubmitForReview() {
	if (submitDoc.loading) return
	submitDoc.submit({ name: props.id })
}

function onSuccessDismissed() {
	successOpen.value = false
}

const statusTone = computed(() => {
	const s = status.value
	if (s === "Approved" || s === "Approved (Draft)") {
		return {
			theme: "green",
			banner: "border-green-200 bg-green-50",
			icon: "check-circle",
			iconColor: "text-green-600",
			title: "text-green-900",
			body: "text-green-800",
			heading: __("Approved"),
			subtitle: __("Your claim has been approved."),
		}
	}
	if (s === "Rejected") {
		return {
			theme: "red",
			banner: "border-red-200 bg-red-50",
			icon: "alert-circle",
			iconColor: "text-red-600",
			title: "text-red-900",
			body: "text-red-800",
			heading: __("Rejected"),
			subtitle: __("Your approver declined this claim."),
		}
	}
	if (s === "Cancelled") {
		return {
			theme: "gray",
			banner: "border-gray-200 bg-gray-50",
			icon: "slash",
			iconColor: "text-gray-500",
			title: "text-gray-900",
			body: "text-gray-700",
			heading: __("Cancelled"),
			subtitle: __("This claim was cancelled."),
		}
	}
	if (s === "Draft") {
		return {
			theme: "blue",
			banner: "border-blue-200 bg-blue-50",
			icon: "edit-3",
			iconColor: "text-blue-600",
			title: "text-blue-900",
			body: "text-blue-800",
			heading: __("Draft"),
			subtitle: __("The save-step submit-for-review didn't run. Tap the button below to retry."),
		}
	}
	// "Requested" (or anything else docstatus=0 that isn't an outright
	// draft) lands here. Banner heading is "Awaiting approval" — the
	// header badge says "Requested" via statusMap below.
	//
	// Owner-side reassurance ("X will review this claim") only makes
	// sense to the filer. When the approver opens the same row they
	// already know they're the reviewer, so we drop the subtitle.
	const me = sessionUser()
	const viewerIsOwner = !!me && doc.value.owner === me
	return {
		theme: "orange",
		banner: "border-amber-200 bg-amber-50",
		icon: "clock",
		iconColor: "text-amber-600",
		title: "text-amber-900",
		body: "text-amber-800",
		heading: __("Awaiting approval"),
		subtitle: viewerIsOwner
			? __("{0} will review this claim.", [
				doc.value.expense_approver_name || doc.value.expense_approver || __("Your approver"),
			])
			: "",
	}
})

function formatMoney(value) {
	if (value == null || value === "") return formatCurrency(0, currency.value)
	return formatCurrency(value, currency.value)
}

function formatDate(value) {
	if (!value) return ""
	const d = dayjs(value)
	return d.isValid() ? d.format("D MMM YYYY") : value
}

const MetaRow = (p) => {
	if (!p.value) return null
	return h(
		"div",
		{ class: "flex items-center justify-between gap-3" },
		[
			h("div", { class: "text-xs font-semibold text-gray-500" }, p.label),
			h(
				"div",
				{ class: "text-sm font-bold text-gray-900 truncate" },
				String(p.value)
			),
		]
	)
}
MetaRow.props = ["label", "value"]

const TotalsRow = (p) =>
	h(
		"div",
		{ class: "flex items-center justify-between gap-3" },
		[
			h(
				"div",
				{
					class: p.strong
						? "text-xs font-bold text-gray-700"
						: "text-xs font-semibold text-gray-500",
				},
				p.label
			),
			h(
				"div",
				{
					class: p.strong
						? "text-base font-extrabold text-gray-900"
						: "text-sm font-bold text-gray-800",
				},
				p.value
			),
		]
	)
TotalsRow.props = ["label", "value", "strong"]
</script>
