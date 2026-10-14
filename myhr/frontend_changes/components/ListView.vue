<template>
	<ion-header class="ion-no-border">
		<div class="w-full sm:max-w-4xl mx-auto">
			<div
				class="flex flex-row bg-white/80 backdrop-blur-md shadow-sm py-3 px-3 items-center justify-between border-b border-gray-100"
			>
				<div class="flex flex-row items-center gap-1 min-w-0">
					<Button
						variant="ghost"
						class="!px-2 hover:bg-gray-100"
						@click="router.back()"
					>
						<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
					</Button>
					<div class="flex flex-col ml-1 overflow-hidden">
						<h2
							class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1"
						>
							{{ pageTitle }}
						</h2>
						<div
							v-if="documents.data?.length"
							class="flex items-center gap-1.5 opacity-60"
						>
							<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
							<span class="text-[10px] font-bold uppercase tracking-widest">
								{{ documents.data.length }} {{ __("entries") }}
							</span>
						</div>
					</div>
				</div>

				<div class="flex flex-row gap-2 shrink-0">
					<button
						id="show-filter-modal"
						type="button"
						class="rounded-xl p-2 border transition-colors"
						:class="
							areFiltersApplied
								? 'bg-blue-50 border-blue-200 text-blue-700'
								: 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
						"
					>
						<FeatherIcon name="filter" class="h-4 w-4" />
					</button>
					<router-link
						v-if="
							createPermission?.data?.has_permission &&
							props.doctype != 'Employee Checkin'
						"
						:to="{ name: formViewRoute }"
						v-slot="{ navigate }"
					>
						<button
							type="button"
							@click="navigate"
							class="rounded-xl px-3 py-2 bg-blue-600 text-white font-black text-[11px] uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center gap-1.5"
						>
							<FeatherIcon name="plus" class="h-3.5 w-3.5" />
							{{ __("New", null, props.doctype) }}
						</button>
					</router-link>
				</div>
			</div>
		</div>
	</ion-header>

	<ion-content>
		<ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
			<ion-refresher-content></ion-refresher-content>
		</ion-refresher>

		<div
			class="flex flex-col mb-7 p-4 h-full w-full sm:max-w-4xl sm:mx-auto overflow-y-auto"
			ref="scrollContainer"
			@scroll="() => handleScroll()"
		>
			<div class="w-full">
				<TabButtons
					v-if="props.tabButtons"
					class="mt-2 mb-4"
					:buttons="props.tabButtons"
					v-model="activeTab"
				/>

				<div
					v-if="!documents.loading && documents.data?.length"
					class="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden divide-y divide-gray-100"
				>
					<div
						v-for="link in documents.data"
						:key="link.name"
						class="p-4 cursor-pointer hover:bg-blue-50/60 active:bg-blue-100/60 transition-colors"
					>
						<!-- All doctypes now open the RequestActionSheet modal on
						     tap. Mirrors the home dashboard tile UX so approvers
						     get Approve / Reject + attachments here too, instead
						     of a stripped-down full-page DetailView. The
						     detail-view route still works for direct deep links
						     (/hrms/expense-claims/{id} etc.). -->
						<component
							v-if="props.doctype === 'Employee Checkin'"
							:is="listItemComponent[doctype]"
							:doc="link"
							:isTeamRequest="isTeamRequest"
							:workflowStateField="workflowStateField"
							@click="openRequestModal(link)"
						/>
						<component
							v-else
							:is="listItemComponent[doctype]"
							:doc="link"
							:isTeamRequest="isTeamRequest"
							:workflowStateField="workflowStateField"
							@click="openActionSheet(link)"
						/>
					</div>
				</div>
				<EmptyState
					:message="__('No {0} found', [props.doctype?.toLowerCase()])"
					v-else-if="!documents.loading"
				/>

				<div
					v-if="documents.loading"
					class="flex mt-6 items-center justify-center"
				>
					<LoadingIndicator class="w-6 h-6 text-blue-600" />
				</div>
			</div>
		</div>

		<CustomIonModal trigger="show-filter-modal">
			<template #actionSheet>
				<ListFiltersActionSheet
					:filterConfig="filterConfig"
					@applyFilters="applyFilters"
					@clearFilters="clearFilters"
					v-model:filters="filterMap"
				/>
			</template>
		</CustomIonModal>
	</ion-content>

	<ion-modal
		ref="modal"
		:is-open="isRequestModalOpen"
		@didDismiss="closeRequestModal"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<RequestActionSheet
			:fields="EMPLOYEE_CHECKIN_FIELDS"
			:showOpenForm="false"
			v-model="selectedRequest"
		/>
	</ion-modal>
