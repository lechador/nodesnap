# Demo runbook — exact reproducible steps

Live stack: API :8000, Web :3000 (dev without Docker; production via `infra/docker-compose.yml`).

## Scenario 1 — New villa (Impact)
1. Open http://localhost:3000. A fresh guest session seeds Demo Villa NYC-01 automatically.
2. Click Basement / Ground / Upper / Roof; toggle Plan / 3D. Note the pool rectangle and terrace.
3. Read the inspector: pool 28.00 m² / 39.20 m³ / 39,200 kg; structure 3,069 kN; services totals.
4. Export review PDF (top right). Show COVER (blank seal/job fields), CALC-101, REG-101 open issues.

## Scenario 2 — Chat change with consequences (Meta + technical depth)
1. In Conversation type: `make the pool 11 metres long` → Send to Meta.
2. Expect: "committed as revision 2", inspector Volume becomes **53.90 m³** (11 × 3.5 × 1.4).
3. Type: `make the living room bigger, 900 square feet` → CP-SAT regenerates (OPTIMAL), revision 3.
4. Undo → restored as a new revision (history never rewritten).

## Scenario 3 — Direct edit + rejection (editing integrity)
1. In the plan, click a room, drag it onto a neighbour → rejected, geometry restored, reason shown.
2. Change pool length with the "Try a real change" control → new revision, recalculated quantities.
3. Export again → PDF and manifest name the new revision; SHA-256 visible.

## Voice
Click Record, say "make the pool twelve metres long", stop. Transcript appears in the chat box
(editable). Send to Meta to commit it.

## Known failure recovery
- Meta key missing/ceiling reached: chat returns an explicit blocked status; editing, calculations
  and downloads keep working. Budget state: `GET /health` → `spend` (official per-token pricing,
  ceiling $135 of the $150 credit).
- Solver infeasible program: reported as INFEASIBLE within the declared grammar, never faked.
- Recorded fallback must be labelled recorded; never present edited numbers as live computation.

## Measured so far (this Mac, local)
- Analysis (pool+areas+frame+services): one API call, results DB-recorded.
- One structured chat call: ~2,300 tokens ≈ **$0.04** estimated (provider billing authoritative).
