<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<!-- Detail / view flow uses the polished read-only DetailView. The
			     stock FormView surfaces every doctype field — including audit
			     fields the employee should not be touching — so we replace it
			     with a card-based summary that matches the apply-flow styling. -->
			<AttendanceRequestDetailView
				v-if="props.id"
				:id="props.id"
			/>

			<!-- Custom new-request UI -->
			<div
				v-else-if="formFields.data"
				class="bg-[#FBFBFC] min-h-screen pb-[120px]"
			>
				<div
					class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative"
				>
					<!-- Glassy sticky header -->
					<div
						class="flex flex-row bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100 items-center gap-1"
					>
						<Button
							variant="ghost"
							class="!px-2 hover:bg-gray-100 transition-colors"
							@click="router.back()"
						>
							<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
						</Button>
						<div class="flex flex-col ml-1 overflow-hidden">
							<h2
								class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1"
							>
								{{ __("New Attendance Request") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span
									class="text-[10px] font-bold uppercase tracking-widest"
									>{{ __("Mark a day you forgot or worked offsite") }}</span
								>
							</div>
						</div>
					</div>

					<!-- Body -->
					<div class="flex-1 px-4 py-5 sm:p-5 space-y-5">
						<!-- Banner -->
						<div
							v-if="banner.tone === 'red'"
							class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 flex items-start gap-3"
						>
							<FeatherIcon
								name="alert-circle"
								class="h-5 w-5 text-red-600 mt-0.5 shrink-0"
							/>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-extrabold text-red-900">
									{{ banner.title }}
								</div>
								<div class="text-xs text-red-800 mt-0.5">
									{{ banner.subtitle }}
								</div>
							</div>
						</div>
						<div
							v-else-if="banner.tone === 'green'"
							class="rounded-2xl border border-green-200 bg-green-50 px-4 py-3 flex items-start gap-3"
						>
							<FeatherIcon
								name="check-circle"
								class="h-5 w-5 text-green-600 mt-0.5 shrink-0"
							/>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-extrabold text-green-900">
									{{ banner.title }}
								</div>
								<div class="text-xs text-green-800 mt-0.5">
									{{ banner.subtitle }}
								</div>
							</div>
						</div>
						<div
							v-else
							class="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 flex items-start gap-3"
						>
							<FeatherIcon
								name="info"
								class="h-5 w-5 text-blue-600 mt-0.5 shrink-0"
							/>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-extrabold text-blue-900">
									{{ banner.title }}
								</div>
								<div class="text-xs text-blue-800 mt-0.5">
									{{ banner.subtitle }}
								</div>
							</div>
						</div>

						<!-- Hero card (shows once reason + dates picked) -->
						<div
							v-if="
								attendanceRequest.reason &&
								attendanceRequest.from_date &&
								attendanceRequest.to_date
							"
							class="rounded-2xl bg-blue-600 p-5 text-white shadow-sm"
						>
							<div
								class="text-[10px] font-black uppercase tracking-widest text-white/80"
							>
								{{ attendanceRequest.reason }}
							</div>
							<div class="mt-1 text-3xl font-black leading-none">
								{{
									formatRange(
										attendanceRequest.from_date,
										attendanceRequest.to_date
									)
								}}
							</div>
							<div class="mt-1 text-xs font-bold text-white/80">
								{{ totalDays }} {{ __("day", null, "duration") }}{{ totalDays !== 1 ? __("s", null, "duration suffix") : "" }}
								<span v-if="attendanceRequest.half_day"> · {{ __("Half day") }}</span>
							</div>
						</div>

						<!-- Section: Reason -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
								>
									<FeatherIcon name="tag" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Reason") }}
										<span class="text-red-500 ml-0.5">*</span>
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Why are you requesting this?") }}
									</span>
								</div>
							</div>
							<div class="grid grid-cols-2 gap-2.5">
								<button
									v-for="reason in REASON_OPTIONS"
									:key="reason.value"
									type="button"
									@click="attendanceRequest.reason = reason.value"
									class="rounded-2xl border-2 px-3 py-3 text-left transition-all min-h-[64px] flex items-center gap-2.5"
									:class="[
										attendanceRequest.reason === reason.value
											? 'border-blue-600 bg-blue-50 shadow-sm'
											: 'border-gray-100 bg-white hover:border-blue-200',
									]"
								>
									<div
										class="p-1.5 rounded-lg shrink-0"
										:class="[
											attendanceRequest.reason === reason.value
												? 'bg-blue-600 text-white'
												: 'bg-gray-100 text-gray-500',
										]"
									>
										<FeatherIcon :name="reason.icon" class="h-4 w-4" />
									</div>
									<div
										class="text-[13px] font-extrabold leading-tight"
										:class="
											attendanceRequest.reason === reason.value
												? 'text-blue-900'
												: 'text-gray-800'
										"
									>
										{{ __(reason.value) }}
									</div>
								</button>
							</div>
						</section>

						<!-- Section: Dates -->
						<section class="space-y-3">
							<div class="flex items-center justify-between gap-3">
								<div class="flex items-center gap-3 min-w-0">
									<div
										class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
									>
										<FeatherIcon name="calendar" class="h-5 w-5" />
									</div>
									<div class="flex flex-col min-w-0">
										<h3
											class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
										>
											{{ __("Dates") }}
											<span class="text-red-500 ml-0.5">*</span>
										</h3>
										<span
											class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em] truncate"
										>
											<span v-if="!attendanceRequest.reason">
												{{ __("Pick a reason first") }}
											</span>
											<span
												v-else-if="
													pendingRange && attendanceRequest.from_date
												"
											>
												{{ __("Tap end date — or tap same day for 1 day") }}
											</span>
											<span
												v-else-if="
													attendanceRequest.from_date &&
													attendanceRequest.to_date
												"
											>
												{{
													formatRange(
														attendanceRequest.from_date,
														attendanceRequest.to_date
													)
												}}
												· {{ totalDays }} {{ __("days") }}
											</span>
											<span v-else>{{ __("Tap a start date") }}</span>
										</span>
									</div>
								</div>

								<button
									type="button"
									@click="toggleHalfDay()"
									class="rounded-full px-3 py-1.5 text-[10px] font-black uppercase tracking-widest border-2 transition-all whitespace-nowrap shrink-0"
									:class="
										attendanceRequest.half_day
											? 'bg-amber-100 text-amber-700 border-amber-300'
											: 'bg-white text-gray-500 border-gray-200 hover:border-amber-200'
									"
								>
									½ {{ __("Half Day") }}
								</button>
							</div>

							<!-- Inline range calendar -->
							<div
								class="rounded-2xl border border-gray-100 bg-white p-3 shadow-sm"
							>
								<div class="flex items-center justify-between mb-2">
									<button
										type="button"
										@click="prevMonth()"
										class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
									>
										<FeatherIcon name="chevron-left" class="h-4 w-4" />
									</button>
									<div class="text-sm font-extrabold text-gray-900">
										{{ monthLabel }}
									</div>
									<button
										type="button"
										@click="nextMonth()"
										class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
									>
										<FeatherIcon name="chevron-right" class="h-4 w-4" />
									</button>
								</div>

								<div
									class="grid grid-cols-7 gap-1 mb-1 text-center text-[10px] font-black uppercase tracking-widest text-gray-400"
								>
									<div>S</div>
									<div>M</div>
									<div>T</div>
									<div>W</div>
									<div>T</div>
									<div>F</div>
									<div>S</div>
								</div>

								<div class="grid grid-cols-7 gap-1">
									<button
										v-for="(cell, idx) in calendarCells"
										:key="idx"
										type="button"
										:disabled="!isCellTappable(cell)"
										@click="cell.date && pickDate(cell)"
										class="h-9 w-full flex items-center justify-center text-[13px] font-bold rounded-lg transition-all relative"
										:class="cellClass(cell)"
									>
										<span v-if="cell.date" class="relative z-10">
											{{ cell.day }}
										</span>
										<span
											v-if="
												cell.date &&
												isHalfDayDate(cell.date) &&
												attendanceRequest.half_day
											"
											class="absolute -bottom-0.5 right-1 text-[8px] font-black text-amber-600 z-10"
										>
											½
										</span>
									</button>
								</div>

								<div
									class="mt-3 pt-3 border-t border-gray-100 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[10px] font-bold text-gray-500 uppercase tracking-widest"
								>
									<div class="flex items-center gap-1.5">
										<div class="w-2.5 h-2.5 rounded bg-blue-600"></div>
										{{ __("Selected") }}
									</div>
									<div class="flex items-center gap-1.5">
										<div class="w-2.5 h-2.5 rounded bg-blue-100"></div>
										{{ __("In range") }}
									</div>
									<div class="flex items-center gap-1.5">
										<div class="w-2.5 h-2.5 rounded bg-gray-200"></div>
										{{ __("Holiday") }}
									</div>
								</div>
							</div>

							<div
								v-if="dateError"
								class="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-bold text-red-700"
							>
								{{ dateError }}
							</div>

							<!-- Half-day day picker for ranges > 1 day -->
							<div
								v-if="
									attendanceRequest.half_day &&
									attendanceRequest.from_date &&
									attendanceRequest.to_date &&
									attendanceRequest.from_date !== attendanceRequest.to_date
								"
								class="rounded-2xl border border-amber-200 bg-amber-50 p-3"
							>
								<div
									class="text-[10px] font-black uppercase tracking-widest text-amber-700 mb-2"
								>
									{{ __("Which day is the half-day?") }}
								</div>
								<div class="flex flex-wrap gap-2">
									<button
										v-for="d in halfDayChoices"
										:key="d"
										type="button"
										@click="attendanceRequest.half_day_date = d"
										class="rounded-full px-3 py-1.5 text-[11px] font-extrabold border-2 transition-all"
										:class="
											attendanceRequest.half_day_date === d
												? 'bg-amber-500 text-white border-amber-500'
												: 'bg-white text-amber-700 border-amber-200 hover:border-amber-400'
										"
									>
										{{ formatShort(d) }}
									</button>
								</div>
							</div>
						</section>

						<!-- Section: Shift (optional) -->
						<section
							v-if="shiftTypes.data?.length"
							class="space-y-3"
						>
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-purple-50 text-purple-600 shadow-sm border border-purple-100"
								>
									<FeatherIcon name="clock" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Shift") }}
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Which shift were you on? Optional") }}
									</span>
								</div>
							</div>
							<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
								<button
									v-for="shift in shiftTypes.data"
									:key="shift.name"
									type="button"
									@click="
										attendanceRequest.shift =
											attendanceRequest.shift === shift.name
												? null
												: shift.name
									"
									class="rounded-2xl border-2 px-4 py-3 text-left transition-all flex items-center gap-3"
									:class="[
										attendanceRequest.shift === shift.name
											? 'border-purple-500 bg-purple-50 shadow-sm'
											: 'border-gray-100 bg-white hover:border-purple-200',
									]"
								>
									<div
										class="p-2 rounded-xl shrink-0"
										:class="[
											attendanceRequest.shift === shift.name
												? 'bg-purple-500 text-white'
												: 'bg-gray-100 text-gray-500',
										]"
									>
										<FeatherIcon name="clock" class="h-4 w-4" />
									</div>
									<div class="flex-1 min-w-0">
										<div
											class="text-[13px] font-extrabold leading-tight"
											:class="
												attendanceRequest.shift === shift.name
													? 'text-purple-900'
													: 'text-gray-800'
											"
										>
											{{ shift.name }}
										</div>
										<div class="text-[11px] font-bold text-gray-500 mt-0.5">
											{{ formatTime(shift.start_time) }} –
											{{ formatTime(shift.end_time) }}
										</div>
									</div>
								</button>
							</div>
						</section>

						<!-- Section: Explanation -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-amber-50 text-amber-600 shadow-sm border border-amber-200"
								>
									<FeatherIcon name="edit-3" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Explanation") }}
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Optional — context for your approver") }}
									</span>
								</div>
							</div>
							<textarea
								v-model="attendanceRequest.explanation"
								rows="3"
								:placeholder="
									__('e.g. Working from home today due to internet outage at the office')
								"
								class="w-full rounded-2xl border border-gray-200 bg-white focus:border-blue-300 p-4 text-sm font-medium text-gray-800 transition-all resize-none outline-none placeholder:text-gray-400"
							></textarea>
						</section>
					</div>
				</div>

				<!-- Floating CTA -->
				<div
					class="fixed bottom-0 left-0 right-0 z-50 sm:max-w-4xl sm:mx-auto px-4 pb-4 pt-3 bg-gradient-to-t from-white via-white to-white/0"
				>
					<div
						class="rounded-2xl bg-white border border-gray-200 shadow-lg overflow-hidden flex items-stretch"
					>
						<div class="flex-1 px-4 py-3 min-w-0">
							<div
								class="text-[9px] font-black uppercase tracking-widest text-gray-400"
							>
								{{ ctaSummary.label }}
							</div>
							<div
								class="text-sm font-extrabold text-gray-900 mt-0.5 truncate"
							>
								{{ ctaSummary.value }}
							</div>
						</div>
						<button
							type="button"
							@click="saveForm"
							:disabled="saving"
							class="px-5 bg-blue-600 text-white font-black text-xs uppercase tracking-widest disabled:opacity-50 hover:brightness-110 active:scale-[0.98] transition-all flex items-center gap-2"
						>
							<LoadingIndicator
								v-if="saving"
								class="h-4 w-4 text-white"
							/>
							<FeatherIcon v-else name="send" class="h-4 w-4" />
							{{ saving ? __("Saving") : __("Submit") }}
						</button>
					</div>
				</div>
			</div>
		</ion-content>

		<SuccessModal
			:isOpen="successOpen"
			:title="__('Request submitted!')"
			:subtitle="__('Your approver will review and respond shortly.')"
			:reference="successDocName"
			@dismiss="onSuccessDismissed"
		/>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import SuccessModal from "@/components/SuccessModal.vue"
