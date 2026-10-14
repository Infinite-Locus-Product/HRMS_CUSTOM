<template>
	<ion-tab-bar
		slot="bottom"
		class="bg-white/95 backdrop-blur-xl border-t border-gray-100 shadow-[0_-1px_3px_rgba(0,0,0,0.04)] w-full sm:max-w-4xl mx-auto py-1 pb-1 standalone:pb-safe-bottom"
	>
		<ion-tab-button
			v-for="item in tabItems"
			:key="item.title"
			:tab="item.tab"
			v-bind="item.fullNav ? {} : { href: item.route }"
			:class="[
				'relative bg-transparent text-[10px] tracking-wide transition-all',
				isActiveTab(item)
					? 'text-blue-700 font-black'
					: 'text-gray-500 font-bold hover:text-gray-700',
			]"
			@click="item.fullNav ? fullNavigate(item.route) : undefined"
		>
			<!-- Top bar accent — only on active -->
			<div
				v-if="isActiveTab(item)"
				class="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-[2px] rounded-b-full bg-blue-600"
			></div>

			<!-- Icon tile -->
			<div
				class="flex items-center justify-center h-10 w-10 rounded-2xl transition-all duration-200"
				:class="
					isActiveTab(item)
						? 'bg-blue-50 text-blue-700 scale-110'
						: 'text-gray-500'
				"
			>
				<component :is="item.icon" class="h-5 w-5" />
			</div>
			<div class="mt-0.5 leading-none">{{ item.title }}</div>
		</ion-tab-button>
	</ion-tab-bar>
</template>

<script setup>
import { useRoute } from "vue-router"
import { IonTabBar, IonTabButton } from "@ionic/vue"

import HomeIcon from "@/components/icons/HomeIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import SalaryIcon from "@/components/icons/SalaryIcon.vue"
import { inject } from "vue"

const __ = inject("$translate")
const route = useRoute()

function fullNavigate(path) {
	window.location.href = "/hrms" + path
}

const TAB_SECTION_PREFIXES = {
	Attendance: [
		"/attendance-requests",
		"/shift-requests",
		"/shift-assignments",
		"/employee-checkins",
	],
	Leaves: ["/leave-applications", "/holidays"],
	Expenses: ["/expense-claims", "/employee-advances"],
	Salary: ["/salary-slips"],
}

function isActiveTab(item) {
	if (route.path === item.route) return true
	const prefixes = TAB_SECTION_PREFIXES[item.tab] || []
	return prefixes.some((p) => route.path.startsWith(p))
}

const tabItems = [
	{
		icon: HomeIcon,
		title: __("Home"),
		tab: "Home",
		route: "/home",
		fullNav: false,
	},
	{
		icon: AttendanceIcon,
		title: __("Attendance"),
		tab: "Attendance",
		route: "/dashboard/attendance",
		fullNav: false,
	},
	{
		icon: LeaveIcon,
		title: __("Leaves"),
		tab: "Leaves",
		route: "/dashboard/leaves",
		fullNav: false,
	},
	{
		icon: ExpenseIcon,
		title: __("Expenses"),
		tab: "Expenses",
		route: "/dashboard/expense-claims",
		fullNav: false,
	},
	{
		icon: SalaryIcon,
		title: __("Salary"),
		tab: "Salary",
		route: "/dashboard/salary-slips",
		fullNav: false,
	},
]
</script>
