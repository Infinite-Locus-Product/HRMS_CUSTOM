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
						{{ __("Leave Application") }}
					</h2>
					<div
						class="text-[10px] font-bold uppercase tracking-widest text-gray-400 truncate"
					>
						{{ props.id }}
					</div>
				</div>
				<Badge
					v-if="status"
					:label="__(status, null, 'Leave Application')"
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
						<div
							v-else-if="status === 'Cancelled' && cancellationReason"
							class="mt-2 rounded-lg bg-white/70 border border-gray-200 px-3 py-2 text-xs text-gray-800 italic"
						>
							"{{ cancellationReason }}"
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
							class="text-sm font-bold text-violet-600 whitespace-nowrap"
						>
							· {{ totalDays }} {{ totalDays === 1 ? __("day") : __("days") }}
						</div>
					</div>
					<div v-if="metaChips.length" class="mt-3 flex flex-wrap gap-2">
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

				<!-- Leave type + balance -->
				<div
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm"
				>
					<div
						class="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2"
					>
						{{ __("Leave Type") }}
					</div>
					<div class="flex items-center justify-between gap-3 flex-wrap">
						<span
							class="inline-flex items-center gap-1.5 rounded-full bg-violet-50 text-violet-700 px-3 py-1 text-xs font-bold"
						>
							<FeatherIcon name="bookmark" class="h-3 w-3" />
							{{ __(doc.leave_type, null, "Leave Type") || __("Not specified") }}
						</span>
						<div
							v-if="doc.leave_balance != null"
							class="text-xs font-semibold text-gray-500"
						>
							{{ __("Balance") }}:
							<span class="text-gray-900 font-bold">{{ doc.leave_balance }}</span>
						</div>
					</div>
				</div>

				<!-- Description -->
				<div
					v-if="doc.description || true"
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm"
				>
					<div
						class="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2"
					>
						{{ __("Reason") }}
					</div>
					<p
						v-if="doc.description"
						class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed"
					>
						{{ doc.description }}
					</p>
					<p v-else class="text-xs text-gray-400 italic">
						{{ __("No reason was provided.") }}
					</p>
				</div>

				<!-- Approver + filed-on summary -->
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
						v-if="approverDisplay"
						class="flex items-center justify-between gap-3"
					>
						<div class="text-xs font-semibold text-gray-500">
							{{ __("Approver") }}
						</div>
						<div class="text-sm font-bold text-gray-900 truncate">
							{{ approverDisplay }}
						</div>
					</div>
					<div
						v-if="doc.posting_date"
						class="flex items-center justify-between gap-3"
					>
						<div class="text-xs font-semibold text-gray-500">
							{{ __("Filed on") }}
						</div>
						<div class="text-sm font-bold text-gray-900 truncate">
							{{ formatDate(doc.posting_date) }}
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
					<div
						v-if="doc.custom_approved_on"
						class="flex items-center justify-between gap-3"
					>
						<div class="text-xs font-semibold text-gray-500">
							{{ __("Approved on") }}
						</div>
						<div class="text-sm font-bold text-gray-900 truncate">
							{{ formatDateTime(doc.custom_approved_on) }}
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

		<Dialog v-model="showCancelDialog">
			<template #body-title>
				<h2 class="text-xl font-bold">{{ __("Cancel Leave Application") }}</h2>
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
	doctype: "Leave Application",
	name: props.id,
	auto: true,
})

const ready = computed(() => Boolean(document.doc))
const doc = computed(() => document.doc || {})

// LA carries its own Open/Approved/Rejected/Cancelled ladder; "Open" reads as
// "Requested" everywhere else in the PWA so we keep the same convention here.
const status = computed(() => {
	if (!ready.value) return ""
	const s = doc.value.status
	if (s === "Open") return "Requested"
	return s || "Requested"
})

const rejectionReason = computed(() =>
	(doc.value.custom_rejection_reason || "").trim() || null
)
const cancellationReason = computed(() =>
	(doc.value.custom_cancellation_reason || "").trim() || null
)

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
					: __("Your leave has been approved."),
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
				subtitle: __("Your approver declined this leave. Reason below."),
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
					? __("Cancelled — reason below.")
					: __("This leave was cancelled."),
			}
		default: {
			// Owner-side reassurance only — drop the subtitle when the
			// approver opens their report's leave from team-requests.
			const viewerIsOwner =
				!!sessionUser.value && doc.value.owner === sessionUser.value
			return {
				theme: "orange",
				icon: "clock",
				iconColor: "text-amber-600",
				banner: "border-amber-200 bg-amber-50",
				title: "text-amber-900",
				body: "text-amber-800",
				heading: __("Awaiting approval"),
				subtitle: viewerIsOwner
					? __("Your approver will review this leave.")
					: "",
			}
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
	if (typeof doc.value.total_leave_days === "number")
		return doc.value.total_leave_days
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
	return chips
})

const approverDisplay = computed(
	() => doc.value.leave_approver_name || doc.value.leave_approver || ""
)

function formatDate(value) {
	if (!value) return ""
	const d = dayjs(value)
	return d.isValid() ? d.format("D MMM YYYY") : value
}

function formatDateTime(value) {
	if (!value) return ""
	const d = dayjs(value)
	return d.isValid() ? d.format("D MMM YYYY, h:mm A") : value
}

// Owner cancel mirrors the AR rule: must be the filer, must still be Open,
// must be docstatus=0. Anything finalised falls back to HR via Desk.
const canCancel = computed(() => {
	if (!ready.value) return false
	if (doc.value.docstatus !== 0) return false
	if ((doc.value.status || "").trim() !== "Open") return false
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
	url: "myhr.api.cancel_leave_application",
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
		// LA cancel flips status to Cancelled but keeps the row, so just
		// reload — the banner re-renders into its Cancelled state.
		document.reload()
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
