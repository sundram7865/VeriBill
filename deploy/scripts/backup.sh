#!/usr/bin/env bash
# Nightly Postgres backup to the instance's EBS volume, keeping the last 14 days.
# Cron (crontab -e):  15 2 * * * /opt/invoiceiq/scripts/backup.sh >> /opt/invoiceiq/backups/backup.log 2>&1
# Files themselves live in Cloudinary. Copy backups off the instance now and then (scp), because
# the brief rules out S3 and an EBS volume alone does not survive losing the instance.
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR=/opt/invoiceiq/backups
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$BACKUP_DIR"

docker compose -f compose.prod.yml --env-file .env exec -T postgres \
  pg_dump -U invoiceiq -d invoiceiq --format=custom \
  > "$BACKUP_DIR/invoiceiq-$STAMP.dump"

find "$BACKUP_DIR" -name 'invoiceiq-*.dump' -mtime +14 -delete
echo "$(date -u) backup ok: invoiceiq-$STAMP.dump ($(du -h "$BACKUP_DIR/invoiceiq-$STAMP.dump" | cut -f1))"
# Restore: docker compose ... exec -T postgres pg_restore -U invoiceiq -d invoiceiq --clean < file.dump
