<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<!-- Detail / view flow uses the polished read-only DetailView. The
			     stock FormView surfaces every doctype field — including audit
			     fields the employee should not be touching — so we replace it
			     with a card-based summary that matches the apply-flow styling. -->
			<LeaveApplicationDetailView
				v-if="props.id"
				:id="props.id"
			/>

			<!-- TEMP REDESIGN: new-application flow gets the Action-Centre styling -->
			<div
				v-else-if="formFields.data"
				class="bg-[#FBFBFC] min-h-screen pb-[120px]"
			>
				<div
					class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative"
				>
					<!-- Glassy sticky header (Action-Centre pattern) -->
					<div
						class="flex flex-row bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100 items-center gap-1"
					>
						<Button
							variant="ghost"
							class="!px-2 hover:bg-gray-100 transition-colors"
							@click="router.back()"
						>
							<FeatherIcon
								name="chevron-left"
								class="h-6 w-6 text-gray-700"
							/>
						</Button>
						<div class="flex flex-col ml-1 overflow-hidden">
							<h2
								class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1"
							>
								{{ __("New Leave Application") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span
									class="text-[10px] font-bold uppercase tracking-widest"
									>{{ __("Apply for time off") }}</span
								>
							</div>
						</div>
					</div>

					<!-- Body -->
					<div class="flex-1 px-4 py-5 sm:p-5 space-y-5">
						<!-- Contextual banner (Action-Centre tonal pattern) -->
						<div
							v-if="banner.tone === 'blue'"
							class="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 flex items-start gap-3"
						>
							<FeatherIcon
								name="info"
								class="h-5 w-5 text-blue-600 mt-0.5 shrink-0"
							/>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-extrabold text-blue-900">
									{{ banner.title }}
								</div>
								<div class="text-xs text-blue-800 mt-0.5">
									{{ banner.subtitle }}
								</div>
							</div>
						</div>
						<div
							v-else-if="banner.tone === 'amber'"
							class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-3"
						>
							<FeatherIcon
								name="alert-triangle"
								class="h-5 w-5 text-amber-600 mt-0.5 shrink-0"
							/>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-extrabold text-amber-900">
									{{ banner.title }}
								</div>
								<div class="text-xs text-amber-800 mt-0.5">
									{{ banner.subtitle }}
								</div>
							</div>
						</div>
						<div
							v-else-if="banner.tone === 'red'"
							class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 flex items-start gap-3"
						>
							<FeatherIcon
								name="alert-circle"
								class="h-5 w-5 text-red-600 mt-0.5 shrink-0"
							/>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-extrabold text-red-900">
									{{ banner.title }}
								</div>
								<div class="text-xs text-red-800 mt-0.5">
									{{ banner.subtitle }}
								</div>
							</div>
						</div>
						<div
							v-else-if="banner.tone === 'green'"
							class="rounded-2xl border border-green-200 bg-green-50 px-4 py-3 flex items-start gap-3"
						>
							<FeatherIcon
								name="check-circle"
								class="h-5 w-5 text-green-600 mt-0.5 shrink-0"
							/>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-extrabold text-green-900">
									{{ banner.title }}
								</div>
								<div class="text-xs text-green-800 mt-0.5">
									{{ banner.subtitle }}
								</div>
							</div>
						</div>

						<!-- Hero balance card — solid blue, Action-Centre primary -->
						<div
							v-if="leaveApplication.leave_type"
							class="rounded-2xl bg-blue-600 p-5 text-white shadow-sm"
						>
							<div class="flex items-start justify-between gap-3">
								<div class="min-w-0">
									<div
										class="text-[10px] font-black uppercase tracking-widest text-white/80 truncate"
									>
										{{ leaveApplication.leave_type }}
									</div>
									<div class="mt-1 flex items-end gap-2">
										<div class="text-3xl font-black leading-none">
											{{
												leaveApplication.leave_balance != null
													? leaveApplication.leave_balance
													: "—"
											}}
										</div>
										<div class="text-xs font-bold text-white/80 mb-0.5">
											{{ __("days available") }}
										</div>
									</div>
								</div>
								<div
									class="rounded-xl bg-white/15 px-3 py-2 shrink-0 text-right"
								>
									<div
										class="text-[9px] font-black uppercase tracking-widest text-white/80"
									>
										{{ __("Leave Balance") }}
									</div>
									<FeatherIcon
										name="trending-up"
										class="h-5 w-5 text-white mt-0.5 ml-auto"
									/>
								</div>
							</div>
							<div class="mt-4 grid grid-cols-2 gap-2">
								<div class="rounded-xl bg-white/15 px-3 py-2">
									<div
										class="text-[9px] font-black uppercase tracking-widest text-white/80"
									>
										{{ __("Requesting") }}
									</div>
									<div class="text-sm font-extrabold mt-0.5">
										{{ leaveApplication.total_leave_days || 0 }}
										{{ __("days") }}
									</div>
								</div>
								<div class="rounded-xl bg-white/15 px-3 py-2">
									<div
										class="text-[9px] font-black uppercase tracking-widest text-white/80"
									>
										{{ __("After this") }}
									</div>
									<div
										class="text-sm font-extrabold mt-0.5"
										:class="{
											'text-red-200':
												remainingAfter != null && remainingAfter < 0,
										}"
									>
										{{ remainingAfter != null ? remainingAfter : "—" }}
										{{ __("days") }}
									</div>
								</div>
							</div>
						</div>

						<!-- Section: Leave Type -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
								>
									<FeatherIcon name="tag" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Leave Type") }}
										<span class="text-red-500 ml-0.5">*</span>
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Pick what kind of leave you need") }}
									</span>
								</div>
							</div>
							<div
								v-if="!leaveTypeOptions.length"
								class="rounded-2xl border border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-center text-xs font-bold uppercase tracking-widest text-gray-400"
							>
								{{ __("Loading leave types…") }}
							</div>
							<div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-2">
								<button
									v-for="type in leaveTypeOptions"
									:key="type.value"
									type="button"
									@click="leaveApplication.leave_type = type.value"
									class="rounded-xl border-2 px-3 py-3 text-left transition-all min-h-[64px] flex items-center gap-2"
									:class="[
										leaveApplication.leave_type === type.value
											? 'border-blue-600 bg-blue-50 shadow-sm'
											: 'border-gray-100 bg-white hover:border-blue-200',
									]"
								>
									<div
										class="p-1.5 rounded-lg shrink-0"
										:class="[
											leaveApplication.leave_type === type.value
												? 'bg-blue-600 text-white'
												: 'bg-gray-100 text-gray-500',
										]"
									>
										<FeatherIcon
											:name="leaveTypeIcon(type.value)"
											class="h-3.5 w-3.5"
										/>
									</div>
									<div
										class="text-[13px] font-extrabold leading-tight min-w-0"
										:class="
											leaveApplication.leave_type === type.value
												? 'text-blue-900'
												: 'text-gray-800'
										"
									>
										{{ type.label }}
									</div>
								</button>
							</div>
						</section>

						<!-- Section: Dates -->
						<section class="space-y-3">
							<div class="flex items-center justify-between gap-3">
								<div class="flex items-center gap-3 min-w-0">
									<div
										class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100"
									>
										<FeatherIcon name="calendar" class="h-5 w-5" />
									</div>
									<div class="flex flex-col min-w-0">
										<h3
											class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
										>
											{{ __("Dates") }}
											<span class="text-red-500 ml-0.5">*</span>
										</h3>
										<span
											class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em] truncate"
										>
											<span v-if="!leaveApplication.leave_type">
												{{ __("Pick a leave type first") }}
											</span>
											<span v-else-if="pendingRange && leaveApplication.from_date">
												{{ __("Tap end date — or tap same day again for 1 day") }}
											</span>
											<span
												v-else-if="
													leaveApplication.from_date && leaveApplication.to_date
												"
											>
												{{
													formatRange(
														leaveApplication.from_date,
														leaveApplication.to_date
													)
												}}
												·
												{{ leaveApplication.total_leave_days || 0 }}
												{{ __("days") }}
											</span>
											<span v-else>{{ __("Tap a start date") }}</span>
										</span>
									</div>
								</div>

								<button
									type="button"
									@click="toggleHalfDay()"
									:disabled="halfDayDisabled"
									class="rounded-full px-3 py-1.5 text-[10px] font-black uppercase tracking-widest border-2 transition-all whitespace-nowrap shrink-0"
									:class="[
										halfDayDisabled
											? 'bg-gray-50 text-gray-300 border-gray-100 cursor-not-allowed'
											: leaveApplication.half_day
											? 'bg-amber-100 text-amber-700 border-amber-300'
											: 'bg-white text-gray-500 border-gray-200 hover:border-amber-200',
									]"
								>
									½ {{ __("Half Day") }}
								</button>
							</div>

							<!-- Inline range calendar -->
							<div
								class="rounded-2xl border border-gray-100 bg-white p-3 shadow-sm"
							>
								<!-- Month nav -->
								<div class="flex items-center justify-between mb-2">
									<button
										type="button"
										@click="prevMonth()"
										class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
									>
										<FeatherIcon name="chevron-left" class="h-4 w-4" />
									</button>
									<div class="text-sm font-extrabold text-gray-900">
										{{ monthLabel }}
									</div>
									<button
										type="button"
										@click="nextMonth()"
										class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
									>
										<FeatherIcon name="chevron-right" class="h-4 w-4" />
									</button>
								</div>

								<!-- Weekday header -->
								<div
									class="grid grid-cols-7 gap-1 mb-1 text-center text-[10px] font-black uppercase tracking-widest text-gray-400"
								>
									<div>S</div>
									<div>M</div>
									<div>T</div>
									<div>W</div>
									<div>T</div>
									<div>F</div>
									<div>S</div>
								</div>

								<!-- Days grid — fixed h-9 cells, no aspect-square -->
								<div class="grid grid-cols-7 gap-1">
									<button
										v-for="(cell, idx) in calendarCells"
										:key="idx"
										type="button"
										:disabled="!isCellTappable(cell)"
										@click="cell.date && pickDate(cell)"
										class="h-9 w-full flex items-center justify-center text-[13px] font-bold rounded-lg transition-all relative"
										:class="cellClass(cell)"
									>
										<span v-if="cell.date" class="relative z-10">
											{{ cell.day }}
										</span>
										<span
											v-if="
												cell.date &&
												isHalfDayDate(cell.date) &&
												leaveApplication.half_day
											"
											class="absolute -bottom-0.5 right-1 text-[8px] font-black text-amber-600 z-10"
										>
											½
										</span>
									</button>
								</div>

								<!-- Legend -->
								<div
									class="mt-3 pt-3 border-t border-gray-100 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[10px] font-bold text-gray-500 uppercase tracking-widest"
								>
									<div class="flex items-center gap-1.5">
										<div class="w-2.5 h-2.5 rounded bg-blue-600"></div>
										{{ __("Selected") }}
									</div>
									<div class="flex items-center gap-1.5">
										<div class="w-2.5 h-2.5 rounded bg-green-100 border border-green-200"></div>
										{{ __("Approved") }}
									</div>
									<div class="flex items-center gap-1.5">
										<div class="w-2.5 h-2.5 rounded bg-amber-100 border border-amber-200"></div>
										{{ __("Pending") }}
									</div>
									<div class="flex items-center gap-1.5">
										<div class="w-2.5 h-2.5 rounded bg-gray-200"></div>
										{{ __("Holiday") }}
									</div>
									<div class="flex items-center gap-1.5">
										<div
											class="w-2.5 h-2.5 rounded bg-gray-50 border border-dashed border-gray-300"
										></div>
										{{ __("Optional") }}
									</div>
								</div>
							</div>

							<!-- Date error -->
							<div
								v-if="dateError"
								class="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-bold text-red-700"
							>
								{{ dateError }}
							</div>

							<!-- Half-day day picker for ranges > 1 day -->
							<div
								v-if="
									leaveApplication.half_day &&
									leaveApplication.from_date &&
									leaveApplication.to_date &&
									leaveApplication.from_date !== leaveApplication.to_date
								"
								class="rounded-2xl border border-amber-200 bg-amber-50 p-3"
							>
								<div
									class="text-[10px] font-black uppercase tracking-widest text-amber-700 mb-2"
								>
									{{ __("Which day is the half-day?") }}
								</div>
								<div class="flex flex-wrap gap-2">
									<button
										v-for="d in halfDayChoices"
										:key="d"
										type="button"
										@click="leaveApplication.half_day_date = d"
										class="rounded-full px-3 py-1.5 text-[11px] font-extrabold border-2 transition-all"
										:class="
											leaveApplication.half_day_date === d
												? 'bg-amber-500 text-white border-amber-500'
												: 'bg-white text-amber-700 border-amber-200 hover:border-amber-400'
										"
									>
										{{ formatShort(d) }}
									</button>
								</div>
							</div>
						</section>

						<!-- Section: Reason -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-amber-50 text-amber-600 shadow-sm border border-amber-200"
								>
									<FeatherIcon name="edit-3" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Reason") }}
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Optional — context for your approver") }}
									</span>
								</div>
							</div>
							<textarea
								v-model="leaveApplication.description"
								rows="3"
								:placeholder="__('e.g. Family wedding out of town')"
								class="w-full rounded-2xl border border-gray-200 bg-white focus:border-blue-300 p-4 text-sm font-medium text-gray-800 transition-all resize-none outline-none placeholder:text-gray-400"
							></textarea>
						</section>

						<!-- Section: Approver -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-green-50 text-green-600 shadow-sm border border-green-100"
								>
									<FeatherIcon name="user-check" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Approver") }}
										<span v-if="approverReqd" class="text-red-500 ml-0.5"
											>*</span
										>
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Who reviews this request") }}
									</span>
								</div>
							</div>

							<div
								v-if="approverOptions.length > 1"
								class="space-y-2"
							>
								<button
									v-for="opt in approverOptions"
									:key="opt.value"
									type="button"
									@click="leaveApplication.leave_approver = opt.value"
									class="w-full rounded-2xl border-2 px-4 py-3 text-left transition-all flex items-center gap-3"
									:class="
										leaveApplication.leave_approver === opt.value
											? 'border-green-500 bg-green-50'
											: 'border-gray-100 bg-white hover:border-green-200'
									"
								>
									<div
										class="w-9 h-9 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-black text-sm shrink-0 border border-green-200"
									>
										{{ initials(opt.name) }}
									</div>
									<div class="flex-1 min-w-0">
										<div
											class="text-sm font-extrabold text-gray-900 truncate"
										>
											{{ opt.name || opt.value }}
										</div>
										<div
											class="text-[11px] font-bold text-gray-500 truncate"
										>
											{{ opt.value }}
										</div>
									</div>
									<FeatherIcon
										v-if="leaveApplication.leave_approver === opt.value"
										name="check-circle"
										class="h-5 w-5 text-green-600 shrink-0"
									/>
								</button>
							</div>

							<div
								v-else-if="approverOptions.length === 1"
								class="rounded-2xl border border-gray-100 bg-white px-4 py-3 flex items-center gap-3"
							>
								<div
									class="w-9 h-9 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-black text-sm shrink-0 border border-green-200"
								>
									{{ initials(approverOptions[0].name) }}
								</div>
								<div class="flex-1 min-w-0">
									<div class="text-sm font-extrabold text-gray-900 truncate">
										{{ approverOptions[0].name || approverOptions[0].value }}
									</div>
									<div class="text-[11px] font-bold text-gray-500 truncate">
										{{ approverOptions[0].value }}
									</div>
								</div>
								<span
									class="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md bg-green-50 text-green-600 border border-green-100"
								>
									{{ __("Auto-assigned") }}
								</span>
							</div>
						</section>

						<!-- Section: Attachments -->
						<section class="space-y-3">
							<div class="flex items-center gap-3">
								<div
									class="p-2.5 rounded-xl bg-gray-50 text-gray-600 shadow-sm border border-gray-200"
								>
									<FeatherIcon name="paperclip" class="h-5 w-5" />
								</div>
								<div class="flex flex-col">
									<h3
										class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]"
									>
										{{ __("Attachments") }}
									</h3>
									<span
										class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]"
									>
										{{ __("Medical certs, tickets — optional") }}
									</span>
								</div>
							</div>

							<label
								class="block rounded-2xl border-2 border-dashed border-gray-200 bg-white hover:border-blue-300 transition-all p-5 cursor-pointer"
							>
								<input
									type="file"
									multiple
									class="hidden"
									@change="handleFileSelect"
								/>
								<div class="flex flex-col items-center gap-2">
									<div
										class="p-2.5 rounded-xl bg-gray-50 border border-gray-200"
									>
										<FeatherIcon
											name="upload-cloud"
											class="h-5 w-5 text-gray-600"
										/>
									</div>
									<div
										class="text-[11px] font-black uppercase tracking-widest text-gray-500"
									>
										{{ __("Tap to upload") }}
									</div>
								</div>
							</label>

							<div v-if="fileAttachments.length" class="space-y-2">
								<div
									v-for="(file, i) in fileAttachments"
									:key="i"
									class="rounded-xl border border-gray-100 bg-white p-3 flex items-center gap-3"
								>
									<div
										class="p-2 rounded-lg bg-gray-50 text-gray-600 shrink-0"
									>
										<FeatherIcon name="file" class="h-4 w-4" />
									</div>
									<div class="flex-1 min-w-0">
										<div class="text-sm font-bold text-gray-900 truncate">
											{{ file.name }}
										</div>
									</div>
									<button
										type="button"
										@click="removeFile(i)"
										class="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
									>
										<FeatherIcon name="x" class="h-4 w-4" />
									</button>
								</div>
							</div>
						</section>
					</div>
				</div>

				<!-- Floating CTA dock — Action-Centre primary blue -->
				<div
					class="fixed bottom-0 left-0 right-0 z-50 sm:max-w-4xl sm:mx-auto px-4 pb-4 pt-3 bg-gradient-to-t from-white via-white to-white/0"
				>
					<div
						class="rounded-2xl bg-white border border-gray-200 shadow-lg overflow-hidden flex items-stretch"
					>
						<div class="flex-1 px-4 py-3 min-w-0">
							<div
								class="text-[9px] font-black uppercase tracking-widest text-gray-400"
							>
								{{ ctaSummary.label }}
							</div>
							<div
								class="text-sm font-extrabold text-gray-900 mt-0.5 truncate"
							>
								{{ ctaSummary.value }}
							</div>
						</div>
						<button
							type="button"
							@click="saveForm"
							:disabled="saving"
							class="px-5 bg-blue-600 text-white font-black text-xs uppercase tracking-widest disabled:opacity-50 hover:brightness-110 active:scale-95 transition-all flex items-center gap-2"
						>
							<LoadingIndicator
								v-if="saving"
								class="h-4 w-4 text-white"
							/>
							<FeatherIcon v-else name="send" class="h-4 w-4" />
							{{ saving ? __("Saving") : __("Submit") }}
						</button>
					</div>
				</div>
			</div>
		</ion-content>

		<SuccessModal
			:isOpen="successOpen"
			:title="__('Leave applied!')"
			:subtitle="__('{0} will be notified shortly.', [approverDisplayName])"
			:reference="successDocName"
			@dismiss="onSuccessDismissed"
		/>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import SuccessModal from "@/components/SuccessModal.vue"
