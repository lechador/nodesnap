# Build status

## 2026-10-30 — Public repo + Linode production deploy LIVE

- Public repo: https://github.com/lechador/nodesnap (pre-push secret/personal-data
  scan clean; `.env`, `nodesnap.db`, `artifacts/` verified gitignored).
- Linode `nodesnap` id 109659783, us-east, g6-standard-4 (4 vCPU / 8 GB, $48/mo
  against the $100/60-day credit), Ubuntu 24.04, IP 23.92.16.155. Docker +
  Compose installed; ufw 22/80/443; SSH key-only (root password generated to a
  local 600 file, never in chat/repo).
- URL: **https://23-92-16-155.sslip.io** (Caddy + Let's Encrypt, cert verified;
  swap for a founder subdomain later — see docs/deployment.md).
- First-ever Compose test — 3 bugs found and fixed in-tree:
  (1) pnpm ignored-build-scripts failure in web image → `strict-dep-builds=false`;
  (2) `/health` 500: Next rewrites are baked at build time, runtime
  `NODESNAP_API` still pointed to localhost → build arg in Dockerfile + Compose;
  (3) missing `restart` policy → `unless-stopped` on all services.
  Also: Compose now only publishes Caddy; server `.env` is `infra/.env` (600).
- Verified over HTTPS from outside: home 200, `/health` ok (Meta configured,
  fresh spend $0), session → seed project → pool analysis exact (28 m² /
  39.20 m³ / 384,421 N), 11-page export PDF SHA-256 matches manifest,
  live Meta chat "make the pool 11 metres long" → revision 2 ($0.0225),
  `docker compose down && up` → revision 2, identical PDF and spend ledger
  all persist. Browser: plan + 3D render (3D needed a resize event in the
  headless harness; same code as local QA).
- Env audit: code reads META_API_KEY/BASE_URL/REASONING/TRANSCRIPTION models,
  DATABASE_URL, ARTIFACT_ROOT, APP_SPEND_CEILING_USD only. `SESSION_SECRET`,
  `REDIS_URL`, `DEMO_MODE` in .env.example are not read by the code.
- Gaps: sslip.io hostname is a placeholder (founder domain pending); Linode
  firewall not used (host ufw instead, token has no firewall need); backup
  snapshot not yet taken.

## 2026-10-27 — Planning + M0/M1 slice working

- Read the full master specification (1,215 lines, Parts A–E). Spec moved to
  `docs/NodeSnap_Master_Build_Specification.md`.
- ChatGPT share link could not be read: ChatGPT returns an account/bot check in both
  cloud and local browsers. Proceeding from the spec, which is self-contained.
- Wrote `AGENTS.md`, `docs/implementation-plan.md`, `docs/capabilities.md`,
  `docs/decisions.md`, this file.

### Verified evidence (actually run, not planned)
- Python workspace (uv, Python 3.12): domain/geometry/engineering/reports + FastAPI.
  `pytest tests/ -q` → **5 passed** (seed program: 6+6 principal rooms, 5 bedrooms,
  no overlaps; pool quantities exact: 28 m², 39.2 m³, 39,200 kg, 384,421 N, 13,729 Pa;
  pool edit → revision 2 with changed hash; PDF is a real revision-bound document).
- API live on :8000 — session → seed project → analysis → pool edit (rev 2) →
  stale edit returns **412** → export PDF with SHA-256 manifest → other session **403**.
  Meta conversation endpoint returns explicit `blocked / MISSING_INPUT` (no key yet).
- Web (Next.js 16, React 19) builds clean; running on :3000. Screenshot-reviewed:
  plan renders all rooms/levels, 3D renders extruded room blocks (fixed R3F wrapper
  sizing bug; three pinned to 0.180.0), inspector shows live pool numbers and gaps.
- PDF first page visually inspected: vector plan, labels readable, pool rectangle and
  revision shown. Labels are small — polish item for M5.
- Contracts: `packages/contracts/openapi.json` + generated `api.d.ts` (11 routes).

### M2 progress (same day)
- CP-SAT layout generation (`packages/geometry/layout.py` + `generate.py`): strip grammar,
  0.1 m grid, ±15% area band, solver status reported honestly (OPTIMAL/FEASIBLE/INFEASIBLE).
  API `POST /projects/{id}/generate`, UI "Regenerate layout" button — verified in browser
  (OPTIMAL → revision 2). Different program targets produce different geometry (tested);
  impossible program returns INFEASIBLE, not a fake layout.
- Drag editing: selected room is draggable in the Konva plan; release commits one
  `move_space` typed command (0.1 m snap); overlap/out-of-plate moves return 422 with
  named objects and the UI restores committed geometry. Undo endpoint creates a new
  revision restoring the parent (history never rewritten) — verified over HTTP.
- Still open in M2: wall assemblies/thickness derivation, doors/openings through shared
  boundaries, access-graph checks, side-corridor topology, 3D transform handles.

