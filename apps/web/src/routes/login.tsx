import { useMutation } from '@tanstack/react-query';
import { Link, createFileRoute, useNavigate } from '@tanstack/react-router';
import { LogIn, Stethoscope } from 'lucide-react';
import { useState } from 'react';

import { type ApiError, defaultHomePath, login } from '@/lib/auth-api';
import { redirectIfAuthenticated } from '@/lib/router-auth';

type LoginSearch = {
  redirect?: string;
};

export const Route = createFileRoute('/login')({
  validateSearch: (search: Record<string, unknown>): LoginSearch => ({
    redirect: typeof search.redirect === 'string' ? search.redirect : undefined,
  }),
  beforeLoad: () => redirectIfAuthenticated(),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const { redirect } = Route.useSearch();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => login({ email, password }),
    onSuccess: (me) => {
      const fallback = defaultHomePath(me);
      navigate({ to: redirect ?? fallback });
    },
    onError: (err: ApiError) => {
      setError(err.message);
    },
  });

  return (
    <div className="mx-auto max-w-md animate-fade-in-up space-y-6 py-6">
      <header className="text-center">
        <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-gradient text-white shadow-glow">
          <Stethoscope className="h-7 w-7" />
        </span>
        <h1 className="mt-4 text-2xl font-bold tracking-tight">Welcome back</h1>
        <p className="mt-1 text-sm text-slate-500">Sign in to access your clinic workspace.</p>
      </header>

      <form
        className="card space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          mutation.mutate();
        }}
      >
        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <label className="block text-sm">
          <span className="label">Email</span>
          <input
            type="email"
            required
            autoComplete="email"
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="label">Password</span>
          <input
            type="password"
            required
            autoComplete="current-password"
            className="input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit" className="btn btn-primary w-full" disabled={mutation.isPending}>
          <LogIn className="h-4 w-4" />
          {mutation.isPending ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="text-center text-sm text-slate-600">
        Need an account?{' '}
        <Link to="/signup" className="font-medium text-brand hover:underline">
          Sign up
        </Link>
      </p>
    </div>
  );
}
