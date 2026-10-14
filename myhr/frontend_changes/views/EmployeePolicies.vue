<template>
	<ion-page>
		<ion-content class="ion-no-padding bg-[#FBFBFC]" style="--background: #FBFBFC;">
			<div class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative pb-[40px]">

				<!-- Sticky Header -->
				<div class="flex flex-col bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100">
					<div class="flex flex-row justify-between items-center gap-4">
						<div class="flex flex-row items-center gap-1 flex-1">
							<Button variant="ghost" class="!px-2 hover:bg-gray-100 transition-colors" @click="goBack()">
								<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
							</Button>
							<div class="flex flex-col ml-1 overflow-hidden">
								<h2 class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1">{{ __("Policy Centre") }}</h2>
								<div v-if="policies" class="flex items-center gap-1.5 opacity-60">
									<div class="w-1.5 h-1.5 rounded-full" :class="pendingCount === 0 ? 'bg-green-500' : 'bg-orange-500'"></div>
									<span class="text-[10px] font-bold uppercase tracking-widest">
										{{ pendingCount === 0 ? __("All caught up") : __("{0} pending", [pendingCount]) }}
									</span>
								</div>
							</div>
						</div>
						<router-link :to="{ name: 'Profile' }" class="ml-1 cursor-pointer hover:ring-2 hover:ring-gray-100 rounded-full transition-all">
							<Avatar :image="user.data.user_image" :label="user.data.first_name" size="lg" />
						</router-link>
					</div>
				</div>

				<!-- Content -->
				<div class="flex-1 px-4 py-4 sm:p-5 space-y-4">

					<!-- Loading -->
					<div v-if="loading" class="flex flex-col items-center justify-center py-32 space-y-4">
						<LoadingIndicator class="h-8 w-8 text-blue-600" />
						<p class="text-xs font-bold text-gray-400 uppercase tracking-widest">{{ __("Loading policies") }}</p>
					</div>

					<!-- Error -->
					<div v-else-if="errorMsg" class="flex flex-col items-center justify-center py-20 bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200">
						<FeatherIcon name="alert-circle" class="h-8 w-8 text-red-500 mb-3" />
						<p class="text-gray-900 font-bold text-lg mb-1">{{ __("Could not load policies") }}</p>
						<p class="text-gray-500 text-sm mb-6">{{ errorMsg }}</p>
						<Button variant="outline" @click="policiesResource.reload()">{{ __("Retry") }}</Button>
					</div>

					<!-- Empty -->
					<div v-else-if="!policies?.length" class="flex flex-col items-center justify-center py-20 bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200">
						<div class="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center mb-4">
							<FeatherIcon name="shield-check" class="h-8 w-8 text-green-500" />
						</div>
						<p class="text-gray-900 font-bold text-lg mb-1">{{ __("No policies assigned") }}</p>
						<p class="text-gray-500 text-sm">{{ __("HR will let you know when something needs your attention.") }}</p>
					</div>

					<!-- Banner if blocking policies pending -->
					<div v-else-if="blockingCount > 0" class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 flex items-start gap-3">
						<FeatherIcon name="alert-triangle" class="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
						<div class="flex-1 min-w-0">
							<div class="text-sm font-extrabold text-red-900">{{ __("Action required to check in") }}</div>
							<div class="text-xs text-red-800 mt-0.5">{{ __("You can't record attendance until you acknowledge the policies marked Required for Check-in below.") }}</div>
						</div>
					</div>

					<!-- Policy list -->
					<div v-if="policies?.length" class="space-y-3">
						<div v-for="policy in policies" :key="policy.name"
							class="bg-white p-4 rounded-2xl border shadow-sm transition-all"
							:class="policy.status === 'Acknowledged' ? 'border-green-100 bg-green-50/5' : 'border-gray-100 hover:border-orange-200'"
						>
							<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
								<div class="flex items-start gap-3 flex-1 min-w-0">
									<div class="p-2.5 rounded-xl shrink-0"
										:class="policy.status === 'Acknowledged' ? 'bg-green-100 text-green-700' : 'bg-orange-50 text-orange-600'"
									>
										<FeatherIcon :name="policy.status === 'Acknowledged' ? 'award' : 'shield'" class="h-5 w-5" />
									</div>
									<div class="flex flex-col min-w-0 flex-1">
										<div class="flex items-center gap-2 flex-wrap mb-1">
											<span class="text-[15px] font-extrabold text-gray-900 leading-tight">{{ policy.policy_name }}</span>
											<span v-if="policy.mandatory_check_in_block" class="text-[9px] font-black uppercase tracking-widest text-red-700 bg-red-50 px-2 py-0.5 rounded-md border border-red-200">{{ __("Required for Check-in") }}</span>
										</div>
										<div class="flex items-center gap-2 flex-wrap">
											<span class="text-[9px] font-black uppercase tracking-widest text-gray-500 bg-gray-50 px-2 py-0.5 rounded-md border border-gray-100">{{ policy.category }}</span>
											<span v-if="policy.status === 'Pending'" class="text-[9px] font-black uppercase tracking-widest text-orange-700 bg-orange-50 px-2 py-0.5 rounded-md border border-orange-200">{{ __("PENDING") }}</span>
											<span v-if="policy.status === 'Acknowledged'" class="text-[9px] font-black uppercase tracking-widest text-green-700 bg-green-50 px-2 py-0.5 rounded-md border border-green-200">{{ __("ACKNOWLEDGED") }}</span>
											<span v-if="policy.policy_version > 1" class="text-[9px] font-black uppercase tracking-widest text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-100">{{ __("v{0}", [policy.policy_version]) }}</span>
										</div>
										<p v-if="policy.description" class="text-xs text-gray-600 mt-2 leading-relaxed">{{ policy.description }}</p>
										<p v-if="policy.acknowledged_at && policy.status === 'Acknowledged'" class="text-[10px] text-gray-400 mt-2">{{ __("Signed") }}: {{ policy.acknowledged_at }}</p>
									</div>
								</div>

								<div class="flex flex-col gap-2 w-full lg:w-auto lg:flex-row lg:items-center">
									<button v-if="policy.file"
										type="button"
										@click="openPreview(policy.file, policy.policy_name || __('Policy'))"
										class="px-4 h-9 rounded-xl bg-gray-50 text-gray-900 border border-gray-300 hover:bg-gray-100 transition-all shadow-sm flex items-center justify-center gap-2 w-full lg:w-auto"
									>
										<FeatherIcon name="eye" class="h-3.5 w-3.5" />
										<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View Policy") }}</span>
									</button>
									<button v-if="policy.status === 'Pending'"
										type="button"
										class="bg-green-50 text-green-800 hover:bg-green-100 border border-green-300 h-9 px-4 rounded-xl text-[9px] font-black uppercase tracking-widest active:scale-95 shadow-sm flex items-center justify-center gap-2 w-full lg:w-auto disabled:opacity-50"
										:disabled="acknowledgingName === policy.name"
										@click="acknowledge(policy)"
									>
										<LoadingIndicator v-if="acknowledgingName === policy.name" class="h-3.5 w-3.5 text-green-700" />
										<FeatherIcon v-else name="check" class="h-3.5 w-3.5" />
										<span>{{ acknowledgingName === policy.name ? __("Saving...") : __("Acknowledge") }}</span>
									</button>
									<button v-if="policy.policy_version > 1"
										type="button"
										class="bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200 h-9 px-3 rounded-xl text-[9px] font-black uppercase tracking-widest flex items-center justify-center gap-2 w-full lg:w-auto"
										@click="loadHistory(policy)"
									>
										<FeatherIcon name="clock" class="h-3.5 w-3.5" />
										<span>{{ __("History") }}</span>
									</button>
								</div>
							</div>

							<!-- Inline history -->
							<div v-if="historyByPolicy[policy.hr_policy]?.length" class="mt-3 pt-3 border-t border-gray-100 space-y-1.5">
								<div class="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-1">{{ __("Previous versions you acknowledged") }}</div>
								<div v-for="h in historyByPolicy[policy.hr_policy]" :key="h.name" class="text-xs text-gray-600 flex items-center gap-2">
									<FeatherIcon name="check-circle" class="h-3 w-3 text-gray-400" />
									<span>v{{ h.policy_version }} — {{ h.acknowledged_at || __("not acknowledged") }}</span>
								</div>
							</div>
						</div>
					</div>

				</div>
			</div>

			<!-- Document Preview Modal (mobile-safe: PDF.js + image inline + external-link fallback) -->
			<DocumentPreviewModal
				:url="previewUrl"
				:title="previewTitle"
				@close="closePreview"
			/>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { ref, computed, inject } from "vue"
