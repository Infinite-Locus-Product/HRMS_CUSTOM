<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<div class="bg-[#FBFBFC] min-h-screen pb-8">
				<div
					class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative"
				>
					<!-- Glassy sticky header -->
					<div
						class="flex flex-row bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100 items-center gap-1"
					>
						<Button
							variant="ghost"
							class="!px-2 hover:bg-gray-100 transition-colors"
							@click="router.back()"
						>
							<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
						</Button>
						<div class="flex flex-col ml-1 overflow-hidden">
							<h2
								class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1"
							>
								{{ __("Profile") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span
									class="text-[10px] font-bold uppercase tracking-widest"
									>{{ __("Your account") }}</span
								>
							</div>
						</div>
					</div>

					<!-- Body -->
					<div class="flex-1 px-4 py-5 sm:p-5 space-y-5">
						<!-- Hero card -->
						<div class="rounded-2xl bg-blue-600 p-5 text-white shadow-sm">
							<div class="flex flex-row items-center gap-4">
								<div
									v-if="user.data.user_image"
									class="h-16 w-16 rounded-full overflow-hidden border-2 border-white/30 shrink-0"
								>
									<img
										:src="user.data.user_image"
										:alt="user.data.first_name"
										class="h-full w-full object-cover"
									/>
								</div>
								<div
									v-else
									class="h-16 w-16 rounded-full bg-white/15 text-white font-black text-xl flex items-center justify-center border-2 border-white/30 shrink-0"
								>
									{{ initials }}
								</div>
								<div class="flex flex-col min-w-0 flex-1">
									<div
										class="text-[10px] font-black uppercase tracking-widest text-white/80"
									>
										{{ employee?.data?.name || __("Employee") }}
									</div>
									<div
										class="text-xl font-black truncate mt-0.5"
									>
										{{ employee?.data?.employee_name || user.data.first_name }}
									</div>
									<div
										v-if="employee?.data?.designation"
										class="text-xs font-bold text-white/80 mt-0.5 truncate"
									>
										{{ employee.data.designation }}
									</div>
								</div>
							</div>
							<div
								v-if="
									employee?.data?.department ||
									employee?.data?.company
								"
								class="mt-4 grid grid-cols-2 gap-2"
							>
								<div
									v-if="employee?.data?.department"
									class="rounded-xl bg-white/15 px-3 py-2"
								>
									<div
										class="text-[9px] font-black uppercase tracking-widest text-white/80"
									>
										{{ __("Department") }}
									</div>
									<div class="text-sm font-extrabold mt-0.5 truncate">
										{{ employee.data.department }}
									</div>
								</div>
								<div
									v-if="employee?.data?.date_of_joining"
									class="rounded-xl bg-white/15 px-3 py-2"
								>
									<div
										class="text-[9px] font-black uppercase tracking-widest text-white/80"
									>
										{{ __("Joined") }}
									</div>
									<div class="text-sm font-extrabold mt-0.5 truncate">
										{{ formatJoinDate(employee.data.date_of_joining) }}
									</div>
								</div>
							</div>
						</div>

						<!-- Profile sections -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
								>
									<FeatherIcon name="user" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Account Details") }}
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Tap any section to view") }}
									</span>
								</div>
							</div>

							<div
								class="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden divide-y divide-gray-100"
							>
								<button
									v-for="link in profileLinks"
									:key="link.title"
									type="button"
									@click="openInfoModal(link)"
									class="w-full flex flex-row p-4 items-center justify-between hover:bg-blue-50/60 active:bg-blue-100/60 cursor-pointer transition-colors text-left"
								>
									<div class="flex flex-row items-center gap-3 grow min-w-0">
										<div
											class="p-2 rounded-xl border shrink-0"
											:class="link.tileClass"
										>
											<FeatherIcon
												:name="link.icon"
												class="h-4 w-4"
												:class="link.iconColor"
											/>
										</div>
										<div class="text-[15px] font-extrabold text-gray-900 truncate">
											{{ link.title }}
										</div>
									</div>
									<FeatherIcon
										name="chevron-right"
										class="h-4 w-4 text-gray-300 shrink-0"
									/>
								</button>
							</div>
						</section>

						<!-- Resignation -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-gray-50 text-gray-600 shadow-sm border border-gray-200"
								>
									<FeatherIcon name="log-out" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Separation") }}
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Initiate or track your resignation") }}
									</span>
								</div>
							</div>
							<router-link
								:to="{ name: 'Resignation' }"
								class="flex flex-row p-4 items-center justify-between rounded-2xl bg-white border border-gray-100 shadow-sm hover:bg-blue-50/60 active:bg-blue-100/60 transition-colors"
							>
								<div class="flex flex-row items-center gap-3 grow min-w-0">
									<div
										class="p-2 rounded-xl border bg-amber-50 border-amber-200 shrink-0"
									>
										<FeatherIcon name="log-out" class="h-4 w-4 text-amber-600" />
									</div>
									<div class="text-[15px] font-extrabold text-gray-900">
										{{ __("Resignation") }}
									</div>
								</div>
								<FeatherIcon
									name="chevron-right"
									class="h-4 w-4 text-gray-300 shrink-0"
								/>
							</router-link>
						</section>

						<!-- Settings section -->
						<section v-if="allowPushNotifications" class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-gray-50 text-gray-600 shadow-sm border border-gray-200"
								>
									<FeatherIcon name="settings" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Preferences") }}
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("App settings and notifications") }}
									</span>
								</div>
							</div>
							<router-link
								:to="{ name: 'Settings' }"
								class="flex flex-row p-4 items-center justify-between rounded-2xl bg-white border border-gray-100 shadow-sm hover:bg-blue-50/60 active:bg-blue-100/60 transition-colors"
							>
								<div class="flex flex-row items-center gap-3 grow min-w-0">
									<div
										class="p-2 rounded-xl border bg-gray-50 border-gray-200 shrink-0"
									>
										<FeatherIcon
											name="settings"
											class="h-4 w-4 text-gray-500"
										/>
									</div>
									<div class="text-[15px] font-extrabold text-gray-900">
										{{ __("Settings") }}
									</div>
								</div>
								<FeatherIcon
									name="chevron-right"
									class="h-4 w-4 text-gray-300 shrink-0"
								/>
							</router-link>
						</section>

						<!-- Log out -->
						<button
							type="button"
							@click="logout"
							class="w-full py-4 rounded-2xl bg-white border-2 border-red-200 text-red-700 font-black text-xs uppercase tracking-widest hover:bg-red-50 active:scale-[0.98] transition-all flex items-center justify-center gap-2 mt-2"
						>
							<FeatherIcon name="log-out" class="h-4 w-4" />
							{{ __("Log Out") }}
						</button>
					</div>
				</div>
			</div>

			<ion-modal
				ref="modal"
				:is-open="isInfoModalOpen"
				@didDismiss="closeInfoModal"
				:initial-breakpoint="1"
				:breakpoints="[0, 1]"
			>
				<ProfileInfoModal
					v-if="selectedItem"
					:title="selectedItem.title"
					:data="
						(selectedItem.fields || []).map((field) => {
							const [label, fieldtype] = getFieldInfo(field)
							return {
								fieldname: field,
								value: employeeDoc.doc?.[field],
								label: label,
								fieldtype: fieldtype,
							}
						})
					"
				/>
			</ion-modal>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { computed, inject, ref, onMounted, onBeforeUnmount } from "vue"
