<template>
	<div
		v-if="document?.doc"
		class="bg-white w-full flex flex-col items-stretch pb-2 max-h-[calc(100vh-5rem)]"
	>
		<!-- Header -->
		<div
			class="w-full flex flex-row items-center gap-3 px-5 pt-5 pb-3 border-b border-gray-100 sticky top-0 z-[100] bg-white"
		>
			<div
				class="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
				:class="iconTile.bg"
			>
				<FeatherIcon :name="iconTile.icon" class="h-5 w-5" :class="iconTile.color" />
			</div>
			<div class="flex flex-col flex-1 min-w-0">
				<span class="text-base font-extrabold text-gray-900 truncate">
					{{ __(props.modelValue.doctype) }}
				</span>
				<span
					class="text-[10px] font-bold uppercase tracking-widest text-gray-400 truncate"
				>
					{{ document.doc.name }}
				</span>
			</div>
			<Badge
				v-if="displayStatus"
				:label="__(displayStatus, null, props.modelValue.doctype)"
				:theme="statusTone.theme"
				variant="subtle"
				size="md"
			/>
		</div>

		<!-- Body -->
		<div class="w-full px-5 py-4 overflow-auto flex flex-col gap-3.5">
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
						v-if="statusTone.quote"
						class="mt-2 rounded-lg bg-white/70 border px-3 py-2 text-xs italic"
						:class="statusTone.quoteClass"
					>
						"{{ statusTone.quote }}"
					</div>
				</div>
			</div>

			<!-- Per-doctype hero / summary cards -->
			<template v-if="props.modelValue.doctype === 'Leave Application'">
				<HeroCard :title="__('When')" :metaChips="leaveMeta">
					<template #value>
						<span>{{ heroDate }}</span>
						<span
							v-if="totalLeaveDays"
							class="text-sm font-bold text-violet-600 whitespace-nowrap ml-1"
						>· {{ totalLeaveDays }} {{ totalLeaveDays === 1 ? __("day") : __("days") }}</span>
					</template>
				</HeroCard>
				<DataCard :title="__('Leave Type')">
					<div class="flex items-center justify-between gap-3 flex-wrap">
						<span
							class="inline-flex items-center gap-1.5 rounded-full bg-violet-50 text-violet-700 px-3 py-1 text-xs font-bold"
						>
							<FeatherIcon name="bookmark" class="h-3 w-3" />
							{{ __(document.doc.leave_type, null, "Leave Type") || __("Not specified") }}
						</span>
						<div
							v-if="document.doc.leave_balance != null"
							class="text-xs font-semibold text-gray-500"
						>
							{{ __("Balance") }}:
							<span class="text-gray-900 font-bold">{{ document.doc.leave_balance }}</span>
						</div>
					</div>
				</DataCard>
				<DataCard :title="__('Reason')">
					<p
						v-if="document.doc.description"
						class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed"
					>{{ document.doc.description }}</p>
					<p v-else class="text-xs text-gray-400 italic">
						{{ __("No reason was provided.") }}
					</p>
				</DataCard>
				<MetaCard :rows="leaveMetaRows" />
			</template>

			<template v-else-if="props.modelValue.doctype === 'Attendance Request'">
				<HeroCard :title="__('When')" :metaChips="arMeta">
					<template #value>
						<span>{{ heroDate }}</span>
						<span
							v-if="totalARDays"
							class="text-sm font-bold text-blue-600 whitespace-nowrap ml-1"
						>· {{ totalARDays }} {{ totalARDays === 1 ? __("day") : __("days") }}</span>
					</template>
				</HeroCard>
				<DataCard :title="__('Reason')">
					<div class="flex items-center gap-2 flex-wrap mb-2">
						<span
							class="inline-flex items-center gap-1.5 rounded-full bg-blue-50 text-blue-700 px-3 py-1 text-xs font-bold"
						>
							<FeatherIcon name="bookmark" class="h-3 w-3" />
							{{ document.doc.reason || __("Not specified") }}
						</span>
					</div>
					<p
						v-if="document.doc.explanation"
						class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed"
					>{{ document.doc.explanation }}</p>
					<p v-else class="text-xs text-gray-400 italic">
						{{ __("No additional explanation was provided.") }}
					</p>
				</DataCard>
				<MetaCard :rows="arMetaRows" />
			</template>

			<template v-else-if="props.modelValue.doctype === 'Expense Claim'">
				<HeroCard :title="__('Grand Total')">
					<template #value>
						<span>{{ formatMoney(document.doc.grand_total, document.doc.currency) }}</span>
					</template>
				</HeroCard>
				<DataCard :title="__('Expense Items')" :count="document.doc.expenses?.length">
					<div
						v-if="document.doc.expenses?.length"
						class="flex flex-col divide-y divide-gray-100"
					>
						<div
							v-for="(item, idx) in document.doc.expenses"
							:key="idx"
							class="py-2.5 first:pt-0 last:pb-0 flex items-start justify-between gap-3"
						>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-bold text-gray-900 truncate">
									{{ item.expense_type || __("Expense") }}
								</div>
								<div
									v-if="item.description || item.expense_date"
									class="text-[11px] text-gray-500 mt-0.5 truncate"
								>
									<span v-if="item.expense_date">{{ formatDate(item.expense_date) }}</span>
									<span v-if="item.expense_date && item.description"> · </span>
									<span v-if="item.description">{{ item.description }}</span>
								</div>
							</div>
							<div
								class="text-sm font-extrabold text-gray-900 whitespace-nowrap"
							>
								{{ formatMoney(item.amount, document.doc.currency) }}
							</div>
						</div>
					</div>
					<p v-else class="text-xs text-gray-400 italic">
						{{ __("No expense items.") }}
					</p>
				</DataCard>
				<DataCard :title="__('Totals')">
					<div class="flex flex-col gap-1.5">
						<TotalsRow
							:label="__('Total claimed')"
							:value="formatMoney(document.doc.total_claimed_amount, document.doc.currency)"
						/>
						<TotalsRow
							:label="__('Total sanctioned')"
							:value="formatMoney(document.doc.total_sanctioned_amount, document.doc.currency)"
						/>
						<TotalsRow
							v-if="document.doc.total_taxes_and_charges"
							:label="__('Taxes & charges')"
							:value="formatMoney(document.doc.total_taxes_and_charges, document.doc.currency)"
						/>
						<TotalsRow
							v-if="document.doc.total_advance_amount"
							:label="__('Advance applied')"
							:value="`- ${formatMoney(document.doc.total_advance_amount, document.doc.currency)}`"
						/>
						<div class="border-t border-gray-100 mt-1.5 pt-1.5">
							<TotalsRow
								:label="__('Grand total')"
								:value="formatMoney(document.doc.grand_total, document.doc.currency)"
								strong
							/>
						</div>
					</div>
				</DataCard>
				<MetaCard :rows="expenseMetaRows" />
			</template>

			<template
				v-else-if="['Shift Request', 'Shift Assignment'].includes(props.modelValue.doctype)"
			>
				<HeroCard :title="__('When')">
					<template #value>
						<span>{{ shiftHeroDate }}</span>
						<span
							v-if="totalShiftDays"
							class="text-sm font-bold text-emerald-600 whitespace-nowrap ml-1"
						>· {{ totalShiftDays }} {{ totalShiftDays === 1 ? __("day") : __("days") }}</span>
					</template>
				</HeroCard>
				<DataCard :title="__('Shift')">
					<div class="flex items-center justify-between gap-3 flex-wrap">
						<span
							class="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 text-emerald-700 px-3 py-1 text-xs font-bold"
						>
							<FeatherIcon name="sun" class="h-3 w-3" />
							{{ document.doc.shift_type || __("Shift") }}
						</span>
						<div
							v-if="document.doc.shift_timing"
							class="text-xs font-semibold text-gray-500"
						>
							{{ document.doc.shift_timing }}
						</div>
					</div>
				</DataCard>
				<MetaCard :rows="shiftMetaRows" />
			</template>

			<!-- Fallback: legacy field-iteration for unknown doctypes -->
			<template v-else>
				<div
					v-for="field in fieldsWithValues"
					:key="field.fieldname"
					:class="[
						['Small Text', 'Text', 'Long Text', 'Table', 'geolocation'].includes(field.fieldtype)
							? 'flex-col'
							: 'flex-row items-center justify-between',
						'flex w-full',
					]"
				>
					<div class="text-gray-600 text-sm">
						{{ __(field.label, null, props.modelValue?.doctype) }}
					</div>
					<component
						v-if="field.fieldtype === 'Table'"
						:is="field.component"
						:doc="document?.doc"
					/>
					<FormattedField
						v-else
						:value="field.value"
						:fieldtype="field.fieldtype"
						:fieldname="field.fieldname"
					/>
				</div>
			</template>

			<!-- Attachments -->
			<DataCard :title="__('Attachments')" :count="attachedFiles?.data?.length">
				<div
					v-if="attachedFiles?.data?.length"
					class="flex flex-col gap-2"
				>
					<button
						v-for="(file, index) in attachedFiles.data"
						:key="index"
						type="button"
						@click="showFilePreview(file)"
						class="rounded-xl border border-gray-100 bg-white hover:bg-blue-50/60 active:bg-blue-100/60 p-3 flex items-center gap-3 transition-colors text-left"
					>
						<div class="p-2 rounded-lg bg-gray-50 text-gray-600 shrink-0">
							<FeatherIcon :name="fileIcon(file)" class="h-4 w-4" />
						</div>
						<div class="flex-1 min-w-0">
							<div class="text-sm font-bold text-gray-900 truncate">
								{{ file.file_name || file.name }}
							</div>
							<div class="text-[11px] font-bold text-gray-500 mt-0.5">
								{{ __("Tap to preview") }}
							</div>
						</div>
						<FeatherIcon name="eye" class="h-4 w-4 text-gray-400 shrink-0" />
					</button>
				</div>
				<div
					v-else
					class="rounded-xl border border-dashed border-gray-200 bg-gray-50/50 px-3 py-3 text-[11px] font-bold uppercase tracking-widest text-gray-400 text-center"
				>
					{{ __("No attachments") }}
				</div>
			</DataCard>
		</div>

		<!-- Actions -->
		<WorkflowActionSheet
			v-if="workflow?.hasWorkflow"
			:doc="document.doc"
			:workflow="workflow"
			view="actionSheet"
		/>

		<div
			v-else-if="
				['Open', 'Draft'].includes(document?.doc?.[approvalField])
				&& hasPermission('approval')
				&& expenseClaimCanApprove
				&& !(props.modelValue.doctype === 'Expense Claim' && canEmployeeCancel)
			"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t border-gray-100 z-[100] p-4 bg-white"
		>
			<Button
				@click="openRejectDialog"
				class="w-full py-5"
				variant="subtle"
				theme="red"
			>
				<template #prefix>
					<FeatherIcon name="x" class="w-4" />
				</template>
				{{ __("Reject") }}
			</Button>

			<Button
				@click="updateDocumentStatus({ status: 'Approved' })"
				class="w-full py-5"
				variant="solid"
				theme="green"
			>
				<template #prefix>
					<FeatherIcon name="check" class="w-4" />
				</template>
				{{ __("Approve") }}
			</Button>
		</div>

		<!-- Expense Claim — buttons hidden because the server gate would
		     block this user (e.g. self-approval blocked by HR Settings).
		     Inline notice instead, so the user understands why they don't
		     see Approve/Reject. Suppressed for the owner of a Draft claim
		     so the Cancel branch can take precedence. -->
		<div
			v-else-if="
				props.modelValue.doctype === 'Expense Claim'
				&& ['Open', 'Draft'].includes(document?.doc?.[approvalField])
				&& hasPermission('approval')
				&& !expenseClaimCanApprove
				&& expenseClaimBlockedReason
				&& !canEmployeeCancel
			"
			class="sticky bottom-0 border-t border-gray-100 z-[100] p-4 bg-white"
		>
			<div class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-3">
				<FeatherIcon name="info" class="h-5 w-5 mt-0.5 text-amber-600 shrink-0" />
				<div class="text-xs font-semibold text-amber-900 leading-relaxed">
					{{ expenseClaimBlockedReason }}
				</div>
			</div>
		</div>

		<!-- Attendance Request approver branch: AR has no `status` field so the
		     generic Open/Draft + approval-status branch above never fires. The
		     PWA convention is "submit = approve" for AR (docstatus 0 → 1
		     creates the Attendance row). Reject routes through the dedicated
		     myhr.api.reject_attendance_request endpoint with a remarks dialog,
		     which deletes the row + notifies the filer. -->
		<div
			v-else-if="
				document?.doc?.doctype === 'Attendance Request' &&
				document?.doc?.docstatus === 0 &&
				hasPermission('submit')
			"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t border-gray-100 z-[100] p-4 bg-white"
		>
			<Button
				@click="openRejectDialog"
				class="w-full py-5"
				variant="subtle"
				theme="red"
			>
				<template #prefix>
					<FeatherIcon name="x" class="w-4" />
				</template>
				{{ __("Reject") }}
			</Button>

			<Button
				@click="updateDocumentStatus({ docstatus: 1 })"
				class="w-full py-5"
				variant="solid"
				theme="green"
			>
				<template #prefix>
					<FeatherIcon name="check" class="w-4" />
				</template>
				{{ __("Approve") }}
			</Button>
		</div>

		<div
			v-else-if="
				document?.doc?.docstatus === 0 &&
				['Approved', 'Rejected'].includes(document?.doc?.[approvalField]) &&
				hasPermission('submit')
			"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t border-gray-100 z-[100] p-4 bg-white"
		>
			<Button
				@click="updateDocumentStatus({ docstatus: 1 })"
				class="w-full py-5"
				variant="solid"
			>
				{{ __("Submit") }}
			</Button>
		</div>

		<!-- Submitted-doc cancel: blocked entirely on LA / AR / Expense Claim
		     so a finalised verdict stays put. HR cancels from Desk if a
		     correction is needed. Keeping the branch for other future
		     submittables that may want a PWA-side cancel. -->
		<div
			v-else-if="
				document?.doc?.docstatus === 1 &&
				hasPermission('cancel') &&
				!NO_PWA_CANCEL_DOCTYPES.includes(props.modelValue.doctype)
			"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t border-gray-100 z-[100] p-4 bg-white"
		>
			<Button
				@click="updateDocumentStatus({ docstatus: 2 })"
				class="w-full py-5"
				variant="subtle"
				theme="red"
			>
				<template #prefix>
					<FeatherIcon name="x" class="w-4" />
				</template>
				{{ __("Cancel") }}
			</Button>
		</div>

		<!-- Employee-side cancel for own pending request. Visible only to
		     the *filer* (owner). State gates per doctype:
		       LA: docstatus=0 AND status=Open
		       AR: docstatus=0
		       EC: docstatus=0 AND approval_status=Draft
		     Backed by myhr.api.cancel_{leave_application,attendance_request,
		     expense_claim} — see cancelMethods below. -->
		<div
			v-else-if="canEmployeeCancel"
			class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t border-gray-100 z-[100] p-4 bg-white"
		>
			<Button
				@click="openCancelDialog"
				class="w-full py-5"
				variant="subtle"
				theme="red"
			>
				<template #prefix>
					<FeatherIcon name="x" class="w-4" />
				</template>
				{{ __("Cancel Request") }}
			</Button>
		</div>

		<!-- Reject reason capture (kept outside the v-if/v-else-if chain so it
		     doesn't break the Vue compiler's sibling check). -->
		<Dialog v-model="showRejectDialog">
			<template #body-title>
				<h2 class="text-xl font-bold">{{ __("Reject {0}", [__(props.modelValue.doctype)]) }}</h2>
			</template>
			<template #body-content>
				<div class="flex flex-col gap-3">
					<p class="text-sm text-gray-700">
						{{ __("Tell the employee why this request is being rejected. They will see this message on their request.") }}
					</p>
					<FormControl
						type="textarea"
						v-model="rejectReason"
						:placeholder="__('Reason for rejection')"
						:rows="4"
					/>
					<p v-if="rejectReasonError" class="text-sm text-red-600">{{ rejectReasonError }}</p>
				</div>
			</template>
			<template #actions>
				<div class="flex flex-row gap-3 w-full">
					<Button
						variant="outline"
						class="py-5 w-full"
						@click="showRejectDialog = false"
					>
						{{ __("Cancel") }}
					</Button>
					<Button
						variant="solid"
						theme="red"
						class="py-5 w-full"
						:loading="rejectInFlight"
						@click="confirmReject"
					>
						{{ __("Reject") }}
					</Button>
				</div>
			</template>
		</Dialog>

		<!-- Cancel reason capture. EC cancel is reason-less by design (see
		     api._cancel_pending_request): nowhere durable to store the reason
		     since the row is deleted, and no approver action has been taken.
		     LA + AR still require a reason for the approver audit trail. -->
		<Dialog v-model="showCancelDialog">
			<template #body-title>
				<h2 class="text-xl font-bold">{{ __("Cancel {0}", [__(props.modelValue.doctype)]) }}</h2>
			</template>
			<template #body-content>
				<div class="flex flex-col gap-3">
					<p class="text-sm text-gray-700">
						{{ __("Once cancelled, this request will be removed from your approver's queue. You can file a new request afterwards if needed.") }}
					</p>
					<FormControl
						v-if="cancelRequiresReason"
						type="textarea"
						v-model="cancelReason"
						:placeholder="__('Reason for cancellation')"
						:rows="4"
					/>
					<p v-if="cancelRequiresReason && cancelReasonError" class="text-sm text-red-600">{{ cancelReasonError }}</p>
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

		<!-- File Preview Modal -->
		<ion-modal
			ref="modal"
			:is-open="showPreviewModal"
			@didDismiss="showPreviewModal = false"
		>
			<FilePreviewModal :file="selectedFile" />
		</ion-modal>

	</div>