import {
	createResource,
	createListResource,
	Button,
	FeatherIcon,
	LoadingIndicator,
	toast,
} from "frappe-ui"
import { computed, ref, watch, inject } from "vue"
import { useRouter } from "vue-router"

import LeaveApplicationDetailView from "@/components/LeaveApplicationDetailView.vue"
import { FileAttachment } from "@/composables"
import { showErrorFromException } from "@/data/errorModal"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const today = dayjs().format("YYYY-MM-DD")
const router = useRouter()

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

const sessionEmployee = inject("$employee")
const currEmployee = ref(sessionEmployee.data.name)
const employeeCompany = ref(sessionEmployee.data.company)
const optionalHolidayError = ref("")
const dateError = ref("")
const fileAttachments = ref([])
const saving = ref(false)

const leaveApplication = ref({
	half_day: 0,
	total_leave_days: 0,
	posting_date: today,
	status: "Open",
})

// formFields stays around to gate the new-application UI on field metadata
// being ready (used to also feed FormView in the edit/detail flow before the
// custom DetailView replaced it).
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Leave Application" },
	transform(data) {
		const excludeFields = [
			"naming_series",
			"sb_other_details",
			"salary_slip",
			"letter_head",
			"hr_approver",
			"follow_via_email",
			"status",
			"posting_date",
			"custom_approved_by",
			"custom_approved_on",
		]
		if (!props.id)
			excludeFields.push("employee", "employee_name", "department", "company")
		return data
			.filter((f) => !excludeFields.includes(f.fieldname))
			.map((field) => {
				if (field.fieldname === "half_day_date") field.hidden = true
				if (field.fieldname === "posting_date") field.default = today
				return field
			})
	},
	onSuccess() {
		leaveApprovalDetails.reload()
		leaveTypes.reload()
		calendarData.reload()
	},
})
formFields.reload()

