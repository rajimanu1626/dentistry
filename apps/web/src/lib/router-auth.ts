import { redirect } from "@tanstack/react-router";

import { auth } from "@/lib/auth";

/** Redirect anonymous users to /login. */
export function requireAuth(): void {
	if (!auth.isAuthenticated()) {
		throw redirect({
			to: "/login",
			search: { redirect: window.location.pathname },
		});
	}
}

/** Redirect signed-in users away from guest-only pages. */
export function redirectIfAuthenticated(to = "/"): void {
	if (auth.isAuthenticated()) {
		throw redirect({ to: auth.isPlatformOperator() ? "/platform" : to });
	}
}

/** Platform console — platform_admin or platform_support. */
export function requirePlatformAuth(): void {
	requireAuth();
	if (!auth.isPlatformOperator()) {
		throw redirect({ to: "/" });
	}
}

/** Clinical workspace — not for platform-only accounts. */
export function requireClinicalWorkspace(): void {
	requireAuth();
	if (auth.isPlatformOperator() && !auth.getClinicId()) {
		throw redirect({ to: "/platform" });
	}
}
