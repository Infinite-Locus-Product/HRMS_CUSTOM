<template>
	<ion-page>
		<ion-content class="ion-no-padding bg-[#FBFBFC]" style="--background: #FBFBFC;">
			<div class="w-full min-h-screen sm:max-w-4xl mx-auto bg-white flex flex-col shadow-xl border-x border-gray-100 relative pb-[120px]">
				<!-- Sticky Header (Glassmorphism) -->
					<div class="flex flex-col bg-white/80 backdrop-blur-md shadow-sm p-4 sticky top-0 z-50 border-b border-gray-100 transition-all duration-300">
						<div class="flex flex-row justify-between items-center gap-4">
							<div class="flex flex-row items-center gap-1 flex-1">
								<Button
									variant="ghost"
									class="!px-2 hover:bg-gray-100 transition-colors"
									@click="goBack()"
								>
									<FeatherIcon name="chevron-left" class="h-6 w-6 text-gray-700" />
								</Button>
								<div class="flex flex-col ml-1 overflow-hidden">
									<h2 class="text-lg font-extrabold text-gray-900 truncate leading-none mb-1">
										{{ __("Action Centre") }}
									</h2>
									<div v-if="acData" class="flex items-center gap-1.5 opacity-60">
										<div class="w-1.5 h-1.5 rounded-full" :class="acData.status === 'Accepted' ? 'bg-green-500' : 'bg-orange-500'"></div>
										<span class="text-[10px] font-bold uppercase tracking-widest">{{ acData.name }}</span>
									</div>
								</div>
							</div>

							<div class="flex flex-row items-center gap-2">
								<router-link
									:to="{ name: 'Notifications' }"
									class="p-2 hover:bg-gray-100 rounded-full transition-all relative"
								>
									<FeatherIcon name="bell" class="h-5 w-5 text-gray-600" />
									<span v-if="unreadNotificationsCount.data" class="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white animate-pulse"></span>
								</router-link>
								<router-link :to="{ name: 'Profile' }" class="ml-1 cursor-pointer hover:ring-2 hover:ring-gray-100 rounded-full transition-all">
									<Avatar :image="user.data.user_image" :label="user.data.first_name" size="lg" />
								</router-link>
							</div>
						</div>
					</div>

					<!-- Content Area -->
					<div class="flex-1 px-4 py-4 sm:p-5 space-y-6 sm:space-y-8">
						<!-- Loading/Error States -->
						<div v-if="loading" class="flex flex-col items-center justify-center py-32 space-y-4">
							<LoadingIndicator class="h-8 w-8 text-blue-600" />
							<p class="text-xs font-bold text-gray-400 uppercase tracking-widest tracking-[0.2em]">{{ __("Syncing Details") }}</p>
						</div>

						<div v-else-if="acData?.error" class="flex flex-col items-center justify-center py-20 bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200">
							<div class="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center mb-4">
								<FeatherIcon name="alert-circle" class="h-8 w-8 text-red-500" />
							</div>
							<p class="text-gray-900 font-bold text-lg mb-1">{{ __("No Action Centre") }}</p>
							<p class="text-gray-500 text-sm">{{ acData.message }}</p>
						</div>

						<!-- Main View -->
						<template v-else-if="acData">
							<!-- State Banner: contextual nudge / status message at the top of the page -->
							<div v-if="acData.status === 'Ready to Submit'" class="mb-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 flex items-start gap-3">
								<FeatherIcon name="alert-triangle" class="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
								<div class="flex-1 min-w-0">
									<div class="text-sm font-extrabold text-amber-900">{{ __("Ready to submit") }}</div>
									<div class="text-xs text-amber-800 mt-0.5">{{ __("All required documents are uploaded. HR can't review until you submit.") }}</div>
								</div>
							</div>

							<div v-else-if="acData.status === 'To be Reviewed'" class="mb-2 rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 flex items-start gap-3">
								<FeatherIcon name="check-circle" class="h-5 w-5 text-blue-600 mt-0.5 shrink-0" />
								<div class="flex-1 min-w-0">
									<div class="text-sm font-extrabold text-blue-900">{{ __("Submitted for review") }}</div>
									<div class="text-xs text-blue-800 mt-0.5">
										<span v-if="acData.submitted_on">{{ __("Submitted on") }} {{ acData.submitted_on }}. </span>{{ __("HR is reviewing your documents — you'll be notified of the result.") }}
									</div>
								</div>
							</div>

							<div v-else-if="acData.status === 'Action Required'" class="mb-2 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 flex items-start gap-3">
								<FeatherIcon name="alert-circle" class="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
								<div class="flex-1 min-w-0">
									<div class="text-sm font-extrabold text-red-900">{{ __("Action required") }}</div>
									<div class="text-xs text-red-800 mt-0.5">{{ __("Some documents need attention. Please re-upload the highlighted ones below.") }}</div>
								</div>
							</div>

							<div v-else-if="acData.status === 'Accepted'" class="mb-2 rounded-2xl border border-green-200 bg-green-50 px-4 py-3 flex items-start gap-3">
								<FeatherIcon name="award" class="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
								<div class="flex-1 min-w-0">
									<div class="text-sm font-extrabold text-green-900">{{ __("Verified by HR") }}</div>
									<div class="text-xs text-green-800 mt-0.5">{{ __("Your onboarding documents are complete.") }}</div>
								</div>
							</div>

							<!-- 0. Personal Details Section (basic info, family, emergency contact) -->
							<section v-if="acData.personal_details?.length" class="space-y-4">
								<div class="flex items-center justify-between group cursor-pointer" @click="toggleSection('personal')">
									<div class="flex items-center gap-3">
										<div class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100">
											<FeatherIcon name="user" class="h-5 w-5" />
										</div>
										<div class="flex flex-col">
											<h3 class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]">{{ __("Personal Details") }}</h3>
											<span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]">{{ personalCompletedCount }} / {{ acData.personal_details.length }} {{ __("FILLED") }}</span>
										</div>
									</div>
									<FeatherIcon :name="expandedSections.personal ? 'chevron-up' : 'chevron-down'" class="h-5 w-5 text-gray-400 group-hover:text-blue-500 transition-all" />
								</div>
								<div v-if="expandedSections.personal" class="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm grid grid-cols-1 sm:grid-cols-2 gap-4 animate-in fade-in slide-in-from-top-4 duration-300">
									<div v-for="pd in acData.personal_details" :key="pd.key" class="flex flex-col gap-1.5">
										<label class="text-[10px] font-black uppercase tracking-widest text-gray-500">
											{{ pd.label }}<span v-if="pd.mandatory" class="text-red-500 ml-1">*</span>
										</label>
										<!-- Select — custom indigo popover dropdown (matches the design kit) -->
										<div v-if="pd.kind === 'select'" class="relative">
											<button
												type="button"
												:disabled="acData.submitted_for_review || acData.status === 'Accepted'"
												class="h-10 w-full px-3 rounded-xl border-2 border-gray-200 hover:border-gray-400 outline-none text-[13px] font-medium text-gray-900 bg-white disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed flex items-center justify-between gap-2 transition-colors"
												@click.stop="toggleDropdown(pd.key)"
											>
												<span :class="!pd.value ? 'text-gray-400' : ''">{{ pd.value || __('Select…') }}</span>
												<FeatherIcon name="chevron-down" class="h-3.5 w-3.5 text-gray-400 shrink-0 transition-transform" :class="{ 'rotate-180': openDropdown === pd.key }" />
											</button>
											<!-- Backdrop closes the popover when tapped outside -->
											<div v-if="openDropdown === pd.key" class="fixed inset-0 z-[80]" @click="closeDropdown"></div>
											<!-- Popover menu — matches the indigo selection style of our other buttons -->
											<div
												v-if="openDropdown === pd.key"
												class="absolute z-[81] mt-1 left-0 right-0 bg-white rounded-xl border border-gray-100 shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150"
											>
												<button
													v-for="opt in pd.options" :key="opt"
													type="button"
													class="w-full px-4 h-10 text-left text-[13px] font-medium flex items-center gap-2 transition-colors"
													:class="pd.value === opt ? '' : 'text-gray-900 hover:bg-blue-50 hover:text-blue-700'"
													:style="pd.value === opt ? 'background-color: #4f46e5; color: white;' : ''"
													@click="selectDropdownOption(pd, opt)"
												>
													<FeatherIcon
														v-if="pd.value === opt"
														name="check"
														class="h-3.5 w-3.5 shrink-0"
														style="color: white;"
													/>
													<span v-else class="w-3.5 shrink-0"></span>
													<span>{{ opt }}</span>
												</button>
											</div>
										</div>
										<!-- Date -->
										<input
											v-else-if="pd.kind === 'date'"
											type="date"
											:value="pd.value"
											:max="todayIso"
											:disabled="acData.submitted_for_review || acData.status === 'Accepted'"
											class="h-10 px-3 rounded-xl border-2 border-gray-200 focus:border-gray-400 outline-none text-[13px] font-medium text-gray-900 bg-white disabled:bg-gray-50 disabled:text-gray-500"
											@change="(e) => commitPersonalField(pd.key, e.target.value)"
										/>
										<!-- Read-only (e.g. Age) -->
										<div
											v-else-if="pd.kind === 'readonly'"
											class="h-10 px-3 rounded-xl border-2 border-dashed border-gray-200 bg-gray-50 text-[13px] font-medium text-gray-700 flex items-center"
										>
											{{ pd.value || __("—") }}
										</div>
										<!-- Phone (tel) -->
										<input
											v-else-if="pd.kind === 'tel'"
											type="tel"
											inputmode="numeric"
											pattern="[0-9]*"
											maxlength="12"
											:value="pd.value"
											:disabled="acData.submitted_for_review || acData.status === 'Accepted'"
											class="h-10 px-3 rounded-xl border-2 border-gray-200 focus:border-gray-400 outline-none text-[13px] font-medium text-gray-900 bg-white disabled:bg-gray-50 disabled:text-gray-500"
											@blur="(e) => commitPersonalField(pd.key, e.target.value)"
										/>
										<!-- Plain text -->
										<input
											v-else
											type="text"
											:value="pd.value"
											:disabled="acData.submitted_for_review || acData.status === 'Accepted'"
											class="h-10 px-3 rounded-xl border-2 border-gray-200 focus:border-gray-400 outline-none text-[13px] font-medium text-gray-900 bg-white disabled:bg-gray-50 disabled:text-gray-500"
											@blur="(e) => commitPersonalField(pd.key, e.target.value)"
										/>
										<span v-if="pd.hint" class="text-[10px] text-gray-400">{{ pd.hint }}</span>
									</div>
								</div>
							</section>

							<!-- 1. Identity Documents Section -->
							<section class="space-y-4">
								<div class="flex items-center justify-between group cursor-pointer" @click="toggleSection('docs')">
									<div class="flex items-center gap-3">
										<div class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100">
											<FeatherIcon name="file-text" class="h-5 w-5" />
										</div>
										<div class="flex flex-col">
											<h3 class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]">{{ __("Identity Documents") }}</h3>
											<span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]">{{ acData.documents?.length || 0 }} {{ __("DOCUMENTS") }}</span>
										</div>
									</div>
									<FeatherIcon :name="expandedSections.docs ? 'chevron-up' : 'chevron-down'" class="h-5 w-5 text-gray-400 group-hover:text-blue-500 transition-all" />
								</div>

								<div v-if="expandedSections.docs" class="grid grid-cols-1 gap-4 animate-in fade-in slide-in-from-top-4 duration-300">
									<div v-for="doc in acData.documents" :key="doc.key" 
										class="group relative overflow-hidden bg-white p-4 rounded-2xl border transition-all duration-300"
										:class="[
											doc.status === 'Rejected' ? 'border-red-200 bg-red-50/20' : 
											doc.status === 'Accepted' ? 'border-green-100 bg-green-50/10' : 'border-gray-100 hover:border-blue-200 shadow-sm'
										]"
									>
										<!-- Identity number/name input — sits above the file controls, full width on mobile.
										     Auto-saves on blur via commitPersonalField. -->
										<div v-if="doc.number_field" class="mb-3 flex flex-col gap-1.5">
											<label class="text-[10px] font-black uppercase tracking-widest text-gray-500">
												{{ doc.number_label }}<span class="text-red-500 ml-1">*</span>
											</label>
											<input
												type="text"
												:value="doc.number_value"
												:disabled="isDocRowLocked(doc)"
												class="h-10 px-3 rounded-xl border-2 border-gray-200 focus:border-gray-400 outline-none text-[13px] font-medium text-gray-900 bg-white disabled:bg-gray-50 disabled:text-gray-500"
												@blur="(e) => commitPersonalField(doc.number_field, e.target.value)"
											/>
											<span v-if="doc.number_hint" class="text-[10px] text-gray-400">{{ doc.number_hint }}</span>
										</div>

										<!-- Doc row: title column must not shrink — avoid w-full on sibling actions at lg (was hiding labels) -->
										<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:gap-6">
											<div class="flex items-start gap-4 flex-1 min-w-0 overflow-hidden">
												<div class="p-3 rounded-2xl shadow-sm transition-all duration-300 shrink-0" 
													:class="[
														doc.status === 'Accepted' ? 'bg-green-100 text-green-700' : 
														doc.status === 'Rejected' ? 'bg-red-100 text-red-600' : 
														doc.status === 'Awaiting HR' ? 'bg-blue-100 text-blue-600' : 'bg-gray-50 text-gray-400'
													]"
												>
													<FeatherIcon :name="doc.status === 'Accepted' ? 'check-circle' : doc.status === 'Rejected' ? 'alert-triangle' : (doc.file || doc.is_na) ? 'clock' : 'file-plus'" class="h-5 w-5" />
												</div>
												<div class="flex flex-col min-w-0 flex-1">
													<div class="text-[15px] font-extrabold text-gray-900 break-words line-clamp-2 tracking-tight leading-tight mb-1">
														{{ doc.label }}<span v-if="doc.mandatory" class="text-red-500 ml-1">*</span>
													</div>
													<div class="flex items-center gap-2">
														<span 
															class="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full"
															:class="{
																'bg-gray-100 text-gray-500 border border-gray-200': !doc.status || doc.status === 'Pending',
																'bg-blue-50 text-blue-600 border border-blue-100': doc.status === 'Awaiting HR',
																'bg-red-50 text-red-600 border border-red-200': doc.status === 'Rejected',
																'bg-green-50 text-green-600 border border-green-100': doc.status === 'Accepted'
															}"
														>
															{{ doc.status === 'Rejected' ? 'Action Required' : (doc.status || 'Pending') }}
														</span>
													</div>
												</div>
											</div>

											<!-- Actions row — hidden once row is locked (Accepted, or post-submit non-Rejected). View link still rendered separately when there's a file. -->
											<div v-if="!isDocRowLocked(doc)" class="flex flex-col gap-2 w-full shrink-0 lg:w-auto lg:max-w-none lg:flex-initial lg:flex-row lg:flex-wrap lg:items-center lg:justify-end">
												<div v-if="!doc.file || doc.is_na" class="flex items-center justify-between gap-4 bg-gray-50/50 px-3 py-2 rounded-xl border border-gray-100 w-full min-w-0 lg:w-auto lg:min-w-[12rem] lg:justify-start">
													<span class="text-[10px] font-bold uppercase tracking-widest text-gray-900 select-none">{{ __("NOT APPLICABLE") }}</span>
													<Checkbox 
														:modelValue="!!doc.is_na" 
														@update:modelValue="(val) => handleNAToggle(doc.key, !val, false, true)"
													/>
												</div>

												<Button
													v-if="!doc.is_na && (!doc.file || doc.status === 'Rejected')"
													variant="subtle"
													class="!h-9 px-4 rounded-xl bg-gray-50 text-gray-900 border border-gray-200 hover:border-gray-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
													:loading="isUploading && pendingUploadKey === doc.key"
													@click="triggerUpload(doc.key, true)"
												>
													<div class="flex items-center gap-2 justify-center">
														<FeatherIcon name="upload-cloud" class="h-3.5 w-3.5 text-blue-600" />
														<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Upload") }}</span>
													</div>
												</Button>
												
												<button
													v-if="doc.file"
													type="button"
													@click="openPreview(doc.file, doc.label)"
													class="px-4 h-9 rounded-xl bg-gray-50 text-gray-900 border border-gray-900 hover:bg-gray-100 transition-all shadow-sm active:scale-95 flex items-center justify-center gap-2 group/btn w-full lg:w-auto"
												>
													<FeatherIcon name="eye" class="h-3.5 w-3.5 group-hover/btn:scale-110 transition-transform" />
													<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View") }}</span>
												</button>

												<Button
													v-if="doc.file || doc.is_na || doc.status === 'Rejected'"
													variant="subtle"
													class="!h-9 px-4 rounded-xl bg-gray-50 text-gray-900 border border-red-200 hover:border-red-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
													@click="executeReset(doc.key, true)"
												>
													<div class="flex items-center gap-2 justify-center">
														<FeatherIcon name="trash-2" class="h-3.5 w-3.5 text-red-600" />
														<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Clear") }}</span>
													</div>
												</Button>
											</div>

											<!-- View-only link when row is locked -->
											<button
												v-else-if="doc.file"
												type="button"
												@click="openPreview(doc.file, doc.label)"
												class="px-4 h-9 rounded-xl bg-gray-50 text-gray-900 border border-gray-300 hover:bg-gray-100 transition-all shadow-sm flex items-center justify-center gap-2 w-full lg:w-auto"
											>
												<FeatherIcon name="eye" class="h-3.5 w-3.5" />
												<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View") }}</span>
											</button>
										</div>

										<!-- Rejection Reason Overlay -->
										<div v-if="doc.status === 'Rejected' && doc.remarks" class="mt-4 p-3 bg-red-100/30 rounded-xl border border-red-100/50 flex items-start gap-3">
											<div class="p-1.5 bg-red-100 text-red-600 rounded-lg">
												<FeatherIcon name="info" class="h-3.5 w-3.5" />
											</div>
											<div class="flex flex-col">
												<span class="text-[10px] font-black uppercase tracking-widest text-red-800 mb-0.5">{{ __("HR Feedback") }}</span>
												<p class="text-[11px] text-red-800 leading-relaxed italic font-medium">"{{ doc.remarks }}"</p>
											</div>
										</div>
									</div>
								</div>
							</section>

							<!-- 2. Declarations Section (Tax Regime, Medical Insurance, Bank Statement) -->
							<section v-if="acData.declarations?.length" class="space-y-4">
								<div class="flex items-center justify-between group cursor-pointer" @click="toggleSection('declarations')">
									<div class="flex items-center gap-3">
										<div class="p-2.5 rounded-xl bg-purple-50 text-purple-600 shadow-sm border border-purple-100">
											<FeatherIcon name="clipboard" class="h-5 w-5" />
										</div>
										<div class="flex flex-col">
											<h3 class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]">{{ __("Declarations") }}</h3>
											<span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]">{{ acData.declarations?.length || 0 }} {{ __("ITEMS") }}</span>
										</div>
									</div>
									<FeatherIcon :name="expandedSections.declarations ? 'chevron-up' : 'chevron-down'" class="h-5 w-5 text-gray-400 group-hover:text-purple-500 transition-all" />
								</div>

								<div v-if="expandedSections.declarations" class="grid grid-cols-1 gap-4 animate-in fade-in slide-in-from-top-4 duration-300">
									<div v-for="decl in acData.declarations" :key="decl.key"
										class="group relative overflow-hidden bg-white p-4 rounded-2xl border transition-all duration-300"
										:class="[
											decl.status === 'Rejected' ? 'border-red-200 bg-red-50/20' :
											decl.status === 'Accepted' ? 'border-green-100 bg-green-50/10' : 'border-gray-100 hover:border-purple-200 shadow-sm'
										]"
									>
										<div class="flex flex-col gap-4">
											<!-- Header row -->
											<div class="flex items-start gap-4 flex-1 min-w-0 overflow-hidden">
												<div class="p-3 rounded-2xl shadow-sm transition-all duration-300 shrink-0"
													:class="[
														decl.status === 'Accepted' ? 'bg-green-100 text-green-700' :
														decl.status === 'Rejected' ? 'bg-red-100 text-red-600' :
														decl.status === 'Awaiting HR' ? 'bg-blue-100 text-blue-600' : 'bg-gray-50 text-gray-400'
													]"
												>
													<FeatherIcon
														:name="decl.status === 'Accepted' ? 'check-circle' : decl.status === 'Rejected' ? 'alert-triangle' : (declarationHasData(decl) ? 'clock' : (decl.kind === 'file' ? 'file-plus' : 'edit-3'))"
														class="h-5 w-5"
													/>
												</div>
												<div class="flex flex-col min-w-0 flex-1">
													<div class="text-[15px] font-extrabold text-gray-900 break-words tracking-tight leading-tight mb-1">
														{{ decl.label }}<span v-if="decl.mandatory" class="text-red-500 ml-1">*</span>
													</div>
													<div v-if="decl.description" class="text-[12px] text-gray-500 leading-relaxed mb-2">
														{{ decl.description }}
													</div>
													<div class="flex items-center gap-2">
														<span
															class="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full"
															:class="{
																'bg-gray-100 text-gray-500 border border-gray-200': !decl.status || decl.status === 'Pending',
																'bg-blue-50 text-blue-600 border border-blue-100': decl.status === 'Awaiting HR',
																'bg-red-50 text-red-600 border border-red-200': decl.status === 'Rejected',
																'bg-green-50 text-green-600 border border-green-100': decl.status === 'Accepted'
															}"
														>
															{{ decl.status === 'Rejected' ? 'Action Required' : (decl.status || 'Pending') }}
														</span>
													</div>
												</div>
											</div>

											<!-- Body — kind-specific UI -->

											<!-- Select kind (Tax Regime, Medical Insurance opt-in) — matches the Submit CTA's indigo styling. Inline style on the active state so the colour survives the HRMS Tailwind purge (indigo classes aren't in the safelist). -->
											<div v-if="decl.kind === 'select' && !isDocRowLocked(decl) && !decl.is_na" class="flex flex-wrap gap-2">
												<button
													v-for="opt in decl.options" :key="opt"
													type="button"
													class="h-10 px-5 rounded-xl border-2 transition-all active:scale-95 font-black uppercase tracking-widest text-[11px] flex items-center gap-2"
													:class="decl.value === opt
														? 'text-white border-transparent'
														: 'bg-white text-gray-700 border-gray-200 hover:border-gray-400 shadow-sm'"
													:style="decl.value === opt
														? 'background-color: #4f46e5; box-shadow: 0 6px 20px rgba(79, 70, 229, 0.35);'
														: ''"
													@click="executeDeclarationSelect(decl, opt)"
												>
													<FeatherIcon v-if="decl.value === opt" name="check" class="h-3.5 w-3.5" style="color: white;" />
													<span :style="decl.value === opt ? 'color: white;' : ''">{{ opt }}</span>
												</button>
											</div>

											<!-- Medical Insurance: Opt-In flow — show assigned policy or "HR will assign" hint -->
											<div v-if="decl.key === 'medical_insurance' && decl.value === 'Opt In' && decl.linked_policy" class="rounded-xl border border-purple-100 bg-purple-50/40 px-3 py-2 flex items-center gap-3">
												<FeatherIcon name="shield" class="h-4 w-4 text-purple-600 shrink-0" />
												<div class="flex flex-col min-w-0 flex-1">
													<span class="text-[10px] font-black uppercase tracking-widest text-purple-700">{{ __("Assigned Policy") }}</span>
													<span class="text-[12px] font-bold text-gray-900 truncate">{{ decl.linked_policy }}</span>
												</div>
											</div>
											<div v-else-if="decl.key === 'medical_insurance' && decl.value === 'Opt In' && !decl.linked_policy" class="rounded-xl border border-amber-200 bg-amber-50/40 px-3 py-2 flex items-center gap-3">
												<FeatherIcon name="info" class="h-4 w-4 text-amber-600 shrink-0" />
												<span class="text-[11px] text-amber-800 font-medium">{{ __("HR will assign your policy after your opt-in is reviewed.") }}</span>
											</div>

											<!-- Medical Insurance: Opt-Out flow — show blank template (non-removable) + signed upload -->
											<div v-if="decl.key === 'medical_insurance' && decl.value === 'Opt Out'" class="flex flex-col gap-3">
												<!-- Blank declaration template (read-only, downloadable, non-removable) -->
												<div v-if="decl.optout_template_url" class="rounded-xl border border-purple-100 bg-purple-50/40 px-3 py-2.5 flex items-center gap-3">
													<FeatherIcon name="file-text" class="h-4 w-4 text-purple-600 shrink-0" />
													<div class="flex flex-col min-w-0 flex-1">
														<span class="text-[10px] font-black uppercase tracking-widest text-purple-700">{{ __("Opt-Out Declaration") }}</span>
														<span class="text-[12px] font-bold text-gray-900 truncate">{{ decl.optout_template_name || __("Declaration Template") }}</span>
														<span class="text-[10px] text-gray-500 mt-0.5">{{ __("Download, sign, and upload the signed copy below.") }}</span>
													</div>
													<button
														type="button"
														@click="openPreview(decl.optout_template_url, decl.optout_template_name || __('Declaration Template'))"
														class="px-3 h-8 rounded-lg bg-white text-purple-700 border border-purple-300 hover:bg-purple-100 transition-all shadow-sm flex items-center gap-1.5 shrink-0"
													>
														<FeatherIcon name="download" class="h-3.5 w-3.5" />
														<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Download") }}</span>
													</button>
												</div>
												<div v-else class="rounded-xl border border-amber-200 bg-amber-50/40 px-3 py-2 flex items-center gap-3">
													<FeatherIcon name="alert-circle" class="h-4 w-4 text-amber-600 shrink-0" />
													<span class="text-[11px] text-amber-800 font-medium">{{ __("HR has not uploaded the opt-out declaration template yet. Please contact HR.") }}</span>
												</div>

												<!-- Signed declaration upload (no Clear — non-removable once uploaded) -->
												<div v-if="!isDocRowLocked(decl)" class="flex flex-col gap-2 lg:flex-row lg:items-center lg:flex-wrap">
													<Button
														v-if="!decl.signed_optout_file"
														variant="subtle"
														class="!h-9 px-4 rounded-xl bg-gray-50 text-gray-900 border border-gray-200 hover:border-purple-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
														:loading="isUploading && pendingUploadKey === 'medical_insurance_signed_optout'"
														@click="triggerSignedOptOutUpload()"
													>
														<div class="flex items-center gap-2 justify-center">
															<FeatherIcon name="upload-cloud" class="h-3.5 w-3.5 text-purple-600" />
															<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Upload Signed Declaration") }}</span>
														</div>
													</Button>
													<button
														v-if="decl.signed_optout_file"
														type="button"
														@click="openPreview(decl.signed_optout_file, __('Signed Declaration'))"
														class="px-4 h-9 rounded-xl bg-gray-50 text-gray-900 border border-gray-900 hover:bg-gray-100 transition-all shadow-sm active:scale-95 flex items-center justify-center gap-2 w-full lg:w-auto"
													>
														<FeatherIcon name="eye" class="h-3.5 w-3.5" />
														<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View Signed Declaration") }}</span>
													</button>
													<Button
														v-if="decl.signed_optout_file"
														variant="subtle"
														class="!h-9 px-4 rounded-xl bg-gray-50 text-gray-900 border border-gray-200 hover:border-purple-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
														:loading="isUploading && pendingUploadKey === 'medical_insurance_signed_optout'"
														@click="triggerSignedOptOutUpload()"
													>
														<div class="flex items-center gap-2 justify-center">
															<FeatherIcon name="refresh-cw" class="h-3.5 w-3.5 text-purple-600" />
															<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Replace Signed Copy") }}</span>
														</div>
													</Button>
												</div>
												<button
													v-else-if="decl.signed_optout_file"
													type="button"
													@click="openPreview(decl.signed_optout_file, __('Signed Declaration'))"
													class="px-4 h-9 rounded-xl bg-gray-50 text-gray-900 border border-gray-300 hover:bg-gray-100 transition-all shadow-sm flex items-center justify-center gap-2 w-full lg:w-auto"
												>
													<FeatherIcon name="eye" class="h-3.5 w-3.5" />
													<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View Signed Declaration") }}</span>
												</button>
											</div>

											<!-- File kind (Bank Statement 6m) -->
											<div v-if="decl.kind === 'file' && !isDocRowLocked(decl)" class="flex flex-col gap-2 lg:flex-row lg:items-center lg:flex-wrap">
												<Button
													v-if="!decl.is_na && (!decl.file || decl.status === 'Rejected')"
													variant="subtle"
													class="!h-9 px-4 rounded-xl bg-gray-50 text-gray-900 border border-gray-200 hover:border-gray-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
													:loading="isUploading && pendingUploadKey === decl.key"
													@click="triggerUpload(decl.key, true)"
												>
													<div class="flex items-center gap-2 justify-center">
														<FeatherIcon name="upload-cloud" class="h-3.5 w-3.5 text-blue-600" />
														<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Upload") }}</span>
													</div>
												</Button>

												<button
													v-if="decl.file"
													type="button"
													@click="openPreview(decl.file, decl.label)"
													class="px-4 h-9 rounded-xl bg-gray-50 text-gray-900 border border-gray-900 hover:bg-gray-100 transition-all shadow-sm active:scale-95 flex items-center justify-center gap-2 w-full lg:w-auto"
												>
													<FeatherIcon name="eye" class="h-3.5 w-3.5" />
													<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View") }}</span>
												</button>

												<Button
													v-if="decl.file || decl.is_na || decl.status === 'Rejected'"
													variant="subtle"
													class="!h-9 px-4 rounded-xl bg-gray-50 text-gray-900 border border-red-200 hover:border-red-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
													@click="executeReset(decl.key, true)"
												>
													<div class="flex items-center gap-2 justify-center">
														<FeatherIcon name="trash-2" class="h-3.5 w-3.5 text-red-600" />
														<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Clear") }}</span>
													</div>
												</Button>
											</div>

											<!-- N/A toggle (always available unless locked) -->
											<div v-if="!isDocRowLocked(decl)" class="flex items-center justify-between gap-4 bg-gray-50/50 px-3 py-2 rounded-xl border border-gray-100">
												<span class="text-[10px] font-bold uppercase tracking-widest text-gray-900 select-none">{{ __("NOT APPLICABLE") }}</span>
												<Checkbox
													:modelValue="!!decl.is_na"
													@update:modelValue="(val) => handleDeclarationNA(decl, !val)"
												/>
											</div>

											<!-- Locked view-only file link -->
											<button
												v-if="decl.kind === 'file' && isDocRowLocked(decl) && decl.file"
												type="button"
												@click="openPreview(decl.file, decl.label)"
												class="px-4 h-9 rounded-xl bg-gray-50 text-gray-900 border border-gray-300 hover:bg-gray-100 transition-all shadow-sm flex items-center justify-center gap-2 w-full lg:w-auto"
											>
												<FeatherIcon name="eye" class="h-3.5 w-3.5" />
												<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View") }}</span>
											</button>

											<!-- Rejection reason -->
											<div v-if="decl.status === 'Rejected' && decl.remarks" class="p-3 bg-red-100/30 rounded-xl border border-red-100/50 flex items-start gap-3">
												<div class="p-1.5 bg-red-100 text-red-600 rounded-lg shrink-0">
													<FeatherIcon name="info" class="h-3.5 w-3.5" />
												</div>
												<div class="flex flex-col">
													<span class="text-[10px] font-black uppercase tracking-widest text-red-800 mb-0.5">{{ __("HR Feedback") }}</span>
													<p class="text-[11px] text-red-800 leading-relaxed italic font-medium">"{{ decl.remarks }}"</p>
												</div>
											</div>
										</div>
									</div>
								</div>
							</section>

							<!-- 2.5. Statutory & Bank Section -->
							<section v-if="acData.statutory_bank?.length" class="space-y-4">
								<div class="flex items-center justify-between group cursor-pointer" @click="toggleSection('statbank')">
									<div class="flex items-center gap-3">
										<div class="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 shadow-sm border border-emerald-100">
											<FeatherIcon name="credit-card" class="h-5 w-5" />
										</div>
										<div class="flex flex-col">
											<h3 class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]">{{ __("Statutory & Bank") }}</h3>
											<span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest tracking-[0.05em]">{{ statutoryBankCompletedCount }} / {{ statutoryBankTotalCount }} {{ __("FILLED") }}</span>
										</div>
									</div>
									<FeatherIcon :name="expandedSections.statbank ? 'chevron-up' : 'chevron-down'" class="h-5 w-5 text-gray-400 group-hover:text-emerald-500 transition-all" />
								</div>
								<div v-if="expandedSections.statbank" class="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm grid grid-cols-1 sm:grid-cols-2 gap-4 animate-in fade-in slide-in-from-top-4 duration-300">
									<div v-for="sb in acData.statutory_bank" :key="sb.key" class="flex flex-col gap-1.5">
										<label class="text-[10px] font-black uppercase tracking-widest text-gray-500">
											{{ sb.label }}<span v-if="sb.mandatory" class="text-red-500 ml-1">*</span>
										</label>
										<input
											:type="sb.kind === 'tel' ? 'tel' : 'text'"
											:inputmode="sb.kind === 'tel' ? 'numeric' : 'text'"
											:value="sb.value"
											:disabled="acData.submitted_for_review || acData.status === 'Accepted'"
											class="h-10 px-3 rounded-xl border-2 border-gray-200 focus:border-gray-400 outline-none text-[13px] font-medium text-gray-900 bg-white disabled:bg-gray-50 disabled:text-gray-500"
											@blur="(e) => commitPersonalField(sb.key, e.target.value)"
										/>
										<span v-if="sb.hint" class="text-[10px] text-gray-400">{{ sb.hint }}</span>
									</div>
								</div>

								<!-- Statutory forms (Form 1 / Form 2 / Form F / PF Form 11) — same upload / N-A / HR-status card as the file-kind declaration. -->
								<div v-if="expandedSections.statbank && acData.statutory_forms?.length" class="grid grid-cols-1 gap-4 animate-in fade-in slide-in-from-top-4 duration-300">
									<div v-for="sf in acData.statutory_forms" :key="sf.key"
										class="group relative overflow-hidden bg-white p-4 rounded-2xl border transition-all duration-300"
										:class="[
											sf.status === 'Rejected' ? 'border-red-200 bg-red-50/20' :
											sf.status === 'Accepted' ? 'border-green-100 bg-green-50/10' : 'border-gray-100 hover:border-emerald-200 shadow-sm'
										]"
									>
										<div class="flex flex-col gap-4">
											<!-- Header row -->
											<div class="flex items-start gap-4 flex-1 min-w-0 overflow-hidden">
												<div class="p-3 rounded-2xl shadow-sm transition-all duration-300 shrink-0"
													:class="[
														sf.status === 'Accepted' ? 'bg-green-100 text-green-700' :
														sf.status === 'Rejected' ? 'bg-red-100 text-red-600' :
														sf.status === 'Awaiting HR' ? 'bg-blue-100 text-blue-600' : 'bg-gray-50 text-gray-400'
													]"
												>
													<FeatherIcon
														:name="sf.status === 'Accepted' ? 'check-circle' : sf.status === 'Rejected' ? 'alert-triangle' : (declarationHasData(sf) ? 'clock' : 'file-plus')"
														class="h-5 w-5"
													/>
												</div>
												<div class="flex flex-col min-w-0 flex-1">
													<div class="text-[15px] font-extrabold text-gray-900 break-words tracking-tight leading-tight mb-1">
														{{ sf.label }}<span v-if="sf.mandatory" class="text-red-500 ml-1">*</span>
													</div>
													<div class="flex items-center gap-2">
														<span
															class="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full"
															:class="{
																'bg-gray-100 text-gray-500 border border-gray-200': !sf.status || sf.status === 'Pending',
																'bg-blue-50 text-blue-600 border border-blue-100': sf.status === 'Awaiting HR',
																'bg-red-50 text-red-600 border border-red-200': sf.status === 'Rejected',
																'bg-green-50 text-green-600 border border-green-100': sf.status === 'Accepted'
															}"
														>
															{{ sf.status === 'Rejected' ? 'Action Required' : (sf.status || 'Pending') }}
														</span>
													</div>
												</div>
											</div>

											<!-- Upload / View / Clear -->
											<div v-if="!isDocRowLocked(sf)" class="flex flex-col gap-2 lg:flex-row lg:items-center lg:flex-wrap">
												<Button
													v-if="!sf.is_na && (!sf.file || sf.status === 'Rejected')"
													variant="subtle"
													class="!h-9 px-4 rounded-xl bg-gray-50 text-gray-900 border border-gray-200 hover:border-gray-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
													:loading="isUploading && pendingUploadKey === sf.key"
													@click="triggerUpload(sf.key, true)"
												>
													<div class="flex items-center gap-2 justify-center">
														<FeatherIcon name="upload-cloud" class="h-3.5 w-3.5 text-blue-600" />
														<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Upload") }}</span>
													</div>
												</Button>

												<button
													v-if="sf.file"
													type="button"
													@click="openPreview(sf.file, sf.label)"
													class="px-4 h-9 rounded-xl bg-gray-50 text-gray-900 border border-gray-900 hover:bg-gray-100 transition-all shadow-sm active:scale-95 flex items-center justify-center gap-2 w-full lg:w-auto"
												>
													<FeatherIcon name="eye" class="h-3.5 w-3.5" />
													<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View") }}</span>
												</button>

												<Button
													v-if="sf.file || sf.is_na || sf.status === 'Rejected'"
													variant="subtle"
													class="!h-9 px-4 rounded-xl bg-gray-50 text-gray-900 border border-red-200 hover:border-red-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
													@click="executeReset(sf.key, true)"
												>
													<div class="flex items-center gap-2 justify-center">
														<FeatherIcon name="trash-2" class="h-3.5 w-3.5 text-red-600" />
														<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Clear") }}</span>
													</div>
												</Button>
											</div>

											<!-- N/A toggle -->
											<div v-if="!isDocRowLocked(sf)" class="flex items-center justify-between gap-4 bg-gray-50/50 px-3 py-2 rounded-xl border border-gray-100">
												<span class="text-[10px] font-bold uppercase tracking-widest text-gray-900 select-none">{{ __("NOT APPLICABLE") }}</span>
												<Checkbox
													:modelValue="!!sf.is_na"
													@update:modelValue="(val) => handleDeclarationNA(sf, !val)"
												/>
											</div>

											<!-- Locked view-only file link -->
											<button
												v-if="isDocRowLocked(sf) && sf.file"
												type="button"
												@click="openPreview(sf.file, sf.label)"
												class="px-4 h-9 rounded-xl bg-gray-50 text-gray-900 border border-gray-300 hover:bg-gray-100 transition-all shadow-sm flex items-center justify-center gap-2 w-full lg:w-auto"
											>
												<FeatherIcon name="eye" class="h-3.5 w-3.5" />
												<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View") }}</span>
											</button>

											<!-- Rejection reason -->
											<div v-if="sf.status === 'Rejected' && sf.remarks" class="p-3 bg-red-100/30 rounded-xl border border-red-100/50 flex items-start gap-3">
												<div class="p-1.5 bg-red-100 text-red-600 rounded-lg shrink-0">
													<FeatherIcon name="info" class="h-3.5 w-3.5" />
												</div>
												<div class="flex flex-col">
													<span class="text-[10px] font-black uppercase tracking-widest text-red-800 mb-0.5">{{ __("HR Feedback") }}</span>
													<p class="text-[11px] text-red-800 leading-relaxed italic font-medium">"{{ sf.remarks }}"</p>
												</div>
											</div>
										</div>
									</div>
								</div>
							</section>

							<!-- 3. Employment History Section -->
							<section v-if="acData.employers?.length" class="space-y-4">
								<div class="flex items-center justify-between group cursor-pointer" @click="toggleSection('employers')">
									<div class="flex items-center gap-3">
										<div class="p-2.5 rounded-xl bg-blue-50 text-blue-600 shadow-sm border border-blue-100">
											<FeatherIcon name="briefcase" class="h-5 w-5" />
										</div>
										<div class="flex flex-col">
											<h3 class="text-sm font-black text-gray-900 uppercase tracking-wide tracking-[0.1em]">{{ __("Employment History") }}</h3>
											<span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{{ acData.employers.filter(e => !e.is_na).length }} {{ __("TOTAL RECORDS") }}</span>
										</div>
									</div>
									<FeatherIcon :name="expandedSections.employers ? 'chevron-up' : 'chevron-down'" class="h-5 w-5 text-gray-400 group-hover:text-blue-500 transition-all" />
								</div>

								<div v-if="expandedSections.employers" class="grid grid-cols-1 gap-4 animate-in fade-in slide-in-from-top-4 duration-300">
									<div v-for="emp in visibleEmployers" :key="emp.key"
										class="group bg-white rounded-2xl border transition-all duration-300 overflow-hidden"
										:class="[
											emp.status === 'Rejected' ? 'border-red-200 bg-red-50/20' : 
											emp.status === 'Accepted' ? 'border-green-100 bg-green-50/5' : 'border-gray-100 hover:shadow-lg'
										]"
									>
										<div class="flex w-full items-stretch hover:bg-gray-50/60 transition-colors">
											<button
												type="button"
												class="flex flex-1 items-center gap-3 p-4 sm:p-5 text-left min-w-0"
												@click="toggleEmployerCard(emp.key)"
											>
												<div class="p-2.5 rounded-xl shadow-sm shrink-0"
													:class="[
														emp.status === 'Accepted' ? 'bg-green-100 text-green-700' :
														emp.status === 'Rejected' ? 'bg-red-100 text-red-600' :
														emp.status === 'Awaiting HR' ? 'bg-blue-50 text-blue-600' : 'bg-gray-50 text-gray-400'
													]"
												>
													<FeatherIcon :name="emp.status === 'Accepted' ? 'shield' : emp.status === 'Awaiting HR' ? 'file-text' : 'file-plus'" class="h-5 w-5" />
												</div>
												<div class="flex-1 min-w-0">
													<div class="flex flex-wrap gap-1 mb-0.5">
														<p v-if="emp.status === 'Accepted'" class="text-[9px] font-black uppercase tracking-widest text-green-600 bg-green-50 px-2 py-0.5 rounded-md border border-green-100">{{ __("VERIFIED") }}</p>
														<p v-else-if="emp.status === 'Rejected'" class="text-[9px] font-black uppercase tracking-widest text-red-600 bg-red-50 px-2 py-0.5 rounded-md border border-red-200">{{ __("ACTION REQUIRED") }}</p>
														<p v-else-if="emp.status === 'Awaiting HR'" class="text-[9px] font-black uppercase tracking-widest text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-100">{{ __("AWAITING HR") }}</p>
														<p v-else class="text-[9px] font-black uppercase tracking-widest text-gray-400 bg-gray-50 px-2 py-0.5 rounded-md border border-gray-100">{{ __("PENDING") }}</p>
													</div>
													<div class="text-sm font-bold text-gray-900 truncate">
														{{ emp.name && emp.name.trim()
															? emp.name
															: (emp.key === "employer_1"
																? __("Most Recent Employer")
																: `${__("Previous Employer")} ${emp.key.replace("employer_", "")}`) }}
													</div>
													<div v-if="emp.from_date || emp.till_date" class="text-[11px] text-gray-500 mt-0.5 truncate">
														{{ emp.from_date || "—" }} → {{ emp.till_date || "—" }}
													</div>
												</div>
												<FeatherIcon
													:name="isEmployerCardOpen(emp.key) ? 'chevron-up' : 'chevron-down'"
													class="h-5 w-5 text-gray-400 shrink-0"
												/>
											</button>
											<!-- Remove an empty user-added Previous Employer slot (undo an
											     accidental "Add Previous Employer"). Hidden once the slot
											     has any data — for those, N/A is the right path. -->
											<button
												v-if="canRemoveEmployer(emp)"
												type="button"
												class="flex items-center justify-center w-10 sm:w-12 text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors border-l border-gray-100"
												:aria-label="__('Remove this employer slot')"
												:title="__('Remove this employer slot')"
												@click.stop="removePreviousEmployer(emp.key)"
											>
												<FeatherIcon name="x" class="h-4 w-4" />
											</button>
										</div>

										<div
											v-show="isEmployerCardOpen(emp.key)"
											class="px-4 pb-5 pt-0 sm:px-6 border-t border-gray-100 space-y-5"
										>
											<!-- Most Recent Employer "No prior employer" toggle.
											     Lets a fresher / first-time hire skip the entire employer 1 block.
											     When ticked the controller wipes name/from/till + every sub-doc file
											     and treats the slot's mandatory docs as auto-satisfied. -->
											<div
												v-if="emp.key === 'employer_1'"
												class="flex items-center justify-between gap-3 mt-2 px-3 py-2 rounded-xl border bg-gray-50/50"
												:class="emp.is_na ? 'border-gray-200' : 'border-gray-100'"
											>
												<div class="flex flex-col gap-0.5 min-w-0">
													<div class="flex items-center gap-2">
														<span class="text-[10px] font-black text-gray-900 uppercase tracking-widest">{{ __("No Prior Employer") }}</span>
														<span
															v-if="emp.is_na"
															class="text-[9px] font-black uppercase tracking-widest text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md border border-gray-200"
														>{{ __("MARKED N/A") }}</span>
													</div>
													<span class="text-[11px] text-gray-500">{{ __("Tick if this is your first job — skips Most Recent and clears any Previous Employers.") }}</span>
												</div>
												<Checkbox
													:modelValue="!!emp.is_na"
													:disabled="isEmployerCardLocked(emp)"
													@update:modelValue="(val) => handleNAToggle(emp.key + '_is_na', !val, false, false)"
												/>
											</div>

											<!-- Hide name/from/till + sub-doc rows when employer 1 is marked N/A. -->
											<div v-if="!(emp.key === 'employer_1' && emp.is_na)" class="flex flex-col gap-5 mt-2">
												<div class="flex flex-col gap-2">
													<span class="text-[10px] font-black text-gray-700 uppercase tracking-widest">{{ __("Employer Name") }}</span>
													<input
														type="text"
														v-model="emp.name"
														:disabled="isEmployerCardLocked(emp)"
														@change="onEmployerMetaCommit(emp, 'name')"
														@blur="onEmployerMetaCommit(emp, 'name')"
														class="w-full h-10 px-4 rounded-xl border border-gray-100 bg-gray-50/50 text-sm font-bold text-gray-900 focus:bg-white focus:border-blue-400 focus:ring-4 focus:ring-blue-50 transition-all placeholder:text-gray-300 outline-none"
														placeholder="Enter Employer Name"
													/>
												</div>
												<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
													<div class="flex flex-col gap-1.5">
														<span class="text-[10px] font-black text-gray-700 uppercase tracking-widest">{{ __("From") }}</span>
														<input
															type="date"
															v-model="emp.from_date"
															:disabled="isEmployerCardLocked(emp)"
															@change="onEmployerMetaCommit(emp, 'from_date')"
															@blur="onEmployerMetaCommit(emp, 'from_date')"
															:class="[
																'w-full h-10 px-4 rounded-xl border bg-gray-50/50 text-sm font-bold text-gray-900 focus:bg-white transition-all outline-none',
																employerDateError(emp)
																	? 'border-red-300 focus:border-red-500 focus:ring-4 focus:ring-red-50'
																	: 'border-gray-100 focus:border-blue-400 focus:ring-4 focus:ring-blue-50',
															]"
														/>
													</div>
													<div class="flex flex-col gap-1.5">
														<span class="text-[10px] font-black text-gray-700 uppercase tracking-widest">{{ __("Till") }}</span>
														<input
															type="date"
															v-model="emp.till_date"
															:disabled="isEmployerCardLocked(emp)"
															@change="onEmployerMetaCommit(emp, 'till_date')"
															@blur="onEmployerMetaCommit(emp, 'till_date')"
															:class="[
																'w-full h-10 px-4 rounded-xl border bg-gray-50/50 text-sm font-bold text-gray-900 focus:bg-white transition-all outline-none',
																employerDateError(emp)
																	? 'border-red-300 focus:border-red-500 focus:ring-4 focus:ring-red-50'
																	: 'border-gray-100 focus:border-blue-400 focus:ring-4 focus:ring-blue-50',
															]"
														/>
													</div>
												</div>
												<div
													v-if="employerDateError(emp)"
													class="flex items-center gap-1.5 -mt-2 text-[11px] font-bold text-red-600"
												>
													<FeatherIcon name="alert-circle" class="h-3.5 w-3.5 shrink-0" />
													<span>{{ employerDateError(emp) }}</span>
												</div>
											</div>

											<div v-if="emp.key === 'employer_1' && emp.documents?.length && !emp.is_na" class="space-y-3 pt-4 border-t border-gray-100">
												<div
													v-for="docRow in emp.documents"
													:key="docRow.key"
													class="rounded-xl border border-gray-100 p-3 bg-gray-50/50"
												>
													<div class="flex items-start justify-between gap-3">
														<div class="min-w-0">
															<div class="text-xs font-bold text-gray-900 break-words">
																{{ docRow.label }}<span v-if="docRow.mandatory" class="text-red-500 ml-1">*</span>
															</div>
															<div class="mt-1 flex items-center gap-2 flex-wrap">
																<p v-if="docRow.mandatory" class="text-[9px] font-black uppercase tracking-widest text-orange-700 bg-orange-50 px-2 py-0.5 rounded-md border border-orange-200">{{ __("REQUIRED") }}</p>
																<p v-else class="text-[9px] font-black uppercase tracking-widest text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md border border-gray-200">{{ __("OPTIONAL") }}</p>
																<p v-if="docRow.status === 'Rejected'" class="text-[9px] font-black uppercase tracking-widest text-red-600 bg-red-50 px-2 py-0.5 rounded-md border border-red-200">{{ __("ACTION REQUIRED") }}</p>
																<p v-else-if="docRow.status === 'Accepted'" class="text-[9px] font-black uppercase tracking-widest text-green-600 bg-green-50 px-2 py-0.5 rounded-md border border-green-200">{{ __("VERIFIED") }}</p>
																<p v-else-if="docRow.file" class="text-[9px] font-black uppercase tracking-widest text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-200">{{ __("AWAITING HR") }}</p>
																<p v-else class="text-[9px] font-black uppercase tracking-widest text-gray-400 bg-gray-50 px-2 py-0.5 rounded-md border border-gray-100">{{ __("PENDING") }}</p>
															</div>
														</div>
														<div class="flex flex-col gap-2 w-full sm:w-auto sm:flex-row sm:flex-wrap sm:justify-end">
															<Button
																v-if="!isDocRowLocked(docRow) && (!docRow.file || docRow.status === 'Rejected')"
																variant="subtle"
																class="!h-8 px-3 rounded-lg bg-gray-50 text-gray-900 border border-gray-200 hover:border-gray-400 transition-all shadow-sm font-normal w-full justify-center sm:w-auto"
																:loading="isUploading && pendingUploadKey === docRow.key"
																@click="triggerEmployer1DocUpload(docRow.key)"
															>
																<div class="flex items-center gap-1.5 justify-center">
																	<FeatherIcon name="upload-cloud" class="h-3.5 w-3.5 text-blue-600" />
																	<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Upload") }}</span>
																</div>
															</Button>

															<button
																v-if="docRow.file"
																type="button"
																@click="openPreview(docRow.file, docRow.label)"
																class="px-3 h-8 rounded-lg bg-gray-50 text-gray-900 border border-gray-900 hover:bg-gray-100 transition-all shadow-sm flex items-center justify-center gap-1.5 w-full sm:w-auto"
															>
																<FeatherIcon name="eye" class="h-3.5 w-3.5" />
																<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View") }}</span>
															</button>

															<Button
																v-if="!isDocRowLocked(docRow) && (docRow.file || docRow.status === 'Rejected')"
																variant="subtle"
																class="!h-8 px-3 rounded-lg text-gray-900 border border-red-200 bg-gray-50 hover:border-red-400 transition-all shadow-sm font-normal w-full justify-center sm:w-auto"
																@click="executeEmployer1DocReset(docRow.key)"
															>
																<div class="flex items-center gap-1.5 justify-center">
																	<FeatherIcon name="trash-2" class="h-3.5 w-3.5 text-red-600" />
																	<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Clear") }}</span>
																</div>
															</Button>
														</div>
													</div>
													<div v-if="docRow.status === 'Rejected' && docRow.remarks" class="mt-2 text-[11px] text-red-700 bg-red-50 border border-red-100 rounded-lg px-2.5 py-2">
														{{ docRow.remarks }}
													</div>
												</div>
											</div>

											<!-- Doc-type subtitle for Employer 2-5. The doc is conditionally required:
											     once any employer detail is entered, the employee must either upload the
											     relieving letter or mark the slot Not Applicable. -->
											<div v-if="emp.key !== 'employer_1'" class="pt-4 border-t border-gray-100">
												<div class="flex items-center gap-2 flex-wrap">
													<span class="text-xs font-bold text-gray-900">{{ __("Relieving Letter / Resignation Acceptance") }}</span>
													<span
														v-if="employerNeedsAction(emp)"
														class="text-[9px] font-black uppercase tracking-widest text-red-700 bg-red-50 px-2 py-0.5 rounded-md border border-red-200"
													>{{ __("DOCUMENT NEEDED") }}</span>
													<span
														v-else-if="emp.is_na"
														class="text-[9px] font-black uppercase tracking-widest text-gray-500 bg-gray-100 px-2 py-0.5 rounded-md border border-gray-200"
													>{{ __("MARKED N/A") }}</span>
												</div>
											</div>

											<div class="flex flex-col gap-4 pt-4 border-t border-gray-100 lg:flex-row lg:items-start lg:justify-between">
												<div class="flex flex-col min-w-0 lg:max-w-[40%]">
													<span class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">{{ __("Status") }}</span>
													<div class="flex flex-wrap items-center gap-2">
														<p v-if="emp.status === 'Accepted'" class="text-[9px] font-black uppercase tracking-widest text-green-600 bg-green-50 px-2 py-0.5 rounded-md border border-green-100">{{ __("VERIFIED") }}</p>
														<p v-else-if="emp.status === 'Rejected'" class="text-[9px] font-black uppercase tracking-widest text-red-600 bg-red-50 px-2 py-0.5 rounded-md border border-red-200">{{ __("ACTION REQUIRED") }}</p>
														<p v-else-if="emp.status === 'Awaiting HR'" class="text-[9px] font-black uppercase tracking-widest text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-100">{{ __("AWAITING HR") }}</p>
														<p v-else class="text-[9px] font-black uppercase tracking-widest text-gray-400 bg-gray-50 px-2 py-0.5 rounded-md border border-gray-100">{{ __("PENDING") }}</p>
													</div>
												</div>

												<div class="flex flex-col gap-2 w-full lg:flex-1 lg:min-w-0 lg:items-end">
													<div v-if="!isEmployerCardLocked(emp) && emp.key !== 'employer_1'" class="flex flex-col gap-2 w-full lg:flex-row lg:flex-wrap lg:justify-end">
														<Button
															variant="subtle"
															class="!h-9 px-4 rounded-xl bg-blue-50 text-blue-900 border border-blue-200 hover:border-blue-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
															:loading="savingEmployerKey === emp.key"
															@click="saveEmployer(emp)"
														>
															<div class="flex items-center gap-2 justify-center">
																<FeatherIcon name="save" class="h-3.5 w-3.5 text-blue-600" />
																<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Save") }}</span>
															</div>
														</Button>

														<div v-if="!emp.file || emp.is_na" class="flex items-center justify-between gap-4 bg-gray-50/50 px-3 py-2 rounded-xl border border-gray-100 w-full lg:max-w-xs">
															<span class="text-[10px] font-bold uppercase tracking-widest text-gray-900 select-none">{{ __("NOT APPLICABLE") }}</span>
															<Checkbox 
																:modelValue="!!emp.is_na"
																:disabled="isEmployerCardLocked(emp)"
																@update:modelValue="(val) => handleNAToggle(emp.key + '_is_na', !val, false, false)"
															/>
														</div>

														<Button
															v-if="!emp.is_na && (!emp.file || emp.status === 'Rejected')"
															variant="subtle"
															class="!h-9 px-4 rounded-xl bg-gray-50 text-gray-900 border border-gray-200 hover:border-gray-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
															:loading="isUploading && pendingUploadKey === emp.key + '_doc'"
															@click="triggerUpload(emp.key + '_doc', false)"
														>
															<div class="flex items-center gap-2 justify-center">
																<FeatherIcon name="upload-cloud" class="h-3.5 w-3.5 text-blue-600" />
																<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Upload") }}</span>
															</div>
														</Button>

														<button
															v-if="emp.file"
															type="button"
															@click="openPreview(emp.file, emp.label)"
															class="px-4 h-9 rounded-xl bg-gray-50 text-gray-900 border border-gray-900 hover:bg-gray-100 transition-all shadow-sm active:scale-95 flex items-center justify-center gap-2 group/btn w-full lg:w-auto"
														>
															<FeatherIcon name="eye" class="h-3.5 w-3.5 group-hover/btn:scale-110 transition-transform" />
															<span class="text-[9px] font-black uppercase tracking-widest">{{ __("View") }}</span>
														</button>

														<Button 
															v-if="emp.file || emp.is_na || emp.status === 'Rejected'"
															variant="subtle" 
															class="!h-9 px-4 rounded-xl text-gray-900 border border-red-200 bg-gray-50 hover:border-red-400 transition-all active:scale-95 shadow-sm font-normal w-full justify-center lg:w-auto"
															@click="executeReset(emp.key + '_doc', false)"
														>
															<div class="flex items-center gap-2 justify-center">
																<FeatherIcon name="trash-2" class="h-3.5 w-3.5 text-red-600" />
																<span class="text-[9px] font-black uppercase tracking-widest">{{ __("Clear") }}</span>
															</div>
														</Button>
													</div>
													<!-- Locked-state pill: only for employer slots 2-5 that HR has Accepted.
													     Employer 1 has its own per-split-doc statuses above and shouldn't render
													     a card-level "Accepted" pill from a layout-conditional v-else. -->
													<div v-else-if="emp.key !== 'employer_1' && isEmployerCardLocked(emp) && emp.status === 'Accepted'" class="w-full lg:flex lg:justify-end">
														<div class="px-4 h-9 bg-green-50 text-green-700 border border-green-200 rounded-xl flex items-center justify-center gap-2 w-full lg:w-auto">
															<FeatherIcon name="check-circle" class="h-3.5 w-3.5" />
															<span class="text-[9px] font-black uppercase tracking-widest leading-none">{{ __("Accepted") }}</span>
														</div>
													</div>
												</div>
											</div>
										</div>
									</div>
								<!-- Dynamic add: Employer 1 is always shown; slots 2-5 appear when they have data or
								     when the user explicitly clicks "Add". Capped at 5 total. -->
								<button
									v-if="expandedSections.employers && canAddPreviousEmployer"
									type="button"
									class="w-full rounded-2xl border-2 border-dashed border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50/30 transition-all p-4 flex items-center justify-center gap-2 text-blue-600"
									@click="addPreviousEmployer"
								>
									<FeatherIcon name="plus-circle" class="h-4 w-4" />
									<span class="text-[10px] font-black uppercase tracking-widest">{{ __("Add Previous Employer") }}</span>
								</button>
								<div
									v-else-if="expandedSections.employers && visibleEmployers.length >= 5"
									class="w-full rounded-2xl border-2 border-dashed border-gray-100 bg-gray-50/50 p-4 flex items-center justify-center gap-2 text-gray-400"
								>
									<FeatherIcon name="info" class="h-4 w-4" />
									<span class="text-[10px] font-black uppercase tracking-widest">{{ __("Maximum 5 employers") }}</span>
								</div>
								</div>
							</section>

							<!-- Policies live on /policies now (own doctype, own page). -->
						</template>
					</div>

					<!-- Hidden file input for native upload (matches Frappe ALLOWED_MIMETYPES) -->
				<input
					type="file"
					ref="fileInputRef"
					class="hidden"
					accept=".jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.xls,.xlsx,.odt,.ods,.txt,.csv,.mp4,.mov"
					@change="onFileChosen"
				/>

				<!-- Sticky Bottom Submit Bar — always visible while the AC is in flight.
				     The Submit CTA is only "live" (blue + clickable) when `canSubmitForReview`
				     is true; otherwise it's greyed out and the caption tells the user what's
				     blocking. Stacked on mobile so the CTA is full-width and unmissable. -->
				<div
					v-if="acData && !acData.submitted_for_review && acData.status !== 'Accepted'"
					class="sticky bottom-0 bg-white border-t-2 px-4 py-3 z-40"
					:class="canSubmitForReview ? 'border-blue-100 shadow-[0_-8px_24px_rgba(79,70,229,0.12)]' : 'border-amber-100 shadow-[0_-8px_24px_rgba(251,191,36,0.12)]'"
					style="padding-bottom: calc(0.75rem + env(safe-area-inset-bottom));"
				>
					<div class="flex flex-col gap-2 max-w-4xl mx-auto">
						<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
							<div class="flex items-center gap-2 text-xs font-bold min-w-0">
								<FeatherIcon
									v-if="canSubmitForReview"
									name="check-circle"
									class="h-4 w-4 text-green-600 shrink-0"
								/>
								<FeatherIcon
									v-else
									name="alert-triangle"
									class="h-4 w-4 text-amber-600 shrink-0"
								/>
								<span
									class="truncate"
									:class="canSubmitForReview ? 'text-gray-700' : 'text-amber-800'"
									:title="canSubmitForReview ? '' : submitBlockerSummary"
								>
									{{ canSubmitForReview ? __("All required uploads complete.") : submitBlockerSummary }}
								</span>
							</div>
							<div class="flex items-center justify-end gap-3 sm:ml-auto">
								<button
									type="button"
									class="h-12 px-5 rounded-xl font-black uppercase text-xs tracking-widest transition-all flex items-center justify-center gap-2 border border-gray-300 text-gray-700 hover:bg-gray-50 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
									:disabled="saveDraftLoading || acData.submitted_for_review || acData.status === 'Accepted'"
									@click="saveDraft"
								>
									<FeatherIcon v-if="saveDraftLoading" name="loader" class="h-4 w-4 animate-spin" />
									<FeatherIcon v-else name="save" class="h-4 w-4" />
									{{ __("Save Draft") }}
								</button>
								<button
									type="button"
									class="h-12 px-6 rounded-xl font-black uppercase text-xs tracking-widest transition-all flex items-center justify-center gap-2 shadow-lg disabled:cursor-not-allowed"
									:class="canSubmitForReview ? 'text-white hover:brightness-110 active:scale-95' : 'text-gray-500 cursor-not-allowed'"
									:style="canSubmitForReview
										? 'background-color: #4f46e5; box-shadow: 0 6px 20px rgba(79, 70, 229, 0.35);'
										: 'background-color: #e5e7eb; box-shadow: none;'"
									:disabled="!canSubmitForReview || isSubmitting"
									@click="openSubmitConfirm"
								>
									<FeatherIcon name="send" class="h-4 w-4" />
									{{ __("Submit for Review") }}
								</button>
							</div>
						</div>
						<div v-if="lastSavedAt" class="text-xs text-gray-500 text-right">
							{{ __("Last saved {0}", [relativeTime(lastSavedAt)]) }}
						</div>
					</div>
				</div>

				<!-- Submit Confirmation Modal -->
				<div v-if="submitModalOpen" class="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
					<div class="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 space-y-5">
						<div class="flex items-start gap-4">
							<div class="p-3 bg-blue-50 text-blue-600 rounded-2xl shrink-0">
								<FeatherIcon name="send" class="h-5 w-5" />
							</div>
							<div class="flex-1 min-w-0">
								<h3 class="text-lg font-extrabold text-gray-900">{{ __("Submit to HR for review?") }}</h3>
								<p class="text-sm text-gray-600 mt-1 leading-relaxed">
									{{ __("Once submitted, HR will start reviewing your documents. You can re-upload only if HR rejects something.") }}
								</p>
							</div>
						</div>
						<div class="rounded-xl bg-gray-50 border border-gray-100 p-3 text-xs text-gray-700 space-y-1">
							<div class="flex justify-between"><span>{{ __("Files uploaded") }}</span><span class="font-bold">{{ uploadedCount }}</span></div>
							<div class="flex justify-between"><span>{{ __("Marked Not Applicable") }}</span><span class="font-bold">{{ naCount }}</span></div>
						</div>
						<div class="flex flex-col-reverse sm:flex-row gap-3 sm:justify-end">
							<button
								type="button"
								class="h-11 px-5 rounded-xl border border-gray-200 text-gray-700 text-xs font-black uppercase tracking-widest hover:bg-gray-50 disabled:opacity-50"
								@click="submitModalOpen = false"
								:disabled="isSubmitting"
							>
								{{ __("Cancel") }}
							</button>
							<button
								type="button"
								class="h-11 px-6 rounded-xl text-white text-xs font-black uppercase tracking-widest hover:brightness-110 disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg"
								style="background-color: #4f46e5; box-shadow: 0 6px 20px rgba(79, 70, 229, 0.35);"
								:disabled="isSubmitting"
								@click="confirmSubmit"
							>
								<LoadingIndicator v-if="isSubmitting" class="h-3.5 w-3.5 text-white" />
								<FeatherIcon v-else name="send" class="h-3.5 w-3.5" />
								{{ isSubmitting ? __("Submitting...") : __("Submit") }}
							</button>
						</div>
					</div>
				</div>

				<!-- Document Preview Modal (mobile-safe: PDF.js + image inline + external-link fallback) -->
				<DocumentPreviewModal
					:url="previewUrl"
					:title="previewTitle"
					@close="closePreview"
				/>

				<!-- Submit Success Toast -->
				<div v-if="submitSuccess" class="fixed inset-0 z-[201] flex items-center justify-center p-4 pointer-events-none">
					<div class="bg-white rounded-3xl shadow-2xl px-8 py-6 flex flex-col items-center gap-3 animate-in fade-in zoom-in duration-300">
						<div class="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
							<FeatherIcon name="check" class="h-8 w-8 text-green-600" />
						</div>
						<div class="text-base font-extrabold text-gray-900">{{ __("Submitted!") }}</div>
						<div class="text-xs text-gray-600">{{ __("HR has been notified.") }}</div>
					</div>
				</div>

				<!-- Floating Sync State -->
					<div v-if="acResource.fetching" class="fixed bottom-24 right-6 z-[100]">
						<div class="bg-blue-600 text-white p-3 px-5 rounded-full shadow-[0_20px_50px_rgba(79,70,229,0.4)] flex items-center gap-3 animate-bounce">
							<LoadingIndicator class="h-4 w-4 text-white" />
							<span class="text-[10px] font-black uppercase tracking-[0.2em]">{{ __("Syncing") }}</span>
						</div>
					</div>
				</div>

		</ion-content>
	</ion-page>
