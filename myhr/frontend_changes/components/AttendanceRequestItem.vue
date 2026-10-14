<template>
	<ListItem
		:isTeamRequest="props.isTeamRequest"
		:employee="props.doc.employee"
		:employeeName="props.doc.employee_name"
	>
		<template #left>
			<div
				class="h-9 w-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0"
			>
				<AttendanceIcon class="h-4 w-4" />
			</div>
			<div class="flex flex-col items-start gap-1 min-w-0">
				<div class="text-sm font-bold text-gray-900 truncate max-w-[60vw]">
					{{ props.doc.reason || __("Attendance Request") }}
				</div>
				<div class="flex items-center gap-1.5 text-[11px] font-semibold text-gray-500">
					<FeatherIcon name="calendar" class="h-3 w-3" />
					<span class="whitespace-nowrap">{{ props.doc.attendance_dates || getDates(props.doc) }}</span>
					<span v-if="totalDays" class="text-gray-300">·</span>
					<span v-if="totalDays" class="whitespace-nowrap">{{ totalDays }} {{ totalDays === 1 ? __("day") : __("days") }}</span>
				</div>
			</div>
		</template>
		<template #right>
			<Badge :variant="badgeVariant" :theme="colorMap[status]" :label="__(status)" size="md" />
			<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400" />
		</template>
	</ListItem>
</template>

<script setup>
import { computed } from "vue"
import { Badge, FeatherIcon } from "frappe-ui"

import ListItem from "@/components/ListItem.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import { getDates, getTotalDays } from "@/data/attendance"

const props = defineProps({
	doc: {
		type: Object,
	},
	workflowStateField: {
		type: String,
		required: false,
	},
})

// HRMS approval flow keeps un-actioned requests at docstatus=0 until the
// approver submits them. "Draft" is the technical name; PWA shows "Requested"
// so the user reads it as "filed and awaiting review".
const status = computed(() => {
	if (props.workflowStateField) return props.doc[props.workflowStateField]
	const ds = props.doc.docstatus
	if (ds === 2) return "Cancelled"
	if (ds === 1) return "Submitted"
	return "Requested"
})

// `total_attendance_days` is set by the list-resource transform, but a row
// opened via deep link may arrive without it; recompute as a fallback so the
// duration never renders blank.
const totalDays = computed(() => {
	const t = props.doc.total_attendance_days
	if (typeof t === "number") return t
	return getTotalDays(props.doc)
})

const colorMap = {
	Requested: "orange",
	Submitted: "blue",
	Cancelled: "gray",
}

const badgeVariant = computed(() =>
	status.value === "Submitted" ? "subtle" : "outline"
)
</script>
