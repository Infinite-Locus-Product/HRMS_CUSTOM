<!--
  Fullscreen document preview modal — mobile-safe.

  Plain <iframe src="*.pdf"> on iOS Safari shows only the first page as a
  static thumbnail and Android Chrome usually refuses inline render. This
  component renders PDFs via PDF.js (lazy-loaded from jsDelivr CDN — no
  bundle dep, no package.json overlay on hrms). Images render via <img>.
  Anything else falls back to an "Open in browser" CTA.
-->
<template>
	<div
		v-if="url"
		class="fixed inset-0 z-[9999] flex flex-col bg-black"
		style="padding-bottom: env(safe-area-inset-bottom);"
		role="dialog"
		aria-modal="true"
	>
		<!-- Header -->
		<div
			class="flex items-center justify-between px-4 py-3 bg-gray-900 text-white shrink-0"
			style="padding-top: max(env(safe-area-inset-top), 0.75rem);"
		>
			<div class="flex items-center gap-2 min-w-0 flex-1">
				<FeatherIcon name="file-text" class="h-4 w-4 shrink-0" />
				<span class="text-sm font-bold truncate">{{ title || __("Document") }}</span>
			</div>
			<a
				:href="url"
				target="_blank"
				rel="noopener"
				class="p-2 rounded-lg hover:bg-white/10 active:scale-95 transition-all shrink-0 ml-2"
				:title="__('Open in new tab')"
			>
				<FeatherIcon name="external-link" class="h-5 w-5" />
			</a>
			<button
				type="button"
				@click="$emit('close')"
				class="p-2 rounded-lg hover:bg-white/10 active:scale-95 transition-all shrink-0 ml-1"
				:aria-label="__('Close')"
			>
				<FeatherIcon name="x" class="h-6 w-6" />
			</button>
		</div>

		<!-- Body -->
		<div
			ref="bodyRef"
			class="flex-1 overflow-y-auto bg-gray-100 doc-preview-body"
			style="-webkit-overflow-scrolling: touch; touch-action: pan-y pinch-zoom;"
		>
			<!-- PDF -->
			<template v-if="kind === 'pdf'">
				<div v-if="pdfLoading" class="flex flex-col items-center justify-center py-32 gap-3 text-white">
					<LoadingIndicator class="h-8 w-8" />
					<div class="text-xs font-bold uppercase tracking-widest opacity-70">
						{{ __("Loading document") }}
					</div>
				</div>
				<div v-else-if="pdfError" class="flex flex-col items-center justify-center py-20 px-6 text-center text-white">
					<FeatherIcon name="alert-triangle" class="h-10 w-10 mb-3 text-red-400" />
					<div class="text-base font-bold mb-1">{{ __("Couldn't render this PDF") }}</div>
					<div class="text-xs opacity-70 mb-4 break-all">{{ pdfError }}</div>
					<a :href="url" target="_blank" rel="noopener" class="px-4 py-2 rounded-lg bg-white text-gray-900 text-sm font-bold">
						{{ __("Open in browser") }}
					</a>
				</div>
				<div v-else class="flex flex-col items-center gap-2 py-2 px-2">
					<canvas
						v-for="(_, i) in pdfPages"
						:key="i"
						:ref="el => setCanvasRef(el, i)"
						class="bg-white shadow-md max-w-full"
					></canvas>
				</div>
			</template>

			<!-- Image -->
			<div
				v-else-if="kind === 'image'"
				class="min-h-full flex items-start justify-center p-2"
			>
				<img
					:src="url"
					class="max-w-full h-auto bg-white shadow-md rounded-sm"
					:alt="title || __('Document')"
				/>
			</div>

			<!-- Other (docx, xlsx, anything unknown) -->
			<div v-else class="flex flex-col items-center justify-center h-full p-6 text-center text-white">
				<FeatherIcon name="file" class="h-12 w-12 mb-3 opacity-60" />
				<div class="text-base font-bold mb-1">{{ __("No inline preview") }}</div>
				<div class="text-xs opacity-70 mb-4">
					{{ __("This file type opens in your browser.") }}
				</div>
				<a
					:href="url"
					target="_blank"
					rel="noopener"
					class="px-4 py-2 rounded-lg bg-white text-gray-900 text-sm font-bold"
				>
					{{ __("Open in browser") }}
				</a>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount, inject } from "vue"
