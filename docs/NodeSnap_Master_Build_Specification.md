# NodeSnap — Master Build Specification
## Meta Global AI Developer Hackathon · Startup Track · NYC Villa Demonstration

**Specification version:** 1.0  
**Research and requirements freeze:** 26 October 2026  
**Product owner:** NodeSnap founder/CEO  
**Technical owner:** NodeSnap CTO  
**Primary development environment:** Muse Code with Muse Wonder Full subscription  
**Application AI provider:** Meta Model API  
**Initial application credit budget:** US$150; additional spending is a founder-controlled setting  
**Purpose of this file:** A detailed implementation assignment for the coding agent and the two-person team.

This file defines the requested software. It is not a construction design, a set of house calculations, or an assertion that a complete NYC submission package has already been produced. All dimensions and quantities specified as demonstration defaults are editable concept assumptions.

---

## Read this first: assignment to the coding agent

Build **NodeSnap**, a homeowner-facing web application that turns a conversation into a coordinated, editable house design, executes traceable engineering calculations, and exports drawings and calculation reports for qualified professionals to review, revise as necessary, sign, and submit to the relevant authority.

The initial demonstration is a contemporary luxury single-family villa in New York City: two above-ground floors, six principal rooms on each floor, an indoor swimming pool in the basement, and an occupied roof terrace. Use a steel primary structure, appropriate timber secondary elements, and a concrete basement/foundation/pool system. The homeowner supplies intent through text or microphone; they do not need to upload a finished architectural project.

Implement the workflow, the domain model, real calculations within declared methods, and coordinated document generation. The building must remain editable through conversation and direct manipulation. Every visible calculation must come from executable software with explicit inputs and units. Every drawing must derive from the same versioned building model. An attractive rendering, a generated narrative, or a screen of placeholder checks does not satisfy this assignment.

The complete requested product includes architecture, structure, foundations, HVAC, plumbing, electrical, energy, drainage, and pool systems. The hackathon schedule requires staged implementation and honest reporting of achieved coverage. Do not remove a requested discipline silently or declare the full target achieved when required methods are missing. Preserve both the full target and a measured record of the implemented prototype.

Proceed autonomously on ordinary implementation choices consistent with this specification. Ask the founders only when a real missing credential, unavailable licensed source, irreversible business decision, or conflicting product requirement prevents progress. A missing engineering input should become a typed unresolved item and an explicitly assumed demonstration scenario where appropriate; it must not cause the agent to invent a measurement.

### How the team should use this file

1. Put this file in a fresh repository as `docs/NodeSnap_Master_Build_Specification.md`.
2. Open that repository in Muse Code. Use the installed model picker to select **Muse Wonder Full** and confirm that subscription access is active. Do not assume the default coding model is Full.
3. Give Muse Code the kickoff prompt in Part E. Ask it to read the entire specification, create a capability ledger and implementation plan, then execute the first milestone.
4. Work milestone by milestone. Require runnable code and the specified evidence at each gate. A plan or screenshot alone is not milestone completion.
5. Keep `docs/build-status.md` current so a new coding session can continue from actual repository state rather than reconstructing work from chat.
6. Before release, reconcile every promised capability against tests, actual outputs, and unresolved issues. Publish claims supported by that evidence.

### Document map

- **Part A — Product, experience, generation, and canonical contracts**
- **Part B — Systems implementation**
- **Part C — Engineering implementation and numerical verification**
- **Part D — NYC data, jurisdiction, drawing package, and professional handoff**
- **Part E — Delivery milestones, acceptance, demo, submission, and coding-agent prompts**

**Precedence within this file:** Part A's settled product choices and normative field vocabulary govern integration. Parts B–D provide detailed implementation requirements. Part E governs delivery evidence. Where an example is narrower than the full requirement, the example does not remove the wider requirement. A future founder-approved change must be recorded in the decision log.

---

# Part A — Product, experience, generation, and canonical contracts

## A1. Product purpose and positioning

**Product promise:** Describe the home you want, explore a coordinated design, understand the consequences of changes, and prepare a traceable professional review package.

The primary user is a homeowner, not a CAD specialist. The application should translate ordinary requests into a structured brief and explain tradeoffs in ordinary language. Professional reviewers are secondary users who inspect geometry, assumptions, calculations, sources, and open decisions.

The initial product is English-language and uses US customary presentation units for the NYC demonstration. Store physical quantities in SI internally. Support a desktop-first design workspace; on smaller screens preserve chat, project review, and document access even if detailed drafting is better on a larger display.

The first jurisdiction is **New York City**, with an explicit NYC code profile and site-specific agency applicability. Do not equate NYC with all of New York State or all US jurisdictions. Future jurisdiction adapters can support other US authorities and Eurocode jurisdictions, but no Europe-wide or US-wide compliance claim belongs in this release. A future Eurocode profile will require the relevant national implementation and parameters, not a global “Eurocode” switch.

NodeSnap's distinctive demonstration should show that a change has consequences across the model: architecture changes, affected engineering results become stale, calculations rerun, and the exported documents update together. That coordinated behavior is the central technical story.

## A2. Settled decisions

| Decision | Binding choice |
|---|---|
| Company/product | NodeSnap; this project represents its pivot |
| Team | CEO and CTO, full-time; identify actual contributors in submission |
| Hackathon track | Startup |
| Recommended theme | Push the Frontier |
| Starting code | Fresh codebase; identify any subsequently reused components and licenses |
| Primary input | Homeowner text conversation and microphone transcription |
| Starting documentation | No existing house drawings required |
| Initial authority context | NYC DOB, with other agencies selected by actual site/work triggers |
| Demonstration use | New single-family residence |
| Storeys/program | Two above-ground floors; six principal rooms on each |
| Supporting spaces | Bathrooms, dressing, stairs, corridors, service spaces, walls and shafts additional to principal-room count |
| Basement | Approximately 3,000 ft² gross; indoor pool and supporting systems |
| Above-ground area | Approximately 6,000 ft² gross total, approximately 3,000 ft² per floor |
| Terrace | Occupied roof terrace; area separate from enclosed-floor targets |
| Materials | Steel primary frame; timber where suitable; reinforced-concrete substructure and pool |
| Architectural character | Contemporary luxury with refined stone, timber, metal, and glass |
| Equipment concept | All-electric baseline; evaluate actual equipment, code applicability and service requirements |
| Editing | Chat edits, draggable 2D objects, constrained 3D transform handles, synchronized selection |
| Engineering scope | Architecture, structure, foundations, HVAC, plumbing, electrical, energy, drainage, pool |
| Export scope | Coordinated PDFs, calculation reports, source/assumption/open-item registers, revision manifest |
| Professional handoff | Review and revision, followed by actual professional signing and authority submission outside this prototype |
| Development AI | Muse Code using Muse Wonder Full subscription |
| Application AI | Meta models only; explicit provider/model allowlist |
| Initial API credits | US$150; no assumption of another team member's credits |
| Technology decisions | Fixed in this document; founders delegated stack selection |
| Unavailable site facts | Retrieve when possible; otherwise preserve unknowns or label demonstration assumptions |
| Actual filing/signatures | Outside prototype; never simulate real signatures, seals, or approvals |

The event guide requires Meta integration. The team's **Meta-only AI** requirement is a stricter project constraint; do not attribute exclusivity to an unverified event rule. Ordinary deterministic libraries, databases, rendering engines, optimizers, and numerical solvers are allowed components of this design. They are not alternative AI providers.

## A3. Chosen villa program and demonstration defaults

### A3.1 Above-ground room program

Use the following program for the seeded demonstration. Counts refer to principal spaces, not bedrooms. The selected arrangement contains **five bedrooms in total**: one guest bedroom downstairs and a primary bedroom plus three additional bedrooms upstairs.

| Ground-floor principal room | Planning allowance |
|---|---:|
| Main living room | 620 ft² |
| Dining room | 300 ft² |
| Kitchen | 340 ft² |
| Family lounge | 360 ft² |
| Study/home office | 200 ft² |
| Guest bedroom | 260 ft² |
| **Principal-room subtotal** | **2,080 ft²** |
| Bathrooms/WCs | 180 ft² |
| Pantry/laundry | 120 ft² |
| Stairs and landings | 180 ft² |
| Circulation | 240 ft² |
| Walls, shafts, and service allowance | 200 ft² |
| **Ground-floor planning total** | **3,000 ft²** |

| Upper-floor principal room | Planning allowance |
|---|---:|
| Primary bedroom | 420 ft² |
| Bedroom 2 | 260 ft² |
| Bedroom 3 | 240 ft² |
| Bedroom 4 | 240 ft² |
| Library/lounge | 380 ft² |
| Flexible studio/fitness room | 300 ft² |
| **Principal-room subtotal** | **1,840 ft²** |
| Dressing spaces | 300 ft² |
| Bathrooms | 360 ft² |
| Stairs and landings | 180 ft² |
| Circulation | 200 ft² |
| Walls, shafts, and service allowance | 120 ft² |
| **Upper-floor planning total** | **3,000 ft²** |

These are **program allocations**, not a completed layout or prescribed minimum dimensions. The geometry generator must calculate actual net/gross areas and report differences. Walls and circulation cannot disappear to make an area total fit. Gross enclosed floor area, room net area, zoning floor area, and roof-terrace area are separate quantities with separate definitions.

### A3.2 Basement and roof

Start with this basement budget: pool hall/deck/lounge 1,500 ft²; pool and mechanical plant 400 ft²; storage 250 ft²; changing/shower/WC 250 ft²; stairs/circulation 250 ft²; walls, shafts and remaining service allowance 350 ft². Total: 3,000 ft².

A **flat-bottom conceptual pool with internal water dimensions of 8.0 m × 3.5 m × 1.4 m water depth** may seed the demonstration. Store its dimensions as editable assumptions. Model water, pool shell, pool-hall enclosure, deck, equipment, and services separately. Water depth is not shell depth or excavation depth. Pool shell thickness, reinforcement, founding arrangement, access safety, and equipment capacities remain outcomes of supported design methods or explicit review items. These concept dimensions prescribe none of those outcomes.

Start the roof terrace at approximately **900 ft²**, adjustable to the generated roof and verified constraints. It is a separately modeled occupied roof zone. Do not count it as an enclosed principal room or use it to inflate the 6,000 ft² enclosed-floor target. Track access, guards, waterproofing, drains/overflows, finishes, and equipment/planter loads where present.

Use local reference elevations for concept generation; actual grade, basement/cellar classification, floor-to-floor heights and permitted roof structures require project-specific determination. Do not hardcode a legal basement classification from the word used in the brief.

### A3.3 Design approach

Prefer legible structural grids and coordinated service zones. Create visual complexity through layered massing, facade setbacks where supported, glazing, shading elements, material quality, terrace composition, and the relationship between spaces. Do not introduce arbitrary transfer structures, large unsupported cantilevers, or unresolved double-height openings merely to look sophisticated.

Seed a plausible envelope near 279 m² per level and let the supported generator determine actual dimensions. A roughly 18 m × 15.5 m rectangle is an optional geometry fixture, not a required final footprint or verified site fit. Any setbacks or voids reduce actual enclosed area and must be reflected in the area schedule.

Favor useful adjacencies: kitchen–dining–living; guest room near an appropriate bathroom; study with some separation; stacked wet-service zones; a consistent stair core; direct maintenance access to pool/plant equipment. Do not route a bedroom's only access through another bedroom. Daylight and privacy preferences are optimization goals until applicable regulatory checks have been implemented. Open-plan living, dining and kitchen spaces may have separate IDs without artificial dividing walls; their area polygons must partition the floor without double counting.

For the initial structural topology, investigate a regular steel gravity frame with dedicated braced bays near the service/core zone, coordinated with circulation and openings. This is a declared concept idealization to be checked with the engineer, not an automatically qualified seismic system. Do not assign seismic coefficients, connection rigidity or diaphragm behavior from that label. Place timber secondary elements only where the selected exposure, fire and structural methods support them; an indoor pool's humidity can affect elements that never touch water.

### A3.4 Site strategy

The initial deterministic demo may use **Demo Villa NYC-01**, a synthetic site with a declared rectangular context, no real address and no BBL. If a starting size is needed, use a 30 m × 45 m context polygon; label it a scenario parameter, not a surveyed or entitled lot. It does not determine legal setbacks or allowable development.

Implement official-data adapters and screen a real NYC parcel using Part D. A real candidate replaces the synthetic context only after the data and uncertainty record are saved. Keep both modes available: reproducible synthetic geometry for software verification, and sourced public context for site-aware demonstration. Never attach invented measurements to a real parcel.

## A4. Product experience and interface requirements

### A4.1 Core journey

1. **Start:** Show a short value proposition and a prompt such as “Describe your home.” Offer the seeded villa example as a one-click starting point.
2. **Brief:** Interpret the request into a compact card: location status, use, floors, rooms, area target, materials, pool, terrace, priorities. Highlight what was stated, inferred, or assumed.
3. **Site:** Resolve supplied location or use the disclosed demo site. Display retrieved evidence, uncertainty, and blockers. Ask the homeowner for an address only if they want site-specific work.
4. **Generate:** Create a bounded number of valid candidate layouts. Show actual workflow stages and let the user inspect alternatives.
5. **Explore:** Keep plan, 3D view, object properties and chat synchronized through stable IDs.
6. **Calculate:** Show supported analysis cases, quantities, check outcomes, governing cases, assumptions and unresolved methods.
7. **Revise:** Accept a conversational change or drag. Preview the proposed change, commit a valid revision, invalidate affected outputs and rerun relevant work.
8. **Review/export:** Show document coverage and issues, preview generated sheets, then download a package tied to a specific revision.

Homeowners should not have to understand a model's tool-call vocabulary. Visible stages should be understandable: “Planning rooms,” “Checking connections,” “Calculating this load case,” “Updating drawings.” Do not show hidden model reasoning, JSON, raw stack traces, or an animated progress percentage without a measured basis.

### A4.2 Workspace layout

Use a restrained, high-quality interface with a dark charcoal navigation frame, light drawing canvas, clear typography, and one calm accent color. The building model and drawings should receive more space than decorative dashboard cards.

- A top bar shows project name, revision, save/job status, units, and export action.
- A collapsible left panel contains conversation and the brief.
- The central workspace supports Plan, 3D, Structure, Systems, and Documents.
- A contextual right inspector shows selected-object dimensions, materials, source basis, related results, and editable properties.
- A bottom activity strip shows actual running jobs and actionable issues; it does not replace detailed result views.
- Floor and layer controls persist across views. Include basement, ground, upper and roof/terrace levels.

Keep status labels in plain language. “Assumed groundwater level” is useful; “confidence 96%” is not a substitute for provenance. Use shape/text as well as color for result status.

### A4.3 Chat and microphone

Record microphone audio with the browser's media APIs and send bounded audio to the server for Meta transcription. Show recording state, stop/cancel controls, duration, and an editable transcript before it becomes a design request. Default to a maximum 60-second recording, configurable after actual provider limits are confirmed. Keep typed chat fully usable when microphone permission is denied.

Do not use the browser's speech-recognition service without establishing its model provider; the selected path is Meta transcription. Spoken audio replies are outside the initial requirement. Do not add an unverified TTS provider.

