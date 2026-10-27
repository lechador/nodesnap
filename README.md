# NodeSnap

Describe the home you want → explore a coordinated, editable design → understand the
consequences of changes → export a traceable package for professional review.

Built for the Meta Global AI Developer Hackathon (Startup Track, "Push the Frontier").
Specification: `docs/NodeSnap_Master_Build_Specification.md`. Current state: `docs/build-status.md`.
Honest capability record: `docs/capabilities.md` — implemented vs. still-gated methods are
listed separately; nothing here claims NYC code compliance, professional sign-off, or DOB approval.

## Run locally (no Docker required)

```bash
uv sync --all-packages
.venv/bin/python -m uvicorn app.main:app --app-dir apps/api --port 8000
cd apps/web && pnpm install && pnpm dev --port 3000   # http://localhost:3000
```

Tests: `.venv/bin/python -m pytest tests/ -q`

## What works today (M0/M1)

- Canonical Pydantic model, immutable revisions with content hashes, typed commands
- Seeded NYC demo villa: exact spec program (6+6 principal rooms, 5 bedrooms, basement
  pool 8.0 × 3.5 × 1.4 m, ~900 ft² roof terrace), synthetic Demo Villa NYC-01 site
- Real deterministic calculations: pool quantities, area schedules from geometry
- Plan (Konva) + 3D (React Three Fiber) derived from the same model; pool edit →
  new revision → recalculation → revision-bound vector PDF export
- Meta adapter (server-side, allowlisted models) — returns an explicit blocked status
  until `META_API_KEY` is set in `.env` (see `.env.example`); no non-Meta fallback

## Stack

Next.js/React 19 + react-konva + R3F/Three (web) · FastAPI/Pydantic + Shapely +
ReportLab (API) · OR-Tools CP-SAT + PyNiteFEA (planned, M2/M3) · Postgres/Redis via
`infra/docker-compose.yml` for deployment (SQLite dev default locally).
