# syntax=docker/dockerfile:1.7

# =============================================================================
# clinic-crm-web dev image — bun dev server, code mounted from host.
# =============================================================================

FROM oven/bun:1.1.45

WORKDIR /work

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
      | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
      > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY package.json bun.lockb* ./
COPY apps/web/package.json ./apps/web/
COPY packages ./packages
RUN bun install || true

EXPOSE 5173

CMD ["bun", "run", "--cwd", "apps/web", "dev"]
