<template>
	<div class="flex flex-col gap-3 w-full">
		<!-- Section header -->
		<div class="flex items-center justify-between gap-3">
			<div class="flex items-center gap-3 min-w-0">
				<div
					class="p-2.5 rounded-xl bg-amber-50 text-amber-600 shadow-sm border border-amber-100"
				>
					<FeatherIcon name="gift" class="h-5 w-5" />
				</div>
				<div class="flex flex-col min-w-0">
					<h3
						class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
					>
						{{ __("Upcoming Holidays") }}
					</h3>
					<span
						class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
					>
						{{ __("Based on your holiday list") }}
					</span>
				</div>
			</div>
			<router-link
				v-if="upcomingHolidays.length"
				:to="{ name: 'HolidayListView' }"
				v-slot="{ navigate }"
			>
				<button
					type="button"
					@click="navigate"
					class="text-[10px] font-black uppercase tracking-widest text-blue-600 hover:text-blue-800 transition-colors flex items-center gap-1 shrink-0"
				>
					{{ __("View all") }}
					<FeatherIcon name="arrow-right" class="h-3 w-3" />
				</button>
			</router-link>
		</div>

		<div
			v-if="upcomingHolidays.length"
			class="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden divide-y divide-gray-100"
		>
			<div
				v-for="holiday in upcomingHolidays"
				:key="holiday.date"
				class="flex flex-row p-3.5 items-center gap-3"
			>
				<div
					class="rounded-xl px-3 py-2 text-center shrink-0 border"
					:class="datePillClass(holiday)"
				>
					<div
						class="text-[9px] font-black uppercase tracking-widest"
						:class="datePillTextClass(holiday)"
					>
						{{ holiday.month_short }}
					</div>
					<div
						class="text-lg font-black leading-none mt-0.5"
						:class="datePillNumClass(holiday)"
					>
						{{ holiday.day }}
					</div>
				</div>
				<div class="flex-1 min-w-0">
					<div class="text-sm font-extrabold text-gray-900 truncate">
						{{ __(holiday.description || "Holiday") }}
					</div>
					<div class="text-[11px] font-bold text-gray-500 mt-0.5 flex items-center gap-1.5">
						<span>{{ holiday.weekday_label }}</span>
						<span
							v-if="holiday.type === 'optional'"
							class="text-[9px] font-black uppercase tracking-widest text-gray-600 px-1.5 py-0.5 rounded-md bg-gray-50 border border-dashed border-gray-300"
						>
							{{ __("Optional") }}
						</span>
						<span
							v-else-if="holiday.type === 'weekly_off'"
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

		<EmptyState v-else :message="__('You have no upcoming holidays')" />
	</div>
</template>

<script setup>
import { inject, computed } from "vue"
import { FeatherIcon, createResource } from "frappe-ui"
import EmptyState from "@/components/EmptyState.vue"

const employee = inject("$employee")
const dayjs = inject("$dayjs")
const __ = inject("$translate")
const today = dayjs().format("YYYY-MM-DD")

// Window: today → +12 months. Limited so the inline list isn't huge; full
// list lives at HolidayListView.
const fromDate = today
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

const upcomingHolidays = computed(() => {
	const rows = calendarData.data?.holidays || []
	// Hide weekly_off from the inline preview — they're noise. Surface only
	// the next 5 *real* holidays; weekly offs surface on the full list page.
	return rows
		.filter((h) => h.type !== "weekly_off")
		.slice(0, 5)
		.map((h) => {
			const d = dayjs(h.date)
			return {
				date: h.date,
				type: h.type,
				description: h.description,
				month_short: d.format("MMM"),
				day: d.format("D"),
				weekday_label: d.format("dddd"),
			}
		})
})

function datePillClass(h) {
	if (h.type === "optional") return "bg-gray-50 border-dashed border-gray-300"
	if (h.type === "weekly_off") return "bg-gray-100 border-gray-200"
	return "bg-amber-50 border-amber-100"
}
function datePillTextClass(h) {
	if (h.type === "optional") return "text-gray-500"
	if (h.type === "weekly_off") return "text-gray-400"
	return "text-amber-700"
}
function datePillNumClass(h) {
	if (h.type === "optional") return "text-gray-700"
	if (h.type === "weekly_off") return "text-gray-500"
	return "text-amber-900"
}
</script>
