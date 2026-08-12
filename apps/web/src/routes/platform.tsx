import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';
import { useMemo, useState } from 'react';

import { auth } from '@/lib/auth';
import { type ApiError, fetchMe } from '@/lib/auth-api';
import {
  type PlatformClinic,
  type PlatformInviteCreated,
  type UsagePlan,
  platformApi,
} from '@/lib/platform-api';
import { requirePlatformAuth } from '@/lib/router-auth';

type Tab = 'clinics' | 'organizations' | 'users' | 'usage' | 'plans';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function usageStatusClass(status: string): string {
  if (status === 'over_limit') return 'text-red-700 bg-red-50';
  if (status === 'warning') return 'text-amber-800 bg-amber-50';
  return 'text-emerald-800 bg-emerald-50';
}

export const Route = createFileRoute('/platform')({
  beforeLoad: requirePlatformAuth,
  component: PlatformConsolePage,
});

function PlatformConsolePage() {
  const queryClient = useQueryClient();
  const isAdmin = auth.isPlatformAdmin();
  const [tab, setTab] = useState<Tab>('clinics');
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const meQuery = useQuery({ queryKey: ['auth', 'me'], queryFn: fetchMe });
  const clinicsQuery = useQuery({
    queryKey: ['platform', 'clinics'],
    queryFn: platformApi.listClinics,
  });
  const groupsQuery = useQuery({
    queryKey: ['platform', 'groups'],
    queryFn: platformApi.listGroups,
  });
  const usersQuery = useQuery({
    queryKey: ['platform', 'users'],
    queryFn: platformApi.listUsers,
  });
  const usageQuery = useQuery({
    queryKey: ['platform', 'usage'],
    queryFn: () => platformApi.listUsageClinics(),
  });
  const plansQuery = useQuery({
    queryKey: ['platform', 'usage-plans'],
    queryFn: platformApi.listUsagePlans,
  });
  const infraCostsQuery = useQuery({
    queryKey: ['platform', 'infra-costs'],
    queryFn: () => platformApi.listInfraCosts(),
    enabled: isAdmin && tab === 'plans',
  });

  const [clinicName, setClinicName] = useState('');
  const [clinicSlug, setClinicSlug] = useState('');
  const [clinicAddress, setClinicAddress] = useState('');
  const [clinicGroupId, setClinicGroupId] = useState('');
  const [groupName, setGroupName] = useState('');
  const [groupOwnerId, setGroupOwnerId] = useState('');
  const [inviteClinicId, setInviteClinicId] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'owner' | 'dentist' | 'receptionist'>('owner');
  const [inviteResult, setInviteResult] = useState<PlatformInviteCreated | null>(null);
  const [selectedUsageClinicId, setSelectedUsageClinicId] = useState<string | null>(null);
  const [planName, setPlanName] = useState('');
  const [planMediaGb, setPlanMediaGb] = useState('5');
  const [planDbMb, setPlanDbMb] = useState('256');
  const [assignPlanClinicId, setAssignPlanClinicId] = useState('');
  const [assignPlanId, setAssignPlanId] = useState('');
  const [reconcileResult, setReconcileResult] = useState<{
    db_media_bytes: number;
    s3_bytes: number;
    s3_object_count: number;
    delta_bytes: number;
  } | null>(null);
  const [infraCostClinicId, setInfraCostClinicId] = useState('');
  const [infraCostStart, setInfraCostStart] = useState('');
  const [infraCostEnd, setInfraCostEnd] = useState('');
  const [infraCostRupees, setInfraCostRupees] = useState('');
  const [infraCostNotes, setInfraCostNotes] = useState('');

  const createClinicMutation = useMutation({
    mutationFn: () =>
      platformApi.createClinic({
        name: clinicName,
        slug: clinicSlug,
        address: clinicAddress || null,
        group_id: clinicGroupId || null,
      }),
    onSuccess: () => {
      setToast('Clinic created.');
      setClinicName('');
      setClinicSlug('');
      setClinicAddress('');
      setClinicGroupId('');
      void queryClient.invalidateQueries({ queryKey: ['platform', 'clinics'] });
    },
    onError: (err: ApiError) => setError(err.message),
  });

  const createGroupMutation = useMutation({
    mutationFn: () => platformApi.createGroup({ name: groupName, owner_user_id: groupOwnerId }),
    onSuccess: () => {
      setToast('Organization created.');
      setGroupName('');
      setGroupOwnerId('');
      void queryClient.invalidateQueries({ queryKey: ['platform', 'groups'] });
    },
    onError: (err: ApiError) => setError(err.message),
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      platformApi.createClinicInvite(inviteClinicId, {
        email: inviteEmail,
        role: inviteRole,
      }),
    onSuccess: (data) => {
      setInviteResult(data);
      setToast('Clinic invite created.');
    },
    onError: (err: ApiError) => setError(err.message),
  });

  const toggleUserMutation = useMutation({
    mutationFn: (args: { userId: string; isActive: boolean }) =>
      platformApi.updateUser(args.userId, { is_active: args.isActive }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['platform', 'users'] });
    },
    onError: (err: ApiError) => setError(err.message),
  });

  const recomputeMutation = useMutation({
    mutationFn: () => platformApi.recomputeUsage(),
    onSuccess: (data) => {
      setToast(`Usage snapshotted for ${data.clinics_processed} clinics.`);
      void queryClient.invalidateQueries({ queryKey: ['platform', 'usage'] });
    },
    onError: (err: ApiError) => setError(err.message),
  });

  const createPlanMutation = useMutation({
    mutationFn: () =>
      platformApi.createUsagePlan({
        name: planName,
        included_media_bytes: Math.round(Number.parseFloat(planMediaGb) * 1024 * 1024 * 1024),
        included_db_bytes: Math.round(Number.parseFloat(planDbMb) * 1024 * 1024),
      }),
    onSuccess: () => {
      setToast('Usage plan created.');
      setPlanName('');
      void queryClient.invalidateQueries({ queryKey: ['platform', 'usage-plans'] });
    },
    onError: (err: ApiError) => setError(err.message),
  });

  const assignPlanMutation = useMutation({
    mutationFn: () => platformApi.assignClinicPlan(assignPlanClinicId, { plan_id: assignPlanId }),
    onSuccess: () => {
      setToast('Plan assigned to clinic.');
      void queryClient.invalidateQueries({ queryKey: ['platform', 'usage'] });
    },
    onError: (err: ApiError) => setError(err.message),
  });

  const usageDetailQuery = useQuery({
    queryKey: ['platform', 'usage', selectedUsageClinicId],
    queryFn: () => {
      const clinicId = selectedUsageClinicId;
      if (!clinicId) {
        return Promise.reject(new Error('No clinic selected'));
      }
      return platformApi.getUsageClinic(clinicId);
    },
    enabled: Boolean(selectedUsageClinicId),
  });

  const usageHistoryQuery = useQuery({
    queryKey: ['platform', 'usage', selectedUsageClinicId, 'history'],
    queryFn: () => {
      const clinicId = selectedUsageClinicId;
      if (!clinicId) {
        return Promise.reject(new Error('No clinic selected'));
      }
      return platformApi.getUsageHistory(clinicId);
    },
    enabled: Boolean(selectedUsageClinicId),
  });

  const reconcileMutation = useMutation({
    mutationFn: (clinicId: string) => platformApi.reconcileS3(clinicId),
    onSuccess: (data) => {
      setReconcileResult(data);
      setToast('S3 reconciliation complete.');
      void queryClient.invalidateQueries({ queryKey: ['platform', 'usage'] });
    },
    onError: (err: ApiError) => setError(err.message),
  });

  const createInfraCostMutation = useMutation({
    mutationFn: () =>
      platformApi.createInfraCost({
        clinic_id: infraCostClinicId,
        period_start: infraCostStart,
        period_end: infraCostEnd,
        cost_paise: Math.round(Number.parseFloat(infraCostRupees) * 100),
        notes: infraCostNotes || null,
      }),
    onSuccess: () => {
      setToast('Infra cost recorded.');
      setInfraCostRupees('');
      setInfraCostNotes('');
      void queryClient.invalidateQueries({ queryKey: ['platform', 'infra-costs'] });
    },
    onError: (err: ApiError) => setError(err.message),
  });

  const tabLabels: Record<Tab, string> = {
    clinics: 'Clinics',
    organizations: 'Organizations',
    users: 'Users',
    usage: 'Usage',
    plans: 'Plans',
  };

  const roleLabel = useMemo(() => {
    const role = meQuery.data?.system_role ?? auth.getSystemRole();
    if (role === 'platform_admin') return 'Platform admin';
    if (role === 'platform_support') return 'Platform support (read-only)';
    return 'Platform';
  }, [meQuery.data?.system_role]);

  const inviteUrl = inviteResult
    ? `${window.location.origin}/signup?token=${encodeURIComponent(inviteResult.invite_token)}&email=${encodeURIComponent(inviteResult.email)}`
    : '';

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Platform console</h1>
        <p className="mt-1 text-sm text-slate-600">
          Manage organizations, clinics, and users. No patient clinical data is available here.
        </p>
        <p className="mt-2 text-xs text-slate-500">
          Signed in as {meQuery.data?.user.email ?? '…'} · {roleLabel}
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        {(['clinics', 'organizations', 'users', 'usage', 'plans'] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            className={tab === t ? 'btn btn-primary' : 'btn'}
            onClick={() => {
              setTab(t);
              setError(null);
            }}
          >
            {tabLabels[t]}
          </button>
        ))}
      </div>

      {toast && <p className="text-sm text-emerald-700">{toast}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {tab === 'clinics' && (
        <div className="space-y-4">
          {isAdmin && (
            <section className="card space-y-3">
              <h2 className="text-lg font-semibold">Create clinic</h2>
              <form
                className="grid gap-3 md:grid-cols-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  setError(null);
                  createClinicMutation.mutate();
                }}
              >
                <label className="block text-sm">
                  <span className="font-medium">Name</span>
                  <input
                    className="input mt-1 w-full"
                    value={clinicName}
                    onChange={(e) => setClinicName(e.target.value)}
                    required
                  />
                </label>
                <label className="block text-sm">
                  <span className="font-medium">Slug</span>
                  <input
                    className="input mt-1 w-full"
                    value={clinicSlug}
                    onChange={(e) => setClinicSlug(e.target.value)}
                    placeholder="sunshine-dental"
                    required
                  />
                </label>
                <label className="block text-sm md:col-span-2">
                  <span className="font-medium">Address</span>
                  <input
                    className="input mt-1 w-full"
                    value={clinicAddress}
                    onChange={(e) => setClinicAddress(e.target.value)}
                  />
                </label>
                <label className="block text-sm md:col-span-2">
                  <span className="font-medium">Organization (optional)</span>
                  <select
                    className="input mt-1 w-full"
                    value={clinicGroupId}
                    onChange={(e) => setClinicGroupId(e.target.value)}
                  >
                    <option value="">Standalone clinic (no organization)</option>
                    {groupsQuery.data?.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.name}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="submit"
                  className="btn btn-primary md:col-span-2"
                  disabled={createClinicMutation.isPending}
                >
                  Create clinic
                </button>
              </form>
            </section>
          )}

          <section className="card space-y-3">
            <h2 className="text-lg font-semibold">Clinics</h2>
            {clinicsQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
            {clinicsQuery.data && clinicsQuery.data.length === 0 && (
              <p className="text-sm text-slate-500">No clinics yet.</p>
            )}
            {clinicsQuery.data && clinicsQuery.data.length > 0 && (
              <ul className="divide-y divide-slate-200">
                {clinicsQuery.data.map((c) => (
                  <ClinicRow key={c.id} clinic={c} />
                ))}
              </ul>
            )}
          </section>

          {isAdmin && (
            <section className="card space-y-3">
              <h2 className="text-lg font-semibold">Invite clinic owner</h2>
              <form
                className="grid gap-3 md:grid-cols-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  setError(null);
                  inviteMutation.mutate();
                }}
              >
                <label className="block text-sm md:col-span-2">
                  <span className="font-medium">Clinic</span>
                  <select
                    className="input mt-1 w-full"
                    value={inviteClinicId}
                    onChange={(e) => setInviteClinicId(e.target.value)}
                    required
                  >
                    <option value="">Select clinic…</option>
                    {clinicsQuery.data?.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.slug})
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  <span className="font-medium">Email</span>
                  <input
                    type="email"
                    className="input mt-1 w-full"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    required
                  />
                </label>
                <label className="block text-sm">
                  <span className="font-medium">Role</span>
                  <select
                    className="input mt-1 w-full"
                    value={inviteRole}
                    onChange={(e) =>
                      setInviteRole(e.target.value as 'owner' | 'dentist' | 'receptionist')
                    }
                  >
                    <option value="owner">Owner</option>
                    <option value="dentist">Dentist</option>
                    <option value="receptionist">Receptionist</option>
                  </select>
                </label>
                <button
                  type="submit"
                  className="btn btn-primary md:col-span-2"
                  disabled={inviteMutation.isPending || !inviteClinicId}
                >
                  Create invite
                </button>
              </form>
              {inviteResult && (
                <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs">
                  <p className="font-medium">Invite URL</p>
                  <p className="mt-1 break-all font-mono">{inviteUrl}</p>
                </div>
              )}
            </section>
          )}
        </div>
      )}

      {tab === 'organizations' && (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            An organization is a parent chain (e.g. &quot;ABC Dental Group&quot;) that can own
            multiple clinic locations. Use this when one business runs several branches. For a
            single clinic, skip this and create the clinic directly under the Clinics tab.
          </p>
          {isAdmin && (
            <section className="card space-y-3">
              <h2 className="text-lg font-semibold">Create organization</h2>
              <form
                className="grid gap-3 md:grid-cols-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  setError(null);
                  createGroupMutation.mutate();
                }}
              >
                <label className="block text-sm">
                  <span className="font-medium">Name</span>
                  <input
                    className="input mt-1 w-full"
                    value={groupName}
                    onChange={(e) => setGroupName(e.target.value)}
                    required
                  />
                </label>
                <label className="block text-sm">
                  <span className="font-medium">Chain owner (existing user)</span>
                  <select
                    className="input mt-1 w-full"
                    value={groupOwnerId}
                    onChange={(e) => setGroupOwnerId(e.target.value)}
                    required
                  >
                    <option value="">Select user…</option>
                    {usersQuery.data?.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name ?? u.email} ({u.email})
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-slate-500">
                    Must be an existing account from the Users tab (not an email address).
                  </p>
                </label>
                <button
                  type="submit"
                  className="btn btn-primary md:col-span-2"
                  disabled={createGroupMutation.isPending || !groupName.trim() || !groupOwnerId}
                >
                  Create organization
                </button>
              </form>
            </section>
          )}
          <section className="card">
            <h2 className="text-lg font-semibold">Organizations</h2>
            {groupsQuery.isLoading && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
            {groupsQuery.data && groupsQuery.data.length === 0 && (
              <p className="mt-2 text-sm text-slate-500">None yet.</p>
            )}
            {groupsQuery.data && groupsQuery.data.length > 0 && (
              <ul className="mt-3 divide-y divide-slate-200">
                {groupsQuery.data.map((g) => (
                  <li key={g.id} className="py-2 text-sm">
                    <p className="font-medium">{g.name}</p>
                    <p className="text-xs text-slate-500 font-mono">
                      {g.id} · owner {g.owner_user_id}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}

      {tab === 'users' && (
        <section className="card">
          <h2 className="text-lg font-semibold">Users</h2>
          {usersQuery.isLoading && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
          {usersQuery.isError && (
            <p className="mt-2 text-sm text-red-600">
              Failed to load users. Try refreshing the page.
            </p>
          )}
          {usersQuery.data && usersQuery.data.length === 0 && (
            <p className="mt-2 text-sm text-slate-500">No users found.</p>
          )}
          {usersQuery.data && usersQuery.data.length > 0 && (
            <ul className="mt-3 divide-y divide-slate-200">
              {usersQuery.data.map((u) => (
                <li key={u.id} className="flex items-center justify-between gap-4 py-2 text-sm">
                  <div>
                    <p className="font-medium">{u.full_name ?? u.email}</p>
                    <p className="text-xs text-slate-500">
                      {u.email}
                      {u.system_role ? ` · ${u.system_role}` : ''}
                      {!u.is_active ? ' · inactive' : ''}
                    </p>
                  </div>
                  {isAdmin && (
                    <button
                      type="button"
                      className="btn text-xs"
                      onClick={() =>
                        toggleUserMutation.mutate({
                          userId: u.id,
                          isActive: !u.is_active,
                        })
                      }
                    >
                      {u.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === 'usage' && (
        <div className="space-y-4">
          <section className="card space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-semibold">Clinic usage</h2>
              <div className="flex flex-wrap gap-2">
                {isAdmin && (
                  <button
                    type="button"
                    className="btn btn-primary text-sm"
                    disabled={recomputeMutation.isPending}
                    onClick={() => recomputeMutation.mutate()}
                  >
                    Snapshot now
                  </button>
                )}
                <button
                  type="button"
                  className="btn text-sm"
                  onClick={async () => {
                    try {
                      const blob = await platformApi.exportUsageCsv();
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = 'clinic-usage-export.csv';
                      link.click();
                      URL.revokeObjectURL(url);
                    } catch (err) {
                      setError(err instanceof Error ? err.message : 'Export failed.');
                    }
                  }}
                >
                  Export CSV
                </button>
              </div>
            </div>
            {usageQuery.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
            {usageQuery.data && usageQuery.data.items.length === 0 && (
              <p className="text-sm text-slate-500">No clinics yet.</p>
            )}
            {usageQuery.data && usageQuery.data.items.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs text-slate-500">
                      <th className="py-2 pr-3">Clinic</th>
                      <th className="py-2 pr-3">Media</th>
                      <th className="py-2 pr-3">Images</th>
                      <th className="py-2 pr-3">Patients</th>
                      <th className="py-2 pr-3">Visits</th>
                      <th className="py-2 pr-3">Members</th>
                      <th className="py-2 pr-3">DB est.</th>
                      <th className="py-2 pr-3">Plan</th>
                      <th className="py-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usageQuery.data.items.map((row) => (
                      <tr
                        key={row.clinic_id}
                        className="border-b border-slate-100 hover:bg-slate-50"
                      >
                        <td className="py-2 pr-3">
                          <button
                            type="button"
                            className="text-left"
                            onClick={() => {
                              setSelectedUsageClinicId(row.clinic_id);
                              setReconcileResult(null);
                            }}
                          >
                            <p className="font-medium">{row.clinic_name}</p>
                            <p className="text-xs text-slate-500 font-mono">{row.clinic_slug}</p>
                          </button>
                        </td>
                        <td className="py-2 pr-3">{formatBytes(row.media_bytes)}</td>
                        <td className="py-2 pr-3">{row.media_count}</td>
                        <td className="py-2 pr-3">{row.patients_count}</td>
                        <td className="py-2 pr-3">{row.visits_count}</td>
                        <td className="py-2 pr-3">{row.members_count}</td>
                        <td className="py-2 pr-3">{formatBytes(row.db_bytes_estimated)}</td>
                        <td className="py-2 pr-3 text-xs">{row.plan_name ?? '—'}</td>
                        <td className="py-2">
                          <span
                            className={`rounded px-2 py-0.5 text-xs ${usageStatusClass(row.status)}`}
                          >
                            {row.status.replace('_', ' ')}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {selectedUsageClinicId && usageDetailQuery.data && (
            <section className="card space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">{usageDetailQuery.data.clinic_name}</h2>
                <button
                  type="button"
                  className="btn text-xs"
                  onClick={() => setSelectedUsageClinicId(null)}
                >
                  Close
                </button>
              </div>
              {usageDetailQuery.data.plan_name && (
                <p className="text-sm text-slate-600">
                  Plan: {usageDetailQuery.data.plan_name}
                  {usageDetailQuery.data.media_usage_pct != null &&
                    ` · Media ${usageDetailQuery.data.media_usage_pct}% of included`}
                  {usageDetailQuery.data.included_media_bytes != null &&
                    ` · Included ${formatBytes(usageDetailQuery.data.included_media_bytes)} media`}
                </p>
              )}
              {usageHistoryQuery.data && usageHistoryQuery.data.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium">30-day trend</h3>
                  <ul className="mt-1 text-sm text-slate-600">
                    {usageHistoryQuery.data.slice(-7).map((point) => (
                      <li key={point.snapshot_date}>
                        {point.snapshot_date}: {formatBytes(point.media_bytes)} media ·{' '}
                        {point.patients_count} patients · {point.visits_count} visits
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {usageDetailQuery.data.media_by_kind.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium">Media by type</h3>
                  <ul className="mt-1 text-sm text-slate-600">
                    {usageDetailQuery.data.media_by_kind.map((m) => (
                      <li key={m.kind}>
                        {m.kind}: {m.count} files · {formatBytes(m.bytes)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {Object.keys(usageDetailQuery.data.usage_events_30d).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium">Events (30 days)</h3>
                  <ul className="mt-1 text-sm text-slate-600">
                    {Object.entries(usageDetailQuery.data.usage_events_30d).map(([k, v]) => (
                      <li key={k}>
                        {k}: {v}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {usageDetailQuery.data.s3_bytes_reconciled != null && (
                <p className="text-sm text-slate-600">
                  Last S3 reconcile: {formatBytes(usageDetailQuery.data.s3_bytes_reconciled)} (
                  {usageDetailQuery.data.s3_bytes_reconciled - usageDetailQuery.data.media_bytes >=
                  0
                    ? '+'
                    : ''}
                  {formatBytes(
                    usageDetailQuery.data.s3_bytes_reconciled - usageDetailQuery.data.media_bytes,
                  )}{' '}
                  vs DB)
                </p>
              )}
              {isAdmin && selectedUsageClinicId && (
                <button
                  type="button"
                  className="btn text-xs"
                  disabled={reconcileMutation.isPending}
                  onClick={() => reconcileMutation.mutate(selectedUsageClinicId)}
                >
                  Reconcile S3 storage
                </button>
              )}
              {reconcileResult && (
                <p className="text-sm text-slate-600">
                  S3: {formatBytes(reconcileResult.s3_bytes)} across{' '}
                  {reconcileResult.s3_object_count} objects · DB:{' '}
                  {formatBytes(reconcileResult.db_media_bytes)} · Delta:{' '}
                  {formatBytes(reconcileResult.delta_bytes)}
                </p>
              )}
            </section>
          )}
        </div>
      )}

      {tab === 'plans' && isAdmin && (
        <div className="space-y-4">
          <section className="card space-y-3">
            <h2 className="text-lg font-semibold">Create usage plan</h2>
            <form
              className="grid gap-3 md:grid-cols-3"
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                createPlanMutation.mutate();
              }}
            >
              <label className="block text-sm">
                <span className="font-medium">Name</span>
                <input
                  className="input mt-1 w-full"
                  value={planName}
                  onChange={(e) => setPlanName(e.target.value)}
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium">Included media (GB)</span>
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  className="input mt-1 w-full"
                  value={planMediaGb}
                  onChange={(e) => setPlanMediaGb(e.target.value)}
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium">Included DB (MB)</span>
                <input
                  type="number"
                  min="0"
                  className="input mt-1 w-full"
                  value={planDbMb}
                  onChange={(e) => setPlanDbMb(e.target.value)}
                  required
                />
              </label>
              <button
                type="submit"
                className="btn btn-primary md:col-span-3"
                disabled={createPlanMutation.isPending}
              >
                Create plan
              </button>
            </form>
          </section>

          <section className="card space-y-3">
            <h2 className="text-lg font-semibold">Assign plan to clinic</h2>
            <form
              className="grid gap-3 md:grid-cols-2"
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                assignPlanMutation.mutate();
              }}
            >
              <label className="block text-sm">
                <span className="font-medium">Clinic</span>
                <select
                  className="input mt-1 w-full"
                  value={assignPlanClinicId}
                  onChange={(e) => setAssignPlanClinicId(e.target.value)}
                  required
                >
                  <option value="">Select clinic…</option>
                  {clinicsQuery.data?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="font-medium">Plan</span>
                <select
                  className="input mt-1 w-full"
                  value={assignPlanId}
                  onChange={(e) => setAssignPlanId(e.target.value)}
                  required
                >
                  <option value="">Select plan…</option>
                  {plansQuery.data?.map((p: UsagePlan) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({formatBytes(p.included_media_bytes)} media)
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="submit"
                className="btn btn-primary md:col-span-2"
                disabled={assignPlanMutation.isPending}
              >
                Assign plan
              </button>
            </form>
          </section>

          <section className="card">
            <h2 className="text-lg font-semibold">Plans</h2>
            {plansQuery.data && plansQuery.data.length === 0 && (
              <p className="mt-2 text-sm text-slate-500">No plans yet.</p>
            )}
            {plansQuery.data && plansQuery.data.length > 0 && (
              <ul className="mt-3 divide-y divide-slate-200 text-sm">
                {plansQuery.data.map((p: UsagePlan) => (
                  <li key={p.id} className="py-2">
                    <p className="font-medium">{p.name}</p>
                    <p className="text-xs text-slate-500">
                      Media {formatBytes(p.included_media_bytes)} · DB{' '}
                      {formatBytes(p.included_db_bytes)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card space-y-3">
            <h2 className="text-lg font-semibold">Import infra cost</h2>
            <p className="text-sm text-slate-600">
              Record monthly infra spend per clinic for billing reconciliation.
            </p>
            <form
              className="grid gap-3 md:grid-cols-2"
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                createInfraCostMutation.mutate();
              }}
            >
              <label className="block text-sm md:col-span-2">
                <span className="font-medium">Clinic</span>
                <select
                  className="input mt-1 w-full"
                  value={infraCostClinicId}
                  onChange={(e) => setInfraCostClinicId(e.target.value)}
                  required
                >
                  <option value="">Select clinic…</option>
                  {clinicsQuery.data?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="font-medium">Period start</span>
                <input
                  type="date"
                  className="input mt-1 w-full"
                  value={infraCostStart}
                  onChange={(e) => setInfraCostStart(e.target.value)}
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium">Period end</span>
                <input
                  type="date"
                  className="input mt-1 w-full"
                  value={infraCostEnd}
                  onChange={(e) => setInfraCostEnd(e.target.value)}
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium">Cost (INR)</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  className="input mt-1 w-full"
                  value={infraCostRupees}
                  onChange={(e) => setInfraCostRupees(e.target.value)}
                  required
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium">Notes</span>
                <input
                  className="input mt-1 w-full"
                  value={infraCostNotes}
                  onChange={(e) => setInfraCostNotes(e.target.value)}
                  placeholder="Optional"
                />
              </label>
              <button
                type="submit"
                className="btn btn-primary md:col-span-2"
                disabled={createInfraCostMutation.isPending}
              >
                Record cost
              </button>
            </form>
            {infraCostsQuery.data && infraCostsQuery.data.length > 0 && (
              <ul className="divide-y divide-slate-200 text-sm">
                {infraCostsQuery.data.slice(0, 10).map((row) => (
                  <li key={row.id} className="py-2">
                    <p className="font-medium font-mono text-xs">{row.clinic_id}</p>
                    <p className="text-slate-600">
                      {row.period_start} → {row.period_end}: ₹{(row.cost_paise / 100).toFixed(2)}
                      {row.notes ? ` · ${row.notes}` : ''}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}

      {tab === 'plans' && !isAdmin && (
        <p className="text-sm text-slate-600">Plans are managed by platform admins only.</p>
      )}
    </div>
  );
}

function ClinicRow({ clinic }: { clinic: PlatformClinic }) {
  return (
    <li className="py-3 text-sm">
      <p className="font-medium">{clinic.name}</p>
      <p className="text-xs text-slate-500">
        <span className="font-mono">{clinic.slug}</span> · {clinic.id}
      </p>
      {clinic.address && <p className="text-xs text-slate-500">{clinic.address}</p>}
    </li>
  );
}
