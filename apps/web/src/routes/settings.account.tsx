import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { auth } from "@/lib/auth";
import {
	type ApiError,
	changePassword,
	fetchMe,
	updateProfile,
} from "@/lib/auth-api";
import { formatClinicRole } from "@/lib/roles";
import { requireAuth } from "@/lib/router-auth";

export const Route = createFileRoute("/settings/account")({
	beforeLoad: requireAuth,
	component: AccountSettingsPage,
});

function AccountSettingsPage() {
	const queryClient = useQueryClient();
	const clinicId = auth.getClinicId();
	const meQuery = useQuery({
		queryKey: ["auth", "me"],
		queryFn: fetchMe,
	});

	const [fullName, setFullName] = useState("");
	const [profileError, setProfileError] = useState<string | null>(null);
	const [profileSuccess, setProfileSuccess] = useState<string | null>(null);

	const [currentPassword, setCurrentPassword] = useState("");
	const [newPassword, setNewPassword] = useState("");
	const [confirmPassword, setConfirmPassword] = useState("");
	const [passwordError, setPasswordError] = useState<string | null>(null);
	const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);

	useEffect(() => {
		if (meQuery.data?.user.full_name) {
			setFullName(meQuery.data.user.full_name);
		}
	}, [meQuery.data]);

	const membership = meQuery.data?.memberships.find(
		(m) => m.clinic_id === clinicId,
	);

	const profileMutation = useMutation({
		mutationFn: () => updateProfile(fullName.trim()),
		onSuccess: async () => {
			setProfileError(null);
			setProfileSuccess("Profile updated.");
			await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
		},
		onError: (err: ApiError) => {
			setProfileSuccess(null);
			setProfileError(err.message);
		},
	});

	const passwordMutation = useMutation({
		mutationFn: () => changePassword(currentPassword, newPassword),
		onSuccess: () => {
			setPasswordError(null);
			setPasswordSuccess("Password updated successfully.");
			setCurrentPassword("");
			setNewPassword("");
			setConfirmPassword("");
		},
		onError: (err: ApiError) => {
			setPasswordSuccess(null);
			setPasswordError(err.message);
		},
	});

	return (
		<div className="mx-auto max-w-xl space-y-6">
			<header>
				<h1 className="text-2xl font-semibold">Account</h1>
				<p className="mt-1 text-sm text-slate-600">
					Update your display name and password.
				</p>
			</header>

			<section className="card space-y-4">
				<h2 className="text-sm font-medium text-slate-800">Profile</h2>
				{meQuery.data && (
					<dl className="grid gap-2 text-sm">
						<div>
							<dt className="text-slate-500">Email</dt>
							<dd className="font-medium text-slate-900">
								{meQuery.data.user.email}
							</dd>
						</div>
						{membership && (
							<div>
								<dt className="text-slate-500">Role</dt>
								<dd className="font-medium text-slate-900">
									{formatClinicRole(membership.role)}
									{membership.clinic_name
										? ` at ${membership.clinic_name}`
										: ""}
								</dd>
							</div>
						)}
					</dl>
				)}
				<form
					className="space-y-4"
					onSubmit={(e) => {
						e.preventDefault();
						setProfileError(null);
						setProfileSuccess(null);
						if (!fullName.trim()) {
							setProfileError("Name is required.");
							return;
						}
						profileMutation.mutate();
					}}
				>
					{profileError && (
						<p className="text-sm text-red-600">{profileError}</p>
					)}
					{profileSuccess && (
						<p className="text-sm text-emerald-700">{profileSuccess}</p>
					)}
					<label className="field">
						<span>Full name</span>
						<input
							type="text"
							required
							maxLength={160}
							autoComplete="name"
							className="input mt-1"
							value={fullName}
							onChange={(e) => setFullName(e.target.value)}
						/>
					</label>
					<button
						type="submit"
						className="btn btn-primary"
						disabled={profileMutation.isPending || !fullName.trim()}
					>
						{profileMutation.isPending ? "Saving…" : "Save profile"}
					</button>
				</form>
			</section>

			<section className="card space-y-4">
				<header>
					<h2 className="text-sm font-medium text-slate-800">Password</h2>
					<p className="mt-1 text-xs text-slate-500">
						Minimum length is 10 characters.
					</p>
				</header>
				<form
					className="space-y-4"
					onSubmit={(e) => {
						e.preventDefault();
						setPasswordError(null);
						setPasswordSuccess(null);
						if (newPassword !== confirmPassword) {
							setPasswordError("New password and confirmation must match.");
							return;
						}
						passwordMutation.mutate();
					}}
				>
					{passwordError && (
						<p className="text-sm text-red-600">{passwordError}</p>
					)}
					{passwordSuccess && (
						<p className="text-sm text-emerald-700">{passwordSuccess}</p>
					)}
					<label className="field">
						<span>Current password</span>
						<input
							type="password"
							required
							minLength={10}
							autoComplete="current-password"
							className="input mt-1"
							value={currentPassword}
							onChange={(e) => setCurrentPassword(e.target.value)}
						/>
					</label>
					<label className="field">
						<span>New password</span>
						<input
							type="password"
							required
							minLength={10}
							autoComplete="new-password"
							className="input mt-1"
							value={newPassword}
							onChange={(e) => setNewPassword(e.target.value)}
						/>
					</label>
					<label className="field">
						<span>Confirm new password</span>
						<input
							type="password"
							required
							minLength={10}
							autoComplete="new-password"
							className="input mt-1"
							value={confirmPassword}
							onChange={(e) => setConfirmPassword(e.target.value)}
						/>
					</label>
					<button
						type="submit"
						className="btn btn-primary"
						disabled={
							passwordMutation.isPending ||
							!currentPassword ||
							!newPassword ||
							!confirmPassword
						}
					>
						{passwordMutation.isPending ? "Updating…" : "Update password"}
					</button>
				</form>
			</section>
		</div>
	);
}