</template>

<script setup>
import { ref, reactive, computed, inject } from "vue"
import {
	FeatherIcon,
	Avatar,
	LoadingIndicator,
	createResource,
	call,
	Button,
	Checkbox,
	Badge,
	toast,
} from "frappe-ui"
import { useIonRouter, IonPage, IonContent, onIonViewWillEnter } from "@ionic/vue"
import { unreadNotificationsCount } from "@/data/notifications"
import { FileAttachment } from "@/composables"
import { showError, showErrorFromException } from "@/data/errorModal"
import DocumentPreviewModal from "@/components/DocumentPreviewModal.vue"

const ionRouter = useIonRouter()
const user = inject("$user")
const __ = inject("$translate")

function goBack() {
	// PWA can be opened via deep link / bookmark / SW cache without any history.
	// If there's no real previous page (length<=2 = login + current), fall back to Home
	// instead of dumping the user to the login screen.
	if (window.history.length > 2) {
		window.history.back()
	} else {
		ionRouter.push({ name: "Home" })
	}
}

// Native file upload state
const fileInputRef = ref(null)
const pendingUploadKey = ref(null)
const pendingUploadIsMandatory = ref(false)
const pendingUploadMode = ref("default")
const isUploading = ref(false)

// In-app document preview (replaces target="_blank" so iOS doesn't strip the chrome)
const previewUrl = ref(null)
const previewTitle = ref("")
function openPreview(url, title) {
	if (!url) return
	previewUrl.value = url
	previewTitle.value = title || __("Document")
}
function closePreview() {
	previewUrl.value = null
	previewTitle.value = ""
}

