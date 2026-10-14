<template>
	<ion-page>
		<ListView
			doctype="Attendance Request"
			:pageTitle="__('Attendance Request History')"
			:tabButtons="TAB_BUTTONS"
			:fields="ATTENDANCE_REQUEST_FIELDS"
			:filterConfig="FILTER_CONFIG"
		/>
	</ion-page>
</template>

<script setup>
import { IonPage } from "@ionic/vue"
import ListView from "@/components/ListView.vue"
import { inject } from "vue"

const __ = inject("$translate")

// Stock HRMS's AttendanceRequestList omitted `tabButtons`, so the page
// hard-coded the filter to `employee == current_employee` and an approver
// could never see their reports' Attendance Requests on the View All page.
// Sibling lists (Leave / Expense Claim / Shift Request) all expose a
// My / Team tab pair — adding the same here for parity.
const TAB_BUTTONS = ["My Requests", "Team Requests"] // __("My Requests"), __("Team Requests")
const ATTENDANCE_REQUEST_FIELDS = ["name", "employee", "employee_name", "reason", "from_date", "to_date", "docstatus"]
const FILTER_CONFIG = [
	{
		fieldname: "shift",
		fieldtype: "Link",
		label: __("Shift"),
		options: "Shift Type",
	},
	{ fieldname: "from_date", fieldtype: "Date", label: __("From Date") },
	{ fieldname: "to_date", fieldtype: "Date", label: __("To Date") },
]
</script>
