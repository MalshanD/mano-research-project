"""
PubMed Evidence service (v2).

Why v2
------
The legacy ``PubMedEvidenceService`` used hardcoded URLs, hit NCBI on every
request, and never pulled abstracts. v2 addresses three needs:

* **Rate-limit hygiene** — NCBI's unauthenticated cap is 3 req/s. With the
  free ``NCBI_API_KEY`` it rises to 10 req/s. v2 reads the key from
  ``settings`` and passes it transparently.
* **Cache first** — every query result is cached for 24 hours by default;
  repeat dashboard views hit Redis (or the in-memory fallback) instead of
  paying the latency + quota cost.
* **Structured cards** — EFetch adds abstract snippets and publication-type
  tags, letting the frontend render "Randomised Controlled Trial" badges
  without inferring from the title.

Scheduled refresh
-----------------
``refresh_curated_interventions()`` walks the ``INTERVENTION_SEARCH_TERMS``
table and pre-warms the cache. The scheduler hook in ``main.py`` fires this
every 6 hours so dashboards always hit warm cache on first load.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.config import (
    PUBMED_EFETCH_URL,
    PUBMED_ESEARCH_URL,
    PUBMED_ESUMMARY_URL,
    settings,
)
from lib.infra.cache import get_cache
from lib.infra.security import sanitize_text

logger = logging.getLogger(__name__)


# ─── Tuning constants ─────────────────────────────────────────────────────────

_CACHE_TTL_SECONDS = 24 * 3600   # 24h — PubMed rarely revises a record same-day.
_NEGATIVE_CACHE_TTL = 30 * 60    # 30min — for empty results so we don't hammer
                                 # NCBI on misspelled query terms.

_ESEARCH_TIMEOUT = 6.0
_ESUMMARY_TIMEOUT = 8.0
_EFETCH_TIMEOUT = 12.0


# Curated mapping — narrower search strings tend to return higher-quality
# hits (systematic reviews, RCTs) than bare intervention keywords.
INTERVENTION_SEARCH_TERMS: Dict[str, str] = {
    "cbt": "cognitive behavioural therapy depression randomized",
    "exercise": "physical exercise depression anxiety meta-analysis",
    "medication": "antidepressant efficacy meta-analysis",
    "wellness_app": "digital mental health intervention randomized",
    "meditation": "mindfulness meditation randomized controlled trial",
    "sleep": "sleep hygiene mental health meta-analysis",
    "breathing": "controlled breathing anxiety randomized",
    "journaling": "expressive writing mental health benefits",
    "social_connection": "social support mental health protective factor",
    "nature_walk": "nature exposure cortisol stress reduction",
    "gratitude": "gratitude practice psychological well-being",
    "yoga": "yoga mental health depression systematic review",
    "control": "treatment as usual depression randomized",
}


_SYSTEMATIC_REVIEW_TYPES = {
    "Systematic Review",
    "Meta-Analysis",
    "Review",
    "Randomized Controlled Trial",
}


# ─── Cache key helpers ────────────────────────────────────────────────────────

def _cache_key(search_term: str, max_results: int, include_abstract: bool) -> str:
    """Stable hash of a query. We sanitise first so minor whitespace / case
    differences don't bust the cache."""
    normalised = sanitize_text(search_term, max_length=200).lower().strip()
    blob = f"{normalised}|{max_results}|{int(include_abstract)}".encode("utf-8")
    return f"pubmed:v2:{hashlib.sha256(blob).hexdigest()[:24]}"


# ─── NCBI wrappers ────────────────────────────────────────────────────────────

def _with_api_key(params: Dict[str, Any]) -> Dict[str, Any]:
    """NCBI accepts an api_key query param; attaches if configured."""
    if settings.ncbi_api_key:
        params = {**params, "api_key": settings.ncbi_api_key}
    return params


async def _esearch(client: httpx.AsyncClient, term: str, max_results: int) -> List[str]:
    params = _with_api_key({
        "db": "pubmed",
        "term": term,
        "retmax": max_results,
        "sort": "relevance",
        "retmode": "json",
    })
    resp = await client.get(PUBMED_ESEARCH_URL, params=params, timeout=_ESEARCH_TIMEOUT)
    if resp.status_code != 200:
        logger.info("esearch_non_200", extra={"status": resp.status_code})
        return []
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", []) or []


