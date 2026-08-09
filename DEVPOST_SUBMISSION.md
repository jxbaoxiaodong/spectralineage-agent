# DEVPOST SUBMISSION DRAFT
# Build with DataHub: The Agent Hackathon
# https://datahub.devpost.com/
#
# FILL IN: GitHub repo URL, video URL, team member(s)
# SUBMIT AT: https://datahub.devpost.com/

---

## Project Name
SpectraLineage Agent

## Tagline
Every FTIR spectrum analysis registered in DataHub as a first-class lineage chain — from raw CSV to evidence-gated verdict, fully provenance-tracked.

## What it does

SpectraLineage Agent turns FTIR spectral analysis into a governed, auditable pipeline by registering every analysis as a complete DataHub lineage chain.

The agent:
1. Accepts a raw FTIR spectrum (CSV of wavenumber peaks)
2. Runs the **Evidence Gate** — a 6-rule citation-grade contract:
   - Axis Permission Registry (wavenumber range validation)
   - Citation Grade Contract (library peak match Δ≤10 cm⁻¹)
   - SHA-256 Audit Chain (each step hash-chained)
   - Verdict Ladder (GREEN / YELLOW / RED)
3. Registers the full provenance in DataHub via the Python SDK:
   - `Dataset` entity: input spectrum (with measured peaks as metadata)
   - `DataFlow`: spectral-auditor-pipeline
   - `DataJob`: evidence-gate
   - `Dataset` entity: output verdict (with verdict, similarity, next-steps)
   - `UpstreamLineage`: spectrum → verdict (TRANSFORMED)
   - `DataJobInputOutput`: explicit I/O binding

**Hero case — DEMO-RUBBER-001:**
Unknown rubber additive, industrial QC batch. Library top-1 match is Polymeric Carbodiimide (70% similarity), but the definitive N=C=N stretch at 2110–2150 cm⁻¹ is absent. Evidence Gate blocks the entity verdict. SpectraLineage Agent registers this as a `library_direction` / YELLOW verdict with pyrolysis GC-MS recommended as the next step — and the entire chain is queryable in DataHub.

## How I built it

- **DataHub Python SDK** (`acryl-datahub==1.7.0`): `DatahubRestEmitter` + `MetadataChangeProposalWrapper` for all metadata writes
- **FastAPI** agent on port 8235 with 4 endpoints: analyze/hero, lineage/{id}, entities, health
- **Vanilla JS SPA** with 4 tabs: Analyze, Lineage, Entities, Architecture — no framework dependencies
- **DataHub Quickstart** (v1.7.0): GMS on :8182, frontend on :9002, full local stack
- Each analysis writes 7 MCP proposals to DataHub → confirmed 200 OK on all writes

## Challenges

- DataHub v1.7.0 relationship graph indices are populated asynchronously (MAE consumer). The `/relationships` REST endpoint returns empty immediately after write. Fixed by using direct `/aspects/{urn}` fetch to verify entity existence — reliable for deterministic lineage confirmation.
- The audit chain field in the case data is a list (not a dict), requiring defensive handling on both the emitter and frontend.

## Accomplishments

- Full end-to-end lineage chain running locally: spectrum CSV → Evidence Gate → verdict, all 4 entities confirmed in DataHub
- Zero production writes — DataHub instance is local-only, ftir.fun integration is read-only (API key optional)
- Complete provenance: verdict metadata includes audit_final_hash, audit_steps, next_steps, registered_at

## What I learned

DataHub's MCP-based write API is robust and simple — 7 `ingestProposal` calls cover the full entity + lineage + job I/O graph. The async indexing behavior of the relationship graph is expected in single-node quickstart setups and the aspects REST API provides a reliable synchronous verification path.

## What's next

- Multi-sample batch: queue N spectra, register all in one DataHub pipeline run
- Live integration: `POST /api/analyze/live` already wired — set `FTIRFUN_API_KEY` to enable real-time FTIR.fun spectrum analysis with immediate DataHub registration
- DataHub Policies: add fine-grained access control per sample origin

## Built With

- datahub (Python SDK, v1.7.0)
- fastapi
- python
- javascript

## GitHub Repository
https://github.com/jxbaoxiaodong/spectralineage-agent

## Demo Video
[TODO — record < 3 minutes: run hero case → show DataHub entities at :9002 → show lineage graph]

## Try It Out
https://github.com/jxbaoxiaodong/spectralineage-agent

