/**
 * Local helpers for the JWT + active clinic stored in localStorage.
 * No PHI lives here — only opaque tokens + ids.
 */

const ACCESS_KEY = 'cc.access_token';
const CLINIC_KEY = 'cc.clinic_id';
const SYSTEM_ROLE_KEY = 'cc.system_role';

export type SystemRole = 'platform_admin' | 'platform_support';

// --- Reactive store plumbing ------------------------------------------------
// `auth` is backed by localStorage, which React cannot observe on its own.
// We expose a tiny subscribe/snapshot pair so components can re-render via
// `useSyncExternalStore` whenever the session changes (login, logout, clinic
// switch) — including changes made in another browser tab.
const listeners = new Set<() => void>();
let version = 0;

function notifyAuthChange(): void {
  version += 1;
  for (const listener of listeners) {
    listener();
  }
}

export function subscribeAuth(listener: () => void): () => void {
  listeners.add(listener);
  const onStorage = (event: StorageEvent) => {
    if (
      event.key === null ||
      event.key === ACCESS_KEY ||
      event.key === CLINIC_KEY ||
      event.key === SYSTEM_ROLE_KEY
    ) {
      notifyAuthChange();
    }
  };
  window.addEventListener('storage', onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener('storage', onStorage);
  };
}

export function getAuthVersion(): number {
  return version;
}

export const auth = {
  getToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },
  setToken(token: string): void {
    localStorage.setItem(ACCESS_KEY, token);
    notifyAuthChange();
  },
  clearToken(): void {
    localStorage.removeItem(ACCESS_KEY);
    notifyAuthChange();
  },
  clearClinicId(): void {
    localStorage.removeItem(CLINIC_KEY);
    notifyAuthChange();
  },
  clearSession(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(CLINIC_KEY);
    localStorage.removeItem(SYSTEM_ROLE_KEY);
    notifyAuthChange();
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
      notifyAuthChange();
      return;
    }
    localStorage.setItem(SYSTEM_ROLE_KEY, role);
    notifyAuthChange();
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
    notifyAuthChange();
  },
  isAuthenticated(): boolean {
    return Boolean(localStorage.getItem(ACCESS_KEY));
  },
  logout(): void {
    this.clearSession();
  },
};
