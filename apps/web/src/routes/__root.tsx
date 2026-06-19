import type { QueryClient } from '@tanstack/react-query';
import { Link, Outlet, createRootRouteWithContext, useNavigate } from '@tanstack/react-router';
import { LayoutDashboard, LogOut, Shield, Stethoscope, UserCog, Users } from 'lucide-react';

import { auth, getAuthVersion, subscribeAuth } from '@/lib/auth';
import { fetchMe, logout } from '@/lib/auth-api';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useSyncExternalStore } from 'react';

interface RootContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RootContext>()({
  component: RootLayout,
});

function RootLayout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  // Re-render the shell whenever the session changes (login, logout, clinic
  // switch, or another tab) so the nav never shows a stale auth state.
  useSyncExternalStore(subscribeAuth, getAuthVersion, getAuthVersion);
  const signedIn = auth.isAuthenticated();
  const meQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: fetchMe,
    enabled: signedIn,
  });
  const isPlatform = auth.isPlatformOperator();
  const hasClinic = Boolean(auth.getClinicId());
  const email = meQuery.data?.user.email;
  const initial = (email ?? '?').slice(0, 1).toUpperCase();

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/" className="group flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient text-white shadow-glow transition-transform group-hover:scale-105">
              <Stethoscope className="h-5 w-5" />
            </span>
            <span className="text-lg font-bold tracking-tight">
              <span className="gradient-text">clinic</span>
              <span className="text-slate-900">-crm</span>
            </span>
          </Link>
          <nav className="flex items-center gap-1 text-sm">
            {signedIn ? (
              <>
                {isPlatform && (
                  <Link
                    to="/platform"
                    className="nav-link inline-flex items-center gap-1.5"
                    activeProps={{
                      className:
                        'nav-link inline-flex items-center gap-1.5 bg-brand-50 text-brand-700',
                    }}
                  >
                    <Shield className="h-4 w-4" />
                    <span className="hidden sm:inline">Platform</span>
                  </Link>
                )}
                {(!isPlatform || hasClinic) && (
                  <>
                    <Link
                      to="/"
                      className="nav-link inline-flex items-center gap-1.5"
                      activeProps={{
                        className:
                          'nav-link inline-flex items-center gap-1.5 bg-brand-50 text-brand-700',
                      }}
                    >
                      <LayoutDashboard className="h-4 w-4" />
                      <span className="hidden sm:inline">Dashboard</span>
                    </Link>
                    <Link
                      to="/patients"
                      className="nav-link inline-flex items-center gap-1.5"
                      activeProps={{
                        className:
                          'nav-link inline-flex items-center gap-1.5 bg-brand-50 text-brand-700',
                      }}
                    >
                      <Users className="h-4 w-4" />
                      <span className="hidden sm:inline">Patients</span>
                    </Link>
                    <Link
                      to="/settings/team"
                      className="nav-link inline-flex items-center gap-1.5"
                      activeProps={{
                        className:
                          'nav-link inline-flex items-center gap-1.5 bg-brand-50 text-brand-700',
                      }}
                    >
                      <UserCog className="h-4 w-4" />
                      <span className="hidden sm:inline">Team</span>
                    </Link>
                  </>
                )}
                <Link
                  to="/settings/security"
                  className="nav-link inline-flex items-center gap-1.5"
                  activeProps={{
                    className:
                      'nav-link inline-flex items-center gap-1.5 bg-brand-50 text-brand-700',
                  }}
                >
                  <Shield className="h-4 w-4" />
                  <span className="hidden sm:inline">Security</span>
                </Link>
                {email && (
                  <span className="ml-2 hidden items-center gap-2 rounded-full border border-slate-200 bg-white py-1 pl-1 pr-3 shadow-soft md:inline-flex">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-gradient text-xs font-bold text-white">
                      {initial}
                    </span>
                    <span className="max-w-[14rem] truncate text-xs text-slate-600">{email}</span>
                  </span>
                )}
                <button
                  type="button"
                  className="btn btn-ghost ml-1 px-2.5 py-1.5"
                  onClick={() => {
                    logout();
                    queryClient.clear();
                    navigate({ to: '/login' });
                  }}
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Sign out</span>
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="nav-link">
                  Sign in
                </Link>
                <Link to="/signup" className="btn btn-primary px-4 py-1.5">
                  Sign up
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 animate-fade-in px-6 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200/70 bg-white/60 py-5 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-6 text-xs text-slate-500 sm:flex-row">
          <span className="flex items-center gap-1.5">
            <Stethoscope className="h-3.5 w-3.5 text-brand" />
            clinic-crm — DPDP-aligned dental CRM
          </span>
          <span className="text-slate-400">Secure · multi-tenant · audit-logged</span>
        </div>
      </footer>
    </div>
  );
}
