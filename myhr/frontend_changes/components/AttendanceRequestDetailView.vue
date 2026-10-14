<template>
	<div class="bg-[#FBFBFC] min-h-screen pb-[120px]">
		<div
			class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative"
		>
			<!-- Glassy sticky header -->
			<div
				class="flex flex-row bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100 items-center gap-2"
			>
				<Button
					variant="ghost"
					class="!px-2 hover:bg-gray-100 transition-colors"
					@click="router.back()"
				>
					<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
				</Button>
				<div class="flex flex-col ml-1 overflow-hidden flex-1 min-w-0">
					<h2
						class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1"
					>
						{{ __("Attendance Request") }}
					</h2>
					<div class="flex items-center gap-1.5">
						<div
							class="text-[10px] font-bold uppercase tracking-widest text-gray-400 truncate"
						>
							{{ props.id }}
						</div>
					</div>
				</div>
				<Badge
					v-if="status"
					:label="__(status)"
					:theme="statusTone.theme"
					variant="subtle"
					size="md"
				/>
			</div>

			<!-- Body -->
			<div v-if="ready" class="flex-1 px-4 py-5 sm:p-5 space-y-4">
				<!-- Status banner -->
				<div
					class="rounded-2xl border px-4 py-3 flex items-start gap-3"
					:class="statusTone.banner"
				>
					<FeatherIcon
						:name="statusTone.icon"
						class="h-5 w-5 mt-0.5 shrink-0"
						:class="statusTone.iconColor"
					/>
					<div class="flex-1 min-w-0">
						<div class="text-sm font-extrabold" :class="statusTone.title">
							{{ statusTone.heading }}
						</div>
						<div class="text-xs mt-0.5" :class="statusTone.body">
							{{ statusTone.subtitle }}
						</div>
						<div
							v-if="rejectionReason"
							class="mt-2 rounded-lg bg-white/70 border border-red-200 px-3 py-2 text-xs text-red-900 italic"
						>
							"{{ rejectionReason }}"
						</div>
					</div>
				</div>

				<!-- Date hero -->
				<div
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm"
				>
					<div
						class="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2"
					>
						{{ __("When") }}
					</div>
					<div class="flex items-baseline gap-2 flex-wrap">
						<div class="text-2xl font-extrabold text-gray-900 leading-none">
							{{ heroDate }}
						</div>
						<div
							v-if="totalDays"
							class="text-sm font-bold text-blue-600 whitespace-nowrap"
						>
							· {{ totalDays }} {{ totalDays === 1 ? __("day") : __("days") }}
						</div>
					</div>
					<div
						v-if="metaChips.length"
						class="mt-3 flex flex-wrap gap-2"
					>
						<span
							v-for="chip in metaChips"
							:key="chip.label"
							class="inline-flex items-center gap-1 rounded-full bg-gray-50 border border-gray-100 px-2.5 py-1 text-[11px] font-bold text-gray-700"
						>
							<FeatherIcon :name="chip.icon" class="h-3 w-3" />
							{{ chip.label }}
						</span>
					</div>
				</div>

				<!-- Reason card -->
				<div
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm"
				>
					<div
						class="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2"
					>
						{{ __("Reason") }}
					</div>
					<div class="flex items-center gap-2 flex-wrap">
						<span
							class="inline-flex items-center gap-1.5 rounded-full bg-blue-50 text-blue-700 px-3 py-1 text-xs font-bold"
						>
							<FeatherIcon name="bookmark" class="h-3 w-3" />
							{{ doc.reason || __("Not specified") }}
						</span>
					</div>
					<p
						v-if="doc.explanation"
						class="mt-3 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed"
					>
						{{ doc.explanation }}
					</p>
					<p
						v-else
						class="mt-3 text-xs text-gray-400 italic"
					>
						{{ __("No additional explanation was provided.") }}
					</p>
				</div>

				<!-- Employee + filed-on summary -->
				<div
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm space-y-2.5"
				>
					<div class="flex items-center justify-between gap-3">
						<div class="text-xs font-semibold text-gray-500">
							{{ __("Filed by") }}
						</div>
						<div class="text-sm font-bold text-gray-900 truncate">
							{{ doc.employee_name || doc.employee }}
						</div>
					</div>
					<div
						v-if="doc.department"
						class="flex items-center justify-between gap-3"
					>
						<div class="text-xs font-semibold text-gray-500">
							{{ __("Department") }}
						</div>
						<div class="text-sm font-bold text-gray-900 truncate">
							{{ doc.department }}
						</div>
					</div>
					<div
						v-if="doc.shift"
						class="flex items-center justify-between gap-3"
					>
						<div class="text-xs font-semibold text-gray-500">
							{{ __("Shift") }}
						</div>
						<div class="text-sm font-bold text-gray-900 truncate">
							{{ doc.shift }}
						</div>
					</div>
					<div
						v-if="doc.creation"
						class="flex items-center justify-between gap-3"
					>
						<div class="text-xs font-semibold text-gray-500">
							{{ __("Filed on") }}
						</div>
						<div class="text-sm font-bold text-gray-900 truncate">
							{{ formatDateTime(doc.creation) }}
						</div>
					</div>
					<div
						v-if="doc.custom_approved_by"
						class="flex items-center justify-between gap-3"
					>
						<div class="text-xs font-semibold text-gray-500">
							{{ __("Approved by") }}
						</div>
						<div class="text-sm font-bold text-gray-900 truncate">
							{{ doc.custom_approved_by }}
						</div>
					</div>
				</div>
			</div>

			<!-- Loading state -->
			<div
				v-else
				class="flex-1 flex items-center justify-center py-20 text-gray-400"
			>
				<LoadingIndicator class="w-5 h-5" />
			</div>

			<!-- Bottom action bar — owner cancel only -->
			<div
				v-if="ready && canCancel"
				class="px-4 pt-3 pb-4 standalone:pb-safe-bottom sm:max-w-4xl w-full sm:mx-auto bg-white sticky bottom-0 drop-shadow-xl z-40 border-t border-gray-100"
			>
				<Button
					class="w-full rounded-xl py-5 text-base"
					variant="subtle"
					theme="red"
					@click="openCancelDialog"
				>
					<template #prefix>
						<FeatherIcon name="x" class="h-4 w-4" />
					</template>
					{{ __("Cancel Request") }}
				</Button>
			</div>
		</div>

		<!-- Cancel-with-remarks dialog (mirrors RequestActionSheet pattern) -->
		<Dialog v-model="showCancelDialog">
			<template #body-title>
				<h2 class="text-xl font-bold">{{ __("Cancel Attendance Request") }}</h2>
			</template>
			<template #body-content>
				<div class="flex flex-col gap-3">
					<p class="text-sm text-gray-700">
						{{ __("Once cancelled, this request will be removed from your approver's queue. You can file a new request afterwards if needed.") }}
					</p>
					<FormControl
						type="textarea"
						v-model="cancelReason"
						:placeholder="__('Reason for cancellation')"
						:rows="4"
					/>
					<p v-if="cancelReasonError" class="text-sm text-red-600">
						{{ cancelReasonError }}
					</p>
				</div>
			</template>
			<template #actions>
				<div class="flex flex-row gap-3 w-full">
					<Button
						variant="outline"
						class="py-5 w-full"
						@click="showCancelDialog = false"
					>
						{{ __("Keep Request") }}
					</Button>
					<Button
						variant="solid"
						theme="red"
						class="py-5 w-full"
						:loading="cancelInFlight"
						@click="confirmCancel"
					>
						{{ __("Cancel Request") }}
					</Button>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue"
