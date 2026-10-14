<template>
	<div class="flex flex-col w-full justify-center gap-2 min-w-0">
		<div class="flex flex-row items-center justify-between gap-3 min-w-0">
			<div class="flex flex-row items-start gap-3 grow min-w-0">
				<slot name="left" />
			</div>
			<div class="flex flex-row justify-end items-center gap-2 shrink-0">
				<slot name="right" />
			</div>
		</div>
		<div
			v-if="props.isTeamRequest"
			class="flex flex-row items-center gap-2 pl-8"
		>
			<EmployeeAvatar :employeeID="props.employee" />
			<div class="text-xs font-bold text-gray-500 truncate">
				{{ props.employeeName }}
			</div>
		</div>
	</div>
</template>

<script setup>
import EmployeeAvatar from "@/components/EmployeeAvatar.vue"

const props = defineProps({
	isTeamRequest: {
		type: Boolean,
		default: false,
	},
	employee: {
		type: String,
		required: false,
	},
	employeeName: {
		type: String,
		required: false,
	},
})
</script>
