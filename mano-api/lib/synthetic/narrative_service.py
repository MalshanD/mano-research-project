"""
Component 1 Enhancement Services

Enhancement A: Future-Self Narrative Engine
  Translates Seq2Seq numerical outcomes into emotionally resonant "future journal entries"
  using Groq Cloud (Llama 3) — free: ~30 RPM, 14.4K req/day, ultra-fast inference.

Enhancement B: Synthetic Social Proof (The Artificial Cohort)
  Uses CTGAN (PRESERVED) to generate 50 synthetic profiles similar to the user,
  runs simulation on them, and presents aggregate social proof statistics.

Enhancement C: PubMed E-utilities Evidence Cards
  Fetches real research evidence from PubMed (free, no API key, 3 req/sec)
  to back intervention recommendations with published studies.

All existing ML models are PRESERVED and REUSED:
  ✓ CTGAN — generates synthetic cohort profiles
  ✓ Seq2Seq + Attention — projects 7-day outcomes
  ✓ PPO Actor-Critic — selects optimal interventions
  ✓ Hybrid LSTM — risk prediction
  ✓ TimeGAN — synthetic wearable data
"""

import os
import httpx
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
from datetime import datetime


# ── Enhancement A: Future-Self Narrative Engine ───────────────────────────────

class FutureSelfNarrativeEngine:
    """
    Translates abstract Seq2Seq simulation numbers into a personal "Future Journal Entry."
    Instead of showing "Day 7: stress=-0.3, anxiety=-0.5", the user sees:
    "It's Day 7. My resting heart rate has stabilized, and my anxiety spikes are much lower."

    Uses Groq Cloud (Llama 3) for ultra-fast inference.
    Free tier: ~30 RPM, 14.4K req/day — no credit card required.
    """

    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def generate_narrative(
        self,
        intervention_name: str,
        simulation_data: Dict,
        user_profile: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        Generate a future-self journal entry from simulation results.

        Args:
            intervention_name: e.g., "High-Intensity Meditation"
            simulation_data: Seq2Seq output {day_1: {...}, day_7: {...}, changes: {...}}
            user_profile: Optional user context for personalization

        Returns:
            A first-person narrative journal entry, or None if unavailable.
        """
        if not self.is_available:
            return self._fallback_narrative(intervention_name, simulation_data)

        # Build the prompt
        prompt = (
            f"You are writing a brief first-person journal entry from the perspective of someone "
            f"who just completed 7 days of '{intervention_name}'. Based on these simulation results:\n\n"
        )

        if simulation_data.get("changes"):
            for metric, change in simulation_data["changes"].items():
                direction = "improved" if change < 0 else "increased"
                prompt += f"- {metric}: {direction} by {abs(change):.1f}\n"

        prompt += (
            f"\nWrite a 3-4 sentence journal entry that feels authentic and personal. "
            f"Focus on how the changes FEEL, not the numbers. Use first person. "
            f"Keep it warm, hopeful, and specific to the intervention."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You write authentic, emotionally resonant journal entries. Keep them brief and personal."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 200,
        }

        try:
            client = await self._get_client()
            resp = await client.post(self.GROQ_URL, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0]["message"]["content"].strip()
        except Exception as e:
            print(f"[FutureSelfNarrative] Groq error: {e}")

        return self._fallback_narrative(intervention_name, simulation_data)

    def _fallback_narrative(self, intervention_name: str, simulation_data: Dict) -> str:
        """Template-based fallback when Groq is unavailable."""
        changes = simulation_data.get("changes", {})
        improvements = [k for k, v in changes.items() if v < 0]

        if improvements:
            improved_text = " and ".join(improvements[:2])
            return (
                f"It's Day 7 of my {intervention_name} journey. I've noticed real changes — "
                f"my {improved_text} levels have genuinely improved. The first few days were hard, "
                f"but I can feel the difference now. This is what progress feels like."
            )
        else:
            return (
                f"After a week of {intervention_name}, I'm starting to notice subtle shifts. "
                f"It hasn't been easy, but showing up every day matters. "
                f"I'm learning that consistency matters more than perfection."
            )


# ── Enhancement C: PubMed Evidence Cards ──────────────────────────────────────

class PubMedEvidenceService:
    """
    Fetches research evidence from PubMed E-utilities (NCBI).
    Free, no API key required, 3 requests/second limit.

    Used to back intervention recommendations with real published studies,
    building trust through transparency.
    """

    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    # Pre-curated search terms for common interventions
    INTERVENTION_SEARCH_TERMS = {
        "meditation": "mindfulness meditation mental health randomized",
        "exercise": "physical exercise depression anxiety reduction meta-analysis",
        "sleep": "sleep hygiene mental health improvement",
        "breathing": "deep breathing anxiety reduction clinical",
        "journaling": "expressive writing mental health benefits",
        "social_connection": "social support mental health protective factor",
        "nature_walk": "nature exposure cortisol stress reduction",
        "gratitude": "gratitude practice psychological well-being",
        "cbt": "cognitive behavioral therapy effectiveness meta-analysis",
        "yoga": "yoga mental health anxiety depression systematic review",
    }

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def get_evidence(self, intervention_type: str, max_results: int = 3) -> List[Dict]:
        """
        Search PubMed for evidence supporting an intervention.

        Returns list of: [{title, authors, journal, year, pmid, url}]
        """
        search_term = self.INTERVENTION_SEARCH_TERMS.get(
            intervention_type.lower(),
            f"{intervention_type} mental health"
        )

        try:
            client = await self._get_client()

            # Step 1: Search for article IDs
            search_params = {
                "db": "pubmed",
                "term": search_term,
                "retmax": max_results,
                "sort": "relevance",
                "retmode": "json",
            }
            search_resp = await client.get(self.SEARCH_URL, params=search_params)
            if search_resp.status_code != 200:
                return []

            search_data = search_resp.json()
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            # Step 2: Get article summaries
            summary_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json",
            }
            summary_resp = await client.get(self.SUMMARY_URL, params=summary_params)
            if summary_resp.status_code != 200:
                return []

            summary_data = summary_resp.json()
            results = summary_data.get("result", {})

            evidence_cards = []
            for pmid in id_list:
                article = results.get(pmid, {})
                if not article:
                    continue

                authors = article.get("authors", [])
                author_str = authors[0].get("name", "Unknown") if authors else "Unknown"
                if len(authors) > 1:
                    author_str += " et al."

                evidence_cards.append({
                    "title": article.get("title", ""),
                    "authors": author_str,
                    "journal": article.get("fulljournalname", article.get("source", "")),
                    "year": article.get("pubdate", "")[:4],
                    "pmid": pmid,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                })

            return evidence_cards

        except Exception as e:
            print(f"[PubMedEvidence] Error: {e}")
            return []

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global singletons
narrative_engine = FutureSelfNarrativeEngine()
pubmed_service = PubMedEvidenceService()
