# myHR Design System

The PWA's visual language was settled across the Action Centre, Leave, Attendance, Policies, and Expense surfaces between 2026-04-15 and 2026-04-28. This doc is the rulebook — when you add a new screen or component, follow these patterns. Don't re-derive them and don't reach for stock frappe-ui defaults that diverge from what's listed here.

> **Hard rule:** never use the stock `frappe-ui <Button variant="solid">` for primary actions. Its default theme renders dark gray / black, which clashes with the brand-blue used everywhere else. Use the native button pattern below.

---

## 1. Colors

### 1.1 Brand
| Token | Value | Used for |
|---|---|---|
| **Brand blue** | `bg-blue-600` / `text-blue-600` | All primary actions, summary cards, active tab indicators, "Claim an Expense" / "Submit" buttons |
| Brand blue hover | `hover:brightness-110` | Standard hover for blue surfaces — never `bg-blue-700` |
| Brand blue press | `active:scale-[0.98]` | Tactile feedback on tap |

### 1.2 Section accent palette
Each functional section gets a coloured icon tile (see §3). Colour ↔ semantic mapping is consistent across the app:

| Theme | Icon tile | Active border | Used for |
|---|---|---|---|
| **Blue** | `bg-blue-50 text-blue-600 border-blue-100` | `border-blue-200` | Identity / "Claim for" / Category / primary metadata |
| **Violet** | `bg-violet-50 text-violet-600 border-violet-100` | `border-violet-200` | Dates / "When" / time-bound metadata · also the **Others** expense category |
| **Green** | `bg-green-50 text-green-600 border-green-100` | `border-green-200` | Approver / approval status / success states |
| **Emerald** | `bg-emerald-50 text-emerald-600 border-emerald-100` | `border-emerald-200` | Money in / Amount input / approved totals · also the **Calls** expense category (`bg-emerald-50`) |
| **Amber** | `bg-amber-50 text-amber-600 border-amber-100` | `border-amber-200` | Notes / Description / pending items · also the **Food** expense category |
| **Rose** | `bg-rose-50 text-rose-600 border-rose-100` | `border-rose-200` | Health / Medical · also rejection/destructive |
| **Sky** | `bg-sky-50 text-sky-600 border-sky-100` | `border-sky-200` | Travel / motion |
| **Gray** | `bg-gray-50 text-gray-600 border-gray-200` | `border-gray-200` | Attachments / neutral metadata |

Pastel-50 backgrounds + 600 text + 100 border is the recipe. Don't introduce 100/300/500 backgrounds for tiles — they break the consistency.

### 1.3 Status colours

| Status | Theme |
|---|---|
| Approved / Paid / Active | green |
| Pending / Requested / Awaiting | amber/orange |
| Rejected / Failed / Cancelled | red |
| Draft / Submitted (in queue) | blue |
| Inactive / Archived | gray |

Use the frappe-ui `<Badge>` with `theme="green|orange|red|blue|gray"` for these. Never paint status pills by hand.

---

## 2. Typography

| Use | Class |
|---|---|
| Page title | `text-base font-extrabold text-gray-900` |
| Section title (uppercase) | `text-sm font-black text-gray-900 uppercase tracking-[0.1em]` |
| Section subtitle | `text-[10px] font-bold text-gray-400 uppercase tracking-[0.05em]` |
| Field label | `text-sm leading-5 text-gray-700` (or wrapped in section title style) |
| Body / value | `text-sm font-extrabold text-gray-900` |
| Secondary value | `text-[11px] font-bold text-gray-500` |
| Helper text | `text-[11px] font-semibold text-gray-400` |
| Big amount display | `text-3xl font-black text-gray-900` |
| Button label (primary) | `font-black text-xs uppercase tracking-widest` |

Required-field marker: `<span class="text-red-500 ml-0.5">*</span>` immediately after the label, never as a CSS pseudo-element.

---

## 3. Section blocks

Every editable concern on a form is its own **section**. The pattern (locked in by the leave-application redesign) is:

```html
<section class="space-y-3">
  <div class="flex items-center gap-3">
    <div class="p-2.5 rounded-xl bg-{theme}-50 text-{theme}-600 shadow-sm border border-{theme}-100">
      <FeatherIcon name="{icon}" class="h-5 w-5" />
    </div>
    <div class="flex flex-col">
      <h3 class="text-sm font-black text-gray-900 uppercase tracking-[0.1em]">
        {{ __("Title") }}<span v-if="reqd" class="text-red-500 ml-0.5">*</span>
      </h3>
      <span class="text-[10px] font-bold text-gray-400 uppercase tracking-[0.05em]">
        {{ __("One-line subtitle that explains the section") }}
      </span>
    </div>
  </div>

  <!-- the input(s) for this section -->
</section>
```

Stack sections with `space-y-5` (20px) inside a `min-h-screen` body. Page padding is `px-4 pt-4 sm:px-5 sm:pt-5` and content max-width is `sm:max-w-4xl sm:mx-auto`.

---

## 4. Buttons

### 4.1 Primary (call-to-action)

The brand-blue native button. **This is the only correct primary button in the app.**

