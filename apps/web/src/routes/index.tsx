import { useQuery } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';
import { Activity, FileText, Image as ImageIcon, Share2, Users } from 'lucide-react';

import { apiClient } from '@/lib/api';
import { auth } from '@/lib/auth';
import { requireAuth } from '@/lib/router-auth';
import { Link, redirect } from '@tanstack/react-router';

interface Health {
  status: string;
  version: string;
  service: string;
}

export const Route = createFileRoute('/')({
  beforeLoad: () => {
    requireAuth();
    if (auth.isPlatformOperator() && !auth.getClinicId()) {
      throw redirect({ to: '/platform' });
    }
  },
  component: DashboardPage,
});

const features = [
  {
    icon: Users,
    title: 'Patients',
    desc: 'Encrypted clinical records, scoped per clinic.',
  },
  {
    icon: FileText,
    title: 'Prescriptions',
    desc: 'Template-driven Rx with printable PDFs.',
  },
  {
    icon: ImageIcon,
    title: 'Media',
    desc: 'Before / after / x-ray imaging in object storage.',
  },
  {
    icon: Share2,
    title: 'Sharing',
    desc: 'Internal grants and secure external handoffs.',
  },
];

function DashboardPage() {
  const { data, isLoading, error } = useQuery<Health>({
    queryKey: ['health'],
    queryFn: () => apiClient.get<Health>('/healthz'),
  });

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-3xl border border-slate-200/70 bg-brand-gradient p-8 text-white shadow-lift">
        <div className="absolute -right-10 -top-16 h-56 w-56 rounded-full bg-white/10 blur-2xl" />
        <div className="absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-white/10 blur-2xl" />
        <div className="relative">
          <p className="text-sm font-medium uppercase tracking-wider text-white/80">Dashboard</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight">
            Welcome to your clinic workspace
          </h1>
          <p className="mt-2 max-w-2xl text-white/85">
            A multi-tenant dental CRM for patients, prescriptions, media, and secure sharing — built
            privacy-first.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              to="/patients"
              className="btn bg-white px-5 font-semibold text-brand-700 shadow-soft hover:bg-white/90"
            >
              <Users className="h-4 w-4" />
              View patients
            </Link>
            <Link
              to="/patients/new"
              className="btn border border-white/40 bg-white/10 px-5 font-semibold text-white hover:bg-white/20"
            >
              New patient
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((f) => (
          <div key={f.title} className="card card-hover">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
              <f.icon className="h-5 w-5" />
            </span>
            <h3 className="mt-3 font-semibold text-slate-900">{f.title}</h3>
            <p className="mt-1 text-sm text-slate-500">{f.desc}</p>
          </div>
        ))}
      </section>

      <section className="card">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-brand" />
          <h2 className="section-title">API status</h2>
        </div>
        {isLoading && <p className="mt-3 text-sm text-slate-500">Checking API…</p>}
        {error && (
          <p className="mt-3 text-sm text-red-600">
            API unreachable. Make sure{' '}
            <code className="rounded bg-slate-100 px-1 font-mono">docker compose up</code> is
            running.
          </p>
        )}
        {data && (
          <dl className="mt-4 grid grid-cols-1 gap-4 text-sm sm:grid-cols-3">
            <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
              <dt className="section-title">Status</dt>
              <dd className="mt-1 flex items-center gap-2 font-semibold text-emerald-600">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
                </span>
                {data.status}
              </dd>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
              <dt className="section-title">Service</dt>
              <dd className="mt-1 font-medium text-slate-800">{data.service}</dd>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
              <dt className="section-title">Version</dt>
              <dd className="mt-1 font-mono text-slate-800">{data.version}</dd>
            </div>
          </dl>
        )}
      </section>
    </div>
  );
}
