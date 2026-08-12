import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { type FormEvent, useState } from "react";

import { patientsApi } from "@/lib/patients";
import { requireClinicalWorkspace } from "@/lib/router-auth";

export const Route = createFileRoute("/patients/new")({
	beforeLoad: requireClinicalWorkspace,
	component: NewPatientPage,
});

interface FormState {
	full_name: string;
	date_of_birth: string;
	sex: string;
	phone: string;
	email: string;
	allergies: string;
	notes: string;
}

const empty: FormState = {
	full_name: "",
	date_of_birth: "",
	sex: "",
	phone: "",
	email: "",
	allergies: "",
	notes: "",
};

function NewPatientPage() {
	const qc = useQueryClient();
	const nav = useNavigate();
	const [form, setForm] = useState<FormState>(empty);

	const m = useMutation({
		mutationFn: () =>
			patientsApi.create({
				full_name: form.full_name,
				date_of_birth: form.date_of_birth || null,
				sex: form.sex || null,
				phone: form.phone || null,
				email: form.email || null,
				allergies: form.allergies || null,
				notes: form.notes || null,
			}),
		onSuccess: async (created) => {
			await qc.invalidateQueries({ queryKey: ["patients"] });
			await nav({
				to: "/patients/$patientId",
				params: { patientId: created.id },
			});
		},
	});

	function update<K extends keyof FormState>(key: K, value: FormState[K]) {
		setForm((s) => ({ ...s, [key]: value }));
	}

	function handleSubmit(e: FormEvent) {
		e.preventDefault();
		m.mutate();
	}

	return (
		<form className="card space-y-5" onSubmit={handleSubmit}>
			<h1 className="text-xl font-semibold">New patient</h1>

			<label className="field" htmlFor="full_name">
				<span>Full name</span>
				<input
					id="full_name"
					required
					className="input mt-1"
					value={form.full_name}
					onChange={(e) => update("full_name", e.target.value)}
				/>
			</label>

			<div className="grid grid-cols-2 gap-4">
				<label className="field" htmlFor="dob">
					<span>Date of birth</span>
					<input
						id="dob"
						type="date"
						className="input mt-1"
						value={form.date_of_birth}
						onChange={(e) => update("date_of_birth", e.target.value)}
					/>
				</label>
				<label className="field" htmlFor="sex">
					<span>Sex</span>
					<select
						id="sex"
						className="input mt-1"
						value={form.sex}
						onChange={(e) => update("sex", e.target.value)}
					>
						<option value="">—</option>
						<option value="F">F</option>
						<option value="M">M</option>
						<option value="other">other</option>
					</select>
				</label>
			</div>

			<label className="field" htmlFor="phone">
				<span>Phone</span>
				<input
					id="phone"
					className="input mt-1"
					value={form.phone}
					onChange={(e) => update("phone", e.target.value)}
				/>
			</label>

			<label className="field" htmlFor="email">
				<span>Email</span>
				<input
					id="email"
					type="email"
					className="input mt-1"
					value={form.email}
					onChange={(e) => update("email", e.target.value)}
				/>
			</label>

			<label className="field" htmlFor="allergies">
				<span>Allergies (encrypted at rest)</span>
				<textarea
					id="allergies"
					rows={2}
					className="input mt-1"
					value={form.allergies}
					onChange={(e) => update("allergies", e.target.value)}
				/>
			</label>

			<label className="field" htmlFor="notes">
				<span>Notes</span>
				<textarea
					id="notes"
					rows={3}
					className="input mt-1"
					value={form.notes}
					onChange={(e) => update("notes", e.target.value)}
				/>
			</label>

			{m.error && (
				<p className="text-sm text-red-600">
					{(m.error as Error).message === "Network Error"
						? "Could not reach the API (often a missing clinic context or blocked CORS). Sign out, sign back in, then retry."
						: (m.error as Error).message}
				</p>
			)}

			<button type="submit" className="btn btn-primary" disabled={m.isPending}>
				{m.isPending ? "Saving…" : "Create patient"}
			</button>
		</form>
	);
}
