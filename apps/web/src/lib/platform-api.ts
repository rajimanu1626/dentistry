import { apiClient } from "@/lib/api";

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
	system_role: "platform_admin" | "platform_support" | null;
	created_at: string;
}

export interface PlatformClinicInviteCreate {
	email: string;
	role: "owner" | "dentist" | "assistant" | "front_desk";
	expires_in_seconds?: number;
}

export interface PlatformInviteCreated {
	invite_id: string;
	email: string;
	role: string;
	invite_token: string;
	expires_at: string;
}

export const platformApi = {
	listGroups: () => apiClient.get<PlatformGroup[]>("/platform/groups"),
	createGroup: (body: { name: string; owner_user_id: string }) =>
		apiClient.post<PlatformGroup>("/platform/groups", body),
	listClinics: () => apiClient.get<PlatformClinic[]>("/platform/clinics"),
	createClinic: (body: {
		name: string;
		slug: string;
		group_id?: string | null;
		address?: string | null;
	}) => apiClient.post<PlatformClinic>("/platform/clinics", body),
	createClinicInvite: (clinicId: string, body: PlatformClinicInviteCreate) =>
		apiClient.post<PlatformInviteCreated>(
			`/platform/clinics/${clinicId}/invites`,
			body,
		),
	listUsers: () => apiClient.get<PlatformUser[]>("/platform/users"),
	updateUser: (
		userId: string,
		body: { is_active?: boolean; full_name?: string },
	) => apiClient.patch<PlatformUser>(`/platform/users/${userId}`, body),
};
