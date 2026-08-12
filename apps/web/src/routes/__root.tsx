import type { QueryClient } from "@tanstack/react-query";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
	Link,
	Outlet,
	createRootRouteWithContext,
	useNavigate,
} from "@tanstack/react-router";
import { useEffect, useId, useRef, useState } from "react";

import { auth, useAuth } from "@/lib/auth";
import { fetchMe, logout } from "@/lib/auth-api";
import { displayUserName, formatClinicRole } from "@/lib/roles";

interface RootContext {
	queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RootContext>()({
	component: RootLayout,
});

function RootLayout() {
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const { isAuthenticated, isPlatformOperator, clinicId } = useAuth();
	const meQuery = useQuery({
		queryKey: ["auth", "me"],
		queryFn: fetchMe,
		enabled: isAuthenticated,
	});
	const hasClinic = Boolean(clinicId);

	// Keep active clinic in sync (needed for X-Clinic-Id on clinical APIs).
	useEffect(() => {
		const memberships = meQuery.data?.memberships;
		if (!memberships?.length) return;
		const stillValid = clinicId
			? memberships.some((m) => m.clinic_id === clinicId)
			: false;
		if (!stillValid) {
			auth.setClinicId(memberships[0].clinic_id);
		}
	}, [meQuery.data, clinicId]);

	const activeMembership = meQuery.data?.memberships.find(
		(m) => m.clinic_id === clinicId,
	);
	const userLabel = meQuery.data
		? displayUserName(meQuery.data.user.full_name, meQuery.data.user.email)
		: null;

	return (
		<div className="flex min-h-full flex-col">
			<header className="border-b border-slate-200 bg-white">
				<div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
					<div className="flex min-w-0 items-baseline gap-3">
						<Link
							to="/"
							className="shrink-0 font-display text-xl font-semibold tracking-tight text-brand"
						>
							Clinic Desk
						</Link>
						{activeMembership && (
							<span
								className="hidden truncate text-sm font-normal text-slate-500 sm:inline"
								title={activeMembership.clinic_name}
							>
								{activeMembership.clinic_name}
							</span>
						)}
					</div>
					<nav className="flex items-center gap-4 text-sm">
						{isAuthenticated ? (
							<>
								{isPlatformOperator && (
									<Link
										to="/platform"
										className="hover:text-brand"
										activeProps={{ className: "text-brand font-medium" }}
									>
										Platform
									</Link>
								)}
								{(!isPlatformOperator || hasClinic) && (
									<>
										<Link
											to="/"
											className="hover:text-brand"
											activeProps={{ className: "text-brand font-medium" }}
										>
											Dashboard
										</Link>
										<Link
											to="/patients"
											className="hover:text-brand"
											activeProps={{ className: "text-brand font-medium" }}
										>
											Patients
										</Link>
										<Link
											to="/settings/team"
											className="hover:text-brand"
											activeProps={{ className: "text-brand font-medium" }}
										>
											Team
										</Link>
									</>
								)}
								{userLabel && meQuery.data && (
									<UserMenu
										userLabel={userLabel}
										email={meQuery.data.user.email}
										roleLabel={
											activeMembership
												? formatClinicRole(activeMembership.role)
												: null
										}
										onSignOut={async () => {
											await logout();
											void queryClient.removeQueries({ queryKey: ["auth"] });
											await navigate({ to: "/login" });
										}}
									/>
								)}
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
			<footer className="border-t border-slate-200/80 bg-white/80 py-4 text-center text-xs text-slate-500 backdrop-blur-sm">
				Clinic Desk — DPDP-aligned dental clinic workspace
			</footer>
		</div>
	);
}

function UserMenu({
	userLabel,
	email,
	roleLabel,
	onSignOut,
}: {
	userLabel: string;
	email: string;
	roleLabel: string | null;
	onSignOut: () => Promise<void>;
}) {
	const [open, setOpen] = useState(false);
	const menuId = useId();
	const rootRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (!open) return;
		function onPointerDown(event: MouseEvent) {
			if (!rootRef.current?.contains(event.target as Node)) {
				setOpen(false);
			}
		}
		function onKeyDown(event: KeyboardEvent) {
			if (event.key === "Escape") setOpen(false);
		}
		document.addEventListener("mousedown", onPointerDown);
		document.addEventListener("keydown", onKeyDown);
		return () => {
			document.removeEventListener("mousedown", onPointerDown);
			document.removeEventListener("keydown", onKeyDown);
		};
	}, [open]);

	return (
		<div className="relative" ref={rootRef}>
			<button
				type="button"
				className="rounded-md px-2 py-1 font-medium text-slate-800 hover:bg-slate-50 hover:text-brand"
				aria-haspopup="menu"
				aria-expanded={open}
				aria-controls={menuId}
				onClick={() => setOpen((v) => !v)}
			>
				{userLabel}
			</button>
			{open && (
				<div
					id={menuId}
					role="menu"
					className="absolute right-0 z-40 mt-2 w-56 rounded-lg border border-slate-200 bg-white py-2 shadow-lg"
				>
					<div className="border-b border-slate-100 px-3 pb-2">
						<p className="truncate text-sm font-medium text-slate-900">
							{userLabel}
						</p>
						<p className="truncate text-xs text-slate-500">{email}</p>
						{roleLabel && (
							<p className="mt-1 text-xs text-slate-600">Role: {roleLabel}</p>
						)}
					</div>
					<Link
						to="/settings/account"
						role="menuitem"
						className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 hover:text-brand"
						onClick={() => setOpen(false)}
					>
						Account settings
					</Link>
					<button
						type="button"
						role="menuitem"
						className="block w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 hover:text-brand"
						onClick={() => {
							setOpen(false);
							void onSignOut();
						}}
					>
						Sign out
					</button>
				</div>
			)}
		</div>
	);
}
