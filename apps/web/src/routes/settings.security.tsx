import { createFileRoute, redirect } from "@tanstack/react-router";

import { requireAuth } from "@/lib/router-auth";

/** Kept for old bookmarks; account settings moved under the user menu. */
export const Route = createFileRoute("/settings/security")({
	beforeLoad: () => {
		requireAuth();
		throw redirect({ to: "/settings/account" });
	},
	component: () => null,
});
