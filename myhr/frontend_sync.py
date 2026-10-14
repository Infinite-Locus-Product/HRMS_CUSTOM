import os
import shutil
import subprocess

import frappe
from frappe.utils import get_bench_path


def apply_custom_ui():
    """Apply custom UI from myhr to hrms and rebuild. Paths use bench root (site-independent)."""
    print("Applying custom UI from myhr to hrms and rebuilding...")
    bench_root = get_bench_path()
    source_base = os.path.join(bench_root, "apps", "myhr", "myhr", "frontend_changes")
    target_base = os.path.join(bench_root, "apps", "hrms", "frontend", "src")

    files_to_sync = [
        ("data/config/requestSummaryFields.js", "data/config/requestSummaryFields.js"),
        # Shared display config for Expense Claim Type categories (icon +
        # theme colour). Keeps the modal chips, line-item rows, and
        # dashboard row icons visually consistent.
        ("data/expenseClaimMeta.js", "data/expenseClaimMeta.js"),
        ("components/FormattedField.vue", "components/FormattedField.vue"),
        # FormField overlay — swaps the native HTML5 date picker for
        # frappe-ui's popover DatePicker (stock had a `FIXME: default
        # datepicker has poor UI` comment). All Date fields across leave,
        # attendance, expense, etc. share this widget.
        ("components/FormField.vue", "components/FormField.vue"),
        ("components/BaseLayout.vue", "components/BaseLayout.vue"),
        ("components/FormView.vue", "components/FormView.vue"),
        ("components/ListView.vue", "components/ListView.vue"),
        ("components/WorkflowActionSheet.vue", "components/WorkflowActionSheet.vue"),
        ("views/Profile.vue", "views/Profile.vue"),
        # Employee-initiated resignation screen (Stage A) + its Profile entry.
        ("views/Resignation.vue", "views/Resignation.vue"),
        # L1 / L2 approval queue for resignations.
        ("views/ResignationApprovals.vue", "views/ResignationApprovals.vue"),
        # Manager Clearance: the leaver's handover form and the manager's review.
        ("views/Handover.vue", "views/Handover.vue"),
        ("views/ClearanceReview.vue", "views/ClearanceReview.vue"),
        # IT Clearance, read-only for the leaver and their manager.
        ("views/ITClearance.vue", "views/ITClearance.vue"),
        # Full & Final settlement, read-only for the leaver.
        ("views/Settlement.vue", "views/Settlement.vue"),
        # HR clearance + relieving letter, read-only for the leaver.
        ("views/HRClearance.vue", "views/HRClearance.vue"),
        # Tax centre: regime choice + exemption declaration.
        ("views/TaxDeclaration.vue", "views/TaxDeclaration.vue"),
        ("views/IncomeTaxSlab.vue", "views/IncomeTaxSlab.vue"),
        ("views/TaxExemptionDeclaration.vue", "views/TaxExemptionDeclaration.vue"),
        ("views/Notifications.vue", "views/Notifications.vue"),
        ("views/AppSettings.vue", "views/AppSettings.vue"),
        ("components/BottomTabs.vue", "components/BottomTabs.vue"),
        ("components/CheckInPanel.vue", "components/CheckInPanel.vue"),
        ("components/AttendanceCalendar.vue", "components/AttendanceCalendar.vue"),
        ("components/RequestList.vue", "components/RequestList.vue"),
        ("components/ListItem.vue", "components/ListItem.vue"),
        ("components/EmptyState.vue", "components/EmptyState.vue"),
        ("components/TabButtons.vue", "components/TabButtons.vue"),
        ("components/LeaveBalance.vue", "components/LeaveBalance.vue"),
        ("components/Holidays.vue", "components/Holidays.vue"),
        ("components/AttendanceRequestItem.vue", "components/AttendanceRequestItem.vue"),
        ("components/ShiftAssignmentItem.vue", "components/ShiftAssignmentItem.vue"),
        ("components/ShiftRequestItem.vue", "components/ShiftRequestItem.vue"),
        ("views/leave/HolidayList.vue", "views/leave/HolidayList.vue"),
        ("views/Login.vue", "views/Login.vue"),
        ("views/expense_claim/Dashboard.vue", "views/expense_claim/Dashboard.vue"),
        ("views/salary_slip/Dashboard.vue", "views/salary_slip/Dashboard.vue"),
        ("views/salary_slip/Detail.vue", "views/salary_slip/Detail.vue"),
        ("components/ExpenseClaimSummary.vue", "components/ExpenseClaimSummary.vue"),
        ("components/ExpenseClaimItem.vue", "components/ExpenseClaimItem.vue"),
        ("components/SalarySlipItem.vue", "components/SalarySlipItem.vue"),
        ("components/EmployeeCheckinItem.vue", "components/EmployeeCheckinItem.vue"),
        ("components/EmployeeAdvanceItem.vue", "components/EmployeeAdvanceItem.vue"),
        ("components/EmployeeAdvanceBalance.vue", "components/EmployeeAdvanceBalance.vue"),
        ("components/PolicyBlockedModal.vue", "components/PolicyBlockedModal.vue"),
        # Mobile-safe document preview modal (PDF.js lazy-loaded from CDN +
        # image inline + external-link fallback). Replaces the plain iframe
        # that only rendered first PDF page on iOS Safari / Android Chrome.
        # Shared by EmployeePolicies and EmployeeActionCentre.
        ("components/DocumentPreviewModal.vue", "components/DocumentPreviewModal.vue"),
        ("views/Home.vue", "views/Home.vue"),
        ("views/leave/Form.vue", "views/leave/Form.vue"),
        ("views/leave/Dashboard.vue", "views/leave/Dashboard.vue"),
        ("views/attendance/Dashboard.vue", "views/attendance/Dashboard.vue"),
        ("views/attendance/AttendanceRequestForm.vue", "views/attendance/AttendanceRequestForm.vue"),
        ("views/attendance/AttendanceRequestList.vue", "views/attendance/AttendanceRequestList.vue"),
        ("views/attendance/ShiftRequestForm.vue", "views/attendance/ShiftRequestForm.vue"),
        ("router/index.js", "router/index.js"),
        ("views/EmployeeDirectory.vue", "views/EmployeeDirectory.vue"),
        ("views/EmployeeActionCentre.vue", "views/EmployeeActionCentre.vue"),
        ("views/EmployeePolicies.vue", "views/EmployeePolicies.vue"),
        ("views/TabbedView.vue", "views/TabbedView.vue"),
        ("components/QuickLinks.vue", "components/QuickLinks.vue"),
        ("components/RequestActionSheet.vue", "components/RequestActionSheet.vue"),
        ("components/LeaveRequestItem.vue", "components/LeaveRequestItem.vue"),
        ("components/AttendanceRequestDetailView.vue", "components/AttendanceRequestDetailView.vue"),
        ("components/LeaveApplicationDetailView.vue", "components/LeaveApplicationDetailView.vue"),
        ("components/ShiftRequestDetailView.vue", "components/ShiftRequestDetailView.vue"),
        ("components/ExpenseClaimDetailView.vue", "components/ExpenseClaimDetailView.vue"),
        ("components/ExpensesTable.vue", "components/ExpensesTable.vue"),
        ("views/expense_claim/Form.vue", "views/expense_claim/Form.vue"),
        ("components/InstallPrompt.vue", "components/InstallPrompt.vue"),
        ("components/DesktopSidebar.vue", "components/DesktopSidebar.vue"),
        ("components/icons/DirectoryIcon.vue", "components/icons/DirectoryIcon.vue"),
        ("components/icons/ActionCentreIcon.vue", "components/icons/ActionCentreIcon.vue"),
        ("components/icons/ExpenseIcon.vue", "components/icons/ExpenseIcon.vue"),
        # Global error modal infrastructure — replaces stacked alert-circle toasts
        # with a single dismissable modal + Frappe-error message sanitizer.
        ("App.vue", "App.vue"),
        ("components/ErrorModal.vue", "components/ErrorModal.vue"),
        ("data/errorModal.js", "data/errorModal.js"),
        # Celebratory success modal — replaces toast-then-redirect on
        # Leave / AR / Expense submission.
        ("components/SuccessModal.vue", "components/SuccessModal.vue"),
    ]

    for src, tgt in files_to_sync:
        src_path = os.path.join(source_base, src)
        tgt_path = os.path.join(target_base, tgt)
        os.makedirs(os.path.dirname(tgt_path), exist_ok=True)
        print(f"Syncing {src_path} -> {tgt_path}", flush=True)
        shutil.copy(src_path, tgt_path)

    print("\n📦 Rebuilding HRMS frontend...", flush=True)
    frontend_dir = os.path.join(bench_root, "apps", "hrms", "frontend")
    result = subprocess.run(["yarn", "build"], cwd=frontend_dir)
    if result.returncode != 0:
        raise RuntimeError(f"yarn build failed with exit code {result.returncode}")

    # Current migrate site only; no hardcoded site name
    if getattr(frappe.local, "site", None):
        frappe.clear_cache()
        site = frappe.local.site
    else:
        site = None
    print(
        f"\n✅ Custom UI applied successfully! (site={site or 'cache clear skipped — run in bench context'})",
        flush=True,
    )


if __name__ == "__main__":
    site = os.environ.get("FRAPPE_SITE")
    if site:
        frappe.init(site=site)
        frappe.connect()
    try:
        apply_custom_ui()
    finally:
        if site:
            frappe.destroy()
