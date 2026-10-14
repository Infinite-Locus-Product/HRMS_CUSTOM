<template>
	<ListItem>
		<template #left>
			<div
				class="p-2 rounded-xl border shrink-0"
				:class="
					isCheckIn
						? 'bg-green-50 border-green-100 text-green-600'
						: 'bg-amber-50 border-amber-100 text-amber-600'
				"
			>
				<FeatherIcon
					:name="isCheckIn ? 'log-in' : 'log-out'"
					class="h-4 w-4"
				/>
			</div>
			<div class="flex flex-col items-start gap-1 min-w-0">
				<div class="text-[15px] font-extrabold text-gray-900">
					{{
						isCheckIn ? __("Checked In") : __("Checked Out")
					}}
				</div>
				<div class="text-[11px] font-bold text-gray-500">
					{{ formatTimestamp(props.doc.time) }}
				</div>
			</div>
		</template>
		<template #right>
			<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-300 shrink-0" />
		</template>
	</ListItem>
</template>

<script setup>
import { computed, inject } from "vue"
import { FeatherIcon } from "frappe-ui"

import ListItem from "@/components/ListItem.vue"
import { formatTimestamp } from "@/utils/formatters"

const __ = inject("$translate")

const props = defineProps({
	doc: { type: Object },
})

const isCheckIn = computed(() => props.doc?.log_type === "IN")
</script>