import { useRouter } from "vue-router"
import { IonModal, IonPage, IonContent } from "@ionic/vue"
import { FeatherIcon, Button, createDocumentResource, createResource } from "frappe-ui"

import { showErrorFromException } from "@/data/errorModal"
import { formatCurrency } from "@/utils/formatters"

import ProfileInfoModal from "@/components/ProfileInfoModal.vue"

import { arePushNotificationsEnabled } from "@/data/notifications"

const DOCTYPE = "Employee"

const socket = inject("$socket")
const session = inject("$session")
const user = inject("$user")
const employee = inject("$employee")
const dayjs = inject("$dayjs")
const __ = inject("$translate")

const router = useRouter()

const profileLinks = [
	{
		icon: "user",
		title: __("Employee Details"),
		tileClass: "bg-blue-50 border-blue-100",
		iconColor: "text-blue-600",
		fields: [
			"employee_name",
			"employee_number",
			"gender",
			"date_of_birth",
			"date_of_joining",
			"blood_group",
		],
	},
	{
		icon: "briefcase",
		title: __("Company Information"),
		tileClass: "bg-purple-50 border-purple-100",
		iconColor: "text-purple-600",
		fields: [
			"company",
			"department",
			"designation",
			"branch",
			"grade",
			"reports_to",
			"employment_type",
		],
	},
	{
		icon: "phone",
		title: __("Contact Information"),
		tileClass: "bg-green-50 border-green-100",
		iconColor: "text-green-600",
		fields: [
			"cell_number",
			"personal_email",
			"company_email",
			"preferred_email",
		],
	},
	{
		icon: "credit-card",
		title: __("Salary Information"),
		tileClass: "bg-amber-50 border-amber-100",
		iconColor: "text-amber-600",
		fields: [
			"ctc",
			"payroll_cost_center",
			"pan_number",
			"provident_fund_account",
			"salary_mode",
			"bank_name",
			"bank_ac_no",
			"ifsc_code",
			"micr_code",
			"iban",
		],
	},
]

