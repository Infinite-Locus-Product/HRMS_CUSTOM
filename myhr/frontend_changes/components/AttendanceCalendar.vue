<template>
	<div class="flex flex-col w-full gap-3" v-if="calendarEvents.data">
		<!-- Section header (Action-Centre pattern) -->
		<div class="flex items-center gap-3 px-1">
			<div
				class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
			>
				<FeatherIcon name="calendar" class="h-5 w-5" />
			</div>
			<div class="flex flex-col min-w-0">
				<h3
					class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
				>
					{{ __("Attendance Calendar") }}
				</h3>
				<span
					class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em] truncate"
				>
					{{ firstOfMonth.format("MMMM YYYY") }} ·
					{{ totalTracked }} {{ __("days tracked") }}
				</span>
			</div>
		</div>

		<div
			class="rounded-2xl border border-gray-100 bg-white p-3 shadow-sm"
		>
			<!-- Month nav -->
			<div class="flex items-center justify-between mb-2">
				<button
					type="button"
					@click="firstOfMonth = firstOfMonth.subtract(1, 'M')"
					class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
				>
					<FeatherIcon name="chevron-left" class="h-4 w-4" />
				</button>
				<div class="text-sm font-extrabold text-gray-900">
					{{ firstOfMonth.format("MMMM YYYY") }}
				</div>
				<button
					type="button"
					@click="firstOfMonth = firstOfMonth.add(1, 'M')"
					class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
				>
					<FeatherIcon name="chevron-right" class="h-4 w-4" />
				</button>
			</div>

			<!-- Weekday header -->
			<div
				class="grid grid-cols-7 gap-1 mb-1 text-center text-[10px] font-black uppercase tracking-widest text-gray-400"
			>
				<div v-for="day in DAYS" :key="day">{{ day }}</div>
			</div>

			<!-- Days grid -->
			<div class="grid grid-cols-7 gap-1">
				<div
					v-for="i in firstOfMonth.get('d')"
					:key="'pad-' + i"
					class="h-9"
				/>
				<div
					v-for="index in firstOfMonth.endOf('M').get('D')"
					:key="index"
					class="h-9 w-full flex items-center justify-center text-[13px] font-bold rounded-lg relative"
					:class="cellClass(index)"
				>
					<span class="relative z-10">{{ index }}</span>
				</div>
			</div>

			<!-- Legend / summary -->
			<div
				class="mt-3 pt-3 border-t border-gray-100 grid grid-cols-4 gap-2"
			>
				<div
					v-for="status in summaryStatuses"
					:key="status"
					class="rounded-xl bg-gray-50 px-2 py-2 flex flex-col items-center"
				>
					<div class="flex items-center gap-1.5">
						<div
							class="w-2 h-2 rounded-full"
							:class="dotClass[status]"
						/>
						<span
							class="text-[9px] font-black uppercase tracking-widest text-gray-500"
						>
							{{ __(status) }}
						</span>
					</div>
					<div
						class="text-base font-extrabold mt-0.5"
						:class="status === 'Absent' ? 'text-red-600' : 'text-gray-900'"
					>
						{{ summary[status] || 0 }}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { createResource, FeatherIcon } from "frappe-ui"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const today = dayjs().format("YYYY-MM-DD")
const firstOfMonth = ref(dayjs().date(1).startOf("D"))

// Background tint per status — mirrors Leave Application calendar palette so
// the two surfaces feel like one design system.
const cellTint = {
	Present: "bg-green-100 text-green-700",
	"Work From Home": "bg-green-100 text-green-700",
	"Half Day": "bg-amber-100 text-amber-700",
	Absent: "bg-red-100 text-red-700",
	"On Leave": "bg-blue-100 text-blue-700",
	Holiday: "bg-gray-200 text-gray-500 line-through",
}

// Saturated dots for the legend pills (more visible at 8px than the cell tints)
const dotClass = {
	Present: "bg-green-500",
	"Half Day": "bg-amber-500",
	Absent: "bg-red-500",
	"On Leave": "bg-blue-500",
}

// __("Present"), __("Half Day"), __("Absent"), __("On Leave"), __("Work From Home")
const summaryStatuses = ["Present", "Half Day", "Absent", "On Leave"]

// Future dates have no real attendance state — API returns "Absent" for them
// regardless. Today's Absent is also undetermined: a no-show isn't decided
// until EOD, so we treat today-as-Absent the same as a future date. Other
// statuses for today (Present, Half Day, On Leave) still apply.
function isAbsentInferred(date, status) {
	if (status !== "Absent") return false
	return date >= today
}

const summary = computed(() => {
	const out = {}
	for (const [date, status] of Object.entries(calendarEvents.data || {})) {
		if (date > today) continue
		if (isAbsentInferred(date, status)) continue
		const s = status === "Work From Home" ? "Present" : status
		out[s] = (out[s] || 0) + 1
	}
	return out
})

const totalTracked = computed(() =>
	summaryStatuses.reduce((acc, s) => acc + (summary.value[s] || 0), 0)
)

watch(firstOfMonth, () => calendarEvents.fetch())

function cellClass(index) {
	const date = firstOfMonth.value.date(index).format("YYYY-MM-DD")
	const isToday = date === today
	const isFuture = date > today
	const rawEvent = isFuture ? null : calendarEvents.data?.[date]
	// Today's "Absent" is suppressed since the day isn't over — render plain
	const event = rawEvent && isAbsentInferred(date, rawEvent) ? null : rawEvent
	const tint = event && cellTint[event]
	const ring = isToday && (!tint || event === "Holiday")
		? " ring-1 ring-blue-300"
		: ""
	if (tint) return tint + ring
	if (isFuture) return "text-gray-400" + ring
	return "text-gray-700" + ring
}

const getFirstLetter = (s) => Array.from(s.trim())[0]

const DAYS = [
	getFirstLetter(__("Sunday")),
	getFirstLetter(__("Monday")),
	getFirstLetter(__("Tuesday")),
	getFirstLetter(__("Wednesday")),
	getFirstLetter(__("Thursday")),
	getFirstLetter(__("Friday")),
	getFirstLetter(__("Saturday")),
]

const calendarEvents = createResource({
	url: "hrms.api.get_attendance_calendar_events",
	auto: true,
	cache: "hrms:attendance_calendar_events",
	makeParams() {
		return {
			from_date: firstOfMonth.value.format("YYYY-MM-DD"),
			to_date: firstOfMonth.value.endOf("M").format("YYYY-MM-DD"),
		}
	},
})
</script>
