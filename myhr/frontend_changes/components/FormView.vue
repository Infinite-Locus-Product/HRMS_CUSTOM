<template>
	<div class="flex flex-col h-full w-full" v-if="isFormReady">
		<div class="w-full h-full bg-white sm:max-w-4xl w-full sm:mx-auto flex flex-col">
			<header
				class="flex flex-row bg-white shadow-sm py-4 px-3 items-center sticky top-0 z-[1000]"
			>
				<Button
					variant="ghost"
					class="!pl-0 hover:bg-white"
					@click="router.back()"
				>
					<FeatherIcon name="chevron-left" class="h-5 w-5" />
				</Button>
				<div
					v-if="id"
					class="flex flex-row items-center gap-2 overflow-hidden grow"
				>
					<h2
						class="text-xl font-semibold text-gray-900 whitespace-nowrap overflow-hidden text-ellipsis"
					>
						{{ __(props.doctype) }}
					</h2>
					<Badge
						:label="id"
						class="whitespace-nowrap text-[8px]"
						variant="outline"
					/>
					<Badge
						v-if="status"
						:label="__(status, null, doctype)"
						:theme="statusColor"
						class="whitespace-nowrap text-[8px]"
					/>

					<Dropdown
						class="ml-auto"
						:options="[
							{
								label: __('Delete'),
								condition: showDeleteButton,
								onClick: () => (showDeleteDialog = true),
							},
							{ label: __('Reload'), onClick: () => reloadDoc() },
						]"
						:button="{
							label: __('Menu'),
							icon: 'more-horizontal',
							variant: 'ghost',
						}"
					/>
				</div>
				<h2 v-else class="text-2xl font-semibold text-gray-900">
					{{ __('New {0}', [__(doctype)], props.doctype) }}
				</h2>
			</header>

			<!-- Form -->
			<div class="bg-white grow overflow-y-auto">
				<!-- Tabs -->
				<template v-if="tabbedView">
					<div
						class="px-4 sticky top-0 z-[100] bg-white text-sm font-medium text-center text-gray-500 border-b border-gray-200 dark:text-gray-400 dark:border-gray-700"
					>
						<ul class="flex -mb-px overflow-auto hide-scrollbar">
							<li class="mr-2 whitespace-nowrap" v-for="tab in tabs">
								<button
									@click="activeTab = tab.name"
									class="inline-block py-4 px-2 border-b-2 border-transparent rounded-t-lg"
									:class="[
										activeTab === tab.name
											? '!text-gray-800 !border-gray-800'
											: 'hover:text-gray-600 hover:border-gray-300',
									]"
								>
									{{ __(tab.name, null, props.doctype) }}
								</button>
							</li>
						</ul>
					</div>

					<template v-for="(fieldList, tabName, index) in tabFields">
						<div
							v-show="tabName === activeTab"
							class="flex flex-col space-y-4 p-4"
						>
							<template v-for="field in fieldList" :key="field.fieldname">
								<slot
									v-if="field.fieldtype == 'Table'"
									:name="field.fieldname"
									:isFormReadOnly="isFormReadOnly"
								></slot>

								<FormField
									v-else
									:fieldtype="field.fieldtype"
									:fieldname="field.fieldname"
									v-model="formModel[field.fieldname]"
									:default="field.default"
									:label="__(field.label, null, props.doctype)"
									:options="field.options"
									:linkFilters="field.linkFilters"
									:documentList="field.documentList"
									:readOnly="isFieldReadOnly(field)"
									:reqd="Boolean(field.reqd)"
									:hidden="Boolean(field.hidden)"
									:errorMessage="field.error_message"
									:minDate="field.minDate"
									:maxDate="field.maxDate"
									:addSectionPadding="fieldList[0].name !== field.name"
								/>
							</template>

							<!-- Attachment upload -->
							<div
								class="flex flex-row gap-2 items-center justify-center p-5"
								v-if="isFileUploading"
							>
								<LoadingIndicator class="w-3 h-3 text-gray-800" />
								<span class="text-gray-900 text-sm">{{ __("Uploading...") }} </span>
							</div>

							<FileUploaderView
								v-else-if="showAttachmentView && index === 0"
								v-model="fileAttachments"
								@handleFileSelect="handleFileSelect"
								@handleFileDelete="handleFileDelete"
							/>
						</div>
					</template>
				</template>

				<div class="flex flex-col space-y-4 p-4" v-else>
					<FormField
						v-for="field in props.fields"
						:key="field.name"
						:fieldtype="field.fieldtype"
						:fieldname="field.fieldname"
						v-model="formModel[field.fieldname]"
						:default="field.default"
						:label="__(field.label, null, props.doctype)"
						:options="field.options"
						:linkFilters="field.linkFilters"
						:documentList="field.documentList"
						:readOnly="isFieldReadOnly(field)"
						:reqd="Boolean(field.reqd)"
						:hidden="Boolean(field.hidden)"
						:errorMessage="field.error_message"
						:minDate="field.minDate"
						:maxDate="field.maxDate"
					/>

					<!-- Attachment upload -->
					<div
						class="flex flex-row gap-2 items-center justify-center p-5"
						v-if="isFileUploading"
					>
						<LoadingIndicator class="w-3 h-3 text-gray-800" />
						<span class="text-gray-900 text-sm">{{ __("Uploading...") }} </span>
					</div>

					<FileUploaderView
						v-else-if="showAttachmentView"
						v-model="fileAttachments"
						@handleFileSelect="handleFileSelect"
						@handleFileDelete="handleFileDelete"
					/>
				</div>
			</div>

			<!-- Form Primary/Secondary Button -->
			<!-- custom form button eg: Download button in salary slips -->
			<div
				v-if="!showFormButton"
				class="px-4 pt-4 pb-4 standalone:pb-safe-bottom sm:max-w-4xl w-full sm:mx-auto bg-white sticky bottom-0 w-full drop-shadow-xl z-40 border-t rounded-t-lg"
			>
				<slot name="formButton"></slot>
			</div>

			<!-- workflow actions -->
			<WorkflowActionSheet
				v-else-if="!isFormDirty && workflow?.hasWorkflow"
				:doc="documentResource.doc"
				:workflow="workflow"
				@workflowApplied="reloadDoc()"
			/>

			<!-- save/submit/cancel — brand-blue primary, matches the
			     "CLAIM AN EXPENSE" / leave-Submit pattern (see
			     docs/DESIGN_SYSTEM.md §Buttons). -->
			<div
				v-else-if="isFormDirty || (!workflow?.hasWorkflow && formButton)"
				class="px-4 pt-4 pb-4 standalone:pb-safe-bottom sm:max-w-4xl w-full sm:mx-auto bg-white sticky bottom-0 w-full drop-shadow-xl z-40 border-t rounded-t-lg"
			>
				<ErrorMessage
					class="mb-2"
					:message="
						formErrorMessage ||
						docList?.insert?.error ||
						insertAndSubmit?.error ||
						documentResource?.setValue?.error
					"
				/>

				<button
					type="button"
					@click="formButton === 'Save' ? saveForm() : submitOrCancelForm()"
					:disabled="
						docList.insert.loading || insertAndSubmit.loading || documentResource?.setValue?.loading
					"
					:class="formButton === 'Cancel'
						? 'w-full py-4 rounded-2xl bg-gray-100 text-gray-700 font-black text-xs uppercase tracking-widest hover:bg-gray-200 active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-50'
						: 'w-full py-4 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50'"
				>
					<LoadingIndicator
						v-if="docList.insert.loading || insertAndSubmit.loading || documentResource?.setValue?.loading"
						class="h-4 w-4 text-white"
					/>
					<FeatherIcon
						v-else
						:name="formButton === 'Save' ? 'send' : formButton === 'Submit' ? 'check' : 'x-circle'"
						class="h-4 w-4"
					/>
					{{ __(formButton) }}
				</button>
			</div>
		</div>
	</div>

	<!-- Confirmation Dialogs -->
	<Dialog v-model="showDeleteDialog">
		<template #body-title>
			<h2 class="text-xl font-bold">{{ __("Delete {0}", [__(props.doctype)]) }}</h2>
		</template>
		<template #body-content>
			<p>
				{{ __("Are you sure you want to delete the {0}", [__(props.doctype)])  }}
				<span class="font-bold">{{ formModel.name }}</span>
				?
			</p>
		</template>
		<template #actions>
			<div class="flex flex-row gap-4">
				<Button
					variant="outline"
					class="py-5 w-full"
					@click="showDeleteDialog = false"
				>
					{{ __("Cancel") }}
				</Button>
				<Button
					variant="solid"
					theme="red"
					@click="handleDocDelete"
					class="py-5 w-full"
				>
					{{__("Delete") }}
				</Button>
			</div>
		</template>
	</Dialog>

	<Dialog v-model="showSubmitDialog">
		<template #body-title>
			<h2 class="text-xl font-bold">{{ __("Confirm") }} </h2>
		</template>
		<template #body-content>
			<p>
				{{ __("Permanently submit {0}", [__(props.doctype)]) }}
				<span class="font-bold">{{ formModel.name }}</span>
				?
			</p>
		</template>
		<template #actions>
			<div class="flex flex-row gap-4">
				<Button
					variant="outline"
					class="py-5 w-full"
					@click="showSubmitDialog = false"
				>
					{{ __("No") }}
				</Button>
				<Button
					variant="solid"
					@click="handleDocUpdate('submit')"
					class="py-5 w-full"
				>
					{{ __("Yes") }}
				</Button>
			</div>
		</template>
	</Dialog>

	<Dialog v-model="showCancelDialog">
		<template #body-title>
			<h2 class="text-xl font-bold">{{ __("Confirm") }} </h2>
		</template>
		<template #body-content>
			<p>
				{{ __("Permanently cancel {0}", [__(props.doctype)]) }}
				<span class="font-bold">{{ formModel.name }}</span
				>?
			</p>
		</template>
		<template #actions>
			<div class="flex flex-row gap-4">
				<Button
					variant="outline"
					class="py-5 w-full"
					@click="showCancelDialog = false"
				>
					{{ __("No") }}
				</Button>
				<Button
					variant="solid"
					@click="handleDocUpdate('cancel')"
					class="py-5 w-full"
				>
					{{ __("Yes") }}
				</Button>
			</div>
		</template>
	</Dialog>

	<!-- Celebratory success popup — replaces the old toast on insert.
	     Dismiss button drives the redirect so the user gets a moment to
	     register the success state before the page swap. -->
	<SuccessModal
		:isOpen="successOpen"
		:title="successTitle || __('{0} submitted!', [__(doctype)])"
		:subtitle="successSubtitle || __('Your approver has been notified.')"
		:reference="successInsertedDoc?.name || ''"
		@dismiss="onSuccessDismissed"
	/>
