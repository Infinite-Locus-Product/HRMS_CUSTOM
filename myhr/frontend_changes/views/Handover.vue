<template>
	<IonPage>
		<IonContent :fullscreen="true">
			<div class="bg-[#FBFBFC] min-h-screen pb-[120px]">
				<div
					class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative"
				>
					<div
						class="flex flex-row bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100 items-center gap-1"
					>
						<Button variant="ghost" class="!px-2 hover:bg-gray-100" @click="goBack">
							<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
						</Button>
						<div class="flex flex-col ml-1 overflow-hidden">
							<h2
								class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1"
							>
								{{ __("Handover & Clearance") }}
							</h2>
							<div class="flex items-center gap-1.5 opacity-60">
								<div class="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
								<span class="text-[10px] font-bold uppercase tracking-widest">
									{{ statusLabel }}
								</span>
							</div>
						</div>
					</div>

					<div v-if="loading" class="flex justify-center py-16">
						<LoadingIndicator class="w-6 h-6 text-gray-500" />
					</div>

					<div
						v-else-if="errorMsg"
						class="m-4 p-4 rounded-2xl bg-red-50 border border-red-200"
					>
						<p class="text-sm font-semibold text-red-800">{{ errorMsg }}</p>
					</div>

					<!-- Nothing to do yet -->
					<div
						v-else-if="!clearance && !separation"
						class="flex-1 px-4 py-16 text-center"
					>
						<FeatherIcon name="inbox" class="h-8 w-8 text-gray-300 mx-auto" />
						<p class="mt-3 text-sm font-bold text-gray-500">
							{{ __("Nothing to hand over yet") }}
						</p>
						<p class="mt-1 text-xs text-gray-400 px-6">
							{{ __("This opens once your resignation has been fully approved.") }}
						</p>
					</div>

					<div v-else class="flex-1 px-4 py-5 sm:p-5 space-y-5">
						<!-- Once it is with the manager -->
						<div
							v-if="clearance && !editable"
							class="rounded-2xl border p-4 flex items-start gap-3"
							:class="statusTone"
						>
							<FeatherIcon :name="statusIcon" class="h-5 w-5 mt-0.5 shrink-0" />
							<div>
								<div class="text-sm font-black">{{ clearance.workflow_state }}</div>
								<p class="text-xs font-medium opacity-80 mt-0.5">
									{{ statusHint }}
								</p>
							</div>
						</div>

						<!-- Handover documents -->
						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<div class="flex items-center justify-between">
								<h2
									class="text-xs font-black uppercase tracking-widest text-gray-500"
								>
									{{ __("Handover Documents") }}
								</h2>
								<Button v-if="editable" variant="subtle" size="sm" @click="addRow">
									{{ __("Add") }}
								</Button>
							</div>

							<p
								v-if="!form.handover_documents.length"
								class="text-xs text-gray-400 font-medium"
							>
								{{
									__(
										"Add a file, a link, or a note for each thing you are handing over.",
									)
								}}
							</p>

							<div
								v-for="(row, i) in form.handover_documents"
								:key="i"
								class="rounded-xl border border-gray-100 bg-gray-50/60 p-3 space-y-2"
							>
								<div class="flex items-center gap-2">
									<input
										v-model="row.title"
										:disabled="!editable"
										:placeholder="__('Title (required), e.g. Client X notes')"
										class="flex-1 rounded-lg border-gray-300 text-sm disabled:bg-gray-50"
									/>
									<button
										v-if="editable"
										type="button"
										@click="form.handover_documents.splice(i, 1)"
										class="p-2 text-gray-400 hover:text-red-600"
									>
										<FeatherIcon name="trash-2" class="h-4 w-4" />
									</button>
								</div>
								<!-- Attached file, once there is one -->
								<div
									v-if="row.attachment"
									class="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2"
								>
									<FeatherIcon
										name="paperclip"
										class="h-4 w-4 text-blue-600 shrink-0"
									/>
									<a
										:href="row.attachment"
										target="_blank"
										rel="noopener"
										class="flex-1 text-xs font-bold text-blue-700 truncate"
									>
										{{ row.file_name || __("View attachment") }}
									</a>
									<button
										v-if="editable"
										type="button"
										@click="clearAttachment(row)"
										class="p-1 text-blue-400 hover:text-red-600"
									>
										<FeatherIcon name="x" class="h-4 w-4" />
									</button>
								</div>

								<!-- Otherwise: attach a file, or paste a link -->
								<template v-else>
									<label
										v-if="editable"
										class="flex items-center justify-center gap-2 rounded-lg border border-dashed border-gray-300 px-3 py-2 cursor-pointer hover:bg-gray-50"
									>
										<LoadingIndicator
											v-if="uploadingIndex === i"
											class="w-4 h-4 text-gray-500"
										/>
										<FeatherIcon
											v-else
											name="upload"
											class="h-4 w-4 text-gray-500"
										/>
										<span class="text-xs font-bold text-gray-600">
											{{
												uploadingIndex === i
													? __("Uploading…")
													: __("Attach a file")
											}}
										</span>
										<input
											type="file"
											class="hidden"
											:disabled="uploadingIndex !== null"
											@change="(e) => attachFile(i, e)"
										/>
									</label>
									<input
										v-model="row.external_link"
										:disabled="!editable"
										:placeholder="
											__('…or paste a link (Drive, Confluence, repo)')
										"
										class="w-full rounded-lg border-gray-300 text-sm disabled:bg-gray-50"
									/>
								</template>
								<textarea
									v-model="row.notes"
									:disabled="!editable"
									rows="2"
									:placeholder="__('Or a short note')"
									class="w-full rounded-lg border-gray-300 text-sm disabled:bg-gray-50"
								/>
							</div>
						</section>

						<!-- Successor + summary -->
						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-4"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Handover Details") }}
							</h2>
							<div>
								<label class="block text-xs font-bold text-gray-600 mb-1">
									{{ __("Primary Successor") }}
								</label>
								<!-- Chosen person -->
								<div
									v-if="form.primary_successor"
									class="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2"
								>
									<FeatherIcon
										name="user"
										class="h-4 w-4 text-blue-600 shrink-0"
									/>
									<div class="flex-1 min-w-0">
										<div class="text-sm font-bold text-blue-900 truncate">
											{{ successorName || form.primary_successor }}
										</div>
										<div
											class="text-[11px] font-semibold text-blue-600 truncate"
										>
											{{ form.primary_successor }}
										</div>
									</div>
									<button
										v-if="editable"
										type="button"
										@click="clearSuccessor"
										class="p-1 text-blue-400 hover:text-red-600"
									>
										<FeatherIcon name="x" class="h-4 w-4" />
									</button>
								</div>

								<!-- Search -->
								<div v-else-if="editable" class="relative">
									<input
										v-model="successorQuery"
										type="text"
										:placeholder="__('Search a colleague by name or ID')"
										class="w-full rounded-lg border-gray-300 text-sm"
										@input="searchColleagues"
										@focus="searchColleagues"
									/>
									<div
										v-if="successorResults.length"
										class="absolute z-20 mt-1 w-full max-h-56 overflow-auto rounded-xl border border-gray-200 bg-white shadow-lg"
									>
										<button
											v-for="person in successorResults"
											:key="person.name"
											type="button"
											@click="pickSuccessor(person)"
											class="w-full text-left px-3 py-2 hover:bg-blue-50 border-b border-gray-50 last:border-0"
										>
											<div class="text-sm font-bold text-gray-900 truncate">
												{{ person.employee_name }}
											</div>
											<div
												class="text-[11px] font-semibold text-gray-400 truncate"
											>
												{{ person.name }}
												<span v-if="person.designation">
													· {{ person.designation }}</span
												>
											</div>
										</button>
									</div>
									<p
										v-else-if="successorQuery && !searchingSuccessor"
										class="mt-1 text-[11px] font-medium text-gray-400"
									>
										{{ __("No one matched.") }}
									</p>
								</div>

								<p v-else class="text-sm text-gray-400">—</p>
							</div>
							<div>
								<label class="block text-xs font-bold text-gray-600 mb-1">
									{{ __("Project / Client Status Summary") }}
								</label>
								<textarea
									v-model="form.project_client_status_summary"
									:disabled="!editable"
									rows="4"
									class="w-full rounded-lg border-gray-300 text-sm disabled:bg-gray-50"
								/>
							</div>
						</section>

						<!-- Confirmations -->
						<section
							class="rounded-2xl bg-white border border-gray-100 shadow-sm p-4 space-y-3"
						>
							<h2 class="text-xs font-black uppercase tracking-widest text-gray-500">
								{{ __("Before You Go") }}
							</h2>
							<p class="text-xs text-gray-400 font-medium -mt-1">
								{{ __("All three are required before you can submit.") }}
							</p>
							<label
								v-for="item in confirmations"
								:key="item.field"
								class="flex items-start gap-3 py-1 cursor-pointer"
							>
								<input
									type="checkbox"
									:checked="!!form[item.field]"
									:disabled="!editable"
									@change="form[item.field] = $event.target.checked ? 1 : 0"
									class="mt-0.5 h-4 w-4 rounded border-gray-300"
								/>
								<span class="text-sm font-semibold text-gray-800">{{
									item.label
								}}</span>
							</label>
						</section>
					</div>

					<div
						v-if="!loading && editable"
						class="fixed bottom-0 inset-x-0 sm:max-w-4xl sm:mx-auto bg-white border-t p-4 flex flex-col standalone:pb-safe-bottom z-30"
					>
						<!-- Errors stay on screen until the next successful action. A toast
						     is not enough: the save that follows a file upload happens in the
						     background, and its toast fires where nobody is looking. -->
						<div
							v-if="actionError"
							class="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 flex items-start gap-2"
						>
							<FeatherIcon
								name="alert-circle"
								class="h-4 w-4 text-red-600 mt-0.5 shrink-0"
							/>
							<p class="text-xs font-semibold text-red-800 flex-1">
								{{ actionError }}
							</p>
							<button
								type="button"
								@click="actionError = ''"
								class="p-0.5 text-red-400 hover:text-red-700"
							>
								<FeatherIcon name="x" class="h-3.5 w-3.5" />
							</button>
						</div>
						<div class="flex gap-3">
							<Button
								class="w-full py-5"
								variant="subtle"
								:loading="saving"
								@click="save(false)"
							>
								{{ __("Save Draft") }}
							</Button>
							<Button
								class="w-full py-5"
								variant="solid"
								:loading="submitting"
								:disabled="!allConfirmed"
								@click="save(true)"
							>
								{{ __("Submit") }}
							</Button>
						</div>
					</div>
				</div>
			</div>
		</IonContent>
	</IonPage>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import { Button, FeatherIcon, LoadingIndicator, createResource, toast } from "frappe-ui";

