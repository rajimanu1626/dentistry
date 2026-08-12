import { useQuery } from "@tanstack/react-query";
import { Link, createFileRoute, redirect } from "@tanstack/react-router";

import { apiClient } from "@/lib/api";
import { auth } from "@/lib/auth";
import { dashboardApi } from "@/lib/dashboard";
import { requireAuth } from "@/lib/router-auth";

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
	const statsQuery = useQuery({
		queryKey: ["dashboard", "stats"],
		queryFn: dashboardApi.stats,
	});
	const healthQuery = useQuery<Health>({
		queryKey: ["health"],
		queryFn: () => apiClient.get<Health>("/healthz"),
	});

	const stats = statsQuery.data;

	return (
		<div className="space-y-8">
			<section className="flex flex-wrap items-end justify-between gap-4">
				<div>
					<h1 className="text-2xl font-semibold">Dashboard</h1>
					<p className="mt-1 text-sm text-slate-600">
						Clinic activity at a glance.
					</p>
				</div>
				<Link to="/patients/new" className="btn btn-primary">
					New patient
				</Link>
			</section>

			<section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				<Stat
					label="Visits today"
					value={stats?.visits_today}
					loading={statsQuery.isLoading}
					hint="Scheduled / recorded today"
				/>
				<Stat
					label="Visits this week"
					value={stats?.visits_this_week}
					loading={statsQuery.isLoading}
					hint="Monday to now"
				/>
				<Stat
					label="Patients"
					value={stats?.patients_total}
					loading={statsQuery.isLoading}
					hint={
						stats
							? `+${stats.patients_added_today} today · +${stats.patients_added_this_week} this week`
							: "Total in this clinic"
					}
				/>
				<Stat
					label="New patients today"
					value={stats?.patients_added_today}
					loading={statsQuery.isLoading}
				/>
				<Stat
					label="New patients this week"
					value={stats?.patients_added_this_week}
					loading={statsQuery.isLoading}
				/>
				<Stat
					label="Open share links"
					value={stats?.open_external_shares}
					loading={statsQuery.isLoading}
					hint="Active external shares"
				/>
			</section>

			{statsQuery.error && (
				<p className="text-sm text-red-600">
					{(statsQuery.error as Error).message ||
						"Could not load clinic insights."}
				</p>
			)}

			<section className="grid gap-4 sm:grid-cols-2">
				<Link
					to="/patients"
					className="rounded-xl border border-slate-200 bg-white p-5 transition hover:border-brand/40 hover:shadow-sm"
				>
					<p className="text-sm font-medium text-brand">Patients</p>
					<p className="mt-1 text-sm text-slate-600">
						Search records, open charts, add visits.
					</p>
				</Link>
				<Link
					to="/settings/team"
					className="rounded-xl border border-slate-200 bg-white p-5 transition hover:border-brand/40 hover:shadow-sm"
				>
					<p className="text-sm font-medium text-brand">Team</p>
					<p className="mt-1 text-sm text-slate-600">
						Invite dentists and staff to this clinic.
					</p>
				</Link>
			</section>

			<section className="rounded-xl border border-slate-200 bg-white px-5 py-4">
				<div className="flex flex-wrap items-center justify-between gap-3 text-sm">
					<p className="font-medium text-slate-700">API</p>
					{healthQuery.isLoading && (
						<p className="text-slate-500">Checking…</p>
					)}
					{healthQuery.error && (
						<p className="text-red-600">Unreachable</p>
					)}
					{healthQuery.data && (
						<p className="text-slate-600">
							<span className="font-medium text-emerald-600">
								{healthQuery.data.status}
							</span>
							<span className="mx-2 text-slate-300">·</span>
							<span className="font-mono text-xs">
								{healthQuery.data.service} {healthQuery.data.version}
							</span>
						</p>
					)}
				</div>
			</section>
		</div>
	);
}

function Stat({
	label,
	value,
	hint,
	loading,
}: {
	label: string;
	value: number | undefined;
	hint?: string;
	loading?: boolean;
}) {
	return (
		<div className="rounded-xl border border-slate-200 bg-white p-5">
			<p className="text-xs font-medium uppercase tracking-wide text-slate-500">
				{label}
			</p>
			<p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">
				{loading ? "—" : (value ?? "—")}
			</p>
			{hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
		</div>
	);
}