import {
	createResource,
	createListResource,
	Button,
	FeatherIcon,
	LoadingIndicator,
	toast,
} from "frappe-ui"
import { computed, ref, watch, inject } from "vue"
import { useRouter } from "vue-router"

import AttendanceRequestDetailView from "@/components/AttendanceRequestDetailView.vue"
import { showErrorFromException } from "@/data/errorModal"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const today = dayjs().format("YYYY-MM-DD")
const router = useRouter()

const props = defineProps({
	id: { type: String, required: false },
})

const sessionEmployee = inject("$employee")
const currEmployee = ref(sessionEmployee.data.name)
const employeeCompany = ref(sessionEmployee.data.company)
const dateError = ref("")
const saving = ref(false)

const attendanceRequest = ref({
	half_day: 0,
	include_holidays: 0,
})

const REASON_OPTIONS = [
	{ value: "Work From Home", icon: "home" },
	{ value: "On Duty", icon: "briefcase" },
]

// formFields stays around for the edit/detail FormView fallback
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Attendance Request" },
	auto: true,
	transform(data) {
		if (props.id) return data
		return data.filter(
			(f) =>
				!["employee", "employee_name", "status", "company"].includes(
					f.fieldname
				)
		)
	},
})

const shiftTypes = createResource({
	url: "frappe.client.get_list",
	params: {
		doctype: "Shift Type",
		fields: ["name", "start_time", "end_time"],
		limit_page_length: 50,
	},
	auto: true,
})

