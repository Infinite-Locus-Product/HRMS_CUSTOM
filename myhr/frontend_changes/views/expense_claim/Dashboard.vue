<template>
	<BaseLayout :pageTitle="__('Expense Claims')">
		<template #body>
			<div class="flex flex-col mt-5 mb-7 p-4 gap-6">
				<ExpenseClaimSummary />

				<div class="w-full">
					<router-link
						:to="{ name: 'ExpenseClaimFormView' }"
						v-slot="{ navigate }"
					>
						<button
							@click="navigate"
							class="w-full py-4 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2"
						>
							<FeatherIcon name="plus-circle" class="h-4 w-4" />
							{{ __("Claim an Expense") }}
						</button>
					</router-link>
				</div>

				<section class="space-y-3">
					<div class="flex items-center gap-3">
						<div
							class="p-2.5 rounded-xl bg-amber-50 text-amber-600 shadow-sm border border-amber-100"
						>
							<FeatherIcon name="credit-card" class="h-5 w-5" />
						</div>
						<div class="flex flex-col">
							<h3
								class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
							>
								{{ __("Recent Expenses") }}
							</h3>
							<span
								class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
							>
								{{ __("Your last claims") }}
							</span>
						</div>
					</div>
					<TabButtons
						:buttons="REQUEST_TABS"
						v-model="activeRequestTab"
					/>
					<RequestList
						v-if="activeRequestTab === 'My Requests'"
						:component="markRaw(ExpenseClaimItem)"
						:items="myClaims.data"
						:addListButton="true"
						listButtonRoute="ExpenseClaimListView"
						:emptyStateMessage="__('You have not raised any Expense Claims')"
					/>
					<RequestList
						v-else
						:component="markRaw(ExpenseClaimItem)"
						:items="teamClaims.data"
						:teamRequests="true"
						:addListButton="true"
						listButtonRoute="ExpenseClaimListView"
						:emptyStateMessage="__('No team Expense Claims waiting on you')"
					/>
				</section>

				<section class="space-y-3">
					<div class="flex items-center justify-between gap-3">
						<div class="flex items-center gap-3 min-w-0">
							<div
								class="p-2.5 rounded-xl bg-green-50 text-green-600 shadow-sm border border-green-100"
							>
								<FeatherIcon name="trending-up" class="h-5 w-5" />
							</div>
							<div class="flex flex-col min-w-0">
								<h3
									class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
								>
									{{ __("Advance Balance") }}
								</h3>
								<span
									class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
								>
									{{ __("Outstanding employee advances") }}
								</span>
							</div>
						</div>
						<router-link
							:to="{ name: 'EmployeeAdvanceListView' }"
							v-slot="{ navigate }"
						>
							<button
								type="button"
								@click="navigate"
								class="text-[10px] font-black uppercase tracking-widest text-blue-600 hover:text-blue-800 transition-colors flex items-center gap-1 shrink-0"
							>
								{{ __("View all") }}
								<FeatherIcon name="arrow-right" class="h-3 w-3" />
							</button>
						</router-link>
					</div>
					<EmployeeAdvanceBalance :items="advanceBalance.data" />
				</section>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { markRaw, ref } from "vue"
import { FeatherIcon } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import ExpenseClaimSummary from "@/components/ExpenseClaimSummary.vue"
import RequestList from "@/components/RequestList.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"
import EmployeeAdvanceBalance from "@/components/EmployeeAdvanceBalance.vue"
import TabButtons from "@/components/TabButtons.vue"

import { myClaims, teamClaims } from "@/data/claims"
import { advanceBalance } from "@/data/advances"

// Same My/Team split that lives on Home — replicated here so an approver
// landing on Expenses from a notification finds the request waiting on them
// without bouncing back to the home tab.
const REQUEST_TABS = ["My Requests", "Team Requests"] // __("My Requests"), __("Team Requests")
const activeRequestTab = ref("My Requests")
</script>
