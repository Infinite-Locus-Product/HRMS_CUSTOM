<template>
	<ion-modal
		:is-open="isOpen"
		@didDismiss="$emit('close')"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="flex flex-col gap-5 p-5 pb-7">
			<div class="flex items-start gap-3">
				<div class="rounded-full bg-red-100 p-2.5 mt-1 shrink-0">
					<FeatherIcon name="alert-triangle" class="w-5 h-5 text-red-600" />
				</div>
				<div class="flex-1 min-w-0">
					<h2 class="text-base font-bold text-gray-900">
						{{ __("Action blocked") }}
					</h2>
					<p class="text-sm text-gray-600 mt-1">
						{{ subtitle || __("You must acknowledge the following HR policies before you can {0}.", [actionLabel]) }}
					</p>
				</div>
			</div>

			<div class="rounded-lg border border-red-200 bg-red-50 divide-y divide-red-100">
				<div
					v-for="p in policies"
					:key="p.name"
					class="flex items-center justify-between gap-3 px-3.5 py-2.5"
				>
					<div class="flex-1 min-w-0">
						<div class="text-sm font-semibold text-red-900 truncate">
							{{ p.policy_name || p.name }}
						</div>
						<div v-if="p.name" class="text-[11px] text-red-700/70 mt-0.5 font-mono">
							{{ p.name }}
						</div>
					</div>
					<a
						v-if="p.file"
						:href="p.file"
						target="_blank"
						rel="noopener"
						class="text-xs font-semibold text-red-700 underline shrink-0"
					>
						{{ __("PDF") }}
					</a>
				</div>
			</div>

			<div class="flex flex-col gap-2">
				<button
					type="button"
					@click="goToPolicies"
					class="w-full py-4 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2"
				>
					<FeatherIcon name="check-circle" class="h-4 w-4" />
					{{ __("Review & Acknowledge") }}
				</button>
				<button
					type="button"
					@click="$emit('close')"
					class="w-full py-3 rounded-2xl bg-white border border-gray-200 text-gray-700 font-bold text-xs uppercase tracking-widest hover:bg-gray-50 transition-all"
				>
					{{ __("Not now") }}
				</button>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { inject } from "vue"
import { useRouter } from "vue-router"
import { IonModal } from "@ionic/vue"
import { FeatherIcon } from "frappe-ui"

const __ = inject("$translate")
const router = useRouter()

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	policies: { type: Array, default: () => [] },
	actionLabel: { type: String, default: "proceed" },
	subtitle: { type: String, default: "" },
})

const emit = defineEmits(["close"])

function goToPolicies() {
	emit("close")
	router.push({ name: "EmployeePolicies" })
}
</script>
