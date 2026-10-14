<template>
	<ion-page>
		<ion-header class="ion-no-border">
			<div class="w-full sm:max-w-4xl mx-auto">
				<div class="flex flex-col bg-white shadow-sm p-4">
					<div class="flex flex-row justify-between items-center">
						<div class="flex flex-row items-center gap-2">
							<h2 class="text-xl font-bold text-gray-900">
								{{ props.pageTitle || __("Frappe HR") }}
							</h2>
						</div>
						<div class="flex flex-row items-center gap-3 ml-auto">
							<!-- Hard-refresh button: bypasses Vue router cache + the
							     service-worker so users can recover from a stale
							     screen without quitting the app. `window.location.reload`
							     triggers SW revalidation; a `router.go(0)` would
							     only re-mount the current route. -->
							<button
								type="button"
								@click="onRefresh"
								:aria-label="__('Refresh')"
								class="flex items-center justify-center"
							>
								<FeatherIcon name="refresh-cw" class="h-6 w-6" />
							</button>
							<router-link
								:to="{ name: 'Notifications' }"
								v-slot="{ navigate }"
								class="flex flex-col items-center"
							>
								<span class="relative inline-block" @click="navigate">
									<FeatherIcon name="bell" class="h-6 w-6" />
									<span
										v-if="unreadNotificationsCount.data"
										class="absolute top-0 right-0.5 inline-block w-2 h-2 bg-red-600 rounded-full border border-white"
									>
									</span>
								</span>
							</router-link>
							<router-link
								:to="{ name: 'Profile' }"
								class="flex flex-col items-center"
							>
								<Avatar
									:image="user.data.user_image"
									:label="user.data.first_name"
									size="xl"
								/>
							</router-link>
						</div>
					</div>
				</div>
			</div>
		</ion-header>

		<ion-content class="ion-no-padding">
			<div class="flex flex-col h-screen w-full sm:max-w-4xl mx-auto">
				<slot name="body"></slot>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonHeader, IonContent, IonPage } from "@ionic/vue"
import { FeatherIcon, Avatar } from "frappe-ui"

import { unreadNotificationsCount } from "@/data/notifications"

import { inject } from "vue"

const user = inject("$user")
const __ = inject("$translate")

const props = defineProps({
	pageTitle: {
		type: String,
		required: false,
		default: "",
	},
})

function onRefresh() {
	window.location.reload()
}
</script>
