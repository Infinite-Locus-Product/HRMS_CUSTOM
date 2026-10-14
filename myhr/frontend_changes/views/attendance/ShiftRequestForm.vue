<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<!-- Detail / view flow uses the polished read-only DetailView, in
			     line with the LA / AR / Expense Claim treatment. -->
			<ShiftRequestDetailView
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
								{{ __("New Shift Request") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span
									class="text-[10px] font-bold uppercase tracking-widest"
									>{{ __("Request a different shift") }}</span
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

						<!-- Hero shift card -->
						<div
							v-if="selectedShift"
							class="rounded-2xl bg-blue-600 p-5 text-white shadow-sm"
						>
							<div class="flex items-start justify-between gap-3">
								<div class="min-w-0">
									<div
										class="text-[10px] font-black uppercase tracking-widest text-white/80 truncate"
									>
										{{ selectedShift.name }}
									</div>
									<div class="mt-1 text-3xl font-black leading-none">
										{{ formatTime(selectedShift.start_time) }}
										<span class="text-white/60">–</span>
										{{ formatTime(selectedShift.end_time) }}
									</div>
									<div class="mt-1 text-xs font-bold text-white/80">
										{{ shiftDuration(selectedShift) }} {{ __("hour shift") }}
									</div>
								</div>
								<div
									class="rounded-xl bg-white/15 px-3 py-2 shrink-0 text-right"
								>
									<div
										class="text-[9px] font-black uppercase tracking-widest text-white/80"
									>
										{{ __("Shift") }}
									</div>
									<FeatherIcon
										name="clock"
										class="h-5 w-5 text-white mt-0.5 ml-auto"
									/>
								</div>
							</div>
							<div
								v-if="
									shiftRequest.from_date && shiftRequest.to_date
								"
								class="mt-4 grid grid-cols-2 gap-2"
							>
								<div class="rounded-xl bg-white/15 px-3 py-2">
									<div
										class="text-[9px] font-black uppercase tracking-widest text-white/80"
									>
										{{ __("From") }}
									</div>
									<div class="text-sm font-extrabold mt-0.5">
										{{ formatDate(shiftRequest.from_date) }}
									</div>
								</div>
								<div class="rounded-xl bg-white/15 px-3 py-2">
									<div
										class="text-[9px] font-black uppercase tracking-widest text-white/80"
									>
										{{ __("Days") }}
									</div>
									<div class="text-sm font-extrabold mt-0.5">
										{{ totalDays }} {{ __("days") }}
									</div>
								</div>
							</div>
						</div>

						<!-- Section: Shift Type -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
								>
									<FeatherIcon name="layers" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Shift Type") }}
										<span class="text-red-500 ml-0.5">*</span>
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Pick the shift you want to work") }}
									</span>
								</div>
							</div>
							<div
								v-if="!shiftTypes.data?.length"
								class="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-center text-xs font-bold uppercase tracking-widest text-gray-400"
							>
								{{ __("Loading shift types…") }}
							</div>
							<div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-2">
								<button
									v-for="shift in shiftTypes.data"
									:key="shift.name"
									type="button"
									@click="shiftRequest.shift_type = shift.name"
									class="rounded-2xl border-2 px-4 py-3 text-left transition-all flex items-center gap-3 min-h-[64px]"
									:class="[
										shiftRequest.shift_type === shift.name
											? 'border-blue-600 bg-blue-50 shadow-sm'
											: 'border-gray-100 bg-white hover:border-blue-200',
									]"
								>
									<div
										class="p-2 rounded-xl shrink-0"
										:class="[
											shiftRequest.shift_type === shift.name
												? 'bg-blue-600 text-white'
												: 'bg-gray-100 text-gray-500',
										]"
									>
										<FeatherIcon
											:name="shiftIcon(shift.name)"
											class="h-4 w-4"
										/>
									</div>
									<div class="flex-1 min-w-0">
										<div
											class="text-[13px] font-extrabold leading-tight"
											:class="
												shiftRequest.shift_type === shift.name
													? 'text-blue-900'
													: 'text-gray-800'
											"
										>
											{{ shift.name }}
										</div>
										<div
											class="text-[11px] font-bold mt-0.5"
											:class="
												shiftRequest.shift_type === shift.name
													? 'text-blue-700'
													: 'text-gray-500'
											"
										>
											{{ formatTime(shift.start_time) }} –
											{{ formatTime(shift.end_time) }}
										</div>
									</div>
									<FeatherIcon
										v-if="shiftRequest.shift_type === shift.name"
										name="check-circle"
										class="h-5 w-5 text-blue-600 shrink-0"
									/>
								</button>
							</div>
						</section>

						<!-- Section: Dates -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
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
										<span v-if="!shiftRequest.shift_type">
											{{ __("Pick a shift type first") }}
										</span>
										<span v-else-if="pendingRange && shiftRequest.from_date">
											{{ __("Tap end date — or tap same day for 1 day") }}
										</span>
										<span
											v-else-if="
												shiftRequest.from_date && shiftRequest.to_date
											"
										>
											{{
												formatRange(
													shiftRequest.from_date,
													shiftRequest.to_date
												)
											}}
											· {{ totalDays }} {{ __("days") }}
										</span>
										<span v-else>{{ __("Tap a start date") }}</span>
									</span>
								</div>
							</div>

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
						</section>

						<!-- Section: Approver -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-green-50 text-green-600 shadow-sm border border-green-100"
								>
									<FeatherIcon name="user-check" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Approver") }}
										<span class="text-red-500 ml-0.5">*</span>
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Who reviews this request") }}
									</span>
								</div>
							</div>

							<div
								v-if="approverOptions.length > 1"
								class="space-y-2"
							>
								<button
									v-for="opt in approverOptions"
									:key="opt.value"
									type="button"
									@click="shiftRequest.approver = opt.value"
									class="w-full rounded-2xl border-2 px-4 py-3 text-left transition-all flex items-center gap-3"
									:class="
										shiftRequest.approver === opt.value
											? 'border-green-500 bg-green-50'
											: 'border-gray-100 bg-white hover:border-green-200'
									"
								>
									<div
										class="w-9 h-9 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-black text-sm shrink-0 border border-green-200"
									>
										{{ initials(opt.name) }}
									</div>
									<div class="flex-1 min-w-0">
										<div
											class="text-sm font-extrabold text-gray-900 truncate"
										>
											{{ opt.name || opt.value }}
										</div>
										<div
											class="text-[11px] font-bold text-gray-500 truncate"
										>
											{{ opt.value }}
										</div>
									</div>
									<FeatherIcon
										v-if="shiftRequest.approver === opt.value"
										name="check-circle"
										class="h-5 w-5 text-green-600 shrink-0"
									/>
								</button>
							</div>

							<div
								v-else-if="approverOptions.length === 1"
								class="rounded-2xl border border-gray-100 bg-white px-4 py-3 flex items-center gap-3"
							>
								<div
									class="w-9 h-9 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-black text-sm shrink-0 border border-green-200"
								>
									{{ initials(approverOptions[0].name) }}
								</div>
								<div class="flex-1 min-w-0">
									<div class="text-sm font-extrabold text-gray-900 truncate">
										{{ approverOptions[0].name || approverOptions[0].value }}
									</div>
									<div class="text-[11px] font-bold text-gray-500 truncate">
										{{ approverOptions[0].value }}
									</div>
								</div>
								<span
									class="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md bg-green-50 text-green-600 border border-green-100"
								>
									{{ __("Auto-assigned") }}
								</span>
							</div>
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
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
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