function triggerUpload(key, isMandatory) {
	pendingUploadMode.value = "default"
	pendingUploadKey.value = key
	pendingUploadIsMandatory.value = isMandatory
	fileInputRef.value.value = ""
	fileInputRef.value.click()
}

function triggerEmployer1DocUpload(docKey) {
	pendingUploadMode.value = "employer_1"
	pendingUploadKey.value = docKey
	pendingUploadIsMandatory.value = false
	fileInputRef.value.value = ""
	fileInputRef.value.click()
}

/** Medical Insurance opt-out signed declaration upload. Distinct mode because
 *  the field name (`medical_insurance_signed_optout`) doesn't follow the
 *  `<prefix>_upload` / `<prefix>_doc` convention used by handleDocSync. */
function triggerSignedOptOutUpload() {
	pendingUploadMode.value = "signed_optout"
	pendingUploadKey.value = "medical_insurance_signed_optout"
	pendingUploadIsMandatory.value = false
	fileInputRef.value.value = ""
	fileInputRef.value.click()
}

async function onFileChosen(e) {
	const file = e.target.files?.[0]
	if (!file || !acData.value) return
	isUploading.value = true
	try {
		const attachment = new FileAttachment(file)
		const fileDoc = await attachment.upload("Employee Action Centre", acData.value.name, "")
		if (pendingUploadMode.value === "employer_1") {
			await handleEmployer1DocSync(pendingUploadKey.value, { file_url: fileDoc.file_url })
		} else if (pendingUploadMode.value === "signed_optout") {
			await fieldSync.submit({
				name: acData.value.name,
				fieldname: "medical_insurance_signed_optout",
				value: fileDoc.file_url,
			})
			await acResource.reload()
		} else {
			await handleDocSync(pendingUploadKey.value, { file_url: fileDoc.file_url }, pendingUploadIsMandatory.value)
		}
	} finally {
		isUploading.value = false
		pendingUploadKey.value = null
		pendingUploadMode.value = "default"
	}
}

