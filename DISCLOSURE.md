# Pre-existing Assets vs. New Work — SpectraLineage Agent

Hackathon: Build with DataHub: The Agent Hackathon (datahub.devpost.com)
Submission period: 2026-07-06 – 2026-08-10

---

## Pre-existing (built before 2026-07-06)

| Asset | Description |
|---|---|
| ftir.fun production platform | 130K+ spectrum library, KG, RAG, LLM analysis — accessed read-only via API |
| FTIR.fun Spectral Auditor P0 demo | Evidence Gate governance framework: Axis Permission Registry, Citation Grade Contract, Audit Chain, Verdict Ladder — running at localhost:8234 |
| Conformance Suite C1–C8 | 8 local governance tests (no production calls) |
| Hero case (DEMO-RUBBER-001) | Pre-recorded rubber additive case with full audit chain |
| 20 years FTIR domain expertise | Domain knowledge behind the governance rules |

## New work during submission period (2026-07-06 – 2026-08-10)

| Asset | Description |
|---|---|
| `emitter.py` | DataHub Python SDK emitter — Dataset, DataFlow, DataJob, UpstreamLineage, DataJobInputOutput registration |
| `server.py` | FastAPI server (port 8235) bridging Spectral Auditor → DataHub |
| `static/` | New frontend (index.html / style.css / app.js) — Analyze / Lineage / Entities / Architecture tabs |
| DataHub integration design | Lineage schema, URN conventions, entity hierarchy for spectral provenance |
| `README.md` / `DISCLOSURE.md` | Hackathon documentation |

## What DataHub contributes (genuinely used, not window-dressing)

- **DatahubRestEmitter + MetadataChangeProposalWrapper** — all metadata writes
- **DatasetProperties** — spectrum metadata + verdict metadata as custom properties
- **UpstreamLineage / UpstreamClass** — spectrum → verdict lineage edge
- **DataFlow + DataJob** — pipeline and Evidence Gate step as first-class DataHub entities
- **DataJobInputOutput** — explicit I/O binding of the Evidence Gate job
- **REST API `/openapi/v3/relationships`** — lineage queries from backend
- **DataHub UI (localhost:9002)** — deep-linked from every registered entity

## Production safety declaration

- ftir.fun production platform: **read-only** access only (via FTIRFUN_API_KEY env, optional)
- DataHub: **local instance only** (localhost:8182 / 9002) — zero writes to any production system
- All demo data is pre-recorded or synthesized — no real customer data