// frappe-ui exports `toast(options)` here — there is no `toast.success`.
// Calling one threw mid-handler and skipped everything after it, which is how a
// successful approval ended up showing no confirmation at all.
function notify(title, text, ok = true) {
	toast({
		title,
		text,
		icon: ok ? "check" : "alert-triangle",
		iconClasses: ok ? "text-green-500" : "text-red-500",
	});
}

import { IonPage, IonContent, useIonRouter, onIonViewWillEnter } from "@ionic/vue";
import { FileAttachment } from "@/composables";

const CLEARANCE_DOCTYPE = "Separation Manager Clearance";

const ionRouter = useIonRouter();
const __ = inject("$translate");

const loading = ref(true);
const saving = ref(false);
const submitting = ref(false);
const uploadingIndex = ref(null);
const actionError = ref("");

const successorQuery = ref("");
const successorResults = ref([]);
const successorName = ref("");
const searchingSuccessor = ref(false);
let successorTimer = null;
const errorMsg = ref("");
const clearance = ref(null);
const separation = ref(null);

const form = ref({
	primary_successor: "",
	project_client_status_summary: "",
	downloaded_payslips: 0,
	downloaded_tax_slips: 0,
	cleared_personal_files: 0,
	handover_documents: [],
});

const confirmations = computed(() => [
	{ field: "downloaded_payslips", label: __("I have downloaded my payslips") },
	{ field: "downloaded_tax_slips", label: __("I have downloaded my tax slips / Form 16") },
	{
		field: "cleared_personal_files",
		label: __("I have cleared personal files from my work device"),
	},
]);

