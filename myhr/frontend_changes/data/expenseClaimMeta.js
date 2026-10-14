// Shared display config for Expense Claim Type categories.
// Catalogue (Calls / Food / Medical / Others / Travel) is small and
// stable; iconography + theme colours live in the frontend so we can
// keep the chip in the modal, the row icon in the line-item list, and
// the icon in the dashboard claim list visually consistent. Unknown
// types fall through to "Others".

export const EXPENSE_TYPE_META = {
    Travel: {
        icon: "navigation",
        bg: "bg-sky-50",
        text: "text-sky-600",
        activeBg: "bg-sky-50",
        activeText: "text-sky-700",
        activeBorder: "border-sky-200",
    },
    Food: {
        icon: "coffee",
        bg: "bg-amber-50",
        text: "text-amber-600",
        activeBg: "bg-amber-50",
        activeText: "text-amber-700",
        activeBorder: "border-amber-200",
    },
    Calls: {
        icon: "phone-call",
        bg: "bg-emerald-50",
        text: "text-emerald-600",
        activeBg: "bg-emerald-50",
        activeText: "text-emerald-700",
        activeBorder: "border-emerald-200",
    },
    Medical: {
        icon: "activity",
        bg: "bg-rose-50",
        text: "text-rose-600",
        activeBg: "bg-rose-50",
        activeText: "text-rose-700",
        activeBorder: "border-rose-200",
    },
    Others: {
        icon: "more-horizontal",
        bg: "bg-violet-50",
        text: "text-violet-600",
        activeBg: "bg-violet-50",
        activeText: "text-violet-700",
        activeBorder: "border-violet-200",
    },
}

export function getExpenseTypeMeta(type) {
    return EXPENSE_TYPE_META[type] || EXPENSE_TYPE_META.Others
}

// Currency symbol map used by the amount input prefix and quick chips.
// Falls back to the ISO code so we never render an empty prefix.
const CURRENCY_SYMBOLS = {
    INR: "₹", USD: "$", EUR: "€", GBP: "£",
    AED: "د.إ", AUD: "A$", CAD: "C$",
}

export function getCurrencySymbol(code) {
    return CURRENCY_SYMBOLS[code || "INR"] || code
}