</template>

<script setup>
import { computed, h, inject, ref, defineAsyncComponent, onMounted } from "vue"
import { IonModal, modalController } from "@ionic/vue"
import { useRouter } from "vue-router"
import {
	toast,
	createDocumentResource,
	createResource,
	Dialog,
	FormControl,
	Button,
	FeatherIcon,
	Badge,
} from "frappe-ui"

import { showErrorFromException } from "@/data/errorModal"

import FormattedField from "@/components/FormattedField.vue"
import FilePreviewModal from "@/components/FilePreviewModal.vue"
import WorkflowActionSheet from "@/components/WorkflowActionSheet.vue"

import { getCompanyCurrency } from "@/data/currencies"
import { formatCurrency } from "@/utils/formatters"
import dayjs from "@/utils/dayjs"

import useWorkflow from "@/composables/workflow"

const __ = inject("$translate")

const props = defineProps({
	fields: {
		type: Array,
		required: true,
	},
	showOpenForm: {
		type: Boolean,
		default: true,
	},
	modelValue: {
		type: Object,
		required: true,
	},
})
const router = useRouter()

let showPreviewModal = ref(false)
let selectedFile = ref({})
let workflow = ref(null)

// Reject-with-remarks dialog state. The Reject button on Leave Application /
// Attendance Request opens this textarea so HR has to write a reason; the
// reason is stamped into custom_rejection_reason and the LA auto-submits to
// Rejected on the same save cycle (see myhr/overrides/leave_application.py).
let showRejectDialog = ref(false)
let rejectReason = ref("")
let rejectReasonError = ref("")
let rejectInFlight = ref(false)