// 1. Reactive State
const acData = ref(null)
const loading = ref(true)
const expandedSections = reactive({
	personal: true,
	docs: true,
	declarations: true,
	statbank: true,
	employers: false,
})

/** ISO 'today' string for the DOB date picker max attribute. */
const todayIso = computed(() => {
	const d = new Date()
	const y = d.getFullYear()
	const m = String(d.getMonth() + 1).padStart(2, "0")
	const dd = String(d.getDate()).padStart(2, "0")
	return `${y}-${m}-${dd}`
})

/** "X / N filled" badge for the Personal Details section header. */
const personalCompletedCount = computed(() => {
	if (!acData.value?.personal_details) return 0
	return acData.value.personal_details.filter((pd) => {
		if (pd.kind === "readonly") return false  // age is auto-derived
		return !!String(pd.value || "").trim()
	}).length
})

/** Same idea for Statutory & Bank — text fields plus the four statutory form
 *  uploads (a form counts as filled when uploaded or marked N/A). */
const statutoryBankCompletedCount = computed(() => {
	if (!acData.value) return 0
	const filled = (acData.value.statutory_bank || []).filter((sb) => !!String(sb.value || "").trim()).length
	const forms = (acData.value.statutory_forms || []).filter((f) => f.file || f.is_na).length
	return filled + forms
})
const statutoryBankTotalCount = computed(() => {
	if (!acData.value) return 0
	return (acData.value.statutory_bank || []).length + (acData.value.statutory_forms || []).length
})