// Holiday tints for the calendar. The API returns holidays of three flavours
// (`fixed`, `optional`, `weekly_off`) — bucket them separately so AR can
// continue to allow taps on weekends / holidays (an employee may legitimately
// have worked on a Saturday, on Good Friday, etc.) while still tinting the
// cell so the user knows they're picking a non-working day.
const fixedHolidayDates = ref(new Set())
const weeklyOffDates = ref(new Set())
const optionalHolidayDates = ref(new Set())
const calendarWindow = {
	from: dayjs().subtract(6, "month").startOf("month").format("YYYY-MM-DD"),
	to: dayjs().add(6, "month").endOf("month").format("YYYY-MM-DD"),
}
createResource({
	url: "myhr.api.get_leave_calendar_data",
	params: {
		employee: currEmployee.value,
		from_date: calendarWindow.from,
		to_date: calendarWindow.to,
	},
	auto: true,
	onSuccess(data) {
		const fixed = new Set()
		const weekly = new Set()
		const optional = new Set()
		;(data?.holidays || []).forEach((h) => {
			if (!h.date) return
			if (h.type === "weekly_off") weekly.add(h.date)
			else if (h.type === "optional") optional.add(h.date)
			else fixed.add(h.date)
		})
		fixedHolidayDates.value = fixed
		weeklyOffDates.value = weekly
		optionalHolidayDates.value = optional
	},
})

