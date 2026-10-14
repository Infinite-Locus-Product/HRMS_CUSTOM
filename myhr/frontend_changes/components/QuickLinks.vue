<template>
	<div class="flex flex-col gap-3 my-2 w-full">
		<div
			class="text-[11px] font-black uppercase tracking-widest text-gray-400 px-1"
		>
			{{ title || __("Quick Links") }}
		</div>
		<div class="flex flex-col gap-3">
			<div
				v-for="(group, gi) in groupedItems"
				:key="gi"
				class="flex flex-col bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden divide-y divide-gray-100"
			>
				<template v-for="link in group" :key="link.title">
					<div
						v-if="link.route"
						class="flex flex-row p-3.5 items-center justify-between hover:bg-blue-50/60 active:bg-blue-100/60 transition-colors cursor-pointer"
						@click="navigateTo(link)"
					>
						<div class="flex flex-row items-center gap-3 grow min-w-0">
							<div
								class="p-2 rounded-xl border shrink-0"
								:class="iconTileClass(link)"
							>
								<component
									:is="link.icon"
									:name="link.iconName"
									:class="iconColorClass(link)"
									style="width: 1.15rem; height: 1.15rem"
								/>
							</div>
							<div
								class="text-[15px] font-extrabold text-gray-900 flex items-center gap-2 truncate"
							>
								{{ link.title }}
								<span
									v-if="link.badge"
									class="min-w-[1.25rem] h-5 px-1.5 rounded-full bg-red-500 text-white text-[10px] font-black inline-flex items-center justify-center leading-none shrink-0"
									>{{ link.badge > 99 ? "99+" : link.badge }}</span
								>
							</div>
						</div>
						<FeatherIcon
							name="chevron-right"
							class="h-4 w-4 text-gray-300 shrink-0"
						/>
					</div>

					<div
						v-else-if="link.onClick"
						class="flex flex-row p-3.5 items-center justify-between hover:bg-blue-50/60 active:bg-blue-100/60 cursor-pointer transition-colors"
						@click="link.onClick"
					>
						<div class="flex flex-row items-center gap-3 grow min-w-0">
							<div
								class="p-2 rounded-xl border shrink-0"
								:class="iconTileClass(link)"
							>
								<component
									:is="link.icon"
									:name="link.iconName"
									:class="iconColorClass(link)"
									style="width: 1.15rem; height: 1.15rem"
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
					</div>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"
import { FeatherIcon } from "frappe-ui"
import { useRouter } from "vue-router"

const router = useRouter()

const props = defineProps({
	title: {
		type: String,
		required: false,
		default: "",
	},
	items: {
		type: Array,
		required: true,
	},
})

const groupedItems = computed(() => {
	const groups = []
	let current = null
	let currentKey = Symbol("init")
	for (const link of props.items) {
		const key = link.group ?? currentKey
		if (key !== currentKey) {
			current = []
			groups.push(current)
			currentKey = key
		}
		current.push(link)
	}
	return groups
})

// Per-group color so tiles aren't a uniform grey wall — keeps the eye scanning
// without overdoing it. All tones are taken from the verified frappe-ui palette.
const TILE_TONES = {
	inbox: "bg-amber-50 border-amber-100",
	requests: "bg-blue-50 border-blue-100",
	browse: "bg-green-50 border-green-100",
	utility: "bg-gray-50 border-gray-200",
}
const ICON_TONES = {
	inbox: "text-amber-600",
	requests: "text-blue-600",
	browse: "text-green-600",
	utility: "text-gray-500",
}

function iconTileClass(link) {
	return TILE_TONES[link.group] || "bg-gray-50 border-gray-200"
}
function iconColorClass(link) {
	return ICON_TONES[link.group] || "text-gray-600"
}

const fullNavRoutes = new Set(["EmployeeActionCentre", "EmployeeDirectory"])

function navigateTo(link) {
	if (fullNavRoutes.has(link.route)) {
		const resolved = router.resolve({ name: link.route })
		window.location.href = resolved.href
	} else {
		router.push({ name: link.route })
	}
}
</script>