const leaveApprovalDetails = createResource({
	url: "hrms.api.get_leave_approval_details",
	params: { employee: currEmployee.value },
	onSuccess(data) {
		setLeaveApprovers(data)
	},
})

const leaveTypesData = ref([])
const leaveTypes = createResource({
	url: "hrms.api.get_leave_types",
	params: {
		employee: currEmployee.value,
		date: today,
	},
	onSuccess(data) {
		leaveTypesData.value = Array.isArray(data) ? data : []
	},
})

const optionalLeaveTypes = createResource({
	url: "myhr.api.get_optional_leave_types",
	auto: true,
	cache: "myhr:optional_leave_types",
})

const optionalLeaveValidation = createResource({
	url: "myhr.api.validate_optional_leave_for_application",
	onSuccess(data) {
		if (!data || data.skipped || data.valid) {
			optionalHolidayError.value = ""
		} else {
			optionalHolidayError.value = data.message || __("Validation failed")
		}
		refreshDateErrors()
	},
	onError(err) {
		const msg = err?.messages?.[0] || err?.message || String(err)
		optionalHolidayError.value = msg
		refreshDateErrors()
	},
})

// Combined holiday + existing-leave fetch so the calendar can tint each day by
// its real state (fixed / optional / pending / approved) without three round-trips.
const fixedHolidayDates = ref(new Set())
const optionalHolidayDates = ref(new Set())
const leaveByDate = ref(new Map()) // date → { status, leave_type, name }

