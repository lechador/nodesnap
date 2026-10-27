# NodeSnap — Implementation Plan

Spec: `docs/NodeSnap_Master_Build_Specification.md` (authoritative, Parts A–E).
Event: Meta Global AI Developer Hackathon, Startup Track, theme "Push the Frontier".
Build period 27 Oct – 4 Nov 2026. **Deadline: 4 Nov 21:00 ET = 5 Nov 02:00 UTC = 05:00/06:00 Tbilisi. Internal freeze 3 Nov.**

Judging: Impact 30% · Meta AI tooling 25% · Technical depth 20% · Demo 25%.
Central story: one conversational change → canonical model revision → affected results go
`stale` → deterministic recalculation → drawings/reports re-export from the same revision.

## Architecture (fixed by spec S1)

- `apps/web` — Next.js + React 19, react-konva (2D plan), React Three Fiber/Three/Drei (3D), Zustand (UI state only)
- `apps/api` — FastAPI (Python 3.12), all business rules + DB writes
- `packages/domain` — Pydantic canonical model, typed commands, status enums, method registry
- `packages/geometry` — Shapely validation, derived geometry
- `packages/engineering` — loads, PyNiteFEA adapter, discipline calculators
- `packages/reports` — ReportLab drawing primitives, sheets, PDF assembly
- `packages/contracts` — OpenAPI → TypeScript types (`openapi-typescript`)
- `tests/fixtures` — disclosed demo inputs + independent analytical references
- `infra` — Dockerfiles, Compose (web/api/worker/postgres/redis/proxy), deploy notes

Canonical rules: SI internally, US customary at presentation; Z-up local coords; stable UUIDs;
immutable revisions (`revision_id` UUID + per-project `revision_number` + `parent_revision_id` + content hash);
typed commands only (chat and drag share the path); normative enums from spec A6.3 verbatim.

AI: Meta only. Runtime `muse-wonder-1.0` (reasoning), `muse-voice-transcribe-1.0` (mic),
optional `muse-image-1.0` (illustrative only). One server-side adapter → `https://api.meta.ai/v1`.
Deterministic software (CP-SAT, Shapely, PyNite) does all geometry/numbers. Model proposes typed
commands; controller validates and commits. Caps: 8 model turns/job, 3 candidates, 60s audio,
`APP_SPEND_CEILING_USD=135` of the $150 credit.

## Milestones (spec Part E; exit = evidence, not dates)

| M | Dates | Work | Exit evidence |
|---|---|---|---|
| M0 | 27 Oct | Scaffold, schemas/enums/registry, Meta structured call, lockfiles | Real Meta call parsed (needs key), build passes, types generated |
| M1 | 27–28 Oct | Seed villa exact program, persisted snapshot, plan/3D, pool quantities, 1 vector PDF | Refresh survives; pool resize updates quantities; PDF = same revision |
| M2 | 28–29 Oct | CP-SAT layouts (central + side corridor), doors/circulation, typed commands, drag, undo, conflicts | 2 briefs → different valid geometry; invalid edit explained |
| M3 | 29–30 Oct | 3 beam fixtures → PyNite adapter, load ledger, baseline steel frame, foundation scenario, invalidation | Fixtures within tolerance; span change changes a real result |
| M4 | 30 Oct–1 Nov | Pool env contract, HVAC/plumbing/electrical/energy/drainage inventories + supported calcs | Real schedules per discipline; gaps explicit, never fake passes |
| M5 | 1–2 Nov | NYC profile/site evidence, all sheet families (C/A/S/F/M/P/E/EN), registers, frozen export | Sheets inspected; IDs/areas agree; blank seal/job fields |
| M6 | 2–3 Nov | Guest isolation, job recovery, rate/cost caps, deploy, 3 scenario rehearsals | Fresh-browser demo, negative-path tests, measured latency/cost |
| M7 | 3–4 Nov | 3-min video, public repo/links, submission | Receipt captured; claims match capability ledger |

Discipline honesty: `workflow_complete` ≠ `discipline_design_complete`. Unimplemented methods stay
in the coverage registry as `research_required`/`blocked` with issue codes — never removed, never
shown as passes. Unknown soil/groundwater/equipment inputs stay null or labeled
`demonstration_assumption`.

## Demo site & villa defaults (spec A3)

Synthetic **Demo Villa NYC-01**, 30 m × 45 m context, no real address/BBL.
Ground (3,000 ft²): living 620, dining 300, kitchen 340, family 360, study 200, guest bed 260 +
support 920. Upper (3,000 ft²): primary 420, bed2 260, bed3 240, bed4 240, library 380, studio 300 +
support 1,160. 5 bedrooms total, 6 principal rooms/floor. Basement 3,000 ft² with pool hall 1,500;
pool water 8.0 × 3.5 × 1.4 m (editable assumption). Roof terrace ~900 ft², tracked separately.
Steel primary frame, timber secondary, RC basement/pool. All-electric concept.
NYC profile: 2022 Construction Codes, ASCE 7-16 via Ch.16, 2025 NYCECC, 2025 NYC Electrical Code.

## Local environment constraints (27 Oct)

- Node 24.16, pnpm 11.21 present. System Python 3.9 → use `uv` to pin Python 3.12.
- **No Docker on this Mac** → Compose file is written for deployment; local dev runs
  web/api/worker processes directly. Postgres/Redis via Compose where available; dev fallback
  must be recorded in decisions.md, not silently substituted in deployed config.
- **No `META_API_KEY` yet** → M0 Meta verification is blocked on founder. Everything non-AI
  (model, calcs, PDF, editing) must work without it; adapter returns explicit blocked status.

## First six tasks (spec order)

1. Monorepo, env examples, Compose, build commands.
2. Pydantic schemas → generated TS contracts.
3. Normative status components + persisted seed snapshot.
4. Three beam fixtures before the structural adapter.
5. One Meta structured-response call + one bounded tool exchange (when key exists).
6. Seed model wired through plan, 3D, real calculation, vector PDF.