import { useRouter } from "vue-router"
import {
	Badge,
	Button,
	Dialog,
	FeatherIcon,
	FormControl,
	LoadingIndicator,
	createDocumentResource,
	createResource,
	toast,
} from "frappe-ui"

import dayjs from "@/utils/dayjs"
import { showErrorFromException } from "@/data/errorModal"

const props = defineProps({
	id: { type: String, required: true },
})

const __ = inject("$translate")
const router = useRouter()
const sessionEmployee = inject("$employee", null)
const sessionUser = computed(() => sessionEmployee?.data?.user_id || null)

const document = createDocumentResource({
	doctype: "Attendance Request",
	name: props.id,
	auto: true,
})

const ready = computed(() => Boolean(document.doc))
const doc = computed(() => document.doc || {})

const rejectionReason = computed(() =>
	(doc.value.custom_rejection_reason || "").trim() || null
)

const cancellationReason = computed(() =>
	(doc.value.custom_cancellation_reason || "").trim() || null
)

// AR lifecycle is docstatus-only on stock HRMS; myHR layers in optional
// rejection/cancellation reason fields. The detail view derives its display
// status from those signals so the user reads "Approved/Rejected/Cancelled"
// instead of having to translate docstatus codes themselves.
const status = computed(() => {
	if (!ready.value) return ""
	if (rejectionReason.value) return "Rejected"
	if (doc.value.docstatus === 1) return "Approved"
	if (doc.value.docstatus === 2) return "Cancelled"
	return "Requested"
})

