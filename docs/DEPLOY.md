# Deploy to one EC2 instance

Target: one Ubuntu 24.04 EC2 instance running Docker Compose (Nginx, API, worker, extractor,
Postgres 16 + pgvector image, Redis), files in Cloudinary, TLS from Let's Encrypt. No other AWS
service. Prerequisites and accounts: docs/SETUP.md.

```
Internet ──443──> nginx (static web + /api proxy + TLS) ──> api ──> postgres, redis
                                                            worker ──> extractor ──> Gemini API
                                                               └────> Cloudinary
```

## 1. Build images (GitHub Actions)

Push to `main`. `images.yml` builds and pushes
`ghcr.io/<owner>/invoiceiq-api`, `-extractor` and `-nginx` tagged with the commit SHA and `latest`.
The nginx image contains the static web build, so production runs no Node process for the web app.

## 2. Prepare the server (once)

```bash
ssh -i your-key.pem ubuntu@<elastic-ip>
# copy deploy/ from the repo to the server, e.g. from your machine:
#   scp -i your-key.pem -r deploy/* ubuntu@<elastic-ip>:/tmp/invoiceiq/
bash /tmp/invoiceiq/scripts/bootstrap.sh          # Docker, Compose plugin, 2 GB swap, /opt/invoiceiq
exit                                               # log out/in so the docker group applies
ssh -i your-key.pem ubuntu@<elastic-ip>
cp -r /tmp/invoiceiq/* /opt/invoiceiq/
cd /opt/invoiceiq
cp .env.prod.example .env && nano .env             # fill every value (SETUP.md)
chmod 600 .env && chmod +x scripts/*.sh
```

## 3. First start

```bash
./scripts/deploy.sh --seed        # pulls images, runs migrations, starts everything, creates users
./scripts/init-letsencrypt.sh     # replaces the temporary self-signed cert with Let's Encrypt
```
Open `https://<your domain>`, sign in with `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`.

Health checks:
```bash
docker compose -f compose.prod.yml --env-file .env ps     # all "healthy"
curl -s https://<your domain>/api/health                   # {"status":"ok","db":"ok","redis":"ok"}
```

## 4. Updates

Push to `main`, wait for `images.yml`, then on the server: `./scripts/deploy.sh`.
Pin a release with `IMAGE_TAG=<sha>` in `.env` to roll back.

## 5. Backups

`scripts/backup.sh` writes a `pg_dump` (custom format) to `/opt/invoiceiq/backups`, keeping 14 days.
Add to crontab: `15 2 * * * /opt/invoiceiq/scripts/backup.sh >> /opt/invoiceiq/backups/backup.log 2>&1`.
Files live in Cloudinary. Copy dumps off the instance occasionally (`scp`), since S3 is out of scope.
Restore: `docker compose -f compose.prod.yml --env-file .env exec -T postgres pg_restore -U invoiceiq -d invoiceiq --clean < backups/<file>.dump`.

## 6. Sizing notes

Memory limits in compose.prod.yml: extractor 512 MB, api/worker 256 MB each, postgres 256 MB,
redis 96 MB, nginx 64 MB. That fits a t3.small (2 GB). On a t3.micro (1 GB) it runs with the 2 GB
swap and `WORKER_CONCURRENCY=1`, but OCR-heavy scans will be slow. These limits were not
load-tested here (NOT MEASURED).

## 7. Security checklist

- Security group: 22 from your IP only; 80/443 public; nothing else (Postgres/Redis/extractor are not
  published).
- `.env` is `chmod 600` and never committed.
- The extractor endpoint requires `EXTRACTOR_SERVICE_TOKEN` and is reachable only on the Docker network.
- Cookies are `Secure` (`COOKIE_SECURE=true` in production compose), `HttpOnly`, `SameSite=Strict`.
- Nginx sets HSTS, CSP, `X-Frame-Options: DENY`, `nosniff`, and rate limits `/api`.
