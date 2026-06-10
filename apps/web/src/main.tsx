import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { auth } from "./lib/auth";
import { routeTree } from "./routeTree.gen";
import "./styles/globals.css";

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 30_000,
			refetchOnWindowFocus: false,
			retry: 1,
		},
	},
});

const router = createRouter({
	routeTree,
	defaultPreload: "intent",
	context: { queryClient },
});

declare module "@tanstack/react-router" {
	interface Register {
		router: typeof router;
	}
}

const rootEl = document.getElementById("root");
if (!rootEl) {
	throw new Error("Missing #root element");
}

async function bootstrapSession(): Promise<void> {
	const token = auth.getToken();
	if (!token) return;

	const baseURL = import.meta.env.DEV
		? "/api"
		: (import.meta.env.VITE_API_BASE_URL ?? "/api");
	const headers: Record<string, string> = { Authorization: `Bearer ${token}` };

	try {
		const response = await fetch(`${baseURL}/auth/me`, { headers });
		if (!response.ok) {
			auth.clearSession();
			return;
		}
		const me = (await response.json()) as {
			memberships: Array<{ clinic_id: string }>;
			system_role: "platform_admin" | "platform_support" | null;
		};
		auth.setSystemRole(me.system_role ?? null);
		auth.clearClinicId();
		if (me.memberships.length > 0) {
			auth.setClinicId(me.memberships[0]!.clinic_id);
		}
	} catch {
		// Offline / API down: keep local session and let route-level requests decide.
	}
}

void bootstrapSession().finally(() => {
	createRoot(rootEl).render(
		<StrictMode>
			<QueryClientProvider client={queryClient}>
				<RouterProvider router={router} />
			</QueryClientProvider>
		</StrictMode>,
	);
});