// Editable only while it is still the leaver's, which the server decides.
const editable = computed(() => !clearance.value || clearance.value.is_employee_half_editable);
const allConfirmed = computed(() => confirmations.value.every((c) => !!form.value[c.field]));

const statusLabel = computed(() => clearance.value?.workflow_state || __("Not started"));

const statusTone = computed(() =>
	clearance.value?.workflow_state === "Complete"
		? "bg-green-50 border-green-200 text-green-800"
		: "bg-blue-50 border-blue-200 text-blue-800",
);
const statusIcon = computed(() =>
	clearance.value?.workflow_state === "Complete" ? "check-circle" : "clock",
);
const statusHint = computed(() =>
	clearance.value?.workflow_state === "Complete"
		? __("Your manager has signed off on the handover.")
		: __("With your manager for verification. Nothing more for you to do."),
);

function goBack() {
	if (window.history.length > 2) window.history.back();
	else ionRouter.push({ name: "Resignation" });
}

function addRow() {
	form.value.handover_documents.push({
		title: "",
		attachment: "",
		file_name: "",
		external_link: "",
		notes: "",
	});
}

function pickSuccessor(person) {
	form.value.primary_successor = person.name;
	successorName.value = person.employee_name;
	successorQuery.value = "";
	successorResults.value = [];
}

function clearSuccessor() {
	form.value.primary_successor = "";
	successorName.value = "";
}

// Debounced: typing a name would otherwise fire a request per keystroke.
function searchColleagues() {
	clearTimeout(successorTimer);
	searchingSuccessor.value = true;
	successorTimer = setTimeout(async () => {
		try {
			successorResults.value = await colleagues.submit({ query: successorQuery.value });
		} catch {
			successorResults.value = [];
		} finally {
			searchingSuccessor.value = false;
		}
	}, 250);
}