import { FeatherIcon, Avatar, LoadingIndicator, createResource, Button, toast } from "frappe-ui"
import { IonPage, IonContent, useIonRouter, onIonViewWillEnter } from "@ionic/vue"
import { showErrorFromException } from "@/data/errorModal"
import DocumentPreviewModal from "@/components/DocumentPreviewModal.vue"

const ionRouter = useIonRouter()
const user = inject("$user")
const __ = inject("$translate")

const policies = ref(null)
const loading = ref(true)
const errorMsg = ref("")
const acknowledgingName = ref(null)
const historyByPolicy = ref({})

// In-app document preview (replaces target="_blank" so iOS doesn't strip the chrome)
const previewUrl = ref(null)
const previewTitle = ref("")
function openPreview(url, title) {
	if (!url) return
	previewUrl.value = url
	previewTitle.value = title || __("Policy")
}
function closePreview() {
	previewUrl.value = null
	previewTitle.value = ""
}

function goBack() {
	// Fall back to Home if there's no real history (PWA deep link / SW cached entry).
	if (window.history.length > 2) {
		window.history.back()
	} else {
		ionRouter.push({ name: "Home" })
	}
}

const policiesResource = createResource({
	url: "myhr.api.get_employee_policies",
	auto: true,
	onSuccess: (data) => {
		loading.value = false
		if (data?.error) {
			errorMsg.value = data.message || data.error
			policies.value = []
			return
		}
		errorMsg.value = ""
		policies.value = data?.policies || []
	},
	onError: (err) => {
		loading.value = false
		errorMsg.value = err?.message || String(err)
	},
})

