# NodeSnap project rules

Read docs/NodeSnap_Master_Build_Specification.md and docs/build-status.md.
The specification governs scope, schemas, statuses, engineering requirements,
NYC sources, milestones, and acceptance evidence.

## Working method
- Implement the next milestone; do not stop at a plan.
- Inspect existing code before editing. Preserve unrelated work.
- Keep tasks small, runnable, and reviewable.
- Update build-status.md with evidence, failures, gaps, and next steps.
- Use official dependency documentation and pin working versions.
- Do not silently remove a requested discipline or change the product scope.

## Product and model integrity
- The canonical Python domain model is authoritative.
- Persist immutable revisions with stable entity IDs and SI quantities.
- Use typed commands for both chat and direct edits.
- All geometry, calculations, schedules and PDFs must identify their revision.
- Invalidate dependent results after changes; never present stale results as current.
- Use the normative status enums from Part A without inventing synonyms.

## AI and engineering
- Use only verified Meta models for AI inference.
- Keep secrets and all provider calls on the server.
- Do not execute model-generated scripts or arbitrary user URLs at runtime.
- Numerical outputs come from deterministic methods with units and provenance.
- Every claimed check needs a source, domain, method and independent evidence.
- Unknown inputs remain unknown or explicit demonstration assumptions.
- Never invent code coefficients, site measurements, member capacities or approvals.
- Separate workflow completion, method verification and discipline completion.

## Verification and delivery
- Run the numerical, revision, access and export checks relevant to the change.
- Inspect actual generated documents; a successful export call is insufficient.
- Keep capability and source/license registers accurate.
- Use synthetic/permitted public fixtures in the public repository.
- Never commit credentials, private customer data, fabricated seals or signatures.
- Ask founders only for genuine blocking access, conflicting requirements,
  irreversible business choices, or externally controlled actions.
