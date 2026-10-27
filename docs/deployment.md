# Deployment

## Production (Docker)
```bash
cp .env.example .env   # set META_API_KEY and SESSION_SECRET; Compose overrides DATABASE_URL/REDIS_URL
docker compose -f infra/docker-compose.yml up --build
```
Services: web (Next.js :3000), api (FastAPI :8000), postgres, redis, named volumes for
database and generated artifacts. The api service also serves `/artifacts`.

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
