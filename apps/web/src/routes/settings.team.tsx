import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useMemo, useState } from 'react';

import { auth } from '@/lib/auth';
import {
  type ApiError,
  createInvite,
  fetchMe,
  leaveClinic,
  listInvites,
  revokeInvite,
} from '@/lib/auth-api';
import { CLINIC_ROLE_OPTIONS, type ClinicRole, formatClinicRole } from '@/lib/roles';
import { requireClinicalWorkspace } from '@/lib/router-auth';

export const Route = createFileRoute('/settings/team')({
  beforeLoad: requireClinicalWorkspace,
  component: TeamSettingsPage,
});

function TeamSettingsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const clinicId = auth.getClinicId();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<ClinicRole>('dentist');
  const [tokenData, setTokenData] = useState<{
    token: string;
    email: string;
    expiresAt: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const meQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: fetchMe,
  });

  const currentMembership = useMemo(
    () => meQuery.data?.memberships.find((m) => m.clinic_id === clinicId),
    [meQuery.data, clinicId],
  );
  const isOwner = currentMembership?.role === 'owner';
  const invitesQuery = useQuery({
    queryKey: ['auth', 'invites'],
    queryFn: listInvites,
    enabled: isOwner,
  });

  const inviteMutation = useMutation({
    mutationFn: () => createInvite({ email, role }),
    onSuccess: (data) => {
      setError(null);
      setToast('Invite created. Share the URL below.');
      setTokenData({
        token: data.invite_token,
        email: data.email,
        expiresAt: data.expires_at,
      });
      void queryClient.invalidateQueries({ queryKey: ['auth', 'invites'] });
    },
    onError: (err: ApiError) => {
      setTokenData(null);
      setError(err.message);
    },
  });
  const revokeMutation = useMutation({
    mutationFn: (inviteId: string) => revokeInvite(inviteId),
    onSuccess: () => {
      setToast('Invite revoked.');
      void queryClient.invalidateQueries({ queryKey: ['auth', 'invites'] });
    },
    onError: (err: ApiError) => setError(err.message),
  });
  const leaveMutation = useMutation({
    mutationFn: leaveClinic,
    onSuccess: async (me) => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ['auth'] });
      if (me.memberships.length === 0) {
        auth.clearClinicId();
        setToast('You left the clinic.');
        await navigate({ to: '/signup' });
        return;
      }
      auth.setClinicId(me.memberships[0].clinic_id);
      setToast(`Switched to ${me.memberships[0].clinic_name}.`);
    },
    onError: (err: ApiError) => setError(err.message),
  });

  const inviteUrl = tokenData
    ? `${window.location.origin}/signup?token=${encodeURIComponent(tokenData.token)}&email=${encodeURIComponent(tokenData.email)}`
    : '';

  async function copy(value: string, label: string): Promise<void> {
    await navigator.clipboard.writeText(value);
    setToast(`${label} copied.`);
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Team & clinic</h1>
        <p className="mt-1 text-sm text-slate-600">
          See your clinic membership, leave if needed, and invite staff.
        </p>
      </header>

      <section className="card space-y-3">
        <h2 className="text-sm font-medium text-slate-800">Your membership</h2>
        {meQuery.isLoading && <p className="text-sm text-slate-500">Loading your membership…</p>}
        {!meQuery.isLoading && !currentMembership && (
          <p className="text-sm text-red-600">
            No clinic selected. Sign out and sign in again to restore clinic context.
          </p>
        )}
        {currentMembership && (
          <>
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">Clinic</dt>
                <dd className="font-medium text-slate-900">{currentMembership.clinic_name}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Your role</dt>
                <dd className="font-medium text-slate-900">
                  {formatClinicRole(currentMembership.role)}
                </dd>
              </div>
            </dl>
            <button
              type="button"
              className="btn text-red-700"
              disabled={leaveMutation.isPending}
              onClick={() => {
                const ok = window.confirm(
                  `Leave ${currentMembership.clinic_name}? You will lose access until invited again.`,
                );
                if (ok) leaveMutation.mutate();
              }}
            >
              {leaveMutation.isPending ? 'Leaving…' : 'Leave clinic'}
            </button>
            {isOwner && (
              <p className="text-xs text-slate-500">
                Owners can leave only when another owner remains.
              </p>
            )}
          </>
        )}
      </section>

      <section className="card space-y-4">
        <header>
          <h2 className="text-sm font-medium text-slate-800">Team invites</h2>
          <p className="mt-1 text-xs text-slate-500">
            Invite dentists, receptionists, and staff. Invite links are one-time use.
          </p>
        </header>
        {!clinicId && (
          <p className="text-sm text-red-600">
            No clinic selected. Sign out and sign in again to initialize your clinic context.
          </p>
        )}
        {toast && <p className="text-sm text-emerald-700">{toast}</p>}
        {!meQuery.isLoading && !isOwner && (
          <p className="text-sm text-slate-600">Only clinic owners can create invite links.</p>
        )}

        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (!isOwner || !clinicId) return;
            inviteMutation.mutate();
          }}
        >
          <label className="field">
            <span>Invitee email</span>
            <input
              type="email"
              required
              className="input mt-1"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="dentist@clinic.com"
              disabled={!isOwner || !clinicId || inviteMutation.isPending}
            />
          </label>

          <label className="field">
            <span>Role</span>
            <select
              className="input mt-1"
              value={role}
              onChange={(e) => setRole(e.target.value as ClinicRole)}
              disabled={!isOwner || !clinicId || inviteMutation.isPending}
            >
              {CLINIC_ROLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={!isOwner || !clinicId || inviteMutation.isPending || !email.trim()}
          >
            {inviteMutation.isPending ? 'Creating invite…' : 'Create invite'}
          </button>
        </form>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {tokenData && (
          <div className="space-y-3 rounded-md border border-slate-200 bg-slate-50 p-4">
            <p className="text-sm font-medium text-slate-800">Invite created</p>
            <p className="text-xs text-slate-600">
              Expires at: <span className="font-mono">{tokenData.expiresAt}</span>
            </p>
            <label htmlFor="invite-token" className="block text-xs font-medium text-slate-700">
              Invite token
            </label>
            <input
              id="invite-token"
              readOnly
              value={tokenData.token}
              className="input input-mono"
            />
            <button
              type="button"
              className="btn"
              onClick={() => void copy(tokenData.token, 'Invite token')}
            >
              Copy token
            </button>
            <label htmlFor="invite-url" className="block text-xs font-medium text-slate-700">
              Invite signup URL
            </label>
            <input id="invite-url" readOnly value={inviteUrl} className="input input-mono" />
            <button
              type="button"
              className="btn"
              onClick={() => void copy(inviteUrl, 'Invite URL')}
            >
              Copy URL
            </button>
          </div>
        )}

        {isOwner && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-slate-700">Recent invites</h3>
            {invitesQuery.isLoading && <p className="text-sm text-slate-500">Loading invites…</p>}
            {invitesQuery.data && invitesQuery.data.length === 0 && (
              <p className="text-sm text-slate-500">No invites created yet.</p>
            )}
            {invitesQuery.data && invitesQuery.data.length > 0 && (
              <ul className="divide-y divide-slate-200 rounded-md border border-slate-200 bg-white">
                {invitesQuery.data.map((invite) => (
                  <li
                    key={invite.invite_id}
                    className="flex items-center justify-between px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-medium">{invite.email}</p>
                      <p className="text-xs text-slate-500">
                        {formatClinicRole(invite.role)} · expires{' '}
                        {new Date(invite.expires_at).toLocaleString()}
                        {invite.accepted_at ? ' · accepted' : ''}
                        {invite.revoked_at ? ' · revoked' : ''}
                      </p>
                    </div>
                    {!invite.accepted_at && !invite.revoked_at && (
                      <button
                        type="button"
                        className="text-xs text-red-600 hover:underline"
                        onClick={() => revokeMutation.mutate(invite.invite_id)}
                        disabled={revokeMutation.isPending}
                      >
                        Revoke
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
