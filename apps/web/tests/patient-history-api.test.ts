import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api";
import { patientsApi } from "@/lib/patients";

vi.mock("@/lib/api", () => ({
	apiClient: {
		get: vi.fn(),
		post: vi.fn(),
		patch: vi.fn(),
		delete: vi.fn(),
	},
}));

describe("patients history/summary api", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("requests patient history with filters", async () => {
		(apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({
			items: [],
			next_cursor: null,
		});

		await patientsApi.history("patient-1", {
			event_type: ["visit"],
			limit: 10,
			cursor: "abc",
		});
		expect(apiClient.get).toHaveBeenCalledWith("/patients/patient-1/history", {
			params: { event_type: ["visit"], limit: 10, cursor: "abc" },
		});
	});

	it("requests visit summary", async () => {
		(apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValue({
			visit: { id: "visit-1" },
			prescriptions: [],
			media: [],
		});

		await patientsApi.visitSummary("visit-1");
		expect(apiClient.get).toHaveBeenCalledWith("/visits/visit-1/summary");
	});
});
