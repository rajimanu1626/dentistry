import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";

import { auth } from "@/lib/auth";
import {
	type ApiError,
	createInvite,
	fetchMe,
	listInvites,
	revokeInvite,
} from "@/lib/auth-api";
import { requireClinicalWorkspace } from "@/lib/router-auth";

type Role = "dentist" | "assistant" | "front_desk" | "owner";

const roleOptions: Array<{ value: Role; label: string }> = [
	{ value: "dentist", label: "Dentist" },
	{ value: "assistant", label: "Assistant" },
	{ value: "front_desk", label: "Front desk" },
	{ value: "owner", label: "Owner" },
];

export const Route = createFileRoute("/settings/team")({
	beforeLoad: requireClinicalWorkspace,
	component: TeamSettingsPage,
});

function TeamSettingsPage() {
	const queryClient = useQueryClient();
	const clinicId = auth.getClinicId();
	const [email, setEmail] = useState("");
	const [role, setRole] = useState<Role>("dentist");
	const [tokenData, setTokenData] = useState<{
		token: string;
		email: string;
		expiresAt: string;
	} | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [toast, setToast] = useState<string | null>(null);

	const meQuery = useQuery({
		queryKey: ["auth", "me"],
		queryFn: fetchMe,
	});

	const currentMembership = useMemo(
		() => meQuery.data?.memberships.find((m) => m.clinic_id === clinicId),
		[meQuery.data, clinicId],
	);
	const isOwner = currentMembership?.role === "owner";
	const invitesQuery = useQuery({
		queryKey: ["auth", "invites"],
		queryFn: listInvites,
		enabled: isOwner,
	});

	const inviteMutation = useMutation({
		mutationFn: () => createInvite({ email, role }),
		onSuccess: (data) => {
			setError(null);
			setToast("Invite created. Share the URL below.");
			setTokenData({
				token: data.invite_token,
				email: data.email,
				expiresAt: data.expires_at,
			});
			void queryClient.invalidateQueries({ queryKey: ["auth", "invites"] });
		},
		onError: (err: ApiError) => {
			setTokenData(null);
			setError(err.message);
		},
	});
	const revokeMutation = useMutation({
		mutationFn: (inviteId: string) => revokeInvite(inviteId),
		onSuccess: () => {
			setToast("Invite revoked.");
			void queryClient.invalidateQueries({ queryKey: ["auth", "invites"] });
		},
		onError: (err: ApiError) => setError(err.message),
	});

	const inviteUrl = tokenData
		? `${window.location.origin}/signup?token=${encodeURIComponent(tokenData.token)}&email=${encodeURIComponent(tokenData.email)}`
		: "";

	async function copy(value: string, label: string): Promise<void> {
		await navigator.clipboard.writeText(value);
		setToast(`${label} copied.`);
	}

	return (
		<div className="space-y-6">
			<header>
				<h1 className="text-2xl font-semibold">Team invites</h1>
				<p className="mt-1 text-sm text-slate-600">
					Invite dentists and staff to your clinic. Invite links are one-time
					use.
				</p>
			</header>

			<section className="card space-y-4">
				{!clinicId && (
					<p className="text-sm text-red-600">
						No clinic selected. Sign out and sign in again to initialize your
						clinic context.
					</p>
				)}
				{toast && <p className="text-sm text-emerald-700">{toast}</p>}
				{meQuery.isLoading && (
					<p className="text-sm text-slate-500">Loading your membership…</p>
				)}
				{!meQuery.isLoading && !isOwner && (
					<p className="text-sm text-red-600">
						Only clinic owners can create invite links.
					</p>
				)}

				<form
					className="space-y-4"
					onSubmit={(e) => {
						e.preventDefault();
						if (!isOwner || !clinicId) return;
						inviteMutation.mutate();
					}}
				>
					<label className="block text-sm">
						<span className="font-medium text-slate-700">Invitee email</span>
						<input
							type="email"
							required
							className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							placeholder="dentist@clinic.com"
							disabled={!isOwner || !clinicId || inviteMutation.isPending}
						/>
					</label>

					<label className="block text-sm">
						<span className="font-medium text-slate-700">Role</span>
						<select
							className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
							value={role}
							onChange={(e) => setRole(e.target.value as Role)}
							disabled={!isOwner || !clinicId || inviteMutation.isPending}
						>
							{roleOptions.map((opt) => (
								<option key={opt.value} value={opt.value}>
									{opt.label}
								</option>
							))}
						</select>
					</label>

					<button
						type="submit"
						className="btn btn-primary"
						disabled={
							!isOwner || !clinicId || inviteMutation.isPending || !email.trim()
						}
					>
						{inviteMutation.isPending ? "Creating invite…" : "Create invite"}
					</button>
				</form>

				{error && <p className="text-sm text-red-600">{error}</p>}

				{tokenData && (
					<div className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-4">
						<p className="text-sm font-medium text-slate-800">Invite created</p>
						<p className="text-xs text-slate-600">
							Expires at:{" "}
							<span className="font-mono">{tokenData.expiresAt}</span>
						</p>
						<label
							htmlFor="invite-token"
							className="block text-xs font-medium text-slate-700"
						>
							Invite token
						</label>
						<input
							id="invite-token"
							readOnly
							value={tokenData.token}
							className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-xs"
						/>
						<button
							type="button"
							className="btn"
							onClick={() => void copy(tokenData.token, "Invite token")}
						>
							Copy token
						</button>
						<label
							htmlFor="invite-url"
							className="block text-xs font-medium text-slate-700"
						>
							Invite signup URL
						</label>
						<input
							id="invite-url"
							readOnly
							value={inviteUrl}
							className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-xs"
						/>
						<button
							type="button"
							className="btn"
							onClick={() => void copy(inviteUrl, "Invite URL")}
						>
							Copy URL
						</button>
					</div>
				)}

				{isOwner && (
					<div className="space-y-2">
						<h3 className="text-sm font-medium text-slate-700">
							Recent invites
						</h3>
						{invitesQuery.isLoading && (
							<p className="text-sm text-slate-500">Loading invites…</p>
						)}
						{invitesQuery.data && invitesQuery.data.length === 0 && (
							<p className="text-sm text-slate-500">No invites created yet.</p>
						)}
						{invitesQuery.data && invitesQuery.data.length > 0 && (
							<ul className="divide-y divide-slate-200 rounded-md border border-slate-200 bg-white">
								{invitesQuery.data.map((invite) => (
									<li
										key={invite.invite_id}
										className="flex items-center justify-between px-3 py-2"
									>
										<div>
											<p className="text-sm font-medium">{invite.email}</p>
											<p className="text-xs text-slate-500">
												{invite.role} · expires{" "}
												{new Date(invite.expires_at).toLocaleString()}
												{invite.accepted_at ? " · accepted" : ""}
												{invite.revoked_at ? " · revoked" : ""}
											</p>
										</div>
										{!invite.accepted_at && !invite.revoked_at && (
											<button
												type="button"
												className="text-xs text-red-600 hover:underline"
												onClick={() => revokeMutation.mutate(invite.invite_id)}
												disabled={revokeMutation.isPending}
											>
												Revoke
											</button>
										)}
									</li>
								))}
							</ul>
						)}
					</div>
				)}
			</section>
		</div>
	);
}