watch(
	() => [
		attendanceRequest.value.from_date,
		attendanceRequest.value.to_date,
		attendanceRequest.value.half_day,
		attendanceRequest.value.half_day_date,
	],
	() => validateDates()
)

// ----- calendar -----
const cursor = ref(dayjs())
const pendingRange = ref(false)
const monthLabel = computed(() => cursor.value.format("MMMM YYYY"))

const calendarCells = computed(() => {
	const startOfMonth = cursor.value.startOf("month")
	const endOfMonth = cursor.value.endOf("month")
	const startWeekday = startOfMonth.day()
	const daysInMonth = endOfMonth.date()

	const cells = []
	for (let i = 0; i < startWeekday; i++) cells.push({ date: null })
	for (let d = 1; d <= daysInMonth; d++) {
		const date = startOfMonth.date(d).format("YYYY-MM-DD")
		const isFixedHoliday = fixedHolidayDates.value.has(date)
		const isWeeklyOff = weeklyOffDates.value.has(date)
		const isOptionalHoliday = optionalHolidayDates.value.has(date)
		const isPast = date < today
		cells.push({ date, day: d, isFixedHoliday, isWeeklyOff, isOptionalHoliday, isPast })
	}
	while (cells.length % 7 !== 0) cells.push({ date: null })
	return cells
})