/** Per employer card expand/collapse (key = emp.key) */
const expandedEmployerCards = reactive({})

/** Slots (2-5) that the user explicitly added in this session, even though they have no
 *  data yet. Persisted in component state only — refreshing collapses them back, which is
 *  the natural "undo" if user accidentally added too many. */
const addedEmployerKeys = ref(new Set())

function toggleEmployerCard(key) {
	expandedEmployerCards[key] = !expandedEmployerCards[key]
}

function isEmployerCardOpen(key) {
	return !!expandedEmployerCards[key]
}

/** Inline date-range validation: Till must not be before From. Returns a translated
 *  error string when both dates are set and inverted; empty string otherwise. The
 *  server enforces the same rule on save (`_validate_employer_dates`); this just
 *  surfaces it in the UI before the user clicks Save. */
function employerDateError(emp) {
	if (!emp) return ""
	const f = emp.from_date
	const t = emp.till_date
	if (f && t && f > t) return __("Till date cannot be before From date")
	return ""
}

/** Whether an employer slot has any meaningful data filled. Used to decide if the slot
 *  should auto-show in the list (without explicit Add). */
function employerHasData(emp) {
	if (!emp) return false
	return !!(
		(emp.name && String(emp.name).trim()) ||
		emp.from_date ||
		emp.till_date ||
		emp.file ||
		emp.is_na ||
		(emp.status && emp.status !== "Pending")
	)
}

