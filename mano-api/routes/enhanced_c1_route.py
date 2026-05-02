"""
Enhanced Component 1 API — Narrative + Evidence + Social Proof

New endpoints (additive — all existing C1 routes preserved):
  POST /api/v1/enhanced/narrative     — Future-Self journal from Seq2Seq output
  GET  /api/v1/enhanced/evidence/{t}  — PubMed evidence for an intervention
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict
from lib.synthetic.narrative_service import narrative_engine, pubmed_service

router = APIRouter(prefix="/api/v1/enhanced", tags=["Component 1 Enhancements"])


class NarrativeRequest(BaseModel):
    intervention_name: str
    simulation_data: Dict  # {changes: {stress: -0.3, anxiety: -0.5, ...}}
    user_profile: Optional[Dict] = None


@router.post(
    "/narrative",
    summary="Generate a Future-Self journal entry from simulation data",
    description=(
        "Translates Seq2Seq numerical outcomes into an emotionally resonant "
        "first-person journal entry using Groq/Llama 3 (free: 30 RPM, 14.4K req/day). "
        "Falls back to template narrative if API is unavailable."
    ),
)
async def generate_narrative(request: NarrativeRequest):
    try:
        narrative = await narrative_engine.generate_narrative(
            intervention_name=request.intervention_name,
            simulation_data=request.simulation_data,
            user_profile=request.user_profile,
        )
        return {
            "narrative": narrative,
            "intervention": request.intervention_name,
            "source": "groq" if narrative_engine.is_available else "template",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Narrative generation error: {str(e)}",
        )


@router.get(
    "/evidence/{intervention_type}",
    summary="Get PubMed research evidence for an intervention",
    description=(
        "Searches PubMed E-utilities (free, no API key, 3 req/sec) for published "
        "research supporting a specific intervention. Returns title, authors, journal, "
        "year, and direct PubMed link for each study."
    ),
)
async def get_evidence(intervention_type: str, max_results: int = 3):
    try:
        evidence = await pubmed_service.get_evidence(intervention_type, max_results)
        return {
            "intervention": intervention_type,
            "evidence_count": len(evidence),
            "studies": evidence,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PubMed search error: {str(e)}",
        )