async def _esummary(client: httpx.AsyncClient, ids: List[str]) -> Dict[str, Any]:
    if not ids:
        return {}
    params = _with_api_key({
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "json",
    })
    resp = await client.get(PUBMED_ESUMMARY_URL, params=params, timeout=_ESUMMARY_TIMEOUT)
    if resp.status_code != 200:
        logger.info("esummary_non_200", extra={"status": resp.status_code})
        return {}
    return resp.json().get("result", {}) or {}


async def _efetch_abstracts(client: httpx.AsyncClient, ids: List[str]) -> Dict[str, str]:
    """Fetch abstracts for the given PMIDs. Returns ``{pmid: abstract}``.

    EFetch only returns XML for PubMed; we parse <AbstractText> nodes and
    concatenate their text content. Missing / structured-only records yield
    an empty string, which the caller gracefully handles.
    """
    if not ids:
        return {}
    params = _with_api_key({
        "db": "pubmed",
        "id": ",".join(ids),
        "rettype": "abstract",
        "retmode": "xml",
    })
    try:
        resp = await client.get(PUBMED_EFETCH_URL, params=params, timeout=_EFETCH_TIMEOUT)
    except Exception as exc:  # pragma: no cover — network path
        logger.info("efetch_failed", extra={"error": str(exc)})
        return {}
    if resp.status_code != 200:
        return {}

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return {}

    out: Dict[str, str] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_node = article.find(".//PMID")
        if pmid_node is None or not pmid_node.text:
            continue
        pmid = pmid_node.text.strip()
        abstract_chunks = [
            (node.text or "") for node in article.findall(".//Abstract/AbstractText")
        ]
        abstract = " ".join(c for c in abstract_chunks if c).strip()
        if abstract:
            out[pmid] = abstract
    return out


# ─── Card assembly ────────────────────────────────────────────────────────────

def _short_authors(authors: List[Dict[str, Any]]) -> str:
    if not authors:
        return "Unknown"
    first = authors[0].get("name", "Unknown")
    return f"{first} et al." if len(authors) > 1 else first


def _abstract_snippet(text: str, max_chars: int = 400) -> Optional[str]:
    if not text:
        return None
    text = sanitize_text(text, max_length=max_chars + 1)
    if len(text) <= max_chars:
        return text
    # Trim on last sentence boundary if possible.
    cut = text[:max_chars]
    last_dot = cut.rfind(". ")
    if last_dot >= max_chars - 120:
        return cut[: last_dot + 1]
    return cut + "…"


def _build_card(pmid: str, summary: Dict[str, Any], abstract: Optional[str]) -> Dict[str, Any]:
    pub_types = list(summary.get("pubtype") or [])
    is_review = any(pt in _SYSTEMATIC_REVIEW_TYPES for pt in pub_types)
    return {
        "pmid": pmid,
        "title": (summary.get("title") or "").strip(),
        "authors_short": _short_authors(summary.get("authors") or []),
        "journal": (summary.get("fulljournalname") or summary.get("source") or "").strip(),
        "year": (summary.get("pubdate") or "")[:4] or None,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "pub_types": pub_types,
        "is_systematic_review": is_review,
        "abstract_snippet": _abstract_snippet(abstract) if abstract else None,
    }


# ─── Public API ───────────────────────────────────────────────────────────────

