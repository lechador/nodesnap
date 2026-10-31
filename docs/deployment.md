# Deployment

## Production (Docker)
Server `.env` lives in `infra/` (Compose reads env from the compose file's
directory, not the repo root):
```bash
# on the server, in the repo root:
git clone https://github.com/lechador/nodesnap.git && cd nodesnap
# create infra/.env (chmod 600): META_API_KEY, POSTGRES_PASSWORD,
# DOMAIN=<hostname for HTTPS, e.g. nodesnap.example.com or <ip>.sslip.io>
docker compose -f infra/docker-compose.yml up --build -d
```
Services: caddy (only public ports 80/443; automatic Let's Encrypt when
`DOMAIN` is set — mic/transcription needs HTTPS), web (Next.js, internal),
api (FastAPI, internal), postgres, redis, named volumes for database,
artifacts and Caddy certs. The api service also serves `/artifacts` via the
web proxy. All services `restart: unless-stopped`.

Live since 2026-10-30: Linode `nodesnap` (us-east, 4 vCPU / 8 GB) at
**https://nodesnap.tech** (also www.nodesnap.tech; A -> 23.92.16.155 at
Namecheap, Let's Encrypt certs for both names verified 2026-10-30).
Fallback hostname https://23-92-16-155.sslip.io no longer configured.

Not yet in Compose: a queue worker. Analyses/exports currently execute in the API process
and are recorded in Postgres; Redis is provisioned for the RQ worker that moves them
out of process. Do not claim async job behaviour until that worker exists and is tested.

## Local development (no Docker, current default)
```bash
uv sync --all-packages
set -a; . ./.env; set +a   # local .env uses sqlite:///./nodesnap.db
.venv/bin/python -m uvicorn app.main:app --app-dir apps/api --port 8000
cd apps/web && pnpm install && pnpm build && pnpm start --port 3000
```

## Backup/restore
- Database: Postgres volume `pgdata` (or `nodesnap.db` locally). Revisions are immutable;
  restoring the DB restores every project/revision.
- Artifacts: volume `artifacts:/data/artifacts` (or `./artifacts` locally); each artifact is
  content-hashed in its export manifest.
- No secrets in the repository: `.env` is gitignored; only `.env.example` is committed.
