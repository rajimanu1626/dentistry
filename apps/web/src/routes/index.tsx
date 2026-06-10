import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";

import { apiClient } from "@/lib/api";
import { auth } from "@/lib/auth";
import { requireAuth } from "@/lib/router-auth";
import { redirect } from "@tanstack/react-router";

interface Health {
	status: string;
	version: string;
	service: string;
}

export const Route = createFileRoute("/")({
	beforeLoad: () => {
		requireAuth();
		if (auth.isPlatformOperator() && !auth.getClinicId()) {
			throw redirect({ to: "/platform" });
		}
	},
	component: DashboardPage,
});

function DashboardPage() {
	const { data, isLoading, error } = useQuery<Health>({
		queryKey: ["health"],
		queryFn: () => apiClient.get<Health>("/healthz"),
	});

	return (
		<div className="space-y-6">
			<section>
				<h1 className="text-2xl font-semibold">Dashboard</h1>
				<p className="mt-1 text-sm text-slate-600">
					Multi-tenant dental CRM — patients, prescriptions, media, and sharing.
				</p>
			</section>

			<section className="card">
				<h2 className="text-sm font-medium uppercase tracking-wide text-slate-500">
					API status
				</h2>
				{isLoading && <p className="mt-2 text-sm">Checking API…</p>}
				{error && (
					<p className="mt-2 text-sm text-red-600">
						API unreachable. Make sure{" "}
						<code className="font-mono">docker compose up</code> is running.
					</p>
				)}
				{data && (
					<dl className="mt-2 grid grid-cols-3 gap-4 text-sm">
						<div>
							<dt className="text-slate-500">Status</dt>
							<dd className="font-medium text-emerald-600">{data.status}</dd>
						</div>
						<div>
							<dt className="text-slate-500">Service</dt>
							<dd>{data.service}</dd>
						</div>
						<div>
							<dt className="text-slate-500">Version</dt>
							<dd className="font-mono">{data.version}</dd>
						</div>
					</dl>
				)}
			</section>
		</div>
	);
}