</template>

<script setup>
import { useRouter } from "vue-router"
import { inject, ref, markRaw, watch, computed, reactive, onMounted } from "vue"
import {
	modalController,
	IonHeader,
	IonContent,
	IonModal,
	IonRefresher,
	IonRefresherContent,
} from "@ionic/vue"

import {
	Button,
	FeatherIcon,
	createResource,
	LoadingIndicator,
	debounce,
} from "frappe-ui"

import TabButtons from "@/components/TabButtons.vue"
import EmptyState from "@/components/EmptyState.vue"
import EmployeeCheckinItem from "@/components/EmployeeCheckinItem.vue"
import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"
import ShiftAssignmentItem from "@/components/ShiftAssignmentItem.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"
import EmployeeAdvanceItem from "@/components/EmployeeAdvanceItem.vue"
import ListFiltersActionSheet from "@/components/ListFiltersActionSheet.vue"
import CustomIonModal from "@/components/CustomIonModal.vue"
import RequestActionSheet from "@/components/RequestActionSheet.vue"
import { EMPLOYEE_CHECKIN_FIELDS } from "@/data/config/requestSummaryFields"

import useWorkflow from "@/composables/workflow"
import { useListUpdate } from "@/composables/realtime"

const __ = inject("$translate")
const props = defineProps({
	doctype: { type: String, required: true },
	fields: { type: Array, required: true },
	groupBy: { type: String, required: false },
	filterConfig: { type: Array, required: true },
	tabButtons: { type: Array, required: false },
	pageTitle: { type: String, required: true },
})

const getButtonKey = (tab) => tab?.key ?? tab

const listItemComponent = {
	"Employee Checkin": markRaw(EmployeeCheckinItem),
	"Attendance Request": markRaw(AttendanceRequestItem),
	"Shift Request": markRaw(ShiftRequestItem),
	"Shift Assignment": markRaw(ShiftAssignmentItem),
	"Leave Application": markRaw(LeaveRequestItem),
	"Expense Claim": markRaw(ExpenseClaimItem),
	"Employee Advance": markRaw(EmployeeAdvanceItem),
}

const router = useRouter()
const dayjs = inject("$dayjs")
const socket = inject("$socket")
const employee = inject("$employee")
const filterMap = reactive({})
const activeTab = ref(
	props.tabButtons ? getButtonKey(props.tabButtons[0]) : undefined
)
const areFiltersApplied = ref(false)
const appliedFilters = ref([])
const workflowStateField = ref(null)
const isRequestModalOpen = ref(false)
const selectedRequest = ref(null)

const scrollContainer = ref(null)
const hasNextPage = ref(true)
const listOptions = ref({
	doctype: props.doctype,
	fields: props.fields,
	group_by: props.groupBy,
	order_by: `\`tab${props.doctype}\`.modified desc`,
	page_length: 50,
})

const isTeamRequest = computed(() => {
	return (
		props.tabButtons &&
		activeTab.value === getButtonKey(props.tabButtons[1])
	)
})

const formViewRoute = computed(
	() => `${props.doctype.replace(/\s+/g, "")}FormView`
)
const detailViewRoute = computed(
	() => `${props.doctype.replace(/\s+/g, "")}DetailView`
)

const defaultFilters = computed(() => {
	const filters = []
	if (isTeamRequest.value) {
		filters.push([props.doctype, "employee", "!=", employee.data.name])
	} else {
		filters.push([props.doctype, "employee", "=", employee.data.name])
	}
	return filters
})

