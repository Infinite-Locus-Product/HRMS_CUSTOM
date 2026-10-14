<template>
	<div
		class="flex flex-col items-center justify-center gap-3 px-5 py-10 text-center"
		:class="[
			props.isTableField
				? 'border-2 border-dashed border-gray-200 rounded-2xl bg-gray-50/50 mt-4'
				: 'rounded-2xl bg-white border border-gray-100 shadow-sm mt-4',
		]"
	>
		<div
			class="p-3 rounded-2xl bg-gray-50 border border-gray-200 text-gray-400"
		>
			<FeatherIcon :name="iconName" class="h-5 w-5" />
		</div>
		<div class="text-sm font-bold text-gray-700">
			{{ __(props.message) }}
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"
import { FeatherIcon } from "frappe-ui"

const props = defineProps({
	message: { type: String },
	isTableField: { type: Boolean, default: false },
	icon: { type: String, default: "" },
})

// Best-effort icon based on the message wording so we don't need every caller
// to pass an icon. Falls back to a neutral inbox icon.
const iconName = computed(() => {
	if (props.icon) return props.icon
	const m = (props.message || "").toLowerCase()
	if (m.includes("leave")) return "calendar"
	if (m.includes("shift")) return "clock"
	if (m.includes("attendance") || m.includes("checkin")) return "user-check"
	if (m.includes("expense") || m.includes("claim")) return "credit-card"
	if (m.includes("salary") || m.includes("slip")) return "file-text"
	if (m.includes("advance")) return "trending-up"
	if (m.includes("notification")) return "bell"
	return "inbox"
})
</script>