/** Whether the relieving doc is needed for this employer slot. True only for slots 2-5
 *  when employer details have been entered, no doc has been uploaded, and not marked N/A. */
function employerNeedsAction(emp) {
	if (!emp || emp.key === "employer_1") return false
	if (emp.is_na) return false
	if (emp.file) return false
	const started = !!((emp.name && String(emp.name).trim()) || emp.from_date || emp.till_date)
	return started
}

/** True when the user has marked Most Recent Employer as N/A — i.e. they have
 *  no prior employer at all (fresher / first-time hire). When this is true,
 *  Previous Employers can't logically exist, so slots 2-5 are hidden and the
 *  "Add Previous Employer" affordance is disabled. */
const isFresher = computed(() => {
	const e1 = acData.value?.employers?.find((e) => e.key === "employer_1")
	return !!(e1 && e1.is_na)
})

/** Filtered employer list for the PWA: Employer 1 always; Employer 2-5 only if
 *  filled or explicitly added by the user, and only when there's a Most Recent
 *  Employer to come "after" in the work history (i.e. user is not a fresher). */
const visibleEmployers = computed(() => {
	if (!acData.value?.employers) return []
	const result = []
	for (const emp of acData.value.employers) {
		if (emp.key === "employer_1") {
			result.push(emp)
			continue
		}
		if (isFresher.value) continue
		if (employerHasData(emp) || addedEmployerKeys.value.has(emp.key)) {
			result.push(emp)
		}
	}
	return result
})

const canAddPreviousEmployer = computed(() => {
	if (isFresher.value) return false
	return visibleEmployers.value.length < 5
})

function addPreviousEmployer() {
	const slots = ["employer_2", "employer_3", "employer_4", "employer_5"]
	for (const key of slots) {
		const emp = acData.value?.employers?.find((e) => e.key === key)
		if (!emp) continue
		if (!employerHasData(emp) && !addedEmployerKeys.value.has(key)) {
			const next = new Set(addedEmployerKeys.value)
			next.add(key)
			addedEmployerKeys.value = next
			expandedEmployerCards[key] = true
			return
		}
	}
	showError(
		__("You can add up to 5 employers (Most Recent + 4 Previous)."),
		__("Limit reached"),
	)
}

/** True only for previous-employer slots (2-5) that the user added in this session
 *  AND that have no data yet — gives a way to undo an accidental "Add Previous
 *  Employer" tap. Slots with any data must go through the N/A toggle (which the
 *  server treats as a real "this employer doesn't exist" signal). */
function canRemoveEmployer(emp) {
	if (!emp || emp.key === "employer_1") return false
	if (!addedEmployerKeys.value.has(emp.key)) return false
	if (employerHasData(emp)) return false
	return true
}

/** Drop a user-added empty slot back to the "Add Previous Employer" affordance.
 *  Pure local state — no server write, the slot was never persisted as anything
 *  other than its default empty row. */
function removePreviousEmployer(empKey) {
	if (!addedEmployerKeys.value.has(empKey)) return
	const next = new Set(addedEmployerKeys.value)
	next.delete(empKey)
	addedEmployerKeys.value = next
	expandedEmployerCards[empKey] = false
}

/** Friendly human label for a given employer slot (used in blocker text). */
function employerSlotLabel(emp) {
	if (!emp) return ""
	if (emp.key === "employer_1") return __("Most Recent Employer")
	const n = parseInt(emp.key.replace("employer_", ""), 10) - 1
	return `${__("Previous Employer")} ${n}`
}

/** List of human-readable blockers preventing Submit-for-Review. Empty list means
 *  the form is fully submittable. Drives both the bottom-bar caption and the
 *  enabled state of the Submit button. */
