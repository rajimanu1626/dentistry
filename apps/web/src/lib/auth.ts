/**
 * Local helpers for the JWT + active clinic stored in localStorage.
 * No PHI lives here — only opaque tokens + ids.
 *
 * Mutations notify subscribers so React re-renders (navbar, guards) without a
 * full page refresh.
 */

import { useSyncExternalStore } from 'react';

const ACCESS_KEY = 'cc.access_token';
const CLINIC_KEY = 'cc.clinic_id';
const SYSTEM_ROLE_KEY = 'cc.system_role';

export type SystemRole = 'platform_admin' | 'platform_support';

type AuthSnapshot = {
  token: string | null;
  clinicId: string | null;
  systemRole: SystemRole | null;
};

const listeners = new Set<() => void>();
let snapshot: AuthSnapshot = readSnapshot();

function readSnapshot(): AuthSnapshot {
  const rawRole = localStorage.getItem(SYSTEM_ROLE_KEY);
  const systemRole =
    rawRole === 'platform_admin' || rawRole === 'platform_support' ? rawRole : null;
  return {
    token: localStorage.getItem(ACCESS_KEY),
    clinicId: localStorage.getItem(CLINIC_KEY),
    systemRole,
  };
}

function emit(): void {
  snapshot = readSnapshot();
  for (const listener of listeners) {
    listener();
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): AuthSnapshot {
  return snapshot;
}

function getServerSnapshot(): AuthSnapshot {
  return { token: null, clinicId: null, systemRole: null };
}

export const auth = {
  getToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },
  setToken(token: string): void {
    localStorage.setItem(ACCESS_KEY, token);
    emit();
  },
  clearToken(): void {
    localStorage.removeItem(ACCESS_KEY);
    emit();
  },
  clearClinicId(): void {
    localStorage.removeItem(CLINIC_KEY);
    emit();
  },
  clearSession(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(CLINIC_KEY);
    localStorage.removeItem(SYSTEM_ROLE_KEY);
    emit();
  },
  getSystemRole(): SystemRole | null {
    const raw = localStorage.getItem(SYSTEM_ROLE_KEY);
    if (raw === 'platform_admin' || raw === 'platform_support') {
      return raw;
    }
    return null;
  },
  setSystemRole(role: SystemRole | null): void {
    if (!role) {
      localStorage.removeItem(SYSTEM_ROLE_KEY);
    } else {
      localStorage.setItem(SYSTEM_ROLE_KEY, role);
    }
    emit();
  },
  isPlatformOperator(): boolean {
    return this.getSystemRole() !== null;
  },
  isPlatformAdmin(): boolean {
    return this.getSystemRole() === 'platform_admin';
  },
  getClinicId(): string | null {
    return localStorage.getItem(CLINIC_KEY);
  },
  setClinicId(id: string): void {
    localStorage.setItem(CLINIC_KEY, id);
    emit();
  },
  isAuthenticated(): boolean {
    return Boolean(localStorage.getItem(ACCESS_KEY));
  },
  logout(): void {
    this.clearSession();
  },
  subscribe,
  getSnapshot,
  getServerSnapshot,
};

/** Reactive auth state for components (navbar, etc.). */
export function useAuth(): AuthSnapshot & {
  isAuthenticated: boolean;
  isPlatformOperator: boolean;
  isPlatformAdmin: boolean;
} {
  const state = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  return {
    ...state,
    isAuthenticated: Boolean(state.token),
    isPlatformOperator: state.systemRole !== null,
    isPlatformAdmin: state.systemRole === 'platform_admin',
  };
}
