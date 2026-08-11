/**
 * Auth API client (login, signup, session).
 */

import { type ApiError, apiClient } from '@/lib/api';
import { auth } from '@/lib/auth';

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
  system_role: 'platform_admin' | 'platform_support' | null;
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
  role: 'dentist' | 'assistant' | 'front_desk' | 'owner';
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
  return apiClient.get<AuthConfig>('/auth/config');
}

export async function login(payload: LoginPayload): Promise<MeResponse> {
  const tokens = await apiClient.post<TokenPair>('/auth/login', payload);
  return applySession(tokens.access_token);
}

export async function signup(payload: SignupPayload): Promise<MeResponse> {
  const tokens = await apiClient.post<TokenPair>('/auth/signup', payload);
  return applySession(tokens.access_token);
}

export async function fetchMe(): Promise<MeResponse> {
  return apiClient.get<MeResponse>('/auth/me');
}

export async function createInvite(payload: InviteCreatePayload): Promise<InviteCreated> {
  return apiClient.post<InviteCreated>('/auth/invites', payload);
}

export async function listInvites(): Promise<InviteRecord[]> {
  return apiClient.get<InviteRecord[]>('/auth/invites');
}

export async function revokeInvite(inviteId: string): Promise<void> {
  await apiClient.delete<void>(`/auth/invites/${inviteId}`);
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiClient.post<void>('/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

export async function applySession(accessToken: string): Promise<MeResponse> {
  auth.setToken(accessToken);
  auth.clearClinicId();
  const me = await fetchMe();
  auth.setSystemRole(me.system_role ?? null);
  if (me.memberships.length > 0) {
    auth.setClinicId(me.memberships[0].clinic_id);
  }
  return me;
}

export function defaultHomePath(me: MeResponse): string {
  if (me.system_role && me.memberships.length === 0) {
    return '/platform';
  }
  return '/';
}

export function logout(): void {
  auth.clearSession();
}

export type { ApiError };