import ShiftRequestDetailView from "@/components/ShiftRequestDetailView.vue"
import { showErrorFromException } from "@/data/errorModal"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const today = dayjs().format("YYYY-MM-DD")
const router = useRouter()

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

const sessionEmployee = inject("$employee")
const currEmployee = ref(sessionEmployee.data.name)
const dateError = ref("")
const saving = ref(false)

const shiftRequest = ref({
	status: "Draft",
})

// formFields kept around for the edit/detail FormView fallback
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Shift Request" },
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

const approverOptionsRaw = ref([])
const approverOptions = computed(() => approverOptionsRaw.value)

createResource({
	url: "hrms.api.get_shift_request_approvers",
	params: { employee: currEmployee.value },
	auto: !props.id,
	onSuccess(data) {
		approverOptionsRaw.value = (data || []).map((a) => ({
			value: a.name,
			name: a.full_name,
		}))
		if (!shiftRequest.value.approver && data?.[0]?.name) {
			shiftRequest.value.approver = data[0].name
		}
	},
})

// Reuse the leave calendar endpoint solely for holidays. Cheap and
// consistent — server returns leave_applications too but we just ignore them.
const fixedHolidayDates = ref(new Set())
const calendarWindow = {
	from: dayjs().subtract(6, "month").startOf("month").format("YYYY-MM-DD"),
	to: dayjs().add(6, "month").endOf("month").format("YYYY-MM-DD"),
}
const calendarData = createResource({
	url: "myhr.api.get_leave_calendar_data",
	params: {
		employee: currEmployee.value,
		from_date: calendarWindow.from,
		to_date: calendarWindow.to,
	},
	auto: true,
	onSuccess(data) {
		const fixed = new Set()
		;(data?.holidays || []).forEach((h) => {
			if (h.date) fixed.add(h.date)
		})
		fixedHolidayDates.value = fixed
	},
})