The conversation should distinguish a design preference from a confirmed site fact. “I want big glass walls” is a preference; “the soil can bear this pressure” is an engineering input requiring source classification. Ask targeted follow-ups only when the answer materially changes the project. In demonstration mode, propose a visible assumption instead of repeating questions already settled in the brief.

### A4.4 Editing and consequences

Implement select, pan, zoom, fit-to-view, floor selection, object inspection, snapping, dimension entry, undo and redo. Prioritize reliable wall/partition movement, room resizing within the supported grammar, opening placement, and equipment relocation over unconstrained freeform CAD.

Dragging provides a local preview. Commit once on release. A structural-object edit has a distinct impact summary; a nonstructural partition must not silently move columns. If an edit cannot preserve connections, reject it with the affected objects highlighted and a specific explanation.

In 3D, provide constrained translation/dimension handles for the same supported object operations. Restrict movement to the declared floor plane or supported axis, preserve snapping, and submit the same typed commands used by the 2D editor. Do not expose arbitrary transforms that can bypass wall, level or structural validation. Unsupported handles remain disabled with an explanation.

A valid example: “Moving this wall increases the living room by the calculated area, changes these partitions, and requires these load or systems results to be updated.” Only display consequences already computed. An invalid example: “Your home remains compliant” because the scene still renders.

Allow the AI to propose a repair after a failed check, but use the same typed command and validation path as a human edit. Require confirmation for a major program/material/system change, while allowing the normal generation workflow to apply the user's requested changes. This is product-level confirmation of a design choice, not a reason for the coding agent to stop routine implementation.

## A5. Layout generation and geometric validity

### A5.1 Bounded generative architecture

Use Meta to interpret the brief, classify room uses, propose adjacency and preference constraints, and explain alternatives. Use deterministic geometry software to construct and validate the layout.

