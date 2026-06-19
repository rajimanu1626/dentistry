import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { type FormEvent, useState } from 'react';

import { patientsApi } from '@/lib/patients';
import { requireClinicalWorkspace } from '@/lib/router-auth';

export const Route = createFileRoute('/patients/new')({
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
  full_name: '',
  date_of_birth: '',
  sex: '',
  phone: '',
  email: '',
  allergies: '',
  notes: '',
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
      await qc.invalidateQueries({ queryKey: ['patients'] });
      await nav({
        to: '/patients/$patientId',
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
    <form className="card space-y-4" onSubmit={handleSubmit}>
      <h1 className="text-xl font-semibold">New patient</h1>

      <div>
        <label className="block text-sm font-medium" htmlFor="full_name">
          Full name
        </label>
        <input
          id="full_name"
          required
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          value={form.full_name}
          onChange={(e) => update('full_name', e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium" htmlFor="dob">
            Date of birth
          </label>
          <input
            id="dob"
            type="date"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            value={form.date_of_birth}
            onChange={(e) => update('date_of_birth', e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium" htmlFor="sex">
            Sex
          </label>
          <select
            id="sex"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            value={form.sex}
            onChange={(e) => update('sex', e.target.value)}
          >
            <option value="">—</option>
            <option value="F">F</option>
            <option value="M">M</option>
            <option value="other">other</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium" htmlFor="phone">
          Phone
        </label>
        <input
          id="phone"
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          value={form.phone}
          onChange={(e) => update('phone', e.target.value)}
        />
      </div>

      <div>
        <label className="block text-sm font-medium" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          type="email"
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          value={form.email}
          onChange={(e) => update('email', e.target.value)}
        />
      </div>

      <div>
        <label className="block text-sm font-medium" htmlFor="allergies">
          Allergies (encrypted at rest)
        </label>
        <textarea
          id="allergies"
          rows={2}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          value={form.allergies}
          onChange={(e) => update('allergies', e.target.value)}
        />
      </div>

      <div>
        <label className="block text-sm font-medium" htmlFor="notes">
          Notes
        </label>
        <textarea
          id="notes"
          rows={3}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          value={form.notes}
          onChange={(e) => update('notes', e.target.value)}
        />
      </div>

      {m.error && <p className="text-sm text-red-600">{(m.error as Error).message}</p>}

      <button type="submit" className="btn btn-primary" disabled={m.isPending}>
        {m.isPending ? 'Saving…' : 'Create patient'}
      </button>
    </form>
  );
}
