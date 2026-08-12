import { Outlet, createFileRoute } from "@tanstack/react-router";

import { requireClinicalWorkspace } from "@/lib/router-auth";

export const Route = createFileRoute("/patients")({
	beforeLoad: requireClinicalWorkspace,
	component: PatientsLayout,
});

function PatientsLayout() {
	return <Outlet />;
}
