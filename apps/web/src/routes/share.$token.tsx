import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

type LandingSummary = {
	share_id: string;
	recipient_label: string | null;
	expires_at: string;
};

type UnlockedPayload = {
	share_session_token: string;
	expires_in: number;
	patient_summary: {
		share_id: string;
		recipient_label: string | null;
		mode?: "visit" | "history" | string;
		visit_summary?: {
			visit_id: string;
			visit_date: string;
			chief_complaint: string | null;
			diagnosis: string | null;
			treatment_plan: string | null;
			notes: string | null;
			prescriptions: Array<{
				items: Array<Record<string, unknown>>;
				notes: string | null;
				created_at: string;
			}>;
		};
		history_summary?: {
			patient_id: string;
			visits: Array<{
				visit_id: string;
				visit_date: string;
				chief_complaint: string | null;
				diagnosis: string | null;
				treatment_plan: string | null;
				notes: string | null;
				prescriptions: Array<{
					items: Array<Record<string, unknown>>;
					notes: string | null;
					created_at: string;
				}>;
			}>;
		};
	};
};

export const Route = createFileRoute("/share/$token")({
	component: ShareAccessPage,
});

function ShareAccessPage() {
	const { token } = Route.useParams();
	const [summary, setSummary] = useState<LandingSummary | null>(null);
	const [password, setPassword] = useState("");
	const [status, setStatus] = useState<string | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [unlocked, setUnlocked] = useState<UnlockedPayload | null>(null);

	async function loadSummary(): Promise<void> {
		setError(null);
		try {
			const res = await fetch(`/api/share/${encodeURIComponent(token)}/summary`);
			if (!res.ok) {
				setError("This link is invalid or expired.");
				return;
			}
			setSummary((await res.json()) as LandingSummary);
		} catch {
			setError("Unable to open share link.");
		}
	}

	async function unlock(): Promise<void> {
		setError(null);
		setStatus(null);
		try {
			const res = await fetch(`/api/share/${encodeURIComponent(token)}/unlock`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ password }),
			});
			if (!res.ok) {
				setError("Wrong password or share is no longer valid.");
				return;
			}
			const payload = (await res.json()) as UnlockedPayload;
			setUnlocked(payload);
			setStatus("Access granted.");
		} catch {
			setError("Unlock failed.");
		}
	}

	return (
		<div className="mx-auto max-w-lg space-y-4">
			<h1 className="text-2xl font-semibold">Shared visit access</h1>
			<button type="button" className="btn" onClick={() => void loadSummary()}>
				Load share details
			</button>
			{summary && (
				<div className="rounded-md border border-slate-200 p-3 text-sm">
					<p>
						<strong>Recipient:</strong> {summary.recipient_label || "External viewer"}
					</p>
					<p>
						<strong>Expires:</strong> {new Date(summary.expires_at).toLocaleString()}
					</p>
				</div>
			)}
			<div className="space-y-2">
				<input
					type="password"
					className="w-full rounded-md border border-slate-300 px-3 py-2"
					placeholder="Enter password provided by clinic"
					value={password}
					onChange={(e) => setPassword(e.target.value)}
				/>
				<button
					type="button"
					className="btn btn-primary"
					onClick={() => void unlock()}
					disabled={!password}
				>
					Unlock
				</button>
			</div>
			{status && <p className="text-sm text-emerald-700">{status}</p>}
			{unlocked?.patient_summary.visit_summary && (
				<div className="space-y-3 rounded-md border border-slate-200 p-4 text-sm">
					<div className="flex items-center justify-between">
						<h2 className="text-lg font-semibold">Visit Summary</h2>
						<button type="button" className="btn" onClick={() => window.print()}>
							Print
						</button>
					</div>
					<p>
						<strong>Date:</strong>{" "}
						{new Date(unlocked.patient_summary.visit_summary.visit_date).toLocaleString()}
					</p>
					<p>
						<strong>Chief complaint:</strong>{" "}
						{unlocked.patient_summary.visit_summary.chief_complaint || "-"}
					</p>
					<p>
						<strong>Diagnosis:</strong>{" "}
						{unlocked.patient_summary.visit_summary.diagnosis || "-"}
					</p>
					<p>
						<strong>Treatment plan:</strong>{" "}
						{unlocked.patient_summary.visit_summary.treatment_plan || "-"}
					</p>
					<p>
						<strong>Notes:</strong> {unlocked.patient_summary.visit_summary.notes || "-"}
					</p>
					<div>
						<strong>Prescriptions:</strong>
						{unlocked.patient_summary.visit_summary.prescriptions.length === 0 ? (
							<p>None.</p>
						) : (
							<ul className="list-disc pl-5">
								{unlocked.patient_summary.visit_summary.prescriptions.map((rx, idx) => (
									<li key={`${rx.created_at}-${idx}`}>
										{rx.items.length} item(s)
										{rx.notes ? ` - ${rx.notes}` : ""}
									</li>
								))}
							</ul>
						)}
					</div>
				</div>
			)}
			{unlocked?.patient_summary.history_summary && (
				<div className="space-y-3 rounded-md border border-slate-200 p-4 text-sm">
					<div className="flex items-center justify-between">
						<h2 className="text-lg font-semibold">Full History Summary</h2>
						<button type="button" className="btn" onClick={() => window.print()}>
							Print
						</button>
					</div>
					{unlocked.patient_summary.history_summary.visits.length === 0 && (
						<p>No visits in shared history.</p>
					)}
					{unlocked.patient_summary.history_summary.visits.map((visit) => (
						<div key={visit.visit_id} className="rounded-md border border-slate-200 p-3">
							<p>
								<strong>Date:</strong> {new Date(visit.visit_date).toLocaleString()}
							</p>
							<p>
								<strong>Chief complaint:</strong> {visit.chief_complaint || "-"}
							</p>
							<p>
								<strong>Diagnosis:</strong> {visit.diagnosis || "-"}
							</p>
							<p>
								<strong>Treatment plan:</strong> {visit.treatment_plan || "-"}
							</p>
							<p>
								<strong>Notes:</strong> {visit.notes || "-"}
							</p>
							<p>
								<strong>Prescriptions:</strong> {visit.prescriptions.length}
							</p>
						</div>
					))}
				</div>
			)}
			{error && <p className="text-sm text-red-600">{error}</p>}
		</div>
	);
}
