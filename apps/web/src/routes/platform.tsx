import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";

import { auth } from "@/lib/auth";
import { type ApiError, fetchMe } from "@/lib/auth-api";
import {
	type PlatformClinic,
	type PlatformInviteCreated,
	platformApi,
} from "@/lib/platform-api";
import { requirePlatformAuth } from "@/lib/router-auth";

type Tab = "clinics" | "organizations" | "users";

export const Route = createFileRoute("/platform")({
	beforeLoad: requirePlatformAuth,
	component: PlatformConsolePage,
});

function PlatformConsolePage() {
	const queryClient = useQueryClient();
	const isAdmin = auth.isPlatformAdmin();
	const [tab, setTab] = useState<Tab>("clinics");
	const [error, setError] = useState<string | null>(null);
	const [toast, setToast] = useState<string | null>(null);

	const meQuery = useQuery({ queryKey: ["auth", "me"], queryFn: fetchMe });
	const clinicsQuery = useQuery({
		queryKey: ["platform", "clinics"],
		queryFn: platformApi.listClinics,
	});
	const groupsQuery = useQuery({
		queryKey: ["platform", "groups"],
		queryFn: platformApi.listGroups,
	});
	const usersQuery = useQuery({
		queryKey: ["platform", "users"],
		queryFn: platformApi.listUsers,
	});

	const [clinicName, setClinicName] = useState("");
	const [clinicSlug, setClinicSlug] = useState("");
	const [clinicAddress, setClinicAddress] = useState("");
	const [clinicGroupId, setClinicGroupId] = useState("");
	const [groupName, setGroupName] = useState("");
	const [groupOwnerId, setGroupOwnerId] = useState("");
	const [inviteClinicId, setInviteClinicId] = useState("");
	const [inviteEmail, setInviteEmail] = useState("");
	const [inviteRole, setInviteRole] = useState<"owner" | "dentist">("owner");
	const [inviteResult, setInviteResult] = useState<PlatformInviteCreated | null>(
		null,
	);

	const createClinicMutation = useMutation({
		mutationFn: () =>
			platformApi.createClinic({
				name: clinicName,
				slug: clinicSlug,
				address: clinicAddress || null,
				group_id: clinicGroupId || null,
			}),
		onSuccess: () => {
			setToast("Clinic created.");
			setClinicName("");
			setClinicSlug("");
			setClinicAddress("");
			setClinicGroupId("");
			void queryClient.invalidateQueries({ queryKey: ["platform", "clinics"] });
		},
		onError: (err: ApiError) => setError(err.message),
	});

	const createGroupMutation = useMutation({
		mutationFn: () =>
			platformApi.createGroup({ name: groupName, owner_user_id: groupOwnerId }),
		onSuccess: () => {
			setToast("Organization created.");
			setGroupName("");
			setGroupOwnerId("");
			void queryClient.invalidateQueries({ queryKey: ["platform", "groups"] });
		},
		onError: (err: ApiError) => setError(err.message),
	});

	const inviteMutation = useMutation({
		mutationFn: () =>
			platformApi.createClinicInvite(inviteClinicId, {
				email: inviteEmail,
				role: inviteRole,
			}),
		onSuccess: (data) => {
			setInviteResult(data);
			setToast("Clinic invite created.");
		},
		onError: (err: ApiError) => setError(err.message),
	});

	const toggleUserMutation = useMutation({
		mutationFn: (args: { userId: string; isActive: boolean }) =>
			platformApi.updateUser(args.userId, { is_active: args.isActive }),
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: ["platform", "users"] });
		},
		onError: (err: ApiError) => setError(err.message),
	});

	const roleLabel = useMemo(() => {
		const role = meQuery.data?.system_role ?? auth.getSystemRole();
		if (role === "platform_admin") return "Platform admin";
		if (role === "platform_support") return "Platform support (read-only)";
		return "Platform";
	}, [meQuery.data?.system_role]);

	const inviteUrl = inviteResult
		? `${window.location.origin}/signup?token=${encodeURIComponent(inviteResult.invite_token)}&email=${encodeURIComponent(inviteResult.email)}`
		: "";

	return (
		<div className="space-y-6">
			<header>
				<h1 className="text-2xl font-semibold">Platform console</h1>
				<p className="mt-1 text-sm text-slate-600">
					Manage organizations, clinics, and users. No patient clinical data is
					available here.
				</p>
				<p className="mt-2 text-xs text-slate-500">
					Signed in as {meQuery.data?.user.email ?? "…"} · {roleLabel}
				</p>
			</header>

			<div className="flex flex-wrap gap-2">
				{(["clinics", "organizations", "users"] as Tab[]).map((t) => (
					<button
						key={t}
						type="button"
						className={tab === t ? "btn btn-primary" : "btn"}
						onClick={() => {
							setTab(t);
							setError(null);
						}}
					>
						{t === "organizations" ? "Organizations" : t[0]!.toUpperCase() + t.slice(1)}
					</button>
				))}
			</div>

			{toast && <p className="text-sm text-emerald-700">{toast}</p>}
			{error && <p className="text-sm text-red-600">{error}</p>}

			{tab === "clinics" && (
				<div className="space-y-4">
					{isAdmin && (
						<section className="card space-y-3">
							<h2 className="text-lg font-semibold">Create clinic</h2>
							<form
								className="grid gap-3 md:grid-cols-2"
								onSubmit={(e) => {
									e.preventDefault();
									setError(null);
									createClinicMutation.mutate();
								}}
							>
								<label className="block text-sm">
									<span className="font-medium">Name</span>
									<input
										className="input mt-1 w-full"
										value={clinicName}
										onChange={(e) => setClinicName(e.target.value)}
										required
									/>
								</label>
								<label className="block text-sm">
									<span className="font-medium">Slug</span>
									<input
										className="input mt-1 w-full"
										value={clinicSlug}
										onChange={(e) => setClinicSlug(e.target.value)}
										placeholder="sunshine-dental"
										required
									/>
								</label>
								<label className="block text-sm md:col-span-2">
									<span className="font-medium">Address</span>
									<input
										className="input mt-1 w-full"
										value={clinicAddress}
										onChange={(e) => setClinicAddress(e.target.value)}
									/>
								</label>
								<label className="block text-sm md:col-span-2">
									<span className="font-medium">Organization (optional)</span>
									<select
										className="input mt-1 w-full"
										value={clinicGroupId}
										onChange={(e) => setClinicGroupId(e.target.value)}
									>
										<option value="">Standalone clinic (no organization)</option>
										{groupsQuery.data?.map((g) => (
											<option key={g.id} value={g.id}>
												{g.name}
											</option>
										))}
									</select>
								</label>
								<button
									type="submit"
									className="btn btn-primary md:col-span-2"
									disabled={createClinicMutation.isPending}
								>
									Create clinic
								</button>
							</form>
						</section>
					)}

					<section className="card space-y-3">
						<h2 className="text-lg font-semibold">Clinics</h2>
						{clinicsQuery.isLoading && (
							<p className="text-sm text-slate-500">Loading…</p>
						)}
						{clinicsQuery.data && clinicsQuery.data.length === 0 && (
							<p className="text-sm text-slate-500">No clinics yet.</p>
						)}
						{clinicsQuery.data && clinicsQuery.data.length > 0 && (
							<ul className="divide-y divide-slate-200">
								{clinicsQuery.data.map((c) => (
									<ClinicRow key={c.id} clinic={c} />
								))}
							</ul>
						)}
					</section>

					{isAdmin && (
						<section className="card space-y-3">
							<h2 className="text-lg font-semibold">Invite clinic owner</h2>
							<form
								className="grid gap-3 md:grid-cols-2"
								onSubmit={(e) => {
									e.preventDefault();
									setError(null);
									inviteMutation.mutate();
								}}
							>
								<label className="block text-sm md:col-span-2">
									<span className="font-medium">Clinic</span>
									<select
										className="input mt-1 w-full"
										value={inviteClinicId}
										onChange={(e) => setInviteClinicId(e.target.value)}
										required
									>
										<option value="">Select clinic…</option>
										{clinicsQuery.data?.map((c) => (
											<option key={c.id} value={c.id}>
												{c.name} ({c.slug})
											</option>
										))}
									</select>
								</label>
								<label className="block text-sm">
									<span className="font-medium">Email</span>
									<input
										type="email"
										className="input mt-1 w-full"
										value={inviteEmail}
										onChange={(e) => setInviteEmail(e.target.value)}
										required
									/>
								</label>
								<label className="block text-sm">
									<span className="font-medium">Role</span>
									<select
										className="input mt-1 w-full"
										value={inviteRole}
										onChange={(e) =>
											setInviteRole(e.target.value as "owner" | "dentist")
										}
									>
										<option value="owner">Owner</option>
										<option value="dentist">Dentist</option>
									</select>
								</label>
								<button
									type="submit"
									className="btn btn-primary md:col-span-2"
									disabled={inviteMutation.isPending || !inviteClinicId}
								>
									Create invite
								</button>
							</form>
							{inviteResult && (
								<div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs">
									<p className="font-medium">Invite URL</p>
									<p className="mt-1 break-all font-mono">{inviteUrl}</p>
								</div>
							)}
						</section>
					)}
				</div>
			)}

			{tab === "organizations" && (
				<div className="space-y-4">
					<p className="text-sm text-slate-600">
						An organization is a parent chain (e.g. &quot;ABC Dental Group&quot;) that
						can own multiple clinic locations. Use this when one business runs
						several branches. For a single clinic, skip this and create the clinic
						directly under the Clinics tab.
					</p>
					{isAdmin && (
						<section className="card space-y-3">
							<h2 className="text-lg font-semibold">Create organization</h2>
							<form
								className="grid gap-3 md:grid-cols-2"
								onSubmit={(e) => {
									e.preventDefault();
									setError(null);
									createGroupMutation.mutate();
								}}
							>
								<label className="block text-sm">
									<span className="font-medium">Name</span>
									<input
										className="input mt-1 w-full"
										value={groupName}
										onChange={(e) => setGroupName(e.target.value)}
										required
									/>
								</label>
								<label className="block text-sm">
									<span className="font-medium">Chain owner (existing user)</span>
									<select
										className="input mt-1 w-full"
										value={groupOwnerId}
										onChange={(e) => setGroupOwnerId(e.target.value)}
										required
									>
										<option value="">Select user…</option>
										{usersQuery.data?.map((u) => (
											<option key={u.id} value={u.id}>
												{u.full_name ?? u.email} ({u.email})
											</option>
										))}
									</select>
									<p className="mt-1 text-xs text-slate-500">
										Must be an existing account from the Users tab (not an email
										address).
									</p>
								</label>
								<button
									type="submit"
									className="btn btn-primary md:col-span-2"
									disabled={
										createGroupMutation.isPending ||
										!groupName.trim() ||
										!groupOwnerId
									}
								>
									Create organization
								</button>
							</form>
						</section>
					)}
					<section className="card">
						<h2 className="text-lg font-semibold">Organizations</h2>
						{groupsQuery.isLoading && (
							<p className="mt-2 text-sm text-slate-500">Loading…</p>
						)}
						{groupsQuery.data && groupsQuery.data.length === 0 && (
							<p className="mt-2 text-sm text-slate-500">None yet.</p>
						)}
						{groupsQuery.data && groupsQuery.data.length > 0 && (
							<ul className="mt-3 divide-y divide-slate-200">
								{groupsQuery.data.map((g) => (
									<li key={g.id} className="py-2 text-sm">
										<p className="font-medium">{g.name}</p>
										<p className="text-xs text-slate-500 font-mono">
											{g.id} · owner {g.owner_user_id}
										</p>
									</li>
								))}
							</ul>
						)}
					</section>
				</div>
			)}

			{tab === "users" && (
				<section className="card">
					<h2 className="text-lg font-semibold">Users</h2>
					{usersQuery.isLoading && (
						<p className="mt-2 text-sm text-slate-500">Loading…</p>
					)}
					{usersQuery.isError && (
						<p className="mt-2 text-sm text-red-600">
							Failed to load users. Try refreshing the page.
						</p>
					)}
					{usersQuery.data && usersQuery.data.length === 0 && (
						<p className="mt-2 text-sm text-slate-500">No users found.</p>
					)}
					{usersQuery.data && usersQuery.data.length > 0 && (
						<ul className="mt-3 divide-y divide-slate-200">
							{usersQuery.data.map((u) => (
								<li
									key={u.id}
									className="flex items-center justify-between gap-4 py-2 text-sm"
								>
									<div>
										<p className="font-medium">
											{u.full_name ?? u.email}
										</p>
										<p className="text-xs text-slate-500">
											{u.email}
											{u.system_role ? ` · ${u.system_role}` : ""}
											{!u.is_active ? " · inactive" : ""}
										</p>
									</div>
									{isAdmin && (
										<button
											type="button"
											className="btn text-xs"
											onClick={() =>
												toggleUserMutation.mutate({
													userId: u.id,
													isActive: !u.is_active,
												})
											}
										>
											{u.is_active ? "Deactivate" : "Activate"}
										</button>
									)}
								</li>
							))}
						</ul>
					)}
				</section>
			)}
		</div>
	);
}

function ClinicRow({ clinic }: { clinic: PlatformClinic }) {
	return (
		<li className="py-3 text-sm">
			<p className="font-medium">{clinic.name}</p>
			<p className="text-xs text-slate-500">
				<span className="font-mono">{clinic.slug}</span> · {clinic.id}
			</p>
			{clinic.address && (
				<p className="text-xs text-slate-500">{clinic.address}</p>
			)}
		</li>
	);
}