// Employee-side cancel-with-remarks dialog state. Mirrors the reject flow but
// goes through dedicated whitelisted endpoints (myhr.api.cancel_leave_application
// / cancel_attendance_request) which enforce the owner + status=Open gate.
let showCancelDialog = ref(false)
let cancelReason = ref("")
let cancelReasonError = ref("")
let cancelInFlight = ref(false)

const sessionEmployee = inject("$employee", null)
const sessionUser = computed(() => sessionEmployee?.data?.user_id || null)

// Cancel button is visible only when:
//   - the doctype is LA, AR, or Expense Claim
//   - the request is still pending review:
//       LA: docstatus=0 AND status=Open (LA carries its own
//           Open/Approved/Rejected/Cancelled ladder)
//       AR: docstatus=0 (no status field — submit = approve)
//       EC: docstatus=0 AND approval_status=Draft (once approver acts the
//           status flips to Approved or Rejected and the row is no longer
//           recallable from the PWA)
//   - the viewer is the original filer (owner), not the approver opening the
//     same row from Team Requests
const CANCELLABLE_DOCTYPES = ["Leave Application", "Attendance Request", "Expense Claim"]
// Doctypes where a submitted (docstatus=1) row must NOT be cancellable from
// the PWA. Once HR / the approver has issued a verdict, corrections happen
// through Desk so the audit trail and accounting entries stay consistent.
const NO_PWA_CANCEL_DOCTYPES = [
	"Leave Application",
	"Attendance Request",
	"Expense Claim",
]
const canEmployeeCancel = computed(() => {
	if (!CANCELLABLE_DOCTYPES.includes(props.modelValue.doctype)) return false
	const doc = document?.doc
	if (!doc) return false
	if (doc.docstatus !== 0) return false
	if (props.modelValue.doctype === "Leave Application" && doc.status !== "Open") return false
	if (props.modelValue.doctype === "Expense Claim" && doc.approval_status !== "Draft") return false
	if (!sessionUser.value) return false
	return doc.owner === sessionUser.value
})