const documents = createResource({
	url: "frappe.desk.reportview.get",
	onSuccess: (data) => {
		if (data.values?.length < listOptions.value.page_length) {
			hasNextPage.value = false
		}
	},
	transform(data) {
		if (data.length === 0) return []
		const fields = data["keys"]
		const values = data["values"]
		const docs = values.map((value) => {
			const doc = {}
			fields.forEach((field, index) => {
				doc[field] = value[index]
			})
			return doc
		})

		let pagedData
		if (!documents.params.start || documents.params.start === 0) {
			pagedData = docs
		} else {
			pagedData = documents.data.concat(docs)
		}
		return pagedData
	},
})

const createPermission = createResource({
	url: "frappe.client.has_permission",
	params: { doctype: props.doctype, docname: null, perm_type: "create" },
	auto: true,
})

const openRequestModal = async (request) => {
	selectedRequest.value = request
	selectedRequest.value.doctype = "Employee Checkin"
	selectedRequest.value.date = request.time
	selectedRequest.value.formatted_time = dayjs(request.time).format("HH:mm a")
	selectedRequest.value.formatted_latitude = `${Number(request.latitude).toFixed(5)}°`
	selectedRequest.value.formatted_longitude = `${Number(request.longitude).toFixed(5)}°`
	isRequestModalOpen.value = true
}

// Open the RequestActionSheet modal for any non-Checkin doctype. Same
// surface the home dashboard tile shows — gives approvers the Approve /
// Reject buttons + attachments which the standalone DetailView pages don't
// carry. The action sheet pulls the full doc via createDocumentResource
// using selectedRequest.name + .doctype.
const openActionSheet = (link) => {
	selectedRequest.value = { ...link, doctype: props.doctype }
	isRequestModalOpen.value = true
}

const closeRequestModal = async () => {
	isRequestModalOpen.value = false
	selectedRequest.value = null
}

function initializeFilters() {
	props.filterConfig.forEach((filter) => {
		filterMap[filter.fieldname] = { condition: "=", value: null }
	})
	appliedFilters.value = []
}
initializeFilters()

function prepareFilters() {
	let condition = ""
	let value = ""
	appliedFilters.value = []
	for (const fieldname in filterMap) {
		condition = filterMap[fieldname].condition
		if (typeof condition === "object" && condition !== null) {
			condition = condition.value
		}
		value = filterMap[fieldname].value
		if (condition && value)
			appliedFilters.value.push([props.doctype, fieldname, condition, value])
	}
}

function applyFilters() {
	prepareFilters()
	fetchDocumentList()
	modalController.dismiss()
	areFiltersApplied.value = appliedFilters.value.length ? true : false
}

function clearFilters() {
	initializeFilters()
	fetchDocumentList()
	modalController.dismiss()
	areFiltersApplied.value = false
}

function fetchDocumentList(start = 0) {
	if (start === 0) hasNextPage.value = true
	// Filter out cancelled docs. docstatus is an int — string comparison can
	// behave inconsistently across MariaDB type coercion in edge cases.
	const filters = [[props.doctype, "docstatus", "!=", 2]]
	filters.push(...defaultFilters.value)
	if (appliedFilters.value) filters.push(...appliedFilters.value)
	// Only push the workflow field once — was being appended on every fetch
	// causing fields[] to grow unbounded with each pagination step.
	if (
		workflowStateField.value &&
		!listOptions.value.fields.includes(workflowStateField.value)
	) {
		listOptions.value.fields.push(workflowStateField.value)
	}

	documents.submit({
		...listOptions.value,
		start: start || 0,
		filters: filters,
	})
}

const handleScroll = debounce(() => {
	if (!hasNextPage.value) return
	const { scrollTop, scrollHeight, clientHeight } = scrollContainer.value
	const scrollPercentage =
		(scrollTop / (scrollHeight - clientHeight)) * 100
	if (scrollPercentage >= 90) {
		const start = documents.params.start + listOptions.value.page_length
		fetchDocumentList(start)
	}
}, 500)

const handleRefresh = (event) => {
	setTimeout(() => {
		fetchDocumentList()
		event.target.complete()
	}, 500)
}

watch(
	() => activeTab.value,
	(_value) => {
		fetchDocumentList()
	}
)

onMounted(async () => {
	const workflow = useWorkflow(props.doctype)
	await workflow.workflowDoc.promise
	workflowStateField.value = workflow.getWorkflowStateField()
	fetchDocumentList()
	useListUpdate(socket, props.doctype, () => fetchDocumentList())
})
</script>