### Meta structured orchestration (2026-10-27, evening)
- Muse structured proposal: probe -> domain validation -> same typed-command commit path as drag edits.
- Live scenario chain on one project: pool 12 m (rev 2) -> pool 9 m (rev 3) -> living room 900 ft2 via CP-SAT (rev 4, OPTIMAL).
- In the browser: typed 'make the pool 11 metres long' -> committed rev 2, inspector volume 53.90 m3 (exact).
- Failure found and handled: model sometimes returned explain/garbled text for explicit changes -> strengthened prompt + one bounded controller repair re-ask. Unsupported requests (helipad) never mutate.

### M3 structure (2026-10-27)
- Fixtures first: independent closed-form references in tests/fixtures; PyNite adapter passes A/B/C at spec E14 tolerances + scaling/sign/invalid-input tests.
- Baseline villa gravity frame (declared idealization, assumed loads/sections): equilibrium residual 1.5e-16, total 3,069 kN, max beam moment 102.3 kN-m, max beam deflection 45.8 mm — shown in UI as quantities with check not_evaluated.
- Foundation bearing scenario: 11.00 kPa average vs assumed 100 kPa (utilization 0.11), geotech basis explicitly missing.
- Found while testing: PyNite deflection_array returns [x, deflection] rows and node-only sampling measures column shortening — both fixed, tests guard them.

### M4 services (2026-10-27)
- Inventories built from canonical spaces (bathrooms/kitchens/equipment); component math hand-checked in tests: conduction 600 W fixture case, runoff conversion exact, current I=P/V, fixture sums.
- UI shows: electrical 24.3 kW connected (101 A @ declared 240 V), 11 fixtures / 74 L/min, envelope conduction 6.38 kW, roof runoff 7.36 L/s — each labelled with what remains gated. Pool environment method remains research_required (ASHRAE transcription gate).

### M5 review package (2026-10-27)
- Export is now an 11-sheet package: COVER (NYC D1 profile, blank job/seal fields) · C-101 synthetic site · A-101-104 plans · CALC-101 pool+areas · S-101 frame reactions · F-101 bearing · MPE-101 services · REG-101 assumptions/methods/open issues. Cover and F-101 pages visually inspected: readable, no clipping.
- Frozen basis: export computes its result set once from the named revision; basis hash precedes file hashes; manifest hash stored externally (no circular hashing). Manifest + canonical model JSON are downloadable artifacts alongside the PDF.

### Transcription (2026-10-27)
- Correct endpoint is POST /v1/asr/transcribe (multipart request JSON + WAV; /audio/transcriptions and Responses input_audio both 404 with this model). Requires mono s16le 16/24 kHz WAV.
- App endpoint + browser mic (MediaRecorder -> 16 kHz WAV in-page) verified: test speech transcribed exactly through the app. Wrong-endpoint probes and the format requirement are recorded here so they are not re-discovered.

### M6 hardening (2026-10-27)
- Spend ledger: every Meta call recorded with token/audio usage and estimated cost from the official pricing page (Wonder $4/$0.20/$20 per M, Transcribe $0.18/h); /health exposes totals vs the $135 ceiling, which blocks new model work while deterministic features continue. One chat call measured ~2,300 tokens = $0.0412.
- docs/demo-runbook.md (3 rehearsed scenarios + recovery) and docs/deployment.md written. Compose worker removed — it referenced a not-yet-built module; Redis stays provisioned for the future RQ worker.
- Three end-to-end scenarios rehearsed live during M1-M5 (seed/inspect/export; chat pool+room changes; drag rejection + pool edit + re-export).

### Responsive pass (2026-10-27, founder report)
- Founder screenshot showed the fixed 320/1fr/330 grid overflowing on a narrow screen. Fixed: CSS breakpoints (<=1100px two columns with inspector below; <=760px single column stacking chat -> workspace -> inspector per spec A4), wrapping button rows, viewport meta + NodeSnap title, and the Konva plan now measures its panel and rescales (labels scale with it).
- Verified: 390x844 no horizontal overflow (scrollWidth == innerWidth), stacked layout + plan fit inspected; 1440px three-column layout unchanged.

### Full-site QA + redesign (2026-10-27, founder request)
- Report: docs/qa-report-2026-10-27.md. Six bugs found by exercising every control; all fixed and re-verified in browser (notable: NaN empty-revision commit, undo ping-pong -> restore-based undo/redo, export revision_number, Retina DPR blur).
- Design system + status strip + plan drawing content (room areas, dimensions, scale bar, north point). Visual review 6/10 credible prototype; top remaining gap is model-level (walls/doors/stair graphic), tracked below.

### Known gaps / next
- META_API_KEY missing → M0 Meta live-verification gate open (founder action).
- UI polish: plan card whitespace, inspector table spacing, small-screen layout (M6).
- M2 next: CP-SAT generation, wall/door model, drag editing, undo.

## Blockers
- ~~META_API_KEY~~ **Resolved 2026-10-27:** key in `.env` (gitignored); `GET /models` 200 with
  muse-wonder-1.0 / muse-voice-transcribe-1.0 / muse-spark-1.3 / muse-image-1.0 present;
  live conversation through the app returned a real reply (417 tokens logged). Structured
  proposal schema + tool loop still to wire. Local `.env` DATABASE_URL set to SQLite
  (the copied Postgres URL crashed startup — no local `nodesnap` role).
- Docker not installed locally → Compose untested on this Mac; dev runs processes directly.
