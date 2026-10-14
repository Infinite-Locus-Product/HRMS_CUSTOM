<template>
	<BaseLayout :pageTitle="__('Leaves & Holidays')">
		<template #body>
			<div class="flex flex-col items-center mt-7 mb-7 py-4">
				<LeaveBalance />

				<div class="flex flex-col gap-7 mt-5 px-4 w-full">
					<router-link
						:to="{ name: 'LeaveApplicationFormView' }"
						v-slot="{ navigate }"
					>
						<button
							@click="navigate"
							class="w-full py-4 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2"
						>
							<FeatherIcon name="plus-circle" class="h-4 w-4" />
							{{ __("Request a Leave") }}
						</button>
					</router-link>
					<div>
						<div class="flex items-center justify-between mb-2">
							<div class="text-lg text-gray-800 font-bold">
								{{ __("Leave Applications") }}
							</div>
						</div>
						<TabButtons
							:buttons="REQUEST_TABS"
							v-model="activeRequestTab"
						/>
						<RequestList
							v-if="activeRequestTab === 'My Requests'"
							:component="markRaw(LeaveRequestItem)"
							:items="myLeaves.data"
							:addListButton="true"
							listButtonRoute="LeaveApplicationListView"
							:emptyStateMessage="__('You have not raised any Leave Applications')"
						/>
						<RequestList
							v-else
							:component="markRaw(LeaveRequestItem)"
							:items="teamLeaves.data"
							:teamRequests="true"
							:addListButton="true"
							listButtonRoute="LeaveApplicationListView"
							:emptyStateMessage="__('No team Leave Applications waiting on you')"
						/>
					</div>
					<Holidays />
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { markRaw, ref } from "vue"
import { FeatherIcon } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import LeaveBalance from "@/components/LeaveBalance.vue"
import RequestList from "@/components/RequestList.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import TabButtons from "@/components/TabButtons.vue"
import Holidays from "@/components/Holidays.vue"

import { myLeaves, teamLeaves } from "@/data/leaves"

// Same My/Team split that lives on Home — replicated here so an approver
// landing on Leaves from a notification finds the request waiting on them
// without bouncing back to the home tab.
const REQUEST_TABS = ["My Requests", "Team Requests"] // __("My Requests"), __("Team Requests")
const activeRequestTab = ref("My Requests")
</script>
