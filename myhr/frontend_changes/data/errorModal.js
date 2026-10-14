// Global error modal state — single source of truth shared by every caller and
// the singleton <ErrorModal /> mounted in App.vue. Replaces the old per-view
// `toast({icon:"alert-circle"...})` pattern, which (a) stacked into 2-3 copies
// of the same error and (b) auto-dismissed before users could read the message.
import { ref } from "vue"

export const errorModalState = ref({ open: false, message: "", title: "Error" })

// Dedupe successive identical errors fired within this window. setValue submits
// can fire onError twice in quick succession when validators throw mid-cycle;
// without dedupe the user sees the same modal flash open → close → open.
const DEDUPE_MS = 1500
let lastMessage = ""
let lastTime = 0

/**
 * Strip the parts of a Frappe error message that don't make sense in a PWA
 * context — desk hyperlinks, the "Reference: NAME" footer, leading/trailing
 * whitespace, and the literal strings "undefined" / "null" that occasionally
 * leak through when the server pushes an empty `_server_messages`.
 */
export function sanitizeErrorText(text) {
	if (text === null || text === undefined) return ""
	let s = String(text)
	if (s === "undefined" || s === "null") return ""
	// Remove desk anchors: <a href="/desk/...">label</a>  → label
	s = s.replace(/<a [^>]*href="\/(?:desk|app)\/[^"]*"[^>]*>(.*?)<\/a>/gi, "$1")
	// Strip the "Reference:" footer Frappe appends with a Desk link
	s = s.replace(/^\s*Reference:.*$/gim, "")
	// Strip remaining HTML tags (frappe.throw can include <b> etc. — keep text)
	s = s.replace(/<\/?[^>]+>/g, "")
	return s.replace(/\n{3,}/g, "\n\n").trim()
}

/**
 * Show the global error modal with a sanitized message. Deduplicates rapid
 * repeats so the user never sees the same error twice in a row.
 */
export function showError(message, title = "Error") {
	const clean = sanitizeErrorText(message)
	if (!clean) return  // nothing meaningful to display — drop silently
	const now = Date.now()
	if (clean === lastMessage && (now - lastTime) < DEDUPE_MS) return
	lastMessage = clean
	lastTime = now
	errorModalState.value = { open: true, message: clean, title }
}

export function closeError() {
	errorModalState.value = { open: false, message: "", title: "Error" }
}

/**
 * Pull the user-facing message out of a Frappe error and display it in the
 * global modal. Cascades through messages[0] → _server_messages → message →
 * exc, parses JSON-stringified Frappe wrappers, and falls back to the caller's
 * fallback string if nothing meaningful is found.
 */
export function showErrorFromException(err, fallback = "") {
	if (!err) {
		if (fallback) showError(fallback)
		return
	}
	let raw = err?.messages?.[0] || err?._server_messages || err?.message || err?.exc
	if (!raw || raw === "undefined" || raw === "null") {
		if (fallback) showError(fallback)
		return
	}
	if (typeof raw === "string" && raw.trim().startsWith("[")) {
		try {
			const arr = JSON.parse(raw)
			if (Array.isArray(arr) && arr.length) raw = arr[0]
		} catch (e) { /* not JSON, keep raw */ }
	}
	if (typeof raw === "string" && raw.trim().startsWith("{")) {
		try {
			const parsed = JSON.parse(raw)
			raw = parsed?.message || parsed?.title || fallback
		} catch (e) { /* not JSON, keep raw */ }
	}
	const text = typeof raw === "string" ? raw : (raw?.message || fallback)
	showError(text || fallback)
}
