<template>
	<div class="hidden"></div>
</template>

<script setup>
import { onMounted } from "vue"

const isIos = () => /iphone|ipad|ipod/.test(window.navigator.userAgent.toLowerCase())
const isInStandaloneMode = () => ("standalone" in window.navigator && window.navigator.standalone)

onMounted(() => {
	window.addEventListener("beforeinstallprompt", (e) => {
		// Prevent the mini-infobar from appearing on mobile
		e.preventDefault()
		// Stash the event so it can be triggered later via Quick Links
		window.deferredPrompt = e
		
		console.log("PWA Install Prompt stashed for manual trigger.")
	})

	window.addEventListener("appinstalled", () => {
		window.deferredPrompt = null
	})
})

// Function to trigger install manually from Quick Link
window.triggerPWAInstall = async () => {
	if (isIos() && !isInStandaloneMode()) {
		alert("Tap the Share button at the bottom of your screen and select 'Add to Home Screen' to install.")
	} else if (window.deferredPrompt) {
		window.deferredPrompt.prompt()
		const { outcome } = await window.deferredPrompt.userChoice
		if (outcome === 'accepted') {
			window.deferredPrompt = null
		}
	} else {
		// If it's already installed or not supported
		alert("App is already installed or your browser doesn't support PWA installation.")
	}
}
</script>
