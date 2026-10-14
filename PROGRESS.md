# myHR PWA Revamp — Progress Log

## Snapshot
- **Before-night snapshot**: `apps/myhr/myhr/frontend_changes.snapshot.before_night.tar.gz` (use to roll back the entire night session)
- **Pre-redesign Form.vue backup**: `apps/myhr/myhr/frontend_changes/views/leave/Form.vue.bak.before_redesign`

## Critical infrastructure note
**Frappe-UI's Tailwind preset replaces Tailwind's color palette entirely.** Only `gray, blue, green, red, orange, yellow, teal, cyan, amber, pink, purple` compile.
- `indigo`, `violet`, `lime`, `emerald`, `sky`, `rose`, `slate`, `stone`, `zinc`, `neutral`, `fuchsia` do NOT exist
- Any `bg-indigo-*`, `text-indigo-*`, etc. silently renders nothing

## Design tokens — locked
- **Section header**: `<div class="p-2.5 rounded-xl bg-{tone}-50 text-{tone}-600 shadow-sm border border-{tone}-100">` icon tile + `text-sm font-black uppercase tracking-wide tracking-[0.1em]` title + `text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]` subtitle
- **Glassy header**: `bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-100 sticky top-0 z-50`
- **Page subtitle pattern**: blue dot `bg-blue-600` + `text-[10px] font-bold uppercase tracking-widest`
- **Primary CTA**: `w-full py-4 rounded-2xl bg-blue-600 text-white font-black text-xs uppercase tracking-widest hover:brightness-110 active:scale-[0.98] transition-all shadow-sm`
- **Secondary CTA**: `bg-white border-2 border-gray-200 text-gray-900 hover:border-blue-300 hover:text-blue-700`
- **Tonal banner**: `rounded-2xl border border-{tone}-200 bg-{tone}-50 px-4 py-3 flex items-start gap-3`
- **Card**: `rounded-2xl border border-gray-100 bg-white shadow-sm`
- **List row hover**: `hover:bg-blue-50/60 active:bg-blue-100/60`
- **Hero card**: solid `bg-blue-600` with white text + `bg-white/15` mini-tiles for stats
- **Status pill**: `text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md bg-{tone}-50 text-{tone}-600 border border-{tone}-100`

## Tonal palette (canonical usage)
- **Blue (primary)** — actions, selection, CTAs, primary section headers
- **Green** — success, approved, approver, contact info, employee checkin
- **Amber** — warnings, half-day, fixed holidays, pending requests, reason/explanation
- **Red** — errors, rejections, absent, log-out
- **Purple** — secondary accents (shifts, payroll period, company info)
- **Gray** — neutral, holidays bg, past dates, settings/utility
- **Pink** — (rarely used) — reserved

## Done before night session
(See bottom of file for full early-session log.)

## Night session (2026-04-28)

### Phase 1 — Profile + plumbing
- **`views/Profile.vue`**: full redesign. Glassy header, blue hero card with avatar+name+role+department+joined chips, four section cards (Employee Details/Company/Contact/Salary) with color-coded tile icons, polished red-bordered Log Out
- **`components/BottomTabs.vue`**: refined further. Glassy `bg-white/95 backdrop-blur-xl`, blue 2px top accent bar on active tab, active icon tile becomes `bg-blue-50 text-blue-700` and scales up 110%, hover state on inactive tabs
- **`components/ListView.vue`**: full redesign. Glassy sticky header, count subtitle ("N entries"), filter pill, primary blue New button (replaces stock variant="solid" black), list rows wrap in `rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden divide-y divide-gray-100` with `hover:bg-blue-50/60` rows

### Phase 2 — Expense Claim feature
- **`views/expense_claim/Dashboard.vue`**: glassy section headers (chart-bar tile for summary, credit-card tile for recent, trending-up for advances), primary blue "Claim an Expense" CTA, "View all" pill links
- **`components/ExpenseClaimSummary.vue`**: hero card pattern. Big total claimed at top, three mini-tiles (Pending/Approved/Rejected) with feather-icon dots
- **`components/ExpenseClaimItem.vue`**: status badge color map updated; `Draft` → `Requested` rename across all combos including `"Approved & Draft"` → `"Approved & Requested"`

### Phase 3 — Salary Slip feature
- **`views/salary_slip/Dashboard.vue`**: blue hero card showing Year-To-Date earnings, purple-tile section header for period picker, blue-tile section for slip list, `rounded-2xl divide-y` slip cards with hover, EmptyState for empty months
- **`views/salary_slip/Detail.vue`**: replaces the stock black "Download PDF" button with primary blue CTA (with download icon + loading indicator)
- **`components/SalarySlipItem.vue`**: blue icon tile, big month-year title, subtitle "Gross ₹X", right side "NET" label + bold net pay, chevron