import { FeatherIcon, LoadingIndicator } from "frappe-ui"

const props = defineProps({
	url: { type: String, default: null },
	title: { type: String, default: "" },
})
defineEmits(["close"])
const __ = inject("$translate")

const PDFJS_VERSION = "4.10.38"
const PDFJS_BASE = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${PDFJS_VERSION}/build`

const kind = computed(() => {
	if (!props.url) return "other"
	const clean = props.url.split("?")[0].split("#")[0].toLowerCase()
	if (clean.endsWith(".pdf")) return "pdf"
	if (/\.(jpe?g|png|webp|gif|bmp|svg)$/.test(clean)) return "image"
	return "other"
})

const bodyRef = ref(null)
const pdfLoading = ref(false)
const pdfError = ref("")
const pdfPages = ref([])
const canvasRefs = ref([])

let renderToken = 0
let pdfDocHandle = null

function setCanvasRef(el, i) {
	canvasRefs.value[i] = el
}

// Module-level so the PDF.js bundle is fetched once per session.
let pdfjsPromise = null
async function loadPdfjs() {
	if (pdfjsPromise) return pdfjsPromise
	pdfjsPromise = (async () => {
		const mod = await import(/* @vite-ignore */ `${PDFJS_BASE}/pdf.min.mjs`)
		// Module worker from jsDelivr (CORS headers OK). If a browser blocks
		// the cross-origin worker, PDF.js falls back to fake worker mode.
		mod.GlobalWorkerOptions.workerSrc = `${PDFJS_BASE}/pdf.worker.min.mjs`
		return mod
	})()
	return pdfjsPromise
}

async function renderPdf(url) {
	const myToken = ++renderToken
	pdfLoading.value = true
	pdfError.value = ""
	pdfPages.value = []
	canvasRefs.value = []
	try {
		const pdfjs = await loadPdfjs()
		if (myToken !== renderToken) return
		// withCredentials so private Frappe files (/private/files/...) inherit session cookie.
		const loadingTask = pdfjs.getDocument({ url, withCredentials: true })
		const doc = await loadingTask.promise
		if (myToken !== renderToken) {
			doc.destroy()
			return
		}
		pdfDocHandle?.destroy()
		pdfDocHandle = doc
		const pages = []
		for (let p = 1; p <= doc.numPages; p++) {
			pages.push(await doc.getPage(p))
			if (myToken !== renderToken) return
		}
		pdfPages.value = pages
		pdfLoading.value = false
		await nextTick()
		const dpr = Math.min(window.devicePixelRatio || 1, 2)
		// 16px = 2 * 8px page x-padding inside the column.
		const containerWidth = Math.max(
			((bodyRef.value?.clientWidth) || window.innerWidth) - 16,
			200
		)
		for (let i = 0; i < pages.length; i++) {
			if (myToken !== renderToken) return
			const page = pages[i]
			const baseViewport = page.getViewport({ scale: 1 })
			const scale = (containerWidth / baseViewport.width) * dpr
			const viewport = page.getViewport({ scale })
			const canvas = canvasRefs.value[i]
			if (!canvas) continue
			canvas.width = viewport.width
			canvas.height = viewport.height
			canvas.style.width = `${viewport.width / dpr}px`
			canvas.style.height = `${viewport.height / dpr}px`
			await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise
		}
	} catch (e) {
		if (myToken !== renderToken) return
		console.error("DocumentPreviewModal: PDF render failed:", e)
		pdfError.value = e?.message || String(e)
		pdfLoading.value = false
	}
}

function reset() {
	renderToken++
	pdfLoading.value = false
	pdfError.value = ""
	pdfPages.value = []
	canvasRefs.value = []
	if (pdfDocHandle) {
		pdfDocHandle.destroy()
		pdfDocHandle = null
	}
}

watch(
	() => [props.url, kind.value],
	([url, k]) => {
		if (!url) {
			reset()
			return
		}
		if (k === "pdf") {
			renderPdf(url)
		} else {
			reset()
		}
	},
	{ immediate: true }
)

onBeforeUnmount(() => reset())
</script>

<style scoped>
.doc-preview-body canvas {
	display: block;
	height: auto;
}
</style>