const selectedShift = computed(() => {
	if (!shiftRequest.value.shift_type) return null
	return (shiftTypes.data || []).find(
		(s) => s.name === shiftRequest.value.shift_type
	)
})

watch(
	() => [shiftRequest.value.from_date, shiftRequest.value.to_date],
	() => validateDates()
)

function shiftIcon(name) {
	const n = (name || "").toLowerCase()
	if (n.includes("morning")) return "sunrise"
	if (n.includes("evening")) return "sunset"
	if (n.includes("night")) return "moon"
	if (n.includes("general") || n.includes("day")) return "sun"
	return "clock"
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

function shiftDuration(s) {
	if (!s?.start_time || !s?.end_time) return "—"
	const start = dayjs(`2000-01-01 ${s.start_time}`)
	let end = dayjs(`2000-01-01 ${s.end_time}`)
	// Treat equal start/end as a 24-hour rolling shift, not a 0-hour shift
	if (end.isSame(start) || end.isBefore(start)) end = end.add(1, "day")
	const hrs = end.diff(start, "minute") / 60
	return Number.isInteger(hrs) ? hrs : hrs.toFixed(1)
}

function formatDate(d) {
	if (!d) return ""
	return dayjs(d).format("MMM D")
}

function formatRange(fd, td) {
	if (!fd) return ""
	if (!td || fd === td) return dayjs(fd).format("MMM D")
	const a = dayjs(fd)
	const b = dayjs(td)
	if (a.month() === b.month())
		return `${a.format("MMM D")} – ${b.format("D")}`
	return `${a.format("MMM D")} – ${b.format("MMM D")}`
}

function initials(name) {
	if (!name) return "?"
	return name
		.split(" ")
		.filter(Boolean)
		.map((s) => s[0])
		.slice(0, 2)
		.join("")
		.toUpperCase()
}

const totalDays = computed(() => {
	const fd = shiftRequest.value.from_date
	const td = shiftRequest.value.to_date
	if (!fd || !td) return 0
	return dayjs(td).diff(dayjs(fd), "day") + 1
})

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
		const isPast = date < today
		cells.push({ date, day: d, isFixedHoliday, isPast })
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
	if (!shiftRequest.value.shift_type) return false
	if (cell.isPast) return false
	if (cell.isFixedHoliday) return false
	return true
}

