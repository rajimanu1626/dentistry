import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, createFileRoute } from '@tanstack/react-router';
import { ArrowLeft } from 'lucide-react';
import { useEffect, useState } from 'react';

import { auth } from '@/lib/auth';
import { patientsApi } from '@/lib/patients';
import { requireClinicalWorkspace } from '@/lib/router-auth';

export const Route = createFileRoute('/visits/$visitId')({
  beforeLoad: requireClinicalWorkspace,
  component: VisitDetailPage,
});

function VisitDetailPage() {
  const queryClient = useQueryClient();
  const { visitId } = Route.useParams();
  const [rxMedication, setRxMedication] = useState('');
  const [rxDose, setRxDose] = useState('');
  const [rxFrequency, setRxFrequency] = useState('');
  const [rxDuration, setRxDuration] = useState('');
  const [rxNotes, setRxNotes] = useState('');
  const [chiefComplaint, setChiefComplaint] = useState('');
  const [diagnosis, setDiagnosis] = useState('');
  const [treatmentPlan, setTreatmentPlan] = useState('');
  const [visitNotes, setVisitNotes] = useState('');
  const [followupDate, setFollowupDate] = useState('');
  const [followupNotes, setFollowupNotes] = useState('');
  const [mediaFile, setMediaFile] = useState<File | null>(null);
  const [mediaKind, setMediaKind] = useState<'before' | 'after' | 'xray' | 'other'>('before');
  const [shareRecipient, setShareRecipient] = useState('');
  const [shareTtlHours, setShareTtlHours] = useState('24');
  const [shareMaxViews, setShareMaxViews] = useState('5');
  const [sharePassword, setSharePassword] = useState('');
  const [shareScopeMode, setShareScopeMode] = useState<'visit' | 'history'>('visit');
  const [createdShare, setCreatedShare] = useState<{
    url: string;
    password: string;
    expiresAt: string;
  } | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [shareMessage, setShareMessage] = useState<string | null>(null);

  const summaryQuery = useQuery({
    queryKey: ['visit-summary', visitId],
    queryFn: () => patientsApi.visitSummary(visitId),
  });
  useEffect(() => {
    if (!summaryQuery.data) return;
    setChiefComplaint(summaryQuery.data.visit.chief_complaint ?? '');
    setDiagnosis(summaryQuery.data.visit.diagnosis ?? '');
    setTreatmentPlan(summaryQuery.data.visit.treatment_plan ?? '');
    setVisitNotes(summaryQuery.data.visit.notes ?? '');
  }, [summaryQuery.data]);
  const mediaQuery = useQuery({
    queryKey: ['patient-media', summaryQuery.data?.visit.patient_id],
    queryFn: () => patientsApi.listMedia(summaryQuery.data!.visit.patient_id),
    enabled: Boolean(summaryQuery.data?.visit.patient_id),
  });
  const externalSharesQuery = useQuery({
    queryKey: ['external-shares', summaryQuery.data?.visit.patient_id],
    queryFn: () => patientsApi.listExternalShares(summaryQuery.data!.visit.patient_id),
    enabled: Boolean(summaryQuery.data?.visit.patient_id),
  });

  const createPrescriptionMutation = useMutation({
    mutationFn: () =>
      patientsApi.createPrescription({
        visit_id: visitId,
        items: [
          {
            medication: rxMedication,
            dose: rxDose,
            frequency: rxFrequency,
            duration: rxDuration,
            notes: rxNotes || null,
          },
        ],
      }),
    onSuccess: () => {
      setActionError(null);
      setRxMedication('');
      setRxDose('');
      setRxFrequency('');
      setRxDuration('');
      setRxNotes('');
      void queryClient.invalidateQueries({ queryKey: ['visit-summary', visitId] });
    },
    onError: (err: unknown) => {
      setActionError(err instanceof Error ? err.message : 'Failed to add prescription.');
    },
  });
  const updateVisitMutation = useMutation({
    mutationFn: () =>
      patientsApi.updateVisit(visitId, {
        chief_complaint: chiefComplaint || null,
        diagnosis: diagnosis || null,
        treatment_plan: treatmentPlan || null,
        notes: visitNotes || null,
      }),
    onSuccess: () => {
      setActionError(null);
      void queryClient.invalidateQueries({ queryKey: ['visit-summary', visitId] });
    },
    onError: (err: unknown) => {
      setActionError(err instanceof Error ? err.message : 'Failed to update visit.');
    },
  });

  const createFollowupMutation = useMutation({
    mutationFn: () => {
      const existing = summaryQuery.data?.visit.notes?.trim();
      const followupLine = `[FOLLOWUP] ${followupDate || 'no-date'} - ${followupNotes || 'No notes'}`;
      const notes = existing ? `${existing}\n${followupLine}` : followupLine;
      return patientsApi.updateVisit(visitId, { notes });
    },
    onSuccess: () => {
      setActionError(null);
      setFollowupDate('');
      setFollowupNotes('');
      void queryClient.invalidateQueries({ queryKey: ['visit-summary', visitId] });
    },
    onError: (err: unknown) => {
      setActionError(err instanceof Error ? err.message : 'Failed to create follow-up.');
    },
  });

  const uploadMediaMutation = useMutation({
    mutationFn: () => {
      if (!summaryQuery.data?.visit.patient_id || !mediaFile) {
        throw new Error('Select a media file first.');
      }
      return patientsApi.uploadMedia(summaryQuery.data.visit.patient_id, {
        file: mediaFile,
        kind: mediaKind,
        visit_id: visitId,
      });
    },
    onSuccess: () => {
      setActionError(null);
      setMediaFile(null);
      void queryClient.invalidateQueries({
        queryKey: ['patient-media', summaryQuery.data?.visit.patient_id],
      });
      void queryClient.invalidateQueries({ queryKey: ['visit-summary', visitId] });
    },
    onError: (err: unknown) => {
      setActionError(err instanceof Error ? err.message : 'Failed to upload media.');
    },
  });
  const createExternalShareMutation = useMutation({
    mutationFn: () => {
      const patientId = summaryQuery.data?.visit.patient_id;
      if (!patientId) throw new Error('Patient context missing.');
      const ttlSeconds = Math.max(1, Number.parseInt(shareTtlHours || '24', 10)) * 3600;
      const maxViews = Math.max(1, Number.parseInt(shareMaxViews || '5', 10));
      return patientsApi.createExternalShare(patientId, {
        expires_in_seconds: ttlSeconds,
        max_views: maxViews,
        recipient_label: shareRecipient || undefined,
        password: sharePassword || undefined,
        scope:
          shareScopeMode === 'history' ? { mode: 'history' } : { mode: 'visit', visit_id: visitId },
      });
    },
    onSuccess: (data) => {
      setActionError(null);
      setCreatedShare({
        url: data.url,
        password: data.password,
        expiresAt: data.expires_at,
      });
      setShareMessage('External share link created.');
      void queryClient.invalidateQueries({
        queryKey: ['external-shares', summaryQuery.data?.visit.patient_id],
      });
    },
    onError: (err: unknown) => {
      setActionError(err instanceof Error ? err.message : 'Failed to create external share.');
    },
  });
  const revokeExternalShareMutation = useMutation({
    mutationFn: (shareId: string) => {
      const patientId = summaryQuery.data?.visit.patient_id;
      if (!patientId) throw new Error('Patient context missing.');
      return patientsApi.revokeExternalShare(patientId, shareId);
    },
    onSuccess: () => {
      setActionError(null);
      setShareMessage('External share revoked.');
      void queryClient.invalidateQueries({
        queryKey: ['external-shares', summaryQuery.data?.visit.patient_id],
      });
    },
    onError: (err: unknown) => {
      setActionError(err instanceof Error ? err.message : 'Failed to revoke external share.');
    },
  });

  async function openProtectedPdf(path: string): Promise<void> {
    const popup = window.open('about:blank', '_blank', 'noopener,noreferrer');
    try {
      const token = auth.getToken();
      const clinicId = auth.getClinicId();
      if (!token || !clinicId) {
        throw new Error('You must be signed in with a clinic selected.');
      }
      const res = await fetch(`/api${path}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'X-Clinic-Id': clinicId,
        },
      });
      if (!res.ok) {
        let message = 'Unable to generate PDF. Please try again.';
        try {
          const body = (await res.json()) as {
            error?: { message?: string };
          };
          if (body.error?.message) {
            message = body.error.message;
          }
        } catch {
          // response was not JSON (e.g. proxy error page)
        }
        throw new Error(message);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      if (popup && !popup.closed) {
        popup.location.href = url;
      } else {
        window.open(url, '_blank', 'noopener,noreferrer');
      }
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      if (popup && !popup.closed) {
        popup.close();
      }
      setActionError(err instanceof Error ? err.message : 'Unable to open PDF.');
    }
  }

  return (
    <div className="space-y-6">
      <Link
        to="/patients"
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition-colors hover:text-brand"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to patients
      </Link>

      {summaryQuery.isLoading && <p className="text-sm text-slate-500">Loading visit summary…</p>}
      {summaryQuery.error && <p className="text-sm text-red-600">Failed to load visit summary.</p>}

      {summaryQuery.data && (
        <>
          <article className="card space-y-3">
            <header>
              <h1 className="text-xl font-semibold">Visit Detail</h1>
              <p className="text-sm text-slate-500">
                {new Date(summaryQuery.data.visit.visit_date).toLocaleString()}
              </p>
            </header>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <Field label="Chief complaint" value={summaryQuery.data.visit.chief_complaint} />
              <Field label="Diagnosis" value={summaryQuery.data.visit.diagnosis} />
              <Field label="Treatment plan" value={summaryQuery.data.visit.treatment_plan} wide />
              <Field label="Notes" value={summaryQuery.data.visit.notes} wide />
            </dl>
          </article>

          <section className="card space-y-3">
            <h2 className="text-lg font-semibold">Update visit details</h2>
            <form
              className="space-y-2"
              onSubmit={(e) => {
                e.preventDefault();
                updateVisitMutation.mutate();
              }}
            >
              <input
                className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="Chief complaint"
                value={chiefComplaint}
                onChange={(e) => setChiefComplaint(e.target.value)}
              />
              <input
                className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="Diagnosis"
                value={diagnosis}
                onChange={(e) => setDiagnosis(e.target.value)}
              />
              <input
                className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="Treatment plan"
                value={treatmentPlan}
                onChange={(e) => setTreatmentPlan(e.target.value)}
              />
              <textarea
                className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="Notes"
                value={visitNotes}
                onChange={(e) => setVisitNotes(e.target.value)}
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={updateVisitMutation.isPending}
              >
                {updateVisitMutation.isPending ? 'Saving...' : 'Save visit details'}
              </button>
            </form>
          </section>

          <section className="card space-y-3">
            <h2 className="text-lg font-semibold">Prescriptions</h2>
            {summaryQuery.data.prescriptions.length === 0 && (
              <p className="text-sm text-slate-500">No prescriptions attached to this visit.</p>
            )}
            {summaryQuery.data.prescriptions.map((rx) => (
              <div key={rx.id} className="rounded-md border border-slate-200 p-3 text-sm">
                <p className="font-medium">Prescription {rx.id.slice(0, 8)}</p>
                <p className="text-slate-600">Items: {rx.items.length}</p>
                {rx.notes && <p className="text-slate-700">{rx.notes}</p>}
              </div>
            ))}
            <form
              className="mt-3 space-y-2 rounded-md border border-slate-200 p-3"
              onSubmit={(e) => {
                e.preventDefault();
                createPrescriptionMutation.mutate();
              }}
            >
              <h3 className="text-sm font-semibold">Add prescription</h3>
              <input
                className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="Medication"
                value={rxMedication}
                onChange={(e) => setRxMedication(e.target.value)}
                required
              />
              <div className="grid grid-cols-3 gap-2">
                <input
                  className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                  placeholder="Dose"
                  value={rxDose}
                  onChange={(e) => setRxDose(e.target.value)}
                  required
                />
                <input
                  className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                  placeholder="Frequency"
                  value={rxFrequency}
                  onChange={(e) => setRxFrequency(e.target.value)}
                  required
                />
                <input
                  className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                  placeholder="Duration"
                  value={rxDuration}
                  onChange={(e) => setRxDuration(e.target.value)}
                  required
                />
              </div>
              <textarea
                className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="Notes"
                value={rxNotes}
                onChange={(e) => setRxNotes(e.target.value)}
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={createPrescriptionMutation.isPending}
              >
                {createPrescriptionMutation.isPending ? 'Saving...' : 'Add prescription'}
              </button>
            </form>
          </section>

          <section className="card space-y-3">
            <h2 className="text-lg font-semibold">Follow-up</h2>
            <form
              className="space-y-2"
              onSubmit={(e) => {
                e.preventDefault();
                createFollowupMutation.mutate();
              }}
            >
              <input
                type="date"
                className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                value={followupDate}
                onChange={(e) => setFollowupDate(e.target.value)}
              />
              <textarea
                className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="Follow-up notes"
                value={followupNotes}
                onChange={(e) => setFollowupNotes(e.target.value)}
              />
              <button type="submit" className="btn" disabled={createFollowupMutation.isPending}>
                {createFollowupMutation.isPending ? 'Saving...' : 'Save follow-up'}
              </button>
            </form>
          </section>

          <section className="card space-y-3">
            <h2 className="text-lg font-semibold">Visit media</h2>
            <form
              className="space-y-2"
              onSubmit={(e) => {
                e.preventDefault();
                uploadMediaMutation.mutate();
              }}
            >
              <select
                className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                value={mediaKind}
                onChange={(e) =>
                  setMediaKind(e.target.value as 'before' | 'after' | 'xray' | 'other')
                }
              >
                <option value="before">Before</option>
                <option value="after">After</option>
                <option value="xray">X-ray</option>
                <option value="other">Other</option>
              </select>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setMediaFile(e.target.files?.[0] ?? null)}
              />
              <button
                type="submit"
                className="btn"
                disabled={uploadMediaMutation.isPending || !mediaFile}
              >
                {uploadMediaMutation.isPending ? 'Uploading...' : 'Upload media'}
              </button>
            </form>
            {mediaQuery.data && mediaQuery.data.length > 0 && (
              <div className="grid grid-cols-2 gap-3">
                {mediaQuery.data
                  .filter((m) => m.visit_id === visitId)
                  .map((m) => (
                    <a
                      key={m.id}
                      href={m.signed_url}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-md border border-slate-200 p-2 text-xs hover:bg-slate-50"
                    >
                      {m.kind} · {new Date(m.created_at).toLocaleString()}
                    </a>
                  ))}
              </div>
            )}
          </section>

          <section className="card space-y-3">
            <h2 className="text-lg font-semibold">Quick actions</h2>
            <div className="flex flex-wrap gap-2">
              {summaryQuery.data.prescriptions[0] && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() =>
                    void openProtectedPdf(
                      `/prescriptions/${summaryQuery.data!.prescriptions[0].id}/pdf`,
                    )
                  }
                >
                  Print prescription
                </button>
              )}
              <button
                type="button"
                className="btn"
                onClick={() => void openProtectedPdf(`/visits/${visitId}/summary/pdf`)}
              >
                Print visit summary
              </button>
              <button
                type="button"
                className="btn"
                onClick={() =>
                  void openProtectedPdf(
                    `/patients/${summaryQuery.data!.visit.patient_id}/history/pdf`,
                  )
                }
              >
                Print full history
              </button>
              <button
                type="button"
                className="btn"
                onClick={async () => {
                  const link = `${window.location.origin}/patients/${summaryQuery.data?.visit.patient_id}?visit=${visitId}`;
                  try {
                    await navigator.clipboard.writeText(link);
                    setShareMessage('Summary link copied.');
                    setActionError(null);
                  } catch {
                    setActionError('Could not copy summary link.');
                  }
                }}
              >
                Share summary link
              </button>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-500">Visit summary link</label>
              <input
                readOnly
                className="w-full rounded-md border border-slate-300 bg-slate-50 px-2 py-1 text-xs"
                value={`${window.location.origin}/patients/${summaryQuery.data.visit.patient_id}?visit=${visitId}`}
              />
            </div>
            {shareMessage && <p className="text-sm text-emerald-700">{shareMessage}</p>}
            {actionError && <p className="text-sm text-red-600">{actionError}</p>}
          </section>

          <section className="card space-y-3">
            <h2 className="text-lg font-semibold">External share (patient handoff)</h2>
            <form
              className="space-y-2"
              onSubmit={(e) => {
                e.preventDefault();
                createExternalShareMutation.mutate();
              }}
            >
              <input
                className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="Recipient label (optional)"
                value={shareRecipient}
                onChange={(e) => setShareRecipient(e.target.value)}
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  min={1}
                  className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                  placeholder="Expiry (hours)"
                  value={shareTtlHours}
                  onChange={(e) => setShareTtlHours(e.target.value)}
                />
                <input
                  type="number"
                  min={1}
                  max={50}
                  className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                  placeholder="Max views"
                  value={shareMaxViews}
                  onChange={(e) => setShareMaxViews(e.target.value)}
                />
              </div>
              <input
                type="text"
                className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="Password (optional, auto-generated if empty)"
                value={sharePassword}
                onChange={(e) => setSharePassword(e.target.value)}
              />
              <select
                className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                value={shareScopeMode}
                onChange={(e) => setShareScopeMode(e.target.value as 'visit' | 'history')}
              >
                <option value="visit">Share this visit only</option>
                <option value="history">Share entire history</option>
              </select>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={createExternalShareMutation.isPending}
              >
                {createExternalShareMutation.isPending ? 'Generating...' : 'Generate secure share'}
              </button>
            </form>

            {createdShare && (
              <div className="space-y-1 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                <p>
                  <strong>URL:</strong> {createdShare.url}
                </p>
                <p>
                  <strong>Password:</strong> {createdShare.password}
                </p>
                <p>
                  <strong>Expires:</strong> {new Date(createdShare.expiresAt).toLocaleString()}
                </p>
              </div>
            )}

            {externalSharesQuery.data && externalSharesQuery.data.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-semibold">Existing shares</h3>
                <ul className="space-y-2">
                  {externalSharesQuery.data.map((share) => (
                    <li
                      key={share.id}
                      className="flex items-center justify-between rounded-md border border-slate-200 p-2 text-sm"
                    >
                      <div>
                        <p>
                          {share.recipient_label || 'External recipient'} · views {share.view_count}
                          /{share.max_views}
                        </p>
                        <p className="text-xs text-slate-500">
                          Expires {new Date(share.expires_at).toLocaleString()}
                          {share.revoked_at ? ' · revoked' : ''}
                        </p>
                      </div>
                      {!share.revoked_at && (
                        <button
                          type="button"
                          className="text-xs text-red-600 hover:underline"
                          disabled={revokeExternalShareMutation.isPending}
                          onClick={() => revokeExternalShareMutation.mutate(share.id)}
                        >
                          Revoke
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
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
