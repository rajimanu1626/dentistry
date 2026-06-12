import { describe, expect, it, vi } from "vitest";

import { redirectIfAuthenticated, requireAuth } from "@/lib/router-auth";

vi.mock("@/lib/auth", () => ({
	auth: {
		isAuthenticated: vi.fn(),
	},
}));

vi.mock("@tanstack/react-router", async () => {
	const actual = await vi.importActual<object>("@tanstack/react-router");
	return { ...actual, redirect: (opts: unknown) => ({ redirected: opts }) };
});

describe("router auth guards", () => {
	it("requireAuth redirects guests", async () => {
		const { auth } = await import("@/lib/auth");
		(auth.isAuthenticated as ReturnType<typeof vi.fn>).mockReturnValue(false);
		expect(() => requireAuth()).toThrow();
	});

	it("redirectIfAuthenticated redirects signed-in users", async () => {
		const { auth } = await import("@/lib/auth");
		(auth.isAuthenticated as ReturnType<typeof vi.fn>).mockReturnValue(true);
		expect(() => redirectIfAuthenticated("/")).toThrow();
	});
});
