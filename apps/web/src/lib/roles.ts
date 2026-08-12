/** Shared clinic role labels and display helpers. */

export type ClinicRole =
	| "owner"
	| "dentist"
	| "assistant"
	| "front_desk"
	| "receptionist";

export const CLINIC_ROLE_OPTIONS: Array<{ value: ClinicRole; label: string }> = [
	{ value: "dentist", label: "Dentist" },
	{ value: "receptionist", label: "Receptionist" },
	{ value: "assistant", label: "Assistant" },
	{ value: "front_desk", label: "Front desk" },
	{ value: "owner", label: "Owner" },
];

export function formatClinicRole(role: string | null | undefined): string {
	if (!role) return "Member";
	const known = CLINIC_ROLE_OPTIONS.find((o) => o.value === role);
	if (known) return known.label;
	return role
		.split("_")
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join(" ");
}

/** Title-case a person's name; fall back to email local-part. */
export function displayUserName(
	fullName: string | null | undefined,
	email: string | null | undefined,
): string {
	const raw = (fullName ?? "").trim() || (email ?? "").split("@")[0] || "User";
	return raw
		.split(/\s+/)
		.filter(Boolean)
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
		.join(" ");
}