const calendarWindow = {
	from: dayjs().subtract(6, "month").startOf("month").format("YYYY-MM-DD"),
	to: dayjs().add(6, "month").endOf("month").format("YYYY-MM-DD"),
}

const calendarData = createResource({
	url: "myhr.api.get_leave_calendar_data",
	params: {
		employee: currEmployee.value,
		from_date: calendarWindow.from,
		to_date: calendarWindow.to,
	},
	onSuccess(data) {
		const fixed = new Set()
		const optional = new Set()
		;(data?.holidays || []).forEach((h) => {
			if (!h.date) return
			if (h.type === "optional") optional.add(h.date)
			else fixed.add(h.date) // fixed + weekly_off both treated as un-tappable for non-Optional types
		})
		fixedHolidayDates.value = fixed
		optionalHolidayDates.value = optional

		const m = new Map()
		;(data?.leave_applications || []).forEach((la) => {
			let cur = dayjs(la.from_date)
			const end = dayjs(la.to_date)
			// Guard against corrupt rows (to_date < from_date) that would loop
			// forever, and cap to 366 days as a sanity bound for any single LA.
			if (!cur.isValid() || !end.isValid() || end.isBefore(cur)) return
			let safety = 0
			while (cur.isSame(end) || cur.isBefore(end)) {
				if (++safety > 366) break
				const ds = cur.format("YYYY-MM-DD")
				// Approved trumps Open if both somehow exist on the same day
				const prev = m.get(ds)
				if (!prev || (prev.status !== "Approved" && la.status === "Approved")) {
					m.set(ds, {
						status: la.status,
						leave_type: la.leave_type,
						name: la.name,
					})
				}
				cur = cur.add(1, "day")
			}
		})
		leaveByDate.value = m
	},
})

