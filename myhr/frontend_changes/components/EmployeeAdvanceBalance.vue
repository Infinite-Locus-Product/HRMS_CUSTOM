<template>
	<div v-if="props.items?.length" class="flex flex-col gap-3">
		<div
			class="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden divide-y divide-gray-100"
		>
			<router-link
				v-for="link in props.items"
				:key="link.name"
				:to="{ name: 'EmployeeAdvanceDetailView', params: { id: link.name } }"
				class="flex flex-row p-4 items-center justify-between hover:bg-blue-50/60 active:bg-blue-100/60 transition-colors"
			>
				<EmployeeAdvanceItem :doc="link" />
			</router-link>
		</div>

		<router-link :to="{ name: 'EmployeeAdvanceFormView' }" v-slot="{ navigate }">
			<button
				type="button"
				@click="navigate"
				class="w-full py-4 rounded-2xl bg-white border-2 border-gray-200 text-gray-900 font-black text-xs uppercase tracking-widest hover:border-blue-300 hover:text-blue-700 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
			>
				<FeatherIcon name="plus" class="h-4 w-4" />
				{{ __("Request an Advance") }}
			</button>
		</router-link>
	</div>
	<div v-else>
		<EmptyState :message="__('You have no advances')" />
		<router-link :to="{ name: 'EmployeeAdvanceFormView' }" v-slot="{ navigate }">
			<button
				type="button"
				@click="navigate"
				class="mt-3 w-full py-4 rounded-2xl bg-white border-2 border-gray-200 text-gray-900 font-black text-xs uppercase tracking-widest hover:border-blue-300 hover:text-blue-700 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
			>
				<FeatherIcon name="plus" class="h-4 w-4" />
				{{ __("Request an Advance") }}
			</button>
		</router-link>
	</div>
</template>

<script setup>
import { inject } from "vue"
import { FeatherIcon } from "frappe-ui"

import EmployeeAdvanceItem from "@/components/EmployeeAdvanceItem.vue"
import EmptyState from "@/components/EmptyState.vue"

const __ = inject("$translate")
const props = defineProps({
	items: { type: Array },
})
</script>
