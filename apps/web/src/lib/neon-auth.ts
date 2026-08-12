/**
 * Neon Auth (Managed Better Auth) client for SPA login/signup.
 *
 * Production uses a same-origin `/neon-auth` proxy (Cloudflare Pages Function)
 * so Safari can store the session cookie as first-party. Direct neonauth.*
 * URLs break under ITP.
 */

import { createAuthClient } from '@neondatabase/neon-js/auth';

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

function captureJwtOnSuccess(store: { jwt: string | null }) {
  return {
    onSuccess: (ctx: { response: Response }) => {
      const header = ctx.response.headers.get('set-auth-jwt');
      if (header && isJwksAccessToken(header)) {
        store.jwt = header;
      }
    },
  };
}

/**
 * Neon Managed Auth allows GET /get-session only. Newer Better Auth clients may
 * POST /get-session when `needsRefresh` is set, which returns HTTP 405
 * (`METHOD_NOT_ALLOWED_DEFER_SESSION_REQUIRED`). Prefer plain GET fetches for JWTs.
 */
async function fetchJwtViaGet(): Promise<string | null> {
  const base = resolveNeonAuthUrl();
  if (!base) return null;

  const tokenRes = await fetch(`${base}/token`, {
    method: 'GET',
    credentials: 'include',
  });
  if (tokenRes.ok) {
    const body = (await tokenRes.json().catch(() => null)) as { token?: string } | null;
    const token = body?.token;
    if (typeof token === 'string' && isJwksAccessToken(token)) {
      return token;
    }
  }

  const sessionRes = await fetch(`${base}/get-session`, {
    method: 'GET',
    credentials: 'include',
  });
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
  // Always try GET first — avoids the Better Auth POST /get-session → 405 trap.
  const viaGet = await fetchJwtViaGet();
  if (viaGet) return viaGet;

  // Fallback through the SDK (may throw AuthApiError on non-2xx).
  try {
    const client = requireNeonAuthClient();
    const { data, error } = await client.token();
    const token = data?.token;
    if (!error && typeof token === 'string' && isJwksAccessToken(token)) {
      return token;
    }
    if (error) {
      throw new Error(error instanceof Error ? error.message : 'Failed to obtain Neon Auth token.');
    }
  } catch (err) {
    const msg = neonAuthErrorMessage(err);
    if (/405|METHOD_NOT_ALLOWED/i.test(msg)) {
      throw new Error(
        'Neon Auth session refresh failed (HTTP 405). Hard-refresh and sign in again.',
      );
    }
    throw err instanceof Error ? err : new Error(msg);
  }

  throw new Error('Neon Auth did not return a JWT. Sign out, hard-refresh, and sign in again.');
}

/** Sign in and return a JWKS JWT (captures set-auth-jwt when present). */
export async function neonSignIn(email: string, password: string): Promise<string> {
  const client = requireNeonAuthClient();
  const captured = { jwt: null as string | null };
  try {
    const result = await client.signIn.email({
      email,
      password,
      fetchOptions: captureJwtOnSuccess(captured),
    });
    if (result.error) {
      throw Object.assign(new Error(neonAuthErrorMessage(result.error)), {
        status: 401,
        code: 'unauthorized',
      });
    }
  } catch (err) {
    if (err && typeof err === 'object' && 'status' in err && 'code' in err) {
      throw Object.assign(new Error(neonAuthErrorMessage(err)), {
        status: (err as { status?: number }).status ?? 401,
        code: (err as { code?: string }).code ?? 'unauthorized',
      });
    }
    throw Object.assign(new Error(neonAuthErrorMessage(err)), {
      status: 401,
      code: 'unauthorized',
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
  try {
    const result = await client.signUp.email({
      name: input.name,
      email: input.email,
      password: input.password,
      fetchOptions: captureJwtOnSuccess(captured),
    });
    if (result.error) {
      throw Object.assign(new Error(neonAuthErrorMessage(result.error)), {
        status: 400,
        code: 'signup_failed',
      });
    }
  } catch (err) {
    if (err && typeof err === 'object' && 'code' in err) {
      throw Object.assign(new Error(neonAuthErrorMessage(err)), {
        status: (err as { status?: number }).status ?? 400,
        code: (err as { code?: string }).code ?? 'signup_failed',
      });
    }
    throw Object.assign(new Error(neonAuthErrorMessage(err)), {
      status: 400,
      code: 'signup_failed',
    });
  }
  if (captured.jwt) return captured.jwt;
  return fetchNeonAccessToken();
}

export function neonAuthErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    const msg = (error as { message?: unknown }).message;
    if (typeof msg === 'string' && msg.trim()) {
      if (/405|METHOD_NOT_ALLOWED_DEFER/i.test(msg)) {
        return 'Sign-in hit a Neon Auth session refresh error. Please hard-refresh and try again.';
      }
      return msg;
    }
  }
  if (error instanceof Error && error.message) return error.message;
  return 'Authentication failed.';
}
