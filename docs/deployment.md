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

Rewrite deployed 2026-10-31 from application commit `396f9cc` (build checkout
`d9e9f0a`). The server checkout is `/opt/nodesnap`; only `api` and `web` were
rebuilt/recreated. Existing environment, volumes, Caddy, Postgres and Redis remain
in place. HTTPS apex/www, the public API, live Meta new-building/add-level flow,
revision/access checks and actual PDF outputs were verified. See
`docs/build-status.md` for the release evidence and remaining product limitations.

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

The verified pre-rewrite backup is `/root/nodesnap-backups/20261031T192316Z` on the
server, with a private off-server copy at
`~/.local/share/nodesnap/backups/20261031T192316Z` on the deployment Mac. It contains
`database.dump`, `artifacts.tar.gz`, `production.env`, baseline hashes, image
references, and restore/upgrade verification records. Keep these files private.
Both database and artifact restoration were tested in isolated temporary locations;
the new API's additive schema startup was rehearsed against restored PostgreSQL
before upgrading production. Old images are retained as
`nodesnap-rollback-api:20261031t192316z` and
`nodesnap-rollback-web:20261031t192316z`. Recovery must account for revisions written
after the backup; do not blindly restore the old database over newer work.

SSH uses the dedicated local key `~/.ssh/nodesnap_deploy_ed25519`, for example:
```bash
ssh -i ~/.ssh/nodesnap_deploy_ed25519 -o IdentitiesOnly=yes root@23.92.16.155
```
The original server key remains authorized. Neither private keys nor production
environment contents belong in this repository.

## 2026-10-31 rewrite compatibility

The rewrite preserves the existing Linode host, hostname configuration, Caddy routing,
service names, ports, Dockerfiles, Compose topology, volume names and build-time
`NODESNAP_API` proxy configuration. Local rewrite verification initially preceded
deployment; the completed production release and PostgreSQL rehearsal are recorded
above. No DNS/billing change was needed.

API startup uses SQLAlchemy `metadata.create_all` to add the new mutation receipts,
command receipts, project events, artifact records, conversations, conversation leases
and application budget tables. Existing actor/project/revision/job/analysis/usage
columns are unchanged. Initial budget state imports the existing recorded spend.
This is an additive compatibility path, not a versioned Alembic migration system.
Back up the database and artifacts before a production upgrade; the code's SQLite
compatibility tests are not a production PostgreSQL upgrade rehearsal.

Stored 0.1 snapshots are loaded without rewriting their bytes or historical hashes.
New revisions use schema 0.2 and contain revision-bound architectural geometry.
Legacy revisions without architecture remain identified as such; use the current
supported template for the full architectural experience. Historical artifacts remain
immutable and must not be overwritten by a new export.

On macOS development, use a writable local artifact directory such as
`ARTIFACT_ROOT=./artifacts`; `/data/artifacts` is the existing container mount. Keep
runtime provider credentials in the ignored local environment file and supply them
to the API process. Provider calls remain server-side and Meta-only.

Build contexts now exclude host dependency directories, Next build output and local secrets using root/web `.dockerignore` files. This prevents a build from a populated Mac checkout replacing Linux dependencies with host files; the Dockerfiles and Compose topology are unchanged.