const approverOptionsRaw = ref([])
const approverReqd = ref(false)
const approverOptions = computed(() => approverOptionsRaw.value)

function setLeaveApprovers(data) {
	approverReqd.value = !!data?.is_mandatory
	approverOptionsRaw.value = (data?.department_approvers || []).map((a) => ({
		value: a.name,
		name: a.full_name,
	}))
	if (!leaveApplication.value.leave_approver && data?.leave_approver) {
		leaveApplication.value.leave_approver = data.leave_approver
		leaveApplication.value.leave_approver_name = data.leave_approver_name
	}
}

const leaveTypeOptions = computed(() =>
	(leaveTypesData.value || []).map((t) => ({ value: t, label: t }))
)

function leaveTypeIcon(name) {
	const n = (name || "").toLowerCase()
	if (n.includes("sick")) return "thermometer"
	if (n.includes("casual")) return "coffee"
	if (n.includes("earned") || n.includes("privilege")) return "sun"
	if (n.includes("maternity") || n.includes("paternity")) return "heart"
	if (n.includes("comp") || n.includes("off")) return "refresh-cw"
	if (n.includes("optional") || n.includes("holiday")) return "star"
	if (n.includes("loss") || n.includes("unpaid")) return "minus-circle"
	if (n.includes("bereavement")) return "cloud-rain"
	return "calendar"
}

const isOptionalLeaveType = computed(() => {
	const optional = optionalLeaveTypes.data || []
	const lt = leaveApplication.value.leave_type
	return Boolean(lt && optional.includes(lt))
})

