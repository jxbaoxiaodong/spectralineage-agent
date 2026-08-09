"""
SpectraLineage Agent — DataHub lineage emitter
Writes spectral analysis provenance to local DataHub (GMS at DATAHUB_GMS).
STRICTLY local DataHub only. Never touches ftir.fun production data.
"""
import os
from datetime import datetime, timezone

import httpx
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import (
    DatasetPropertiesClass,
    UpstreamLineageClass,
    UpstreamClass,
    DatasetLineageTypeClass,
    DataFlowInfoClass,
    DataJobInfoClass,
    DataJobInputOutputClass,
    StatusClass,
)

DATAHUB_GMS = os.getenv("DATAHUB_GMS", "http://localhost:8182")
PLATFORM = "ftir"
ENV = "PROD"
PIPELINE_ID = "spectral-auditor-pipeline"
JOB_ID = "evidence-gate"
FLOW_URN = f"urn:li:dataFlow:(spectralLineage,{PIPELINE_ID},{ENV})"
JOB_URN = f"urn:li:dataJob:({FLOW_URN},{JOB_ID})"


def dataset_urn(name: str) -> str:
    return f"urn:li:dataset:(urn:li:dataPlatform:{PLATFORM},{name},{ENV})"


class SpectralLineageEmitter:
    def __init__(self):
        self.gms = DATAHUB_GMS
        self._rest = DatahubRestEmitter(gms_server=self.gms)

    def _push(self, mcp: MetadataChangeProposalWrapper):
        self._rest.emit(mcp)

    def _ensure_pipeline(self):
        """Register the Spectral Auditor pipeline and Evidence Gate job in DataHub."""
        self._push(MetadataChangeProposalWrapper(
            entityUrn=FLOW_URN,
            aspect=DataFlowInfoClass(
                name="Spectral Auditor Pipeline",
                description=(
                    "FTIR.fun Evidence Gate — tri-axis retrieval (Library + KG + RAG/LLM) "
                    "with Axis Permission Registry, Citation Grade Contract (delta≤10 cm⁻¹), "
                    "Verdict Ladder, and SHA-256 Audit Chain per stage."
                ),
                project="spectral-lineage-agent",
            )
        ))
        self._push(MetadataChangeProposalWrapper(
            entityUrn=FLOW_URN, aspect=StatusClass(removed=False)
        ))
        self._push(MetadataChangeProposalWrapper(
            entityUrn=JOB_URN,
            aspect=DataJobInfoClass(
                name="Evidence Gate",
                description=(
                    "KG/RAG axes forbidden from writing resolved_level or direction_label "
                    "(Axis Permission Registry §2.1). Citation delta window ≤10 cm⁻¹. "
                    "SHA-256 checkpoint per stage. Falsification → EXPLICIT_FAIL."
                ),
                type="BATCH",
                flowUrn=FLOW_URN,
            )
        ))
        self._push(MetadataChangeProposalWrapper(
            entityUrn=JOB_URN, aspect=StatusClass(removed=False)
        ))

    def emit_analysis(self, case: dict) -> dict:
        """
        Register one spectral analysis run in DataHub.
        Creates: input Dataset → DataJob → output verdict Dataset, with lineage edges.
        Returns dict of URNs + verdict summary.
        """
        sample_id = case["sample_id"]
        s_urn = dataset_urn(f"{sample_id}.spectrum")
        v_urn = dataset_urn(f"{sample_id}.verdict")

        self._ensure_pipeline()

        # Input: raw spectrum dataset
        peaks = case.get("measured_peaks_cm", [])
        self._push(MetadataChangeProposalWrapper(
            entityUrn=s_urn,
            aspect=DatasetPropertiesClass(
                name=case.get("filename", f"{sample_id}.csv"),
                description=case.get("sample_description", "Unknown sample"),
                customProperties={
                    "measured_peaks_cm": ",".join(str(p) for p in peaks),
                    "peak_count": str(len(peaks)),
                    "note_missing": case.get("note_missing", ""),
                    "source": "ftir.fun",
                    "registered_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        ))
        self._push(MetadataChangeProposalWrapper(
            entityUrn=s_urn, aspect=StatusClass(removed=False)
        ))

        # Output: verdict dataset
        eg = case.get("evidence_gate", {})
        verdict = eg.get("verdict", "UNKNOWN")
        top1 = (case.get("library_result", {}).get("top_candidates") or [{}])[0]
        # audit_chain may be a list of steps or a dict with a "steps" key
        raw_audit = case.get("audit_chain", [])
        if isinstance(raw_audit, list):
            audit_steps = raw_audit
            audit_final_hash = audit_steps[-1].get("sha256", "") if audit_steps else ""
        else:
            audit_steps = raw_audit.get("steps", [])
            audit_final_hash = raw_audit.get("final_hash", "")

        # evidence_gate field aliases
        block_reason = eg.get("block_reason") or eg.get("blocked_reason", "")
        next_steps = eg.get("recommended_next_steps") or eg.get("next_steps", [])

        self._push(MetadataChangeProposalWrapper(
            entityUrn=v_urn,
            aspect=DatasetPropertiesClass(
                name=f"{sample_id}.verdict",
                description=(
                    f"Evidence Gate verdict [{verdict}]: {block_reason}"
                ),
                customProperties={
                    "verdict": verdict,
                    "verdict_ladder_level": eg.get("direction", eg.get("verdict_ladder", "")),
                    "blocked_reason": block_reason,
                    "entity_blocked": str(eg.get("entity_blocked", "")),
                    "top1_name": top1.get("name", ""),
                    "top1_similarity": str(top1.get("similarity", "")),
                    "top1_spectral_id": top1.get("spectral_id", ""),
                    "audit_steps": str(len(audit_steps)),
                    "audit_final_hash": audit_final_hash,
                    "next_steps": "; ".join(next_steps) if isinstance(next_steps, list) else str(next_steps),
                    "registered_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        ))
        self._push(MetadataChangeProposalWrapper(
            entityUrn=v_urn, aspect=StatusClass(removed=False)
        ))

        # Lineage: spectrum ──► verdict
        self._push(MetadataChangeProposalWrapper(
            entityUrn=v_urn,
            aspect=UpstreamLineageClass(
                upstreams=[UpstreamClass(
                    dataset=s_urn,
                    type=DatasetLineageTypeClass.TRANSFORMED,
                )]
            )
        ))

        # DataJob I/O
        self._push(MetadataChangeProposalWrapper(
            entityUrn=JOB_URN,
            aspect=DataJobInputOutputClass(
                inputDatasets=[s_urn],
                outputDatasets=[v_urn],
            )
        ))

        return {
            "spectrum_urn": s_urn,
            "verdict_urn": v_urn,
            "flow_urn": FLOW_URN,
            "job_urn": JOB_URN,
            "verdict": verdict,
            "top1_name": top1.get("name", ""),
            "top1_similarity": top1.get("similarity", 0),
        }

    def query_entity(self, urn: str) -> dict:
        try:
            r = httpx.get(f"{self.gms}/entities/v2/{urn}", timeout=5)
            return r.json() if r.status_code == 200 else {"status": r.status_code}
        except Exception as e:
            return {"error": str(e)}

    def search_datasets(self, query: str = "ftir", count: int = 20) -> list:
        """List datasets via DataHub OpenAPI v3 (works in v1.7.0)."""
        try:
            r = httpx.get(
                f"{self.gms}/openapi/v3/entity/dataset",
                params={"systemMetadata": "false", "count": count},
                timeout=8,
            )
            if r.status_code != 200:
                return []
            results = []
            for e in r.json().get("entities", []):
                urn = e.get("urn", "")
                props = (e.get("datasetProperties") or {}).get("value", {})
                platform = ""
                if "dataPlatform:" in urn:
                    platform = urn.split("dataPlatform:")[1].split(",")[0].rstrip(")")
                results.append({
                    "urn": urn,
                    "name": props.get("name", urn.split(",")[1] if "," in urn else urn),
                    "description": props.get("description", ""),
                    "platform": platform,
                    "custom_properties": props.get("customProperties", {}),
                })
            return results
        except Exception:
            return []

    def is_healthy(self) -> bool:
        try:
            return httpx.get(f"{self.gms}/health", timeout=2).status_code == 200
        except Exception:
            return False