function showFilePreview(fileObj) {
	selectedFile.value = fileObj
	showPreviewModal.value = true
}

function fileIcon(file) {
	const name = (file?.file_name || file?.name || "").toLowerCase()
	if (/\.(png|jpg|jpeg|gif|webp|svg|bmp|tiff|heic)$/i.test(name)) return "image"
	if (/\.pdf$/i.test(name)) return "file-text"
	if (/\.(doc|docx)$/i.test(name)) return "file-text"
	if (/\.(xls|xlsx|csv)$/i.test(name)) return "grid"
	if (/\.(zip|tar|gz|rar)$/i.test(name)) return "archive"
	if (/\.(mp4|mov|webm|avi)$/i.test(name)) return "video"
	if (/\.(mp3|wav|m4a|ogg)$/i.test(name)) return "music"
	return "file"
}

const document = createDocumentResource({
	doctype: props.modelValue.doctype,
	name: props.modelValue.name,
	auto: true,
	onSuccess(doc) {
		attachedFiles.reload()
	},
})

const attachedFiles = createResource({
	url: "hrms.api.get_attachments",
	params: {
		dt: props.modelValue.doctype,
		dn: props.modelValue.name,
	},
	auto: true,
})

const docPermissions = createResource({
	url: "frappe.client.get_doc_permissions",
	params: { doctype: props.modelValue.doctype, docname: props.modelValue.name },
	auto: true,
})

