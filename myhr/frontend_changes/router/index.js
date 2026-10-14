import { createRouter, createWebHistory } from "@ionic/vue-router"

import TabbedView from "@/views/TabbedView.vue"
import attendanceRoutes from "./attendance"
import leaveRoutes from "./leaves"
import claimRoutes from "./claims"
import employeeAdvanceRoutes from "./advances"
import salarySlipRoutes from "./salary_slips"

// Routes that render WITH the bottom tab bar (list / browse pages — users may
// bounce to another section). Forms & detail/edit views stay top-level so the
// focused task flow owns the bottom edge (Save button + workflow action sheet).
const TABBED_LIST_ROUTE_NAMES = new Set([
	"LeaveApplicationListView",
	"ExpenseClaimListView",
	"AttendanceRequestListView",
	"ShiftRequestListView",
	"ShiftAssignmentListView",
	"EmployeeCheckinListView",
	"EmployeeAdvanceListView",
	"HolidayListView",
])

// myhr-only routes that aren't part of the per-feature router files.
const myhrExtraRoutes = [
	{
		name: "HolidayListView",
		path: "/holidays",
		component: () => import("@/views/leave/HolidayList.vue"),
	},
]

const allModuleRoutes = [
	...attendanceRoutes,
	...leaveRoutes,
	...claimRoutes,
	...employeeAdvanceRoutes,
	...salarySlipRoutes,
	...myhrExtraRoutes,
]
const tabbedListRoutes = allModuleRoutes.filter((r) =>
	TABBED_LIST_ROUTE_NAMES.has(r.name)
)
const standaloneFormRoutes = allModuleRoutes.filter(
	(r) => !TABBED_LIST_ROUTE_NAMES.has(r.name)
)

const routes = [
	{
		path: "/",
		component: TabbedView,
		children: [
			{ path: "", redirect: "/home" },
			{
				path: "/home",
				name: "Home",
				component: () => import("@/views/Home.vue"),
			},
			{
				path: "/dashboard/attendance",
				name: "AttendanceDashboard",
				component: () => import("@/views/attendance/Dashboard.vue"),
			},
			{
				path: "/dashboard/leaves",
				name: "LeavesDashboard",
				component: () => import("@/views/leave/Dashboard.vue"),
			},
			{
				path: "/dashboard/expense-claims",
				name: "ExpenseClaimsDashboard",
				component: () => import("@/views/expense_claim/Dashboard.vue"),
			},
			{
				path: "/dashboard/salary-slips",
				name: "SalarySlipsDashboard",
				component: () => import("@/views/salary_slip/Dashboard.vue"),
			},
			{
				path: "/directory",
				name: "EmployeeDirectory",
				component: () => import("@/views/EmployeeDirectory.vue"),
			},
			{
				path: "/action-centre",
				name: "EmployeeActionCentre",
				component: () => import("@/views/EmployeeActionCentre.vue"),
			},
			{
				path: "/policies",
				name: "EmployeePolicies",
				component: () => import("@/views/EmployeePolicies.vue"),
			},
			// Browse / list pages — bottom tab bar visible
			...tabbedListRoutes,
			// Utility pages — bottom tab bar visible
			{
				// Employee-initiated resignation (Stage A). Reached from the
				// Profile screen; the approval routing itself is owned by the
				// Employee Separation Approval workflow.
				path: "/resignation",
				name: "Resignation",
				component: () => import("@/views/Resignation.vue"),
			},
			{
				// L1 / L2 queue. Which rows appear is decided server-side by the
				// workflow state plus who is named on the record.
				path: "/resignation-approvals",
				name: "ResignationApprovals",
				component: () => import("@/views/ResignationApprovals.vue"),
			},
			{
				// The leaver's handover half of the Manager Clearance.
				path: "/handover",
				name: "Handover",
				component: () => import("@/views/Handover.vue"),
			},
			{
				// The reporting manager's review of one handover.
				path: "/handover/:name",
				name: "ClearanceReview",
				component: () => import("@/views/ClearanceReview.vue"),
			},
			{
				// Read-only: what IT recorded, including any recovery amount.
				path: "/it-clearance",
				name: "ITClearance",
				component: () => import("@/views/ITClearance.vue"),
			},
			{
				// Read-only: the leaver's own final settlement. Deliberately not
				// shared with their manager — it itemises their pay.
				path: "/settlement",
				name: "Settlement",
				component: () => import("@/views/Settlement.vue"),
			},
			{
				// Read-only: exit interview, items to return, and the relieving
				// letter. Leaver-only — it sits beside re-hire eligibility, which
				// they must never see.
				path: "/hr-clearance",
				name: "HRClearance",
				component: () => import("@/views/HRClearance.vue"),
			},
			{
				// Tax centre: regime choice + exemption declaration.
				path: "/tax-declaration",
				name: "TaxDeclaration",
				component: () => import("@/views/TaxDeclaration.vue"),
			},
			{
				path: "/tax-declaration/slab",
				name: "IncomeTaxSlab",
				component: () => import("@/views/IncomeTaxSlab.vue"),
			},
			{
				path: "/tax-declaration/exemptions",
				name: "TaxExemptionDeclaration",
				component: () => import("@/views/TaxExemptionDeclaration.vue"),
			},
			{
				path: "/profile",
				name: "Profile",
				component: () => import("@/views/Profile.vue"),
			},
			{
				path: "/notifications",
				name: "Notifications",
				component: () => import("@/views/Notifications.vue"),
			},
			{
				path: "/settings",
				name: "Settings",
				component: () => import("@/views/AppSettings.vue"),
			},
		],
	},
	// Out-of-nav pages — no tab bar
	{
		path: "/login",
		name: "Login",
		component: () => import("@/views/Login.vue"),
	},
	{
		path: "/invalid-employee",
		name: "InvalidEmployee",
		component: () => import("@/views/InvalidEmployee.vue"),
	},
	// Form / detail / edit views — focused task flows, no tab bar
	...standaloneFormRoutes,
]

const router = createRouter({
	history: createWebHistory("/hrms"),
	routes,
})

export default router