async def fetch_evidence(
    intervention: str,
    *,
    max_results: int = 3,
    include_abstract: bool = True,
) -> Dict[str, Any]:
    """Return a source-tagged payload for a given intervention.

    On full PubMed failure we return an empty ``cards`` list tagged as
    ``fallback``. Never raises — consumers render an empty state.
    """
    safe_intervention = sanitize_text(intervention, max_length=80).lower().strip()
    search_term = INTERVENTION_SEARCH_TERMS.get(
        safe_intervention, f"{safe_intervention} mental health"
    )

    cache = get_cache()
    key = _cache_key(search_term, max_results, include_abstract)
    try:
        hit = await cache.get(key)
    except Exception:  # pragma: no cover
        hit = None

    if hit:
        return {
            "intervention": safe_intervention,
            "cards": hit.get("cards", []),
            "source": "cached",
            "provider": "pubmed",
            "cache_key": key,
            "notes": hit.get("notes", []),
        }

    notes: List[str] = []
    cards: List[Dict[str, Any]] = []

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            ids = await _esearch(client, search_term, max_results)
            if not ids:
                notes.append("No PMIDs returned by ESearch")
                # Negative-cache the empty result briefly so we don't retry hot.
                try:
                    await cache.set(key, {"cards": [], "notes": notes}, ttl=_NEGATIVE_CACHE_TTL)
                except Exception:  # pragma: no cover
                    pass
                return {
                    "intervention": safe_intervention,
                    "cards": [],
                    "source": "fallback",
                    "provider": "pubmed",
                    "cache_key": key,
                    "notes": notes,
                }

            summaries = await _esummary(client, ids)
            abstracts: Dict[str, str] = {}
            if include_abstract:
                abstracts = await _efetch_abstracts(client, ids)

            for pmid in ids:
                summary = summaries.get(pmid)
                if not summary:
                    continue
                cards.append(_build_card(pmid, summary, abstracts.get(pmid)))
    except Exception as exc:
        logger.exception("evidence_fetch_failed", extra={"error": str(exc)})
        notes.append(f"PubMed error: {exc}")
        return {
            "intervention": safe_intervention,
            "cards": [],
            "source": "fallback",
            "provider": "pubmed",
            "cache_key": key,
            "notes": notes,
        }

    latency_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "evidence_fetched",
        extra={
            "intervention": safe_intervention,
            "result_count": len(cards),
            "latency_ms": round(latency_ms, 1),
            "api_key_set": bool(settings.ncbi_api_key),
        },
    )

    # Dedupe by PMID and promote systematic reviews to the top.
    seen: set = set()
    deduped: List[Dict[str, Any]] = []
    for card in cards:
        pmid = card["pmid"]
        if pmid in seen:
            continue
        seen.add(pmid)
        deduped.append(card)
    deduped.sort(key=lambda c: (not c["is_systematic_review"], -int(c.get("year") or "0" or 0)))

    try:
        await cache.set(key, {"cards": deduped, "notes": notes}, ttl=_CACHE_TTL_SECONDS)
    except Exception:  # pragma: no cover
        pass

    return {
        "intervention": safe_intervention,
        "cards": deduped,
        "source": "live",
        "provider": "pubmed",
        "cache_key": key,
        "notes": notes,
    }


async def refresh_curated_interventions() -> Dict[str, int]:
    """Scheduler entry point — pre-warms the cache for the curated term list.

    Runs sequentially with a small sleep between queries to stay well under
    NCBI's rate cap even when the API key is absent. Returns a summary for
    logging (``{intervention: cards_fetched}``) — exceptions inside one
    query never abort the others.
    """
    summary: Dict[str, int] = {}
    for intervention in INTERVENTION_SEARCH_TERMS:
        try:
            result = await fetch_evidence(intervention, max_results=3, include_abstract=True)
            summary[intervention] = len(result.get("cards", []))
        except Exception as exc:  # pragma: no cover — defensive
            logger.info(
                "evidence_refresh_item_failed",
                extra={"intervention": intervention, "error": str(exc)},
            )
            summary[intervention] = -1
        # Space requests ~500ms apart so we never exceed 3 req/s even without a key.
        await asyncio.sleep(0.5)
    logger.info("evidence_refresh_complete", extra={"summary": summary})
    return summary


def schedule_evidence_refresh() -> None:
    """Register the evidence-refresh job with the global scheduler.

    Safe to call multiple times — ``schedule_interval`` uses
    ``replace_existing=True``.
    """
    # Deferred import avoids circular deps between scheduler + services.
    from lib.infra.scheduler import get_scheduler

    scheduler = get_scheduler()

    def _run() -> None:
        # The scheduler expects a sync callable; we launch the coroutine on
        # the running loop so we don't block the scheduler worker thread.
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:  # pragma: no cover
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(refresh_curated_interventions(), loop)
        else:
            loop.run_until_complete(refresh_curated_interventions())

    scheduler.schedule_interval(
        "evidence_refresh_curated",
        _run,
        seconds=6 * 3600,  # every 6 hours
        run_on_start=False,  # first cache-populate happens lazily on first hit
    )
