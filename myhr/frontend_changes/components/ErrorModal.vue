<template>
	<Teleport to="body">
		<Transition name="error-modal">
			<div
				v-if="state.open"
				class="fixed inset-0 z-[300] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
				@click.self="close"
			>
				<div
					class="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 space-y-5"
					role="alertdialog"
					aria-modal="true"
					aria-labelledby="error-modal-title"
				>
					<div class="flex items-start gap-3">
						<div class="p-2.5 bg-red-50 text-red-600 rounded-2xl shrink-0">
							<FeatherIcon name="alert-circle" class="h-5 w-5" />
						</div>
						<div class="flex-1 min-w-0">
							<h3 id="error-modal-title" class="text-base font-extrabold text-gray-900">
								{{ state.title }}
							</h3>
							<p class="text-sm text-gray-700 mt-1.5 leading-relaxed whitespace-pre-line break-words">
								{{ state.message }}
							</p>
						</div>
						<button
							type="button"
							class="text-gray-400 hover:text-gray-700 shrink-0 -mt-1 -mr-1 p-1 rounded-lg hover:bg-gray-100 transition-colors"
							:aria-label="__('Close')"
							@click="close"
						>
							<FeatherIcon name="x" class="h-5 w-5" />
						</button>
					</div>
					<div class="flex justify-end">
						<button
							type="button"
							class="h-10 px-6 rounded-xl text-white text-xs font-black uppercase tracking-widest hover:brightness-110 active:scale-95 transition-all shadow-md"
							style="background-color: #4f46e5; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3);"
							@click="close"
						>
							{{ __("Close") }}
						</button>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>

<script setup>
import { inject } from "vue"
import { FeatherIcon } from "frappe-ui"
import { errorModalState, closeError } from "@/data/errorModal"

const __ = inject("$translate") || ((s) => s)
const state = errorModalState

function close() {
	closeError()
}
</script>

<style scoped>
.error-modal-enter-active,
.error-modal-leave-active {
	transition: opacity 0.18s ease;
}
.error-modal-enter-from,
.error-modal-leave-to {
	opacity: 0;
}
.error-modal-enter-active > div,
.error-modal-leave-active > div {
	transition: transform 0.18s ease;
}
.error-modal-enter-from > div,
.error-modal-leave-to > div {
	transform: translateY(-8px);
}
</style>
