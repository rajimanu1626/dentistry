# syntax=docker/dockerfile:1.7

# =============================================================================
# clinic-crm-web dev image — bun dev server, code mounted from host.
# =============================================================================

FROM oven/bun:1.1.45

WORKDIR /work

COPY package.json bun.lockb* ./
COPY apps/web/package.json ./apps/web/
COPY packages ./packages
RUN bun install || true

EXPOSE 5173

CMD ["bun", "run", "--cwd", "apps/web", "dev"]
