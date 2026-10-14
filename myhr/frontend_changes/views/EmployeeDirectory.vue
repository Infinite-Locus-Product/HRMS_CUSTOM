<template>
	<ion-page>
		<ion-content class="ion-no-padding bg-[#FBFBFC]" style="--background: #FBFBFC;">
			<div class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative pb-[120px]">
				<!-- Sticky glassmorphism header — matches Action Centre -->
				<div class="flex flex-col bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100 transition-all duration-300">
					<div class="flex flex-row justify-between items-center gap-4">
						<div class="flex flex-row items-center gap-1 flex-1 min-w-0">
							<Button
								variant="ghost"
								class="!px-2 hover:bg-gray-100 transition-colors"
								@click="goBack()"
							>
								<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
							</Button>
							<div class="flex flex-col ml-1 overflow-hidden">
								<h2 class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1">
									{{ __("Employee Directory") }}
								</h2>
								<div class="flex items-center gap-1.5 opacity-60">
									<div class="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
									<span class="text-[10px] font-bold uppercase tracking-widest">
										{{ employees.length }} {{ employees.length === 1 ? __("MEMBER") : __("MEMBERS") }}
									</span>
								</div>
							</div>
						</div>

						<div class="flex flex-row items-center gap-2">
							<router-link
								:to="{ name: 'Notifications' }"
								class="p-2 hover:bg-gray-100 rounded-full transition-all relative"
							>
								<FeatherIcon name="bell" class="h-5 w-5 text-gray-600" />
								<span
									v-if="unreadNotificationsCount.data"
									class="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white animate-pulse"
								></span>
							</router-link>
							<router-link
								:to="{ name: 'Profile' }"
								class="ml-1 cursor-pointer hover:ring-2 hover:ring-gray-100 rounded-full transition-all"
							>
								<Avatar :image="user.data.user_image" :label="user.data.first_name" size="lg" />
							</router-link>
						</div>
					</div>
				</div>

				<!-- Content -->
				<div class="flex-1 px-4 py-4 sm:p-5 space-y-5">
					<!-- Search bar — large, rounded, with leading icon and clear affordance -->
					<div class="relative">
						<FeatherIcon
							name="search"
							class="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 pointer-events-none"
						/>
						<input
							v-model="searchQuery"
							type="text"
							:placeholder="__('Search by name, role, dept, phone, email…')"
							class="w-full h-12 pl-12 pr-12 rounded-2xl border border-gray-100 bg-white text-sm font-medium text-gray-900 placeholder:text-gray-400 focus:outline-none focus:bg-white focus:border-blue-300 focus:ring-4 focus:ring-blue-50 shadow-sm transition-all"
						/>
						<button
							v-if="searchQuery"
							type="button"
							class="absolute right-3 top-1/2 -translate-y-1/2 h-7 w-7 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-all"
							:aria-label="__('Clear search')"
							@click="searchQuery = ''"
						>
							<FeatherIcon name="x" class="h-3.5 w-3.5 text-gray-600" />
						</button>
					</div>

					<!-- Department filter chips — single-select; "All" resets. Hidden if 0/1 distinct department. -->
					<div
						v-if="distinctDepartments.length > 1"
						class="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 scrollbar-hide"
					>
						<button
							type="button"
							class="shrink-0 h-9 px-3.5 rounded-xl border whitespace-nowrap transition-all flex items-center gap-1.5 active:scale-95"
							:class="selectedDepartment === null
								? 'bg-gray-900 text-white border-gray-900 shadow-sm'
								: 'bg-white text-gray-700 border-gray-100 hover:border-gray-300'"
							@click="selectedDepartment = null"
						>
							<span class="text-[10px] font-black uppercase tracking-widest">{{ __("All") }}</span>
							<span
								class="text-[10px] font-black tabular-nums px-1.5 py-0.5 rounded-md"
								:class="selectedDepartment === null ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-500'"
							>{{ employees.length }}</span>
						</button>
						<button
							v-for="dept in distinctDepartments"
							:key="dept"
							type="button"
							class="shrink-0 h-9 px-3.5 rounded-xl border whitespace-nowrap transition-all flex items-center gap-1.5 active:scale-95"
							:class="selectedDepartment === dept
								? 'bg-blue-50 text-blue-700 border-blue-200 shadow-sm'
								: 'bg-white text-gray-700 border-gray-100 hover:border-gray-300'"
							@click="selectedDepartment = (selectedDepartment === dept ? null : dept)"
						>
							<span class="text-[10px] font-black uppercase tracking-widest">{{ dept }}</span>
							<span
								class="text-[10px] font-black tabular-nums px-1.5 py-0.5 rounded-md"
								:class="selectedDepartment === dept ? 'bg-white/70 text-blue-700' : 'bg-gray-100 text-gray-500'"
							>{{ departmentCounts[dept] || 0 }}</span>
						</button>
					</div>

					<!-- Result count strip — shown only when filters are active -->
					<div
						v-if="(searchQuery || selectedDepartment) && filteredEmployees.length"
						class="flex items-center justify-between"
					>
						<span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
							{{ filteredEmployees.length }}
							{{ filteredEmployees.length === 1 ? __("RESULT") : __("RESULTS") }}
						</span>
						<button
							type="button"
							class="text-[10px] font-black text-blue-600 hover:text-blue-700 uppercase tracking-widest"
							@click="searchQuery = ''; selectedDepartment = null"
						>
							{{ __("Clear filters") }}
						</button>
					</div>

					<!-- Directory cards -->
					<div v-if="filteredEmployees.length" class="grid grid-cols-1 gap-3">
						<div
							v-for="emp in filteredEmployees"
							:key="emp.employee_id"
							class="group bg-white rounded-2xl border border-gray-100 overflow-hidden transition-all duration-300"
							:class="isExpanded(emp.employee_id) ? 'shadow-lg border-blue-100' : 'hover:shadow-md hover:border-gray-200'"
						>
							<button
								type="button"
								class="flex w-full items-center gap-3 p-4 text-left hover:bg-gray-50/60 transition-colors"
								@click="toggleExpand(emp.employee_id)"
							>
								<!-- Initials avatar with deterministic accent ring -->
								<div
									class="h-12 w-12 rounded-2xl flex items-center justify-center shrink-0 shadow-sm border"
									:class="avatarPalette(emp.employee_name).classes"
								>
									<img
										v-if="emp.image"
										:src="emp.image"
										:alt="emp.employee_name"
										class="h-full w-full rounded-2xl object-cover"
									/>
									<span
										v-else
										class="text-base font-black tracking-tight"
									>{{ initials(emp.employee_name) }}</span>
								</div>

								<div class="flex-1 min-w-0">
									<div class="text-sm font-bold text-gray-900 truncate leading-tight">
										{{ emp.employee_name }}
									</div>
									<div
										v-if="emp.designation"
										class="text-xs font-medium text-gray-500 truncate mt-0.5"
									>
										{{ emp.designation }}
									</div>
									<div
										v-if="emp.department"
										class="mt-1.5 inline-flex items-center gap-1 max-w-full"
									>
										<span class="text-[9px] font-black uppercase tracking-widest text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-100 truncate">
											{{ emp.department }}
										</span>
									</div>
								</div>

								<FeatherIcon
									:name="isExpanded(emp.employee_id) ? 'chevron-up' : 'chevron-down'"
									class="h-5 w-5 text-gray-400 shrink-0 transition-transform"
								/>
							</button>

							<div
								v-show="isExpanded(emp.employee_id)"
								class="px-4 pb-4 pt-0 border-t border-gray-100 bg-gray-50/40 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200"
							>
								<!-- Identity grid: Employee ID + Department, only render rows that have data -->
								<div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3">
									<div v-if="emp.employee_id" class="flex flex-col gap-0.5">
										<span class="text-[9px] font-black text-gray-400 uppercase tracking-widest">
											{{ __("Employee ID") }}
										</span>
										<span class="text-xs font-bold text-gray-800 break-all">
											{{ emp.employee_id }}
										</span>
									</div>
									<div v-if="emp.department" class="flex flex-col gap-0.5">
										<span class="text-[9px] font-black text-gray-400 uppercase tracking-widest">
											{{ __("Department") }}
										</span>
										<span class="text-xs font-bold text-gray-800">
											{{ emp.department }}
										</span>
									</div>
								</div>

								<!-- Contact actions — phone + email render as primary CTAs -->
								<div
									v-if="emp.mobile_number || emp.employee_email"
									class="flex flex-col gap-2"
								>
									<a
										v-if="emp.mobile_number"
										:href="'tel:' + emp.mobile_number"
										class="flex items-center gap-3 px-3 h-11 rounded-xl bg-white border border-gray-100 hover:border-blue-200 hover:bg-blue-50/30 transition-all active:scale-[.98] shadow-sm"
										@click.stop
									>
										<div class="p-1.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-100 shrink-0">
											<FeatherIcon name="phone" class="h-3.5 w-3.5" />
										</div>
										<div class="flex flex-col flex-1 min-w-0">
											<span class="text-[9px] font-black uppercase tracking-widest text-gray-400">{{ __("Mobile") }}</span>
											<span class="text-xs font-bold text-gray-900 truncate">{{ emp.mobile_number }}</span>
										</div>
										<FeatherIcon name="phone-call" class="h-4 w-4 text-gray-400 shrink-0" />
									</a>
									<a
										v-if="emp.employee_email"
										:href="'mailto:' + emp.employee_email"
										class="flex items-center gap-3 px-3 h-11 rounded-xl bg-white border border-gray-100 hover:border-blue-200 hover:bg-blue-50/30 transition-all active:scale-[.98] shadow-sm"
										@click.stop
									>
										<div class="p-1.5 rounded-lg bg-blue-50 text-blue-600 border border-blue-100 shrink-0">
											<FeatherIcon name="mail" class="h-3.5 w-3.5" />
										</div>
										<div class="flex flex-col flex-1 min-w-0">
											<span class="text-[9px] font-black uppercase tracking-widest text-gray-400">{{ __("Email") }}</span>
											<span class="text-xs font-bold text-gray-900 truncate break-all">{{ emp.employee_email }}</span>
										</div>
										<FeatherIcon name="external-link" class="h-4 w-4 text-gray-400 shrink-0" />
									</a>
								</div>

								<!-- Soft empty-contact note when neither phone nor email is on file -->
								<div
									v-if="!emp.mobile_number && !emp.employee_email"
									class="flex items-center gap-2 px-3 py-2 rounded-xl bg-gray-50 border border-gray-100"
								>
									<FeatherIcon name="info" class="h-3.5 w-3.5 text-gray-400 shrink-0" />
									<span class="text-[11px] font-medium text-gray-500">
										{{ __("No contact details on file") }}
									</span>
								</div>
							</div>
						</div>
					</div>

					<!-- Empty state — search vs default -->
					<div
						v-else-if="!loading"
						class="flex flex-col items-center justify-center py-20 bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200"
					>
						<div class="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center mb-4">
							<FeatherIcon
								:name="searchQuery || selectedDepartment ? 'search' : 'users'"
								class="h-8 w-8 text-gray-400"
							/>
						</div>
						<p class="text-gray-900 font-bold text-base mb-1">
							{{ searchQuery || selectedDepartment ? __("No matching colleagues") : __("Directory is empty") }}
						</p>
						<p v-if="searchQuery || selectedDepartment" class="text-gray-500 text-xs mb-5">
							{{ __("Try a different name, role or department.") }}
						</p>
						<Button
							v-if="searchQuery || selectedDepartment"
							variant="outline"
							@click="searchQuery = ''; selectedDepartment = null"
						>
							{{ __("Clear filters") }}
						</Button>
					</div>

					<!-- Loading state -->
					<div v-if="loading" class="flex flex-col items-center justify-center py-32 space-y-4">
						<LoadingIndicator class="h-8 w-8 text-blue-600" />
						<p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
							{{ __("Loading Directory") }}
						</p>
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { ref, computed, inject } from "vue"
import { FeatherIcon, Avatar, Button, LoadingIndicator, createResource } from "frappe-ui"
import { useIonRouter, onIonViewWillEnter } from "@ionic/vue"
import { unreadNotificationsCount } from "@/data/notifications"
import { showErrorFromException } from "@/data/errorModal"

