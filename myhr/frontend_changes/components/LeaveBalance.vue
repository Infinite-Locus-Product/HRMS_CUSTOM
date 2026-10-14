<template>
	<div class="flex flex-col w-full gap-3 px-4">
		<!-- Section header (Action-Centre pattern) -->
		<div class="flex items-center justify-between gap-3">
			<div class="flex items-center gap-3 min-w-0">
				<div
					class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
				>
					<FeatherIcon name="bar-chart-2" class="h-5 w-5" />
				</div>
				<div class="flex flex-col min-w-0">
					<h3
						class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
					>
						{{ __("Leave Balance") }}
					</h3>
					<span
						class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
					>
						{{ __("Available across leave types") }}
					</span>
				</div>
			</div>
			<router-link
				v-if="leaveBalance.data"
				:to="{ name: 'LeaveApplicationListView' }"
				v-slot="{ navigate }"
			>
				<button
					type="button"
					@click="navigate"
					class="text-[10px] font-black uppercase tracking-widest text-blue-600 hover:text-blue-800 transition-colors flex items-center gap-1 shrink-0"
				>
					{{ __("Leave Requests") }}
					<FeatherIcon name="arrow-right" class="h-3 w-3" />
				</button>
			</router-link>
		</div>

		<!-- Cards row -->
		<div
			v-if="leaveBalance.data && Object.keys(leaveBalance.data).length"
			class="flex flex-row gap-3 overflow-x-auto pb-2 -mx-4 px-4 hide-scrollbar"
		>
			<div
				v-for="(allocation, leave_type, index) in leaveBalance.data"
				:key="leave_type"
				class="flex flex-col rounded-2xl border shadow-sm p-4 shrink-0 w-[160px]"
				:class="cardTone(index)"
			>
				<div
					class="text-[10px] font-black uppercase tracking-widest"
					:class="labelTone(index)"
				>
					{{ __(leave_type, null, "Leave Type") }}
				</div>
				<div class="mt-2 flex items-baseline gap-1">
					<span class="text-3xl font-black leading-none text-gray-900">
						{{ allocation.balance_leaves }}
					</span>
					<span class="text-xs font-bold text-gray-500">
						/ {{ allocation.allocated_leaves }}
					</span>
				</div>
				<div class="text-[11px] font-bold text-gray-500 mt-0.5">
					{{ __("days left") }}
				</div>
				<div class="mt-3 h-1.5 rounded-full bg-white/80 overflow-hidden">
					<div
						class="h-full rounded-full transition-all"
						:class="barTone(index)"
						:style="{
							width: `${Math.min(
								100,
								Math.max(0, allocation.balance_percentage || 0)
							)}%`,
						}"
					></div>
				</div>
			</div>
		</div>

		<EmptyState v-else :message="__('You have no leaves allocated')" />
	</div>
</template>

<script setup>
import { leaveBalance } from "@/data/leaves"
import { inject } from "vue"
import { FeatherIcon } from "frappe-ui"
import EmptyState from "@/components/EmptyState.vue"

const __ = inject("$translate")

// Rotate through frappe-ui safe palette tones; never indigo (not in palette).
const TONES = [
	{
		card: "bg-blue-50 border-blue-100",
		label: "text-blue-700",
		bar: "bg-blue-500",
	},
	{
		card: "bg-green-50 border-green-100",
		label: "text-green-700",
		bar: "bg-green-500",
	},
	{
		card: "bg-amber-50 border-amber-100",
		label: "text-amber-700",
		bar: "bg-amber-500",
	},
	{
		card: "bg-purple-50 border-purple-100",
		label: "text-purple-700",
		bar: "bg-purple-500",
	},
	{
		card: "bg-teal-50 border-teal-100",
		label: "text-teal-700",
		bar: "bg-teal-500",
	},
]

const cardTone = (i) => TONES[i % TONES.length].card
const labelTone = (i) => TONES[i % TONES.length].label
const barTone = (i) => TONES[i % TONES.length].bar
</script>

<style scoped>
.hide-scrollbar::-webkit-scrollbar {
	display: none;
}
.hide-scrollbar {
	-ms-overflow-style: none;
	scrollbar-width: none;
}
</style>
