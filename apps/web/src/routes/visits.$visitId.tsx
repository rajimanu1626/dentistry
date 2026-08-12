import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { MediaGallery } from "@/components/media-gallery";
import { openProtectedPdf } from "@/lib/pdf";
import { patientsApi } from "@/lib/patients";
import { requireClinicalWorkspace } from "@/lib/router-auth";

export const Route = createFileRoute("/visits/$visitId")({
	beforeLoad: requireClinicalWorkspace,
	component: VisitDetailPage,
});

function VisitDetailPage() {
	const queryClient = useQueryClient();
	const { visitId } = Route.useParams();
	const [rxMedication, setRxMedication] = useState("");
	const [rxDose, setRxDose] = useState("");
	const [rxFrequency, setRxFrequency] = useState("");
	const [rxDuration, setRxDuration] = useState("");
	const [rxNotes, setRxNotes] = useState("");
	const [chiefComplaint, setChiefComplaint] = useState("");
	const [diagnosis, setDiagnosis] = useState("");
	const [treatmentPlan, setTreatmentPlan] = useState("");
	const [visitNotes, setVisitNotes] = useState("");
	const [followupDate, setFollowupDate] = useState("");
	const [followupNotes, setFollowupNotes] = useState("");
	const [mediaFile, setMediaFile] = useState<File | null>(null);
	const [mediaKind, setMediaKind] = useState<"before" | "after" | "xray" | "other">(
		"before",
	);
	const [shareRecipient, setShareRecipient] = useState("");
	const [shareTtlHours, setShareTtlHours] = useState("24");
	const [shareMaxViews, setShareMaxViews] = useState("5");
	const [sharePassword, setSharePassword] = useState("");
	const [shareScopeMode, setShareScopeMode] = useState<"visit" | "history">("visit");
	const [createdShare, setCreatedShare] = useState<{
		url: string;
		password: string;
		expiresAt: string;
	} | null>(null);
	const [actionError, setActionError] = useState<string | null>(null);
	const [shareMessage, setShareMessage] = useState<string | null>(null);
	const [selectedMediaId, setSelectedMediaId] = useState<string | null>(null);
	const [pdfIncludeMedia, setPdfIncludeMedia] = useState(false);

	const summaryQuery = useQuery({
		queryKey: ["visit-summary", visitId],
		queryFn: () => patientsApi.visitSummary(visitId),
	});
	useEffect(() => {
		if (!summaryQuery.data) return;
		setChiefComplaint(summaryQuery.data.visit.chief_complaint ?? "");
		setDiagnosis(summaryQuery.data.visit.diagnosis ?? "");
		setTreatmentPlan(summaryQuery.data.visit.treatment_plan ?? "");
		setVisitNotes(summaryQuery.data.visit.notes ?? "");
	}, [summaryQuery.data]);
	const mediaQuery = useQuery({
		queryKey: ["patient-media", summaryQuery.data?.visit.patient_id],
		queryFn: () => patientsApi.listMedia(summaryQuery.data!.visit.patient_id),
		enabled: Boolean(summaryQuery.data?.visit.patient_id),
	});
	const externalSharesQuery = useQuery({
		queryKey: ["external-shares", summaryQuery.data?.visit.patient_id],
		queryFn: () => patientsApi.listExternalShares(summaryQuery.data!.visit.patient_id),
		enabled: Boolean(summaryQuery.data?.visit.patient_id),
	});

	const createPrescriptionMutation = useMutation({
		mutationFn: () =>
			patientsApi.createPrescription({
				visit_id: visitId,
				items: [
					{
						medication: rxMedication,
						dose: rxDose,
						frequency: rxFrequency,
						duration: rxDuration,
						notes: rxNotes || null,
					},
				],
			}),
		onSuccess: () => {
			setActionError(null);
			setRxMedication("");
			setRxDose("");
			setRxFrequency("");
			setRxDuration("");
			setRxNotes("");
			void queryClient.invalidateQueries({ queryKey: ["visit-summary", visitId] });
		},
		onError: (err: unknown) => {
			setActionError(err instanceof Error ? err.message : "Failed to add prescription.");
		},
	});
	const updateVisitMutation = useMutation({
		mutationFn: () =>
			patientsApi.updateVisit(visitId, {
				chief_complaint: chiefComplaint || null,
				diagnosis: diagnosis || null,
				treatment_plan: treatmentPlan || null,
				notes: visitNotes || null,
			}),
		onSuccess: () => {
			setActionError(null);
			void queryClient.invalidateQueries({ queryKey: ["visit-summary", visitId] });
		},
		onError: (err: unknown) => {
			setActionError(err instanceof Error ? err.message : "Failed to update visit.");
		},
	});

	const createFollowupMutation = useMutation({
		mutationFn: () => {
			const existing = summaryQuery.data?.visit.notes?.trim();
			const followupLine = `[FOLLOWUP] ${followupDate || "no-date"} - ${followupNotes || "No notes"}`;
			const notes = existing ? `${existing}\n${followupLine}` : followupLine;
			return patientsApi.updateVisit(visitId, { notes });
		},
		onSuccess: () => {
			setActionError(null);
			setFollowupDate("");
			setFollowupNotes("");
			void queryClient.invalidateQueries({ queryKey: ["visit-summary", visitId] });
		},
		onError: (err: unknown) => {
			setActionError(err instanceof Error ? err.message : "Failed to create follow-up.");
		},
	});

	const uploadMediaMutation = useMutation({
		mutationFn: () => {
			if (!summaryQuery.data?.visit.patient_id || !mediaFile) {
				throw new Error("Select a media file first.");
			}
			return patientsApi.uploadMedia(summaryQuery.data.visit.patient_id, {
				file: mediaFile,
				kind: mediaKind,
				visit_id: visitId,
			});
		},
		onSuccess: () => {
			setActionError(null);
			setMediaFile(null);
			void queryClient.invalidateQueries({
				queryKey: ["patient-media", summaryQuery.data?.visit.patient_id],
			});
			void queryClient.invalidateQueries({ queryKey: ["visit-summary", visitId] });
		},
		onError: (err: unknown) => {
			setActionError(err instanceof Error ? err.message : "Failed to upload media.");
		},
	});
	const createExternalShareMutation = useMutation({
		mutationFn: () => {
			const patientId = summaryQuery.data?.visit.patient_id;
			if (!patientId) throw new Error("Patient context missing.");
			const ttlSeconds = Math.max(1, Number.parseInt(shareTtlHours || "24", 10)) * 3600;
			const maxViews = Math.max(1, Number.parseInt(shareMaxViews || "5", 10));
			return patientsApi.createExternalShare(patientId, {
				expires_in_seconds: ttlSeconds,
				max_views: maxViews,
				recipient_label: shareRecipient || undefined,
				password: sharePassword || undefined,
				scope:
					shareScopeMode === "history"
						? { mode: "history" }
						: { mode: "visit", visit_id: visitId },
			});
		},
		onSuccess: (data) => {
			setActionError(null);
			setCreatedShare({
				url: data.url,
				password: data.password,
				expiresAt: data.expires_at,
			});
			setShareMessage("External share link created.");
			void queryClient.invalidateQueries({
				queryKey: ["external-shares", summaryQuery.data?.visit.patient_id],
			});
		},
		onError: (err: unknown) => {
			setActionError(err instanceof Error ? err.message : "Failed to create external share.");
		},
	});
	const revokeExternalShareMutation = useMutation({
		mutationFn: (shareId: string) => {
			const patientId = summaryQuery.data?.visit.patient_id;
			if (!patientId) throw new Error("Patient context missing.");
			return patientsApi.revokeExternalShare(patientId, shareId);
		},
		onSuccess: () => {
			setActionError(null);
			setShareMessage("External share revoked.");
			void queryClient.invalidateQueries({
				queryKey: ["external-shares", summaryQuery.data?.visit.patient_id],
			});
		},
		onError: (err: unknown) => {
			setActionError(err instanceof Error ? err.message : "Failed to revoke external share.");
		},
	});

	function handleOpenPdf(path: string): void {
		void openProtectedPdf(path, { includeMedia: pdfIncludeMedia }).catch((err) => {
			setActionError(err instanceof Error ? err.message : "Unable to open PDF.");
		});
	}

	return (
		<div className="space-y-6">
			<Link to="/patients" className="text-sm text-brand hover:underline">
				← Back to patients
			</Link>

			{summaryQuery.isLoading && (
				<p className="text-sm text-slate-500">Loading visit summary…</p>
			)}
			{summaryQuery.error && (
				<p className="text-sm text-red-600">Failed to load visit summary.</p>
			)}

			{summaryQuery.data && (
				<>
					<article className="card space-y-3">
						<header>
							<h1 className="text-xl font-semibold">Visit Detail</h1>
							<p className="text-sm text-slate-500">
								{new Date(summaryQuery.data.visit.visit_date).toLocaleString()}
							</p>
						</header>
						<dl className="grid grid-cols-2 gap-4 text-sm">
							<Field
								label="Chief complaint"
								value={summaryQuery.data.visit.chief_complaint}
							/>
							<Field
								label="Diagnosis"
								value={summaryQuery.data.visit.diagnosis}
							/>
							<Field
								label="Treatment plan"
								value={summaryQuery.data.visit.treatment_plan}
								wide
							/>
							<Field label="Notes" value={summaryQuery.data.visit.notes} wide />
						</dl>
					</article>

					<section className="card space-y-3">
						<h2 className="text-lg font-semibold">Update visit details</h2>
						<form
							className="space-y-2"
							onSubmit={(e) => {
								e.preventDefault();
								updateVisitMutation.mutate();
							}}
						>
							<input
								className="input input-sm"
								placeholder="Chief complaint"
								value={chiefComplaint}
								onChange={(e) => setChiefComplaint(e.target.value)}
							/>
							<input
								className="input input-sm"
								placeholder="Diagnosis"
								value={diagnosis}
								onChange={(e) => setDiagnosis(e.target.value)}
							/>
							<input
								className="input input-sm"
								placeholder="Treatment plan"
								value={treatmentPlan}
								onChange={(e) => setTreatmentPlan(e.target.value)}
							/>
							<textarea
								className="input input-sm"
								placeholder="Notes"
								value={visitNotes}
								onChange={(e) => setVisitNotes(e.target.value)}
							/>
							<button
								type="submit"
								className="btn btn-primary"
								disabled={updateVisitMutation.isPending}
							>
								{updateVisitMutation.isPending ? "Saving..." : "Save visit details"}
							</button>
						</form>
					</section>

					<section className="card space-y-3">
						<h2 className="text-lg font-semibold">Prescriptions</h2>
						{summaryQuery.data.prescriptions.length === 0 && (
							<p className="text-sm text-slate-500">
								No prescriptions attached to this visit.
							</p>
						)}
						{summaryQuery.data.prescriptions.map((rx) => (
							<div
								key={rx.id}
								className="rounded-md border border-slate-200 p-3 text-sm"
							>
								<p className="font-medium">Prescription {rx.id.slice(0, 8)}</p>
								<p className="text-slate-600">Items: {rx.items.length}</p>
								{rx.notes && <p className="text-slate-700">{rx.notes}</p>}
							</div>
						))}
						<form
							className="mt-3 space-y-2 rounded-md border border-slate-200 p-3"
							onSubmit={(e) => {
								e.preventDefault();
								createPrescriptionMutation.mutate();
							}}
						>
							<h3 className="text-sm font-semibold">Add prescription</h3>
							<input
								className="input input-sm"
								placeholder="Medication"
								value={rxMedication}
								onChange={(e) => setRxMedication(e.target.value)}
								required
							/>
							<div className="grid grid-cols-3 gap-2">
								<input
									className="input input-sm"
									placeholder="Dose"
									value={rxDose}
									onChange={(e) => setRxDose(e.target.value)}
									required
								/>
								<input
									className="input input-sm"
									placeholder="Frequency"
									value={rxFrequency}
									onChange={(e) => setRxFrequency(e.target.value)}
									required
								/>
								<input
									className="input input-sm"
									placeholder="Duration"
									value={rxDuration}
									onChange={(e) => setRxDuration(e.target.value)}
									required
								/>
							</div>
							<textarea
								className="input input-sm"
								placeholder="Notes"
								value={rxNotes}
								onChange={(e) => setRxNotes(e.target.value)}
							/>
							<button
								type="submit"
								className="btn btn-primary"
								disabled={createPrescriptionMutation.isPending}
							>
								{createPrescriptionMutation.isPending ? "Saving..." : "Add prescription"}
							</button>
						</form>
					</section>

					<section className="card space-y-3">
						<h2 className="text-lg font-semibold">Follow-up</h2>
						<form
							className="space-y-2"
							onSubmit={(e) => {
								e.preventDefault();
								createFollowupMutation.mutate();
							}}
						>
							<input
								type="date"
								className="input input-sm"
								value={followupDate}
								onChange={(e) => setFollowupDate(e.target.value)}
							/>
							<textarea
								className="input input-sm"
								placeholder="Follow-up notes"
								value={followupNotes}
								onChange={(e) => setFollowupNotes(e.target.value)}
							/>
							<button
								type="submit"
								className="btn"
								disabled={createFollowupMutation.isPending}
							>
								{createFollowupMutation.isPending ? "Saving..." : "Save follow-up"}
							</button>
						</form>
					</section>

					<section className="card space-y-3">
						<h2 className="text-lg font-semibold">Visit media</h2>
						<form
							className="space-y-2"
							onSubmit={(e) => {
								e.preventDefault();
								uploadMediaMutation.mutate();
							}}
						>
							<select
								className="input input-sm"
								value={mediaKind}
								onChange={(e) =>
									setMediaKind(
										e.target.value as "before" | "after" | "xray" | "other",
									)
								}
							>
								<option value="before">Before</option>
								<option value="after">After</option>
								<option value="xray">X-ray</option>
								<option value="other">Other</option>
							</select>
							<input
								type="file"
								accept="image/*"
								onChange={(e) => setMediaFile(e.target.files?.[0] ?? null)}
							/>
							<button
								type="submit"
								className="btn"
								disabled={uploadMediaMutation.isPending || !mediaFile}
							>
								{uploadMediaMutation.isPending ? "Uploading..." : "Upload media"}
							</button>
						</form>
						{mediaQuery.data && (
							<MediaGallery
								items={mediaQuery.data.filter(
									(m) => m.visit_id === visitId || m.visit_id == null,
								)}
								emptyMessage="No media for this visit yet."
								selectedId={selectedMediaId}
								onSelect={setSelectedMediaId}
							/>
						)}
					</section>

					<section className="card space-y-3">
						<h2 className="text-lg font-semibold">Quick actions</h2>
						<label className="flex items-center gap-2 text-sm text-slate-600">
							<input
								type="checkbox"
								className="rounded border-slate-300"
								checked={pdfIncludeMedia}
								onChange={(event) => setPdfIncludeMedia(event.target.checked)}
							/>
							Include images and scans in PDF exports
						</label>
						<div className="flex flex-wrap gap-2">
							{summaryQuery.data.prescriptions[0] && (
								<button
									type="button"
									className="btn btn-primary"
									onClick={() =>
										handleOpenPdf(
											`/prescriptions/${summaryQuery.data!.prescriptions[0].id}/pdf`,
										)
									}
								>
									Print prescription
								</button>
							)}
							<button
								type="button"
								className="btn"
								onClick={() => handleOpenPdf(`/visits/${visitId}/summary/pdf`)}
							>
								Print visit summary
							</button>
							<button
								type="button"
								className="btn"
								onClick={() =>
									handleOpenPdf(
										`/patients/${summaryQuery.data!.visit.patient_id}/history/pdf`,
									)
								}
							>
								Print full history
							</button>
							<button
								type="button"
								className="btn"
								onClick={async () => {
									const link = `${window.location.origin}/patients/${summaryQuery.data?.visit.patient_id}?visit=${visitId}`;
									try {
										await navigator.clipboard.writeText(link);
										setShareMessage("Summary link copied.");
										setActionError(null);
									} catch {
										setActionError("Could not copy summary link.");
									}
								}}
							>
								Share summary link
							</button>
						</div>
						<div className="space-y-1">
							<label className="text-xs text-slate-500">Visit summary link</label>
							<input
								readOnly
								className="input input-sm input-mono"
								value={`${window.location.origin}/patients/${summaryQuery.data.visit.patient_id}?visit=${visitId}`}
							/>
						</div>
						{shareMessage && <p className="text-sm text-emerald-700">{shareMessage}</p>}
						{actionError && <p className="text-sm text-red-600">{actionError}</p>}
					</section>

					<section className="card space-y-3">
						<h2 className="text-lg font-semibold">External share (patient handoff)</h2>
						<form
							className="space-y-2"
							onSubmit={(e) => {
								e.preventDefault();
								createExternalShareMutation.mutate();
							}}
						>
							<input
								className="input input-sm"
								placeholder="Recipient label (optional)"
								value={shareRecipient}
								onChange={(e) => setShareRecipient(e.target.value)}
							/>
							<div className="grid grid-cols-2 gap-2">
								<input
									type="number"
									min={1}
									className="input input-sm"
									placeholder="Expiry (hours)"
									value={shareTtlHours}
									onChange={(e) => setShareTtlHours(e.target.value)}
								/>
								<input
									type="number"
									min={1}
									max={50}
									className="input input-sm"
									placeholder="Max views"
									value={shareMaxViews}
									onChange={(e) => setShareMaxViews(e.target.value)}
								/>
							</div>
							<input
								type="text"
								className="input input-sm"
								placeholder="Password (optional, auto-generated if empty)"
								value={sharePassword}
								onChange={(e) => setSharePassword(e.target.value)}
							/>
							<select
								className="input input-sm"
								value={shareScopeMode}
								onChange={(e) =>
									setShareScopeMode(e.target.value as "visit" | "history")
								}
							>
								<option value="visit">Share this visit only</option>
								<option value="history">Share entire history</option>
							</select>
							<button
								type="submit"
								className="btn btn-primary"
								disabled={createExternalShareMutation.isPending}
							>
								{createExternalShareMutation.isPending ? "Generating..." : "Generate secure share"}
							</button>
						</form>

						{createdShare && (
							<div className="space-y-1 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
								<p>
									<strong>URL:</strong> {createdShare.url}
								</p>
								<p>
									<strong>Password:</strong> {createdShare.password}
								</p>
								<p>
									<strong>Expires:</strong> {new Date(createdShare.expiresAt).toLocaleString()}
								</p>
							</div>
						)}

						{externalSharesQuery.data && externalSharesQuery.data.length > 0 && (
							<div className="space-y-2">
								<h3 className="text-sm font-semibold">Existing shares</h3>
								<ul className="space-y-2">
									{externalSharesQuery.data.map((share) => (
										<li
											key={share.id}
											className="flex items-center justify-between rounded-md border border-slate-200 p-2 text-sm"
										>
											<div>
												<p>
													{share.recipient_label || "External recipient"} · views{" "}
													{share.view_count}/{share.max_views}
												</p>
												<p className="text-xs text-slate-500">
													Expires {new Date(share.expires_at).toLocaleString()}
													{share.revoked_at ? " · revoked" : ""}
												</p>
											</div>
											{!share.revoked_at && (
												<button
													type="button"
													className="text-xs text-red-600 hover:underline"
													disabled={revokeExternalShareMutation.isPending}
													onClick={() => revokeExternalShareMutation.mutate(share.id)}
												>
													Revoke
												</button>
											)}
										</li>
									))}
								</ul>
							</div>
						)}
					</section>
				</>
			)}
		</div>
	);
}

function Field({
	label,
	value,
	wide = false,
}: { label: string; value: string | null; wide?: boolean }) {
	return (
		<div className={wide ? "col-span-2" : ""}>
			<dt className="text-slate-500">{label}</dt>
			<dd>{value ?? <span className="text-slate-400">—</span>}</dd>
		</div>
	);
}
