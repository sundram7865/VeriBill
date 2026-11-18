#!/usr/bin/env bash
# Pull the latest images and (re)start the stack. Run from /opt/veribill.
#   ./scripts/deploy.sh          # update
#   ./scripts/deploy.sh --seed   # first deploy: also create the demo tenant and users
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE="docker compose -f compose.prod.yml --env-file .env"

if [ -n "${GHCR_TOKEN:-}" ]; then
  # Only needed if the packages are private: a PAT with read:packages.
  echo "$GHCR_TOKEN" | docker login ghcr.io -u "${GHCR_USER:?set GHCR_USER}" --password-stdin
fi

$COMPOSE pull
$COMPOSE up -d --remove-orphans

if [ "${1:-}" = "--seed" ]; then
  echo "==> Seeding demo tenant and users"
  $COMPOSE run --rm \
    -e SEED_ADMIN_EMAIL -e SEED_ADMIN_PASSWORD -e SEED_REVIEWER_EMAIL -e SEED_REVIEWER_PASSWORD \
    api node dist/scripts/seed.js
fi

docker image prune -f >/dev/null
$COMPOSE ps
