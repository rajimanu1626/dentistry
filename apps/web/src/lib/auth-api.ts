/**
 * Auth API client (login, signup, session).
 *
 * When `VITE_NEON_AUTH_URL` is set, credentials go through Neon Auth and our
 * API only receives Bearer JWTs + clinic bootstrap/invite completion.
 */

import { type ApiError, apiClient } from "@/lib/api";
import { auth } from "@/lib/auth";
import {
	isNeonAuthEnabled,
	neonAuthErrorMessage,
	neonSignIn,
	neonSignUp,
	requireNeonAuthClient,
} from "@/lib/neon-auth";
import type { ClinicRole } from "@/lib/roles";

export interface TokenPair {
	access_token: string;
	refresh_token: string;
	token_type: string;
	expires_in: number;
}

export interface AuthConfig {
	signup_mode: string;
	can_signup: boolean;
	can_bootstrap_clinic: boolean;
	requires_invite: boolean;
	identity_provider: string;
}

export interface ClinicMembership {
	clinic_id: string;
	clinic_slug: string;
	clinic_name: string;
	role: string;
}

export interface MeResponse {
	user: { id: string; email: string; full_name: string | null };
	memberships: ClinicMembership[];
	system_role: "platform_admin" | "platform_support" | null;
}

export interface SignupPayload {
	email: string;
	password: string;
	full_name: string;
	invite_token?: string;
	clinic_name?: string;
	clinic_slug?: string;
}

export interface LoginPayload {
	email: string;
	password: string;
}

export interface InviteCreatePayload {
	email: string;
	role: ClinicRole;
	expires_in_seconds?: number;
}

export interface InviteCreated {
	invite_id: string;
	email: string;
	role: string;
	invite_token: string;
	expires_at: string;
}

export interface InviteRecord {
	invite_id: string;
	email: string;
	role: string;
	expires_at: string;
	accepted_at: string | null;
	revoked_at: string | null;
	created_at: string;
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
	return apiClient.get<AuthConfig>("/auth/config");
}

async function postWithRetry<T>(
	path: string,
	body: unknown,
	attempts = 2,
): Promise<T> {
	let lastError: unknown;
	for (let i = 0; i < attempts; i += 1) {
		try {
			return await apiClient.post<T>(path, body);
		} catch (err) {
			lastError = err;
			if (i === attempts - 1) break;
			await new Promise((r) => setTimeout(r, 400 * (i + 1)));
		}
	}
	throw lastError;
}

export async function login(payload: LoginPayload): Promise<MeResponse> {
	if (isNeonAuthEnabled) {
		auth.clearSession();
		try {
			const token = await neonSignIn(payload.email, payload.password);
			return applySession(token);
		} catch (err) {
			if (err && typeof err === "object" && "status" in err) {
				throw err;
			}
			throw Object.assign(
				new Error(neonAuthErrorMessage(err)),
				{ status: 401, code: "unauthorized" },
			) as ApiError;
		}
	}

	const tokens = await apiClient.post<TokenPair>("/auth/login", payload);
	return applySession(tokens.access_token);
}

export async function signup(payload: SignupPayload): Promise<MeResponse> {
	if (isNeonAuthEnabled) {
		auth.clearSession();
		let token: string;
		try {
			token = await neonSignUp({
				email: payload.email,
				password: payload.password,
				name: payload.full_name,
			});
		} catch (err) {
			// Neon account may already exist from a prior half-finished invite signup.
			const msg = neonAuthErrorMessage(err).toLowerCase();
			const alreadyExists =
				msg.includes("already") ||
				msg.includes("exist") ||
				msg.includes("registered");
			if (
				alreadyExists &&
				(payload.invite_token ||
					(payload.clinic_name && payload.clinic_slug))
			) {
				try {
					token = await neonSignIn(payload.email, payload.password);
				} catch {
					if (err && typeof err === "object" && "status" in err) {
						throw err;
					}
					throw Object.assign(new Error(neonAuthErrorMessage(err)), {
						status: 400,
						code: "signup_failed",
					}) as ApiError;
				}
			} else if (err && typeof err === "object" && "status" in err) {
				throw err;
			} else {
				throw Object.assign(new Error(neonAuthErrorMessage(err)), {
					status: 400,
					code: "signup_failed",
				}) as ApiError;
			}
		}
		auth.setToken(token);
		auth.clearClinicId();

		if (payload.invite_token) {
			const me = await postWithRetry<MeResponse>("/auth/accept-invite", {
				invite_token: payload.invite_token,
				full_name: payload.full_name,
			});
			return finalizeMe(me);
		}

		if (payload.clinic_name && payload.clinic_slug) {
			const me = await postWithRetry<MeResponse>("/auth/bootstrap-clinic", {
				clinic_name: payload.clinic_name,
				clinic_slug: payload.clinic_slug,
				full_name: payload.full_name,
			});
			return finalizeMe(me);
		}

		return applySession(token);
	}

	const tokens = await apiClient.post<TokenPair>("/auth/signup", payload);
	return applySession(tokens.access_token);
}

export async function fetchMe(): Promise<MeResponse> {
	return apiClient.get<MeResponse>("/auth/me");
}

export async function createInvite(
	payload: InviteCreatePayload,
): Promise<InviteCreated> {
	return apiClient.post<InviteCreated>("/auth/invites", payload);
}

export async function listInvites(): Promise<InviteRecord[]> {
	return apiClient.get<InviteRecord[]>("/auth/invites");
}

export async function revokeInvite(inviteId: string): Promise<void> {
	await apiClient.delete<void>(`/auth/invites/${inviteId}`);
}

export async function leaveClinic(): Promise<MeResponse> {
	const me = await apiClient.delete<MeResponse>("/auth/memberships/me");
	return finalizeMe(me);
}

export async function updateProfile(fullName: string): Promise<MeResponse> {
	const me = await apiClient.patch<MeResponse>("/auth/me", {
		full_name: fullName,
	});
	return finalizeMe(me);
}

export async function changePassword(
	currentPassword: string,
	newPassword: string,
): Promise<void> {
	if (isNeonAuthEnabled) {
		const { error } = await requireNeonAuthClient().changePassword({
			currentPassword,
			newPassword,
			revokeOtherSessions: true,
		});
		if (error) {
			throw Object.assign(new Error(neonAuthErrorMessage(error)), {
				status: 400,
				code: "change_password_failed",
			}) as ApiError;
		}
		return;
	}

	await apiClient.post<void>("/auth/change-password", {
		current_password: currentPassword,
		new_password: newPassword,
	});
}

function finalizeMe(me: MeResponse): MeResponse {
	auth.setSystemRole(me.system_role ?? null);
	if (me.memberships.length > 0) {
		auth.setClinicId(me.memberships[0].clinic_id);
	} else {
		auth.clearClinicId();
	}
	return me;
}

export async function applySession(accessToken: string): Promise<MeResponse> {
	auth.setToken(accessToken);
	auth.clearClinicId();
	const me = await fetchMe();
	return finalizeMe(me);
}

export function defaultHomePath(me: MeResponse): string {
	if (me.system_role && me.memberships.length === 0) {
		return "/platform";
	}
	return "/";
}

export async function logout(): Promise<void> {
	if (isNeonAuthEnabled) {
		try {
			await requireNeonAuthClient().signOut();
		} catch {
			// still clear local session
		}
	}
	auth.clearSession();
}

export type { ApiError };
