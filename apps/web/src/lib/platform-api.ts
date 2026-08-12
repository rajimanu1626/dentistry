import { apiClient } from '@/lib/api';

export interface PlatformGroup {
  id: string;
  name: string;
  owner_user_id: string;
  created_at: string;
}

export interface PlatformClinic {
  id: string;
  slug: string;
  name: string;
  group_id: string | null;
  address: string | null;
  created_at: string;
}

export interface PlatformUser {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  system_role: 'platform_admin' | 'platform_support' | null;
  created_at: string;
}

export interface PlatformClinicInviteCreate {
  email: string;
  role: 'owner' | 'dentist' | 'assistant' | 'front_desk' | 'receptionist';
  expires_in_seconds?: number;
}

export interface PlatformInviteCreated {
  invite_id: string;
  email: string;
  role: string;
  invite_token: string;
  expires_at: string;
}

export type UsageStatus = 'ok' | 'warning' | 'over_limit';

export interface ClinicUsageMetrics {
  clinic_id: string;
  clinic_name: string;
  clinic_slug: string;
  media_bytes: number;
  media_count: number;
  patients_count: number;
  visits_count: number;
  prescriptions_count: number;
  members_count: number;
  audit_rows_count: number;
  active_external_shares_count: number;
  db_bytes_estimated: number;
  s3_bytes_reconciled: number | null;
  plan_id: string | null;
  plan_name: string | null;
  included_media_bytes: number | null;
  included_db_bytes: number | null;
  media_usage_pct: number | null;
  db_usage_pct: number | null;
  status: UsageStatus;
}

export interface ClinicUsagePage {
  items: ClinicUsageMetrics[];
  total: number;
  page: number;
  page_size: number;
}

export interface ClinicUsageDetail extends ClinicUsageMetrics {
  media_by_kind: { kind: string; count: number; bytes: number }[];
  usage_events_30d: Record<string, number>;
}

export interface UsagePlan {
  id: string;
  name: string;
  included_media_bytes: number;
  included_db_bytes: number;
  max_members: number | null;
  created_at: string;
  updated_at: string;
}

export interface ClinicPlanAssignment {
  id: string;
  clinic_id: string;
  plan_id: string;
  plan_name: string;
  starts_at: string;
  ends_at: string | null;
  created_at: string;
}

export interface ClinicInfraCost {
  id: string;
  clinic_id: string;
  period_start: string;
  period_end: string;
  cost_paise: number;
  source: string;
  notes: string | null;
  created_at: string;
}

export interface UsageHistoryPoint {
  snapshot_date: string;
  media_bytes: number;
  patients_count: number;
  visits_count: number;
  db_bytes_estimated: number;
}

export interface S3ReconcileResult {
  clinic_id: string;
  db_media_bytes: number;
  s3_bytes: number;
  s3_object_count: number;
  delta_bytes: number;
}

export const platformApi = {
  listGroups: () => apiClient.get<PlatformGroup[]>('/platform/groups'),
  createGroup: (body: { name: string; owner_user_id: string }) =>
    apiClient.post<PlatformGroup>('/platform/groups', body),
  listClinics: () => apiClient.get<PlatformClinic[]>('/platform/clinics'),
  createClinic: (body: {
    name: string;
    slug: string;
    group_id?: string | null;
    address?: string | null;
  }) => apiClient.post<PlatformClinic>('/platform/clinics', body),
  createClinicInvite: (clinicId: string, body: PlatformClinicInviteCreate) =>
    apiClient.post<PlatformInviteCreated>(`/platform/clinics/${clinicId}/invites`, body),
  listUsers: () => apiClient.get<PlatformUser[]>('/platform/users'),
  updateUser: (userId: string, body: { is_active?: boolean; full_name?: string }) =>
    apiClient.patch<PlatformUser>(`/platform/users/${userId}`, body),
  listUsageClinics: (page = 1, pageSize = 50) =>
    apiClient.get<ClinicUsagePage>(`/platform/usage/clinics?page=${page}&page_size=${pageSize}`),
  getUsageClinic: (clinicId: string) =>
    apiClient.get<ClinicUsageDetail>(`/platform/usage/clinics/${clinicId}`),
  getUsageHistory: (clinicId: string, days = 30) =>
    apiClient.get<UsageHistoryPoint[]>(`/platform/usage/clinics/${clinicId}/history?days=${days}`),
  recomputeUsage: () =>
    apiClient.post<{ clinics_processed: number; snapshot_date: string }>(
      '/platform/usage/recompute',
      {},
    ),
  exportUsageCsv: () => apiClient.getBlob('/platform/usage/export'),
  listUsagePlans: () => apiClient.get<UsagePlan[]>('/platform/usage/plans'),
  createUsagePlan: (body: {
    name: string;
    included_media_bytes: number;
    included_db_bytes: number;
    max_members?: number | null;
  }) => apiClient.post<UsagePlan>('/platform/usage/plans', body),
  assignClinicPlan: (clinicId: string, body: { plan_id: string }) =>
    apiClient.post<ClinicPlanAssignment>(`/platform/usage/clinics/${clinicId}/plan`, body),
  reconcileS3: (clinicId: string) =>
    apiClient.post<{
      clinic_id: string;
      db_media_bytes: number;
      s3_bytes: number;
      s3_object_count: number;
      delta_bytes: number;
    }>(`/platform/usage/clinics/${clinicId}/reconcile-s3`, {}),
  listInfraCosts: (clinicId?: string) =>
    apiClient.get<ClinicInfraCost[]>(
      clinicId
        ? `/platform/usage/infra-costs?clinic_id=${clinicId}`
        : '/platform/usage/infra-costs',
    ),
  createInfraCost: (body: {
    clinic_id: string;
    period_start: string;
    period_end: string;
    cost_paise: number;
    source?: string;
    notes?: string | null;
  }) => apiClient.post<ClinicInfraCost>('/platform/usage/infra-costs', body),
};