```html
<button
  type="button"
  @click="..."
  :disabled="..."
  class="w-full py-4 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50"
>
  <FeatherIcon name="send" class="h-4 w-4" />
  {{ __("Submit") }}
</button>
```

Width: `w-full` for sticky-bottom CTAs, `px-5` for inline pill buttons. Vertical padding: `py-4` (full-width) or `py-3` (inline).

### 4.2 Secondary (neutral)
```html
class="… bg-gray-100 text-gray-700 hover:bg-gray-200 …"
```
Same shape (`rounded-2xl`, `font-black uppercase tracking-widest`). Used for Cancel, Back, dismiss-without-action.

### 4.3 Destructive
Outline-style with rose tint — never solid red:
```html
class="… bg-red-50 text-red-600 border border-red-100 hover:bg-red-100 …"
```
Used for Delete inside a modal where the primary action sits next to it. Solid red is reserved for system-wide irreversible alerts only.

### 4.4 Ghost / icon
Round neutral button for top-bar close / nav:
```html
class="h-9 w-9 rounded-xl bg-gray-100 text-gray-600 flex items-center justify-center hover:bg-gray-200"
```

### 4.5 Disabled state
Always `disabled:opacity-50 disabled:cursor-not-allowed` — never re-paint to a darker bg.

---

## 5. Inputs

### 5.1 Base text input / textarea
```html
class="w-full rounded-2xl border border-gray-200 bg-white p-4 text-sm font-medium text-gray-800 focus:border-blue-300 focus:ring-2 focus:ring-blue-100 transition-all outline-none placeholder:text-gray-400"
```
Always `rounded-2xl`. Always 2px focus ring in `blue-100`. Never use `border-blue-500` on focus — too saturated.

### 5.2 Date input
**Never use native `<input type="date">`** — use frappe-ui's `<DatePicker>` (already wired into `FormField.vue`'s Date branch). The native picker's calendar UI clashes with the rest of the app.

### 5.3 Currency input
Big symbol prefix in `gray-300`, big number in `gray-900`. The amount is a centerpiece of the screen, treat it accordingly.

```html
<div class="flex items-center gap-3 rounded-2xl border-2 border-gray-100 bg-white px-5 py-4 focus-within:border-emerald-300 focus-within:ring-4 focus-within:ring-emerald-50">
  <span class="text-3xl font-black text-gray-300">{{ currencySymbol }}</span>
  <input
    type="number" inputmode="decimal" step="0.01"
    class="w-full bg-transparent border-0 text-3xl font-black text-gray-900 placeholder-gray-300 focus:outline-none focus:ring-0 p-0"
  />
</div>
```

### 5.4 Quick-add chips
Small pill buttons for "+₹100 / +₹500 / +₹1,000". Match the section's accent theme (emerald for amount, blue for category, etc.).
```html
class="px-3.5 py-2 rounded-full bg-emerald-50 text-emerald-700 text-xs font-bold hover:bg-emerald-100"
```

---

## 6. Cards

### 6.1 Surface card
```html
class="rounded-2xl border border-gray-100 bg-white px-4 py-3"
```
Used inside a section to wrap one piece of content.

### 6.2 Selectable card (radio-as-card)
Two-px border so the selected state is visible without changing layout:
```html
class="w-full rounded-2xl border-2 px-4 py-3 transition-all
       {{selected ? 'border-{theme}-500 bg-{theme}-50' : 'border-gray-100 bg-white hover:border-{theme}-200'}}"
```
On selection, render a `check-circle` icon at the right edge in the section's theme.

### 6.3 Avatar tile (for person rows)
```html
<div class="w-9 h-9 rounded-full bg-{theme}-100 text-{theme}-700 flex items-center justify-center font-black text-sm border border-{theme}-200">
  {{ initials(name) }}
</div>
```
Initials: first letter of up-to-two whitespace-separated tokens, uppercase. Always pair with name (extra-bold) + secondary line (semibold gray-500).

---

## 7. Empty states

A dashed rounded rectangle, oversized icon, single-line CTA. **No subtitle** — the icon + label is enough.

```html
<button class="w-full rounded-2xl border border-dashed border-gray-200 bg-gray-50/60 p-8 flex flex-col items-center justify-center gap-3 hover:border-blue-300 hover:bg-blue-50/60">
  <div class="h-16 w-16 rounded-3xl bg-white border border-gray-200 flex items-center justify-center text-gray-500 shadow-sm">
    <FeatherIcon name="plus" class="h-9 w-9" stroke-width="2.5" />
  </div>
  <div class="text-base font-bold text-gray-800">{{ __("Claim expense") }}</div>
</button>
```

---

## 8. Modals

### 8.1 Full-screen modal (preferred for forms)
Use Ionic's `<ion-modal>` **without** the `breakpoints` prop — that gives a proper full-screen page. Reserve the bottom-sheet / drawer style only for short pickers and filter overlays.

Top bar: 9×9 ghost close button on the left, centered title, equal-width spacer on the right for symmetry.

