/**
 * Single seam for all backend HTTP calls. No fetch/axios usage outside this file
 * (enforced by .cursor/rules/web-conventions.mdc).
 */

import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios';

import { auth } from '@/lib/auth';

// In local dev, always go through Vite's /api proxy so browser-side requests
// don't depend on host/container localhost semantics.
const baseURL = import.meta.env.DEV ? '/api' : (import.meta.env.VITE_API_BASE_URL ?? '/api');

const axiosInstance: AxiosInstance = axios.create({
  baseURL,
  timeout: 15_000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

axiosInstance.interceptors.request.use((config) => {
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    // Let the browser set multipart boundary automatically.
    config.headers['Content-Type'] = undefined;
  }
  const token = localStorage.getItem('cc.access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const clinic = localStorage.getItem('cc.clinic_id');
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
};
