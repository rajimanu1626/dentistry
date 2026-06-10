import { useMutation } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

import { type ApiError, changePassword } from "@/lib/auth-api";
import { requireAuth } from "@/lib/router-auth";

export const Route = createFileRoute("/settings/security")({
	beforeLoad: requireAuth,
	component: SecuritySettingsPage,
});

function SecuritySettingsPage() {
	const [currentPassword, setCurrentPassword] = useState("");
	const [newPassword, setNewPassword] = useState("");
	const [confirmPassword, setConfirmPassword] = useState("");
	const [error, setError] = useState<string | null>(null);
	const [success, setSuccess] = useState<string | null>(null);

	const mutation = useMutation({
		mutationFn: () => changePassword(currentPassword, newPassword),
		onSuccess: () => {
			setError(null);
			setSuccess("Password updated successfully.");
			setCurrentPassword("");
			setNewPassword("");
			setConfirmPassword("");
		},
		onError: (err: ApiError) => {
			setSuccess(null);
			setError(err.message);
		},
	});

	return (
		<div className="mx-auto max-w-xl space-y-6">
			<header>
				<h1 className="text-2xl font-semibold">Security</h1>
				<p className="mt-1 text-sm text-slate-600">
					Update your account password. Minimum length is 10 characters.
				</p>
			</header>

			<form
				className="card space-y-4"
				onSubmit={(e) => {
					e.preventDefault();
					setError(null);
					setSuccess(null);
					if (newPassword !== confirmPassword) {
						setError("New password and confirmation must match.");
						return;
					}
					mutation.mutate();
				}}
			>
				{error && <p className="text-sm text-red-600">{error}</p>}
				{success && <p className="text-sm text-emerald-700">{success}</p>}
				<label className="block text-sm">
					<span className="font-medium text-slate-700">Current password</span>
					<input
						type="password"
						required
						minLength={10}
						autoComplete="current-password"
						className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
						value={currentPassword}
						onChange={(e) => setCurrentPassword(e.target.value)}
					/>
				</label>
				<label className="block text-sm">
					<span className="font-medium text-slate-700">New password</span>
					<input
						type="password"
						required
						minLength={10}
						autoComplete="new-password"
						className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
						value={newPassword}
						onChange={(e) => setNewPassword(e.target.value)}
					/>
				</label>
				<label className="block text-sm">
					<span className="font-medium text-slate-700">
						Confirm new password
					</span>
					<input
						type="password"
						required
						minLength={10}
						autoComplete="new-password"
						className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
						value={confirmPassword}
						onChange={(e) => setConfirmPassword(e.target.value)}
					/>
				</label>
				<button
					type="submit"
					className="btn btn-primary"
					disabled={
						mutation.isPending ||
						!currentPassword ||
						!newPassword ||
						!confirmPassword
					}
				>
					{mutation.isPending ? "Updating…" : "Update password"}
				</button>
			</form>
		</div>
	);
}
