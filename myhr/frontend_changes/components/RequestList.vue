<template>
	<div
		v-if="props.items?.length"
		class="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden mt-4"
	>
		<div class="divide-y divide-gray-100">
			<div
				v-for="link in props.items"
				:key="link.name"
				class="flex flex-row p-4 items-center justify-between cursor-pointer hover:bg-blue-50/60 transition-colors active:bg-blue-100/60"
				@click="openRequestModal(link)"
			>
				<component
					:is="props.component || link.component"
					:doc="link"
					:workflowStateField="link.workflow_state_field"
					:isTeamRequest="props.teamRequests"
				/>
			</div>
		</div>

		<router-link
			v-if="props.addListButton"
			:to="{ name: props.listButtonRoute }"
			v-slot="{ navigate }"
		>
			<button
				type="button"
				@click="navigate"
				class="w-full px-4 py-3 flex items-center justify-center gap-1.5 text-[11px] font-black uppercase tracking-widest text-gray-500 hover:text-blue-700 bg-gray-50/50 hover:bg-blue-50 border-t border-gray-100 transition-colors"
			>
				{{ __("View All") }}
				<FeatherIcon name="arrow-right" class="h-3.5 w-3.5" />
			</button>
		</router-link>
	</div>
	<EmptyState
		v-else
		:message="emptyStateMessage || __('You have no requests')"
	/>

	<ion-modal
		ref="modal"
		:is-open="isRequestModalOpen"
		@didDismiss="closeRequestModal"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<RequestActionSheet
			:fields="fieldsMap[selectedRequest?.doctype]"
			v-model="selectedRequest"
		/>
	</ion-modal>
</template>

<script setup>
import { ref, inject } from "vue"
import { IonModal } from "@ionic/vue"
import { FeatherIcon } from "frappe-ui"
import RequestActionSheet from "@/components/RequestActionSheet.vue"
import EmptyState from "@/components/EmptyState.vue"

import {
	LEAVE_FIELDS,
	EXPENSE_CLAIM_FIELDS,
	ATTENDANCE_REQUEST_FIELDS,
	SHIFT_REQUEST_FIELDS,
	SHIFT_FIELDS,
} from "@/data/config/requestSummaryFields"

const __ = inject("$translate")
const props = defineProps({
	component: {
		type: Object,
	},
	items: {
		type: Array,
	},
	teamRequests: {
		type: Boolean,
		default: false,
	},
	addListButton: {
		type: Boolean,
		default: false,
	},
	listButtonRoute: {
		type: String,
		default: "",
	},
	emptyStateMessage: {
		type: String,
		default: "",
	},
})

const fieldsMap = {
	"Leave Application": LEAVE_FIELDS,
	"Expense Claim": EXPENSE_CLAIM_FIELDS,
	"Attendance Request": ATTENDANCE_REQUEST_FIELDS,
	"Shift Request": SHIFT_REQUEST_FIELDS,
	"Shift Assignment": SHIFT_FIELDS,
}

const isRequestModalOpen = ref(false)
const selectedRequest = ref(null)

const openRequestModal = async (request) => {
	selectedRequest.value = request
	isRequestModalOpen.value = true
}

const closeRequestModal = async () => {
	isRequestModalOpen.value = false
	selectedRequest.value = null
}
</script>
