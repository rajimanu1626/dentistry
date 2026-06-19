import { apiClient } from './api';

export interface PatientListItem {
  id: string;
  patient_code: string;
  full_name: string;
  date_of_birth: string | null;
  sex: string | null;
  created_at: string;
}

export interface PatientPage {
  items: PatientListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface PatientPublic extends PatientListItem {
  clinic_id: string;
  phone: string | null;
  email: string | null;
  address: string | null;
  allergies: string | null;
  medical_history: string | null;
  notes: string | null;
  updated_at: string;
}

export interface PatientCreate {
  full_name: string;
  date_of_birth?: string | null;
  sex?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  allergies?: string | null;
  medical_history?: string | null;
  notes?: string | null;
}

export interface VisitHistoryItem {
  id: string;
  event_type: 'visit' | 'prescription' | 'media' | 'internal_share' | 'external_share' | string;
  event_time: string;
  visit_id: string | null;
  patient_id: string;
  title: string;
  summary: string | null;
  metadata: Record<string, unknown>;
}

export interface VisitHistoryPage {
  items: VisitHistoryItem[];
  next_cursor: string | null;
}

export interface VisitSummary {
  visit: {
    id: string;
    clinic_id: string;
    patient_id: string;
    dentist_id: string | null;
    visit_date: string;
    chief_complaint: string | null;
    diagnosis: string | null;
    treatment_plan: string | null;
    notes: string | null;
    created_at: string;
    updated_at: string;
  };
  prescriptions: Array<{
    id: string;
    clinic_id: string;
    visit_id: string;
    template_id: string | null;
    items: Array<Record<string, unknown>>;
    notes: string | null;
    pdf_object_key: string | null;
    created_at: string;
    updated_at: string;
  }>;
  media: Array<{
    id: string;
    kind: string;
    object_key: string;
    mime_type: string;
    created_at: string;
    visit_id: string | null;
  }>;
}

export interface VisitCreatePayload {
  patient_id: string;
  visit_date: string;
  dentist_id?: string | null;
  chief_complaint?: string | null;
  diagnosis?: string | null;
  treatment_plan?: string | null;
  notes?: string | null;
}

export interface VisitUpdatePayload {
  visit_date?: string;
  dentist_id?: string | null;
  chief_complaint?: string | null;
  diagnosis?: string | null;
  treatment_plan?: string | null;
  notes?: string | null;
}

export interface PrescriptionItemPayload {
  medication: string;
  dose: string;
  frequency: string;
  duration: string;
  notes?: string | null;
}

export interface PrescriptionCreatePayload {
  visit_id: string;
  template_id?: string | null;
  items: PrescriptionItemPayload[];
  notes?: string | null;
}

export interface PatientMediaItem {
  id: string;
  clinic_id: string;
  patient_id: string;
  visit_id: string | null;
  kind: string;
  mime_type: string;
  width_px: number | null;
  height_px: number | null;
  bytes_size: number | null;
  object_key: string;
  created_at: string;
  signed_url: string;
}

export interface ExternalShareCreatePayload {
  expires_in_seconds?: number;
  max_views?: number;
  recipient_label?: string;
  scope?: Record<string, unknown>;
  password?: string;
}

export interface ExternalShareCreated {
  id: string;
  url: string;
  password: string;
  expires_at: string;
  max_views: number;
}

export interface ExternalShareRecord {
  id: string;
  patient_id: string;
  clinic_id: string;
  recipient_label: string | null;
  expires_at: string;
  revoked_at: string | null;
  max_views: number;
  view_count: number;
  failed_attempts: number;
  last_accessed_at: string | null;
  created_by: string | null;
  created_at: string;
}

export const patientsApi = {
  list: (params?: { page?: number; page_size?: number; q?: string }) =>
    apiClient.get<PatientPage>('/patients', { params }),
  get: (id: string) => apiClient.get<PatientPublic>(`/patients/${id}`),
  create: (body: PatientCreate) => apiClient.post<PatientPublic>('/patients', body),
  update: (id: string, body: Partial<PatientCreate>) =>
    apiClient.patch<PatientPublic>(`/patients/${id}`, body),
  remove: (id: string) => apiClient.delete<void>(`/patients/${id}`),
  history: (
    id: string,
    params?: {
      event_type?: string[];
      q?: string;
      cursor?: string;
      limit?: number;
    },
  ) => apiClient.get<VisitHistoryPage>(`/patients/${id}/history`, { params }),
  visitSummary: (visitId: string) => apiClient.get<VisitSummary>(`/visits/${visitId}/summary`),
  createVisit: (body: VisitCreatePayload) => apiClient.post<{ id: string }>('/visits', body),
  updateVisit: (visitId: string, body: VisitUpdatePayload) =>
    apiClient.patch(`/visits/${visitId}`, body),
  createPrescription: (body: PrescriptionCreatePayload) =>
    apiClient.post<{ id: string }>('/prescriptions', body),
  listMedia: (patientId: string) =>
    apiClient.get<PatientMediaItem[]>(`/patients/${patientId}/media`),
  uploadMedia: (
    patientId: string,
    body: {
      file: File;
      kind: 'before' | 'after' | 'xray' | 'other';
      visit_id?: string;
    },
  ) => {
    const form = new FormData();
    form.append('file', body.file);
    form.append('kind', body.kind);
    if (body.visit_id) form.append('visit_id', body.visit_id);
    return apiClient.post<PatientMediaItem>(`/patients/${patientId}/media`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  createExternalShare: (patientId: string, body: ExternalShareCreatePayload) =>
    apiClient.post<ExternalShareCreated>(`/patients/${patientId}/external-shares`, body),
  listExternalShares: (patientId: string) =>
    apiClient.get<ExternalShareRecord[]>(`/patients/${patientId}/external-shares`),
  revokeExternalShare: (patientId: string, shareId: string) =>
    apiClient.delete<void>(`/patients/${patientId}/external-shares/${shareId}`),
};