const statusTone = computed(() => {
	switch (status.value) {
		case "Approved":
			return {
				theme: "green",
				icon: "check-circle",
				iconColor: "text-green-600",
				banner: "border-green-200 bg-green-50",
				title: "text-green-900",
				body: "text-green-800",
				heading: __("Approved"),
				subtitle: doc.value.custom_approved_on
					? __("Approved on {0}", [formatDateTime(doc.value.custom_approved_on)])
					: __("Your manager has approved this request."),
			}
		case "Rejected":
			return {
				theme: "red",
				icon: "alert-circle",
				iconColor: "text-red-600",
				banner: "border-red-200 bg-red-50",
				title: "text-red-900",
				body: "text-red-800",
				heading: __("Rejected"),
				subtitle: __("Your manager declined this request. Reason below."),
			}
		case "Cancelled":
			return {
				theme: "gray",
				icon: "slash",
				iconColor: "text-gray-500",
				banner: "border-gray-200 bg-gray-50",
				title: "text-gray-900",
				body: "text-gray-700",
				heading: __("Cancelled"),
				subtitle: cancellationReason.value
					? __("Cancelled — {0}", [cancellationReason.value])
					: __("This request was cancelled."),
			}
		default:
			return {
				theme: "orange",
				icon: "clock",
				iconColor: "text-amber-600",
				banner: "border-amber-200 bg-amber-50",
				title: "text-amber-900",
				body: "text-amber-800",
				heading: __("Awaiting approval"),
				subtitle: __("Your manager will review this request."),
			}
	}
})

const heroDate = computed(() => {
	if (!doc.value.from_date) return ""
	const from = dayjs(doc.value.from_date)
	const to = doc.value.to_date ? dayjs(doc.value.to_date) : null
	if (!to || from.isSame(to, "day")) return from.format("ddd, D MMM YYYY")
	return `${from.format("D MMM")} → ${to.format("D MMM YYYY")}`
})

const totalDays = computed(() => {
	if (!doc.value.from_date || !doc.value.to_date) return null
	const t = dayjs(doc.value.to_date)
	const f = dayjs(doc.value.from_date)
	return t.diff(f, "day") + 1
})

const metaChips = computed(() => {
	const chips = []
	if (doc.value.half_day) {
		chips.push({
			icon: "clock",
			label: doc.value.half_day_date
				? __("Half day on {0}", [dayjs(doc.value.half_day_date).format("D MMM")])
				: __("Half day"),
		})
	}
	if (doc.value.include_holidays) {
		chips.push({ icon: "calendar", label: __("Includes holidays") })
	}
	if (doc.value.shift) {
		chips.push({ icon: "sun", label: doc.value.shift })
	}
	return chips
})

function formatDateTime(value) {
	if (!value) return ""
	const d = dayjs(value)
	if (!d.isValid()) return value
	return d.format("D MMM YYYY, h:mm A")
}

// Owner-only cancel matches the RequestActionSheet gate: must be the filer of
// the AR and the row must still be docstatus=0. Any other state routes through
// HR via Desk per the LA/AR design rules.
const canCancel = computed(() => {
	if (!ready.value) return false
	if (doc.value.docstatus !== 0) return false
	if (rejectionReason.value) return false
	if (!sessionUser.value) return false
	return doc.value.owner === sessionUser.value
})

const showCancelDialog = ref(false)
const cancelReason = ref("")
const cancelReasonError = ref("")
const cancelInFlight = ref(false)

function openCancelDialog() {
	cancelReason.value = ""
	cancelReasonError.value = ""
	showCancelDialog.value = true
}

const cancelResource = createResource({
	url: "myhr.api.cancel_attendance_request",
	onSuccess() {
		cancelInFlight.value = false
		showCancelDialog.value = false
		toast({
			title: __("Success"),
			text: __("Request cancelled."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		// AR cancel deletes the row server-side; bounce back to the list so the
		// user doesn't sit on a now-404 detail screen.
		router.replace({ name: "AttendanceRequestListView" })
	},
	onError(err) {
		cancelInFlight.value = false
		showErrorFromException(err, __("Cancellation failed!"))
	},
})

function confirmCancel() {
	const reason = (cancelReason.value || "").trim()
	if (!reason) {
		cancelReasonError.value = __("Cancellation reason is required.")
		return
	}
	cancelReasonError.value = ""
	cancelInFlight.value = true
	cancelResource.submit({ name: props.id, reason })
}
</script>
