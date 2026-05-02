"""
Component 4 — Filter-bubble mitigation for the community Feed Ranker.

Why this exists
---------------
``feed_ranker.rank_feed_posts`` scores every post by personalised
relevance, blends that with recency, and sorts descending. For a
stressed/anxious user that means the top of the feed is reliably
"stress / anxiety content — ranked by how stressed you are". Over
weeks this creates a classic filter bubble:

* The user stops seeing milestones, tips, or general-discussion posts
  even when they'd be restorative.
* Posts about coping strategies that don't match the user's *current*
  affect (but might *help* them shift it) are systematically hidden.
* New post types never get surfaced, because the model was trained on
  the same narrow slice of interactions.

This module adds a small, deterministic "exploration pass" over the
ranked feed that intermixes serendipitous posts — different post_type
and different topical focus — into the top-N without disturbing the
fundamental relevance ordering of the rest. Think of it as the news-
feed equivalent of epsilon-greedy: most of what you see is relevance-
optimal, but a fixed fraction is deliberately diverse.

Design choices
--------------
1. **Interleave, don't replace.** We reserve a fraction of the top-N
   slots for exploration picks. The relevance-top stays at rank 1.
   Exploration picks slide into slots ``[3, 6, 9, ...]`` by default.
   That way a user who only scans the first screen still sees mostly
   relevance-ranked content, but notices variety.

2. **Dual-axis novelty.** A candidate is "novel" if it differs from
   the already-selected head on (a) ``post_type`` and (b) dominant
   topical density. We compute a cheap novelty score per candidate
   and pick the best-novelty-among-the-least-ranked.

3. **Bounded draw pool.** Exploration candidates come from positions
   ``[N, min(len, N*exploration_pool_mult)]`` of the original ranking.
   Pulling from far below is expensive and usually bad — a post that
   ranked #1000 is almost certainly low-quality for this user, not
   just off-topic.

4. **Opt-in.** Default ``exploration_rate=0.0`` keeps existing
   behaviour exactly. Callers that want filter-bubble mitigation set
   ``exploration_rate=0.15`` (≈ 1 in 7 slots explored).

Pure-Python, no torch dependency. Used by ``feed_ranker.rank_feed_posts``
as an optional post-processing step after the MLP scores are in place.
"""

from __future__ import annotations

from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fraction of top-N slots reserved for exploration picks.
# 0.15 ≈ every 7th slot is a serendipity injection. Empirically:
#   - < 0.10: user barely notices, doesn't actually break the bubble.
#   - > 0.25: feed feels scattered, relevance drops too far.
DEFAULT_EXPLORATION_RATE = 0.15

# How far down the ranking to draw exploration candidates from. At 3x
# we sample from positions [top_n, 3*top_n). Beyond that the candidate
# pool is too stale to be useful.
DEFAULT_EXPLORATION_POOL_MULT = 3

# Minimum top-N to even bother exploring. Below this the feed is too
# short for injection to matter and the user just wants the ranked order.
MIN_TOP_N_FOR_EXPLORATION = 5

# Post-type vocabulary mirrors feed_ranker.POST_TYPES. Duplicated here
# so this module stays a leaf (no import from the ranker).
POST_TYPES = ('reflect', 'milestone', 'tip', 'discussion', 'support')


# ---------------------------------------------------------------------------
# Feature extraction helpers
# ---------------------------------------------------------------------------

def _post_type(post: dict) -> str:
    pt = post.get('post_type', 'reflect')
    # feed_ranker handles enum .name unwrap; replicate defensively.
    if hasattr(pt, 'name'):
        pt = pt.name
    return str(pt)


def _dominant_topic(post: dict) -> str:
    """Return the dominant topic for a post.

    If the ranker already attached ``text_features`` we use them;
    otherwise fall back to a cheap keyword scan over ``paragraph``.
    The label is opaque — it only needs to be a stable string we can
    compare between posts. For filter-bubble purposes, "two posts
    with dominant topic 'stress'" are considered similar regardless
    of exact density.
    """
    text = (post.get('paragraph') or '').lower()
    # Minimal keyword dictionary — catches the common axes without
    # pulling in the full text_feature_config. If no keyword matches
    # we return the empty string, treated as its own bucket.
    buckets = {
        'stress': ('stress', 'overwhelm', 'burnout', 'pressure'),
        'anxiety': ('anxiety', 'worry', 'panic', 'nervous'),
        'depression': ('depress', 'hopeless', 'empty', 'numb'),
        'wellness': ('sleep', 'exercise', 'nutrition', 'health'),
        'social': ('friend', 'family', 'lonely', 'connect'),
        'emotional': ('feel', 'emotion', 'cry', 'grief'),
        'coping': ('breathe', 'cope', 'meditation', 'journal'),
    }
    best_topic = ''
    best_hits = 0
    for topic, kws in buckets.items():
        hits = sum(1 for kw in kws if kw in text)
        if hits > best_hits:
            best_hits = hits
            best_topic = topic
    return best_topic


