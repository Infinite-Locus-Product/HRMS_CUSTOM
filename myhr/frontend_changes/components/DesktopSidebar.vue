<template>
	<div class="hidden lg:flex flex-col w-64 h-screen bg-gray-50 border-r border-gray-200 sticky top-0 left-0 p-4 shrink-0 overflow-y-auto">
		<!-- Sidebar Logo / Branding -->
		<div class="flex items-center gap-3 px-2 mb-8 mt-2">
			<div class="w-8 h-8 rounded-lg bg-gray-900 flex items-center justify-center text-white shrink-0 shadow-lg">
				<span class="font-bold text-xs">HR</span>
			</div>
			<div class="flex flex-col">
				<span class="font-bold text-gray-900 text-sm tracking-tight leading-none mb-1">{{ __("Frappe HR") }}</span>
				<span class="text-[10px] text-gray-500 uppercase font-bold tracking-widest leading-none">Self-Service</span>
			</div>
		</div>

		<!-- Nav Items -->
		<nav class="flex flex-col gap-1 flex-grow">
			<component
				:is="item.fullNav ? 'div' : 'router-link'"
				v-for="item in navItems"
				:key="item.title"
				v-bind="item.fullNav ? {} : { to: item.route }"
				class="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all group relative overflow-hidden cursor-pointer"
				:class="[
					route.path === item.route 
						? 'bg-white shadow-sm ring-1 ring-black/5 text-gray-900' 
						: 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
				]"
				@click="item.fullNav ? fullNavigate(item.route) : undefined"
			>
				<!-- Active Indicator -->
				<div 
					v-if="route.path === item.route"
					class="absolute left-0 top-1/4 bottom-1/4 w-1 bg-gray-900 rounded-r-full"
				></div>
				
				<component :is="item.icon" class="h-5 w-5 shrink-0 transition-transform group-hover:scale-110" />
				<span class="text-sm font-semibold whitespace-nowrap">{{ item.title }}</span>
			</component>
		</nav>

		<!-- Bottom Identity / Org context -->
		<div class="mt-auto px-2 py-4 border-t border-gray-100 bg-white/50 rounded-2xl p-2 mb-4">
			<div class="flex items-center gap-3">
				<div class="w-10 h-10 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center border border-white shadow-sm shrink-0">
					<span class="text-xs font-bold text-gray-400 capitalize">{{ user.data.first_name?.[0] }}</span>
				</div>
				<div class="flex flex-col min-w-0">
					<span class="text-xs font-bold text-gray-900 truncate">{{ user.data.full_name }}</span>
					<span class="text-[10px] text-gray-500 truncate">{{ user.data.email }}</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { inject } from "vue"
import { useRoute } from "vue-router"

import HomeIcon from "@/components/icons/HomeIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import DirectoryIcon from "@/components/icons/DirectoryIcon.vue"
import ActionCentreIcon from "@/components/icons/ActionCentreIcon.vue"

const __ = inject("$translate")
const user = inject("$user")
const route = useRoute()

// Full browser navigation for routes that don't participate in Ionic's tab stack correctly
function fullNavigate(path) {
	window.location.href = "/hrms" + path
}

const navItems = [
	{
		icon: HomeIcon,
		title: __("Overview"),
		route: "/home",
		fullNav: false,
	},
	{
		icon: ActionCentreIcon,
		title: __("Action Centre"),
		route: "/action-centre",
		fullNav: true,
	},
	{
		icon: AttendanceIcon,
		title: __("Attendance"),
		route: "/dashboard/attendance",
		fullNav: false,
	},
	{
		icon: LeaveIcon,
		title: __("Leaves"),
		route: "/dashboard/leaves",
		fullNav: false,
	},
	{
		icon: ExpenseIcon,
		title: __("Expenses"),
		route: "/dashboard/expense-claims",
		fullNav: false,
	},
	{
		icon: DirectoryIcon,
		title: __("Employee Directory"),
		route: "/directory",
		fullNav: true,
	},
]
</script>
