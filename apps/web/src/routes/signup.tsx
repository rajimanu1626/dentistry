import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, createFileRoute, useNavigate } from '@tanstack/react-router';
import { Stethoscope, UserPlus } from 'lucide-react';
import { useMemo, useState } from 'react';

import { type ApiError, fetchAuthConfig, signup } from '@/lib/auth-api';
import { redirectIfAuthenticated } from '@/lib/router-auth';

type SignupSearch = {
  token?: string;
  email?: string;
};

export const Route = createFileRoute('/signup')({
  validateSearch: (search: Record<string, unknown>): SignupSearch => ({
    token: typeof search.token === 'string' ? search.token : undefined,
    email: typeof search.email === 'string' ? search.email : undefined,
  }),
  beforeLoad: () => redirectIfAuthenticated(),
  component: SignupPage,
});

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

function SignupPage() {
  const navigate = useNavigate();
  const { token: tokenFromUrl, email: emailFromUrl } = Route.useSearch();

  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['auth', 'config'],
    queryFn: fetchAuthConfig,
  });

  const [email, setEmail] = useState(emailFromUrl ?? '');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [inviteToken, setInviteToken] = useState(tokenFromUrl ?? '');
  const [clinicName, setClinicName] = useState('');
  const [clinicSlug, setClinicSlug] = useState('');
  const [error, setError] = useState<string | null>(null);

  const showClinicFields = config?.can_bootstrap_clinic ?? false;
  const requiresInvite = config?.requires_invite ?? false;

  const canSubmit = useMemo(() => {
    if (!config?.can_signup) return false;
    if (requiresInvite && !inviteToken.trim()) return false;
    if (showClinicFields && (!clinicName.trim() || !clinicSlug.trim())) return false;
    return true;
  }, [config, requiresInvite, inviteToken, showClinicFields, clinicName, clinicSlug]);

  const mutation = useMutation({
    mutationFn: () =>
      signup({
        email,
        password,
        full_name: fullName,
        invite_token: inviteToken.trim() || undefined,
        clinic_name: showClinicFields ? clinicName : undefined,
        clinic_slug: showClinicFields ? clinicSlug : undefined,
      }),
    onSuccess: () => navigate({ to: '/' }),
    onError: (err: ApiError) => setError(err.message),
  });

  if (configLoading) {
    return <p className="text-sm text-slate-500">Loading sign-up options…</p>;
  }

  if (config && !config.can_signup) {
    return (
      <div className="card mx-auto max-w-md space-y-3 text-center">
        <h1 className="text-xl font-semibold">Sign-up disabled</h1>
        <p className="text-sm text-slate-600">
          New accounts are invite-only. Contact your clinic administrator for access.
        </p>
        <Link to="/login" className="font-medium text-brand hover:underline">
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md animate-fade-in-up space-y-6 py-6">
      <header className="text-center">
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gradient text-white shadow-glow">
          <Stethoscope className="h-7 w-7" />
        </span>
        <h1 className="mt-4 text-2xl font-bold tracking-tight">Create account</h1>
        <p className="mt-1 text-sm text-slate-500">
          {requiresInvite
            ? 'Use the invite link or token from your clinic admin.'
            : showClinicFields
              ? 'Register the first clinic on this instance.'
              : 'Complete the form below.'}
        </p>
      </header>

      <form
        className="card space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!canSubmit) return;
          setError(null);
          mutation.mutate();
        }}
      >
        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {requiresInvite && (
          <label className="block text-sm">
            <span className="label">Invite token</span>
            <input
              type="text"
              required
              className="input font-mono text-xs"
              value={inviteToken}
              onChange={(e) => setInviteToken(e.target.value)}
              placeholder="Paste token from your invite email"
            />
          </label>
        )}

        <label className="block text-sm">
          <span className="label">Full name</span>
          <input
            type="text"
            required
            className="input"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="label">Email</span>
          <input
            type="email"
            required
            autoComplete="email"
            readOnly={Boolean(emailFromUrl)}
            className="input read-only:bg-slate-50"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="label">Password</span>
          <input
            type="password"
            required
            minLength={10}
            autoComplete="new-password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <span className="mt-1 block text-xs text-slate-500">At least 10 characters.</span>
        </label>

        {showClinicFields && (
          <>
            <label className="block text-sm">
              <span className="label">Clinic name</span>
              <input
                type="text"
                required
                className="input"
                value={clinicName}
                onChange={(e) => {
                  setClinicName(e.target.value);
                  if (!clinicSlug || clinicSlug === slugify(clinicName)) {
                    setClinicSlug(slugify(e.target.value));
                  }
                }}
              />
            </label>
            <label className="block text-sm">
              <span className="label">Clinic URL slug</span>
              <input
                type="text"
                required
                pattern="^[a-z0-9][a-z0-9\-]{1,79}$"
                className="input font-mono text-sm"
                value={clinicSlug}
                onChange={(e) => setClinicSlug(e.target.value)}
              />
            </label>
          </>
        )}

        <button
          type="submit"
          className="btn btn-primary w-full"
          disabled={mutation.isPending || !canSubmit}
        >
          <UserPlus className="h-4 w-4" />
          {mutation.isPending ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="text-center text-sm text-slate-600">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-brand hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
