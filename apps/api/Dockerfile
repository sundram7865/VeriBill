# Build context: repository root (needs the pnpm workspace files).
FROM node:22.22.1-bookworm-slim AS base
RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g pnpm@10.34.9
# Slow or flaky networks: wait longer per request and retry more before failing the build.
ENV npm_config_fetch_timeout=600000 \
    npm_config_fetch_retries=5 \
    npm_config_network_concurrency=8
WORKDIR /repo

# ---- compile TypeScript ----
FROM base AS build
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/api/package.json apps/api/
RUN pnpm install --frozen-lockfile --filter @veribill/api
COPY apps/api apps/api
RUN pnpm --filter @veribill/api exec prisma generate \
    && pnpm --filter @veribill/api build

# ---- runtime: production deps only; one image runs the api, the worker and migrations ----
FROM base AS runtime
ENV NODE_ENV=production
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/api/package.json apps/api/
RUN pnpm install --frozen-lockfile --prod --filter @veribill/api
COPY apps/api/prisma apps/api/prisma
RUN pnpm --filter @veribill/api exec prisma generate
COPY --from=build /repo/apps/api/dist apps/api/dist
WORKDIR /repo/apps/api
RUN mkdir -p /repo/apps/api/.data && chown -R node:node /repo/apps/api/.data
USER node
EXPOSE 4000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD node -e "fetch('http://localhost:'+(process.env.PORT||4000)+'/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "dist/server.js"]
