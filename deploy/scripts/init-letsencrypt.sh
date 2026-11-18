#!/usr/bin/env bash
# First real TLS certificate. Needs: DNS A record for $DOMAIN -> the Elastic IP, ports 80/443
# open in the security group, and the stack running (Nginx starts with a temporary certificate).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a

COMPOSE="docker compose -f compose.prod.yml --env-file .env"

# Remove the temporary self-signed certificate so certbot can create the real one.
$COMPOSE run --rm --entrypoint sh certbot -c \
  "rm -rf /etc/letsencrypt/live/${DOMAIN} /etc/letsencrypt/archive/${DOMAIN} /etc/letsencrypt/renewal/${DOMAIN}.conf"

$COMPOSE run --rm --entrypoint certbot certbot certonly --webroot -w /var/www/certbot \
  -d "$DOMAIN" --email "$LETSENCRYPT_EMAIL" --agree-tos --no-eff-email --non-interactive

$COMPOSE exec nginx nginx -s reload
echo "Certificate installed for ${DOMAIN}; renewal runs automatically in the certbot container."