const submitBlockers = computed(() => {
	if (!acData.value) return []
	const blockers = []

	// Mandatory personal documents (Aadhar, PAN, Education).
	for (const d of acData.value.documents || []) {
		if (d.mandatory && !d.file && !d.is_na) blockers.push(d.label)
		// Inline number/name field inside the same identity card.
		// Skip when the row is N/A — both file and number gates collapse together.
		if (d.number_field && !d.is_na && !String(d.number_value || "").trim()) {
			blockers.push(d.number_label)
		}
	}

	// Mandatory declarations (Tax Regime, Medical Insurance, Bank Statement 6m).
	for (const decl of acData.value.declarations || []) {
		if (!decl.mandatory || decl.is_na) continue
		if (decl.kind === "select" && !decl.value) blockers.push(decl.label)
		if (decl.kind === "file" && !decl.file) blockers.push(decl.label)
	}

	// Mandatory personal-details fields (Name, DOB, Gender, etc.).
	for (const pd of acData.value.personal_details || []) {
		if (pd.kind === "readonly") continue  // age is auto-derived
		if (pd.mandatory && !String(pd.value || "").trim()) blockers.push(pd.label)
	}

	// Mandatory statutory & bank fields (Bank name/account/IFSC).
	for (const sb of acData.value.statutory_bank || []) {
		if (sb.mandatory && !String(sb.value || "").trim()) blockers.push(sb.label)
	}

	// Statutory form uploads (Form 1 / Form 2 / Form F / PF Form 11) — satisfied by a file or N/A.
	for (const sf of acData.value.statutory_forms || []) {
		if (sf.mandatory && !sf.is_na && !sf.file) blockers.push(sf.label)
	}

	// Employer slots — slot 1 is required UNLESS marked N/A (fresher); slots
	// 2-5 are only required if the user has started entering data for them.
	for (const emp of acData.value.employers || []) {
		if (emp.is_na) continue  // N/A short-circuits all checks for the slot
		const slotLabel = employerSlotLabel(emp)
		const name = emp.name && String(emp.name).trim()
		const hasSubDocFile = !!(emp.documents && emp.documents.some((d) => d.file))
		const started = !!(name || emp.from_date || emp.till_date || emp.file || hasSubDocFile)

		if (emp.key === "employer_1") {
			if (!name || !emp.from_date || !emp.till_date) {
				blockers.push(`${slotLabel}: ${__("complete details")}`)
			} else if (emp.from_date > emp.till_date) {
				blockers.push(`${slotLabel}: ${__("invalid date range")}`)
			}
			for (const sub of emp.documents || []) {
				if (sub.mandatory && !sub.file) blockers.push(sub.label)
			}
		} else if (started) {
			if (!name || !emp.from_date || !emp.till_date) {
				blockers.push(`${slotLabel}: ${__("complete details")}`)
			} else if (emp.from_date > emp.till_date) {
				blockers.push(`${slotLabel}: ${__("invalid date range")}`)
			} else if (!emp.file) {
				blockers.push(`${slotLabel}: ${__("relieving letter")}`)
			}
		}
	}

	// Cross-slot tenure overlap. Two employer stints with overlapping
	// [from, till] windows are nonsensical (you can't be employed full-time
	// at two places at once). Compares every pair of slots that has both
	// dates set and is not N/A. We surface a single dedupe'd blocker.
	const dated = (acData.value.employers || []).filter(
		(e) => !e.is_na && e.from_date && e.till_date && e.from_date <= e.till_date,
	)
	const overlapPairs = []
	for (let i = 0; i < dated.length; i++) {
		for (let j = i + 1; j < dated.length; j++) {
			const a = dated[i]
			const b = dated[j]
			// Inclusive overlap: [a.from, a.till] ∩ [b.from, b.till] ≠ ∅
			if (a.from_date <= b.till_date && b.from_date <= a.till_date) {
				overlapPairs.push(`${employerSlotLabel(a)} ↔ ${employerSlotLabel(b)}`)
			}
		}
	}
	if (overlapPairs.length) {
		blockers.push(
			`${__("Tenure overlap")}: ${overlapPairs.join("; ")}`,
		)
	}

	return blockers
})

/** Whether the Submit-for-Review CTA should be enabled. Combines the blocker
 *  list with server-side gates (already submitted / accepted). */
const canSubmitForReview = computed(() => {
	if (!acData.value) return false
	if (acData.value.submitted_for_review) return false
	if (acData.value.status === "Accepted") return false
	return submitBlockers.value.length === 0
})

/** Short caption shown in the sticky bottom bar — full list if it fits, else a
 *  truncated "X, Y + N more pending" form. */
const submitBlockerSummary = computed(() => {
	const list = submitBlockers.value
	if (!list.length) return ""
	if (list.length === 1) return `${list[0]} ${__("pending")}`
	if (list.length <= 3) return `${list.join(", ")} ${__("pending")}`
	return `${list.slice(0, 2).join(", ")} + ${list.length - 2} ${__("more pending")}`
})

/** Read-only employer card: locked once HR has Accepted, OR after the AC has been submitted
 * for any row that isn't currently Rejected (rejected rows remain actionable so the employee
 * can re-upload). */
function isEmployerCardLocked(emp) {
	if (!emp) return false
	if (emp.status === "Accepted") return true
	if (acData.value?.submitted_for_review && emp.status !== "Rejected") return true
	return false
}

/** Same lock semantics for non-employer rows (Aadhar / PAN / Education + Employer 1 split docs). */
function isDocRowLocked(row) {
	if (!row) return false
	if (row.status === "Accepted") return true
	if (acData.value?.submitted_for_review && row.status !== "Rejected") return true
	return false
}

const acResource = createResource({
	url: "myhr.api.get_employee_action_centre",
	auto: true,
	onSuccess: (data) => {
		acData.value = data
		loading.value = false
		if (data?.custom_last_saved_at) {
			lastSavedAt.value = data.custom_last_saved_at
		}
	}
})

// Refresh whenever the user navigates back into the AC page (e.g., after HR Accept/Reject
// happens on Desk while the page is still in the navigation stack).
onIonViewWillEnter(() => {
	acResource.reload()
})

function toggleSection(section) {
	expandedSections[section] = !expandedSections[section]
}

// 2. Navigation Sync Functions
const fieldSync = createResource({ url: "myhr.api.update_action_centre_field" })
const bulkSync = createResource({ url: "myhr.api.bulk_update_action_centre_fields" })
const reuploadSync = createResource({ url: "myhr.api.reupload_document" })
const toggleNASync = createResource({
	url: "myhr.api.update_action_centre_field",
	onSuccess: () => acResource.reload()
})
const resetAllSync = createResource({ url: "myhr.api.reset_action_centre_field" })
const submitSync = createResource({ url: "myhr.api.submit_action_centre" })

// Submit gate state
const submitModalOpen = ref(false)
const submitSuccess = ref(false)
const isSubmitting = ref(false)

const uploadedCount = computed(() => {
	if (!acData.value) return 0
	let n = 0
	for (const d of acData.value.documents || []) if (d.file) n++
	for (const decl of acData.value.declarations || []) {
		if (decl.kind === "file" && decl.file) n++
		if (decl.kind === "select" && decl.value) n++
	}
	for (const sf of acData.value.statutory_forms || []) if (sf.file) n++
	for (const e of acData.value.employers || []) {
		if (e.file) n++
		for (const sub of e.documents || []) if (sub.file) n++
	}
	return n
})

const naCount = computed(() => {
	if (!acData.value) return 0
	let n = 0
	for (const d of acData.value.documents || []) if (d.is_na) n++
	for (const decl of acData.value.declarations || []) if (decl.is_na) n++
	for (const sf of acData.value.statutory_forms || []) if (sf.is_na) n++
	for (const e of acData.value.employers || []) if (e.is_na) n++
	return n
})

function openSubmitConfirm() {
	submitModalOpen.value = true
}

// --- Save Draft (added 2026-05-01) -----------------------------------------
// Traverses the structured arrays returned by get_employee_action_centre and
// emits a flat {fieldname: value} payload. The server-side allow-list in
// myhr/api.py:save_action_centre_draft is the security guardrail — no
// client-side field enumeration needed.

const saveDraftLoading = ref(false)
const lastSavedAt = ref(null)

function _buildSaveDraftPayload(ac) {
	const payload = {}

	// Identity documents: {key, file, is_na, number_field, number_value}
	// DB fields: {key}_upload, {key}_is_na, number_field (e.g. aadhar_number)
	for (const doc of ac.documents || []) {
		if (!doc.key) continue
		if (doc.file != null) payload[`${doc.key}_upload`] = doc.file
		payload[`${doc.key}_is_na`] = doc.is_na ? 1 : 0
		if (doc.number_field && doc.number_value != null) {
			payload[doc.number_field] = doc.number_value
		}
	}

	// Personal details and statutory/bank: {key, value}
	// DB field name == key (e.g. personal_full_name, bank_account_number)
	for (const pd of ac.personal_details || []) {
		if (pd.key && pd.kind !== "readonly" && pd.value != null) {
			payload[pd.key] = pd.value
		}
	}
	for (const sb of ac.statutory_bank || []) {
		if (sb.key && sb.value != null) payload[sb.key] = sb.value
	}

	// Statutory forms: {key, data_field, file, is_na} — data_field is `<key>_upload`.
	for (const sf of ac.statutory_forms || []) {
		if (!sf.key) continue
		if (sf.data_field && sf.file != null) payload[sf.data_field] = sf.file
		payload[`${sf.key}_is_na`] = sf.is_na ? 1 : 0
	}

	// Declarations: {key, data_field, kind, value, file, is_na}
	// kind="select" → data_field holds the Select value; kind="file" → data_field holds the file URL
	for (const decl of ac.declarations || []) {
		if (!decl.key) continue
		if (decl.kind === "select" && decl.data_field && decl.value != null) {
			payload[decl.data_field] = decl.value
		}
		if (decl.kind === "file" && decl.data_field && decl.file != null) {
			payload[decl.data_field] = decl.file
		}
		payload[`${decl.key}_is_na`] = decl.is_na ? 1 : 0
	}

	// Employers: {key, name, from_date, till_date, is_na}
	// key = "employer_1" … "employer_5"
	// DB fields: {key}_name, {key}_from, {key}_till, {key}_is_na
	for (const emp of ac.employers || []) {
		if (!emp.key) continue
		if (emp.name != null) payload[`${emp.key}_name`] = emp.name
		if (emp.from_date != null) payload[`${emp.key}_from`] = emp.from_date
		if (emp.till_date != null) payload[`${emp.key}_till`] = emp.till_date
		payload[`${emp.key}_is_na`] = emp.is_na ? 1 : 0
	}

	return payload
}

async function saveDraft() {
	if (acData.value?.submitted_for_review || acData.value?.status === "Accepted") return
	const payload = _buildSaveDraftPayload(acData.value || {})
	saveDraftLoading.value = true
	try {
		const res = await call("myhr.api.save_action_centre_draft", {
			name: acData.value.name,
			payload: JSON.stringify(payload),
		})
		lastSavedAt.value = res.saved_at
		acData.value.custom_last_saved_at = res.saved_at
		toast({
			title: __("Draft saved"),
			text: __("Saved at {0}", [formatDraftTime(res.saved_at)]),
			icon: "check",
			iconClasses: "text-green-500",
		})
	} catch (err) {
		toast({
			title: __("Save failed"),
			text: err?.message || __("Please try again."),
			icon: "alert-triangle",
			iconClasses: "text-red-500",
		})
	} finally {
		saveDraftLoading.value = false
	}
}