const permittedWriteFields = createResource({
	url: "hrms.api.get_permitted_fields_for_write",
	params: { doctype: props.modelValue.doctype },
	auto: true,
})

// Expense Claim row-level approval capability. Mirrors the server gate
// (`gate_expense_claim_approval`) so the Approve/Reject buttons hide when
// the session user can't actually approve this specific claim — most
// notably when `prevent_self_expense_approval` is on and the viewer is
// the Employee themselves. Returns `{can_approve, reason}`.
const expenseClaimCapability = createResource({
	url: "myhr.api.can_approve_expense_claim",
	params: { name: props.modelValue.name },
	auto: props.modelValue.doctype === "Expense Claim",
})

const expenseClaimCanApprove = computed(() => {
	if (props.modelValue.doctype !== "Expense Claim") return true
	if (!expenseClaimCapability.data) return true // optimistic until response
	return !!expenseClaimCapability.data.can_approve
})

const expenseClaimBlockedReason = computed(() => {
	if (props.modelValue.doctype !== "Expense Claim") return ""
	return expenseClaimCapability.data?.reason || ""
})

function hasPermission(action) {
	if (action === "approval")
		return permittedWriteFields.data?.includes(approvalField.value)
	return docPermissions.data?.permissions[action]
}

const approvalField = computed(() => {
	return props.modelValue.doctype === "Expense Claim"
		? "approval_status"
		: "status"
})

const currency = computed(() => {
	let docCurrency = document?.doc?.currency

	if (!docCurrency && document?.doc?.company) {
		docCurrency = getCompanyCurrency(document?.doc?.company)
	}
	return docCurrency
})

const fieldsWithValues = computed(() => {
	if (!document.doc) return []

	return props.fields.map((field) => {
		const raw =
			document.doc[field.fieldname] ?? props.modelValue[field.fieldname]

		if (field.fieldtype === "Currency") {
			return {
				...field,
				value: formatCurrency(raw, currency.value),
			}
		}
		if (field.fieldtype === "Table") {
			return {
				...field,
				value: raw,
				component: defineAsyncComponent(() =>
					import(`../components/${field.componentName}.vue`)
				),
			}
		}
		return { ...field, value: raw }
	})
})

const getSuccessMessage = ({ status = "", docstatus = 0 }) => {
	if (status) {
		return __("{0} successfully!", [__(status)])
	} else if (docstatus) {
		return __("Document {0} successfully!", [
			docstatus === 1 ? __("submitted") : __("cancelled"),
		])
	}
}

const getFailureMessage = ({ status = "", docstatus = 0 }) => {
	if (status) {
		return __("{0} failed!", [status === __("Approved") ? __("Approval") : __("Rejection")])
	} else if (docstatus) {
		return __('Document {0} failed!', [docstatus === 1 ? __("submission") : __("cancellation")])
	}
}

const updateDocumentStatus = ({ status = "", docstatus = 0, extraValues = {} }) => {
	let updateValues = { ...extraValues }

	if (status) updateValues[approvalField.value] = status
	if (docstatus) updateValues.docstatus = docstatus

	document.setValue.submit(
		{ ...updateValues },
		{
			onSuccess() {
				if (docstatus !== 0) modalController.dismiss()

				toast({
					title: __("Success"),
					text: getSuccessMessage({ status, docstatus }),
					icon: "check-circle",
					position: "bottom-center",
					iconClasses: "text-green-500",
				})
			},
			onError(err) {
				showErrorFromException(err, getFailureMessage({ status, docstatus }))
			},
		}
	)
}

