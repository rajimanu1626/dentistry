import type { QueryClient } from '@tanstack/react-query';
import { Link, Outlet, createRootRouteWithContext, useNavigate } from '@tanstack/react-router';

import { auth } from '@/lib/auth';
import { fetchMe, logout } from '@/lib/auth-api';
import { useQuery } from '@tanstack/react-query';

interface RootContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RootContext>()({
  component: RootLayout,
});

function RootLayout() {
  const navigate = useNavigate();
  const signedIn = auth.isAuthenticated();
  const meQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: fetchMe,
    enabled: signedIn,
  });
  const isPlatform = auth.isPlatformOperator();
  const hasClinic = Boolean(auth.getClinicId());

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-lg font-semibold text-brand">
            clinic-crm
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            {signedIn ? (
              <>
                {isPlatform && (
                  <Link
                    to="/platform"
                    className="hover:text-brand"
                    activeProps={{ className: 'text-brand font-medium' }}
                  >
                    Platform
                  </Link>
                )}
                {(!isPlatform || hasClinic) && (
                  <>
                    <Link
                      to="/"
                      className="hover:text-brand"
                      activeProps={{ className: 'text-brand font-medium' }}
                    >
                      Dashboard
                    </Link>
                    <Link
                      to="/patients"
                      className="hover:text-brand"
                      activeProps={{ className: 'text-brand font-medium' }}
                    >
                      Patients
                    </Link>
                    <Link
                      to="/settings/team"
                      className="hover:text-brand"
                      activeProps={{ className: 'text-brand font-medium' }}
                    >
                      Team
                    </Link>
                  </>
                )}
                <Link
                  to="/settings/security"
                  className="hover:text-brand"
                  activeProps={{ className: 'text-brand font-medium' }}
                >
                  Security
                </Link>
                {meQuery.data?.user.email && (
                  <span className="hidden text-slate-500 sm:inline">{meQuery.data.user.email}</span>
                )}
                <button
                  type="button"
                  className="text-slate-600 hover:text-brand"
                  onClick={() => {
                    logout();
                    navigate({ to: '/login' });
                  }}
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="hover:text-brand">
                  Sign in
                </Link>
                <Link to="/signup" className="hover:text-brand">
                  Sign up
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
        clinic-crm — DPDP-aligned dental CRM
      </footer>
    </div>
  );
}
