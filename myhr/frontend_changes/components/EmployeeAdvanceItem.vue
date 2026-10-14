<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div
				class="p-2 rounded-xl bg-green-50 border border-green-100 text-green-600 shrink-0"
			>
				<EmployeeAdvanceIcon class="h-4 w-4" />
			</div>
			<div class="flex flex-col items-start gap-1 min-w-0">
				<div
					v-if="props.doc.balance_amount"
					class="text-[15px] font-extrabold text-gray-900 leading-tight"
				>
					{{ formatCurrency(props.doc.balance_amount, props.doc.currency) }}
					<span class="text-gray-400">/</span>
					<span class="text-gray-500 text-[13px] font-bold">
						{{ formatCurrency(props.doc.paid_amount, props.doc.currency) }}
					</span>
				</div>
				<div
					v-else
					class="text-[15px] font-extrabold text-gray-900 leading-tight"
				>
					{{ formatCurrency(props.doc.advance_amount, props.doc.currency) }}
				</div>
				<div class="text-[11px] font-bold text-gray-500">
					{{ __(props.doc.purpose) }}
					<span class="whitespace-pre"> · </span>
					{{ postingDate }}
				</div>
			</div>
		</template>
		<template #right>
			<Badge
				variant="outline"
				:theme="colorMap[status] || 'gray'"
				:label="__(displayStatus, null, 'Employee Advance')"
				size="md"
			/>
			<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-300 shrink-0" />
		</template>
	</ListItem>
</template>

<script setup>
import { FeatherIcon, Badge } from "frappe-ui"
import { computed, inject } from "vue"

import ListItem from "@/components/ListItem.vue"
import EmployeeAdvanceIcon from "@/components/icons/EmployeeAdvanceIcon.vue"
import { formatCurrency } from "@/utils/formatters"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const props = defineProps({
	doc: { type: Object },
	isTeamRequest: { type: Boolean, default: false },
	workflowStateField: { type: String, required: false },
})

const colorMap = {
	Paid: "green",
	Unpaid: "orange",
	Claimed: "blue",
	Returned: "gray",
	"Partly Claimed and Returned": "orange",
	Requested: "orange",
}

const postingDate = computed(() => {
	return dayjs(props.doc.posting_date).format("D MMM")
})

const status = computed(() => {
	return props.workflowStateField
		? props.doc[props.workflowStateField]
		: props.doc.status
})

const displayStatus = computed(() =>
	status.value === "Draft" ? "Requested" : status.value
)
</script>