Select **OR-Tools CP-SAT** for bounded room-placement constraints and **Shapely** for final planar checks. CP-SAT works over integer formulations; formulate the search on an explicit integer grid and convert to SI geometry afterward. Its feasible/optimal status describes the encoded problem, not building-code compliance. Source: [OR-Tools CP-SAT documentation](https://developers.google.com/optimization/cp/cp_solver).

Start with an orthogonal layout grammar: rectangular or supported composite room regions, horizontal floors, vertical walls, a limited set of envelope shapes, and explicit circulation/stair/service zones. Initially support a central-corridor topology and a side-corridor topology with a fixed stair/service core. Solve these families separately; do not begin with unrestricted corridor routing and simultaneous invention of the structural grid. Expose these capabilities in the product. A request outside the grammar should return the supported alternative and a recorded limitation, not distorted geometry.

Use a configurable 0.1 m planning grid for the first search, and a separate tighter numeric tolerance for geometric validation. The planning grid is a design-resolution choice, not a code tolerance. Preserve exact final coordinates from accepted operations; do not repeatedly round canonical geometry during display conversions.

### A5.2 Generation stages

1. Validate the brief and calculate the area budget.
2. Determine available envelope constraints. Distinguish sourced constraints from assumed scenario boundaries.
3. Reserve vertical circulation, necessary service zones, structural planning bands, and declared access points.
4. Solve room placement with non-overlap, envelope containment, area ranges, aspect-ratio bounds, mandatory adjacencies, and reserved-zone constraints.
5. Construct a circulation/access graph and place doors/openings through actual shared boundaries.
6. Create wall assemblies and subtract their thickness consistently; distinguish clear room dimensions from wall centerlines and outside dimensions.
7. Align supported stacked elements across levels and identify required structural/service transitions.
8. Derive linked architectural and analytical objects using explicit rules.
9. Run geometry, topology, and implemented regulatory checks.
10. Score valid candidates for declared preferences and return up to three alternatives.

Hard geometry constraints are not soft preference penalties. A layout with overlapping rooms or inaccessible spaces must be rejected even if its aesthetic score is high. Adjacency is insufficient without a usable doorway and connected circulation. Stair objects must connect actual levels; a symbol on a plan does not establish a viable vertical route.

Keep optimization bounded by wall-clock time, variable count and candidate count. Store solver status and seed/settings. Distinguish timeout with a feasible incumbent from infeasibility and invalid model configuration. Reproducibility under fixed settings matters more than claiming a globally optimal home.

Precompute permitted width/depth pairs for each room zone and constrain placement with allowed tuples and two-dimensional non-overlap. Bound preferences with integer penalties. Reserve corridor/core geometry first. Require a usable shared doorway segment, not a corner touch. Derive clear-room polygons from wall-centerline zones and actual wall assemblies, then recheck dimensions. When quantizing constraints, round minimum requirements upward and maximum extents downward so the search grid cannot weaken them.

Pin the solver version, sort inputs, use one solver worker, save the random seed and deterministic search budget, and retain an outer wall-clock limit. Verify the selected version's parameter names from its documentation rather than copying deprecated settings. Report native `solver_status` separately: `UNKNOWN` means no conclusion within the run; `INFEASIBLE` means no solution within the encoded supported family; `FEASIBLE` is sufficient for a candidate; `OPTIMAL` does not mean an optimal real-world house. Limit post-validation retries. Sources: [official CP-SAT Python API](https://or-tools.github.io/docs/python/classortools_1_1sat_1_1python_1_1cp__model_1_1CpModel.html), [solver parameters](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto).

### A5.3 First implementation and extension

Begin with a deterministic, explicitly labeled seed villa that exercises the entire data pipeline. Then make program parameters and constraints drive actual generation. By the final demonstration, changing a supported room/program parameter must produce a real model change; the interface cannot return the same hardcoded plan for every prompt.

Do not implement global structural optimization, arbitrary curved architecture, autonomous connection detailing for every condition, or unconstrained whole-house topology search before the baseline works. Preserve these as roadmap entries with explicit gaps. The first release's generative range should be measurable: supported envelope families, room count ranges, edit types, and constraints.

## A6. Canonical data contracts and normative status vocabulary

### A6.1 One authoritative model

All accepted changes create immutable revisions of one canonical building model. Frontend meshes, canvas objects, screenshots, narrative answers, and PDFs are derived views. They cannot independently own dimensions or calculation results.

Use stable UUIDs for domain entities. Use a UUID `revision_id`, a per-project integer `revision_number`, and a UUID/null `parent_revision_id`. A content hash identifies the exact canonical snapshot. Hash canonical serialization with stable ordering and finite-number handling; do not hash mutable UI state.

Canonical coordinates are local, right-handed, and **Z-up**. Store georeferencing separately, including source coordinate system, origin, and north rotation. Implement explicit adapters for screen coordinates, Three.js orientation, geographic data and solver axes. Test them with asymmetric geometry so swapped or mirrored axes are visible.

The snapshot contains project brief, site evidence, jurisdiction profile, geometry, assemblies, structural topology, service networks, assumptions, scenarios and requirement references. Calculation outputs and exported artifacts are separate immutable records referencing the snapshot.

### A6.2 Core entity inventory

| Entity | Minimum required content |
|---|---|
| Project | Owner/session, title, jurisdiction, brief version, current revision |
| ProjectSnapshot | IDs, content hash, schema version, UTC creation time, geometry/systems, input/evidence references |
| SiteContext | Site mode, identifiers if verified, boundary source, CRS, constraints, unknowns |
| JurisdictionProfile | Authority, effective/filing-date basis, code editions/amendments, rule versions |
| Level | Name, reference elevation, relationships to adjacent levels and grade evidence |
| Space | Use, principal/support classification, polygon, level, net area, adjacency/access |
| Wall/Openings | Assembly, geometry, host references, structural role if declared, dimensions |
| Slab/Roof/Terrace | Geometry, elevations, assembly, use/load zones, openings, drainage relationships |
| StructuralElement | Physical ID, analytical idealization, section/material, connections/supports, source properties |
| Network/Equipment | Discipline, endpoints, service/load requirements, route, selection/source status |
| PoolSystem | Water geometry, shell references, environment zone, plant and service interfaces |
| Assumption | Field/object, typed value, rationale, scenario, author, validity domain, review status |
| Evidence | Source URL/document, publisher, edition/version, retrieval date, hash, transformations and rights |
| EngineeringMethod | Declared domain, source, implementation version/hash, fixtures, review record |
| AnalysisRun | Snapshot, scenarios, input hash, solver/method versions, status, results |
| CheckResult | Requirement/method, quantities, comparison, scenario, provenance, outcome and freshness |
| Issue | Code, severity, object/sheet references, required resolution, owner role and state |
| ExportManifest | Export ID/basis hash, snapshot, result-set IDs, template version, files/pages, content hashes, coverage and review state; its own hash is stored externally |

Store source facts as typed records rather than loose prose. Distinguish the authority of the source from the way the field was acquired: an official tax map is still not a measured foundation survey.

### A6.3 Normative states

Use these exact machine values throughout the implementation. Human-readable labels can vary without changing the meaning.

| Field | Values | Meaning |
|---|---|---|
| `input_basis` | `official_dataset`, `project_document`, `user_supplied`, `demonstration_assumption`, `derived` | Origin of a quantity; derived quantities retain upstream origins |
| `method_state` | `research_required`, `implemented`, `verified_for_scope` | Verification of a method within its declared domain |
| `execution_status` | `completed`, `blocked`, `unsupported`, `error` | Outcome of an attempted discipline method |
| `check_outcome` | `pass`, `fail`, `not_evaluated`, `not_applicable` | Result of a specific applicable check |
| `freshness_status` | `current`, `stale` | Whether a result corresponds to active dependencies |
| `review_status` | `unreviewed`, `review_pending`, `reviewed_with_comments`, `reviewed_for_scope` | Recorded professional review, with reviewer/scope/revision |
| `document_presence` | `missing`, `partial`, `generated`, `export_verified` | Existence and export verification of a document |
| `authority_process` | `not_submitted`, `external_status_recorded` | No actual authority action in the prototype; later status needs evidence |
| `job_status` | `queued`, `running`, `cancel_requested`, `succeeded`, `failed`, `cancelled` | Queue execution lifecycle; distinct from engineering outcomes |

Each quantity/input has one scalar `input_basis`. A result-level `input_bases` array may aggregate the distinct bases of all upstream inputs; it must not replace their individual provenance records.

A method that is merely implemented may expose experimental quantities, but its check outcome remains `not_evaluated` until the claimed check is verified for its scope. A verified check using assumptions can pass its **assumed scenario**, with that qualification displayed. A stale historical pass remains historical; it cannot appear as a current result.

The frontend may group stages as Concept, Coordinated Draft, and Review Package. These labels are summaries of evidence, not global compliance states. Maintain `workflow_complete` separately from per-discipline `discipline_design_complete`. A review package can contain explicit open issues; the UI must identify that fact rather than imply immediate signing readiness.

### A6.4 Example blocked result

The following fixture is a contract example, not a result for the villa:

```json
{
  "result_id": "5e4df79b-ac1b-4bf1-8f4b-691f69ebedcc",
  "project_id": "7b7cbaca-71f3-4c55-a5cb-c17eebd671d0",
  "revision_id": "71b5024e-8214-4628-a06f-c884a2736f3b",
  "discipline": "foundations",
  "method_id": "foundation_bearing_review",
  "method_state": "research_required",
  "execution_status": "blocked",
  "check_outcome": "not_evaluated",
  "freshness_status": "current",
  "review_status": "unreviewed",
  "scenario_id": "baseline",
  "demand": null,
  "criterion": null,
  "derived_quantities": [],
  "input_bases": ["demonstration_assumption"],
  "evidence_ids": [],
  "issues": [
    {
      "code": "MISSING_INPUT",
      "field": "geotechnical_design_basis",
      "message": "A project geotechnical basis or an explicit demonstration scenario is required.",
      "owner_role": "structural_or_geotechnical_reviewer"
    }
  ]
}
```

The final schema must additionally include hashes, method versions, timestamps and object references defined above. Do not pass this small example off as the complete production schema.

### A6.5 Requirement and evidence graph

Each design requirement links to inputs, applicable method, resulting quantities/checks, affected objects, and affected sheets. Each revision records changed objects and invalidated dependencies. If an input cannot be traced, its derived claim cannot be marked verified.

Use content hashes for reuse of unchanged calculations, but only after demonstrating that the complete dependency set is included. Initially prefer safe recomputation of affected modules over clever caching that can hide a missing dependency.

## A7. Meta implementation policy

### A7.1 Development versus application access

Use **Muse Code + Muse Wonder Full** for repository work. Full is documented as a Muse Code subscription option; do not invent a Model API identifier for it. API keys can take precedence over browser subscription sign-in, so verify the actual coding authentication mode before assuming subscription access is being used. Sources: [Muse Code](https://dev.meta.ai/docs/muse-code), [authentication](https://dev.meta.ai/docs/muse-code/auth), [model availability](https://dev.meta.ai/docs/models).

Use `muse-wonder-1.0` for application reasoning. An optional `muse-spark-1.3` path can handle routine classification/summarization only after a small project-specific quality comparison. Default to Wonder when the task affects design interpretation. Model selection does not change the requirement for deterministic calculations.

Use `muse-voice-transcribe-1.0` for microphone transcription. Optional `muse-image-1.0` may produce mood/concept imagery clearly labeled illustrative; it must never be used as the source of dimensioned plans, member geometry or quantities. Do not add SAM or open-weight deployment merely to increase the number of Meta products named in the demo.

At integration time, list accessible account models through the documented Model API and record the actual returned IDs. If a specified ID is unavailable, surface the issue and select a verified Meta alternative through an explicit configuration change. No silent non-Meta fallback.

### A7.2 API adapter

Keep one server-side adapter for Meta requests at `https://api.meta.ai/v1`. Use the Responses API consistently unless a verified required capability necessitates another endpoint. Use direct HTTP or a compatible client configured only to Meta; do not let a client's default endpoint route inference elsewhere.

Keep model schemas small and stage-specific. Validate structured output twice: schema validation, then domain validation. The platform currently documents `tool_choice: "auto"` only; the application controller must invoke mandatory calculations itself. Do not use invented forced-tool settings or assume `strict` makes model-selected arguments physically valid. Sources: [tool calling](https://dev.meta.ai/docs/tool-calling), [structured output](https://dev.meta.ai/docs/structured-output).

Tool registry:

| Tool | Allowed purpose | Output |
|---|---|---|
| `read_project_summary` | Retrieve bounded current state | Brief and relevant object summaries |
| `lookup_site_evidence` | Query approved site adapters | Evidence envelope with provenance |
| `propose_program` | Structure homeowner requirements | Validated brief proposal |
| `generate_layout_candidates` | Invoke deterministic generation | Candidate IDs, geometry issues and scores |
| `preview_commands` | Evaluate a change without committing | Diff, impacts and validation issues |
| `commit_validated_commands` | Commit an authorized valid proposal through controller | New revision and affected dependencies |
| `request_analysis` | Enqueue supported deterministic methods | Job ID and declared scope |
| `read_results` | Retrieve bounded persisted results | Quantities, outcomes, assumptions and issues |
| `request_export` | Queue a snapshot-specific review package | Job ID and manifest basis |

The model cannot execute arbitrary scripts, SQL, shell commands or user-supplied URLs. Network access is through allowlisted adapters. A homeowner request is untrusted project input; it cannot override provider restrictions, authorization, source requirements or engineering validation.

Bind each model tool result to its call ID. Handle multiple calls, refusals, malformed output, partial results, rate limits and timeouts. Use application-level caps for custom-tool loops; a provider's built-in tool limit does not necessarily cap application-controlled custom calls. Save useful work before a bounded loop exits.

### A7.3 Credits and data

Keep coding-subscription usage and application API spending separate. Start with an application soft budget plan of US$20 for access/schema checks, US$45 for integration and evaluation, US$25 for rehearsals, and US$60 reserved for the final demonstration and retries. These are planning allocations, not token-price promises.

Set a configurable hard application reservation ceiling below the remaining credit balance, account for concurrent calls atomically, and expose spend to the team. Log observed token counts, model ID and current documented prices; provider billing remains authoritative. Recheck current rates before deployment. Source: [Meta pricing and rate limits](https://dev.meta.ai/docs/pricing-rate-limits).

Use Standard data handling where the account offers that choice unless the founder deliberately chooses another mode after reading its terms. Do not place real customer files, secrets, or private project details in a public hackathon repository. Publish synthetic fixtures and permissible public-data snapshots with source/license records.

### A7.4 Runtime configuration

Implement these application-owned configuration names; map the secret to the provider's documented authorization header in one adapter:

```dotenv
APP_ENV=development
META_BASE_URL=https://api.meta.ai/v1
META_REASONING_MODEL=muse-wonder-1.0
META_TRANSCRIPTION_MODEL=muse-voice-transcribe-1.0
META_API_KEY=
DATABASE_URL=
REDIS_URL=
ARTIFACT_ROOT=/data/artifacts
SESSION_SECRET=
APP_SPEND_CEILING_USD=135
MAX_MODEL_TURNS_PER_JOB=8
MAX_LAYOUT_CANDIDATES=3
MAX_AUDIO_SECONDS=60
DEMO_MODE=true
```

Only empty/example secrets belong in `.env.example`. Check the installed Muse Code authentication separately; exporting a runtime key into the coding-agent shell can change its access mode. Deployment credentials, DNS, billing changes and public posting remain founder-controlled actions.

---

# Part B — Systems implementation

## S1. Repository, processes, and ownership

Implement NodeSnap as one repository with a Next.js application and a Python application. Use React 19, TypeScript, react-konva 19, React Three Fiber 9, Three.js, Drei, and Zustand for the browser. Zustand manages interface state; it is not a second authoritative database. The documented React major-version pairings are requirements, not suggestions.[1][2]

Use Python 3.12, FastAPI, Pydantic, Shapely, OR-Tools CP-SAT, PyniteFEA, NumPy/SciPy, SQLAlchemy, Alembic, RQ, Redis, PostgreSQL, and ReportLab. Add PsychroLib through a verified adapter for supported psychrometric properties. Use pnpm for the web workspace and uv for the Python workspace. Start with Node.js 24 LTS as the build target and verify the selected stable Next.js/React dependencies in M0. Commit exact resolved versions in pnpm and uv lockfiles after an initial compatibility build. Install `PyniteFEA`, not the unrelated `Pynite` distribution. Its optional visualization dependencies are unnecessary because NodeSnap supplies its own viewer and reports.[3]

Use these directories:

- `apps/web`: application shell, chat, plan editor, 3D viewer, results, and document preview.
- `apps/api`: FastAPI routes, authentication, database models, orchestration, and worker entry point.
- `packages/domain`: Pydantic building models, edit commands, calculation contracts, and coverage records.
- `packages/geometry`: canonical geometry validation and derived geometry.
- `packages/engineering`: loads, solver adapter, material checks, and discipline calculators.
- `packages/reports`: drawing primitives, sheet templates, schedules, and PDF assembly.
- `packages/contracts`: generated OpenAPI document and TypeScript types.
- `tests/fixtures`: disclosed demonstration inputs and independently checked analytical examples.
- `infra`: Dockerfiles, Compose configuration, reverse proxy configuration, and deployment instructions.

Docker Compose runs `web`, `api`, `worker`, `postgres`, `redis`, and a TLS reverse proxy. API and worker use the same Python image and package versions. Persist PostgreSQL data, Redis queue data, and generated artifacts in named volumes. Keep the worker outside the API process so analysis cannot block ordinary requests. RQ executes ordinary Python functions in a background worker; FastAPI also distinguishes heavy background computation from small in-process tasks.[4][5]

Python owns business rules and all database writes. Next.js serves the interface and forwards same-origin API requests. Avoid separate Next.js and Python implementations of geometry or engineering decisions. Generate browser API types from FastAPI OpenAPI using `openapi-typescript`; Pydantic remains the schema authority.[6][7]

## S2. Canonical building model

Every project has one canonical, versioned building model. Architectural plans, structural analytical models, MEP overlays, the 3D scene, quantities, and reports are derived views. Neither Konva shapes nor Three.js meshes are persisted as the building definition.

Use stable UUIDs for domain objects. A project has a UUID `project_id`. Every accepted change creates a UUID `revision_id`, a `parent_revision_id`, and an integer `revision_number` that increases within that project. The UUID is the concurrency identity; the integer is a human-readable sequence. Create the number inside the same transaction that commits the revision.

The model contains site, levels, spaces, walls, openings, slabs, roofs, structural members, supports, material assignments, equipment, fixtures, water bodies, and explicitly declared design inputs. References between objects use IDs. Derived analytical elements retain references to their source architectural elements.

Use a right-handed local coordinate system: X and Y span the plan, and positive Z points upward. Define the site origin and true-north rotation explicitly. The browser adapter converts world Y to downward screen Y; it must never modify the domain coordinates to accommodate canvas conventions.

Use SI units internally: metres, square metres, cubic metres, newtons, newton-metres, pascals, kilograms, seconds, watts, joules, and kelvin. Use descriptive unit suffixes such as `height_m`, `force_n`, and `pressure_pa`. Convert display and document values to US customary units at presentation boundaries. Never store a bare number whose physical meaning depends on the current display-unit setting.

Record six main rooms per above-ground floor as a brief requirement, with bathrooms, circulation, stairs, utility spaces, and service areas separately classified. Treat the indoor basement pool and roof terrace as first-class elements with geometry, use, loads, and discipline dependencies. The pool's water volume, operating level, empty condition, equipment, and ventilation requirements cannot be inferred solely from its floor-plan rectangle.

Pydantic validates structure and types. Additional validators check geometry, topology, finite numbers, positive sizes, referenced IDs, nonzero member lengths, connected load paths, support definitions, and required engineering inputs. Shapely supports planar geometric operations; it does not replace three-dimensional structural analysis.[8]

## S3. Edits, transactions, and concurrency

All changes use typed commands, whether proposed through chat or initiated by dragging. Do not let a model replace the entire project JSON for a small edit. Each command includes a declared base revision and a UUID command ID. The server validates the complete proposed result before committing it atomically.

Example request body for a single wall translation:

```json
{
  "base_revision_id": "71b5024e-8214-4628-a06f-c884a2736f3b",
  "commands": [
    {
      "command_id": "6e08f997-65f7-4b11-8b3f-58e3e3c20c57",
      "type": "move_wall",
      "element_id": "109c04b1-f0dc-4df0-ab6b-e0a8d8591c17",
      "translation_m": {"x": 0.3, "y": 0.0, "z": 0.0},
      "preserve_connections": true
    }
  ]
}
```

These identifiers illustrate the contract and do not describe a complete designed building. A wall command is accepted only when its referenced objects exist and the supported connection-preservation rules produce valid geometry. Unsupported topology changes return a specific validation error.

For commands that change an existing building revision, send `If-Match` containing the quoted base-revision UUID as an HTTP entity tag, plus `base_revision_id` in the body and an `Idempotency-Key`. Require agreement between the header revision and body revision. Analyses and exports name an explicit target revision, which may be historical; they do not require it to be the current head. Session/project creation and job cancellation have their own preconditions and do not require a nonexistent or irrelevant building base revision.

Authenticate and authorize first, then look up the actor/endpoint/idempotency key and request-body hash. Return a previously completed matching response before checking whether the project head has advanced. A key reused with different content returns HTTP 409. For a new command request, atomically reserve the key, lock the project head, compare the base revision, validate the result, insert the immutable revision, advance the head, save the response and insert an audit event in one transaction. Handle concurrent identical in-flight requests through that unique key record without applying them twice. Return HTTP 412 when a new request's `If-Match` precondition is stale, HTTP 422 for invalid header/body agreement or domain validation failure, and HTTP 403 for an ownership failure. The UI treats a stale precondition as an edit conflict and reloads the current revision.

A command ID must never be applied twice. Use a transactional outbox for job dispatch so database commitment and queue delivery cannot leave a successful edit without its intended analysis request. Duplicate queue delivery is expected and must be harmless.

Undo creates a new revision from the selected earlier state; it never rewrites history. Ordinary users cannot edit past revisions. AI suggestions remain proposals until the controller commits their validated commands. A stale AI proposal must be regenerated against the new revision rather than silently rebased across structural changes.

## S4. REST contracts

Use `/api/v1` as the public prefix. Return JSON envelopes with a `request_id`. Error envelopes contain `code`, a short actionable `message`, and structured field or element references; never include stack traces or credentials.

| Route | Contract |
| --- | --- |
| `POST /demo/sessions` | Create an isolated demonstration actor and secure session cookie. |
| `POST /projects` | Create a project from a brief; return project and initial revision identifiers. |
| `GET /projects/{project_id}` | Return current revision metadata, summary, and permissions. |
| `GET /projects/{project_id}/revisions/{revision_id}` | Return the immutable canonical snapshot. |
| `POST /projects/{project_id}/commands` | Validate and atomically commit typed changes; return the new revision and invalidated result groups. |
| `POST /projects/{project_id}/conversations` | Accept text and a base revision; create an orchestration job. |
| `POST /projects/{project_id}/transcriptions` | Accept bounded audio, call Meta transcription, and return editable transcript text. |
| `POST /projects/{project_id}/analyses` | Queue supported calculations for one explicit revision. |
| `GET /projects/{project_id}/coverage?revision_id=...` | Return per-discipline methods, prerequisites, results, and gaps. |
| `GET /jobs/{job_id}` | Return job state, target revision, stage, progress, and result references. |
| `POST /jobs/{job_id}/cancel` | Record a cancellation request; return the current state. |
| `GET /projects/{project_id}/events` | Stream resumable server-sent events for authorized project activity. |
| `POST /projects/{project_id}/exports` | Queue a PDF package for an explicit revision and coverage snapshot. |
| `GET /artifacts/{artifact_id}` | Authorize and download an immutable artifact. |

Do not use an unspecified “current project” inside a calculation or export request. Every such request names its revision. Return HTTP 202 and a job URL for queued work. Use narrow response models; never expose raw database rows.

## S5. Job lifecycle and events

Persist jobs in PostgreSQL. Redis transports queue messages; it is not the sole record of a calculation. Jobs transition from `queued` to `running`, then to `succeeded`, `failed`, or `cancelled`. A queued or running job may enter `cancel_requested`; the worker checks this state between bounded stages. A completed job cannot later become cancelled. Define this race explicitly in the worker transaction.

Jobs include `job_id`, `project_id`, `revision_id`, `job_status`, `kind`, `stage`, `attempt`, `created_at`, `started_at`, `finished_at`, `heartbeat_at`, `error_code`, and `result_refs`. Do not report fabricated percentages. Prefer stage labels and completed/total item counts when the amount of work is known.

Use a lease or row lock so only one worker owns a job attempt. Configure timeouts for model calls, analysis, and reporting. Retry transient transport errors with exponential backoff and jitter. Do not retry invalid geometry, unsupported methods, or missing engineering inputs as if they were network failures. Retry only idempotent operations; persist completed stage outputs before continuing.

Store project events with a monotonically increasing `event_sequence`. SSE event IDs use that sequence, and `Last-Event-ID` resumes delivery. If retained events are unavailable, emit a resynchronization instruction and have the browser reload current job and project state. Example event data:

```json
{
  "event_sequence": 42,
  "type": "analysis.stage_completed",
  "project_id": "7b7cbaca-71f3-4c55-a5cb-c17eebd671d0",
  "revision_id": "71b5024e-8214-4628-a06f-c884a2736f3b",
  "job_id": "efb25e52-98f3-48f3-a1b0-2b79fbd7c46f",
  "stage": "validate_geometry",
  "completed_items": 1,
  "total_items": 1
}
```

A successful old-revision job remains successful historically. Its freshness is derived by comparison with the active revision and calculation-input hash. The UI must not display that result as current. Reusing an unchanged numerical payload requires a new result binding to the target revision after verifying its complete dependency hash; retain the original run ID as provenance. Otherwise recompute. Export result bindings must all target the frozen export revision. Network reconnection must not restart an already accepted edit or job.

## S6. Bounded Meta orchestration

Use `muse-wonder-1.0` through `https://api.meta.ai/v1` for application reasoning. Muse Wonder Full is a development-time Muse Code option, not a runtime API model. Do not invent a Full API identifier or assume raising reasoning effort selects it. Use `muse-voice-transcribe-1.0` for microphone transcription; the documented model returns text, not synthesized speech.[9]

Implement one controller with typed stages: interpret brief, propose commands, validate proposal, commit revision, derive analysis inputs, calculate, evaluate coverage, and summarize. The controller invokes required deterministic stages directly. Additional agents may assist development, but the running product must not give several language-model personas concurrent authority over building state.

Use schema-constrained output for proposals. Meta supports JSON Schema through Responses `text.format` or Chat Completions `response_format`. Generate small stage-specific schemas from Pydantic, then adapt them to Meta's supported strict subset. Validate the adaptation in a contract test. All strict object properties are required and extra properties are forbidden; represent optional values explicitly with nullable types where supported. Avoid recursive schemas and deep whole-building payloads.[10]

For developer-defined tools, only expose stage-appropriate, allowlisted functions. Meta currently supports only `tool_choice: "auto"`; do not send `required`, `none`, or a forced function name. Function-tool `strict` validates the supplied schema subset and is not a substitute for server-side argument validation. Handle plain-text responses when the workflow expected a proposal. Reject invalid or incomplete outputs and provide a bounded repair opportunity.[11]

Default caps per orchestration job: eight model turns, two proposal repairs, three candidate layouts, and one active mutation stage. Use per-request timeouts and output-token limits. On reaching a cap, save useful work and return a clear recoverable status. Never continue an unbounded “improve until perfect” loop.

The model may propose typed geometry operations, select from documented options, request existing results, and explain validated outputs. It may not execute arbitrary Python, JavaScript, SQL, shell commands, downloaded scripts, or URLs supplied by a homeowner. Treat prompts, uploaded text, and transcripts as project input, never as executable instructions or authority to change system rules.

Persist stage inputs, validated outputs, model identifier, request identifier, latency, token usage, and tool-result references. Store concise user-facing explanations, not private model reasoning. A second language-model review cannot establish the correctness of a numerical solver.

## S7. Calculations, provenance, and coverage

Separate structural analysis from design checks. Pynite computes supported structural responses; purpose-built checks evaluate those responses using declared methods, inputs, material data, and applicable limits. Pynite's documented beam-column formulation omits transverse shear deformation, and linear analysis cannot silently stand in for required nonlinear or second-order analysis.[12][13]

Every result stores its revision, canonical input hash, engine version, method identifier, units, assumptions, source inputs, reference edition, verified source links, and validation-fixture identifier. Provenance distinguishes user-confirmed input, explicit demonstration assumption, referenced data, and calculated quantity. Unknown soil, groundwater, equipment performance, or site conditions remain missing inputs until supplied.

Use the normative Part A fields: `execution_status` is `completed`, `blocked`, `unsupported`, or `error`; `check_outcome` is `pass`, `fail`, `not_evaluated`, or `not_applicable`; `method_state` is `research_required`, `implemented`, or `verified_for_scope`. Keep `freshness_status` separate. Missing inputs cannot produce a passing check. A method that has not been verified for its declared scope may expose experimental quantities, but its claimed check remains `not_evaluated`.

The coverage registry lists architecture, structure, foundations/basement, pool, roof terrace, electrical, plumbing, ventilation, energy, drainage, and document requirements. For each, declare implemented calculations and exclusions. Pool water load accounting does not establish pool-shell design; a ventilation schedule does not establish moisture-control performance. Report exact calculated quantities and unresolved work without converting partial coverage into an overall compliance badge.

Reject nonfinite results, unstable models, missing load paths, invalid units, and unsuccessful solver convergence. Verification fixtures should include hand-checkable beams and frames, equilibrium checks, unit conversions, and deliberately invalid inputs. Store failures as structured outcomes that the UI can explain.

## S8. Editor behavior and export integrity

During a drag, update an optimistic local preview and show snapped dimensions. Rebuild adjacent visual geometry from the preview model. Do not make a model API call on pointer movement. On pointer release, submit one typed command with the base revision. If validation fails, restore the last committed geometry and highlight the affected elements. If the base is stale, reload and offer a fresh edit; do not silently discard another accepted change.

Selection IDs are shared between plan and 3D views. Changing the active floor affects visibility, not stored geometry. Show calculations as pending after a relevant edit and retain old results only with their revision label. Undo/redo must use the same revision system as chat edits.

An export job freezes an `export_id` and an `export_basis_hash` covering its revision, coverage snapshot, calculation-result set and report-template version. Render files using that fixed identity/basis, then compute the generated files' content hashes, create the final artifact manifest, and hash that manifest. Store the final manifest's own hash outside the manifest bytes. Do not embed a final manifest hash inside a file that the same manifest hashes, or embed a file's own content hash into itself; both create circular definitions. ReportLab draws plans and diagrams from canonical coordinates and paginates schedules and calculations.[14][15] Never assemble a PDF from whichever results happen to be latest when each page renders.

If the project changes during export, the package remains a valid historical export and is labeled with its original revision. The interface offers a new export for the current revision. Include review status, assumptions, missing inputs, source references, and a machine-readable manifest alongside the PDF. Use a persistent artifact ID and content hash; never overwrite an artifact in place.

## S9. Demonstration access, abuse limits, and observability

Provide isolated guest demonstration sessions using an opaque server-generated token in a Secure, HttpOnly, SameSite cookie. Store only its hash server-side. Check ownership on every project, job, and artifact request. Optional sharing creates a read-only token; it never grants mutation or API-spending authority. Seed demonstration projects are copied per actor, not edited globally.

Validate request origins for cookie-authenticated mutations, restrict CORS, cap request bodies and audio duration, and keep credentials server-side. Configure limits for projects, two simultaneous jobs per actor, job submissions per minute, and model usage. Bound numerical input sizes and model complexity before enqueueing expensive work.

Track observed Meta token charges and reserve a conservative estimated allowance before each call. A configurable application spending ceiling stops new model work before exhausting the intended budget; actual provider billing remains authoritative. Never assume a notification is a hard spending limit. Log request IDs, revision IDs, stage latency, failure categories, queue depth, and estimated cost without logging secrets. Preserve usable non-AI editing and existing artifacts when a model call is unavailable.

## S10. Primary implementation references

1. React Three Fiber version compatibility: https://r3f.docs.pmnd.rs/getting-started/introduction
2. React Konva compatibility and canvas behavior: https://konvajs.org/docs/react/index.html
3. Pynite package installation: https://pynite.readthedocs.io/en/latest/installation.html
4. RQ queues and workers: https://python-rq.org/docs/
5. FastAPI background-task guidance: https://fastapi.tiangolo.com/tutorial/background-tasks/
6. Pydantic JSON Schema: https://docs.pydantic.dev/latest/concepts/json_schema/
7. OpenAPI TypeScript: https://openapi-ts.dev/introduction
8. Shapely planar geometry: https://shapely.readthedocs.io/en/stable/manual.html
9. Meta model catalog and availability: https://dev.meta.ai/docs/models
10. Meta structured output: https://dev.meta.ai/docs/structured-output
11. Meta tool calling: https://dev.meta.ai/docs/tool-calling
12. Pynite member assumptions: https://pynite.readthedocs.io/en/latest/member.html
13. Pynite analysis methods: https://pynite.readthedocs.io/en/latest/analysis.html
14. ReportLab vector drawing: https://docs.reportlab.com/reportlab/userguide/ch2_graphics/
15. ReportLab document layout: https://docs.reportlab.com/reportlab/userguide/ch5_platypus/

---

# Part C — Engineering implementation and numerical verification

## E1. Binding engineering objective and supported example

Build the engineering services behind NodeSnap's homeowner experience: conversation and microphone input produce a coordinated building model; direct edits update that model; deterministic calculations explain consequences; the platform exports the complete requested set of discipline documents for professional review. The target includes architecture, structural engineering, foundations, HVAC, plumbing, electrical engineering, energy, drainage, and the indoor pool. Do not delete a discipline or substitute an empty screen to meet the deadline.

The demonstration program is a new single-family NYC villa with approximately 6,000 square feet above grade and a 3,000-square-foot basement, two above-grade storeys, six main rooms on each above-grade floor, additional bathrooms/circulation/utility spaces, an indoor basement pool, and an occupied roof terrace. These areas are program targets, not structural dimensions or permissible zoning floor area. Use steel for the principal superstructure, timber secondary elements where applicable, and reinforced concrete for the substructure and pool shell. Material selections do not establish approved construction type, fire resistance, or a structural system.

The full product target is a coordinated package that qualified professionals can review, complete where necessary, sign, and submit. The prototype must report its actual calculation coverage and unresolved requirements. Maintain two separate acceptance records: `workflow_complete`, covering the operating end-to-end experience, and `discipline_design_complete`, covering verified engineering scope. A completed workflow cannot set the second record automatically. If a planned capability remains unimplemented, record the specific gap and affected sheets; do not describe the original full target as achieved.

This part specifies implementation contracts. It does not provide member sizes, foundation dimensions, equipment capacities, code factors, or a design for the demonstration house. Numerical examples below are independent software verification fixtures only.

## E2. Source-controlled methods and honest result states

Implement a method registry before implementing compliance checks. Each `EngineeringMethod` requires an ID, version, discipline, purpose, equations or executable procedure, unit conventions, input domain, exclusions, source title/edition/section, source URL or licensed-document reference, rights/access record, reference test cases, reviewer record where available, and implementation hash. A method's `method_state` becomes `verified_for_scope` only after its stated applicability and reference tests pass. This is implementation verification, not professional approval of an entire project.

Every code-compliance algorithm must have a reliable, lawfully available method source and the correct applicable edition. A model's recollection, search snippet, or plausible coefficient is insufficient. Store individual coefficients as sourced inputs; never embed an unidentified constant inside a formula. Ordinary physical equations and analytical fixtures may be implemented from explicit derivations without claiming they constitute a code check. Distinguish a physical capacity estimate from a code-prescribed design resistance.

The jurisdiction profile must identify separate construction, energy, electrical, and referenced-standard editions, plus relevant amendments. NYC's official structural chapter expressly modifies ASCE 7 and specifies structural information for drawings; it is not an instruction to use whichever ASCE edition an API defaults to. Inspect the adopted reference and amendments before implementing hazard retrieval or combinations. [NYC 2022 Building Code, Chapter 16](https://www.nyc.gov/assets/buildings/codes-pdf/cons_codes_2022/2022BC_Chapter16_StructuralDesignWBwm.pdf).

Use independent status fields rather than one green indicator:

| Field | Required values and meaning |
|---|---|
| `input_basis` | `official_dataset`, `project_document`, `user_supplied`, `demonstration_assumption`, or `derived`; derived values retain the full provenance chain |
| `method_state` | `research_required`, `implemented`, or `verified_for_scope` |
| `execution_status` | `completed`, `blocked`, `unsupported`, or `error`; queued/running states belong to the separate job lifecycle |
| `freshness_status` | `current` or `stale`, evaluated separately from historical execution |
| `check_outcome` | `pass`, `fail`, `not_evaluated`, or `not_applicable`; applicability exclusions require reasons |
| `review_status` | `unreviewed`, `review_pending`, `reviewed_with_comments`, or `reviewed_for_scope`; record reviewer, scope and revision |

A calculated value based on demonstration assumptions can be useful. Label its check as “passes this assumed scenario,” never as an unqualified code-compliance result. Unknowns are nullable values with reasons, not zeros. `NOT_IMPLEMENTED`, `MISSING_INPUT`, `OUTSIDE_METHOD_DOMAIN`, `UNVERIFIED_SOURCE`, `UNSTABLE_MODEL`, and `STALE_REVISION` must be machine-readable issue codes. A successful API response or converged solver does not mean a check passed.

## E3. Common module contract and units

All discipline services consume an immutable `ProjectSnapshot`. It includes `project_id`, `revision_id`, content hash, jurisdiction-profile version, source/evidence IDs, canonical geometry, systems, approved assumptions, and requested analysis scenarios. Services return a `DisciplineResult` containing the same revision identifiers, method/solver versions, evaluated scenarios, derived quantities, checks, issues, drawing primitives, schedules, and dependency IDs. Store the exact inputs and outputs needed to reproduce a run.

Each derived quantity has an object ID, quantity type, value, unit, source inputs, method ID, and scenario ID. Each check additionally records demand, allowable/resistance or criterion, comparison operator, governing case, applicability decision, and outcome. A missing resistance cannot produce a utilization ratio. Do not divide by zero or replace an unavailable value with an arbitrary “safe” capacity.

Use SI internally: metres, square/cubic metres, newtons, pascals, kilograms, seconds, watts, joules, amperes, volts, and radians. Store temperature as a typed quantity distinguishing absolute temperature from temperature difference. Present NYC drawing dimensions in the selected US customary format while preserving unrounded internal values. Unit conversions must occur at validated boundaries. Declare whether a library's density input means mass density or weight density; an ambiguous solver parameter must block adapter verification.

Separate `geometry`, `analysis`, `design_checks`, and `drawing_generation`. A drawing module may format an analysis result but may not calculate a new engineering value invisibly. A language model may request whitelisted operations and explain returned results; it may not supply the final numerical result in place of those operations. Prefer deterministic functions with typed inputs over generated scripts executed during a customer session.

## E4. Architecture and canonical geometry

The architecture module converts the confirmed program into rooms, circulation, vertical connections, enclosure, openings, and service zones. Its input includes program areas, relationships, site constraints, floor elevations, supported shape grammar, and declared architectural assumptions. Its output includes persistent room/object IDs, polygons, boundaries, adjacency, dimensions, usable/gross area schedules, elevations, sections, door/window schedules, and a list of applicability checks.

Generate architectural and analytical geometry separately, linked by IDs. A decorative wall mesh is not automatically a load-bearing member. Every structural object must identify its physical counterpart, support/load role, orientation, and analytical idealization. Likewise, each duct or pipe schematic must identify actual endpoints even before its detailed route is resolved.

Validate closed non-self-intersecting room boundaries, positive areas, non-overlapping occupied spaces, consistent floor levels, opening-to-host relationships, and connections between circulation/stair objects. The program count must distinguish six main rooms from bathrooms, corridors, and utilities. An area budget must identify differences between target and generated areas; it must not adjust displayed totals to conceal a mismatch.

Keep geometric checks separate from regulated checks. Detecting a stair without a connection is a topology error. Judging stair width, headroom, travel distance, guards, accessibility, fire separation, or allowable area requires the applicable sourced rule. Missing rule implementation generates a named review item, not a pass.

Use constrained editing with snapping and a reversible transaction. A drag previews the changed geometry and its consequences; validation either commits the new revision or returns actionable issues. Moving a partition does not silently move a column. Moving a column does not silently change its support or connection type. Architectural openings that intersect structural or MEP objects create coordination issues requiring resolution.

## E5. Structural loads, analysis, and design checks

Implement three independent services: `build_load_model`, `solve_structure`, and `evaluate_structural_checks`.

`build_load_model` consumes geometry, source-controlled assemblies/materials, occupancy/use assignments, equipment weights, pool scenarios, terrace use, hazard/site data, and a verified combination method. Return load objects with physical origin, load case, direction, magnitude/unit, application region, and transfer rule. Track self-weight ownership so the same member is not included by both the adapter and an explicit load. Do not turn an area load into a line load without recording its tributary area or transfer procedure.

The planned load coverage includes gravity, occupancy, partitions, equipment, wind, snow, rain/ponding, seismic effects, pool water, earth pressure, groundwater, and applicable construction scenarios. Applicability is assessed per case. Missing site or method inputs block that case while leaving unrelated supported calculations available. Never use a single arbitrary lateral load as a substitute for completed wind and seismic design.

The roof terrace is an occupied roof. Distinguish its occupancy, finishes, permanent landscaping if present, equipment, guard/parapet actions, drainage, and snow/wind exposure. Maintain separate saturated/dry assembly quantities where relevant. Do not reuse an unoccupied-roof load by convenience. No terrace load or combination coefficient is specified here; obtain the applicable value and limitations from the selected code method.

`solve_structure` consumes a validated analytical graph: nodes, member axes, sections, materials, releases, supports, diaphragms/constraints, physical connection assumptions, and load scenarios. It returns displacements, member forces, reactions, equilibrium residuals, diagnostic information, and governing scenarios. Record the physical justification for constraints. Reject disconnected nodes, zero-length members, invalid section properties, missing supports, and unsupported nonlinear behavior. Never cure instability by adding fictitious restraints or making a connection rigid without a corresponding declared design change.

Use a pinned PyNite release behind an adapter for the bounded elastic frame work. The official documentation distinguishes linear analysis from models with nonlinear features and describes stability/statics diagnostics. Verify the selected release's actual API and behavior before integration. Its support for an analysis option is not evidence that all structural design requirements have been met. [PyNite analysis](https://pynite.readthedocs.io/en/latest/analysis.html), [model API](https://pynite.readthedocs.io/en/latest/FEModel3D.html), and [stability](https://pynite.readthedocs.io/en/latest/stability.html).

`evaluate_structural_checks` consumes solver demands plus verified material-design methods. Planned steel checks must address their applicable strength, stability, serviceability, and connection requirements; timber checks must identify the relevant material/product properties, orientation, modification factors, connections, and service conditions. Reinforced-concrete substructure checks are a separate implementation. Do not substitute elastic bending stress divided by yield stress for every required steel limit state, or divide a reaction by soil bearing pressure and call that a completed foundation design.

Use one explicit lateral-force-resisting-system assumption for each supported baseline. Document how diaphragm loads reach that system and foundations. A braced frame, moment frame, and gravity frame are not interchangeable labels. Seismic system coefficients, mass participation, analysis eligibility, torsion, vertical irregularity, drift, stability, diaphragm, and connection/detailing requirements each need the appropriate implemented method or a visible gap. A coloured deformation animation is a visualization of a stated analysis case, not proof of earthquake performance.

The structural engineer's review should target the baseline idealization, load paths, selected methods, benchmark outputs, and governing scenarios. Record its actual scope. Do not infer that their availability validates unreviewed HVAC, electrical, foundation, or pool methods.

## E6. Foundations, excavation, and groundwater

`foundation_assessment` consumes foundation geometry, support reactions by combination, basement/pool levels, soil profile, bearing parameters, groundwater scenarios, adjacent structures, and excavation assumptions. The result includes reaction transfer, pressure distributions for supported methods, screening/design checks, a foundation plan, sections, and unresolved site requirements.

Each soil parameter must identify a project report or a demonstration assumption, its depth range, unit, interpretation, and applicability. Public map information cannot become a site-specific bearing value, settlement parameter, groundwater measurement, or excavation recommendation merely because it contains a soil label. The prototype may run explicitly assumed scenarios, with that basis visible in every affected result.

Represent the pool shell, basement slab, retaining walls, and primary footings as distinct objects. Record whether a pool bears independently on soil or transfers load into the building; prevent double counting. Consider full-pool, empty-pool, and groundwater scenarios where applicable. Unsupported uplift, retaining-wall, settlement, sliding, overturning, punching, reinforcement, and excavation checks remain enumerated gaps.

A reaction-based preliminary bearing calculation is a real calculation within its stated domain. Its output must say which action resultant and pressure assumption were used. It cannot imply settlement or reinforcement adequacy. Drawing details generated without a verified detailing method must be labelled schematic and tied to open review items rather than shown with invented reinforcement sizes.

## E7. Indoor pool as a coupled engineering system

Create `PoolSystem` as a first-class subsystem linking water geometry, shell, enclosure, HVAC zone, water treatment, circulation, heating, drainage, equipment loads, and electrical requirements. ASHRAE's official indoor-pool guidance describes the combined importance of humidity, envelope performance, ventilation, and water treatment; an ordinary residential sensible-load calculation does not cover this subsystem. Its public page was inspected, but the empirical evaporation method and its coefficients still require exact method transcription, applicability review, and tests before implementation. [ASHRAE indoor swimming pools](https://handbook.ashrae.org/Handbooks/A23/SI/A23_Ch06/a23_ch06_si.aspx).

Implement a pure `pool_quantities` function first. For a simple declared basin geometry, compute surface area and water volume. Calculate mass as `rho_water * volume`, water weight as `mass * g`, and hydrostatic pressure as `rho_water * g * depth` within the hydrostatic model. Density and gravitational acceleration must be explicit physical-property inputs with documented units and basis. They are not code factors. A complex/sloped basin requires a validated geometric integration method; do not use bounding-box volume.

Then implement a `pool_environment` contract with water temperature, room temperature/humidity, ambient pressure, outdoor conditions, cover state/schedule, activity assumption, water features, wet-deck representation, and the selected evaporation method. Return moisture generation, latent energy transfer, pool heat balance terms, zone load contributions, and unresolved equipment-selection tasks. Do not insert an undocumented “residential pool factor.”

Use explicit mass and energy accounting: moisture generation is measured as mass per time; multiplying an evaporation rate by a documented latent heat in compatible units gives latent power. Pool water warm-up energy is `mass * specific_heat * temperature_change`, which is not the same as steady operating heat loss. Identify heat recovery once, with its boundary and destination, so recovered heat is not credited twice. Equipment electrical input is not identical to its useful heating or moisture-removal output.

For psychrometric properties, a pinned PsychroLib adapter is a candidate. Its repository documents SI/IP support and the method basis; verify each selected function's units, domain, and version against reference cases. It does not calculate a complete natatorium design. [PsychroLib](https://github.com/psychrometrics/psychrolib).

The pool results must connect to an envelope condensation review, ventilation/exhaust strategy, treatment/circulation equipment, service clearances, drainage, electrical loads, and protection/bonding requirements. Until the relevant methods are implemented, these remain named review tasks. The interface must never mark the indoor-pool environment complete solely because a heater or generic air conditioner appears in the model.

## E8. HVAC and mechanical systems

`mechanical_design` consumes room geometry, envelope assemblies, design weather, indoor conditions, occupancy/equipment schedules, ventilation method, and pool results. Output a room/zone load ledger, system zoning, supported ventilation calculations, selected equipment records, schematic ducts/pipes, schedules, controls intent, and mechanical sheets.

Compute each supported heat-transfer component transparently. For an applicable steady conduction calculation, `U * area * temperature_difference` produces heat flow; document the assembly basis and boundary conditions. This is one component, not a full cooling-load method or statutory energy analysis. Solar gains, infiltration, ventilation, thermal storage, latent loads, and operating schedules require their own sourced methods and domains.

Keep ordinary dwelling zones separate from the pool zone. Carry pool moisture, ventilation, and heat-recovery quantities through named interfaces rather than multiplying an ordinary room load by a guessed allowance. A missing latent method blocks pool equipment sizing but does not block geometric coordination or verified water-load calculations.

Represent every proposed equipment item with manufacturer/model evidence if selected, operating conditions, capacity type, input power, and suitability status. When no equipment is selected, show a required performance envelope and placeholder equipment volume labelled unselected. Do not invent a product or claim a catalogue name satisfies calculated duty without checking the relevant rated conditions.

Routing must connect endpoints and detect geometric conflicts and required service zones. A route that fits does not establish pressure-drop, airflow, noise, fire-damper, or installation compliance. Store those as individual method-backed checks. The sheet and equipment schedule must agree about every equipment ID and zone served.

## E9. Plumbing, domestic water, and pool services

`plumbing_design` consumes fixture inventory, room uses, equipment connections, supply conditions, vertical levels, discharge assumptions, and applicable sizing methods. Output fixture/connection schedules, supported demand calculations, domestic hot-water quantities, cold/hot water and drainage/vent network diagrams, equipment connections, and outstanding requirements.

Model supply, domestic hot water, sanitary drainage, venting, stormwater, pool circulation, pool discharge, and any groundwater management as distinct networks. Connections between them require a defined, reviewed interface. Do not automatically discharge pool water into a storm line or merge basement drainage into an arbitrary nearest pipe.

Each network edge records endpoints, material/product if known, diameter if actually determined, length, elevation change, and calculation state. Each node records fixture/equipment identity and demand basis. Conservation checks must detect disconnected fixtures, unserved equipment, and inconsistent aggregate demand. Fixture-unit values, simultaneity/demand methods, permissible slopes, venting, backflow, and discharge requirements require sourced rules; do not replace them with generic percentages.

For below-grade fixtures, compare elevations against the declared downstream connection conditions. Unknown sewer invert or connection information creates a review task. Do not infer gravity drainage just because the line is drawn downhill in a plan view. When pumping is proposed, track required duty calculation, selected equipment, electrical connection, and alarm/control dependencies.

The pool module supplies water volume and equipment interfaces; plumbing owns supply/discharge networks and their checks. Pool treatment/circulation sizing requires its separate applicable method. A complete-looking pipe diagram is not evidence that those specialist methods have run.

## E10. Electrical systems

`electrical_design` consumes room uses, lighting/receptacle program, declared supply system, appliance schedules, mechanical/pool equipment input requirements, and verified electrical methods. Return connected-load and demand-load schedules, circuit/panel assignments, a single-line schematic, equipment connections, plan symbols, and check coverage.

Distinguish real power, apparent power, power factor, efficiency, voltage, phase, and current. Conversion between watts and amperes requires the declared circuit model and applicable inputs. Thermal output from a heat pump or pool heater must not be used directly as electrical input. Demand factors, conductor ampacity, derating, protection, fault conditions, grounding/bonding, and special-location requirements need the adopted NYC electrical method.

Build an electrical dependency graph: each equipment item is supplied exactly once; each circuit terminates at an identified panel; every panel has a defined upstream relationship or a visible missing-service issue. Verify schedule totals independently. Track load changes from HVAC/pool revisions, and invalidate upstream sizing/checks when those inputs change.

Represent pool-area electrical requirements explicitly in the coverage manifest. Do not mark them satisfied because symbols were placed on a drawing. Require actual methods and details for the checks that are claimed. The current code profile must use the appropriate NYC electrical edition and amendments rather than assuming the newest national NEC edition. [NYC Electrical Code](https://www.nyc.gov/site/buildings/codes/electrical-code.page).

## E11. Energy and envelope

`energy_assessment` consumes envelope areas/assemblies, fenestration, infiltration/ventilation assumptions, system properties, schedules, and the selected compliance pathway. Output an auditable component ledger, supported thermal quantities, pathway-specific checks, required testing/documentation items, and energy sheets.

The official DOB page identifies the 2025 NYCECC for relevant complete applications from March 30, 2026. Keep this edition distinct from the construction-code edition. Determine the appropriate residential pathway and its project applicability before encoding criteria. [NYC Energy Conservation Code](https://www.nyc.gov/site/buildings/codes/energy-conservation-code.page).

Do not equate a lower calculated heat loss with code compliance. The method must account for the applicable mandatory provisions and pathway requirements. If a required compliance tool or licensed method has not been integrated, label the calculated quantities as an energy review input and list the missing analysis; do not fabricate an official report or certificate.

Envelope assemblies must preserve each layer/material definition and source. Distinguish nominal insulation value from whole-assembly performance. Pool enclosure and thermal-bridge/condensation work must remain linked to the pool environment; an ordinary wall preset cannot erase those issues.

## E12. Roof terrace, stormwater, and drainage

`drainage_design` consumes catchment geometry, surface layers, slopes/elevations, drain/overflow positions, rainfall basis, receiving-system assumptions, and supported hydraulic methods. Return drainage zones, flow paths, supported runoff quantities, capacity checks, overflow scenarios, details, and unresolved connection requirements.

Separate water generation from conveyance and destination. A simple scenario calculation may multiply area by rainfall intensity and a declared runoff coefficient when its method is applicable. Its coefficient, event basis, unit conversion, and domain must be explicit. Such a result alone does not determine gutter/downpipe capacity, detention, infiltration, or an approved connection.

Coordinate occupied roof surfaces, pavers, waterproofing, penetrations, door thresholds, parapets/guards, drains, and overflows. A layout edit that changes roof falls or introduces a barrier must rerun water-path checks. A blocked-primary-drain scenario must connect drainage assumptions with structural rain/ponding analysis rather than leave those disciplines independent.

Do not silently terminate a drain at the site boundary. The receiving system and connection basis remain a named input. Underground infiltration, groundwater management, and pool discharge require separate applicability and source checks. NYC Plumbing Code Chapter 11 is a research gate for the applicable storm-drainage requirements; its detailed algorithms were not verified during this research. [Official chapter viewer](https://www.nyc.gov/assets/buildings/apps/pdf_viewer/viewer.html?file=2022PC_Chapter11_StormDrainageWBwm.pdf&section=conscode_2022).

## E13. Change propagation and coordinated exports

Implement a dependency graph, not a global “recalculate” button that merely asks the model again. Every object/quantity records its upstream dependencies. On a committed edit, calculate the affected closure, mark results stale, rerun validated modules in dependency order, and publish one consistent result set. Independent modules can execute concurrently; downstream modules must wait for their actual inputs.

| Edit | Required dependent work |
|---|---|
| Move a nonstructural partition | room areas/adjacency, openings, affected zones/fixtures/circuits, partition load assignment where applicable, schedules/drawings |
| Extend a structural span | analytical geometry, tributary loads, analysis/checks, reactions/foundation assessment, routing conflicts, all affected sheets |
| Increase pool surface area | water volume/load where geometry changes, evaporation-method inputs, environmental/thermal quantities, equipment/plumbing/electrical dependencies |
| Change roof-terrace layout | use/load zones, permanent assembly quantities, drainage paths, penetrations, parapet/guard interfaces, structural and architectural checks |
| Change a soil or groundwater assumption | foundation/basement/pool scenarios and related details; preserve unaffected room geometry |
| Change equipment selection | duty validation, service clearances, weight/supports, electrical input, plumbing/duct connections, schedules |

A PDF package is a frozen snapshot. Every sheet must carry project/revision identity, generation date, discipline, status, and linked source/calculation references. Include the coordinated drawing index, design basis, assumptions register, method/coverage register, calculation reports, and an issue schedule identifying affected objects and sheets. The system must distinguish “complete for defined review scope” from “review package with open gaps.” Do not fabricate an applicant number, signature, seal, or authority approval.

## E14. Independent numerical verification fixtures

Create these fixtures before connecting structural analysis to the UI. They are artificial academic members, not proposed house members. Assumptions: prismatic Euler–Bernoulli bending, linear elasticity, small displacements, prescribed constant flexural rigidity, no self-weight, no shear deformation, no axial/geometric nonlinearity, and explicit support conditions. Expected values are magnitudes; the adapter must separately verify the selected global/local sign convention. Constrain out-of-plane degrees of freedom only as declared by the planar fixture, not as an arbitrary repair to a building model.

**Fixture A: simply supported beam under uniform load.** Set span `L=4 m`, downward load `w=5,000 N/m`, `E=200,000,000,000 Pa`, and `I=0.000008 m^4`. Independent equilibrium gives each support reaction `wL/2=10,000 N` and maximum bending moment `wL²/8=10,000 N·m`. Integrating `EI v''''=w` with simple-support boundary conditions gives midpoint deflection `5wL⁴/(384EI)=0.010416666666666666 m` and end-slope magnitude `wL³/(24EI)=0.008333333333333333 rad`. These exact expressions, not rounded display strings, are the reference.

**Fixture B: simply supported beam with midpoint point load.** Set `L=3 m`, downward `P=12,000 N`, `E=200,000,000,000 Pa`, and `I=0.000006 m^4`. Each reaction is `6,000 N`; maximum moment is `PL/4=9,000 N·m`; midpoint deflection is `PL³/(48EI)=0.005625 m`. Include an exact midpoint sample/node as appropriate to the adapter; do not compare a nearby sampled value to the maximum and relax tolerance to compensate.

**Fixture C: cantilever with end point load.** Set `L=2 m`, downward `P=1,000 N`, `E=200,000,000,000 Pa`, and `I=0.000010 m^4`. The fixed support carries `1,000 N` vertical force and `2,000 N·m` moment. Tip deflection is `PL³/(3EI)=0.0013333333333333333 m`; tip rotation magnitude is `PL²/(2EI)=0.001 rad`. Check the reaction moment sign explicitly.

Store formulas and expected numbers in a test-only reference implementation independent of production assembly/solver code. For these well-conditioned linear fixtures, use `abs(actual-expected) <= abs_tol + rel_tol*abs(expected)`, with `rel_tol=1e-6`, displacement `abs_tol=1e-9 m`, rotation `abs_tol=1e-9 rad`, and force/moment absolute tolerances of `1e-4` in their SI units. These are software verification tolerances, not engineering acceptance limits. Investigate failures; do not loosen tolerances to conceal different physical assumptions. If the selected solver includes shear deformation, explicitly use its appropriate bending-only option or derive a separate reference for its actual formulation.

Additional required tests: double load and verify doubled linear response; reverse the load and verify signs; double elastic modulus and verify halved displacement for the same geometry/load; preserve reactions where equilibrium dictates; remove a necessary support and expect an instability error; reject negative stiffness and mixed-unit inputs. Do not apply linear scaling expectations to nonlinear cases.

## E15. Multidisciplinary acceptance and implementation sequence

First implement snapshot schemas, provenance, units, geometry validation, method registry, and status rendering. Next implement the analytical fixtures and a standalone structural adapter. Then generate the bounded villa's rooms, floors, pool, roof terrace, structural topology, and coordinated drawing primitives. Establish a visible baseline before adding optimization or multiple design alternatives.

Implement the load ledger and one fully reproducible structural scenario next, then add each supported scenario/check with source and tests. In parallel, build the pool quantity ledger and discipline network inventories. Add HVAC, plumbing, electrical, energy, drainage, and foundation calculations through the common method contract. Resolve method/source gaps explicitly, rather than allowing the coding model to invent methods to keep a feature green.

Run one deliberate edit through the whole dependency graph: a span change must update structure/reactions; a pool change must update its affected mass/environment/services; a terrace edit must update loading/drainage. Reconcile totals and object IDs across the regenerated PDFs. Only after these paths work should the team add cosmetic rendering, broader freeform generation, or automated option ranking.

Acceptance requires numerical reference agreement; source/edition applicability; finite values and units; connected networks; no duplicate loads; structural equilibrium within a declared scaled numerical tolerance; correct stale-result behavior; repeatable results from identical snapshots; and identical dimensions/quantities across model, schedules, and drawings. Every claimed check must have a real executable method and a reproducible result. Every requested discipline must have meaningful content and an honest coverage record.

At release, publish an internal capability manifest listing each planned full capability, actual implementation, validated domain, evidence/tests, remaining gap, and affected deliverable. The demo may show supported calculations under explicit assumptions, but the package must identify unresolved methods and inputs. A serious gap in a discipline prevents its `discipline_design_complete` milestone; it does not justify silently removing that discipline or declaring the full target complete.

## E16. Verified documentation and remaining research gates

Documentation verified for this part: the official NYC structural chapter's reference/modification and documentation framework; the NYC energy edition notice; PyNite's model, analysis, and stability descriptions; ASHRAE's indoor-pool systems discussion; and PsychroLib's stated units/method basis. These checks establish suitable starting sources, not verification of a complete house-design implementation.

Research gates before corresponding compliance algorithms are enabled: exact NYC-referenced structural standards and amendments; load combinations and applicability; steel, timber, concrete and foundation methods; wind/snow/rain/seismic procedures; pool evaporation and psychrometric operating assumptions; HVAC/ventilation and equipment-selection procedures; plumbing demand/venting/backflow/discharge methods; electrical sizing/protection/pool requirements; energy-pathway rules; stormwater/hydraulic methods; and architectural/zoning/fire/life-safety provisions. Obtain reliable access, record edition/section and use rights, implement fixtures, and obtain appropriate review. If a gate remains open, retain the planned capability and expose its exact implementation gap.

---

# Part D — NYC data, jurisdiction, documents, and professional handoff

**Research date: 26 October 2026. Product target: documents prepared for review by an architect and structural/MEP engineers, with signing and authority submission performed later by authorized professionals.** This appendix specifies NodeSnap’s demonstration: a detached single-family villa with two main floors, six principal rooms per main floor, additional bathrooms and circulation, an indoor basement pool, and an occupied roof terrace. The structural concept combines steel and timber above a reinforced-concrete substructure. It includes architecture, structure, foundations, mechanical systems, plumbing, electrical systems, energy, and drainage. Site conditions and professional decisions remain explicit dependencies.

“Ready for professional review” means that a reviewer can inspect the coordinated work, reproduce supported calculations, and identify unresolved questions. It does not mean that every design question is resolved or that DOB would accept the package. If necessary inputs remain assumed, title the export **Demonstration design — assumptions require professional verification**. Never describe such a set as signed, approved, filed, or construction-ready.

## D1. Versioned jurisdiction profile

Store the following baseline in a dated jurisdiction profile, then recheck amendments and applicability before any real project handoff. A filing date changes the applicable profile; changing that date must invalidate affected checks.

| Topic | Baseline for this demonstration | Implementation rule |
|---|---|---|
| Construction codes | NYC’s official collection is the **2022 NYC Construction Codes**, including Building, Mechanical, Plumbing, and Fuel Gas codes, with amendments. | Store the relevant code, amendment, section, retrieval date, and applicability decision with each implemented check. Do not substitute a New York State residential-code profile. |
| Structural loading | **ASCE 7-16**, subject to NYC Building Code Chapter 16 modifications. Section 1601.1.1 establishes the NYC modification relationship. | Select loads and combinations using the adopted NYC profile; do not silently use ASCE 7-22 because it is newer. Store the actual source for every implemented rule. |
| Energy | **2025 NYCECC** applies to completed applications filed on or after **30 March 2026**. | Confirm the residential compliance path and current accepted analysis/reporting method. Do not automatically select a commercial ASHRAE path. |
| Electrical | **2025 NYC Electrical Code**, incorporating NYC changes to the **2020 NEC**; the general changeover occurred **21 December 2025**, subject to documented transition provisions. | Use the current profile for this new demonstration; separately determine whether electrical plan review applies. |

Primary references: [2022 Construction Codes](https://www.nyc.gov/site/buildings/codes/2022-construction-codes.page), [Building Code Chapter 16](https://www.nyc.gov/assets/buildings/codes-pdf/cons_codes_2022/2022BC_Chapter16_StructuralDesignWBwm.pdf), [ICC’s NYC Chapter 35 reference list](https://codes.iccsafe.org/content/NYNYCBC2022P1/chapter-35-referenced-nbsp-standards), [current energy applicability](https://www.nyc.gov/site/buildings/codes/energy-conservation-code.page), [24 March 2026 energy notice](https://www.nyc.gov/assets/buildings/pdf/nycecc_guidance-sn.pdf), and [electrical code](https://www.nyc.gov/site/buildings/codes/electrical-code.page).

**Source limitation:** the ASCE 7-16 entry was verified through the primary publisher’s indexed Chapter 35 text, while full-page access was restricted. NYC’s Chapter 16 PDF was accessible. Obtain an accessible, authorized copy of the complete referenced provisions before implementing or professionally validating structural checks. References to a standard are not a complete implementation of that standard.

## D2. Official site-data adapters and evidence contract

Resolve an address to candidate sites before calculating a buildable envelope. An ambiguous result must remain ambiguous. A tax lot, zoning lot, building identification number, and postal address are related identifiers, not interchangeable representations of the project boundary.

| Adapter | Verified resource or documented interface | Normalized output and limits |
|---|---|---|
| Address resolution | NYC Planning documents GeoSearch v2 at [its official migration guide](https://github.com/NYCPlanning/labs-geosearch-docker/blob/master/MIGRATING.md). Documented request: `https://geosearch.planninglabs.nyc/v2/autocomplete?text=<encoded-address>`. | Candidate label, coordinates, BBL/BIN when returned, and match evidence. The v2 documentation identifies `properties.addendum.pad.bbl` and `.bin`; validate actual responses. Return multiple candidates when necessary. |
| Address fallback | [NYC API portal](https://api-portal.nyc.gov/) lists Geoclient. | Use the team’s own credentials and current documented interface. Never import credentials from examples or third-party configuration files. |
| Parcel attributes | [NYC Open Data PLUTO](https://data.cityofnewyork.us/City-Government/Primary-Land-Use-Tax-Lot-Output-PLUTO-/64uk-42ks). | BBL, published land-use and lot attributes, source release. Discover the current schema during integration; whitelist necessary fields and exclude owner names. |
| Parcel geometry | [NYC Planning MapPLUTO/PLUTO resources](https://www.nyc.gov/content/planning/pages/resources/datasets/mappluto-pluto-change). | Published tax-lot polygon, coordinate reference system, release/version. Tax-map geometry is planning context, not a licensed boundary or topographic survey. |
| Zoning context | [NYC GIS zoning features](https://www.nyc.gov/content/planning/pages/resources/datasets/gis-zoning-features), [ZoLa](https://zola.planning.nyc.gov/), and [Zoning Resolution](https://zr.planning.nyc.gov/). | Intersect published district/overlay/special-district layers with the parcel; retain intersections and source versions. Current text, map amendments, zoning-lot conditions, and professional interpretation control the final envelope. ZoLa is a review interface, not an assumed public API. |
| Seismic reference data | [USGS ASCE 7-16 service documentation](https://earthquake.usgs.gov/ws/building-codes/asce7-16) and [USGS design-ground-motions portal](https://www.usgs.gov/programs/earthquake-hazards/design-ground-motions-portal). | Use confirmed coordinates, a documented risk-category decision and an evidenced or explicitly assumed site class. Preserve request parameters, reference edition, returned values/units and warnings. Verify the actual JSON interface during integration. Retrieved reference data still require the applicable NYC amendments and structural method; they do not establish completed seismic design. |
| Flood screening | [NYC Flood Hazard Mapper](https://dcp.maps.arcgis.com/apps/webappviewer/index.html?id=1c37d271fba14163bbb520517153d6d5), [NYC climate-resiliency resources](https://www.nyc.gov/content/planning/pages/our-work/plans/citywide/climate-resiliency), and [FEMA NFHL service information](https://hazards.fema.gov/femaportal/wps/portal/NFHLWMS). | Preserve map panel, map series/date, mapped zone and available elevations. Screen the applicable NYC comparison of effective and preliminary maps; do not treat a single NFHL response or future-climate layer as the entire legal flood determination. |

Resource documentation and dataset identities were checked on the research date. Several dynamic pages exposed limited content, and successful live JSON/API calls were not established for every adapter. Integration must therefore include a connectivity/schema check and an honest fallback. No endpoint in this part is a promise of uptime or permission-free access.

Every adapter returns a common evidence envelope: `query`, `site_identifiers`, `source_url`, `dataset_version`, `retrieved_at`, `coordinate_system`, `raw_response_hash`, `normalized_fields`, `field_provenance`, `warnings`, and `retrieval_status`. The adapter-specific `retrieval_status` values are `verified_response`, `cached_response`, `ambiguous`, `unavailable`, and `unsupported`; these are separate from calculation execution states. Preserve the raw public response or a permissible evidence snapshot. Record each transformation and unit conversion. A cache hit displays its original retrieval date; refreshing a source creates a new evidence version.

An empty response must not become “no restriction.” Distinguish no matching feature from retrieval failure, missing layers, incomplete coverage, and an unchecked requirement. A model may summarize evidence but may not invent source URLs, parcel facts, survey elevations, soil strengths, groundwater levels, utility capacity, or official approvals. Unknown fields remain null with a reason and an assigned reviewer.

Do not infer geotechnical properties from neighborhood appearance, building age, or nearby projects. Soil-bearing values, settlement parameters, groundwater, excavation conditions, and seismic site classification need suitable project evidence and engineering review. Similarly, public geometry does not establish surveyed boundaries, easements, legal access, party-wall conditions, or exact neighboring foundations.

## D3. Demonstration-site screening procedure

Use a reproducible selection procedure instead of placing an attractive house on an unverified address:

1. Search public parcel data for plausible low-density residential contexts in Queens or Staten Island. This is a candidate-search preference, not a finding that a particular lot allows the design. Keep personal owner information outside the application.
2. Resolve identifiers, confirm polygon consistency, and retrieve current zoning layers and relevant text. Check whether a zoning lot differs from the displayed tax lot. Record candidate rejection reasons.
3. Screen flood conditions, historic designation, special districts and overlays, mapped street/access conditions, trees, nearby structures, grade uncertainty, and available utility evidence. Route uncertain conditions to an unresolved checklist. A mapped constraint is not automatically an absolute prohibition; its implications need review.
4. Assess whether the intended massing, basement, terrace, excavation, and pool could be investigated sensibly on that candidate. Prefer a candidate with fewer verified complications, without suppressing genuine requirements.
5. Freeze a dated public-data snapshot. Label the proposed villa as hypothetical and distinguish public observations from demonstration assumptions. Do not imply ownership, permission to build, availability for purchase, or verified vacancy.
6. If no suitable real candidate can be verified, use **Demo Villa NYC-01**, a synthetic site without a real street address or BBL. Publish synthetic dimensions and jurisdiction assumptions prominently. That fallback demonstrates the workflow; it cannot demonstrate a parcel-specific entitlement determination.

Maintain separate site layers: published context, supplied professional evidence, and demonstration assumptions. An engineer may review the assumptions for an illustrative analysis, but that review does not turn invented subsurface conditions into measured facts. Changing any load-bearing assumption invalidates dependent calculations and drawings.

## D4. Candidate PDF manifest

Generate a configurable project manifest before drawing sheets. The prefixes below are **NodeSnap organizational labels**, not a claim that DOB mandates these exact discipline codes, sheet counts, or filenames. Validate the eventual submission naming and work-type mapping against the current filing workflow. DOB’s New Building FAQ identifies **foundation and structural work types** for new buildings, with filing arrangement depending on the applicants. [DOB New Building FAQ](https://www.nyc.gov/site/buildings/industry/new-building-buildfaqs.page).

Each manifest item has an applicability state: `required`, `applicable`, `unverified`, or `not_applicable`. `Required` needs an identified authority or an explicit project-deliverable requirement. `Applicable` means relevant to the selected design while the precise filing obligation remains to be established. `Unverified` means a pending determination, not permission to omit it. `Not_applicable` requires an explanation and reviewer attribution. All families below are required project deliverables for this selected villa; their final authority requirements remain project-specific.

| Family | Candidate content | Determinations to attach |
|---|---|---|
| Cover/index | Scope, code profile, sheet list, revision history, project identifiers, assumptions, unresolved items, discipline coordination. | Actual job identifiers, applicant information, filing arrangement, required forms. |
| **C — Site/civil** | Survey-reference sheet, existing/proposed site context, zoning analysis, grading and drainage concept, utility routing, excavation context. | Authentic survey, zoning-lot evidence, connection approvals, stormwater obligations, sidewalk/street/tree implications. |
| **A — Architecture** | Basement, two main-floor and roof plans; elevations; sections; room/area schedules; stairs, doors/windows, envelope and waterproofing details; terrace/pool relationships. | Occupancy, construction type, zoning envelope, accessibility, egress, fire separation, guards and enclosure requirements. |
| **S — Structure** | Structural grids, framing plans, member schedules, steel/timber connections, lateral system, load-path diagrams, design criteria, coordinated penetrations. | Applicable material standards, connections, diaphragms, stability, serviceability, fire/corrosion/durability treatment, inspection requirements. |
| **F — Foundations** | Reinforced-concrete substructure, foundation plans/sections, pool basin relationship, reinforcement details, retaining/excavation concepts. | Geotechnical report, groundwater, settlement, uplift, adjacency and excavation support, waterproofing joints and sequencing. |
| **M — Mechanical** | Heating/cooling and ventilation plans, equipment schedules, duct routing, pool dehumidification/exhaust strategy and controls. | Room loads, outdoor air, moisture control, pressure relationships, equipment performance, maintenance access and energy coordination. |
| **P — Plumbing** | Domestic water, sanitary/vent, hot-water systems, roof/site drainage interfaces, pool circulation/treatment/backwash diagrams. | Water demand, sewer/utility capacity, discharge route, backflow provisions, drainage sizing, pool safety and equipment requirements. |
| **E — Electrical** | Lighting/power plans, service/load schedules, panel schedules, single-line diagram, pool and plant equipment circuits. | Service capacity, protective devices, wet-area provisions, bonding/grounding, controls, required electrical plan review. |
| **EN — Energy** | Envelope assemblies, fenestration/thermal properties, compliance method, supporting analysis, mechanical/electrical coordination. | Current accepted residential path, required reports/details, inspection documentation and professional certification. |
| Calculation annexes | Structural inputs/results, foundation assumptions, pool basin/water/groundwater cases, terrace loads, MEP sizing, energy and drainage calculations. | Reproducible methods, solver versions, supported scope, units, source references, engineer review and unresolved cases. |

Use DOB’s [Plan Examination Guidelines, revised 30 April 2014](https://www.nyc.gov/assets/buildings/pdf/plan_exam_user_guide.pdf) as a historical drawing-content reference only. They identify useful categories of coordinated plans, details, dimensions and technical documentation, but are not a current, exhaustive checklist for this project. Do not translate their older paper/BSCAN practices into universal DOB NOW requirements. Current portal requirements, applicable codes, work types and project circumstances determine the actual package.

## D5. Pool, terrace, and agency dependencies

The indoor basement pool is a separate interdisciplinary design feature, not a decorative object. Review its water and basin loads, groundwater and buoyancy scenarios, differential movement, concrete crack-control strategy, penetrations, joints and waterproofing. Coordinate pool-hall temperature/humidity, condensation at glazing and thermal bridges, dedicated moisture removal, ventilation, corrosion exposure, and protection of adjacent timber and steel. Trace equipment and maintenance routes through the architecture. Identify circulation, treatment, discharge, access/barrier, suction-entrapment and electrical bonding/protection questions explicitly. The applicability of every pool provision must be checked against its actual use and configuration; [Local Law 77 of 2023](https://www.nyc.gov/assets/buildings/local_laws/ll77of2023.pdf) amended Building Code Section 3109.5 concerning private pools.

For the roof terrace, resolve intended occupancy and access, egress, guards, usable area, structural live loads, concentrated loads from furniture/planters, drainage and emergency overflow, waterproofing interfaces, penetrations, maintenance and material exposure. Distinguish an occupied terrace from an inaccessible roof in both the architectural model and structural load model. Do not assume roof occupancy leaves height, area, zoning, fire-safety, or accessibility determinations unchanged. These are review dependencies, not asserted project-specific code conclusions.

Screen agency involvement as a conditional matrix: DOB for applicable building/work-type processes; DEP for water/sewer and relevant drainage or discharge matters; DOT for affected public-way work; Parks for affected public trees; LPC for designated properties/districts; and other authorities where site facts establish a trigger. DEP’s [connection-proposal guidance](https://www.nyc.gov/assets/dep/downloads/pdf/about/water-and-sewer-forms/scp-hcp-selfcert-application-guidelines.pdf) and [27 May 2025 PARIS announcement](https://www.nyc.gov/site/dep/news/052725/new-online-process-site-house-connection-proposals-now-available-paris) show that connection processes extend beyond a drawing export. Do not invent an “all agencies cleared” status from map screening.

## D6. Export verification and professional handoff

Maintain these independent status dimensions for every document and major design requirement. The labels below describe the user interface; serialize the normative Part A enums and retain the separate coverage/applicability record:

| Dimension | Example states |
|---|---|
| Document presence | Missing; partial; generated; export-verified. |
| Design coverage | Unsupported; assumed; awaiting input; checked within implemented scope; failed check. |
| Professional review | Not assigned; pending; revisions requested; reviewed, with reviewer/date/scope. |
| Authority process | Not submitted; later externally reported filing status with evidence. |

A generated sheet cannot turn an unsupported calculation into a checked design. A successful solver run cannot establish professional review. A professional comment or review flag cannot establish DOB approval. Show counts and unresolved dependencies by dimension instead of one misleading “100% permit-ready” progress bar.

Run deterministic export checks: all referenced sheets exist; drawing views and schedules share the same model revision; dimensions and units agree; plans/sections align; required project fields are present; assumptions are visible; calculation references resolve; no clipped text or missing glyphs appears. Use selectable text and vector linework where practical, embedded fonts, legible line weights, consistent title blocks, scale bars and page labels. Render representative pages for visual inspection. Configure page sizes and upload constraints from verified current requirements; do not invent a universal DOB paper size or file-size limit.

DOB’s [Build FAQ](https://www.nyc.gov/site/buildings/industry/dob-now-build-faqs.page) describes job-number/extension identification on drawings and an approval stamp on approved plans. In NodeSnap, **leave actual job-number, professional signature, seal, and authority approval fields blank** until legitimately supplied. Show their status beside the field. Never generate a plausible-looking seal, signature, filing number, or approval stamp. Export review copies without simulating an approved set.

Deliver the coordinated PDF set, calculation reports, source/evidence register, assumptions register, unresolved-item register, and revision summary. Include the editable model and structured results if supported. Assign each unresolved item an owner and the evidence needed to close it. Before a reviewer marks a discipline reviewed, require a recorded scope and revision; later changes reopen affected reviews.

Actual filing is a separate professional process. DOB identifies a New York State licensed PE or RA as the applicant who files plans, and [obtaining a permit](https://www.nyc.gov/site/buildings/property-or-business-owner/obtaining-a-permit.page) involves applications and required documents beyond the exported drawings. [DOB NOW: Build](https://www.nyc.gov/site/buildings/industry/dob-now-build.page) is the filing environment. NodeSnap prepares the handoff and records evidenced outcomes; this demonstration neither signs nor submits a filing, and matching a PDF layout does not guarantee acceptance.

## D7. Additional NYC requirements that cross disciplines

### Building classification, fire protection, and egress

Create a required classification record covering grade plane, actual levels, each relevant story-count definition, basement/cellar determination, occupancy/use, construction type, fire-resistance strategy, sprinkler applicability, stair continuity, roof access, guards and applicable escape/rescue requirements. Two main floors and twelve principal rooms are program requirements; they do not determine those classifications.

DOB Bulletin 2023-017 explains the conditional treatment of unenclosed stairs and sprinkler exceptions in one- and two-family dwellings, including the counting of basements/cellars for the discussed stair provision. Implement the applicable conditions and exceptions rather than a blanket sprinkler or stair-enclosure rule. Source: [DOB Bulletin 2023-017](https://www.nyc.gov/assets/buildings/bldgs_bulletins/bb_2023-017.pdf).

### Real-project geotechnical evidence

NYC Building Code 1803.2 requires a geotechnical investigation/report for new structures, and Section 1803.1 assigns engineering responsibility for the investigation. The synthetic demonstration's assumed soil and groundwater scenarios cannot satisfy that requirement. Source: [NYC Building Code Chapter 18](https://www.nyc.gov/assets/buildings/codes-pdf/cons_codes_2022/2022BC_Chapter18_SoilsFoundationsWBwm.pdf).

Track both the scenario evaluated and the real-project evidence outstanding. Foundation completion for a real site remains blocked until required investigation, survey, adjacency data and professional interpretations are incorporated. Replacing assumptions with actual evidence creates a new revision and invalidates dependent work.

### Electrification and equipment choices

Use an **all-electric equipment concept** for this synthetic baseline. That is a product/design choice supporting a coherent first implementation, not a claim that every conceivable fuel use is prohibited in 2026.

DOB's LL154 guidance applies its first low-rise/R-3 phase from 1 January 2024, excluding service hot water in that phase; the phase beginning 2 July 2027 includes service hot water. Evaluate applicability by filing date and equipment function, including any claimed exception. Do not infer the classification of a pool-heating system without checking the relevant provisions. Source: [DOB building-electrification guidance](https://www.nyc.gov/site/buildings/codes/ll154-building-electrification.page).

The equipment schedule must therefore include energy source, function, input power, applicable rule, exception basis if any, and status. Coordinate heat-pump/ventilation/pool plant duty with electrical service demand and roof/site equipment placement. “All electric” does not determine adequate service capacity or suitable equipment.

### Sustainable roof and occupied terrace

Evaluate Local Laws 92/94. DOB's guidance requires qualifying solar/green-roof coverage of the applicable sustainable roofing zone and describes area-specific exclusions. An occupied roof terrace does not by itself establish a whole-roof exemption. Source: [DOB solar and green-roof guidance](https://www.nyc.gov/site/buildings/codes/ll92-solar-green-roofs.page).

Create a roof-area ledger with actual geometry for terrace, roof structures, access, equipment, drainage features, proposed solar/green-roof areas and claimed exclusions. Record the legal basis for each exclusion. Union overlapping exclusion polygons before subtraction; do not double-count them. The approximately 900 ft² terrace target is a program choice, not evidence of an exemption.

Coordinate any applicable sustainable-roof system with permanent/saturated loads, wind/support interfaces, access, drainage and electrical design. If those methods remain unsupported, identify the specific design/document gap.

### Technical reports and inspections

Generate an applicability register for special/progress inspections and technical reports using the current work types and conditions. DOB's November 2025 technical-report matrix distinguishes mandatory, conditional and other potentially required reports. Use it as a dated source to be rechecked at filing; do not populate every project with every report. Source: [DOB technical-report matrix](https://www.nyc.gov/assets/buildings/pdf/dob_now_technical_reports.pdf).

Record inspection type, trigger, responsible professional/agency if supplied, anticipated documentation, and status. Planned inspections are not completed inspections. Do not generate completed inspection certificates or professional declarations.

## D8. Handoff acceptance clarification

The full product aims to produce work ready for professional review and eventual signing/submission after the professional's required review and completion. The professional's remaining work is not presumed to be merely signing a PDF.

For each discipline, identify completed calculations, preliminary sizing, schematic documentation, unresolved inputs and unsupported checks separately. The package must make it possible to assess and reproduce the work. An unresolved geotechnical requirement, unimplemented material check, incomplete pool environmental design or missing architectural classification remains an explicit blocker to the corresponding complete-design claim, even when useful drawings and calculations can already be exported.

---

# Part E — Delivery, verification, demo, and coding-agent instructions

## E-Delivery 1. Implementation strategy and ownership

The two founders should own distinct integration responsibilities. The CTO owns repository architecture, data contracts, deterministic methods, integration, deployment and code review. The CEO owns the homeowner journey, visual hierarchy, requirements/source ledger, representative scenarios, evidence collection, submission copy and demo recording. Both can use Muse Code, but changes to shared schemas and database migrations need one integration owner.

Use small tasks with explicit file ownership. Parallelize independent UI and calculation work only after contracts are established. If multiple coding sessions touch the repository, use isolated branches/worktrees and merge through the integration owner. Do not ask several agents to rewrite the same canonical schema simultaneously.

Invite the available structural engineer to review the actual analysis idealization, assumptions and independent fixtures early. Record what they actually reviewed. Their availability is not a license, a seal, or evidence of review across every discipline. Architectural, geotechnical and building-services completion may require additional professional input; record that need in the full-product roadmap and capability ledger.

### Completion vocabulary

- **Workflow complete:** A supported request can generate a model, calculate supported scenarios, accept a real edit, update affected results and export a consistent package.
- **Method verified for scope:** A particular implementation passes appropriate independent reference tests and has a reviewed source/applicability record.
- **Discipline design complete:** All applicable required design tasks for that discipline and project are resolved within validated methods, inputs and review requirements.
- **Professional handoff complete:** The package includes the actual deliverables, sources, assumptions, issues and editable evidence necessary for the named review scope.
- **Submitted/approved:** An external authority process supported by real evidence, outside this prototype.

These are separate acceptance results. The nine-day schedule below is a delivery plan for the operating prototype and its demonstrated methods. It is not a guarantee that two people can independently validate every NYC design discipline in that period.

## E-Delivery 2. Milestones and dates

The published guide lists a build period of **27 October–4 November 2026** and a kickoff on 26 October. Preserve accurate work dates. If eligibility of work on the kickoff date matters, obtain the organizer's clarification and record it; do not backdate commits or invent approval. Source: [official participant guide](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details).

The submission deadline is **4 November 2026 at 9:00 p.m. Eastern Standard Time**, equivalent to **5 November at 02:00 UTC** and **5 November at 06:00 in Tbilisi**. Confirm event updates before submission. Set the team's internal content freeze for 3 November and finish uploading at least several hours before the official deadline.

| Milestone | Target | Concrete work | Exit evidence |
|---|---|---|---|
| M0 — Access and contracts | 27 Oct, first half | Confirm Muse subscription/model; verify Meta API access and strict-schema/tool contracts; choose dependency lockfiles; scaffold services; define canonical schemas, enums and method registry | A real authenticated Meta call, a parsed structured response, provider/model log, successful application build, empty-secret example config, schema/type generation |
| M1 — One complete path | 27–28 Oct | Seed the exact villa program; persist a snapshot; render plan/3D; compute pool surface area and volume from canonical water geometry; export one genuine vector drawing and calculation page | A saved project survives refresh; changing pool dimensions updates its quantities; result and PDF reference the same revision; no placeholder values |
| M2 — Generation and editing | 28–29 Oct | Implement constrained layouts, room/area schedules, doors/circulation, floor alignment, typed commands, snapping, undo, conflict handling | Two supported briefs produce meaningfully different valid geometry; a drag and chat edit commit revisions; invalid edits are explained |
| M3 — Structure and dependencies | 29–30 Oct | Pass analytical fixtures; build load ledger and a physically justified baseline frame; implement sourced checks available within scope; link reactions and foundation scenarios; add invalidation | Fixture reports, equilibrium/diagnostics, a real change affecting a real result, engineer feedback with stated scope |
| M4 — Pool and services | 30 Oct–1 Nov | Pool quantities and environmental method when verified; room load/inventory work; connected plumbing/electrical/mechanical networks; energy/drainage method coverage; all-electric concept | Real quantities/schedules for each implemented discipline, traceable methods, cross-discipline changes, explicit unresolved checks |
| M5 — NYC review package | 1–2 Nov | Integrate site evidence; code/classification ledger; all sheet families; calculation annexes; issue/source registers; snapshot-specific export | Rendered representative sheets, consistent IDs/areas, source references, blank genuine approval fields, no stale values |
| M6 — Reliability and release candidate | 2–3 Nov | Guest isolation, job recovery, rate/cost caps, deployment, access tests, three scenario rehearsals, readable README and capability manifest | Fresh-browser live demo, verified download, negative-path tests, pinned build, measured latency/cost |
| M7 — Submission and presentation | 3–4 Nov | Record three-minute demo, validate public links/repository, complete factual submission, review rights/new-work record, archive final demo revision | Accessible repo/product/video, accurate claims, contributors listed, submission receipt captured by the team |

Work can overlap where dependencies allow. A milestone is not complete because its date has arrived. If a method/source gate remains unresolved, preserve that capability as an explicit gap and continue unaffected work. Do not use fabricated output to satisfy the schedule.

### First six implementation tasks

1. Create the monorepo, environment examples, Compose services and build commands.
2. Implement Pydantic schemas and generate TypeScript contracts.
3. Implement the normative status components and a persisted seed snapshot.
4. Write the three independent beam fixtures before integrating the structural adapter.
5. Implement one Meta structured-response call and one bounded custom-tool exchange against the actual account.
6. Wire the seed model through plan, 3D, a real calculation and a vector PDF.

This sequence produces a working foundation before large amounts of interface polish or agent orchestration.

## E-Delivery 3. Verification and acceptance matrix

Use tests where failure can invalidate engineering output, corrupt revisions, expose another user's project, or misrepresent the product. Avoid large suites that merely mirror rendering implementation. The following checks resolve concrete risks.

| Area | Required acceptance evidence |
|---|---|
| Room program | Six principal spaces on each main floor; five total bedrooms under the chosen program; support spaces excluded from principal count; actual area reconciliation |
| Geometry | Closed valid polygons, no unintended overlaps, positive dimensions, explicit wall-thickness treatment, door-host validity, connected circulation |
| Vertical coordination | Stair/core relationships align; floor/roof elevations agree across views; pool geometry remains inside its declared physical system |
| Layout solver | Impossible area input, corner-touch adjacency, disconnected room, reduced clear width, timeout and infeasible-family cases handled distinctly |
| Units/axes | Independently checked SI↔US conversions; asymmetric model tests prevent axis swaps/mirroring; no NaN/infinite values |
| Structural adapter | Three analytical fixtures within stated tolerances; reaction/equilibrium checks; known instability rejected; releases/sign conventions documented |
| Design methods | Each claimed check has a source/edition/domain, executable method, fixture, input basis and result; unverified methods cannot pass |
| Load accounting | Member self-weight, pool water/shell, floor assemblies and equipment included exactly once through a recorded load path |
| Foundation scenario | Missing geotechnical evidence remains unresolved; scenario assumptions cannot close real-project evidence requirements |
| Pool | Internal water geometry and quantities reconcile; full/empty/groundwater cases have coverage states; moisture/services dependencies explicit |
| Mechanical | Zone/room inventories and available load components reconcile; pool latent work separate; selected versus unselected equipment distinguished |
| Plumbing | Fixture/equipment networks connected; supply, sanitary, vent, storm and pool networks distinguished; unknown receiving conditions visible |
| Electrical | Connected-load totals independently reconcile; equipment input power used correctly; circuit/panel graph valid; wet-area checks explicit |
| Energy/roof/drainage | Pathway and method recorded; roof-area ledger reconciles; supported runoff quantities use stated units/basis; outlets/overflow dependencies shown |
| Revision integrity | Drag and chat share commands; duplicate mutation is idempotent; simultaneous stale edit returns conflict; old job cannot overwrite current results |
| Export integrity | Every sheet/result references one frozen revision; manifest hashes match files; dimensions/schedules agree; sources/issues present |
| Rendering | Representative A/S/F/M/P/E/EN/C pages rendered and inspected; readable text/lineweights; no clipping/missing symbols; scale and units visible |
| Access isolation | Session A cannot read/mutate/download Session B's private project; share token is read-only and cannot initiate spending |
| Model boundaries | Nonallowlisted model/provider rejected; invalid model output repaired within cap or failed clearly; no arbitrary code/network execution |
| Recovery | Source/model failure, worker failure, cancellation and browser reconnect preserve state and explain next actions |
| Cost control | Concurrent requests reserve budget correctly; ceiling stops new model work; existing model editing and downloads remain available |
| Submission evidence | Public URLs accessible, no secrets/private source files, contributors/new-work history and capability limits recorded |

Also test three end-to-end scenarios:

**Scenario 1 — New villa:** Begin from the chosen brief. Generate a valid supported layout, inspect basement and terrace, run supported methods and export a consistent review package.

**Scenario 2 — Structural change:** Request a longer supported span or another engineered change that actually affects the baseline. Show stale results immediately, rerun analysis and show the real new outcome. If a verified limit is exceeded, explain it and propose a valid repair through typed commands. Do not script a fake failure.

**Scenario 3 — Pool/roof change:** Change pool surface dimensions or terrace allocation. Verify quantities and the relevant structural, mechanical, electrical or drainage dependencies update. Unsupported downstream work remains explicitly unresolved.

A prototype may finish the workflow while one or more discipline-design gates remain open. The release notes must disclose those exact gates. “All checks passed” is allowed only for a clearly named finite set of checks that actually ran and passed.

## E-Delivery 4. PDF and artifact delivery details

Generate a **drawing set PDF** and a **calculation/review report PDF**, plus a structured manifest. Keep page count driven by content and readability. The user's requested package is comprehensive; a cover page with generic narrative is not a substitute for drawings and calculations.

Use the discipline manifest in Part D. A sheet needing unresolved design content must show a bounded schematic or a clearly identified open item; do not invent member sizes, reinforcement, pipe diameters or protective-device ratings for visual completeness.

Every package should expose:

- Project name and site mode, including synthetic/demo status where applicable.
- Exact model revision, generation time, code-profile version and report-template version.
- Sheet and calculation index with working internal references.
- Geometry and quantity schedules tied to stable object IDs.
- Actual evaluated scenarios and methods.
- Assumptions, unresolved inputs, unsupported methods and failed checks.
- Sources and evidence retrieval/version information.
- Professional review scope/status and actual reviewer details only when supplied.
- An export manifest with immutable artifact IDs and content hashes.

The PDF title block should use “Professional review draft” or the more specific status supported by the package. If an assumed site/design is used, include “Demonstration design — assumptions require professional verification.” Do not watermark so heavily that dimensions become unreadable.

Provide machine-readable JSON export of the canonical model and result manifest as an additional developer/reviewer convenience. Optional IFC/DXF export can follow the stable PDF path; do not let it delay the required demonstration. IFC is an interchange format, not the canonical database.

Do not call a partial set complete merely because every discipline has a page. The coverage register determines what those pages establish.

## E-Delivery 5. Demonstration and judging strategy

The official guide weights **Impact 30%, Use of Meta AI Tooling 25%, Technical Depth & Execution 20%, and Demo 25%**. Build the presentation around evidence for those four categories. The selected theme is Push the Frontier. Sources: [participant guide](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details), [event rules](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver).

| Criterion | Evidence NodeSnap should show |
|---|---|
| Impact | A homeowner begins without a finished design and reaches an intelligible coordinated proposal; explain how professionals can inspect the work |
| Meta tooling | Real Meta interpretation, structured tool orchestration and microphone transcription; actual model/request records; Muse Code's role in development |
| Technical depth | Canonical model, deterministic geometry, independent calculations, connected disciplines, stale-result invalidation, reproducible documents |
| Demo | A coherent three-minute story with a real design change, visible consequences and a readable PDF artifact |

### Three-minute video plan

| Time | Screen/action | Narrative purpose |
|---|---|---|
| 0:00–0:15 | Homeowner prompt and villa goal | State the problem and product in plain language |
| 0:15–0:40 | Brief interpretation and generated plan/3D | Show Meta turning intent into a structured project |
| 0:40–1:05 | Basement pool, upper floor and roof terrace | Establish that the chosen complex villa is represented coherently |
| 1:05–1:40 | One supported structural edit, stale state, recalculation and result | Show actual engineering consequences and a repair when applicable |
| 1:40–2:05 | Pool or roof dependency update; one source/assumption view | Demonstrate multidisciplinary coordination and traceability |
| 2:05–2:35 | Exported drawings and calculation report | Show the tangible professional handoff |
| 2:35–3:00 | Meta architecture, actual coverage and next product step | Connect technical proof to startup value |

Suggested opening: **“NodeSnap lets a homeowner describe a house and turns that conversation into an editable design, coordinated calculations, and a package professionals can inspect.”**

Suggested closing: **“This demonstration connects homeowner intent, an editable building model, verified calculations within a declared scope, and revision-consistent documents. Our next step is expanding validated design coverage with professional partners.”**

Use the strongest actual behavior achieved, not an assumed pass/fail story. If engineering repair is not fully implemented, show the real detected issue and its affected documents rather than claim an autonomous correction.

Editing a video for clarity is acceptable as presentation work; indicate accelerated or omitted waiting time. A recorded fallback must be labeled recorded. Do not simulate live computation with edited numbers or prerecorded UI presented as live.

### Measure before claiming

Record time to first valid plan, time for a representative change, calculation/export time, model calls/tokens and estimated cost per scenario. Report sample count and machine/network conditions. Measure exact coverage counts, such as implemented verified checks versus applicable registered requirements, without implying that the count alone measures completeness.

Do not claim a percentage reduction in architectural/engineering effort without a defined comparison and actual measurement. Do not claim city acceptance, zero errors, guaranteed permits, proprietary-code performance or a hackathon win.

Bonus prizes are optional opportunities. Prioritize the core rubric. A public demonstration post can support the event's viral category if the founders choose to post it; the published guide describes engagement through 8 November end of day, with the timezone not specified in the reviewed material. No social posting is authorized by this build specification alone. Do not distort the architecture to pursue a model-specific bonus that the selected deployment does not qualify for.

## E-Delivery 6. Release and submission record

The guide requires a public repository, identifies a maximum team size of four, and limits the demo to clearly identifiable hackathon work. It calls for open-source work but does not specify a particular project license in the reviewed text. The founders should select the repository license deliberately and retain notices for dependencies and assets. Do not assume public access alone grants reuse rights.

The official terms also grant organizers broad rights to submitted material and do not treat submissions as confidential. Keep confidential startup/customer materials outside the submission. This is a practical submission-design constraint, not a reason to delay the public prototype. Sources: [participant guide](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/details), [official terms](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver).

Required repository documentation:

| File | Content |
|---|---|
| `README.md` | Product purpose, live demo/video, setup, supported scope, Meta usage, architecture, sample workflow |
| `AGENTS.md` | Durable coding rules from the next section |
| `docs/NodeSnap_Master_Build_Specification.md` | This specification |
| `docs/build-status.md` | Current milestone, completed evidence, failures, next actions |
| `docs/capabilities.md` | Planned capability, implemented method, validated domain, evidence and gap |
| `docs/engineering-methods.md` | Method/source/edition/domain registry and independent references |
| `docs/decisions.md` | Material choices and changes with rationale |
| `docs/new-work-log.md` | Actual event work dates, contributions, reused components |
| `docs/source-and-license-register.md` | Sources, rights/access restrictions, data/assets and dependency notices |
| `docs/demo-runbook.md` | Exact reproducible demo steps, known failure recovery, recorded fallback |
| `docs/deployment.md` | Build/start/migration/backup/restore configuration with no secrets |
| `.env.example` | Empty secrets and documented configuration names |

Before submission, the founders should verify public repository access, product URL access in a fresh browser, video duration/access, contributor identities, actual theme/track choices, source/license records, and final claim accuracy. Capture the submission confirmation. Do not assume a successfully uploaded video means the competition entry was submitted.

Keep the final demonstration snapshot, permissible cached evidence, export hashes, lockfiles, and commit identifier. Judges should be able to reproduce the stated scenario without using private owner data or hidden manual calculations.

## E-Delivery 7. Coding-agent kickoff prompt

Copy the following into Muse Code after placing this specification in the repository. Select Muse Wonder Full through the installed interface before starting.

> Read docs/NodeSnap_Master_Build_Specification.md completely. It is the authoritative assignment for NodeSnap. Inspect the repository before changing it. Build the application in the specified milestones, beginning with M0 and M1. Do not stop after producing a plan.
>
> First create a concise implementation plan, the capability ledger, and AGENTS.md using the supplied rules. Then scaffold the specified stack, implement the canonical schemas/statuses, verify actual Meta access, and establish one end-to-end path from a persisted demo building to plan/3D, a real calculation, and a revision-specific vector PDF.
>
> Use Meta-only AI. Keep Muse Wonder Full development access separate from application API access. Use deterministic geometry and numerical tools for authoritative geometry/calculations. Do not invent APIs, model identifiers, source values, code factors, site measurements, engineering results, professional approvals or completed tests.
>
> Follow the exact room program, basement pool, roof terrace, NYC scope and full discipline target. Maintain honest coverage and unresolved-input records. Read the relevant engineering and NYC sections before implementing each module. Verify dependency APIs against their installed versions and official documentation.
>
> At each milestone, run the meaningful checks, inspect actual outputs, fix failures, and update docs/build-status.md with evidence and next actions. Continue routine reversible work independently. Escalate only specific missing access, source rights, irreconcilable requirements or founder-controlled business actions. Never hide an engineering gap by returning a placeholder pass.

For a headless workflow, Muse Code documents `muse exec --prompt-file`. Put the kickoff text in a prompt file and use the installed version's help to confirm its invocation and selected model. Do not guess a Full model CLI identifier. The interactive model picker is the preferred initial setup. Source: [Muse Code configuration](https://dev.meta.ai/docs/muse-code/configuration).

## E-Delivery 8. Proposed AGENTS.md

Use this project-specific content after merging any legitimate repository instructions. Do not overwrite existing rules blindly.

```markdown
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
```

### Follow-up prompt after any milestone

> Read the current build status and inspect the implementation. Reconcile completed claims against actual tests and artifacts. Fix the highest-impact remaining failure, then continue the next milestone in the master specification. Preserve canonical contracts and the full target. Report exactly what now works, the evidence, and the remaining blockers.

## E-Delivery 9. Final release gate

The prototype is ready to present when a fresh user can complete the supported journey, the meaningful calculations agree with independent references, changes propagate correctly, the documents are internally consistent, and all remaining gaps are visible and accurately described.

The full professional-design target is achieved only as each applicable discipline and evidence requirement is actually completed. Preserve that distinction in the code, interface, documents, README and pitch. It is central to making NodeSnap credible as the platform expands beyond the demonstration.

---

## Source and verification note

Primary sources are linked beside the relevant claims throughout this file. The participant guide and official terms were read with browser access where the text reader could not retrieve them. Source identities and documented interfaces were researched as of 26 October 2026; successful live responses, account entitlements, current dataset schemas and every detailed engineering algorithm were not all verified in this planning exercise. Those implementation checks are explicitly assigned to milestones and method gates.

This specification's room program, software architecture, milestones, schemas, UI behavior and acceptance plan are original implementation decisions. Numerical beam examples are independently derived software fixtures. No approved villa design, proprietary calculation package, completed code implementation or actual permit has been supplied or represented as existing.
