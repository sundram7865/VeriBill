# Build context: repository root. Builds the static web export and bakes it into Nginx,
# so production runs no Node process for the web app.
FROM node:22.22.1-bookworm-slim AS web
RUN npm install -g pnpm@10.34.9
# Slow or flaky networks: wait longer per request and retry more before failing the build.
ENV npm_config_fetch_timeout=600000 \
    npm_config_fetch_retries=5 \
    npm_config_network_concurrency=8
WORKDIR /repo
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/web/package.json apps/web/
COPY apps/web/scripts apps/web/scripts
RUN pnpm install --frozen-lockfile --filter @veribill/web
COPY apps/web apps/web
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @veribill/web build

FROM nginx:1.28.0-alpine
RUN apk add --no-cache openssl && rm /etc/nginx/conf.d/default.conf
COPY deploy/nginx/templates/ /etc/nginx/templates/
COPY deploy/nginx/40-ensure-cert.sh /docker-entrypoint.d/40-ensure-cert.sh
RUN chmod +x /docker-entrypoint.d/40-ensure-cert.sh
COPY --from=web /repo/apps/web/out /usr/share/nginx/html
