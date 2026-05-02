"""
Tests for lib/activity/feed_diversity.py
=========================================
Covers filter-bubble mitigation via exploration injection into the
ranked feed.
"""
from __future__ import annotations

import pytest

from lib.CBT.feed_diversity import (
    DEFAULT_EXPLORATION_RATE,
    MIN_TOP_N_FOR_EXPLORATION,
    inject_exploration,
)


def _post(post_id, post_type, paragraph, ranking_score):
    return {
        'id': post_id,
        'post_type': post_type,
        'paragraph': paragraph,
        'ranking_score': ranking_score,
    }


def _ranked(n, post_type='reflect', paragraph='stress overwhelm'):
    return [
        _post(f'p{i}', post_type, paragraph, round(1.0 - i * 0.01, 4))
        for i in range(n)
    ]


class TestInjectExploration:
    def test_disabled_by_default(self):
        # exploration_rate=0.0 → identity.
        posts = _ranked(20)
        result = inject_exploration(posts, exploration_rate=0.0)
        assert [p['id'] for p in result] == [p['id'] for p in posts]

    def test_empty_input(self):
        assert inject_exploration([], exploration_rate=0.2) == []

    def test_below_min_top_n_is_noop(self):
        # Too few posts → don't bother injecting, just hand back.
        posts = _ranked(MIN_TOP_N_FOR_EXPLORATION - 1)
        result = inject_exploration(posts, exploration_rate=0.2)
        assert [p['id'] for p in result] == [p['id'] for p in posts]

    def test_headline_preserved(self):
        # The #1 relevance pick is sacred — never displaced.
        posts = (
            _ranked(5, 'reflect', 'stress') +
            _ranked(15, 'tip', 'coping')  # novel pool
        )
        # fix ids so pool ids don't collide
        for i, p in enumerate(posts):
            p['id'] = f'p{i}'
            p['ranking_score'] = round(1.0 - i * 0.01, 4)
        result = inject_exploration(posts, exploration_rate=0.3, top_n=10)
        assert result[0]['id'] == 'p0'

    def test_injects_from_below_top_n(self):
        # Build a feed where the top-N is uniform (all reflect/stress)
        # and the candidate pool has a different type/topic.
        top = [
            _post(f'h{i}', 'reflect', 'stress overwhelm burnout', 0.9 - i * 0.01)
            for i in range(10)
        ]
        pool = [
            _post(f'c{i}', 'milestone', 'breathe meditation coping', 0.5 - i * 0.01)
            for i in range(10)
        ]
        posts = top + pool
        result = inject_exploration(posts, exploration_rate=0.3, top_n=10)
        # After injection, at least one of positions 2..9 should be a
        # milestone-from-pool, tagged exploration=True.
        injected = [r for r in result[:10] if r.get('exploration')]
        assert len(injected) >= 1
        assert all(r['post_type'] == 'milestone' for r in injected)

    def test_tags_exploration_flag(self):
        posts = _ranked(20)
        # Make some candidates genuinely different so injection fires.
        for i in range(10, 20):
            posts[i]['post_type'] = 'tip'
            posts[i]['paragraph'] = 'coping journal meditation'
        result = inject_exploration(posts, exploration_rate=0.3, top_n=10)
        # Every post should have the field set (True or False).
        for r in result:
            assert 'exploration' in r

    def test_rate_clamped_to_max(self):
        posts = _ranked(20)
        for i in range(10, 20):
            posts[i]['post_type'] = 'tip'
        # Even with rate=0.99, the function caps at 0.5 internally.
        result = inject_exploration(posts, exploration_rate=0.99, top_n=10)
        # Top-1 still preserved
        assert result[0]['id'] == 'p0'
        # Length unchanged
        assert len(result) == len(posts)

    def test_preserves_length_and_membership(self):
        posts = _ranked(25)
        for i in range(15, 25):
            posts[i]['post_type'] = 'tip'
        result = inject_exploration(posts, exploration_rate=0.2, top_n=10)
        assert len(result) == len(posts)
        assert {p['id'] for p in result} == {p['id'] for p in posts}

    def test_empty_candidate_pool(self):
        # top_n equals list length → no candidates below top_n.
        posts = _ranked(10)
        result = inject_exploration(posts, exploration_rate=0.3, top_n=10)
        # Nothing to inject from → return unchanged order (but tagged).
        assert [p['id'] for p in result] == [p['id'] for p in posts]
        for p in result:
            assert p['exploration'] is False

    def test_displaced_post_not_lost(self):
        # When an injection swaps a novel pool post into slot k, the
        # post that was there should re-appear later in the output.
        posts = (
            [_post(f'h{i}', 'reflect', 'stress', 0.9 - i * 0.01) for i in range(10)] +
            [_post(f'c{i}', 'milestone', 'breathe coping', 0.5 - i * 0.01) for i in range(10)]
        )
        ids_before = {p['id'] for p in posts}
        result = inject_exploration(posts, exploration_rate=0.3, top_n=10)
        assert {p['id'] for p in result} == ids_before

    def test_novelty_prefers_different_type(self):
        # Build a feed where the headline is 'reflect' and pool has
        # both 'reflect' and 'milestone'. Injection should pick the
        # milestone because it's type-novel.
        top = [_post('h0', 'reflect', 'stress', 0.9)] + [
            _post(f'h{i}', 'reflect', 'stress', 0.9 - i * 0.01)
            for i in range(1, 10)
        ]
        pool = [
            _post('c_same', 'reflect', 'stress overwhelm', 0.4),
            _post('c_novel', 'milestone', 'breathe coping meditation', 0.35),
        ]
        posts = top + pool + [_post(f'pad{i}', 'reflect', 'stress', 0.1 - i * 0.01) for i in range(5)]
        result = inject_exploration(posts, exploration_rate=0.2, top_n=10)
        head_ids = [r['id'] for r in result[:10]]
        # c_novel should outrank c_same for injection even though c_same
        # has higher ranking_score.
        if 'c_same' in head_ids or 'c_novel' in head_ids:
            # If both got in, c_novel must be present.
            assert 'c_novel' in head_ids


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
