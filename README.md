# NodeSnap

Describe a home, explore its architectural model, make traceable changes, and export a revision-specific review draft.

NodeSnap is a homeowner-facing concept workspace built around one authoritative Python building model. The 2026-10-31 rewrite adds a new architectural studio, physical walls and openings, connected stairs, cutaway/exploded 3D, dimensioned plans, and a stronger transactional backend. The existing Linode / Docker Compose deployment configuration is preserved; this rewrite has not been deployed to production.

## Run locally

Requires Python 3.12, uv, Node.js 24 and the pnpm version declared in `apps/web/package.json`.

```bash
uv sync --all-packages --frozen
.venv/bin/python -m uvicorn app.main:app --app-dir apps/api --port 8000
```

In another terminal:

```bash
cd apps/web
corepack pnpm install --frozen-lockfile
corepack pnpm dev --port 3000
```

Open `http://localhost:3000`. SQLite is the local default; production retains PostgreSQL. Exported artifacts use `ARTIFACT_ROOT` (default `./artifacts`). See `.env.example` for server configuration. Supply `META_API_KEY` to the API process to enable Meta conversation/transcription. Without it, direct editing, generation, deterministic calculations and exports remain usable; AI returns an explicit blocked result.

## Supported workflow

1. Open the synthetic NYC villa: six principal rooms on each main floor, five bedrooms, basement indoor pool and approximately 900 ft² roof terrace.
2. Explore exterior, floor cutaway and exploded 3D; switch to dimensioned plans and inspect actual net areas.
3. Edit supported pool dimensions, terrace area, floor height, finishes or shared partitions. Accepted changes create immutable revisions; stale results are identified.
4. Generate another layout within the central-corridor template, inspect differences and restore earlier designs without rewriting history.
5. Run supported calculations and download the vector review PDF, canonical model JSON and hashed manifest.

Meta conversation and microphone transcription share the same server validation boundaries. Live integration verified pool and room changes through Meta, alongside controlled-provider tests. A transcription fixture exposed a “pool”/“cool” recognition error, so the transcript remains editable before submission. Detailed timings and evidence are in build status.

## Scope and evidence

Architectural walls, doors/windows, slabs, terrace guards and stair geometry come from the same revision as the plans and schedules. Material textures, furniture and landscape presentation are illustrative. Canonical dimensions are SI; the interface and plan sheets provide customary presentation units.

The numerical modules retain exact pool quantities, independently tested beam fixtures, an explicitly independent gravity-frame scenario, bearing screening, service inventories, conduction and runoff components. The frame is not a structural model of each architectural revision. Complete structural, foundation, MEP, energy, drainage and pool-environment design remains open. PDFs are professional review drafts with assumptions and gaps, not signed or approved construction documents.

- [Master specification](docs/NodeSnap_Master_Build_Specification.md)
- [Current build evidence and next steps](docs/build-status.md)
- [Capability ledger](docs/capabilities.md)
- [Engineering methods](docs/engineering-methods.md)
- [Sources and licenses](docs/source-and-license-register.md)
- [Deployment and compatibility](docs/deployment.md)

## Checks

```bash
.venv/bin/python -m pytest tests/ -q
cd apps/web
corepack pnpm build
corepack pnpm lint
```

The Python suite covers numerical fixtures, connected geometry, immutable history, finite inputs, owner isolation, idempotency, concurrent edits, provider restrictions, spend reservations and export hashes. Check build status for the latest actually executed browser/rendering evidence and any remaining limitations.

## Architecture

`apps/web` is Next.js/React with React Three Fiber/Three.js. `apps/api` is FastAPI with separate persistence, orchestration, spend and analysis modules. `packages/domain` owns canonical schemas and typed edits; `geometry` owns validation/CP-SAT generation; `engineering` owns deterministic methods; `reports` draws canonical vector documents. API calls remain same-origin through the existing Next.js proxy.

Production services remain Caddy, web, API, PostgreSQL and Redis with existing named volumes. Heavy jobs still execute in the API process; an independent queue worker remains future work. Exact resolved dependencies are recorded in `uv.lock` and `apps/web/pnpm-lock.yaml`.
