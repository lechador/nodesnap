# Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-10-27 | Spec is the single source of truth; ChatGPT share treated as unread | Share link blocked by ChatGPT account check in both browsers; spec file (151 KB) contains the full assignment |
| 2026-10-27 | Local dev runs processes directly (no Docker) | Docker not installed on this Mac; `infra/docker-compose.yml` still written for deployment per spec S1 |
| 2026-10-27 | Python 3.12 pinned via uv | System Python is 3.9; spec S1 requires 3.12 |
| 2026-10-27 | SQLite dev default via `DATABASE_URL` (Postgres in Compose) | No local Postgres/Docker; SQLAlchemy keeps the switch config-only |
| 2026-10-27 | three pinned to 0.180.0 | R3F scene rendered blank with three 0.186 in the harness browser; 0.180 verified by screenshot + pixel probe |
| 2026-10-27 | Jobs execute in-process for M1; RQ worker in M6 | Keeps M1 contracts identical while deferring queue infra; recorded, not hidden |