function formatDraftTime(iso) {
	if (!iso) return ""
	const d = new Date(iso.replace(" ", "T"))
	return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function relativeTime(iso) {
	if (!iso) return ""
	const d = new Date(iso.replace(" ", "T"))
	const diffMs = Date.now() - d.getTime()
	const m = Math.round(diffMs / 60000)
	if (m < 1) return __("just now")
	if (m < 60) return __("{0}m ago", [m])
	const h = Math.round(m / 60)
	if (h < 24) return __("{0}h ago", [h])
	const days = Math.round(h / 24)
	return __("{0}d ago", [days])
}
// ---------------------------------------------------------------------------

/** Silently persist a single Most Recent Employer (slot 1) metadata field
 *  whenever the user finishes typing/picking a value. Slot 1 has no Save
 *  button (unlike slots 2-5), so without this, typed values stay client-only
 *  and the submit-time server validator throws "Most Recent Employer:
 *  Employer Name / From / Till cannot be left blank" even though the user
 *  can see the values in the inputs. We only autosave slot 1 here — slots
 *  2-5 keep their explicit Save flow so a user adding a previous employer
 *  can change their mind before persisting.
 *
 *  Server-side date-order validation runs on every save, so we guard against
 *  triggering it with a half-typed range (e.g. From set, Till still empty). */
async function onEmployerMetaCommit(emp, field) {
	if (!emp || emp.key !== "employer_1") return
	if (!acData.value || isEmployerCardLocked(emp)) return
	if (employerDateError(emp)) return  // server will reject; let user fix first
	const fieldnameMap = {
		name: `${emp.key}_name`,
		from_date: `${emp.key}_from`,
		till_date: `${emp.key}_till`,
	}
	const fieldname = fieldnameMap[field]
	if (!fieldname) return
	const value = field === "name"
		? (emp.name ?? "")
		: (emp[field] ?? "")
	try {
		await fieldSync.submit({ name: acData.value.name, fieldname, value })
	} catch (error) {
		// Non-blocking — user can still tap Submit, which does a full flush.
		console.warn("autosave failed", fieldname, error)
	}
}

async function confirmSubmit() {
	if (!acData.value || isSubmitting.value) return
	isSubmitting.value = true
	try {
		// Defence-in-depth: flush every employer slot's name/from/till to the
		// server before submitting. Belt-and-suspenders against blur not
		// firing on slot 1 (e.g. user taps Submit while an input is still
		// focused) and against slots 2-5 the user edited but didn't Save. The
		// server's _validate_employer_required_fields and the new
		// _validate_employer_no_overlap will then run against current state.
		const patch = {}
		for (const emp of acData.value.employers || []) {
			if (isEmployerCardLocked(emp)) continue
			patch[`${emp.key}_name`] = emp.name ?? ""
			patch[`${emp.key}_from`] = emp.from_date ?? ""
			patch[`${emp.key}_till`] = emp.till_date ?? ""
		}
		if (Object.keys(patch).length) {
			await bulkSync.submit({
				name: acData.value.name,
				patch: JSON.stringify(patch),
			})
		}

		await submitSync.submit({ name: acData.value.name })
		submitModalOpen.value = false
		submitSuccess.value = true
		setTimeout(() => { submitSuccess.value = false }, 1800)
		await acResource.reload()
	} catch (error) {
		showErrorFromException(error, __("Could not submit"))
	} finally {
		isSubmitting.value = false
	}
}

const savingEmployerKey = ref(null)

async function saveEmployer(emp) {
	if (!acData.value || isEmployerCardLocked(emp)) return
	const dateErr = employerDateError(emp)
	if (dateErr) {
		showError(dateErr, __("Invalid dates"))
		return
	}
	savingEmployerKey.value = emp.key
	try {
		await bulkSync.submit({
			name: acData.value.name,
			patch: JSON.stringify({
				[`${emp.key}_name`]: emp.name ?? "",
				[`${emp.key}_from`]: emp.from_date ?? "",
				[`${emp.key}_till`]: emp.till_date ?? "",
			}),
		})
		await acResource.reload()
		toast({
			title: __("Saved"),
			text: __("Employer details saved"),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
	} catch (error) {
		showErrorFromException(error, __("Could not save employer details"))
	} finally {
		savingEmployerKey.value = null
	}
}

async function handleDocSync(key, file, isMandatory = false) {
	if (!acData.value) return
	const fileUrl = file.file_url 
	
	// Define the raw prefix (e.g. 'aadhar' or 'employer_1')
	const rawPrefix = isMandatory ? key : key.replace('_doc', '')
	
	// CRITICAL: Definitive N/A Reset first to prevent dual state
	const naField = `${rawPrefix}_is_na`
	await fieldSync.submit({ name: acData.value.name, fieldname: naField, value: 0 })

	const row = acData.value.documents?.find(d => d.key === key)
		|| acData.value.declarations?.find(d => d.key === key)
		|| acData.value.statutory_forms?.find(d => d.key === key)
		|| acData.value.employers?.find(e => e.key === rawPrefix)
	
	// Use Re-upload API ONLY if there's a history
	if (row?.status === 'Rejected' || (row?.file && row?.status !== 'Pending')) {
		await reuploadSync.submit({
			name: acData.value.name,
			prefix: rawPrefix,
			file_url: fileUrl
		})
	} else {
		// Standard First-Time Upload
		const fieldName = isMandatory ? `${rawPrefix}_upload` : `${rawPrefix}_doc`
		await fieldSync.submit({
			name: acData.value.name,
			fieldname: fieldName,
			value: fileUrl
		})
	}
	
	// Force full reload only after both updates are committed
	await acResource.reload()
}

async function handleEmployerDocSync(key, file) {
	await handleDocSync(key, file, false)
}

function getEmployer1DocRow(docKey) {
	const employer1 = acData.value?.employers?.find((e) => e.key === "employer_1")
	return employer1?.documents?.find((d) => d.key === docKey)
}

async function handleEmployer1DocSync(docKey, file) {
	if (!acData.value) return
	const fileUrl = file.file_url
	const row = getEmployer1DocRow(docKey)

	if (row?.status === "Rejected" || (row?.file && row?.status !== "Pending")) {
		await reuploadSync.submit({
			name: acData.value.name,
			prefix: docKey,
			file_url: fileUrl,
		})
	} else {
		await fieldSync.submit({
			name: acData.value.name,
			fieldname: `${docKey}_doc`,
			value: fileUrl,
		})
	}

	await acResource.reload()
}

async function executeEmployer1DocReset(docKey) {
	await resetAllSync.submit({
		name: acData.value.name,
		fieldname: `${docKey}_doc`,
		is_mandatory: 0,
	})
	await acResource.reload()
}

async function executeReset(fieldName, isMandatory) {
	await resetAllSync.submit({ 
		name: acData.value.name, 
		fieldname: fieldName,
		is_mandatory: isMandatory ? 1 : 0
	})
	await acResource.reload()
}

async function handleNAToggle(fieldName, current, hasFile, isMandatory = false) {
	// Toggle N/A on/off. The server's `_enforce_data_invariants` clears the file
	// in the same save when is_na=1 arrives, and `_sweep_ghost_statuses` promotes
	// per-row status accordingly — no need for the client to chain extra writes.
	const newStatus = current ? 0 : 1
	const actualKey = isMandatory ? fieldName : fieldName.replace('_is_na', '')

	// Optimistic UI update so the user sees the toggle flip immediately.
	if (acData.value) {
		if (isMandatory) {
			const doc = acData.value.documents?.find(d => d.key === actualKey)
			if (doc) {
				doc.is_na = newStatus
				if (newStatus === 1) doc.file = ""
				doc.status = newStatus === 1 ? "Awaiting HR" : (doc.file ? "Awaiting HR" : "Pending")
			}
		} else {
			const empKey = fieldName.includes('_is_na') ? fieldName.replace('_is_na', '') : fieldName
			const emp = acData.value.employers?.find(e => e.key === empKey)
			if (emp) {
				const wasFresher = emp.key === "employer_1" && emp.is_na
				emp.is_na = newStatus
				if (emp.key === "employer_1" && wasFresher && newStatus === 0) {
					// Fresher toggled OFF — mirror the server's reverse
					// propagation that clears auto-N/A on slots 2-5 so the user
					// can fill them from a clean state on the next reload.
					for (const otherEmp of acData.value.employers || []) {
						if (otherEmp.key === "employer_1") continue
						otherEmp.is_na = 0
						otherEmp.status = "Pending"
					}
				}
				if (newStatus === 1) {
					// Mirror the server's `_enforce_data_invariants`: marking a slot
					// N/A clears name/from/till/file in the same save. Done locally
					// so the user sees the wipe immediately instead of waiting for
					// the server round-trip + reload.
					emp.file = ""
					emp.name = ""
					emp.from_date = ""
					emp.till_date = ""
					// Most Recent Employer (slot 1) has split sub-doc rows — wipe
					// each file locally so the form looks clean before the round-trip.
					if (empKey === "employer_1" && emp.documents) {
						for (const sub of emp.documents) {
							sub.file = ""
							sub.status = "Pending"
						}
						// "Fresher" implies no prior employers at all — wipe slots
						// 2-5 locally and collapse any user-added empty cards. The
						// server does the same in `_enforce_data_invariants` on save
						// AND propagates is_na=1 to slots 2-5 so the row sweep flips
						// their status to "Awaiting HR" (otherwise the Home badge
						// keeps counting them as Pending tasks). Mirror that here.
						for (const otherEmp of acData.value.employers || []) {
							if (otherEmp.key === "employer_1") continue
							otherEmp.name = ""
							otherEmp.from_date = ""
							otherEmp.till_date = ""
							otherEmp.file = ""
							otherEmp.is_na = 1
							otherEmp.status = "Awaiting HR"
						}
						addedEmployerKeys.value = new Set()
					}
				}
				emp.status = newStatus === 1 ? "Awaiting HR" : (emp.file ? "Awaiting HR" : "Pending")
			}
		}
	}

	// Single server write — server handles the cascade (file wipe + status promote + master recompute).
	const serverFieldName = isMandatory ? `${fieldName}_is_na` : fieldName
	await toggleNASync.submit({
		name: acData.value.name,
		fieldname: serverFieldName,
		value: newStatus,
	})
}

// ----- Personal Details / Statutory & Bank / Identity Numbers -----

/** Tracks which Select dropdown popover is currently open. Empty string = none.
 *  Only one popover open at a time — clicking another auto-closes the previous. */
const openDropdown = ref("")
function toggleDropdown(key) {
	openDropdown.value = openDropdown.value === key ? "" : key
}
function closeDropdown() {
	openDropdown.value = ""
}
async function selectDropdownOption(pd, value) {
	closeDropdown()
	await commitPersonalField(pd.key, value)
}

/** Persist a personal/statutory/identity-number field to the AC. Used by every
 *  text/select/date/tel input in the new buckets and by the inline number
 *  inputs inside the Identity Documents cards. Optimistic local update, then
 *  full server save. The server-side validate() chain runs format checks
 *  (PAN regex, 10/12-digit, etc.) and surfaces any error via showError. */
async function commitPersonalField(fieldname, value) {
	if (!acData.value || !fieldname) return
	const trimmed = typeof value === "string" ? value.trim() : value

	// Optimistic local update so the UI doesn't blink while the round-trip
	// completes. Find the row in whichever bucket carries it.
	for (const pd of acData.value.personal_details || []) {
		if (pd.key === fieldname) { pd.value = trimmed; break }
	}
	for (const sb of acData.value.statutory_bank || []) {
		if (sb.key === fieldname) { sb.value = trimmed; break }
	}
	for (const d of acData.value.documents || []) {
		if (d.number_field === fieldname) { d.number_value = trimmed; break }
	}

	try {
		await fieldSync.submit({
			name: acData.value.name,
			fieldname,
			value: trimmed,
		})
	} catch (err) {
		showErrorFromException(err)
	}
	// Reload so server-computed fields (personal_age) and master status flow back.
	await acResource.reload()
}

// ----- Declarations (Tax Regime, Medical Insurance opt-in, Bank Statement) -----

/** True if the declaration has any committed data (Select value, file, or N/A).
 *  Drives the icon picker on the card header. */
function declarationHasData(decl) {
	if (!decl) return false
	if (decl.is_na) return true
	if (decl.kind === "select") return !!decl.value
	if (decl.kind === "file") return !!decl.file
	return false
}

/** Persist a Tax Regime / Medical Insurance choice. Optimistically updates
 *  the local card so the user sees the pick reflected immediately, then
 *  syncs the data field + clears N/A in one round-trip via bulkSync. The
 *  server's _sweep_ghost_statuses promotes the row's approval_status from
 *  Pending → Awaiting HR on save. */
async function executeDeclarationSelect(decl, value) {
	if (!decl || !acData.value) return
	if (isDocRowLocked(decl)) return
	const dataField = decl.data_field
	if (!dataField) return

	// Optimistic UI
	decl.value = value
	decl.is_na = 0
	decl.status = "Awaiting HR"

	try {
		await bulkSync.submit({
			name: acData.value.name,
			patch: JSON.stringify({
				[dataField]: value,
				[`${decl.key}_is_na`]: 0,
			}),
		})
	} catch (err) {
		showErrorFromException(err)
	}
	await acResource.reload()
}

/** Toggle the N/A flag on a declaration. Mirrors handleNAToggle but routes
 *  the optimistic update to the declarations array instead of documents/employers. */
async function handleDeclarationNA(decl, current) {
	if (!decl || !acData.value) return
	if (isDocRowLocked(decl)) return
	const newStatus = current ? 0 : 1

	// Optimistic UI: clearing the data field on N/A=1 mirrors the server's
	// _enforce_data_invariants — keeps the card consistent before the round-trip.
	decl.is_na = newStatus
	if (newStatus === 1) {
		decl.value = ""
		decl.file = ""
	}
	decl.status = newStatus === 1
		? "Awaiting HR"
		: ((decl.value || decl.file) ? "Awaiting HR" : "Pending")

	try {
		await toggleNASync.submit({
			name: acData.value.name,
			fieldname: `${decl.key}_is_na`,
			value: newStatus,
		})
	} catch (err) {
		showErrorFromException(err)
	}
}

// Policy acknowledgements are now handled by the standalone /policies page
// via myhr.api.acknowledge_policy_acknowledgement.

// 4. UI Decorators (Clean Labels)
function getCleanStatus(status, hasFile) {
	const s = (status || "").toLowerCase()
	if (s === 'approved') return __("VERIFIED")
	if (s === 'rejected') return __("RE-UPLOAD REQUIRED")
	if (hasFile) return __("AWAITING HR REVIEW")
	return __("MISSING ATTACHMENT")
}

</script>

<style scoped>
.ion-page {
	--ion-background-color: #FBFBFC;
}

textarea {
	border: 1.5px solid rgba(239, 68, 68, 0.1);
	transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

textarea:focus {
	outline: none;
	background: #fff;
	border-color: #EF4444;
	box-shadow: 0 10px 15px -3px rgba(239, 68, 68, 0.1);
}

/* Custom Scrollbar for Desktop */
::-webkit-scrollbar {
	width: 6px;
}
::-webkit-scrollbar-track {
	background: transparent;
}
::-webkit-scrollbar-thumb {
	background: #E5E7EB;
	border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
	background: #D1D5DB;
}
</style>