### Phase 4 — Employee Checkin + Advance
- **`components/EmployeeCheckinItem.vue`**: redesign. Green tile for checkin, amber tile for checkout (visual differentiation by log_type), bigger title "Checked In" / "Checked Out"
- **`components/EmployeeAdvanceItem.vue`**: green tile, balance/paid breakdown, status badge with `Draft` → `Requested` rename
- **`components/EmployeeAdvanceBalance.vue`**: rounded-2xl card wrapping advances list with hover, secondary outline "Request an Advance" CTA below
- **`views/expense_claim/Dashboard.vue`** (cross-ref): wires EmployeeAdvanceBalance into "Advance Balance" section

### Phase 5 — Notifications + Settings + Login
- **`views/Notifications.vue`**: glassy header showing "N unread" or "All caught up", action bar with rounded pill buttons (Settings/Mark all read/Clear all) tinted appropriately, list rows in `rounded-2xl divide-y` card with absolute-positioned blue dot indicator for unread, blue-50 hover, ghost icon buttons for mark-read/dismiss
- **`views/AppSettings.vue`**: glassy header, blue-tile section header "Notifications · Push notifications and alerts", switch wrapped in proper card with loading state
- **`views/Login.vue`**: full redesign. Centered rounded-3xl card on FBFBFC bg, brand logo tile, "Welcome back" hero, blue CTA login button with icon, "or" divider with horizontal lines, OAuth provider buttons styled as bordered outline cards

### Phase 6 — QA sweep
- Replaced **all `indigo` color references → `blue`** in:
  - `views/EmployeeActionCentre.vue` (20 occurrences)
  - `views/EmployeeDirectory.vue` (2 occurrences)
  - `views/EmployeePolicies.vue` (1 occurrence)
- **`components/PolicyBlockedModal.vue`**: stock `variant="solid"` "Review & Acknowledge" + ghost "Not now" buttons replaced with primary blue + secondary outline pattern
- Status label rename "Draft" → "Requested" for ExpenseClaim, EmployeeAdvance (continuation of earlier work for Leave/Shift/Attendance)

## Files added to `frontend_sync.py` this session
```
views/Login.vue
views/expense_claim/Dashboard.vue
views/salary_slip/Dashboard.vue
views/salary_slip/Detail.vue
components/ExpenseClaimSummary.vue
components/ExpenseClaimItem.vue
components/SalarySlipItem.vue
components/EmployeeCheckinItem.vue
components/EmployeeAdvanceItem.vue
components/EmployeeAdvanceBalance.vue
```

## What's still stock (intentionally untouched, low priority)
- `views/InvalidEmployee.vue` — fallback page rarely seen
- `views/employee_advance/Form.vue` + List.vue — generic FormView/ListView (gets list polish through ListView overlay; form rebuild deferred)
- `views/expense_claim/Form.vue` + List.vue — same (Form is a child-table form, full rebuild deferred for safety; List inherits ListView polish)
- `views/attendance/ShiftAssignmentForm.vue` + List.vue — same (rarely opened by employees)
- `views/attendance/AttendanceRequestList.vue` / `EmployeeCheckinList.vue` — these still wrap stock ListView, so they inherit the new ListView styling automatically
- `views/leave/List.vue` — same; inherits ListView polish
- `components/WorkflowActionSheet.vue` "Actions" button — kept stock variant=solid since approve/reject buttons use theme colors meaningfully

## How to revert tonight's work entirely
```bash
cd /Users/abhay.nain/Desktop/Antigravity/ERP/ERP_Demo/apps/myhr/myhr
rm -rf frontend_changes
tar -xzf frontend_changes.snapshot.before_night.tar.gz
bench --site erp.localhost execute myhr.frontend_sync.apply_custom_ui
```

---

## Pre-night-session log (early sessions)
- Leave Application form (`views/leave/Form.vue`) — full custom redesign: glassy header, hero balance card, leave-type chip picker, inline range calendar with anchor/range flow, half-day chip toggle, contact-card approver, attachments tile, floating CTA dock
- Calendar tinting for leave form: holidays / optional / approved / pending leave shown with priority-ordered colors; selectability rules per leave type
- Backend: new whitelisted endpoint `myhr.api.get_leave_calendar_data(employee, from_date, to_date)`
- Demo seed data: 4 leave types × 10 active employees = 40 Leave Allocations for FY2026-27
- Shift Request form — custom redesign with shift-type chip picker, hero card, calendar
- Attendance Request form — custom redesign mirroring leave form (Reason chips, calendar, optional shift picker, explanation textarea)
- Holiday List page (`views/leave/HolidayList.vue`) — real route at `/holidays`, grouped by month, Fixed/Optional badges, weekly_off hidden, header + back button + bottom tabs visible
- Plumbing components redesigned: RequestList, ListItem, EmptyState, BottomTabs, TabButtons, QuickLinks, LeaveBalance, Holidays, AttendanceCalendar, RequestActionSheet (removed external-link arrow + made attachments tappable)
- Status label rename: "Open" → "Requested" across LeaveRequestItem, ShiftRequestItem, AttendanceRequestItem, ShiftAssignmentItem
- CTA buttons across leave/Dashboard, attendance/Dashboard, CheckInPanel
- Demo seed: 3 extra Shift Types added
