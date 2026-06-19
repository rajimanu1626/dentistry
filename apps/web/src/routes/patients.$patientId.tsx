import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, createFileRoute, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';

import { patientsApi } from '@/lib/patients';
import { requireClinicalWorkspace } from '@/lib/router-auth';

export const Route = createFileRoute('/patients/$patientId')({
  beforeLoad: requireClinicalWorkspace,
  component: PatientDetailPage,
});

function PatientDetailPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { patientId } = Route.useParams();
  const [eventType, setEventType] = useState<string>('all');
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [visitNotes, setVisitNotes] = useState('');
  const [visitError, setVisitError] = useState<string | null>(null);
  const { data, isLoading, error } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => patientsApi.get(patientId),
  });
  const historyQuery = useQuery({
    queryKey: ['patient-history', patientId, eventType, cursor],
    queryFn: () =>
      patientsApi.history(patientId, {
        event_type: eventType === 'all' ? undefined : [eventType],
        cursor,
        limit: 10,
      }),
  });
  const createVisitMutation = useMutation({
    mutationFn: () =>
      patientsApi.createVisit({
        patient_id: patientId,
        visit_date: new Date().toISOString(),
        chief_complaint: chiefComplaint || null,
        notes: visitNotes || null,
      }),
    onSuccess: (data) => {
      setVisitError(null);
      setChiefComplaint('');
      setVisitNotes('');
      void queryClient.invalidateQueries({
        queryKey: ['patient-history', patientId],
      });
      void navigate({ to: '/visits/$visitId', params: { visitId: data.id } });
    },
    onError: (err: unknown) => {
      setVisitError(err instanceof Error ? err.message : 'Failed to create visit.');
    },
  });

  return (
    <div className="space-y-6">
      <Link to="/patients" className="text-sm text-brand hover:underline">
        ← Back to patients
      </Link>

      {isLoading && <p className="text-sm">Loading…</p>}
      {error && <p className="text-sm text-red-600">Failed to load patient.</p>}

      {data && (
        <>
          <article className="card space-y-4">
            <header>
              <h1 className="text-2xl font-semibold">{data.full_name}</h1>
              <p className="text-sm text-slate-500">{data.patient_code}</p>
            </header>

            <dl className="grid grid-cols-2 gap-4 text-sm">
              <Field label="Date of birth" value={data.date_of_birth} />
              <Field label="Sex" value={data.sex} />
              <Field label="Phone" value={data.phone} />
              <Field label="Email" value={data.email} />
              <Field label="Address" value={data.address} wide />
              <Field label="Allergies" value={data.allergies} wide />
              <Field label="Medical history" value={data.medical_history} wide />
              <Field label="Notes" value={data.notes} wide />
            </dl>
          </article>

          <section className="card space-y-4">
            <div className="space-y-2 rounded-md border border-slate-200 p-3">
              <h3 className="text-sm font-semibold">Add today's log</h3>
              <form
                className="space-y-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  createVisitMutation.mutate();
                }}
              >
                <input
                  className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                  placeholder="Chief complaint"
                  value={chiefComplaint}
                  onChange={(e) => setChiefComplaint(e.target.value)}
                />
                <textarea
                  className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                  placeholder="Notes"
                  value={visitNotes}
                  onChange={(e) => setVisitNotes(e.target.value)}
                />
                <p className="text-xs text-slate-500">
                  Diagnosis and treatment plan can be added on the Visit page after saving.
                </p>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={createVisitMutation.isPending}
                >
                  {createVisitMutation.isPending ? 'Saving...' : "Save today's log"}
                </button>
              </form>
              {visitError && <p className="text-sm text-red-600">{visitError}</p>}
            </div>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Visit Log & History</h2>
              <select
                className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                value={eventType}
                onChange={(e) => {
                  setCursor(undefined);
                  setEventType(e.target.value);
                }}
              >
                <option value="all">All events</option>
                <option value="visit">Visits</option>
                <option value="prescription">Prescriptions</option>
                <option value="media">Media</option>
                <option value="internal_share">Internal shares</option>
                <option value="external_share">External shares</option>
              </select>
            </div>

            {historyQuery.isLoading && <p className="text-sm text-slate-500">Loading history…</p>}
            {historyQuery.error && <p className="text-sm text-red-600">Failed to load history.</p>}

            {historyQuery.data && historyQuery.data.items.length === 0 && (
              <p className="text-sm text-slate-500">No timeline events yet.</p>
            )}

            {historyQuery.data && historyQuery.data.items.length > 0 && (
              <ol className="space-y-3">
                {historyQuery.data.items.map((item) => (
                  <li key={item.id} className="rounded-md border border-slate-200 p-3">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium">{item.title}</p>
                        <p className="text-xs text-slate-500">
                          {new Date(item.event_time).toLocaleString()} · {item.event_type}
                        </p>
                        {item.summary && (
                          <p className="mt-1 text-sm text-slate-700">{item.summary}</p>
                        )}
                      </div>
                      {item.visit_id && (
                        <Link
                          to="/visits/$visitId"
                          params={{ visitId: item.visit_id }}
                          className="text-xs text-brand hover:underline"
                        >
                          Open visit
                        </Link>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            )}

            {historyQuery.data?.next_cursor && (
              <button
                type="button"
                className="btn"
                onClick={() => setCursor(historyQuery.data?.next_cursor ?? undefined)}
              >
                Load older events
              </button>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function Field({
  label,
  value,
  wide = false,
}: { label: string; value: string | null; wide?: boolean }) {
  return (
    <div className={wide ? 'col-span-2' : ''}>
      <dt className="text-slate-500">{label}</dt>
      <dd>{value ?? <span className="text-slate-400">—</span>}</dd>
    </div>
  );
}
