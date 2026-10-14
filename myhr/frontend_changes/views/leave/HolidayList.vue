<template>
	<BaseLayout :pageTitle="__('Holiday List')">
		<template #body>
			<div class="flex flex-col gap-4 p-4">
				<!-- Section header -->
				<div class="flex items-center gap-3 px-1 mt-2">
					<div
						class="p-2.5 rounded-xl bg-amber-50 text-amber-600 shadow-sm border border-amber-100"
					>
						<FeatherIcon name="gift" class="h-5 w-5" />
					</div>
					<div class="flex flex-col min-w-0">
						<h3
							class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
						>
							{{ __("All Holidays") }}
						</h3>
						<span
							class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
						>
							<span v-if="holidays.length">
								{{ holidays.length }} {{ __("holidays") }} ·
								{{ optionalCount }} {{ __("optional") }}
							</span>
							<span v-else>{{ __("Loading…") }}</span>
						</span>
					</div>
				</div>

				<!-- Grouped by month -->
				<div class="flex flex-col gap-4">
					<div
						v-for="bucket in monthBuckets"
						:key="bucket.key"
						class="space-y-2"
					>
						<div
							class="text-[11px] font-black uppercase tracking-widest text-gray-400 px-1"
						>
							{{ bucket.label }}
						</div>
						<div
							class="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden divide-y divide-gray-100"
						>
							<div
								v-for="h in bucket.items"
								:key="h.date"
								class="flex flex-row p-3.5 items-center gap-3"
							>
								<div
									class="rounded-xl px-3 py-2 text-center shrink-0 border"
									:class="datePillClass(h)"
								>
									<div
										class="text-[9px] font-black uppercase tracking-widest"
										:class="datePillTextClass(h)"
									>
										{{ h.month_short }}
									</div>
									<div
										class="text-lg font-black leading-none mt-0.5"
										:class="datePillNumClass(h)"
									>
										{{ h.day }}
									</div>
								</div>
								<div class="flex-1 min-w-0">
									<div
										class="text-sm font-extrabold truncate"
										:class="
											h.is_past
												? 'text-gray-500'
												: 'text-gray-900'
										"
									>
										{{ __(h.description || "Holiday") }}
									</div>
									<div
										class="text-[11px] font-bold text-gray-500 mt-0.5 flex items-center gap-1.5"
									>
										<span>{{ h.weekday_label }}</span>
										<span
											v-if="h.type === 'optional'"
											class="text-[9px] font-black uppercase tracking-widest text-gray-600 px-1.5 py-0.5 rounded-md bg-gray-50 border border-dashed border-gray-300"
										>
											{{ __("Optional") }}
										</span>
										<span
											v-else-if="h.type === 'weekly_off'"
											class="text-[9px] font-black uppercase tracking-widest text-gray-500 px-1.5 py-0.5 rounded-md bg-gray-100 border border-gray-200"
										>
											{{ __("Weekly Off") }}
										</span>
										<span
											v-else
											class="text-[9px] font-black uppercase tracking-widest text-amber-700 px-1.5 py-0.5 rounded-md bg-amber-50 border border-amber-100"
										>
											{{ __("Fixed") }}
										</span>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<EmptyState
					v-if="!holidays.length && !calendarData.loading"
					:message="__('No holidays in your holiday list')"
				/>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject } from "vue"
import { createResource, FeatherIcon } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import EmptyState from "@/components/EmptyState.vue"

const employee = inject("$employee")
const dayjs = inject("$dayjs")
const __ = inject("$translate")
const today = dayjs().format("YYYY-MM-DD")

// Pull a wide window so the user gets their entire allocation period.
const fromDate = dayjs().subtract(3, "month").startOf("month").format("YYYY-MM-DD")
const toDate = dayjs().add(12, "month").endOf("month").format("YYYY-MM-DD")

const calendarData = createResource({
	url: "myhr.api.get_leave_calendar_data",
	params: {
		employee: employee.data.name,
		from_date: fromDate,
		to_date: toDate,
	},
	auto: true,
})

const holidays = computed(() => {
	const rows = calendarData.data?.holidays || []
	// Hide weekly offs entirely — Sat/Sun aren't useful as a "holiday" entry.
	// Only fixed and optional surface here.
	return rows
		.filter((h) => h.type !== "weekly_off")
		.map((h) => {
			const d = dayjs(h.date)
			return {
				date: h.date,
				type: h.type,
				description: h.description,
				month_short: d.format("MMM"),
				day: d.format("D"),
				weekday_label: d.format("dddd"),
				is_past: h.date < today,
				month_key: d.format("YYYY-MM"),
				month_label: d.format("MMMM YYYY"),
			}
		})
		.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0))
})

const optionalCount = computed(
	() => holidays.value.filter((h) => h.type === "optional").length
)

const monthBuckets = computed(() => {
	const map = new Map()
	holidays.value.forEach((h) => {
		if (!map.has(h.month_key)) {
			map.set(h.month_key, {
				key: h.month_key,
				label: h.month_label,
				items: [],
			})
		}
		map.get(h.month_key).items.push(h)
	})
	return [...map.values()]
})

function datePillClass(h) {
	if (h.type === "optional")
		return "bg-gray-50 border-dashed border-gray-300"
	if (h.type === "weekly_off") return "bg-gray-100 border-gray-200"
	return h.is_past
		? "bg-gray-50 border-gray-200"
		: "bg-amber-50 border-amber-100"
}
function datePillTextClass(h) {
	if (h.type === "optional") return "text-gray-500"
	if (h.type === "weekly_off") return "text-gray-400"
	return h.is_past ? "text-gray-400" : "text-amber-700"
}
function datePillNumClass(h) {
	if (h.type === "optional") return "text-gray-700"
	if (h.type === "weekly_off") return "text-gray-500"
	return h.is_past ? "text-gray-500" : "text-amber-900"
}
</script>
