<template>
	<BaseLayout pageTitle="Attendance">
		<template #body>
			<div class="flex flex-col mt-7 mb-7 p-4 gap-7">
				<AttendanceCalendar />
				<div class="w-full">
					<router-link
						:to="{ name: 'AttendanceRequestFormView' }"
						v-slot="{ navigate }"
					>
						<button
							@click="navigate"
							class="w-full py-4 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2"
						>
							<FeatherIcon name="plus-circle" class="h-4 w-4" />
							{{ __("Request Attendance") }}
						</button>
					</router-link>
				</div>
				<div>
					<div class="flex items-center justify-between mb-2">
						<div class="text-lg text-gray-800 font-bold">
							{{ __("Attendance Requests") }}
						</div>
					</div>
					<TabButtons
						:buttons="REQUEST_TABS"
						v-model="activeRequestTab"
					/>
					<RequestList
						v-if="activeRequestTab === 'My Requests'"
						:component="markRaw(AttendanceRequestItem)"
						:items="myAttendanceRequests?.data?.slice(0, 5)"
						:addListButton="true"
						:listButtonRoute="__('AttendanceRequestListView')"
						:emptyStateMessage="__('You have not raised any Attendance Requests')"
					/>
					<RequestList
						v-else
						:component="markRaw(AttendanceRequestItem)"
						:items="teamAttendanceRequests?.data?.slice(0, 5)"
						:teamRequests="true"
						:addListButton="true"
						:listButtonRoute="__('AttendanceRequestListView')"
						:emptyStateMessage="__('No team Attendance Requests waiting on you')"
					/>
				</div>
				<div>
					<div class="text-lg text-gray-800 font-bold">
						{{ __("Upcoming Shifts") }}
					</div>
					<RequestList
						:component="markRaw(ShiftAssignmentItem)"
						:items="upcomingShifts"
						:addListButton="true"
						listButtonRoute="ShiftAssignmentListView"
						:emptyStateMessage="__('You have no upcoming shifts')"
					/>
				</div>
				<div class="w-full">
					<router-link
						:to="{ name: 'ShiftRequestFormView' }"
						v-slot="{ navigate }"
					>
						<button
							@click="navigate"
							class="w-full py-4 rounded-2xl bg-white border-2 border-gray-200 text-gray-900 font-black text-xs uppercase tracking-widest hover:border-blue-300 hover:text-blue-700 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
						>
							<FeatherIcon name="clock" class="h-4 w-4" />
							{{ __("Request a Shift") }}
						</button>
					</router-link>
				</div>
				<div>
					<div class="text-lg text-gray-800 font-bold">
						{{ __("Recent Shift Requests") }}
					</div>
					<RequestList
						:component="markRaw(ShiftRequestItem)"
						:items="myShiftRequests?.data?.slice(0, 5)"
						:addListButton="true"
						listButtonRoute="ShiftRequestListView"
					/>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, markRaw, ref } from "vue"
import { createResource, FeatherIcon } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"
import ShiftAssignmentItem from "@/components/ShiftAssignmentItem.vue"
import RequestList from "@/components/RequestList.vue"
import TabButtons from "@/components/TabButtons.vue"
import AttendanceCalendar from "@/components/AttendanceCalendar.vue"

import {
	getShiftDates,
	getTotalShiftDays,
	getShiftTiming,
	myAttendanceRequests,
	myShiftRequests,
	teamAttendanceRequests,
} from "@/data/attendance"

// Same My/Team split that lives on Home — replicated here so an approver
// landing on Attendance from a notification finds the request waiting on
// them without bouncing back to the home tab.
const REQUEST_TABS = ["My Requests", "Team Requests"] // __("My Requests"), __("Team Requests")
const activeRequestTab = ref("My Requests")

const dayjs = inject("$dayjs")

const shifts = createResource({
	url: "hrms.api.get_shifts",
	auto: true,
	cache: "hrms:shifts",
	transform: (data) => {
		return data.map((assignment) => {
			assignment.doctype = "Shift Assignment"
			assignment.is_upcoming =
				!assignment.end_date || dayjs(assignment.end_date).isAfter(dayjs())
			assignment.shift_dates = getShiftDates(assignment)
			assignment.total_shift_days = getTotalShiftDays(assignment)
			assignment.shift_timing = getShiftTiming(assignment)
			return assignment
		})
	},
})

const upcomingShifts = computed(() => {
	const filteredShifts = shifts.data?.filter((shift) => shift.is_upcoming)
	return filteredShifts?.slice(0, 5)
})
</script>
