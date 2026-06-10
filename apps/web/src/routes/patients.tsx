import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { patientsApi } from "@/lib/patients";
import { requireClinicalWorkspace } from "@/lib/router-auth";

export const Route = createFileRoute("/patients")({
	beforeLoad: requireClinicalWorkspace,
	component: PatientsPage,
});

function PatientsPage() {
	const [searchInput, setSearchInput] = useState("");
	const [searchQuery, setSearchQuery] = useState("");

	useEffect(() => {
		const handle = window.setTimeout(() => {
			setSearchQuery(searchInput.trim());
		}, 300);
		return () => window.clearTimeout(handle);
	}, [searchInput]);

	const { data, isLoading, isFetching, error } = useQuery({
		queryKey: ["patients", { page: 1, q: searchQuery }],
		queryFn: () =>
			patientsApi.list({ page: 1, page_size: 20, q: searchQuery || undefined }),
	});

	return (
		<div className="space-y-6">
			<header className="flex items-center justify-between">
				<h1 className="text-2xl font-semibold">Patients</h1>
				<Link to="/patients/new" className="btn btn-primary">
					New patient
				</Link>
			</header>

			<section className="card space-y-4">
				<div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
					<label htmlFor="patient-search" className="mb-2 block text-sm font-medium">
						Find patient quickly
					</label>
					<div className="flex gap-2">
						<input
							id="patient-search"
							type="search"
							className="input w-full"
							placeholder="Name, patient ID, or mobile number"
							value={searchInput}
							onChange={(event) => setSearchInput(event.target.value)}
						/>
						{searchInput && (
							<button
								type="button"
								className="btn"
								onClick={() => {
									setSearchInput("");
									setSearchQuery("");
								}}
							>
								Clear
							</button>
						)}
					</div>
					<div className="mt-2 flex items-center justify-between text-xs text-slate-500">
						<p>Supports name, patient ID, and phone search in current clinic.</p>
						{isFetching && !isLoading && <p>Updating results…</p>}
					</div>
				</div>
				{data && (
					<p className="text-xs text-slate-500">
						Showing {data.items.length} of {data.total} patient
						{data.total === 1 ? "" : "s"}
						{searchQuery ? ` for "${searchQuery}"` : ""}.
					</p>
				)}
				{isLoading && <p className="text-sm text-slate-500">Loading…</p>}
				{error && (
					<p className="text-sm text-red-600">
						Failed to load patients. Make sure you are signed in and have a
						clinic selected.
					</p>
				)}
				{data && data.items.length === 0 && (
					<p className="text-sm text-slate-500">
						{searchQuery ? (
							"No patients match this search."
						) : (
							<>
								No patients yet — click <strong>New patient</strong> to add the
								first one.
							</>
						)}
					</p>
				)}
				{data && data.items.length > 0 && (
					<ul className="divide-y divide-slate-200">
						{data.items.map((p) => (
							<li key={p.id} className="flex items-center justify-between py-3">
								<div>
									<p className="font-medium">{p.full_name}</p>
									<p className="text-xs text-slate-500">
										{p.patient_code}
										{p.date_of_birth ? ` · DOB ${p.date_of_birth}` : ""}
									</p>
								</div>
								<Link
									to="/patients/$patientId"
									params={{ patientId: p.id }}
									className="text-sm text-brand hover:underline"
								>
									Open
								</Link>
							</li>
						))}
					</ul>
				)}
			</section>
		</div>
	);
}