</template>

<script setup>
import { computed, inject, nextTick, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import {
	ErrorMessage,
	Badge,
	FeatherIcon,
	createListResource,
	createDocumentResource,
	toast,
	createResource,
	Dropdown,
	Dialog,
	LoadingIndicator,
} from "frappe-ui"
import FormField from "@/components/FormField.vue"
import FileUploaderView from "@/components/FileUploaderView.vue"
import WorkflowActionSheet from "@/components/WorkflowActionSheet.vue"
import SuccessModal from "@/components/SuccessModal.vue"

import { FileAttachment, guessStatusColor } from "@/composables"
import { showErrorFromException } from "@/data/errorModal"
import useWorkflow from "@/composables/workflow"
import { getCompanyCurrency } from "@/data/currencies"
import { formatCurrency } from "@/utils/formatters"

const props = defineProps({
	doctype: {
		type: String,
		required: true,
	},
	modelValue: {
		type: Object,
		required: true,
	},
	isSubmittable: {
		type: Boolean,
		required: false,
		default: false,
	},
	fields: {
		type: Array,
		required: true,
	},
	id: {
		type: String,
		required: false,
	},
	tabbedView: {
		type: Boolean,
		required: false,
		default: false,
	},
	tabs: {
		type: Array,
		required: false,
	},
	showAttachmentView: {
		type: Boolean,
		required: false,
		default: false,
	},
	showFormButton: {
		type: Boolean,
		required: false,
		default: true,
	},
	// Where to send the user after a successful insert. Default routes to the
	// per-doctype DetailView; pass "list" to bounce back to the list view
	// instead. Used by Leave Application / Attendance Request so the employee
	// doesn't land on a confusing edit screen with Status/Approval fields they
	// shouldn't be touching.
	redirectAfterInsert: {
		type: String,
		required: false,
		default: "detail", // "detail" | "list"
	},
	// Suppress the Delete entry in the header `…` menu. Used by Leave
	// Application / Attendance Request — employees withdraw via the
	// Cancel-with-remarks flow, never via destructive delete; HR can still
	// delete from Desk if a row is genuinely garbage.
	allowDelete: {
		type: Boolean,
		required: false,
		default: true,
	},
	// Collapse Save + Submit into a single tap: after the insert resolves,
	// flip docstatus 0 → 1 so the doc lands in the approver's queue
	// immediately. Only meaningful when isSubmittable is true.
	submitOnSave: {
		type: Boolean,
		required: false,
		default: false,
	},
	// Strings shown in the success modal that pops up after a successful
	// insert. Falls back to a generic "<Doctype> submitted!" headline.
	successTitle: {
		type: String,
		required: false,
		default: "",
	},
	successSubtitle: {
		type: String,
		required: false,
		default: "",
	},
	// Optional whitelisted endpoint to call AFTER a successful insert,
	// before the success modal pops. Receives `{name: data.name}`. Used
	// by the Expense Claim flow to chain `submit_expense_claim_for_review`
	// onto Save so the claim lands in the approver's queue immediately.
	// Generic enough to use elsewhere — it's just "post-insert hook".
	postInsertEndpoint: {
		type: String,
		required: false,
		default: "",
	},
})
const emit = defineEmits(["validateForm", "update:modelValue"])
const router = useRouter()

const __ = inject("$translate")

let activeTab = ref(props.tabs?.[0].name)
let fileAttachments = ref([])
let statusColor = ref("")
let formErrorMessage = ref("")
let isFormDirty = ref(false)
let isFormUpdated = ref(false)
let showDeleteDialog = ref(false)
let showSubmitDialog = ref(false)
let showCancelDialog = ref(false)
let isFileUploading = ref(false)
let workflow = ref(null)

const formModel = computed({
	get() {
		return props.modelValue
	},
	set(newValue) {
		emit("update:modelValue", newValue)
	},
})

const status = computed(() => {
	if (!props.id) return ""

	if (workflow.value) {
		const stateField = workflow.value.getWorkflowStateField()
		if (stateField) return formModel.value[stateField]
	}

	return formModel.value.status || formModel.value.approval_status
})

watch(
	() => formModel.value,
	() => {
		if (!props.id) return

		if (isFormReady.value && !isFormUpdated.value) {
			isFormDirty.value = true
		} else if (isFormUpdated.value) {
			isFormUpdated.value = false
		}
	},
	{ deep: true }
)

watch(
	() => status.value,
	async (value) => {
		if (!value) return
		statusColor.value = await guessStatusColor(props.doctype, status.value)
	},
	{ immediate: true }
)

const tabFields = computed(() => {
	let fieldsByTab = {}
	let fieldList = []
	let firstFieldIndex = 0
	let lastFieldIndex = 0

	props.tabs?.forEach((tab) => {
		lastFieldIndex = props.fields.findIndex(
			(field) => field.fieldname === tab.lastField
		)
		fieldList = props.fields.slice(firstFieldIndex, lastFieldIndex + 1)
		fieldsByTab[tab.name] = fieldList
		firstFieldIndex = lastFieldIndex + 1
	})

	return fieldsByTab
})

const attachedFiles = createResource({
	url: "hrms.api.get_attachments",
	params: {
		dt: props.doctype,
		dn: props.id,
	},
	transform(data) {
		return data.map((file) => (file.uploaded = true))
	},
	onSuccess(data) {
		fileAttachments.value = data
	},
})

const handleFileSelect = (e) => {
	if (props.id) {
		uploadAllAttachments(props.doctype, props.id, [...e.target.files])
	} else {
		fileAttachments.value.push(...e.target.files)
	}
}

const handleFileDelete = async (fileObj) => {
	if (fileObj.uploaded) {
		const fileAttachment = new FileAttachment(fileObj)
		await fileAttachment.delete()
		await attachedFiles.reload()
	} else {
		fileAttachments.value = fileAttachments.value.filter(
			(file) => file.name !== fileObj.name
		)
	}
}

async function uploadAllAttachments(documentType, documentName, attachments) {
	isFileUploading.value = true

	const uploadPromises = attachments.map((attachment) => {
		const fileAttachment = new FileAttachment(attachment)
		return fileAttachment
			.upload(documentType, documentName, "")
			.then((fileDoc) => {
				fileDoc.uploaded = true
				if (props.id) {
					fileAttachments.value.push(fileDoc)
				}
			})
	})

	await Promise.allSettled(uploadPromises)
	isFileUploading.value = false
}

// CRUD for doc
// Success modal state — replaces the old toast + immediate redirect.
const successOpen = ref(false)
const successInsertedDoc = ref(null)

function onSuccessDismissed() {
	successOpen.value = false
	const data = successInsertedDoc.value
	if (!data) return

	if (props.redirectAfterInsert === "list") {
		router.replace({
			name: `${props.doctype.replace(/\s+/g, "")}ListView`,
		})
	} else {
		router.replace({
			name: `${props.doctype.replace(/\s+/g, "")}DetailView`,
			params: { id: data.name },
		})
	}
}

// Single-shot insert+submit — used when submitOnSave is true. Avoids
// the TimestampMismatchError that hits when controllers update fields
// via db.set_value during insert (Expense Claim child totals etc.) by
// keeping insert and submit in one server transaction.
const insertAndSubmit = createResource({
	url: "myhr.api.insert_and_submit",
	async onSuccess(data) {
		await uploadAllAttachments(data.doctype, data.name, fileAttachments.value)
		successInsertedDoc.value = data
		successOpen.value = true
	},
	onError(err) {
		console.error(`Error creating ${props.doctype}`, err)
		showErrorFromException(err, __("Error creating {0}", [__(props.doctype)]))
	},
})

// Generic post-insert hook caller. Lazy-built so we don't allocate a
// resource when the prop isn't set.
let postInsertResource = null
function callPostInsertHook(name) {
	if (!props.postInsertEndpoint) return Promise.resolve()
	if (!postInsertResource) {
		postInsertResource = createResource({
			url: props.postInsertEndpoint,
			onError(err) {
				console.error(`Post-insert hook failed for ${props.doctype}`, err)
				showErrorFromException(
					err,
					__("Saved, but the follow-up step failed."),
				)
			},
		})
	}
	return postInsertResource.submit({ name })
}

const docList = createListResource({
	doctype: props.doctype,
	insert: {
		async onSuccess(data) {
			await uploadAllAttachments(data.doctype, data.name, fileAttachments.value)
			// Run the optional post-insert hook (e.g. submit-for-review).
			// If it throws, the catch above logs and shows the error modal;
			// we still pop the success modal since the doc was inserted —
			// the user can retry the chained step from the detail view.
			try {
				await callPostInsertHook(data.name)
			} catch (e) {
				/* error already surfaced via the resource's onError */
			}
			successInsertedDoc.value = data
			successOpen.value = true
		},
		onError(err) {
			console.error(`Error creating ${props.doctype}`, err)
			showErrorFromException(err, __("Error creating {0}", [__(props.doctype)]))
		},
	},
})

const documentResource = createDocumentResource({
	doctype: props.doctype,
	name: props.id,
	fields: "*",
	setValue: {
		onSuccess() {
			toast({
				title: __("Success"),
				text: __("{0} updated successfully!", [__(props.doctype)]),
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
		},
		onError(err) {
			console.error(`Error updating ${props.doctype}`, err)
			showErrorFromException(err, __("Error updating {0}", [__(props.doctype)]))
		},
	},
	delete: {
		onSuccess() {
			router.back()
			toast({
				title: __("Success"),
				text: __("{0} deleted successfully!", [__(props.doctype)]),
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
		},
		onError(err) {
			console.error(`Error deleting ${props.doctype}`, err)
			showErrorFromException(err, __("Error deleting {0}", [__(props.doctype)]))
		},
	},
})

const docPermissions = createResource({
	url: "frappe.client.get_doc_permissions",
	params: { doctype: props.doctype, docname: props.id },
})

const permittedWriteFields = createResource({
	url: "hrms.api.get_permitted_fields_for_write",
	params: { doctype: props.doctype },
})

const formButton = computed(() => {
	if (!props.showFormButton) return

	if (props.id && props.isSubmittable && !isFormDirty.value) {
		if (formModel.value.docstatus === 0 && hasPermission("submit")) {
			return "Submit"
		} else if (formModel.value.docstatus === 1 && hasPermission("cancel")) {
			return "Cancel"
		}
	} else if (formModel.value.docstatus !== 2) {
		return "Save"
	}
})

function showDeleteButton() {
	if (!props.allowDelete) return false
	return props.id && formModel.value.docstatus !== 1 && hasPermission("delete")
}

function hasPermission(action) {
	return docPermissions.data?.permissions[action]
}

function isFieldReadOnly(field) {
	return (
		Boolean(field.read_only)
		|| isFormReadOnly.value
		|| (props.id && !permittedWriteFields.data?.includes(field.fieldname))
	)
}

function handleDocInsert() {
	if (!validateMandatoryFields()) return
	if (props.submitOnSave && props.isSubmittable) {
		// Single-shot path — inserts and submits in one server call.
		// Approver can still flip approval_status on the submitted doc
		// (it's an allow_on_submit field).
		insertAndSubmit.submit({ doc: formModel.value })
	} else {
		docList.insert.submit(formModel.value)
	}
}

function validateMandatoryFields() {
	const errorFields = props.fields
		.filter(
			(field) =>
				field.reqd && !field.hidden && !formModel.value[field.fieldname]
		)
		.map((field) => field.label)

	if (errorFields.length) {
		formErrorMessage.value = `${errorFields.join(", ")} ${
			errorFields.length > 1 ? "fields are mandatory" : "field is mandatory"
		}`
		return false
	} else {
		formErrorMessage.value = ""
		return true
	}
}

async function handleDocUpdate(action) {
	if (documentResource.doc) {
		let params = { ...formModel.value }

		if (!validateMandatoryFields()) return

		if (action == "submit") {
			params.docstatus = 1
		} else if (action == "cancel") {
			params.docstatus = 2
		}

		await documentResource.setValue.submit(params)
		await documentResource.get.promise
		resetForm()
	}

	if (action === "submit") showSubmitDialog.value = false
	else if (action === "cancel") showCancelDialog.value = false
}

function saveForm() {
	emit("validateForm")

	if (props.id) {
		handleDocUpdate()
	} else {
		handleDocInsert()
	}
}

function submitOrCancelForm() {
	if (isFormDirty.value) return

	if (formModel.value.docstatus === 0) {
		emit("validateForm")
		showSubmitDialog.value = true
	} else if (formModel.value.docstatus === 1) {
		showCancelDialog.value = true
	}
}

function handleDocDelete() {
	documentResource.delete.submit()
	showDeleteDialog.value = false
}

async function reloadDoc() {
	await documentResource.reload()
	resetForm()
}

function resetForm() {
	formModel.value = { ...documentResource.doc }
	nextTick(() => {
		isFormDirty.value = false
		isFormUpdated.value = true
	})
}

async function setFormattedCurrency() {
	const companyCurrency = await getCompanyCurrency(formModel.value.company)

	props.fields.forEach((field) => {
		if (field.fieldtype !== "Currency") return
		if (!(field.readOnly || isFormReadOnly.value)) return

		if (field.options === "currency") {
			formModel.value[field.fieldname] = formatCurrency(
				formModel.value[field.fieldname],
				formModel.value.currency
			)
		} else {
			formModel.value[field.fieldname] = formatCurrency(
				formModel.value[field.fieldname],
				companyCurrency
			)
		}
	})
}

const isFormReadOnly = computed(() => {
	if (!isFormReady.value) return true
	if (!props.id) return false

	// submitted & cancelled docs are read only
	if (formModel.value.docstatus !== 0) return true

	// read only due to workflow based on current user's roles
	if (workflow.value?.isReadOnly(formModel.value)) return true
})

const isFormReady = computed(() => {
	if (!props.id) return true

	return !documentResource.get.loading && documentResource.doc
})

onMounted(async () => {
	if (props.id) {
		await documentResource.get.promise
		formModel.value = { ...documentResource.doc }
		await docPermissions.reload()
		await permittedWriteFields.reload()
		await attachedFiles.reload()
		await setFormattedCurrency()

		// workflow
		workflow.value = useWorkflow(props.doctype)

		isFormDirty.value = false
	}
})
</script>
