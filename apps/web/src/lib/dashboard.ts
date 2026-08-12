import { apiClient } from '@/lib/api';

export interface ClinicDashboardStats {
  timezone: string;
  patients_total: number;
  patients_added_today: number;
  patients_added_this_week: number;
  visits_today: number;
  visits_this_week: number;
  open_external_shares: number;
}

export const dashboardApi = {
  stats: () => apiClient.get<ClinicDashboardStats>('/dashboard/stats'),
};
