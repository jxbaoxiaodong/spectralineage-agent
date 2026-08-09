# SpectraLineage Agent

**Build with DataHub: The Agent Hackathon** — FTIR spectral provenance governance via DataHub lineage

> Every FTIR spectrum analysis is registered in DataHub as a first-class lineage chain:
> raw spectrum file → Evidence Gate pipeline → verdict dataset.
> Full provenance. Immutable audit. Reproducible.

## Demo

```
http://localhost:8235        # SpectraLineage Agent UI
http://localhost:9002        # DataHub UI (lineage graph, entities)
```

## Architecture

```
Spectrum CSV
    │
    ▼
[Library Search]  ←── 130K+ spectra (ftir.fun)
    │
    ▼
[Evidence Gate]   ←── Axis Permission Registry
    │                  Citation Grade Contract (Δ≤10 cm⁻¹)
    │                  SHA-256 Audit Chain
    ▼
Verdict Dataset
    │
    ▼  (registered via DataHub Python SDK)
DataHub
    ├── Dataset: {sample}.spectrum   (input, with peak metadata)
    ├── DataFlow: spectral-auditor-pipeline
    ├── DataJob:  evidence-gate
    └── Dataset: {sample}.verdict    (output, verdict + audit metadata)
              └── UpstreamLineage → {sample}.spectrum
```

## DataHub Integration

| SDK Feature | Usage |
|---|---|
| `DatahubRestEmitter` | All metadata writes to local DataHub GMS |
| `MetadataChangeProposalWrapper` | MCP-based entity registration |
| `DatasetProperties` | Spectrum metadata + verdict metadata as custom properties |
| `UpstreamLineage` | spectrum → verdict lineage edge (TRANSFORMED) |
| `DataFlow + DataJob` | Pipeline and Evidence Gate as first-class entities |
| `DataJobInputOutput` | Explicit I/O binding |
| REST `/aspects/{urn}` | Entity existence & property verification |
| REST `/openapi/v3/entity/dataset` | Dataset catalog listing |

## Quick Start

```bash
# 1. Start DataHub (images already cached, ~30s)
datahub docker quickstart --no-pull

# 2. Install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure (optional — leave FTIRFUN_API_KEY blank for demo mode)
cp .env.example .env

# 4. Start the agent
uvicorn server:app --host 0.0.0.0 --port 8235

# 5. Open UI
open http://localhost:8235
```

## Hero Case

**Sample:** Unknown Rubber Additive (industrial QC batch 47)
**Measured peaks:** 710, 820, 1060, 1240, 1375, 1460, 1540, 1600, 2920, 3000, 3060 cm⁻¹
**Library Top-1:** Polymeric Carbodiimide (anti-hydrolysis agent) — 70% similarity
**Key finding:** Required N=C=N stretch at 2110–2140 cm⁻¹ is **absent** → entity verdict blocked
**Verdict:** `library_direction` / YELLOW
**Next steps:** Pyrolysis GC-MS, XRF, TGA

## Why this matters

Bare LLM: "70% match, probably Polymeric Carbodiimide"
SpectraLineage Agent: "Library similarity 70%, but the definitive N=C=N peak at 2130 cm⁻¹ is
absent. Entity verdict blocked. Recommend pyrolysis GC-MS. Full lineage registered in DataHub."

## License

Apache 2.0 — see LICENSE
