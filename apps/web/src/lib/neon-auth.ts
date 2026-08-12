/**
 * Neon Auth (Managed Better Auth) client for SPA login/signup.
 *
 * Production uses a same-origin `/neon-auth` proxy (Cloudflare Pages Function)
 * so Safari can store the session cookie as first-party. Direct neonauth.*
 * URLs break under ITP.
 */

import { createAuthClient } from "@neondatabase/neon-js/auth";

/** Better Auth vanilla client surface we actually call. */
type NeonBetterAuthClient = {
	token: () => Promise<{ data?: { token?: string } | null; error?: unknown }>;
	getSession: (opts?: {
		fetchOptions?: { onSuccess?: (ctx: { response: Response }) => void };
	}) => Promise<{
		data?: {
			session?: { token?: string } | null;
		} | null;
		error?: unknown;
	}>;
	signIn: {
		email: (args: {
			email: string;
			password: string;
			fetchOptions?: { onSuccess?: (ctx: { response: Response }) => void };
		}) => Promise<{ data?: unknown; error?: unknown }>;
	};
	signUp: {
		email: (args: {
			name: string;
			email: string;
			password: string;
			fetchOptions?: { onSuccess?: (ctx: { response: Response }) => void };
		}) => Promise<{ data?: unknown; error?: unknown }>;
	};
	signOut: () => Promise<unknown>;
	changePassword: (args: {
		currentPassword: string;
		newPassword: string;
		revokeOtherSessions?: boolean;
	}) => Promise<{ data?: unknown; error?: unknown }>;
};

function resolveNeonAuthUrl(): string | undefined {
	const raw = import.meta.env.VITE_NEON_AUTH_URL as string | undefined;
	if (!raw) return undefined;
	if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
	const path = raw.startsWith("/") ? raw : `/${raw}`;
	if (typeof window !== "undefined") {
		return `${window.location.origin}${path}`;
	}
	return path;
}

export const isNeonAuthEnabled = Boolean(
	import.meta.env.VITE_NEON_AUTH_URL as string | undefined,
);

let _client: NeonBetterAuthClient | null | undefined;

function getAuthClient(): NeonBetterAuthClient | null {
	if (_client !== undefined) return _client;
	const url = resolveNeonAuthUrl();
	if (!url) {
		_client = null;
		return null;
	}
	_client = createAuthClient(url, {
		fetchOptions: { credentials: "include" },
	} as { allowAnonymous?: boolean }) as unknown as NeonBetterAuthClient;
	return _client;
}

export function requireNeonAuthClient(): NeonBetterAuthClient {
	const client = getAuthClient();
	if (!client) {
		throw new Error(
			"Neon Auth is not configured. Set VITE_NEON_AUTH_URL for this build.",
		);
	}
	return client;
}

function b64UrlToJson(segment: string): Record<string, unknown> | null {
	try {
		const padded = segment.replace(/-/g, "+").replace(/_/g, "/");
		const pad =
			padded.length % 4 === 0 ? "" : "=".repeat(4 - (padded.length % 4));
		return JSON.parse(atob(padded + pad)) as Record<string, unknown>;
	} catch {
		return null;
	}
}

/** True when the string is a JWKS-verifiable JWT (not a Better Auth session id). */
export function isJwksAccessToken(token: string | null | undefined): boolean {
	if (!token) return false;
	const parts = token.split(".");
	if (parts.length !== 3 || !parts[0]) return false;
	const header = b64UrlToJson(parts[0]);
	if (!header) return false;
	const alg = header.alg;
	return alg === "EdDSA" || alg === "RS256" || alg === "ES256";
}

function captureJwtOnSuccess(store: { jwt: string | null }) {
	return {
		onSuccess: (ctx: { response: Response }) => {
			const header = ctx.response.headers.get("set-auth-jwt");
			if (header && isJwksAccessToken(header)) {
				store.jwt = header;
			}
		},
	};
}

/** Fetch a short-lived JWT for Authorization: Bearer. */
export async function fetchNeonAccessToken(): Promise<string> {
	const client = requireNeonAuthClient();

	const { data, error } = await client.token();
	const tokenFromEndpoint = data?.token;
	if (!error && isJwksAccessToken(tokenFromEndpoint)) {
		return tokenFromEndpoint as string;
	}

	const captured = { jwt: null as string | null };
	const sessionResult = await client.getSession({
		fetchOptions: captureJwtOnSuccess(captured),
	});

	if (captured.jwt && isJwksAccessToken(captured.jwt)) {
		return captured.jwt;
	}

	const sessionToken = sessionResult.data?.session?.token;
	if (typeof sessionToken === "string" && isJwksAccessToken(sessionToken)) {
		return sessionToken;
	}

	if (error) {
		throw new Error(
			error instanceof Error
				? error.message
				: "Failed to obtain Neon Auth token.",
		);
	}
	throw new Error(
		"Neon Auth did not return a JWT. Sign out, hard-refresh, and sign in again.",
	);
}

/** Sign in and return a JWKS JWT (captures set-auth-jwt when present). */
export async function neonSignIn(
	email: string,
	password: string,
): Promise<string> {
	const client = requireNeonAuthClient();
	const captured = { jwt: null as string | null };
	const result = await client.signIn.email({
		email,
		password,
		fetchOptions: captureJwtOnSuccess(captured),
	});
	if (result.error) {
		throw Object.assign(new Error(neonAuthErrorMessage(result.error)), {
			status: 401,
			code: "unauthorized",
		});
	}
	if (captured.jwt) return captured.jwt;
	return fetchNeonAccessToken();
}

/** Sign up and return a JWKS JWT. */
export async function neonSignUp(input: {
	email: string;
	password: string;
	name: string;
}): Promise<string> {
	const client = requireNeonAuthClient();
	const captured = { jwt: null as string | null };
	const result = await client.signUp.email({
		name: input.name,
		email: input.email,
		password: input.password,
		fetchOptions: captureJwtOnSuccess(captured),
	});
	if (result.error) {
		throw Object.assign(new Error(neonAuthErrorMessage(result.error)), {
			status: 400,
			code: "signup_failed",
		});
	}
	if (captured.jwt) return captured.jwt;
	return fetchNeonAccessToken();
}

export function neonAuthErrorMessage(error: unknown): string {
	if (error && typeof error === "object" && "message" in error) {
		const msg = (error as { message?: unknown }).message;
		if (typeof msg === "string" && msg.trim()) return msg;
	}
	if (error instanceof Error && error.message) return error.message;
	return "Authentication failed.";
}
