<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<!-- Category-coloured icon — matches the chips in the line-item
			     modal and the row icons inside an open claim, so the user
			     reads "this is a Food claim" before reading the amount. -->
			<div
				class="h-9 w-9 rounded-xl flex items-center justify-center shrink-0"
				:class="`${typeMeta.bg} ${typeMeta.text}`"
			>
				<FeatherIcon :name="typeMeta.icon" class="h-4 w-4" />
			</div>
			<div class="flex flex-col items-start gap-1.5">
				<div class="text-base font-normal text-gray-800">
					{{ claimTitle }}
				</div>
				<div class="text-xs font-normal text-gray-500">
					<span>{{ claimDates }}</span>
					<span class="whitespace-pre"> &middot; </span>
					<span class="whitespace-nowrap">
						{{ formatCurrency(props.doc.total_claimed_amount, props.doc.currency) }}
					</span>
				</div>
			</div>
		</template>
		<template #right>
			<Badge
				variant="outline"
				:theme="statusMap[status]"
				:label="__(displayStatus, null, 'Expense Claim')"
				size="md"
			/>
			<FeatherIcon name="chevron-right" class="h-5 w-5 text-gray-500" />
		</template>
	</ListItem>
</template>

<script setup>
import { FeatherIcon, Badge } from "frappe-ui"
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"

import { formatCurrency } from "@/utils/formatters"
import { getExpenseTypeMeta } from "@/data/expenseClaimMeta"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const props = defineProps({
	doc: {
		type: Object,
	},
	isTeamRequest: {
		type: Boolean,
		default: false,
	},
	workflowStateField: {
		type: String,
		required: false,
	},
})

// Display map: rename "Draft" → "Requested" in line with PWA convention.
const statusMap = {
	Requested: "orange",
	Submitted: "blue",
	Cancelled: "gray",
	Paid: "green",
	Unpaid: "orange",
	Approved: "green",
	Rejected: "red",
}

const status = computed(() => {
	if (props.workflowStateField) {
		return props.doc[props.workflowStateField]
	} else if (props.doc.approval_status === "Rejected") {
		return "Rejected"
	} else if (props.doc.status === "Paid") {
		return "Paid"
	} else if (props.doc.approval_status === "Approved") {
		return "Approved"
	}
	return props.doc.status === "Draft" ? "Requested" : props.doc.status
})

const displayStatus = computed(() => status.value)

const claimTitle = computed(() => {
	let title = __(props.doc.expense_type)
	if (props.doc.total_expenses > 1) {
		title = __("{0} & {1} more", [title, props.doc.total_expenses - 1])
	}
	return title
})

// Category meta drives the row's icon + colour. Falls back to "Others"
// for unknown types or claims with no expense_type yet.
const typeMeta = computed(() => getExpenseTypeMeta(props.doc.expense_type))

const claimDates = computed(() => {
	const fd = props.doc.from_date
	const td = props.doc.to_date
	if (!fd && !td) return dayjs(props.doc.posting_date).format("D MMM")
	if (!td || fd === td) return dayjs(fd).format("D MMM")
	if (!fd) return dayjs(td).format("D MMM")
	return `${dayjs(fd).format("D MMM")} - ${dayjs(td).format("D MMM")}`
})
</script>