function prevMonth() {
	cursor.value = cursor.value.subtract(1, "month")
}
function nextMonth() {
	cursor.value = cursor.value.add(1, "month")
}

function isCellTappable(cell) {
	if (!cell.date) return false
	if (!attendanceRequest.value.reason) return false
	// AR is for forgot-to-checkin / WFH on past or current dates — future-
	// dated AR doesn't make sense (can't be present for a day that hasn't
	// happened) and the controller may reject it.
	if (cell.date > today) return false
	// Weekends and holidays remain tappable — an AR is precisely for "I worked
	// on a non-working day" or "I forgot to check in", so a Saturday WFH or a
	// fixed-holiday on-duty day must be selectable. The cell styling in
	// `cellClass` keeps the visual distinction so the user knows it's a
	// non-working day.
	return true
}

function pickDate(cell) {
	if (!cell.date) return
	if (!isCellTappable(cell)) return
	const date = cell.date
	const fd = attendanceRequest.value.from_date

	if (!fd || !pendingRange.value) {
		attendanceRequest.value.from_date = date
		attendanceRequest.value.to_date = date
		attendanceRequest.value.half_day_date = attendanceRequest.value.half_day
			? date
			: null
		pendingRange.value = true
		return
	}
	if (date < fd) {
		attendanceRequest.value.from_date = date
		attendanceRequest.value.to_date = fd
	} else if (date > fd) {
		attendanceRequest.value.to_date = date
	}
	pendingRange.value = false
	if (
		attendanceRequest.value.half_day &&
		!attendanceRequest.value.half_day_date
	) {
		attendanceRequest.value.half_day_date = attendanceRequest.value.from_date
	}
}

function cellClass(cell) {
	if (!cell.date) return "opacity-0 pointer-events-none"
	const fd = attendanceRequest.value.from_date
	const td = attendanceRequest.value.to_date
	const date = cell.date
	const noReason = !attendanceRequest.value.reason
	const isAnchor = pendingRange.value && fd === date
	const isStart = fd === date
	const isEnd = td === date && fd !== td
	const isOnlyPick = fd === td && fd === date && !pendingRange.value
	const inRange = fd && td && date > fd && date < td
	const isToday = date === today

	const base = []
	if (isAnchor) {
		base.push(
			"bg-blue-600 text-white shadow-sm ring-2 ring-blue-300 ring-offset-1 animate-pulse"
		)
	} else if (isOnlyPick || isStart || isEnd) {
		base.push("bg-blue-600 text-white shadow-sm")
	} else if (inRange) {
		base.push("bg-blue-100 text-blue-700")
	} else if (cell.isFixedHoliday) {
		// Fixed holiday — tinted but still tappable (AR is for days you worked).
		base.push("bg-amber-50 text-amber-800 hover:bg-amber-100")
	} else if (cell.isWeeklyOff) {
		// Weekly off — subtle gray tint to mark "non-working day", still tappable.
		base.push("bg-gray-50 text-gray-500 hover:bg-blue-50")
	} else if (cell.isOptionalHoliday) {
		// Optional holiday — same tint family as fixed but lighter.
		base.push("text-amber-700 hover:bg-amber-50")
	} else if (noReason) {
		base.push("text-gray-300 cursor-not-allowed")
	} else {
		base.push("text-gray-700 hover:bg-blue-50")
	}
	if (isToday && !(isStart || isEnd || isOnlyPick || isAnchor))
		base.push("ring-1 ring-blue-300")
	return base.join(" ")
}

