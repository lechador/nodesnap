# Capability ledger

Full target preserved for every row. Status uses spec vocabulary; a gap is never deleted.

| Capability | Planned | Implemented | Method state | Evidence | Gap |
|---|---|---|---|---|---|
| Canonical model + immutable revisions | yes | YES (M1) | — | — | M0/M1 |
| Brief interpretation (Meta Wonder) | yes | YES (structured) | implemented | Strict json_schema proposal verified live; chat 'make the pool 11 metres long' committed rev 2 in UI (volume 53.90 m3), living-room 900 ft2 -> CP-SAT OPTIMAL rev 4, unsupported requests never mutate | occasional garbled explanations required a bounded repair pass (implemented, 1 retry) |
| Microphone transcription (Meta) | yes | no | implemented | muse-voice-transcribe-1.0 confirmed present in account model list | transcription endpoint not yet called with audio |
| CP-SAT layout generation (2 topologies) | yes | PARTIAL (central-corridor strip grammar) | research_required | — | M2 |
| Geometry/topology validation (Shapely) | yes | no | research_required | — | M1/M2 |
| Typed commands, drag edit, undo, conflicts | yes | YES (move_space/set_pool_dimensions, 412/422 paths) | — | — | M2 |
| Pool quantities (area/volume/mass/hydrostatic) | yes | YES (M1) | research_required | — | M1; physics only, not shell design |
| Pool environment / evaporation | yes | no | research_required | — | method source gate (ASHRAE) open |
| Structural fixtures A/B/C | yes | YES | verified_for_scope | tests/test_m3_fixtures.py at E14 tolerances (rel 1e-6) | planar beams only |
| PyNite frame analysis | yes | YES | implemented | gravity frame: 3,069 kN applied = reactions, residual 1.5e-16; interior > corner columns | frame idealization unreviewed; no lateral/member checks |
| Load ledger + combinations | yes | no | research_required | — | NYC/ASCE source gate open |
| Steel/timber/RC design checks | yes | no | research_required | — | sourced methods required |
| Foundations/basement scenarios | yes | PARTIAL (bearing scenario) | implemented | uniform-pressure scenario vs assumed 100 kPa in analyses + UI | settlement/uplift/reinforcement gated; no geotech evidence |
| HVAC loads + ventilation | yes | no | research_required | — | sourced methods required |
| Plumbing networks + demand | yes | no | research_required | — | sourced methods required |
| Electrical loads + panel graph | yes | no | research_required | — | 2025 NYC Electrical method required |
| Energy (2025 NYCECC pathway) | yes | no | research_required | — | pathway determination required |
| Roof terrace + drainage/runoff | yes | no | research_required | — | hydraulic method gate open |
| NYC site evidence adapters | yes | no | research_required | — | live API verification in M5 |
| Drawing set + calc report PDFs | yes | PARTIAL (4 plans + calc page) | research_required | — | M1 (1 sheet) → M5 (all families) |
| Export manifest + hashes | yes | no | — | — | M5 |
| Guest sessions, isolation, spend caps | yes | no | — | — | M6 |