function pickDate(cell) {
	if (!cell.date) return
	if (!isCellTappable(cell)) return
	const date = cell.date
	const fd = shiftRequest.value.from_date

	if (!fd || !pendingRange.value) {
		shiftRequest.value.from_date = date
		shiftRequest.value.to_date = date
		pendingRange.value = true
		return
	}

	if (date < fd) {
		shiftRequest.value.from_date = date
		shiftRequest.value.to_date = fd
	} else if (date > fd) {
		shiftRequest.value.to_date = date
	}
	pendingRange.value = false
}

function cellClass(cell) {
	if (!cell.date) return "opacity-0 pointer-events-none"
	const fd = shiftRequest.value.from_date
	const td = shiftRequest.value.to_date
	const date = cell.date
	const noShift = !shiftRequest.value.shift_type
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
		base.push("bg-gray-200 text-gray-500 line-through cursor-not-allowed")
	} else if (cell.isPast) {
		base.push("text-gray-300 cursor-not-allowed")
	} else if (noShift) {
		base.push("text-gray-300 cursor-not-allowed")
	} else {
		base.push("text-gray-700 hover:bg-blue-50")
	}
	if (isToday && !(isStart || isEnd || isOnlyPick || isAnchor))
		base.push("ring-1 ring-blue-300")
	return base.join(" ")
}

function validateDates() {
	const fd = shiftRequest.value.from_date
	const td = shiftRequest.value.to_date
	if (!(fd && td)) {
		dateError.value = ""
		return
	}
	dateError.value = fd > td ? __("To Date cannot be before From Date") : ""
}

function validateForm() {
	shiftRequest.value.employee = currEmployee.value
}

const banner = computed(() => {
	if (dateError.value)
		return { tone: "red", title: __("Heads up"), subtitle: dateError.value }
	if (
		shiftRequest.value.shift_type &&
		shiftRequest.value.from_date &&
		shiftRequest.value.to_date
	)
		return {
			tone: "green",
			title: __("Looks good"),
			subtitle: __(
				"{0} will be notified when you submit.",
				[approverName.value || __("Your approver")]
			),
		}
	return {
		tone: "blue",
		title: __("Pick a shift and dates"),
		subtitle: __("You'll see the timing breakdown as you go."),
	}
})

const approverName = computed(() => {
	const opt = approverOptionsRaw.value.find(
		(o) => o.value === shiftRequest.value.approver
	)
	return opt?.name || ""
})

const ctaSummary = computed(() => {
	const fd = shiftRequest.value.from_date
	const td = shiftRequest.value.to_date
	if (fd && td && shiftRequest.value.shift_type)
		return {
			label: __("{0} days · {1}", [
				totalDays.value,
				formatRange(fd, td),
			]),
			value: shiftRequest.value.shift_type,
		}
	if (shiftRequest.value.shift_type)
		return {
			label: __("Step 2 of 2"),
			value: __("Pick dates to continue"),
		}
	return {
		label: __("Step 1 of 2"),
		value: __("Pick a shift type"),
	}
})

const docList = createListResource({
	doctype: "Shift Request",
	insert: {
		onSuccess() {
			toast({
				title: __("Success"),
				text: __("Shift Request created successfully!"),
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
			router.replace({ name: "ShiftRequestListView" })
		},
		onError(err) {
			saving.value = false
			console.error("Error creating Shift Request", err)
			showErrorFromException(err, __("Error creating Shift Request"))
		},
	},
})

function saveForm() {
	validateForm()
	if (!shiftRequest.value.shift_type) {
		toast({
			title: __("Pick a shift type"),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-amber-500",
		})
		return
	}
	if (!shiftRequest.value.from_date || !shiftRequest.value.to_date) {
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
	if (!shiftRequest.value.approver) {
		toast({
			title: __("Pick an approver"),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-amber-500",
		})
		return
	}
	saving.value = true
	docList.insert.submit(shiftRequest.value)
}
</script>
