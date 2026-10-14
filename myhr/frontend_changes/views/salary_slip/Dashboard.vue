<template>
	<BaseLayout :pageTitle="__('Salary Slips')">
		<template #body>
			<div class="flex flex-col my-5 p-4 gap-5">
				<!-- Hero YTD card -->
				<div
					class="rounded-2xl bg-blue-600 p-5 text-white shadow-sm"
					v-if="lastSalarySlip && lastSalarySlip.year_to_date"
				>
					<div
						class="text-[10px] font-black uppercase tracking-widest text-white/80"
					>
						{{ __("Year To Date") }}
					</div>
					<div class="mt-1 text-3xl font-black leading-none">
						{{
							formatCurrency(
								lastSalarySlip.year_to_date,
								lastSalarySlip.currency
							)
						}}
					</div>
					<div class="mt-1 text-xs font-bold text-white/80">
						{{ __("Gross earnings since April") }}
					</div>
				</div>

				<!-- Period picker -->
				<section class="space-y-3">
					<div class="flex items-center gap-3">
						<div
							class="p-2.5 rounded-xl bg-purple-50 text-purple-600 shadow-sm border border-purple-100"
						>
							<FeatherIcon name="calendar" class="h-5 w-5" />
						</div>
						<div class="flex flex-col">
							<h3
								class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
							>
								{{ __("Payroll Period") }}
							</h3>
							<span
								class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
							>
								{{ __("Pick a period to view slips") }}
							</span>
						</div>
					</div>
					<div class="rounded-2xl bg-white border border-gray-100 shadow-sm p-3">
						<Autocomplete
							:placeholder="__('Select Payroll Period')"
							v-model="selectedPeriod"
							:options="payrollPeriods.data"
						/>
					</div>
				</section>

				<!-- Slips section -->
				<section class="space-y-3">
					<div class="flex items-center gap-3">
						<div
							class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
						>
							<FeatherIcon name="file-text" class="h-5 w-5" />
						</div>
						<div class="flex flex-col">
							<h3
								class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
							>
								{{ __("Salary Slips") }}
							</h3>
							<span
								class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
							>
								<span v-if="documents.data?.length">
									{{ documents.data.length }} {{ __("slips") }}
								</span>
								<span v-else>{{ __("Tap a slip to view details") }}</span>
							</span>
						</div>
					</div>

					<div
						v-if="documents.data?.length"
						class="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden divide-y divide-gray-100"
					>
						<div
							v-for="link in documents.data"
							:key="link.name"
							class="p-4 cursor-pointer hover:bg-blue-50/60 active:bg-blue-100/60 transition-colors"
						>
							<router-link
								:to="{
									name: 'SalarySlipDetailView',
									params: { id: link.name },
								}"
								v-slot="{ navigate }"
							>
								<SalarySlipItem :doc="link" @click="navigate" />
							</router-link>
						</div>
					</div>
					<EmptyState v-else :message="__('No salary slips found')" />
				</section>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject, ref, computed, watch, onMounted, onBeforeUnmount } from "vue"
import { Autocomplete, FeatherIcon, createListResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import EmptyState from "@/components/EmptyState.vue"
import SalarySlipItem from "@/components/SalarySlipItem.vue"

import { formatCurrency } from "@/utils/formatters"

let selectedPeriod = ref({})
let periodsByName = ref({})

const employee = inject("$employee")
const dayjs = inject("$dayjs")
const socket = inject("$socket")
const __ = inject("$translate")

const payrollPeriods = createListResource({
	doctype: "Payroll Period",
	fields: ["name", "start_date", "end_date"],
	filters: { company: employee.data?.company },
	orderBy: "start_date desc",
	auto: true,
	transform(data) {
		return data.map((period) => {
			periodsByName.value[period.name] = period
			return {
				label: getPeriodLabel(period),
				value: period.name,
			}
		})
	},
	onSuccess: (data) => {
		selectedPeriod.value = data[0]
	},
})

const documents = createListResource({
	doctype: "Salary Slip",
	fields: [
		"name",
		"start_date",
		"end_date",
		"currency",
		"gross_pay",
		"net_pay",
		"year_to_date",
	],
	filters: { employee: employee.data?.name, docstatus: 1 },
	orderBy: "end_date desc",
})

const lastSalarySlip = computed(() => documents.data?.[0])

function getPeriodLabel(period) {
	return `${dayjs(period?.start_date).format("MMM YYYY")} - ${dayjs(
		period?.end_date
	).format("MMM YYYY")}`
}

watch(
	() => selectedPeriod.value,
	(value) => {
		let period = periodsByName.value[value?.value]
		documents.filters.start_date = [
			"between",
			[period?.start_date, period?.end_date],
		]
		documents.reload()
	}
)

onMounted(() => {
	socket.on("hrms:update_salary_slips", (data) => {
		if (data.employee === employee.data.name) {
			documents.reload()
		}
	})
})

onBeforeUnmount(() => {
	socket.off("hrms:update_salary_slips")
})
</script>
