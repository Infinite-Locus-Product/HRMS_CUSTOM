<template>
	<ion-modal :is-open="isOpen" @didDismiss="onDismiss">
		<div class="bg-white w-full h-full flex flex-col items-center justify-center px-6">
			<!-- Animated check circle -->
			<div class="relative">
				<div
					class="absolute inset-0 rounded-full bg-emerald-100 animate-ping"
					style="animation-duration: 1.6s; animation-iteration-count: 2"
				/>
				<div
					class="relative h-24 w-24 rounded-full bg-emerald-500 text-white flex items-center justify-center shadow-lg shadow-emerald-200"
				>
					<FeatherIcon name="check" class="h-12 w-12" stroke-width="3" />
				</div>
			</div>

			<h2 class="mt-8 text-2xl font-black text-gray-900 text-center">
				{{ title || __("Submitted!") }}
			</h2>
			<p
				v-if="subtitle"
				class="mt-2 text-sm font-semibold text-gray-500 text-center max-w-xs"
			>
				{{ subtitle }}
			</p>

			<!-- Optional reference label (e.g. document name) -->
			<div
				v-if="reference"
				class="mt-5 px-4 py-2 rounded-full bg-gray-100 text-gray-700 text-xs font-bold tracking-wide"
			>
				{{ reference }}
			</div>

			<button
				type="button"
				@click="onDismiss"
				class="mt-10 w-full max-w-sm py-4 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2"
				:style="{ marginBottom: 'max(1rem, env(safe-area-inset-bottom))' }"
			>
				{{ ctaLabel || __("Done") }}
			</button>
		</div>
	</ion-modal>
</template>

<script setup>
import { inject, onUnmounted, watch } from "vue"
import { IonModal } from "@ionic/vue"
import { FeatherIcon } from "frappe-ui"

const __ = inject("$translate")

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	title: { type: String, default: "" },
	subtitle: { type: String, default: "" },
	reference: { type: String, default: "" },
	ctaLabel: { type: String, default: "" },
	// How long to hold the modal open before auto-dismissing. Set to 0
	// to disable and require a manual tap.
	autoDismissMs: { type: Number, default: 2500 },
})

const emit = defineEmits(["dismiss"])

let dismissTimer = null

function clearTimer() {
	if (dismissTimer) {
		clearTimeout(dismissTimer)
		dismissTimer = null
	}
}

function onDismiss() {
	clearTimer()
	emit("dismiss")
}

// Start the auto-dismiss countdown when the modal opens; cancel it if
// the modal closes (manual tap, route change, parent unmount).
watch(
	() => props.isOpen,
	(open) => {
		clearTimer()
		if (open && props.autoDismissMs > 0) {
			dismissTimer = setTimeout(() => emit("dismiss"), props.autoDismissMs)
		}
	},
	{ immediate: true },
)

onUnmounted(clearTimer)
</script>
