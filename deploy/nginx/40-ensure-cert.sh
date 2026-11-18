#!/bin/sh
# Nginx cannot start its HTTPS server without a certificate, and Let's Encrypt cannot issue one
# until Nginx serves the HTTP challenge. Break the loop with a temporary self-signed certificate;
# scripts/init-letsencrypt.sh replaces it with a real one and reloads Nginx.
set -eu
LIVE="/etc/letsencrypt/live/${DOMAIN}"
if [ ! -f "${LIVE}/fullchain.pem" ]; then
  echo "no certificate for ${DOMAIN} yet: creating a temporary self-signed one"
  mkdir -p "${LIVE}"
  openssl req -x509 -nodes -newkey rsa:2048 -days 2 \
    -keyout "${LIVE}/privkey.pem" -out "${LIVE}/fullchain.pem" \
    -subj "/CN=${DOMAIN}" >/dev/null 2>&1
fi
