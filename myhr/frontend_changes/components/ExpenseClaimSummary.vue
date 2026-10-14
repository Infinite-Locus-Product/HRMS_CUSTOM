<template>
	<div v-if="summary.data" class="flex flex-col w-full gap-3">
		<div class="flex items-center gap-3">
			<div
				class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
			>
				<FeatherIcon name="bar-chart-2" class="h-5 w-5" />
			</div>
			<div class="flex flex-col">
				<h3
					class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
				>
					{{ __("Expense Summary") }}
				</h3>
				<span
					class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
				>
					{{ __("Year to date") }}
				</span>
			</div>
		</div>

		<!-- Hero total card -->
		<div class="rounded-2xl bg-blue-600 p-5 text-white shadow-sm">
			<div
				class="text-[10px] font-black uppercase tracking-widest text-white/80"
			>
				{{ __("Total Claimed") }}
			</div>
			<div class="mt-1 text-3xl font-black leading-none">
				{{ formatCurrency(total_claimed_amount, company_currency) }}
			</div>

			<div class="mt-4 grid grid-cols-3 gap-2">
				<div class="rounded-xl bg-white/15 px-3 py-2">
					<div class="flex items-center gap-1">
						<FeatherIcon
							name="clock"
							class="h-3 w-3 text-amber-200"
						/>
						<span
							class="text-[9px] font-black uppercase tracking-widest text-white/80"
						>
							{{ __("Pending") }}
						</span>
					</div>
					<div class="text-sm font-extrabold mt-0.5 truncate">
						{{
							formatCurrency(
								summary.data?.total_pending_amount || 0,
								company_currency
							)
						}}
					</div>
				</div>
				<div class="rounded-xl bg-white/15 px-3 py-2">
					<div class="flex items-center gap-1">
						<FeatherIcon
							name="check-circle"
							class="h-3 w-3 text-green-200"
						/>
						<span
							class="text-[9px] font-black uppercase tracking-widest text-white/80"
						>
							{{ __("Approved") }}
						</span>
					</div>
					<div class="text-sm font-extrabold mt-0.5 truncate">
						{{
							formatCurrency(
								summary.data?.total_approved_amount || 0,
								company_currency
							)
						}}
					</div>
				</div>
				<div class="rounded-xl bg-white/15 px-3 py-2">
					<div class="flex items-center gap-1">
						<FeatherIcon name="x-circle" class="h-3 w-3 text-red-200" />
						<span
							class="text-[9px] font-black uppercase tracking-widest text-white/80"
						>
							{{ __("Rejected") }}
						</span>
					</div>
					<div class="text-sm font-extrabold mt-0.5 truncate">
						{{
							formatCurrency(
								summary.data?.total_rejected_amount || 0,
								company_currency
							)
						}}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui"
import { computed } from "vue"

import { expenseClaimSummary as summary } from "@/data/claims"
import { formatCurrency } from "@/utils/formatters"

const total_claimed_amount = computed(() => {
	return (
		(summary.data?.total_pending_amount || 0) +
		(summary.data?.total_claimed_in_approved || 0) +
		(summary.data?.total_rejected_amount || 0)
	)
})

const company_currency = computed(() => summary.data?.currency)
</script>
