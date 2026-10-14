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
						{{ __("Shift Request") }}
					</h2>
					<div
						class="text-[10px] font-bold uppercase tracking-widest text-gray-400 truncate"
					>
						{{ props.id }}
					</div>
				</div>
				<Badge
					v-if="status"
					:label="__(status, null, 'Shift Request')"
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
							class="text-sm font-bold text-emerald-600 whitespace-nowrap"
						>
							· {{ totalDays }} {{ totalDays === 1 ? __("day") : __("days") }}
						</div>
					</div>
				</div>

				<!-- Shift type -->
				<div
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm"
				>
					<div
						class="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2"
					>
						{{ __("Shift") }}
					</div>
					<span
						class="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 text-emerald-700 px-3 py-1 text-xs font-bold"
					>
						<FeatherIcon name="sun" class="h-3 w-3" />
						{{ doc.shift_type || __("Not specified") }}
					</span>
				</div>

				<!-- Meta -->
				<div
					class="rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm space-y-2.5"
				>
					<MetaRow :label="__('Filed by')" :value="doc.employee_name || doc.employee" />
					<MetaRow :label="__('Department')" :value="doc.department" />
					<MetaRow :label="__('Approver')" :value="doc.approver_name || doc.approver" />
					<MetaRow :label="__('Filed on')" :value="formatDateTime(doc.creation)" />
				</div>
			</div>

			<div
				v-else
				class="flex-1 flex items-center justify-center py-20 text-gray-400"
			>
				<LoadingIndicator class="w-5 h-5" />
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, h, inject } from "vue"
import { useRouter } from "vue-router"
import {
	Badge,
	Button,
	FeatherIcon,
	LoadingIndicator,
	createDocumentResource,
} from "frappe-ui"
import dayjs from "@/utils/dayjs"

const props = defineProps({
	id: { type: String, required: true },
})

const __ = inject("$translate")
const router = useRouter()

const document = createDocumentResource({
	doctype: "Shift Request",
	name: props.id,
	auto: true,
})
const ready = computed(() => Boolean(document.doc))
const doc = computed(() => document.doc || {})

const status = computed(() => {
	if (!ready.value) return ""
	const s = doc.value.status
	if (s) return s
	if (doc.value.docstatus === 1) return "Approved"
	if (doc.value.docstatus === 2) return "Cancelled"
	return "Requested"
})

const statusTone = computed(() => {
	switch (status.value) {
		case "Approved":
			return {
				theme: "green",
				banner: "border-green-200 bg-green-50",
				icon: "check-circle",
				iconColor: "text-green-600",
				title: "text-green-900",
				body: "text-green-800",
				heading: __("Approved"),
				subtitle: __("Shift change is in effect."),
			}
		case "Rejected":
			return {
				theme: "red",
				banner: "border-red-200 bg-red-50",
				icon: "alert-circle",
				iconColor: "text-red-600",
				title: "text-red-900",
				body: "text-red-800",
				heading: __("Rejected"),
				subtitle: __("Your manager declined this shift change."),
			}
		case "Cancelled":
			return {
				theme: "gray",
				banner: "border-gray-200 bg-gray-50",
				icon: "slash",
				iconColor: "text-gray-500",
				title: "text-gray-900",
				body: "text-gray-700",
				heading: __("Cancelled"),
				subtitle: __("This shift change was cancelled."),
			}
		default:
			return {
				theme: "orange",
				banner: "border-amber-200 bg-amber-50",
				icon: "clock",
				iconColor: "text-amber-600",
				title: "text-amber-900",
				body: "text-amber-800",
				heading: __("Awaiting approval"),
				subtitle: __("Your manager will review this shift change."),
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
	return dayjs(doc.value.to_date).diff(dayjs(doc.value.from_date), "day") + 1
})

function formatDateTime(value) {
	if (!value) return ""
	const d = dayjs(value)
	return d.isValid() ? d.format("D MMM YYYY, h:mm A") : value
}

const MetaRow = (p) => {
	if (!p.value) return null
	return h(
		"div",
		{ class: "flex items-center justify-between gap-3" },
		[
			h("div", { class: "text-xs font-semibold text-gray-500" }, p.label),
			h(
				"div",
				{ class: "text-sm font-bold text-gray-900 truncate" },
				String(p.value)
			),
		]
	)
}
MetaRow.props = ["label", "value"]
</script>