function isHalfDayDate(date) {
	return attendanceRequest.value.half_day_date === date
}

const halfDayChoices = computed(() => {
	const fd = attendanceRequest.value.from_date
	const td = attendanceRequest.value.to_date
	if (!fd || !td) return []
	if (fd === td) return [fd]
	return [fd, td]
})

function toggleHalfDay() {
	const next = attendanceRequest.value.half_day ? 0 : 1
	attendanceRequest.value.half_day = next
	if (!next) {
		attendanceRequest.value.half_day_date = null
	} else {
		attendanceRequest.value.half_day_date =
			attendanceRequest.value.from_date || null
	}
}

function validateDates() {
	const fd = attendanceRequest.value.from_date
	const td = attendanceRequest.value.to_date
	if (!(fd && td)) {
		dateError.value = ""
		return
	}
	dateError.value = fd > td ? __("To Date cannot be before From Date") : ""
}

function validateForm() {
	attendanceRequest.value.employee = currEmployee.value
	attendanceRequest.value.company = employeeCompany.value
}

function formatRange(fd, td) {
	if (!fd) return ""
	if (!td || fd === td) return dayjs(fd).format("MMM D")
	const a = dayjs(fd)
	const b = dayjs(td)
	if (a.month() === b.month()) return `${a.format("MMM D")} – ${b.format("D")}`
	return `${a.format("MMM D")} – ${b.format("MMM D")}`
}

function formatShort(d) {
	return dayjs(d).format("ddd, MMM D")
}

function formatTime(t) {
	if (!t) return ""
	const [h, m] = String(t).split(":")
	const hh = parseInt(h, 10)
	const mm = m || "00"
	const ampm = hh >= 12 ? "PM" : "AM"
	const display = hh % 12 || 12
	return `${display}:${mm} ${ampm}`
}

const totalDays = computed(() => {
	const fd = attendanceRequest.value.from_date
	const td = attendanceRequest.value.to_date
	if (!fd || !td) return 0
	return dayjs(td).diff(dayjs(fd), "day") + 1
})

const banner = computed(() => {
	if (dateError.value)
		return { tone: "red", title: __("Heads up"), subtitle: dateError.value }
	if (
		attendanceRequest.value.reason &&
		attendanceRequest.value.from_date &&
		attendanceRequest.value.to_date
	)
		return {
			tone: "green",
			title: __("Looks good"),
			subtitle: __(
				"Your approver will be notified when you submit."
			),
		}
	return {
		tone: "blue",
		title: __("Pick a reason and dates"),
		subtitle: __(
			"This files a request to mark you present for the chosen days."
		),
	}
})

const ctaSummary = computed(() => {
	const r = attendanceRequest.value.reason
	const fd = attendanceRequest.value.from_date
	const td = attendanceRequest.value.to_date
	if (r && fd && td)
		return {
			label: __("{0} days · {1}", [totalDays.value, formatRange(fd, td)]),
			value: r,
		}
	if (r)
		return { label: __("Step 2 of 2"), value: __("Pick dates to continue") }
	return { label: __("Step 1 of 2"), value: __("Pick a reason") }
})

// Success modal state — replaces the old toast + immediate redirect.
const successOpen = ref(false)
const successDocName = ref("")
function onSuccessDismissed() {
	successOpen.value = false
	router.replace({ name: "AttendanceRequestListView" })
}

const docList = createListResource({
	doctype: "Attendance Request",
	insert: {
		onSuccess(data) {
			successDocName.value = data?.name || ""
			successOpen.value = true
		},
		onError(err) {
			saving.value = false
			console.error("Error creating Attendance Request", err)
			showErrorFromException(err, __("Error creating Attendance Request"))
		},
	},
})

function saveForm() {
	validateForm()
	if (!attendanceRequest.value.reason) {
		toast({
			title: __("Pick a reason"),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-amber-500",
		})
		return
	}
	if (!attendanceRequest.value.from_date || !attendanceRequest.value.to_date) {
		toast({
			title: __("Pick a date range"),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-amber-500",
		})
		return
	}
	if (dateError.value) {
		toast({
			title: dateError.value,
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
		return
	}
	saving.value = true
	docList.insert.submit(attendanceRequest.value)
}
</script>
