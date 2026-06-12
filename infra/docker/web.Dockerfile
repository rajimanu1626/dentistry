# syntax=docker/dockerfile:1.7

# =============================================================================
# clinic-crm-web — multi-stage Dockerfile (bun build -> nginx serve)
# =============================================================================

ARG BUN_VERSION=1.1.45
ARG NGINX_VERSION=1.27-alpine

# ----- builder ---------------------------------------------------------------
FROM oven/bun:${BUN_VERSION} AS builder

WORKDIR /work

COPY package.json bun.lockb* ./
COPY apps/web/package.json ./apps/web/
COPY packages ./packages

RUN bun install --frozen-lockfile || bun install

COPY apps/web ./apps/web
COPY tsconfig.base.json* ./

WORKDIR /work/apps/web
RUN bun run build

# ----- runtime ---------------------------------------------------------------
FROM nginx:${NGINX_VERSION} AS runtime

RUN rm -rf /usr/share/nginx/html/*

COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /work/apps/web/dist /usr/share/nginx/html

RUN addgroup -g 1001 -S app \
    && adduser  -u 1001 -G app -S app

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/ >/dev/null 2>&1 || exit 1
