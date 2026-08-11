import { useQuery } from '@tanstack/react-query';
import { Link, createFileRoute } from '@tanstack/react-router';
import { ChevronRight, Plus, Search, Users } from 'lucide-react';
import { useEffect, useState } from 'react';

import { patientsApi } from '@/lib/patients';
import { requireClinicalWorkspace } from '@/lib/router-auth';

export const Route = createFileRoute('/patients')({
  beforeLoad: requireClinicalWorkspace,
  component: PatientsPage,
});

function PatientsPage() {
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const handle = window.setTimeout(() => {
      setSearchQuery(searchInput.trim());
    }, 300);
    return () => window.clearTimeout(handle);
  }, [searchInput]);

  const { data, isLoading, isFetching, error } = useQuery({
    queryKey: ['patients', { page: 1, q: searchQuery }],
    queryFn: () => patientsApi.list({ page: 1, page_size: 20, q: searchQuery || undefined }),
  });

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
            <Users className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Patients</h1>
            <p className="text-sm text-slate-500">Manage clinical records for your clinic.</p>
          </div>
        </div>
        <Link to="/patients/new" className="btn btn-primary">
          <Plus className="h-4 w-4" />
          New patient
        </Link>
      </header>

      <section className="card space-y-4">
        <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <label htmlFor="patient-search" className="label">
            Find patient quickly
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                id="patient-search"
                type="search"
                className="input pl-9"
                placeholder="Name, patient ID, or mobile number"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </div>
            {searchInput && (
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setSearchInput('');
                  setSearchQuery('');
                }}
              >
                Clear
              </button>
            )}
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
            <p>Supports name, patient ID, and phone search in current clinic.</p>
            {isFetching && !isLoading && <p>Updating results…</p>}
          </div>
        </div>
        {data && (
          <p className="text-xs text-slate-500">
            Showing {data.items.length} of {data.total} patient
            {data.total === 1 ? '' : 's'}
            {searchQuery ? ` for "${searchQuery}"` : ''}.
          </p>
        )}
        {isLoading && <p className="text-sm text-slate-500">Loading…</p>}
        {error && (
          <p className="text-sm text-red-600">
            Failed to load patients. Make sure you are signed in and have a clinic selected.
          </p>
        )}
        {data && data.items.length === 0 && (
          <p className="text-sm text-slate-500">
            {searchQuery ? (
              'No patients match this search.'
            ) : (
              <>
                No patients yet — click <strong>New patient</strong> to add the first one.
              </>
            )}
          </p>
        )}
        {data && data.items.length > 0 && (
          <ul className="space-y-2">
            {data.items.map((p) => (
              <li key={p.id}>
                <Link
                  to="/patients/$patientId"
                  params={{ patientId: p.id }}
                  className="group flex items-center justify-between gap-3 rounded-xl border border-slate-100 px-3 py-3 transition-all hover:border-brand-200 hover:bg-brand-50/40"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-gradient text-sm font-bold text-white">
                      {p.full_name.slice(0, 1).toUpperCase()}
                    </span>
                    <div>
                      <p className="font-semibold text-slate-900">{p.full_name}</p>
                      <p className="flex items-center gap-2 text-xs text-slate-500">
                        <span className="badge badge-muted font-mono">{p.patient_code}</span>
                        {p.date_of_birth ? `DOB ${p.date_of_birth}` : ''}
                      </p>
                    </div>
                  </div>
                  <span className="flex items-center gap-1 text-sm font-medium text-brand opacity-70 transition-opacity group-hover:opacity-100">
                    Open
                    <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
