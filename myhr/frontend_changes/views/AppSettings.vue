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
								{{ __("Settings") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span
									class="text-[10px] font-bold uppercase tracking-widest"
								>
									{{ __("Preferences and toggles") }}
								</span>
							</div>
						</div>
					</div>

					<div class="flex-1 px-4 py-5 space-y-5">
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
								>
									<FeatherIcon name="bell" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Notifications") }}
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Push notifications and alerts") }}
									</span>
								</div>
							</div>
							<div
								class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4"
							>
								<Switch
									size="md"
									:label="__('Enable Push Notifications')"
									:model-value="pushNotificationState"
									:disabled="disablePushSetting"
									:description="description"
									@update:model-value="togglePushNotifications"
								/>
								<div
									v-if="isLoading"
									class="flex mt-3 items-center justify-center gap-2"
								>
									<LoadingIndicator class="w-3 h-3 text-blue-600" />
									<span class="text-xs font-bold text-gray-600">
										{{
											pushNotificationState
												? __("Disabling…")
												: __("Enabling…")
										}}
									</span>
								</div>
							</div>
						</section>
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { useRouter } from "vue-router"
import {
	Button,
	FeatherIcon,
	Switch,
	toast,
	LoadingIndicator,
} from "frappe-ui"

import { computed, inject, ref } from "vue"

import { arePushNotificationsEnabled } from "@/data/notifications"
import { showError, showErrorFromException } from "@/data/errorModal"

const __ = inject("$translate")
const router = useRouter()
const pushNotificationState = ref(
	window.frappePushNotification?.isNotificationEnabled()
)
const isLoading = ref(false)

const disablePushSetting = computed(() => {
	return (
		!(
			window.frappe?.boot.push_relay_server_url &&
			arePushNotificationsEnabled.data
		) || isLoading.value
	)
})

const description = computed(() => {
	return !(
		window.frappe?.boot.push_relay_server_url &&
		arePushNotificationsEnabled.data
	)
		? __("Push notifications have been disabled on your site")
		: ""
})

const togglePushNotifications = (newValue) => {
	if (newValue) {
		enablePushNotifications()
	} else {
		isLoading.value = true
		window.frappePushNotification
			.disableNotification()
			.then((_data) => {
				pushNotificationState.value = false
				toast({
					title: __("Success"),
					text: __("Push notifications disabled"),
					icon: "check-circle",
					position: "bottom-center",
					iconClasses: "text-green-500",
				})
			})
			.catch((error) => {
				showErrorFromException(
					error,
					__("Could not disable push notifications")
				)
			})
			.finally(() => {
				isLoading.value = false
			})
	}
}

const enablePushNotifications = () => {
	isLoading.value = true
	window.frappePushNotification
		.enableNotification()
		.then((data) => {
			if (data.permission_granted) {
				pushNotificationState.value = true
			} else {
				showError(__("Push Notification permission denied"))
				pushNotificationState.value = false
			}
		})
		.catch((error) => {
			showErrorFromException(error, __("Could not enable push notifications"))
			pushNotificationState.value = false
		})
		.finally(() => {
			isLoading.value = false
		})
}
</script>
