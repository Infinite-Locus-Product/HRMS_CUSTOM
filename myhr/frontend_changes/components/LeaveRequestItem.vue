<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div
				class="h-9 w-9 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center shrink-0"
			>
				<LeaveIcon class="h-4 w-4" />
			</div>
			<div class="flex flex-col items-start gap-1 min-w-0">
				<div class="text-sm font-bold text-gray-900 truncate max-w-[60vw]">
					{{ __(props.doc.leave_type, null, "Leave Type") }}
				</div>
				<div class="flex items-center gap-1.5 text-[11px] font-semibold text-gray-500">
					<FeatherIcon name="calendar" class="h-3 w-3" />
					<span class="whitespace-nowrap">{{ props.doc.leave_dates || getLeaveDates(props.doc) }}</span>
					<span v-if="totalDays" class="text-gray-300">·</span>
					<span v-if="totalDays" class="whitespace-nowrap">{{ totalDays }} {{ totalDays === 1 ? __("day") : __("days") }}</span>
				</div>
			</div>
		</template>
		<template #right>
			<Badge :variant="badgeVariant" :theme="badgeTheme" :label="__(status, null, 'Leave Application')" size="md" />
			<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400" />
		</template>
	</ListItem>
</template>

<script setup>
import { computed } from "vue"
import { FeatherIcon, Badge } from "frappe-ui"

import ListItem from "@/components/ListItem.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import { getLeaveDates } from "@/data/leaves"

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

// PWA convention: "Open" reads as "Requested" so it's clear the request is
// filed and awaiting the approver. Backend still uses "Open" — display only.
const rawStatus = computed(() => {
	return props.workflowStateField
		? props.doc[props.workflowStateField]
		: props.doc.status
})

const status = computed(() => {
	if (rawStatus.value === "Open") return "Requested"
	return rawStatus.value
})

const totalDays = computed(() => {
	const t = props.doc.total_leave_days
	if (typeof t === "number") return t
	return null
})

const colorMap = {
	Approved: "green",
	Rejected: "red",
	Requested: "orange",
	Cancelled: "gray",
}

const badgeTheme = computed(() => colorMap[status.value] || "gray")

const badgeVariant = computed(() =>
	["Approved", "Rejected"].includes(status.value) ? "subtle" : "outline"
)
</script>
