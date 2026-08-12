/**
 * Single seam for all backend HTTP calls. No fetch/axios usage outside this file
 * (enforced by .cursor/rules/web-conventions.mdc).
 */

import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios';

import { auth } from '@/lib/auth';
import { fetchNeonAccessToken, isJwksAccessToken, isNeonAuthEnabled } from '@/lib/neon-auth';

// In local dev, always go through Vite's /api proxy so browser-side requests
// don't depend on host/container localhost semantics.
const baseURL = import.meta.env.DEV ? '/api' : (import.meta.env.VITE_API_BASE_URL ?? '/api');

const axiosInstance: AxiosInstance = axios.create({
  baseURL,
  timeout: 15_000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

let refreshInFlight: Promise<string | null> | null = null;

function jwtStillFresh(token: string, skewSeconds = 60): boolean {
  try {
    const parts = token.split('.');
    if (parts.length < 2 || !parts[1]) return false;
    const padded = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const pad = padded.length % 4 === 0 ? '' : '='.repeat(4 - (padded.length % 4));
    const payload = JSON.parse(atob(padded + pad)) as { exp?: number };
    return typeof payload.exp === 'number' && payload.exp * 1000 > Date.now() + skewSeconds * 1000;
  } catch {
    return false;
  }
}

async function resolveAccessToken(): Promise<string | null> {
  const existing = auth.getToken();
  if (!isNeonAuthEnabled) {
    return existing;
  }

  // Drop leftover local HS256 / opaque session tokens from before Neon Auth.
  if (existing && !isJwksAccessToken(existing)) {
    auth.clearToken();
  }

  const current = auth.getToken();
  if (current && isJwksAccessToken(current) && jwtStillFresh(current)) {
    return current;
  }

  // Only refresh when we already had a token (signed-in) or Neon session may exist.
  // Avoid calling /token on anonymous /auth/config requests.
  if (!current && !existing) {
    return null;
  }

  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const token = await fetchNeonAccessToken();
        auth.setToken(token);
        return token;
      } catch {
        auth.clearToken();
        return null;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

axiosInstance.interceptors.request.use(async (config) => {
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    // Let the browser set multipart boundary automatically.
    config.headers['Content-Type'] = undefined;
  }
  const token = await resolveAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const clinic = auth.getClinicId();
  if (clinic) {
    config.headers['X-Clinic-Id'] = clinic;
  }
  return config;
});

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      auth.clearSession();
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        const redirect = `${window.location.pathname}${window.location.search}`;
        window.location.assign(`/login?redirect=${encodeURIComponent(redirect)}`);
      }
    }
    return Promise.reject(error);
  },
);

export interface ApiError extends Error {
  status: number;
  code: string;
  details?: Record<string, unknown>;
}

function normalize(error: unknown): never {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | {
          error?: {
            code?: string;
            message?: string;
            details?: Record<string, unknown>;
          };
        }
      | undefined;
    let message = data?.error?.message ?? error.message;
    const details = data?.error?.details as
      | { errors?: Array<{ loc?: unknown[]; msg?: string }> }
      | undefined;
    if (details?.errors?.length) {
      const hint = details.errors
        .map((item) => {
          const field = item.loc?.slice(-1)[0];
          return field ? `${String(field)}: ${item.msg ?? 'invalid'}` : item.msg;
        })
        .filter(Boolean)
        .join('; ');
      if (hint) {
        message = `${message} (${hint})`;
      }
    }
    const err = new Error(message) as ApiError;
    err.status = error.response?.status ?? 0;
    err.code = data?.error?.code ?? 'network_error';
    if (data?.error?.details) {
      err.details = data.error.details as Record<string, unknown>;
    }
    throw err;
  }
  throw error;
}

export const apiClient = {
  get: async <T>(path: string, config?: AxiosRequestConfig): Promise<T> => {
    try {
      const { data } = await axiosInstance.get<T>(path, config);
      return data;
    } catch (e) {
      normalize(e);
    }
  },
  post: async <T>(path: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    try {
      const { data } = await axiosInstance.post<T>(path, body, config);
      return data;
    } catch (e) {
      normalize(e);
    }
  },
  put: async <T>(path: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    try {
      const { data } = await axiosInstance.put<T>(path, body, config);
      return data;
    } catch (e) {
      normalize(e);
    }
  },
  patch: async <T>(path: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    try {
      const { data } = await axiosInstance.patch<T>(path, body, config);
      return data;
    } catch (e) {
      normalize(e);
    }
  },
  delete: async <T>(path: string, config?: AxiosRequestConfig): Promise<T> => {
    try {
      const { data } = await axiosInstance.delete<T>(path, config);
      return data;
    } catch (e) {
      normalize(e);
    }
  },
  /** Authenticated binary download (PDFs, etc.). */
  getBlob: async (path: string, config?: AxiosRequestConfig): Promise<Blob> => {
    try {
      const { data } = await axiosInstance.get<Blob>(path, {
        ...config,
        responseType: 'blob',
        timeout: config?.timeout ?? 60_000,
      });
      if (data.type === 'application/json') {
        const text = await data.text();
        try {
          const parsed = JSON.parse(text) as {
            error?: { message?: string; code?: string };
          };
          const err = new Error(parsed.error?.message ?? 'Request failed.') as ApiError;
          err.status = 400;
          err.code = parsed.error?.code ?? 'request_failed';
          throw err;
        } catch (inner) {
          if (inner && typeof inner === 'object' && 'status' in inner) {
            throw inner;
          }
          throw new Error('Request failed.');
        }
      }
      return data;
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.data instanceof Blob) {
        try {
          const text = await e.response.data.text();
          const parsed = JSON.parse(text) as {
            error?: { message?: string; code?: string };
          };
          const err = new Error(parsed.error?.message ?? e.message) as ApiError;
          err.status = e.response.status;
          err.code = parsed.error?.code ?? 'request_failed';
          throw err;
        } catch (inner) {
          if (inner && typeof inner === 'object' && 'status' in inner) {
            throw inner;
          }
        }
      }
      normalize(e);
    }
  },
};
