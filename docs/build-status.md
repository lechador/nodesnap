# Build status

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

### Known gaps / next
- META_API_KEY missing → M0 Meta live-verification gate open (founder action).
- UI polish: plan card whitespace, inspector table spacing, small-screen layout (M6).
- M2 next: CP-SAT generation, wall/door model, drag editing, undo.

## Blockers
- META_API_KEY (founder) for live Meta verification.
- Docker not installed locally → Compose untested on this Mac; dev runs processes directly.
