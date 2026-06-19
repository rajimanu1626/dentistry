/**
 * Local helpers for the JWT + active clinic stored in localStorage.
 * No PHI lives here — only opaque tokens + ids.
 */

const ACCESS_KEY = 'cc.access_token';
const CLINIC_KEY = 'cc.clinic_id';
const SYSTEM_ROLE_KEY = 'cc.system_role';

export type SystemRole = 'platform_admin' | 'platform_support';

export const auth = {
  getToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  },
  setToken(token: string): void {
    localStorage.setItem(ACCESS_KEY, token);
  },
  clearToken(): void {
    localStorage.removeItem(ACCESS_KEY);
  },
  clearClinicId(): void {
    localStorage.removeItem(CLINIC_KEY);
  },
  clearSession(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(CLINIC_KEY);
    localStorage.removeItem(SYSTEM_ROLE_KEY);
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
      return;
    }
    localStorage.setItem(SYSTEM_ROLE_KEY, role);
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
  },
  isAuthenticated(): boolean {
    return Boolean(localStorage.getItem(ACCESS_KEY));
  },
  logout(): void {
    this.clearSession();
  },
};