def _novelty_score(candidate: dict, selected: list) -> float:
    """Return in [0, 1] — higher = more novel vs the selected head.

    Two components, equally weighted:
      * post-type novelty: 1.0 if no selected post shares this type,
        else 0.0.
      * topic novelty: fraction of selected posts whose dominant topic
        differs from the candidate's.
    """
    if not selected:
        return 1.0

    cand_type = _post_type(candidate)
    cand_topic = _dominant_topic(candidate)

    type_novelty = 0.0 if any(_post_type(p) == cand_type for p in selected) else 1.0

    diff_topics = sum(1 for p in selected if _dominant_topic(p) != cand_topic)
    topic_novelty = diff_topics / len(selected)

    return 0.5 * type_novelty + 0.5 * topic_novelty


# ---------------------------------------------------------------------------
# Main interleave algorithm
# ---------------------------------------------------------------------------

def inject_exploration(
    ranked_posts: list,
    *,
    exploration_rate: float = DEFAULT_EXPLORATION_RATE,
    top_n: int = 20,
    pool_mult: int = DEFAULT_EXPLORATION_POOL_MULT,
) -> list:
    """Return a new ranked list with exploration picks interleaved.

    ``ranked_posts`` must already be sorted by ``ranking_score``
    descending (the normal output of ``rank_feed_posts``).

    The top rank-1 slot is never touched — the single most relevant
    post always leads. Other reserved slots are chosen on a stride
    computed from ``exploration_rate`` so the injections are evenly
    spread across the top-N window.

    Marks each injected post with ``exploration: True`` (and swapped-
    out posts get ``exploration: False``), so the frontend can render
    a "You might also like" chip if desired.

    No-ops when:
    * ``exploration_rate <= 0`` (feature disabled)
    * ``len(ranked_posts) < MIN_TOP_N_FOR_EXPLORATION``
    * The candidate pool below ``top_n`` is empty.
    """
    if exploration_rate <= 0.0 or not ranked_posts:
        return list(ranked_posts)
    if len(ranked_posts) < MIN_TOP_N_FOR_EXPLORATION:
        return list(ranked_posts)

    rate = min(max(float(exploration_rate), 0.0), 0.5)
    n = min(int(top_n), len(ranked_posts))
    n_explore = int(round(n * rate))
    if n_explore <= 0:
        return list(ranked_posts)

    # Candidate pool: positions [n, min(len, n*pool_mult)).
    pool_end = min(len(ranked_posts), n * max(int(pool_mult), 1))
    if pool_end <= n:
        # No candidates below the top-N window — nothing to inject, but
        # still tag every post so the caller has a stable schema.
        tagged = list(ranked_posts)
        for p in tagged:
            p.setdefault('exploration', False)
        return tagged
    candidate_indices = list(range(n, pool_end))
    if not candidate_indices:
        tagged = list(ranked_posts)
        for p in tagged:
            p.setdefault('exploration', False)
        return tagged

    # Choose the exploration slots evenly across [2, n) — position 1
    # (index 0) is the headline relevance pick, never overwritten.
    # Stride = (n - 1) / n_explore so picks are roughly equispaced.
    stride = max((n - 1) / n_explore, 1.0)
    explore_slots = []
    pos = stride
    while len(explore_slots) < n_explore and pos < n:
        idx = int(round(pos))
        if 0 < idx < n and idx not in explore_slots:
            explore_slots.append(idx)
        pos += stride
    if not explore_slots:
        return list(ranked_posts)

    output = list(ranked_posts)
    # Tag everything as non-exploration by default so downstream code
    # can rely on the field's presence.
    for p in output:
        p.setdefault('exploration', False)

    selected_head = [output[i] for i in range(n) if i not in explore_slots]
    used_candidates: set[int] = set()

    for slot in sorted(explore_slots):
        best_cand_idx = None
        best_score = -1.0
        for cand_idx in candidate_indices:
            if cand_idx in used_candidates:
                continue
            cand = output[cand_idx]
            score = _novelty_score(cand, selected_head)
            if score > best_score:
                best_score = score
                best_cand_idx = cand_idx
        if best_cand_idx is None:
            continue  # pool exhausted — leave relevance pick in place


        displaced = output[slot]
        promoted = output[best_cand_idx]
        promoted['exploration'] = True
        # Swap in the novel pick, push the displaced relevance-pick
        # down into the candidate slot so nothing is lost.
        output[slot], output[best_cand_idx] = promoted, displaced
        selected_head.append(promoted)
        used_candidates.add(best_cand_idx)

    return output


__all__ = [
    'DEFAULT_EXPLORATION_RATE',
    'DEFAULT_EXPLORATION_POOL_MULT',
    'MIN_TOP_N_FOR_EXPLORATION',
    'POST_TYPES',
    'inject_exploration',
]