### 8.2 Success modal
Use the shared `<SuccessModal>` for any "request submitted" / "saved" celebration. Pulsing emerald check, big headline, optional subtitle, optional doc-name reference pill, primary blue CTA. Auto-dismisses after 2.5s (override with `:autoDismissMs="0"` if the surface needs a manual tap).

### 8.3 Confirmation dialog
Use frappe-ui `<Dialog>` for destructive confirms (Delete, Cancel, Submit-with-warning). Two buttons side by side: secondary (gray) + primary (blue). Never put the destructive action on the right — it's the secondary intent there.

---

## 9. Icons

Feather icons, sourced from frappe-ui's `<FeatherIcon>`. Sizes: `h-4 w-4` inline, `h-5 w-5` in section tiles, `h-9 w-9` in empty-state hero, `h-12 w-12` in success-modal hero. `stroke-width="2"` is the default; use `2.5` only for hero icons that need extra weight.

Don't mix icon libraries. If Feather doesn't have the glyph, find a different concept.

---

## 10. Spacing scale

| Token | Use |
|---|---|
| `gap-1.5` (6px) | between icon + tight label |
| `gap-2` (8px) | between chips in a row |
| `gap-3` (12px) | between icon-tile and section title block |
| `space-y-3` (12px) | within a section (header → input) |
| `space-y-5` (20px) | between sections on a form |
| `mt-5` / `mt-7` (20–28px) | between major dashboard blocks |

Page padding: `px-4 pt-4 sm:px-5 sm:pt-5`. Sticky-bottom CTA padding: `px-4 py-3 standalone:pb-safe-bottom`.

---

## 11. Anti-patterns — do not ship these

- ❌ `<Button variant="solid">` (renders dark gray — use the native blue button pattern).
- ❌ `<input type="date">` (native browser calendar — use `<DatePicker>` from frappe-ui).
- ❌ Solid red buttons (use rose-tinted outline for destructive in-modal actions).
- ❌ `bg-blue-700`, `bg-blue-500`, etc. for primary actions (only `bg-blue-600`).
- ❌ Mixing emoji with FeatherIcons (commit to one icon system).
- ❌ Status pills painted with custom Tailwind classes (use frappe-ui `<Badge>`).
- ❌ Subtitle text below empty-state CTAs (the icon + label is the message; extra copy is noise).
- ❌ Custom rounded radii — stick to the scale (`rounded-xl` 12px, `rounded-2xl` 16px, `rounded-3xl` 24px, `rounded-full`).
- ❌ Bottom-sheet drawers for full-form flows (use full-screen ion-modal).
- ❌ Toast for terminal success (insert + redirect) — use `<SuccessModal>` so the user gets a beat to register what happened.
- ❌ Chaining `frappe.client.insert` then `frappe.client.submit` from the client. Doctypes whose controllers update fields via `frappe.db.set_value` during save (Expense Claim's child totals, etc.) bump `modified` out-of-band, so the second call's `check_if_latest` trips with `TimestampMismatchError`. If you must commit-on-save, use `myhr.api.insert_and_submit` (one transaction). Better: prefer the **draft + Submit-for-Review** flow below.

---

## 11a. Submit pattern — draft first, submit on detail

Submittable doctypes (Expense Claim, Employee Action Centre, etc.) follow a two-step pattern that mirrors how the user thinks: *fill out → review → submit*.

1. **Save creates a draft** (docstatus 0). The form's primary CTA is "Save" — it inserts and routes to the detail view.
2. **Detail view shows a sticky "Submit for Review"** CTA at the bottom, gated on `docstatus === 0 && doc.owner === sessionUser()`. Tapping it calls `myhr.api.submit_doc(doctype, name)` to flip docstatus 0 → 1.
3. **Success modal pops** ("Claim submitted! / *Suresh Patel has been notified.*"), the detail page reloads with the fresh doc, banner re-renders to the submitted state.
4. **Approver acts on the submitted doc** via `approval_status` (which is `allow_on_submit`, so docstatus=1 doesn't block them).

Why not single-shot insert+submit? Two reasons:
- The user gets to *review* their work before committing — fewer panicked retractions, fewer half-done submissions.
- The flow is consistent with the EAC submit-for-review pattern the user already knows.

The single-shot endpoint (`myhr.api.insert_and_submit`) still exists as a primitive for surfaces where a draft preview adds no value. Use sparingly.

---

## 12. Where the rules live in code

| Concern | File |
|---|---|
| Date input | `components/FormField.vue` (Date branch uses `DatePicker`) |
| Section block pattern | `views/leave/Form.vue`, `views/expense_claim/Form.vue` |
| Primary button | `components/CheckInPanel.vue`, `components/PolicyBlockedModal.vue` (canonical examples) |
| Selectable card | `views/leave/Form.vue` (approver section), `components/ExpensesTable.vue` (category chips) |
| Empty state | `components/ExpensesTable.vue` |
| Success modal | `components/SuccessModal.vue` |
| Expense category meta (icon + theme) | `data/expenseClaimMeta.js` |

Anything new that touches buttons, inputs, sections, modals, or status colours must consult this doc first. If you find yourself hand-rolling a colour or radius, stop — pick the matching token from above.
