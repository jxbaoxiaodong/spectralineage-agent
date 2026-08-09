"""
SpectraLineage Agent — FastAPI server
Port 8235 | DataHub GMS: localhost:8182 | DataHub UI: localhost:9002
No production writes. All DataHub writes are local-only.
"""
import json, os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx
from dotenv import load_dotenv

from emitter import SpectralLineageEmitter, DATAHUB_GMS, FLOW_URN, JOB_URN

load_dotenv()

DEMO_PORT = int(os.getenv("DEMO_PORT", "8235"))
DATAHUB_FRONTEND = os.getenv("DATAHUB_FRONTEND", "http://localhost:9002")
FTIRFUN_API_KEY = os.getenv("FTIRFUN_API_KEY", "")
ROOT = Path(__file__).parent
CASES_DIR = ROOT / "cases"

app = FastAPI(
    title="SpectraLineage Agent",
    description="FTIR spectral provenance with DataHub lineage governance",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(ROOT / "static" / "index.html")


# ── health ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    em = SpectralLineageEmitter()
    return {
        "status": "ok",
        "datahub_gms": DATAHUB_GMS,
        "datahub_healthy": em.is_healthy(),
        "datahub_ui": DATAHUB_FRONTEND,
        "api_key_configured": bool(FTIRFUN_API_KEY),
        "live_analysis_available": bool(FTIRFUN_API_KEY),
    }


# ── hero case: analyze + register lineage in DataHub ─────────────────────

@app.post("/api/analyze/hero")
def analyze_hero():
    case_path = CASES_DIR / "hero_case.json"
    if not case_path.exists():
        raise HTTPException(404, "hero_case.json not found")
    case = json.loads(case_path.read_text())

    em = SpectralLineageEmitter()
    lineage = em.emit_analysis(case)

    # Build DataHub UI deep-link
    v_urn_encoded = lineage["verdict_urn"].replace(":", "%3A").replace(",", "%2C").replace("(", "%28").replace(")", "%29")
    dh_link = f"{DATAHUB_FRONTEND}/dataset/{v_urn_encoded}"

    return {
        "sample_id": case["sample_id"],
        "sample_description": case.get("sample_description"),
        "filename": case.get("filename"),
        "measured_peaks_cm": case.get("measured_peaks_cm"),
        "note_missing": case.get("note_missing"),
        "library_result": case.get("library_result"),
        "evidence_gate": case.get("evidence_gate"),
        "audit_chain": case.get("audit_chain"),
        "lineage_registered": lineage,
        "datahub_link": dh_link,
        "datahub_lineage_ui": f"{DATAHUB_FRONTEND}/lineage/{v_urn_encoded}",
    }


# ── lineage query for a sample ────────────────────────────────────────────

def _urn_encode(urn: str) -> str:
    return urn.replace(":", "%3A").replace(",", "%2C").replace("(", "%28").replace(")", "%29")


def _fetch_dataset_info(urn: str) -> dict:
    """Fetch dataset properties aspect directly — reliable in DataHub v1.7.0."""
    try:
        r = httpx.get(
            f"{DATAHUB_GMS}/aspects/{_urn_encode(urn)}",
            params={"aspect": "datasetProperties", "version": "0"},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            props = data.get("aspect", {}).get("com.linkedin.dataset.DatasetProperties", {})
            return {
                "exists": True,
                "name": props.get("name", ""),
                "description": props.get("description", ""),
                "custom_properties": props.get("customProperties", {}),
            }
    except Exception:
        pass
    return {"exists": False}


@app.get("/api/lineage/{sample_id}")
def get_lineage(sample_id: str):
    v_urn = f"urn:li:dataset:(urn:li:dataPlatform:ftir,{sample_id}.verdict,PROD)"
    s_urn = f"urn:li:dataset:(urn:li:dataPlatform:ftir,{sample_id}.spectrum,PROD)"

    spectrum_info = _fetch_dataset_info(s_urn)
    verdict_info = _fetch_dataset_info(v_urn)

    chain = [
        {
            "step": 1, "type": "dataset", "label": "Input Spectrum",
            "urn": s_urn,
            "name": spectrum_info.get("name", f"{sample_id}.spectrum"),
            "exists_in_datahub": spectrum_info.get("exists", False),
            "datahub_url": f"{DATAHUB_FRONTEND}/dataset/{_urn_encode(s_urn)}",
        },
        {
            "step": 2, "type": "dataflow", "label": "Pipeline",
            "urn": FLOW_URN,
            "name": "spectral-auditor-pipeline",
            "datahub_url": f"{DATAHUB_FRONTEND}/pipelines/{FLOW_URN}",
        },
        {
            "step": 3, "type": "datajob", "label": "Evidence Gate",
            "urn": JOB_URN,
            "name": "evidence-gate (Citation Grade Contract)",
            "datahub_url": f"{DATAHUB_FRONTEND}/tasks/{JOB_URN}",
        },
        {
            "step": 4, "type": "dataset", "label": "Output Verdict",
            "urn": v_urn,
            "name": verdict_info.get("name", f"{sample_id}.verdict"),
            "verdict": verdict_info.get("custom_properties", {}).get("verdict", ""),
            "exists_in_datahub": verdict_info.get("exists", False),
            "datahub_url": f"{DATAHUB_FRONTEND}/dataset/{_urn_encode(v_urn)}",
        },
    ]

    return {
        "sample_id": sample_id,
        "lineage_confirmed": spectrum_info.get("exists", False) and verdict_info.get("exists", False),
        "lineage_chain": chain,
        "spectrum": {**spectrum_info, "urn": s_urn},
        "verdict": {**verdict_info, "urn": v_urn},
        "datahub_lineage_ui": f"{DATAHUB_FRONTEND}/lineage/{_urn_encode(v_urn)}",
    }


# ── DataHub entity list ────────────────────────────────────────────────────

@app.get("/api/entities")
def list_entities():
    em = SpectralLineageEmitter()
    datasets = em.search_datasets("ftir", count=20)
    return {
        "count": len(datasets),
        "datasets": datasets,
        "datahub_ui": DATAHUB_FRONTEND,
        "pipeline_url": f"{DATAHUB_FRONTEND}/pipelines/{FLOW_URN}",
    }


# ── live analysis via production API (read-only, opt-in) ──────────────────

@app.post("/api/analyze/live")
async def analyze_live(peaks: str, sample_id: str = "CUSTOM-001"):
    """Proxy to ftir.fun production API (read-only). Requires FTIRFUN_API_KEY."""
    if not FTIRFUN_API_KEY:
        raise HTTPException(
            503,
            detail="FTIRFUN_API_KEY not set — running in pre-recorded demo mode. "
                   "Set FTIRFUN_API_KEY in .env to enable live analysis.",
        )
    peak_list = [int(p.strip()) for p in peaks.split(",") if p.strip()]
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://ftir.fun/ftir/analyze_spectrum",
            headers={"Authorization": f"Bearer {FTIRFUN_API_KEY}"},
            json={"peaks": peak_list, "sample_id": sample_id},
            timeout=30,
        )
    result = r.json()
    em = SpectralLineageEmitter()
    lineage = em.emit_analysis({
        "sample_id": sample_id,
        "filename": f"{sample_id}.csv",
        "measured_peaks_cm": peak_list,
        **result,
    })
    return {"result": result, "lineage_registered": lineage}