const isInfoModalOpen = ref(false)
const selectedItem = ref(null)

const allowPushNotifications = computed(
	() =>
		window.frappe?.boot.push_relay_server_url &&
		arePushNotificationsEnabled.data
)

const initials = computed(() => {
	const name =
		employee?.data?.employee_name || user.data.first_name || ""
	return name
		.split(" ")
		.filter(Boolean)
		.map((s) => s[0])
		.slice(0, 2)
		.join("")
		.toUpperCase()
})

const openInfoModal = async (request) => {
	selectedItem.value = request
	isInfoModalOpen.value = true
}

const closeInfoModal = async (_request) => {
	isInfoModalOpen.value = false
	selectedItem.value = null
}

// Don't mutate the raw doc — re-running transform on reload would re-format
// the already-formatted ctc string. Keep a separate computed for display.
const employeeDoc = createDocumentResource({
	doctype: DOCTYPE,
	name: employee.data.name,
	fields: "*",
	auto: true,
	transform: (data) => {
		if (data && data.ctc != null && typeof data.ctc === "number") {
			data.ctc = formatCurrency(data.ctc, data.salary_currency)
		}
		return data
	},
})

const employeeDocType = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: DOCTYPE },
	auto: true,
})

const getFieldInfo = (fieldname) => {
	const field = (employeeDocType.data || []).find(
		(field) => field.fieldname === fieldname
	)
	return [__(field?.label, null, "Employee"), field?.fieldtype]
}

function formatJoinDate(d) {
	if (!d) return ""
	return dayjs(d).format("MMM YYYY")
}

const logout = async () => {
	try {
		await session.logout.submit()
	} catch (e) {
		console.error("Logout failed:", e)
		showErrorFromException(e, __("An error occurred while attempting to log out!"))
	}
}

onMounted(() => {
	socket.emit("doctype_subscribe", DOCTYPE)
	socket.on("list_update", (data) => {
		if (data.doctype === DOCTYPE && data.name === employee.data.name) {
			employeeDoc.reload()
		}
	})
})

onBeforeUnmount(() => {
	socket.emit("doctype_unsubscribe", DOCTYPE)
	socket.off("list_update")
})
</script>