// Optional leaves are full-day-only — same gate as the optional leave type check.
const halfDayDisabled = isOptionalLeaveType

watch(
	() => leaveApplication.value.leave_type,
	(leave_type) => {
		// clear stale balance immediately so the hero card doesn't show last type's number
		leaveApplication.value.leave_balance = null
		setLeaveBalance()
		enforceFullDayForOptional(leave_type)
	}
)

watch(
	() => leaveApplication.value.from_date,
	(from_date) => {
		if (from_date) {
			leaveTypes.fetch({
				employee: currEmployee.value,
				date: from_date,
			})
		}
	}
)

watch(
	() => [
		leaveApplication.value.from_date,
		leaveApplication.value.to_date,
		leaveApplication.value.half_day,
		leaveApplication.value.half_day_date,
	],
	() => {
		validateDates()
		setTotalLeaveDays()
	}
)

watch(
	() => [
		leaveApplication.value.leave_type,
		leaveApplication.value.from_date,
		leaveApplication.value.to_date,
	],
	() => {
		const lt = leaveApplication.value.leave_type
		const fd = leaveApplication.value.from_date
		const td = leaveApplication.value.to_date
		if (!(lt && fd && td)) {
			optionalHolidayError.value = ""
			refreshDateErrors()
			return
		}
		optionalLeaveValidation.submit({
			employee: currEmployee.value,
			leave_type: lt,
			from_date: fd,
			to_date: td,
		})
	}
)

watch(
	() => leaveApplication.value.leave_approver,
	(newApprover) => {
		const opt = approverOptionsRaw.value.find((o) => o.value === newApprover)
		if (opt) leaveApplication.value.leave_approver_name = opt.name
	}
)

function setLeaveBalance() {
	const lt = leaveApplication.value.leave_type
	if (!lt) return
	// Show the as-of-today balance even before dates are picked. Once a range is
	// chosen, refetch with the from_date / to_date so the number reflects that
	// allocation window.
	const fd = leaveApplication.value.from_date || today
	const td = leaveApplication.value.to_date || today
	const leaveBalance = createResource({
		url: "hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on",
		params: {
			employee: currEmployee.value,
			date: fd,
			to_date: td,
			leave_type: lt,
			consider_all_leaves_in_the_allocation_period: 1,
		},
		onSuccess(data) {
			leaveApplication.value.leave_balance = data
		},
	})
	leaveBalance.reload()
}

function setTotalLeaveDays() {
	if (!areValuesSet()) return
	const leaveDays = createResource({
		url: "hrms.hr.doctype.leave_application.leave_application.get_number_of_leave_days",
		params: {
			employee: currEmployee.value,
			leave_type: leaveApplication.value.leave_type,
			from_date: leaveApplication.value.from_date,
			to_date: leaveApplication.value.to_date,
			half_day: leaveApplication.value.half_day,
			half_day_date: leaveApplication.value.half_day_date,
		},
		onSuccess(data) {
			leaveApplication.value.total_leave_days = data
		},
	})
	leaveDays.reload()
	setLeaveBalance()
}

function enforceFullDayForOptional(leave_type) {
	const optional = optionalLeaveTypes.data || []
	const isOptional = leave_type && optional.includes(leave_type)
	if (isOptional && leaveApplication.value.half_day) {
		leaveApplication.value.half_day = 0
		leaveApplication.value.half_day_date = null
	}
}

function validateDates() {
	const fd = leaveApplication.value.from_date
	const td = leaveApplication.value.to_date
	if (!(fd && td)) {
		dateError.value = ""
		return
	}
	if (fd > td) dateError.value = __("To Date cannot be before From Date")
	else dateError.value = ""
	refreshDateErrors()
}

function refreshDateErrors() {
	if (optionalHolidayError.value) {
		dateError.value = optionalHolidayError.value
	} else {
		const fd = leaveApplication.value.from_date
		const td = leaveApplication.value.to_date
		dateError.value =
			fd && td && fd > td ? __("To Date cannot be before From Date") : ""
	}
}

function areValuesSet() {
	return (
		leaveApplication.value.from_date &&
		leaveApplication.value.to_date &&
		leaveApplication.value.leave_type
	)
}

function validateForm() {
	leaveApplication.value.employee = currEmployee.value
	leaveApplication.value.company = employeeCompany.value
	leaveApplication.value.posting_date = today
	if (!leaveApplication.value.status) leaveApplication.value.status = "Open"
}

// ----- calendar -----
const cursor = ref(dayjs())
const pendingRange = ref(false)
const monthLabel = computed(() => cursor.value.format("MMMM YYYY"))

const calendarCells = computed(() => {
	const startOfMonth = cursor.value.startOf("month")
	const endOfMonth = cursor.value.endOf("month")
	const startWeekday = startOfMonth.day()
	const daysInMonth = endOfMonth.date()

	const cells = []
	for (let i = 0; i < startWeekday; i++) cells.push({ date: null })
	for (let d = 1; d <= daysInMonth; d++) {
		const date = startOfMonth.date(d).format("YYYY-MM-DD")
		const isFixedHoliday = fixedHolidayDates.value.has(date)
		const isOptionalHoliday = optionalHolidayDates.value.has(date)
		const existingLeave = leaveByDate.value.get(date) || null
		const isPast = date < today
		cells.push({
			date,
			day: d,
			isFixedHoliday,
			isOptionalHoliday,
			existingLeave,
			isPast,
		})
	}
	while (cells.length % 7 !== 0) cells.push({ date: null })
	return cells
})

