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
							class="!px-2 hover:bg-gray-100"
							@click="router.back()"
						>
							<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
						</Button>
						<div class="flex flex-col ml-1 overflow-hidden">
							<h2
								class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1"
							>
								{{ __("Notifications") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span
									class="text-[10px] font-bold uppercase tracking-widest"
								>
									<span v-if="unreadNotificationsCount.data">
										{{
											__("{0} unread", [unreadNotificationsCount.data])
										}}
									</span>
									<span v-else>{{ __("All caught up") }}</span>
								</span>
							</div>
						</div>
					</div>

					<!-- Action bar -->
					<div
						v-if="unreadNotificationsCount.data || notifications.data?.length"
						class="flex flex-row gap-2 px-4 pt-4 flex-wrap"
					>
						<button
							v-if="allowPushNotifications"
							type="button"
							@click="router.push({ name: 'Settings' })"
							class="rounded-xl px-3 py-2 bg-white border border-gray-200 text-gray-700 hover:border-gray-300 text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5"
						>
							<FeatherIcon name="settings" class="h-3.5 w-3.5" />
							{{ __("Settings") }}
						</button>
						<button
							v-if="unreadNotificationsCount.data"
							type="button"
							@click="markAllAsRead.submit"
							:disabled="markAllAsRead.loading"
							class="rounded-xl px-3 py-2 bg-blue-50 border border-blue-100 text-blue-700 hover:bg-blue-100 text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 disabled:opacity-50"
						>
							<FeatherIcon name="check-circle" class="h-3.5 w-3.5" />
							{{ __("Mark all read") }}
						</button>
						<button
							v-if="notifications.data?.length"
							type="button"
							@click="confirmClearAll"
							:disabled="clearAll.loading"
							class="rounded-xl px-3 py-2 bg-red-50 border border-red-100 text-red-700 hover:bg-red-100 text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 disabled:opacity-50"
						>
							<FeatherIcon name="trash-2" class="h-3.5 w-3.5" />
							{{ __("Clear all") }}
						</button>
					</div>

					<div class="flex-1 px-4 py-4 space-y-4">
						<div
							v-if="notifications.data?.length"
							class="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden divide-y divide-gray-100"
						>
							<div
								v-for="item in notifications.data"
								:key="item.name"
								class="flex flex-row items-start gap-3 p-4 hover:bg-blue-50/40 transition-colors relative"
							>
								<!-- Unread indicator -->
								<div
									v-if="!item.read"
									class="absolute top-4 left-1.5 w-1.5 h-1.5 rounded-full bg-blue-500"
								></div>

								<div
									class="flex flex-row items-start grow cursor-pointer min-w-0 ml-1"
									@click="openNotification(item)"
								>
									<EmployeeAvatar :userID="item.from_user" size="lg" />
									<div class="flex flex-col gap-0.5 grow ml-3 min-w-0">
										<div
											class="text-sm leading-5 text-gray-800 break-words"
											:class="item.read ? 'font-medium' : 'font-bold'"
											v-html="item.message"
										></div>
										<div
											class="text-[11px] font-bold text-gray-500"
										>
											{{ dayjs(item.creation).fromNow() }}
										</div>
									</div>
								</div>
								<div class="flex flex-row items-center gap-1 shrink-0 ml-2">
									<button
										v-if="!item.read"
										type="button"
										:title="__('Mark as read')"
										@click.stop="markAsRead(item.name)"
										class="p-1.5 rounded-lg hover:bg-green-50 text-gray-400 hover:text-green-600 transition-colors"
									>
										<FeatherIcon name="check" class="w-4 h-4" />
									</button>
									<button
										type="button"
										:title="__('Dismiss')"
										@click.stop="dismissOne(item.name)"
										class="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
									>
										<FeatherIcon name="x" class="w-4 h-4" />
									</button>
								</div>
							</div>
						</div>

						<div
							v-if="
								notifications.data?.length && notifications.hasNextPage
							"
							class="flex"
						>
							<button
								type="button"
								@click="loadMore"
								class="ml-auto rounded-xl px-3 py-2 bg-white border border-gray-200 text-gray-700 hover:border-gray-300 text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5"
							>
								{{ __("Load more") }}
							</button>
						</div>

						<EmptyState
							v-else-if="!notifications.data?.length"
							:message="__('You have no notifications')"
						/>
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonContent, IonPage, onIonViewWillEnter } from "@ionic/vue"
import { useRouter } from "vue-router"
import { createResource, Button, FeatherIcon, toast } from "frappe-ui"
import { showErrorFromException } from "@/data/errorModal"

import { computed, inject, onMounted, ref } from "vue"
import EmployeeAvatar from "@/components/EmployeeAvatar.vue"
import EmptyState from "@/components/EmptyState.vue"

import {
	unreadNotificationsCount,
	notifications,
	arePushNotificationsEnabled,
} from "@/data/notifications"

const dayjs = inject("$dayjs")
const router = useRouter()
const __ = inject("$translate")
const currentStart = ref(0)
const pageLength = 10

const allowPushNotifications = computed(
	() =>
		window.frappe?.boot.push_relay_server_url &&
		arePushNotificationsEnabled.data
)

const markAllAsRead = createResource({
	url: "hrms.api.mark_all_notifications_as_read",
	onSuccess() {
		notifications.reload()
		unreadNotificationsCount.reload()
	},
})

const clearAll = createResource({
	url: "myhr.api.clear_all_notifications",
	onSuccess() {
		notifications.reload()
		unreadNotificationsCount.reload()
		toast({
			title: __("Cleared"),
			text: __("All notifications removed."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
	},
	onError(err) {
		showErrorFromException(err, __("Could not clear notifications"))
	},
})

function confirmClearAll() {
	if (!notifications.data?.length) return
	if (window.confirm(__("Clear all notifications? This cannot be undone."))) {
		clearAll.submit()
	}
}

const markReadResource = createResource({
	url: "myhr.api.mark_notification_read",
	onSuccess() {
		notifications.reload()
		unreadNotificationsCount.reload()
	},
	onError(err) {
		showErrorFromException(err, __("Could not mark as read"))
	},
})

function markAsRead(name) {
	markReadResource.submit({ notification: name })
}

const dismissOneResource = createResource({
	url: "myhr.api.dismiss_notification",
	onSuccess() {
		notifications.reload()
		unreadNotificationsCount.reload()
	},
	onError(err) {
		showErrorFromException(err, __("Could not dismiss notification"))
	},
})

function dismissOne(name) {
	dismissOneResource.submit({ notification: name })
}

const REFERENCE_TYPE_ROUTES = {
	"Leave Application": "LeavesDashboard",
	"Expense Claim": "ExpenseClaimsDashboard",
	"Attendance Request": "AttendanceDashboard",
	"Policy Acknowledgement": "EmployeePolicies",
	"HR Policy": "EmployeePolicies",
}

function openNotification(item) {
	// Tapping a notification = "I've seen this". Mark read both optimistically
	// (so the unread dot disappears immediately and the row drops out of the
	// filtered list on next reload) and on the server. The submit is
	// fire-and-forget — by the time the user navigates back here, the next
	// `onIonViewWillEnter` reload will have a server-side read=1.
	if (!item.read) {
		item.read = 1
		markAsRead(item.name)
	}
	const target = REFERENCE_TYPE_ROUTES[item.reference_document_type]
	if (target) {
		router.push({ name: target })
	}
}

function refreshNotificationsList() {
	notifications.filters = {
		...(notifications.filters || {}),
		read: 0,
	}
	notifications.start = 0
	notifications.pageLength = 10
	notifications.reload()
	unreadNotificationsCount.reload()
}

onMounted(refreshNotificationsList)

// Ionic keeps pages alive on the nav stack, so `onMounted` only fires once
// for the lifetime of the session. Without `onIonViewWillEnter`, a user who
// taps a notification → lands on Attendance/Leave → navigates back here
// would still see the just-tapped row because the filtered list never
// re-fetched after the server flipped read=1. This hook closes that loop.
onIonViewWillEnter(refreshNotificationsList)

function loadMore() {
	currentStart.value += pageLength
	notifications.start = currentStart.value
	notifications.pageLength = pageLength
	notifications.list.fetch()
}
</script>
