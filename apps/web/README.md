# clinic-crm web

React 19 + Vite + TanStack Router/Query.

```bash
bun install
bun run dev
bun run test
bun run lint
```

Conventions enforced by `.cursor/rules/web-conventions.mdc`:

- All API calls go through `src/lib/api.ts`. No `fetch` / `axios` outside.
- TanStack Router is **file-based**; create new routes under `src/routes/`. The
  Vite plugin regenerates `src/routeTree.gen.ts` on save.
- TanStack Query is the source of truth for server state. Use mutations for writes.
- Components live in `src/components/`. Tailwind + shadcn/ui style.
- No PHI in URLs.
