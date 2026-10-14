<template>
	<ListItem>
		<template #left>
			<div
				class="p-2 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 shrink-0"
			>
				<SalaryIcon class="h-4 w-4" />
			</div>
			<div class="flex flex-col items-start gap-1 min-w-0">
				<div class="text-[15px] font-extrabold text-gray-900 truncate">
					{{ title }}
				</div>
				<div
					v-if="doc?.gross_pay"
					class="text-[11px] font-bold text-gray-500"
				>
					{{ __("Gross") }}
					{{ formatCurrency(doc.gross_pay, doc.currency) }}
				</div>
			</div>
		</template>
		<template #right>
			<div class="flex flex-col items-end gap-0.5">
				<span
					class="text-[9px] font-black uppercase tracking-widest text-gray-400"
				>
					{{ __("Net") }}
				</span>
				<span
					v-if="doc?.net_pay"
					class="text-sm font-extrabold text-gray-900"
				>
					{{ formatCurrency(doc.net_pay, doc.currency) }}
				</span>
			</div>
			<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-300 shrink-0" />
		</template>
	</ListItem>
</template>

<script setup>
import { computed, inject } from "vue"
import { FeatherIcon } from "frappe-ui"

import ListItem from "@/components/ListItem.vue"
import SalaryIcon from "@/components/icons/SalaryIcon.vue"

import { formatCurrency } from "@/utils/formatters"

const dayjs = inject("$dayjs")
const __ = inject("$translate")

const props = defineProps({
	doc: { type: Object },
})

const title = computed(() => {
	if (dayjs(props.doc.start_date).isSame(props.doc.end_date, "month")) {
		return dayjs(props.doc.start_date).format("MMM YYYY")
	} else {
		return `${dayjs(props.doc.start_date).format("MMM YYYY")} - ${dayjs(
			props.doc.end_date
		).format("MMM YYYY")}`
	}
})
</script>