function openRejectDialog() {
	rejectReason.value = ""
	rejectReasonError.value = ""
	showRejectDialog.value = true
}

// Attendance Request uses a dedicated endpoint instead of the generic
// setValue path: AR has no `status` field, and even if it did, stock HRMS
// would block submit-then-cancel. The endpoint stamps the reason, deletes
// the row (semantic equivalent of "rejected" for AR — the row never reaches
// docstatus=1, so no Attendance row gets created), and notifies the filer.
const arRejectResource = createResource({
	url: "myhr.api.reject_attendance_request",
	onSuccess() {
		rejectInFlight.value = false
		showRejectDialog.value = false
		modalController.dismiss()
		toast({
			title: __("Success"),
			text: __("Rejected successfully!"),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
	},
	onError(err) {
		rejectInFlight.value = false
		showErrorFromException(err, __("Rejection failed!"))
	},
})

function confirmReject() {
	const reason = (rejectReason.value || "").trim()
	if (!reason) {
		rejectReasonError.value = __("Rejection reason is required.")
		return
	}
	rejectReasonError.value = ""
	rejectInFlight.value = true

	if (props.modelValue.doctype === "Attendance Request") {
		arRejectResource.submit({ name: props.modelValue.name, reason })
		return
	}

	// Leave Application uses `custom_rejection_reason` (added in setup.py).
	const extra = { custom_rejection_reason: reason }
	document.setValue.submit(
		{ [approvalField.value]: "Rejected", ...extra },
		{
			onSuccess() {
				rejectInFlight.value = false
				showRejectDialog.value = false
				modalController.dismiss()
				toast({
					title: __("Success"),
					text: __("Rejected successfully!"),
					icon: "check-circle",
					position: "bottom-center",
					iconClasses: "text-green-500",
				})
			},
			onError(err) {
				rejectInFlight.value = false
				showErrorFromException(err, __("Rejection failed!"))
			},
		}
	)
}

const cancelMethods = {
	"Leave Application": "myhr.api.cancel_leave_application",
	"Attendance Request": "myhr.api.cancel_attendance_request",
	"Expense Claim": "myhr.api.cancel_expense_claim",
}
const cancelResource = createResource({
	url: cancelMethods[props.modelValue.doctype] || "myhr.api.cancel_leave_application",
	onSuccess() {
		cancelInFlight.value = false
		showCancelDialog.value = false
		modalController.dismiss()
		toast({
			title: __("Success"),
			text: __("Request cancelled."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
	},
	onError(err) {
		cancelInFlight.value = false
		showErrorFromException(err, __("Cancellation failed!"))
	},
})

// EC cancel is a "rescind my own draft" — no reason field surfaces in the
// dialog (server defaults to a generic message). LA + AR still capture a
// reason because their approver audit trail relies on it.
const cancelRequiresReason = computed(
	() => props.modelValue.doctype !== "Expense Claim"
)

function openCancelDialog() {
	cancelReason.value = ""
	cancelReasonError.value = ""
	showCancelDialog.value = true
}

function confirmCancel() {
	const reason = (cancelReason.value || "").trim()
	if (cancelRequiresReason.value && !reason) {
		cancelReasonError.value = __("Cancellation reason is required.")
		return
	}
	cancelReasonError.value = ""
	cancelInFlight.value = true
	cancelResource.submit({
		name: props.modelValue.name,
		reason,
	})
}

const openFormView = () => {
	modalController.dismiss()
	router.push({
		name: `${props.modelValue.doctype.replace(/\s+/g, "")}DetailView`,
		params: { id: props.modelValue.name },
	})
}

onMounted(() => {
	workflow.value = useWorkflow(props.modelValue.doctype)
})

// ---------------------------------------------------------------------------
// Doctype-specific presentation helpers (status banner, hero, meta rows)
// ---------------------------------------------------------------------------

const ICON_TILES = {
	"Leave Application": { icon: "umbrella", bg: "bg-violet-50", color: "text-violet-600" },
	"Attendance Request": { icon: "user-check", bg: "bg-blue-50", color: "text-blue-600" },
	"Expense Claim": { icon: "credit-card", bg: "bg-amber-50", color: "text-amber-600" },
	"Shift Request": { icon: "sun", bg: "bg-emerald-50", color: "text-emerald-600" },
	"Shift Assignment": { icon: "sun", bg: "bg-emerald-50", color: "text-emerald-600" },
}

const iconTile = computed(() => ICON_TILES[props.modelValue.doctype] || {
	icon: "file-text",
	bg: "bg-gray-50",
	color: "text-gray-600",
})

const rejectionReason = computed(
	() => (document.doc?.custom_rejection_reason || "").trim() || null
)
const cancellationReason = computed(
	() => (document.doc?.custom_cancellation_reason || "").trim() || null
)

// Status displayed to the user. Each doctype carries its own ladder; we map
// them all into a small, consistent vocabulary so the banner styling can be
// driven from a single source instead of branching on doctype downstream.
const displayStatus = computed(() => {
	if (!document.doc) return ""
	const dt = props.modelValue.doctype
	const ds = document.doc.docstatus

	if (dt === "Leave Application") {
		const s = document.doc.status
		if (s === "Open") return "Requested"
		return s || "Requested"
	}
	if (dt === "Attendance Request") {
		if (rejectionReason.value) return "Rejected"
		if (ds === 1) return "Approved"
		if (ds === 2) return "Cancelled"
		return "Requested"
	}
	if (dt === "Expense Claim") {
		const a = document.doc.approval_status
		if (a === "Approved") return ds === 1 ? "Approved" : "Approved (Draft)"
		if (a === "Rejected") return "Rejected"
		if (ds === 2) return "Cancelled"
		return "Requested"
	}
	if (["Shift Request", "Shift Assignment"].includes(dt)) {
		const s = document.doc.status
		if (s) return s
		if (ds === 1) return "Approved"
		if (ds === 2) return "Cancelled"
		return "Requested"
	}
	return ""
})

const statusTone = computed(() => {
	const s = displayStatus.value
	if (s === "Approved" || s === "Approved (Draft)") {
		return {
			theme: "green",
			banner: "border-green-200 bg-green-50",
			icon: "check-circle",
			iconColor: "text-green-600",
			title: "text-green-900",
			body: "text-green-800",
			heading: __("Approved"),
			subtitle: document.doc?.custom_approved_on
				? __("Approved on {0}", [formatDateTime(document.doc.custom_approved_on)])
				: __("This request has been approved."),
			quote: null,
			quoteClass: "",
		}
	}
	if (s === "Rejected") {
		return {
			theme: "red",
			banner: "border-red-200 bg-red-50",
			icon: "alert-circle",
			iconColor: "text-red-600",
			title: "text-red-900",
			body: "text-red-800",
			heading: __("Rejected"),
			subtitle: rejectionReason.value
				? __("This request was declined. Reason below.")
				: __("This request was declined."),
			quote: rejectionReason.value,
			quoteClass: "border-red-200 text-red-900",
		}
	}
	if (s === "Cancelled") {
		return {
			theme: "gray",
			banner: "border-gray-200 bg-gray-50",
			icon: "slash",
			iconColor: "text-gray-500",
			title: "text-gray-900",
			body: "text-gray-700",
			heading: __("Cancelled"),
			subtitle: cancellationReason.value
				? __("Cancelled — reason below.")
				: __("This request was cancelled."),
			quote: cancellationReason.value,
			quoteClass: "border-gray-200 text-gray-800",
		}
	}
	// Owner-side reassurance ("your approver will review this") only makes
	// sense to the filer. When the approver opens the same row from their
	// team-requests queue they ARE the approver, so we drop the subtitle.
	const viewerIsOwner =
		!!sessionUser.value && document.doc?.owner === sessionUser.value
	return {
		theme: "orange",
		banner: "border-amber-200 bg-amber-50",
		icon: "clock",
		iconColor: "text-amber-600",
		title: "text-amber-900",
		body: "text-amber-800",
		heading: __("Awaiting approval"),
		subtitle: viewerIsOwner
			? __("Your approver will review this shortly.")
			: "",
		quote: null,
		quoteClass: "",
	}
})

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

function formatMoney(value, code) {
	if (value == null || value === "") return formatCurrency(0, code || currency.value)
	return formatCurrency(value, code || currency.value)
}

const heroDate = computed(() => {
	const doc = document.doc
	if (!doc?.from_date) return ""
	const from = dayjs(doc.from_date)
	const to = doc.to_date ? dayjs(doc.to_date) : null
	if (!to || from.isSame(to, "day")) return from.format("ddd, D MMM YYYY")
	return `${from.format("D MMM")} → ${to.format("D MMM YYYY")}`
})

const totalLeaveDays = computed(() => {
	const doc = document.doc
	if (!doc) return null
	if (typeof doc.total_leave_days === "number") return doc.total_leave_days
	if (!doc.from_date || !doc.to_date) return null
	return dayjs(doc.to_date).diff(dayjs(doc.from_date), "day") + 1
})

const totalARDays = computed(() => {
	const doc = document.doc
	if (!doc?.from_date || !doc?.to_date) return null
	return dayjs(doc.to_date).diff(dayjs(doc.from_date), "day") + 1
})

const leaveMeta = computed(() => {
	const doc = document.doc
	const chips = []
	if (doc?.half_day) {
		chips.push({
			icon: "clock",
			label: doc.half_day_date
				? __("Half day on {0}", [dayjs(doc.half_day_date).format("D MMM")])
				: __("Half day"),
		})
	}
	return chips
})

const arMeta = computed(() => {
	const doc = document.doc
	const chips = []
	if (doc?.half_day) {
		chips.push({
			icon: "clock",
			label: doc.half_day_date
				? __("Half day on {0}", [dayjs(doc.half_day_date).format("D MMM")])
				: __("Half day"),
		})
	}
	if (doc?.include_holidays) chips.push({ icon: "calendar", label: __("Includes holidays") })
	if (doc?.shift) chips.push({ icon: "sun", label: doc.shift })
	return chips
})

function row(label, value) {
	if (value == null || value === "") return null
	return { label, value }
}

const leaveMetaRows = computed(() => {
	const doc = document.doc || {}
	return [
		row(__("Filed by"), doc.employee_name || doc.employee),
		row(__("Department"), doc.department),
		row(__("Approver"), doc.leave_approver_name || doc.leave_approver),
		row(__("Filed on"), formatDate(doc.posting_date)),
		row(__("Approved by"), doc.custom_approved_by),
		row(__("Approved on"), doc.custom_approved_on ? formatDateTime(doc.custom_approved_on) : null),
	].filter(Boolean)
})

const arMetaRows = computed(() => {
	const doc = document.doc || {}
	return [
		row(__("Filed by"), doc.employee_name || doc.employee),
		row(__("Department"), doc.department),
		row(__("Filed on"), formatDateTime(doc.creation)),
		row(__("Approved by"), doc.custom_approved_by),
	].filter(Boolean)
})

const expenseMetaRows = computed(() => {
	const doc = document.doc || {}
	return [
		row(__("Filed by"), doc.employee_name || doc.employee),
		row(__("Posting date"), formatDate(doc.posting_date)),
		row(__("Approver"), doc.expense_approver_name || doc.expense_approver),
		row(__("Cost center"), doc.cost_center),
		row(__("Project"), doc.project),
	].filter(Boolean)
})

const totalShiftDays = computed(() => {
	const doc = document.doc
	if (!doc) return null
	if (typeof doc.total_shift_days === "number") return doc.total_shift_days
	const f = doc.from_date || doc.start_date
	const t = doc.to_date || doc.end_date
	if (!f || !t) return null
	return dayjs(t).diff(dayjs(f), "day") + 1
})

const shiftHeroDate = computed(() => {
	const doc = document.doc
	if (!doc) return ""
	const f = doc.from_date || doc.start_date
	const t = doc.to_date || doc.end_date
	if (!f) return ""
	const from = dayjs(f)
	const to = t ? dayjs(t) : null
	if (!to || from.isSame(to, "day")) return from.format("ddd, D MMM YYYY")
	return `${from.format("D MMM")} → ${to.format("D MMM YYYY")}`
})

const shiftMetaRows = computed(() => {
	const doc = document.doc || {}
	return [
		row(__("Filed by"), doc.employee_name || doc.employee),
		row(__("Department"), doc.department),
		row(__("Approver"), doc.approver_name || doc.approver),
		row(__("Filed on"), formatDateTime(doc.creation)),
	].filter(Boolean)
})

// ---------------------------------------------------------------------------
// Tiny render-time helpers used inline above. Kept as render functions so the
// template stays readable and we don't need a separate file per primitive.
// ---------------------------------------------------------------------------

const HeroCard = (props2, { slots }) =>
	h(
		"div",
		{ class: "rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm" },
		[
			h(
				"div",
				{
					class:
						"text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2",
				},
				props2.title
			),
			h(
				"div",
				{ class: "flex items-baseline gap-1 flex-wrap" },
				h(
					"div",
					{ class: "text-2xl font-extrabold text-gray-900 leading-none" },
					slots.value?.()
				)
			),
			props2.metaChips && props2.metaChips.length
				? h(
						"div",
						{ class: "mt-3 flex flex-wrap gap-2" },
						props2.metaChips.map((chip) =>
							h(
								"span",
								{
									class:
										"inline-flex items-center gap-1 rounded-full bg-gray-50 border border-gray-100 px-2.5 py-1 text-[11px] font-bold text-gray-700",
								},
								[
									h(FeatherIcon, { name: chip.icon, class: "h-3 w-3" }),
									chip.label,
								]
							)
						)
				  )
				: null,
		]
	)
HeroCard.props = ["title", "metaChips"]

const DataCard = (props2, { slots }) =>
	h(
		"div",
		{ class: "rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm" },
		[
			h(
				"div",
				{
					class:
						"flex items-center justify-between mb-2",
				},
				[
					h(
						"div",
						{
							class:
								"text-[10px] font-black uppercase tracking-widest text-gray-400",
						},
						props2.title
					),
					props2.count != null
						? h(
								"div",
								{
									class:
										"text-[10px] font-black uppercase tracking-widest text-gray-300",
								},
								String(props2.count)
						  )
						: null,
				]
			),
			slots.default?.(),
		]
	)
DataCard.props = ["title", "count"]

const MetaCard = (props2) => {
	if (!props2.rows?.length) return null
	return h(
		"div",
		{
			class:
				"rounded-2xl border border-gray-100 bg-white px-4 py-4 shadow-sm space-y-2.5",
		},
		props2.rows.map((r) =>
			h(
				"div",
				{ class: "flex items-center justify-between gap-3" },
				[
					h("div", { class: "text-xs font-semibold text-gray-500" }, r.label),
					h(
						"div",
						{ class: "text-sm font-bold text-gray-900 truncate" },
						String(r.value)
					),
				]
			)
		)
	)
}
MetaCard.props = ["rows"]

const TotalsRow = (props2) =>
	h(
		"div",
		{ class: "flex items-center justify-between gap-3" },
		[
			h(
				"div",
				{
					class: props2.strong
						? "text-xs font-bold text-gray-700"
						: "text-xs font-semibold text-gray-500",
				},
				props2.label
			),
			h(
				"div",
				{
					class: props2.strong
						? "text-base font-extrabold text-gray-900"
						: "text-sm font-bold text-gray-800",
				},
				props2.value
			),
		]
	)
TotalsRow.props = ["label", "value", "strong"]
</script>

<style scoped>
ion-modal {
	--height: 100%;
}
</style>
