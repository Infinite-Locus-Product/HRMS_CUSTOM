<template>
	<div class="flex p-1 bg-gray-100 rounded-2xl border border-gray-200">
		<button
			v-for="button in buttons"
			:key="button.key ?? button.label ?? button"
			class="flex-1 px-4 py-2 transition-all rounded-xl text-[12px] font-black uppercase tracking-widest"
			:class="
				modelValue === (button.key ?? button.label ?? button)
					? 'bg-white text-blue-700 shadow-sm'
					: 'text-gray-500 hover:text-gray-700'
			"
			@click="$emit('update:modelValue', button.key ?? button.label ?? button)"
		>
			{{ button.label ?? __(button) }}
		</button>
	</div>
</template>

<script setup>
const props = defineProps({
	buttons: {
		type: Array,
		required: true,
	},
	modelValue: {
		type: String,
	},
})

defineEmits(["update:modelValue"])
</script>
