/**
 * Neon Auth (Managed Better Auth) client for SPA login/signup.
 *
 * Production uses a same-origin `/neon-auth` proxy (Cloudflare Pages Function)
 * so Safari can store the session cookie as first-party. Direct neonauth.*
 * URLs break under ITP.
 *
 * We use plain `fetch` for sign-in/out and JWT retrieval. The @neondatabase/auth
 * SDK triggers POST /get-session after sign-in, which Neon Managed Auth rejects
 * with HTTP 405 unless deferSessionRefresh is enabled server-side.
 */

import { createAuthClient } from '@neondatabase/neon-js/auth';

/** Better Auth vanilla client surface for password change only. */
type NeonBetterAuthClient = {
  changePassword: (args: {
    currentPassword: string;
    newPassword: string;
    revokeOtherSessions?: boolean;
  }) => Promise<{ data?: unknown; error?: unknown }>;
};

function resolveNeonAuthUrl(): string | undefined {
  const raw = import.meta.env.VITE_NEON_AUTH_URL as string | undefined;
  if (!raw) return undefined;
  if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
  const path = raw.startsWith('/') ? raw : `/${raw}`;
  if (typeof window !== 'undefined') {
    return `${window.location.origin}${path}`;
  }
  return path;
}

export const isNeonAuthEnabled = Boolean(import.meta.env.VITE_NEON_AUTH_URL as string | undefined);

let _client: NeonBetterAuthClient | null | undefined;

function getAuthClient(): NeonBetterAuthClient | null {
  if (_client !== undefined) return _client;
  const url = resolveNeonAuthUrl();
  if (!url) {
    _client = null;
    return null;
  }
  _client = createAuthClient(url, {
    fetchOptions: { credentials: 'include' },
  } as { allowAnonymous?: boolean }) as unknown as NeonBetterAuthClient;
  return _client;
}

export function requireNeonAuthClient(): NeonBetterAuthClient {
  const client = getAuthClient();
  if (!client) {
    throw new Error('Neon Auth is not configured. Set VITE_NEON_AUTH_URL for this build.');
  }
  return client;
}

function neonAuthBaseUrl(): string {
  const base = resolveNeonAuthUrl();
  if (!base) {
    throw new Error('Neon Auth is not configured. Set VITE_NEON_AUTH_URL for this build.');
  }
  return base;
}

async function neonAuthFetch(path: string, init?: RequestInit): Promise<Response> {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return fetch(`${neonAuthBaseUrl()}${normalized}`, {
    credentials: 'include',
    ...init,
  });
}

function b64UrlToJson(segment: string): Record<string, unknown> | null {
  try {
    const padded = segment.replace(/-/g, '+').replace(/_/g, '/');
    const pad = padded.length % 4 === 0 ? '' : '='.repeat(4 - (padded.length % 4));
    return JSON.parse(atob(padded + pad)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/** True when the string is a JWKS-verifiable JWT (not a Better Auth session id). */
export function isJwksAccessToken(token: string | null | undefined): boolean {
  if (!token) return false;
  const parts = token.split('.');
  if (parts.length !== 3 || !parts[0]) return false;
  const header = b64UrlToJson(parts[0]);
  if (!header) return false;
  const alg = header.alg;
  return alg === 'EdDSA' || alg === 'RS256' || alg === 'ES256';
}

async function readAuthError(res: Response): Promise<{ message: string; code: string }> {
  const body = (await res.json().catch(() => null)) as { message?: string; code?: string } | null;
  return {
    message: body?.message?.trim() || `Authentication failed (HTTP ${res.status}).`,
    code: body?.code ?? 'unauthorized',
  };
}

/** Fetch a JWKS JWT using GET /token then GET /get-session (never POST). */
async function fetchJwtViaGet(): Promise<string | null> {
  const tokenRes = await neonAuthFetch('/token', { method: 'GET' });
  if (tokenRes.ok) {
    const body = (await tokenRes.json().catch(() => null)) as { token?: string } | null;
    const token = body?.token;
    if (typeof token === 'string' && isJwksAccessToken(token)) {
      return token;
    }
  }

  const sessionRes = await neonAuthFetch('/get-session', { method: 'GET' });
  if (sessionRes.ok) {
    const header = sessionRes.headers.get('set-auth-jwt');
    if (typeof header === 'string' && isJwksAccessToken(header)) {
      return header;
    }
    const body = (await sessionRes.json().catch(() => null)) as {
      session?: { token?: string } | null;
    } | null;
    const sessionToken = body?.session?.token;
    if (typeof sessionToken === 'string' && isJwksAccessToken(sessionToken)) {
      return sessionToken;
    }
  }

  return null;
}

/** Fetch a short-lived JWT for Authorization: Bearer. */
export async function fetchNeonAccessToken(): Promise<string> {
  const viaGet = await fetchJwtViaGet();
  if (viaGet) return viaGet;
  throw new Error('Neon Auth did not return a JWT. Sign out, hard-refresh, and sign in again.');
}

/** Sign in and return a JWKS JWT. Uses fetch only — no SDK session refresh. */
export async function neonSignIn(email: string, password: string): Promise<string> {
  const res = await neonAuthFetch('/sign-in/email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  const headerJwt = res.headers.get('set-auth-jwt');
  if (typeof headerJwt === 'string' && isJwksAccessToken(headerJwt)) {
    return headerJwt;
  }

  if (!res.ok) {
    const { message, code } = await readAuthError(res);
    throw Object.assign(new Error(message), {
      status: res.status === 401 ? 401 : res.status,
      code,
    });
  }

  const jwt = await fetchJwtViaGet();
  if (jwt) return jwt;

  throw new Error('Sign-in succeeded but Neon Auth did not return a JWT. Try again.');
}

/** Sign up and return a JWKS JWT. Uses fetch only — no SDK session refresh. */
export async function neonSignUp(input: {
  email: string;
  password: string;
  name: string;
}): Promise<string> {
  const res = await neonAuthFetch('/sign-up/email', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: input.email,
      password: input.password,
      name: input.name,
    }),
  });

  const headerJwt = res.headers.get('set-auth-jwt');
  if (typeof headerJwt === 'string' && isJwksAccessToken(headerJwt)) {
    return headerJwt;
  }

  if (!res.ok) {
    const { message, code } = await readAuthError(res);
    throw Object.assign(new Error(message), {
      status: res.status === 400 ? 400 : res.status,
      code: code === 'unauthorized' ? 'signup_failed' : code,
    });
  }

  const jwt = await fetchJwtViaGet();
  if (jwt) return jwt;

  throw new Error('Sign-up succeeded but Neon Auth did not return a JWT. Try signing in.');
}

/** Sign out of Neon Auth (fetch only). */
export async function neonSignOut(): Promise<void> {
  await neonAuthFetch('/sign-out', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  }).catch(() => {
    // Best-effort; local session is cleared either way.
  });
}

export function neonAuthErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    const msg = (error as { message?: unknown }).message;
    if (typeof msg === 'string' && msg.trim()) return msg;
  }
  if (error instanceof Error && error.message) return error.message;
  return 'Authentication failed.';
}
