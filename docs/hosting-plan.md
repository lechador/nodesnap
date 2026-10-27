# Hosting plan

Decision recorded 2026-10-27: develop locally without Docker; **production = one VPS +
Docker Compose** from `infra/docker-compose.yml`. Deadline context: submission
4 Nov 21:00 ET; judges must open a public HTTPS URL in a fresh browser.

## Recommendation

**One VPS, everything on it** (web + api + Postgres + Redis + Caddy for TLS).
NodeSnap is a 4-service app with tiny traffic and heavy-but-bursty Python
(PyNite/SciPy). Splitting it across PaaS services buys nothing for the demo and
adds cookie/CORS/build failure modes. One box = one `docker compose up`, one
backup, one log stream.

Sizing: minimum 2 vCPU / 4 GB (Next build + frame analysis), comfortable 4 vCPU / 8 GB.

| Option | Cost | Effort | Risk for the demo |
|---|---|---|---|
| **Hetzner CX33** (4 vCPU / 8 GB / 80 GB, EU or US) | **€8.99/mo** incl. IPv4, hourly billing (≈ €0.014/h) | Medium: you run Docker + updates | EU latency to US judges ~100 ms — fine for this app; single point of failure |
| DigitalOcean NYC (2 vCPU / 4 GB) | $24/mo | Medium | Same shape, US-East for judges, 3× the price |
| Your existing Zenhost/CloudPanel server | $0 marginal | Low–Medium | Only if Docker is available there; otherwise processes + nginx by hand. Check first — free beats new |
| Render (2 web services + Postgres + Key Value) | ≈ $7+$25+$6+$10 = **$48/mo** (2 GB API tier) | Low | Free tiers spin down (fatal for judges); per-service pricing stacks; artifacts need a paid disk |
| Vercel (web) + VPS (api/db) | $0–20 + VPS | Medium–High | Two deploys, rewrite/cookie edge cases; only worth it after the hackathon |

Prices checked 27 Oct 2026 (Hetzner June-2026 rate card; Render published pricing).

## Target architecture on the box

```
Internet → Caddy (:443, automatic Let's Encrypt)
             ├─ nodesnap.<domain>      → web:3000  (Next.js; /api + /artifacts proxied by Next rewrites)
             └─ (same origin — no CORS, session cookie stays first-party)
Docker Compose: web · api · postgres · redis
Volumes: pgdata (projects/revisions/spend ledger) · artifacts (PDFs, manifests, model JSON)
```

Keep the single-origin design: the web container proxies API calls, so the
guest-session cookie never crosses domains.

## Launch sequence (≈ 1 hour)

1. Provision the VPS (or confirm Docker on the existing server). Harden: SSH key only, ufw 22/80/443.
2. Point DNS `nodesnap.<your-domain>` A-record at the box (a subdomain of a domain you already own = $0; a fresh short domain ≈ $10–15/yr if you want it for the pitch).
3. `git clone` the public repo; create `.env` **on the server** (never commit): `META_API_KEY`, strong `SESSION_SECRET`, Postgres password, `APP_SPEND_CEILING_USD=135`, `DEMO_MODE=true`.
4. Add the Caddy service to Compose (or host Caddy) with the domain; `docker compose up --build -d`.
5. Smoke-test from a **fresh browser/incognito**: the 3 runbook scenarios (docs/demo-runbook.md), one chat edit, one mic transcription, one export download. Check `GET /health` spend reads $0-ish.
6. Snapshot/backup the box; record the URL + commit hash in docs/build-status.md.
7. Freeze content 3 Nov; leave the box running through judging (a week of Hetzner ≈ €2–3).

## App-specific pre-launch checks

- [ ] Fresh production DB (no local test projects/spend in the ledger)
- [ ] `META_API_KEY` works from the server (one chat call; watch spend ≈ $0.04)
- [ ] Artifacts volume persists across `docker compose down/up` (export, restart, download again)
- [ ] Postgres volume persists revisions across restarts
- [ ] HTTPS valid; page loads with no mixed-content or console errors
- [ ] Public GitHub repo contains no `.env`, no private data (checked before pushing)
- [ ] Backup snapshot taken after the successful rehearsal

## After the hackathon (only if it grows)

Split when a single box hurts: web → Vercel, api stays on the VPS behind its
own subdomain, Postgres → managed (DO/Hetzner volume snapshots first), artifacts
→ object storage (R2/S3) behind the same artifact IDs. The contracts
(DATABASE_URL/REDIS_URL/ARTIFACT_ROOT env) already allow this without code changes.
