<template>
	<BaseLayout>
		<template #body>
			<div class="flex flex-col items-center my-7 p-4 gap-5">
				<CheckInPanel />

				<!-- Pending policies banner — shown when employee has unacknowledged policies -->
				<router-link
					v-if="policyCounts.count > 0"
					:to="{ name: 'EmployeePolicies' }"
					class="w-full"
				>
					<div
						class="rounded-2xl px-4 py-3 flex items-start gap-3 border shadow-sm transition-all hover:shadow-md"
						:class="
							policyCounts.blocking_count > 0
								? 'bg-red-50 border-red-200'
								: 'bg-amber-50 border-amber-200'
						"
					>
						<FeatherIcon
							:name="policyCounts.blocking_count > 0 ? 'alert-triangle' : 'shield'"
							class="h-5 w-5 mt-0.5 shrink-0"
							:class="
								policyCounts.blocking_count > 0 ? 'text-red-600' : 'text-amber-600'
							"
						/>
						<div class="flex-1 min-w-0">
							<div
								class="text-sm font-extrabold"
								:class="
									policyCounts.blocking_count > 0
										? 'text-red-900'
										: 'text-amber-900'
								"
							>
								{{ policyCounts.count }}
								{{ policyCounts.count === 1 ? __("policy") : __("policies") }}
								{{ __("pending acknowledgement") }}
							</div>
							<div
								class="text-xs mt-0.5"
								:class="
									policyCounts.blocking_count > 0
										? 'text-red-800'
										: 'text-amber-800'
								"
							>
								{{
									policyCounts.blocking_count > 0
										? __(
												"Some are required before you can check in. Tap to review.",
											)
										: __("Tap to review and acknowledge.")
								}}
							</div>
						</div>
						<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400 mt-1.5" />
					</div>
				</router-link>

				<!-- Action Centre draft card — surfaces an open AC so the employee can return to it. -->
				<router-link
					v-if="acCardVisible"
					:to="{ name: 'EmployeeActionCentre' }"
					class="w-full"
				>
					<div
						class="rounded-2xl px-4 py-3 flex items-start gap-3 border border-blue-200 bg-blue-50 shadow-sm transition-all hover:shadow-md"
					>
						<ActionCentreIcon class="h-5 w-5 mt-0.5 shrink-0 text-blue-600" />
						<div class="flex-1 min-w-0">
							<div class="text-sm font-extrabold text-blue-900">
								{{ __("Action Centre") }}
							</div>
							<div class="text-xs mt-0.5 text-blue-800">
								{{ acCardLabel }}
							</div>
						</div>
						<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400 mt-1.5" />
					</div>
				</router-link>

				<QuickLinks :items="quickLinks" :title="__('Quick Links')" />
				<RequestPanel />
			</div>

			<PolicyBlockedModal
				:is-open="policyModalOpen"
				:policies="blockingPolicies"
				:action-label="__('submit an attendance request')"
				@close="policyModalOpen = false"
			/>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject, markRaw, computed, ref } from "vue";
import { useRouter } from "vue-router";
import { onIonViewWillEnter } from "@ionic/vue";

import { createResource, FeatherIcon } from "frappe-ui";

import CheckInPanel from "@/components/CheckInPanel.vue";
import QuickLinks from "@/components/QuickLinks.vue";
import BaseLayout from "@/components/BaseLayout.vue";
import RequestPanel from "@/components/RequestPanel.vue";
import PolicyBlockedModal from "@/components/PolicyBlockedModal.vue";
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue";
import ShiftIcon from "@/components/icons/ShiftIcon.vue";
import LeaveIcon from "@/components/icons/LeaveIcon.vue";
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue";
import EmployeeAdvanceIcon from "@/components/icons/EmployeeAdvanceIcon.vue";
import SalaryIcon from "@/components/icons/SalaryIcon.vue";
import DirectoryIcon from "@/components/icons/DirectoryIcon.vue";
import ActionCentreIcon from "@/components/icons/ActionCentreIcon.vue";

const __ = inject("$translate");
const router = useRouter();

// Pending counts for the Action Centre quick-link badge.
const actionCentreSummary = createResource({
	url: "myhr.api.get_employee_action_centre",
	auto: true,
});

// Resignations waiting on this user as L1 or L2. Returns [] for everyone who
// is not an approver, so the quick link simply never appears for them.
const resignationApprovals = createResource({
	url: "myhr.clearance_api.get_my_separation_inbox",
	auto: true,
});

// Pending counts for the Policies banner + quick-link badge.
const policyCountResource = createResource({
	url: "myhr.api.get_pending_policy_count",
	auto: true,
});

const policyCounts = computed(() => policyCountResource.data || { count: 0, blocking_count: 0 });

const resignationApprovalCount = computed(() => (resignationApprovals.data || []).length);

const acCardVisible = computed(() => {
	const ac = actionCentreSummary.data;
	if (!ac || ac.error) return false;
	if (ac.submitted_for_review) return false;
	if (ac.status === "Accepted") return false;
	return true;
});

const acCardLabel = computed(() => {
	const ac = actionCentreSummary.data;
	if (!ac) return __("Start your details");
	if (!ac.custom_last_saved_at) return __("Start your details");
	return __("Draft saved {0}", [relativeTime(ac.custom_last_saved_at)]);
});

