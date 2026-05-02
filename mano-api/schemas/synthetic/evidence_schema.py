"""
Schemas for the PubMed Evidence (v2) service.

Shape
-----
Each ``EvidenceCard`` represents one peer-reviewed study attached to an
intervention recommendation. Cards are deduplicated by ``pmid`` and sorted
by journal-prestige / publication-year heuristics inside the service.

The enclosing ``EvidenceResponse`` carries a standard source-tag envelope so
the frontend can render trust badges (live / cached / fallback) without
having to read service-specific metadata.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EvidenceCard(BaseModel):
    pmid: str
    title: str
    authors_short: str = Field(
        ...,
        description="First author 'et al.' form, e.g. 'Smith JA et al.'.",
    )
    journal: str
    year: Optional[str] = None
    url: str
    pub_types: List[str] = Field(
        default_factory=list,
        description="PubMed publication types, e.g. 'Randomized Controlled Trial'.",
    )
    is_systematic_review: bool = False
    abstract_snippet: Optional[str] = Field(
        default=None,
        description="First ~400 chars of the abstract. Only populated when EFetch succeeds.",
    )


class EvidenceRequest(BaseModel):
    intervention: str = Field(
        ...,
        description=(
            "Intervention keyword. Matches curated search-term table if known "
            "(cbt, exercise, meditation, …); otherwise a free-form search is run."
        ),
    )
    max_results: int = Field(default=3, ge=1, le=10)
    include_abstract: bool = Field(
        default=True,
        description="When True, an extra EFetch call is made to populate abstract snippets.",
    )


class EvidenceResponse(BaseModel):
    intervention: str
    cards: List[EvidenceCard]
    source: str = Field(..., description="live | cached | fallback")
    provider: str = Field(default="pubmed")
    cache_key: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
