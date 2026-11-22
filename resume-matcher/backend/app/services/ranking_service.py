"""Ranking: descending final score; ties broken by mandatory-skill score, then semantic score.

Equal scores share the same rank ("competition ranking": 1, 2, 2, 4) so no candidate is
arbitrarily placed above an equally-scored one.
"""
from collections.abc import Iterable


def _key(r) -> tuple:
    return (r.final_score or 0.0, r.skill_score or 0.0, r.semantic_score or 0.0)


def assign_ranks(results: Iterable) -> list:
    ordered = sorted(results, key=_key, reverse=True)
    prev, rank = None, 0
    for i, r in enumerate(ordered, start=1):
        k = _key(r)
        if k != prev:
            rank, prev = i, k
        r.rank = rank
    return ordered