function clearAttachment(row) {
	// The File record itself is left alone: it stays attached to the clearance
	// and is still reachable from Desk, which matters if someone removes a row
	// by accident on the last day.
	row.attachment = "";
	row.file_name = "";
}

async function attachFile(index, event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file) return;

	uploadingIndex.value = index;
	actionError.value = "";
	try {
		// Uploading needs a document to attach to, so a brand-new handover is
		// saved as a draft first. Nothing is lost if the upload then fails.
		const name = await ensureSaved();
		const fileDoc = await new FileAttachment(file).upload(CLEARANCE_DOCTYPE, name, null);
		const row = form.value.handover_documents[index];
		row.attachment = fileDoc.file_url;
		row.file_name = fileDoc.file_name || file.name;
		// The row's title is mandatory server-side. Someone who has just picked
		// a file has already said what it is, so default to its name rather
		// than failing the save and wiping the form.
		if (!(row.title || "").trim()) {
			row.title = (fileDoc.file_name || file.name || "").replace(/\.[^.]+$/, "");
		}
		await save(false, { silent: true });
		notify(__("Attached"), file.name);
	} catch (err) {
		reportError(err, __("Could not attach that file."));
	} finally {
		uploadingIndex.value = null;
	}
}

async function ensureSaved() {
	if (clearance.value?.name) return clearance.value.name;
	await save(false, { silent: true });
	if (!clearance.value?.name) throw new Error(__("Could not start your handover."));
	return clearance.value.name;
}

function hydrate(data) {
	separation.value = data?.separation || null;
	clearance.value = data?.exists ? data.clearance : null;
	successorName.value = clearance.value?.primary_successor_name || "";
	if (clearance.value) {
		for (const key of Object.keys(form.value)) {
			if (key === "handover_documents") continue;
			form.value[key] = clearance.value[key] ?? form.value[key];
		}
		form.value.handover_documents = (clearance.value.handover_documents || []).map((r) => ({
			title: r.title || "",
			attachment: r.attachment || "",
			file_name: r.file_name || "",
			external_link: r.external_link || "",
			notes: r.notes || "",
		}));
	}
	loading.value = false;
}

const resource = createResource({
	url: "myhr.clearance_api.get_my_clearance",
	onSuccess: hydrate,
	onError: (err) => {
		loading.value = false;
		errorMsg.value = err?.messages?.[0] || err?.message || String(err);
	},
});

const saveResource = createResource({ url: "myhr.clearance_api.save_my_handover" });
// One place that decides what the user is told when something fails. Frappe
// puts the useful sentence in `messages[0]`; `message` is often a bare
// exception. The banner and the toast get the same words.
function reportError(err, fallback) {
	const message = err?.messages?.[0] || err?.message || fallback;
	actionError.value = message;
	notify(__("Something went wrong"), message, false);
	return message;
}

// The Employee doctype is locked down per-user, so the framework's own Link
// search would come back empty. This endpoint returns the same public fields
// the company directory already shows everyone.
const colleagues = createResource({ url: "myhr.clearance_api.search_colleagues" });

async function save(isSubmit, { silent = false } = {}) {
	if (isSubmit && !allConfirmed.value) {
		notify(__("Not ready"), __("Tick all three confirmations before submitting."), false);
		return;
	}
	const rows = form.value.handover_documents.filter(
		(r) => r.attachment || r.external_link || (r.notes || "").trim(),
	);
	if (isSubmit && !rows.length) {
		notify(__("Not ready"), __("Add at least one handover document."), false);
		return;
	}
	// Mandatory on the child row. Without this the save fails server-side with
	// a bare field name and the whole form is lost on the next refresh.
	const untitled = rows.findIndex((r) => !(r.title || "").trim());
	if (untitled !== -1) {
		notify(__("Not ready"), __("Give handover document {0} a title.", [untitled + 1]), false);
		return;
	}

	const busy = isSubmit ? submitting : saving;
	busy.value = true;
	actionError.value = "";
	try {
		// The response is the refreshed view; swapping it in avoids re-fetching
		// the same endpoint and being served a cached copy.
		const result = await saveResource.submit({
			payload: JSON.stringify({ ...form.value, handover_documents: rows }),
			submit: isSubmit ? 1 : 0,
		});
		clearance.value = result;
		if (!silent)
			notify(
				isSubmit ? __("Submitted") : __("Draft saved"),
				isSubmit ? __("Sent to your manager.") : __("You can come back to it."),
			);
	} catch (err) {
		if (silent) throw err;
		reportError(err, __("Could not save."));
	} finally {
		busy.value = false;
	}
}

onIonViewWillEnter(() => {
	loading.value = true;
	errorMsg.value = "";
	actionError.value = "";
	resource.reload();
});
</script>
