/**
 * Same-origin reverse proxy for Neon Auth.
 *
 * Safari (ITP) blocks third-party cookies on *.neonauth.*.neon.tech when the
 * SPA runs on clinic-crm-web.pages.dev. Proxying Auth under /neon-auth makes
 * the session cookie first-party so sign-in + authClient.token() work.
 */

const UPSTREAM =
	"https://ep-dawn-water-azzonm38.neonauth.c-3.ap-southeast-1.aws.neon.tech/neondb/auth";

type PagesContext = {
	request: Request;
	params: { path?: string | string[] };
};

function rewriteSetCookie(cookie: string): string {
	return cookie
		.split(";")
		.map((part) => part.trim())
		.filter((part) => {
			const lower = part.toLowerCase();
			if (lower.startsWith("domain=")) return false;
			if (lower === "partitioned") return false;
			return true;
		})
		.map((part) => {
			if (part.toLowerCase().startsWith("samesite=")) {
				return "SameSite=Lax";
			}
			return part;
		})
		.join("; ");
}

export async function onRequest(context: PagesContext): Promise<Response> {
	const incoming = new URL(context.request.url);
	const rawPath = context.params.path;
	const suffix = Array.isArray(rawPath)
		? rawPath.join("/")
		: (rawPath ?? "");
	const target = `${UPSTREAM}/${suffix}${incoming.search}`;

	const headers = new Headers(context.request.headers);
	headers.delete("host");
	// Avoid compressing mismatches through the Worker edge.
	headers.delete("accept-encoding");

	const init: RequestInit = {
		method: context.request.method,
		headers,
		redirect: "manual",
	};

	if (
		context.request.method !== "GET" &&
		context.request.method !== "HEAD" &&
		context.request.method !== "OPTIONS"
	) {
		init.body = context.request.body;
		// Required when streaming a body from an incoming Request in CF Workers.
		(init as RequestInit & { duplex?: string }).duplex = "half";
	}

	const upstream = await fetch(target, init);
	const outHeaders = new Headers(upstream.headers);

	const setCookies =
		typeof outHeaders.getSetCookie === "function"
			? outHeaders.getSetCookie()
			: [];
	outHeaders.delete("set-cookie");
	for (const cookie of setCookies) {
		outHeaders.append("set-cookie", rewriteSetCookie(cookie));
	}

	// Same-origin browser calls — drop upstream CORS so the browser treats
	// this as a first-party response.
	outHeaders.delete("access-control-allow-origin");
	outHeaders.delete("access-control-allow-credentials");
	outHeaders.delete("access-control-allow-headers");
	outHeaders.delete("access-control-allow-methods");
	outHeaders.delete("access-control-expose-headers");

	return new Response(upstream.body, {
		status: upstream.status,
		statusText: upstream.statusText,
		headers: outHeaders,
	});
}
