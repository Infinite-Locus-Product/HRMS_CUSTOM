<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<div
				class="min-h-screen w-full bg-[#FBFBFC] flex flex-col justify-center items-center p-4"
			>
				<div
					class="w-full sm:max-w-md mx-auto rounded-3xl bg-white border border-gray-100 shadow-xl p-8 sm:p-10"
				>
					<!-- Header / brand -->
					<div class="flex flex-col items-center gap-3 mb-8">
						<div
							class="p-3 rounded-2xl bg-blue-50 border border-blue-100 shadow-sm"
						>
							<FrappeHRLogo class="h-7 w-7 text-blue-600" />
						</div>
						<div class="text-2xl font-extrabold text-gray-900 text-center">
							{{ __("Welcome back") }}
						</div>
						<div
							class="text-[11px] font-bold text-gray-400 uppercase tracking-widest text-center"
						>
							{{ __("Sign in to Frappe HR") }}
						</div>
					</div>

					<form
						v-if="!user_pass_login_disabled.data"
						class="flex flex-col space-y-4"
						@submit.prevent="submit"
					>
						<Input
							:label="__('Email')"
							:placeholder="__('johndoe@mail.com')"
							v-model="email"
							type="text"
							autocomplete="username"
						/>
						<Input
							:label="__('Password')"
							type="password"
							placeholder="••••••"
							v-model="password"
							autocomplete="current-password"
						/>
						<ErrorMessage :message="errorMessage" />
						<button
							type="submit"
							:disabled="session.login.loading"
							class="w-full py-3.5 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50 mt-3"
						>
							<LoadingIndicator
								v-if="session.login.loading"
								class="h-4 w-4 text-white"
							/>
							<FeatherIcon v-else name="log-in" class="h-4 w-4" />
							{{ __("Login") }}
						</button>
					</form>

					<template v-if="authProviders.data?.length">
						<div
							v-if="!user_pass_login_disabled.data"
							class="flex items-center gap-3 my-6"
						>
							<div class="h-px bg-gray-200 flex-1"></div>
							<div
								class="text-[10px] font-black uppercase tracking-widest text-gray-400"
							>
								{{ __("or") }}
							</div>
							<div class="h-px bg-gray-200 flex-1"></div>
						</div>
						<div class="space-y-2.5">
							<a
								v-for="provider in authProviders.data"
								:key="provider.name"
								class="flex items-center justify-center gap-2 px-4 py-3 rounded-2xl bg-white border-2 border-gray-200 text-gray-700 font-bold text-sm hover:border-blue-300 hover:text-blue-700 transition-all"
								:href="provider.auth_url"
							>
								<img
									class="h-4 w-4"
									:src="provider.icon"
									:alt="provider.provider_name"
								/>
								<span>{{ __("Login with {0}", [provider.provider_name]) }}</span>
							</a>
						</div>
					</template>

					<div
						v-else-if="user_pass_login_disabled.data"
						class="text-center text-sm text-gray-600 py-8"
					>
						{{
							__(
								"No login methods are available. Please contact your administrator."
							)
						}}
					</div>
				</div>
			</div>

			<Dialog v-model="resetPassword.showDialog">
				<template #body-title>
					<h2 class="text-lg font-bold">{{ __("Reset Password") }}</h2>
				</template>
				<template #body-content>
					<p>
						{{
							__(
								"Your password has expired. Please reset your password to continue"
							)
						}}
					</p>
				</template>
				<template #actions>
					<a
						class="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 transition-all"
						:href="resetPassword.link"
						target="_blank"
					>
						{{ __("Go to Reset Password page") }}
					</a>
				</template>
			</Dialog>

			<Dialog v-model="otp.showDialog">
				<template #body-title>
					<h2 class="text-lg font-bold">{{ __("OTP Verification") }}</h2>
				</template>
				<template #body-content>
					<p class="mb-4" v-if="otp.verification.prompt">
						{{ otp.verification.prompt }}
					</p>

					<form class="flex flex-col space-y-4" @submit.prevent="submit">
						<Input
							:label="__('OTP Code')"
							type="text"
							placeholder="000000"
							v-model="otp.code"
							autocomplete="one-time-code"
						/>
						<ErrorMessage :message="errorMessage" />
						<button
							type="submit"
							:disabled="session.otp.loading"
							class="w-full py-3.5 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50 mt-3"
						>
							<LoadingIndicator
								v-if="session.otp.loading"
								class="h-4 w-4 text-white"
							/>
							{{ __("Verify") }}
						</button>
					</form>
				</template>
			</Dialog>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { inject, reactive, ref } from "vue"
import {
	Input,
	ErrorMessage,
	Dialog,
	FeatherIcon,
	LoadingIndicator,
	createResource,
} from "frappe-ui"

import FrappeHRLogo from "@/components/icons/FrappeHRLogo.vue"

const email = ref(null)
const password = ref(null)
const errorMessage = ref("")

const resetPassword = reactive({ showDialog: false, link: "" })
const otp = reactive({
	showDialog: false,
	tmp_id: "",
	code: "",
	verification: {},
})

const session = inject("$session")
const __ = inject("$translate")

async function submit(e) {
	try {
		let response
		if (otp.showDialog) {
			response = await session.otp(otp.tmp_id, otp.code)
		} else {
			response = await session.login(email.value, password.value)
		}

		if (response.message === "Password Reset") {
			resetPassword.showDialog = true
			resetPassword.link = response.redirect_to
		} else {
			resetPassword.showDialog = false
			resetPassword.link = ""
		}

		if (response.verification) {
			if (response.verification.setup) {
				otp.showDialog = true
				otp.tmp_id = response.tmp_id
				otp.verification = response.verification
			} else {
				window.open(
					"/login?redirect-to=" +
						encodeURIComponent(window.location.pathname),
					"_blank"
				)
			}
		}
	} catch (error) {
		const msgs = error?.messages
		errorMessage.value = Array.isArray(msgs) && msgs.length
			? msgs.join("\n")
			: error?.message || String(error) || __("Login failed")
	}
}

const user_pass_login_disabled = createResource({
	url: "hrms.api.system_settings.get_user_pass_login_disabled",
	method: "GET",
	initialData: 1,
	auto: true,
})

const authProviders = createResource({
	url: "hrms.api.oauth.oauth_providers",
	auto: true,
})
</script>