function relativeTime(iso) {
	if (!iso) return "";
	const d = new Date(iso.replace(" ", "T"));
	const diffMs = Date.now() - d.getTime();
	const m = Math.round(diffMs / 60000);
	if (m < 1) return __("just now");
	if (m < 60) return __("{0}m ago", [m]);
	const h = Math.round(m / 60);
	if (h < 24) return __("{0}h ago", [h]);
	const days = Math.round(h / 24);
	return __("{0}d ago", [days]);
}

// Refresh resources every time the user returns to Home from an inner page (e.g., after
// acknowledging a policy or submitting Action Centre, the badge counts should be live).
onIonViewWillEnter(() => {
	actionCentreSummary.reload();
	policyCountResource.reload();
	// Easy to miss: this one is `auto: true`, so without an explicit reload it
	// fetches once on first mount and never again. The Separation Approvals tile
	// would keep its badge after the manager had already approved the
	// resignation or completed the handover, with an empty list behind it.
	resignationApprovals.reload();
});

const policyModalOpen = ref(false);
const blockingPolicies = ref([]);

const attendanceRequestGate = createResource({
	url: "myhr.api.can_open_attendance_request",
	auto: false,
});

async function handleAttendanceRequestClick() {
	await attendanceRequestGate.reload();
	const result = attendanceRequestGate.data || {};

	if (result.allowed) {
		router.push({ name: "AttendanceRequestFormView" });
		return;
	}

	// Pre-flight gate failed — show modal listing the blocking policies.
	blockingPolicies.value = result.blocking || [];
	policyModalOpen.value = true;
}

function actionCentrePendingCount(ac) {
	if (!ac || ac.error) return 0;
	let n = 0;
	const done = (s) => s === "Accepted" || s === "Awaiting HR";
	for (const d of ac.documents || []) {
		if (!done(d.status)) n++;
	}
	for (const e of ac.employers || []) {
		// Most Recent Employer (slot 1) is always required, so always counts.
		if (e.key === "employer_1") {
			if (!done(e.status)) n++;
			continue;
		}
		// Previous Employer slots (2-5) only count once the user has started
		// filling them — empty slots are hidden in the UI (and a fresher's
		// slots are auto-N/A on the server) so they shouldn't show up as
		// outstanding tasks on the Home badge.
		const started = !!(
			e.is_na ||
			e.file ||
			(e.name && String(e.name).trim()) ||
			e.from_date ||
			e.till_date
		);
		if (started && !done(e.status)) n++;
	}
	return n;
}

const quickLinks = computed(() => {
	const acPending = actionCentrePendingCount(actionCentreSummary.data);
	const policyPending = policyCounts.value.count;

	return [
		// 1) Inbox / pending — always first
		{
			group: "inbox",
			icon: markRaw(ActionCentreIcon),
			title: __("Action Centre"),
			route: "EmployeeActionCentre",
			...(acPending > 0 ? { badge: acPending } : {}),
		},
		// 1b) Resignation approvals — shown only while something is actually
		// waiting on this user as L1 or L2.
		...(resignationApprovalCount.value > 0
			? [
					{
						group: "inbox",
						icon: markRaw(ActionCentreIcon),
						title: __("Separation Approvals"),
						route: "ResignationApprovals",
						badge: resignationApprovalCount.value,
					},
				]
			: []),
		// 2) Self-service requests — ordered by frequency of use
		{
			group: "requests",
			icon: markRaw(LeaveIcon),
			title: __("Request Leave"),
			route: "LeaveApplicationFormView",
		},
		{
			group: "requests",
			icon: markRaw(AttendanceIcon),
			title: __("Request Attendance"),
			onClick: handleAttendanceRequestClick,
		},
		{
			group: "requests",
			icon: markRaw(ShiftIcon),
			title: __("Request a Shift"),
			route: "ShiftRequestFormView",
		},
		{
			group: "requests",
			icon: markRaw(ExpenseIcon),
			title: __("Claim an Expense"),
			route: "ExpenseClaimFormView",
		},
		// 3) Browse / reference
		{
			group: "browse",
			icon: markRaw(SalaryIcon),
			title: __("View Salary Slips"),
			route: "SalarySlipsDashboard",
		},
		{
			group: "browse",
			icon: markRaw(DirectoryIcon),
			title: __("Employee Directory"),
			route: "EmployeeDirectory",
		},
		{
			group: "browse",
			icon: markRaw(FeatherIcon),
			iconName: "shield",
			title: __("Policy Centre"),
			route: "EmployeePolicies",
			...(policyPending > 0 ? { badge: policyPending } : {}),
		},
		{
			group: "browse",
			icon: markRaw(FeatherIcon),
			iconName: "percent",
			title: __("Tax Declaration"),
			route: "TaxDeclaration",
		},
		// 4) Setup utility — last
		{
			group: "utility",
			icon: markRaw(FeatherIcon),
			iconName: "download",
			title: __("Install My HR App"),
			onClick: () =>
				window.triggerPWAInstall
					? window.triggerPWAInstall()
					: alert("Installation only available on mobile browsers or Chrome/Edge."),
		},
	];
});
</script>
