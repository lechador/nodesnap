# Source and license register

Recorded 2026-10-31. This register distinguishes engineering sources, visual inspiration, authored presentation assets and installed software. Referenced websites do not grant permission to copy their models, photographs, diagrams or branded UI. No visual-reference asset was downloaded into the application during the rewrite.

## Product source reconciliation

The repository master specification and the user-supplied plain-text attachment contain the same substantive assignment. Full-text comparison after removing link markup/punctuation found only list numbering and code-fence language-label differences (56 tokens); no changed room program, discipline, deployment or acceptance requirement.

- Repository specification SHA-256: `6c6742bc565f01faa04589a055d955c9a0ad0add659ff77bb5567f13db4d900c`.
- User attachment SHA-256: `a2c4d63f7f38927eafc2708174bb93f9e16fd8df71857d046f874cbacc5b3335`.
- Attachment retained outside the public repository; no private path or customer data is copied into fixtures.

## Visual references and assets

| Source / asset | Use | Rights treatment |
|---|---|---|
| [Chief Architect](https://www.chiefarchitect.com/) | User-supplied reference for architectural modeling workflow and presentation | Inspiration only; no proprietary code, model, screenshot or plan copied |
| [Pinterest building-plan collection](https://www.pinterest.com/georgemuchm6/building-plan/) | User-supplied reference for plan clarity and architectural linework | Inspiration only; individual images/rights not imported |
| [CGTrader tropical modern villa](https://www.cgtrader.com/3d-models/architectural/other/tropical-modern-villa-at-sunset) | User-supplied reference for contemporary stone/timber/glass character | No purchase, download, model or texture reuse; listing is not a license grant |
| [LinkedIn workflow video](https://www.linkedin.com/feed/update/urn:li:activity:7511381277690712065/) | User-supplied interaction/workflow reference | Reference only; no video, account data or frames embedded in product |
| [Awesome gamedev agent skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) | User-suggested development guidance | No downloaded third-party game asset or copied engine source used |
| Stone/timber textures | Authored procedural CanvasTexture generation in `apps/web/app/Villa3D.tsx` | Repository-authored presentation code; no remote texture service |
| Furniture, landscape and scene lighting | Authored procedural presentation geometry | Illustrative only; excluded from canonical engineering quantities |
| Plans, building geometry, room/door/stair objects | Derived from repository canonical model and disclosed assumptions | Original synthetic fixture; no private architectural plan or measured site copied |
| Interface icons | Authored inline SVG strokes | No icon image service or licensed icon pack added |
| Geist / Geist Mono | Existing Next.js font integration | [SIL Open Font License 1.1](https://raw.githubusercontent.com/vercel/geist-font/main/OFL.txt), Copyright 2024 The Geist Project Authors; fetched by Next font build integration |
| Report fonts | ReportLab standard PDF font references (Helvetica) | No commercial font file added to this repository |

## Dependency versions and notices

Versions below were read from installed package metadata on the rewrite workstation. Runtime frontend versions are exact-pinned in package.json. Exact dependency resolution and integrity hashes are in `uv.lock` and `apps/web/pnpm-lock.yaml`. License labels are metadata summaries; retain each package's distributed license/notice files, including transitive bundled native-library notices.

| Runtime package | Installed version | License metadata |
|---|---:|---|
| Next.js | 16.4.3 | MIT |
| React / React DOM | 19.3.0 | MIT |
| Three.js | 0.180.0 | MIT |
| React Three Fiber | 9.8.2 | MIT |
| Drei | 10.7.9 | MIT |
| Konva | 10.9.0 | MIT |
| react-konva | 19.3.2 | MIT |
| Zustand | 5.0.16 | MIT |
| FastAPI | 0.162.0 | MIT |
| Pydantic | 2.14.1 | MIT |
| Shapely | 2.2.0 | BSD-3-Clause; bundled GEOS notices remain applicable |
| OR-Tools | 9.15.6755 | Apache-2.0 |
| PyNiteFEA | 3.2.0 | MIT |
| ReportLab | 5.1.0 | BSD, per distributed `license.txt` |
| SQLAlchemy | 2.1.6 | MIT |
| HTTPX | 0.28.1 | BSD-3-Clause |
| NumPy | 2.5.4 | BSD-3-Clause and bundled 0BSD/MIT/Zlib/CC0 notices |
| SciPy | 1.18.1 | BSD license plus bundled native-library notices/runtime exceptions |
| psycopg | 3.3.6 | LGPL-3.0-only |

Development/inspection: TypeScript 5.9.3 (Apache-2.0), Prettier 3.9.10 (MIT), openapi-typescript 7.13.0 (MIT), pytest 9.1.1 (MIT), PyMuPDF 2.0 (AGPL-3.0 or Artifex commercial license per distribution metadata). PyMuPDF is used only in the dev dependency group for PDF rendering/tests; the API image installs with `--no-dev`. Do not assume its dual license is permissive production embedding. No repository-wide license has been selected by this rewrite; that remains a founder decision.

Existing deployment images remain `python:3.12-slim`, `node:24-slim`, `postgres:17`, `redis:7`, and `caddy:2`. Their tags were preserved, not newly pinned to immutable digests; upstream image/software licenses and notices remain applicable.

## Engineering, provider and software documentation

| Source | Used for | Verification boundary |
|---|---|---|
| [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/) | Typed commands, discriminated unions and model validation | Implementation/reference reading; package compatibility established by tests |
| [Shapely manual](https://shapely.readthedocs.io/en/stable/manual.html) | Polygon validity, area, containment and boundary geometry | Geometric operations only |
| [CP-SAT documentation](https://developers.google.com/optimization/cp/cp_solver) | Integer optimization, statuses and bounded search | Bounded family only; native `OPTIMAL` is not a house-design claim |
| [ReportLab vector graphics](https://docs.reportlab.com/reportlab/userguide/ch2_graphics/) | Canonical vector drawing, page and coordinate behavior | Actual generated pages rendered/inspected |
| [PyNite documentation](https://pynite.readthedocs.io/en/latest/) | Structural adapter API and declared assumptions | Independent fixtures verify a restricted method, not project design |
| [Meta model catalog](https://dev.meta.ai/docs/models), [structured output](https://dev.meta.ai/docs/structured-output), [pricing](https://dev.meta.ai/docs/pricing-rate-limits) | Provider allowlist, schema boundary and estimated reservation/spend | Server-only adapter; current live-call evidence belongs in build status |
| NYC/ASHRAE/other engineering links in specification Parts C/D | Jurisdiction profile and future method/source gates | References retained; no code coefficients or proprietary standard text invented/copied |

Current public fixtures are synthetic. No survey, parcel ownership record, customer drawing, signature, seal, authority approval or private credential is included. Official-source authority is distinct from measured site evidence; source links alone never close a discipline-design gate.