function prevMonth() {
	cursor.value = cursor.value.subtract(1, "month")
}
function nextMonth() {
	cursor.value = cursor.value.add(1, "month")
}

function isCellTappable(cell) {
	if (!cell.date) return false
	if (!leaveApplication.value.leave_type) return false
	// Past dates ARE tappable (back-dated leave applications allowed); they
	// render with a muted-italic hint via cellClass.
	if (cell.existingLeave && cell.existingLeave.status === "Approved") return false
	if (cell.isFixedHoliday) return false
	if (cell.isOptionalHoliday && !isOptionalLeaveType.value) return false
	// Pending-leave overlap is allowed (with warning) so the user can extend it
	return true
}

function pickDate(cell) {
	if (!cell.date) return
	if (!isCellTappable(cell)) return
	const date = cell.date
	const fd = leaveApplication.value.from_date

	if (!fd || !pendingRange.value) {
		// 1st tap (or 3rd-tap reset): anchor a single day; await 2nd tap to extend
		leaveApplication.value.from_date = date
		leaveApplication.value.to_date = date
		leaveApplication.value.half_day_date = leaveApplication.value.half_day
			? date
			: null
		pendingRange.value = true
		return
	}

	// 2nd tap → extend the range from the anchor
	let flipped = false
	if (date < fd) {
		leaveApplication.value.from_date = date
		leaveApplication.value.to_date = fd
		flipped = true
	} else if (date > fd) {
		leaveApplication.value.to_date = date
	}
	// tapping the same day twice keeps it as a 1-day leave
	pendingRange.value = false
	if (leaveApplication.value.half_day) {
		// On flip, the old anchor (now in the middle/end of the range) may not
		// be a valid half-day boundary anymore — reset to the new from_date.
		if (flipped || !leaveApplication.value.half_day_date) {
			leaveApplication.value.half_day_date = leaveApplication.value.from_date
		}
	}
}

function cellClass(cell) {
	if (!cell.date) return "opacity-0 pointer-events-none"
	const fd = leaveApplication.value.from_date
	const td = leaveApplication.value.to_date
	const date = cell.date
	const noLeaveType = !leaveApplication.value.leave_type
	const isAnchor = pendingRange.value && fd === date
	const isStart = fd === date
	const isEnd = td === date && fd !== td
	const isOnlyPick = fd === td && fd === date && !pendingRange.value
	const inRange = fd && td && date > fd && date < td
	const isToday = date === today
	const lv = cell.existingLeave

	const base = []
	// Priority order: active selection > approved leave > pending leave > holiday > optional > past > available
	if (isAnchor) {
		base.push("bg-blue-600 text-white shadow-sm ring-2 ring-blue-300 ring-offset-1 animate-pulse")
	} else if (isOnlyPick || isStart || isEnd) {
		base.push("bg-blue-600 text-white shadow-sm")
	} else if (inRange) {
		base.push("bg-blue-100 text-blue-700")
	} else if (lv && lv.status === "Approved") {
		base.push("bg-green-100 text-green-700 cursor-not-allowed")
	} else if (lv && lv.status === "Open") {
		base.push("bg-amber-100 text-amber-700")
	} else if (cell.isFixedHoliday) {
		base.push("bg-gray-200 text-gray-500 line-through cursor-not-allowed")
	} else if (cell.isOptionalHoliday) {
		// dashed border signals "selectable only with Optional Holiday Leave type"
		base.push(
			"bg-gray-50 text-gray-600 border border-dashed border-gray-300"
		)
		if (!isOptionalLeaveType.value) base.push("cursor-not-allowed opacity-70")
	} else if (cell.isPast) {
		// Back-dated leave allowed — selectable but visually muted-italic to hint past
		base.push("text-gray-500 italic hover:bg-blue-50")
	} else if (noLeaveType) {
		base.push("text-gray-300 cursor-not-allowed")
	} else {
		base.push("text-gray-700 hover:bg-blue-50")
	}
	if (isToday && !(isStart || isEnd || isOnlyPick || isAnchor))
		base.push("ring-1 ring-blue-300")
	return base.join(" ")
}

function isHalfDayDate(date) {
	return leaveApplication.value.half_day_date === date
}

const halfDayChoices = computed(() => {
	const fd = leaveApplication.value.from_date
	const td = leaveApplication.value.to_date
	if (!fd || !td) return []
	if (fd === td) return [fd]
	// Build full inclusive list so user can pick any day in the range as
	// the half-day. Cap at 31 to keep the chip row manageable; longer
	// ranges drop back to from/to endpoints.
	const out = []
	let cur = dayjs(fd)
	const end = dayjs(td)
	if (!cur.isValid() || !end.isValid() || end.isBefore(cur)) return [fd, td]
	let safety = 0
	while ((cur.isSame(end) || cur.isBefore(end)) && safety < 31) {
		out.push(cur.format("YYYY-MM-DD"))
		cur = cur.add(1, "day")
		safety++
	}
	return out.length ? out : [fd, td]
})

