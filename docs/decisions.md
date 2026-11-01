# Decision log

| Date | Decision | Rationale |
|---|---|---|
| 2026-10-27 | Spec is the single source of truth; ChatGPT share treated as unread | Share link blocked by ChatGPT account check in both browsers; spec file (151 KB) contains the full assignment |
| 2026-10-27 | Local dev runs processes directly (no Docker) | Docker not installed on this Mac; `infra/docker-compose.yml` still written for deployment per spec S1 |
| 2026-10-27 | Python 3.12 pinned via uv | System Python is 3.9; spec S1 requires 3.12 |
| 2026-10-27 | SQLite dev default via `DATABASE_URL` (Postgres in Compose) | No local Postgres/Docker; SQLAlchemy keeps the switch config-only |
| 2026-10-27 | three pinned to 0.180.0 | R3F scene rendered blank with three 0.186 in the harness browser; 0.180 verified by screenshot + pixel probe |
| 2026-10-27 | Jobs execute in-process for M1; RQ worker in M6 | Keeps M1 contracts identical while deferring queue infra; recorded, not hidden |
| 2026-10-27 | Docker = deployment path, direct processes = local dev | Compose gives judges/host one-command reproducibility for the 6-service spec architecture; local iteration stays faster without Docker Desktop, contracts kept identical via DATABASE_URL/REDIS_URL switches |
| 2026-10-31 | Replace the workspace and backend services while preserving deployed infrastructure | User explicitly requested a complete application rewrite with the same deployment; no remote deployment/DNS/billing action taken |
| 2026-10-31 | Canonical architecture schema 0.2 with legacy 0.1 hash preservation | Walls, openings, slabs, stairs and clear-area metrics must agree across 2D/3D/PDF; old revisions remain immutable |
| 2026-10-31 | Physical envelope inside gross footprint; partitions on zone boundaries | Clear metrics deduct full exterior wall and half shared partition thickness; zone area and program targets remain distinct |
| 2026-10-31 | Fixed connected core and central-corridor solver family | Stable stairs/circulation and valid shared openings take priority; arbitrary/freeform and side-corridor generation remain declared gaps |
| 2026-10-31 | Separate presentation assets from canonical engineering | Procedural texture, furniture and landscape improve 3D legibility without inventing equipment capacities or physical design loads |
| 2026-10-31 | Conservative result invalidation and explicit independent structural baseline | A fixed frame calculation cannot be presented as structural consequences of edited room/pool/facade geometry |
| 2026-10-31 | Additive persistence tables and guarded head updates | Preserve existing deployed database rows while implementing idempotency, command replay protection, events and budget reservations |
| 2026-11-01 | Support private-home yard, detached garage and outdoor pool as canonical site features | Founder explicitly requested addable yard and garage. A separate typed site layout preserves house rooms while providing coordinated 3D, site-plan and export geometry; garage is an unconditioned outbuilding with a vehicle-door opening and approach |
| 2026-11-01 | Distinguish indoor/outdoor pool location and preserve room history on conversion | Outdoor water belongs in the yard/site plan, not an enclosed pool hall or house slab opening. Moving an existing indoor pool outdoors retains the former hall layout and records the conversion assumption rather than silently redesigning rooms |
| 2026-11-01 | Keep geometric site quantities separate from house and engineering scope | Yard grass subtracts deck holes; deck subtracts water; garage gross/clear floor area remains separate. Garage roof contributes to runoff but not house conduction. Outdoor evaporation remains unsourced/research_required, and indoor dehumidification is not applicable |
| 2026-11-01 | Synthetic layout extents are not parcel boundaries or permitted clearances | Rear-yard gap, garage separation, driveway, pool deck and context margin are concept assumptions. Synthetic context follows saved geometry; sourced parcel context is never resized. Legal site fit, curb access, pool barriers, garage fire/ventilation and engineering adequacy require independent evidence |
| 2026-11-01 | Preserve deployed topology, historical hashes and existing asset/license basis for site features | Optional fields are omitted from legacy serialization when absent/default; edits create new revisions with stable surviving IDs. Site geometry is application-generated, with no added external assets or dependencies and no Compose/service-topology change |