const ionRouter = useIonRouter()
const user = inject("$user")
const __ = inject("$translate")

function goBack() {
	// Fall back to Home if there's no real history (PWA deep link / SW cached entry).
	if (window.history.length > 2) {
		window.history.back()
	} else {
		ionRouter.push({ name: "Home" })
	}
}

const employees = ref([])
const searchQuery = ref("")
const selectedDepartment = ref(null)
const loading = ref(true)

const expandedIds = ref(new Set())

function isExpanded(employeeId) {
	return expandedIds.value.has(employeeId)
}

function toggleExpand(employeeId) {
	const next = new Set(expandedIds.value)
	if (next.has(employeeId)) {
		next.delete(employeeId)
	} else {
		next.add(employeeId)
	}
	expandedIds.value = next
}

/** Two-letter initials from "Firstname Lastname" → "FL"; falls back to "?". */
function initials(name) {
	if (!name) return "?"
	const parts = String(name).trim().split(/\s+/).filter(Boolean)
	if (!parts.length) return "?"
	if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
	return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

// Six pastel palettes — picked deterministically from the name so the same
// person always renders the same accent. Stays inside the AC-style colour
// vocabulary (blue / amber / green / red / purple / teal) so the directory
// reads as part of the same design system.
const _AVATAR_PALETTES = [
	{ classes: "bg-blue-50 text-blue-700 border-blue-100" },
	{ classes: "bg-amber-50 text-amber-700 border-amber-100" },
	{ classes: "bg-green-50 text-green-700 border-green-100" },
	{ classes: "bg-rose-50 text-rose-700 border-rose-100" },
	{ classes: "bg-violet-50 text-violet-700 border-violet-100" },
	{ classes: "bg-teal-50 text-teal-700 border-teal-100" },
]
function avatarPalette(name) {
	const key = String(name || "").trim()
	if (!key) return _AVATAR_PALETTES[0]
	let h = 0
	for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0
	return _AVATAR_PALETTES[h % _AVATAR_PALETTES.length]
}

const dirResource = createResource({
	url: "myhr.api.get_employee_directory",
	auto: true,
	onSuccess: (data) => {
		employees.value = data || []
		loading.value = false
	},
	onError: (err) => {
		console.error("Directory fetch failed:", err)
		loading.value = false
		showErrorFromException(err, __("Could not load directory"))
	}
})

// Refresh on re-entry so newly-added / departed colleagues appear without a manual refresh.
onIonViewWillEnter(() => {
	dirResource.reload()
})

/** Distinct, alphabetised list of departments — populates the filter chips. */
const distinctDepartments = computed(() => {
	const set = new Set()
	for (const e of employees.value) {
		if (e.department) set.add(e.department)
	}
	return Array.from(set).sort()
})

/** Per-department head-count for the chip labels — computed once per data load. */
const departmentCounts = computed(() => {
	const counts = {}
	for (const e of employees.value) {
		if (!e.department) continue
		counts[e.department] = (counts[e.department] || 0) + 1
	}
	return counts
})

/** Combines department chip + free-text search. Search corpus extended to phone + email. */
const filteredEmployees = computed(() => {
	let list = employees.value
	if (selectedDepartment.value) {
		list = list.filter((e) => e.department === selectedDepartment.value)
	}
	if (!searchQuery.value) return list
	const q = searchQuery.value.toLowerCase().trim()
	return list.filter(
		(e) =>
			(e.employee_name && e.employee_name.toLowerCase().includes(q)) ||
			(e.designation && e.designation.toLowerCase().includes(q)) ||
			(e.department && e.department.toLowerCase().includes(q)) ||
			(e.employee_id && e.employee_id.toLowerCase().includes(q)) ||
			(e.mobile_number && String(e.mobile_number).toLowerCase().includes(q)) ||
			(e.employee_email && e.employee_email.toLowerCase().includes(q))
	)
})
</script>