function toggleHalfDay() {
	if (halfDayDisabled.value) return
	const next = leaveApplication.value.half_day ? 0 : 1
	leaveApplication.value.half_day = next
	if (!next) {
		leaveApplication.value.half_day_date = null
	} else {
		leaveApplication.value.half_day_date =
			leaveApplication.value.from_date || null
	}
}

function formatRange(fd, td) {
	if (!fd) return ""
	if (!td || fd === td) return dayjs(fd).format("MMM D")
	const a = dayjs(fd)
	const b = dayjs(td)
	if (a.month() === b.month())
		return `${a.format("MMM D")} – ${b.format("D")}`
	return `${a.format("MMM D")} – ${b.format("MMM D")}`
}

function formatShort(d) {
	return dayjs(d).format("ddd, MMM D")
}

function initials(name) {
	if (!name) return "?"
	return name
		.split(" ")
		.filter(Boolean)
		.map((s) => s[0])
		.slice(0, 2)
		.join("")
		.toUpperCase()
}

const remainingAfter = computed(() => {
	const bal = leaveApplication.value.leave_balance
	const req = leaveApplication.value.total_leave_days
	if (bal == null || req == null) return null
	return Math.round((bal - req) * 10) / 10
})

const overlapsPending = computed(() => {
	const fd = leaveApplication.value.from_date
	const td = leaveApplication.value.to_date
	if (!fd || !td) return false
	let cur = dayjs(fd)
	const end = dayjs(td)
	while (cur.isSame(end) || cur.isBefore(end)) {
		const ds = cur.format("YYYY-MM-DD")
		const lv = leaveByDate.value.get(ds)
		if (lv && lv.status === "Open") return true
		cur = cur.add(1, "day")
	}
	return false
})

const banner = computed(() => {
	if (dateError.value)
		return { tone: "red", title: __("Heads up"), subtitle: dateError.value }
	if (overlapsPending.value)
		return {
			tone: "amber",
			title: __("Overlaps a pending request"),
			subtitle: __(
				"You already have a leave request awaiting approval on these dates. Submitting will create a separate one."
			),
		}
	if (remainingAfter.value != null && remainingAfter.value < 0)
		return {
			tone: "amber",
			title: __("You'll be in the red"),
			subtitle: __(
				"This request exceeds your available balance — your approver may push back."
			),
		}
	if (
		leaveApplication.value.leave_type &&
		leaveApplication.value.from_date &&
		leaveApplication.value.to_date
	)
		return {
			tone: "green",
			title: __("Looks good"),
			subtitle: __("{0} will be notified when you submit.", [
				leaveApplication.value.leave_approver_name || __("Your approver"),
			]),
		}
	return {
		tone: "blue",
		title: __("Pick a leave type and dates"),
		subtitle: __(
			"You'll see your live balance and total days requested as you go."
		),
	}
})

const ctaSummary = computed(() => {
	const fd = leaveApplication.value.from_date
	const td = leaveApplication.value.to_date
	const days = leaveApplication.value.total_leave_days
	if (fd && td)
		return {
			label: __("{0} days · {1}", [days || 0, formatRange(fd, td)]),
			value: leaveApplication.value.leave_type || __("Pick a leave type"),
		}
	if (leaveApplication.value.leave_type)
		return {
			label: __("Step 2 of 2"),
			value: __("Pick dates to continue"),
		}
	return {
		label: __("Step 1 of 2"),
		value: __("Pick a leave type"),
	}
})

function handleFileSelect(e) {
	fileAttachments.value.push(...e.target.files)
	e.target.value = ""
}
function removeFile(idx) {
	fileAttachments.value.splice(idx, 1)
}

// Success modal state — replaces the old toast + immediate redirect.
const successOpen = ref(false)
const successDocName = ref("")
const approverDisplayName = computed(() => {
	const opt = approverOptionsRaw.value.find(
		(o) => o.value === leaveApplication.value.leave_approver,
	)
	return opt?.name || opt?.value || __("your approver")
})

function onSuccessDismissed() {
	successOpen.value = false
	router.replace({ name: "LeaveApplicationListView" })
}

const docList = createListResource({
	doctype: "Leave Application",
	insert: {
		async onSuccess(data) {
			for (const f of fileAttachments.value) {
				try {
					const fa = new FileAttachment(f)
					await fa.upload(data.doctype, data.name, "")
				} catch (e) {
					console.error("upload failed", e)
				}
			}
			successDocName.value = data.name || ""
			successOpen.value = true
		},
		onError(err) {
			saving.value = false
			console.error("Error creating Leave Application", err)
			showErrorFromException(err, __("Error creating Leave Application"))
		},
	},
})

function saveForm() {
	validateForm()
	if (!leaveApplication.value.leave_type) {
		toast({
			title: __("Pick a leave type"),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-amber-500",
		})
		return
	}
	if (
		!leaveApplication.value.from_date ||
		!leaveApplication.value.to_date
	) {
		toast({
			title: __("Pick a date range"),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-amber-500",
		})
		return
	}
	if (dateError.value) {
		toast({
			title: dateError.value,
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
		})
		return
	}
	if (approverReqd.value && !leaveApplication.value.leave_approver) {
		toast({
			title: __("Pick an approver"),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-amber-500",
		})
		return
	}
	saving.value = true
	docList.insert.submit(leaveApplication.value)
}
</script>