const ackResource = createResource({ url: "myhr.api.acknowledge_policy_acknowledgement" })
const historyResource = createResource({ url: "myhr.api.get_employee_policy_history" })

// Refresh whenever the user navigates back to this page so newly-assigned policies
// (e.g., HR just published a new one) appear without a manual refresh.
onIonViewWillEnter(() => {
	policiesResource.reload()
})

const pendingCount = computed(() => (policies.value || []).filter(p => p.status === "Pending").length)
const blockingCount = computed(() => (policies.value || []).filter(p => p.status === "Pending" && p.mandatory_check_in_block).length)

async function acknowledge(policy) {
	if (acknowledgingName.value) return
	acknowledgingName.value = policy.name
	try {
		await ackResource.submit({ name: policy.name })
		await policiesResource.reload()
		toast({ title: __("Acknowledged"), text: policy.policy_name, icon: "check-circle", position: "bottom-center", iconClasses: "text-green-500" })
	} catch (error) {
		showErrorFromException(error, __("Could not acknowledge"))
	} finally {
		acknowledgingName.value = null
	}
}

async function loadHistory(policy) {
	if (historyByPolicy.value[policy.hr_policy]) {
		// Toggle: clear if already loaded
		delete historyByPolicy.value[policy.hr_policy]
		historyByPolicy.value = { ...historyByPolicy.value }
		return
	}
	const res = await historyResource.submit({ hr_policy: policy.hr_policy })
	historyByPolicy.value = { ...historyByPolicy.value, [policy.hr_policy]: res?.history || [] }
}
</script>

<style scoped>
.ion-page { --ion-background-color: #FBFBFC; }
</style>
